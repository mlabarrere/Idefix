// « Galaxie du renseignement » — PORT React fidèle de frontend/js/galaxy.js,
// ENRICHI de la couche DOMAINES (sites web) demandée par Micky.
//
// Méta-graphe : 1 communauté = 1 NÉBULEUSE (dégradé radial + halo + respiration),
// arcs-ponts dorés (top-30), fond étoilé maison. Clic nébuleuse -> BLOOM (éclosion
// en canaux, fcose local). Clic canal -> sélection partagée -> drawer.
//
// DOMAINES : au bloom, les sites cités par les canaux éclos apparaissent en
// hexagones, DÉDUPLIQUÉS globalement (un domaine cité par plusieurs canaux/sphères
// = un nœud MULTI-LIÉ qui fait pont). Catégorisés par heuristique (presse / réseau
// social / vidéo / infra adverse / institutionnel / autre) -> couleur + filtre.
//
// Filtres de NŒUDS : type (canaux / sites web), catégorie de site, crédibilité,
// archétype, sphère. + légende + recherche fly-to. Lib = Cytoscape + fcose (locale).
// Fond TOUJOURS sombre (espace), quel que soit le thème.
//
// ponytail: Split into NebulaeLayer + BloomCanvas + DomainNodes + Filters components,
// upgrade: when bundle size (currently ~500kb) impacts Vercel deployment metrics
import { useEffect, useMemo, useRef, useState } from 'react'
import { useTranslation } from 'react-i18next'
import cytoscape, { type Core, type EdgeSingular, type NodeSingular } from 'cytoscape'
import { loadEmbedSnapshot, loadSnapshot } from '../data/loaders'
import type { Bridge, Community, RussosphereSnapshot, SphereChannel } from '../data/types'
import type { GraphModel } from '../graph/useGraphModel'
import { GALAXY } from '../graph/palette'
import { useSelection } from '../state/SelectionContext'
import { useSnapshotMode } from '../state/SnapshotMode'
import { EmptyState, Spinner, useAsync } from '../ui'

// Coordonnées de layout PRÉCALCULÉES (offline) portées sur communautés + canaux.
// Espace monde ABSOLU commun (canal placé dans un disque centré sur le centroïde
// de sa communauté). On les CONSOMME ici au lieu de relancer un force-layout.
type XY = { x?: number; y?: number }

/* ── helpers (portés) ── */
// Native CSS color-mix (Safari 16.2+, Chrome 111+) au lieu de hand-rolled lighten
const lighten = (hex: string, amt: number): string =>
  `color-mix(in srgb, ${hex} ${Math.round((1 - amt) * 100)}%, white)`
// Label court MAIS UNIQUE : plusieurs communautés partagent le même thème
// (« Relais francophones », « Géopolitique / agrégateurs »…) et ne se distinguent
// que par leur canal représentatif (suffixe ` · @handle`). On garde donc ce
// représentant, sinon 7 nébuleuses différentes s'affichent toutes pareil.
function shortLabel(l?: string | null): string {
  if (!l) return '—'
  const parts = String(l).split(' · ')
  const theme = parts[0].replace(/\s*\([^)]*\)\s*$/, '').trim()
  const rep = parts.slice(1).find((p) => p.trim().startsWith('@'))
  return rep ? `${theme} · ${rep.trim()}` : theme
}
const cssEsc = (s: string | number) => String(s).replace(/([^\w-])/g, '\\$1')

const ARCH: Record<string, { label: string }> = {
  source: { label: 'seeding-source' },
  hub: { label: 'forward-hub' },
  bridge: { label: 'cross-channel-bridge' },
  reactivator: { label: 'reactivator' },
}
const CRED_VALS: [string, string][] = [
  ['suspect', GALAXY.cred.suspect],
  ['other', GALAXY.cred.other],
  ['legit', GALAXY.cred.legit],
]

/* ── typologie de domaines (HEURISTIQUE côté client — à remplacer par une
   typologie offline). Ordre = priorité de match. ── */
// ponytail: Move to scripts/export_static.py for offline classification,
// upgrade: when domain data volume justifies pre-processing overhead
const DOM_CATS = [
  { key: 'adversary', label: 'infra adverse', color: GALAXY.dom.adversary },
  { key: 'social', label: 'réseau social', color: GALAXY.dom.social },
  { key: 'video', label: 'vidéo', color: GALAXY.dom.video },
  { key: 'news', label: 'presse / média', color: GALAXY.dom.news },
  { key: 'gov', label: 'institutionnel', color: GALAXY.dom.gov },
  { key: 'other', label: 'autre', color: GALAXY.dom.other },
] as const
type DomCatKey = (typeof DOM_CATS)[number]['key']
const DOM_COLOR: Record<string, string> = Object.fromEntries(DOM_CATS.map((c) => [c.key, c.color]))

const ADVERSARY_PAT = /(pravda|news-?front|southfront|geopolitik|reseauinternational|voltairenet|rt\.|russia\.?today|sputnik|ria\.ru|tass|katehon|tsargrad|strategic-culture|globalresearch|donbass|sodepa|afrique-?media|rrn|doppelganger)/i
const SOCIAL_PAT = /(t\.me|telegram|twitter|x\.com|facebook|fb\.com|fb\.me|vk\.com|vk\.ru|ok\.ru|instagram|tiktok|gab\.com|truthsocial|gettr|mastodon|threads)/i
const VIDEO_PAT = /(youtube|youtu\.be|rumble|odysee|dailymotion|vimeo|bitchute|dzen\.ru|rutube)/i
const NEWS_PAT = /(news|presse|journal|media|info|actu|quotidien|gazette|tribune|\.tv|\btv\b|figaro|lemonde|liberation|bfm|francetv|france24|20minutes|afp|reuters|lepoint|valeursactuelles|sudradio|cnews|parisien)/i
const GOV_PAT = /(\.gouv\.fr|\.gov\b|\.gov\.|europa\.eu|nato\.int|\.mil\b|elysee|defense\.gouv|interieur\.gouv|assemblee-nationale|senat\.fr|onu\.|un\.org)/i

function domainCategory(domain: string): DomCatKey {
  const d = String(domain).toLowerCase()
  if (ADVERSARY_PAT.test(d)) return 'adversary'
  if (GOV_PAT.test(d)) return 'gov'
  if (SOCIAL_PAT.test(d)) return 'social'
  if (VIDEO_PAT.test(d)) return 'video'
  if (NEWS_PAT.test(d)) return 'news'
  return 'other'
}

interface Indexed {
  COMM: Map<number, Community>
  CH: Map<number, SphereChannel & { commId: number; commColor: string; commLabel: string }>
  BR: Map<number, Bridge>
  maxBet: number
  maxSize: number
  suspRatio: Map<number, number>
}

function indexSnap(snap: RussosphereSnapshot): Indexed {
  const COMM = new Map<number, Community>()
  const CH = new Map<number, SphereChannel & { commId: number; commColor: string; commLabel: string }>()
  const BR = new Map<number, Bridge>()
  let maxBet = 0.001
  let maxSize = 1
  const suspRatio = new Map<number, number>()
  for (const c of snap.communities || []) {
    COMM.set(c.id, c)
    maxSize = Math.max(maxSize, c.size || c.channels.length)
    const n = c.channels.length || 1
    let susp = 0
    for (const ch of c.channels) {
      CH.set(ch.channel_id, { ...ch, commId: c.id, commColor: c.color, commLabel: c.label })
      if (ch.credibility_prior === 'suspect') susp++
    }
    suspRatio.set(c.id, susp / n)
  }
  for (const b of snap.bridges || []) {
    BR.set(b.channel_id, b)
    maxBet = Math.max(maxBet, b.betweenness || 0)
  }
  return { COMM, CH, BR, maxBet, maxSize, suspRatio }
}

function chArchetype(ix: Indexed, ch: SphereChannel): string {
  const b = ix.BR.get(ch.channel_id)
  const bet = b ? b.betweenness : ch.betweenness || 0
  if (bet >= 0.06) return 'bridge'
  if ((ch.engagement || 0) >= 1500000) return 'hub'
  if (ch.is_seed) return 'source'
  if (ch.credibility_prior === 'suspect' && bet > 0.005) return 'source'
  return 'reactivator'
}

interface Filters {
  cred: Set<string>
  arch: Set<string>
  comm: Set<number>
  domCat: Set<string>
  channels: boolean
  domains: boolean
}
const emptyFilters = (): Filters => ({ cred: new Set(), arch: new Set(), comm: new Set(), domCat: new Set(), channels: true, domains: true })

// `highlightIds` = ensemble de canaux d'un scénario. FILTRE DUR : le hors-scénario
// passe en .gone (display:none) → on ne voit QUE le scénario (membres dorés + cadrage).
// Piloté par ThemeLens (scénarios). Un seul mécanisme (applyStory).
// `cockpitTop` = sections injectées en HAUT du cockpit gauche (Thèmes / Histoires
// / Épisodes, fournies par Overview) — tous les contrôles vivent dans UN cockpit.
export function GalaxyCanvas({
  model,
  highlightIds,
  cockpitTop,
}: {
  model: GraphModel
  highlightIds?: number[] | null
  cockpitTop?: React.ReactNode
}) {
  const { missionId, select, selected } = useSelection()
  const { mode } = useSnapshotMode()
  // En mode 'embedding', on lit le snapshot regroupé par embeddings (repli sur
  // Analytics s'il est absent) → nébuleuses + arcs basculent instantanément.
  const { data: snap, loading } = useAsync(
    () => (mode === 'embedding'
      ? loadEmbedSnapshot(missionId).then((s) => s ?? loadSnapshot(missionId))
      : loadSnapshot(missionId)),
    [missionId, mode],
  )

  const boxRef = useRef<HTMLDivElement>(null)
  const cyHostRef = useRef<HTMLDivElement>(null)
  const starRef = useRef<HTMLCanvasElement>(null)
  const tipRef = useRef<HTMLDivElement>(null)
  const cyRef = useRef<Core | null>(null)
  const apiRef = useRef<{
    bloom: (id: number) => void
    focus: (chId: number) => void
    clearEgo: () => void
    recenter: () => void
    applyFilters: () => void
    applyStory: (ids: number[] | null) => void
  } | null>(null)
  const filtersRef = useRef<Filters>(emptyFilters())

  // `t` capturé dans une REF : les tooltips Cytoscape (HTML impératif construit dans
  // le gros useEffect) lisent `tRef.current` — `t` n'est donc PAS dans les deps de
  // cet effet, sinon toute la scène serait détruite/reconstruite à chaque changement
  // de langue (coûteux + perte d'état du graphe). Les tooltips reflètent la langue
  // au PROCHAIN survol, sans rebuild. Les libellés JSX, eux, utilisent `t` direct
  // (réactifs : le composant se re-rend via useTranslation).
  const { t } = useTranslation()
  const tRef = useRef(t)
  useEffect(() => {
    tRef.current = t
  }, [t])

  const [filters, setFilters] = useState<Filters>(emptyFilters())
  const [opened, setOpened] = useState<number[]>([])
  const [q, setQ] = useState('')
  // Vue GALAXIE (nébuleuses → bloom, comportement historique par DÉFAUT) vs
  // COMPOUND (toutes les communautés en BOÎTES étiquetées « ceci est la Russie /
  // la France », canaux visibles à l'intérieur — comme la démo cytoscape-fcose).
  const [viewMode, setViewMode] = useState<'galaxy' | 'compound'>('galaxy')

  filtersRef.current = filters
  const ix = useMemo(() => (snap ? indexSnap(snap) : null), [snap])

  /* ── recherche fly-to ── */
  const hits = useMemo(() => {
    if (!ix || !q.trim()) return []
    const needle = q.trim().toLowerCase().replace(/^@/, '')
    const out: { id: number; label: string; comm: string; color: string }[] = []
    for (const ch of ix.CH.values()) {
      const h = (ch.username || '#' + ch.channel_id).toLowerCase()
      if (h.includes(needle) || (ch.title || '').toLowerCase().includes(needle)) {
        out.push({ id: ch.channel_id, label: '@' + (ch.username || '#' + ch.channel_id), comm: shortLabel(ch.commLabel), color: ch.commColor })
        if (out.length >= 12) break
      }
    }
    return out
  }, [ix, q])

  /* ════════ STARFIELD (statique) ════════ */
  // Rendu UNIQUE au montage + un re-rendu au resize. Plus de boucle rAF : le champ
  // d'étoiles était l'une des sources de charge CPU permanente. « Au repos » = le
  // scintillement à sin=0, soit l'alpha de base `a` de chaque étoile (identique).
  useEffect(() => {
    const cv = starRef.current
    const host = boxRef.current
    if (!cv || !host) return
    const ctx = cv.getContext('2d')!
    const DPR = Math.min(2, window.devicePixelRatio || 1)
    const draw = () => {
      const w = host.clientWidth || 1
      const h = host.clientHeight || 1
      const W = (cv.width = w * DPR)
      const H = (cv.height = h * DPR)
      cv.style.width = w + 'px'
      cv.style.height = h + 'px'
      const count = Math.round((w * h) / 5200)
      ctx.clearRect(0, 0, W, H)
      for (let i = 0; i < count; i++) {
        const x = Math.random() * W
        const y = Math.random() * H
        const r = (Math.random() * 1.3 + 0.25) * DPR
        const a = Math.random() * 0.6 + 0.15
        const hue = Math.random() < 0.12 ? 'gold' : Math.random() < 0.2 ? 'blue' : 'white'
        ctx.beginPath()
        ctx.arc(x, y, r, 0, Math.PI * 2)
        ctx.fillStyle = hue === 'gold' ? GALAXY.starfield.gold(a) : hue === 'blue' ? GALAXY.starfield.blue(a) : GALAXY.starfield.white(a)
        ctx.fill()
      }
    }
    draw()
    const ro = new ResizeObserver(draw)
    ro.observe(host)
    return () => ro.disconnect()
  }, [snap])

  /* ════════ CYTOSCAPE GALAXIE ════════ */
  useEffect(() => {
    if (!ix || !snap || !cyHostRef.current) return
    const host = cyHostRef.current

    /* ════════ MODE COMPOUND : boîtes-communautés (façon démo cytoscape-fcose) ════
       Toutes les communautés en BOÎTES étiquetées (« ceci est la Russie / la France »)
       avec leurs canaux VISIBLES à l'intérieur, positionnés par leurs coordonnées
       PRÉCALCULÉES (x/y offline, même repère que la galaxie) → layout 'preset',
       AUCUN force-layout, AUCUNE animation de nœud / transition / rAF (perf = étoile
       polaire). Cytoscape auto-dimensionne chaque parent autour de ses enfants. ── */
    if (viewMode === 'compound') {
      const comms = snap.communities || []
      // Garde-fou perf : au-delà d'un budget global de canaux rendus d'un coup, on
      // garde le TOP par engagement dans chaque boîte (proportionnel) et on ANNONCE
      // le nombre masqué sur la boîte + en console (jamais de troncature silencieuse).
      const BUDGET = 1500
      const totalCh = comms.reduce((s, c) => s + c.channels.length, 0)
      const capped = totalCh > BUDGET
      const cels: cytoscape.ElementDefinition[] = []
      let rendered = 0
      let hiddenTot = 0
      for (const c of comms) {
        const cxy = c as Community & XY
        const chans = c.channels
        const cap = capped ? Math.max(10, Math.round((BUDGET * chans.length) / totalCh)) : chans.length
        const kept =
          cap < chans.length
            ? chans.slice().sort((a, b) => (b.engagement || 0) - (a.engagement || 0)).slice(0, cap)
            : chans
        const nHidden = chans.length - kept.length
        hiddenTot += nHidden
        cels.push({
          data: {
            id: 'box-' + c.id,
            kind: 'box',
            commId: c.id,
            label: c.label, // DONNÉE brute (non traduite)
            boxLabel: shortLabel(c.label) + (nHidden ? `  +${nHidden}` : ''),
            color: c.color,
            count: c.size || chans.length,
            susp: c.n_suspects || 0,
            ndom: c.n_domains || 0,
            hidden: nHidden,
          },
        })
        const maxEng = Math.max(1, ...chans.map((x) => x.engagement || 0))
        kept.forEach((ch, i) => {
          const chxy = ch as SphereChannel & XY
          const b = ix.BR.get(ch.channel_id)
          const bet = b ? b.betweenness : ch.betweenness || 0
          const broker = bet > 0.04
          // coord PRÉCALCULÉE ; repli en grille autour du centroïde si absente (évite
          // l'empilement à l'origine, sans relancer de layout).
          const fx = chxy.x ?? (cxy.x ?? 0) + (((i % 24) - 12) * 14)
          const fy = chxy.y ?? (cxy.y ?? 0) + ((Math.floor(i / 24) - 6) * 14)
          cels.push({
            group: 'nodes',
            data: {
              id: 'ch-' + ch.channel_id,
              kind: 'channel',
              chId: ch.channel_id,
              commId: c.id,
              parent: 'box-' + c.id, // ENFANT du parent compound
              label: '@' + (ch.username || '#' + ch.channel_id),
              color: c.color,
              diam: broker ? 22 + 34 * (bet / ix.maxBet) : 12 + 16 * Math.sqrt((ch.engagement || 0) / maxEng),
              broker,
              seed: !!ch.is_seed,
              arch: chArchetype(ix, ch),
            },
            position: { x: fx, y: fy },
          })
          rendered++
        })
      }
      // eslint-disable-next-line no-console
      console.info(
        `[galaxie/compound] ${missionId} : ${rendered} canaux dans ${comms.length} boîtes` +
          (capped ? ` — ${hiddenTot} masqué(s) (budget ${BUDGET}, top-engagement par boîte)` : ' — aucun masquage'),
      )

      const cstyle: unknown = [
        {
          // BOÎTE-communauté = nœud compound PARENT : « ceci est la Russie / la France ».
          selector: 'node[kind="box"]',
          style: {
            shape: 'round-rectangle',
            'background-color': 'data(color)',
            'background-opacity': 0.07,
            'border-color': 'data(color)',
            'border-width': 2,
            'border-opacity': 0.6,
            padding: 26,
            label: 'data(boxLabel)',
            color: GALAXY.text.label,
            'font-family': 'JetBrains Mono, monospace',
            'font-size': '13px',
            'font-weight': 700,
            'text-valign': 'top',
            'text-halign': 'center',
            'text-margin-y': -4,
            'text-wrap': 'wrap',
            'text-max-width': 220,
            'text-outline-color': GALAXY.text.outline,
            'text-outline-width': 3,
            'min-zoomed-font-size': 7,
          },
        },
        {
          // CANAL enfant : même style que la galaxie (halo neutralisé, aucune transition).
          selector: 'node[kind="channel"]',
          style: {
            width: 'data(diam)',
            height: 'data(diam)',
            shape: 'ellipse',
            'background-color': 'data(color)',
            'background-opacity': 0.7,
            'border-color': 'data(color)',
            'border-width': 1.2,
            'border-opacity': 0.95,
            'underlay-color': 'data(color)',
            'underlay-opacity': 0,
            label: '',
          },
        },
        {
          selector: 'node[?broker]',
          style: {
            'border-color': GALAXY.gold,
            'border-width': 2.6,
            'background-opacity': 0.85,
            'underlay-color': GALAXY.gold,
            'underlay-opacity': 0.35,
            'underlay-padding': 4,
            label: 'data(label)',
            color: GALAXY.gold,
            'font-family': 'JetBrains Mono, monospace',
            'font-size': '9px',
            'font-weight': 700,
            'text-valign': 'bottom',
            'text-margin-y': 4,
            'text-outline-color': GALAXY.text.outline,
            'text-outline-width': 2,
          },
        },
        {
          selector: 'node[?seed]',
          style: {
            'border-color': GALAXY.seed,
            'border-width': 2.6,
            'underlay-color': GALAXY.seed,
            'underlay-opacity': 0.4,
            'underlay-padding': 4,
            label: 'data(label)',
            color: GALAXY.seed,
            'font-size': '10px',
            'font-weight': 700,
            'text-valign': 'bottom',
            'text-margin-y': 5,
            'text-outline-color': GALAXY.text.outline,
            'text-outline-width': 2,
          },
        },
        { selector: '.glow', style: { 'border-width': 5, 'underlay-opacity': 0.55, 'underlay-padding': 10 } },
        { selector: '.faded', style: { opacity: 0.22 } },
        { selector: '.dim', style: { opacity: 0.08 } },
        { selector: '.gone', style: { display: 'none' } },
        { selector: '.story-dim', style: { opacity: 0.06 } },
        {
          selector: '.story-member',
          style: { 'border-color': GALAXY.gold, 'border-width': 3, 'underlay-color': GALAXY.gold, 'underlay-opacity': 0.45, 'underlay-padding': 6 },
        },
        { selector: 'node[kind="channel"]:selected', style: { 'border-color': GALAXY.selected, 'border-width': 5 } },
      ]

      const cy = cytoscape({
        container: host,
        elements: cels,
        style: cstyle as cytoscape.StylesheetJson,
        layout: { name: 'preset' }, // positions offline, AUCUN force-layout au runtime
        minZoom: 0.03,
        maxZoom: 3.4,
        wheelSensitivity: 0.45,
        pixelRatio: 'auto',
      })
      cyRef.current = cy
      if (import.meta.env.DEV) (window as unknown as { __cy?: Core }).__cy = cy
      // Vue figée : ni glissement de boîte (déplacerait toute une communauté), ni
      // sélection de boîte — seuls les canaux sont sélectionnables (→ dossier).
      cy.nodes().ungrabify()
      cy.nodes('node[kind="box"]').unselectify()

      let fitted = false
      const refit = () => {
        if (cy.destroyed()) return
        cy.resize()
        if (!fitted && host.clientWidth > 1 && host.clientHeight > 1) {
          cy.fit(cy.elements(), 60)
          fitted = true
        }
      }
      const ro = new ResizeObserver(refit)
      ro.observe(host)
      requestAnimationFrame(refit)

      /* filtres (best-effort) — estompe canaux/boîtes hors filtre, tout reste en place */
      const chMatches = (cid: number, arch: string) => {
        const f = filtersRef.current
        const ch = ix.CH.get(cid)
        if (!ch) return true
        if (f.cred.size) {
          const cv = ch.credibility_prior === 'suspect' ? 'suspect' : ch.credibility_prior === 'other' ? 'other' : 'legit'
          if (!f.cred.has(cv)) return false
        }
        if (f.arch.size && !f.arch.has(arch)) return false
        if (f.comm.size && !f.comm.has(ch.commId)) return false
        return true
      }
      const applyFilters = () => {
        const f = filtersRef.current
        const anyComm = f.comm.size > 0
        cy.nodes('node[kind="box"]').forEach((n) => {
          n.removeClass('dim')
          if (anyComm && !f.comm.has(n.data('commId'))) n.addClass('dim')
        })
        cy.nodes('node[kind="channel"]').forEach((n) => {
          n.removeClass('dim gone')
          if (!f.channels) n.addClass('gone')
          else if (!chMatches(n.data('chId'), n.data('arch'))) n.addClass('dim')
        })
      }

      /* tooltip (local, même présentation que la galaxie) */
      const tip = tipRef.current!
      const moveTip = (pos: { x: number; y: number }) => {
        if (tip.style.display !== 'block' || !pos) return
        const w = host.clientWidth
        const h = host.clientHeight
        tip.style.left = Math.min(pos.x + 16, w - tip.offsetWidth - 14) + 'px'
        tip.style.top = Math.min(pos.y + 14, h - tip.offsetHeight - 14) + 'px'
      }
      const showTip = (html: string, pos: { x: number; y: number }) => {
        tip.innerHTML = html
        tip.style.display = 'block'
        moveTip(pos)
      }
      const hideTip = () => (tip.style.display = 'none')
      const tipBox = (n: NodeSingular) =>
        `<div style="color:${n.data('color')};font-weight:700">${n.data('label')}</div><div style="opacity:.8">${tRef.current('graph.tooltip.commStats', { count: n.data('count'), susp: n.data('susp'), ndom: n.data('ndom') })}</div>` +
        (n.data('hidden') ? `<div style="opacity:.7">${tRef.current('graph.tooltip.hiddenChannels', { hidden: n.data('hidden') })}</div>` : '')
      const tipCh = (n: NodeSingular) => {
        const ch = ix.CH.get(n.data('chId'))
        const arch = ARCH[n.data('arch')]?.label || n.data('arch')
        return `<div style="color:${n.data('color')};font-weight:700">${n.data('label')}</div>${ch?.title ? `<div style="opacity:.8">${ch.title}</div>` : ''}<div style="opacity:.8">${tRef.current('graph.tooltip.credibility', { cred: ch?.credibility_prior || '—', arch })}</div>${n.data('broker') ? `<div style="color:${GALAXY.gold}">${tRef.current('graph.tooltip.broker')}</div>` : ''}<div style="color:${GALAXY.text.telegram};margin-top:3px">${tRef.current('graph.tooltip.clicDossier')}</div>`
      }

      cy.on('mouseover', 'node[kind="channel"]', (e) => {
        e.target.addClass('glow')
        showTip(tipCh(e.target), e.renderedPosition)
        host.style.cursor = 'pointer'
      })
      cy.on('mouseout', 'node[kind="channel"]', (e) => {
        e.target.removeClass('glow')
        hideTip()
        host.style.cursor = ''
      })
      cy.on('mouseover', 'node[kind="box"]', (e) => {
        showTip(tipBox(e.target), e.renderedPosition)
        host.style.cursor = 'pointer'
      })
      cy.on('mouseout', 'node[kind="box"]', hideTip)
      cy.on('mousemove', (e) => moveTip(e.renderedPosition))
      cy.on('tap', 'node[kind="channel"]', (e) => select(e.target.data('chId')))
      // Tap sur une boîte (compound) : sélection sans recadrage caméra (zoom auto désactivé §4).
      cy.on('tap', (e) => {
        if (e.target === cy) select(null)
      })

      apiRef.current = {
        // « éclore » depuis la liste des sphères = cadrer instantanément la boîte.
        bloom: (commId: number) => {
          const box = cy.$('#box-' + commId)
          if (box.length) cy.fit(box, 50)
        },
        // sélection (clic graphe/tableau/recherche) → halo + recentrage, tout reste visible.
        focus: (chId: number) => {
          cy.$('node.glow').removeClass('glow')
          const n = cy.$('#ch-' + cssEsc(String(chId)))
          if (!n.length) return
          cy.$('node:selected').unselect()
          n.addClass('glow').select()
          // Sélection : halo seul, PAS de recentrage caméra (zoom auto désactivé §4).
        },
        clearEgo: () => {
          cy.elements().removeClass('glow faded story-dim story-member')
          cy.$('node:selected').unselect()
          applyFilters()
        },
        recenter: () => cy.fit(cy.elements(), 60),
        applyFilters,
        // histoire/épisode : halo doré sur les membres présents, estompage du reste.
        applyStory: (ids: number[] | null) => {
          cy.elements().removeClass('story-dim story-member')
          if (!ids || !ids.length) {
            applyFilters()
            return
          }
          const idSet = new Set(ids)
          let members = cy.collection()
          idSet.forEach((id) => {
            members = members.union(cy.$('#ch-' + cssEsc(String(id))))
          })
          if (!members.length) return
          const keep = members.union(members.parent())
          cy.elements().difference(keep).addClass('story-dim')
          members.addClass('story-member')
          cy.fit(members, 140)
        },
      }

      applyFilters()

      return () => {
        ro.disconnect()
        cy.destroy()
        cyRef.current = null
        apiRef.current = null
      }
    }

    const openedRef: { current: number[] } = { current: [] }

    const haloRing = (id: number) => {
      const r = ix.suspRatio.get(id) || 0
      if (r >= 0.4) return GALAXY.halo.suspectHigh
      if (r >= 0.15) return GALAXY.halo.suspectMid
      return ix.COMM.get(id)?.color || GALAXY.fallbackComm
    }

    // label de communauté -> id (pour relier les canaux ponts aux nébuleuses cibles ;
    // bridges[].connects[].label correspond exactement au label communautaire).
    const commByLabel = new Map<string, number>()
    for (const c of snap.communities || []) commByLabel.set(c.label, c.id)

    /* éléments : nébuleuses + arcs top-30 */
    const els: cytoscape.ElementDefinition[] = []
    for (const c of snap.communities || []) {
      const sz = c.size || c.channels.length
      const cxy = c as Community & XY
      els.push({
        data: {
          id: 'comm-' + c.id,
          kind: 'nebula',
          commId: c.id,
          label: shortLabel(c.label),
          full: c.label,
          color: c.color,
          ring: haloRing(c.id),
          grad: `${lighten(c.color, GALAXY.nebula.lightenAmt)} ${c.color} ${GALAXY.nebula.gradOuter}`,
          diam: 56 + 120 * Math.sqrt(sz / ix.maxSize),
          count: sz,
          susp: c.n_suspects || 0,
          ndom: c.n_domains || 0,
        },
        // Layout PRÉCALCULÉ (offline) : position monde de la communauté → 'preset'.
        position: cxy.x != null && cxy.y != null ? { x: cxy.x, y: cxy.y } : undefined,
      })
    }
    // Arcs inter-communautés : on montrait seulement le top-30 → ~19/36 nébuleuses
    // flottaient sans lien. On prend le top-120 PUIS on garantit que chaque
    // communauté a au moins son arc le plus fort (connectivité, sans rien inventer).
    const allArcs = (snap.meta_graph?.edges || []).slice().sort((a, b) => b.weight - a.weight)
    const mgEdges = allArcs.slice(0, 120)
    const inArcs = new Set<number>()
    mgEdges.forEach((e) => { inArcs.add(e.source); inArcs.add(e.target) })
    for (const e of allArcs.slice(120)) {
      if (!inArcs.has(e.source) || !inArcs.has(e.target)) {
        mgEdges.push(e)
        inArcs.add(e.source); inArcs.add(e.target)
      }
    }
    const maxW = Math.max(1, ...mgEdges.map((e) => e.weight))
    mgEdges.forEach((e, i) => {
      els.push({
        data: {
          id: 'arc-' + i,
          kind: 'arc',
          source: 'comm-' + e.source,
          target: 'comm-' + e.target,
          w: 1.4 + 7 * (e.weight / maxW),
          weight: e.weight,
          sname: shortLabel(ix.COMM.get(e.source)?.label || String(e.source)),
          tname: shortLabel(ix.COMM.get(e.target)?.label || String(e.target)),
        },
      })
    })

    const style: unknown = [
      {
        // NÉBULEUSE : couleur pleine + halo via underlay (props 100% supportées —
        // pas de radial-gradient ni shadow-* qui empêchaient le rendu). C'est le
        // SEUL nœud qui garde un underlay permanent (faible cardinalité ~27).
        selector: 'node[kind="nebula"]',
        style: {
          width: 'data(diam)',
          height: 'data(diam)',
          shape: 'ellipse',
          'background-color': 'data(color)',
          'background-opacity': 0.92,
          'border-color': 'data(ring)',
          'border-width': 3,
          'border-opacity': 0.95,
          'underlay-color': 'data(ring)',
          'underlay-opacity': 0.3,
          'underlay-padding': 16,
          'underlay-shape': 'ellipse',
          label: 'data(label)',
          color: GALAXY.text.label,
          'font-family': 'JetBrains Mono, monospace',
          'font-size': '11px',
          'font-weight': 600,
          'text-valign': 'center',
          'text-halign': 'center',
          'text-wrap': 'wrap',
          'text-max-width': 'data(diam)',
          'text-outline-color': GALAXY.text.outline,
          'text-outline-width': 2.5,
          'min-zoomed-font-size': 6,
          'transition-property': 'border-width underlay-opacity opacity',
          'transition-duration': '250ms',
        },
      },
      {
        // CANAL : underlay permanent NEUTRALISÉ (opacity 0 → aucun dessin de halo
        // par nœud sur des centaines de canaux = coût de repaint constant supprimé) ;
        // transitions retirées (repaints en masse). On CONSERVE `underlay-color` pour
        // que le halo CONDITIONNEL `.glow` (survol) reprenne la couleur du canal —
        // les autres halos (broker/seed/.story-member) fixent leur propre couleur.
        selector: 'node[kind="channel"]',
        style: {
          width: 'data(diam)',
          height: 'data(diam)',
          shape: 'ellipse',
          'background-color': 'data(color)',
          'background-opacity': 0.7,
          'border-color': 'data(color)',
          'border-width': 1.2,
          'border-opacity': 0.95,
          'underlay-color': 'data(color)',
          'underlay-opacity': 0,
          label: '',
        },
      },
      {
        // DOMAINE = hexagone, couleur = catégorie, taille = degré multi-lien.
        // Transitions retirées (couche à forte cardinalité).
        selector: 'node[kind="domain"]',
        style: {
          width: 'data(diam)',
          height: 'data(diam)',
          shape: 'hexagon',
          'background-color': 'data(color)',
          'background-opacity': 0.22,
          'border-color': 'data(color)',
          'border-width': 'data(bw)',
          label: 'data(label)',
          color: 'data(color)',
          'font-family': 'JetBrains Mono, monospace',
          'font-size': '8px',
          'text-valign': 'bottom',
          'text-margin-y': 2,
          'text-wrap': 'ellipsis',
          'text-max-width': '84px',
          'min-zoomed-font-size': 8,
        },
      },
      {
        selector: 'node[?broker]',
        style: {
          'border-color': GALAXY.gold,
          'border-width': 2.6,
          'background-opacity': 0.85,
          'underlay-color': GALAXY.gold,
          'underlay-opacity': 0.35,
          'underlay-padding': 4,
          label: 'data(label)',
          color: GALAXY.gold,
          'font-family': 'JetBrains Mono, monospace',
          'font-size': '9px',
          'font-weight': 700,
          'text-valign': 'bottom',
          'text-margin-y': 4,
          'text-wrap': 'ellipsis',
          'text-max-width': '96px',
          'text-outline-color': GALAXY.text.outline,
          'text-outline-width': 2,
        },
      },
      {
        selector: 'node[?seed]',
        style: {
          'border-color': GALAXY.seed,
          'border-width': 2.6,
          'underlay-color': GALAXY.seed,
          'underlay-opacity': 0.4,
          'underlay-padding': 4,
          label: 'data(label)',
          color: GALAXY.seed,
          'font-size': '10px',
          'font-weight': 700,
          'text-valign': 'bottom',
          'text-margin-y': 5,
          'text-wrap': 'ellipsis',
          'text-max-width': '96px',
          'text-outline-color': GALAXY.text.outline,
          'text-outline-width': 2,
        },
      },
      {
        // Arc-pont : bezier plein + couleur unie (simplifié depuis unbundled-bezier
        // + line-gradient, coûteux). Le highlight (.arc-hot) reste fluide via transition.
        selector: 'edge[kind="arc"]',
        style: {
          width: 'data(w)',
          'curve-style': 'bezier',
          'line-color': GALAXY.arc,
          'line-opacity': 0.45,
          'target-arrow-shape': 'none',
          'transition-property': 'opacity width line-opacity',
          'transition-duration': '220ms',
        },
      },
      {
        selector: 'edge[kind="link"]',
        style: {
          width: 'data(w)',
          'curve-style': 'bezier',
          'line-color': 'data(col)',
          opacity: 0.5,
          'target-arrow-shape': 'none',
        },
      },
      {
        // arête canal -> domaine (citation) — transitions retirées (forte cardinalité)
        selector: 'edge[kind="dlink"]',
        style: {
          width: 1,
          'curve-style': 'bezier',
          'line-color': 'data(col)',
          'line-style': 'dotted',
          opacity: 0.4,
          'target-arrow-shape': 'none',
        },
      },
      {
        // ego-focus : forward canal -> canal (orange, orienté)
        selector: 'edge[kind="cc"][family="forward"]',
        style: {
          width: 'mapData(w, 1, 40, 1.8, 5.5)',
          'line-color': GALAXY.ego.forward,
          opacity: 0.92,
          'target-arrow-color': GALAXY.ego.forward,
          'target-arrow-shape': 'triangle',
          'arrow-scale': 0.9,
          'curve-style': 'bezier',
        },
      },
      {
        // ego-focus : coordination canal <-> canal (vert pointillé)
        selector: 'edge[kind="cc"][family="coord"]',
        style: { width: 2, 'line-color': GALAXY.ego.coord, 'line-style': 'dashed', 'curve-style': 'bezier', opacity: 0.85, 'target-arrow-shape': 'none' },
      },
      {
        // intra-communauté (bloom) : forward réel, discret pour CONNECTER sans saturer
        selector: 'edge[kind="intra"][family="forward"]',
        style: { width: 'mapData(w, 1, 40, 0.6, 3)', 'line-color': GALAXY.ego.intraForward, 'curve-style': 'bezier', 'target-arrow-shape': 'none', opacity: 0.5 },
      },
      {
        // intra-communauté (bloom) : coordination réelle (vert pointillé léger)
        selector: 'edge[kind="intra"][family="coord"]',
        style: { width: 1, 'line-color': GALAXY.ego.intraCoord, 'line-style': 'dotted', 'curve-style': 'bezier', 'target-arrow-shape': 'none', opacity: 0.45 },
      },
      {
        // étiquette visible des canaux de l'ego (pour LIRE les voisins connectés)
        selector: '.ego-label',
        style: {
          label: 'data(label)',
          'font-size': '8.5px',
          'font-family': 'JetBrains Mono, monospace',
          color: GALAXY.text.egoLabel,
          'text-valign': 'bottom',
          'text-margin-y': 3,
          'text-outline-color': GALAXY.text.outline,
          'text-outline-width': 2,
          'z-index': 50,
        },
      },
      { selector: '.dim', style: { opacity: 0.07 } },
      { selector: '.dim-mid', style: { opacity: 0.07 } },
      { selector: '.arc-hidden', style: { display: 'none' } },
      { selector: '.gone', style: { display: 'none' } },
      // Mode HISTOIRE : tout ce qui n'appartient pas à la phase active s'efface
      // presque totalement (l'attention va aux canaux de l'histoire).
      { selector: '.story-dim', style: { opacity: 0.05 } },
      {
        selector: '.story-member',
        style: { 'border-color': GALAXY.gold, 'border-width': 3, 'underlay-color': GALAXY.gold, 'underlay-opacity': 0.45, 'underlay-padding': 6 },
      },
      { selector: '.glow', style: { 'border-width': 5, 'underlay-opacity': 0.55, 'underlay-padding': 10 } },
      { selector: '.arc-hot', style: { 'line-opacity': 0.95, width: 'mapData(weight, 0, 80, 4, 12)' } },
      { selector: '.faded', style: { opacity: 0.22 } },
      { selector: 'node:selected', style: { 'border-color': GALAXY.selected, 'border-width': 5 } },
    ]

    const cy = cytoscape({
      container: host,
      elements: els,
      style: style as cytoscape.StylesheetJson,
      // 'preset' = positions PRÉCALCULÉES (offline) portées sur chaque nébuleuse.
      // Plus AUCUN force-layout au runtime (l'ancien fcose proof/1800 itérations
      // était une charge d'init lourde). Le refit ResizeObserver cadre la scène
      // une fois que le conteneur flex a une taille réelle.
      layout: { name: 'preset' },
      minZoom: 0.05,
      maxZoom: 3.4,
      wheelSensitivity: 0.45,
      pixelRatio: 'auto',
    })
    cyRef.current = cy
    if (import.meta.env.DEV) (window as unknown as { __cy?: Core }).__cy = cy // inspection e2e/debug

    // Fiabilise le rendu dans un conteneur flex + StrictMode (double-montage) :
    // Cytoscape mesure 0 à l'init -> il faut resize()+fit() DÈS que le conteneur
    // a une taille réelle (ResizeObserver), avec garde anti-instance-détruite.
    let fitted = false
    const refit = () => {
      if (cy.destroyed()) return
      cy.resize()
      if (!fitted && host.clientWidth > 1 && host.clientHeight > 1) {
        cy.fit(cy.elements(), 80)
        fitted = true
      }
    }
    const ro = new ResizeObserver(refit)
    ro.observe(host)
    requestAnimationFrame(refit)

    /* ── DOMAINES : (re)synchronise la couche site web selon les canaux visibles ── */
    const DOM_CAP = 60
    const syncDomains = () => {
      const present = new Set<number>()
      cy.nodes('node[kind="channel"]').forEach((n) => {
        present.add(n.data('chId'))
      })
      // agrège les domaines cités par les canaux présents
      const agg = new Map<string, { count: number; citers: number[] }>()
      for (const cid of present) {
        const a = model.adj.get(cid)
        if (!a) continue
        for (const d of a.domains) {
          let e = agg.get(d.domain)
          if (!e) {
            e = { count: 0, citers: [] }
            agg.set(d.domain, e)
          }
          e.count += d.count || 1
          e.citers.push(cid)
        }
      }
      // garde les plus MULTI-LIÉS d'abord (ce sont les ponts), puis les plus cités
      const kept = [...agg.entries()]
        .sort((a, b) => b[1].citers.length - a[1].citers.length || b[1].count - a[1].count)
        .slice(0, DOM_CAP)
      const keepNodeIds = new Set(kept.map(([d]) => 'dom-' + d))
      // retire les domaines/arêtes périmés
      const stale = cy.nodes('node[kind="domain"]').filter((n) => !keepNodeIds.has(n.id()))
      if (stale.length) cy.remove(stale)
      const add: cytoscape.ElementDefinition[] = []
      for (const [domain, info] of kept) {
        const id = 'dom-' + domain
        const cat = domainCategory(domain)
        let sx = 0,
          sy = 0,
          k = 0
        for (const cid of info.citers) {
          const cn = cy.$('#ch-' + cssEsc(String(cid)))
          if (cn.length) {
            const p = cn.position()
            sx += p.x
            sy += p.y
            k++
          }
        }
        if (!cy.$('#' + cssEsc(id)).length) {
          add.push({
            group: 'nodes',
            data: {
              id,
              kind: 'domain',
              domain,
              label: domain.replace(/^www\./, ''),
              cat,
              color: DOM_COLOR[cat],
              diam: 9 + Math.min(16, info.citers.length * 2.2),
              bw: info.citers.length > 1 ? 1.8 : 1,
              degree: info.citers.length,
            },
            position: k ? { x: sx / k, y: sy / k } : undefined,
          })
        }
        for (const cid of info.citers) {
          const lid = 'dl-' + domain + '-' + cid
          if (!cy.$('#' + cssEsc(lid)).length)
            add.push({ group: 'edges', data: { id: lid, kind: 'dlink', source: 'ch-' + cid, target: id, col: DOM_COLOR[cat] } })
        }
      }
      if (add.length) cy.add(add)
    }

    /* filtres */
    const indexedCh = (cid: number) => ix.CH.get(cid)
    const channelMatches = (cid: number, arch: string) => {
      const f = filtersRef.current
      const ch = indexedCh(cid)
      if (!ch) return true
      if (f.cred.size) {
        const cv = ch.credibility_prior === 'suspect' ? 'suspect' : ch.credibility_prior === 'other' ? 'other' : 'legit'
        if (!f.cred.has(cv)) return false
      }
      if (f.arch.size && !f.arch.has(arch)) return false
      if (f.comm.size && !f.comm.has(ch.commId)) return false
      return true
    }
    const applyBloomDim = () => {
      const op = new Set(openedRef.current)
      // Opacité INLINE (bat la transition/animation qui écrasait la classe).
      cy.nodes('[kind="nebula"]').forEach((n) => { n.stop().removeStyle('opacity') })
      cy.edges('[kind="arc"]').removeClass('arc-hidden')
      if (op.size === 0) {
        // tout replié : vue d'ensemble (arcs visibles) + recadrage global
        cy.animate({ fit: { eles: cy.elements('[kind="nebula"], [kind="arc"]'), padding: 80 }, duration: 600, easing: 'ease-in-out-cubic' })
        return
      }
      // une sphère est éclatée : on EFFACE les autres nébuleuses et les arcs méta
      // (vue d'ensemble) pour ne voir QUE les canaux de la sphère ouverte.
      cy.nodes('[kind="nebula"]').forEach((n) => {
        if (!op.has(n.data('commId'))) n.style('opacity', 0.06)
      })
      cy.edges('[kind="arc"]').addClass('arc-hidden')
    }
    const applyFilters = () => {
      const f = filtersRef.current
      const anyComm = f.comm.size > 0
      cy.nodes('[kind="nebula"]').forEach((n) => {
        n.removeClass('dim')
        if (anyComm && !f.comm.has(n.data('commId'))) n.addClass('dim')
      })
      cy.nodes('[kind="channel"]').forEach((n) => {
        n.removeClass('dim gone')
        if (!f.channels) n.addClass('gone')
        else if (!channelMatches(n.data('chId'), n.data('arch'))) n.addClass('dim')
      })
      cy.nodes('[kind="domain"]').forEach((n) => {
        n.removeClass('dim gone')
        if (!f.domains) n.addClass('gone')
        else if (f.domCat.size && !f.domCat.has(n.data('cat'))) n.addClass('dim')
      })
      cy.edges('[kind="dlink"]').forEach((e) => {
        e.removeClass('dim')
        const dn = e.target()
        if (dn.hasClass('dim') || dn.hasClass('gone')) e.addClass('dim')
      })
      applyBloomDim()
    }

    /* bloom */
    const expandBloom = (commId: number, animateFit = true) => {
      const c = ix.COMM.get(commId)
      if (!c || openedRef.current.includes(commId)) return
      openedRef.current = [...openedRef.current, commId]
      const nebula = cy.$('#comm-' + commId)
      const origin = nebula.position()
      const maxEng = Math.max(1, ...c.channels.map((ch) => ch.engagement || 0))
      const add: cytoscape.ElementDefinition[] = []
      c.channels.forEach((ch) => {
        const id = 'ch-' + ch.channel_id
        if (cy.$('#' + cssEsc(id)).length) return
        const b = ix.BR.get(ch.channel_id)
        const bet = b ? b.betweenness : ch.betweenness || 0
        const broker = bet > 0.04
        // Position PRÉCALCULÉE (offline) : coord monde ABSOLUE du canal, même repère
        // que la nébuleuse. Repli sur le centroïde de la nébuleuse si jamais absente.
        const chxy = ch as SphereChannel & XY
        add.push({
          group: 'nodes',
          data: {
            id,
            kind: 'channel',
            chId: ch.channel_id,
            commId,
            label: '@' + (ch.username || '#' + ch.channel_id),
            color: c.color,
            diam: broker ? 22 + 34 * (bet / ix.maxBet) : 12 + 16 * Math.sqrt((ch.engagement || 0) / maxEng),
            broker,
            seed: !!ch.is_seed,
            arch: chArchetype(ix, ch),
          },
          position: { x: chxy.x ?? origin.x, y: chxy.y ?? origin.y },
        })
      })
      // Liens inter-communautés : un canal PONT (présent dans bridges[]) trace des
      // arêtes dorées vers les AUTRES nébuleuses qu'il relie -> rôle de pont visible.
      c.channels.forEach((ch) => {
        const b = ix.BR.get(ch.channel_id)
        if (!b || !(b.connects || []).length) return
        b.connects.forEach((cn, ci) => {
          const tgtId = commByLabel.get(cn.label)
          if (tgtId == null || tgtId === commId) return
          add.push({
            group: 'edges',
            data: { id: `lnk-${ch.channel_id}-${tgtId}-${ci}`, kind: 'link', source: 'ch-' + ch.channel_id, target: 'comm-' + tgtId, w: 1 + Math.min(4, cn.edges || 1), col: GALAXY.ego.link },
          })
        })
      })
      // Liens INTRA-communauté : forwards + coordinations RÉELS (graph.json, via
      // model.adj) entre les canaux éclos — pour qu'ils soient CONNECTÉS et non
      // posés en cercle isolé. Bornés (perf) ; on ne crée aucun lien inventé.
      const commSet = new Set(c.channels.map((x) => x.channel_id))
      const seenIntra = new Set<string>()
      let intra = 0
      for (const ch of c.channels) {
        if (intra >= 500) break
        const a = model.adj.get(ch.channel_id)
        if (!a) continue
        for (const x of a.fwdTo) {
          if (intra >= 500) break
          if (!commSet.has(x.cid) || x.cid === ch.channel_id) continue
          const id = `intra-f-${ch.channel_id}-${x.cid}`
          if (seenIntra.has(id)) continue
          seenIntra.add(id)
          add.push({ group: 'edges', data: { id, kind: 'intra', family: 'forward', commId, source: 'ch-' + ch.channel_id, target: 'ch-' + x.cid, w: x.count || 1 } })
          intra++
        }
        for (const x of a.coord) {
          if (intra >= 500) break
          if (!commSet.has(x.cid) || x.cid === ch.channel_id) continue
          const lo = Math.min(ch.channel_id, x.cid), hi = Math.max(ch.channel_id, x.cid)
          const id = `intra-c-${lo}-${hi}`
          if (seenIntra.has(id)) continue
          seenIntra.add(id)
          add.push({ group: 'edges', data: { id, kind: 'intra', family: 'coord', commId, source: 'ch-' + ch.channel_id, target: 'ch-' + x.cid, w: x.count || 1 } })
          intra++
        }
      }
      cy.add(add)
      // Positions PRÉCALCULÉES → AUCUN force-layout au bloom (l'ancien fcose local
      // était la 2ᵉ charge CPU d'interaction). Fondu d'opacité léger : on pose
      // l'inline opacity à 0 puis on anime vers 1, et on RETIRE l'inline en fin
      // d'anim pour rendre la main aux classes (.dim/.faded/.story-dim gèrent
      // ensuite l'opacité via CSS — sinon l'inline écraserait les filtres).
      const bloomed = cy.$(`node[commId=${commId}][kind="channel"]`)
      bloomed.style('opacity', 0)
      bloomed.animate({ style: { opacity: 1 } }, { duration: 400, complete: () => bloomed.removeStyle('opacity') })
      syncDomains()
      applyFilters()
      // Cadrer sur les canaux de la sphère (+ ses domaines) pour qu'ils
      // remplissent l'écran — les autres nébuleuses, effacées, sortent du cadre.
      let focus = bloomed.union(nebula)
      focus = focus.union(cy.edges(`[kind="intra"][commId=${commId}]`))
      // animateFit=false lors d'un bloom EN MASSE (applyStory sur N communautés) :
      // sinon N animations caméra s'enchaînent = strobe. Un fit final unique cadre la vue.
      if (animateFit && focus.length > 1) cy.animate({ fit: { eles: focus, padding: 70 }, duration: 600, easing: 'ease-in-out-cubic' })
      nebula.animate({ style: { 'background-opacity': 0.06, 'border-opacity': 0.4 } }, { duration: 400 })
      applyBloomDim()
      setOpened([...openedRef.current])
    }
    const collapseBloom = (commId: number) => {
      openedRef.current = openedRef.current.filter((x) => x !== commId)
      const kids = cy.$(`node[commId=${commId}][kind="channel"]`)
      const nebula = cy.$('#comm-' + commId)
      const origin = nebula.position()
      kids.forEach((n) => {
        n.animate({ position: { x: origin.x, y: origin.y }, style: { opacity: 0, width: 2, height: 2 } }, { duration: 380, easing: 'ease-in-cubic' })
      })
      window.setTimeout(() => {
        cy.remove(kids)
        syncDomains()
        applyFilters()
      }, 420)
      nebula.animate({ style: { 'background-opacity': 0.9, 'border-opacity': 0.9 } }, { duration: 400 })
      applyBloomDim()
      setOpened([...openedRef.current])
    }
    const toggleBloom = (commId: number) => (openedRef.current.includes(commId) ? collapseBloom(commId) : expandBloom(commId))

    /* surbrillance */
    const egoCleanup = () => {
      cy.remove(cy.elements('[?ephemeral]')) // retire les voisins injectés
      cy.remove(cy.edges('[kind="cc"]')) // retire les arêtes canal-canal
    }
    const clearHi = () => {
      egoCleanup()
      cy.elements().removeClass('arc-hot pick faded glow ego-label')
      cy.nodes('[kind="channel"]').removeStyle('opacity') // efface les bypass d'estompage
      cy.$('node:selected').unselect()
      applyBloomDim()
      applyFilters()
    }
    const highlightArc = (edge: EdgeSingular) => {
      clearHi()
      const a = edge.source(),
        b = edge.target()
      edge.addClass('arc-hot')
      a.addClass('glow')
      b.addClass('glow')
      const keep = a.union(b).union(edge)
      cy.elements('[kind="nebula"], [kind="arc"]').difference(keep).addClass('faded')
    }
    const illuminateDomain = (n: NodeSingular) => {
      clearHi()
      const nb = n.connectedEdges().connectedNodes()
      n.addClass('glow')
      nb.addClass('glow')
      cy.elements().difference(n.union(nb).union(n.connectedEdges())).addClass('faded')
    }

    /* ── EGO-FOCUS : clic canal -> voir ses AUTRES CANAUX connectés (forward +
       coordination), injectés en éphémère s'ils ne sont pas déjà éclos, + ses
       domaines ; le reste est estompé. ── */
    const ego = (chId: number) => {
      clearHi() // nettoie l'ego précédent + le surlignage
      const centerSel = '#ch-' + cssEsc(String(chId))
      let center = cy.$(centerSel)
      if (!center.length) {
        const meta = ix.CH.get(chId)
        const ext = cy.extent()
        cy.add({
          group: 'nodes',
          data: { id: 'ch-' + chId, kind: 'channel', chId, label: '@' + (meta?.username || '#' + chId), color: meta?.commColor || GALAXY.fallbackNode, diam: 18, ephemeral: true },
          position: { x: (ext.x1 + ext.x2) / 2, y: (ext.y1 + ext.y2) / 2 },
        })
        center = cy.$(centerSel)
      }
      const a = model.adj.get(chId)
      const raw: { cid: number; fam: 'forward' | 'coord'; dir: 'in' | 'out' | 'un'; w: number }[] = []
      if (a) {
        a.fwdFrom.forEach((x) => raw.push({ cid: x.cid, fam: 'forward', dir: 'in', w: x.count || 1 }))
        a.fwdTo.forEach((x) => raw.push({ cid: x.cid, fam: 'forward', dir: 'out', w: x.count || 1 }))
        a.coord.forEach((x) => raw.push({ cid: x.cid, fam: 'coord', dir: 'un', w: x.count || 1 }))
      }
      const seen = new Set<string>()
      const list = raw.filter((n) => {
        if (n.cid === chId) return false
        const k = n.cid + n.fam + n.dir
        if (seen.has(k)) return false
        seen.add(k)
        return true
      }).slice(0, 28)
      const cpos = center.position()
      const add: cytoscape.ElementDefinition[] = []
      const egoIds = new Set<string>(['ch-' + chId])
      list.forEach((nb, i) => {
        const nid = 'ch-' + nb.cid
        egoIds.add(nid)
        if (!cy.$('#' + cssEsc(nid)).length) {
          const meta = ix.CH.get(nb.cid)
          const ang = (i / list.length) * Math.PI * 2
          const rad = 110 + (i % 3) * 34
          add.push({
            group: 'nodes',
            data: { id: nid, kind: 'channel', chId: nb.cid, label: '@' + (meta?.username || '#' + nb.cid), color: meta?.commColor || GALAXY.fallbackNode, diam: 13, ephemeral: true },
            position: { x: cpos.x + Math.cos(ang) * rad, y: cpos.y + Math.sin(ang) * rad },
          })
        }
        const src = nb.dir === 'in' ? nb.cid : chId
        const tgt = nb.dir === 'in' ? chId : nb.cid
        add.push({ group: 'edges', data: { id: `cc-${chId}-${nb.cid}-${nb.fam}-${nb.dir}`, kind: 'cc', family: nb.fam, source: 'ch-' + src, target: 'ch-' + tgt, w: nb.w } })
      })
      if (add.length) cy.add(add)
      let egoNodes = cy.collection()
      egoIds.forEach((id) => {
        egoNodes = egoNodes.union(cy.$('#' + cssEsc(id)))
      })
      const dlinks = center.connectedEdges('[kind="dlink"]')
      const egoDomains = dlinks.connectedNodes('[kind="domain"]')
      const ccEdges = cy.edges('[kind="cc"]')
      const keep = egoNodes.union(egoDomains).union(ccEdges).union(dlinks)
      const rest = cy.elements('node, edge').difference(keep)
      rest.addClass('faded')
      // les canaux éclos portent une opacité inline (bypass de bloom) qui
      // écraserait .faded : on stoppe et on pose le bypass d'estompage.
      // 0.22 (pas 0.05) : on ATTÉNUE le contexte sans le faire disparaître —
      // zoomer sur un nœud doit garder la galaxie lisible autour.
      const restCh = rest.nodes('[kind="channel"]')
      restCh.stop()
      restCh.style('opacity', 0.22)
      egoNodes.removeStyle('opacity')
      egoNodes.addClass('ego-label')
      center.addClass('glow').select()
      // Ego-focus : halo + estompage du contexte, SANS animation caméra — cliquer un
      // canal ne recentre/zoome plus (désactivation des zooms auto par nœud, §4).
    }
    const focus = (chId: number) => {
      const ch = ix.CH.get(chId)
      if (cy.$('#ch-' + cssEsc(String(chId))).length) {
        ego(chId)
        return
      }
      if (ch && !openedRef.current.includes(ch.commId)) expandBloom(ch.commId)
      const tryF = () => {
        if (cy.$('#ch-' + cssEsc(String(chId))).length) ego(chId)
        else window.setTimeout(tryF, 120)
      }
      tryF()
    }

    /* ── HISTOIRES : la phase active filtre la galaxie sur ses canaux ──
       Auto-bloom des sphères concernées, estompage quasi-total du reste
       (.story-dim, opacité 0.05), étiquettes + halo doré sur les membres,
       cadrage sur l'ensemble. ids null/vide => galaxie libre. */
    const applyStory = (ids: number[] | null) => {
      cy.elements().removeClass('gone story-dim story-member')
      cy.nodes('[kind="channel"]').removeStyle('opacity') // efface les bypass du mode histoire
      if (!ids || ids.length === 0) {
        applyFilters()
        return
      }
      const idSet = new Set(ids)
      const comms = new Set<number>()
      idSet.forEach((id) => {
        const ch = ix.CH.get(id)
        if (ch) comms.add(ch.commId)
      })
      comms.forEach((cid) => {
        if (!openedRef.current.includes(cid)) expandBloom(cid, false) // pas de fit par communauté → anti-strobe
      })
      // Un thème peut éclater BEAUCOUP de communautés (canaux dispersés) : les
      // blooms finissent à des instants variables. Au lieu d'un timeout fixe, on
      // RÉ-ESSAIE jusqu'à ce que (presque) tous les membres existent comme nœuds.
      const expected = [...idSet].filter((id) => ix.CH.has(id)).length
      let tries = 0
      const tryHighlight = () => {
        if (cy.destroyed()) return
        let members = cy.collection()
        idSet.forEach((id) => {
          members = members.union(cy.$('#ch-' + cssEsc(String(id))))
        })
        // attendre encore si trop peu de membres sont apparus (blooms en cours)
        if (members.length < Math.max(1, Math.floor(expected * 0.9)) && tries < 12) {
          tries += 1
          window.setTimeout(tryHighlight, 180)
          return
        }
        if (!members.length) return // rien à illuminer (p. ex. phase sans données)
        cy.elements().removeClass('gone story-dim story-member')
        const nebulas = cy.nodes('[kind="nebula"]').filter((n) => comms.has(n.data('commId')))
        // FILTRE DUR : on garde les membres + leurs nébuleuses + les arêtes INTERNES
        // au set gardé ; tout le reste passe en .gone (display:none) → « on ne voit
        // QUE le scénario ». Les membres restent toujours visibles.
        const keptNodes = members.union(nebulas)
        const keepEdges = keptNodes.connectedEdges().filter((e) => keptNodes.contains(e.source()) && keptNodes.contains(e.target()))
        const keep = keptNodes.union(keepEdges)
        const rest = cy.elements().difference(keep)
        rest.stop()
        rest.addClass('gone')
        members.removeClass('gone dim')
        members.addClass('story-member ego-label')
        cy.animate({ fit: { eles: members, padding: 140 } }, { duration: 600, easing: 'ease-in-out-cubic' })
      }
      window.setTimeout(tryHighlight, 200)
    }

    /* tooltip */
    const tip = tipRef.current!
    const moveTip = (pos: { x: number; y: number }) => {
      if (tip.style.display !== 'block' || !pos) return
      const w = host.clientWidth,
        h = host.clientHeight
      tip.style.left = Math.min(pos.x + 16, w - tip.offsetWidth - 14) + 'px'
      tip.style.top = Math.min(pos.y + 14, h - tip.offsetHeight - 14) + 'px'
    }
    const showTip = (html: string, pos: { x: number; y: number }) => {
      tip.innerHTML = html
      tip.style.display = 'block'
      moveTip(pos)
    }
    const hideTip = () => (tip.style.display = 'none')
    const tipNode = (n: NodeSingular) => {
      const kind = n.data('kind')
      if (kind === 'nebula')
        return `<div style="color:${n.data('color')};font-weight:700">${n.data('full')}</div><div style="opacity:.8">${tRef.current('graph.tooltip.commStats', { count: n.data('count'), susp: n.data('susp'), ndom: n.data('ndom') })}</div><div style="color:${GALAXY.gold};margin-top:3px">${tRef.current('graph.tooltip.clicBloom')}</div>`
      if (kind === 'domain') {
        const lbl = tRef.current('graph.filter.dom.' + (n.data('cat') || 'other'))
        return `<div style="color:${n.data('color')};font-weight:700">${n.data('label')}</div><div style="opacity:.8">${tRef.current('graph.tooltip.domain', { cat: lbl })}</div><div style="opacity:.8">${tRef.current('graph.tooltip.citedBy', { n: n.data('degree') })}</div><div style="color:${GALAXY.text.telegram};margin-top:3px">${tRef.current('graph.tooltip.clicCiters')}</div>`
      }
      const ch = ix.CH.get(n.data('chId'))
      const arch = ARCH[n.data('arch')]?.label || n.data('arch')
      return `<div style="color:${n.data('color')};font-weight:700">${n.data('label')}</div>${ch?.title ? `<div style="opacity:.8">${ch.title}</div>` : ''}<div style="opacity:.8">${tRef.current('graph.tooltip.credibility', { cred: ch?.credibility_prior || '—', arch })}</div>${n.data('broker') ? `<div style="color:${GALAXY.gold}">${tRef.current('graph.tooltip.broker')}</div>` : ''}<div style="color:${GALAXY.text.telegram};margin-top:3px">${tRef.current('graph.tooltip.clicDossier')}</div>`
    }

    cy.on('mouseover', 'node', (e) => {
      e.target.addClass('glow')
      showTip(tipNode(e.target), e.renderedPosition)
      host.style.cursor = 'pointer'
    })
    cy.on('mouseout', 'node', (e) => {
      e.target.removeClass('glow')
      hideTip()
      host.style.cursor = ''
    })
    cy.on('mouseover', 'edge[kind="arc"]', (e) =>
      showTip(
        `<div style="color:${GALAXY.gold};font-weight:700">${tRef.current('graph.tooltip.arcTitle')}</div><div style="opacity:.8">${e.target.data('sname')} ↔ ${e.target.data('tname')}</div><div style="opacity:.8">${tRef.current('graph.tooltip.arcEdges', { n: e.target.data('weight') })}</div>`,
        e.renderedPosition,
      ),
    )
    cy.on('mouseout', 'edge', hideTip)
    cy.on('mousemove', (e) => moveTip(e.renderedPosition))
    cy.on('tap', 'node[kind="nebula"]', (e) => toggleBloom(e.target.data('commId')))
    cy.on('tap', 'node[kind="channel"]', (e) => select(e.target.data('chId')))
    cy.on('tap', 'node[kind="domain"]', (e) => illuminateDomain(e.target))
    cy.on('tap', 'edge[kind="arc"]', (e) => highlightArc(e.target))
    cy.on('tap', (e) => {
      if (e.target === cy) select(null)
    })

    apiRef.current = {
      bloom: toggleBloom,
      focus,
      clearEgo: clearHi,
      recenter: () => cy.animate({ fit: { eles: cy.elements(), padding: 90 } }, { duration: 650, easing: 'ease-in-out-cubic' }),
      applyFilters,
      applyStory,
    }

    return () => {
      ro.disconnect()
      cy.destroy()
      cyRef.current = null
      apiRef.current = null
    }
  }, [ix, snap, model, select, viewMode])

  /* ré-applique les filtres quand l'UI change */
  useEffect(() => {
    apiRef.current?.applyFilters()
  }, [filters])

  /* la sélection (clic graphe, tableau, recherche) pilote l'ego-focus */
  useEffect(() => {
    const cy = cyRef.current
    if (!cy) return
    if (selected == null) {
      apiRef.current?.clearEgo()
      return
    }
    apiRef.current?.focus(selected)
  }, [selected, ix])

  /* l'ensemble à illuminer (histoire OU épisode) pilote le filtre */
  useEffect(() => {
    apiRef.current?.applyStory(highlightIds && highlightIds.length ? highlightIds : null)
  }, [highlightIds, ix])

  /* raccourcis clavier : Échap = désélection + vide la recherche, f = recentrer.
     Ignorés quand une saisie a le focus (pour ne pas voler les frappes). */
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      const t = e.target as HTMLElement | null
      if (t && (t.tagName === 'INPUT' || t.tagName === 'TEXTAREA' || t.isContentEditable)) return
      if (e.key === 'Escape') {
        setQ('')
        select(null)
      } else if (e.key === 'f' || e.key === 'F') {
        apiRef.current?.recenter()
      }
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [select])

  if (loading) return <Spinner />
  if (!snap || !ix || !(snap.communities || []).length)
    return (
      <EmptyState
        title={t('graph.emptyTitle')}
        hint={t('graph.emptyHint', { missionId })}
      />
    )

  const toggle = (fam: 'cred' | 'arch' | 'comm' | 'domCat', val: string | number) =>
    setFilters((f) => {
      const next: Filters = { ...f, cred: new Set(f.cred), arch: new Set(f.arch), comm: new Set(f.comm), domCat: new Set(f.domCat) }
      const set = next[fam] as Set<string | number>
      set.has(val) ? set.delete(val) : set.add(val)
      return next
    })
  const toggleType = (k: 'channels' | 'domains') => setFilters((f) => ({ ...f, [k]: !f[k] }))
  const reset = () => setFilters(emptyFilters())
  const nFilters =
    filters.cred.size + filters.arch.size + filters.comm.size + filters.domCat.size + (filters.channels ? 0 : 1) + (filters.domains ? 0 : 1)

  const comms = (snap.communities || []).slice().sort((a, b) => (b.size || 0) - (a.size || 0))
  const chip = (on: boolean) =>
    `cursor-pointer select-none rounded-full px-2.5 py-1 text-xs ring-1 ring-inset transition ${
      on ? 'ring-white/40 text-white' : 'ring-white/10 text-slate-400 hover:ring-white/25'
    }`

  const sectionTitle = 'flex items-center justify-between px-1 text-[10px] font-semibold uppercase tracking-wide text-slate-500'

  return (
    <div className="flex h-full w-full">
      {/* ════════ COCKPIT (gauche) — TOUS les contrôles, un seul endroit ════════ */}
      <aside className="flex w-72 shrink-0 flex-col gap-3 overflow-y-auto border-r border-white/10 bg-[#070e1f] p-3">
        {/* Sections injectées par Overview : Thèmes · Histoires · Épisodes */}
        {cockpitTop}

        {/* Mode de vue : Galaxie (défaut) vs Compound (boîtes-communautés) */}
        <div>
          <div className={sectionTitle + ' mb-1'}>{t('graph.view.label')}</div>
          <div className="flex gap-1 rounded-lg bg-[#0a162e] p-0.5 ring-1 ring-inset ring-white/10">
            {(['galaxy', 'compound'] as const).map((m) => (
              <button
                key={m}
                type="button"
                onClick={() => setViewMode(m)}
                aria-pressed={viewMode === m}
                className={`flex-1 rounded-md px-2 py-1 text-xs transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-400 ${
                  viewMode === m ? 'bg-white/10 text-white ring-1 ring-inset ring-white/20' : 'text-slate-400 hover:text-slate-200'
                }`}
              >
                {m === 'galaxy' ? t('graph.view.galaxy') : t('graph.view.compound')}
              </button>
            ))}
          </div>
        </div>

        {/* Recherche */}
        <div>
          <div className={sectionTitle + ' mb-1'}>{t('graph.search.label')}</div>
          <div className="relative">
            <input
              value={q}
              onChange={(e) => setQ(e.target.value)}
              placeholder={t('graph.search.placeholder')}
              className="w-full rounded-lg border border-white/10 bg-[#0a162e] px-3 py-1.5 text-xs text-slate-100 placeholder:text-slate-500 focus:border-amber-400/50 focus:outline-none"
            />
            {hits.length > 0 && (
              <div className="absolute left-0 right-0 z-30 mt-1 max-h-72 overflow-auto rounded-lg border border-white/10 bg-[#0a162e] p-1 shadow-2xl">
                {hits.map((h) => (
                  <button
                    key={h.id}
                    onClick={() => { select(h.id); setQ('') }}
                    className="flex w-full items-center gap-2 rounded px-2 py-1.5 text-left text-xs text-slate-200 hover:bg-white/5"
                  >
                    <span className="h-2 w-2 shrink-0 rounded-full" style={{ background: h.color }} />
                    <span className="font-mono text-[#229ED9]">{h.label}</span>
                    <span className="ml-auto truncate text-slate-500">{h.comm}</span>
                  </button>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Filtres */}
        <details open className="text-xs text-slate-200">
          <summary className={sectionTitle + ' cursor-pointer list-none py-1'}>
            <span>{t('graph.filter.heading')}{nFilters ? ` · ${nFilters}` : ''}</span>
            {nFilters > 0 && (
              <button type="button" onClick={(e) => { e.preventDefault(); reset() }} className="text-amber-300 hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-amber-400">{t('graph.filter.reset')}</button>
            )}
          </summary>
          <div className="mt-1 space-y-2">
            <div>
              <div className="mb-1 text-[10px] text-slate-500">{t('graph.filter.nodeType')}</div>
              <div className="flex flex-wrap gap-1.5">
                <button type="button" aria-pressed={filters.channels} onClick={() => toggleType('channels')} className={`${chip(filters.channels)} focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-400`}>{t('graph.filter.channels')}</button>
                <button type="button" aria-pressed={filters.domains} onClick={() => toggleType('domains')} className={`${chip(filters.domains)} focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-400`}>{t('graph.filter.domains')}</button>
              </div>
            </div>
            <div>
              <div className="mb-1 text-[10px] text-slate-500">{t('graph.filter.credibility')}</div>
              <div className="flex flex-wrap gap-1.5">
                {CRED_VALS.map(([v, col]) => (
                  <button type="button" key={v} aria-pressed={filters.cred.has(v)} onClick={() => toggle('cred', v)} className={`${chip(filters.cred.has(v))} focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-400`}>
                    <span className="mr-1 inline-block h-1.5 w-1.5 rounded-full align-middle" style={{ background: col }} />
                    {t('graph.cred.' + v)}
                  </button>
                ))}
              </div>
            </div>
            <div>
              <div className="mb-1 text-[10px] text-slate-500">{t('graph.filter.archetype')}</div>
              <div className="flex flex-wrap gap-1.5">
                {Object.keys(ARCH).map((k) => (
                  <button type="button" key={k} aria-pressed={filters.arch.has(k)} onClick={() => toggle('arch', k)} className={`${chip(filters.arch.has(k))} focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-400`}>{t('graph.arch.label.' + k)}</button>
                ))}
              </div>
            </div>
            <div>
              <div className="mb-1 text-[10px] text-slate-500">{t('graph.filter.domCategory')}</div>
              <div className="flex flex-wrap gap-1.5">
                {DOM_CATS.map((c) => (
                  <button type="button" key={c.key} aria-pressed={filters.domCat.has(c.key)} onClick={() => toggle('domCat', c.key)} className={`${chip(filters.domCat.has(c.key))} focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-400`}>
                    <span className="mr-1 inline-block h-1.5 w-1.5 rounded-full align-middle" style={{ background: c.color }} />
                    {t('graph.filter.dom.' + c.key)}
                  </button>
                ))}
              </div>
            </div>
          </div>
        </details>

        {/* Sphères (clic = éclore/replier) */}
        <details open className="text-xs">
          <summary className={sectionTitle + ' cursor-pointer list-none py-1'}>
            <span>{t('graph.spheres.heading')} · {comms.length}</span>
            {opened.length > 0 && <span className="text-amber-300">{t('graph.spheres.open', { n: opened.length })}</span>}
          </summary>
          <div className="mt-1 max-h-72 overflow-auto">
            {comms.map((c) => {
              const open = opened.includes(c.id)
              return (
                <button
                  key={c.id}
                  onClick={() => apiRef.current?.bloom(c.id)}
                  onMouseEnter={() => cyRef.current?.$('#comm-' + c.id + ', #box-' + c.id).addClass('glow')}
                  onMouseLeave={() => cyRef.current?.$('#comm-' + c.id + ', #box-' + c.id).removeClass('glow')}
                  className={`flex w-full items-center gap-2 rounded px-2 py-1 text-left text-xs hover:bg-white/5 ${open ? 'text-white' : 'text-slate-300'}`}
                >
                  <span className="h-2.5 w-2.5 shrink-0 rounded-full" style={{ background: c.color, boxShadow: open ? `0 0 6px ${c.color}` : 'none' }} />
                  <span className="flex-1 truncate" title={c.label}>{shortLabel(c.label)}</span>
                  <span className="font-mono text-slate-500">{c.size}</span>
                  {c.n_suspects ? <span className="text-rose-400">{c.n_suspects}⚑</span> : null}
                </button>
              )
            })}
          </div>
        </details>
      </aside>

      {/* ════════ CANVAS (droite) ════════ */}
      <div ref={boxRef} className="relative h-full flex-1 overflow-hidden" style={{ background: 'radial-gradient(ellipse at 50% 42%, #0a1530 0%, #050c1c 55%, #02050f 100%)' }}>
        <canvas ref={starRef} className="pointer-events-none absolute inset-0 z-0" />
        <div ref={cyHostRef} className="relative z-10 h-full w-full" />
        <button
          onClick={() => apiRef.current?.recenter()}
          className="absolute right-3 top-3 z-20 rounded-full border border-white/10 bg-[#0a162e]/80 px-3 py-1.5 text-xs text-slate-300 backdrop-blur hover:border-white/25"
          title={t('graph.recenterTitle')}
        >
          {t('graph.recenter')}
        </button>
        <div
          ref={tipRef}
          className="pointer-events-none absolute z-30 hidden max-w-xs overflow-hidden break-words rounded-lg border border-amber-500/30 bg-[#06122699] px-3 py-2 text-[11px] leading-snug text-slate-100 backdrop-blur"
          style={{ display: 'none' }}
        />
      </div>
    </div>
  )
}
