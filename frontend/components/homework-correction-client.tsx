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

function answerValue(submission: HomeworkSubmission, question: HomeworkQuestion) {
  const answers = (submission.answers || {}) as Record<string, unknown>;
  return text(answers[question.id]);
}

function answerLabel(question: HomeworkQuestion, rawAnswer: string) {
  if (!rawAnswer) return "Sem resposta registrada";
  if (question.tipo === "multipla_escolha") {
    const idx = Number(rawAnswer);
    const option = Number.isFinite(idx) ? question.opcoes?.[idx] : "";
    return option ? `${String.fromCharCode(65 + idx)}) ${option}` : rawAnswer;
  }
  if (question.tipo === "verdadeiro_falso") {
    const value = lower(rawAnswer);
    if (["1", "v", "true", "verdadeiro"].includes(value)) return "Verdadeiro";
    if (["0", "f", "false", "falso"].includes(value)) return "Falso";
  }
  return rawAnswer;
}

function expectedLabel(question: HomeworkQuestion) {
  if (question.tipo === "multipla_escolha" && question.correta_idx !== null && question.correta_idx !== undefined) {
    const idx = Number(question.correta_idx);
    const option = question.opcoes?.[idx];
    return option ? `${String.fromCharCode(65 + idx)}) ${option}` : `Alternativa ${idx}`;
  }
  if (question.tipo === "verdadeiro_falso") {
    const value = lower(question.correta_texto);
    if (["1", "v", "true", "verdadeiro"].includes(value)) return "Verdadeiro";
    if (["0", "f", "false", "falso"].includes(value)) return "Falso";
  }
  return text(question.feedback) || "Resposta aberta: avaliar criterio, clareza e completude.";
}

function objectiveScore(question: HomeworkQuestion, rawAnswer: string) {
  const points = Number(question.pontos) || 0;
  if (!rawAnswer) return 0;
  if (question.tipo === "multipla_escolha" && question.correta_idx !== null && question.correta_idx !== undefined) {
    return Number(rawAnswer) === Number(question.correta_idx) ? points : 0;
  }
  if (question.tipo === "verdadeiro_falso" && text(question.correta_texto)) {
    const answer = lower(rawAnswer);
    const expected = lower(question.correta_texto);
    const normalizedAnswer = ["1", "true", "verdadeiro"].includes(answer) ? "v" : ["0", "false", "falso"].includes(answer) ? "f" : answer;
    const normalizedExpected = ["1", "true", "verdadeiro"].includes(expected) ? "v" : ["0", "false", "falso"].includes(expected) ? "f" : expected;
    return normalizedAnswer === normalizedExpected ? points : 0;
  }
  return 0;
}

function suggestedQuestionScore(question: HomeworkQuestion, rawAnswer: string) {
  const points = Number(question.pontos) || 0;
  if (!rawAnswer) return 0;
  if (question.tipo === "aberta" || question.tipo === "upload") return Number((points * 0.8).toFixed(1));
  return objectiveScore(question, rawAnswer);
}

function statusBadge(status: unknown) {
  return lower(status).includes("corrigido") ? "success" : "warning";
}

type SubmissionWithHomework = {
  submission: HomeworkSubmission;
  homework?: Homework;
};

export function HomeworkCorrectionClient({ items }: { items: SubmissionWithHomework[] }) {
  const router = useRouter();
  const [selectedId, setSelectedId] = useState(text(items[0]?.submission.id));
  const [studentFilter, setStudentFilter] = useState("");
  const [statusFilter, setStatusFilter] = useState("pendentes");
  const selected = items.find((item) => text(item.submission.id) === selectedId) || items[0];
  const students = useMemo(() => Array.from(new Set(items.map((item) => text(item.submission.aluno)).filter(Boolean))).sort(), [items]);

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
            <select className="form-input" value={studentFilter} onChange={(event) => setStudentFilter(event.target.value)}>
              <option value="">Todos os alunos</option>
              {students.map((student) => <option key={student} value={student}>{student}</option>)}
            </select>
          </div>
          <div className="form-group">
            <label className="form-label">Status</label>
            <select className="form-input" value={statusFilter} onChange={(event) => setStatusFilter(event.target.value)}>
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
        <div className="empty-state"><div className="empty-title">Nenhuma entrega recebida</div><p className="empty-desc">As respostas aparecem aqui assim que o aluno enviar a licao pelo portal.</p></div>
      ) : (
        <div className="correction-layout">
          <div className="correction-list">
            {visible.map(({ submission, homework }) => {
              const active = text(submission.id) === text(selected?.submission.id);
              const questions = homework?.questions || [];
              const answered = questions.filter((question) => answerValue(submission, question)).length;
              return (
                <button className={`correction-list-item${active ? " active" : ""}`} key={text(submission.id)} onClick={() => setSelectedId(text(submission.id))} type="button">
                  <span className={`badge badge-${statusBadge(submission.status)}`}><span className="badge-dot" />{text(submission.status || "Aguardando correcao")}</span>
                  <strong>{text(submission.aluno)}</strong>
                  <small>{text(homework?.titulo || "Licao")} · {answered}/{questions.length} respostas</small>
                  <em>{text(submission.submitted_at || "-")}</em>
                </button>
              );
            })}
          </div>
          {selected && <CorrectionDetail key={text(selected.submission.id)} item={selected} onSaved={() => router.refresh()} />}
        </div>
      )}
    </div>
  );
}

function CorrectionDetail({ item, onSaved }: { item: SubmissionWithHomework; onSaved: () => void }) {
  const { submission, homework } = item;
  const questions = homework?.questions || [];
  const maxScore = questions.reduce((sum, question) => sum + (Number(question.pontos) || 0), 0) || 10;
  const initialScores = Object.fromEntries(questions.map((question) => {
    const saved = Number((submission.question_scores || {})[question.id]);
    return [question.id, Number.isFinite(saved) && saved > 0 ? saved : suggestedQuestionScore(question, answerValue(submission, question))];
  }));
  const [questionScores, setQuestionScores] = useState<Record<string, number>>(initialScores);
  const [score, setScore] = useState(String(Number(submission.score ?? Object.values(initialScores).reduce((sum, value) => sum + Number(value || 0), 0)).toFixed(1)));
  const [feedback, setFeedback] = useState(text(submission.feedback));
  const [saving, setSaving] = useState(false);
  const [msg, setMsg] = useState("");

  function applyAiHelp() {
    const nextScores = Object.fromEntries(questions.map((question) => [question.id, suggestedQuestionScore(question, answerValue(submission, question))]));
    const nextTotal = Object.values(nextScores).reduce((sum, value) => sum + Number(value || 0), 0);
    const missing = questions.filter((question) => !answerValue(submission, question)).length;
    const open = questions.filter((question) => ["aberta", "upload"].includes(question.tipo)).length;
    setQuestionScores(nextScores);
    setScore(String(Number(nextTotal.toFixed(1))));
    setFeedback([
      "IA de apoio: respostas objetivas conferidas pelo gabarito cadastrado.",
      open ? "Ha respostas abertas/anexos que precisam de validacao humana antes de concluir." : "",
      missing ? `${missing} questao(oes) sem resposta registrada.` : "Entrega completa para as questoes cadastradas."
    ].filter(Boolean).join(" "));
  }

  function setQuestionScore(id: string, value: string) {
    const numeric = Number(value) || 0;
    const next = { ...questionScores, [id]: numeric };
    setQuestionScores(next);
    setScore(String(Number(Object.values(next).reduce((sum, item) => sum + Number(item || 0), 0).toFixed(1))));
  }

  async function save() {
    setSaving(true);
    setMsg("");
    const res = await fetch("/api/licoes/review", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ submission_id: submission.id, score: Number(score), feedback, question_scores: questionScores })
    });
    const data = await res.json().catch(() => ({}));
    setSaving(false);
    if (!res.ok) {
      setMsg(text((data as { error?: string }).error) || "Erro ao salvar correcao.");
      return;
    }
    setMsg("Correcao salva e nota lancada.");
    onSaved();
  }

  return (
    <article className="card correction-detail">
      <div className="card-header">
        <div>
          <div className="section-eyebrow">Entrega selecionada</div>
          <h3 className="section-title">{text(submission.aluno)}</h3>
          <p className="section-subtitle">{text(homework?.titulo || "Licao")} · {text(submission.submitted_at || "-")}</p>
        </div>
        <span className={`badge badge-${statusBadge(submission.status)}`}><span className="badge-dot" />{text(submission.status || "Aguardando correcao")}</span>
      </div>
      <div className="card-body">
        <div className="correction-actions">
          <button className="btn btn-secondary" type="button" onClick={applyAiHelp}>IA ajudar na correcao</button>
          <div className="form-group correction-score">
            <label className="form-label">Nota final / {maxScore}</label>
            <input className="form-input" type="number" min={0} max={maxScore} step="0.1" value={score} onChange={(event) => setScore(event.target.value)} />
          </div>
        </div>
        <div className="correction-question-list">
          {questions.map((question, index) => {
            const raw = answerValue(submission, question);
            return (
              <div className={`correction-question${raw ? "" : " missing"}`} key={question.id}>
                <div className="correction-question-head">
                  <strong>Questao {index + 1}</strong>
                  <span>{Number(question.pontos) || 0} pts</span>
                </div>
                <p>{text(question.enunciado)}</p>
                <div className="correction-answer-grid">
                  <div>
                    <span>Resposta do aluno</span>
                    <strong>{answerLabel(question, raw)}</strong>
                    {raw && <small>Valor registrado: {raw}</small>}
                  </div>
                  <div>
                    <span>Gabarito / criterio</span>
                    <strong>{expectedLabel(question)}</strong>
                  </div>
                  <div>
                    <span>Pontuacao da questao</span>
                    <input className="form-input" type="number" min={0} max={Number(question.pontos) || 0} step="0.1" value={questionScores[question.id] ?? 0} onChange={(event) => setQuestionScore(question.id, event.target.value)} />
                  </div>
                </div>
              </div>
            );
          })}
        </div>
        <div className="form-group">
          <label className="form-label">Devolutiva para o aluno</label>
          <textarea className="form-input form-textarea" rows={4} value={feedback} onChange={(event) => setFeedback(event.target.value)} placeholder="Escreva uma orientacao clara e curta." />
        </div>
        {msg && <div className={msg.includes("salva") ? "form-success" : "form-error"}>{msg}</div>}
        <button className="btn btn-primary" type="button" onClick={save} disabled={saving}>{saving ? "Salvando..." : "Salvar correcao"}</button>
      </div>
    </article>
  );
}

