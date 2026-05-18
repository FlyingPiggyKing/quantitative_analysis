## Why

龙虎榜（机构龙虎榜）展示了个股交易中机构投资者的买卖行为，是短线交易的重要参考指标。目前系统已有通用趋势分析，但缺少针对龙虎榜股票的机构交易行为分析能力。用户需要一个专门的agent来分析龙虎榜股票的机构交易特征，结合六维双轮选股体系给出机构视角的选股建议。

## What Changes

- **新增 institutional_trading_analysis_agent**：基于 LangChain 的专业机构交易分析 Agent，使用 Tushare 数据
- **新增龙虎榜股票详情页**：独立于现有 `/stock/[symbol]` 页面，仅包含 AI 趋势分析和立刻分析按钮
- **新增机构交易分析 API**：支持异步队列执行，不阻塞服务器
- **新增 Agent System Prompt**：存放在 `backend/services/agent_prompts/` 目录

## Capabilities

### New Capabilities

- `institutional-trading-analysis-agent`: 基于六维双轮选股体系，专门分析龙虎榜股票的机构买卖行为、技术面、资金流向等维度，给出机构视角的选股建议。整合 LangChain，支持异步队列执行。
- `dragon-tiger-stock-detail-page`: 龙虎榜股票专属详情页，仅包含 AI 趋势分析模块和立刻分析按钮，数据仅限 A 股。

### Modified Capabilities

- **DragonTigerList 组件升级**：龙虎榜列表新增 AI龙虎预测 列，实时显示各股票的机构分析预测结果（图标+置信度）
- **主页布局调整**：登录用户可在自选股下方看到龙虎榜模块

## Impact

### 新增文件

- `backend/services/institutional_trading_analysis_agent.py` — Agent 实现
- `backend/services/agent_prompts/institutional_trading_analysis_agent.txt` — System Prompt
- `backend/services/institutional_trading_analysis_task_queue.py` — 独立任务队列
- `backend/api/institutional_trading_analysis.py` — API 路由
- `frontend/src/app/stock/dragon-tiger/[symbol]/page.tsx` — 详情页
- `frontend/src/components/InstitutionalAnalysisPanel.tsx` — 六维分析面板组件
- `frontend/src/services/institutionalTradingAnalysis.ts` — 前端调用服务

### 修改文件

- `frontend/src/components/DragonTigerList.tsx` — 新增 AI龙虎预测 列、日期显示在标题右侧、代码名称合并列、主页同时显示给登录用户
- `frontend/src/app/page.tsx` — 登录用户显示龙虎榜模块
- `backend/services/trend_prediction_service.py` — 支持 source 字段区分 institutional/trend 分析

### 依赖

- LangChain（整合现有）
- Tushare（A 股数据）
- TaskQueue（独立队列，不复用现有 trend prediction 队列）
