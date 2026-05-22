import { NextRequest, NextResponse } from "next/server";
import { getSession } from "@/lib/auth";
import { dbList, dbSet } from "@/lib/db";
import { gradeHomeworkWithWiz } from "@/lib/homework-ai-grader";
import { lower, nowIso, studentMatchesTarget, text, type Homework, type HomeworkSubmission, type Row } from "@/lib/school-modules";
import { hasWorkbookStudentTarget, releasedWorkbookLessons, studentWorkbookBook } from "@/lib/workbook-lessons";

export async function POST(req: NextRequest) {
  const session = await getSession();
  if (!session || session.perfil !== "Aluno") return NextResponse.json({ error: "Nao autorizado" }, { status: 401 });
  const body = (await req.json()) as { activity_id?: string; answers?: Record<string, string> };
  const activityId = text(body.activity_id);
  const [activities, students, submissions] = await Promise.all([
    dbList<Homework>("activities.json"),
    dbList<Row>("students.json"),
    dbList<HomeworkSubmission>("activity_submissions.json"),
  ]);
  const student = students.find((item) => text(item.login || item.usuario) === text(session.usuario) || text(item.nome || item.name) === text(session.pessoa));
  const homework = activities.find((item) => text(item.id) === activityId);
  if (!homework) return NextResponse.json({ error: "Licao nao encontrada." }, { status: 404 });

  if (lower(homework.origem).includes("workbook")) {
    const book = studentWorkbookBook(student, session.unit);
    const studentSubmissions = submissions.filter((item) => text(item.aluno_login) === text(session.usuario) || text(item.aluno) === text(session.pessoa));
    const registeredWorkbookLessons = activities
      .filter((item) => lower(item.origem).includes("workbook"))
      .filter((item) => studentMatchesTarget(item, session, student))
      .filter((item) => !book || lower(item.livro).includes(`livro ${book}`));
    const individualWorkbookLessons = registeredWorkbookLessons.filter(hasWorkbookStudentTarget);
    const workbookBase = individualWorkbookLessons.length > 0
      ? individualWorkbookLessons
      : registeredWorkbookLessons;
    const released = releasedWorkbookLessons(workbookBase, studentSubmissions)
      .some((item) => text(item.id) === activityId);
    if (!released) {
      return NextResponse.json({ error: "Conclua a licao anterior antes de enviar esta atividade." }, { status: 403 });
    }
  }

  const answers = body.answers || {};
  const missing = (homework.questions || []).filter((question) => !text(answers[question.id]));
  if (missing.length > 0) {
    return NextResponse.json({ error: "Responda todas as questoes obrigatorias antes de enviar." }, { status: 400 });
  }

  const existingIdx = submissions.findIndex((item) => text(item.activity_id) === activityId && text(item.aluno_login) === text(session.usuario));
  if (existingIdx >= 0 && !homework.allow_resubmission) {
    return NextResponse.json({ error: "Esta licao ja foi enviada e nao permite reenvio." }, { status: 403 });
  }

  const aiGrade = await gradeHomeworkWithWiz(homework, answers);
  const canAutoCorrect = Boolean(aiGrade);
  const maxScore = (homework.questions || []).reduce((sum, question) => sum + (Number(question.pontos) || 0), 0) || 10;
  const submission: HomeworkSubmission = {
    ...(existingIdx >= 0 ? submissions[existingIdx] : {}),
    id: existingIdx >= 0 ? submissions[existingIdx].id : crypto.randomUUID(),
    activity_id: activityId,
    aluno: session.pessoa || session.usuario,
    aluno_login: session.usuario,
    turma: text(session.unit),
    answers,
    question_scores: aiGrade?.questionScores || {},
    score: aiGrade?.total || 0,
    feedback: aiGrade?.feedback,
    status: canAutoCorrect ? "Corrigido" : "Aguardando correcao IA",
    submitted_at: nowIso(),
    graded_at: canAutoCorrect ? nowIso() : undefined,
    graded_by: canAutoCorrect ? "Wiz IA" : undefined,
  };
  const next = existingIdx >= 0
    ? submissions.map((item, index) => index === existingIdx ? submission : item)
    : [...submissions, submission];
  if (canAutoCorrect) {
    const [grades, audit] = await Promise.all([
      dbList<Row>("grades.json"),
      dbList<Row>("grade_audit.json"),
    ]);
    const gradeId = `homework_${text(submission.id)}`;
    const gradeRecord = {
      id: gradeId,
      aluno: submission.aluno,
      aluno_login: submission.aluno_login,
      titulo: homework.titulo || "Licao de Casa",
      desafio: homework.titulo || "Licao de Casa",
      disciplina: homework.disciplina || "Ingles",
      turma: submission.turma || homework.turma,
      nota: aiGrade?.total || 0,
      pontos: aiGrade?.total || 0,
      total: maxScore,
      status: "Corrigido",
      origem: "Licao de Casa",
      origem_id: submission.activity_id,
      corrigido_por: "Wiz IA",
      data: nowIso(),
    };
    const gradeIdx = grades.findIndex((grade) => text(grade.id) === gradeId);
    const nextGrades = gradeIdx >= 0
      ? grades.map((grade, index) => index === gradeIdx ? { ...grade, ...gradeRecord } : grade)
      : [...grades, gradeRecord];
    const auditEntry = {
      id: crypto.randomUUID(),
      tipo: gradeIdx >= 0 ? "alteracao_nota_licao_automatica" : "lancamento_nota_licao_automatica",
      submission_id: submission.id,
      activity_id: submission.activity_id,
      aluno: submission.aluno,
      nota: aiGrade?.total || 0,
      usuario: "Wiz IA",
      perfil: "sistema",
      resumo: aiGrade?.summary,
      data: nowIso(),
    };
    await Promise.all([
      dbSet("activity_submissions.json", next),
      dbSet("grades.json", nextGrades),
      dbSet("grade_audit.json", [...audit, auditEntry]),
    ]);
  } else {
    await dbSet("activity_submissions.json", next);
  }
  return NextResponse.json(submission, { status: 201 });
}
