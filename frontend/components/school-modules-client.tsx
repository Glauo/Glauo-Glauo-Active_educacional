"use client";

import { useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import type { Homework, HomeworkQuestion, HomeworkSubmission, WallPost } from "@/lib/school-modules";

type Row = Record<string, unknown>;

function text(value: unknown) {
  return String(value || "").trim();
}

function splitLines(value: string) {
  return value.split("\n").map((item) => item.trim()).filter(Boolean);
}

function closeIcon() {
  return <svg viewBox="0 0 20 20" fill="currentColor"><path fillRule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clipRule="evenodd" /></svg>;
}

export function MuralCreateButton({ canPin }: { canPin: boolean }) {
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const [saving, setSaving] = useState(false);
  const [erro, setErro] = useState("");
  const [form, setForm] = useState({
    titulo: "",
    tipo_post: "Aviso Geral",
    mensagem: "",
    turma: "Todas",
    turmas: "",
    aluno: "",
    publicar_em: "",
    expira_em: "",
    anexos: "",
    capa_url: "",
    fixado: false,
    requer_confirmacao: false,
    enquete: "",
  });

  function update(field: keyof typeof form, value: string | boolean) {
    setForm((prev) => ({ ...prev, [field]: value }));
    setErro("");
  }

  async function salvar() {
    if (!form.titulo.trim() || !form.mensagem.trim()) {
      setErro("Titulo e conteudo sao obrigatorios.");
      return;
    }
    setSaving(true);
    const res = await fetch("/api/mural", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        ...form,
        turmas: splitLines(form.turmas),
        anexos: splitLines(form.anexos),
        enquete_opcoes: splitLines(form.enquete).slice(0, 4),
      }),
    });
    setSaving(false);
    if (!res.ok) {
      const data = await res.json().catch(() => ({}));
      setErro(text((data as { error?: string }).error) || "Erro ao publicar.");
      return;
    }
    setOpen(false);
    router.refresh();
  }

  return (
    <>
      <button className="btn btn-primary" onClick={() => setOpen(true)}>
        <svg viewBox="0 0 20 20" fill="currentColor"><path fillRule="evenodd" d="M10 3a1 1 0 011 1v5h5a1 1 0 110 2h-5v5a1 1 0 11-2 0v-5H4a1 1 0 110-2h5V4a1 1 0 011-1z" clipRule="evenodd" /></svg>
        Novo comunicado
      </button>
      {open && (
        <div className="modal-overlay" onClick={(event) => event.currentTarget === event.target && setOpen(false)}>
          <div className="modal-box">
            <div className="modal-header">
              <div>
                <div className="modal-title">Publicar no mural</div>
                <div className="modal-subtitle">Feed institucional para alunos e responsaveis</div>
              </div>
              <button className="modal-close" onClick={() => setOpen(false)}>{closeIcon()}</button>
            </div>
            <div className="modal-body">
              <div className="form-grid">
                <div className="form-group form-group-span2"><label className="form-label">Titulo *</label><input className="form-input" maxLength={100} value={form.titulo} onChange={(e) => update("titulo", e.target.value)} /></div>
                <div className="form-group"><label className="form-label">Tipo</label><select className="form-input" value={form.tipo_post} onChange={(e) => update("tipo_post", e.target.value)}><option>Comunicado Importante</option><option>Evento</option><option>Informacao Pedagogica</option><option>Conquista / Reconhecimento</option><option>Urgente</option><option>Aviso Geral</option></select></div>
                <div className="form-group"><label className="form-label">Turma principal</label><input className="form-input" value={form.turma} onChange={(e) => update("turma", e.target.value)} placeholder="Todas, 8A, Teens..." /></div>
                <div className="form-group form-group-span2"><label className="form-label">Conteudo *</label><textarea className="form-input form-textarea" rows={5} value={form.mensagem} onChange={(e) => update("mensagem", e.target.value)} placeholder="Escreva o comunicado com clareza..." /></div>
                <div className="form-group"><label className="form-label">Turmas adicionais</label><textarea className="form-input form-textarea" rows={3} value={form.turmas} onChange={(e) => update("turmas", e.target.value)} placeholder="Uma turma por linha" /></div>
                <div className="form-group"><label className="form-label">Aluno especifico</label><input className="form-input" value={form.aluno} onChange={(e) => update("aluno", e.target.value)} placeholder="Opcional" /></div>
                <div className="form-group"><label className="form-label">Publicar em</label><input className="form-input" type="datetime-local" value={form.publicar_em} onChange={(e) => update("publicar_em", e.target.value)} /></div>
                <div className="form-group"><label className="form-label">Expira em</label><input className="form-input" type="datetime-local" value={form.expira_em} onChange={(e) => update("expira_em", e.target.value)} /></div>
                <div className="form-group"><label className="form-label">Anexos / links</label><textarea className="form-input form-textarea" rows={3} value={form.anexos} onChange={(e) => update("anexos", e.target.value)} placeholder="Um link por linha" /></div>
                <div className="form-group"><label className="form-label">Imagem de capa</label><input className="form-input" value={form.capa_url} onChange={(e) => update("capa_url", e.target.value)} placeholder="URL da imagem" /></div>
                <div className="form-group"><label className="form-label">Enquete</label><textarea className="form-input form-textarea" rows={3} value={form.enquete} onChange={(e) => update("enquete", e.target.value)} placeholder="Ate 4 opcoes, uma por linha" /></div>
                <div className="form-group">
                  <label className="form-label">Regras</label>
                  <label className="attendance-item"><input type="checkbox" checked={form.requer_confirmacao} onChange={(e) => update("requer_confirmacao", e.target.checked)} /> Confirmacao de leitura</label>
                  {canPin && <label className="attendance-item" style={{ marginTop: 8 }}><input type="checkbox" checked={form.fixado} onChange={(e) => update("fixado", e.target.checked)} /> Fixar no topo</label>}
                </div>
              </div>
              {erro && <div className="form-error">{erro}</div>}
            </div>
            <div className="modal-footer">
              <button className="btn btn-secondary" disabled={saving} onClick={() => setOpen(false)}>Cancelar</button>
              <button className="btn btn-primary" disabled={saving} onClick={salvar}>{saving ? "Publicando..." : "Publicar"}</button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}

export function MuralConfirmButton({ post, compact = false }: { post: WallPost; compact?: boolean }) {
  const router = useRouter();
  const [opcao, setOpcao] = useState("");
  const [saving, setSaving] = useState(false);
  const opcoes = Array.isArray(post.enquete_opcoes) ? post.enquete_opcoes : [];

  async function confirmar() {
    setSaving(true);
    await fetch("/api/mural/confirm", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ id: post.id, opcao }),
    });
    setSaving(false);
    router.refresh();
  }

  return (
    <div style={{ display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap" }}>
      {opcoes.length > 0 && (
        <select className="form-input" style={{ width: compact ? 160 : 240, height: 36 }} value={opcao} onChange={(e) => setOpcao(e.target.value)}>
          <option value="">Votar na enquete</option>
          {opcoes.map((item) => <option key={item} value={item}>{item}</option>)}
        </select>
      )}
      <button className="btn btn-secondary btn-sm" onClick={confirmar} disabled={saving || (opcoes.length > 0 && !opcao && !post.requer_confirmacao)}>
        {saving ? "Registrando..." : post.requer_confirmacao ? "Li e entendi" : "Registrar"}
      </button>
    </div>
  );
}

export function HomeworkCreateButton({ turmas, alunos }: { turmas: Row[]; alunos: Row[] }) {
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const [saving, setSaving] = useState(false);
  const [erro, setErro] = useState("");
  const [form, setForm] = useState({
    titulo: "",
    disciplina: "",
    turma: "Todas",
    aluno: "",
    due_date: "",
    livro: "",
    capitulo: "",
    aula_referencia: "",
    habilidade: "",
    descricao: "",
    peso: "10",
    allow_resubmission: false,
    quantidade: "5",
    dificuldade: "Medio",
    foco: "",
  });
  const [questions, setQuestions] = useState<HomeworkQuestion[]>([{
    id: crypto.randomUUID(),
    tipo: "aberta",
    enunciado: "",
    pontos: 10,
  }]);

  function update(field: keyof typeof form, value: string | boolean) {
    setForm((prev) => ({ ...prev, [field]: value }));
    setErro("");
  }

  function updateQuestion(index: number, patch: Partial<HomeworkQuestion>) {
    setQuestions((prev) => prev.map((question, i) => i === index ? { ...question, ...patch } : question));
  }

  async function gerarWiz() {
    setSaving(true);
    const res = await fetch("/api/licoes/wiz", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(form),
    });
    const data = await res.json().catch(() => ({}));
    setSaving(false);
    if (!res.ok) {
      setErro(text(data.error) || "Erro ao gerar com Prof Wiz.");
      return;
    }
    setForm((prev) => ({ ...prev, titulo: text(data.titulo) || prev.titulo, descricao: text(data.descricao) || prev.descricao }));
    setQuestions(Array.isArray(data.questions) ? data.questions : questions);
  }

  async function salvar(status: "Ativa" | "Rascunho") {
    if (!form.titulo.trim()) {
      setErro("Titulo da licao e obrigatorio.");
      return;
    }
    setSaving(true);
    const payload = {
      ...form,
      status,
      peso: Number(form.peso) || 10,
      questions: questions.map((question) => ({
        ...question,
        enunciado: text(question.enunciado) || "Questao sem enunciado",
        opcoes: Array.isArray(question.opcoes) ? question.opcoes : [],
        pontos: Number(question.pontos) || 1,
      })),
    };
    const res = await fetch("/api/licoes", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    setSaving(false);
    if (!res.ok) {
      const data = await res.json().catch(() => ({}));
      setErro(text(data.error) || "Erro ao salvar licao.");
      return;
    }
    setOpen(false);
    router.refresh();
  }

  return (
    <>
      <button className="btn btn-primary" onClick={() => setOpen(true)}>
        <svg viewBox="0 0 20 20" fill="currentColor"><path fillRule="evenodd" d="M10 3a1 1 0 011 1v5h5a1 1 0 110 2h-5v5a1 1 0 11-2 0v-5H4a1 1 0 110-2h5V4a1 1 0 011-1z" clipRule="evenodd" /></svg>
        Nova licao
      </button>
      {open && (
        <div className="modal-overlay" onClick={(event) => event.currentTarget === event.target && setOpen(false)}>
          <div className="modal-box" style={{ maxWidth: 980 }}>
            <div className="modal-header">
              <div>
                <div className="modal-title">Nova licao de casa</div>
                <div className="modal-subtitle">Crie manualmente ou gere uma base revisavel com Prof Wiz</div>
              </div>
              <button className="modal-close" onClick={() => setOpen(false)}>{closeIcon()}</button>
            </div>
            <div className="modal-body">
              <div className="form-grid">
                <div className="form-group form-group-span2"><label className="form-label">Titulo *</label><input className="form-input" value={form.titulo} onChange={(e) => update("titulo", e.target.value)} /></div>
                <div className="form-group"><label className="form-label">Disciplina</label><input className="form-input" value={form.disciplina} onChange={(e) => update("disciplina", e.target.value)} placeholder="Ingles, Matematica..." /></div>
                <div className="form-group"><label className="form-label">Turma</label><select className="form-input" value={form.turma} onChange={(e) => update("turma", e.target.value)}><option>Todas</option>{turmas.map((t, i) => <option key={text(t.id || t.nome || t.name || i)}>{text(t.nome || t.name || `Turma ${i + 1}`)}</option>)}</select></div>
                <div className="form-group"><label className="form-label">Aluno especifico</label><select className="form-input" value={form.aluno} onChange={(e) => update("aluno", e.target.value)}><option value="">Turma inteira</option>{alunos.map((a, i) => <option key={text(a.id || a.login || i)}>{text(a.nome || a.name || a.login)}</option>)}</select></div>
                <div className="form-group"><label className="form-label">Prazo</label><input className="form-input" type="datetime-local" value={form.due_date} onChange={(e) => update("due_date", e.target.value)} /></div>
                <div className="form-group"><label className="form-label">Livro / apostila</label><input className="form-input" value={form.livro} onChange={(e) => update("livro", e.target.value)} /></div>
                <div className="form-group"><label className="form-label">Capitulo / unidade</label><input className="form-input" value={form.capitulo} onChange={(e) => update("capitulo", e.target.value)} /></div>
                <div className="form-group"><label className="form-label">Aula de referencia</label><input className="form-input" value={form.aula_referencia} onChange={(e) => update("aula_referencia", e.target.value)} /></div>
                <div className="form-group"><label className="form-label">Habilidade / topico</label><input className="form-input" value={form.habilidade} onChange={(e) => update("habilidade", e.target.value)} /></div>
                <div className="form-group"><label className="form-label">Peso</label><input className="form-input" type="number" value={form.peso} onChange={(e) => update("peso", e.target.value)} /></div>
                <div className="form-group form-group-span2"><label className="form-label">Instrucoes</label><textarea className="form-input form-textarea" rows={4} value={form.descricao} onChange={(e) => update("descricao", e.target.value)} /></div>
              </div>

              <div className="card" style={{ marginTop: 16 }}>
                <div className="card-header">
                  <div>
                    <div className="section-eyebrow">Prof Wiz</div>
                    <h3 className="section-title">Geracao assistida</h3>
                  </div>
                  <button className="btn btn-secondary btn-sm" onClick={gerarWiz} disabled={saving}>Gerar com Prof Wiz</button>
                </div>
                <div className="card-body">
                  <div className="form-grid">
                    <div className="form-group"><label className="form-label">Questoes</label><input className="form-input" type="number" value={form.quantidade} onChange={(e) => update("quantidade", e.target.value)} /></div>
                    <div className="form-group"><label className="form-label">Dificuldade</label><select className="form-input" value={form.dificuldade} onChange={(e) => update("dificuldade", e.target.value)}><option>Facil</option><option>Medio</option><option>Dificil</option><option>Adaptativo</option></select></div>
                    <div className="form-group form-group-span2"><label className="form-label">Foco especifico</label><input className="form-input" value={form.foco} onChange={(e) => update("foco", e.target.value)} /></div>
                  </div>
                </div>
              </div>

              <div style={{ display: "flex", flexDirection: "column", gap: 12, marginTop: 16 }}>
                {questions.map((question, index) => (
                  <div className="card" key={question.id}>
                    <div className="card-body">
                      <div className="form-grid">
                        <div className="form-group"><label className="form-label">Tipo</label><select className="form-input" value={question.tipo} onChange={(e) => updateQuestion(index, { tipo: e.target.value as HomeworkQuestion["tipo"] })}><option value="aberta">Dissertativa</option><option value="multipla_escolha">Multipla escolha</option><option value="verdadeiro_falso">Verdadeiro/Falso</option><option value="upload">Upload</option></select></div>
                        <div className="form-group"><label className="form-label">Pontos</label><input className="form-input" type="number" value={question.pontos} onChange={(e) => updateQuestion(index, { pontos: Number(e.target.value) })} /></div>
                        <div className="form-group form-group-span2"><label className="form-label">Enunciado</label><textarea className="form-input form-textarea" rows={3} value={question.enunciado} onChange={(e) => updateQuestion(index, { enunciado: e.target.value })} /></div>
                        {question.tipo === "multipla_escolha" && <><div className="form-group form-group-span2"><label className="form-label">Alternativas</label><textarea className="form-input form-textarea" rows={3} value={(question.opcoes || []).join("\n")} onChange={(e) => updateQuestion(index, { opcoes: splitLines(e.target.value) })} /></div><div className="form-group"><label className="form-label">Correta (0=A)</label><input className="form-input" type="number" min={0} value={question.correta_idx ?? 0} onChange={(e) => updateQuestion(index, { correta_idx: Number(e.target.value) })} /></div></>}
                        {question.tipo === "verdadeiro_falso" && <div className="form-group"><label className="form-label">Gabarito</label><select className="form-input" value={question.correta_texto || "V"} onChange={(e) => updateQuestion(index, { correta_texto: e.target.value })}><option value="V">Verdadeiro</option><option value="F">Falso</option></select></div>}
                      </div>
                    </div>
                  </div>
                ))}
                <button className="btn btn-secondary btn-sm" onClick={() => setQuestions((prev) => [...prev, { id: crypto.randomUUID(), tipo: "aberta", enunciado: "", pontos: 1 }])}>Adicionar questao</button>
              </div>
              <label className="attendance-item" style={{ marginTop: 16 }}><input type="checkbox" checked={form.allow_resubmission} onChange={(e) => update("allow_resubmission", e.target.checked)} /> Permitir reenvio</label>
              {erro && <div className="form-error">{erro}</div>}
            </div>
            <div className="modal-footer">
              <button className="btn btn-secondary" disabled={saving} onClick={() => salvar("Rascunho")}>Salvar rascunho</button>
              <button className="btn btn-primary" disabled={saving} onClick={() => salvar("Ativa")}>{saving ? "Salvando..." : "Salvar e publicar"}</button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}

export function HomeworkSubmitForm({ homework, submission }: { homework: Homework; submission?: HomeworkSubmission }) {
  const router = useRouter();
  const [answers, setAnswers] = useState<Record<string, string>>((submission?.answers as Record<string, string>) || {});
  const [feedback, setFeedback] = useState("");
  const [saving, setSaving] = useState(false);
  const questions = homework.questions || [];
  const done = text(submission?.status);

  function update(id: string, value: string) {
    setAnswers((prev) => ({ ...prev, [id]: value }));
    setFeedback("");
  }

  async function enviar() {
    setSaving(true);
    const res = await fetch("/api/licoes/submit", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ activity_id: homework.id, answers }),
    });
    const data = await res.json().catch(() => ({}));
    setSaving(false);
    if (!res.ok) {
      setFeedback(text(data.error) || "Erro ao enviar.");
      return;
    }
    setFeedback("Licao enviada com sucesso.");
    router.refresh();
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
      {questions.map((question, index) => (
        <div key={question.id} className="card">
          <div className="card-body">
            <div className="section-eyebrow">Questao {index + 1} de {questions.length} | {question.pontos} pts</div>
            <h3 className="section-title" style={{ fontSize: "1rem", marginBottom: 10 }}>{question.enunciado}</h3>
            {question.tipo === "multipla_escolha" ? (
              <div style={{ display: "grid", gap: 8 }}>
                {(question.opcoes || []).map((opcao, optionIndex) => (
                  <label className="attendance-item" key={`${question.id}_${optionIndex}`}>
                    <input type="radio" name={question.id} checked={answers[question.id] === String(optionIndex)} onChange={() => update(question.id, String(optionIndex))} disabled={done === "Corrigido"} />
                    {String.fromCharCode(65 + optionIndex)}) {opcao}
                  </label>
                ))}
              </div>
            ) : question.tipo === "verdadeiro_falso" ? (
              <div style={{ display: "flex", gap: 8 }}><button className={`btn ${answers[question.id] === "V" ? "btn-primary" : "btn-secondary"}`} onClick={() => update(question.id, "V")} disabled={done === "Corrigido"}>Verdadeiro</button><button className={`btn ${answers[question.id] === "F" ? "btn-primary" : "btn-secondary"}`} onClick={() => update(question.id, "F")} disabled={done === "Corrigido"}>Falso</button></div>
            ) : (
              <textarea className="form-input form-textarea" rows={4} value={answers[question.id] || ""} onChange={(e) => update(question.id, e.target.value)} disabled={done === "Corrigido"} placeholder={question.tipo === "upload" ? "Cole aqui o link do arquivo enviado ou descreva o anexo." : "Digite sua resposta..."} />
            )}
          </div>
        </div>
      ))}
      {submission?.status === "Corrigido" && <div className="form-success">Corrigida: nota {Number(submission.score || 0).toFixed(1)}. {text(submission.feedback)}</div>}
      {feedback && <div className={feedback.includes("sucesso") ? "form-success" : "form-error"}>{feedback}</div>}
      <button className="btn btn-primary" onClick={enviar} disabled={saving || (submission && !homework.allow_resubmission && submission.status !== "Rascunho")}>{saving ? "Enviando..." : submission ? "Reenviar licao" : "Enviar licao"}</button>
    </div>
  );
}

export function HomeworkReviewForm({ submission, homework }: { submission: HomeworkSubmission; homework?: Homework }) {
  const router = useRouter();
  const maxScore = useMemo(() => (homework?.questions || []).reduce((sum, question) => sum + (Number(question.pontos) || 0), 0) || 10, [homework]);
  const [score, setScore] = useState(String(submission.score ?? 0));
  const [feedback, setFeedback] = useState(text(submission.feedback));
  const [msg, setMsg] = useState("");
  const [saving, setSaving] = useState(false);

  async function salvar() {
    setSaving(true);
    const res = await fetch("/api/licoes/review", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ submission_id: submission.id, score: Number(score), feedback }),
    });
    const data = await res.json().catch(() => ({}));
    setSaving(false);
    if (!res.ok) {
      setMsg(text(data.error) || "Erro ao corrigir.");
      return;
    }
    setMsg("Correcao salva e nota lancada.");
    router.refresh();
  }

  return (
    <div style={{ display: "grid", gridTemplateColumns: "120px minmax(220px, 1fr) auto", gap: 8, alignItems: "end" }}>
      <div className="form-group"><label className="form-label">Nota / {maxScore}</label><input className="form-input" type="number" min={0} max={maxScore} value={score} onChange={(e) => setScore(e.target.value)} /></div>
      <div className="form-group"><label className="form-label">Feedback</label><input className="form-input" value={feedback} onChange={(e) => setFeedback(e.target.value)} placeholder="Comentario para o aluno" /></div>
      <button className="btn btn-primary" onClick={salvar} disabled={saving}>{saving ? "Salvando..." : "Salvar"}</button>
      {msg && <div className={msg.includes("salva") ? "form-success" : "form-error"} style={{ gridColumn: "1 / -1" }}>{msg}</div>}
    </div>
  );
}
