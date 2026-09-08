// Lëtzebuergescht Wierderbuch. Géint `Messages` typiséiert:
// all Schlëssel deen am Verglach mat fr.ts feelt, brécht den Typecheck.
//
// ⚠ HUMAN-REVIEW ERFUERDERLECH (§16.7). Lëtzebuergesch huet eng dënn
// CLDR/MT-Ofdeckung; dës Wäerter sinn e Best-effort a mussen vun engem
// Mënsch iwwerpréift ginn ier se als definitiv gëllen. Kuck docs/i18n.md.
import type { Messages } from './fr'

export const lb: Messages = {
  // Sproochewiessel (Endonymer, identesch an alle Wierderbicher).
  'lang.fr': 'Français',
  'lang.en': 'English',
  'lang.es': 'Español',
  'lang.nl': 'Nederlands',
  'lang.lb': 'Lëtzebuergesch',
  'lang.de': 'Deutsch',
  'lang.switcherAria': 'Sprooch wielen',

  // Auteurssignatur.
  'signature.role': 'OSINT-Analyst',

  // Zougangsspär.
  'gate.title': 'Idéfix — beschränkten Zougang',
  'gate.subtitle': 'Gitt d’Passwuert an, fir op d’Analysten-Interface zouzegräifen.',
  'gate.passwordLabel': 'Passwuert',
  'gate.unlock': 'Opspären',
  'gate.checking': 'Gëtt iwwerpréift…',
  'gate.wrong': 'Falscht Passwuert.',
  'gate.disclaimer':
    'Nëmmen eng Interface-Spär. D’Donnéeë ginn nach ëmmer statesch ausgeliwwert — net als staark Zougangskontroll ze betruechten.',

  // Navigatioun.
  'nav.synthese': 'Iwwersiicht',
  'nav.galaxie': 'Galaxis',
  'nav.analyse': 'Analyse',
  'nav.channels': 'Kanäl',
  'nav.methodologie': 'Methodologie',
  'nav.mission': 'Missioun',
  'nav.resources': 'Ressourcen',
  'nav.science': 'Wëssenschaft',
  'nav.settings': 'Astellungen',
  'nav.statusSoon': 'geschwënn',
  'nav.statusPlanned': 'geplangt',
  'nav.emptySoon': 'Donnéeë fir dës Missioun kommen nach — de Bundle gouf nach net generéiert.',
  'nav.emptyPlanned': 'Geplangte Missioun — net ëmgesat.',

  // Missiounsportfolio.
  'missions.intro':
    'Plattform fir d’Analyse vu Verbreedung a Koordinatioun op Telegram. Wielt eng Missioun — all eng ass en analytesche Beräich, mat eegener Ofdeckung an eegene Grenzen.',
  'missions.statusActive': 'aktiv',
  'missions.statusSoon': 'Donnéeë kommen',
  'missions.statusPlanned': 'geplangt',

  // Missiounsiwwersiicht.
  'overview.emptyTitle': 'Keng Donnéeë fir dës Missioun.',
  'overview.emptyHint': 'De Bundle generéieren: python scripts/export_static.py --mission {{missionId}}',
  'overview.dataHealth': 'Donnéeëqualitéit',
  'overview.keyFigures': 'Schlësselzuelen',
  'overview.topSuspect': 'Verdächtegst Kanäl',
  'overview.generated': 'generéiert {{date}}',
  'overview.bundlePartial': 'deelweise Bundle (ëffentlech)',
  'overview.bundleComplete': 'komplette Bundle',
  'overview.statChannels': 'Kanäl',
  'overview.statEdges': 'Kanten',
  'overview.statMessages': 'Messagen',
  'overview.statCommunities': 'Communautéiten',
  'overview.hintModularity': 'Modularitéit {{value}}',
  'overview.statT2': 'T2-Kanäl',
  'overview.hintT2': 'bestätegt (≥2 Familljen)',
  'overview.statTotal': 'Kanäl am Ganzen',
  'overview.statDensity': 'Dicht',
  'overview.hintDensity': 'Kanten / Knuet',
  'overview.linkGalaxieDesc': 'Den interaktive Graf entdecken',
  'overview.linkChannelsDesc': 'Komplett Analysetabell',
  'overview.caveatFallback':
    'Nëmmen Telegram-Ofdeckung — d’Schicht vun der Massverstäerkung gëtt net observéiert.',

  // Kanaltabell.
  'channels.title': 'All Kanäl',
  'channels.count': '{{n}} Kanäl',
  'channels.searchPlaceholder': 'Filteren (Handle / Titel)…',
  'channels.colCanal': 'Kanal',
  'channels.colSuspicion': 'Verdacht',
  'channels.colTier': 'Niveau',
  'channels.colArchetype': 'Archetyp',
  'channels.colCiblage': 'Zilausriichtung',
  'channels.colGate': 'Gate',
  'channels.emptyIndex': 'Keen Kanalindex fir dës Missioun.',
  'channels.emptyMatch': 'Keen Kanal passt.',

  // Astellungen.
  'settings.title': 'Astellungen',
  'settings.subtitle': 'Uweisungsastellungen — lokal op dëse Browser applizéiert.',
  'settings.themeLabel': 'Design',
  'settings.themeHint': 'Hell oder däischter Interface.',
  'settings.langLabel': 'Sprooch',
  'settings.langHint': 'Sprooch vun der Interface.',
  'settings.communityLabel': 'Communautéits-Usiicht',
  'settings.communityHint':
    'Gruppéierung vun der Galaxis: strukturell (Analytics) oder semantesch (LLM-Embedding).',

  // Methodologie-Säit.
  'methodology.title': 'Methodologie',
  'methodology.secBrief': 'Idéfix, kuerz gefaasst',
  'methodology.secCoverage': 'Ofdeckung & Grenzen',
  'methodology.secPipeline': 'D’Pipeline, vun Ufank bis Enn',
  'methodology.secScore': 'De Verdachtsscore',
  'methodology.secTiers': 'Attributiounsniveauen',
  'methodology.secCommunities': 'Communautéiten: Analytics vs. Embeddings',
  'methodology.secValidation': 'Validéierungsstand (éierlech)',
  'methodology.secGovernance': 'Governance & Ethik',
  'methodology.step1': 'Sammlung',
  'methodology.step2': 'Grafopbau',
  'methodology.step3': 'Verdachtsscore',
  'methodology.step4': 'Episoden-Erkennung',
  'methodology.step5': 'Communautéiten',
  'methodology.step6': 'Export',
  'methodology.step7': 'Späicherung',
  'methodology.step8': 'Build & Ausliwwerung',

  // Design-Wiessel.
  'theme.toLight': 'Op Hell wiesselen',
  'theme.toDark': 'Op Däischter wiesselen',
  'theme.toggleAria': 'Design wiesselen',

  // Narrativ Leescht (StoryBar).
  'story.heading': 'Geschichten',
  'story.selectedPrefix': 'Geschicht: {{title}}',
  'story.pickerButton': 'Geschichten ▾',
  'story.exit': '✕ Geschicht verloossen — zréck op déi fräi Galaxis',
  'story.statusDerived': 'aus Donnéeë rekonstruéiert',
  'story.statusEditorial': 'redaktionell (offen Quellen)',
  'story.statusPartial': 'deelweis Donnéeën',
  'story.uncrawledChannels': 'net gecrawlt Kanäl: {{list}}',
  'story.noTelegramData':
    'keng Telegram-Donnéeën am Bundle fir dës Phase — Narrativ aus offene Quellen dokumentéiert',

  // Episoden-Usiicht + RU→FR-Panel.

  // Galaxis (GalaxyCanvas) — Cockpit, Legend, Filteren, Usiichtwiessel + Tooltips.
  'graph.view.label': 'Usiicht',
  'graph.view.galaxy': 'Galaxis',
  'graph.view.compound': 'Compound',
  'graph.search.label': 'Sichen',
  'graph.search.placeholder': 'E Kanal sichen…',
  'graph.filter.heading': 'Filteren',
  'graph.filter.reset': 'zerécksetzen',
  'graph.filter.nodeType': 'Knuettyp',
  'graph.filter.channels': 'Kanäl',
  'graph.filter.domains': 'Websäiten',
  'graph.filter.credibility': 'Glafwierdegkeet',
  'graph.filter.archetype': 'Archetyp',
  'graph.filter.domCategory': 'Websäit-Kategorie',
  'graph.filter.dom.adversary': 'géignereg Infrastruktur',
  'graph.filter.dom.social': 'sozialt Netzwierk',
  'graph.filter.dom.video': 'Video',
  'graph.filter.dom.news': 'Press / Medien',
  'graph.filter.dom.gov': 'institutionell',
  'graph.filter.dom.other': 'aner',
  'graph.spheres.heading': 'Sphären',
  'graph.spheres.open': '{{n}} op',
  'graph.recenter': '⊙ zentréieren',
  'graph.recenterTitle': 'D’Galaxis nei zentréieren',
  'graph.emptyTitle': 'Keen Communautéits-Snapshot fir dës Missioun.',
  'graph.emptyHint':
    'Generéieren: python scripts/analyze_communities.py --mission {{missionId}}, duerno de Bundle nei exportéieren.',
  'graph.tooltip.commStats': '{{count}} Kanäl · {{susp}} verdächteg · {{ndom}} Domain(en)',
  'graph.tooltip.clicBloom': 'Klick → opbléien',
  'graph.tooltip.hiddenChannels': '{{hidden}} Kanal/Kanäl verstoppt · Perf-Budget',
  'graph.tooltip.credibility': 'Glafwierdegkeet: {{cred}} · {{arch}}',
  'graph.tooltip.broker': 'Vermëttler (Bréck)',
  'graph.tooltip.clicDossier': 'Klick → Dossier',
  'graph.tooltip.domain': 'Websäit · {{cat}}',
  'graph.tooltip.citedBy': 'zitéiert vun {{n}} Kanal/Kanäl',
  'graph.tooltip.clicCiters': 'Klick → zitéierend Kanäl',
  'graph.tooltip.arcTitle': 'Bréck tëscht Communautéiten',
  'graph.tooltip.arcEdges': '{{n}} Kanten',
  'graph.arch.seeding-source':
    'sä-t widderholl en Narrativ virum Fan-out — e Fréiwarnungszil.',
  'graph.arch.forward-hub': 'breet weidergeleeten Inhalt (staarke Fan-out op Déift 1).',
  'graph.arch.cross-channel-bridge':
    'léisst d’Narrativ tëscht ofgeschotte Communautéite circuléieren — dacks méi geféierlech wéi de gréisste Sender.',
  'graph.arch.reactivator': 'reinjizéiert reegelméisseg en aalt Narrativ an nei Diskussiounen.',
  'graph.score.a': 'Noosinn zu enger scho bekannter Behaaptung (BGE-M3). An v0 net verdrahtet.',
  'graph.score.b':
    'Roll bei der Verbreedung (Bridge Score): Sä-Quell / Hub / Bréck tëscht Communautéiten / Reaktivator.',
  'graph.score.c':
    'Koordinéiert Verhalen (D3lta): identesch Texter, an engem Δt-Fënster synchroniséiert Reposts, Ko-Zitatioune — iwwer den Zoufall eraus.',
  'graph.score.d': 'Iwwergräifende Réckfall: Forward-Afloss + Widderkéier vum Sä-Kanal.',
  'graph.score.e': 'Wahrscheinlechkeet vun engem KI-Urspronk (Text/Audio/Video). An v0 net verdrahtet.',
  'graph.score.f':
    'Semantesch Kohärenz (Embedding): Distanz zur organescher FR-Baseline + Noosinn zu bekannte géignereg Kanäl.',
  'graph.score.telegram_visibility': 'Observéierbart Volumen/Engagement vum Kanal.',
  'graph.score.telegram_velocity': 'Relaisgeschwindegkeet (Forward-Latenz).',
  'graph.score.telegram_source_diversity': 'Diversitéit vun de sendende Kanäl ronderëm de Knuet.',
  'graph.score.telegram_disclosure_precision':
    'EEFI-Präzisioun vun deem wat opgedeckt gëtt (Positioun, Eskort, Zäitplang…).',
  'graph.score.telegram_propagation': 'Reechwäit (gewonnen Forwards / Fan-out).',
  'graph.score.telegram_adverse_attention': 'Undeel vun der Opmierksamkeet vu géignereg Kanäl (Russosphär).',

  // Kanal-Drawer (ChannelDrawer).
  'drawer.notInIndex': 'Kanal net am Scoring-Index.',
  'drawer.openTelegram': 'An Telegram opmaachen',
  'drawer.close': 'Zoumaachen',
  'drawer.tierT1': 'observéierbar Verbreedung',
  'drawer.tierT2': 'verhalensbezunnen Widderkéier',
  'drawer.whyArchetype': 'Firwat dësen Archetyp:',
  'drawer.inNarrative': 'Am Narrativ — ',
  'drawer.gateMet': '✓ Bestätegt vu méintere Signaler',
  'drawer.gateUnmet': '✗ Net genuch Bestätegung',
  'drawer.gateMetDetail': 'op d’mannst zwou Signalfamilljen decken sech (Anti-Falsch-Positiv-Regel).',
  'drawer.gateUnmetDetail': 'bis elo nëmmen ee Signaltyp: virun engem Schluss ze bestätegen.',
  'drawer.fiveFamilies': 'Fënnef Signalfamilljen',
  'drawer.definition': 'Definitioun — ',
  'drawer.naV0': 'N/A v0',
  'drawer.calcTitle': 'Berechnungsdetail — firwat dëse Score',
  'drawer.calcRow': '{{k}}: Gewiicht {{weight}} × Wäert {{value}}',
  'drawer.calcBase': 'Basis (renormaliséiert)',
  'drawer.boostReforward': 'Reforward-Verdacht-Boost',
  'drawer.boostAdversary': 'Géigner-Domain-Boost ({{n}})',
  'drawer.boostTargeting': 'Zilausriichtungs-Boost',
  'drawer.severityFactor': 'Schweregradfaktor',
  'drawer.combinedSuspicion': 'kombinéierte Verdacht',
  'drawer.calcFormula':
    'Basis = Σ(Gewiicht × Wäert vun den ausgeléiste Familljen) renormaliséiert, dann × Schweregradfaktor (begrenzt), op [0,1] beschränkt.',
  'drawer.noFamilyTriggered': 'Keng Famill ausgeléist.',
  'drawer.semanticTitle': 'Semantesch Kohärenz — Embedding-Noosinn',
  'drawer.baselineDistance': 'Distanz zur organescher FR-Baseline',
  'drawer.baselineScale': '0 = identesch mat FR-Medien, 1 = entgéintgesat',
  'drawer.similarChannels': 'Semantesch ähnlech Kanäl (Top 3)',
  'drawer.commenters': 'Kommentatoren vun der verbonnener Grupp —',
  'drawer.commentersCount': '{{n}} fir {{m}} Messagen',
  'drawer.commentersNote':
    'Observéierbart Engagement vun der verbonnener Diskussiounsgrupp. De Graf bleift kanalzentréiert — dëst ass keng Modelléierung vun de Benotzer.',
  'drawer.interactions': 'Interaktiounen — wien mécht wat',
  'drawer.relaysFrom': 'Leet Inhalt weider vun',
  'drawer.relayedBy': 'Weidergeleet vun',
  'drawer.coordinatedWith': 'Koordinéiert mat',
  'drawer.citesDomains': 'Zitéiert d’Domainen',

  'mission.russosphere.label': 'Russosphär → franséisch riets Extrem',
  'mission.russosphere.description': "Koordinéiert Desinformatioun géint d'Bild, d'Integritéit oder d'Souveränitéit vu Frankräich.",
  'mission.russosphere.caveat': "Nëmmen Telegram-Ofdeckung — d'Schicht vun der Massverstäerkung (X / aner Plattformen) gëtt net observéiert.",
  'mission.gan.label': 'GAN — informationell Spuer',
  'mission.gan.description': 'Observéierbar Telegram-Spuer vun der Fliger-Marinegrupp (Charles de Gaulle) — OPSEC-Zil vun der Miniméierung + géignereg Opmierksamkeet.',
  'mission.gan.caveat': 'NËMMEN OP TELEGRAM OBSERVÉIERBAR — net déi ganz Spuer. AIS / Strava / X / Press / Satellit kënnen Telegram späisen, gi awer net komplett gesammelt.',
  'mission.dircom_minarm.label': 'DIRCOM MinArm (geplangt)',
  'mission.dircom_minarm.description': 'Erëmverwäertung / Transformatioun / Verzerrung vun offiziellen DIRCOM-Messagen op Telegram.',
  'mission.dircom_minarm.caveat': 'Geplangte Missioun — net ëmgesat.',
  'graph.themeLens.heading': 'Themen (Lënsen)',
  'graph.theme.gan': 'GAN-Spuer',
  'graph.theme.france_targeting': 'Frankräich-Ziler',
  'graph.theme.francophone': 'Frankophon',
  // Szenarien: methodologesch Warnung (Indizien ≠ Beweis vun Afloss).
  'scenario.warning': 'Dëse Szenario weist dokumentéiert strukturell Indizien — ni e Beweis vun Afloss. Mat de Beweisniveauen liesen.',
  'scenario.warning.gan': 'Informatiounsofdrock nëmmen op ëffentlechen Inhalter. Keng operationell oder taktesch Verfolgung; Narrativen, keng Eenheetspositiounen.',
  'scenario.warning.france_targeting': 'RU→FR-Porositéit op Telegram observéiert: Indizien vun der Zirkulatioun, keng Attributioun vun direktem Afloss.',
  'graph.cred.suspect': 'verdächteg',
  'graph.cred.other': 'aner',
  'graph.cred.legit': 'legitim',
  'graph.arch.label.source': 'Sä-Quell',
  'graph.arch.label.hub': 'Forward-Hub',
  'graph.arch.label.bridge': 'Bréck tëscht Communautéiten',
  'graph.arch.label.reactivator': 'Reaktivator',
  'gan.title': 'GAN-Spuer · OPSEC',
  'gan.channels': '{{n}} Kanäl',
  'gan.origination': 'Urspronk {{n}}',
  'gan.adverseShare': 'géignereg Verstäerkung {{n}} ({{pct}}%)',
  'gan.prose': "D'Telegram-Spuer vum GAN ass virun allem Russosphär-Erëmverwäertung ({{pct}}%). OPSEC-Zil: miniméieren.",
  'gan.carrierMentions': 'Erwähnunge vum Fliger-Dréier',
  'gan.internalLinks': 'intern Linken',
  'gan.origHead': 'Urspronk',
  'gan.advHead': 'Géignereg',
  'gan.caveat': 'Nëmmen op Telegram observéierbar — ni déi ganz Spuer (cf. Strava).',

  // Gemeinsam.
  'common.loading': 'Gëtt gelueden…',
}
