export const COURSE_MODULES = [
  "Ingles em turma online",
  "Turma presencial",
  "Intensivo Vip",
  "Aulas Vip",
  "Teens Completo",
  "Reposicoes",
  "Aula em turma Online",
  "Aula em turma Vip",
  "Vip",
  "Intensivo vip online",
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
    .replace(/[\u0300-\u036f]/g, "");
}

export function teacherClassValueByModule(moduleName: unknown) {
  const module = normalized(moduleName);
  if (!module) return 0;
  if (module.includes("repos")) return 50;
  if (module.includes("intensivo") && module.includes("vip")) return 30;
  if (module.includes("teens") || module.includes("tens")) return 100;
  if (module.includes("aulas vip") || module === "vip") return 50;
  if (module.includes("turma") || module.includes("presencial") || module.includes("online")) return 100;
  return 0;
}

export function isVipModule(moduleName: unknown) {
  return normalized(moduleName).includes("vip");
}

export function vipPlanTotal(planName: unknown) {
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
  const modulo = aluno.modulo || aluno.modalidade || aluno.tipo_aula || aluno.vip_tipo_plano;
  const hasExplicitCounter = toInt(aluno.vip_aulas_total) > 0 || toInt(aluno.vip_aulas_restantes) > 0;
  const hasVipPlan = isVipModule(aluno.vip_tipo_plano);
  if (!isVipModule(modulo) && !hasVipPlan && !hasExplicitCounter) return null;

  const planTotal = vipPlanTotal(aluno.vip_tipo_plano || "Pacote 10 aulas");
  const total = Math.max(1, toInt(aluno.vip_aulas_total) || planTotal || VIP_DEFAULT_TOTAL);
  const restantes = Math.min(total, Math.max(0, toInt(aluno.vip_aulas_restantes || total)));
  const dadas = Math.max(0, total - restantes);

  return { total, dadas, restantes };
}

export function formatModuleValue(moduleName: unknown) {
  const value = teacherClassValueByModule(moduleName);
  return value.toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
}
