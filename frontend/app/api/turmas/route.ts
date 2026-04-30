import { NextRequest, NextResponse } from "next/server";
import { dbList, dbSet } from "@/lib/db";
import { getSession } from "@/lib/auth";

const KEY = "classes.json";

export async function GET() {
  const session = await getSession();
  if (!session) return NextResponse.json({ error: "Não autorizado." }, { status: 401 });

  const turmas = await dbList(KEY);
  return NextResponse.json({ turmas });
}

export async function POST(req: NextRequest) {
  const session = await getSession();
  if (!session) return NextResponse.json({ error: "Não autorizado." }, { status: 401 });

  try {
    const body = await req.json();
    const turmas = await dbList<Record<string, unknown>>(KEY);
    const nova = { ...body, id: body.id || crypto.randomUUID(), created_at: new Date().toISOString() };
    turmas.push(nova);
    await dbSet(KEY, turmas);
    return NextResponse.json({ ok: true, turma: nova }, { status: 201 });
  } catch (err) {
    console.error("[turmas POST]", err);
    return NextResponse.json({ error: "Erro ao salvar turma." }, { status: 500 });
  }
}

export async function PUT(req: NextRequest) {
  const session = await getSession();
  if (!session) return NextResponse.json({ error: "Não autorizado." }, { status: 401 });

  try {
    const { id, ...updates } = await req.json();
    if (!id) return NextResponse.json({ error: "ID obrigatório." }, { status: 400 });

    const turmas = await dbList<Record<string, unknown>>(KEY);
    const idx = turmas.findIndex((t) => t.id === id || t.nome === id);
    if (idx === -1) return NextResponse.json({ error: "Turma não encontrada." }, { status: 404 });

    turmas[idx] = { ...turmas[idx], ...updates, updated_at: new Date().toISOString() };
    await dbSet(KEY, turmas);
    return NextResponse.json({ ok: true, turma: turmas[idx] });
  } catch (err) {
    console.error("[turmas PUT]", err);
    return NextResponse.json({ error: "Erro ao atualizar turma." }, { status: 500 });
  }
}

export async function DELETE(req: NextRequest) {
  const session = await getSession();
  if (!session) return NextResponse.json({ error: "Não autorizado." }, { status: 401 });
  const { searchParams } = new URL(req.url);
  const id = searchParams.get("id");
  if (!id) return NextResponse.json({ error: "id obrigatório" }, { status: 400 });
  const turmas = await dbList<Record<string, unknown>>(KEY);
  const filtered = turmas.filter((t) => t.id !== id && t.nome !== id);
  await dbSet(KEY, filtered);
  return NextResponse.json({ ok: true });
}
