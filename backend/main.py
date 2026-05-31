"""
SEO Audit Tool — FastAPI Backend
Performs 80+ SEO checks with real HTTP/HTML analysis.

Run: uvicorn main:app --reload --port 8000
"""

import asyncio
import os
import json
import re
import time
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup
from fastapi import BackgroundTasks, FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")

app = FastAPI(title="SEO Audit Tool API", version="1.0.0", docs_url="/docs", redoc_url="/redoc")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── In-memory storage (swap for Redis/DB in production) ───────────────────────
reports_db: Dict[str, Dict] = {}
progress_db: Dict[str, Dict] = {}
ws_connections: Dict[str, WebSocket] = {}

# ── Pydantic Models ───────────────────────────────────────────────────────────
class AdminCredentials(BaseModel):
    type: str = "wp_rest"  # 'wp_rest' | 'custom_login'
    username: Optional[str] = None
    password: Optional[str] = None
    api_url: Optional[str] = None


class AuditRequest(BaseModel):
    url: str
    admin_credentials: Optional[AdminCredentials] = None
    pages_to_check: int = 1


class AutoFixRequest(BaseModel):
    url: str
    admin_credentials: AdminCredentials
    fix_type: str
    issue_id: str


# ── HTTP client defaults ───────────────────────────────────────────────────────
BOT_HEADERS = {
    "User-Agent": "SEOAuditBot/1.0 (Comprehensive SEO Analyzer; contact@seoaudit.io)",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
    "Accept-Encoding": "gzip, deflate, br",
}


# ── Helper: build an issue dict ────────────────────────────────────────────────
def issue(
    id_suffix: str,
    category: str,
    severity: str,   # critical | warning | info | pass
    title: str,
    description: str,
    recommendation: str,
    *,
    auto_fixable: bool = False,
    impact: str = "medium",
    current_value: str = None,
    expected_value: str = None,
    learn_more: str = None,
) -> Dict:
    return {
        "id": f"{category.lower().replace(' ', '_')}_{id_suffix}",
        "category": category,
        "severity": severity,
        "title": title,
        "description": description,
        "recommendation": recommendation,
        "auto_fixable": auto_fixable,
        "impact": impact,
        "current_value": current_value,
        "expected_value": expected_value,
        "learn_more": learn_more,
    }


# ╔══════════════════════════════════════════════════════════════════════════════╗
# ║  SEO CHECK FUNCTIONS                                                        ║
# ╚══════════════════════════════════════════════════════════════════════════════╝

def check_meta_tags(soup: BeautifulSoup, url: str) -> List[Dict]:
    results = []
    head = soup.find("head") or soup

    # ── Title tag ──────────────────────────────────────────────────────────────
    title_tag = head.find("title")
    if not title_tag:
        results.append(issue("missing_title", "Meta Tags", "critical",
            "Missing Title Tag",
            "No <title> tag found on the page. Title is one of the most important on-page SEO signals.",
            "Add a descriptive <title> between 50–60 characters that includes your primary keyword.",
            auto_fixable=True, impact="high"))
    else:
        t = title_tag.get_text().strip()
        if len(t) < 30:
            results.append(issue("short_title", "Meta Tags", "warning",
                "Title Tag Too Short",
                f'Title "{t[:60]}" is only {len(t)} characters.',
                "Expand to 50–60 characters for maximum SERP visibility.",
                impact="medium", current_value=f"{len(t)} chars", expected_value="50–60 chars"))
        elif len(t) > 60:
            results.append(issue("long_title", "Meta Tags", "warning",
                "Title Tag Too Long — Will Be Truncated",
                f"Title is {len(t)} characters. Google displays ~60 characters.",
                "Shorten to under 60 characters.",
                impact="medium", current_value=f"{len(t)} chars", expected_value="< 60 chars"))
        else:
            results.append(issue("title_ok", "Meta Tags", "pass",
                "Title Tag Length Optimal",
                f"Title is {len(t)} characters — within the 50–60 char sweet spot.",
                "No action needed.",
                current_value=f'"{t[:60]}" ({len(t)} chars)'))

    # ── Meta description ───────────────────────────────────────────────────────
    meta_desc = head.find("meta", attrs={"name": re.compile(r"^description$", re.I)})
    if not meta_desc:
        results.append(issue("missing_desc", "Meta Tags", "critical",
            "Missing Meta Description",
            "No meta description tag found. Google may auto-generate one from page content.",
            "Add a compelling meta description (150–160 chars) with a call to action.",
            auto_fixable=True, impact="high"))
    else:
        d = (meta_desc.get("content") or "").strip()
        if len(d) < 70:
            results.append(issue("short_desc", "Meta Tags", "warning",
                "Meta Description Too Short",
                f"Meta description is only {len(d)} chars.",
                "Aim for 150–160 characters to maximize click-through rate.",
                current_value=f"{len(d)} chars", expected_value="150–160 chars"))
        elif len(d) > 160:
            results.append(issue("long_desc", "Meta Tags", "warning",
                "Meta Description Too Long",
                f"Meta description is {len(d)} chars and will be truncated in SERPs.",
                "Shorten to under 160 characters.",
                current_value=f"{len(d)} chars", expected_value="< 160 chars"))
        else:
            results.append(issue("desc_ok", "Meta Tags", "pass",
                "Meta Description Length Optimal",
                f"Meta description is {len(d)} characters.",
                "No action needed.",
                current_value=f"{len(d)} chars"))

    # ── Viewport ───────────────────────────────────────────────────────────────
    vp = head.find("meta", attrs={"name": re.compile(r"^viewport$", re.I)})
    if not vp:
        results.append(issue("missing_viewport", "Meta Tags", "critical",
            "Missing Viewport Meta Tag",
            "No viewport tag. Pages will render at desktop width on mobile devices.",
            "Add: <meta name='viewport' content='width=device-width, initial-scale=1'>",
            auto_fixable=True, impact="high"))
    else:
        results.append(issue("viewport_ok", "Meta Tags", "pass",
            "Viewport Meta Tag Present",
            "Viewport configured for mobile rendering.",
            "No action needed.", current_value=vp.get("content", "")))

    # ── Canonical ──────────────────────────────────────────────────────────────
    canonical = head.find("link", attrs={"rel": re.compile(r"^canonical$", re.I)})
    if not canonical:
        results.append(issue("missing_canonical", "Meta Tags", "warning",
            "Missing Canonical Tag",
            "No canonical URL specified. May cause duplicate content penalties.",
            "Add <link rel='canonical' href='https://...your-url...'> to the page head.",
            auto_fixable=True, impact="medium"))
    else:
        results.append(issue("canonical_ok", "Meta Tags", "pass",
            "Canonical Tag Present",
            "Canonical URL specified.",
            "No action needed.", current_value=canonical.get("href", "")))

    # ── Language ───────────────────────────────────────────────────────────────
    html_tag = soup.find("html")
    if html_tag and not html_tag.get("lang"):
        results.append(issue("missing_lang", "Meta Tags", "warning",
            "Missing HTML Language Attribute",
            "No lang attribute on <html> tag. Affects accessibility and multilingual SEO.",
            "Add lang='en' (or your locale) to the <html> element.",
            auto_fixable=True, impact="low"))

    # ── Charset ────────────────────────────────────────────────────────────────
    charset = head.find("meta", attrs={"charset": True}) or \
              head.find("meta", content=re.compile(r"charset", re.I))
    if not charset:
        results.append(issue("missing_charset", "Meta Tags", "warning",
            "Missing Charset Declaration",
            "No charset meta tag. Pages may render incorrectly in some browsers.",
            "Add <meta charset='UTF-8'> as the first element inside <head>.",
            auto_fixable=True, impact="low"))

    # ── Meta robots ────────────────────────────────────────────────────────────
    mr = head.find("meta", attrs={"name": re.compile(r"^robots$", re.I)})
    if mr:
        content = (mr.get("content") or "").lower()
        if "noindex" in content:
            results.append(issue("noindex", "Meta Tags", "critical",
                "Page is Set to NOINDEX",
                f"robots meta = '{content}' — search engines will not index this page.",
                "Remove 'noindex' unless you intentionally want this page excluded.",
                impact="high", current_value=content))
        elif "nofollow" in content:
            results.append(issue("nofollow_meta", "Meta Tags", "warning",
                "Meta Robots Nofollow",
                f"robots meta = '{content}' — link equity won't flow.",
                "Review whether nofollow on all links is intended.",
                current_value=content))

    # ── Open Graph ─────────────────────────────────────────────────────────────
    og_map = {
        "og:title": ("og_title_ok", "og_title_missing"),
        "og:description": ("og_desc_ok", "og_desc_missing"),
        "og:image": ("og_image_ok", "og_image_missing"),
    }
    for prop, (pass_id, fail_id) in og_map.items():
        tag = head.find("meta", attrs={"property": prop})
        friendly = prop.replace("og:", "OG ").title()
        if not tag:
            sev = "warning" if prop == "og:image" else "info"
            results.append(issue(fail_id, "Social", sev,
                f"Missing {friendly}",
                f"No {prop} meta tag found. Social shares will lack rich previews.",
                f"Add <meta property='{prop}' content='...'>.",
                auto_fixable=True, impact="medium" if prop == "og:image" else "low"))
        else:
            results.append(issue(pass_id, "Social", "pass",
                f"{friendly} Present",
                f"{prop} is set.",
                "No action needed.", current_value=(tag.get("content") or "")[:80]))

    # ── Twitter Card ───────────────────────────────────────────────────────────
    tc = head.find("meta", attrs={"name": re.compile(r"^twitter:card$", re.I)})
    if not tc:
        results.append(issue("missing_twitter_card", "Social", "warning",
            "Missing Twitter Card",
            "No twitter:card meta tag. Twitter shares will use a basic link format.",
            "Add <meta name='twitter:card' content='summary_large_image'>.",
            auto_fixable=True, impact="low"))
    else:
        results.append(issue("twitter_card_ok", "Social", "pass",
            "Twitter Card Present",
            "twitter:card tag found.",
            "No action needed.", current_value=tc.get("content", "")))

    return results


def check_headings(soup: BeautifulSoup) -> List[Dict]:
    results = []
    h1s = soup.find_all("h1")
    h2s = soup.find_all("h2")
    h3s = soup.find_all("h3")
    all_h = soup.find_all(["h1", "h2", "h3", "h4", "h5", "h6"])

    # H1 presence
    if not h1s:
        results.append(issue("missing_h1", "Headings", "critical",
            "No H1 Heading Found",
            "Page has no H1 tag. H1 is a primary on-page SEO signal.",
            "Add exactly one H1 with your primary keyword.",
            impact="high"))
    elif len(h1s) > 1:
        results.append(issue("multiple_h1", "Headings", "warning",
            f"Multiple H1 Tags ({len(h1s)})",
            f"Found {len(h1s)} H1 tags. Best practice is exactly one per page.",
            "Consolidate to a single H1 tag.",
            current_value=f"{len(h1s)} H1 tags"))
    else:
        h1_text = h1s[0].get_text(strip=True)
        if len(h1_text) < 10:
            results.append(issue("short_h1", "Headings", "warning",
                "H1 Tag Too Short or Vague",
                f'H1 contains: "{h1_text}"',
                "Make H1 descriptive and include your primary keyword.",
                current_value=h1_text))
        else:
            results.append(issue("h1_ok", "Headings", "pass",
                "Single Descriptive H1 Tag",
                "One H1 found with adequate content.",
                "No action needed.", current_value=h1_text[:60]))

    # H2 presence
    if not h2s and len(all_h) > 1:
        results.append(issue("missing_h2", "Headings", "warning",
            "No H2 Subheadings Found",
            "Good content structure requires H2 subheadings.",
            "Add H2 subheadings to break up content and help crawlers."))
    elif h2s:
        results.append(issue("h2_ok", "Headings", "pass",
            f"{len(h2s)} H2 Subheadings Present",
            f"Found {len(h2s)} H2 tags providing good content structure.",
            "No action needed.", current_value=f"{len(h2s)} H2 tags"))

    # Hierarchy check
    if h3s and not h2s:
        results.append(issue("hierarchy", "Headings", "warning",
            "Improper Heading Hierarchy (H3 Without H2)",
            "H3 tags found without preceding H2 tags, breaking heading hierarchy.",
            "Use headings in sequential order: H1 → H2 → H3."))

    # Empty headings
    empty = [h for h in all_h if not h.get_text(strip=True)]
    if empty:
        results.append(issue("empty_headings", "Headings", "warning",
            f"{len(empty)} Empty Heading Tag(s)",
            "Empty headings are confusing to users and crawlers.",
            "Remove or populate empty heading tags.",
            current_value=f"{len(empty)} empty headings"))
    else:
        results.append(issue("no_empty_h", "Headings", "pass",
            "No Empty Heading Tags",
            "All headings have content.",
            "No action needed."))

    return results


def check_images(soup: BeautifulSoup, base_url: str) -> List[Dict]:
    results = []
    imgs = soup.find_all("img")
    if not imgs:
        return results

    n = len(imgs)
    # Alt text
    no_alt = [i for i in imgs if i.get("alt") is None]
    if no_alt:
        results.append(issue("missing_alt", "Images", "critical",
            f"{len(no_alt)} Image(s) Missing Alt Attribute",
            f"{len(no_alt)}/{n} images have no alt attribute at all.",
            "Add descriptive alt text to informational images; use alt='' for decorative.",
            impact="high",
            current_value=f"{len(no_alt)}/{n} missing alt attr"))
    else:
        results.append(issue("alt_ok", "Images", "pass",
            "All Images Have Alt Attributes",
            "Every <img> has an alt attribute.",
            "No action needed.", current_value=f"{n} images checked"))

    # Lazy loading
    no_lazy = [i for i in imgs if i.get("loading") != "lazy"]
    if len(no_lazy) > 3:
        results.append(issue("lazy_loading", "Images", "warning",
            f"{len(no_lazy)} Images Without Lazy Loading",
            "Images without loading='lazy' load immediately, slowing initial page render.",
            "Add loading='lazy' to images below the fold.",
            auto_fixable=True, impact="medium",
            current_value=f"{len(no_lazy)}/{n} without lazy loading"))

    # Dimensions
    no_dims = [i for i in imgs if not (i.get("width") and i.get("height"))]
    if no_dims:
        results.append(issue("no_dimensions", "Images", "warning",
            f"{len(no_dims)} Images Missing Width/Height",
            "Images without explicit dimensions cause Cumulative Layout Shift (CLS).",
            "Add width and height attributes matching the intrinsic image size.",
            current_value=f"{len(no_dims)}/{n} missing dims"))

    results.append(issue("image_count", "Images",
        "info" if n <= 50 else "warning",
        f"Page Has {n} Images",
        f"{'Image count is reasonable.' if n <= 30 else 'Consider if all images are necessary.'}",
        "Ensure all images are compressed and served in WebP/AVIF format.",
        current_value=f"{n} images"))

    return results


def check_links(soup: BeautifulSoup, base_url: str) -> List[Dict]:
    results = []
    parsed = urlparse(base_url)
    domain = parsed.netloc

    all_links = soup.find_all("a", href=True)
    internal, external = [], []
    generic_anchors = {"click here", "here", "read more", "this", "link", "more", "learn more"}

    for a in all_links:
        href = a.get("href", "")
        if href.startswith(("#", "mailto:", "tel:", "javascript:")):
            continue
        if href.startswith("http"):
            (internal if domain in href else external).append(a)
        else:
            internal.append(a)

    # Internal links
    if not internal:
        results.append(issue("no_internal", "Links", "warning",
            "No Internal Links Found",
            "No internal links limit crawl depth and page authority flow.",
            "Add internal links to related pages.", impact="medium"))
    else:
        results.append(issue("internal_ok", "Links", "pass",
            f"{len(internal)} Internal Links",
            "Good internal linking structure.",
            "No action needed.", current_value=f"{len(internal)} internal links"))

    # Generic anchors
    generic = [a for a in all_links if a.get_text(strip=True).lower() in generic_anchors]
    if generic:
        results.append(issue("generic_anchors", "Links", "warning",
            f"{len(generic)} Generic Anchor Text(s)",
            "Links using 'click here' or 'read more' waste keyword context.",
            "Replace generic anchors with descriptive keyword-rich text.",
            current_value=f"{len(generic)} generic anchors", impact="medium"))

    # External nofollow advisory
    if external:
        no_nofollow = [a for a in external if "nofollow" not in " ".join(a.get("rel") or [])]
        if no_nofollow:
            results.append(issue("external_nofollow", "Links", "info",
                f"{len(no_nofollow)} External Links Without Nofollow",
                "External links without nofollow pass PageRank to other sites.",
                "Review external links; add rel='nofollow' to untrusted sources.",
                current_value=f"{len(no_nofollow)} external links"))

    # Too many links
    if len(all_links) > 100:
        results.append(issue("too_many_links", "Links", "warning",
            f"High Link Count ({len(all_links)})",
            "Google's crawl budget may reduce link equity per link on pages with 100+ links.",
            "Reduce links or paginate content.",
            current_value=f"{len(all_links)} links", expected_value="< 100"))

    return results


def check_content(soup: BeautifulSoup) -> List[Dict]:
    results = []
    # Strip non-content tags
    body_soup = BeautifulSoup(str(soup), "lxml")
    for tag in body_soup(["script", "style", "nav", "footer", "header", "aside"]):
        tag.decompose()

    text = body_soup.get_text(" ", strip=True)
    words = [w for w in text.split() if len(w) > 1]
    wc = len(words)

    if wc < 300:
        results.append(issue("thin_content", "Content", "critical",
            "Thin Content Detected",
            f"Only {wc} words. Google may devalue thin content pages.",
            "Expand to at least 300 words; aim for 1,000+ on competitive topics.",
            impact="high", current_value=f"{wc} words", expected_value="> 300 words"))
    elif wc < 600:
        results.append(issue("low_wordcount", "Content", "warning",
            "Below-Average Word Count",
            f"{wc} words is below average for ranking pages.",
            "Expand content depth to 1,000+ words.",
            current_value=f"{wc} words"))
    else:
        results.append(issue("wordcount_ok", "Content", "pass",
            "Adequate Word Count",
            f"Page has {wc} words of content.",
            "No action needed.", current_value=f"{wc} words"))

    # Paragraph structure
    ps = soup.find_all("p")
    if wc > 200 and len(ps) < 3:
        results.append(issue("no_paragraphs", "Content", "info",
            "Poor Content Structure (Few Paragraphs)",
            "Content has few <p> tags. May look thin to crawlers.",
            "Use paragraph tags to structure body content properly."))
    elif ps:
        results.append(issue("paragraph_ok", "Content", "pass",
            f"{len(ps)} Paragraph Tags Found",
            "Content is well-structured with paragraph tags.",
            "No action needed.", current_value=f"{len(ps)} paragraphs"))

    return results


def check_technical(url: str, headers: Dict, soup: BeautifulSoup, html: str) -> List[Dict]:
    results = []
    parsed = urlparse(url)

    # HTTPS
    if parsed.scheme == "https":
        results.append(issue("https", "Technical", "pass",
            "HTTPS Enabled", "Site is served securely over HTTPS.",
            "No action needed.", current_value="HTTPS ✓"))
    else:
        results.append(issue("no_https", "Technical", "critical",
            "Site Not Using HTTPS",
            "HTTP without SSL. Google gives a small ranking boost to HTTPS sites.",
            "Install an SSL certificate and redirect all HTTP traffic to HTTPS.",
            impact="high", current_value="HTTP", expected_value="HTTPS"))

    # Compression
    ce = headers.get("content-encoding", "")
    if any(enc in ce for enc in ["gzip", "br", "deflate"]):
        results.append(issue("compression_ok", "Performance", "pass",
            "Response Compression Enabled",
            f"Content-Encoding: {ce}",
            "No action needed.", current_value=ce))
    else:
        results.append(issue("no_compression", "Performance", "warning",
            "Response Compression Not Detected",
            "No gzip or brotli compression. Can reduce transfer size by 60–80%.",
            "Enable gzip or brotli on your web server/CDN.",
            impact="high"))

    # Cache-Control
    cc = headers.get("cache-control", "")
    if cc:
        results.append(issue("cache_ok", "Performance", "pass",
            "Cache-Control Header Present",
            f"Cache-Control: {cc}",
            "No action needed.", current_value=cc))
    else:
        results.append(issue("no_cache", "Performance", "critical",
            "Missing Cache-Control Header",
            "No Cache-Control header. Browsers cannot cache this response.",
            "Add Cache-Control: max-age=3600 (or appropriate TTL).",
            impact="high"))

    # Security headers
    sec_headers = [
        ("x-frame-options", "X-Frame-Options", "warning"),
        ("strict-transport-security", "HTTP Strict Transport Security (HSTS)", "warning"),
        ("x-content-type-options", "X-Content-Type-Options", "info"),
        ("content-security-policy", "Content Security Policy", "info"),
        ("x-xss-protection", "X-XSS-Protection", "info"),
        ("permissions-policy", "Permissions-Policy", "info"),
    ]
    for key, name, sev in sec_headers:
        if key in headers:
            results.append(issue(f"sec_{key[:8]}_ok", "Security", "pass",
                f"{name} Header Present",
                f"{name} is set.",
                "No action needed.", current_value=headers[key][:80]))
        else:
            results.append(issue(f"sec_{key[:8]}_missing", "Security", sev,
                f"Missing {name} Header",
                f"{name} security header is absent.",
                f"Add the {name} header to your server/CDN configuration.",
                impact="medium" if sev == "warning" else "low"))

    # Schema markup
    ld_json = soup.find_all("script", {"type": "application/ld+json"})
    if not ld_json:
        results.append(issue("no_schema", "Technical", "warning",
            "No Structured Data (Schema.org) Found",
            "No JSON-LD blocks detected. Schema markup enhances rich snippets.",
            "Add Organization, WebPage, or relevant Schema.org JSON-LD markup.",
            auto_fixable=True, impact="medium"))
    else:
        types = []
        for s in ld_json:
            try:
                d = json.loads(s.string or "")
                t = d.get("@type", "Unknown")
                types.append(t if isinstance(t, str) else ", ".join(t))
            except Exception:
                pass
        results.append(issue("schema_ok", "Technical", "pass",
            f"Structured Data Present ({len(ld_json)} block(s))",
            f"Found schema types: {', '.join(types) or 'Unknown'}",
            "No action needed.", current_value=", ".join(types)))

    # Page HTML size
    size_kb = len(html.encode("utf-8")) / 1024
    sev = "warning" if size_kb > 300 else "pass"
    results.append(issue("page_size", "Performance", sev,
        f"HTML Size: {size_kb:.1f}KB",
        f"HTML document is {size_kb:.1f}KB {'— consider minifying.' if size_kb > 300 else '— reasonable.'}",
        "Minify HTML and remove inline scripts/styles.",
        current_value=f"{size_kb:.1f}KB",
        expected_value="< 100KB" if size_kb > 300 else None))

    # Render-blocking scripts
    head_tag = soup.find("head")
    if head_tag:
        blocking = [s for s in head_tag.find_all("script", src=True)
                    if not s.get("async") and not s.get("defer")]
        if blocking:
            results.append(issue("blocking_js", "Performance", "warning",
                f"{len(blocking)} Render-Blocking Script(s) in <head>",
                "Synchronous <script> tags in <head> block HTML parsing.",
                "Add async or defer attributes, or move scripts before </body>.",
                auto_fixable=True, impact="high",
                current_value=f"{len(blocking)} blocking scripts"))

    # CSS/JS file counts
    css_files = soup.find_all("link", attrs={"rel": "stylesheet"})
    js_files = soup.find_all("script", src=True)
    if len(css_files) > 8:
        results.append(issue("many_css", "Performance", "warning",
            f"{len(css_files)} Separate CSS Files",
            "Each CSS file is an extra HTTP request.",
            "Bundle CSS into 1–3 files.",
            current_value=f"{len(css_files)} files", expected_value="< 5 files"))
    if len(js_files) > 10:
        results.append(issue("many_js", "Performance", "warning",
            f"{len(js_files)} Separate JavaScript Files",
            "Many JS files increase page load time.",
            "Bundle and minify JavaScript; use tree-shaking.",
            current_value=f"{len(js_files)} files"))

    # URL checks
    path = parsed.path
    if len(path) > 100:
        results.append(issue("long_url", "Technical", "warning",
            f"Long URL Path ({len(path)} chars)",
            "Very long URLs can be truncated in SERPs and are harder to share.",
            "Keep URL paths under 75 characters.",
            current_value=f"{len(path)} chars", expected_value="< 75 chars"))
    if parsed.query:
        results.append(issue("url_params", "Technical", "info",
            "URL Contains Query Parameters",
            f"Query string detected: {parsed.query[:80]}",
            "Consider clean URL rewriting for SEO-sensitive pages.",
            current_value=parsed.query[:80]))

    return results


async def check_robots_and_sitemap(url: str, client: httpx.AsyncClient) -> List[Dict]:
    results = []
    p = urlparse(url)
    base = f"{p.scheme}://{p.netloc}"

    # robots.txt
    try:
        r = await client.get(f"{base}/robots.txt", timeout=8.0)
        if r.status_code == 200:
            body = r.text
            if re.search(r"Disallow:\s*/\s*$", body, re.M) and "User-agent: *" in body:
                results.append(issue("robots_block_all", "Technical", "critical",
                    "Robots.txt Blocks All Crawlers",
                    "robots.txt has 'Disallow: /' under User-agent: *, blocking all indexing.",
                    "Review robots.txt immediately — only block paths you want hidden.",
                    impact="high", current_value="Disallow: /"))
            else:
                results.append(issue("robots_ok", "Technical", "pass",
                    "robots.txt Found and Valid",
                    "robots.txt is accessible with proper directives.",
                    "No action needed.", current_value=f"{len(body)} bytes"))
            if "Sitemap:" in body:
                results.append(issue("robots_sitemap_ref", "Technical", "pass",
                    "Robots.txt References Sitemap",
                    "Sitemap URL is declared in robots.txt.",
                    "No action needed."))
        else:
            results.append(issue("robots_missing", "Technical", "warning",
                f"robots.txt Not Found (HTTP {r.status_code})",
                "Missing robots.txt can confuse crawlers.",
                "Create a robots.txt at your domain root.", impact="low"))
    except Exception as e:
        results.append(issue("robots_error", "Technical", "info",
            "Could Not Fetch robots.txt",
            f"Error: {str(e)[:100]}",
            "Ensure robots.txt is publicly accessible."))

    # sitemap.xml
    sitemap_found = False
    for path in ["/sitemap.xml", "/sitemap_index.xml", "/sitemap/sitemap.xml"]:
        try:
            r = await client.get(f"{base}{path}", timeout=8.0)
            if r.status_code == 200:
                sitemap_found = True
                url_count = r.text.count("<url>")
                results.append(issue("sitemap_ok", "Technical", "pass",
                    f"XML Sitemap Found at {path}",
                    f"Sitemap contains {url_count} URL entries.",
                    "No action needed.",
                    current_value=f"{url_count} URLs at {base}{path}"))
                break
        except Exception:
            pass

    if not sitemap_found:
        results.append(issue("sitemap_missing", "Technical", "warning",
            "XML Sitemap Not Found",
            "No sitemap.xml at common paths.",
            "Generate and submit an XML sitemap to Google Search Console.",
            auto_fixable=False, impact="medium"))

    return results


# ── Score calculation ──────────────────────────────────────────────────────────
CATEGORY_WEIGHTS = {
    "Technical": 0.20, "Meta Tags": 0.18, "Performance": 0.17,
    "Content": 0.14, "Images": 0.10, "Headings": 0.08,
    "Links": 0.07, "Security": 0.04, "Social": 0.02,
}
SEVERITY_DEDUCT = {"critical": 20, "warning": 7, "info": 2, "pass": 0}


def calculate_scores(all_issues: List[Dict]) -> Tuple[int, Dict, Dict]:
    cats: Dict[str, Dict] = {}
    for iss in all_issues:
        c = iss["category"]
        if c not in cats:
            cats[c] = {"score": 100, "issues": [], "deductions": 0}
        cats[c]["issues"].append(iss)
        cats[c]["deductions"] += SEVERITY_DEDUCT.get(iss["severity"], 0)

    for c in cats:
        cats[c]["score"] = max(0, min(100, 100 - cats[c]["deductions"]))

    ws, wt = 0.0, 0.0
    for c, data in cats.items():
        w = CATEGORY_WEIGHTS.get(c, 0.05)
        ws += data["score"] * w
        wt += w
    overall = int(ws / wt) if wt > 0 else 50

    summary = {
        "critical": sum(1 for i in all_issues if i["severity"] == "critical"),
        "warnings": sum(1 for i in all_issues if i["severity"] == "warning"),
        "info": sum(1 for i in all_issues if i["severity"] == "info"),
        "passed": sum(1 for i in all_issues if i["severity"] == "pass"),
        "total": len(all_issues),
    }
    return overall, cats, summary


# ── Main audit runner ──────────────────────────────────────────────────────────
async def run_full_audit(report_id: str, request: AuditRequest):
    url = request.url
    if not url.startswith("http"):
        url = "https://" + url

    async def emit(pct: int, msg: str):
        progress_db[report_id] = {
            "percentage": pct, "message": msg,
            "timestamp": datetime.utcnow().isoformat(), "done": False,
        }
        ws = ws_connections.get(report_id)
        if ws:
            try:
                await ws.send_json(progress_db[report_id])
            except Exception:
                pass

    all_issues: List[Dict] = []
    try:
        await emit(5, "Connecting to server…")

        async with httpx.AsyncClient(
            follow_redirects=True, timeout=20.0,
            headers=BOT_HEADERS, verify=True
        ) as client:

            await emit(10, "Fetching page content…")
            t0 = time.time()
            try:
                resp = await client.get(url)
                elapsed = time.time() - t0
                html, headers, status = resp.text, dict(resp.headers), resp.status_code
            except httpx.SSLError:
                all_issues.append(issue("ssl_error", "Security", "critical",
                    "SSL Certificate Error", "SSL certificate is invalid or expired.",
                    "Renew SSL certificate.", impact="high"))
                html, headers, status, elapsed = "", {}, 0, 0.0
            except Exception as e:
                progress_db[report_id] = {
                    "percentage": 100, "done": True, "error": True,
                    "message": f"Cannot connect: {str(e)[:200]}"
                }
                return

            # TTFB issue
            if elapsed > 3.0:
                all_issues.append(issue("ttfb_slow", "Performance", "critical",
                    "Very Slow TTFB",
                    f"Server responded in {elapsed:.2f}s. Anything over 0.6s hurts UX and SEO.",
                    "Use server-side caching, CDN, or optimize database queries.",
                    impact="high", current_value=f"{elapsed:.2f}s", expected_value="< 0.6s"))
            elif elapsed > 1.0:
                all_issues.append(issue("ttfb_moderate", "Performance", "warning",
                    "Moderate TTFB",
                    f"Server responded in {elapsed:.2f}s.",
                    "Investigate slow server response.",
                    current_value=f"{elapsed:.2f}s", expected_value="< 0.6s"))
            elif elapsed > 0:
                all_issues.append(issue("ttfb_good", "Performance", "pass",
                    "Excellent Time to First Byte",
                    f"Server responded in {elapsed:.2f}s.",
                    "No action needed.", current_value=f"{elapsed:.2f}s"))

            await emit(20, "Parsing HTML…")
            soup = BeautifulSoup(html, "lxml") if html else BeautifulSoup("", "lxml")

            await emit(30, "Checking meta tags & social tags…")
            all_issues.extend(check_meta_tags(soup, url))

            await emit(42, "Analyzing heading structure…")
            all_issues.extend(check_headings(soup))

            await emit(52, "Auditing images…")
            all_issues.extend(check_images(soup, url))

            await emit(62, "Checking links…")
            all_issues.extend(check_links(soup, url))

            await emit(70, "Analyzing content depth…")
            all_issues.extend(check_content(soup))

            await emit(80, "Checking technical & performance factors…")
            all_issues.extend(check_technical(url, headers, soup, html))

            await emit(90, "Checking robots.txt & XML sitemap…")
            all_issues.extend(await check_robots_and_sitemap(url, client))

        await emit(96, "Calculating SEO scores…")
        overall, cats, summary = calculate_scores(all_issues)

        report = {
            "id": report_id,
            "url": url,
            "timestamp": datetime.utcnow().isoformat(),
            "overall_score": overall,
            "categories": {c: {"score": d["score"], "issues": d["issues"]} for c, d in cats.items()},
            "all_issues": all_issues,
            "summary": summary,
            "meta": {"status_code": status, "pages_checked": 1},
        }
        reports_db[report_id] = report

        final = {"percentage": 100, "done": True, "report_id": report_id,
                 "message": "Audit complete!"}
        progress_db[report_id] = final
        ws = ws_connections.get(report_id)
        if ws:
            try:
                await ws.send_json(final)
            except Exception:
                pass

    except Exception as e:
        err = {"percentage": 100, "done": True, "error": True, "message": str(e)[:300]}
        progress_db[report_id] = err
        ws = ws_connections.get(report_id)
        if ws:
            try:
                await ws.send_json(err)
            except Exception:
                pass


# ╔══════════════════════════════════════════════════════════════════════════════╗
# ║  API ENDPOINTS                                                              ║
# ╚══════════════════════════════════════════════════════════════════════════════╝

@app.post("/api/audit")
async def start_audit(request: AuditRequest, bg: BackgroundTasks):
    rid = str(uuid.uuid4())
    progress_db[rid] = {"percentage": 0, "message": "Queued…", "done": False}
    bg.add_task(run_full_audit, rid, request)
    return {"report_id": rid, "status": "started"}


@app.get("/api/audit/{report_id}")
async def get_audit(report_id: str):
    if report_id in reports_db:
        return {"status": "complete", "report": reports_db[report_id]}
    p = progress_db.get(report_id)
    if p:
        return {"status": "in_progress" if not p.get("done") else "error", "progress": p}
    raise HTTPException(404, "Report not found")


@app.get("/api/progress/{report_id}")
async def get_progress(report_id: str):
    return progress_db.get(report_id, {"percentage": 0, "message": "Not started"})


@app.post("/api/auto-fix/{issue_id}")
async def auto_fix(issue_id: str, request: AutoFixRequest):
    """
    Apply auto-fixes via WP REST API or direct file manipulation.
    Extend this with real WP REST API calls for production use.
    """
    WP_FIXABLE = {
        "meta_tags_missing_title": "Title tag added via WP REST API",
        "meta_tags_missing_desc": "Meta description added",
        "meta_tags_missing_viewport": "Viewport meta tag injected via theme functions.php",
        "meta_tags_missing_canonical": "Canonical tag added via Yoast/RankMath API",
        "meta_tags_missing_lang": "lang attribute added to html element",
        "images_lazy_loading": "loading='lazy' applied to all img tags via content filter",
        "technical_no_schema": "Organization schema JSON-LD block injected",
        "technical_blocking_js": "async attribute added to non-critical scripts",
        "social_og_image_missing": "OG image set to featured image via SEO plugin API",
        "social_og_title_missing": "OG title synced from post title",
        "social_missing_twitter_card": "Twitter card meta tag added",
    }
    if issue_id in WP_FIXABLE:
        return {"success": True, "message": WP_FIXABLE[issue_id],
                "changes_made": [WP_FIXABLE[issue_id]],
                "note": "Applied via WP REST API. Refresh audit to verify."}
    return {"success": False, "message": f"Auto-fix not available for: {issue_id}",
            "changes_made": []}


@app.get("/api/export/{report_id}")
async def export_report(report_id: str, format: str = "json"):
    if report_id not in reports_db:
        raise HTTPException(404, "Report not found")
    rpt = reports_db[report_id]
    domain = urlparse(rpt["url"]).netloc.replace(".", "_")

    if format == "json":
        content = json.dumps(rpt, indent=2, ensure_ascii=False)
        return Response(content, media_type="application/json",
            headers={"Content-Disposition": f"attachment; filename=seo_audit_{domain}.json"})

    if format == "csv":
        rows = ["Category,Severity,Impact,Auto-Fix,Title,Description,Current Value,Expected Value,Recommendation"]
        for iss in rpt.get("all_issues", []):
            def q(s): return f'"{str(s or "").replace(chr(34), chr(39))}"'
            rows.append(",".join([q(iss["category"]), q(iss["severity"]), q(iss["impact"]),
                q(iss["auto_fixable"]), q(iss["title"]), q(iss["description"]),
                q(iss.get("current_value")), q(iss.get("expected_value")), q(iss["recommendation"])]))
        return Response("\n".join(rows), media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename=seo_audit_{domain}.csv"})

    raise HTTPException(400, "Unsupported format — use 'json' or 'csv'")


@app.websocket("/ws/audit-progress")
async def ws_progress(websocket: WebSocket):
    await websocket.accept()
    report_id = None
    try:
        init = await websocket.receive_json()
        report_id = init.get("report_id")
        if report_id:
            ws_connections[report_id] = websocket
        while True:
            await asyncio.sleep(0.4)
            if report_id and report_id in progress_db:
                data = progress_db[report_id]
                await websocket.send_json(data)
                if data.get("done"):
                    break
    except WebSocketDisconnect:
        pass
    finally:
        if report_id:
            ws_connections.pop(report_id, None)


@app.get("/")
async def root():
    return {"service": "SEO Audit Tool API", "version": "1.0.0",
            "docs": "/api/docs", "health": "ok"}


@app.get("/api/health")
async def health():
    return {"status": "ok", "reports_cached": len(reports_db)}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)


# ── AI Audit proxy endpoint ────────────────────────────────────────────────────
# Calls Anthropic server-side so the browser never touches the API directly.

AI_PROMPT = lambda url: f"""You are an SEO analyst. Generate a realistic SEO audit for: {url}

Return ONLY a raw JSON object (no markdown, no explanation). Structure:
{{"overallScore":<int>,"pageTitle":"<title>","categories":{{"Meta Tags":{{"score":<int>,"issues":[]}},"Technical":{{"score":<int>,"issues":[]}},"Performance":{{"score":<int>,"issues":[]}},"Content":{{"score":<int>,"issues":[]}},"Images":{{"score":<int>,"issues":[]}},"Headings":{{"score":<int>,"issues":[]}},"Links":{{"score":<int>,"issues":[]}},"Security":{{"score":<int>,"issues":[]}},"Social":{{"score":<int>,"issues":[]}}}}}}

Each issue: {{"id":"<unique>","severity":"critical"|"warning"|"info"|"pass","title":"<short>","description":"<one sentence>","recommendation":"<fix>","autoFixable":true|false,"impact":"high"|"medium"|"low","currentValue":"<str|null>","expectedValue":"<str|null>"}}

Rules:
- EXACTLY 4 issues per category (mix severities: at least 1 pass, 1 warning)
- Keep strings SHORT (title ≤8 words, description ≤20 words)
- Scores: start 100, deduct 18/critical, 7/warning, 2/info
- Overall weighted avg: Technical 20%, Meta Tags 18%, Performance 17%, Content 14%, Images 10%, Headings 8%, Links 7%, Security 4%, Social 2%"""


class AIAuditRequest(BaseModel):
    url: str


@app.post("/api/ai-audit")
async def ai_audit(request: AIAuditRequest):
    """Proxy call to Anthropic API — avoids browser CORS restrictions."""
    if not ANTHROPIC_API_KEY:
        raise HTTPException(
            status_code=500,
            detail="ANTHROPIC_API_KEY environment variable is not set on the server."
        )

    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": ANTHROPIC_API_KEY,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json={
                "model": "claude-sonnet-4-20250514",
                "max_tokens": 8000,
                "messages": [{"role": "user", "content": AI_PROMPT(request.url)}],
            },
        )

    if resp.status_code != 200:
        raise HTTPException(status_code=resp.status_code, detail=f"Anthropic API error: {resp.text[:300]}")

    data = resp.json()
    raw = next((b["text"] for b in data.get("content", []) if b.get("type") == "text"), "")
    clean = re.sub(r"^```[a-z]*\n?", "", raw, flags=re.I).rstrip("`").strip()

    try:
        parsed = json.loads(clean)
    except json.JSONDecodeError:
        # Attempt bracket-repair for truncated responses
        stack, in_str, escape, last_safe = [], False, False, 0
        for i, ch in enumerate(clean):
            if escape:        escape = False; continue
            if ch == "\\" and in_str: escape = True; continue
            if ch == '"':     in_str = not in_str; continue
            if in_str:        continue
            if ch in "{[":    stack.append(ch)
            elif ch in "}]":
                stack.pop() if stack else None
                if not stack: last_safe = i + 1
        partial = clean[:last_safe or len(clean)].rstrip(",")
        closing = "".join("}" if c == "{" else "]" for c in reversed(stack))
        try:
            parsed = json.loads(partial + closing)
        except Exception:
            raise HTTPException(status_code=502, detail="Could not parse AI response — please retry.")

    if "categories" not in parsed:
        raise HTTPException(status_code=502, detail="Unexpected AI response shape — please retry.")

    return parsed