"use client";

import { useState, useMemo } from "react";
import { useRouter } from "next/navigation";

type Fornecedor = {
  id: string;
  nome: string;
  cpf_cnpj?: string;
  telefone?: string;
  email?: string;
  endereco?: string;
  categoria?: string;
  chave_pix?: string;
  banco?: string;
  observacoes?: string;
  created_at?: string;
  updated_at?: string;
};

type Despesa = {
  id?: string;
  aluno?: string;
  nome?: string;
  descricao?: string;
  valor?: number | string;
  vencimento?: string;
  data_vencimento?: string;
  status?: string;
  situacao?: string;
  fornecedor_id?: string;
  [k: string]: unknown;
};

const CATEGORIAS = [
  "Aluguel", "Água", "Energia", "Internet", "Material didático",
  "Limpeza", "Manutenção", "Marketing", "Serviços", "Outros"
];

const FORM_VAZIO = {
  nome: "", cpf_cnpj: "", telefone: "", email: "",
  endereco: "", categoria: "Outros", chave_pix: "", banco: "", observacoes: "",
};

function parseValor(v: unknown): number {
  return parseFloat(String(v || "0").replace(/[^\d.,]/g, "").replace(",", ".")) || 0;
}

function formatBRL(v: number): string {
  return v.toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
}

function parseBRDate(v: string): Date {
  if (!v) return new Date(NaN);
  const m = v.match(/^(\d{2})\/(\d{2})\/(\d{4})/);
  if (m) return new Date(Number(m[3]), Number(m[2]) - 1, Number(m[1]));
  return new Date(v);
}

function fmtDate(v: string) {
  if (!v) return v;
  if (/^\d{2}\/\d{2}\/\d{4}/.test(v)) return v.substring(0, 10);
  const d = parseBRDate(v);
  if (isNaN(d.getTime())) return v;
  return d.toLocaleDateString("pt-BR");
}

function statusBadge(s: string) {
  const l = s.toLowerCase();
  if (l.includes("pago") || l.includes("baixado") || l.includes("liquidado")) return "success";
  if (l.includes("atraso") || l.includes("vencido")) return "danger";
  return "warning";
}

function hoje() {
  return new Date().toISOString().slice(0, 10);
}

function FornecedorModal({
  fornecedor,
  onClose,
  onSaved,
}: {
  fornecedor?: Fornecedor;
  onClose: () => void;
  onSaved: () => void;
}) {
  const isEdit = Boolean(fornecedor?.id);
  const [form, setForm] = useState({ ...FORM_VAZIO, ...(fornecedor || {}) });
  const [saving, setSaving] = useState(false);
  const [erro, setErro] = useState("");

  function upd(k: string, v: string) {
    setForm((p) => ({ ...p, [k]: v }));
    setErro("");
  }

  async function salvar() {
    if (!form.nome.trim()) { setErro("Nome é obrigatório."); return; }
    setSaving(true);
    const res = await fetch("/api/financeiro/fornecedores", {
      method: isEdit ? "PUT" : "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(isEdit ? { id: fornecedor!.id, ...form } : form),
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
      <div className="modal-box" style={{ maxWidth: 580 }}>
        <div className="modal-header">
          <div>
            <div className="modal-title">{isEdit ? "Editar fornecedor" : "Novo fornecedor"}</div>
            <div className="modal-subtitle">Dados do fornecedor/prestador</div>
          </div>
          <button className="modal-close" onClick={onClose}>
            <svg viewBox="0 0 20 20" fill="currentColor"><path fillRule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clipRule="evenodd" /></svg>
          </button>
        </div>
        <div className="modal-body">
          <div className="form-grid">
            <div className="form-group form-group-span2">
              <label className="form-label">Nome *</label>
              <input className="form-input" value={form.nome} onChange={(e) => upd("nome", e.target.value)} autoFocus placeholder="Nome do fornecedor" />
            </div>
            <div className="form-group">
              <label className="form-label">CPF / CNPJ</label>
              <input className="form-input" value={form.cpf_cnpj} onChange={(e) => upd("cpf_cnpj", e.target.value)} placeholder="000.000.000-00" />
            </div>
            <div className="form-group">
              <label className="form-label">Categoria</label>
              <select className="form-input" value={form.categoria} onChange={(e) => upd("categoria", e.target.value)}>
                {CATEGORIAS.map((c) => <option key={c}>{c}</option>)}
              </select>
            </div>
            <div className="form-group">
              <label className="form-label">Telefone</label>
              <input className="form-input" value={form.telefone} onChange={(e) => upd("telefone", e.target.value)} placeholder="(00) 00000-0000" />
            </div>
            <div className="form-group">
              <label className="form-label">E-mail</label>
              <input className="form-input" type="email" value={form.email} onChange={(e) => upd("email", e.target.value)} placeholder="email@exemplo.com" />
            </div>
            <div className="form-group form-group-span2">
              <label className="form-label">Endereço</label>
              <input className="form-input" value={form.endereco} onChange={(e) => upd("endereco", e.target.value)} placeholder="Rua, número, bairro, cidade" />
            </div>
            <div className="form-group">
              <label className="form-label">Chave PIX</label>
              <input className="form-input" value={form.chave_pix} onChange={(e) => upd("chave_pix", e.target.value)} placeholder="CPF, e-mail, telefone ou aleatória" />
            </div>
            <div className="form-group">
              <label className="form-label">Banco</label>
              <input className="form-input" value={form.banco} onChange={(e) => upd("banco", e.target.value)} placeholder="Ex: Nubank, Itaú" />
            </div>
            <div className="form-group form-group-span2">
              <label className="form-label">Observações</label>
              <textarea className="form-input form-textarea" rows={2} value={form.observacoes} onChange={(e) => upd("observacoes", e.target.value)} placeholder="Observações opcionais..." />
            </div>
          </div>
          {erro && <div className="form-error">{erro}</div>}
        </div>
        <div className="modal-footer">
          <button className="btn btn-secondary" onClick={onClose} disabled={saving}>Cancelar</button>
          <button className="btn btn-primary" onClick={salvar} disabled={saving}>{saving ? "Salvando…" : isEdit ? "Salvar" : "Criar fornecedor"}</button>
        </div>
      </div>
    </div>
  );
}

function DespesaFornecedorModal({
  fornecedor,
  onClose,
  onSaved,
}: {
  fornecedor: Fornecedor;
  onClose: () => void;
  onSaved: () => void;
}) {
  const [form, setForm] = useState({
    descricao: "",
    valor: "",
    vencimento: hoje(),
    status: "Pendente",
  });
  const [saving, setSaving] = useState(false);
  const [erro, setErro] = useState("");

  function upd(k: string, v: string) {
    setForm((p) => ({ ...p, [k]: v }));
    setErro("");
  }

  async function salvar() {
    if (!form.valor || isNaN(parseFloat(form.valor.replace(",", ".")))) { setErro("Informe um valor válido."); return; }
    if (!form.vencimento) { setErro("Informe o vencimento."); return; }
    setSaving(true);
    const res = await fetch("/api/financeiro", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        tipo: "despesas",
        aluno: fornecedor.nome,
        fornecedor_id: fornecedor.id,
        descricao: form.descricao,
        valor: form.valor,
        vencimento: form.vencimento,
        status: form.status,
      }),
    });
    setSaving(false);
    if (!res.ok) { const d = await res.json().catch(() => ({})); setErro((d as { error?: string }).error || "Erro ao salvar."); return; }
    onSaved();
  }

  return (
    <div className="modal-overlay" onClick={(e) => e.target === e.currentTarget && onClose()}>
      <div className="modal-box" style={{ maxWidth: 480 }}>
        <div className="modal-header">
          <div>
            <div className="modal-title">Nova despesa</div>
            <div className="modal-subtitle">Fornecedor: {fornecedor.nome}</div>
          </div>
          <button className="modal-close" onClick={onClose}>
            <svg viewBox="0 0 20 20" fill="currentColor"><path fillRule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clipRule="evenodd" /></svg>
          </button>
        </div>
        <div className="modal-body">
          <div className="form-grid">
            <div className="form-group form-group-span2">
              <label className="form-label">Descrição</label>
              <input className="form-input" value={form.descricao} onChange={(e) => upd("descricao", e.target.value)} placeholder="Ex: Aluguel Dezembro" autoFocus />
            </div>
            <div className="form-group">
              <label className="form-label">Valor (R$) *</label>
              <input className="form-input" inputMode="decimal" value={form.valor} onChange={(e) => upd("valor", e.target.value)} placeholder="0,00" />
            </div>
            <div className="form-group">
              <label className="form-label">Vencimento *</label>
              <input className="form-input" type="date" value={form.vencimento} onChange={(e) => upd("vencimento", e.target.value)} />
            </div>
            <div className="form-group form-group-span2">
              <label className="form-label">Status</label>
              <select className="form-input" value={form.status} onChange={(e) => upd("status", e.target.value)}>
                <option>Pendente</option>
                <option>Pago</option>
                <option>Atrasado</option>
                <option>Cancelado</option>
              </select>
            </div>
          </div>
          {erro && <div className="form-error">{erro}</div>}
        </div>
        <div className="modal-footer">
          <button className="btn btn-secondary" onClick={onClose} disabled={saving}>Cancelar</button>
          <button className="btn btn-primary" onClick={salvar} disabled={saving}>{saving ? "Salvando…" : "Criar despesa"}</button>
        </div>
      </div>
    </div>
  );
}

export function FinanceiroFornecedores({
  fornecedores: fornecedoresInicial,
  despesas,
}: {
  fornecedores: Fornecedor[];
  despesas: Despesa[];
}) {
  const router = useRouter();
  const [fornecedores, setFornecedores] = useState<Fornecedor[]>(fornecedoresInicial);
  const [modalNovo, setModalNovo] = useState(false);
  const [editando, setEditando] = useState<Fornecedor | null>(null);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [novaDepForn, setNovaDepForn] = useState<Fornecedor | null>(null);
  const [busca, setBusca] = useState("");
  const [filtroCategoria, setFiltroCategoria] = useState("Todas");
  const [deletando, setDeletando] = useState<string | null>(null);

  const filtrados = useMemo(() => fornecedores.filter((f) => {
    const matchBusca = !busca || f.nome.toLowerCase().includes(busca.toLowerCase()) || String(f.categoria || "").toLowerCase().includes(busca.toLowerCase());
    const matchCat = filtroCategoria === "Todas" || f.categoria === filtroCategoria;
    return matchBusca && matchCat;
  }), [fornecedores, busca, filtroCategoria]);

  const fornecedorSelecionado = selectedId ? fornecedores.find((f) => f.id === selectedId) : null;

  const despesasFornecedor = useMemo(() => {
    if (!fornecedorSelecionado) return [];
    return despesas.filter((d) =>
      d.fornecedor_id === fornecedorSelecionado.id ||
      String(d.aluno || d.nome || "").toLowerCase() === fornecedorSelecionado.nome.toLowerCase()
    );
  }, [despesas, fornecedorSelecionado]);

  async function recarregar() {
    const res = await fetch("/api/financeiro/fornecedores");
    if (res.ok) {
      const data = await res.json().catch(() => ({}));
      setFornecedores(Array.isArray(data.fornecedores) ? data.fornecedores : []);
    }
    router.refresh();
  }

  async function excluirFornecedor(id: string) {
    if (!confirm("Excluir este fornecedor? As despesas relacionadas não serão removidas.")) return;
    setDeletando(id);
    await fetch(`/api/financeiro/fornecedores?id=${id}`, { method: "DELETE" });
    setDeletando(null);
    if (selectedId === id) setSelectedId(null);
    await recarregar();
  }

  async function baixarDespesa(despesa: Despesa) {
    if (!confirm("Registrar baixa desta despesa?")) return;
    await fetch("/api/financeiro", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ id: despesa.id, tipo: "despesas", status: "Pago", data_baixa: hoje() }),
    });
    router.refresh();
  }

  async function excluirDespesa(despesa: Despesa) {
    if (!confirm("Excluir esta despesa? Esta ação não pode ser desfeita.")) return;
    await fetch(`/api/financeiro?id=${despesa.id}&tipo=despesas`, { method: "DELETE" });
    router.refresh();
  }

  const totalFornecedor = despesasFornecedor.reduce((s, d) => s + parseValor(d.valor), 0);
  const totalPagoForn = despesasFornecedor.filter((d) => statusBadge(String(d.status || "")) === "success").reduce((s, d) => s + parseValor(d.valor), 0);

  return (
    <>
      <div className="card">
        <div className="toolbar">
          <div className="toolbar-left">
            <div className="search-bar">
              <span className="search-icon">
                <svg viewBox="0 0 20 20" fill="currentColor"><path fillRule="evenodd" d="M8 4a4 4 0 100 8 4 4 0 000-8zM2 8a6 6 0 1110.89 3.476l4.817 4.817a1 1 0 01-1.414 1.414l-4.816-4.816A6 6 0 012 8z" clipRule="evenodd" /></svg>
              </span>
              <input className="search-input" placeholder="Buscar fornecedor..." value={busca} onChange={(e) => setBusca(e.target.value)} />
            </div>
          </div>
          <div className="toolbar-right">
            <select className="filter-select" value={filtroCategoria} onChange={(e) => setFiltroCategoria(e.target.value)}>
              <option value="Todas">Todas as categorias</option>
              {CATEGORIAS.map((c) => <option key={c}>{c}</option>)}
            </select>
            <button className="btn btn-primary" onClick={() => setModalNovo(true)}>
              <svg viewBox="0 0 20 20" fill="currentColor" width={16} height={16} style={{ marginRight: 4 }}>
                <path fillRule="evenodd" d="M10 3a1 1 0 011 1v5h5a1 1 0 110 2h-5v5a1 1 0 11-2 0v-5H4a1 1 0 110-2h5V4a1 1 0 011-1z" clipRule="evenodd" />
              </svg>
              Novo fornecedor
            </button>
          </div>
        </div>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: selectedId ? "1fr 1.5fr" : "1fr", gap: 16 }}>
        {/* Lista de fornecedores */}
        <div className="card">
          <div className="card-header">
            <div>
              <div className="section-eyebrow">Fornecedores</div>
              <h3 className="section-title">Cadastro de fornecedores</h3>
              <p className="section-subtitle">{filtrados.length} fornecedor{filtrados.length !== 1 ? "es" : ""}</p>
            </div>
          </div>
          <div className="card-body" style={{ paddingTop: 0 }}>
            {filtrados.length === 0 ? (
              <div className="empty-state">
                <div className="empty-title">Nenhum fornecedor cadastrado</div>
                <p className="empty-desc">Clique em "Novo fornecedor" para começar.</p>
              </div>
            ) : (
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Nome / Categoria</th>
                    <th>Contato</th>
                    <th>PIX</th>
                    <th>Ações</th>
                  </tr>
                </thead>
                <tbody>
                  {filtrados.map((f) => (
                    <tr
                      key={f.id}
                      style={{ cursor: "pointer", background: selectedId === f.id ? "rgba(37,99,235,0.06)" : undefined }}
                      onClick={() => setSelectedId(selectedId === f.id ? null : f.id)}
                    >
                      <td>
                        <div className="table-name-cell">
                          <span className="table-name-primary">{f.nome}</span>
                          {f.categoria && <span className="table-name-secondary">{f.categoria}</span>}
                        </div>
                      </td>
                      <td>
                        <div style={{ fontSize: "0.82rem", color: "var(--text-secondary)" }}>
                          {f.telefone && <div>{f.telefone}</div>}
                          {f.email && <div>{f.email}</div>}
                        </div>
                      </td>
                      <td>
                        {f.chave_pix ? (
                          <span style={{ fontSize: "0.78rem", fontFamily: "monospace", color: "var(--text-secondary)" }}>{f.chave_pix}</span>
                        ) : (
                          <span style={{ color: "var(--text-faint)", fontSize: "0.78rem" }}>—</span>
                        )}
                      </td>
                      <td onClick={(e) => e.stopPropagation()}>
                        <div style={{ display: "flex", gap: 4 }}>
                          <button className="btn btn-ghost btn-sm" title="Ver despesas" onClick={() => setSelectedId(selectedId === f.id ? null : f.id)}>
                            <svg viewBox="0 0 20 20" fill="currentColor" width={14} height={14}><path d="M10 12a2 2 0 100-4 2 2 0 000 4z" /><path fillRule="evenodd" d="M.458 10C1.732 5.943 5.522 3 10 3s8.268 2.943 9.542 7c-1.274 4.057-5.064 7-9.542 7S1.732 14.057.458 10zM14 10a4 4 0 11-8 0 4 4 0 018 0z" clipRule="evenodd" /></svg>
                          </button>
                          <button className="btn btn-ghost btn-sm" title="Editar" onClick={() => setEditando(f)}>
                            <svg viewBox="0 0 20 20" fill="currentColor" width={14} height={14}><path d="M13.586 3.586a2 2 0 112.828 2.828l-.793.793-2.828-2.828.793-.793zM11.379 5.793L3 14.172V17h2.828l8.38-8.379-2.83-2.828z" /></svg>
                          </button>
                          <button className="btn btn-ghost btn-sm" title="Excluir" style={{ color: "var(--red-600)" }} disabled={deletando === f.id} onClick={() => excluirFornecedor(f.id)}>
                            <svg viewBox="0 0 20 20" fill="currentColor" width={14} height={14}><path fillRule="evenodd" d="M9 2a1 1 0 00-.894.553L7.382 4H4a1 1 0 000 2v10a2 2 0 002 2h8a2 2 0 002-2V6a1 1 0 100-2h-3.382l-.724-1.447A1 1 0 0011 2H9zM7 8a1 1 0 012 0v6a1 1 0 11-2 0V8zm5-1a1 1 0 00-1 1v6a1 1 0 102 0V8a1 1 0 00-1-1z" clipRule="evenodd" /></svg>
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </div>

        {/* Painel de despesas do fornecedor selecionado */}
        {fornecedorSelecionado && (
          <div className="card">
            <div className="card-header">
              <div>
                <div className="section-eyebrow">Despesas</div>
                <h3 className="section-title">{fornecedorSelecionado.nome}</h3>
                <p className="section-subtitle">{despesasFornecedor.length} lançamento{despesasFornecedor.length !== 1 ? "s" : ""}</p>
              </div>
              <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
                <div style={{ textAlign: "right" }}>
                  <div style={{ fontSize: "0.68rem", color: "var(--text-muted)", marginBottom: 2 }}>Total</div>
                  <div style={{ fontWeight: 800, color: "var(--red-700)", fontSize: "1rem" }}>{formatBRL(totalFornecedor)}</div>
                  {totalPagoForn > 0 && <div style={{ fontSize: "0.72rem", color: "var(--green-700)" }}>Pago: {formatBRL(totalPagoForn)}</div>}
                </div>
                <button className="btn btn-primary btn-sm" onClick={() => setNovaDepForn(fornecedorSelecionado)}>
                  <svg viewBox="0 0 20 20" fill="currentColor" width={14} height={14} style={{ marginRight: 4 }}>
                    <path fillRule="evenodd" d="M10 3a1 1 0 011 1v5h5a1 1 0 110 2h-5v5a1 1 0 11-2 0v-5H4a1 1 0 110-2h5V4a1 1 0 011-1z" clipRule="evenodd" />
                  </svg>
                  Novo lançamento
                </button>
                <button className="btn btn-ghost btn-sm" onClick={() => setSelectedId(null)} title="Fechar painel">
                  <svg viewBox="0 0 20 20" fill="currentColor" width={16} height={16}><path fillRule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clipRule="evenodd" /></svg>
                </button>
              </div>
            </div>

            {fornecedorSelecionado.banco || fornecedorSelecionado.chave_pix ? (
              <div style={{ padding: "10px 20px", background: "var(--surface-raised)", borderBottom: "1px solid var(--border)", fontSize: "0.82rem", color: "var(--text-secondary)", display: "flex", gap: 16, flexWrap: "wrap" }}>
                {fornecedorSelecionado.chave_pix && <span><strong>PIX:</strong> {fornecedorSelecionado.chave_pix}</span>}
                {fornecedorSelecionado.banco && <span><strong>Banco:</strong> {fornecedorSelecionado.banco}</span>}
                {fornecedorSelecionado.telefone && <span><strong>Tel:</strong> {fornecedorSelecionado.telefone}</span>}
              </div>
            ) : null}

            <div className="card-body" style={{ paddingTop: 0 }}>
              {despesasFornecedor.length === 0 ? (
                <div className="empty-state">
                  <div className="empty-title">Sem despesas para este fornecedor</div>
                  <p className="empty-desc">Clique em "Novo lançamento" para registrar.</p>
                </div>
              ) : (
                <table className="data-table">
                  <thead>
                    <tr>
                      <th>Descrição</th>
                      <th>Vencimento</th>
                      <th>Valor</th>
                      <th>Status</th>
                      <th>Ações</th>
                    </tr>
                  </thead>
                  <tbody>
                    {despesasFornecedor.map((d, i) => {
                      const status = String(d.status || d.situacao || "Pendente");
                      const venc = String(d.vencimento || d.data_vencimento || "");
                      const atrasado = venc && statusBadge(status) !== "success" && parseBRDate(venc) < new Date();
                      const badge = statusBadge(status);
                      return (
                        <tr key={String(d.id || i)}>
                          <td>
                            <div className="table-name-cell">
                              <span className="table-name-primary">{String(d.descricao || "Sem descrição")}</span>
                            </div>
                          </td>
                          <td>
                            <span style={{ fontWeight: 600, color: atrasado ? "var(--red-600)" : "inherit" }}>
                              {venc ? fmtDate(venc) : "—"}{atrasado ? " ⚠" : ""}
                            </span>
                          </td>
                          <td>
                            <span style={{ fontWeight: 700, color: "var(--red-700)" }}>{formatBRL(parseValor(d.valor))}</span>
                          </td>
                          <td>
                            <span className={`badge badge-${badge}`}><span className="badge-dot" />{status}</span>
                          </td>
                          <td>
                            <div style={{ display: "flex", gap: 4 }}>
                              {badge !== "success" && (
                                <button className="btn btn-ghost btn-sm" style={{ color: "var(--green-700)", fontSize: "0.75rem" }} onClick={() => baixarDespesa(d)}>
                                  Baixar
                                </button>
                              )}
                              <button className="btn btn-ghost btn-sm" style={{ color: "var(--red-600)", fontSize: "0.75rem" }} onClick={() => excluirDespesa(d)}>
                                Excluir
                              </button>
                            </div>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              )}
            </div>
          </div>
        )}
      </div>

      {modalNovo && (
        <FornecedorModal
          onClose={() => setModalNovo(false)}
          onSaved={() => { setModalNovo(false); recarregar(); }}
        />
      )}

      {editando && (
        <FornecedorModal
          fornecedor={editando}
          onClose={() => setEditando(null)}
          onSaved={() => { setEditando(null); recarregar(); }}
        />
      )}

      {novaDepForn && (
        <DespesaFornecedorModal
          fornecedor={novaDepForn}
          onClose={() => setNovaDepForn(null)}
          onSaved={() => { setNovaDepForn(null); router.refresh(); }}
        />
      )}
    </>
  );
}
