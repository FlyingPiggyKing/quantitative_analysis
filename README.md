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
| `GET /health` | 健康检查 |
