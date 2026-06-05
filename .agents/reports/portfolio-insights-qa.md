# QA Report: Portfolio Insights

**Branch:** feature/portfolio-insights
**Date:** 2026-06-05
**Verdict: ✅ PASS**

## Test Results
| Suite | Result | Details |
|-------|--------|---------|
| Backend pytest | ✅ 52/52 | All 52 backend unit tests passed successfully. |
| Frontend build | ✅ PASS | Vite production build compiled successfully in 793ms. |
| Frontend type check | ✅ PASS | `npx tsc --noEmit` executed successfully with no compilation errors. |
| Frontend lint | ✅ PASS | `npm run lint` executed successfully with no styling or formatting errors. |

## Acceptance Criteria
| # | Criterion | Status | Details |
|---|-----------|--------|---------|
| 1 | **Database Schema & Migrations**: Cache `yfinance` details in `AssetMetadata` table for 24h, add `currency` column to `Account` with default `'USD'`, and run automatic migrations. | ✅ PASS | Implemented in [database.py](file:///home/heisenberg/projects/folio/backend/app/database.py#L15-L26) and [models.py](file:///home/heisenberg/projects/folio/backend/app/models.py#L79-L97). |
| 2 | **Backend Services & API**: Endpoint `GET /api/v1/portfolio/insights` returns holdings metadata, cash balances, and exchange rate. Handles rate-limiting and offline fallback. | ✅ PASS | Implemented in [portfolio.py (router)](file:///home/heisenberg/projects/folio/backend/app/routers/portfolio.py#L31-L33) and [portfolio.py (service)](file:///home/heisenberg/projects/folio/backend/app/services/portfolio.py#L332-L398). |
| 3 | **Frontend Navigation & Routing**: Register page route at `/insights` and place an Insights link with a dynamic icon in the sidebar. Support inline account currency selection. | ✅ PASS | Registered in [App.tsx](file:///home/heisenberg/projects/folio/frontend/src/App.tsx#L19), added in [Sidebar.tsx](file:///home/heisenberg/projects/folio/frontend/src/components/layout/Sidebar.tsx#L13), and configured in [Transactions.tsx](file:///home/heisenberg/projects/folio/frontend/src/pages/Transactions.tsx#L119). |
| 4 | **Portfolio Analytics & Calculations**: Normalize all holdings and cash values dynamically based on active display currency. Compute weighted Beta, P/E, Div Yield, and P/B. | ✅ PASS | Calculations completed in [Insights.tsx](file:///home/heisenberg/projects/folio/frontend/src/pages/Insights.tsx#L60-L215). |
| 5 | **Visualizations**: Render donut/pie charts for allocations, risk profile chart, 52W range sliders rendered, and custom SVG Treemap with color interpolation for unrealized P&L %. | ✅ PASS | Rendered in [Insights.tsx](file:///home/heisenberg/projects/folio/frontend/src/pages/Insights.tsx#L391-L706). *(Note: Risk profile is rendered as a donut chart, satisfying the allocation visual).* |
| 6 | **Error & Edge Cases**: Gracefully handle zero holdings/cash with clean empty states. Ensure instant UI updates upon display currency toggle. | ✅ PASS | Handled in [Insights.tsx](file:///home/heisenberg/projects/folio/frontend/src/pages/Insights.tsx#L89-L107) and hooks. |

## Issues Found
- **None.** All previously identified linting errors (component created during render, unused variables, and `let` variable preference) have been successfully resolved by the developer agent.

## Notes
- **Code Quality**: The code is highly modular, clean, and complies with all styling and formatting conventions listed in `AGENTS.md`. 
- **Tooltips**: The custom tooltip components are correctly declared outside of render scopes with typed props.
- **Robustness**: The backend logic gracefully handles yfinance crawler failures by writing safe fallbacks to the database, ensuring the web app never crashes due to upstream rate limits or outages.
