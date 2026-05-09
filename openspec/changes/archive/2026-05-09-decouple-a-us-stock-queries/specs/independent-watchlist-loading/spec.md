# independent-watchlist-loading Specification

## ADDED Requirements

### Requirement: Independent loading states per market
The WatchList component SHALL maintain separate loading states for A-share and US stock data.

#### Scenario: A-share loads before US stock
- **WHEN** user views WatchList
- **AND** A-share watchlist and valuation data is fetched successfully
- **AND** US stock data is still loading
- **THEN** system displays A-share data immediately
- **AND** US stock section shows loading indicator independently

#### Scenario: US stock loads before A-share
- **WHEN** user views WatchList
- **AND** US stock watchlist and valuation data is fetched successfully
- **AND** A-share data is still loading
- **THEN** system displays US stock data immediately
- **AND** A-share section shows loading indicator independently

### Requirement: A-share loading completes before US stock
- **WHEN** user views WatchList with A-share and US stocks
- **AND** A-share data arrives after 100ms
- **AND** US stock data arrives after 7000ms (cache miss + proxy delay)
- **THEN** system displays A-share data within 200ms of page load
- **AND** system displays US stock data when it arrives after 7000ms

### Requirement: A-share displays when US stock fails
- **WHEN** user views WatchList
- **AND** A-share data is available
- **AND** US stock valuation query fails (e.g., network error, rate limit)
- **THEN** system displays A-share data immediately
- **AND** US stock section shows error state without blocking A-share display

### Requirement: US stock displays when A-share fails
- **WHEN** user views WatchList
- **AND** US stock data is available
- **AND** A-share valuation query fails
- **THEN** system displays US stock data immediately
- **AND** A-share section shows error state without blocking US stock display

### Requirement: Tab switching fetches data independently
- **WHEN** user is on A-share tab and switches to US tab
- **AND** US stock data has not been loaded yet
- **THEN** system initiates US stock data fetch
- **AND** US tab shows loading indicator
- **AND** A-share data remains displayed in background

### Requirement: Active tab data prioritized on initial load
- **WHEN** user loads WatchList
- **AND** active tab is "A" (A-share)
- **THEN** system fetches A-share watchlist and valuation data first
- **AND** system may fetch US stock data in parallel or after A-share completes
