"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";

type EventoData = {
  id?: string;
  titulo?: string;
  tipo?: string;
  data?: string;
  horario?: string;
  turma?: string;
  professor?: string;
  descricao?: string;
  status?: string;
  [k: string]: unknown;
};

type Form = {
  titulo: string;
  tipo: string;
  data: string;
  horario: string;
  turma: string;
  professor: string;
  descricao: string;
  status: string;
};

const hoje = () => new Date().toISOString().slice(0, 10);

function fromEvento(e?: EventoData): Form {
  return {
    titulo: String(e?.titulo || ""),
    tipo: String(e?.tipo || "Aula"),
    data: String(e?.data || hoje()),
    horario: String(e?.horario || e?.hora || ""),
    turma: String(e?.turma || ""),
    professor: String(e?.professor || ""),
    descricao: String(e?.descricao || ""),
    status: String(e?.status || "Agendado")
  };
}

function AgendaModal({
  evento,
  onClose,
  onSaved
}: {
  evento?: EventoData;
  onClose: () => void;
  onSaved: () => void;
}) {
  const isEdit = Boolean(evento?.id);
  const [form, setForm] = useState<Form>(fromEvento(evento));
  const [saving, setSaving] = useState(false);
  const [erro, setErro] = useState("");

  function update(field: keyof Form, value: string) {
    setForm((prev) => ({ ...prev, [field]: value }));
    setErro("");
  }

  async function excluir() {
    if (!confirm(`Excluir o evento "${evento?.titulo}"? Esta ação não pode ser desfeita.`)) return;
    setSaving(true);
    await fetch(`/api/agenda?id=${evento!.id}`, { method: "DELETE" });
    setSaving(false);
    onSaved();
  }

  async function salvar() {
    if (!form.titulo.trim()) { setErro("O título do evento é obrigatório."); return; }
    if (!form.data) { setErro("A data é obrigatória."); return; }

    setSaving(true);
    const payload = isEdit ? { id: evento!.id, ...form } : form;
    const res = await fetch("/api/agenda", {
      method: isEdit ? "PUT" : "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
    setSaving(false);
    if (!res.ok) {
      const d = await res.json().catch(() => ({}));
      setErro((d as { error?: string }).error || "Erro ao salvar.");
      return;
    }
    onSaved();
  }

  return (
    <div className="modal-overlay" onClick={(e) => e.target === e.currentTarget && onClose()}>
      <div className="modal-box">
        <div className="modal-header">
          <div>
            <div className="modal-title">{isEdit ? "Editar evento" : "Novo evento"}</div>
            {isEdit && <div className="modal-subtitle">{evento?.titulo}</div>}
          </div>
          <button className="modal-close" onClick={onClose}>
            <svg viewBox="0 0 20 20" fill="currentColor"><path fillRule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clipRule="evenodd" /></svg>
          </button>
        </div>

        <div className="modal-body">
          <div className="form-grid">
            <div className="form-group form-group-span2">
              <label className="form-label">Título *</label>
              <input
                className="form-input"
                placeholder="Ex: Aula — Turma A | Reunião de equipe"
                value={form.titulo}
                onChange={(e) => update("titulo", e.target.value)}
                autoFocus
              />
            </div>
            <div className="form-group">
              <label className="form-label">Tipo</label>
              <select className="form-input" value={form.tipo} onChange={(e) => update("tipo", e.target.value)}>
                <option>Aula</option>
                <option>Reunião</option>
                <option>Reposição</option>
                <option>Evento</option>
                <option>Feriado</option>
                <option>Recesso</option>
                <option>Avaliação</option>
                <option>Outro</option>
              </select>
            </div>
            <div className="form-group">
              <label className="form-label">Status</label>
              <select className="form-input" value={form.status} onChange={(e) => update("status", e.target.value)}>
                <option>Agendado</option>
                <option>Em andamento</option>
                <option>Concluído</option>
                <option>Cancelado</option>
                <option>Pendente confirmação</option>
              </select>
            </div>
            <div className="form-group">
              <label className="form-label">Data *</label>
              <input className="form-input" type="date" value={form.data} onChange={(e) => update("data", e.target.value)} />
            </div>
            <div className="form-group">
              <label className="form-label">Horário</label>
              <input className="form-input" type="time" value={form.horario} onChange={(e) => update("horario", e.target.value)} />
            </div>
            <div className="form-group">
              <label className="form-label">Turma</label>
              <input className="form-input" placeholder="Ex: Turma A" value={form.turma} onChange={(e) => update("turma", e.target.value)} />
            </div>
            <div className="form-group">
              <label className="form-label">Professor</label>
              <input className="form-input" placeholder="Nome do professor" value={form.professor} onChange={(e) => update("professor", e.target.value)} />
            </div>
            <div className="form-group form-group-span2">
              <label className="form-label">Observações</label>
              <textarea className="form-input form-textarea" rows={3} placeholder="Notas, conteúdo da aula, observações..." value={form.descricao} onChange={(e) => update("descricao", e.target.value)} />
            </div>
          </div>
          {erro && <div className="form-error">{erro}</div>}
        </div>

        <div className="modal-footer">
          {isEdit && <button className="btn btn-danger btn-sm" onClick={excluir} disabled={saving} style={{ marginRight: "auto" }}>Excluir</button>}
          <button className="btn btn-secondary" onClick={onClose} disabled={saving}>Cancelar</button>
          <button className="btn btn-primary" onClick={salvar} disabled={saving}>
            {saving ? "Salvando…" : isEdit ? "Salvar alterações" : "Criar evento"}
          </button>
        </div>
      </div>
    </div>
  );
}

export function NovoEventoBtn() {
  const router = useRouter();
  const [open, setOpen] = useState(false);
  return (
    <>
      <button className="btn btn-primary" onClick={() => setOpen(true)}>
        <svg viewBox="0 0 20 20" fill="currentColor"><path fillRule="evenodd" d="M10 3a1 1 0 011 1v5h5a1 1 0 110 2h-5v5a1 1 0 11-2 0v-5H4a1 1 0 110-2h5V4a1 1 0 011-1z" clipRule="evenodd" /></svg>
        Novo evento
      </button>
      {open && (
        <AgendaModal
          onClose={() => setOpen(false)}
          onSaved={() => { setOpen(false); router.refresh(); }}
        />
      )}
    </>
  );
}

export function EditarEventoBtn({ evento }: { evento: EventoData }) {
  const router = useRouter();
  const [open, setOpen] = useState(false);
  return (
    <>
      <button className="btn btn-ghost btn-sm btn-icon" title="Editar evento" onClick={() => setOpen(true)}>
        <svg viewBox="0 0 20 20" fill="currentColor"><path d="M13.586 3.586a2 2 0 112.828 2.828l-.793.793-2.828-2.828.793-.793zM11.379 5.793L3 14.172V17h2.828l8.38-8.379-2.83-2.828z" /></svg>
      </button>
      {open && (
        <AgendaModal
          evento={evento}
          onClose={() => setOpen(false)}
          onSaved={() => { setOpen(false); router.refresh(); }}
        />
      )}
    </>
  );
}
