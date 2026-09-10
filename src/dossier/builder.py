"""
Dossier builder — packages scorer output into a validated JSON evidence dossier.

Every dossier must pass DossierSchema validation (Pydantic) before being
persisted. The schema enforces:
  - attribution_tier: T1|T2 only (T3 raises ValidationError)
  - coverage_callout: non-empty (the single-platform-blindness caveat)
  - methodology_version_hash: from METHODOLOGY.md SHA-256

PoC v0: writes JSON files under data/dossiers/; DB write deferred to v1.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal, cast

import structlog

from src.scorer.base import ScoreSummary
from src.shared.dossier import (
    COVERAGE_CALLOUT_FR,
    DossierSchema,
    EvidenceChannel,
    ScoreResult,
    get_methodology_version_hash,
    new_dossier_id,
    now_utc,
)

log = structlog.get_logger(__name__)

# Alias des Literal du schéma : les gardes de ``_internal_role`` et l'échelle
# produite par ``overall_severity`` donnent exactement ces valeurs, donc les
# signatures doivent le dire plutôt que de renvoyer ``str``.
CascadeRoleLiteral = Literal[
    "seeding-source", "forward-hub", "cross-channel-bridge", "reactivator"
]
SeverityTierLiteral = Literal["T1", "T2", "T3", "T4", "T5"]
_VALID_CASCADE_ROLES: frozenset[str] = frozenset(
    {"seeding-source", "forward-hub", "cross-channel-bridge", "reactivator"}
)

DOSSIERS_DIR = Path(__file__).parent.parent.parent / "data" / "dossiers"


@dataclass
class DossierOutput:
    dossier_id: str
    json_path: Path
    schema: DossierSchema


def build_dossier(
    episode_id: str,
    scores: ScoreSummary,
    evidence_channels: list[dict] | None = None,
    attribution_tier: Literal["T1", "T2"] = "T1",
) -> DossierOutput:
    """
    Build and persist a validated evidence dossier.

    Args:
        episode_id: The registered claim/episode identifier.
        scores: Output from score_channel().
        evidence_channels: Optional list of channel dicts with role annotations.
        attribution_tier: "T1" (observable diffusion) or "T2" (behavioral recurrence).

    Returns:
        DossierOutput with the dossier_id, output path, and validated schema.
    """
    dossier_id = new_dossier_id()

    # Build ScoreResult list from ScoreSummary
    score_results = [
        ScoreResult(
            family="claim_proximity",
            value=scores.claim_proximity,
            confidence_low=max(0.0, scores.claim_proximity - 0.1),
            confidence_high=min(1.0, scores.claim_proximity + 0.1),
            triggered=scores.claim_proximity >= 0.3,
        ),
        ScoreResult(
            family="cascade_role",
            value=scores.cascade_role,
            confidence_low=max(0.0, scores.cascade_role - 0.1),
            confidence_high=min(1.0, scores.cascade_role + 0.1),
            triggered=scores.cascade_role >= 0.3,
            evidence={"note": "Bridge Score stub — v0"},
        ),
        ScoreResult(
            family="coordination",
            value=scores.coordination,
            confidence_low=0.0,
            confidence_high=0.0,
            triggered=False,
            evidence={"note": "D3lta stub — v0"},
        ),
        ScoreResult(
            family="recidivism",
            value=scores.recidivism,
            confidence_low=0.0,
            confidence_high=0.0,
            triggered=False,
            evidence={"note": "Cross-episode recidivism stub — v0"},
        ),
        ScoreResult(
            family="genai",
            value=scores.genai_probability,
            confidence_low=0.0,
            confidence_high=0.0,
            triggered=False,
            evidence={"note": "GenAI-origin stub — v0"},
        ),
    ]

    # Build EvidenceChannel list
    ev_channels = []
    for ch in (evidence_channels or []):
        ev_channels.append(
            EvidenceChannel(
                channel_id=ch.get("channel_id", 0),
                username=ch.get("username"),
                cascade_role=ch.get("cascade_role"),
                bridge_score=ch.get("bridge_score"),
            )
        )

    schema = DossierSchema(
        dossier_id=dossier_id,
        episode_id=episode_id,
        attribution_tier=attribution_tier,
        # ``overall_severity`` renvoie ``str`` ; l'échelle T1..T5 qu'il produit est
        # exactement le Literal du schéma (src/scorer/base.py::overall_severity).
        severity_tier=cast("SeverityTierLiteral", scores.overall_severity),
        methodology_version_hash=get_methodology_version_hash(),
        created_at=now_utc(),
        multi_source_rule_met=scores.multi_source_rule_met,
        scores=score_results,
        evidence_channels=ev_channels,
        coverage_callout=COVERAGE_CALLOUT_FR,
    )

    # Persist as JSON
    DOSSIERS_DIR.mkdir(parents=True, exist_ok=True)
    json_path = DOSSIERS_DIR / f"{dossier_id}.json"
    json_path.write_text(schema.model_dump_json(indent=2), encoding="utf-8")

    log.info(
        "dossier_built",
        dossier_id=dossier_id,
        episode_id=episode_id,
        attribution_tier=attribution_tier,
        severity_tier=schema.severity_tier,
        multi_source_rule_met=schema.multi_source_rule_met,
        path=str(json_path),
    )

    return DossierOutput(dossier_id=dossier_id, json_path=json_path, schema=schema)


# --------------------------------------------------------------------------- #
# Frontend-contract dossier (consommé par frontend/console-operateur.html)    #
# --------------------------------------------------------------------------- #
#
# La console opérateur consomme un objet d'EPISODES[] avec un schéma propre
# (scores a..e avec couleurs, channels_detail, timeline 24 buckets). On le
# construit ICI à partir des ScoreResult réels des familles b/c/d, tout en
# faisant transiter la garde institutionnelle :
#   - attribution_tier limité à T1/T2 (DossierSchema valide -> ValidationError
#     si on tente T3) ;
#   - COVERAGE_CALLOUT_FR injecté (single-platform-blindness) ;
#   - règle multi-source (>=3 signaux de >=2 familles) recalculée sur les
#     scores réels du cluster.

# Couleurs imposées par le contrat frontend (une par famille).
_FAMILY_COLORS = {
    "a": "#3B82F6",  # claim_proximity
    "b": "#F0B429",  # cascade_role
    "c": "#22c55e",  # coordination
    "d": "#ef4444",  # recidivism
    "e": "#a78bfa",  # genai
}

# Mapping archétype interne (cascade_role) -> archétype court attendu par le front.
_ARCH_FRONT = {
    "seeding-source": "source",
    "forward-hub": "hub",
    "cross-channel-bridge": "bridge",
    "reactivator": "reactivator",
}

_MULTI_SOURCE_THRESHOLD = 0.3


def _round01(x: float) -> float:
    return round(max(0.0, min(1.0, float(x))), 4)


def _ev_pairs(evidence: dict, keys: list[tuple[str, str]]) -> list[list]:
    """Sélectionne des paires [label, valeur] de preuve pour le front."""
    out: list[list] = []
    for src_key, label in keys:
        if src_key in evidence and evidence[src_key] is not None:
            v = evidence[src_key]
            if isinstance(v, float):
                v = round(v, 4)
            out.append([label, v])
    return out


def build_episode_dossier(
    *,
    episode_id: str,
    title: str,
    theme: str,
    severity_tier: str,
    cluster_channels: list[dict],
    cascade_scores: dict,
    coordination_scores: dict,
    recidivism_scores: dict,
    forward_influence_norm: dict[int, float],
    timeline: list[int],
    hours: int,
    attribution_tier: Literal["T1", "T2"] = "T2",
    next_tier: str = "T4",
) -> dict:
    """
    Assemble un dossier au CONTRAT frontend (objet d'EPISODES[]).

    Args:
        episode_id: identifiant d'épisode (sert d'`id`).
        title, theme: libellés institutionnels du cluster.
        severity_tier: tier de sévérité ("T3", ...) — sert à `tier`/`tc`.
        cluster_channels: liste de dicts {channel_id, username, member_count}
            définissant le périmètre exact du cluster.
        cascade_scores / coordination_scores / recidivism_scores:
            dicts {channel_id: ScoreResult} produits par les scorers (familles
            b / c / d) — RÉELS.
        forward_influence_norm: {channel_id: forward-influence normalisée 0..1}.
        timeline: 24 entiers (activité de forward réelle par bucket).
        hours: durée observée de l'épisode (heures).
        attribution_tier: "T1" ou "T2" (jamais "T3" — garde institutionnelle).
        next_tier: prochain palier d'escalade affiché.

    Returns:
        dict conforme au contrat EPISODES[] (sérialisable JSON tel quel).

    Effet de bord : valide un DossierSchema interne (T1/T2 only,
    coverage_callout obligatoire) pour faire respecter la garde institutionnelle.
    """
    cluster_ids = [c["channel_id"] for c in cluster_channels]

    # --- Agrégation des scores réels au niveau cluster -------------------- #
    # Famille b (cascade) : on prend le canal au Bridge Score le plus fort
    # comme représentant du rôle structurel du cluster.
    b_vals = [(cid, cascade_scores[cid]) for cid in cluster_ids if cid in cascade_scores]
    b_lead_cid, b_lead = max(b_vals, key=lambda kv: kv[1].value) if b_vals else (None, None)
    b_value = b_lead.value if b_lead else 0.0
    b_arch_internal = (b_lead.evidence.get("archetype") if b_lead else None) or "forward-hub"
    b_label = _ARCH_FRONT.get(b_arch_internal, b_arch_internal)

    # Famille c (coordination) : force max de co-forwarding dans le cluster.
    c_vals = [(cid, coordination_scores[cid]) for cid in cluster_ids if cid in coordination_scores]
    c_lead_cid, c_lead = max(c_vals, key=lambda kv: kv[1].value) if c_vals else (None, None)
    c_value = c_lead.value if c_lead else 0.0

    # Famille d (récidivisme) : canal le plus récidiviste du cluster.
    d_vals = [(cid, recidivism_scores[cid]) for cid in cluster_ids if cid in recidivism_scores]
    d_lead_cid, d_lead = max(d_vals, key=lambda kv: kv[1].value) if d_vals else (None, None)
    d_value = d_lead.value if d_lead else 0.0

    def _band(score) -> tuple[float, float]:
        if score is None:
            return 0.0, 0.0
        return _round01(score.confidence_low), _round01(score.confidence_high)

    b_lo, b_hi = _band(b_lead)
    c_lo, c_hi = _band(c_lead)
    d_lo, d_hi = _band(d_lead)

    # --- Stubs explicites pour a (proximité) et e (origine IA) ------------ #
    stub_ev_a = [["statut", "N/A — pas de registre d'épisodes (v0)"]]
    stub_ev_e = [["statut", "N/A — détecteur GenAI non câblé (v0)"]]

    scores = {
        "a": {
            "n": "Proximité revendication",
            "v": 0.0, "lo": 0.0, "hi": 0.0,
            "c": _FAMILY_COLORS["a"],
            "ev": stub_ev_a,
        },
        "b": {
            "n": "Rôle en cascade",
            "v": _round01(b_value), "lo": b_lo, "hi": b_hi,
            "c": _FAMILY_COLORS["b"],
            "label": b_label,
            "ev": _ev_pairs(
                b_lead.evidence if b_lead else {},
                [
                    ("archetype", "archétype"),
                    ("bridge_raw", "Bridge Score brut"),
                    ("in_degree", "origines relayées"),
                    ("out_degree", "canaux relayeurs"),
                    ("out_weight", "forwards gagnés"),
                ],
            ),
        },
        "c": {
            "n": "Coordination",
            "v": _round01(c_value), "lo": c_lo, "hi": c_hi,
            "c": _FAMILY_COLORS["c"],
            "ev": _ev_pairs(
                c_lead.evidence if c_lead else {},
                [
                    ("jaccard_max", "Jaccard co-forward max"),
                    ("coforward_partners", "pairs co-forwardants"),
                    ("shared_origins", "origines partagées"),
                    ("coforward_pair_count_graph", "paires co-forward (graphe)"),
                ],
            ),
        },
        "d": {
            "n": "Récidivisme inter-épisodes",
            "v": _round01(d_value), "lo": d_lo, "hi": d_hi,
            "c": _FAMILY_COLORS["d"],
            "ev": _ev_pairs(
                d_lead.evidence if d_lead else {},
                [
                    ("forward_influence", "forward-influence"),
                    ("source_recurrence", "relayeurs distincts"),
                    ("forward_influence_norm", "forward-influence (norm.)"),
                ],
            ),
        },
        "e": {
            "n": "Probabilité origine IA",
            "v": 0.0, "lo": 0.0, "hi": 0.0,
            "c": _FAMILY_COLORS["e"],
            "ev": stub_ev_e,
        },
    }

    # --- Règle multi-source sur les scores réels (b, c, d) ---------------- #
    triggered = [
        fam for fam, val in (("b", b_value), ("c", c_value), ("d", d_value))
        if val >= _MULTI_SOURCE_THRESHOLD
    ]
    n_signals = len(triggered)
    n_families = len(triggered)  # 1 famille = 1 signal ici
    gate_met = n_signals >= 3 and n_families >= 2
    gate_detail = f"{n_signals} signaux · {n_families} familles"

    # --- channels_detail : vrais canaux du cluster ------------------------ #
    channels_detail = []
    for c in cluster_channels:
        cid = c["channel_id"]
        cscore = cascade_scores.get(cid)
        arch_internal = (cscore.evidence.get("archetype") if cscore else None) or "forward-hub"
        channels_detail.append({
            "id": f"@{c['username']}" if c.get("username") else f"id={cid}",
            "arch": _ARCH_FRONT.get(arch_internal, "hub"),
            "subs": int(c.get("member_count") or 0),
            "fi": _round01(forward_influence_norm.get(cid, 0.0)),
        })

    # --- Garde institutionnelle : valider un DossierSchema interne -------- #
    # (force attribution_tier ∈ {T1,T2} et la présence du coverage_callout).
    score_results_internal = [
        ScoreResult(family="cascade_role", value=_round01(b_value),
                    confidence_low=b_lo, confidence_high=b_hi,
                    triggered=b_value >= _MULTI_SOURCE_THRESHOLD,
                    evidence=(b_lead.evidence if b_lead else {})),
        ScoreResult(family="coordination", value=_round01(c_value),
                    confidence_low=c_lo, confidence_high=c_hi,
                    triggered=c_value >= _MULTI_SOURCE_THRESHOLD,
                    evidence=(c_lead.evidence if c_lead else {})),
        ScoreResult(family="recidivism", value=_round01(d_value),
                    confidence_low=d_lo, confidence_high=d_hi,
                    triggered=d_value >= _MULTI_SOURCE_THRESHOLD,
                    evidence=(d_lead.evidence if d_lead else {})),
    ]
    sev = severity_tier if severity_tier in {"T1", "T2", "T3", "T4", "T5"} else "T3"
    DossierSchema(
        dossier_id=new_dossier_id(),
        episode_id=episode_id,
        attribution_tier=attribution_tier,  # T3 -> ValidationError (par design)
        severity_tier=sev,  # type: ignore[arg-type]
        methodology_version_hash=get_methodology_version_hash(),
        created_at=now_utc(),
        multi_source_rule_met=gate_met,
        scores=score_results_internal,
        evidence_channels=[
            EvidenceChannel(
                channel_id=c["channel_id"],
                username=c.get("username"),
                cascade_role=_internal_role(cascade_scores.get(c["channel_id"])),
            )
            for c in cluster_channels
        ],
        coverage_callout=COVERAGE_CALLOUT_FR,
    )

    # --- Objet final au contrat frontend ---------------------------------- #
    return {
        "id": episode_id,
        "tier": severity_tier,
        "tc": severity_tier.lower(),
        "theme": theme,
        "title": title,
        "channels": len(cluster_channels),
        "hours": int(hours),
        "scores": scores,
        "gateMet": gate_met,
        "gateDetail": gate_detail,
        "nextTier": next_tier,
        "attr": attribution_tier,
        "channels_detail": channels_detail,
        "timeline": [int(x) for x in timeline],
        "coverage_callout": COVERAGE_CALLOUT_FR,
    }


def _internal_role(score) -> CascadeRoleLiteral | None:
    """Archétype interne valide pour EvidenceChannel (ou None).

    Le type de retour est le Literal attendu par ``EvidenceChannel`` : la garde
    ci-dessous EST la validation, il faut donc que la signature le dise.
    """
    if score is None:
        return None
    arch = score.evidence.get("archetype")
    if arch in _VALID_CASCADE_ROLES:
        return cast("CascadeRoleLiteral", arch)
    return None
