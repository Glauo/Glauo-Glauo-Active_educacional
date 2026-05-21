import { AppShell } from "@/components/app-shell";
import { ComercialCrm } from "@/components/comercial-crm";
import { getSession } from "@/lib/auth";
import {
  SALES_AGENDA_KEY,
  SALES_LEADS_KEY,
  canManageCommercial,
  leadStage,
  leadStatus,
  text,
  type CommercialAgendaItem,
  type CommercialLead,
} from "@/lib/comercial";
import { dbList } from "@/lib/db";
import { redirect } from "next/navigation";

export default async function ComercialPage() {
  const session = await getSession();
  if (!session) redirect("/login");
  if (!canManageCommercial(session.perfil)) redirect("/");

  const [leads, agenda, pagamentos] = await Promise.all([
    dbList<CommercialLead>(SALES_LEADS_KEY),
    dbList<CommercialAgendaItem>(SALES_AGENDA_KEY),
    dbList<Record<string, unknown>>("sales_payments.json"),
  ]);

  const pendentes = leads.filter((lead) => !/fech|desist|descart/i.test(`${leadStatus(lead)} ${leadStage(lead)}`)).length;
  const quentes = leads.filter((lead) => /quente|negocia|fechamento/i.test(`${leadStatus(lead)} ${leadStage(lead)}`)).length;
  const agendados = agenda.filter((item) => !/conclu|cancel/i.test(text(item.status || item.situacao))).length;
  const userName = session.pessoa || session.usuario;

  return (
    <AppShell breadcrumb="Comercial" userName={userName} userRole={session.perfil} userUnit={session.unit}>
      <div className="page-header">
        <div className="page-title-block">
          <div className="page-eyebrow"><span className="page-eyebrow-dot" />COMERCIAL</div>
          <h1 className="page-title">Painel Comercial</h1>
          <p className="page-description">Funil de vendas, contatos e retornos comerciais no fluxo operacional do Active.</p>
        </div>
        <div className="page-actions">
          <a className="btn btn-secondary" href="/atendimento">Atendimento</a>
        </div>
      </div>

      <section className="metric-grid metric-grid-3">
        <div className="metric-card"><div className="metric-label">Leads cadastrados</div><div className="metric-value">{leads.length}</div><div className="metric-note">Base comercial ativa</div></div>
        <div className="metric-card metric-card-gold"><div className="metric-label">Pendentes</div><div className="metric-value">{pendentes}</div><div className="metric-note">Precisam de continuidade</div></div>
        <div className="metric-card metric-card-green"><div className="metric-label">Agenda aberta</div><div className="metric-value">{agendados}</div><div className="metric-note">{quentes} oportunidades quentes | {pagamentos.length} registros financeiros</div></div>
      </section>

      <ComercialCrm leads={leads} agenda={agenda} seller={userName} />
    </AppShell>
  );
}
