# frontend/ — Agent Context

> React 19 + TypeScript SPA with TanStack Query, Recharts, and Tailwind CSS v4.

## Module Structure

```
frontend/
├── src/
│   ├── main.tsx             # Entry point, QueryClientProvider, BrowserRouter
│   ├── App.tsx              # Route definitions, AppShell layout
│   ├── App.css              # App-level styles
│   ├── index.css            # Global styles, Tailwind v4 import, design tokens
│   ├── api/                 # Axios client and endpoint wrappers
│   ├── components/
│   │   └── layout/          # AppShell, Sidebar, navigation components
│   ├── hooks/               # TanStack Query custom hooks (useAccounts, usePortfolio, etc.)
│   ├── pages/
│   │   ├── Dashboard.tsx    # Stats cards, AreaChart, PieChart, time period selector
│   │   ├── Transactions.tsx # Search/filter bar, transaction table, add trade modal
│   │   ├── Holdings.tsx     # Position table with P&L, live totals row
│   │   └── Insights.tsx     # Portfolio insights and analytics
│   ├── types/               # TypeScript interfaces matching backend schemas
│   ├── test/                # Vitest setup and test utilities
│   └── assets/              # Static assets
├── e2e/                     # Playwright E2E tests
│   ├── playwright.config.ts # Playwright configuration
│   ├── dashboard.spec.ts    # Dashboard smoke tests
│   ├── transactions.spec.ts # Transactions page tests
│   ├── holdings.spec.ts     # Holdings page tests
│   └── navigation.spec.ts   # Navigation and routing tests
├── index.html               # HTML entry point
├── vite.config.ts           # Vite + React + Tailwind v4 plugin config
├── vitest.config.ts         # Vitest unit test configuration
├── tsconfig.json            # TypeScript project references
├── tsconfig.app.json        # App TypeScript config
├── tsconfig.node.json       # Node/Vite TypeScript config
├── eslint.config.js         # ESLint flat config with TS + React plugins
└── package.json             # Dependencies and scripts
```

## Key Patterns

- **TanStack Query**: All server data via `useQuery`/`useMutation` hooks — never `useState` + `fetch`
- **Tailwind CSS v4**: Imported via `@import "tailwindcss"` in `index.css`, plugin via `@tailwindcss/vite`
- **Vite proxy**: `/api` requests proxy to `http://localhost:8000` in development
- **Axios client**: Configured in `src/api/` with typed response wrappers
- **React Router v7**: Client-side routing with `BrowserRouter` and `Routes`

## Styling

- **Dark mode** with custom design tokens in `index.css`
- Custom scrollbars and micro-animations
- Lucide React for iconography
- Recharts for charts (AreaChart for history, PieChart for allocation)

## Build & Dev

```bash
cd frontend

# Development (port 5174)
npm run dev

# Production build (tsc type-check + vite bundle)
npm run build

# Lint
npm run lint

# Type check only
npx tsc --noEmit
```

## Testing

```bash
cd frontend

# Unit tests (Vitest)
npm run test

# Unit tests in watch mode
npm run test:watch

# E2E tests (Playwright — requires backend + frontend running)
npm run test:e2e

# Full verification (from project root)
bash scripts/verify.sh
bash scripts/verify.sh --e2e  # includes Playwright
```

### Vitest (Unit Tests)
- Config: `vitest.config.ts`
- Setup: `src/test/setup.ts` (jest-dom matchers, cleanup)
- Test files: `src/**/*.test.{ts,tsx}`
- Environment: jsdom
- Use `@testing-library/react` for component tests
- Use `@testing-library/user-event` for user interaction simulation

### Playwright (E2E Tests)
- Config: `e2e/playwright.config.ts`
- Test files: `e2e/*.spec.ts`
- Browser: Chromium only
- Base URL: `http://localhost:5174`
- Runs in isolation against a local development server

## Adding a New Feature

1. Add TypeScript interfaces to `src/types/`
2. Add API endpoint functions to `src/api/`
3. Create TanStack Query hooks in `src/hooks/`
4. Build components in `src/components/`
5. Wire into pages in `src/pages/`
6. Write Vitest unit tests for new hooks/utilities
7. Write Playwright E2E tests for new user flows (if applicable)
8. Run `bash scripts/verify.sh` to verify everything passes

## Conventions
- **Tailwind CSS v4**: Use `@import "tailwindcss"` in CSS — no `tailwind.config.js`
- **TanStack Query**: All server data via query hooks — never `useState` + `useEffect` for fetching
- **Vite proxy**: `/api` requests proxy to `http://localhost:8000` in dev
- **Port**: Dev server runs on `5174`
- **Node**: Requires Node 22+ (see `.nvmrc`)
