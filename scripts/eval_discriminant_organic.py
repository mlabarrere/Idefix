"""Exp 3 — Discriminant : coordination HOSTILE vs ORGANIQUE (Q6).

Le système sait-il distinguer un réseau coordonné hostile d'un groupe ORGANIQUE
qui co-poste (militantisme, viralité, auto-repost média) ? Dans le code, la famille
coordination (c) se déclenche IDENTIQUEMENT pour les deux ; seuls les BOOSTS de
sévérité (reforward-depuis-suspect, domaine-adverse, france_targeting) discriminent.

Cette expérience le CHIFFRE :
  - parmi les canaux à forte coordination, qu'est-ce qui explique l'écart de
    suspicion — la coordination elle-même, ou les boosts d'« ancrage adverse » ?
  - et elle fait REMONTER les candidats « organiques » (forte coordination, faible
    ancrage adverse) à départager à l'œil.

READ-ONLY : data/channels.json. Écrit data/eval/discriminant_organic.json.
Usage : python scripts/eval_discriminant_organic.py
"""
from __future__ import annotations

import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
_SCRIPTS = Path(__file__).resolve().parent
for _p in (str(_REPO), str(_SCRIPTS)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import _eval_common as ev  # noqa: E402


def _linkage(sev: dict) -> float:
    """Ancrage adverse = fraction reforward-depuis-suspect + citations domaine-adverse (saturé)."""
    if not sev:
        return 0.0
    return float(sev.get("reforward_suspect_frac") or 0.0) + min(
        1.0, (sev.get("adversary_domain_citations") or 0) / 5.0
    )


def main() -> None:
    ch = ev.load_channels()["channels"]

    rows = []
    for c in ch:
        comp = c.get("_components") or {}
        cc = comp.get("c") or {}
        sev = comp.get("_severity_detail") or {}
        rows.append({
            "username": c.get("username"),
            "title": c.get("title"),
            "coord_value": float(cc.get("value") or 0.0),
            "coord_trig": bool(cc.get("triggered")),
            "base": float(comp.get("_base") or 0.0),
            "suspicion": float((c.get("suspicion") or {}).get("v") or 0.0),
            "factor": float(comp.get("_severity_factor") or 1.0),
            "linkage": _linkage(sev),
            "reforward_suspect": float((sev or {}).get("reforward_suspect_frac") or 0.0),
            "adv_domains": int((sev or {}).get("adversary_domain_citations") or 0),
            "france_targeting": float(c.get("france_targeting") or 0.0),
            "credibility_prior": c.get("credibility_prior"),
            "tier": c.get("tier"),
        })

    # Univers « coordonné » = coordination déclenchée.
    coord = [r for r in rows if r["coord_trig"]]
    coord.sort(key=lambda r: r["coord_value"], reverse=True)

    # Rang de suspicion global (1 = plus suspect).
    susp_order = sorted(rows, key=lambda r: r["suspicion"], reverse=True)
    rank = {r["username"]: i + 1 for i, r in enumerate(susp_order)}

    # AUTOMATIQUE : parmi les coordonnés, qu'est-ce qui explique la suspicion ?
    if len(coord) >= 2:
        sp_coord = ev.spearman([r["suspicion"] for r in coord], [r["coord_value"] for r in coord])
        sp_link = ev.spearman([r["suspicion"] for r in coord], [r["linkage"] for r in coord])
        sp_base = ev.spearman([r["suspicion"] for r in coord], [r["base"] for r in coord])
    else:
        sp_coord = sp_link = sp_base = 0.0

    # Candidats ORGANIQUES : forte coordination MAIS faible ancrage adverse.
    organic = [
        r for r in coord
        if r["reforward_suspect"] < 0.20
        and r["adv_domains"] == 0
        and r["france_targeting"] < 0.10
        and r["credibility_prior"] != "suspect"
    ]
    organic.sort(key=lambda r: r["coord_value"], reverse=True)
    # Combien de candidats organiques polluent le top-50 de suspicion ?
    organic_in_top50 = [r for r in organic if rank.get(r["username"], 10**9) <= 50]

    report = {
        "experiment": "discriminant_hostile_vs_organic",
        "n_coordination_triggered": len(coord),
        "n_T2": sum(1 for r in rows if r["tier"] == "T2"),
        "what_drives_suspicion_among_coordinated": {
            "spearman_suspicion_vs_coordination_value": round(sp_coord, 4),
            "spearman_suspicion_vs_adversary_linkage": round(sp_link, 4),
            "spearman_suspicion_vs_base": round(sp_base, 4),
            "lecture": "Si linkage >> coordination_value, la discrimination vient des "
                       "boosts d'ancrage adverse, PAS de la structure de coordination.",
        },
        "organic_candidates_count": len(organic),
        "organic_candidates_in_suspicion_top50": len(organic_in_top50),
        "top15_coordination": [
            {"username": r["username"], "title": (r["title"] or "")[:60],
             "coord_value": round(r["coord_value"], 3), "suspicion": round(r["suspicion"], 3),
             "rang_suspicion": rank.get(r["username"]),
             "adversary_linkage": round(r["linkage"], 3),
             "credibility_prior": r["credibility_prior"], "tier": r["tier"],
             "verdict_humain": "?? (organique / adverse / inconnu)"}
            for r in coord[:15]
        ],
        "organic_candidates_to_label": [
            {"username": r["username"], "title": (r["title"] or "")[:60],
             "coord_value": round(r["coord_value"], 3), "suspicion": round(r["suspicion"], 3),
             "rang_suspicion": rank.get(r["username"]),
             "verdict_humain": "?? (organique / adverse)"}
            for r in organic[:20]
        ],
        "falsify_rule": "FALSIFIÉ si ≥3 des organic_candidates confirmés organiques sont dans "
                        "le top-50 suspicion (contamination de la file opérationnelle).",
        "human_step_required": True,
    }

    p = ev.write_report("discriminant_organic.json", report)
    print(f"[Exp3 discriminant] écrit -> {p}")
    print(f"  coordonnés (c déclenchée): {len(coord)} | T2: {report['n_T2']}")
    w = report["what_drives_suspicion_among_coordinated"]
    print(f"  Parmi les coordonnés — ce qui explique la suspicion :")
    print(f"    Spearman(suspicion, valeur_coordination) = {w['spearman_suspicion_vs_coordination_value']:+.3f}")
    print(f"    Spearman(suspicion, ancrage_adverse)     = {w['spearman_suspicion_vs_adversary_linkage']:+.3f}")
    print(f"    Spearman(suspicion, base_structurelle)   = {w['spearman_suspicion_vs_base']:+.3f}")
    print(f"  candidats organiques (forte coord, faible ancrage adverse): {len(organic)} "
          f"| dont dans top-50 suspicion: {len(organic_in_top50)}")
    print(f"  -> {len(report['organic_candidates_to_label'])} candidats à départager à l'œil (dans le rapport)")


if __name__ == "__main__":
    main()
