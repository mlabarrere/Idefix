"""Benchmark runtime minimal — chiffres de performance reproductibles.

Mesure ce qui est local et déterministe : taille du corpus (REST Supabase), taux
de cache embeddings, débit d'encodage (cache hit vs miss). Écrit docs/metrics/perf.json.

ponytail : volontairement minimal — pas de profiling fin, juste les ordres de grandeur
cités dans l'audit. Étendre si un goulot précis doit être tracé.

Usage : python scripts/bench.py
"""
import json
import os
import time
import urllib.request
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

_REPO = Path(__file__).resolve().parents[1]
CACHE = _REPO / "data" / "embed_cache"
OUT = _REPO / "docs" / "metrics" / "perf.json"
BASE = os.environ["SUPABASE_URL"].rstrip("/") + "/rest/v1"
KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY") or os.environ["SUPABASE_KEY"]


def _count(table: str) -> int:
    req = urllib.request.Request(
        f"{BASE}/{table}?select=*",
        headers={"apikey": KEY, "Authorization": f"Bearer {KEY}",
                 "Range": "0-0", "Prefer": "count=exact"},
    )
    with urllib.request.urlopen(req, timeout=40) as r:
        cr = r.headers.get("Content-Range", "")
    return int(cr.split("/")[-1]) if "/" in cr else 0


def main() -> None:
    perf: dict = {"generated": "bench"}

    # 1. Tailles de corpus (REST)
    t = time.perf_counter()
    perf["corpus"] = {t_: _count(t_) for t_ in ("channels", "edges", "messages", "channel_scores")}
    perf["rest_count_seconds"] = round(time.perf_counter() - t, 2)

    # 2. Cache embeddings
    n_cache = len(list(CACHE.glob("*.npy"))) if CACHE.exists() else 0
    perf["embed_cache_files"] = n_cache

    # 3. Débit d'encodage (hit vs miss) — petit échantillon
    try:
        from src.embed.encoder import Embedder
        emb = Embedder()
        sample = [f"benchmark idefix phrase numéro {i} texte de test" for i in range(32)]
        t = time.perf_counter()
        emb.encode_texts(sample)            # miss (1er encodage)
        miss = time.perf_counter() - t
        t = time.perf_counter()
        emb.encode_texts(sample)            # hit (cache)
        hit = time.perf_counter() - t
        perf["encode_32_miss_s"] = round(miss, 3)
        perf["encode_32_hit_s"] = round(hit, 3)
        perf["encode_throughput_texts_per_s_miss"] = round(32 / miss, 1) if miss else None
        perf["cache_speedup_x"] = round(miss / hit, 1) if hit else None
    except Exception as e:  # noqa: BLE001
        perf["encode_error"] = str(e)[:120]

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(perf, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(perf, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
