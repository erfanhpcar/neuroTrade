import type { TradingMode } from "@/types/system";

// Trading mode must never be visually ambiguous (see frontend/AGENTS.md). Status
// is conveyed with an explicit label and icon, not color alone.
const MODE_STYLES: Record<TradingMode, { className: string; icon: string; label: string }> = {
  PAPER: {
    className: "bg-sky-500/15 text-sky-300 ring-1 ring-sky-500/40",
    icon: "◦",
    label: "PAPER — simulated, no real orders",
  },
  SEMI: {
    className: "bg-amber-500/15 text-amber-300 ring-1 ring-amber-500/40",
    icon: "◐",
    label: "SEMI — operator approval required",
  },
  FULL: {
    className: "bg-red-500/20 text-red-300 ring-1 ring-red-500/50",
    icon: "●",
    label: "FULL — live execution",
  },
  HALTED: {
    className: "bg-slate-500/20 text-slate-300 ring-1 ring-slate-500/50",
    icon: "■",
    label: "HALTED — new exposure blocked",
  },
};

export function ModeBadge({ mode }: { mode: TradingMode }) {
  const style = MODE_STYLES[mode];
  return (
    <span
      className={`inline-flex items-center gap-2 rounded-full px-3 py-1 text-sm font-semibold ${style.className}`}
      title={style.label}
    >
      <span aria-hidden>{style.icon}</span>
      {mode}
    </span>
  );
}
