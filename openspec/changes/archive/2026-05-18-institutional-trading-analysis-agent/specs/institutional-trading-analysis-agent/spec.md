# institutional-trading-analysis-agent

## ADDED Requirements

### Requirement: Agent shall analyze institutional trading behavior for Dragon Tiger List stocks

The `institutional_trading_analysis_agent` SHALL use the six-dimensional dual-wheel stock selection methodology (六维双轮选股体系) to analyze A-share stocks appearing on the Dragon Tiger List (龙虎榜). The agent SHALL accept a stock symbol as input and return structured analysis including trend direction, confidence, and institutional trading insights.

#### Scenario: Agent returns valid analysis for a Dragon Tiger List stock
- **WHEN** User clicks "立刻分析" on a Dragon Tiger List stock detail page
- **THEN** System SHALL submit analysis to background queue and return a task_id
- **THEN** System SHALL poll task status until completion
- **THEN** System SHALL display analysis results including trend_direction, confidence, and institutional trading insights

#### Scenario: Agent requires authentication for analysis
- **WHEN** Unauthenticated user clicks "立刻分析"
- **THEN** System SHALL show authentication modal
- **THEN** System SHALL NOT proceed with analysis

#### Scenario: Agent handles Tushare API failure gracefully
- **WHEN** Tushare API returns an error or times out
- **THEN** Agent SHALL retry up to 3 times with exponential backoff
- **THEN** If all retries fail, Agent SHALL return error result with trend_direction="neutral" and confidence=0

#### Scenario: Agent output follows structured JSON schema
- **WHEN** Agent completes analysis successfully
- **THEN** Response SHALL include `trend_direction` (enum: "up", "down", "neutral")
- **THEN** Response SHALL include `confidence` (integer 0-100)
- **THEN** Response SHALL include `summary` (string, Chinese text)
- **THEN** Response SHALL include `情绪分析`, `技术分析`, `趋势判断` blocks when available
- **THEN** Response SHALL be compatible with existing `TrendAnalysisPanel` frontend component

### Requirement: Agent shall integrate with LangChain for orchestration

The `institutional_trading_analysis_agent` SHALL use LangChain's DeepAgent or equivalent pattern for LLM orchestration, similar to the existing `stock_trend_agent.py` implementation.

#### Scenario: Agent uses ChatOpenAI model with MiniMax API
- **WHEN** Agent is invoked
- **THEN** Agent SHALL use `ChatOpenAI` with `openai_api_base="https://api.minimax.chat/v1"`
- **THEN** Agent SHALL use model configured via environment variable `MINIMAX_API_KEY`

#### Scenario: Agent uses system prompt from external file
- **WHEN** Agent is initialized
- **THEN** System prompt SHALL be loaded from `backend/services/agent_prompts/institutional_trading_analysis_agent.txt`
- **THEN** Today's date SHALL be injected into the system prompt at runtime

#### Scenario: Agent provides data context from Tushare
- **WHEN** Agent is called with a stock symbol
- **THEN** System SHALL fetch K-line data (100 days), valuation data, money flow data, and financial fundamentals
- **THEN** Data SHALL be formatted as context string and passed to the LLM

### Requirement: Agent shall use independent task queue for non-blocking execution

The analysis SHALL be executed in a background thread pool to avoid blocking the server's main processes.

#### Scenario: Analysis runs in background thread pool
- **WHEN** User submits analysis request
- **THEN** Request SHALL be queued in `InstitutionalTradingAnalysisTaskQueue`
- **THEN** API SHALL return immediately with task_id
- **THEN** Client SHALL poll for task completion

#### Scenario: Task queue supports concurrent execution
- **WHEN** Multiple analysis requests arrive simultaneously
- **THEN** TaskQueue SHALL process up to 3 analyses concurrently (max_workers=3)
- **THEN** Each task SHALL be tracked independently via UUID

### Requirement: Agent shall analyze institutional trading dimensions

The agent SHALL analyze the following six dimensions based on 六维双轮选股 methodology:

#### Scenario:资金流向维度 analysis
- **WHEN** Agent performs analysis
- **THEN** Agent SHALL consider Dragon Tiger List net buy/sell amounts (机构龙虎榜净买入/净卖出)
- **THEN** Agent SHALL consider main force money flow (主力资金流向, 5-day net inflow)

#### Scenario:技术面维度 analysis
- **WHEN** Agent performs analysis
- **THEN** Agent SHALL analyze K-line patterns, MACD signals (golden/death cross)
- **THEN** Agent SHALL analyze RSI zones (overbought >80, oversold <20)
- **THEN** Agent SHALL analyze MA positioning (price vs MA5, MA20)

#### Scenario:机构行为维度 analysis
- **WHEN** Agent performs analysis
- **THEN** Agent SHALL consider reason for appearing on Dragon Tiger List (上榜原因)
- **THEN** Agent SHALL consider institutional buy/sell strength (机构买卖力道)
- **THEN** Agent SHALL consider seat distribution if available

#### Scenario:基本面维度 analysis
- **WHEN** Agent performs analysis
- **THEN** Agent SHALL consider PE (TTM), PB, turnover rate, market cap
- **THEN** Agent SHALL consider financial metrics (EPS, ROE, profit margins, growth rates)

#### Scenario:情绪维度 analysis
- **WHEN** Agent performs analysis
- **THEN** Agent SHALL consider overall market sentiment
- **THEN** Agent SHALL consider capital market sentiment

#### Scenario:趋势维度 analysis
- **WHEN** Agent performs analysis
- **THEN** Agent SHALL provide short-term trend (5-10 days) assessment
- **THEN** Agent SHALL provide medium-term trend (20-60 days) assessment
