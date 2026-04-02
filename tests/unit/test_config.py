"""Tests for core configuration."""

import pytest
from src.core.config import Settings, PROMPTS_DIR


class TestSettings:
    def test_default_values(self, settings):
        assert settings.openai_model == "gpt-4o"
        assert settings.llm_temperature == 0.7
        assert settings.environment == "development"

    def test_is_production(self, settings):
        assert not settings.is_production

    def test_is_production_true(self):
        s = Settings(environment="production")
        assert s.is_production

    def test_get_prompt_path(self, settings):
        path = settings.get_prompt_path("query_handler")
        assert path.name == "query_handler.txt"
        assert path.parent == PROMPTS_DIR

    def test_load_prompt_exists(self, settings):
        prompt = settings.load_prompt("query_handler")
        assert "intent" in prompt.lower() or "route" in prompt.lower()

    def test_load_prompt_missing(self, settings):
        with pytest.raises(FileNotFoundError):
            settings.load_prompt("nonexistent_agent")

    def test_api_keys_from_init(self, settings):
        assert settings.openai_api_key == "sk-test-openai-key"
        assert settings.tavily_api_key == "tvly-test-key"

    def test_blog_word_limits(self, settings):
        assert settings.blog_min_words < settings.blog_max_words
        assert settings.blog_min_words >= 800
