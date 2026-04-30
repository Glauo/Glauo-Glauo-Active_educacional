import { NextRequest, NextResponse } from "next/server";
import { dbList, dbSet } from "@/lib/db";
import { getSession } from "@/lib/auth";

type ItemEstoque = { id?: string; nome?: string; categoria?: string; quantidade?: number | string; quantidade_minima?: number | string; preco?: number | string; [k: string]: unknown };
type MovimentoEstoque = { id?: string; item?: string; tipo?: string; quantidade?: number | string; data?: string; [k: string]: unknown };

export async function GET(req: NextRequest) {
  const session = await getSession();
  if (!session) return NextResponse.json({ error: "Não autorizado" }, { status: 401 });
  const { searchParams } = new URL(req.url);
  const tipo = searchParams.get("tipo") || "itens";
  if (tipo === "movimentos") {
    return NextResponse.json(await dbList<MovimentoEstoque>("inventory_moves.json"));
  }
  if (tipo === "pedidos") {
    return NextResponse.json(await dbList("material_orders.json"));
  }
  return NextResponse.json(await dbList<ItemEstoque>("inventory.json"));
}

export async function POST(req: NextRequest) {
  const session = await getSession();
  if (!session) return NextResponse.json({ error: "Não autorizado" }, { status: 401 });
  const { searchParams } = new URL(req.url);
  const tipo = searchParams.get("tipo") || "itens";

  if (tipo === "movimentos") {
    const body = await req.json() as MovimentoEstoque;
    const movimentos = await dbList<MovimentoEstoque>("inventory_moves.json");
    const novo = { ...body, id: body.id || `mov_${Date.now()}`, data: body.data || new Date().toISOString() };
    movimentos.push(novo);

    // Atualiza quantidade do item no inventário
    if (body.item && body.quantidade) {
      const itens = await dbList<ItemEstoque>("inventory.json");
      const idx = itens.findIndex((i) => i.id === body.item || i.nome === body.item);
      if (idx !== -1) {
        const qtd = Number(itens[idx].quantidade) || 0;
        const delta = Number(body.quantidade) || 0;
        itens[idx].quantidade = body.tipo === "saida" ? Math.max(0, qtd - delta) : qtd + delta;
        await dbSet("inventory.json", itens);
      }
    }

    await dbSet("inventory_moves.json", movimentos);
    return NextResponse.json(novo, { status: 201 });
  }

  const body = await req.json() as ItemEstoque;
  const itens = await dbList<ItemEstoque>("inventory.json");
  const novo = { ...body, id: body.id || `inv_${Date.now()}` };
  itens.push(novo);
  await dbSet("inventory.json", itens);
  return NextResponse.json(novo, { status: 201 });
}

export async function PUT(req: NextRequest) {
  const session = await getSession();
  if (!session) return NextResponse.json({ error: "Não autorizado" }, { status: 401 });
  const body = await req.json() as ItemEstoque;
  if (!body.id) return NextResponse.json({ error: "id obrigatório" }, { status: 400 });
  const itens = await dbList<ItemEstoque>("inventory.json");
  const idx = itens.findIndex((i) => i.id === body.id);
  if (idx === -1) return NextResponse.json({ error: "Não encontrado" }, { status: 404 });
  itens[idx] = { ...itens[idx], ...body };
  await dbSet("inventory.json", itens);
  return NextResponse.json(itens[idx]);
}

export async function DELETE(req: NextRequest) {
  const session = await getSession();
  if (!session) return NextResponse.json({ error: "Não autorizado" }, { status: 401 });
  const { searchParams } = new URL(req.url);
  const id = searchParams.get("id");
  if (!id) return NextResponse.json({ error: "id obrigatório" }, { status: 400 });
  const itens = await dbList<ItemEstoque>("inventory.json");
  const filtered = itens.filter((i) => i.id !== id);
  await dbSet("inventory.json", filtered);
  return NextResponse.json({ ok: true });
}
