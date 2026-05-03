## Why

The stock news search prompts need to be more specific about temporal context. Currently the prompts use vague terms like "最新新闻" (latest news) without specifying the exact date. Adding explicit date references will improve the relevance and accuracy of news searches, especially when distinguishing between today's news and this week's news.

## What Changes

1. **User message enhancement**: After the user message containing "请分析股票...的未来2周趋势", append today's date for temporal clarity
2. **News search prompt enhancement**: Change from generic "搜索最新新闻" to "搜索今天 '日期' 最新新闻，再搜索这周的新闻" - explicitly searching today's news and this week's news separately

## Capabilities

### New Capabilities
- `date-specific-news-search`: Capability to perform date-specific news searches with explicit today and week time ranges

### Modified Capabilities
- `stock-news-time-range`: Extend to require two distinct searches - one for today's news with explicit date, and one for this week's news

## Impact

- **Modified files**: Stock trend analysis agent prompts and user message handlers
- **Affected agents**: Stock trend analysis DeepAgent
- **Search behavior**: search_with_fallback will receive more specific date parameters for today and week time ranges
