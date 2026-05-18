"use client";

import { useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { EditarDesafioBtn } from "./desafio-modal";

function DesafioDeleteBtn({ id, titulo }: { id: string; titulo: string }) {
  const router = useRouter();
  const [saving, setSaving] = useState(false);

  async function excluir() {
    if (!confirm(`Excluir o desafio "${titulo}"? Esta ação não pode ser desfeita.`)) return;
    setSaving(true);
    await fetch(`/api/desafios?id=${encodeURIComponent(id)}`, { method: "DELETE" });
    setSaving(false);
    router.refresh();
  }

  return (
    <button className="btn btn-danger btn-sm" onClick={excluir} disabled={saving} title="Excluir desafio">
      {saving ? "..." : "Excluir"}
    </button>
  );
}

type Desafio = { id?: string; titulo?: string; title?: string; turma?: string; descricao?: string; pontos?: number | string; status?: string; [k: string]: unknown };
type Conclusao = { desafio_id?: string; aluno?: string; pontos?: number | string; [k: string]: unknown };

function statusBadge(status: string) {
  const l = status.toLowerCase();
  if (l.includes("rascunho")) return "neutral";
  if (l.includes("arquiv")) return "neutral";
  return "success";
}

export function DesafiosTable({ desafios, conclusoes }: { desafios: Desafio[]; conclusoes: Conclusao[] }) {
  const [busca, setBusca] = useState("");

  const filtrados = useMemo(() => {
    if (!busca.trim()) return desafios;
    const q = busca.toLowerCase();
    return desafios.filter((d) =>
      String(d.titulo || d.title || "").toLowerCase().includes(q) ||
      String(d.turma || "").toLowerCase().includes(q) ||
      String(d.descricao || "").toLowerCase().includes(q)
    );
  }, [desafios, busca]);

  return (
    <div className="card">
      <div className="card-header">
        <div>
          <div className="section-eyebrow">Conteúdo</div>
          <h3 className="section-title">Desafios publicados</h3>
          <p className="section-subtitle">{filtrados.length} de {desafios.length}</p>
        </div>
        <div className="search-bar">
          <span className="search-icon">
            <svg viewBox="0 0 20 20" fill="currentColor">
              <path fillRule="evenodd" d="M8 4a4 4 0 100 8 4 4 0 000-8zM2 8a6 6 0 1110.89 3.476l4.817 4.817a1 1 0 01-1.414 1.414l-4.816-4.816A6 6 0 012 8z" clipRule="evenodd" />
            </svg>
          </span>
          <input
            className="search-input"
            placeholder="Buscar desafio ou turma..."
            value={busca}
            onChange={(e) => setBusca(e.target.value)}
            style={{ minWidth: "200px" }}
          />
        </div>
      </div>
      <div className="card-body" style={{ paddingTop: "12px" }}>
        {desafios.length === 0 ? (
          <div className="empty-state">
            <div className="empty-icon">
              <svg viewBox="0 0 20 20" fill="currentColor">
                <path d="M9 2a1 1 0 000 2h2a1 1 0 100-2H9z" />
                <path fillRule="evenodd" d="M4 5a2 2 0 012-2 3 3 0 003 3h2a3 3 0 003-3 2 2 0 012 2v11a2 2 0 01-2 2H6a2 2 0 01-2-2V5z" clipRule="evenodd" />
              </svg>
            </div>
            <div className="empty-title">Nenhum desafio cadastrado</div>
            <p className="empty-desc">Crie um novo desafio para os alunos usando o botão acima.</p>
          </div>
        ) : filtrados.length === 0 ? (
          <div className="empty-state">
            <div className="empty-title">Nenhum resultado para "{busca}"</div>
            <p className="empty-desc">Tente outro termo de busca.</p>
          </div>
        ) : (
          <table className="data-table">
            <thead>
              <tr>
                <th>Desafio</th>
                <th>Turma</th>
                <th>Pontos</th>
                <th>Status</th>
                <th>Conclusões</th>
                <th>Ações</th>
              </tr>
            </thead>
            <tbody>
              {filtrados.map((d, i) => {
                const titulo = String(d.titulo || d.title || `Desafio ${i + 1}`);
                const turma = String(d.turma || "Todas");
                const pontos = Number(d.pontos) || 0;
                const status = String(d.status || "Publicado");
                const nConclusoes = conclusoes.filter((c) => c.desafio_id === (d.id || titulo)).length;
                return (
                  <tr key={String(d.id || i)}>
                    <td>
                      <div className="table-name-cell">
                        <span className="table-name-primary">{titulo}</span>
                        {d.descricao && (
                          <span className="table-name-secondary">
                            {String(d.descricao).slice(0, 60)}{String(d.descricao).length > 60 ? "…" : ""}
                          </span>
                        )}
                      </div>
                    </td>
                    <td>{turma}</td>
                    <td><span className="badge badge-gold">{pontos} pts</span></td>
                    <td>
                      <span className={`badge badge-${statusBadge(status)}`}>
                        <span className="badge-dot" />{status}
                      </span>
                    </td>
                    <td style={{ fontWeight: 600 }}>{nConclusoes}</td>
                    <td>
                      <div style={{ display: "flex", gap: 4 }}>
                        <EditarDesafioBtn desafio={d} />
                        <DesafioDeleteBtn id={String(d.id || titulo)} titulo={titulo} />
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
  );
}
