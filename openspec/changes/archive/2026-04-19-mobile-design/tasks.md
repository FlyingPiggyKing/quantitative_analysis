## 1. Mobile Base Styles and Viewport

- [x] 1.1 Review and update viewport meta tag in `frontend/src/app/layout.tsx` if needed
- [x] 1.2 Verify global CSS has appropriate mobile base font sizes (16px body minimum)
- [x] 1.3 Add mobile-specific spacing utilities if needed in globals.css

## 2. Index Page Mobile Adaptation

- [x] 2.1 Update main container in `page.tsx` to use full-width layout on mobile (`w-full px-4`)
- [x] 2.2 Modify WatchList component (`WatchList.tsx`) to detect mobile viewport
- [x] 2.3 Create mobile card view layout for watchlist items when `width < 640px`
- [x] 2.4 Style watchlist cards: `rounded-lg p-3 mb-3 min-h-[44px]` with tap feedback
- [x] 2.5 Update PETrendSparkline for mobile (smaller size, no labels)
- [x] 2.6 Make search input full-width on mobile in `page.tsx`

## 3. Stock Detail Page Mobile Adaptation

- [x] 3.1 Update stock header in `stock/[symbol]/page.tsx` to stack vertically on mobile
- [x] 3.2 Modify header valuation metrics to use 2-column grid on mobile
- [x] 3.3 Update StockChart component (`StockChart.tsx`) for mobile height (~250px)
- [x] 3.4 Verify chart touch interactions work on mobile (crosshair, tooltips)

## 4. Indicator Panel Mobile Adaptation

- [x] 4.1 Update IndicatorPanel component (`IndicatorPanel.tsx`) to stack vertically on mobile
- [x] 4.2 Add collapsible accordion behavior for each indicator on mobile
- [x] 4.3 Ensure indicator panels remain 3-column grid at `md:` breakpoint and above

## 5. Trend Analysis Panel Mobile Adaptation

- [x] 5.1 Update TrendAnalysisPanel component (`TrendAnalysisPanel.tsx`) for mobile layout
- [x] 5.2 Make sections collapsible on mobile (Technical, Fundamental, Sentiment stacked)
- [x] 5.3 Add "Show more" expansion for analysis summary text on mobile
- [x] 5.4 Maintain existing layout on desktop/tablet

## 6. Touch Interactions and Polish

- [x] 6.1 Ensure all buttons have 44px minimum touch target
- [x] 6.2 Add visual tap feedback (opacity/scale) on interactive elements
- [ ] 6.3 Test pull-to-refresh behavior on index and stock detail pages
- [x] 6.4 Verify loading skeleton states render correctly on mobile
- [x] 6.5 Test horizontal overflow is eliminated on all pages

## 7. Testing

- [ ] 7.1 Test index page on iPhone Safari (320px width)
- [ ] 7.2 Test stock detail page on iPhone Safari
- [ ] 7.3 Test landscape orientation behavior
- [ ] 7.4 Verify tap targets meet 44px minimum (use iPhone accessibility inspector)
