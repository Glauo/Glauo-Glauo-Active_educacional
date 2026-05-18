import { NextRequest, NextResponse } from "next/server";
import { getSession } from "@/lib/auth";
import { dbList, dbSet } from "@/lib/db";
import { autoScore, lower, nowIso, studentMatchesTarget, text, type Homework, type HomeworkSubmission, type Row } from "@/lib/school-modules";
import { getWorkbookHomeworkById, releasedWorkbookLessons, studentWorkbookBook, workbookLessonsForBook } from "@/lib/workbook-lessons";

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
  let homework = activities.find((item) => text(item.id) === activityId);
  if (!homework) {
    const workbookHomework = getWorkbookHomeworkById(activityId);
    const book = studentWorkbookBook(student, session.unit);
    const studentSubmissions = submissions.filter((item) => text(item.aluno_login) === text(session.usuario) || text(item.aluno) === text(session.pessoa));
    const workbookLessons = releasedWorkbookLessons(workbookLessonsForBook(book), studentSubmissions);
    const released = workbookLessons.some((item) => text(item.id) === activityId);
    if (workbookHomework && released && text(workbookHomework.livro).includes(text(book))) {
      homework = workbookHomework;
    }
  }
  if (!homework) return NextResponse.json({ error: "Licao nao encontrada." }, { status: 404 });

  if (lower(homework.origem).includes("workbook")) {
    const book = studentWorkbookBook(student, session.unit);
    const studentSubmissions = submissions.filter((item) => text(item.aluno_login) === text(session.usuario) || text(item.aluno) === text(session.pessoa));
    const registeredWorkbookLessons = activities
      .filter((item) => lower(item.origem).includes("workbook"))
      .filter((item) => studentMatchesTarget(item, session, student))
      .filter((item) => !book || lower(item.livro).includes(`livro ${book}`));
    const workbookBase = registeredWorkbookLessons.length > 0 ? registeredWorkbookLessons : workbookLessonsForBook(book);
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

  const scored = autoScore(homework, answers);
  const submission: HomeworkSubmission = {
    ...(existingIdx >= 0 ? submissions[existingIdx] : {}),
    id: existingIdx >= 0 ? submissions[existingIdx].id : crypto.randomUUID(),
    activity_id: activityId,
    aluno: session.pessoa || session.usuario,
    aluno_login: session.usuario,
    turma: text(session.unit),
    answers,
    question_scores: scored.questionScores,
    score: scored.total,
    status: "Aguardando correcao",
    submitted_at: nowIso(),
  };
  const next = existingIdx >= 0
    ? submissions.map((item, index) => index === existingIdx ? submission : item)
    : [...submissions, submission];
  await dbSet("activity_submissions.json", next);
  return NextResponse.json(submission, { status: 201 });
}
