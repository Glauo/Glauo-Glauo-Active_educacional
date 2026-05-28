import { NextRequest, NextResponse } from "next/server";
import { getSession } from "@/lib/auth";
import { dbList, dbSet } from "@/lib/db";
import { isAdminOrCoordinator } from "@/lib/roles";

type Row = Record<string, unknown>;

const ATTENDANCE_KEY = "attendance.json";

function text(value: unknown) {
  return String(value || "").trim();
}

function manualDateIso(value: unknown) {
  const raw = text(value);
  if (/^\d{4}-\d{2}-\d{2}$/.test(raw)) return `${raw}T12:00:00-03:00`;
  const parsed = raw ? new Date(raw) : new Date();
  return Number.isNaN(parsed.getTime()) ? new Date().toISOString() : parsed.toISOString();
}

export async function POST(req: NextRequest) {
  const session = await getSession();
  if (!session || !isAdminOrCoordinator(session)) {
    return NextResponse.json({ error: "Apenas administradores e coordenadores podem lancar faltas." }, { status: 403 });
  }

  const body = await req.json() as Row;
  const aluno = text(body.aluno);
  const alunoId = text(body.aluno_id || body.alunoId || body.login);
  const data = manualDateIso(body.data || body.data_aula);

  if (!aluno || !data) {
    return NextResponse.json({ error: "Aluno e data da falta sao obrigatorios." }, { status: 400 });
  }

  const frequencias = await dbList<Row>(ATTENDANCE_KEY);
  const registro: Row = {
    id: crypto.randomUUID(),
    aula_id: text(body.aula_id) || `manual_${Date.now()}`,
    turma_id: text(body.turma_id || body.turma),
    turma: text(body.turma),
    professor: text(body.professor || session.pessoa || session.usuario),
    aluno_id: alunoId,
    aluno,
    presente: false,
    falta: true,
    manual: true,
    origem: "lancamento_manual_adm",
    livro: text(body.livro),
    licao_inicio: text(body.licao_inicio),
    licao_fim: text(body.licao_fim),
    materia: text(body.materia || "Lancamento manual"),
    tarefa: text(body.tarefa),
    observacoes: text(body.observacoes),
    data,
    criado_por: session.pessoa || session.usuario,
    created_at: new Date().toISOString(),
  };

  await dbSet(ATTENDANCE_KEY, [...frequencias, registro]);
  return NextResponse.json(registro, { status: 201 });
}
