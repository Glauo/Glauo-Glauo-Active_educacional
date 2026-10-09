# Frontend Next.js

## Validacao de financeiro e usuarios

Execute nesta pasta: `npm test`, `npm run lint` e `npm run build`.
Os testes usam banco/API simulados: nao criam boletos, nao baixam parcelas reais e nao enviam mensagens.
Depois do build, `node scripts/users-ui-smoke.cjs` valida a tela de usuarios em 1366px e 390px com dados ficticios. Requer Chrome (ou `CHROME_PATH`) e porta local 4317 livre. Capturas ficam somente em `.next/`, fora do Git.

### Mercado Pago

- Webhook: `/api/financeiro/mercado-pago/webhook`; configure notificacoes de pagamentos na aplicacao Mercado Pago.
- Use `ACTIVE_MERCADO_PAGO_ACCESS_TOKEN` (ou os aliases existentes) e `ACTIVE_MERCADO_PAGO_WEBHOOK_SECRET`.
- Configure a chave secreta gerada em Mercado Pago > Sua integracao > Webhooks no ambiente ou nas configuracoes de boleto. Sem a chave, o webhook falha fechado com HTTP 503; assinatura invalida retorna HTTP 401. Payload e query devem indicar o mesmo pagamento.
- A baixa consulta `/v1/payments/{id}`. IDs/external_reference/metadata devem apontar para uma unica parcela; CPF, nome ou valor isolados nao autorizam baixa.
- Parcela, recibo e auditoria sao gravados na mesma transacao PostgreSQL em `active_kv`, sem criar tabelas ou apagar dados. Notificacoes repetidas nao criam outro recibo.
- O botao existente **Verificar pagamento** usa a mesma rotina e confere o ID da parcela solicitada.
- O servico `wizbot` confere pagamentos pendentes a cada cinco minutos por `POST /api/financeiro/cron-pagamentos`, autenticado no header `x-cron-secret`; mantenha o mesmo `CRON_SECRET` aleatorio, exclusivo e com no minimo 32 caracteres no frontend e no `wizbot`. O Compose falha se essa variavel nao estiver configurada. Essa rotina apenas consulta pagamentos existentes e nao gera boletos.
- A geracao informa vencimento tecnico no limite de 30 dias aceito pela API de boleto; o vencimento financeiro escolar continua separado e e preservado na parcela. O prazo do banco nao e ilimitado: boleto vencido pode ser recusado/estornado, entao uma segunda via deve ser emitida com encargos atualizados.
- Referencias oficiais: [webhooks](https://www.mercadopago.com.br/developers/pt/docs/links-and-debts/additional-content/your-integrations/notifications/webhooks) e [vencimento de boletos](https://www.mercadopago.com.br/developers/pt/docs/checkout-api-payments/integration-configuration/other-payment-methods?scope=prod).

### Usuarios e senhas

- `/usuarios/credenciais` lista usuarios internos (incluindo coordenadores), professores e alunos. Edicao, desativacao e redefinicao sao exclusivas do ADM no backend.
- O ultimo administrador ativo nao pode ser desativado, excluido ou rebaixado; a verificacao ocorre na transacao.
- Senhas redefinidas sao armazenadas com scrypt e salt aleatorio. A senha temporaria aparece somente na resposta ao ADM; mensagens enviam instrucoes, nao a senha.
- O primeiro login com senha temporaria encaminha para `/alterar-senha`. Sessao antiga e invalidada apos redefinicao; contas inativas ou perfis alterados sao reavaliados no backend sem cache de autorizacao.
- Credenciais antigas continuam aceitas por compatibilidade; isso nao equivale a uma migracao completa de todas as senhas legadas.
- Producao exige `JWT_SECRET` com pelo menos 32 caracteres. Preserve o segredo existente se adequado; mudar esse valor invalida sessoes.

### Antes de publicar

Confirme backup do banco, segredo JWT, token/segredo webhook da mesma aplicacao Mercado Pago e acesso HTTPS publico ao endpoint. Valide uma cobranca conhecida sem gerar pagamento ou baixa manual ficticia. Testes locais nao comprovam entrega real do webhook, email/WhatsApp, nem substituem validacao visual autenticada em producao.

### Arquivos envolvidos nesta correcao

- Financeiro: `lib/mercadopago-sync.ts`, `lib/db.ts`, `lib/student-payment-automation.ts`, `app/api/financeiro/mercado-pago/webhook/route.ts`, `app/api/financeiro/verificar-pagamento/route.ts`.
- Gestao ADM: `lib/user-management.ts`, `app/api/usuarios/gestao/route.ts`, `app/api/usuarios/credenciais/route.ts`, `app/usuarios/credenciais/page.tsx`, `lib/access-control.ts`, `components/app-shell.tsx`.
- Autenticacao: `lib/auth.ts`, `lib/passwords.ts`, `lib/jwt-config.ts`, `lib/student-credentials.ts`, `middleware.ts`, `app/api/auth/route.ts`, `app/api/auth/aluno/route.ts`, `app/api/auth/alterar-senha/route.ts`, `app/alterar-senha/page.tsx`.
- Layout, comandos e validacao: `app/globals.css`, `package.json`, `scripts/financial-users.test.cjs`, `scripts/load-test-module.cjs`, `scripts/users-ui-smoke.cjs`, este `README.md`.

Base inicial da migracao do Active Educacional para `Next.js`.

## Objetivo desta pasta
- criar a nova camada visual sem desligar o sistema atual
- preparar o shell do sistema
- migrar os modulos por etapas

## Nesta etapa
- estrutura inicial do `Next.js`
- layout base
- pagina inicial da migracao

## Proximo passo
- criar shell autenticado
- montar sidebar e header reutilizaveis
- abrir rotas iniciais:
  - `/dashboard`
  - `/alunos`
  - `/professores`
  - `/turmas`
  - `/agenda`
  - `/financeiro`
