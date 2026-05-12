import { AppShell } from "@/components/app-shell";
import { NotaRapidaForm } from "@/components/notas-form";
import { NotasClient } from "@/components/notas-client";
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

      <NotasClient notas={notas} frequencias={frequencias} />
    </AppShell>
  );
}
