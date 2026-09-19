import os

from dotenv import load_dotenv

load_dotenv()


class Settings:
    anthropic_api_key: str = os.environ.get("ANTHROPIC_API_KEY", "")
    semantic_scholar_api_key: str = os.environ.get("SEMANTIC_SCHOLAR_API_KEY", "")
    database_url: str = os.environ.get(
        "DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/research_deck"
    )
    claude_model: str = os.environ.get("CLAUDE_MODEL", "claude-sonnet-5")
    embedding_model: str = os.environ.get("EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
    reranker_model: str = os.environ.get("RERANKER_MODEL", "cross-encoder/ms-marco-MiniLM-L-6-v2")
    embedding_dim: int = int(os.environ.get("EMBEDDING_DIM", "384"))
    output_dir: str = os.environ.get("OUTPUT_DIR", os.path.join(os.path.dirname(__file__), "..", "output"))
    max_papers_per_topic: int = int(os.environ.get("MAX_PAPERS_PER_TOPIC", "50"))


settings = Settings()
