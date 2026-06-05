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
│   │   └── Holdings.tsx     # Position table with P&L, live totals row
│   ├── types/               # TypeScript interfaces matching backend schemas
│   └── assets/              # Static assets
├── index.html               # HTML entry point
├── vite.config.ts           # Vite + React + Tailwind v4 plugin config
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

## Adding a New Feature

1. Add TypeScript interfaces to `src/types/`
2. Add API endpoint functions to `src/api/`
3. Create TanStack Query hooks in `src/hooks/`
4. Build components in `src/components/`
5. Wire into pages in `src/pages/`
6. Run `npm run build` to verify (type-check + bundle)
