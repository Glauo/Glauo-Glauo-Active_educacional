"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";

type LivroData = { id?: string; titulo?: string; title?: string; autor?: string; author?: string; nivel?: string; turma?: string; url?: string; tipo?: string; [k: string]: unknown };
type VideoData = { id?: string; titulo?: string; title?: string; turma?: string; url?: string; descricao?: string; [k: string]: unknown };

/* ─── Modal Livro ─── */
function LivroModal({ livro, onClose, onSaved }: { livro?: LivroData; onClose: () => void; onSaved: () => void }) {
  const isEdit = Boolean(livro?.id);
  const [form, setForm] = useState({
    titulo: String(livro?.titulo || livro?.title || ""),
    autor: String(livro?.autor || livro?.author || ""),
    nivel: String(livro?.nivel || ""),
    turma: String(livro?.turma || "Todas"),
    url: String(livro?.url || ""),
  });
  const [saving, setSaving] = useState(false);
  const [erro, setErro] = useState("");

  function update(field: keyof typeof form, value: string) { setForm((p) => ({ ...p, [field]: value })); setErro(""); }

  async function excluir() {
    if (!confirm(`Excluir o livro "${livro?.titulo}"? Esta ação não pode ser desfeita.`)) return;
    setSaving(true);
    await fetch(`/api/biblioteca?tipo=livros&id=${livro!.id}`, { method: "DELETE" });
    setSaving(false);
    onSaved();
  }

  async function salvar() {
    if (!form.titulo.trim()) { setErro("O título é obrigatório."); return; }
    setSaving(true);
    const payload = isEdit ? { id: livro!.id, ...form } : form;
    const res = await fetch("/api/biblioteca?tipo=livros", {
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
            <div className="modal-title">{isEdit ? "Editar livro" : "Adicionar livro"}</div>
            {isEdit && <div className="modal-subtitle">{livro?.titulo}</div>}
          </div>
          <button className="modal-close" onClick={onClose}>
            <svg viewBox="0 0 20 20" fill="currentColor"><path fillRule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clipRule="evenodd" /></svg>
          </button>
        </div>
        <div className="modal-body">
          <div className="form-grid">
            <div className="form-group form-group-span2">
              <label className="form-label">Título *</label>
              <input className="form-input" placeholder="Título do livro didático" value={form.titulo} onChange={(e) => update("titulo", e.target.value)} autoFocus />
            </div>
            <div className="form-group">
              <label className="form-label">Autor</label>
              <input className="form-input" placeholder="Nome do autor" value={form.autor} onChange={(e) => update("autor", e.target.value)} />
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
              <label className="form-label">Turma</label>
              <input className="form-input" placeholder="Ex: Turma A (ou 'Todas')" value={form.turma} onChange={(e) => update("turma", e.target.value)} />
            </div>
            <div className="form-group form-group-span2">
              <label className="form-label">Link / URL do PDF</label>
              <input className="form-input" type="url" placeholder="https://..." value={form.url} onChange={(e) => update("url", e.target.value)} />
              <span className="form-hint">Cole o link do Google Drive, Dropbox ou servidor</span>
            </div>
          </div>
          {erro && <div className="form-error">{erro}</div>}
        </div>
        <div className="modal-footer">
          {isEdit && <button className="btn btn-danger btn-sm" onClick={excluir} disabled={saving} style={{ marginRight: "auto" }}>Excluir</button>}
          <button className="btn btn-secondary" onClick={onClose} disabled={saving}>Cancelar</button>
          <button className="btn btn-primary" onClick={salvar} disabled={saving}>
            {saving ? "Salvando…" : isEdit ? "Salvar alterações" : "Adicionar livro"}
          </button>
        </div>
      </div>
    </div>
  );
}

/* ─── Modal Vídeo ─── */
function VideoModal({ onClose, onSaved }: { onClose: () => void; onSaved: () => void }) {
  const [form, setForm] = useState({ titulo: "", url: "", turma: "", descricao: "" });
  const [saving, setSaving] = useState(false);
  const [erro, setErro] = useState("");

  function update(field: keyof typeof form, value: string) { setForm((p) => ({ ...p, [field]: value })); setErro(""); }

  async function salvar() {
    if (!form.titulo.trim()) { setErro("O título é obrigatório."); return; }
    if (!form.url.trim()) { setErro("O link do vídeo é obrigatório."); return; }
    setSaving(true);
    const res = await fetch("/api/biblioteca?tipo=videos", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(form),
    });
    setSaving(false);
    if (!res.ok) { const d = await res.json().catch(() => ({})); setErro((d as {error?:string}).error || "Erro ao salvar."); return; }
    onSaved();
  }

  return (
    <div className="modal-overlay" onClick={(e) => e.target === e.currentTarget && onClose()}>
      <div className="modal-box">
        <div className="modal-header">
          <div className="modal-title">Adicionar vídeo / aula gravada</div>
          <button className="modal-close" onClick={onClose}>
            <svg viewBox="0 0 20 20" fill="currentColor"><path fillRule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clipRule="evenodd" /></svg>
          </button>
        </div>
        <div className="modal-body">
          <div className="form-grid">
            <div className="form-group form-group-span2">
              <label className="form-label">Título *</label>
              <input className="form-input" placeholder="Ex: Aula 12 — Present Perfect" value={form.titulo} onChange={(e) => update("titulo", e.target.value)} autoFocus />
            </div>
            <div className="form-group form-group-span2">
              <label className="form-label">Link do vídeo *</label>
              <input className="form-input" type="url" placeholder="https://youtube.com/... ou link do Drive" value={form.url} onChange={(e) => update("url", e.target.value)} />
            </div>
            <div className="form-group">
              <label className="form-label">Turma</label>
              <input className="form-input" placeholder="Ex: Turma B" value={form.turma} onChange={(e) => update("turma", e.target.value)} />
            </div>
            <div className="form-group form-group-span2">
              <label className="form-label">Descrição</label>
              <textarea className="form-input form-textarea" rows={2} placeholder="Breve descrição do conteúdo..." value={form.descricao} onChange={(e) => update("descricao", e.target.value)} />
            </div>
          </div>
          {erro && <div className="form-error">{erro}</div>}
        </div>
        <div className="modal-footer">
          <button className="btn btn-secondary" onClick={onClose} disabled={saving}>Cancelar</button>
          <button className="btn btn-primary" onClick={salvar} disabled={saving}>{saving ? "Salvando…" : "Adicionar vídeo"}</button>
        </div>
      </div>
    </div>
  );
}

export function AdicionarLivroBtn({ livro }: { livro?: LivroData } = {}) {
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const isEdit = Boolean(livro?.id);
  return (
    <>
      {isEdit
        ? <button className="btn btn-secondary btn-sm" style={{ flex: 1 }} onClick={() => setOpen(true)}>Editar</button>
        : <button className="btn btn-primary" onClick={() => setOpen(true)}>
            <svg viewBox="0 0 20 20" fill="currentColor"><path fillRule="evenodd" d="M10 3a1 1 0 011 1v5h5a1 1 0 110 2h-5v5a1 1 0 11-2 0v-5H4a1 1 0 110-2h5V4a1 1 0 011-1z" clipRule="evenodd" /></svg>
            Adicionar livro
          </button>
      }
      {open && <LivroModal livro={livro} onClose={() => setOpen(false)} onSaved={() => { setOpen(false); router.refresh(); }} />}
    </>
  );
}

export function AdicionarVideoBtn() {
  const router = useRouter();
  const [open, setOpen] = useState(false);
  return (
    <>
      <button className="btn btn-secondary btn-sm" onClick={() => setOpen(true)}>+ Vídeo</button>
      {open && <VideoModal onClose={() => setOpen(false)} onSaved={() => { setOpen(false); router.refresh(); }} />}
    </>
  );
}

// Keep type available for external usage
export type { LivroData, VideoData };
