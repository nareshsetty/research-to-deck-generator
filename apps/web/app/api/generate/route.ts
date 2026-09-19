import { NextRequest, NextResponse } from "next/server";
import { getDeckQueue } from "@/lib/queue";

export async function POST(request: NextRequest) {
  let body: unknown;
  try {
    body = await request.json();
  } catch {
    return NextResponse.json({ error: "Request body must be valid JSON" }, { status: 400 });
  }

  const topic = (body as { topic?: unknown })?.topic;
  if (typeof topic !== "string" || !topic.trim()) {
    return NextResponse.json({ error: "'topic' is required and must be a non-empty string" }, { status: 400 });
  }

  const queue = getDeckQueue();
  const job = await queue.add("generate-deck", { topic: topic.trim() });

  return NextResponse.json({ jobId: job.id }, { status: 202 });
}
