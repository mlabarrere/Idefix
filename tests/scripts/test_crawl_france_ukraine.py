"""Pure tests for the France–Ukraine russophone acquisition campaign."""

import importlib.util
import sys
from pathlib import Path

import pytest

_SPEC = importlib.util.spec_from_file_location(
    "crawl_france_ukraine",
    Path(__file__).resolve().parents[2] / "scripts" / "crawl_france_ukraine.py",
)
campaign = importlib.util.module_from_spec(_SPEC)
assert _SPEC.loader is not None
sys.modules[_SPEC.name] = campaign
_SPEC.loader.exec_module(campaign)


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("Макрон: Франция продолжит поддержку Украины", True),
        ("France soutient l'Ukraine", False),  # no observable russophone context
        ("Франция обсуждает выборы", False),  # no Ukraine signal
        ("Украина обсуждает переговоры", False),  # no France signal
        (None, False),
    ],
)
def test_compound_observable_gate(text, expected):
    assert campaign.is_france_ukraine_cyrillic(text) is expected


def test_discovery_ranking_is_deterministic_and_capped():
    rows = [
        {"channel_id": 30, "username": "c", "title": None,
         "topic_forwards": 2, "distinct_relayers": 1},
        {"channel_id": 20, "username": "b", "title": "B",
         "topic_forwards": 3, "distinct_relayers": 1},
        {"channel_id": 10, "username": "a", "title": "A",
         "topic_forwards": 3, "distinct_relayers": 2},
    ]
    ranked = campaign.rank_discovery_rows(rows, cap=2)
    assert [r.username for r in ranked] == ["a", "b"]
    assert all(r.kind == "discover" for r in ranked)


def test_discovery_tie_breaks_on_stable_channel_id():
    rows = [
        {"channel_id": 20, "username": "later", "title": None,
         "topic_forwards": 1, "distinct_relayers": 1},
        {"channel_id": 10, "username": "first", "title": None,
         "topic_forwards": 1, "distinct_relayers": 1},
    ]
    assert [r.username for r in campaign.rank_discovery_rows(rows, 10)] == [
        "first", "later"
    ]


def test_empty_discovery_queue_is_valid():
    assert campaign.rank_discovery_rows([], cap=12) == []
