## Why

本项目是 monorepo，会分别部署在国内、国外两台服务器。国内服务器运行 `backend/` 和 `frontend/`，访问外部数据源（特别是 yfinance / yahooquery）受限。国外服务器访问外部数据源通畅，但本机不承载 `backend/` 也不直接服务前端。

要解决「国内服务器上的前端能稳定地看到美股 ETF 数据」这一需求，需要在国外服务器上运行一个**只读**的数据采集与推送模块，定时从 yahooquery 拉取数据、落本地 sqlite（用于重试和审计）、再通过 HMAC 鉴权的 HTTP 推送到国内 ingest 端点。本 change 覆盖「国外机」这一侧；国内侧的 ingest 接收与持久化由平行 change `etf-remote-data-persist` 负责。

## What Changes

- **新增** `remote_data/` 目录，作为国外机运行时**唯一**的代码入口（不 import 任何 `backend/` 代码）
- **新增** `remote_data/main.py` 入口；用 `python -m remote_data` 启动
- **新增** `remote_data/fetcher/` 子包，封装 yahooquery 的数据获取：
  - `etf_quote`（实时价 / 盘前盘后价 / 成交量）
  - `etf_fundamentals`（当前 PE / PB / 股息率）
  - `etf_holdings`（Top10 持仓）
  - `etf_sector_weightings`（行业权重）
  - `etf_performance`（多周期回报 ytd / 1y / 3y / 5y / 10y）
  - `etf_equity_holdings`（组合 PE / PB / PS）
  - `etf_esg`（ESG 评分）
  - `etf_news`（新闻）
- **新增** `remote_data/store/` 子包：本地 sqlite（默认 `data/etf_local.db`），每张业务表带 `pushed_at` 字段，作为推送重试游标
- **新增** `remote_data/pusher/` 子包：HMAC-SHA256 + timestamp 窗口鉴权的 HTTP 客户端；指数退避重试；payload schema 校验
- **新增** `remote_data/scheduler/` 子包：基于 APScheduler 的 cron 调度，按不同数据类配置 cadence
- **新增** `remote_data/config.py`：从 `.env` 读取所有配置（`DEPLOY_ROLE=LOCAL`、`REMOTE_INGEST_URL`、`ETF_PIPELINE_SECRET`、symbol 白名单等）
- **新增** `remote_data/pyproject.toml`：只依赖 `yahooquery` / `httpx` / `pydantic` / `apscheduler` / `python-dotenv`
- **新增** `remote_data/.env.example`：环境变量样例
- **新增** `remote_data/README.md`：在海外机器上的部署/运行说明
- **新增** 一次性 backfill 任务：拉取所有 20 只 ETF 的当前 PE/PB/股息率 + 2 年内能拿到的估值历史（实测 yahooquery 对个股 `valuation_measures` 约 2 年，ETF 无历史，仅当 PE 代理用——具体策略见 `etf-remote-data-persist` change 的 specs）
- **新增** `remote_data/scripts/init_local_db.py`：独立 Python 初始化脚本，调用 `local_db.init()`，供运维 / 灾备 / smoke test 使用；与 `main.py` 启动钩子共享同一份 schema 应用代码
- **新增** `scripts/start-etf-fetcher.sh`：Shell 启动脚本，先跑 `init_local_db.py` 再起 `python -m remote_data`；与 systemd 路径并存，由 `main.py` 启动钩子兜底

## Capabilities

### New Capabilities

- `etf-fetcher`: 从 yahooquery 拉取各类 ETF 数据的 fetcher 子模块契约（每个 data type 一个函数，返回标准化 record 列表）
- `etf-local-store`: 本地 sqlite schema 与「pushed_at 重试游标」语义
- `etf-pusher`: HMAC-SHA256 + timestamp 窗口鉴权的推送客户端契约（payload schema、签名规则、重试策略）
- `etf-scheduler`: 不同数据类的 cadence 配置与调度入口
- `etf-config`: `.env` 配置项清单与默认值

### Modified Capabilities

无。本 change 不修改任何已有 `backend/` 或 `frontend/` 代码；国外机运行时不依赖国内机任何代码路径。

## Impact

- **新增代码区**：`remote_data/`（独立 pyproject、独立 venv）
- **新增启动脚本**：
  - `remote_data/scripts/init_local_db.py`（独立 Python 初始化入口）
  - `scripts/start-etf-fetcher.sh`（Shell 启动入口；与 systemd 路径并存，由 main.py 启动钩子兜底）
- **新增配置**：根目录增加 `remote_data/.env.example`（**不入 git 真值**，只入样例）
- **运行模型变更**：国外机从「无 backend 进程」变为「只有 `remote_data` 进程」
- **依赖变更**：国外机新增 `yahooquery` / `httpx` / `pydantic` / `apscheduler`
- **风险**：
  - 跨海网络不稳定 → pusher 必须有重试 + 本地积压能力（设计已覆盖）
  - yahooquery 限流 → 必须加 `YAHOOQUERY_MAX_RETRIES` 和 cadence 留余量
  - HMAC secret 分发 → 需手动在两台机器 `.env` 写入，**不进 git**
- **配套 change（不属本 change 范围）**：`etf-remote-data-persist` 定义了接收端契约，本 change 严格遵守其 ingest 端点路径、header 名称、payload schema
