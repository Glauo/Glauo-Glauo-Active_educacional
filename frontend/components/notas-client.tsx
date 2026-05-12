"use client";

import { useMemo, useState } from "react";

type Row = Record<string, unknown>;

function text(v: unknown) { return String(v || "").trim(); }
function num(v: unknown) { const n = Number(v); return Number.isFinite(n) ? n : 0; }

function notaBadgeClass(nota: number) {
  if (nota >= 7) return "success";
  if (nota >= 5) return "warning";
  return "danger";
}

function FrequenciaResumo({ frequencias }: { frequencias: Row[] }) {
  const porTurma = useMemo(() => {
    const map: Record<string, { turma: string; total: number; faltas: number; alunos: Set<string> }> = {};
    for (const f of frequencias) {
      const turma = text(f.turma || f.turma_id || "Geral");
      if (!map[turma]) map[turma] = { turma, total: 0, faltas: 0, alunos: new Set() };
      map[turma].total++;
      if (f.falta) map[turma].faltas++;
      const aluno = text(f.aluno || f.aluno_id);
      if (aluno) map[turma].alunos.add(aluno);
    }
    return Object.values(map).sort((a, b) => b.total - a.total);
  }, [frequencias]);

  if (frequencias.length === 0) {
    return (
      <div className="card" style={{ marginTop: 24 }}>
        <div className="card-header">
          <div>
            <div className="section-eyebrow">Frequência</div>
            <h3 className="section-title">Presenças por turma</h3>
          </div>
        </div>
        <div className="card-body">
          <div className="empty-state">
            <div className="empty-title">Nenhuma frequência registrada</div>
            <p className="empty-desc">As presenças são registradas automaticamente ao fechar uma aula no painel do professor.</p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="card" style={{ marginTop: 24 }}>
      <div className="card-header">
        <div>
          <div className="section-eyebrow">Frequência</div>
          <h3 className="section-title">Presenças por turma</h3>
          <p className="section-subtitle">{frequencias.length} registros de aula</p>
        </div>
      </div>
      <div className="card-body" style={{ paddingTop: 12 }}>
        <table className="data-table">
          <thead>
            <tr>
              <th>Turma</th>
              <th>Alunos</th>
              <th>Registros</th>
              <th>Faltas</th>
              <th>Frequência</th>
            </tr>
          </thead>
          <tbody>
            {porTurma.map((t) => {
              const pct = t.total > 0 ? Math.round(((t.total - t.faltas) / t.total) * 100) : 100;
              const badgeClass = pct >= 75 ? "success" : pct >= 60 ? "warning" : "danger";
              return (
                <tr key={t.turma}>
                  <td style={{ fontWeight: 700 }}>{t.turma}</td>
                  <td>{t.alunos.size}</td>
                  <td>{t.total}</td>
                  <td style={{ color: t.faltas > 0 ? "var(--red-700)" : undefined, fontWeight: t.faltas > 0 ? 700 : undefined }}>
                    {t.faltas}
                  </td>
                  <td>
                    <span className={`badge badge-${badgeClass}`}>
                      <span className="badge-dot" />{pct}%
                    </span>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}

export function NotasClient({ notas, frequencias }: { notas: Row[]; frequencias: Row[] }) {
  const [busca, setBusca] = useState("");
  const [filtroTurma, setFiltroTurma] = useState("");

  const turmas = useMemo(() => [...new Set(notas.map((n) => text(n.turma)).filter(Boolean))].sort(), [notas]);

  const filtradas = useMemo(() => {
    return notas.filter((n) => {
      const matchTurma = !filtroTurma || text(n.turma) === filtroTurma;
      const matchBusca = !busca.trim() ||
        text(n.aluno).toLowerCase().includes(busca.toLowerCase()) ||
        text(n.titulo || n.desafio).toLowerCase().includes(busca.toLowerCase());
      return matchTurma && matchBusca;
    });
  }, [notas, busca, filtroTurma]);

  const media = filtradas.length
    ? filtradas.reduce((s, n) => s + num(n.nota), 0) / filtradas.length
    : 0;

  return (
    <>
      <div className="card" style={{ marginTop: 24 }}>
        <div className="card-header">
          <div>
            <div className="section-eyebrow">Boletim</div>
            <h3 className="section-title">Notas lançadas</h3>
            <p className="section-subtitle">{filtradas.length} de {notas.length} registros{media > 0 ? ` — média ${media.toFixed(1)}` : ""}</p>
          </div>
          <div style={{ display: "flex", gap: "8px", flexWrap: "wrap" }}>
            {turmas.length > 0 && (
              <select
                className="filter-select"
                value={filtroTurma}
                onChange={(e) => setFiltroTurma(e.target.value)}
              >
                <option value="">Todas as turmas</option>
                {turmas.map((t) => <option key={t}>{t}</option>)}
              </select>
            )}
            <div className="search-bar">
              <span className="search-icon">
                <svg viewBox="0 0 20 20" fill="currentColor">
                  <path fillRule="evenodd" d="M8 4a4 4 0 100 8 4 4 0 000-8zM2 8a6 6 0 1110.89 3.476l4.817 4.817a1 1 0 01-1.414 1.414l-4.816-4.816A6 6 0 012 8z" clipRule="evenodd" />
                </svg>
              </span>
              <input
                className="search-input"
                placeholder="Buscar aluno ou desafio..."
                value={busca}
                onChange={(e) => setBusca(e.target.value)}
                style={{ minWidth: "180px" }}
              />
            </div>
          </div>
        </div>
        <div className="card-body" style={{ paddingTop: 12 }}>
          {notas.length === 0 ? (
            <div className="empty-state">
              <div className="empty-title">Nenhuma nota lançada</div>
              <p className="empty-desc">Corrija um desafio para a nota aparecer aqui e no painel do aluno.</p>
            </div>
          ) : filtradas.length === 0 ? (
            <div className="empty-state">
              <div className="empty-title">Nenhum resultado</div>
              <p className="empty-desc">Ajuste os filtros para ver as notas.</p>
            </div>
          ) : (
            <table className="data-table">
              <thead>
                <tr>
                  <th>Aluno</th>
                  <th>Desafio</th>
                  <th>Turma</th>
                  <th>Nota</th>
                  <th>Status</th>
                  <th>Data</th>
                </tr>
              </thead>
              <tbody>
                {filtradas.map((n, i) => {
                  const nota = num(n.nota);
                  return (
                    <tr key={text(n.id || i)}>
                      <td style={{ fontWeight: 700 }}>{text(n.aluno)}</td>
                      <td>{text(n.titulo || n.desafio)}</td>
                      <td>{text(n.turma || "—")}</td>
                      <td>
                        <span className={`badge badge-${notaBadgeClass(nota)}`}>{nota.toFixed(1)}</span>
                      </td>
                      <td>
                        <span className="badge badge-success">
                          <span className="badge-dot" />{text(n.status || "Corrigido")}
                        </span>
                      </td>
                      <td style={{ color: "var(--text-muted)", fontSize: "0.875rem" }}>
                        {n.data ? new Date(String(n.data)).toLocaleDateString("pt-BR") : "—"}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          )}
        </div>
      </div>

      <FrequenciaResumo frequencias={frequencias} />
    </>
  );
}
