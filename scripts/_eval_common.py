"""Helpers READ-ONLY pour la batterie de validation/falsification du score.

> Programme de falsification (plan 2026-06-08) : le score de suspicion mesure-t-il
> une manipulation, ou seulement une position structurale dans le graphe ?

Lit l'INSTANTANÉ statique `data/*.json` (celui sur lequel les scores ont été
matérialisés) — JAMAIS la DB live, qui a divergé depuis l'export (le crawler
tourne). Sorties JSON sous `data/eval/`. Aucune écriture hors `data/eval/`.
"""
from __future__ import annotations

import json
from pathlib import Path

from scipy.stats import spearmanr

_REPO = Path(__file__).resolve().parents[1]
DATA = _REPO / "data"
EVAL_OUT = DATA / "eval"


def load_channels() -> dict:
    return json.loads((DATA / "channels.json").read_text(encoding="utf-8"))


def load_graph() -> dict:
    return json.loads((DATA / "graph.json").read_text(encoding="utf-8"))


def spearman(a: list[float], b: list[float]) -> float:
    """Corrélation de rang de Spearman (scipy — dépendance garantie)."""
    if len(a) != len(b) or len(a) < 2:
        return 0.0
    r = spearmanr(a, b).correlation
    return float(r) if r == r else 0.0  # NaN -> 0


def topk_set(ids: list, scores: list[float], k: int) -> set:
    """Ensemble des ids du top-K par score décroissant (tri stable déterministe)."""
    order = sorted(range(len(ids)), key=lambda i: (scores[i], str(ids[i])), reverse=True)
    return {ids[i] for i in order[:k]}


def jaccard(a: set, b: set) -> float:
    u = a | b
    return len(a & b) / len(u) if u else 0.0


def write_report(name: str, obj: dict) -> Path:
    EVAL_OUT.mkdir(parents=True, exist_ok=True)
    p = EVAL_OUT / name
    p.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")
    return p
