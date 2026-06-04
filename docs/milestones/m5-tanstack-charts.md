# Milestone 5: TanStack Query Integration & Charts

## Goal
Connect the frontend components to the backend API using TanStack Query hooks, implement Recharts visualizations on the Dashboard, and complete the full transactions CRUD user flows.

## Scope Constraints
- **DO**: Create TanStack Query hooks for all operations, invalidating cached data appropriately.
- **DO**: Implement responsive, interactive area and pie charts on the Dashboard.
- **DO**: Build form state management for adding/deleting transactions, including dynamic fields and error toast feedback.
- **DO NOT**: Implement automated E2E integration test scripts or mock scenarios (reserved for Milestone 6).

## Prerequisites
- Milestone 1–3 (backend services) and Milestone 4 (frontend shell) are fully completed and verified.

## Tasks

### 5.1 — TanStack Query Wrapper Setup
- **`frontend/src/main.tsx`**: Initialize the QueryClient and wrap the `<App />` component in the `<QueryClientProvider />`:
  ```typescript
  import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

  const queryClient = new QueryClient({
    defaultOptions: {
      queries: {
        staleTime: 30000, // 30 seconds
        refetchOnWindowFocus: true,
      },
    },
  });
  ```

### 5.2 — React Hooks Layer (`frontend/src/hooks/`)
Create custom hooks file structure:
- **`useAccounts.ts`**:
  - `useAccounts()`: lists accounts (`GET /accounts`).
  - `useCreateAccount()`: mutation (`POST /accounts`). Invalidates `["accounts"]`.
- **`useAssets.ts`**:
  - `useAssets()`: lists assets (`GET /assets`).
  - `useCreateAsset()`: mutation (`POST /assets`). Invalidates `["assets"]`.
- **`useTransactions.ts`**:
  - `useTransactions(filters)`: fetches transactions list filtered by query params.
  - `useCreateTransaction()`: mutation (`POST /transactions`).
    - **CRITICAL**: On success, must invalidate `["transactions"]` AND `["portfolio"]` to refresh both lists and dashboard charts.
  - `useDeleteTransaction()`: mutation (`DELETE /transactions/{id}`). Invalidates `["transactions"]` AND `["portfolio"]`.
- **`usePortfolio.ts`**:
  - `usePortfolioSummary()`: query for `GET /portfolio/summary`.
  - `usePortfolioHistory(period)`: query for `GET /portfolio/history?period={period}`.
  - `usePortfolioAllocation()`: query for `GET /portfolio/allocation`.

### 5.3 — Interactive Dashboard Page
- Wire stat cards directly to `usePortfolioSummary()` query results. Render clean loading skeleton components during query states.
- **Portfolio Value Chart**:
  - Render a Recharts `<AreaChart>` with a smooth gradient fill.
  - Source data from `usePortfolioHistory(period)`.
  - Render selector buttons for periods `1M`, `3M`, `6M`, `1Y`, `ALL`.
  - Tooltip: Show date and formatted cash, stock, and total portfolio valuation.
- **Allocation Chart**:
  - Render a Recharts `<PieChart>` using `usePortfolioAllocation()`.
  - Add tooltips and legend keys. Highlight percentage slices.

### 5.4 — Interactive Transactions Page
- Bind transaction table to `useTransactions()`. Color-code transaction types: `BUY` (green badge), `SELL` (red badge), `DEPOSIT`/`WITHDRAWAL`/`FEE` (blue/slate).
- Add delete button calling `useDeleteTransaction()`. Add browser confirmation popup.
- **Add Transaction Modal**:
  - Render form fields: Account, Type, Date, Notes.
  - Conditional validation rendering:
    - If Type is `BUY` or `SELL`: Render Ticker (select/input), Quantity, Price fields.
    - If Type is `DEPOSIT`, `WITHDRAWAL`, or `FEE`: Render Cash Amount field.
  - Inline Asset registration: If ticker typed doesn't exist, offer quick button: "Register asset [TICKER]" calling `useCreateAsset()`.
  - On error (e.g. insufficient shares/cash), catch exceptions and render standard error toast notifications.

### 5.5 — Interactive Holdings Page
- Fetch position metrics from `usePortfolioSummary()` `holdings` list.
- Render holdings table. Color-code P&L columns: positive unrealized values green, negative values red.
- Compute and append a summary "Totals" row at the bottom of the table.

## Validation Checkpoint
Verify milestone execution:
1. Start both servers:
   - Backend: `cd backend && uvicorn app.main:app` (on port 8000).
   - Frontend: `cd frontend && npm run dev` (on port 5173).
2. Create an account and asset via the UI.
3. Test Deposit transaction -> Cash card on Dashboard immediately updates.
4. Test Buy transaction -> Portfolio value chart starts rendering, holdings show new row.
5. Test Sell transaction (partial) -> Realized P&L shows up, shares remaining reduce.
6. Verify no runtime errors appear in the browser console.

## Completion Protocol
Once all items pass verification:
1. Write completion log to `docs/status/m5-complete.md`.
2. Add an entry under `## [v0.5.0]` in `CHANGELOG.md`.
3. Update `AGENTS.md` roadmap status to mark M5 as `[x]`.
4. Report completion to the user and request manual QA.
