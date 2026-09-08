"""Tests for _parse_message media capture — OFFLINE (no DB, no Telegram).

Hydrogram Message objects are simulated with plain stand-ins exposing only the
attributes _parse_message reads. The load-bearing new behaviour: media_hash is
now filled from the media object's file_unique_id (no download), and stays None
when there is no media.
"""
from datetime import datetime, timezone

from src.ingestor.handlers import _parse_message

T0 = datetime(2026, 6, 1, 12, 0, 0, tzinfo=timezone.utc)


class _Media:
    """Stand-in for a Hydrogram media object (photo/video/document/...)."""

    def __init__(self, file_unique_id):
        self.file_unique_id = file_unique_id


class _Msg:
    """Minimal Hydrogram Message stand-in. Absent media attrs default to None."""

    def __init__(self, *, mid=1, date=T0, text=None, caption=None, **media):
        self.id = mid
        self.date = date
        self.text = text
        self.caption = caption
        # every media kind _parse_message probes — default None unless provided
        for attr in ("photo", "video", "document", "animation", "audio", "voice"):
            setattr(self, attr, media.get(attr))


class TestMediaHash:
    def test_photo_file_unique_id_captured(self):
        msg = _Msg(photo=_Media("AQADphoto123"))
        parsed = _parse_message(msg, channel_id=100)
        assert parsed["media_type"] == "photo"
        assert parsed["media_hash"] == "AQADphoto123"

    def test_video_captured(self):
        parsed = _parse_message(_Msg(video=_Media("VIDuid")), channel_id=100)
        assert parsed["media_type"] == "video"
        assert parsed["media_hash"] == "VIDuid"

    def test_document_animation_audio_voice_each_captured(self):
        cases = {
            "document": "DOCuid",
            "animation": "ANIuid",
            "audio": "AUDuid",
            "voice": "VOIuid",
        }
        for attr, uid in cases.items():
            parsed = _parse_message(_Msg(**{attr: _Media(uid)}), channel_id=100)
            assert parsed["media_type"] == attr
            assert parsed["media_hash"] == uid

    def test_no_media_hash_is_none(self):
        parsed = _parse_message(_Msg(text="texte sans média"), channel_id=100)
        assert parsed["media_type"] is None
        assert parsed["media_hash"] is None

    def test_photo_wins_over_later_kinds(self):
        # A message carrying several media attrs: probe order is photo-first.
        msg = _Msg(photo=_Media("PHOTOuid"), document=_Media("DOCuid"))
        parsed = _parse_message(msg, channel_id=100)
        assert parsed["media_type"] == "photo"
        assert parsed["media_hash"] == "PHOTOuid"

    def test_media_without_file_unique_id_yields_none_hash(self):
        # Defensive: a media object missing file_unique_id still classifies the
        # type but stores no hash (rather than crashing).
        class _Bare:
            pass

        msg = _Msg(video=_Bare())
        parsed = _parse_message(msg, channel_id=100)
        assert parsed["media_type"] == "video"
        assert parsed["media_hash"] is None
