# Stock Analyzer

股票K线图和技术指标分析工具。

## 技术栈

- **后端**: FastAPI + Tushare Pro
- **前端**: Next.js + TradingView lightweight-charts
- **图表**: K线图、MACD、RSI、移动平均线

## 环境配置

### 1. 配置 Tushare Token

1. 注册 [Tushare Pro](https://tushare.pro)
2. 登录后在「个人中心」→「API Token」获取 Token
3. 创建 `backend/.env` 文件：

```bash
cd backend
cp .env.example .env
```

4. 编辑 `backend/.env`，填入你的 Token：

```env
TUSHARE_TOKEN=你的Token
```

### 2. 安装依赖

```bash
cd backend
uv sync
```

### 3. 启动后端

**方式一：使用 uv run（推荐）**

```bash
cd backend
uv run uvicorn main:app --reload --port 8000
```

`python-dotenv` 会自动读取 `.env` 文件中的环境变量。

**方式二：使用快捷脚本**

```bash
./start-backend.sh
```

**方式三：手动设置环境变量**

```bash
export TUSHARE_TOKEN=你的Token
uv run uvicorn backend.main:app --port 8000
```

后端启动后，访问 http://localhost:8000/docs 查看 API 文档。

### 4. 启动前端

```bash
cd frontend
npm install
npm run dev
```

访问 http://localhost:3000

### 5. 代理设置（如需要）

如果网络无法直接访问 Tushare，需设置代理：

```bash
export https_proxy=http://127.0.0.1:10887
export http_proxy=http://127.0.0.1:10887
```

## 使用

1. 访问 http://localhost:3000
2. 输入股票代码（如 000001、600000、300750）
3. 查看 K 线图和技术指标

## API 端点

| 端点 | 说明 |
|------|------|
| `GET /api/stock/{symbol}` | 股票基本信息 |
| `GET /api/stock/{symbol}/kline?days=100` | K 线数据 |
| `GET /api/stock/{symbol}/realtime` | 实时行情 |
| `GET /api/stock/{symbol}/indicators?days=100` | 技术指标 |
| `GET /health` | 健康检查 |

## 部署

### 构建前端

```bash
cd frontend
npm run build
```

### 启动后端（生产模式）

```bash
cd backend
uv run uvicorn backend.main:app --port 8000
```

访问 http://localhost:8000 查看前端页面。

## 示例股票代码

| 代码 | 名称 |
|------|------|
| 000001 | 平安银行 |
| 600000 | 浦发银行 |
| 300059 | 东方财富 |
| 300750 | 宁德时代 |
| 510300 | 300ETF |
