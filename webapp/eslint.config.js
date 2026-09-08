// ─────────────────────────────────────────────────────────────────────────────
// ESLint flat config (ESM) — Idéfix web app.
//
// Composes:
//   • @eslint/js               → JS recommended
//   • typescript-eslint        → TS recommended (non-type-checked: fast, no project
//                                service, avoids OneDrive type-info overhead)
//   • eslint-plugin-react-hooks→ rules-of-hooks (error) + exhaustive-deps (warn)
//   • eslint-plugin-better-tailwindcss → UI-contract keystone
//
// KEYSTONE RULE (verified against the INSTALLED package, v4.6.1):
//   rule id  : better-tailwindcss/no-unknown-classes      ← NOT "no-unregistered-classes"
//   severity : error  (any class not registered by Tailwind is a hard failure)
//   entry pt : settings["better-tailwindcss"].entryPoint = "src/index.css"
//              → the Tailwind v4 CSS-first entry; makes the @theme tokens
//                (ink/brand/gold/azure/scarlet/jade, --font-*, --radius-*, …)
//                resolve as REGISTERED utilities. (`entryPoint` is the v4 option;
//                `tailwindConfig` would be its v3 counterpart — not used here.)
//
// ADVISORY FOR NOW: the existing components still use raw Tailwind palette classes
// and hardcoded hex; tokenization lands in Phase 2. Expect a non-zero baseline.
// This config only needs to LOAD cleanly and RUN — see `eslint --print-config`.
// ─────────────────────────────────────────────────────────────────────────────
import js from '@eslint/js'
import globals from 'globals'
import tseslint from 'typescript-eslint'
import reactHooks from 'eslint-plugin-react-hooks'
import betterTailwind from 'eslint-plugin-better-tailwindcss'

export default tseslint.config(
  // ── Never lint build output, deps, or the plain-JS build scripts ────────────
  {
    ignores: ['dist/**', 'node_modules/**', '.vercel/**', 'public/**', 'scripts/*.mjs'],
  },

  // ── Base recommended rulesets ───────────────────────────────────────────────
  js.configs.recommended,
  ...tseslint.configs.recommended,

  // ── Application source (browser runtime) ────────────────────────────────────
  {
    files: ['src/**/*.{ts,tsx}'],
    languageOptions: {
      ecmaVersion: 2022,
      sourceType: 'module',
      globals: { ...globals.browser },
    },
    plugins: {
      'react-hooks': reactHooks,
      'better-tailwindcss': betterTailwind,
    },
    settings: {
      // Point the Tailwind resolver at the v4 CSS-first entry so @theme tokens
      // count as registered classes (relative to this config's directory).
      'better-tailwindcss': {
        entryPoint: 'src/index.css',
      },
    },
    rules: {
      // React hooks — the two classic rules (kept minimal & predictable; the app
      // already relies on the `react-hooks/exhaustive-deps` id in disable comments).
      'react-hooks/rules-of-hooks': 'error',
      'react-hooks/exhaustive-deps': 'warn',

      // KEYSTONE — every class must be registered by Tailwind (incl. @theme tokens).
      // Whitelist: the app's legitimate global component classes (.epi-*, .handle
      // defined in index.css Tier 3) and the arbitrary attribute-variant bracket
      // syntax used with Headless UI (`data-[…]`, `aria-[…]`).
      'better-tailwindcss/no-unknown-classes': [
        'error',
        {
          ignore: [
            '^epi-', // .epi-computed / .epi-hypothesis / .epi-evidence / .epi-limit
            '^handle$', // .handle (@handles bleu Telegram)
            'data-\\[', // data-[focus]:… / data-[disabled]:… (Headless UI)
            'aria-\\[', // aria-[…] attribute variants
          ],
        },
      ],

      // Stylistic UI-contract helpers — advisory (warn) so they never block CI now.
      'better-tailwindcss/enforce-consistent-class-order': 'warn',
      'better-tailwindcss/no-duplicate-classes': 'warn',
    },
  },

  // ── Node tooling (contract script + this config) ────────────────────────────
  {
    files: ['scripts/**/*.{ts,mts,cts}', 'eslint.config.js', 'vite.config.ts'],
    languageOptions: {
      ecmaVersion: 2022,
      sourceType: 'module',
      globals: { ...globals.node },
    },
  },
)
