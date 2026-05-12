import { NextRequest, NextResponse } from "next/server";
import { getSession } from "@/lib/auth";
import { dbList, dbSet } from "@/lib/db";

type Row = Record<string, unknown>;

function text(value: unknown) {
  return String(value || "").trim();
}

function belongsToStudent(row: Row, usuario: string, pessoa: string) {
  const keys = [row.aluno_login, row.usuario, row.aluno, row.destinatario].map((v) => text(v).toLowerCase()).filter(Boolean);
  return keys.includes(usuario.toLowerCase()) || keys.includes(pessoa.toLowerCase());
}

export async function GET() {
  const session = await getSession();
  if (!session || !session.perfil.toLowerCase().includes("aluno")) {
    return NextResponse.json({ error: "Nao autorizado" }, { status: 401 });
  }
  const messages = await dbList<Row>("student_teacher_chat.json");
  return NextResponse.json({
    messages: messages
      .filter((row) => belongsToStudent(row, session.usuario, session.pessoa || session.usuario))
      .sort((a, b) => text(a.data).localeCompare(text(b.data))),
  });
}

export async function POST(req: NextRequest) {
  const session = await getSession();
  if (!session || !session.perfil.toLowerCase().includes("aluno")) {
    return NextResponse.json({ error: "Nao autorizado" }, { status: 401 });
  }
  const body = await req.json().catch(() => ({}));
  const mensagem = text(body.mensagem);
  if (!mensagem) return NextResponse.json({ error: "Mensagem obrigatoria." }, { status: 400 });

  const messages = await dbList<Row>("student_teacher_chat.json");
  const item = {
    id: crypto.randomUUID(),
    origem: "aluno",
    aluno: session.pessoa || session.usuario,
    aluno_login: session.usuario,
    turma: session.unit || "",
    autor: session.pessoa || session.usuario,
    mensagem,
    status: "enviado",
    data: new Date().toISOString(),
  };
  const next = [...messages, item];
  await dbSet("student_teacher_chat.json", next);
  return NextResponse.json({
    ok: true,
    message: item,
    messages: next
      .filter((row) => belongsToStudent(row, session.usuario, session.pessoa || session.usuario))
      .sort((a, b) => text(a.data).localeCompare(text(b.data))),
  }, { status: 201 });
}
