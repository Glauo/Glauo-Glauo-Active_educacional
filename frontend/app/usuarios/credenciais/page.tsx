"use client";

import { useEffect, useState } from "react";
import { AppShell } from "@/components/app-shell";

type Usuario = { id: string; nome: string; usuario: string; perfil: string; temAcesso: boolean };

export default function CredenciaisUsuariosPage() {
  const [usuarios, setUsuarios] = useState<Usuario[]>([]);
  const [edit, setEdit] = useState<Usuario | null>(null);
  const [senha, setSenha] = useState("");
  const [feedback, setFeedback] = useState("");

  useEffect(() => {
    fetch("/api/usuarios/credenciais").then((r) => r.json()).then((d) => setUsuarios(Array.isArray(d) ? d : []));
  }, []);

  async function salvar() {
    if (!edit) return;
    const res = await fetch("/api/usuarios/credenciais", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ ...edit, senha })
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      setFeedback(data.error || "Erro ao salvar acesso.");
      return;
    }
    setUsuarios((prev) => prev.map((u) => u.id === edit.id ? { ...u, usuario: data.usuario, temAcesso: true } : u));
    setEdit(null);
    setSenha("");
    setFeedback("Acesso atualizado com sucesso.");
  }

  return (
    <AppShell breadcrumb="Acessos">
      <div className="page-header">
        <div className="page-title-block">
          <div className="page-eyebrow"><span className="page-eyebrow-dot" />Seguranca</div>
          <h1 className="page-title">Credenciais de Usuarios</h1>
          <p className="page-description">Coordenador ou ADM configura login e senha de professores e usuarios internos.</p>
        </div>
        <div className="page-actions"><a className="btn btn-secondary" href="/alunos/credenciais">Credenciais de alunos</a></div>
      </div>
      {feedback && <div className={feedback.includes("Erro") ? "form-error" : "form-success"} style={{ marginBottom: 16 }}>{feedback}</div>}
      <div className="card">
        <div className="card-body" style={{ paddingTop: 12 }}>
          <table className="data-table">
            <thead><tr><th>Professor / usuario</th><th>Login</th><th>Perfil</th><th>Status</th><th>Acoes</th></tr></thead>
            <tbody>
              {usuarios.map((u) => (
                <tr key={u.id}>
                  <td style={{ fontWeight: 700 }}>{u.nome}</td>
                  <td>{u.usuario || "-"}</td>
                  <td>{u.perfil}</td>
                  <td><span className={`badge badge-${u.temAcesso ? "success" : "warning"}`}><span className="badge-dot" />{u.temAcesso ? "Com acesso" : "Sem acesso"}</span></td>
                  <td><button className="btn btn-secondary btn-sm" onClick={() => { setEdit(u); setSenha(""); }}>Editar senha</button></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
      {edit && (
        <div className="modal-overlay" onClick={(e) => e.target === e.currentTarget && setEdit(null)}>
          <div className="modal-box" style={{ maxWidth: 520 }}>
            <div className="modal-header"><div className="modal-title">Editar acesso</div><button className="modal-close" onClick={() => setEdit(null)}>x</button></div>
            <div className="modal-body">
              <div className="form-grid">
                <div className="form-group"><label className="form-label">Nome</label><input className="form-input" value={edit.nome} readOnly /></div>
                <div className="form-group"><label className="form-label">Login</label><input className="form-input" value={edit.usuario} onChange={(e) => setEdit({ ...edit, usuario: e.target.value })} /></div>
                <div className="form-group"><label className="form-label">Perfil</label><select className="form-input" value={edit.perfil} onChange={(e) => setEdit({ ...edit, perfil: e.target.value })}><option>Professor</option><option>Coordenador</option><option>Admin</option></select></div>
                <div className="form-group"><label className="form-label">Nova senha</label><input className="form-input" type="password" value={senha} onChange={(e) => setSenha(e.target.value)} /></div>
              </div>
            </div>
            <div className="modal-footer"><button className="btn btn-secondary" onClick={() => setEdit(null)}>Cancelar</button><button className="btn btn-primary" disabled={!edit.usuario || senha.length < 4} onClick={salvar}>Salvar acesso</button></div>
          </div>
        </div>
      )}
    </AppShell>
  );
}
