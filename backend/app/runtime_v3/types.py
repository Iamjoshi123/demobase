from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class IntentAssessment:
    mode: str
    rationale: str
    focus: Optional[str] = None
    should_demo: bool = False
    should_answer: bool = True
    should_clarify: bool = False
    should_handoff: bool = False
    policy_decision: str = "allow"


@dataclass
class ObservationSnapshot:
    url: str = ""
    title: str = ""
    visible_text: str = ""
    screen_summary: str = ""
    active_module: str = ""
    visible_actions: list[str] = field(default_factory=list)
    action_candidates: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class RetrievalSnapshot:
    context_text: str = ""
    citations: list[str] = field(default_factory=list)
    chunks: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class ActionPlan:
    strategy: str
    stagehand_instruction: Optional[str] = None
    candidate: Optional[dict[str, Any]] = None
    fallback_recipe_id: Optional[str] = None
    fallback_recipe_name: Optional[str] = None
    rationale: str = ""


@dataclass
class VerificationSnapshot:
    success: bool
    detail: str
    page_url: str = ""
    page_title: str = ""


@dataclass
class TurnPipelineResult:
    intent: IntentAssessment
    observation: ObservationSnapshot
    retrieval: RetrievalSnapshot
    action_plan: ActionPlan
    verification: Optional[VerificationSnapshot] = None
