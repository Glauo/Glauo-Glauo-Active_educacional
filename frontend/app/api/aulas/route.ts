import { NextRequest, NextResponse } from "next/server";
import { getSession } from "@/lib/auth";
import { dbList, dbSet } from "@/lib/db";
import { isAdminOrCoordinator, isTeacher, sameName } from "@/lib/roles";

type Row = Record<string, unknown>;

const CLASSES_KEY = "classes.json";
const TEACHERS_KEY = "teachers.json";
const SESSIONS_KEY = "class_sessions.json";
const PAYABLES_KEY = "payables.json";

function text(value: unknown) {
  return String(value || "").trim();
}

function moneyValue(value: unknown) {
  const n = parseFloat(String(value || "").replace(/[^\d.,-]/g, "").replace(",", "."));
  return Number.isFinite(n) ? n : 0;
}

function className(turma: Row) {
  return text(turma.nome || turma.name || turma.turma);
}

function classId(turma: Row) {
  return text(turma.id || className(turma));
}

function teacherName(professor: Row) {
  return text(professor.nome || professor.name || professor.pessoa);
}

function findClass(turmas: Row[], idOrName: string) {
  return turmas.find((t) => classId(t) === idOrName || className(t) === idOrName);
}

function canUseClass(session: NonNullable<Awaited<ReturnType<typeof getSession>>>, turma: Row) {
  if (isAdminOrCoordinator(session)) return true;
  if (!isTeacher(session)) return false;
  return sameName(session.pessoa || session.usuario, turma.professor);
}

export async function GET() {
  const session = await getSession();
  if (!session) return NextResponse.json({ error: "Não autorizado." }, { status: 401 });
  const aulas = await dbList<Row>(SESSIONS_KEY);
  const visible = isAdminOrCoordinator(session)
    ? aulas
    : aulas.filter((a) => sameName(a.professor, session.pessoa || session.usuario));
  return NextResponse.json({ aulas: visible });
}

export async function POST(req: NextRequest) {
  const session = await getSession();
  if (!session) return NextResponse.json({ error: "Não autorizado." }, { status: 401 });

  try {
    const body = await req.json();
    const action = text(body.action);
    const turmaRef = text(body.turmaId || body.turma || body.turmaNome);
    if (!turmaRef) return NextResponse.json({ error: "Turma obrigatória." }, { status: 400 });

    const [turmas, professores, aulas, despesas] = await Promise.all([
      dbList<Row>(CLASSES_KEY),
      dbList<Row>(TEACHERS_KEY),
      dbList<Row>(SESSIONS_KEY),
      dbList<Row>(PAYABLES_KEY)
    ]);

    const turma = findClass(turmas, turmaRef);
    if (!turma) return NextResponse.json({ error: "Turma não encontrada." }, { status: 404 });
    if (!canUseClass(session, turma)) return NextResponse.json({ error: "Sem permissão para esta turma." }, { status: 403 });

    const turmaId = classId(turma);
    const professor = text(turma.professor || body.professor || session.pessoa);
    const teacher: Row = professores.find((p) => sameName(teacherName(p), professor)) || {};
    const livro = text(turma.livro || turma.book || body.livro);
    const licaoAtual = text(turma.ultima_licao || turma.licao_atual || turma.ultima_aula || body.licao_inicio);

    if (action === "open") {
      const aberta = aulas.find((a) => a.status === "aberta" && text(a.turma_id) === turmaId);
      if (aberta) return NextResponse.json({ error: "Esta turma já possui aula aberta." }, { status: 409 });

      const aula = {
        id: crypto.randomUUID(),
        turma_id: turmaId,
        turma: className(turma),
        professor,
        professor_telefone: text(teacher.telefone || teacher.whatsapp || teacher.celular),
        professor_email: text(teacher.email),
        livro,
        licao_inicio: text(body.licao_inicio) || licaoAtual,
        status: "aberta",
        aberta_por: session.pessoa || session.usuario,
        inicio: new Date().toISOString(),
        created_at: new Date().toISOString()
      };

      const nextTurmas = turmas.map((t) => classId(t) === turmaId ? { ...t, aula_aberta_id: aula.id, aula_status: "Aberta" } : t);
      await Promise.all([dbSet(SESSIONS_KEY, [...aulas, aula]), dbSet(CLASSES_KEY, nextTurmas)]);
      return NextResponse.json({ ok: true, aula }, { status: 201 });
    }

    if (action === "close") {
      const aulaId = text(body.aulaId);
      const idx = aulas.findIndex((a) =>
        a.status === "aberta" &&
        (text(a.id) === aulaId || text(a.turma_id) === turmaId)
      );
      if (idx === -1) return NextResponse.json({ error: "Nenhuma aula aberta encontrada para esta turma." }, { status: 404 });

      const licaoFim = text(body.licao_fim || body.licao_final);
      if (!licaoFim) return NextResponse.json({ error: "Informe a lição em que a aula parou." }, { status: 400 });

      const valorAula = moneyValue(body.valor_aula || turma.valor_aula || teacher.valor_aula || teacher.valor_hora || teacher.valor);
      const base = aulas[idx];
      const fechada = {
        ...base,
        status: "fechada",
        licao_fim: licaoFim,
        observacoes: text(body.observacoes),
        valor_aula: valorAula,
        fechada_por: session.pessoa || session.usuario,
        fim: new Date().toISOString(),
        updated_at: new Date().toISOString()
      };
      const nextAulas = [...aulas];
      nextAulas[idx] = fechada;

      const nextTurmas = turmas.map((t) => classId(t) === turmaId ? {
        ...t,
        ultima_licao: licaoFim,
        ultima_aula: new Date().toISOString(),
        aula_aberta_id: "",
        aula_status: "Fechada"
      } : t);

      const aulaFechadaId = text(base.id);
      const alreadyPayable = despesas.some((d) => text(d.aula_id) === aulaFechadaId);
      const descricao = `Aula dada - ${className(turma)} - ${livro || "Livro não informado"} - lição ${text(base.licao_inicio) || "início"} até ${licaoFim}`;
      const payable = {
        id: crypto.randomUUID(),
        aula_id: aulaFechadaId,
        tipo_origem: "aula_professor",
        categoria: "Professor",
        aluno: professor,
        nome: professor,
        professor,
        professor_telefone: text(teacher.telefone || teacher.whatsapp || teacher.celular),
        professor_email: text(teacher.email),
        turma: className(turma),
        livro,
        licao_inicio: text(base.licao_inicio),
        licao_fim: licaoFim,
        descricao,
        valor: valorAula,
        vencimento: new Date().toISOString().slice(0, 10),
        status: "Pendente",
        created_at: new Date().toISOString()
      };

      await Promise.all([
        dbSet(SESSIONS_KEY, nextAulas),
        dbSet(CLASSES_KEY, nextTurmas),
        dbSet(PAYABLES_KEY, alreadyPayable ? despesas : [...despesas, payable])
      ]);

      return NextResponse.json({ ok: true, aula: fechada, financeiro: alreadyPayable ? null : payable });
    }

    return NextResponse.json({ error: "Ação inválida." }, { status: 400 });
  } catch (err) {
    console.error("[aulas POST]", err);
    return NextResponse.json({ error: "Erro ao processar aula." }, { status: 500 });
  }
}
