import { AppShell } from "@/components/app-shell";
import { getSession } from "@/lib/auth";
import { redirect } from "next/navigation";

function canAccess(perfil: string) {
  const role = perfil.toLowerCase();
  return role.includes("admin") || role.includes("coord") || role.includes("dire") || role.includes("comercial");
}

export default async function CondoJobPage() {
  const session = await getSession();
  if (!session) redirect("/login");
  if (!canAccess(session.perfil)) redirect("/");

  const condoJobUrl = process.env.NEXT_PUBLIC_CONDOJOB_URL || process.env.CONDOJOB_URL || "";

  return (
    <AppShell breadcrumb="CondoJob" userName={session.pessoa || session.usuario} userRole={session.perfil}>
      <div className="page-header">
        <div className="page-title-block">
          <div className="page-eyebrow"><span className="page-eyebrow-dot" />Integração</div>
          <h1 className="page-title">Painel CondoJob</h1>
          <p className="page-description">
            Acesso rápido ao painel CondoJob para acompanhar solicitações, operação e atendimentos vinculados.
          </p>
        </div>
        <div className="page-actions">
          {condoJobUrl ? (
            <a className="btn btn-primary" href={condoJobUrl} target="_blank" rel="noreferrer">
              Abrir CondoJob
            </a>
          ) : (
            <span className="badge badge-info"><span className="badge-dot" />Painel habilitado</span>
          )}
        </div>
      </div>

      <div className="metric-grid metric-grid-3">
        <div className="metric-card metric-card-blue">
          <div className="metric-icon metric-icon-blue">
            <svg viewBox="0 0 20 20" fill="currentColor">
              <path d="M4 3a2 2 0 00-2 2v10a2 2 0 002 2h5v-4h2v4h5a2 2 0 002-2V5a2 2 0 00-2-2H4z" />
            </svg>
          </div>
          <div className="metric-label">CondoJob</div>
          <div className="metric-value">Ativo</div>
          <div className="metric-note">Módulo disponível no menu lateral</div>
        </div>
        <div className="metric-card metric-card-green">
          <div className="metric-icon metric-icon-green">
            <svg viewBox="0 0 20 20" fill="currentColor">
              <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 10-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
            </svg>
          </div>
          <div className="metric-label">Permissões</div>
          <div className="metric-value">Gestão</div>
          <div className="metric-note">Admin, direção, coordenação e comercial</div>
        </div>
        <div className="metric-card metric-card-gold">
          <div className="metric-icon metric-icon-gold">
            <svg viewBox="0 0 20 20" fill="currentColor">
              <path d="M11 3a1 1 0 100 2h2.586l-6.293 6.293a1 1 0 101.414 1.414L15 6.414V9a1 1 0 102 0V4a1 1 0 00-1-1h-5z" />
              <path d="M5 5a2 2 0 00-2 2v8a2 2 0 002 2h8a2 2 0 002-2v-3a1 1 0 10-2 0v3H5V7h3a1 1 0 000-2H5z" />
            </svg>
          </div>
          <div className="metric-label">Acesso externo</div>
          <div className="metric-value">{condoJobUrl ? "Pronto" : "Pendente"}</div>
          <div className="metric-note">{condoJobUrl ? "URL configurada" : "Aguardando URL oficial"}</div>
        </div>
      </div>

      <div className="card card-raised">
        <div className="card-header">
          <div>
            <div className="section-eyebrow">Painel</div>
            <h3 className="section-title">Área CondoJob</h3>
            <p className="section-subtitle">
              {condoJobUrl ? "O painel externo está disponível para abertura em nova aba." : "O módulo já está visível. Falta apenas cadastrar a URL externa oficial quando ela estiver disponível."}
            </p>
          </div>
        </div>
        <div className="card-body">
          {condoJobUrl ? (
            <div style={{ display: "grid", gap: 14 }}>
              <div className="alert alert-info">
                Use o botão acima para abrir o painel CondoJob em uma nova aba com segurança.
              </div>
              <iframe
                title="Painel CondoJob"
                src={condoJobUrl}
                style={{ width: "100%", minHeight: 620, border: "1px solid var(--border)", borderRadius: "var(--radius-lg)", background: "var(--surface)" }}
              />
            </div>
          ) : (
            <div className="empty-state">
              <div className="empty-icon">
                <svg viewBox="0 0 20 20" fill="currentColor">
                  <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 10-2 0v4a1 1 0 00.293.707l2 2a1 1 0 001.414-1.414L11 9.586V6z" clipRule="evenodd" />
                </svg>
              </div>
              <div className="empty-title">Painel CondoJob recolocado no sistema</div>
              <p className="empty-desc">
                O acesso já aparece no menu lateral. Quando a URL oficial for configurada em CONDOJOB_URL ou NEXT_PUBLIC_CONDOJOB_URL, o botão de abertura fica ativo automaticamente.
              </p>
            </div>
          )}
        </div>
      </div>
    </AppShell>
  );
}
