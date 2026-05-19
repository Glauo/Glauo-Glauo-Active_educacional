// Official module types - Mister Wiz definition
export const COURSE_MODULES = [
  "Aula em Turma",
  "Aula Teens Presencial",
  "Aulas VIP Personalizadas",
  "Intensivo Online Ouro",
  "Reposicao de Aula",
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
export const VIP_UNLIMITED = -1;

function normalized(value: unknown) {
  return String(value || "")
    .trim()
    .toLowerCase()
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "");
}

// Maps every legacy module name to a new canonical module name.
const LEGACY_MAP: Record<string, string> = {
  "ingles em turma online": "Aula em Turma",
  "turma presencial": "Aula em Turma",
  "aula em turma online": "Aula em Turma",
  "presencial em turma": "Aula em Turma",
  "online em turma": "Aula em Turma",
  "kids completo presencial": "Aula em Turma",
  "teens completo": "Aula Teens Presencial",
  "intensivo vip": "Intensivo Online Ouro",
  "intensivo vip online": "Intensivo Online Ouro",
  "aula intensivo vip": "Intensivo Online Ouro",
  "aula em turma vip": "Intensivo Online Ouro",
  "intensivo online ouro": "Intensivo Online Ouro",
  "intensino online ouro": "Intensivo Online Ouro",
  "vip": "Aulas VIP Personalizadas",
  "aulas vip": "Aulas VIP Personalizadas",
  "aula vip": "Aulas VIP Personalizadas",
  "aula vip particular": "Aulas VIP Personalizadas",
  "aula vip personalizada": "Aulas VIP Personalizadas",
  "aulas vip personalizadas": "Aulas VIP Personalizadas",
  "reposicoes": "Reposicao de Aula",
  "reposicao": "Reposicao de Aula",
  "reposicao de aula": "Reposicao de Aula",
  "repos": "Reposicao de Aula",
};

export function migrateModule(moduleName: unknown): string {
  const norm = normalized(moduleName);
  if (!norm) return "Aula em Turma";
  if (LEGACY_MAP[norm]) return LEGACY_MAP[norm];
  if (norm.includes("repos")) return "Reposicao de Aula";
  if (norm.includes("teens") || norm.includes("tens")) return "Aula Teens Presencial";
  if (norm.includes("intensivo") || norm.includes("intensino") || norm.includes("ouro")) return "Intensivo Online Ouro";
  if (norm === "vip" || (norm.includes("vip") && !norm.includes("intensivo") && !norm.includes("intensino") && !norm.includes("em turma"))) return "Aulas VIP Personalizadas";
  if (norm.includes("turma") || norm.includes("online") || norm.includes("presencial")) return "Aula em Turma";
  return "Aula em Turma";
}

// Teacher pay per class:
//   Aula em Turma             -> R$ 100
//   Aula Teens Presencial     -> R$ 100
//   Aulas VIP Personalizadas  -> R$  50
//   Intensivo Online Ouro     -> R$  30
//   Reposicao de Aula         -> R$  50
export function teacherClassValueByModule(moduleName: unknown): number {
  const m = normalized(moduleName);
  if (!m) return 0;
  if (m.includes("repos")) return 50;
  if (m.includes("intensivo") || m.includes("intensino") || m.includes("ouro")) return 30;
  if (m.includes("teens")) return 100;
  if (m.includes("vip")) return 50;
  if (m.includes("turma")) return 100;
  return 0;
}

// Only "Aulas VIP Personalizadas" triggers the lesson-package counter.
export function isVipModule(moduleName: unknown): boolean {
  const m = normalized(moduleName);
  return m === "aulas vip personalizadas" || m === "aula vip personalizada" || m === "aula vip particular" || m === "vip particular";
}

export function isVipUnlimitedPlan(planName: unknown): boolean {
  const plan = normalized(planName);
  return plan.includes("indetermin") || plan.includes("ilimitad") || plan.includes("sem limite");
}

export function vipPlanTotal(planName: unknown): number {
  if (isVipUnlimitedPlan(planName)) return VIP_UNLIMITED;
  const plan = normalized(planName);
  if (plan.includes("10")) return VIP_DEFAULT_TOTAL;
  if (plan.includes("avulsa") || plan.includes("avulso")) return 1;
  return VIP_DEFAULT_TOTAL;
}

function toInt(value: unknown) {
  const n = parseInt(String(value || "0"), 10);
  return Number.isFinite(n) ? n : 0;
}

export function vipPackageStats(aluno: Record<string, unknown>): {
  total: number; dadas: number; restantes: number; unlimited: boolean;
} | null {
  const modulo = aluno.modulo || aluno.modalidade || aluno.tipo_aula;
  const hasVipPlan = isVipModule(aluno.vip_tipo_plano);
  if (!isVipModule(modulo) && !hasVipPlan) return null;

  const planName = aluno.vip_tipo_plano || "Pacote 10 aulas";
  const unlimited = isVipUnlimitedPlan(planName) || toInt(aluno.vip_aulas_total) === VIP_UNLIMITED;
  if (unlimited) {
    const explicitDadas = toInt(aluno.vip_aulas_dadas ?? aluno.aulas_dadas_vip);
    return { total: VIP_UNLIMITED, dadas: explicitDadas, restantes: VIP_UNLIMITED, unlimited: true };
  }

  const planTotal = vipPlanTotal(planName);
  const total = Math.max(1, toInt(aluno.vip_aulas_total) || planTotal || VIP_DEFAULT_TOTAL);
  const explicitDadas = toInt(aluno.vip_aulas_dadas ?? aluno.aulas_dadas_vip);
  const rawRestantes = aluno.vip_aulas_restantes;
  const restantes = rawRestantes === null || rawRestantes === undefined || rawRestantes === ""
    ? Math.max(0, total - explicitDadas)
    : Math.min(total, Math.max(0, toInt(rawRestantes)));
  const dadas = Math.max(0, explicitDadas || (total - restantes));

  return { total, dadas, restantes, unlimited: false };
}

export function formatModuleValue(moduleName: unknown): string {
  const value = teacherClassValueByModule(moduleName);
  return value.toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
}
