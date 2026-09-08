"""Client Mistral (SDK officiel) — cache, coût, secret, mock via async_client httpx.

N'effectue AUCUN appel réseau réel : ``httpx.MockTransport`` est injecté dans le
SDK via ``async_client``. On vérifie le wrapper (cache/coût/secret/déterminisme),
pas le SDK lui-même.
"""
from __future__ import annotations

import json

import httpx
import pytest

from src.llm.mistral import MistralClient, MistralError


def _chat_response(content: dict, *, ptok=120, ctok=30) -> httpx.Response:
    """Forme JSON d'une réponse /v1/chat/completions attendue par le SDK mistralai."""
    body = {
        "id": "cmpl-test",
        "object": "chat.completion",
        "created": 1700000000,
        "model": "mistral-large-latest",
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": json.dumps(content)},
                "finish_reason": "stop",
            }
        ],
        "usage": {"prompt_tokens": ptok, "completion_tokens": ctok,
                  "total_tokens": ptok + ctok},
    }
    return httpx.Response(200, json=body)


def _handler_factory(content: dict, counter: dict):
    def handler(request: httpx.Request) -> httpx.Response:
        counter["n"] += 1
        counter["last_auth"] = request.headers.get("Authorization")
        return _chat_response(content)
    return handler


@pytest.mark.asyncio
async def test_cache_miss_then_hit(tmp_path):
    counter = {"n": 0}
    transport = httpx.MockTransport(_handler_factory({"label": "x", "confidence": 0.9}, counter))
    kw = dict(api_key="k-test", cache_dir=tmp_path, transport=transport, rps=0)

    async with MistralClient(**kw) as c:
        r1 = await c.complete(system="s", user="u")
    assert counter["n"] == 1 and r1.cache_hit is False
    assert r1.parsed == {"label": "x", "confidence": 0.9}
    assert (tmp_path / f"{r1.request_hash}.json").exists()
    assert r1.usage.total_tokens == 150
    assert r1.usage.est_cost_usd > 0

    # Re-run identique : HIT cache, AUCUN appel réseau, coût 0.
    async with MistralClient(**kw) as c2:
        r2 = await c2.complete(system="s", user="u")
        assert r2.cache_hit is True
        assert c2.totals.est_cost_usd == 0.0
    assert counter["n"] == 1
    assert r2.request_hash == r1.request_hash


@pytest.mark.asyncio
async def test_cache_dir_accepts_str(tmp_path):
    counter = {"n": 0}
    transport = httpx.MockTransport(_handler_factory({"ok": True}, counter))
    async with MistralClient(api_key="k", cache_dir=str(tmp_path), transport=transport, rps=0) as c:
        r = await c.complete(system="s", user="u")
    assert r.parsed == {"ok": True}
    assert (tmp_path / f"{r.request_hash}.json").exists()


@pytest.mark.asyncio
async def test_api_error_raises_without_leaking(tmp_path):
    def handler(request: httpx.Request) -> httpx.Response:
        # 400 avec un corps qui ÉCHO le prompt — ne doit jamais fuiter.
        return httpx.Response(400, json={"message": "echo of secret prompt"})

    async with MistralClient(
        api_key="k", cache_dir=tmp_path, transport=httpx.MockTransport(handler), rps=0,
    ) as c:
        with pytest.raises(MistralError) as exc:
            await c.complete(system="s", user="u", cache=False)
    assert "echo of secret prompt" not in str(exc.value)


@pytest.mark.asyncio
async def test_missing_key_raises_before_network(tmp_path):
    async with MistralClient(api_key=None, cache_dir=tmp_path, rps=0) as c:
        with pytest.raises(MistralError):
            await c.complete(system="s", user="u")


@pytest.mark.asyncio
async def test_api_key_in_header_never_in_cache(tmp_path):
    counter = {"n": 0}
    transport = httpx.MockTransport(_handler_factory({"a": 1}, counter))
    async with MistralClient(
        api_key="k-supersecret", cache_dir=tmp_path, transport=transport, rps=0,
    ) as c:
        r = await c.complete(system="s", user="u")
    # le SDK pose l'en-tête Authorization: Bearer <clé>.
    assert counter["last_auth"] == "Bearer k-supersecret"
    cache_text = (tmp_path / f"{r.request_hash}.json").read_text(encoding="utf-8")
    assert "k-supersecret" not in cache_text  # la clé n'est jamais cachée
