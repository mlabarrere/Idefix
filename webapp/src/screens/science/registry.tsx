// Registre unique de la bibliothèque scientifique : pilote la sidebar, la page
// d'accueil et les routes. Ajouter un doc = ajouter une entrée ici + sa page.
import type { ComponentType } from 'react'
import { MethodologieComplete } from './MethodologieComplete'
import { AnalyticsEmbeddings } from './AnalyticsEmbeddings'
import { AuditScientifique } from './AuditScientifique'
import { ValidationState } from './ValidationState'
import { ValidationLab } from './ValidationLab'
import { ModeleGraphe } from './ModeleGraphe'
import { Coordination } from './Coordination'
import { ContratAnalytique } from './ContratAnalytique'
import { PochesDossiers } from './PochesDossiers'
import { CapacitesAvancees } from './CapacitesAvancees'
import { Bibliographie } from './Bibliographie'
import { Glossaire } from './Glossaire'

export type ScienceDoc = {
  slug: string
  title: string
  short: string // accroche courte (sidebar + cartes d'accueil)
  source: string // .md canonique
  group: 'Méthode' | 'Validation' | 'Modèle & contrats' | 'Référence'
  Component?: ComponentType
}

export const SCIENCE_DOCS: ScienceDoc[] = [
  // ── Méthode ──────────────────────────────────────────────────────────────
  {
    slug: 'methodologie',
    title: 'Méthodologie (canonique)',
    short: 'Le document méthodologique pré-publié : familles de score, gate, tiers, validation, gouvernance.',
    source: 'METHODOLOGY.md',
    group: 'Méthode',
    Component: MethodologieComplete,
  },
  {
    slug: 'analytics-embeddings',
    title: 'Analytics vs embeddings',
    short: 'Le trade-off des deux lectures de la galaxie : cohésion sémantique vs modularité structurelle.',
    source: 'docs/analytics-vs-embedding.md',
    group: 'Méthode',
    Component: AnalyticsEmbeddings,
  },
  // ── Validation ───────────────────────────────────────────────────────────
  {
    slug: 'audit',
    title: 'Audit scientifique',
    short: 'Validité des inférences, métriques réelles, 4 expériences, gaps bloquants, verdict.',
    source: 'docs/scientific-audit.md',
    group: 'Validation',
    Component: AuditScientifique,
  },
  {
    slug: 'validation',
    title: 'État de validation',
    short: 'État de falsification du score de suspicion — ce qui est prouvé, ce qui ne l\'est pas.',
    source: 'docs/validation-state.md',
    group: 'Validation',
    Component: ValidationState,
  },
  {
    slug: 'validation-lab',
    title: 'Laboratoire de validation',
    short: 'Contrats gold épisode externe et corpus organique pour fermer les gaps de validation.',
    source: 'docs/validation-lab.md',
    group: 'Validation',
    Component: ValidationLab,
  },
  // ── Modèle & contrats ────────────────────────────────────────────────────
  {
    slug: 'graphe',
    title: 'Modèle de graphe',
    short: 'Le graphe multiplex centré-canal et ses familles d\'arêtes (propagation, influence, coordination).',
    source: 'docs/graph-model.md',
    group: 'Modèle & contrats',
    Component: ModeleGraphe,
  },
  {
    slug: 'coordination',
    title: 'Fabrique de coordination',
    short: 'Registre des signaux de coordination actifs/réservés, seuils et fenêtres temporelles.',
    source: 'docs/coordination-fabric.md',
    group: 'Modèle & contrats',
    Component: Coordination,
  },
  {
    slug: 'contrat-analytique',
    title: 'Contrat analytique',
    short: 'Contrat de données commun : claims, épisodes, preuves, poches, runs de score.',
    source: 'docs/analytical-contract.md',
    group: 'Modèle & contrats',
    Component: ContratAnalytique,
  },
  {
    slug: 'poches-dossiers',
    title: 'Poches & dossiers de preuve',
    short: 'Score de poches informationnelles et contrat Evidence Dossier v1.',
    source: 'docs/pockets-and-dossiers.md',
    group: 'Modèle & contrats',
    Component: PochesDossiers,
  },
  {
    slug: 'capacites-avancees',
    title: 'Gates de capacités avancées',
    short: 'Gates d\'activation : media reuse, GenAI, GNN, STIX.',
    source: 'docs/advanced-capability-gates.md',
    group: 'Modèle & contrats',
    Component: CapacitesAvancees,
  },
  // ── Référence ────────────────────────────────────────────────────────────
  {
    slug: 'bibliographie',
    title: 'Bibliographie',
    short: 'Références académiques ancrant chaque choix méthodologique (DOI / arXiv).',
    source: 'docs/references.md',
    group: 'Référence',
    Component: Bibliographie,
  },
  {
    slug: 'glossaire',
    title: 'Glossaire',
    short: 'Vocabulaire technique et institutionnel (usage VIGINUM/UE).',
    source: 'docs/glossary.md',
    group: 'Référence',
    Component: Glossaire,
  },
]

export const SCIENCE_GROUPS: ScienceDoc['group'][] = [
  'Méthode',
  'Validation',
  'Modèle & contrats',
  'Référence',
]
