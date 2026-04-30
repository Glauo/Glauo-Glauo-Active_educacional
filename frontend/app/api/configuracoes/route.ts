import { NextRequest, NextResponse } from "next/server";
import { dbGet, dbSet } from "@/lib/db";
import { getSession } from "@/lib/auth";

const KEYS = ["sistema_config.json", "smtp_config.json", "boleto_config.json"] as const;

export async function GET() {
  const session = await getSession();
  if (!session || session.perfil === "Aluno") {
    return NextResponse.json({ error: "Não autorizado" }, { status: 401 });
  }
  const [sistema, smtp, boleto] = await Promise.all(KEYS.map((k) => dbGet(k)));
  return NextResponse.json({ sistema: sistema || {}, smtp: smtp || {}, boleto: boleto || {} });
}

export async function PUT(req: NextRequest) {
  const session = await getSession();
  if (!session || session.perfil === "Aluno") {
    return NextResponse.json({ error: "Não autorizado" }, { status: 401 });
  }
  const body = await req.json() as { secao: string; dados: Record<string, unknown> };
  const keyMap: Record<string, string> = {
    sistema: "sistema_config.json",
    smtp: "smtp_config.json",
    boleto: "boleto_config.json"
  };
  const key = keyMap[body.secao];
  if (!key) return NextResponse.json({ error: "Seção inválida." }, { status: 400 });

  const atual = await dbGet<Record<string, unknown>>(key) || {};
  await dbSet(key, { ...atual, ...body.dados });
  return NextResponse.json({ ok: true });
}
