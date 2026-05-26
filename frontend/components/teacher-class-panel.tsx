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

function currentTime() {
  return new Date().toTimeString().slice(0, 5);
}

function todayFormatted() {
  return new Date().toLocaleDateString("pt-BR", { weekday: "long", day: "2-digit", month: "long" });
}

function formatOpenTime(isoStr: string) {
  if (!isoStr) return "";
  const d = new Date(isoStr);
  if (Number.isNaN(d.getTime())) return isoStr;
  return d.toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" });
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
  const [tipoAula, setTipoAula] = useState("Aula Normal");
  const [professorNome, setProfessorNome] = useState("");
  const [dataAula, setDataAula] = useState(todayISO());
  const [horaInicio, setHoraInicio] = useState(currentTime());
  const [licaoInicio, setLicaoInicio] = useState("");
  const [licaoFim, setLicaoFim] = useState("");
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

  const alunosTurma = useMemo(() => alunos.filter((a) => {
    const t = text(a.turma || a.classe);
    return t.toLowerCase() === className(selected || {}).toLowerCase();
  }), [alunos, selected]);

  const presencasOk =
    alunosTurma.length === 0 ||
    alunosTurma.every((a) => presentes[text(a.id || a.login || a.nome || a.name)] !== undefined);

  const materiaAuto = openClass
    ? text(openClass.tipo_aula || openClass.modulo || tipoAula)
    : tipoAula;

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
        hora_inicio: horaInicio,
        tipo_aula: tipoAula,
        licao_inicio: licaoInicio || ultimaLicao,
        licao_fim: licaoFim,
        materia: materiaAuto,
        tarefa: "",
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
    setMessage(action === "open" ? "Aula aberta com sucesso." : "Aula fechada e financeiro do professor lancado.");
    setLicaoInicio("");
    setLicaoFim("");
    setPresentes({});
    setObservacoes("");
    setHoraInicio(currentTime());
    if (admin) setDataAula(todayISO());
    router.refresh();
  }

  function marcarTodos(presente: boolean) {
    const next: Record<string, boolean> = {};
    alunosTurma.forEach((a) => {
      next[text(a.id || a.login || a.nome || a.name)] = presente;
    });
    setPresentes(next);
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
          <div className="section-eyebrow">{openClass ? "Aula em andamento" : "Registrar aula"}</div>
          <h3 className="section-title">{openClass ? className(selected || {}) : "Abrir aula"}</h3>
          <p className="section-subtitle">
            {openClass
              ? `Aberta às ${formatOpenTime(text(openClass.inicio))} · ${text(openClass.tipo_aula || openClass.modulo || "Aula Normal")}`
              : `${userName} · ${todayFormatted()}`}
          </p>
        </div>
        <span className={`badge badge-${openClass ? "warning" : "success"}`}>
          <span className="badge-dot" />
          {openClass ? "Em andamento" : "Pronto para abrir"}
        </span>
      </div>

      <div className="card-body teacher-class-body">

        {/* ── ESTADO: NENHUMA AULA ABERTA ── */}
        {!openClass && (
          <div className="form-grid">
            {/* Info do professor (readonly) */}
            <div className="form-group form-group-span2" style={{ background: "var(--surface-raised)", borderRadius: "var(--radius-md)", padding: "12px 14px", display: "flex", gap: 24, flexWrap: "wrap" }}>
              <div style={{ display: "flex", flexDirection: "column", gap: 2 }}>
                <span style={{ fontSize: "0.68rem", textTransform: "uppercase", color: "var(--text-muted)", letterSpacing: "0.08em" }}>Professor</span>
                <span style={{ fontWeight: 700, fontSize: "0.95rem" }}>{professorEfetivo || userName}</span>
              </div>
              <div style={{ display: "flex", flexDirection: "column", gap: 2 }}>
                <span style={{ fontSize: "0.68rem", textTransform: "uppercase", color: "var(--text-muted)", letterSpacing: "0.08em" }}>Data</span>
                <span style={{ fontWeight: 700, fontSize: "0.95rem" }}>{admin ? dataAula : new Date().toLocaleDateString("pt-BR")}</span>
              </div>
              {livro && (
                <div style={{ display: "flex", flexDirection: "column", gap: 2 }}>
                  <span style={{ fontSize: "0.68rem", textTransform: "uppercase", color: "var(--text-muted)", letterSpacing: "0.08em" }}>Livro</span>
                  <span style={{ fontWeight: 700, fontSize: "0.95rem" }}>{livro}</span>
                </div>
              )}
              {ultimaLicao && (
                <div style={{ display: "flex", flexDirection: "column", gap: 2 }}>
                  <span style={{ fontSize: "0.68rem", textTransform: "uppercase", color: "var(--text-muted)", letterSpacing: "0.08em" }}>Última lição</span>
                  <span style={{ fontWeight: 600, fontSize: "0.9rem", color: "var(--text-secondary)" }}>{ultimaLicao}</span>
                </div>
              )}
            </div>

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
                    {className(t)}{admin ? ` — ${text(t.professor || "Sem professor")}` : ""}
                  </option>
                ))}
              </select>
            </div>

            {/* Tipo de aula */}
            <div className="form-group form-group-span2">
              <label className="form-label">Tipo de aula</label>
              <div style={{ display: "flex", gap: 12 }}>
                {["Aula Normal", "Reposição"].map((tipo) => (
                  <label key={tipo} style={{ display: "flex", alignItems: "center", gap: 8, cursor: "pointer", padding: "8px 16px", borderRadius: "var(--radius-md)", border: `2px solid ${tipoAula === tipo ? "var(--blue-600)" : "var(--border)"}`, background: tipoAula === tipo ? "rgba(37,99,235,0.06)" : "transparent", fontWeight: tipoAula === tipo ? 700 : 400, fontSize: "0.9rem" }}>
                    <input
                      type="radio"
                      name="tipoAula"
                      value={tipo}
                      checked={tipoAula === tipo}
                      onChange={() => setTipoAula(tipo)}
                      style={{ accentColor: "var(--blue-600)" }}
                    />
                    {tipo}
                  </label>
                ))}
              </div>
            </div>

            {/* Hora de início + Lição que inicia */}
            <div className="form-group">
              <label className="form-label">Hora de início</label>
              <input
                className="form-input"
                type="time"
                value={horaInicio}
                onChange={(e) => setHoraInicio(e.target.value)}
              />
              <div className="form-help">Preenchido com o horário atual automaticamente.</div>
            </div>

            <div className="form-group">
              <label className="form-label">Lição que inicia</label>
              <input
                className="form-input"
                placeholder={ultimaLicao || "Ex: Unit 4 pág 32"}
                value={licaoInicio}
                onChange={(e) => setLicaoInicio(e.target.value)}
              />
              {ultimaLicao && <div className="form-help">Última registrada: {ultimaLicao}</div>}
            </div>

            {/* Campos extras para admin */}
            {admin && (
              <>
                <div className="form-group">
                  <label className="form-label">Professor da aula</label>
                  <select className="form-input" value={professorNome} onChange={(e) => setProfessorNome(e.target.value)}>
                    <option value="">— usar o da turma ({text(selected?.professor) || "sem professor"}) —</option>
                    {professorNames.map((n) => <option key={n} value={n}>{n}</option>)}
                  </select>
                </div>
                <div className="form-group">
                  <label className="form-label">Data da aula</label>
                  <input className="form-input" type="date" value={dataAula} onChange={(e) => setDataAula(e.target.value)} />
                  <div className="form-help">Lançamento retroativo — somente ADM/Coordenador.</div>
                </div>
              </>
            )}
          </div>
        )}

        {/* ── ESTADO: AULA ABERTA ── */}
        {openClass && (
          <div className="form-grid">
            {/* Resumo da aula aberta */}
            <div className="form-group form-group-span2" style={{ background: "rgba(234,179,8,0.06)", borderRadius: "var(--radius-md)", padding: "12px 14px", border: "1px solid rgba(234,179,8,0.2)", display: "flex", gap: 24, flexWrap: "wrap" }}>
              <div style={{ display: "flex", flexDirection: "column", gap: 2 }}>
                <span style={{ fontSize: "0.68rem", textTransform: "uppercase", color: "var(--text-muted)", letterSpacing: "0.08em" }}>Professor</span>
                <span style={{ fontWeight: 700, fontSize: "0.9rem" }}>{text(openClass.professor)}</span>
              </div>
              <div style={{ display: "flex", flexDirection: "column", gap: 2 }}>
                <span style={{ fontSize: "0.68rem", textTransform: "uppercase", color: "var(--text-muted)", letterSpacing: "0.08em" }}>Tipo</span>
                <span style={{ fontWeight: 700, fontSize: "0.9rem" }}>{text(openClass.tipo_aula || "Aula Normal")}</span>
              </div>
              <div style={{ display: "flex", flexDirection: "column", gap: 2 }}>
                <span style={{ fontSize: "0.68rem", textTransform: "uppercase", color: "var(--text-muted)", letterSpacing: "0.08em" }}>Livro</span>
                <span style={{ fontWeight: 700, fontSize: "0.9rem" }}>{text(openClass.livro || "—")}</span>
              </div>
              <div style={{ display: "flex", flexDirection: "column", gap: 2 }}>
                <span style={{ fontSize: "0.68rem", textTransform: "uppercase", color: "var(--text-muted)", letterSpacing: "0.08em" }}>Lição início</span>
                <span style={{ fontWeight: 700, fontSize: "0.9rem" }}>{text(openClass.licao_inicio || "—")}</span>
              </div>
              <div style={{ display: "flex", flexDirection: "column", gap: 2 }}>
                <span style={{ fontSize: "0.68rem", textTransform: "uppercase", color: "var(--text-muted)", letterSpacing: "0.08em" }}>Aberta às</span>
                <span style={{ fontWeight: 700, fontSize: "0.9rem" }}>{formatOpenTime(text(openClass.inicio))}</span>
              </div>
            </div>

            {/* Lição que parou */}
            <div className="form-group form-group-span2">
              <label className="form-label">Lição em que parou *</label>
              <input
                className="form-input"
                placeholder="Ex: Unit 4 pág 36"
                value={licaoFim}
                onChange={(e) => setLicaoFim(e.target.value)}
                autoFocus
              />
            </div>

            {/* Presenças */}
            <div className="form-group form-group-span2">
              <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 8 }}>
                <label className="form-label" style={{ marginBottom: 0 }}>
                  Presenças ({alunosTurma.length} aluno{alunosTurma.length !== 1 ? "s" : ""})
                </label>
                {alunosTurma.length > 0 && (
                  <div style={{ display: "flex", gap: 6 }}>
                    <button type="button" className="btn btn-ghost btn-sm" onClick={() => marcarTodos(true)} style={{ fontSize: "0.75rem" }}>Todos presentes</button>
                    <button type="button" className="btn btn-ghost btn-sm" onClick={() => marcarTodos(false)} style={{ fontSize: "0.75rem" }}>Todos faltaram</button>
                  </div>
                )}
              </div>
              <div className="attendance-grid">
                {alunosTurma.length === 0 ? (
                  <span style={{ fontSize: "0.85rem", color: "var(--text-muted)" }}>
                    Nenhum aluno vinculado a esta turma.
                  </span>
                ) : (
                  alunosTurma.map((a) => {
                    const id = text(a.id || a.login || a.nome || a.name);
                    const marcado = presentes[id];
                    return (
                      <label key={id} className="attendance-item" style={{ background: marcado === true ? "rgba(5,150,105,0.08)" : marcado === false ? "rgba(239,68,68,0.06)" : undefined, borderRadius: "var(--radius-sm)", padding: "6px 10px" }}>
                        <input
                          type="checkbox"
                          checked={Boolean(marcado)}
                          onChange={(e) => setPresentes((p) => ({ ...p, [id]: e.target.checked }))}
                        />
                        <span style={{ fontWeight: marcado !== undefined ? 600 : 400 }}>
                          {text(a.nome || a.name || a.login)}
                        </span>
                        {marcado === false && <span style={{ fontSize: "0.72rem", color: "var(--red-500)", marginLeft: 4 }}>Falta</span>}
                      </label>
                    );
                  })
                )}
              </div>
              {!presencasOk && (
                <div className="form-help" style={{ color: "var(--gold-700)", marginTop: 6 }}>
                  Marque presença ou falta de todos os alunos para fechar a aula.
                </div>
              )}
            </div>

            {/* Observações */}
            <div className="form-group form-group-span2">
              <label className="form-label">Observações da aula <span style={{ fontWeight: 400, color: "var(--text-muted)" }}>(opcional)</span></label>
              <textarea
                className="form-input form-textarea"
                rows={2}
                placeholder="Anotações sobre alunos, conteúdo extra, ocorrências, etc."
                value={observacoes}
                onChange={(e) => setObservacoes(e.target.value)}
              />
            </div>
          </div>
        )}

        {message && (
          <div className={isError ? "form-error" : "form-success"} style={{ marginTop: 12 }}>
            {message}
          </div>
        )}

        <div className="teacher-class-actions" style={{ marginTop: 16 }}>
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
              disabled={saving || !licaoFim.trim() || !presencasOk}
              onClick={() => submit("close")}
              title={!licaoFim.trim() ? "Informe a lição em que parou" : !presencasOk ? "Marque presença ou falta de todos os alunos" : ""}
            >
              {saving ? "Fechando..." : "Fechar aula e lançar financeiro"}
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
