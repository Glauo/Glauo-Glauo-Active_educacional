import { NextResponse } from "next/server";
import { getSession } from "@/lib/auth";
import { dbGet, dbList, dbSet, getPool } from "@/lib/db";
import { isAdminOrCoordinator } from "@/lib/roles";
import { getSchoolClasses } from "@/lib/school-data";

function canRepair(perfil: string) {
  const p = perfil.toLowerCase();
  return p.includes("dire") || isAdminOrCoordinator({ perfil });
}

function text(value: unknown) {
  return String(value || "").trim();
}

function normalize(value: unknown) {
  return text(value)
    .toLowerCase()
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .replace(/\s+/g, " ");
}

function moneyKey(value: unknown) {
  const n = Number.parseFloat(text(value).replace(/[^\d,.-]/g, "").replace(/\./g, "").replace(",", ".")) || 0;
  return n.toFixed(2);
}

function dateKey(value: unknown) {
  const raw = text(value);
  const br = raw.match(/^(\d{2})\/(\d{2})\/(\d{4})/);
  if (br) return `${br[3]}-${br[2]}-${br[1]}`;
  const date = new Date(raw);
  return Number.isNaN(date.getTime()) ? normalize(raw) : date.toISOString().slice(0, 10);
}

function isPaid(value: unknown) {
  const status = normalize(value);
  return status.includes("pago") || status.includes("baixado") || status.includes("liquidado");
}

function duplicateReceivableKey(item: Record<string, unknown>) {
  return [
    normalize(item.aluno_id || item.aluno_login || item.login || item.aluno || item.nome),
    normalize(item.descricao || item.categoria || item.tipo || "mensalidade"),
    normalize(item.parcela || item.numero_parcela || "1"),
    dateKey(item.vencimento || item.data_vencimento),
    moneyKey(item.valor_parcela ?? item.valor_total ?? item.valor),
  ].join("|");
}

function keepScore(item: Record<string, unknown>) {
  let score = 0;
  if (isPaid(item.status || item.situacao)) score += 1000;
  if (text(item.boleto_pdf_url) || text(item.boleto_pdf_b64)) score += 100;
  if (text(item.boleto_codigo) || text(item.codigo)) score += 50;
  if (text(item.updated_at)) score += 20;
  if (text(item.created_at)) score += 10;
  return score;
}

function keepNewestFirst(a: Record<string, unknown>, b: Record<string, unknown>) {
  const scoreDiff = keepScore(b) - keepScore(a);
  if (scoreDiff !== 0) return scoreDiff;
  return text(b.updated_at || b.created_at || b.id).localeCompare(text(a.updated_at || a.created_at || a.id));
}

async function removeDuplicateReceivables(actions: string[], session: { pessoa: string; usuario: string; perfil: string }) {
  const receivables = await dbList<Record<string, unknown>>("receivables.json");
  const groups = new Map<string, Record<string, unknown>[]>();

  for (const item of receivables) {
    const key = duplicateReceivableKey(item);
    if (!key.startsWith("|") && !key.includes("||")) {
      groups.set(key, [...(groups.get(key) || []), item]);
    }
  }

  const kept: Record<string, unknown>[] = [];
  const removed: Record<string, unknown>[] = [];

  for (const item of receivables) {
    const key = duplicateReceivableKey(item);
    const group = groups.get(key);
    if (!group || group.length <= 1) {
      kept.push(item);
      continue;
    }
    const sorted = [...group].sort(keepNewestFirst);
    if (item === sorted[0]) kept.push(item);
    else removed.push(item);
  }

  if (removed.length === 0) {
    actions.push("receivables_duplicados_0");
    return;
  }

  const audit = await dbList<Record<string, unknown>>("finance_audit.json");
  const auditEntries = removed.map((item) => ({
    id: crypto.randomUUID(),
    data: new Date().toISOString(),
    acao: "remover_parcela_duplicada",
    tipo: "recebimentos",
    lancamento_id: item.id,
    usuario: session.pessoa || session.usuario,
    perfil: session.perfil,
    antes: item,
  }));

  await dbSet("receivables.json", kept);
  await dbSet("finance_audit.json", [...audit, ...auditEntries]);
  actions.push(`receivables_duplicados_removidos_${removed.length}`);
}

async function stripBooksBase64(actions: string[]) {
  const pool = getPool();
  if (pool) {
    try {
      const res = await pool.query(
        `UPDATE active_kv
         SET value = (
           SELECT COALESCE(jsonb_agg(elem - 'file_b64'), '[]'::jsonb)
           FROM jsonb_array_elements(value::jsonb) AS elem
         ),
         updated_at = now()
         WHERE key = $1
           AND jsonb_typeof(value::jsonb) = 'array'
         RETURNING jsonb_array_length(value::jsonb) AS total`,
        ["books"]
      );
      if (res.rowCount) actions.push(`books_file_b64_removido_sql_${res.rows[0]?.total || 0}`);
      return;
    } catch (err) {
      actions.push(`books_sql_falhou_${err instanceof Error ? err.message.slice(0, 80) : "erro"}`);
    }
  }

  const books = await dbList<Record<string, unknown>>("books.json");
  if (books.some((book) => typeof book.file_b64 === "string")) {
    await dbSet("books.json", books.map((book) => {
      const next = { ...book };
      delete next.file_b64;
      return next;
    }));
    actions.push("books_file_b64_removido_fallback");
  }
}

async function runRepair() {
  const session = await getSession();
  if (!session || !canRepair(session.perfil)) {
    return NextResponse.json({ error: "Nao autorizado" }, { status: 401 });
  }

  const actions: string[] = [];

  await stripBooksBase64(actions);
  await removeDuplicateReceivables(actions, session);

  const classes = await dbGet<unknown[]>("classes.json");
  if (!Array.isArray(classes) || classes.length === 0) {
    const rebuilt = await getSchoolClasses();
    if (rebuilt.length > 0) {
      await dbSet("classes.json", rebuilt);
      actions.push(`classes_recriadas_${rebuilt.length}`);
    }
  }

  return NextResponse.json({ ok: true, actions });
}

export async function GET() {
  return runRepair();
}

export async function POST() {
  return runRepair();
}
