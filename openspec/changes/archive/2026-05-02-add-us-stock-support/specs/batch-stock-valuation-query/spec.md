# batch-stock-valuation-query Specification

## Purpose
Batch query stock valuation metrics and basic info for multiple symbols in a single API call.

## ADDED Requirements

### Requirement: Batch valuation handles mixed market symbols
The system SHALL handle batch valuation requests containing both A-share and US stock symbols.

#### Scenario: Mixed market batch request
- **WHEN** GET request to `/api/stock/batch/valuation?symbols=600938,GOOGL,TSLA`
- **THEN** the response SHALL include valuation data for both A-share and US stocks
- **AND** A-share stocks use Tushare `daily_basic` endpoint
- **AND** US stocks use Tushare `us_daily` endpoint (or return null for unavailable fields)
- **AND** results array contains data for all valid symbols

### Requirement: Batch info handles mixed market symbols
The system SHALL handle batch info requests containing both A-share and US stock symbols.

#### Scenario: Mixed market batch info request
- **WHEN** GET request to `/api/stock/batch/info?symbols=600938,GOOGL`
- **THEN** the response SHALL include info for both A-share and US stocks
- **AND** each result SHALL include `market` field indicating "A" or "US"
