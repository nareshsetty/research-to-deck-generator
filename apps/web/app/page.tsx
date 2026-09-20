"use client";

import { useState, useRef } from "react";

type Status =
  | { status: "idle" }
  | { status: "waiting" | "active" | "delayed" }
  | { status: "completed"; downloadUrl: string; numSlides: number; numSources: number }
  | { status: "failed"; error: string };

export default function Home() {
  const [topic, setTopic] = useState("");
  const [jobId, setJobId] = useState<string | null>(null);
  const [result, setResult] = useState<Status>({ status: "idle" });
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  function stopPolling() {
    if (pollRef.current) {
      clearInterval(pollRef.current);
      pollRef.current = null;
    }
  }

  async function poll(id: string) {
    const res = await fetch(`/api/status/${id}`);
    const data = await res.json();
    setResult(data);
    if (data.status === "completed" || data.status === "failed") {
      stopPolling();
    }
  }

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    if (!topic.trim()) return;

    stopPolling();
    setResult({ status: "waiting" });

    const res = await fetch("/api/generate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ topic }),
    });

    if (!res.ok) {
      const data = await res.json().catch(() => ({}));
      setResult({ status: "failed", error: data.error || "Request failed" });
      return;
    }

    const data = await res.json();
    setJobId(data.jobId);
    pollRef.current = setInterval(() => poll(data.jobId), 3000);
  }

  return (
    <main style={{ maxWidth: 640, margin: "4rem auto", fontFamily: "system-ui, sans-serif", padding: "0 1rem" }}>
      <h1>Research-to-Deck Generator</h1>
      <p style={{ color: "#555" }}>
        Enter a research topic. We&apos;ll pull papers from OpenAlex, synthesize the
        highest-signal findings, and generate a cited, branded slide deck.
      </p>

      <form onSubmit={handleSubmit} style={{ display: "flex", gap: "0.5rem", marginTop: "1.5rem" }}>
        <input
          value={topic}
          onChange={(e) => setTopic(e.target.value)}
          placeholder="e.g. retrieval-augmented generation"
          style={{ flex: 1, padding: "0.5rem 0.75rem", fontSize: "1rem" }}
        />
        <button type="submit" style={{ padding: "0.5rem 1rem", fontSize: "1rem" }}>
          Generate
        </button>
      </form>

      {jobId && (
        <div style={{ marginTop: "1.5rem" }}>
          <p>
            Job <code>{jobId}</code>
          </p>
          {result.status === "waiting" || result.status === "active" || result.status === "delayed" ? (
            <p>Working on it&hellip; (ingesting papers, retrieving findings, synthesizing slides)</p>
          ) : null}
          {result.status === "completed" && (
            <p>
              ✅ Deck ready — {result.numSlides} slides from {result.numSources} sources.{" "}
              <a href={result.downloadUrl} target="_blank" rel="noopener noreferrer">
                Download PPTX
              </a>
            </p>
          )}
          {result.status === "failed" && <p style={{ color: "crimson" }}>❌ {result.error}</p>}
        </div>
      )}
    </main>
  );
}
