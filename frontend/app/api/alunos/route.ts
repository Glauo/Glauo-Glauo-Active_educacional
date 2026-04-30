import { NextRequest, NextResponse } from "next/server";
import { dbList, dbSet } from "@/lib/db";
import { getSession } from "@/lib/auth";

const KEY = "students.json";

export async function GET() {
  const session = await getSession();
  if (!session) return NextResponse.json({ error: "Não autorizado." }, { status: 401 });

  const alunos = await dbList(KEY);
  return NextResponse.json({ alunos });
}

export async function POST(req: NextRequest) {
  const session = await getSession();
  if (!session) return NextResponse.json({ error: "Não autorizado." }, { status: 401 });

  try {
    const body = await req.json();
    const alunos = await dbList<Record<string, unknown>>(KEY);

    const novo = {
      ...body,
      id: body.id || crypto.randomUUID(),
      created_at: new Date().toISOString()
    };

    alunos.push(novo);
    await dbSet(KEY, alunos);
    return NextResponse.json({ ok: true, aluno: novo }, { status: 201 });
  } catch (err) {
    console.error("[alunos POST]", err);
    return NextResponse.json({ error: "Erro ao salvar aluno." }, { status: 500 });
  }
}

export async function PUT(req: NextRequest) {
  const session = await getSession();
  if (!session) return NextResponse.json({ error: "Não autorizado." }, { status: 401 });

  try {
    const body = await req.json();
    const { id, ...updates } = body;

    if (!id) return NextResponse.json({ error: "ID obrigatório." }, { status: 400 });

    const alunos = await dbList<Record<string, unknown>>(KEY);
    const idx = alunos.findIndex((a) => a.id === id || a.nome === id);
    if (idx === -1) return NextResponse.json({ error: "Aluno não encontrado." }, { status: 404 });

    alunos[idx] = { ...alunos[idx], ...updates, updated_at: new Date().toISOString() };
    await dbSet(KEY, alunos);
    return NextResponse.json({ ok: true, aluno: alunos[idx] });
  } catch (err) {
    console.error("[alunos PUT]", err);
    return NextResponse.json({ error: "Erro ao atualizar aluno." }, { status: 500 });
  }
}

export async function DELETE(req: NextRequest) {
  const session = await getSession();
  if (!session) return NextResponse.json({ error: "Não autorizado." }, { status: 401 });

  const { searchParams } = new URL(req.url);
  const id = searchParams.get("id");
  if (!id) return NextResponse.json({ error: "ID obrigatório." }, { status: 400 });

  const alunos = await dbList<Record<string, unknown>>(KEY);
  const filtered = alunos.filter((a) => a.id !== id && a.nome !== id);
  await dbSet(KEY, filtered);
  return NextResponse.json({ ok: true });
}
