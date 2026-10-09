"use client";
import { useState, type FormEvent } from "react";

export default function AlterarSenha() {
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    if (form.get("nova_senha") !== form.get("confirmacao")) { setError("As senhas nao coincidem."); return; }
    setBusy(true); setError("");
    try {
      const res = await fetch("/api/auth/alterar-senha", { method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify(Object.fromEntries(form)), signal: AbortSignal.timeout(20000) });
      const data = await res.json();
      if (!res.ok) { setError(data.error || "Nao foi possivel salvar."); return; }
      window.location.assign(data.redirectTo || "/");
    } catch { setError("Falha de conexao. Verifique sua conexao e entre novamente."); }
    finally { setBusy(false); }
  }
  return <main className="password-change-page"><section className="card password-change-card">
    <h1>Defina sua senha pessoal</h1>
    <p>Para proteger seu acesso, substitua a senha temporaria. Use pelo menos 8 caracteres, com maiuscula, minuscula e numero.</p>
    <form onSubmit={submit}>
      <label className="form-group">Senha atual<input className="form-input" name="senha_atual" type="password" autoComplete="current-password" required /></label>
      <label className="form-group">Nova senha<input className="form-input" name="nova_senha" type="password" autoComplete="new-password" minLength={8} maxLength={128} required /></label>
      <label className="form-group">Confirmar nova senha<input className="form-input" name="confirmacao" type="password" autoComplete="new-password" required /></label>
      {error && <p className="form-error" role="alert">{error}</p>}
      <button className="btn btn-primary" disabled={busy}>{busy ? "Salvando..." : "Salvar nova senha"}</button>
      <a className="btn btn-secondary" href="/login">Voltar ao login</a>
    </form>
  </section></main>;
}
