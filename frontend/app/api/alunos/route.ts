import { NextRequest, NextResponse } from "next/server";
import { dbList, dbListWithoutKeys, dbSet } from "@/lib/db";
import { getSession } from "@/lib/auth";
import { isVipModule, teacherClassValueByModule, VIP_DEFAULT_TOTAL, vipPlanTotal } from "@/lib/course-modules";

const KEY = "students.json";
const HEAVY_KEYS = ["file_b64", "pdf_b64", "base64", "arquivo_b64", "foto_b64", "imagem_b64", "documento_b64", "anexo_b64"];

function text(value: unknown) {
  return String(value || "").trim();
}

function digits(value: unknown) {
  return text(value).replace(/\D/g, "");
}

function nextMatricula(alunos: Record<string, unknown>[]) {
  let max = 0;
  for (const aluno of alunos) {
    const n = Number(digits(aluno.matricula));
    if (Number.isFinite(n) && n > max) max = n;
  }
  return String(max + 1).padStart(4, "0");
}

function normalizeAluno(body: Record<string, unknown>) {
  const modulo = text(body.modulo || body.modalidade);
  const vip = isVipModule(modulo);
  const vipTotalDefault = vipPlanTotal(body.vip_tipo_plano || "Pacote 10 aulas") || VIP_DEFAULT_TOTAL;
  const responsavel =
    body.responsavel && typeof body.responsavel === "object" && !Array.isArray(body.responsavel)
      ? body.responsavel as Record<string, unknown>
      : {};
  const responsavelNome = text(body.responsavel_nome || responsavel.nome || body.responsavel);
  const login = text(body.login || body.usuario).toLowerCase();
  return {
    ...body,
    nome: text(body.nome || body.name),
    turma: text(body.turma || body.classe),
    classe: text(body.turma || body.classe),
    livro: text(body.livro || body.book),
    book: text(body.livro || body.book),
    modulo,
    matricula: text(body.matricula),
    usuario: login,
    login,
    senha: text(body.senha),
    rg: text(body.rg),
    genero: text(body.genero || body.sexo),
    idade: text(body.idade),
    cidade_natal: text(body.cidade_natal),
    pais: text(body.pais || "Brasil"),
    cep: text(body.cep),
    rua: text(body.rua),
    numero: text(body.numero),
    complemento: text(body.complemento),
    cidade: text(body.cidade),
    bairro: text(body.bairro),
    valor_professor_aula: teacherClassValueByModule(modulo),
    vip_tipo_plano: vip ? text(body.vip_tipo_plano || "Pacote 10 aulas") : "",
    vip_aulas_total: vip ? Number(body.vip_aulas_total || vipTotalDefault) : 0,
    vip_aulas_restantes: vip ? Number(body.vip_aulas_restantes || body.vip_aulas_total || vipTotalDefault) : 0,
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

  const alunos = await dbListWithoutKeys(KEY, HEAVY_KEYS);
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
    if (!text(normalized.matricula)) normalized.matricula = nextMatricula(alunos);

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
