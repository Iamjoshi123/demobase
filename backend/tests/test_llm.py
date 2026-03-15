import httpx
import pytest

from app.services import llm


class _FailingAnthropicClient:
    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def post(self, url, headers=None, json=None):
        request = httpx.Request("POST", url)
        response = httpx.Response(429, request=request)
        raise httpx.HTTPStatusError("rate limited", request=request, response=response)


class _OpenRouterClient:
    def __init__(self, payload):
        self.payload = payload

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def post(self, url, headers=None, json=None):
        request = httpx.Request("POST", url)
        return httpx.Response(200, request=request, json=self.payload)


@pytest.mark.asyncio
async def test_generate_anthropic_rate_limit_returns_specific_message(monkeypatch):
    monkeypatch.setattr(llm.settings, "app_env", "development")
    monkeypatch.setattr(llm.settings, "aws_bedrock_token", None)
    monkeypatch.setattr(llm.settings, "openai_api_key", None)
    monkeypatch.setattr(llm.settings, "anthropic_api_key", "test-anthropic-key")
    monkeypatch.setattr(llm.httpx, "AsyncClient", lambda timeout=60: _FailingAnthropicClient())

    async def fake_ollama(*args, **kwargs):
        return kwargs.get("unavailable_message") or "unexpected"

    monkeypatch.setattr(llm, "_generate_ollama", fake_ollama)

    response = await llm.generate("hello")

    assert "Anthropic is temporarily rate limited" in response
    assert "retry in a moment" in response


@pytest.mark.asyncio
async def test_generate_raises_in_deterministic_demo_mode(monkeypatch):
    monkeypatch.setattr(llm.settings, "app_env", "development")
    monkeypatch.setattr(llm.settings, "deterministic_demo_mode", True)

    with pytest.raises(RuntimeError, match="Deterministic demo mode"):
        await llm.generate("hello")


@pytest.mark.asyncio
async def test_generate_openrouter_uses_chat_completion(monkeypatch):
    monkeypatch.setattr(llm.settings, "app_env", "development")
    monkeypatch.setattr(llm.settings, "deterministic_demo_mode", False)
    monkeypatch.setattr(llm.settings, "aws_bedrock_token", None)
    monkeypatch.setattr(llm.settings, "openrouter_api_key", "test-openrouter-key")
    monkeypatch.setattr(llm.settings, "openrouter_model", "nvidia/nemotron-nano-9b-v2:free")
    monkeypatch.setattr(llm.settings, "openai_api_key", None)
    monkeypatch.setattr(llm.settings, "anthropic_api_key", None)
    monkeypatch.setattr(
        llm.httpx,
        "AsyncClient",
        lambda timeout=60: _OpenRouterClient({"choices": [{"message": {"content": "openrouter ok"}}]}),
    )

    response = await llm.generate("hello")

    assert response == "openrouter ok"
