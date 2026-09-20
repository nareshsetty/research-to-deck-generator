import io
import logging

import requests
from pypdf import PdfReader

from .config import settings
from .db import get_connection
from .embeddings import embed_texts

logger = logging.getLogger(__name__)

OPENALEX_WORKS_URL = "https://api.openalex.org/works"
SELECT_FIELDS = "id,title,abstract_inverted_index,authorships,publication_year,doi,best_oa_location"
CHUNK_WORDS = 200
CHUNK_OVERLAP_WORDS = 50


def reconstruct_abstract(inverted_index: dict[str, list[int]] | None) -> str:
    """OpenAlex returns abstracts as an inverted index ({word: [positions]}) to
    respect publisher copyright on full-text redistribution. Rebuild plain text from it."""
    if not inverted_index:
        return ""
    positions: list[tuple[int, str]] = []
    for word, indices in inverted_index.items():
        for index in indices:
            positions.append((index, word))
    positions.sort(key=lambda item: item[0])
    return " ".join(word for _, word in positions)


def search_papers(topic: str, limit: int) -> list[dict]:
    params = {
        "search": topic,
        "per_page": min(limit, 200),
        "select": SELECT_FIELDS,
    }
    if settings.openalex_mailto:
        params["mailto"] = settings.openalex_mailto

    response = requests.get(OPENALEX_WORKS_URL, params=params, timeout=30)
    response.raise_for_status()
    return response.json().get("results", [])


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
    """Fetch papers for a topic from OpenAlex, chunk + embed their text,
    and upsert them into Postgres/pgvector. Returns the number of papers ingested."""
    limit = limit or settings.max_papers_per_topic
    papers = search_papers(topic, limit)

    conn = get_connection()
    ingested = 0
    try:
        with conn.cursor() as cur:
            for paper in papers:
                paper_id = paper.get("id")
                title = paper.get("title")
                if not paper_id or not title:
                    continue

                abstract = reconstruct_abstract(paper.get("abstract_inverted_index"))
                authors = ", ".join(
                    authorship["author"]["display_name"]
                    for authorship in paper.get("authorships") or []
                    if authorship.get("author", {}).get("display_name")
                )
                year = paper.get("publication_year")
                url = paper.get("doi") or paper_id

                pdf_url = (paper.get("best_oa_location") or {}).get("pdf_url")
                pdf_text = fetch_pdf_text(pdf_url) if pdf_url else None
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
