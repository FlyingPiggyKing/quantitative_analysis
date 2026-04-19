## Context

The current website uses a PC browser-optimized layout with fixed max-width containers and large typography. When accessed from iPhone (320px-428px viewport width), the experience degrades significantly:
- Tables overflow horizontally, requiring horizontal scroll
- Charts are cramped and difficult to read
- Navigation requires precision taps on small targets
- Text is too small for comfortable reading
- No touch-friendly interactions

The tech stack is Next.js 16.2.2 with React 19.2.4 and Tailwind CSS v4. No UI framework is used - all styling is via Tailwind utilities.

## Goals / Non-Goals

**Goals:**
- Create mobile-friendly layouts for index page and stock detail page
- Ensure charts render well on mobile viewports
- Make all interactive elements touch-friendly (44x44pt minimum tap targets)
- Maintain dark theme aesthetic on mobile
- Use existing Tailwind CSS infrastructure without adding new dependencies

**Non-Goals:**
- Native iOS app or PWA - web only
- Complete redesign - preserve existing design language
- Adding new functionality - purely responsive adaptation
- Supporting tablets or devices wider than 428px (handled by existing responsive)

## Decisions

### 1: Mobile-First Breakpoints
**Decision**: Use Tailwind's default breakpoints with explicit mobile-first utilities.
**Rationale**: Tailwind v4 supports mobile-first by default. No custom breakpoints needed.
- `sm:` (640px) - Large phones landscape
- `md:` (768px) - Tablets (existing)
- Mobile base styles apply to 320px-428px iPhone widths

**Alternative considered**: Custom breakpoints. Rejected - Tailwind defaults are sufficient and avoid complexity.

### 2: Chart Height Adaptation
**Decision**: Charts use percentage-based or adaptive height on mobile instead of fixed 400px.
**Rationale**: Mobile viewports vary in height. Charts should fill available space without scrolling.
- Mobile: ~250px height for candlestick chart
- Indicator panels stack vertically on mobile

**Alternative considered**: Fixed smaller height. Rejected - reduces readability.

### 3: Table-to-Card Transformation
**Decision**: Watchlist table transforms to card-based layout on mobile.
**Rationale**: Tables with many columns are unusable on mobile. Cards display essential info vertically.
- Mobile shows: symbol, name, trend indicator, PE/PB in 2-column grid
- Tap card to navigate to stock detail

**Alternative considered**: Horizontal scroll. Rejected - poor UX, easy to accidentally scroll table instead of page.

### 4: Bottom Navigation vs Top Bar
**Decision**: Keep existing top header on mobile but make it more compact.
**Rationale**: The site has minimal navigation (home + stock pages). Bottom nav adds complexity without benefit.

**Alternative considered**: Bottom tab bar. Rejected - only 2 main pages make bottom nav unnecessary.

### 5: Touch Interactions
**Decision**: Keep existing interactions but add touch feedback (scale transforms on tap).
**Rationale**: Most interactions are tap-based already (navigation, buttons). No gesture complexity needed.

## Risks / Trade-offs

| Risk | Mitigation |
|------|------------|
| Charts less detailed on small screens | Show essential data only; full chart on tap expands |
| Card layout may miss data visible in table | Prioritize most important columns; secondary data in expandable section |
| Touch targets too small | Enforce 44px minimum tap targets per Apple HIG |
| Landscape orientation awkward | Support but prioritize portrait; use full width in landscape |

## Open Questions

1. **PE Trend Sparkline on mobile cards**: Should we show the sparkline on mobile cards or omit for space?
   - Current leaning: Show simplified sparkline (no labels) on mobile cards

2. **Indicator Panel collapse**: Should indicators like MACD/RSI be collapsed by default on mobile?
   - Current leaning: Yes, collapsible accordion to save vertical space

3. **Trend Analysis Panel on stock detail**: Should full AI analysis be visible on mobile or collapsed?
   - Current leaning: Visible but compact - summary only, expandable for full text
