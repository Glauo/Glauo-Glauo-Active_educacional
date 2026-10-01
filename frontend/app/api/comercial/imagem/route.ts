import { NextRequest, NextResponse } from "next/server";
import { getSession } from "@/lib/auth";
import { canManageCommercial } from "@/lib/comercial";
import { dbGet } from "@/lib/db";

type CommercialImage = { id: string; nome: string; mime: string; base64: string };

export async function GET(req: NextRequest) {
  const session = await getSession();
  if (!session || !canManageCommercial(session.perfil)) {
    return NextResponse.json({ error: "Nao autorizado." }, { status: 403 });
  }
  const id = req.nextUrl.searchParams.get("id") || "";
  if (!/^[a-z0-9-]{1,80}$/.test(id)) {
    return NextResponse.json({ error: "Imagem invalida." }, { status: 400 });
  }
  const images = await dbGet<CommercialImage[]>("sales_contact_images.json");
  const image = Array.isArray(images) ? images.find((item) => item.id === id) : undefined;
  if (!image || image.id !== id || image.mime !== "image/png" || !image.base64) {
    return NextResponse.json({ error: "Imagem nao encontrada." }, { status: 404 });
  }
  const download = req.nextUrl.searchParams.get("download") === "1";
  return new NextResponse(Buffer.from(image.base64, "base64"), {
    headers: {
      "Content-Type": "image/png",
      "Content-Disposition": `${download ? "attachment" : "inline"}; filename="${encodeURIComponent(image.nome)}"`,
      "Cache-Control": "private, no-store",
      "X-Content-Type-Options": "nosniff",
    },
  });
}
