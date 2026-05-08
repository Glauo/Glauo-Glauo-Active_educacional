import { Pool } from "pg";

declare global {
  // eslint-disable-next-line no-var
  var _pgPool: Pool | undefined;
  // eslint-disable-next-line no-var
  var _activeKvCache: Map<string, unknown> | undefined;
}

const RETRIES = 3;

function cache() {
  if (!globalThis._activeKvCache) globalThis._activeKvCache = new Map<string, unknown>();
  return globalThis._activeKvCache;
}

function wait(ms: number) {
  return new Promise((resolve) => setTimeout(resolve, ms));
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
  const normalizedKey = normalizeKey(key);
  const lastGood = cache().get(normalizedKey) as T | undefined;
  if (!pool) return lastGood ?? null;

  for (let attempt = 1; attempt <= RETRIES; attempt++) {
    try {
      const res = await pool.query<{ value: T }>(
        "SELECT value FROM active_kv WHERE key = $1",
        [normalizedKey]
      );
      const value = res.rows[0]?.value ?? null;
      if (value !== null) cache().set(normalizedKey, value);
      return value;
    } catch (err) {
      console.error(`[dbGet] Falha ao ler ${normalizedKey} tentativa ${attempt}/${RETRIES}`, err);
      if (attempt < RETRIES) await wait(150 * attempt);
    }
  }

  return lastGood ?? null;
}

export async function dbSet(key: string, value: unknown): Promise<boolean> {
  const pool = getPool();
  if (!pool) throw new Error(`Banco de dados indisponivel para gravar ${normalizeKey(key)}`);
  const normalizedKey = normalizeKey(key);

  for (let attempt = 1; attempt <= RETRIES; attempt++) {
    try {
      await pool.query(
        `INSERT INTO active_kv (key, value, updated_at)
         VALUES ($1, $2::jsonb, now())
         ON CONFLICT (key) DO UPDATE
           SET value = EXCLUDED.value,
               updated_at = now()`,
        [normalizedKey, JSON.stringify(value)]
      );
      cache().set(normalizedKey, value);
      return true;
    } catch (err) {
      console.error(`[dbSet] Falha ao gravar ${normalizedKey} tentativa ${attempt}/${RETRIES}`, err);
      if (attempt < RETRIES) await wait(200 * attempt);
    }
  }

  throw new Error(`Nao foi possivel gravar ${normalizedKey} apos ${RETRIES} tentativas`);
}

export async function dbList<T = unknown>(key: string): Promise<T[]> {
  const result = await dbGet<T[]>(key);
  return Array.isArray(result) ? result : [];
}

export async function dbListWithoutKeys<T = unknown>(key: string, keys: string[]): Promise<T[]> {
  const pool = getPool();
  if (!pool || keys.length === 0) {
    const items = await dbList<Record<string, unknown>>(key);
    return items.map((item) => {
      const next = { ...item };
      for (const k of keys) delete next[k];
      return next as T;
    });
  }

  try {
    const res = await pool.query<{ value: T[] }>(
      `SELECT COALESCE(jsonb_agg(elem - $2::text[]), '[]'::jsonb) AS value
       FROM active_kv, jsonb_array_elements(value) elem
       WHERE key = $1`,
      [normalizeKey(key), keys]
    );
    return Array.isArray(res.rows[0]?.value) ? res.rows[0].value : [];
  } catch {
    const items = await dbList<Record<string, unknown>>(key);
    return items.map((item) => {
      const next = { ...item };
      for (const k of keys) delete next[k];
      return next as T;
    });
  }
}

export function isDbAvailable(): boolean {
  return getPool() !== null;
}
