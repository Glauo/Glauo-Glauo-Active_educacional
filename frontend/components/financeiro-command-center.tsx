"use client";

import { useMemo, useState } from "react";
import { useRouter } from "next/navigation";

type Row = Record<string, unknown>;

function text(value: unknown) {
  return String(value || "").trim();
}

function parseValor(v: unknown): number {
  return parseFloat(String(v || "0").replace(/[^\d.,-]/g, "").replace(",", ".")) || 0;
}

function formatBRL(v: number): string {
  return v.toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
}

function isPaid(row: Row) {
  const s = text(row.status || row.situacao).toLowerCase();
  return s.includes("pago") || s.includes("baixado") || s.includes("liquidado");
}

function dateOf(row: Row) {
  const raw = text(row.vencimento || row.data_vencimento || row.data_pagamento || row.data_baixa);
  if (!raw) return null;
  const date = new Date(raw);
  return Number.isNaN(date.getTime()) ? null : date;
}

function daysLate(row: Row) {
  const d = dateOf(row);
  if (!d || isPaid(row)) return 0;
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  d.setHours(0, 0, 0, 0);
  return Math.max(0, Math.floor((today.getTime() - d.getTime()) / 86400000));
}

function ResultPill({ label, value, tone }: { label: string; value: string; tone: "green" | "gold" | "red" | "blue" }) {
  const color = tone === "green" ? "var(--green-700)" : tone === "gold" ? "var(--gold-700)" : tone === "red" ? "var(--red-700)" : "var(--blue-600)";
  return (
    <div style={{ padding: "10px 12px", border: "1px solid var(--border)", borderRadius: "var(--radius-md)", background: "var(--surface-raised)" }}>
      <div style={{ fontSize: "0.72rem", color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.08em", fontWeight: 700 }}>{label}</div>
      <div style={{ color, fontWeight: 800, marginTop: 2 }}>{value}</div>
    </div>
  );
}

function BatchBoletosButton() {
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const [competencia, setCompetencia] = useState(new Date().toISOString().slice(0, 7));
  const [valor, setValor] = useState("");
  const [dia, setDia] = useState("10");
  const [msg, setMsg] = useState("");
  const [saving, setSaving] = useState(false);

  async function gerar() {
    setSaving(true);
    const res = await fetch("/api/financeiro/lote", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ competencia, valor_padrao: valor, dia_vencimento: dia }),
    });
    const data = await res.json().catch(() => ({}));
    setSaving(false);
    if (!res.ok) {
      setMsg(text(data.error) || "Erro ao gerar boletos.");
      return;
    }
    setMsg(`${data.criados || 0} boleto(s) gerados. ${data.ignorados || 0} ignorado(s).`);
    router.refresh();
  }

  return (
    <>
      <button className="btn btn-secondary" onClick={() => setOpen(true)}>
        <svg viewBox="0 0 20 20" fill="currentColor"><path d="M4 3a2 2 0 00-2 2v1h16V5a2 2 0 00-2-2H4z" /><path fillRule="evenodd" d="M18 8H2v7a2 2 0 002 2h12a2 2 0 002-2V8zM5 12a1 1 0 011-1h4a1 1 0 110 2H6a1 1 0 01-1-1z" clipRule="evenodd" /></svg>
        Gerar mes
      </button>
      {open && (
        <div className="modal-overlay" onClick={(event) => event.target === event.currentTarget && setOpen(false)}>
          <div className="modal-box" style={{ maxWidth: 520 }}>
            <div className="modal-header">
              <div>
                <div className="modal-title">Gerar boletos do mes</div>
                <div className="modal-subtitle">Cria mensalidades para alunos ativos e evita duplicidade na competencia.</div>
              </div>
              <button className="modal-close" onClick={() => setOpen(false)}>
                <svg viewBox="0 0 20 20" fill="currentColor"><path fillRule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clipRule="evenodd" /></svg>
              </button>
            </div>
            <div className="modal-body">
              <div className="form-grid">
                <div className="form-group"><label className="form-label">Competencia</label><input className="form-input" type="month" value={competencia} onChange={(e) => setCompetencia(e.target.value)} /></div>
                <div className="form-group"><label className="form-label">Dia de vencimento</label><input className="form-input" type="number" min={1} max={28} value={dia} onChange={(e) => setDia(e.target.value)} /></div>
                <div className="form-group form-group-span2"><label className="form-label">Valor padrao, se o aluno nao tiver mensalidade cadastrada</label><input className="form-input" inputMode="decimal" value={valor} onChange={(e) => setValor(e.target.value)} placeholder="Ex: 350,00" /></div>
              </div>
              {msg && <div className={msg.includes("Erro") ? "form-error" : "form-success"}>{msg}</div>}
            </div>
            <div className="modal-footer">
              <button className="btn btn-secondary" onClick={() => setOpen(false)} disabled={saving}>Fechar</button>
              <button className="btn btn-primary" onClick={gerar} disabled={saving}>{saving ? "Gerando..." : "Gerar boletos"}</button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}

export function FinanceiroCommandCenter({
  recebimentos,
  despesas,
  alunos,
  professores,
}: {
  recebimentos: Row[];
  despesas: Row[];
  alunos: Row[];
  professores: Row[];
}) {
  const [busca, setBusca] = useState("");
  const now = new Date();
  const month = now.getMonth();
  const year = now.getFullYear();

  const stats = useMemo(() => {
    let receitaMes = 0;
    let receitaMesAnterior = 0;
    let futuro = 0;
    let vencido = 0;
    let vencemHoje = 0;
    const inadimplentes = new Map<string, { aluno: string; total: number; maxDias: number; count: number }>();

    for (const row of recebimentos) {
      const value = parseValor(row.valor_pago || row.valor);
      const paid = isPaid(row);
      const due = dateOf(row);
      if (paid) {
        const paidDate = new Date(text(row.data_baixa || row.updated_at || row.created_at || row.vencimento || ""));
        if (!Number.isNaN(paidDate.getTime()) && paidDate.getMonth() === month && paidDate.getFullYear() === year) receitaMes += value;
        const previous = new Date(year, month - 1, 1);
        if (!Number.isNaN(paidDate.getTime()) && paidDate.getMonth() === previous.getMonth() && paidDate.getFullYear() === previous.getFullYear()) receitaMesAnterior += value;
        continue;
      }
      if (!due) {
        futuro += value;
        continue;
      }
      const today = new Date();
      today.setHours(0, 0, 0, 0);
      due.setHours(0, 0, 0, 0);
      if (due.getTime() === today.getTime()) vencemHoje += 1;
      if (due < today) {
        const dias = daysLate(row);
        vencido += value;
        const aluno = text(row.aluno || row.nome || "Nao identificado");
        const current = inadimplentes.get(aluno) || { aluno, total: 0, maxDias: 0, count: 0 };
        inadimplentes.set(aluno, { aluno, total: current.total + value, maxDias: Math.max(current.maxDias, dias), count: current.count + 1 });
      } else {
        futuro += value;
      }
    }

    const folhaPendente = despesas
      .filter((row) => !isPaid(row))
      .filter((row) => [row.aluno, row.nome, row.descricao, row.tipo].map((v) => text(v).toLowerCase()).join(" ").includes("prof"))
      .reduce((sum, row) => sum + parseValor(row.valor), 0);

    return {
      receitaMes,
      receitaMesAnterior,
      futuro,
      vencido,
      vencemHoje,
      folhaPendente,
      inadimplentes: Array.from(inadimplentes.values()).sort((a, b) => b.total - a.total),
    };
  }, [recebimentos, despesas, month, year]);

  const results = useMemo(() => {
    const q = busca.trim().toLowerCase();
    if (!q) return [];
    const found = [
      ...recebimentos.map((row) => ({ tipo: "Boleto", titulo: text(row.aluno || row.nome || row.descricao), detalhe: `${text(row.descricao)} | ${formatBRL(parseValor(row.valor))} | ${text(row.status || "Pendente")}` })),
      ...despesas.map((row) => ({ tipo: "Despesa", titulo: text(row.aluno || row.nome || row.descricao), detalhe: `${text(row.descricao)} | ${formatBRL(parseValor(row.valor))}` })),
      ...alunos.map((row) => ({ tipo: "Aluno", titulo: text(row.nome || row.name || row.login), detalhe: `${text(row.turma || row.classe)} | ${text(row.responsavel || "")}` })),
      ...professores.map((row) => ({ tipo: "Professor", titulo: text(row.nome || row.name || row.login), detalhe: `${text(row.disciplina || row.email || "")}` })),
    ];
    return found.filter((item) => `${item.tipo} ${item.titulo} ${item.detalhe}`.toLowerCase().includes(q)).slice(0, 8);
  }, [busca, recebimentos, despesas, alunos, professores]);

  const crescimento = stats.receitaMesAnterior ? ((stats.receitaMes - stats.receitaMesAnterior) / stats.receitaMesAnterior) * 100 : 0;

  return (
    <div style={{ display: "grid", gap: 18 }}>
      <div className="card card-hero">
        <div className="card-body">
          <div style={{ display: "grid", gridTemplateColumns: "minmax(260px, 1fr) auto", gap: 16, alignItems: "start" }}>
            <div>
              <div className="section-eyebrow">Centro de comando financeiro</div>
              <h3 className="section-title" style={{ fontSize: "1.35rem", marginBottom: 8 }}>Tudo em ate 3 cliques</h3>
              <div className="search-bar" style={{ width: "100%", maxWidth: 620 }}>
                <span className="search-icon"><svg viewBox="0 0 20 20" fill="currentColor"><path fillRule="evenodd" d="M8 4a4 4 0 100 8 4 4 0 000-8zM2 8a6 6 0 1110.89 3.476l4.817 4.817a1 1 0 01-1.414 1.414l-4.816-4.816A6 6 0 012 8z" clipRule="evenodd" /></svg></span>
                <input className="search-input" value={busca} onChange={(e) => setBusca(e.target.value)} placeholder="Buscar aluno, boleto, professor, turma, CPF ou descricao..." style={{ minWidth: 260 }} />
              </div>
              {results.length > 0 && (
                <div style={{ display: "grid", gap: 8, marginTop: 12 }}>
                  {results.map((item, index) => (
                    <div className="spotlight-row" key={`${item.tipo}_${index}`}>
                      <span className="badge badge-info"><span className="badge-dot" />{item.tipo}</span>
                      <span className="spotlight-label">{item.titulo}</span>
                      <span className="spotlight-value" style={{ fontSize: "0.78rem" }}>{item.detalhe}</span>
                    </div>
                  ))}
                </div>
              )}
            </div>
            <div style={{ display: "flex", gap: 8, flexWrap: "wrap", justifyContent: "flex-end" }}>
              <BatchBoletosButton />
              <button className="btn btn-secondary" onClick={() => window.print()}>Relatorio rapido</button>
            </div>
          </div>
        </div>
      </div>

      <div className="metric-grid metric-grid-4">
        <div className="metric-card metric-card-green"><div className="metric-label">Receita do mes</div><div className="metric-value" style={{ fontSize: "1.45rem" }}>{formatBRL(stats.receitaMes)}</div><div className="metric-note">{crescimento >= 0 ? "+" : ""}{crescimento.toFixed(1)}% vs mes anterior</div></div>
        <div className="metric-card metric-card-gold"><div className="metric-label">A receber futuro</div><div className="metric-value" style={{ fontSize: "1.45rem" }}>{formatBRL(stats.futuro)}</div><div className="metric-note">Boletos em aberto nao vencidos</div></div>
        <div className="metric-card metric-card-red"><div className="metric-label">Inadimplencia</div><div className="metric-value" style={{ fontSize: "1.45rem" }}>{formatBRL(stats.vencido)}</div><div className="metric-note">{stats.inadimplentes.length} aluno(s) com atraso</div></div>
        <div className="metric-card metric-card-blue"><div className="metric-label">Folha pendente</div><div className="metric-value" style={{ fontSize: "1.45rem" }}>{formatBRL(stats.folhaPendente)}</div><div className="metric-note">Professores/fornecedores</div></div>
      </div>

      <div className="content-grid grid-2-1">
        <div className="card">
          <div className="card-header">
            <div>
              <div className="section-eyebrow">Alertas automaticos</div>
              <h3 className="section-title">Prioridade de hoje</h3>
            </div>
          </div>
          <div className="card-body">
            <div className="spotlight-list">
              <div className="spotlight-row"><span className="spotlight-label">Boletos vencendo hoje</span><span className="spotlight-value">{stats.vencemHoje}</span></div>
              <div className="spotlight-row"><span className="spotlight-label">Alunos com 2+ mensalidades em atraso</span><span className="spotlight-value">{stats.inadimplentes.filter((item) => item.count >= 2).length}</span></div>
              <div className="spotlight-row"><span className="spotlight-label">Maior atraso</span><span className="spotlight-value">{Math.max(0, ...stats.inadimplentes.map((item) => item.maxDias))} dias</span></div>
            </div>
          </div>
        </div>
        <div className="card">
          <div className="card-body">
            <div className="section-eyebrow">Inadimplencia por faixa</div>
            <div style={{ display: "grid", gap: 8, marginTop: 12 }}>
              <ResultPill label="1-30 dias" value={String(stats.inadimplentes.filter((item) => item.maxDias <= 30).length)} tone="gold" />
              <ResultPill label="31-60 dias" value={String(stats.inadimplentes.filter((item) => item.maxDias > 30 && item.maxDias <= 60).length)} tone="red" />
              <ResultPill label="+60 dias" value={String(stats.inadimplentes.filter((item) => item.maxDias > 60).length)} tone="red" />
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
