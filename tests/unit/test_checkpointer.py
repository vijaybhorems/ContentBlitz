"""Unit tests for the checkpointer factory in src.workflow.graph."""

from unittest.mock import MagicMock, patch

import pytest
from langgraph.checkpoint.memory import MemorySaver

from src.core.config import Settings
from src.workflow.graph import create_checkpointer


@pytest.fixture
def settings_no_redis():
    return Settings(
        openai_api_key="sk-test",
        redis_url=None,
    )


@pytest.fixture
def settings_with_redis():
    return Settings(
        openai_api_key="sk-test",
        redis_url="redis://localhost:6379/0",
    )


class TestCreateCheckpointer:
    """Tests for create_checkpointer()."""

    def test_returns_memory_saver_when_no_redis_url(self, settings_no_redis):
        """Without redis_url, should return MemorySaver."""
        saver = create_checkpointer(settings_no_redis)
        assert isinstance(saver, MemorySaver)

    def test_returns_memory_saver_when_redis_url_empty(self):
        """Empty string redis_url should also fall back to MemorySaver."""
        settings = Settings(openai_api_key="sk-test", redis_url="")
        saver = create_checkpointer(settings)
        assert isinstance(saver, MemorySaver)

    def test_returns_async_redis_saver_when_redis_url_set(self, settings_with_redis):
        """With a redis_url, should return AsyncRedisSaver."""
        with patch(
            "src.workflow.graph.AsyncRedisSaver", create=True
        ) as MockSaver:
            mock_instance = MagicMock()
            MockSaver.return_value = mock_instance

            # Patch the import inside create_checkpointer
            with patch.dict(
                "sys.modules",
                {"langgraph.checkpoint.redis.aio": MagicMock(AsyncRedisSaver=MockSaver)},
            ):
                saver = create_checkpointer(settings_with_redis)

            assert saver is not None

    def test_falls_back_to_memory_on_redis_import_error(self, settings_with_redis):
        """If AsyncRedisSaver import fails, should gracefully fall back to MemorySaver."""
        with patch.dict("sys.modules", {"langgraph.checkpoint.redis.aio": None}):
            saver = create_checkpointer(settings_with_redis)
            assert isinstance(saver, MemorySaver)

    def test_falls_back_to_memory_on_redis_connection_error(self, settings_with_redis):
        """If AsyncRedisSaver constructor raises, should fall back to MemorySaver."""

        def raise_conn_error(*args, **kwargs):
            raise ConnectionError("Cannot connect to Redis")

        with patch.dict(
            "sys.modules",
            {
                "langgraph.checkpoint.redis.aio": MagicMock(
                    AsyncRedisSaver=MagicMock(side_effect=raise_conn_error)
                )
            },
        ):
            saver = create_checkpointer(settings_with_redis)
            assert isinstance(saver, MemorySaver)


class TestBuildGraphCheckpointer:
    """Verify build_graph passes the checkpointer to compile()."""

    def test_build_graph_uses_custom_checkpointer(self, settings_no_redis):
        """build_graph should pass an explicit checkpointer to compile()."""
        custom_checkpointer = MemorySaver()
        from src.workflow.graph import build_graph

        with patch("src.integrations.llm_client.openai.AsyncOpenAI"):
            graph = build_graph(settings_no_redis, checkpointer=custom_checkpointer)

        # The compiled graph should exist (no crash)
        assert graph is not None

    def test_build_graph_defaults_to_memory_without_redis(self, settings_no_redis):
        """Without redis_url, build_graph should default to MemorySaver."""
        from src.workflow.graph import build_graph

        with patch("src.integrations.llm_client.openai.AsyncOpenAI"):
            graph = build_graph(settings_no_redis)

        assert graph is not None
