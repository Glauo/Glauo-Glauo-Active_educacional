import { NextRequest, NextResponse } from "next/server";
import { getSession } from "@/lib/auth";
import { dbList, dbSet } from "@/lib/db";
import {
  SALES_AGENDA_KEY,
  SALES_LEADS_KEY,
  canManageCommercial,
  leadName,
  leadPhone,
  legacyDate,
  nowIso,
  text,
  type CommercialAgendaItem,
  type CommercialLead,
} from "@/lib/comercial";

function unauthorized() {
  return NextResponse.json({ error: "Nao autorizado." }, { status: 401 });
}

function duration(value: unknown) {
  const parsed = Number(value);
  return Number.isFinite(parsed) && parsed > 0 ? Math.min(Math.round(parsed), 240) : 45;
}

function agendaFields(body: CommercialAgendaItem) {
  const next: CommercialAgendaItem = {};
  const keys: (keyof CommercialAgendaItem)[] = [
    "lead_id",
    "tipo",
    "data",
    "hora",
    "detalhes",
    "meeting_link",
    "status",
    "vendedor",
  ];
  for (const key of keys) {
    if (key in body) next[key] = text(body[key]);
  }
  if ("data" in next) next.data = legacyDate(next.data);
  if ("duracao_minutos" in body) next.duracao_minutos = duration(body.duracao_minutos);
  return next;
}

async function leadById(id: string) {
  const leads = await dbList<CommercialLead>(SALES_LEADS_KEY);
  return leads.find((lead) => text(lead.id) === id);
}

export async function GET() {
  const session = await getSession();
  if (!session || !canManageCommercial(session.perfil)) return unauthorized();
  const agenda = await dbList<CommercialAgendaItem>(SALES_AGENDA_KEY);
  return NextResponse.json({ agenda });
}

export async function POST(req: NextRequest) {
  const session = await getSession();
  if (!session || !canManageCommercial(session.perfil)) return unauthorized();

  const body = (await req.json()) as CommercialAgendaItem;
  const fields = agendaFields(body);
  const leadId = text(fields.lead_id);
  const lead = await leadById(leadId);
  if (!lead) return NextResponse.json({ error: "Selecione um lead valido." }, { status: 400 });
  if (!text(fields.data)) return NextResponse.json({ error: "Informe a data do agendamento." }, { status: 400 });

  const createdAt = nowIso();
  const item: CommercialAgendaItem = {
    ...body,
    ...fields,
    id: text(body.id) || crypto.randomUUID(),
    lead_id: leadId,
    lead_nome: leadName(lead),
    lead_telefone: leadPhone(lead),
    tipo: text(fields.tipo || "Retorno"),
    data: legacyDate(fields.data),
    hora: text(fields.hora),
    duracao_minutos: duration(fields.duracao_minutos),
    detalhes: text(fields.detalhes),
    meeting_link: text(fields.meeting_link),
    status: text(fields.status || "Agendado"),
    vendedor: text(fields.vendedor || session.pessoa || session.usuario),
    created_at: text(body.created_at || createdAt),
    updated_at: createdAt,
    whatsapp_sent: Boolean(body.whatsapp_sent),
    whatsapp_status: text(body.whatsapp_status),
  };

  const agenda = await dbList<CommercialAgendaItem>(SALES_AGENDA_KEY);
  await dbSet(SALES_AGENDA_KEY, [...agenda, item]);
  return NextResponse.json({ item }, { status: 201 });
}

export async function PUT(req: NextRequest) {
  const session = await getSession();
  if (!session || !canManageCommercial(session.perfil)) return unauthorized();

  const body = (await req.json()) as CommercialAgendaItem;
  const id = text(body.id);
  if (!id) return NextResponse.json({ error: "id obrigatorio." }, { status: 400 });

  const agenda = await dbList<CommercialAgendaItem>(SALES_AGENDA_KEY);
  const index = agenda.findIndex((item) => text(item.id) === id);
  if (index === -1) return NextResponse.json({ error: "Agendamento nao encontrado." }, { status: 404 });

  const updates = agendaFields(body);
  const leadId = text(updates.lead_id || agenda[index].lead_id);
  const lead = leadId ? await leadById(leadId) : null;
  const next: CommercialAgendaItem = {
    ...agenda[index],
    ...updates,
    id,
    lead_id: leadId,
    lead_nome: lead ? leadName(lead) : text(agenda[index].lead_nome),
    lead_telefone: lead ? leadPhone(lead) : text(agenda[index].lead_telefone),
    updated_at: nowIso(),
  };
  if (!text(next.data)) return NextResponse.json({ error: "Informe a data do agendamento." }, { status: 400 });

  agenda[index] = next;
  await dbSet(SALES_AGENDA_KEY, agenda);
  return NextResponse.json({ item: next });
}
