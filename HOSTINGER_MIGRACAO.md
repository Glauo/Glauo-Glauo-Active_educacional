# Migracao para Hostinger (VPS + Docker)

## 1) Preparar VPS
Execute no terminal do VPS (Ubuntu):

```bash
sudo apt update
sudo apt install -y docker.io docker-compose-plugin git
sudo systemctl enable docker
sudo systemctl start docker
```

## 2) Clonar projeto
```bash
git clone https://github.com/Glauo/Glauo-Glauo-Active_educacional.git
cd Glauo-Glauo-Active_educacional
git checkout principal
```

## 3) Configurar variaveis
```bash
cp deploy/hostinger/.env.example deploy/hostinger/.env
nano deploy/hostinger/.env
```

Ajuste pelo menos:
- `DOMAIN` (dominio/subdominio final)
- `ACME_EMAIL`

Se quiser banco Postgres externo, configure `ACTIVE_DATABASE_URL`.
Se nao configurar, o sistema roda com persistencia em arquivo local em `./data` (com volume Docker).

## 4) Apontar DNS
No painel DNS do seu dominio, crie:
- `A` para `@` (ou subdominio) apontando para o IP do VPS.

## 5) Subir aplicacao
```bash
docker compose -f docker-compose.hostinger.yml up -d --build
docker compose -f docker-compose.hostinger.yml ps
```

Ver logs:
```bash
docker compose -f docker-compose.hostinger.yml logs -f app
docker compose -f docker-compose.hostinger.yml logs -f caddy
```

## 6) Migrar dados atuais
Opcao recomendada:
1. Entre no sistema atual.
2. Gere/baixe backup ZIP em **Backup > Exportar backup**.
3. Entre no sistema novo (Hostinger).
4. Restaure em **Backup > Restaurar backup**.

Se voce ja tem o arquivo `active_backup_*.zip`, basta restaurar no sistema novo.

## 7) Checklist de validacao
- Login admin funcionando.
- Quantidade de alunos/professores/turmas correta.
- Financeiro carregando valores.
- Desafios: criar/manual/IA, editar e excluir.
- Recibo PDF do professor gerando.
- Backup manual criando arquivo em `_data_backups`.

## 8) Comandos uteis
Rebuild apos atualizacao:
```bash
git pull origin principal
docker compose -f docker-compose.hostinger.yml up -d --build
```

Reiniciar:
```bash
docker compose -f docker-compose.hostinger.yml restart
```

Parar:
```bash
docker compose -f docker-compose.hostinger.yml down
```
