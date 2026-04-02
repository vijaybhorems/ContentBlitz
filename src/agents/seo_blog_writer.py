"""SEO Blog Writer Agent — generates search-optimized long-form blog posts."""

import re
from typing import Any

from src.agents.base_agent import BaseAgent
from src.core.models import BlogContent
from src.core.state import ContentState


class SEOBlogWriterAgent(BaseAgent):
    """Creates SEO-optimized blog posts from research results."""

    agent_name = "seo_blog_writer"

    async def process(self, state: ContentState) -> dict[str, Any]:
        topic = state.get("target_topic", "")
        keywords = state.get("target_keywords", [])
        research = state.get("research_results")

        # Build context from research
        research_context = ""
        if research:
            research_context = (
                f"\n\nRESEARCH SUMMARY:\n{research.summary}\n\n"
                "KEY FINDINGS:\n" + "\n".join(f"- {f}" for f in research.key_findings) + "\n\n"
                "SOURCES:\n" + "\n".join(
                    f"- {s.title} ({s.url}): {s.snippet[:200]}" for s in research.sources[:8]
                )
            )

        keyword_instruction = ""
        if keywords:
            keyword_instruction = f"\n\nPrimary keyword: {keywords[0]}\nSecondary keywords: {', '.join(keywords[1:])}"

        messages = self._build_messages(
            f"Write a comprehensive SEO blog post about: {topic}\n"
            f"{keyword_instruction}"
            f"{research_context}\n\n"
            f"Target word count: {self.settings.blog_min_words}-{self.settings.blog_max_words} words."
        )

        result = await self.llm.generate_json(messages, max_tokens=6000)

        body = result.get("body_markdown", "")
        word_count = len(body.split())
        headers = self._extract_headers(body)

        blog = BlogContent(
            title=result.get("title", f"Guide to {topic}"),
            meta_description=result.get("meta_description", "")[:160],
            body_markdown=body,
            word_count=word_count,
            keywords_used=result.get("keywords_used", keywords),
            headers=result.get("headers", headers),
        )

        self.logger.info(
            "blog_generated",
            title=blog.title,
            word_count=blog.word_count,
            headers_count=len(blog.headers),
        )

        return {"blog_content": blog}

    @staticmethod
    def _extract_headers(markdown: str) -> list[str]:
        """Extract H2 and H3 headers from markdown."""
        return re.findall(r"^#{2,3}\s+(.+)$", markdown, re.MULTILINE)
