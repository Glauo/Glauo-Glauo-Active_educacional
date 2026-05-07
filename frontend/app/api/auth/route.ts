import { NextRequest, NextResponse } from "next/server";
import { validateCredentials, signToken, COOKIE_NAME, TTL_SECONDS, dashboardForPerfil } from "@/lib/auth";

export async function POST(req: NextRequest) {
  try {
    const { usuario, senha, unit } = await req.json();

    if (!usuario || !senha) {
      return NextResponse.json({ error: "Usuário e senha são obrigatórios." }, { status: 400 });
    }

    const user = await validateCredentials(String(usuario), String(senha), String(unit || "Matriz"));

    if (!user) {
      return NextResponse.json({ error: "Usuário ou senha incorretos." }, { status: 401 });
    }

    const token = await signToken(user);

    const redirectTo = String(user.unit || "").toLowerCase().includes("condojob")
      ? "/condojob"
      : dashboardForPerfil(user.perfil);
    const res = NextResponse.json({ ok: true, user, redirectTo });
    res.cookies.set(COOKIE_NAME, token, {
      httpOnly: true,
      secure: process.env.NODE_ENV === "production",
      sameSite: "lax",
      maxAge: TTL_SECONDS,
      path: "/"
    });
    return res;
  } catch (err) {
    console.error("[auth]", err);
    return NextResponse.json({ error: "Erro interno." }, { status: 500 });
  }
}

export async function DELETE() {
  const res = NextResponse.json({ ok: true });
  res.cookies.delete(COOKIE_NAME);
  return res;
}
