"""Content Strategist Agent — formats research into structured content briefs."""

from typing import Any

from src.agents.base_agent import BaseAgent
from src.core.models import StrategyReport
from src.core.state import ContentState


class ContentStrategistAgent(BaseAgent):
    """Transforms raw research into actionable content strategy reports."""

    agent_name = "content_strategist"

    async def process(self, state: ContentState) -> dict[str, Any]:
        topic = state.get("target_topic", "")
        research = state.get("research_results")

        if not research:
            return {
                "strategy_report": StrategyReport(
                    title=f"Content Strategy: {topic}",
                    executive_summary="No research data available for strategy generation.",
                    sections=[],
                    content_angles=[],
                    sources_cited=[],
                ),
            }

        # Build research context
        source_text = "\n\n".join(
            f"Source: {s.title} ({s.url})\n{s.snippet}" for s in research.sources[:10]
        )

        messages = self._build_messages(
            f"Create a content strategy report for: {topic}\n\n"
            f"RESEARCH SUMMARY:\n{research.summary}\n\n"
            f"KEY FINDINGS:\n" + "\n".join(f"- {f}" for f in research.key_findings) + "\n\n"
            f"SOURCES:\n{source_text}"
        )

        result = await self.llm.generate_json(messages)

        report = StrategyReport(
            title=result.get("title", f"Content Strategy: {topic}"),
            executive_summary=result.get("executive_summary", research.summary),
            sections=result.get("sections", []),
            content_angles=result.get("content_angles", []),
            sources_cited=research.sources,
        )

        self.logger.info(
            "strategy_report_generated",
            title=report.title,
            sections_count=len(report.sections),
            angles_count=len(report.content_angles),
        )

        return {"strategy_report": report}
