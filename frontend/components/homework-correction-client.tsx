"use client";

import { useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import type { Homework, HomeworkQuestion, HomeworkSubmission } from "@/lib/school-modules";

function text(value: unknown) {
  return String(value ?? "").trim();
}

function lower(value: unknown) {
  return text(value).toLowerCase();
}

// Try question ID first, then positional fallback (handles homework edited after submission)
function answerValue(submission: HomeworkSubmission, question: HomeworkQuestion, idx: number): string {
  const answers = (submission.answers || {}) as Record<string, unknown>;
  const byId = text(answers[question.id]);
  if (byId) return byId;
  const vals = Object.values(answers);
  return idx < vals.length ? text(vals[idx]) : "";
}

function answerLabel(question: HomeworkQuestion, raw: string) {
  if (!raw) return "Sem resposta registrada";
  if (question.tipo === "multipla_escolha") {
    const idx = Number(raw);
    const opt = Number.isFinite(idx) ? question.opcoes?.[idx] : undefined;
    return opt ? `${String.fromCharCode(65 + idx)}) ${opt}` : raw;
  }
  if (question.tipo === "verdadeiro_falso") {
    if (["1", "v", "true", "verdadeiro"].includes(lower(raw))) return "Verdadeiro";
    if (["0", "f", "false", "falso"].includes(lower(raw))) return "Falso";
  }
  return raw;
}

function expectedLabel(question: HomeworkQuestion) {
  if (question.tipo === "multipla_escolha") return "A Wiz IA avalia a alternativa pelo enunciado e contexto.";
  if (question.tipo === "verdadeiro_falso") return "A Wiz IA avalia se a resposta faz sentido pelo enunciado.";
  if (true) return text(question.feedback) || "Resposta aberta; avaliar criterio, clareza e completude.";
  if ((question as HomeworkQuestion).tipo === "multipla_escolha" && question.correta_idx !== null && question.correta_idx !== undefined) {
    const idx = Number(question.correta_idx);
    const opt = question.opcoes?.[idx];
    return opt ? `${String.fromCharCode(65 + idx)}) ${opt}` : `Alternativa ${idx + 1}`;
  }
  if ((question as HomeworkQuestion).tipo === "verdadeiro_falso") {
    if (["1", "v", "true", "verdadeiro"].includes(lower(question.correta_texto))) return "Verdadeiro";
    if (["0", "f", "false", "falso"].includes(lower(question.correta_texto))) return "Falso";
  }
  return text(question.feedback) || "Resposta aberta — avaliar criterio, clareza e completude.";
}

function suggestedScore(question: HomeworkQuestion, raw: string): number {
  const pts = Number(question.pontos) || 0;
  if (!raw) return 0;
  if (question.tipo === "multipla_escolha" || question.tipo === "verdadeiro_falso") return 0;
  return Number((pts * 0.8).toFixed(1));
}

function statusBadge(status: unknown) {
  return lower(status).includes("corrigido") ? "success" : "warning";
}

type SubmissionWithHomework = { submission: HomeworkSubmission; homework?: Homework };

export function HomeworkCorrectionClient({ items }: { items: SubmissionWithHomework[] }) {
  const router = useRouter();
  const [selectedId, setSelectedId] = useState(text(items[0]?.submission.id));
  const [studentFilter, setStudentFilter] = useState("");
  const [statusFilter, setStatusFilter] = useState("pendentes");
  const selected = items.find((item) => text(item.submission.id) === selectedId) || items[0];
  const students = useMemo(() =>
    Array.from(new Set(items.map((item) => text(item.submission.aluno)).filter(Boolean))).sort(),
    [items]
  );

  const visible = items.filter((item) => {
    const matchesStudent = !studentFilter || text(item.submission.aluno) === studentFilter;
    const corrected = lower(item.submission.status).includes("corrigido");
    const matchesStatus = statusFilter === "todos" || (statusFilter === "corrigidas" ? corrected : !corrected);
    return matchesStudent && matchesStatus;
  });

  return (
    <div className="correction-workspace">
      <div className="correction-toolbar card">
        <div className="card-body correction-toolbar-body">
          <div className="form-group">
            <label className="form-label">Aluno</label>
            <select className="form-input" value={studentFilter} onChange={(e) => setStudentFilter(e.target.value)}>
              <option value="">Todos os alunos</option>
              {students.map((s) => <option key={s} value={s}>{s}</option>)}
            </select>
          </div>
          <div className="form-group">
            <label className="form-label">Status</label>
            <select className="form-input" value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)}>
              <option value="pendentes">Aguardando correcao</option>
              <option value="corrigidas">Corrigidas</option>
              <option value="todos">Todas</option>
            </select>
          </div>
          <div className="metric-card metric-card-gold" style={{ minHeight: 76 }}>
            <div className="metric-label">Na fila</div>
            <div className="metric-value">{visible.length}</div>
          </div>
        </div>
      </div>

      {items.length === 0 ? (
        <div className="empty-state">
          <div className="empty-title">Nenhuma entrega recebida</div>
          <p className="empty-desc">As respostas aparecem aqui assim que o aluno enviar a licao pelo portal.</p>
        </div>
      ) : visible.length === 0 ? (
        <div className="empty-state">
          <div className="empty-title">Nenhuma entrega neste filtro</div>
          <p className="empty-desc">Mude o filtro de status ou aluno para ver outras entregas.</p>
        </div>
      ) : (
        <div className="correction-layout">
          <div className="correction-list">
            {visible.map(({ submission, homework }) => {
              const active = text(submission.id) === text(selected?.submission.id);
              const questions = homework?.questions || [];
              const answers = (submission.answers || {}) as Record<string, unknown>;
              const answered = questions.filter((q, i) => answerValue(submission, q, i)).length;
              const totalRaw = Object.values(answers).filter(v => text(v)).length;
              const display = Math.max(answered, totalRaw);
              const total = Math.max(questions.length, Object.keys(answers).length);
              return (
                <button
                  className={`correction-list-item${active ? " active" : ""}`}
                  key={text(submission.id)}
                  onClick={() => setSelectedId(text(submission.id))}
                  type="button"
                >
                  <span className={`badge badge-${statusBadge(submission.status)}`}>
                    <span className="badge-dot" />{text(submission.status || "Aguardando")}
                  </span>
                  <strong>{text(submission.aluno)}</strong>
                  <small>{text(homework?.titulo || "Licao")} · {display}/{total} respostas</small>
                  <em>{text(submission.submitted_at || "-")}</em>
                </button>
              );
            })}
          </div>
          {selected && (
            <CorrectionDetail
              key={text(selected.submission.id)}
              item={selected}
              onSaved={() => router.refresh()}
            />
          )}
        </div>
      )}
    </div>
  );
}

function CorrectionDetail({ item, onSaved }: { item: SubmissionWithHomework; onSaved: () => void }) {
  const { submission, homework } = item;
  const questions = homework?.questions || [];
  const answers = (submission.answers || {}) as Record<string, unknown>;
  const maxScore = questions.reduce((s, q) => s + (Number(q.pontos) || 0), 0) || 10;

  const initialScores = Object.fromEntries(questions.map((q, idx) => {
    const saved = Number((submission.question_scores || {})[q.id]);
    const raw = answerValue(submission, q, idx);
    const hasSavedScore = Object.prototype.hasOwnProperty.call(submission.question_scores || {}, q.id);
    return [q.id, hasSavedScore && Number.isFinite(saved) ? saved : suggestedScore(q, raw)];
  }));

  const [questionScores, setQuestionScores] = useState<Record<string, number>>(initialScores);
  const [score, setScore] = useState(
    String(Number(submission.score ?? Object.values(initialScores).reduce((s, v) => s + Number(v || 0), 0)).toFixed(1))
  );
  const [feedback, setFeedback] = useState(text(submission.feedback));
  const [saving, setSaving] = useState(false);
  const [aiLoading, setAiLoading] = useState(false);
  const [msg, setMsg] = useState("");

  // Answers that exist in submission but don't map to any current question ID
  const mappedIds = new Set(questions.map(q => q.id));
  const orphanAnswers = Object.entries(answers).filter(([k, v]) => !mappedIds.has(k) && text(v));

  async function applyAi() {
    if (!homework) return;
    setAiLoading(true);
    setMsg("");
    try {
      const res = await fetch("/api/licoes/ai-review", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ submission, homework, persist: true }),
      });
      const data = await res.json().catch(() => ({})) as {
        questionScores?: Record<string, number>;
        suggestedTotal?: number;
        feedback?: string;
        error?: string;
        saved?: boolean;
      };
      if (!res.ok) { setMsg(data.error || "Erro ao consultar IA."); return; }
      if (data.questionScores) {
        setQuestionScores((prev) => ({ ...prev, ...data.questionScores }));
        setScore(String(data.suggestedTotal ?? 0));
      }
      if (data.feedback) setFeedback(data.feedback);
      if (data.saved) {
        setMsg("Wiz IA avaliou e lancou a nota automaticamente.");
        onSaved();
      }
    } finally {
      setAiLoading(false);
    }
  }

  function updateQuestionScore(id: string, value: string) {
    const n = Number(value) || 0;
    const next = { ...questionScores, [id]: n };
    setQuestionScores(next);
    setScore(String(Number(Object.values(next).reduce((s, v) => s + Number(v || 0), 0).toFixed(1))));
  }

  async function save() {
    setSaving(true);
    setMsg("");
    const res = await fetch("/api/licoes/review", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ submission_id: submission.id, score: Number(score), feedback, question_scores: questionScores }),
    });
    const data = await res.json().catch(() => ({})) as { error?: string };
    setSaving(false);
    if (!res.ok) { setMsg(data.error || "Erro ao salvar correcao."); return; }
    setMsg("Correcao salva e nota lancada.");
    onSaved();
  }

  return (
    <article className="card correction-detail">
      <div className="card-header">
        <div>
          <div className="section-eyebrow">Entrega selecionada</div>
          <h3 className="section-title">{text(submission.aluno)}</h3>
          <p className="section-subtitle">
            {text(homework?.titulo || "Licao")} · {text(submission.submitted_at || "-")}
          </p>
        </div>
        <span className={`badge badge-${statusBadge(submission.status)}`}>
          <span className="badge-dot" />{text(submission.status || "Aguardando correcao")}
        </span>
      </div>
      <div className="card-body">
        <div className="correction-actions">
          <button className="btn btn-secondary" type="button" onClick={applyAi} disabled={aiLoading || !homework}>
            {aiLoading ? "Avaliando..." : "Avaliar com IA e lancar nota"}
          </button>
          <div className="form-group correction-score">
            <label className="form-label">Nota final / {maxScore}</label>
            <input
              className="form-input"
              type="number" min={0} max={maxScore} step="0.1"
              value={score}
              onChange={(e) => setScore(e.target.value)}
            />
          </div>
        </div>

        {/* Questions with answers */}
        {questions.length > 0 ? (
          <div className="correction-question-list">
            {questions.map((q, idx) => {
              const raw = answerValue(submission, q, idx);
              const label = answerLabel(q, raw);
              return (
                <div className={`correction-question${raw ? "" : " missing"}`} key={q.id}>
                  <div className="correction-question-head">
                    <strong>Questao {idx + 1} — {q.tipo === "aberta" ? "Dissertativa" : q.tipo === "multipla_escolha" ? "Multipla escolha" : q.tipo === "verdadeiro_falso" ? "V/F" : "Upload"}</strong>
                    <span>{Number(q.pontos) || 0} pts</span>
                  </div>
                  <p style={{ marginBottom: 8 }}>{text(q.enunciado)}</p>
                  <div className="correction-answer-grid">
                    <div>
                      <span>Resposta do aluno</span>
                      <strong style={{ color: raw ? "inherit" : "var(--red-600)" }}>{label}</strong>
                      {raw && raw !== label && <small style={{ color: "var(--text-muted)" }}>Valor: {raw}</small>}
                    </div>
                    <div>
                      <span>Critério da IA</span>
                      <strong>{expectedLabel(q)}</strong>
                    </div>
                    <div>
                      <span>Pontuacao</span>
                      <input
                        className="form-input"
                        type="number" min={0} max={Number(q.pontos) || 0} step="0.1"
                        value={questionScores[q.id] ?? 0}
                        onChange={(e) => updateQuestionScore(q.id, e.target.value)}
                      />
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        ) : (
          /* No questions mapped — show raw answers from submission */
          <div className="correction-question-list">
            <div style={{ padding: "10px 14px", background: "var(--amber-50)", border: "1px solid var(--amber-200)", borderRadius: 8, marginBottom: 12, fontSize: "0.875rem" }}>
              Esta lição nao tem questoes mapeadas (pode ter sido criada sem questoes ou editada). Exibindo respostas brutas da entrega.
            </div>
            {Object.entries(answers).map(([key, val], i) => (
              <div className="correction-question" key={key}>
                <div className="correction-question-head">
                  <strong>Resposta {i + 1}</strong>
                  <small style={{ color: "var(--text-muted)" }}>chave: {key.slice(0, 12)}…</small>
                </div>
                <div className="correction-answer-grid">
                  <div>
                    <span>Resposta do aluno</span>
                    <strong>{text(val) || "—"}</strong>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Orphan answers (IDs changed after submission due to edit) */}
        {orphanAnswers.length > 0 && questions.length > 0 && (
          <details style={{ marginTop: 12 }}>
            <summary style={{ cursor: "pointer", fontSize: "0.8125rem", color: "var(--amber-700)", fontWeight: 600 }}>
              {orphanAnswers.length} resposta(s) sem questao correspondente — lição foi editada apos o envio
            </summary>
            <div className="correction-question-list" style={{ marginTop: 8 }}>
              {orphanAnswers.map(([key, val], i) => (
                <div className="correction-question" key={key}>
                  <div className="correction-question-head">
                    <strong>Resposta extra {i + 1}</strong>
                    <small style={{ color: "var(--amber-600)" }}>ID original: {key.slice(0, 16)}…</small>
                  </div>
                  <div className="correction-answer-grid">
                    <div><span>Resposta registrada</span><strong>{text(val)}</strong></div>
                  </div>
                </div>
              ))}
            </div>
          </details>
        )}

        <div className="form-group" style={{ marginTop: 16 }}>
          <label className="form-label">Devolutiva para o aluno</label>
          <textarea
            className="form-input form-textarea"
            rows={4}
            value={feedback}
            onChange={(e) => setFeedback(e.target.value)}
            placeholder="Escreva uma orientacao clara e curta para o aluno."
          />
        </div>

        {msg && (
          <div className={msg.includes("salva") ? "form-success" : "form-error"} style={{ marginBottom: 8 }}>
            {msg}
          </div>
        )}

        <button className="btn btn-primary" type="button" onClick={save} disabled={saving}>
          {saving ? "Salvando..." : "Salvar correcao e lancar nota"}
        </button>
      </div>
    </article>
  );
}
