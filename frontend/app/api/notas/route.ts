import { NextRequest, NextResponse } from "next/server";
import { getSession } from "@/lib/auth";
import { dbList, dbSet } from "@/lib/db";
import { notifyStudentsAboutLaunch } from "@/lib/student-launch-notifications";

type Row = Record<string, unknown>;

function text(value: unknown) {
  return String(value || "").trim();
}

export async function GET() {
  const session = await getSession();
  if (!session) return NextResponse.json({ error: "Nao autorizado" }, { status: 401 });
  const notas = await dbList<Row>("grades.json");
  if (session.perfil === "Aluno") {
    return NextResponse.json(notas.filter((n) => text(n.aluno) === session.pessoa || text(n.aluno_login) === session.usuario));
  }
  return NextResponse.json(notas);
}

export async function POST(req: NextRequest) {
  const session = await getSession();
  if (!session || session.perfil === "Aluno") return NextResponse.json({ error: "Nao autorizado" }, { status: 401 });

  const body = await req.json() as Row;
  const aluno = text(body.aluno);
  const titulo = text(body.titulo || body.desafio);
  const nota = Number(body.nota);
  if (!aluno || !titulo || !Number.isFinite(nota)) {
    return NextResponse.json({ error: "Aluno, desafio/titulo e nota sao obrigatorios." }, { status: 400 });
  }

  const [notas, conclusoes, students] = await Promise.all([
    dbList<Row>("grades.json"),
    dbList<Row>("challenge_completions.json"),
    dbList<Row>("students.json")
  ]);
  const id = text(body.id) || crypto.randomUUID();
  const registro: Row = {
    ...body,
    id,
    aluno,
    titulo,
    desafio: titulo,
    nota,
    pontos: Number(body.pontos || nota),
    corrigido_por: session.pessoa || session.usuario,
    status: "Corrigido",
    data: new Date().toISOString()
  };
  registro.notification_status = await notifyStudentsAboutLaunch({
    students,
    item: registro,
    kind: "nota",
    title: `Nota lançada: ${titulo}`,
    body: nota >= 7
      ? `Sua nota foi ${nota}. Parabéns pelo resultado! Continue acompanhando as correções e feedbacks para evoluir ainda mais.`
      : `Sua nota foi ${nota}. Revise os pontos corrigidos, estude mais um pouco e conte com o professor para melhorar seus resultados.`,
    session,
  });
  const idx = notas.findIndex((n) => text(n.id) === id);
  const nextNotas = idx >= 0 ? notas.map((n, i) => i === idx ? { ...n, ...registro } : n) : [...notas, registro];

  const desafioId = text(body.desafio_id || body.id_desafio || body.desafioId || titulo);
  const conclIdx = conclusoes.findIndex((c) => text(c.desafio_id) === desafioId && text(c.aluno) === aluno);
  const conclusao = {
    desafio_id: desafioId,
    aluno,
    pontos: Number(body.pontos || nota),
    nota,
    status: "Corrigido",
    data: new Date().toISOString()
  };
  const nextConclusoes = conclIdx >= 0 ? conclusoes.map((c, i) => i === conclIdx ? { ...c, ...conclusao } : c) : [...conclusoes, conclusao];

  await Promise.all([dbSet("grades.json", nextNotas), dbSet("challenge_completions.json", nextConclusoes)]);
  return NextResponse.json(registro, { status: 201 });
}
