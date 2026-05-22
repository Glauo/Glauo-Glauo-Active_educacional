"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";

type DesafioData = {
  id?: string;
  titulo?: string;
  title?: string;
  turma?: string;
  turmas?: string[] | string;
  aluno?: string;
  descricao?: string;
  pontos?: number | string;
  tipo?: string;
  opcoes?: string[] | string;
  resposta_correta?: string;
  livro?: string;
  licao?: string;
  status?: string;
  [k: string]: unknown;
};

type Form = {
  titulo: string;
  turma: string;
  turmas: string[];
  aluno: string;
  pontos: string;
  descricao: string;
  tipo: string;
  opcoes: string;
  resposta_correta: string;
  livro: string;
  licao: string;
  status: string;
};

type Row = Record<string, unknown>;

function text(value: unknown) {
  return String(value || "").trim();
}

function splitTargets(value: unknown) {
  if (Array.isArray(value)) return value.map(text).filter(Boolean);
  return text(value).split(/[,\n;]/).map((item) => item.trim()).filter(Boolean);
}

function rowName(row: Row) {
  return text(row.nome || row.name || row.aluno || row.login);
}

function rowClass(row: Row) {
  return text(row.turma || row.classe || row.class);
}

function classNames(rows: Row[]) {
  return [...new Set(rows.map((row) => text(row.nome || row.name || row.turma || row.classe)).filter(Boolean))];
}

function toggleTarget(targets: string[], value: string) {
  return targets.includes(value) ? targets.filter((item) => item !== value) : [...targets, value];
}

function fromDesafio(d?: DesafioData): Form {
  return {
    titulo: String(d?.titulo || d?.title || ""),
    turma: String(d?.turma || "Todas"),
    turmas: splitTargets(d?.turmas),
    aluno: String(d?.aluno || ""),
    pontos: String(d?.pontos || "10"),
    descricao: String(d?.descricao || ""),
    tipo: String(d?.tipo || "Pergunta direta"),
    opcoes: Array.isArray(d?.opcoes) ? d.opcoes.join("\n") : String(d?.opcoes || ""),
    resposta_correta: String(d?.resposta_correta || ""),
    livro: String(d?.livro || ""),
    licao: String(d?.licao || ""),
    status: String(d?.status || "Publicado"),
  };
}

function DesafioModal({
  desafio,
  turmas = [],
  alunos = [],
  onClose,
  onSaved,
}: {
  desafio?: DesafioData;
  turmas?: Row[];
  alunos?: Row[];
  onClose: () => void;
  onSaved: () => void;
}) {
  const isEdit = Boolean(desafio?.id);
  const [form, setForm] = useState<Form>(fromDesafio(desafio));
  const [saving, setSaving] = useState(false);
  const [erro, setErro] = useState("");
  const nomesTurmas = classNames(turmas);

  function update(field: keyof Form, value: string) {
    setForm((p) => ({ ...p, [field]: value }));
    setErro("");
  }

  function toggleTurma(turma: string) {
    setForm((prev) => ({ ...prev, turmas: toggleTarget(prev.turmas, turma) }));
    setErro("");
  }

  function gerarComWiz() {
    const livro = form.livro || "livro da turma";
    const licao = form.licao || "licao atual";
    setForm((p) => ({
      ...p,
      titulo: p.titulo || `Desafio Wiz - ${livro} - ${licao}`,
      descricao: `Responda com base no ${livro}, ${licao}. Leia o conteudo, resolva as questoes e justifique suas respostas quando necessario.`,
      tipo: p.tipo || "Multipla escolha",
      opcoes: p.opcoes || "A) Resposta 1\nB) Resposta 2\nC) Resposta 3\nD) Resposta 4",
      resposta_correta: p.resposta_correta || "A"
    }));
  }

  async function excluir() {
    if (!confirm(`Excluir o desafio "${desafio?.titulo}"? Esta acao nao pode ser desfeita.`)) return;
    setSaving(true);
    await fetch(`/api/desafios?id=${desafio!.id}`, { method: "DELETE" });
    setSaving(false);
    onSaved();
  }

  async function salvar() {
    if (!form.titulo.trim()) { setErro("O titulo e obrigatorio."); return; }
    if (!form.pontos || isNaN(Number(form.pontos))) { setErro("Informe um valor de pontos valido."); return; }
    setSaving(true);
    const turmasMarcadas = form.turmas.filter((turma) => turma !== form.turma);
    const usarMarcadas = form.turma === "Todas" && turmasMarcadas.length > 0;
    const payload = {
      ...(isEdit ? { id: desafio!.id } : {}),
      ...form,
      turma: usarMarcadas ? turmasMarcadas[0] : form.turma,
      turmas: usarMarcadas ? turmasMarcadas.slice(1) : turmasMarcadas,
      opcoes: form.opcoes.split("\n").map((o) => o.trim()).filter(Boolean),
      pontos: Number(form.pontos)
    };
    const res = await fetch("/api/desafios", {
      method: isEdit ? "PUT" : "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    setSaving(false);
    if (!res.ok) { const d = await res.json().catch(() => ({})); setErro((d as {error?:string}).error || "Erro ao salvar."); return; }
    onSaved();
  }

  return (
    <div className="modal-overlay" onClick={(e) => e.target === e.currentTarget && onClose()}>
      <div className="modal-box">
        <div className="modal-header">
          <div>
            <div className="modal-title">{isEdit ? "Editar desafio" : "Novo desafio"}</div>
            {isEdit && <div className="modal-subtitle">{desafio?.titulo}</div>}
          </div>
          <button className="modal-close" onClick={onClose}>
            <svg viewBox="0 0 20 20" fill="currentColor"><path fillRule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clipRule="evenodd" /></svg>
          </button>
        </div>
        <div className="modal-body">
          <div className="form-grid">
            <div className="form-group form-group-span2">
              <label className="form-label">Titulo do desafio *</label>
              <input className="form-input" placeholder="Ex: Revise a licao e responda" value={form.titulo} onChange={(e) => update("titulo", e.target.value)} autoFocus />
            </div>
            <div className="form-group"><label className="form-label">Turma principal</label>{nomesTurmas.length > 0 ? <select className="form-input" value={form.turma} onChange={(e) => update("turma", e.target.value)}><option>Todas</option>{nomesTurmas.map((turma) => <option key={turma}>{turma}</option>)}</select> : <input className="form-input" placeholder="Ex: Turma A ou Todas" value={form.turma} onChange={(e) => update("turma", e.target.value)} />}</div>
            <div className="form-group"><label className="form-label">Pontos</label><input className="form-input" type="number" min="0" placeholder="10" value={form.pontos} onChange={(e) => update("pontos", e.target.value)} /></div>
            <div className="form-group form-group-span2">
              <label className="form-label">Turmas adicionais</label>
              {nomesTurmas.length > 0 ? (
                <>
                  <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))", gap: 8 }}>
                    {nomesTurmas.map((turma) => (
                      <label className="attendance-item" key={turma}>
                        <input type="checkbox" checked={form.turmas.includes(turma)} onChange={() => toggleTurma(turma)} />
                        {turma}
                      </label>
                    ))}
                  </div>
                  <div className="form-help">Marque outras turmas para publicar o mesmo desafio em mais de uma turma.</div>
                </>
              ) : (
                <textarea className="form-input form-textarea" rows={2} value={form.turmas.join("\n")} onChange={(e) => setForm((prev) => ({ ...prev, turmas: splitTargets(e.target.value) }))} placeholder="Uma turma por linha" />
              )}
            </div>
            <div className="form-group form-group-span2"><label className="form-label">Aluno especifico</label>{alunos.length > 0 ? <select className="form-input" value={form.aluno} onChange={(e) => update("aluno", e.target.value)}><option value="">Turma(s) selecionada(s)</option>{alunos.map((aluno, index) => <option key={text(aluno.id || aluno.login || index)} value={text(aluno.login || aluno.usuario || rowName(aluno))}>{rowName(aluno)}{rowClass(aluno) ? ` - ${rowClass(aluno)}` : ""}</option>)}</select> : <input className="form-input" value={form.aluno} onChange={(e) => update("aluno", e.target.value)} placeholder="Opcional" />}</div>
            <div className="form-group"><label className="form-label">Tipo de desafio</label><select className="form-input" value={form.tipo} onChange={(e) => update("tipo", e.target.value)}><option>Multipla escolha</option><option>Pergunta direta</option><option>Assinalar</option></select></div>
            <div className="form-group"><label className="form-label">Livro</label><input className="form-input" placeholder="Livro da turma" value={form.livro} onChange={(e) => update("livro", e.target.value)} /></div>
            <div className="form-group"><label className="form-label">Licao</label><input className="form-input" placeholder="Ex: Unidade 4 - pagina 36" value={form.licao} onChange={(e) => update("licao", e.target.value)} /></div>
            <div className="form-group form-group-span2"><label className="form-label">Descricao / enunciado</label><textarea className="form-input form-textarea" rows={4} placeholder="Descreva o desafio, instrucoes e o que o aluno deve entregar..." value={form.descricao} onChange={(e) => update("descricao", e.target.value)} /></div>
            <div className="form-group form-group-span2"><label className="form-label">Opcoes / alternativas</label><textarea className="form-input form-textarea" rows={3} placeholder="Uma alternativa por linha" value={form.opcoes} onChange={(e) => update("opcoes", e.target.value)} /></div>
            <div className="form-group"><label className="form-label">Resposta correta</label><input className="form-input" placeholder="Ex: A ou texto esperado" value={form.resposta_correta} onChange={(e) => update("resposta_correta", e.target.value)} /></div>
            <div className="form-group"><label className="form-label">Status</label><select className="form-input" value={form.status} onChange={(e) => update("status", e.target.value)}><option>Publicado</option><option>Rascunho</option><option>Arquivado</option></select></div>
          </div>
          {erro && <div className="form-error">{erro}</div>}
        </div>
        <div className="modal-footer">
          {isEdit && <button className="btn btn-danger btn-sm" onClick={excluir} disabled={saving} style={{ marginRight: "auto" }}>Excluir</button>}
          <button className="btn btn-secondary" onClick={gerarComWiz} disabled={saving}>Wiz criar licao</button>
          <button className="btn btn-secondary" onClick={onClose} disabled={saving}>Cancelar</button>
          <button className="btn btn-primary" onClick={salvar} disabled={saving}>{saving ? "Salvando..." : isEdit ? "Salvar alteracoes" : "Publicar desafio"}</button>
        </div>
      </div>
    </div>
  );
}

export function NovoDesafioBtn({ turmas, alunos }: { turmas: Row[]; alunos: Row[] }) {
  const router = useRouter();
  const [open, setOpen] = useState(false);
  return (
    <>
      <button className="btn btn-primary" onClick={() => setOpen(true)}>
        <svg viewBox="0 0 20 20" fill="currentColor"><path fillRule="evenodd" d="M10 3a1 1 0 011 1v5h5a1 1 0 110 2h-5v5a1 1 0 11-2 0v-5H4a1 1 0 110-2h5V4a1 1 0 011-1z" clipRule="evenodd" /></svg>
        Novo desafio
      </button>
      {open && <DesafioModal turmas={turmas} alunos={alunos} onClose={() => setOpen(false)} onSaved={() => { setOpen(false); router.refresh(); }} />}
    </>
  );
}

export function EditarDesafioBtn({ desafio }: { desafio: DesafioData }) {
  const router = useRouter();
  const [open, setOpen] = useState(false);
  return (
    <>
      <button className="btn btn-ghost btn-sm" style={{ fontSize: "0.75rem" }} onClick={() => setOpen(true)}>Editar</button>
      {open && <DesafioModal desafio={desafio} onClose={() => setOpen(false)} onSaved={() => { setOpen(false); router.refresh(); }} />}
    </>
  );
}
