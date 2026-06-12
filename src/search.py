import html
import os
import re
import time
from dataclasses import asdict, dataclass
from typing import Any, Dict, List, Optional
from urllib.parse import parse_qs, quote_plus, unquote, urlparse
import requests
from bs4 import BeautifulSoup

@dataclass
class SearchResult:
    question: str
    query: str
    title: str
    url: str
    snippet: str
    content: str

    def to_dict(self) -> Dict[str, str]:
        return asdict(self)

class DuckDuckGoSearchTool:
    def __init__(
        self,
        *,
        timeout: Optional[int] = None,
        user_agent: Optional[str] = None,
        sleep_between_requests: float = 0.5,
    ) -> None:
        self.timeout = timeout or int(os.getenv("REQUEST_TIMEOUT_SECONDS", "20"))
        self.user_agent = user_agent or os.getenv(
            "USER_AGENT",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120 Safari/537.36",
        )
        self.sleep_between_requests = sleep_between_requests
        self.session = requests.Session()
        self.session.headers.update(
            {"User-Agent": self.user_agent, "Accept-Language": "en-US,en;q=0.9"}
        )

    def search(self, query: str, *, max_results: int = 5) -> List[Dict[str, str]]:
        for variant in self._query_variants(query):
            results = self._search_once(variant, max_results=max_results)
            if results:
                if variant != query:
                    print(f"Search fallback used: {variant}")
                return results

        print(f"Warning: no parsable search results for query: {query!r}")
        return []

    def search_and_extract(
        self, question: str, *, max_results: int = 3, max_chars_per_page: int = 2500
    ) -> List[SearchResult]:
        rows: List[SearchResult] = []
        for item in self.search(question, max_results=max_results):
            content = self.extract_page_text(item["url"], max_chars=max_chars_per_page)
            rows.append(
                SearchResult(
                    question=question,
                    query=question,
                    title=item["title"],
                    url=item["url"],
                    snippet=item["snippet"],
                    content=content,
                )
            )
            time.sleep(self.sleep_between_requests)
        return rows

    def extract_page_text(self, url: str, *, max_chars: int = 2500) -> str:
        try:
            response = self.session.get(url, timeout=self.timeout, allow_redirects=True)
            response.raise_for_status()
            content_type = response.headers.get("Content-Type", "").lower()
            if "text/html" not in content_type and "application/xhtml" not in content_type:
                return ""

            soup = BeautifulSoup(response.text, "lxml")
            for tag in soup(["script", "style", "noscript", "svg", "form", "header", "footer", "nav"]):
                tag.decompose()

            pieces: List[str] = []
            if soup.title and soup.title.string:
                pieces.append(soup.title.string)

            for tag in soup.find_all(["h1", "h2", "h3", "p", "li"]):
                text = self._clean_text(tag.get_text(" "))
                if len(text) >= 40:
                    pieces.append(text)
                if sum(len(piece) for piece in pieces) >= max_chars:
                    break

            return self._clean_text("\n".join(pieces))[:max_chars]
        except requests.RequestException as exc:
            return f"Could not fetch page: {exc}"

    def _search_once(self, query: str, *, max_results: int = 5) -> List[Dict[str, str]]:
        providers = [
            ("duckduckgo", f"https://duckduckgo.com/html/?q={quote_plus(query)}"),
            ("duckduckgo-html", f"https://html.duckduckgo.com/html/?q={quote_plus(query)}"),
            ("bing", f"https://www.bing.com/search?q={quote_plus(query)}"),
            ("yahoo", f"https://search.yahoo.com/search?p={quote_plus(query)}"),
        ]

        for provider, url in providers:
            try:
                response = self.session.get(url, timeout=self.timeout, allow_redirects=True)
                response.raise_for_status()
            except requests.RequestException:
                continue

            soup = BeautifulSoup(response.text, "lxml")
            if provider.startswith("duckduckgo") and self._looks_like_duckduckgo_challenge(response, soup):
                continue

            results = self._parse_search_results(provider, soup, max_results=max_results)
            if results:
                return results
            time.sleep(0.25)
        return []

    def _parse_search_results(self, provider: str, soup: BeautifulSoup, *, max_results: int) -> List[Dict[str, str]]:
        results: List[Dict[str, str]] = []

        if provider.startswith("duckduckgo"):
            for block in soup.select("div.result"):
                link = block.select_one("a.result__a")
                snippet_node = block.select_one("a.result__snippet") or block.select_one("div.result__snippet")
                self._append_search_result(results, link, snippet_node, max_results=max_results)
        elif provider == "bing":
            for block in soup.select("li.b_algo"):
                link = block.select_one("h2 a")
                snippet_node = block.select_one("p")
                self._append_search_result(results, link, snippet_node, max_results=max_results)
        elif provider == "yahoo":
            for block in soup.select("div.algo"):
                link = block.select_one("h3 a") or block.select_one("a")
                snippet_node = block.select_one("div.compText") or block.select_one("p")
                self._append_search_result(results, link, snippet_node, max_results=max_results)

        return results[:max_results]

    def _append_search_result(self, results: List[Dict[str, str]], link: Any, snippet_node: Any, *, max_results: int) -> None:
        if not link or len(results) >= max_results:
            return

        raw_href = link.get("href", "")
        resolved_url = self._resolve_search_url(raw_href)
        if not resolved_url.startswith(("http://", "https://")):
            return

        results.append({
            "title": self._clean_text(link.get_text(" ")),
            "url": resolved_url,
            "snippet": self._clean_text(snippet_node.get_text(" ") if snippet_node else ""),
        })

    def _resolve_search_url(self, raw_href: str) -> str:
        raw_href = html.unescape(raw_href)
        if raw_href.startswith("//"):
            raw_href = "https:" + raw_href
            
        parsed = urlparse(raw_href)
        qs = parse_qs(parsed.query)

        if "uddg" in qs and qs["uddg"]:
            return unquote(qs["uddg"][0])
        if "RU" in qs and qs["RU"]:
            return unquote(qs["RU"][0])
        if "u" in qs and qs["u"]:
            return unquote(qs["u"][0])

        match = re.search(r"/RU=([^/]+)", raw_href)
        if match:
            return unquote(match.group(1))

        return raw_href

    @staticmethod
    def _query_variants(query: str) -> List[str]:
        stopwords = {
            "a", "an", "and", "are", "as", "at", "be", "by", "do", "does", "for", "from",
            "has", "have", "how", "in", "into", "is", "it", "of", "on", "or", "regarding",
            "specifically", "the", "their", "this", "to", "used", "what", "when", "where",
            "which", "who", "why", "with", "within"
        }
        words = re.findall(r"[A-Za-z][A-Za-z0-9+/-]*", query)
        keywords = [word for word in words if len(word) > 2 and word.lower() not in stopwords]

        variants = [query]
        if keywords:
            variants.append(" ".join(keywords[:14]))
            variants.append(" ".join(keywords[:9]))
        return list(dict.fromkeys(variants))

    @staticmethod
    def _looks_like_duckduckgo_challenge(response: requests.Response, soup: BeautifulSoup) -> bool:
        if response.status_code == 202:
            return True
        page_text = soup.get_text(" ", strip=True).lower()
        challenge_markers = ["anomaly", "unfortunately", "bot", "challenge", "please prove"]
        return not soup.select("div.result") and any(marker in page_text for marker in challenge_markers)

    @staticmethod
    def _clean_text(text: str) -> str:
        text = html.unescape(text or "")
        text = re.sub(r"\s+", " ", text)
        return text.strip()
