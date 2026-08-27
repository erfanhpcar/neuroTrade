import { HealthMonitor } from "@/components/HealthMonitor";
import { ModeBadge } from "@/components/ModeBadge";
import { fetchHealth, fetchSystemStatus } from "@/lib/api";
import type { HealthResponse, SystemStatusResponse } from "@/types/system";

// Server component: fetch authoritative state from the control plane over REST.
export default async function DashboardPage() {
  let status: SystemStatusResponse | null = null;
  let health: HealthResponse | null = null;
  let loadError: string | null = null;

  try {
    [status, health] = await Promise.all([fetchSystemStatus(), fetchHealth()]);
  } catch {
    loadError = "The control plane is not reachable. Start the backend on port 8000.";
  }

  return (
    <main className="mx-auto max-w-4xl px-6 py-12">
      <header className="mb-8 flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">neuroTrade</h1>
          <p className="text-sm text-slate-400">
            Deterministic quant/systematic trading platform · Phase 0 skeleton
          </p>
        </div>
        {status ? <ModeBadge mode={status.trading_mode} /> : null}
      </header>

      {loadError ? (
        <p className="mb-8 rounded-xl border border-red-500/40 bg-red-500/10 px-4 py-3 text-sm text-red-300">
          {loadError}
        </p>
      ) : null}

      <div className="grid gap-6">
        <HealthMonitor initial={health} />

        {status ? (
          <section className="rounded-xl border border-slate-800 bg-slate-900/50 p-6">
            <h2 className="mb-4 text-lg font-semibold text-slate-100">System configuration</h2>
            <dl className="grid grid-cols-1 gap-3 sm:grid-cols-2">
              <Field label="Environment" value={status.app_env} />
              <Field label="Trading mode" value={status.trading_mode} />
              <Field label="Market data provider" value={status.market_data_provider} />
              <Field label="Default symbol" value={status.default_symbol} />
              <Field label="Default timeframe" value={status.default_timeframe} />
            </dl>
          </section>
        ) : null}
      </div>
    </main>
  );
}

function Field({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg bg-slate-950/60 px-4 py-3">
      <dt className="text-xs uppercase tracking-wide text-slate-500">{label}</dt>
      <dd className="mt-1 font-mono text-sm text-slate-200">{value}</dd>
    </div>
  );
}
