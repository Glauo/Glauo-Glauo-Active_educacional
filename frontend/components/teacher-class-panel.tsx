"use client";

import { useMemo, useState } from "react";
import { useRouter } from "next/navigation";

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

function canSeeAll(role: string) {
  const r = role.toLowerCase();
  return r.includes("admin") || r.includes("coord");
}

export function TeacherClassPanel({
  turmas,
  aulas,
  professores,
  userName,
  userRole
}: {
  turmas: Row[];
  aulas: Row[];
  professores: Row[];
  userName: string;
  userRole: string;
}) {
  const router = useRouter();
  const [turmaId, setTurmaId] = useState("");
  const [licaoInicio, setLicaoInicio] = useState("");
  const [licaoFim, setLicaoFim] = useState("");
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
  const valorAula = moneyValue(selected?.valor_aula || teacher.valor_aula || teacher.valor_hora || teacher.valor);

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
        observacoes,
        valor_aula: valorAula
      })
    });
    const payload = await response.json().catch(() => ({}));
    setSaving(false);
    if (!response.ok) {
      setMessage(payload.error || "Não foi possível salvar a aula.");
      return;
    }
    setMessage(action === "open" ? "Aula aberta com sucesso." : "Aula fechada e financeiro do professor lançado.");
    setLicaoInicio("");
    setLicaoFim("");
    setObservacoes("");
    router.refresh();
  }

  if (!visibleClasses.length) {
    return (
      <div className="card teacher-class-panel">
        <div className="empty-state">
          <div className="empty-title">Nenhuma turma disponível</div>
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
          <p className="section-subtitle">Ao fechar, a aula entra automaticamente no financeiro como pagamento ao professor.</p>
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
            <label className="form-label">Livro automático</label>
            <input className="form-input" value={livro || "Livro não informado"} readOnly />
          </div>
          <div className="form-group">
            <label className="form-label">Valor da aula</label>
            <input className="form-input" value={valorAula ? formatBRL(valorAula) : "Sem valor cadastrado"} readOnly />
          </div>
          <div className="form-group">
            <label className="form-label">Lição que inicia</label>
            <input
              className="form-input"
              placeholder={ultimaLicao || "Ex: Unidade 4 - página 32"}
              value={licaoInicio || (openClass ? text(openClass.licao_inicio) : "")}
              onChange={(e) => setLicaoInicio(e.target.value)}
              readOnly={Boolean(openClass)}
            />
          </div>
          <div className="form-group">
            <label className="form-label">Lição em que parou</label>
            <input
              className="form-input"
              placeholder="Ex: Unidade 4 - página 36"
              value={licaoFim}
              onChange={(e) => setLicaoFim(e.target.value)}
              disabled={!openClass}
            />
          </div>
          <div className="form-group form-group-span2">
            <label className="form-label">Observações da aula</label>
            <textarea
              className="form-input form-textarea"
              rows={3}
              placeholder="Presença, conteúdo, tarefa e observações rápidas."
              value={observacoes}
              onChange={(e) => setObservacoes(e.target.value)}
              disabled={!openClass}
            />
          </div>
        </div>

        {message && <div className={message.includes("sucesso") || message.includes("lançado") ? "form-success" : "form-error"}>{message}</div>}

        <div className="teacher-class-actions">
          {!openClass ? (
            <button className="btn btn-primary" disabled={saving} onClick={() => submit("open")}>
              {saving ? "Abrindo..." : "Abrir aula"}
            </button>
          ) : (
            <button className="btn btn-primary" disabled={saving || !licaoFim.trim()} onClick={() => submit("close")}>
              {saving ? "Fechando..." : "Fechar aula e lançar financeiro"}
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
