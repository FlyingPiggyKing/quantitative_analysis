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

## Common Mistakes

- **HK/US turnover as 0**: Futu returns a decimal (0.025 = 2.5%), Tushare returns a percentage (2.5 = 2.5%). Multiply by 100 for HK/US.
- **HK market cap "0亿"**: Tushare returns 万元, Futu returns HKD dollars. Use `/10000` for A-share, `/1e8` for HK.
- **US market cap too large**: Futu returns USD, not cents. Use `/1e8` 亿美元 directly, do NOT multiply by exchange rate.
- **Money flow sign**: Use `>= 0 ? "+" : "-"` for display; AI context should reflect net flow direction.

## Backend

- Dependencies are managed in `backend/.venv` (uv virtualenv)
- Use `uv` for Python dependency operations (e.g., `uv pip install`, `uv sync`)
- Run backend from `backend/` directory


# Coding Behaviour Guidelines

Behavioral guidelines to reduce common LLM coding mistakes. Merge with project-specific instructions as needed.

**Tradeoff:** These guidelines bias toward caution over speed. For trivial tasks, use judgment.

## 1. Think Before Coding

**Don't assume. Don't hide confusion. Surface tradeoffs.**

Before implementing:
- State your assumptions explicitly. If uncertain, ask.
- If multiple interpretations exist, present them - don't pick silently.
- If a simpler approach exists, say so. Push back when warranted.
- If something is unclear, stop. Name what's confusing. Ask.

## 2. Simplicity First

**Minimum code that solves the problem. Nothing speculative.**

- No features beyond what was asked.
- No abstractions for single-use code.
- No "flexibility" or "configurability" that wasn't requested.
- No error handling for impossible scenarios.
- If you write 200 lines and it could be 50, rewrite it.

Ask yourself: "Would a senior engineer say this is overcomplicated?" If yes, simplify.

## 3. Surgical Changes

**Touch only what you must. Clean up only your own mess.**

When editing existing code:
- Don't "improve" adjacent code, comments, or formatting.
- Don't refactor things that aren't broken.
- Match existing style, even if you'd do it differently.
- If you notice unrelated dead code, mention it - don't delete it.

When your changes create orphans:
- Remove imports/variables/functions that YOUR changes made unused.
- Don't remove pre-existing dead code unless asked.

The test: Every changed line should trace directly to the user's request.

## 4. Goal-Driven Execution

**Define success criteria. Loop until verified.**

Transform tasks into verifiable goals:
- "Add validation" → "Write tests for invalid inputs, then make them pass"
- "Fix the bug" → "Write a test that reproduces it, then make it pass"
- "Refactor X" → "Ensure tests pass before and after"

For multi-step tasks, state a brief plan:
```
1. [Step] → verify: [check]
2. [Step] → verify: [check]
3. [Step] → verify: [check]
```

Strong success criteria let you loop independently. Weak criteria ("make it work") require constant clarification.

---

**These guidelines are working if:** fewer unnecessary changes in diffs, fewer rewrites due to overcomplication, and clarifying questions come before implementation rather than after mistakes.

