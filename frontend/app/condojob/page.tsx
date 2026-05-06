import { BookOpen, FileCheck2, GraduationCap, Trophy, Users, WalletCards } from "lucide-react";
import { AppShell } from "@/components/app-shell";
import { getSession } from "@/lib/auth";
import { redirect } from "next/navigation";

const modulos = [
  {
    icon: BookOpen,
    titulo: "Cursos",
    descricao: "Criacao e gestao de cursos com aulas, carga horaria, nota minima e controle de matriculas.",
    itens: ["Nome e descricao do curso", "Carga horaria", "Nota minima para certificado", "Preco ou gratuito"]
  },
  {
    icon: Users,
    titulo: "Alunos",
    descricao: "Cadastro, matricula e acompanhamento de alunos por curso com historico de progresso.",
    itens: ["Matricula por curso", "Progresso de aulas", "Status de conclusao", "Historico de acesso"]
  },
  {
    icon: FileCheck2,
    titulo: "Atividades",
    descricao: "Envio de atividades pelos alunos e correcao pela coordenacao com nota e feedback.",
    itens: ["Submissao de atividade", "Aguardando correcao", "Nota e feedback", "Status de aprovacao"]
  },
  {
    icon: Trophy,
    titulo: "Certificados",
    descricao: "Emissao automatica de certificados ao concluir curso com nota acima do minimo exigido.",
    itens: ["Conclusao do curso", "Nota acima do minimo", "Emissao automatica", "Download disponivel"]
  },
  {
    icon: WalletCards,
    titulo: "Financeiro",
    descricao: "Controle de pagamentos vinculados a matriculas, com status e historico por aluno.",
    itens: ["Pagamentos por aluno", "Status de matricula", "Historico financeiro", "Relatorio de receita"]
  },
  {
    icon: GraduationCap,
    titulo: "Documentos",
    descricao: "Upload e gestao de documentos por aluno, com visualizacao e download pela coordenacao.",
    itens: ["Upload de documento", "Tipo e descricao", "Visualizacao pelo aluno", "Gestao pela coordenacao"]
  }
];

const fluxo = [
  "Coordenacao cria o curso com aulas, carga horaria e nota minima.",
  "Aluno e matriculado no curso e recebe acesso ao conteudo.",
  "Aluno assiste aulas e submete atividades para correcao.",
  "Coordenacao corrige e registra nota e feedback.",
  "Ao concluir com nota suficiente, certificado e emitido automaticamente.",
  "Aluno acessa certificado, documentos e historico financeiro no painel."
];

function canAccess(perfil: string) {
  const role = perfil.toLowerCase();
  return role.includes("admin") || role.includes("coord") || role.includes("dire") || role.includes("comercial");
}

export default async function CondoJobPage() {
  const session = await getSession();
  if (!session) redirect("/login");
  if (!canAccess(session.perfil)) redirect("/");

  const userName = session.pessoa || session.usuario;

  return (
    <AppShell breadcrumb="CondoJob" userName={userName} userRole={session.perfil}>
      <div className="page-header">
        <div className="page-title-block">
          <div className="page-eyebrow"><span className="page-eyebrow-dot" />EAD</div>
          <h1 className="page-title">CondoJob Educacao</h1>
          <p className="page-description">
            Plataforma EAD com cursos, aulas, atividades, certificados, financeiro e documentos por aluno.
          </p>
        </div>
        <div className="page-actions">
          <span className="badge badge-success"><span className="badge-dot" />{modulos.length} modulos ativos</span>
        </div>
      </div>

      <section className="metric-grid">
        {modulos.map((m) => {
          const Icon = m.icon;
          return (
            <div className="metric" key={m.titulo}>
              <div className="metric-icon"><Icon size={19} /></div>
              <strong>{m.titulo}</strong>
              <span className="muted">Modulo ativo</span>
            </div>
          );
        })}
      </section>

      <div className="split-grid">
        <section className="panel education-panel">
          <div className="section-header">
            <div>
              <h2>Fluxo do aluno</h2>
              <p className="muted">Do cadastro ao certificado — passo a passo da plataforma.</p>
            </div>
          </div>
          <div className="education-list">
            {fluxo.map((item) => (
              <article className="education-item" key={item}>
                <strong>{item}</strong>
              </article>
            ))}
          </div>
        </section>

        <section className="panel education-panel">
          <div className="section-header">
            <div>
              <h2>Perfis de acesso</h2>
              <p className="muted">Quem acessa e o que cada perfil pode fazer na plataforma.</p>
            </div>
          </div>
          <div className="education-card-grid single">
            <article className="education-card">
              <h3>Coordenador</h3>
              <p>Cria cursos e aulas, matricula alunos, corrige atividades, emite relatorios e gerencia financeiro e documentos.</p>
            </article>
            <article className="education-card">
              <h3>Aluno</h3>
              <p>Acessa cursos matriculados, assiste aulas, submete atividades, baixa certificados, consulta financeiro e envia documentos.</p>
            </article>
          </div>
        </section>
      </div>

      <section className="panel education-panel education-full">
        <div className="section-header">
          <div>
            <h2>Modulos da plataforma</h2>
            <p className="muted">Visao completa de cada area disponivel no CondoJob EAD.</p>
          </div>
        </div>
        <div className="education-card-grid">
          {modulos.map((m) => {
            const Icon = m.icon;
            return (
              <article className="education-card" key={m.titulo}>
                <span className="status-pill">Modulo ativo</span>
                <h3 style={{ display: "flex", alignItems: "center", gap: 8 }}>
                  <Icon size={16} />{m.titulo}
                </h3>
                <p>{m.descricao}</p>
                <div className="tag-row">
                  {m.itens.map((item) => <span key={item}>{item}</span>)}
                </div>
              </article>
            );
          })}
        </div>
      </section>
    </AppShell>
  );
}
