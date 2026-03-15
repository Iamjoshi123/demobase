from __future__ import annotations

import json
from typing import Any

from app.v2.models import MeetingSessionV2

DEFAULT_DEMO_LANGUAGE = "en"

LANGUAGE_LABELS: dict[str, str] = {
    "en": "English",
    "hi": "Hindi",
    "es": "Spanish",
    "fr": "French",
    "de": "German",
    "pt": "Portuguese",
    "ja": "Japanese",
}

GREETING_TEMPLATES: dict[str, str] = {
    "en": "Welcome {buyer}. I'll tailor this {workspace} walkthrough to your evaluation goals.",
    "hi": "स्वागत है {buyer}. मैं इस {workspace} walkthrough को आपके evaluation goals के अनुसार दिखाऊंगा।",
    "es": "Bienvenido, {buyer}. Adaptaré este recorrido de {workspace} a tus objetivos de evaluación.",
    "fr": "Bienvenue {buyer}. J'adapterai cette démonstration de {workspace} à vos objectifs d'évaluation.",
    "de": "Willkommen {buyer}. Ich passe diese {workspace}-Demo an Ihre Evaluationsziele an.",
    "pt": "Bem-vindo, {buyer}. Vou adaptar esta demonstração de {workspace} aos seus objetivos de avaliação.",
    "ja": "{buyer}さん、ようこそ。{workspace} のデモを評価目的に合わせてご案内します。",
}


def sanitize_demo_language(value: str | None) -> str:
    normalized = (value or "").strip().lower()
    if normalized in LANGUAGE_LABELS:
        return normalized
    return DEFAULT_DEMO_LANGUAGE


def language_name(language_code: str | None) -> str:
    return LANGUAGE_LABELS.get(sanitize_demo_language(language_code), LANGUAGE_LABELS[DEFAULT_DEMO_LANGUAGE])


def parse_personalization(personalization_json: str | None) -> dict[str, Any]:
    if not personalization_json:
        return {}
    try:
        payload = json.loads(personalization_json)
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}


def meeting_language(meeting: MeetingSessionV2) -> str:
    payload = parse_personalization(meeting.personalization_json)
    return sanitize_demo_language(payload.get("preferred_language"))


def update_meeting_language(meeting: MeetingSessionV2, language_code: str | None) -> str:
    payload = parse_personalization(meeting.personalization_json)
    payload["preferred_language"] = sanitize_demo_language(language_code)
    meeting.personalization_json = json.dumps(payload)
    return payload["preferred_language"]


def build_greeting_text(*, buyer_name: str | None, workspace_name: str, language_code: str | None) -> str:
    language = sanitize_demo_language(language_code)
    template = GREETING_TEMPLATES.get(language, GREETING_TEMPLATES[DEFAULT_DEMO_LANGUAGE])
    buyer = buyer_name or ("there" if language == "en" else "there")
    return template.format(buyer=buyer, workspace=workspace_name)
