"""snapshot_store push/pull — AUCUN appel réseau.

``urllib.request.urlopen`` est monkeypatché par un fake in-memory : le push
enregistre le corps POST, le pull le rejoue. On vérifie (1) la dégradation
gracieuse quand SUPABASE_URL est absent et (2) le roundtrip sur les clés stables
(communities/stats), le scrub ne touchant pas ces clés non-secrètes.
"""
from __future__ import annotations

import io
import json

from src.shared import snapshot_store


def test_pull_returns_none_without_env(monkeypatch):
    monkeypatch.delenv("SUPABASE_URL", raising=False)
    monkeypatch.delenv("SUPABASE_KEY", raising=False)
    assert snapshot_store.pull_snapshot("m", "ls") is None


def test_push_pull_roundtrip(monkeypatch):
    monkeypatch.setenv("SUPABASE_URL", "https://fake.supabase.co")
    monkeypatch.setenv("SUPABASE_KEY", "service-role-key")

    store: dict = {}  # (mission, label_source) -> snapshot poussé

    def fake_urlopen(req, timeout=None):
        body = json.loads(req.data.decode()) if req.data else None
        if body is not None:  # POST (push) : on enregistre le snapshot scrubbé
            row = body[0]
            store[(row["mission"], row["label_source"])] = row["snapshot"]
            return io.BytesIO(b"")  # return=minimal -> corps vide
        # GET (pull) : on rejoue depuis l'URL (mission=eq.X&label_source=eq.Y)
        from urllib.parse import parse_qs, urlsplit
        q = parse_qs(urlsplit(req.full_url).query)
        snap = store.get((q["mission"][0].removeprefix("eq."),
                          q["label_source"][0].removeprefix("eq.")))
        rows = [{"snapshot": snap}] if snap is not None else []
        return io.BytesIO(json.dumps(rows).encode())

    # context-manager (with urlopen(...) as r): BytesIO supporte déjà __enter__/__exit__
    monkeypatch.setattr(snapshot_store.urllib.request, "urlopen", fake_urlopen)

    snapshot = {"communities": [{"id": 1, "size": 12}], "stats": {"n": 1}}
    snapshot_store.push_snapshot("ukraine", "louvain", snapshot)
    pulled = snapshot_store.pull_snapshot("ukraine", "louvain")

    assert pulled is not None
    assert pulled["communities"] == snapshot["communities"]
    assert pulled["stats"] == snapshot["stats"]


def test_pull_returns_none_on_empty_rows(monkeypatch):
    monkeypatch.setenv("SUPABASE_URL", "https://fake.supabase.co")
    monkeypatch.setenv("SUPABASE_KEY", "k")
    monkeypatch.setattr(snapshot_store.urllib.request, "urlopen",
                        lambda req, timeout=None: io.BytesIO(b"[]"))
    assert snapshot_store.pull_snapshot("absent", "louvain") is None
