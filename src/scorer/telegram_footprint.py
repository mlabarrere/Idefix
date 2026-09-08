"""Familles de score « empreinte Telegram » (mission GAN) — cœurs PURS.

Six familles ``telegram_*`` mesurant l'empreinte informationnelle OBSERVABLE SUR
TELEGRAM du GAN (domaine §5.1). Noms ``telegram_*`` = verrou de périmètre : on
mesure l'observable Telegram, JAMAIS l'empreinte totale. Fonctions pures sur le
graphe (mêmes conventions que ``cascade_role`` / ``recidivism``) ; aucune DB sauf
le ``disclosure_precision`` qui consomme des textes fournis par l'enveloppe I/O.

  (visibility)          volume/engagement observable
  (velocity)            rapidité de relais (latence forward)
  (source_diversity)    diversité des canaux émetteurs autour du nœud
  (propagation)         portée (forwards gagnés / fan-out)
  (adverse_attention)   part de l'attention venant de canaux adverses (russosphère)
  (disclosure_precision) précision EEFI de ce qui est divulgué (rubrique injectée)

Chaque scorer renvoie ``{channel_id: ScoreResult}`` (value ∈ [0,1], bande ±0.15,
triggered ≥ 0.3, évidence explicable). MÉTA-CONTRAINTE 1 : modulateurs, jamais
des gates.
"""
from __future__ import annotations

import math
from typing import Callable, Mapping, Sequence

import networkx as nx

from src.shared.dossier import ScoreResult

TRIGGER_THRESHOLD = 0.3
_VELOCITY_REF_SECONDS = 72 * 3600  # latence de saturation (72 h, fenêtre coordination)

# Type de la rubrique EEFI injectée : (text, lang) -> ADI ∈ [0,1].
DisclosurePrecisionRubric = Callable[[str | None, str | None], float]


def _result(family: str, value: float, evidence: dict) -> ScoreResult:
    v = round(max(0.0, min(1.0, value)), 6)
    return ScoreResult(
        family=family,
        value=v,
        confidence_low=round(max(0.0, v - 0.15), 6),
        confidence_high=round(min(1.0, v + 0.15), 6),
        triggered=v >= TRIGGER_THRESHOLD,
        evidence=evidence,
    )


def _sat_log(x: float, ref: float) -> float:
    """Saturation log bornée [0,1] : log1p(x)/log1p(ref)."""
    if ref <= 0:
        return 0.0
    return max(0.0, min(1.0, math.log1p(max(x, 0.0)) / math.log1p(ref)))


def score_telegram_visibility(fwd: nx.DiGraph) -> dict[int, ScoreResult]:
    """Visibilité = engagement observable (vues+forwards agrégés, poids de nœud).

    Normalisée par log-saturation sur le max observé (évite qu'un canal viral
    écrase l'échelle).
    """
    if fwd.number_of_nodes() == 0:
        return {}
    eng = {n: float(fwd.nodes[n].get("engagement") or 0) for n in fwd.nodes}
    max_eng = max(eng.values(), default=0.0)
    out: dict[int, ScoreResult] = {}
    for n, e in eng.items():
        value = _sat_log(e, max_eng) if max_eng > 0 else 0.0
        out[n] = _result(
            "telegram_visibility", value,
            {"engagement": int(e), "engagement_max": int(max_eng)},
        )
    return out


def score_telegram_propagation(fwd: nx.DiGraph) -> dict[int, ScoreResult]:
    """Portée = forwards gagnés (somme des poids d'arêtes SORTANTES, origine->relayeur).

    Cadre « empreinte » de la portée de propagation ; normalisée log-sat sur le max.
    """
    if fwd.number_of_nodes() == 0:
        return {}
    reach = {n: 0.0 for n in fwd.nodes}
    for origin, _relayer, data in fwd.edges(data=True):
        reach[origin] += float(data.get("count") or 1)
    max_reach = max(reach.values(), default=0.0)
    out: dict[int, ScoreResult] = {}
    for n, r in reach.items():
        value = _sat_log(r, max_reach) if max_reach > 0 else 0.0
        out[n] = _result(
            "telegram_propagation", value,
            {"forward_reach": r, "relayers": fwd.out_degree(n), "reach_max": max_reach},
        )
    return out


def score_telegram_source_diversity(fwd: nx.DiGraph) -> dict[int, ScoreResult]:
    """Diversité = nb de partenaires forward DISTINCTS (voisins entrants+sortants).

    Une empreinte portée par de nombreux canaux distincts est plus diffuse/robuste
    qu'un relai unique. Normalisée par le max observé.
    """
    if fwd.number_of_nodes() == 0:
        return {}
    partners: dict[int, int] = {}
    for n in fwd.nodes:
        neigh = set(fwd.successors(n)) | set(fwd.predecessors(n))
        neigh.discard(n)
        partners[n] = len(neigh)
    max_p = max(partners.values(), default=0)
    out: dict[int, ScoreResult] = {}
    for n, p in partners.items():
        value = (p / max_p) if max_p > 0 else 0.0
        out[n] = _result(
            "telegram_source_diversity", value,
            {"distinct_partners": p, "partners_max": max_p},
        )
    return out


def score_telegram_velocity(fwd: nx.DiGraph) -> dict[int, ScoreResult]:
    """Vélocité = rapidité de relais, depuis ``min_delay_s`` des arêtes forward incidentes.

    value = 1 - sat(min_delay) : relai en quelques minutes -> ~1 ; en plusieurs
    jours -> ~0. Canal sans arête forward incidente -> 0 (aucun signal de vélocité).
    """
    if fwd.number_of_nodes() == 0:
        return {}
    out: dict[int, ScoreResult] = {}
    for n in fwd.nodes:
        delays: list[int] = []
        for _u, _v, data in fwd.in_edges(n, data=True):
            d = data.get("min_delay_s")
            if d is not None:
                delays.append(int(d))
        for _u, _v, data in fwd.out_edges(n, data=True):
            d = data.get("min_delay_s")
            if d is not None:
                delays.append(int(d))
        if not delays:
            out[n] = _result("telegram_velocity", 0.0,
                             {"min_delay_s": None, "note": "aucune arête forward incidente"})
            continue
        fastest = min(delays)
        value = 1.0 - _sat_log(fastest, _VELOCITY_REF_SECONDS)
        out[n] = _result(
            "telegram_velocity", value,
            {"min_delay_s": fastest, "ref_seconds": _VELOCITY_REF_SECONDS,
             "incident_forward_edges": len(delays)},
        )
    return out


def score_telegram_adverse_attention(
    fwd: nx.DiGraph,
    adversary_channel_ids: set[int],
) -> dict[int, ScoreResult]:
    """Attention adverse = part des forwards ENTRANTS venant de canaux adverses.

    Pour chaque canal-relayeur/origine, fraction du poids des forwards entrants
    dont l'ORIGINE est dans ``adversary_channel_ids`` (canaux liés à la russosphère
    — alignés sur l'infrastructure adverse). Aucun forward entrant -> 0.
    """
    if fwd.number_of_nodes() == 0:
        return {}
    adv = adversary_channel_ids or set()
    out: dict[int, ScoreResult] = {}
    for n in fwd.nodes:
        total = 0.0
        adverse = 0.0
        for origin, _relayer, data in fwd.in_edges(n, data=True):
            w = float(data.get("count") or 1)
            total += w
            if origin in adv:
                adverse += w
        value = (adverse / total) if total > 0 else 0.0
        out[n] = _result(
            "telegram_adverse_attention", value,
            {"adverse_inbound_weight": adverse, "total_inbound_weight": total,
             "adversary_partners": sum(1 for o, _r, _d in fwd.in_edges(n, data=True) if o in adv)},
        )
    return out


def score_telegram_disclosure_precision(
    messages_by_channel: Mapping[int, Sequence[tuple[str | None, str | None]]],
    rubric: DisclosurePrecisionRubric,
) -> dict[int, ScoreResult]:
    """Précision de divulgation EEFI par canal (rubrique INJECTÉE).

    Agrégation **max-avec-couverture** (cf. ``targeting.aggregate_channel``) : le
    score canal = ADI max d'un message (un canal qui divulgue une fois précisément
    fait surface) ; l'évidence porte couverture + moyenne. La rubrique
    (sévérités EEFI) est une décision métier (calibration MinArm) — injectée, pas
    codée en dur ici.
    """
    out: dict[int, ScoreResult] = {}
    for cid, messages in messages_by_channel.items():
        if not messages:
            out[cid] = _result("telegram_disclosure_precision", 0.0,
                               {"messages_sampled": 0, "coverage": 0.0, "mean_adi": 0.0})
            continue
        adis = [float(rubric(t, lang)) for t, lang in messages]
        n = len(adis)
        hits = sum(1 for a in adis if a > 0.0)
        max_adi = max(adis)
        out[cid] = _result(
            "telegram_disclosure_precision", max_adi,
            {"messages_sampled": n, "coverage": round(hits / n, 4),
             "mean_adi": round(sum(adis) / n, 4), "max_adi": round(max_adi, 4)},
        )
    return out
