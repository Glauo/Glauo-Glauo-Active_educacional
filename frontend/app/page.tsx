import { AppShell } from "@/components/app-shell";
import { dbList } from "@/lib/db";
import { dashboardForPerfil, getSession } from "@/lib/auth";
import { redirect } from "next/navigation";

type Aluno = Record<string, unknown>;
type Turma = Record<string, unknown>;
type Professor = Record<string, unknown>;
type Recebimento = { status?: string; vencimento?: string; valor?: number | string; [k: string]: unknown };

function formatBRL(value: number): string {
  return value.toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
}

function calcStats(recebimentos: Recebimento[]) {
  const hoje = new Date();
  hoje.setHours(0, 0, 0, 0);

  let totalAberto = 0;
  let inadimplentes = 0;
  let vencemHoje = 0;

  for (const r of recebimentos) {
    const status = String(r.status || "").toLowerCase();
    if (status === "pago" || status === "baixado") continue;

    const val = parseFloat(String(r.valor || "0").replace(/[^\d.,]/g, "").replace(",", ".")) || 0;
    totalAberto += val;

    const venc = r.vencimento ? new Date(String(r.vencimento)) : null;
    if (venc) {
      if (venc < hoje) inadimplentes++;
      if (venc.toDateString() === hoje.toDateString()) vencemHoje++;
    }
  }

  return { totalAberto, inadimplentes, vencemHoje };
}

export default async function DashboardPage() {
  const session = await getSession();
  if (!session) redirect("/login");
  const dashboard = dashboardForPerfil(session.perfil);
  if (dashboard !== "/") redirect(dashboard);

  const [alunos, turmas, professores, recebimentos, agenda] = await Promise.all([
    dbList<Aluno>("students.json"),
    dbList<Turma>("classes.json"),
    dbList<Professor>("teachers.json"),
    dbList<Recebimento>("receivables.json"),
    dbList<Record<string, unknown>>("agenda.json")
  ]);

  const alunosAtivos = alunos.filter((a) => {
    const s = String(a.status || a.situacao || "ativo").toLowerCase();
    return !s.includes("inativ") && !s.includes("cancel");
  });

  const { totalAberto, inadimplentes, vencemHoje } = calcStats(recebimentos);

  const turmasAtivas = turmas.filter((t) => {
    const s = String(t.status || t.situacao || "ativa").toLowerCase();
    return !s.includes("inativ") && !s.includes("cancel");
  });

  const hoje = new Date();
  const agendaHoje = agenda.filter((e) => {
    const d = e.data || e.date || e.dia;
    if (!d) return false;
    const eDate = new Date(String(d));
    return eDate.toDateString() === hoje.toDateString();
  });

  const userName = session.pessoa || session.usuario;
  const userRole = session.perfil;

  return (
    <AppShell breadcrumb="Dashboard" userName={userName} userRole={userRole}>
      {/* Header */}
      <div className="page-header">
        <div className="page-title-block">
          <div className="page-eyebrow">
            <span className="page-eyebrow-dot" />
            Visão Geral
          </div>
          <h1 className="page-title">Dashboard executivo</h1>
          <p className="page-description">
            Panorama completo da operação — alunos, turmas, financeiro e agenda do dia.
          </p>
        </div>
        <div className="page-actions">
          <div className="badge badge-success">
            <span className="badge-dot" />
            Sistema operacional
          </div>
        </div>
      </div>

      {/* Métricas principais */}
      <div className="metric-grid metric-grid-4">
        <div className="metric-card metric-card-blue">
          <div className="metric-icon metric-icon-blue">
            <svg viewBox="0 0 20 20" fill="currentColor">
              <path d="M9 6a3 3 0 11-6 0 3 3 0 016 0zM17 6a3 3 0 11-6 0 3 3 0 016 0zM12.93 17c.046-.327.07-.66.07-1a6.97 6.97 0 00-1.5-4.33A5 5 0 0119 16v1h-6.07zM6 11a5 5 0 015 5v1H1v-1a5 5 0 015-5z" />
            </svg>
          </div>
          <div className="metric-label">Alunos ativos</div>
          <div className="metric-value">{alunosAtivos.length}</div>
          <div className="metric-note">{alunos.length} cadastrados no total</div>
        </div>

        <div className="metric-card metric-card-green">
          <div className="metric-icon metric-icon-green">
            <svg viewBox="0 0 20 20" fill="currentColor">
              <path d="M9 4.804A7.968 7.968 0 005.5 4c-1.255 0-2.443.29-3.5.804v10A7.969 7.969 0 015.5 14c1.669 0 3.218.51 4.5 1.385A7.962 7.962 0 0114.5 14c1.255 0 2.443.29 3.5.804v-10A7.968 7.968 0 0014.5 4c-1.255 0-2.443.29-3.5.804V12a1 1 0 11-2 0V4.804z" />
            </svg>
          </div>
          <div className="metric-label">Turmas ativas</div>
          <div className="metric-value">{turmasAtivas.length}</div>
          <div className="metric-note">{professores.length} professores cadastrados</div>
        </div>

        <div className="metric-card metric-card-gold">
          <div className="metric-icon metric-icon-gold">
            <svg viewBox="0 0 20 20" fill="currentColor">
              <path d="M4 4a2 2 0 00-2 2v1h16V6a2 2 0 00-2-2H4z" />
              <path fillRule="evenodd" d="M18 9H2v5a2 2 0 002 2h12a2 2 0 002-2V9zM4 13a1 1 0 011-1h1a1 1 0 110 2H5a1 1 0 01-1-1zm5-1a1 1 0 100 2h1a1 1 0 100-2H9z" clipRule="evenodd" />
            </svg>
          </div>
          <div className="metric-label">A receber</div>
          <div className="metric-value">{formatBRL(totalAberto)}</div>
          <div className="metric-note">{vencemHoje} vencem hoje</div>
        </div>

        <div className="metric-card metric-card-red">
          <div className="metric-icon metric-icon-red">
            <svg viewBox="0 0 20 20" fill="currentColor">
              <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
            </svg>
          </div>
          <div className="metric-label">Inadimplentes</div>
          <div className="metric-value">{inadimplentes}</div>
          <div className="metric-note">{recebimentos.length} lançamentos no total</div>
        </div>
      </div>

      {/* Conteúdo principal */}
      <div className="content-grid grid-2-1">
        {/* Agenda do dia */}
        <div className="card card-raised">
          <div className="card-header">
            <div>
              <div className="section-eyebrow">Operação</div>
              <h3 className="section-title">Agenda de hoje</h3>
              <p className="section-subtitle">{hoje.toLocaleDateString("pt-BR", { weekday: "long", day: "2-digit", month: "long" })}</p>
            </div>
            <div className="badge badge-info">
              <span className="badge-dot" />
              {agendaHoje.length} eventos
            </div>
          </div>
          <div className="card-body">
            {agendaHoje.length === 0 ? (
              <div className="empty-state">
                <div className="empty-icon">
                  <svg viewBox="0 0 20 20" fill="currentColor">
                    <path fillRule="evenodd" d="M6 2a1 1 0 00-1 1v1H4a2 2 0 00-2 2v10a2 2 0 002 2h12a2 2 0 002-2V6a2 2 0 00-2-2h-1V3a1 1 0 10-2 0v1H7V3a1 1 0 00-1-1zm0 5a1 1 0 000 2h8a1 1 0 100-2H6z" clipRule="evenodd" />
                  </svg>
                </div>
                <div className="empty-title">Agenda do dia vazia</div>
                <p className="empty-desc">Nenhum evento registrado para hoje. Os dados da agenda aparecerão aqui automaticamente.</p>
              </div>
            ) : (
              <div className="timeline">
                {agendaHoje.slice(0, 6).map((evento, i) => {
                  const status = String(evento.status || "").toLowerCase();
                  const dotClass = status.includes("conclu") ? "timeline-dot-done"
                    : status.includes("andamento") ? "timeline-dot-active"
                    : status.includes("atenc") ? "timeline-dot-warn"
                    : "";
                  return (
                    <div className="timeline-item" key={String(evento.id || i)}>
                      <div className="timeline-time">
                        {String(evento.horario || evento.hora || evento.time || "--:--")}
                      </div>
                      <div className={`timeline-dot ${dotClass}`} />
                      <div className="timeline-body">
                        <div className="timeline-body-top">
                          <span className="timeline-title">
                            {String(evento.titulo || evento.turma || evento.descricao || "Evento")}
                          </span>
                          {(evento.status as string | undefined) && (
                            <span className={`badge badge-${
                              status.includes("conclu") ? "success" :
                              status.includes("andamento") ? "info" :
                              "warning"
                            }`}>{String(evento.status)}</span>
                          )}
                        </div>
                        {(evento.professor as string | undefined) && (
                          <p className="timeline-meta">{String(evento.professor)}</p>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </div>

        {/* Painel lateral */}
        <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
          {/* Turmas recentes */}
          <div className="card">
            <div className="card-body">
              <div className="section-eyebrow">Pedagógico</div>
              <h3 className="section-title" style={{ marginBottom: "16px" }}>Turmas em destaque</h3>
              {turmasAtivas.length === 0 ? (
                <p className="text-muted text-sm">Nenhuma turma cadastrada.</p>
              ) : (
                <div className="spotlight-list">
                  {turmasAtivas.slice(0, 5).map((t, i) => (
                    <div className="spotlight-row" key={String(t.id || i)}>
                      <span className="spotlight-label">
                        {String(t.nome || t.name || `Turma ${i + 1}`)}
                      </span>
                      <span className="spotlight-value text-sm">
                        {String(t.professor || t.livro || t.book || "—")}
                      </span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>

          {/* Ações rápidas */}
          <div className="card card-hero">
            <div className="card-body">
              <div className="section-eyebrow">Atalhos</div>
              <h3 className="section-title" style={{ marginBottom: "16px" }}>Ações rápidas</h3>
              <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
                {[
                  { href: "/alunos", label: "Gerenciar alunos" },
                  { href: "/turmas", label: "Ver turmas" },
                  { href: "/financeiro", label: "Painel financeiro" },
                  { href: "/agenda", label: "Agenda do dia" }
                ].map((item) => (
                  <a
                    key={item.href}
                    href={item.href}
                    className="module-chip"
                    style={{ textDecoration: "none" }}
                  >
                    <span className="module-chip-name">{item.label}</span>
                    <svg width="14" height="14" viewBox="0 0 20 20" fill="currentColor" style={{ opacity: 0.4 }}>
                      <path fillRule="evenodd" d="M7.293 14.707a1 1 0 010-1.414L10.586 10 7.293 6.707a1 1 0 011.414-1.414l4 4a1 1 0 010 1.414l-4 4a1 1 0 01-1.414 0z" clipRule="evenodd" />
                    </svg>
                  </a>
                ))}
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Últimos alunos */}
      {alunos.length > 0 && (
        <div className="card">
          <div className="card-header">
            <div>
              <div className="section-eyebrow">Alunos</div>
              <h3 className="section-title">Cadastros recentes</h3>
            </div>
            <a href="/alunos" className="btn btn-secondary btn-sm">Ver todos</a>
          </div>
          <div className="card-body" style={{ paddingTop: "12px" }}>
            <table className="data-table">
              <thead>
                <tr>
                  <th>Aluno</th>
                  <th>Turma</th>
                  <th>Status</th>
                  <th>Financeiro</th>
                </tr>
              </thead>
              <tbody>
                {alunos.slice(-5).reverse().map((a, i) => {
                  const nome = String(a.nome || a.name || `Aluno ${i + 1}`);
                  const turma = String(a.turma || a.classe || "—");
                  const status = String(a.status || a.situacao || "Ativo");
                  const financeiro = String(a.status_financeiro || a.situacao_financeira || "Regular");
                  const isOk = financeiro.toLowerCase().includes("regular") || financeiro.toLowerCase().includes("em dia");

                  return (
                    <tr key={String(a.id || i)}>
                      <td>
                        <div className="table-name-cell">
                          <span className="table-name-primary">{nome}</span>
                          {(a.responsavel as string | undefined) && (
                            <span className="table-name-secondary">{String(a.responsavel)}</span>
                          )}
                        </div>
                      </td>
                      <td>{turma}</td>
                      <td>
                        <span className={`badge badge-${status.toLowerCase().includes("inativ") ? "neutral" : "success"}`}>
                          <span className="badge-dot" />
                          {status}
                        </span>
                      </td>
                      <td>
                        <span className={`badge badge-${isOk ? "success" : "danger"}`}>
                          <span className="badge-dot" />
                          {financeiro}
                        </span>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </AppShell>
  );
}
