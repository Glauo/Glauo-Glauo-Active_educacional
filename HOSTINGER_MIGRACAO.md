# Deploy — Hostinger VPS (Docker)

## Arquitetura

| Serviço    | Função                               | Porta interna |
|------------|--------------------------------------|---------------|
| `frontend` | Next.js — interface pública          | 3000          |
| `app`      | Streamlit / Wiz backend (automações) | 8501 (interno)|
| `wizbot`   | Wiz webhook WhatsApp                 | 8787          |
| `caddy`    | HTTPS automático + reverse proxy     | 80 / 443      |

O Caddy é o único serviço com portas públicas. O Streamlit não é acessível pelo navegador — serve apenas como backend para automações internas.

---

## 1) Preparar VPS

Execute no terminal do VPS (Ubuntu 22.04+):

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

## 3) Configurar variáveis de ambiente

```bash
cp deploy/hostinger/.env.example deploy/hostinger/.env
nano deploy/hostinger/.env
```

**Obrigatórios** (sem estes o sistema não sobe corretamente):

| Variável             | Exemplo                                    | Descrição                           |
|----------------------|--------------------------------------------|-------------------------------------|
| `DOMAIN`             | `app.seudominio.com`                       | Domínio/subdomínio final            |
| `ACME_EMAIL`         | `admin@seudominio.com`                     | E-mail para certificado SSL         |
| `ACTIVE_DATABASE_URL`| `postgresql://user:pass@host:5432/dbname`  | Banco PostgreSQL externo            |
| `JWT_SECRET`         | string longa e aleatória                   | Autenticação Next.js (sessões)      |

Gerar um `JWT_SECRET` seguro:
```bash
openssl rand -base64 48
```

**Opcionais** (WhatsApp / IA):
- `GROQ_API_KEY`, `ACTIVE_WIZ_MODEL`, etc. — veja `.env.example`

## 4) Apontar DNS

No painel DNS do domínio, crie um registro:
- Tipo `A`, nome `@` (ou subdomínio como `app`), valor = **IP público do VPS**

Aguarde propagação (geralmente 5–15 minutos na Hostinger).

## 5) Subir os serviços

```bash
docker compose -f docker-compose.hostinger.yml up -d --build
docker compose -f docker-compose.hostinger.yml ps
```

Verificar status e logs:
```bash
# Status geral
docker compose -f docker-compose.hostinger.yml ps

# Logs do Next.js
docker compose -f docker-compose.hostinger.yml logs -f frontend

# Logs do Caddy (HTTPS/SSL)
docker compose -f docker-compose.hostinger.yml logs -f caddy

# Logs do Streamlit/backend
docker compose -f docker-compose.hostinger.yml logs -f app

# Logs do Wiz webhook
docker compose -f docker-compose.hostinger.yml logs -f wizbot
```

## 6) Migrar dados existentes

O banco PostgreSQL é compartilhado — tabela `active_kv`. Se o banco já tem dados do Streamlit, o Next.js os lê automaticamente (mesma chave, mesmo formato).

Se estiver migrando de arquivos locais:
1. Acesse o sistema Streamlit atual
2. Gere backup em **Backup > Exportar backup**
3. Restaure no novo ambiente em **Backup > Restaurar backup**

## 7) Checklist de validação

**Autenticação:**
- [ ] Login admin funcionando via Next.js
- [ ] Sessão persiste após F5 (cookie `ae_session`)
- [ ] Logout redireciona para `/login`

**Dados:**
- [ ] Quantidade de alunos/professores/turmas correta
- [ ] Dados financeiros (recebimentos e pagamentos) carregando
- [ ] Estoque com itens e saldo correto
- [ ] Biblioteca com livros e vídeos listados
- [ ] Desafios listados e criáveis (manual e IA)
- [ ] Agenda com eventos carregando

**CRUD:**
- [ ] Criar novo aluno, editar, excluir
- [ ] Criar nova turma, editar, excluir
- [ ] Criar novo professor, editar, excluir
- [ ] Lançar entrada de estoque, excluir item
- [ ] Adicionar livro/vídeo, excluir livro

**Infra:**
- [ ] HTTPS ativo (cadeado verde no navegador)
- [ ] Webhook WhatsApp respondendo em `/wapi/webhook`
- [ ] Health check Wiz em `/health/wiz`

## 8) Atualizar após deploys futuros

```bash
git pull origin principal
docker compose -f docker-compose.hostinger.yml up -d --build
```

Reiniciar sem rebuild:
```bash
docker compose -f docker-compose.hostinger.yml restart
```

Parar tudo:
```bash
docker compose -f docker-compose.hostinger.yml down
```

Limpar imagens antigas (liberar espaço):
```bash
docker image prune -f
```
