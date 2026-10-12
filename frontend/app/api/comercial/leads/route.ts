import { NextRequest, NextResponse } from "next/server";
import { getSession } from "@/lib/auth";
import { dbList, dbSet, dbTransaction } from "@/lib/db";
import {
  SALES_AGENDA_KEY,
  SALES_AUDIT_KEY,
  SALES_LEADS_KEY,
  canManageCommercial,
  leadPhone,
  normalizeTags,
  nowIso,
  text,
  type CommercialLead,
} from "@/lib/comercial";
import { isAdmin } from "@/lib/roles";

function unauthorized() {
  return NextResponse.json({ error: "Nao autorizado." }, { status: 401 });
}

function editableFields(body: CommercialLead) {
  const next: CommercialLead = {};
  const keys: (keyof CommercialLead)[] = [
    "nome",
    "telefone",
    "celular",
    "email",
    "status",
    "estagio_funil",
    "origem",
    "interesse",
    "cargo",
    "empresa",
    "cidade",
    "estado",
    "observacao",
    "vendedor",
    "ultimo_contato",
  ];

  for (const key of keys) {
    if (key in body) next[key] = text(body[key]);
  }

  if ("email" in next) next.email = text(next.email).toLowerCase();
  if ("tags" in body) next.tags = normalizeTags(body.tags);
  return next;
}

function validateLead(lead: CommercialLead) {
  if (!text(lead.nome || lead.name)) return "Informe o nome do lead.";
  if (!leadPhone(lead)) return "Informe telefone ou celular do lead.";
  return "";
}

export async function GET() {
  const session = await getSession();
  if (!session || !canManageCommercial(session.perfil)) return unauthorized();
  const leads = await dbList<CommercialLead>(SALES_LEADS_KEY);
  return NextResponse.json({ leads });
}

export async function POST(req: NextRequest) {
  const session = await getSession();
  if (!session || !canManageCommercial(session.perfil)) return unauthorized();

  const body = (await req.json()) as CommercialLead;
  const fields = editableFields(body);
  const fallbackPhone = text(fields.telefone || fields.celular);
  const createdAt = nowIso();
  const lead: CommercialLead = {
    ...body,
    ...fields,
    id: text(body.id) || crypto.randomUUID(),
    nome: text(fields.nome),
    telefone: text(fields.telefone || fallbackPhone),
    celular: text(fields.celular || fallbackPhone),
    status: text(fields.status || "Novo contato"),
    estagio_funil: text(fields.estagio_funil || "Contato inicial"),
    vendedor: text(fields.vendedor || session.pessoa || session.usuario),
    tags: normalizeTags(body.tags),
    campos_personalizados: body.campos_personalizados && typeof body.campos_personalizados === "object"
      ? body.campos_personalizados
      : {},
    created_at: text(body.created_at || createdAt),
    updated_at: createdAt,
    ultimo_contato: text(fields.ultimo_contato),
    interacoes: Array.isArray(body.interacoes) && body.interacoes.length
      ? body.interacoes
      : [{
          data_hora: createdAt,
          canal: "Sistema",
          acao: "Lead cadastrado",
          descricao: "Registro inicial criado no Comercial.",
          pagina: "",
        }],
    landing_pages: Array.isArray(body.landing_pages) ? body.landing_pages : [],
    conversoes: Array.isArray(body.conversoes) ? body.conversoes : [],
  };
  const validation = validateLead(lead);
  if (validation) return NextResponse.json({ error: validation }, { status: 400 });

  const leads = await dbList<CommercialLead>(SALES_LEADS_KEY);
  await dbSet(SALES_LEADS_KEY, [...leads, lead]);
  return NextResponse.json({ lead }, { status: 201 });
}

export async function PUT(req: NextRequest) {
  const session = await getSession();
  if (!session || !canManageCommercial(session.perfil)) return unauthorized();

  const body = (await req.json()) as CommercialLead;
  const id = text(body.id);
  if (!id) return NextResponse.json({ error: "id obrigatorio." }, { status: 400 });

  const leads = await dbList<CommercialLead>(SALES_LEADS_KEY);
  const index = leads.findIndex((lead) => text(lead.id) === id);
  if (index === -1) return NextResponse.json({ error: "Lead nao encontrado." }, { status: 404 });

  const next: CommercialLead = {
    ...leads[index],
    ...editableFields(body),
    id,
    updated_at: nowIso(),
  };
  if (!text(next.telefone) && text(next.celular)) next.telefone = text(next.celular);
  if (!text(next.celular) && text(next.telefone)) next.celular = text(next.telefone);

  const validation = validateLead(next);
  if (validation) return NextResponse.json({ error: validation }, { status: 400 });

  leads[index] = next;
  await dbSet(SALES_LEADS_KEY, leads);
  return NextResponse.json({ lead: next });
}

class LeadDeleteError extends Error {
  constructor(message: string, readonly status: number) {
    super(message);
  }
}

export async function DELETE(req: NextRequest) {
  const session = await getSession();
  if (!session) return unauthorized();
  if (!isAdmin(session)) {
    return NextResponse.json({ error: "Apenas o administrador pode excluir empresas e contatos." }, { status: 403 });
  }

  const id = text(new URL(req.url).searchParams.get("id"));
  if (!id) return NextResponse.json({ error: "id obrigatorio." }, { status: 400 });

  try {
    const result = await dbTransaction(
      [SALES_LEADS_KEY, SALES_AGENDA_KEY, SALES_AUDIT_KEY],
      (values) => {
        const leads = Array.isArray(values.sales_leads) ? values.sales_leads as CommercialLead[] : [];
        const index = leads.findIndex((lead) => text(lead.id) === id);
        if (index === -1) throw new LeadDeleteError("Cadastro nao encontrado.", 404);

        const lead = leads[index];
        const agenda = Array.isArray(values.sales_agenda) ? values.sales_agenda as Record<string, unknown>[] : [];
        const relatedAgenda = agenda.filter((item) => text(item.lead_id) === id);
        const audit = Array.isArray(values.sales_audit) ? values.sales_audit as Record<string, unknown>[] : [];

        values.sales_leads = leads.filter((_, leadIndex) => leadIndex !== index);
        values.sales_agenda = agenda.filter((item) => text(item.lead_id) !== id);
        values.sales_audit = [...audit, {
          id: crypto.randomUUID(),
          data_hora: nowIso(),
          acao: "excluir_empresa_contato",
          responsavel: text(session.pessoa || session.usuario),
          lead_id: id,
          nome: text(lead.nome || lead.name),
          empresa: text(lead.empresa),
          agendamentos_removidos: relatedAgenda.length,
        }];

        return { removedAgenda: relatedAgenda.length };
      },
    );

    return NextResponse.json({ ok: true, agendamentos_removidos: result.removedAgenda });
  } catch (error) {
    if (error instanceof LeadDeleteError) {
      return NextResponse.json({ error: error.message }, { status: error.status });
    }
    console.error("[comercial/leads] Falha ao excluir cadastro", error);
    return NextResponse.json({ error: "Nao foi possivel excluir o cadastro." }, { status: 500 });
  }
}
