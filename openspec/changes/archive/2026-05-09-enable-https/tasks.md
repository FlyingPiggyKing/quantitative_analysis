## 1. Documentation and Configuration

- [x] 1.1 Update `frontend/.env.example` with `NEXT_PUBLIC_API_URL=https://your-api-domain.com` example
- [x] 1.2 Add HTTPS deployment instructions to `frontend/HTTPS_NGINX.md`
- [x] 1.3 Document reverse proxy configuration (nginx) in frontend/HTTPS_NGINX.md

## 2. Backend Security (Optional but Recommended)

- [x] 2.1 Update backend startup to bind to `127.0.0.1:8000` instead of `0.0.0.0:8000` for production
- [x] 2.2 Add comment in backend README about HTTPS reverse proxy requirement

## 3. Verification

- [ ] 3.1 Verify frontend makes HTTPS API calls in production
- [ ] 3.2 Confirm no Mixed Content errors in browser console
