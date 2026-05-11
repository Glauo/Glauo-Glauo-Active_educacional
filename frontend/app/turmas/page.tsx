import { AppShell } from "@/components/app-shell";
import { getSession } from "@/lib/auth";
import { redirect } from "next/navigation";
import { NovaTurmaBtn, EditarTurmaBtn } from "@/components/turma-modal";
import { getSchoolClasses } from "@/lib/school-data";

type Turma = { id?: string; nome?: string; name?: string; professor?: string; modulo?: string; tipo_aula?: string; modalidade?: string; livro?: string; book?: string; status?: string; situacao?: string; ultima_licao?: string; ultima_aula?: string; horario?: string; dias?: string; link_zoom?: string; valor_aula?: string | number; total_aulas_vip?: string | number; aulas_realizadas_vip?: string | number; [k: string]: unknown };

function statusBadge(s: string) {
  const l = s.toLowerCase();
  if (l.includes("atenc") || l.includes("pendente")) return "warning";
  if (l.includes("inativ") || l.includes("cancel")) return "neutral";
  return "success";
}

export default async function TurmasPage() {
  const session = await getSession();
  if (!session) redirect("/login");

  const turmas = await getSchoolClasses() as Turma[];

  const ativas = turmas.filter((t) => {
    const s = String(t.status || t.situacao || "ativa").toLowerCase();
    return !s.includes("inativ") && !s.includes("cancel");
  });

  const comPendencia = ativas.filter((t) => {
    const s = String(t.status || "").toLowerCase();
    return s.includes("atenc") || s.includes("pendente");
  });

  return (
    <AppShell breadcrumb="Turmas" userName={session.pessoa || session.usuario} userRole={session.perfil}>
      <div className="page-header">
        <div className="page-title-block">
          <div className="page-eyebrow"><span className="page-eyebrow-dot" />Estrutura Escolar</div>
          <h1 className="page-title">Turmas</h1>
          <p className="page-description">Modulo de aula, professor, livro, agenda, link online e saldo VIP das turmas.</p>
        </div>
        <div className="page-actions">
          <NovaTurmaBtn />
        </div>
      </div>

      <div className="metric-grid metric-grid-3">
        <div className="metric-card metric-card-blue">
          <div className="metric-icon metric-icon-blue">
            <svg viewBox="0 0 20 20" fill="currentColor"><path d="M9 4.804A7.968 7.968 0 005.5 4c-1.255 0-2.443.29-3.5.804v10A7.969 7.969 0 015.5 14c1.669 0 3.218.51 4.5 1.385A7.962 7.962 0 0114.5 14c1.255 0 2.443.29 3.5.804v-10A7.968 7.968 0 0014.5 4c-1.255 0-2.443.29-3.5.804V12a1 1 0 11-2 0V4.804z" /></svg>
          </div>
          <div className="metric-label">Turmas ativas</div>
          <div className="metric-value">{ativas.length}</div>
          <div className="metric-note">{turmas.length} cadastradas no total</div>
        </div>
        <div className="metric-card metric-card-green">
          <div className="metric-icon metric-icon-green">
            <svg viewBox="0 0 20 20" fill="currentColor"><path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" /></svg>
          </div>
          <div className="metric-label">No ritmo</div>
          <div className="metric-value">{Math.max(0, ativas.length - comPendencia.length)}</div>
          <div className="metric-note">Fluxo pedagógico regular</div>
        </div>
        <div className="metric-card metric-card-gold">
          <div className="metric-icon metric-icon-gold">
            <svg viewBox="0 0 20 20" fill="currentColor"><path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" /></svg>
          </div>
          <div className="metric-label">Com atenção</div>
          <div className="metric-value">{comPendencia.length}</div>
          <div className="metric-note">Pendências pedagógicas</div>
        </div>
      </div>

      <div className="card">
        <div className="card-header">
          <div>
            <div className="section-eyebrow">Mapa de turmas</div>
            <h3 className="section-title">Progresso por grupo</h3>
          </div>
          <div className="search-bar">
            <span className="search-icon"><svg viewBox="0 0 20 20" fill="currentColor"><path fillRule="evenodd" d="M8 4a4 4 0 100 8 4 4 0 000-8zM2 8a6 6 0 1110.89 3.476l4.817 4.817a1 1 0 01-1.414 1.414l-4.816-4.816A6 6 0 012 8z" clipRule="evenodd" /></svg></span>
            <input className="search-input" placeholder="Buscar turma ou professor..." />
          </div>
        </div>
        <div className="card-body">
          {turmas.length === 0 ? (
            <div className="empty-state">
              <div className="empty-icon"><svg viewBox="0 0 20 20" fill="currentColor"><path d="M9 4.804A7.968 7.968 0 005.5 4c-1.255 0-2.443.29-3.5.804v10A7.969 7.969 0 015.5 14c1.669 0 3.218.51 4.5 1.385A7.962 7.962 0 0114.5 14c1.255 0 2.443.29 3.5.804v-10A7.968 7.968 0 0014.5 4c-1.255 0-2.443.29-3.5.804V12a1 1 0 11-2 0V4.804z" /></svg></div>
              <div className="empty-title">Nenhuma turma cadastrada</div>
              <p className="empty-desc">As turmas do Streamlit são carregadas automaticamente do banco PostgreSQL.</p>
            </div>
          ) : (
            <div className="entity-grid">
              {turmas.map((t, i) => {
                const nome = String(t.nome || t.name || `Turma ${i + 1}`);
                const professor = String(t.professor || "—");
                const modulo = String(t.modulo || t.tipo_aula || t.modalidade || "—");
                const livro = String(t.livro || t.book || "—");
                const status = String(t.status || t.situacao || "Ativa");
                const ultimaLicao = String(t.ultima_licao || t.ultima_aula || "—");
                const horario = String(t.dias || t.horario || "—");
                const totalVip = Number(t.total_aulas_vip || 0);
                const feitasVip = Number(t.aulas_realizadas_vip || 0);
                return (
                  <div className="entity-card" key={String(t.id || i)}>
                    <div className="entity-card-top">
                      <div className="entity-card-info">
                        <div className="entity-card-name">{nome}</div>
                        <div className="entity-card-sub">{professor} | {modulo}</div>
                      </div>
                      <span className={`badge badge-${statusBadge(status)}`}><span className="badge-dot" />{status}</span>
                    </div>
                    <div className="entity-card-rows">
                      <div className="entity-card-row">
                        <span className="entity-card-row-label">Modulo</span>
                        <span className="entity-card-row-value">{modulo}</span>
                      </div>
                      <div className="entity-card-row">
                        <span className="entity-card-row-label">Livro</span>
                        <span className="entity-card-row-value">{livro}</span>
                      </div>
                      <div className="entity-card-row">
                        <span className="entity-card-row-label">Última lição</span>
                        <span className="entity-card-row-value">{ultimaLicao}</span>
                      </div>
                      <div className="entity-card-row">
                        <span className="entity-card-row-label">Agenda</span>
                        <span className="entity-card-row-value">{horario}</span>
                      </div>
                      {String(t.link_zoom || "").trim() && (
                        <div className="entity-card-row">
                          <span className="entity-card-row-label">Online</span>
                          <span className="entity-card-row-value">Link cadastrado</span>
                        </div>
                      )}
                      {modulo === "Vip" && (
                        <div className="entity-card-row">
                          <span className="entity-card-row-label">Saldo aulas VIP</span>
                          <span className="entity-card-row-value">{Math.max(0, totalVip - feitasVip)} de {totalVip || "—"}</span>
                        </div>
                      )}
                    </div>
                    <div style={{ marginTop: "12px" }}>
                      <EditarTurmaBtn turma={t} />
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </div>
    </AppShell>
  );
}
