import { dbGet, dbList, dbSet, dbUpdate, dbTransaction } from "@/lib/db";
import { releaseStudentAccessAfterPayment } from "@/lib/student-payment-automation";

type Row = Record<string, unknown>;
type ReconcileState = {
  running_until?: string;
  last_run_started_at?: string;
  last_run_completed_at?: string;
  last_run_result?: {
    checked: number;
    matched: number;
    paid: number;
    errors: number;
  };
};
type ReconcileOptions = {
  limit?: number;
  minIntervalMs?: number;
  lockMs?: number;
  force?: boolean;
};
const RECONCILE_STATE_KEY = "mercado_pago_reconcile_state.json";

function text(value: unknown) {
  return String(value || "").trim();
}

function validPaymentId(value: unknown) {
  const candidate = text(value);
  return /^[0-9]+$/.test(candidate) ? candidate : "";
}

export function mercadoPagoPaymentIdFromReceivable(row: Row) {
  return [
    row.mercado_pago_payment_id,
    row.mp_payment_id,
    row.boleto_mercado_pago_payment_id,
    row.pix_mercado_pago_payment_id,
    // Older records stored the Mercado Pago payment id in these generic fields.
    // Accept them only when they are numeric; barcodes and internal UUIDs are not payment ids.
    row.boleto_codigo,
    row.pix_codigo,
  ].map(validPaymentId).find(Boolean) || "";
}

function lower(value: unknown) {
  return text(value).toLowerCase();
}

function asRow(value: unknown): Row {
  return value && typeof value === "object" && !Array.isArray(value) ? value as Row : {};
}

function moneyNumber(value: unknown) {
  const raw = text(value).replace(/[^\d.,-]/g, "");
  const normalized = raw.includes(",")
    ? raw.replace(/\./g, "").replace(",", ".")
    : raw;
  const n = parseFloat(normalized);
  return Number.isFinite(n) ? Number(n.toFixed(2)) : 0;
}

function toIsoDate(value: unknown, fallbackIso: string) {
  const parsed = new Date(text(value) || fallbackIso);
  return Number.isNaN(parsed.getTime()) ? fallbackIso.slice(0, 10) : parsed.toISOString().slice(0, 10);
}

function isSettledStatus(status: unknown) {
  const value = lower(status);
  return value.includes("pago") || value.includes("baixado") || value.includes("liquidado") || value === "approved";
}

function isManualSettlementLocked(row: Row) {
  return Boolean(row.mercado_pago_manual_lock) && isSettledStatus(row.status || row.situacao);
}

function paymentMetadata(payment: Row) {
  return payment.metadata && typeof payment.metadata === "object" && !Array.isArray(payment.metadata)
    ? payment.metadata as Row
    : {};
}

function paymentMethodId(payment: Row) {
  const method = payment.payment_method && typeof payment.payment_method === "object" && !Array.isArray(payment.payment_method)
    ? payment.payment_method as Row
    : {};
  return lower(payment.payment_method_id || method.id);
}

function paymentMethodLabel(payment: Row) {
  const methodId = paymentMethodId(payment);
  if (methodId === "pix") return "Pix Mercado Pago";
  if (methodId.includes("bol")) return "Boleto Mercado Pago";
  return text((payment.payment_method as Row | undefined)?.type || methodId || "Mercado Pago");
}

function boletoToken(config: Row | null) {
  return text(
    process.env.ACTIVE_MERCADO_PAGO_ACCESS_TOKEN ||
    process.env.MERCADO_PAGO_ACCESS_TOKEN ||
    process.env.MP_ACCESS_TOKEN ||
    config?.mercado_pago_access_token ||
    config?.MERCADO_PAGO_ACCESS_TOKEN ||
    config?.mp_access_token ||
    config?.access_token ||
    config?.api_key
  );
}

async function audit(entry: Row) {
  await dbUpdate<Row[]>("finance_audit.json", (log) => [
    ...(Array.isArray(log) ? log : []),
    { id: crypto.randomUUID(), data: new Date().toISOString(), ...entry },
  ], []);
}

export async function loadMercadoPagoPayment(paymentId: string) {
  const config = await dbGet<Row>("boleto_config.json");
  const token = boletoToken(config);
  if (!token) {
    throw new Error("Mercado Pago Access Token nao configurado.");
  }

  if (!/^[0-9]+$/.test(paymentId)) throw new Error("Identificador de pagamento invalido.");
  const res = await fetch(`https://api.mercadopago.com/v1/payments/${encodeURIComponent(paymentId)}`, {
    signal: AbortSignal.timeout(15000),
    headers: { Authorization: `Bearer ${token}` },
    cache: "no-store",
  });
  const data = await res.json().catch(() => ({})) as Row;
  if (!res.ok) {
    throw new Error(text(data.message || data.error || `Mercado Pago HTTP ${res.status}`));
  }
  if (text(data.id) !== paymentId) throw new Error("Pagamento retornado nao corresponde ao solicitado.");
  return data;
}

export async function cancelMercadoPagoPayment(paymentId: string) {
  const config = await dbGet<Row>("boleto_config.json");
  const token = boletoToken(config);
  if (!token) throw new Error("Mercado Pago Access Token nao configurado.");
  const res = await fetch(`https://api.mercadopago.com/v1/payments/${encodeURIComponent(paymentId)}`, {
    method: "PUT",
    headers: {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ status: "cancelled" }),
    cache: "no-store",
  });
  const data = await res.json().catch(() => ({})) as Row;
  if (!res.ok) throw new Error(text(data.message || data.error || `Mercado Pago HTTP ${res.status}`));
  return data;
}

function mappedFinanceStatus(status: string) {
  switch (lower(status)) {
    case "approved":
      return "Pago";
    case "pending":
      return "Pendente";
    case "in_process":
      return "Em processamento";
    case "rejected":
      return "Recusada";
    case "cancelled":
      return "Cancelada";
    case "refunded":
      return "Estornada";
    case "charged_back":
      return "Contestada";
    default:
      return "Pendente";
  }
}

export function findReceivableIndex(receivables: Row[], payment: Row, paymentId: string) {
  const metadata = paymentMetadata(payment);
  const refs = [payment.external_reference, metadata.lancamento_id, metadata.external_reference,
    metadata.invoice_id, metadata.installment_id].map(text).filter(Boolean);
  const matches = receivables.map((item, index) => {
    const ids = [mercadoPagoPaymentIdFromReceivable(item), item.mercado_pago_previous_payment_id,
      ...(Array.isArray(item.mercado_pago_payment_history) ? item.mercado_pago_payment_history : [])]
      .map(validPaymentId).filter(Boolean);
    const invoiceRefs = [item.id, item.external_reference, item.payment_external_reference].map(text).filter(Boolean);
    return ids.includes(paymentId) || refs.some(ref => invoiceRefs.includes(ref)) ? index : -1;
  }).filter(index => index >= 0);
  // Never infer the installment from a name, CPF, email or amount.
  if (matches.length !== 1) return -1;
  const item = receivables[matches[0]];
  const invoiceRefs = [item.id, item.external_reference, item.payment_external_reference].map(text).filter(Boolean);
  if (refs.some(ref => !invoiceRefs.includes(ref))) return -1;
  const studentId = text(metadata.aluno_id || metadata.student_id);
  const storedStudentId = text(item.aluno_id || item.student_id);
  if (studentId && storedStudentId && studentId !== storedStudentId) return -1;
  return matches[0];
}

export type MercadoPagoSyncResult = {
  ok: true;
  matched: boolean;
  paid: boolean;
  paymentId: string;
  status: string;
  requiresReview?: boolean;
  expectedAmount?: number;
  actualAmount?: number;
  lancamento?: Row;
}

function isOpenFinanceStatus(status: unknown) {
  const value = lower(status);
  return !value || (!value.includes("pago") && !value.includes("baixado") && !value.includes("liquidado") && !value.includes("cancel") && !value.includes("estorn") && !value.includes("contest"));
}

function isTerminalMercadoPagoStatus(status: unknown) {
  const value = lower(status);
  return value === "approved" || value === "rejected" || value === "cancelled" || value === "refunded" || value === "charged_back";
}

function minutesSince(value: unknown) {
  const raw = text(value);
  if (!raw) return Number.POSITIVE_INFINITY;
  const parsed = new Date(raw);
  if (Number.isNaN(parsed.getTime())) return Number.POSITIVE_INFINITY;
  return Math.floor((Date.now() - parsed.getTime()) / 60000);
}

function msSince(value: unknown) {
  const raw = text(value);
  if (!raw) return Number.POSITIVE_INFINITY;
  const parsed = new Date(raw);
  if (Number.isNaN(parsed.getTime())) return Number.POSITIVE_INFINITY;
  return Date.now() - parsed.getTime();
}

function isLockActive(state: ReconcileState | null) {
  const until = text(state?.running_until);
  if (!until) return false;
  const parsed = new Date(until);
  return !Number.isNaN(parsed.getTime()) && parsed.getTime() > Date.now();
}

export async function syncMercadoPagoPayment(paymentId: string, source: "webhook" | "manual", expectedReceivableId?: string): Promise<MercadoPagoSyncResult> {
  const payment = await loadMercadoPagoPayment(paymentId);
  const status = lower(payment.status);
  const statusDetail = text(payment.status_detail);
  const metadata = paymentMetadata(payment);
  const externalReference = text(payment.external_reference || metadata.lancamento_id || metadata.external_reference);
  const now = new Date().toISOString();
  const result = await dbTransaction(
    ["receivables", "receipts", "finance_audit"],
    (values) => {
      const receivables = (Array.isArray(values.receivables) ? values.receivables : []) as Row[];
      const receipts = (Array.isArray(values.receipts) ? values.receipts : []) as Row[];
      const logs = (Array.isArray(values.finance_audit) ? values.finance_audit : []) as Row[];
      const log = (entry: Row) => logs.push({ id: crypto.randomUUID(), data: now, origem: source,
        mercado_pago_payment_id: paymentId, external_reference: externalReference, status, status_detail: statusDetail, ...entry });
      values.finance_audit = logs;
      const idx = findReceivableIndex(receivables, payment, paymentId);
      if (idx < 0 || (expectedReceivableId && text(receivables[idx]?.id) !== expectedReceivableId)) {
        log({ acao: "mercado_pago_pagamento_sem_lancamento_seguro" });
        return { ok: true as const, matched: false, paid: false, paymentId, status };
      }
      const before = receivables[idx];
      const currentId = text(before.mercado_pago_payment_id || before.mp_payment_id);
      const settled = isSettledStatus(before.status || before.situacao);
      const paid = status === "approved";
      const staleDate = Date.parse(text(payment.date_last_updated));
      const storedDate = Date.parse(text(before.mercado_pago_updated_at));
      if ((currentId && currentId !== paymentId && (!paid || settled)) ||
          (currentId === paymentId && Number.isFinite(staleDate) && Number.isFinite(storedDate) && staleDate < storedDate) ||
          (settled && !paid && !["refunded", "charged_back"].includes(status))) {
        log({ acao: "mercado_pago_status_antigo_ignorado", lancamento_id: before.id });
        return { ok: true as const, matched: true, paid: paid && settled, paymentId, status, lancamento: before };
      }
      // transaction_amount is the amount applied to the receivable. total_paid_amount
      // may include payer-side fees and must not be credited to the school account.
      const paidAmount = moneyNumber(payment.transaction_amount);
      if (paid && (paidAmount <= 0 || (text(payment.currency_id) && payment.currency_id !== "BRL"))) {
        throw new Error("Pagamento aprovado com valor ou moeda invalida.");
      }
      const expectedAmount = [
        before.mercado_pago_transaction_amount,
        before.boleto_valor_atualizado,
        before.pix_valor_atualizado,
        before.valor_parcela,
        before.valor,
        before.valor_total,
      ].map(moneyNumber).find(value => value > 0) || 0;
      if (paid && (expectedAmount <= 0 || Math.abs(paidAmount - expectedAmount) >= 0.01)) {
        const discrepancy: Row = {
          ...before,
          mercado_pago_payment_id: paymentId,
          mp_payment_id: paymentId,
          mercado_pago_status: status,
          payment_status: status,
          mercado_pago_detail: statusDetail,
          mercado_pago_updated_at: text(payment.date_last_updated),
          last_payment_check_at: now,
          mercado_pago_revisao_necessaria: true,
          mercado_pago_valor_esperado: expectedAmount,
          mercado_pago_valor_recebido: paidAmount,
        };
        receivables[idx] = discrepancy;
        values.receivables = receivables;
        log({ acao: "mercado_pago_valor_divergente_revisao_manual", lancamento_id: before.id,
          valor_esperado: expectedAmount, valor_recebido: paidAmount });
        return { ok: true as const, matched: true, paid: false, requiresReview: true,
          expectedAmount, actualAmount: paidAmount, paymentId, status, lancamento: discrepancy };
      }
      const paymentDate = toIsoDate(payment.date_approved || payment.date_last_updated, now);
      const next: Row = {
        ...before,
        external_reference: externalReference || text(before.external_reference || before.id),
        payment_status: status, mercado_pago_status: status, mp_status: status,
        mercado_pago_detail: statusDetail, mp_status_detail: statusDetail,
        mercado_pago_payment_id: paymentId, mp_payment_id: paymentId,
        mercado_pago_payment_method: paymentMethodId(payment), payment_method: paymentMethodLabel(payment),
        mercado_pago_updated_at: text(payment.date_last_updated),
        last_payment_check_at: now,
        ...(source === "webhook" ? { webhook_received_at: now, mercado_pago_webhook_at: now } : {}),
        updated_at: now, updated_by: source === "webhook" ? "Mercado Pago" : "Verificacao manual Mercado Pago",
      };
      if (paid) {
        Object.assign(next, { status: "Pago", situacao: "Pago", paid_at: paymentDate,
          paid_amount: paidAmount, valor_pago: paidAmount, data_baixa: text(before.data_baixa) || paymentDate,
          forma_pagamento: paymentMethodLabel(payment), baixado_por: text(before.baixado_por) || "Mercado Pago",
          mercado_pago_revisao_necessaria: false, mercado_pago_valor_esperado: expectedAmount,
          mercado_pago_valor_recebido: paidAmount });
        if (!receipts.some(receipt => text(receipt.mercado_pago_payment_id) === paymentId ||
            text(receipt.autenticidade) === `AE-MP-${paymentId}`)) {
          receipts.push({ id: crypto.randomUUID(), lancamento_id: text(before.id), tipo: "recebimentos",
            pessoa: before.aluno || before.nome, descricao: before.descricao || "Mensalidade escolar",
            valor: before.valor, valor_pago: paidAmount, forma_pagamento: paymentMethodLabel(payment),
            data: now, autenticidade: `AE-MP-${paymentId}`, gerado_automaticamente: true,
            mercado_pago_payment_id: paymentId });
        }
      } else if (!isManualSettlementLocked(before)) {
        next.status = mappedFinanceStatus(status);
        next.situacao = next.status;
      }
      receivables[idx] = next;
      values.receivables = receivables;
      values.receipts = receipts;
      log({ acao: paid ? (settled ? "mercado_pago_baixa_duplicada_ignorada" : "baixar_pagamento_mercado_pago") :
        "atualizar_status_mercado_pago", lancamento_id: before.id, antes: before, depois: next });
      return { ok: true as const, matched: true, paid, paymentId, status, lancamento: next };
    },
  );
  if (result.paid && result.lancamento && status === "approved") {
    // Financial commit is durable even if a downstream school automation fails.
    try {
      await releaseStudentAccessAfterPayment(result.lancamento, paymentId);
    } catch {
      await audit({ acao: "mercado_pago_liberacao_aluno_pendente", mercado_pago_payment_id: paymentId,
        lancamento_id: result.lancamento.id });
    }
  }
    return result;
  }

export async function reconcileMercadoPagoPendingReceivables(input: number | ReconcileOptions = 12) {
  const options = typeof input === "number" ? { limit: input } : input;
  const limit = Math.max(0, options.limit ?? 12);
  const minIntervalMs = Math.max(0, options.minIntervalMs ?? 90_000);
  const lockMs = Math.max(10_000, options.lockMs ?? 120_000);
  const force = Boolean(options.force);
  const state = await dbGet<ReconcileState>(RECONCILE_STATE_KEY);
  if (!force) {
    if (isLockActive(state)) {
      return {
        checked: 0,
        matched: 0,
        paid: 0,
        errors: 0,
        skipped: true,
        reason: "lock_active",
      };
    }
    if (msSince(state?.last_run_started_at || state?.last_run_completed_at) < minIntervalMs) {
      return {
        checked: 0,
        matched: 0,
        paid: 0,
        errors: 0,
        skipped: true,
        reason: "recent_run",
      };
    }
  }

  const now = new Date();
  await dbSet(RECONCILE_STATE_KEY, {
    ...(state || {}),
    last_run_started_at: now.toISOString(),
    running_until: new Date(now.getTime() + lockMs).toISOString(),
  } satisfies ReconcileState);

  const receivables = await dbList<Row>("receivables.json");
  const candidates = receivables
    .filter((row) => {
      const paymentId = mercadoPagoPaymentIdFromReceivable(row);
      if (!paymentId) return false;
      if (isManualSettlementLocked(row)) return false;
      if (!isOpenFinanceStatus(row.status || row.situacao)) return false;
      if (isTerminalMercadoPagoStatus(row.payment_status || row.mercado_pago_status || row.mp_status)) return false;
      return minutesSince(row.last_payment_check_at) >= 2;
    })
    .sort((a, b) => {
      const aChecked = minutesSince(a.last_payment_check_at);
      const bChecked = minutesSince(b.last_payment_check_at);
      if (aChecked !== bChecked) return bChecked - aChecked;
      return text(a.vencimento || a.data_vencimento).localeCompare(text(b.vencimento || b.data_vencimento));
    })
    .slice(0, limit);

  let checked = 0;
  let matched = 0;
  let paid = 0;
  let errors = 0;

  try {
    for (const row of candidates) {
      const paymentId = mercadoPagoPaymentIdFromReceivable(row);
      if (!paymentId) continue;
      checked++;
      try {
        const result = await syncMercadoPagoPayment(paymentId, "manual");
        if (result.matched) matched++;
        if (result.paid) paid++;
      } catch (error) {
        errors++;
        await audit({
          acao: "mercado_pago_reconciliacao_automatica_erro",
          mercado_pago_payment_id: paymentId,
          lancamento_id: row.id,
          erro: error instanceof Error ? error.message : String(error),
        });
      }
    }
  } finally {
    await dbSet(RECONCILE_STATE_KEY, {
      last_run_started_at: now.toISOString(),
      last_run_completed_at: new Date().toISOString(),
      running_until: "",
      last_run_result: { checked, matched, paid, errors },
    } satisfies ReconcileState);
  }

  return { checked, matched, paid, errors };
}
