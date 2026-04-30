import { NextRequest, NextResponse } from "next/server";
import { validateStudentCredentials, signToken, COOKIE_NAME, TTL_SECONDS } from "@/lib/auth";

export async function POST(req: NextRequest) {
  try {
    const { login, senha } = await req.json();

    if (!login || !senha) {
      return NextResponse.json({ error: "Login e senha são obrigatórios." }, { status: 400 });
    }

    const user = await validateStudentCredentials(String(login), String(senha));

    if (!user) {
      return NextResponse.json({ error: "Login ou senha incorretos." }, { status: 401 });
    }

    const token = await signToken(user);
    const res = NextResponse.json({ ok: true, user });
    res.cookies.set(COOKIE_NAME, token, {
      httpOnly: true,
      secure: process.env.NODE_ENV === "production",
      sameSite: "lax",
      maxAge: TTL_SECONDS,
      path: "/"
    });
    return res;
  } catch (err) {
    console.error("[auth/aluno]", err);
    return NextResponse.json({ error: "Erro interno." }, { status: 500 });
  }
}
