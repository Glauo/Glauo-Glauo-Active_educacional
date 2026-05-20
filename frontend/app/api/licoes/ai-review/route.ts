import { NextRequest, NextResponse } from "next/server";
import { getSession } from "@/lib/auth";
import { dbList, dbSet } from "@/lib/db";
import { gradeHomeworkWithWiz } from "@/lib/homework-ai-grader";
import { canManageAllSchoolContent, homeworkTotal, nowIso, text, type Homework, type HomeworkSubmission, type Row } from "@/lib/school-modules";

export async function POST(req: NextRequest) {
  const session = await getSession();
  if (!session || !canManageAllSchoolContent(session)) {
    return NextResponse.json({ error: "Nao autorizado" }, { status: 401 });
  }

  const body = (await req.json()) as { submission: HomeworkSubmission; homework: Homework; persist?: boolean };
  const { submission, homework } = body;
  let sourceSubmission = submission;

  if (body.persist) {
    const submissions = await dbList<HomeworkSubmission>("activity_submissions.json");
    const existing = submissions.find((item) => text(item.id) === text(submission.id));
    if (!existing) return NextResponse.json({ error: "Entrega nao encontrada." }, { status: 404 });
    sourceSubmission = existing;
  }

  const answers = (sourceSubmission.answers || {}) as Record<string, unknown>;
  const grade = await gradeHomeworkWithWiz(homework, answers);
  if (!grade) {
    return NextResponse.json({ error: "Wiz IA indisponivel. Configure GROQ_API_KEY ou ACTIVE_GROQ_API_KEY para corrigir automaticamente sem respostas cadastradas." }, { status: 503 });
  }

  if (body.persist) {
    const submissions = await dbList<HomeworkSubmission>("activity_submissions.json");
    const idx = submissions.findIndex((item) => text(item.id) === text(sourceSubmission.id));
    if (idx === -1) return NextResponse.json({ error: "Entrega nao encontrada." }, { status: 404 });

    const maxScore = homeworkTotal(homework) || 10;
    const reviewed: HomeworkSubmission = {
      ...submissions[idx],
      question_scores: grade.questionScores,
      score: grade.total,
      feedback: grade.feedback,
      status: "Corrigido",
      graded_at: nowIso(),
      graded_by: "Wiz IA",
    };
    submissions[idx] = reviewed;

    const [grades, audit] = await Promise.all([
      dbList<Row>("grades.json"),
      dbList<Row>("grade_audit.json"),
    ]);
    const gradeId = `homework_${text(reviewed.id)}`;
    const gradeRecord = {
      id: gradeId,
      aluno: reviewed.aluno,
      aluno_login: reviewed.aluno_login,
      titulo: homework.titulo || "Licao de Casa",
      desafio: homework.titulo || "Licao de Casa",
      disciplina: homework.disciplina || "Ingles",
      turma: reviewed.turma || homework.turma,
      nota: grade.total,
      pontos: grade.total,
      total: maxScore,
      status: "Corrigido",
      origem: "Licao de Casa",
      origem_id: reviewed.activity_id,
      corrigido_por: "Wiz IA",
      data: nowIso(),
    };
    const gradeIdx = grades.findIndex((item) => text(item.id) === gradeId);
    const nextGrades = gradeIdx >= 0
      ? grades.map((item, index) => index === gradeIdx ? { ...item, ...gradeRecord } : item)
      : [...grades, gradeRecord];
    const auditEntry = {
      id: crypto.randomUUID(),
      tipo: gradeIdx >= 0 ? "alteracao_nota_licao_ia" : "lancamento_nota_licao_ia",
      submission_id: reviewed.id,
      activity_id: reviewed.activity_id,
      aluno: reviewed.aluno,
      nota: grade.total,
      usuario: session.pessoa || session.usuario,
      perfil: session.perfil,
      corrigido_por: "Wiz IA",
      resumo: grade.summary,
      data: nowIso(),
    };

    await Promise.all([
      dbSet("activity_submissions.json", submissions),
      dbSet("grades.json", nextGrades),
      dbSet("grade_audit.json", [...audit, auditEntry]),
    ]);

    return NextResponse.json({
      questionScores: grade.questionScores,
      suggestedTotal: grade.total,
      feedback: grade.feedback,
      summary: grade.summary,
      saved: true,
      submission: reviewed,
    });
  }

  return NextResponse.json({
    questionScores: grade.questionScores,
    suggestedTotal: grade.total,
    feedback: grade.feedback,
    summary: grade.summary,
  });
}
