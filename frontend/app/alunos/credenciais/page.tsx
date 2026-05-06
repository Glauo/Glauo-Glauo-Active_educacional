"use client";

import { useEffect, useState } from "react";
import { AppShell } from "@/components/app-shell";

type AlunoCredencial = {
  id: string;
  nome: string;
  turma: string;
  login: string | null;
  telefone?: string;
  temAcesso: boolean;
};

type EditState = {
  id: string;
  login: string;
  senha: string;
  confirmar: string;
};

type SaveResponse = {
  error?: string;
  login?: string;
  whatsapp_url?: string;
  whatsapp_message?: string;
};

export default function CredenciaisPage() {
  const [alunos, setAlunos] = useState<AlunoCredencial[]>([]);
  const [loading, setLoading] = useState(true);
  const [editando, setEditando] = useState<EditState | null>(null);
  const [salvando, setSalvando] = useState(false);
  const [feedback, setFeedback] = useState<{ tipo: "ok" | "erro"; msg: string } | null>(null);
  const [whatsappLink, setWhatsappLink] = useState("");
  const [busca, setBusca] = useState("");

  useEffect(() => {
    fetch("/api/alunos/credenciais")
      .then((r) => r.json())
      .then((data) => {
        setAlunos(Array.isArray(data) ? data : []);
        setLoading(false);
      })
      .catch(() => setLoading(false));
  }, []);

  const alunosFiltrados = alunos.filter((a) =>
    !busca ||
    (a.nome || "").toLowerCase().includes(busca.toLowerCase()) ||
    (a.turma || "").toLowerCase().includes(busca.toLowerCase()) ||
    (a.login || "").toLowerCase().includes(busca.toLowerCase())
  );

  function abrirEditor(a: AlunoCredencial) {
    setFeedback(null);
    setWhatsappLink("");
    setEditando({ id: a.id, login: a.login || "", senha: "", confirmar: "" });
  }

  function cancelar() {
    setEditando(null);
    setFeedback(null);
    setWhatsappLink("");
  }

  async function salvar() {
    if (!editando) return;

    if (!editando.login.trim()) {
      setFeedback({ tipo: "erro", msg: "O login não pode ser vazio." });
      return;
    }
    if (editando.login.trim().length < 3) {
      setFeedback({ tipo: "erro", msg: "Login deve ter pelo menos 3 caracteres." });
      return;
    }
    if (!editando.senha) {
      setFeedback({ tipo: "erro", msg: "A senha não pode ser vazia." });
      return;
    }
    if (editando.senha.length < 4) {
      setFeedback({ tipo: "erro", msg: "Senha deve ter pelo menos 4 caracteres." });
      return;
    }
    if (editando.senha !== editando.confirmar) {
      setFeedback({ tipo: "erro", msg: "A senha e a confirmação não coincidem." });
      return;
    }

    setSalvando(true);
    setFeedback(null);
    setWhatsappLink("");

    const res = await fetch("/api/alunos/credenciais", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ id: editando.id, login: editando.login, senha: editando.senha })
    });

    const data = await res.json() as SaveResponse;
    setSalvando(false);

    if (!res.ok) {
      setFeedback({ tipo: "erro", msg: data.error || "Erro ao salvar." });
      return;
    }

    const savedLogin = data.login || editando.login.trim().toLowerCase();
    setFeedback({ tipo: "ok", msg: `Acesso configurado com sucesso para login: ${savedLogin}` });
    setWhatsappLink(data.whatsapp_url || "");
    setAlunos((prev) =>
      prev.map((a) =>
        a.id === editando.id ? { ...a, login: savedLogin, temAcesso: true } : a
      )
    );
  }

  async function removerAcesso(a: AlunoCredencial) {
    if (!confirm(`Remover o acesso de "${a.nome}"? O aluno não conseguirá mais fazer login.`)) return;

    const res = await fetch(`/api/alunos/credenciais?id=${a.id}`, { method: "DELETE" });
    if (res.ok) {
      setAlunos((prev) =>
        prev.map((al) => al.id === a.id ? { ...al, login: null, temAcesso: false } : al)
      );
      setFeedback({ tipo: "ok", msg: `Acesso de "${a.nome}" removido.` });
    } else {
      setFeedback({ tipo: "erro", msg: "Erro ao remover acesso." });
    }
  }

  const comAcesso = alunos.filter((a) => a.temAcesso).length;
  const semAcesso = alunos.length - comAcesso;

  return (
    <AppShell breadcrumb="Credenciais de Alunos">
      <div className="page-header">
        <div className="page-title-block">
          <div className="page-eyebrow"><span className="page-eyebrow-dot" />Módulo Acadêmico</div>
          <h1 className="page-title">Gerenciar Acessos</h1>
          <p className="page-description">Configure login e senha para que os alunos acessem a área do aluno.</p>
        </div>
        <div className="page-actions">
          <a href="/aluno/login" target="_blank" className="btn btn-secondary">
            <svg viewBox="0 0 20 20" fill="currentColor"><path d="M11 3a1 1 0 100 2h2.586l-6.293 6.293a1 1 0 101.414 1.414L15 6.414V9a1 1 0 102 0V4a1 1 0 00-1-1h-5z" /><path d="M5 5a2 2 0 00-2 2v8a2 2 0 002 2h8a2 2 0 002-2v-3a1 1 0 10-2 0v3H5V7h3a1 1 0 000-2H5z" /></svg>
            Ver área do aluno
          </a>
        </div>
      </div>

      <div className="metric-grid metric-grid-3" style={{ marginBottom: "24px" }}>
        <div className="metric-card metric-card-blue">
          <div className="metric-label">Total de alunos</div>
          <div className="metric-value">{alunos.length}</div>
          <div className="metric-note">Cadastrados no sistema</div>
        </div>
        <div className="metric-card metric-card-green">
          <div className="metric-label">Com acesso configurado</div>
          <div className="metric-value">{comAcesso}</div>
          <div className="metric-note">Conseguem fazer login</div>
        </div>
        <div className="metric-card metric-card-red">
          <div className="metric-label">Sem acesso</div>
          <div className="metric-value">{semAcesso}</div>
          <div className="metric-note">Aguardando configuração</div>
        </div>
      </div>

      {feedback && (
        <div style={{
          background: feedback.tipo === "ok" ? "rgba(34,197,94,0.08)" : "rgba(239,68,68,0.08)",
          border: `1px solid ${feedback.tipo === "ok" ? "rgba(34,197,94,0.25)" : "rgba(239,68,68,0.25)"}`,
          borderRadius: "var(--radius-md)",
          padding: "14px 18px",
          marginBottom: "20px",
          color: feedback.tipo === "ok" ? "var(--green-700)" : "var(--red-700)",
          fontSize: "0.875rem",
          display: "flex",
          alignItems: "center",
          gap: "10px"
        }}>
          {feedback.tipo === "ok"
            ? <svg width="16" height="16" viewBox="0 0 20 20" fill="currentColor"><path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" /></svg>
            : <svg width="16" height="16" viewBox="0 0 20 20" fill="currentColor"><path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z" clipRule="evenodd" /></svg>
          }
          {feedback.msg}
        </div>
      )}

      <div className="card">
        <div className="card-header">
          <div>
            <div className="section-eyebrow">Controle de Acesso</div>
            <h3 className="section-title">Todos os alunos</h3>
            <p className="section-subtitle">{alunosFiltrados.length} alunos</p>
          </div>
          <div className="search-bar">
            <span className="search-icon">
              <svg viewBox="0 0 20 20" fill="currentColor"><path fillRule="evenodd" d="M8 4a4 4 0 100 8 4 4 0 000-8zM2 8a6 6 0 1110.89 3.476l4.817 4.817a1 1 0 01-1.414 1.414l-4.816-4.816A6 6 0 012 8z" clipRule="evenodd" /></svg>
            </span>
            <input
              className="search-input"
              placeholder="Buscar por nome, turma ou login..."
              value={busca}
              onChange={(e) => setBusca(e.target.value)}
            />
          </div>
        </div>
        <div className="card-body" style={{ paddingTop: "12px" }}>
          {loading ? (
            <div className="empty-state">
              <div className="empty-title">Carregando alunos…</div>
            </div>
          ) : alunosFiltrados.length === 0 ? (
            <div className="empty-state">
              <div className="empty-title">Nenhum aluno encontrado</div>
              <p className="empty-desc">Verifique a busca ou o banco de dados.</p>
            </div>
          ) : (
            <table className="data-table">
              <thead>
                <tr>
                  <th>Aluno</th>
                  <th>Turma</th>
                  <th>Login configurado</th>
                  <th>Acesso</th>
                  <th>Ações</th>
                </tr>
              </thead>
              <tbody>
                {alunosFiltrados.map((a) => (
                  <tr key={a.id}>
                    <td style={{ fontWeight: 600 }}>{a.nome || "—"}</td>
                    <td>{a.turma || "—"}</td>
                    <td style={{ fontFamily: "monospace", fontSize: "0.875rem" }}>
                      {a.login || <span style={{ color: "var(--text-faint)" }}>não configurado</span>}
                    </td>
                    <td>
                      <span className={`badge badge-${a.temAcesso ? "success" : "neutral"}`}>
                        <span className="badge-dot" />
                        {a.temAcesso ? "Ativo" : "Sem acesso"}
                      </span>
                    </td>
                    <td>
                      <div style={{ display: "flex", gap: "6px" }}>
                        <button
                          className="btn btn-primary btn-sm"
                          onClick={() => abrirEditor(a)}
                        >
                          {a.temAcesso ? "Alterar" : "Configurar"}
                        </button>
                        {a.temAcesso && (
                          <button
                            className="btn btn-danger btn-sm"
                            onClick={() => removerAcesso(a)}
                          >
                            Remover
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>

      {/* Modal de edição */}
      {editando && (
        <div style={{
          position: "fixed", inset: 0,
          background: "rgba(0,0,0,0.45)",
          display: "flex", alignItems: "center", justifyContent: "center",
          zIndex: 1000,
          backdropFilter: "blur(4px)"
        }}>
          <div style={{
            background: "var(--surface-raised)",
            borderRadius: "var(--radius-xl)",
            padding: "32px",
            width: "100%",
            maxWidth: "440px",
            boxShadow: "var(--shadow-xl)"
          }}>
            <div style={{ marginBottom: "24px" }}>
              <h3 style={{ fontSize: "1.125rem", fontWeight: 700, color: "var(--text-primary)", marginBottom: "4px" }}>
                {alunos.find(a => a.id === editando.id)?.temAcesso ? "Alterar credenciais" : "Configurar acesso"}
              </h3>
              <p style={{ fontSize: "0.875rem", color: "var(--text-muted)" }}>
                Aluno: <strong>{alunos.find(a => a.id === editando.id)?.nome}</strong>
              </p>
            </div>

            <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
              <div className="form-group">
                <label className="form-label">Login do aluno</label>
                <input
                  className="form-input"
                  type="text"
                  placeholder="Ex: joao.silva"
                  value={editando.login}
                  onChange={(e) => setEditando(prev => prev ? { ...prev, login: e.target.value } : null)}
                  autoComplete="off"
                />
                <span style={{ fontSize: "0.75rem", color: "var(--text-faint)" }}>Somente letras minúsculas, números e ponto.</span>
              </div>

              <div className="form-group">
                <label className="form-label">Nova senha</label>
                <input
                  className="form-input"
                  type="password"
                  placeholder="Mínimo 4 caracteres"
                  value={editando.senha}
                  onChange={(e) => setEditando(prev => prev ? { ...prev, senha: e.target.value } : null)}
                  autoComplete="new-password"
                />
              </div>

              <div className="form-group">
                <label className="form-label">Confirmar senha</label>
                <input
                  className="form-input"
                  type="password"
                  placeholder="Repita a senha"
                  value={editando.confirmar}
                  onChange={(e) => setEditando(prev => prev ? { ...prev, confirmar: e.target.value } : null)}
                  autoComplete="new-password"
                />
              </div>

              {feedback?.tipo === "erro" && (
                <div style={{
                  background: "rgba(239,68,68,0.08)",
                  border: "1px solid rgba(239,68,68,0.25)",
                  borderRadius: "var(--radius-md)",
                  padding: "12px 14px",
                  color: "var(--red-700)",
                  fontSize: "0.875rem"
                }}>
                  {feedback.msg}
                </div>
              )}

              {feedback?.tipo === "ok" && (
                <div style={{
                  background: "rgba(34,197,94,0.08)",
                  border: "1px solid rgba(34,197,94,0.25)",
                  borderRadius: "var(--radius-md)",
                  padding: "12px 14px",
                  color: "var(--green-700)",
                  fontSize: "0.875rem"
                }}>
                  {feedback.msg}
                </div>
              )}

              <div style={{ display: "flex", gap: "10px", marginTop: "8px" }}>
                <button
                  className="btn btn-secondary"
                  style={{ flex: 1 }}
                  onClick={cancelar}
                  disabled={salvando}
                >
                  Cancelar
                </button>
                <button
                  className="btn btn-primary"
                  style={{ flex: 1 }}
                  onClick={salvar}
                  disabled={salvando}
                >
                  {salvando ? "Salvando…" : "Salvar acesso"}
                </button>
              </div>
              {whatsappLink && (
                <a className="btn btn-secondary" href={whatsappLink} target="_blank" rel="noreferrer" style={{ justifyContent: "center" }}>
                  Enviar login e senha por WhatsApp
                </a>
              )}
            </div>
          </div>
        </div>
      )}
    </AppShell>
  );
}
