import { AppShell } from "@/components/app-shell";
import { HomeworkCorrectionClient } from "@/components/homework-correction-client";
import { getSession } from "@/lib/auth";
import { dbList } from "@/lib/db";
import { canManageAllSchoolContent, isHomeworkActivity, text, type Homework, type HomeworkSubmission } from "@/lib/school-modules";
import { redirect } from "next/navigation";

export default async function CorrecaoLicoesPage() {
  const session = await getSession();
  if (!session) redirect("/login");
  if (!canManageAllSchoolContent(session)) redirect("/");

  const [activities, submissions] = await Promise.all([
    dbList<Homework>("activities.json"),
    dbList<HomeworkSubmission>("activity_submissions.json"),
  ]);
  const licoes = activities.filter(isHomeworkActivity);
  const items = submissions
    .filter((submission) => licoes.some((item) => text(item.id) === text(submission.activity_id)))
    .map((submission) => ({
      submission,
      homework: licoes.find((item) => text(item.id) === text(submission.activity_id)),
    }))
    .sort((a, b) => text(b.submission.submitted_at).localeCompare(text(a.submission.submitted_at)));

  const corrigidas = items.filter((item) => text(item.submission.status).toLowerCase().includes("corrigido")).length;
  const pendentes = items.length - corrigidas;

  return (
    <AppShell breadcrumb="Correcao de Licoes" userName={session.pessoa || session.usuario} userRole={session.perfil}>
      <div className="page-header">
        <div className="page-title-block">
          <div className="page-eyebrow"><span className="page-eyebrow-dot" />Coordenacao</div>
          <h1 className="page-title">Correcao de licoes</h1>
          <p className="page-description">Abra a entrega, veja cada resposta do aluno, use a IA de apoio e salve a nota final sem alterar os dados originais.</p>
        </div>
      </div>

      <div className="metric-grid metric-grid-3">
        <div className="metric-card metric-card-green"><div className="metric-label">Entregas</div><div className="metric-value">{items.length}</div><div className="metric-note">Respostas recebidas</div></div>
        <div className="metric-card metric-card-gold"><div className="metric-label">A corrigir</div><div className="metric-value">{pendentes}</div><div className="metric-note">Aguardando avaliacao</div></div>
        <div className="metric-card metric-card-blue"><div className="metric-label">Corrigidas</div><div className="metric-value">{corrigidas}</div><div className="metric-note">Notas lancadas</div></div>
      </div>

      <HomeworkCorrectionClient items={items} />
    </AppShell>
  );
}

