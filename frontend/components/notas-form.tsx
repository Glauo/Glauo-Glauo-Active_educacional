"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";

type Row = Record<string, unknown>;

function text(value: unknown) {
  return String(value || "").trim();
}

export function NotaRapidaForm({ alunos, desafios }: { alunos: Row[]; desafios: Row[] }) {
  const router = useRouter();
  const [aluno, setAluno] = useState("");
  const [desafioId, setDesafioId] = useState("");
  const [nota, setNota] = useState("");
  const [feedback, setFeedback] = useState("");
  const desafio = desafios.find((d) => text(d.id || d.titulo || d.title) === desafioId);

  async function salvar() {
    setFeedback("");
    const alunoNome = text(alunos.find((a) => text(a.id || a.login || a.nome || a.name) === aluno)?.nome || alunos.find((a) => text(a.id || a.login || a.nome || a.name) === aluno)?.name || aluno);
    const titulo = text(desafio?.titulo || desafio?.title);
    const res = await fetch("/api/notas", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        aluno: alunoNome,
        aluno_id: aluno,
        desafio_id: desafioId || titulo,
        titulo,
        nota: Number(nota),
        pontos: Number(nota),
        turma: text(desafio?.turma)
      })
    });
    if (!res.ok) {
      const data = await res.json().catch(() => ({}));
      setFeedback(data.error || "Erro ao salvar nota.");
      return;
    }
    setFeedback("Nota lancada e enviada para o painel do aluno.");
    setNota("");
    router.refresh();
  }

  return (
    <div className="card">
      <div className="card-header">
        <div>
          <div className="section-eyebrow">Correcao</div>
          <h3 className="section-title">Lancar nota de desafio</h3>
          <p className="section-subtitle">A nota aparece automaticamente em Notas e no painel do aluno.</p>
        </div>
      </div>
      <div className="card-body">
        <div className="form-grid">
          <div className="form-group">
            <label className="form-label">Aluno</label>
            <select className="form-input" value={aluno} onChange={(e) => setAluno(e.target.value)}>
              <option value="">Selecione</option>
              {alunos.map((a) => <option key={text(a.id || a.login || a.nome || a.name)} value={text(a.id || a.login || a.nome || a.name)}>{text(a.nome || a.name || a.login)}</option>)}
            </select>
          </div>
          <div className="form-group">
            <label className="form-label">Desafio</label>
            <select className="form-input" value={desafioId} onChange={(e) => setDesafioId(e.target.value)}>
              <option value="">Selecione</option>
              {desafios.map((d) => <option key={text(d.id || d.titulo || d.title)} value={text(d.id || d.titulo || d.title)}>{text(d.titulo || d.title)}</option>)}
            </select>
          </div>
          <div className="form-group">
            <label className="form-label">Nota</label>
            <input className="form-input" type="number" min="0" max="100" value={nota} onChange={(e) => setNota(e.target.value)} />
          </div>
        </div>
        {feedback && <div className={feedback.includes("Erro") ? "form-error" : "form-success"}>{feedback}</div>}
      </div>
      <div className="modal-footer">
        <button className="btn btn-primary" disabled={!aluno || !desafioId || !nota} onClick={salvar}>Salvar nota</button>
      </div>
    </div>
  );
}
