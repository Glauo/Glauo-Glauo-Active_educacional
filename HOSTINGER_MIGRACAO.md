# Deploy Hostinger VPS (Docker)

## Arquitetura

| Servico    | Funcao                            | Porta interna |
|------------|-----------------------------------|---------------|
| `frontend` | Next.js - interface publica Node.js | 3000          |
| `wizbot`   | Wiz webhook WhatsApp              | 8787          |
| `caddy`    | HTTPS automatico + reverse proxy  | 80 / 443      |

O Caddy e o unico servico com portas publicas. A aplicacao principal do Active Educacional roda em Node.js/Next.js.

## 1) Preparar VPS

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y docker.io docker-compose-plugin git
sudo systemctl enable --now docker
```

## 2) Clonar projeto

```bash
git clone https://github.com/Glauo/Glauo-Glauo-Active_educacional.git
cd Glauo-Glauo-Active_educacional
git checkout principal
```

## 3) Configurar variaveis de ambiente

Configure no painel do Easypanel/Hostinger ou em arquivo `.env` usado pelo compose:

| Variavel | Descricao |
|----------|-----------|
| `ACTIVE_DATABASE_URL` | Banco PostgreSQL do Active |
| `DATABASE_URL` | Mesmo banco, usado como fallback |
| `JWT_SECRET` | Segredo de sessao do Next.js |
| `GROQ_API_KEY` ou `ACTIVE_GROQ_API_KEY` | Chave da Wiz IA |
| `ACTIVE_MERCADO_PAGO_ACCESS_TOKEN` ou `MERCADO_PAGO_ACCESS_TOKEN` | Token para gerar boleto Mercado Pago |
| `WAPI_BASE_URL`, `WAPI_TOKEN`, `WAPI_INSTANCE_ID` | Envio WhatsApp |

Gerar um `JWT_SECRET` seguro:

```bash
openssl rand -base64 48
```

## 4) Subir os servicos

```bash
docker compose -f docker-compose.hostinger.yml up -d --build
docker compose -f docker-compose.hostinger.yml ps
```

Verificar logs:

```bash
docker compose -f docker-compose.hostinger.yml logs -f frontend
docker compose -f docker-compose.hostinger.yml logs -f wizbot
docker compose -f docker-compose.hostinger.yml logs -f caddy
```

## 5) Checklist de validacao

- Login admin funcionando via Next.js
- Sessao persiste apos F5
- Alunos, professores e turmas carregando
- Financeiro com recebimentos, baixas e boleto Mercado Pago
- Wiz IA corrigindo atividades
- Mural publicando para turmas cadastradas
- Webhook WhatsApp respondendo

## 6) Atualizar apos deploys futuros

```bash
git pull origin principal
docker compose -f docker-compose.hostinger.yml up -d --build
```
