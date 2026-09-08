import { test, expect } from './fixtures'

// Galaxie (GraphView → GalaxyCanvas, lazy + data-loaded). En DEV, GalaxyCanvas
// expose la poignée Cytoscape sur window.__cy — on l'inspecte pour vérifier que la
// scène a des nœuds, puis que la vue « Compound » matérialise des boîtes-communautés
// (nœuds parents kind="box"). Assertions résilientes : le graphe est paresseux et
// se reconstruit à chaque changement de vue (l'ancienne instance cy est détruite).

// Compte des nœuds Cytoscape via window.__cy, tolérant à une instance transitoirement
// détruite (retourne -1 en cas d'erreur/absence ⇒ le poll retente).
function countNodes(page: import('@playwright/test').Page, selector?: string) {
  return page.evaluate((sel) => {
    const cy = (window as unknown as {
      __cy?: { destroyed?: () => boolean; nodes: (s?: string) => { length: number } }
    }).__cy
    try {
      if (!cy || (cy.destroyed && cy.destroyed())) return -1
      return cy.nodes(sel).length
    } catch {
      return -1
    }
  }, selector)
}

test.describe('galaxie (graph)', () => {
  test('la scène a des nœuds, et la vue Compound produit des boîtes-communautés', async ({ page }) => {
    await page.goto('/#/m/russosphere/graph')

    // 1) La scène galaxie se monte et contient des nœuds (nébuleuses).
    await expect
      .poll(() => countNodes(page), { timeout: 30_000, message: 'window.__cy doit exposer des nœuds' })
      .toBeGreaterThan(0)

    // En vue galaxie, aucune boîte-communauté (kind="box").
    await expect.poll(() => countNodes(page, '[kind="box"]'), { timeout: 10_000 }).toBe(0)

    // 2) Bascule vers la vue « Compound ».
    const compoundBtn = page.getByRole('button', { name: 'Compound' })
    await expect(compoundBtn).toBeVisible()
    await compoundBtn.click()

    // Des boîtes-communautés (nœuds parents kind="box") apparaissent.
    await expect
      .poll(() => countNodes(page, '[kind="box"]'), {
        timeout: 30_000,
        message: 'la vue Compound doit rendre des nœuds kind="box"',
      })
      .toBeGreaterThan(0)

    // 3) Retour à la vue « Galaxie » — la scène a de nouveau des nœuds.
    await page.getByRole('button', { name: 'Galaxie' }).click()
    await expect.poll(() => countNodes(page), { timeout: 30_000 }).toBeGreaterThan(0)
  })
})
