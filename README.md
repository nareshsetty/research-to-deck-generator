# Research-to-Deck Generator

RAG over 50+ papers via the Semantic Scholar API → synthesize findings with Claude → auto-generate a branded, cited PPTX deck with speaker notes. Exposed as a Next.js API, backed by a BullMQ job queue and a Python FastAPI pipeline service.

## Architecture

```
apps/web        Next.js app — POST /api/generate enqueues a job, GET /api/status/:id polls it
apps/worker     Node BullMQ worker — picks up jobs, calls the Python pipeline service
services/pptx-engine   Python FastAPI service — ingestion, RAG, synthesis, PPTX assembly
```

- **Ingestion**: Semantic Scholar API → fetch paper abstracts (+ open-access PDF text when available) → chunk → embed (sentence-transformers, local, no extra API key) → store in Postgres/pgvector.
- **RAG**: 4 query variants per topic, similarity search per variant, merge + dedupe, then cross-encoder re-ranking to surface the highest-signal chunks.
- **Synthesis**: Claude (`claude-sonnet-5`) turns the top findings into a structured slide plan (titles, bullets, speaker notes, per-slide citations), grounded only in the retrieved excerpts.
- **Deck assembly**: python-pptx builds a branded deck — title slide, one slide per topic with footer citation markers and speaker notes, and a numbered References slide.
- **API**: `POST /api/generate { topic }` → BullMQ job → `GET /api/status/:jobId` → `{ status, downloadUrl }` once complete.

Why a separate Python service instead of running python-pptx inside the Next.js API route: Vercel's Next.js runtime is Node/Edge only and cannot execute python-pptx, sentence-transformers, or pgvector's Python client. The Next.js app and Node worker only orchestrate; all Python-dependent work runs in `services/pptx-engine`.

## Prerequisites

- Node.js 20+
- Python 3.11 (3.14 currently lacks prebuilt wheels for `torch`/`sentence-transformers` — this repo's Python service was built and tested against 3.11)
- Docker (for local Postgres+pgvector and Redis) — or your own Postgres 16 with the `vector` extension and a Redis instance
- An Anthropic API key
- Optionally, a Semantic Scholar API key (the public API works without one at a lower rate limit)

## Local setup

### 1. Start infrastructure

```bash
docker compose up -d
```

This starts Postgres (with pgvector) on `localhost:5432` and Redis on `localhost:6379`.

### 2. Python pipeline service (`services/pptx-engine`)

```bash
cd services/pptx-engine
uv venv --python 3.11 .venv
uv pip install -p .venv -r requirements.txt
cp .env.example .env
# edit .env and set ANTHROPIC_API_KEY (and SEMANTIC_SCHOLAR_API_KEY if you have one)
.venv/Scripts/activate   # or: source .venv/bin/activate on macOS/Linux
uvicorn app.main:app --reload --port 8000
```

Verify each pipeline stage independently:

```bash
python scripts/test_deck.py                                    # no DB/network/API key needed
python scripts/test_ingestion.py "retrieval augmented generation"
python scripts/test_retrieval.py "retrieval augmented generation"
python scripts/test_synthesis.py "retrieval augmented generation"  # needs ANTHROPIC_API_KEY
```

### 3. Worker (`apps/worker`)

```bash
cd apps/worker
npm install
cp .env.example .env
npm start
```

### 4. Web app (`apps/web`)

```bash
cd apps/web
npm install
cp .env.local.example .env.local
npm run dev
```

Open http://localhost:3000, enter a topic, and watch it move through waiting → active → completed with a download link.

### End-to-end via curl

```bash
curl -X POST http://localhost:3000/api/generate \
  -H "Content-Type: application/json" \
  -d '{"topic": "retrieval augmented generation"}'
# => { "jobId": "1" }

curl http://localhost:3000/api/status/1
# => { "status": "completed", "downloadUrl": "http://localhost:8000/download/<uuid>.pptx", ... }
```

## Deployment notes

- **`apps/web`** deploys to Vercel as-is (Next.js). Set `REDIS_URL` to a managed Redis instance (e.g. Upstash) in the Vercel project's environment variables.
- **`apps/worker`** and **`services/pptx-engine`** are long-running processes (the worker holds an open BullMQ connection; the Python service keeps embedding/re-ranking models loaded in memory) and are not a fit for Vercel's serverless functions. Deploy them to a persistent host (Render, Fly.io, Railway, or a small VM) pointed at the same Redis and Postgres instances as the web app.
- No infrastructure has been provisioned or deployed as part of this build — connect real Postgres/Redis/Vercel projects and run the deploy yourself when ready.

## Environment variables

| Variable | Used by | Purpose |
|---|---|---|
| `ANTHROPIC_API_KEY` | pptx-engine | Claude synthesis calls |
| `SEMANTIC_SCHOLAR_API_KEY` | pptx-engine | Optional, raises Semantic Scholar rate limit |
| `DATABASE_URL` | pptx-engine | Postgres/pgvector connection |
| `REDIS_URL` | web, worker | BullMQ queue connection |
| `PYTHON_SERVICE_URL` | worker | Internal URL to call the pipeline service |
| `PUBLIC_PYTHON_SERVICE_URL` | worker | Public URL used to build the download link returned to clients |
