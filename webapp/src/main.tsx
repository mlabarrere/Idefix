import React from 'react'
import ReactDOM from 'react-dom/client'
import { RouterProvider } from 'react-router-dom'
import { I18nextProvider } from 'react-i18next'
import i18n from './state/i18n'
import { router } from './router'
import { applyTheme, initialTheme } from './state/theme'
import './index.css'

// Applique le thème avant le rendu (évite le flash clair/sombre).
applyTheme(initialTheme())

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <I18nextProvider i18n={i18n}>
      <RouterProvider router={router} />
    </I18nextProvider>
  </React.StrictMode>,
)
