"use client";

import { useState, useMemo, useEffect } from "react";
import { useRouter } from "next/navigation";

type AulaItem = {
  id?: string;
  professor?: string;
  aluno?: string;
  nome?: string;
  data_aula?: string;
  vencimento?: string;
  data_vencimento?: string;
  turma?: string;
  horario?: string;
  local?: string;
  modulo?: string;
  descricao?: string;
  valor?: number | string;
  status?: string;
  duracao_minutos?: number | string;
  licao_inicio?: string;
  licao_fim?: string;
  [k: string]: unknown;
};

type Fechamento = {
  id: string;
  professor_id: string;
  professor_nome: string;
  periodo_inicio: string;
  periodo_fim: string;
  total_aulas: number;
  valor_total: number;
  status: "pre_fechamento" | "fechado" | "enviado" | "pago" | "cancelado";
  aulas: AulaItem[];
  created_at: string;
  updated_at: string;
  pago_em?: string;
  pago_por?: string;
};

type Professor = {
  id?: string;
  nome?: string;
  name?: string;
  telefone?: string;
  email?: string;
  [k: string]: unknown;
};

function parseValor(v: unknown): number {
  return parseFloat(String(v || "0").replace(/[^\d.,]/g, "").replace(",", ".")) || 0;
}

function formatBRL(v: number): string {
  return v.toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
}

function printWindow(elementId: string, title = "Relatório — Ativo Educacional") {
  const el = document.getElementById(elementId);
  if (!el) return;
  const w = window.open("", "_blank", "width=960,height=700");
  if (!w) return;
  w.document.write(`<!DOCTYPE html><html lang="pt-BR"><head>
<meta charset="utf-8"><title>${title}</title>
<style>
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;color:#1e293b;background:#fff;padding:24px 32px;font-size:14px}
table{width:100%;border-collapse:collapse;font-size:13px}
thead tr{background:#0f172a!important;color:#fff!important;-webkit-print-color-adjust:exact;print-color-adjust:exact}
th{padding:9px 12px;text-align:left;font-weight:700;font-size:11px;text-transform:uppercase;letter-spacing:.06em}
td{padding:9px 12px}
tbody tr:nth-child(even){background:#f8fafc}
tbody tr{border-bottom:1px solid #e2e8f0}
tfoot tr:first-child{border-top:2px solid #0f172a}
@page{margin:15mm;size:A4}
@media print{body{padding:0}}
</style></head><body>${el.innerHTML}</body></html>`);
  w.document.close();
  setTimeout(() => { try { w.print(); } catch { /**/ } }, 400);
}

function parseBRDate(v: string): Date {
  if (!v) return new Date(NaN);
  const m = v.match(/^(\d{2})\/(\d{2})\/(\d{4})/);
  if (m) return new Date(Number(m[3]), Number(m[2]) - 1, Number(m[1]));
  return new Date(v);
}

function fmtDate(v: string) {
  if (!v) return "—";
  if (/^\d{2}\/\d{2}\/\d{4}/.test(v)) return v.substring(0, 10);
  const d = parseBRDate(v);
  if (isNaN(d.getTime())) return v;
  return d.toLocaleDateString("pt-BR");
}

function statusBadge(s: string) {
  const l = s.toLowerCase();
  if (l.includes("pago") || l.includes("baixado") || l.includes("liquidado")) return "success";
  if (l.includes("atraso") || l.includes("vencido")) return "danger";
  return "warning";
}

function statusFechamentoBadge(s: string) {
  if (s === "pago") return { cls: "success", label: "Pago" };
  if (s === "fechado") return { cls: "neutral", label: "Fechado" };
  if (s === "enviado") return { cls: "warning", label: "Enviado" };
  if (s === "cancelado") return { cls: "danger", label: "Cancelado" };
  return { cls: "gold", label: "Pré-fechamento" };
}

function isProfessorPayable(p: AulaItem) {
  const all = [p.professor, p.aluno, p.nome, p.descricao, p.tipo_origem]
    .map((v) => String(v || "").toLowerCase())
    .join(" ");
  return all.includes("professor") || all.includes("salário") || all.includes("salario") || all.includes("docente") || all.includes("pagto prof") || all.includes("aula_professor");
}

function periodoAtual(): { inicio: string; fim: string } {
  const agora = new Date();
  let anoInicio = agora.getFullYear();
  let mesInicio = agora.getMonth() - 1;
  if (mesInicio < 0) { mesInicio = 11; anoInicio--; }
  const inicio = new Date(anoInicio, mesInicio, 10).toISOString().slice(0, 10);
  const fim = new Date(agora.getFullYear(), agora.getMonth(), 9).toISOString().slice(0, 10);
  return { inicio, fim };
}

function dentroDoperiodo(data: string, inicio: string, fim: string): boolean {
  if (!data) return false;
  let d: Date;
  const mBR = data.match(/^(\d{2})\/(\d{2})\/(\d{4})/);
  if (mBR) d = new Date(Number(mBR[3]), Number(mBR[2]) - 1, Number(mBR[1]));
  else d = new Date(data);
  if (isNaN(d.getTime())) return false;
  const dInicio = new Date(inicio);
  const dFim = new Date(fim);
  dInicio.setHours(0, 0, 0, 0);
  dFim.setHours(23, 59, 59, 999);
  return d >= dInicio && d <= dFim;
}

function DetalheProfModal({
  professor,
  payables,
  fechamento,
  onClose,
  onSaved,
}: {
  professor: Professor;
  payables: AulaItem[];
  fechamento?: Fechamento;
  onClose: () => void;
  onSaved: () => void;
}) {
  const router = useRouter();
  const profNome = String(professor.nome || professor.name || "");
  const { inicio, fim } = periodoAtual();

  const aulasDoMes = useMemo(() => {
    if (fechamento) return fechamento.aulas;
    return payables.filter((p) => {
      const pNome = String(p.professor || p.aluno || p.nome || "");
      const dataAula = String(p.data_aula || p.vencimento || p.data_vencimento || "");
      return (isProfessorPayable(p) || pNome === profNome) && pNome === profNome && dentroDoperiodo(dataAula, inicio, fim);
    });
  }, [payables, fechamento, profNome, inicio, fim]);

  const total = aulasDoMes.reduce((s, a) => s + parseValor(a.valor), 0);
  const totalPago = aulasDoMes.filter((a) => statusBadge(String(a.status || "")) === "success").reduce((s, a) => s + parseValor(a.valor), 0);

  const [gerando, setGerando] = useState(false);
  const [marcandoPago, setMarcandoPago] = useState(false);
  const [msg, setMsg] = useState("");

  async function gerarFechamento() {
    setGerando(true);
    setMsg("");
    const profId = String(professor.id || profNome);
    const res = await fetch("/api/financeiro/professor-fechamento", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        professor_nome: profNome,
        professor_id: profId,
        periodo_inicio: inicio,
        periodo_fim: fim,
      }),
    });
    setGerando(false);
    if (!res.ok) {
      const d = await res.json().catch(() => ({}));
      setMsg((d as { error?: string }).error || "Erro ao gerar fechamento.");
      return;
    }
    setMsg("Fechamento gerado com sucesso!");
    onSaved();
  }

  async function marcarPago() {
    if (!fechamento) { setMsg("Gere o fechamento primeiro."); return; }
    if (!confirm(`Marcar fechamento de ${profNome} como PAGO? Esta ação requer perfil Admin.`)) return;
    setMarcandoPago(true);
    const res = await fetch("/api/financeiro/professor-fechamento", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ id: fechamento.id, status: "pago" }),
    });
    setMarcandoPago(false);
    if (!res.ok) {
      const d = await res.json().catch(() => ({}));
      setMsg((d as { error?: string }).error || "Erro ao marcar como pago.");
      return;
    }
    setMsg("Marcado como pago!");
    onSaved();
    router.refresh();
  }

  const hoje = new Date().toLocaleDateString("pt-BR");
  const aulasOrdenadas = [...aulasDoMes].sort((a, b) =>
    String(a.data_aula || a.vencimento || "").localeCompare(String(b.data_aula || b.vencimento || ""))
  );

  return (
    <div className="modal-overlay" onClick={(e) => e.target === e.currentTarget && onClose()}>
      <div className="modal-box" style={{ maxWidth: 860, width: "95vw", maxHeight: "92vh", overflowY: "auto" }}>
        <div className="modal-header">
          <div>
            <div className="modal-title">Fechamento — {profNome}</div>
            <div className="modal-subtitle">Período: {fmtDate(inicio)} a {fmtDate(fim)}</div>
          </div>
          <div style={{ display: "flex", gap: 8 }}>
            <button className="btn btn-secondary btn-sm" onClick={() => printWindow("fechamento-print", `Fechamento — ${profNome}`)}>
              <svg viewBox="0 0 20 20" fill="currentColor" width={14} height={14} style={{ marginRight: 4 }}>
                <path fillRule="evenodd" d="M5 4v3H4a2 2 0 00-2 2v3a2 2 0 002 2h1v2a1 1 0 001 1h8a1 1 0 001-1v-2h1a2 2 0 002-2V9a2 2 0 00-2-2h-1V4a1 1 0 00-1-1H6a1 1 0 00-1 1zm2 0h6v3H7V4zm0 8H6v4h8v-4h-7v1a1 1 0 102 0v-1z" clipRule="evenodd" />
              </svg>
              Imprimir / PDF
            </button>
            <button className="modal-close" onClick={onClose}>
              <svg viewBox="0 0 20 20" fill="currentColor"><path fillRule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clipRule="evenodd" /></svg>
            </button>
          </div>
        </div>

        <div className="modal-body" id="fechamento-print" style={{ padding: "24px 28px" }}>
          {/* Cabeçalho do documento */}
          <div style={{ textAlign: "center", borderBottom: "2px solid var(--navy-900)", paddingBottom: 16, marginBottom: 20 }}>
            <div style={{ fontWeight: 900, fontSize: "1.375rem", color: "var(--navy-900)" }}>ATIVO EDUCACIONAL</div>
            <div style={{ fontSize: "0.75rem", color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.14em", marginTop: 4 }}>Fechamento de Pagamento — Professor</div>
          </div>

          {/* Dados do professor */}
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: "10px 20px", padding: "14px 18px", background: "var(--surface-raised)", borderRadius: "var(--radius-md)", border: "1px solid var(--border)", marginBottom: 20 }}>
            <div style={{ gridColumn: "span 2" }}>
              <div style={{ fontSize: "0.7rem", textTransform: "uppercase", letterSpacing: "0.1em", color: "var(--text-muted)", marginBottom: 2 }}>Professor</div>
              <div style={{ fontWeight: 700, fontSize: "1.0625rem", color: "var(--navy-900)" }}>{profNome}</div>
            </div>
            <div>
              <div style={{ fontSize: "0.7rem", textTransform: "uppercase", letterSpacing: "0.1em", color: "var(--text-muted)", marginBottom: 2 }}>Emissão</div>
              <div style={{ fontWeight: 600 }}>{hoje}</div>
            </div>
            <div style={{ gridColumn: "span 3" }}>
              <div style={{ fontSize: "0.7rem", textTransform: "uppercase", letterSpacing: "0.1em", color: "var(--text-muted)", marginBottom: 2 }}>Período</div>
              <div style={{ fontWeight: 600 }}>{fmtDate(inicio)} a {fmtDate(fim)}</div>
            </div>
            {fechamento && (
              <div>
                <div style={{ fontSize: "0.7rem", textTransform: "uppercase", letterSpacing: "0.1em", color: "var(--text-muted)", marginBottom: 2 }}>Status</div>
                <span className={`badge badge-${statusFechamentoBadge(fechamento.status).cls}`}>
                  <span className="badge-dot" />{statusFechamentoBadge(fechamento.status).label}
                </span>
              </div>
            )}
          </div>

          {/* Tabela de aulas */}
          <div style={{ marginBottom: 20 }}>
            <div style={{ fontSize: "0.72rem", textTransform: "uppercase", letterSpacing: "0.1em", fontWeight: 700, color: "var(--text-muted)", marginBottom: 8 }}>
              Detalhamento das Aulas ({aulasOrdenadas.length})
            </div>
            {aulasOrdenadas.length === 0 ? (
              <div className="empty-state">
                <div className="empty-title">Nenhuma aula no período</div>
                <p className="empty-desc">Não há aulas registradas em payables para este professor no período.</p>
              </div>
            ) : (
              <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.85rem" }}>
                <thead>
                  <tr style={{ background: "var(--navy-900)", color: "#fff" }}>
                    <th style={{ padding: "8px 10px", textAlign: "left", fontSize: "0.72rem", textTransform: "uppercase" }}>Data</th>
                    <th style={{ padding: "8px 10px", textAlign: "left", fontSize: "0.72rem", textTransform: "uppercase" }}>Turma</th>
                    <th style={{ padding: "8px 10px", textAlign: "left", fontSize: "0.72rem", textTransform: "uppercase" }}>Horário</th>
                    <th style={{ padding: "8px 10px", textAlign: "left", fontSize: "0.72rem", textTransform: "uppercase" }}>Lição / Módulo</th>
                    <th style={{ padding: "8px 10px", textAlign: "center", fontSize: "0.72rem", textTransform: "uppercase" }}>Duração</th>
                    <th style={{ padding: "8px 10px", textAlign: "right", fontSize: "0.72rem", textTransform: "uppercase" }}>Valor</th>
                    <th style={{ padding: "8px 10px", textAlign: "center", fontSize: "0.72rem", textTransform: "uppercase" }}>Status</th>
                  </tr>
                </thead>
                <tbody>
                  {aulasOrdenadas.map((a, i) => {
                    const dataAula = String(a.data_aula || a.vencimento || a.data_vencimento || "—");
                    const licao = [a.licao_inicio, a.licao_fim ? `a ${a.licao_fim}` : ""].filter(Boolean).join(" ") || String(a.modulo || a.descricao || "—");
                    const dur = a.duracao_minutos ? `${a.duracao_minutos} min` : "—";
                    const sPago = statusBadge(String(a.status || "")) === "success";
                    return (
                      <tr key={String(a.id || i)} style={{ background: i % 2 === 0 ? "transparent" : "var(--surface-raised)", borderBottom: "1px solid var(--border)" }}>
                        <td style={{ padding: "8px 10px", fontWeight: 600 }}>{dataAula !== "—" ? fmtDate(dataAula) : "—"}</td>
                        <td style={{ padding: "8px 10px" }}>{String(a.turma || "—")}</td>
                        <td style={{ padding: "8px 10px" }}>{String(a.horario || "—")}</td>
                        <td style={{ padding: "8px 10px", color: "var(--text-secondary)" }}>{licao}</td>
                        <td style={{ padding: "8px 10px", textAlign: "center", color: "var(--text-secondary)" }}>{dur}</td>
                        <td style={{ padding: "8px 10px", textAlign: "right", fontWeight: 700 }}>{formatBRL(parseValor(a.valor))}</td>
                        <td style={{ padding: "8px 10px", textAlign: "center" }}>
                          <span style={{
                            display: "inline-block", padding: "2px 8px", borderRadius: 99,
                            fontSize: "0.68rem", fontWeight: 700, textTransform: "uppercase",
                            background: sPago ? "rgba(5,150,105,0.12)" : "rgba(234,179,8,0.12)",
                            color: sPago ? "var(--green-700)" : "var(--gold-700)"
                          }}>
                            {sPago ? "Pago" : "Pendente"}
                          </span>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
                <tfoot>
                  <tr style={{ borderTop: "2px solid var(--navy-900)" }}>
                    <td colSpan={5} style={{ padding: "9px 10px", fontWeight: 700 }}>Total ({aulasOrdenadas.length} aulas)</td>
                    <td style={{ padding: "9px 10px", textAlign: "right", fontWeight: 800, fontSize: "1rem", color: "var(--navy-900)" }}>{formatBRL(total)}</td>
                    <td />
                  </tr>
                  {totalPago > 0 && (
                    <tr>
                      <td colSpan={5} style={{ padding: "4px 10px", fontSize: "0.78rem", color: "var(--green-700)" }}>Já pago</td>
                      <td style={{ padding: "4px 10px", textAlign: "right", fontWeight: 700, color: "var(--green-700)", fontSize: "0.82rem" }}>{formatBRL(totalPago)}</td>
                      <td />
                    </tr>
                  )}
                  {total - totalPago > 0 && (
                    <tr>
                      <td colSpan={5} style={{ padding: "4px 10px", fontSize: "0.78rem", color: "var(--gold-700)" }}>Saldo a pagar</td>
                      <td style={{ padding: "4px 10px", textAlign: "right", fontWeight: 700, color: "var(--gold-700)", fontSize: "0.82rem" }}>{formatBRL(total - totalPago)}</td>
                      <td />
                    </tr>
                  )}
                </tfoot>
              </table>
            )}
          </div>

          {/* Resumo */}
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16, marginBottom: 20 }}>
            <div style={{ padding: "14px 18px", background: "linear-gradient(135deg, rgba(5,150,105,0.07), rgba(5,150,105,0.02))", border: "1.5px solid rgba(5,150,105,0.18)", borderRadius: "var(--radius-md)" }}>
              <div style={{ fontSize: "0.68rem", textTransform: "uppercase", letterSpacing: "0.1em", color: "var(--text-muted)", marginBottom: 6 }}>Valor Total a Pagar</div>
              <div style={{ fontSize: "1.625rem", fontWeight: 900, color: "var(--green-700)" }}>{formatBRL(total)}</div>
              <div style={{ marginTop: 4, fontSize: "0.78rem", color: "var(--text-secondary)" }}>{aulasOrdenadas.length} aulas no período</div>
            </div>
            {fechamento && (
              <div style={{ padding: "14px 18px", border: "1.5px solid var(--border)", borderRadius: "var(--radius-md)", background: "var(--surface-raised)" }}>
                <div style={{ fontSize: "0.68rem", textTransform: "uppercase", letterSpacing: "0.1em", color: "var(--text-muted)", marginBottom: 6 }}>Status do Fechamento</div>
                <span className={`badge badge-${statusFechamentoBadge(fechamento.status).cls}`}>
                  <span className="badge-dot" />{statusFechamentoBadge(fechamento.status).label}
                </span>
                {fechamento.pago_em && (
                  <div style={{ marginTop: 6, fontSize: "0.78rem", color: "var(--text-secondary)" }}>
                    Pago em: {fmtDate(fechamento.pago_em)} por {fechamento.pago_por}
                  </div>
                )}
              </div>
            )}
          </div>
        </div>

        <div className="modal-footer">
          {msg && <span style={{ flex: 1, fontSize: "0.82rem", color: msg.includes("sucesso") || msg.includes("Pago") ? "var(--green-700)" : "var(--red-600)" }}>{msg}</span>}
          {(!fechamento || fechamento.status === "pre_fechamento") && (
            <button className="btn btn-primary" onClick={gerarFechamento} disabled={gerando}>
              {gerando ? "Gerando…" : fechamento ? "Atualizar fechamento" : "Gerar fechamento"}
            </button>
          )}
          {fechamento && fechamento.status !== "pago" && fechamento.status !== "cancelado" && (
            <button className="btn btn-secondary" onClick={marcarPago} disabled={marcandoPago}>
              {marcandoPago ? "Aguarde…" : "Marcar como pago"}
            </button>
          )}
          <button className="btn btn-secondary" onClick={onClose}>Fechar</button>
        </div>
      </div>
    </div>
  );
}

export function FinanceiroProfessorFechamento({
  professores,
  payables,
}: {
  professores: Professor[];
  payables: AulaItem[];
}) {
  const [fechamentos, setFechamentos] = useState<Fechamento[]>([]);
  const [carregado, setCarregado] = useState(false);
  const [detalheProf, setDetalheProf] = useState<Professor | null>(null);
  const [busca, setBusca] = useState("");

  const { inicio, fim } = periodoAtual();

  async function carregarFechamentos() {
    const res = await fetch("/api/financeiro/professor-fechamento");
    if (res.ok) {
      const data = await res.json().catch(() => ({}));
      setFechamentos(Array.isArray(data.fechamentos) ? data.fechamentos : []);
    }
    setCarregado(true);
  }

  // Load on mount
  useEffect(() => { carregarFechamentos(); }, []);

  const profsFiltrados = useMemo(() => {
    return professores.filter((p) => {
      const nome = String(p.nome || p.name || "");
      return !busca || nome.toLowerCase().includes(busca.toLowerCase());
    });
  }, [professores, busca]);

  function getFechamentoAtual(prof: Professor): Fechamento | undefined {
    const profId = String(prof.id || prof.nome || prof.name || "");
    const profNome = String(prof.nome || prof.name || "");
    return fechamentos.find(
      (f) =>
        (f.professor_id === profId || f.professor_nome === profNome) &&
        f.periodo_inicio === inicio &&
        f.periodo_fim === fim &&
        f.status !== "cancelado"
    );
  }

  function getAulasMes(prof: Professor): AulaItem[] {
    const profNome = String(prof.nome || prof.name || "");
    return payables.filter((p) => {
      const pNome = String(p.professor || p.aluno || p.nome || "");
      const dataAula = String(p.data_aula || p.vencimento || p.data_vencimento || "");
      return pNome === profNome && dentroDoperiodo(dataAula, inicio, fim);
    });
  }

  const totalMes = profsFiltrados.reduce((s, p) => {
    const aulas = getAulasMes(p);
    return s + aulas.reduce((as, a) => as + parseValor(a.valor), 0);
  }, 0);

  const totalFechados = fechamentos.filter((f) => f.status === "pago" && f.periodo_inicio === inicio).reduce((s, f) => s + f.valor_total, 0);

  return (
    <>
      <div className="metric-grid metric-grid-3">
        <div className="metric-card metric-card-blue">
          <div className="metric-icon metric-icon-blue">
            <svg viewBox="0 0 20 20" fill="currentColor"><path fillRule="evenodd" d="M10 9a3 3 0 100-6 3 3 0 000 6zm-7 9a7 7 0 1114 0H3z" clipRule="evenodd" /></svg>
          </div>
          <div className="metric-label">Professores</div>
          <div className="metric-value">{professores.length}</div>
          <div className="metric-note">Cadastrados no sistema</div>
        </div>
        <div className="metric-card metric-card-gold">
          <div className="metric-icon metric-icon-gold">
            <svg viewBox="0 0 20 20" fill="currentColor"><path d="M4 4a2 2 0 00-2 2v1h16V6a2 2 0 00-2-2H4z" /><path fillRule="evenodd" d="M18 9H2v5a2 2 0 002 2h12a2 2 0 002-2V9z" clipRule="evenodd" /></svg>
          </div>
          <div className="metric-label">Total do período</div>
          <div className="metric-value" style={{ fontSize: "1.375rem" }}>{formatBRL(totalMes)}</div>
          <div className="metric-note">{fmtDate(inicio)} a {fmtDate(fim)}</div>
        </div>
        <div className="metric-card metric-card-green">
          <div className="metric-icon metric-icon-green">
            <svg viewBox="0 0 20 20" fill="currentColor"><path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" /></svg>
          </div>
          <div className="metric-label">Fechamentos pagos</div>
          <div className="metric-value" style={{ fontSize: "1.375rem" }}>{formatBRL(totalFechados)}</div>
          <div className="metric-note">{fechamentos.filter((f) => f.status === "pago" && f.periodo_inicio === inicio).length} professores pagos</div>
        </div>
      </div>

      <div className="card">
        <div className="toolbar">
          <div className="toolbar-left">
            <div className="search-bar">
              <span className="search-icon">
                <svg viewBox="0 0 20 20" fill="currentColor"><path fillRule="evenodd" d="M8 4a4 4 0 100 8 4 4 0 000-8zM2 8a6 6 0 1110.89 3.476l4.817 4.817a1 1 0 01-1.414 1.414l-4.816-4.816A6 6 0 012 8z" clipRule="evenodd" /></svg>
              </span>
              <input className="search-input" placeholder="Buscar professor..." value={busca} onChange={(e) => setBusca(e.target.value)} />
            </div>
          </div>
          <div className="toolbar-right">
            <span style={{ fontSize: "0.78rem", color: "var(--text-muted)" }}>Período: {fmtDate(inicio)} a {fmtDate(fim)}</span>
            <button className="btn btn-secondary btn-sm" onClick={carregarFechamentos}>
              <svg viewBox="0 0 20 20" fill="currentColor" width={14} height={14} style={{ marginRight: 4 }}>
                <path fillRule="evenodd" d="M4 2a1 1 0 011 1v2.101a7.002 7.002 0 0111.601 2.566 1 1 0 11-1.885.666A5.002 5.002 0 005.999 7H9a1 1 0 010 2H4a1 1 0 01-1-1V3a1 1 0 011-1zm.008 9.057a1 1 0 011.276.61A5.002 5.002 0 0014.001 13H11a1 1 0 110-2h5a1 1 0 011 1v5a1 1 0 11-2 0v-2.101a7.002 7.002 0 01-11.601-2.566 1 1 0 01.61-1.276z" clipRule="evenodd" />
              </svg>
              Recarregar
            </button>
          </div>
        </div>
      </div>

      <div className="card">
        <div className="card-header">
          <div>
            <div className="section-eyebrow">Fechamentos</div>
            <h3 className="section-title">Pagamento de professores — período atual</h3>
            <p className="section-subtitle">{profsFiltrados.length} professor{profsFiltrados.length !== 1 ? "es" : ""}</p>
          </div>
        </div>
        <div className="card-body" style={{ paddingTop: 0 }}>
          {!carregado ? (
            <div className="empty-state"><div className="empty-title">Carregando fechamentos…</div></div>
          ) : profsFiltrados.length === 0 ? (
            <div className="empty-state">
              <div className="empty-title">Nenhum professor cadastrado</div>
              <p className="empty-desc">Cadastre professores em teachers.json para ver os fechamentos.</p>
            </div>
          ) : (
            <table className="data-table">
              <thead>
                <tr>
                  <th>Professor</th>
                  <th>Aulas no período</th>
                  <th>Valor a pagar</th>
                  <th>Status fechamento</th>
                  <th>Ações</th>
                </tr>
              </thead>
              <tbody>
                {profsFiltrados.map((prof, i) => {
                  const profNome = String(prof.nome || prof.name || `Professor ${i + 1}`);
                  const aulas = getAulasMes(prof);
                  const totalProf = aulas.reduce((s, a) => s + parseValor(a.valor), 0);
                  const fechamento = getFechamentoAtual(prof);
                  const { cls, label } = fechamento
                    ? statusFechamentoBadge(fechamento.status)
                    : { cls: "neutral", label: "Sem fechamento" };

                  return (
                    <tr key={String(prof.id || i)}>
                      <td>
                        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                          <div style={{ width: 32, height: 32, borderRadius: "50%", background: "linear-gradient(135deg, var(--blue-600), var(--navy-900))", display: "flex", alignItems: "center", justifyContent: "center", color: "#fff", fontWeight: 800, fontSize: "0.9rem", flexShrink: 0 }}>
                            {profNome.charAt(0).toUpperCase()}
                          </div>
                          <div>
                            <div style={{ fontWeight: 700 }}>{profNome}</div>
                            {prof.email && <div style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>{String(prof.email)}</div>}
                          </div>
                        </div>
                      </td>
                      <td>
                        <span style={{ fontWeight: 700 }}>{fechamento ? fechamento.total_aulas : aulas.length}</span>
                        <span style={{ color: "var(--text-muted)", fontSize: "0.8rem" }}> aula{aulas.length !== 1 ? "s" : ""}</span>
                      </td>
                      <td>
                        <span style={{ fontWeight: 800, fontSize: "0.9375rem", color: totalProf > 0 ? "var(--navy-900)" : "var(--text-faint)" }}>
                          {formatBRL(fechamento ? fechamento.valor_total : totalProf)}
                        </span>
                      </td>
                      <td>
                        <span className={`badge badge-${cls}`}><span className="badge-dot" />{label}</span>
                      </td>
                      <td>
                        <button className="btn btn-primary btn-sm" onClick={() => setDetalheProf(prof)}>
                          Ver detalhes
                        </button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          )}
        </div>
      </div>

      {detalheProf && (
        <DetalheProfModal
          professor={detalheProf}
          payables={payables}
          fechamento={getFechamentoAtual(detalheProf)}
          onClose={() => setDetalheProf(null)}
          onSaved={() => { carregarFechamentos(); }}
        />
      )}
    </>
  );
}
