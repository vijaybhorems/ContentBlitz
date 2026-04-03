"""Google OAuth 2.0 handler for ContentBlitz.

Flow
----
1. `get_auth_url()` — builds the Google authorization URL with an HMAC-signed
   state token.  No session state is written — the token is self-verifying.
2. User is redirected to Google, approves, and Google sends them back to the
   app with ``?code=AUTH_CODE&state=STATE`` query parameters.
3. `handle_callback(code, state)` — verifies the HMAC signature of the state
   token (no session lookup needed), exchanges the code for an access token,
   then fetches the user's profile from Google.
4. Returns ``(user_dict, None)`` on success or ``(None, error_reason)`` on
   failure so the caller can show a specific error message.

Why HMAC state instead of session state?
-----------------------------------------
Streamlit creates a **new session** every time the browser navigates away and
comes back (which is exactly what happens during an OAuth redirect).  Storing
the CSRF token in ``st.session_state`` therefore never survives the round-trip
to Google.  An HMAC-signed state token is self-contained: we can verify it
purely from its contents using the client secret as the signing key, with no
server-side storage required.

OAuth is **optional** — when ``GOOGLE_CLIENT_ID`` is not configured the app
runs without any authentication gate (useful for local development).
"""

from __future__ import annotations

import hashlib
import hmac
import secrets
from typing import Optional
from urllib.parse import urlencode

import httpx
import streamlit as st

from src.utils.logging_config import get_logger

logger = get_logger(__name__)

# ── Google OAuth 2.0 endpoints ────────────────────────────────────────────────
_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
_TOKEN_URL = "https://oauth2.googleapis.com/token"
_USERINFO_URL = "https://www.googleapis.com/oauth2/v3/userinfo"

# Session-state key for the authenticated user
_KEY_USER = "user"


# ── HMAC state helpers ────────────────────────────────────────────────────────

def _make_state(client_secret: str) -> str:
    """Return a self-verifying CSRF state token: ``<nonce>.<hmac_hex>``.

    The HMAC is computed over the nonce using the OAuth client secret as the
    key, so it can be re-verified on the callback without any server-side
    storage.
    """
    nonce = secrets.token_urlsafe(24)
    sig = hmac.new(
        client_secret.encode(),
        nonce.encode(),
        hashlib.sha256,
    ).hexdigest()[:24]
    return f"{nonce}.{sig}"


def _verify_state(state: str, client_secret: str) -> bool:
    """Return True when ``state`` carries a valid HMAC for this client secret."""
    try:
        nonce, received_sig = state.rsplit(".", 1)
    except ValueError:
        logger.warning("oauth_state_bad_format")
        return False

    expected_sig = hmac.new(
        client_secret.encode(),
        nonce.encode(),
        hashlib.sha256,
    ).hexdigest()[:24]

    valid = hmac.compare_digest(expected_sig, received_sig)
    if not valid:
        logger.warning("oauth_state_invalid_hmac")
    return valid


# ── Main handler class ────────────────────────────────────────────────────────

class GoogleOAuthHandler:
    """Manages the Google OAuth 2.0 authorization-code flow for Streamlit."""

    def __init__(self, client_id: str, client_secret: str, redirect_uri: str) -> None:
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri

    # ── Public API ────────────────────────────────────────────────────────────

    def get_auth_url(self) -> str:
        """Return the Google authorization URL with an HMAC-signed state token."""
        state = _make_state(self.client_secret)

        params = {
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "response_type": "code",
            "scope": "openid email profile",
            "state": state,
            "access_type": "offline",
            "prompt": "select_account",
        }
        return f"{_AUTH_URL}?{urlencode(params)}"

    def handle_callback(self, code: str, state: str) -> tuple[Optional[dict], Optional[str]]:
        """Exchange ``code`` for user info after verifying the HMAC ``state``.

        Returns:
            ``(user_dict, None)`` on success.
            ``(None, error_reason)`` on any failure so the caller can display
            a specific, actionable error message.
        """
        # ── 1. CSRF verification (stateless HMAC) ─────────────────────────────
        if not _verify_state(state, self.client_secret):
            reason = (
                "State token verification failed. This usually means "
                "GOOGLE_CLIENT_SECRET in your .env doesn't match the secret "
                "used when the login link was generated. "
                "Check that GOOGLE_CLIENT_SECRET is set correctly."
            )
            logger.warning("oauth_callback_rejected_bad_state")
            return None, reason

        # ── 2. Exchange authorization code for tokens ─────────────────────────
        try:
            token_resp = httpx.post(
                _TOKEN_URL,
                data={
                    "code": code,
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "redirect_uri": self.redirect_uri,
                    "grant_type": "authorization_code",
                },
                timeout=15,
            )
        except Exception as exc:
            reason = f"Network error contacting Google: {exc}"
            logger.error("oauth_token_exchange_failed", error=str(exc))
            return None, reason

        tokens = token_resp.json()

        # Google returns 4xx with a JSON error body on auth failures —
        # don't raise_for_status(); read the error field instead.
        if "error" in tokens:
            google_error = tokens["error"]
            google_desc = tokens.get("error_description", "")

            if google_error == "redirect_uri_mismatch":
                reason = (
                    f"**redirect_uri_mismatch** — Google rejected the redirect URI.\n\n"
                    f"App is sending: `{self.redirect_uri}`\n\n"
                    f"Fix: add exactly that URI to your OAuth client's "
                    f"**Authorized redirect URIs** in "
                    f"[Google Cloud Console](https://console.cloud.google.com/apis/credentials) "
                    f"(including any trailing slash)."
                )
            elif google_error == "invalid_client":
                reason = (
                    "**invalid_client** — GOOGLE_CLIENT_ID or GOOGLE_CLIENT_SECRET "
                    "is wrong. Double-check both values in your .env file against "
                    "the Google Cloud Console credentials page."
                )
            else:
                reason = (
                    f"**{google_error}** — {google_desc or 'No description from Google.'}"
                )

            logger.error(
                "oauth_token_error",
                error=google_error,
                description=google_desc,
                redirect_uri=self.redirect_uri,
            )
            return None, reason

        access_token = tokens.get("access_token")
        if not access_token:
            reason = (
                f"Google returned no access_token. Response keys: "
                f"{list(tokens.keys())}"
            )
            logger.error("oauth_no_access_token", response_keys=list(tokens.keys()))
            return None, reason

        # ── 3. Fetch user profile ─────────────────────────────────────────────
        try:
            user_resp = httpx.get(
                _USERINFO_URL,
                headers={"Authorization": f"Bearer {access_token}"},
                timeout=10,
            )
            user_resp.raise_for_status()
            user = user_resp.json()
        except Exception as exc:
            reason = f"Failed to fetch user profile from Google: {exc}"
            logger.error("oauth_userinfo_failed", error=str(exc))
            return None, reason

        logger.info("oauth_login_success", email=user.get("email", "unknown"))
        return user, None

    # ── Helpers ───────────────────────────────────────────────────────────────

    @staticmethod
    def get_current_user() -> Optional[dict]:
        """Return the authenticated user dict, or ``None`` if not logged in."""
        return st.session_state.get(_KEY_USER)

    @staticmethod
    def set_user(user: dict) -> None:
        """Persist authenticated user info into session state."""
        st.session_state[_KEY_USER] = user

    @staticmethod
    def logout() -> None:
        """Clear the authenticated user from session state."""
        st.session_state.pop(_KEY_USER, None)
        logger.info("oauth_logout")
