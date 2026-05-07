import { NextRequest, NextResponse } from "next/server";
import { dbList, dbListWithoutKeys, dbSet } from "@/lib/db";
import { getSession } from "@/lib/auth";
import { sendWhatsApp } from "@/lib/whatsapp";

function text(value: unknown) {
  return String(value || "").trim();
}

const HEAVY_KEYS = ["boleto_pdf_b64", "file_b64", "pdf_b64", "base64", "arquivo_b64", "foto_b64", "imagem_b64", "documento_b64", "anexo_b64"];

function isPaid(value: unknown) {
  const status = text(value).toLowerCase();
  return status.includes("pago") || status.includes("baixado") || status.includes("liquidado");
}

async function audit(entry: Record<string, unknown>) {
  const log = await dbList<Record<string, unknown>>("finance_audit.json");
  await dbSet("finance_audit.json", [
    ...log,
    { id: crypto.randomUUID(), data: new Date().toISOString(), ...entry },
  ]);
}

function money(value: unknown) {
  const n = Number.parseFloat(text(value).replace(/[^\d,.-]/g, "").replace(/\./g, "").replace(",", ".")) || 0;
  return n.toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
}

function boletoMessage(lancamento: Record<string, unknown>, origin: string) {
  const id = text(lancamento.id);
  const pdfUrl = text(lancamento.boleto_pdf_url);
  const link = pdfUrl
    ? (pdfUrl.startsWith("http") ? pdfUrl : `${origin}${pdfUrl}`)
    : `${origin}/api/financeiro/boleto?id=${encodeURIComponent(id)}`;
  return [
    "Ola! Seu boleto/fatura da Active Educacional foi salvo.",
    "",
    `Aluno: ${text(lancamento.aluno || lancamento.nome)}`,
    `Referencia: ${text(lancamento.descricao)}`,
    `Parcela: ${text(lancamento.parcela) || "1"}`,
    `Valor: ${money(lancamento.valor_parcela || lancamento.valor)}`,
    `Vencimento: ${text(lancamento.vencimento || lancamento.data_vencimento)}`,
    "",
    `Acesse o boleto: ${link}`,
  ].join("\n");
}

function shouldSendWhatsApp(data: Record<string, unknown>) {
  return data.enviar_whatsapp === true ||
    text(data.enviar_whatsapp).toLowerCase() === "true" ||
    text((data.notification_status as Record<string, unknown> | undefined)?.whatsapp) === "link_gerado";
}

export async function GET(req: NextRequest) {
  const session = await getSession();
  if (!session) return NextResponse.json({ error: "Nao autorizado." }, { status: 401 });

  const { searchParams } = new URL(req.url);
  const tipo = searchParams.get("tipo") || "recebimentos";
  const key = tipo === "despesas" ? "payables.json" : "receivables.json";
  const lancamentos = searchParams.get("include_pdf") === "true" ? await dbList(key) : await dbListWithoutKeys(key, HEAVY_KEYS);
  return NextResponse.json({ lancamentos });
}

export async function POST(req: NextRequest) {
  const session = await getSession();
  if (!session) return NextResponse.json({ error: "Nao autorizado." }, { status: 401 });

  try {
    const body = await req.json();
    const { tipo = "recebimentos", ...data } = body;
    const key = tipo === "despesas" ? "payables.json" : "receivables.json";

    const lancamentos = await dbList<Record<string, unknown>>(key);
    const id = text(data.id) || crypto.randomUUID();
    const pdfUpdate = text(data.boleto_pdf_b64) ? {
      boleto_status: "Importado",
      boleto_pdf_url: `/api/financeiro/boleto-pdf?id=${encodeURIComponent(id)}`,
      boleto_pdf_mime: text(data.boleto_pdf_mime) || "application/pdf",
    } : {};
    const boletoUpdate = data.gerar_boleto ? {
      boleto_status: "Gerado",
      boleto_codigo: text(data.boleto_codigo) || `AE-${String(id).slice(0, 8).toUpperCase()}`,
      boleto_gerado_em: new Date().toISOString(),
      status: data.status || "Boleto gerado",
    } : {};
    const novo = {
      ...data,
      ...boletoUpdate,
      ...pdfUpdate,
      id,
      created_at: new Date().toISOString(),
      created_by: session.pessoa || session.usuario
    };
    lancamentos.push(novo);
    await dbSet(key, lancamentos);
    if (tipo !== "despesas" && shouldSendWhatsApp(data)) {
      const result = await sendWhatsApp(novo.telefone || novo.whatsapp, boletoMessage(novo, new URL(req.url).origin), session);
      const notificationStatus = { ...(novo.notification_status as Record<string, unknown> | undefined), whatsapp: result.ok ? "enviado_wapi" : result.status };
      novo.notification_status = notificationStatus;
      await dbSet(key, lancamentos.map((item) => item.id === id ? novo : item));
    }
    await audit({
      acao: "criar_lancamento",
      tipo,
      lancamento_id: novo.id,
      usuario: session.pessoa || session.usuario,
      perfil: session.perfil,
      depois: novo,
    });
    return NextResponse.json({ ok: true, lancamento: novo }, { status: 201 });
  } catch (err) {
    console.error("[financeiro POST]", err);
    return NextResponse.json({ error: "Erro ao salvar lancamento." }, { status: 500 });
  }
}

export async function PUT(req: NextRequest) {
  const session = await getSession();
  if (!session) return NextResponse.json({ error: "Nao autorizado." }, { status: 401 });

  try {
    const { id, tipo = "recebimentos", ...updates } = await req.json();
    if (!id) return NextResponse.json({ error: "ID obrigatorio." }, { status: 400 });

    const key = tipo === "despesas" ? "payables.json" : "receivables.json";
    const lancamentos = await dbList<Record<string, unknown>>(key);
    const idx = lancamentos.findIndex((l) => l.id === id);
    if (idx === -1) return NextResponse.json({ error: "Lancamento nao encontrado." }, { status: 404 });

    const before = { ...lancamentos[idx] };
    const wasPaid = isPaid(lancamentos[idx].status);
    const willBePaid = isPaid(updates.status);
    const isReversal = Boolean(updates.estorno);
    if (wasPaid && updates.status && !willBePaid && !isReversal) {
      return NextResponse.json({ error: "Lancamento pago so pode voltar para aberto por estorno auditado." }, { status: 409 });
    }

    const pdfUpdate = text(updates.boleto_pdf_b64) ? {
      boleto_status: "Importado",
      boleto_pdf_url: `/api/financeiro/boleto-pdf?id=${encodeURIComponent(id)}`,
      boleto_pdf_mime: text(updates.boleto_pdf_mime) || "application/pdf",
    } : {};
    const boletoUpdate = updates.gerar_boleto ? {
      boleto_status: "Gerado",
      boleto_codigo: text(lancamentos[idx].boleto_codigo) || `AE-${String(id).slice(0, 8).toUpperCase()}`,
      boleto_gerado_em: new Date().toISOString(),
      status: updates.status || "Boleto gerado",
    } : {};

    const estornoUpdate = isReversal ? {
      status: "Pendente",
      estornado_em: new Date().toISOString(),
      estornado_por: session.pessoa || session.usuario,
      estorno_motivo: text(updates.estorno_motivo) || "Estorno manual",
      data_baixa: "",
      valor_pago: "",
      forma_pagamento: "",
    } : {};

    lancamentos[idx] = {
      ...lancamentos[idx],
      ...updates,
      ...boletoUpdate,
      ...pdfUpdate,
      ...estornoUpdate,
      updated_at: new Date().toISOString(),
      updated_by: session.pessoa || session.usuario,
    };

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
        valor_pago: lancamento.valor_pago || lancamento.valor,
        forma_pagamento: lancamento.forma_pagamento || "Nao informado",
        data: new Date().toISOString(),
        autenticidade: `AE-${String(id).slice(0, 8).toUpperCase()}-${Date.now().toString(36).toUpperCase()}`,
        gerado_automaticamente: true,
        whatsapp: lancamento.telefone || lancamento.whatsapp || lancamento.professor_telefone || "",
      };
      writes.push(dbSet("receipts.json", [...recibos, recibo]));
    }

    await Promise.all(writes);
    if (tipo !== "despesas" && shouldSendWhatsApp(updates)) {
      const result = await sendWhatsApp(lancamentos[idx].telefone || lancamentos[idx].whatsapp, boletoMessage(lancamentos[idx], new URL(req.url).origin), session);
      lancamentos[idx].notification_status = { ...(lancamentos[idx].notification_status as Record<string, unknown> | undefined), whatsapp: result.ok ? "enviado_wapi" : result.status };
      await dbSet(key, lancamentos);
    }
    await audit({
      acao: isReversal ? "estornar_baixa" : willBePaid && !wasPaid ? "baixar_pagamento" : updates.gerar_boleto ? "gerar_boleto" : "editar_lancamento",
      tipo,
      lancamento_id: id,
      usuario: session.pessoa || session.usuario,
      perfil: session.perfil,
      antes: before,
      depois: lancamentos[idx],
    });
    return NextResponse.json({ ok: true, lancamento: lancamentos[idx] });
  } catch (err) {
    console.error("[financeiro PUT]", err);
    return NextResponse.json({ error: "Erro ao atualizar lancamento." }, { status: 500 });
  }
}

export async function DELETE(req: NextRequest) {
  const session = await getSession();
  if (!session) return NextResponse.json({ error: "Nao autorizado." }, { status: 401 });
  const { searchParams } = new URL(req.url);
  const id = searchParams.get("id");
  const tipo = searchParams.get("tipo") || "recebimentos";
  if (!id) return NextResponse.json({ error: "id obrigatorio" }, { status: 400 });
  const key = tipo === "despesas" ? "payables.json" : "receivables.json";
  const lancamentos = await dbList<Record<string, unknown>>(key);
  const target = lancamentos.find((l) => l.id === id);
  if (target && isPaid(target.status)) {
    return NextResponse.json({ error: "Lancamento pago nao pode ser excluido. Use estorno/cancelamento auditado." }, { status: 409 });
  }
  const filtered = lancamentos.filter((l) => l.id !== id);
  await dbSet(key, filtered);
  await audit({
    acao: "excluir_lancamento",
    tipo,
    lancamento_id: id,
    usuario: session.pessoa || session.usuario,
    perfil: session.perfil,
    antes: target || null,
  });
  return NextResponse.json({ ok: true });
}
