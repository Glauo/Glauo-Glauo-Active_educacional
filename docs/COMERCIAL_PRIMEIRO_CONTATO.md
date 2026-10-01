# Primeiro contato comercial

O módulo `/comercial` usa a identidade CondoJob, o site `https://condojob.org`
e a apresentação de Glauco Volpini como mensagem padrão de vendas.
O cabeçalho e a identificação da barra lateral usam CondoJob apenas em `/comercial`.
Empresa/condomínio e cargo do contato usam os campos existentes `empresa` e `cargo`.
Os rótulos Indicação de clientes e Contratação preservam os valores legados
`Indicacao de alunos` e `Matricula`, respectivamente, sem migrar históricos.

Leads com `primeiro_contato` exibem o botão **Primeiro contato** no funil.
O objeto contém `mensagem`, `imagem_id` e `status: "Preparado"`.
Preparar material não registra envio nem altera status ou último contato do lead.

As imagens originais são armazenadas uma vez em `active_kv`, chave
`sales_contact_images`, como lista de objetos com `id`, `nome`, `mime` e `base64`.
Essa chave participa dos backups manuais e automáticos.

`GET /api/comercial/imagem?id=<id>` exige sessão com acesso ao Comercial.
Use `download=1` para baixar o PNG original.

No modal, copie a mensagem ou abra o WhatsApp com o texto preenchido e anexe
a imagem baixada. O envio atual pela W-API aceita texto; esse fluxo mantém
a imagem disponível para anexação manual, sem disparar mensagens automaticamente.
