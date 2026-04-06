## 1. Project Setup

- [x] 1.1 Initialize FastAPI backend project structure
- [x] 1.2 Configure uv for Python dependency management
- [x] 1.3 Create Next.js frontend project
- [x] 1.4 Setup .gitignore and remove sensitive files from version control

## 2. Backend - Core Infrastructure

- [x] 2.1 Configure python-dotenv for .env loading
- [x] 2.2 Implement Tushare token loading from environment
- [x] 2.3 Create FastAPI app with CORS middleware
- [x] 2.4 Setup API router structure under /api/stock prefix

## 3. Backend - Stock Data APIs

- [x] 3.1 Implement stock info endpoint (`GET /api/stock/{symbol}`)
- [x] 3.2 Implement K-line data endpoint (`GET /api/stock/{symbol}/kline`)
- [x] 3.3 Implement realtime quote endpoint (`GET /api/stock/{symbol}/realtime`)
- [x] 3.4 Implement indicators endpoint (`GET /api/stock/{symbol}/indicators`)
- [x] 3.5 Add health check endpoint (`GET /health`)

## 4. Backend - Technical Indicator Calculations

- [x] 4.1 Implement MACD calculation (12, 26, 9 parameters)
- [x] 4.2 Implement RSI calculation (6, 12, 24 periods)
- [x] 4.3 Implement Moving Average calculation (5, 10, 20, 60 days)

## 5. Frontend - Core Pages

- [x] 5.1 Create home page with stock search input
- [x] 5.2 Create stock detail page (`/stock/[symbol]`)
- [x] 5.3 Implement navigation between pages
- [x] 5.4 Add loading and error states

## 6. Frontend - Chart Components

- [x] 6.1 Integrate lightweight-charts library
- [x] 6.2 Create StockChart component with candlestick series
- [x] 6.3 Add volume histogram overlay
- [x] 6.4 Fix date format conversion (yyyy-mm-dd for lightweight-charts)

## 7. Frontend - Indicator Display

- [x] 7.1 Create IndicatorPanel component
- [x] 7.2 Display MACD values (DIF, DEA, HIST)
- [x] 7.3 Display RSI values (RSI6, RSI12, RSI24)
- [x] 7.4 Display MA values (MA5, MA10, MA20, MA60)

## 8. Documentation & Configuration

- [x] 8.1 Create .env.example with Tushare token placeholder
- [x] 8.2 Update README.md with setup instructions
- [x] 8.3 Create start-backend.sh script
- [x] 8.4 Push initial commit to GitHub public repository

## 9. Verification & Testing

- [x] 9.1 Test stock info API for 300750 (宁德时代)
- [x] 9.2 Test K-line data API with date format validation
- [x] 9.3 Test technical indicators calculation
- [x] 9.4 Verify frontend loads and displays chart correctly
