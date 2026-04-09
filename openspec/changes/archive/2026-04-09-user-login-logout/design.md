## Context

The stock analysis application currently has no authentication layer. All users share a single global watchlist stored in `watchlist.db`. The application serves a single Next.js frontend and FastAPI backend.

**Current State:**
- Backend: FastAPI with SQLite database (`watchlist.db`)
- Frontend: Next.js with React, pages at `/` (home) and `/stock/[symbol]` (stock detail)
- No user sessions, no access control

**Stakeholders:** Single user (jack.zhu) initially, with capability for future multi-user access.

## Goals / Non-Goals

**Goals:**
- Implement user registration and login with JWT tokens
- Add image captcha on login page to prevent automated attacks
- Isolate watchlists per user so each sees only their own stocks
- Create default user `jack.zhu` with password `imabigboy820518`
- Migrate existing watchlist entries to the default user

**Non-Goals:**
- OAuth/social login integration
- Password reset functionality
- User profile management
- Admin panel or user management UI
- Role-based access control beyond owner isolation

## Decisions

### Decision 1: JWT over Session Cookies

**Choice:** Use JWT (JSON Web Tokens) for authentication.

**Rationale:**
- Stateless - simplifies backend scaling
- Frontend stores token in localStorage and sends in `Authorization: Bearer <token>` header
- No server-side session storage needed

**Alternative considered:** HTTP-only session cookies
- Pros: More secure against XSS, automatic on browser close
- Cons: Requires server-side session store or database-backed sessions; more complex for this single-server setup

### Decision 2: Password Hashing with bcrypt

**Choice:** Use `bcrypt` via `passlib` library.

**Rationale:**
- Industry standard for password hashing with salt
- Configurable work factor for future hardening
- Python ecosystem standard via `passlib`

### Decision 3: Image Captcha (Simple CAPTCHA)

**Choice:** Server-side CAPTCHA generation with 6-character random string, stored in database with expiry.

**Implementation:**
- Generate random string (uppercase letters + digits, avoiding confusing chars like 0/O, 1/l)
- Store in SQLite `captchas` table with `created_at` timestamp
- Return base64-encoded PNG image to client
- Verify CAPTCHA on login form submission

**Alternative considered:** Google reCAPTCHA
- Pros: More robust, well-tested
- Cons: Requires external service registration, API keys, network dependency

### Decision 4: Database Schema Changes

**Changes:**
1. Create `users` table with `id`, `username`, `password_hash`, `created_at`
2. Rename/modify `watchlist` table to `user_watchlist` with `user_id` foreign key
3. Create `captchas` table with `id`, `code`, `created_at`
4. Create `user_sessions` table with `id`, `user_id`, `token_hash`, `created_at`, `expires_at`

**Migration:** Existing watchlist data will be preserved and assigned to user `jack.zhu` (id=1).

### Decision 5: Frontend Auth Flow

**Flow:**
1. Unauthenticated users accessing protected routes redirect to `/login`
2. Login page shows login form and sign-up form (toggleable)
3. CAPTCHA image displayed above form fields
4. On successful login, JWT stored in localStorage, redirect to home
5. API calls include `Authorization: Bearer <token>` header
6. Logout clears localStorage and redirects to login

## Risks / Trade-offs

**[Risk] XSS attacks on JWT storage** → **Mitigation:** In production, consider HTTP-only cookies. For now, localStorage is acceptable for this internal tool.

**[Risk] Weak default user password** → **Mitigation:** The default password `imabigboy820518` should be changed after first login. Consider adding a "change password on first login" flag.

**[Risk] CAPTCHA brute force** → **Mitigation:** CAPTCHA codes expire after 5 minutes; rate limit login attempts (implement later if needed).

**[Risk] No HTTPS in development** → **Mitigation:** JWT tokens are vulnerable to interception on HTTP. Force HTTPS in production; development uses localhost.

## Migration Plan

1. **Backup existing database** (`watchlist.db`)
2. **Create new database schema** with migration script
3. **Create default user `jack.zhu`** with hashed password
4. **Migrate existing watchlist entries** to user `jack.zhu` (user_id=1)
5. **Deploy backend** with new auth endpoints
6. **Deploy frontend** with login page
7. **Verify login** with default user credentials

**Rollback:** Restore `watchlist.db` from backup; revert API and frontend changes.

## Open Questions

1. Should CAPTCHA be required for sign-up as well as login?
2. Should we implement JWT refresh tokens for extended sessions?
3. Should we add a "remember me" option to extend token expiry?
