## 1. Modify user message to include today's date

- [x] 1.1 In `analyze_stock_trend()` function, after constructing the user message containing "请分析股票...的未来2周趋势", append today's date using `get_today_date()` in format "（日期: YYYY-MM-DD）"

## 2. Update news search instruction with date-specific prompts

- [x] 2.1 Change the news search instruction from "请使用 search_with_fallback 工具搜索最新新闻，然后结合以上技术数据给出预测" to "请使用 search_with_fallback 工具搜索今天 '{{today_date}}' 最新新闻，再搜索这周的新闻，然后结合以上技术数据给出预测"
- [x] 2.2 Ensure `get_today_date()` is called when building the user message to populate the date placeholder
