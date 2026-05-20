import { AppShell } from "@/components/app-shell";
import { HomeworkCreateButton } from "@/components/school-modules-client";
import { HomeworkDeleteTodayBtn } from "@/components/homework-actions";
import { HomeworkStudentLessonsClient } from "@/components/homework-student-lessons-client";
import { getSession } from "@/lib/auth";
import { dbList } from "@/lib/db";
import { canManageSchoolContent, isHomeworkActivity, text, type Homework, type HomeworkSubmission } from "@/lib/school-modules";
import { redirect } from "next/navigation";

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
  const licoesOrdenadas = [...licoes].sort((a, b) => {
    const dateDiff = text(b.created_at || b.updated_at).localeCompare(text(a.created_at || a.updated_at));
    if (dateDiff !== 0) return dateDiff;
    return text(a.titulo).localeCompare(text(b.titulo));
  });
  const entregas = submissions.filter((submission) => licoes.some((item) => text(item.id) === text(submission.activity_id)));
  const corrigidas = entregas.filter((submission) => text(submission.status).toLowerCase().includes("corrigido"));
  const pendentes = entregas.length - corrigidas.length;
  const today = new Date().toISOString().slice(0, 10);
  const licoesHoje = licoes.filter((l) => text(l.created_at).startsWith(today));
  const turmaNames = turmas.map((t) => text(t.nome || t.name || "")).filter(Boolean);

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
            <HomeworkDeleteTodayBtn todayCount={licoesHoje.length} />
          </div>
          <div className="card-body" style={{ paddingTop: 12 }}>
            {licoes.length === 0 ? (
              <div className="empty-state"><div className="empty-title">Nenhuma licao criada</div><p className="empty-desc">Use Nova licao para publicar tarefa manual ou gerar questoes com Prof Wiz.</p></div>
            ) : (
              <HomeworkStudentLessonsClient licoes={licoesOrdenadas} entregas={entregas} alunos={alunos} turmaNames={turmaNames} />
            )}
          </div>
        </div>

        <div className="card card-hero">
          <div className="card-body">
            <div className="section-eyebrow">Prof Wiz</div>
            <h3 className="section-title" style={{ marginBottom: 14 }}>Fluxo com revisao humana</h3>
            <div className="pipeline">
              <div className="pipeline-step"><div className="pipeline-num">01</div><div className="pipeline-title">Professor informa turma, disciplina, livro e topico.</div></div>
              <div className="pipeline-step"><div className="pipeline-num">02</div><div className="pipeline-title">Prof Wiz gera questoes editaveis; a correcao automatica usa IA.</div></div>
              <div className="pipeline-step"><div className="pipeline-num">03</div><div className="pipeline-title">Publicacao acontece somente apos revisao do professor.</div></div>
            </div>
          </div>
        </div>
      </div>
    </AppShell>
  );
}
