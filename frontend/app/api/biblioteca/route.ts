import { NextRequest, NextResponse } from "next/server";
import { dbList, dbSet } from "@/lib/db";
import { getSession } from "@/lib/auth";

type Livro = { id?: string; titulo?: string; autor?: string; nivel?: string; turma?: string; url?: string; [k: string]: unknown };

export async function GET(req: NextRequest) {
  const session = await getSession();
  if (!session) return NextResponse.json({ error: "Não autorizado" }, { status: 401 });
  const { searchParams } = new URL(req.url);
  const tipo = searchParams.get("tipo") || "livros";
  const key = tipo === "videos" ? "videos.json" : tipo === "materiais" ? "materials.json" : "books.json";
  const itens = await dbList(key);
  return NextResponse.json(itens);
}

export async function POST(req: NextRequest) {
  const session = await getSession();
  if (!session) return NextResponse.json({ error: "Não autorizado" }, { status: 401 });
  const { searchParams } = new URL(req.url);
  const tipo = searchParams.get("tipo") || "livros";
  const key = tipo === "videos" ? "videos.json" : tipo === "materiais" ? "materials.json" : "books.json";
  const body = await req.json() as Livro;
  const itens = await dbList<Livro>(key);
  const novo = { ...body, id: body.id || `bib_${Date.now()}` };
  itens.push(novo);
  await dbSet(key, itens);
  return NextResponse.json(novo, { status: 201 });
}

export async function PUT(req: NextRequest) {
  const session = await getSession();
  if (!session) return NextResponse.json({ error: "Não autorizado" }, { status: 401 });
  const { searchParams } = new URL(req.url);
  const tipo = searchParams.get("tipo") || "livros";
  const key = tipo === "videos" ? "videos.json" : tipo === "materiais" ? "materials.json" : "books.json";
  const body = await req.json() as Livro;
  if (!body.id) return NextResponse.json({ error: "id obrigatório" }, { status: 400 });
  const itens = await dbList<Livro>(key);
  const idx = itens.findIndex((l) => l.id === body.id);
  if (idx === -1) return NextResponse.json({ error: "Não encontrado" }, { status: 404 });
  itens[idx] = { ...itens[idx], ...body };
  await dbSet(key, itens);
  return NextResponse.json(itens[idx]);
}

export async function DELETE(req: NextRequest) {
  const session = await getSession();
  if (!session) return NextResponse.json({ error: "Não autorizado" }, { status: 401 });
  const { searchParams } = new URL(req.url);
  const id = searchParams.get("id");
  const tipo = searchParams.get("tipo") || "livros";
  if (!id) return NextResponse.json({ error: "id obrigatório" }, { status: 400 });
  const key = tipo === "videos" ? "videos.json" : tipo === "materiais" ? "materials.json" : "books.json";
  const itens = await dbList<Livro>(key);
  const filtered = itens.filter((l) => l.id !== id);
  await dbSet(key, filtered);
  return NextResponse.json({ ok: true });
}
