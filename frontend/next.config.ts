import type { NextConfig } from "next";

/**
 * Server-only control-plane origin. Browser traffic uses same-origin `/api/*`
 * rewrites so we do not need `NEXT_PUBLIC_*` backend URLs or CORS for Phase 0.
 */
function backendOrigin(): string {
  const raw = process.env.BACKEND_URL ?? "http://127.0.0.1:8000";
  return raw.replace(/\/$/, "");
}

const nextConfig: NextConfig = {
  reactStrictMode: true,
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: `${backendOrigin()}/api/:path*`,
      },
    ];
  },
};

export default nextConfig;
