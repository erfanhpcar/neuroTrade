/**
 * Server-only control-plane origin. Never expose this via NEXT_PUBLIC_*.
 */
export function backendOrigin(): string {
  const raw = process.env.BACKEND_URL ?? "http://127.0.0.1:8000";
  return raw.replace(/\/$/, "");
}
