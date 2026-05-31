## Context

Currently the system uses simple authentication without any authorization. All authenticated users have equal access. We need to implement RBAC (Role-Based Access Control) to restrict sensitive operations.

**Current State:**
- Users table exists in `watchlist.db` with: id, username, password_hash, created_at
- Guest users (unauthenticated) have no stored identity
- No role or permission concept exists

**Stakeholders:** jack.zhu (admin), future power users, regular registered users, guest users

## Goals / Non-Goals

**Goals:**
- Implement basic RBAC with 4 roles and 3 permissions
- Support many-to-many relationship between users and roles
- Support many-to-many relationship between roles and permissions
- Provide backup before any schema migration
- Seed default data for roles/permissions

**Non-Goals:**
- No fine-grained resource-level permissions (just role-level)
- No role hierarchy (admin > power_user > user > guest)
- No API endpoints for managing roles/permissions (inline in migration only)
- No guest user record in database (guest is absence of authentication)

## Decisions

### Decision 1: Database Schema Design

**Choice:** SQLite with junction tables for many-to-many relationships

```
roles (id, name, description, created_at)
permissions (id, name, description, created_at)
user_roles (user_id, role_id) - junction table
role_permissions (role_id, permission_id) - junction table
```

**Why:**
- Existing SQLite database (watchlist.db) keeps things simple
- Junction tables are standard SQL pattern for many-to-many
- Minimal schema changes to existing users table (add is_guest column)

**Alternatives Considered:**
- Single `role` column on users table: Rejected - doesn't support multiple roles per user
- Separate permission flags on users: Rejected - not extensible

### Decision 2: Guest Handling

**Choice:** `is_guest` boolean flag on users table + default "guest" role assignment

**Why:**
- Guests are unauthenticated but need a role for permission checks
- Setting `is_guest=1` on anonymous sessions allows consistent permission checking

**Alternatives Considered:**
- Null user_id for guests: More complex joins
- No guest role, just check `is_guest`: Rejected - role provides consistent pattern

### Decision 3: Permission Check Implementation

**Choice:** Decorator/middleware pattern in API layer

**Why:**
- Keeps permission logic centralized
- Easy to add `@require_permission("assign_role")` to endpoints

**Alternatives Considered:**
- Permission checks in each service: Scattered logic
- Frontend-only checks: Insecure, can be bypassed

### Decision 4: Backup Strategy

**Choice:** Python script that copies `watchlist.db` to `watchlist.db.backup.<timestamp>`

**Why:**
- Simple, no external dependencies
- SQLite file-based backup is just a file copy

## Risks / Trade-offs

| Risk | Mitigation |
|------|------------|
| Migration failure mid-way | Backup before migration, transaction-style execution |
| Role assignment error | Use explicit seed data, verify with SELECT queries |
| Guest access not properly blocked | Middleware to require authentication for protected endpoints |

## Migration Plan

1. Run `scripts/backup_database.py` to backup `watchlist.db`
2. Run `scripts/migrate_roles_permissions.py` which:
   - Creates new tables (roles, permissions, user_roles, role_permissions)
   - Adds `is_guest` column to users table
   - Seeds default roles and permissions
   - Assigns jack.zhu to admin + power_user roles
3. Update application code to use role/permission checks
4. No rollback needed if backup exists - restore from backup file

## Open Questions

- Should we delete the backup after successful migration or keep it?
- Do we need to track role assignment history (audit log)?
