"""LinkedIn Post Writer Agent — generates engaging professional social content."""

from typing import Any

from src.agents.base_agent import BaseAgent
from src.core.models import LinkedInContent
from src.core.state import ContentState


class LinkedInWriterAgent(BaseAgent):
    """Creates LinkedIn posts optimized for engagement."""

    agent_name = "linkedin_writer"

    async def process(self, state: ContentState) -> dict[str, Any]:
        topic = state.get("target_topic", "")
        research = state.get("research_results")

        research_context = ""
        if research:
            research_context = (
                f"\n\nRESEARCH CONTEXT:\n{research.summary}\n\n"
                f"KEY DATA POINTS:\n" + "\n".join(f"- {f}" for f in research.key_findings[:5])
            )

        messages = self._build_messages(
            f"Create an engaging LinkedIn post about: {topic}\n"
            f"{research_context}\n\n"
            f"Target length: {self.settings.linkedin_min_chars}-{self.settings.linkedin_max_chars} characters."
        )

        result = await self.llm.generate_json(messages)

        post_text = result.get("post_text", "")
        hashtags = result.get("hashtags", [])

        # Ensure hashtags start with #
        hashtags = [h if h.startswith("#") else f"#{h}" for h in hashtags]

        content = LinkedInContent(
            post_text=post_text,
            hashtags=hashtags,
            hook_type=result.get("hook_type", "unknown"),
            character_count=len(post_text),
        )

        self.logger.info(
            "linkedin_post_generated",
            hook_type=content.hook_type,
            char_count=content.character_count,
            hashtags_count=len(content.hashtags),
        )

        return {"linkedin_content": content}
