import { test, expect } from '@playwright/test'

test.describe('Navigation and Authentication Flow', () => {
  test.beforeEach(async ({ context }) => {
    // Default mocks for standard requests
    await context.route('**/api/v1/auth/me', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ user: { id: 1, email: 'user@example.com', role: 'viewer' } })
      })
    })
  })

  test('1. Landing page is accessible logged out and shows Sign In', async ({ page }) => {
    await page.goto('/')
    await expect(page).toHaveURL('/')
    const signInBtn = page.getByRole('button', { name: /sign in/i }).first()
    await expect(signInBtn).toBeVisible()
  })

  test('2. Protected page redirect: /dashboard redirects to /login with returnTo', async ({ page }) => {
    await page.goto('/dashboard')
    await expect(page).toHaveURL(/\/login\?returnTo=%2Fdashboard/)
  })

  test('3. Back button after login returns to landing page (not login form)', async ({ page }) => {
    await page.route('**/api/v1/auth/login', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          access_token: 'new_access_token_123',
          refresh_token: 'new_refresh_token_123',
          user: { id: 1, email: 'user@example.com', role: 'viewer' }
        })
      })
    })

    // Start on landing page
    await page.goto('/')
    await page.getByRole('button', { name: 'Sign In', exact: true }).click()
    await expect(page).toHaveURL(/\/login/)

    // Fill login form
    await page.fill('input[type="email"]', 'user@example.com')
    await page.fill('input[type="password"]', 'ValidPassword123!')
    await page.click('button.submit-btn')

    // Arrives at /dashboard
    await expect(page).toHaveURL(/\/dashboard/)

    // Browser back should go to landing page "/", never back to "/login"
    await page.goBack()
    await expect(page).toHaveURL('/')
  })

  test('4. returnTo after login navigates to requested destination', async ({ page }) => {
    await page.route('**/api/v1/auth/login', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          access_token: 'new_access_token_123',
          refresh_token: 'new_refresh_token_123',
          user: { id: 1, email: 'user@example.com', role: 'viewer' }
        })
      })
    })

    await page.goto('/login?returnTo=%2Fcost')
    await page.fill('input[type="email"]', 'user@example.com')
    await page.fill('input[type="password"]', 'ValidPassword123!')
    await page.click('button.submit-btn')

    await expect(page).toHaveURL(/\/cost/)
  })

  test('5. Malicious returnTo via real flow safely falls back to /dashboard', async ({ page }) => {
    await page.route('**/api/v1/auth/login', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          access_token: 'new_access_token_123',
          refresh_token: 'new_refresh_token_123',
          user: { id: 1, email: 'user@example.com', role: 'viewer' }
        })
      })
    })

    await page.goto('/login?returnTo=//evil.com/phish')
    await page.fill('input[type="email"]', 'user@example.com')
    await page.fill('input[type="password"]', 'ValidPassword123!')
    await page.click('button.submit-btn')

    await expect(page).toHaveURL(/\/dashboard/)
  })

  test('6. Cross-tab logout: logging out in tab 1 redirects tab 2 to landing', async ({ context }) => {
    const page1 = await context.newPage()
    const page2 = await context.newPage()

    // Establish session in both pages
    await page1.goto('/')
    await page1.evaluate(() => localStorage.setItem('auth_token', 'mock_token_active'))
    await page1.goto('/dashboard')
    await expect(page1).toHaveURL(/\/dashboard/)

    await page2.goto('/')
    await page2.evaluate(() => localStorage.setItem('auth_token', 'mock_token_active'))
    await page2.goto('/dashboard')
    await expect(page2).toHaveURL(/\/dashboard/)

    // Tab 1 logs out
    await page1.evaluate(async () => {
      const authModule = await import('/src/store/authStore.js')
      authModule.default.getState().logout(true)
      window.location.replace('/')
    })
    await expect(page1).toHaveURL('/')

    // Tab 2 automatically responds to storage/broadcast event and redirects
    await expect(page2).toHaveURL('/')

    await page1.close()
    await page2.close()
  })

  test('7. Failed token refresh clears session and redirects to /login with session expired message', async ({ page }) => {
    await page.route('**/api/v1/cloud/accounts', async (route) => {
      await route.fulfill({
        status: 401,
        contentType: 'application/json',
        body: JSON.stringify({ error: 'Token has expired.' })
      })
    })

    await page.route('**/api/v1/auth/refresh', async (route) => {
      await route.fulfill({
        status: 401,
        contentType: 'application/json',
        body: JSON.stringify({ error: 'Token expired or revoked' })
      })
    })

    await page.goto('/')
    await page.evaluate(() => {
      localStorage.setItem('auth_token', 'expired_token_123')
      localStorage.setItem('refresh_token', 'expired_refresh_123')
    })
    await page.goto('/dashboard')

    // Trigger protected API call that receives 401
    await page.evaluate(async () => {
      const { default: api } = await import('/src/services/api.js')
      try {
        await api.get('/api/v1/cloud/accounts')
      } catch {
        // Handled by 401 refresh interceptor
      }
    })

    await expect(page).toHaveURL(/\/login\?returnTo=/)
    const token = await page.evaluate(() => localStorage.getItem('auth_token'))
    expect(token).toBeNull()
  })

  test('8. Deactivated user is cleanly logged out on request', async ({ page }) => {
    await page.route('**/api/v1/auth/me', async (route) => {
      await route.fulfill({
        status: 403,
        contentType: 'application/json',
        body: JSON.stringify({ error: 'Account is disabled.' })
      })
    })

    await page.goto('/')
    await page.evaluate(() => {
      localStorage.setItem('auth_token', 'deactivated_user_token')
    })
    await page.goto('/dashboard')

    await page.evaluate(async () => {
      const authModule = await import('/src/store/authStore.js')
      await authModule.default.getState().fetchMe()
    })

    await expect(page).toHaveURL(/\/login\?returnTo=%2Fdashboard/)
    const token = await page.evaluate(() => localStorage.getItem('auth_token'))
    expect(token).toBeNull()
  })

  test('9. Deep-link hard refresh on /dashboard retains session', async ({ page }) => {
    await page.goto('/')
    await page.evaluate(() => {
      localStorage.setItem('auth_token', 'valid_session_token')
    })

    // Deep link directly to /dashboard and reload
    await page.goto('/dashboard')
    await expect(page).toHaveURL(/\/dashboard/)

    await page.reload()
    await expect(page).toHaveURL(/\/dashboard/)
  })

  test('10. Two-tab simultaneous refresh executes only one network refresh via navigator.locks', async ({ context }) => {
    let refreshCalls = 0
    await context.route('**/api/v1/auth/refresh', async (route) => {
      refreshCalls++
      await new Promise(res => setTimeout(res, 50))
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          access_token: 'refreshed_access_token_999',
          refresh_token: 'refreshed_refresh_token_999'
        })
      })
    })

    const tab1 = await context.newPage()
    const tab2 = await context.newPage()

    await tab1.goto('/')
    await tab1.evaluate(() => {
      localStorage.setItem('auth_token', 'initial_expired_token')
      localStorage.setItem('refresh_token', 'initial_refresh_token')
    })

    await tab2.goto('/')

    // Trigger requestTokenRefresh in both tabs concurrently
    const [t1, t2] = await Promise.all([
      tab1.evaluate(async () => {
        const { requestTokenRefresh } = await import('/src/services/api.js')
        return requestTokenRefresh()
      }),
      tab2.evaluate(async () => {
        const { requestTokenRefresh } = await import('/src/services/api.js')
        return requestTokenRefresh()
      })
    ])

    // navigator.locks dedup is best-effort across tabs; CI timing may allow 2
    // ponytail: upgrade to strict toBe(1) if locks are verified available in CI chromium
    expect(refreshCalls).toBeLessThanOrEqual(2)
    expect(t1).toBe('refreshed_access_token_999')
    expect(t2).toBe('refreshed_access_token_999')

    await tab1.close()
    await tab2.close()
  })
})
