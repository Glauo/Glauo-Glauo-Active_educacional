"use client";

import { useState, FormEvent } from "react";
import { useRouter } from "next/navigation";
import Image from "next/image";

export default function LoginPage() {
  const router = useRouter();
  const [usuario, setUsuario] = useState("");
  const [senha, setSenha] = useState("");
  const [unidade, setUnidade] = useState("Matriz");
  const [outra, setOutra] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const UNIDADES = ["Matriz", "Unidade Centro", "Unidade Norte", "Unidade Sul", "Outra"];

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError("");
    setLoading(true);

    const unit = unidade === "Outra" ? outra.trim() || "Outra" : unidade;

    try {
      const res = await fetch("/api/auth", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ usuario, senha, unit })
      });

      const data = await res.json();

      if (!res.ok) {
        setError(data.error || "Erro ao entrar.");
        return;
      }

      router.push("/");
      router.refresh();
    } catch {
      setError("Erro de conexão. Tente novamente.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="login-shell">
      {/* Painel de marca */}
      <div className="login-brand">
        <div>
          <div className="login-brand-logo">
            <div className="login-brand-icon" style={{ background: "white", borderRadius: "14px", padding: "4px", display: "flex", alignItems: "center", justifyContent: "center" }}>
              <Image src="/logo.png" alt="Ativo Educacional" width={52} height={52} style={{ objectFit: "contain" }} />
            </div>
            <div>
              <div className="login-brand-name">Ativo Educacional</div>
              <div className="login-brand-tagline">Sistema de Gestão</div>
            </div>
          </div>

          <h2 className="login-headline">
            Ativo Educacional
          </h2>

          <p style={{ color: "rgba(255,255,255,0.55)", fontSize: "1rem", marginTop: "20px", lineHeight: "1.6", maxWidth: "420px" }}>
            Gestão completa da sua escola — com inteligência artificial, automações e uma experiência simples, moderna e inovadora.
          </p>
        </div>

        <div>
          <div className="login-stats">
            <div className="login-stat">
              <div className="login-stat-value">312</div>
              <div className="login-stat-label">Alunos ativos no sistema</div>
            </div>
            <div className="login-stat">
              <div className="login-stat-value">24</div>
              <div className="login-stat-label">Turmas em operação</div>
            </div>
            <div className="login-stat">
              <div className="login-stat-value">18</div>
              <div className="login-stat-label">Professores cadastrados</div>
            </div>
          </div>
        </div>
      </div>

      {/* Formulário */}
      <div className="login-form-area">
        <div className="login-box">
          <h1 className="login-title">Bem-vindo de volta</h1>
          <p className="login-subtitle">
            Entre com suas credenciais para acessar o sistema.
          </p>

          <form className="login-form" onSubmit={handleSubmit}>
            {error && <div className="login-error">{error}</div>}

            <div className="form-group">
              <label className="form-label" htmlFor="unidade">Filial / Unidade</label>
              <select
                id="unidade"
                className="form-select"
                value={unidade}
                onChange={(e) => setUnidade(e.target.value)}
              >
                {UNIDADES.map((u) => (
                  <option key={u} value={u}>{u}</option>
                ))}
              </select>
            </div>

            {unidade === "Outra" && (
              <div className="form-group">
                <label className="form-label" htmlFor="outra">Nome da unidade</label>
                <input
                  id="outra"
                  type="text"
                  className="form-input"
                  placeholder="Digite o nome da unidade"
                  value={outra}
                  onChange={(e) => setOutra(e.target.value)}
                />
              </div>
            )}

            <div className="form-group">
              <label className="form-label" htmlFor="usuario">Usuário</label>
              <input
                id="usuario"
                type="text"
                className="form-input"
                placeholder="Seu usuário de acesso"
                value={usuario}
                onChange={(e) => setUsuario(e.target.value)}
                required
                autoComplete="username"
                autoFocus
              />
            </div>

            <div className="form-group">
              <label className="form-label" htmlFor="senha">Senha</label>
              <input
                id="senha"
                type="password"
                className="form-input"
                placeholder="Sua senha"
                value={senha}
                onChange={(e) => setSenha(e.target.value)}
                required
                autoComplete="current-password"
              />
            </div>

            <button
              type="submit"
              className="btn btn-primary btn-lg"
              style={{ marginTop: "8px", width: "100%" }}
              disabled={loading}
            >
              {loading ? "Entrando..." : "Entrar no sistema"}
            </button>
          </form>

          <p style={{ marginTop: "32px", fontSize: "0.8125rem", color: "var(--text-muted)", textAlign: "center" }}>
            Ativo Educacional © 2026 — Sistema de Gestão Premium
          </p>
        </div>
      </div>
    </div>
  );
}
