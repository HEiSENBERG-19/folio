# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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
