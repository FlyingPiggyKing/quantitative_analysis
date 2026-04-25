## Why

Currently, guests viewing the preset stock list cannot see AI trend predictions for stocks. Only logged-in users with a watchlist can see "AI下周预测" (AI next-week prediction). This creates a suboptimal experience for potential users who must sign up just to see basic AI predictions. Enabling AI predictions in the guest view will showcase the value of the analysis feature and encourage user sign-ups.

## What Changes

- **Modified `PresetStockList` component** to fetch and display AI trend predictions alongside existing valuation data
- **Desktop table view**: Add "AI下周预测" column showing trend direction and confidence
- **Mobile card view**: Add AI prediction indicator next to stock name
- **Trend indicator colors**: Green (up), Red (down), Gray (neutral) - consistent with logged-in view

## Capabilities

### New Capabilities
(None - this change extends existing UI behavior without new requirements)

### Modified Capabilities
(None - this change enables existing `stock-trend-display` capability in guest view, but does not change any spec requirements)

## Impact

**Frontend:**
- `frontend/src/components/PresetStockList.tsx` - Add trend prediction fetch and display logic
- `frontend/src/services/trendPrediction.ts` - Already exports `getTrendPredictions()` and `TrendPrediction` interface (no changes needed)

**Backend:**
- No changes required - existing `/api/trend-predictions` endpoint already returns predictions for all analyzed stocks (public endpoint, no auth required)

**Dependencies:**
- Relies on existing trend prediction data being populated via batch analysis
