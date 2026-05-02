import { AppShell } from "@/components/app-shell";
import { dbList } from "@/lib/db";
import { getSession } from "@/lib/auth";
import { redirect } from "next/navigation";
import { NovoProfessorBtn, EditarProfessorBtn } from "@/components/professor-modal";
import { TeacherClassPanel } from "@/components/teacher-class-panel";

type Professor = { id?: string; nome?: string; name?: string; area?: string; especialidade?: string; turmas?: string | string[]; status?: string; situacao?: string; telefone?: string; email?: string; [k: string]: unknown };

export default async function ProfessoresPage() {
  const session = await getSession();
  if (!session) redirect("/login");

  const professores = await dbList<Professor>("teachers.json");
  const turmas = await dbList<Record<string, unknown>>("classes.json");
  const aulas = await dbList<Record<string, unknown>>("class_sessions.json");
  const alunos = await dbList<Record<string, unknown>>("students.json");

  const ativos = professores.filter((p) => {
    const s = String(p.status || p.situacao || "ativo").toLowerCase();
    return !s.includes("inativ") && !s.includes("cancel");
  });

  return (
    <AppShell breadcrumb="Professores" userName={session.pessoa || session.usuario} userRole={session.perfil}>
      <div className="page-header">
        <div className="page-title-block">
          <div className="page-eyebrow"><span className="page-eyebrow-dot" />Módulo Acadêmico</div>
          <h1 className="page-title">Professores</h1>
          <p className="page-description">Equipe docente — carga de aulas, turmas cobertas e status operacional.</p>
        </div>
        <div className="page-actions">
          <NovoProfessorBtn />
        </div>
      </div>

      <div className="metric-grid metric-grid-3">
        <div className="metric-card metric-card-blue">
          <div className="metric-icon metric-icon-blue">
            <svg viewBox="0 0 20 20" fill="currentColor"><path fillRule="evenodd" d="M10 9a3 3 0 100-6 3 3 0 000 6zm-7 9a7 7 0 1114 0H3z" clipRule="evenodd" /></svg>
          </div>
          <div className="metric-label">Docentes ativos</div>
          <div className="metric-value">{ativos.length}</div>
          <div className="metric-note">{professores.length} cadastrados no total</div>
        </div>
        <div className="metric-card metric-card-green">
          <div className="metric-icon metric-icon-green">
            <svg viewBox="0 0 20 20" fill="currentColor"><path d="M9 4.804A7.968 7.968 0 005.5 4c-1.255 0-2.443.29-3.5.804v10A7.969 7.969 0 015.5 14c1.669 0 3.218.51 4.5 1.385A7.962 7.962 0 0114.5 14c1.255 0 2.443.29 3.5.804v-10A7.968 7.968 0 0014.5 4c-1.255 0-2.443.29-3.5.804V12a1 1 0 11-2 0V4.804z" /></svg>
          </div>
          <div className="metric-label">Turmas cobertas</div>
          <div className="metric-value">{turmas.length}</div>
          <div className="metric-note">Total de turmas no sistema</div>
        </div>
        <div className="metric-card metric-card-gold">
          <div className="metric-icon metric-icon-gold">
            <svg viewBox="0 0 20 20" fill="currentColor"><path fillRule="evenodd" d="M6 2a1 1 0 00-1 1v1H4a2 2 0 00-2 2v10a2 2 0 002 2h12a2 2 0 002-2V6a2 2 0 00-2-2h-1V3a1 1 0 10-2 0v1H7V3a1 1 0 00-1-1zm0 5a1 1 0 000 2h8a1 1 0 100-2H6z" clipRule="evenodd" /></svg>
          </div>
          <div className="metric-label">Média de turmas</div>
          <div className="metric-value">{ativos.length > 0 ? (turmas.length / ativos.length).toFixed(1) : "—"}</div>
          <div className="metric-note">Turmas por professor</div>
        </div>
      </div>

      <TeacherClassPanel
        turmas={turmas}
        aulas={aulas}
        professores={professores}
        alunos={alunos}
        userName={session.pessoa || session.usuario}
        userRole={session.perfil}
      />

      <div className="card">
        <div className="toolbar">
          <div className="toolbar-left">
            <div className="search-bar">
              <span className="search-icon"><svg viewBox="0 0 20 20" fill="currentColor"><path fillRule="evenodd" d="M8 4a4 4 0 100 8 4 4 0 000-8zM2 8a6 6 0 1110.89 3.476l4.817 4.817a1 1 0 01-1.414 1.414l-4.816-4.816A6 6 0 012 8z" clipRule="evenodd" /></svg></span>
              <input className="search-input" placeholder="Buscar professor ou área..." />
            </div>
          </div>
          <div className="toolbar-right">
            <select className="filter-select"><option>Qualquer status</option><option>Ativo</option><option>Inativo</option></select>
          </div>
        </div>
      </div>

      <div className="card">
        <div className="card-header">
          <div>
            <div className="section-eyebrow">Equipe</div>
            <h3 className="section-title">Professores em operação</h3>
            <p className="section-subtitle">{professores.length} registros</p>
          </div>
        </div>
        <div className="card-body" style={{ paddingTop: "12px" }}>
          {professores.length === 0 ? (
            <div className="empty-state">
              <div className="empty-icon"><svg viewBox="0 0 20 20" fill="currentColor"><path fillRule="evenodd" d="M10 9a3 3 0 100-6 3 3 0 000 6zm-7 9a7 7 0 1114 0H3z" clipRule="evenodd" /></svg></div>
              <div className="empty-title">Nenhum professor cadastrado</div>
              <p className="empty-desc">Os professores do sistema Streamlit são carregados automaticamente do banco PostgreSQL.</p>
            </div>
          ) : (
            <table className="data-table">
              <thead>
                <tr>
                  <th>Professor</th>
                  <th>Área</th>
                  <th>Turmas</th>
                  <th>Status</th>
                  <th>Ações</th>
                </tr>
              </thead>
              <tbody>
                {professores.map((p, i) => {
                  const nome = String(p.nome || p.name || `Professor ${i + 1}`);
                  const area = String(p.area || p.especialidade || "—");
                  const turmasList = Array.isArray(p.turmas)
                    ? (p.turmas as string[]).join(", ")
                    : String(p.turmas || "—");
                  const status = String(p.status || p.situacao || "Ativo");
                  const hue = (nome.charCodeAt(0) * 97) % 360;
                  return (
                    <tr key={String(p.id || i)}>
                      <td>
                        <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
                          <div className="avatar avatar-sm" style={{ background: `hsl(${hue},45%,42%)` }}>{nome.slice(0, 2).toUpperCase()}</div>
                          <div className="table-name-cell">
                            <span className="table-name-primary">{nome}</span>
                            {p.email && <span className="table-name-secondary">{String(p.email)}</span>}
                          </div>
                        </div>
                      </td>
                      <td>{area}</td>
                      <td style={{ maxWidth: "220px", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{turmasList}</td>
                      <td>
                        <span className={`badge badge-${status.toLowerCase().includes("inativ") ? "neutral" : "success"}`}>
                          <span className="badge-dot" />{status}
                        </span>
                      </td>
                      <td><EditarProfessorBtn professor={p} /></td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </AppShell>
  );
}
