import { NextRequest, NextResponse } from "next/server";
import { dbList, dbSet } from "@/lib/db";
import { getSession } from "@/lib/auth";

const KEY = "agenda.json";

export async function GET() {
  const session = await getSession();
  if (!session) return NextResponse.json({ error: "Não autorizado." }, { status: 401 });

  const agenda = await dbList(KEY);
  return NextResponse.json({ agenda });
}

export async function POST(req: NextRequest) {
  const session = await getSession();
  if (!session) return NextResponse.json({ error: "Não autorizado." }, { status: 401 });

  try {
    const body = await req.json();
    const agenda = await dbList<Record<string, unknown>>(KEY);
    const novo = { ...body, id: body.id || crypto.randomUUID(), created_at: new Date().toISOString() };
    agenda.push(novo);
    await dbSet(KEY, agenda);
    return NextResponse.json({ ok: true, evento: novo }, { status: 201 });
  } catch (err) {
    console.error("[agenda POST]", err);
    return NextResponse.json({ error: "Erro ao salvar evento." }, { status: 500 });
  }
}

export async function PUT(req: NextRequest) {
  const session = await getSession();
  if (!session) return NextResponse.json({ error: "Não autorizado." }, { status: 401 });

  try {
    const { id, ...updates } = await req.json();
    if (!id) return NextResponse.json({ error: "ID obrigatório." }, { status: 400 });

    const agenda = await dbList<Record<string, unknown>>(KEY);
    const idx = agenda.findIndex((e) => e.id === id);
    if (idx === -1) return NextResponse.json({ error: "Evento não encontrado." }, { status: 404 });

    agenda[idx] = { ...agenda[idx], ...updates, updated_at: new Date().toISOString() };
    await dbSet(KEY, agenda);
    return NextResponse.json({ ok: true, evento: agenda[idx] });
  } catch (err) {
    console.error("[agenda PUT]", err);
    return NextResponse.json({ error: "Erro ao atualizar evento." }, { status: 500 });
  }
}

export async function DELETE(req: NextRequest) {
  const session = await getSession();
  if (!session) return NextResponse.json({ error: "Não autorizado." }, { status: 401 });
  const { searchParams } = new URL(req.url);
  const id = searchParams.get("id");
  if (!id) return NextResponse.json({ error: "id obrigatório" }, { status: 400 });
  const agenda = await dbList<Record<string, unknown>>(KEY);
  const filtered = agenda.filter((e) => e.id !== id);
  await dbSet(KEY, filtered);
  return NextResponse.json({ ok: true });
}
