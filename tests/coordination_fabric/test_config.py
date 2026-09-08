import pytest

from src.coordination_fabric.config import (
    DEFAULT_COORDINATION_WINDOW_SECONDS,
    active_signals,
    reserved_signals,
    signal_by_type,
)


def test_active_signals_match_materialized_edge_families():
    # TEXT_SIM / TRANSLATION activated with the local-embeddings track (Lot C).
    assert {s.edge_type for s in active_signals()} == {
        "CO_FORWARD",
        "CO_URL",
        "CO_URL_EXACT",
        "CO_HASHTAG",
        "TEXT_SIM",
        "TRANSLATION",
    }


def test_text_sim_signals_carry_calibration_thresholds():
    assert signal_by_type("TEXT_SIM").threshold == 0.715
    assert signal_by_type("TRANSLATION").threshold == 0.85
    assert signal_by_type("TEXT_SIM").evidence_field == "text_embedding"


def test_reserved_signals_include_copypasta_and_media_future_work():
    reserved = {s.edge_type: s for s in reserved_signals()}

    assert reserved["COPYPASTA"].threshold == 0.693
    assert reserved["MEDIA_REUSE"].evidence_field == "media_hash"
    # TEXT_SIM / TRANSLATION are no longer reserved (now active).
    assert "TEXT_SIM" not in reserved
    assert "TRANSLATION" not in reserved


def test_all_windowed_signals_use_72h_default():
    for signal in active_signals() + reserved_signals():
        assert signal.default_window_seconds == DEFAULT_COORDINATION_WINDOW_SECONDS


def test_signal_lookup_is_case_insensitive():
    assert signal_by_type("co_url_exact").edge_type == "CO_URL_EXACT"


def test_unknown_signal_raises_key_error():
    with pytest.raises(KeyError):
        signal_by_type("unknown")
