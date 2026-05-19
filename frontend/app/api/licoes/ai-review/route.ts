import { NextRequest, NextResponse } from "next/server";
import { getSession } from "@/lib/auth";
import { canManageAllSchoolContent, text, type Homework, type HomeworkQuestion, type HomeworkSubmission } from "@/lib/school-modules";

function lower(v: unknown) { return text(v).toLowerCase(); }

function getAnswer(answers: Record<string, unknown>, questionId: string, idx: number): string {
  const byId = text(answers[questionId]);
  if (byId) return byId;
  const vals = Object.values(answers);
  return idx < vals.length ? text(vals[idx]) : "";
}

function scoreObjective(question: HomeworkQuestion, answer: string): { score: number; correct: boolean } {
  const pts = Number(question.pontos) || 0;
  if (!answer) return { score: 0, correct: false };
  if (question.tipo === "multipla_escolha" && question.correta_idx !== null && question.correta_idx !== undefined) {
    const correct = Number(answer) === Number(question.correta_idx);
    return { score: correct ? pts : 0, correct };
  }
  if (question.tipo === "verdadeiro_falso" && text(question.correta_texto)) {
    const norm = (v: string) => ["1", "true", "verdadeiro"].includes(lower(v)) ? "v" : ["0", "false", "falso"].includes(lower(v)) ? "f" : lower(v);
    const correct = norm(answer) === norm(text(question.correta_texto));
    return { score: correct ? pts : 0, correct };
  }
  return { score: 0, correct: false };
}

function scoreOpen(question: HomeworkQuestion, answer: string): number {
  const pts = Number(question.pontos) || 0;
  if (!answer.trim()) return 0;
  const words = answer.trim().split(/\s+/).length;
  const ratio = words < 5 ? 0.4 : words < 15 ? 0.6 : words < 30 ? 0.8 : 0.9;
  return Number((pts * ratio).toFixed(1));
}

export async function POST(req: NextRequest) {
  const session = await getSession();
  if (!session || !canManageAllSchoolContent(session)) {
    return NextResponse.json({ error: "Nao autorizado" }, { status: 401 });
  }

  const body = (await req.json()) as { submission: HomeworkSubmission; homework: Homework };
  const { submission, homework } = body;
  const questions = homework.questions || [];
  const answers = (submission.answers || {}) as Record<string, unknown>;

  const results = questions.map((q, idx) => {
    const raw = getAnswer(answers, q.id, idx);
    let suggestedScore = 0;
    let observation = "";

    if (q.tipo === "multipla_escolha" || q.tipo === "verdadeiro_falso") {
      const { score, correct } = scoreObjective(q, raw);
      suggestedScore = score;
      observation = !raw ? "Sem resposta." : correct ? "Correta conforme gabarito." : "Incorreta conforme gabarito.";
    } else {
      suggestedScore = scoreOpen(q, raw);
      const words = raw.trim().split(/\s+/).filter(Boolean).length;
      observation = !raw ? "Sem resposta registrada."
        : words < 5 ? "Resposta muito curta — verifique se o aluno desenvolveu o raciocinio."
        : words < 15 ? "Resposta parcial — avalie se os pontos principais foram abordados."
        : "Resposta com desenvolvimento adequado — valide o conteudo especifico.";
    }
    return { questionId: q.id, suggestedScore, observation, raw };
  });

  const suggestedTotal = Number(results.reduce((s, r) => s + r.suggestedScore, 0).toFixed(1));
  const totalMax = questions.reduce((s, q) => s + (Number(q.pontos) || 0), 0);
  const openCount = questions.filter(q => q.tipo === "aberta" || q.tipo === "upload").length;
  const missingCount = results.filter(r => !r.raw).length;
  const objectiveCount = questions.length - openCount;

  const lines = [
    `IA analisou ${questions.length} questao(oes).`,
    objectiveCount > 0 ? `${objectiveCount} objetiva(s) corrigida(s) automaticamente pelo gabarito.` : "",
    openCount > 0 ? `${openCount} dissertativa(s) com nota sugerida por extensao — valide o conteudo antes de salvar.` : "",
    missingCount > 0 ? `Atencao: ${missingCount} questao(oes) sem resposta registrada.` : "Entrega completa.",
    `Nota sugerida: ${suggestedTotal} / ${totalMax}.`,
  ].filter(Boolean).join(" ");

  const questionScores: Record<string, number> = {};
  for (const r of results) questionScores[r.questionId] = r.suggestedScore;

  return NextResponse.json({ questionScores, suggestedTotal, feedback: lines, details: results });
}
