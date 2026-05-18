"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { ModalPortal } from "@/components/modal-portal";
import { text, type Homework } from "@/lib/school-modules";

function fmtDate(iso: string) {
  if (!iso) return "";
  const d = new Date(iso);
  return Number.isNaN(d.getTime()) ? iso : d.toLocaleDateString("pt-BR");
}

/* ── Delete individual ── */
export function HomeworkDeleteBtn({ licao }: { licao: Homework }) {
  const router = useRouter();
  const [saving, setSaving] = useState(false);

  async function excluir() {
    if (!confirm(`Excluir a lição "${text(licao.titulo)}"? Esta ação não pode ser desfeita.`)) return;
    setSaving(true);
    await fetch(`/api/licoes?id=${encodeURIComponent(text(licao.id))}`, { method: "DELETE" });
    setSaving(false);
    router.refresh();
  }

  return (
    <button className="btn btn-danger btn-sm" onClick={excluir} disabled={saving} title="Excluir lição">
      {saving ? "..." : "Excluir"}
    </button>
  );
}

/* ── Edit modal ── */
type EditForm = {
  titulo: string;
  descricao: string;
  turma: string;
  disciplina: string;
  due_date: string;
  status: string;
};

export function HomeworkEditBtn({ licao, turmas }: { licao: Homework; turmas: string[] }) {
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const [saving, setSaving] = useState(false);
  const [erro, setErro] = useState("");
  const [form, setForm] = useState<EditForm>({
    titulo: text(licao.titulo),
    descricao: text(licao.descricao),
    turma: text(licao.turma || "Todas"),
    disciplina: text(licao.disciplina || "Inglês"),
    due_date: text(licao.due_date),
    status: text(licao.status || "Ativa"),
  });

  function upd<K extends keyof EditForm>(k: K, v: EditForm[K]) {
    setForm((p) => ({ ...p, [k]: v }));
    setErro("");
  }

  async function salvar() {
    if (!form.titulo.trim()) { setErro("Título é obrigatório."); return; }
    setSaving(true);
    const res = await fetch("/api/licoes", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ id: text(licao.id), ...form }),
    });
    setSaving(false);
    if (!res.ok) {
      const d = await res.json().catch(() => ({}));
      setErro((d as { error?: string }).error || "Erro ao salvar.");
      return;
    }
    setOpen(false);
    router.refresh();
  }

  return (
    <>
      <button className="btn btn-secondary btn-sm" onClick={() => setOpen(true)}>Editar</button>
      {open && (
        <ModalPortal>
          <div className="modal-overlay" onClick={(e) => e.target === e.currentTarget && setOpen(false)}>
            <div className="modal-box" style={{ maxWidth: 620 }}>
              <div className="modal-header">
                <div className="modal-title">Editar lição de casa</div>
                <button className="modal-close" onClick={() => setOpen(false)}>
                  <svg viewBox="0 0 20 20" fill="currentColor"><path fillRule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clipRule="evenodd" /></svg>
                </button>
              </div>
              <div className="modal-body">
                <div className="form-grid">
                  <div className="form-group form-group-span2">
                    <label className="form-label">Título *</label>
                    <input className="form-input" value={form.titulo} onChange={(e) => upd("titulo", e.target.value)} autoFocus />
                  </div>
                  <div className="form-group form-group-span2">
                    <label className="form-label">Descrição / instruções</label>
                    <textarea className="form-input form-textarea" rows={3} value={form.descricao} onChange={(e) => upd("descricao", e.target.value)} />
                  </div>
                  <div className="form-group">
                    <label className="form-label">Turma</label>
                    <select className="form-input" value={form.turma} onChange={(e) => upd("turma", e.target.value)}>
                      <option value="Todas">Todas as turmas</option>
                      {turmas.map((t) => <option key={t} value={t}>{t}</option>)}
                    </select>
                  </div>
                  <div className="form-group">
                    <label className="form-label">Disciplina</label>
                    <input className="form-input" value={form.disciplina} onChange={(e) => upd("disciplina", e.target.value)} />
                  </div>
                  <div className="form-group">
                    <label className="form-label">Prazo (data)</label>
                    <input className="form-input" type="date" value={form.due_date} onChange={(e) => upd("due_date", e.target.value)} />
                  </div>
                  <div className="form-group">
                    <label className="form-label">Status</label>
                    <select className="form-input" value={form.status} onChange={(e) => upd("status", e.target.value)}>
                      <option>Ativa</option>
                      <option>Rascunho</option>
                      <option>Encerrada</option>
                    </select>
                  </div>
                </div>
                {erro && <div className="form-error" style={{ marginTop: 8 }}>{erro}</div>}
              </div>
              <div className="modal-footer">
                <button className="btn btn-secondary" onClick={() => setOpen(false)} disabled={saving}>Cancelar</button>
                <button className="btn btn-primary" onClick={salvar} disabled={saving}>{saving ? "Salvando..." : "Salvar alterações"}</button>
              </div>
            </div>
          </div>
        </ModalPortal>
      )}
    </>
  );
}

/* ── Delete all published today ── */
export function HomeworkDeleteTodayBtn({ todayCount }: { todayCount: number }) {
  const router = useRouter();
  const [saving, setSaving] = useState(false);
  const [msg, setMsg] = useState("");

  async function excluirHoje() {
    if (todayCount === 0) { setMsg("Não há lições publicadas hoje para excluir."); return; }
    if (!confirm(`Excluir TODAS as ${todayCount} lições publicadas hoje? Esta ação não pode ser desfeita.`)) return;
    setSaving(true);
    const res = await fetch("/api/licoes?bulk=today", { method: "DELETE" });
    const data = await res.json().catch(() => ({}));
    setSaving(false);
    if (!res.ok) { setMsg((data as { error?: string }).error || "Erro ao excluir."); return; }
    setMsg(`${(data as { deleted?: number }).deleted || 0} lições excluídas com sucesso.`);
    router.refresh();
  }

  return (
    <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
      <button
        className="btn btn-danger btn-sm"
        onClick={excluirHoje}
        disabled={saving || todayCount === 0}
        title={todayCount === 0 ? "Nenhuma lição publicada hoje" : `Excluir ${todayCount} lições de hoje`}
      >
        {saving ? "Excluindo..." : `Excluir todas de hoje${todayCount > 0 ? ` (${todayCount})` : ""}`}
      </button>
      {msg && <span style={{ fontSize: "0.8125rem", color: msg.includes("sucesso") ? "var(--green-700)" : "var(--red-600)" }}>{msg}</span>}
    </div>
  );
}
