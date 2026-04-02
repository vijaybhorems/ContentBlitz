"""Generate SVG files from Mermaid diagram definitions using Playwright."""

import json
from pathlib import Path
from playwright.sync_api import sync_playwright

OUTPUT_DIR = Path(__file__).parent / "diagrams"
OUTPUT_DIR.mkdir(exist_ok=True)

DIAGRAMS = {
    "01_full_system_architecture": """
flowchart TB
    subgraph UI["Web Interface - Streamlit / React"]
        CHAT["Conversational\\nChat Interface"]
        DASH["Content Dashboard\\n& Preview"]
        EXPORT["Export &\\nPublishing"]
    end

    CHAT --> QH
    DASH --> QH

    subgraph ORCHESTRATOR["LangGraph Orchestration Layer"]
        QH["Query Handler\\nAgent\\nIntent classification\\n& routing"]
        STATE["State Manager\\nLangGraph Checkpointer\\n+ Redis"]
        QH <--> STATE
    end

    subgraph BRAND["Brand Voice System"]
        BVE["Brand Voice\\nExtractor"]
        BVP["Voice Profile\\nStore"]
        BVE --> BVP
    end

    subgraph CORE_AGENTS["Core Content Agents"]
        RA["Deep Research\\nAgent"]
        BLOG["SEO Blog\\nWriter Agent"]
        LI["LinkedIn Post\\nWriter Agent"]
        IMG["Image Generation\\nAgent"]
        CS["Content\\nStrategist Agent"]
    end

    subgraph ENHANCEMENTS["Enhancement Agents"]
        HG["Hallucination\\nGuard Agent"]
        MCG["Multi-modal\\nCampaign Generator"]
        ABV["A/B Variant\\nGenerator"]
    end

    subgraph RESEARCH_DATA["Research Data Sources"]
        TAVILY["Tavily AI /\\nSERP API"]
        NEWS["NewsAPI /\\nGDELT"]
        ACADEMIC["Semantic Scholar /\\narXiv / CrossRef"]
        SOCIAL["Reddit API /\\nHN API"]
        TRENDS["Google Trends\\npytrends"]
    end

    subgraph SEO_DATA["SEO Data Sources"]
        KW["DataForSEO /\\nAhrefs API"]
        SERP["SERP Analysis\\nTop 10"]
        GSC["Google Search\\nConsole API"]
    end

    subgraph SOCIAL_DATA["Social Data Sources"]
        HASHTAG["RiteTag /\\nHashtagify"]
        LINKEDIN_DATA["LinkedIn Analytics\\nShield App"]
        BUZZSUMO["BuzzSumo API"]
    end

    subgraph IMAGE_DATA["Image Services"]
        DALLE["DALL-E 3"]
        STABILITY["Stability AI\\nSDXL"]
        UNSPLASH["Unsplash API"]
        CANVA["Canva API\\noptional"]
    end

    subgraph VERIFICATION["Verification Sources"]
        WIKI["Wikipedia /\\nWikidata"]
        WOLFRAM["Wolfram Alpha\\nAPI"]
        FACTCHECK["Google Fact Check\\nTools API"]
        CLAIMBUSTER["ClaimBuster\\nAPI"]
    end

    subgraph SCORING["Engagement Scoring"]
        COSCHEDULE["CoSchedule\\nHeadline Analyzer"]
        SHARETHROUGH["Sharethrough\\nScore API"]
        EMV["Advanced Marketing\\nInstitute EMV"]
        UPWORTHY["Upworthy Research\\nArchive 22k tests"]
    end

    subgraph BRAND_SOURCES["Brand Input Sources"]
        WEBSITE["Company Website\\nscraped"]
        BLOG_ARCHIVE["Existing Blog\\nPosts"]
        GUIDELINES["Brand Guidelines\\nPDF"]
        LI_PROFILE["LinkedIn Profile\\nPosts"]
    end

    QH --> RA & BLOG & LI & IMG & CS & MCG
    BVP -.->|voice profile injected\\ninto system prompts| BLOG & LI & CS & MCG & ABV

    RA --> TAVILY & NEWS & ACADEMIC & SOCIAL & TRENDS
    BLOG --> KW & SERP & GSC
    LI --> HASHTAG & LINKEDIN_DATA
    IMG --> DALLE & STABILITY & UNSPLASH & CANVA

    BLOG & LI & CS --> HG
    HG --> WIKI & WOLFRAM & FACTCHECK & CLAIMBUSTER
    HG -.->|flagged claims\\n+ trust score| DASH

    BLOG & LI --> ABV
    ABV --> COSCHEDULE & SHARETHROUGH & EMV & UPWORTHY & BUZZSUMO
    ABV -.->|ranked variants\\n+ score breakdown| DASH

    MCG --> RA
    MCG --> BLOG & LI & IMG
    MCG -.->|unified campaign\\npackage| DASH

    BVE --> WEBSITE & BLOG_ARCHIVE & GUIDELINES & LI_PROFILE

    EXPORT -.-> CMS["WordPress /\\nGhost / Medium"]
    EXPORT -.-> SCHEDULER["Buffer /\\nHootsuite"]

    style UI fill:#e8f0fe,stroke:#4285f4,color:#1a1a1a
    style ORCHESTRATOR fill:#e8f0fe,stroke:#1a73e8,color:#1a1a1a
    style CORE_AGENTS fill:#e8f0fe,stroke:#1a73e8,color:#1a1a1a
    style ENHANCEMENTS fill:#fce8e6,stroke:#d93025,color:#1a1a1a
    style RESEARCH_DATA fill:#e6f4ea,stroke:#1e8e3e,color:#1a1a1a
    style SEO_DATA fill:#e6f4ea,stroke:#1e8e3e,color:#1a1a1a
    style SOCIAL_DATA fill:#e6f4ea,stroke:#1e8e3e,color:#1a1a1a
    style IMAGE_DATA fill:#e6f4ea,stroke:#1e8e3e,color:#1a1a1a
    style VERIFICATION fill:#e6f4ea,stroke:#1e8e3e,color:#1a1a1a
    style SCORING fill:#e6f4ea,stroke:#1e8e3e,color:#1a1a1a
    style BRAND fill:#f3e8fd,stroke:#8430ce,color:#1a1a1a
    style BRAND_SOURCES fill:#f3e8fd,stroke:#8430ce,color:#1a1a1a

    style QH fill:#1a73e8,stroke:#1558b0,color:#fff
    style RA fill:#1a73e8,stroke:#1558b0,color:#fff
    style BLOG fill:#1a73e8,stroke:#1558b0,color:#fff
    style LI fill:#1a73e8,stroke:#1558b0,color:#fff
    style IMG fill:#1a73e8,stroke:#1558b0,color:#fff
    style CS fill:#1a73e8,stroke:#1558b0,color:#fff

    style HG fill:#d93025,stroke:#b3261e,color:#fff
    style MCG fill:#d93025,stroke:#b3261e,color:#fff
    style ABV fill:#d93025,stroke:#b3261e,color:#fff

    style BVE fill:#8430ce,stroke:#6a1fb0,color:#fff
    style BVP fill:#8430ce,stroke:#6a1fb0,color:#fff
    style STATE fill:#e37400,stroke:#b85c00,color:#fff
""",

    "02_hallucination_guard": """
flowchart LR
    subgraph INPUT["Input"]
        GC["Generated Content\\nblog / LinkedIn / report"]
        SS["Source Snippets\\nfrom Research Agent"]
    end

    subgraph PIPELINE["Hallucination Guard Pipeline"]
        direction TB
        CE["1. Claim Extractor\\nLLM extracts all factual\\nassertions as a list"]
        SM["2. Source Matcher\\nSemantic similarity check\\nagainst original snippets"]
        EV["3. External Verifier\\nChecks unmatched claims\\nagainst knowledge bases"]
        FL["4. Flagging Layer\\nClassify each claim"]
        CE --> SM --> EV --> FL
    end

    subgraph EXTERNAL["External Verification"]
        W["Wikipedia /\\nWikidata"]
        WA["Wolfram Alpha"]
        GFC["Google Fact\\nCheck API"]
        CB["ClaimBuster"]
    end

    subgraph OUTPUT["Output"]
        TS["Trust Score\\n0-100"]
        AC["Annotated Content\\nVerified / Unsupported /\\nContradicted"]
        REC["Recommendations\\nRephrase / add citation /\\nremove claim"]
    end

    GC --> CE
    SS --> SM
    EV --> W & WA & GFC & CB
    FL --> TS & AC & REC

    style INPUT fill:#e8f0fe,stroke:#1a73e8,color:#1a1a1a
    style PIPELINE fill:#fce8e6,stroke:#d93025,color:#1a1a1a
    style EXTERNAL fill:#e6f4ea,stroke:#1e8e3e,color:#1a1a1a
    style OUTPUT fill:#fef7e0,stroke:#e37400,color:#1a1a1a

    style CE fill:#d93025,stroke:#b3261e,color:#fff
    style SM fill:#d93025,stroke:#b3261e,color:#fff
    style EV fill:#d93025,stroke:#b3261e,color:#fff
    style FL fill:#d93025,stroke:#b3261e,color:#fff
""",

    "03_campaign_generator": """
flowchart TB
    TOPIC["Topic Input\\n+ Brand Profile"]

    subgraph RESEARCH["Phase 1: Shared Research"]
        RA2["Deep Research Agent\\nSingle research pass\\nshared across all outputs"]
    end

    subgraph PLANNING["Phase 2: Campaign Planning"]
        CP["Campaign Planner"]
        THESIS["Core Thesis"]
        MSGS["3 Key Messages"]
        HOOK["Emotional Hook"]
        PERSONA["Target Persona"]
        CP --> THESIS & MSGS & HOOK & PERSONA
    end

    subgraph GENERATION["Phase 3: Parallel Content Generation"]
        direction LR
        B["Blog Writer\\nUses: thesis + all 3 messages\\n+ SEO keyword"]
        L["LinkedIn Writer\\nUses: hook + 1 key message\\n+ different angle"]
        I["Image Prompt Engineer\\nUses: emotional hook\\n+ visual metaphor"]
    end

    subgraph COHERENCE["Phase 4: Coherence Check"]
        CC["Campaign Coherence Checker\\nValidates:\\nHeadline alignment across formats\\nCTA consistency\\nVisual-to-text message match\\nNo contradictory claims"]
    end

    subgraph PACKAGE["Campaign Package Output"]
        direction LR
        OBLOG["SEO Blog Post\\n~1500 words"]
        OLI["LinkedIn Post\\n~200 words"]
        OIMG["Hero Image\\n1200x630px"]
        OMETA["Campaign Brief\\n+ Style Notes"]
    end

    TOPIC --> RA2
    RA2 --> CP
    CP --> B & L & I
    B & L & I --> CC
    CC --> OBLOG & OLI & OIMG & OMETA

    style TOPIC fill:#8430ce,stroke:#6a1fb0,color:#fff
    style RESEARCH fill:#e8f0fe,stroke:#1a73e8,color:#1a1a1a
    style PLANNING fill:#fce8e6,stroke:#d93025,color:#1a1a1a
    style GENERATION fill:#e8f0fe,stroke:#1a73e8,color:#1a1a1a
    style COHERENCE fill:#fce8e6,stroke:#d93025,color:#1a1a1a
    style PACKAGE fill:#e6f4ea,stroke:#1e8e3e,color:#1a1a1a

    style RA2 fill:#1a73e8,stroke:#1558b0,color:#fff
    style CP fill:#d93025,stroke:#b3261e,color:#fff
    style CC fill:#d93025,stroke:#b3261e,color:#fff
    style B fill:#1a73e8,stroke:#1558b0,color:#fff
    style L fill:#1a73e8,stroke:#1558b0,color:#fff
    style I fill:#1a73e8,stroke:#1558b0,color:#fff
""",

    "04_ab_variant_generator": """
flowchart TB
    INPUT2["Content Input\\nheadline, post, CTA"]

    subgraph STRATEGY["Variant Strategy Engine"]
        direction TB
        VS["Variant Strategist"]
        HOOKS["Hook Rotation Matrix"]
        CTAS["CTA Rotation Matrix"]
        VS --> HOOKS & CTAS
    end

    subgraph HOOK_TYPES["Hook Types Applied"]
        direction LR
        H1["Question Hook\\nAre you still doing X\\nthe old way?"]
        H2["Stat Hook\\n73% of marketers\\nstruggle with..."]
        H3["Story Hook\\nLast month a startup\\ndiscovered..."]
        H4["Provocation Hook\\nEverything you know\\nabout X is wrong"]
    end

    subgraph SCORING2["Engagement Scoring Pipeline"]
        direction TB
        S1["CoSchedule\\nHeadline Analyzer\\nReadability + word balance"]
        S2["Sharethrough\\nScore API\\nEngagement prediction"]
        S3["EMV Analysis\\nEmotional marketing\\nvalue score"]
        S4["LLM Scoring Rubric\\nFew-shot from Upworthy\\n22k A/B test dataset"]
        S5["BuzzSumo\\nVirality potential"]
    end

    subgraph OUTPUT2["Ranked Output"]
        direction LR
        V1["Variant A\\nScore: 87/100\\nStat-led hook\\nStrong for LinkedIn"]
        V2["Variant B\\nScore: 74/100\\nQuestion hook\\nStrong for blog H1"]
        V3["Variant C\\nScore: 68/100\\nStory hook\\nStrong for email"]
    end

    INPUT2 --> VS
    HOOKS --> H1 & H2 & H3 & H4
    H1 & H2 & H3 & H4 --> S1 & S2 & S3 & S4 & S5
    S1 & S2 & S3 & S4 & S5 --> V1 & V2 & V3

    style INPUT2 fill:#8430ce,stroke:#6a1fb0,color:#fff
    style STRATEGY fill:#fce8e6,stroke:#d93025,color:#1a1a1a
    style HOOK_TYPES fill:#e8f0fe,stroke:#1a73e8,color:#1a1a1a
    style SCORING2 fill:#e6f4ea,stroke:#1e8e3e,color:#1a1a1a
    style OUTPUT2 fill:#fef7e0,stroke:#e37400,color:#1a1a1a

    style VS fill:#d93025,stroke:#b3261e,color:#fff
""",

    "05_brand_voice_extraction": """
flowchart LR
    subgraph SOURCES["Brand Input Sources"]
        direction TB
        WEB["Company Website\\nBeautifulSoup scrape"]
        BLOGS["Existing Blog\\nPosts URL list"]
        PDF2["Brand Guidelines\\nPDF pdfplumber"]
        LIP["LinkedIn Profile\\nPosts Apify"]
        SAMPLES["User Writing\\nSamples pasted"]
    end

    subgraph EXTRACTION["Voice Analysis Pipeline"]
        direction TB
        TE["Tone Extractor\\nFormality level\\nHumor frequency\\nTechnical depth"]
        SE["Style Fingerprint\\nAvg sentence length\\nActive vs passive voice\\nParagraph structure"]
        VE["Vocabulary Map\\nPreferred terms\\nBanned words\\nIndustry jargon"]
        AE["Analogy Patterns\\nMetaphor style\\nExample types\\nCultural references"]
    end

    subgraph PROFILE["Voice Profile in Redis"]
        VP["Brand Voice Profile\\nJSON schema with\\nall extracted attributes"]
    end

    subgraph INJECTION["System Prompt Injection"]
        direction TB
        A1["Blog Writer"]
        A2["LinkedIn Writer"]
        A3["Content Strategist"]
        A4["Campaign Generator"]
        A5["A/B Variant Generator"]
    end

    WEB & BLOGS & PDF2 & LIP & SAMPLES --> TE & SE & VE & AE
    TE & SE & VE & AE --> VP
    VP -->|injected into\\nsystem prompt| A1 & A2 & A3 & A4 & A5

    style SOURCES fill:#f3e8fd,stroke:#8430ce,color:#1a1a1a
    style EXTRACTION fill:#fce8e6,stroke:#d93025,color:#1a1a1a
    style PROFILE fill:#fef7e0,stroke:#e37400,color:#1a1a1a
    style INJECTION fill:#e8f0fe,stroke:#1a73e8,color:#1a1a1a
    style VP fill:#e37400,stroke:#b85c00,color:#fff
""",

    "06_technology_stack": """
flowchart TB
    subgraph FRONTEND["Frontend Layer"]
        ST["Streamlit / React"]
    end

    subgraph ORCHESTRATION["Orchestration Layer"]
        LG["LangGraph\\nWorkflow engine"]
        SM2["State Management\\nRedis + Checkpointer"]
    end

    subgraph AGENTS["Agent Layer - 9 Agents"]
        direction LR
        BASE["Base Agents x6\\nQuery Handler - Research\\nBlog - LinkedIn - Image\\nContent Strategist"]
        ENH["Enhancement Agents x3\\nHallucination Guard\\nCampaign Generator\\nA/B Variant Generator"]
    end

    subgraph MODELS["LLM / Generation Layer"]
        direction LR
        GPT["OpenAI GPT-4\\nPrimary LLM"]
        CLAUDE["Claude Sonnet\\nFallback LLM"]
        GEMINI["Google Gemini\\nFallback LLM"]
        DALLE2["DALL-E 3\\nImage gen"]
        SDXL["Stability AI\\nImage fallback"]
    end

    subgraph DATA["External Data Layer - 20+ APIs"]
        direction LR
        SEARCH["Search & Research\\nTavily, SERP, NewsAPI\\nSemantic Scholar, Reddit"]
        SEOD["SEO & Analytics\\nDataForSEO, Ahrefs\\nGoogle Search Console"]
        SOCIALD["Social & Engagement\\nRiteTag, BuzzSumo\\nLinkedIn Analytics"]
        VERIFY["Verification\\nWikipedia, Wolfram Alpha\\nFact Check API, ClaimBuster"]
        SCORE["Scoring\\nCoSchedule, Sharethrough\\nEMV, Upworthy Dataset"]
    end

    subgraph OBSERVE["Observability Layer"]
        LS["LangSmith"]
        WB["Weights & Biases"]
        HC["Helicone"]
    end

    ST <--> LG
    LG <--> SM2
    LG <--> AGENTS
    AGENTS <--> MODELS
    AGENTS <--> DATA
    AGENTS -.-> OBSERVE

    style FRONTEND fill:#e8f0fe,stroke:#4285f4,color:#1a1a1a
    style ORCHESTRATION fill:#e8f0fe,stroke:#1a73e8,color:#1a1a1a
    style AGENTS fill:#e8f0fe,stroke:#1a73e8,color:#1a1a1a
    style MODELS fill:#f3e8fd,stroke:#8430ce,color:#1a1a1a
    style DATA fill:#e6f4ea,stroke:#1e8e3e,color:#1a1a1a
    style OBSERVE fill:#fef7e0,stroke:#e37400,color:#1a1a1a
"""
}

HTML_TEMPLATE = """<!DOCTYPE html>
<html><head>
<script src="https://cdn.jsdelivr.net/npm/mermaid@11/dist/mermaid.min.js"></script>
<script>
mermaid.initialize({{
    startOnLoad: false,
    theme: 'default',
    flowchart: {{ htmlLabels: false, curve: 'basis' }}
}});
window.onload = async function() {{
    const {{ svg }} = await mermaid.render('diagram', document.getElementById('source').textContent);
    document.getElementById('output').innerHTML = svg;
    document.title = 'DONE';
}};
</script>
</head><body style="margin:0;padding:20px;background:white;">
<pre id="source" style="display:none">{diagram}</pre>
<div id="output"></div>
</body></html>"""


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch()

        for name, mermaid_code in DIAGRAMS.items():
            print(f"Rendering {name}...")
            html = HTML_TEMPLATE.format(diagram=mermaid_code.strip())
            tmp_html = OUTPUT_DIR / f"_tmp_{name}.html"
            tmp_html.write_text(html)

            # Use a large viewport so diagrams aren't clipped
            page = browser.new_page(viewport={"width": 3200, "height": 2400})
            page.goto(f"file://{tmp_html.resolve()}")
            page.wait_for_function("document.title === 'DONE'", timeout=30000)

            # Get bounding box of the rendered SVG element
            svg_el = page.query_selector("#output svg")
            bbox = svg_el.bounding_box()

            # Screenshot just the SVG area with 2x scale for crisp output
            png_path = OUTPUT_DIR / f"{name}.png"
            page.screenshot(
                path=str(png_path),
                clip={
                    "x": max(0, bbox["x"] - 10),
                    "y": max(0, bbox["y"] - 10),
                    "width": bbox["width"] + 20,
                    "height": bbox["height"] + 20,
                },
                scale="device",
            )
            page.close()
            tmp_html.unlink()
            print(f"  -> saved {png_path}")

        browser.close()
    print(f"\nAll {len(DIAGRAMS)} SVGs saved to {OUTPUT_DIR}/")


if __name__ == "__main__":
    main()
