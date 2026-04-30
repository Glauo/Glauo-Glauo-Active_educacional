import { NextRequest, NextResponse } from "next/server";
import { dbList, dbSet } from "@/lib/db";
import { getSession } from "@/lib/auth";

const KEY = "teachers.json";

export async function GET() {
  const session = await getSession();
  if (!session) return NextResponse.json({ error: "Não autorizado." }, { status: 401 });

  const professores = await dbList(KEY);
  return NextResponse.json({ professores });
}

export async function POST(req: NextRequest) {
  const session = await getSession();
  if (!session) return NextResponse.json({ error: "Não autorizado." }, { status: 401 });

  try {
    const body = await req.json();
    const professores = await dbList<Record<string, unknown>>(KEY);
    const novo = { ...body, id: body.id || crypto.randomUUID(), created_at: new Date().toISOString() };
    professores.push(novo);
    await dbSet(KEY, professores);
    return NextResponse.json({ ok: true, professor: novo }, { status: 201 });
  } catch (err) {
    console.error("[professores POST]", err);
    return NextResponse.json({ error: "Erro ao salvar professor." }, { status: 500 });
  }
}

export async function PUT(req: NextRequest) {
  const session = await getSession();
  if (!session) return NextResponse.json({ error: "Não autorizado." }, { status: 401 });

  try {
    const { id, ...updates } = await req.json();
    if (!id) return NextResponse.json({ error: "ID obrigatório." }, { status: 400 });

    const professores = await dbList<Record<string, unknown>>(KEY);
    const idx = professores.findIndex((p) => p.id === id || p.nome === id);
    if (idx === -1) return NextResponse.json({ error: "Professor não encontrado." }, { status: 404 });

    professores[idx] = { ...professores[idx], ...updates, updated_at: new Date().toISOString() };
    await dbSet(KEY, professores);
    return NextResponse.json({ ok: true, professor: professores[idx] });
  } catch (err) {
    console.error("[professores PUT]", err);
    return NextResponse.json({ error: "Erro ao atualizar professor." }, { status: 500 });
  }
}

export async function DELETE(req: NextRequest) {
  const session = await getSession();
  if (!session) return NextResponse.json({ error: "Não autorizado." }, { status: 401 });
  const { searchParams } = new URL(req.url);
  const id = searchParams.get("id");
  if (!id) return NextResponse.json({ error: "id obrigatório" }, { status: 400 });
  const professores = await dbList<Record<string, unknown>>(KEY);
  const filtered = professores.filter((p) => p.id !== id && p.nome !== id);
  await dbSet(KEY, filtered);
  return NextResponse.json({ ok: true });
}
