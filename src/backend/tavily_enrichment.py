from typing import Any

from logger import log_info, log_warning

try:
    from langchain_tavily import TavilyCrawl, TavilyExtract, TavilyMap
except ImportError:  # pragma: no cover
    TavilyCrawl = None
    TavilyExtract = None
    TavilyMap = None


class TavilyEnricher:
    def __init__(self) -> None:
        if TavilyCrawl is None or TavilyMap is None or TavilyExtract is None:
            raise RuntimeError(
                "langchain_tavily is not installed. Add dependency 'langchain-tavily'."
            )
        self.mapper = TavilyMap(max_depth=1, max_breadth=10, max_pages=25)
        self.crawler = TavilyCrawl(max_depth=1, max_breadth=10, max_pages=25)
        self.extractor = TavilyExtract(extract_depth="basic")

    @staticmethod
    def _extract_urls(payload: Any) -> set[str]:
        urls: set[str] = set()
        if isinstance(payload, dict):
            for value in payload.values():
                urls.update(TavilyEnricher._extract_urls(value))
        elif isinstance(payload, list):
            for item in payload:
                urls.update(TavilyEnricher._extract_urls(item))
        elif isinstance(payload, str) and payload.startswith(("http://", "https://")):
            urls.add(payload)
        return urls

    def discover_related_urls(self, seed_url: str) -> set[str]:
        log_info(f"Running TavilyMap and TavilyCrawl for {seed_url}")
        discovered_urls: set[str] = {seed_url}

        try:
            extracted = self.extractor.invoke({"urls": [seed_url]})
            discovered_urls.update(self._extract_urls(extracted))
        except Exception as exc:
            log_warning(f"TavilyExtract failed for '{seed_url}': {exc}")

        try:
            mapped = self.mapper.invoke({"url": seed_url})
            discovered_urls.update(self._extract_urls(mapped))
        except Exception as exc:
            log_warning(f"TavilyMap failed for '{seed_url}': {exc}")

        try:
            crawled = self.crawler.invoke({"url": seed_url})
            discovered_urls.update(self._extract_urls(crawled))
        except Exception as exc:
            log_warning(f"TavilyCrawl failed for '{seed_url}': {exc}")

        return discovered_urls
