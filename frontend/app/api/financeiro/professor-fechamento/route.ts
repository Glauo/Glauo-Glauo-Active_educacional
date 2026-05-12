import { NextRequest, NextResponse } from "next/server";
import { dbList, dbSet } from "@/lib/db";
import { getSession } from "@/lib/auth";

const KEY = "professor_fechamentos.json";

type AulaItem = {
  id?: string;
  data_aula?: string;
  vencimento?: string;
  data_vencimento?: string;
  turma?: string;
  horario?: string;
  local?: string;
  modulo?: string;
  descricao?: string;
  valor?: number | string;
  status?: string;
  [k: string]: unknown;
};

type Fechamento = {
  id: string;
  professor_id: string;
  professor_nome: string;
  periodo_inicio: string;
  periodo_fim: string;
  total_aulas: number;
  valor_total: number;
  status: "pre_fechamento" | "fechado" | "enviado" | "pago" | "cancelado";
  aulas: AulaItem[];
  created_at: string;
  updated_at: string;
  pago_em?: string;
  pago_por?: string;
};

function parseValor(v: unknown): number {
  return parseFloat(String(v || "0").replace(/[^\d.,]/g, "").replace(",", ".")) || 0;
}

function dentroDoperiodo(data: string, inicio: string, fim: string): boolean {
  if (!data) return false;
  // Normalize date string
  let d: Date;
  const mBR = data.match(/^(\d{2})\/(\d{2})\/(\d{4})/);
  if (mBR) {
    d = new Date(Number(mBR[3]), Number(mBR[2]) - 1, Number(mBR[1]));
  } else {
    d = new Date(data);
  }
  if (isNaN(d.getTime())) return false;
  const dInicio = new Date(inicio);
  const dFim = new Date(fim);
  dInicio.setHours(0, 0, 0, 0);
  dFim.setHours(23, 59, 59, 999);
  return d >= dInicio && d <= dFim;
}

export async function GET(req: NextRequest) {
  const session = await getSession();
  if (!session) return NextResponse.json({ error: "Nao autorizado." }, { status: 401 });

  const { searchParams } = new URL(req.url);
  const professor_id = searchParams.get("professor_id");
  const periodo = searchParams.get("periodo"); // YYYY-MM

  let fechamentos = await dbList<Fechamento>(KEY);

  if (professor_id) {
    fechamentos = fechamentos.filter((f) => f.professor_id === professor_id);
  }
  if (periodo) {
    fechamentos = fechamentos.filter(
      (f) => f.periodo_inicio.startsWith(periodo) || f.periodo_fim.startsWith(periodo)
    );
  }

  // Sort by created_at desc
  fechamentos = fechamentos.sort((a, b) => b.created_at.localeCompare(a.created_at));

  return NextResponse.json({ fechamentos });
}

export async function POST(req: NextRequest) {
  const session = await getSession();
  if (!session) return NextResponse.json({ error: "Nao autorizado." }, { status: 401 });

  try {
    const body = await req.json();
    const { professor_nome, professor_id, periodo_inicio, periodo_fim } = body;

    if (!professor_nome || !professor_id || !periodo_inicio || !periodo_fim) {
      return NextResponse.json({ error: "Campos obrigatorios: professor_nome, professor_id, periodo_inicio, periodo_fim." }, { status: 400 });
    }

    const fechamentos = await dbList<Fechamento>(KEY);

    // Verificar duplicidade
    const existente = fechamentos.find(
      (f) =>
        f.professor_id === professor_id &&
        f.periodo_inicio === periodo_inicio &&
        f.periodo_fim === periodo_fim &&
        f.status !== "cancelado"
    );

    if (existente) {
      if (existente.status === "pago") {
        return NextResponse.json({ error: "Fechamento ja pago para este periodo. Nao pode ser sobrescrito." }, { status: 409 });
      }
      // Se for rascunho/pre_fechamento, atualiza
      if (existente.status === "pre_fechamento") {
        const payables = await dbList<AulaItem>("payables.json");
        const aulas = payables.filter(
          (p) => {
            const profName = String(p.professor || p.aluno || p.nome || "");
            const dataAula = String(p.data_aula || p.vencimento || p.data_vencimento || "");
            return profName === professor_nome && dentroDoperiodo(dataAula, periodo_inicio, periodo_fim);
          }
        );
        const valor_total = aulas.reduce((s, a) => s + parseValor(a.valor), 0);

        const idx = fechamentos.findIndex((f) => f.id === existente.id);
        fechamentos[idx] = {
          ...fechamentos[idx],
          total_aulas: aulas.length,
          valor_total,
          aulas,
          updated_at: new Date().toISOString(),
        };
        await dbSet(KEY, fechamentos);
        return NextResponse.json({ ok: true, fechamento: fechamentos[idx] });
      }
    }

    // Buscar aulas do período
    const payables = await dbList<AulaItem>("payables.json");
    const aulas = payables.filter((p) => {
      const profName = String(p.professor || p.aluno || p.nome || "");
      const dataAula = String(p.data_aula || p.vencimento || p.data_vencimento || "");
      return profName === professor_nome && dentroDoperiodo(dataAula, periodo_inicio, periodo_fim);
    });

    const valor_total = aulas.reduce((s, a) => s + parseValor(a.valor), 0);
    const now = new Date().toISOString();

    const novo: Fechamento = {
      id: crypto.randomUUID(),
      professor_id,
      professor_nome,
      periodo_inicio,
      periodo_fim,
      total_aulas: aulas.length,
      valor_total,
      status: "pre_fechamento",
      aulas,
      created_at: now,
      updated_at: now,
    };

    fechamentos.push(novo);
    await dbSet(KEY, fechamentos);
    return NextResponse.json({ ok: true, fechamento: novo }, { status: 201 });
  } catch (err) {
    console.error("[professor-fechamento POST]", err);
    return NextResponse.json({ error: "Erro ao criar fechamento." }, { status: 500 });
  }
}

export async function PUT(req: NextRequest) {
  const session = await getSession();
  if (!session) return NextResponse.json({ error: "Nao autorizado." }, { status: 401 });

  try {
    const body = await req.json();
    const { id, status } = body;
    if (!id || !status) return NextResponse.json({ error: "id e status sao obrigatorios." }, { status: 400 });

    const statusValidos = ["pre_fechamento", "fechado", "enviado", "pago", "cancelado"];
    if (!statusValidos.includes(status)) {
      return NextResponse.json({ error: `Status invalido. Use: ${statusValidos.join(", ")}` }, { status: 400 });
    }

    // Somente Admin pode marcar como pago
    if (status === "pago" && session.perfil !== "Admin") {
      return NextResponse.json({ error: "Apenas Admin pode marcar fechamento como pago." }, { status: 403 });
    }

    const fechamentos = await dbList<Fechamento>(KEY);
    const idx = fechamentos.findIndex((f) => f.id === id);
    if (idx === -1) return NextResponse.json({ error: "Fechamento nao encontrado." }, { status: 404 });

    const updates: Partial<Fechamento> = { status: status as Fechamento["status"], updated_at: new Date().toISOString() };
    if (status === "pago") {
      updates.pago_em = new Date().toISOString();
      updates.pago_por = session.pessoa || session.usuario;
    }

    fechamentos[idx] = { ...fechamentos[idx], ...updates };
    await dbSet(KEY, fechamentos);
    return NextResponse.json({ ok: true, fechamento: fechamentos[idx] });
  } catch (err) {
    console.error("[professor-fechamento PUT]", err);
    return NextResponse.json({ error: "Erro ao atualizar fechamento." }, { status: 500 });
  }
}

export async function DELETE(req: NextRequest) {
  const session = await getSession();
  if (!session) return NextResponse.json({ error: "Nao autorizado." }, { status: 401 });

  const { searchParams } = new URL(req.url);
  const id = searchParams.get("id");
  if (!id) return NextResponse.json({ error: "id obrigatorio." }, { status: 400 });

  const fechamentos = await dbList<Fechamento>(KEY);
  const idx = fechamentos.findIndex((f) => f.id === id);
  if (idx === -1) return NextResponse.json({ error: "Fechamento nao encontrado." }, { status: 404 });

  // Cancela logicamente — não deleta fisicamente
  fechamentos[idx] = {
    ...fechamentos[idx],
    status: "cancelado",
    updated_at: new Date().toISOString(),
  };
  await dbSet(KEY, fechamentos);
  return NextResponse.json({ ok: true });
}
