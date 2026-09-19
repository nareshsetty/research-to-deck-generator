import { NextRequest, NextResponse } from "next/server";
import { getDeckQueue } from "@/lib/queue";

export async function GET(
  _request: NextRequest,
  { params }: { params: Promise<{ jobId: string }> }
) {
  const { jobId } = await params;
  const queue = getDeckQueue();
  const job = await queue.getJob(jobId);

  if (!job) {
    return NextResponse.json({ error: "Job not found" }, { status: 404 });
  }

  const state = await job.getState();

  if (state === "completed") {
    return NextResponse.json({
      status: "completed",
      downloadUrl: job.returnvalue?.downloadUrl,
      numSlides: job.returnvalue?.numSlides,
      numSources: job.returnvalue?.numSources,
    });
  }

  if (state === "failed") {
    return NextResponse.json({ status: "failed", error: job.failedReason }, { status: 200 });
  }

  return NextResponse.json({ status: state });
}
