## ADDED Requirements

### Requirement: Yahoo Finance search for US stocks
The stock trend analysis agent SHALL prioritize Yahoo Finance news when analyzing US stocks.

#### Scenario: US stock news search with Yahoo Finance priority
- **WHEN** agent analyzes a US stock (market == "US")
- **THEN** agent SHALL construct a search query targeting Yahoo Finance articles: "[stock name] [stock symbol] site:finance.yahoo.com"
- **AND** this Yahoo Finance-focused search SHALL be the primary news source
- **AND** if Yahoo Finance search returns insufficient results, agent SHALL fall back to generic stock news search

#### Scenario: A-share stock search unchanged
- **WHEN** agent analyzes an A-share stock (market == "A")
- **THEN** agent SHALL use the existing generic search approach unchanged
- **AND** no Yahoo Finance filtering SHALL be applied

### Requirement: Market-aware search strategy
The search strategy SHALL be determined by the market parameter passed to `analyze_stock_trend()`.

#### Scenario: US market triggers Yahoo Finance priority
- **WHEN** `analyze_stock_trend(symbol, name)` is called with a US stock symbol
- **THEN** the market parameter SHALL be set to "US"
- **AND** the search instruction SHALL include Yahoo Finance targeting

#### Scenario: A-share market uses generic search
- **WHEN** `analyze_stock_trend(symbol, name)` is called with an A-share symbol
- **THEN** the market parameter SHALL be set to "A"
- **AND** the search SHALL use generic stock news without Yahoo Finance filtering
