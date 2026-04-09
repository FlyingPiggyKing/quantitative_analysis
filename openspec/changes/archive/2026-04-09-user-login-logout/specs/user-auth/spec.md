## ADDED Requirements

### Requirement: User registration

The system SHALL allow new users to create an account with a unique username and password.

#### Scenario: Successful registration
- **WHEN** user submits a registration form with username "newuser" and password "SecurePass123"
- **THEN** system creates a new user record with hashed password and returns success message
- **AND** system does NOT return the password or password hash

#### Scenario: Username already exists
- **WHEN** user submits a registration form with username "existinguser" where username already exists
- **THEN** system returns error "Username already taken" with HTTP 409 status

#### Scenario: Weak password rejected
- **WHEN** user submits a registration form with password "123" (too short)
- **THEN** system returns error "Password must be at least 8 characters" with HTTP 400 status

### Requirement: User login

The system SHALL authenticate users with valid username and password credentials and return a JWT token.

#### Scenario: Successful login
- **WHEN** user submits login form with correct username and password
- **THEN** system returns a valid JWT token with HTTP 200 status
- **AND** token contains user_id and username claims
- **AND** token expires in 24 hours

#### Scenario: Invalid username
- **WHEN** user submits login form with non-existent username
- **THEN** system returns error "Invalid username or password" with HTTP 401 status

#### Scenario: Invalid password
- **WHEN** user submits login form with correct username but wrong password
- **THEN** system returns error "Invalid username or password" with HTTP 401 status

### Requirement: User logout

The system SHALL allow authenticated users to invalidate their current session token.

#### Scenario: Successful logout
- **WHEN** authenticated user calls POST /api/auth/logout with valid token
- **THEN** system invalidates the token and returns success message
- **AND** subsequent requests with the same token return HTTP 401

#### Scenario: Logout without token
- **WHEN** unauthenticated user calls POST /api/auth/logout without token
- **THEN** system returns error "Authentication required" with HTTP 401 status

### Requirement: Protected endpoints require authentication

The system SHALL reject requests to protected endpoints without valid authentication tokens.

#### Scenario: Access watchlist without token
- **WHEN** user requests GET /api/watchlist without Authorization header
- **THEN** system returns error "Authentication required" with HTTP 401 status

#### Scenario: Access watchlist with invalid token
- **WHEN** user requests GET /api/watchlist with invalid or expired token
- **THEN** system returns error "Invalid or expired token" with HTTP 401 status

#### Scenario: Access watchlist with valid token
- **WHEN** user requests GET /api/watchlist with valid Authorization header
- **THEN** system returns the authenticated user's watchlist items

### Requirement: Token contains user identity

The JWT token SHALL contain claims that identify the authenticated user.

#### Scenario: Token payload structure
- **WHEN** system issues a JWT token after successful login
- **THEN** token payload contains "sub" claim with user_id
- **AND** token payload contains "username" claim with the user's username
- **AND** token payload contains "exp" claim with expiration timestamp
