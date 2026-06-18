## Why

盘面新闻（hourly news summary）目前完全瘫痪，原因是 `backend/services/news_analysis_task_queue.py::_fetch_tushare_news` 调用的 `pro.news(src='sina')` 在当前 Tushare token 下已无权限（积分门槛/试用期已过），导致整点拉不到任何新闻，后续的 AI 摘要、数据库入库、前端展示都跟着空跑。`major_news` 接口在同一 token 下仍然可用、实测一次可拉 800 条，已能覆盖"小时级回顾"的颗粒度（深度长稿反而比短快讯更利于 LLM 总结）。短期先切到 `major_news` 恢复数据流，长篇新闻 30~60 分钟延迟对"回望式"小时摘要影响可接受。

## What Changes

- **修改** `backend/services/news_analysis_task_queue.py::_fetch_tushare_news`：
  - `pro.news(src='sina')` → `pro.major_news(src='', start_date=..., end_date=...)`
  - 字段映射：`datetime` 来源由 `row['datetime']` 改为 `row['pub_time']`（major_news 返回该字段）
  - 移除 `row.get('rel', 0.5) / 100.0` 逻辑，major_news 不存在 `rel` 字段，相关性直接默认 `0.5`
  - `start_date`/`end_date` 用 `YYYYMMDD` 格式（major_news 要求），窗口覆盖当前小时向前 1 小时 + 今日剩余时段以容错跨整点
  - `src` 字段保留回填逻辑（major_news 返回 `src` 字段）
- **不动**：agent (`news_analysis_agent.py`)、入库逻辑 (`_save_hourly_news`)、API (`hourly_news.py`)、调度器 (`run_news_analysis.py`)、前端 — 全部复用。
- **回退预案**：在 `_fetch_tushare_news` 顶部保留一行常量 `NEWS_PROVIDER = "major_news"`，未来如果 `news` 接口恢复，改回一行即可。

## Capabilities

### New Capabilities
无（不引入新能力，仅替换数据源）。

### Modified Capabilities
- `background-analysis-task`: 小时新闻抓取所使用的数据源由 `pro.news` 改为 `pro.major_news`，但任务队列/进度/状态/失败/清理的需求本身不变。**仅在字段映射层面有差异**，不属于 requirement 级别变化，**不列入 Modified Capabilities**（如果审阅认为需要标注可加 `## MODIFIED Requirements` 说明数据源，但不会引入新场景）。

## Impact

- 受影响代码：
  - `backend/services/news_analysis_task_queue.py`（唯一改动点，约 30 行）
- 受影响依赖：
  - `tushare` SDK：新增调用 `pro.major_news`，要求当前 token 仍具有 `major_news` 权限（已确认有）
  - 数据库 schema、入库字段、API 响应 — 零变化
- 受影响运行：
  - 下一整点（如 18:00）调度器触发后，应能正常拉取到长篇新闻并完成 AI 摘要入库
  - 前端 `hourly_news` 页面随数据回填而恢复
- 风险与权衡：
  - major_news 更新较 news 慢（30~60 分钟延迟），小时回顾场景可接受
  - 若用户后续要求"5 分钟内突发新闻入分析"，major_news 不够，需要叠加其他数据源（不在本变更范围）
