## ADDED Requirements

### Requirement: User-specific watchlist isolation

The system SHALL ensure each user can only view, add, and remove stocks from their own watchlist.

#### Scenario: User sees only their own stocks
- **WHEN** authenticated user "alice" requests GET /api/watchlist
- **THEN** system returns only stocks added by user "alice"
- **AND** system does NOT return stocks added by user "bob"

#### Scenario: Add stock to own watchlist
- **WHEN** authenticated user "alice" adds stock "600000" to watchlist
- **THEN** stock "600000" appears in user "alice"'s watchlist
- **AND** stock "600000" does NOT appear in user "bob"'s watchlist

#### Scenario: Remove stock from own watchlist
- **WHEN** authenticated user "alice" removes stock "600000" from watchlist
- **THEN** stock "600000" is removed from user "alice"'s watchlist
- **AND** user "bob"'s watchlist remains unchanged (if "bob" had added "600000")

#### Scenario: Cannot access other user's watchlist
- **WHEN** authenticated user "alice" attempts to delete stock "600000" that belongs to user "bob"
- **THEN** system returns error "Stock not found in watchlist" with HTTP 404 status

### Requirement: Default user has existing stocks

The default user "jack.zhu" SHALL own all stocks that existed in the watchlist before authentication was added.

#### Scenario: Default user migration
- **WHEN** the authentication system is first deployed
- **THEN** all existing watchlist entries are assigned to user "jack.zhu" (user_id=1)
- **AND** user "jack.zhu" can view all previously added stocks

### Requirement: Watchlist requires authentication

The system SHALL reject unauthenticated requests to watchlist endpoints.

#### Scenario: Get watchlist without authentication
- **WHEN** unauthenticated user requests GET /api/watchlist
- **THEN** system returns error "Authentication required" with HTTP 401 status

#### Scenario: Add to watchlist without authentication
- **WHEN** unauthenticated user requests POST /api/watchlist to add a stock
- **THEN** system returns error "Authentication required" with HTTP 401 status

#### Scenario: Delete from watchlist without authentication
- **WHEN** unauthenticated user requests DELETE /api/watchlist/{symbol}
- **THEN** system returns error "Authentication required" with HTTP 401 status
