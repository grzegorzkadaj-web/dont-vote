import logging
import os
from datetime import datetime, timezone
from typing import Any

from langchain_core.documents import Document
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

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
        self._answer_rewriter = None
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
                self._answer_rewriter = (
                    ChatPromptTemplate.from_template(
                        """Przepisz poniższą odpowiedź po polsku.
Zachowaj fakty i sens, nie dodawaj nowych informacji.
Zwróć wyłącznie treść odpowiedzi.

Odpowiedź:
{answer}"""
                    )
                    | ChatOpenAI(model=settings.chat_model, temperature=0)
                    | StrOutputParser()
                )
            except Exception as exc:
                logger.warning("Failed to initialize TavilySearch: %s", exc)

    def _rewrite_answer_to_polish(self, answer: Any) -> str | None:
        if not isinstance(answer, str):
            return None
        answer_text = answer.strip()
        if not answer_text:
            return None
        if self._answer_rewriter is None:
            return answer_text

        try:
            rewritten = self._answer_rewriter.invoke({"answer": answer_text})
            if isinstance(rewritten, str) and rewritten.strip():
                return rewritten.strip()
        except Exception as exc:
            logger.warning("Błąd przepisywania odpowiedzi Tavily po polsku: %s", exc)
        return answer_text

    def search_deputy_public_info(
        self, deputy_name: str, party_name: str | None = None
    ) -> dict[str, Any]:
        """Wyszukuje informacje publiczne o pośle za pomocą Tavily."""
        query = (
            f"{deputy_name} poseł {party_name or ''} Sejm działalność polityczna. Odpowiedz po polsku."
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

            answer = self._rewrite_answer_to_polish(res.get("answer"))
            raw_results = res.get("results") or []
            sources = []
            for item in raw_results:
                if isinstance(item, dict):
                    sources.append(
                        {
                            "title": item.get("title") or "Brak tytułu",
                            "url": item.get("url") or "",
                            "snippet": item.get("content") or "",
                            "score": item.get("score"),
                        }
                    )

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

    @staticmethod
    def _parse_published_at(raw_result: dict[str, Any]) -> str | None:
        date_candidates = (
            raw_result.get("published_date"),
            raw_result.get("published"),
            raw_result.get("date"),
        )
        for candidate in date_candidates:
            if not isinstance(candidate, str):
                continue
            value = candidate.strip()
            if not value:
                continue
            normalized = value.replace("Z", "+00:00")
            try:
                parsed = datetime.fromisoformat(normalized)
                if parsed.tzinfo is None:
                    parsed = parsed.replace(tzinfo=timezone.utc)
                return parsed.astimezone(timezone.utc).isoformat()
            except ValueError:
                if len(value) >= 10:
                    return value
        return None

    @staticmethod
    def _sort_key_by_newest(item: dict[str, Any]) -> tuple[int, float, float]:
        published_at = item.get("published_at")
        if isinstance(published_at, str) and published_at:
            try:
                timestamp = datetime.fromisoformat(
                    published_at.replace("Z", "+00:00")
                ).timestamp()
                return (1, timestamp, float(item.get("score") or 0.0))
            except ValueError:
                pass
        return (0, 0.0, float(item.get("score") or 0.0))

    def search_deputy_opinion_findings(
        self,
        deputy_name: str,
        deputy_id: int,
        deputy_club: str,
        question: str,
        limit: int,
    ) -> list[dict[str, Any]]:
        if self._search_tool is None:
            return []

        query = (
            f"{deputy_name} {question}. Znajdź wypowiedzi polityka, cytaty i artykuły."
        ).strip()
        try:
            response = self._search_tool.invoke(
                query, topic="news", search_depth="advanced"
            )
            if not isinstance(response, dict):
                return []
            raw_results = response.get("results") or []
            findings: list[dict[str, Any]] = []
            for item in raw_results:
                if not isinstance(item, dict):
                    continue
                findings.append(
                    {
                        "deputy_id": deputy_id,
                        "deputy_name": deputy_name,
                        "deputy_club": deputy_club,
                        "title": item.get("title") or "Brak tytułu",
                        "url": item.get("url") or "",
                        "snippet": item.get("content") or "",
                        "published_at": self._parse_published_at(item),
                        "score": item.get("score"),
                    }
                )
            findings.sort(key=self._sort_key_by_newest, reverse=True)
            return findings[:limit]
        except Exception as exc:
            logger.warning(
                "Błąd wyszukiwania opinii Tavily dla '%s' i pytania '%s': %s",
                deputy_name,
                question,
                exc,
            )
            return []
