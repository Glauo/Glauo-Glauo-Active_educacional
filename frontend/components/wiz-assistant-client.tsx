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

function text(value: unknown) {
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
        <p className="chat-text">{msg.text}</p>
        <span className="chat-time">{msg.ts}</span>
      </div>
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
      text: `Olá! Sou o Wiz, assistente operacional do Ativo Educacional. Posso cadastrar alunos, criar tarefas, lançar cobranças, enviar mensagens, agendar aulas e muito mais. Como posso ajudar?`,
      ts: now(),
    },
  ]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  const todayLogs = logs.filter((log) => {
    const date = text(log.data || log.date);
    return date && new Date(date).toDateString() === new Date().toDateString();
  });
  const successLogs = logs.filter((log) => text(log.status).toLowerCase().includes("conclu"));

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  async function send() {
    const prompt = input.trim();
    if (!prompt || loading) return;

    const userMsg: Message = { id: crypto.randomUUID(), role: "user", text: prompt, ts: now() };
    setMessages((prev) => [...prev, userMsg]);
    setInput("");
    setLoading(true);

    try {
      const res = await fetch("/api/wiz", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ action: "answer", data: { prompt } }),
      });
      const json = await res.json().catch(() => ({}));
      const reply = text(json.message || json.error || (res.ok ? "Feito." : "Erro ao processar a solicitação."));
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
        <div className="card wiz-chat-card">
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

          <div className="wiz-input-bar">
            <textarea
              ref={inputRef}
              className="wiz-input"
              rows={1}
              placeholder="Digite o que precisa fazer... (Enter para enviar)"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={onKey}
              disabled={loading}
            />
            <button
              className="wiz-send-btn"
              onClick={send}
              disabled={loading || !input.trim()}
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
