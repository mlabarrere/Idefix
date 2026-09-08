// Dictionnaire source (français) — SOURCE DE VÉRITÉ des clés d'i18n.
// Plat, clés en notation pointée stable. Le français est la langue source :
// tout ajout de clé se fait d'abord ici, puis se répercute dans en.ts / es.ts
// (typés contre `Messages`, donc une clé manquante casse le typecheck).
//
// Phases 1B → 2C/2D : extraction du switcher de langue, du verrou d'accès (gate),
// puis du chrome d'UI (nav, portfolio, synthèse, canaux, paramètres, méthodologie,
// thème, commun). Le contenu éditorial (labels/descriptions de missions, prose de
// la page méthodologie) reste en français côté données.
export const fr = {
  // Switcher de langue (endonymes : mêmes libellés dans les trois dictionnaires).
  'lang.fr': 'Français',
  'lang.en': 'English',
  'lang.es': 'Español',
  'lang.nl': 'Nederlands',
  'lang.lb': 'Lëtzebuergesch',
  'lang.de': 'Deutsch',
  'lang.switcherAria': 'Choisir la langue',

  // Signature auteur (§15.4) — le rôle est traduit, le nom ne l'est pas.
  'signature.role': 'Analyste OSINT',

  // Verrou d'accès (PasswordGate) — FR byte-identique aux littéraux actuels.
  'gate.title': 'Idéfix — accès restreint',
  'gate.subtitle': "Saisissez le mot de passe pour accéder à l'interface analyste.",
  'gate.passwordLabel': 'Mot de passe',
  'gate.unlock': 'Déverrouiller',
  'gate.checking': 'Vérification…',
  'gate.wrong': 'Mot de passe incorrect.',
  'gate.disclaimer':
    "Verrou d'interface uniquement. Les données restent servies en statique — ne pas considérer comme un contrôle d'accès fort.",

  // Navigation (coquille produit) — libellés d'onglets, liens, suffixes de statut,
  // aria-labels et états vides de mission.
  'nav.synthese': 'Synthèse',
  'nav.galaxie': 'Galaxie',
  'nav.analyse': 'Analyse',
  'nav.channels': 'Canaux',
  'nav.methodologie': 'Méthodologie',
  'nav.mission': 'Mission',
  'nav.resources': 'Ressources',
  'nav.science': 'Science',
  'nav.settings': 'Paramètres',
  'nav.statusSoon': 'à venir',
  'nav.statusPlanned': 'planifiée',
  'nav.emptySoon': 'Données à venir pour cette mission — le bundle n’a pas encore été généré.',
  'nav.emptyPlanned': 'Mission planifiée — non implémentée.',

  // Portfolio des missions (page d'accueil) — intro + badges de statut.
  // (les labels/descriptions/caveats des missions restent des DONNÉES, non traduits.)
  'missions.intro':
    "Plateforme d'analyse de propagation et de coordination sur Telegram. Choisissez une mission — chacune est un périmètre analytique, avec sa couverture et ses limites.",
  'missions.statusActive': 'active',
  'missions.statusSoon': 'données à venir',
  'missions.statusPlanned': 'planifiée',

  // Synthèse mission — en-têtes de section, libellés/indices de stats, liens de vue.
  'overview.emptyTitle': 'Aucune donnée pour cette mission.',
  'overview.emptyHint': 'Générez le bundle : python scripts/export_static.py --mission {{missionId}}',
  'overview.dataHealth': 'Santé des données',
  'overview.keyFigures': 'Chiffres clés',
  'overview.topSuspect': 'Canaux les plus suspects',
  'overview.generated': 'généré {{date}}',
  'overview.bundlePartial': 'bundle partiel (public)',
  'overview.bundleComplete': 'bundle complet',
  'overview.statChannels': 'Canaux',
  'overview.statEdges': 'Arêtes',
  'overview.statMessages': 'Messages',
  'overview.statCommunities': 'Communautés',
  'overview.hintModularity': 'modularité {{value}}',
  'overview.statT2': 'Canaux T2',
  'overview.hintT2': 'corroborés (≥2 familles)',
  'overview.statTotal': 'Total canaux',
  'overview.statDensity': 'Densité',
  'overview.hintDensity': 'arêtes / nœud',
  'overview.linkGalaxieDesc': 'Explorer le graphe interactif',
  'overview.linkChannelsDesc': 'Table analytique complète',
  'overview.caveatFallback':
    "Couverture Telegram uniquement — la couche d'amplification de masse n'est pas observée.",

  // Table des canaux — en-têtes de colonnes, recherche, compte, états vides.
  'channels.title': 'Tous les canaux',
  'channels.count': '{{n}} canaux',
  'channels.searchPlaceholder': 'Filtrer (handle / titre)…',
  'channels.colCanal': 'Canal',
  'channels.colSuspicion': 'Suspicion',
  'channels.colTier': 'Tier',
  'channels.colArchetype': 'Archétype',
  'channels.colCiblage': 'Ciblage',
  'channels.colGate': 'Gate',
  'channels.emptyIndex': 'Aucun index de canaux pour cette mission.',
  'channels.emptyMatch': 'Aucun canal ne correspond.',

  // Écran Paramètres — titre, sous-titre, libellés/indices des réglages.
  'settings.title': 'Paramètres',
  'settings.subtitle': "Préférences d'affichage — appliquées localement à ce navigateur.",
  'settings.themeLabel': 'Thème',
  'settings.themeHint': 'Interface claire ou sombre.',
  'settings.langLabel': 'Langue',
  'settings.langHint': "Langue de l'interface.",
  'settings.communityLabel': 'Vue communautés',
  'settings.communityHint':
    'Regroupement de la galaxie : structurel (Analytics) ou sémantique (LLM Embedding).',

  // Page méthodologie (in-app) — titre + en-têtes de section + noms d'étapes.
  // (la prose des sections reste du contenu éditorial en français, non traduit.)
  'methodology.title': 'Méthodologie',
  'methodology.secBrief': 'Idéfix, en bref',
  'methodology.secCoverage': 'Couverture & limites',
  'methodology.secPipeline': 'Le pipeline, de bout en bout',
  'methodology.secScore': 'Le score de suspicion',
  'methodology.secTiers': "Tiers d'attribution",
  'methodology.secCommunities': 'Communautés : analytics vs embeddings',
  'methodology.secValidation': 'État de validation (honnête)',
  'methodology.secGovernance': 'Gouvernance & éthique',
  'methodology.step1': 'Collecte',
  'methodology.step2': 'Construction du graphe',
  'methodology.step3': 'Score de suspicion',
  'methodology.step4': "Découverte d'épisodes",
  'methodology.step5': 'Communautés',
  'methodology.step6': 'Export',
  'methodology.step7': 'Stockage',
  'methodology.step8': 'Build & diffusion',

  // Bascule de thème (tooltips + aria).
  'theme.toLight': 'Passer en clair',
  'theme.toDark': 'Passer en sombre',
  'theme.toggleAria': 'Basculer le thème',

  // Bandeau narratif (StoryBar) — sélecteur d'histoires + phases + honnêteté.
  'story.heading': 'Histoires',
  'story.selectedPrefix': 'Histoire : {{title}}',
  'story.pickerButton': 'Histoires ▾',
  'story.exit': "✕ Quitter l'histoire — retour à la galaxie libre",
  'story.statusDerived': 'reconstruite des données',
  'story.statusEditorial': 'éditoriale (sources ouvertes)',
  'story.statusPartial': 'données partielles',
  'story.uncrawledChannels': 'canaux non crawlés : {{list}}',
  'story.noTelegramData':
    'aucune donnée Telegram dans le bundle pour cette phase — narration documentée par sources ouvertes',


  // Galaxie (GalaxyCanvas) — cockpit, légende, filtres, bascule de vue + tooltips
  // Cytoscape. Les libellés de communautés/boîtes restent des DONNÉES (non traduits) ;
  // de même les valeurs d'énumération (archétype brut, crédibilité) affichées telles quelles.
  'graph.view.label': 'Vue',
  'graph.view.galaxy': 'Galaxie',
  'graph.view.compound': 'Compound',
  'graph.search.label': 'Recherche',
  'graph.search.placeholder': 'Rechercher un canal…',
  'graph.filter.heading': 'Filtres',
  'graph.filter.reset': 'réinitialiser',
  'graph.filter.nodeType': 'Type de nœud',
  'graph.filter.channels': 'canaux',
  'graph.filter.domains': 'sites web',
  'graph.filter.credibility': 'Crédibilité',
  'graph.filter.archetype': 'Archétype',
  'graph.filter.domCategory': 'Catégorie de site',
  // Catégories de domaines (typologie heuristique client) — libellés chrome.
  'graph.filter.dom.adversary': 'infra adverse',
  'graph.filter.dom.social': 'réseau social',
  'graph.filter.dom.video': 'vidéo',
  'graph.filter.dom.news': 'presse / média',
  'graph.filter.dom.gov': 'institutionnel',
  'graph.filter.dom.other': 'autre',
  'graph.spheres.heading': 'Sphères',
  'graph.spheres.open': '{{n}} ouverte(s)',
  'graph.recenter': '⊙ recentrer',
  'graph.recenterTitle': 'Recentrer la galaxie',
  'graph.emptyTitle': 'Pas de snapshot de communautés pour cette mission.',
  'graph.emptyHint':
    'Générez : python scripts/analyze_communities.py --mission {{missionId}}, puis ré-exportez le bundle.',
  // Tooltips Cytoscape (construits en HTML impératif) — rendus via tRef.current.
  'graph.tooltip.commStats': '{{count}} canaux · {{susp}} suspect(s) · {{ndom}} domaine(s)',
  'graph.tooltip.clicBloom': 'clic → éclore',
  'graph.tooltip.hiddenChannels': '{{hidden}} canal(aux) masqué(s) · budget perf',
  'graph.tooltip.credibility': 'crédibilité : {{cred}} · {{arch}}',
  'graph.tooltip.broker': 'courtier (pont)',
  'graph.tooltip.clicDossier': 'clic → dossier',
  'graph.tooltip.domain': 'site web · {{cat}}',
  'graph.tooltip.citedBy': 'cité par {{n}} canal(aux)',
  'graph.tooltip.clicCiters': 'clic → canaux citeurs',
  'graph.tooltip.arcTitle': 'Pont inter-communautés',
  'graph.tooltip.arcEdges': '{{n}} arêtes',
  // Interprétations d'archétype (grammar.ts, drawer « Pourquoi cet archétype »).
  'graph.arch.seeding-source':
    "amorce récurremment une narrative avant le fan-out — cible d'alerte précoce.",
  'graph.arch.forward-hub': 'contenu largement forwardé (fort fan-out depth-1).',
  'graph.arch.cross-channel-bridge':
    'fait circuler la narrative entre communautés cloisonnées — souvent plus dangereux que le plus gros diffuseur.',
  'graph.arch.reactivator': 'réinjecte périodiquement une vieille narrative dans de nouvelles discussions.',
  // Définitions des familles de score (grammar.ts, drawer + title des tooltips).
  'graph.score.a': 'Proximité à une revendication déjà connue (BGE-M3). Non câblé en v0.',
  'graph.score.b':
    "Rôle dans la propagation (Bridge Score) : source d'amorçage / hub / pont inter-communautés / réactivateur.",
  'graph.score.c':
    'Comportement coordonné (D3lta) : mêmes textes, reposts synchronisés sur fenêtre Δt, co-citations — au-delà du hasard.',
  'graph.score.d': "Récidive inter-épisodes : forward-influence + récurrence du canal d'amorçage.",
  'graph.score.e': "Probabilité d'origine IA (texte/audio/vidéo). Non câblé en v0.",
  'graph.score.f':
    'Cohérence sémantique (embedding) : distance à baseline FR organique + proximité à canaux adversaires connus.',
  'graph.score.telegram_visibility': 'Volume/engagement observable du canal.',
  'graph.score.telegram_velocity': 'Rapidité de relais (latence de forward).',
  'graph.score.telegram_source_diversity': 'Diversité des canaux émetteurs autour du nœud.',
  'graph.score.telegram_disclosure_precision':
    'Précision EEFI de ce qui est divulgué (position, escorte, calendrier…).',
  'graph.score.telegram_propagation': 'Portée (forwards gagnés / fan-out).',
  'graph.score.telegram_adverse_attention': "Part de l'attention venant de canaux adverses (russosphère).",

  // Drawer canal (ChannelDrawer) — chrome uniquement (titres/@handles/nombres = DONNÉES).
  'drawer.notInIndex': 'Canal absent de l’index de scoring.',
  'drawer.openTelegram': 'Ouvrir sur Telegram',
  'drawer.close': 'Fermer',
  'drawer.tierT1': 'diffusion observable',
  'drawer.tierT2': 'récurrence comportementale',
  'drawer.whyArchetype': 'Pourquoi cet archétype :',
  'drawer.inNarrative': 'Dans le récit — ',
  'drawer.gateMet': '✓ Corroboré par plusieurs signaux',
  'drawer.gateUnmet': '✗ Corroboration insuffisante',
  'drawer.gateMetDetail': 'au moins deux familles de signal concordent (règle anti-faux-positif).',
  'drawer.gateUnmetDetail': 'un seul type de signal pour l’instant : à confirmer avant de conclure.',
  'drawer.fiveFamilies': 'Cinq familles de signal',
  'drawer.definition': 'Définition — ',
  'drawer.naV0': 'N/A v0',
  'drawer.calcTitle': 'Détail du calcul — pourquoi ce score',
  'drawer.calcRow': '{{k}} : poids {{weight}} × val {{value}}',
  'drawer.calcBase': 'base (renormalisée)',
  'drawer.boostReforward': 'boost reforward-suspect',
  'drawer.boostAdversary': 'boost domaine adverse ({{n}})',
  'drawer.boostTargeting': 'boost ciblage',
  'drawer.severityFactor': 'facteur de sévérité',
  'drawer.combinedSuspicion': 'suspicion combinée',
  'drawer.calcFormula':
    'base = Σ(poids × valeur des familles déclenchées) renormalisée, puis × facteur de sévérité (borné), borné [0,1].',
  'drawer.noFamilyTriggered': 'Aucune famille déclenchée.',
  'drawer.semanticTitle': 'Cohérence sémantique — proximité embedding',
  'drawer.baselineDistance': 'Distance baseline FR organique',
  'drawer.baselineScale': '0 = identique médias FR, 1 = opposé',
  'drawer.similarChannels': 'Canaux sémantiquement similaires (top 3)',
  'drawer.commenters': 'Commentateurs du groupe lié —',
  'drawer.commentersCount': '{{n}} pour {{m}} messages',
  'drawer.commentersNote':
    "Engagement observable du groupe de discussion lié. Le graphe reste canal-centrique — ceci n'est pas une modélisation des utilisateurs.",
  'drawer.interactions': 'Interactions — qui fait quoi',
  'drawer.relaysFrom': 'Relaie le contenu de',
  'drawer.relayedBy': 'Relayé par',
  'drawer.coordinatedWith': 'Coordonné avec',
  'drawer.citesDomains': 'Cite les domaines',

  // Missions (label/description/caveat) — étaient des DONNÉES codées en dur, désormais i18n.
  'mission.russosphere.label': 'Russosphère → extrême droite FR',
  'mission.russosphere.description':
    "Désinformation coordonnée visant l'image, l'intégrité ou la souveraineté de la France.",
  'mission.russosphere.caveat':
    "Couverture Telegram uniquement — la couche d'amplification de masse (X / autres plateformes) n'est pas observée.",
  'mission.gan.label': 'GAN — empreinte informationnelle',
  'mission.gan.description':
    "Empreinte observable sur Telegram du groupe aéronaval (Charles de Gaulle) — objectif OPSEC de minimisation + attention adverse.",
  'mission.gan.caveat':
    "Empreinte OBSERVABLE SUR TELEGRAM uniquement — non l'empreinte totale. AIS / Strava / X / presse / satellite peuvent alimenter Telegram mais ne sont pas collectés exhaustivement.",
  'mission.dircom_minarm.label': 'DIRCOM MinArm (planifié)',
  'mission.dircom_minarm.description':
    'Reprise / transformation / déformation des messages officiels DIRCOM sur Telegram.',
  'mission.dircom_minarm.caveat': 'Mission planifiée — non implémentée.',

  // Lentilles de thème (galaxie) — titre + labels par id de thème.
  'graph.themeLens.heading': 'Thèmes (lentilles)',
  'graph.theme.gan': 'Empreinte GAN',
  'graph.theme.france_targeting': 'Ciblage France',
  'graph.theme.francophone': 'Francophone',
  // Scénarios : avertissement méthodologique (indices ≠ preuve d'influence).
  'scenario.warning': 'Ce scénario met en évidence des indices structurels documentés — jamais une preuve d’influence. Interpréter avec les niveaux de preuve.',
  'scenario.warning.gan': 'Empreinte informationnelle sur contenus publics uniquement. Aucun suivi opérationnel ni tactique ; narratifs, pas positions d’unités.',
  'scenario.warning.france_targeting': 'Porosité RU→FR observée sur Telegram : indices de circulation, pas une attribution d’influence directe.',

  // Chips de filtre — crédibilité + libellés d'archétype.
  'graph.cred.suspect': 'suspect',
  'graph.cred.other': 'autre',
  'graph.cred.legit': 'légitime',
  'graph.arch.label.source': "source d'amorçage",
  'graph.arch.label.hub': 'hub de forward',
  'graph.arch.label.bridge': 'pont inter-communautés',
  'graph.arch.label.reactivator': 'réactivateur',

  // Carte empreinte GAN (OPSEC).
  'gan.title': 'Empreinte GAN · OPSEC',
  'gan.channels': '{{n}} canaux',
  'gan.origination': 'origination {{n}}',
  'gan.adverseShare': 'amplif. adverse {{n}} ({{pct}}%)',
  'gan.prose':
    "L'empreinte Telegram du GAN est surtout de la reprise russosphère ({{pct}}%). Objectif OPSEC : la minimiser.",
  'gan.carrierMentions': 'mentions porte-avions',
  'gan.internalLinks': 'liens internes',
  'gan.origHead': 'Origination',
  'gan.advHead': 'Adverse',
  'gan.caveat': "Observable sur Telegram uniquement — jamais l'empreinte totale (cf. Strava).",

  // Commun — libellés partagés multi-écrans.
  'common.loading': 'Chargement…',
} as const

// Ensemble de clés dérivé du dictionnaire source.
export type MessageKey = keyof typeof fr
// Contrat que les autres langues doivent honorer intégralement (aucune clé en moins).
export type Messages = Record<MessageKey, string>
