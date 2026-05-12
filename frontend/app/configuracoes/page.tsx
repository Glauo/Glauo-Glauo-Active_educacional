import { AppShell } from "@/components/app-shell";
import { ConfiguracoesForm } from "@/components/configuracoes-form";
import { dbGet } from "@/lib/db";
import { getSession } from "@/lib/auth";
import { redirect } from "next/navigation";

type SistemaConfig = { nome_escola?: string; cnpj?: string; telefone?: string; email_contato?: string; endereco?: string; cidade?: string; estado?: string; cep?: string; [k: string]: unknown };
type SmtpConfig = { host?: string; port?: number | string; user?: string; from_name?: string; enabled?: boolean; [k: string]: unknown };
type BoletoConfig = { banco?: string; agencia?: string; conta?: string; cedente?: string; carteira?: string; instrucoes?: string; dias_vencimento?: number | string; [k: string]: unknown };

export default async function ConfiguracoesPage() {
  const session = await getSession();
  if (!session) redirect("/login");

  const [sistema, smtp, boleto] = await Promise.all([
    dbGet<SistemaConfig>("sistema_config.json"),
    dbGet<SmtpConfig>("smtp_config.json"),
    dbGet<BoletoConfig>("boleto_config.json"),
  ]);

  return (
    <AppShell breadcrumb="Configurações" userName={session.pessoa || session.usuario} userRole={session.perfil}>
      <ConfiguracoesForm
        sistema={sistema || {}}
        smtp={smtp || {}}
        boleto={boleto || {}}
      />
    </AppShell>
  );
}
