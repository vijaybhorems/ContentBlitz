"""SEO scoring and content optimization utilities."""

import re
from dataclasses import dataclass


@dataclass
class SEOScore:
    """Breakdown of SEO scoring factors."""

    overall: float
    keyword_in_title: bool
    keyword_in_first_paragraph: bool
    keyword_density: float
    heading_structure: bool
    meta_description_length: bool
    word_count_ok: bool
    has_internal_structure: bool
    details: list[str]


def calculate_seo_score(
    title: str,
    body: str,
    meta_description: str,
    primary_keyword: str,
    min_words: int = 1200,
    max_words: int = 1800,
) -> SEOScore:
    """Calculate an SEO quality score for a blog post.

    Args:
        title: Blog post title.
        body: Full body text (markdown).
        meta_description: Meta description.
        primary_keyword: Primary keyword to optimize for.
        min_words: Minimum word count.
        max_words: Maximum word count.

    Returns:
        SEOScore with overall score 0-100 and factor breakdown.
    """
    details: list[str] = []
    score = 0.0
    keyword_lower = primary_keyword.lower()

    # 1. Keyword in title (15 points)
    kw_in_title = keyword_lower in title.lower()
    if kw_in_title:
        score += 15
    else:
        details.append(f"Primary keyword '{primary_keyword}' not found in title")

    # 2. Keyword in first paragraph (10 points)
    paragraphs = [p.strip() for p in body.split("\n\n") if p.strip() and not p.strip().startswith("#")]
    first_para = paragraphs[0].lower() if paragraphs else ""
    kw_in_first = keyword_lower in first_para
    if kw_in_first:
        score += 10
    else:
        details.append("Primary keyword not found in first paragraph")

    # 3. Keyword density (15 points) — target 1-2%
    words = body.lower().split()
    word_count = len(words)
    if word_count > 0:
        kw_count = body.lower().count(keyword_lower)
        kw_density = (kw_count / word_count) * 100
        if 0.5 <= kw_density <= 2.5:
            score += 15
        elif 0.2 <= kw_density <= 3.0:
            score += 8
            details.append(f"Keyword density {kw_density:.1f}% — aim for 1-2%")
        else:
            details.append(f"Keyword density {kw_density:.1f}% — significantly outside 1-2% target")
    else:
        kw_density = 0.0

    # 4. Heading structure (15 points) — H2s and H3s present
    h2_count = len(re.findall(r"^##\s", body, re.MULTILINE))
    h3_count = len(re.findall(r"^###\s", body, re.MULTILINE))
    has_headings = h2_count >= 2 and h3_count >= 1
    if has_headings:
        score += 15
    elif h2_count >= 2:
        score += 10
        details.append("Consider adding H3 subheadings for better structure")
    else:
        details.append(f"Only {h2_count} H2 headings — aim for 3+")

    # 5. Meta description (10 points)
    meta_ok = 120 <= len(meta_description) <= 160
    if meta_ok:
        score += 10
    elif meta_description:
        score += 5
        details.append(f"Meta description is {len(meta_description)} chars — aim for 120-160")
    else:
        details.append("Missing meta description")

    # 6. Word count (15 points)
    wc_ok = min_words <= word_count <= max_words
    if wc_ok:
        score += 15
    elif word_count >= min_words * 0.8:
        score += 10
        details.append(f"Word count {word_count} — slightly under target {min_words}")
    else:
        details.append(f"Word count {word_count} — target is {min_words}-{max_words}")

    # 7. Internal structure (20 points) — lists, bold, links
    has_lists = bool(re.search(r"^[-*]\s", body, re.MULTILINE) or re.search(r"^\d+\.\s", body, re.MULTILINE))
    has_bold = "**" in body
    has_structure = has_lists and has_bold
    if has_structure:
        score += 20
    elif has_lists or has_bold:
        score += 12
        details.append("Add more formatting (bold, lists) for scanability")
    else:
        details.append("Content lacks formatting — add bold text, bullet points, or numbered lists")

    return SEOScore(
        overall=round(min(score, 100), 1),
        keyword_in_title=kw_in_title,
        keyword_in_first_paragraph=kw_in_first,
        keyword_density=round(kw_density, 2),
        heading_structure=has_headings,
        meta_description_length=meta_ok,
        word_count_ok=wc_ok,
        has_internal_structure=has_structure,
        details=details,
    )


def estimate_reading_time(word_count: int, wpm: int = 238) -> int:
    """Estimate reading time in minutes."""
    return max(1, round(word_count / wpm))
