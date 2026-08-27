// Shared REST types. Keep aligned with `docs/10_REST_API.md` and the backend
// response models in `backend/app/api/system.py`.

export const TRADING_MODES = ["PAPER", "SEMI", "FULL", "HALTED"] as const;
export type TradingMode = (typeof TRADING_MODES)[number];

export interface DependencyHealth {
  postgres: boolean;
  redis: boolean;
}

export interface HealthResponse {
  status: "ok" | "degraded";
  trading_mode: TradingMode;
  dependencies: DependencyHealth;
}

export interface SystemStatusResponse {
  trading_mode: TradingMode;
  app_env: string;
  market_data_provider: string;
  default_symbol: string;
  default_timeframe: string;
}
