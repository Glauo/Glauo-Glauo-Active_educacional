import { NextResponse } from "next/server";
import { getSession } from "@/lib/auth";
import { dbGet, dbList, dbSet } from "@/lib/db";
import { isAdminOrCoordinator } from "@/lib/roles";
import { getSchoolClasses } from "@/lib/school-data";

function canRepair(perfil: string) {
  const p = perfil.toLowerCase();
  return p.includes("dire") || isAdminOrCoordinator({ perfil });
}

export async function POST() {
  const session = await getSession();
  if (!session || !canRepair(session.perfil)) {
    return NextResponse.json({ error: "Nao autorizado" }, { status: 401 });
  }

  const actions: string[] = [];

  const books = await dbList<Record<string, unknown>>("books.json");
  if (books.some((book) => typeof book.file_b64 === "string")) {
    await dbSet("books.json", books.map((book) => {
      const next = { ...book };
      delete next.file_b64;
      return next;
    }));
    actions.push("books_file_b64_removido");
  }

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
