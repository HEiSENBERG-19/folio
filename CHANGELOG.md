# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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
