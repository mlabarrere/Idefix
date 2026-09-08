import { test, expect } from './fixtures'

// Le portfolio a été supprimé : l'accueil EST la galaxie. /#/missions (ancien
// point d'entrée) doit désormais rediriger vers la galaxie de la mission par défaut.
test.describe('pas de portfolio', () => {
  test('/#/missions redirige vers la galaxie par défaut', async ({ page }) => {
    await page.goto('/#/missions')
    await expect(page).toHaveURL(/#\/m\/russosphere$/)

    // La coquille mission est montée (nav produit visible), pas de cartes de portfolio.
    await expect(page.getByRole('navigation').getByRole('link', { name: 'Galaxie' })).toBeVisible()
  })
})
