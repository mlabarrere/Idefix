// Palette impérative de la GALAXIE — couleurs de rendu (Cytoscape + starfield)
// extraites de GalaxyCanvas.tsx pour éviter les hex magiques dupliqués.
// Les VALEURS sont strictement identiques à l'historique (aucun changement visuel).
// Les couleurs purement typographiques (label, outline) figurent sous `text`.

export const GALAXY = {
  // Or signature (courtiers/ponts, membres d'histoire, halos, arc chaud)
  gold: '#FAC83A',
  // Vert « graine » (canaux seed)
  seed: '#4ade80',
  // Repli couleur de communauté / de canal quand la métadonnée manque
  fallbackComm: '#3a4a63',
  fallbackNode: '#64748b',
  // Bord de sélection
  selected: '#fff',

  // Arc-pont inter-communautés : trait plein (simplifié depuis un dégradé)
  arc: '#C9880A',

  // Crédibilité (filtre + swatches)
  cred: {
    suspect: '#f87171',
    other: '#94a3b8',
    legit: '#4ade80',
  },

  // Catégories de domaines (sites web)
  dom: {
    adversary: '#f87171',
    social: '#a78bfa',
    video: '#fb7185',
    news: '#60a5fa',
    gov: '#34d399',
    other: '#94a3b8',
  },

  // Halo de nébuleuse selon le ratio de suspects
  halo: {
    suspectHigh: '#f87171', // ratio >= 0.4
    suspectMid: '#FAC83A', // ratio >= 0.15
  },

  // Arêtes canal-canal (ego-focus + intra-bloom)
  ego: {
    forward: '#EA580C',
    coord: '#22c55e',
    intraForward: 'rgba(234,88,12,.32)',
    intraCoord: 'rgba(34,197,94,.28)',
    link: 'rgba(201,136,10,.55)',
  },

  // Couleurs typographiques (labels / contours / lien Telegram dans les tooltips)
  text: {
    label: '#e7f0ff',
    outline: '#02060f',
    egoLabel: '#e2e8f0',
    telegram: '#229ed9',
  },

  // Nébuleuse : dégradé radial (stop externe sombre + facteur d'éclaircissement)
  nebula: {
    gradOuter: '#060d1c',
    lightenAmt: 0.5,
  },

  // Fond étoilé — alpha dynamique par étoile, triplets RGB constants.
  starfield: {
    gold: (a: number) => `rgba(250,200,58,${a})`,
    blue: (a: number) => `rgba(140,180,232,${a})`,
    white: (a: number) => `rgba(210,228,255,${a})`,
  },
} as const
