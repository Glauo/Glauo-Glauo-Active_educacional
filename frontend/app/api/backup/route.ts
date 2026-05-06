import { NextRequest, NextResponse } from "next/server";
import { inflateRawSync } from "node:zlib";
import { mkdir, writeFile } from "node:fs/promises";
import path from "node:path";
import { getSession } from "@/lib/auth";
import { dbGet, dbSet } from "@/lib/db";
import { isAdminOrCoordinator } from "@/lib/roles";

const BACKUP_KEYS = [
  "students.json",
  "classes.json",
  "teachers.json",
  "users.json",
  "receivables.json",
  "payables.json",
  "professor_fechamentos.json",
  "fornecedores.json",
  "finance_audit.json",
  "agenda.json",
  "messages.json",
  "activities.json",
  "activity_submissions.json",
  "homework_submissions.json",
  "grades.json",
  "challenges.json",
  "challenge_completions.json",
  "certificates.json",
  "books.json",
  "videos.json",
  "materials.json",
  "fee_templates.json",
  "inventory.json",
  "inventory_moves.json",
  "material_orders.json",
  "stock.json",
  "sales_leads.json",
  "sales_agenda.json",
  "sales_payments.json",
  "class_sessions.json",
  "sistema_config.json",
  "smtp_config.json",
  "boleto_config.json",
  "meta.json",
  "wiz_action_audit.json",
  "wiz_reference_docs.json",
  "email_log.json",
  "chatbot_active_log.json",
  "backup_audit.json",
];

function filenameDate() {
  return new Date().toISOString().replace(/\D/g, "").slice(0, 14);
}

function canManageBackup(perfil: string) {
  const p = perfil.toLowerCase();
  return p.includes("dire") || isAdminOrCoordinator({ perfil });
}

function safeFilename(value: unknown, fallback: string) {
  const name = String(value || fallback)
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .replace(/[^a-zA-Z0-9._-]+/g, "-")
    .replace(/-+/g, "-")
    .replace(/^-|-$/g, "");
  return name || fallback;
}

async function saveImportedPdf(base64: string, filename: string) {
  const uploadDir = path.join(process.cwd(), "public", "uploads", "livros");
  await mkdir(uploadDir, { recursive: true });
  const cleanBase64 = base64.includes(",") ? base64.split(",").pop() || "" : base64;
  const buffer = Buffer.from(cleanBase64, "base64");
  if (!buffer.length) return "";
  const safeName = `${Date.now()}-${safeFilename(filename, "livro.pdf")}`;
  await writeFile(path.join(uploadDir, safeName), buffer);
  return `/uploads/livros/${safeName}`;
}

async function normalizeBackupValue(key: string, value: unknown) {
  if (value === null || value === undefined) return undefined;

  if (key === "books.json" && Array.isArray(value)) {
    const normalized = [];
    for (const [index, row] of value.entries()) {
      if (!row || typeof row !== "object" || Array.isArray(row)) {
        normalized.push(row);
        continue;
      }
      const livro = { ...row } as Record<string, unknown>;
      const fileB64 = typeof livro.file_b64 === "string" ? livro.file_b64 : "";
      if (fileB64.length > 1000 && !livro.url && !livro.file_path) {
        const url = await saveImportedPdf(fileB64, String(livro.file_name || livro.titulo || `livro-${index + 1}.pdf`)).catch(() => "");
        if (url) {
          livro.url = url;
          livro.file_path = url;
        }
      }
      delete livro.file_b64;
      normalized.push(livro);
    }
    return normalized;
  }

  return value;
}

function findEndOfCentralDirectory(buffer: Buffer) {
  const signature = 0x06054b50;
  const minOffset = Math.max(0, buffer.length - 65557);
  for (let offset = buffer.length - 22; offset >= minOffset; offset -= 1) {
    if (buffer.readUInt32LE(offset) === signature) return offset;
  }
  return -1;
}

function unzipJsonFiles(buffer: Buffer) {
  const eocd = findEndOfCentralDirectory(buffer);
  if (eocd === -1) throw new Error("ZIP invalido.");

  const entries = buffer.readUInt16LE(eocd + 10);
  let offset = buffer.readUInt32LE(eocd + 16);
  const data: Record<string, unknown> = {};

  for (let index = 0; index < entries; index += 1) {
    if (buffer.readUInt32LE(offset) !== 0x02014b50) throw new Error("Cabecalho ZIP invalido.");

    const method = buffer.readUInt16LE(offset + 10);
    const compressedSize = buffer.readUInt32LE(offset + 20);
    const nameLength = buffer.readUInt16LE(offset + 28);
    const extraLength = buffer.readUInt16LE(offset + 30);
    const commentLength = buffer.readUInt16LE(offset + 32);
    const localOffset = buffer.readUInt32LE(offset + 42);
    const filename = buffer.toString("utf8", offset + 46, offset + 46 + nameLength);

    offset += 46 + nameLength + extraLength + commentLength;
    if (!filename.endsWith(".json")) continue;
    if (buffer.readUInt32LE(localOffset) !== 0x04034b50) throw new Error("Arquivo ZIP invalido.");

    const localNameLength = buffer.readUInt16LE(localOffset + 26);
    const localExtraLength = buffer.readUInt16LE(localOffset + 28);
    const start = localOffset + 30 + localNameLength + localExtraLength;
    const compressed = buffer.subarray(start, start + compressedSize);
    const content = method === 0
      ? compressed
      : method === 8
        ? inflateRawSync(compressed)
        : null;

    if (!content) continue;
    data[filename] = JSON.parse(content.toString("utf8"));
  }

  return data;
}

async function readBackupFile(file: File) {
  const buffer = Buffer.from(await file.arrayBuffer());
  const name = file.name.toLowerCase();
  if (name.endsWith(".zip") || file.type.includes("zip")) return unzipJsonFiles(buffer);

  const parsed = JSON.parse(buffer.toString("utf8")) as unknown;
  const source = parsed && typeof parsed === "object" && !Array.isArray(parsed)
    ? parsed as Record<string, unknown>
    : {};
  return source.data && typeof source.data === "object" && !Array.isArray(source.data)
    ? source.data as Record<string, unknown>
    : source;
}

export async function GET() {
  const session = await getSession();
  if (!session || !canManageBackup(session.perfil)) {
    return NextResponse.json({ error: "Nao autorizado" }, { status: 401 });
  }

  const data: Record<string, unknown> = {};
  for (const key of BACKUP_KEYS) {
    const value = await dbGet(key);
    if (value !== null && value !== undefined) data[key] = value;
  }

  const backup = {
    version: "active-educacional-backup-v1",
    generated_at: new Date().toISOString(),
    generated_by: session.usuario,
    data,
  };

  return new NextResponse(JSON.stringify(backup, null, 2), {
    headers: {
      "Content-Type": "application/json; charset=utf-8",
      "Content-Disposition": `attachment; filename="active_backup_${filenameDate()}.json"`,
      "Cache-Control": "no-store",
    },
  });
}

export async function POST(req: NextRequest) {
  const session = await getSession();
  if (!session || !canManageBackup(session.perfil)) {
    return NextResponse.json({ error: "Nao autorizado" }, { status: 401 });
  }

  const form = await req.formData();
  const file = form.get("backup") || form.get("arquivo_backup");
  if (!(file instanceof File)) {
    return NextResponse.json({ error: "Envie um arquivo de bkup em JSON." }, { status: 400 });
  }

  let data: Record<string, unknown>;
  try {
    data = await readBackupFile(file);
  } catch {
    return NextResponse.json({ error: "Arquivo de bkup invalido. Envie JSON ou ZIP do Active." }, { status: 400 });
  }

  let restored = 0;
  const skipped: string[] = [];
  for (const key of BACKUP_KEYS) {
    if (!Object.prototype.hasOwnProperty.call(data, key)) continue;
    const value = await normalizeBackupValue(key, data[key]);
    if (value === undefined) {
      skipped.push(key);
      continue;
    }
    await dbSet(key, value);
    restored += 1;
  }

  const audit = await dbGet<Record<string, unknown>[]>("backup_audit.json") || [];
  audit.unshift({
    id: `backup_${Date.now()}`,
    tipo: "importacao",
    arquivo: file.name,
    restaurados: restored,
    ignorados: skipped,
    usuario: session.usuario,
    perfil: session.perfil,
    created_at: new Date().toISOString(),
  });
  await dbSet("backup_audit.json", audit.slice(0, 200));

  return NextResponse.json({ ok: true, restored, skipped });
}
