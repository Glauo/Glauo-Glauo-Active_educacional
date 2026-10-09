import { randomBytes, randomInt, scrypt, timingSafeEqual } from "node:crypto";
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
  // Older admin/user records may still contain bcrypt hashes from the legacy
  // credential manager. Do not compare those hashes as if they were raw text.
  if (/^\$2[aby]\$/.test(stored)) {
    try {
      return await bcrypt.compare(password, stored.replace(/^\$2y\$/, "$2b$"));
    } catch {
      return false;
    }
  }
  if (!stored.startsWith("scrypt$")) {
    // Existing credentials stay compatible until changed; new resets are hashed.
    const a = Buffer.from(password), b = Buffer.from(stored);
    return a.length === b.length && timingSafeEqual(a, b);
  }
  const [, salt, digest] = stored.split("$");
  if (!/^[a-f0-9]{32}$/.test(salt || "") || !/^[a-f0-9]{128}$/.test(digest || "")) return false;
  const key = await derive(password, salt, 64) as Buffer;
  return timingSafeEqual(key, Buffer.from(digest, "hex"));
}

export function generatedTempPassword() {
  const groups = ["ABCDEFGHJKLMNPQRSTUVWXYZ", "abcdefghijkmnopqrstuvwxyz", "23456789", "@#$%!"];
  const chars = groups.map(group => group[randomInt(group.length)]);
  const all = groups.join("");
  while (chars.length < 12) chars.push(all[randomInt(all.length)]);
  for (let i = chars.length - 1; i > 0; i--) {
    const j = randomInt(i + 1);
    [chars[i], chars[j]] = [chars[j], chars[i]];
  }
  return chars.join("");
}
