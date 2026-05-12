import { NextRequest, NextResponse } from "next/server";
import { dbList, dbSet } from "@/lib/db";
import { getSession } from "@/lib/auth";

type Desafio = { id?: string; titulo?: string; turma?: string; pontos?: number | string; status?: string; [k: string]: unknown };

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
  const desafios = await dbList<Desafio>("challenges.json");
  const novo = { ...body, id: body.id || `d_${Date.now()}`, status: body.status || "Publicado" };
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
  desafios[idx] = { ...desafios[idx], ...body };
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
