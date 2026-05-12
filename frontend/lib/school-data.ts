import { dbList } from "./db";

export type ClassRow = {
  id?: string;
  nome?: string;
  name?: string;
  professor?: string;
  modulo?: string;
  tipo_aula?: string;
  modalidade?: string;
  livro?: string;
  book?: string;
  status?: string;
  situacao?: string;
  dias?: string;
  horario?: string;
  [k: string]: unknown;
};

type StudentRow = {
  turma?: string;
  classe?: string;
  modulo?: string;
  modalidade?: string;
  livro?: string;
  book?: string;
  [k: string]: unknown;
};

type SessionRow = {
  turma?: string;
  classe?: string;
  professor?: string;
  modulo?: string;
  livro?: string;
  book?: string;
  dias?: string;
  horario?: string;
  [k: string]: unknown;
};

function text(value: unknown) {
  return String(value || "").trim();
}

function titleFrom(value: unknown) {
  return text(value) || "";
}

function normalizeName(value: unknown) {
  return text(value).toLowerCase();
}

export async function getSchoolClasses(): Promise<ClassRow[]> {
  const classes = await dbList<ClassRow>("classes.json");
  if (classes.length > 0) return classes;

  const [students, sessions] = await Promise.all([
    dbList<StudentRow>("students.json"),
    dbList<SessionRow>("class_sessions.json"),
  ]);

  const byName = new Map<string, ClassRow>();

  function upsert(nome: string, seed: Partial<ClassRow>) {
    const cleanName = titleFrom(nome);
    if (!cleanName || cleanName.toLowerCase() === "sem turma") return;
    const key = normalizeName(cleanName);
    const current = byName.get(key) || {
      id: `turma_${cleanName.toLowerCase().replace(/[^a-z0-9]+/g, "_")}`,
      nome: cleanName,
      status: "Ativa",
    };
    byName.set(key, {
      ...current,
      ...Object.fromEntries(Object.entries(seed).filter(([, value]) => text(value))),
      nome: cleanName,
    });
  }

  for (const student of students) {
    upsert(text(student.turma || student.classe), {
      modulo: text(student.modulo || student.modalidade),
      livro: text(student.livro || student.book),
      book: text(student.livro || student.book),
    });
  }

  for (const session of sessions) {
    upsert(text(session.turma || session.classe), {
      professor: text(session.professor),
      modulo: text(session.modulo),
      livro: text(session.livro || session.book),
      book: text(session.livro || session.book),
      dias: text(session.dias),
      horario: text(session.horario),
    });
  }

  return Array.from(byName.values());
}
