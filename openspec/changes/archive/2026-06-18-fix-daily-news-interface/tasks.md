## 1. 修改数据源调用

- [x] 1.1 在 `backend/services/news_analysis_task_queue.py` 顶部加模块级常量 `NEWS_PROVIDER = "major_news"`
- [x] 1.2 在 `_fetch_tushare_news` 内根据 `NEWS_PROVIDER` 派发：
  - `major_news` 分支：`pro.major_news(src='', start_date=YYYYMMDD, end_date=YYYYMMDD)`
  - `news` 分支（保留回退骨架）：`pro.news(src='sina')`，按原逻辑处理 `rel` 字段
- [x] 1.3 `major_news` 分支内的字段映射：
  - `row.get('datetime')` → 改为 `row.get('pub_time')`，保留对老 `datetime` 字段的 fallback
  - `row.get('rel', 0.5) / 100.0 if row.get('rel') else 0.5` → 直接 `0.5`
  - `row.get('title')` / `row.get('content')[:500]` / `row.get('src', 'unknown')` 保持不变
- [x] 1.4 Python 侧二次过滤：`_run_news_analysis` 改为不传 `minutes`，由 fetch 层根据 `PROVIDER_TIME_WINDOW_MINUTES` 选默认窗口（major_news=24h, news=60min）
- [x] 1.5 异常处理、日志格式（`logger.warning / .info / .error` 文案）保持不变

> **变更（实施中发现，2026-06-11）**：原计划窗口 60min，实测 `major_news` 数据延迟 ~20h，60min 窗口下 0 条新闻通过。新增 `PROVIDER_TIME_WINDOW_MINUTES` 常量，`major_news` 改用 24h 窗口；语义上从"小时摘要"变成"近 24h 重点新闻"，但能保证有数据。

## 2. 本地验证

- [x] 2.1 手动调用 `submit_news_analysis_task()` 一次，等任务结束，确认 task status = completed
  _（TUSHARE_TOKEN 加载自 backend/.env；任务 `d7e1a9df-...` 状态 completed，3/3 进度）_
- [x] 2.2 检查返回的 `news_list` 非空，每条都有 `datetime / title / content / source / relevance` 五个键
  _（真实 API：186 条新闻在过去 24h 命中；每条均有 5 个键；`content` 为空是 `major_news` 接口特征——只有 title，没有正文）_
- [x] 2.3 检查 `hourly_news` 表有新增行，`summary_json.top3_news` 至少有 1 条
  _（新行：`hour_timestamp=2026-06-11-20, created_at=2026-06-11 20:36:56`，`top3_news` 3 条，`market_impact.direction="流出偏多"`，`sector_impact` 6 个板块）_
- [x] 2.4 `curl /api/hourly_news?limit=1` 确认 API 返回 200 且 `market_impact` 不为默认值
  _（`GET /api/hourly_news` 和 `/api/hourly_news/latest` 均返回 200，含完整 top3_news + market_impact + sector_impact）_
- [ ] 2.5 整点观察一次调度（不手动触发），确认 `run_hourly_news_analysis()` 走通整条链路
  _（需等下一个整点；当前服务已确认手动触发 e2e 全通，整点调度器走的是同一条调用链）_

## 3. 文档与回退

- [x] 3.1 在 `NEWS_PROVIDER` 常量处加一行注释：`# 如果 Tushare news 权限恢复，把这里改为 "news" 即可回退`
- [x] 3.2 在 `backend/services/news_analysis_task_queue.py` 的 docstring 或 README（如有）补一句"当前数据源：Tushare major_news"
  _（已写入 `_fetch_tushare_news` docstring：`Current data source: Tushare major_news (long-form, deep coverage).`）_
- [ ] 3.3 暂不在本次提交中创建 Tushare 客服工单；如验证通过后 7 天内 major_news 仍稳定，可考虑写工单确认 news 接口现状
  _（用户动作；待 2.5 验证通过后自行决定）_
