import json
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware

from src.backend.config import settings
from src.backend.database import (
    get_all_politician_positions,
    get_politician_position_by_id,
    init_db,
    save_contact_submission,
)
from src.backend.parties import PARTY_CONFIGS, load_calculated_positions
from src.backend.rag import RAGService
from src.backend.schemas import (
    AskRequest,
    AskResponse,
    ContactSubmissionRequest,
    ContactSubmissionResponse,
    DeputyActivityStats,
    DeputyDossierResponse,
    DeputyListItem,
    DeputyPublicInfo,
    FeedbackRequest,
    PartyOverview,
    PoliticianOpinionFinding,
    PoliticianPosition,
    PoliticiansOpinionRequest,
    PoliticiansOpinionResponse,
    VotingsSearchRequest,
    VotingsSearchResponse,
)
from src.backend.security import (
    anonymize_ip,
    contact_rate_limiter,
    verify_cloudflare_turnstile,
)
from src.backend.tavily_enrichment import TavilyDeputyService
from src.backend.votings import SejmVotingService

allowed_frontend_origins = [
    origin.strip().rstrip("/")
    for origin in settings.frontend_origin.split(",")
    if origin.strip()
]


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize local SQLite database
    init_db()
    yield


app = FastAPI(title="Polityczny RAG API", version="0.1.0", lifespan=lifespan)
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


@lru_cache(maxsize=1)
def get_tavily_deputy_service() -> TavilyDeputyService:
    return TavilyDeputyService()


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


@app.get("/api/deputies", response_model=list[DeputyListItem])
def list_deputies() -> list[DeputyListItem]:
    try:
        mps = get_sejm_voting_service().get_deputies_list()
        return [DeputyListItem(**mp) for mp in mps]
    except Exception as exc:
        raise HTTPException(
            status_code=500, detail=f"Błąd pobierania listy posłów: {exc}"
        ) from exc


@app.get("/api/deputies/{deputy_id}/dossier", response_model=DeputyDossierResponse)
def get_deputy_dossier(deputy_id: int) -> DeputyDossierResponse:
    voting_svc = get_sejm_voting_service()
    deputy_dict = voting_svc.get_deputy_details(deputy_id)
    if not deputy_dict or not deputy_dict.get("id"):
        raise HTTPException(
            status_code=404, detail="Nie znaleziono posła o podanym ID."
        )

    try:
        activity_stats_dict = voting_svc.get_deputy_activity_stats(deputy_id)
        activity_stats = DeputyActivityStats(**activity_stats_dict)
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Błąd pobierania statystyk posła z Sejm API: {exc}",
        ) from exc

    try:
        tavily_svc = get_tavily_deputy_service()
        public_info_dict = tavily_svc.search_deputy_public_info(
            deputy_name=deputy_dict.get("first_last_name", ""),
            party_name=activity_stats.party_name,
        )
        public_info = DeputyPublicInfo(**public_info_dict)
    except Exception as exc:
        public_info = DeputyPublicInfo(
            query=f"{deputy_dict.get('first_last_name', '')} Sejm",
            answer=f"Błąd pobierania danych publicznych: {exc}",
            sources=[],
        )

    return DeputyDossierResponse(
        deputy=DeputyListItem(**deputy_dict),
        activity_stats=activity_stats,
        public_info=public_info,
    )


@app.get("/api/politicians/positions", response_model=list[PoliticianPosition])
def list_politician_positions() -> list[PoliticianPosition]:
    """Zwraca obliczone i zapisane w bazie danych pozycje polityków na scenie politycznej."""
    try:
        positions = get_all_politician_positions()
        if not positions:
            # Auto-populate first time so the frontend tab is not empty on fresh deployments.
            from calculate_politician_positions import (
                calculate_and_store_all_politicians,
            )

            calculate_and_store_all_politicians(use_ai=False)
            positions = get_all_politician_positions()
        return [PoliticianPosition(**p) for p in positions]
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Błąd pobierania pozycji polityków z bazy danych: {exc}",
        ) from exc


@app.post("/api/politicians/opinions/search", response_model=PoliticiansOpinionResponse)
def search_politician_opinions(
    payload: PoliticiansOpinionRequest,
) -> PoliticiansOpinionResponse:
    try:
        deputies = get_sejm_voting_service().get_deputies_list()
        deputies_by_id = {int(item["id"]): item for item in deputies if item.get("id")}
        tavily_service = get_tavily_deputy_service()

        findings: list[dict] = []
        for deputy_id in payload.deputy_ids:
            deputy = deputies_by_id.get(deputy_id)
            if deputy is None:
                continue
            findings.extend(
                tavily_service.search_deputy_opinion_findings(
                    deputy_name=deputy.get("first_last_name", ""),
                    deputy_id=deputy_id,
                    deputy_club=deputy.get("club_display_name")
                    or deputy.get("club", ""),
                    question=payload.question,
                    limit=payload.limit_per_deputy,
                )
            )

        findings.sort(
            key=lambda item: (
                1 if item.get("published_at") else 0,
                item.get("published_at") or "",
                float(item.get("score") or 0.0),
            ),
            reverse=True,
        )
        response_items = [PoliticianOpinionFinding(**item) for item in findings]
        return PoliticiansOpinionResponse(
            question=payload.question,
            findings_count=len(response_items),
            findings=response_items,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Błąd wyszukiwania opinii polityków: {exc}",
        ) from exc


@app.get("/api/politicians/{deputy_id}/position", response_model=PoliticianPosition)
def get_politician_position(deputy_id: int) -> PoliticianPosition:
    """Zwraca pozycję i szczegóły głosowań pojedynczego polityka."""
    pos = get_politician_position_by_id(deputy_id)
    if not pos:
        raise HTTPException(
            status_code=404,
            detail="Brak obliczonej pozycji dla tego posła w bazie danych.",
        )
    return PoliticianPosition(**pos)


@app.post("/api/contact", response_model=ContactSubmissionResponse)
def submit_contact(
    payload: ContactSubmissionRequest, request: Request
) -> ContactSubmissionResponse:
    # 1. Determine client IP (handles reverse proxy / Cloudflare CF-Connecting-IP / X-Forwarded-For)
    client_ip = (
        request.headers.get("cf-connecting-ip")
        or request.headers.get("x-forwarded-for", "").split(",")[0].strip()
        or (request.client.host if request.client else "unknown")
    )

    # 2. Honeypot protection against simple bot harvesters
    if payload.honeypot and payload.honeypot.strip():
        # Silently succeed for bots so they think their spam succeeded
        return ContactSubmissionResponse(
            status="ok",
            message="Wiadomość została przyjęta.",
        )

    # 3. DDoS / brute-force rate limiting
    if not contact_rate_limiter.is_allowed(client_ip):
        raise HTTPException(
            status_code=429,
            detail="Zbyt wiele zapytań z Twojego adresu. Ze względów bezpieczeństwa prosimy odczekać kilka minut przed kolejną próbą.",
        )

    # 4. Mandatory RODO consent validation
    if not payload.rodo_consent:
        raise HTTPException(
            status_code=400,
            detail="Wymagana jest zgoda na przetwarzanie danych osobowych (RODO).",
        )

    # 5. Cloudflare Turnstile verification
    turnstile_ok, turnstile_msg = verify_cloudflare_turnstile(
        payload.turnstile_token, remote_ip=client_ip
    )
    if not turnstile_ok:
        raise HTTPException(status_code=400, detail=turnstile_msg)

    # 6. Save in local database
    user_agent = request.headers.get("user-agent", "")[:500]
    sub_id = save_contact_submission(
        email=payload.email,
        category=payload.category,
        message=payload.message,
        rodo_consent=payload.rodo_consent,
        ip_address=anonymize_ip(client_ip),
        user_agent=user_agent,
    )

    return ContactSubmissionResponse(
        status="ok",
        message="Dziękujemy! Twoja wiadomość została zapisana w bazie. Odpowiemy najszybciej jak to możliwe.",
        submission_id=sub_id,
    )
