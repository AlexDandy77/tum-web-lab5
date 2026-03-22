"""DuckDuckGo HTML search integration."""

from dataclasses import dataclass
from urllib.parse import quote_plus, urlparse, parse_qs, unquote


@dataclass
class SearchResult:
    title: str
    url: str
    snippet: str


def _extract_ddg_url(href: str) -> str:
    """Unwrap DuckDuckGo redirect URLs like /l/?uddg=https%3A%2F%2F..."""
    if href.startswith("/l/?") or "duckduckgo.com/l/?" in href:
        parsed = urlparse(href)
        params = parse_qs(parsed.query)
        uddg = params.get("uddg", [""])[0]
        if uddg:
            return unquote(uddg)
    return href


def search(query: str, client) -> list:
    """Search DuckDuckGo HTML and return up to 10 SearchResult objects."""
    url = f"https://html.duckduckgo.com/html/?q={quote_plus(query)}"
    response = client.request(url)

    try:
        from bs4 import BeautifulSoup
        return _parse_bs4(response.body)
    except ImportError:
        return _parse_stdlib(response.body)


def _parse_bs4(html: str) -> list:
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(html, "html.parser")
    results = []
    for div in soup.select(".result"):
        title_tag = div.select_one(".result__a")
        snippet_tag = div.select_one(".result__snippet")
        if not title_tag:
            continue
        href = title_tag.get("href", "")
        url = _extract_ddg_url(href)
        if not url or url.startswith("//duckduckgo"):
            continue
        results.append(SearchResult(
            title=title_tag.get_text(strip=True),
            url=url,
            snippet=snippet_tag.get_text(strip=True) if snippet_tag else "",
        ))
        if len(results) >= 10:
            break
    return results


def _parse_stdlib(html: str) -> list:
    """Fallback parser using stdlib html.parser."""
    from html.parser import HTMLParser

    class DDGParser(HTMLParser):
        def __init__(self):
            super().__init__()
            self.results = []
            self._in_result = False
            self._in_title = False
            self._in_snippet = False
            self._current = None
            self._depth = 0

        def handle_starttag(self, tag, attrs):
            attrs_dict = dict(attrs)
            classes = attrs_dict.get("class", "").split()
            if "result" in classes and tag == "div":
                self._in_result = True
                self._current = SearchResult("", "", "")
            if self._in_result and tag == "a" and "result__a" in classes:
                self._in_title = True
                href = attrs_dict.get("href", "")
                if self._current:
                    self._current.url = _extract_ddg_url(href)
            if self._in_result and "result__snippet" in classes:
                self._in_snippet = True

        def handle_endtag(self, tag):
            if self._in_title and tag == "a":
                self._in_title = False
            if self._in_snippet and tag in ("a", "span"):
                self._in_snippet = False
                if self._current and self._current.url:
                    self.results.append(self._current)
                    self._current = None
                    self._in_result = False

        def handle_data(self, data):
            if self._in_title and self._current:
                self._current.title += data
            elif self._in_snippet and self._current:
                self._current.snippet += data

    parser = DDGParser()
    parser.feed(html)
    return parser.results[:10]


def print_results(results: list) -> None:
    if not results:
        print("No results found.")
        return
    for i, r in enumerate(results, 1):
        print(f"{i}. {r.title}")
        print(f"   {r.url}")
        if r.snippet:
            print(f"   {r.snippet}")
        print()
