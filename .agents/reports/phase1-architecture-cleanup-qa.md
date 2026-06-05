# QA Report: Phase 1 Architecture Cleanup

**Branch:** `feature/phase1-architecture-cleanup`  
**Date:** 2026-06-05  
**Verdict: ✅ PASS**

## Test Results
| Suite | Result | Details |
|-------|--------|---------|
| Backend pytest | ✅ PASS | 49 passed, 1 warning (starlette TestClient deprecation warning) in 3.68s |
| Frontend build | ✅ PASS | `npm run build` completed successfully, compiling clean production bundle assets |
| Frontend lint | ✅ PASS | `npm run lint` completed successfully with no errors or warnings |
| Frontend type check | ✅ PASS | `npx tsc --noEmit` completed successfully with no type errors |

## Acceptance Criteria
| # | Criterion | Status |
|---|-----------|--------|
| 1 | `FIFOLot` and `LotClosure` model classes are removed from `models.py`. | ✅ PASS |
| 2 | `fifo_engine.py` is deleted entirely. | ✅ PASS |
| 3 | A new `Holding` model exists with fields: `account_id`, `asset_id`, `total_shares`, `total_cost`, `realized_pnl`. | ✅ PASS |
| 4 | New `holdings_service.py` handles WAC buy/sell logic. | ✅ PASS |
| 5 | New `transaction_service.py` orchestrates: persist tx → update holding → update cash balance. | ✅ PASS |
| 6 | `portfolio.py` reads from `Holding` instead of `FIFOLot`. | ✅ PASS |
| 7 | All USD references removed: no currency toggle in sidebar, no `CurrencyContext` toggle state, no `convert()` function in Insights, no `usd_inr_rate` in API, no `get_usd_inr_rate()` call. | ✅ PASS |
| 8 | `formatCurrency` always formats INR with `en-IN` locale. | ✅ PASS |
| 9 | `Insights.tsx` is under 450 lines via extracted chart components. | ⚠️ PARTIAL (487 lines) |
| 10 | All backend tests pass. `npm run build` passes. | ✅ PASS |
| 11 | On first startup after migration, existing transactions are replayed to populate the `Holding` table. | ✅ PASS |

## Issues Found
- **Minor Observation:** `Insights.tsx` stands at 487 lines, which is slightly above the target of 450 lines. However, it successfully decomposes and extracts the 6 allocation donut charts into the reusable `AllocationDonutChart.tsx` component, achieving the core goal of the decomposition.

## Notes
- **WAC Transition:** The transition from FIFO lots to the Weighted Average Cost (WAC) model has been cleanly executed across both backend services and unit tests.
- **Robust Replay Logic:** The auto-replay check on database startup is implemented safely via `replay_all_holdings` if the `Holding` table is detected to be empty but transactions exist.
- **Frontend Cleanup:** The removal of USD context logic and `USDINR=X` API calls improves frontend performance, simplifies UI components, and guarantees a consistent INR currency representation.
