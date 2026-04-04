"""Squarespace blog publishing client.

Squarespace does NOT have an official public API for creating blog posts.
This client uses the **internal CMS API** — the same endpoints that the
Squarespace admin editor calls when you create a post through the UI.

Authentication
--------------
Requires a Squarespace API key generated from:
  Admin → Settings → Developer → Developer API Keys

The key is sent as ``Authorization: Bearer <key>`` on all requests.

Setup
-----
Set these environment variables (or in ``.env``):
    SQUARESPACE_API_KEY=<your key>
    SQUARESPACE_BLOG_COLLECTION_ID=<collection id>  (visible in page settings)
    SQUARESPACE_SITE_URL=https://www.vijaybhore.dev

Limitations
-----------
- This API is undocumented by Squarespace and may change without notice.
- Only blog/news collection types are supported.
- Content must be provided as HTML (markdown is converted before calling).
"""

from __future__ import annotations

from typing import Optional

import httpx

from src.utils.logging_config import get_logger

logger = get_logger(__name__)


class SquarespacePublishError(Exception):
    """Raised when blog publishing fails."""

    def __init__(self, message: str, status_code: int | None = None, detail: str = ""):
        self.status_code = status_code
        self.detail = detail
        super().__init__(message)


def _markdown_to_html(md: str) -> str:
    """Convert markdown to HTML, falling back to basic conversion if
    the ``markdown`` package is not installed."""
    try:
        import markdown as md_lib

        return md_lib.markdown(
            md,
            extensions=["extra", "codehilite", "toc", "nl2br"],
        )
    except ImportError:
        # Minimal fallback — paragraphs, bold, italic, headers, links
        import re

        html = md
        # Headers (### → <h3>)
        for level in range(6, 0, -1):
            pat = re.compile(rf"^{'#' * level}\s+(.+)$", re.MULTILINE)
            html = pat.sub(rf"<h{level}>\1</h{level}>", html)
        # Bold **text** → <strong>
        html = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", html)
        # Italic *text* → <em>
        html = re.sub(r"\*(.+?)\*", r"<em>\1</em>", html)
        # Links [text](url) → <a>
        html = re.sub(r"\[(.+?)\]\((.+?)\)", r'<a href="\2">\1</a>', html)
        # Paragraphs (double newline)
        paragraphs = re.split(r"\n{2,}", html)
        html = "".join(
            f"<p>{p.strip()}</p>" if not p.strip().startswith("<h") else p.strip()
            for p in paragraphs
            if p.strip()
        )
        return html


class SquarespaceClient:
    """Publishes blog posts to a Squarespace site via the internal CMS API."""

    def __init__(
        self,
        api_key: str,
        site_url: str,
        blog_collection_id: str,
    ) -> None:
        self.api_key = api_key
        # Normalise — strip trailing slash
        self.site_url = site_url.rstrip("/")
        self.blog_collection_id = blog_collection_id

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "User-Agent": "ContentBlitz/1.0",
        }

    def publish_blog_post(
        self,
        title: str,
        body_markdown: str,
        *,
        tags: list[str] | None = None,
        meta_description: str = "",
        is_draft: bool = False,
        author_name: str = "",
    ) -> dict:
        """Create a blog post in the configured Squarespace collection.

        Args:
            title: Post title.
            body_markdown: Post body in markdown (converted to HTML).
            tags: Optional list of tags.
            meta_description: SEO meta description.
            is_draft: If True, post is saved as draft.
            author_name: Author display name.

        Returns:
            Dict with ``url`` and ``id`` of the created post.

        Raises:
            SquarespacePublishError: On any failure.
        """
        body_html = _markdown_to_html(body_markdown)

        payload: dict = {
            "title": title,
            "body": body_html,
            "draft": is_draft,
        }
        if tags:
            payload["tags"] = tags
        if meta_description:
            payload["excerpt"] = meta_description
        if author_name:
            payload["author"] = {"displayName": author_name}

        url = f"{self.site_url}/api/content/collection/{self.blog_collection_id}"

        logger.info(
            "squarespace_publish_attempt",
            title=title[:60],
            collection=self.blog_collection_id,
            draft=is_draft,
        )

        try:
            resp = httpx.post(url, json=payload, headers=self._headers(), timeout=30)
        except Exception as exc:
            raise SquarespacePublishError(
                f"Network error: {exc}",
                detail="Could not reach Squarespace. Check your SQUARESPACE_SITE_URL.",
            ) from exc

        if resp.status_code in (200, 201):
            data = resp.json()
            post_id = data.get("id", "")
            post_url_slug = data.get("urlId", data.get("fullUrl", ""))
            result = {
                "id": post_id,
                "url": f"{self.site_url}/news/{post_url_slug}" if post_url_slug else "",
                "title": title,
            }
            logger.info("squarespace_publish_success", **result)
            return result

        # ── Error handling ────────────────────────────────────────────────
        status = resp.status_code
        try:
            error_body = resp.json()
        except Exception:
            error_body = {"raw": resp.text[:500]}

        if status == 401:
            raise SquarespacePublishError(
                "Authentication failed (401).",
                status_code=status,
                detail=(
                    "Your SQUARESPACE_API_KEY is invalid or expired. "
                    "Generate a new one at: Admin → Settings → Developer → API Keys"
                ),
            )
        elif status == 403:
            raise SquarespacePublishError(
                "Forbidden (403).",
                status_code=status,
                detail=(
                    "The API key doesn't have write permissions for this collection. "
                    "Try regenerating the key with broader permissions, or check "
                    "that SQUARESPACE_BLOG_COLLECTION_ID is correct."
                ),
            )
        elif status == 404:
            raise SquarespacePublishError(
                "Collection not found (404).",
                status_code=status,
                detail=(
                    f"Collection ID '{self.blog_collection_id}' was not found. "
                    "Verify SQUARESPACE_BLOG_COLLECTION_ID in your .env."
                ),
            )
        else:
            raise SquarespacePublishError(
                f"Squarespace returned HTTP {status}.",
                status_code=status,
                detail=str(error_body)[:300],
            )
