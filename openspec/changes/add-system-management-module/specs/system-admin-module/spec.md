## ADDED Requirements

### Requirement: System Admin Module Visibility
The system SHALL display a "系统管理" (System Administration) tab in the top-level module navigation ONLY for users who have the `system_statistics` permission.

#### Scenario: Admin user sees System Administration tab
- **WHEN** an authenticated user with `system_statistics` permission views the homepage
- **THEN** the module tab bar shows three tabs: "我的自选", "投资分析", and "系统管理"

#### Scenario: Regular user does not see System Administration tab
- **WHEN** an authenticated user without `system_statistics` permission views the homepage
- **THEN** the module tab bar shows only two tabs: "我的自选" and "投资分析"
- **AND** "系统管理" tab is not rendered

#### Scenario: Guest user does not see System Administration tab
- **WHEN** an unauthenticated (guest) user views the homepage
- **THEN** the module tab bar shows only two tabs: "我的自选" and "投资分析"
- **AND** "系统管理" tab is not rendered

### Requirement: System Admin Module Content
The system SHALL display two statistics blocks within the System Administration module: stock statistics and user statistics.

#### Scenario: System Administration module displays stock statistics block
- **WHEN** admin user views the System Administration module
- **THEN** a "股票统计" (Stock Statistics) block is displayed
- **AND** it lists all stocks from the global watchlist table
- **AND** it shows the total count of stocks (e.g., "共 X 只股票")

#### Scenario: System Administration module displays user statistics block
- **WHEN** admin user views the System Administration module
- **THEN** a "用户统计" (User Statistics) block is displayed
- **AND** it lists all registered users (username and registration date)
- **AND** it shows the total count of users (e.g., "共 X 位用户")

### Requirement: System Admin API Endpoint
The system SHALL provide an API endpoint `/api/admin/stats` that returns watchlist stocks and user statistics, accessible only to users with `system_statistics` permission.

#### Scenario: Authorized user can access admin stats endpoint
- **WHEN** a user with `system_statistics` permission calls `GET /api/admin/stats` with valid authentication
- **THEN** the response contains `watchlist_stocks` array with symbol, name, added_at for each stock
- **AND** the response contains `users` array with id, username, created_at for each user
- **AND** the response contains `watchlist_count` and `user_count` integers

#### Scenario: Unauthorized user cannot access admin stats endpoint
- **WHEN** a user without `system_statistics` permission calls `GET /api/admin/stats`
- **THEN** the system returns HTTP 403 Forbidden
- **AND** error message indicates insufficient permissions
