import type { SessionUser } from "./auth";

export function isAdminOrCoordinator(session: Pick<SessionUser, "perfil"> | null) {
  const perfil = String(session?.perfil || "").toLowerCase();
  return perfil.includes("admin") || perfil.includes("coord");
}

export function isTeacher(session: Pick<SessionUser, "perfil"> | null) {
  return String(session?.perfil || "").toLowerCase().includes("prof");
}

export function sameName(a: unknown, b: unknown) {
  return String(a || "").trim().toLowerCase() === String(b || "").trim().toLowerCase();
}
