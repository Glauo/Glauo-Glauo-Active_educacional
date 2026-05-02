import { AppShell } from "@/components/app-shell";
import { NotaRapidaForm } from "@/components/notas-form";
import { getSession } from "@/lib/auth";
import { dbList } from "@/lib/db";
import { redirect } from "next/navigation";

type Row = Record<string, unknown>;

function text(value: unknown) {
  return String(value || "").trim();
}

function numberValue(value: unknown) {
  const n = Number(value);
  return Number.isFinite(n) ? n : 0;
}

export default async function NotasPage() {
  const session = await getSession();
  if (!session) redirect("/login");
  if (session.perfil === "Aluno") redirect("/aluno");

  const [notas, alunos, desafios, frequencias] = await Promise.all([
    dbList<Row>("grades.json"),
    dbList<Row>("students.json"),
    dbList<Row>("challenges.json"),
    dbList<Row>("attendance.json")
  ]);

  const media = notas.length ? notas.reduce((s, n) => s + numberValue(n.nota), 0) / notas.length : 0;
  const faltas = frequencias.filter((f) => f.falta).length;

  return (
    <AppShell breadcrumb="Notas" userName={session.pessoa || session.usuario} userRole={session.perfil}>
      <div className="page-header">
        <div className="page-title-block">
          <div className="page-eyebrow"><span className="page-eyebrow-dot" />Modulo Pedagogico</div>
          <h1 className="page-title">Notas e Faltas</h1>
          <p className="page-description">Notas de desafios corrigidos, presencas, faltas e acompanhamento por turma.</p>
        </div>
      </div>

      <div className="metric-grid metric-grid-3">
        <div className="metric-card metric-card-blue"><div className="metric-label">Notas lancadas</div><div className="metric-value">{notas.length}</div><div className="metric-note">Correcoes registradas</div></div>
        <div className="metric-card metric-card-green"><div className="metric-label">Media geral</div><div className="metric-value">{media.toFixed(1)}</div><div className="metric-note">Baseada nas notas lancadas</div></div>
        <div className="metric-card metric-card-red"><div className="metric-label">Faltas</div><div className="metric-value">{faltas}</div><div className="metric-note">Registros de aula fechada</div></div>
      </div>

      <NotaRapidaForm alunos={alunos} desafios={desafios} />

      <div className="card" style={{ marginTop: 24 }}>
        <div className="card-header">
          <div>
            <div className="section-eyebrow">Boletim</div>
            <h3 className="section-title">Notas lancadas</h3>
            <p className="section-subtitle">{notas.length} registros</p>
          </div>
        </div>
        <div className="card-body" style={{ paddingTop: 12 }}>
          {notas.length === 0 ? (
            <div className="empty-state"><div className="empty-title">Nenhuma nota lancada</div><p className="empty-desc">Corrija um desafio para a nota aparecer aqui e no painel do aluno.</p></div>
          ) : (
            <table className="data-table">
              <thead><tr><th>Aluno</th><th>Desafio</th><th>Turma</th><th>Nota</th><th>Status</th><th>Data</th></tr></thead>
              <tbody>
                {notas.map((n, i) => (
                  <tr key={text(n.id || i)}>
                    <td style={{ fontWeight: 700 }}>{text(n.aluno)}</td>
                    <td>{text(n.titulo || n.desafio)}</td>
                    <td>{text(n.turma || "-")}</td>
                    <td><span className="badge badge-gold">{numberValue(n.nota).toFixed(1)}</span></td>
                    <td><span className="badge badge-success"><span className="badge-dot" />{text(n.status || "Corrigido")}</span></td>
                    <td>{n.data ? new Date(String(n.data)).toLocaleDateString("pt-BR") : "-"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </AppShell>
  );
}
