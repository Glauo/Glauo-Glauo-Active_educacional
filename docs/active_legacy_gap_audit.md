# Varredura do sistema antigo Active Educacional

Data: 2026-05-06

## Ja restaurado nesta rodada

- Cadastro de aluno com modulo, responsavel, dados financeiros basicos e VIP.
- Controle VIP por aluno: `vip_tipo_plano`, `vip_aulas_total`, `vip_aulas_restantes`.
- Exibicao do saldo VIP como aulas dadas/total e restantes.
- Consumo automatico de 1 aula VIP ao fechar aula.
- Pagamento automatico do professor por modulo ao fechar aula.
- Visualizacao de faturas/boletos no detalhe do aluno.
- Envio de login e senha por WhatsApp via link pronto apos alterar credenciais.

## Gaps ainda identificados no antigo `app.py`

- Cadastro completo do aluno:
  - matricula automatica
  - genero
  - RG
  - cidade natal
  - pais
  - CEP
  - rua
  - numero
  - complemento
  - cidade
  - bairro
  - idade calculada pela data de nascimento
  - livro automatico vindo da turma
  - puxar aluno existente para corrigir no mesmo formulario

- Validacoes antigas:
  - aluno menor de idade exigia nome e CPF do responsavel
  - CPF do aluno com pelo menos 5 digitos para gerar senha
  - login automatico por data de nascimento e senha pelos 5 primeiros digitos do CPF
  - bloqueio quando login ja existe

- Comunicacao:
  - envio real por provedor WhatsApp/Evolution API
  - envio real por e-mail/SMTP
  - logs de comunicacao por origem/evento
  - notificacao de atualizacao de cadastro por e-mail + WhatsApp

- Financeiro do aluno:
  - geracao de parcelas no cadastro/matricula
  - dia de vencimento por contrato
  - boleto externo anexado
  - envio em massa de boletos por e-mail + WhatsApp
  - regua de cobranca mais completa

- Area pedagogica:
  - filtros por professor na lista de alunos
  - colunas visiveis configuraveis na lista
  - desafios direcionados para aluno VIP
  - livro/nivel automatico para desafios de aluno VIP

- Professores e aulas:
  - comprovantes/recibos completos do pagamento do professor
  - fechamento mensal por periodo com assinatura
  - lancamento manual de aulas do professor
  - relatorios exportaveis em PDF/Excel no mesmo nivel do sistema antigo

## Prioridade recomendada

1. Completar cadastro de aluno com matricula, endereco, RG, genero e idade.
2. Automatizar login/senha do aluno no cadastro completo, igual ao antigo.
3. Integrar WhatsApp real via configuracao existente, alem do link `wa.me`.
4. Restaurar geracao de parcelas/boletos a partir do cadastro do aluno.
5. Completar relatorios/exportacoes de alunos, financeiro e professores.
