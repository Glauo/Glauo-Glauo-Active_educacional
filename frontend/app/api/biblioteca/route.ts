import { NextRequest, NextResponse } from "next/server";
import { mkdir, writeFile } from "fs/promises";
import path from "path";
import { getSession } from "@/lib/auth";
import { dbList, dbSet } from "@/lib/db";

type Livro = { id?: string; titulo?: string; autor?: string; nivel?: string; turma?: string; url?: string; pdf_nome?: string; [k: string]: unknown };

function keyFor(tipo: string) {
  return tipo === "videos" ? "videos.json" : tipo === "materiais" ? "materials.json" : "books.json";
}

function text(value: unknown) {
  return String(value || "").trim();
}

function safeFileName(value: string) {
  return value
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .replace(/[^a-zA-Z0-9._-]+/g, "-")
    .replace(/-+/g, "-")
    .replace(/^-|-$/g, "")
    .toLowerCase();
}

async function livroFromFormData(req: NextRequest, existing: Livro = {}) {
  const form = await req.formData();
  const id = text(form.get("id")) || text(existing.id) || `bib_${Date.now()}`;
  const file = form.get("arquivo_pdf");
  const livro: Livro = {
    ...existing,
    id,
    titulo: text(form.get("titulo")),
    autor: text(form.get("autor")),
    nivel: text(form.get("nivel")),
    turma: text(form.get("turma")) || "Todas",
    url: text(form.get("url")) || text(existing.url),
  };

  if (file instanceof File && file.size > 0) {
    if (file.type && file.type !== "application/pdf") {
      throw new Error("Envie apenas arquivo PDF.");
    }
    const uploadsDir = path.join(process.cwd(), "public", "uploads", "livros");
    await mkdir(uploadsDir, { recursive: true });
    const base = safeFileName(file.name || `${id}.pdf`) || `${id}.pdf`;
    const filename = `${Date.now()}-${base.endsWith(".pdf") ? base : `${base}.pdf`}`;
    await writeFile(path.join(uploadsDir, filename), Buffer.from(await file.arrayBuffer()));
    livro.url = `/uploads/livros/${filename}`;
    livro.pdf_nome = file.name || filename;
  }

  return livro;
}

async function requestBody(req: NextRequest, existing?: Livro) {
  const isForm = req.headers.get("content-type")?.includes("multipart/form-data");
  return isForm ? livroFromFormData(req, existing) : req.json() as Promise<Livro>;
}

export async function GET(req: NextRequest) {
  const session = await getSession();
  if (!session) return NextResponse.json({ error: "Nao autorizado" }, { status: 401 });
  const { searchParams } = new URL(req.url);
  const itens = await dbList(keyFor(searchParams.get("tipo") || "livros"));
  return NextResponse.json(itens);
}

export async function POST(req: NextRequest) {
  const session = await getSession();
  if (!session) return NextResponse.json({ error: "Nao autorizado" }, { status: 401 });
  const { searchParams } = new URL(req.url);
  const key = keyFor(searchParams.get("tipo") || "livros");
  const itens = await dbList<Livro>(key);
  try {
    const body = await requestBody(req);
    const novo = { ...body, id: body.id || `bib_${Date.now()}` };
    itens.push(novo);
    await dbSet(key, itens);
    return NextResponse.json(novo, { status: 201 });
  } catch (err) {
    return NextResponse.json({ error: err instanceof Error ? err.message : "Erro ao salvar." }, { status: 400 });
  }
}

export async function PUT(req: NextRequest) {
  const session = await getSession();
  if (!session) return NextResponse.json({ error: "Nao autorizado" }, { status: 401 });
  const { searchParams } = new URL(req.url);
  const key = keyFor(searchParams.get("tipo") || "livros");
  const itens = await dbList<Livro>(key);
  const incoming = await requestBody(req);
  if (!incoming.id) return NextResponse.json({ error: "id obrigatorio" }, { status: 400 });
  const idx = itens.findIndex((l) => l.id === incoming.id);
  if (idx === -1) return NextResponse.json({ error: "Nao encontrado" }, { status: 404 });
  const body = req.headers.get("content-type")?.includes("multipart/form-data")
    ? incoming
    : { ...itens[idx], ...incoming };
  itens[idx] = body;
  await dbSet(key, itens);
  return NextResponse.json(itens[idx]);
}

export async function DELETE(req: NextRequest) {
  const session = await getSession();
  if (!session) return NextResponse.json({ error: "Nao autorizado" }, { status: 401 });
  const { searchParams } = new URL(req.url);
  const id = searchParams.get("id");
  if (!id) return NextResponse.json({ error: "id obrigatorio" }, { status: 400 });
  const key = keyFor(searchParams.get("tipo") || "livros");
  const itens = await dbList<Livro>(key);
  await dbSet(key, itens.filter((l) => l.id !== id));
  return NextResponse.json({ ok: true });
}
