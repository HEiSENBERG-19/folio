# Folio — Agent Context

> Single-user stock portfolio tracker with FIFO P&L accounting.

## Tech Stack
- **Backend:** Python 3.12+, FastAPI, SQLModel, SQLite, yfinance
- **Frontend:** React 18, TypeScript, Vite, Tailwind CSS v4, TanStack Query, Recharts
- **Testing:** pytest (backend), manual QA (frontend)

## Project Structure
- `backend/app/` — FastAPI application
  - `models.py` — SQLModel table definitions
  - `schemas.py` — Pydantic request/response schemas
  - `routers/` — API route handlers (accounts, assets, transactions, portfolio)
  - `services/` — Business logic (fifo_engine, portfolio, price_service)
- `frontend/src/` — React application
  - `api/` — Axios client and endpoint wrappers
  - `components/` — UI components (layout, dashboard, transactions, ui)
  - `hooks/` — TanStack Query custom hooks
  - `pages/` — Route pages (Dashboard, Transactions, Holdings)
  - `types/` — TypeScript interfaces

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

## Agent Roles

This project uses a multi-agent development workflow. Each agent has a defined role:

| Agent | Definition | Purpose |
|-------|-----------|---------|
| Planning Agent | [`.agents/agents/planning.agent.md`](.agents/agents/planning.agent.md) | Writes feature specifications |
| Developer Agent | [`.agents/agents/developer.agent.md`](.agents/agents/developer.agent.md) | Implements from approved plans |
| QA Agent | [`.agents/agents/qa.agent.md`](.agents/agents/qa.agent.md) | Verifies features, produces reports |
| Git Agent | [`.agents/agents/git.agent.md`](.agents/agents/git.agent.md) | Commits, merges, releases |

## Skills Reference

| Skill | Guide | Covers |
|-------|-------|--------|
| Python Backend | [`.agents/skills/python-backend/SKILL.md`](.agents/skills/python-backend/SKILL.md) | FastAPI, SQLModel, pytest |
| React Frontend | [`.agents/skills/react-frontend/SKILL.md`](.agents/skills/react-frontend/SKILL.md) | React, TypeScript, Vite, Tailwind |
| Plan Specification | [`.agents/skills/plan-spec/SKILL.md`](.agents/skills/plan-spec/SKILL.md) | Feature spec template and format |
| Git Workflow | [`.agents/skills/git-workflow/SKILL.md`](.agents/skills/git-workflow/SKILL.md) | Branches, commits, merges, releases |

## Git Conventions

- **Commit format:** [Conventional Commits](https://www.conventionalcommits.org/) — see [`.github/git-commit-instructions.md`](.github/git-commit-instructions.md)
- **Branch naming:** `feature/<name>`, `fix/<name>`, `chore/<name>`
- **Merge strategy:** `--no-ff` merges to `main`
- **Scopes:** `accounts`, `assets`, `transactions`, `portfolio`, `fifo`, `ui`, `api`, `db`, `deps`, `build`

## Module Navigation
- [`backend/AGENTS.md`](backend/AGENTS.md) — Backend-specific conventions and patterns
- [`frontend/AGENTS.md`](frontend/AGENTS.md) — Frontend-specific conventions and patterns

## Current Status
- [x] M1: Backend Setup & Database Layer
- [x] M2: FIFO Engine & Transaction Processing
- [x] M3: yfinance Integration & Portfolio API
- [x] M4: Frontend UI Shell & Layout
- [x] M5: TanStack Query & Charts
- [x] M6: End-to-End Testing & Validation

## Reference Documents
- `ARCHITECTURE.md` — Full technical architecture (frozen v1 spec)
- [`docs/archive/v1/MILESTONE_PLAN.md`](docs/archive/v1/MILESTONE_PLAN.md) — Archived milestone plan (frozen v1 spec)
- [`docs/archive/v1/milestones/`](docs/archive/v1/milestones/) — Archived task specs per milestone
- [`docs/archive/v1/status/`](docs/archive/v1/status/) — Archived completion logs from prior milestones
- [`docs/workflow-guide.md`](docs/workflow-guide.md) — Human guide for managing the agent workflow
