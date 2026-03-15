from __future__ import annotations

from typing import Any, Awaitable, Callable, Optional

from sqlmodel import Session, select

from app.browser.executor import get_browser_state, observe_action_candidates
from app.models.recipe import DemoRecipe
from app.policies.engine import evaluate_policy
from app.retrieval.vector_store import search as vector_search
from app.runtime_v3.types import (
    ActionPlan,
    IntentAssessment,
    ObservationSnapshot,
    RetrievalSnapshot,
    TurnPipelineResult,
)


BrowserStateReader = Callable[[str], Awaitable[Optional[dict[str, Any]]]]
ActionObserver = Callable[[str, str], Awaitable[list[dict[str, Any]]]]
Retriever = Callable[..., list[dict[str, Any]]]


class DemoTurnPipeline:
    def __init__(
        self,
        *,
        browser_state_reader: BrowserStateReader = get_browser_state,
        action_observer: ActionObserver = observe_action_candidates,
        retriever: Retriever = vector_search,
    ) -> None:
        self._browser_state_reader = browser_state_reader
        self._action_observer = action_observer
        self._retriever = retriever

    async def inspect(self, db: Session, meeting: Any, buyer_message: str) -> TurnPipelineResult:
        policy = evaluate_policy(db, meeting.workspace_id, buyer_message)
        recipe = _match_recipe(db, meeting.workspace_id, buyer_message)
        intent = _assess_intent(buyer_message, policy.decision, recipe, getattr(meeting, "stage", None))
        observation = await self._observe(meeting, buyer_message, intent)
        retrieval = self._retrieve(meeting.workspace_id, buyer_message)
        action_plan = _plan_action(intent, observation, retrieval, recipe)
        return TurnPipelineResult(
            intent=intent,
            observation=observation,
            retrieval=retrieval,
            action_plan=action_plan,
        )

    async def _observe(
        self,
        meeting: Any,
        buyer_message: str,
        intent: IntentAssessment,
    ) -> ObservationSnapshot:
        if not getattr(meeting, "runtime_session_id", None):
            return ObservationSnapshot()

        state = await self._browser_state_reader(meeting.runtime_session_id) or {}
        candidates: list[dict[str, Any]] = []
        if intent.should_demo:
            candidates = await self._action_observer(meeting.runtime_session_id, _stagehand_goal_prompt(buyer_message))

        return ObservationSnapshot(
            url=str(state.get("url") or ""),
            title=str(state.get("title") or ""),
            visible_text=str(state.get("visible_text") or ""),
            screen_summary=str(state.get("stagehand_summary") or ""),
            active_module=str(state.get("stagehand_active_module") or ""),
            visible_actions=list(state.get("stagehand_primary_actions") or []),
            action_candidates=candidates,
        )

    def _retrieve(self, workspace_id: str, buyer_message: str) -> RetrievalSnapshot:
        chunks = self._retriever(buyer_message, workspace_id, top_k=4)
        return RetrievalSnapshot(
            context_text="\n---\n".join(item["content"] for item in chunks if item.get("content")),
            citations=[item.get("document_id", "") for item in chunks if item.get("document_id")],
            chunks=chunks,
        )


def build_verified_narration(
    *,
    action_type: str,
    target: str | None,
    before_state: dict[str, Any] | None,
    after_state: dict[str, Any] | None,
    fallback_narration: str | None,
) -> str:
    before_state = before_state or {}
    after_state = after_state or {}
    before_title = str(before_state.get("title") or "")
    after_title = str(after_state.get("title") or "")
    before_url = str(before_state.get("url") or "")
    after_url = str(after_state.get("url") or "")
    before_module = str(before_state.get("stagehand_active_module") or "")
    after_summary = str(after_state.get("stagehand_summary") or "")
    after_module = str(after_state.get("stagehand_active_module") or "")

    if after_title and after_title != before_title:
        return f"Opened {after_title}."
    if after_module and after_module != before_module:
        return f"Moved into {after_module}."
    if after_url and after_url != before_url:
        return f"Navigated to {after_url}."
    if after_summary:
        return f"Confirmed the page changed: {after_summary}"
    if fallback_narration:
        return fallback_narration
    if target:
        return f"Completed {action_type} for {target}."
    return f"Completed {action_type}."


def _assess_intent(
    buyer_message: str,
    policy_decision: str,
    recipe: DemoRecipe | None,
    previous_stage: str | None,
) -> IntentAssessment:
    lowered = buyer_message.lower()
    if policy_decision == "refuse":
        return IntentAssessment(mode="refuse", rationale="Blocked by policy", should_answer=False, policy_decision="refuse")
    if policy_decision == "escalate":
        return IntentAssessment(
            mode="escalate",
            rationale="Needs human follow-up",
            should_answer=True,
            should_handoff=True,
            policy_decision="escalate",
        )

    show_tokens = ("show", "walk me", "demo", "take me", "open", "navigate", "how do i", "where do i", "can you show")
    question_tokens = ("what", "how", "does", "can", "is", "are")
    if any(token in lowered for token in show_tokens):
        return IntentAssessment(mode="show_and_tell", rationale="Buyer asked for a product walkthrough", focus=buyer_message[:80], should_demo=True)
    if recipe is not None:
        return IntentAssessment(mode="show_and_tell", rationale="Known walkthrough matches the buyer request", focus=recipe.name, should_demo=True)
    if previous_stage == "intro" and lowered.strip() and (len(lowered.split()) >= 3 or any(token in lowered for token in question_tokens)):
        return IntentAssessment(
            mode="show_and_tell",
            rationale="Lead with a live walkthrough during the intro stage",
            focus=buyer_message[:80],
            should_demo=True,
            should_answer=True,
        )
    if any(token in lowered for token in question_tokens):
        return IntentAssessment(mode="answer_only", rationale="Buyer asked an informational question", focus=buyer_message[:80], should_answer=True)
    if len(lowered.split()) < 3:
        return IntentAssessment(mode="clarify", rationale="Request is too short to act safely", should_answer=False, should_clarify=True)
    return IntentAssessment(mode="answer_only", rationale="Default to grounded answer", focus=buyer_message[:80], should_answer=True)


def _plan_action(
    intent: IntentAssessment,
    observation: ObservationSnapshot,
    retrieval: RetrievalSnapshot,
    recipe: DemoRecipe | None,
) -> ActionPlan:
    if intent.mode in {"refuse", "escalate"}:
        return ActionPlan(strategy=intent.mode, rationale=intent.rationale)
    if intent.should_clarify:
        if observation.action_candidates:
            candidate = observation.action_candidates[0]
            instruction = _candidate_instruction(candidate)
            if instruction:
                return ActionPlan(
                    strategy="stagehand_first",
                    stagehand_instruction=instruction,
                    candidate=candidate,
                    fallback_recipe_id=recipe.id if recipe else None,
                    fallback_recipe_name=recipe.name if recipe else None,
                    rationale="Using the best visible UI target instead of asking the buyer to drive the walkthrough",
                )
        return ActionPlan(strategy="clarify", rationale=intent.rationale)

    if observation.action_candidates:
        candidate = observation.action_candidates[0]
        instruction = _candidate_instruction(candidate)
        if instruction:
            return ActionPlan(
                strategy="stagehand_first",
                stagehand_instruction=instruction,
                candidate=candidate,
                fallback_recipe_id=recipe.id if recipe else None,
                fallback_recipe_name=recipe.name if recipe else None,
                rationale="Using the best visible UI target from the current page",
            )

    if recipe is not None and intent.should_demo:
        return ActionPlan(
            strategy="recipe_fallback",
            fallback_recipe_id=recipe.id,
            fallback_recipe_name=recipe.name,
            rationale="Using a known demo flow because no reliable direct target was observed",
        )

    if retrieval.context_text or observation.screen_summary:
        return ActionPlan(strategy="answer_only", rationale="Enough product context exists to answer without acting")

    return ActionPlan(strategy="clarify", rationale="Not enough live context to choose a safe product action")


def _candidate_instruction(candidate: dict[str, Any]) -> str:
    for key in ("description", "instruction", "action_description", "action"):
        value = candidate.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    selector = candidate.get("selector")
    method = candidate.get("method") or candidate.get("type")
    if selector and method:
        return f"{method} the element {selector}"
    if selector:
        return f"Use the element {selector}"
    return ""


def _stagehand_goal_prompt(buyer_message: str) -> str:
    return (
        "Inspect the current page and identify the safest visible action that helps with this buyer request: "
        f"{buyer_message}. Prefer read-only navigation and clearly labeled product actions."
    )


def _match_recipe(db: Session, workspace_id: str, buyer_message: str) -> Optional[DemoRecipe]:
    recipes = db.exec(
        select(DemoRecipe)
        .where(DemoRecipe.workspace_id == workspace_id, DemoRecipe.is_active)
        .order_by(DemoRecipe.priority.desc())
    ).all()
    lowered = buyer_message.lower()
    best_recipe: DemoRecipe | None = None
    best_score = 0
    for recipe in recipes:
        score = 0
        triggers = [item.strip().lower() for item in recipe.trigger_phrases.split(",") if item.strip()]
        score += sum(1 for trigger in triggers if trigger in lowered)
        if recipe.name.lower() in lowered:
            score += 2
        if recipe.description and any(token in lowered for token in recipe.description.lower().split()[:6]):
            score += 1
        if score > best_score:
            best_score = score
            best_recipe = recipe
    return best_recipe if best_score > 0 else None
