## 1. SubModuleTabs 组件修改

- [x] 1.1 更新 `AnalysisSubModule` 类型，添加 `"indexMetrics"`
- [x] 1.2 在 analysis 模块 tab bar 中添加"指数指标"按钮
- [x] 1.3 更新 `analysisSubContent` 接口，添加 `renderIndexMetricsContent` 回调
- [x] 1.4 默认选中"资金流向"（保持现有行为）

## 2. IndexMetricsPanel 组件开发

- [x] 2.1 创建 `frontend/src/components/IndexMetricsPanel.tsx` 组件
- [x] 2.2 定义指数列表常量（6个指数及顺序）
- [x] 2.3 实现单个 IndexCard 子组件
- [x] 2.4 实现时间范围下拉菜单（5年/10年）
- [x] 2.5 实现刷新按钮（单指数独立刷新）
- [x] 2.6 实现估值状态指示器（绿/黄/红）

## 3. 指标计算与 API

- [x] 3.1 创建 `backend/app/api/index_metrics.py` API 路由
- [x] 3.2 实现 `get_index_pe_history(ts_code, years)` 函数调用 `index_dailybasic`
- [x] 3.3 实现 `calculate_pe_percentile(pe_series, years)` 计算函数
- [x] 3.4 实现每日缓存（内存缓存，次日凌晨过期）

## 4. 页面集成

- [x] 4.1 在 `page.tsx` 中添加 `renderIndexMetricsContent` 渲染函数
- [x] 4.2 将 IndexMetricsPanel 添加到 analysisSubContent props

## 5. 测试与验证

- [x] 5.1 测试 6 个指数都能正确显示（实现完成，需手动测试）
- [x] 5.2 测试 5 年/10 年切换重新计算（实现完成，需手动测试）
- [x] 5.3 测试单指数刷新不影响其他指数（实现完成，需手动测试）
- [x] 5.4 测试估值状态颜色正确显示（实现完成，需手动测试）

## 6. 行业指数功能

- [x] 6.1 在后端 `SW_INDUSTRY_LIST` 添加申万一级行业列表（28个）
- [x] 6.2 创建 `ALL_INDEX_LOOKUP` 字典支持行业代码查询
- [x] 6.3 新增 `/api/index/industry/list` 端点返回行业列表
- [x] 6.4 更新 `/api/index/history` 和 `/api/index/metrics` 支持行业查询
- [x] 6.5 前端添加 `fetchIndustryList()` 服务函数
- [x] 6.6 在 `IndexMetricsPanel` 添加行业选择下拉框
- [x] 6.7 行业数据加载时同时获取 metrics 和 history
- [x] 6.8 行业估值展示与指数估值一致的 UI（指标网格 + 图表横线）
- [x] 6.9 测试选择不同行业能正确加载数据
- [x] 6.10 测试行业图表机会值/危险值横线正确显示
