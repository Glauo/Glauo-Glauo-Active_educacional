import { SignJWT, jwtVerify } from "jose";
import { cookies } from "next/headers";
import { dbListFresh as dbList } from "./db";
import { jwtSecret } from "./jwt-config";
import { verifyPassword } from "./passwords";

const COOKIE_NAME = "ae_session";
const TTL_SECONDS = 60 * 60 * 8; // 8 horas

export type SessionUser = {
  usuario: string;
  perfil: string;
  pessoa: string;
  unit?: string;
  must_change_password?: boolean;
  password_reset_at?: string;
  record_id?: string;
};

type RawUser = {
  id?: string;
  usuario: string;
  senha: string;
  perfil: string;
  pessoa: string;
  unit?: string;
  is_active?: boolean;
  status?: string;
  deleted_at?: string;
  must_change_password?: boolean;
  last_login_at?: string;
  password_reset_at?: string;
};

export async function signToken(payload: SessionUser): Promise<string> {
  return new SignJWT({ ...payload })
    .setProtectedHeader({ alg: "HS256" })
    .setIssuedAt()
    .setExpirationTime(`${TTL_SECONDS}s`)
    .sign(jwtSecret());
}

export async function verifyToken(token: string): Promise<SessionUser | null> {
  try {
    const { payload } = await jwtVerify(token, jwtSecret());
    return payload as unknown as SessionUser;
  } catch {
    return null;
  }
}

export async function getSession(allowPasswordChange = false): Promise<SessionUser | null> {
  const cookieStore = await cookies();
  const token = cookieStore.get(COOKIE_NAME)?.value;
  if (!token) return null;
  const session = await verifyToken(token);
  if (!session) return null;
  const student = normalize(session.perfil).includes("aluno");
  const records = await dbList<Record<string, unknown>>(student ? "students" : "users").catch(() => []);
  const candidates = records.filter(row => normalize(student ? row.login || row.usuario : row.usuario) === normalize(session.usuario) &&
    (session.record_id ? String(row.id ?? "") === String(session.record_id) : !session.pessoa || normalize(row.pessoa || row.nome || row.name) === normalize(session.pessoa)));
  const current = candidates.length === 1 ? candidates[0] : undefined;
  if (!current || !isActiveRecord(current)) return null;
  if (String(current.password_reset_at || "") !== String(session.password_reset_at || "")) return null;
  if (current.must_change_password && !allowPasswordChange) return null;
  return { ...session, perfil: student ? "Aluno" : String(current.perfil || ""),
    must_change_password: Boolean(current.must_change_password) };
}

type StudentRecord = {
  id?: string;
  nome?: string;
  name?: string;
  login?: string;
  senha?: string;
  turma?: string;
  classe?: string;
  is_active?: boolean;
  status?: string;
  deleted_at?: string;
  [k: string]: unknown;
};

function normalize(value: unknown) {
  return String(value || "").trim().toLowerCase();
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
  const users: RawUser[] = await dbList<RawUser>("users.json");


  const candidates = users.filter(u => isActiveRecord(u) && normalize(u.usuario) === login);
  const matches = [];
  for (const user of candidates) if (await verifyPassword(password, user.senha)) matches.push(user);
  const found = matches.length === 1 ? matches[0] : null;

  if (!found) {
    return validateStudentCredentials(login, password);
  }

  return {
    must_change_password: Boolean(found.must_change_password),
    password_reset_at: String(found.password_reset_at || ""),
    record_id: found.id == null ? undefined : String(found.id),
    usuario: found.usuario,
    perfil: found.perfil,
    pessoa: found.pessoa,
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
  const candidates = students.filter(s => isActiveRecord(s) && normalize(s.login || s.usuario) === normalizedLogin);
  const matches = [];
  for (const student of candidates) if (await verifyPassword(password, student.senha)) matches.push(student);
  const found = matches.length === 1 ? matches[0] : null;
  if (!found) return null;
  return {
    must_change_password: Boolean(found.must_change_password),
    password_reset_at: String(found.password_reset_at || ""),
    record_id: found.id == null ? undefined : String(found.id),
    usuario: String(found.login || found.usuario),
    perfil: "Aluno",
    pessoa: String(found.nome || found.name || found.login),
    unit: String(found.turma || found.classe || "")
  };
}

export { COOKIE_NAME, TTL_SECONDS };
