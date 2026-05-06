"use client";

import { useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { teacherClassValueByModule } from "@/lib/course-modules";

type Row = Record<string, unknown>;

function text(value: unknown) {
  return String(value || "").trim();
}

function sameName(a: unknown, b: unknown) {
  return text(a).toLowerCase() === text(b).toLowerCase();
}

function classId(turma: Row) {
  return text(turma.id || turma.nome || turma.name);
}

function className(turma: Row) {
  return text(turma.nome || turma.name || "Turma");
}

function moneyValue(value: unknown) {
  const n = parseFloat(String(value || "").replace(/[^\d.,-]/g, "").replace(",", "."));
  return Number.isFinite(n) ? n : 0;
}

function formatBRL(value: number) {
  return value.toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
}

function classModule(turma?: Row) {
  return text(turma?.modulo || turma?.tipo_aula || turma?.modalidade || turma?.nivel);
}

function canSeeAll(role: string) {
  const r = role.toLowerCase();
  return r.includes("admin") || r.includes("coord");
}

export function TeacherClassPanel({
  turmas,
  aulas,
  professores,
  alunos,
  userName,
  userRole
}: {
  turmas: Row[];
  aulas: Row[];
  professores: Row[];
  alunos: Row[];
  userName: string;
  userRole: string;
}) {
  const router = useRouter();
  const [turmaId, setTurmaId] = useState("");
  const [licaoInicio, setLicaoInicio] = useState("");
  const [licaoFim, setLicaoFim] = useState("");
  const [materia, setMateria] = useState("");
  const [tarefa, setTarefa] = useState("");
  const [presentes, setPresentes] = useState<Record<string, boolean>>({});
  const [observacoes, setObservacoes] = useState("");
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState("");

  const visibleClasses = useMemo(() => {
    if (canSeeAll(userRole)) return turmas;
    return turmas.filter((t) => sameName(t.professor, userName));
  }, [turmas, userName, userRole]);

  const selected = visibleClasses.find((t) => classId(t) === turmaId) || visibleClasses[0];
  const selectedId = selected ? classId(selected) : "";
  const openClass = aulas.find((a) => text(a.status) === "aberta" && text(a.turma_id) === selectedId);
  const teacher = professores.find((p) => sameName(p.nome || p.name, selected?.professor)) || {};
  const livro = text(selected?.livro || selected?.book);
  const ultimaLicao = text(selected?.ultima_licao || selected?.licao_atual || selected?.ultima_aula);
  const modulo = classModule(selected);
  const valorAula = teacherClassValueByModule(modulo) || moneyValue(selected?.valor_aula || teacher.valor_aula || teacher.valor_hora || teacher.valor);
  const alunosTurma = alunos.filter((a) => sameName(a.turma || a.classe, className(selected || {})));
  const presencasOk = alunosTurma.length === 0 || alunosTurma.every((a) => presentes[text(a.id || a.login || a.nome || a.name)] !== undefined);

  async function submit(action: "open" | "close") {
    if (!selectedId) return;
    setSaving(true);
    setMessage("");
    const response = await fetch("/api/aulas", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        action,
        turmaId: selectedId,
        licao_inicio: licaoInicio || ultimaLicao,
        licao_fim: licaoFim,
        materia,
        tarefa,
        observacoes,
        valor_aula: valorAula,
        presencas: alunosTurma.map((a) => {
          const id = text(a.id || a.login || a.nome || a.name);
          return { aluno_id: id, aluno: text(a.nome || a.name || a.login), presente: Boolean(presentes[id]) };
        })
      })
    });
    const payload = await response.json().catch(() => ({}));
    setSaving(false);
    if (!response.ok) {
      setMessage(payload.error || "Nao foi possivel salvar a aula.");
      return;
    }
    setMessage(action === "open" ? "Aula aberta com sucesso." : "Aula fechada e financeiro do professor lancado.");
    setLicaoInicio("");
    setLicaoFim("");
    setMateria("");
    setTarefa("");
    setPresentes({});
    setObservacoes("");
    router.refresh();
  }

  if (!visibleClasses.length) {
    return (
      <div className="card teacher-class-panel">
        <div className="empty-state">
          <div className="empty-title">Nenhuma turma disponivel</div>
          <p className="empty-desc">Vincule uma turma ao professor para abrir e fechar aulas.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="card teacher-class-panel">
      <div className="card-header">
        <div>
          <div className="section-eyebrow">Painel do professor</div>
          <h3 className="section-title">Abrir e fechar aula</h3>
          <p className="section-subtitle">O fechamento exige licao, materia, tarefa e presencas.</p>
        </div>
        <span className={`badge badge-${openClass ? "warning" : "success"}`}><span className="badge-dot" />{openClass ? "Aula aberta" : "Pronto para abrir"}</span>
      </div>

      <div className="card-body teacher-class-body">
        <div className="form-grid">
          <div className="form-group form-group-span2">
            <label className="form-label">Turma</label>
            <select className="form-input" value={selectedId} onChange={(e) => setTurmaId(e.target.value)}>
              {visibleClasses.map((t) => <option key={classId(t)} value={classId(t)}>{className(t)} - {text(t.professor || "Sem professor")}</option>)}
            </select>
          </div>
          <div className="form-group">
            <label className="form-label">Livro automatico</label>
            <input className="form-input" value={livro || "Livro nao informado"} readOnly />
          </div>
          <div className="form-group">
            <label className="form-label">Modulo</label>
            <input className="form-input" value={modulo || "Modulo nao informado"} readOnly />
          </div>
          <div className="form-group">
            <label className="form-label">Valor da aula</label>
            <input className="form-input" value={valorAula ? formatBRL(valorAula) : "Sem valor cadastrado"} readOnly />
          </div>
          <div className="form-group">
            <label className="form-label">Licao que inicia</label>
            <input className="form-input" placeholder={ultimaLicao || "Ex: Unidade 4 - pagina 32"} value={licaoInicio || (openClass ? text(openClass.licao_inicio) : "")} onChange={(e) => setLicaoInicio(e.target.value)} readOnly={Boolean(openClass)} />
          </div>
          <div className="form-group">
            <label className="form-label">Licao em que parou</label>
            <input className="form-input" placeholder="Ex: Unidade 4 - pagina 36" value={licaoFim} onChange={(e) => setLicaoFim(e.target.value)} disabled={!openClass} />
          </div>
          <div className="form-group form-group-span2">
            <label className="form-label">Materia / conteudo da aula</label>
            <input className="form-input" placeholder="Ex: Simple Past, paginas 34 a 38" value={materia} onChange={(e) => setMateria(e.target.value)} disabled={!openClass} />
          </div>
          <div className="form-group form-group-span2">
            <label className="form-label">Tarefa de casa</label>
            <input className="form-input" placeholder="Ex: Workbook p. 12 exercicios 1 a 5" value={tarefa} onChange={(e) => setTarefa(e.target.value)} disabled={!openClass} />
          </div>
          <div className="form-group form-group-span2">
            <label className="form-label">Presencas da turma</label>
            <div className="attendance-grid">
              {alunosTurma.length === 0 ? (
                <div className="text-muted text-sm">Nenhum aluno vinculado a esta turma.</div>
              ) : alunosTurma.map((a) => {
                const id = text(a.id || a.login || a.nome || a.name);
                return (
                  <label key={id} className="attendance-item">
                    <input type="checkbox" checked={Boolean(presentes[id])} onChange={(e) => setPresentes((p) => ({ ...p, [id]: e.target.checked }))} disabled={!openClass} />
                    <span>{text(a.nome || a.name || a.login)}</span>
                  </label>
                );
              })}
            </div>
          </div>
          <div className="form-group form-group-span2">
            <label className="form-label">Observacoes da aula</label>
            <textarea className="form-input form-textarea" rows={3} placeholder="Presenca, conteudo, tarefa e observacoes rapidas." value={observacoes} onChange={(e) => setObservacoes(e.target.value)} disabled={!openClass} />
          </div>
        </div>

        {message && <div className={message.includes("sucesso") || message.includes("lancado") ? "form-success" : "form-error"}>{message}</div>}

        <div className="teacher-class-actions">
          {!openClass ? (
            <button className="btn btn-primary" disabled={saving} onClick={() => submit("open")}>
              {saving ? "Abrindo..." : "Abrir aula"}
            </button>
          ) : (
            <button className="btn btn-primary" disabled={saving || !licaoFim.trim() || !materia.trim() || !tarefa.trim() || !presencasOk} onClick={() => submit("close")}>
              {saving ? "Fechando..." : "Fechar aula e lancar financeiro"}
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
