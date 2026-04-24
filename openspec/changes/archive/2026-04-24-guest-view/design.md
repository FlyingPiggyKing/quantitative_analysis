## Context

Currently, all stock information in the quantitative analysis platform requires user authentication. Users must login/register before they can see any stock data, including the home page stock list, stock search, and stock detail pages. This creates unnecessary friction for first-time visitors.

The system consists of:
- Frontend: Next.js application with stock browsing and analysis features
- Backend: API endpoints for stock data, watchlist management, and trend analysis

## Goals / Non-Goals

**Goals:**
- Allow guest users to view preset stock list on home page without authentication
- Allow guest users to search stocks and view stock details without authentication
- Require authentication for watchlist modification (adding/removing stocks)
- Require authentication for trend analysis features
- Show login/register prompts when guests attempt restricted actions

**Non-Goals:**
- Full public API access - only specified read operations are public
- User registration flow implementation (existing system assumed)
- Modifying existing stock data or quotes APIs

## Decisions

### 1. Public Routes vs Authenticated Routes

**Decision**: Implement route-level access control with different behaviors for public vs authenticated features.

**Rationale**: Clean separation between public content and user-specific features. Frontend routes are divided into:
- Public routes: Home page, stock search, stock detail pages (no auth required)
- Protected routes: Watchlist management, trend analysis trigger (auth required)

**Alternatives considered**:
- Single-page approach with conditional rendering: More complex, harder to maintain
- Server-side rendering based on auth: Over-engineered for this use case

### 2. Preset Stock List Configuration

**Decision**: Define 5 preset stocks in configuration: 601318 (Ping An), 300750 (CATL), 688981 (SMIC), 601899 (Zijin Mining), 600938 (China Oilfield).

**Rationale**: These are well-known stocks across different sectors (finance, EV battery, semiconductors, mining, oil) that showcase platform capabilities.

### 3. Auth-Gated Action Handling

**Decision**: When guest users attempt authenticated actions, show a login/register modal overlay rather than redirecting to a separate page.

**Rationale**: Better UX - user doesn't lose context of what they were trying to do.

**Alternatives considered**:
- Redirect to login page: Loses user context, higher friction
- Disable buttons: Poor discoverability of required auth

## Risks / Trade-offs

- **Risk**: Backend API might have inconsistent auth requirements across endpoints
  - **Mitigation**: Audit all stock-related endpoints and ensure consistent auth enforcement

- **Risk**: Search functionality might expose more data than intended
  - **Mitigation**: Search returns only stock metadata (name, symbol, market), not user-specific data

- **Trade-off**: Guest users can see stock details but cannot save to watchlist
  - **Acceptable**: This is the intended behavior - demonstrates value before requiring signup
