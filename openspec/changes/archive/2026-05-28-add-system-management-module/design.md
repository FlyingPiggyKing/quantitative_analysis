## Context

The system has a role-based permission system where `admin` role has `system_statistics` permission. The homepage uses `ModuleTabs` component with two modules: "我的自选" (watchlist) and "投资分析" (analysis). Users with `system_statistics` permission need a dedicated admin module to view system statistics.

## Goals / Non-Goals

**Goals:**
- Add "系统管理" (System Administration) tab visible only to users with `system_statistics` permission
- Display stock statistics: list all unique stocks from `user_watchlist` across all users, with market and user count
- Display user statistics: list all registered users with count

**Non-Goals:**
- Not implementing user management (create/edit/delete users)
- Not implementing role assignment in this module
- Not adding new permissions or modifying the RBAC system

## Decisions

### 1. New API Endpoint Structure
Create a new backend API route `/api/admin/stats` that returns:
- `watchlist_stocks`: Array of stocks from `user_watchlist` table, deduplicated by symbol, with market and user_count
- `watchlist_count`: Total number of unique stocks
- `users`: Array of registered users
- `user_count`: Total number of registered users

**Rationale**: Keeps admin-related functionality under `/api/admin/` prefix for clear separation.

### 2. Frontend Component Structure
- Modify `ModuleTabs` to accept an optional third tab content for admin
- Create `SystemAdminPanel` component that fetches and displays admin statistics
- Conditionally render the admin tab based on user's `system_statistics` permission

**Rationale**: Follows existing patterns in the codebase where permissions gate visibility.

### 3. Permission Check
Use existing `RoleService.user_has_permission(user_id, 'system_statistics')` method.
The frontend already has `useAuth()` hook that provides user info.

**Rationale**: Reuses existing infrastructure rather than creating new permission checks.

## Risks / Trade-offs

- [Risk] User list exposure → [Mitigation] Only users with `system_statistics` permission can access this endpoint. The API should also validate the session token.
- [Risk] Performance with large user_watchlist → [Mitigation] User watchlist is expected to be small (<10000 entries). If needed, add pagination later.
