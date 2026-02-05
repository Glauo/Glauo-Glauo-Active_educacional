import base64
import datetime
from pathlib import Path

import pandas as pd
import streamlit as st

# --- CONFIGURACAO DA PAGINA ---
st.set_page_config(
    page_title="Active Educacional",
    page_icon=":mortar_board:",
    layout="wide",
    initial_sidebar_state="expanded",
)

# --- ESTILOS CSS PERSONALIZADOS ---
st.markdown(
    """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Sora:wght@500;700&family=Manrope:wght@400;600;700&display=swap');
    :root {
        --brand-900: #0d1b6f;
        --brand-700: #1A237E;
        --brand-500: #2c4be0;
        --mint-50: #f1fbf4;
        --mint-100: #dff6e6;
        --ink-900: #0c0f1a;
    }
    .stApp, .stMarkdown, label, input, select, textarea {
        font-family: 'Manrope', 'Segoe UI', sans-serif;
        color: var(--ink-900);
    }
    .main-header {font-size: 2.6rem; color: var(--brand-900); font-weight: 700; font-family: 'Sora', sans-serif;}
    .sub-header {font-size: 1.5rem; color: #333;}
    .login-title {font-family: 'Sora', sans-serif; font-weight: 700; color: var(--brand-900); font-size: 1.35rem;}
    .login-tagline {font-family: 'Manrope', sans-serif; font-weight: 800; color: #0c0f1a; font-size: 1.05rem;}
    .login-head {max-width: 420px; margin: 0 auto; text-align: left;}
    div[data-testid="stForm"] {
        max-width: 420px;
        margin: 8px auto 0;
        background: var(--mint-100);
        border: 3px solid var(--brand-700);
        padding: 18px;
        border-radius: 14px;
        box-shadow: 0 12px 30px rgba(13,27,111,0.14);
    }
    div[data-testid="stForm"] label {
        font-family: 'Manrope', 'Segoe UI', sans-serif;
        font-weight: 800;
        color: #0c0f1a;
        font-size: 0.95rem;
    }
    div[data-testid="stForm"] div.stButton {display: flex; justify-content: flex-start;}
    div[data-testid="stForm"] div.stButton > button {
        background: #ffd54f;
        color: #111;
        border: 2px solid #f2c230;
        font-weight: 800;
        border-radius: 10px;
        padding: 0.55rem 1.1rem;
        width: auto;
    }
    div[data-testid="stForm"] [data-baseweb="input"] input,
    div[data-testid="stForm"] [data-baseweb="textarea"] textarea,
    div[data-testid="stForm"] [data-baseweb="select"] > div {
        background: #ffffff !important;
        border: 1.6px solid #0d1b6f !important;
        border-radius: 8px !important;
    }
    div[data-testid="stForm"] [data-baseweb="input"] input:focus,
    div[data-testid="stForm"] [data-baseweb="textarea"] textarea:focus,
    div[data-testid="stForm"] [data-baseweb="select"] > div:focus-within {
        border-color: #2c4be0 !important;
        box-shadow: 0 0 0 2px rgba(44,75,224,0.15);
    }
    .hero-card {
        background: rgba(255,255,255,0.94);
        border: 2px solid rgba(13,27,111,0.18);
        border-radius: 20px;
        padding: 26px;
        box-shadow: 0 16px 40px rgba(10,20,60,0.12);
    }
    .hero-header {display: flex; align-items: center; gap: 18px; justify-content: flex-start;}
    .hero-logo-wrap {
        width: 120px;
        height: 120px;
        border-radius: 16px;
        background: #ffffff;
        display: flex;
        align-items: center;
        justify-content: center;
        box-shadow: 0 10px 24px rgba(13,27,111,0.10);
        border: 1px solid rgba(13,27,111,0.12);
    }
    .hero-logo {width: 96px; height: auto; display: block;}
    .hero-text {display: flex; flex-direction: column; gap: 6px;}
    .hero-kicker {
        display: inline-block;
        padding: 6px 12px;
        border-radius: 999px;
        background: #eef2ff;
        color: var(--brand-900);
        font-weight: 700;
        font-size: 0.85rem;
        letter-spacing: 0.4px;
        text-transform: uppercase;
        margin-bottom: 12px;
        font-family: 'Sora', sans-serif;
    }
    .hero-title {
        font-size: 2.2rem;
        font-weight: 700;
        color: var(--brand-900);
        font-family: 'Sora', sans-serif;
        margin: 0;
        line-height: 1.2;
    }
    .hero-sub {
        font-size: 1.02rem;
        color: #2c3e62;
        font-weight: 600;
        margin: 6px 0 10px;
    }
    .hero-list {list-style: none; padding-left: 0; margin: 10px 0 0;}
    .hero-list li {padding: 6px 0; border-bottom: 1px dashed rgba(26,35,126,0.15); color: #2b3550;}
    .hero-list li:last-child {border-bottom: none;}
    .hero-badges {margin-top: 14px; display: flex; gap: 8px; justify-content: flex-start; flex-wrap: wrap;}
    .hero-badge {background: #f0f7ff; color: #0d1b6f; padding: 6px 10px; border-radius: 999px; font-size: 0.85rem; font-weight: 700;}
    .card {background-color: #f0f2f6; padding: 20px; border-radius: 10px; margin-bottom: 10px;}
    .metric-container {background-color: white; padding: 15px; border-radius: 8px; border-left: 5px solid #1A237E; box-shadow: 0 2px 4px rgba(0,0,0,0.1);}
    .login-form-title {margin-bottom: 6px;}
    .pill {display: inline-block; padding: 4px 10px; border-radius: 999px; background: #e8eaf6; color: #1A237E; font-size: 0.85rem;}
</style>
""",
    unsafe_allow_html=True,
)

# --- GERENCIAMENTO DE SESSAO (LOGIN SIMULADO) ---
if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False
if "role" not in st.session_state:
    st.session_state["role"] = None
if "user_name" not in st.session_state:
    st.session_state["user_name"] = ""
if "unit" not in st.session_state:
    st.session_state["unit"] = ""
if "messages" not in st.session_state:
    st.session_state["messages"] = []
if "videos" not in st.session_state:
    st.session_state["videos"] = []
if "materials" not in st.session_state:
    st.session_state["materials"] = []
if "students" not in st.session_state:
    st.session_state["students"] = []
if "teachers" not in st.session_state:
    st.session_state["teachers"] = []
if "classes" not in st.session_state:
    st.session_state["classes"] = []
if "receivables" not in st.session_state:
    st.session_state["receivables"] = []
if "payables" not in st.session_state:
    st.session_state["payables"] = []
if "users" not in st.session_state:
    st.session_state["users"] = []


def get_logo_path():
    candidates = [
        Path("logo_active2.png"),
        Path("logo_active2.jpg"),
        Path("logo_active2.jpeg"),
        Path("logo_active2.webp"),
        Path("logo_active.png"),
        Path("logo_active.jpg"),
        Path("logo_active.jpeg"),
        Path("logo_active.webp"),
        Path("logo.png"),
        Path("logo.jpg"),
        Path("logo.jpeg"),
        Path("logo.webp"),
    ]
    for path in candidates:
        if path.exists():
            return path
    return None


def get_background_css():
    bg_candidates = [
        Path("imagem_active.png"),
        Path("imagem_active.jpg"),
        Path("imagem_active.jpeg"),
        Path("imagem_active.webp"),
    ]
    bg_path = next((p for p in bg_candidates if p.exists()), None)
    if not bg_path:
        return ""
    encoded = base64.b64encode(bg_path.read_bytes()).decode("utf-8")
    return f"""
<style>
    .stApp {{
        background-image:
            linear-gradient(rgba(255,255,255,0.90), rgba(255,255,255,0.90)),
            url("data:image/png;base64,{encoded}");
        background-size: cover;
        background-position: center;
        background-attachment: fixed;
    }}
</style>
"""


st.markdown(get_background_css(), unsafe_allow_html=True)


# --- FUNCOES DE LOGIN ---
def login_user(role, name, unit):
    st.session_state["logged_in"] = True
    st.session_state["role"] = role
    st.session_state["user_name"] = name
    st.session_state["unit"] = unit
    st.rerun()


def logout_user():
    st.session_state["logged_in"] = False
    st.session_state["role"] = None
    st.session_state["unit"] = ""
    st.rerun()


def class_names():
    return [c["nome"] for c in st.session_state["classes"]]


def teacher_names():
    return [t["nome"] for t in st.session_state["teachers"]]


def parse_money(value):
    try:
        return float(str(value).replace(",", "."))
    except ValueError:
        return 0.0


def format_money(value):
    return f"R$ {value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


# ==============================================================================
# TELA DE LOGIN
# ==============================================================================
if not st.session_state["logged_in"]:
    left, right = st.columns([1.1, 1])
    logo_path = get_logo_path()
    logo_html = ""
    if logo_path:
        logo_html = (
            "<div class='hero-logo-wrap'>"
            f"<img class='hero-logo' src='data:image/png;base64,{base64.b64encode(logo_path.read_bytes()).decode('utf-8')}'/>"
            "</div>"
        )

    with left:
        hero_html = f"""
        <div class='hero-card'>
            <div class='hero-kicker'>Active Educacional</div>
            <div class='hero-header'>
                {logo_html}
                <div class='hero-text'>
                    <div class='hero-title'>Sistema Educacional Ativo</div>
                    <div class='hero-sub'>Gestao academica, comunicacao e conteudo em um unico lugar.</div>
                </div>
            </div>
            <ul class='hero-list'>
                <li>Mensagens diretas com alunos e turmas</li>
                <li>Aulas gravadas e materiais organizados</li>
                <li>Financeiro simples e controle de matriculas</li>
            </ul>
            <div class='hero-badges'>
                <span class='hero-badge'>Seguro</span>
                <span class='hero-badge'>Rapido</span>
                <span class='hero-badge'>Profissional</span>
            </div>
        </div>
        """
        st.markdown(hero_html, unsafe_allow_html=True)

    with right:
        st.markdown(
            "<div class='login-head'>"
            "<div class='login-title login-form-title'>Conecte-se</div>"
            "<div class='login-tagline'>Acesse a Plataforma Educacional</div>"
            "</div>",
            unsafe_allow_html=True,
        )
        with st.form("login_form"):
            role = st.selectbox("Perfil", ["Aluno", "Professor", "Coordenador"])
            unidades = ["Matriz", "Unidade Centro", "Unidade Norte", "Unidade Sul", "Outra"]
            unidade_sel = st.selectbox("Unidade", unidades)
            if unidade_sel == "Outra":
                unidade = st.text_input("Digite a unidade")
            else:
                unidade = unidade_sel
            nome = st.text_input("Nome do usuario")
            senha = st.text_input("Senha", type="password")
            entrar = st.form_submit_button("Entrar")
        if entrar:
            login_user(role, nome.strip() or "Usuario", unidade.strip())

# ==============================================================================
# AREA DO ALUNO
# ==============================================================================
elif st.session_state["role"] == "Aluno":
    # Sidebar
    with st.sidebar:
        logo_path = get_logo_path()
        if logo_path:
            st.image(str(logo_path), width=140)
        else:
            st.image("https://cdn-icons-png.flaticon.com/512/3135/3135715.png", width=100)
        st.markdown(f"### Ola, {st.session_state['user_name']}")
        if st.session_state["unit"]:
            st.caption(f"Unidade: {st.session_state['unit']}")
        st.info("Nivel: Intermediario B1")
        st.markdown("---")
        menu_aluno = st.radio(
            "Navegacao",
            [
                "Dashboard",
                "Minhas Aulas",
                "Boletim & Frequencia",
                "Mensagens",
                "Aulas Gravadas",
                "Materiais de Estudo",
            ],
        )
        st.markdown("---")
        if st.button("Sair"):
            logout_user()

    # Conteudo Principal
    if menu_aluno == "Dashboard":
        st.markdown('<p class="main-header">Painel do Aluno</p>', unsafe_allow_html=True)

        # Alerta de Aula ao Vivo
        st.error("AULA AO VIVO AGORA: Conversation Class - Travel Tips (Iniciou ha 10 min)")
        if st.button("CLIQUE PARA ENTRAR NA AULA (ZOOM)", type="primary"):
            st.write("Redirecionando para o Zoom...")

        st.markdown("### Meu Progresso")
        col1, col2, col3 = st.columns(3)
        col1.metric("Aulas Assistidas", "24/30", "80%")
        col2.metric("Media Geral", "8.5", "+0.5")
        col3.metric("Proxima Prova", "15/02", "Oral Test")

        st.markdown("### Atividades Pendentes")
        st.info("Homework: Past Perfect Exercises (Vence amanha)")
        st.info("Leitura: Chapter 4 - The Great Gatsby")

    elif menu_aluno == "Minhas Aulas":
        st.markdown('<p class="main-header">Grade Curricular</p>', unsafe_allow_html=True)

        modules = {
            "Modulo 1: Introducao e Greetings": [
                "Aula 1.1 - Hello & Goodbye",
                "Aula 1.2 - Verb To Be",
            ],
            "Modulo 2: Present Continuous": [
                "Aula 2.1 - What are you doing?",
                "Aula 2.2 - Gerunds",
            ],
            "Modulo 3: Travel & Vocabulary": [
                "Aula 3.1 - At the Airport",
                "Aula 3.2 - Hotel Check-in",
            ],
        }

        for mod, aulas in modules.items():
            with st.expander(mod, expanded=False):
                for aula in aulas:
                    st.checkbox(f"{aula}", value=True)
                st.button(f"Ver Material de {mod.split(':')[0]}")

    elif menu_aluno == "Boletim & Frequencia":
        st.markdown(
            '<p class="main-header">Desempenho Academico</p>',
            unsafe_allow_html=True,
        )

        tab1, tab2 = st.tabs(["Notas", "Presenca"])

        with tab1:
            data = {
                "Competencia": ["Speaking", "Listening", "Reading", "Writing", "Grammar"],
                "Nota": [8.5, 9.0, 7.5, 8.0, 7.0],
                "Meta": [7.0, 7.0, 7.0, 7.0, 7.0],
            }
            df_notas = pd.DataFrame(data)

            # Grafico de barras simples
            st.bar_chart(df_notas.set_index("Competencia"))
            st.dataframe(df_notas, use_container_width=True)

        with tab2:
            st.write("Historico de Frequencia - Fev/2026")
            col1, col2 = st.columns(2)
            col1.metric("Presencas", "12")
            col2.metric("Faltas", "2", "-1")

            # Tabela simples de presenca
            presenca = pd.DataFrame(
                {
                    "Data": ["01/02", "03/02", "05/02", "08/02"],
                    "Status": ["Presente", "Presente", "Falta", "Presente"],
                }
            )
            st.table(presenca)

    elif menu_aluno == "Mensagens":
        st.markdown('<p class="main-header">Mensagens</p>', unsafe_allow_html=True)
        if not st.session_state["messages"]:
            st.info("Sem mensagens no momento.")
        else:
            for msg in reversed(st.session_state["messages"]):
                st.markdown(
                    f"**{msg['titulo']}**  \n"
                    f"{msg['mensagem']}  \n"
                    f"<span class='pill'>De: {msg['autor']}</span> "
                    f"<span class='pill'>Data: {msg['data']}</span> "
                    f"<span class='pill'>Turma: {msg['turma']}</span>",
                    unsafe_allow_html=True,
                )
                st.markdown("---")

    elif menu_aluno == "Aulas Gravadas":
        st.markdown('<p class="main-header">Aulas Gravadas</p>', unsafe_allow_html=True)
        if not st.session_state["videos"]:
            st.info("Sem videos cadastrados.")
        else:
            for video in reversed(st.session_state["videos"]):
                st.markdown(f"**{video['titulo']}**")
                st.caption(f"Turma: {video['turma']} | Data: {video['data']}")
                if video["url"]:
                    st.video(video["url"])
                st.markdown("---")

    elif menu_aluno == "Materiais de Estudo":
        st.markdown('<p class="main-header">Materiais de Estudo</p>', unsafe_allow_html=True)
        if not st.session_state["materials"]:
            st.info("Sem materiais cadastrados.")
        else:
            for mat in reversed(st.session_state["materials"]):
                st.markdown(f"**{mat['titulo']}**")
                st.caption(f"Turma: {mat['turma']} | Data: {mat['data']}")
                if mat["descricao"]:
                    st.write(mat["descricao"])
                if mat["link"]:
                    st.markdown(f"[Abrir material]({mat['link']})")
                st.markdown("---")

# ==============================================================================
# AREA DO PROFESSOR
# ==============================================================================
elif st.session_state["role"] == "Professor":
    # Sidebar
    with st.sidebar:
        logo_path = get_logo_path()
        if logo_path:
            st.image(str(logo_path), width=140)
        else:
            st.image("https://cdn-icons-png.flaticon.com/512/1995/1995539.png", width=100)
        st.markdown(f"### {st.session_state['user_name']}")
        if st.session_state["unit"]:
            st.caption(f"Unidade: {st.session_state['unit']}")
        st.warning("Perfil: Docente")
        st.markdown("---")
        menu_prof = st.radio(
            "Gestao",
            [
                "Minhas Turmas",
                "Diario de Classe (Chamada)",
                "Mensagens para Alunos",
                "Aulas Gravadas",
                "Materiais de Estudo",
            ],
        )
        st.markdown("---")
        if st.button("Sair"):
            logout_user()

    if menu_prof == "Minhas Turmas":
        st.markdown('<p class="main-header">Painel do Professor</p>', unsafe_allow_html=True)
        st.write(f"Hoje e: {datetime.date.today().strftime('%d/%m/%Y')}")

        col1, col2 = st.columns(2)
        with col1:
            st.markdown(
                """
            <div class="metric-container">
                <h3>Proxima Aula: 14:00</h3>
                <h2>Ingles Teens B1</h2>
                <p>Sala Virtual 01 - 12 Alunos</p>
            </div>
            """,
                unsafe_allow_html=True,
            )
            st.button("Iniciar Aula (Zoom)")

        with col2:
            st.markdown(
                """
            <div class="metric-container">
                <h3>Hoje: 19:00</h3>
                <h2>Adults Conversation</h2>
                <p>Sala Virtual 03 - 8 Alunos</p>
            </div>
            """,
                unsafe_allow_html=True,
            )

    elif menu_prof == "Diario de Classe (Chamada)":
        st.markdown('<p class="main-header">Realizar Chamada</p>', unsafe_allow_html=True)

        turma = st.selectbox("Selecione a Turma", ["Ingles Teens B1", "Adults Conversation"])
        data_chamada = st.date_input("Data da Aula", datetime.date.today())

        st.markdown("---")

        # Tabela editavel para chamada rapida
        df_alunos = pd.DataFrame(
            [
                {"Aluno": "Ana Clara", "Matricula": "202401", "Presente": True, "Obs": ""},
                {"Aluno": "Bruno Souza", "Matricula": "202402", "Presente": True, "Obs": ""},
                {"Aluno": "Carlos Eduardo", "Matricula": "202403", "Presente": False, "Obs": "Atestado"},
                {"Aluno": "Daniela Lima", "Matricula": "202404", "Presente": True, "Obs": ""},
            ]
        )

        edited_df = st.data_editor(
            df_alunos,
            column_config={
                "Presente": st.column_config.CheckboxColumn(
                    "Presenca?",
                    help="Marque se o aluno estava presente",
                    default=False,
                )
            },
            disabled=["Aluno", "Matricula"],
            hide_index=True,
            use_container_width=True,
        )

        st.markdown("### Resumo")
        total_presentes = edited_df["Presente"].sum()
        st.write(f"Total de Presentes: **{total_presentes}** / {len(edited_df)}")

        if st.button("SALVAR CHAMADA NO SISTEMA", type="primary"):
            st.success(
                f"Chamada da turma {turma} salva com sucesso para o dia {data_chamada}!"
            )

    elif menu_prof == "Mensagens para Alunos":
        st.markdown('<p class="main-header">Enviar Mensagem</p>', unsafe_allow_html=True)
        with st.form("form_msg"):
            titulo = st.text_input("Titulo da mensagem")
            mensagem = st.text_area("Mensagem")
            turma = st.selectbox("Turma", ["Todas", "Ingles Teens B1", "Adults Conversation"])
            enviar = st.form_submit_button("Enviar")
        if enviar:
            st.session_state["messages"].append(
                {
                    "titulo": titulo.strip() or "Mensagem",
                    "mensagem": mensagem.strip() or "Sem conteudo.",
                    "turma": turma,
                    "autor": st.session_state["user_name"],
                    "data": datetime.date.today().strftime("%d/%m/%Y"),
                }
            )
            st.success("Mensagem enviada.")

    elif menu_prof == "Aulas Gravadas":
        st.markdown('<p class="main-header">Cadastrar Aula Gravada</p>', unsafe_allow_html=True)
        with st.form("form_video"):
            titulo = st.text_input("Titulo da aula gravada")
            url = st.text_input("Link do video (YouTube/Drive)")
            turma = st.selectbox("Turma do video", ["Ingles Teens B1", "Adults Conversation"])
            enviar = st.form_submit_button("Cadastrar")
        if enviar:
            st.session_state["videos"].append(
                {
                    "titulo": titulo.strip() or "Aula gravada",
                    "url": url.strip(),
                    "turma": turma,
                    "data": datetime.date.today().strftime("%d/%m/%Y"),
                }
            )
            st.success("Video cadastrado.")

        if st.session_state["videos"]:
            st.markdown("### Videos cadastrados")
            for video in reversed(st.session_state["videos"]):
                st.markdown(f"**{video['titulo']}**")
                st.caption(f"Turma: {video['turma']} | Data: {video['data']}")
                if video["url"]:
                    st.video(video["url"])
                st.markdown("---")

    elif menu_prof == "Materiais de Estudo":
        st.markdown('<p class="main-header">Cadastrar Material</p>', unsafe_allow_html=True)
        with st.form("form_material"):
            titulo = st.text_input("Titulo do material")
            descricao = st.text_area("Descricao")
            link = st.text_input("Link do material (Drive/Docs)")
            turma = st.selectbox("Turma do material", ["Ingles Teens B1", "Adults Conversation"])
            enviar = st.form_submit_button("Cadastrar")
        if enviar:
            st.session_state["materials"].append(
                {
                    "titulo": titulo.strip() or "Material",
                    "descricao": descricao.strip(),
                    "link": link.strip(),
                    "turma": turma,
                    "data": datetime.date.today().strftime("%d/%m/%Y"),
                }
            )
            st.success("Material cadastrado.")

        if st.session_state["materials"]:
            st.markdown("### Materiais cadastrados")
            for mat in reversed(st.session_state["materials"]):
                st.markdown(f"**{mat['titulo']}**")
                st.caption(f"Turma: {mat['turma']} | Data: {mat['data']}")
                if mat["descricao"]:
                    st.write(mat["descricao"])
                if mat["link"]:
                    st.markdown(f"[Abrir material]({mat['link']})")
                st.markdown("---")

# ==============================================================================
# AREA DO COORDENADOR
# ==============================================================================
elif st.session_state["role"] == "Coordenador":
    # Sidebar
    with st.sidebar:
        logo_path = get_logo_path()
        if logo_path:
            st.image(str(logo_path), width=140)
        else:
            st.image("https://cdn-icons-png.flaticon.com/512/1995/1995539.png", width=100)
        st.markdown(f"### {st.session_state['user_name']}")
        if st.session_state["unit"]:
            st.caption(f"Unidade: {st.session_state['unit']}")
        st.success("Perfil: Coordenador")
        st.markdown("---")
        menu_coord = st.radio(
            "Administracao",
            [
                "Dashboard",
                "Cadastro de Alunos",
                "Cadastro de Professores",
                "Turmas",
                "Financeiro",
                "Usuarios e Logins",
                "Conteudos",
            ],
        )
        st.markdown("---")
        if st.button("Sair"):
            logout_user()

    if menu_coord == "Dashboard":
        st.markdown('<p class="main-header">Painel do Coordenador</p>', unsafe_allow_html=True)
        total_alunos = len(st.session_state["students"])
        total_professores = len(st.session_state["teachers"])
        total_turmas = len(st.session_state["classes"])
        total_receber = sum(parse_money(item["valor"]) for item in st.session_state["receivables"])
        total_pagar = sum(parse_money(item["valor"]) for item in st.session_state["payables"])
        saldo = total_receber - total_pagar

        col1, col2, col3 = st.columns(3)
        col1.metric("Alunos", total_alunos)
        col2.metric("Professores", total_professores)
        col3.metric("Turmas", total_turmas)

        col4, col5, col6 = st.columns(3)
        col4.metric("A Receber", format_money(total_receber))
        col5.metric("A Pagar", format_money(total_pagar))
        col6.metric("Saldo", format_money(saldo))

        st.info("Cadastre alunos, professores, turmas e organize o financeiro nas abas ao lado.")

    elif menu_coord == "Cadastro de Alunos":
        st.markdown('<p class="main-header">Cadastro de Alunos</p>', unsafe_allow_html=True)
        with st.form("form_aluno"):
            nome = st.text_input("Nome completo")
            matricula = st.text_input("Matricula")
            turma_opcoes = class_names()
            if turma_opcoes:
                turma = st.selectbox("Turma", turma_opcoes)
            else:
                turma = st.text_input("Turma")
            email = st.text_input("Email")
            telefone = st.text_input("Telefone")
            cidade = st.text_input("Cidade")
            endereco = st.text_input("Endereco")
            cep = st.text_input("CEP")
            numero = st.text_input("Numero")
            rg = st.text_input("RG")
            cpf = st.text_input("CPF")

            st.markdown("---")
            menor = st.checkbox("Aluno menor de idade?")
            resp_nome = resp_email = resp_telefone = ""
            resp_cidade = resp_endereco = resp_cep = resp_numero = ""
            resp_rg = resp_cpf = ""
            if menor:
                st.subheader("Dados do Responsavel")
                resp_nome = st.text_input("Nome completo do responsavel")
                resp_email = st.text_input("Email do responsavel")
                resp_telefone = st.text_input("Telefone do responsavel")
                resp_cidade = st.text_input("Cidade do responsavel")
                resp_endereco = st.text_input("Endereco do responsavel")
                resp_cep = st.text_input("CEP do responsavel")
                resp_numero = st.text_input("Numero do responsavel")
                resp_rg = st.text_input("RG do responsavel")
                resp_cpf = st.text_input("CPF do responsavel")
            cadastrar = st.form_submit_button("Cadastrar aluno")
        if cadastrar:
            st.session_state["students"].append(
                {
                    "nome": nome.strip() or "Aluno",
                    "matricula": matricula.strip(),
                    "turma": turma.strip(),
                    "email": email.strip(),
                    "telefone": telefone.strip(),
                    "cidade": cidade.strip(),
                    "endereco": endereco.strip(),
                    "cep": cep.strip(),
                    "numero": numero.strip(),
                    "rg": rg.strip(),
                    "cpf": cpf.strip(),
                    "menor": "Sim" if menor else "Nao",
                    "resp_nome": resp_nome.strip(),
                    "resp_email": resp_email.strip(),
                    "resp_telefone": resp_telefone.strip(),
                    "resp_cidade": resp_cidade.strip(),
                    "resp_endereco": resp_endereco.strip(),
                    "resp_cep": resp_cep.strip(),
                    "resp_numero": resp_numero.strip(),
                    "resp_rg": resp_rg.strip(),
                    "resp_cpf": resp_cpf.strip(),
                }
            )
            st.success("Aluno cadastrado.")

        if st.session_state["students"]:
            st.markdown("### Alunos cadastrados")
            df_students = pd.DataFrame(st.session_state["students"])
            st.dataframe(df_students, use_container_width=True)

            st.markdown("### Excluir aluno")
            aluno_options = [
                f"{idx + 1} - {row['nome']} ({row.get('matricula','')})"
                for idx, row in df_students.iterrows()
            ]
            aluno_sel = st.selectbox("Selecione o aluno", aluno_options, key="del_aluno")
            if st.button("Excluir aluno selecionado"):
                idx = aluno_options.index(aluno_sel)
                st.session_state["students"].pop(idx)
                st.success("Aluno excluido.")
                st.rerun()
        else:
            st.info("Nenhum aluno cadastrado.")

    elif menu_coord == "Cadastro de Professores":
        st.markdown('<p class="main-header">Cadastro de Professores</p>', unsafe_allow_html=True)
        with st.form("form_professor"):
            nome = st.text_input("Nome completo")
            area = st.text_input("Area/Especialidade")
            email = st.text_input("Email")
            telefone = st.text_input("Telefone")
            cadastrar = st.form_submit_button("Cadastrar professor")
        if cadastrar:
            st.session_state["teachers"].append(
                {
                    "nome": nome.strip() or "Professor",
                    "area": area.strip(),
                    "email": email.strip(),
                    "telefone": telefone.strip(),
                }
            )
            st.success("Professor cadastrado.")

        if st.session_state["teachers"]:
            st.markdown("### Professores cadastrados")
            df_teachers = pd.DataFrame(st.session_state["teachers"])
            st.dataframe(df_teachers, use_container_width=True)

            st.markdown("### Excluir professor")
            prof_options = [
                f"{idx + 1} - {row['nome']}"
                for idx, row in df_teachers.iterrows()
            ]
            prof_sel = st.selectbox("Selecione o professor", prof_options, key="del_prof")
            if st.button("Excluir professor selecionado"):
                idx = prof_options.index(prof_sel)
                st.session_state["teachers"].pop(idx)
                st.success("Professor excluido.")
                st.rerun()
        else:
            st.info("Nenhum professor cadastrado.")

    elif menu_coord == "Turmas":
        st.markdown('<p class="main-header">Cadastro de Turmas</p>', unsafe_allow_html=True)
        with st.form("form_turma"):
            nome_turma = st.text_input("Nome da turma")
            nivel = st.text_input("Nivel")
            professores = teacher_names()
            if professores:
                professor = st.selectbox("Professor", professores)
            else:
                professor = st.text_input("Professor")
            dias = st.text_input("Dias (ex: Seg/Qua/Sex)")
            horario = st.text_input("Horario (ex: 19:00)")
            cadastrar = st.form_submit_button("Cadastrar turma")
        if cadastrar:
            st.session_state["classes"].append(
                {
                    "nome": nome_turma.strip() or "Turma",
                    "nivel": nivel.strip(),
                    "professor": professor.strip(),
                    "dias": dias.strip(),
                    "horario": horario.strip(),
                }
            )
            st.success("Turma cadastrada.")

        if st.session_state["classes"]:
            st.markdown("### Turmas cadastradas")
            df_classes = pd.DataFrame(st.session_state["classes"])
            st.dataframe(df_classes, use_container_width=True)

            st.markdown("### Excluir turma")
            turma_options = [
                f"{idx + 1} - {row['nome']}"
                for idx, row in df_classes.iterrows()
            ]
            turma_sel = st.selectbox("Selecione a turma", turma_options, key="del_turma")
            if st.button("Excluir turma selecionada"):
                idx = turma_options.index(turma_sel)
                st.session_state["classes"].pop(idx)
                st.success("Turma excluida.")
                st.rerun()
        else:
            st.info("Nenhuma turma cadastrada.")

    elif menu_coord == "Financeiro":
        st.markdown('<p class="main-header">Financeiro</p>', unsafe_allow_html=True)
        tab1, tab2 = st.tabs(["Contas a Receber", "Contas a Pagar"])

        with tab1:
            with st.form("form_receber"):
                descricao = st.text_input("Descricao", key="rec_descricao")
                alunos = [s["nome"] for s in st.session_state["students"]]
                if alunos:
                    aluno = st.selectbox("Aluno", alunos, key="rec_aluno")
                else:
                    aluno = st.text_input("Aluno", key="rec_aluno_txt")
                valor = st.text_input("Valor (ex: 150,00)", key="rec_valor")
                vencimento = st.date_input(
                    "Vencimento", datetime.date.today(), key="rec_venc"
                )
                status = st.selectbox("Status", ["Aberto", "Pago"], key="rec_status")
                cadastrar = st.form_submit_button("Lancar conta a receber")
            if cadastrar:
                st.session_state["receivables"].append(
                    {
                        "descricao": descricao.strip() or "Mensalidade",
                        "aluno": aluno.strip(),
                        "valor": valor.strip(),
                        "vencimento": vencimento.strftime("%d/%m/%Y"),
                        "status": status,
                    }
                )
                st.success("Conta a receber cadastrada.")

            if st.session_state["receivables"]:
                st.markdown("### Contas a receber")
                df_rec = pd.DataFrame(st.session_state["receivables"])
                st.dataframe(df_rec, use_container_width=True)

                st.markdown("### Excluir conta a receber")
                rec_options = [
                    f"{idx + 1} - {row['descricao']} ({row.get('aluno','')})"
                    for idx, row in df_rec.iterrows()
                ]
                rec_sel = st.selectbox("Selecione a conta", rec_options, key="del_rec")
                if st.button("Excluir conta a receber"):
                    idx = rec_options.index(rec_sel)
                    st.session_state["receivables"].pop(idx)
                    st.success("Conta excluida.")
                    st.rerun()
            else:
                st.info("Nenhuma conta a receber cadastrada.")

        with tab2:
            with st.form("form_pagar"):
                descricao = st.text_input("Descricao", key="pag_descricao")
                fornecedor = st.text_input("Fornecedor", key="pag_fornecedor")
                valor = st.text_input("Valor (ex: 300,00)", key="pag_valor")
                vencimento = st.date_input(
                    "Vencimento", datetime.date.today(), key="pag_venc"
                )
                status = st.selectbox("Status", ["Aberto", "Pago"], key="pag_status")
                cadastrar = st.form_submit_button("Lancar conta a pagar")
            if cadastrar:
                st.session_state["payables"].append(
                    {
                        "descricao": descricao.strip() or "Despesa",
                        "fornecedor": fornecedor.strip(),
                        "valor": valor.strip(),
                        "vencimento": vencimento.strftime("%d/%m/%Y"),
                        "status": status,
                    }
                )
                st.success("Conta a pagar cadastrada.")

            if st.session_state["payables"]:
                st.markdown("### Contas a pagar")
                df_pay = pd.DataFrame(st.session_state["payables"])
                st.dataframe(df_pay, use_container_width=True)

                st.markdown("### Excluir conta a pagar")
                pay_options = [
                    f"{idx + 1} - {row['descricao']} ({row.get('fornecedor','')})"
                    for idx, row in df_pay.iterrows()
                ]
                pay_sel = st.selectbox("Selecione a conta", pay_options, key="del_pay")
                if st.button("Excluir conta a pagar"):
                    idx = pay_options.index(pay_sel)
                    st.session_state["payables"].pop(idx)
                    st.success("Conta excluida.")
                    st.rerun()
            else:
                st.info("Nenhuma conta a pagar cadastrada.")

    elif menu_coord == "Usuarios e Logins":
        st.markdown('<p class="main-header">Usuarios e Logins</p>', unsafe_allow_html=True)
        st.info("Cadastro simples de login (demo, sem criptografia).")
        with st.form("form_login"):
            perfil = st.selectbox("Perfil", ["Aluno", "Professor", "Coordenador"])
            if perfil == "Aluno":
                alunos = [s["nome"] for s in st.session_state["students"]]
                pessoa = st.selectbox("Aluno", alunos) if alunos else st.text_input("Aluno")
            elif perfil == "Professor":
                professores = teacher_names()
                pessoa = (
                    st.selectbox("Professor", professores)
                    if professores
                    else st.text_input("Professor")
                )
            else:
                pessoa = st.text_input("Nome do coordenador")
            usuario = st.text_input("Usuario")
            senha = st.text_input("Senha", type="password")
            cadastrar = st.form_submit_button("Criar login")
        if cadastrar:
            st.session_state["users"].append(
                {
                    "usuario": usuario.strip() or "usuario",
                    "perfil": perfil,
                    "pessoa": pessoa.strip(),
                    "senha": senha.strip(),
                }
            )
            st.success("Login criado.")

        if st.session_state["users"]:
            st.markdown("### Usuarios cadastrados")
            df_users = pd.DataFrame(st.session_state["users"])
            if "senha" in df_users.columns:
                df_users["senha"] = "******"
            st.dataframe(df_users, use_container_width=True)

            st.markdown("### Excluir usuario")
            user_options = [
                f"{idx + 1} - {row['usuario']} ({row.get('perfil','')})"
                for idx, row in df_users.iterrows()
            ]
            user_sel = st.selectbox("Selecione o usuario", user_options, key="del_user")
            if st.button("Excluir usuario selecionado"):
                idx = user_options.index(user_sel)
                st.session_state["users"].pop(idx)
                st.success("Usuario excluido.")
                st.rerun()
        else:
            st.info("Nenhum usuario cadastrado.")

    elif menu_coord == "Conteudos":
        st.markdown('<p class="main-header">Gestao de Conteudos</p>', unsafe_allow_html=True)
        tab1, tab2, tab3 = st.tabs(["Mensagens", "Aulas Gravadas", "Materiais"])

        with tab1:
            if st.session_state["messages"]:
                st.markdown("### Mensagens enviadas")
                df_msg = pd.DataFrame(st.session_state["messages"])
                st.dataframe(df_msg, use_container_width=True)
                msg_options = [
                    f"{idx + 1} - {row['titulo']} ({row.get('turma','')})"
                    for idx, row in df_msg.iterrows()
                ]
                msg_sel = st.selectbox("Selecione a mensagem", msg_options, key="del_msg")
                if st.button("Excluir mensagem"):
                    idx = msg_options.index(msg_sel)
                    st.session_state["messages"].pop(idx)
                    st.success("Mensagem excluida.")
                    st.rerun()
            else:
                st.info("Nenhuma mensagem enviada.")

        with tab2:
            if st.session_state["videos"]:
                st.markdown("### Aulas gravadas")
                df_vid = pd.DataFrame(st.session_state["videos"])
                st.dataframe(df_vid, use_container_width=True)
                vid_options = [
                    f"{idx + 1} - {row['titulo']} ({row.get('turma','')})"
                    for idx, row in df_vid.iterrows()
                ]
                vid_sel = st.selectbox("Selecione a aula", vid_options, key="del_vid")
                if st.button("Excluir aula gravada"):
                    idx = vid_options.index(vid_sel)
                    st.session_state["videos"].pop(idx)
                    st.success("Aula excluida.")
                    st.rerun()
            else:
                st.info("Nenhuma aula gravada cadastrada.")

        with tab3:
            if st.session_state["materials"]:
                st.markdown("### Materiais")
                df_mat = pd.DataFrame(st.session_state["materials"])
                st.dataframe(df_mat, use_container_width=True)
                mat_options = [
                    f"{idx + 1} - {row['titulo']} ({row.get('turma','')})"
                    for idx, row in df_mat.iterrows()
                ]
                mat_sel = st.selectbox("Selecione o material", mat_options, key="del_mat")
                if st.button("Excluir material"):
                    idx = mat_options.index(mat_sel)
                    st.session_state["materials"].pop(idx)
                    st.success("Material excluido.")
                    st.rerun()
            else:
                st.info("Nenhum material cadastrado.")
