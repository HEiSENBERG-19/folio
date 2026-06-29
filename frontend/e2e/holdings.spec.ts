import { test, expect } from '@playwright/test'

test.describe('Holdings', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/holdings')
  })

  test('should display holdings page', async ({ page }) => {
    await expect(page.locator('h1, [data-testid="page-title"]').first()).toBeVisible()
  })

  test('should display holdings table', async ({ page }) => {
    const table = page.locator('table, [data-testid*="holdings"], [role="table"]')
    await expect(table.first()).toBeVisible({ timeout: 10_000 })
  })
})
