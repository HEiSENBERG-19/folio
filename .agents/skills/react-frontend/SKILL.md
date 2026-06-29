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
- **Unit Testing**: Vitest with React Testing Library
- **E2E Testing**: Playwright (Chromium)

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

# Unit tests (Vitest)
npm run test

# Unit tests in watch mode
npm run test:watch

# E2E tests (Playwright — requires running servers)
npm run test:e2e

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
- `Insights.tsx` — Portfolio analytics and insights

## Testing Patterns

### Vitest Unit Tests
- Config: `vitest.config.ts`
- Setup: `src/test/setup.ts`
- Pattern: `src/**/*.test.{ts,tsx}`
- Use `@testing-library/react` for rendering components
- Use `@testing-library/user-event` for simulating interactions
- Mock API calls with `vi.mock()` for isolated tests

```typescript
import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'

describe('MyComponent', () => {
  it('should render correctly', () => {
    render(<MyComponent />)
    expect(screen.getByText('Hello')).toBeInTheDocument()
  })
})
```

### Playwright E2E Tests
- Config: `e2e/playwright.config.ts`
- Pattern: `e2e/*.spec.ts`
- Browser: Chromium only
- Smoke tests — verify pages load and critical elements exist
- Add specific tests per feature as part of the develop workflow

```typescript
import { test, expect } from '@playwright/test'

test('page loads', async ({ page }) => {
  await page.goto('/my-page')
  await expect(page.locator('h1')).toBeVisible()
})
```

## Conventions
- **Tailwind CSS v4**: Use `@import "tailwindcss"` in CSS — no `tailwind.config.js`
- **TanStack Query**: All server data via query hooks — never `useState` + `useEffect` for fetching
- **Vite proxy**: `/api` requests proxy to `http://localhost:8000` in dev
- **Port**: Dev server runs on `5174`
- **Node**: Requires Node 22+ (see `.nvmrc`)
