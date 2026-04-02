"""Application configuration using Pydantic Settings."""

from pathlib import Path
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
CONFIG_DIR = PROJECT_ROOT / "config"
PROMPTS_DIR = CONFIG_DIR / "prompts"


class Settings(BaseSettings):
    """Application settings loaded from environment variables and .env file."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # API Keys
    openai_api_key: str = ""
    anthropic_api_key: str = ""
    tavily_api_key: str = ""
    stability_api_key: str = ""

    # LLM Configuration
    openai_model: str = "gpt-4o"
    anthropic_model: str = "claude-sonnet-4-20250514"
    llm_temperature: float = 0.7
    llm_max_tokens: int = 4096

    # Image Generation
    dalle_model: str = "dall-e-3"
    image_size: str = "1024x1024"
    image_quality: str = "standard"

    # Search Configuration
    tavily_search_depth: str = "advanced"
    tavily_max_results: int = 5

    # Application
    environment: str = "development"
    log_level: str = "INFO"
    redis_url: Optional[str] = None

    # Timeouts and Retries
    api_timeout: float = 60.0
    max_retries: int = 3
    retry_backoff: float = 1.0

    # Content Settings
    blog_min_words: int = 1200
    blog_max_words: int = 1800
    linkedin_min_chars: int = 150
    linkedin_max_chars: int = 3000

    @property
    def is_production(self) -> bool:
        """Return True when ``environment`` is ``production``."""
        return self.environment == "production"

    def get_prompt_path(self, agent_name: str) -> Path:
        """Return the path to ``config/prompts/{agent_name}.txt``."""
        return PROMPTS_DIR / f"{agent_name}.txt"

    def load_prompt(self, agent_name: str) -> str:
        path = self.get_prompt_path(agent_name)
        if path.exists():
            return path.read_text().strip()
        raise FileNotFoundError(f"Prompt file not found: {path}")


def get_settings() -> Settings:
    """Factory function for Settings singleton."""
    return Settings()
