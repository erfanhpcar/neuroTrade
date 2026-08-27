"use client";

import { useCallback, useEffect, useState } from "react";

import { ApiError, fetchHealth } from "@/lib/api";
import { StatusPill } from "@/components/StatusPill";
import type { HealthResponse } from "@/types/system";

const POLL_INTERVAL_MS = 5000;
const STALE_AFTER_MS = 15000;

interface Props {
  initial: HealthResponse | null;
}

// Client-side liveness poller. The dashboard treats the control plane as the
// source of truth and re-fetches over REST; if polling fails or data goes stale
// it says so visibly rather than presenting stale state as healthy.
export function HealthMonitor({ initial }: Props) {
  const [health, setHealth] = useState<HealthResponse | null>(initial);
  const [error, setError] = useState<string | null>(null);
  const [updatedAt, setUpdatedAt] = useState<number | null>(initial ? Date.now() : null);
  const [now, setNow] = useState<number>(Date.now());

  const poll = useCallback(async () => {
    try {
      const next = await fetchHealth();
      setHealth(next);
      setUpdatedAt(Date.now());
      setError(null);
    } catch (cause) {
      setError(cause instanceof ApiError ? cause.message : "Unknown error");
    }
  }, []);

  useEffect(() => {
    void poll();
    const pollTimer = setInterval(() => void poll(), POLL_INTERVAL_MS);
    const clockTimer = setInterval(() => setNow(Date.now()), 1000);
    return () => {
      clearInterval(pollTimer);
      clearInterval(clockTimer);
    };
  }, [poll]);

  const isStale = updatedAt !== null && now - updatedAt > STALE_AFTER_MS;
  const secondsAgo = updatedAt !== null ? Math.floor((now - updatedAt) / 1000) : null;

  return (
    <section className="rounded-xl border border-slate-800 bg-slate-900/50 p-6">
      <div className="mb-4 flex items-center justify-between">
        <h2 className="text-lg font-semibold text-slate-100">Control plane health</h2>
        <span className="text-xs text-slate-400">
          {secondsAgo === null ? "never" : `updated ${secondsAgo}s ago`}
        </span>
      </div>

      {error ? (
        <p className="rounded-md bg-red-500/10 px-3 py-2 text-sm text-red-300">
          Cannot reach control plane — {error}
        </p>
      ) : null}

      {isStale ? (
        <p className="mb-3 rounded-md bg-amber-500/10 px-3 py-2 text-sm text-amber-300">
          ⚠ Data is stale (no successful update in {STALE_AFTER_MS / 1000}s).
        </p>
      ) : null}

      {health ? (
        <div className="flex flex-wrap items-center gap-3">
          <span
            className={`inline-flex items-center gap-2 rounded-md px-2.5 py-1 text-sm ${
              health.status === "ok"
                ? "bg-emerald-500/15 text-emerald-300 ring-1 ring-emerald-500/40"
                : "bg-amber-500/15 text-amber-300 ring-1 ring-amber-500/40"
            }`}
          >
            <span aria-hidden>{health.status === "ok" ? "✓" : "⚠"}</span>
            status: {health.status}
          </span>
          <StatusPill ok={health.dependencies.postgres} label="PostgreSQL" />
          <StatusPill ok={health.dependencies.redis} label="Redis" />
        </div>
      ) : (
        <p className="text-sm text-slate-400">Loading…</p>
      )}
    </section>
  );
}
