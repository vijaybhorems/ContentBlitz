"""Thin node functions that delegate to agent instances.

Each node function is registered with the LangGraph StateGraph.
It receives the current state, calls the agent's run() method, and returns state updates.
"""

from typing import Any

from src.core.state import ContentState


class WorkflowNodes:
    """Container for all workflow node functions, bound to agent instances."""

    def __init__(self, agents: dict[str, Any]):
        """Initialize with a dict of agent_name -> agent_instance."""
        self._agents = agents

    async def query_handler(self, state: ContentState) -> dict[str, Any]:
        return await self._agents["query_handler"].run(state)

    async def deep_research(self, state: ContentState) -> dict[str, Any]:
        return await self._agents["deep_research"].run(state)

    async def seo_blog_writer(self, state: ContentState) -> dict[str, Any]:
        return await self._agents["seo_blog_writer"].run(state)

    async def linkedin_writer(self, state: ContentState) -> dict[str, Any]:
        return await self._agents["linkedin_writer"].run(state)

    async def image_generation(self, state: ContentState) -> dict[str, Any]:
        return await self._agents["image_generation"].run(state)

    async def content_strategist(self, state: ContentState) -> dict[str, Any]:
        return await self._agents["content_strategist"].run(state)

    async def hallucination_guard(self, state: ContentState) -> dict[str, Any]:
        return await self._agents["hallucination_guard"].run(state)

    async def ab_variant_generator(self, state: ContentState) -> dict[str, Any]:
        return await self._agents["ab_variant_generator"].run(state)
