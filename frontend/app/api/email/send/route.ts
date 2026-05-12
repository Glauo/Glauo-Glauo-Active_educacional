import { NextRequest, NextResponse } from "next/server";
import { getSession } from "@/lib/auth";
import { sendEmail } from "@/lib/email";

function text(value: unknown) {
  return String(value || "").trim();
}

export async function POST(req: NextRequest) {
  const session = await getSession();
  if (!session) return NextResponse.json({ error: "Nao autorizado." }, { status: 401 });

  try {
    const body = await req.json();
    const email = text(body.email || body.para || body.destinatario);
    const assunto = text(body.assunto || body.subject || "Active Educacional");
    const mensagem = text(body.mensagem || body.message);
    if (!email || !mensagem) {
      return NextResponse.json({ error: "E-mail e mensagem sao obrigatorios." }, { status: 400 });
    }

    const result = await sendEmail(email, assunto, mensagem, session);
    return NextResponse.json(result, { status: result.ok ? 200 : 502 });
  } catch (err) {
    console.error("[email/send POST]", err);
    return NextResponse.json({ error: "Erro ao enviar e-mail." }, { status: 500 });
  }
}
