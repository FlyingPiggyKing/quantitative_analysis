## Why

本项目是 monorepo，分别部署在国内、国外两台服务器。国外服务器（由平行 change `etf-fetcher-pusher` 覆盖）定时从 yahooquery 拉取 ~20 只美股 ETF 数据并通过 HMAC 鉴权的 HTTP POST 推送到国内服务器。本 change 解决「国内服务器**接收、验证、落地、对外可读**」这一侧的需求：

1. 提供一个 ingest 端点，验证 HMAC + timestamp 窗口、Pydantic 校验 payload、UPSERT 到本地 sqlite
2. 给前端 / 内部其它 service 提供稳定的读 API
3. 用 IP 速率限制防止误用和暴力探测

数据来自平行 change 的 local pusher；本 change 严格遵守其在 `etf-pusher` spec 中定义的端点、header、payload 契约。

## What Changes

- **新增** `backend/api/etf_ingest.py`：POST `/api/etf/ingest` 端点，包含 HMAC 验签 + timestamp 窗口中间件
- **新增** `backend/api/etf_read.py`：GET 系列读 API（`/api/etf/...`）
- **新增** `backend/services/etf_service.py`：封装对 `etf_remote.db` 的读写
- **新增** `backend/services/etf_ingest_service.py`：dispatch 接收到的 payload 到对应 data_type 的 UPSERT
- **新增** `backend/schemas/etf.py`：与 `etf-fetcher-pusher` 的 `etf-pusher` spec **完全一致**的 Pydantic 模型
- **新增** `backend/migrations/etf_schema.sql`：新 SQLite 表 DDL
- **新增** sqlite 文件 `data/etf_remote.db`（运行时创建，不入 git）
- **新增** `backend/middleware/hmac_auth.py`：FastAPI 中间件，做 HMAC 验签 + 时间戳窗口
- **新增** `backend/middleware/rate_limit.py`：基于 IP 的滑动窗口限流
- **新增** 配置项注入到现有 `.env.example` / `.env`（`ETF_PIPELINE_SECRET`、`INGEST_MAX_REQUESTS_PER_DAY`、`REMOTE_DB_PATH` 等）
- **新增** `etf_ingest_log` 审计表：每次 ingest 调用的源 IP、时间、batch_id、accepted/rejected 计数

## Capabilities

### New Capabilities

- `etf-ingest-auth`: HMAC-SHA256 + timestamp 窗口验签中间件（含 401 行为、白名单路径）
- `etf-ingest-endpoint`: POST `/api/etf/ingest` 端点（payload 校验、按 `data_type` 分发、审计日志、4xx/5xx 错误模型）
- `etf-persistence`: `etf_remote.db` 的表结构与 UPSERT 语义（按 `(symbol, as_of/ts)` 唯一键）
- `etf-read-api`: 前端调用的读端点（quote、fundamentals、holdings、sector、performance、equity_holdings、esg、news）
- `etf-rate-limit`: 简单 IP 滑动窗口限流（默认 50000 req/天）
- `etf-config`: 后端侧新增的 env 变量清单

### Modified Capabilities

无。本 change 仅**新增**后端文件，**不修改**任何现有 endpoint 的行为（`/api/stock/*`、`/api/etf/ingest` 是新路径，不冲突）。

## Impact

- **新增代码区**：
  - `backend/api/etf_ingest.py`、`backend/api/etf_read.py`
  - `backend/services/etf_service.py`、`backend/services/etf_ingest_service.py`
  - `backend/schemas/etf.py`
  - `backend/middleware/hmac_auth.py`、`backend/middleware/rate_limit.py`
  - `backend/migrations/etf_schema.sql`
- **新增数据库**：`data/etf_remote.db`（独立于 `watchlist.db`）
- **新增配置**：`backend/.env` 增加 `ETF_PIPELINE_SECRET`、`INGEST_MAX_REQUESTS_PER_DAY`、`REMOTE_DB_PATH`、`TIME_WINDOW_SECONDS`
- **依赖变更**：FastAPI 已存在，无新依赖
- **风险**：
  - ingest 端点暴露在公网 → 必须**只**接受带正确 HMAC 的请求（中间件严格）
  - 速率限制误判 → 用宽松的 50000/天默认值，给真实流量充足余量
  - payload schema 漂移 → 强制 Pydantic 校验，校验失败 → 4xx（让 local 端落死信）
- **配套 change（不属本 change 范围）**：`etf-fetcher-pusher` 定义了发送端契约，本 change 严格遵守其 ingest 端点路径、header 名称、payload schema
- **后续 change（不属本 change 范围）**：ETF 前端页面、新增 alert/telegram 通道
