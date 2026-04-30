"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";

type ProfessorData = {
  id?: string;
  nome?: string;
  email?: string;
  telefone?: string;
  area?: string;
  especialidade?: string;
  carga_horaria?: string | number;
  status?: string;
  [k: string]: unknown;
};

type Form = {
  nome: string;
  email: string;
  telefone: string;
  area: string;
  carga_horaria: string;
  status: string;
};

function fromProf(p?: ProfessorData): Form {
  return {
    nome: String(p?.nome || ""),
    email: String(p?.email || ""),
    telefone: String(p?.telefone || ""),
    area: String(p?.area || p?.especialidade || ""),
    carga_horaria: String(p?.carga_horaria || ""),
    status: String(p?.status || "Ativo")
  };
}

function ProfessorModal({
  professor,
  onClose,
  onSaved
}: {
  professor?: ProfessorData;
  onClose: () => void;
  onSaved: () => void;
}) {
  const isEdit = Boolean(professor?.id);
  const [form, setForm] = useState<Form>(fromProf(professor));
  const [saving, setSaving] = useState(false);
  const [erro, setErro] = useState("");

  function update(field: keyof Form, value: string) {
    setForm((prev) => ({ ...prev, [field]: value }));
    setErro("");
  }

  async function excluir() {
    if (!confirm(`Excluir o professor "${professor?.nome}"? Esta ação não pode ser desfeita.`)) return;
    setSaving(true);
    await fetch(`/api/professores?id=${professor!.id}`, { method: "DELETE" });
    setSaving(false);
    onSaved();
  }

  async function salvar() {
    if (!form.nome.trim()) {
      setErro("O nome do professor é obrigatório.");
      return;
    }
    setSaving(true);
    const payload = isEdit
      ? { id: professor!.id, ...form, especialidade: form.area }
      : { ...form, especialidade: form.area };
    const res = await fetch("/api/professores", {
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
            <div className="modal-title">{isEdit ? "Editar professor" : "Novo professor"}</div>
            {isEdit && <div className="modal-subtitle">{professor?.nome}</div>}
          </div>
          <button className="modal-close" onClick={onClose}>
            <svg viewBox="0 0 20 20" fill="currentColor"><path fillRule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clipRule="evenodd" /></svg>
          </button>
        </div>

        <div className="modal-body">
          <div className="form-grid">
            <div className="form-group form-group-span2">
              <label className="form-label">Nome completo *</label>
              <input
                className="form-input"
                placeholder="Nome do professor"
                value={form.nome}
                onChange={(e) => update("nome", e.target.value)}
                autoFocus
              />
            </div>
            <div className="form-group">
              <label className="form-label">E-mail</label>
              <input className="form-input" type="email" placeholder="email@exemplo.com" value={form.email} onChange={(e) => update("email", e.target.value)} />
            </div>
            <div className="form-group">
              <label className="form-label">Telefone</label>
              <input className="form-input" placeholder="(11) 99999-0000" value={form.telefone} onChange={(e) => update("telefone", e.target.value)} />
            </div>
            <div className="form-group form-group-span2">
              <label className="form-label">Área / Especialidade</label>
              <input className="form-input" placeholder="Ex: Inglês, Conversação, Preparatório" value={form.area} onChange={(e) => update("area", e.target.value)} />
            </div>
            <div className="form-group">
              <label className="form-label">Carga horária semanal</label>
              <input className="form-input" type="number" placeholder="Horas/semana" value={form.carga_horaria} onChange={(e) => update("carga_horaria", e.target.value)} min="0" />
            </div>
            <div className="form-group">
              <label className="form-label">Status</label>
              <select className="form-input" value={form.status} onChange={(e) => update("status", e.target.value)}>
                <option>Ativo</option>
                <option>Inativo</option>
                <option>Afastado</option>
              </select>
            </div>
          </div>
          {erro && <div className="form-error">{erro}</div>}
        </div>

        <div className="modal-footer">
          {isEdit && <button className="btn btn-danger btn-sm" onClick={excluir} disabled={saving} style={{ marginRight: "auto" }}>Excluir</button>}
          <button className="btn btn-secondary" onClick={onClose} disabled={saving}>Cancelar</button>
          <button className="btn btn-primary" onClick={salvar} disabled={saving}>
            {saving ? "Salvando…" : isEdit ? "Salvar alterações" : "Cadastrar professor"}
          </button>
        </div>
      </div>
    </div>
  );
}

export function NovoProfessorBtn() {
  const router = useRouter();
  const [open, setOpen] = useState(false);
  return (
    <>
      <button className="btn btn-primary" onClick={() => setOpen(true)}>
        <svg viewBox="0 0 20 20" fill="currentColor"><path fillRule="evenodd" d="M10 3a1 1 0 011 1v5h5a1 1 0 110 2h-5v5a1 1 0 11-2 0v-5H4a1 1 0 110-2h5V4a1 1 0 011-1z" clipRule="evenodd" /></svg>
        Novo professor
      </button>
      {open && (
        <ProfessorModal
          onClose={() => setOpen(false)}
          onSaved={() => { setOpen(false); router.refresh(); }}
        />
      )}
    </>
  );
}

export function EditarProfessorBtn({ professor }: { professor: ProfessorData }) {
  const router = useRouter();
  const [open, setOpen] = useState(false);
  return (
    <>
      <button className="btn btn-ghost btn-sm btn-icon" title="Editar" onClick={() => setOpen(true)}>
        <svg viewBox="0 0 20 20" fill="currentColor"><path d="M13.586 3.586a2 2 0 112.828 2.828l-.793.793-2.828-2.828.793-.793zM11.379 5.793L3 14.172V17h2.828l8.38-8.379-2.83-2.828z" /></svg>
      </button>
      {open && (
        <ProfessorModal
          professor={professor}
          onClose={() => setOpen(false)}
          onSaved={() => { setOpen(false); router.refresh(); }}
        />
      )}
    </>
  );
}
