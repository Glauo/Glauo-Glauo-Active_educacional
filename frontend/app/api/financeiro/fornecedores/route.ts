import { NextRequest, NextResponse } from "next/server";
import { dbList, dbSet } from "@/lib/db";
import { getSession } from "@/lib/auth";

const KEY = "fornecedores.json";

type Fornecedor = {
  id: string;
  nome: string;
  cpf_cnpj: string;
  telefone: string;
  email: string;
  endereco: string;
  categoria: string;
  chave_pix: string;
  banco: string;
  observacoes: string;
  created_at: string;
  updated_at: string;
};

export async function GET(req: NextRequest) {
  const session = await getSession();
  if (!session) return NextResponse.json({ error: "Nao autorizado." }, { status: 401 });

  const { searchParams } = new URL(req.url);
  const id = searchParams.get("id");
  const fornecedores = await dbList<Fornecedor>(KEY);

  if (id) {
    const found = fornecedores.find((f) => f.id === id);
    if (!found) return NextResponse.json({ error: "Fornecedor nao encontrado." }, { status: 404 });
    return NextResponse.json({ fornecedor: found });
  }

  return NextResponse.json({ fornecedores });
}

export async function POST(req: NextRequest) {
  const session = await getSession();
  if (!session) return NextResponse.json({ error: "Nao autorizado." }, { status: 401 });

  try {
    const body = await req.json();
    const fornecedores = await dbList<Fornecedor>(KEY);
    const now = new Date().toISOString();
    const novo: Fornecedor = {
      id: crypto.randomUUID(),
      nome: String(body.nome || "").trim(),
      cpf_cnpj: String(body.cpf_cnpj || "").trim(),
      telefone: String(body.telefone || "").trim(),
      email: String(body.email || "").trim(),
      endereco: String(body.endereco || "").trim(),
      categoria: String(body.categoria || "Outros").trim(),
      chave_pix: String(body.chave_pix || "").trim(),
      banco: String(body.banco || "").trim(),
      observacoes: String(body.observacoes || "").trim(),
      created_at: now,
      updated_at: now,
    };
    if (!novo.nome) return NextResponse.json({ error: "Nome e obrigatorio." }, { status: 400 });
    fornecedores.push(novo);
    await dbSet(KEY, fornecedores);
    return NextResponse.json({ ok: true, fornecedor: novo }, { status: 201 });
  } catch (err) {
    console.error("[fornecedores POST]", err);
    return NextResponse.json({ error: "Erro ao salvar fornecedor." }, { status: 500 });
  }
}

export async function PUT(req: NextRequest) {
  const session = await getSession();
  if (!session) return NextResponse.json({ error: "Nao autorizado." }, { status: 401 });

  try {
    const body = await req.json();
    const { id, ...updates } = body;
    if (!id) return NextResponse.json({ error: "ID obrigatorio." }, { status: 400 });
    const fornecedores = await dbList<Fornecedor>(KEY);
    const idx = fornecedores.findIndex((f) => f.id === id);
    if (idx === -1) return NextResponse.json({ error: "Fornecedor nao encontrado." }, { status: 404 });
    fornecedores[idx] = { ...fornecedores[idx], ...updates, id, updated_at: new Date().toISOString() };
    await dbSet(KEY, fornecedores);
    return NextResponse.json({ ok: true, fornecedor: fornecedores[idx] });
  } catch (err) {
    console.error("[fornecedores PUT]", err);
    return NextResponse.json({ error: "Erro ao atualizar fornecedor." }, { status: 500 });
  }
}

export async function DELETE(req: NextRequest) {
  const session = await getSession();
  if (!session) return NextResponse.json({ error: "Nao autorizado." }, { status: 401 });
  const { searchParams } = new URL(req.url);
  const id = searchParams.get("id");
  if (!id) return NextResponse.json({ error: "id obrigatorio." }, { status: 400 });
  const fornecedores = await dbList<Fornecedor>(KEY);
  const filtered = fornecedores.filter((f) => f.id !== id);
  if (filtered.length === fornecedores.length) return NextResponse.json({ error: "Fornecedor nao encontrado." }, { status: 404 });
  await dbSet(KEY, filtered);
  return NextResponse.json({ ok: true });
}
