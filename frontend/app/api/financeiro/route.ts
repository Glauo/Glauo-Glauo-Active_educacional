import { NextRequest, NextResponse } from "next/server";
import { dbList, dbSet } from "@/lib/db";
import { getSession } from "@/lib/auth";

function text(value: unknown) {
  return String(value || "").trim();
}

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

    const wasPaid = String(lancamentos[idx].status || "").toLowerCase().includes("pago");
    const willBePaid = String(updates.status || "").toLowerCase().includes("pago");
    const boletoUpdate = updates.gerar_boleto ? {
      boleto_status: "Gerado",
      boleto_codigo: text(lancamentos[idx].boleto_codigo) || `AE-${String(id).slice(0, 8).toUpperCase()}`,
      boleto_gerado_em: new Date().toISOString(),
      status: updates.status || "Boleto gerado"
    } : {};

    lancamentos[idx] = { ...lancamentos[idx], ...updates, ...boletoUpdate, updated_at: new Date().toISOString() };

    const writes: Promise<boolean>[] = [dbSet(key, lancamentos)];
    if (!wasPaid && willBePaid) {
      const recibos = await dbList<Record<string, unknown>>("receipts.json");
      const lancamento = lancamentos[idx];
      const recibo = {
        id: crypto.randomUUID(),
        lancamento_id: id,
        tipo,
        pessoa: lancamento.aluno || lancamento.nome || lancamento.professor,
        descricao: lancamento.descricao,
        valor: lancamento.valor,
        data: new Date().toISOString(),
        gerado_automaticamente: true,
        whatsapp: lancamento.telefone || lancamento.whatsapp || lancamento.professor_telefone || ""
      };
      writes.push(dbSet("receipts.json", [...recibos, recibo]));
    }

    await Promise.all(writes);
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
