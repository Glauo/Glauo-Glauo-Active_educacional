"use client";

import { useMemo, useState } from "react";
import { HomeworkReviewForm } from "@/components/school-modules-client";
import { text, type Homework, type HomeworkSubmission } from "@/lib/school-modules";

function lower(v: unknown) { return text(v).toLowerCase(); }

function getAnswer(answers: Record<string, unknown>, questionId: string, idx: number): string {
  const byId = text(answers[questionId]);
  if (byId) return byId;
  const vals = Object.values(answers);
  return idx < vals.length ? text(vals[idx]) : "";
}

export function LicoesEntregasBtn({
  licoes,
  entregas,
}: {
  licoes: Homework[];
  entregas: HomeworkSubmission[];
}) {
  const [open, setOpen] = useState(false);
  const [selectedAluno, setSelectedAluno] = useState("");

  const alunos = useMemo(
    () => Array.from(new Set(entregas.map((e) => text(e.aluno)).filter(Boolean))).sort(),
    [entregas]
  );

  const entregasDoAluno = useMemo(() => {
    if (!selectedAluno) return [];
    return entregas
      .filter((e) => text(e.aluno) === selectedAluno)
      .map((e) => ({ entrega: e, licao: licoes.find((l) => text(l.id) === text(e.activity_id)) }));
  }, [entregas, licoes, selectedAluno]);

  if (!open) {
    return (
      <button className="btn btn-secondary" onClick={() => setOpen(true)}>
        <svg viewBox="0 0 20 20" fill="currentColor" width={16} height={16}>
          <path d="M9 2a1 1 0 000 2h2a1 1 0 100-2H9z" />
          <path fillRule="evenodd" d="M4 5a2 2 0 012-2 3 3 0 003 3h2a3 3 0 003-3 2 2 0 012 2v11a2 2 0 01-2 2H6a2 2 0 01-2-2V5zm4 5a1 1 0 011-1h5a1 1 0 110 2H9a1 1 0 01-1-1z" clipRule="evenodd" />
        </svg>
        Ver entregas ({entregas.length})
      </button>
    );
  }

  return (
    <div className="card" style={{ marginTop: 24 }}>
      <div className="card-header">
        <div>
          <div className="section-eyebrow">Correcao</div>
          <h3 className="section-title">Entregas por aluno</h3>
          <p className="section-subtitle">Selecione um aluno para ver e corrigir suas licoes</p>
        </div>
        <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
          <select
            className="form-input"
            style={{ width: 240 }}
            value={selectedAluno}
            onChange={(e) => setSelectedAluno(e.target.value)}
          >
            <option value="">Selecione um aluno...</option>
            {alunos.map((a) => <option key={a} value={a}>{a}</option>)}
          </select>
          <button className="btn btn-secondary btn-sm" onClick={() => { setOpen(false); setSelectedAluno(""); }}>
            Fechar
          </button>
        </div>
      </div>
      <div className="card-body">
        {!selectedAluno ? (
          <div className="empty-state">
            <div className="empty-title">Selecione um aluno acima</div>
            <p className="empty-desc">Escolha o aluno para ver as licoes entregues e lancar a nota.</p>
          </div>
        ) : entregasDoAluno.length === 0 ? (
          <div className="empty-state">
            <div className="empty-title">Nenhuma entrega de {selectedAluno}</div>
            <p className="empty-desc">Este aluno ainda nao enviou nenhuma licao.</p>
          </div>
        ) : (
          <div style={{ display: "grid", gap: 16 }}>
            {entregasDoAluno.map(({ entrega, licao }) => (
              <div className="entity-card" key={text(entrega.id)} style={{ cursor: "default" }}>
                <div className="entity-card-top">
                  <div className="entity-card-info">
                    <div className="entity-card-name">{text(licao?.titulo || "Licao")}</div>
                    <div className="entity-card-sub">
                      {text(licao?.disciplina || "Geral")} · Enviada em {text(entrega.submitted_at || "-")}
                    </div>
                  </div>
                  <span className={`badge badge-${lower(entrega.status).includes("corrigido") ? "success" : "warning"}`}>
                    <span className="badge-dot" />
                    {text(entrega.status || "Aguardando correcao")}
                  </span>
                </div>

                {(licao?.questions || []).length > 0 && (
                  <div style={{ display: "grid", gap: 8, marginBottom: 14 }}>
                    {(licao?.questions || []).map((q, idx) => {
                      const ans = entrega.answers as Record<string, unknown> | undefined;
                      const raw = getAnswer(ans || {}, q.id, idx);
                      return (
                        <div className="attendance-item" key={q.id} style={{ alignItems: "flex-start", gap: 8 }}>
                          <strong style={{ minWidth: 20 }}>{idx + 1}.</strong>
                          <span style={{ flex: 1 }}>{q.enunciado}</span>
                          <span style={{ color: raw ? "var(--text-primary)" : "var(--red-500)", fontStyle: raw ? "normal" : "italic", maxWidth: 260 }}>
                            {raw || "Sem resposta"}
                          </span>
                        </div>
                      );
                    })}
                  </div>
                )}

                <HomeworkReviewForm submission={entrega} homework={licao} />
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
