/** REST types aligned with docs/10_REST_API.md GET /api/health. */

export const TRADING_MODES = ["PAPER", "SEMI", "FULL", "HALTED"] as const;
export type TradingMode = (typeof TRADING_MODES)[number];

export type HealthPayload = {
  status: "ok";
  service: "control-plane";
  trading_mode: TradingMode;
  app_env: string;
};
