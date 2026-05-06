import { NextResponse } from "next/server";
import { getSession } from "@/lib/auth";
import { dbGet, dbList, dbSet, getPool } from "@/lib/db";
import { isAdminOrCoordinator } from "@/lib/roles";
import { getSchoolClasses } from "@/lib/school-data";

function canRepair(perfil: string) {
  const p = perfil.toLowerCase();
  return p.includes("dire") || isAdminOrCoordinator({ perfil });
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
