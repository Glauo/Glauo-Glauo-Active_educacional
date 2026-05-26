import { NextRequest, NextResponse } from "next/server";
import { dbList, dbSet } from "@/lib/db";

const FECHAMENTOS_KEY = "professor_fechamentos.json";

type AulaItem = {
  id?: string;
  professor?: string;
  aluno?: string;
  nome?: string;
  data_aula?: string;
  vencimento?: string;
  data_vencimento?: string;
  valor?: number | string;
  [k: string]: unknown;
};

type Professor = {
  id?: string;
  nome?: string;
  name?: string;
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

function toISO(d: Date): string {
  return d.toISOString().slice(0, 10);
}

function dentroDoperiodo(data: string, inicio: string, fim: string): boolean {
  if (!data) return false;
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

function calcularPeriodo(): { inicio: string; fim: string } {
  const agora = new Date();

  // Periodo financeiro dos professores: dia 05 a dia 05.
  const base = agora.getDate() >= 5
    ? new Date(agora.getFullYear(), agora.getMonth(), 5)
    : new Date(agora.getFullYear(), agora.getMonth() - 1, 5);

  const inicio = toISO(base);
  const fim = toISO(new Date(base.getFullYear(), base.getMonth() + 1, 5));

  return { inicio, fim };
}

export async function GET(req: NextRequest) {
  const { searchParams } = new URL(req.url);
  const secret = searchParams.get("secret");
  const cronSecret = process.env.CRON_SECRET;

  if (!cronSecret || secret !== cronSecret) {
    return NextResponse.json({ error: "Nao autorizado." }, { status: 401 });
  }

  try {
    const { inicio, fim } = calcularPeriodo();
    const agora = new Date();
    const diaAtual = agora.getDate();
    const statusFechamento: Fechamento["status"] = diaAtual >= 5 ? "fechado" : "pre_fechamento";

    const [professores, payables, fechamentos] = await Promise.all([
      dbList<Professor>("teachers.json"),
      dbList<AulaItem>("payables.json"),
      dbList<Fechamento>(FECHAMENTOS_KEY),
    ]);

    let criados = 0;
    let ignorados = 0;
    let processados = 0;

    const fechamentosAtualizados = [...fechamentos];

    for (const prof of professores) {
      const professorNome = String(prof.nome || prof.name || "").trim();
      const professorId = String(prof.id || professorNome);
      if (!professorNome) continue;

      processados++;

      // Verifica se já existe fechamento não-cancelado para este período
      const existente = fechamentosAtualizados.find(
        (f) =>
          f.professor_id === professorId &&
          f.periodo_inicio === inicio &&
          f.periodo_fim === fim &&
          f.status !== "cancelado"
      );

      if (existente) {
        // Se já está pago, ignorar
        if (existente.status === "pago") {
          ignorados++;
          continue;
        }
        // Se é rascunho/pre_fechamento, atualizar
        if (existente.status === "pre_fechamento") {
          const aulas = payables.filter((p) => {
            const profName = String(p.professor || p.aluno || p.nome || "");
            const dataAula = String(p.data_aula || p.vencimento || p.data_vencimento || "");
            return profName === professorNome && dentroDoperiodo(dataAula, inicio, fim);
          });
          const valor_total = aulas.reduce((s, a) => s + parseValor(a.valor), 0);
          const idx = fechamentosAtualizados.findIndex((f) => f.id === existente.id);
          fechamentosAtualizados[idx] = {
            ...fechamentosAtualizados[idx],
            total_aulas: aulas.length,
            valor_total,
            aulas,
            status: statusFechamento,
            updated_at: new Date().toISOString(),
          };
          // Count as criado since it was updated
          criados++;
          continue;
        }
        ignorados++;
        continue;
      }

      // Buscar aulas do período para este professor
      const aulas = payables.filter((p) => {
        const profName = String(p.professor || p.aluno || p.nome || "");
        const dataAula = String(p.data_aula || p.vencimento || p.data_vencimento || "");
        return profName === professorNome && dentroDoperiodo(dataAula, inicio, fim);
      });

      const valor_total = aulas.reduce((s, a) => s + parseValor(a.valor), 0);
      const now = new Date().toISOString();

      const novoFechamento: Fechamento = {
        id: crypto.randomUUID(),
        professor_id: professorId,
        professor_nome: professorNome,
        periodo_inicio: inicio,
        periodo_fim: fim,
        total_aulas: aulas.length,
        valor_total,
        status: statusFechamento,
        aulas,
        created_at: now,
        updated_at: now,
      };

      fechamentosAtualizados.push(novoFechamento);
      criados++;
    }

    await dbSet(FECHAMENTOS_KEY, fechamentosAtualizados);

    return NextResponse.json({
      ok: true,
      processados,
      criados,
      ignorados,
      periodo: { inicio, fim },
      status: statusFechamento,
    });
  } catch (err) {
    console.error("[financeiro/cron GET]", err);
    return NextResponse.json({ error: "Erro interno no cron de fechamento." }, { status: 500 });
  }
}
