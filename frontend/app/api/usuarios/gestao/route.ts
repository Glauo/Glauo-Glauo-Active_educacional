import { NextRequest, NextResponse } from "next/server";
import { getSession } from "@/lib/auth";
import { dbList, dbTransaction } from "@/lib/db";
import { isAdmin } from "@/lib/roles";
import { sendWhatsApp } from "@/lib/whatsapp";
import { sendEmail } from "@/lib/email";
import { studentCredentialEmail, studentCredentialPhone } from "@/lib/student-credentials";

import { generatedTempPassword, hashPassword } from "@/lib/passwords";
import { linkedTeacherUser, mutateManagedUser, UserManagementError } from "@/lib/user-management";

type Row = Record<string, unknown>;

function text(value: unknown) {
  return String(value || "").trim();
}

function lower(value: unknown) {
  return text(value).toLowerCase();
}

function digits(value: unknown) {
  return text(value).replace(/\D/g, "");
}

function normalizeStatus(value: unknown, fallback = "Ativo") {
  const raw = lower(value || fallback);
  return raw.includes("inativ") || raw.includes("cancel") || raw.includes("arquiv") ? "Inativo" : "Ativo";
}

function isActiveRow(row: Row, fallback = true) {
  if (row.is_active === false) return false;
  if (text(row.deleted_at)) return false;
  const status = normalizeStatus(row.status || row.situacao, fallback ? "Ativo" : "Inativo");
  return status === "Ativo";
}

function listPayload(users: Row[], teachers: Row[], students: Row[]) {
  const internal = users
    .filter((user) => !teachers.some(teacher => linkedTeacherUser([user], teacher)))
    .map((user) => ({
      source: "internal",
      id: text(user.id || user.usuario || user.pessoa || user.nome),
      nome: text(user.pessoa || user.nome || user.usuario),
      usuario: text(user.usuario),
      perfil: text(user.perfil || "Usuario"),
      email: text(user.email),
      telefone: text(user.celular || user.telefone || user.whatsapp),
      cpf: text(user.cpf),
      status: isActiveRow(user) ? "Ativo" : "Inativo",
      is_active: isActiveRow(user),
      tem_acesso: Boolean(text(user.usuario) && text(user.senha)),
      created_at: text(user.created_at),
      last_login_at: text(user.last_login_at),
      deleted_at: text(user.deleted_at),
    }));

  const teachersPayload = teachers.map((teacher) => {
    const linked = linkedTeacherUser(users, teacher);
    const nome = text(teacher.nome || teacher.name);
    return {
      source: "teacher",
      id: text(teacher.id || nome),
      nome,
      usuario: text(linked?.usuario || teacher.usuario || teacher.login),
      perfil: text(linked?.perfil || "Professor"),
      email: text(teacher.email || linked?.email),
      telefone: text(teacher.celular || teacher.telefone || teacher.whatsapp || linked?.celular || linked?.telefone),
      cpf: text(teacher.cpf),
      status: isActiveRow(teacher) ? "Ativo" : "Inativo",
      is_active: isActiveRow(teacher),
      tem_acesso: Boolean(text(linked?.usuario || teacher.usuario || teacher.login) && text(linked?.senha || teacher.senha)),
      created_at: text(teacher.created_at || linked?.created_at),
      last_login_at: text(linked?.last_login_at),
      deleted_at: text(teacher.deleted_at || linked?.deleted_at),
    };
  });

  const studentsPayload = students.map((student) => ({
    source: "student",
    id: text(student.id || student.nome),
    nome: text(student.nome || student.name),
    usuario: text(student.login || student.usuario),
    perfil: "Aluno",
    email: text(student.email || student.responsavel_email),
    telefone: text(student.telefone || student.celular || student.whatsapp || student.responsavel_telefone),
    cpf: text(student.cpf),
    status: isActiveRow(student) ? "Ativo" : "Inativo",
    is_active: isActiveRow(student),
    tem_acesso: Boolean(text(student.login || student.usuario) && text(student.senha)),
    created_at: text(student.created_at),
    last_login_at: text(student.last_login_at),
    deleted_at: text(student.deleted_at),
  }));

  return [...internal, ...teachersPayload, ...studentsPayload]
    .sort((a, b) => a.nome.localeCompare(b.nome, "pt-BR"));
}

async function notifyPasswordReset(payload: { nome: string; login: string; senha: string; email?: string; telefone?: string }, session: NonNullable<Awaited<ReturnType<typeof getSession>>>) {
  const message = [
    `Ola, ${payload.nome || "usuario"}!`,
    "Sua senha de acesso ao Active Educacional foi redefinida.",
    "",
    `Login: ${payload.login}`,
    "Solicite a senha temporaria ao administrador. Voce devera altera-la no primeiro acesso.",
    "",
    "Portal: https://ativoeducacional.tech/login",
  ].join("\n");

  const [whatsapp, mail] = await Promise.all([
    payload.telefone ? sendWhatsApp(payload.telefone, message, session) : Promise.resolve({ ok: false, status: "sem telefone" }),
    payload.email ? sendEmail(payload.email, "Redefinicao de senha - Active Educacional", message, session) : Promise.resolve({ ok: false, status: "sem email" }),
  ]);

  return {
    whatsapp: whatsapp.ok ? "enviado_wapi" : whatsapp.status,
    email: mail.ok ? "enviado_smtp" : mail.status,
  };
}

export async function GET() {
  const session = await getSession();
  if (!session || !isAdmin(session)) {
    return NextResponse.json({ error: "Acesso restrito a administradores." }, { status: 403 });
  }

  const [users, teachers, students] = await Promise.all([
    dbList<Row>("users.json"),
    dbList<Row>("teachers.json"),
    dbList<Row>("students.json"),
  ]);

  return NextResponse.json({
    usuarios: listPayload(users, teachers, students),
  });
}

async function mutate(req: NextRequest, action: "edit" | "delete" | "reset") {
  const session = await getSession();
  if (!session || !isAdmin(session)) return NextResponse.json({ error: "Acesso restrito a administradores." }, { status: 403 });
  const body = action === "delete" ? Object.fromEntries(new URL(req.url).searchParams) : await req.json().catch(() => ({})) as Row;
  if (action === "reset" && body.action !== "reset_password") return NextResponse.json({ error: "Acao invalida." }, { status: 400 });
  const tempPassword = action === "reset" ? generatedTempPassword() : "";
  const passwordHash = tempPassword ? await hashPassword(tempPassword) : undefined;
  try {
    const updated = await dbTransaction(["users", "teachers", "students", "users_audit"], values =>
      mutateManagedUser(values, body, action, text(session.pessoa || session.usuario), passwordHash));
    if (action !== "reset") return NextResponse.json({ ok: true });
    // Never persist the temporary password in outbound message history.
    const notify = await notifyPasswordReset({
      nome: text(updated.nome || updated.pessoa), login: text(updated.usuario || updated.login),
      senha: "", email: studentCredentialEmail(updated), telefone: studentCredentialPhone(updated),
    }, session).catch(() => ({ whatsapp: "falha_notificacao", email: "falha_notificacao" }));
    return NextResponse.json({ ok: true, senha_temporaria: tempPassword, notify }, { headers: { "Cache-Control": "no-store" } });
  } catch (error) {
    return NextResponse.json({ error: error instanceof UserManagementError ? error.message : "Nao foi possivel salvar. Tente novamente." },
      { status: error instanceof UserManagementError ? error.status : 500 });
  }
}
export async function PUT(req: NextRequest) { return mutate(req, "edit"); }
export async function POST(req: NextRequest) { return mutate(req, "reset"); }
export async function DELETE(req: NextRequest) { return mutate(req, "delete"); }
