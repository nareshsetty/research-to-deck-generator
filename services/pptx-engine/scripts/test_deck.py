"""Run: python scripts/test_deck.py — builds a deck from hardcoded sample data,
with no DB, network, or API key required. Use this to sanity-check PPTX assembly
and branding in isolation."""
import sys

sys.path.insert(0, ".")

from app.deck import build_deck
from app.models import Finding, Slide, SlidePlan

SAMPLE_FINDINGS = [
    Finding(
        paper_id="sample-1",
        title="Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks",
        authors="Lewis et al.",
        year=2020,
        url="https://arxiv.org/abs/2005.11401",
        content="RAG combines a retriever with a seq2seq generator to ground outputs in retrieved documents.",
        score=0.9,
    ),
    Finding(
        paper_id="sample-2",
        title="Dense Passage Retrieval for Open-Domain Question Answering",
        authors="Karpukhin et al.",
        year=2020,
        url="https://arxiv.org/abs/2004.04906",
        content="Dense embeddings trained with a dual-encoder outperform sparse retrieval like BM25.",
        score=0.85,
    ),
]

SAMPLE_PLAN = SlidePlan(
    deck_title="Sample Deck: Retrieval-Augmented Generation",
    slides=[
        Slide(
            title="What is RAG?",
            bullets=[
                "Combines a retriever with a generator model",
                "Grounds generated text in retrieved evidence",
            ],
            speaker_notes="RAG was introduced to reduce hallucination by conditioning generation on retrieved passages.",
            citations=["sample-1"],
        ),
        Slide(
            title="Why Dense Retrieval Matters",
            bullets=[
                "Dual-encoder embeddings outperform sparse BM25 retrieval",
                "Enables semantic matching beyond keyword overlap",
            ],
            speaker_notes="Dense Passage Retrieval showed large gains over traditional sparse methods on open-domain QA benchmarks.",
            citations=["sample-2"],
        ),
    ],
)

if __name__ == "__main__":
    output_path = "output/sample_deck.pptx"
    build_deck(SAMPLE_PLAN, SAMPLE_FINDINGS, output_path)
    print(f"Sample deck written to {output_path}")
