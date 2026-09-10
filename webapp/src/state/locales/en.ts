// Dictionnaire anglais (British English / en-GB). Typé contre `Messages` :
// toute clé manquante par rapport à fr.ts échoue au typecheck.
import type { Messages } from './fr'

export const en: Messages = {
  // Switcher de langue (endonymes, identiques dans les trois dictionnaires).
  'lang.fr': 'Français',
  'lang.en': 'English',
  'lang.es': 'Español',
  'lang.nl': 'Nederlands',
  'lang.lb': 'Lëtzebuergesch',
  'lang.de': 'Deutsch',
  'lang.switcherAria': 'Choose language',

  // Author signature (§15.4) — role is translated, the name is not.
  'signature.role': 'OSINT Analyst',

  // Access gate.
  'gate.title': 'Idéfix — restricted access',
  'gate.subtitle': 'Enter the password to access the analyst interface.',
  'gate.passwordLabel': 'Password',
  'gate.unlock': 'Unlock',
  'gate.checking': 'Checking…',
  'gate.wrong': 'Incorrect password.',
  'gate.disclaimer':
    'Interface lock only. The data is still served statically — do not treat this as strong access control.',

  // Navigation.
  'nav.synthese': 'Overview',
  'nav.galaxie': 'Galaxy',
  'nav.analyse': 'Analysis',
  'nav.channels': 'Channels',
  'nav.methodologie': 'Methodology',
  'nav.mission': 'Mission',
  'nav.settings': 'Settings',
  'nav.statusSoon': 'coming soon',
  'nav.statusPlanned': 'planned',
  'nav.emptySoon': 'Data coming soon for this mission — the bundle has not been generated yet.',
  'nav.emptyPlanned': 'Planned mission — not implemented.',

  // Mission portfolio.
  'missions.intro':
    'Telegram propagation and coordination analysis platform. Choose a mission — each one is an analytical scope, with its own coverage and limitations.',
  'missions.statusActive': 'active',
  'missions.statusSoon': 'data coming soon',
  'missions.statusPlanned': 'planned',

  // Mission overview.
  'overview.emptyTitle': 'No data for this mission.',
  'overview.emptyHint': 'Generate the bundle: python scripts/export_static.py --mission {{missionId}}',
  'overview.dataHealth': 'Data health',
  'overview.keyFigures': 'Key figures',
  'overview.topSuspect': 'Most suspicious channels',
  'overview.generated': 'generated {{date}}',
  'overview.bundlePartial': 'partial bundle (public)',
  'overview.bundleComplete': 'complete bundle',
  'overview.statChannels': 'Channels',
  'overview.statEdges': 'Edges',
  'overview.statMessages': 'Messages',
  'overview.statCommunities': 'Communities',
  'overview.hintModularity': 'modularity {{value}}',
  'overview.statT2': 'T2 channels',
  'overview.hintT2': 'corroborated (≥2 families)',
  'overview.statTotal': 'Total channels',
  'overview.statDensity': 'Density',
  'overview.hintDensity': 'edges / node',
  'overview.linkGalaxieDesc': 'Explore the interactive graph',
  'overview.linkChannelsDesc': 'Full analytical table',
  'overview.caveatFallback':
    'Telegram coverage only — the mass-amplification layer is not observed.',

  // Channels table.
  'channels.title': 'All channels',
  'channels.count': '{{n}} channels',
  'channels.searchPlaceholder': 'Filter (handle / title)…',
  'channels.colCanal': 'Channel',
  'channels.colSuspicion': 'Suspicion',
  'channels.colTier': 'Tier',
  'channels.colArchetype': 'Archetype',
  'channels.colCiblage': 'Targeting',
  'channels.colGate': 'Gate',
  'channels.emptyIndex': 'No channel index for this mission.',
  'channels.emptyMatch': 'No channel matches.',

  // Settings screen.
  'settings.title': 'Settings',
  'settings.subtitle': 'Display preferences — applied locally to this browser.',
  'settings.themeLabel': 'Theme',
  'settings.themeHint': 'Light or dark interface.',
  'settings.langLabel': 'Language',
  'settings.langHint': 'Interface language.',
  'settings.communityLabel': 'Communities view',
  'settings.communityHint':
    'Galaxy grouping: structural (Analytics) or semantic (LLM Embedding).',

  // Methodology page (in-app).
  'methodology.title': 'Methodology',
  'methodology.secBrief': 'Idéfix, in brief',
  'methodology.secCoverage': 'Coverage & limitations',
  'methodology.secPipeline': 'The pipeline, end to end',
  'methodology.secScore': 'The suspicion score',
  'methodology.secTiers': 'Attribution tiers',
  'methodology.secCommunities': 'Communities: analytics vs embeddings',
  'methodology.secValidation': 'Validation status (honest)',
  'methodology.secGovernance': 'Governance & ethics',
  'methodology.step1': 'Collection',
  'methodology.step2': 'Graph construction',
  'methodology.step3': 'Suspicion score',
  'methodology.step4': 'Episode discovery',
  'methodology.step5': 'Communities',
  'methodology.step6': 'Export',
  'methodology.step7': 'Storage',
  'methodology.step8': 'Build & delivery',

  // Theme toggle.
  'theme.toLight': 'Switch to light',
  'theme.toDark': 'Switch to dark',
  'theme.toggleAria': 'Toggle theme',

  // Narrative bar (StoryBar).
  'story.heading': 'Stories',
  'story.selectedPrefix': 'Story: {{title}}',
  'story.pickerButton': 'Stories ▾',
  'story.exit': '✕ Exit story — back to the free galaxy',
  'story.statusDerived': 'reconstructed from data',
  'story.statusEditorial': 'editorial (open sources)',
  'story.statusPartial': 'partial data',
  'story.uncrawledChannels': 'uncrawled channels: {{list}}',
  'story.noTelegramData':
    'no Telegram data in the bundle for this phase — narrative documented from open sources',


  // Galaxy (GalaxyCanvas) — cockpit, legend, filters, view toggle + Cytoscape tooltips.
  'graph.view.label': 'View',
  'graph.view.galaxy': 'Galaxy',
  'graph.view.compound': 'Compound',
  'graph.search.label': 'Search',
  'graph.search.placeholder': 'Search for a channel…',
  'graph.filter.heading': 'Filters',
  'graph.filter.reset': 'reset',
  'graph.filter.nodeType': 'Node type',
  'graph.filter.channels': 'channels',
  'graph.filter.domains': 'websites',
  'graph.filter.credibility': 'Credibility',
  'graph.filter.archetype': 'Archetype',
  'graph.filter.domCategory': 'Site category',
  'graph.filter.dom.adversary': 'adversarial infra',
  'graph.filter.dom.social': 'social network',
  'graph.filter.dom.video': 'video',
  'graph.filter.dom.news': 'press / media',
  'graph.filter.dom.gov': 'institutional',
  'graph.filter.dom.other': 'other',
  'graph.spheres.heading': 'Spheres',
  'graph.spheres.open': '{{n}} open',
  'graph.recenter': '⊙ recentre',
  'graph.recenterTitle': 'Recentre the galaxy',
  'graph.emptyTitle': 'No community snapshot for this mission.',
  'graph.emptyHint':
    'Generate it: python scripts/analyze_communities.py --mission {{missionId}}, then re-export the bundle.',
  'graph.tooltip.commStats': '{{count}} channels · {{susp}} suspect(s) · {{ndom}} domain(s)',
  'graph.tooltip.clicBloom': 'click → bloom',
  'graph.tooltip.hiddenChannels': '{{hidden}} channel(s) hidden · perf budget',
  'graph.tooltip.credibility': 'credibility: {{cred}} · {{arch}}',
  'graph.tooltip.broker': 'broker (bridge)',
  'graph.tooltip.clicDossier': 'click → dossier',
  'graph.tooltip.domain': 'website · {{cat}}',
  'graph.tooltip.citedBy': 'cited by {{n}} channel(s)',
  'graph.tooltip.clicCiters': 'click → citing channels',
  'graph.tooltip.arcTitle': 'Cross-community bridge',
  'graph.tooltip.arcEdges': '{{n}} edges',
  'graph.arch.seeding-source':
    'recurrently seeds a narrative before fan-out — an early-warning target.',
  'graph.arch.forward-hub': 'widely forwarded content (strong depth-1 fan-out).',
  'graph.arch.cross-channel-bridge':
    'circulates the narrative between siloed communities — often more dangerous than the largest broadcaster.',
  'graph.arch.reactivator': 'periodically reinjects an old narrative into new discussions.',
  'graph.score.a': 'Proximity to an already-known claim (BGE-M3). Not wired in v0.',
  'graph.score.b':
    'Role in propagation (Bridge Score): seeding source / hub / cross-community bridge / reactivator.',
  'graph.score.c':
    'Coordinated behaviour (D3lta): identical texts, reposts synchronised within a Δt window, co-citations — beyond chance.',
  'graph.score.d': 'Cross-episode recidivism: forward-influence + recurrence of the seeding channel.',
  'graph.score.e': 'Probability of AI origin (text/audio/video). Not wired in v0.',
  'graph.score.f':
    'Semantic coherence (embedding): distance to organic FR baseline + proximity to known adversarial channels.',
  'graph.score.telegram_visibility': 'Observable volume/engagement of the channel.',
  'graph.score.telegram_velocity': 'Relay speed (forward latency).',
  'graph.score.telegram_source_diversity': 'Diversity of emitting channels around the node.',
  'graph.score.telegram_disclosure_precision':
    'EEFI precision of what is disclosed (position, escort, schedule…).',
  'graph.score.telegram_propagation': 'Reach (forwards gained / fan-out).',
  'graph.score.telegram_adverse_attention': 'Share of attention coming from adversarial channels (russosphere).',

  // Channel drawer (ChannelDrawer) — chrome only.
  'drawer.notInIndex': 'Channel not in the scoring index.',
  'drawer.openTelegram': 'Open on Telegram',
  'drawer.close': 'Close',
  'drawer.tierT1': 'observable broadcast',
  'drawer.tierT2': 'behavioural recurrence',
  'drawer.whyArchetype': 'Why this archetype:',
  'drawer.inNarrative': 'In the narrative — ',
  'drawer.gateMet': '✓ Corroborated by several signals',
  'drawer.gateUnmet': '✗ Insufficient corroboration',
  'drawer.gateMetDetail': 'at least two signal families agree (anti-false-positive rule).',
  'drawer.gateUnmetDetail': 'only one signal type so far: to be confirmed before concluding.',
  'drawer.fiveFamilies': 'Five signal families',
  'drawer.definition': 'Definition — ',
  'drawer.naV0': 'N/A v0',
  'drawer.calcTitle': 'Calculation detail — why this score',
  'drawer.calcRow': '{{k}} : weight {{weight}} × val {{value}}',
  'drawer.calcBase': 'base (renormalised)',
  'drawer.boostReforward': 'reforward-suspect boost',
  'drawer.boostAdversary': 'adversarial domain boost ({{n}})',
  'drawer.boostTargeting': 'targeting boost',
  'drawer.severityFactor': 'severity factor',
  'drawer.combinedSuspicion': 'combined suspicion',
  'drawer.calcFormula':
    'base = Σ(weight × value of triggered families) renormalised, then × severity factor (bounded), clamped to [0,1].',
  'drawer.noFamilyTriggered': 'No family triggered.',
  'drawer.semanticTitle': 'Semantic coherence — embedding proximity',
  'drawer.baselineDistance': 'Distance to organic FR baseline',
  'drawer.baselineScale': '0 = identical to FR media, 1 = opposite',
  'drawer.similarChannels': 'Semantically similar channels (top 3)',
  'drawer.commenters': 'Commenters of the linked group —',
  'drawer.commentersCount': '{{n}} for {{m}} messages',
  'drawer.commentersNote':
    'Observable engagement of the linked discussion group. The graph remains channel-centric — this is not a modelling of users.',
  'drawer.interactions': 'Interactions — who does what',
  'drawer.relaysFrom': 'Relays content from',
  'drawer.relayedBy': 'Relayed by',
  'drawer.coordinatedWith': 'Coordinated with',
  'drawer.citesDomains': 'Cites the domains',

  // Missions — labels, descriptions & caveats.
  'mission.russosphere.label': 'Russosphere → French far-right',
  'mission.russosphere.description': "Coordinated disinformation targeting France's image, integrity or sovereignty.",
  'mission.russosphere.caveat': 'Telegram coverage only — the mass-amplification layer (X / other platforms) is not observed.',
  'mission.gan.label': 'GAN — information footprint',
  'mission.gan.description': 'Observable Telegram footprint of the carrier group (Charles de Gaulle) — OPSEC goal of minimisation + adversarial attention.',
  'mission.gan.caveat': 'OBSERVABLE ON TELEGRAM only — not the total footprint. AIS / Strava / X / press / satellite may feed Telegram but are not collected exhaustively.',
  'mission.dircom_minarm.label': 'DIRCOM MinArm (planned)',
  'mission.dircom_minarm.description': 'Reuse / transformation / distortion of official DIRCOM messages on Telegram.',
  'mission.dircom_minarm.caveat': 'Planned mission — not implemented.',

  // Graph — theme lenses, credibility & archetype labels.
  'graph.themeLens.heading': 'Themes (lenses)',
  'graph.theme.gan': 'GAN footprint',
  'graph.theme.france_targeting': 'France targeting',
  'graph.theme.francophone': 'Francophone',
  // Scenarios: methodological warning (indicators ≠ proof of influence).
  'scenario.warning': 'This scenario surfaces documented structural indicators — never proof of influence. Read alongside the evidence levels.',
  'scenario.warning.gan': 'Informational footprint on public content only. No operational or tactical tracking; narratives, not unit positions.',
  'scenario.warning.france_targeting': 'RU→FR porosity observed on Telegram: circulation indicators, not an attribution of direct influence.',
  'graph.cred.suspect': 'suspect',
  'graph.cred.other': 'other',
  'graph.cred.legit': 'legit',
  'graph.arch.label.source': 'seeding source',
  'graph.arch.label.hub': 'forward hub',
  'graph.arch.label.bridge': 'cross-community bridge',
  'graph.arch.label.reactivator': 'reactivator',

  // GAN footprint · OPSEC panel.
  'gan.title': 'GAN footprint · OPSEC',
  'gan.channels': '{{n}} channels',
  'gan.origination': 'origination {{n}}',
  'gan.adverseShare': 'adversarial amplif. {{n}} ({{pct}}%)',
  'gan.prose': "The GAN's Telegram footprint is mostly russosphere reuse ({{pct}}%). OPSEC goal: minimise it.",
  'gan.carrierMentions': 'carrier mentions',
  'gan.internalLinks': 'internal links',
  'gan.origHead': 'Origination',
  'gan.advHead': 'Adverse',
  'gan.caveat': 'Observable on Telegram only — never the total footprint (cf. Strava).',

  // Shared.
  'common.loading': 'Loading…',
}
