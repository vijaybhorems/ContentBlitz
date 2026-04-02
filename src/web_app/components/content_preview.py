"""Content preview component — tabbed display of generated content."""

import base64

import streamlit as st

from src.utils.content_optimizer import calculate_seo_score, estimate_reading_time


def render_content_preview(result: dict):
    """Render tabs for all generated content types."""
    tabs_needed = []
    if result.get("blog_content"):
        tabs_needed.append("Blog Post")
    if result.get("linkedin_content"):
        tabs_needed.append("LinkedIn Post")
    if result.get("image_result"):
        tabs_needed.append("Image")
    if result.get("strategy_report"):
        tabs_needed.append("Strategy Report")
    if result.get("fact_check_result"):
        tabs_needed.append("Fact Check")
    if result.get("ab_variants"):
        tabs_needed.append("A/B Variants")
    if result.get("research_results"):
        tabs_needed.append("Research")

    if not tabs_needed:
        st.info("No content generated yet.")
        return

    tabs = st.tabs(tabs_needed)
    tab_index = 0

    if result.get("blog_content"):
        with tabs[tab_index]:
            _render_blog(result["blog_content"], result.get("target_keywords", []))
        tab_index += 1

    if result.get("linkedin_content"):
        with tabs[tab_index]:
            _render_linkedin(result["linkedin_content"])
        tab_index += 1

    if result.get("image_result"):
        with tabs[tab_index]:
            _render_image(result["image_result"])
        tab_index += 1

    if result.get("strategy_report"):
        with tabs[tab_index]:
            _render_strategy(result["strategy_report"])
        tab_index += 1

    if result.get("fact_check_result"):
        with tabs[tab_index]:
            _render_fact_check(result["fact_check_result"])
        tab_index += 1

    if result.get("ab_variants"):
        with tabs[tab_index]:
            _render_ab_variants(result["ab_variants"])
        tab_index += 1

    if result.get("research_results"):
        with tabs[tab_index]:
            _render_research(result["research_results"])
        tab_index += 1


def _render_blog(blog, keywords: list):
    """Render blog post with SEO metrics."""
    st.subheader(blog.title)

    col1, col2, col3 = st.columns(3)
    col1.metric("Word Count", blog.word_count)
    col2.metric("Reading Time", f"{estimate_reading_time(blog.word_count)} min")

    # Calculate SEO score
    primary_kw = keywords[0] if keywords else ""
    if primary_kw:
        seo = calculate_seo_score(blog.title, blog.body_markdown, blog.meta_description, primary_kw)
        col3.metric("SEO Score", f"{seo.overall}/100")
        if seo.details:
            with st.expander("SEO Suggestions"):
                for detail in seo.details:
                    st.markdown(f"- {detail}")

    st.caption(f"**Meta:** {blog.meta_description}")
    st.divider()
    st.markdown(blog.body_markdown)

    # Copy button
    st.download_button(
        "Download as Markdown",
        data=f"# {blog.title}\n\n{blog.body_markdown}",
        file_name="blog_post.md",
        mime="text/markdown",
    )


def _render_linkedin(li):
    """Render LinkedIn post preview."""
    st.subheader("LinkedIn Post")

    col1, col2 = st.columns(2)
    col1.metric("Characters", li.character_count)
    col2.metric("Hook Type", li.hook_type.title())

    st.divider()
    st.text_area("Post Preview", li.post_text, height=300, disabled=True)

    if li.hashtags:
        st.markdown("**Hashtags:** " + " ".join(li.hashtags))

    st.download_button(
        "Copy to Clipboard",
        data=li.post_text + "\n\n" + " ".join(li.hashtags),
        file_name="linkedin_post.txt",
        mime="text/plain",
    )


def _render_image(img):
    """Render generated image."""
    st.subheader("Generated Image")
    st.caption(f"Provider: {img.provider} | Prompt: {img.prompt_used[:200]}")

    if img.image_url:
        st.image(img.image_url, use_container_width=True)
    elif img.image_base64:
        image_bytes = base64.b64decode(img.image_base64)
        st.image(image_bytes, use_container_width=True)
    else:
        st.warning("No image data available")

    if img.revised_prompt:
        with st.expander("Revised Prompt (by DALL-E)"):
            st.markdown(img.revised_prompt)


def _render_strategy(report):
    """Render strategy report."""
    st.subheader(report.title)
    st.markdown(f"**Executive Summary:** {report.executive_summary}")

    for section in report.sections:
        with st.expander(section.get("heading", "Section")):
            st.markdown(section.get("content", ""))
            data_points = section.get("data_points", [])
            if data_points:
                for dp in data_points:
                    st.markdown(f"- {dp}")

    if report.content_angles:
        st.subheader("Recommended Content Angles")
        for i, angle in enumerate(report.content_angles, 1):
            st.markdown(f"{i}. {angle}")


def _render_fact_check(fc):
    """Render fact check results."""
    st.subheader("Hallucination Guard Report")

    col1, col2, col3 = st.columns(3)
    col1.metric("Trust Score", f"{fc.trust_score}/100")
    col2.metric("Claims Verified", f"{fc.verified_claims}/{fc.total_claims}")
    col3.metric("Flagged", len(fc.flagged_claims))

    if fc.flagged_claims:
        st.warning(f"{len(fc.flagged_claims)} claims need attention")
        for claim in fc.flagged_claims:
            status_icon = "⚠️" if claim.status == "unsupported" else "❌"
            st.markdown(f"{status_icon} **{claim.status.title()}:** {claim.text}")

    if fc.recommendations:
        with st.expander("Recommendations"):
            for rec in fc.recommendations:
                st.markdown(f"- {rec}")

    if fc.claims:
        with st.expander(f"All Claims ({len(fc.claims)})"):
            for claim in fc.claims:
                icon = {"verified": "✅", "unsupported": "⚠️", "contradicted": "❌"}.get(claim.status, "❓")
                st.markdown(f"{icon} {claim.text}")


def _render_research(research):
    """Render research results and sources."""
    st.subheader("Research Results")
    st.markdown(research.summary)

    if research.key_findings:
        st.subheader("Key Findings")
        for finding in research.key_findings:
            st.markdown(f"- {finding}")

    if research.sources:
        st.subheader(f"Sources ({len(research.sources)})")
        for source in research.sources:
            with st.expander(f"{source.title} (relevance: {source.relevance_score:.0%})"):
                st.markdown(f"**URL:** {source.url}")
                st.markdown(source.snippet)


def _render_ab_variants(ab):
    """Render A/B variant comparison."""
    st.subheader("A/B Variant Generator")
    st.caption(f"Content type: {ab.content_type} | Original: {ab.original_headline[:60]}")

    if not ab.variants:
        st.info("No variants generated.")
        return

    # Top recommendation
    if ab.recommendation:
        st.success(f"**Recommendation:** {ab.recommendation}")

    st.divider()

    # Render each variant as a card
    for i, variant in enumerate(ab.variants):
        medal = {0: "\U0001f947", 1: "\U0001f948", 2: "\U0001f949"}.get(i, f"#{i + 1}")
        hook_emoji = {
            "question": "\u2753",
            "statistic": "\U0001f4ca",
            "story": "\U0001f4d6",
            "provocation": "\u26a1",
            "contrast": "\U0001f504",
        }.get(variant.hook_type, "\U0001f4dd")

        with st.expander(
            f"{medal} {hook_emoji} {variant.hook_type.title()} Hook — Score: {variant.score:.0f}/100",
            expanded=(i == 0),
        ):
            st.markdown(f"### {variant.headline}")

            if variant.body_preview:
                st.markdown(f"*{variant.body_preview}*")

            # Score breakdown
            if variant.score_breakdown:
                cols = st.columns(len(variant.score_breakdown))
                for col, (dim, score) in zip(cols, variant.score_breakdown.items()):
                    col.metric(dim.replace("_", " ").title(), f"{score}/20")

            if variant.rationale:
                st.caption(f"**Why it works:** {variant.rationale}")

    # Comparison table
    if len(ab.variants) > 1:
        st.divider()
        st.subheader("Score Comparison")
        import pandas as pd

        rows = []
        for v in ab.variants:
            row = {"Hook": v.hook_type.title(), "Headline": v.headline[:50], "Score": v.score}
            row.update({k.replace("_", " ").title(): val for k, val in v.score_breakdown.items()})
            rows.append(row)
        df = pd.DataFrame(rows)
        st.dataframe(df, use_container_width=True, hide_index=True)
