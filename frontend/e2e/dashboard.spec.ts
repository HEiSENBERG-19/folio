import { test, expect } from '@playwright/test'

test.describe('Dashboard', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/')
  })

  test('should display portfolio summary cards', async ({ page }) => {
    // Dashboard should have stat cards for portfolio value, gain/loss, etc.
    const cards = page.locator('[data-testid*="stat-card"], .stat-card, [class*="card"]')
    await expect(cards.first()).toBeVisible({ timeout: 10_000 })
  })

  test('should display portfolio chart', async ({ page }) => {
    // Recharts renders SVG elements
    const chart = page.locator('.recharts-wrapper, [data-testid*="chart"], svg.recharts-surface')
    await expect(chart.first()).toBeVisible({ timeout: 10_000 })
  })

  test('should have time period selector', async ({ page }) => {
    const selector = page.locator('[data-testid*="period"], button:has-text("1W"), button:has-text("1M"), button:has-text("1Y")')
    await expect(selector.first()).toBeVisible({ timeout: 10_000 })
  })
})
