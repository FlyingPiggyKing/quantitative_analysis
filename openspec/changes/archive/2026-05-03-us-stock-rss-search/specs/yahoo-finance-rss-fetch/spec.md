## ADDED Requirements

### Requirement: Yahoo Finance RSS fetching
The system SHALL fetch Yahoo Finance RSS feed via proxy to obtain authoritative news list for US stocks.

#### Scenario: Fetch RSS for US stock
- **WHEN** `fetch_yahoo_finance_rss(symbol)` is called for a US stock symbol
- **THEN** the system SHALL fetch `https://feeds.finance.yahoo.com/rss/2.0/headline?s={symbol}&region=US&lang=en-US` via configured proxy
- **AND** return a list of news items containing: title, description, link, pubDate

#### Scenario: RSS fetch fails or times out
- **WHEN** RSS fetch fails (network error, proxy error, timeout)
- **THEN** the system SHALL return an empty list
- **AND** log a warning message

#### Scenario: Parse RSS XML response
- **WHEN** RSS XML is successfully fetched
- **THEN** the system SHALL parse each `<item>` element extracting: title, description (summary), link, pubDate
- **AND** return a structured list sorted by publication date (newest first)

### Requirement: RSS news item structure
Each RSS news item SHALL contain the following fields:

- `title`: News headline (string)
- `description`: Short summary/snippet (string)
- `link`: URL to full article (string)
- `pubDate`: Publication date in ISO format (string)

#### Scenario: RSS news item format
- **WHEN** RSS feed is successfully parsed
- **THEN** each news item SHALL be a dictionary with keys: title, description, link, pubDate
- **AND** items SHALL be sorted by pubDate descending (newest first)
