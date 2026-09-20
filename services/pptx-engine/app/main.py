import logging
import os
import uuid

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse

from .config import settings
from .db import init_db, topic_already_ingested
from .deck import build_deck
from .ingestion import ingest_topic
from .models import GenerateRequest, GenerateResponse
from .retrieval import retrieve_findings
from .synthesis import synthesize_slide_plan

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Research-to-Deck Generator")


@app.on_event("startup")
def on_startup() -> None:
    init_db()


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/generate", response_model=GenerateResponse)
def generate(request: GenerateRequest) -> GenerateResponse:
    topic = request.topic.strip()
    if not topic:
        raise HTTPException(status_code=400, detail="topic must not be empty")

    if request.force_reingest or not topic_already_ingested(topic):
        logger.info("Ingesting papers for topic: %s", topic)
        ingested = ingest_topic(topic, limit=request.num_papers)
        if ingested == 0 and not topic_already_ingested(topic):
            raise HTTPException(
                status_code=422,
                detail="No papers with usable text were found for this topic on OpenAlex.",
            )

    findings = retrieve_findings(topic)
    if not findings:
        raise HTTPException(status_code=422, detail="No relevant findings retrieved for this topic.")

    slide_plan = synthesize_slide_plan(topic, findings)

    filename = f"{uuid.uuid4().hex}.pptx"
    output_path = f"{settings.output_dir}/{filename}"
    build_deck(slide_plan, findings, output_path)

    return GenerateResponse(
        filename=filename,
        download_url=f"/download/{filename}",
        num_slides=len(slide_plan.slides),
        num_sources=len({f.paper_id for f in findings}),
    )


@app.get("/download/{filename}")
def download(filename: str) -> FileResponse:
    safe_name = os.path.basename(filename)
    path = f"{settings.output_dir}/{safe_name}"
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(
        path,
        media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation",
        filename=safe_name,
    )
