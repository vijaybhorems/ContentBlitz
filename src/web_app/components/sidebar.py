"""Streamlit sidebar component — settings, API status, and mode selection."""

import streamlit as st


def render_sidebar() -> dict:
    """Render the sidebar and return current settings.

    Returns:
        Dict with content_mode and any overrides.
    """
    with st.sidebar:
        st.title("ContentBlitz")
        st.caption("AI Content Marketing Assistant")
        st.divider()

        # Content mode selector
        content_mode = st.selectbox(
            "Content Mode",
            options=["Auto-detect", "Blog Post", "LinkedIn Post", "Research", "Image", "Strategy"],
            help="Auto-detect lets the AI classify your intent. Or choose a specific mode.",
        )

        st.divider()

        # API Status
        st.subheader("API Status")
        _show_api_status("OpenAI", st.session_state.get("openai_ok"))
        _show_api_status("Anthropic", st.session_state.get("anthropic_ok"))
        _show_api_status("Tavily", st.session_state.get("tavily_ok"))
        _show_api_status("Stability AI", st.session_state.get("stability_ok"), optional=True)

        st.divider()

        # Advanced settings
        with st.expander("Advanced Settings"):
            temperature = st.slider("LLM Temperature", 0.0, 1.0, 0.7, 0.1)
            max_tokens = st.number_input("Max Tokens", 1024, 8192, 4096, 512)

        st.divider()
        st.caption("Built with LangGraph + OpenAI + Claude")

    return {
        "content_mode": content_mode,
        "temperature": temperature if "temperature" in dir() else 0.7,
        "max_tokens": max_tokens if "max_tokens" in dir() else 4096,
    }


def _show_api_status(name: str, is_ok: bool | None, optional: bool = False):
    """Show API connection status indicator."""
    if is_ok is True:
        st.markdown(f"✅ **{name}** — Connected")
    elif is_ok is False:
        if optional:
            st.markdown(f"⚪ **{name}** — Not configured (optional)")
        else:
            st.markdown(f"❌ **{name}** — Not connected")
    else:
        st.markdown(f"⚪ **{name}** — Checking...")
