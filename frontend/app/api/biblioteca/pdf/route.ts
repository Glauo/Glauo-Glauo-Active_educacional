import { NextRequest, NextResponse } from "next/server";
import { getSession } from "@/lib/auth";
import { dbList } from "@/lib/db";
import { getLibraryPdf, libraryPdfKey, libraryPdfUrl } from "@/lib/library-pdfs";

type Row = Record<string, unknown>;

function text(value: unknown) {
  return String(value || "").trim();
}

export async function GET(req: NextRequest) {
  const session = await getSession();
  if (!session) return NextResponse.json({ error: "Nao autorizado." }, { status: 401 });

  const id = text(req.nextUrl.searchParams.get("id"));
  if (!id) return NextResponse.json({ error: "ID do PDF obrigatorio." }, { status: 400 });

  const key = libraryPdfKey(req.nextUrl.searchParams.get("tipo") || "livros");
  const file = await getLibraryPdf(key, id);
  if (file?.pdf_b64) {
    return new NextResponse(Buffer.from(file.pdf_b64, "base64"), {
      headers: {
        "Content-Type": text(file.pdf_mime) || "application/pdf",
        "Content-Disposition": `inline; filename="${encodeURIComponent(text(file.pdf_nome) || `${id}.pdf`)}"`,
        "Cache-Control": "private, max-age=60",
      },
    });
  }

  const items = await dbList<Row>(key);
  const item = items.find((row) => text(row.id) === id);
  const url = text(item?.url || item?.file_path);
  if (url && url !== libraryPdfUrl(key, id)) {
    return NextResponse.redirect(new URL(url, req.url));
  }

  return NextResponse.json({ error: "PDF nao encontrado na biblioteca." }, { status: 404 });
}
