## Context

现有系统已有通用的 `stock_trend_agent.py` 和 `TrendPredictionService`，但：
1. 通用 agent 基于六维双轮选股体系设计，不够聚焦机构交易行为
2. 龙虎榜股票点击后跳转至 `/stock/[symbol]` 通用详情页，与普通股票共用页面
3. 现有趋势分析使用共享队列，高并发时可能阻塞

本设计为龙虎榜股票创建独立的机构交易分析 Agent 和专属详情页，参考 `stock_trend_agent.py` 的实现模式，使用 Tushare 数据，整合 LangChain，通过独立队列异步执行。

## Goals / Non-Goals

**Goals:**
- 创建 `institutional_trading_analysis_agent` 基于六维双轮选股体系，聚焦龙虎榜股票的机构交易分析
- Agent System Prompt 存放于 `backend/services/agent_prompts/institutional_trading_analysis_agent.txt`
- 新建 `/stock/dragon-tiger/[symbol]` 页面，仅含 AI 趋势分析模块和立刻分析按钮
- 独立任务队列 `institutional_trading_analysis_task_queue.py`，不阻塞现有 trend prediction 队列
- 整合 LangChain（参考现有 agent 模式）
- 使用 Tushare 获取 A 股数据（不依赖代理）

**Non-Goals:**
- 不修改现有的 `/stock/[symbol]` 页面
- 不创建新的数据库模型，复用现有 `TrendPredictionService` 的存储逻辑
- 不支持 HK/US 市场的机构分析（仅限 A 股龙虎榜）

## Decisions

### 1. Agent 实现：参考 `stock_trend_agent.py` 而非新建

**决策**：参考 `stock_trend_agent.py` 的 DeepAgent + LangChain 模式，创建新的 `institutional_trading_analysis_agent.py`

**理由**：
- 现有 agent 已有完整的模型调用、错误处理、重试逻辑
- 保持 API 和调用模式一致，降低学习成本
- `analyze_stock_trend()` → `analyze_institutional_trading()` 函数签名相似

**替代方案**：
- 从零实现 LangChain Agent → 工作量大，且失去一致性
- 继承现有 agent 类 → 耦合过高，修改现有代码风险大

### 2. 独立任务队列

**决策**：新建 `institutional_trading_analysis_task_queue.py`，使用 ThreadPoolExecutor + UUID 追踪

**理由**：
- 龙虎榜分析可能批量操作，不能阻塞现有的单个股票趋势分析
- 现有 `task_queue.py` 的 `submit_single_analysis_task` 已验证可用
- 队列逻辑简单（提交 → 后台执行 → UUID 查询），直接复用模式

**替代方案**：
- 复用现有 `TaskQueue` → 队列混用，监控困难
- 使用 Celery/RQ → 引入额外依赖，当前场景过于复杂

### 3. 详情页路由：`/stock/dragon-tiger/[symbol]`

**决策**：在 `frontend/src/app/stock/dragon-tiger/[symbol]/page.tsx` 创建新页面

**理由**：
- Next.js App Router 约定，[symbol] 为动态路由
- 独立路径避免与现有 `/stock/[symbol]` 冲突
- DragonTigerList 组件中 Link 替换为 `/stock/dragon-tiger/{ts_code}`

**替代方案**：
- 使用 query param：`/stock/[symbol]?from=dragon-tiger` → 页面复杂度增加，条件分支多
- 在现有页面增加 tab → 修改现有页面，违背不干扰原则

### 4. Agent System Prompt 存放

**决策**：`backend/services/agent_prompts/institutional_trading_analysis_agent.txt`

**理由**：
- 与现有 `stock_trend_agent.py` 中的 `get_system_prompt()` 函数分离
- 方便单独修改 prompt 而不触碰代码
- 与六维双轮选股.md 的内容对应

**替代方案**：
- 存放在数据库 → 运行时修改更灵活，但引入额外依赖
- 硬编码在 Python 文件中 → 修改需代码部署

### 5. 六维双轮选股体系的具体维度

基于 `六维_双轮选股.md` 的内容，取舍后保留核心维度：

1. **资金流向维度**：机构龙虎榜净买入/净卖出、主力资金流向
2. **技术面维度**：K 线形态、MACD、RSI、均线排列
3. **机构行为维度**：上榜原因、机构买卖力道、席位分布
4. **基本面维度**：PE、PB、换手率、市值（来自 Tushare）
5. **情绪维度**：市场整体情绪、资金情绪
6. **趋势维度**：短期（5-10日）、中期（20-60日）趋势判断

### 6. 数据存储：source 字段区分分析类型

**决策**：复用 `TrendPredictionService`，通过 `source` 字段区分 institutional/trend 两种分析类型

**理由**：
- institutional analysis 使用 `source="institutional"` 保存，六维双轮字段
- trend analysis 使用 `source="trend"` 保存，旧三维字段（情绪分析/技术分析/趋势判断）
- retrieval 时同时提取两种格式，确保向后兼容

### 7. DragonTigerList 内联预测显示

**决策**：龙虎榜列表页直接显示 AI 预测结果，无需进入详情页

**理由**：
- 用户可以在列表页快速浏览各股票的机构分析预测
- 与"我的自选"中"AI下周预测"风格保持一致
- 桌面端：日期显示在标题右侧，代码+名称合并为一列，AI预测独占一列靠右显示
- 移动端：显示"AI龙虎"标签，预测图标与价格、涨跌幅并排

**样式规范**：
- 使用 `vt-pred-up`/`vt-pred-down`/`vt-pred-flat` CSS 类（与 AI下周预测 一致）
- 标题使用 `vt-pred-col-header` 样式
- 菱形装饰已移除

## Risks / Trade-offs

| Risk | Mitigation |
|------|------------|
| Agent 分析时间过长（>30s）阻塞线程 | 独立队列 + 前端轮询，超时显示友好错误 |
| Tushare API 限流导致分析失败 | 指数退避重试，参考 `stock_trend_agent.py` 的 MAX_RETRIES=3 |
| 六维双轮选股 Prompt 过于复杂，输出不稳定 | JSON Schema 约束输出格式，预留降级方案（仅返回 trend_direction + confidence） |
| 前端轮询频率过高压垮服务器 | 轮询间隔 3s，参考现有 `AnalysisProgressBar` 模式 |
| 页面刷新丢失分析状态 | 分析结果存入 TrendPredictionService，页面加载时优先展示已保存结果 |

## Open Questions

1. **Agent 输出格式**：六维双轮选股体系的输出结构是否需要与现有 `stock_trend_agent` 完全一致？（建议保持一致以便前端复用 `TrendAnalysisPanel`）
2. **缓存策略**：分析结果是否需要像 `TrendPredictionService` 一样按日期缓存，还是每次都重新分析？
3. **批量分析**：是否需要支持批量分析多个龙虎榜股票？（建议初期仅支持单个股票立即分析）
