"use client";

import { useState, useMemo } from "react";
import { EditarAlunoBtn } from "./aluno-modal";

type Aluno = {
  id?: string;
  nome?: string;
  name?: string;
  turma?: string;
  classe?: string;
  livro?: string;
  book?: string;
  status?: string;
  situacao?: string;
  status_financeiro?: string;
  situacao_financeira?: string;
  responsavel?: string;
  [k: string]: unknown;
};

function statusBadge(s: string) {
  const l = s.toLowerCase();
  if (l.includes("inativ") || l.includes("cancel")) return "neutral";
  if (l.includes("atenc") || l.includes("pendente")) return "warning";
  return "success";
}

function financBadge(s: string) {
  const l = s.toLowerCase();
  if (l.includes("atraso") || l.includes("vencido") || l.includes("inadim")) return "danger";
  if (l.includes("pendent") || l.includes("boleto")) return "warning";
  return "success";
}

export function AlunosSearchTable({ alunos }: { alunos: Aluno[] }) {
  const [busca, setBusca] = useState("");
  const [filtroStatus, setFiltroStatus] = useState("Todos");
  const [filtroFinanceiro, setFiltroFinanceiro] = useState("Todos");
  const [filtroTurma, setFiltroTurma] = useState("Todas");

  const turmas = useMemo(() => {
    const set = new Set(alunos.map((a) => String(a.turma || a.classe || "")).filter(Boolean));
    return ["Todas", ...Array.from(set).sort()];
  }, [alunos]);

  const filtrados = useMemo(() => {
    return alunos.filter((a) => {
      const nome = String(a.nome || a.name || "").toLowerCase();
      const turma = String(a.turma || a.classe || "").toLowerCase();
      const resp = String((a.responsavel as string | undefined) || "").toLowerCase();
      const status = String(a.status || a.situacao || "Ativo");
      const financeiro = String(a.status_financeiro || a.situacao_financeira || "Regular");

      const matchBusca = !busca || nome.includes(busca.toLowerCase()) || turma.includes(busca.toLowerCase()) || resp.includes(busca.toLowerCase());
      const matchStatus = filtroStatus === "Todos" || status.toLowerCase().includes(filtroStatus.toLowerCase());
      const matchFinanceiro = filtroFinanceiro === "Todos" ||
        (filtroFinanceiro === "Regular" && financBadge(financeiro) === "success") ||
        (filtroFinanceiro === "Inadimplente" && financBadge(financeiro) === "danger") ||
        (filtroFinanceiro === "Pendente" && financBadge(financeiro) === "warning");
      const matchTurma = filtroTurma === "Todas" || String(a.turma || a.classe || "") === filtroTurma;

      return matchBusca && matchStatus && matchFinanceiro && matchTurma;
    });
  }, [alunos, busca, filtroStatus, filtroFinanceiro, filtroTurma]);

  return (
    <>
      {/* Barra de busca e filtros */}
      <div className="card">
        <div className="toolbar">
          <div className="toolbar-left">
            <div className="search-bar">
              <span className="search-icon">
                <svg viewBox="0 0 20 20" fill="currentColor"><path fillRule="evenodd" d="M8 4a4 4 0 100 8 4 4 0 000-8zM2 8a6 6 0 1110.89 3.476l4.817 4.817a1 1 0 01-1.414 1.414l-4.816-4.816A6 6 0 012 8z" clipRule="evenodd" /></svg>
              </span>
              <input
                className="search-input"
                placeholder="Buscar por nome, turma ou responsável..."
                value={busca}
                onChange={(e) => setBusca(e.target.value)}
              />
            </div>
          </div>
          <div className="toolbar-right">
            <select className="filter-select" value={filtroTurma} onChange={(e) => setFiltroTurma(e.target.value)}>
              {turmas.map((t) => <option key={t}>{t}</option>)}
            </select>
            <select className="filter-select" value={filtroStatus} onChange={(e) => setFiltroStatus(e.target.value)}>
              <option value="Todos">Qualquer status</option>
              <option>Ativo</option>
              <option>Inativo</option>
            </select>
            <select className="filter-select" value={filtroFinanceiro} onChange={(e) => setFiltroFinanceiro(e.target.value)}>
              <option value="Todos">Todo financeiro</option>
              <option>Regular</option>
              <option>Inadimplente</option>
              <option>Pendente</option>
            </select>
          </div>
        </div>
      </div>

      {/* Tabela */}
      <div className="card">
        <div className="card-header">
          <div>
            <div className="section-eyebrow">Lista</div>
            <h3 className="section-title">Todos os alunos</h3>
            <p className="section-subtitle">
              {filtrados.length === alunos.length
                ? `${alunos.length} registros`
                : `${filtrados.length} de ${alunos.length} (filtro ativo)`}
            </p>
          </div>
        </div>
        <div className="card-body" style={{ paddingTop: "12px" }}>
          {filtrados.length === 0 ? (
            <div className="empty-state">
              <div className="empty-icon">
                <svg viewBox="0 0 20 20" fill="currentColor"><path d="M9 6a3 3 0 11-6 0 3 3 0 016 0zM17 6a3 3 0 11-6 0 3 3 0 016 0zM12.93 17c.046-.327.07-.66.07-1a6.97 6.97 0 00-1.5-4.33A5 5 0 0119 16v1h-6.07zM6 11a5 5 0 015 5v1H1v-1a5 5 0 015-5z" /></svg>
              </div>
              <div className="empty-title">Nenhum aluno encontrado</div>
              <p className="empty-desc">Ajuste os filtros para ver mais resultados.</p>
            </div>
          ) : (
            <table className="data-table">
              <thead>
                <tr>
                  <th>Aluno</th>
                  <th>Turma</th>
                  <th>Livro</th>
                  <th>Status</th>
                  <th>Financeiro</th>
                  <th>Ações</th>
                </tr>
              </thead>
              <tbody>
                {filtrados.map((a, i) => {
                  const nome = String(a.nome || a.name || `Aluno ${i + 1}`);
                  const turma = String(a.turma || a.classe || "—");
                  const livro = String(a.livro || a.book || "—");
                  const status = String(a.status || a.situacao || "Ativo");
                  const financeiro = String(a.status_financeiro || a.situacao_financeira || "Regular");
                  const hue = (nome.charCodeAt(0) * 137) % 360;
                  return (
                    <tr key={String(a.id || i)}>
                      <td>
                        <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
                          <div className="avatar avatar-sm" style={{ background: `hsl(${hue},50%,42%)` }}>
                            {nome.slice(0, 2).toUpperCase()}
                          </div>
                          <div className="table-name-cell">
                            <span className="table-name-primary">{nome}</span>
                            {(a.responsavel as string | undefined) && (
                              <span className="table-name-secondary">{String(a.responsavel)}</span>
                            )}
                          </div>
                        </div>
                      </td>
                      <td>{turma}</td>
                      <td>{livro}</td>
                      <td>
                        <span className={`badge badge-${statusBadge(status)}`}>
                          <span className="badge-dot" />{status}
                        </span>
                      </td>
                      <td>
                        <span className={`badge badge-${financBadge(financeiro)}`}>
                          <span className="badge-dot" />{financeiro}
                        </span>
                      </td>
                      <td>
                        <EditarAlunoBtn aluno={a} />
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
