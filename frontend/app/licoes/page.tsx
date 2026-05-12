import { AppShell } from "@/components/app-shell";
import { HomeworkCreateButton, HomeworkReviewForm } from "@/components/school-modules-client";
import { getSession } from "@/lib/auth";
import { dbList } from "@/lib/db";
import { canManageSchoolContent, homeworkTotal, isHomeworkActivity, text, type Homework, type HomeworkSubmission } from "@/lib/school-modules";
import { redirect } from "next/navigation";

function statusBadge(status: string) {
  const value = status.toLowerCase();
  if (value.includes("rascunho")) return "neutral";
  if (value.includes("encerr")) return "warning";
  return "success";
}

export default async function LicoesPage() {
  const session = await getSession();
  if (!session) redirect("/login");
  if (!canManageSchoolContent(session)) redirect("/");

  const [activities, submissions, turmas, alunos] = await Promise.all([
    dbList<Homework>("activities.json"),
    dbList<HomeworkSubmission>("activity_submissions.json"),
    dbList<Record<string, unknown>>("classes.json"),
    dbList<Record<string, unknown>>("students.json"),
  ]);
  const licoes = activities.filter(isHomeworkActivity);
  const entregas = submissions.filter((submission) => licoes.some((item) => text(item.id) === text(submission.activity_id)));
  const corrigidas = entregas.filter((submission) => text(submission.status).toLowerCase().includes("corrigido"));
  const pendentes = entregas.length - corrigidas.length;

  return (
    <AppShell breadcrumb="Licoes de Casa" userName={session.pessoa || session.usuario} userRole={session.perfil}>
      <div className="page-header">
        <div className="page-title-block">
          <div className="page-eyebrow"><span className="page-eyebrow-dot" />Pedagogico</div>
          <h1 className="page-title">Licao de casa</h1>
          <p className="page-description">Crie tarefas por turma, gere questoes com Prof Wiz, acompanhe entregas e lance notas com rastreabilidade.</p>
        </div>
        <div className="page-actions"><HomeworkCreateButton turmas={turmas} alunos={alunos} /></div>
      </div>

      <div className="metric-grid metric-grid-4">
        <div className="metric-card metric-card-blue"><div className="metric-label">Licoes criadas</div><div className="metric-value">{licoes.length}</div><div className="metric-note">Ativas, rascunhos e encerradas</div></div>
        <div className="metric-card metric-card-green"><div className="metric-label">Entregas</div><div className="metric-value">{entregas.length}</div><div className="metric-note">Respostas recebidas</div></div>
        <div className="metric-card metric-card-gold"><div className="metric-label">Corrigidas</div><div className="metric-value">{corrigidas.length}</div><div className="metric-note">Notas lancadas no boletim</div></div>
        <div className="metric-card metric-card-red"><div className="metric-label">A corrigir</div><div className="metric-value">{pendentes}</div><div className="metric-note">Aguardando avaliacao</div></div>
      </div>

      <div className="content-grid grid-2-1">
        <div className="card">
          <div className="card-header">
            <div>
              <div className="section-eyebrow">Gestao</div>
              <h3 className="section-title">Licoes publicadas</h3>
            </div>
          </div>
          <div className="card-body" style={{ paddingTop: 12 }}>
            {licoes.length === 0 ? (
              <div className="empty-state"><div className="empty-title">Nenhuma licao criada</div><p className="empty-desc">Use Nova licao para publicar tarefa manual ou gerar questoes com Prof Wiz.</p></div>
            ) : (
              <table className="data-table">
                <thead><tr><th>Licao</th><th>Turma</th><th>Disciplina</th><th>Prazo</th><th>Status</th><th>Entregas</th></tr></thead>
                <tbody>
                  {licoes.map((licao) => {
                    const count = entregas.filter((submission) => text(submission.activity_id) === text(licao.id)).length;
                    return (
                      <tr key={text(licao.id)}>
                        <td><div className="table-name-cell"><span className="table-name-primary">{text(licao.titulo)}</span><span className="table-name-secondary">{(licao.questions || []).length} questoes | {homeworkTotal(licao)} pts</span></div></td>
                        <td>{text(licao.turma || "Todas")}</td>
                        <td>{text(licao.disciplina || "Geral")}</td>
                        <td>{text(licao.due_date || "-")}</td>
                        <td><span className={`badge badge-${statusBadge(text(licao.status || "Ativa"))}`}><span className="badge-dot" />{text(licao.status || "Ativa")}</span></td>
                        <td style={{ fontWeight: 700 }}>{count}</td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            )}
          </div>
        </div>

        <div className="card card-hero">
          <div className="card-body">
            <div className="section-eyebrow">Prof Wiz</div>
            <h3 className="section-title" style={{ marginBottom: 14 }}>Fluxo com revisao humana</h3>
            <div className="pipeline">
              <div className="pipeline-step"><div className="pipeline-num">01</div><div className="pipeline-title">Professor informa turma, disciplina, livro e topico.</div></div>
              <div className="pipeline-step"><div className="pipeline-num">02</div><div className="pipeline-title">Prof Wiz gera questoes editaveis com gabarito.</div></div>
              <div className="pipeline-step"><div className="pipeline-num">03</div><div className="pipeline-title">Publicacao acontece somente apos revisao do professor.</div></div>
            </div>
          </div>
        </div>
      </div>

      <div className="card">
        <div className="card-header">
          <div>
            <div className="section-eyebrow">Correcao</div>
            <h3 className="section-title">Entregas dos alunos</h3>
            <p className="section-subtitle">Questoes objetivas recebem pontuacao inicial automatica; professor valida e salva a nota final.</p>
          </div>
        </div>
        <div className="card-body">
          {entregas.length === 0 ? (
            <div className="empty-state"><div className="empty-title">Nenhuma entrega recebida</div><p className="empty-desc">As respostas aparecem aqui assim que o aluno enviar a licao pelo portal.</p></div>
          ) : (
            <div style={{ display: "grid", gap: 14 }}>
              {entregas.slice().reverse().map((submission) => {
                const licao = licoes.find((item) => text(item.id) === text(submission.activity_id));
                return (
                  <div className="entity-card" key={text(submission.id)} style={{ cursor: "default" }}>
                    <div className="entity-card-top">
                      <div className="entity-card-info">
                        <div className="entity-card-name">{text(submission.aluno)}</div>
                        <div className="entity-card-sub">{text(licao?.titulo || "Licao")} | {text(submission.submitted_at || "-")}</div>
                      </div>
                      <span className={`badge badge-${text(submission.status).toLowerCase().includes("corrigido") ? "success" : "warning"}`}><span className="badge-dot" />{text(submission.status || "Aguardando correcao")}</span>
                    </div>
                    <div style={{ display: "grid", gap: 8, marginBottom: 14 }}>
                      {(licao?.questions || []).map((question, idx) => (
                        <div className="attendance-item" key={question.id} style={{ alignItems: "flex-start" }}>
                          <strong>{idx + 1}.</strong>
                          <span>{question.enunciado}</span>
                          <span style={{ color: "var(--text-muted)" }}>Resposta: {text((submission.answers as Record<string, string> | undefined)?.[question.id]) || "-"}</span>
                        </div>
                      ))}
                    </div>
                    <HomeworkReviewForm submission={submission} homework={licao} />
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
