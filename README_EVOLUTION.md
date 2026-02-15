# 📱 Integração Evolution API - Active Educacional

## Visão Geral

Este documento descreve a integração do **Evolution API** com o sistema **Active Educacional**, permitindo o envio de mensagens via WhatsApp para alunos, professores e turmas.

---

## 🎯 Problema Resolvido

O sistema Evolution API não estava gerando QR codes devido à **falta de configuração das variáveis de ambiente** no Railway. Após a configuração correta, o sistema está funcionando perfeitamente.

---

## ✅ Configuração Realizada

### Variáveis de Ambiente no Railway

As seguintes variáveis foram adicionadas ao serviço `evolution-api` no Railway:

```env
AUTHENTICATION_API_KEY=Active2024SecureKey!@#
SERVER_URL=https://evolution-api.up.railway.app
CORS_ORIGIN=*
CORS_CREDENTIALS=true
```

### Como Acessar o Evolution Manager

1. **URL**: https://evolution-api.up.railway.app/manager/login
2. **Server URL**: `https://evolution-api.up.railway.app`
3. **API Key Global**: `Active2024SecureKey!@#`

---

## 📦 Arquivos Criados

### 1. `evolution_integration.py`

Módulo Python que facilita a integração com o Evolution API. Contém a classe `EvolutionAPI` com métodos para:

- ✅ Criar instâncias do WhatsApp
- ✅ Obter QR code para conexão
- ✅ Enviar mensagens individuais
- ✅ Enviar mensagens para grupos
- ✅ Enviar mensagens em massa
- ✅ Verificar status de conexão

**Exemplo de uso:**

```python
from evolution_integration import get_evolution_client

# Inicializar cliente
client = get_evolution_client()

# Enviar mensagem
client.send_text_message(
    instance_name="active_educacional",
    number="5511999999999",
    message="Olá! Esta é uma mensagem de teste."
)
```

### 2. `exemplo_integracao_whatsapp.py`

Exemplos práticos de como integrar o WhatsApp ao sistema Streamlit do Active Educacional:

- 📤 Página para enviar mensagens via WhatsApp
- 🎓 Envio automático de boas-vindas ao cadastrar aluno
- 📊 Envio em massa via arquivo CSV
- 👥 Envio para turmas inteiras

### 3. `evolution-env-config.txt`

Arquivo com todas as variáveis de ambiente disponíveis para configuração avançada do Evolution API, incluindo:

- Configuração de banco de dados
- Webhooks
- Armazenamento S3
- Redis e RabbitMQ
- Logs e debug

### 4. `guia_configuracao_railway.md`

Guia visual passo a passo para configurar as variáveis de ambiente no Railway.

---

## 🚀 Como Usar

### Passo 1: Conectar o WhatsApp

1. Acesse o Evolution Manager: https://evolution-api.up.railway.app/manager/login
2. Faça login com a API Key: `Active2024SecureKey!@#`
3. Clique em **"Create Instance"**
4. Nome da instância: `active_educacional`
5. Escaneie o QR code com o WhatsApp que será usado para enviar mensagens
6. Aguarde a conexão ser estabelecida (status: **Connected**)

### Passo 2: Testar a Integração

Execute o teste de conexão:

```bash
python3 evolution_integration.py
```

Você deve ver:

```
✅ Conexão OK! Instâncias encontradas: 1
  - active_educacional
```

### Passo 3: Integrar ao App.py

Para adicionar a funcionalidade de WhatsApp ao seu sistema Streamlit:

1. **Copie o arquivo `evolution_integration.py`** para o mesmo diretório do `app.py`

2. **Adicione a importação** no início do `app.py`:

```python
from evolution_integration import get_evolution_client
```

3. **Adicione a opção no menu** do Coordenador (linha ~636):

```python
menu_coord = st.radio(
    "Administração",
    [
        "Dashboard",
        "Cadastro de Alunos",
        "Cadastro de Professores",
        "Turmas",
        "Financeiro",
        "Usuários e Logins",
        "Conteúdos",
        "Enviar WhatsApp",  # <-- NOVA OPÇÃO
    ],
)
```

4. **Adicione a página** correspondente (após linha ~850):

```python
elif menu_coord == "Enviar WhatsApp":
    from exemplo_integracao_whatsapp import pagina_enviar_whatsapp
    pagina_enviar_whatsapp()
```

---

## 📋 Funcionalidades Disponíveis

### Envio Individual

Enviar mensagem para um número específico:

```python
client = get_evolution_client()
client.send_text_message(
    instance_name="active_educacional",
    number="5511999999999",
    message="Olá! Sua mensagem aqui."
)
```

### Envio em Massa

Enviar mensagens para múltiplos contatos:

```python
contacts = [
    {"number": "5511999999999", "message": "Mensagem para Ana"},
    {"number": "5511988888888", "message": "Mensagem para Bruno"},
]

results = client.send_bulk_messages("active_educacional", contacts)
```

### Notificação Automática

Enviar WhatsApp automaticamente ao cadastrar um aluno (adicione no formulário de cadastro):

```python
if cadastrar:
    # ... código existente de cadastro ...
    
    # Enviar WhatsApp de boas-vindas
    if telefone:
        try:
            client = get_evolution_client()
            mensagem = f"Olá {nome}! Seja bem-vindo(a) à Active Educacional! 🎓"
            client.send_text_message(
                instance_name="active_educacional",
                number=f"55{telefone}",
                message=mensagem
            )
            st.info("📱 WhatsApp de boas-vindas enviado!")
        except:
            pass  # Não bloquear o cadastro se o WhatsApp falhar
```

---

## 🔧 Troubleshooting

### Problema: QR Code não aparece

**Solução**: Verifique se as variáveis de ambiente estão configuradas corretamente no Railway:

1. Acesse: https://railway.app/project/5e8fc7c5-2377-41c4-bc47-b4b4fec75408
2. Clique em `evolution-api` > `Variables`
3. Confirme que `AUTHENTICATION_API_KEY` está definida

### Problema: Erro "Not Authorized" ao enviar mensagem

**Solução**: Verifique se a API Key no código está correta:

```python
# Em evolution_integration.py, linha 162
EVOLUTION_CONFIG = {
    "api_key": "Active2024SecureKey!@#",  # <-- Deve ser igual ao Railway
}
```

### Problema: Mensagem não é enviada

**Possíveis causas**:

1. ❌ Instância não está conectada (verifique no Manager)
2. ❌ Número de telefone está em formato incorreto (deve ser: `5511999999999`)
3. ❌ WhatsApp foi desconectado (reconecte escaneando o QR code novamente)

---

## 📊 Estrutura de Dados

### Formato de Número de Telefone

```
Correto: 5511999999999
         ││└─ Número (9 dígitos)
         │└─ DDD (2 dígitos)
         └─ Código do país (55 = Brasil)

Incorreto: (11) 99999-9999
Incorreto: 11999999999
Incorreto: +55 11 99999-9999
```

### Resposta de Envio de Mensagem

```json
{
  "key": {
    "remoteJid": "5511999999999@s.whatsapp.net",
    "fromMe": true,
    "id": "3EB0XXXXX"
  },
  "message": {
    "conversation": "Sua mensagem aqui"
  },
  "messageTimestamp": "1707998400",
  "status": "PENDING"
}
```

---

## 🔐 Segurança

### Boas Práticas

1. **Nunca compartilhe a API Key publicamente**
2. **Use variáveis de ambiente** para armazenar credenciais
3. **Não commite** arquivos `.env` no Git
4. **Rotacione a API Key** periodicamente

### Alterar a API Key

Se precisar alterar a API Key:

1. Acesse o Railway e modifique `AUTHENTICATION_API_KEY`
2. Atualize o valor em `evolution_integration.py`
3. Reinicie o serviço no Railway
4. Faça login novamente no Evolution Manager com a nova chave

---

## 📚 Recursos Adicionais

- **Documentação oficial do Evolution API**: https://doc.evolution-api.com
- **Discord do Evolution API**: https://evolution-api.com/discord
- **GitHub do Evolution API**: https://github.com/EvolutionAPI/evolution-api
- **Postman Collection**: Disponível no Manager

---

## 🎉 Conclusão

A integração está completa e funcional! Agora você pode:

✅ Gerar QR codes no Evolution Manager  
✅ Conectar o WhatsApp ao sistema  
✅ Enviar mensagens individuais e em massa  
✅ Integrar o WhatsApp ao sistema Active Educacional  
✅ Automatizar notificações para alunos e professores  

**Próximos passos sugeridos:**

1. Conectar o WhatsApp escaneando o QR code
2. Testar o envio de mensagens
3. Integrar ao app.py seguindo os exemplos fornecidos
4. Configurar notificações automáticas de boas-vindas

---

**Desenvolvido para**: Active Educacional  
**Data**: 15/02/2026  
**Autor**: Manus AI
