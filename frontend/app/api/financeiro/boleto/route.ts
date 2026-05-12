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

  const codigo = text(lancamento.boleto_codigo) || `AE-${id.slice(0, 8).toUpperCase()}`;
  const html = `<!doctype html><html><head><meta charset="utf-8"><title>Boleto ${codigo}</title><style>
    body{font-family:Arial,sans-serif;margin:40px;color:#172033} .box{border:2px solid #172033;padding:24px;border-radius:10px;max-width:760px;margin:auto}
    h1{margin:0 0 8px;font-size:24px}.muted{color:#64748b;font-size:12px;text-transform:uppercase;letter-spacing:.08em}
    .grid{display:grid;grid-template-columns:1fr 1fr;gap:14px;margin-top:24px}.value{font-weight:700;font-size:18px}.bar{font-family:monospace;font-size:22px;letter-spacing:3px;border:1px dashed #64748b;padding:18px;text-align:center;margin-top:24px}
    @media print{button{display:none}}
  </style></head><body><div class="box">
    <div class="muted">Ativo Educacional - Boleto / Fatura</div><h1>${text(lancamento.descricao) || "Mensalidade escolar"}</h1>
    <div class="grid"><div><div class="muted">Aluno</div><div class="value">${text(lancamento.aluno || lancamento.nome)}</div></div>
    <div><div class="muted">Vencimento</div><div class="value">${text(lancamento.vencimento || lancamento.data_vencimento)}</div></div>
    <div><div class="muted">Valor</div><div class="value">${money(lancamento.valor)}</div></div>
    <div><div class="muted">Codigo</div><div class="value">${codigo}</div></div></div>
    <div class="bar">${codigo.replace(/-/g, " ")} ${String(lancamento.valor || "0").replace(/\D/g, "").padStart(8, "0")}</div>
    <p>Documento gerado pelo sistema Ativo Educacional. Use a opcao imprimir do navegador para salvar em PDF.</p>
    <button onclick="window.print()">Gerar PDF</button>
  </div></body></html>`;

  return new NextResponse(html, { headers: { "content-type": "text/html; charset=utf-8" } });
}
