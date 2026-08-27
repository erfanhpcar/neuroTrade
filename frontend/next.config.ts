import type { NextConfig } from "next";

/**
 * Server-only control-plane origin lives in `BACKEND_URL`. Browser traffic uses
 * the same-origin `/api/[...path]` BFF route so we do not need `NEXT_PUBLIC_*`
 * backend URLs or CORS for Phase 0. The proxy reads BACKEND_URL at request time.
 */
const nextConfig: NextConfig = {
  reactStrictMode: true,
};

export default nextConfig;
