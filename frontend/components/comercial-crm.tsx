"use client";

import { useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { AutoWhatsAppButton } from "@/components/auto-whatsapp-button";
import {
  AGENDA_TYPE_OPTIONS,
  LEAD_STATUS_OPTIONS,
  PIPELINE_STAGE_OPTIONS,
  leadName,
  leadPhone,
  leadStage,
  leadStatus,
  normalizeTags,
  text,
  type CommercialAgendaItem,
  type CommercialLead,
} from "@/lib/comercial";

type LeadForm = {
  nome: string;
  telefone: string;
  celular: string;
  email: string;
  status: string;
  estagio_funil: string;
  origem: string;
  interesse: string;
  vendedor: string;
  cidade: string;
  estado: string;
  tags: string;
  observacao: string;
};

type AgendaForm = {
  lead_id: string;
  tipo: string;
  data: string;
  hora: string;
  duracao_minutos: string;
  detalhes: string;
  meeting_link: string;
  status: string;
};

function closeIcon() {
  return <svg viewBox="0 0 20 20" fill="currentColor"><path fillRule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clipRule="evenodd" /></svg>;
}

function editIcon() {
  return <svg viewBox="0 0 20 20" fill="currentColor"><path d="M13.586 3.586a2 2 0 112.828 2.828l-.793.793-2.828-2.828.793-.793zM11.379 5.793L3 14.172V17h2.828l8.38-8.379-2.83-2.828z" /></svg>;
}

function plusIcon() {
  return <svg viewBox="0 0 20 20" fill="currentColor"><path fillRule="evenodd" d="M10 3a1 1 0 011 1v5h5a1 1 0 110 2h-5v5a1 1 0 11-2 0v-5H4a1 1 0 110-2h5V4a1 1 0 011-1z" clipRule="evenodd" /></svg>;
}

function lower(value: unknown) {
  return text(value).toLowerCase();
}

function dateForInput(value: unknown) {
  const raw = text(value);
  const br = raw.match(/^(\d{2})\/(\d{2})\/(\d{4})$/);
  if (br) return `${br[3]}-${br[2]}-${br[1]}`;
  return raw.match(/^\d{4}-\d{2}-\d{2}$/) ? raw : "";
}

function dateValue(value: unknown) {
  const normalized = dateForInput(value);
  return normalized ? new Date(`${normalized}T12:00:00`).getTime() : Number.MAX_SAFE_INTEGER;
}

function tagsText(value: unknown) {
  return normalizeTags(value).join(", ");
}

function leadForm(lead?: CommercialLead, seller = ""): LeadForm {
  return {
    nome: leadName(lead || {}, ""),
    telefone: text(lead?.telefone || lead?.whatsapp),
    celular: text(lead?.celular),
    email: text(lead?.email),
    status: leadStatus(lead || {}),
    estagio_funil: leadStage(lead || {}),
    origem: text(lead?.origem),
    interesse: text(lead?.interesse || lead?.curso || lead?.modulo),
    vendedor: text(lead?.vendedor || lead?.responsavel || lead?.atendente || seller),
    cidade: text(lead?.cidade),
    estado: text(lead?.estado),
    tags: tagsText(lead?.tags),
    observacao: text(lead?.observacao),
  };
}

function agendaForm(item?: CommercialAgendaItem, lead?: CommercialLead): AgendaForm {
  return {
    lead_id: text(item?.lead_id || lead?.id),
    tipo: text(item?.tipo || "Retorno"),
    data: dateForInput(item?.data || item?.date) || new Date().toISOString().slice(0, 10),
    hora: text(item?.hora || "10:00"),
    duracao_minutos: text(item?.duracao_minutos || "45"),
    detalhes: text(item?.detalhes || item?.descricao || item?.observacao || item?.obs),
    meeting_link: text(item?.meeting_link),
    status: text(item?.status || item?.situacao || "Agendado"),
  };
}

function tone(value: unknown) {
  const current = lower(value);
  if (current.includes("fech") || current.includes("conclu") || current.includes("pos")) return "success";
  if (current.includes("desist") || current.includes("descart") || current.includes("cancel")) return "danger";
  if (current.includes("quente") || current.includes("negocia") || current.includes("agenda")) return "warning";
  return "neutral";
}

function agendaClient(item: CommercialAgendaItem) {
  return text(item.lead_nome || item.nome || item.cliente || item.aluno || "Lead");
}

function agendaDetails(item: CommercialAgendaItem) {
  return text(item.detalhes || item.descricao || item.observacao || item.obs);
}

function waMessage(lead: CommercialLead) {
  const interest = text(lead.interesse || lead.curso || lead.modulo);
  return `Ola ${leadName(lead)}! Aqui e da Active Educacional. Quero dar continuidade ao seu atendimento${interest ? ` sobre ${interest}` : ""}.`;
}

async function apiRequest(url: string, method: string, payload?: unknown) {
  const response = await fetch(url, {
    method,
    headers: payload ? { "Content-Type": "application/json" } : undefined,
    body: payload ? JSON.stringify(payload) : undefined,
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(text((data as { error?: string }).error || "Nao foi possivel salvar."));
  return data;
}

function LeadModal({ lead, seller, onClose, onSaved }: { lead?: CommercialLead; seller: string; onClose: () => void; onSaved: () => void }) {
  const isEdit = Boolean(lead?.id);
  const [form, setForm] = useState<LeadForm>(() => leadForm(lead, seller));
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  function update(field: keyof LeadForm, value: string) {
    setForm((current) => ({ ...current, [field]: value }));
    setError("");
  }

  async function save() {
    setSaving(true);
    setError("");
    try {
      await apiRequest("/api/comercial/leads", isEdit ? "PUT" : "POST", { ...(isEdit ? { id: lead?.id } : {}), ...form, tags: normalizeTags(form.tags) });
      onSaved();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erro ao salvar lead.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="modal-overlay" onClick={(event) => event.target === event.currentTarget && onClose()}>
      <div className="modal-box commercial-modal-box">
        <div className="modal-header">
          <div><div className="modal-title">{isEdit ? "Editar lead" : "Novo lead"}</div><div className="modal-subtitle">Cadastro ligado ao funil e agenda.</div></div>
          <button className="modal-close" type="button" aria-label="Fechar" onClick={onClose}>{closeIcon()}</button>
        </div>
        <div className="modal-body">
          <div className="form-grid">
            <div className="form-group form-group-span2"><label className="form-label">Nome *</label><input className="form-input" value={form.nome} onChange={(event) => update("nome", event.target.value)} autoFocus /></div>
            <div className="form-group"><label className="form-label">Telefone / WhatsApp *</label><input className="form-input" value={form.telefone} onChange={(event) => update("telefone", event.target.value)} /></div>
            <div className="form-group"><label className="form-label">Celular</label><input className="form-input" value={form.celular} onChange={(event) => update("celular", event.target.value)} /></div>
            <div className="form-group"><label className="form-label">E-mail</label><input className="form-input" type="email" value={form.email} onChange={(event) => update("email", event.target.value)} /></div>
            <div className="form-group"><label className="form-label">Consultor</label><input className="form-input" value={form.vendedor} onChange={(event) => update("vendedor", event.target.value)} /></div>
            <div className="form-group"><label className="form-label">Etapa do funil</label><select className="form-input" value={form.estagio_funil} onChange={(event) => update("estagio_funil", event.target.value)}>{PIPELINE_STAGE_OPTIONS.map((stage) => <option key={stage}>{stage}</option>)}</select></div>
            <div className="form-group"><label className="form-label">Status</label><select className="form-input" value={form.status} onChange={(event) => update("status", event.target.value)}>{LEAD_STATUS_OPTIONS.map((status) => <option key={status}>{status}</option>)}</select></div>
            <div className="form-group"><label className="form-label">Origem</label><input className="form-input" placeholder="Instagram, indicacao..." value={form.origem} onChange={(event) => update("origem", event.target.value)} /></div>
            <div className="form-group"><label className="form-label">Interesse / curso</label><input className="form-input" value={form.interesse} onChange={(event) => update("interesse", event.target.value)} /></div>
            <div className="form-group"><label className="form-label">Cidade</label><input className="form-input" value={form.cidade} onChange={(event) => update("cidade", event.target.value)} /></div>
            <div className="form-group"><label className="form-label">Estado</label><input className="form-input" maxLength={2} value={form.estado} onChange={(event) => update("estado", event.target.value.toUpperCase())} /></div>
            <div className="form-group form-group-span2"><label className="form-label">Tags</label><input className="form-input" placeholder="VIP, retorno, indicacao" value={form.tags} onChange={(event) => update("tags", event.target.value)} /></div>
            <div className="form-group form-group-span2"><label className="form-label">Observacoes</label><textarea className="form-input form-textarea" rows={4} value={form.observacao} onChange={(event) => update("observacao", event.target.value)} /></div>
          </div>
          {error && <div className="form-error">{error}</div>}
        </div>
        <div className="modal-footer">
          <button className="btn btn-secondary" type="button" onClick={onClose} disabled={saving}>Cancelar</button>
          <button className="btn btn-primary" type="button" onClick={save} disabled={saving}>{saving ? "Salvando..." : isEdit ? "Salvar lead" : "Criar lead"}</button>
        </div>
      </div>
    </div>
  );
}

function AgendaModal({ item, lead, leads, onClose, onSaved }: { item?: CommercialAgendaItem; lead?: CommercialLead; leads: CommercialLead[]; onClose: () => void; onSaved: () => void }) {
  const isEdit = Boolean(item?.id);
  const [form, setForm] = useState<AgendaForm>(() => agendaForm(item, lead));
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  function update(field: keyof AgendaForm, value: string) {
    setForm((current) => ({ ...current, [field]: value }));
    setError("");
  }

  async function save() {
    setSaving(true);
    setError("");
    try {
      await apiRequest("/api/comercial/agenda", isEdit ? "PUT" : "POST", { ...(isEdit ? { id: item?.id } : {}), ...form, duracao_minutos: Number(form.duracao_minutos) || 45 });
      onSaved();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erro ao salvar agendamento.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="modal-overlay" onClick={(event) => event.target === event.currentTarget && onClose()}>
      <div className="modal-box">
        <div className="modal-header">
          <div><div className="modal-title">{isEdit ? "Editar agendamento" : "Novo agendamento"}</div><div className="modal-subtitle">Retorno comercial ligado ao lead.</div></div>
          <button className="modal-close" type="button" aria-label="Fechar" onClick={onClose}>{closeIcon()}</button>
        </div>
        <div className="modal-body">
          <div className="form-grid">
            <div className="form-group form-group-span2">
              <label className="form-label">Lead *</label>
              <select className="form-input" value={form.lead_id} onChange={(event) => update("lead_id", event.target.value)}>
                <option value="">Selecione</option>
                {leads.map((current) => <option key={text(current.id)} value={text(current.id)}>{leadName(current)} {leadPhone(current) ? `- ${leadPhone(current)}` : ""}</option>)}
              </select>
            </div>
            <div className="form-group"><label className="form-label">Tipo</label><select className="form-input" value={form.tipo} onChange={(event) => update("tipo", event.target.value)}>{AGENDA_TYPE_OPTIONS.map((type) => <option key={type}>{type}</option>)}</select></div>
            <div className="form-group"><label className="form-label">Status</label><select className="form-input" value={form.status} onChange={(event) => update("status", event.target.value)}><option>Agendado</option><option>Concluido</option><option>Cancelado</option></select></div>
            <div className="form-group"><label className="form-label">Data *</label><input className="form-input" type="date" value={form.data} onChange={(event) => update("data", event.target.value)} /></div>
            <div className="form-group"><label className="form-label">Horario</label><input className="form-input" type="time" value={form.hora} onChange={(event) => update("hora", event.target.value)} /></div>
            <div className="form-group"><label className="form-label">Duracao (min)</label><input className="form-input" type="number" min={15} max={240} step={15} value={form.duracao_minutos} onChange={(event) => update("duracao_minutos", event.target.value)} /></div>
            <div className="form-group"><label className="form-label">Link da reuniao</label><input className="form-input" value={form.meeting_link} onChange={(event) => update("meeting_link", event.target.value)} /></div>
            <div className="form-group form-group-span2"><label className="form-label">Detalhes</label><textarea className="form-input form-textarea" rows={3} value={form.detalhes} onChange={(event) => update("detalhes", event.target.value)} /></div>
          </div>
          {error && <div className="form-error">{error}</div>}
        </div>
        <div className="modal-footer">
          <button className="btn btn-secondary" type="button" onClick={onClose} disabled={saving}>Cancelar</button>
          <button className="btn btn-primary" type="button" onClick={save} disabled={saving}>{saving ? "Salvando..." : "Salvar agenda"}</button>
        </div>
      </div>
    </div>
  );
}

export function ComercialCrm({ leads, agenda, seller }: { leads: CommercialLead[]; agenda: CommercialAgendaItem[]; seller: string }) {
  const router = useRouter();
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("Todos");
  const [leadModal, setLeadModal] = useState<CommercialLead | "new" | null>(null);
  const [agendaModal, setAgendaModal] = useState<{ item?: CommercialAgendaItem; lead?: CommercialLead } | null>(null);
  const [busy, setBusy] = useState("");
  const [notice, setNotice] = useState("");

  const visibleLeads = useMemo(() => {
    const query = lower(search);
    return leads.filter((lead) => {
      const searchable = [leadName(lead), leadPhone(lead), lead.email, lead.interesse, lead.origem, lead.vendedor, tagsText(lead.tags)].map(lower).join(" ");
      const statusOk = statusFilter === "Todos" || leadStatus(lead) === statusFilter;
      return statusOk && (!query || searchable.includes(query));
    });
  }, [leads, search, statusFilter]);

  const agendaOrdered = useMemo(() => [...agenda].sort((left, right) => dateValue(left.data || left.date) - dateValue(right.data || right.date) || text(left.hora).localeCompare(text(right.hora))), [agenda]);

  function saved() {
    setLeadModal(null);
    setAgendaModal(null);
    setNotice("Comercial atualizado.");
    router.refresh();
  }

  async function patchLead(lead: CommercialLead, changes: Partial<CommercialLead>) {
    if (!lead.id) return;
    setBusy(`lead-${lead.id}`);
    setNotice("");
    try {
      await apiRequest("/api/comercial/leads", "PUT", { id: lead.id, ...changes });
      setNotice("Lead atualizado no funil.");
      router.refresh();
    } catch (err) {
      setNotice(err instanceof Error ? err.message : "Nao foi possivel atualizar o lead.");
    } finally {
      setBusy("");
    }
  }

  async function patchAgenda(item: CommercialAgendaItem, status: string) {
    if (!item.id) return;
    setBusy(`agenda-${item.id}`);
    setNotice("");
    try {
      await apiRequest("/api/comercial/agenda", "PUT", { id: item.id, status });
      setNotice("Agenda comercial atualizada.");
      router.refresh();
    } catch (err) {
      setNotice(err instanceof Error ? err.message : "Nao foi possivel atualizar a agenda.");
    } finally {
      setBusy("");
    }
  }

  return (
    <>
      <section className="card commercial-workbench">
        <div className="card-header commercial-card-header">
          <div><div className="section-eyebrow">FUNIL</div><h3 className="section-title">Pipeline de leads</h3><p className="section-subtitle">Mova o lead por etapa, agende retornos e mantenha o atendimento no mesmo painel.</p></div>
          <div className="commercial-toolbar-actions"><button className="btn btn-secondary" type="button" onClick={() => setAgendaModal({})} disabled={leads.length === 0}>{plusIcon()}Agendar</button><button className="btn btn-primary" type="button" onClick={() => setLeadModal("new")}>{plusIcon()}Novo lead</button></div>
        </div>
        <div className="card-body commercial-workbench-body">
          <div className="commercial-filters">
            <div className="search-bar"><span className="search-icon"><svg viewBox="0 0 20 20" fill="currentColor"><path fillRule="evenodd" d="M8.5 3a5.5 5.5 0 104.07 9.2l3.61 3.62a1 1 0 001.42-1.42l-3.62-3.61A5.5 5.5 0 008.5 3zm-3.5 5.5a3.5 3.5 0 117 0 3.5 3.5 0 01-7 0z" clipRule="evenodd" /></svg></span><input className="search-input" value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Buscar lead, telefone, origem ou interesse" /></div>
            <select className="form-input" value={statusFilter} onChange={(event) => setStatusFilter(event.target.value)}><option>Todos</option>{LEAD_STATUS_OPTIONS.map((status) => <option key={status}>{status}</option>)}</select>
          </div>
          {notice && <div className="commercial-notice">{notice}</div>}
          <div className="commercial-board" aria-label="Funil comercial">
            {PIPELINE_STAGE_OPTIONS.map((stage) => {
              const stageLeads = visibleLeads.filter((lead) => leadStage(lead) === stage);
              return (
                <section className="commercial-stage" key={stage}>
                  <div className="commercial-stage-head"><strong>{stage}</strong><span>{stageLeads.length}</span></div>
                  <div className="commercial-stage-list">
                    {stageLeads.length === 0 && <div className="commercial-stage-empty">Sem leads nesta etapa.</div>}
                    {stageLeads.map((lead) => (
                      <article className="commercial-lead" key={text(lead.id) || `${leadName(lead)}-${stage}`}>
                        <div className="commercial-lead-head"><button className="commercial-lead-name" type="button" onClick={() => setLeadModal(lead)}>{leadName(lead)}</button><button className="btn btn-ghost btn-sm btn-icon" type="button" title="Editar lead" onClick={() => setLeadModal(lead)}>{editIcon()}</button></div>
                        <div className="commercial-lead-meta">{text(lead.interesse || lead.curso || lead.origem || "Sem interesse informado")}</div>
                        <div className="commercial-lead-badges"><span className={`badge badge-${tone(leadStatus(lead))}`}><span className="badge-dot" />{leadStatus(lead)}</span>{leadPhone(lead) && <span className="commercial-phone">{leadPhone(lead)}</span>}</div>
                        <div className="commercial-inline-fields">
                          <select className="form-input" aria-label={`Etapa de ${leadName(lead)}`} value={leadStage(lead)} disabled={busy === `lead-${lead.id}`} onChange={(event) => patchLead(lead, { estagio_funil: event.target.value })}>{PIPELINE_STAGE_OPTIONS.map((option) => <option key={option}>{option}</option>)}</select>
                          <select className="form-input" aria-label={`Status de ${leadName(lead)}`} value={leadStatus(lead)} disabled={busy === `lead-${lead.id}`} onChange={(event) => patchLead(lead, { status: event.target.value })}>{LEAD_STATUS_OPTIONS.map((option) => <option key={option}>{option}</option>)}</select>
                        </div>
                        <div className="commercial-lead-actions"><button className="btn btn-secondary btn-sm" type="button" onClick={() => setAgendaModal({ lead })}>Agendar</button>{leadPhone(lead) && <AutoWhatsAppButton phone={leadPhone(lead)} message={waMessage(lead)} className="btn btn-ghost btn-sm" />}</div>
                      </article>
                    ))}
                  </div>
                </section>
              );
            })}
          </div>
        </div>
      </section>

      <section className="card">
        <div className="card-header commercial-card-header">
          <div><div className="section-eyebrow">AGENDA</div><h3 className="section-title">Tarefas e retornos comerciais</h3><p className="section-subtitle">A agenda mantem o proximo contato visivel para cada oportunidade.</p></div>
          <button className="btn btn-secondary" type="button" onClick={() => setAgendaModal({})} disabled={leads.length === 0}>{plusIcon()}Novo retorno</button>
        </div>
        <div className="card-body commercial-agenda-wrap">
          {agendaOrdered.length === 0 ? <div className="empty-state"><div className="empty-title">Sem retornos comerciais</div><p className="empty-desc">Agende um contato a partir do lead para acompanhar a oportunidade.</p></div> : (
            <table className="data-table commercial-agenda-table">
              <thead><tr><th>Quando</th><th>Lead</th><th>Tipo</th><th>Status</th><th>Detalhes</th><th>Acoes</th></tr></thead>
              <tbody>
                {agendaOrdered.map((item, index) => (
                  <tr key={text(item.id) || index}>
                    <td><strong>{text(item.data || item.date) || "-"}</strong><div className="muted">{text(item.hora) || "--:--"} | {text(item.duracao_minutos || 45)} min</div></td>
                    <td><span className="table-name-primary">{agendaClient(item)}</span><div className="muted">{text(item.lead_telefone)}</div></td>
                    <td>{text(item.tipo || "Retorno")}</td>
                    <td><span className={`badge badge-${tone(item.status || item.situacao)}`}><span className="badge-dot" />{text(item.status || item.situacao || "Agendado")}</span></td>
                    <td>{agendaDetails(item) || "-"}</td>
                    <td><div className="commercial-agenda-actions"><button className="btn btn-ghost btn-sm btn-icon" type="button" title="Editar agendamento" onClick={() => setAgendaModal({ item })}>{editIcon()}</button><button className="btn btn-secondary btn-sm" type="button" disabled={busy === `agenda-${item.id}`} onClick={() => patchAgenda(item, "Concluido")}>Concluir</button><button className="btn btn-ghost btn-sm" type="button" disabled={busy === `agenda-${item.id}`} onClick={() => patchAgenda(item, "Cancelado")}>Cancelar</button></div></td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </section>

      {leadModal && <LeadModal lead={leadModal === "new" ? undefined : leadModal} seller={seller} onClose={() => setLeadModal(null)} onSaved={saved} />}
      {agendaModal && <AgendaModal item={agendaModal.item} lead={agendaModal.lead} leads={leads} onClose={() => setAgendaModal(null)} onSaved={saved} />}
    </>
  );
}
