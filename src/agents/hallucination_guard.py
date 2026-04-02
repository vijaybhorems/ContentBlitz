"""Hallucination Guard Agent — fact-checks content against research sources."""

from typing import Any

from src.agents.base_agent import BaseAgent
from src.core.models import Claim, FactCheckResult
from src.core.state import ContentState


class HallucinationGuardAgent(BaseAgent):
    """Extracts factual claims from generated content and verifies against research sources."""

    agent_name = "hallucination_guard"

    async def process(self, state: ContentState) -> dict[str, Any]:
        # Get the generated content to check
        content_to_check = self._get_content_to_check(state)
        research = state.get("research_results")

        if not content_to_check:
            self.logger.info("no_content_to_fact_check")
            return {"fact_check_result": FactCheckResult(trust_score=100.0)}

        if not research or not research.raw_snippets:
            self.logger.warning("no_research_sources_for_verification")
            return {
                "fact_check_result": FactCheckResult(
                    trust_score=50.0,
                    recommendations=["No research sources available for verification."],
                )
            }

        # Build source context
        source_context = "\n\n".join(
            f"[Source {i+1}] {s.title}: {s.snippet}"
            for i, s in enumerate(research.sources[:10])
        )

        # Single LLM call for claim extraction + verification
        messages = self._build_messages(
            f"CONTENT TO FACT-CHECK:\n{content_to_check[:4000]}\n\n"
            f"RESEARCH SOURCES:\n{source_context}\n\n"
            f"Extract all factual claims from the content and verify each one against the research sources."
        )

        result = await self.llm.generate_json(messages)

        # Parse claims
        claims = []
        for c in result.get("claims", []):
            claims.append(
                Claim(
                    text=c.get("text", ""),
                    status=c.get("status", "unsupported"),
                    source_match=c.get("source_match"),
                    confidence=c.get("confidence", 0.5),
                )
            )

        # Calculate trust score
        if claims:
            verified = sum(1 for c in claims if c.status == "verified")
            trust_score = (verified / len(claims)) * 100
        else:
            verified = 0
            trust_score = 100.0  # No claims = nothing to flag

        flagged = [c for c in claims if c.status in ("unsupported", "contradicted")]

        fact_check = FactCheckResult(
            trust_score=round(trust_score, 1),
            total_claims=len(claims),
            verified_claims=verified,
            claims=claims,
            flagged_claims=flagged,
            recommendations=result.get("recommendations", []),
        )

        self.logger.info(
            "fact_check_complete",
            total_claims=fact_check.total_claims,
            verified=fact_check.verified_claims,
            flagged=len(fact_check.flagged_claims),
            trust_score=fact_check.trust_score,
        )

        return {"fact_check_result": fact_check}

    @staticmethod
    def _get_content_to_check(state: ContentState) -> str:
        """Extract the text content that needs fact-checking."""
        if state.get("blog_content"):
            blog = state["blog_content"]
            return f"{blog.title}\n\n{blog.body_markdown}"
        if state.get("linkedin_content"):
            return state["linkedin_content"].post_text
        if state.get("strategy_report"):
            report = state["strategy_report"]
            sections_text = "\n".join(
                s.get("content", "") for s in report.sections
            )
            return f"{report.executive_summary}\n\n{sections_text}"
        return ""
