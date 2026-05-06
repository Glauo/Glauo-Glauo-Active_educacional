"use client";

import { useMemo, useState } from "react";
import { useRouter } from "next/navigation";

type Row = Record<string, unknown>;

type FormState = {
  titulo: string;
  mensagem: string;
  turma: string;
  disciplina: string;
  prazo: string;
  foco: string;
  nome: string;
  telefone: string;
  email: string;
  valor: string;
  parcelas: string;
  vencimento: string;
  categoria: string;
};

const initialForm: FormState = {
  titulo: "",
  mensagem: "",
  turma: "Todas",
  disciplina: "Ingles",
  prazo: "",
  foco: "",
  nome: "",
  telefone: "",
  email: "",
  valor: "",
  parcelas: "1",
  vencimento: "",
  categoria: "Mensalidade",
};

function text(value: unknown) {
  return String(value || "").trim();
}

const actions = [
  { id: "create_wall_post", label: "Comunicado", desc: "Cria aviso no mural e prepara envio." },
  { id: "create_homework", label: "Tarefa", desc: "Gera lição de casa revisável." },
  { id: "create_work", label: "Trabalho", desc: "Cria trabalho/desafio avaliativo." },
  { id: "create_student", label: "Cadastro", desc: "Cadastra aluno rápido." },
  { id: "create_financial", label: "Recebimento", desc: "Lança parcelas e boleto." },
  { id: "create_agenda", label: "Agenda", desc: "Agenda evento/aula." },
  { id: "prepare_message", label: "Envio", desc: "Prepara mensagem para WhatsApp/e-mail." },
];

export function WizAssistantClient({
  logs,
  alunos,
  turmas,
  professores,
}: {
  logs: Row[];
  alunos: Row[];
  turmas: Row[];
  professores: Row[];
}) {
  const router = useRouter();
  const [active, setActive] = useState("create_wall_post");
  const [prompt, setPrompt] = useState("");
  const [form, setForm] = useState<FormState>(initialForm);
  const [loading, setLoading] = useState(false);
  const [reply, setReply] = useState("");
  const [error, setError] = useState("");

  const todayLogs = useMemo(() => {
    const today = new Date().toDateString();
    return logs.filter((log) => {
      const date = text(log.data || log.date);
      return date && new Date(date).toDateString() === today;
    });
  }, [logs]);

  const successLogs = logs.filter((log) => text(log.status).toLowerCase().includes("conclu"));
  const activeAction = actions.find((item) => item.id === active) || actions[0];

  function update<K extends keyof FormState>(field: K, value: FormState[K]) {
    setForm((prev) => ({ ...prev, [field]: value }));
    setError("");
  }

  async function run(action: string, data: Row) {
    setLoading(true);
    setError("");
    setReply("");
    const res = await fetch("/api/wiz", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ action, data }),
    });
    const json = await res.json().catch(() => ({}));
    setLoading(false);
    if (!res.ok) {
      setError(text(json.error || json.message || "Erro ao executar Wiz."));
      return;
    }
    setReply(text(json.message || "Tarefa concluida."));
    router.refresh();
  }

  function actionPayload(): Row {
    if (active === "create_wall_post") {
      return { titulo: form.titulo, mensagem: form.mensagem, turma: form.turma, enviar_whatsapp: true, enviar_email: true };
    }
    if (active === "create_homework") {
      return { titulo: form.titulo, disciplina: form.disciplina, turma: form.turma, prazo: form.prazo, foco: form.foco || form.mensagem, quantidade_questoes: 5 };
    }
    if (active === "create_work") {
      return { titulo: form.titulo, disciplina: form.disciplina, turma: form.turma, prazo: form.prazo, descricao: form.mensagem, pontos: 10 };
    }
    if (active === "create_student") {
      return { nome: form.nome, turma: form.turma, telefone: form.telefone, email: form.email, valor_mensalidade: form.valor };
    }
    if (active === "create_financial") {
      return { aluno: form.nome, telefone: form.telefone, email: form.email, valor_total: form.valor, parcelas: form.parcelas, vencimento: form.vencimento, categoria: form.categoria, gerar_boleto: true };
    }
    if (active === "create_agenda") {
      return { titulo: form.titulo, descricao: form.mensagem, turma: form.turma, data: form.prazo, professor: form.nome };
    }
    return { destinatario: form.nome || form.turma, assunto: form.titulo, mensagem: form.mensagem, canal: "WhatsApp e e-mail" };
  }

  async function runPrompt() {
    if (!prompt.trim()) return;
    await run("answer", { prompt });
  }

  async function runActive() {
    await run(active, actionPayload());
  }

  return (
    <>
      <div className="metric-grid metric-grid-4">
        <div className="metric-card metric-card-blue">
          <div className="metric-label">Ações do Wiz</div>
          <div className="metric-value">{logs.length}</div>
          <div className="metric-note">{todayLogs.length} hoje</div>
        </div>
        <div className="metric-card metric-card-green">
          <div className="metric-label">Concluídas</div>
          <div className="metric-value">{successLogs.length}</div>
          <div className="metric-note">Execução registrada</div>
        </div>
        <div className="metric-card metric-card-gold">
          <div className="metric-label">Alunos</div>
          <div className="metric-value">{alunos.length}</div>
          <div className="metric-note">Contexto do sistema</div>
        </div>
        <div className="metric-card metric-card-blue">
          <div className="metric-label">Turmas</div>
          <div className="metric-value">{turmas.length}</div>
          <div className="metric-note">{professores.length} professores</div>
        </div>
      </div>

      <div className="card card-raised">
        <div className="card-header">
          <div>
            <div className="section-eyebrow">Comando direto</div>
            <h3 className="section-title">Assistente operacional Wiz</h3>
            <p className="section-subtitle">Use comandos objetivos. O Wiz só responde sobre ações do sistema.</p>
          </div>
        </div>
        <div className="card-body">
          <div className="form-grid">
            <div className="form-group form-group-span2">
              <label className="form-label">O que precisa fazer?</label>
              <textarea
                className="form-input form-textarea"
                rows={3}
                value={prompt}
                onChange={(e) => setPrompt(e.target.value)}
                placeholder="Ex: criar tarefa para turma Chicago sobre simple present com prazo sexta"
              />
            </div>
          </div>
          <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginTop: 12 }}>
            <button className="btn btn-primary" onClick={runPrompt} disabled={loading || !prompt.trim()}>{loading ? "Executando..." : "Analisar comando"}</button>
            <button className="btn btn-secondary" onClick={() => setPrompt("")}>Limpar</button>
          </div>
          {(reply || error) && (
            <div className={`alert ${error ? "alert-danger" : "alert-success"}`} style={{ marginTop: 12 }}>
              {error || reply}
            </div>
          )}
        </div>
      </div>

      <div className="content-grid grid-2-1">
        <div className="card">
          <div className="card-header">
            <div>
              <div className="section-eyebrow">Execução</div>
              <h3 className="section-title">{activeAction.label}</h3>
              <p className="section-subtitle">{activeAction.desc}</p>
            </div>
          </div>
          <div className="card-body">
            <div className="tab-bar" style={{ marginBottom: 16 }}>
              {actions.map((item) => (
                <button key={item.id} className={`tab-btn${active === item.id ? " active" : ""}`} onClick={() => setActive(item.id)}>
                  {item.label}
                </button>
              ))}
            </div>

            <div className="form-grid">
              {["create_wall_post", "create_homework", "create_work", "create_agenda", "prepare_message"].includes(active) && (
                <div className="form-group form-group-span2">
                  <label className="form-label">Título / assunto</label>
                  <input className="form-input" value={form.titulo} onChange={(e) => update("titulo", e.target.value)} />
                </div>
              )}
              {["create_wall_post", "create_homework", "create_work", "create_agenda", "prepare_message"].includes(active) && (
                <div className="form-group form-group-span2">
                  <label className="form-label">Mensagem / instruções / contexto</label>
                  <textarea className="form-input form-textarea" rows={3} value={form.mensagem} onChange={(e) => update("mensagem", e.target.value)} />
                </div>
              )}
              {["create_wall_post", "create_homework", "create_work", "create_student", "create_agenda", "prepare_message"].includes(active) && (
                <div className="form-group">
                  <label className="form-label">Turma</label>
                  <select className="form-input" value={form.turma} onChange={(e) => update("turma", e.target.value)}>
                    <option>Todas</option>
                    {turmas.map((turma, index) => <option key={text(turma.id) || index}>{text(turma.nome || turma.name || turma.turma)}</option>)}
                  </select>
                </div>
              )}
              {["create_homework", "create_work"].includes(active) && (
                <div className="form-group">
                  <label className="form-label">Disciplina</label>
                  <input className="form-input" value={form.disciplina} onChange={(e) => update("disciplina", e.target.value)} />
                </div>
              )}
              {["create_homework", "create_work"].includes(active) && (
                <div className="form-group form-group-span2">
                  <label className="form-label">Foco do conteúdo</label>
                  <input className="form-input" value={form.foco} onChange={(e) => update("foco", e.target.value)} placeholder="Ex: Simple present, vocabulary unit 3, speaking practice" />
                </div>
              )}
              {["create_homework", "create_work", "create_agenda"].includes(active) && (
                <div className="form-group">
                  <label className="form-label">Prazo / data</label>
                  <input className="form-input" type="date" value={form.prazo} onChange={(e) => update("prazo", e.target.value)} />
                </div>
              )}
              {["create_student", "create_financial", "create_agenda", "prepare_message"].includes(active) && (
                <div className="form-group">
                  <label className="form-label">{active === "create_agenda" ? "Professor" : "Aluno / destinatário"}</label>
                  <input className="form-input" value={form.nome} onChange={(e) => update("nome", e.target.value)} />
                </div>
              )}
              {["create_student", "create_financial"].includes(active) && (
                <>
                  <div className="form-group">
                    <label className="form-label">WhatsApp</label>
                    <input className="form-input" value={form.telefone} onChange={(e) => update("telefone", e.target.value)} />
                  </div>
                  <div className="form-group">
                    <label className="form-label">E-mail</label>
                    <input className="form-input" type="email" value={form.email} onChange={(e) => update("email", e.target.value)} />
                  </div>
                </>
              )}
              {["create_student", "create_financial"].includes(active) && (
                <div className="form-group">
                  <label className="form-label">Valor</label>
                  <input className="form-input" inputMode="decimal" value={form.valor} onChange={(e) => update("valor", e.target.value)} />
                </div>
              )}
              {active === "create_financial" && (
                <>
                  <div className="form-group">
                    <label className="form-label">Parcelas</label>
                    <input className="form-input" type="number" min={1} max={48} value={form.parcelas} onChange={(e) => update("parcelas", e.target.value)} />
                  </div>
                  <div className="form-group">
                    <label className="form-label">Vencimento</label>
                    <input className="form-input" type="date" value={form.vencimento} onChange={(e) => update("vencimento", e.target.value)} />
                  </div>
                  <div className="form-group">
                    <label className="form-label">Categoria</label>
                    <select className="form-input" value={form.categoria} onChange={(e) => update("categoria", e.target.value)}>
                      <option>Matricula</option>
                      <option>Mensalidade</option>
                      <option>Material</option>
                      <option>Renegociacao</option>
                    </select>
                  </div>
                </>
              )}
            </div>

            <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginTop: 16 }}>
              <button className="btn btn-primary" onClick={runActive} disabled={loading}>{loading ? "Executando..." : `Executar ${activeAction.label}`}</button>
              <button className="btn btn-secondary" onClick={() => setForm(initialForm)}>Limpar formulário</button>
            </div>
          </div>
        </div>

        <div className="card">
          <div className="card-header">
            <div>
              <div className="section-eyebrow">Histórico</div>
              <h3 className="section-title">Últimas execuções</h3>
              <p className="section-subtitle">Auditoria do Assistente Wiz</p>
            </div>
          </div>
          <div className="card-body" style={{ paddingTop: 12 }}>
            {logs.length === 0 ? (
              <div className="empty-state">
                <div className="empty-title">Sem execuções ainda</div>
                <p className="empty-desc">Quando o Wiz fizer algo, o registro aparece aqui.</p>
              </div>
            ) : (
              <div className="spotlight-list">
                {logs.slice(-12).reverse().map((log, index) => (
                  <div className="spotlight-row" key={text(log.id) || index}>
                    <span className="spotlight-label">
                      {text(log.acao || log.action)}
                      <span style={{ display: "block", color: "var(--text-muted)", fontSize: "0.75rem", fontWeight: 500 }}>
                        {text(log.resultado).slice(0, 80)}
                      </span>
                    </span>
                    <span className={`badge badge-${text(log.status).includes("erro") ? "danger" : "success"}`}>
                      <span className="badge-dot" />{text(log.status || "ok")}
                    </span>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </>
  );
}
