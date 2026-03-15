"""Planner service - orchestrates how to respond to buyer queries.

Decisions:
- answer_only: answer from knowledge base, no demo needed
- answer_and_demo: answer + show it in browser
- clarify: ask for more detail before acting
- escalate: defer to human (pricing, legal, etc.)
- refuse: block the action (destructive, out of scope)
"""

import logging
from typing import Optional
from dataclasses import dataclass
from sqlmodel import Session, select
from app.models.recipe import DemoRecipe
from app.models.session import DemoSession
from app.browser.executor import get_browser_state
from app.retrieval.vector_store import search as vector_search
from app.policies.engine import evaluate_policy, PolicyDecision
from app.services.llm import generate

logger = logging.getLogger(__name__)


@dataclass
class PlanResult:
    decision: str  # answer_only, answer_and_demo, clarify, escalate, refuse
    response_text: str
    recipe_id: Optional[str] = None
    retrieval_context: Optional[str] = None
    policy_decision: Optional[PolicyDecision] = None
    citations: list[str] = None

    def __post_init__(self):
        if self.citations is None:
            self.citations = []


async def plan_response(
    db: Session,
    session: DemoSession,
    user_message: str,
) -> PlanResult:
    """Main planner: decide what to do with a buyer's message.

    Steps:
    1. Check policies (refuse/escalate if needed)
    2. Search for matching recipe
    3. Retrieve from knowledge base
    4. Decide action type
    5. Generate response
    """
    workspace_id = session.workspace_id

    # Step 1: Policy check
    policy = evaluate_policy(db, workspace_id, user_message)
    if policy.decision == "refuse":
        return PlanResult(
            decision="refuse",
            response_text=f"I'm not able to help with that. {policy.reason or 'This falls outside what I can assist with in this demo.'}",
            policy_decision=policy,
        )
    if policy.decision == "escalate":
        return PlanResult(
            decision="escalate",
            response_text=f"That's a great question! {policy.reason or 'This topic'} would be best discussed with our sales team. I can help demonstrate product features in the meantime. Would you like to see something specific?",
            policy_decision=policy,
        )

    # Step 2: Match a recipe
    recipe = _match_recipe(db, workspace_id, user_message)

    # Step 3: Retrieve context
    retrieval_results = vector_search(user_message, workspace_id, top_k=5)
    context_text = "\n---\n".join([r["content"] for r in retrieval_results]) if retrieval_results else ""
    citations = [r.get("document_id", "") for r in retrieval_results if r.get("document_id")]
    browser_state = await get_browser_state(session.id) if session.browser_session_id else None
    live_page_context = ""
    if browser_state:
        visible_text = (browser_state.get("visible_text") or "")[:1200]
        stagehand_summary = browser_state.get("stagehand_summary") or ""
        stagehand_module = browser_state.get("stagehand_active_module") or ""
        stagehand_actions = browser_state.get("stagehand_primary_actions") or []
        live_page_context = (
            f"Live product page title: {browser_state.get('title') or 'Unknown'}\n"
            f"Live product URL: {browser_state.get('url') or ''}\n"
            f"Visible page text:\n{visible_text}"
        )
        if stagehand_summary:
            live_page_context += f"\nStagehand screen summary: {stagehand_summary}"
        if stagehand_module:
            live_page_context += f"\nActive module: {stagehand_module}"
        if stagehand_actions:
            live_page_context += f"\nPrimary visible actions: {', '.join(stagehand_actions[:6])}"

    # Step 4: Decide action type
    decision = await _decide_action(user_message, context_text, recipe is not None)

    # Step 5: Generate response
    response = await _generate_response(
        user_message=user_message,
        context=context_text,
        live_page_context=live_page_context,
        decision=decision,
        recipe_name=recipe.name if recipe else None,
    )

    return PlanResult(
        decision=decision,
        response_text=response,
        recipe_id=recipe.id if recipe else None,
        retrieval_context=(context_text or live_page_context)[:500] if (context_text or live_page_context) else None,
        policy_decision=policy,
        citations=citations,
    )


def _match_recipe(db: Session, workspace_id: str, user_message: str) -> Optional[DemoRecipe]:
    """Find the best matching recipe based on trigger phrases."""
    recipes = db.exec(
        select(DemoRecipe).where(
            DemoRecipe.workspace_id == workspace_id,
            DemoRecipe.is_active,
        ).order_by(DemoRecipe.priority.desc())
    ).all()

    user_lower = user_message.lower()
    best_match = None
    best_score = 0

    for recipe in recipes:
        triggers = [t.strip().lower() for t in recipe.trigger_phrases.split(",") if t.strip()]
        score = sum(1 for t in triggers if t in user_lower)
        # Also check recipe name and description
        if recipe.name.lower() in user_lower:
            score += 2
        if recipe.description and any(word in user_lower for word in recipe.description.lower().split()[:5]):
            score += 1

        if score > best_score:
            best_score = score
            best_match = recipe

    return best_match if best_score > 0 else None


async def _decide_action(user_message: str, context: str, has_recipe: bool) -> str:
    """Decide the response action type."""
    msg_lower = user_message.lower()

    # Clear demo intent signals
    demo_signals = ["show me", "demonstrate", "walk me through", "how do i", "can you show",
                    "let me see", "navigate to", "go to", "open", "create a", "edit",
                    "how would", "can your software"]
    if any(signal in msg_lower for signal in demo_signals):
        if has_recipe:
            return "answer_and_demo"
        return "answer_and_demo"  # Try exploratory demo

    # Question signals
    question_signals = ["what is", "what are", "do you have", "does it", "tell me about",
                        "explain", "describe", "how does"]
    if any(signal in msg_lower for signal in question_signals) or "?" in user_message:
        if has_recipe and context:
            return "answer_and_demo"
        return "answer_only"

    # Vague / needs clarification
    if len(user_message.split()) < 4 and "?" not in user_message:
        return "clarify"

    # Default: answer + demo if recipe available
    if has_recipe:
        return "answer_and_demo"
    if context:
        return "answer_only"
    return "clarify"


async def _generate_response(
    user_message: str,
    context: str,
    live_page_context: str = "",
    decision: str = "answer_only",
    recipe_name: Optional[str] = None,
) -> str:
    """Generate the agent's spoken/text response."""
    system = """You are a product demo assistant. You help potential buyers understand a B2B SaaS product.
Rules:
- Be concise but helpful (2-4 sentences)
- If you have context from docs, use it to ground your answer
- If showing a demo, briefly describe what you'll show
- Never make up features not mentioned in the context
- If uncertain, say you'll check and verify
- Be conversational and friendly"""

    prompt_parts = [f"Buyer's question: {user_message}"]

    if context:
        prompt_parts.append(f"\nRelevant product documentation:\n{context[:1500]}")
    else:
        prompt_parts.append("\nNo specific documentation found for this question.")

    if live_page_context:
        prompt_parts.append(f"\nCurrent live product state:\n{live_page_context}")

    if decision == "answer_and_demo" and recipe_name:
        prompt_parts.append(f"\nYou will also demonstrate this with the '{recipe_name}' workflow.")
    elif decision == "answer_and_demo":
        prompt_parts.append("\nYou will also try to demonstrate this live in the product.")
    elif decision == "clarify":
        prompt_parts.append("\nThe question is unclear. Ask for clarification about what they'd like to see.")

    prompt = "\n".join(prompt_parts)

    try:
        return await generate(prompt, system)
    except Exception as e:
        logger.error(f"LLM generation failed: {e}")
        # Fallback response
        if context:
            return f"Based on our documentation: {context[:300]}... Would you like me to show you this in the product?"
        if live_page_context:
            return f"From the live product page I can currently see: {live_page_context[:300]}... Tell me what area you want me to focus on."
        return "I'd be happy to help! Could you tell me a bit more about what you're looking for? I can show you features directly in the product."
