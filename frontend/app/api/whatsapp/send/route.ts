import { NextRequest, NextResponse } from "next/server";
import { getSession } from "@/lib/auth";
import { sendWhatsApp } from "@/lib/whatsapp";

function text(value: unknown) {
  return String(value || "").trim();
}

export async function POST(req: NextRequest) {
  const session = await getSession();
  if (!session) return NextResponse.json({ error: "Nao autorizado." }, { status: 401 });

  try {
    const body = await req.json();
    const telefone = text(body.telefone || body.whatsapp || body.numero);
    const mensagem = text(body.mensagem || body.message);
    if (!telefone || !mensagem) {
      return NextResponse.json({ error: "Telefone e mensagem sao obrigatorios." }, { status: 400 });
    }

    const result = await sendWhatsApp(telefone, mensagem, session);
    return NextResponse.json(result, { status: result.ok ? 200 : 502 });
  } catch (err) {
    console.error("[whatsapp/send POST]", err);
    return NextResponse.json({ error: "Erro ao enviar WhatsApp." }, { status: 500 });
  }
}
