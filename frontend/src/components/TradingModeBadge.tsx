import { presentTradingMode } from "@/lib/health";
import type { TradingMode } from "@/types/health";

const TONE_CLASS: Record<ReturnType<typeof presentTradingMode>["tone"], string> = {
  safe: "border-emerald-600 bg-emerald-950 text-emerald-100",
  caution: "border-amber-600 bg-amber-950 text-amber-100",
  danger: "border-red-600 bg-red-950 text-red-100",
  halted: "border-slate-500 bg-slate-900 text-slate-100",
};

export function TradingModeBadge({ mode }: { mode: TradingMode }) {
  const view = presentTradingMode(mode);
  return (
    <div
      className={`max-w-md rounded-lg border px-4 py-3 ${TONE_CLASS[view.tone]}`}
      role="status"
      aria-label={`Trading mode ${view.label}`}
    >
      <p className="text-xs font-semibold uppercase tracking-wide">Trading mode</p>
      <p className="mt-1 font-mono text-2xl font-bold">{view.label}</p>
      <p className="mt-1 text-sm">{view.detail}</p>
    </div>
  );
}
