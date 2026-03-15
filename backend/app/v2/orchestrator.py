"""V2 meeting orchestration for personalized product demos."""

from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import dataclass, field
from typing import Optional

from sqlmodel import Session

from app.models.recipe import DemoRecipe
from app.models.workspace import Workspace
from app.runtime_v3.pipeline import DemoTurnPipeline
from app.runtime_v3.types import ObservationSnapshot, TurnPipelineResult
from app.services.llm import generate
from app.v2.language import language_name, meeting_language
from app.v2.models import MeetingSessionV2

logger = logging.getLogger(__name__)


@dataclass
class MeetingTurn:
    response_text: str
    stage: str
    policy_decision: str
    next_actions: list[str] = field(default_factory=list)
    citations: list[str] = field(default_factory=list)
    recipe_id: Optional[str] = None
    recipe_name: Optional[str] = None
    should_handoff: bool = False
    focus: Optional[str] = None
    browser_instruction: Optional[str] = None
    action_strategy: str = "answer_only"
    metadata: dict[str, object] = field(default_factory=dict)


class MeetingOrchestrator:
    def __init__(self, *, pipeline: Optional[DemoTurnPipeline] = None) -> None:
        self._pipeline = pipeline or DemoTurnPipeline()

    async def handle_turn(
        self,
        db: Session,
        meeting: MeetingSessionV2,
        buyer_message: str,
        *,
        realtime: bool = False,
    ) -> MeetingTurn:
        workspace = db.get(Workspace, meeting.workspace_id)
        preferred_language = meeting_language(meeting)
        planning_message = await _normalize_buyer_message_for_planning(buyer_message, preferred_language)
        pipeline_result = await self._pipeline.inspect(db, meeting, planning_message)
        intent = pipeline_result.intent
        action_plan = pipeline_result.action_plan
        recipe = db.get(DemoRecipe, action_plan.fallback_recipe_id) if action_plan.fallback_recipe_id else None

        if intent.policy_decision == "refuse":
            return MeetingTurn(
                response_text=(
                    "I can't help with that in the demo environment. "
                    "That request falls outside the allowed demo scope."
                ),
                stage="handoff",
                policy_decision="refuse",
                next_actions=["offer_safe_alternative"],
                should_handoff=False,
                metadata={"rationale": intent.rationale},
            )

        if intent.policy_decision == "escalate":
            return MeetingTurn(
                response_text=(
                    "That part is best handled by a human sales conversation. "
                    "I can still walk you through the product and show the relevant workflow while they follow up."
                ),
                stage="handoff",
                policy_decision="escalate",
                next_actions=["handoff_human_sales", "continue_safe_demo"],
                should_handoff=True,
                metadata={"rationale": intent.rationale},
            )

        stage = _determine_stage(meeting.stage, pipeline_result)
        focus = _derive_focus(buyer_message, pipeline_result, recipe)
        next_actions = _build_next_actions(action_plan)
        action_strategy = action_plan.strategy
        browser_instruction = action_plan.stagehand_instruction

        if action_strategy in {"stagehand_first", "recipe_fallback", "clarify"}:
            response_text = _compose_direct_reply(
                workspace=workspace,
                pipeline_result=pipeline_result,
                recipe=recipe,
                realtime=realtime,
                preferred_language=preferred_language,
            )
        else:
            try:
                response_text = await asyncio.wait_for(
                    _generate_answer_reply(
                        workspace=workspace,
                        meeting=meeting,
                        buyer_message=planning_message,
                        original_buyer_message=buyer_message,
                        pipeline_result=pipeline_result,
                        recipe=recipe,
                        realtime=realtime,
                        preferred_language=preferred_language,
                    ),
                    timeout=8 if realtime else 14,
                )
            except asyncio.TimeoutError:
                logger.warning("Meeting reply generation timed out for meeting %s", meeting.id)
                response_text = _fallback_answer_reply(workspace, pipeline_result, recipe)

        response_text = await _localize_for_buyer(response_text, preferred_language, realtime=realtime)

        return MeetingTurn(
            response_text=response_text,
            stage=stage,
            policy_decision=intent.policy_decision,
            next_actions=next_actions,
            citations=pipeline_result.retrieval.citations,
            recipe_id=recipe.id if recipe else None,
            recipe_name=recipe.name if recipe else None,
            should_handoff=intent.should_handoff,
            focus=focus,
            browser_instruction=browser_instruction,
            action_strategy=action_strategy,
            metadata={
                "workspace_name": workspace.name if workspace else None,
                "browser_instruction": browser_instruction,
                "action_strategy": action_strategy,
                "intent_mode": intent.mode,
                "intent_rationale": intent.rationale,
                "preferred_language": preferred_language,
                "observed_module": pipeline_result.observation.active_module,
                "observed_summary": pipeline_result.observation.screen_summary,
            },
        )


async def _generate_answer_reply(
    *,
    workspace: Optional[Workspace],
    meeting: MeetingSessionV2,
    buyer_message: str,
    original_buyer_message: str,
    pipeline_result: TurnPipelineResult,
    recipe: Optional[DemoRecipe],
    realtime: bool,
    preferred_language: str,
) -> str:
    intent = pipeline_result.intent
    observation = pipeline_result.observation
    retrieval = pipeline_result.retrieval

    persona_lines = [
        f"Buyer name: {meeting.buyer_name or 'Unknown'}",
        f"Buyer company: {meeting.company_name or 'Unknown'}",
        f"Buyer role: {meeting.role_title or 'Unknown'}",
        f"Buyer goal: {meeting.goal or 'Understand the product'}",
        f"Intent mode: {intent.mode}",
        f"Intent rationale: {intent.rationale}",
        f"Preferred reply language: {language_name(preferred_language)}",
        f"Workspace: {workspace.name if workspace else 'Product demo'}",
    ]

    prompt_parts = [
        "You are preparing a grounded product demo response.",
        "\n".join(persona_lines),
        f"Buyer message for planning: {buyer_message}",
        f"Original buyer message: {original_buyer_message}",
        f"Observed product state:\n{_render_observation_context(observation)}",
    ]
    if retrieval.context_text:
        prompt_parts.append(f"Relevant product documentation:\n{retrieval.context_text[:1200]}")
    if recipe is not None:
        prompt_parts.append(f"Relevant walkthrough workflow: {recipe.name}")
    prompt_parts.append(
        "Answer the buyer directly. Ground the reply in the observed screen and documentation. "
        "Do not dump raw page text or raw URLs unless necessary."
    )
    prompt_parts.append(
        "Default to a simple live-demo policy: show while telling. "
        "Walk the buyer through what is on screen now and the next UI area you would open."
    )
    prompt_parts.append(
        "Sound empathetic and enthusiastic, but stay specific and grounded in the product."
    )
    prompt_parts.append(f"Respond in {language_name(preferred_language)}.")
    if realtime:
        prompt_parts.append(
            "This response will be spoken live. Keep it to one or two short sentences, sound natural, "
            "and make the walkthrough easy to follow."
        )

    system = (
        "You are a warm, high-signal demo agent. "
        "Answer only from the supplied product context. "
        "Default to show while telling. "
        "If the buyer wants a walkthrough, mention the concrete UI area you are showing now and the next thing you would open. "
        "Sound empathetic and enthusiastic without overhyping."
    )
    if realtime:
        system += " Optimize for spoken conversation speed and natural turn-taking."

    try:
        return await generate(
            "\n\n".join(prompt_parts),
            system=system,
            max_tokens=200 if realtime else 420,
            temperature=0.15 if realtime else 0.2,
        )
    except Exception:
        return _fallback_answer_reply(workspace, pipeline_result, recipe)


def personalize_summary_payload(meeting: MeetingSessionV2) -> str:
    return json.dumps(
        {
            "buyer_name": meeting.buyer_name,
            "company_name": meeting.company_name,
            "role_title": meeting.role_title,
            "goal": meeting.goal,
            "preferred_language": meeting_language(meeting),
        }
    )


def _determine_stage(previous_stage: str, pipeline_result: TurnPipelineResult) -> str:
    strategy = pipeline_result.action_plan.strategy
    if strategy in {"refuse", "escalate"}:
        return "handoff"
    if strategy in {"stagehand_first", "recipe_fallback"}:
        return "demo"
    if strategy == "clarify":
        return "discover" if previous_stage == "intro" else previous_stage or "discover"
    return "answer"


def _build_next_actions(action_plan) -> list[str]:
    if action_plan.strategy == "stagehand_first":
        actions = []
        if action_plan.stagehand_instruction:
            actions.append(f"run_browser_instruction:{action_plan.stagehand_instruction}")
        if action_plan.fallback_recipe_id:
            actions.append(f"fallback_recipe:{action_plan.fallback_recipe_id}")
        actions.append("continue_conversation")
        return actions
    if action_plan.strategy == "recipe_fallback" and action_plan.fallback_recipe_id:
        return [f"fallback_recipe:{action_plan.fallback_recipe_id}", "share_browser_context", "continue_conversation"]
    if action_plan.strategy == "answer_only":
        return ["answer_question", "offer_walkthrough"]
    if action_plan.strategy == "clarify":
        return ["clarify_buyer_goal", "continue_conversation"]
    return ["continue_conversation"]


def _derive_focus(
    buyer_message: str,
    pipeline_result: TurnPipelineResult,
    recipe: Optional[DemoRecipe],
) -> Optional[str]:
    if recipe is not None:
        return recipe.name
    candidate = pipeline_result.action_plan.candidate or {}
    for key in ("description", "action_description", "selector"):
        value = candidate.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()[:80]
    if pipeline_result.observation.active_module:
        return pipeline_result.observation.active_module[:80]
    if pipeline_result.intent.focus:
        return pipeline_result.intent.focus[:80]
    message = buyer_message.strip()
    return message[:80] if message else None


def _compose_direct_reply(
    *,
    workspace: Optional[Workspace],
    pipeline_result: TurnPipelineResult,
    recipe: Optional[DemoRecipe],
    realtime: bool,
    preferred_language: str,
) -> str:
    action_plan = pipeline_result.action_plan
    observation = pipeline_result.observation
    product_name = workspace.name if workspace else "the product"

    if action_plan.strategy == "clarify":
        return (
            "Absolutely. I'll start with the most relevant product area and walk you through it live."
            if realtime
            else "Absolutely. I'll start with the most relevant product area and walk you through it in the live product."
        )

    if action_plan.strategy == "stagehand_first":
        target = _action_target_label(action_plan.candidate, observation, action_plan.stagehand_instruction)
        if realtime:
            return f"Absolutely. I'll open {target} in {product_name} and walk you through what matters as we go."
        return f"I'll open {target} in the live {product_name} experience and walk you through what matters as we go."

    if action_plan.strategy == "recipe_fallback" and recipe is not None:
        if realtime:
            return f"Absolutely. I'll walk you through {recipe.name} live and call out the key steps as we go."
        return f"I'll use {recipe.name} in the live product and walk you through the key steps as we go."

    return _fallback_answer_reply(workspace, pipeline_result, recipe)


def _fallback_answer_reply(
    workspace: Optional[Workspace],
    pipeline_result: TurnPipelineResult,
    recipe: Optional[DemoRecipe],
) -> str:
    observation = pipeline_result.observation
    retrieval = pipeline_result.retrieval
    product_name = workspace.name if workspace else "the product"

    if observation.screen_summary and observation.active_module:
        return (
            f"Right now I'm on {observation.active_module}. "
            f"{observation.screen_summary} I'll keep walking you through what you're seeing so it stays easy to follow."
        )
    if observation.screen_summary:
        return f"Right now in {product_name}, {observation.screen_summary} I'll keep walking you through it live."
    if recipe is not None:
        return f"I'll use the {recipe.name} walkthrough and walk you through the product as I go."
    if retrieval.context_text:
        return f"Based on the product context, {retrieval.context_text[:220]} I'll keep the walkthrough moving and explain each step as we go."
    return "I'll lead the walkthrough from here and show you each step while I explain it."


async def _normalize_buyer_message_for_planning(buyer_message: str, preferred_language: str) -> str:
    if preferred_language == "en" or not buyer_message.strip():
        return buyer_message
    try:
        translated = await generate(
            (
                "Translate the following buyer request into concise English for internal planning only. "
                "Preserve product names and exact UI labels.\n\n"
                f"{buyer_message}"
            ),
            system="You translate software demo requests into concise English for internal planning.",
            max_tokens=120,
            temperature=0,
        )
        return translated.strip() or buyer_message
    except Exception:
        return buyer_message


async def _localize_for_buyer(text: str, preferred_language: str, *, realtime: bool) -> str:
    if preferred_language == "en" or not text.strip():
        return text
    try:
        localized = await generate(
            (
                f"Rewrite the following software demo reply in {language_name(preferred_language)}. "
                "Keep product names and exact UI labels unchanged. Do not add information.\n\n"
                f"{text}"
            ),
            system="You localize software demo replies while preserving product names and UI labels.",
            max_tokens=220 if realtime else 320,
            temperature=0,
        )
        return localized.strip() or text
    except Exception:
        return text


def _render_observation_context(observation: ObservationSnapshot) -> str:
    parts = [
        f"Page title: {observation.title or 'Unknown'}",
        f"URL: {observation.url or ''}",
    ]
    if observation.active_module:
        parts.append(f"Active module: {observation.active_module}")
    if observation.screen_summary:
        parts.append(f"Screen summary: {observation.screen_summary}")
    if observation.visible_actions:
        parts.append(f"Visible actions: {', '.join(observation.visible_actions[:5])}")
    if observation.visible_text:
        parts.append(f"Visible text excerpt: {observation.visible_text[:300]}")
    return "\n".join(parts)


def _action_target_label(
    candidate: dict | None,
    observation: ObservationSnapshot,
    instruction: Optional[str],
) -> str:
    candidate = candidate or {}
    for key in ("description", "action_description", "instruction"):
        value = candidate.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    if observation.active_module:
        return observation.active_module
    if instruction:
        return instruction
    return "the relevant workflow"
