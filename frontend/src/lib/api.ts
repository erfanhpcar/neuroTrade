// Centralized API access layer. Components must not issue raw fetch calls; they
// call these helpers so error handling and base-URL resolution stay in one place.

import type { HealthResponse, SystemStatusResponse } from "@/types/system";

/**
 * Base URL for the FastAPI control plane.
 *
 * On the server (SSR) we talk to the backend directly via `BACKEND_URL`. In the
 * browser we use `NEXT_PUBLIC_BACKEND_URL`. Never put secrets in either value.
 */
function backendBaseUrl(): string {
  if (typeof window === "undefined") {
    return process.env.BACKEND_URL ?? "http://localhost:8000";
  }
  return process.env.NEXT_PUBLIC_BACKEND_URL ?? "http://localhost:8000";
}

export class ApiError extends Error {
  constructor(
    message: string,
    readonly status?: number,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

async function getJson<T>(path: string): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${backendBaseUrl()}${path}`, {
      cache: "no-store",
      headers: { accept: "application/json" },
    });
  } catch {
    throw new ApiError(`Cannot reach control plane at ${path}`);
  }
  if (!response.ok) {
    throw new ApiError(`Request to ${path} failed`, response.status);
  }
  return (await response.json()) as T;
}

export function fetchHealth(): Promise<HealthResponse> {
  return getJson<HealthResponse>("/api/health");
}

export function fetchSystemStatus(): Promise<SystemStatusResponse> {
  return getJson<SystemStatusResponse>("/api/system/status");
}
