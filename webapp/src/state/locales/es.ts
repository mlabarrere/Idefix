// Dictionnaire espagnol (español). Typé contre `Messages` :
// toute clé manquante par rapport à fr.ts échoue au typecheck.
import type { Messages } from './fr'

export const es: Messages = {
  // Switcher de langue (endónimos, idénticos en los tres diccionarios).
  'lang.fr': 'Français',
  'lang.en': 'English',
  'lang.es': 'Español',
  'lang.nl': 'Nederlands',
  'lang.lb': 'Lëtzebuergesch',
  'lang.de': 'Deutsch',
  'lang.switcherAria': 'Elegir idioma',

  // Firma del autor (§15.4) — el rol se traduce, el nombre no.
  'signature.role': 'Analista OSINT',

  // Verrou d'accès (puerta de acceso).
  'gate.title': 'Idéfix — acceso restringido',
  'gate.subtitle': 'Introduzca la contraseña para acceder a la interfaz del analista.',
  'gate.passwordLabel': 'Contraseña',
  'gate.unlock': 'Desbloquear',
  'gate.checking': 'Verificando…',
  'gate.wrong': 'Contraseña incorrecta.',
  'gate.disclaimer':
    'Solo bloquea la interfaz. Los datos se siguen sirviendo de forma estática: no lo considere un control de acceso robusto.',

  // Navegación.
  'nav.synthese': 'Resumen',
  'nav.galaxie': 'Galaxia',
  'nav.analyse': 'Análisis',
  'nav.channels': 'Canales',
  'nav.methodologie': 'Metodología',
  'nav.mission': 'Misión',
  'nav.settings': 'Ajustes',
  'nav.statusSoon': 'próximamente',
  'nav.statusPlanned': 'planificada',
  'nav.emptySoon': 'Datos próximamente para esta misión: el paquete aún no se ha generado.',
  'nav.emptyPlanned': 'Misión planificada: no implementada.',

  // Cartera de misiones.
  'missions.intro':
    'Plataforma de análisis de propagación y coordinación en Telegram. Elija una misión: cada una es un perímetro analítico, con su cobertura y sus límites.',
  'missions.statusActive': 'activa',
  'missions.statusSoon': 'datos próximamente',
  'missions.statusPlanned': 'planificada',

  // Síntesis de misión.
  'overview.emptyTitle': 'No hay datos para esta misión.',
  'overview.emptyHint': 'Genere el paquete: python scripts/export_static.py --mission {{missionId}}',
  'overview.dataHealth': 'Estado de los datos',
  'overview.keyFigures': 'Cifras clave',
  'overview.topSuspect': 'Canales más sospechosos',
  'overview.generated': 'generado {{date}}',
  'overview.bundlePartial': 'paquete parcial (público)',
  'overview.bundleComplete': 'paquete completo',
  'overview.statChannels': 'Canales',
  'overview.statEdges': 'Aristas',
  'overview.statMessages': 'Mensajes',
  'overview.statCommunities': 'Comunidades',
  'overview.hintModularity': 'modularidad {{value}}',
  'overview.statT2': 'Canales T2',
  'overview.hintT2': 'corroborados (≥2 familias)',
  'overview.statTotal': 'Total de canales',
  'overview.statDensity': 'Densidad',
  'overview.hintDensity': 'aristas / nodo',
  'overview.linkGalaxieDesc': 'Explorar el grafo interactivo',
  'overview.linkChannelsDesc': 'Tabla analítica completa',
  'overview.caveatFallback':
    'Cobertura solo de Telegram: la capa de amplificación masiva no se observa.',

  // Tabla de canales.
  'channels.title': 'Todos los canales',
  'channels.count': '{{n}} canales',
  'channels.searchPlaceholder': 'Filtrar (handle / título)…',
  'channels.colCanal': 'Canal',
  'channels.colSuspicion': 'Sospecha',
  'channels.colTier': 'Nivel',
  'channels.colArchetype': 'Arquetipo',
  'channels.colCiblage': 'Segmentación',
  'channels.colGate': 'Gate',
  'channels.emptyIndex': 'No hay índice de canales para esta misión.',
  'channels.emptyMatch': 'Ningún canal coincide.',

  // Pantalla de ajustes.
  'settings.title': 'Ajustes',
  'settings.subtitle': 'Preferencias de visualización: se aplican localmente a este navegador.',
  'settings.themeLabel': 'Tema',
  'settings.themeHint': 'Interfaz clara u oscura.',
  'settings.langLabel': 'Idioma',
  'settings.langHint': 'Idioma de la interfaz.',
  'settings.communityLabel': 'Vista de comunidades',
  'settings.communityHint':
    'Agrupación de la galaxia: estructural (Analytics) o semántica (LLM Embedding).',

  // Página de metodología (in-app).
  'methodology.title': 'Metodología',
  'methodology.secBrief': 'Idéfix, en resumen',
  'methodology.secCoverage': 'Cobertura y límites',
  'methodology.secPipeline': 'El pipeline, de principio a fin',
  'methodology.secScore': 'La puntuación de sospecha',
  'methodology.secTiers': 'Niveles de atribución',
  'methodology.secCommunities': 'Comunidades: analytics vs embeddings',
  'methodology.secValidation': 'Estado de validación (honesto)',
  'methodology.secGovernance': 'Gobernanza y ética',
  'methodology.step1': 'Recopilación',
  'methodology.step2': 'Construcción del grafo',
  'methodology.step3': 'Puntuación de sospecha',
  'methodology.step4': 'Descubrimiento de episodios',
  'methodology.step5': 'Comunidades',
  'methodology.step6': 'Exportación',
  'methodology.step7': 'Almacenamiento',
  'methodology.step8': 'Compilación y difusión',

  // Cambio de tema.
  'theme.toLight': 'Cambiar a claro',
  'theme.toDark': 'Cambiar a oscuro',
  'theme.toggleAria': 'Cambiar el tema',

  // Barra narrativa (StoryBar).
  'story.heading': 'Historias',
  'story.selectedPrefix': 'Historia: {{title}}',
  'story.pickerButton': 'Historias ▾',
  'story.exit': '✕ Salir de la historia — volver a la galaxia libre',
  'story.statusDerived': 'reconstruida a partir de datos',
  'story.statusEditorial': 'editorial (fuentes abiertas)',
  'story.statusPartial': 'datos parciales',
  'story.uncrawledChannels': 'canales no rastreados: {{list}}',
  'story.noTelegramData':
    'no hay datos de Telegram en el paquete para esta fase — narración documentada con fuentes abiertas',


  // Galaxia (GalaxyCanvas) — cabina, leyenda, filtros, cambio de vista + tooltips de Cytoscape.
  'graph.view.label': 'Vista',
  'graph.view.galaxy': 'Galaxia',
  'graph.view.compound': 'Compound',
  'graph.search.label': 'Búsqueda',
  'graph.search.placeholder': 'Buscar un canal…',
  'graph.filter.heading': 'Filtros',
  'graph.filter.reset': 'restablecer',
  'graph.filter.nodeType': 'Tipo de nodo',
  'graph.filter.channels': 'canales',
  'graph.filter.domains': 'sitios web',
  'graph.filter.credibility': 'Credibilidad',
  'graph.filter.archetype': 'Arquetipo',
  'graph.filter.domCategory': 'Categoría de sitio',
  'graph.filter.dom.adversary': 'infra adversa',
  'graph.filter.dom.social': 'red social',
  'graph.filter.dom.video': 'vídeo',
  'graph.filter.dom.news': 'prensa / medios',
  'graph.filter.dom.gov': 'institucional',
  'graph.filter.dom.other': 'otro',
  'graph.spheres.heading': 'Esferas',
  'graph.spheres.open': '{{n}} abierta(s)',
  'graph.recenter': '⊙ recentrar',
  'graph.recenterTitle': 'Recentrar la galaxia',
  'graph.emptyTitle': 'No hay instantánea de comunidades para esta misión.',
  'graph.emptyHint':
    'Genere: python scripts/analyze_communities.py --mission {{missionId}}, luego vuelva a exportar el paquete.',
  'graph.tooltip.commStats': '{{count}} canales · {{susp}} sospechoso(s) · {{ndom}} dominio(s)',
  'graph.tooltip.clicBloom': 'clic → expandir',
  'graph.tooltip.hiddenChannels': '{{hidden}} canal(es) oculto(s) · presupuesto de rendimiento',
  'graph.tooltip.credibility': 'credibilidad: {{cred}} · {{arch}}',
  'graph.tooltip.broker': 'intermediario (puente)',
  'graph.tooltip.clicDossier': 'clic → expediente',
  'graph.tooltip.domain': 'sitio web · {{cat}}',
  'graph.tooltip.citedBy': 'citado por {{n}} canal(es)',
  'graph.tooltip.clicCiters': 'clic → canales citadores',
  'graph.tooltip.arcTitle': 'Puente entre comunidades',
  'graph.tooltip.arcEdges': '{{n}} aristas',
  'graph.arch.seeding-source':
    'siembra recurrentemente una narrativa antes del fan-out — objetivo de alerta temprana.',
  'graph.arch.forward-hub': 'contenido ampliamente reenviado (fuerte fan-out de nivel 1).',
  'graph.arch.cross-channel-bridge':
    'hace circular la narrativa entre comunidades compartimentadas — a menudo más peligroso que el mayor difusor.',
  'graph.arch.reactivator': 'reinyecta periódicamente una vieja narrativa en nuevas discusiones.',
  'graph.score.a': 'Proximidad a una afirmación ya conocida (BGE-M3). No cableado en v0.',
  'graph.score.b':
    'Papel en la propagación (Bridge Score): fuente de siembra / hub / puente entre comunidades / reactivador.',
  'graph.score.c':
    'Comportamiento coordinado (D3lta): mismos textos, republicaciones sincronizadas en una ventana Δt, cocitas — más allá del azar.',
  'graph.score.d': 'Reincidencia entre episodios: forward-influence + recurrencia del canal de siembra.',
  'graph.score.e': 'Probabilidad de origen IA (texto/audio/vídeo). No cableado en v0.',
  'graph.score.f':
    'Coherencia semántica (embedding): distancia a la línea base FR orgánica + proximidad a canales adversarios conocidos.',
  'graph.score.telegram_visibility': 'Volumen/engagement observable del canal.',
  'graph.score.telegram_velocity': 'Rapidez de retransmisión (latencia de reenvío).',
  'graph.score.telegram_source_diversity': 'Diversidad de canales emisores alrededor del nodo.',
  'graph.score.telegram_disclosure_precision':
    'Precisión EEFI de lo divulgado (posición, escolta, calendario…).',
  'graph.score.telegram_propagation': 'Alcance (reenvíos ganados / fan-out).',
  'graph.score.telegram_adverse_attention': 'Parte de la atención proveniente de canales adversarios (rusosfera).',

  // Panel de canal (ChannelDrawer) — solo chrome.
  'drawer.notInIndex': 'Canal ausente del índice de puntuación.',
  'drawer.openTelegram': 'Abrir en Telegram',
  'drawer.close': 'Cerrar',
  'drawer.tierT1': 'difusión observable',
  'drawer.tierT2': 'recurrencia comportamental',
  'drawer.whyArchetype': 'Por qué este arquetipo:',
  'drawer.inNarrative': 'En el relato — ',
  'drawer.gateMet': '✓ Corroborado por varias señales',
  'drawer.gateUnmet': '✗ Corroboración insuficiente',
  'drawer.gateMetDetail': 'al menos dos familias de señal concuerdan (regla anti-falsos-positivos).',
  'drawer.gateUnmetDetail': 'un solo tipo de señal por ahora: a confirmar antes de concluir.',
  'drawer.fiveFamilies': 'Cinco familias de señal',
  'drawer.definition': 'Definición — ',
  'drawer.naV0': 'N/A v0',
  'drawer.calcTitle': 'Detalle del cálculo — por qué esta puntuación',
  'drawer.calcRow': '{{k}} : peso {{weight}} × val {{value}}',
  'drawer.calcBase': 'base (renormalizada)',
  'drawer.boostReforward': 'boost rereenvío-sospechoso',
  'drawer.boostAdversary': 'boost dominio adverso ({{n}})',
  'drawer.boostTargeting': 'boost segmentación',
  'drawer.severityFactor': 'factor de severidad',
  'drawer.combinedSuspicion': 'sospecha combinada',
  'drawer.calcFormula':
    'base = Σ(peso × valor de las familias activadas) renormalizada, luego × factor de severidad (acotado), acotado a [0,1].',
  'drawer.noFamilyTriggered': 'Ninguna familia activada.',
  'drawer.semanticTitle': 'Coherencia semántica — proximidad de embedding',
  'drawer.baselineDistance': 'Distancia a la línea base FR orgánica',
  'drawer.baselineScale': '0 = idéntico a medios FR, 1 = opuesto',
  'drawer.similarChannels': 'Canales semánticamente similares (top 3)',
  'drawer.commenters': 'Comentaristas del grupo vinculado —',
  'drawer.commentersCount': '{{n}} para {{m}} mensajes',
  'drawer.commentersNote':
    'Engagement observable del grupo de discusión vinculado. El grafo sigue siendo canal-céntrico — esto no es una modelización de los usuarios.',
  'drawer.interactions': 'Interacciones — quién hace qué',
  'drawer.relaysFrom': 'Retransmite el contenido de',
  'drawer.relayedBy': 'Retransmitido por',
  'drawer.coordinatedWith': 'Coordinado con',
  'drawer.citesDomains': 'Cita los dominios',

  // Misiones (etiquetas, descripciones, advertencias).
  'mission.russosphere.label': 'Rusosfera → extrema derecha FR',
  'mission.russosphere.description':
    'Desinformación coordinada dirigida contra la imagen, la integridad o la soberanía de Francia.',
  'mission.russosphere.caveat':
    'Cobertura solo de Telegram — la capa de amplificación masiva (X / otras plataformas) no se observa.',
  'mission.gan.label': 'GAN — huella informacional',
  'mission.gan.description':
    'Huella observable en Telegram del grupo aeronaval (Charles de Gaulle) — objetivo OPSEC de minimización + atención adversaria.',
  'mission.gan.caveat':
    'Huella OBSERVABLE EN TELEGRAM únicamente — no la huella total. AIS / Strava / X / prensa / satélite pueden alimentar Telegram pero no se recopilan exhaustivamente.',
  'mission.dircom_minarm.label': 'DIRCOM MinArm (planificado)',
  'mission.dircom_minarm.description':
    'Reutilización / transformación / distorsión de los mensajes oficiales DIRCOM en Telegram.',
  'mission.dircom_minarm.caveat': 'Misión planificada — no implementada.',

  // Temas y lentes del grafo.
  'graph.themeLens.heading': 'Temas (lentes)',
  'graph.theme.gan': 'Huella GAN',
  'graph.theme.france_targeting': 'Focalización Francia',
  'graph.theme.francophone': 'Francófono',
  // Escenarios: advertencia metodológica (indicios ≠ prueba de influencia).
  'scenario.warning': 'Este escenario resalta indicios estructurales documentados, nunca una prueba de influencia. Interpretar junto a los niveles de evidencia.',
  'scenario.warning.gan': 'Huella informacional solo sobre contenidos públicos. Sin seguimiento operativo ni táctico; narrativas, no posiciones de unidades.',
  'scenario.warning.france_targeting': 'Porosidad RU→FR observada en Telegram: indicios de circulación, no una atribución de influencia directa.',
  'graph.cred.suspect': 'sospechoso',
  'graph.cred.other': 'otro',
  'graph.cred.legit': 'legítimo',
  'graph.arch.label.source': 'fuente de siembra',
  'graph.arch.label.hub': 'hub de reenvío',
  'graph.arch.label.bridge': 'puente entre comunidades',
  'graph.arch.label.reactivator': 'reactivador',

  // Panel GAN · OPSEC.
  'gan.title': 'Huella GAN · OPSEC',
  'gan.channels': '{{n}} canales',
  'gan.origination': 'originación {{n}}',
  'gan.adverseShare': 'amplif. adversaria {{n}} ({{pct}}%)',
  'gan.prose':
    'La huella en Telegram del GAN es sobre todo reutilización de la rusosfera ({{pct}}%). Objetivo OPSEC: minimizarla.',
  'gan.carrierMentions': 'menciones del portaaviones',
  'gan.internalLinks': 'enlaces internos',
  'gan.origHead': 'Originación',
  'gan.advHead': 'Adverso',
  'gan.caveat': 'Observable solo en Telegram — nunca la huella total (cf. Strava).',

  // Compartido.
  'common.loading': 'Cargando…',
}
