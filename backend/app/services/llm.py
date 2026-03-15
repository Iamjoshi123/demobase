"""LLM service with hybrid strategy: local Ollama by default, hosted fallback."""

import httpx
import json
import logging
from typing import Optional
from app.config import settings

logger = logging.getLogger(__name__)


async def generate(
    prompt: str,
    system: str = "You are a helpful product demo assistant.",
    model: Optional[str] = None,
    max_tokens: int = 1024,
    temperature: float = 0.3,
) -> str:
    """Generate a completion using the best available LLM provider.

    Priority: OpenAI > Anthropic > Ollama (local).
    """
    if settings.app_env == "test":
        marker = "Relevant product documentation:\n"
        if marker in prompt:
            snippet = prompt.split(marker, 1)[1].split("\n\n", 1)[0].strip()
            return f"Test response based on docs: {snippet[:220]}"
        return "Test response: Please share more detail about what you want to see."

    if settings.deterministic_demo_mode:
        raise RuntimeError("Deterministic demo mode is enabled")

    if settings.has_bedrock:
        return await _generate_bedrock(prompt, system, model or settings.aws_bedrock_model, max_tokens, temperature)
    if settings.has_openrouter:
        return await _generate_openrouter(prompt, system, model or settings.openrouter_model, max_tokens, temperature)
    if settings.has_openai:
        return await _generate_openai(prompt, system, model or "gpt-4o-mini", max_tokens, temperature)
    if settings.has_anthropic:
        return await _generate_anthropic(prompt, system, model or "claude-sonnet-4-20250514", max_tokens, temperature)
    return await _generate_ollama(prompt, system, model or "llama3.2", max_tokens, temperature)


async def _generate_bedrock(prompt: str, system: str, model: str, max_tokens: int, temperature: float) -> str:
    """Call AWS Bedrock Converse API with Bearer token auth."""
    region = settings.aws_bedrock_region
    url = f"https://bedrock-runtime.{region}.amazonaws.com/model/{model}/converse"
    async with httpx.AsyncClient(timeout=60) as client:
        try:
            resp = await client.post(
                url,
                headers={
                    "Authorization": f"Bearer {settings.aws_bedrock_token}",
                    "Content-Type": "application/json",
                },
                json={
                    "messages": [{"role": "user", "content": [{"text": f"{system}\n\n{prompt}"}]}],
                    "inferenceConfig": {
                        "maxTokens": max_tokens,
                        "temperature": temperature,
                    },
                },
            )
            resp.raise_for_status()
            data = resp.json()
            return data["output"]["message"]["content"][0]["text"]
        except Exception as e:
            logger.error(f"Bedrock API error: {e}")
            return await _generate_ollama(
                prompt,
                system,
                "llama3.2",
                max_tokens,
                temperature,
                unavailable_message=_provider_failure_message("Bedrock", e),
            )


async def _generate_openai(prompt: str, system: str, model: str, max_tokens: int, temperature: float) -> str:
    """Call OpenAI chat completions API."""
    async with httpx.AsyncClient(timeout=60) as client:
        try:
            resp = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {settings.openai_api_key}"},
                json={
                    "model": model,
                    "messages": [
                        {"role": "system", "content": system},
                        {"role": "user", "content": prompt},
                    ],
                    "max_tokens": max_tokens,
                    "temperature": temperature,
                },
            )
            resp.raise_for_status()
            return resp.json()["choices"][0]["message"]["content"]
        except Exception as e:
            logger.error(f"OpenAI API error: {e}")
            # Fall through to Ollama
            return await _generate_ollama(
                prompt,
                system,
                "llama3.2",
                max_tokens,
                temperature,
                unavailable_message=_provider_failure_message("OpenAI", e),
            )


async def _generate_openrouter(prompt: str, system: str, model: str, max_tokens: int, temperature: float) -> str:
    """Call OpenRouter chat completions API."""
    if "embed" in model.lower():
        raise RuntimeError(f"OpenRouter model {model} is an embedding model, not a chat model")

    async with httpx.AsyncClient(timeout=60) as client:
        try:
            resp = await client.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {settings.openrouter_api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": model,
                    "messages": [
                        {"role": "system", "content": system},
                        {"role": "user", "content": prompt},
                    ],
                    "max_tokens": max_tokens,
                    "temperature": temperature,
                },
            )
            resp.raise_for_status()
            return resp.json()["choices"][0]["message"]["content"]
        except Exception as e:
            logger.error(f"OpenRouter API error: {e}")
            return await _generate_ollama(
                prompt,
                system,
                "llama3.2",
                max_tokens,
                temperature,
                unavailable_message=_provider_failure_message("OpenRouter", e),
            )


async def _generate_anthropic(prompt: str, system: str, model: str, max_tokens: int, temperature: float) -> str:
    """Call Anthropic messages API."""
    async with httpx.AsyncClient(timeout=60) as client:
        try:
            resp = await client.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": settings.anthropic_api_key,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
                json={
                    "model": model,
                    "system": system,
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": max_tokens,
                    "temperature": temperature,
                },
            )
            resp.raise_for_status()
            return resp.json()["content"][0]["text"]
        except Exception as e:
            logger.error(f"Anthropic API error: {e}")
            return await _generate_ollama(
                prompt,
                system,
                "llama3.2",
                max_tokens,
                temperature,
                unavailable_message=_provider_failure_message("Anthropic", e),
            )


async def _generate_ollama(
    prompt: str,
    system: str,
    model: str,
    max_tokens: int,
    temperature: float,
    unavailable_message: Optional[str] = None,
) -> str:
    """Call local Ollama API."""
    async with httpx.AsyncClient(timeout=120) as client:
        try:
            resp = await client.post(
                f"{settings.ollama_base_url}/api/generate",
                json={
                    "model": model,
                    "prompt": prompt,
                    "system": system,
                    "options": {
                        "num_predict": max_tokens,
                        "temperature": temperature,
                    },
                    "stream": False,
                },
            )
            resp.raise_for_status()
            return resp.json().get("response", "I'm unable to generate a response right now.")
        except Exception as e:
            logger.error(f"Ollama API error: {e}")
            if unavailable_message:
                return unavailable_message
            return (
                "I apologize, but I'm currently unable to process your request. "
                "No LLM provider is available. Please check the backend configuration."
            )


def _provider_failure_message(provider: str, error: Exception) -> str:
    if isinstance(error, httpx.HTTPStatusError):
        status = error.response.status_code
        if status == 429:
            return (
                f"I apologize, but {provider} is temporarily rate limited right now. "
                "Please retry in a moment."
            )
        if status == 401:
            return (
                f"I apologize, but {provider} rejected the request due to invalid credentials. "
                "Please check the backend API key configuration."
            )
        if status == 403:
            return (
                f"I apologize, but {provider} rejected the request due to insufficient permissions. "
                "Please check the backend account configuration."
            )
        return (
            f"I apologize, but {provider} is currently unavailable "
            f"(HTTP {status}). Please retry in a moment."
        )

    return (
        f"I apologize, but {provider} is currently unavailable. "
        "Please retry in a moment."
    )


async def generate_json(
    prompt: str,
    system: str = "You are a helpful assistant. Respond only with valid JSON.",
    model: Optional[str] = None,
) -> dict:
    """Generate and parse a JSON response from the LLM."""
    raw = await generate(prompt, system, model, temperature=0.1)
    # Try to extract JSON from the response
    try:
        # Handle markdown code blocks
        if "```json" in raw:
            raw = raw.split("```json")[1].split("```")[0].strip()
        elif "```" in raw:
            raw = raw.split("```")[1].split("```")[0].strip()
        return json.loads(raw)
    except json.JSONDecodeError:
        logger.warning(f"Failed to parse LLM JSON response: {raw[:200]}")
        return {"error": "Failed to parse response", "raw": raw}
