import { Pool } from "pg";

declare global {
  // eslint-disable-next-line no-var
  var _pgPool: Pool | undefined;
}

function createPool(): Pool | null {
  const url =
    process.env.ACTIVE_DATABASE_URL ||
    process.env.DATABASE_URL ||
    process.env.POSTGRES_URL;

  if (!url) return null;

  return new Pool({
    connectionString: url.startsWith("postgres://")
      ? url.replace("postgres://", "postgresql://")
      : url,
    ssl: process.env.NODE_ENV === "production"
      ? { rejectUnauthorized: false }
      : false,
    max: 10,
    idleTimeoutMillis: 30000,
    connectionTimeoutMillis: 5000,
  });
}

export function getPool(): Pool | null {
  if (!globalThis._pgPool) {
    globalThis._pgPool = createPool() ?? undefined;
  }
  return globalThis._pgPool ?? null;
}

// Streamlit stores keys without the .json extension (uses Path.stem).
// Strip it here so both systems share the same namespace.
function normalizeKey(key: string): string {
  return key.endsWith(".json") ? key.slice(0, -5) : key;
}

export async function dbGet<T = unknown>(key: string): Promise<T | null> {
  const pool = getPool();
  if (!pool) return null;
  try {
    const res = await pool.query<{ value: T }>(
      "SELECT value FROM active_kv WHERE key = $1",
      [normalizeKey(key)]
    );
    return res.rows[0]?.value ?? null;
  } catch {
    return null;
  }
}

export async function dbSet(key: string, value: unknown): Promise<boolean> {
  const pool = getPool();
  if (!pool) return false;
  try {
    await pool.query(
      `INSERT INTO active_kv (key, value, updated_at)
       VALUES ($1, $2, now())
       ON CONFLICT (key) DO UPDATE
         SET value = EXCLUDED.value,
             updated_at = now()`,
      [normalizeKey(key), JSON.stringify(value)]
    );
    return true;
  } catch {
    return false;
  }
}

export async function dbList<T = unknown>(key: string): Promise<T[]> {
  const result = await dbGet<T[]>(key);
  return Array.isArray(result) ? result : [];
}

export function isDbAvailable(): boolean {
  return getPool() !== null;
}
