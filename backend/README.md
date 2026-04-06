# Backend

## 使用 uv 管理

### 安装依赖
```bash
cd backend
uv sync
```

### 运行开发服务器
```bash
uv run uvicorn main:app --reload --port 8000
```

### 安装新依赖
```bash
uv add <package>
uv add --dev <package>
```

### 查看已安装的包
```bash
uv pip list
```
