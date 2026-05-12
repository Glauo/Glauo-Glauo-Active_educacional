import { AppShell } from "@/components/app-shell";
import { dbList } from "@/lib/db";
import { getSession } from "@/lib/auth";
import { redirect } from "next/navigation";
import { NovoDesafioBtn } from "@/components/desafio-modal";
import { NotaRapidaForm } from "@/components/notas-form";
import { DesafiosTable } from "@/components/desafios-table";

type Desafio = { id?: string; titulo?: string; title?: string; turma?: string; descricao?: string; pontos?: number | string; status?: string; data_publicacao?: string; data?: string; [k: string]: unknown };
type Conclusao = { desafio_id?: string; aluno?: string; pontos?: number | string; data?: string; [k: string]: unknown };

export default async function DesafiosPage() {
  const session = await getSession();
  if (!session) redirect("/login");

  const [desafios, conclusoes, alunos] = await Promise.all([
    dbList<Desafio>("challenges.json"),
    dbList<Conclusao>("challenge_completions.json"),
    dbList<Record<string, unknown>>("students.json")
  ]);

  const publicados = desafios.filter((d) => {
    const s = String(d.status || "publicado").toLowerCase();
    return !s.includes("rascunho") && !s.includes("arquiv");
  });

  const totalPontos = conclusoes.reduce((acc, c) => acc + (Number(c.pontos) || 0), 0);

  return (
    <AppShell breadcrumb="Desafios" userName={session.pessoa || session.usuario} userRole={session.perfil}>
      <div className="page-header">
        <div className="page-title-block">
          <div className="page-eyebrow"><span className="page-eyebrow-dot" />Módulo Pedagógico</div>
          <h1 className="page-title">Desafios & Lições</h1>
          <p className="page-description">Gerencie desafios publicados por turma, acompanhe conclusões e ranking de pontos.</p>
        </div>
        <div className="page-actions">
          <NovoDesafioBtn />
        </div>
      </div>

      <div className="metric-grid metric-grid-4">
        <div className="metric-card metric-card-blue">
          <div className="metric-icon metric-icon-blue">
            <svg viewBox="0 0 20 20" fill="currentColor"><path d="M9 2a1 1 0 000 2h2a1 1 0 100-2H9z" /><path fillRule="evenodd" d="M4 5a2 2 0 012-2 3 3 0 003 3h2a3 3 0 003-3 2 2 0 012 2v11a2 2 0 01-2 2H6a2 2 0 01-2-2V5z" clipRule="evenodd" /></svg>
          </div>
          <div className="metric-label">Desafios criados</div>
          <div className="metric-value">{desafios.length}</div>
          <div className="metric-note">{publicados.length} publicados ativamente</div>
        </div>
        <div className="metric-card metric-card-green">
          <div className="metric-icon metric-icon-green">
            <svg viewBox="0 0 20 20" fill="currentColor"><path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" /></svg>
          </div>
          <div className="metric-label">Conclusões</div>
          <div className="metric-value">{conclusoes.length}</div>
          <div className="metric-note">Desafios concluídos por alunos</div>
        </div>
        <div className="metric-card metric-card-gold">
          <div className="metric-icon metric-icon-gold">
            <svg viewBox="0 0 20 20" fill="currentColor"><path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z" /></svg>
          </div>
          <div className="metric-label">Total de pontos</div>
          <div className="metric-value">{totalPontos.toLocaleString("pt-BR")}</div>
          <div className="metric-note">Distribuídos entre os alunos</div>
        </div>
        <div className="metric-card metric-card-red">
          <div className="metric-icon metric-icon-red">
            <svg viewBox="0 0 20 20" fill="currentColor"><path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z" clipRule="evenodd" /></svg>
          </div>
          <div className="metric-label">Rascunhos</div>
          <div className="metric-value">{desafios.length - publicados.length}</div>
          <div className="metric-note">Aguardando publicação</div>
        </div>
      </div>

      <div className="content-grid grid-2-1">
        <DesafiosTable desafios={desafios} conclusoes={conclusoes} />

        {/* Ranking */}
        <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
          <div className="card card-gold">
            <div className="card-body">
              <div className="section-eyebrow">Ranking</div>
              <h3 className="section-title" style={{ marginBottom: "16px" }}>Top alunos</h3>
              {conclusoes.length === 0 ? (
                <p className="text-muted text-sm">Nenhuma conclusão registrada ainda.</p>
              ) : (
                <div className="spotlight-list">
                  {Object.entries(
                    conclusoes.reduce((acc: Record<string, number>, c) => {
                      const aluno = String(c.aluno || "Anônimo");
                      acc[aluno] = (acc[aluno] || 0) + (Number(c.pontos) || 0);
                      return acc;
                    }, {})
                  )
                    .sort((a, b) => b[1] - a[1])
                    .slice(0, 6)
                    .map(([aluno, pts], idx) => (
                      <div className="spotlight-row" key={aluno}>
                        <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
                          <span style={{ fontSize: "0.75rem", fontWeight: 800, color: idx < 3 ? "var(--gold-600)" : "var(--text-muted)", width: "20px" }}>
                            #{idx + 1}
                          </span>
                          <span className="spotlight-label">{aluno}</span>
                        </div>
                        <span className="spotlight-value">{pts} pts</span>
                      </div>
                    ))}
                </div>
              )}
            </div>
          </div>

          <div className="card">
            <div className="card-body">
              <div className="section-eyebrow">Fluxo pedagógico</div>
              <h3 className="section-title" style={{ marginBottom: "16px" }}>Como funciona</h3>
              <div className="pipeline">
                {[
                  "Professor fecha a aula e registra a lição",
                  "Wiz sugere desafio baseado no conteúdo",
                  "Aluno responde na área do aluno",
                  "Professor aprova e pontos são creditados"
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
        </div>
      </div>
      <div style={{ marginTop: 24 }}>
        <NotaRapidaForm alunos={alunos} desafios={desafios} />
      </div>
    </AppShell>
  );
}
