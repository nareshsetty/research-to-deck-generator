"use client";

import { useEffect, useRef, useState } from "react";

type Status =
  | { status: "idle" }
  | { status: "waiting" | "active" | "delayed" }
  | { status: "completed"; downloadUrl: string; numSlides: number; numSources: number }
  | { status: "failed"; error: string };

const PROGRESS_STAGES = [
  "Pulling papers from OpenAlex",
  "Ranking the highest-signal findings",
  "Synthesizing and citing sources",
  "Laying out your branded slides",
];

function SpinnerIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" aria-hidden="true">
      <circle
        cx="12"
        cy="12"
        r="9"
        stroke="currentColor"
        strokeWidth="3"
        strokeOpacity="0.25"
      />
      <path
        d="M21 12a9 9 0 0 0-9-9"
        stroke="currentColor"
        strokeWidth="3"
        strokeLinecap="round"
        style={{ transformOrigin: "center", animation: "spin 0.8s linear infinite" }}
      />
    </svg>
  );
}

function CheckIcon() {
  return (
    <svg width="22" height="22" viewBox="0 0 24 24" fill="none" aria-hidden="true">
      <circle cx="12" cy="12" r="11" fill="var(--color-primary)" />
      <path
        d="M7 12.5l3 3 7-7"
        stroke="var(--color-card)"
        strokeWidth="2.2"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

function ErrorIcon() {
  return (
    <svg width="22" height="22" viewBox="0 0 24 24" fill="none" aria-hidden="true">
      <circle cx="12" cy="12" r="11" fill="var(--color-destructive)" />
      <path
        d="M12 7v6"
        stroke="var(--color-card)"
        strokeWidth="2.2"
        strokeLinecap="round"
      />
      <circle cx="12" cy="16.2" r="1.3" fill="var(--color-card)" />
    </svg>
  );
}

function DownloadIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" aria-hidden="true">
      <path
        d="M12 4v11m0 0-4-4m4 4 4-4M5 19h14"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

export default function Home() {
  const [topic, setTopic] = useState("");
  const [jobId, setJobId] = useState<string | null>(null);
  const [result, setResult] = useState<Status>({ status: "idle" });
  const [stageIndex, setStageIndex] = useState(0);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const stageRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const isProcessing =
    result.status === "waiting" || result.status === "active" || result.status === "delayed";

  function stopPolling() {
    if (pollRef.current) {
      clearInterval(pollRef.current);
      pollRef.current = null;
    }
  }

  useEffect(() => {
    if (!isProcessing) return;
    stageRef.current = setInterval(() => {
      setStageIndex((i) => Math.min(i + 1, PROGRESS_STAGES.length - 1));
    }, 3500);
    return () => {
      if (stageRef.current) {
        clearInterval(stageRef.current);
        stageRef.current = null;
      }
    };
  }, [isProcessing]);

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
    setStageIndex(0);
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

  const progressPercent = isProcessing
    ? Math.round(((stageIndex + 1) / PROGRESS_STAGES.length) * 100)
    : 0;

  return (
    <main
      style={{
        flex: 1,
        display: "flex",
        justifyContent: "center",
        padding: "var(--space-7) var(--space-3) var(--space-6)",
      }}
    >
      <div style={{ width: "100%", maxWidth: 640 }}>
        <div style={{ textAlign: "center", marginBottom: "var(--space-6)" }}>
          <span
            style={{
              display: "inline-flex",
              alignItems: "center",
              gap: "var(--space-1)",
              padding: "6px 14px",
              borderRadius: 999,
              background: "var(--color-muted)",
              color: "var(--color-primary)",
              fontSize: 13,
              fontWeight: 700,
              letterSpacing: 0.3,
              textTransform: "uppercase",
              marginBottom: "var(--space-4)",
            }}
          >
            Research → Slides, automatically
          </span>
          <h1
            style={{
              fontSize: "clamp(2rem, 4vw, 2.75rem)",
              fontWeight: 700,
              lineHeight: 1.15,
              marginBottom: "var(--space-3)",
            }}
          >
            Research-to-Deck Generator
          </h1>
          <p
            style={{
              color: "var(--color-muted-foreground)",
              fontSize: "1.0625rem",
              maxWidth: 520,
              marginInline: "auto",
            }}
          >
            Enter a research topic. We&apos;ll pull papers from OpenAlex, synthesize the
            highest-signal findings, and generate a cited, branded slide deck.
          </p>
        </div>

        <div
          style={{
            background: "var(--color-card)",
            color: "var(--color-card-foreground)",
            border: "1px solid var(--color-border)",
            borderRadius: "var(--radius-lg)",
            boxShadow: "var(--shadow-card)",
            padding: "var(--space-5)",
          }}
        >
          <form onSubmit={handleSubmit}>
            <label
              htmlFor="topic"
              style={{
                display: "block",
                fontSize: 14,
                fontWeight: 700,
                marginBottom: "var(--space-2)",
              }}
            >
              Research topic
            </label>
            <div style={{ display: "flex", gap: "var(--space-2)", flexWrap: "wrap" }}>
              <input
                id="topic"
                value={topic}
                onChange={(e) => setTopic(e.target.value)}
                placeholder="e.g. retrieval-augmented generation"
                disabled={isProcessing}
                style={{
                  flex: "1 1 260px",
                  padding: "12px 14px",
                  fontSize: "1rem",
                  color: "var(--color-card-foreground)",
                  background: "var(--color-background)",
                  border: "1.5px solid var(--color-border)",
                  borderRadius: "var(--radius-sm)",
                }}
              />
              <button
                type="submit"
                disabled={isProcessing || !topic.trim()}
                style={{
                  display: "inline-flex",
                  alignItems: "center",
                  justifyContent: "center",
                  gap: "var(--space-2)",
                  padding: "12px 22px",
                  fontSize: "1rem",
                  fontWeight: 700,
                  color: "#ffffff",
                  background: isProcessing ? "var(--color-muted-foreground)" : "var(--color-primary)",
                  border: "none",
                  borderRadius: "var(--radius-sm)",
                  opacity: !topic.trim() && !isProcessing ? 0.55 : 1,
                  transition: "background-color 200ms ease, transform 150ms ease",
                  minHeight: 44,
                }}
                onMouseDown={(e) => {
                  if (!isProcessing) e.currentTarget.style.transform = "scale(0.98)";
                }}
                onMouseUp={(e) => {
                  e.currentTarget.style.transform = "scale(1)";
                }}
              >
                {isProcessing ? (
                  <>
                    <SpinnerIcon /> Generating&hellip;
                  </>
                ) : (
                  "Generate deck"
                )}
              </button>
            </div>
            <p style={{ fontSize: 13, color: "var(--color-muted-foreground)", marginTop: "var(--space-2)" }}>
              Typically takes 1–3 minutes depending on how much literature exists.
            </p>
          </form>

          {result.status !== "idle" && (
            <div
              role="status"
              aria-live="polite"
              style={{
                marginTop: "var(--space-5)",
                paddingTop: "var(--space-4)",
                borderTop: "1px solid var(--color-border)",
                animation: "fade-in-up 250ms ease",
              }}
            >
              {isProcessing && (
                <div>
                  <div
                    style={{
                      display: "flex",
                      justifyContent: "space-between",
                      alignItems: "center",
                      marginBottom: "var(--space-2)",
                    }}
                  >
                    <span style={{ fontSize: 14, fontWeight: 700 }}>
                      {PROGRESS_STAGES[stageIndex]}
                    </span>
                    {jobId && (
                      <span style={{ fontSize: 12, color: "var(--color-muted-foreground)" }}>
                        Job {jobId.slice(0, 8)}
                      </span>
                    )}
                  </div>
                  <div
                    aria-busy="true"
                    style={{
                      height: 8,
                      borderRadius: 999,
                      background: "var(--color-muted)",
                      overflow: "hidden",
                    }}
                  >
                    <div
                      style={{
                        height: "100%",
                        width: `${progressPercent}%`,
                        background: "var(--color-primary)",
                        borderRadius: 999,
                        transition: "width 600ms ease",
                      }}
                    />
                  </div>
                </div>
              )}

              {result.status === "completed" && (
                <div style={{ display: "flex", alignItems: "flex-start", gap: "var(--space-3)" }}>
                  <CheckIcon />
                  <div style={{ flex: 1 }}>
                    <p style={{ fontWeight: 700, marginBottom: 2 }}>Your deck is ready</p>
                    <p style={{ fontSize: 14, color: "var(--color-muted-foreground)", marginBottom: "var(--space-3)" }}>
                      {result.numSlides} slides synthesized from {result.numSources} sources.
                    </p>
                    <a
                      href={result.downloadUrl}
                      target="_blank"
                      rel="noopener noreferrer"
                      style={{
                        display: "inline-flex",
                        alignItems: "center",
                        gap: "var(--space-2)",
                        padding: "10px 18px",
                        fontSize: 14,
                        fontWeight: 700,
                        color: "#ffffff",
                        background: "var(--color-accent)",
                        borderRadius: "var(--radius-sm)",
                        minHeight: 44,
                      }}
                    >
                      <DownloadIcon /> Download PPTX
                    </a>
                  </div>
                </div>
              )}

              {result.status === "failed" && (
                <div style={{ display: "flex", alignItems: "flex-start", gap: "var(--space-3)" }}>
                  <ErrorIcon />
                  <div>
                    <p style={{ fontWeight: 700, marginBottom: 2 }}>Generation failed</p>
                    <p style={{ fontSize: 14, color: "var(--color-muted-foreground)" }}>{result.error}</p>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </main>
  );
}
