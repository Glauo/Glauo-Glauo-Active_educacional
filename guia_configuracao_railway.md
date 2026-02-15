
# Guia Visual: Configurando o Evolution API no Railway

Este guia irá ajudá-lo a configurar as variáveis de ambiente essenciais para o funcionamento do Evolution API no seu projeto do Railway. Siga os passos abaixo para resolver o problema de geração de QR code.

---

### Passo 1: Acesse as Variáveis do seu Projeto

1.  Faça login no seu painel do Railway: [https://railway.app/dashboard](https://railway.app/dashboard)
2.  Selecione o projeto onde o seu **Evolution API** está implantado.
3.  Dentro do projeto, clique no serviço correspondente ao Evolution API.
4.  Navegue até a aba **"Variables"** (Variáveis).

Você verá uma interface parecida com esta, onde todas as variáveis de ambiente do seu serviço são gerenciadas:

![Interface de Variáveis do Railway](https
/home/ubuntu/Active_educacional/railway_variables_interface.png)

---

### Passo 2: Adicione as Variáveis de Ambiente

Agora, você precisa adicionar as variáveis de ambiente que estão faltando. Para a configuração mínima e essencial, você precisará de pelo menos as seguintes variáveis:

-   `AUTHENTICATION_API_KEY`
-   `SERVER_URL`
-   `CORS_ORIGIN`
-   `CORS_CREDENTIALS`

1.  Clique no botão **"New Variable"** (Nova Variável) ou **"Raw Editor"** para adicionar as variáveis em massa.
2.  Copie as variáveis do arquivo `evolution-env-config.txt` que eu preparei para você.

**Para a configuração mínima, copie e cole o seguinte no Raw Editor:**

```env
AUTHENTICATION_API_KEY=Active2024SecureKey!@#
SERVER_URL=https://evolution-api.up.railway.app
CORS_ORIGIN=*
CORS_CREDENTIALS=true
```

**Observação:** Você pode (e deve) alterar o valor da `AUTHENTICATION_API_KEY` para uma senha mais segura de sua escolha.

![Adicionando uma nova variável no Railway](/home/ubuntu/Active_educacional/railway_add_variable.png)

---

### Passo 3: Reinicie o Serviço

Após adicionar as variáveis, o Railway deve reiniciar o seu serviço automaticamente. Se não o fizer, você pode forçar um "redeploy" (reimplantação) na aba **"Deployments"**.

---

### Passo 4: Teste a Geração do QR Code

1.  Acesse novamente a sua interface do Evolution Manager: [https://evolution-api.up.railway.app/manager/login](https://evolution-api.up.railway.app/manager/login)
2.  Use a `AUTHENTICATION_API_KEY` que você acabou de configurar para fazer o login.
3.  Crie uma nova instância e o QR code deverá ser gerado com sucesso.

Se você seguir estes passos, o problema de geração do QR code deverá ser resolvido. Se ainda assim encontrar dificuldades, me avise!
