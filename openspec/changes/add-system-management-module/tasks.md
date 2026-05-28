## 1. Backend API

- [x] 1.1 Create `/api/admin/stats` endpoint returning watchlist stocks and user list with counts
- [x] 1.2 Add `system_statistics` permission check to the admin/stats endpoint using `require_permission` decorator
- [x] 1.3 Create endpoint to check if current user has `system_statistics` permission (e.g., `/api/auth/permissions`)

## 2. Frontend Service

- [x] 2.1 Add `checkPermission(permission: string): Promise<boolean>` function to auth service
- [x] 2.2 Add `useSystemAdminAccess()` hook or extend `useAuth()` to expose permission state

## 3. Frontend Components

- [x] 3.1 Modify `ModuleTabs` to accept optional `adminContent` prop and render third tab when provided
- [x] 3.2 Create `SystemAdminPanel.tsx` component with stock statistics and user statistics blocks
- [x] 3.3 Add `hasSystemStatisticsPermission` state to `page.tsx` after user loads
- [x] 3.4 Conditionally render System Administration tab in homepage when user has permission

## 4. Styling

- [x] 4.1 Ensure System Administration tab matches existing tab styling (brass-emboss active state)
- [x] 4.2 Style statistics blocks to match existing vt-panel styling
