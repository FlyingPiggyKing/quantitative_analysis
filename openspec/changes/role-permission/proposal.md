## Why

Currently the system has no role or permission concept - all authenticated users have the same access. We need a role-based access control (RBAC) system to restrict certain features to specific users (e.g., only admins can assign roles, only power users can use customized agents).

## What Changes

- Add `roles` table to store role definitions (admin, power_user, user, guest)
- Add `permissions` table to store permission definitions (assign_role, system_statistics, customized_agent)
- Add `user_roles` junction table to assign roles to users (many-to-many)
- Add `role_permissions` junction table to assign permissions to roles (many-to-many)
- Update `users` table with `is_guest` flag to distinguish registered vs. guest users
- Create backup script to backup database before any schema changes
- Add seed data for default roles and permissions
- Set jack.zhu as both admin and power_user

## Capabilities

### New Capabilities
- `role-permission-management`: Full RBAC system with roles, permissions, user-role assignments
- `database-backup`: Backup script for watchlist.db before migrations

### Modified Capabilities
<!-- No existing spec-level behavior changes -->

## Impact
- Database: New tables in `backend/watchlist.db` (roles, permissions, user_roles, role_permissions)
- Backend: New service `role_service.py`, updated `db_migration.py`
- API: New endpoints for role/permission checks (middleware)
