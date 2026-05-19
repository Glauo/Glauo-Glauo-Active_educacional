import { NextRequest, NextResponse } from "next/server";
import { getSession } from "@/lib/auth";
import { sendEmail } from "@/lib/email";
import { sendWhatsApp } from "@/lib/whatsapp";

function text(v: unknown) { return String(v || "").trim(); }

export async function POST(req: NextRequest) {
  const session = await getSession();
  if (!session) return NextResponse.json({ error: "Nao autorizado" }, { status: 401 });

  const body = (await req.json()) as {
    canal: "whatsapp" | "email" | "ambos";
    telefone?: string;
    email?: string;
    assunto?: string;
    mensagem: string;
  };

  const results: Record<string, string> = {};

  if (body.canal === "whatsapp" || body.canal === "ambos") {
    const telefone = text(body.telefone);
    if (telefone) {
      const r = await sendWhatsApp(telefone, body.mensagem, session);
      results.whatsapp = r.status;
    } else {
      results.whatsapp = "sem telefone cadastrado";
    }
  }

  if (body.canal === "email" || body.canal === "ambos") {
    const email = text(body.email);
    if (email) {
      const r = await sendEmail(email, body.assunto || "Ativo Educacional", body.mensagem, session);
      results.email = r.status;
    } else {
      results.email = "sem email cadastrado";
    }
  }

  const allOk = Object.values(results).some((s) => s === "enviado" || s === "ok" || s.includes("250") || s.includes("sent"));
  return NextResponse.json({ ok: allOk, results });
}
