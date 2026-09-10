/**
 * check-ui-contract.ts — Idéfix static UI-contract auditor (Phase 1C).
 *
 * A dependency-free (Node built-ins + tsx) scanner over `src/**\/*.{ts,tsx}`.
 * It enforces the design-system contract that keeps color/spacing decisions in
 * the token layer instead of scattered literals, and that keeps pages/data-views
 * structurally honest. It is a REPORTER, not a fixer.
 *
 * ADVISORY FOR NOW: the components still predate tokenization (Phase 2), so a
 * large non-zero baseline is EXPECTED and acceptable. The script must always run
 * to completion, print a grouped summary + total, and exit non-zero if anything
 * was found. It never throws on a single bad file (each file is try/caught).
 *
 * Checks:
 *   1. raw color literals (#hex / rgb( / hsl() — allowed ONLY in the token files
 *      (missions.ts, graph/palette.ts).
 *   2. inline `style={{…}}` setting a color/background/border property — allowed
 *      for data-driven layout (width/height/transform) and inside the graph
 *      renderer (src/graph/**, GalaxyCanvas, GraphView) which paints a canvas.
 *   3. arbitrary pixel values inside className brackets (e.g. w-[13px]).
 *   4. layering: primitives live under components/ui/, composites under
 *      components/patterns/ (reported, not fatal, if the dirs don't exist yet).
 *   5. every route/page composes a shell + a page-header — full-bleed
 *      GraphView/GalaxyCanvas are allowlisted.
 *   6. every data view branches loading / empty / error.
 */
import { readdirSync, readFileSync, statSync, existsSync } from 'node:fs'
import { join, dirname, relative, sep, basename } from 'node:path'
import { fileURLToPath } from 'node:url'

// ── Paths ────────────────────────────────────────────────────────────────────
const HERE = dirname(fileURLToPath(import.meta.url))
const ROOT = join(HERE, '..') // webapp/
const SRC = join(ROOT, 'src')

// ── Allowlists (single source of truth — keep labeled + at the top) ───────────
/** Files permitted to hold raw color literals (the token / data layer). */
const COLOR_TOKEN_FILES = new Set(['src/data/missions.ts', 'src/graph/palette.ts'])
/** Dirs whose inline style props are data-driven canvas paint, not UI chrome. */
const STYLE_ALLOW_DIR_PREFIXES = ['src/graph/']
/** Basenames whose inline style props are exempt (the full-bleed graph views). */
const STYLE_ALLOW_BASENAMES = new Set(['GalaxyCanvas.tsx', 'GraphView.tsx'])
/** Full-bleed pages exempt from the shell + page-header requirement (check 5). */
const FULL_BLEED_PAGES = new Set(['GraphView.tsx', 'GalaxyCanvas.tsx'])
/** src/screens files that are NOT route pages (shells / registries / helpers). */
const NOT_A_PAGE = new Set(['ScienceShell.tsx', 'registry.tsx', 'docs-ui.tsx', 'ValidationState.tsx'])

// ── Types ─────────────────────────────────────────────────────────────────────
interface Finding {
  check: string
  file: string // repo-relative, forward-slashed
  line: number
  detail: string
}
const findings: Finding[] = []
const add = (check: string, file: string, line: number, detail: string) =>
  findings.push({ check, file, line, detail })

// ── Helpers ───────────────────────────────────────────────────────────────────
const rel = (abs: string) => relative(ROOT, abs).split(sep).join('/')
const lineAt = (text: string, index: number) => text.slice(0, index).split('\n').length

/** Recursively collect *.ts / *.tsx under a directory. */
function walk(dir: string): string[] {
  const out: string[] = []
  let entries: ReturnType<typeof readdirSync>
  try {
    entries = readdirSync(dir, { withFileTypes: true })
  } catch {
    return out
  }
  for (const e of entries) {
    const p = join(dir, e.name)
    if (e.isDirectory()) out.push(...walk(p))
    else if (/\.tsx?$/.test(e.name)) out.push(p)
  }
  return out
}

/** Strip line (`//`) and block (`/* … *\/`) comments so we don't match inside them.
 *  Deliberately naive (no string-awareness) — good enough for literal detection
 *  and never crashes. Returns text with comments blanked (length preserved). */
function stripComments(src: string): string {
  let out = src.replace(/\/\*[\s\S]*?\*\//g, (m) => m.replace(/[^\n]/g, ' '))
  out = out
    .split('\n')
    .map((l) => {
      const i = l.indexOf('//')
      return i === -1 ? l : l.slice(0, i) + ' '.repeat(l.length - i)
    })
    .join('\n')
  return out
}

/** Extract balanced `style={{ … }}` object bodies with their start offset. */
function extractStyleObjects(src: string): { body: string; index: number }[] {
  const res: { body: string; index: number }[] = []
  const re = /style\s*=\s*\{\{/g
  let m: RegExpExecArray | null
  while ((m = re.exec(src))) {
    const start = m.index + m[0].length
    let depth = 2 // we already consumed `{{`
    let i = start
    for (; i < src.length && depth > 0; i++) {
      if (src[i] === '{') depth++
      else if (src[i] === '}') depth--
    }
    res.push({ body: src.slice(start, i - 2), index: m.index })
  }
  return res
}

/** Is a JSX/CSS style property name color-bearing (vs. allowed layout)? */
function isColorProp(name: string): boolean {
  const n = name.toLowerCase()
  if (/color/.test(n)) return true // color, backgroundColor, borderColor, caretColor…
  if (n.startsWith('background')) return true // background, backgroundImage…
  if (n === 'border' || /^border(top|right|bottom|left)$/.test(n)) return true // shorthand → carries color
  if (n === 'fill' || n === 'stroke' || n === 'boxshadow' || n === 'outline') return true
  return false // width / height / transform / borderRadius / opacity / … are fine
}

// ── The scan ──────────────────────────────────────────────────────────────────
const files = walk(SRC)

for (const abs of files) {
  const file = rel(abs)
  const base = basename(abs)
  let src: string
  try {
    src = readFileSync(abs, 'utf8')
  } catch (err) {
    add('read-error', file, 0, `could not read file: ${(err as Error).message}`)
    continue
  }

  try {
    const code = stripComments(src)

    // CHECK 1 — raw color literals (outside the token layer) ───────────────────
    if (!COLOR_TOKEN_FILES.has(file)) {
      const colorRe = /#[0-9a-fA-F]{3,8}\b|(?:rgba?|hsla?)\s*\(/g
      let m: RegExpExecArray | null
      while ((m = colorRe.exec(code))) {
        add('1·raw-color-literal', file, lineAt(code, m.index), m[0].trim())
      }
    }

    // CHECK 2 — inline style color/background/border props ──────────────────────
    const styleExempt =
      STYLE_ALLOW_DIR_PREFIXES.some((p) => file.startsWith(p)) || STYLE_ALLOW_BASENAMES.has(base)
    if (!styleExempt) {
      for (const { body, index } of extractStyleObjects(code)) {
        // property keys are identifiers/strings immediately before a `:`
        const propRe = /(?:^|[{,\s])(['"]?)([A-Za-z-]+)\1\s*:/g
        let pm: RegExpExecArray | null
        while ((pm = propRe.exec(body))) {
          if (isColorProp(pm[2])) {
            add('2·inline-style-color', file, lineAt(code, index), `style={{ …${pm[2]}… }}`)
          }
        }
      }
    }

    // CHECK 3 — arbitrary px in className brackets (e.g. w-[13px]) ──────────────
    const pxRe = /[\w-]*-\[\d*\.?\d+px\]/g
    let px: RegExpExecArray | null
    while ((px = pxRe.exec(code))) {
      add('3·arbitrary-px', file, lineAt(code, px.index), px[0])
    }
  } catch (err) {
    // Never let one pathological file abort the whole audit.
    add('scan-error', file, 0, `scan failed: ${(err as Error).message}`)
  }
}

// CHECK 4 — component layering (primitives → ui/, composites → patterns/) ──────
const UI_DIR = join(SRC, 'components', 'ui')
const PATTERNS_DIR = join(SRC, 'components', 'patterns')
const uiExists = existsSync(UI_DIR) && statSync(UI_DIR).isDirectory()
const patternsExists = existsSync(PATTERNS_DIR) && statSync(PATTERNS_DIR).isDirectory()
if (uiExists) {
  // Primitives must not import composites (patterns) — that inverts the layering.
  for (const abs of walk(UI_DIR)) {
    const file = rel(abs)
    const src = (() => {
      try {
        return readFileSync(abs, 'utf8')
      } catch {
        return ''
      }
    })()
    const m = /from\s+['"][^'"]*components\/patterns[^'"]*['"]/.exec(src)
    if (m) add('4·layering', file, lineAt(src, m.index), 'primitive (components/ui) imports a composite (components/patterns)')
  }
}

// CHECK 5 — route pages compose a shell + a page-header ────────────────────────
// NOTE (interpretation): mission pages currently rely on the router <Outlet> for
// their shell rather than self-composing a shell primitive, and use raw <h1>/
// <header> for their header. Science docs compose <DocPage> (the doc shell+header).
// This check measures distance to the Phase-2 target where every page self-composes
// a <PageShell> + <PageHeader>. Full-bleed graph views are allowlisted.
const SCREENS = join(SRC, 'screens')
for (const abs of walk(SCREENS)) {
  const base = basename(abs)
  if (!base.endsWith('.tsx') || NOT_A_PAGE.has(base) || FULL_BLEED_PAGES.has(base)) continue
  const file = rel(abs)
  let src: string
  try {
    src = readFileSync(abs, 'utf8')
  } catch {
    continue
  }
  const hasHeader = /<(PageHeader|DocPage|header|h1)\b/.test(src)
  const hasShell = /\b\w*Shell\b/.test(src) || /<\w*Shell\b/.test(src) || /\bDocPage\b/.test(src)
  if (!hasShell) add('5·page-shell', file, 1, 'route page does not compose a shell primitive')
  if (!hasHeader) add('5·page-header', file, 1, 'route page has no page-header region (<h1>/<header>/PageHeader/DocPage)')
}

// CHECK 6 — data views branch loading / empty / error ─────────────────────────
for (const abs of files) {
  if (!abs.endsWith('.tsx')) continue
  const file = rel(abs)
  let src: string
  try {
    src = readFileSync(abs, 'utf8')
  } catch {
    continue
  }
  const isDataView =
    /from\s+['"][^'"]*data\/loaders['"]/.test(src) || /\buseAsync\b/.test(src) || /\buseGraphModel\b/.test(src)
  if (!isDataView) continue
  const hasLoading = /\bloading\b/.test(src) || /<Spinner\b/.test(src)
  const hasEmpty = /\bEmptyState\b/.test(src) || /\bempty\b/i.test(src)
  const hasError = /\berror\b/i.test(src) || /\.catch\s*\(/.test(src) || /\bcatch\s*\(/.test(src)
  if (!hasLoading) add('6·data-loading', file, 1, 'data view has no loading branch')
  if (!hasEmpty) add('6·data-empty', file, 1, 'data view has no empty branch')
  if (!hasError) add('6·data-error', file, 1, 'data view has no error branch')
}

// CHECK 7 — brand chrome: BrandMark in shell + auth, Signature present, and the
// logo asset is consumed ONLY through the BrandMark pattern (§15.5). ──────────
const BRAND_MARK_HOSTS = ['src/app/AppShell.tsx']
const BRAND_PATTERN_FILE = 'src/components/patterns/BrandMark.tsx'
const BRAND_CONFIG_FILE = 'src/brand.config.ts'
const readSafe = (abs: string) => {
  try {
    return readFileSync(abs, 'utf8')
  } catch {
    return ''
  }
}
for (const rp of BRAND_MARK_HOSTS) {
  const src = readSafe(join(ROOT, rp))
  if (src && !/<BrandMark\b/.test(src)) add('7·brand-mark', rp, 1, 'shell/auth does not render <BrandMark>')
}
// Signature must appear somewhere (client-facing attribution, §15.4).
if (!files.some((abs) => /<Signature\b/.test(readSafe(abs)))) {
  add('7·signature', 'src/', 1, 'no route renders <Signature>')
}
// The logo asset path must not be referenced outside the BrandMark pattern / config.
for (const abs of files) {
  const file = rel(abs)
  if (file === BRAND_PATTERN_FILE || file === BRAND_CONFIG_FILE) continue
  const code = stripComments(readSafe(abs))
  const m = /['"`][^'"`]*\/brand\/[^'"`]*['"`]/.exec(code)
  if (m) add('7·brand-asset', file, lineAt(code, m.index), 'logo asset referenced outside BrandMark pattern')
}

// ── Report ────────────────────────────────────────────────────────────────────
const GAL = 'src/components/GalaxyCanvas.tsx'
const groups = new Map<string, Finding[]>()
for (const f of findings) {
  if (!groups.has(f.check)) groups.set(f.check, [])
  groups.get(f.check)!.push(f)
}

console.log('\n══════════════════════════════════════════════════════════════════')
console.log(' Idéfix — UI-contract audit (Phase 1C · advisory until Phase 2)')
console.log('══════════════════════════════════════════════════════════════════')
console.log(` scanned: ${files.length} file(s) under src/`)
console.log(` components/ui present: ${uiExists ? 'yes' : 'no (Phase 2)'} · components/patterns present: ${patternsExists ? 'yes' : 'no (Phase 2)'}`)

for (const check of [...groups.keys()].sort()) {
  const list = groups.get(check)!
  console.log(`\n▸ ${check} — ${list.length} finding(s)`)
  for (const f of list.slice(0, 100)) {
    console.log(`    ${f.file}:${f.line}  ${f.detail}`)
  }
  if (list.length > 100) console.log(`    … and ${list.length - 100} more`)
}

console.log('\n──────────────────────────── summary ────────────────────────────')
for (const check of [...groups.keys()].sort()) {
  console.log(`  ${check.padEnd(26)} ${String(groups.get(check)!.length).padStart(4)}`)
}
const total = findings.length
const galTotal = findings.filter((f) => f.file === GAL).length
console.log('  ' + '─'.repeat(30))
console.log(`  ${'TOTAL'.padEnd(26)} ${String(total).padStart(4)}`)
console.log(`  ${'TOTAL excl. GalaxyCanvas'.padEnd(26)} ${String(total - galTotal).padStart(4)}`)
console.log('══════════════════════════════════════════════════════════════════\n')

process.exit(total > 0 ? 1 : 0)
