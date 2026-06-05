# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [v1.0.0] — 2026-06-05

### Added
- Comprehensive API integration tests for full trade lifecycle, transaction deletions with replay verification, portfolio history data integrity, and error bounds (insufficient shares, insufficient cash, FK delete conflicts) in `backend/tests/test_api.py`.
- Deterministic scenario test validating FIFO math correctness, cash balances, lot status, and realized P&L calculations over a multi-day transaction sequence.
- Performance sanity check benchmark verifying that `/portfolio/summary` resolves in under 2 seconds, and `/portfolio/history` resolves in under 5 seconds initially and under 500ms on subsequent requests using SQLite caching.
- Verified zero TypeScript compilation and lint errors on the production-ready frontend bundle using Vite compiler.

## [v0.5.0] — 2026-06-05

### Added
- Integrated TanStack Query client wrapper in main entry point
- Created custom React query and mutation hooks for accounts, assets, transactions, and portfolio endpoints
- Fully wired Interactive Dashboard with Recharts AreaChart (performance value history) and PieChart (asset allocation) supporting custom interactive tooltips and time period selections
- Implemented responsive skeleton screens and empty-state placeholders on Dashboard and Holdings tables
- Implemented functional search, type filters, and account/asset filters on the Transactions page
- Built dynamic Add Trade modal with conditional field validation and inline creations (quick account creation and inline asset registration)
- Implemented delete transaction triggers with confirmation alerts and real-time ledger recalculation
- Implemented floating Toast notification banners to display detailed success and error responses
- Computed and appended live totals row at the bottom of the Positions/Holdings table
- Completed TypeScript compilation checks (`npm run build`) and verified all backend tests pass

### Fixed
- Fixed yfinance fetching database write crash caused by `NaN` or `Infinite` closing prices on market closed dates or holidays, which previously triggered `IntegrityError` on the `PriceCache` table and subsequent session transaction failures.

## [v0.4.0] — 2026-06-04

### Added
- Scaffolding of the React + Vite + TypeScript frontend project with dev dependencies
- Custom Vite plugin registration for Tailwind CSS v4 and backend API proxy settings
- Styling infrastructure with custom design tokens, dark background aesthetics, custom scrollbars, and micro-animations
- Client-side navigation Sidebar with link highlights and Lucide icons
- Responsive layout AppShell supporting mobile viewport hamburger toggle drawer
- Typescript interfaces representing database models and API schema definitions
- Mock-data-driven page views for Dashboard (stat cards, line/pie chart containers), Transactions (search/filter bar, transaction list table), and Holdings (position tables, progress bars)
- Zero-error typescript compilation verified by `npm run build`

## [v0.3.0] — 2026-06-04


### Added
- Historical price fetching from yfinance with a persistent local SQLite `PriceCache`
- Price matrix generator utilizing Pandas to reindex calendar dates and forward-fill market closed gaps
- Portfolio summary aggregates, calculating weighted average cost basis, market values, and unrealized and realized P&L
- Historical snapshot walking of transaction ledgers to build daily portfolio values (holdings value + cash balance)
- Asset allocation percentage endpoints
- `/portfolio/summary`, `/portfolio/history`, and `/portfolio/allocation` API endpoints
- Comprehensive test coverage for pricing service, cache validations, fill logic, and portfolio endpoints

## [v0.2.0] — 2026-06-04


### Added
- FIFO matching engine service `fifo_engine.py` with `process_sell`, `process_transaction`, and `replay_ledger`
- Validation logic in `TransactionCreate` schema for BUY, SELL, DEPOSIT, WITHDRAWAL, and FEE transactions
- Transaction CRUD API endpoints: `GET /transactions`, `POST /transactions`, `GET /transactions/{id}`, and `DELETE /transactions/{id}`
- Automated test coverage in `tests/test_fifo_engine.py` verifying lot allocation, realized P&L, balance checks, and ledger replay
- Consolidated pytest fixtures to `tests/conftest.py`

## [v0.1.0] — 2026-06-04


### Added
- Backend project scaffolding with Python virtual environment and `requirements.txt`
- SQLModel table definitions: `Account`, `Asset`, `Transaction`, `FIFOLot`, `LotClosure`, `PriceCache`
- `PriceCache` unique constraint on `(asset_id, price_date)`
- FastAPI application shell with CORS middleware and lifespan startup handler
- `GET /`, `GET|POST /api/v1/accounts`, `GET|PUT|DELETE /api/v1/accounts/{id}` endpoints
- `GET|POST /api/v1/assets`, `GET|DELETE /api/v1/assets/{id}` endpoints
- Auto-uppercase ticker normalization on asset creation
- 409 Conflict responses for duplicate names/tickers and FK-protected deletes
- Pytest test suite (17 tests, all passing)
