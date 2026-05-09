# HTTPS Deployment with Nginx (Same Machine)

## Problem

When the frontend is served over HTTPS, browsers block HTTP API requests (Mixed Content error).

```
Mixed Content: The page at 'https://51stock.com.cn/' was loaded over HTTPS,
but requested an insecure resource 'http://8.153.90.28:8000/api/...'
```

## Solution (Same Machine Deployment)

Deploy both frontend and backend on the same machine with Nginx as reverse proxy.

### Architecture

```
Browser (HTTPS) ──► Nginx (:443) ──► Next.js (localhost:3000)
                            │
                            └──► Backend API (localhost:8000)
```

### 1. Set Production API URL

```bash
# frontend/.env.production
NEXT_PUBLIC_API_URL=https://51stock.com.cn
```

### 2. Backend Configuration

Start backend bound to localhost only:

```bash
# Start backend on localhost only (not exposed to internet)
uv run uvicorn backend.api:app --host 127.0.0.1 --port 8000
```

### 3. Nginx Configuration

```nginx
# /etc/nginx/sites-available/51stock.com.cn

# Frontend (Next.js)
server {
    listen 443 ssl;
    server_name 51stock.com.cn;

    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;

    location / {
        proxy_pass http://127.0.0.1:3000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}

# Backend API
server {
    listen 443 ssl;
    server_name api.51stock.com.cn;

    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

**Note**: Use the same SSL certificate for both `51stock.com.cn` and `api.51stock.com.cn` (or a wildcard cert).

### 4. Enable the site

```bash
sudo ln -s /etc/nginx/sites-available/51stock.com.cn /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

## Key Points

1. **Backend binds to 127.0.0.1 only** - not directly accessible from internet
2. **Nginx handles HTTPS** - certificates managed at proxy level
3. **Browser calls HTTPS API** - no Mixed Content error
4. **Both services on same machine** - no network complexity

## Verification

1. Open browser DevTools → Network tab
2. Check API requests go to `https://api.51stock.com.cn/...`
3. No Mixed Content errors in Console
