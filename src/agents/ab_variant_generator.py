"""A/B Variant Generator Agent — creates headline/hook variants and scores them."""

from typing import Any

from src.agents.base_agent import BaseAgent
from src.core.models import ABVariantResult, Variant
from src.core.state import ContentState


HOOK_TYPES = ["question", "statistic", "story", "provocation", "contrast"]


class ABVariantGeneratorAgent(BaseAgent):
    """Generates multiple content variants with different hooks and scores them.

    Given a blog headline or LinkedIn post, produces 3-5 variants using
    different hook strategies (question, statistic, story, provocation, contrast),
    scores each on engagement potential, and recommends the best option.
    """

    agent_name = "ab_variant_generator"

    async def process(self, state: ContentState) -> dict[str, Any]:
        content_type, original_headline, original_hook, content_text = self._extract_content(state)

        if not original_headline and not content_text:
            self.logger.info("no_content_for_variants")
            return {}

        self.logger.info(
            "generating_variants",
            content_type=content_type,
            original_headline=original_headline[:80],
        )

        # Build context for the LLM
        topic = state.get("target_topic", "")
        keywords = state.get("target_keywords", [])
        research_summary = ""
        if state.get("research_results"):
            research_summary = state["research_results"].summary[:500]

        user_content = (
            f"CONTENT TYPE: {content_type}\n"
            f"TOPIC: {topic}\n"
            f"KEYWORDS: {', '.join(keywords[:5])}\n"
            f"ORIGINAL HEADLINE: {original_headline}\n"
            f"ORIGINAL HOOK TYPE: {original_hook}\n"
            f"CONTENT PREVIEW: {content_text[:800]}\n"
            f"RESEARCH CONTEXT: {research_summary}\n\n"
            f"Generate 3-5 A/B variants using different hook types. "
            f"Score each variant on a 0-100 scale across these dimensions: "
            f"engagement, clarity, emotional_impact, curiosity_gap, audience_fit. "
            f"Rank by overall score."
        )

        messages = self._build_messages(user_content)
        result = await self.llm.generate_json_fast(messages)

        # Parse variants
        variants = []
        for v in result.get("variants", []):
            variants.append(
                Variant(
                    hook_type=v.get("hook_type", "unknown"),
                    headline=v.get("headline", ""),
                    body_preview=v.get("body_preview", ""),
                    score=min(100.0, max(0.0, float(v.get("score", 0)))),
                    score_breakdown=v.get("score_breakdown", {}),
                    rationale=v.get("rationale", ""),
                )
            )

        # Sort by score descending
        variants.sort(key=lambda v: v.score, reverse=True)

        ab_result = ABVariantResult(
            original_headline=original_headline,
            original_hook_type=original_hook,
            variants=variants,
            recommendation=result.get("recommendation", ""),
            content_type=content_type,
        )

        self.logger.info(
            "variants_generated",
            count=len(variants),
            top_score=variants[0].score if variants else 0,
            top_hook=variants[0].hook_type if variants else "none",
        )

        return {"ab_variants": ab_result}

    @staticmethod
    def _extract_content(state: ContentState) -> tuple[str, str, str, str]:
        """Extract headline, hook type, and preview text from state.

        Returns:
            (content_type, headline, hook_type, preview_text)
        """
        if state.get("blog_content"):
            blog = state["blog_content"]
            return (
                "blog",
                blog.title,
                "informational",
                blog.body_markdown[:1000],
            )
        if state.get("linkedin_content"):
            li = state["linkedin_content"]
            # First line of LinkedIn post is typically the hook
            lines = li.post_text.strip().split("\n")
            headline = lines[0] if lines else ""
            return (
                "linkedin",
                headline,
                li.hook_type or "unknown",
                li.post_text,
            )
        return ("", "", "", "")
