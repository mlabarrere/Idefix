"""Exp 2 — Récupération d'épisode connu (SM-1 : top-K précision/rappel).

Le top-K de suspicion fait-il REMONTER une opération documentée ? Épisode test :
le cluster Dugin (webapp/public/data/russosphere/dugin_cluster.json).

>>> AVERTISSEMENT CIRCULARITÉ (load-bearing) : on n'utilise QUE la MEMBERSHIP
>>> (les usernames). On IGNORE tous les scores/fi/arch du dossier (auto-dérivés).
>>> Mais la membership vient en partie de l'allowlist analyste + connectivité, et
>>> les scores de channels.json viennent du MÊME scoreur → ce test est INDICATIF.
>>> Le test NON circulaire exige une liste de graines EXTERNE (humain) :
>>> data/eval/gold_episode_<nom>.json = {"episode":..,"seeds":[..],"relays":[..]}.
>>> S'il existe, ce script l'utilise en plus du cluster Dugin.

READ-ONLY. Écrit data/eval/episode_recovery.json.
Usage : python scripts/eval_episode_recovery.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
_SCRIPTS = Path(__file__).resolve().parent
for _p in (str(_REPO), str(_SCRIPTS)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import _eval_common as ev  # noqa: E402

from src.validation_lab.schema import load_external_gold_episode  # noqa: E402

DOSSIER = _REPO / "webapp" / "public" / "data" / "russosphere" / "dugin_cluster.json"
GOLD_DIR = _REPO / "data" / "eval"


# En deçà de ce nombre de membres du gold effectivement présents dans le
# corpus, l'expérience n'a pas la puissance de trancher : le verdict est
# NON CONCLUANT plutôt qu'interprété (docs/experiments/exp2-episode-recovery.md).
MIN_MATCHED_FOR_VERDICT = 10


def _norm(u: str) -> str:
    return (u or "").lstrip("@").lower()


def _evaluate(name: str, members: list[str], rank: dict, n: int) -> dict:
    matched = [(_norm(u), rank[_norm(u)]) for u in members if _norm(u) in rank]
    ranks = sorted(r for _, r in matched)
    out = {"episode": name, "cluster_size": len(members), "matched_in_corpus": len(matched)}
    # DÉFAUT D11 (corrigé 2026-09). ``random_control_recall@k`` valait
    # ``len(members) * k / n`` : c'est le NOMBRE DE HITS ATTENDU sous classement
    # aléatoire, pas un recall. Il était pourtant affiché à côté d'un vrai
    # ``recall@k = hits / len(members)``, si bien que le même fichier de sortie
    # supportait deux lectures contradictoires du même run. Le contrôle correct
    # pour un recall@k est ``k / n`` (probabilité qu'un membre donné tombe dans
    # le top-k au hasard). Le comptage attendu est conservé, mais sous un nom
    # qui dit ce qu'il est.
    #
    # ``matched_in_corpus`` est la base des recalls : un membre du gold ABSENT
    # du corpus ne peut pas être récupéré, et le compter comme un échec de
    # classement confond couverture et performance. Les deux dénominateurs sont
    # publiés pour que la distinction reste lisible.
    for k in (20, 50, 100):
        hit = sum(1 for r in ranks if r <= k)
        out[f"hits@{k}"] = hit
        out[f"recall@{k}"] = round(hit / len(members), 4) if members else 0.0
        out[f"recall_in_corpus@{k}"] = round(hit / len(matched), 4) if matched else 0.0
        out[f"precision@{k}"] = round(hit / k, 4)
        # Contrôle aléatoire, exprimé dans la MÊME unité que recall@k.
        out[f"random_control_recall@{k}"] = round(min(1.0, k / n), 4) if n else 0.0
        # …et le nombre de hits attendu, nommé pour ce qu'il est.
        out[f"expected_hits_random@{k}"] = round(len(matched) * k / n, 3) if n else 0.0
    out["rank_median"] = ranks[len(ranks) // 2] if ranks else None
    out["rank_min"] = ranks[0] if ranks else None
    out["rank_max"] = ranks[-1] if ranks else None

    # Lift : hits observés / hits attendus. Comparaison homogène (comptes).
    exp50 = out["expected_hits_random@50"]
    hit50 = out["hits@50"]
    out["beats_random_x"] = round(hit50 / exp50, 2) if exp50 else None

    # Puissance : sous ~10 membres du gold réellement présents dans le corpus,
    # un lift est arithmétiquement réel mais non probant. On le dit.
    out["underpowered"] = len(matched) < MIN_MATCHED_FOR_VERDICT
    if out["underpowered"]:
        out["indicative_verdict"] = (
            f"NON CONCLUANT ({len(matched)} membre(s) du gold dans le corpus, "
            f"minimum {MIN_MATCHED_FOR_VERDICT}) — voir "
            f"docs/experiments/exp2-episode-recovery.md"
        )
    elif (out["beats_random_x"] or 0) <= 2.0 or (out["rank_median"] or 0) > 200:
        out["indicative_verdict"] = "FAIBLE (≤2× hasard ou sources enfouies)"
    else:
        out["indicative_verdict"] = "RÉCUPÈRE (au-dessus du hasard)"
    return out


def main() -> None:
    ch = ev.load_channels()["channels"]
    n = len(ch)
    susp_order = sorted(ch, key=lambda c: (c.get("suspicion") or {}).get("v") or 0.0, reverse=True)
    rank = {_norm(c.get("username")): i + 1 for i, c in enumerate(susp_order)}

    episodes = []

    # 1) Cluster Dugin — MEMBERSHIP ONLY (usernames), avec caveat circularité.
    # Optionnel : l'ancien dossier circulaire n'est plus dans le bundle (export REST).
    # On ne dépend QUE du gold externe (non circulaire) quand il est absent.
    if DOSSIER.exists():
        dug = json.loads(DOSSIER.read_text(encoding="utf-8"))
        dug_members = [c["id"] for c in dug.get("channels_detail", [])]
        ev_dug = _evaluate("dugin_cluster (INDICATIF — circularité)", dug_members, rank, n)
        # Sous-test sources (arch=source) — FLAG : arch est auto-dérivé → circulaire.
        sources = [c["id"] for c in dug.get("channels_detail", []) if c.get("arch") == "source"]
        src_ranks = sorted(rank[_norm(u)] for u in sources if _norm(u) in rank)
        ev_dug["documented_sources_arch"] = {
            "count": len(sources),
            "rank_median": src_ranks[len(src_ranks) // 2] if src_ranks else None,
            "in_top50": sum(1 for r in src_ranks if r <= 50),
            "caveat": "arch='source' est auto-dérivé du scoreur -> ce sous-test est CIRCULAIRE.",
        }
        episodes.append(ev_dug)

    # 2) Gold externe (NON circulaire) s'il existe.
    gold_files = sorted(GOLD_DIR.glob("gold_episode_*.json")) if GOLD_DIR.exists() else []
    for gf in gold_files:
        try:
            g = load_external_gold_episode(gf).legacy_eval_payload()
            schema_status = "schema:v1"
        except Exception:
            g = json.loads(gf.read_text(encoding="utf-8"))
            schema_status = "legacy"
        members = list(dict.fromkeys((g.get("seeds") or []) + (g.get("relays") or [])))
        e = _evaluate(f"{g.get('episode', gf.stem)} (EXTERNE — non circulaire)", members, rank, n)
        e["gold_schema"] = schema_status
        if g.get("seeds"):
            sr = sorted(rank[_norm(u)] for u in g["seeds"] if _norm(u) in rank)
            e["external_seeds"] = {
                "count": len(g["seeds"]),
                "rank_median": sr[len(sr) // 2] if sr else None,
                "in_top50": sum(1 for r in sr if r <= 50),
            }
        episodes.append(e)

    report = {
        "experiment": "known_episode_topk_recovery",
        "n_channels": n,
        "episodes": episodes,
        "note": "Le test PROBANT nécessite data/eval/gold_episode_<nom>.json (liste de "
                "graines définie par un HUMAIN externe). Sans lui, seul le cluster Dugin "
                "(indicatif, circularité partielle) est mesuré.",
        "has_external_gold": bool(gold_files),
    }
    p = ev.write_report("episode_recovery.json", report)
    print(f"[Exp2 recovery] écrit -> {p}  | gold externe: {bool(gold_files)}")
    for e in episodes:
        print(
            f"  {e['episode']}: {e['matched_in_corpus']}/{e['cluster_size']} "
            f"dans le corpus | recall@50={e['recall@50']} "
            f"(hasard={e['random_control_recall@50']}, ×{e['beats_random_x']}) | "
            f"rang médian={e['rank_median']} "
            f"(min {e['rank_min']}, max {e['rank_max']}) | "
            f"{e['indicative_verdict']}"
        )
        if "documented_sources_arch" in e:
            s = e["documented_sources_arch"]
            print(
                f"    sources(arch, CIRCULAIRE): {s['count']} | "
                f"rang médian {s['rank_median']} | top50 {s['in_top50']}"
            )


if __name__ == "__main__":
    main()
