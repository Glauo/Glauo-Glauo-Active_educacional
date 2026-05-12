# Wizbot Standalone

Projeto isolado do webhook do WhatsApp para publicar em um projeto separado no EasyPanel.

## EasyPanel

- Tipo: `Dockerfile / Git`
- Repositório: este mesmo repositório
- Branch: `principal`
- Caminho de build: `deploy/wizbot`

## Porta

- Serviço HTTP: `8787`

## URL

- Health: `/health`
- Webhook: `/wapi/webhook?token=SEU_TOKEN`

## Variáveis mínimas

- `GROQ_API_KEY`
- `ACTIVE_WHATSAPP_PROVIDER=wapi`
- `WAPI_BASE_URL`
- `WAPI_TOKEN`
- `WAPI_INSTANCE_ID`
- `ACTIVE_WIZ_WEBHOOK_TOKEN`

## Observação

Esse bot é isolado do app principal para não interferir no deploy do Ativo. Ele responde de forma genérica e usa o W-API apenas para receber e devolver mensagens.
