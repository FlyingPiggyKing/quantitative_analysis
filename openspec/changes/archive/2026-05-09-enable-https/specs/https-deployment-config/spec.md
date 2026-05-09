## ADDED Requirements

### Requirement: Frontend API URL supports HTTPS in production
The frontend SHALL use HTTPS URL for API calls when deployed to production environment to avoid Mixed Content errors.

#### Scenario: Development environment uses localhost HTTP
- **WHEN** `NEXT_PUBLIC_API_URL` is not set
- **THEN** frontend SHALL use `http://localhost:8000` as API base URL

#### Scenario: Production environment uses HTTPS API URL
- **WHEN** `NEXT_PUBLIC_API_URL` is set to `https://api.example.com`
- **THEN** frontend SHALL use `https://api.example.com` as API base URL

#### Scenario: Browser blocks mixed content
- **WHEN** frontend page is loaded over HTTPS and makes HTTP API request
- **THEN** browser SHALL block the request with Mixed Content error

### Requirement: Backend runs behind reverse proxy for HTTPS
The backend SHALL be deployed behind a reverse proxy that terminates HTTPS, so the backend can run on HTTP localhost.

#### Scenario: Reverse proxy forwards HTTPS requests to backend
- **WHEN** reverse proxy receives HTTPS request on port 443
- **THEN** proxy SHALL forward request to backend at `http://127.0.0.1:8000` over localhost

#### Scenario: Backend binds to localhost only
- **WHEN** backend starts in production
- **THEN** it SHALL bind to `127.0.0.1:8000` (not exposed directly to internet)
