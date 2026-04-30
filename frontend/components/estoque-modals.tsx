"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";

type ItemEstoque = { id?: string; nome?: string; name?: string; categoria?: string; quantidade?: number | string; [k: string]: unknown };

/* ─── Modal de Entrada / Saída ─── */
function MovimentoModal({ itens, onClose, onSaved }: { itens: ItemEstoque[]; onClose: () => void; onSaved: () => void }) {
  const [itemId, setItemId] = useState(itens[0]?.id || "");
  const [tipo, setTipo] = useState<"entrada" | "saida">("entrada");
  const [quantidade, setQuantidade] = useState("");
  const [observacao, setObservacao] = useState("");
  const [saving, setSaving] = useState(false);
  const [erro, setErro] = useState("");

  const itemSelecionado = itens.find((i) => String(i.id) === itemId);

  async function salvar() {
    if (!itemId) { setErro("Selecione um item."); return; }
    if (!quantidade || isNaN(Number(quantidade)) || Number(quantidade) <= 0) { setErro("Informe uma quantidade válida."); return; }
    setSaving(true);
    const res = await fetch("/api/estoque?tipo=movimentos", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ item: itemId, tipo, quantidade: Number(quantidade), observacao, data: new Date().toISOString() }),
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
            <div className="modal-title">Lançar movimentação</div>
            <div className="modal-subtitle">Registre entrada ou saída de material</div>
          </div>
          <button className="modal-close" onClick={onClose}>
            <svg viewBox="0 0 20 20" fill="currentColor"><path fillRule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clipRule="evenodd" /></svg>
          </button>
        </div>
        <div className="modal-body">
          <div className="form-grid">
            <div className="form-group form-group-span2">
              <label className="form-label">Tipo de movimentação</label>
              <div style={{ display: "flex", gap: "8px" }}>
                {(["entrada", "saida"] as const).map((t) => (
                  <button key={t} type="button" onClick={() => setTipo(t)} style={{
                    flex: 1, padding: "10px", borderRadius: "var(--radius-md)",
                    border: `2px solid ${tipo === t ? (t === "entrada" ? "var(--green-600)" : "var(--red-600)") : "var(--border)"}`,
                    background: tipo === t ? (t === "entrada" ? "rgba(34,197,94,0.06)" : "rgba(239,68,68,0.06)") : "transparent",
                    color: tipo === t ? (t === "entrada" ? "var(--green-700)" : "var(--red-700)") : "var(--text-muted)",
                    fontWeight: 600, fontSize: "0.875rem", cursor: "pointer", transition: "all 0.15s"
                  }}>
                    {t === "entrada" ? "↑ Entrada" : "↓ Saída"}
                  </button>
                ))}
              </div>
            </div>
            <div className="form-group form-group-span2">
              <label className="form-label">Item *</label>
              {itens.length === 0 ? (
                <p style={{ color: "var(--text-muted)", fontSize: "0.875rem" }}>Nenhum item cadastrado no estoque.</p>
              ) : (
                <select className="form-input" value={itemId} onChange={(e) => setItemId(e.target.value)}>
                  {itens.map((i) => (
                    <option key={String(i.id)} value={String(i.id)}>
                      {String(i.nome || i.name || i.id)} — estoque atual: {Number(i.quantidade) || 0}
                    </option>
                  ))}
                </select>
              )}
            </div>
            {itemSelecionado && tipo === "saida" && (
              <div className="form-group form-group-span2">
                <div style={{ background: "rgba(239,68,68,0.06)", border: "1px solid rgba(239,68,68,0.2)", borderRadius: "var(--radius-md)", padding: "10px 14px", fontSize: "0.875rem", color: "var(--red-700)" }}>
                  Estoque atual: <strong>{Number(itemSelecionado.quantidade) || 0} unidades</strong>
                </div>
              </div>
            )}
            <div className="form-group">
              <label className="form-label">Quantidade *</label>
              <input className="form-input" type="number" min="1" placeholder="0" value={quantidade} onChange={(e) => { setQuantidade(e.target.value); setErro(""); }} />
            </div>
            <div className="form-group">
              <label className="form-label">Observação</label>
              <input className="form-input" placeholder="Ex: Entrega para Turma A" value={observacao} onChange={(e) => setObservacao(e.target.value)} />
            </div>
          </div>
          {erro && <div className="form-error">{erro}</div>}
        </div>
        <div className="modal-footer">
          <button className="btn btn-secondary" onClick={onClose} disabled={saving}>Cancelar</button>
          <button className="btn btn-primary" onClick={salvar} disabled={saving || itens.length === 0}>
            {saving ? "Registrando…" : "Registrar movimentação"}
          </button>
        </div>
      </div>
    </div>
  );
}

/* ─── Modal Novo Item de Estoque ─── */
function NovoItemModal({ onClose, onSaved }: { onClose: () => void; onSaved: () => void }) {
  const [form, setForm] = useState({ nome: "", categoria: "", quantidade: "0", quantidade_minima: "0", preco: "" });
  const [saving, setSaving] = useState(false);
  const [erro, setErro] = useState("");

  function update(field: keyof typeof form, value: string) { setForm((p) => ({ ...p, [field]: value })); setErro(""); }

  async function salvar() {
    if (!form.nome.trim()) { setErro("O nome do item é obrigatório."); return; }
    setSaving(true);
    const res = await fetch("/api/estoque", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ ...form, quantidade: Number(form.quantidade), quantidade_minima: Number(form.quantidade_minima) }),
    });
    setSaving(false);
    if (!res.ok) { const d = await res.json().catch(() => ({})); setErro((d as {error?:string}).error || "Erro ao salvar."); return; }
    onSaved();
  }

  return (
    <div className="modal-overlay" onClick={(e) => e.target === e.currentTarget && onClose()}>
      <div className="modal-box">
        <div className="modal-header">
          <div className="modal-title">Novo item de estoque</div>
          <button className="modal-close" onClick={onClose}>
            <svg viewBox="0 0 20 20" fill="currentColor"><path fillRule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clipRule="evenodd" /></svg>
          </button>
        </div>
        <div className="modal-body">
          <div className="form-grid">
            <div className="form-group form-group-span2">
              <label className="form-label">Nome do item *</label>
              <input className="form-input" placeholder="Ex: Apostila Nível A1, Caneta azul..." value={form.nome} onChange={(e) => update("nome", e.target.value)} autoFocus />
            </div>
            <div className="form-group form-group-span2">
              <label className="form-label">Categoria</label>
              <input className="form-input" placeholder="Ex: Material didático, Papelaria..." value={form.categoria} onChange={(e) => update("categoria", e.target.value)} />
            </div>
            <div className="form-group">
              <label className="form-label">Quantidade inicial</label>
              <input className="form-input" type="number" min="0" value={form.quantidade} onChange={(e) => update("quantidade", e.target.value)} />
            </div>
            <div className="form-group">
              <label className="form-label">Estoque mínimo</label>
              <input className="form-input" type="number" min="0" value={form.quantidade_minima} onChange={(e) => update("quantidade_minima", e.target.value)} />
              <span className="form-hint">Alerta quando abaixo deste valor</span>
            </div>
            <div className="form-group">
              <label className="form-label">Preço unitário (R$)</label>
              <input className="form-input" placeholder="0,00" value={form.preco} onChange={(e) => update("preco", e.target.value)} />
            </div>
          </div>
          {erro && <div className="form-error">{erro}</div>}
        </div>
        <div className="modal-footer">
          <button className="btn btn-secondary" onClick={onClose} disabled={saving}>Cancelar</button>
          <button className="btn btn-primary" onClick={salvar} disabled={saving}>{saving ? "Salvando…" : "Cadastrar item"}</button>
        </div>
      </div>
    </div>
  );
}

export function LancarEntradaBtn({ itens }: { itens: ItemEstoque[] }) {
  const router = useRouter();
  const [open, setOpen] = useState(false);
  return (
    <>
      <button className="btn btn-primary" onClick={() => setOpen(true)}>
        <svg viewBox="0 0 20 20" fill="currentColor"><path fillRule="evenodd" d="M10 3a1 1 0 011 1v5h5a1 1 0 110 2h-5v5a1 1 0 11-2 0v-5H4a1 1 0 110-2h5V4a1 1 0 011-1z" clipRule="evenodd" /></svg>
        Lançar entrada
      </button>
      {open && <MovimentoModal itens={itens} onClose={() => setOpen(false)} onSaved={() => { setOpen(false); router.refresh(); }} />}
    </>
  );
}

export function NovoItemEstoqueBtn() {
  const router = useRouter();
  const [open, setOpen] = useState(false);
  return (
    <>
      <button className="btn btn-secondary" onClick={() => setOpen(true)}>
        <svg viewBox="0 0 20 20" fill="currentColor"><path fillRule="evenodd" d="M10 3a1 1 0 011 1v5h5a1 1 0 110 2h-5v5a1 1 0 11-2 0v-5H4a1 1 0 110-2h5V4a1 1 0 011-1z" clipRule="evenodd" /></svg>
        Novo item
      </button>
      {open && <NovoItemModal onClose={() => setOpen(false)} onSaved={() => { setOpen(false); router.refresh(); }} />}
    </>
  );
}
