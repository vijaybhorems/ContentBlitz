"""Tests for workflow routing conditions."""

import pytest

from src.workflow.conditions import route_after_content, route_after_research, route_by_intent


class TestRouteByIntent:
    def test_image_routes_direct(self):
        assert route_by_intent({"intent": "image"}) == "image_generation"

    def test_blog_routes_to_research(self):
        assert route_by_intent({"intent": "blog"}) == "deep_research"

    def test_linkedin_routes_to_research(self):
        assert route_by_intent({"intent": "linkedin"}) == "deep_research"

    def test_research_routes_to_research(self):
        assert route_by_intent({"intent": "research"}) == "deep_research"

    def test_strategy_routes_to_research(self):
        assert route_by_intent({"intent": "strategy"}) == "deep_research"

    def test_missing_intent_defaults_to_research(self):
        assert route_by_intent({}) == "deep_research"


class TestRouteAfterResearch:
    def test_blog_routes_to_writer(self):
        assert route_after_research({"intent": "blog"}) == "seo_blog_writer"

    def test_linkedin_routes_to_writer(self):
        assert route_after_research({"intent": "linkedin"}) == "linkedin_writer"

    def test_strategy_routes_to_strategist(self):
        assert route_after_research({"intent": "strategy"}) == "content_strategist"

    def test_research_routes_to_strategist(self):
        assert route_after_research({"intent": "research"}) == "content_strategist"

    def test_unknown_defaults_to_strategist(self):
        assert route_after_research({"intent": "unknown"}) == "content_strategist"


class TestRouteAfterContent:
    def test_blog_routes_to_fact_check(self):
        assert route_after_content({"intent": "blog"}) == "hallucination_guard"

    def test_linkedin_routes_to_fact_check(self):
        assert route_after_content({"intent": "linkedin"}) == "hallucination_guard"

    def test_strategy_routes_to_end(self):
        assert route_after_content({"intent": "strategy"}) == "__end__"

    def test_research_routes_to_end(self):
        assert route_after_content({"intent": "research"}) == "__end__"

    def test_empty_routes_to_end(self):
        assert route_after_content({}) == "__end__"
