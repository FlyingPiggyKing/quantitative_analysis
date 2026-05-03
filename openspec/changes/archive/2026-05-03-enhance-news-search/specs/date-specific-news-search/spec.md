## ADDED Requirements

### Requirement: Date-specific news search prompts
The stock trend analysis agent prompts SHALL include explicit date references when searching for news, using two distinct time ranges.

#### Scenario: User message with date for 2-week trend analysis
- **WHEN** user submits message containing "请分析股票" and "的未来2周趋势"
- **THEN** the processed message SHALL append "（日期: YYYY-MM-DD）" where YYYY-MM-DD is today's date from `get_today_date()`

#### Scenario: Today's news search with explicit date
- **WHEN** agent searches for latest news using search_with_fallback
- **THEN** the search instruction SHALL be "请使用 search_with_fallback 工具搜索今天 'YYYY-MM-DD' 最新新闻"
- **AND** YYYY-MM-DD SHALL be today's date

#### Scenario: Week news search after today's news
- **WHEN** agent completes today's news search
- **THEN** agent SHALL follow with "再搜索这周的新闻" instruction
- **AND** this search SHALL use time_range="week" for broader context

### Requirement: Combined news search instruction format
The news search instruction SHALL combine both today's and week's search in a single coherent instruction.

#### Scenario: Full news search instruction
- **WHEN** agent prepares news search instruction
- **THEN** instruction SHALL be: "请使用 search_with_fallback 工具搜索今天 'YYYY-MM-DD' 最新新闻，再搜索这周的新闻，然后结合以上技术数据给出预测"
- **AND** today's date SHALL be formatted as YYYY-MM-DD
- **AND** agent SHALL perform two sequential searches before making prediction
