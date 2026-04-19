## ADDED Requirements

### Requirement: Mobile Viewport Configuration
The application SHALL include proper mobile viewport meta tag for iPhone display.

#### Scenario: Index page on iPhone
- **WHEN** user visits index page from iPhone (320px-428px width)
- **THEN** page SHALL render without horizontal overflow
- **AND** base font size SHALL be readable without zooming

#### Scenario: Stock detail page on iPhone
- **WHEN** user visits stock detail page from iPhone
- **THEN** page SHALL render without horizontal overflow
- **AND** all content SHALL be accessible via vertical scrolling

### Requirement: Responsive Container Behavior
Containers SHALL adapt to mobile viewport with appropriate padding and max-width.

#### Scenario: Index page container on mobile
- **WHEN** index page renders on mobile
- **THEN** main container SHALL use full width with `px-4` horizontal padding
- **AND** max-width restriction SHALL be removed or set to 100%

#### Scenario: Stock detail header on mobile
- **WHEN** stock detail page renders on mobile
- **THEN** stock header SHALL stack vertically (symbol, price, valuation metrics)
- **AND** valuation metrics SHALL use 2-column grid layout

### Requirement: Typography Scaling
Text sizes SHALL be appropriate for mobile reading without zooming.

#### Scenario: Headings on mobile
- **WHEN** page renders on mobile
- **THEN** main heading (stock symbol) SHALL be `text-2xl` minimum
- **AND** section headings SHALL be `text-lg` minimum

#### Scenario: Body text on mobile
- **WHEN** page renders on mobile
- **THEN** body text SHALL be `text-base` (16px) minimum
- **AND** secondary text (labels, captions) SHALL be `text-sm` minimum

### Requirement: Spacing Adaptation
Vertical spacing between sections SHALL increase on mobile for comfortable touch scanning.

#### Scenario: Section spacing on mobile
- **WHEN** page renders on mobile
- **THEN** spacing between major sections SHALL be `gap-6` or larger
- **AND** padding within sections SHALL be `p-4` minimum

### Requirement: Touch Target Sizing
Interactive elements SHALL meet minimum touch target size for iPhone.

#### Scenario: Button touch targets
- **WHEN** any button renders on mobile
- **THEN** button SHALL have minimum 44x44px touch target
- **AND** spacing between adjacent buttons SHALL be at least 8px

#### Scenario: Watchlist row tap target
- **WHEN** watchlist card renders on mobile
- **THEN** entire card SHALL be tappable
- **AND** card SHALL have visual feedback on tap (opacity or scale change)
