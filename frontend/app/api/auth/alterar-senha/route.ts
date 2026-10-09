import { NextRequest, NextResponse } from "next/server";
import { getSession, signToken, COOKIE_NAME, TTL_SECONDS, dashboardForPerfil } from "@/lib/auth";
import { dbTransaction } from "@/lib/db";
import { hashPassword, verifyPassword } from "@/lib/passwords";

export async function POST(req: NextRequest) {
  const session = await getSession(true);
  if (!session) return NextResponse.json({ error: "Entre novamente para alterar sua senha." }, { status: 401 });
  const body = await req.json().catch(() => ({}));
  const password = String(body.nova_senha || "");
  if (password.length < 8 || password.length > 128 || !/[A-Z]/.test(password) || !/[a-z]/.test(password) || !/\d/.test(password)) {
    return NextResponse.json({ error: "Use de 8 a 128 caracteres, com maiuscula, minuscula e numero." }, { status: 400 });
  }
  const key = session.perfil.toLowerCase().includes("aluno") ? "students" : "users";
  const hash = await hashPassword(password);
  try {
    const resetAt = await dbTransaction([key, "teachers", "users_audit"], async values => {
      const rows = (values[key] || []) as Record<string, unknown>[];
      const candidates = rows.filter(item => String(item.usuario || item.login || "").toLowerCase() === session.usuario.toLowerCase() &&
        (!session.record_id || String(item.id || "") === session.record_id));
      const row = candidates.length === 1 ? candidates[0] : undefined;
      if (!row || row.is_active === false || row.deleted_at || String(row.password_reset_at || "") !== String(session.password_reset_at || "") ||
          !(await verifyPassword(String(body.senha_atual || ""), row.senha))) throw new Error("credentials");
      const now = new Date().toISOString();
      Object.assign(row, { senha: hash, must_change_password: false, password_reset_at: now, password_changed_at: now });
      if (key === "users" && row.professor_id) {
        for (const teacher of (values.teachers || []) as Record<string, unknown>[]) {
          if (String(teacher.id || teacher.nome) === String(row.professor_id)) Object.assign(teacher, { senha: hash, must_change_password: false, password_reset_at: now });
        }
      }
      const logs = (values.users_audit || []) as Record<string, unknown>[];
      logs.push({ id: crypto.randomUUID(), data: now, acao: "trocar_propria_senha", actor: session.usuario });
      values.users_audit = logs;
      return now;
    });
    const res = NextResponse.json({ ok: true, redirectTo: dashboardForPerfil(session.perfil) });
    res.cookies.set(COOKIE_NAME, await signToken({ ...session, must_change_password: false, password_reset_at: resetAt }), {
      httpOnly: true, secure: process.env.NODE_ENV === "production", sameSite: "lax", maxAge: TTL_SECONDS, path: "/",
    });
    return res;
  } catch {
    return NextResponse.json({ error: "Nao foi possivel alterar. Confira a senha atual ou entre novamente." }, { status: 400 });
  }
}
