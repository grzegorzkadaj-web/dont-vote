import json
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from src.backend.config import settings
from src.backend.parties import PARTY_CONFIGS, load_calculated_positions
from src.backend.rag import RAGService
from src.backend.schemas import (
    AskRequest,
    AskResponse,
    FeedbackRequest,
    PartyOverview,
    VotingsSearchRequest,
    VotingsSearchResponse,
)
from src.backend.votings import SejmVotingService

allowed_frontend_origins = [
    origin.strip().rstrip("/")
    for origin in settings.frontend_origin.split(",")
    if origin.strip()
]

app = FastAPI(title="Polityczny RAG API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_frontend_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@lru_cache(maxsize=1)
def get_rag_service() -> RAGService:
    return RAGService()


@lru_cache(maxsize=1)
def get_sejm_voting_service() -> SejmVotingService:
    return SejmVotingService()


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/parties", response_model=list[PartyOverview])
def get_parties() -> list[PartyOverview]:
    calculated_positions = load_calculated_positions(settings.party_positions_path)
    return [
        PartyOverview(
            key=config.key,
            display_name=config.display_name,
            index_name=config.index_name,
            programme_url=config.programme_url,
            axis_x=float(
                calculated_positions.get(config.key, {}).get("axis_x", config.axis_x)
            ),
            axis_y=float(
                calculated_positions.get(config.key, {}).get("axis_y", config.axis_y)
            ),
            axis_label=str(
                calculated_positions.get(config.key, {}).get(
                    "axis_label", config.axis_label
                )
            ),
            axis_justification=str(
                calculated_positions.get(config.key, {}).get("justification", "")
            )
            or None,
        )
        for config in PARTY_CONFIGS.values()
    ]


@app.post("/api/ask", response_model=AskResponse)
def ask_question(payload: AskRequest) -> AskResponse:
    try:
        return get_rag_service().ask(question=payload.question, parties=payload.parties)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/feedback")
def submit_feedback(payload: FeedbackRequest) -> dict[str, str]:
    feedback_path = Path(settings.feedback_store_path)
    feedback_path.parent.mkdir(parents=True, exist_ok=True)

    row = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "question": payload.question,
        "party_key": payload.party_key,
        "helpful": payload.helpful,
    }
    with feedback_path.open("a", encoding="utf-8") as file:
        file.write(json.dumps(row, ensure_ascii=False) + "\n")

    return {"status": "saved"}


@app.post("/api/votings/search", response_model=VotingsSearchResponse)
def search_votings(payload: VotingsSearchRequest) -> VotingsSearchResponse:
    try:
        acts = get_sejm_voting_service().search_acts_and_votes(
            query=payload.query, limit=payload.limit
        )
        return VotingsSearchResponse(
            query=payload.query, results_count=len(acts), acts=acts
        )
    except Exception as exc:
        raise HTTPException(
            status_code=500, detail=f"Błąd wyszukiwania głosowań: {exc}"
        ) from exc


@app.get("/api/votings/search", response_model=VotingsSearchResponse)
def search_votings_get(
    q: str = Query(..., min_length=2, description="Temat lub słowo kluczowe"),
    limit: int = Query(8, ge=1, le=20),
) -> VotingsSearchResponse:
    try:
        acts = get_sejm_voting_service().search_acts_and_votes(query=q, limit=limit)
        return VotingsSearchResponse(query=q, results_count=len(acts), acts=acts)
    except Exception as exc:
        raise HTTPException(
            status_code=500, detail=f"Błąd wyszukiwania głosowań: {exc}"
        ) from exc
