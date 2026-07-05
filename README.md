# Stock Analyzer

股票K线图和技术指标分析工具。

## 技术栈

- **后端**: FastAPI + Tushare Pro + Futu API
- **前端**: Next.js + TradingView lightweight-charts
- **图表**: K线图、MACD、RSI、移动平均线

## 快速启动

### 后端

```bash
cd backend
uv sync
uv run uvicorn main:app --reload --port 8000
```

访问 http://localhost:8000/docs 查看 API 文档。

### 前端

```bash
cd frontend
npm install
npm run dev
```

访问 http://localhost:3000

## 环境配置

复制 `backend/.env.example` 为 `backend/.env`，配置以下变量：

| 变量 | 说明 |
|------|------|
| `TUSHARE_TOKEN` | Tushare Pro API Token (https://tushare.pro) |
| `FUTU_OPEND_HOST` | Futu OpenD 地址 (默认 127.0.0.1) |
| `FUTU_OPEND_PORT` | Futu OpenD 端口 (默认 11111) |

## 部署

参见 [frontend/HTTPS_NGINX.md](frontend/HTTPS_NGINX.md)

### 本地开发

- 后端: `uv run uvicorn main:app --reload --port 8000` → API: http://localhost:8000
- 前端: `npm run dev` → http://localhost:3000

### 生产环境

1. 构建前端: `cd frontend && npm run build && npm start`
2. 启动后端: `uv run uvicorn backend.api:app --host 127.0.0.1 --port 8000`
3. Nginx 反向代理处理 HTTPS，参见 frontend/HTTPS_NGINX.md

## API 端点

| 端点 | 说明 |
|------|------|
| `GET /api/stock/{symbol}` | 股票基本信息 |
| `GET /api/stock/{symbol}/kline?days=100` | K 线数据 |
| `GET /api/stock/{symbol}/realtime` | 实时行情 |
| `GET /api/stock/{symbol}/indicators?days=100` | 技术指标 |
| `GET /api/stock/main-business?symbol=600519&type=P` | A 股主营业务构成（Tushare fina_mainbz；按产品/地区/行业，含毛利率、利润占比、跨期对比） |
| `GET /api/stock/main-business-futu?symbol=00700` | 港股 / 美股主营业务构成（Futu get_financials_revenue_breakdown；按产品/地区/行业/业务，仅收入与占比） |
| `GET /api/stock/main-business-futu/history?symbol=00700` | 港股 / 美股最近 4 年按产品跨期对比（4 次并行 Futu 调用） |
| `GET /health` | 健康检查 |

## 系统管理面板

拥有 `system_statistics` 权限的账户登录后，首页会出现 **"系统管理"** 标签，包含：

- **趋势分析进度**：查看 / 触发趋势分析任务
- **股票统计**：所有用户自选股的去重统计
- **用户统计**：注册用户列表
- **ETF 数据推送监控**：海外 `remote_data` → 国内 `etf_remote.db` 推送健康度（每张表最近一次推送时间、最新数据日期、行数、状态色）。阈值由 `ETF_PUSH_WARN_HOURS` / `ETF_PUSH_STALE_HOURS` 控制，请求时读取，修改后无需重启。
