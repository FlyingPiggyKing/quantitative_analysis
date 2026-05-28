## Why

The system needs an administrative module for users with `system_statistics` permission to view system-wide statistics. This provides visibility into watch list usage and user activity for admin users like jack.zhu.

## What Changes

- Add "系统管理" (System Administration) tab to the top-level module navigation
- The tab is only visible to authenticated users with `system_statistics` permission
- The module displays two statistics blocks:
  1. **股票统计**: Lists all stocks in the watch list with total count
  2. **用户统计**: Lists all registered users with total count

## Capabilities

### New Capabilities
- `system-admin-module`: Administrative module displaying watch list stock statistics and user statistics. Only accessible to users with `system_statistics` permission.

### Modified Capabilities
- `module-layout-tabs`: Extend top-level tabs to include "系统管理" option for users with appropriate permissions

## Impact

- Frontend: New SystemAdminModule component, modification to ModuleTabs to conditionally show the tab
- Backend: New API endpoint(s) to fetch watch list stocks and user list for admin purposes
- The `system_statistics` permission gate already exists in the role/permission system
