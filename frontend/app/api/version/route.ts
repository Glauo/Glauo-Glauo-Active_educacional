import { NextResponse } from "next/server";

export async function GET() {
  return NextResponse.json({
    app: "active-educacional",
    runtime: "node-next",
    sha: process.env.GIT_SHA || process.env.NEXT_PUBLIC_BUILD_SHA || "local",
    marker: "active-node-webhook-public-2026-06-01",
    time: new Date().toISOString(),
  });
}
