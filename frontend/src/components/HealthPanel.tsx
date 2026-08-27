"use client";

import { useEffect, useState } from "react";

import { TradingModeBadge } from "@/components/TradingModeBadge";
import { ApiError, fetchHealth } from "@/lib/api";
import { isStale, POLL_INTERVAL_MS } from "@/lib/health";
import type { HealthPayload } from "@/types/health";

type PanelState = {
  health: HealthPayload | null;
  error: string | null;
  fetchedAtMs: number | null;
  nowMs: number;
};

const INITIAL: PanelState = {
  health: null,
  error: null,
  fetchedAtMs: null,
  nowMs: Date.now(),
};

export function HealthPanel() {
  const [state, setState] = useState<PanelState>(INITIAL);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      try {
        const health = await fetchHealth();
        if (cancelled) {
          return;
        }
        setState({
          health,
          error: null,
          fetchedAtMs: Date.now(),
          nowMs: Date.now(),
        });
      } catch (error) {
        if (cancelled) {
          return;
        }
        const message =
          error instanceof ApiError ? error.message : "Health payload could not be read";
        setState((previous) => ({
          ...previous,
          error: message,
          nowMs: Date.now(),
        }));
      }
    }

    void load();
    const poll = window.setInterval(() => {
      void load();
    }, POLL_INTERVAL_MS);
    const tick = window.setInterval(() => {
      setState((previous) => ({ ...previous, nowMs: Date.now() }));
    }, 1_000);

    return () => {
      cancelled = true;
      window.clearInterval(poll);
      window.clearInterval(tick);
    };
  }, []);

  const stale =
    state.fetchedAtMs !== null ? isStale(state.fetchedAtMs, state.nowMs) : false;
  const loading = state.health === null && state.error === null;

  return (
    <section className="space-y-4 rounded-xl border border-slate-800 bg-slate-900/60 p-6">
      <h2 className="text-lg font-semibold text-slate-100">Control plane</h2>

      {loading ? (
        <p className="text-sm text-slate-300">Loading control-plane health…</p>
      ) : null}

      {state.error ? (
        <p
          className="rounded-md border border-red-500/40 bg-red-950/40 px-3 py-2 text-sm text-red-200"
          role="alert"
        >
          {state.error}. Start the backend with `make backend-run` if it is not running.
        </p>
      ) : null}

      {stale ? (
        <p
          className="rounded-md border border-amber-500/40 bg-amber-950/40 px-3 py-2 text-sm text-amber-100"
          role="status"
        >
          Health data is stale. Last successful fetch is older than 15 seconds. Do not treat
          this view as current trading state.
        </p>
      ) : null}

      {state.health ? (
        <>
          <TradingModeBadge mode={state.health.trading_mode} />
          <dl className="grid grid-cols-1 gap-3 sm:grid-cols-2">
            <Field label="Liveness" value={state.health.status} />
            <Field label="Service" value={state.health.service} />
            <Field label="App environment" value={state.health.app_env} />
            <Field
              label="Last successful fetch"
              value={
                state.fetchedAtMs
                  ? new Date(state.fetchedAtMs).toISOString()
                  : "never"
              }
            />
          </dl>
          <p className="text-xs text-slate-400">
            This is control-plane liveness only. PostgreSQL, Redis, and worker heartbeat
            are not probed yet.
          </p>
        </>
      ) : null}
    </section>
  );
}

function Field({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg bg-slate-950/70 px-4 py-3">
      <dt className="text-xs uppercase tracking-wide text-slate-500">{label}</dt>
      <dd className="mt-1 font-mono text-sm text-slate-200">{value}</dd>
    </div>
  );
}
