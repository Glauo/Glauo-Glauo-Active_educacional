import { NextRequest, NextResponse } from "next/server";
import { mkdir, writeFile } from "fs/promises";
import path from "path";
import { getSession } from "@/lib/auth";

function safeFileName(value: string) {
  return value
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .replace(/[^a-zA-Z0-9._-]+/g, "-")
    .replace(/-+/g, "-")
    .replace(/^-|-$/g, "")
    .toLowerCase();
}

export async function POST(req: NextRequest) {
  const session = await getSession();
  if (!session) return NextResponse.json({ error: "Nao autorizado." }, { status: 401 });

  try {
    const form = await req.formData();
    const file = form.get("arquivo_pdf");
    if (!(file instanceof File) || file.size === 0) {
      return NextResponse.json({ error: "Selecione um arquivo PDF." }, { status: 400 });
    }
    if (file.type && file.type !== "application/pdf") {
      return NextResponse.json({ error: "Envie apenas arquivo PDF." }, { status: 400 });
    }

    const buffer = Buffer.from(await file.arrayBuffer());
    const uploadsDir = path.join(process.cwd(), "public", "uploads", "boletos");
    const base = safeFileName(file.name || "boleto.pdf") || "boleto.pdf";
    const filename = `${Date.now()}-${base.endsWith(".pdf") ? base : `${base}.pdf`}`;
    let url = "";

    try {
      await mkdir(uploadsDir, { recursive: true });
      await writeFile(path.join(uploadsDir, filename), buffer);
      url = `/uploads/boletos/${filename}`;
    } catch (err) {
      console.warn("[upload-pdf] arquivo publico nao persistiu; usando base64 no lancamento", err);
    }

    return NextResponse.json({
      ok: true,
      url,
      nome: file.name,
      b64: buffer.toString("base64"),
      mime: "application/pdf",
    });
  } catch (err) {
    console.error("[upload-pdf POST]", err);
    return NextResponse.json({ error: "Erro ao salvar arquivo PDF." }, { status: 500 });
  }
}
