---
name: Configurable Display Currency
status: Approved
priority: high
created: 2026-06-05
updated: 2026-06-05
progress:
  - "[x] Task 1: Create CurrencyContext and provider"
  - "[x] Task 2: Wrap App in CurrencyProvider"
  - "[x] Task 3: Integrate currency hook in Dashboard.tsx"
  - "[x] Task 4: Integrate currency hook in Holdings.tsx"
  - "[x] Task 5: Integrate currency hook in Transactions.tsx"
  - "[x] Task 6: Add currency toggle UI in Sidebar.tsx"
  - "[ ] Task 7: E2E Manual testing and verification"
---

# Feature: Configurable Display Currency

## Summary
Introduce a configurable currency system in the frontend, enabling users to toggle between USD ($) and INR (₹). When a user selects a currency, all portfolio summary stats, cash balances, asset values, charts, and transaction forms will dynamically update to display and format values in the selected currency using the appropriate locale (e.g. `en-US` for USD and `en-IN` for INR's lakh/crore formatting). The choice will be persisted in the browser's `localStorage` so that it persists across page reloads.

## Motivation
Currently, all currency display values in the frontend are hardcoded to USD ($) and formatted with the `en-US` locale. However, users who primarily or exclusively invest in Indian stocks have assets priced in INR. Since `yfinance` returns the native price without currency conversion and transactions are inputted in INR, showing a `$` symbol next to these amounts is incorrect and confusing. Users need their portfolio values formatted in INR (₹) with proper Indian numbering system format (e.g., lakhs/crores).

## Acceptance Criteria
1. Introduce a frontend global context `CurrencyContext` that manages the user's active currency (`USD` or `INR`), defaulting to `USD`.
2. Persist the chosen currency in `localStorage` under `folio_currency`.
3. Render a currency selection widget at the bottom of the sidebar (supporting switching between USD and INR).
4. Format all portfolio summary stats, cash balances, asset values, and transaction details in the active currency.
5. Use `en-IN` locale for formatting INR values (resulting in ₹ symbol and Indian numbering format, e.g. `₹1,50,000.00`), and `en-US` for USD.
6. Dynamically update charts to use the active currency's symbol (e.g., in the Y-axis label formatting and tooltips).
7. Dynamically update the Transaction page input fields to label unit prices and cash amounts with the active currency symbol (e.g., `Price per Unit (₹)` instead of `Price per Unit ($)`).

## Technical Design

### Backend
*None — no database or backend changes.*
The backend stores raw floats for cash balances, asset prices, and transactions without currency assumptions. It already handles yfinance ticker native currency inputs.

### Frontend
- **New File**: `frontend/src/context/CurrencyContext.tsx`
  - Defines the `Currency` type: `'USD' | 'INR'`.
  - Exposes `useCurrency` hook returning:
    - `currency`: Current active currency.
    - `setCurrency(curr)`: Updates active currency and saves to `localStorage`.
    - `formatCurrency(val)`: Formats numeric values to currency strings using `Intl.NumberFormat`. Uses `en-US` for USD and `en-IN` for INR.
    - `currencySymbol`: Active symbol (`$` or `₹`).
- **File Update**: `frontend/src/App.tsx`
  - Wrap the entire application routing structure with `CurrencyProvider`.
- **File Update**: `frontend/src/components/layout/Sidebar.tsx`
  - Import `useCurrency`.
  - Add a styled currency selection group (segmented buttons) just above the version number to toggle between USD and INR.
- **File Update**: `frontend/src/pages/Dashboard.tsx`
  - Import `useCurrency`.
  - Replace localized `formatCurrency` with the hook version.
  - Dynamically display `IndianRupee` or `DollarSign` icon in the "Invested Capital" card based on active currency.
  - Replace hardcoded `'$0.00'` values with `formatCurrency(0)`.
  - Replace hardcoded `$` in the AreaChart `YAxis` and tooltips with the dynamic `currencySymbol`.
- **File Update**: `frontend/src/pages/Holdings.tsx`
  - Import `useCurrency`.
  - Replace localized `formatCurrency` with the hook version.
- **File Update**: `frontend/src/pages/Transactions.tsx`
  - Import `useCurrency`.
  - Replace localized `formatCurrency` with the hook version.
  - Dynamically update inputs:
    - Label `Price per Unit ($)` to `Price per Unit ({currencySymbol})`.
    - Label `Cash Amount ($)` to `Cash Amount ({currencySymbol})`.
  - Format the cash balances in the account select dropdown option list using the hook's `formatCurrency`.

### Database Changes
*None — no database changes.*

## Edge Cases
- **Null/Undefined/Zero amounts**: Ensure currency formatting handles zero, negative, and missing amounts gracefully. (e.g. replacing hardcoded `"$0.00"` fallback with `formatCurrency(0)`).
- **Chart re-renders**: Verify that updating the currency state successfully triggers chart re-rendering.
- **LocalStorage corruption**: If the value in localStorage is not `'USD'` or `'INR'`, default to `'USD'`.

## Testing Strategy
- **Frontend Verification**:
  - Verify local storage saves the user preference on toggle.
  - Verify page content updates instantly when currency is toggled.
  - Verify number format (e.g. ₹1,50,000.00 for INR, $150,000.00 for USD).
  - Verify chart tooltips, chart Y-axis, transaction account selectors, and transaction forms display correct currency symbols.
- **Regression Testing**:
  - Run `npm run lint` and `npx tsc --noEmit` on frontend to ensure TypeScript type safety.
  - Run backend pytest suite to verify no regressions on core calculations: `python -m pytest -v` inside `backend/`.

## Files to Modify
- `frontend/src/App.tsx` — Add `CurrencyProvider` wrapper.
- `frontend/src/components/layout/Sidebar.tsx` — Add currency toggle widget.
- `frontend/src/pages/Dashboard.tsx` — Integrate dynamic currency formatting, dynamic icon, update Recharts tooltips/Y-axis.
- `frontend/src/pages/Holdings.tsx` — Integrate dynamic currency formatting.
- `frontend/src/pages/Transactions.tsx` — Integrate dynamic currency formatting, update label units, format cash dropdown values.

## New Files
- `frontend/src/context/CurrencyContext.tsx` — Expose `CurrencyProvider`, `useCurrency` context hook.
