import { SignJWT, jwtVerify } from "jose";
import { cookies } from "next/headers";
import { dbList } from "./db";

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
  usuario: string;
  senha: string;
  perfil: string;
  pessoa: string;
  unit?: string;
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

export async function validateCredentials(
  usuario: string,
  senha: string,
  unit?: string
): Promise<SessionUser | null> {
  let users: RawUser[] = await dbList<RawUser>("users.json");

  if (!users || users.length === 0) {
    users = [
      { usuario: "admin", senha: "2523", perfil: "Admin", pessoa: "Administrador" }
    ];
  }

  const found = users.find(
    (u) => u.usuario === usuario && u.senha === senha
  );

  if (!found) return null;

  return {
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
  const students = await dbList<StudentRecord>("students.json");
  const found = students.find(
    (s) => s.login && s.login === login && s.senha === senha
  );
  if (!found) return null;
  return {
    usuario: found.login!,
    perfil: "Aluno",
    pessoa: String(found.nome || found.name || found.login),
    unit: String(found.turma || found.classe || "")
  };
}

export { COOKIE_NAME, TTL_SECONDS };
