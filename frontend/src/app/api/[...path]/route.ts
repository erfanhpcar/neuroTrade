import { NextRequest, NextResponse } from "next/server";

import { backendOrigin } from "@/lib/backend";

export const dynamic = "force-dynamic";

/**
 * Same-origin BFF proxy. Reads BACKEND_URL at request time so Compose can
 * retarget the control plane without rebuilding Next.js rewrites.
 */
export async function GET(
  request: NextRequest,
  context: { params: Promise<{ path: string[] }> },
): Promise<NextResponse> {
  const { path } = await context.params;
  if (path.length === 0) {
    return NextResponse.json({ error: "not_found" }, { status: 404 });
  }

  const target = `${backendOrigin()}/api/${path.join("/")}${request.nextUrl.search}`;
  try {
    const upstream = await fetch(target, {
      cache: "no-store",
      headers: {
        accept: "application/json",
        "x-request-id": request.headers.get("x-request-id") ?? "",
      },
    });
    const body = await upstream.text();
    const response = new NextResponse(body, { status: upstream.status });
    const contentType = upstream.headers.get("content-type");
    if (contentType) {
      response.headers.set("content-type", contentType);
    }
    const requestId = upstream.headers.get("x-request-id");
    if (requestId) {
      response.headers.set("x-request-id", requestId);
    }
    return response;
  } catch {
    return NextResponse.json({ error: "control_plane_unreachable" }, { status: 502 });
  }
}
