import { NextRequest, NextResponse } from "next/server";
import { validateStudentCredentials, signToken, COOKIE_NAME, TTL_SECONDS, dashboardForPerfil } from "@/lib/auth";
import { dbUpdate } from "@/lib/db";

function text(value: unknown) {
  return String(value || "").trim();
}

function lower(value: unknown) {
  return text(value).toLowerCase();
}

export async function POST(req: NextRequest) {
  try {
    const { login, senha } = await req.json();

    if (!login || !senha) {
      return NextResponse.json({ error: "Login e senha sao obrigatorios." }, { status: 400 });
    }

    const user = await validateStudentCredentials(String(login), String(senha));
    if (!user) {
      return NextResponse.json({ error: "Login ou senha incorretos." }, { status: 401 });
    }

    await dbUpdate<Record<string, unknown>[]>("students.json", rows =>
      (rows || []).map(item => lower(item.login || item.usuario) === lower(user.usuario) &&
        (user.record_id ? String(item.id) === user.record_id : text(item.nome || item.name) === user.pessoa)
        ? { ...item, last_login_at: new Date().toISOString() } : item), []);

    const token = await signToken(user);
    const res = NextResponse.json({ ok: true, user, redirectTo: (user.must_change_password ? "/alterar-senha" : dashboardForPerfil(user.perfil)) });
    res.cookies.set(COOKIE_NAME, token, {
      httpOnly: true,
      secure: process.env.NODE_ENV === "production",
      sameSite: "lax",
      maxAge: TTL_SECONDS,
      path: "/",
    });
    return res;
  } catch (err) {
    console.error("[auth/aluno]", err);
    return NextResponse.json({ error: "Erro interno." }, { status: 500 });
  }
}
