import { SignJWT, jwtVerify } from "jose";
import { cookies } from "next/headers";
import { dbList } from "./db";
import { verifyPassword } from "./passwords";

const SECRET = new TextEncoder().encode(
  process.env.JWT_SECRET || "active-educacional-secret-2026-change-in-production"
);

const COOKIE_NAME = "ae_session";
const TTL_SECONDS = 60 * 60 * 8; // 8 horas

export type SessionUser = {
  usuario: string;
  perfil: string;
  pessoa: string;
  unit?: string;
};

type RawUser = {
  id?: string;
  usuario?: string;
  senha?: string;
  perfil?: string;
  pessoa?: string;
  email?: string;
  cpf?: string;
  professor_id?: string;
  unit?: string;
  is_active?: boolean;
  status?: string;
  deleted_at?: string;
};

export async function signToken(payload: SessionUser): Promise<string> {
  return new SignJWT({ ...payload })
    .setProtectedHeader({ alg: "HS256" })
    .setIssuedAt()
    .setExpirationTime(`${TTL_SECONDS}s`)
    .sign(SECRET);
}

export async function verifyToken(token: string): Promise<SessionUser | null> {
  try {
    const { payload } = await jwtVerify(token, SECRET);
    return payload as unknown as SessionUser;
  } catch {
    return null;
  }
}

export async function getSession(): Promise<SessionUser | null> {
  const cookieStore = await cookies();
  const token = cookieStore.get(COOKIE_NAME)?.value;
  if (!token) return null;
  return verifyToken(token);
}

type StudentRecord = {
  id?: string;
  nome?: string;
  name?: string;
  login?: string;
  senha?: string;
  turma?: string;
  classe?: string;
  [k: string]: unknown;
};

function normalize(value: unknown) {
  return String(value || "").trim().toLowerCase();
}

function digits(value: unknown) {
  return String(value || "").replace(/\D/g, "");
}

function isAdminProfile(value: unknown) {
  return normalize(value).includes("admin");
}

function isActiveRecord(record: { is_active?: boolean; status?: string; deleted_at?: string } | null | undefined) {
  if (!record) return false;
  if (record.is_active === false) return false;
  if (String(record.deleted_at || "").trim()) return false;
  const status = normalize(record.status || "ativo");
  return !status.includes("inativ") && !status.includes("cancel") && !status.includes("arquiv");
}
export function dashboardForPerfil(perfil?: string) {
  const p = normalize(perfil);
  if (p.includes("aluno")) return "/aluno";
  if (p.includes("prof")) return "/agenda";
  if (p.includes("comercial")) return "/comercial";
  if (p.includes("coord")) return "/";
  if (p.includes("admin") || p.includes("dire")) return "/";
  return "/";
}

export async function validateCredentials(
  usuario: string,
  senha: string,
  unit?: string
): Promise<SessionUser | null> {
  const login = normalize(usuario);
  const password = String(senha);
  let users: RawUser[] = await dbList<RawUser>("users.json");

  if (!users || users.length === 0) {
    users = [
      { usuario: "admin", senha: "2523", perfil: "Admin", pessoa: "Administrador" }
    ];
  }

  const candidates = users.filter(u => isActiveRecord(u) &&
    (normalize(u.usuario) === login || normalize(u.email) === login));
  const matches = [];
  for (const user of candidates) {
    const passwordMatches = await verifyPassword(password, user.senha);
    const cpfMatches = !isAdminProfile(user.perfil) && digits(password).length === 11 &&
      digits(user.cpf) === digits(password);
    if (passwordMatches || cpfMatches) matches.push(user);
  }
  let found = matches.length === 1 ? matches[0] : null;

  // Legacy professor records may have the CPF only in teachers and an old
  // login/password in users. Email + full CPF is accepted only for a uniquely
  // linked, active, non-admin account.
  if (!found && login.includes("@") && digits(password).length === 11) {
    const teachers = await dbList<Record<string, unknown>>("teachers.json");
    const teacherMatches = teachers.filter(teacher => isActiveRecord(teacher) &&
      normalize(teacher.email) === login && digits(teacher.cpf) === digits(password));
    if (teacherMatches.length === 1) {
      const teacher = teacherMatches[0];
      const teacherId = String(teacher.id || teacher.nome || "").trim();
      const teacherName = normalize(teacher.nome || teacher.name);
      const linkedUsers = users.filter(user => isActiveRecord(user) && !isAdminProfile(user.perfil) && (
        (teacherId && String(user.professor_id || "").trim() === teacherId) ||
        normalize(user.usuario) === login || normalize(user.email) === login ||
        (teacherName && normalize(user.pessoa) === teacherName)
      ));
      if (linkedUsers.length === 1) found = linkedUsers[0];
    }
  }

  if (!found) {
    return validateStudentCredentials(login, password);
  }

  return {
    usuario: String(found.usuario || found.email || login),
    perfil: String(found.perfil || ""),
    pessoa: String(found.pessoa || found.usuario || found.email || login),
    unit: unit || found.unit || "Matriz"
  };
}

export async function validateStudentCredentials(
  login: string,
  senha: string
): Promise<SessionUser | null> {
  const normalizedLogin = normalize(login);
  const password = String(senha);
  const students = await dbList<StudentRecord>("students.json");
  const found = students.find(
    (s) => s.login && normalize(s.login) === normalizedLogin && String(s.senha) === password
  );
  if (!found) return null;
  return {
    usuario: String(found.login),
    perfil: "Aluno",
    pessoa: String(found.nome || found.name || found.login),
    unit: String(found.turma || found.classe || "")
  };
}

export { COOKIE_NAME, TTL_SECONDS };
