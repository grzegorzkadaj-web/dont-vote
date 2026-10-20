import logging
import os
from typing import Any

from langchain_core.documents import Document

logger = logging.getLogger(__name__)

try:
    from langchain_tavily import TavilyCrawl, TavilyExtract, TavilyMap, TavilySearch
except ImportError:  # pragma: no cover
    TavilyCrawl = None
    TavilyExtract = None
    TavilyMap = None
    TavilySearch = None


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
    def _extract_text_values(payload: Any) -> list[str]:
        texts: list[str] = []
        text_keys = (
            "raw_content",
            "content",
            "text",
            "markdown",
            "extract",
            "excerpt",
            "summary",
        )

        if isinstance(payload, dict):
            for key in text_keys:
                value = payload.get(key)
                if isinstance(value, str):
                    cleaned = value.strip()
                    if cleaned:
                        texts.append(cleaned)
            for value in payload.values():
                texts.extend(TavilyEnricher._extract_text_values(value))
        elif isinstance(payload, list):
            for item in payload:
                texts.extend(TavilyEnricher._extract_text_values(item))

        return texts

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
            logger.warning("TavilyMap failed for '%s': %s", seed_url, exc)

        try:
            crawled = self.crawler.invoke({"url": seed_url})
            discovered_urls.update(self._extract_urls(crawled))
        except Exception as exc:
            logger.warning("TavilyCrawl failed for '%s': %s", seed_url, exc)

        return discovered_urls

    def extract_documents_from_urls(self, urls: list[str]) -> list[Document]:
        documents: list[Document] = []
        for url in urls:
            try:
                extracted = self.extractor.invoke({"urls": [url]})
            except Exception as exc:
                logger.warning("TavilyExtract failed for '%s': %s", url, exc)
                continue

            text_fragments = self._extract_text_values(extracted)
            page_content = "\n\n".join(text_fragments).strip()
            if not page_content:
                continue

            documents.append(
                Document(
                    page_content=page_content,
                    metadata={"source": url, "url": url},
                )
            )
        return documents


class TavilyDeputyService:
    def __init__(self, max_results: int = 5) -> None:
        self.max_results = max_results
        self._search_tool = None
        if TavilySearch is not None:
            try:
                from src.backend.config import settings

                api_key = settings.tavily_api_key or os.getenv("TAVILY_API_KEY")
                if api_key:
                    self._search_tool = TavilySearch(
                        max_results=self.max_results,
                        include_answer=True,
                        tavily_api_key=api_key,
                    )
                else:
                    self._search_tool = TavilySearch(
                        max_results=self.max_results, include_answer=True
                    )
            except Exception as exc:
                logger.warning("Failed to initialize TavilySearch: %s", exc)

    def search_deputy_public_info(
        self, deputy_name: str, party_name: str | None = None
    ) -> dict[str, Any]:
        """Wyszukuje informacje publiczne o pośle za pomocą Tavily."""
        query = (
            f"{deputy_name} poseł {party_name or ''} Sejm działalność polityczna"
        ).strip()

        if self._search_tool is None:
            return {
                "query": query,
                "answer": "Usługa Tavily nie jest obecnie skonfigurowana lub brak klucza API.",
                "sources": [],
            }

        try:
            res = self._search_tool.invoke(query)
            if not isinstance(res, dict):
                return {"query": query, "answer": None, "sources": []}

            answer = res.get("answer")
            raw_results = res.get("results") or []
            sources = []
            for item in raw_results:
                if isinstance(item, dict):
                    sources.append({
                        "title": item.get("title") or "Brak tytułu",
                        "url": item.get("url") or "",
                        "snippet": item.get("content") or "",
                        "score": item.get("score"),
                    })

            return {
                "query": query,
                "answer": answer,
                "sources": sources,
            }
        except Exception as exc:
            logger.warning("Błąd wyszukiwania Tavily dla '%s': %s", deputy_name, exc)
            return {
                "query": query,
                "answer": f"Wystąpił błąd podczas pobierania informacji z Tavily: {exc}",
                "sources": [],
            }

