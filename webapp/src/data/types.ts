// Contrat de données du bundle statique (produit par scripts/export_static.py +
// analyze_communities.py / analyze_porosity.py). Aucun backend.

export interface Manifest {
  version?: string
  generated_at: string
  public?: boolean
  mission?: string
  files?: Record<string, string>
  // Export complet (export_static.py). Absent du bundle REST minimal.
  stats?: { n_channels: number; n_edges: number; n_messages: number }
  // Bundle REST minimal (export_via_rest_api.py) — pas de bloc `stats`.
  channels_count?: number
}

export interface SymmetricRatio {
  adversary_infra: number
  organic_fr: number
  note?: string
}

export interface ChannelIndexRow {
  channel_id: number
  username: string | null
  title: string | null
  suspicion: number | null
  tier: string | null
  archetype: string | null
  credibility_prior: string | null
  fr_score: number | null
  france_targeting: number | null
  gate_met: boolean | null
}

export interface ChannelsIndex {
  generated_at: string
  coverage_callout?: string
  symmetric_ratio?: SymmetricRatio
  total: number
  channels: ChannelIndexRow[]
}

// --- Graphe (graph.json) ---------------------------------------------------
export interface GraphNodeChannel {
  channel_id: number
  username: string
  title: string
  archetype: string | null
  credibility_prior: string
  engagement: number
  fr_score: number | null
  confidence?: { level: string; reason: string }
}
export interface GraphNodeDomain {
  domain: string
}
export type GraphNode = GraphNodeChannel | GraphNodeDomain

export interface GraphEdge {
  family: 'propagation' | 'coordination' | 'influence'
  type: string
  source?: number | string
  target?: number | string
  a?: number
  b?: number
  count?: number
  delay_seconds?: number | null
  dt_seconds?: number | null
}

export interface GraphData {
  generated_at: string
  coverage_callout?: string
  nodes: GraphNode[]
  edges: GraphEdge[]
}

// --- Snapshot communautés (russosphere_snapshot.json) ----------------------
export interface SphereChannel {
  channel_id: number
  username: string
  title: string
  engagement: number
  credibility_prior: string
  fr_score: number | null
  member_count: number | null
  betweenness: number
  is_seed: boolean
}
// Étiquette LLM (piste parallèle Mistral) — additif, optionnel. Provient du
// snapshot parallèle <mission>_llm_snapshot.json (jamais du snapshot lexical).
export interface LlmLabel {
  label: string
  theme?: string
  confidence: number | null
  rationale?: string
}
export interface Community {
  id: number
  label: string
  color: string
  size: number
  n_domains: number
  n_suspects: number
  channels: SphereChannel[]
  domains: string[]
  llm?: LlmLabel | null
}
export interface Bridge {
  channel_id: number
  username: string
  title: string
  betweenness: number
  credibility_prior: string
  community: string
  community_id: number
  connects: { label: string; edges: number }[]
  is_seed: boolean
}
export interface MetaGraph {
  nodes: { id: number; label: string; color: string; size: number; n_suspects: number }[]
  edges: { source: number; target: number; weight: number }[]
}
// Deltas factuels Analytics ↔ LLM Embedding (snapshot embedding seulement).
// Produit par src/embed/community.comparison_block — alimente le callout du switch.
export interface SnapshotComparison {
  intra_cohesion: { analytics: number; embedding: number; gain_pct: number | null }
  modularity: { analytics: number; embedding: number }
  n_communities: { analytics: number; embedding: number }
  n_bridges: number
  metric_note?: string
}
export interface RussosphereSnapshot {
  generated_at: string
  seed?: { channel_id: number; username: string; community_id: number; community_label: string }
  // 'embedding' pour le snapshot <mission>_embed_snapshot.json (sinon Analytics).
  label_source?: string
  model?: string
  stats: {
    n_nodes: number
    n_channels: number
    n_domains: number
    n_edges: number
    n_communities: number
    modularity: number
    comparison?: SnapshotComparison
  }
  communities: Community[]
  bridges: Bridge[]
  meta_graph: MetaGraph
  coverage_callout?: string
}

// --- Diff de snapshots (snapshot_diff.json — scripts/compare_snapshots.py) ---
// Décrit l'évolution des communautés entre deux runs. Champs de comptage
// optionnels ; `channels_drifted` peut être un nombre OU un tableau (defensive).
export interface SnapshotDiff {
  mission?: string
  compared_snapshots?: [string, string] | string[]
  channels_appeared?: number
  channels_disappeared?: number
  channels_drifted?: number | unknown[]
  communities_merged?: number
  communities_split?: number
  flag_high_drift?: string
}

// --- Détail canal explicable (channels/<id>.json) --------------------------
export interface ScoreFamily {
  n: string // libellé
  v: number
  lo: number
  hi: number
  c: string // couleur hex
  na?: boolean
  ev: [string, unknown][]
  label?: string | null
  // Scoring rigoureux (additif, optionnel) : significativité vs modèle nul.
  z?: number
  p?: number
  ci?: [number, number]
  significant?: boolean
}
export interface SeverityDetail {
  reforward_suspect_frac?: number
  reforward_boost?: number
  adversary_domain_citations?: number
  adversary_domains?: string[]
  adversary_boost?: number
  france_targeting?: number | null
  france_boost?: number
  factor?: number
}
export interface ScoreComponents {
  [family: string]:
    | { weight: number; value: number | null; contribution?: number; triggered?: boolean; na?: boolean }
    | number
    | SeverityDetail
    | undefined
  _base?: number
  _severity_factor?: number
  _combined?: number
  _severity_detail?: SeverityDetail
}
export interface ChannelDetail {
  channel_id: number
  username: string | null
  title: string
  suspicion: { v: number; lo: number; hi: number }
  archetype: string | null
  credibility_prior: string
  fr_score: number | null
  france_targeting: number | null
  reforward_from?: { suspect: number; legit: number; other: number }
  scores: Record<string, ScoreFamily>
  confidence?: { level: string; reason: string; age_days?: number }
  gate?: { met: boolean; families: number; detail: string }
  tier?: string
  _components?: ScoreComponents
  llm?: LlmLabel | null
  // Scoring rigoureux (additif) : p combinée (Stouffer), q-value FDR, drapeau.
  p_combined?: number
  q_value?: number
  flagged?: boolean
  // Phase 1 embedding signals
  embedding_proximity?: { channel_id: number; handle: string; cosine: number }[]
}

// --- Histoires (stories.json — sélecteur narratif, UX rév. 2 couche 2) ------
export interface StoryEvidence {
  kind: string
  [k: string]: unknown
}
export interface StoryPhase {
  id: string
  name: string
  date_label: string
  date_range: [string, string]
  headline_stat: string
  narrative: string
  channel_ids: number[]
  usernames: string[]
  missing_usernames?: string[]
  evidence?: StoryEvidence[]
}
export interface Story {
  id: string
  title: string
  subtitle?: string
  // derived = reconstruite des données · editorial = documentée hors-base ·
  // partial = éditoriale dont des canaux manquent au bundle (honnêteté affichée)
  data_status: 'derived' | 'editorial' | 'partial'
  tier?: string
  phases: StoryPhase[]
}
export interface StoriesBundle {
  generated_at: string
  mission: string
  stories: Story[]
}

// --- Thèmes (themes.json) — lentilles sur LE graphe unique ------------------
// Chaque thème = un ensemble de canaux portant ce thème (GAN / ciblage France /
// francophone…). Illuminer un thème montre où ses canaux vivent dans la galaxie
// et leurs liens avec les autres — « faire des liens entre russophilie/RN/GAN ».
export interface Theme {
  id: string
  label: string
  color: string
  channel_ids: number[]
}
export interface ThemesBundle {
  generated_at: string
  themes: Theme[]
}

// --- Empreinte GAN (gan_footprint.json — OPSEC) -----------------------------
export interface GanChannelRef {
  channel_id: number
  username: string
  title: string
  gan_targeting: number
  credibility: string
  messages?: number
}
export interface GanFootprint {
  generated_at: string
  n_channels: number
  n_origination: number
  n_adverse: number
  internal_circulation: { forward?: number; media_reuse?: number; co_forward?: number }
  carrier_mentions: number
  origination: GanChannelRef[]
  adverse: GanChannelRef[]
  recent_mentions: { username: string; credibility: string; ts: string; text: string }[]
  timeline: { month: string; n: number }[]
  coverage_callout?: string
}

// --- Commentateurs (commenters.json — engagement des groupes liés) ----------
export interface CommentersChannel {
  n_comments: number
  n_commenters: number
  top: { id: number; username: string | null; count: number }[]
}
export interface CommentersBundle {
  generated_at: string
  mission: string
  n_channels: number
  note?: string
  channels: Record<string, CommentersChannel>
}
