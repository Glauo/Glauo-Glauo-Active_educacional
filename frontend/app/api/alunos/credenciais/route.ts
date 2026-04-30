import { NextRequest, NextResponse } from "next/server";
import { dbList, dbSet } from "@/lib/db";
import { getSession } from "@/lib/auth";

type Aluno = { id?: string; nome?: string; name?: string; login?: string; senha?: string; turma?: string; [k: string]: unknown };

export async function GET() {
  const session = await getSession();
  if (!session || session.perfil === "Aluno") {
    return NextResponse.json({ error: "Não autorizado" }, { status: 401 });
  }

  const alunos = await dbList<Aluno>("students.json");
  // Retorna alunos sem expor senhas
  const lista = alunos.map((a) => ({
    id: a.id,
    nome: a.nome || a.name,
    turma: a.turma,
    login: a.login || null,
    temAcesso: Boolean(a.login && a.senha)
  }));
  return NextResponse.json(lista);
}

export async function PUT(req: NextRequest) {
  const session = await getSession();
  if (!session || session.perfil === "Aluno") {
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
  const conflito = alunos.find((a) => a.login === loginTrimmed && a.id !== id);
  if (conflito) {
    return NextResponse.json({ error: "Este login já está em uso por outro aluno." }, { status: 409 });
  }

  const idx = alunos.findIndex((a) => a.id === id || String(a.id) === String(id));
  if (idx === -1) {
    return NextResponse.json({ error: "Aluno não encontrado." }, { status: 404 });
  }

  alunos[idx] = { ...alunos[idx], login: loginTrimmed, senha: String(senha) };
  await dbSet("students.json", alunos);

  return NextResponse.json({ ok: true, login: loginTrimmed });
}

export async function DELETE(req: NextRequest) {
  const session = await getSession();
  if (!session || session.perfil === "Aluno") {
    return NextResponse.json({ error: "Não autorizado" }, { status: 401 });
  }

  const { searchParams } = new URL(req.url);
  const id = searchParams.get("id");
  if (!id) return NextResponse.json({ error: "id obrigatório" }, { status: 400 });

  const alunos = await dbList<Aluno>("students.json");
  const idx = alunos.findIndex((a) => a.id === id || String(a.id) === id);
  if (idx === -1) return NextResponse.json({ error: "Aluno não encontrado." }, { status: 404 });

  // Remove credenciais mas mantém o registro do aluno
  delete alunos[idx].login;
  delete alunos[idx].senha;
  await dbSet("students.json", alunos);

  return NextResponse.json({ ok: true });
}
