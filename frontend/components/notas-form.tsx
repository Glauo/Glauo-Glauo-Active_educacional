"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";

type Row = Record<string, unknown>;

function text(value: unknown) {
  return String(value || "").trim();
}

function rowKey(row: Row) {
  return text(row.id || row.login || row.nome || row.name);
}

function rowName(row?: Row) {
  return text(row?.nome || row?.name || row?.login);
}

function todayInputValue() {
  const now = new Date();
  const year = now.getFullYear();
  const month = String(now.getMonth() + 1).padStart(2, "0");
  const day = String(now.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

export function NotaRapidaForm({
  alunos,
  desafios,
  canManageManual = false
}: {
  alunos: Row[];
  desafios: Row[];
  canManageManual?: boolean;
}) {
  const router = useRouter();
  const [aluno, setAluno] = useState("");
  const [desafioId, setDesafioId] = useState("");
  const [tituloNota, setTituloNota] = useState("");
  const [nota, setNota] = useState("");
  const [feedback, setFeedback] = useState("");
  const [faltaAluno, setFaltaAluno] = useState("");
  const [faltaData, setFaltaData] = useState(todayInputValue());
  const [faltaMateria, setFaltaMateria] = useState("");
  const [faltaObservacoes, setFaltaObservacoes] = useState("");
  const [faltaFeedback, setFaltaFeedback] = useState("");
  const [salvandoFalta, setSalvandoFalta] = useState(false);
  const desafio = desafios.find((d) => text(d.id || d.titulo || d.title) === desafioId);
  const alunoSelecionado = alunos.find((a) => rowKey(a) === aluno);
  const faltaAlunoSelecionado = alunos.find((a) => rowKey(a) === faltaAluno);
  const notaTitulo = text(desafio?.titulo || desafio?.title || tituloNota);
  const podeSalvarNota = Boolean(aluno && nota && (desafioId || (canManageManual && tituloNota.trim())));

  async function salvar() {
    setFeedback("");
    const alunoNome = rowName(alunoSelecionado) || aluno;
    const titulo = notaTitulo;
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
        turma: text(alunoSelecionado?.turma || alunoSelecionado?.classe || desafio?.turma),
        origem: desafioId ? "desafio" : "lancamento_manual_adm"
      })
    });
    if (!res.ok) {
      const data = await res.json().catch(() => ({})) as { error?: string };
      setFeedback(data.error || "Erro ao salvar nota.");
      return;
    }
    setFeedback("Nota lancada e enviada para o painel do aluno.");
    setNota("");
    setTituloNota("");
    setDesafioId("");
    router.refresh();
  }

  async function salvarFalta() {
    setFaltaFeedback("");
    setSalvandoFalta(true);
    const alunoNome = rowName(faltaAlunoSelecionado) || faltaAluno;
    const res = await fetch("/api/frequencias", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        aluno: alunoNome,
        aluno_id: faltaAluno,
        turma: text(faltaAlunoSelecionado?.turma || faltaAlunoSelecionado?.classe),
        data: faltaData,
        materia: faltaMateria,
        observacoes: faltaObservacoes
      })
    });
    setSalvandoFalta(false);
    if (!res.ok) {
      const data = await res.json().catch(() => ({})) as { error?: string };
      setFaltaFeedback(data.error || "Erro ao lancar falta.");
      return;
    }
    setFaltaFeedback("Falta lancada no historico do aluno.");
    setFaltaMateria("");
    setFaltaObservacoes("");
    router.refresh();
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "18px" }}>
      <div className="card">
        <div className="card-header">
          <div>
            <div className="section-eyebrow">Correcao</div>
            <h3 className="section-title">Lancar nota para aluno</h3>
            <p className="section-subtitle">Use um desafio existente ou informe uma atividade manual para registrar a nota no painel do aluno.</p>
          </div>
        </div>
        <div className="card-body">
          <div className="form-grid">
            <div className="form-group">
              <label className="form-label">Aluno</label>
              <select className="form-input" value={aluno} onChange={(e) => setAluno(e.target.value)}>
                <option value="">Selecione</option>
                {alunos.map((a) => <option key={rowKey(a)} value={rowKey(a)}>{rowName(a)}</option>)}
              </select>
            </div>
            <div className="form-group">
              <label className="form-label">Desafio</label>
              <select className="form-input" value={desafioId} onChange={(e) => setDesafioId(e.target.value)}>
                <option value="">Sem desafio vinculado</option>
                {desafios.map((d) => <option key={text(d.id || d.titulo || d.title)} value={text(d.id || d.titulo || d.title)}>{text(d.titulo || d.title)}</option>)}
              </select>
            </div>
            {canManageManual && (
              <div className="form-group">
                <label className="form-label">Atividade / descricao</label>
                <input
                  className="form-input"
                  value={tituloNota}
                  onChange={(e) => setTituloNota(e.target.value)}
                  placeholder="Ex: Participacao, prova oral, recuperacao..."
                  disabled={Boolean(desafioId)}
                />
              </div>
            )}
            <div className="form-group">
              <label className="form-label">Nota</label>
              <input className="form-input" type="number" min="0" max="100" value={nota} onChange={(e) => setNota(e.target.value)} />
            </div>
          </div>
          {feedback && <div className={feedback.includes("Erro") ? "form-error" : "form-success"}>{feedback}</div>}
        </div>
        <div className="modal-footer">
          <button className="btn btn-primary" disabled={!podeSalvarNota} onClick={salvar}>Salvar nota</button>
        </div>
      </div>

      {canManageManual && (
        <div className="card">
          <div className="card-header">
            <div>
              <div className="section-eyebrow">Frequencia</div>
              <h3 className="section-title">Lancar falta manual</h3>
              <p className="section-subtitle">Registro restrito a administradores e coordenadores para ajustes pontuais no historico do aluno.</p>
            </div>
          </div>
          <div className="card-body">
            <div className="form-grid">
              <div className="form-group">
                <label className="form-label">Aluno</label>
                <select className="form-input" value={faltaAluno} onChange={(e) => setFaltaAluno(e.target.value)}>
                  <option value="">Selecione</option>
                  {alunos.map((a) => <option key={rowKey(a)} value={rowKey(a)}>{rowName(a)}</option>)}
                </select>
              </div>
              <div className="form-group">
                <label className="form-label">Data da falta</label>
                <input className="form-input" type="date" value={faltaData} onChange={(e) => setFaltaData(e.target.value)} />
              </div>
              <div className="form-group">
                <label className="form-label">Materia / aula</label>
                <input className="form-input" value={faltaMateria} onChange={(e) => setFaltaMateria(e.target.value)} placeholder="Ex: Aula regular, reposicao..." />
              </div>
              <div className="form-group" style={{ gridColumn: "1 / -1" }}>
                <label className="form-label">Observacoes</label>
                <textarea className="form-input" rows={3} value={faltaObservacoes} onChange={(e) => setFaltaObservacoes(e.target.value)} placeholder="Motivo ou detalhe interno, se houver." />
              </div>
            </div>
            {faltaFeedback && <div className={faltaFeedback.includes("Erro") ? "form-error" : "form-success"}>{faltaFeedback}</div>}
          </div>
          <div className="modal-footer">
            <button className="btn btn-primary" disabled={!faltaAluno || !faltaData || salvandoFalta} onClick={salvarFalta}>
              {salvandoFalta ? "Lancando..." : "Lancar falta"}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
