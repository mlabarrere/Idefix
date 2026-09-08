"""Lexique d'entités du Groupe Aéronaval (GAN / *Charles de Gaulle*) — multilingue.

Pilote le moteur générique ``src/normalizer/targeting.py`` (aucun code de matching
ici — uniquement des DONNÉES). Conçu pour détecter le GAN **même quand « GAN »
n'est pas écrit**, via 4 niveaux (domaine §5.2) :

  1. **directe** — ancre exacte (``charles de gaulle``, ``r91``, RU ``шарль де голль``).
  2. **paraphrastique** — fuzzy + embeddings BGE-M3 (seam ``claim_proximity``, v0 N/A).
  3. **indice contextuel faible** — terme générique (``porte-avions`` / ``авианосец`` /
     ``frégate``) compté UNIQUEMENT avec une ancre présente (gate contextuel du moteur).
  4. **cooccurrence → mention implicite** — capté par la LARGEUR multi-catégories :
     p. ex. ``porte-avions français`` (ancre) + ``toulon`` (ancre) + ``escorte``
     (contextuel) couvre plusieurs catégories ⇒ score élevé sans nommer le navire.

ANCRES vs CONTEXTUELS (même discipline que ``FRANCE_LEXICON``) :
  * ANCRES = sans ambiguïté liées au GAN FRANÇAIS (``charles de gaulle``,
    ``groupe aéronaval``, ``marine nationale``, ``porte-avions français``,
    ``clemenceau 25``, ``toulon`` = port-base, formes d'escorte multi-mots).
  * CONTEXTUELS = vocabulaire générique (``porte-avions``, ``aircraft carrier``,
    ``frégate``, ``suez``, sigles ambigus ``gan``/``csg``/``cvbg`` — GAN est aussi
    un assureur / « Generative Adversarial Network », CSG une taxe / le Centre
    spatial guyanais) → comptés seulement en présence d'une ancre.

Chaque terme contextuel DOIT aussi figurer dans une catégorie (pour avoir un
pattern) ET dans ``GAN_CONTEXTUAL_TERMS`` (pour être classé contextuel).
TODO(analyst): graine PoC à curer/étendre (formes RU/translittérations utilisées
par les canaux OSINT/milbloggers).
"""
from __future__ import annotations

from src.scorer.channel_suspicion import ADVERSARY_DOMAINS as _RUSSO_ADVERSARY_DOMAINS

GAN_LEXICON: dict[str, list[str]] = {
    # Le navire, nommé — ancres fortes + contextuels « porte-avions » génériques.
    "carrier_named": [
        # ANCRES
        "charles de gaulle", "charles-de-gaulle", "porte-avions charles de gaulle",
        "le charles de gaulle", "r91", "fs charles de gaulle", "pa charles de gaulle",
        "french aircraft carrier", "porte-avions français", "porte-avion français",
        "шарль де голль", "шарль-де-голль", "авианосец шарль де голль", "р91",
        # CONTEXTUELS (génériques — porte-avions de n'importe quel pays)
        "porte-avions", "porte-avion", "aircraft carrier", "carrier", "авианосец",
        "ядерный авианосец", "nuclear aircraft carrier",
    ],
    # Le groupe aéronaval comme formation — ancres + sigles ambigus contextuels.
    "carrier_group": [
        # ANCRES
        "groupe aéronaval", "carrier strike group", "carrier vessel battle group",
        "french carrier group", "french carrier strike group", "groupe aeronaval",
        "французская авианосная группа", "авианосная группа",
        # CONTEXTUELS (sigles/locutions ambigus)
        "gan", "csg", "cvbg", "naval task force", "task group", "ударная группа",
    ],
    # Escorte — formes multi-mots ancres ; noms nus / génériques contextuels.
    "escort": [
        # ANCRES (formes désambiguïsées)
        "frégate forbin", "fs forbin", "frégate provence", "fs provence",
        "frégate alsace", "fs alsace", "jacques chevallier", "fs jacques chevallier",
        # CONTEXTUELS (génériques / noms nus ambigus : provence/alsace = régions)
        "frégate", "fregate", "escorte", "escorteur", "destroyer", "forbin",
        "bâtiments accompagnateurs", "фрегат", "эсминец",
    ],
    # Groupe aérien embarqué — ancres spécifiques ; aéronefs génériques contextuels.
    "air_wing": [
        # ANCRES
        "rafale marine", "groupe aérien embarqué", "e-2c hawkeye",
        # CONTEXTUELS
        "rafale", "hawkeye", "flottille", "gae", "рафаль", "хокай",
    ],
    # Marine française — ancres (mention de la marine FR = pertinente à l'empreinte).
    "french_navy": [
        "marine nationale", "french navy", "flotte française", "marine française",
        "вмс франции", "французский флот", "военно-морской флот франции",
    ],
    # Déploiements / port-base — ancres spécifiques ; géographie générique contextuelle.
    "deployment": [
        # ANCRES
        "clemenceau 25", "mission clemenceau", "toulon", "тулон",
        # exercices distinctifs impliquant le GAN (recherche 2026-06-10)
        "varuna", "pacific steller",
        # CONTEXTUELS (géographie générique)
        "escale", "méditerranée orientale", "mer rouge", "suez", "détroit",
        "средиземное море", "суэцкий канал", "красное море",
    ],
    # Incidents / vecteurs d'exposition documentés (recherche 2026-06-10) :
    # le navire espion Zhigulevsk (drone vers l'ancrage du CdG, fév 2026) et la
    # fuite Strava (mars 2026). « strava » est CONTEXTUEL (app de sport générique,
    # compté seulement avec une ancre GAN présente) ; le nom du navire est une ancre.
    "incidents": [
        # ANCRES
        "zhigulevsk", "жигулевск",
        # CONTEXTUELS
        "strava", "navire espion", "разведывательный корабль",
    ],
}

# Termes génériques comptés UNIQUEMENT en présence d'une ancre (gate contextuel).
# Chacun figure verbatim dans une catégorie ci-dessus.
GAN_CONTEXTUAL_TERMS: frozenset[str] = frozenset(
    {
        "porte-avions", "porte-avion", "aircraft carrier", "carrier", "авианосец",
        "ядерный авианосец", "nuclear aircraft carrier",
        "gan", "csg", "cvbg", "naval task force", "task group", "ударная группа",
        "frégate", "fregate", "escorte", "escorteur", "destroyer", "forbin",
        "bâtiments accompagnateurs", "фрегат", "эсминец",
        "rafale", "hawkeye", "flottille", "gae", "рафаль", "хокай",
        "escale", "méditerranée orientale", "mer rouge", "suez", "détroit",
        "средиземное море", "суэцкий канал", "красное море",
        "strava", "navire espion", "разведывательный корабль",
    }
)

# Couche « attention adverse » = la russosphère (même appareil OSINT/milblogger
# qui surveille les déploiements). On réutilise donc les domaines adverses
# documentés du projet plutôt que d'en inventer de spécifiques au GAN.
GAN_ADVERSARY_DOMAINS: frozenset[str] = _RUSSO_ADVERSARY_DOMAINS
