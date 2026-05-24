# sector-money-flow-sankey Specification

## Purpose

板块资金流向Sankey图模块：展示过去5个交易日Top 8净流入板块的资金流向Sankey图，作为"投资分析"下的新子模块。

## ADDED Requirements

### Requirement: 板块资金流向API返回正确数据结构
系统 SHALL 通过Tushare `moneyflow_ind_dc` 接口获取板块日级别资金流向数据，并返回包含并集板块列表、每日Top 8及净流入金额的结构化数据。

#### Scenario: 成功获取5天数据
- **WHEN** 前端调用 `/api/stock/sector-money-flow?days=5&top_n=8`
- **THEN** API返回包含 `sectors`（所有出现板块）、`daily_top`（每日Top8列表）、`net_amounts`（每日各板块净流入额）的JSON
- **AND** 数据为最近5个交易日

#### Scenario: 无数据时返回空结构
- **WHEN** Tushare API返回空数据或接口调用失败
- **THEN** API返回 `{ "sectors": [], "daily_top": {}, "net_amounts": {}, "error": "..." }`
- **AND** 前端展示"暂无数据"提示

### Requirement: Sankey图垂直布局
Sankey图 SHALL 采用垂直布局，最新日期位于上方，最老日期位于下方。

#### Scenario: 垂直排列日期
- **WHEN** Sankey图渲染时
- **THEN** 日期从新到旧依次排列：最新在上，最老在下
- **AND** 日期标签显示在对应横截面旁

### Requirement: 每日板块按net_amount排序
每个日期截面内，板块 SHALL 按净流入金额从大到小从左向右排列。

#### Scenario: 左至右按净流入排序
- **WHEN** 某日有多个板块时
- **THEN** net_amount最大的板块位于该日期截面的最左侧
- **AND** net_amount最小的板块位于该日期截面的最右侧

### Requirement: Sankey流量连线表示资金流转
相邻日期截面间 SHALL 通过U型折线连接，表示资金在板块间的流转关系。

#### Scenario: 共同板块间连线
- **WHEN** 连续两日同时出现在Top 8的板块
- **THEN** 用U型折线连接这两日的同一板块
- **AND** 折线宽度反映净流入金额的相对大小

#### Scenario: 跨日板块流量估算
- **WHEN** 两日Top 8板块不完全相同时
- **THEN** 共同板块保留直接连线
- **AND** 消失/新增板块的流量按比例分配到相邻板块（示意性质）

### Requirement: 板块去重（罗马数字后缀）
系统 SHALL 合并具有相同基础名称但不同罗马数字后缀的板块。

#### Scenario: 合并Ⅱ、Ⅲ等变体
- **WHEN** Tushare返回如"家电零部件Ⅱ"和"家电零部件Ⅲ"
- **THEN** 合并为基础名称"家电零部件"，金额相加
- **AND** 合并后的数据用于排序和连接

### Requirement: 子模块标签显示
"资金流向" SHALL 作为"投资分析"模块下的一个子模块标签显示，默认选中。

#### Scenario: 显示资金流向Tab
- **WHEN** 用户选择"投资分析"模块
- **THEN** 底部Tab栏显示"资金流向"和"机构龙虎榜"两个选项
- **AND** "资金流向"为默认选中项

#### Scenario: 切换到机构龙虎榜子模块
- **WHEN** 用户点击"机构龙虎榜"Tab
- **THEN** 页面展示机构龙虎榜组件

### Requirement: Sankey图点击高亮交互
Sankey图 SHALL 支持点击折线或图例高亮对应板块。

#### Scenario: 点击折线高亮板块
- **WHEN** 用户点击图中的U型折线
- **THEN** 对应板块高亮显示，其他板块弱化
- **AND** 折线透明度：选中0.95，其他0.1

#### Scenario: 点击图例项切换高亮
- **WHEN** 用户点击底部图例中的板块项
- **THEN** 切换该板块的高亮状态

#### Scenario: 清除高亮
- **WHEN** 用户点击图中的空白区域
- **THEN** 清除所有高亮，恢复正常显示

### Requirement: 底部图例显示累计净流入
底部图例 SHALL 显示每个板块的5日累计净流入金额。

#### Scenario: 图例内容
- **WHEN** 图例渲染时
- **THEN** 显示每个有跨日连接线的板块
- **AND** 累计金额 = Σ(该板块5日net_amount)
- **AND** 按累计金额降序排列
- **AND** 正数显示绿色，负数显示红色

### Requirement: 资金流向模块样式
资金流向子模块 SHALL 使用与"机构龙虎榜"一致的样式（无panel边框，仅Tab栏+内容）。

#### Scenario: 无边框布局
- **WHEN** "资金流向"子模块被选中
- **THEN** Tab栏下方直接显示Sankey图，无额外vt-panel容器
- **AND** 日期显示在Tab栏右侧

### Requirement: 响应式布局
系统 SHALL 在移动端和桌面端提供适配的布局。

#### Scenario: 移动端布局
- **WHEN** 屏幕宽度 < 640px
- **THEN** 减少padding、条形高度、字体大小
- **AND** 调整条形区域和标签区域的比例
