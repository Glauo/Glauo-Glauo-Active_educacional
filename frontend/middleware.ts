import { NextRequest, NextResponse } from "next/server";
import { jwtVerify } from "jose";

import { jwtSecret } from "./lib/jwt-config";

const PUBLIC_PATHS = ["/login", "/aluno/login", "/limpar-cache", "/api/auth", "/api/version", "/api/financeiro/mercado-pago/webhook", "/api/financeiro/cron-pagamentos", "/api/backup/auto", "/api/financeiro/dedupe"];
const PUBLIC_FILES = ["/logo.png", "/manifest.json", "/sw.js", "/limpar-cache.html"];

export async function middleware(req: NextRequest) {
  const { pathname } = req.nextUrl;

  // Libera caminhos públicos e assets
  if (
    PUBLIC_PATHS.some((p) => pathname.startsWith(p)) ||
    PUBLIC_FILES.includes(pathname) ||
    pathname.startsWith("/uploads/") ||
    pathname.startsWith("/_next") ||
    pathname.startsWith("/favicon") ||
    pathname.startsWith("/icons/")
  ) {
    return NextResponse.next();
  }

  const token = req.cookies.get("ae_session")?.value;

  if (!token) {
    const loginUrl = new URL("/login", req.url);
    loginUrl.searchParams.set("next", pathname);
    return NextResponse.redirect(loginUrl);
  }

  try {
    const { payload } = await jwtVerify(token, jwtSecret());
    if (payload.must_change_password && pathname !== "/alterar-senha") {
      if (pathname.startsWith("/api/")) return NextResponse.json({ error: "Altere sua senha para continuar." }, { status: 403 });
      return NextResponse.redirect(new URL("/alterar-senha", req.url));
    }
    return NextResponse.next();
  } catch {
    const loginUrl = new URL("/login", req.url);
    return NextResponse.redirect(loginUrl);
  }
}

export const config = {
  matcher: ["/((?!api/version.*|api/backup/auto.*|api/financeiro/dedupe.*|api/financeiro/mercado-pago/webhook.*|api/financeiro/cron-pagamentos.*|_next/static|_next/image|favicon.ico|logo.png|manifest.json|sw.js|limpar-cache.html|icons/|uploads/).*)"]
};
