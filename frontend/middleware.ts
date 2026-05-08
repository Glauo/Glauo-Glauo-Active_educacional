import { NextRequest, NextResponse } from "next/server";
import { jwtVerify } from "jose";

const SECRET = new TextEncoder().encode(
  process.env.JWT_SECRET || "active-educacional-secret-2026-change-in-production"
);

const PUBLIC_PATHS = ["/login", "/aluno/login", "/limpar-cache", "/api/auth"];
const PUBLIC_FILES = ["/logo.png", "/manifest.json", "/sw.js"];

export async function middleware(req: NextRequest) {
  const { pathname } = req.nextUrl;

  // Libera caminhos públicos e assets
  if (
    PUBLIC_PATHS.some((p) => pathname.startsWith(p)) ||
    PUBLIC_FILES.includes(pathname) ||
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
    await jwtVerify(token, SECRET);
    return NextResponse.next();
  } catch {
    const loginUrl = new URL("/login", req.url);
    return NextResponse.redirect(loginUrl);
  }
}

export const config = {
  matcher: ["/((?!_next/static|_next/image|favicon.ico|logo.png|manifest.json|sw.js|icons/).*)"]
};
