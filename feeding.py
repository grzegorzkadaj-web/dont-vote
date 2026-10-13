import argparse
import os
import tempfile
import urllib.request
from dataclasses import dataclass
from typing import Any, Iterable

from dotenv import load_dotenv
from langchain_core.documents import Document
from langchain_openai import OpenAIEmbeddings
from langchain_pinecone import PineconeVectorStore
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_unstructured import UnstructuredLoader

from logger import log_error, log_header, log_info, log_success, log_warning
from src.backend.parties import PARTY_CONFIGS, PartyKey
from src.backend.tavily_enrichment import TavilyEnricher

load_dotenv()


@dataclass(frozen=True)
class IngestionConfig:
    chunk_size: int = 1_000
    chunk_overlap: int = 200
    pinecone_batch_size: int = 8
    pinecone_embedding_chunk_size: int = 8


def _sanitize_metadata(raw_metadata: dict[str, Any]) -> dict[str, Any]:
    allowed_scalar_keys = {
        "source",
        "url",
        "filename",
        "filetype",
        "page_number",
        "languages",
    }
    cleaned: dict[str, Any] = {}
    for key in allowed_scalar_keys:
        value = raw_metadata.get(key)
        if value is None:
            continue
        if isinstance(value, (str, int, float, bool)):
            value_as_str = str(value)
            if len(value_as_str) <= 1_000:
                cleaned[key] = value
        elif isinstance(value, list):
            short_items = [
                item for item in value if isinstance(item, str) and len(item) <= 256
            ][:10]
            if short_items:
                cleaned[key] = short_items
    return cleaned


def _download_to_temp_file(url: str) -> str:
    request = urllib.request.Request(
        url=url,
        headers={"User-Agent": "politics-rag-ingestion/1.0"},
    )
    with urllib.request.urlopen(request, timeout=60) as response:
        content = response.read()

    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_file:
        temp_file.write(content)
        return temp_file.name


def _load_source_documents(source: str) -> list[Document]:
    if source.startswith(("http://", "https://")):
        temp_path = _download_to_temp_file(source)
        try:
            loader = UnstructuredLoader(
                file_path=[temp_path],
                chunking_strategy="basic",
                max_characters=1_000_000,
                languages=["pol"],
            )
            return loader.load()
        finally:
            try:
                os.remove(temp_path)
            except OSError:
                pass

    loader = UnstructuredLoader(
        file_path=[source],
        chunking_strategy="basic",
        max_characters=1_000_000,
        languages=["pol"],
    )
    return loader.load()


def build_documents_for_party(
    party: PartyKey,
    use_tavily_enrichment: bool,
) -> list[Document]:
    party_config = PARTY_CONFIGS[party]
    log_info(
        f"Loading programme for {party_config.display_name}: {party_config.programme_url}"
    )

    documents = _load_source_documents(party_config.programme_url)

    source_urls: set[str] = {party_config.programme_url}
    if use_tavily_enrichment:
        enricher = TavilyEnricher()
        mapped_urls = enricher.discover_related_urls(party_config.programme_url)
        source_urls.update(mapped_urls)

    base_metadata = {
        "party": party,
        "party_display_name": party_config.display_name,
        "programme_url": party_config.programme_url,
        "source_urls": sorted(source_urls),
    }

    for document in documents:
        cleaned_source_metadata = _sanitize_metadata(document.metadata)
        document.metadata = {**cleaned_source_metadata, **base_metadata}

    return documents


def split_documents(
    documents: Iterable[Document], config: IngestionConfig
) -> list[Document]:
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=config.chunk_size,
        chunk_overlap=config.chunk_overlap,
    )
    return splitter.split_documents(list(documents))


def ingest_party(party: PartyKey, use_tavily_enrichment: bool) -> None:
    party_config = PARTY_CONFIGS[party]
    ingestion_config = IngestionConfig()
    documents = build_documents_for_party(
        party, use_tavily_enrichment=use_tavily_enrichment
    )
    split_docs = split_documents(documents, ingestion_config)
    log_info(f"Prepared {len(split_docs)} chunks for {party_config.display_name}.")

    embeddings = OpenAIEmbeddings(
        model=os.environ.get("EMBEDDINGS_MODEL"),
        chunk_size=50,
        retry_min_seconds=10,
    )

    vector_store = PineconeVectorStore(
        index_name=party_config.index_name,
        embedding=embeddings,
    )
    vector_store.add_documents(
        documents=split_docs,
        batch_size=ingestion_config.pinecone_batch_size,
        embedding_chunk_size=ingestion_config.pinecone_embedding_chunk_size,
    )
    log_success(
        f"Upserted {len(split_docs)} chunks into Pinecone index '{party_config.index_name}'."
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Load Polish political parties programmes and upsert them to Pinecone."
    )
    parser.add_argument(
        "--party",
        choices=[*PARTY_CONFIGS.keys(), "all"],
        default="all",
        help="Choose a single party to ingest or ingest all of them.",
    )
    parser.add_argument(
        "--use-tavily-enrichment",
        action="store_true",
        help="Discover related URLs with TavilyMap/TavilyCrawl before writing metadata.",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    selected: list[PartyKey]
    if args.party == "all":
        selected = list(PARTY_CONFIGS.keys())
    else:
        selected = [args.party]

    log_header("Starting ingestion to Pinecone")
    if args.use_tavily_enrichment and not os.getenv("TAVILY_API_KEY"):
        log_warning(
            "TAVILY_API_KEY is missing. Tavily enrichment is disabled for this run."
        )
        args.use_tavily_enrichment = False

    try:
        for party_key in selected:
            ingest_party(party_key, use_tavily_enrichment=args.use_tavily_enrichment)
    except Exception as exc:
        log_error(f"Ingestion failed: {exc}")
        raise

    log_success("Ingestion completed.")
