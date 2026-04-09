## ADDED Requirements

### Requirement: CAPTCHA generation

The system SHALL generate a random alphanumeric string and corresponding image for CAPTCHA verification.

#### Scenario: Request new CAPTCHA
- **WHEN** client requests GET /api/captcha
- **THEN** system generates a 6-character random string using uppercase letters and digits (excluding ambiguous characters 0, O, 1, l)
- **AND** system stores the CAPTCHA code in database with creation timestamp
- **AND** system returns a base64-encoded PNG image of the CAPTCHA

#### Scenario: CAPTCHA expires after 5 minutes
- **WHEN** a CAPTCHA older than 5 minutes is submitted for verification
- **THEN** system rejects the verification with error "CAPTCHA expired"

### Requirement: CAPTCHA verification

The system SHALL verify submitted CAPTCHA codes against stored values.

#### Scenario: Valid CAPTCHA submission
- **WHEN** user submits login/signup form with correct CAPTCHA code
- **THEN** system verifies the CAPTCHA code matches and is not expired
- **AND** verification succeeds

#### Scenario: Invalid CAPTCHA code
- **WHEN** user submits login/signup form with incorrect CAPTCHA code
- **THEN** system returns error "Invalid CAPTCHA code" with HTTP 400 status

#### Scenario: Expired CAPTCHA
- **WHEN** user submits login/signup form with an expired CAPTCHA code
- **THEN** system returns error "CAPTCHA expired" with HTTP 400 status

#### Scenario: CAPTCHA case sensitivity
- **WHEN** user submits CAPTCHA code "abc123" when the actual code is "ABC123"
- **THEN** system SHALL treat the codes as case-insensitive and verification succeeds

### Requirement: CAPTCHA linked to session

The system SHALL associate CAPTCHA codes with user sessions to prevent replay attacks.

#### Scenario: CAPTCHA code is single-use
- **WHEN** a CAPTCHA code is successfully verified
- **THEN** the CAPTCHA code is invalidated and cannot be reused
- **AND** a new CAPTCHA must be requested for subsequent verification attempts
