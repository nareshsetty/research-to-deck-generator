import json

import openai

from .config import settings
from .models import Finding, Slide, SlidePlan

SYSTEM_PROMPT = """You are a research analyst who turns retrieved paper excerpts into a concise, \
well-organized slide deck outline. Base every claim only on the numbered excerpts provided. \
Do not invent findings, statistics, or papers that are not present in the excerpts. If the \
excerpts do not support a strong claim, write a more general/qualified bullet instead of \
fabricating specifics."""

USER_PROMPT_TEMPLATE = """Topic: {topic}

Numbered source excerpts (cite by number in "citation_indices"):
{excerpts}

Produce a slide deck outline as JSON with this exact shape:
{{
  "deck_title": "string",
  "slides": [
    {{
      "title": "string",
      "bullets": ["string", "string", "string"],
      "speaker_notes": "string, 2-4 sentences expanding on the bullets",
      "citation_indices": [1, 2]
    }}
  ]
}}

Rules:
- Produce between 5 and 8 content slides (not counting a title slide, which you should not include).
- Each slide's citation_indices must reference the numbered excerpts that support its bullets.
- Every content slide must have at least one citation.
- Respond with ONLY the JSON object, no prose, no markdown code fences.
"""


def _format_excerpts(findings: list[Finding]) -> str:
    lines = []
    for index, finding in enumerate(findings, start=1):
        lines.append(
            f"[{index}] {finding.title} ({finding.authors}, {finding.year}): {finding.content[:800]}"
        )
    return "\n\n".join(lines)


def synthesize_slide_plan(topic: str, findings: list[Finding]) -> SlidePlan:
    client = openai.OpenAI(api_key=settings.groq_api_key, base_url="https://api.groq.com/openai/v1")

    completion = client.chat.completions.create(
        model=settings.groq_model,
        max_tokens=4096,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": USER_PROMPT_TEMPLATE.format(
                    topic=topic, excerpts=_format_excerpts(findings)
                ),
            },
        ],
    )

    raw_text = completion.choices[0].message.content.strip()
    if raw_text.startswith("```"):
        raw_text = raw_text.strip("`")
        raw_text = raw_text.split("\n", 1)[1] if "\n" in raw_text else raw_text

    data = json.loads(raw_text)

    slides = []
    for slide_data in data.get("slides", []):
        indices = slide_data.get("citation_indices", [])
        citations = [
            findings[i - 1].paper_id
            for i in indices
            if isinstance(i, int) and 1 <= i <= len(findings)
        ]
        slides.append(
            Slide(
                title=slide_data.get("title", "Untitled"),
                bullets=slide_data.get("bullets", []),
                speaker_notes=slide_data.get("speaker_notes", ""),
                citations=citations,
            )
        )

    return SlidePlan(deck_title=data.get("deck_title", topic.title()), slides=slides)
