import { createHmac, timingSafeEqual } from "crypto";
import { NextRequest, NextResponse } from "next/server";
import { dbGet, dbUpdate } from "@/lib/db";
import { syncMercadoPagoPayment } from "@/lib/mercadopago-sync";

type Row = Record<string, unknown>;

function text(value: unknown) {
  return String(value || "").trim();
}

function lower(value: unknown) {
  return text(value).toLowerCase();
}

function moneyNumber(value: unknown) {
  const n = parseFloat(String(value || "0").replace(/[^\d.,-]/g, "").replace(",", "."));
  return Number.isFinite(n) && n > 0 ? Number(n.toFixed(2)) : 0;
}

function parseSignature(header: string) {
  const parts = Object.fromEntries(header.split(",").map((part) => {
    const [key, ...rest] = part.trim().split("=");
    return [key, rest.join("=")];
  }));
  return { ts: text(parts.ts), v1: text(parts.v1) };
}

function safeCompareHex(a: string, b: string) {
  if (!/^[a-f0-9]+$/i.test(a) || !/^[a-f0-9]+$/i.test(b)) return false;
  const left = Buffer.from(a, "hex");
  const right = Buffer.from(b, "hex");
  if (left.length !== right.length) return false;
  return timingSafeEqual(left, right);
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

function webhookSecret(config: Row | null) {
  return text(
    process.env.ACTIVE_MERCADO_PAGO_WEBHOOK_SECRET ||
    process.env.MERCADO_PAGO_WEBHOOK_SECRET ||
    config?.mercado_pago_webhook_secret ||
    config?.webhook_secret
  );
}

async function audit(entry: Row) {
  await dbUpdate<Row[]>("finance_audit.json", log => [
    ...(Array.isArray(log) ? log : []),
    { id: crypto.randomUUID(), data: new Date().toISOString(), ...entry },
  ], []);
}

function verifySignature(req: NextRequest, dataId: string, secret: string) {
  const signature = text(req.headers.get("x-signature"));
  const requestId = text(req.headers.get("x-request-id"));
  if (!secret) return { configured: false, valid: true, reason: "secret_not_configured" };
  if (!signature || !requestId || !dataId) return { configured: true, valid: false, reason: "headers_missing" };
  const { ts, v1 } = parseSignature(signature);
  if (!ts || !v1) return { configured: true, valid: false, reason: "signature_malformed" };
  const manifest = `id:${dataId.toLowerCase()};request-id:${requestId};ts:${ts};`;
  const expected = createHmac("sha256", secret).update(manifest).digest("hex");
  return { configured: true, valid: safeCompareHex(expected, v1), reason: "checked" };
}

export async function GET() {
  return NextResponse.json({ ok: true, endpoint: "mercado-pago-webhook" });
}

export async function POST(req: NextRequest) {
  const url = new URL(req.url);
  const body = await req.json().catch(() => ({})) as Row;
  const data = (body.data || {}) as Row;
  const queryId = text(url.searchParams.get("data.id") || url.searchParams.get("id"));
  const paymentId = queryId || text(data.id);
  if (queryId && data.id && queryId !== text(data.id)) {
    return NextResponse.json({ error: "Identificadores divergentes." }, { status: 400 });
  }
  const topic = lower(body.type || body.topic || url.searchParams.get("type") || url.searchParams.get("topic"));

  if (!paymentId || (topic && !topic.includes("payment"))) {
    return NextResponse.json({ ok: true, ignored: true });
  }

  const config = await dbGet<Row>("boleto_config.json");
  const token = boletoToken(config);
  if (!token) return NextResponse.json({ error: "Mercado Pago Access Token nao configurado." }, { status: 500 });

  const secret = webhookSecret(config);
  if (!secret) {
    await audit({
      acao: "mercado_pago_webhook_sem_chave_secreta",
      mercado_pago_payment_id: paymentId,
    });
    return NextResponse.json({ error: "Configure a chave secreta do webhook Mercado Pago." }, { status: 503 });
  }

  const signature = verifySignature(req, paymentId, secret);
  if (!signature.valid) {
    await audit({
      acao: "mercado_pago_webhook_assinatura_nao_validada",
      mercado_pago_payment_id: paymentId,
      motivo: signature.reason,
    });
    return NextResponse.json({ error: "Assinatura invalida." }, { status: 401 });
  }

  try {
    const result = await syncMercadoPagoPayment(paymentId, "webhook");
    await audit({
      acao: "mercado_pago_webhook_processado",
      mercado_pago_payment_id: paymentId,
      matched: result.matched,
      paid: result.paid,
      status: result.status,
      assinatura_webhook_validada: signature.valid,
    });
    return NextResponse.json({ ok: true, matched: result.matched, paid: result.paid,
      requiresReview: result.requiresReview === true, paymentId, status: result.status });
  } catch (err) {
    console.error("[mercado-pago webhook]", err);
    await audit({
      acao: "mercado_pago_webhook_erro",
      mercado_pago_payment_id: paymentId,
      erro: err instanceof Error ? err.message : String(err),
    });
    return NextResponse.json({ error: "Erro ao processar webhook Mercado Pago." }, { status: 500 });
  }
}
