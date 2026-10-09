import { NextRequest, NextResponse } from "next/server";
import { getSession } from "@/lib/auth";
import { dbList, dbTransaction } from "@/lib/db";
import { isAdmin } from "@/lib/roles";
import { sendWhatsApp } from "@/lib/whatsapp";

import { hashPassword } from "@/lib/passwords";
import { linkedTeacherUser, mutateManagedUser, UserManagementError } from "@/lib/user-management";

type Row = Record<string, unknown>;

function text(value: unknown) {
  return String(value || "").trim();
}

function phoneFromTeacher(professor: Row) {
  return text(professor.whatsapp || professor.telefone || professor.celular || professor.phone);
}

function credentialMessage(nome: string, usuario: string, senha: string) {
  return [
    `Ola, ${nome || "professor"}!`,
    "Seu acesso ao painel Active Educacional foi atualizado.",
    "",
    `Login: ${usuario}`,
    "Solicite sua senha temporaria ao administrador e altere-a no primeiro acesso.",
    "",
    "Portal: https://ativoeducacional.tech/login",
  ].join("\n");
}

export async function GET() {
  const session = await getSession();
  if (!session || !isAdmin(session)) return NextResponse.json({ error: "Nao autorizado" }, { status: 401 });
  const [users, professores] = await Promise.all([dbList<Row>("users.json"), dbList<Row>("teachers.json")]);
  const lista = professores.map((p) => {
    const nome = text(p.nome || p.name);
    const user = linkedTeacherUser(users, p);
    return {
      id: text(p.id || nome),
      nome,
      perfil: text(user?.perfil || "Professor"),
      usuario: text(user?.usuario),
      temAcesso: Boolean(user?.usuario && user?.senha)
    };
  });
  return NextResponse.json(lista);
}

export async function PUT(req: NextRequest) {
  const session = await getSession();
  if (!session || !isAdmin(session)) return NextResponse.json({ error: "Nao autorizado" }, { status: 403 });
  const body = await req.json().catch(() => ({})) as Row;
  if (!text(body.id) || !text(body.usuario) || text(body.senha).length < 8 || text(body.senha).startsWith("scrypt$")) {
    return NextResponse.json({ error: "Informe o professor, login e uma nova senha de pelo menos 8 caracteres." }, { status: 400 });
  }
  const hash = await hashPassword(String(body.senha));
  try {
    const professor = await dbTransaction(["users", "teachers", "users_audit"], values => {
      const updated = mutateManagedUser(values, { ...body, source: "teacher" }, "edit", session.usuario);
      mutateManagedUser(values, { id: body.id, source: "teacher" }, "reset", session.usuario, hash);
      if (text(body.perfil)) {
        const linked = linkedTeacherUser(values.users as Row[], updated);
        if (linked) mutateManagedUser(values, { source: "internal", id: linked.id || linked.usuario, perfil: body.perfil }, "edit", session.usuario);
      }
      return updated;
    });
    const telefone = phoneFromTeacher(professor);
    const whatsapp = telefone ? await sendWhatsApp(telefone, credentialMessage(text(professor.nome), text(body.usuario), ""), session)
      .catch(() => ({ ok: false, status: "falha_notificacao" })) : { ok: false, status: "sem telefone" };
    return NextResponse.json({ ok: true, usuario: body.usuario, telefone, whatsapp_status: whatsapp.status, whatsapp_enviado: whatsapp.ok });
  } catch (error) {
    return NextResponse.json({ error: error instanceof UserManagementError ? error.message : "Nao foi possivel salvar." },
      { status: error instanceof UserManagementError ? error.status : 500 });
  }
}

export async function DELETE(req: NextRequest) {
  const session = await getSession();
  if (!session || !isAdmin(session)) return NextResponse.json({ error: "Nao autorizado" }, { status: 403 });
  try {
    await dbTransaction(["users", "teachers", "users_audit"], values =>
      mutateManagedUser(values, { source: "teacher", id: new URL(req.url).searchParams.get("id") }, "delete", session.usuario));
    return NextResponse.json({ ok: true });
  } catch (error) {
    return NextResponse.json({ error: error instanceof UserManagementError ? error.message : "Nao foi possivel desativar." },
      { status: error instanceof UserManagementError ? error.status : 500 });
  }
}
