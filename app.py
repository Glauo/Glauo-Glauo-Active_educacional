import base64
import datetime
import json
import uuid
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

# --- GERENCIAMENTO DE SESSAO (INICIALIZACAO) ---
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
if "grades" not in st.session_state:
    st.session_state["grades"] = []
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
if "fee_templates" not in st.session_state:
    st.session_state["fee_templates"] = []
if "account_profile" not in st.session_state:
    st.session_state["account_profile"] = None
if "email_log" not in st.session_state:
    st.session_state["email_log"] = []

ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "123"
USERS_FILE = Path("users.json")
MESSAGES_FILE = Path("messages.json")
VIDEOS_FILE = Path("videos.json")
MATERIALS_FILE = Path("materials.json")
GRADES_FILE = Path("grades.json")
WHATSAPP_NUMBER = "5516996043314" # Seu numero

# --- FUNCOES DE UTILIDADE ---
def get_logo_path():
    candidates = [
        Path("image_8fc66d.png"),
        Path("logo_active2.png"),
        Path("logo_active2.jpg"),
        Path("logo.png"),
    ]
    for path in candidates:
        if path.exists():
            return path
    return None

def load_users():
    if USERS_FILE.exists():
        try:
            data = json.loads(USERS_FILE.read_text(encoding="utf-8"))
            return data if isinstance(data, list) else []
        except Exception:
            return []
    return []

def save_users(users):
    USERS_FILE.write_text(json.dumps(users, ensure_ascii=False, indent=2), encoding="utf-8")

def load_list(path):
    if path.exists():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            return data if isinstance(data, list) else []
        except Exception:
            return []
    return []

def save_list(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

def ensure_admin_user(users):
    if not any(u.get("usuario") == ADMIN_USERNAME for u in users):
        users.append({
            "usuario": ADMIN_USERNAME,
            "senha": ADMIN_PASSWORD,
            "perfil": "Admin",
            "pessoa": "Administrador",
        })
    return users

def find_user(username):
    for user in st.session_state["users"]:
        if user.get("usuario", "").lower() == username.lower():
            return user
    return None

def login_user(role, name, unit, account_profile):
    st.session_state["logged_in"] = True
    st.session_state["role"] = role
    st.session_state["user_name"] = name
    st.session_state["unit"] = unit
    st.session_state["account_profile"] = account_profile
    st.rerun()

def logout_user():
    st.session_state["logged_in"] = False
    st.session_state["role"] = None
    st.session_state["unit"] = ""
    st.session_state["account_profile"] = None
    st.rerun()

# --- HELPER FUNCTIONS DE NEGOCIO ---
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

def parse_date(value):
    try:
        return datetime.datetime.strptime(value, "%d/%m/%Y").date()
    except Exception:
        return None

def is_overdue(item):
    if item.get("status") == "Pago": return False
    venc = parse_date(item.get("vencimento", ""))
    if not venc: return False
    return venc < datetime.date.today()

def add_receivable(aluno, descricao, valor, vencimento, cobranca, categoria):
    codigo = f"{cobranca.upper()}-{uuid.uuid4().hex[:8].upper()}"
    st.session_state["receivables"].append({
        "descricao": descricao.strip() or "Mensalidade",
        "aluno": aluno.strip(),
        "categoria": categoria,
        "cobranca": cobranca,
        "codigo": codigo,
        "valor": valor.strip(),
        "vencimento": vencimento.strftime("%d/%m/%Y"),
        "status": "Aberto",
    })
    return codigo

def allowed_portals(profile):
    if profile == "Aluno": return ["Aluno"]
    if profile == "Professor": return ["Professor"]
    if profile == "Coordenador": return ["Aluno", "Professor", "Coordenador"]
    if profile == "Admin": return ["Aluno", "Professor", "Coordenador"]
    return []

def email_students_by_turma(turma, assunto, corpo, origem):
    # Simulacao de envio de email
    for student in st.session_state["students"]:
        if turma == "Todas" or student.get("turma") == turma:
            email = student.get("email", "").strip()
            if email:
                st.session_state["email_log"].append({
                    "destinatario": student.get("nome", "Aluno"),
                    "email": email,
                    "assunto": assunto,
                    "mensagem": corpo,
                    "origem": origem,
                    "data": datetime.date.today().strftime("%d/%m/%Y"),
                })

def sidebar_menu(title, options, key):
    st.markdown(f"<h3 style='color:#1e3a8a; font-family:Sora;'>{title}</h3>", unsafe_allow_html=True)
    if key not in st.session_state:
        st.session_state[key] = options[0]
    for option in options:
        # Usa um estilo de botao nativo mas que sera estilizado pelo CSS global
        active = st.session_state[key] == option
        if st.button(option, key=f"{key}_{option}", type="primary" if active else "secondary"):
            st.session_state[key] = option
            st.rerun()
    return st.session_state[key]

# ==============================================================================
# CSS DINAMICO (LOGIN vs SISTEMA INTERNO)
# ==============================================================================

if not st.session_state["logged_in"]:
    # --- CSS DA TELA DE LOGIN (NOVO DESIGN) ---
    st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Manrope:wght@400;600;700;800&family=Sora:wght@400;600;700&display=swap');
        
        .stApp {
            background: linear-gradient(135deg, #0f172a 0%, #1e3a8a 50%, #3b82f6 100%);
            font-family: 'Manrope', sans-serif;
        }
        header {visibility: hidden;}
        footer {visibility: hidden;}
        .block-container {
            padding-top: 5rem;
            padding-bottom: 5rem;
            max-width: 1000px;
        }
        .info-card {
            background: rgba(255, 255, 255, 0.95);
            border-radius: 24px;
            padding: 40px;
            height: 100%;
            box-shadow: 0 20px 50px rgba(0,0,0,0.2);
            color: #1e293b;
            display: flex;
            flex-direction: column;
            justify-content: center;
        }
        .logo-area { margin-bottom: 24px; }
        .logo-img { max-width: 80px; }
        .info-title {
            font-family: 'Sora', sans-serif;
            font-size: 2rem;
            font-weight: 700;
            color: #0f172a;
            line-height: 1.2;
            margin-bottom: 12px;
        }
        .info-subtitle {
            font-size: 1rem;
            color: #64748b;
            margin-bottom: 32px;
            line-height: 1.5;
        }
        .feature-item {
            display: flex;
            align-items: center;
            gap: 16px;
            margin-bottom: 20px;
        }
        .feature-icon-box {
            width: 48px;
            height: 48px;
            background: #eff6ff;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 1.2rem;
            color: #2563eb;
        }
        .feature-text {
            font-weight: 600;
            color: #334155;
            font-size: 0.95rem;
        }
        .feature-sub {
            font-size: 0.8rem;
            color: #94a3b8;
        }
        .whatsapp-button {
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 10px;
            background: #22c55e;
            color: white !important;
            font-weight: 700;
            padding: 14px;
            border-radius: 12px;
            text-decoration: none;
            margin-top: 20px;
            transition: transform 0.2s;
            box-shadow: 0 4px 12px rgba(34, 197, 94, 0.3);
        }
        .whatsapp-button:hover {
            transform: translateY(-2px);
            opacity: 0.95;
        }
        div[data-testid="stForm"] {
            background: #ffffff;
            border-radius: 24px;
            padding: 40px;
            border: none;
            box-shadow: 0 20px 50px rgba(0,0,0,0.2);
        }
        .login-header {
            font-family: 'Sora', sans-serif;
            font-size: 1.5rem;
            font-weight: 700;
            color: #0f172a;
            margin-bottom: 4px;
        }
        .login-sub {
            font-size: 0.9rem;
            color: #64748b;
            margin-bottom: 24px;
        }
        div[data-testid="stForm"] label {
            font-size: 0.85rem;
            font-weight: 600;
            color: #475569;
        }
        div[data-testid="stForm"] input, 
        div[data-testid="stForm"] select,
        div[data-testid="stForm"] div[data-baseweb="select"] > div {
            background-color: #f8fafc !important;
            border: 1px solid #e2e8f0 !important;
            border-radius: 12px !important;
            color: #334155 !important;
            height: 48px;
        }
        div[data-testid="stForm"] input:focus, 
        div[data-testid="stForm"] div[data-baseweb="select"] > div:focus-within {
            border-color: #3b82f6 !important;
            box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1) !important;
        }
        div[data-testid="stForm"] button {
            background: linear-gradient(to right, #2563eb, #1d4ed8);
            color: white;
            border: none;
            border-radius: 12px;
            font-weight: 700;
            padding: 0.75rem 1rem;
            width: 100%;
            font-size: 1rem;
            margin-top: 10px;
        }
        div[data-testid="stForm"] button:hover {
            opacity: 0.9;
            border: none;
        }
    </style>
    """, unsafe_allow_html=True)

else:
    # --- CSS DO SISTEMA INTERNO (DASHBOARD PROFISSIONAL) ---
    st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Manrope:wght@400;600;700&family=Sora:wght@500;700&display=swap');
        
        /* Fundo Geral */
        .stApp { 
            background: #f8fafc; /* Cinza muito claro, quase branco */
            font-family: 'Manrope', sans-serif; 
        }
        
        /* Header Principal */
        .main-header { 
            font-family: 'Sora', sans-serif; 
            font-size: 1.8rem; 
            font-weight: 700; 
            color: #1e3a8a; 
            margin-bottom: 20px;
        }
        
        /* --- SIDEBAR PERSONALIZADA --- */
        section[data-testid="stSidebar"] {
            background-color: #ffffff;
            border-right: 1px solid #e2e8f0;
            box-shadow: 2px 0 10px rgba(0,0,0,0.02);
        }
        
        /* Botões Inativos da Sidebar */
        section[data-testid="stSidebar"] .stButton > button {
            background-color: transparent;
            border: none;
            color: #64748b;
            text-align: left;
            font-weight: 600;
            padding: 0.6rem 1rem;
            width: 100%;
            border-radius: 8px;
            transition: all 0.2s;
            margin-bottom: 4px;
        }
        section[data-testid="stSidebar"] .stButton > button:hover {
            color: #1e3a8a;
            background-color: #f1f5f9;
            transform: translateX(4px);
        }
        
        /* Botão ATIVO da Sidebar (Destaque) */
        section[data-testid="stSidebar"] .stButton > button[kind="primary"] {
            background: linear-gradient(90deg, #eff6ff 0%, #ffffff 100%);
            color: #1d4ed8;
            border-left: 4px solid #1d4ed8;
            border-radius: 4px 8px 8px 4px;
            box-shadow: 0 2px 5px rgba(29, 78, 216, 0.05);
        }

        /* --- CARDS DE METRICAS (Estilo Novo) --- */
        .dash-card {
            background: white;
            padding: 24px;
            border-radius: 16px;
            border: 1px solid #e2e8f0;
            box-shadow: 0 4px 20px rgba(0,0,0,0.03);
            transition: transform 0.2s, box-shadow 0.2s;
            height: 100%;
            display: flex;
            flex-direction: column;
            justify-content: space-between;
        }
        .dash-card:hover {
            transform: translateY(-2px);
            box-shadow: 0 10px 25px rgba(0,0,0,0.06);
            border-color: #cbd5e1;
        }
        .card-title {
            font-size: 0.9rem;
            color: #64748b;
            font-weight: 600;
            margin-bottom: 8px;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }
        .card-value {
            font-family: 'Sora', sans-serif;
            font-size: 2rem;
            font-weight: 700;
            color: #0f172a;
        }
        .card-sub {
            font-size: 0.85rem;
            margin-top: 8px;
            display: flex;
            align-items: center;
            gap: 6px;
        }
        .trend-up { color: #10b981; background: #ecfdf5; padding: 2px 8px; border-radius: 99px; font-weight: 700; }
        .trend-neutral { color: #64748b; }
        
        /* --- ESTILIZAÇÃO DE TABELAS (Containers) --- */
        div[data-testid="stDataFrame"] {
            background: white;
            padding: 16px;
            border-radius: 12px;
            border: 1px solid #e2e8f0;
            box-shadow: 0 2px 8px rgba(0,0,0,0.02);
        }
        
        /* Formularios Internos */
        div[data-testid="stForm"] {
            background: white;
            padding: 30px;
            border-radius: 16px;
            border: 1px solid #e2e8f0;
            box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05);
        }
        
        /* Inputs Internos */
        input, textarea, select {
            border-radius: 8px !important;
            border: 1px solid #cbd5e1 !important;
        }
        input:focus {
            border-color: #3b82f6 !important;
            box-shadow: 0 0 0 2px rgba(59, 130, 246, 0.1) !important;
        }
    </style>
    """, unsafe_allow_html=True)

# ==============================================================================
# LOGICA DE INICIALIZACAO DE DADOS
# ==============================================================================
st.session_state["messages"] = load_list(MESSAGES_FILE)
st.session_state["videos"] = load_list(VIDEOS_FILE)
st.session_state["materials"] = load_list(MATERIALS_FILE)
st.session_state["grades"] = load_list(GRADES_FILE)

if not st.session_state["users"]:
    st.session_state["users"] = load_users()
    st.session_state["users"] = ensure_admin_user(st.session_state["users"])
    save_users(st.session_state["users"])

# ==============================================================================
# TELA DE LOGIN
# ==============================================================================
if not st.session_state["logged_in"]:
    col_left, col_right = st.columns([1, 0.8], gap="large")
    with col_left:
        logo_path = get_logo_path()
        logo_html = ""
        if logo_path:
            encoded_logo = base64.b64encode(logo_path.read_bytes()).decode('utf-8')
            logo_html = f"<img src='data:image/png;base64,{encoded_logo}' class='logo-img'>"
        
        # Correção da identação do HTML
        st.markdown(f"""
<div class="info-card">
<div class="logo-area">{logo_html}</div>
<div class="info-title">Sistema Educacional<br>Ativo</div>
<div class="info-subtitle">Gestão acadêmica, comunicação e conteúdo pedagógico em um único lugar.</div>
<div class="feature-item">
<div class="feature-icon-box">💬</div>
<div><div class="feature-text">Mensagens Diretas</div><div class="feature-sub">Comunicação rápida com alunos e turmas.</div></div>
</div>
<div class="feature-item">
<div class="feature-icon-box">🎥</div>
<div><div class="feature-text">Aulas Gravadas</div><div class="feature-sub">Conteúdo organizado e acessível 24h.</div></div>
</div>
<div class="feature-item">
<div class="feature-icon-box">💲</div>
<div><div class="feature-text">Financeiro Simples</div><div class="feature-sub">Controle de matrículas e pagamentos.</div></div>
</div>
<a href="https://wa.me/{WHATSAPP_NUMBER}" target="_blank" class="whatsapp-button">📱 Falar com Suporte no WhatsApp</a>
</div>
""", unsafe_allow_html=True)

    with col_right:
        st.write("") 
        st.write("")
        with st.form("login_form"):
            st.markdown("""<div class="login-header">Conecte-se</div><div class="login-sub">Acesse a Plataforma Educacional</div>""", unsafe_allow_html=True)
            role = st.selectbox("Perfil", ["Aluno", "Professor", "Coordenador"])
            unidades = ["Matriz", "Unidade Centro", "Unidade Norte", "Unidade Sul", "Outra"]
            unidade_sel = st.selectbox("Unidade", unidades)
            if unidade_sel == "Outra":
                unidade = st.text_input("Digite o nome da unidade", placeholder="Ex: Unidade Nova")
            else:
                unidade = unidade_sel
            usuario = st.text_input("Usuário", placeholder="Seu usuário de acesso")
            senha = st.text_input("Senha", type="password", placeholder="Sua senha")
            entrar = st.form_submit_button("Entrar no Sistema")
        
        if entrar:
            user = find_user(usuario.strip())
            if not usuario.strip() or not senha.strip():
                st.error("⚠️ Informe usuário e senha.")
            elif not user or user.get("senha") != senha.strip():
                st.error("⚠️ Usuário ou senha inválidos.")
            else:
                perfil_conta = user.get("perfil", "")
                if role not in allowed_portals(perfil_conta):
                    st.error(f"⚠️ Este usuário não tem permissão de {role}.")
                else:
                    display_name = user.get("pessoa") or usuario.strip()
                    login_user(role, display_name, str(unidade).strip(), perfil_conta)

# ==============================================================================
# LOGICA DO SISTEMA (DASHBOARD COM VISUAL NOVO)
# ==============================================================================
elif st.session_state["role"] == "Aluno":
    with st.sidebar:
        logo_path = get_logo_path()
        if logo_path: st.image(str(logo_path), width=120)
        st.markdown(f"### Olá, {st.session_state['user_name']}")
        if st.session_state["unit"]: st.caption(f"Unidade: {st.session_state['unit']}")
        st.info("Nível: Intermediário B1")
        st.markdown("---")
        menu_aluno_label = sidebar_menu("Navegação", ["🏠 Painel", "📚 Minhas Aulas", "📊 Boletim e Frequência", "💬 Mensagens", "🎥 Aulas Gravadas", "💰 Financeiro", "📂 Materiais de Estudo"], "menu_aluno")
        st.markdown("---")
        if st.button("Sair"): logout_user()

    menu_aluno_map = {"🏠 Painel": "Dashboard", "📚 Minhas Aulas": "Minhas Aulas", "📊 Boletim e Frequência": "Boletim & Frequencia", "💬 Mensagens": "Mensagens", "🎥 Aulas Gravadas": "Aulas Gravadas", "💰 Financeiro": "Financeiro", "📂 Materiais de Estudo": "Materiais de Estudo"}
    menu_aluno = menu_aluno_map.get(menu_aluno_label, "Dashboard")

    if menu_aluno == "Dashboard":
        st.markdown('<div class="main-header">Painel do Aluno</div>', unsafe_allow_html=True)
        st.error("🔴 AULA AO VIVO AGORA: Conversation Class - Travel Tips")
        if st.button("ENTRAR NA AULA (ZOOM)", type="primary"): st.write("Redirecionando para o Zoom...")
        
        st.markdown("<br>", unsafe_allow_html=True)
        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown("""
            <div class="dash-card">
                <div><div class="card-title">Aulas Assistidas</div><div class="card-value">24/30</div></div>
                <div class="card-sub"><span class="trend-up">80%</span> <span class="trend-neutral">Concluído</span></div>
            </div>""", unsafe_allow_html=True)
        with col2:
            st.markdown("""
            <div class="dash-card">
                <div><div class="card-title">Média Geral</div><div class="card-value">8.5</div></div>
                <div class="card-sub"><span class="trend-up">+0.5</span> <span class="trend-neutral">Último mês</span></div>
            </div>""", unsafe_allow_html=True)
        with col3:
            st.markdown("""
            <div class="dash-card">
                <div><div class="card-title">Próxima Prova</div><div class="card-value">15/02</div></div>
                <div class="card-sub"><span style="color:#64748b">Oral Test - Unit 5</span></div>
            </div>""", unsafe_allow_html=True)

    elif menu_aluno == "Minhas Aulas":
        st.markdown('<div class="main-header">Grade Curricular</div>', unsafe_allow_html=True)
        modules = {"Módulo 1: Introdução": ["Aula 1.1 - Hello", "Aula 1.2 - Colors"], "Módulo 2: Verbos": ["Aula 2.1 - To Be", "Aula 2.2 - Can"]}
        for mod, aulas in modules.items():
            with st.expander(mod):
                for aula in aulas: st.checkbox(f"{aula}", value=True)
                st.button(f"Ver Material {mod}", key=mod)

    elif menu_aluno == "Boletim & Frequencia":
        st.markdown('<div class="main-header">Desempenho Acadêmico</div>', unsafe_allow_html=True)
        tab1, tab2 = st.tabs(["Notas", "Presença"])
        aluno_nome = st.session_state["user_name"]
        notas = [g for g in st.session_state["grades"] if g.get("aluno") == aluno_nome and g.get("status") == "Aprovado"]
        with tab1:
            if notas: st.dataframe(pd.DataFrame(notas), use_container_width=True)
            else: st.info("Nenhuma nota lançada.")
        with tab2: st.info("Frequência: 92% de presença.")

    elif menu_aluno == "Mensagens":
        st.markdown('<div class="main-header">Mensagens</div>', unsafe_allow_html=True)
        if not st.session_state["messages"]: st.info("Sem mensagens.")
        for msg in reversed(st.session_state["messages"]):
            with st.container():
                st.markdown(f"""
                <div style="background:white; padding:16px; border-radius:12px; border:1px solid #e2e8f0; margin-bottom:10px;">
                    <div style="font-weight:700; color:#1e3a8a;">{msg['titulo']}</div>
                    <div style="font-size:0.85rem; color:#64748b; margin-bottom:8px;">{msg['data']} | {msg['autor']}</div>
                    <div>{msg['mensagem']}</div>
                </div>
                """, unsafe_allow_html=True)

    elif menu_aluno == "Aulas Gravadas":
        st.markdown('<div class="main-header">Aulas Gravadas</div>', unsafe_allow_html=True)
        if not st.session_state["videos"]: st.info("Sem vídeos.")
        for v in reversed(st.session_state["videos"]):
            with st.expander(f"🎥 {v['titulo']} ({v['data']})"):
                if v['url']: st.video(v['url'])
            
    elif menu_aluno == "Materiais de Estudo":
        st.markdown('<div class="main-header">Materiais</div>', unsafe_allow_html=True)
        if not st.session_state["materials"]: st.info("Sem materiais.")
        for m in reversed(st.session_state["materials"]):
            with st.container():
                st.markdown(f"**{m['titulo']}**")
                st.write(m['descricao'])
                if m['link']: st.markdown(f"[📥 Baixar Arquivo]({m['link']})")
                st.markdown("---")

    elif menu_aluno == "Financeiro":
        st.markdown('<div class="main-header">Financeiro</div>', unsafe_allow_html=True)
        meus = [r for r in st.session_state["receivables"] if r.get("aluno") == st.session_state["user_name"]]
        if meus: st.dataframe(pd.DataFrame(meus), use_container_width=True)
        else: st.info("Financeiro em dia.")

elif st.session_state["role"] in ["Professor", "Coordenador"]:
    perfil = st.session_state["role"]
    with st.sidebar:
        logo_path = get_logo_path()
        if logo_path: st.image(str(logo_path), width=120)
        st.markdown(f"### {st.session_state['user_name']}")
        st.caption(f"Perfil: {perfil}")
        st.markdown("---")
        opts = ["Minhas Turmas", "Diário de Classe", "Mensagens", "Notas", "Aulas Gravadas", "Materiais"] if perfil == "Professor" else ["Dashboard", "Alunos", "Professores", "Turmas", "Financeiro", "Aprovação Notas", "Usuários", "Conteúdos"]
        menu_sel = sidebar_menu("Menu", opts, f"menu_{perfil}")
        st.markdown("---")
        if st.button("Sair"): logout_user()

    st.markdown(f'<div class="main-header">Área do {perfil}: {menu_sel}</div>', unsafe_allow_html=True)
    
    if perfil == "Coordenador":
        if menu_sel == "Dashboard":
            c1, c2, c3 = st.columns(3)
            with c1:
                st.markdown(f"""<div class="dash-card"><div><div class="card-title">Total de Alunos</div><div class="card-value">{len(st.session_state["students"])}</div></div></div>""", unsafe_allow_html=True)
            with c2:
                st.markdown(f"""<div class="dash-card"><div><div class="card-title">Professores</div><div class="card-value">{len(st.session_state["teachers"])}</div></div></div>""", unsafe_allow_html=True)
            with c3:
                st.markdown(f"""<div class="dash-card"><div><div class="card-title">Turmas Ativas</div><div class="card-value">{len(st.session_state["classes"])}</div></div></div>""", unsafe_allow_html=True)
            
        elif menu_sel == "Alunos":
            with st.form("add_student"):
                st.subheader("Novo Aluno")
                c1, c2 = st.columns(2)
                with c1: nome = st.text_input("Nome")
                with c2: mat = st.text_input("Matrícula")
                turma = st.selectbox("Turma", ["Sem Turma"] + class_names())
                if st.form_submit_button("Cadastrar"):
                    st.session_state["students"].append({"nome": nome, "matricula": mat, "turma": turma})
                    st.success("Salvo!")
            st.dataframe(pd.DataFrame(st.session_state["students"]), use_container_width=True)

        elif menu_sel == "Professores":
            with st.form("add_prof"):
                nome = st.text_input("Nome do Professor")
                if st.form_submit_button("Cadastrar"):
                    st.session_state["teachers"].append({"nome": nome})
                    st.success("Salvo!")
            st.dataframe(pd.DataFrame(st.session_state["teachers"]), use_container_width=True)

        elif menu_sel == "Turmas":
            with st.form("add_class"):
                nome = st.text_input("Nome da Turma")
                if st.form_submit_button("Cadastrar"):
                    st.session_state["classes"].append({"nome": nome})
                    st.success("Salvo!")
            st.dataframe(pd.DataFrame(st.session_state["classes"]), use_container_width=True)
            
        elif menu_sel == "Financeiro":
            st.info("Gestão Financeira Completa (Contas a Pagar/Receber)")
            if st.session_state["receivables"]: st.dataframe(pd.DataFrame(st.session_state["receivables"]), use_container_width=True)
            else: st.info("Sem lançamentos.")
                
        elif menu_sel == "Usuários":
            with st.form("new_user"):
                c1, c2, c3 = st.columns(3)
                with c1: u_user = st.text_input("Usuário")
                with c2: u_pass = st.text_input("Senha", type="password")
                with c3: u_role = st.selectbox("Perfil", ["Aluno", "Professor", "Coordenador"])
                if st.form_submit_button("Criar Login"):
                    st.session_state["users"].append({"usuario": u_user, "senha": u_pass, "perfil": u_role})
                    st.success("Criado!")
            st.dataframe(pd.DataFrame(st.session_state["users"]), use_container_width=True)

        elif menu_sel == "Conteúdos":
            st.write("Gestão de Mensagens e Materiais")
            
    elif perfil == "Professor":
        if menu_sel == "Minhas Turmas":
            st.info("Seus horários de aula.")
            st.markdown("""<div class="dash-card"><div><div class="card-title">Próxima Aula</div><div class="card-value">Inglês Teens B1</div><div class="card-sub">14:00 - Sala 01</div></div></div>""", unsafe_allow_html=True)
        elif menu_sel == "Diário de Classe":
            st.write("Realizar chamada.")
        elif menu_sel == "Notas":
             st.write("Lançamento de notas.")