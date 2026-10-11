import { randomBytes, scrypt, timingSafeEqual } from "node:crypto";
import { promisify } from "node:util";
import bcrypt from "bcryptjs";

const derive = promisify(scrypt);

export async function hashPassword(password: string) {
  const salt = randomBytes(16).toString("hex");
  const key = await derive(password, salt, 64) as Buffer;
  return `scrypt$${salt}$${key.toString("hex")}`;
}

export async function verifyPassword(password: string, stored: unknown) {
  if (typeof stored !== "string" || !stored) return false;
  if (/^\$2[aby]\$/.test(stored)) {
    try {
      return await bcrypt.compare(password, stored.replace(/^\$2y\$/, "$2b$"));
    } catch {
      return false;
    }
  }
  if (!stored.startsWith("scrypt$")) {
    const a = Buffer.from(password);
    const b = Buffer.from(stored);
    return a.length === b.length && timingSafeEqual(a, b);
  }
  const [, salt, digest] = stored.split("$");
  if (!/^[a-f0-9]{32}$/.test(salt || "") || !/^[a-f0-9]{128}$/.test(digest || "")) return false;
  const key = await derive(password, salt, 64) as Buffer;
  return timingSafeEqual(key, Buffer.from(digest, "hex"));
}
