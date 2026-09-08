"""Push d'un snapshot communautés vers Supabase (REST, service-role).

Source de vérité = table ``public.community_snapshots`` (mission, label_source,
snapshot jsonb). Le clustering (ici) PUSH ; le build Vercel PULL (prebuild Node,
``webapp/scripts/pull-snapshots.mjs``). Le navigateur ne touche jamais la DB —
durcissement RLS conservé (service-role seul). Le scrub canonique est appliqué
AU PUSH : ce qui entre en base est déjà public-safe.

AURA bloque le wire-protocol PostgreSQL (5432/6543) ; on passe par REST (443).
Identifiants lus depuis l'env (``SUPABASE_URL`` + ``SUPABASE_KEY`` service-role).
"""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.request


def push_snapshot(mission: str, label_source: str, snapshot: dict) -> None:
    """Upsert (mission, label_source) -> snapshot scrubbé. Lève sur erreur HTTP."""
    from src.shared.scrub import scrub  # ponytail: lazy import, pull_snapshot n'en a pas besoin
    key = os.environ["SUPABASE_KEY"]  # service-role (bypasse RLS)
    base = os.environ["SUPABASE_URL"].rstrip("/")
    body = json.dumps(
        [{"mission": mission, "label_source": label_source, "snapshot": scrub(snapshot)}]
    ).encode("utf-8")
    # on_conflict + merge-duplicates = UPSERT sur la PK (mission, label_source).
    req = urllib.request.Request(
        f"{base}/rest/v1/community_snapshots?on_conflict=mission,label_source",
        data=body,
        headers={
            "apikey": key,
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
            "Prefer": "resolution=merge-duplicates,return=minimal",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=60):
        pass


def pull_snapshot(mission: str, label_source: str) -> dict | None:
    """Fetch snapshot via REST. Renvoie le payload ou None (404 ou SUPABASE_* absent)."""
    base = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_KEY")
    if not base or not key:
        return None  # ponytail: graceful degradation
    url = (f"{base.rstrip('/')}/rest/v1/community_snapshots?"
           f"mission=eq.{mission}&label_source=eq.{label_source}")
    req = urllib.request.Request(url, headers={"apikey": key, "Authorization": f"Bearer {key}"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            rows = json.loads(r.read().decode())
        return rows[0]["snapshot"] if rows else None
    except urllib.error.HTTPError:
        return None
