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


class FeedbackRequest(BaseModel):
    question: str = Field(min_length=5, max_length=2_000)
    party_key: str = Field(min_length=2, max_length=64)
    helpful: bool
