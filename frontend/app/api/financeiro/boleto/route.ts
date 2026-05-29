import { NextRequest, NextResponse } from "next/server";
import { getSession } from "@/lib/auth";
import { dbList } from "@/lib/db";

type Row = Record<string, unknown>;

function text(value: unknown) {
  return String(value || "").trim();
}

function money(value: unknown) {
  const n = parseFloat(String(value || "0").replace(/[^\d.,-]/g, "").replace(",", "."));
  return (Number.isFinite(n) ? n : 0).toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
}

export async function GET(req: NextRequest) {
  const session = await getSession();
  if (!session) return NextResponse.json({ error: "Nao autorizado" }, { status: 401 });

  const id = new URL(req.url).searchParams.get("id");
  if (!id) return NextResponse.json({ error: "id obrigatorio" }, { status: 400 });

  const recebimentos = await dbList<Row>("receivables.json");
  const lancamento = recebimentos.find((r) => text(r.id) === id);
  if (!lancamento) return NextResponse.json({ error: "Boleto nao encontrado" }, { status: 404 });

  if (session.perfil === "Aluno" && text(lancamento.aluno || lancamento.nome) !== session.pessoa) {
    return NextResponse.json({ error: "Nao autorizado" }, { status: 403 });
  }

  // Prioridade 1: redirecionar para boleto real do Mercado Pago
  const boletoUrl = text(lancamento.boleto_url);
  if (boletoUrl && boletoUrl.startsWith("http")) {
    return NextResponse.redirect(boletoUrl);
  }

  // Prioridade 2: redirecionar para URL de pagamento Pix
  const pixUrl = text(lancamento.pix_url);
  if (pixUrl && pixUrl.startsWith("http")) {
    return NextResponse.redirect(pixUrl);
  }

  // Prioridade 3: PDF importado
  const pdfUrl = text(lancamento.boleto_pdf_url || lancamento.boleto_pdf_public_url);
  if (pdfUrl && pdfUrl.startsWith("/api/")) {
    return NextResponse.redirect(new URL(pdfUrl, req.url));
  }

  // Prioridade 4: exibir pagina com linha digitavel e Pix copia-e-cola
  const codigo = text(lancamento.boleto_codigo) || `AE-${id.slice(0, 8).toUpperCase()}`;
  const linhaDigitavel = text(lancamento.boleto_linha_digitavel);
  const pixQrCode = text(lancamento.pix_qr_code);
  const pixQrImageB64 = text(lancamento.pix_qr_image_b64);
  const boletoStatus = text(lancamento.boleto_status);
  const mpPaymentId = text(lancamento.mp_payment_id);
  const mpStatus = text(lancamento.mp_status);
  const mpErro = text(lancamento.boleto_erro);

  const linhaSection = linhaDigitavel
    ? `<div class="bar">${linhaDigitavel}</div><p style="text-align:center;font-size:12px;color:#64748b">Linha digitavel - copie e pague em qualquer banco</p>`
    : `<div class="bar">${codigo.replace(/-/g, " ")} ${String(lancamento.valor || "0").replace(/\D/g, "").padStart(8, "0")}</div>`;

  const pixSection = pixQrCode
    ? `<div style="margin-top:24px;padding:16px;background:#f0fdf4;border-radius:8px;border:1px solid #bbf7d0"><div class="muted" style="margin-bottom:8px">Pix copia e cola</div><textarea readonly onclick="this.select()" style="width:100%;font-size:12px;padding:8px;border:1px solid #ccc;border-radius:4px;resize:none;height:64px">${pixQrCode}</textarea>${pixQrImageB64 ? `<div style="text-align:center;margin-top:12px"><img src="data:image/png;base64,${pixQrImageB64}" style="max-width:200px" alt="QR Code Pix"/></div>` : ""}</div>`
    : "";

  let avisoHtml = "";
  if (boletoStatus === "Erro MP" && mpErro) {
    avisoHtml = `<div style="margin-top:16px;padding:12px;background:#fef2f2;border:1px solid #fca5a5;border-radius:6px;font-size:13px">Erro ao gerar boleto no Mercado Pago: <strong>${mpErro}</strong><br>Entre em contato com a secretaria.</div>`;
  } else if (!boletoUrl && !linhaDigitavel && !pixQrCode) {
    avisoHtml = `<div style="margin-top:16px;padding:12px;background:#fef9c3;border:1px solid #fde047;border-radius:6px;font-size:13px">O boleto bancario ainda nao foi gerado. Entre em contato para solicitar a segunda via.</div>`;
  }

  const mpInfoHtml = mpPaymentId
    ? `<div style="margin-top:12px;padding:10px;background:#eff6ff;border:1px solid #bfdbfe;border-radius:6px;font-size:12px;color:#1e40af"><strong>Mercado Pago</strong> - Payment ID: ${mpPaymentId} | Status: ${mpStatus || "pending"}</div>`
    : "";

  const html = `<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Boleto ${codigo}</title><style>
    body{font-family:Arial,sans-serif;margin:40px;color:#172033} .box{border:2px solid #172033;padding:24px;border-radius:10px;max-width:760px;margin:auto}
    h1{margin:0 0 8px;font-size:24px}.muted{color:#64748b;font-size:12px;text-transform:uppercase;letter-spacing:.08em}
    .grid{display:grid;grid-template-columns:1fr 1fr;gap:14px;margin-top:24px}.value{font-weight:700;font-size:18px}
    .bar{font-family:monospace;font-size:16px;letter-spacing:2px;border:1px dashed #64748b;padding:18px;text-align:center;margin-top:24px;word-break:break-all}
    @media print{button{display:none}}
  </style></head><body><div class="box">
    <div class="muted">Ativo Educacional - Boleto / Fatura</div><h1>${text(lancamento.descricao) || "Mensalidade escolar"}</h1>
    <div class="grid">
      <div><div class="muted">Aluno</div><div class="value">${text(lancamento.aluno || lancamento.nome)}</div></div>
      <div><div class="muted">Vencimento</div><div class="value">${text(lancamento.vencimento || lancamento.data_vencimento)}</div></div>
      <div><div class="muted">Valor</div><div class="value">${money(lancamento.valor_parcela || lancamento.valor)}</div></div>
      <div><div class="muted">Status</div><div class="value">${text(lancamento.boleto_status || lancamento.status) || "Em aberto"}</div></div>
    </div>
    ${linhaSection}
    ${pixSection}
    ${mpInfoHtml}
    ${avisoHtml}
    <p style="margin-top:20px;font-size:12px;color:#64748b">Documento gerado pelo sistema Ativo Educacional. Use a opcao imprimir do navegador para salvar em PDF.</p>
    <button onclick="window.print()">Gerar PDF</button>
  </div></body></html>`;

  return new NextResponse(html, { headers: { "content-type": "text/html; charset=utf-8" } });
}
