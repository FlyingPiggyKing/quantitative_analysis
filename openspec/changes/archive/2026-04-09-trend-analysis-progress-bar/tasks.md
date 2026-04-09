## 1. Create Progress Bar Component

- [x] 1.1 Create `AnalysisProgressBar` component in `frontend/src/components/`
- [x] 1.2 Add progress bar UI: text display "Analyzing: X/Y stocks (Z%)" and visual bar
- [x] 1.3 Add dismiss button with hover state styling
- [x] 1.4 Style with specified colors (bg: #F3F4F6, fill: #3B82F6, text: #374151)

## 2. Integrate Progress Bar into Watch List Page

- [x] 2.1 Import and add `AnalysisProgressBar` to bottom of watch list page (`frontend/src/app/page.tsx`)
- [x] 2.2 Add state for active task ID and progress data
- [x] 2.3 Add localStorage persistence for active task ID
- [x] 2.4 Check for active task on page load and restore state

## 3. Add Polling Logic

- [x] 3.1 Create `useTaskStatus` hook or integrate polling in page component
- [x] 3.2 Poll `/api/trend-predictions/task/{task_id}` every 3 seconds when task is running
- [x] 3.3 Update progress state on each successful poll
- [x] 3.4 Clear polling and hide progress bar when task completes or fails

## 4. Testing

- [ ] 4.1 Verify progress bar appears when task is running
- [ ] 4.2 Verify progress bar hides when task completes/fails
- [ ] 4.3 Verify dismiss button hides progress bar for session
- [ ] 4.4 Verify progress bar persists across page refresh
