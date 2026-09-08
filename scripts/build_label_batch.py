"""Génération d'un batch d'items pour la labellisation gold (Story 1.1, T2, AC1 + AC8).

Pipeline de sélection (deux portes France, voir review B1) :
  1. Pré-filtre canal : channels.extra.fr_score >= min_fr_score (tag_france.py).
  2. Porte France AU NIVEAU MESSAGE (NFR-15) : le texte doit contenir >=1 mot-clé
     France — élimine le hors-scope manifeste (Kremlin, Cuba/USA…) qui se glissait
     via des canaux globalement France-pertinents.
  3. Lien revendication TF-IDF cosinus (« lexical ») ; les items dont la proximité
     est < min_claim_proximity vont en file `needs_manual_screening` (le lien claim
     serait du bruit), PAS dans le batch labellisé.
  4. Échantillon stratifié reproductible des items éligibles → data/annotations/<batch_id>.jsonl
     Items écartés → data/annotations/<batch_id>__needs_manual_screening.jsonl

Usage (CLI) :
    python scripts/build_label_batch.py --n 300 --batch-id batch-20260604
    python scripts/build_label_batch.py --n 300 --min-fr-score 0.20 --min-claim-proximity 0.05

Contraintes métier (AR) :
- AC8 : aucun appel réseau (ni Telegram/MTProto ni API Google FC) — lecture DB seule.
- AC1/NFR-15 : filtre France réutilise channels.extra.fr_score + mots-clés tag_france.py.
- NFR-20 : sklearn pour TF-IDF/cosinus — pas d'implémentation maison.
"""

from __future__ import annotations

import argparse
import asyncio
import random
import re
import statistics
import sys
from datetime import date
from pathlib import Path
from typing import Any

import asyncpg
from src.shared.db import db_connect
from dotenv import load_dotenv
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

# Ensure repo root is on sys.path when run as a script (python scripts/build_label_batch.py)
_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from src.labeling import io  # noqa: E402
from src.labeling.schema import BatchItem, make_item_id  # noqa: E402

# ---------------------------------------------------------------------------
# Fonctions pures (importables par les tests sans DB)
# ---------------------------------------------------------------------------

# Mots-clés France au niveau message — miroir de scripts/tag_france.py::FR_KW.
# La porte France-message (NFR-15) exige >=1 occurrence dans le texte du message.
from src.missions.russosphere import FR_KEYWORDS_ELECTORAL as FR_KW  # noqa: E402
_FR_PATTERN = re.compile("|".join(re.escape(k) for k in FR_KW), re.IGNORECASE)


def france_keyword_match(text: str | None) -> bool:
    """True si le texte du message contient >=1 mot-clé France (porte NFR-15)."""
    if not text:
        return False
    return _FR_PATTERN.search(text) is not None


# Médias français légitimes connus (graines snowball) — classe « legit » = négatifs
# probables (vrai journalisme). Liste curée, éditable. Le label final reste donné
# par les juges ; ceci n'est qu'un a priori d'échantillonnage pour équilibrer les classes.
LEGIT_USERNAMES = {
    "france24_fr", "rfi_fr", "actu17", "mediavenir", "euronewsfr", "alertefr", "neodia",
}


def classify_credibility(
    username: str | None,
    fr_score: float | None,
    low_cred_threshold: float = 0.15,
    legit_usernames: set[str] | None = None,
) -> str:
    """A priori de crédibilité de la SOURCE pour équilibrer le batch (review : gold 97% Vrai).

    - "legit"   : média français connu (liste curée) → négatifs probables.
    - "suspect" : canal à faible score France (fr_score < seuil) = apparat à faible
                  crédibilité (cluster Dugin/Geopolitika/Pravda) → positifs probables.
    - "other"   : le reste (canaux France ambigus / relais).
    Ce n'est PAS le label : les juges évaluent chaque message indépendamment.
    """
    legit = legit_usernames if legit_usernames is not None else LEGIT_USERNAMES
    u = (username or "").lower()
    if u in legit:
        return "legit"
    if fr_score is not None and fr_score < low_cred_threshold:
        return "suspect"
    return "other"


def credibility_balanced_sample(
    items: list[Any],
    n: int,
    seed: int = 42,
) -> list[Any]:
    """Échantillon de n items équilibré par classe de crédibilité de source.

    Prend autant de « suspect » (positifs probables) que possible jusqu'à n/2,
    apparie avec autant de « legit » (négatifs), puis complète avec « other » et le
    reliquat. Stratifie par revendication (stratified_sample) à l'intérieur de chaque
    classe pour couvrir les narratifs. Déterministe (seed).
    """
    if not items:
        return []

    def _cred(it: Any) -> str:
        if hasattr(it, "source_credibility"):
            return it.source_credibility or "other"
        return it.get("source_credibility", "other") if isinstance(it, dict) else "other"

    by = {"suspect": [], "legit": [], "other": []}
    for it in items:
        by.get(_cred(it), by["other"]).append(it)

    n_pos = min(len(by["suspect"]), n // 2)
    n_neg = min(len(by["legit"]), n - n_pos)
    selected = (
        stratified_sample(by["suspect"], n_pos, seed=seed)
        + stratified_sample(by["legit"], n_neg, seed=seed + 1)
    )
    # Complète avec « other » puis tout reliquat si on n'a pas atteint n
    remaining = n - len(selected)
    if remaining > 0:
        leftover = by["other"] + by["suspect"][n_pos:] + by["legit"][n_neg:]
        selected += stratified_sample(leftover, remaining, seed=seed + 2)

    rng = random.Random(seed)
    rng.shuffle(selected)
    return selected


def split_by_proximity(
    items: list[Any],
    min_proximity: float,
) -> tuple[list[Any], list[Any]]:
    """Partitionne les items en (éligibles, à_screener) selon claim_proximity.

    Éligible si claim_proximity >= min_proximity (lien revendication exploitable) ;
    sinon le lien claim est trop faible → screening manuel (review B1).
    Lit l'attribut .claim_proximity (BatchItem) ou la clé (dict).

    Robustesse (review MED) : une proximité None / non numérique est coercée à 0.0
    (l'item part en screening) plutôt que de lever TypeError et faire échouer le batch.
    """
    def _prox(item: Any) -> float:
        if hasattr(item, "claim_proximity"):
            raw = item.claim_proximity
        elif isinstance(item, dict):
            raw = item.get("claim_proximity", 0.0)
        else:
            return 0.0
        try:
            return float(raw)
        except (TypeError, ValueError):
            return 0.0

    eligible = [i for i in items if _prox(i) >= min_proximity]
    screened = [i for i in items if _prox(i) < min_proximity]
    return eligible, screened


def rank_nearest_claim(
    message_texts: list[str],
    claims: list[dict],
) -> list[tuple[str | None, str | None, float]]:
    """Associe chaque message à la revendication enregistrée la plus proche.

    Utilise TF-IDF + similarité cosinus (sklearn, NFR-20).
    Méthode d'ancrage : « lexical ».

    Args:
        message_texts: textes des messages candidats.
        claims: liste de dicts issus de io.load_claims() — champ « claim_text » requis.

    Returns:
        Liste de triplets (claim_id | None, claim_text | None, proximity ∈ [0, 1])
        dans le même ordre que message_texts.
        Si message_texts ou claims est vide, retourne des triplets (None, None, 0.0).

    Robustesse (review MED) :
        - les revendications dépourvues de « id » ou « claim_text » sont ignorées
          (un avertissement est émis) plutôt que de lever KeyError ;
        - si le vocabulaire TF-IDF est vide (textes tous vides / stopwords),
          retourne (None, None, 0.0) pour chaque message au lieu de lever
          ValueError.
    """
    if not message_texts:
        return []
    if not claims:
        return [(None, None, 0.0) for _ in message_texts]

    # Garde : ignorer les revendications mal formées (id/claim_text manquant)
    claim_texts: list[str] = []
    claim_ids: list[str] = []
    for c in claims:
        if "id" not in c or "claim_text" not in c:
            print(
                f"[rank_nearest_claim] revendication ignorée (id/claim_text "
                f"manquant) : {c!r}",
                file=sys.stderr,
            )
            continue
        claim_ids.append(c["id"])
        claim_texts.append(c["claim_text"])

    if not claim_texts:
        # Toutes les revendications étaient mal formées → aucune ancre exploitable.
        print(
            "[rank_nearest_claim] aucune revendication valide après filtrage — "
            "retour (None, None, 0.0).",
            file=sys.stderr,
        )
        return [(None, None, 0.0) for _ in message_texts]

    # Ajuster min_df dynamiquement pour les petits corpus de test
    n_docs = len(claim_texts) + len(message_texts)
    min_df = 1 if n_docs < 10 else 2

    vectorizer = TfidfVectorizer(
        analyzer="word",
        ngram_range=(1, 2),
        min_df=min_df,
        sublinear_tf=True,
    )
    all_texts = claim_texts + message_texts
    try:
        tfidf_matrix = vectorizer.fit_transform(all_texts)
    except ValueError as exc:
        # « empty vocabulary » : tous les textes sont vides / stopwords.
        print(
            f"[rank_nearest_claim] vocabulaire TF-IDF vide ({exc}) — "
            "retour (None, None, 0.0) pour chaque message.",
            file=sys.stderr,
        )
        return [(None, None, 0.0) for _ in message_texts]

    claim_matrix = tfidf_matrix[: len(claim_texts)]
    message_matrix = tfidf_matrix[len(claim_texts) :]

    # shape: (n_messages, n_claims)
    sims = cosine_similarity(message_matrix, claim_matrix)

    results: list[tuple[str | None, str | None, float]] = []
    for row in sims:
        best_idx = int(row.argmax())
        score = float(row[best_idx])
        results.append((claim_ids[best_idx], claim_texts[best_idx], round(score, 6)))

    return results


def stratified_sample(
    items: list[Any],
    n: int,
    seed: int = 42,
) -> list[Any]:
    """Échantillon déterministe de n items, stratifié par candidate_claim_id.

    Garantit que chaque claim_id distinct est représenté au moins une fois si
    possible, puis complète au hasard jusqu'à n.

    Limite documentée (review MED, LOW) : si n < nombre de buckets claim distincts,
    la phase 1 est tronquée à n (`selected[:n]`) et tous les claims ne sont PAS
    garantis représentés. C'est une limite acceptée de la Phase 1 du PoC, pas un
    défaut — calibrer n >= nombre de claims attendus pour une couverture complète.

    Les items peuvent être des BatchItem Pydantic ou des dicts ;
    l'attribut / clé candidate_claim_id est consulté.

    Args:
        items: liste d'items à échantillonner.
        n: taille cible. Si len(items) <= n, retourne tous les items (mélangés).
        seed: graine pour la reproductibilité déterministe.

    Returns:
        Sous-liste de taille min(n, len(items)).
    """
    if not items:
        return []

    rng = random.Random(seed)

    if len(items) <= n:
        shuffled = list(items)
        rng.shuffle(shuffled)
        return shuffled

    def _claim_id(item: Any) -> str | None:
        if hasattr(item, "candidate_claim_id"):
            return item.candidate_claim_id
        return item.get("candidate_claim_id") if isinstance(item, dict) else None

    # Grouper par claim_id
    buckets: dict[str | None, list[Any]] = {}
    for item in items:
        cid = _claim_id(item)
        buckets.setdefault(cid, []).append(item)

    selected: list[Any] = []

    # Phase 1 : prendre un représentant par bucket (couverture des claims)
    for cid in sorted(buckets.keys(), key=lambda x: (x is None, x)):
        bucket = buckets[cid]
        rng.shuffle(bucket)
        selected.append(bucket.pop())

    selected = selected[:n]  # cap si déjà trop

    # Phase 2 : compléter depuis le pool restant
    pool: list[Any] = []
    for bucket in buckets.values():
        pool.extend(bucket)
    rng.shuffle(pool)

    remaining_slots = n - len(selected)
    selected.extend(pool[:remaining_slots])

    rng.shuffle(selected)
    return selected


# ---------------------------------------------------------------------------
# Requête DB + orchestration (async main — jamais importé par les tests)
# ---------------------------------------------------------------------------

# NOTE (review): we do NOT pre-filter on the channel fr_score here. Disinformation
# is propagated by LOW-fr_score channels (the Dugin/Geopolitika apparatus), so a
# channel-level France filter discards exactly the positives we need. Thematic
# France filtering is enforced at the MESSAGE level (france_keyword_match, NFR-15);
# fr_score is kept only as a credibility signal for class balancing. The $1 floor
# defaults to 0.0 (off) but remains tunable.
_QUERY = """
SELECT
    m.message_id,
    m.channel_id,
    m.text,
    m.timestamp,
    m.urls,
    c.username                      AS username,
    (c.extra->>'fr_score')::float   AS fr_score,
    COALESCE(c.username, c.title)   AS channel_name
FROM messages m
JOIN channels c ON c.channel_id = m.channel_id
WHERE
    COALESCE((c.extra->>'fr_score')::float, 0.0) >= $1
    AND m.text IS NOT NULL
    AND char_length(m.text) > 20
    AND m.is_deleted = false
ORDER BY m.timestamp DESC
"""


async def _fetch_candidates(
    conn: asyncpg.Connection,
    min_fr_score: float,
) -> list[dict]:
    """Récupère les messages France-pertinents depuis PostgreSQL."""
    rows = await conn.fetch(_QUERY, min_fr_score)
    result = []
    for r in rows:
        urls_raw = r["urls"]
        if isinstance(urls_raw, list):
            urls = [str(u) for u in urls_raw]
        elif isinstance(urls_raw, str):
            import json as _json

            try:
                parsed = _json.loads(urls_raw)
                urls = [str(u) for u in parsed] if isinstance(parsed, list) else []
            except Exception:
                urls = []
        else:
            urls = []

        result.append(
            {
                "message_id": r["message_id"],
                "channel_id": r["channel_id"],
                "text": r["text"],
                "timestamp": r["timestamp"],
                "urls": urls,
                "username": r["username"],
                "fr_score": r["fr_score"],
                "channel_name": r["channel_name"],
            }
        )
    return result


async def main(
    n: int = 300,
    batch_id: str | None = None,
    min_fr_score: float = 0.0,
    min_claim_proximity: float = 0.04,
    seed: int = 42,
) -> None:
    """Point d'entrée principal : sélectionne, filtre France, annote, split, écrit."""
    if batch_id is None:
        batch_id = f"batch-{date.today().strftime('%Y%m%d')}"

    load_dotenv()
    conn = await db_connect()

    try:
        candidates_raw = await _fetch_candidates(conn, min_fr_score)
    finally:
        await conn.close()

    total_candidates = len(candidates_raw)
    print(f"Candidats canal (fr_score >= {min_fr_score}) : {total_candidates}")

    if not candidates_raw:
        print("Aucun candidat trouvé — vérifier fr_score ou l'état de la DB.")
        return

    # Porte France AU NIVEAU MESSAGE (NFR-15) — élimine le hors-scope manifeste.
    france_candidates = [c for c in candidates_raw if france_keyword_match(c["text"])]
    print(f"Après porte France-message (>=1 mot-clé) : {len(france_candidates)}")

    if not france_candidates:
        print("Aucun message ne passe la porte France — élargir FR_KW ou min_fr_score.")
        return

    # Lier chaque message à la revendication la plus proche (TF-IDF lexical)
    claims = io.load_claims()
    texts = [c["text"] for c in france_candidates]
    rankings = rank_nearest_claim(texts, claims)

    # Construire les BatchItem (avec a priori de crédibilité de source)
    batch_items: list[BatchItem] = []
    for raw, (claim_id, claim_text, proximity) in zip(france_candidates, rankings):
        item = BatchItem(
            item_id=make_item_id(raw["channel_id"], raw["message_id"], batch_id),
            batch_id=batch_id,
            channel_id=raw["channel_id"],
            message_id=raw["message_id"],
            channel_name=raw["channel_name"],
            text=raw["text"],
            timestamp=raw["timestamp"],
            urls=raw["urls"],
            fr_score=raw["fr_score"],
            candidate_claim_id=claim_id,
            candidate_claim_text=claim_text,
            claim_link_method="lexical",
            claim_proximity=proximity,
            source_credibility=classify_credibility(raw.get("username"), raw["fr_score"]),
        )
        batch_items.append(item)

    # Split par proximité (review B1) — MAIS les items « suspect » (positifs probables,
    # rares) sont exemptés du plancher : leur proximité lexicale aux claims français est
    # basse (contenu russe/multilingue), or ce sont précisément les exemples de désinfo
    # recherchés. Le candidate_claim n'est qu'un indice ; le juge tranche. Le plancher
    # ne s'applique qu'aux négatifs (legit/other) pour les garder on-topic.
    suspect_items = [i for i in batch_items if i.source_credibility == "suspect"]
    rest = [i for i in batch_items if i.source_credibility != "suspect"]
    rest_eligible, screened = split_by_proximity(rest, min_claim_proximity)
    eligible = suspect_items + rest_eligible
    print(
        f"Éligibles : {len(eligible)} (dont {len(suspect_items)} suspects exemptés de seuil) "
        f"| à screener : {len(screened)}"
    )

    # Pool éligible par classe de crédibilité (positifs/négatifs probables)
    pool_cred: dict[str, int] = {}
    for it in eligible:
        k = it.source_credibility or "other"
        pool_cred[k] = pool_cred.get(k, 0) + 1
    print(f"Vivier éligible par crédibilité : {pool_cred}")

    # Échantillon ÉQUILIBRÉ par crédibilité (review : éviter le gold 97% Vrai)
    sampled = credibility_balanced_sample(eligible, n=n, seed=seed)

    # Écriture du batch + de la file de screening
    out_path = io.ANNOTATIONS_DIR / f"{batch_id}.jsonl"
    count = io.write_jsonl(out_path, sampled)

    screening_path = io.ANNOTATIONS_DIR / f"{batch_id}__needs_manual_screening.jsonl"
    screening_count = io.write_jsonl(screening_path, screened)

    # Résumé
    fr_scores = [i.fr_score for i in sampled if i.fr_score is not None]
    proximities = [i.claim_proximity for i in sampled]
    claim_dist: dict[str | None, int] = {}
    cred_dist: dict[str, int] = {}
    for item in sampled:
        key = item.candidate_claim_id or "None"
        claim_dist[key] = claim_dist.get(key, 0) + 1
        cred_dist[item.source_credibility or "other"] = (
            cred_dist.get(item.source_credibility or "other", 0) + 1
        )

    print(f"\n=== Batch '{batch_id}' ===")
    print(f"  Candidats canal       : {total_candidates}")
    print(f"  Après porte France    : {len(france_candidates)}")
    print(f"  Éligibles / screening : {len(eligible)} / {screening_count}")
    print(f"  Items échantillonnés  : {count}")
    print(f"  Sortie batch          : {out_path}")
    print(f"  Sortie screening      : {screening_path}")
    if fr_scores:
        print(
            f"  fr_score  min={min(fr_scores):.3f}  "
            f"médiane={statistics.median(fr_scores):.3f}  "
            f"max={max(fr_scores):.3f}"
        )
    if proximities:
        print(
            f"  proximité  min={min(proximities):.3f}  "
            f"médiane={statistics.median(proximities):.3f}  "
            f"max={max(proximities):.3f}"
        )
    print(f"\n  Balance par crédibilité de source (a priori) : {cred_dist}")
    print("\n  Distribution par candidate_claim_id :")
    for cid in sorted(claim_dist.keys()):
        print(f"    {cid:15s}  {claim_dist[cid]:3d}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Génère un batch de labellisation gold pour Idéfix."
    )
    parser.add_argument(
        "--n", type=int, default=300, help="Taille du batch (défaut 300)"
    )
    parser.add_argument(
        "--batch-id",
        default=None,
        help="Identifiant du batch (défaut batch-YYYYMMDD)",
    )
    parser.add_argument(
        "--min-fr-score",
        type=float,
        default=0.0,
        help="Plancher fr_score canal (défaut 0.0 = off ; le filtre France est au niveau message)",
    )
    parser.add_argument(
        "--min-claim-proximity",
        type=float,
        default=0.04,
        help="Seuil de proximité claim sous lequel un item part en screening (défaut 0.04)",
    )
    parser.add_argument(
        "--seed", type=int, default=42, help="Graine aléatoire (défaut 42)"
    )
    args = parser.parse_args()
    asyncio.run(
        main(
            n=args.n,
            batch_id=args.batch_id,
            min_fr_score=args.min_fr_score,
            min_claim_proximity=args.min_claim_proximity,
            seed=args.seed,
        )
    )
