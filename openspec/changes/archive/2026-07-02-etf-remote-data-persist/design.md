## Context

本项目是 monorepo。国外服务器（由 `etf-fetcher-pusher` change 负责）按 cadence 拉取美股 ETF 数据后，通过 HTTPS POST 把数据推到国内服务器。国内服务器（运行 `backend/` 和 `frontend/`）需要：

1. 一个 ingest 端点接收推送、验签、校验、落地
2. 落地后给前端 / 内部其它 service 提供读 API
3. 防止误用和暴力探测的限流

国内服务器访问 yahooquery 不稳定，但前端的请求量（read API）和 ingest 端的请求量（push API）都很小且频次可控，**单进程 FastAPI 即可承载**，不引入额外基础设施（无 Redis / MQ / K8s）。

跨海网络是单向上传（local → remote），是设计的主要约束——必须能承受 local 端 6h+ 断网后的批量补发。

## Goals / Non-Goals

**Goals:**
- 实现 `/api/etf/ingest` 端点，HMAC-SHA256 + timestamp 窗口验签
- Pydantic 严格校验 payload；任何字段类型不匹配 → 4xx
- UPSERT 到 `etf_remote.db`，按 `(symbol, as_of/ts)` 唯一键，重复推送幂等
- 提供 read API 给前端，覆盖 8 种 data type 的查询
- IP 滑动窗口限流，默认 50000 req/天
- 不修改任何现有 endpoint 行为

**Non-Goals:**
- 国外机 fetcher / pusher 本身（属于 `etf-fetcher-pusher`）
- ETF 前端页面（属于未来 change）
- 多 region / 异地容灾（用户明确说单点）
- 反向同步（remote → local）
- WebSocket 推送（前端按需 GET 即可）
- 真实 K 线图（本轮不要；quote 实时价够用）

## Decisions

### 1. 数据库：独立 sqlite 文件 `data/etf_remote.db`

**Why**: 不与 `watchlist.db` 共享，避免迁移打架；体量预期 ~1-2 GB/年（4 万 ETF 数据点/天 + 新闻），sqlite 完全能扛。

**Path**: `REMOTE_DB_PATH` 配置项，默认 `./data/etf_remote.db`。

**Alternatives considered**:
- **复用 `watchlist.db`**：表多、迁移路径敏感、backup 流程复杂。否决。
- **Postgres**：单进程、单机 sqlite 够用，过重。否决。

### 2. 表结构：与 `etf-fetcher-pusher` 的 `etf-local-store` 1:1 对齐，**去掉** `pushed_at` / `failed_at` / `etf_dead_letter`

**Why**: 远端是「已落地、给前端读」的状态机，不需要推送游标。pusher 在源端管推送，远端只负责 verify + UPSERT。

**表清单**：
```
etf_quote        (symbol, ts PK, price, pre_market_price, post_market_price, volume)
etf_fundamentals (symbol, as_of PK, pe, pb, dividend_yield, dividend_rate)
etf_holdings     (symbol, as_of_date PK, payload_json)
etf_sector_weights (symbol, as_of_date PK, payload_json)
etf_performance  (symbol, as_of_date PK, ytd, 1y, 3y, 5y, 10y)
etf_equity_holdings (symbol, as_of_date PK, payload_json)
etf_esg          (symbol, as_of_date PK, payload_json)
etf_news         (url PK, symbol, title, publisher, published_at, summary)
etf_ingest_log   (id PK, batch_id, data_type, source_ip, accepted, rejected, received_at)
```

**UPSERT 策略**：
- `etf_quote`：PK = `(symbol, ts)`；重复推送 = 同一时间点的价格取最新一条（UPDATE 全部字段）
- `etf_fundamentals`：PK = `(symbol, as_of)`；重复推送 = 覆盖
- `etf_holdings / sector_weights / equity_holdings / esg`：PK = `(symbol, as_of_date)`；payload_json 整列覆盖
- `etf_news`：PK = `url`；同一 url 不重复入库（`INSERT OR IGNORE`）
- `etf_performance`：PK = `(symbol, as_of_date)`；逐字段覆盖

### 3. 鉴权中间件：HMAC-SHA256 + timestamp 窗口（与 `etf-fetcher-pusher` 严格对称）

**Algorithm**:
```
expected = HMAC_SHA256(secret, timestamp_utf8 + b"\n" + body_utf8)
ok = hmac.compare_digest(expected, header_signature)
ok &= abs(now - timestamp) <= TIME_WINDOW_SECONDS
```

**Headers**:
- `X-ETF-Pipeline-Timestamp`: ISO8601 UTC string
- `X-ETF-Pipeline-Signature`: hex string

**白名单路径**：HMAC 中间件**只**保护 `/api/etf/ingest`；所有其它路径（read API、`/docs`、`/health`）不受 HMAC 限制（read API 通过 CORS / 限流保护）。

**Why middleware (not dependency injection)**: 中间件一次性处理所有 ingest 路径，验签失败立即 401，pydantic 校验前先 fail-fast，节省 CPU。

### 4. 端点：单一 `/api/etf/ingest`，按 `data_type` 字段分发

**Why**: 单一端点便于中间件保护、限流、审计；`data_type` 字段驱动 UPSERT 路径。

**Request body**:
```json
{
  "data_type": "etf_quote | etf_fundamentals | etf_holdings | etf_sector_weights | etf_performance | etf_equity_holdings | etf_esg | etf_news",
  "batch_id": "2026-06-29T03:14:00Z-etf_quote",
  "records": [ ... per-type records ... ]
}
```

**Response (success)**:
```json
{ "accepted": 5, "rejected": 0, "batch_id": "..." }
```

**Response (partial success, per-record validation failure)**:
```json
{ "accepted": 4, "rejected": 1, "batch_id": "...", "errors": [{"index": 2, "error": "..."}] }
```

**Response codes**:
- `200 OK` — 全成功
- `207 Multi-Status` — 部分记录成功（仍写 accepted/rejected 计数）
- `400 Bad Request` — payload schema 不匹配 / 缺字段 / `data_type` 未知
- `401 Unauthorized` — HMAC 验签失败 / 时间戳窗口外
- `429 Too Many Requests` — IP 限流
- `500 Internal Server Error` — 远端异常

### 5. Read API：覆盖 8 种 data type，全部 GET，路径前缀 `/api/etf/`

| Path | Returns |
|---|---|
| `GET /api/etf/quote/{symbol}?limit=480` | 最新 N 条 quote（默认 480 = 2 个交易日 / 5 min 粒度） |
| `GET /api/etf/fundamentals/{symbol}` | 最新一条 fundamentals |
| `GET /api/etf/holdings/{symbol}` | 最新 Top10 持仓 |
| `GET /api/etf/sector-weights/{symbol}` | 最新行业权重 |
| `GET /api/etf/equity-holdings/{symbol}` | 最新组合 PE/PB/PS |
| `GET /api/etf/performance/{symbol}` | 最新多周期回报 |
| `GET /api/etf/esg/{symbol}` | 最新 ESG |
| `GET /api/etf/news/{symbol}?page=1&page_size=20` | 分页新闻 |
| `GET /api/etf/symbols` | 所有已收录的 ETF 列表（去重 symbol） |

**Why GET + 路径参数**: 简单、可缓存（CDN / nginx）；与现有 `/api/stock/{symbol}` 风格一致。

### 6. 限流：IP 滑动窗口（内存 + 周期性落 sqlite 防重启丢失）

**Algorithm**: Sliding window log（精确但内存大）或 sliding window counter（近似但省内存）。选 counter。

**Key**: `source_ip`（从 `X-Forwarded-For` 第一段取，国内机前置 nginx 透传；否则用 socket remote_addr）。

**Default**: 50000 req/天/IP。**能容纳 local 端 5min × 288 ticks × 20 ETFs / 8 types = 每天约 1440 次/数据类，远低于上限**。

**Why include `X-Forwarded-For` parsing**: 国内机前置 nginx（参考 `frontend/HTTPS_NGINX.md`），FastAPI 自身只能看到 `127.0.0.1`。需要解析 header 拿真实 client IP。

**Storage**: 内存 dict `{ip: {window_start_ts, count}}`，每 60s 落一次 sqlite（`rate_limit_state` 表），重启时回填。

### 7. 错误处理

| 错误 | 处理 |
|---|---|
| HMAC 验签失败 | 401，**不**写 ingest_log（避免日志污染） |
| Timestamp 窗口外 | 401，**不**写 ingest_log |
| `data_type` 未知 | 400，写 ingest_log（schema 错是有用的诊断信息） |
| 单条 record 字段错 | 跳过该条，其它条继续；返回 207 |
| 全 batch 失败 | 400，写 ingest_log |
| DB UPSERT 异常 | 500，写 ingest_log，记录 payload 摘要（不存全量避免日志爆炸） |
| IP 限流触发 | 429，写 ingest_log（用于识别异常 client） |

### 8. 部署

- 与现有 backend 共进程（FastAPI 单 app，注册 router 即可）
- 启动时执行 `etf_schema.sql`（幂等 CREATE IF NOT EXISTS）
- 配置文件：`backend/.env.example` 增加新键（**不破坏**现有项）
- HTTPS 由前置 nginx 处理（`frontend/HTTPS_NGINX.md` 已说明）

## Risks / Trade-offs

- **[R1] ingest 端点暴露公网 → 被嗅探 / 暴力破解**
  - Mitigation: HMAC 中间件严守；timestamp 窗口 5min；限流 50000/天/IP；不返回详细错误（避免 oracle）
- **[R2] secret 泄露 = 系统沦陷**
  - Mitigation: 32+ 字节随机 + 不入 git + 定期轮换（运维侧，不在本 change）
- **[R3] payload schema 漂移**
  - Mitigation: Pydantic 严格校验；4xx 让 local 端落死信 + 告警
- **[R4] local 端断网 6h+ 后批量补发 → 突发流量**
  - Mitigation: 每批 500 records 上限；限流 50000/天远大于实际频率；UPSERT 幂等
- **[R5] 内存限流 dict 在大流量 / 攻击时膨胀**
  - Mitigation: counter 算法（O(1) per IP）；定期落 sqlite；攻击者打到限流上限后无新写入
- **[R6] etf_remote.db 单文件无 HA**
  - Mitigation: 接受（用户明确说单点）；用现有的 `.backup` 工具每日 cron 备份
- **[R7] 与 `etf-fetcher-pusher` 的契约漂移**
  - Mitigation: 本 change 的 Pydantic schema 与 `etf-pusher` spec 的 payload schema 字段名 / 类型**逐字段一致**；两端都用 schema 作为 single source of truth（两边各自维护 pydantic，但作为 spec 锁定契约）

## Migration Plan

- **首次部署**：
  1. `git pull` 当前分支
  2. `cd backend && uv sync`（无新依赖）
  3. 在 `backend/.env` 增加 `ETF_PIPELINE_SECRET`（与国外机一致）、`INGEST_MAX_REQUESTS_PER_DAY=50000`、`REMOTE_DB_PATH=./data/etf_remote.db`
  4. 重启 backend
  5. backend 启动时执行 `etf_schema.sql`，创建表
  6. 国外机开始推送 → 观察 `etf_ingest_log` 表 + read API
- **升级**：滚动重启（FastAPI 单进程，简单）；schema 变更走 idempotent migration
- **回滚**：删除新增的 router 注册即可，旧代码路径不受影响

## Open Questions

- 是否要给 read API 加 token 鉴权（CORS 已能挡住浏览器跨域，但命令行 / 内部 service 仍能直调）？
  - **决定**：本 change 不加（仅内网用，CORS 足够）；未来需要时再单独 change
- `etf_remote.db` 是否需要每日冷备份？
  - **决定**：现有 `watchlist.db.backup.*` 模式可复用，本 change 不实现，文档化建议
- 是否需要 systemd `/health` 端点返回 ingest 状态（最近一次成功时间）？
  - **决定**：复用现有 `/health`，加几个 ETF 相关字段（`etf_last_ingest_at`）
