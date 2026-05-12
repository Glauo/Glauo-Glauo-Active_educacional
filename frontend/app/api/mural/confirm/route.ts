import { NextRequest, NextResponse } from "next/server";
import { getSession } from "@/lib/auth";
import { dbList, dbSet } from "@/lib/db";
import { nowIso, text, type WallPost } from "@/lib/school-modules";

export async function POST(req: NextRequest) {
  const session = await getSession();
  if (!session) return NextResponse.json({ error: "Nao autorizado" }, { status: 401 });
  const { id, opcao } = (await req.json()) as { id?: string; opcao?: string };
  const posts = await dbList<WallPost>("messages.json");
  const idx = posts.findIndex((post) => text(post.id) === text(id));
  if (idx === -1) return NextResponse.json({ error: "Post nao encontrado" }, { status: 404 });

  const post = posts[idx];
  const confirmacoes = Array.isArray(post.confirmacoes) ? post.confirmacoes : [];
  const usuario = text(session.usuario);
  if (!confirmacoes.some((item) => text(item.usuario) === usuario)) {
    confirmacoes.push({
      usuario,
      nome: session.pessoa || usuario,
      perfil: session.perfil,
      data: nowIso(),
    });
  }

  const votos = Array.isArray(post.votos) ? post.votos.filter((vote) => text(vote.usuario) !== usuario) : [];
  if (text(opcao)) {
    votos.push({ usuario, nome: session.pessoa || usuario, opcao: text(opcao), data: nowIso() });
  }

  posts[idx] = { ...post, confirmacoes, votos };
  await dbSet("messages.json", posts);
  return NextResponse.json(posts[idx]);
}
