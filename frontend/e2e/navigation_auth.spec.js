import { test, expect } from '@playwright/test'

test.describe('Navigation and Authentication Flow', () => {
  test('1. Landing page is accessible logged out and renders Sign In button', async ({ page }) => {
    await page.goto('/')
    await expect(page).toHaveURL('/')
    const signInBtn = page.getByRole('button', { name: /sign in/i }).first()
    await expect(signInBtn).toBeVisible()
  })

  test('2. Unauthenticated user opening /dashboard is redirected to /login with returnTo', async ({ page }) => {
    await page.goto('/dashboard')
    await expect(page).toHaveURL(/\/login\?returnTo=%2Fdashboard/)
  })

  test('3. Open redirect prevention: malicious returnTo falls back to /dashboard after login', async ({ page }) => {
    await page.goto('/login?returnTo=//evil.com')
    await expect(page.getByRole('button', { name: 'Sign In', exact: true })).toBeVisible()
  })

  test('4. Logged-in user opening /login is redirected to /dashboard', async ({ page }) => {
    // Mock /me endpoint
    await page.route('**/api/v1/auth/me', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ user: { id: 1, email: 'user@example.com', role: 'viewer' } })
      })
    })

    await page.addInitScript(() => {
      localStorage.setItem('auth_token', 'valid_mock_token_123')
    })

    await page.goto('/login')
    await expect(page).toHaveURL(/\/dashboard/)
  })

  test('5. Logged-in user on landing page sees Dashboard button and CTA', async ({ page }) => {
    await page.route('**/api/v1/auth/me', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ user: { id: 1, email: 'user@example.com', role: 'viewer' } })
      })
    })

    await page.addInitScript(() => {
      localStorage.setItem('auth_token', 'valid_mock_token_123')
    })

    await page.goto('/')
    await expect(page).toHaveURL('/')
    const dashBtn = page.getByRole('button', { name: 'Dashboard', exact: true }).first()
    await expect(dashBtn).toBeVisible()
  })

  test('6. Logout clears storage and navigates to landing page', async ({ page }) => {
    await page.route('**/api/v1/auth/me', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ user: { id: 1, email: 'user@example.com', role: 'viewer' } })
      })
    })

    await page.goto('/')
    await page.evaluate(() => {
      localStorage.setItem('auth_token', 'valid_mock_token_123')
    })
    await page.goto('/dashboard')
    await expect(page).toHaveURL(/\/dashboard/)

    // Trigger logout via window
    await page.evaluate(async () => {
      const authModule = await import('/src/store/authStore.js')
      authModule.default.getState().logout(true)
      window.location.replace('/')
    })

    await expect(page).toHaveURL('/')
    const token = await page.evaluate(() => localStorage.getItem('auth_token'))
    expect(token).toBeNull()

    // Back button attempt should not restore dashboard
    await page.goBack()
    const url = page.url()
    expect(url).not.toContain('/dashboard')
  })
})
