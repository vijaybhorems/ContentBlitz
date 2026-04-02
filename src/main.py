"""ContentBlitz entry point — run the workflow programmatically or start the web app."""

import asyncio
import sys
import uuid

from src.core.config import get_settings
from src.utils.logging_config import setup_logging
from src.workflow.graph import build_graph


async def run_query(query: str) -> dict:
    """Run a single query through the ContentBlitz workflow.

    Args:
        query: Natural language content request.

    Returns:
        Final workflow state dict.
    """
    settings = get_settings()
    setup_logging(settings.log_level, settings.environment)

    graph = build_graph(settings)

    # thread_id is required when a checkpointer is attached to the graph
    config = {"configurable": {"thread_id": uuid.uuid4().hex}}

    result = await graph.ainvoke(
        {"user_query": query, "errors": [], "processing_log": []},
        config=config,
    )
    return result


def main():
    """CLI entry point."""
    if len(sys.argv) < 2:
        print("Usage: python -m src.main '<query>'")
        print("  Example: python -m src.main 'Write a blog about AI in healthcare'")
        sys.exit(1)

    query = " ".join(sys.argv[1:])
    result = asyncio.run(run_query(query))

    print("\n" + "=" * 60)
    intent = result.get("intent")
    print(f"Intent: {intent}")

    if intent == "rejected":
        print(f"\n{result.get('rejection_message', 'Request could not be completed.')}")
        return

    print(f"Topic: {result.get('target_topic')}")
    print(f"Processing: {' → '.join(result.get('processing_log', []))}")

    if result.get("blog_content"):
        blog = result["blog_content"]
        print(f"\n📝 Blog: {blog.title}")
        print(f"   Words: {blog.word_count}")
        print(f"   SEO Score: {blog.seo_score}")

    if result.get("linkedin_content"):
        li = result["linkedin_content"]
        print(f"\n💼 LinkedIn Post ({li.character_count} chars, {li.hook_type} hook)")
        print(f"   {li.post_text[:200]}...")

    if result.get("image_result"):
        img = result["image_result"]
        print(f"\n🎨 Image: {img.provider}")
        print(f"   Prompt: {img.prompt_used[:100]}")

    if result.get("strategy_report"):
        sr = result["strategy_report"]
        print(f"\n📊 Strategy: {sr.title}")

    if result.get("fact_check_result"):
        fc = result["fact_check_result"]
        print(f"\n🛡️ Trust Score: {fc.trust_score}/100 ({fc.verified_claims}/{fc.total_claims} claims verified)")

    if result.get("errors"):
        print(f"\n⚠️ Errors: {result['errors']}")


if __name__ == "__main__":
    main()
