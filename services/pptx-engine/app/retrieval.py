from .db import get_connection
from .embeddings import embed_texts, rerank
from .models import Finding

CANDIDATES_PER_QUERY = 15


def build_query_variants(topic: str) -> list[str]:
    return [
        topic,
        f"key findings and results about {topic}",
        f"methodology and approach used in {topic} research",
        f"recent advances and open challenges in {topic}",
    ]


def _search_chunks(cur, topic: str, embedding: list[float], limit: int) -> list[tuple]:
    cur.execute(
        """
        SELECT c.paper_id, p.title, p.authors, p.year, p.url, c.content,
               1 - (c.embedding <=> %s::vector) AS similarity
        FROM chunks c
        JOIN papers p ON p.paper_id = c.paper_id
        WHERE p.topic = %s
        ORDER BY c.embedding <=> %s::vector
        LIMIT %s
        """,
        (embedding, topic, embedding, limit),
    )
    return cur.fetchall()


def retrieve_findings(topic: str, top_k: int = 8) -> list[Finding]:
    """Multi-query retrieval over pgvector followed by cross-encoder re-ranking."""
    queries = build_query_variants(topic)
    query_embeddings = embed_texts(queries)

    conn = get_connection()
    try:
        with conn.cursor() as cur:
            merged: dict[str, dict] = {}
            for embedding in query_embeddings:
                rows = _search_chunks(cur, topic, embedding, CANDIDATES_PER_QUERY)
                for paper_id, title, authors, year, url, content, similarity in rows:
                    key = f"{paper_id}:{hash(content)}"
                    existing = merged.get(key)
                    if existing is None or similarity > existing["similarity"]:
                        merged[key] = {
                            "paper_id": paper_id,
                            "title": title,
                            "authors": authors or "",
                            "year": year,
                            "url": url,
                            "content": content,
                            "similarity": float(similarity),
                        }
    finally:
        conn.close()

    candidates = list(merged.values())
    if not candidates:
        return []

    rerank_scores = rerank(topic, [c["content"] for c in candidates])
    for candidate, score in zip(candidates, rerank_scores):
        candidate["score"] = score

    candidates.sort(key=lambda c: c["score"], reverse=True)
    top_candidates = candidates[:top_k]

    return [
        Finding(
            paper_id=c["paper_id"],
            title=c["title"],
            authors=c["authors"],
            year=c["year"],
            url=c["url"],
            content=c["content"],
            score=c["score"],
        )
        for c in top_candidates
    ]
