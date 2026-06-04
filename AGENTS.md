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

## Current Status
- [x] M1: Backend Setup & Database Layer
- [x] M2: FIFO Engine & Transaction Processing
- [ ] M3: yfinance Integration & Portfolio API
- [ ] M4: Frontend UI Shell & Layout
- [ ] M5: TanStack Query & Charts
- [ ] M6: End-to-End Testing & Validation

## Reference Documents
- `ARCHITECTURE.md` — Full technical architecture (frozen v1 spec)
- `MILESTONE_PLAN.md` — Full milestone plan (frozen v1 spec)
- `docs/milestones/mN.md` — Enriched task spec per milestone
- `docs/status/` — Completion logs from prior milestones
