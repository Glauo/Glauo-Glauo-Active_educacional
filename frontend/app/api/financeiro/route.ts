import { NextRequest, NextResponse } from "next/server";
import { dbList, dbSet } from "@/lib/db";
import { getSession } from "@/lib/auth";

export async function GET(req: NextRequest) {
  const session = await getSession();
  if (!session) return NextResponse.json({ error: "Não autorizado." }, { status: 401 });

  const { searchParams } = new URL(req.url);
  const tipo = searchParams.get("tipo") || "recebimentos";

  const key = tipo === "despesas" ? "payables.json" : "receivables.json";
  const lancamentos = await dbList(key);
  return NextResponse.json({ lancamentos });
}

export async function POST(req: NextRequest) {
  const session = await getSession();
  if (!session) return NextResponse.json({ error: "Não autorizado." }, { status: 401 });

  try {
    const body = await req.json();
    const { tipo = "recebimentos", ...data } = body;
    const key = tipo === "despesas" ? "payables.json" : "receivables.json";

    const lancamentos = await dbList<Record<string, unknown>>(key);
    const novo = { ...data, id: data.id || crypto.randomUUID(), created_at: new Date().toISOString() };
    lancamentos.push(novo);
    await dbSet(key, lancamentos);
    return NextResponse.json({ ok: true, lancamento: novo }, { status: 201 });
  } catch (err) {
    console.error("[financeiro POST]", err);
    return NextResponse.json({ error: "Erro ao salvar lançamento." }, { status: 500 });
  }
}

export async function PUT(req: NextRequest) {
  const session = await getSession();
  if (!session) return NextResponse.json({ error: "Não autorizado." }, { status: 401 });

  try {
    const { id, tipo = "recebimentos", ...updates } = await req.json();
    if (!id) return NextResponse.json({ error: "ID obrigatório." }, { status: 400 });

    const key = tipo === "despesas" ? "payables.json" : "receivables.json";
    const lancamentos = await dbList<Record<string, unknown>>(key);
    const idx = lancamentos.findIndex((l) => l.id === id);
    if (idx === -1) return NextResponse.json({ error: "Lançamento não encontrado." }, { status: 404 });

    lancamentos[idx] = { ...lancamentos[idx], ...updates, updated_at: new Date().toISOString() };
    await dbSet(key, lancamentos);
    return NextResponse.json({ ok: true, lancamento: lancamentos[idx] });
  } catch (err) {
    console.error("[financeiro PUT]", err);
    return NextResponse.json({ error: "Erro ao atualizar lançamento." }, { status: 500 });
  }
}

export async function DELETE(req: NextRequest) {
  const session = await getSession();
  if (!session) return NextResponse.json({ error: "Não autorizado." }, { status: 401 });
  const { searchParams } = new URL(req.url);
  const id = searchParams.get("id");
  const tipo = searchParams.get("tipo") || "recebimentos";
  if (!id) return NextResponse.json({ error: "id obrigatório" }, { status: 400 });
  const key = tipo === "despesas" ? "payables.json" : "receivables.json";
  const lancamentos = await dbList<Record<string, unknown>>(key);
  const filtered = lancamentos.filter((l) => l.id !== id);
  await dbSet(key, filtered);
  return NextResponse.json({ ok: true });
}
