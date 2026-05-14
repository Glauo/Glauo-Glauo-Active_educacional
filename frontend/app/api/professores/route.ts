import { NextRequest, NextResponse } from "next/server";
import { dbList, dbSet } from "@/lib/db";
import { getSession } from "@/lib/auth";
import { isAdminOrCoordinator } from "@/lib/roles";

const KEY = "teachers.json";

function text(value: unknown) {
  return String(value || "").trim();
}

function lower(value: unknown) {
  return text(value).toLowerCase();
}

async function syncProfessorUser(professor: Record<string, unknown>, oldLogin?: string) {
  const usuario = text(professor.usuario || professor.login);
  const senha = text(professor.senha);
  if (!usuario || !senha) return false;

  const users = await dbList<Record<string, unknown>>("users.json");
  const professorId = text(professor.id || professor.nome);
  const professorNome = text(professor.nome);
  const idx = users.findIndex((u) =>
    lower(u.usuario) === lower(oldLogin || usuario) ||
    lower(u.usuario) === lower(usuario) ||
    text(u.professor_id) === professorId ||
    text(u.pessoa) === professorNome
  );
  const record = {
    professor_id: professorId,
    usuario,
    senha,
    perfil: "Professor",
    pessoa: professorNome,
    email: lower(professor.email),
    celular: text(professor.celular || professor.telefone || professor.whatsapp),
  };
  if (idx >= 0) users[idx] = { ...users[idx], ...record };
  else users.push(record);
  return dbSet("users.json", users);
}

export async function GET() {
  const session = await getSession();
  if (!session) return NextResponse.json({ error: "Nao autorizado." }, { status: 401 });

  const professores = await dbList(KEY);
  return NextResponse.json({ professores });
}

export async function POST(req: NextRequest) {
  const session = await getSession();
  if (!session) return NextResponse.json({ error: "Nao autorizado." }, { status: 401 });
  if (!isAdminOrCoordinator(session)) return NextResponse.json({ error: "Apenas coordenadores e administradores podem cadastrar professores." }, { status: 403 });

  try {
    const body = await req.json();
    const professores = await dbList<Record<string, unknown>>(KEY);
    const nome = text(body.nome);
    if (!nome) return NextResponse.json({ error: "Nome do professor e obrigatorio." }, { status: 400 });
    const login = text(body.usuario || body.login);
    if (login) {
      const users = await dbList<Record<string, unknown>>("users.json");
      if (users.some((u) => lower(u.usuario) === lower(login))) {
        return NextResponse.json({ error: "Login automatico ja existe." }, { status: 409 });
      }
    }

    const novo = { ...body, nome, id: body.id || crypto.randomUUID(), created_at: new Date().toISOString() };
    professores.push(novo);
    await Promise.all([dbSet(KEY, professores), syncProfessorUser(novo)]);
    return NextResponse.json({ ok: true, professor: novo }, { status: 201 });
  } catch (err) {
    console.error("[professores POST]", err);
    return NextResponse.json({ error: "Erro ao salvar professor." }, { status: 500 });
  }
}

export async function PUT(req: NextRequest) {
  const session = await getSession();
  if (!session) return NextResponse.json({ error: "Nao autorizado." }, { status: 401 });
  if (!isAdminOrCoordinator(session)) return NextResponse.json({ error: "Apenas coordenadores e administradores podem editar professores." }, { status: 403 });

  try {
    const { id, ...updates } = await req.json();
    if (!id) return NextResponse.json({ error: "ID obrigatorio." }, { status: 400 });

    const professores = await dbList<Record<string, unknown>>(KEY);
    const idx = professores.findIndex((p) => p.id === id || p.nome === id);
    if (idx === -1) return NextResponse.json({ error: "Professor nao encontrado." }, { status: 404 });

    const oldNome = text(professores[idx].nome);
    const oldLogin = text(professores[idx].usuario || professores[idx].login);
    const newLogin = lower(updates.usuario || updates.login);
    if (newLogin) {
      const users = await dbList<Record<string, unknown>>("users.json");
      const targetRef = text(professores[idx].id || professores[idx].nome);
      const conflict = users.find((u) =>
        lower(u.usuario) === newLogin &&
        text(u.professor_id) !== targetRef &&
        text(u.pessoa) !== oldNome
      );
      if (conflict) return NextResponse.json({ error: "Este login ja esta em uso por outro usuario." }, { status: 409 });
    }
    professores[idx] = { ...professores[idx], ...updates, updated_at: new Date().toISOString() };

    const writes: Promise<boolean>[] = [dbSet(KEY, professores), syncProfessorUser(professores[idx], oldLogin)];
    const newNome = text(professores[idx].nome);
    if (oldNome && newNome && oldNome !== newNome) {
      const turmas = await dbList<Record<string, unknown>>("classes.json");
      let changed = false;
      for (const turma of turmas) {
        if (text(turma.professor) === oldNome) {
          turma.professor = newNome;
          changed = true;
        }
      }
      if (changed) writes.push(dbSet("classes.json", turmas));
    }

    await Promise.all(writes);
    return NextResponse.json({ ok: true, professor: professores[idx] });
  } catch (err) {
    console.error("[professores PUT]", err);
    return NextResponse.json({ error: "Erro ao atualizar professor." }, { status: 500 });
  }
}

export async function DELETE(req: NextRequest) {
  const session = await getSession();
  if (!session) return NextResponse.json({ error: "Nao autorizado." }, { status: 401 });
  if (!isAdminOrCoordinator(session)) return NextResponse.json({ error: "Apenas coordenadores e administradores podem excluir professores." }, { status: 403 });
  const { searchParams } = new URL(req.url);
  const id = searchParams.get("id");
  if (!id) return NextResponse.json({ error: "id obrigatorio" }, { status: 400 });

  const professores = await dbList<Record<string, unknown>>(KEY);
  const target = professores.find((p) => p.id === id || p.nome === id);
  const targetName = text(target?.nome);
  const targetLogin = lower(target?.usuario || target?.login);
  const filtered = professores.filter((p) => p.id !== id && p.nome !== id);

  const writes: Promise<boolean>[] = [dbSet(KEY, filtered)];
  if (targetName) {
    const turmas = await dbList<Record<string, unknown>>("classes.json");
    let changed = false;
    for (const turma of turmas) {
      if (text(turma.professor) === targetName) {
        turma.professor = "Sem Professor";
        changed = true;
      }
    }
    if (changed) writes.push(dbSet("classes.json", turmas));
  }
  if (targetLogin) {
    const users = await dbList<Record<string, unknown>>("users.json");
    writes.push(dbSet("users.json", users.filter((u) => !(lower(u.usuario) === targetLogin && text(u.perfil) === "Professor"))));
  }

  await Promise.all(writes);
  return NextResponse.json({ ok: true });
}
