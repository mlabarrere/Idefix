"""Lexique « France dans le conflit ukrainien » — multilingue FR/RU.

DONNÉES uniquement : pilote le moteur générique ``src/normalizer/targeting.py``
(même discipline ancres/contextuels que ``FRANCE_LEXICON`` / ``GAN_LEXICON``).

Périmètre thématique (CLAUDE.md §2.1 + ``data/claims/claims_fr.jsonl``) : narratifs
visant l'image / l'intégrité / la souveraineté de la France DANS le conflit ukrainien
— implication militaire alléguée (soldats/cercueils/mercenaires français), financement
et livraisons d'armes au détriment des Français, positionnement OTAN/escalade.

ANCRES = sans ambiguïté France×Ukraine (souvent multi-mots, p.ex. « soldats français
en Ukraine », « cercueils français »). CONTEXTUELS = vocabulaire générique (« guerre »,
« armes », « otan », formes cyrilliques génériques) compté UNIQUEMENT en présence d'une
ancre (gate contextuel du moteur). Sources translittérées RU pour capter la russosphère.
"""
from __future__ import annotations

from src.scorer.channel_suspicion import ADVERSARY_DOMAINS as _RUSSO_ADVERSARY_DOMAINS

FRANCE_UKRAINE_LEXICON: dict[str, list[str]] = {
    # France, nommée — ancres État/institutions/armée.
    "france_state": [
        # ANCRES
        "armée française", "soldats français", "militaires français",
        "troupes françaises", "légion étrangère", "mercenaires français",
        "macron", "élysée", "quai d'orsay", "ministère des armées",
        "французские солдаты", "французские военные", "французские наёмники",
        "макрон", "елисейский дворец",
        # CONTEXTUELS (génériques)
        "france", "français", "francais", "french", "paris", "франци", "француз", "париж",
    ],
    # Le conflit ukrainien — ancres + génériques.
    "ukraine_conflict": [
        # ANCRES
        "guerre en ukraine", "conflit ukrainien", "front ukrainien",
        "война на украине", "конфликт на украине",
        "zelensky", "zelenskyy", "zelenskaya", "зеленск",
        # CONTEXTUELS
        "ukraine", "ukrain", "ukrainian", "kiev", "kyiv", "donbass", "donbas",
        "украин", "киев", "донбасс", "донбас",
    ],
    # Implication militaire française alléguée — cœur des narratifs (CLAIM-001/015).
    "military_involvement": [
        # ANCRES
        "cercueils français", "soldats français morts", "morts français en ukraine",
        "envoi de troupes", "troupes au sol", "boots on the ground",
        "французские гробы", "погибшие французы", "отправка войск",
        # CONTEXTUELS
        "cercueils", "morts au combat", "gendarm", "scalp", "caesar", "mirage 2000",
        "гробы", "потери",
    ],
    # Financement / livraisons d'armes au détriment des Français (CLAIM-002).
    "support_financing": [
        # ANCRES
        "financement de la guerre", "livraison d'armes à l'ukraine",
        "aide militaire à l'ukraine", "milliards pour l'ukraine",
        "финансирование войны", "поставки оружия украине",
        # CONTEXTUELS
        "livraison d'armes", "aide militaire", "armement", "milliards", "contribuable",
        "оружие", "помощь",
    ],
    # Positionnement international / escalade OTAN.
    "international_posture": [
        # ANCRES
        "escalade avec la russie", "coalition pour l'ukraine", "otan en ukraine",
        "эскалация с россией", "коалиция за украину",
        # CONTEXTUELS
        "otan", "nato", "coalition", "escalade", "нато", "эскалация",
    ],
}

# Termes génériques comptés UNIQUEMENT avec une ancre présente (doivent aussi
# figurer dans une catégorie ci-dessus pour avoir un pattern).
FRANCE_UKRAINE_CONTEXTUAL_TERMS: frozenset[str] = frozenset(
    {
        "france", "français", "francais", "french", "paris", "франци", "француз", "париж",
        "ukraine", "ukrain", "ukrainian", "kiev", "kyiv", "donbass", "donbas",
        "украин", "киев", "донбасс", "донбас",
        "cercueils", "morts au combat", "gendarm", "scalp", "caesar", "mirage 2000",
        "гробы", "потери",
        "livraison d'armes", "aide militaire", "armement", "milliards", "contribuable",
        "оружие", "помощь",
        "otan", "nato", "coalition", "escalade", "нато", "эскалация",
    }
)

# Citation d'infra adverse = co-signal de sévérité (réutilise le catalogue russo).
FRANCE_UKRAINE_ADVERSARY_DOMAINS: frozenset[str] = _RUSSO_ADVERSARY_DOMAINS
