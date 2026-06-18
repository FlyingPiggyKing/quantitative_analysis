# hourly-news-data-source Specification

## Purpose
TBD - created by archiving change fix-daily-news-interface. Update Purpose after archive.
## Requirements
### Requirement: Hourly news data source
The hourly news analysis task queue SHALL fetch A-share market news from Tushare's `major_news` interface (provider-agnostic contract: list of `{datetime, title, content, source, relevance}` dicts) for the past 60 minutes from the moment the task runs.

The fetch layer MUST be parameterised by a single module-level constant `NEWS_PROVIDER` so that swapping data sources (e.g. reverting to `pro.news(src='sina')` if permissions are restored) is a one-line change.

#### Scenario: Successful fetch from major_news
- **WHEN** scheduler triggers `_run_news_analysis` at hour boundary
- **AND** Tushare `pro.major_news(src='', start_date=YYYYMMDD, end_date=YYYYMMDD)` returns a non-empty DataFrame
- **THEN** the system SHALL filter rows where `pub_time >= now - 60 minutes`
- **AND** SHALL project each row to `{datetime: pub_time str, title, content (truncated to 500 chars), source: src, relevance: 0.5}`
- **AND** SHALL return the list to the agent for analysis

#### Scenario: Empty response from major_news
- **WHEN** Tushare `pro.major_news` returns an empty DataFrame or `None`
- **THEN** the system SHALL log a warning and return `[]`
- **AND** the task queue SHALL set task status to `failed` with `error="No news available"`

#### Scenario: major_news call raises
- **WHEN** Tushare `pro.major_news` raises any exception (auth, network, rate limit)
- **THEN** the system SHALL log the error
- **AND** SHALL return `[]`
- **AND** the task queue SHALL set task status to `failed` with the exception message

#### Scenario: Field `rel` absent
- **WHEN** `major_news` rows do not contain a `rel` column
- **THEN** the system SHALL default `relevance` to `0.5` (the agent's filter threshold) so all returned news pass the relevance gate

#### Scenario: Provider swap (regression guard)
- **WHEN** the `NEWS_PROVIDER` constant is changed back to `"news"` in a future commit
- **THEN** the fetch layer SHALL dispatch to the `pro.news(src='sina')` path
- **AND** the rest of the pipeline (agent / DB / API / frontend) SHALL continue to work without any further change

