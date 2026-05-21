function text(value: unknown) {
  return String(value || "").trim();
}

function normalize(value: unknown) {
  return text(value)
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase();
}

function money(value: unknown) {
  const n = Number.parseFloat(text(value).replace(/[^\d,.-]/g, "").replace(/\./g, "").replace(",", ".")) || 0;
  return n.toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
}

function financeCategory(row: Record<string, unknown>) {
  const raw = normalize(row.tipo_lancamento_detalhe || row.categoria || row.descricao || row.boleto_status);
  if (raw.includes("matric")) return "matricula";
  if (raw.includes("mensal")) return "mensalidade";
  if (raw.includes("material") || raw.includes("livro") || raw.includes("apostila")) return "material";
  if (raw.includes("reneg") || raw.includes("acordo")) return "renegociacao";
  if (raw.includes("avulsa") || raw.includes("avulso")) return "aula_avulsa";
  if (raw.includes("repos")) return "reposicao";
  if (raw.includes("evento")) return "evento";
  if (raw.includes("boleto")) return "boleto";
  return "outros";
}

function categoryTitle(category: string) {
  const titles: Record<string, string> = {
    matricula: "Matricula",
    mensalidade: "Mensalidade",
    material: "Material didatico",
    renegociacao: "Renegociacao financeira",
    aula_avulsa: "Aula avulsa",
    reposicao: "Reposicao de aula",
    evento: "Evento",
    boleto: "Boleto importado",
    outros: "Lancamento financeiro",
  };
  return titles[category] || titles.outros;
}

function introFor(category: string) {
  const intros: Record<string, string> = {
    matricula: "Informamos que a cobranca de matricula foi lancada no sistema.",
    mensalidade: "Informamos que a mensalidade foi lancada no sistema.",
    material: "Informamos que a cobranca de material didatico foi lancada no sistema.",
    renegociacao: "Informamos que a renegociacao financeira foi registrada no sistema.",
    aula_avulsa: "Informamos que a cobranca referente a aula avulsa foi lancada no sistema.",
    reposicao: "Informamos que a cobranca referente a reposicao de aula foi lancada no sistema.",
    evento: "Informamos que a cobranca referente ao evento foi lancada no sistema.",
    boleto: "Informamos que o boleto/fatura foi anexado e esta disponivel para pagamento.",
    outros: "Informamos que um lancamento financeiro foi registrado no sistema.",
  };
  return intros[category] || intros.outros;
}

export function financeMessage(row: Record<string, unknown>, origin = "") {
  const id = text(row.id);
  const pdfUrl = text(row.boleto_pdf_url || row.boleto_pdf_public_url);
  const link = pdfUrl
    ? (pdfUrl.startsWith("http") ? pdfUrl : `${origin}${pdfUrl}`)
    : (id ? `${origin}/api/financeiro/boleto?id=${encodeURIComponent(id)}` : origin);
  const category = financeCategory(row);
  const title = categoryTitle(category);
  const aluno = text(row.aluno || row.nome || "Aluno");
  const referencia = text(row.descricao || title);
  const parcela = text(row.parcela);
  const vencimento = text(row.vencimento || row.data_vencimento);
  const status = text(row.status || row.situacao);
  const subject = `${title} Active Educacional - ${referencia || aluno}`;
  const lines = [
    `Ola, ${aluno}!`,
    "",
    introFor(category),
    "",
    `Referencia: ${referencia}`,
    parcela ? `Parcela: ${parcela}` : "",
    `Valor: ${money(row.valor_parcela || row.valor || row.valor_total)}`,
    vencimento ? `Vencimento: ${vencimento}` : "",
    status ? `Status: ${status}` : "",
    "",
    link ? `Acesse aqui: ${link}` : "",
    "",
    "Em caso de duvida, fale com a secretaria da Active Educacional.",
  ].filter((line) => line !== "");

  return { subject, body: lines.join("\n") };
}
