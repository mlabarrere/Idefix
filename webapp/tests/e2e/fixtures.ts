// Fixtures e2e communes. Le verrou d'accès (PasswordGate) a été retiré : l'app
// démarre directement, sans écran de mot de passe. Ce module ne fait plus que
// ré-exporter `test`/`expect` pour que les specs partagent un point d'import
// unique (et pour rebrancher un bypass ici si un verrou revient un jour).
export { test, expect } from '@playwright/test'
