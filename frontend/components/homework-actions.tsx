"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { ModalPortal } from "@/components/modal-portal";
import { text, type Homework, type HomeworkQuestion } from "@/lib/school-modules";

type Row = Record<string, unknown>;

function splitLines(value: string) {
  return value.split("\n").map((item) => item.trim()).filter(Boolean);
}

function toggleList(list: string[], value: string) {
  return list.includes(value) ? list.filter((item) => item !== value) : [...list, value];
}

function rowName(row: Row) {
  return text(row.nome || row.name || row.nome_completo || row.aluno || row.login || row.usuario);
}

function rowClass(row: Row) {
  return text(row.turma || row.classe || row.class);
}

function rowValue(row: Row) {
  return text(row.login || row.usuario || rowName(row));
}

function normalizeQuestions(licao: Homework): HomeworkQuestion[] {
  const questions = Array.isArray(licao.questions) ? licao.questions : [];
  if (questions.length > 0) {
    return questions.map((question, index) => ({
      id: text(question.id) || crypto.randomUUID(),
      tipo: question.tipo || "aberta",
      enunciado: text(question.enunciado) || `Questao ${index + 1}`,
      opcoes: Array.isArray(question.opcoes) ? question.opcoes.map(text).filter(Boolean) : [],
      pontos: Number(question.pontos) || 1,
      feedback: text(question.feedback),
    }));
  }
  return [{
    id: crypto.randomUUID(),
    tipo: "aberta",
    enunciado: text(licao.descricao) || "Descreva sua resposta.",
    pontos: Number(licao.peso) || 10,
  }];
}

type EditForm = {
  titulo: string;
  descricao: string;
  turma: string;
  turmas: string[];
  aluno: string;
  disciplina: string;
  livro: string;
  capitulo: string;
  aula_referencia: string;
  habilidade: string;
  peso: string;
  due_date: string;
  status: string;
  allow_resubmission: boolean;
};

export function HomeworkDeleteBtn({ licao }: { licao: Homework }) {
  const router = useRouter();
  const [saving, setSaving] = useState(false);

  async function excluir() {
    if (!confirm(`Excluir a licao "${text(licao.titulo)}"? Esta acao nao pode ser desfeita.`)) return;
    setSaving(true);
    await fetch(`/api/licoes?id=${encodeURIComponent(text(licao.id))}`, { method: "DELETE" });
    setSaving(false);
    router.refresh();
  }

  return (
    <button className="btn btn-danger btn-sm" onClick={excluir} disabled={saving} title="Excluir licao">
      {saving ? "..." : "Excluir"}
    </button>
  );
}

export function HomeworkEditBtn({ licao, turmas, alunos = [] }: { licao: Homework; turmas: string[]; alunos?: Row[] }) {
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const [saving, setSaving] = useState(false);
  const [erro, setErro] = useState("");
  const [form, setForm] = useState<EditForm>({
    titulo: text(licao.titulo),
    descricao: text(licao.descricao),
    turma: text(licao.turma || "Todas"),
    turmas: Array.isArray(licao.turmas) ? licao.turmas.map(text).filter(Boolean) : [],
    aluno: text(licao.aluno),
    disciplina: text(licao.disciplina || "Ingles"),
    livro: text(licao.livro),
    capitulo: text(licao.capitulo),
    aula_referencia: text(licao.aula_referencia),
    habilidade: text(licao.habilidade),
    peso: text(licao.peso || 10),
    due_date: text(licao.due_date),
    status: text(licao.status || "Ativa"),
    allow_resubmission: Boolean(licao.allow_resubmission),
  });
  const [questions, setQuestions] = useState<HomeworkQuestion[]>(normalizeQuestions(licao));

  function upd<K extends keyof EditForm>(key: K, value: EditForm[K]) {
    setForm((prev) => ({ ...prev, [key]: value }));
    setErro("");
  }

  function toggleTurma(turma: string) {
    setForm((prev) => ({ ...prev, turmas: toggleList(prev.turmas, turma) }));
    setErro("");
  }

  function updateQuestion(index: number, patch: Partial<HomeworkQuestion>) {
    setQuestions((prev) => prev.map((question, position) => position === index ? { ...question, ...patch } : question));
    setErro("");
  }

  function addQuestion() {
    setQuestions((prev) => [...prev, { id: crypto.randomUUID(), tipo: "aberta", enunciado: "", pontos: 1 }]);
  }

  function removeQuestion(index: number) {
    setQuestions((prev) => prev.length === 1 ? prev : prev.filter((_, position) => position !== index));
  }

  async function salvar() {
    if (!form.titulo.trim()) {
      setErro("Titulo e obrigatorio.");
      return;
    }
    if (questions.some((question) => !text(question.enunciado))) {
      setErro("Preencha o enunciado de todas as questoes.");
      return;
    }
    if (questions.some((question) => question.tipo === "multipla_escolha" && (question.opcoes || []).map(text).filter(Boolean).length < 2)) {
      setErro("Questoes de multipla escolha precisam de pelo menos duas alternativas.");
      return;
    }

    setSaving(true);
    const turmasMarcadas = form.turmas.filter((turma) => turma !== form.turma);
    const normalizedQuestions = questions.map((question, index) => ({
      ...question,
      id: text(question.id) || crypto.randomUUID(),
      enunciado: text(question.enunciado) || `Questao ${index + 1}`,
      opcoes: question.tipo === "multipla_escolha" ? (question.opcoes || []).map(text).filter(Boolean) : [],
      pontos: Number(question.pontos) || 1,
    }));
    const res = await fetch("/api/licoes", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        id: text(licao.id),
        ...form,
        turmas: turmasMarcadas,
        peso: Number(form.peso) || normalizedQuestions.reduce((sum, question) => sum + (Number(question.pontos) || 0), 0) || 10,
        allow_resubmission: form.allow_resubmission,
        questions: normalizedQuestions,
      }),
    });
    setSaving(false);
    if (!res.ok) {
      const data = await res.json().catch(() => ({}));
      setErro((data as { error?: string }).error || "Erro ao salvar.");
      return;
    }
    setOpen(false);
    router.refresh();
  }

  return (
    <>
      <button className="btn btn-secondary btn-sm" onClick={() => setOpen(true)}>Editar</button>
      {open && (
        <ModalPortal>
          <div className="modal-overlay" onClick={(event) => event.target === event.currentTarget && setOpen(false)}>
            <div className="modal-box" style={{ maxWidth: 980 }}>
              <div className="modal-header">
                <div>
                  <div className="modal-title">Editar licao de casa</div>
                  <div className="modal-subtitle">Revise destinatarios, conteudo e questoes completas.</div>
                </div>
                <button className="modal-close" onClick={() => setOpen(false)}>
                  <svg viewBox="0 0 20 20" fill="currentColor"><path fillRule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clipRule="evenodd" /></svg>
                </button>
              </div>
              <div className="modal-body">
                <div className="form-grid">
                  <div className="form-group form-group-span2"><label className="form-label">Titulo *</label><input className="form-input" value={form.titulo} onChange={(event) => upd("titulo", event.target.value)} autoFocus /></div>
                  <div className="form-group form-group-span2"><label className="form-label">Descricao / instrucoes</label><textarea className="form-input form-textarea" rows={3} value={form.descricao} onChange={(event) => upd("descricao", event.target.value)} /></div>
                  <div className="form-group"><label className="form-label">Turma principal</label><select className="form-input" value={form.turma} onChange={(event) => upd("turma", event.target.value)}><option value="Todas">Todas as turmas</option>{turmas.map((turma) => <option key={turma} value={turma}>{turma}</option>)}</select></div>
                  <div className="form-group"><label className="form-label">Aluno especifico</label><select className="form-input" value={form.aluno} onChange={(event) => upd("aluno", event.target.value)}><option value="">Turma(s) selecionada(s)</option>{alunos.map((aluno, index) => { const value = rowValue(aluno); return <option key={text(aluno.id || value || index)} value={value}>{rowName(aluno)}{rowClass(aluno) ? ` - ${rowClass(aluno)}` : ""}</option>; })}</select></div>
                  <div className="form-group form-group-span2">
                    <label className="form-label">Turmas adicionais</label>
                    <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(170px, 1fr))", gap: 8 }}>
                      {turmas.map((turma) => <label className="attendance-item" key={turma}><input type="checkbox" checked={form.turmas.includes(turma)} onChange={() => toggleTurma(turma)} />{turma}</label>)}
                    </div>
                  </div>
                  <div className="form-group"><label className="form-label">Disciplina</label><input className="form-input" value={form.disciplina} onChange={(event) => upd("disciplina", event.target.value)} /></div>
                  <div className="form-group"><label className="form-label">Livro / apostila</label><input className="form-input" value={form.livro} onChange={(event) => upd("livro", event.target.value)} /></div>
                  <div className="form-group"><label className="form-label">Capitulo / unidade</label><input className="form-input" value={form.capitulo} onChange={(event) => upd("capitulo", event.target.value)} /></div>
                  <div className="form-group"><label className="form-label">Aula de referencia</label><input className="form-input" value={form.aula_referencia} onChange={(event) => upd("aula_referencia", event.target.value)} /></div>
                  <div className="form-group"><label className="form-label">Habilidade / topico</label><input className="form-input" value={form.habilidade} onChange={(event) => upd("habilidade", event.target.value)} /></div>
                  <div className="form-group"><label className="form-label">Prazo</label><input className="form-input" type="datetime-local" value={form.due_date} onChange={(event) => upd("due_date", event.target.value)} /></div>
                  <div className="form-group"><label className="form-label">Peso total</label><input className="form-input" type="number" value={form.peso} onChange={(event) => upd("peso", event.target.value)} /></div>
                  <div className="form-group"><label className="form-label">Status</label><select className="form-input" value={form.status} onChange={(event) => upd("status", event.target.value)}><option>Ativa</option><option>Rascunho</option><option>Encerrada</option></select></div>
                  <div className="form-group"><label className="form-label">Reenvio</label><label className="attendance-item"><input type="checkbox" checked={form.allow_resubmission} onChange={(event) => upd("allow_resubmission", event.target.checked)} />Permitir reenvio</label></div>
                </div>

                <div className="card" style={{ marginTop: 16 }}>
                  <div className="card-header">
                    <div><div className="section-eyebrow">Conteudo da tarefa</div><h3 className="section-title">Questoes</h3></div>
                    <span className="badge badge-gold">{questions.length} questao(oes)</span>
                  </div>
                  <div className="card-body" style={{ display: "flex", flexDirection: "column", gap: 12 }}>
                    {questions.map((question, index) => (
                      <div className="card" key={question.id}>
                        <div className="card-body">
                          <div className="form-grid">
                            <div className="form-group"><label className="form-label">Tipo</label><select className="form-input" value={question.tipo} onChange={(event) => updateQuestion(index, { tipo: event.target.value as HomeworkQuestion["tipo"] })}><option value="aberta">Dissertativa</option><option value="multipla_escolha">Multipla escolha</option><option value="verdadeiro_falso">Verdadeiro/Falso</option><option value="upload">Upload</option></select></div>
                            <div className="form-group"><label className="form-label">Pontos</label><input className="form-input" type="number" value={question.pontos} onChange={(event) => updateQuestion(index, { pontos: Number(event.target.value) })} /></div>
                            <div className="form-group form-group-span2"><label className="form-label">Enunciado</label><textarea className="form-input form-textarea" rows={3} value={question.enunciado} onChange={(event) => updateQuestion(index, { enunciado: event.target.value })} /></div>
                            {question.tipo === "multipla_escolha" && <div className="form-group form-group-span2"><label className="form-label">Alternativas</label><textarea className="form-input form-textarea" rows={3} value={(question.opcoes || []).join("\n")} onChange={(event) => updateQuestion(index, { opcoes: splitLines(event.target.value) })} /></div>}
                          </div>
                          <div style={{ display: "flex", justifyContent: "flex-end", marginTop: 10 }}><button className="btn btn-secondary btn-sm" type="button" onClick={() => removeQuestion(index)} disabled={questions.length === 1}>Remover questao</button></div>
                        </div>
                      </div>
                    ))}
                    <button className="btn btn-secondary btn-sm" type="button" onClick={addQuestion}>Adicionar questao</button>
                  </div>
                </div>
                {erro && <div className="form-error" style={{ marginTop: 8 }}>{erro}</div>}
              </div>
              <div className="modal-footer">
                <button className="btn btn-secondary" onClick={() => setOpen(false)} disabled={saving}>Cancelar</button>
                <button className="btn btn-primary" onClick={salvar} disabled={saving}>{saving ? "Salvando..." : "Salvar alteracoes"}</button>
              </div>
            </div>
          </div>
        </ModalPortal>
      )}
    </>
  );
}

export function HomeworkDeleteTodayBtn({ todayCount }: { todayCount: number }) {
  const router = useRouter();
  const [saving, setSaving] = useState(false);
  const [msg, setMsg] = useState("");

  async function excluirHoje() {
    if (todayCount === 0) {
      setMsg("Nao ha licoes publicadas hoje para excluir.");
      return;
    }
    if (!confirm(`Excluir TODAS as ${todayCount} licoes publicadas hoje? Esta acao nao pode ser desfeita.`)) return;
    setSaving(true);
    const res = await fetch("/api/licoes?bulk=today", { method: "DELETE" });
    const data = await res.json().catch(() => ({}));
    setSaving(false);
    if (!res.ok) {
      setMsg((data as { error?: string }).error || "Erro ao excluir.");
      return;
    }
    setMsg(`${(data as { deleted?: number }).deleted || 0} licoes excluidas com sucesso.`);
    router.refresh();
  }

  return (
    <div style={{ display: "flex", alignItems: "center", gap: 12, flexWrap: "wrap" }}>
      <button className="btn btn-danger btn-sm" onClick={excluirHoje} disabled={saving || todayCount === 0} title={todayCount === 0 ? "Nenhuma licao publicada hoje" : `Excluir ${todayCount} licoes de hoje`}>
        {saving ? "Excluindo..." : `Excluir todas de hoje${todayCount > 0 ? ` (${todayCount})` : ""}`}
      </button>
      {msg && <span style={{ fontSize: "0.8125rem", color: msg.includes("sucesso") ? "var(--green-700)" : "var(--red-600)" }}>{msg}</span>}
    </div>
  );
}
