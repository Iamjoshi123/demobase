from types import SimpleNamespace

import pytest

from app.browser.stagehand_adapter import StagehandAdapter, settings as stagehand_settings


class FakePage:
    url = "https://app.example.com/reports"


def _result_namespace(**kwargs):
    return SimpleNamespace(**kwargs)


@pytest.mark.asyncio
async def test_stagehand_adapter_summarize_page_caches_by_url(monkeypatch):
    adapter = StagehandAdapter()
    calls = {"extract": 0}

    class FakeSession:
        async def extract(self, **kwargs):
            calls["extract"] += 1
            return _result_namespace(
                data=_result_namespace(
                    result={
                        "summary": "The reports screen shows performance analytics.",
                        "active_module": "Reports",
                        "primary_actions": ["Filter reports", "Export report"],
                        "entities": ["Northwind team"],
                    }
                )
            )

    async def fake_ensure_session():
        return FakeSession()

    monkeypatch.setattr(adapter, "_ensure_session", fake_ensure_session)

    first = await adapter.summarize_page(FakePage())
    second = await adapter.summarize_page(FakePage())

    assert first["summary"] == "The reports screen shows performance analytics."
    assert second["active_module"] == "Reports"
    assert calls["extract"] == 1


@pytest.mark.asyncio
async def test_stagehand_adapter_act_maps_response(monkeypatch):
    adapter = StagehandAdapter()

    class FakeAction:
        def model_dump(self):
            return {"description": "Click analytics", "selector": "a[href='/reports']"}

    class FakeSession:
        async def act(self, **kwargs):
            return _result_namespace(
                success=True,
                data=_result_namespace(
                    result=_result_namespace(
                        success=True,
                        message="Opened the reports area.",
                        actionDescription="Clicked the analytics navigation",
                        actions=[FakeAction()],
                    )
                ),
            )

    async def fake_ensure_session():
        return FakeSession()

    monkeypatch.setattr(adapter, "_ensure_session", fake_ensure_session)

    result = await adapter.act(FakePage(), "Open the analytics reports page")

    assert result["success"] is True
    assert result["action_description"] == "Clicked the analytics navigation"
    assert result["actions"][0]["selector"] == "a[href='/reports']"


@pytest.mark.asyncio
async def test_stagehand_adapter_accepts_bridge_dict_response(monkeypatch):
    adapter = StagehandAdapter()

    class FakeSession:
        async def extract(self, **kwargs):
            return {
                "result": {
                    "summary": "The analytics screen is open.",
                    "active_module": "Analytics",
                    "primary_actions": ["Filter", "Export"],
                    "entities": ["Q1 pipeline"],
                }
            }

        async def act(self, **kwargs):
            return {
                "success": True,
                "message": "Opened analytics.",
                "action_description": "Clicked analytics navigation",
                "actions": [{"selector": "a[href='/reports']"}],
            }

    async def fake_ensure_session():
        return FakeSession()

    monkeypatch.setattr(adapter, "_ensure_session", fake_ensure_session)

    summary = await adapter.summarize_page(FakePage())
    act = await adapter.act(FakePage(), "Open analytics")

    assert summary["active_module"] == "Analytics"
    assert act["success"] is True
    assert act["actions"][0]["selector"] == "a[href='/reports']"


def test_stagehand_adapter_uses_openrouter_key_for_openrouter_models(monkeypatch):
    adapter = StagehandAdapter()

    monkeypatch.setattr(stagehand_settings, "stagehand_model_name", "openrouter/openai/gpt-4.1-mini")
    monkeypatch.setattr(stagehand_settings, "openrouter_api_key", "openrouter-key")

    assert adapter._resolve_model_key() == "openrouter-key"
    assert adapter._resolve_model_base_url() == "https://openrouter.ai/api/v1"
