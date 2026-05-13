"use client";

import { useEffect, useState } from "react";
import { AppShell } from "@/components/app-shell";

type Usuario = { id: string; nome: string; usuario: string; perfil: string; temAcesso: boolean };
type AccessModule = { key: string; label: string; path: string; allowed: boolean };
type UsuarioPermissao = { id: string; nome: string; usuario: string; perfil: string; blocked_routes: string[]; modules: AccessModule[] };

export default function CredenciaisUsuariosPage() {
  const [usuarios, setUsuarios] = useState<Usuario[]>([]);
  const [edit, setEdit] = useState<Usuario | null>(null);
  const [senha, setSenha] = useState("");
  const [feedback, setFeedback] = useState("");
  const [permissoes, setPermissoes] = useState<UsuarioPermissao[]>([]);
  const [savingPermissao, setSavingPermissao] = useState("");

  useEffect(() => {
    fetch("/api/usuarios/credenciais").then((r) => r.json()).then((d) => setUsuarios(Array.isArray(d) ? d : []));
    carregarPermissoes();
  }, []);

  async function carregarPermissoes() {
    const res = await fetch("/api/acessos/permissoes");
    const data = await res.json().catch(() => ({}));
    setPermissoes(Array.isArray(data.usuarios) ? data.usuarios : []);
  }

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
    void carregarPermissoes();
  }

  async function alternarPermissao(usuario: UsuarioPermissao, module: AccessModule, liberado: boolean) {
    const atual = new Set(usuario.blocked_routes || []);
    if (liberado) atual.delete(module.path);
    else atual.add(module.path);

    const blocked_routes = Array.from(atual);
    setSavingPermissao(`${usuario.usuario}:${module.path}`);
    const res = await fetch("/api/acessos/permissoes", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ usuario: usuario.usuario, blocked_routes }),
    });
    const data = await res.json().catch(() => ({}));
    setSavingPermissao("");
    if (!res.ok) {
      setFeedback(data.error || "Erro ao salvar permissao.");
      return;
    }
    setPermissoes((prev) => prev.map((item) =>
      item.usuario === usuario.usuario
        ? {
            ...item,
            blocked_routes,
            modules: item.modules.map((m) => m.path === module.path ? { ...m, allowed: liberado } : m),
          }
        : item
    ));
    setFeedback("Permissao atualizada com sucesso.");
  }

  return (
    <AppShell breadcrumb="Acessos">
      <div className="page-header">
        <div className="page-title-block">
          <div className="page-eyebrow"><span className="page-eyebrow-dot" />Seguranca</div>
          <h1 className="page-title">Credenciais de Usuarios</h1>
          <p className="page-description">Coordenador ou ADM configura login e senha de professores e usuarios internos.</p>
        </div>
        <div className="page-actions">
          <a className="btn btn-secondary" href="#permissoes">Permissoes por usuario</a>
          <a className="btn btn-secondary" href="/alunos/credenciais">Credenciais de alunos</a>
        </div>
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
      <div className="card" id="permissoes" style={{ marginTop: 18 }}>
        <div className="card-header">
          <div>
            <div className="section-eyebrow">Permissoes</div>
            <h3 className="section-title">Controle de acesso por usuario</h3>
            <p className="section-subtitle">Desmarque os modulos que o usuario nao pode acessar. A alteracao reflete no menu e bloqueia a navegacao pelo painel.</p>
          </div>
        </div>
        <div className="card-body" style={{ paddingTop: 12 }}>
          <table className="data-table">
            <thead><tr><th>Usuario</th><th>Perfil</th><th>Modulos liberados</th></tr></thead>
            <tbody>
              {permissoes.map((u) => (
                <tr key={u.usuario}>
                  <td>
                    <div style={{ fontWeight: 800 }}>{u.nome || u.usuario}</div>
                    <div className="muted" style={{ fontSize: "0.78rem" }}>{u.usuario}</div>
                  </td>
                  <td>{u.perfil}</td>
                  <td>
                    <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
                      {u.modules.map((m) => {
                        const id = `${u.usuario}:${m.path}`;
                        return (
                          <label key={m.path} className={`badge badge-${m.allowed ? "success" : "neutral"}`} style={{ cursor: "pointer" }}>
                            <input
                              type="checkbox"
                              checked={m.allowed}
                              disabled={savingPermissao === id}
                              onChange={(e) => alternarPermissao(u, m, e.target.checked)}
                              style={{ marginRight: 6 }}
                            />
                            {m.label}
                          </label>
                        );
                      })}
                    </div>
                  </td>
                </tr>
              ))}
              {!permissoes.length && (
                <tr><td colSpan={3}><div className="empty-state"><div className="empty-title">Nenhum usuario encontrado</div><p className="empty-desc">Crie usuarios internos para controlar permissao por modulo.</p></div></td></tr>
              )}
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
