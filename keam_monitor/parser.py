from __future__ import annotations

import hashlib
import json
import posixpath
from dataclasses import asdict, dataclass, field
from typing import Any, Iterable, Mapping, Protocol, Sequence
from urllib.parse import unquote, urljoin, urlparse, urlunparse

from bs4 import BeautifulSoup, Comment
from bs4.element import Tag

from .utils import normalize_whitespace

NOISE_TAGS = {
    "script",
    "style",
    "noscript",
    "svg",
    "iframe",
    "meta",
    "link",
    "header",
    "footer",
    "nav",
    "form",
    "input",
    "button",
    "select",
    "option",
    "aside",
}
NOISE_TOKENS = (
    "ad",
    "advert",
    "banner",
    "breadcrumb",
    "counter",
    "copyright",
    "footer",
    "header",
    "menu",
    "navbar",
    "popup",
    "script",
    "sidebar",
    "social",
    "timestamp",
    "visitor",
)
RELEVANT_KEYWORDS = (
    "admission",
    "allot",
    "candidate",
    "download",
    "keam",
    "merit",
    "notice",
    "notification",
    "pdf",
    "prospectus",
    "rank",
    "result",
    "seat",
)
IMPORTANT_PHRASES = ("allotment", "allotment list", "phase", "trial")
BULLET = "\u2022"


@dataclass(frozen=True, order=True)
class ContentItem:
    """One meaningful monitored item from a notice section."""

    title: str
    url: str = ""
    type: str = "notice"

    def to_state(self) -> dict[str, str]:
        return asdict(self)


@dataclass(frozen=True)
class ParsedPage:
    """Structured page snapshot used for change detection."""

    documents: tuple[ContentItem, ...] = field(default_factory=tuple)
    notices: tuple[ContentItem, ...] = field(default_factory=tuple)
    title: str = ""

    @property
    def text(self) -> str:
        """Compatibility text for bot /latest, not raw page HTML text."""
        sections: list[str] = []
        if self.documents:
            sections.append(_bullet_section("PDFs", [item.title for item in self.documents]))
        if self.notices:
            sections.append(_bullet_section("Notices", [item.title for item in self.notices]))
        return "\n\n".join(sections)

    @property
    def links(self) -> tuple[str, ...]:
        return tuple(item.title for item in (*self.documents, *self.notices) if item.url)

    @property
    def pdfs(self) -> tuple[str, ...]:
        return tuple(item.title for item in self.documents)

    @property
    def titles(self) -> tuple[str, ...]:
        return tuple(item.title for item in self.notices)

    def state_payload(self) -> dict[str, list[dict[str, str]]]:
        return {
            "documents": [item.to_state() for item in self.documents],
            "notices": [item.to_state() for item in self.notices],
        }

    def canonical_json(self) -> str:
        return json.dumps(self.state_payload(), sort_keys=True, separators=(",", ":"))


class PageParser(Protocol):
    """Parser strategy interface for future multi-site support."""

    def parse(self, html: str, base_url: str = "") -> ParsedPage:
        """Return a structured page snapshot."""


class KeamNoticeParser:
    """Extract meaningful notices and PDFs from the KEAM notice area."""

    def parse(self, html: str, base_url: str = "") -> ParsedPage:
        soup = BeautifulSoup(html, "html.parser")
        remove_noise(soup)

        target = choose_content_container(soup)
        if target is None:
            target = soup.body or soup

        documents = tuple(_unique_items(extract_documents(target, base_url)))
        notices = tuple(_unique_items(extract_notices(target, base_url, documents)))
        return ParsedPage(documents=documents, notices=notices, title=safe_title(soup))


def normalize_html(html: str, base_url: str = "", parser: PageParser | None = None) -> ParsedPage:
    """Parse HTML and extract a structured meaningful snapshot."""
    strategy = parser or KeamNoticeParser()
    return strategy.parse(html, base_url=base_url)


def remove_noise(soup: BeautifulSoup) -> None:
    """Remove page chrome and volatile elements before extracting notices."""
    for tag in soup.find_all(list(NOISE_TAGS)):
        tag.decompose()

    for comment in soup.find_all(string=lambda value: isinstance(value, Comment)):
        comment.extract()

    for tag in list(soup.find_all(True)):
        if isinstance(tag, Tag) and has_noise_attributes(tag):
            tag.decompose()


def has_noise_attributes(tag: Tag) -> bool:
    """Return True when attributes identify counters, navigation, ads, or chrome."""
    if tag.name in NOISE_TAGS:
        return True

    attrs = tag.attrs or {}
    class_value = attrs.get("class", "")
    class_text = " ".join(class_value) if isinstance(class_value, list) else str(class_value)
    attr_text = " ".join(
        [
            str(attrs.get("id", "")),
            class_text,
            str(attrs.get("role", "")),
            str(attrs.get("aria-label", "")),
        ]
    ).lower()
    return any(token in attr_text for token in NOISE_TOKENS)


def choose_content_container(soup: BeautifulSoup) -> Tag | None:
    """Select the strongest likely notice container using link and keyword signals."""
    preferred = soup.find_all(["main", "article", "section", "div", "table", "ul", "ol"])
    scored: list[tuple[int, Tag]] = []

    for candidate in preferred:
        score = score_content_container(candidate)
        if score > 0:
            scored.append((score, candidate))

    if not scored:
        return None

    scored.sort(key=lambda item: item[0], reverse=True)
    return scored[0][1]


def score_content_container(candidate: Tag) -> int:
    """Score a candidate by notice-like text and useful links."""
    text = candidate.get_text(" ", strip=True).lower()
    if not text:
        return 0

    score = sum(2 for keyword in RELEVANT_KEYWORDS if keyword in text)
    score += sum(5 for phrase in IMPORTANT_PHRASES if phrase in text)
    score += min(len(candidate.find_all("a", href=True)), 8) * 2
    score += min(len(candidate.find_all(["li", "tr", "p"])), 8)
    if candidate.name in {"main", "article", "section", "table", "ul", "ol"}:
        score += 3
    if len(text.split()) > 8:
        score += 1
    return score


def extract_documents(container: Tag, base_url: str = "") -> Iterable[ContentItem]:
    """Extract PDF download links from the useful notice section."""
    for anchor in container.find_all("a", href=True):
        href = str(anchor.get("href", "")).strip()
        title = clean_title(anchor.get_text(" ", strip=True)) or title_from_url(href)
        if title and is_pdf_link(href, title):
            yield ContentItem(title=title, url=normalize_url(href, base_url), type="pdf")


def extract_notices(
    container: Tag,
    base_url: str = "",
    documents: Sequence[ContentItem] = (),
) -> Iterable[ContentItem]:
    """Extract notice titles and non-PDF hyperlinks from the useful notice section."""
    document_urls = {item.url for item in documents}

    for anchor in container.find_all("a", href=True):
        href = str(anchor.get("href", "")).strip()
        url = normalize_url(href, base_url)
        title = clean_title(anchor.get_text(" ", strip=True)) or title_from_url(href)
        if title and url not in document_urls:
            yield ContentItem(title=title, url=url, type="notice")

    linked_titles = {clean_title(anchor.get_text(" ", strip=True)) for anchor in container.find_all("a")}
    for element in container.find_all(["h1", "h2", "h3", "h4", "strong", "li", "p", "tr"]):
        if element.find("a"):
            continue
        title = clean_title(element.get_text(" ", strip=True))
        if is_notice_text(title) and title not in linked_titles:
            yield ContentItem(title=title, type="notice")


def is_notice_text(value: str) -> bool:
    """Return True when text is stable enough to track as a notice."""
    if not (4 <= len(value) <= 180):
        return False
    lowered = value.lower()
    if any(token in lowered for token in ("visitor", "visited", "last updated", "copyright")):
        return False
    return any(keyword in lowered for keyword in RELEVANT_KEYWORDS)


def clean_title(value: str) -> str:
    """Normalize notice titles while ignoring formatting and whitespace churn."""
    return normalize_whitespace(" ".join(value.split())).strip(" :-")


def normalize_url(href: str, base_url: str = "") -> str:
    """Normalize hrefs for stable structured comparison."""
    absolute = urljoin(base_url, href.strip())
    parsed = urlparse(absolute)
    path = posixpath.normpath(unquote(parsed.path)) if parsed.path else ""
    if parsed.path.endswith("/") and not path.endswith("/"):
        path = f"{path}/"
    return urlunparse(
        (
            parsed.scheme.lower(),
            parsed.netloc.lower(),
            path,
            "",
            parsed.query,
            "",
        )
    )


def is_pdf_link(href: str, label: str = "") -> bool:
    """Return True when an anchor points to or clearly labels a PDF."""
    parsed = urlparse(href)
    path = unquote(parsed.path).lower()
    return path.endswith(".pdf") or label.lower().endswith(".pdf")


def title_from_url(href: str) -> str:
    """Build a readable fallback title from a URL path."""
    path = unquote(urlparse(href).path)
    filename = path.rstrip("/").split("/")[-1]
    return filename.replace("_", " ").replace("-", " ").strip()


def safe_title(soup: BeautifulSoup) -> str:
    """Return a normalized HTML title, if one exists."""
    title = soup.title.string if soup.title and soup.title.string else ""
    return " ".join(title.split())


def compute_hash(content: str) -> str:
    """Compute a SHA-256 hash for canonical structured content."""
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def change_summary(previous_state: Mapping[str, Any], current_page: ParsedPage) -> str:
    """Create a concise Markdown summary of meaningful structured changes."""
    previous_documents = _items_from_state(previous_state, "documents", fallback_key="pdfs", item_type="pdf")
    previous_notices = _items_from_state(previous_state, "notices", fallback_key="titles", item_type="notice")
    current_documents = current_page.documents
    current_notices = current_page.notices

    new_pdfs, removed_pdfs, changed_downloads = _diff_items(previous_documents, current_documents)
    new_notices, removed_notices, changed_links = _diff_items(previous_notices, current_notices)
    changed_titles = _changed_titles(previous_notices, current_notices)

    sections: list[str] = []
    if new_pdfs:
        sections.append(_bullet_section("New PDFs", [item.title for item in new_pdfs]))
    if new_notices:
        sections.append(_bullet_section("New Notices", [item.title for item in new_notices]))
    if removed_pdfs or removed_notices:
        removed = [item.title for item in (*removed_pdfs, *removed_notices)]
        sections.append(_bullet_section("Removed", removed))
    if changed_titles:
        sections.append(_bullet_section("Changed Notice Titles", changed_titles))
    changed_link_titles = [f"{item.title} updated" for item in (*changed_links, *changed_downloads)]
    if changed_link_titles:
        sections.append(_bullet_section("Changed Links", changed_link_titles))

    if not sections:
        return "Structured content changed, but no notice or PDF changes were detected."
    return "\n\n".join(sections)


def _items_from_state(
    state: Mapping[str, Any],
    key: str,
    fallback_key: str,
    item_type: str,
) -> tuple[ContentItem, ...]:
    raw_items = state.get(key)
    if isinstance(raw_items, Sequence) and not isinstance(raw_items, str):
        items: list[ContentItem] = []
        for raw_item in raw_items:
            if isinstance(raw_item, Mapping):
                title = clean_title(str(raw_item.get("title", "")))
                if title:
                    items.append(
                        ContentItem(
                            title=title,
                            url=normalize_url(str(raw_item.get("url", ""))),
                            type=str(raw_item.get("type", item_type)),
                        )
                    )
        return tuple(_unique_items(items))

    return tuple(
        ContentItem(title=clean_title(str(value)), type=item_type)
        for value in _sequence_value(state, fallback_key)
        if clean_title(str(value))
    )


def _diff_items(
    previous: Sequence[ContentItem],
    current: Sequence[ContentItem],
) -> tuple[tuple[ContentItem, ...], tuple[ContentItem, ...], tuple[ContentItem, ...]]:
    previous_exact = set(previous)
    current_exact = set(current)
    previous_by_title = {item.title.casefold(): item for item in previous}
    current_by_title = {item.title.casefold(): item for item in current}
    previous_urls = {item.url for item in previous if item.url}
    current_urls = {item.url for item in current if item.url}

    changed_links = tuple(
        current_by_title[key]
        for key in sorted(previous_by_title.keys() & current_by_title.keys())
        if previous_by_title[key].url != current_by_title[key].url
        and previous_by_title[key].url
        and current_by_title[key].url
    )
    changed_titles_or_links = set(changed_links)

    new_items = tuple(
        sorted(
            item
            for item in current_exact - previous_exact
            if item.title.casefold() not in previous_by_title
            and (not item.url or item.url not in previous_urls)
            and item not in changed_titles_or_links
        )
    )
    removed_items = tuple(
        sorted(
            item
            for item in previous_exact - current_exact
            if item.title.casefold() not in current_by_title
            and (not item.url or item.url not in current_urls)
        )
    )
    return new_items, removed_items, changed_links


def _changed_titles(previous: Sequence[ContentItem], current: Sequence[ContentItem]) -> tuple[str, ...]:
    previous_by_url = {item.url: item for item in previous if item.url}
    current_by_url = {item.url: item for item in current if item.url}
    changes = [
        f"{previous_by_url[url].title} -> {current_by_url[url].title}"
        for url in sorted(previous_by_url.keys() & current_by_url.keys())
        if previous_by_url[url].title != current_by_url[url].title
    ]
    return tuple(changes)


def _unique_items(items: Iterable[ContentItem]) -> tuple[ContentItem, ...]:
    seen: set[ContentItem] = set()
    unique: list[ContentItem] = []
    for item in items:
        if not item.title or item in seen:
            continue
        seen.add(item)
        unique.append(item)
    return tuple(sorted(unique))


def _sequence_value(mapping: Mapping[str, Any], key: str) -> Sequence[Any]:
    """Return a sequence value from a mapping, or an empty tuple."""
    value = mapping.get(key, ())
    if isinstance(value, Sequence) and not isinstance(value, str):
        return value
    return ()


def _bullet_section(title: str, values: Sequence[str]) -> str:
    """Format a titled bullet-list section."""
    return f"{title}\n{BULLET} " + f"\n{BULLET} ".join(values)
