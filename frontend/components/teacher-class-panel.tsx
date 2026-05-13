"use client";

import { useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { teacherClassValueByModule } from "@/lib/course-modules";

type Row = Record<string, unknown>;

function text(value: unknown) {
  return String(value || "").trim();
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

function isAdmin(role: string) {
  const r = role.toLowerCase();
  return r.includes("admin") || r.includes("coord") || r.includes("gestor") || r.includes("diretor");
}

function todayISO() {
  return new Date().toISOString().slice(0, 10);
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
  const admin = isAdmin(userRole);

  // Admins see all turmas; teachers only their own
  const visibleClasses = useMemo(() => {
    if (admin) return turmas;
    return turmas.filter((t) => {
      const prof = text(t.professor);
      return !prof || prof.toLowerCase() === userName.toLowerCase();
    });
  }, [turmas, userName, admin]);

  const professorNames = useMemo(() => {
    const names = professores.map((p) => text(p.nome || p.name || p.usuario || p.login)).filter(Boolean);
    return Array.from(new Set(names)).sort();
  }, [professores]);

  const [turmaId, setTurmaId] = useState("");
  const [professorNome, setProfessorNome] = useState("");
  const [dataAula, setDataAula] = useState(todayISO());
  const [licaoInicio, setLicaoInicio] = useState("");
  const [licaoFim, setLicaoFim] = useState("");
  const [materia, setMateria] = useState("");
  const [tarefa, setTarefa] = useState("");
  const [presentes, setPresentes] = useState<Record<string, boolean>>({});
  const [observacoes, setObservacoes] = useState("");
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState("");
  const [isError, setIsError] = useState(false);

  const selected = useMemo(
    () => visibleClasses.find((t) => classId(t) === turmaId) || visibleClasses[0],
    [visibleClasses, turmaId]
  );
  const selectedId = selected ? classId(selected) : "";

  const openClass = aulas.find(
    (a) => text(a.status) === "aberta" && text(a.turma_id) === selectedId
  );

  const livro = text(selected?.livro || selected?.book);
  const modulo = classModule(selected);
  const ultimaLicao = text(selected?.ultima_licao || selected?.licao_atual || selected?.ultima_aula);

  // Professor: for admin it's the override or the one in the turma; for teacher it's themselves
  const professorEfetivo = admin
    ? (professorNome || text(selected?.professor))
    : userName;

  const teacher = professores.find((p) => {
    const n = text(p.nome || p.name || p.usuario || p.login);
    return n.toLowerCase() === professorEfetivo.toLowerCase();
  }) || {};

  const valorAula =
    teacherClassValueByModule(modulo) ||
    moneyValue(selected?.valor_aula || (teacher as Row).valor_aula || (teacher as Row).valor_hora || (teacher as Row).valor);

  const alunosTurma = alunos.filter((a) => {
    const t = text(a.turma || a.classe);
    return t.toLowerCase() === className(selected || {}).toLowerCase();
  });

  const presencasOk =
    alunosTurma.length === 0 ||
    alunosTurma.every((a) => presentes[text(a.id || a.login || a.nome || a.name)] !== undefined);

  async function submit(action: "open" | "close") {
    if (!selectedId) { setMessage("Selecione uma turma."); setIsError(true); return; }
    setSaving(true);
    setMessage("");
    setIsError(false);

    const response = await fetch("/api/aulas", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        action,
        turmaId: selectedId,
        professor: professorEfetivo,
        data_aula: dataAula,
        licao_inicio: licaoInicio || ultimaLicao,
        licao_fim: licaoFim,
        materia,
        tarefa,
        observacoes,
        valor_aula: valorAula,
        presencas: alunosTurma.map((a) => {
          const id = text(a.id || a.login || a.nome || a.name);
          return {
            aluno_id: id,
            aluno: text(a.nome || a.name || a.login),
            presente: Boolean(presentes[id]),
          };
        }),
      }),
    });

    const payload = await response.json().catch(() => ({}));
    setSaving(false);

    if (!response.ok) {
      setIsError(true);
      setMessage(text((payload as { error?: string }).error || "Nao foi possivel salvar a aula."));
      return;
    }

    setIsError(false);
    setMessage(
      action === "open"
        ? "Aula aberta com sucesso."
        : "Aula fechada e financeiro do professor lancado."
    );
    setLicaoInicio("");
    setLicaoFim("");
    setMateria("");
    setTarefa("");
    setPresentes({});
    setObservacoes("");
    setDataAula(todayISO());
    router.refresh();
  }

  if (!visibleClasses.length) {
    return (
      <div className="card teacher-class-panel">
        <div className="empty-state">
          <div className="empty-title">Nenhuma turma disponivel</div>
          <p className="empty-desc">
            {admin
              ? "Cadastre turmas no módulo de Turmas para lançar aulas."
              : "Solicite ao administrador que vincule uma turma ao seu nome."}
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="card teacher-class-panel">
      <div className="card-header">
        <div>
          <div className="section-eyebrow">Lançamento manual</div>
          <h3 className="section-title">Registrar aula</h3>
          <p className="section-subtitle">
            Abra a aula, preencha conteúdo e presenças, depois feche para gerar o financeiro do professor.
          </p>
        </div>
        <span className={`badge badge-${openClass ? "warning" : "success"}`}>
          <span className="badge-dot" />
          {openClass ? "Aula aberta" : "Pronto para abrir"}
        </span>
      </div>

      <div className="card-body teacher-class-body">
        <div className="form-grid">
          {/* Turma */}
          <div className="form-group form-group-span2">
            <label className="form-label">Turma *</label>
            <select
              className="form-input"
              value={selectedId}
              onChange={(e) => { setTurmaId(e.target.value); setMessage(""); }}
            >
              {visibleClasses.map((t) => (
                <option key={classId(t)} value={classId(t)}>
                  {className(t)} — {text(t.professor || "Sem professor")}
                </option>
              ))}
            </select>
          </div>

          {/* Professor (admin só) */}
          {admin && (
            <div className="form-group">
              <label className="form-label">Professor da aula</label>
              <select
                className="form-input"
                value={professorNome}
                onChange={(e) => setProfessorNome(e.target.value)}
              >
                <option value="">— usar o da turma ({text(selected?.professor) || "sem professor"}) —</option>
                {professorNames.map((n) => (
                  <option key={n} value={n}>{n}</option>
                ))}
              </select>
            </div>
          )}

          {/* Data da aula */}
          <div className="form-group">
            <label className="form-label">Data da aula</label>
            <input
              className="form-input"
              type="date"
              value={dataAula}
              onChange={(e) => setDataAula(e.target.value)}
              readOnly={!admin}
              disabled={!admin}
            />
            {!admin && <div className="form-help">Professor abre e fecha somente a aula do dia. Lancamento manual retroativo fica com ADM/Coordenador.</div>}
          </div>

          {/* Livro e módulo (readonly) */}
          <div className="form-group">
            <label className="form-label">Livro</label>
            <input className="form-input" value={livro || "Não informado"} readOnly />
          </div>
          <div className="form-group">
            <label className="form-label">Módulo</label>
            <input className="form-input" value={modulo || "Não informado"} readOnly />
          </div>

          {/* Valor */}
          <div className="form-group">
            <label className="form-label">Valor da aula</label>
            <input
              className="form-input"
              value={valorAula ? formatBRL(valorAula) : "Sem valor cadastrado"}
              readOnly
            />
          </div>

          {/* Lição início */}
          <div className="form-group">
            <label className="form-label">Lição que inicia</label>
            <input
              className="form-input"
              placeholder={ultimaLicao || "Ex: Unit 4 — página 32"}
              value={licaoInicio || (openClass ? text(openClass.licao_inicio) : "")}
              onChange={(e) => setLicaoInicio(e.target.value)}
              readOnly={Boolean(openClass)}
            />
          </div>

          {/* Lição fim */}
          <div className="form-group">
            <label className="form-label">Lição em que parou</label>
            <input
              className="form-input"
              placeholder="Ex: Unit 4 — página 36"
              value={licaoFim}
              onChange={(e) => setLicaoFim(e.target.value)}
              disabled={!openClass}
            />
          </div>

          {/* Matéria */}
          <div className="form-group form-group-span2">
            <label className="form-label">Matéria / conteúdo da aula</label>
            <input
              className="form-input"
              placeholder="Ex: Simple Past, páginas 34 a 38"
              value={materia}
              onChange={(e) => setMateria(e.target.value)}
              disabled={!openClass}
            />
          </div>

          {/* Tarefa */}
          <div className="form-group form-group-span2">
            <label className="form-label">Tarefa de casa</label>
            <input
              className="form-input"
              placeholder="Ex: Workbook p. 12 exercícios 1 a 5"
              value={tarefa}
              onChange={(e) => setTarefa(e.target.value)}
              disabled={!openClass}
            />
          </div>

          {/* Presenças */}
          <div className="form-group form-group-span2">
            <label className="form-label">Presenças da turma</label>
            <div className="attendance-grid">
              {alunosTurma.length === 0 ? (
                <span style={{ fontSize: "0.85rem", color: "var(--text-muted)" }}>
                  Nenhum aluno vinculado a esta turma.
                </span>
              ) : (
                alunosTurma.map((a) => {
                  const id = text(a.id || a.login || a.nome || a.name);
                  return (
                    <label key={id} className="attendance-item">
                      <input
                        type="checkbox"
                        checked={Boolean(presentes[id])}
                        onChange={(e) =>
                          setPresentes((p) => ({ ...p, [id]: e.target.checked }))
                        }
                        disabled={!openClass}
                      />
                      <span>{text(a.nome || a.name || a.login)}</span>
                    </label>
                  );
                })
              )}
            </div>
          </div>

          {/* Observações */}
          <div className="form-group form-group-span2">
            <label className="form-label">Observações da aula</label>
            <textarea
              className="form-input form-textarea"
              rows={2}
              placeholder="Anotações sobre a aula, alunos, conteúdo, etc."
              value={observacoes}
              onChange={(e) => setObservacoes(e.target.value)}
              disabled={!openClass}
            />
          </div>
        </div>

        {message && (
          <div className={isError ? "form-error" : "form-success"} style={{ marginTop: 12 }}>
            {message}
          </div>
        )}

        <div className="teacher-class-actions">
          {!openClass ? (
            <button
              className="btn btn-primary"
              disabled={saving || !selectedId}
              onClick={() => submit("open")}
            >
              {saving ? "Abrindo..." : "Abrir aula"}
            </button>
          ) : (
            <button
              className="btn btn-primary"
              disabled={
                saving ||
                !licaoFim.trim() ||
                !materia.trim() ||
                !tarefa.trim() ||
                !presencasOk
              }
              onClick={() => submit("close")}
              title={
                !licaoFim.trim()
                  ? "Preencha a lição em que parou"
                  : !materia.trim()
                  ? "Preencha a matéria"
                  : !tarefa.trim()
                  ? "Preencha a tarefa"
                  : !presencasOk
                  ? "Marque a presença de todos os alunos"
                  : ""
              }
            >
              {saving ? "Fechando..." : "Fechar aula e lançar financeiro"}
            </button>
          )}
          {openClass && (
            <span style={{ fontSize: "0.8rem", color: "var(--text-muted)", alignSelf: "center" }}>
              Aula aberta em {text(openClass.inicio).replace("T", " ").slice(0, 16)}
            </span>
          )}
        </div>
      </div>
    </div>
  );
}
