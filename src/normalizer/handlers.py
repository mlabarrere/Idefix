"""Normalizer — clean text, extract URLs, compute media fingerprints."""

import re
from urllib.parse import urlparse

import structlog

log = structlog.get_logger(__name__)

URL_RE = re.compile(r"https?://[^\s\)\]\"'>]+")
# Telegram usernames: 5–32 chars, must start with a letter, [A-Za-z0-9_].
# (?<![\w@/]) avoids matching e-mails (foo@bar) and t.me/@handle path fragments.
MENTION_RE = re.compile(r"(?<![\w@/])@([A-Za-z][A-Za-z0-9_]{3,31})")
# Hashtags: '#' + tag of Latin OR Cyrillic letters, digits, underscore.
# Multilingual on purpose (RU/FR adversary content mixes scripts). (?<![\w#])
# avoids matching mid-word '#' and '##' chains; the tag body excludes '#' so
# "#a#b" yields two tags. \w in re's default Unicode mode also matches accented
# Latin (é, à) which French hashtags use.
HASHTAG_RE = re.compile(
    r"(?<![\w#])#([A-Za-z0-9_À-ɏЀ-ӿ]+)"
)
# Hosts that are not adversary/source domains (link shorteners / platforms): keep
# them out of the CITES_DOMAIN signal noise. Extend as needed.
_PLATFORM_HOSTS = {
    # social / messaging platforms
    "t.me", "telegram.me", "telegram.org", "youtu.be", "youtube.com",
    "twitter.com", "x.com",
    # pure link shorteners (opaque — would need unshortening to be useful)
    "bit.ly", "tinyurl.com", "t.co", "cutt.ly", "linktr.ee", "ow.ly",
    "buff.ly", "goo.gl", "is.gd", "rb.gy", "lnkd.in",
}


def extract_urls(text: str | None) -> list[str]:
    """Extract and lightly canonicalize URLs from message text."""
    if not text:
        return []
    found = URL_RE.findall(text)
    canonical = []
    for url in found:
        url = url.rstrip(".,;:!?»«")  # strip trailing punctuation
        try:
            p = urlparse(url)
            canonical.append(f"{p.scheme}://{p.netloc}{p.path}")
        except Exception:
            canonical.append(url)
    return list(dict.fromkeys(canonical))


def canonical_domain(url: str) -> str | None:
    """Return the lowercased registrable host of a URL (www. stripped, port removed).

    NOTE: this is a heuristic netloc (e.g. 'sub.example.co.uk' stays as-is, not folded
    to 'example.co.uk'). A true registrable-domain fold would need tldextract / the
    public-suffix list — deferred; the netloc is enough to spot Pravda/Doppelganger hosts.
    """
    if not url:
        return None
    try:
        netloc = urlparse(url if "://" in url else f"http://{url}").netloc.lower()
    except Exception:
        return None
    netloc = netloc.split("@")[-1].split(":")[0]  # drop userinfo + port
    if netloc.startswith("www."):
        netloc = netloc[4:]
    return netloc or None


def extract_mentions(text: str | None) -> list[str]:
    """Extract @-mentioned usernames (lowercased, without the @). Deduplicated."""
    if not text:
        return []
    return list(dict.fromkeys(m.lower() for m in MENTION_RE.findall(text)))


def extract_hashtags(text: str | None) -> list[str]:
    """Extract #-hashtags (lowercased, without the #). Deduplicated.

    Multilingual: matches Latin (incl. accented) AND Cyrillic letters, digits and
    underscore (RU/FR adversary content mixes scripts). Tags shorter than 2 chars
    are dropped (a lone "#a" carries no coordination signal). Order-preserving
    dedup, mirroring ``extract_mentions``.
    """
    if not text:
        return []
    tags = (m.lower() for m in HASHTAG_RE.findall(text))
    return list(dict.fromkeys(t for t in tags if len(t) >= 2))


def is_platform_host(domain: str | None) -> bool:
    """True for link-shorteners / big platforms we exclude from the adversary signal."""
    return bool(domain) and domain in _PLATFORM_HOSTS


def clean_text(text: str | None) -> str | None:
    """Strip Telegram formatting entities from text."""
    if not text:
        return None
    # Remove markdown-style formatting
    text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)
    text = re.sub(r"__(.+?)__", r"\1", text)
    return text.strip() or None


def detect_language(text: str | None) -> str | None:
    """Detect language of text. Returns ISO 639-1 code or None.

    LEGACY / UNUSED (2026-06-08): not wired into the pipeline; the `langdetect`
    dependency was removed. France-targeting uses a multilingual lexicon, not
    language detection. The lazy import below degrades to None if absent.
    """
    if not text or len(text) < 20:
        return None
    try:
        from langdetect import detect
        return detect(text)
    except Exception:
        return None


def compute_media_hash(file_path: str) -> str | None:
    """Compute perceptual hash for images. Returns hex string or None.

    LEGACY / UNUSED (2026-06-08): not wired into the pipeline; the `imagehash`
    dependency was removed. Media-reuse edges key on Telegram's `file_unique_id`
    (see _parse_message), not pHash. The lazy import below degrades to None.
    """
    try:
        import imagehash
        from PIL import Image
        img = Image.open(file_path)
        return str(imagehash.phash(img))
    except Exception:
        return None
