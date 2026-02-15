"""
Exemplo de como integrar o Evolution API ao sistema Active Educacional
Este arquivo mostra como adicionar funcionalidade de envio de WhatsApp ao app.py
"""

import streamlit as st
from evolution_integration import get_evolution_client

# ============================================================================
# EXEMPLO 1: Adicionar ao menu do Coordenador - Enviar mensagem via WhatsApp
# ============================================================================

def pagina_enviar_whatsapp():
    """Página para enviar mensagens via WhatsApp"""
    st.markdown('<p class="main-header">Enviar Mensagem via WhatsApp</p>', unsafe_allow_html=True)
    
    # Inicializar cliente Evolution
    client = get_evolution_client()
    
    # Verificar status da conexão
    with st.expander("ℹ️ Status da Conexão WhatsApp"):
        try:
            instances = client.list_instances()
            if instances:
                st.success(f"✅ Conectado! {len(instances)} instância(s) ativa(s)")
                for inst in instances:
                    instance_name = inst.get('instance', {}).get('instanceName', 'N/A')
                    st.info(f"📱 Instância: {instance_name}")
            else:
                st.warning("⚠️ Nenhuma instância conectada. Configure primeiro no Evolution Manager.")
                st.markdown("[Acessar Evolution Manager](https://evolution-api.up.railway.app/manager/login)")
        except Exception as e:
            st.error(f"❌ Erro ao verificar conexão: {e}")
    
    st.markdown("---")
    
    # Formulário de envio
    with st.form("form_whatsapp"):
        st.subheader("📤 Enviar Mensagem")
        
        tipo_envio = st.radio(
            "Tipo de envio",
            ["Individual", "Para toda uma turma", "Mensagem em massa"]
        )
        
        if tipo_envio == "Individual":
            numero = st.text_input(
                "Número do WhatsApp (com DDD)",
                placeholder="11999999999",
                help="Digite apenas números, sem espaços ou caracteres especiais"
            )
            mensagem = st.text_area(
                "Mensagem",
                placeholder="Digite sua mensagem aqui..."
            )
            
        elif tipo_envio == "Para toda uma turma":
            turma = st.selectbox(
                "Selecione a turma",
                ["Inglês Teens B1", "Adults Conversation"]
            )
            mensagem = st.text_area(
                "Mensagem para a turma",
                placeholder="Digite a mensagem que será enviada para todos os alunos da turma..."
            )
            
        else:  # Mensagem em massa
            st.info("📋 Carregue um arquivo CSV com as colunas: numero, mensagem")
            arquivo = st.file_uploader(
                "Arquivo CSV",
                type=["csv"],
                help="Formato: numero,mensagem (sem espaços no número)"
            )
        
        enviar = st.form_submit_button("📨 Enviar WhatsApp", type="primary")
    
    # Processar envio
    if enviar:
        try:
            if tipo_envio == "Individual":
                if not numero or not mensagem:
                    st.error("❌ Preencha todos os campos!")
                else:
                    # Formatar número (adicionar código do país se necessário)
                    numero_formatado = f"55{numero}" if not numero.startswith("55") else numero
                    
                    with st.spinner("Enviando mensagem..."):
                        result = client.send_text_message(
                            instance_name="active_educacional",
                            number=numero_formatado,
                            message=mensagem
                        )
                    
                    st.success(f"✅ Mensagem enviada com sucesso para {numero}!")
                    st.json(result)
            
            elif tipo_envio == "Para toda uma turma":
                # Buscar alunos da turma (exemplo com dados mockados)
                alunos_turma = [
                    {"nome": "Ana Clara", "telefone": "5511999999999"},
                    {"nome": "Bruno Souza", "telefone": "5511988888888"},
                ]
                
                if not mensagem:
                    st.error("❌ Digite a mensagem!")
                else:
                    with st.spinner(f"Enviando para {len(alunos_turma)} alunos..."):
                        contacts = [
                            {"number": aluno["telefone"], "message": mensagem}
                            for aluno in alunos_turma
                        ]
                        results = client.send_bulk_messages("active_educacional", contacts)
                    
                    # Mostrar resultados
                    success_count = sum(1 for r in results if r["status"] == "success")
                    st.success(f"✅ {success_count}/{len(results)} mensagens enviadas!")
                    
                    with st.expander("Ver detalhes"):
                        for result in results:
                            if result["status"] == "success":
                                st.success(f"✅ {result['number']}")
                            else:
                                st.error(f"❌ {result['number']}: {result['error']}")
            
            else:  # Mensagem em massa
                if arquivo:
                    import pandas as pd
                    df = pd.read_csv(arquivo)
                    
                    with st.spinner(f"Enviando {len(df)} mensagens..."):
                        contacts = [
                            {"number": str(row["numero"]), "message": row["mensagem"]}
                            for _, row in df.iterrows()
                        ]
                        results = client.send_bulk_messages("active_educacional", contacts)
                    
                    success_count = sum(1 for r in results if r["status"] == "success")
                    st.success(f"✅ {success_count}/{len(results)} mensagens enviadas!")
                else:
                    st.error("❌ Carregue um arquivo CSV!")
        
        except Exception as e:
            st.error(f"❌ Erro ao enviar: {e}")


# ============================================================================
# EXEMPLO 2: Como adicionar ao menu principal do app.py
# ============================================================================

"""
Para adicionar ao seu app.py, adicione esta opção no menu do Coordenador:

# No menu do Coordenador (linha ~636)
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
        "Enviar WhatsApp",  # <-- ADICIONAR ESTA LINHA
    ],
)

# Depois, adicione o elif correspondente (após a linha ~850):
elif menu_coord == "Enviar WhatsApp":
    pagina_enviar_whatsapp()
"""


# ============================================================================
# EXEMPLO 3: Enviar notificação automática ao cadastrar aluno
# ============================================================================

def exemplo_notificacao_automatica():
    """
    Exemplo de como enviar WhatsApp automaticamente ao cadastrar um aluno
    """
    # No formulário de cadastro de aluno (após a linha ~709):
    
    """
    if cadastrar:
        # ... código existente de cadastro ...
        
        # ADICIONAR: Enviar WhatsApp de boas-vindas
        if telefone:  # Se o aluno forneceu telefone
            try:
                client = get_evolution_client()
                mensagem_boas_vindas = f'''
Olá {nome}! 👋

Seja bem-vindo(a) à Active Educacional! 🎓

Você foi matriculado(a) na turma: {turma}

Em breve você receberá mais informações sobre as aulas.

Qualquer dúvida, estamos à disposição!

Active Educacional
                '''
                
                client.send_text_message(
                    instance_name="active_educacional",
                    number=f"55{telefone}",
                    message=mensagem_boas_vindas.strip()
                )
                
                st.info("📱 WhatsApp de boas-vindas enviado!")
            except:
                pass  # Não bloquear o cadastro se o WhatsApp falhar
    """


# ============================================================================
# TESTE RÁPIDO
# ============================================================================

if __name__ == "__main__":
    print("📱 Este é um arquivo de exemplo de integração.")
    print("Para usar, copie as funções para o seu app.py")
    print("\nTestando conexão com Evolution API...")
    
    try:
        client = get_evolution_client()
        instances = client.list_instances()
        print(f"✅ Conexão OK! {len(instances)} instância(s) encontrada(s)")
    except Exception as e:
        print(f"❌ Erro: {e}")
