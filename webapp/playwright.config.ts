import { defineConfig, devices } from '@playwright/test'

// Harnais E2E « smoke / inspection » d'Idéfix — assertions déterministes
// (rôles, textes, comptes, classes). PAS de visual-regression (toHaveScreenshot),
// PAS de projets mobiles, PAS d'axe : ces couches sont explicitement différées.
//
// Chromium local uniquement (aucun Docker sur cette machine). Le serveur est le
// dev server Vite lancé par le bloc `webServer` ci-dessous.
const PORT = 5173
const BASE_URL = `http://localhost:${PORT}`

export default defineConfig({
  testDir: './tests/e2e',
  // Un seul navigateur : on ne veut pas de flakiness inter-worker sur une lib
  // graphe lazy + data-loaded. Fail-fast raisonnable, retry unique en CI.
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  workers: process.env.CI ? 1 : undefined,
  reporter: process.env.CI ? [['github'], ['html', { open: 'never' }]] : [['list'], ['html', { open: 'never' }]],

  use: {
    baseURL: BASE_URL,
    // Déterminisme : viewport fixe, thème clair, réduction des animations, et
    // locale FR (⇒ navigator.language='fr-FR' ⇒ i18n démarre en français, ce que
    // le spec i18n suppose avant de basculer en anglais).
    viewport: { width: 1280, height: 800 },
    colorScheme: 'light',
    locale: 'fr-FR',
    reducedMotion: 'reduce',
    trace: 'on-first-retry',
  },

  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],

  // Démarre Vite (port figé + strictPort ⇒ l'URL attendue est garantie, pas de
  // dérive de port). Cold start sur OneDrive : timeout large. Réutilise un serveur
  // déjà lancé en local, jamais en CI.
  webServer: {
    command: 'npm run dev -- --port 5173 --strictPort',
    url: BASE_URL,
    reuseExistingServer: !process.env.CI,
    timeout: 180_000,
    stdout: 'ignore',
    stderr: 'pipe',
  },
})
