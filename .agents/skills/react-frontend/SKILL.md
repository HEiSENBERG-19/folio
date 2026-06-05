# Skill: React Frontend

## When to Use
When working on the React frontend in `frontend/src/`.

## Tech Stack
- **Framework**: React 19 with TypeScript 6
- **Build Tool**: Vite 8
- **Styling**: Tailwind CSS v4 (via `@tailwindcss/vite` plugin)
- **State Management**: TanStack Query v5 (server state)
- **HTTP Client**: Axios
- **Charts**: Recharts 3
- **Icons**: Lucide React
- **Routing**: React Router DOM v7
- **Linting**: ESLint 10 with TypeScript and React plugins

## Commands

```bash
cd frontend

# Start dev server (port 5174, proxies /api to localhost:8000)
npm run dev

# Production build (type-check + bundle)
npm run build

# Type check only
npx tsc --noEmit

# Lint
npm run lint

# Preview production build
npm run preview
```

## Project Patterns

### API Layer (`src/api/`)
- Axios client configured with base URL
- One function per endpoint, grouped by resource
- Returns typed responses matching backend schemas

### Types (`src/types/`)
- TypeScript interfaces matching backend Pydantic schemas
- Shared between API layer, hooks, and components

### Hooks (`src/hooks/`)
- TanStack Query hooks for all server state
- `useQuery` for reads, `useMutation` for writes
- **No local state for API data** — TanStack Query is the cache

### Components (`src/components/`)
- `layout/` — AppShell, Sidebar, navigation
- Reusable UI components for shared patterns

### Pages (`src/pages/`)
- `Dashboard.tsx` — Stats, Recharts AreaChart + PieChart
- `Transactions.tsx` — Search/filter, transaction list, add trade modal
- `Holdings.tsx` — Position table with live totals

## Conventions
- **Tailwind CSS v4**: Use `@import "tailwindcss"` in CSS — no `tailwind.config.js`
- **TanStack Query**: All server data via query hooks — never `useState` + `useEffect` for fetching
- **Vite proxy**: `/api` requests proxy to `http://localhost:8000` in dev
- **Port**: Dev server runs on `5174`
- **No test runner configured yet** — `npm run build` (tsc + vite) is the primary validation
