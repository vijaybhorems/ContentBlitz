"""Custom exception hierarchy for ContentBlitz."""


class ContentBlitzError(Exception):
    """Base exception for all ContentBlitz errors."""


class APIError(ContentBlitzError):
    """Error communicating with an external API."""

    def __init__(self, provider: str, message: str, status_code: int | None = None):
        self.provider = provider
        self.status_code = status_code
        super().__init__(f"[{provider}] {message} (status={status_code})")


class LLMError(ContentBlitzError):
    """Error from LLM provider."""

    def __init__(self, provider: str, message: str):
        self.provider = provider
        super().__init__(f"[{provider}] {message}")


class LLMFallbackExhausted(ContentBlitzError):
    """All LLM providers failed."""

    def __init__(self, errors: list[str]):
        self.errors = errors
        super().__init__(f"All LLM providers failed: {'; '.join(errors)}")


class AgentError(ContentBlitzError):
    """Error within an agent's processing logic."""

    def __init__(self, agent_name: str, message: str):
        self.agent_name = agent_name
        super().__init__(f"[{agent_name}] {message}")


class ImageGenerationError(ContentBlitzError):
    """All image generation providers failed."""

    def __init__(self, errors: list[str]):
        self.errors = errors
        super().__init__(f"Image generation failed: {'; '.join(errors)}")


class ConfigurationError(ContentBlitzError):
    """Missing or invalid configuration."""
