## Context

The application consists of:
- **Frontend**: Next.js app served over HTTPS (https://51stock.com.cn/)
- **Backend**: FastAPI/uvicorn running on port 8000, currently HTTP only

When frontend makes API calls to `http://8.153.90.28:8000/`, browsers block these as Mixed Content since the parent page is HTTPS.

**Current API URL setup in frontend:**
```typescript
const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
```

## Goals / Non-Goals

**Goals:**
- Fix Mixed Content error by ensuring API calls use HTTPS
- Document correct environment configuration for HTTPS deployment

**Non-Goals:**
- Implementing backend HTTPS directly on uvicorn (use reverse proxy instead)
- Setting up TLS certificates (handled by hosting platform or reverse proxy)

## Decisions

### Decision 1: Use reverse proxy for HTTPS termination

**Chosen approach:** Deploy backend behind a reverse proxy (nginx/Caddy/cloudflare) that handles HTTPS, and proxy to backend over localhost HTTP.

**Rationale:**
- Backend code doesn't need modification for HTTPS
- Certificates managed by reverse proxy or hosting platform
- Standard production practice
- uvicorn can run on localhost only (127.0.0.1) behind proxy

**Alternatives considered:**
- Enable HTTPS directly in uvicorn: Rejected - requires managing certificates in application code, less secure
- Cloudflare proxy: Works but requires specific hosting setup
- Same-machine Option B (separate ports): Rejected - requires exposing backend directly with valid HTTPS certificate

### Decision 2: Document `NEXT_PUBLIC_API_URL` configuration

**Chosen approach:** Document that production deployments must set `NEXT_PUBLIC_API_URL` to the HTTPS endpoint.

**Rationale:**
- `NEXT_PUBLIC_` variables are exposed to browser (as per Next.js docs)
- Need HTTPS URL for production, localhost HTTP for development

## Risks / Trade-offs

[Risk] Misconfigured API URL → **Mitigation**: Document clearly, use `.env.production` template

[Risk] Backend not accessible from outside → **Mitigation**: Run behind reverse proxy on standard ports (443 for HTTPS)

## Migration Plan

1. Set `NEXT_PUBLIC_API_URL=https://api.51stock.com.cn` in production environment
2. Configure reverse proxy (nginx/Caddy) to:
   - Terminate HTTPS on port 443
   - Proxy to backend at `http://127.0.0.1:8000`
3. Ensure backend binds to localhost only (not exposed directly)
4. Update `.env.example` with production HTTPS URL example

## Open Questions

1. What reverse proxy/hosting platform is being used (nginx, Caddy, cloudflare, etc.)?
2. Should the backend also be modified to bind to localhost only for security?
