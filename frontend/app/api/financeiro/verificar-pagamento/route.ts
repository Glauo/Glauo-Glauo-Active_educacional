import { NextRequest, NextResponse } from "next/server";
import { getSession } from "@/lib/auth";
import { dbList } from "@/lib/db";
import { isAdminOrCoordinator } from "@/lib/roles";
import { mercadoPagoPaymentIdFromReceivable, syncMercadoPagoPayment } from "@/lib/mercadopago-sync";

type Row = Record<string, unknown>;

function text(value: unknown) {
  return String(value || "").trim();
}

export async function POST(req: NextRequest) {
  const session = await getSession();
  if (!session || !isAdminOrCoordinator(session)) {
    return NextResponse.json({ error: "Nao autorizado." }, { status: 401 });
  }

  const body = await req.json().catch(() => ({})) as Row;
  const id = text(body.id);
  const paymentIdBody = text(body.payment_id);

  let paymentId = paymentIdBody;
  if (!paymentId && id) {
    const receivables = await dbList<Row>("receivables.json");
    const lancamento = receivables.find((item) => text(item.id) === id);
    if (!lancamento) {
      return NextResponse.json({ error: "Lancamento nao encontrado." }, { status: 404 });
    }
    paymentId = mercadoPagoPaymentIdFromReceivable(lancamento);
  }

  if (!paymentId) {
    return NextResponse.json({ error: "Pagamento Mercado Pago ainda nao vinculado a este lancamento." }, { status: 400 });
  }

  try {
    const result = await syncMercadoPagoPayment(paymentId, "manual", id || undefined);
    return NextResponse.json({
      ok: true,
      matched: result.matched,
      paid: result.paid,
      status: result.status,
      payment_id: result.paymentId,
      lancamento: result.lancamento,
      requires_review: result.requiresReview === true,
      expected_amount: result.expectedAmount,
      actual_amount: result.actualAmount,
      message: !result.matched ? "Pagamento consultado, mas sem vinculo seguro com esta parcela. Nenhuma baixa realizada." : result.requiresReview
        ? "O Mercado Pago aprovou o pagamento, mas o valor esperado esta ausente ou diverge do lancamento. A baixa foi bloqueada e requer conferencia administrativa."
        : result.paid
        ? "Pagamento confirmado e financeiro atualizado."
        : `Pagamento consultado com status ${result.status}.`,
    });
  } catch (err) {
    return NextResponse.json({
      error: err instanceof Error ? err.message : "Erro ao verificar pagamento no Mercado Pago.",
    }, { status: 500 });
  }
}
