"""Smoke test for alembic/versions/0006 — OFFLINE (no DB, no alembic run)."""
import importlib.util
from pathlib import Path

_MIG_PATH = (
    Path(__file__).resolve().parents[2]
    / "alembic"
    / "versions"
    / "0006_mission_composite_pk.py"
)


def _load_migration(monkeypatch):
    recorded: list[str] = []
    import alembic.op as op_mod

    monkeypatch.setattr(op_mod, "execute", lambda stmt: recorded.append(str(stmt)))
    spec = importlib.util.spec_from_file_location("mig_0006", _MIG_PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod, recorded


def test_revision_chain(monkeypatch):
    mod, _ = _load_migration(monkeypatch)
    assert mod.revision == "0006"
    assert mod.down_revision == "0005"


def test_upgrade_sets_composite_pks(monkeypatch):
    mod, recorded = _load_migration(monkeypatch)
    mod.upgrade()
    joined = "\n".join(recorded)
    assert "PRIMARY KEY (mission, channel_id)" in joined
    assert "PRIMARY KEY (mission)" in joined
    # vieille PK retirée avant la nouvelle (DROP IF EXISTS)
    assert "DROP CONSTRAINT IF EXISTS channel_scores_pkey" in joined
    assert "DROP CONSTRAINT IF EXISTS scores_run_meta_pkey" in joined


def test_downgrade_reverts_pks(monkeypatch):
    mod, recorded = _load_migration(monkeypatch)
    mod.downgrade()
    joined = "\n".join(recorded)
    assert "PRIMARY KEY (channel_id)" in joined
    assert "PRIMARY KEY (id)" in joined
