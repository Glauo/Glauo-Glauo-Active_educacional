import { AppShell } from "@/components/app-shell";
import { dbList } from "@/lib/db";
import { getSession } from "@/lib/auth";
import { redirect } from "next/navigation";

type WizLog = { id?: string; acao?: string; action?: string; resultado?: string; result?: string; usuario?: string; user?: string; data?: string; date?: string; status?: string; tipo?: string; [k: string]: unknown };

export default async function WizPage() {
  const session = await getSession();
  if (!session) redirect("/login");

  const logs = await dbList<WizLog>("wiz_action_audit.json");
  const chatLogs = await dbList<Record<string, unknown>>("chatbot_active_log.json");

  const hoje = new Date();
  const logsHoje = logs.filter((l) => {
    const d = l.data || l.date;
    if (!d) return false;
    return new Date(String(d)).toDateString() === hoje.toDateString();
  });

  const sucesso = logs.filter((l) => {
    const s = String(l.status || l.resultado || "").toLowerCase();
    return s.includes("ok") || s.includes("sucess") || s.includes("conclu");
  });

  return (
    <AppShell breadcrumb="Wiz IA" userName={session.pessoa || session.usuario} userRole={session.perfil}>
      <div className="page-header">
        <div className="page-title-block">
          <div className="page-eyebrow"><span className="page-eyebrow-dot" />Assistente Operacional</div>
          <h1 className="page-title">Wiz IA</h1>
          <p className="page-description">
            Assistente inteligente para automações, comunicação com alunos e suporte operacional.
          </p>
        </div>
        <div className="page-actions">
          <div className="badge badge-neutral">
            <span className="badge-dot" />
            {session.perfil === "Admin" ? "Acesso total" : "Acesso limitado"}
          </div>
        </div>
      </div>

      <div className="metric-grid metric-grid-3">
        <div className="metric-card metric-card-blue">
          <div className="metric-icon metric-icon-blue">
            <svg viewBox="0 0 20 20" fill="currentColor">
              <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-8-3a1 1 0 00-.867.5 1 1 0 11-1.731-1A3 3 0 0113 8a3.001 3.001 0 01-2 2.83V11a1 1 0 11-2 0v-1a1 1 0 011-1 1 1 0 100-2zm0 8a1 1 0 100-2 1 1 0 000 2z" clipRule="evenodd" />
            </svg>
          </div>
          <div className="metric-label">Ações totais</div>
          <div className="metric-value">{logs.length}</div>
          <div className="metric-note">{logsHoje.length} executadas hoje</div>
        </div>
        <div className="metric-card metric-card-green">
          <div className="metric-icon metric-icon-green">
            <svg viewBox="0 0 20 20" fill="currentColor">
              <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
            </svg>
          </div>
          <div className="metric-label">Sucesso</div>
          <div className="metric-value">{sucesso.length}</div>
          <div className="metric-note">Ações concluídas com êxito</div>
        </div>
        <div className="metric-card metric-card-gold">
          <div className="metric-icon metric-icon-gold">
            <svg viewBox="0 0 20 20" fill="currentColor">
              <path d="M2 5a2 2 0 012-2h7a2 2 0 012 2v4a2 2 0 01-2 2H9l-3 3v-3H4a2 2 0 01-2-2V5z" />
              <path d="M15 7v2a4 4 0 01-4 4H9.828l-1.766 1.767c.28.149.599.233.938.233h2l3 3v-3h2a2 2 0 002-2V9a2 2 0 00-2-2h-1z" />
            </svg>
          </div>
          <div className="metric-label">Conversas</div>
          <div className="metric-value">{chatLogs.length}</div>
          <div className="metric-note">Interações no chatbot</div>
        </div>
      </div>

      <div className="content-grid grid-2-1">
        {/* Log de ações */}
        <div className="card">
          <div className="card-header">
            <div>
              <div className="section-eyebrow">Auditoria</div>
              <h3 className="section-title">Histórico de ações do Wiz</h3>
              <p className="section-subtitle">{logs.length} ações registradas</p>
            </div>
          </div>
          <div className="card-body" style={{ paddingTop: "12px" }}>
            {logs.length === 0 ? (
              <div className="empty-state">
                <div className="empty-icon">
                  <svg viewBox="0 0 20 20" fill="currentColor">
                    <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-8-3a1 1 0 00-.867.5 1 1 0 11-1.731-1A3 3 0 0113 8a3.001 3.001 0 01-2 2.83V11a1 1 0 11-2 0v-1a1 1 0 011-1 1 1 0 100-2zm0 8a1 1 0 100-2 1 1 0 000 2z" clipRule="evenodd" />
                  </svg>
                </div>
                <div className="empty-title">Nenhuma ação registrada</div>
                <p className="empty-desc">As ações do Wiz são registradas automaticamente quando o assistente executa tarefas no sistema.</p>
              </div>
            ) : (
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Ação</th>
                    <th>Usuário</th>
                    <th>Data</th>
                    <th>Status</th>
                  </tr>
                </thead>
                <tbody>
                  {logs.slice(-20).reverse().map((l, i) => {
                    const acao = String(l.acao || l.action || l.tipo || `Ação ${i + 1}`);
                    const usuario = String(l.usuario || l.user || "Sistema");
                    const data = l.data || l.date;
                    const dataStr = data
                      ? new Date(String(data)).toLocaleString("pt-BR", { day: "2-digit", month: "2-digit", hour: "2-digit", minute: "2-digit" })
                      : "—";
                    const status = String(l.status || l.resultado || "—");
                    const isOk = status.toLowerCase().includes("ok") || status.toLowerCase().includes("sucess") || status.toLowerCase().includes("conclu");
                    return (
                      <tr key={String(l.id || i)}>
                        <td>
                          <div className="table-name-cell">
                            <span className="table-name-primary">{acao}</span>
                            {l.resultado && l.resultado !== l.status && (
                              <span className="table-name-secondary">{String(l.resultado).slice(0, 60)}</span>
                            )}
                          </div>
                        </td>
                        <td>{usuario}</td>
                        <td style={{ color: "var(--text-muted)", fontSize: "0.8125rem" }}>{dataStr}</td>
                        <td>
                          <span className={`badge badge-${isOk ? "success" : status === "—" ? "neutral" : "warning"}`}>
                            <span className="badge-dot" />{status.length > 20 ? status.slice(0, 20) + "…" : status}
                          </span>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            )}
          </div>
        </div>

        {/* Painel de controle */}
        <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
          <div className="card card-hero">
            <div className="card-body">
              <div className="section-eyebrow">Automações</div>
              <h3 className="section-title" style={{ marginBottom: "16px" }}>Gatilhos configurados</h3>
              <div className="spotlight-list">
                {[
                  { label: "Aluno criado", key: "on_student_created" },
                  { label: "Professor criado", key: "on_teacher_created" },
                  { label: "Financeiro criado", key: "on_financial_created" },
                  { label: "Agenda criada", key: "on_agenda_created" },
                  { label: "Nota aprovada", key: "on_grade_approved" }
                ].map((item) => (
                  <div className="spotlight-row" key={item.key}>
                    <span className="spotlight-label">{item.label}</span>
                    <span className="badge badge-success"><span className="badge-dot" />Ativo</span>
                  </div>
                ))}
              </div>
            </div>
          </div>

          <div className="card">
            <div className="card-body">
              <div className="section-eyebrow">Canais</div>
              <h3 className="section-title" style={{ marginBottom: "16px" }}>Notificações</h3>
              <div className="spotlight-list">
                <div className="spotlight-row">
                  <span className="spotlight-label">WhatsApp</span>
                  <span className="badge badge-neutral"><span className="badge-dot" />Verificar</span>
                </div>
                <div className="spotlight-row">
                  <span className="spotlight-label">E-mail</span>
                  <span className="badge badge-neutral"><span className="badge-dot" />Verificar</span>
                </div>
                <div className="spotlight-row">
                  <span className="spotlight-label">Total de ações hoje</span>
                  <span className="spotlight-value">{logsHoje.length}</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </AppShell>
  );
}
