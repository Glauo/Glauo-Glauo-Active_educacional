import { NextRequest, NextResponse } from "next/server";
import { validateCredentials, signToken, COOKIE_NAME, TTL_SECONDS, dashboardForPerfil } from "@/lib/auth";
import { dbUpdate } from "@/lib/db";

function text(value: unknown) {
  return String(value || "").trim();
}

function lower(value: unknown) {
  return text(value).toLowerCase();
}

export async function POST(req: NextRequest) {
  try {
    const { usuario, senha, unit } = await req.json();

    if (!usuario || !senha) {
      return NextResponse.json({ error: "Usuario e senha sao obrigatorios." }, { status: 400 });
    }

    const user = await validateCredentials(String(usuario), String(senha), String(unit || "Matriz"));
    if (!user) {
      return NextResponse.json({ error: "Usuario ou senha incorretos." }, { status: 401 });
    }

    // Updating last-login is audit metadata, not part of credential validation.
    // A transient write failure must not reject an otherwise valid sign-in.
    try {
      await dbUpdate<Record<string, unknown>[]>("users.json", rows =>
        (rows || []).map(item => lower(item.usuario) === lower(user.usuario) &&
          (user.record_id ? String(item.id ?? "") === String(user.record_id) : text(item.pessoa || item.nome) === user.pessoa)
          ? { ...item, last_login_at: new Date().toISOString() } : item), []);
    } catch (err) {
      console.error("[auth] Nao foi possivel atualizar o ultimo acesso; login validado sera mantido.", err);
    }

    const token = await signToken(user);
    const isAdmin = String(user.perfil || "").toLowerCase().includes("admin");
    const redirectTo = user.must_change_password
      ? "/alterar-senha"
      : (!isAdmin && String(user.unit || "").toLowerCase().includes("condojob")
        ? "/condojob"
        : dashboardForPerfil(user.perfil));

    const res = NextResponse.json({ ok: true, user, redirectTo });
    res.cookies.set(COOKIE_NAME, token, {
      httpOnly: true,
      secure: process.env.NODE_ENV === "production",
      sameSite: "lax",
      maxAge: TTL_SECONDS,
      path: "/",
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
