r"""Démon de backfill CADENCÉ (48h) — remplit les coquilles cataloguées-mais-vides.

> Contexte (Micky, 2026-06-06) : l'ordinateur reste allumé ; ce démon récupère la
> data en continu, EN PRENANT SON TEMPS, pile sous la limite tolérée, pour ne
> JAMAIS faire bannir le compte +33 (compte PERSONNEL et établi).

SÛRETÉ (load-bearing) :
  * SÉRIALISÉ, un seul compte, un seul process. JAMAIS parallélisé (ban-cascade,
    risque #5). Aucun sous-agent ne touche MTProto.
  * LECTURE SEULE : lit l'historique de canaux PUBLICS et écrit dans NOTRE base.
    Aucun envoi, aucun join (get_chat_history ne rejoint pas le canal).
  * MASSIVEMENT sous les limites : Telegram garde ses seuils SECRETS (volontaire-
    ment) ; le seul signal fiable est le FLOOD_WAIT. On cadence très large (pause
    jittée de plusieurs minutes entre canaux) et on RALENTIT ENCORE plus à la
    moindre pression. Compte ancien + lecture polie = profil le plus sûr (sources
    : core.telegram.org/mtproto ; docs Telethon/Pyrogram — « hitting limits ne
    bannit pas ; les ignorer, oui »).
  * ADAPTATIF sans toucher au client : on mesure le temps par canal ; s'il
    explose (le client a dormi sur un FLOOD_WAIT), on augmente l'écart ; sinon on
    le détend doucement vers la base.
  * REPRENABLE : re-interroge les canaux non-backfillés à chaque cycle ; dédup par
    ON CONFLICT à l'insert. Arrêt propre via fichier sentinelle, plafond horaire,
    ou épuisement de la liste.

Lancement DÉTACHÉ (survit à la session ; laisser le PC allumé) — PowerShell :
    $env:PYTHONUTF8="1"; $env:PYTHONPATH="."
    Start-Process -WindowStyle Hidden .\.venv\Scripts\python.exe `
      -ArgumentList "scripts/paced_backfill.py" `
      -RedirectStandardOutput logs\backfill.out -RedirectStandardError logs\backfill.err

Arrêt propre :  New-Item scripts\.stop_backfill        (le démon s'arrête au canal suivant)
Suivi        :  Get-Content logs\backfill.out -Wait -Tail 20

Usage (réglages par défaut prudents) :
    python scripts/paced_backfill.py [--limit 300] [--min-gap 90] [--max-gap 150]
                                     [--max-hours 48] [--max-channels N]
"""
import argparse
import asyncio
import random
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv  # noqa: E402

load_dotenv()

from src.ingestor.client import TelegramClient  # noqa: E402
from src.ingestor.handlers import backfill_channel  # noqa: E402
from src.ingestor.run_lock import (  # noqa: E402
    release_collector_lock,
    try_acquire_collector_lock,
)
from src.shared.db import db_connect  # noqa: E402

STOP_FILE = ROOT / "scripts" / ".stop_backfill"

# Sous ce temps (s), un backfill s'est passé sans pression -> on détend l'écart.
# Au-dessus, le client a probablement dormi sur un FLOOD_WAIT -> on ralentit.
_PRESSURE_SECONDS = 45.0
_GAP_CAP = 900.0  # plafond d'écart adaptatif (15 min) : on ne se fige jamais

# Drapeaux Windows SetThreadExecutionState (anti-veille) — cf. _prevent_sleep().
_ES_CONTINUOUS = 0x80000000
_ES_SYSTEM_REQUIRED = 0x00000001


# Coquilles à remplir : 0 message, un username résolvable. Les plus CONNECTÉES
# d'abord (référencées par forward/mention) = meilleur ROI si 48h ne suffit pas.
_NEXT_Q = """
    SELECT c.channel_id, c.username,
           COALESCE(r.refs, 0) AS refs
    FROM channels c
    LEFT JOIN (
        SELECT dst_channel_id, COUNT(*) AS refs
        FROM edges
        WHERE dst_channel_id IS NOT NULL AND edge_type IN ('FORWARD', 'MENTIONS')
        GROUP BY dst_channel_id
    ) r ON r.dst_channel_id = c.channel_id
    WHERE c.username IS NOT NULL AND c.username <> ''
      AND NOT EXISTS (SELECT 1 FROM messages m WHERE m.channel_id = c.channel_id)
    ORDER BY refs DESC, c.channel_id
    LIMIT $1
"""


async def _next_channels(conn, batch: int) -> list:
    return await conn.fetch(_NEXT_Q, batch)


def _now() -> float:
    return time.monotonic()


def _prevent_sleep():
    """Empêche la VEILLE Windows tant que le crawl tourne (le PC local doit rester
    éveillé pour grinder 48 h). ``SetThreadExecutionState(ES_CONTINUOUS |
    ES_SYSTEM_REQUIRED)`` garde le SYSTÈME éveillé sans forcer l'écran allumé
    (pas de ES_DISPLAY_REQUIRED → l'écran peut s'éteindre). Renvoie un callable de
    libération (réinitialise à ES_CONTINUOUS). No-op hors Windows.
    Réf. core Windows API ; cf. lib `wakepy` qui fait pareil.
    """
    if sys.platform != "win32":
        return lambda: None
    import ctypes

    k = ctypes.windll.kernel32
    k.SetThreadExecutionState(_ES_CONTINUOUS | _ES_SYSTEM_REQUIRED)

    def _release():
        k.SetThreadExecutionState(_ES_CONTINUOUS)

    return _release


async def main(
    *, limit: int, min_gap: float, max_gap: float, max_hours: float,
    max_channels: int | None, batch: int,
) -> None:
    conn = await db_connect()
    lock_acquired = await try_acquire_collector_lock(conn)
    if not lock_acquired:
        print("[paced_backfill] autre collecteur Telegram actif -> arrêt.", flush=True)
        await conn.close()
        return
    client = TelegramClient.from_env()
    release_sleep = _prevent_sleep()  # garde le PC éveillé pendant le crawl

    started = _now()
    deadline = started + max_hours * 3600
    gap = min_gap            # écart adaptatif courant
    done = 0
    inserted_total = 0
    floods = 0

    remaining = await conn.fetchval(
        "SELECT COUNT(*) FROM channels c WHERE c.username IS NOT NULL AND c.username<>'' "
        "AND NOT EXISTS (SELECT 1 FROM messages m WHERE m.channel_id=c.channel_id)"
    )
    print(
        f"[paced_backfill] démarrage · {remaining} coquilles résolvables · "
        f"limit={limit} msg/canal · écart {min_gap:.0f}-{max_gap:.0f}s (adaptatif) · "
        f"plafond {max_hours:.0f}h · lecture seule, sérialisé.",
        flush=True,
    )

    try:
        async with client:
            while True:
                if STOP_FILE.exists():
                    print("[paced_backfill] STOP sentinelle -> arrêt propre.", flush=True)
                    break
                if _now() >= deadline:
                    print("[paced_backfill] plafond horaire atteint -> arrêt.", flush=True)
                    break
                if max_channels is not None and done >= max_channels:
                    print(f"[paced_backfill] max-channels={max_channels} atteint.", flush=True)
                    break

                rows = await _next_channels(conn, batch)
                if not rows:
                    print("[paced_backfill] plus de coquilles -> terminé.", flush=True)
                    break

                for row in rows:
                    if STOP_FILE.exists() or _now() >= deadline:
                        break
                    if max_channels is not None and done >= max_channels:
                        break

                    uname = row["username"]
                    t0 = _now()
                    try:
                        n = await backfill_channel(client, conn, "@" + uname, limit=limit)
                    except Exception as e:  # noqa: BLE001 — un canal mort ne tue pas le run
                        n = 0
                        print(f"[paced_backfill] !! @{uname} échec: {e}", flush=True)
                    elapsed = _now() - t0
                    done += 1
                    inserted_total += n

                    # Adaptatif : pression détectée si le canal a traîné (FLOOD_WAIT
                    # interne au client) -> on élargit ; sinon on détend vers la base.
                    if elapsed > _PRESSURE_SECONDS:
                        floods += 1
                        gap = min(_GAP_CAP, gap * 1.5)
                        tag = f"⟂ pression ({elapsed:.0f}s) -> écart {gap:.0f}s"
                    else:
                        gap = max(min_gap, gap * 0.97)
                        tag = ""

                    h = (_now() - started) / 3600
                    print(
                        f"[paced_backfill] {done:>4} @{uname:<24} +{n:>3} msg · "
                        f"{elapsed:>4.0f}s · total {inserted_total} · {h:.1f}h {tag}",
                        flush=True,
                    )

                    # Pause cadencée (jittée, humaine) AVANT le canal suivant.
                    sleep_s = random.uniform(gap, max(gap, max_gap))
                    await asyncio.sleep(sleep_s)
    finally:
        release_sleep()  # rend la main à la gestion d'énergie normale
        await release_collector_lock(conn)
        await conn.close()

    h = (_now() - started) / 3600
    print(
        f"[paced_backfill] FIN · {done} canaux · {inserted_total} messages · "
        f"{floods} épisodes de pression · {h:.1f}h.",
        flush=True,
    )


if __name__ == "__main__":
    ap = argparse.ArgumentParser(
        description="Backfill cadencé 48h des coquilles (sérialisé, lecture seule)."
    )
    ap.add_argument("--limit", type=int, default=300, help="Messages par canal")
    ap.add_argument("--min-gap", type=float, default=90.0, help="Écart min entre canaux (s)")
    ap.add_argument("--max-gap", type=float, default=150.0, help="Écart max entre canaux (s)")
    ap.add_argument("--max-hours", type=float, default=48.0, help="Plafond de durée (h)")
    ap.add_argument("--max-channels", type=int, default=None, help="Plafond de canaux (test)")
    ap.add_argument("--batch", type=int, default=50, help="Canaux récupérés par cycle DB")
    args = ap.parse_args()
    asyncio.run(main(
        limit=args.limit, min_gap=args.min_gap, max_gap=args.max_gap,
        max_hours=args.max_hours, max_channels=args.max_channels, batch=args.batch,
    ))
