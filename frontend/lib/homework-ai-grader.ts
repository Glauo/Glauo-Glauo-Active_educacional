import { homeworkEvaluationMessage } from "./homework-feedback";
import { dbGet } from "./db";
import { homeworkTotal, text, type Homework, type HomeworkQuestion } from "./school-modules";

type AiGradeResult = {
  questionScores: Record<string, number>;
  total: number;
  feedback: string;
  summary: string;
};

type AiConfig = {
  key: string;
  model: string;
  base: string;
};

async function aiConfig(): Promise<AiConfig> {
  const [sistema, wiz] = await Promise.all([
    dbGet<Record<string, unknown>>("sistema_config.json"),
    dbGet<Record<string, unknown>>("wiz_settings.json"),
  ]);
  const key = text(
    process.env.ACTIVE_HOMEWORK_GRADER_API_KEY ||
    process.env.ACTIVE_GROQ_API_KEY ||
    process.env.GROQ_API_KEY ||
    process.env.ACTIVE_OPENAI_API_KEY ||
    process.env.OPENAI_API_KEY ||
    wiz?.ACTIVE_HOMEWORK_GRADER_API_KEY ||
    wiz?.ACTIVE_GROQ_API_KEY ||
    wiz?.GROQ_API_KEY ||
    wiz?.api_key ||
    sistema?.ACTIVE_GROQ_API_KEY ||
    sistema?.GROQ_API_KEY ||
    sistema?.OPENAI_API_KEY
  );
  const model = text(
    process.env.ACTIVE_HOMEWORK_GRADER_MODEL ||
    process.env.ACTIVE_WIZ_MODEL ||
    process.env.ACTIVE_CHATBOT_MODEL ||
    wiz?.ACTIVE_HOMEWORK_GRADER_MODEL ||
    wiz?.ACTIVE_WIZ_MODEL ||
    wiz?.model ||
    sistema?.ACTIVE_HOMEWORK_GRADER_MODEL ||
    sistema?.ACTIVE_WIZ_MODEL ||
    sistema?.ACTIVE_CHATBOT_MODEL ||
    "llama-3.3-70b-versatile"
  );
  const base = text(
    process.env.ACTIVE_AI_BASE_URL ||
    wiz?.ACTIVE_AI_BASE_URL ||
    wiz?.api_base ||
    sistema?.ACTIVE_AI_BASE_URL ||
    ((process.env.OPENAI_API_KEY || process.env.ACTIVE_OPENAI_API_KEY) && !process.env.GROQ_API_KEY && !process.env.ACTIVE_GROQ_API_KEY
      ? "https://api.openai.com/v1"
      : "https://api.groq.com/openai/v1")
  );
  return { key, model, base };
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

function normalize(value: unknown) {
  return text(value)
    .toLowerCase()
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .replace(/[^a-z0-9]+/g, " ")
    .trim();
}

function selectedOption(question: HomeworkQuestion, rawAnswer: string) {
  const numeric = Number(rawAnswer);
  if (Number.isFinite(numeric) && question.opcoes?.[numeric]) return question.opcoes[numeric];
  const letter = rawAnswer.trim().toUpperCase().match(/^[A-Z]/)?.[0];
  if (letter) {
    const idx = letter.charCodeAt(0) - 65;
    if (question.opcoes?.[idx]) return question.opcoes[idx];
  }
  return rawAnswer;
}

function localGrade(homework: Homework, answers: Record<string, unknown>, reason: string): AiGradeResult {
  const questions = homework.questions || [];
  const maxScore = homeworkTotal(homework) || 10;
  const questionScores: Record<string, number> = {};

  for (const [index, question] of questions.entries()) {
    const max = Number(question.pontos) || 0;
    const rawAnswer = text(answers[question.id]) || text(Object.values(answers)[index]);
    if (!rawAnswer) {
      questionScores[question.id] = 0;
      continue;
    }

    if (question.tipo === "multipla_escolha" && question.correta_idx !== null && question.correta_idx !== undefined) {
      const selected = normalize(selectedOption(question, rawAnswer));
      const expected = normalize(question.opcoes?.[Number(question.correta_idx)]);
      questionScores[question.id] = selected && expected && selected === expected ? max : 0;
      continue;
    }

    if (question.tipo === "verdadeiro_falso" && text(question.correta_texto)) {
      const answer = normalize(answerFor(question, answers, index));
      const expected = normalize(question.correta_texto);
      questionScores[question.id] = answer === expected ? max : 0;
      continue;
    }

    if (text(question.correta_texto)) {
      const answer = normalize(rawAnswer);
      const expected = normalize(question.correta_texto);
      questionScores[question.id] = answer && expected && (answer === expected || answer.includes(expected) || expected.includes(answer)) ? max : 0;
      continue;
    }

    questionScores[question.id] = clampScore(max * 0.7, max);
  }

  const total = clampScore(Object.values(questionScores).reduce((sum, value) => sum + value, 0), maxScore);
  return {
    questionScores,
    total,
    feedback: homeworkEvaluationMessage(total, maxScore),
    summary: `${reason} A Wiz IA aplicou uma correcao local para nao travar o lancamento. Revise respostas abertas quando necessario.`,
  };
}

export async function gradeHomeworkWithWiz(homework: Homework, answers: Record<string, unknown>): Promise<AiGradeResult> {
  const config = await aiConfig();
  if (!config.key) return localGrade(homework, answers, "Chave de IA externa nao configurada.");

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
    const res = await fetch(`${config.base.replace(/\/$/, "")}/chat/completions`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${config.key}`,
      },
      body: JSON.stringify({
        model: config.model,
        temperature: 0.05,
        max_tokens: 1800,
        messages: [
          { role: "system", content: "Voce corrige atividades escolares com criterio pedagogico, sem depender de respostas pre-cadastradas." },
          { role: "user", content: prompt },
        ],
      }),
    });
    if (!res.ok) return localGrade(homework, answers, `Servico de IA retornou HTTP ${res.status}.`);
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
    return localGrade(homework, answers, "Servico de IA indisponivel no momento.");
  }
}
