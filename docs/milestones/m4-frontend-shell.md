# Milestone 4: Frontend UI Shell & Layout

## Goal
Scaffold a polished, dark-mode-first React + Vite + TypeScript frontend, integrate Tailwind CSS v4, configure client-side routing, and create the main app shell with placeholders for Dashboard, Transactions, and Holdings.

## Scope Constraints
- **DO**: Scaffold React, install UI/routing dependencies, configure a Vite proxy for backend API calls, and build a beautiful, responsive layout shell.
- **DO**: Use Tailwind CSS v4 styling rules directly in code.
- **DO NOT**: Fetch live API data using React Hooks or TanStack Query. Keep pages strictly populated with static mock data/skeletons for now. Do not draw real charts.

## Prerequisites
- Milestone 1 backend is functional (needed for proxy smoke test).

## Tasks

### 4.1 — Vite & React Scaffolding
In the `frontend/` directory, set up the project:
1. Run Vite scaffolding:
   ```bash
   npx -y create-vite@latest ./ --template react-ts
   ```
2. Install client dependencies:
   ```bash
   npm install react-router-dom @tanstack/react-query recharts axios lucide-react
   npm install -D tailwindcss @tailwindcss/vite
   ```
3. Configure Vite plugins & proxy settings in `vite.config.ts`:
   ```typescript
   import { defineConfig } from 'vite';
   import react from '@vitejs/plugin-react';
   import tailwindcss from '@tailwindcss/vite';

   export default defineConfig({
     plugins: [react(), tailwindcss()],
     server: {
       proxy: {
         '/api': 'http://localhost:8000',
       },
     },
   });
   ```

### 4.2 — Global Design & Styling (Tailwind v4)
- **`frontend/src/index.css`**: Configure core styling settings. Set up a dark, high-end theme:
  - Font: Import and configure a modern sans font like Outfit or Inter.
  - Colors: Use deep slate/navy backgrounds (e.g., `#090D16`), card surfaces with glassmorphism properties (`bg-slate-900/60`, `backdrop-blur-md`, `border-slate-800`), green and red accent text matching P&L status.
  - Smooth hover actions and micro-transitions:
  ```css
  @import "tailwindcss";

  @theme {
    --color-bg-main: #0b0f19;
    --color-bg-card: rgba(17, 24, 39, 0.7);
    --color-border-card: rgba(255, 255, 255, 0.08);
  }

  body {
    background-color: var(--color-bg-main);
    color: #f3f4f6;
    font-family: 'Inter', sans-serif;
  }
  ```

### 4.3 — Routing & Sidebar App Shell
- **`frontend/src/types/index.ts`**: Recreate the backend model schemas in TypeScript:
  - `TxType` enum (`BUY`, `SELL`, `DEPOSIT`, `WITHDRAWAL`, `FEE`).
  - interfaces for `Account`, `Asset`, `Transaction`, `HoldingDetail`, `PortfolioSummary`, `PortfolioHistoryPoint`, `AllocationSlice`.
- **`frontend/src/api/client.ts`**: Create an Axios instance with `baseURL: "/api/v1"`.
- **`frontend/src/components/layout/Sidebar.tsx`**: Side navigation with app title "Folio", links to Dashboard (`/`), Transactions (`/transactions`), and Holdings (`/holdings`), styled with hover feedback and active states. Use `lucide-react` icons.
- **`frontend/src/components/layout/AppShell.tsx`**: Renders sidebar and content container. Handles mobile viewport responsiveness.
- **`frontend/src/App.tsx`**: Add `BrowserRouter`, `<Routes>`, and basic layout boundaries.

### 4.4 — Page Placeholders (Mock Data)
- **`frontend/src/pages/Dashboard.tsx`**:
  - Stat cards grid: Net Portfolio Value, Invested Capital, Unrealized P&L (color-coded), Realized P&L, Cash Balance.
  - Empty grid segments for charts: Area/Line chart placeholder, Pie chart placeholder.
- **`frontend/src/pages/Transactions.tsx`**:
  - Action bar with a "+ Add Trade" button.
  - Transaction table with columns for date, type, ticker, quantity, price, total amount, notes, and actions. Populate with 3 rows of realistic mock data.
- **`frontend/src/pages/Holdings.tsx`**:
  - Position table showing ticker, shares held, average cost, current price, market value, unrealized P&L, and realized P&L. Populate with mock positions.

## Validation Checkpoint
Verify milestone execution:
1. Start the Vite server:
   ```bash
   cd frontend && npm run dev
   ```
2. Open `http://localhost:5173` in a browser.
3. Assert:
   - Sidebar navigates between `/`, `/transactions`, and `/holdings` smoothly.
   - Page layouts render correctly in dark mode.
   - Page layout wraps nicely on mobile widths.
   - Run a fetch test from the browser console to confirm the proxy forwards `/api/v1/accounts` to the running backend.

## Completion Protocol
Once all items pass verification:
1. Write completion log to `docs/status/m4-complete.md`.
2. Add an entry under `## [v0.4.0]` in `CHANGELOG.md`.
3. Update `AGENTS.md` roadmap status to mark M4 as `[x]`.
4. Report completion to the user and request manual QA.
