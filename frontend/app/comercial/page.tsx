import { AppShell } from "@/components/app-shell";
import { getSession } from "@/lib/auth";
import { dbList } from "@/lib/db";
import { redirect } from "next/navigation";

function text(value: unknown) {
  return String(value || "").trim();
}

function phoneLink(value: unknown, message: string) {
  const digits = text(value).replace(/\D/g, "");
  return digits ? `https://wa.me/${digits}?text=${encodeURIComponent(message)}` : "";
}

function status(value: unknown) {
  const s = text(value || "Novo");
  const lower = s.toLowerCase();
  if (lower.includes("matric") || lower.includes("convert")) return "success";
  if (lower.includes("perd") || lower.includes("cancel")) return "danger";
  if (lower.includes("agenda") || lower.includes("negocia")) return "warning";
  return "neutral";
}

export default async function ComercialPage() {
  const session = await getSession();
  if (!session) redirect("/login");

  const [leads, agenda, pagamentos] = await Promise.all([
    dbList<Record<string, unknown>>("sales_leads.json"),
    dbList<Record<string, unknown>>("sales_agenda.json"),
    dbList<Record<string, unknown>>("sales_payments.json"),
  ]);

  const recentes = leads.slice(-20).reverse();
  const pendentes = leads.filter((l) => !/matric|convert|perd|cancel/i.test(text(l.status || l.etapa || l.situacao))).length;
  const agendados = agenda.filter((a) => !/feito|conclu|cancel/i.test(text(a.status || a.situacao))).length;
  const userName = session.pessoa || session.usuario;

  return (
    <AppShell breadcrumb="Comercial" userName={userName} userRole={session.perfil} userUnit={session.unit}>
      <div className="page-header">
        <div className="page-title-block">
          <div className="page-eyebrow"><span className="page-eyebrow-dot" />COMERCIAL</div>
          <h1 className="page-title">Painel Comercial</h1>
          <p className="page-description">Leads, atendimentos, agenda comercial e conversoes recuperados do sistema anterior.</p>
        </div>
        <div className="page-actions">
          <a className="btn btn-secondary" href="/atendimento">Atendimento</a>
        </div>
      </div>

      <section className="metric-grid metric-grid-3">
        <div className="metric-card"><div className="metric-label">Leads cadastrados</div><div className="metric-value">{leads.length}</div><div className="metric-note">Base comercial ativa</div></div>
        <div className="metric-card metric-card-gold"><div className="metric-label">Pendentes</div><div className="metric-value">{pendentes}</div><div className="metric-note">Precisam de retorno</div></div>
        <div className="metric-card metric-card-green"><div className="metric-label">Agenda aberta</div><div className="metric-value">{agendados}</div><div className="metric-note">{pagamentos.length} registros financeiros comerciais</div></div>
      </section>

      <section className="card">
        <div className="card-header">
          <div>
            <div className="section-eyebrow">LEADS</div>
            <h3 className="section-title">Últimos contatos</h3>
            <p className="section-subtitle">Acompanhamento comercial para matriculas e retornos.</p>
          </div>
        </div>
        <div className="card-body" style={{ paddingTop: 0 }}>
          {recentes.length === 0 ? (
            <div className="empty-state"><div className="empty-title">Nenhum lead encontrado</div><p className="empty-desc">Quando houver cadastro comercial, ele aparece aqui.</p></div>
          ) : (
            <table className="data-table">
              <thead><tr><th>Nome</th><th>Telefone</th><th>Interesse</th><th>Status</th><th>Responsavel</th><th>Acoes</th></tr></thead>
              <tbody>
                {recentes.map((lead, index) => {
                  const nome = text(lead.nome || lead.name || lead.aluno || lead.cliente || `Lead ${index + 1}`);
                  const telefone = text(lead.telefone || lead.whatsapp || lead.celular);
                  const interesse = text(lead.interesse || lead.curso || lead.modulo || lead.observacao || "-");
                  const st = text(lead.status || lead.etapa || lead.situacao || "Novo");
                  const msg = `Ola ${nome}! Aqui e da Active Educacional. Estamos entrando em contato sobre: ${interesse}.`;
                  return (
                    <tr key={text(lead.id) || `${nome}-${index}`}>
                      <td><div className="table-name-cell"><span className="table-name-primary">{nome}</span><span className="table-name-secondary">{text(lead.email)}</span></div></td>
                      <td>{telefone || "-"}</td>
                      <td>{interesse}</td>
                      <td><span className={`badge badge-${status(st)}`}><span className="badge-dot" />{st}</span></td>
                      <td>{text(lead.vendedor || lead.responsavel || lead.atendente) || "-"}</td>
                      <td>{phoneLink(telefone, msg) ? <a className="btn btn-secondary btn-sm" href={phoneLink(telefone, msg)} target="_blank" rel="noreferrer">WhatsApp</a> : <span className="muted">-</span>}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          )}
        </div>
      </section>

      <section className="card">
        <div className="card-header">
          <div>
            <div className="section-eyebrow">AGENDA</div>
            <h3 className="section-title">Retornos e visitas</h3>
          </div>
        </div>
        <div className="card-body" style={{ paddingTop: 0 }}>
          {agenda.length === 0 ? (
            <div className="empty-state"><div className="empty-title">Sem agenda comercial</div><p className="empty-desc">Os compromissos comerciais importados aparecem aqui.</p></div>
          ) : (
            <table className="data-table">
              <thead><tr><th>Data</th><th>Cliente</th><th>Tipo</th><th>Status</th><th>Observacao</th></tr></thead>
              <tbody>
                {agenda.slice(-12).reverse().map((item, index) => (
                  <tr key={text(item.id) || index}>
                    <td>{text(item.data || item.date || item.inicio) || "-"}</td>
                    <td>{text(item.nome || item.cliente || item.aluno) || "-"}</td>
                    <td>{text(item.tipo || item.assunto || item.categoria) || "-"}</td>
                    <td><span className={`badge badge-${status(item.status || item.situacao)}`}><span className="badge-dot" />{text(item.status || item.situacao || "Aberto")}</span></td>
                    <td>{text(item.observacao || item.obs || item.descricao) || "-"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </section>
    </AppShell>
  );
}
