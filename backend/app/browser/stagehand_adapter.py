"""Stagehand adapter backed by a local Node bridge."""

from __future__ import annotations

import logging
import os
import time
import uuid
from typing import Any, Optional

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

PAGE_SUMMARY_SCHEMA = {
    "type": "object",
    "properties": {
        "summary": {"type": "string", "maxLength": 220},
        "active_module": {"type": "string"},
        "primary_actions": {"type": "array", "items": {"type": "string"}, "maxItems": 5},
        "entities": {"type": "array", "items": {"type": "string"}, "maxItems": 5},
    },
    "required": ["summary", "primary_actions"],
}


class _BridgeSession:
    def __init__(
        self,
        *,
        bridge_url: str,
        cdp_url: str,
        model_name: str,
        api_key: str,
        base_url: str | None,
        session_key: str,
    ) -> None:
        self._bridge_url = bridge_url.rstrip("/")
        self._cdp_url = cdp_url
        self._model_name = model_name
        self._api_key = api_key
        self._base_url = base_url
        self._session_key = session_key

    async def act(self, *, page: Any | None = None, input: str, timeout_ms: int = 20000) -> dict[str, Any]:
        return await self._post(
            "/v1/act",
            {
                "cdp_url": self._cdp_url,
                "instruction": input,
                "model_name": self._model_name,
                "api_key": self._api_key,
                "base_url": self._base_url,
                "page_url": _page_url(page),
                "session_key": self._session_key,
                "timeout_ms": timeout_ms,
            },
        )

    async def observe(
        self,
        *,
        page: Any | None = None,
        instruction: str,
        timeout_ms: int = 20000,
    ) -> dict[str, Any]:
        return await self._post(
            "/v1/observe",
            {
                "cdp_url": self._cdp_url,
                "instruction": instruction,
                "model_name": self._model_name,
                "api_key": self._api_key,
                "base_url": self._base_url,
                "page_url": _page_url(page),
                "session_key": self._session_key,
                "timeout_ms": timeout_ms,
            },
        )

    async def extract(
        self,
        *,
        page: Any | None = None,
        instruction: str,
        schema: dict[str, Any],
        timeout_ms: int = 20000,
    ) -> dict[str, Any]:
        return await self._post(
            "/v1/extract",
            {
                "cdp_url": self._cdp_url,
                "instruction": instruction,
                "model_name": self._model_name,
                "api_key": self._api_key,
                "base_url": self._base_url,
                "page_url": _page_url(page),
                "schema": schema,
                "session_key": self._session_key,
                "timeout_ms": timeout_ms,
            },
        )

    async def end(self) -> None:
        try:
            await self._post("/v1/release", {"session_key": self._session_key})
        except Exception as exc:  # pragma: no cover - cleanup path
            logger.debug("Stagehand bridge release failed: %s", exc)

    async def _post(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        timeout = httpx.Timeout(connect=5, read=90, write=30, pool=30)
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(f"{self._bridge_url}{path}", json=payload)
            response.raise_for_status()
            return response.json()


class StagehandAdapter:
    def __init__(self) -> None:
        self._session: Any = None
        self._cdp_url: Optional[str] = None
        self._last_summary_url: Optional[str] = None
        self._last_summary_at = 0.0
        self._last_summary_payload: dict[str, Any] = {}
        self._session_key = f"stagehand-{uuid.uuid4().hex}"

    @property
    def enabled(self) -> bool:
        return (
            settings.enable_stagehand
            and self._bridge_mode_enabled()
            and bool(self._resolve_model_key())
        )

    async def act(self, page: Any, instruction: str) -> dict[str, Any]:
        if not instruction.strip():
            return {"success": False, "error": "Instruction is empty"}

        session = await self._ensure_session()
        if session is None:
            return {"success": False, "error": "Stagehand is not configured"}

        try:
            response = await session.act(page=page, input=instruction)
        except Exception as exc:
            logger.warning("Stagehand act failed: %s", exc)
            return {"success": False, "error": str(exc)}

        if isinstance(response, dict):
            return response

        result = getattr(getattr(response, "data", None), "result", None)
        actions = getattr(result, "actions", None) if result is not None else None
        return {
            "success": bool(getattr(response, "success", False) and getattr(result, "success", True)),
            "message": getattr(result, "message", "") if result is not None else "",
            "action_description": getattr(result, "actionDescription", "") if result is not None else "",
            "actions": [item.model_dump() for item in actions] if actions else [],
        }

    async def observe(self, page: Any, instruction: str) -> list[dict[str, Any]]:
        session = await self._ensure_session()
        if session is None:
            return []

        try:
            response = await session.observe(page=page, instruction=instruction)
        except Exception as exc:
            logger.warning("Stagehand observe failed: %s", exc)
            return []

        if isinstance(response, dict):
            actions = response.get("actions")
            return list(actions) if isinstance(actions, list) else []
        if isinstance(response, list):
            return response

        result = getattr(getattr(response, "data", None), "result", None) or []
        return [item.model_dump() for item in result]

    async def summarize_page(self, page: Any) -> dict[str, Any]:
        session = await self._ensure_session()
        if session is None:
            return {}

        page_url = _page_url(page)
        now = time.monotonic()
        if (
            page_url
            and page_url == self._last_summary_url
            and self._last_summary_payload
            and (now - self._last_summary_at) < 5
        ):
            return dict(self._last_summary_payload)

        try:
            response = await session.extract(
                page=page,
                instruction=(
                    "Briefly summarize this product screen. "
                    "Return one short summary, the current module, up to five visible actions, and up to five key entities."
                ),
                schema=PAGE_SUMMARY_SCHEMA,
            )
        except Exception as exc:
            logger.warning("Stagehand extract failed: %s", exc)
            return {}

        if isinstance(response, dict):
            payload = response.get("result", response)
        else:
            payload = getattr(getattr(response, "data", None), "result", None)
        payload = payload if isinstance(payload, dict) else {}
        self._last_summary_url = page_url
        self._last_summary_at = now
        self._last_summary_payload = payload
        return dict(payload)

    async def close(self) -> None:
        if self._session is not None:
            try:
                await self._session.end()
            except Exception as exc:  # pragma: no cover - cleanup path
                logger.debug("Stagehand session close failed: %s", exc)
            self._session = None

    def set_browser_cdp_url(self, cdp_url: Optional[str]) -> None:
        self._cdp_url = cdp_url

    async def _ensure_session(self) -> Any | None:
        if not self.enabled:
            return None
        if self._session is not None:
            return self._session
        if not self._cdp_url:
            logger.warning("Stagehand bridge requires a CDP URL but none is configured")
            return None

        bridge_url = settings.stagehand_bridge_url.rstrip("/")
        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(connect=3, read=5, write=5, pool=5)) as client:
                response = await client.get(f"{bridge_url}/health")
                response.raise_for_status()
        except Exception as exc:
            logger.warning("Stagehand bridge is unavailable at %s: %s", bridge_url, exc)
            return None

        model_key = self._resolve_model_key()
        if not model_key:
            logger.warning("Stagehand model key is not configured")
            return None

        base_url = self._resolve_model_base_url()
        self._session = _BridgeSession(
            bridge_url=bridge_url,
            cdp_url=self._cdp_url,
            model_name=settings.stagehand_model_name,
            api_key=model_key,
            base_url=base_url,
            session_key=self._session_key,
        )
        return self._session

    def _bridge_mode_enabled(self) -> bool:
        return settings.stagehand_server_mode in {"bridge", "local", "node-bridge"}

    def _resolve_model_key(self) -> Optional[str]:
        model_name = settings.stagehand_model_name
        if model_name.startswith("openrouter/"):
            return settings.openrouter_api_key
        if model_name.startswith("anthropic/"):
            return settings.anthropic_api_key
        if model_name.startswith(("google/", "gemini/")):
            return os.environ.get("GOOGLE_API_KEY") or os.environ.get("GOOGLE_GENERATIVE_AI_API_KEY")
        return settings.openai_api_key

    def _resolve_model_base_url(self) -> Optional[str]:
        if settings.stagehand_model_name.startswith("openrouter/"):
            return settings.openrouter_base_url
        return None


def _page_url(page: Any | None) -> str:
    if page is None:
        return ""
    value = getattr(page, "url", "")
    return value() if callable(value) else value or ""
