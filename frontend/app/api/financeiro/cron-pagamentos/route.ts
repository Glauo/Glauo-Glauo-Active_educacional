import { timingSafeEqual } from "crypto";
import { NextRequest, NextResponse } from "next/server";
import { reconcileMercadoPagoPendingReceivables } from "@/lib/mercadopago-sync";

export const dynamic = "force-dynamic";

function secretMatches(received: string, expected: string) {
  const left = Buffer.from(received);
  const right = Buffer.from(expected);
  return left.length === right.length && timingSafeEqual(left, right);
}

export async function POST(req: NextRequest) {
  const expected = process.env.CRON_SECRET || process.env.ACTIVE_CRON_SECRET || "";
  const received = req.headers.get("x-cron-secret") || "";
  if (expected.length < 32 || !received || !secretMatches(received, expected)) {
    return NextResponse.json({ error: "Nao autorizado." }, { status: 401 });
  }

  try {
    const result = await reconcileMercadoPagoPendingReceivables({ limit: 12, minIntervalMs: 0, lockMs: 120_000 });
    return NextResponse.json({ ok: true, ...result, executado_em: new Date().toISOString() }, {
      headers: { "Cache-Control": "no-store" },
    });
  } catch (error) {
    console.error("[financeiro/cron-pagamentos]", error);
    return NextResponse.json({ error: "Falha na conferencia automatica Mercado Pago." }, { status: 500 });
  }
}
