"""Abstract base agent with logging, error handling, and LLM access."""

import time
from abc import ABC, abstractmethod
from typing import Any

from src.core.config import Settings
from src.core.state import ContentState
from src.integrations.llm_client import LLMClient
from src.utils.logging_config import get_logger


class BaseAgent(ABC):
    """Base class for all ContentBlitz agents.

    Provides:
    - LLM client access
    - Structured logging with timing
    - System prompt loading from config/prompts/
    - Error wrapping with state updates
    """

    agent_name: str = "base"

    def __init__(self, settings: Settings, llm_client: LLMClient):
        self.settings = settings
        self.llm = llm_client
        self.logger = get_logger(f"agent.{self.agent_name}")
        self._system_prompt: str | None = None

    @property
    def system_prompt(self) -> str:
        """Load system prompt from config/prompts/{agent_name}.txt."""
        if self._system_prompt is None:
            try:
                self._system_prompt = self.settings.load_prompt(self.agent_name)
            except FileNotFoundError:
                self.logger.warning("prompt_file_not_found", agent=self.agent_name)
                self._system_prompt = f"You are the {self.agent_name} agent."
        return self._system_prompt

    @abstractmethod
    async def process(self, state: ContentState) -> dict[str, Any]:
        """Process the state and return updates.

        Args:
            state: Current workflow state.

        Returns:
            Dict of state updates to merge.
        """
        pass

    async def run(self, state: ContentState) -> dict[str, Any]:
        """Execute the agent with logging and error handling.

        This is the entry point called by LangGraph nodes.
        """
        self.logger.info("agent_started", agent=self.agent_name, intent=state.get("intent"))
        start = time.monotonic()

        try:
            updates = await self.process(state)
            duration_ms = (time.monotonic() - start) * 1000

            self.logger.info(
                "agent_completed",
                agent=self.agent_name,
                duration_ms=round(duration_ms, 1),
                update_keys=list(updates.keys()),
            )

            # Add to processing log
            updates.setdefault("processing_log", [self.agent_name])
            return updates

        except Exception as e:
            duration_ms = (time.monotonic() - start) * 1000
            self.logger.error(
                "agent_error",
                agent=self.agent_name,
                error=str(e),
                error_type=type(e).__name__,
                duration_ms=round(duration_ms, 1),
            )

            return {
                "errors": [
                    {
                        "agent": self.agent_name,
                        "error": str(e),
                        "error_type": type(e).__name__,
                    }
                ],
                "processing_log": [f"{self.agent_name} (failed)"],
            }

    def _build_messages(
        self, user_content: str, system_override: str | None = None
    ) -> list[dict[str, str]]:
        """Build LLM message list with system prompt.

        Args:
            user_content: The user message content.
            system_override: Override the default system prompt.

        Returns:
            List of message dicts for the LLM.
        """
        return [
            {"role": "system", "content": system_override or self.system_prompt},
            {"role": "user", "content": user_content},
        ]
