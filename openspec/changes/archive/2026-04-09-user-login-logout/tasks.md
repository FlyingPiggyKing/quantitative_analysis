## 1. Database Migration

- [x] 1.1 Create database migration script to add `users` table with username and password_hash
- [x] 1.2 Create database migration script to add `user_watchlist` table with user_id foreign key
- [x] 1.3 Create database migration script to add `captchas` table for CAPTCHA storage
- [x] 1.4 Create database migration script to add `user_sessions` table for token tracking
- [x] 1.5 Migrate existing watchlist entries to user `jack.zhu` (user_id=1)
- [x] 1.6 Create default user `jack.zhu` with password `imabigboy820518`

## 2. Backend Auth API (Python/FastAPI)

- [x] 2.1 Add `pyjwt` and `passlib[bcrypt]` dependencies to pyproject.toml
- [x] 2.2 Create `backend/api/auth.py` with registration endpoint POST /api/auth/register
- [x] 2.3 Create `backend/api/auth.py` with login endpoint POST /api/auth/login
- [x] 2.4 Create `backend/api/auth.py` with logout endpoint POST /api/auth/logout
- [x] 2.5 Create `backend/api/captcha.py` with GET /api/captcha endpoint
- [x] 2.6 Create `backend/services/auth_service.py` for JWT token generation and validation
- [x] 2.7 Create `backend/services/captcha_service.py` for CAPTCHA generation and verification
- [x] 2.8 Create `backend/services/user_service.py` for user CRUD operations
- [x] 2.9 Add authentication dependency to watchlist endpoints

## 3. Backend Watchlist Updates

- [x] 3.1 Update `backend/services/watchlist_service.py` to use `user_watchlist` table
- [x] 3.2 Update `backend/api/watchlist.py` to filter by authenticated user_id
- [x] 3.3 Update `backend/main.py` to include new auth router and captcha router

## 4. Frontend Login Page

- [x] 4.1 Create `frontend/src/app/login/page.tsx` with login form
- [x] 4.2 Add sign-up form toggle to login page
- [x] 4.3 Integrate CAPTCHA image display in login page
- [x] 4.4 Add form validation for login/signup forms
- [x] 4.5 Handle successful login redirect to home page

## 5. Frontend Auth Context & API

- [x] 5.1 Create `frontend/src/contexts/AuthContext.tsx` for auth state management
- [x] 5.2 Create `frontend/src/services/auth.ts` for auth API calls
- [x] 5.3 Add token to API requests via fetch interceptor or helper
- [x] 5.4 Create logout function that clears token and redirects to login

## 6. Frontend Route Protection

- [x] 6.1 Update `frontend/src/app/layout.tsx` to wrap with AuthContext provider
- [x] 6.2 Protect home page `/` to redirect unauthenticated users to /login
- [x] 6.3 Protect stock detail page `/stock/[symbol]` to redirect unauthenticated users

## 7. Testing & Verification

- [x] 7.1 Test user registration with new username
- [x] 7.2 Test user login with default user `jack.zhu` / `imabigboy820518`
- [x] 7.3 Test CAPTCHA verification on login
- [x] 7.4 Test that user can only see their own watchlist stocks
- [x] 7.5 Test logout clears session
- [x] 7.6 Verify all existing watchlist stocks are accessible by `jack.zhu`
