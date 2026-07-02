## Context

本项目是 monorepo：同一份代码同时部署在国内服务器（运行 `backend/` + `frontend/`）和国外服务器（仅作数据源出口）。前端需要美股 ETF 数据，但国内机访问 yfinance/yahooquery 受限、不稳定。

本 change 解决「国外机 → 国内机」的数据管线**国外侧**：拉取、暂存、推送。不涉及国内侧的接收、落地、查询 API——那些由平行 change `etf-remote-data-persist` 定义。

跨海链路不稳定、且两台机器时钟不完全对齐——这是所有设计决策的底层假设。

## Goals / Non-Goals

**Goals:**
- 在国外机启动一个常驻进程，按配置 cadence 定时拉取 ~20 只 ETF 的数据
- 数据本地落 sqlite，**任何推送失败都能从本地重放**
- 推送采用 HMAC-SHA256 + timestamp 窗口鉴权（防重放、防篡改）
- 与 `etf-remote-data-persist` 严格对齐 ingest 端点契约
- 国外机的依赖与启动**完全自包含**，不引用 `backend/` 任何代码

**Non-Goals:**
- 国内侧的 ingest endpoint 实现（属于 `etf-remote-data-persist`）
- 前端展示（属于未来 change）
- 反向同步（国内→国外）——本 change 单向
- 实时 K 线（用户明确说本轮不要）
- 2 年以上的 PE/PB 历史（实测 yahooquery 拿不到）
- 多机 HA / failover（接受单点权威）

## Decisions

### 1. 推送协议：HTTP POST（不是 rclone / S3）

**Why**: HTTP 是最直接的契约；HMAC 鉴权、payload schema 校验、idempotent UPSERT 都好做。S3 / rclone 适合「大文件批」，不适合「小批量高频」。

**Alternatives considered**:
- **rclone 到 S3 兼容存储**：要求国内机跑一个 listener，且 cross-cloud egress 成本高。否决。
- **国内机主动 pull**：NAT 穿透 + 跨海双向都更不稳。否决。
- **直连数据库同步**：跨海直连 SQLite 文件，丢失原子性。否决。

### 2. 鉴权：HMAC-SHA256 + timestamp 窗口（±5 分钟）

**Why**: 防重放、防篡改。secret 只在两台机器的 `.env` 里，**绝不入 git**。

**Algorithm**:
```
to_sign = timestamp_utf8 + b"\n" + body_utf8
signature = hmac.new(secret, to_sign, hashlib.sha256).hexdigest()
```

**Window**: 300s。短到能容忍跨海网络抖动 + 时钟几百毫秒漂移，长到不足以让一个被嗅探的请求被长时间重放。

**Alternatives considered**:
- **mTLS**：需要签发客户端证书、CA 维护，运维成本高。否决。
- **静态 API key in header**：被嗅探 = 永久泄露。否决。
- **OAuth / JWT**：本场景无 user 概念，过度设计。否决。

### 3. 本地存储：sqlite（`data/etf_local.db`），每张业务表带 `pushed_at`

**Why**: 重试游标 = `WHERE pushed_at IS NULL`。push 成功后 UPDATE 一行即可。`etf_news` 单独考虑保留窗口（默认 30 天后归档到 `etf_news_archive`）。

**Schema 概要**（每张业务表）：
```
etf_quote:        symbol, ts, price, pre_market_price, post_market_price, volume, pushed_at
etf_fundamentals: symbol, as_of, pe, pb, dividend_yield, ..., pushed_at
etf_holdings:     symbol, as_of_date, payload_json, pushed_at
etf_sector_weights: symbol, as_of_date, payload_json, pushed_at
etf_performance:  symbol, as_of_date, ytd_return, 1y/3y/5y/10y_return, pushed_at
etf_equity_holdings: symbol, as_of_date, payload_json, pushed_at
etf_esg:          symbol, as_of_date, payload_json, pushed_at
etf_news:         url_pk, symbol, title, body, published_at, source, pushed_at
push_log:         id, data_type, batch_id, sent_at, http_status, retry_count, error
```

**Alternatives considered**:
- **纯文件（jsonl）**：查询/重试游标管理麻烦。否决。
- **Postgres / MySQL**：在仅做缓冲的本地侧过重。否决。

### 4. Push 载荷：一次只推一种 `data_type`、包含多条 records

**Why**: 单一类型失败不影响其它类型；UPSERT 简单（`(symbol, as_of/ts)` 唯一键）；重试粒度更细。

**Body schema**：
```json
{
  "data_type": "etf_quote",
  "batch_id": "2026-06-29T03:14:00Z-etf_quote",
  "records": [ { "symbol": "QQQ", "ts": "...", "price": 521.34, ... }, ... ]
}
```

**Alternatives considered**:
- **大杂烩 payload**：一个请求里塞所有类型，失败重试代价大。否决。
- **一条记录一次请求**：HTTP 开销太大、HMAC 验签成本高。否决。

### 5. 调度：APScheduler 进程内 cron

**Why**: 单进程即可，避免额外引入 systemd timer / Celery beat。job 失败有 listener，能 push 到 `push_log`。

**Cadence 默认值**（可在 `.env` 覆盖）：

| Job | 频率 | 触发条件 |
|---|---|---|
| `fetch_quotes` | 每 5 min | 美股交易时段（含盘前盘后降频） |
| `fetch_news` | 每 60 min | 醒着时段 |
| `fetch_kline` | 每天 1 次 | 美东 16:30 后 |
| `fetch_fundamentals` | 每天 1 次 | EOD |
| `fetch_holdings` | 每周 1 次 | 周日 10:00 ET |
| `fetch_sector_weights` | 每周 1 次 | 周日 10:00 ET |
| `fetch_equity_holdings` | 每周 1 次 | 周日 10:00 ET |
| `fetch_performance` | 每天 1 次 | EOD |
| `fetch_esg` | 每月 1 次 | 月初 |
| `push_pending` | 持续运行 | 独立循环：每 30s 扫 `pushed_at IS NULL` 推送 |
| `backfill_fundamentals_2y` | 启动时跑一次 | 仅当 `etf_fundamentals` 表为空时触发 |

**Alternatives considered**:
- **systemd timer**：每 job 一个 unit，调试不方便。否决。
- **Celery beat + worker**：过重。否决。

### 6. yahooquery 包装：每个 data type 一个文件

**Why**: fetcher 文件大、字段多，分文件便于 review / mock / 测试。统一返回「标准化 record dict」格式（不返回 yahooquery 原始结构），下游 pusher 不感知数据源。

**Why normalize early**: 后续若要切换数据源（multpl、FMP），pusher 一行不改。

### 7. 错误处理

| 错误 | 处理 |
|---|---|
| yahooquery 单只 ETF 失败 | 跳过、写 `fetch_log`、不阻塞其它 ETF |
| yahooquery 整体失败（断网/限流） | 整个 job 失败、写 `fetch_log`、下个 cadence 继续 |
| 单条推送 5xx / timeout | 退避 1s → 4s → 16s → 落 `push_log`、下个 push 循环继续 |
| 单条推送 4xx（schema 错） | 立即落 `etf_dead_letter`、标记 `failed_at`、告警、不再重试 |
| HMAC 验签失败（理论上不会，因为是我们自签） | 401（由 remote 端处理；本地不感知） |
| 连续 N 次推送失败 | 发告警（Telegram / 日志，看 §5 决策） |

### 8. 部署

- **进程管理**：systemd unit（推荐） / supervisor / pm2，三选一，用户定
- **启动**：`python -m remote_data`
- **日志**：stdout + `data/etf_local.log`（rotating）
- **健康检查**：可选暴露 `localhost:8001/health`（仅本地，外部不开放）
- **重启策略**：on-failure，30s 内最多 3 次

### 9. Bootstrap：三种入口共享一份 schema 应用逻辑

「拉起 fetcher-pusher」在生产环境至少有三条入口：systemd（unit 启动 `python -m remote_data`）、`scripts/start-etf-fetcher.sh`（手动 / ad-hoc 调试）、纯 `python -m remote_data`（开发机直跑）。这三条入口必须共享同一份 schema 应用代码（`local_db.init()`），否则 schema 迁移会漂移。

| 入口 | 文件 | 谁调 | 时机 |
|---|---|---|---|
| **A. `main.py` 启动钩子** | `remote_data/main.py` 的 `if __name__ == "__main__"` | systemd unit / 开发机直接调用 | 在 `scheduler.start()` **之前**调用 `local_db.init()` |
| **B. 独立 Python 初始化脚本** | `remote_data/scripts/init_local_db.py` | 运维 / 部署脚本 / 灾备恢复 / CI smoke test | 显式跑一次；可重复跑（幂等） |
| **C. Shell 启动脚本** | `scripts/start-etf-fetcher.sh` | 不想用 systemd 的部署者 / 前台调试 | 启动 daemon **之前**先调 B，再让 daemon 走 A 的同一份 `local_db.init()` |

**Why three entry points, not one**:
- **A** 保证即使用户直接 `python -m remote_data`（开发机 / 临时调试）表也会建出来——不能假设运维知道有新脚本
- **B** 让运维可以在不上 daemon 的情况下初始化 DB（例如新建 replica、灾备恢复、CI smoke test）
- **C** 把「先建表再起 daemon」做成原子操作，避免运维忘了先跑 B——但仍然让 A 做兜底

**Why not one script (e.g., only the systemd unit)**:
- systemd 之外的部署者（mac 开发机、docker、裸前台）也需要等价保证
- 与 `etf-remote-data-persist` 的 `init_etf_db.py` 路径对称，便于运维记忆

**Idempotency contract**: `local_db.init()` MUST be safe to call:
- on a fresh filesystem (creates `data/` parent dir + `etf_local.db` + 全部表)
- on a DB with all tables present (no-op, `CREATE TABLE IF NOT EXISTS`)
- on a DB with a subset of tables (creates the missing ones)

**`.env` loading**: `init_local_db.py` MUST call `load_dotenv()` on `remote_data/.env` so `LOCAL_DB_PATH` overrides work without manual `export`. Same logic as `remote_data/config.py`.

## Risks / Trade-offs

- **[R1] 跨海网络抖动 → 推送 5xx 频繁**
  - Mitigation: 指数退避 + 本地积压 + `pushed_at` 游标；网络恢复后批量补发
- **[R2] yahooquery 单点依赖**（Yahoo 改 API / 限流）
  - Mitigation: fetcher 抽象层 + normalize 早做，切换到 FMP / multpl 只需改 fetcher 一个子包
- **[R3] HMAC secret 一旦泄露** = 系统完全沦陷
  - Mitigation: 64 字节随机生成 + 不进 git + 定期轮换（在 ops 文档里说明，不在本 change 实现）
- **[R4] 时钟漂移**导致 timestamp 窗口误拒
  - Mitigation: window 选 5 分钟（容忍 1s 级漂移足够）；两端跑 `chrony` / `ntpdate`
- **[R5] 本地 sqlite 无限增长**
  - Mitigation: `etf_quote` 保留 90 天；`etf_kline` 保留 2 年；`etf_news` 保留 30 天（详情见 etf-local-store spec）
- **[R6] 单点权威 → 国外机宕机 = 数据停摆**
  - Mitigation: 接受（用户明确不要国内机做容灾）；监控告警即可
- **[R7] 20 只 ETF 白名单写死**
  - Mitigation: 从 `.env` 读，未来要改不动代码

## Migration Plan

- **首次部署（推荐路径：systemd unit）**：
  1. `git pull` 当前分支
  2. `cd remote_data && uv sync`
  3. `cp .env.example .env`、填入 `REMOTE_INGEST_URL` / `ETF_PIPELINE_SECRET`（与国内机一致）/ `SYMBOLS`
  4. `uv run remote_data/scripts/init_local_db.py` —— 单独跑一次，建空 DB + 表（幂等）
  5. 配 systemd unit（沿用 README 模板），`ExecStart` 直接写 `python -m remote_data`——main.py 启动钩子会在 scheduler 启动前再调一次 `local_db.init()`，是兜底
  6. `systemctl start remote-data`
  7. 观察 `data/etf_local.log` + `push_log` 表
- **首次部署（无 systemd 路径：`start-etf-fetcher.sh`）**：
  1. 同上 1-3
  2. `scripts/start-etf-fetcher.sh` —— 内部顺序：`init_local_db.py` → `python -m remote_data`
  3. 适用场景：mac 开发机、临时调试、不想引入 systemd 的部署者
- **灾备 / replica**：
  - 只跑 `uv run remote_data/scripts/init_local_db.py` 即可建好空 DB；不启 daemon
- **升级**：
  1. 国外机 `git pull` → `systemctl restart remote-data`
  2. 国内机**先升** ingest 端点（向后兼容旧 schema），再升国外机
- **回滚**：
  1. `systemctl stop remote-data`
  2. 切换到上一 commit 重启
  3. 本地 `etf_local.db` 是兼容的（schema 变更必须先做迁移）

## Open Questions

- 进程守护选 systemd / supervisor / pm2？（决策未拍）
- 告警通道：Telegram 还是只写日志？（决策未拍）
- `.env` 在国外机上是手填还是要从 secrets manager 拉？（项目目前没有 secrets manager）
- 白名单 ETF 是否要可在线热更新（不重启拉新 list）？（先做 `.env` 重启生效）
