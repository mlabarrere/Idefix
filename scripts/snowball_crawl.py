"""Bounded snowball frontier crawl (hop-N, multi-vagues) + France-relevance tagging.

Chaque vague : prend la frontière (canaux à username, pas encore backfillés, classés par
PROXIMITÉ-France inférée, cf. infra), les backfille (capés, jittered, FLOOD_WAIT géré par le
client). Entre les vagues, la frontière est re-interrogée → elle intègre les canaux découverts
à la vague précédente (capillarité en profondeur). À la fin, re-tag France (Axiome #1 : tag,
don't filter).

DIRIGER-France (graph-model §5.2) : la frontière brute classée par `in_fwd DESC` attrape
massivement l'appareil pro-RU NON-France (rendement anti-France ~2 %). On la DIRIGE vers la
France en ANCRANT l'expansion sur les GRAINES France déjà en base (cf. docstring de
_frontier_score) — pas par forwards entrants bruts, ni par une moyenne diluée.

ANCRAGE-France (décision Micky 2026-06-05) : la v1 dirigée classait par `relay_fr_mean`
(MOYENNE des fr_score des relayeurs). Sur données réelles le graphe est ~98 % appareil
non-France, donc la moyenne est diluée par les nombreux relayeurs fr≈0 (plafond observé
~0.06) et le classement retombe sur largeur+volume → toujours non-France. v2 : on ANCRE
l'expansion sur les graines France (relayeurs fr_score ≥ θ) et on classe par une CONTRIBUTION
qui NE SE DILUE PAS (somme saturée des fr_score des relayeurs). Un seul relayeur fortement
France suffit alors à remonter un candidat.

UN SEUL processus, SÉRIALISÉ (règle dure : jamais paralléliser MTProto). Lecture seule sauf
écritures DB d'ingestion. JAMAIS d'appel Telegram en --dry-run.

Usage :
    python scripts/snowball_crawl.py                      # 1 vague de 12
    python scripts/snowball_crawl.py --waves 3 --cap 20   # 3 vagues de 20 (capillarité profonde)
    python scripts/snowball_crawl.py --dry-run --cap 30   # classement frontière, AUCUN réseau
    python scripts/snowball_crawl.py --dry-run --anchor-threshold 0.2   # calibrer θ d'ancrage
"""
import argparse
import asyncio
import json
import random
import re

from dotenv import load_dotenv

from src.shared.db import db_connect

load_dotenv()

LIMIT = 150
from src.missions.russosphere import FR_KEYWORDS as FR_KW  # noqa: E402

# Seuil d'ancrage France par défaut : un relayeur est une « graine France » si fr_score ≥ θ.
# Réutilise le seuil "flagged" existant de _retag_france (fr>=0.15) — cohérence d'un bout à
# l'autre du pipeline. Surchargeable via --anchor-threshold pour calibration.
ANCHOR_THRESHOLD = 0.15

# --- Score d'ANCRAGE-France de la frontière (DIRIGER-France v2) ----------------------------
#
# Un canal candidat n'est pas encore backfillé : il n'a AUCUN message à lui, donc aucun
# fr_score direct. On INFÈRE sa pertinence-France depuis le graphe déjà en base, via les
# canaux backfillés qui le RELAIENT (= dont les messages le forwardent : une arête FORWARD
# origine→relayeur où le candidat est l'origine, graph-model §2.3.1).
#
# Hypothèse (graph-model §3.3) : un canal relayé par des relayeurs eux-mêmes France-pertinents
# est probablement plus France-pertinent. Le signal séparateur n'est pas la classe du candidat
# mais la composition-crédibilité de son voisinage FORWARD.
#
# POURQUOI PAS LA MOYENNE (v1 abandonnée). `relay_fr_mean` = avg(fr_score des relayeurs) se
# DILUE : le graphe étant ~98 % appareil non-France, un candidat relayé par 1 graine France@0.8
# ET 50 canaux non-France@0 obtient 0.8/51 ≈ 0.016. Sur données réelles la moyenne plafonne à
# ~0.06 et le tri retombe sur largeur+volume (toujours non-France). On veut l'inverse : qu'UN
# SEUL relayeur fortement France suffise à remonter le candidat. La moyenne ne peut pas le faire.
#
# Score composite EXPLICITE (NFR-8 — chaque composante justifiable) :
#
#     frontier_score = sat(relay_fr_sum, FR_SUM_REF)
#                      + W_BREADTH * sat(distinct_relayers, BREADTH_REF)
#                      + W_VOLUME  * sat(in_fwd,           VOLUME_REF)
#
#   avec  sat(x, ref) = log1p(x) / log1p(ref), clampé à [0,1]  — saturation bornée.
#
#   • sat(relay_fr_sum)    — SOMME des fr_score des relayeurs, saturée ∈ [0,1]. COMPOSANTE
#                            PRIMAIRE. La somme (≠ moyenne) NE SE DILUE PAS : ajouter des
#                            relayeurs non-France (fr≈0) n'abaisse pas le score ; ajouter une
#                            graine France (fr élevé) le monte. FR_SUM_REF fixe le point de
#                            saturation : un seul relayeur à fr≥~0.45 sature déjà ~80 % de la
#                            composante (cf. _sat), donc UNE graine France forte suffit à
#                            dominer tout candidat relayé seulement par l'appareil non-France.
#   • sat(distinct_relayers) — largeur du voisinage ∈ [0,1] : être relayé par PLUSIEURS canaux
#                            est plus probant qu'un relai unique (corrobore). DÉPARTAGE SECONDAIRE.
#                            Note : la corroboration "France" propre est portée par la somme ;
#                            cette composante reste un simple départage de largeur, borné.
#   • sat(in_fwd)          — SIGNAL SECONDAIRE ∈ [0,1] : volume de forwards entrants (départage,
#                            conserve l'utilité capillaire). Saturation → le volume brut ne peut
#                            pas écraser la proximité-France.
#
# Poids : la masse auxiliaire TOTALE (W_BREADTH + W_VOLUME = 0.30) est strictement < 1 = portée
# de la composante primaire saturée. Conséquence load-bearing : un candidat à somme-France
# saturée (composante primaire → 1) bat TOUJOURS un candidat à somme-France nulle (appareil
# non-France, fr≈0), quel que soit son volume/largeur → exactement l'inversion voulue. C'est la
# même garantie qu'en v1, mais sur la SOMME saturée (non diluable) au lieu de la moyenne.
#
# ANCRAGE (filtre dur optionnel, --anchor-threshold θ) : `france_relayers` = nombre de relayeurs
# distincts à fr_score ≥ θ. Quand θ>0 (défaut), la frontière ne retient que les candidats ANCRÉS
# (france_relayers ≥ 1) ; si l'ancrage vide la frontière, on RETOMBE proprement (warning) sur le
# tri global pour ne pas bloquer le crawl. Voir _rank_frontier.
W_BREADTH = 0.20
W_VOLUME = 0.10
FR_SUM_REF = 0.6    # somme fr_score des relayeurs → composante primaire saturée
BREADTH_REF = 8     # ~8 relayeurs distincts → composante largeur saturée
VOLUME_REF = 200    # ~200 forwards entrants → composante volume saturée

# Pour un candidat C (origine), on agrège ses relayeurs R (channels backfillés dont un message
# a forward_from_channel_id = C). On NE compte un relayeur que s'il a au moins un message en
# base (donc backfillé) : un relayeur sans message n'a pas de fr_score fiable.
#
# $1 = θ (seuil d'ancrage) : sert UNIQUEMENT à compter `france_relayers` (relayeurs fr≥θ) pour
# l'ancrage et la visibilité --dry-run. Le filtre dur d'ancrage est appliqué côté Python
# (_rank_frontier) pour garder le fallback propre si la frontière ancrée est vide.
_FRONTIER_Q = """
    WITH backfilled AS (SELECT DISTINCT channel_id FROM messages),
         relays AS (
            SELECT m.forward_from_channel_id AS cand_id,
                   m.channel_id              AS relayer_id,
                   count(*)                  AS n
            FROM messages m
            WHERE m.forward_from_channel_id IS NOT NULL
              -- exclure les self-loops (un canal qui se re-poste lui-même) : un canal n'est
              -- pas son propre relayeur. Cohérent avec build_graph.py (origin == reposter exclu).
              AND m.forward_from_channel_id <> m.channel_id
            GROUP BY m.forward_from_channel_id, m.channel_id
         ),
         -- fr_score par relayeur (un seul par relayeur, AVANT toute agrégation par candidat) :
         -- cast blindé — extra->>'fr_score' est du JSONB libre. Un ::float direct sur une valeur
         -- non numérique ferait ÉCHOUER toute la requête. On ne caste que les valeurs numériques
         -- bien formées ; sinon 0.0 (= relayeur non France-tagué).
         relays_fr AS (
            SELECT r.cand_id,
                   r.relayer_id,
                   r.n,
                   CASE
                     WHEN rc.extra->>'fr_score' ~ '^-?[0-9]+(\\.[0-9]+)?$'
                     THEN (rc.extra->>'fr_score')::float
                     ELSE 0.0
                   END AS relayer_fr
            FROM relays r
            JOIN channels rc ON rc.channel_id = r.relayer_id
            WHERE r.relayer_id IN (SELECT channel_id FROM backfilled)
         ),
         agg AS (
            SELECT cand_id,
                   count(DISTINCT relayer_id)                         AS distinct_relayers,
                   sum(n)                                             AS in_fwd,
                   -- SOMME (non diluable) des fr_score des relayeurs : composante primaire v2.
                   sum(relayer_fr)                                    AS relay_fr_sum,
                   -- ancrage : nombre de relayeurs distincts qui sont des graines France (fr≥θ).
                   count(DISTINCT relayer_id) FILTER (WHERE relayer_fr >= $1) AS france_relayers
            FROM relays_fr
            GROUP BY cand_id
         )
    SELECT c.channel_id,
           c.username,
           COALESCE(a.in_fwd, 0)             AS in_fwd,
           COALESCE(a.distinct_relayers, 0)  AS distinct_relayers,
           COALESCE(a.relay_fr_sum, 0.0)     AS relay_fr_sum,
           COALESCE(a.france_relayers, 0)    AS france_relayers
    FROM channels c
    LEFT JOIN agg a ON a.cand_id = c.channel_id
    WHERE c.username IS NOT NULL
      AND c.channel_id NOT IN (SELECT channel_id FROM backfilled)
"""


def _sat(x: float, ref: float) -> float:
    """Saturation bornée STRICTEMENT à [0,1] : log1p(x)/log1p(ref), clampée aux DEUX bouts.

    x<=0 → 0 ; x>=ref → 1. Le clamp haut (min 1.0) est LOAD-BEARING : sans lui, un candidat
    à très gros in_fwd/relayers ferait dépasser la masse auxiliaire au-delà de 0.30 et pourrait
    battre un candidat 100 %-France (relay_fr_mean=1) — exactement l'inversion que DIRIGER-France
    interdit. ref doit être > 0 (sinon log1p(ref)=0 → division ; les constantes du module le sont).
    """
    import math

    return max(0.0, min(1.0, math.log1p(max(x, 0.0)) / math.log1p(ref)))


def _frontier_score(relay_fr_sum: float, distinct_relayers: int, in_fwd: int) -> float:
    """Score composite d'ancrage-France d'un candidat de frontière (cf. en-tête module).

    sat(relay_fr_sum) est la composante primaire NON DILUABLE (somme saturée des fr_score des
    relayeurs) ; breadth (largeur du voisinage) et volume (in_fwd) sont des départages saturés
    bornés dont la masse totale (W_BREADTH+W_VOLUME=0.30) reste < 1 → la proximité-France prime
    toujours. La somme (≠ moyenne v1) garantit qu'UN SEUL relayeur fortement France remonte le
    candidat sans être dilué par l'appareil non-France.
    """
    return (
        _sat(float(relay_fr_sum), FR_SUM_REF)
        + W_BREADTH * _sat(distinct_relayers, BREADTH_REF)
        + W_VOLUME * _sat(in_fwd, VOLUME_REF)
    )


def _rank_frontier(rows, cap: int, anchor_threshold: float = 0.0):
    """Trie les lignes brutes de _FRONTIER_Q par score d'ancrage-France décroissant.

    Fonction pure (lignes simulées OK en test) : prend des mappings avec les clés
    relay_fr_sum / distinct_relayers / in_fwd / france_relayers / channel_id / username, renvoie
    la liste cappée d'objets enrichis d'un champ `score`. Départage stable : score, puis
    relay_fr_sum, puis in_fwd (déterministe).

    ANCRAGE (filtre dur). Si anchor_threshold > 0, on ne retient que les candidats ANCRÉS sur au
    moins une graine France (france_relayers >= 1, déjà compté côté SQL avec ce même θ). FILTRE
    DUR — pas un boost : sur un graphe ~98 % non-France, un boost laisserait le volume du gros
    appareil non-France remonter ; le filtre dur garantit qu'un candidat relayé UNIQUEMENT par
    l'appareil non-France ne peut PAS entrer dans la frontière, point. FALLBACK propre : si
    l'ancrage vide la frontière (aucun candidat ancré — graphe encore trop pauvre en France),
    on retombe sur le tri global non ancré (avec warning côté appelant) pour ne pas bloquer le
    crawl. Le booléen `anchored` renvoyé dit si l'ancrage a été effectivement appliqué.
    """
    def enrich(r):
        return {
            "channel_id": r["channel_id"],
            "username": r["username"],
            # SQL sum() → PostgreSQL numeric → asyncpg Decimal ; format `:d` la rejette
            # (« invalid format string »). count(DISTINCT) reste bigint→int. On normalise.
            "in_fwd": int(r["in_fwd"]),
            "distinct_relayers": int(r["distinct_relayers"]),
            "relay_fr_sum": float(r["relay_fr_sum"]),
            "france_relayers": int(r["france_relayers"]),
            "score": _frontier_score(
                r["relay_fr_sum"], r["distinct_relayers"], r["in_fwd"]),
        }

    scored = [enrich(r) for r in rows]
    anchored = False
    if anchor_threshold > 0:
        kept = [d for d in scored if d["france_relayers"] >= 1]
        if kept:
            scored = kept
            anchored = True
        # sinon : fallback silencieux ici (l'appelant émet le warning), scored inchangé.
    scored.sort(
        key=lambda d: (d["score"], d["relay_fr_sum"], d["in_fwd"]), reverse=True)
    return scored[:cap], anchored


async def _frontier(conn, cap: int, anchor_threshold: float = ANCHOR_THRESHOLD):
    rows = await conn.fetch(_FRONTIER_Q, anchor_threshold)
    ranked, anchored = _rank_frontier(rows, cap, anchor_threshold)
    if anchor_threshold > 0 and not anchored:
        print(f"  [warn] ancrage θ={anchor_threshold:.2f} : frontière ancrée VIDE "
              f"(aucun candidat relayé par une graine France) → fallback tri global non ancré.")
    return ranked


async def _run_wave(client, conn, cap: int, limit: int, wave: int,
                    anchor_threshold: float) -> int:
    from src.ingestor.handlers import backfill_channel

    frontier = await _frontier(conn, cap, anchor_threshold)
    print(f"\n--- Vague {wave} · frontière ancrée-France θ={anchor_threshold:.2f} "
          f"(cap {cap}) : {len(frontier)} canaux ---")
    done = 0
    for r in frontier:
        uname = "@" + r["username"]
        try:
            n = await backfill_channel(client, conn, uname, limit=limit)
            done += 1
            print(f"  {uname:24s} score={r['score']:.3f} "
                  f"frΣ={r['relay_fr_sum']:.3f} grainesFR={r['france_relayers']:<3d} "
                  f"relais={r['distinct_relayers']:<3d} in_fwd={r['in_fwd']:<3d} -> {n} msgs")
        except Exception as e:
            print(f"  {uname:24s} -> ERROR {type(e).__name__}: {str(e)[:40]}")
        await asyncio.sleep(random.uniform(2, 4))  # account hygiene (jitter)
    return done


async def _dry_run(conn, cap: int, anchor_threshold: float) -> None:
    """Imprime le classement de frontière SANS backfiller ni ouvrir de session Telegram."""
    frontier = await _frontier(conn, cap, anchor_threshold)
    print(f"\n=== --dry-run · classement frontière ancrée-France θ={anchor_threshold:.2f} "
          f"(cap {cap}) : {len(frontier)} canaux ===")
    print(f"  {'#':>3s}  {'canal':24s} {'score':>7s}  {'frΣ':>7s}  "
          f"{'grainesFR':>9s}  {'relais':>6s}  {'in_fwd':>6s}")
    for i, r in enumerate(frontier, 1):
        uname = "@" + r["username"]
        print(f"  {i:>3d}  {uname:24s} {r['score']:>7.3f}  {r['relay_fr_sum']:>7.3f}  "
              f"{r['france_relayers']:>9d}  {r['distinct_relayers']:>6d}  {r['in_fwd']:>6d}")
    print(f"\n  frΣ = somme (non diluée) des fr_score des relayeurs ; grainesFR = relayeurs "
          f"fr≥θ ({anchor_threshold:.2f}).")
    print("  (--dry-run : aucun backfill, aucune session Telegram ouverte.)")


async def _retag_france(conn) -> None:
    print("\n=== Tag pertinence-France (channels.extra.fr_score) ===")
    rows = await conn.fetch("SELECT channel_id, COALESCE(username,title) AS name FROM channels")
    pattern = "|".join(re.escape(k) for k in FR_KW)  # parameterized regex — apostrophe-safe
    tagged = []
    for r in rows:
        cid = r["channel_id"]
        total = await conn.fetchval("SELECT count(*) FROM messages WHERE channel_id=$1", cid)
        if not total:
            continue
        hits = await conn.fetchval(
            "SELECT count(*) FROM messages WHERE channel_id=$1 AND text ~* $2", cid, pattern)
        fr = round(hits / total, 3)
        await conn.execute("UPDATE channels SET extra = $2::jsonb WHERE channel_id=$1",
                           cid, json.dumps({"fr_score": fr, "msg_sampled": total}))
        tagged.append((r["name"], fr, total))
    flagged = sum(1 for _, fr, _ in tagged if fr >= 0.15)
    print(f"  {len(tagged)} canaux taggés · {flagged} France-pertinents (fr>=0.15)")


async def main(cap: int, waves: int, limit: int, dry_run: bool,
               anchor_threshold: float) -> None:
    conn = await db_connect()
    lock_acquired = False
    try:
        if dry_run:
            # Aucune instanciation du client Telegram, aucun réseau.
            await _dry_run(conn, cap, anchor_threshold)
            return

        from src.ingestor.client import TelegramClient
        from src.ingestor.run_lock import try_acquire_collector_lock

        lock_acquired = await try_acquire_collector_lock(conn)
        if not lock_acquired:
            print("Un autre collecteur Telegram est déjà actif -> arrêt.")
            return

        total_done = 0
        client = TelegramClient.from_env()
        async with client:
            for w in range(1, waves + 1):
                done = await _run_wave(client, conn, cap, limit, w, anchor_threshold)
                total_done += done
                if done == 0:
                    print("  (frontière vide — arrêt anticipé)")
                    break
        await _retag_france(conn)
        print(f"\nTerminé : {total_done} canaux backfillés sur {waves} vague(s).")
    finally:
        if lock_acquired:
            from src.ingestor.run_lock import release_collector_lock
            await release_collector_lock(conn)
        await conn.close()


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Snowball crawl multi-vagues (sérialisé).")
    ap.add_argument("--cap", type=int, default=12, help="Canaux backfillés par vague")
    ap.add_argument("--waves", type=int, default=1, help="Nombre de vagues séquentielles")
    ap.add_argument("--limit", type=int, default=LIMIT, help="Messages par canal")
    ap.add_argument("--anchor-threshold", type=float, default=ANCHOR_THRESHOLD,
                    help="Seuil θ d'ancrage France : ne retenir que les candidats relayés par "
                         "au moins une graine France (fr_score>=θ). 0 désactive l'ancrage "
                         f"(tri global). Défaut {ANCHOR_THRESHOLD}.")
    ap.add_argument("--dry-run", action="store_true",
                    help="Imprime le classement de frontière ancrée-France SANS backfiller "
                         "ni ouvrir de session Telegram (mode de revue du tri).")
    args = ap.parse_args()
    asyncio.run(main(cap=args.cap, waves=args.waves, limit=args.limit,
                     dry_run=args.dry_run, anchor_threshold=args.anchor_threshold))
