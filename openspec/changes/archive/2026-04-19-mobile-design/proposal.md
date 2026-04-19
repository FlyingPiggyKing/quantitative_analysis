## Why

The current website is designed for PC browsers with large screens. When accessed from an iPhone, the experience is poor - text is too small, tables overflow horizontally, charts are cramped, and navigation is difficult without hover states. As mobile web traffic grows, users need a usable experience on their phones.

## What Changes

- Implement mobile-first responsive design for the index page and stock detail page
- Restructure layouts for vertical scrolling on narrow screens
- Adapt chart components for mobile viewport sizes
- Add mobile-friendly navigation and touch interactions
- Optimize typography and spacing for readability on small screens
- Simplify complex data tables into mobile-appropriate views

## Capabilities

### New Capabilities
- `mobile-responsive-layout`: Create responsive layout system that adapts index and stock detail pages for mobile viewports (320px-428px iPhone width)
- `mobile-chart-adaptation`: Adapt candlestick chart and indicator panels for smaller screens with appropriate sizing and touch interactions
- `mobile-navigation`: Add mobile-optimized navigation patterns including collapsible sections and swipe gestures where appropriate

### Modified Capabilities
- `watch-list-display`: The watchlist table requires mobile adaptation to display well on small screens (collapse columns, card view)
- `stock-trend-display`: Trend analysis panel needs mobile layout reflow to fit narrow viewports

## Impact

- **Frontend**: Tailwind CSS v4 already in use - will add mobile breakpoints and utility classes
- **Components**: StockChart, IndicatorPanel, TrendAnalysisPanel, WatchList require mobile adaptations
- **No backend changes**: Pure frontend UI/UX changes
- **No API changes**: All data fetching remains unchanged
