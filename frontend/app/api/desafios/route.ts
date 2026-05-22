import { NextRequest, NextResponse } from "next/server";
import { dbList, dbSet } from "@/lib/db";
import { getSession } from "@/lib/auth";
import { notifyStudentsAboutLaunch } from "@/lib/student-launch-notifications";
import { normalizeList, text } from "@/lib/school-modules";

type Desafio = { id?: string; titulo?: string; turma?: string; turmas?: string[]; aluno?: string; alunos?: string[]; pontos?: number | string; status?: string; [k: string]: unknown };

export async function GET() {
  const session = await getSession();
  if (!session) return NextResponse.json({ error: "Não autorizado" }, { status: 401 });
  const desafios = await dbList<Desafio>("challenges.json");
  return NextResponse.json(desafios);
}

export async function POST(req: NextRequest) {
  const session = await getSession();
  if (!session) return NextResponse.json({ error: "Não autorizado" }, { status: 401 });
  const body = await req.json() as Desafio;
  const [desafios, students] = await Promise.all([dbList<Desafio>("challenges.json"), dbList<Record<string, unknown>>("students.json")]);
  const novo: Desafio = {
    ...body,
    id: body.id || `d_${Date.now()}`,
    turma: text(body.turma || "Todas") || "Todas",
    turmas: normalizeList(body.turmas),
    aluno: text(body.aluno),
    alunos: normalizeList(body.alunos),
    status: body.status || "Publicado",
  };
  novo.notification_status = await notifyStudentsAboutLaunch({
    students,
    item: novo,
    kind: "desafio",
    title: `Novo desafio: ${text(novo.titulo || "Desafio")}`,
    body: `Um novo desafio foi lancado para voce. Pontos: ${text(novo.pontos || 0)}.`,
    session,
  });
  desafios.push(novo);
  await dbSet("challenges.json", desafios);
  return NextResponse.json(novo, { status: 201 });
}

export async function PUT(req: NextRequest) {
  const session = await getSession();
  if (!session) return NextResponse.json({ error: "Não autorizado" }, { status: 401 });
  const body = await req.json() as Desafio;
  if (!body.id) return NextResponse.json({ error: "id obrigatório" }, { status: 400 });
  const desafios = await dbList<Desafio>("challenges.json");
  const idx = desafios.findIndex((d) => d.id === body.id);
  if (idx === -1) return NextResponse.json({ error: "Não encontrado" }, { status: 404 });
  desafios[idx] = {
    ...desafios[idx],
    ...body,
    turma: text(body.turma || desafios[idx].turma || "Todas") || "Todas",
    turmas: body.turmas === undefined ? desafios[idx].turmas : normalizeList(body.turmas),
    aluno: body.aluno === undefined ? desafios[idx].aluno : text(body.aluno),
    alunos: body.alunos === undefined ? desafios[idx].alunos : normalizeList(body.alunos),
  };
  await dbSet("challenges.json", desafios);
  return NextResponse.json(desafios[idx]);
}

export async function DELETE(req: NextRequest) {
  const session = await getSession();
  if (!session) return NextResponse.json({ error: "Não autorizado" }, { status: 401 });
  const { searchParams } = new URL(req.url);
  const id = searchParams.get("id");
  if (!id) return NextResponse.json({ error: "id obrigatório" }, { status: 400 });
  const desafios = await dbList<Desafio>("challenges.json");
  const filtered = desafios.filter((d) => d.id !== id);
  await dbSet("challenges.json", filtered);
  return NextResponse.json({ ok: true });
}
