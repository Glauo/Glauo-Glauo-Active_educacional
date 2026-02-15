# Solução Final - QR Code Evolution API

## Problema Identificado

O Evolution API v2.2.3 tinha um **bug conhecido** (Issue #2367 no GitHub) que causava um **loop infinito de reconexão**, impedindo a geração do QR code. O endpoint `/instance/connect` sempre retornava `{"count": 0}`.

## Causa Raiz

O Baileys (biblioteca WhatsApp) fechava a conexão durante a configuração inicial (antes do scan do QR), e o código do Evolution API disparava um loop de reconexão ao invés de aguardar a geração do QR code.

## Solução Aplicada

Foram adicionadas **2 variáveis de ambiente** no Railway:

```
NODE_OPTIONS="--network-family-autoselection-attempt-timeout=1000"
CONFIG_SESSION_PHONE_VERSION="2.3000.1028450369"
```

### NODE_OPTIONS
Aumenta o timeout de seleção de família de rede, permitindo que o QR code seja gerado corretamente antes do timeout.

### CONFIG_SESSION_PHONE_VERSION
Define uma versão específica do WhatsApp para evitar problemas de compatibilidade.

## Credenciais de Acesso

| Item | Valor |
|------|-------|
| **URL do Manager** | https://evolution-api-production-349d.up.railway.app/manager |
| **API Key Global** | `Active2024SecureKey!@#` |
| **Instância** | `active_educacional` |
| **Token da Instância** | Gerado automaticamente na criação |

## Como Usar

1. Acesse o Evolution Manager: https://evolution-api-production-349d.up.railway.app/manager/login
2. Faça login com a API Key: `Active2024SecureKey!@#`
3. Clique na instância `active_educacional`
4. Clique em "Get QR Code"
5. Escaneie com o WhatsApp

## Referências

- [Issue #2367 - BUG ERROR GENERATE QR CODE](https://github.com/EvolutionAPI/evolution-api/issues/2367)
- [PR #2365 - Bug Fix: QR Code Infinite Reconnection Loop](https://github.com/EvolutionAPI/evolution-api/pull/2365)
- [Issue #2388 - NODE_OPTIONS fix](https://github.com/EvolutionAPI/evolution-api/issues/2388)
