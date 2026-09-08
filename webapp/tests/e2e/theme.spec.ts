import { test, expect } from './fixtures'

// Bascule de thème (ThemeToggle) — ajoute/retire .dark sur <html> et persiste
// dans localStorage['idefix-theme'].
test.describe('theme', () => {
  test('la bascule (dé)active .dark sur <html> et persiste', async ({ page }) => {
    await page.goto('/#/m/russosphere')

    const html = page.locator('html')
    // Départ en clair (use.colorScheme = 'light', pas de préférence stockée).
    await expect(html).not.toHaveClass(/dark/)

    // Le header mission n'a qu'un ThemeToggle (aria-label FR).
    const toggle = page.getByRole('button', { name: 'Basculer le thème' })
    await expect(toggle).toBeVisible()

    // → sombre.
    await toggle.click()
    await expect(html).toHaveClass(/dark/)
    await expect
      .poll(async () => page.evaluate(() => localStorage.getItem('idefix-theme')))
      .toBe('dark')

    // → clair (retour).
    await toggle.click()
    await expect(html).not.toHaveClass(/dark/)
    await expect
      .poll(async () => page.evaluate(() => localStorage.getItem('idefix-theme')))
      .toBe('light')
  })
})
