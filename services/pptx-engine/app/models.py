from pydantic import BaseModel


class GenerateRequest(BaseModel):
    topic: str
    num_papers: int | None = None
    force_reingest: bool = False


class GenerateResponse(BaseModel):
    filename: str
    download_url: str
    num_slides: int
    num_sources: int


class Finding(BaseModel):
    paper_id: str
    title: str
    authors: str
    year: int | None
    url: str | None
    content: str
    score: float


class Slide(BaseModel):
    title: str
    bullets: list[str]
    speaker_notes: str
    citations: list[str] = []


class SlidePlan(BaseModel):
    deck_title: str
    slides: list[Slide]
