import { test, expect } from '@playwright/test'

test.describe('Navigation', () => {
  test('should load the dashboard page by default', async ({ page }) => {
    await page.goto('/')
    await expect(page).toHaveURL('/')
    await expect(page.locator('h1, [data-testid="page-title"]').first()).toBeVisible()
  })

  test('should navigate to transactions page', async ({ page }) => {
    await page.goto('/')
    await page.click('a[href="/transactions"], [data-testid="nav-transactions"]')
    await expect(page).toHaveURL('/transactions')
  })

  test('should navigate to holdings page', async ({ page }) => {
    await page.goto('/')
    await page.click('a[href="/holdings"], [data-testid="nav-holdings"]')
    await expect(page).toHaveURL('/holdings')
  })

  test('should navigate to insights page', async ({ page }) => {
    await page.goto('/')
    await page.click('a[href="/insights"], [data-testid="nav-insights"]')
    await expect(page).toHaveURL('/insights')
  })

  test('sidebar should be visible', async ({ page }) => {
    await page.goto('/')
    await expect(page.locator('nav, [data-testid="sidebar"]').first()).toBeVisible()
  })
})
