"use client";

import { useState, useMemo } from "react";
import { LancarEntradaBtn } from "./estoque-modals";

type ItemEstoque = {
  id?: string;
  nome?: string;
  name?: string;
  categoria?: string;
  quantidade?: number | string;
  quantidade_minima?: string | number;
  preco?: number | string;
  [k: string]: unknown;
};

type MovimentoEstoque = {
  id?: string;
  item?: string;
  tipo?: string;
  quantidade?: number | string;
  data?: string;
  responsavel?: string;
  observacao?: string;
  [k: string]: unknown;
};

type Pedido = {
  id?: string;
  item?: string;
  quantidade?: number | string;
  status?: string;
  data?: string;
  fornecedor?: string;
  [k: string]: unknown;
};

type Tab = "inventario" | "movimentos" | "pedidos";

function formatPreco(v: unknown): string {
  const n = parseFloat(String(v || "0").replace(/[^\d.,]/g, "").replace(",", "."));
  if (!n) return "—";
  return n.toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
}

function formatData(d: unknown): string {
  if (!d) return "—";
  const s = String(d);
  try {
    return new Date(s).toLocaleDateString("pt-BR");
  } catch {
    return s;
  }
}

function tipoBadge(tipo: string) {
  const l = tipo.toLowerCase();
  if (l.includes("saída") || l.includes("saida") || l.includes("saiu")) return "danger";
  if (l.includes("entrada") || l.includes("entrou")) return "success";
  return "neutral";
}

function pedidoBadge(status: string) {
  const l = status.toLowerCase();
  if (l.includes("entregue") || l.includes("concluído") || l.includes("concluido")) return "success";
  if (l.includes("cancel")) return "neutral";
  if (l.includes("andamento") || l.includes("pendente")) return "warning";
  return "neutral";
}

function InventarioTab({ estoque }: { estoque: ItemEstoque[] }) {
  const [busca, setBusca] = useState("");

  const filtrados = useMemo(() => {
    if (!busca) return estoque;
    const q = busca.toLowerCase();
    return estoque.filter((item) =>
      String(item.nome || item.name || "").toLowerCase().includes(q) ||
      String(item.categoria || "").toLowerCase().includes(q)
    );
  }, [estoque, busca]);

  return (
    <div className="card">
      <div className="card-header">
        <div>
          <div className="section-eyebrow">Inventário</div>
          <h3 className="section-title">Todos os itens</h3>
          <p className="section-subtitle">{filtrados.length} de {estoque.length} itens</p>
        </div>
        <div className="search-bar">
          <span className="search-icon">
            <svg viewBox="0 0 20 20" fill="currentColor">
              <path fillRule="evenodd" d="M8 4a4 4 0 100 8 4 4 0 000-8zM2 8a6 6 0 1110.89 3.476l4.817 4.817a1 1 0 01-1.414 1.414l-4.816-4.816A6 6 0 012 8z" clipRule="evenodd" />
            </svg>
          </span>
          <input
            className="search-input"
            placeholder="Buscar item ou categoria..."
            value={busca}
            onChange={(e) => setBusca(e.target.value)}
          />
        </div>
      </div>
      <div className="card-body" style={{ paddingTop: "12px" }}>
        {estoque.length === 0 ? (
          <div className="empty-state">
            <div className="empty-icon">
              <svg viewBox="0 0 20 20" fill="currentColor">
                <path d="M5 3a2 2 0 00-2 2v2a2 2 0 002 2h2a2 2 0 002-2V5a2 2 0 00-2-2H5zM5 11a2 2 0 00-2 2v2a2 2 0 002 2h2a2 2 0 002-2v-2a2 2 0 00-2-2H5z" />
              </svg>
            </div>
            <div className="empty-title">Estoque vazio</div>
            <p className="empty-desc">Lance entradas de material para popular o inventário.</p>
          </div>
        ) : (
          <table className="data-table">
            <thead>
              <tr>
                <th>Item</th>
                <th>Categoria</th>
                <th>Quantidade</th>
                <th>Mínimo</th>
                <th>Preço</th>
                <th>Status</th>
                <th>Ações</th>
              </tr>
            </thead>
            <tbody>
              {filtrados.map((item, i) => {
                const nome = String(item.nome || item.name || `Item ${i + 1}`);
                const cat = String(item.categoria || "—");
                const qtd = Number(item.quantidade) || 0;
                const min = Number(item.quantidade_minima) || 0;
                const critico = min > 0 && qtd < min;
                return (
                  <tr key={String(item.id || i)}>
                    <td><span style={{ fontWeight: 600 }}>{nome}</span></td>
                    <td>{cat}</td>
                    <td style={{ fontWeight: 700, fontSize: "1rem" }}>{qtd}</td>
                    <td style={{ color: "var(--text-muted)" }}>{min || "—"}</td>
                    <td>{formatPreco(item.preco)}</td>
                    <td>
                      <span className={`badge badge-${critico ? "danger" : "success"}`}>
                        <span className="badge-dot" />{critico ? "Crítico" : "Regular"}
                      </span>
                    </td>
                    <td>
                      <LancarEntradaBtn itens={[item]} />
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}

function MovimentosTab({ movimentos }: { movimentos: MovimentoEstoque[] }) {
  return (
    <div className="card">
      <div className="card-header">
        <div>
          <div className="section-eyebrow">Histórico</div>
          <h3 className="section-title">Movimentos de Estoque</h3>
          <p className="section-subtitle">{movimentos.length} registros</p>
        </div>
      </div>
      <div className="card-body" style={{ paddingTop: "12px" }}>
        {movimentos.length === 0 ? (
          <div className="empty-state">
            <div className="empty-icon">
              <svg viewBox="0 0 20 20" fill="currentColor">
                <path fillRule="evenodd" d="M3 3a1 1 0 011-1h12a1 1 0 011 1v3a1 1 0 01-.293.707L12 11.414V15a1 1 0 01-.293.707l-2 2A1 1 0 018 17v-5.586L3.293 6.707A1 1 0 013 6V3z" clipRule="evenodd" />
              </svg>
            </div>
            <div className="empty-title">Nenhum movimento registrado</div>
            <p className="empty-desc">As entradas e saídas de materiais aparecerão aqui.</p>
          </div>
        ) : (
          <table className="data-table">
            <thead>
              <tr>
                <th>Data</th>
                <th>Item</th>
                <th>Tipo</th>
                <th>Quantidade</th>
                <th>Responsável</th>
                <th>Observação</th>
              </tr>
            </thead>
            <tbody>
              {[...movimentos].reverse().map((mv, i) => {
                const tipo = String(mv.tipo || "Movimento");
                return (
                  <tr key={String(mv.id || i)}>
                    <td style={{ color: "var(--text-muted)", fontSize: "0.875rem" }}>{formatData(mv.data)}</td>
                    <td><span style={{ fontWeight: 600 }}>{String(mv.item || "—")}</span></td>
                    <td>
                      <span className={`badge badge-${tipoBadge(tipo)}`}>
                        <span className="badge-dot" />{tipo}
                      </span>
                    </td>
                    <td style={{ fontWeight: 700 }}>{Number(mv.quantidade) || "—"}</td>
                    <td>{String(mv.responsavel || "—")}</td>
                    <td style={{ color: "var(--text-muted)", fontSize: "0.875rem" }}>{String(mv.observacao || "—")}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}

function PedidosTab({ pedidos }: { pedidos: Pedido[] }) {
  return (
    <div className="card">
      <div className="card-header">
        <div>
          <div className="section-eyebrow">Compras</div>
          <h3 className="section-title">Pedidos de Material</h3>
          <p className="section-subtitle">{pedidos.length} pedidos registrados</p>
        </div>
      </div>
      <div className="card-body" style={{ paddingTop: "12px" }}>
        {pedidos.length === 0 ? (
          <div className="empty-state">
            <div className="empty-icon">
              <svg viewBox="0 0 20 20" fill="currentColor">
                <path d="M9 2a1 1 0 000 2h2a1 1 0 100-2H9z" />
                <path fillRule="evenodd" d="M4 5a2 2 0 012-2 3 3 0 003 3h2a3 3 0 003-3 2 2 0 012 2v11a2 2 0 01-2 2H6a2 2 0 01-2-2V5zm3 4a1 1 0 000 2h.01a1 1 0 100-2H7zm3 0a1 1 0 000 2h3a1 1 0 100-2h-3zm-3 4a1 1 0 100 2h.01a1 1 0 100-2H7zm3 0a1 1 0 100 2h3a1 1 0 100-2h-3z" clipRule="evenodd" />
              </svg>
            </div>
            <div className="empty-title">Nenhum pedido registrado</div>
            <p className="empty-desc">Pedidos de reposição de material aparecerão aqui.</p>
          </div>
        ) : (
          <table className="data-table">
            <thead>
              <tr>
                <th>Data</th>
                <th>Item</th>
                <th>Quantidade</th>
                <th>Fornecedor</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {pedidos.map((p, i) => {
                const status = String(p.status || "Pendente");
                return (
                  <tr key={String(p.id || i)}>
                    <td style={{ color: "var(--text-muted)", fontSize: "0.875rem" }}>{formatData(p.data)}</td>
                    <td><span style={{ fontWeight: 600 }}>{String(p.item || "—")}</span></td>
                    <td style={{ fontWeight: 700 }}>{Number(p.quantidade) || "—"}</td>
                    <td>{String(p.fornecedor || "—")}</td>
                    <td>
                      <span className={`badge badge-${pedidoBadge(status)}`}>
                        <span className="badge-dot" />{status}
                      </span>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}

export function EstoqueTabView({
  estoque,
  movimentos,
  pedidos,
}: {
  estoque: ItemEstoque[];
  movimentos: MovimentoEstoque[];
  pedidos: Pedido[];
}) {
  const [tab, setTab] = useState<Tab>("inventario");

  const tabs: { id: Tab; label: string; count: number }[] = [
    { id: "inventario", label: "Inventário", count: estoque.length },
    { id: "movimentos", label: "Movimentos", count: movimentos.length },
    { id: "pedidos", label: "Pedidos", count: pedidos.length },
  ];

  return (
    <div>
      <div className="tab-bar" style={{ marginBottom: "20px" }}>
        {tabs.map((t) => (
          <button
            key={t.id}
            className={`tab-btn${tab === t.id ? " active" : ""}`}
            onClick={() => setTab(t.id)}
          >
            {t.label}
            <span className="tab-count">{t.count}</span>
          </button>
        ))}
      </div>

      {tab === "inventario" && <InventarioTab estoque={estoque} />}
      {tab === "movimentos" && <MovimentosTab movimentos={movimentos} />}
      {tab === "pedidos" && <PedidosTab pedidos={pedidos} />}
    </div>
  );
}
