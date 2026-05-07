import { AppShell } from "@/components/app-shell";
import { getSession } from "@/lib/auth";
import { dbGet, dbList } from "@/lib/db";
import { redirect } from "next/navigation";

function text(value: unknown) {
  return String(value || "").trim();
}

function badge(value: unknown) {
  const v = text(value).toLowerCase();
  if (v.includes("enviado") || v.includes("ok") || v.includes("success")) return "success";
  if (v.includes("falha") || v.includes("erro")) return "danger";
  if (v.includes("pend") || v.includes("fila")) return "warning";
  return "neutral";
}

export default async function AtendimentoPage() {
  const session = await getSession();
  if (!session) redirect("/login");

  const [logs, leads, sistema] = await Promise.all([
    dbList<Record<string, unknown>>("email_log.json"),
    dbList<Record<string, unknown>>("sales_leads.json"),
    dbGet<Record<string, unknown>>("sistema_config.json"),
  ]);

  const mensagens = logs.slice(-30).reverse();
  const whats = mensagens.filter((l) => text(l.canal || l.origem).toLowerCase().includes("whatsapp") || text(l.whatsapp));
  const email = mensagens.filter((l) => text(l.canal).toLowerCase().includes("email") || text(l.destinatario).includes("@"));
  const wapiOk = Boolean(text(sistema?.WAPI_BASE_URL || sistema?.W_API_URL || sistema?.WAPI_URL) && text(sistema?.WAPI_TOKEN || sistema?.W_API_TOKEN || sistema?.WAPI_API_KEY));
  const userName = session.pessoa || session.usuario;

  return (
    <AppShell breadcrumb="Atendimento" userName={userName} userRole={session.perfil} userUnit={session.unit}>
      <div className="page-header">
        <div className="page-title-block">
          <div className="page-eyebrow"><span className="page-eyebrow-dot" />ATENDIMENTO</div>
          <h1 className="page-title">Painel de Atendimento</h1>
          <p className="page-description">WhatsApp, e-mail, contatos comerciais e historico de envios automáticos.</p>
        </div>
        <div className="page-actions">
          <span className={`badge badge-${wapiOk ? "success" : "warning"}`}><span className="badge-dot" />W-API {wapiOk ? "configurada" : "pendente"}</span>
          <a className="btn btn-secondary" href="/comercial">Comercial</a>
        </div>
      </div>

      <section className="metric-grid metric-grid-3">
        <div className="metric-card"><div className="metric-label">Mensagens registradas</div><div className="metric-value">{logs.length}</div><div className="metric-note">Historico de comunicação</div></div>
        <div className="metric-card metric-card-green"><div className="metric-label">WhatsApp</div><div className="metric-value">{whats.length}</div><div className="metric-note">Envios W-API e manuais</div></div>
        <div className="metric-card metric-card-gold"><div className="metric-label">Leads para atender</div><div className="metric-value">{leads.length}</div><div className="metric-note">{email.length} e-mails no historico recente</div></div>
      </section>

      <section className="card">
        <div className="card-header">
          <div>
            <div className="section-eyebrow">HISTORICO</div>
            <h3 className="section-title">Últimos envios</h3>
            <p className="section-subtitle">Tudo que o sistema enviou ou tentou enviar fica registrado aqui.</p>
          </div>
        </div>
        <div className="card-body" style={{ paddingTop: 0 }}>
          {mensagens.length === 0 ? (
            <div className="empty-state"><div className="empty-title">Sem envios registrados</div><p className="empty-desc">Ao enviar boletos, senhas ou comunicados, o historico aparece aqui.</p></div>
          ) : (
            <table className="data-table">
              <thead><tr><th>Data</th><th>Canal</th><th>Destinatario</th><th>Assunto</th><th>Status</th></tr></thead>
              <tbody>
                {mensagens.map((log, index) => (
                  <tr key={text(log.id) || index}>
                    <td>{text(log.data || log.created_at) || "-"}</td>
                    <td>{text(log.canal || log.origem || "Sistema")}</td>
                    <td>{text(log.destinatario || log.whatsapp || log.email || log.para) || "-"}</td>
                    <td>{text(log.assunto || log.titulo || log.mensagem).slice(0, 80) || "-"}</td>
                    <td><span className={`badge badge-${badge(log.status)}`}><span className="badge-dot" />{text(log.status || "registrado")}</span></td>
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
