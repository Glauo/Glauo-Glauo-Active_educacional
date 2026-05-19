import { NextRequest, NextResponse } from "next/server";
import { getSession } from "@/lib/auth";
import { dbList, dbSet } from "@/lib/db";
import { canManageAllSchoolContent, homeworkTotal, nowIso, text, type Homework, type HomeworkSubmission, type Row } from "@/lib/school-modules";

export async function POST(req: NextRequest) {
  const session = await getSession();
  if (!session || !canManageAllSchoolContent(session)) {
    return NextResponse.json({ error: "Nao autorizado" }, { status: 401 });
  }
  const body = (await req.json()) as { submission_id?: string; score?: number; feedback?: string; question_scores?: Record<string, number> };
  const submissionId = text(body.submission_id);
  const submissions = await dbList<HomeworkSubmission>("activity_submissions.json");
  const idx = submissions.findIndex((item) => text(item.id) === submissionId);
  if (idx === -1) return NextResponse.json({ error: "Entrega nao encontrada." }, { status: 404 });
  const existing = submissions[idx];
  if (text(existing.status).toLowerCase().includes("corrigido") && !canManageAllSchoolContent(session)) {
    return NextResponse.json({ error: "Nota ja lancada. Alteracao exige permissao de coordenacao." }, { status: 403 });
  }

  const activities = await dbList<Homework>("activities.json");
  const homework = activities.find((item) => text(item.id) === text(existing.activity_id));
  const maxScore = homework ? homeworkTotal(homework) : 100;
  const score = Math.max(0, Math.min(Number(body.score) || 0, maxScore || 100));
  const reviewed: HomeworkSubmission = {
    ...existing,
    score,
    feedback: text(body.feedback),
    question_scores: body.question_scores || existing.question_scores || {},
    status: "Corrigido",
    graded_at: nowIso(),
    graded_by: session.pessoa || session.usuario,
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
    titulo: homework?.titulo || "Licao de Casa",
    desafio: homework?.titulo || "Licao de Casa",
    disciplina: homework?.disciplina || "Geral",
    turma: reviewed.turma || homework?.turma,
    nota: score,
    pontos: score,
    total: maxScore,
    status: "Corrigido",
    origem: "Licao de Casa",
    origem_id: reviewed.activity_id,
    corrigido_por: session.pessoa || session.usuario,
    data: nowIso(),
  };
  const gradeIdx = grades.findIndex((grade) => text(grade.id) === gradeId);
  const nextGrades = gradeIdx >= 0 ? grades.map((grade, index) => index === gradeIdx ? { ...grade, ...gradeRecord } : grade) : [...grades, gradeRecord];
  const auditEntry = {
    id: crypto.randomUUID(),
    tipo: gradeIdx >= 0 ? "alteracao_nota_licao" : "lancamento_nota_licao",
    submission_id: reviewed.id,
    activity_id: reviewed.activity_id,
    aluno: reviewed.aluno,
    nota: score,
    usuario: session.pessoa || session.usuario,
    perfil: session.perfil,
    data: nowIso(),
  };

  await Promise.all([
    dbSet("activity_submissions.json", submissions),
    dbSet("grades.json", nextGrades),
    dbSet("grade_audit.json", [...audit, auditEntry]),
  ]);
  return NextResponse.json(reviewed);
}
