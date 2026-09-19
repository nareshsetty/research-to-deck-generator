"""Run: python scripts/test_synthesis.py "your topic" (after test_ingestion.py) """
import json
import sys

sys.path.insert(0, ".")

from app.retrieval import retrieve_findings
from app.synthesis import synthesize_slide_plan

if __name__ == "__main__":
    topic = sys.argv[1] if len(sys.argv) > 1 else "retrieval augmented generation"
    findings = retrieve_findings(topic)
    if not findings:
        print("No findings retrieved — run test_ingestion.py first.")
        sys.exit(1)

    slide_plan = synthesize_slide_plan(topic, findings)
    print(json.dumps(slide_plan.model_dump(), indent=2))
