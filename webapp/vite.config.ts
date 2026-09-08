import { fileURLToPath } from 'node:url'
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

// Build STATIQUE, no-backend : base relative pour un hébergement sous n'importe
// quel chemin (GitHub Pages, file://). Les bundles JSON par mission sont servis
// depuis public/data/<mission>/ (produits hors-ligne par scripts/export_static.py).
export default defineConfig({
  base: './',
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
    },
  },
  build: { outDir: 'dist', sourcemap: false },
})
