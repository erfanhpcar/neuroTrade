// Small accessible status indicator. Never encodes state by color only: it always
// includes an icon and text label.
export function StatusPill({ ok, label }: { ok: boolean; label: string }) {
  return (
    <span
      className={`inline-flex items-center gap-2 rounded-md px-2.5 py-1 text-sm ${
        ok
          ? "bg-emerald-500/15 text-emerald-300 ring-1 ring-emerald-500/40"
          : "bg-red-500/15 text-red-300 ring-1 ring-red-500/40"
      }`}
    >
      <span aria-hidden>{ok ? "✓" : "✕"}</span>
      <span>
        {label}: {ok ? "up" : "down"}
      </span>
    </span>
  );
}
