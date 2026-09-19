import psycopg
from pgvector.psycopg import register_vector

from .config import settings

SCHEMA_SQL = """
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS papers (
    paper_id TEXT PRIMARY KEY,
    topic TEXT NOT NULL,
    title TEXT NOT NULL,
    authors TEXT,
    year INTEGER,
    url TEXT,
    abstract TEXT
);

CREATE TABLE IF NOT EXISTS chunks (
    id SERIAL PRIMARY KEY,
    paper_id TEXT NOT NULL REFERENCES papers(paper_id) ON DELETE CASCADE,
    chunk_index INTEGER NOT NULL,
    content TEXT NOT NULL,
    embedding vector(%(embedding_dim)s),
    UNIQUE(paper_id, chunk_index)
);
"""


def get_connection() -> psycopg.Connection:
    conn = psycopg.connect(settings.database_url, autocommit=True)
    register_vector(conn)
    return conn


def init_db() -> None:
    conn = psycopg.connect(settings.database_url, autocommit=True)
    try:
        with conn.cursor() as cur:
            cur.execute(
                SCHEMA_SQL.replace("%(embedding_dim)s", str(settings.embedding_dim))
            )
    finally:
        conn.close()


def topic_already_ingested(topic: str) -> bool:
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM papers WHERE topic = %s", (topic,))
            (count,) = cur.fetchone()
            return count > 0
    finally:
        conn.close()
