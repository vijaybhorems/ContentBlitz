"""Research panel component — displays source attribution."""

import streamlit as st


def render_research_sidebar(result: dict):
    """Render research sources in the sidebar."""
    research = result.get("research_results")
    if not research or not research.sources:
        return

    with st.sidebar:
        st.divider()
        st.subheader(f"Sources ({len(research.sources)})")
        for source in research.sources[:5]:
            st.markdown(f"**[{source.title}]({source.url})**")
            st.caption(source.snippet[:100] + "...")
