# Copilot Instructions for `politics`

## Build, test, and lint commands

This repository is a small Python project managed with `uv` (`pyproject.toml` + `uv.lock`).

- Install dependencies:
  - `uv sync`
- Run ingestion pipeline (load PDF/URL content, chunk it, embed it, upsert to Pinecone):
  - `uv run python feeding.py`
- Run retrieval query pipeline:
  - `uv run python retriever.py`
- Lint/format tools available in project dependencies:
  - `uv run isort .`
  - `uv run black .`

Testing status:
- There is currently no configured test suite (`tests/` and `pytest` config are absent), so there is no repository-native single-test command yet.

## High-level architecture

The codebase is organized around a two-step Retrieval-Augmented Generation flow:

1. **Ingestion (`feeding.py`)**
   - Loads source documents (currently from URL, can also include local files) using `UnstructuredLoader`.
   - Splits content with `RecursiveCharacterTextSplitter` (`chunk_size=1000`, `chunk_overlap=200`).
   - Creates embeddings with `OpenAIEmbeddings` (model from env) and writes vectors to Pinecone via `PineconeVectorStore.from_documents`.

2. **Retrieval + generation (`retriever.py`)**
   - Reconnects to the same Pinecone index and embedding model.
   - Builds a retriever (`k=5`) and composes a LangChain runnable pipeline:
     `question -> retriever -> format context -> prompt -> ChatOpenAI -> string output`.
   - Prompt instructs answers in Polish and only from retrieved context.

Supporting utility:
- `logger.py` defines ANSI color logging helpers (`log_info`, `log_success`, `log_error`, `log_warning`, `log_header`) for script-style CLI output.

## Key conventions in this repository

- **Environment-driven runtime configuration**: both pipelines call `load_dotenv()` and read key settings from environment variables (`EMBEDDINGS_MODEL`, `INDEX_NAME`). Keep new components consistent with this pattern.
- **Script entrypoint style**: operational flows are implemented in top-level scripts guarded by `if __name__ == "__main__":` rather than package modules/CLI framework.
- **Shared vector contract between ingestion and retrieval**: `feeding.py` and `retriever.py` must use compatible embedding model and the same Pinecone index name; changing either side requires coordinated updates.
- **Polish-language answer behavior**: retrieval prompt currently enforces Polish output. Preserve this unless intentionally changing product behavior.
