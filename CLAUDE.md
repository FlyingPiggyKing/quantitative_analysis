# Project Context

This is a quantitative analysis project.

## Tech Stack

- **Dependency Management**: uv (Python)
- **China A-Stocks**: [Tushare](https://tushare.pro/)
  - API docs: https://tushare.pro/document/2 or `context7: tushare_pro_document`
- **US Stocks**: [FutuAPI](https://openapi.futunn.com/futu-api-doc/)
  - API docs: https://openapi.futunn.com/futu-api-doc/quote/overview.html or `context7: futunnopen/py-futu-api`
  - Local skill installed: `futuapi`

## Data Sources & Units

| Market | API | Currency | Market Cap Unit | Turnover Rate | Money Flow |
|--------|-----|----------|----------------|---------------|------------|
| A-share | Tushare | CNY 元 | `total_mv` in 元 → `/10000` 显示为亿元 | Already a % (e.g., 2.5) | `net_d5_amount` in 万元 → `/10000` 显示为亿元 |
| HK | Futu | HKD | `total_mv` in HKD → `/1e8` 显示为亿HKD | Decimal fraction (<1) → `*100` 显示为% | In HKD → `/1e8` 显示为亿HKD |
| US | Futu | USD | `total_mv` in USD → `/1e8` 显示为亿美元 | Decimal fraction (<1) → `*100` 显示为% | In USD → `/1e8` 显示为亿美元 |

### Common Mistakes

- **HK/US turnover as 0**: Futu returns a decimal (0.025 = 2.5%), Tushare returns a percentage (2.5 = 2.5%). Multiply by 100 for HK/US.
- **HK market cap "0亿"**: Tushare returns 万元, Futu returns HKD dollars. Use `/10000` for A-share, `/1e8` for HK.
- **US market cap too large**: Futu returns USD, not cents. Use `/1e8` 亿美元 directly, do NOT multiply by exchange rate.
- **Money flow sign**: Use `>= 0 ? "+" : "-"` for display; AI context should reflect net flow direction.

## Backend

- Dependencies are managed in `backend/.venv` (uv virtualenv)
- Use `uv` for Python dependency operations (e.g., `uv pip install`, `uv sync`)
- Run backend from `backend/` directory
