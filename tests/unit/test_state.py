"""Tests for state schema."""

from src.core.state import ContentState, _merge_lists
from src.core.models import ResearchResult


class TestContentState:
    def test_create_minimal_state(self):
        state: ContentState = {"user_query": "test", "errors": [], "processing_log": []}
        assert state["user_query"] == "test"

    def test_merge_lists_reducer(self):
        result = _merge_lists(["a", "b"], ["c"])
        assert result == ["a", "b", "c"]

    def test_merge_lists_empty(self):
        result = _merge_lists([], ["a"])
        assert result == ["a"]

    def test_state_with_research(self, sample_research_result):
        state: ContentState = {
            "user_query": "test",
            "research_results": sample_research_result,
            "errors": [],
            "processing_log": [],
        }
        assert len(state["research_results"].sources) == 5

    def test_state_optional_fields(self):
        """ContentState uses total=False so all fields are optional."""
        state: ContentState = {}
        assert state.get("intent") is None
        assert state.get("blog_content") is None
