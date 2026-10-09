export function jwtSecret() {
  const secret = process.env.JWT_SECRET;
  if (process.env.NODE_ENV === "production" && (!secret || secret.length < 32)) {
    throw new Error("JWT_SECRET deve estar configurado com pelo menos 32 caracteres.");
  }
  return new TextEncoder().encode(secret || "active-development-only-do-not-use-in-production");
}
