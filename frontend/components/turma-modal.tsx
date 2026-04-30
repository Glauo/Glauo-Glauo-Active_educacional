"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";

type TurmaData = {
  id?: string;
  nome?: string;
  nivel?: string;
  professor?: string;
  livro?: string;
  horario?: string;
  dia_semana?: string;
  sala?: string;
  status?: string;
  [k: string]: unknown;
};

type Form = {
  nome: string;
  nivel: string;
  professor: string;
  livro: string;
  horario: string;
  dia_semana: string;
  sala: string;
  status: string;
};

function fromTurma(t?: TurmaData): Form {
  return {
    nome: String(t?.nome || ""),
    nivel: String(t?.nivel || ""),
    professor: String(t?.professor || ""),
    livro: String(t?.livro || ""),
    horario: String(t?.horario || ""),
    dia_semana: String(t?.dia_semana || ""),
    sala: String(t?.sala || ""),
    status: String(t?.status || "Ativa")
  };
}

function TurmaModal({
  turma,
  onClose,
  onSaved
}: {
  turma?: TurmaData;
  onClose: () => void;
  onSaved: () => void;
}) {
  const isEdit = Boolean(turma?.id);
  const [form, setForm] = useState<Form>(fromTurma(turma));
  const [saving, setSaving] = useState(false);
  const [erro, setErro] = useState("");

  function update(field: keyof Form, value: string) {
    setForm((prev) => ({ ...prev, [field]: value }));
    setErro("");
  }

  async function excluir() {
    if (!confirm(`Excluir a turma "${turma?.nome}"? Esta ação não pode ser desfeita.`)) return;
    setSaving(true);
    await fetch(`/api/turmas?id=${turma!.id}`, { method: "DELETE" });
    setSaving(false);
    onSaved();
  }

  async function salvar() {
    if (!form.nome.trim()) {
      setErro("O nome da turma é obrigatório.");
      return;
    }
    setSaving(true);
    const payload = isEdit ? { id: turma!.id, ...form } : form;
    const res = await fetch("/api/turmas", {
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
            <div className="modal-title">{isEdit ? "Editar turma" : "Nova turma"}</div>
            {isEdit && <div className="modal-subtitle">{turma?.nome}</div>}
          </div>
          <button className="modal-close" onClick={onClose}>
            <svg viewBox="0 0 20 20" fill="currentColor"><path fillRule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clipRule="evenodd" /></svg>
          </button>
        </div>

        <div className="modal-body">
          <div className="form-grid">
            <div className="form-group form-group-span2">
              <label className="form-label">Nome da turma *</label>
              <input
                className="form-input"
                placeholder="Ex: Turma Básico A — Noite"
                value={form.nome}
                onChange={(e) => update("nome", e.target.value)}
                autoFocus
              />
            </div>
            <div className="form-group">
              <label className="form-label">Nível</label>
              <select className="form-input" value={form.nivel} onChange={(e) => update("nivel", e.target.value)}>
                <option value="">Selecione…</option>
                <option>Básico</option>
                <option>Básico Avançado</option>
                <option>Intermediário</option>
                <option>Upper Intermediate</option>
                <option>Avançado</option>
                <option>Conversação</option>
                <option>Preparatório</option>
              </select>
            </div>
            <div className="form-group">
              <label className="form-label">Professor</label>
              <input className="form-input" placeholder="Nome do professor" value={form.professor} onChange={(e) => update("professor", e.target.value)} />
            </div>
            <div className="form-group">
              <label className="form-label">Livro</label>
              <input className="form-input" placeholder="Livro didático" value={form.livro} onChange={(e) => update("livro", e.target.value)} />
            </div>
            <div className="form-group">
              <label className="form-label">Dia(s) da semana</label>
              <input className="form-input" placeholder="Ex: Seg, Qua, Sex" value={form.dia_semana} onChange={(e) => update("dia_semana", e.target.value)} />
            </div>
            <div className="form-group">
              <label className="form-label">Horário</label>
              <input className="form-input" placeholder="Ex: 19h00 – 20h30" value={form.horario} onChange={(e) => update("horario", e.target.value)} />
            </div>
            <div className="form-group">
              <label className="form-label">Sala</label>
              <input className="form-input" placeholder="Ex: Sala 3" value={form.sala} onChange={(e) => update("sala", e.target.value)} />
            </div>
            <div className="form-group">
              <label className="form-label">Status</label>
              <select className="form-input" value={form.status} onChange={(e) => update("status", e.target.value)}>
                <option>Ativa</option>
                <option>Em atenção</option>
                <option>Inativa</option>
              </select>
            </div>
          </div>
          {erro && <div className="form-error">{erro}</div>}
        </div>

        <div className="modal-footer">
          {isEdit && <button className="btn btn-danger btn-sm" onClick={excluir} disabled={saving} style={{ marginRight: "auto" }}>Excluir</button>}
          <button className="btn btn-secondary" onClick={onClose} disabled={saving}>Cancelar</button>
          <button className="btn btn-primary" onClick={salvar} disabled={saving}>
            {saving ? "Salvando…" : isEdit ? "Salvar alterações" : "Criar turma"}
          </button>
        </div>
      </div>
    </div>
  );
}

export function NovaTurmaBtn() {
  const router = useRouter();
  const [open, setOpen] = useState(false);
  return (
    <>
      <button className="btn btn-primary" onClick={() => setOpen(true)}>
        <svg viewBox="0 0 20 20" fill="currentColor"><path fillRule="evenodd" d="M10 3a1 1 0 011 1v5h5a1 1 0 110 2h-5v5a1 1 0 11-2 0v-5H4a1 1 0 110-2h5V4a1 1 0 011-1z" clipRule="evenodd" /></svg>
        Nova turma
      </button>
      {open && (
        <TurmaModal
          onClose={() => setOpen(false)}
          onSaved={() => { setOpen(false); router.refresh(); }}
        />
      )}
    </>
  );
}

export function EditarTurmaBtn({ turma }: { turma: TurmaData }) {
  const router = useRouter();
  const [open, setOpen] = useState(false);
  return (
    <>
      <button className="btn btn-ghost btn-sm" onClick={() => setOpen(true)}>Editar</button>
      {open && (
        <TurmaModal
          turma={turma}
          onClose={() => setOpen(false)}
          onSaved={() => { setOpen(false); router.refresh(); }}
        />
      )}
    </>
  );
}
