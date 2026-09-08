/**
 * check-i18n-parity.ts — i18n completeness gate (§16.5).
 *
 * Key parity is ALREADY enforced by the compiler: every locale is typed
 * `: Messages` against fr.ts, so a missing/extra key fails `tsc`. This script
 * adds what the type system cannot see:
 *   1. key parity across all locales (defence-in-depth vs. a stray `as any`),
 *   2. no empty / whitespace-only / `__MISSING__` placeholder values,
 *   3. no unresolved `{{placeholder}}` mismatch vs. the source (fr) — a value
 *      that drops or invents an interpolation token is a real translation bug.
 *
 * Dependency-free (tsx + Node built-ins). Reporter: prints a summary and exits
 * non-zero on any finding. `lb` is expected to be human-reviewed (§16.7) but
 * must still carry non-empty values — this gate enforces presence, not quality.
 */
import { fr } from '../src/state/locales/fr'
import { en } from '../src/state/locales/en'
import { es } from '../src/state/locales/es'
import { nl } from '../src/state/locales/nl'
import { lb } from '../src/state/locales/lb'
import { de } from '../src/state/locales/de'

const LOCALES: Record<string, Record<string, string>> = { fr, en, es, nl, lb, de }
const SOURCE = 'fr'
const MISSING_MARKER = '__MISSING__'

const problems: string[] = []
const sourceKeys = Object.keys(LOCALES[SOURCE])
const sourceKeySet = new Set(sourceKeys)

/** Set of `{{token}}` names in a string. */
const placeholders = (v: string): Set<string> =>
  new Set([...v.matchAll(/\{\{\s*(\w+)\s*\}\}/g)].map((m) => m[1]))

for (const [name, dict] of Object.entries(LOCALES)) {
  const keys = Object.keys(dict)
  const keySet = new Set(keys)

  // 1 — key parity vs. source
  for (const k of sourceKeys) if (!keySet.has(k)) problems.push(`[${name}] missing key: ${k}`)
  for (const k of keys) if (!sourceKeySet.has(k)) problems.push(`[${name}] extra key: ${k}`)

  // 2 & 3 — value health
  for (const k of keys) {
    if (!sourceKeySet.has(k)) continue
    const v = dict[k]
    if (typeof v !== 'string' || v.trim() === '') problems.push(`[${name}] empty value: ${k}`)
    else if (v.includes(MISSING_MARKER)) problems.push(`[${name}] ${MISSING_MARKER} value: ${k}`)
    else {
      const want = placeholders(LOCALES[SOURCE][k])
      const got = placeholders(v)
      for (const p of want) if (!got.has(p)) problems.push(`[${name}] dropped {{${p}}} in: ${k}`)
      for (const p of got) if (!want.has(p)) problems.push(`[${name}] stray {{${p}}} in: ${k}`)
    }
  }
}

console.log('\n════════════════ i18n parity & completeness ════════════════')
console.log(` locales: ${Object.keys(LOCALES).join(', ')} · source: ${SOURCE} · keys: ${sourceKeys.length}`)
if (problems.length === 0) {
  console.log(' ✓ all locales complete — no missing keys, empty values, or placeholder drift.')
} else {
  for (const p of problems.slice(0, 200)) console.log(`   ✗ ${p}`)
  if (problems.length > 200) console.log(`   … and ${problems.length - 200} more`)
  console.log(`\n ${problems.length} problem(s).`)
}
console.log('═════════════════════════════════════════════════════════════\n')
process.exit(problems.length > 0 ? 1 : 0)
