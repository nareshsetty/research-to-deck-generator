from functools import lru_cache

from sentence_transformers import CrossEncoder, SentenceTransformer

from .config import settings


@lru_cache(maxsize=1)
def get_embedder() -> SentenceTransformer:
    return SentenceTransformer(settings.embedding_model)


@lru_cache(maxsize=1)
def get_reranker() -> CrossEncoder:
    return CrossEncoder(settings.reranker_model)


def embed_texts(texts: list[str]) -> list[list[float]]:
    if not texts:
        return []
    vectors = get_embedder().encode(texts, normalize_embeddings=True)
    return [vector.tolist() for vector in vectors]


def rerank(query: str, candidates: list[str]) -> list[float]:
    if not candidates:
        return []
    pairs = [[query, candidate] for candidate in candidates]
    scores = get_reranker().predict(pairs)
    return [float(score) for score in scores]
