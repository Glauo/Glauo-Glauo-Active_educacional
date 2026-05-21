export const SALES_LEADS_KEY = "sales_leads.json";
export const SALES_AGENDA_KEY = "sales_agenda.json";

export const LEAD_STATUS_OPTIONS = [
  "Novo contato",
  "Leads frios",
  "Leads quentes",
  "Evoluindo",
  "Fechado",
  "Desistir",
  "Indicacao de alunos",
] as const;

export const PIPELINE_STAGE_OPTIONS = [
  "Descoberta",
  "Contato inicial",
  "Qualificacao",
  "Apresentacao",
  "Negociacao",
  "Fechamento",
  "Pos-venda",
  "Descartado",
] as const;

export const AGENDA_TYPE_OPTIONS = [
  "Ligacao",
  "WhatsApp",
  "Visita",
  "Reuniao online",
  "Matricula",
  "Retorno",
] as const;

export type CommercialLead = {
  id?: string;
  nome?: string;
  name?: string;
  telefone?: string;
  celular?: string;
  whatsapp?: string;
  email?: string;
  status?: string;
  etapa?: string;
  situacao?: string;
  estagio_funil?: string;
  origem?: string;
  interesse?: string;
  curso?: string;
  modulo?: string;
  cargo?: string;
  empresa?: string;
  cidade?: string;
  estado?: string;
  tags?: unknown;
  campos_personalizados?: unknown;
  observacao?: string;
  vendedor?: string;
  responsavel?: string;
  atendente?: string;
  created_at?: string;
  updated_at?: string;
  ultimo_contato?: string;
  interacoes?: unknown[];
  landing_pages?: unknown[];
  conversoes?: unknown[];
  [key: string]: unknown;
};

export type CommercialAgendaItem = {
  id?: string;
  lead_id?: string;
  lead_nome?: string;
  lead_telefone?: string;
  nome?: string;
  cliente?: string;
  aluno?: string;
  tipo?: string;
  data?: string;
  date?: string;
  hora?: string;
  duracao_minutos?: number | string;
  detalhes?: string;
  descricao?: string;
  observacao?: string;
  obs?: string;
  meeting_link?: string;
  google_calendar_link?: string;
  status?: string;
  situacao?: string;
  vendedor?: string;
  created_at?: string;
  updated_at?: string;
  whatsapp_sent?: boolean;
  whatsapp_status?: string;
  [key: string]: unknown;
};

export function text(value: unknown) {
  return String(value || "").trim();
}

export function lower(value: unknown) {
  return text(value).toLowerCase();
}

export function canManageCommercial(perfil: unknown) {
  const role = lower(perfil);
  return ["admin", "coord", "dire", "gestor", "comercial"].some((item) => role.includes(item));
}

export function leadName(lead: CommercialLead, fallback = "Lead") {
  return text(lead.nome || lead.name || fallback);
}

export function leadPhone(lead: CommercialLead) {
  return text(lead.telefone || lead.whatsapp || lead.celular);
}

export function leadStage(lead: CommercialLead) {
  return text(lead.estagio_funil || lead.etapa || "Contato inicial");
}

export function leadStatus(lead: CommercialLead) {
  return text(lead.status || lead.situacao || "Novo contato");
}

export function normalizeTags(value: unknown) {
  const items = Array.isArray(value) ? value : text(value).split(",");
  return Array.from(new Set(items.map((item) => text(item)).filter(Boolean)));
}

export function nowIso() {
  return new Date().toISOString();
}

export function legacyDate(value: unknown) {
  const raw = text(value);
  const iso = raw.match(/^(\d{4})-(\d{2})-(\d{2})$/);
  return iso ? `${iso[3]}/${iso[2]}/${iso[1]}` : raw;
}
