"""Run: python scripts/test_retrieval.py "your topic" (after test_ingestion.py) """
import sys

sys.path.insert(0, ".")

from app.retrieval import retrieve_findings

if __name__ == "__main__":
    topic = sys.argv[1] if len(sys.argv) > 1 else "retrieval augmented generation"
    findings = retrieve_findings(topic)
    print(f"Retrieved {len(findings)} findings for topic: {topic!r}\n")
    for i, finding in enumerate(findings, start=1):
        print(f"[{i}] score={finding.score:.3f} {finding.title} ({finding.year})")
        print(f"    {finding.content[:160]}...\n")
