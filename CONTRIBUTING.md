# Contributing to MediVita

Create a focused branch, keep changes scoped, and never commit credentials or health data. For local setup, follow the commands in the README.

Before opening a pull request:

1. Run `npm run lint`, `npm run typecheck`, `npm test`, and `npm run build` in `frontend/`.
2. Run `ruff check .` and `pytest` in `backend/`.
3. Explain user-facing changes and include screenshots when layout changes.
4. Preserve the established design tokens, safety language, API shapes, and demo-mode behavior.

Use conventional, descriptive commit messages. Report security issues privately as described in `SECURITY.md`.
