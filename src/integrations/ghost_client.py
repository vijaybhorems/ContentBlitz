"""Ghost Admin API client for publishing blog posts.

Uses the official Ghost Admin API with JWT authentication.
https://ghost.org/docs/admin-api/

Setup
-----
1. In Ghost Admin go to **Settings → Integrations → Add Custom Integration**.
2. Copy the **Admin API Key** (format ``<id>:<hex_secret>``).
3. Set these env vars (or add to ``.env``):
       GHOST_ADMIN_API_KEY=<id>:<hex_secret>
       GHOST_API_URL=https://lens.vijaybhore.dev
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import httpx
import jwt  # PyJWT

from src.utils.logging_config import get_logger

logger = get_logger(__name__)


class GhostPublishError(Exception):
    """Raised when Ghost publishing fails."""

    def __init__(self, message: str, status_code: int | None = None, detail: str = ""):
        self.status_code = status_code
        self.detail = detail
        super().__init__(message)


def _markdown_to_html(md: str) -> str:
    """Convert markdown to HTML for Ghost."""
    try:
        import markdown as md_lib

        return md_lib.markdown(
            md,
            extensions=["extra", "codehilite", "toc", "nl2br"],
        )
    except ImportError:
        import re

        html = md
        for level in range(6, 0, -1):
            pat = re.compile(rf"^{'#' * level}\s+(.+)$", re.MULTILINE)
            html = pat.sub(rf"<h{level}>\1</h{level}>", html)
        html = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", html)
        html = re.sub(r"\*(.+?)\*", r"<em>\1</em>", html)
        html = re.sub(r"\[(.+?)\]\((.+?)\)", r'<a href="\2">\1</a>', html)
        paragraphs = re.split(r"\n{2,}", html)
        html = "".join(
            f"<p>{p.strip()}</p>" if not p.strip().startswith("<h") else p.strip()
            for p in paragraphs
            if p.strip()
        )
        return html


class GhostClient:
    """Publishes blog posts via the Ghost Admin API."""

    def __init__(self, api_url: str, admin_api_key: str) -> None:
        self.api_url = api_url.rstrip("/")
        if ":" not in admin_api_key:
            raise GhostPublishError(
                "Invalid GHOST_ADMIN_API_KEY format.",
                detail=(
                    "The key must be in `id:secret` format. "
                    "Get it from Ghost Admin → Settings → Integrations → "
                    "your integration → Admin API Key."
                ),
            )
        self._key_id, self._key_secret = admin_api_key.split(":", 1)

    # ── JWT auth ──────────────────────────────────────────────────────────────

    def _make_token(self) -> str:
        """Generate a short-lived JWT for the Ghost Admin API."""
        now = int(datetime.now(timezone.utc).timestamp())
        payload = {
            "iat": now,
            "exp": now + 300,  # 5 minutes max
            "aud": "/admin/",
        }
        return jwt.encode(
            payload,
            bytes.fromhex(self._key_secret),
            algorithm="HS256",
            headers={"kid": self._key_id},
        )

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Ghost {self._make_token()}",
            "Content-Type": "application/json",
        }

    # ── Publish ───────────────────────────────────────────────────────────────

    def publish_blog_post(
        self,
        title: str,
        body_markdown: str,
        *,
        tags: list[str] | None = None,
        meta_description: str = "",
        is_draft: bool = False,
    ) -> dict[str, Any]:
        """Create a blog post on Ghost.

        Args:
            title: Post title.
            body_markdown: Post body in markdown (converted to HTML).
            tags: Optional tag names (created automatically if new).
            meta_description: SEO meta description.
            is_draft: If True, saved as draft; otherwise published immediately.

        Returns:
            Dict with ``url``, ``id``, and ``title`` of the created post.

        Raises:
            GhostPublishError: On any failure.
        """
        body_html = _markdown_to_html(body_markdown)

        # Wrap in HTML card markers for lossless preservation in Ghost editor
        wrapped_html = (
            f"<!--kg-card-begin: html-->{body_html}<!--kg-card-end: html-->"
        )

        post_data: dict[str, Any] = {
            "title": title,
            "html": wrapped_html,
            "status": "draft" if is_draft else "published",
        }
        if tags:
            post_data["tags"] = tags
        if meta_description:
            post_data["meta_description"] = meta_description
            post_data["custom_excerpt"] = meta_description

        url = f"{self.api_url}/ghost/api/admin/posts/?source=html"

        logger.info(
            "ghost_publish_attempt",
            title=title[:60],
            status=post_data["status"],
        )

        try:
            resp = httpx.post(
                url,
                json={"posts": [post_data]},
                headers=self._headers(),
                timeout=30,
                follow_redirects=True,
            )
        except Exception as exc:
            raise GhostPublishError(
                f"Network error: {exc}",
                detail=f"Could not reach Ghost at {self.api_url}. Check GHOST_API_URL.",
            ) from exc

        if resp.status_code in (200, 201):
            data = resp.json()
            post = data.get("posts", [{}])[0]
            result = {
                "id": post.get("id", ""),
                "url": post.get("url", ""),
                "title": post.get("title", title),
                "status": post.get("status", ""),
            }
            logger.info("ghost_publish_success", **result)
            return result

        # ── Error handling ────────────────────────────────────────────────
        status = resp.status_code
        try:
            error_body = resp.json()
            errors = error_body.get("errors", [{}])
            error_msg = errors[0].get("message", "") if errors else ""
            error_type = errors[0].get("type", "") if errors else ""
        except Exception:
            error_msg = resp.text[:300]
            error_type = ""

        if status == 401:
            raise GhostPublishError(
                "Authentication failed (401).",
                status_code=status,
                detail=(
                    f"Ghost said: *{error_msg}*\n\n"
                    "Your GHOST_ADMIN_API_KEY is invalid or expired. "
                    "Regenerate it at: Ghost Admin → Settings → Integrations → "
                    "your custom integration → Admin API Key."
                ),
            )
        elif status == 403:
            raise GhostPublishError(
                "Forbidden (403).",
                status_code=status,
                detail=f"Ghost said: *{error_msg}*\n\nThe API key lacks permissions.",
            )
        elif status == 422:
            raise GhostPublishError(
                "Validation error (422).",
                status_code=status,
                detail=f"Ghost rejected the post: *{error_msg}* ({error_type})",
            )
        else:
            raise GhostPublishError(
                f"Ghost returned HTTP {status}.",
                status_code=status,
                detail=f"{error_type}: {error_msg}" if error_type else error_msg,
            )
