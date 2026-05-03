## Why

Currently, A-share (China) and US stock queries are executed sequentially - the frontend waits for both queries to complete before displaying any data. This causes unnecessary delay: if US stock data takes longer to fetch or fails, it blocks A-share data from displaying. Users should see A-share data immediately when it's ready, without waiting for US stock queries.

## What Changes

- Refactor stock info fetching to run A-share and US stock queries independently and in parallel
- Implement fire-and-forget pattern for stock queries - each query resolves/rejects independently
- A-share display is unaffected by US stock query state (pending, success, or failure)
- US stock display is unaffected by A-share query state
- Add proper error handling so failed queries don't propagate to affect other displays

## Capabilities

### New Capabilities
- `independent-stock-query`: Frontend capability to fetch A-share and US stock data independently, displaying each as soon as its data arrives. Each query operates in isolation with its own loading and error states.

### Modified Capabilities
- `stock-query`: No requirement changes - only implementation changes to support parallel, independent fetching
- `us-stock-data`: No requirement changes - only implementation changes to support parallel, independent fetching

## Impact

- **Frontend**: Stock info display component needs to handle independent loading states per market type
- **Backend**: No changes required - API endpoints remain the same
- **Performance**: A-share data displays immediately upon query completion, without waiting for US stock queries
