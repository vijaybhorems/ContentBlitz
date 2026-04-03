"""Login page component for ContentBlitz."""

from __future__ import annotations

from typing import Optional

import streamlit as st

from src.web_app.auth import GoogleOAuthHandler


def render_login_page(oauth: GoogleOAuthHandler) -> None:
    """Render the full-page login screen."""
    # Centre the login card
    _, col, _ = st.columns([1, 1.6, 1])

    with col:
        st.markdown("<br><br>", unsafe_allow_html=True)

        st.markdown(
            """
            <div style="text-align:center; margin-bottom: 8px;">
                <span style="font-size:3rem;">⚡</span>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.title("ContentBlitz")
        st.caption("AI-powered multi-agent content marketing assistant")

        st.markdown("---")
        st.markdown(
            "<p style='text-align:center; color:#555; margin-bottom:20px;'>"
            "Sign in to continue</p>",
            unsafe_allow_html=True,
        )

        auth_url = oauth.get_auth_url()

        # Render a styled "Sign in with Google" button via a link
        st.markdown(
            f"""
            <div style="display:flex; justify-content:center; margin-top:8px;">
                <a href="{auth_url}" target="_self"
                   style="display:inline-flex; align-items:center; gap:10px;
                          background:#fff; color:#3c4043; border:1px solid #dadce0;
                          border-radius:4px; padding:10px 24px; font-size:15px;
                          font-weight:500; text-decoration:none; box-shadow:0 1px 3px rgba(0,0,0,.12);
                          transition:box-shadow .2s;">
                    <svg width="20" height="20" viewBox="0 0 48 48">
                        <path fill="#EA4335" d="M24 9.5c3.5 0 6.6 1.2 9 3.2l6.7-6.7C35.8 2.5 30.2 0 24 0 14.8 0 6.9 5.4 3 13.3l7.8 6C12.7 13.2 17.9 9.5 24 9.5z"/>
                        <path fill="#4285F4" d="M46.6 24.5c0-1.6-.1-3.1-.4-4.5H24v8.5h12.7c-.6 3-2.3 5.5-4.8 7.2l7.6 5.9c4.4-4.1 7.1-10.1 7.1-17.1z"/>
                        <path fill="#FBBC05" d="M10.8 28.7A14.5 14.5 0 0 1 9.5 24c0-1.6.3-3.2.8-4.7L2.5 13.3A23.9 23.9 0 0 0 0 24c0 3.8.9 7.4 2.5 10.6l8.3-5.9z"/>
                        <path fill="#34A853" d="M24 48c6.2 0 11.4-2 15.2-5.5l-7.6-5.9c-2 1.4-4.7 2.2-7.6 2.2-6.1 0-11.3-3.7-13.2-9l-7.8 6C6.9 42.6 14.8 48 24 48z"/>
                    </svg>
                    Sign in with Google
                </a>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown(
            "<p style='text-align:center;font-size:12px;color:#aaa;'>"
            "By signing in you agree to use this service for professional content marketing only.</p>",
            unsafe_allow_html=True,
        )


def render_user_badge(user: dict) -> None:
    """Render a compact user avatar + name + logout button in the sidebar."""
    picture = user.get("picture", "")
    name = user.get("name", user.get("email", "User"))
    email = user.get("email", "")

    with st.sidebar:
        st.markdown("---")
        if picture:
            st.markdown(
                f"""
                <div style="display:flex;align-items:center;gap:10px;margin-bottom:4px;">
                    <img src="{picture}" width="36" height="36"
                         style="border-radius:50%;border:1px solid #ddd;">
                    <div>
                        <div style="font-weight:600;font-size:13px;">{name}</div>
                        <div style="font-size:11px;color:#888;">{email}</div>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        else:
            st.markdown(f"**{name}**  \n<small>{email}</small>", unsafe_allow_html=True)

        if st.button("Sign out", use_container_width=True):
            GoogleOAuthHandler.logout()
            st.rerun()
