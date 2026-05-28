## 1. Backup Script

- [x] 1.1 Create `scripts/backup_database.py` to backup `watchlist.db` with timestamp
- [x] 1.2 Test backup script execution

## 2. Database Migration

- [x] 2.1 Create `scripts/migrate_roles_permissions.py` migration script
- [x] 2.2 Add `roles` table with 4 default roles
- [x] 2.3 Add `permissions` table with 3 default permissions
- [x] 2.4 Add `user_roles` junction table
- [x] 2.5 Add `role_permissions` junction table
- [x] 2.6 Add `is_guest` column to `users` table
- [x] 2.7 Seed role-permission mappings
- [x] 2.8 Assign jack.zhu to admin and power_user roles
- [x] 2.9 Assign default 'user' role to existing registered users
- [x] 2.10 Verify migration with SELECT queries

## 3. Role Service

- [x] 3.1 Create `backend/services/role_service.py` with `RoleService` class
- [x] 3.2 Implement `user_has_permission(user_id, permission)` method
- [x] 3.3 Implement `get_user_roles(user_id)` method
- [x] 3.4 Implement `get_role_permissions(role_id)` method
- [x] 3.5 Implement `is_guest_user(user_id)` method

## 4. Permission Middleware

- [x] 4.1 Add `require_permission(permission_name)` decorator to auth.py
- [N/A] 4.2 Apply `@require_permission("system_statistics")` to stats endpoint (if exists) - No stats endpoint currently exists
- [N/A] 4.3 Apply `@require_permission("assign_role")` to role assignment endpoint (if exists) - No role assignment endpoint currently exists
