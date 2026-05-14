"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";

type Row = Record<string, unknown>;

type Message = {
  id: string;
  role: "user" | "wiz";
  text: string;
  ts: string;
};

const QUICK_ACTIONS = [
  {
    label: "Registrar aula",
    icon: "📝",
    template: "Registrar aula da professora [Nome] na turma [Nome da Turma] hoje, lição [ex: Unit 5]",
  },
  {
    label: "Novo aluno",
    icon: "👤",
    template: "Cadastrar aluno [Nome Completo] na turma [Nome da Turma], livro [Livro 1], telefone [Telefone]",
  },
  {
    label: "Comunicado",
    icon: "📢",
    template: "Criar comunicado: [Título] — [Mensagem] para todos os alunos",
  },
  {
    label: "Tarefa",
    icon: "📋",
    template: "Criar tarefa de inglês para turma [Nome da Turma], conteúdo: [Conteúdo], 5 questões",
  },
  {
    label: "Biblioteca PDF",
    icon: "PDF",
    template: "Cadastrar material PDF na biblioteca: titulo [Nome do material], tipo material, turma Todas, link [URL do PDF]",
  },
];

function str(value: unknown) {
  return String(value || "").trim();
}

function now() {
  return new Date().toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" });
}

function WizIcon() {
  return (
    <div className="wiz-avatar">
      <svg viewBox="0 0 20 20" fill="currentColor">
        <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-8-3a1 1 0 00-.867.5 1 1 0 11-1.731-1A3 3 0 0113 8a3.001 3.001 0 01-2 2.83V11a1 1 0 11-2 0v-1a1 1 0 011-1 1 1 0 100-2zm0 8a1 1 0 100-2 1 1 0 000 2z" clipRule="evenodd" />
      </svg>
    </div>
  );
}

function ChatBubble({ msg }: { msg: Message }) {
  const isUser = msg.role === "user";
  return (
    <div className={`chat-row ${isUser ? "chat-row-user" : "chat-row-wiz"}`}>
      {!isUser && <WizIcon />}
      <div className={`chat-bubble ${isUser ? "chat-bubble-user" : "chat-bubble-wiz"}`}>
        <p className="chat-text" style={{ whiteSpace: "pre-wrap" }}>{msg.text}</p>
        <span className="chat-time">{msg.ts}</span>
      </div>
    </div>
  );
}

function RefPanel({ turmas, professores }: { turmas: Row[]; professores: Row[] }) {
  const [open, setOpen] = useState(false);
  return (
    <div style={{ borderTop: "1px solid var(--border)", padding: "8px 16px", background: "var(--bg-secondary)" }}>
      <button
        onClick={() => setOpen((v) => !v)}
        style={{ background: "none", border: "none", cursor: "pointer", color: "var(--text-muted)", fontSize: "0.78rem", display: "flex", alignItems: "center", gap: 4, padding: 0 }}
      >
        <svg viewBox="0 0 20 20" fill="currentColor" style={{ width: 14, height: 14 }}>
          <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clipRule="evenodd" />
        </svg>
        {open ? "Ocultar" : "Ver"} turmas e professores disponíveis
      </button>
      {open && (
        <div style={{ marginTop: 8, display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
          <div>
            <div style={{ fontSize: "0.72rem", fontWeight: 700, color: "var(--text-muted)", marginBottom: 4, textTransform: "uppercase", letterSpacing: "0.05em" }}>Turmas ({turmas.length})</div>
            <div style={{ display: "flex", flexWrap: "wrap", gap: 4 }}>
              {turmas.map((t, i) => (
                <span key={i} style={{ fontSize: "0.72rem", background: "var(--bg-hover)", borderRadius: 4, padding: "2px 6px", color: "var(--text-secondary)" }}>
                  {str(t.nome || t.name)}
                </span>
              ))}
            </div>
          </div>
          <div>
            <div style={{ fontSize: "0.72rem", fontWeight: 700, color: "var(--text-muted)", marginBottom: 4, textTransform: "uppercase", letterSpacing: "0.05em" }}>Professores ({professores.length})</div>
            <div style={{ display: "flex", flexWrap: "wrap", gap: 4 }}>
              {professores.map((p, i) => (
                <span key={i} style={{ fontSize: "0.72rem", background: "var(--bg-hover)", borderRadius: 4, padding: "2px 6px", color: "var(--text-secondary)" }}>
                  {str(p.nome || p.name)}
                </span>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

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
  const [messages, setMessages] = useState<Message[]>([
    {
      id: "welcome",
      role: "wiz",
      text: `Olá! Sou o Wiz, assistente operacional do Ativo Educacional.\n\nPosso registrar aulas de professores, cadastrar alunos, criar tarefas, lançar cobranças, enviar comunicados e muito mais.\n\nUse os atalhos abaixo ou descreva o que precisa fazer.`,
      ts: now(),
    },
  ]);
  const [input, setInput] = useState("");
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [loading, setLoading] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const todayLogs = logs.filter((log) => {
    const date = str(log.data || log.date);
    return date && new Date(date).toDateString() === new Date().toDateString();
  });
  const successLogs = logs.filter((log) => str(log.status).toLowerCase().includes("conclu"));

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  function applyQuickAction(template: string) {
    setInput(template);
    setTimeout(() => {
      const ta = inputRef.current;
      if (!ta) return;
      ta.focus();
      ta.setSelectionRange(ta.value.length, ta.value.length);
    }, 50);
  }

  function onFileChange(file: File | null) {
    if (!file) return;
    if (file.type && file.type !== "application/pdf") {
      setMessages((prev) => [...prev, { id: crypto.randomUUID(), role: "wiz", text: "Envie apenas arquivo PDF para a biblioteca.", ts: now() }]);
      return;
    }
    setSelectedFile(file);
    if (!input.trim()) {
      setInput(`Cadastrar material PDF na biblioteca: titulo ${file.name.replace(/\.pdf$/i, "")}, tipo material, turma Todas`);
    }
  }

  async function send() {
    const prompt = input.trim();
    const file = selectedFile;
    if ((!prompt && !file) || loading) return;

    const userMsg: Message = { id: crypto.randomUUID(), role: "user", text: file ? `${prompt || "Cadastrar material PDF na biblioteca"}\n[Anexo: ${file.name}]` : prompt, ts: now() };
    setMessages((prev) => [...prev, userMsg]);
    setInput("");
    setSelectedFile(null);
    if (fileInputRef.current) fileInputRef.current.value = "";
    setLoading(true);

    try {
      let res: Response;
      if (file) {
        const form = new FormData();
        form.append("action", "add_library_material");
        form.append("prompt", prompt);
        form.append("tipo", "material");
        form.append("arquivo_pdf", file);
        res = await fetch("/api/wiz", { method: "POST", body: form });
      } else {
        res = await fetch("/api/wiz", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ action: "answer", data: { prompt } }),
        });
      }
      const json = await res.json().catch(() => ({}));
      const reply = str(json.message || json.error || (res.ok ? "Feito." : "Erro ao processar a solicitação."));
      setMessages((prev) => [...prev, { id: crypto.randomUUID(), role: "wiz", text: reply, ts: now() }]);
      if (res.ok) router.refresh();
    } catch {
      setMessages((prev) => [...prev, { id: crypto.randomUUID(), role: "wiz", text: "Sem conexão. Tente novamente.", ts: now() }]);
    } finally {
      setLoading(false);
      inputRef.current?.focus();
    }
  }

  function onKey(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      send();
    }
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
          <div className="metric-note">no sistema</div>
        </div>
        <div className="metric-card metric-card-blue">
          <div className="metric-label">Turmas</div>
          <div className="metric-value">{turmas.length}</div>
          <div className="metric-note">{professores.length} professores</div>
        </div>
      </div>

      <div className="content-grid grid-2-1">
        {/* Chat */}
        <div className="card wiz-chat-card" style={{ display: "flex", flexDirection: "column" }}>
          <div className="card-header" style={{ borderBottom: "1px solid var(--border)", flexShrink: 0 }}>
            <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
              <WizIcon />
              <div>
                <h3 className="section-title" style={{ margin: 0 }}>Professor Wiz</h3>
                <p className="section-subtitle" style={{ margin: 0 }}>Assistente operacional — descreva o que precisa fazer</p>
              </div>
            </div>
            <span className="badge badge-success"><span className="badge-dot" />Online</span>
          </div>

          {/* Quick action chips */}
          <div style={{ display: "flex", gap: 8, padding: "10px 16px", flexWrap: "wrap", borderBottom: "1px solid var(--border)", background: "var(--bg-secondary)", flexShrink: 0 }}>
            {QUICK_ACTIONS.map((action) => (
              <button
                key={action.label}
                onClick={() => applyQuickAction(action.template)}
                disabled={loading}
                style={{
                  display: "flex", alignItems: "center", gap: 5,
                  background: "var(--bg-card)", border: "1px solid var(--border)",
                  borderRadius: 20, padding: "5px 12px", cursor: "pointer",
                  fontSize: "0.78rem", fontWeight: 600, color: "var(--text-primary)",
                  transition: "all 0.15s",
                }}
                onMouseEnter={(e) => { e.currentTarget.style.borderColor = "var(--primary)"; e.currentTarget.style.color = "var(--primary)"; }}
                onMouseLeave={(e) => { e.currentTarget.style.borderColor = "var(--border)"; e.currentTarget.style.color = "var(--text-primary)"; }}
              >
                <span>{action.icon}</span>
                {action.label}
              </button>
            ))}
          </div>

          <div className="wiz-chat-messages">
            {messages.map((msg) => (
              <ChatBubble key={msg.id} msg={msg} />
            ))}
            {loading && (
              <div className="chat-row chat-row-wiz">
                <WizIcon />
                <div className="chat-bubble chat-bubble-wiz">
                  <div className="wiz-typing">
                    <span /><span /><span />
                  </div>
                </div>
              </div>
            )}
            <div ref={bottomRef} />
          </div>

          <RefPanel turmas={turmas} professores={professores} />

          <div className="wiz-input-bar">
            <input
              ref={fileInputRef}
              type="file"
              accept="application/pdf,.pdf"
              style={{ display: "none" }}
              onChange={(e) => onFileChange(e.target.files?.[0] || null)}
              disabled={loading}
            />
            <button
              type="button"
              onClick={() => fileInputRef.current?.click()}
              disabled={loading}
              aria-label="Anexar PDF"
              title="Anexar PDF"
              style={{
                width: 42,
                height: 42,
                borderRadius: 14,
                border: "1px solid var(--border)",
                background: selectedFile ? "var(--primary-light)" : "var(--bg-card)",
                color: selectedFile ? "var(--primary)" : "var(--text-secondary)",
                display: "inline-flex",
                alignItems: "center",
                justifyContent: "center",
                cursor: loading ? "not-allowed" : "pointer",
                flexShrink: 0,
              }}
            >
              <svg viewBox="0 0 20 20" fill="currentColor" style={{ width: 18, height: 18 }}>
                <path fillRule="evenodd" d="M8 4a3 3 0 016 0v8a5 5 0 01-10 0V5a1 1 0 012 0v7a3 3 0 106 0V4a1 1 0 10-2 0v8a1 1 0 11-2 0V4z" clipRule="evenodd" />
              </svg>
            </button>
            <textarea
              ref={inputRef}
              className="wiz-input"
              rows={2}
              placeholder={`Ex: Registrar aula da professora Ana na turma Chicago hoje, lição Unit 5\nEnter para enviar · Shift+Enter nova linha`}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={onKey}
              disabled={loading}
            />
            <button
              className="wiz-send-btn"
              onClick={send}
              disabled={loading || (!input.trim() && !selectedFile)}
              aria-label="Enviar"
            >
              <svg viewBox="0 0 20 20" fill="currentColor">
                <path d="M10.894 2.553a1 1 0 00-1.788 0l-7 14a1 1 0 001.169 1.409l5-1.429A1 1 0 009 15.571V11a1 1 0 112 0v4.571a1 1 0 00.725.962l5 1.428a1 1 0 001.17-1.408l-7-14z" />
              </svg>
            </button>
          </div>
        </div>

        {/* Audit log */}
        <div className="card">
          <div className="card-header">
            <div>
              <div className="section-eyebrow">Histórico</div>
              <h3 className="section-title">Últimas execuções</h3>
              <p className="section-subtitle">Auditoria do Wiz</p>
            </div>
          </div>
          <div className="card-body" style={{ paddingTop: 12 }}>
            {logs.length === 0 ? (
              <div className="empty-state">
                <div className="empty-title">Sem execuções ainda</div>
                <p className="empty-desc">Quando o Wiz executar algo, o registro aparece aqui.</p>
              </div>
            ) : (
              <div className="spotlight-list">
                {logs.slice(-15).reverse().map((log, index) => (
                  <div className="spotlight-row" key={str(log.id) || index}>
                    <span className="spotlight-label">
                      {str(log.acao || log.action)}
                      <span style={{ display: "block", color: "var(--text-muted)", fontSize: "0.75rem", fontWeight: 500 }}>
                        {str(log.resultado).slice(0, 80)}
                      </span>
                    </span>
                    <span className={`badge badge-${str(log.status).includes("erro") ? "danger" : "success"}`}>
                      <span className="badge-dot" />{str(log.status || "ok")}
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
