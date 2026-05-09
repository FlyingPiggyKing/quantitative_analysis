# Project Context

This is a quantitative analysis project.

## Tech Stack

- **Dependency Management**: uv (Python)
- **China A-Stocks**: [Tushare](https://tushare.pro/)
  - API docs: https://tushare.pro/document/2 or `context7: tushare_pro_document`
- **US Stocks**: [FutuAPI](https://openapi.futunn.com/futu-api-doc/)
  - API docs: https://openapi.futunn.com/futu-api-doc/quote/overview.html or `context7: futunnopen/py-futu-api`
  - Local skill installed: `futuapi`

## Backend

- Dependencies are managed in `backend/.venv` (uv virtualenv)
- Use `uv` for Python dependency operations (e.g., `uv pip install`, `uv sync`)
- Run backend from `backend/` directory
