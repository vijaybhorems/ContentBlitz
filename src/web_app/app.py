"""ContentBlitz Streamlit Application — main entry point for the web UI."""

import asyncio
import uuid
from pathlib import Path

import streamlit as st

from src.core.config import Settings, get_settings
from src.utils.logging_config import setup_logging
from src.web_app.auth import GoogleOAuthHandler
from src.web_app.components.chat_interface import (
    add_assistant_message,
    add_user_message,
    render_chat_history,
    render_chat_input,
)
from src.web_app.components.content_preview import render_content_preview
from src.web_app.components.login import render_login_page, render_user_badge
from src.web_app.components.research_panel import render_research_sidebar
from src.web_app.components.sidebar import render_sidebar
from src.workflow.graph import build_graph

# Page config
st.set_page_config(
    page_title="ContentBlitz — AI Content Marketing",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Load custom CSS
css_path = Path(__file__).parent / "styles" / "custom.css"
if css_path.exists():
    st.markdown(f"<style>{css_path.read_text()}</style>", unsafe_allow_html=True)


def _init_session_state():
    """Initialize session state on first load."""
    if "initialized" not in st.session_state:
        st.session_state.initialized = True
        st.session_state.messages = []
        st.session_state.last_result = None

        settings = get_settings()
        setup_logging(settings.log_level, settings.environment)

        # Check API key availability
        st.session_state.openai_ok = bool(settings.openai_api_key)
        st.session_state.anthropic_ok = bool(settings.anthropic_api_key)
        st.session_state.tavily_ok = bool(settings.tavily_api_key)
        st.session_state.stability_ok = bool(settings.stability_api_key)


def _run_workflow(query: str, settings: Settings) -> dict:
    """Run the LangGraph workflow synchronously for Streamlit."""
    graph = build_graph(settings)

    # Map mode overrides
    mode_to_intent = {
        "Blog Post": "blog",
        "LinkedIn Post": "linkedin",
        "Research": "research",
        "Image": "image",
        "Strategy": "strategy",
    }

    initial_state = {
        "user_query": query,
        "errors": [],
        "processing_log": [],
    }

    # Unique thread per request; allows the checkpointer to track state
    config = {"configurable": {"thread_id": uuid.uuid4().hex}}

    loop = asyncio.new_event_loop()
    try:
        result = loop.run_until_complete(graph.ainvoke(initial_state, config=config))
    finally:
        loop.close()

    return result


def _get_oauth_handler(settings: Settings) -> GoogleOAuthHandler | None:
    """Return a configured OAuth handler, or None when OAuth is disabled."""
    if not settings.oauth_enabled:
        return None
    return GoogleOAuthHandler(
        client_id=settings.google_client_id,
        client_secret=settings.google_client_secret,
        redirect_uri=settings.oauth_redirect_uri,
    )


def _handle_auth(settings: Settings) -> bool:
    """Run the auth gate. Returns True when the user is allowed to proceed.

    - If OAuth is not configured (dev mode), always returns True.
    - If a valid user is already in session state, returns True.
    - If Google redirected back with ``?code=`` query params, exchanges
      the code, stores the user, and returns True.
    - Otherwise renders the login page and returns False (halts main()).
    """
    oauth = _get_oauth_handler(settings)
    if oauth is None:
        return True  # Auth disabled — open access

    # Already authenticated?
    if GoogleOAuthHandler.get_current_user():
        return True

    # Callback from Google? (query params contain code + state)
    params = st.query_params
    code = params.get("code")
    state = params.get("state")

    if code and state:
        with st.spinner("Signing you in…"):
            user, error_reason = oauth.handle_callback(code, state)

        # Clear OAuth params from the URL regardless of outcome
        st.query_params.clear()

        if user:
            GoogleOAuthHandler.set_user(user)
            st.rerun()
            return True  # rerun will re-enter with user set
        else:
            st.error("Sign-in failed — see details below.")
            with st.expander("Error details", expanded=True):
                st.markdown(error_reason or "Unknown error — check server logs.")
                st.markdown("---")
                st.markdown(
                    f"**Redirect URI the app is using:** `{settings.oauth_redirect_uri}`\n\n"
                    "This must be added exactly (including trailing slash) to "
                    "**Authorized redirect URIs** in "
                    "[Google Cloud Console → Credentials]"
                    "(https://console.cloud.google.com/apis/credentials)."
                )

    # Not authenticated — show login page
    render_login_page(oauth)
    return False


def main():
    _init_session_state()
    settings = get_settings()

    # ── Auth gate ─────────────────────────────────────────────────────────────
    if not _handle_auth(settings):
        return  # Login page already rendered; stop here

    # ── Authenticated — render user badge in sidebar ──────────────────────────
    user = GoogleOAuthHandler.get_current_user()
    if user:
        render_user_badge(user)

    # Sidebar
    sidebar_config = render_sidebar()

    # Main content area
    st.title("⚡ ContentBlitz")
    st.caption("AI-powered multi-agent content marketing assistant")

    # Layout: chat on left, preview on right
    chat_col, preview_col = st.columns([1, 1])

    with chat_col:
        st.subheader("Chat")
        render_chat_history()
        user_input = render_chat_input()

        if user_input:
            add_user_message(user_input)

            with st.chat_message("user"):
                st.markdown(user_input)

            with st.chat_message("assistant"):
                with st.spinner("Processing your request..."):
                    try:
                        result = _run_workflow(user_input, settings)
                        st.session_state.last_result = result

                        intent = result.get("intent", "unknown")

                        # Graceful rejection for unsafe/inappropriate requests
                        if intent == "rejected":
                            rejection_msg = result.get(
                                "rejection_message",
                                "This request cannot be completed as it falls outside acceptable use guidelines.",
                            )
                            st.warning(rejection_msg)
                            add_assistant_message(rejection_msg)
                        else:
                            # Build summary response
                            topic = result.get("target_topic", "")
                            log = result.get("processing_log", [])

                            summary = f"**{intent.title()}** content generated for *{topic}*\n\n"
                            summary += f"Pipeline: {' → '.join(log)}\n\n"

                            if result.get("blog_content"):
                                summary += f"📝 **Blog:** {result['blog_content'].title} ({result['blog_content'].word_count} words)\n\n"
                            if result.get("linkedin_content"):
                                summary += f"💼 **LinkedIn:** {result['linkedin_content'].character_count} chars ({result['linkedin_content'].hook_type} hook)\n\n"
                            if result.get("image_result"):
                                summary += f"🎨 **Image:** Generated via {result['image_result'].provider}\n\n"
                            if result.get("strategy_report"):
                                summary += f"📊 **Strategy:** {result['strategy_report'].title}\n\n"
                            if result.get("fact_check_result"):
                                fc = result["fact_check_result"]
                                summary += f"🛡️ **Trust Score:** {fc.trust_score}/100 ({fc.verified_claims}/{fc.total_claims} claims verified)\n\n"
                            if result.get("errors"):
                                summary += f"⚠️ **Errors:** {len(result['errors'])} issues encountered\n"

                            st.markdown(summary)
                            add_assistant_message(summary)

                    except Exception as e:
                        error_msg = f"Error: {e}"
                        st.error(error_msg)
                        add_assistant_message(error_msg)

    with preview_col:
        st.subheader("Content Preview")
        if st.session_state.get("last_result"):
            render_content_preview(st.session_state.last_result)
        else:
            st.info("Send a message to generate content. Results will appear here.")

    # Research sources in sidebar
    if st.session_state.get("last_result"):
        render_research_sidebar(st.session_state.last_result)


if __name__ == "__main__":
    main()
