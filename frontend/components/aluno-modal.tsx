"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";

type AlunoData = {
  id?: string;
  nome?: string;
  turma?: string;
  livro?: string;
  responsavel?: string;
  telefone?: string;
  email?: string;
  status?: string;
  [k: string]: unknown;
};

type Form = {
  nome: string;
  turma: string;
  livro: string;
  responsavel: string;
  telefone: string;
  email: string;
  status: string;
};

function fromAluno(a?: AlunoData): Form {
  return {
    nome: String(a?.nome || ""),
    turma: String(a?.turma || ""),
    livro: String(a?.livro || ""),
    responsavel: String(a?.responsavel || ""),
    telefone: String(a?.telefone || ""),
    email: String(a?.email || ""),
    status: String(a?.status || "Ativo")
  };
}

function AlunoModal({
  aluno,
  onClose,
  onSaved
}: {
  aluno?: AlunoData;
  onClose: () => void;
  onSaved: () => void;
}) {
  const isEdit = Boolean(aluno?.id);
  const [form, setForm] = useState<Form>(fromAluno(aluno));
  const [saving, setSaving] = useState(false);
  const [erro, setErro] = useState("");

  function update(field: keyof Form, value: string) {
    setForm((prev) => ({ ...prev, [field]: value }));
    setErro("");
  }

  async function excluir() {
    if (!confirm(`Excluir o aluno "${aluno?.nome}"? Esta ação não pode ser desfeita.`)) return;
    setSaving(true);
    await fetch(`/api/alunos?id=${aluno!.id}`, { method: "DELETE" });
    setSaving(false);
    onSaved();
  }

  async function salvar() {
    if (!form.nome.trim()) {
      setErro("O nome do aluno é obrigatório.");
      return;
    }
    setSaving(true);
    const payload = isEdit ? { id: aluno!.id, ...form } : form;
    const res = await fetch("/api/alunos", {
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
            <div className="modal-title">{isEdit ? "Editar aluno" : "Novo aluno"}</div>
            {isEdit && <div className="modal-subtitle">{aluno?.nome}</div>}
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
                placeholder="Nome do aluno"
                value={form.nome}
                onChange={(e) => update("nome", e.target.value)}
                autoFocus
              />
            </div>
            <div className="form-group">
              <label className="form-label">Turma</label>
              <input className="form-input" placeholder="Ex: Turma A" value={form.turma} onChange={(e) => update("turma", e.target.value)} />
            </div>
            <div className="form-group">
              <label className="form-label">Livro</label>
              <input className="form-input" placeholder="Livro didático" value={form.livro} onChange={(e) => update("livro", e.target.value)} />
            </div>
            <div className="form-group">
              <label className="form-label">Responsável</label>
              <input className="form-input" placeholder="Nome do responsável" value={form.responsavel} onChange={(e) => update("responsavel", e.target.value)} />
            </div>
            <div className="form-group">
              <label className="form-label">Telefone</label>
              <input className="form-input" placeholder="(11) 99999-0000" value={form.telefone} onChange={(e) => update("telefone", e.target.value)} />
            </div>
            <div className="form-group form-group-span2">
              <label className="form-label">E-mail</label>
              <input className="form-input" type="email" placeholder="email@exemplo.com" value={form.email} onChange={(e) => update("email", e.target.value)} />
            </div>
            <div className="form-group">
              <label className="form-label">Status</label>
              <select className="form-input" value={form.status} onChange={(e) => update("status", e.target.value)}>
                <option>Ativo</option>
                <option>Inativo</option>
                <option>Em atenção</option>
              </select>
            </div>
          </div>
          {erro && <div className="form-error">{erro}</div>}
        </div>

        <div className="modal-footer">
          {isEdit && <button className="btn btn-danger btn-sm" onClick={excluir} disabled={saving} style={{ marginRight: "auto" }}>Excluir</button>}
          <button className="btn btn-secondary" onClick={onClose} disabled={saving}>Cancelar</button>
          <button className="btn btn-primary" onClick={salvar} disabled={saving}>
            {saving ? "Salvando…" : isEdit ? "Salvar alterações" : "Cadastrar aluno"}
          </button>
        </div>
      </div>
    </div>
  );
}

export function NovoAlunoBtn() {
  const router = useRouter();
  const [open, setOpen] = useState(false);
  return (
    <>
      <button className="btn btn-primary" onClick={() => setOpen(true)}>
        <svg viewBox="0 0 20 20" fill="currentColor"><path fillRule="evenodd" d="M10 3a1 1 0 011 1v5h5a1 1 0 110 2h-5v5a1 1 0 11-2 0v-5H4a1 1 0 110-2h5V4a1 1 0 011-1z" clipRule="evenodd" /></svg>
        Novo aluno
      </button>
      {open && (
        <AlunoModal
          onClose={() => setOpen(false)}
          onSaved={() => { setOpen(false); router.refresh(); }}
        />
      )}
    </>
  );
}

export function EditarAlunoBtn({ aluno }: { aluno: AlunoData }) {
  const router = useRouter();
  const [open, setOpen] = useState(false);
  return (
    <>
      <button className="btn btn-ghost btn-sm btn-icon" title="Editar" onClick={() => setOpen(true)}>
        <svg viewBox="0 0 20 20" fill="currentColor"><path d="M13.586 3.586a2 2 0 112.828 2.828l-.793.793-2.828-2.828.793-.793zM11.379 5.793L3 14.172V17h2.828l8.38-8.379-2.83-2.828z" /></svg>
      </button>
      {open && (
        <AlunoModal
          aluno={aluno}
          onClose={() => setOpen(false)}
          onSaved={() => { setOpen(false); router.refresh(); }}
        />
      )}
    </>
  );
}
