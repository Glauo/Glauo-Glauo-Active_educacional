import { AppShell } from "@/components/app-shell";
import { dbList } from "@/lib/db";
import { getSession } from "@/lib/auth";
import { redirect } from "next/navigation";
import { LancarEntradaBtn, NovoItemEstoqueBtn } from "@/components/estoque-modals";

type ItemEstoque = { id?: string; nome?: string; name?: string; categoria?: string; quantidade?: number | string; quantidade_minima?: string | number; preco?: number | string; [k: string]: unknown };
type MovimentoEstoque = { id?: string; item?: string; tipo?: string; quantidade?: number | string; data?: string; [k: string]: unknown };

export default async function EstoquePage() {
  const session = await getSession();
  if (!session) redirect("/login");

  const [estoque, movimentos, pedidos] = await Promise.all([
    dbList<ItemEstoque>("inventory.json"),
    dbList<MovimentoEstoque>("inventory_moves.json"),
    dbList<Record<string, unknown>>("material_orders.json")
  ]);

  const abaixoMinimo = estoque.filter((item) => {
    const qtd = Number(item.quantidade) || 0;
    const min = Number(item.quantidade_minima) || 0;
    return min > 0 && qtd < min;
  });

  const totalItens = estoque.reduce((acc, item) => acc + (Number(item.quantidade) || 0), 0);

  return (
    <AppShell breadcrumb="Estoque" userName={session.pessoa || session.usuario} userRole={session.perfil}>
      <div className="page-header">
        <div className="page-title-block">
          <div className="page-eyebrow"><span className="page-eyebrow-dot" />Gestão Operacional</div>
          <h1 className="page-title">Estoque</h1>
          <p className="page-description">Controle de materiais, apostilas e itens operacionais da escola.</p>
        </div>
        <div className="page-actions">
          <NovoItemEstoqueBtn />
          <LancarEntradaBtn itens={estoque} />
        </div>
      </div>

      <div className="metric-grid metric-grid-4">
        <div className="metric-card metric-card-blue">
          <div className="metric-icon metric-icon-blue">
            <svg viewBox="0 0 20 20" fill="currentColor"><path d="M5 3a2 2 0 00-2 2v2a2 2 0 002 2h2a2 2 0 002-2V5a2 2 0 00-2-2H5zM5 11a2 2 0 00-2 2v2a2 2 0 002 2h2a2 2 0 002-2v-2a2 2 0 00-2-2H5zM11 5a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2V5zM14 11a1 1 0 011 1v1h1a1 1 0 110 2h-1v1a1 1 0 11-2 0v-1h-1a1 1 0 110-2h1v-1a1 1 0 011-1z" /></svg>
          </div>
          <div className="metric-label">Itens cadastrados</div>
          <div className="metric-value">{estoque.length}</div>
          <div className="metric-note">{totalItens} unidades no total</div>
        </div>
        <div className="metric-card metric-card-red">
          <div className="metric-icon metric-icon-red">
            <svg viewBox="0 0 20 20" fill="currentColor"><path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" /></svg>
          </div>
          <div className="metric-label">Abaixo do mínimo</div>
          <div className="metric-value">{abaixoMinimo.length}</div>
          <div className="metric-note">Precisam de reposição</div>
        </div>
        <div className="metric-card metric-card-green">
          <div className="metric-icon metric-icon-green">
            <svg viewBox="0 0 20 20" fill="currentColor"><path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" /></svg>
          </div>
          <div className="metric-label">Movimentos</div>
          <div className="metric-value">{movimentos.length}</div>
          <div className="metric-note">Entradas e saídas registradas</div>
        </div>
        <div className="metric-card metric-card-gold">
          <div className="metric-icon metric-icon-gold">
            <svg viewBox="0 0 20 20" fill="currentColor"><path d="M9 2a1 1 0 000 2h2a1 1 0 100-2H9z" /><path fillRule="evenodd" d="M4 5a2 2 0 012-2 3 3 0 003 3h2a3 3 0 003-3 2 2 0 012 2v11a2 2 0 01-2 2H6a2 2 0 01-2-2V5zm3 4a1 1 0 000 2h.01a1 1 0 100-2H7zm3 0a1 1 0 000 2h3a1 1 0 100-2h-3zm-3 4a1 1 0 100 2h.01a1 1 0 100-2H7zm3 0a1 1 0 100 2h3a1 1 0 100-2h-3z" clipRule="evenodd" /></svg>
          </div>
          <div className="metric-label">Pedidos</div>
          <div className="metric-value">{pedidos.length}</div>
          <div className="metric-note">Pedidos de material registrados</div>
        </div>
      </div>

      {abaixoMinimo.length > 0 && (
        <div className="card" style={{ borderColor: "rgba(239,68,68,0.2)", background: "rgba(239,68,68,0.03)" }}>
          <div className="card-body">
            <div style={{ display: "flex", alignItems: "center", gap: "12px", marginBottom: "16px" }}>
              <div className="alert-icon alert-icon-danger">
                <svg viewBox="0 0 20 20" fill="currentColor"><path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" /></svg>
              </div>
              <div>
                <div className="section-title" style={{ color: "var(--red-700)" }}>Itens com estoque crítico</div>
                <div className="section-subtitle">{abaixoMinimo.length} itens abaixo do mínimo definido</div>
              </div>
            </div>
            <div className="alert-list">
              {abaixoMinimo.map((item, i) => (
                <div className="alert-item" key={String(item.id || i)}>
                  <div className="alert-icon alert-icon-danger">
                    <svg viewBox="0 0 20 20" fill="currentColor"><path d="M5 3a2 2 0 00-2 2v2a2 2 0 002 2h2a2 2 0 002-2V5a2 2 0 00-2-2H5z" /></svg>
                  </div>
                  <div className="alert-body">
                    <div className="alert-title">{String(item.nome || item.name || `Item ${i + 1}`)}</div>
                    <div className="alert-text">
                      Estoque atual: <strong>{Number(item.quantidade)}</strong> — Mínimo: <strong>{Number(item.quantidade_minima)}</strong>
                    </div>
                  </div>
                  <button className="btn btn-secondary btn-sm">Pedir</button>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      <div className="card">
        <div className="card-header">
          <div>
            <div className="section-eyebrow">Inventário</div>
            <h3 className="section-title">Todos os itens</h3>
            <p className="section-subtitle">{estoque.length} itens cadastrados</p>
          </div>
          <div className="search-bar">
            <span className="search-icon"><svg viewBox="0 0 20 20" fill="currentColor"><path fillRule="evenodd" d="M8 4a4 4 0 100 8 4 4 0 000-8zM2 8a6 6 0 1110.89 3.476l4.817 4.817a1 1 0 01-1.414 1.414l-4.816-4.816A6 6 0 012 8z" clipRule="evenodd" /></svg></span>
            <input className="search-input" placeholder="Buscar item ou categoria..." />
          </div>
        </div>
        <div className="card-body" style={{ paddingTop: "12px" }}>
          {estoque.length === 0 ? (
            <div className="empty-state">
              <div className="empty-icon"><svg viewBox="0 0 20 20" fill="currentColor"><path d="M5 3a2 2 0 00-2 2v2a2 2 0 002 2h2a2 2 0 002-2V5a2 2 0 00-2-2H5zM5 11a2 2 0 00-2 2v2a2 2 0 002 2h2a2 2 0 002-2v-2a2 2 0 00-2-2H5z" /></svg></div>
              <div className="empty-title">Estoque vazio</div>
              <p className="empty-desc">Lance entradas de material ou configure a URL do banco para carregar o estoque do Streamlit.</p>
            </div>
          ) : (
            <table className="data-table">
              <thead>
                <tr><th>Item</th><th>Categoria</th><th>Quantidade</th><th>Mínimo</th><th>Status</th><th>Ações</th></tr>
              </thead>
              <tbody>
                {estoque.map((item, i) => {
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
    </AppShell>
  );
}
