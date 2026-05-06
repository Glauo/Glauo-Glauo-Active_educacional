import { NextRequest, NextResponse } from "next/server";
import { dbList, dbSet } from "@/lib/db";
import { getSession } from "@/lib/auth";
import { isVipModule, teacherClassValueByModule, vipPlanTotal } from "@/lib/course-modules";

const KEY = "students.json";

function text(value: unknown) {
  return String(value || "").trim();
}

function normalizeAluno(body: Record<string, unknown>) {
  const modulo = text(body.modulo || body.modalidade);
  const vip = isVipModule(modulo);
  const vipTotalDefault = vipPlanTotal(body.vip_tipo_plano);
  const responsavel =
    body.responsavel && typeof body.responsavel === "object" && !Array.isArray(body.responsavel)
      ? body.responsavel as Record<string, unknown>
      : {};
  const responsavelNome = text(body.responsavel_nome || responsavel.nome || body.responsavel);
  return {
    ...body,
    nome: text(body.nome || body.name),
    turma: text(body.turma || body.classe),
    classe: text(body.turma || body.classe),
    livro: text(body.livro || body.book),
    book: text(body.livro || body.book),
    modulo,
    valor_professor_aula: teacherClassValueByModule(modulo),
    vip_tipo_plano: vip ? text(body.vip_tipo_plano || "Pacote 10 aulas") : "",
    vip_aulas_total: vip ? Number(body.vip_aulas_total || vipTotalDefault || 0) : 0,
    vip_aulas_restantes: vip ? Number(body.vip_aulas_restantes || body.vip_aulas_total || vipTotalDefault || 0) : 0,
    responsavel: {
      nome: responsavelNome,
      cpf: text(body.responsavel_cpf || responsavel.cpf),
      celular: text(body.responsavel_telefone || responsavel.celular || responsavel.telefone || body.telefone),
      telefone: text(body.responsavel_telefone || responsavel.telefone || responsavel.celular || body.telefone),
      email: text(body.responsavel_email || responsavel.email),
    },
    responsavel_nome: responsavelNome,
    responsavel_cpf: text(body.responsavel_cpf || responsavel.cpf),
    responsavel_telefone: text(body.responsavel_telefone || responsavel.telefone || responsavel.celular || body.telefone),
    responsavel_email: text(body.responsavel_email || responsavel.email),
  };
}

export async function GET() {
  const session = await getSession();
  if (!session) return NextResponse.json({ error: "Não autorizado." }, { status: 401 });

  const alunos = await dbList(KEY);
  return NextResponse.json({ alunos });
}

export async function POST(req: NextRequest) {
  const session = await getSession();
  if (!session) return NextResponse.json({ error: "Não autorizado." }, { status: 401 });

  try {
    const body = await req.json();
    const alunos = await dbList<Record<string, unknown>>(KEY);
    const normalized = normalizeAluno(body);
    if (!text(normalized.nome)) return NextResponse.json({ error: "Nome do aluno e obrigatorio." }, { status: 400 });

    const novo = {
      ...normalized,
      id: body.id || crypto.randomUUID(),
      created_at: new Date().toISOString()
    };

    alunos.push(novo);
    await dbSet(KEY, alunos);
    return NextResponse.json({ ok: true, aluno: novo }, { status: 201 });
  } catch (err) {
    console.error("[alunos POST]", err);
    return NextResponse.json({ error: "Erro ao salvar aluno." }, { status: 500 });
  }
}

export async function PUT(req: NextRequest) {
  const session = await getSession();
  if (!session) return NextResponse.json({ error: "Não autorizado." }, { status: 401 });

  try {
    const body = await req.json();
    const { id, ...updates } = body;

    if (!id) return NextResponse.json({ error: "ID obrigatório." }, { status: 400 });

    const alunos = await dbList<Record<string, unknown>>(KEY);
    const idx = alunos.findIndex((a) => a.id === id || a.nome === id);
    if (idx === -1) return NextResponse.json({ error: "Aluno não encontrado." }, { status: 404 });

    alunos[idx] = { ...alunos[idx], ...normalizeAluno(updates), updated_at: new Date().toISOString() };
    await dbSet(KEY, alunos);
    return NextResponse.json({ ok: true, aluno: alunos[idx] });
  } catch (err) {
    console.error("[alunos PUT]", err);
    return NextResponse.json({ error: "Erro ao atualizar aluno." }, { status: 500 });
  }
}

export async function DELETE(req: NextRequest) {
  const session = await getSession();
  if (!session) return NextResponse.json({ error: "Não autorizado." }, { status: 401 });

  const { searchParams } = new URL(req.url);
  const id = searchParams.get("id");
  if (!id) return NextResponse.json({ error: "ID obrigatório." }, { status: 400 });

  const alunos = await dbList<Record<string, unknown>>(KEY);
  const filtered = alunos.filter((a) => a.id !== id && a.nome !== id);
  await dbSet(KEY, filtered);
  return NextResponse.json({ ok: true });
}
