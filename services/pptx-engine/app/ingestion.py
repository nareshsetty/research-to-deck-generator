import io
import logging

import requests
from pypdf import PdfReader

from .config import settings
from .db import get_connection
from .embeddings import embed_texts

logger = logging.getLogger(__name__)

SEMANTIC_SCHOLAR_SEARCH_URL = "https://api.semanticscholar.org/graph/v1/paper/search"
PAPER_FIELDS = "title,abstract,authors,year,url,openAccessPdf,externalIds"
CHUNK_WORDS = 200
CHUNK_OVERLAP_WORDS = 50


def search_papers(topic: str, limit: int) -> list[dict]:
    headers = {}
    if settings.semantic_scholar_api_key:
        headers["x-api-key"] = settings.semantic_scholar_api_key

    response = requests.get(
        SEMANTIC_SCHOLAR_SEARCH_URL,
        params={"query": topic, "limit": min(limit, 100), "fields": PAPER_FIELDS},
        headers=headers,
        timeout=30,
    )
    response.raise_for_status()
    return response.json().get("data", [])


def fetch_pdf_text(pdf_url: str) -> str | None:
    try:
        response = requests.get(pdf_url, timeout=20)
        response.raise_for_status()
        reader = PdfReader(io.BytesIO(response.content))
        pages = [page.extract_text() or "" for page in reader.pages[:15]]
        text = "\n".join(pages).strip()
        return text or None
    except Exception as exc:  # noqa: BLE001 - PDF fetching is best-effort
        logger.warning("PDF fetch failed for %s: %s", pdf_url, exc)
        return None


def chunk_text(text: str) -> list[str]:
    words = text.split()
    if not words:
        return []
    chunks = []
    step = CHUNK_WORDS - CHUNK_OVERLAP_WORDS
    for start in range(0, len(words), step):
        chunk_words = words[start : start + CHUNK_WORDS]
        if not chunk_words:
            continue
        chunks.append(" ".join(chunk_words))
        if start + CHUNK_WORDS >= len(words):
            break
    return chunks


def ingest_topic(topic: str, limit: int | None = None) -> int:
    """Fetch papers for a topic from Semantic Scholar, chunk + embed their text,
    and upsert them into Postgres/pgvector. Returns the number of papers ingested."""
    limit = limit or settings.max_papers_per_topic
    papers = search_papers(topic, limit)

    conn = get_connection()
    ingested = 0
    try:
        with conn.cursor() as cur:
            for paper in papers:
                paper_id = paper.get("paperId")
                title = paper.get("title")
                if not paper_id or not title:
                    continue

                abstract = paper.get("abstract") or ""
                authors = ", ".join(a.get("name", "") for a in paper.get("authors") or [])
                year = paper.get("year")
                url = paper.get("url")

                pdf_info = paper.get("openAccessPdf") or {}
                pdf_text = fetch_pdf_text(pdf_info["url"]) if pdf_info.get("url") else None
                full_text = pdf_text or abstract
                if not full_text:
                    continue

                cur.execute(
                    """
                    INSERT INTO papers (paper_id, topic, title, authors, year, url, abstract)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (paper_id) DO UPDATE SET
                        topic = EXCLUDED.topic,
                        title = EXCLUDED.title,
                        authors = EXCLUDED.authors,
                        year = EXCLUDED.year,
                        url = EXCLUDED.url,
                        abstract = EXCLUDED.abstract
                    """,
                    (paper_id, topic, title, authors, year, url, abstract),
                )

                chunks = chunk_text(full_text)
                if not chunks:
                    continue
                embeddings = embed_texts(chunks)
                for index, (content, embedding) in enumerate(zip(chunks, embeddings)):
                    cur.execute(
                        """
                        INSERT INTO chunks (paper_id, chunk_index, content, embedding)
                        VALUES (%s, %s, %s, %s)
                        ON CONFLICT (paper_id, chunk_index) DO UPDATE SET
                            content = EXCLUDED.content,
                            embedding = EXCLUDED.embedding
                        """,
                        (paper_id, index, content, embedding),
                    )
                ingested += 1
    finally:
        conn.close()

    return ingested
