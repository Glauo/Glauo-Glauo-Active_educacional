/**
 * Integração com a API do Mercado Pago — Boleto Bancário
 * Documentação: https://www.mercadopago.com.br/developers/pt/docs
 *
 * O Access Token é lido na seguinte ordem de prioridade:
 *  1. Variável de ambiente MP_ACCESS_TOKEN ou MERCADOPAGO_ACCESS_TOKEN
 *  2. Campo mp_access_token salvo em boleto_config.json (via tela de Configurações)
 *  3. Token padrão embutido (fallback)
 */

import { dbGet } from "@/lib/db";

export interface MpBoletoInput {
  transaction_amount: number;
  description: string;
  payer_email: string;
  payer_first_name?: string;
  payer_last_name?: string;
  payer_cpf?: string;
  date_of_expiration?: string; // ISO 8601: "2025-06-10T23:59:59.000-03:00"
  external_reference?: string;
  notification_url?: string;
}

export interface MpBoletoResult {
  ok: boolean;
  payment_id?: number;
  status?: string;
  status_detail?: string;
  boleto_url?: string;
  barcode?: string;
  date_of_expiration?: string;
  error?: string;
  raw?: unknown;
}

const DEFAULT_ACCESS_TOKEN =
  "APP_USR-4713753450558393-052911-fe06bce27704ad491468ea178b863b04-3424597237";

async function getAccessToken(): Promise<string> {
  // 1. Variável de ambiente
  const envToken =
    process.env.MP_ACCESS_TOKEN || process.env.MERCADOPAGO_ACCESS_TOKEN;
  if (envToken) return envToken;

  // 2. Configuração salva no banco de dados
  try {
    const boletoConfig = await dbGet<Record<string, unknown>>("boleto_config.json");
    const dbToken = String(boletoConfig?.mp_access_token || "").trim();
    if (dbToken && dbToken.startsWith("APP_USR")) return dbToken;
  } catch {
    // ignora erro de leitura do banco
  }

  // 3. Fallback: token padrão
  return DEFAULT_ACCESS_TOKEN;
}

/**
 * Cria um boleto bancário via API do Mercado Pago.
 * Retorna a URL do boleto (external_resource_url) e o código de barras.
 */
export async function criarBoleteMercadoPago(input: MpBoletoInput): Promise<MpBoletoResult> {
  const accessToken = await getAccessToken();

  // Data de expiração padrão: 3 dias a partir de hoje
  const expiration =
    input.date_of_expiration ||
    (() => {
      const d = new Date();
      d.setDate(d.getDate() + 3);
      d.setHours(23, 59, 59, 0);
      const offset = "-03:00";
      const pad = (n: number) => String(n).padStart(2, "0");
      return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}.000${offset}`;
    })();

  const cpfLimpo = (input.payer_cpf || "00000000000").replace(/\D/g, "");
  const cpfFinal = cpfLimpo.length >= 11 ? cpfLimpo.slice(0, 11) : cpfLimpo.padEnd(11, "0");

  const body: Record<string, unknown> = {
    transaction_amount: Number(input.transaction_amount.toFixed(2)),
    description: input.description.slice(0, 255),
    payment_method_id: "bolbradesco",
    date_of_expiration: expiration,
    payer: {
      email: input.payer_email || "pagador@activeeducacional.com.br",
      first_name: (input.payer_first_name || "Responsavel").slice(0, 60),
      last_name: (input.payer_last_name || "Financeiro").slice(0, 60),
      identification: {
        type: "CPF",
        number: cpfFinal,
      },
    },
  };

  if (input.external_reference) {
    body.external_reference = input.external_reference;
  }
  if (input.notification_url) {
    body.notification_url = input.notification_url;
  }

  const idempotencyKey = `ae-boleto-${input.external_reference || Date.now()}-${Math.random().toString(36).slice(2, 10)}`;

  try {
    const res = await fetch("https://api.mercadopago.com/v1/payments", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${accessToken}`,
        "X-Idempotency-Key": idempotencyKey,
      },
      body: JSON.stringify(body),
    });

    const data = (await res.json()) as Record<string, unknown>;

    if (!res.ok) {
      const cause = Array.isArray(data.cause)
        ? (data.cause as Array<Record<string, unknown>>).map((c) => c.description || c.code).join("; ")
        : "";
      const errMsg = String(data.message || data.error || `HTTP ${res.status}`) + (cause ? ` (${cause})` : "");
      console.error("[MercadoPago] Erro ao criar boleto:", errMsg, data);
      return { ok: false, error: errMsg, raw: data };
    }

    const txDetails = (data.transaction_details as Record<string, unknown>) || {};
    const boletoUrl = String(txDetails.external_resource_url || "");
    const barcode = String(
      (txDetails.barcode as Record<string, unknown> | undefined)?.content ||
      txDetails.payment_method_reference_id ||
      ""
    );

    return {
      ok: true,
      payment_id: Number(data.id),
      status: String(data.status || "pending"),
      status_detail: String(data.status_detail || ""),
      boleto_url: boletoUrl,
      barcode,
      date_of_expiration: String(data.date_of_expiration || expiration),
      raw: data,
    };
  } catch (err) {
    const errMsg = err instanceof Error ? err.message : "Erro desconhecido";
    console.error("[MercadoPago] Excecao ao criar boleto:", errMsg);
    return { ok: false, error: errMsg };
  }
}
