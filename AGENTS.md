# Folio — Agent Context

> Single-user stock portfolio tracker with weighted average cost P&L accounting.

## Tech Stack
- **Backend:** Python 3.12+, FastAPI, SQLModel, SQLite, yfinance
- **Frontend:** React 19, TypeScript 6, Vite 8, Tailwind CSS v4, TanStack Query, Recharts
- **Testing:** pytest (backend), Vitest (frontend unit), Playwright (frontend E2E)

## Project Structure
- `backend/app/` — FastAPI application
  - `models.py` — SQLModel table definitions
  - `schemas.py` — Pydantic request/response schemas
  - `routers/` — API route handlers (accounts, assets, transactions, portfolio)
  - `services/` — Business logic (holdings_service, transaction_service, portfolio, price_service)
- `frontend/src/` — React application
  - `api/` — Axios client and endpoint wrappers
  - `components/` — UI components (layout, dashboard, transactions, ui)
  - `hooks/` — TanStack Query custom hooks
  - `pages/` — Route pages (Dashboard, Transactions, Holdings, Insights)
  - `types/` — TypeScript interfaces
  - `test/` — Test setup and utilities
- `frontend/e2e/` — Playwright E2E tests

## Coding Conventions
- Use `datetime.now(timezone.utc)` not `datetime.utcnow()`
- All API routes prefixed with `/api/v1`
- Backend errors return `{"detail": "message"}` with appropriate HTTP status
- Frontend uses TanStack Query for all server state — no local state for API data
- Tailwind CSS v4 with `@import "tailwindcss"` — no v3 config files
- `float` for monetary values (acceptable for single-user scope)

## Quick Commands

| Action | Command |
|--------|---------|
| Backend tests | `cd backend && source .venv/bin/activate && python -m pytest -v` |
| Backend server | `cd backend && source .venv/bin/activate && uvicorn app.main:app --reload` |
| Frontend dev | `cd frontend && npm run dev` |
| Frontend build | `cd frontend && npm run build` |
| Frontend lint | `cd frontend && npm run lint` |
| Frontend type check | `cd frontend && npx tsc --noEmit` |
| Frontend unit tests | `cd frontend && npm run test` |
| Frontend E2E tests | `cd frontend && npm run test:e2e` |
| **Full verification** | `bash scripts/verify.sh` |
| **Full + E2E** | `bash scripts/verify.sh --e2e` |

## Development Workflow

This project uses a **skill-based workflow**. Instead of separate agent personas, there are skill files that define _what to do_ at each phase. Work happens in a single session.

### How to Use

| Phase | What to Say | Skill | Recommended Model |
|-------|-------------|-------|-------------------|
| **Plan** | "Read `.agents/skills/plan/SKILL.md` and plan: _\<feature\>_" | [plan](/.agents/skills/plan/SKILL.md) | Opus (strong reasoning) |
| **Implement** | "Read `.agents/skills/develop/SKILL.md` and implement `.agents/plans/<name>.md`" | [develop](.agents/skills/develop/SKILL.md) | Flash (fast, cheap) |
| **Verify** | "Read `.agents/skills/verify/SKILL.md` and verify the current state" | [verify](.agents/skills/verify/SKILL.md) | Flash |

### Workflow Lifecycle

```
Plan (Opus) → You approve → Implement + Verify + Commit (Flash) → You push
```

The implementation phase includes automated verification via `scripts/verify.sh`. The agent does NOT push — you always push manually.

## Skills Reference

| Skill | Guide | Covers |
|-------|-------|--------|
| Plan | [`.agents/skills/plan/SKILL.md`](.agents/skills/plan/SKILL.md) | Feature planning, spec writing, plan format |
| Develop | [`.agents/skills/develop/SKILL.md`](.agents/skills/develop/SKILL.md) | Implementation, verification gate, git commit |
| Verify | [`.agents/skills/verify/SKILL.md`](.agents/skills/verify/SKILL.md) | Standalone build/test verification |
| Python Backend | [`.agents/skills/python-backend/SKILL.md`](.agents/skills/python-backend/SKILL.md) | FastAPI, SQLModel, pytest patterns |
| React Frontend | [`.agents/skills/react-frontend/SKILL.md`](.agents/skills/react-frontend/SKILL.md) | React, TypeScript, Vite, Vitest, Playwright |

## Git Conventions

- **Commit format:** [Conventional Commits](https://www.conventionalcommits.org/) — see [`.github/git-commit-instructions.md`](.github/git-commit-instructions.md)
- **Branch naming:** `feature/<name>`, `fix/<name>`, `chore/<name>`
- **Merge strategy:** `--no-ff` merges to `main`
- **Scopes:** `accounts`, `assets`, `transactions`, `portfolio`, `ui`, `api`, `db`, `deps`, `build`
- **Commits per feature:** Single squash commit with conventional format

## Module Navigation
- [`backend/AGENTS.md`](backend/AGENTS.md) — Backend-specific conventions and patterns
- [`frontend/AGENTS.md`](frontend/AGENTS.md) — Frontend-specific conventions and patterns

## Enforcement

| Mechanism | What It Does |
|-----------|-------------|
| `scripts/verify.sh` | Runs all checks (pytest, lint, tsc, vitest, build). Exit code gates the commit phase. |
| `scripts/pre-commit` | Lint check on staged files (ruff + eslint) |
| `scripts/pre-push` | pytest + tsc + vitest + build before push |
| Agent never pushes | The develop skill stops before `git push` — you push manually |

## Current Status
- [x] M1: Backend Setup & Database Layer
- [x] M2: Transaction Processing
- [x] M3: yfinance Integration & Portfolio API
- [x] M4: Frontend UI Shell & Layout
- [x] M5: TanStack Query & Charts
- [x] M6: End-to-End Testing & Validation

## Reference Documents
- `ARCHITECTURE.md` — Full technical architecture (frozen v1 spec)
- [`docs/archive/v1/MILESTONE_PLAN.md`](docs/archive/v1/MILESTONE_PLAN.md) — Archived milestone plan (frozen v1 spec)
- [`docs/archive/v1/milestones/`](docs/archive/v1/milestones/) — Archived task specs per milestone
- [`docs/archive/v1/status/`](docs/archive/v1/status/) — Archived completion logs from prior milestones
- [`docs/workflow-guide.md`](docs/workflow-guide.md) — Guide for the skill-based development workflow
