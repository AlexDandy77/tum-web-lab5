"""HTML to human-readable text converter."""

from html.parser import HTMLParser as _StdlibHTMLParser


def extract_text(html: str) -> str:
    """Convert HTML to readable plain text, stripping all tags."""
    try:
        from bs4 import BeautifulSoup
        return _bs4_extract(html)
    except ImportError:
        return _stdlib_extract(html)


def _bs4_extract(html: str) -> str:
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "nav", "header", "footer", "noscript", "iframe"]):
        tag.decompose()
    text = soup.get_text(separator="\n")
    return _collapse_lines(text)


class _TextExtractor(_StdlibHTMLParser):
    SKIP_TAGS = {"script", "style", "head", "nav", "footer", "iframe", "noscript"}

    def __init__(self):
        super().__init__()
        self._skip_depth = 0
        self.parts = []

    def handle_starttag(self, tag, attrs):
        if tag in self.SKIP_TAGS:
            self._skip_depth += 1

    def handle_endtag(self, tag):
        if tag in self.SKIP_TAGS and self._skip_depth > 0:
            self._skip_depth -= 1

    def handle_data(self, data):
        if self._skip_depth == 0:
            self.parts.append(data)


def _stdlib_extract(html: str) -> str:
    extractor = _TextExtractor()
    extractor.feed(html)
    return _collapse_lines("".join(extractor.parts))


def _collapse_lines(text: str) -> str:
    lines = [line.strip() for line in text.splitlines()]
    lines = [l for l in lines if l]
    return "\n".join(lines)
