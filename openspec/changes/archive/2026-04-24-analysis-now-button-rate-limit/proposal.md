## Why

The "立刻分析" (Force Analysis Now) button on the stock detail page allows users to trigger trend analysis on demand. Without rate limiting, users could repeatedly click the button, causing unnecessary API calls, increased LLM costs, and potential abuse.

## What Changes

- Add per-user per-stock rate limiting for the analysis trigger: 1 click per hour maximum
- Frontend "立刻分析" button shall be disabled for 1 hour after a successful click
- Frontend shall display remaining cooldown time when button is disabled
- Backend shall enforce the rate limit and reject rapid repeated requests

## Capabilities

### New Capabilities
- `analysis-trigger-rate-limit`: Rate limiting for the "立刻分析" button, restricting each user to one trigger per stock per hour

### Modified Capabilities
- `stock-trend-display`: The "立刻分析" button behavior changes to respect rate limiting (disabled state, cooldown display)

## Impact

- **Frontend**: Stock detail page `page.tsx` - button disabled state and cooldown display
- **Backend**: API endpoint `/api/trend-predictions/batch-async` or similar - rate limit enforcement
- **Storage**: May need to track last trigger timestamp per user per stock
