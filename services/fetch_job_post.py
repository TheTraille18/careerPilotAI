"""Best-effort fetch of public job posting pages (e.g. public LinkedIn URLs).

Paste remains the reliable path — this is an optional helper when a URL is public.
Prefers the job description / "About the job" section, not the full page chrome.
"""

from __future__ import annotations

import json
import re
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from bs4 import BeautifulSoup, Tag

DEFAULT_TIMEOUT_SECONDS = 20
MAX_BODY_CHARS = 50_000

_BROWSER_UA = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
)

_LOGIN_MARKERS = (
    "authwall",
    "join linkedin",
    "sign in to linkedin",
    "sign in to continue",
    "create an account",
    "login to continue",
    "session_redirect",
)

# Stop "About the job" extraction at these common following sections.
_SECTION_STOP_RE = re.compile(
    r"^(about the company|about us|similar jobs|people also viewed|"
    r"show more|show less|see more|see less|benefits|base pay range|"
    r"seniority level|employment type|job function|industries|"
    r"applicants for this job|meet the hiring team)\b",
    re.I,
)

_LINKEDIN_DESC_SELECTORS = (
    "div.show-more-less-html__markup",
    "div.description__text",
    "div.jobs-description__content",
    "div.jobs-box__html-content",
    "section.description div.show-more-less-html__markup",
    "div#job-details",
    "article.jobs-description",
)


class JobPostFetchError(Exception):
    """Raised when a public job URL cannot be fetched or parsed usefully."""


def fetch_public_job_description(url: str) -> str:
    """Download a public job URL and return extracted plain-text description."""
    cleaned = (url or "").strip()
    if not cleaned:
        raise JobPostFetchError("Job URL is empty")
    if not cleaned.startswith(("http://", "https://")):
        raise JobPostFetchError("Job URL must start with http:// or https://")

    html = _download_html(cleaned)
    text = _extract_job_text(html, source_url=cleaned)
    if not text or len(text) < 40:
        raise JobPostFetchError(
            "Could not extract a usable job description (page may require login)"
        )
    return text


def _download_html(url: str) -> str:
    request = Request(
        url,
        headers={
            "User-Agent": _BROWSER_UA,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
        },
        method="GET",
    )
    try:
        with urlopen(request, timeout=DEFAULT_TIMEOUT_SECONDS) as response:
            raw = response.read()
            charset = response.headers.get_content_charset() or "utf-8"
            return raw.decode(charset, errors="replace")
    except HTTPError as exc:
        raise JobPostFetchError(f"HTTP {exc.code} fetching job URL") from exc
    except URLError as exc:
        raise JobPostFetchError(f"Failed to fetch job URL: {exc.reason}") from exc


def _extract_job_text(html: str, *, source_url: str) -> str:
    soup = BeautifulSoup(html, "lxml")
    for tag in soup(["script", "style", "noscript", "svg"]):
        # Keep JSON-LD scripts for structured description before removing others.
        if tag.name == "script" and tag.get("type") == "application/ld+json":
            continue
        tag.decompose()

    host = source_url.lower()
    candidates: list[str] = []

    json_ld = _description_from_json_ld(soup)
    if json_ld:
        candidates.append(json_ld)

    if "linkedin.com" in host:
        linkedin = _linkedin_about_the_job(soup)
        if linkedin:
            candidates.append(linkedin)
        for selector in _LINKEDIN_DESC_SELECTORS:
            node = soup.select_one(selector)
            if node:
                candidates.append(_node_text(node))
    else:
        # Generic job boards: prefer description-ish blocks, not whole page.
        for selector in (
            "div.job-description",
            "section.job-description",
            "div[class*='description']",
            "div[class*='job-details']",
            "article",
        ):
            node = soup.select_one(selector)
            if node:
                candidates.append(_node_text(node))

        heading_block = _text_after_heading(soup, ("about the job", "job description", "description"))
        if heading_block:
            candidates.append(heading_block)

    # Prefer description-sized chunks — longest under a soft cap, not whole-page dumps.
    usable = [_clean_description(c) for c in candidates if c and len(c.strip()) >= 40]
    usable = [c for c in usable if len(c) >= 40]
    if not usable:
        raise JobPostFetchError(
            "Could not find an About the job / description section"
        )

    under_cap = [c for c in usable if len(c) <= 12000]
    text = max(under_cap, key=len) if under_cap else min(usable, key=len)

    if any(marker in text.lower() for marker in _LOGIN_MARKERS) and len(text) < 500:
        raise JobPostFetchError(
            "Page looks like a LinkedIn login wall; paste the description instead"
        )

    if len(text) > MAX_BODY_CHARS:
        text = text[:MAX_BODY_CHARS].rstrip() + "\n..."
    return text


def _description_from_json_ld(soup: BeautifulSoup) -> str:
    for script in soup.find_all("script", attrs={"type": "application/ld+json"}):
        raw = script.string or script.get_text() or ""
        raw = raw.strip()
        if not raw:
            continue
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            continue
        for item in _iter_json_ld_items(data):
            if not isinstance(item, dict):
                continue
            type_name = item.get("@type")
            types = type_name if isinstance(type_name, list) else [type_name]
            if "JobPosting" not in types:
                continue
            desc = item.get("description")
            if isinstance(desc, str) and desc.strip():
                # description is often HTML
                return _node_text(BeautifulSoup(desc, "lxml"))
    return ""


def _iter_json_ld_items(data):
    if isinstance(data, list):
        for item in data:
            yield from _iter_json_ld_items(item)
        return
    if isinstance(data, dict):
        if "@graph" in data and isinstance(data["@graph"], list):
            for item in data["@graph"]:
                yield from _iter_json_ld_items(item)
        yield data


def _linkedin_about_the_job(soup: BeautifulSoup) -> str:
    """Find the About the job heading and take following description content."""
    heading_block = _text_after_heading(soup, ("about the job",))
    if heading_block:
        return heading_block

    # Public LinkedIn pages often nest markup under a description section.
    for section in soup.find_all(["section", "div"]):
        classes = " ".join(section.get("class") or []).lower()
        if "description" not in classes and "job-details" not in classes:
            continue
        markup = section.select_one("div.show-more-less-html__markup")
        if markup:
            return _node_text(markup)
        text = _node_text(section)
        if "about the job" in text.lower() and len(text) > 80:
            return _trim_from_about_heading(text)
    return ""


def _text_after_heading(soup: BeautifulSoup, headings: tuple[str, ...]) -> str:
    heading_names = {h.lower() for h in headings}
    for tag in soup.find_all(["h1", "h2", "h3", "h4", "strong", "span", "div"]):
        label = tag.get_text(" ", strip=True).lower().rstrip(":")
        if label not in heading_names:
            continue

        chunks: list[str] = []
        for sibling in tag.next_siblings:
            if not isinstance(sibling, Tag):
                continue
            sibling_text = sibling.get_text(" ", strip=True)
            if not sibling_text:
                continue
            if _SECTION_STOP_RE.match(sibling_text):
                break
            # Nested description markup is ideal
            markup = sibling.select_one("div.show-more-less-html__markup") if sibling.name else None
            if markup:
                chunks.append(_node_text(markup))
                break
            chunks.append(_node_text(sibling))
            if sum(len(c) for c in chunks) > 500:
                # Enough description gathered
                pass
        if chunks:
            return _normalize_whitespace("\n\n".join(chunks))

        parent = tag.parent
        if parent:
            markup = parent.select_one("div.show-more-less-html__markup")
            if markup:
                return _node_text(markup)
    return ""


def _trim_from_about_heading(text: str) -> str:
    lines = text.splitlines()
    start = 0
    for i, line in enumerate(lines):
        if line.strip().lower().rstrip(":") == "about the job":
            start = i + 1
            break
    kept: list[str] = []
    for line in lines[start:]:
        if _SECTION_STOP_RE.match(line.strip()):
            break
        kept.append(line)
    return _normalize_whitespace("\n".join(kept))


def _node_text(node: Tag | BeautifulSoup) -> str:
    return _normalize_whitespace(node.get_text("\n", strip=True))


def _clean_description(text: str) -> str:
    text = _normalize_whitespace(text)
    # Drop common UI crumbs
    text = re.sub(r"\bShow more\b", "", text, flags=re.I)
    text = re.sub(r"\bShow less\b", "", text, flags=re.I)
    text = _normalize_whitespace(text)
    if text.lower().startswith("about the job"):
        text = _trim_from_about_heading("About the job\n" + text[len("about the job") :])
    return text


def _normalize_whitespace(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+\n", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()
