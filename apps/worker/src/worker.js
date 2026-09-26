import "dotenv/config";
import { Worker } from "bullmq";
import IORedis from "ioredis";

const REDIS_URL = process.env.REDIS_URL || "redis://localhost:6379";
const PYTHON_SERVICE_URL = process.env.PYTHON_SERVICE_URL || "http://localhost:8000";
const PUBLIC_PYTHON_SERVICE_URL = process.env.PUBLIC_PYTHON_SERVICE_URL || PYTHON_SERVICE_URL;
const QUEUE_NAME = "deck-generation";

async function processJob(job) {
  const { topic } = job.data;
  if (!topic) {
    throw new Error("Job is missing required 'topic' field");
  }

  console.log(`[worker] job ${job.id}: generating deck for topic "${topic}"`);

  const response = await fetch(`${PYTHON_SERVICE_URL}/generate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ topic }),
    // Ingesting ~50 papers + embedding + rerank + synthesis on CPU can run well past
    // undici's default 5-minute fetch timeout, which surfaces as an opaque "fetch failed".
    signal: AbortSignal.timeout(20 * 60 * 1000),
  });

  if (!response.ok) {
    const body = await response.text();
    throw new Error(`pptx-engine returned ${response.status}: ${body}`);
  }

  const data = await response.json();
  console.log(`[worker] job ${job.id}: deck ready (${data.num_slides} slides, ${data.num_sources} sources)`);

  return {
    filename: data.filename,
    downloadUrl: `${PUBLIC_PYTHON_SERVICE_URL}${data.download_url}`,
    numSlides: data.num_slides,
    numSources: data.num_sources,
  };
}

const connection = new IORedis(REDIS_URL, { maxRetriesPerRequest: null });

const worker = new Worker(QUEUE_NAME, processJob, {
  connection,
  concurrency: 1,
});

worker.on("completed", (job) => {
  console.log(`[worker] job ${job.id} completed`);
});

worker.on("failed", (job, err) => {
  console.error(`[worker] job ${job?.id} failed:`, err.message);
});

console.log(`[worker] listening on queue "${QUEUE_NAME}" via ${REDIS_URL}`);
