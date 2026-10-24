from pydantic import BaseModel, Field


class AskRequest(BaseModel):
    question: str = Field(min_length=5, max_length=2_000)
    parties: list[str] | None = None


class SourceItem(BaseModel):
    url: str
    score: float
    snippet: str


class PartyAnswer(BaseModel):
    party_key: str
    party_display_name: str
    answer: str
    sources: list[SourceItem]


class AskResponse(BaseModel):
    question: str
    answers: list[PartyAnswer]


class PartyOverview(BaseModel):
    key: str
    display_name: str
    index_name: str
    programme_url: str
    axis_x: float
    axis_y: float
    axis_label: str
    axis_justification: str | None = None


class FeedbackRequest(BaseModel):
    question: str = Field(min_length=5, max_length=2_000)
    party_key: str = Field(min_length=2, max_length=64)
    helpful: bool


class VotingPartyStat(BaseModel):
    club_id: str
    club_name: str
    yes: int
    no: int
    abstain: int
    absent: int
    total: int
    stance: str
    percent_yes: float
    percent_no: float
    percent_abstain: float


class VotingTotalVotes(BaseModel):
    yes: int
    no: int
    abstain: int
    absent: int = 0
    total: int


class ActVotingItem(BaseModel):
    id: str
    act_name: str
    short_description: str
    document_type: str = "projekt ustawy"
    sitting: int
    voting_number: int
    date: str | None = None
    topic: str | None = None
    passed: bool = True
    display_address: str | None = None
    eli: str | None = None
    links: dict[str, str] = Field(default_factory=dict)
    total_votes: VotingTotalVotes
    parties: list[VotingPartyStat] = Field(default_factory=list)


class VotingsSearchRequest(BaseModel):
    query: str = Field(min_length=2, max_length=500)
    limit: int = Field(default=8, ge=1, le=20)


class VotingsSearchResponse(BaseModel):
    query: str
    results_count: int
    acts: list[ActVotingItem]


class ContactSubmissionRequest(BaseModel):
    email: str = Field(min_length=5, max_length=254)
    category: str = Field(default="pytanie", min_length=2, max_length=64)
    message: str = Field(min_length=10, max_length=5000)
    rodo_consent: bool = Field(
        ..., description="Zgoda na przetwarzanie danych osobowych (RODO)"
    )
    turnstile_token: str | None = None
    honeypot: str | None = None


class ContactSubmissionResponse(BaseModel):
    status: str
    message: str
    submission_id: int | None = None


class DeputyListItem(BaseModel):
    id: int
    first_last_name: str
    last_first_name: str
    club: str
    club_display_name: str
    district_name: str | None = None
    district_num: int | None = None
    email: str | None = None
    photo_url: str
    active: bool = True


class DeputyActivityStats(BaseModel):
    deputy_id: int
    total_votings: int
    voted_votings: int
    unexcused_absences: int
    unexcused_absence_days: int
    excused_absences: int
    attendance_rate: float
    club_id: str
    party_name: str
    act_proposals_count: int
    interpellations_count: int
    written_questions_count: int
    term: int = 10


class TavilySearchResultItem(BaseModel):
    title: str
    url: str
    snippet: str
    score: float | None = None


class DeputyPublicInfo(BaseModel):
    query: str
    answer: str | None = None
    sources: list[TavilySearchResultItem] = Field(default_factory=list)


class DeputyDossierResponse(BaseModel):
    deputy: DeputyListItem
    activity_stats: DeputyActivityStats
    public_info: DeputyPublicInfo


class PoliticiansOpinionRequest(BaseModel):
    question: str = Field(min_length=5, max_length=500)
    deputy_ids: list[int] = Field(min_length=1, max_length=25)
    limit_per_deputy: int = Field(default=3, ge=1, le=5)


class PoliticianOpinionFinding(BaseModel):
    deputy_id: int
    deputy_name: str
    deputy_club: str
    title: str
    url: str
    snippet: str
    published_at: str | None = None
    score: float | None = None


class PoliticiansOpinionResponse(BaseModel):
    question: str
    findings_count: int
    findings: list[PoliticianOpinionFinding]


class PoliticianVotingDetail(BaseModel):
    sitting: int
    voting_number: int
    short_title: str
    category: str
    axis: str  # "x" or "y"
    vote: str  # "YES", "NO", "ABSTAIN", "ABSENT"
    vote_label: str  # "Za", "Przeciw", "Wstrzymał się", "Nieobecny"
    impact: str  # "lewicowy", "prawicowy", "konserwatywny", "progresywny", etc.
    description: str


class PoliticianPosition(BaseModel):
    deputy_id: int
    first_last_name: str
    club: str
    club_display_name: str
    photo_url: str
    axis_x: float
    axis_y: float
    axis_label: str
    summary: str
    economic_description: str
    worldview_description: str
    voting_details: list[PoliticianVotingDetail] = Field(default_factory=list)
    calculated_at: str
