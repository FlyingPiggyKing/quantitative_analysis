## Why

Currently the stock analysis application has no user authentication. All users share a single global watchlist, making it impossible to provide personalized stock tracking. User login/logout functionality is needed to enable per-user stock watchlists and secure access to the application.

## What Changes

- Add user registration endpoint with username/password
- Add user login endpoint returning a session token (JWT)
- Add user logout endpoint to invalidate tokens
- Add login page with sign-up and login forms
- Add image captcha verification on login page to prevent robotic attacks
- Modify watchlist API to filter stocks by logged-in user
- Create default user account `jack.zhu` with password `imabigboy820518`
- Assign existing watchlist stocks to the default user `jack.zhu`

## Capabilities

### New Capabilities

- `user-auth`: User authentication covering registration, login, logout with JWT tokens and password hashing
- `captcha`: Image captcha generation and verification to prevent robotic login attempts
- `user-watchlist`: Per-user watchlist isolation ensuring users only see their own stocks

### Modified Capabilities

- `stock-query`: No requirement changes — only implementation modifications to support authenticated endpoints
- `stock-search`: No requirement changes — only implementation modifications to support authenticated endpoints

## Impact

- **Backend**: New `auth` API module with JWT-based authentication, new `captcha` module for image generation
- **Database**: New `users` table, new `user_watchlist` table replacing global watchlist, new `captcha` table
- **Frontend**: New login page, auth context provider, protected routes, API interceptor for token injection
- **Dependencies**: Add `pyjwt`, `bcrypt`/`passlib` Python packages; no new frontend dependencies
