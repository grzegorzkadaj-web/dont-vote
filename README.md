# Politics RAG Web App

Web application to compare Polish political parties' programmes with a RAG architecture:
- **Vector DB**: Pinecone (separate index per party)
- **Backend**: FastAPI + LangChain + OpenAI + Pinecone
- **Frontend**: Next.js

## Party data and Pinecone indices

Programme sources:
- Platforma Obywatelska: `https://platforma.org/upload/document/201/attachments/413/100%20konkretow-pdf.pdf`
- Konfederacja Korony Polskiej: `https://konfederacjakoronypolskiej.pl/wp-content/uploads/2023/03/Program-KKP-internet.pdf`
- Konfederacja: `https://konfederacja.pl/app/uploads/Konfederacja_WiN_Program_2023-1.pdf`
- Partia Razem: `https://partiarazem.pl/deklaracja-programowa`

Pinecone indices:
- Platforma Obywatelska: `parties-po-index`
- Konfederacja Korony Polskiej: `parties-kkp-index`
- Konfederacja: `parties-konfederacja-index`
- Partia Razem: `parties-razem-index`

## Project structure

- `feeding.py` – manual ingestion script (PDF -> chunks -> embeddings -> Pinecone).
- `retriever.py` – CLI query script for quick backend verification.
- `src/backend` – FastAPI app and RAG logic.
- `src/frontend` – Next.js UI.

## Environment variables

Create `.env` in repo root with at least:

```env
OPENAI_API_KEY=...
PINECONE_API_KEY=...
PINECONE_ENVIRONMENT=...
EMBEDDINGS_MODEL=text-embedding-3-large
CHAT_MODEL=gpt-4o-mini
FRONTEND_ORIGIN=http://localhost:3000
NEXT_PUBLIC_BACKEND_URL=http://localhost:8000
TAVILY_API_KEY=... # optional, only for --use-tavily-enrichment
```

`NEXT_PUBLIC_BACKEND_URL` can be set with or without a trailing slash.
`FRONTEND_ORIGIN` accepts one origin or a comma-separated list (for example local + Railway frontend), and each value can be set with or without a trailing slash.

## Installation

Python:
```bash
uv sync
```

Frontend:
```bash
cd src/frontend
npm install
```

## Ingestion (manual, local only)

Load all parties to Pinecone:

```bash
uv run python feeding.py --party all
```

Load a single party:

```bash
uv run python feeding.py --party po
uv run python feeding.py --party kkp
uv run python feeding.py --party konfederacja
uv run python feeding.py --party razem
```

Optional Tavily URL enrichment:

```bash
uv run python feeding.py --party all --use-tavily-enrichment
```

For website-based programmes (for example Partia Razem), Tavily extraction is required and uses `TAVILY_API_KEY`.

## Run backend

```bash
uv run uvicorn src.backend.main:app --host 0.0.0.0 --port 8000 --reload
```

## Run frontend

```bash
cd src/frontend
npm run dev
```

Open `http://localhost:3000`.

## Production note

On production (Railway), run only the retriever/backend part (`src/backend`).  
Ingestion (`feeding.py`) is designed for manual local execution before deployment.