import { test, expect } from './fixtures'

// Coquille mission (AppShell) + écran Analyse (Synthèse + Canaux fusionnés).
test.describe('mission russosphere', () => {
  test('AppShell : marque + nav (Galaxie / Analyse), pas de bandeau de couverture', async ({ page }) => {
    await page.goto('/#/m/russosphere')

    // La marque renvoie désormais à la galaxie (plus de portfolio).
    await expect(page.locator('a[href="#/m/russosphere"]').first()).toBeVisible()

    // Nav produit — libellés FR par défaut (locale fr-FR). Synthèse + Canaux fusionnés → Analyse.
    const nav = page.getByRole('navigation')
    await expect(nav.getByRole('link', { name: 'Galaxie' })).toBeVisible()
    await expect(nav.getByRole('link', { name: 'Analyse' })).toBeVisible()

    // Le bandeau de couverture a été supprimé partout.
    await expect(page.getByText(/Couverture Telegram uniquement/i)).toHaveCount(0)
  })

  test('Analyse : rail de stats (santé + chiffres clés)', async ({ page }) => {
    await page.goto('/#/m/russosphere/analyse')

    await expect(page.getByRole('heading', { name: 'Santé des données' })).toBeVisible()
    await expect(page.getByRole('heading', { name: 'Chiffres clés' })).toBeVisible()

    // Tuiles de stats réelles (labels StatCard).
    await expect(page.getByText('Communautés', { exact: true })).toBeVisible()
    await expect(page.getByText('Densité', { exact: true })).toBeVisible()
  })

  test('Analyse : la table analytique a des lignes', async ({ page }) => {
    await page.goto('/#/m/russosphere/analyse')

    // En-tête de la table des canaux.
    await expect(page.getByRole('heading', { name: /Tous les canaux/ })).toBeVisible()

    // La table DataTable est rendue avec des lignes de corps.
    const table = page.getByRole('table')
    await expect(table).toBeVisible()

    const rows = table.locator('tbody tr')
    await expect.poll(async () => rows.count(), { timeout: 15_000 }).toBeGreaterThan(0)
  })

  test('anciens liens : /channels et /synthese redirigent vers /analyse', async ({ page }) => {
    await page.goto('/#/m/russosphere/channels')
    await expect(page).toHaveURL(/#\/m\/russosphere\/analyse$/)
  })
})
