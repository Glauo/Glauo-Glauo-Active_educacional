import { NextRequest, NextResponse } from "next/server";
import { getSession } from "@/lib/auth";
import { gradeHomeworkWithWiz } from "@/lib/homework-ai-grader";
import { canManageAllSchoolContent, type Homework, type HomeworkSubmission } from "@/lib/school-modules";

export async function POST(req: NextRequest) {
  const session = await getSession();
  if (!session || !canManageAllSchoolContent(session)) {
    return NextResponse.json({ error: "Nao autorizado" }, { status: 401 });
  }

  const body = (await req.json()) as { submission: HomeworkSubmission; homework: Homework };
  const { submission, homework } = body;
  const answers = (submission.answers || {}) as Record<string, unknown>;
  const grade = await gradeHomeworkWithWiz(homework, answers);
  if (!grade) {
    return NextResponse.json({ error: "Wiz IA indisponivel. Configure GROQ_API_KEY ou ACTIVE_GROQ_API_KEY para corrigir automaticamente sem respostas cadastradas." }, { status: 503 });
  }
  return NextResponse.json({
    questionScores: grade.questionScores,
    suggestedTotal: grade.total,
    feedback: grade.feedback,
    summary: grade.summary,
  });
}
