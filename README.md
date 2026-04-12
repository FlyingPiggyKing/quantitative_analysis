# Stock Analyzer

股票K线图和技术指标分析工具。

## 技术栈

- **后端**: FastAPI + Tushare Pro
- **前端**: Next.js + TradingView lightweight-charts
- **图表**: K线图、MACD、RSI、移动平均线

## 环境配置

### 1. 配置 API Keys

复制 `backend/.env.example` 为 `backend/.env` 并配置以下变量：

| 变量 | 说明 | 获取方式 |
|------|------|----------|
| `TUSHARE_TOKEN` | Tushare Pro API Token | https://tushare.pro |
| `MINIMAX_API_KEY` | MiniMax API Key | 用于AI股票分析 |
| `TAVILY_API_KEY` | Tavily API Key | https://tavily.com - 用于搜索股票新闻 |

### 2. 配置 Tushare Token

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

## 服务器迁移/部署检查清单

迁移到新服务器时，按以下步骤检查：

### 1. 端口开放
确保防火墙打开以下端口：
- **3000** - 前端
- **8000** - 后端 API

### 2. 数据库初始化

`watchlist.db` 需要创建以下表才能正常运行：

```bash
sqlite3 backend/watchlist.db "
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS captchas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS user_sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    token_jti TEXT NOT NULL UNIQUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP NOT NULL
);

CREATE TABLE IF NOT EXISTS user_watchlist (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    symbol TEXT NOT NULL,
    name TEXT NOT NULL,
    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id),
    UNIQUE(user_id, symbol)
);
"
```

### 3. 前端环境变量

如果前端和后端不在同一服务器，或使用非 localhost 访问，需创建 `frontend/.env.production`：

```bash
echo "NEXT_PUBLIC_API_URL=http://你的服务器IP:8000" > frontend/.env.production
```

然后重新构建：
```bash
cd frontend
npm run build
npm start
```

### 4. 数据库文件

- `backend/watchlist.db` - 用户、验证码、会话数据
- `backend/trend_predictions.db` - 股票趋势预测数据（可选，如不存在会自动创建）

### 5. 依赖安装

```bash
cd backend
uv sync
```

### 6. 启动服务

方式一：使用快捷脚本（推荐）
```bash
./start.sh
```

方式二：手动启动
```bash
# 后端
cd backend && nohup ./backend/.venv/bin/python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 &

# 前端
cd frontend && npm run build && nohup npm start &
```

### 7. 常见问题

**CAPTCHA CORS 错误**：检查前端 `.env.production` 是否设置正确的 `NEXT_PUBLIC_API_URL`

**sqlite3.OperationalError: no such table**：运行上面的数据库初始化 SQL

**net::ERR_CONNECTION_TIMED_OUT**：检查防火墙是否打开 8000 端口

## 示例股票代码

| 代码 | 名称 |
|------|------|
| 000001 | 平安银行 |
| 600000 | 浦发银行 |
| 300059 | 东方财富 |
| 300750 | 宁德时代 |
| 510300 | 300ETF |
