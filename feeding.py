import argparse
import base64
import io
import os
import tempfile
import urllib.request
from dataclasses import dataclass
from typing import Any, Iterable
from urllib.parse import urlparse

from dotenv import load_dotenv
from langchain_core.documents import Document
from langchain_core.messages import HumanMessage
from langchain_chroma import Chroma
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_unstructured import UnstructuredLoader
from pypdf import PdfReader
from pypdfium2 import PdfDocument

from logger import log_error, log_header, log_info, log_success, log_warning
from src.backend.parties import PARTY_CONFIGS, PartyKey
from src.backend.tavily_enrichment import TavilyEnricher

load_dotenv()


@dataclass(frozen=True)
class IngestionConfig:
    chunk_size: int = 1_000
    chunk_overlap: int = 200


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


def _is_http_url(value: str) -> bool:
    return value.startswith(("http://", "https://"))


def _is_pdf_source(value: str) -> bool:
    if _is_http_url(value):
        parsed_path = urlparse(value).path.lower()
        return parsed_path.endswith(".pdf")
    return value.lower().endswith(".pdf")


def _load_pdf_documents(source: str) -> list[Document]:
    if _is_http_url(source):
        temp_path = _download_to_temp_file(source)
    else:
        temp_path = source

    try:
        try:
            loader = UnstructuredLoader(
                file_path=[temp_path],
                chunking_strategy="basic",
                max_characters=1_000_000,
                languages=["pol"],
                strategy="fast",
            )
            documents = loader.load()
            if documents:
                return documents
            log_warning(
                "Unstructured PDF extraction returned no content. Falling back to pypdf."
            )
        except Exception as exc:
            log_warning(
                f"Unstructured PDF extraction failed ({exc}). Falling back to pypdf."
            )

        try:
            return _load_pdf_documents_with_pypdf(file_path=temp_path, source=source)
        except Exception as exc:
            log_warning(
                f"pypdf extraction failed ({exc}). Falling back to OpenAI OCR via pypdfium2."
            )

        return _load_pdf_documents_with_openai_ocr(file_path=temp_path, source=source)
    finally:
        if _is_http_url(source):
            try:
                os.remove(temp_path)
            except OSError:
                pass


def _load_pdf_documents_with_pypdf(file_path: str, source: str) -> list[Document]:
    reader = PdfReader(file_path)
    documents: list[Document] = []
    for page_number, page in enumerate(reader.pages, start=1):
        text = (page.extract_text() or "").strip()
        if not text:
            continue
        documents.append(
            Document(
                page_content=text,
                metadata={
                    "source": source,
                    "url": source,
                    "page_number": page_number,
                    "filetype": "application/pdf",
                },
            )
        )

    if not documents:
        raise RuntimeError("No textual content extracted from PDF with pypdf.")

    return documents


def _extract_text_from_chat_content(content: Any) -> str:
    if isinstance(content, str):
        return content.strip()
    if isinstance(content, list):
        text_parts: list[str] = []
        for part in content:
            if isinstance(part, dict) and part.get("type") == "text":
                text = part.get("text")
                if isinstance(text, str) and text.strip():
                    text_parts.append(text.strip())
        return "\n".join(text_parts).strip()
    return str(content).strip()


def _load_pdf_documents_with_openai_ocr(file_path: str, source: str) -> list[Document]:
    ocr_model = (
        os.environ.get("OCR_MODEL") or os.environ.get("CHAT_MODEL") or "gpt-4o-mini"
    )
    llm = ChatOpenAI(model=ocr_model, temperature=0)
    pdf = PdfDocument(file_path)
    documents: list[Document] = []

    try:
        for page_number in range(len(pdf)):
            page = pdf[page_number]
            rendered = page.render(scale=2.0)
            image = rendered.to_pil()
            buffer = io.BytesIO()
            image.save(buffer, format="JPEG", quality=75, optimize=True)
            encoded = base64.b64encode(buffer.getvalue()).decode("ascii")

            response = llm.invoke(
                [
                    HumanMessage(
                        content=[
                            {
                                "type": "text",
                                "text": (
                                    "Extract all visible text from this Polish political programme page. "
                                    "Return only plain text transcription. "
                                    "If there is no readable text, return an empty string."
                                ),
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{encoded}",
                                },
                            },
                        ]
                    )
                ]
            )
            text = _extract_text_from_chat_content(response.content)
            if not text:
                continue

            documents.append(
                Document(
                    page_content=text,
                    metadata={
                        "source": source,
                        "url": source,
                        "page_number": page_number + 1,
                        "filetype": "application/pdf",
                        "extraction_method": f"openai_ocr:{ocr_model}",
                    },
                )
            )
    finally:
        pdf.close()

    if not documents:
        raise RuntimeError("No textual content extracted from PDF with OpenAI OCR.")

    log_info(
        f"OpenAI OCR extracted text from {len(documents)} page(s) using model '{ocr_model}'."
    )
    return documents


def _load_source_documents(source: str) -> list[Document]:
    if _is_pdf_source(source):
        return _load_pdf_documents(source)
    if _is_http_url(source):
        loader = UnstructuredLoader(
            web_url=source,
            chunking_strategy="basic",
            max_characters=1_000_000,
            languages=["pol"],
        )
    else:
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

    source_urls: set[str] = {party_config.programme_url}
    documents = _load_source_documents(party_config.programme_url)

    if use_tavily_enrichment:
        enricher = TavilyEnricher()
        discovered_urls = enricher.discover_related_urls(party_config.programme_url)
        source_urls.update(discovered_urls)
        enriched_documents = enricher.extract_documents_from_urls(
            sorted(discovered_urls)
        )
        if enriched_documents:
            documents.extend(enriched_documents)

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

    persist_directory = os.environ.get("CHROMA_PERSIST_DIRECTORY", ".chroma")
    vector_store = Chroma(
        collection_name=party_config.index_name,
        embedding_function=embeddings,
        persist_directory=persist_directory,
    )
    vector_store.add_documents(documents=split_docs)
    log_success(
        f"Upserted {len(split_docs)} chunks into Chroma collection "
        f"'{party_config.index_name}' (persist_directory='{persist_directory}')."
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Load Polish political parties programmes and upsert them to Chroma."
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

    log_header("Starting ingestion to Chroma")
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
