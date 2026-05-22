import { dbList, dbListWithoutKeys } from "@/lib/db";
import { getSession } from "@/lib/auth";
import { redirect } from "next/navigation";
import { StudentPortalClient } from "@/components/student-portal-client";
import { isHomeworkActivity, studentMatchesTarget, text, type Homework, type HomeworkSubmission, type WallPost } from "@/lib/school-modules";
import { hasWorkbookStudentTarget, releasedWorkbookLessons, studentWorkbookBook } from "@/lib/workbook-lessons";

type Aluno = { id?: string; nome?: string; name?: string; login?: string; turma?: string; classe?: string; livro?: string; book?: string; status?: string; [k: string]: unknown };
type Desafio = { id?: string; titulo?: string; title?: string; turma?: string; pontos?: number | string; status?: string; [k: string]: unknown };
type Conclusao = { desafio_id?: string; aluno?: string; pontos?: number | string; data?: string; [k: string]: unknown };
type Nota = { aluno?: string; aluno_login?: string; titulo?: string; desafio?: string; nota?: number | string; status?: string; data?: string; [k: string]: unknown };
type Recebimento = { id?: string; aluno?: string; nome?: string; aluno_login?: string; aluno_id?: string; descricao?: string; valor?: number | string; valor_parcela?: number | string; vencimento?: string; data_vencimento?: string; status?: string; [k: string]: unknown };

const HEAVY_KEYS = ["boleto_pdf_b64", "file_b64", "pdf_b64", "base64", "arquivo_b64", "foto_b64", "imagem_b64", "documento_b64", "anexo_b64"];

function lower(value: unknown) {
  return text(value).toLowerCase();
}

function sameStudentInvoice(row: Recebimento, aluno: Aluno | undefined, session: { usuario: string; pessoa: string }) {
  const possible = [
    row.aluno_login,
    row.aluno_id,
    row.aluno,
    row.nome,
  ].map(lower).filter(Boolean);
  const studentKeys = [
    session.usuario,
    session.pessoa,
    aluno?.id,
    aluno?.login,
    aluno?.nome,
    aluno?.name,
  ].map(lower).filter(Boolean);
  return possible.some((item) => studentKeys.includes(item));
}

function matchesAgenda(row: Record<string, unknown>, aluno: Aluno | undefined, turma: string, session: { usuario: string; pessoa: string }) {
  const targetStudent = lower(row.aluno || row.aluno_nome || row.aluno_login);
  if (targetStudent) {
    return [session.usuario, session.pessoa, aluno?.nome, aluno?.name, aluno?.login].map(lower).includes(targetStudent);
  }
  const targetClass = lower(row.turma || row.classe || row.target_turma);
  if (!targetClass || ["todas", "todos", "escola toda"].includes(targetClass)) return true;
  return targetClass === lower(turma);
}

function visibleChallenge(row: Desafio, session: NonNullable<Awaited<ReturnType<typeof getSession>>>, aluno?: Aluno) {
  const status = lower(row.status || "publicado");
  if (status.includes("rascunho") || status.includes("arquiv") || status.includes("inativ") || status.includes("cancel")) return false;
  return studentMatchesTarget(row, session, aluno);
}

export default async function AlunoHomePage() {
  const session = await getSession();
  if (!session) redirect("/aluno/login");
  if (!lower(session.perfil).includes("aluno")) redirect("/");

  const [alunos, desafios, conclusoes, notas, frequencias, recebimentos, mensagens, atividades, entregas, agenda] = await Promise.all([
    dbListWithoutKeys<Aluno>("students.json", HEAVY_KEYS),
    dbList<Desafio>("challenges.json"),
    dbList<Conclusao>("challenge_completions.json"),
    dbList<Nota>("grades.json"),
    dbList<Record<string, unknown>>("attendance.json"),
    dbListWithoutKeys<Recebimento>("receivables.json", HEAVY_KEYS),
    dbList<WallPost>("messages.json"),
    dbList<Homework>("activities.json"),
    dbList<HomeworkSubmission>("activity_submissions.json"),
    dbList<Record<string, unknown>>("agenda.json"),
  ]);

  const meuPerfil = alunos.find((a) => lower(a.login) === lower(session.usuario) || lower(a.nome || a.name) === lower(session.pessoa));
  const minhaTurma = text(meuPerfil?.turma || meuPerfil?.classe || session.unit);
  const sessionLite = { usuario: session.usuario, pessoa: session.pessoa || session.usuario, unit: session.unit };

  const muralPosts = mensagens
    .filter((post) => studentMatchesTarget(post, session, meuPerfil))
    .sort((a, b) => {
      if (Boolean(a.fixado) !== Boolean(b.fixado)) return Boolean(a.fixado) ? -1 : 1;
      return text(b.publicado_em || b.data).localeCompare(text(a.publicado_em || a.data));
    });

  const minhasEntregas = entregas.filter((entrega) => lower(entrega.aluno_login) === lower(session.usuario) || lower(entrega.aluno) === lower(session.pessoa));
  const licoesCadastradas = atividades
    .filter(isHomeworkActivity)
    .filter((atividade) => studentMatchesTarget(atividade, session, meuPerfil))
    .filter((atividade) => !lower(atividade.status).includes("rascunho"));
  const workbookBook = studentWorkbookBook(meuPerfil, session.unit);
  const licoesWorkbookCadastradas = licoesCadastradas
    .filter((atividade) => lower(atividade.origem).includes("workbook"))
    .filter((atividade) => !workbookBook || lower(atividade.livro).includes(`livro ${workbookBook}`));
  const licoesNaoWorkbook = licoesCadastradas.filter((atividade) => !lower(atividade.origem).includes("workbook"));
  const licoesWorkbookIndividuais = licoesWorkbookCadastradas.filter(hasWorkbookStudentTarget);
  const workbookBase = licoesWorkbookIndividuais.length > 0
    ? licoesWorkbookIndividuais
    : licoesWorkbookCadastradas;
  const workbookLicoes = releasedWorkbookLessons(workbookBase, minhasEntregas);
  const licoes = [...licoesNaoWorkbook, ...workbookLicoes];

  const minhasNotas = notas.filter((n) => lower(n.aluno) === lower(session.pessoa) || lower(n.aluno_login) === lower(session.usuario));
  const minhasFaturas = recebimentos
    .filter((r) => sameStudentInvoice(r, meuPerfil, sessionLite))
    .sort((a, b) => text(a.vencimento || a.data_vencimento).localeCompare(text(b.vencimento || b.data_vencimento)));
  const meusDesafios = desafios.filter((d) => visibleChallenge(d, session, meuPerfil));
  const minhasConclusoes = conclusoes.filter((c) => lower(c.aluno) === lower(session.usuario) || lower(c.aluno) === lower(session.pessoa));
  const minhasFaltas = frequencias.filter((f) => (lower(f.aluno) === lower(session.pessoa) || lower(f.aluno_id) === lower(meuPerfil?.id || session.usuario)) && Boolean(f.falta)).length;
  const minhaAgenda = agenda
    .filter((item) => matchesAgenda(item, meuPerfil, minhaTurma, sessionLite))
    .sort((a, b) => text(a.data || a.date).localeCompare(text(b.data || b.date)));

  return (
    <StudentPortalClient
      session={sessionLite}
      perfil={meuPerfil || null}
      muralPosts={muralPosts}
      licoes={licoes}
      entregas={minhasEntregas}
      notas={minhasNotas}
      faturas={minhasFaturas}
      desafios={meusDesafios}
      conclusoes={minhasConclusoes}
      agenda={minhaAgenda}
      faltas={minhasFaltas}
    />
  );
}
