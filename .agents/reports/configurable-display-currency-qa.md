# QA Report: Configurable Display Currency

**Branch:** feature/configurable-display-currency
**Date:** 2026-06-05
**Verdict: ✅ PASS**

## Test Results
| Suite | Result | Details |
|-------|--------|---------|
| Backend pytest | ✅ 49/49 | All 49 backend tests passed successfully in 4.18s |
| Frontend build | ✅ PASS | Vite production build completed successfully without errors |
| Frontend lint & type check | ✅ PASS | `eslint .` and `tsc --noEmit` executed successfully with no errors |

## Acceptance Criteria
| # | Criterion | Status |
|---|-----------|--------|
| 1 | Introduce a frontend global context `CurrencyContext` that manages the user's active currency (`USD` or `INR`), defaulting to `USD`. | ✅ |
| 2 | Persist the chosen currency in `localStorage` under `folio_currency`. | ✅ |
| 3 | Render a currency selection widget at the bottom of the sidebar (supporting switching between USD and INR). | ✅ |
| 4 | Format all portfolio summary stats, cash balances, asset values, and transaction details in the active currency. | ✅ |
| 5 | Use `en-IN` locale for formatting INR values (resulting in ₹ symbol and Indian numbering format, e.g. `₹1,50,000.00`), and `en-US` for USD. | ✅ |
| 6 | Dynamically update charts to use the active currency's symbol (e.g., in the Y-axis label formatting and tooltips). | ✅ |
| 7 | Dynamically update the Transaction page input fields to label unit prices and cash amounts with the active currency symbol (e.g., `Price per Unit (₹)` instead of `Price per Unit ($)`). | ✅ |

## Issues Found
- None. All implementation details align with the approved plan.

## Notes
- Code quality is high, with excellent modularization. The currency context is isolated under a React Context (`useCurrency`) which handles data formatting, currency symbol lookup, and persistent state.
- Edge cases, such as `localStorage` corruption/missing state and `null`/`undefined`/`zero` amounts, are handled gracefully in the context provider.
- Chart re-renders successfully trigger upon currency switches, updating Y-axis formatting and tooltips on the fly.
