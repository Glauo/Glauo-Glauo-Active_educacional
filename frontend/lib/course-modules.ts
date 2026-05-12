// Official module types — Mister Wiz definition
export const COURSE_MODULES = [
  "Aula em Turma",
  "Aula Teens Presencial",
  "Aula VIP Particular",
  "Aula Intensivo VIP",
  "Reposição de Aula",
] as const;

export const BOOK_LEVELS = [
  "Livro 1",
  "Livro 1.2",
  "Livro 2",
  "Livro 3",
  "Livro 3.2",
  "Livro 4",
  "Livro 5",
  "Livro 6",
] as const;

export const VIP_DEFAULT_TOTAL = 10;

function normalized(value: unknown) {
  return String(value || "")
    .trim()
    .toLowerCase()
    .normalize("NFD")
    .replace(/[̀-ͯ]/g, "");
}

// Maps every legacy module name to a new canonical module name
const LEGACY_MAP: Record<string, string> = {
  "ingles em turma online":   "Aula em Turma",
  "turma presencial":         "Aula em Turma",
  "aula em turma online":     "Aula em Turma",
  "presencial em turma":      "Aula em Turma",
  "online em turma":          "Aula em Turma",
  "kids completo presencial": "Aula em Turma",
  "teens completo":           "Aula Teens Presencial",
  "intensivo vip":            "Aula Intensivo VIP",
  "intensivo vip online":     "Aula Intensivo VIP",
  "aula em turma vip":        "Aula Intensivo VIP",
  "vip":                      "Aula VIP Particular",
  "aulas vip":                "Aula VIP Particular",
  "aula vip particular":      "Aula VIP Particular",
  "reposicoes":               "Reposição de Aula",
  "reposicao":                "Reposição de Aula",
  "reposicao de aula":        "Reposição de Aula",
  "repos":                    "Reposição de Aula",
};

export function migrateModule(moduleName: unknown): string {
  const norm = normalized(moduleName);
  if (!norm) return "Aula em Turma";
  if (LEGACY_MAP[norm]) return LEGACY_MAP[norm];
  // Fuzzy fallbacks for unknown legacy names
  if (norm.includes("repos")) return "Reposição de Aula";
  if (norm.includes("teens") || norm.includes("tens")) return "Aula Teens Presencial";
  if (norm.includes("intensivo")) return "Aula Intensivo VIP";
  if (norm === "vip" || (norm.includes("vip") && !norm.includes("intensivo") && !norm.includes("em turma"))) return "Aula VIP Particular";
  if (norm.includes("turma") || norm.includes("online") || norm.includes("presencial")) return "Aula em Turma";
  return "Aula em Turma";
}

// Teacher pay per class:
//   Aula em Turma         -> R$ 100
//   Aula Teens Presencial -> R$ 100
//   Aula VIP Particular   -> R$  50
//   Aula Intensivo VIP    -> R$  30
//   Reposicao de Aula     -> R$  50
export function teacherClassValueByModule(moduleName: unknown): number {
  const m = normalized(moduleName);
  if (!m) return 0;
  if (m.includes("repos")) return 50;
  if (m.includes("intensivo")) return 30; // must come before generic "vip"
  if (m.includes("teens")) return 100;
  if (m.includes("vip")) return 50;
  if (m.includes("turma")) return 100;
  return 0;
}

// Only "Aula VIP Particular" triggers the lesson-package counter
export function isVipModule(moduleName: unknown): boolean {
  const m = normalized(moduleName);
  return m === "aula vip particular" || m === "vip particular";
}

export function vipPlanTotal(planName: unknown): number {
  const plan = normalized(planName);
  if (plan.includes("10")) return VIP_DEFAULT_TOTAL;
  if (plan.includes("avulsa") || plan.includes("avulso")) return 1;
  return VIP_DEFAULT_TOTAL;
}

function toInt(value: unknown) {
  const n = parseInt(String(value || "0"), 10);
  return Number.isFinite(n) ? n : 0;
}

export function vipPackageStats(aluno: Record<string, unknown>) {
  const modulo = aluno.modulo || aluno.modalidade || aluno.tipo_aula;
  const hasVipPlan = isVipModule(aluno.vip_tipo_plano);
  if (!isVipModule(modulo) && !hasVipPlan) return null;

  const planTotal = vipPlanTotal(aluno.vip_tipo_plano || "Pacote 10 aulas");
  const total = Math.max(1, toInt(aluno.vip_aulas_total) || planTotal || VIP_DEFAULT_TOTAL);
  const restantes = Math.min(total, Math.max(0, toInt(aluno.vip_aulas_restantes || total)));
  const dadas = Math.max(0, total - restantes);

  return { total, dadas, restantes };
}

export function formatModuleValue(moduleName: unknown): string {
  const value = teacherClassValueByModule(moduleName);
  return value.toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
}
