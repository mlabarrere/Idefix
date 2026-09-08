"""Client Mistral async — SDK officiel + déterminisme, cache offline, secret-safe.

Wrapper autour du **SDK officiel ``mistralai``** (transport/auth/retry/parsing gérés
en amont) qui AJOUTE ce que le SDK n'a pas, pour la PISTE PARALLÈLE
(cf. ``src/llm/__init__``) :

- **Déterminisme** (repro/EIP) : ``temperature=0.0`` + ``random_seed`` fixe ; le
  ``request_hash`` (sha256 de l'entrée) est la clé de cache déterministe.
- **Cache offline** (``data/llm_cache/<hash>.json``) : un hit court-circuite le
  réseau (coût 0) → re-runs gratuits et reproductibles.
- **Secret-safe** : le SDK pose l'en-tête ``Authorization`` en interne ; la clé
  n'est jamais journalisée, jamais écrite dans le cache, jamais dans ``MistralResult``.
- **Comptabilité coût** + ``--budget`` (token-bucket ``rps`` côté client) ;
  retry/backoff 429/5xx **délégué au SDK** (``RetryConfig``).
- **Mockable** : ``transport=`` injecte un ``httpx.MockTransport`` (passé en
  ``async_client`` au SDK) → tests hors-ligne.

``mistralai``/``httpx`` sont importés en LAZY (uniquement à l'ouverture du client) :
importer ce module ne requiert pas l'extra ``llm``.
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import structlog

from src.llm.prompts import PROMPT_VERSION

log = structlog.get_logger(__name__)

DEFAULT_MODEL = "mistral-large-latest"
# server_url du SDK (le SDK ajoute ``/v1/chat/completions``).
DEFAULT_API_BASE = "https://api.mistral.ai"
_DEFAULT_CACHE_DIR = Path(__file__).resolve().parents[2] / "data" / "llm_cache"

# Tarifs estimatifs (USD / 1K tokens) — (input, output). Valeurs indicatives pour
# la comptabilité de coût ; à ajuster si la grille Mistral évolue. Le coût réel est
# facturé par Mistral ; ici on ESTIME pour piloter --budget-usd et le report d'éval.
_PRICE_PER_1K: dict[str, tuple[float, float]] = {
    "mistral-large-latest": (0.002, 0.006),
    "mistral-medium-latest": (0.0009, 0.0028),
    "mistral-small-latest": (0.0002, 0.0006),
}


class MistralError(RuntimeError):
    """Erreur d'appel Mistral (config manquante, échec après retries, 4xx)."""


def resolve_api_key() -> str | None:
    """Clé API depuis l'environnement (jamais loggée). ``None`` si absente."""
    return os.environ.get("MISTRAL_API_KEY") or None


def resolve_model() -> str:
    return os.environ.get("MISTRAL_MODEL") or DEFAULT_MODEL


def _price_for(model: str) -> tuple[float, float]:
    # Repli sur la grille "large" si le modèle exact n'est pas tabulé.
    return _PRICE_PER_1K.get(model, _PRICE_PER_1K[DEFAULT_MODEL])


@dataclass(frozen=True)
class MistralUsage:
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    est_cost_usd: float = 0.0

    def __add__(self, other: "MistralUsage") -> "MistralUsage":
        return MistralUsage(
            self.prompt_tokens + other.prompt_tokens,
            self.completion_tokens + other.completion_tokens,
            self.total_tokens + other.total_tokens,
            round(self.est_cost_usd + other.est_cost_usd, 6),
        )


@dataclass(frozen=True)
class MistralResult:
    content: str
    parsed: dict | None
    model: str
    prompt_version: str
    usage: MistralUsage
    cache_hit: bool
    request_hash: str


def _request_hash(
    *, model: str, system: str, user: str, json_mode: bool,
    schema: dict | None, temperature: float, seed: int | None,
) -> str:
    payload = json.dumps(
        {
            "model": model,
            "prompt_version": PROMPT_VERSION,
            "system": system,
            "user": user,
            "json_mode": json_mode,
            "schema": schema,
            "temperature": temperature,
            "seed": seed,
        },
        sort_keys=True,
        ensure_ascii=False,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


class _RateLimiter:
    """Token-bucket async simple, ``rps`` requêtes/seconde en régime établi."""

    def __init__(self, rps: float) -> None:
        self._min_interval = 1.0 / rps if rps > 0 else 0.0
        self._last = 0.0
        self._lock = asyncio.Lock()

    async def acquire(self) -> None:
        if self._min_interval <= 0:
            return
        async with self._lock:
            now = time.monotonic()
            wait = self._min_interval - (now - self._last)
            if wait > 0:
                await asyncio.sleep(wait)
            self._last = time.monotonic()


class MistralClient:
    """Client async. Usage : ``async with MistralClient() as c: await c.complete(...)``."""

    def __init__(
        self,
        *,
        model: str | None = None,
        api_key: str | None = None,
        api_base: str | None = None,
        cache_dir: Path | None = None,
        timeout_s: float = 60.0,
        rps: float = 2.0,
        transport: Any | None = None,
    ) -> None:
        self.model = model or resolve_model()
        self._api_key = api_key if api_key is not None else resolve_api_key()
        base = api_base or os.environ.get("MISTRAL_API_BASE") or DEFAULT_API_BASE
        self._api_base = base.rstrip("/")
        self.cache_dir = Path(cache_dir) if cache_dir else _DEFAULT_CACHE_DIR
        self.timeout_s = timeout_s
        self._limiter = _RateLimiter(rps)
        self._transport = transport
        self._sdk: Any | None = None
        self._owned_httpx: Any | None = None
        self.totals = MistralUsage()

    # ── cycle de vie ──
    async def __aenter__(self) -> "MistralClient":
        # Imports LAZY : n'exigent l'extra ``llm`` qu'à l'ouverture réelle.
        import httpx
        from mistralai import Mistral
        from mistralai.utils import BackoffStrategy, RetryConfig

        # Retry 429/5xx délégué au SDK (backoff exponentiel + erreurs réseau).
        retry = RetryConfig(
            "backoff",
            BackoffStrategy(
                initial_interval=500, max_interval=30000,
                exponent=1.5, max_elapsed_time=int(self.timeout_s * 1000) + 60000,
            ),
            retry_connection_errors=True,
        )
        # En test, ``transport`` injecte un MockTransport via un async_client httpx.
        if self._transport is not None:
            self._owned_httpx = httpx.AsyncClient(transport=self._transport)
        self._sdk = Mistral(
            api_key=self._api_key or "",
            server_url=self._api_base,
            async_client=self._owned_httpx,
            retry_config=retry,
            timeout_ms=int(self.timeout_s * 1000),
        )
        return self

    async def __aexit__(self, *exc: object) -> None:
        if self._sdk is not None:
            close = getattr(self._sdk, "__aexit__", None)
            if close is not None:
                try:
                    await close(None, None, None)
                except Exception:  # pragma: no cover - fermeture best-effort
                    pass
            self._sdk = None
        if self._owned_httpx is not None:
            await self._owned_httpx.aclose()
            self._owned_httpx = None

    # ── cache ──
    def _cache_path(self, request_hash: str) -> Path:
        return self.cache_dir / f"{request_hash}.json"

    def _read_cache(self, request_hash: str) -> dict | None:
        p = self._cache_path(request_hash)
        if not p.exists():
            return None
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return None

    def _write_cache(self, request_hash: str, record: dict) -> None:
        # Le cache NE CONTIENT JAMAIS la clé API (record = content/usage/model only).
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self._cache_path(request_hash).write_text(
            json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    # ── appel ──
    async def complete(
        self,
        *,
        system: str,
        user: str,
        json_mode: bool = True,
        schema: dict | None = None,
        temperature: float = 0.0,
        seed: int | None = 12345,
        cache: bool = True,
    ) -> MistralResult:
        rh = _request_hash(
            model=self.model, system=system, user=user, json_mode=json_mode,
            schema=schema, temperature=temperature, seed=seed,
        )

        if cache:
            cached = self._read_cache(rh)
            if cached is not None:
                usage = MistralUsage(**cached.get("usage", {}))
                # un hit compte les tokens mais coûte 0 (déjà facturé/local).
                self.totals = self.totals + MistralUsage(
                    usage.prompt_tokens, usage.completion_tokens, usage.total_tokens, 0.0
                )
                content = cached.get("content", "")
                log.info("mistral_cache_hit", request_hash=rh, model=self.model)
                return MistralResult(
                    content=content,
                    parsed=_safe_json(content) if json_mode else None,
                    model=cached.get("model", self.model),
                    prompt_version=cached.get("prompt_version", PROMPT_VERSION),
                    usage=usage,
                    cache_hit=True,
                    request_hash=rh,
                )

        if not self._api_key:
            raise MistralError(
                "MISTRAL_API_KEY absente — définir la variable d'environnement "
                "(cf. .env.example) ou utiliser --dry-run."
            )
        if self._sdk is None:
            raise MistralError("Client non ouvert — utiliser 'async with MistralClient()'.")

        await self._limiter.acquire()
        response_format = {"type": "json_object"} if json_mode else {"type": "text"}
        try:
            res = await self._sdk.chat.complete_async(
                model=self.model,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                temperature=temperature,
                random_seed=seed,
                response_format=response_format,
            )
        except Exception as e:  # SDKError / validation / réseau — pas de fuite du corps
            from mistralai import models as _mm

            if isinstance(e, (_mm.SDKError, _mm.HTTPValidationError)):
                code = getattr(e, "status_code", "?")
                raise MistralError(f"Mistral erreur API (status {code}).") from None
            if isinstance(e, _mm.ResponseValidationError):
                raise MistralError("Mistral : réponse API invalide (schéma).") from None
            raise MistralError("Mistral : échec d'appel.") from None

        content = _extract_content(res)
        u = getattr(res, "usage", None)
        pin, pout = _price_for(self.model)
        prompt_tok = int(getattr(u, "prompt_tokens", 0) or 0)
        compl_tok = int(getattr(u, "completion_tokens", 0) or 0)
        usage = MistralUsage(
            prompt_tokens=prompt_tok,
            completion_tokens=compl_tok,
            total_tokens=int(getattr(u, "total_tokens", prompt_tok + compl_tok) or 0),
            est_cost_usd=round(prompt_tok / 1000 * pin + compl_tok / 1000 * pout, 6),
        )
        self.totals = self.totals + usage

        if cache:
            self._write_cache(
                rh,
                {
                    "content": content,
                    "model": self.model,
                    "prompt_version": PROMPT_VERSION,
                    "usage": {
                        "prompt_tokens": usage.prompt_tokens,
                        "completion_tokens": usage.completion_tokens,
                        "total_tokens": usage.total_tokens,
                        "est_cost_usd": usage.est_cost_usd,
                    },
                },
            )

        parsed = _safe_json(content) if json_mode else None
        if json_mode and parsed is None:
            log.warning("mistral_json_parse_failed", request_hash=rh, model=self.model)
        log.info(
            "mistral_call_ok",
            request_hash=rh,
            model=self.model,
            cache_hit=False,
            total_tokens=usage.total_tokens,
            est_cost_usd=usage.est_cost_usd,
        )
        return MistralResult(
            content=content,
            parsed=parsed,
            model=self.model,
            prompt_version=PROMPT_VERSION,
            usage=usage,
            cache_hit=False,
            request_hash=rh,
        )

def _safe_json(content: str) -> dict | None:
    try:
        obj = json.loads(content)
        return obj if isinstance(obj, dict) else None
    except (json.JSONDecodeError, TypeError):
        return None


def _extract_content(res: Any) -> str:
    """Texte de la réponse SDK : ``choices[0].message.content`` (str ou chunks)."""
    try:
        c = res.choices[0].message.content
    except (AttributeError, IndexError, TypeError):
        return ""
    if isinstance(c, list):
        parts: list[str] = []
        for chunk in c:
            t = getattr(chunk, "text", None)
            if t is None and isinstance(chunk, dict):
                t = chunk.get("text")
            if t:
                parts.append(str(t))
        return "".join(parts)
    return c or ""
