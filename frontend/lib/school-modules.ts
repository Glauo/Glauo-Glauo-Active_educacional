import type { SessionUser } from "./auth";

export type Row = Record<string, unknown>;

export type WallPost = Row & {
  id?: string;
  titulo?: string;
  mensagem?: string;
  tipo_post?: string;
  turma?: string;
  turmas?: string[];
  publico?: string;
  aluno?: string;
  autor?: string;
  data?: string;
  status?: string;
  fixado?: boolean;
  requer_confirmacao?: boolean;
  confirmacoes?: ReadReceipt[];
  enquete_opcoes?: string[];
  votos?: PollVote[];
};

export type ReadReceipt = {
  usuario: string;
  nome: string;
  perfil: string;
  data: string;
};

export type PollVote = {
  usuario: string;
  nome: string;
  opcao: string;
  data: string;
};

export type HomeworkQuestion = {
  id: string;
  tipo: "aberta" | "multipla_escolha" | "verdadeiro_falso" | "upload";
  enunciado: string;
  opcoes?: string[];
  correta_idx?: number | null;
  correta_texto?: string;
  pontos: number;
  feedback?: string;
};

export type Homework = Row & {
  id?: string;
  tipo?: string;
  titulo?: string;
  descricao?: string;
  disciplina?: string;
  turma?: string;
  turmas?: string[];
  aluno?: string;
  alunos?: string[];
  livro?: string;
  capitulo?: string;
  aula_referencia?: string;
  habilidade?: string;
  due_date?: string;
  peso?: number;
  status?: string;
  autor?: string;
  questions?: HomeworkQuestion[];
  allow_resubmission?: boolean;
};

export type HomeworkSubmission = Row & {
  id?: string;
  activity_id?: string;
  aluno?: string;
  aluno_login?: string;
  turma?: string;
  answers?: Record<string, string>;
  status?: string;
  score?: number;
  feedback?: string;
  question_scores?: Record<string, number>;
  submitted_at?: string;
  graded_at?: string;
  graded_by?: string;
};

export function text(value: unknown) {
  return String(value || "").trim();
}

export function lower(value: unknown) {
  return text(value).toLowerCase();
}

export function todayPtBr() {
  return new Date().toLocaleDateString("pt-BR");
}

export function nowIso() {
  return new Date().toISOString();
}

export function canManageSchoolContent(session: Pick<SessionUser, "perfil"> | null) {
  const perfil = lower(session?.perfil);
  return perfil.includes("admin") || perfil.includes("coord") || perfil.includes("prof");
}

export function canManageAllSchoolContent(session: Pick<SessionUser, "perfil"> | null) {
  const perfil = lower(session?.perfil);
  return perfil.includes("admin") || perfil.includes("coord") || perfil.includes("dire");
}

export function getStudentName(session: Pick<SessionUser, "pessoa" | "usuario">) {
  return text(session.pessoa || session.usuario);
}

export function normalizeList(value: unknown): string[] {
  if (Array.isArray(value)) return value.map(text).filter(Boolean);
  return text(value)
    .split(/[,\n;]/)
    .map((item) => item.trim())
    .filter(Boolean);
}

export function studentMatchesTarget(item: Row, session: SessionUser, student?: Row | null) {
  const studentName = getStudentName(session);
  const studentLogin = text(session.usuario);
  const studentClass = text(student?.turma || student?.classe || session.unit);
  const targetStudent = text(item.aluno || item.aluno_nome || item.target_aluno);
  const targetStudents = normalizeList(item.alunos || item.alunos_especificos);
  const targetClass = text(item.turma || item.target_turma);
  const targetClasses = normalizeList(item.turmas || item.target_turmas || item.target_turmas_envio);
  const publico = lower(item.publico || item.destinatarios);

  if (targetStudent && lower(targetStudent) !== lower(studentName) && lower(targetStudent) !== lower(studentLogin)) {
    return false;
  }
  if (targetStudents.length > 0 && !targetStudents.some((name) => lower(name) === lower(studentName) || lower(name) === lower(studentLogin))) {
    return false;
  }
  if (targetClass && !["todas", "todos", "escola toda"].includes(lower(targetClass)) && lower(targetClass) !== lower(studentClass)) {
    return false;
  }
  if (targetClasses.length > 0 && !targetClasses.some((turma) => ["todas", "todos", "escola toda"].includes(lower(turma)) || lower(turma) === lower(studentClass))) {
    return false;
  }
  if (publico.includes("professor") || publico.includes("coord")) return false;
  return true;
}

export function isHomeworkActivity(activity: Row) {
  const combined = `${text(activity.tipo)} ${text(activity.titulo)} ${text(activity.origem)}`.toLowerCase();
  return combined.includes("licao") || combined.includes("lição") || combined.includes("homework") || combined.includes("tarefa de casa");
}

export function homeworkTotal(homework: Homework) {
  const questions = Array.isArray(homework.questions) ? homework.questions : [];
  return questions.reduce((sum, question) => sum + (Number(question.pontos) || 0), 0);
}

export function autoScore(homework: Homework, answers: Record<string, string>) {
  const questionScores: Record<string, number> = {};
  let total = 0;
  for (const question of homework.questions || []) {
    const answer = text(answers[question.id]);
    let score = 0;
    if (question.tipo === "multipla_escolha" && question.correta_idx !== null && question.correta_idx !== undefined) {
      score = Number(answer) === Number(question.correta_idx) ? Number(question.pontos) || 0 : 0;
    } else if (question.tipo === "verdadeiro_falso" && question.correta_texto) {
      score = lower(answer) === lower(question.correta_texto) ? Number(question.pontos) || 0 : 0;
    }
    questionScores[question.id] = score;
    total += score;
  }
  return { total, questionScores };
}

export function tagBadge(kind?: string) {
  const value = lower(kind);
  if (value.includes("urgent")) return "danger";
  if (value.includes("evento")) return "gold";
  if (value.includes("pedag")) return "info";
  if (value.includes("conquista")) return "success";
  if (value.includes("importante")) return "warning";
  return "neutral";
}
