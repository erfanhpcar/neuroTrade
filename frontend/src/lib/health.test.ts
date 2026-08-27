import { describe, expect, it } from "vitest";

import {
  isStale,
  parseHealth,
  presentTradingMode,
  STALE_AFTER_MS,
} from "@/lib/health";

const valid = {
  status: "ok",
  service: "control-plane",
  trading_mode: "PAPER",
  app_env: "development",
};

describe("parseHealth", () => {
  it("accepts the Phase 0 liveness contract", () => {
    expect(parseHealth(valid)).toEqual(valid);
  });

  it("ignores extra fields", () => {
    expect(parseHealth({ ...valid, dependencies: { postgres: true } })).toEqual(valid);
  });

  it("rejects a missing trading_mode", () => {
    expect(() =>
      parseHealth({
        status: valid.status,
        service: valid.service,
        app_env: valid.app_env,
      }),
    ).toThrow(/trading_mode/);
  });

  it("rejects an unknown trading_mode instead of defaulting to PAPER", () => {
    expect(() => parseHealth({ ...valid, trading_mode: "LIVE" })).toThrow(/trading_mode/);
  });

  it("rejects a non-ok status", () => {
    expect(() => parseHealth({ ...valid, status: "degraded" })).toThrow(/status/);
  });

  it("rejects a non-object payload", () => {
    expect(() => parseHealth(null)).toThrow(/not an object/);
    expect(() => parseHealth("ok")).toThrow(/not an object/);
  });
});

describe("presentTradingMode", () => {
  it("labels PAPER as the safe default with text, not color alone", () => {
    const view = presentTradingMode("PAPER");
    expect(view.label).toBe("PAPER");
    expect(view.detail.toLowerCase()).toContain("no live orders");
    expect(view.tone).toBe("safe");
  });

  it("never treats FULL as the safe default", () => {
    const view = presentTradingMode("FULL");
    expect(view.tone).toBe("danger");
    expect(view.detail).toMatch(/Phase 10/i);
  });

  it("keeps HALT distinct from closing positions", () => {
    const view = presentTradingMode("HALTED");
    expect(view.detail.toLowerCase()).toContain("new orders are blocked");
    expect(view.detail.toLowerCase()).toContain("not closed");
  });
});

describe("isStale", () => {
  it("marks snapshots older than the stale window", () => {
    expect(isStale(0, STALE_AFTER_MS)).toBe(false);
    expect(isStale(0, STALE_AFTER_MS + 1)).toBe(true);
  });
});
