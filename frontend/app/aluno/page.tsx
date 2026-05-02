import { dbList } from "@/lib/db";
import { getSession } from "@/lib/auth";
import { redirect } from "next/navigation";
import { StudentLogoutBtn } from "@/components/student-logout-btn";

type Aluno = { id?: string; nome?: string; name?: string; login?: string; turma?: string; classe?: string; livro?: string; book?: string; status?: string; [k: string]: unknown };
type Desafio = { id?: string; titulo?: string; title?: string; turma?: string; pontos?: number | string; status?: string; [k: string]: unknown };
type Conclusao = { desafio_id?: string; aluno?: string; pontos?: number | string; data?: string; [k: string]: unknown };
type Nota = { aluno?: string; aluno_login?: string; titulo?: string; desafio?: string; nota?: number | string; status?: string; data?: string; [k: string]: unknown };
type Recebimento = { id?: string; aluno?: string; nome?: string; descricao?: string; valor?: number | string; vencimento?: string; data_vencimento?: string; status?: string; [k: string]: unknown };

export default async function AlunoHomePage() {
  const session = await getSession();
  if (!session) redirect("/aluno/login");
  if (session.perfil !== "Aluno") redirect("/");

  const [alunos, desafios, conclusoes, notas, frequencias, recebimentos] = await Promise.all([
    dbList<Aluno>("students.json"),
    dbList<Desafio>("challenges.json"),
    dbList<Conclusao>("challenge_completions.json"),
    dbList<Nota>("grades.json"),
    dbList<Record<string, unknown>>("attendance.json"),
    dbList<Recebimento>("receivables.json")
  ]);

  const meuPerfil = alunos.find((a) => a.login === session.usuario);
  const minhaTurma = meuPerfil?.turma || meuPerfil?.classe || session.unit || "";

  const desafiosDisponiveis = desafios.filter((d) => {
    const s = String(d.status || "publicado").toLowerCase();
    const ehPublicado = !s.includes("rascunho") && !s.includes("arquiv");
    const turmaOk = !d.turma || d.turma === minhaTurma || d.turma === "Todas";
    return ehPublicado && turmaOk;
  });

  const minhasConclusoes = conclusoes.filter(
    (c) => c.aluno === session.usuario || c.aluno === session.pessoa
  );
  const meusPontos = minhasConclusoes.reduce((acc, c) => acc + (Number(c.pontos) || 0), 0);
  const minhasNotas = notas.filter((n) => n.aluno === session.pessoa || n.aluno_login === session.usuario);
  const minhasFaltas = frequencias.filter((f) => (f.aluno === session.pessoa || f.aluno_id === meuPerfil?.id || f.aluno_id === session.usuario) && f.falta).length;
  const minhasFaturas = recebimentos.filter((r) => String(r.aluno || r.nome || "").trim().toLowerCase() === String(session.pessoa).trim().toLowerCase());
  const debitosAbertos = minhasFaturas.filter((r) => !String(r.status || "").toLowerCase().includes("pago"));
  const totalDebitos = debitosAbertos.reduce((s, r) => s + (parseFloat(String(r.valor || "0").replace(/[^\d.,-]/g, "").replace(",", ".")) || 0), 0);

  const concluidosIds = new Set(minhasConclusoes.map((c) => c.desafio_id));

  const ranking = Object.entries(
    conclusoes.reduce((acc: Record<string, number>, c) => {
      const a = String(c.aluno || "");
      if (a) acc[a] = (acc[a] || 0) + (Number(c.pontos) || 0);
      return acc;
    }, {})
  )
    .sort((a, b) => b[1] - a[1])
    .map(([nome]) => nome);

  const minhaPos = ranking.indexOf(session.usuario) + 1 || ranking.indexOf(session.pessoa) + 1;

  return (
    <div style={{ minHeight: "100vh", background: "var(--bg-base)" }}>
      {/* Header */}
      <header style={{
        background: "linear-gradient(135deg, #0f2044 0%, #1a3a6e 100%)",
        padding: "0 32px",
        height: "64px",
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        boxShadow: "0 2px 12px rgba(0,0,0,0.18)"
      }}>
        <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
          <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
            <path d="M22 10v6M2 10l10-5 10 5-10 5z" />
            <path d="M6 12v5c3 3 9 3 12 0v-5" />
          </svg>
          <span style={{ color: "white", fontWeight: 700, fontSize: "1rem" }}>Active Educacional</span>
          <span style={{ color: "rgba(255,255,255,0.3)", margin: "0 4px" }}>/</span>
          <span style={{ color: "rgba(255,255,255,0.7)", fontSize: "0.875rem" }}>Área do Aluno</span>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: "16px" }}>
          <div style={{ textAlign: "right" }}>
            <div style={{ color: "white", fontWeight: 600, fontSize: "0.875rem" }}>{session.pessoa}</div>
            {minhaTurma && <div style={{ color: "rgba(255,255,255,0.55)", fontSize: "0.75rem" }}>{minhaTurma}</div>}
          </div>
          <StudentLogoutBtn />
        </div>
      </header>

      <main style={{ maxWidth: "960px", margin: "0 auto", padding: "32px 24px" }}>
        {/* Boas-vindas */}
        <div style={{ marginBottom: "32px" }}>
          <div style={{ fontSize: "0.8125rem", fontWeight: 600, color: "var(--blue-500)", textTransform: "uppercase", letterSpacing: "0.08em", marginBottom: "6px" }}>
            Olá, bem-vindo(a)!
          </div>
          <h1 style={{ fontSize: "1.875rem", fontWeight: 800, color: "var(--text-primary)" }}>
            {session.pessoa}
          </h1>
          {minhaTurma && (
            <p style={{ color: "var(--text-muted)", marginTop: "4px" }}>Turma: <strong>{minhaTurma}</strong></p>
          )}
        </div>

        {/* Métricas pessoais */}
        <div className="metric-grid metric-grid-3" style={{ marginBottom: "32px" }}>
          <div className="metric-card metric-card-gold">
            <div className="metric-icon metric-icon-gold">
              <svg viewBox="0 0 20 20" fill="currentColor"><path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z" /></svg>
            </div>
            <div className="metric-label">Meus pontos</div>
            <div className="metric-value">{meusPontos.toLocaleString("pt-BR")}</div>
            <div className="metric-note">Acumulados em desafios</div>
          </div>
          <div className="metric-card metric-card-green">
            <div className="metric-icon metric-icon-green">
              <svg viewBox="0 0 20 20" fill="currentColor"><path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" /></svg>
            </div>
            <div className="metric-label">Desafios concluídos</div>
            <div className="metric-value">{minhasConclusoes.length}</div>
            <div className="metric-note">De {desafiosDisponiveis.length} disponíveis</div>
          </div>
          <div className="metric-card metric-card-blue">
            <div className="metric-icon metric-icon-blue">
              <svg viewBox="0 0 20 20" fill="currentColor"><path fillRule="evenodd" d="M10 9a3 3 0 100-6 3 3 0 000 6zm-7 9a7 7 0 1114 0H3z" clipRule="evenodd" /></svg>
            </div>
            <div className="metric-label">Posição no ranking</div>
            <div className="metric-value">{minhaPos > 0 ? `#${minhaPos}` : "—"}</div>
            <div className="metric-note">Entre todos os alunos</div>
          </div>
        </div>

        <div className="card" style={{ marginBottom: "24px" }}>
          <div className="card-header">
            <div>
              <div className="section-eyebrow">Boletim</div>
              <h3 className="section-title">Minhas notas e faltas</h3>
              <p className="section-subtitle">{minhasNotas.length} notas registradas - {minhasFaltas} faltas</p>
            </div>
          </div>
          <div className="card-body" style={{ paddingTop: "12px" }}>
            {minhasNotas.length === 0 ? (
              <div className="empty-state"><div className="empty-title">Nenhuma nota publicada</div><p className="empty-desc">As notas aparecem aqui assim que o professor corrigir os desafios.</p></div>
            ) : (
              <table className="data-table">
                <thead><tr><th>Desafio</th><th>Nota</th><th>Status</th><th>Data</th></tr></thead>
                <tbody>
                  {minhasNotas.map((n, i) => (
                    <tr key={String(n.id || i)}>
                      <td style={{ fontWeight: 600 }}>{String(n.titulo || n.desafio || "-")}</td>
                      <td><span className="badge badge-gold">{Number(n.nota || 0).toFixed(1)}</span></td>
                      <td><span className="badge badge-success"><span className="badge-dot" />{String(n.status || "Corrigido")}</span></td>
                      <td>{n.data ? new Date(String(n.data)).toLocaleDateString("pt-BR") : "-"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </div>

        <div className="card" style={{ marginBottom: "24px" }}>
          <div className="card-header">
            <div>
              <div className="section-eyebrow">Financeiro</div>
              <h3 className="section-title">Debitos, faturas e boletos</h3>
              <p className="section-subtitle">Voce pode consultar faturas e baixar boletos. Alteracoes financeiras sao restritas a administracao.</p>
            </div>
            <span className="badge badge-warning"><span className="badge-dot" />{totalDebitos.toLocaleString("pt-BR", { style: "currency", currency: "BRL" })} em aberto</span>
          </div>
          <div className="card-body" style={{ paddingTop: "12px" }}>
            {minhasFaturas.length === 0 ? (
              <div className="empty-state"><div className="empty-title">Nenhuma fatura encontrada</div><p className="empty-desc">Quando houver boleto ou mensalidade, ela aparecera aqui.</p></div>
            ) : (
              <table className="data-table">
                <thead><tr><th>Fatura</th><th>Vencimento</th><th>Valor</th><th>Status</th><th>Boleto</th></tr></thead>
                <tbody>
                  {minhasFaturas.map((f, i) => {
                    const pago = String(f.status || "").toLowerCase().includes("pago");
                    return (
                      <tr key={String(f.id || i)}>
                        <td style={{ fontWeight: 600 }}>{String(f.descricao || "Mensalidade")}</td>
                        <td>{String(f.vencimento || f.data_vencimento || "-")}</td>
                        <td>{(parseFloat(String(f.valor || "0").replace(/[^\d.,-]/g, "").replace(",", ".")) || 0).toLocaleString("pt-BR", { style: "currency", currency: "BRL" })}</td>
                        <td><span className={`badge badge-${pago ? "success" : "warning"}`}><span className="badge-dot" />{String(f.status || "Pendente")}</span></td>
                        <td><a className="btn btn-secondary btn-sm" href={`/api/financeiro/boleto?id=${String(f.id)}`} target="_blank" rel="noreferrer">Baixar boleto</a></td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            )}
          </div>
        </div>

        {/* Desafios disponíveis */}
        <div className="card">
          <div className="card-header">
            <div>
              <div className="section-eyebrow">Pedagógico</div>
              <h3 className="section-title">Desafios disponíveis</h3>
              <p className="section-subtitle">{desafiosDisponiveis.length} desafios para a sua turma</p>
            </div>
          </div>
          <div className="card-body" style={{ paddingTop: "12px" }}>
            {desafiosDisponiveis.length === 0 ? (
              <div className="empty-state">
                <div className="empty-icon">
                  <svg viewBox="0 0 20 20" fill="currentColor"><path d="M9 2a1 1 0 000 2h2a1 1 0 100-2H9z" /><path fillRule="evenodd" d="M4 5a2 2 0 012-2 3 3 0 003 3h2a3 3 0 003-3 2 2 0 012 2v11a2 2 0 01-2 2H6a2 2 0 01-2-2V5z" clipRule="evenodd" /></svg>
                </div>
                <div className="empty-title">Nenhum desafio disponível</div>
                <p className="empty-desc">Seu professor publicará os desafios em breve.</p>
              </div>
            ) : (
              <table className="data-table">
                <thead>
                  <tr><th>Desafio</th><th>Pontos</th><th>Status</th></tr>
                </thead>
                <tbody>
                  {desafiosDisponiveis.map((d, i) => {
                    const titulo = String(d.titulo || d.title || `Desafio ${i + 1}`);
                    const pontos = Number(d.pontos) || 0;
                    const concluido = concluidosIds.has(d.id || titulo);
                    return (
                      <tr key={String(d.id || i)}>
                        <td style={{ fontWeight: 600 }}>{titulo}</td>
                        <td><span className="badge badge-gold">{pontos} pts</span></td>
                        <td>
                          <span className={`badge badge-${concluido ? "success" : "neutral"}`}>
                            <span className="badge-dot" />
                            {concluido ? "Concluído" : "Pendente"}
                          </span>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            )}
          </div>
        </div>

        {/* Informações do perfil */}
        {meuPerfil && (
          <div className="card" style={{ marginTop: "24px" }}>
            <div className="card-header">
              <div>
                <div className="section-eyebrow">Meu perfil</div>
                <h3 className="section-title">Informações cadastradas</h3>
              </div>
            </div>
            <div className="card-body">
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "16px" }}>
                {[
                  { label: "Nome", value: String(meuPerfil.nome || meuPerfil.name || "—") },
                  { label: "Turma", value: String(meuPerfil.turma || meuPerfil.classe || "—") },
                  { label: "Livro", value: String(meuPerfil.livro || meuPerfil.book || "—") },
                  { label: "Login", value: String(meuPerfil.login || "—") }
                ].map(({ label, value }) => (
                  <div key={label}>
                    <div style={{ fontSize: "0.75rem", fontWeight: 600, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.06em", marginBottom: "4px" }}>{label}</div>
                    <div style={{ fontWeight: 600, color: "var(--text-primary)" }}>{value}</div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
