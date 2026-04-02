"""Conditional routing functions for the LangGraph workflow."""

from src.core.state import ContentState


def route_by_intent(state: ContentState) -> str:
    """Route from query_handler to the next node based on classified intent.

    Intents that need research first (blog, linkedin, strategy) route to deep_research.
    Image routes directly to image_generation.
    Rejected requests short-circuit to END.
    """
    intent = state.get("intent", "research")

    if intent == "rejected":
        return "__end__"

    if intent == "image":
        return "image_generation"

    # All other intents go through research first
    return "deep_research"


def route_after_research(state: ContentState) -> str:
    """Route from deep_research to the appropriate content generation node."""
    intent = state.get("intent", "research")

    routing = {
        "blog": "seo_blog_writer",
        "linkedin": "linkedin_writer",
        "strategy": "content_strategist",
        "research": "content_strategist",
    }

    return routing.get(intent, "content_strategist")


def route_after_content(state: ContentState) -> str:
    """Route from content generation to hallucination guard or end.

    Only blog and linkedin content gets fact-checked.
    """
    intent = state.get("intent", "")

    if intent in ("blog", "linkedin"):
        return "hallucination_guard"

    return "__end__"
