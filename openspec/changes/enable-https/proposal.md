## Why

When HTTPS is enabled on the frontend, browsers block insecure (HTTP) API requests due to Mixed Content policy. The error "Mixed Content: The page at 'https://51stock.com.cn/' was loaded over HTTPS, but requested an insecure resource 'http://8.153.90.28:8000/'" indicates that API calls are being made over HTTP while the page is served over HTTPS.

## What Changes

- Configure frontend to use HTTPS API URL when deployed
- Ensure `NEXT_PUBLIC_API_URL` is properly set for production
- Document HTTPS configuration requirements for deployment
- Optionally enable HTTPS directly on uvicorn for backend

## Capabilities

### New Capabilities

- `https-deployment-config`: Document and configure HTTPS deployment settings for both frontend and backend

### Modified Capabilities

- `frontend-api-url`: Update the API URL configuration to support HTTPS in production

## Impact

- **Files affected**: `frontend/src/services/stock.ts`, `frontend/src/services/auth.tsx`, potentially `backend/main.py` or deployment configs
- **Environment variables**: `NEXT_PUBLIC_API_URL` must be set to HTTPS URL in production
- **Deployment**: Backend API must be accessible via HTTPS or behind a reverse proxy
