"""Rubrique EEFI — précision de divulgation pour l'empreinte GAN (cœur PUR).

Gradue la SENSIBILITÉ opérationnelle d'une divulgation observée dans un texte,
selon la rubrique du domaine (``domain-gan-empreinte-informationnelle-2026-06-09``
§3.2 ; cadre OPSEC OTAN AJP-3.10.2 / US NTTP 3-13.3M). Renvoie un score ∈ [0,1]
= **ADI par message** : la sévérité MAXIMALE d'un indicateur EEFI détecté
(position exacte = 1.0 ; zone vague ≈ 0). Injectée dans
``score_telegram_disclosure_precision`` (famille GAN ``telegram_disclosure_precision``).

⚠ Les PONDÉRATIONS de sévérité sont une **décision métier** (calibration MinArm) ;
les valeurs ci-dessous sont une graine v0 alignée sur la rubrique du domaine, à
confirmer/ajuster par la cellule OPSEC. Heuristique transparente (regex repliés
casse+accents), pas de modèle — auditable (NFR-8).

SEVERITY MODULATOR, NEVER A GATE : ne filtre/exclut jamais ; produit un score.
"""
from __future__ import annotations

import re
import unicodedata


def _fold(s: str) -> str:
    nkfd = unicodedata.normalize("NFKD", s or "")
    return "".join(c for c in nkfd if not unicodedata.combining(c)).lower()


# (sévérité, nom, [motifs regex repliés]). Ordonné par sévérité décroissante.
# Domaine §3.2. Motifs volontairement prudents (rappel modéré, précision correcte).
_INDICATORS: list[tuple[float, str, list[str]]] = [
    (1.00, "exact_position", [
        r"\b\d{1,3}[.,]\d{2,}\s*[°o]?\s*[nsew]\b",   # coord décimales + hémisphère
        r"\b\d{1,2}\s*[°o]\s*\d{1,2}['′]",       # deg/min
        r"\bcoordonnees?\b", r"\blat(itude)?\b.*\blong", r"\bgeoloc",
        r"\bgps\b", r"\bposition exacte\b", r"\bточные координаты\b",
    ]),
    (0.95, "course_route", [
        r"\bcap au\b", r"\ben route vers\b", r"\bfait route vers\b",
        r"\bheading (to|toward)\b", r"\bbound for\b", r"\bcourse\b",
        r"\bкурс(ом)? на\b", r"\bнаправляется в\b",
    ]),
    (0.90, "schedule_intent", [
        r"\bappareill", r"\bdepart (le|prevu)", r"\bretour (le|prevu)",
        r"\barrivee prevue\b", r"\bdeploiement (le|du)\b", r"\brentre le\b",
        r"\bdepart(s|ure)? (on|at)\b", r"\bexpected (to arrive|at)\b",
        r"\bотправл", r"\bприбуд", r"\bожидается (прибытие|выход)\b",
    ]),
    (0.88, "escort_composition", [
        r"\bescorte de\b", r"\baccompagne (de|par)\b", r"\bscreen(ed)? by\b",
        r"\bescorted by\b", r"\bcompose de\b.*\b(fregate|destroyer)\b",
        r"\bв сопровождении\b",
    ]),
    (0.85, "readiness_maintenance", [
        r"\ben (maintenance|carenage|cale seche)\b", r"\bindisponib",
        r"\bdrydock\b", r"\brepair(s|ed)?\b", r"\breadiness\b", r"\bна ремонте\b",
    ]),
    (0.82, "next_port", [
        r"\bprochaine escale\b", r"\bfait escale a\b", r"\bnext port\b",
        r"\bport (call|visit) (at|in)\b", r"\bзаход в порт\b",
    ]),
    (0.80, "air_wing_sorties", [
        r"\bsorties? (aerienne|de chasse)\b", r"\bcatapultage", r"\bappontage",
        r"\bsortie rate\b", r"\bflight (ops|schedule)\b", r"\bвылет",
    ]),
    (0.78, "imagery_layout", [
        r"\bphoto (du pont|de la passerelle|des antennes)\b",
        r"\bpont d'envol\b", r"\bflight deck\b", r"\bhull (photo|number)\b",
        r"\bфото (палубы|корабля)\b",
    ]),
    (0.75, "named_personnel", [
        r"\bcommandant (du|de bord)\b", r"\bpacha\b", r"\bcommanding officer\b",
        r"\bcapitaine de vaisseau\b", r"\bcontre-amiral\b", r"\bкомандир корабля\b",
    ]),
]

# Compilation unique (motifs déjà repliés).
_COMPILED: list[tuple[float, str, list[re.Pattern[str]]]] = [
    (sev, name, [re.compile(p, re.UNICODE) for p in pats])
    for sev, name, pats in _INDICATORS
]


def eefi_disclosure_precision(text: str | None, language: str | None = None) -> float:
    """ADI d'un message ∈ [0,1] = sévérité max d'un indicateur EEFI détecté.

    Cross-langue (ne conditionne pas sur ``language``). ``None``/vide -> 0.0.
    """
    if not text:
        return 0.0
    folded = _fold(text)
    best = 0.0
    for sev, _name, patterns in _COMPILED:
        if sev <= best:
            break  # ordonné décroissant : inutile de continuer sous le meilleur
        if any(p.search(folded) for p in patterns):
            best = sev
            break  # le premier (plus sévère) trouvé domine
    return best


def eefi_disclosure_detail(text: str | None, language: str | None = None) -> dict:
    """Variante explicable : { adi, indicators: [noms détectés] } (NFR-8)."""
    if not text:
        return {"adi": 0.0, "indicators": []}
    folded = _fold(text)
    hits: list[str] = []
    adi = 0.0
    for sev, name, patterns in _COMPILED:
        if any(p.search(folded) for p in patterns):
            hits.append(name)
            adi = max(adi, sev)
    return {"adi": round(adi, 4), "indicators": hits}


def null_rubric(text: str | None, language: str | None = None) -> float:
    """Rubrique stub (0.0 partout) — dégradation N/A tant que non calibrée."""
    return 0.0
