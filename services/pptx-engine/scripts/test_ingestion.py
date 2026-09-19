"""Run: python scripts/test_ingestion.py "your topic" """
import sys

sys.path.insert(0, ".")

from app.db import init_db
from app.ingestion import ingest_topic

if __name__ == "__main__":
    topic = sys.argv[1] if len(sys.argv) > 1 else "retrieval augmented generation"
    init_db()
    count = ingest_topic(topic, limit=10)
    print(f"Ingested {count} papers for topic: {topic!r}")
