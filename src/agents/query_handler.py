"""Query Handler Agent — classifies user intent and routes to appropriate agents."""

from typing import Any

from src.agents.base_agent import BaseAgent
from src.core.state import ContentState

VALID_INTENTS = {"research", "blog", "linkedin", "image", "strategy"}


class QueryHandlerAgent(BaseAgent):
    """Classifies user queries into intents and extracts structured routing info."""

    agent_name = "query_handler"

    async def process(self, state: ContentState) -> dict[str, Any]:
        user_query = state["user_query"]

        self.logger.info("classifying_intent", query=user_query[:100])

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
