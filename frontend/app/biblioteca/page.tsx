import { AppShell } from "@/components/app-shell";
import { dbList } from "@/lib/db";
import { getSession } from "@/lib/auth";
import { redirect } from "next/navigation";
import { AdicionarLivroBtn, AdicionarVideoBtn } from "@/components/biblioteca-modal";

type Livro = { id?: string; titulo?: string; title?: string; autor?: string; author?: string; nivel?: string; nivel_livro?: string; turma?: string; categoria?: string; tipo?: string; url?: string; file_path?: string; status?: string; [k: string]: unknown };
type Video = { id?: string; titulo?: string; title?: string; turma?: string; url?: string; descricao?: string; [k: string]: unknown };

export default async function BibliotecaPage() {
  const session = await getSession();
  if (!session) redirect("/login");

  const [livros, videos, materiais] = await Promise.all([
    dbList<Livro>("books.json"),
    dbList<Video>("videos.json"),
    dbList<Record<string, unknown>>("materials.json")
  ]);

  const categorias = [...new Set(livros.map((l) => String(l.categoria || l.tipo || l.nivel || "Geral")))];

  return (
    <AppShell breadcrumb="Biblioteca" userName={session.pessoa || session.usuario} userRole={session.perfil}>
      <div className="page-header">
        <div className="page-title-block">
          <div className="page-eyebrow"><span className="page-eyebrow-dot" />Recursos Pedagógicos</div>
          <h1 className="page-title">Biblioteca</h1>
          <p className="page-description">Livros didáticos, vídeos e materiais de apoio organizados por turma e nível.</p>
        </div>
        <div className="page-actions">
          <AdicionarVideoBtn />
          <AdicionarLivroBtn />
        </div>
      </div>

      <div className="metric-grid metric-grid-3">
        <div className="metric-card metric-card-blue">
          <div className="metric-icon metric-icon-blue">
            <svg viewBox="0 0 20 20" fill="currentColor"><path d="M9 4.804A7.968 7.968 0 005.5 4c-1.255 0-2.443.29-3.5.804v10A7.969 7.969 0 015.5 14c1.669 0 3.218.51 4.5 1.385A7.962 7.962 0 0114.5 14c1.255 0 2.443.29 3.5.804v-10A7.968 7.968 0 0014.5 4c-1.255 0-2.443.29-3.5.804V12a1 1 0 11-2 0V4.804z" /></svg>
          </div>
          <div className="metric-label">Livros cadastrados</div>
          <div className="metric-value">{livros.length}</div>
          <div className="metric-note">{categorias.length} categorias diferentes</div>
        </div>
        <div className="metric-card metric-card-green">
          <div className="metric-icon metric-icon-green">
            <svg viewBox="0 0 20 20" fill="currentColor"><path d="M2 6a2 2 0 012-2h6a2 2 0 012 2v8a2 2 0 01-2 2H4a2 2 0 01-2-2V6zM14.553 7.106A1 1 0 0014 8v4a1 1 0 00.553.894l2 1A1 1 0 0018 13V7a1 1 0 00-1.447-.894l-2 1z" /></svg>
          </div>
          <div className="metric-label">Vídeos</div>
          <div className="metric-value">{videos.length}</div>
          <div className="metric-note">Aulas e conteúdos em vídeo</div>
        </div>
        <div className="metric-card metric-card-gold">
          <div className="metric-icon metric-icon-gold">
            <svg viewBox="0 0 20 20" fill="currentColor"><path fillRule="evenodd" d="M4 4a2 2 0 012-2h4.586A2 2 0 0112 2.586L15.414 6A2 2 0 0116 7.414V16a2 2 0 01-2 2H6a2 2 0 01-2-2V4zm2 6a1 1 0 011-1h6a1 1 0 110 2H7a1 1 0 01-1-1zm1 3a1 1 0 100 2h6a1 1 0 100-2H7z" clipRule="evenodd" /></svg>
          </div>
          <div className="metric-label">Materiais</div>
          <div className="metric-value">{materiais.length}</div>
          <div className="metric-note">Apostilas e arquivos de apoio</div>
        </div>
      </div>

      {/* Abas de conteúdo */}
      <div className="card">
        <div className="card-header">
          <div>
            <div className="section-eyebrow">Acervo</div>
            <h3 className="section-title">Livros didáticos</h3>
            <p className="section-subtitle">{livros.length} títulos cadastrados</p>
          </div>
          <div className="toolbar-right">
            <select className="filter-select">
              <option>Todas as categorias</option>
              {categorias.map((c) => <option key={c}>{c}</option>)}
            </select>
            <div className="search-bar">
              <span className="search-icon"><svg viewBox="0 0 20 20" fill="currentColor"><path fillRule="evenodd" d="M8 4a4 4 0 100 8 4 4 0 000-8zM2 8a6 6 0 1110.89 3.476l4.817 4.817a1 1 0 01-1.414 1.414l-4.816-4.816A6 6 0 012 8z" clipRule="evenodd" /></svg></span>
              <input className="search-input" placeholder="Buscar livro ou autor..." style={{ minWidth: "180px" }} />
            </div>
          </div>
        </div>
        <div className="card-body" style={{ paddingTop: "12px" }}>
          {livros.length === 0 ? (
            <div className="empty-state">
              <div className="empty-icon"><svg viewBox="0 0 20 20" fill="currentColor"><path d="M9 4.804A7.968 7.968 0 005.5 4c-1.255 0-2.443.29-3.5.804v10A7.969 7.969 0 015.5 14c1.669 0 3.218.51 4.5 1.385A7.962 7.962 0 0114.5 14c1.255 0 2.443.29 3.5.804v-10A7.968 7.968 0 0014.5 4c-1.255 0-2.443.29-3.5.804V12a1 1 0 11-2 0V4.804z" /></svg></div>
              <div className="empty-title">Nenhum livro cadastrado</div>
              <p className="empty-desc">Adicione livros didáticos ou importe do sistema Streamlit via banco de dados.</p>
            </div>
          ) : (
            <div className="entity-grid">
              {livros.map((l, i) => {
                const titulo = String(l.titulo || l.title || `Livro ${i + 1}`);
                const autor = String(l.autor || l.author || "—");
                const nivel = String(l.nivel || l.nivel_livro || l.categoria || "Geral");
                const turma = String(l.turma || "Todas");
                const temArquivo = Boolean(l.url || l.file_path);
                return (
                  <div className="entity-card" key={String(l.id || i)}>
                    <div className="entity-card-top">
                      <div style={{ display: "flex", alignItems: "center", gap: "12px", flex: 1 }}>
                        <div style={{ width: "40px", height: "40px", borderRadius: "var(--radius-md)", background: "linear-gradient(135deg, var(--blue-500), var(--navy-600))", display: "grid", placeItems: "center", flexShrink: 0 }}>
                          <svg width="20" height="20" viewBox="0 0 20 20" fill="white"><path d="M9 4.804A7.968 7.968 0 005.5 4c-1.255 0-2.443.29-3.5.804v10A7.969 7.969 0 015.5 14c1.669 0 3.218.51 4.5 1.385A7.962 7.962 0 0114.5 14c1.255 0 2.443.29 3.5.804v-10A7.968 7.968 0 0014.5 4c-1.255 0-2.443.29-3.5.804V12a1 1 0 11-2 0V4.804z" /></svg>
                        </div>
                        <div className="entity-card-info">
                          <div className="entity-card-name">{titulo}</div>
                          <div className="entity-card-sub">{autor}</div>
                        </div>
                      </div>
                      {temArquivo && (
                        <span className="badge badge-success"><span className="badge-dot" />PDF</span>
                      )}
                    </div>
                    <div className="entity-card-rows">
                      <div className="entity-card-row">
                        <span className="entity-card-row-label">Nível</span>
                        <span className="entity-card-row-value">{nivel}</span>
                      </div>
                      <div className="entity-card-row">
                        <span className="entity-card-row-label">Turma</span>
                        <span className="entity-card-row-value">{turma}</span>
                      </div>
                    </div>
                    <div style={{ marginTop: "12px", display: "flex", gap: "6px" }}>
                      {temArquivo && (
                        <a href={String(l.url || l.file_path)} target="_blank" rel="noopener noreferrer" className="btn btn-primary btn-sm" style={{ flex: 1 }}>Baixar</a>
                      )}
                      <AdicionarLivroBtn livro={l} />
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </div>

      {/* Vídeos */}
      {videos.length > 0 && (
        <div className="card">
          <div className="card-header">
            <div>
              <div className="section-eyebrow">Mídia</div>
              <h3 className="section-title">Vídeos e aulas gravadas</h3>
            </div>
            <AdicionarVideoBtn />
          </div>
          <div className="card-body" style={{ paddingTop: "12px" }}>
            <table className="data-table">
              <thead>
                <tr><th>Título</th><th>Turma</th><th>Link</th></tr>
              </thead>
              <tbody>
                {videos.slice(0, 20).map((v, i) => (
                  <tr key={String(v.id || i)}>
                    <td>
                      <div className="table-name-cell">
                        <span className="table-name-primary">{String(v.titulo || v.title || `Vídeo ${i + 1}`)}</span>
                        {(v.descricao as string | undefined) && <span className="table-name-secondary">{String(v.descricao).slice(0, 60)}</span>}
                      </div>
                    </td>
                    <td>{String(v.turma || "—")}</td>
                    <td>
                      {(v.url as string | undefined) ? (
                        <a href={String(v.url)} target="_blank" rel="noopener noreferrer" className="btn btn-ghost btn-sm">
                          <svg viewBox="0 0 20 20" fill="currentColor"><path d="M11 3a1 1 0 100 2h2.586l-6.293 6.293a1 1 0 101.414 1.414L15 6.414V9a1 1 0 102 0V4a1 1 0 00-1-1h-5z" /><path d="M5 5a2 2 0 00-2 2v8a2 2 0 002 2h8a2 2 0 002-2v-3a1 1 0 10-2 0v3H5V7h3a1 1 0 000-2H5z" /></svg>
                          Abrir
                        </a>
                      ) : <span className="text-muted text-sm">—</span>}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </AppShell>
  );
}
