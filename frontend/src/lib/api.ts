import { backendOrigin } from "@/lib/backend";
import { parseHealth } from "@/lib/health";
import type { HealthPayload } from "@/types/health";

/**
 * Browser calls same-origin `/api/health` (BFF proxy to the control plane).
 * Server code talks to BACKEND_URL directly. Neither value is a secret.
 */
export function healthRequestUrl(): string {
  if (typeof window === "undefined") {
    return `${backendOrigin()}/api/health`;
  }
  return "/api/health";
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

export async function fetchHealth(): Promise<HealthPayload> {
  let response: Response;
  try {
    response = await fetch(healthRequestUrl(), {
      cache: "no-store",
      headers: { accept: "application/json" },
    });
  } catch {
    throw new ApiError("Cannot reach the control plane");
  }
  if (!response.ok) {
    throw new ApiError("Health request failed", response.status);
  }
  const body: unknown = await response.json();
  return parseHealth(body);
}
