## ADDED Requirements

### Requirement: Role and Permission Data Model
The system SHALL provide a relational data model for roles and permissions.

#### Data Model: roles table
- `id` INTEGER PRIMARY KEY
- `name` TEXT NOT NULL UNIQUE (admin, power_user, user, guest)
- `description` TEXT
- `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP

#### Data Model: permissions table
- `id` INTEGER PRIMARY KEY
- `name` TEXT NOT NULL UNIQUE (assign_role, system_statistics, customized_agent)
- `description` TEXT
- `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP

#### Data Model: user_roles table
- `user_id` INTEGER NOT NULL, FOREIGN KEY → users(id)
- `role_id` INTEGER NOT NULL, FOREIGN KEY → roles(id)
- PRIMARY KEY (user_id, role_id)

#### Data Model: role_permissions table
- `role_id` INTEGER NOT NULL, FOREIGN KEY → roles(id)
- `permission_id` INTEGER NOT NULL, FOREIGN KEY → permissions(id)
- PRIMARY KEY (role_id, permission_id)

#### Data Model: users.is_guest column
- `is_guest` INTEGER DEFAULT 0 (0=registered user, 1=guest)

### Requirement: Default Role Assignment
The system SHALL assign default roles to users upon registration and to guests.

#### Scenario: New registered user gets 'user' role
- **WHEN** a new user successfully registers
- **THEN** they are assigned the 'user' role by default
- **AND** `is_guest` is set to 0

#### Scenario: Guest user gets 'guest' role
- **WHEN** an unauthenticated user accesses the system
- **THEN** they are considered a guest user
- **AND** `is_guest` is set to 1 on their session

### Requirement: Role-Permission Mappings
The system SHALL associate permissions with roles as follows:

| Role | Permissions |
|------|-------------|
| admin | assign_role, system_statistics, customized_agent |
| power_user | customized_agent |
| user | (none by default) |
| guest | (none by default) |

#### Scenario: jack.zhu has admin and power_user roles
- **WHEN** querying user 'jack.zhu'
- **THEN** they have both 'admin' and 'power_user' roles
- **AND** they have all permissions: assign_role, system_statistics, customized_agent

### Requirement: Permission Checking
The system SHALL provide a way to check if a user has a specific permission.

#### Scenario: Check user permission via RoleService
- **WHEN** calling `RoleService.user_has_permission(user_id, 'customized_agent')`
- **THEN** it returns true if the user has a role with that permission
- **AND** it returns false otherwise

#### Scenario: Permission check considers all user roles
- **WHEN** jack.zhu (admin + power_user) checks permission 'assign_role'
- **THEN** it returns true (via admin role)
- **WHEN** a regular user checks permission 'assign_role'
- **THEN** it returns false (no role has that permission)

### Requirement: Middleware for Protected Endpoints
The system SHALL provide middleware to protect API endpoints.

#### Scenario: Protected endpoint rejects unauthorized user
- **WHEN** a user without 'system_statistics' permission accesses a protected endpoint
- **THEN** the system returns HTTP 403 Forbidden
- **AND** error message indicates insufficient permissions
