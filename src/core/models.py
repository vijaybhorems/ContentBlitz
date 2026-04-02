"""Pydantic models for structured content outputs."""

from typing import Optional

from pydantic import BaseModel, Field


class Source(BaseModel):
    """A research source with URL and snippet."""

    url: str
    title: str
    snippet: str
    relevance_score: float = Field(default=0.0, ge=0.0, le=1.0)


class ResearchResult(BaseModel):
    """Output from the Deep Research Agent."""

    query: str
    sources: list[Source] = Field(default_factory=list)
    summary: str = ""
    key_findings: list[str] = Field(default_factory=list)
    raw_snippets: list[str] = Field(default_factory=list)
    search_queries_used: list[str] = Field(default_factory=list)


class BlogContent(BaseModel):
    """Output from the SEO Blog Writer Agent."""

    title: str
    meta_description: str
    body_markdown: str
    word_count: int = 0
    keywords_used: list[str] = Field(default_factory=list)
    seo_score: Optional[float] = None
    headers: list[str] = Field(default_factory=list)


class LinkedInContent(BaseModel):
    """Output from the LinkedIn Post Writer Agent."""

    post_text: str
    hashtags: list[str] = Field(default_factory=list)
    hook_type: str = ""
    character_count: int = 0


class ImageResult(BaseModel):
    """Output from the Image Generation Agent."""

    image_url: Optional[str] = None
    image_base64: Optional[str] = None
    prompt_used: str = ""
    revised_prompt: Optional[str] = None
    provider: str = ""  # "dalle3" or "stability"


class StrategyReport(BaseModel):
    """Output from the Content Strategist Agent."""

    title: str
    executive_summary: str
    sections: list[dict] = Field(default_factory=list)
    content_angles: list[str] = Field(default_factory=list)
    sources_cited: list[Source] = Field(default_factory=list)


class Claim(BaseModel):
    """A factual claim extracted for verification."""

    text: str
    status: str = "pending"  # verified | unsupported | contradicted
    source_match: Optional[str] = None
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)


class FactCheckResult(BaseModel):
    """Output from the Hallucination Guard Agent."""

    trust_score: float = Field(default=0.0, ge=0.0, le=100.0)
    total_claims: int = 0
    verified_claims: int = 0
    claims: list[Claim] = Field(default_factory=list)
    flagged_claims: list[Claim] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)


class Variant(BaseModel):
    """A single A/B variant with hook, content, and engagement score."""

    hook_type: str = ""  # question | statistic | story | provocation | contrast
    headline: str = ""
    body_preview: str = ""  # First 2-3 sentences rewritten with this hook
    score: float = Field(default=0.0, ge=0.0, le=100.0)
    score_breakdown: dict = Field(default_factory=dict)  # per-dimension scores
    rationale: str = ""  # Why this variant works


class ABVariantResult(BaseModel):
    """Output from the A/B Variant Generator Agent."""

    original_headline: str = ""
    original_hook_type: str = ""
    variants: list[Variant] = Field(default_factory=list)
    recommendation: str = ""  # Which variant to use and why
    content_type: str = ""  # "blog" or "linkedin"


class LLMResponse(BaseModel):
    """Standardized response from LLM providers."""

    content: str
    model: str
    provider: str  # "openai" or "anthropic"
    usage: dict = Field(default_factory=dict)
