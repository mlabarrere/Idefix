"""Tests for text-derived edge extractors (mentions / URLs / domains)."""

from src.normalizer.handlers import (
    canonical_domain,
    extract_hashtags,
    extract_mentions,
    extract_urls,
    is_platform_host,
)


class TestMentions:
    def test_basic(self):
        assert extract_mentions("Relayé par @Dugin_Aleksandr et @geopolitika_fr") == [
            "dugin_aleksandr",
            "geopolitika_fr",
        ]

    def test_lowercased_and_deduped(self):
        assert extract_mentions("@RFI_Fr @rfi_fr @RFI_FR") == ["rfi_fr"]

    def test_ignores_emails(self):
        assert extract_mentions("écrire à contact@example.com") == []

    def test_ignores_tme_path(self):
        # t.me/@handle path fragment must not be picked up as a mention
        assert extract_mentions("https://t.me/@somechannel voir ici") == []

    def test_min_length(self):
        # usernames are >=5 chars (letter + >=4) — @abc is too short
        assert extract_mentions("@abc trop court, @abcd ok") == ["abcd"]

    def test_empty(self):
        assert extract_mentions("") == []
        assert extract_mentions(None) == []


class TestHashtags:
    def test_latin_and_cyrillic(self):
        # Latin and Cyrillic tags both captured, lowercased, in order.
        assert extract_hashtags("Soutenez #France2027 et #Новости #Україна") == [
            "france2027",
            "новости",
            "україна",
        ]

    def test_lowercased_and_deduped(self):
        assert extract_hashtags("#Macron #macron #MACRON") == ["macron"]

    def test_accented_latin_kept(self):
        # French hashtags use accents (\w matches é/à in Unicode mode).
        assert extract_hashtags("#élection au #café") == ["élection", "café"]

    def test_min_length_two(self):
        # a lone single char carries no signal -> dropped; 2 chars kept.
        assert extract_hashtags("#a court, #ok gardé, #1 dropped, #ru kept") == [
            "ok",
            "ru",
        ]

    def test_underscore_and_digits(self):
        assert extract_hashtags("#stop_otan #plan_2027") == ["stop_otan", "plan_2027"]

    def test_empty(self):
        assert extract_hashtags("") == []
        assert extract_hashtags(None) == []
        assert extract_hashtags("aucun hashtag ici") == []


class TestUrls:
    def test_extract_and_strip_trailing_punct(self):
        urls = extract_urls("Voir https://factuel.afp.com/article-123. Et https://pravda-fr.com/x")
        assert "https://factuel.afp.com/article-123" in urls
        assert "https://pravda-fr.com/x" in urls

    def test_dedup(self):
        assert len(extract_urls("https://a.com/x https://a.com/x")) == 1

    def test_empty(self):
        assert extract_urls(None) == []


class TestCanonicalDomain:
    def test_strip_www_and_lowercase(self):
        assert canonical_domain("https://WWW.Pravda-FR.com/article") == "pravda-fr.com"

    def test_drop_port_and_userinfo(self):
        assert canonical_domain("http://user@host.example:8080/p") == "host.example"

    def test_bare_domain(self):
        assert canonical_domain("rrn.world/path") == "rrn.world"

    def test_subdomain_kept(self):
        assert canonical_domain("https://factuel.afp.com/x") == "factuel.afp.com"

    def test_empty(self):
        assert canonical_domain("") is None


class TestPlatformHost:
    def test_known_platforms(self):
        assert is_platform_host("t.me") is True
        assert is_platform_host("youtube.com") is True

    def test_real_source_not_platform(self):
        assert is_platform_host("pravda-fr.com") is False
        assert is_platform_host(None) is False
