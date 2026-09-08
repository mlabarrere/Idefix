"""Histoires ÉDITORIALES de la mission GAN — épisodes documentés hors-base.

Consommées par ``scripts/build_stories.py`` (les handles sont résolus contre le
bundle au build ; les canaux absents de la base marquent l'histoire
``data_status: "partial"`` — honnêteté : la narration est documentée par des
sources ouvertes, les données Telegram correspondantes ne sont pas encore
crawlées).

Sources primaires (recherche 2026-06-10, voir
``_bmad-output/planning-artifacts/research/domain-gan-empreinte-informationnelle-2026-06-09.md``) :
- Fuite Strava : Le Monde 19-20 mars 2026 ; Euronews ; Marine Insight ; rafale
  Pravda (news-pravda.com / france.news-pravda.com) ; commentaire du député
  Zhuravlev via Pravda France (15 avril 2026).
- Drone Zhigulevsk : USNI News 27 fév 2026 ; Defence Express ; couverture
  russosphère même jour (Rybar via SolovievLive).

Périmètre : empreinte OBSERVABLE SUR TELEGRAM, jamais totale — le cas Strava
démontre précisément que la fuite primaire peut naître HORS Telegram, la
russosphère Telegram servant de caisse de résonance.
"""
from __future__ import annotations

EDITORIAL_STORIES: list[dict] = [
    {
        "id": "gan-fuite-strava",
        "title": "GAN — la fuite Strava",
        "subtitle": "Une session de jogging expose le porte-avions ; la russosphère amplifie",
        "data_status": "partial",  # narration documentée, crawl Telegram GAN à venir
        "tier": "T1",
        "phases": [
            {
                "id": "fuite",
                "name": "La fuite",
                "date_label": "13 mars 2026",
                "date_range": ["2026-03-13T00:00:00+00:00", "2026-03-13T23:59:59+00:00"],
                "headline_stat": "coordonnées GPS publiques, ~100 km des côtes turques",
                "narrative": (
                    "Un officier enregistre un jogging sur le pont d'envol du "
                    "Charles de Gaulle en Méditerranée orientale. La session Strava "
                    "est publique : position précise du porte-avions au large de "
                    "Chypre. La fuite primaire naît HORS Telegram — c'est la leçon "
                    "OPSEC centrale de l'épisode."
                ),
                "usernames": [],
                "evidence": [
                    {"kind": "press", "source": "Le Monde",
                     "note": "révélation publique 19-20 mars 2026"},
                ],
            },
            {
                "id": "exposition",
                "name": "L'exposition",
                "date_label": "19–20 mars 2026",
                "date_range": ["2026-03-19T00:00:00+00:00", "2026-03-20T23:59:59+00:00"],
                "headline_stat": "reprise presse internationale en ~24 h",
                "narrative": (
                    "Le Monde publie ; la reprise internationale est immédiate "
                    "(Euronews, TechCrunch, Stars & Stripes…). L'information passe "
                    "du domaine technique (une app de sport) au récit géopolitique."
                ),
                "usernames": ["Mer_et_Marine", "OpexNews", "naval_news"],
                "evidence": [
                    {"kind": "press", "source": "Euronews", "note": "20 mars 2026"},
                ],
            },
            {
                "id": "amplification-adverse",
                "name": "L'amplification adverse",
                "date_label": "20 mars → 15 avr 2026",
                "date_range": ["2026-03-20T00:00:00+00:00", "2026-04-15T23:59:59+00:00"],
                "headline_stat": "5+ articles Pravda · commentaire d'un député russe",
                "narrative": (
                    "Le réseau Pravda publie en rafale (news-pravda.com, "
                    "france.news-pravda.com) ; Rybar contextualise le redéploiement "
                    "du GAN ; le député Zhuravlev commente via Pravda France le "
                    "15 avril. La fuite involontaire devient un actif narratif "
                    "adverse — c'est l'« attention adverse » que la mission mesure."
                ),
                "usernames": ["rybar", "rybar_en", "wargonzo"],
                "evidence": [
                    {"kind": "adversary_domain", "domain": "news-pravda.com",
                     "note": "rafale 19-20 mars 2026"},
                    {"kind": "adversary_domain", "domain": "france.news-pravda.com",
                     "note": "commentaire Zhuravlev, 15 avril 2026"},
                ],
            },
        ],
    },
    {
        "id": "gan-drone-zhigulevsk",
        "title": "GAN — le drone du Zhigulevsk",
        "subtitle": "Reconnaissance physique, caisse de résonance informationnelle",
        "data_status": "partial",
        "tier": "T1",
        "phases": [
            {
                "id": "incident",
                "name": "L'incident",
                "date_label": "26 fév 2026",
                "date_range": ["2026-02-26T00:00:00+00:00", "2026-02-26T23:59:59+00:00"],
                "headline_stat": "drone lancé vers l'ancrage du CdG (Öresund)",
                "narrative": (
                    "Le navire espion russe Zhigulevsk (flotte Baltique) lance un "
                    "drone vers l'ancrage du Charles de Gaulle près de Malmö. Les "
                    "forces suédoises le brouillent et annoncent l'incident le "
                    "lendemain. La reconnaissance physique suit le tracking "
                    "informationnel — les deux couches se nourrissent."
                ),
                "usernames": [],
                "evidence": [
                    {"kind": "press", "source": "USNI News", "note": "27 fév 2026"},
                ],
            },
            {
                "id": "couverture-russosphere",
                "name": "La couverture russosphère",
                "date_label": "27 fév 2026",
                "date_range": ["2026-02-27T00:00:00+00:00", "2026-02-28T23:59:59+00:00"],
                "headline_stat": "résumé vidéo Rybar relayé le jour même",
                "narrative": (
                    "Rybar publie un résumé vidéo spécial relayé via SolovievLive "
                    "le jour même. L'incident militaire devient contenu : la "
                    "russosphère documente, cadre et amplifie sa propre opération "
                    "de reconnaissance."
                ),
                "usernames": ["rybar", "SolovievLive", "wargonzo"],
                "evidence": [
                    {"kind": "press", "source": "Defence Express",
                     "note": "analyse de l'incident"},
                ],
            },
        ],
    },
]
