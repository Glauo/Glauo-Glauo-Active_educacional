"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";

type LancamentoData = {
  id?: string;
  aluno?: string;
  nome?: string;
  descricao?: string;
  valor?: number | string;
  vencimento?: string;
  data_vencimento?: string;
  status?: string;
  tipo_lancamento?: string;
  [k: string]: unknown;
};

type Form = {
  tipo_lancamento: "recebimentos" | "despesas";
  aluno: string;
  descricao: string;
  valor: string;
  vencimento: string;
  status: string;
};

const hoje = () => new Date().toISOString().slice(0, 10);

function LancamentoModal({
  lancamento,
  tipoInicial,
  onClose,
  onSaved
}: {
  lancamento?: LancamentoData;
  tipoInicial?: "recebimentos" | "despesas";
  onClose: () => void;
  onSaved: () => void;
}) {
  const isEdit = Boolean(lancamento?.id);
  const [form, setForm] = useState<Form>({
    tipo_lancamento: tipoInicial || (lancamento?.tipo_lancamento as "recebimentos" | "despesas") || "recebimentos",
    aluno: String(lancamento?.aluno || lancamento?.nome || ""),
    descricao: String(lancamento?.descricao || ""),
    valor: String(lancamento?.valor || ""),
    vencimento: String(lancamento?.vencimento || lancamento?.data_vencimento || hoje()),
    status: String(lancamento?.status || "Pendente")
  });
  const [saving, setSaving] = useState(false);
  const [erro, setErro] = useState("");

  function update<K extends keyof Form>(field: K, value: Form[K]) {
    setForm((prev) => ({ ...prev, [field]: value }));
    setErro("");
  }

  async function excluir() {
    if (!confirm("Excluir este lançamento? Esta ação não pode ser desfeita.")) return;
    setSaving(true);
    await fetch(`/api/financeiro?id=${lancamento!.id}&tipo=${form.tipo_lancamento}`, { method: "DELETE" });
    setSaving(false);
    onSaved();
  }

  async function salvar() {
    if (!form.valor || isNaN(parseFloat(form.valor.replace(",", ".")))) {
      setErro("Informe um valor válido.");
      return;
    }
    if (!form.vencimento) { setErro("Informe a data de vencimento."); return; }

    setSaving(true);
    const payload = isEdit
      ? { id: lancamento!.id, tipo: form.tipo_lancamento, aluno: form.aluno, descricao: form.descricao, valor: form.valor, vencimento: form.vencimento, status: form.status }
      : { tipo: form.tipo_lancamento, aluno: form.aluno, descricao: form.descricao, valor: form.valor, vencimento: form.vencimento, status: form.status };

    const res = await fetch(`/api/financeiro`, {
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

  const isRecebimento = form.tipo_lancamento === "recebimentos";

  return (
    <div className="modal-overlay" onClick={(e) => e.target === e.currentTarget && onClose()}>
      <div className="modal-box">
        <div className="modal-header">
          <div>
            <div className="modal-title">{isEdit ? "Editar lançamento" : "Novo lançamento"}</div>
            <div className="modal-subtitle">{isRecebimento ? "Recebimento / Mensalidade" : "Despesa / Custo"}</div>
          </div>
          <button className="modal-close" onClick={onClose}>
            <svg viewBox="0 0 20 20" fill="currentColor"><path fillRule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clipRule="evenodd" /></svg>
          </button>
        </div>
        <div className="modal-body">
          <div className="form-grid">
            {!isEdit && (
              <div className="form-group form-group-span2">
                <label className="form-label">Tipo de lançamento</label>
                <div style={{ display: "flex", gap: "8px" }}>
                  {(["recebimentos", "despesas"] as const).map((t) => (
                    <button
                      key={t}
                      type="button"
                      onClick={() => update("tipo_lancamento", t)}
                      style={{
                        flex: 1,
                        padding: "10px",
                        borderRadius: "var(--radius-md)",
                        border: `2px solid ${form.tipo_lancamento === t ? (t === "recebimentos" ? "var(--green-600)" : "var(--red-600)") : "var(--border)"}`,
                        background: form.tipo_lancamento === t ? (t === "recebimentos" ? "rgba(34,197,94,0.06)" : "rgba(239,68,68,0.06)") : "transparent",
                        color: form.tipo_lancamento === t ? (t === "recebimentos" ? "var(--green-700)" : "var(--red-700)") : "var(--text-muted)",
                        fontWeight: 600, fontSize: "0.875rem", cursor: "pointer", transition: "all 0.15s"
                      }}
                    >
                      {t === "recebimentos" ? "↑ Recebimento" : "↓ Despesa"}
                    </button>
                  ))}
                </div>
              </div>
            )}
            <div className="form-group form-group-span2">
              <label className="form-label">{isRecebimento ? "Aluno / Responsável" : "Fornecedor / Descrição"}</label>
              <input
                className="form-input"
                placeholder={isRecebimento ? "Nome do aluno" : "Ex: Aluguel, Salário..."}
                value={form.aluno}
                onChange={(e) => update("aluno", e.target.value)}
                autoFocus
              />
            </div>
            <div className="form-group form-group-span2">
              <label className="form-label">Descrição / Referência</label>
              <input className="form-input" placeholder="Ex: Mensalidade Janeiro/2026" value={form.descricao} onChange={(e) => update("descricao", e.target.value)} />
            </div>
            <div className="form-group">
              <label className="form-label">Valor (R$) *</label>
              <input
                className="form-input"
                placeholder="0,00"
                value={form.valor}
                onChange={(e) => update("valor", e.target.value)}
                inputMode="decimal"
              />
            </div>
            <div className="form-group">
              <label className="form-label">Vencimento *</label>
              <input className="form-input" type="date" value={form.vencimento} onChange={(e) => update("vencimento", e.target.value)} />
            </div>
            <div className="form-group form-group-span2">
              <label className="form-label">Status</label>
              <select className="form-input" value={form.status} onChange={(e) => update("status", e.target.value)}>
                <option>Pendente</option>
                <option>Pago</option>
                <option>Atrasado</option>
                <option>Boleto gerado</option>
                <option>Cancelado</option>
              </select>
            </div>
          </div>
          {erro && <div className="form-error">{erro}</div>}
        </div>
        <div className="modal-footer">
          {isEdit && <button className="btn btn-danger btn-sm" onClick={excluir} disabled={saving} style={{ marginRight: "auto" }}>Excluir</button>}
          <button className="btn btn-secondary" onClick={onClose} disabled={saving}>Cancelar</button>
          <button className="btn btn-primary" onClick={salvar} disabled={saving}>
            {saving ? "Salvando…" : isEdit ? "Salvar alterações" : "Criar lançamento"}
          </button>
        </div>
      </div>
    </div>
  );
}

export function NovoLancamentoBtn() {
  const router = useRouter();
  const [open, setOpen] = useState(false);
  return (
    <>
      <button className="btn btn-primary" onClick={() => setOpen(true)}>
        <svg viewBox="0 0 20 20" fill="currentColor"><path fillRule="evenodd" d="M10 3a1 1 0 011 1v5h5a1 1 0 110 2h-5v5a1 1 0 11-2 0v-5H4a1 1 0 110-2h5V4a1 1 0 011-1z" clipRule="evenodd" /></svg>
        Novo lançamento
      </button>
      {open && (
        <LancamentoModal
          onClose={() => setOpen(false)}
          onSaved={() => { setOpen(false); router.refresh(); }}
        />
      )}
    </>
  );
}

export function EditarLancamentoBtn({ lancamento, tipo }: { lancamento: LancamentoData; tipo: "recebimentos" | "despesas" }) {
  const router = useRouter();
  const [open, setOpen] = useState(false);
  return (
    <>
      <button className="btn btn-ghost btn-sm btn-icon" title="Editar" onClick={() => setOpen(true)}>
        <svg viewBox="0 0 20 20" fill="currentColor"><path d="M13.586 3.586a2 2 0 112.828 2.828l-.793.793-2.828-2.828.793-.793zM11.379 5.793L3 14.172V17h2.828l8.38-8.379-2.83-2.828z" /></svg>
      </button>
      {open && (
        <LancamentoModal
          lancamento={lancamento}
          tipoInicial={tipo}
          onClose={() => setOpen(false)}
          onSaved={() => { setOpen(false); router.refresh(); }}
        />
      )}
    </>
  );
}

export function BaixaBtn({ lancamento, tipo }: { lancamento: LancamentoData; tipo: "recebimentos" | "despesas" }) {
  const router = useRouter();
  const [loading, setLoading] = useState(false);
  const [aviso, setAviso] = useState(false);
  const [open, setOpen] = useState(false);
  const [form, setForm] = useState({
    valor_pago: String(lancamento.valor || ""),
    forma_pagamento: "PIX",
    data_baixa: hoje(),
    banco_destino: "",
    observacao_baixa: "",
  });
  const jaFoiBaixado = String(lancamento.status || "").toLowerCase().includes("pago") ||
    String(lancamento.status || "").toLowerCase().includes("baixado");

  if (jaFoiBaixado) return null;

  async function darBaixa() {
    setLoading(true);
    const res = await fetch("/api/financeiro", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        id: lancamento.id,
        tipo,
        status: "Pago",
        data_baixa: form.data_baixa,
        valor_pago: form.valor_pago,
        forma_pagamento: form.forma_pagamento,
        banco_destino: form.banco_destino,
        observacao_baixa: form.observacao_baixa,
      })
    });
    setLoading(false);
    if (!res.ok) {
      const data = await res.json().catch(() => ({}));
      alert(String(data.error || "Erro ao registrar baixa."));
      return;
    }
    setOpen(false);
    setAviso(true);
    setTimeout(() => setAviso(false), 3500);
    router.refresh();
  }

  return (
    <>
    <button
      className="btn btn-ghost btn-sm"
      style={{ fontSize: "0.75rem", color: "var(--green-700)" }}
      onClick={() => setOpen(true)}
      disabled={loading}
      title="Registrar pagamento"
    >
      {loading ? "..." : "Baixa"}
    </button>
    {aviso && <span className="badge badge-success"><span className="badge-dot" />Recibo automatico</span>}
    {open && (
      <div className="modal-overlay" onClick={(e) => e.target === e.currentTarget && setOpen(false)}>
        <div className="modal-box" style={{ maxWidth: 540 }}>
          <div className="modal-header">
            <div>
              <div className="modal-title">Registrar pagamento</div>
              <div className="modal-subtitle">Baixa com recibo automatico e log de auditoria</div>
            </div>
            <button className="modal-close" onClick={() => setOpen(false)}>
              <svg viewBox="0 0 20 20" fill="currentColor"><path fillRule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clipRule="evenodd" /></svg>
            </button>
          </div>
          <div className="modal-body">
            <div className="form-grid">
              <div className="form-group"><label className="form-label">Valor pago</label><input className="form-input" inputMode="decimal" value={form.valor_pago} onChange={(e) => setForm((p) => ({ ...p, valor_pago: e.target.value }))} /></div>
              <div className="form-group"><label className="form-label">Data do pagamento</label><input className="form-input" type="date" value={form.data_baixa} onChange={(e) => setForm((p) => ({ ...p, data_baixa: e.target.value }))} /></div>
              <div className="form-group"><label className="form-label">Forma</label><select className="form-input" value={form.forma_pagamento} onChange={(e) => setForm((p) => ({ ...p, forma_pagamento: e.target.value }))}><option>PIX</option><option>Boleto</option><option>Dinheiro</option><option>Cartao</option><option>TED</option><option>Cheque</option></select></div>
              <div className="form-group"><label className="form-label">Banco / conta</label><input className="form-input" value={form.banco_destino} onChange={(e) => setForm((p) => ({ ...p, banco_destino: e.target.value }))} /></div>
              <div className="form-group form-group-span2"><label className="form-label">Observacao</label><textarea className="form-input form-textarea" rows={3} value={form.observacao_baixa} onChange={(e) => setForm((p) => ({ ...p, observacao_baixa: e.target.value }))} /></div>
            </div>
          </div>
          <div className="modal-footer">
            <button className="btn btn-secondary" onClick={() => setOpen(false)} disabled={loading}>Cancelar</button>
            <button className="btn btn-primary" onClick={darBaixa} disabled={loading}>{loading ? "Salvando..." : "Confirmar baixa"}</button>
          </div>
        </div>
      </div>
    )}
    </>
  );
}

export function EstornoBtn({ lancamento, tipo }: { lancamento: LancamentoData; tipo: "recebimentos" | "despesas" }) {
  const router = useRouter();
  const [loading, setLoading] = useState(false);
  const pago = String(lancamento.status || "").toLowerCase().includes("pago") ||
    String(lancamento.status || "").toLowerCase().includes("baixado");
  if (!pago) return null;

  async function estornar() {
    const motivo = prompt("Motivo do estorno (obrigatorio):");
    if (!motivo?.trim()) return;
    setLoading(true);
    const res = await fetch("/api/financeiro", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ id: lancamento.id, tipo, estorno: true, estorno_motivo: motivo })
    });
    setLoading(false);
    if (!res.ok) {
      const data = await res.json().catch(() => ({}));
      alert(String(data.error || "Erro ao estornar."));
      return;
    }
    router.refresh();
  }

  return (
    <button className="btn btn-ghost btn-sm" style={{ fontSize: "0.72rem", color: "var(--red-700)" }} onClick={estornar} disabled={loading} title="Estornar baixa com auditoria">
      {loading ? "..." : "Estornar"}
    </button>
  );
}
