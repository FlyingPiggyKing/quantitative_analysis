## Context

The `WatchList.tsx` component currently uses a single shared `loading` state that blocks both A-share and US stock data until all fetches complete. This causes A-share data to be delayed when US stock data (which uses Yahoo Finance with proxy and can take 7+ seconds on cache miss) is slow.

Current data flow:
1. `setLoading(true)` - blocks entire component
2. Fetch A-share and US watchlists in parallel via `Promise.all`
3. Fetch valuations for both markets in parallel via `Promise.allSettled`
4. Fetch predictions globally (single endpoint)
5. `setLoading(false)` - unblocks entire component only after ALL complete

The backend API already supports independent queries per market. The issue is purely frontend state management.

## Goals / Non-Goals

**Goals:**
- A-share data displays as soon as it's available, without waiting for US stock data
- US stock data displays as soon as it's available, without waiting for A-share data
- Each market tab shows independent loading indicators
- Graceful degradation when one market's data fails

**Non-Goals:**
- No backend changes (API already supports independent queries)
- Not changing the API response format
- Not adding new endpoints

## Decisions

### Decision 1: Separate loading states per market

**Chosen Approach:** Replace single `loading` state with `aShareLoading` and `usLoading` booleans.

**Rationale:** Each market needs to transition from "loading" to "displayed" independently. The current `loading` state is a single gate that blocks the entire component.

**Alternatives Considered:**
- Use `useReducer` with complex state machine - overkill for this case
- Separate components for A-share and US stock - would require significant refactoring of tab structure

### Decision 2: Staggered initial fetch based on active tab

**Chosen Approach:** On initial load, prioritize fetching data for the active tab first.

**Rationale:** Users typically view one tab at a time. Fetching the inactive tab's data in the background is wasteful if the user never switches tabs.

**Alternatives Considered:**
- Fetch both immediately on mount - current behavior, causes unnecessary delays
- Fetch on tab switch only - could cause perceived delay when switching tabs

### Decision 3: Predictions as non-blocking

**Chosen Approach:** Predictions already use a separate try/catch. Keep predictions as a non-blocking fetch that doesn't affect market data display.

**Rationale:** Predictions are nice-to-have UI enhancement, not critical data. They shouldn't block stock display per the existing spec requirements.

## Risks / Trade-offs

**[Risk]** User switches tabs quickly before data loads → **Mitigation:** Each tab maintains its own loading state, so switching to a tab that's still loading shows appropriate loading indicator.

**[Risk]** Race condition where tab state changes during fetch → **Mitigation:** Use `AbortController` or cleanup function in `useEffect` to cancel in-flight requests when component unmounts or dependencies change.

**[Risk]** Double fetch when switching tabs → **Mitigation:** Cache fetched data in state and only re-fetch if `refreshTrigger` changes or user explicitly requests refresh.

## Open Questions

1. Should we prefetch the inactive tab's data in the background after active tab loads? This would speed up tab switching but adds network load.
