"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";

type DesafioData = {
  id?: string;
  titulo?: string;
  title?: string;
  turma?: string;
  descricao?: string;
  pontos?: number | string;
  status?: string;
  [k: string]: unknown;
};

type Form = {
  titulo: string;
  turma: string;
  pontos: string;
  descricao: string;
  status: string;
};

function fromDesafio(d?: DesafioData): Form {
  return {
    titulo: String(d?.titulo || d?.title || ""),
    turma: String(d?.turma || "Todas"),
    pontos: String(d?.pontos || "10"),
    descricao: String(d?.descricao || ""),
    status: String(d?.status || "Publicado"),
  };
}

function DesafioModal({ desafio, onClose, onSaved }: { desafio?: DesafioData; onClose: () => void; onSaved: () => void }) {
  const isEdit = Boolean(desafio?.id);
  const [form, setForm] = useState<Form>(fromDesafio(desafio));
  const [saving, setSaving] = useState(false);
  const [erro, setErro] = useState("");

  function update(field: keyof Form, value: string) {
    setForm((p) => ({ ...p, [field]: value }));
    setErro("");
  }

  async function excluir() {
    if (!confirm(`Excluir o desafio "${desafio?.titulo}"? Esta ação não pode ser desfeita.`)) return;
    setSaving(true);
    await fetch(`/api/desafios?id=${desafio!.id}`, { method: "DELETE" });
    setSaving(false);
    onSaved();
  }

  async function salvar() {
    if (!form.titulo.trim()) { setErro("O título é obrigatório."); return; }
    if (!form.pontos || isNaN(Number(form.pontos))) { setErro("Informe um valor de pontos válido."); return; }
    setSaving(true);
    const payload = isEdit
      ? { id: desafio!.id, ...form, pontos: Number(form.pontos) }
      : { ...form, pontos: Number(form.pontos) };
    const res = await fetch("/api/desafios", {
      method: isEdit ? "PUT" : "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    setSaving(false);
    if (!res.ok) { const d = await res.json().catch(() => ({})); setErro((d as {error?:string}).error || "Erro ao salvar."); return; }
    onSaved();
  }

  return (
    <div className="modal-overlay" onClick={(e) => e.target === e.currentTarget && onClose()}>
      <div className="modal-box">
        <div className="modal-header">
          <div>
            <div className="modal-title">{isEdit ? "Editar desafio" : "Novo desafio"}</div>
            {isEdit && <div className="modal-subtitle">{desafio?.titulo}</div>}
          </div>
          <button className="modal-close" onClick={onClose}>
            <svg viewBox="0 0 20 20" fill="currentColor"><path fillRule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clipRule="evenodd" /></svg>
          </button>
        </div>
        <div className="modal-body">
          <div className="form-grid">
            <div className="form-group form-group-span2">
              <label className="form-label">Título do desafio *</label>
              <input className="form-input" placeholder="Ex: Revise o Capítulo 5 e responda as questões" value={form.titulo} onChange={(e) => update("titulo", e.target.value)} autoFocus />
            </div>
            <div className="form-group">
              <label className="form-label">Turma</label>
              <input className="form-input" placeholder="Ex: Turma A (ou 'Todas')" value={form.turma} onChange={(e) => update("turma", e.target.value)} />
            </div>
            <div className="form-group">
              <label className="form-label">Pontos</label>
              <input className="form-input" type="number" min="0" placeholder="10" value={form.pontos} onChange={(e) => update("pontos", e.target.value)} />
            </div>
            <div className="form-group form-group-span2">
              <label className="form-label">Descrição / Enunciado</label>
              <textarea className="form-input form-textarea" rows={4} placeholder="Descreva o desafio, as instruções e o que o aluno deve entregar..." value={form.descricao} onChange={(e) => update("descricao", e.target.value)} />
            </div>
            <div className="form-group">
              <label className="form-label">Status</label>
              <select className="form-input" value={form.status} onChange={(e) => update("status", e.target.value)}>
                <option>Publicado</option>
                <option>Rascunho</option>
                <option>Arquivado</option>
              </select>
            </div>
          </div>
          {erro && <div className="form-error">{erro}</div>}
        </div>
        <div className="modal-footer">
          {isEdit && <button className="btn btn-danger btn-sm" onClick={excluir} disabled={saving} style={{ marginRight: "auto" }}>Excluir</button>}
          <button className="btn btn-secondary" onClick={onClose} disabled={saving}>Cancelar</button>
          <button className="btn btn-primary" onClick={salvar} disabled={saving}>
            {saving ? "Salvando…" : isEdit ? "Salvar alterações" : "Publicar desafio"}
          </button>
        </div>
      </div>
    </div>
  );
}

export function NovoDesafioBtn() {
  const router = useRouter();
  const [open, setOpen] = useState(false);
  return (
    <>
      <button className="btn btn-primary" onClick={() => setOpen(true)}>
        <svg viewBox="0 0 20 20" fill="currentColor"><path fillRule="evenodd" d="M10 3a1 1 0 011 1v5h5a1 1 0 110 2h-5v5a1 1 0 11-2 0v-5H4a1 1 0 110-2h5V4a1 1 0 011-1z" clipRule="evenodd" /></svg>
        Novo desafio
      </button>
      {open && <DesafioModal onClose={() => setOpen(false)} onSaved={() => { setOpen(false); router.refresh(); }} />}
    </>
  );
}

export function EditarDesafioBtn({ desafio }: { desafio: DesafioData }) {
  const router = useRouter();
  const [open, setOpen] = useState(false);
  return (
    <>
      <button className="btn btn-ghost btn-sm" style={{ fontSize: "0.75rem" }} onClick={() => setOpen(true)}>Editar</button>
      {open && <DesafioModal desafio={desafio} onClose={() => setOpen(false)} onSaved={() => { setOpen(false); router.refresh(); }} />}
    </>
  );
}
