"""Query Handler Agent — classifies user intent and routes to appropriate agents."""

from typing import Any

from src.agents.base_agent import BaseAgent
from src.core.config import PROMPTS_DIR
from src.core.state import ContentState

VALID_INTENTS = {"research", "blog", "linkedin", "image", "strategy"}

_REJECTION_MESSAGE = (
    "I'm sorry, but I'm unable to process this request. "
    "It appears to contain content that falls outside the acceptable use policy for this platform. "
    "Please submit a request related to professional content marketing and I'll be happy to help."
)


class QueryHandlerAgent(BaseAgent):
    """Classifies user queries into intents and extracts structured routing info."""

    agent_name = "query_handler"

    @property
    def _safety_system_prompt(self) -> str:
        path = PROMPTS_DIR / "content_safety.txt"
        return path.read_text().strip()

    async def _is_request_safe(self, user_query: str) -> tuple[bool, str]:
        """Run a content safety check on the raw user query.

        Returns:
            (is_safe, reason) — reason is empty string when safe.
        """
        messages = [
            {"role": "system", "content": self._safety_system_prompt},
            {"role": "user", "content": user_query},
        ]
        result = await self.llm.generate_json(messages)
        is_safe = result.get("is_safe", True)
        reason = result.get("reason", "")
        return bool(is_safe), str(reason)

    async def process(self, state: ContentState) -> dict[str, Any]:
        user_query = state["user_query"]

        self.logger.info("classifying_intent", query=user_query[:100])

        # --- Content safety guardrail ---
        is_safe, safety_reason = await self._is_request_safe(user_query)
        if not is_safe:
            self.logger.warning(
                "request_rejected_by_safety_guardrail",
                reason=safety_reason,
                query=user_query[:100],
            )
            return {
                "intent": "rejected",
                "target_topic": "",
                "target_keywords": [],
                "rejection_message": _REJECTION_MESSAGE,
            }

        messages = self._build_messages(user_query)
        result = await self.llm.generate_json(messages)

        intent = result.get("intent", "research")
        if intent not in VALID_INTENTS:
            self.logger.warning("invalid_intent_defaulting", raw_intent=intent)
            intent = "research"

        topic = result.get("topic", user_query)
        keywords = result.get("keywords", [])

        self.logger.info(
            "intent_classified",
            intent=intent,
            topic=topic,
            keywords_count=len(keywords),
        )

        return {
            "intent": intent,
            "target_topic": topic,
            "target_keywords": keywords if isinstance(keywords, list) else [],
        }
