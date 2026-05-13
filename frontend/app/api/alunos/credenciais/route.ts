import { NextRequest, NextResponse } from "next/server";
import { dbList, dbSet } from "@/lib/db";
import { getSession } from "@/lib/auth";
import { isAdminOrCoordinator } from "@/lib/roles";
import { sendWhatsApp } from "@/lib/whatsapp";

type Aluno = { id?: string; nome?: string; name?: string; login?: string; senha?: string; turma?: string; classe?: string; celular?: string; telefone?: string; whatsapp?: string; responsavel?: unknown; responsavel_telefone?: string; responsavel_email?: string; [k: string]: unknown };

function text(value: unknown) {
  if (value && typeof value === "object" && !Array.isArray(value)) {
    const row = value as Record<string, unknown>;
    return String(row.nome || row.name || row.celular || row.telefone || row.whatsapp || row.email || "").trim();
  }
  return String(value || "").trim();
}

function phoneFromStudent(aluno: Aluno) {
  const responsavel = aluno.responsavel && typeof aluno.responsavel === "object" && !Array.isArray(aluno.responsavel)
    ? aluno.responsavel as Record<string, unknown>
    : {};
  return text(aluno.celular || aluno.whatsapp || aluno.telefone || aluno.responsavel_telefone || responsavel.celular || responsavel.telefone || responsavel.whatsapp);
}

function whatsappUrl(phone: unknown, message: string) {
  let digits = String(phone || "").replace(/\D/g, "");
  if (digits.length === 10 || digits.length === 11) digits = `55${digits}`;
  return digits ? `https://wa.me/${digits}?text=${encodeURIComponent(message)}` : "";
}

function credentialMessage(aluno: Aluno, login: string, senha: string) {
  const nome = text(aluno.nome || aluno.name || "Aluno");
  return [
    `Olá, ${nome}!`,
    "Seu acesso ao portal do aluno Active Educacional foi atualizado.",
    "",
    `Login: ${login}`,
    `Senha: ${senha}`,
    "",
    "Acesse pelo portal da escola. Se tiver dificuldade, fale com a secretaria.",
  ].join("\n");
}

function sameStudent(aluno: Aluno, id: string) {
  const ref = text(id).toLowerCase();
  return [aluno.id, aluno.nome, aluno.name].some((value) => text(value).toLowerCase() === ref);
}

export async function GET() {
  const session = await getSession();
  if (!session || !isAdminOrCoordinator(session)) {
    return NextResponse.json({ error: "Não autorizado" }, { status: 401 });
  }

  const alunos = await dbList<Aluno>("students.json");
  // Retorna alunos sem expor senhas
  const lista = alunos.map((a) => ({
    id: a.id,
    nome: a.nome || a.name,
    turma: a.turma || a.classe,
    login: a.login || null,
    senha: a.senha || null,
    telefone: phoneFromStudent(a),
    temAcesso: Boolean(a.login && a.senha)
  }));
  return NextResponse.json(lista);
}

export async function PUT(req: NextRequest) {
  const session = await getSession();
  if (!session || !isAdminOrCoordinator(session)) {
    return NextResponse.json({ error: "Não autorizado" }, { status: 401 });
  }

  const { id, login, senha } = await req.json() as { id: string; login: string; senha: string };

  if (!id || !login || !senha) {
    return NextResponse.json({ error: "id, login e senha são obrigatórios." }, { status: 400 });
  }

  const loginTrimmed = String(login).trim().toLowerCase();
  if (loginTrimmed.length < 3) {
    return NextResponse.json({ error: "Login deve ter pelo menos 3 caracteres." }, { status: 400 });
  }
  if (String(senha).length < 4) {
    return NextResponse.json({ error: "Senha deve ter pelo menos 4 caracteres." }, { status: 400 });
  }

  const alunos = await dbList<Aluno>("students.json");

  // Verifica se o login já está em uso por outro aluno
  const conflito = alunos.find((a) => a.login === loginTrimmed && !sameStudent(a, id));
  if (conflito) {
    return NextResponse.json({ error: "Este login já está em uso por outro aluno." }, { status: 409 });
  }

  const idx = alunos.findIndex((a) => sameStudent(a, id));
  if (idx === -1) {
    return NextResponse.json({ error: "Aluno não encontrado." }, { status: 404 });
  }

  alunos[idx] = { ...alunos[idx], login: loginTrimmed, senha: String(senha) };
  await dbSet("students.json", alunos);

  const message = credentialMessage(alunos[idx], loginTrimmed, String(senha));
  const telefone = phoneFromStudent(alunos[idx]);
  const whatsapp = telefone ? await sendWhatsApp(telefone, message, session) : { ok: false, status: "sem telefone" };
  return NextResponse.json({
    ok: true,
    login: loginTrimmed,
    telefone,
    whatsapp_status: whatsapp.status,
    whatsapp_enviado: whatsapp.ok,
    whatsapp_url: whatsappUrl(telefone, message),
    whatsapp_message: message,
  });
}

export async function DELETE(req: NextRequest) {
  const session = await getSession();
  if (!session || !isAdminOrCoordinator(session)) {
    return NextResponse.json({ error: "Não autorizado" }, { status: 401 });
  }

  const { searchParams } = new URL(req.url);
  const id = searchParams.get("id");
  if (!id) return NextResponse.json({ error: "id obrigatório" }, { status: 400 });

  const alunos = await dbList<Aluno>("students.json");
  const idx = alunos.findIndex((a) => sameStudent(a, id));
  if (idx === -1) return NextResponse.json({ error: "Aluno não encontrado." }, { status: 404 });

  // Remove credenciais mas mantém o registro do aluno
  delete alunos[idx].login;
  delete alunos[idx].senha;
  await dbSet("students.json", alunos);

  return NextResponse.json({ ok: true });
}
