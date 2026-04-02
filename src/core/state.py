"""LangGraph state definition for the ContentBlitz workflow."""

from typing import Annotated, TypedDict

from src.core.models import (
    ABVariantResult,
    BlogContent,
    FactCheckResult,
    ImageResult,
    LinkedInContent,
    ResearchResult,
    StrategyReport,
)


def _merge_lists(left: list, right: list) -> list:
    """Reducer that merges two lists (used for append-only state fields)."""
    return left + right


class ContentState(TypedDict, total=False):
    """Central state flowing through all agents in the LangGraph workflow.

    Each agent reads from shared fields and writes to its own output field.
    """

    # --- Input ---
    user_query: str
    conversation_history: list[dict]

    # --- Routing (set by query_handler) ---
    intent: str  # research | blog | linkedin | image | strategy | rejected
    target_topic: str
    target_keywords: list[str]
    rejection_message: str  # set when intent == "rejected"

    # --- Research (set by deep_research) ---
    research_results: ResearchResult

    # --- Content Outputs (set by respective agents) ---
    blog_content: BlogContent
    linkedin_content: LinkedInContent
    image_result: ImageResult
    strategy_report: StrategyReport

    # --- Quality (set by hallucination_guard) ---
    fact_check_result: FactCheckResult

    # --- A/B Variants (set by ab_variant_generator) ---
    ab_variants: ABVariantResult

    # --- Metadata ---
    errors: Annotated[list[dict], _merge_lists]
    processing_log: Annotated[list[str], _merge_lists]
