import { homeworkEvaluationMessage } from "./homework-feedback";
import { homeworkTotal, text, type Homework, type HomeworkQuestion } from "./school-modules";

type AiGradeResult = {
  questionScores: Record<string, number>;
  total: number;
  feedback: string;
  summary: string;
};

function modelName() {
  return process.env.ACTIVE_HOMEWORK_GRADER_MODEL ||
    process.env.ACTIVE_WIZ_MODEL ||
    process.env.ACTIVE_CHATBOT_MODEL ||
    "llama-3.3-70b-versatile";
}

function apiKey() {
  return text(process.env.GROQ_API_KEY || process.env.ACTIVE_GROQ_API_KEY || process.env.OPENAI_API_KEY);
}

function apiBase() {
  return text(process.env.ACTIVE_AI_BASE_URL) || (process.env.OPENAI_API_KEY && !process.env.GROQ_API_KEY && !process.env.ACTIVE_GROQ_API_KEY
    ? "https://api.openai.com/v1"
    : "https://api.groq.com/openai/v1");
}

function answerFor(question: HomeworkQuestion, answers: Record<string, unknown>, index: number) {
  const raw = text(answers[question.id]);
  const fallback = text(Object.values(answers)[index]);
  const value = raw || fallback;
  if (question.tipo === "multipla_escolha") {
    const optionIndex = Number(value);
    const option = Number.isFinite(optionIndex) ? question.opcoes?.[optionIndex] : "";
    return option ? `${String.fromCharCode(65 + optionIndex)}) ${option}` : value;
  }
  if (question.tipo === "verdadeiro_falso") {
    const low = value.toLowerCase();
    if (["1", "true", "v", "verdadeiro"].includes(low)) return "Verdadeiro";
    if (["0", "false", "f", "falso"].includes(low)) return "Falso";
  }
  return value;
}

function extractJson(raw: string) {
  const cleaned = raw.trim().replace(/^```(?:json)?/i, "").replace(/```$/i, "").trim();
  try { return JSON.parse(cleaned) as Record<string, unknown>; } catch { /**/ }
  const match = cleaned.match(/\{[\s\S]*\}/);
  if (!match) return null;
  try { return JSON.parse(match[0]) as Record<string, unknown>; } catch { return null; }
}

function clampScore(value: unknown, max: number) {
  const n = Number(value);
  if (!Number.isFinite(n)) return 0;
  return Math.max(0, Math.min(Number(n.toFixed(1)), max));
}

export async function gradeHomeworkWithWiz(homework: Homework, answers: Record<string, unknown>): Promise<AiGradeResult | null> {
  const key = apiKey();
  if (!key) return null;

  const questions = homework.questions || [];
  const maxScore = homeworkTotal(homework) || 10;
  const payload = questions.map((question, index) => ({
    id: question.id,
    tipo: question.tipo,
    enunciado: question.enunciado,
    opcoes: question.opcoes || [],
    pontos: Number(question.pontos) || 0,
    resposta_aluno: answerFor(question, answers, index),
  }));

  const prompt = [
    "Voce e a Wiz IA corrigindo avaliacoes e licoes de ingles do Mister Wiz.",
    "Corrija SEM usar respostas cadastradas no sistema. Use apenas o enunciado, alternativas, contexto e resposta do aluno.",
    "Para multipla escolha ou verdadeiro/falso, escolha se a resposta do aluno faz sentido linguisticamente e conceitualmente.",
    "Para resposta aberta/upload textual, avalie clareza, ingles, completude e aderencia ao enunciado.",
    "A nota de cada questao deve ficar entre 0 e os pontos da questao.",
    "Responda somente JSON valido no formato:",
    '{"questionScores":{"id_da_questao":0},"summary":"resumo curto da correcao"}',
    "",
    `Atividade: ${text(homework.titulo || "Licao de Casa")}`,
    `Descricao: ${text(homework.descricao)}`,
    `Disciplina: ${text(homework.disciplina || "Ingles")}`,
    `Total maximo: ${maxScore}`,
    `Questoes e respostas: ${JSON.stringify(payload)}`,
  ].join("\n");

  try {
    const res = await fetch(`${apiBase().replace(/\/$/, "")}/chat/completions`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${key}`,
      },
      body: JSON.stringify({
        model: modelName(),
        temperature: 0.05,
        max_tokens: 1800,
        messages: [
          { role: "system", content: "Voce corrige atividades escolares com criterio pedagogico, sem depender de respostas pre-cadastradas." },
          { role: "user", content: prompt },
        ],
      }),
    });
    if (!res.ok) return null;
    const data = await res.json().catch(() => ({})) as { choices?: Array<{ message?: { content?: string } }> };
    const parsed = extractJson(text(data.choices?.[0]?.message?.content));
    const rawScores = (parsed?.questionScores || {}) as Record<string, unknown>;
    const questionScores: Record<string, number> = {};
    for (const question of questions) {
      questionScores[question.id] = clampScore(rawScores[question.id], Number(question.pontos) || 0);
    }
    const total = clampScore(Object.values(questionScores).reduce((sum, value) => sum + value, 0), maxScore);
    return {
      questionScores,
      total,
      feedback: homeworkEvaluationMessage(total, maxScore),
      summary: text(parsed?.summary) || "Corrigida automaticamente pela Wiz IA.",
    };
  } catch {
    return null;
  }
}
