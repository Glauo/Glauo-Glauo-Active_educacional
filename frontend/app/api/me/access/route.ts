import { NextResponse } from "next/server";
import { getSession } from "@/lib/auth";
import { ACCESS_MODULES, canAccessPath, getAccessForSession } from "@/lib/access-control";

export async function GET() {
  const session = await getSession();
  if (!session) return NextResponse.json({ error: "Nao autorizado." }, { status: 401 });

  const { blockedRoutes } = await getAccessForSession(session);
  return NextResponse.json({
    blockedRoutes,
    modules: ACCESS_MODULES.map((module) => ({
      ...module,
      allowed: canAccessPath(session.perfil, module.path, blockedRoutes),
    })),
  });
}
