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
  status?: string;
  situacao?: string;
  codigo?: string;
  [k: string]: unknown;
};

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

function isMesAtual(venc: string): boolean {
  const d = new Date(venc);
  const now = new Date();
  return d.getMonth() === now.getMonth() && d.getFullYear() === now.getFullYear();
}

function isMesPassado(venc: string): boolean {
  const d = new Date(venc);
  const now = new Date();
  const mp = new Date(now.getFullYear(), now.getMonth() - 1, 1);
  return d.getMonth() === mp.getMonth() && d.getFullYear() === mp.getFullYear();
}

export function FinanceiroTable({ recebimentos }: { recebimentos: Lancamento[] }) {
  const [busca, setBusca] = useState("");
  const [filtroStatus, setFiltroStatus] = useState("Todos");
  const [filtroPeriodo, setFiltroPeriodo] = useState("Todos");

  const filtrados = useMemo(() => {
    return recebimentos.filter((r) => {
      const nome = String(r.aluno || r.nome || r.descricao || "").toLowerCase();
      const codigo = String(r.codigo || "").toLowerCase();
      const status = String(r.status || r.situacao || "Pendente");
      const venc = String(r.vencimento || r.data_vencimento || "");

      const matchBusca = !busca || nome.includes(busca.toLowerCase()) || codigo.includes(busca.toLowerCase());

      const matchStatus = filtroStatus === "Todos" ||
        (filtroStatus === "Em aberto" && statusBadge(status) !== "success") ||
        (filtroStatus === "Pago" && statusBadge(status) === "success") ||
        (filtroStatus === "Atrasado" && statusBadge(status) === "danger");

      const matchPeriodo = filtroPeriodo === "Todos" ||
        (filtroPeriodo === "Este mês" && venc && isMesAtual(venc)) ||
        (filtroPeriodo === "Mês passado" && venc && isMesPassado(venc));

      return matchBusca && matchStatus && matchPeriodo;
    });
  }, [recebimentos, busca, filtroStatus, filtroPeriodo]);

  return (
    <>
      <div className="card">
        <div className="toolbar">
          <div className="toolbar-left">
            <div className="search-bar">
              <span className="search-icon">
                <svg viewBox="0 0 20 20" fill="currentColor"><path fillRule="evenodd" d="M8 4a4 4 0 100 8 4 4 0 000-8zM2 8a6 6 0 1110.89 3.476l4.817 4.817a1 1 0 01-1.414 1.414l-4.816-4.816A6 6 0 012 8z" clipRule="evenodd" /></svg>
              </span>
              <input className="search-input" placeholder="Buscar aluno, código ou descrição..." value={busca} onChange={(e) => setBusca(e.target.value)} />
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
            <h3 className="section-title">Fila de lançamentos</h3>
            <p className="section-subtitle">
              {filtrados.length === recebimentos.length
                ? `${recebimentos.length} lançamentos no total`
                : `${filtrados.length} de ${recebimentos.length} (filtro ativo)`}
            </p>
          </div>
          <div style={{ textAlign: "right" }}>
            <div style={{ fontSize: "0.75rem", color: "var(--text-muted)", marginBottom: "2px" }}>Total filtrado</div>
            <div style={{ fontWeight: 700, fontSize: "1rem", color: "var(--text-primary)" }}>
              {formatBRL(filtrados.reduce((acc, r) => acc + parseValor(r.valor), 0))}
            </div>
          </div>
        </div>
        <div className="card-body" style={{ paddingTop: "12px" }}>
          {filtrados.length === 0 ? (
            <div className="empty-state">
              <div className="empty-title">Nenhum lançamento encontrado</div>
              <p className="empty-desc">Ajuste os filtros para ver mais resultados.</p>
            </div>
          ) : (
            <table className="data-table">
              <thead>
                <tr>
                  <th>Aluno / Descrição</th>
                  <th>Vencimento</th>
                  <th>Valor</th>
                  <th>Status</th>
                  <th>Ações</th>
                </tr>
              </thead>
              <tbody>
                {filtrados.map((r, i) => {
                  const nome = String(r.aluno || r.nome || r.descricao || `Lançamento ${i + 1}`);
                  const venc = String(r.vencimento || r.data_vencimento || "—");
                  const valor = parseValor(r.valor);
                  const status = String(r.status || r.situacao || "Pendente");
                  const vencFormatado = venc !== "—" ? (() => { try { return new Date(venc).toLocaleDateString("pt-BR"); } catch { return venc; } })() : "—";
                  const atrasado = venc !== "—" && statusBadge(status) !== "success" && new Date(venc) < new Date();
                  return (
                    <tr key={String(r.id || i)}>
                      <td>
                        <div className="table-name-cell">
                          <span className="table-name-primary">{nome}</span>
                          {r.codigo && <span className="table-name-secondary">{String(r.codigo)}</span>}
                          {(r.descricao as string | undefined) && String(r.descricao) !== nome && (
                            <span className="table-name-secondary">{String(r.descricao)}</span>
                          )}
                        </div>
                      </td>
                      <td>
                        <span style={{ fontWeight: 600, fontSize: "0.875rem", color: atrasado ? "var(--red-600)" : "inherit" }}>
                          {vencFormatado}
                          {atrasado && " ⚠"}
                        </span>
                      </td>
                      <td>
                        <span style={{ fontWeight: 700, fontSize: "0.9375rem" }}>{formatBRL(valor)}</span>
                      </td>
                      <td>
                        <span className={`badge badge-${statusBadge(status)}`}>
                          <span className="badge-dot" />{status}
                        </span>
                      </td>
                      <td>
                        <div style={{ display: "flex", gap: "4px" }}>
                          <BaixaBtn lancamento={r} tipo="recebimentos" />
                          <EditarLancamentoBtn lancamento={r} tipo="recebimentos" />
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
    </>
  );
}
