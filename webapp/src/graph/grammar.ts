// Grammaire visuelle du graphe — PORTÉE de frontend/js/situation.js (verbatim
// pour les couleurs/mappings) : taille=suspicion, bordure=crédibilité,
// halo=france_targeting, forme=gate, 3 familles d'arêtes. Couleurs passées en
// data() (mappers purs) pour rester typé sans styles-fonction.
import type cytoscape from 'cytoscape'
import i18n from '@/state/i18n'

export const ARCH_COLORS: Record<string, string> = {
  'seeding-source': '#DC2626',
  'forward-hub': '#EA580C',
  'cross-channel-bridge': '#C9880A',
  reactivator: '#64748B',
}
export const CRED_COLORS: Record<string, string> = {
  legit: '#22c55e',
  suspect: '#DC2626',
  other: '#64748B',
}
export const SIDE_COLORS: Record<string, string> = { RU: '#f87171', FR: '#60A5FA' }
export const FR_SIDE_MIN = 0.15

// Libellés FR déplacés vers les dictionnaires i18n (graph.arch.* / graph.score.*).
// Ces helpers lisent le SINGLETON i18n (module non-React, pas de hook) : ils sont
// appelés PAR RENDU depuis ChannelDrawer (qui souscrit à useTranslation et se
// re-rend donc à chaque changement de langue) → la langue courante est prise en
// compte. `i18n.exists` reproduit la sémantique « clé absente → chaîne vide » des
// anciens objets (Record) pour que les tests `&&` des consommateurs restent vrais.
export function archInterp(archetype: string | null | undefined): string {
  const key = 'graph.arch.' + String(archetype ?? '')
  return archetype && i18n.exists(key) ? i18n.t(key) : ''
}
export function scoreHelp(fam: string | null | undefined): string {
  const key = 'graph.score.' + String(fam ?? '')
  return fam && i18n.exists(key) ? i18n.t(key) : ''
}

export function tgUrl(u: string | null | undefined): string | null {
  const h = String(u || '').replace(/^@/, '')
  return /^[A-Za-z0-9_]{4,}$/.test(h) ? 'https://t.me/' + h : null
}

export const at = (u: string | null | undefined) => '@' + String(u || '').replace(/^@/, '')
export const fmt = (v: unknown) => (typeof v === 'number' ? v.toFixed(2) : '—')

export function fmtDur(s: number | null | undefined): string {
  if (s == null) return '—'
  if (s < 60) return s + 's'
  if (s < 3600) return Math.round(s / 60) + 'min'
  if (s < 86400) return (s / 3600).toFixed(1) + 'h'
  return (s / 86400).toFixed(1) + 'j'
}

export const GRAPH_STYLE: cytoscape.StylesheetJson = [
  {
    // Zone thématique (nœud compound parent) : tintée par la couleur de la sphère,
    // nommée. Les canaux d'une même communauté sont clusterisés à l'intérieur.
    selector: 'node[kind="community"]',
    style: {
      // Zone thématique DOUCE (pas de boîte dure) : halo translucide arrondi +
      // nom de la sphère. Les nœuds, colorés par thème, forment le cluster.
      shape: 'round-rectangle',
      'background-color': 'data(ccolor)',
      'background-opacity': 0.05,
      'background-blacken': -0.1,
      'border-width': 0,
      label: 'data(label)',
      'font-size': '12px',
      'font-weight': 700,
      'font-family': 'Plus Jakarta Sans, sans-serif',
      color: 'data(ccolor)',
      'text-valign': 'top',
      'text-halign': 'center',
      'text-margin-y': 4,
      'text-max-width': '180px',
      'text-wrap': 'ellipsis',
      'text-opacity': 0.85,
      'min-zoomed-font-size': 6,
      padding: '18px',
      'z-index': 0,
    },
  },
  {
    selector: 'node[kind="channel"]',
    style: {
      width: 'mapData(susp,0,1,10,30)',
      height: 'mapData(susp,0,1,10,30)',
      'background-color': 'data(c_fill)',
      'background-opacity': 0.9,
      'border-color': 'data(c_cred)',
      'border-width': 2,
      'border-opacity': 0.95,
      shape: 'ellipse',
      label: 'data(label)',
      'font-size': '8px',
      'font-family': 'JetBrains Mono, monospace',
      color: '#229ED9',
      'text-valign': 'bottom',
      'text-halign': 'center',
      'text-margin-y': 3,
      'min-zoomed-font-size': 7,
      'underlay-color': '#ef4444',
      'underlay-shape': 'ellipse',
      'underlay-opacity': 'data(ul_op)',
      'underlay-padding': 'data(ul_pad)',
    },
  },
  { selector: 'node[gate_met = 1]', style: { shape: 'diamond', 'border-width': 2.5 } },
  { selector: 'node[degraded = 1]', style: { 'border-style': 'dashed' } },
  {
    selector: 'node[kind="domain"]',
    style: {
      shape: 'hexagon',
      width: 11,
      height: 11,
      'background-color': '#6366f1',
      'background-opacity': 0.22,
      'border-color': '#6366f1',
      'border-width': 1.5,
      label: 'data(label)',
      'font-size': '7.5px',
      'font-family': 'JetBrains Mono, monospace',
      color: '#6366f1',
      'text-valign': 'bottom',
      'text-halign': 'center',
      'text-margin-y': 2,
      'min-zoomed-font-size': 8,
    },
  },
  {
    selector: 'edge[family="propagation"]',
    style: {
      width: 'mapData(count,1,40,1,5)',
      'line-color': 'rgba(234,88,12,.5)',
      'target-arrow-color': 'rgba(234,88,12,.7)',
      'target-arrow-shape': 'triangle',
      'arrow-scale': 0.7,
      'curve-style': 'bezier',
      opacity: 0.75,
    },
  },
  {
    selector: 'edge[family="coordination"]',
    style: {
      width: 'mapData(count,1,20,1.2,3.5)',
      'line-color': 'rgba(34,197,94,.5)',
      'line-style': 'dashed',
      'curve-style': 'bezier',
      opacity: 0.7,
      'target-arrow-shape': 'none',
    },
  },
  {
    selector: 'edge[family="influence"]',
    style: {
      width: 1.2,
      'line-color': 'rgba(120,160,220,.4)',
      'line-style': 'dotted',
      'target-arrow-color': 'rgba(120,160,220,.45)',
      'target-arrow-shape': 'triangle',
      'arrow-scale': 0.55,
      'curve-style': 'bezier',
      opacity: 0.65,
    },
  },
  { selector: 'node:selected', style: { 'border-color': '#6366f1', 'border-width': 4, 'border-opacity': 1 } },
  { selector: '.faded', style: { opacity: 0.1 } },
  { selector: '.hl', style: { 'border-color': '#6366f1', 'border-width': 4 } },
] as unknown as cytoscape.StylesheetJson
