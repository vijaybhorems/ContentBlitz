"""Chat interface component for conversational content creation."""

import streamlit as st


def render_chat_history():
    """Render the conversation history."""
    for msg in st.session_state.get("messages", []):
        role = msg["role"]
        content = msg["content"]

        with st.chat_message(role):
            if isinstance(content, dict):
                _render_rich_response(content)
            else:
                st.markdown(content)


def render_chat_input() -> str | None:
    """Render chat input and return the user's message."""
    return st.chat_input(
        "What content would you like to create? (e.g., 'Write a blog about AI in healthcare')"
    )


def add_user_message(message: str):
    """Add a user message to the conversation."""
    if "messages" not in st.session_state:
        st.session_state.messages = []
    st.session_state.messages.append({"role": "user", "content": message})


def add_assistant_message(content: str | dict):
    """Add an assistant message to the conversation."""
    if "messages" not in st.session_state:
        st.session_state.messages = []
    st.session_state.messages.append({"role": "assistant", "content": content})


def _render_rich_response(content: dict):
    """Render a structured response with intent and processing info."""
    intent = content.get("intent", "unknown")
    topic = content.get("topic", "")
    processing = content.get("processing_log", [])

    st.markdown(f"**Intent:** {intent} | **Topic:** {topic}")
    if processing:
        st.caption(f"Pipeline: {' → '.join(processing)}")

    if content.get("summary"):
        st.markdown(content["summary"])
