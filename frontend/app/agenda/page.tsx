import { AppShell } from "@/components/app-shell";
import { dbList } from "@/lib/db";
import { getSession } from "@/lib/auth";
import { redirect } from "next/navigation";
import { NovoEventoBtn, EditarEventoBtn } from "@/components/agenda-modal";

type Evento = { id?: string; titulo?: string; descricao?: string; turma?: string; professor?: string; horario?: string; hora?: string; time?: string; data?: string; date?: string; dia?: string; status?: string; tipo?: string; [k: string]: unknown };

function dotClass(status: string) {
  const l = status.toLowerCase();
  if (l.includes("conclu")) return "timeline-dot-done";
  if (l.includes("andamento")) return "timeline-dot-active";
  if (l.includes("atenc") || l.includes("confirm")) return "timeline-dot-warn";
  return "";
}

function statusBadge(s: string) {
  const l = s.toLowerCase();
  if (l.includes("conclu")) return "success";
  if (l.includes("andamento")) return "info";
  return "warning";
}

export default async function AgendaPage() {
  const session = await getSession();
  if (!session) redirect("/login");

  const agenda = await dbList<Evento>("agenda.json");

  const hoje = new Date();
  hoje.setHours(0, 0, 0, 0);

  const agendaHoje = agenda.filter((e) => {
    const d = e.data || e.date || e.dia;
    if (!d) return false;
    const dt = new Date(String(d));
    return dt.toDateString() === hoje.toDateString();
  });

  const agendaSemana = agenda.filter((e) => {
    const d = e.data || e.date || e.dia;
    if (!d) return false;
    const dt = new Date(String(d));
    const fim = new Date(hoje);
    fim.setDate(fim.getDate() + 7);
    return dt >= hoje && dt <= fim;
  });

  const pendentes = agenda.filter((e) => {
    const s = String(e.status || "").toLowerCase();
    return s.includes("pendent") || s.includes("confirm") || s === "";
  });

  const exibir = agendaHoje.length > 0 ? agendaHoje : agenda.slice(0, 10);

  return (
    <AppShell breadcrumb="Agenda" userName={session.pessoa || session.usuario} userRole={session.perfil}>
      <div className="page-header">
        <div className="page-title-block">
          <div className="page-eyebrow"><span className="page-eyebrow-dot" />Operação Diária</div>
          <h1 className="page-title">Agenda</h1>
          <p className="page-description">
            Central de operação — aulas, compromissos e fechamento de aula com registro de lição.
          </p>
        </div>
        <div className="page-actions">
          <span style={{ fontSize: "0.8125rem", color: "var(--text-muted)", fontWeight: 600 }}>
            {hoje.toLocaleDateString("pt-BR", { weekday: "long", day: "2-digit", month: "long" })}
          </span>
          <NovoEventoBtn />
        </div>
      </div>

      <div className="metric-grid metric-grid-3">
        <div className="metric-card metric-card-blue">
          <div className="metric-icon metric-icon-blue">
            <svg viewBox="0 0 20 20" fill="currentColor"><path fillRule="evenodd" d="M6 2a1 1 0 00-1 1v1H4a2 2 0 00-2 2v10a2 2 0 002 2h12a2 2 0 002-2V6a2 2 0 00-2-2h-1V3a1 1 0 10-2 0v1H7V3a1 1 0 00-1-1zm0 5a1 1 0 000 2h8a1 1 0 100-2H6z" clipRule="evenodd" /></svg>
          </div>
          <div className="metric-label">Eventos hoje</div>
          <div className="metric-value">{agendaHoje.length}</div>
          <div className="metric-note">Registrados para hoje</div>
        </div>
        <div className="metric-card metric-card-green">
          <div className="metric-icon metric-icon-green">
            <svg viewBox="0 0 20 20" fill="currentColor"><path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" /></svg>
          </div>
          <div className="metric-label">Esta semana</div>
          <div className="metric-value">{agendaSemana.length}</div>
          <div className="metric-note">Nos próximos 7 dias</div>
        </div>
        <div className="metric-card metric-card-gold">
          <div className="metric-icon metric-icon-gold">
            <svg viewBox="0 0 20 20" fill="currentColor"><path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" /></svg>
          </div>
          <div className="metric-label">Pendentes</div>
          <div className="metric-value">{pendentes.length}</div>
          <div className="metric-note">Aguardando confirmação</div>
        </div>
      </div>

      <div className="content-grid grid-2-1">
        <div className="card">
          <div className="card-header">
            <div>
              <div className="section-eyebrow">Timeline</div>
              <h3 className="section-title">{agendaHoje.length > 0 ? "Aulas de hoje" : "Próximos eventos"}</h3>
            </div>
            <div className="badge badge-info"><span className="badge-dot" />{exibir.length} eventos</div>
          </div>
          <div className="card-body">
            {exibir.length === 0 ? (
              <div className="empty-state">
                <div className="empty-icon"><svg viewBox="0 0 20 20" fill="currentColor"><path fillRule="evenodd" d="M6 2a1 1 0 00-1 1v1H4a2 2 0 00-2 2v10a2 2 0 002 2h12a2 2 0 002-2V6a2 2 0 00-2-2h-1V3a1 1 0 10-2 0v1H7V3a1 1 0 00-1-1zm0 5a1 1 0 000 2h8a1 1 0 100-2H6z" clipRule="evenodd" /></svg></div>
                <div className="empty-title">Agenda vazia</div>
                <p className="empty-desc">Nenhum evento registrado. Crie eventos no sistema Streamlit ou clique em "Novo evento".</p>
              </div>
            ) : (
              <div className="timeline">
                {exibir.map((e, i) => {
                  const titulo = String(e.titulo || e.turma || e.descricao || `Evento ${i + 1}`);
                  const horario = String(e.horario || e.hora || e.time || "—");
                  const status = String(e.status || "Agendado");
                  const professor = e.professor ? String(e.professor) : null;
                  return (
                    <div className="timeline-item" key={String(e.id || i)}>
                      <div className="timeline-time">{horario}</div>
                      <div className={`timeline-dot ${dotClass(status)}`} />
                      <div className="timeline-body">
                        <div className="timeline-body-top">
                          <span className="timeline-title">{titulo}</span>
                          <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
                            <span className={`badge badge-${statusBadge(status)}`}>
                              <span className="badge-dot" />{status}
                            </span>
                            <EditarEventoBtn evento={e} />
                          </div>
                        </div>
                        {professor && <p className="timeline-meta">{professor}</p>}
                        {e.descricao && titulo !== String(e.descricao) && (
                          <p className="timeline-detail">{String(e.descricao)}</p>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </div>

        <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
          <div className="card">
            <div className="card-body">
              <div className="section-eyebrow">Fechamento</div>
              <h3 className="section-title" style={{ marginBottom: "16px" }}>Checklist da aula</h3>
              <div className="pipeline">
                {[
                  "Registrar onde a turma parou no livro",
                  "Salvar observação objetiva da aula",
                  "Disparar tarefa alinhada ao conteúdo",
                  "Confirmar presença dos alunos"
                ].map((item, idx) => (
                  <div className="pipeline-step" key={idx}>
                    <div className="pipeline-num">0{idx + 1}</div>
                    <div className="pipeline-text">
                      <div className="pipeline-title">{item}</div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>

          <div className="card card-gold">
            <div className="card-body">
              <div className="section-eyebrow">Resumo</div>
              <h3 className="section-title" style={{ marginBottom: "16px" }}>Visão da semana</h3>
              <div className="spotlight-list">
                <div className="spotlight-row">
                  <span className="spotlight-label">Eventos hoje</span>
                  <span className="spotlight-value">{agendaHoje.length}</span>
                </div>
                <div className="spotlight-row">
                  <span className="spotlight-label">Esta semana</span>
                  <span className="spotlight-value">{agendaSemana.length}</span>
                </div>
                <div className="spotlight-row">
                  <span className="spotlight-label">Total na agenda</span>
                  <span className="spotlight-value">{agenda.length}</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </AppShell>
  );
}
