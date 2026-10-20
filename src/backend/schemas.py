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
    rodo_consent: bool = Field(..., description="Zgoda na przetwarzanie danych osobowych (RODO)")
    turnstile_token: str | None = None
    honeypot: str | None = None


class ContactSubmissionResponse(BaseModel):
    status: str
    message: str
    submission_id: int | None = None
