"""Image Generation Agent — creates visuals with DALL-E 3 and Stability AI fallback."""

from typing import Any

from src.agents.base_agent import BaseAgent
from src.core.exceptions import APIError, ContentBlitzError, ImageGenerationError
from src.core.models import ImageResult
from src.core.state import ContentState
from src.integrations.openai_image_client import OpenAIImageClient
from src.integrations.stability_client import StabilityClient


class ImageGenerationAgent(BaseAgent):
    """Generates images using LLM-optimized prompts with provider fallback."""

    agent_name = "image_generation"

    def __init__(self, settings, llm_client, dalle_client: OpenAIImageClient, stability_client: StabilityClient):
        super().__init__(settings, llm_client)
        self.dalle = dalle_client
        self.stability = stability_client

    async def process(self, state: ContentState) -> dict[str, Any]:
        topic = state.get("target_topic", "")
        blog = state.get("blog_content")

        # Build context for prompt engineering
        context = topic
        if blog:
            context = f"Topic: {topic}\nBlog title: {blog.title}"

        # Step 1: Engineer an optimized image prompt
        image_prompt = await self._engineer_prompt(context)
        self.logger.info("image_prompt_engineered", prompt=image_prompt[:100])

        # Step 2: Generate image with fallback
        result = await self._generate_with_fallback(image_prompt)

        return {"image_result": result}

    async def _engineer_prompt(self, context: str) -> str:
        """Use LLM to create an optimized image generation prompt."""
        messages = self._build_messages(
            f"Create an image generation prompt for the following content:\n\n{context}\n\n"
            f"The image should be suitable as a hero image for a blog post or social media."
        )

        try:
            result = await self.llm.generate_json(messages)
            return result.get("prompt", f"Professional illustration about {context[:100]}")
        except ContentBlitzError as e:
            self.logger.warning("prompt_engineering_failed", error=str(e))
            return f"Professional, modern illustration representing {context[:100]}, clean design, vibrant colors"

    async def _generate_with_fallback(self, prompt: str) -> ImageResult:
        """Try DALL-E 3 first, fall back to Stability AI."""
        errors: list[str] = []

        # Try DALL-E 3
        if self.settings.openai_api_key:
            try:
                result = await self.dalle.generate(prompt)
                self.logger.info("image_generated_dalle3")
                return result
            except APIError as e:
                errors.append(str(e))
                self.logger.warning("dalle3_failed", error=str(e), falling_back_to="stability")

        # Fallback: Stability AI
        if self.settings.stability_api_key:
            try:
                result = await self.stability.generate(prompt)
                self.logger.info("image_generated_stability_fallback")
                return result
            except APIError as e:
                errors.append(str(e))
                self.logger.error("stability_also_failed", error=str(e))

        raise ImageGenerationError(errors or ["No image generation API keys configured"])
