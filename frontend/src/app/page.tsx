import { HealthPanel } from "@/components/HealthPanel";

export default function DashboardPage() {
  return (
    <main className="mx-auto max-w-3xl px-6 py-12">
      <header className="mb-8 space-y-2">
        <h1 className="text-3xl font-bold tracking-tight">neuroTrade</h1>
        <p className="text-sm text-slate-400">
          Deterministic quant/systematic trading platform. Phase 0 operator shell —
          observation only, no order or flatten controls.
        </p>
      </header>
      <HealthPanel />
    </main>
  );
}
