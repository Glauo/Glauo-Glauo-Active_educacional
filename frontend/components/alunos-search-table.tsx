"use client";

import { useMemo, useState } from "react";
import { EditarAlunoBtn } from "./aluno-modal";

type Aluno = {
  id?: string;
  nome?: string;
  name?: string;
  turma?: string;
  classe?: string;
  livro?: string;
  book?: string;
  modulo?: string;
  modalidade?: string;
  vip_tipo_plano?: string;
  vip_aulas_total?: string | number;
  vip_aulas_restantes?: string | number;
  status?: string;
  situacao?: string;
  status_financeiro?: string;
  situacao_financeira?: string;
  responsavel?: unknown;
  responsavel_nome?: string;
  responsavel_telefone?: string;
  responsavel_email?: string;
  telefone?: string;
  whatsapp?: string;
  phone?: string;
  email?: string;
  login?: string;
  senha?: string;
  data_nascimento?: string;
  nascimento?: string;
  cpf?: string;
  endereco?: string;
  address?: string;
  observacoes?: string;
  obs?: string;
  [k: string]: unknown;
};

type Recebimento = {
  id?: string;
  aluno?: string;
  nome?: string;
  aluno_login?: string;
  descricao?: string;
  valor?: string | number;
  vencimento?: string;
  data_vencimento?: string;
  status?: string;
  situacao?: string;
  [k: string]: unknown;
};

function text(value: unknown) {
  if (value && typeof value === "object" && !Array.isArray(value)) {
    const row = value as Record<string, unknown>;
    return String(row.nome || row.name || row.celular || row.telefone || row.email || "").trim();
  }
  return String(value || "").trim();
}

function parseValor(v: unknown) {
  return parseFloat(String(v || "0").replace(/[^\d.,-]/g, "").replace(",", ".")) || 0;
}

function formatBRL(v: number) {
  return v.toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
}

function whatsappUrl(phone: unknown, message: string) {
  let digits = String(phone || "").replace(/\D/g, "");
  if (digits.length === 10 || digits.length === 11) digits = `55${digits}`;
  return digits ? `https://wa.me/${digits}?text=${encodeURIComponent(message)}` : "";
}

function credentialMessage(aluno: Aluno, login: string, senha: string) {
  const nome = text(aluno.nome || aluno.name || "Aluno");
  return [
    `Olá, ${nome}!`,
    "Seu acesso ao portal do aluno Active Educacional foi atualizado.",
    "",
    `Login: ${login}`,
    `Senha: ${senha}`,
    "",
    "Acesse pelo portal da escola. Se tiver dificuldade, fale com a secretaria.",
  ].join("\n");
}

function toInt(value: unknown) {
  const n = parseInt(String(value || "0"), 10);
  return Number.isFinite(n) ? n : 0;
}

function vipLabel(aluno: Aluno) {
  const total = toInt(aluno.vip_aulas_total);
  const restantes = Math.max(0, toInt(aluno.vip_aulas_restantes || total));
  if (!total) return "";
  const dadas = Math.max(0, total - restantes);
  return `${dadas}/${total} aulas dadas | ${restantes} restantes`;
}

function fmtDate(v: unknown) {
  const raw = text(v);
  if (!raw) return "-";
  if (/^\d{2}\/\d{2}\/\d{4}/.test(raw)) return raw.slice(0, 10);
  const d = new Date(raw);
  return Number.isNaN(d.getTime()) ? raw : d.toLocaleDateString("pt-BR");
}

function statusBadge(s: string) {
  const l = s.toLowerCase();
  if (l.includes("inativ") || l.includes("cancel")) return "neutral";
  if (l.includes("atenc") || l.includes("pendente")) return "warning";
  return "success";
}

function financBadge(s: string) {
  const l = s.toLowerCase();
  if (l.includes("atraso") || l.includes("vencido") || l.includes("inadim")) return "danger";
  if (l.includes("pendent") || l.includes("boleto")) return "warning";
  return "success";
}

function DetailRow({ label, value }: { label: string; value?: string }) {
  if (!value || value === "-") return null;
  return (
    <div className="drawer-detail-row">
      <span className="drawer-detail-label">{label}</span>
      <span className="drawer-detail-value">{value}</span>
    </div>
  );
}

function faturasDoAluno(aluno: Aluno, recebimentos: Recebimento[]) {
  const nome = text(aluno.nome || aluno.name).toLowerCase();
  const login = text(aluno.login).toLowerCase();
  return recebimentos
    .filter((r) => {
      const alunoRec = text(r.aluno || r.nome).toLowerCase();
      const loginRec = text(r.aluno_login).toLowerCase();
      return (nome && alunoRec === nome) || (login && loginRec === login);
    })
    .sort((a, b) => text(a.vencimento || a.data_vencimento).localeCompare(text(b.vencimento || b.data_vencimento)));
}

function AcessoAlunoBox({ aluno }: { aluno: Aluno }) {
  const [login, setLogin] = useState(text(aluno.login));
  const [senha, setSenha] = useState(text(aluno.senha));
  const [saving, setSaving] = useState(false);
  const [feedback, setFeedback] = useState("");
  const [whatsappLink, setWhatsappLink] = useState("");

  async function salvar() {
    setFeedback("");
    setWhatsappLink("");
    if (!login.trim() || senha.length < 4) {
      setFeedback("Informe login e senha com pelo menos 4 caracteres.");
      return;
    }
    setSaving(true);
    const res = await fetch("/api/alunos/credenciais", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ id: aluno.id, login, senha }),
    });
    const data = await res.json().catch(() => ({}));
    setSaving(false);
    if (!res.ok) {
      setFeedback(data.error || "Erro ao alterar acesso.");
      return;
    }
    setFeedback("Acesso atualizado com sucesso.");
    const fallbackPhone = text(aluno.celular || aluno.whatsapp || aluno.telefone || aluno.responsavel_telefone || aluno.responsavel);
    setWhatsappLink(data.whatsapp_url || whatsappUrl(fallbackPhone, credentialMessage(aluno, login, senha)));
  }

  return (
    <div className="drawer-section">
      <div className="drawer-section-title">Acesso do aluno</div>
      <div className="form-grid">
        <div className="form-group">
          <label className="form-label">Login</label>
          <input className="form-input" value={login} onChange={(e) => setLogin(e.target.value)} />
        </div>
        <div className="form-group">
          <label className="form-label">Senha</label>
          <input className="form-input" value={senha} onChange={(e) => setSenha(e.target.value)} />
        </div>
      </div>
      {feedback && <div className={feedback.includes("sucesso") ? "form-success" : "form-error"} style={{ marginTop: 10 }}>{feedback}</div>}
      <div style={{ display: "flex", gap: 8, marginTop: 12, flexWrap: "wrap" }}>
        <button className="btn btn-primary btn-sm" onClick={salvar} disabled={saving || !aluno.id}>{saving ? "Salvando..." : "Alterar senha/login"}</button>
        {whatsappLink && <a className="btn btn-secondary btn-sm" href={whatsappLink} target="_blank" rel="noreferrer">Enviar WhatsApp</a>}
        <a className="btn btn-secondary btn-sm" href="/alunos/credenciais">Gerenciar todos</a>
      </div>
    </div>
  );
}

function AlunoDrawer({ aluno, recebimentos, onClose, canManageAccess }: { aluno: Aluno; recebimentos: Recebimento[]; onClose: () => void; canManageAccess: boolean }) {
  const nome = text(aluno.nome || aluno.name || "Aluno");
  const turma = text(aluno.turma || aluno.classe || "-");
  const livro = text(aluno.livro || aluno.book || "-");
  const modulo = text(aluno.modulo || aluno.modalidade || "-");
  const vip = vipLabel(aluno);
  const status = text(aluno.status || aluno.situacao || "Ativo");
  const faturas = faturasDoAluno(aluno, recebimentos);
  const totalAberto = faturas.filter((f) => financBadge(text(f.status || f.situacao || "Pendente")) !== "success").reduce((s, f) => s + parseValor(f.valor), 0);
  const financeiro = text(aluno.status_financeiro || aluno.situacao_financeira || (totalAberto > 0 ? "Pendente" : "Regular"));
  const responsavel = text(aluno.responsavel_nome || aluno.responsavel || "-");
  const telefone = text(aluno.responsavel_telefone || aluno.telefone || aluno.phone || "-");
  const email = text(aluno.responsavel_email || aluno.email || "-");
  const nascimento = text(aluno.data_nascimento || aluno.nascimento || "-");
  const cpf = text(aluno.cpf || "-");
  const endereco = text(aluno.endereco || aluno.address || "-");
  const obs = text(aluno.observacoes || aluno.obs || "-");
  const hue = (nome.charCodeAt(0) * 137) % 360;
  const initials = nome.split(" ").map((n) => n[0]).slice(0, 2).join("").toUpperCase();

  return (
    <>
      <div className="drawer-backdrop" onClick={onClose} />
      <div className="drawer">
        <div className="drawer-header">
          <div className="drawer-title-row">
            <div className="avatar avatar-lg" style={{ background: `hsl(${hue},50%,42%)` }}>{initials}</div>
            <div>
              <h2 className="drawer-title">{nome}</h2>
              <p className="drawer-subtitle">Turma {turma} | {livro}</p>
            </div>
          </div>
          <button className="drawer-close" onClick={onClose} aria-label="Fechar">
            <svg viewBox="0 0 20 20" fill="currentColor"><path fillRule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clipRule="evenodd" /></svg>
          </button>
          <div className="drawer-badges">
            <span className={`badge badge-${statusBadge(status)}`}><span className="badge-dot" />{status}</span>
            <span className={`badge badge-${financBadge(financeiro)}`}><span className="badge-dot" />{financeiro}</span>
          </div>
        </div>

        <div className="drawer-body">
          <div className="drawer-section">
            <div className="drawer-section-title">Dados pessoais</div>
            <DetailRow label="CPF" value={cpf} />
            <DetailRow label="Data de nascimento" value={nascimento} />
            <DetailRow label="Endereco" value={endereco} />
          </div>

          <div className="drawer-section">
            <div className="drawer-section-title">Responsavel</div>
            <DetailRow label="Nome" value={responsavel} />
            <DetailRow label="Telefone" value={telefone} />
            <DetailRow label="E-mail" value={email} />
          </div>

          <div className="drawer-section">
            <div className="drawer-section-title">Academico</div>
            <DetailRow label="Turma" value={turma} />
            <DetailRow label="Modulo" value={modulo} />
            <DetailRow label="Plano VIP" value={text(aluno.vip_tipo_plano)} />
            <DetailRow label="Aulas VIP" value={vip} />
            <DetailRow label="Livro / Apostila" value={livro} />
          </div>

          <div className="drawer-section">
            <div className="drawer-section-title">Boletos e faturas</div>
            {faturas.length === 0 ? (
              <p className="drawer-obs">Nenhuma fatura encontrada para este aluno.</p>
            ) : (
              <table className="data-table">
                <thead><tr><th>Descricao</th><th>Vencimento</th><th>Valor</th><th>Status</th><th>Boleto</th></tr></thead>
                <tbody>
                  {faturas.map((f, i) => (
                    <tr key={text(f.id || i)}>
                      <td>{text(f.descricao || "Mensalidade")}</td>
                      <td style={{ fontWeight: 700 }}>{fmtDate(f.vencimento || f.data_vencimento)}</td>
                      <td>{formatBRL(parseValor(f.valor))}</td>
                      <td><span className={`badge badge-${financBadge(text(f.status || f.situacao || "Pendente"))}`}><span className="badge-dot" />{text(f.status || f.situacao || "Pendente")}</span></td>
                      <td>{f.id ? <a className="btn btn-secondary btn-sm" href={`/api/financeiro/boleto?id=${text(f.id)}`} target="_blank" rel="noreferrer">Abrir</a> : "-"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>

          {obs !== "-" && (
            <div className="drawer-section">
              <div className="drawer-section-title">Observacoes</div>
              <p className="drawer-obs">{obs}</p>
            </div>
          )}
          {canManageAccess && <AcessoAlunoBox aluno={aluno} />}
        </div>

        <div className="drawer-footer">
          <EditarAlunoBtn aluno={aluno} />
        </div>
      </div>
    </>
  );
}

export function AlunosSearchTable({ alunos, recebimentos, canManageAccess }: { alunos: Aluno[]; recebimentos: Recebimento[]; canManageAccess: boolean }) {
  const [busca, setBusca] = useState("");
  const [filtroStatus, setFiltroStatus] = useState("Todos");
  const [filtroFinanceiro, setFiltroFinanceiro] = useState("Todos");
  const [filtroTurma, setFiltroTurma] = useState("Todas");
  const [alunoSelecionado, setAlunoSelecionado] = useState<Aluno | null>(null);

  const turmas = useMemo(() => {
    const set = new Set(alunos.map((a) => text(a.turma || a.classe)).filter(Boolean));
    return ["Todas", ...Array.from(set).sort()];
  }, [alunos]);

  const filtrados = useMemo(() => {
    return alunos.filter((a) => {
      const nome = text(a.nome || a.name).toLowerCase();
      const turma = text(a.turma || a.classe).toLowerCase();
      const resp = text(a.responsavel_nome || a.responsavel).toLowerCase();
      const modulo = text(a.modulo || a.modalidade).toLowerCase();
      const status = text(a.status || a.situacao || "Ativo");
      const faturas = faturasDoAluno(a, recebimentos);
      const totalAberto = faturas.filter((f) => financBadge(text(f.status || f.situacao || "Pendente")) !== "success").reduce((s, f) => s + parseValor(f.valor), 0);
      const financeiro = text(a.status_financeiro || a.situacao_financeira || (totalAberto > 0 ? "Pendente" : "Regular"));

      const q = busca.toLowerCase();
      const matchBusca = !busca || nome.includes(q) || turma.includes(q) || resp.includes(q) || modulo.includes(q);
      const matchStatus = filtroStatus === "Todos" || status.toLowerCase().includes(filtroStatus.toLowerCase());
      const matchFinanceiro = filtroFinanceiro === "Todos" ||
        (filtroFinanceiro === "Regular" && financBadge(financeiro) === "success") ||
        (filtroFinanceiro === "Inadimplente" && financBadge(financeiro) === "danger") ||
        (filtroFinanceiro === "Pendente" && financBadge(financeiro) === "warning");
      const matchTurma = filtroTurma === "Todas" || text(a.turma || a.classe) === filtroTurma;

      return matchBusca && matchStatus && matchFinanceiro && matchTurma;
    });
  }, [alunos, recebimentos, busca, filtroStatus, filtroFinanceiro, filtroTurma]);

  return (
    <>
      {alunoSelecionado && (
        <AlunoDrawer aluno={alunoSelecionado} recebimentos={recebimentos} canManageAccess={canManageAccess} onClose={() => setAlunoSelecionado(null)} />
      )}

      <div className="card">
        <div className="toolbar">
          <div className="toolbar-left">
            <div className="search-bar">
              <span className="search-icon"><svg viewBox="0 0 20 20" fill="currentColor"><path fillRule="evenodd" d="M8 4a4 4 0 100 8 4 4 0 000-8zM2 8a6 6 0 1110.89 3.476l4.817 4.817a1 1 0 01-1.414 1.414l-4.816-4.816A6 6 0 012 8z" clipRule="evenodd" /></svg></span>
              <input className="search-input" placeholder="Buscar por nome, turma, modulo ou responsavel..." value={busca} onChange={(e) => setBusca(e.target.value)} />
            </div>
          </div>
          <div className="toolbar-right">
            <select className="filter-select" value={filtroTurma} onChange={(e) => setFiltroTurma(e.target.value)}>
              {turmas.map((t) => <option key={t}>{t}</option>)}
            </select>
            <select className="filter-select" value={filtroStatus} onChange={(e) => setFiltroStatus(e.target.value)}>
              <option value="Todos">Qualquer status</option>
              <option>Ativo</option>
              <option>Inativo</option>
            </select>
            <select className="filter-select" value={filtroFinanceiro} onChange={(e) => setFiltroFinanceiro(e.target.value)}>
              <option value="Todos">Todo financeiro</option>
              <option>Regular</option>
              <option>Inadimplente</option>
              <option>Pendente</option>
            </select>
          </div>
        </div>
      </div>

      <div className="card">
        <div className="card-header">
          <div>
            <div className="section-eyebrow">Lista</div>
            <h3 className="section-title">Todos os alunos</h3>
            <p className="section-subtitle">{filtrados.length === alunos.length ? `${alunos.length} registros` : `${filtrados.length} de ${alunos.length} (filtro ativo)`}</p>
          </div>
        </div>
        <div className="card-body" style={{ paddingTop: "12px" }}>
          {filtrados.length === 0 ? (
            <div className="empty-state">
              <div className="empty-title">Nenhum aluno encontrado</div>
              <p className="empty-desc">Ajuste os filtros para ver mais resultados.</p>
            </div>
          ) : (
            <table className="data-table">
              <thead>
                <tr>
                  <th>Aluno</th>
                  <th>Turma</th>
                  <th>Modulo</th>
                  <th>VIP</th>
                  <th>Livro</th>
                  <th>Status</th>
                  <th>Financeiro</th>
                  <th>Acoes</th>
                </tr>
              </thead>
              <tbody>
                {filtrados.map((a, i) => {
                  const nome = text(a.nome || a.name || `Aluno ${i + 1}`);
                  const turma = text(a.turma || a.classe || "-");
                  const modulo = text(a.modulo || a.modalidade || "-");
                  const vip = vipLabel(a);
                  const livro = text(a.livro || a.book || "-");
                  const status = text(a.status || a.situacao || "Ativo");
                  const faturas = faturasDoAluno(a, recebimentos);
                  const totalAberto = faturas.filter((f) => financBadge(text(f.status || f.situacao || "Pendente")) !== "success").reduce((s, f) => s + parseValor(f.valor), 0);
                  const financeiro = text(a.status_financeiro || a.situacao_financeira || (totalAberto > 0 ? "Pendente" : "Regular"));
                  const hue = (nome.charCodeAt(0) * 137) % 360;
                  return (
                    <tr key={text(a.id || i)} className="table-row-clickable" onClick={() => setAlunoSelecionado(a)}>
                      <td>
                        <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
                          <div className="avatar avatar-sm" style={{ background: `hsl(${hue},50%,42%)` }}>{nome.slice(0, 2).toUpperCase()}</div>
                          <div className="table-name-cell">
                            <span className="table-name-primary">{nome}</span>
                            {text(a.responsavel_nome || a.responsavel) && <span className="table-name-secondary">{text(a.responsavel_nome || a.responsavel)}</span>}
                          </div>
                        </div>
                      </td>
                      <td>{turma}</td>
                      <td>{modulo}</td>
                      <td>{vip || "-"}</td>
                      <td>{livro}</td>
                      <td><span className={`badge badge-${statusBadge(status)}`}><span className="badge-dot" />{status}</span></td>
                      <td><span className={`badge badge-${financBadge(financeiro)}`}><span className="badge-dot" />{financeiro}</span></td>
                      <td onClick={(e) => e.stopPropagation()}><EditarAlunoBtn aluno={a} /></td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </>
  );
}
