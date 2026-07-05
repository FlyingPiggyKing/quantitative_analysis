## MODIFIED Requirements

### Requirement: Fetcher normalizes raw yahooquery output
The system MUST convert raw yahooquery responses to the normalized record shapes described above before returning. Downstream pusher and store modules MUST NOT import from `yahooquery` directly.

#### Scenario: Timestamp fields are always ISO8601 UTC
- **WHEN** any fetcher returns records with a timestamp
- **THEN** that timestamp MUST be a string in ISO8601 UTC form with a `Z` suffix

#### Scenario: Timestamp inputs from yahooquery may be epoch or ISO date string
- **WHEN** the fetcher receives a `regularMarketTime`, `preMarketTime`, or `postMarketTime` value from yahooquery
- **THEN** the fetcher MUST accept both shapes: an integer/float epoch in seconds AND an ISO date string (with or without trailing `Z`); both shapes are converted to a single canonical ISO8601 UTC `Z`-suffixed string before being placed in the record; values that cannot be parsed in either form are treated as missing and the corresponding record is dropped with a `fetch_log` error entry

#### Scenario: Missing fields are null, not absent
- **WHEN** a yahooquery field is unavailable (e.g., `preMarketPrice` for a non-trading moment)
- **THEN** the normalized record MUST include the key with value `null`

## REMOVED Requirements

### Requirement: Fetch news
**Reason:** Yahoo Finance news endpoint is currently unavailable from the overseas host (HTTP 429 / error response for every symbol under the deployed yahooquery version). The fetcher code path (`fetch_news`) was also written against a stale API shape (`Ticker.news` is a method, not a property). News ingestion is parked until a viable alternative source is selected and a follow-up change is opened.
**Migration:** The `etf_news` table, the `insert_etf_news` helper, and `fetch_news` module remain in place so a future change can re-enable news without a schema migration. The scheduler no longer schedules a news fetch job. See OpenSpec change `fix-quote-and-news` design.md (decision D3) for revival notes.