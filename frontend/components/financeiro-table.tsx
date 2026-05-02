"use client";

import { useState, useMemo } from "react";
import { BaixaBtn, EditarLancamentoBtn } from "./financeiro-modal";

type Lancamento = {
  id?: string;
  aluno?: string;
  nome?: string;
  descricao?: string;
  valor?: number | string;
  vencimento?: string;
  data_vencimento?: string;
  data_baixa?: string;
  status?: string;
  situacao?: string;
  tipo?: string;
  codigo?: string;
  [k: string]: unknown;
};

type Tab = "recebimentos" | "despesas" | "professores" | "relatorio";

function parseValor(v: unknown): number {
  return parseFloat(String(v || "0").replace(/[^\d.,]/g, "").replace(",", ".")) || 0;
}

function formatBRL(v: number): string {
  return v.toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
}

function statusBadge(s: string) {
  const l = s.toLowerCase();
  if (l.includes("pago") || l.includes("baixado") || l.includes("liquidado")) return "success";
  if (l.includes("atraso") || l.includes("vencido")) return "danger";
  if (l.includes("pendent") || l.includes("boleto")) return "warning";
  return "neutral";
}

function fmtDate(v: string) {
  try { return new Date(v).toLocaleDateString("pt-BR"); } catch { return v; }
}

/* ── Recibo ── */
function ReciboModal({ lancamento, onClose }: { lancamento: Lancamento; onClose: () => void }) {
  const nome = String(lancamento.aluno || lancamento.nome || "Pagante");
  const descricao = String(lancamento.descricao || "");
  const valor = parseValor(lancamento.valor);
  const dataBaixa = lancamento.data_baixa
    ? fmtDate(String(lancamento.data_baixa))
    : new Date().toLocaleDateString("pt-BR");
  const recNum = String(lancamento.id || Date.now()).slice(-6).toUpperCase();

  return (
    <div className="modal-overlay" onClick={(e) => e.target === e.currentTarget && onClose()}>
      <div className="modal-box" style={{ maxWidth: 500 }}>
        <div className="modal-header">
          <div className="modal-title">Recibo de Pagamento</div>
          <div style={{ display: "flex", gap: 8 }}>
            <button className="btn btn-secondary btn-sm" onClick={() => window.print()}>
              <svg viewBox="0 0 20 20" fill="currentColor" width={14} height={14}>
                <path fillRule="evenodd" d="M5 4v3H4a2 2 0 00-2 2v3a2 2 0 002 2h1v2a1 1 0 001 1h8a1 1 0 001-1v-2h1a2 2 0 002-2V9a2 2 0 00-2-2h-1V4a1 1 0 00-1-1H6a1 1 0 00-1 1zm2 0h6v3H7V4zm0 8H6v4h8v-4h-7v1a1 1 0 102 0v-1z" clipRule="evenodd" />
              </svg>
              Imprimir
            </button>
            <button className="modal-close" onClick={onClose}>
              <svg viewBox="0 0 20 20" fill="currentColor"><path fillRule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clipRule="evenodd" /></svg>
            </button>
          </div>
        </div>
        <div className="modal-body" id="recibo-print">
          <div style={{ textAlign: "center", paddingBottom: 20, marginBottom: 20, borderBottom: "2px solid var(--border)" }}>
            <div style={{ fontWeight: 800, fontSize: "1.375rem", color: "var(--navy-900)" }}>Ativo Educacional</div>
            <div style={{ fontSize: "0.72rem", color: "var(--text-muted)", letterSpacing: "0.12em", textTransform: "uppercase", marginTop: 4 }}>Recibo de Pagamento</div>
          </div>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "14px 24px", marginBottom: 20 }}>
            <div>
              <div style={{ fontSize: "0.72rem", textTransform: "uppercase", letterSpacing: "0.08em", color: "var(--text-muted)", marginBottom: 4 }}>Recibo nº</div>
              <div style={{ fontWeight: 700, fontFamily: "monospace", fontSize: "1rem" }}>{recNum}</div>
            </div>
            <div>
              <div style={{ fontSize: "0.72rem", textTransform: "uppercase", letterSpacing: "0.08em", color: "var(--text-muted)", marginBottom: 4 }}>Data</div>
              <div style={{ fontWeight: 700 }}>{dataBaixa}</div>
            </div>
            <div style={{ gridColumn: "span 2" }}>
              <div style={{ fontSize: "0.72rem", textTransform: "uppercase", letterSpacing: "0.08em", color: "var(--text-muted)", marginBottom: 4 }}>Recebemos de</div>
              <div style={{ fontWeight: 700, fontSize: "1.0625rem" }}>{nome}</div>
            </div>
            <div style={{ gridColumn: "span 2" }}>
              <div style={{ fontSize: "0.72rem", textTransform: "uppercase", letterSpacing: "0.08em", color: "var(--text-muted)", marginBottom: 4 }}>Referente a</div>
              <div style={{ color: "var(--text-secondary)" }}>{descricao || "Mensalidade / Serviços Educacionais"}</div>
            </div>
          </div>
          <div style={{ padding: "20px 24px", background: "linear-gradient(135deg, rgba(5,150,105,0.06), rgba(5,150,105,0.02))", borderRadius: "var(--radius-lg)", border: "2px solid rgba(5,150,105,0.15)", textAlign: "center", marginBottom: 20 }}>
            <div style={{ fontSize: "0.72rem", color: "var(--text-muted)", marginBottom: 8, textTransform: "uppercase", letterSpacing: "0.1em" }}>Valor Recebido</div>
            <div style={{ fontSize: "2.25rem", fontWeight: 800, color: "var(--green-700)", letterSpacing: "-0.03em" }}>{formatBRL(valor)}</div>
          </div>
          <div style={{ borderTop: "1px dashed var(--border)", paddingTop: 14, textAlign: "center" }}>
            <div style={{ fontSize: "0.75rem", color: "var(--text-faint)" }}>Ativo Educacional {new Date().getFullYear()} - Sistema de Gestao Educacional</div>
            <div style={{ fontSize: "0.7rem", color: "var(--text-faint)", marginTop: 3 }}>Este recibo confirma o pagamento do valor acima especificado.</div>
          </div>
        </div>
      </div>
    </div>
  );
}

function ReciboBtn({ lancamento }: { lancamento: Lancamento }) {
  const [open, setOpen] = useState(false);
  const isPago = String(lancamento.status || "").toLowerCase().includes("pago") ||
    String(lancamento.status || "").toLowerCase().includes("baixado");
  if (!isPago) return null;
  return (
    <>
      <button className="btn btn-ghost btn-sm" style={{ fontSize: "0.72rem", color: "var(--blue-600)" }} onClick={() => setOpen(true)} title="Ver recibo">Recibo</button>
      {open && <ReciboModal lancamento={lancamento} onClose={() => setOpen(false)} />}
    </>
  );
}

/* ── Tab: Recebimentos ── */
function RecebimentosTab({ recebimentos }: { recebimentos: Lancamento[] }) {
  const [busca, setBusca] = useState("");
  const [filtroStatus, setFiltroStatus] = useState("Todos");
  const [filtroPeriodo, setFiltroPeriodo] = useState("Todos");

  function isMesAtual(v: string) { const d = new Date(v), n = new Date(); return d.getMonth() === n.getMonth() && d.getFullYear() === n.getFullYear(); }
  function isMesPassado(v: string) { const d = new Date(v), n = new Date(), mp = new Date(n.getFullYear(), n.getMonth() - 1, 1); return d.getMonth() === mp.getMonth() && d.getFullYear() === mp.getFullYear(); }

  const filtrados = useMemo(() => recebimentos.filter((r) => {
    const nome = String(r.aluno || r.nome || r.descricao || "").toLowerCase();
    const status = String(r.status || r.situacao || "Pendente");
    const venc = String(r.vencimento || r.data_vencimento || "");
    const matchBusca = !busca || nome.includes(busca.toLowerCase()) || String(r.codigo || "").toLowerCase().includes(busca.toLowerCase());
    const matchStatus = filtroStatus === "Todos" ||
      (filtroStatus === "Em aberto" && statusBadge(status) !== "success") ||
      (filtroStatus === "Pago" && statusBadge(status) === "success") ||
      (filtroStatus === "Atrasado" && statusBadge(status) === "danger");
    const matchPeriodo = filtroPeriodo === "Todos" ||
      (filtroPeriodo === "Este mês" && venc && isMesAtual(venc)) ||
      (filtroPeriodo === "Mês passado" && venc && isMesPassado(venc));
    return matchBusca && matchStatus && matchPeriodo;
  }), [recebimentos, busca, filtroStatus, filtroPeriodo]);

  const total = filtrados.reduce((s, r) => s + parseValor(r.valor), 0);

  return (
    <>
      <div className="card">
        <div className="toolbar">
          <div className="toolbar-left">
            <div className="search-bar">
              <span className="search-icon"><svg viewBox="0 0 20 20" fill="currentColor"><path fillRule="evenodd" d="M8 4a4 4 0 100 8 4 4 0 000-8zM2 8a6 6 0 1110.89 3.476l4.817 4.817a1 1 0 01-1.414 1.414l-4.816-4.816A6 6 0 012 8z" clipRule="evenodd" /></svg></span>
              <input className="search-input" placeholder="Buscar aluno ou descrição..." value={busca} onChange={(e) => setBusca(e.target.value)} />
            </div>
          </div>
          <div className="toolbar-right">
            <select className="filter-select" value={filtroStatus} onChange={(e) => setFiltroStatus(e.target.value)}>
              <option value="Todos">Todos os status</option>
              <option>Em aberto</option>
              <option>Pago</option>
              <option>Atrasado</option>
            </select>
            <select className="filter-select" value={filtroPeriodo} onChange={(e) => setFiltroPeriodo(e.target.value)}>
              <option value="Todos">Todos os períodos</option>
              <option>Este mês</option>
              <option>Mês passado</option>
            </select>
          </div>
        </div>
      </div>
      <div className="card">
        <div className="card-header">
          <div>
            <div className="section-eyebrow">Recebimentos</div>
            <h3 className="section-title">Mensalidades e cobranças</h3>
            <p className="section-subtitle">{filtrados.length} de {recebimentos.length} lançamentos</p>
          </div>
          <div style={{ textAlign: "right" }}>
            <div style={{ fontSize: "0.72rem", color: "var(--text-muted)", marginBottom: 2 }}>Total filtrado</div>
            <div style={{ fontWeight: 700, fontSize: "1rem" }}>{formatBRL(total)}</div>
          </div>
        </div>
        <div className="card-body" style={{ paddingTop: 12 }}>
          {filtrados.length === 0 ? (
            <div className="empty-state"><div className="empty-title">Nenhum lançamento encontrado</div><p className="empty-desc">Ajuste os filtros para ver mais resultados.</p></div>
          ) : (
            <table className="data-table">
              <thead><tr><th>Aluno / Descrição</th><th>Vencimento</th><th>Valor</th><th>Status</th><th>Ações</th></tr></thead>
              <tbody>
                {filtrados.map((r, i) => {
                  const nome = String(r.aluno || r.nome || r.descricao || `Lançamento ${i + 1}`);
                  const venc = String(r.vencimento || r.data_vencimento || "—");
                  const status = String(r.status || r.situacao || "Pendente");
                  const atrasado = venc !== "—" && statusBadge(status) !== "success" && new Date(venc) < new Date();
                  return (
                    <tr key={String(r.id || i)}>
                      <td>
                        <div className="table-name-cell">
                          <span className="table-name-primary">{nome}</span>
                          {r.codigo && <span className="table-name-secondary">{String(r.codigo)}</span>}
                          {String(r.descricao || "") && String(r.descricao) !== nome && <span className="table-name-secondary">{String(r.descricao)}</span>}
                        </div>
                      </td>
                      <td><span style={{ fontWeight: 600, color: atrasado ? "var(--red-600)" : "inherit" }}>{venc !== "—" ? fmtDate(venc) : "—"}{atrasado && " ⚠"}</span></td>
                      <td><span style={{ fontWeight: 700, fontSize: "0.9375rem" }}>{formatBRL(parseValor(r.valor))}</span></td>
                      <td><span className={`badge badge-${statusBadge(status)}`}><span className="badge-dot" />{status}</span></td>
                      <td><div style={{ display: "flex", gap: 4 }}><BaixaBtn lancamento={r} tipo="recebimentos" /><ReciboBtn lancamento={r} /><EditarLancamentoBtn lancamento={r} tipo="recebimentos" /></div></td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </>
  );
}

/* ── Tab: Despesas ── */
function DespesasTab({ despesas }: { despesas: Lancamento[] }) {
  const [busca, setBusca] = useState("");
  const [filtroStatus, setFiltroStatus] = useState("Todos");

  const filtrados = useMemo(() => despesas.filter((d) => {
    const nome = String(d.aluno || d.nome || d.descricao || "").toLowerCase();
    const status = String(d.status || d.situacao || "Pendente");
    const matchBusca = !busca || nome.includes(busca.toLowerCase());
    const matchStatus = filtroStatus === "Todos" ||
      (filtroStatus === "Em aberto" && statusBadge(status) !== "success") ||
      (filtroStatus === "Pago" && statusBadge(status) === "success");
    return matchBusca && matchStatus;
  }), [despesas, busca, filtroStatus]);

  const total = filtrados.reduce((s, d) => s + parseValor(d.valor), 0);

  return (
    <>
      <div className="card">
        <div className="toolbar">
          <div className="toolbar-left">
            <div className="search-bar">
              <span className="search-icon"><svg viewBox="0 0 20 20" fill="currentColor"><path fillRule="evenodd" d="M8 4a4 4 0 100 8 4 4 0 000-8zM2 8a6 6 0 1110.89 3.476l4.817 4.817a1 1 0 01-1.414 1.414l-4.816-4.816A6 6 0 012 8z" clipRule="evenodd" /></svg></span>
              <input className="search-input" placeholder="Buscar fornecedor ou despesa..." value={busca} onChange={(e) => setBusca(e.target.value)} />
            </div>
          </div>
          <div className="toolbar-right">
            <select className="filter-select" value={filtroStatus} onChange={(e) => setFiltroStatus(e.target.value)}>
              <option value="Todos">Todos</option>
              <option>Em aberto</option>
              <option>Pago</option>
            </select>
          </div>
        </div>
      </div>
      <div className="card">
        <div className="card-header">
          <div>
            <div className="section-eyebrow">Despesas</div>
            <h3 className="section-title">Custos e pagamentos</h3>
            <p className="section-subtitle">{filtrados.length} de {despesas.length} lançamentos</p>
          </div>
          <div style={{ textAlign: "right" }}>
            <div style={{ fontSize: "0.72rem", color: "var(--text-muted)", marginBottom: 2 }}>Total filtrado</div>
            <div style={{ fontWeight: 700, fontSize: "1rem", color: "var(--red-700)" }}>{formatBRL(total)}</div>
          </div>
        </div>
        <div className="card-body" style={{ paddingTop: 12 }}>
          {filtrados.length === 0 ? (
            <div className="empty-state"><div className="empty-title">Nenhuma despesa encontrada</div><p className="empty-desc">Cadastre despesas com "Novo lançamento → Despesa".</p></div>
          ) : (
            <table className="data-table">
              <thead><tr><th>Fornecedor / Descrição</th><th>Vencimento</th><th>Valor</th><th>Status</th><th>Ações</th></tr></thead>
              <tbody>
                {filtrados.map((d, i) => {
                  const nome = String(d.aluno || d.nome || d.descricao || `Despesa ${i + 1}`);
                  const venc = String(d.vencimento || d.data_vencimento || "—");
                  const status = String(d.status || d.situacao || "Pendente");
                  const atrasado = venc !== "—" && statusBadge(status) !== "success" && new Date(venc) < new Date();
                  return (
                    <tr key={String(d.id || i)}>
                      <td>
                        <div className="table-name-cell">
                          <span className="table-name-primary">{nome}</span>
                          {String(d.descricao || "") && String(d.descricao) !== nome && <span className="table-name-secondary">{String(d.descricao)}</span>}
                        </div>
                      </td>
                      <td><span style={{ fontWeight: 600, color: atrasado ? "var(--red-600)" : "inherit" }}>{venc !== "—" ? fmtDate(venc) : "—"}{atrasado && " ⚠"}</span></td>
                      <td><span style={{ fontWeight: 700, color: "var(--red-700)" }}>{formatBRL(parseValor(d.valor))}</span></td>
                      <td><span className={`badge badge-${statusBadge(status)}`}><span className="badge-dot" />{status}</span></td>
                      <td><div style={{ display: "flex", gap: 4 }}><BaixaBtn lancamento={d} tipo="despesas" /><EditarLancamentoBtn lancamento={d} tipo="despesas" /></div></td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </>
  );
}

/* ── Tab: Pagamento Professores ── */
function ProfessoresTab({ despesas }: { despesas: Lancamento[] }) {
  const profDespesas = useMemo(() => despesas.filter((d) => {
    const all = [d.aluno, d.nome, d.descricao, d.tipo].map((v) => String(v || "").toLowerCase()).join(" ");
    return all.includes("professor") || all.includes("salário") || all.includes("salario") || all.includes("docente") || all.includes("pagto prof");
  }), [despesas]);

  const total = profDespesas.reduce((s, d) => s + parseValor(d.valor), 0);
  const totalPago = profDespesas.filter((d) => statusBadge(String(d.status || "")) === "success").reduce((s, d) => s + parseValor(d.valor), 0);

  return (
    <>
      <div className="metric-grid metric-grid-3">
        <div className="metric-card metric-card-gold">
          <div className="metric-icon metric-icon-gold"><svg viewBox="0 0 20 20" fill="currentColor"><path fillRule="evenodd" d="M10 9a3 3 0 100-6 3 3 0 000 6zm-7 9a7 7 0 1114 0H3z" clipRule="evenodd" /></svg></div>
          <div className="metric-label">Lançamentos</div>
          <div className="metric-value">{profDespesas.length}</div>
          <div className="metric-note">Pagamentos de professores</div>
        </div>
        <div className="metric-card metric-card-green">
          <div className="metric-icon metric-icon-green"><svg viewBox="0 0 20 20" fill="currentColor"><path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" /></svg></div>
          <div className="metric-label">Pago</div>
          <div className="metric-value" style={{ fontSize: "1.5rem" }}>{formatBRL(totalPago)}</div>
          <div className="metric-note">Pagamentos confirmados</div>
        </div>
        <div className="metric-card metric-card-red">
          <div className="metric-icon metric-icon-red"><svg viewBox="0 0 20 20" fill="currentColor"><path d="M4 4a2 2 0 00-2 2v1h16V6a2 2 0 00-2-2H4z" /><path fillRule="evenodd" d="M18 9H2v5a2 2 0 002 2h12a2 2 0 002-2V9z" clipRule="evenodd" /></svg></div>
          <div className="metric-label">Em aberto</div>
          <div className="metric-value" style={{ fontSize: "1.5rem" }}>{formatBRL(total - totalPago)}</div>
          <div className="metric-note">Aguardando pagamento</div>
        </div>
      </div>
      <div className="card">
        <div className="card-header">
          <div>
            <div className="section-eyebrow">Professores</div>
            <h3 className="section-title">Pagamento de professores</h3>
            <p className="section-subtitle">{profDespesas.length} lançamentos encontrados</p>
          </div>
        </div>
        <div className="card-body" style={{ paddingTop: 12 }}>
          {profDespesas.length === 0 ? (
            <div className="empty-state">
              <div className="empty-title">Nenhum pagamento de professor encontrado</div>
              <p className="empty-desc">Cadastre despesas com "professor", "salário" ou "docente" na descrição para aparecerem aqui.</p>
            </div>
          ) : (
            <table className="data-table">
              <thead><tr><th>Professor / Referência</th><th>Vencimento</th><th>Valor</th><th>Status</th><th>Ações</th></tr></thead>
              <tbody>
                {profDespesas.map((d, i) => {
                  const nome = String(d.aluno || d.nome || d.descricao || `Pagamento ${i + 1}`);
                  const venc = String(d.vencimento || d.data_vencimento || "—");
                  const status = String(d.status || d.situacao || "Pendente");
                  return (
                    <tr key={String(d.id || i)}>
                      <td>
                        <div className="table-name-cell">
                          <span className="table-name-primary">{nome}</span>
                          {String(d.descricao || "") && String(d.descricao) !== nome && <span className="table-name-secondary">{String(d.descricao)}</span>}
                        </div>
                      </td>
                      <td><span style={{ fontWeight: 600 }}>{venc !== "—" ? fmtDate(venc) : "—"}</span></td>
                      <td><span style={{ fontWeight: 700 }}>{formatBRL(parseValor(d.valor))}</span></td>
                      <td><span className={`badge badge-${statusBadge(status)}`}><span className="badge-dot" />{status}</span></td>
                      <td><div style={{ display: "flex", gap: 4 }}><BaixaBtn lancamento={d} tipo="despesas" /><EditarLancamentoBtn lancamento={d} tipo="despesas" /></div></td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </>
  );
}

/* ── Tab: Relatório mensal ── */
function RelatorioTab({ recebimentos, despesas }: { recebimentos: Lancamento[]; despesas: Lancamento[] }) {
  const meses = useMemo(() => {
    const map = new Map<string, { chave: string; mes: string; recebido: number; aReceber: number; totalDespesas: number }>();

    function addEntry(chave: string, date: Date) {
      if (!map.has(chave)) map.set(chave, { chave, mes: date.toLocaleDateString("pt-BR", { month: "long", year: "numeric" }), recebido: 0, aReceber: 0, totalDespesas: 0 });
      return map.get(chave)!;
    }

    for (const r of recebimentos) {
      const v = r.vencimento || r.data_vencimento; if (!v) continue;
      const d = new Date(String(v)); if (isNaN(d.getTime())) continue;
      const chave = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}`;
      const entry = addEntry(chave, d);
      const s = String(r.status || r.situacao || "").toLowerCase();
      if (s.includes("pago") || s.includes("baixado") || s.includes("liquidado")) entry.recebido += parseValor(r.valor);
      else entry.aReceber += parseValor(r.valor);
    }

    for (const d of despesas) {
      const v = d.vencimento || d.data_vencimento; if (!v) continue;
      const dt = new Date(String(v)); if (isNaN(dt.getTime())) continue;
      const chave = `${dt.getFullYear()}-${String(dt.getMonth() + 1).padStart(2, "0")}`;
      addEntry(chave, dt).totalDespesas += parseValor(d.valor);
    }

    return Array.from(map.values()).sort((a, b) => b.chave.localeCompare(a.chave));
  }, [recebimentos, despesas]);

  const totais = meses.reduce((a, m) => ({ rec: a.rec + m.recebido, ar: a.ar + m.aReceber, dep: a.dep + m.totalDespesas }), { rec: 0, ar: 0, dep: 0 });

  return (
    <>
      <div className="metric-grid metric-grid-3">
        <div className="metric-card metric-card-green">
          <div className="metric-icon metric-icon-green"><svg viewBox="0 0 20 20" fill="currentColor"><path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" /></svg></div>
          <div className="metric-label">Total recebido</div>
          <div className="metric-value" style={{ fontSize: "1.5rem" }}>{formatBRL(totais.rec)}</div>
          <div className="metric-note">Todos os períodos</div>
        </div>
        <div className="metric-card metric-card-gold">
          <div className="metric-icon metric-icon-gold"><svg viewBox="0 0 20 20" fill="currentColor"><path d="M4 4a2 2 0 00-2 2v1h16V6a2 2 0 00-2-2H4z" /></svg></div>
          <div className="metric-label">A receber</div>
          <div className="metric-value" style={{ fontSize: "1.5rem" }}>{formatBRL(totais.ar)}</div>
          <div className="metric-note">Em aberto (todos os períodos)</div>
        </div>
        <div className="metric-card metric-card-red">
          <div className="metric-icon metric-icon-red"><svg viewBox="0 0 20 20" fill="currentColor"><path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" /></svg></div>
          <div className="metric-label">Total despesas</div>
          <div className="metric-value" style={{ fontSize: "1.5rem" }}>{formatBRL(totais.dep)}</div>
          <div className="metric-note">Todos os períodos</div>
        </div>
      </div>
      <div className="card">
        <div className="card-header">
          <div>
            <div className="section-eyebrow">Relatório</div>
            <h3 className="section-title">Resumo mensal</h3>
            <p className="section-subtitle">{meses.length} meses com movimentação</p>
          </div>
        </div>
        <div className="card-body" style={{ paddingTop: 12 }}>
          {meses.length === 0 ? (
            <div className="empty-state"><div className="empty-title">Sem dados para relatório</div><p className="empty-desc">Não há lançamentos com datas cadastradas.</p></div>
          ) : (
            <table className="data-table">
              <thead><tr><th>Mês</th><th>Recebido</th><th>A receber</th><th>Despesas</th><th>Saldo</th></tr></thead>
              <tbody>
                {meses.map((m) => {
                  const saldo = m.recebido - m.totalDespesas;
                  return (
                    <tr key={m.chave}>
                      <td style={{ textTransform: "capitalize", fontWeight: 600 }}>{m.mes}</td>
                      <td style={{ color: "var(--green-700)", fontWeight: 700 }}>{formatBRL(m.recebido)}</td>
                      <td style={{ color: "var(--gold-700)" }}>{formatBRL(m.aReceber)}</td>
                      <td style={{ color: "var(--red-700)" }}>{formatBRL(m.totalDespesas)}</td>
                      <td><span style={{ fontWeight: 700, color: saldo >= 0 ? "var(--green-700)" : "var(--red-700)" }}>{formatBRL(saldo)}</span></td>
                    </tr>
                  );
                })}
              </tbody>
              <tfoot>
                <tr>
                  <td style={{ fontWeight: 700 }}>Total geral</td>
                  <td style={{ color: "var(--green-700)", fontWeight: 800 }}>{formatBRL(totais.rec)}</td>
                  <td style={{ color: "var(--gold-700)", fontWeight: 800 }}>{formatBRL(totais.ar)}</td>
                  <td style={{ color: "var(--red-700)", fontWeight: 800 }}>{formatBRL(totais.dep)}</td>
                  <td><span style={{ fontWeight: 800, color: (totais.rec - totais.dep) >= 0 ? "var(--green-700)" : "var(--red-700)" }}>{formatBRL(totais.rec - totais.dep)}</span></td>
                </tr>
              </tfoot>
            </table>
          )}
        </div>
      </div>
    </>
  );
}

/* ── Export principal ── */
export function FinanceiroTable({ recebimentos, despesas }: { recebimentos: Lancamento[]; despesas: Lancamento[] }) {
  const [tab, setTab] = useState<Tab>("recebimentos");

  const tabs: { id: Tab; label: string }[] = [
    { id: "recebimentos", label: "Recebimentos" },
    { id: "despesas", label: "Despesas" },
    { id: "professores", label: "Pagto. Professores" },
    { id: "relatorio", label: "Relatório" },
  ];

  return (
    <>
      <div className="card">
        <div className="card-body" style={{ paddingTop: 16, paddingBottom: 16 }}>
          <div className="tab-bar">
            {tabs.map((t) => (
              <button key={t.id} className={`tab-btn${tab === t.id ? " active" : ""}`} onClick={() => setTab(t.id)}>{t.label}</button>
            ))}
          </div>
        </div>
      </div>
      {tab === "recebimentos" && <RecebimentosTab recebimentos={recebimentos} />}
      {tab === "despesas" && <DespesasTab despesas={despesas} />}
      {tab === "professores" && <ProfessoresTab despesas={despesas} />}
      {tab === "relatorio" && <RelatorioTab recebimentos={recebimentos} despesas={despesas} />}
    </>
  );
}
