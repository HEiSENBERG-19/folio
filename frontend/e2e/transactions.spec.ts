import { test, expect } from '@playwright/test'

test.describe('Transactions', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/transactions')
  })

  test('should display transactions page', async ({ page }) => {
    await expect(page.locator('h1, [data-testid="page-title"]').first()).toBeVisible()
  })

  test('should have add transaction button', async ({ page }) => {
    const addBtn = page.locator('button:has-text("Add"), button:has-text("Trade"), [data-testid*="add"]')
    await expect(addBtn.first()).toBeVisible({ timeout: 10_000 })
  })

  test('should have CSV import button', async ({ page }) => {
    const importBtn = page.locator('button:has-text("Import"), button:has-text("CSV"), [data-testid*="import"]')
    await expect(importBtn.first()).toBeVisible({ timeout: 10_000 })
  })
})
