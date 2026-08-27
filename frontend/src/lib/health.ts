import { TRADING_MODES, type HealthPayload, type TradingMode } from "@/types/health";

export const POLL_INTERVAL_MS = 5_000;
export const STALE_AFTER_MS = 15_000;

export class HealthParseError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "HealthParseError";
  }
}

export function isTradingMode(value: unknown): value is TradingMode {
  return typeof value === "string" && (TRADING_MODES as readonly string[]).includes(value);
}

/**
 * Narrow a JSON value to the Phase 0 health contract.
 * Extra fields are ignored. Missing/invalid fields fail closed.
 */
export function parseHealth(data: unknown): HealthPayload {
  if (typeof data !== "object" || data === null || Array.isArray(data)) {
    throw new HealthParseError("health payload is not an object");
  }
  const rec = data as Record<string, unknown>;
  if (rec.status !== "ok") {
    throw new HealthParseError("health status is not ok");
  }
  if (rec.service !== "control-plane") {
    throw new HealthParseError("unexpected health service");
  }
  if (!isTradingMode(rec.trading_mode)) {
    throw new HealthParseError("invalid trading_mode");
  }
  if (typeof rec.app_env !== "string" || rec.app_env.trim() === "") {
    throw new HealthParseError("invalid app_env");
  }
  return {
    status: "ok",
    service: "control-plane",
    trading_mode: rec.trading_mode,
    app_env: rec.app_env,
  };
}

export function isStale(fetchedAtMs: number, nowMs: number): boolean {
  return nowMs - fetchedAtMs > STALE_AFTER_MS;
}

export type ModePresentation = {
  mode: TradingMode;
  label: string;
  detail: string;
  tone: "safe" | "caution" | "danger" | "halted";
};

/**
 * Text-first mode copy. Color is a secondary cue only.
 * FULL is never presented as the safe default.
 */
export function presentTradingMode(mode: TradingMode): ModePresentation {
  switch (mode) {
    case "PAPER":
      return {
        mode,
        label: "PAPER",
        detail: "Safe default. No live orders are sent.",
        tone: "safe",
      };
    case "SEMI":
      return {
        mode,
        label: "SEMI",
        detail: "Operator approval is required before execution.",
        tone: "caution",
      };
    case "FULL":
      return {
        mode,
        label: "FULL",
        detail: "Unexpected live mode. FULL is disabled until Phase 10 live readiness.",
        tone: "danger",
      };
    case "HALTED":
      return {
        mode,
        label: "HALTED",
        detail: "New orders are blocked. Existing positions are not closed by this state.",
        tone: "halted",
      };
  }
}
