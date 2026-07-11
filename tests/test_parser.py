from __future__ import annotations

from keam_monitor.parser import ContentItem, ParsedPage, change_summary, compute_hash, normalize_html


def test_normalize_html_extracts_structured_notices_and_pdfs() -> None:
    html = """
    <html><body>
      <header>Header</header>
      <nav>Menu</nav>
      <main>
        <h2>First Phase Allotment Published</h2>
        <p>Candidate details are here.</p>
        <a href="/file.pdf">First Allotment.pdf</a>
        <a href="/notice.html">First Phase Allotment Published</a>
      </main>
      <script>var x=1;</script>
    </body></html>
    """
    parsed = normalize_html(html, base_url="https://cee.kerala.gov.in/keam2026/")
    assert parsed.documents == (
        ContentItem(
            title="First Allotment.pdf",
            url="https://cee.kerala.gov.in/file.pdf",
            type="pdf",
        ),
    )
    assert ContentItem(
        title="First Phase Allotment Published",
        url="https://cee.kerala.gov.in/notice.html",
        type="notice",
    ) in parsed.notices
    assert "Header" not in parsed.text


def test_structured_hash_ignores_formatting_and_visitor_counter_noise() -> None:
    first = normalize_html(
        """
        <main>
          <div id="visitor-counter">Visitors: 10</div>
          <a href="/prospectus.pdf"> Prospectus.pdf </a>
          <a href="/notice">Trial Allotment</a>
        </main>
        """,
        base_url="https://example.com/",
    )
    second = normalize_html(
        """
        <main>
          <div id="visitor-counter">Visitors: 11</div>
          <p><a href="/prospectus.pdf">
            Prospectus.pdf
          </a></p>
          <span><a href="/notice">Trial    Allotment</a></span>
        </main>
        """,
        base_url="https://example.com/",
    )
    assert compute_hash(first.canonical_json()) == compute_hash(second.canonical_json())


def test_change_summary_reports_meaningful_changes() -> None:
    previous = {
        "documents": [
            {"title": "Trial Allotment.pdf", "url": "https://example.com/trial.pdf", "type": "pdf"},
            {"title": "Prospectus.pdf", "url": "https://example.com/prospectus-old.pdf", "type": "pdf"},
        ],
        "notices": [
            {"title": "Trial Allotment", "url": "https://example.com/trial", "type": "notice"},
            {"title": "Old Notice Title", "url": "https://example.com/renamed", "type": "notice"},
            {"title": "Changed Hyperlink", "url": "https://example.com/old-link", "type": "notice"},
        ],
    }
    current = ParsedPage(
        documents=(
            ContentItem("First Allotment.pdf", "https://example.com/first.pdf", "pdf"),
            ContentItem("Prospectus.pdf", "https://example.com/prospectus-new.pdf", "pdf"),
        ),
        notices=(
            ContentItem("First Phase Allotment Published", "https://example.com/first", "notice"),
            ContentItem("New Notice Title", "https://example.com/renamed", "notice"),
            ContentItem("Changed Hyperlink", "https://example.com/new-link", "notice"),
        ),
    )
    summary = change_summary(previous, current)
    assert "New PDFs\n\u2022 First Allotment.pdf" in summary
    assert "New Notices\n\u2022 First Phase Allotment Published" in summary
    assert "Removed\n\u2022 Trial Allotment.pdf\n\u2022 Trial Allotment" in summary
    assert "Changed Notice Titles\n\u2022 Old Notice Title -> New Notice Title" in summary
    assert "\u2022 Changed Hyperlink updated" in summary
    assert "\u2022 Prospectus.pdf updated" in summary
