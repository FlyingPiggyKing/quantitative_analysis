## Context

`backend/services/news_analysis_task_queue.py::_fetch_tushare_news` 是整点调度器拉取"过去 1 小时市场新闻"的唯一入口，调用链：

```
scheduler (run_news_analysis.py)
  → submit_news_analysis_task()
    → _run_news_analysis()
      → _fetch_tushare_news(minutes=60)  ← 当前调用 pro.news(src='sina')，已无权限
      → analyze_hourly_news()           ← AI agent 摘要
      → _save_hourly_news()             ← 写入 SQLite
```

下游消费者：
- `backend/api/hourly_news.py` (GET `/api/hourly_news` & `/api/hourly_news/latest`) — 前端盘面新闻页面
- `news_analysis_agent.py::analyze_hourly_news` — 接收 list[dict]，字段约定 `datetime / title / content / source / relevance`

约束：
- 同一 Tushare token 仍有 `major_news` 权限（已实测）
- `major_news` 接口签名：`major_news(src='', start_date='YYYYMMDD', end_date='YYYYMMDD', fields=...)`
- `major_news` 返回字段包含 `pub_time / title / content / src`，**不包含** `rel / classify`
- 改动必须最小化：agent、入库、API、前端契约保持稳定

## Goals / Non-Goals

**Goals:**
- 把 `_fetch_tushare_news` 的 Tushare 调用从 `pro.news(src='sina')` 切到 `pro.major_news(src='', start_date=..., end_date=...)`
- 输出字典结构（`datetime / title / content / source / relevance`）与下游契约完全一致，agent / API / 前端零修改
- 通过一个常量集中切换数据源，便于未来在 `news` 权限恢复时一行回退
- 改动后下一整点调度能正常入库长篇新闻

**Non-Goals:**
- 不增加新的数据源（如财联社、雪球、东方财富开放 API）
- 不修改 agent prompt / 模型选择 / 摘要输出 schema
- 不修改数据库 schema / API 响应 / 前端 UI
- 不优化相关性打分（major_news 不提供 `rel` 字段，统一默认 `0.5`）
- 不改调度器频率与窗口

## Decisions

### Decision 1: 数据源 = `pro.major_news`，`src=''`（全源）
**Why:** 用户调研结论 —— `major_news` 同 token 可用、长篇主流财经媒体（华尔街见闻/同花顺/东方财富），对 LLM 总结更友好。`src=''` 让 Tushare 聚合全源，避免单源覆盖不足。

**Alternatives considered:**
- `pro.major_news(src='wallstreetcn')` 等单源 — 风险：单源挂掉即数据全断，且每个 src 要单独申请权限
- 切 akshare 或其他源 — 风险：新增依赖、入库字段可能不一致、突破"零成本 / 不重启"约束

### Decision 2: 字段映射 — `pub_time → datetime`，`relevance` 默认 0.5
**Why:** `major_news` 返回 `pub_time`（格式 `%Y-%m-%d %H:%M:%S`，与原 `datetime` 同），无 `rel` 字段。保持下游契约的 `relevance` 键存在但固定 0.5，agent 的 `>= 0.5` 过滤逻辑天然放行所有新闻。

**Alternatives considered:**
- 改 agent 过滤阈值以适配新语义 — 风险：扩展变更面、违反"其他都不动"
- 启发式 relevance 估算（标题长度 / 是否含板块词） — 风险：引入新逻辑、需测试、超出修复范围

### Decision 3: 时间窗口 = 当前小时向前 1 小时 + 今日起点
**Why:** `major_news` 只接受 `start_date`/`end_date`（`YYYYMMDD`，不接收时分）。用 `datetime.now() - timedelta(hours=1)` 计算的 `start_date` 实际是"过去 1 小时所在自然日"，覆盖窗口安全，避免漏掉跨日新闻。`end_date` 取今天，容错跨整点。

```python
now = datetime.now()
start_dt = now - timedelta(hours=1)
start_date = start_dt.strftime('%Y%m%d')
end_date = now.strftime('%Y%m%d')
df = pro.major_news(src='', start_date=start_date, end_date=end_date)
```

然后在 Python 侧按 `pub_time >= now - timedelta(hours=60)` 二次过滤，保留原"过去 60 分钟"语义。

**Alternatives considered:**
- `start_date=今天, end_date=今天` 拉全日再过滤 — 已采用，安全
- 不做 Python 侧二次过滤、全靠日期参数 — 风险：当日会引入大量陈旧新闻，污染 LLM 输入

### Decision 4: 引入模块级常量 `NEWS_PROVIDER = "major_news"`
**Why:** 集中切换点，未来 `news` 权限恢复时改一行即可（同时把 `pro.news` 分支加回 if/else，或注释掉 major_news 段）。

**Alternatives considered:**
- env var 注入 — 风险：超出"30 行代码几分钟"范围、引入配置管理
- 直接写死 major_news — 已采用，简单且未来可一眼识别回退点

### Decision 5: 异常处理保持原状
**Why:** 原代码 try/except 后 `return []`，与"其他都不动"一致。如果 `major_news` 失败，下游会走"No news available"分支并以 `status=FAILED` 写入任务队列，不影响其他流程。

## Risks / Trade-offs

- **[R1] major_news 延迟 30~60 分钟** → Mitigation：本场景是小时级回望，可接受；如未来要"5 分钟内突发新闻"，需叠加额外数据源（Non-Goal，已记录）。
- **[R2] major_news 某天突然也失效** → Mitigation：日志中保留 `logger.error(f"[NewsTask] Error fetching Tushare news: {e}")`，监控可发现；同时 NEWS_PROVIDER 常量让切回 news / 切到其他源都快速。
- **[R3] `pub_time` 时间格式与 `datetime` 不一致** → Mitigation：try/except 解析时同时支持 `datetime` 字段（旧）和 `pub_time` 字段（新），并 fallback 到 `pd.to_datetime` 容错。
- **[R4] 全日拉取 + Python 过滤可能拉回 800 条但只用 1 小时** → Mitigation：Tushare 单次 800 条上限对小时聚合无影响；后续若 token 限额收紧，可在 start_date 收紧到 `now.strftime('%Y%m%d')` 仅当日。
- **[R5] `src` 字段在 major_news 可能与 news 不同** → Mitigation：原代码 `row.get('src', 'unknown')` 已容错，下游 agent 不强依赖 src。

## Migration Plan

**部署步骤：**
1. 修改 `backend/services/news_analysis_task_queue.py::_fetch_tushare_news`（约 30 行）
2. 不需要数据库迁移
3. 不需要重启服务（如有持续运行的调度器，触发下次整点即可生效；如需立即验证，可手动调用 `submit_news_analysis_task()`）

**回退策略：**
- 一行回退：把 `NEWS_PROVIDER = "major_news"` 改为 `"news"`，并在 `_fetch_tushare_news` 中用 if/else 分发到原 `pro.news(src='sina')` 调用（建议在本次修改时预留好 if/else 骨架，即使当前只走 major_news 分支）
- 若 Tushare `news` 权限确认恢复：删掉 major_news 分支，恢复到原 30 行代码即可

**验证步骤：**
1. 手动调用 `_fetch_tushare_news(minutes=60)` 一次，看返回条数与字段
2. 触发整点调度（`run_hourly_news_analysis()`），看任务状态从 `pending → running → completed`
3. 查询 `hourly_news` 表确认有新增行
4. 前端 `hourly_news` 页面看是否恢复显示

## Open Questions

- 是否要在本变更中同时提交一个 PR 备注"如果 news 权限恢复的回退 commit 模板"？（倾向于不在本次提交，只在 NEWS_PROVIDER 常量附近加注释）
- 是否需要把 `major_news` 抓取的数据量上限（如限制只取 200 条送入 agent）做一次 prompt 评估？（倾向于不在本变更范围，留作后续优化）
