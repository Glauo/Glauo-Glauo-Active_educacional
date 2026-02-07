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
WHATSAPP_NUMBER = "5516996043314" 

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

def create_or_update_login(username, password, role, person_name):
    # Verifica se usuario ja existe
    existing = next((u for u in st.session_state["users"] if u["usuario"] == username), None)
    if existing:
        existing["senha"] = password
        existing["perfil"] = role
        existing["pessoa"] = person_name
    else:
        st.session_state["users"].append({
            "usuario": username,
            "senha": password,
            "perfil": role,
            "pessoa": person_name
        })

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
    st.markdown(f"<h3 style='color:#1e3a8a; font-family:Sora; margin-top:0;'>{title}</h3>", unsafe_allow_html=True)
    if key not in st.session_state:
        st.session_state[key] = options[0]
    for option in options:
        active = st.session_state[key] == option
        if st.button(option, key=f"{key}_{option}", type="primary" if active else "secondary"):
            st.session_state[key] = option
            st.rerun()
    return st.session_state[key]

# ==============================================================================
# CSS DINAMICO
# ==============================================================================

if not st.session_state["logged_in"]:
    st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Manrope:wght@400;600;700;800&family=Sora:wght@400;600;700&display=swap');
        .stApp { background: linear-gradient(135deg, #0f172a 0%, #1e3a8a 50%, #3b82f6 100%); font-family: 'Manrope', sans-serif; }
        header, footer {visibility: hidden;}
        .block-container { padding-top: 5rem; padding-bottom: 5rem; max-width: 1000px; }
        .info-card { background: rgba(255, 255, 255, 0.95); border-radius: 24px; padding: 40px; height: 100%; box-shadow: 0 20px 50px rgba(0,0,0,0.2); color: #1e293b; display: flex; flex-direction: column; justify-content: center; }
        .logo-area { margin-bottom: 24px; }
        .logo-img { max-width: 80px; }
        .info-title { font-family: 'Sora', sans-serif; font-size: 2rem; font-weight: 700; color: #0f172a; line-height: 1.2; margin-bottom: 12px; }
        .info-subtitle { font-size: 1rem; color: #64748b; margin-bottom: 32px; line-height: 1.5; }
        .feature-item { display: flex; align-items: center; gap: 16px; margin-bottom: 20px; }
        .feature-icon-box { width: 48px; height: 48px; background: #eff6ff; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 1.2rem; color: #2563eb; }
        .feature-text { font-weight: 600; color: #334155; font-size: 0.95rem; }
        .feature-sub { font-size: 0.8rem; color: #94a3b8; }
        .whatsapp-button { display: flex; align-items: center; justify-content: center; gap: 10px; background: #22c55e; color: white !important; font-weight: 700; padding: 14px; border-radius: 12px; text-decoration: none; margin-top: 20px; transition: transform 0.2s; box-shadow: 0 4px 12px rgba(34, 197, 94, 0.3); }
        .whatsapp-button:hover { transform: translateY(-2px); opacity: 0.95; }
        div[data-testid="stForm"] { background: #ffffff; border-radius: 24px; padding: 40px; border: none; box-shadow: 0 20px 50px rgba(0,0,0,0.2); }
        .login-header { font-family: 'Sora', sans-serif; font-size: 1.5rem; font-weight: 700; color: #0f172a; margin-bottom: 4px; }
        .login-sub { font-size: 0.9rem; color: #64748b; margin-bottom: 24px; }
        div[data-testid="stForm"] label { font-size: 0.85rem; font-weight: 600; color: #475569; }
        div[data-testid="stForm"] input, div[data-testid="stForm"] select, div[data-testid="stForm"] div[data-baseweb="select"] > div { background-color: #f8fafc !important; border: 1px solid #e2e8f0 !important; border-radius: 12px !important; color: #334155 !important; height: 48px; }
        div[data-testid="stForm"] input:focus { border-color: #3b82f6 !important; box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1) !important; }
        div[data-testid="stForm"] button { background: linear-gradient(to right, #2563eb, #1d4ed8); color: white; border: none; border-radius: 12px; font-weight: 700; padding: 0.75rem 1rem; width: 100%; font-size: 1rem; margin-top: 10px; }
        div[data-testid="stForm"] button:hover { opacity: 0.9; border: none; }
    </style>
    """, unsafe_allow_html=True)
else:
    st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Manrope:wght@400;600;700&family=Sora:wght@500;700&display=swap');
        .stApp { background: #f8fafc; font-family: 'Manrope', sans-serif; }
        .main-header { font-family: 'Sora', sans-serif; font-size: 1.8rem; font-weight: 700; color: #1e3a8a; margin-bottom: 20px; }
        section[data-testid="stSidebar"] { background-color: #ffffff; border-right: 1px solid #e2e8f0; box-shadow: 2px 0 10px rgba(0,0,0,0.02); }
        section[data-testid="stSidebar"] .stButton > button { background-color: transparent; border: none; color: #64748b; text-align: left; font-weight: 600; padding: 0.6rem 1rem; width: 100%; border-radius: 8px; transition: all 0.2s; margin-bottom: 4px; }
        section[data-testid="stSidebar"] .stButton > button:hover { color: #1e3a8a; background-color: #f1f5f9; transform: translateX(4px); }
        section[data-testid="stSidebar"] .stButton > button[kind="primary"] { background: linear-gradient(90deg, #eff6ff 0%, #ffffff 100%); color: #1d4ed8; border-left: 4px solid #1d4ed8; border-radius: 4px 8px 8px 4px; box-shadow: 0 2px 5px rgba(29, 78, 216, 0.05); }
        .dash-card { background: white; padding: 24px; border-radius: 16px; border: 1px solid #e2e8f0; box-shadow: 0 4px 20px rgba(0,0,0,0.03); transition: transform 0.2s, box-shadow 0.2s; height: 100%; display: flex; flex-direction: column; justify-content: space-between; }
        .dash-card:hover { transform: translateY(-2px); box-shadow: 0 10px 25px rgba(0,0,0,0.06); border-color: #cbd5e1; }
        .card-title { font-size: 0.9rem; color: #64748b; font-weight: 600; margin-bottom: 8px; text-transform: uppercase; letter-spacing: 0.5px; }
        .card-value { font-family: 'Sora', sans-serif; font-size: 2rem; font-weight: 700; color: #0f172a; }
        .card-sub { font-size: 0.85rem; margin-top: 8px; display: flex; align-items: center; gap: 6px; }
        .trend-up { color: #10b981; background: #ecfdf5; padding: 2px 8px; border-radius: 99px; font-weight: 700; }
        .trend-neutral { color: #64748b; }
        div[data-testid="stDataFrame"] { background: white; padding: 16px; border-radius: 12px; border: 1px solid #e2e8f0; box-shadow: 0 2px 8px rgba(0,0,0,0.02); margin-bottom: 16px; }
        div[data-testid="stForm"] { background: white; padding: 30px; border-radius: 16px; border: 1px solid #e2e8f0; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05); margin-bottom: 20px; }
        input, textarea, select { border-radius: 8px !important; border: 1px solid #cbd5e1 !important; }
        input:focus { border-color: #3b82f6 !important; box-shadow: 0 0 0 2px rgba(59, 130, 246, 0.1) !important; }
        button[kind="primary"] { background: #1e3a8a; border-radius: 8px; }
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
        st.markdown(f"""
<div class="info-card">
<div class="logo-area">{logo_html}</div>
<div class="info-title">Sistema Educacional<br>Ativo</div>
<div class="info-subtitle">Gestão acadêmica, comunicação e conteúdo pedagógico em um único lugar.</div>
<div class="feature-item"><div class="feature-icon-box">💬</div><div><div class="feature-text">Mensagens Diretas</div><div class="feature-sub">Comunicação rápida com alunos e turmas.</div></div></div>
<div class="feature-item"><div class="feature-icon-box">🎥</div><div><div class="feature-text">Aulas Gravadas</div><div class="feature-sub">Conteúdo organizado e acessível 24h.</div></div></div>
<div class="feature-item"><div class="feature-icon-box">💲</div><div><div class="feature-text">Financeiro Simples</div><div class="feature-sub">Controle de matrículas e pagamentos.</div></div></div>
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
            if unidade_sel == "Outra": unidade = st.text_input("Digite o nome da unidade")
            else: unidade = unidade_sel
            usuario = st.text_input("Usuário", placeholder="Seu usuário de acesso")
            senha = st.text_input("Senha", type="password", placeholder="Sua senha")
            entrar = st.form_submit_button("Entrar no Sistema")
        
        if entrar:
            user = find_user(usuario.strip())
            if not usuario.strip() or not senha.strip(): st.error("⚠️ Informe usuário e senha.")
            elif not user or user.get("senha") != senha.strip(): st.error("⚠️ Usuário ou senha inválidos.")
            else:
                perfil_conta = user.get("perfil", "")
                if role not in allowed_portals(perfil_conta): st.error(f"⚠️ Este usuário não tem permissão de {role}.")
                else:
                    display_name = user.get("pessoa") or usuario.strip()
                    login_user(role, display_name, str(unidade).strip(), perfil_conta)

# ==============================================================================
# ALUNO
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
        link_aula = "https://zoom.us/join"
        turma_aluno = next((s["turma"] for s in st.session_state["students"] if s["nome"] == st.session_state["user_name"]), None)
        if turma_aluno:
            turma_obj = next((c for c in st.session_state["classes"] if c["nome"] == turma_aluno), None)
            if turma_obj and "link_zoom" in turma_obj: link_aula = turma_obj["link_zoom"]
        st.error(f"🔴 AULA AO VIVO AGORA")
        st.link_button("ENTRAR NA AULA (ZOOM)", link_aula, type="primary")
        st.markdown("<br>", unsafe_allow_html=True)
        col1, col2, col3 = st.columns(3)
        with col1: st.markdown("""<div class="dash-card"><div><div class="card-title">Aulas Assistidas</div><div class="card-value">24/30</div></div><div class="card-sub"><span class="trend-up">80%</span> <span class="trend-neutral">Concluído</span></div></div>""", unsafe_allow_html=True)
        with col2: st.markdown("""<div class="dash-card"><div><div class="card-title">Média Geral</div><div class="card-value">8.5</div></div><div class="card-sub"><span class="trend-up">+0.5</span> <span class="trend-neutral">Último mês</span></div></div>""", unsafe_allow_html=True)
        with col3: st.markdown("""<div class="dash-card"><div><div class="card-title">Próxima Prova</div><div class="card-value">15/02</div></div><div class="card-sub"><span style="color:#64748b">Oral Test - Unit 5</span></div></div>""", unsafe_allow_html=True)

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
                st.markdown(f"""<div style="background:white; padding:16px; border-radius:12px; border:1px solid #e2e8f0; margin-bottom:10px;"><div style="font-weight:700; color:#1e3a8a;">{msg['titulo']}</div><div style="font-size:0.85rem; color:#64748b; margin-bottom:8px;">{msg['data']} | {msg['autor']}</div><div>{msg['mensagem']}</div></div>""", unsafe_allow_html=True)

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

# ==============================================================================
# PROFESSOR
# ==============================================================================
elif st.session_state["role"] == "Professor":
    with st.sidebar:
        logo_path = get_logo_path()
        if logo_path: st.image(str(logo_path), width=120)
        st.markdown(f"### {st.session_state['user_name']}")
        st.caption("Perfil: Docente")
        st.markdown("---")
        menu_prof_label = sidebar_menu("Gestão", ["👥 Minhas Turmas", "📝 Diário de Classe", "💬 Mensagens", "📊 Notas", "🎥 Aulas Gravadas", "📂 Materiais"], "menu_prof")
        st.markdown("---")
        if st.button("Sair"): logout_user()

    menu_prof_map = {"👥 Minhas Turmas": "Minhas Turmas", "📝 Diário de Classe": "Diario", "💬 Mensagens": "Mensagens", "📊 Notas": "Notas", "🎥 Aulas Gravadas": "Aulas", "📂 Materiais": "Materiais"}
    menu_prof = menu_prof_map.get(menu_prof_label, "Minhas Turmas")

    if menu_prof == "Minhas Turmas":
        st.markdown('<div class="main-header">Painel do Professor</div>', unsafe_allow_html=True)
        minhas_turmas = [c for c in st.session_state["classes"] if st.session_state["user_name"] in str(c.get("professor", ""))]
        if not minhas_turmas: minhas_turmas = st.session_state["classes"]
        if not minhas_turmas: st.info("Nenhuma turma encontrada.")
        else:
            col_control, col_card = st.columns([1, 1], gap="large")
            with col_control:
                st.markdown("### 📡 Configurar Aula Ao Vivo")
                with st.form("config_aula"):
                    turma_selecionada_nome = st.selectbox("Selecione a Turma", [t["nome"] for t in minhas_turmas])
                    turma_atual = next(t for t in minhas_turmas if t["nome"] == turma_selecionada_nome)
                    link_atual = turma_atual.get("link_zoom", "")
                    novo_link = st.text_input("Cole o Link do Zoom aqui", value=link_atual, placeholder="https://zoom.us/...")
                    if st.form_submit_button("Salvar e Enviar para Alunos"):
                        turma_atual["link_zoom"] = novo_link
                        st.success(f"Link enviado com sucesso para a turma {turma_selecionada_nome}!")
                        st.rerun()
            with col_card:
                st.markdown("### 👀 Visualização")
                link_final = turma_atual.get("link_zoom", "#")
                texto_botao = "Iniciar Aula (Zoom)" if link_final and link_final != "#" else "Aguardando Link..."
                disabled_state = False if link_final and link_final != "#" else True
                st.markdown(f"""<div class="dash-card"><div><div class="card-title" style="color:#1d4ed8;">Turma Selecionada</div><div class="card-value">{turma_atual['nome']}</div></div><div class="card-sub">📅 {turma_atual.get('dias', 'Horário a definir')}</div><div style="margin-top:15px; font-size:0.9rem; color:#64748b;">Link atual: <a href="{link_final}" target="_blank">{link_final[:30]}...</a></div></div>""", unsafe_allow_html=True)
                st.markdown("<br>", unsafe_allow_html=True)
                if not disabled_state: st.link_button(texto_botao, link_final, type="primary")
                else: st.warning("⚠️ Cadastre o link ao lado para liberar o botão.")

    elif menu_prof == "Diario":
        st.markdown('<div class="main-header">Diário de Classe</div>', unsafe_allow_html=True)
        with st.form("chamada"):
            c1, c2 = st.columns(2)
            with c1: turma = st.selectbox("Turma", ["Inglês Teens B1", "Adults Conversation"])
            with c2: data = st.date_input("Data", datetime.date.today())
            st.markdown("---")
            df_alunos = pd.DataFrame([{"Aluno": "Ana Clara", "Presente": True}, {"Aluno": "Bruno Souza", "Presente": True}, {"Aluno": "Carlos Eduardo", "Presente": False}])
            edited_df = st.data_editor(df_alunos, num_rows="dynamic", use_container_width=True)
            st.form_submit_button("Salvar Chamada")

    elif menu_prof == "Mensagens":
        st.markdown('<div class="main-header">Enviar Mensagem</div>', unsafe_allow_html=True)
        with st.form("form_msg"):
            st.text_input("Título")
            st.text_area("Mensagem")
            st.selectbox("Turma", ["Todas", "Teens B1", "Adults"])
            st.form_submit_button("Enviar")

    elif menu_prof == "Notas":
        st.markdown('<div class="main-header">Lançamento de Notas</div>', unsafe_allow_html=True)
        with st.form("form_notas"):
            c1, c2 = st.columns(2)
            with c1: st.text_input("Aluno")
            with c2: st.selectbox("Turma", class_names() or ["Sem Turmas"])
            c3, c4 = st.columns(2)
            with c3: st.number_input("Nota Trabalho", 0.0, 10.0)
            with c4: st.number_input("Nota Presença", 0.0, 10.0)
            st.selectbox("Situação", ["Aprovado", "Reprovado"])
            st.form_submit_button("Enviar para Aprovação")

    elif menu_prof == "Aulas":
        st.markdown('<div class="main-header">Cadastrar Aula Gravada</div>', unsafe_allow_html=True)
        with st.form("new_vid"):
            st.text_input("Título")
            st.text_input("Link (YouTube)")
            st.selectbox("Turma", ["Teens B1", "Adults"])
            st.form_submit_button("Cadastrar")

    elif menu_prof == "Materiais":
        st.markdown('<div class="main-header">Cadastrar Material</div>', unsafe_allow_html=True)
        with st.form("new_mat"):
            st.text_input("Título")
            st.text_area("Descrição")
            st.text_input("Link (Drive)")
            st.form_submit_button("Cadastrar")

# ==============================================================================
# COORDENADOR
# ==============================================================================
elif st.session_state["role"] == "Coordenador":

    with st.sidebar:
        logo_path = get_logo_path()
        if logo_path: st.image(str(logo_path), width=120)
        st.markdown(f"### {st.session_state['user_name']}")
        st.caption("Perfil: Coordenação")
        st.markdown("---")
        menu_coord_label = sidebar_menu("Administração", ["📊 Dashboard", "🔗 Links Ao Vivo", "🧑‍🎓 Alunos", "👩‍🏫 Professores", "🔐 Usuários", "🏫 Turmas", "💰 Financeiro", "📝 Aprovação Notas", "📚 Conteúdos"], "menu_coord")
        st.markdown("---")
        if st.button("Sair"): logout_user()

    menu_coord_map = {"📊 Dashboard": "Dashboard", "🔗 Links Ao Vivo": "Links", "🧑‍🎓 Alunos": "Alunos", "👩‍🏫 Professores": "Professores", "🔐 Usuários": "Usuarios", "🏫 Turmas": "Turmas", "💰 Financeiro": "Financeiro", "📝 Aprovação Notas": "Notas", "📚 Conteúdos": "Conteudos"}
    menu_coord = menu_coord_map.get(menu_coord_label, "Dashboard")

if menu_coord == "Alunos":
    st.markdown('<div class="main-header">Gestão Geral de Alunos</div>', unsafe_allow_html=True)
    
    # Aba de visualização global
    if st.session_state["students"]:
        df_completo = pd.DataFrame(st.session_state["students"])
        st.write("### Todos os Alunos Cadastrados")
        st.dataframe(df_completo, use_container_width=True) # Coordenador vê tudo 
    else:
        st.info("Nenhum aluno encontrado na base de dados.")
        logo_path = get_logo_path()
        if logo_path: st.image(str(logo_path), width=120)
        st.markdown(f"### {st.session_state['user_name']}")
        st.caption("Perfil: Coordenação")
        st.markdown("---")
        menu_coord_label = sidebar_menu("Administração", ["📊 Dashboard", "🔗 Links Ao Vivo", "🧑‍🎓 Alunos", "👩‍🏫 Professores", "🔐 Usuários", "🏫 Turmas", "💰 Financeiro", "📝 Aprovação Notas", "📚 Conteúdos"], "menu_coord")
        st.markdown("---")
        if st.button("Sair"): logout_user()

    menu_coord_map = {"📊 Dashboard": "Dashboard", "🔗 Links Ao Vivo": "Links", "🧑‍🎓 Alunos": "Alunos", "👩‍🏫 Professores": "Professores", "🔐 Usuários": "Usuarios", "🏫 Turmas": "Turmas", "💰 Financeiro": "Financeiro", "📝 Aprovação Notas": "Notas", "📚 Conteúdos": "Conteudos"}
    menu_coord = menu_coord_map.get(menu_coord_label, "Dashboard")

    if menu_coord == "Dashboard":
        st.markdown('<div class="main-header">Painel do Coordenador</div>', unsafe_allow_html=True)
        c1, c2, c3 = st.columns(3)
        with c1: st.markdown(f"""<div class="dash-card"><div><div class="card-title">Total de Alunos</div><div class="card-value">{len(st.session_state["students"])}</div></div><div class="card-sub"><span class="trend-up">Ativos</span></div></div>""", unsafe_allow_html=True)
        with c2: st.markdown(f"""<div class="dash-card"><div><div class="card-title">Professores</div><div class="card-value">{len(st.session_state["teachers"])}</div></div></div>""", unsafe_allow_html=True)
        with c3: st.markdown(f"""<div class="dash-card"><div><div class="card-title">Turmas</div><div class="card-value">{len(st.session_state["classes"])}</div></div></div>""", unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)
        total_rec = sum(parse_money(i["valor"]) for i in st.session_state["receivables"])
        total_pag = sum(parse_money(i["valor"]) for i in st.session_state["payables"])
        saldo = total_rec - total_pag
        c4, c5, c6 = st.columns(3)
        with c4: st.markdown(f"""<div class="dash-card"><div><div class="card-title">A Receber</div><div class="card-value" style="color:#2563eb;">{format_money(total_rec)}</div></div></div>""", unsafe_allow_html=True)
        with c5: st.markdown(f"""<div class="dash-card"><div><div class="card-title">A Pagar</div><div class="card-value" style="color:#dc2626;">{format_money(total_pag)}</div></div></div>""", unsafe_allow_html=True)
        with c6:
             color = "#16a34a" if saldo >= 0 else "#dc2626"
             st.markdown(f"""<div class="dash-card"><div><div class="card-title">Saldo Atual</div><div class="card-value" style="color:{color};">{format_money(saldo)}</div></div></div>""", unsafe_allow_html=True)

    elif menu_coord == "Links":
        st.markdown('<div class="main-header">🔗 Gerenciar Links Ao Vivo</div>', unsafe_allow_html=True)
        st.info("Aqui você define o link da aula ao vivo para cada turma. Esse link aparecerá automaticamente para todos os alunos.")
        turmas_disponiveis = [t["nome"] for t in st.session_state["classes"]]
        if not turmas_disponiveis:
            st.warning("Cadastre turmas primeiro na aba 'Turmas'.")
        else:
            with st.form("gerenciar_links"):
                turma_sel = st.selectbox("Selecione a Turma", turmas_disponiveis)
                turma_obj = next((t for t in st.session_state["classes"] if t["nome"] == turma_sel), None)
                link_atual = turma_obj.get("link_zoom", "") if turma_obj else ""
                novo_link = st.text_input("Link da Aula Ao Vivo (Zoom/Meet/Teams)", value=link_atual)
                if st.form_submit_button("Salvar Link para a Turma"):
                    if turma_obj:
                        turma_obj["link_zoom"] = novo_link
                        st.success(f"Link atualizado com sucesso para a turma {turma_sel}!")

    # --- ALUNOS (CADASTRO COMPLETO + LOGIN) ---
    elif menu_coord == "Alunos":
        st.markdown('<div class="main-header">Gestão de Alunos</div>', unsafe_allow_html=True)
        tab1, tab2 = st.tabs(["➕ Cadastro Completo", "✏️ Gerenciar / Excluir"])
        
        with tab1:
            with st.form("add_student_full"):
                st.markdown("### 👤 Dados Pessoais")
                c1, c2, c3 = st.columns(3)
                with c1: nome = st.text_input("Nome Completo *")
                with c2: 
                    idade = st.number_input("Idade *", min_value=1, max_value=120, step=1)
                    dt_nasc = st.date_input("Data de Nascimento", datetime.date(2000, 1, 1), format="DD/MM/YYYY")
                with c3: celular = st.text_input("Celular/WhatsApp *")
                
                c4, c5, c6 = st.columns(3)
                with c4: email = st.text_input("E-mail do Aluno *")
                with c5: rg = st.text_input("RG")
                with c6: cpf = st.text_input("CPF")
                
                st.divider()
                st.markdown("### 🔐 Acesso ao Sistema")
                clog1, clog2 = st.columns(2)
                with clog1: login_user_aluno = st.text_input("Criar Login do Aluno")
                with clog2: login_pass_aluno = st.text_input("Criar Senha do Aluno", type="password")

                st.divider()
                st.markdown("### 📍 Endereço")
                ce1, ce2, ce3 = st.columns(3)
                with ce1: cep = st.text_input("CEP")
                with ce2: cidade = st.text_input("Cidade")
                with ce3: bairro = st.text_input("Bairro")
                ce4, ce5 = st.columns([3, 1])
                with ce4: rua = st.text_input("Rua")
                with ce5: numero = st.text_input("Número")
                
                ce6, ce7 = st.columns(2)
                with ce6: natal = st.text_input("Cidade Natal")
                with ce7: pais = st.text_input("País de Origem", value="Brasil")

                st.divider()
                st.markdown("### 🎓 Turma")
                turma = st.selectbox("Vincular à Turma", ["Sem Turma"] + class_names())
                
                st.divider()
                st.markdown("### 👨‍👩‍👦 Responsável Legal / Financeiro")
                st.caption("Obrigatório para menores de 18 anos.")
                cr1, cr2 = st.columns(2)
                with cr1: resp_nome = st.text_input("Nome do Responsável")
                with cr2: resp_cpf = st.text_input("CPF do Responsável")
                cr3, cr4 = st.columns(2)
                with cr3: resp_cel = st.text_input("Celular do Responsável")
                with cr4: resp_email = st.text_input("E-mail do Responsável")
                
                if st.form_submit_button("Cadastrar Aluno e Criar Login"):
                    if idade < 18 and (not resp_nome or not resp_cpf):
                        st.error("⛔ ERRO: Aluno menor de idade! Preencha o Responsável.")
                    elif not nome or not email:
                        st.error("⛔ ERRO: Nome e E-mail obrigatórios.")
                    else:
                        novo_aluno = {
                            "nome": nome, "idade": idade, "nascimento": dt_nasc.strftime("%d/%m/%Y"),
                            "celular": celular, "email": email, "rg": rg, "cpf": cpf,
                            "cidade_natal": natal, "pais": pais, "cep": cep, "cidade": cidade, 
                            "bairro": bairro, "rua": rua, "numero": numero, "turma": turma,
                            "responsavel": {"nome": resp_nome, "cpf": resp_cpf, "celular": resp_cel, "email": resp_email}
                        }
                        st.session_state["students"].append(novo_aluno)
                        
                        # CRIA LOGIN AUTOMATICO
                        if login_user_aluno and login_pass_aluno:
                            create_or_update_login(login_user_aluno, login_pass_aluno, "Aluno", nome)
                            st.toast("Login criado com sucesso!")
                        
                        dest = resp_email if idade < 18 else email
                        st.success(f"✅ Aluno cadastrado! Kit Boas-vindas enviado para {dest}.")
        
        with tab2:
            if not st.session_state["students"]: st.info("Nenhum aluno.")
            else:
                aluno_nomes = [s["nome"] for s in st.session_state["students"]]
                aluno_sel = st.selectbox("Selecione o Aluno", aluno_nomes)
                aluno_obj = next((s for s in st.session_state["students"] if s["nome"] == aluno_sel), None)
                if aluno_obj:
                    with st.form("edit_student"):
                        st.subheader(f"Editando: {aluno_obj['nome']}")
                        new_nome = st.text_input("Nome", value=aluno_obj["nome"])
                        new_cel = st.text_input("Celular", value=aluno_obj.get("celular", ""))
                        new_turma = st.selectbox("Turma", ["Sem Turma"] + class_names())
                        new_email = st.text_input("Email", value=aluno_obj.get("email", ""))
                        c_edit, c_del = st.columns([1, 1])
                        with c_edit:
                            if st.form_submit_button("💾 Salvar Alterações"):
                                aluno_obj["nome"] = new_nome
                                aluno_obj["celular"] = new_cel
                                aluno_obj["turma"] = new_turma
                                aluno_obj["email"] = new_email
                                st.success("Atualizado!")
                                st.rerun()
                        with c_del:
                            if st.form_submit_button("🗑️ EXCLUIR ALUNO", type="primary"):
                                st.session_state["students"].remove(aluno_obj)
                                st.error("Excluído.")
                                st.rerun()

    # --- PROFESSORES (CADASTRO + LOGIN) ---
    elif menu_coord == "Professores":
        st.markdown('<div class="main-header">Gestão de Professores</div>', unsafe_allow_html=True)
        tab1, tab2 = st.tabs(["➕ Novo Professor", "✏️ Gerenciar / Excluir"])
        with tab1:
            with st.form("add_prof"):
                c1, c2 = st.columns(2)
                with c1: nome = st.text_input("Nome Completo")
                with c2: area = st.text_input("Área de Ensino")
                st.divider()
                st.markdown("### 🔐 Acesso ao Sistema")
                cp1, cp2 = st.columns(2)
                with cp1: login_user_prof = st.text_input("Criar Login do Professor")
                with cp2: login_pass_prof = st.text_input("Criar Senha do Professor", type="password")
                
                if st.form_submit_button("Cadastrar Professor e Criar Login"):
                    st.session_state["teachers"].append({"nome": nome, "area": area})
                    if login_user_prof and login_pass_prof:
                        create_or_update_login(login_user_prof, login_pass_prof, "Professor", nome)
                        st.toast("Login de professor criado!")
                    st.success("Professor salvo!")
        with tab2:
            if not st.session_state["teachers"]: st.info("Nenhum professor.")
            else:
                prof_nomes = [t["nome"] for t in st.session_state["teachers"]]
                prof_sel = st.selectbox("Selecione o Professor", prof_nomes)
                prof_obj = next((t for t in st.session_state["teachers"] if t["nome"] == prof_sel), None)
                if prof_obj:
                    with st.form("edit_prof"):
                        new_nome = st.text_input("Nome", value=prof_obj["nome"])
                        new_area = st.text_input("Área", value=prof_obj.get("area", ""))
                        c_edit, c_del = st.columns([1, 1])
                        with c_edit:
                            if st.form_submit_button("💾 Salvar Alterações"):
                                prof_obj["nome"] = new_nome
                                prof_obj["area"] = new_area
                                st.success("Atualizado!")
                                st.rerun()
                        with c_del:
                            if st.form_submit_button("🗑️ EXCLUIR PROFESSOR", type="primary"):
                                st.session_state["teachers"].remove(prof_obj)
                                st.error("Excluído.")
                                st.rerun()

    # --- TURMAS (GERENCIAR/EXCLUIR) ---
    elif menu_coord == "Turmas":
        st.markdown('<div class="main-header">Gestão de Turmas</div>', unsafe_allow_html=True)
        tab1, tab2 = st.tabs(["➕ Nova Turma", "✏️ Gerenciar / Excluir"])
        
        with tab1:
            with st.form("add_class"):
                c1, c2 = st.columns(2)
                with c1: nome = st.text_input("Nome da Turma")
                with c2: prof = st.selectbox("Professor", ["Selecione"] + teacher_names())
                c3, c4 = st.columns(2)
                with c3: dias = st.text_input("Dias e Horários")
                with c4: link = st.text_input("Link do Zoom (Inicial)")
                if st.form_submit_button("Cadastrar Turma"):
                    st.session_state["classes"].append({"nome": nome, "professor": prof, "dias": dias, "link_zoom": link})
                    st.success("Turma salva!")
        
        with tab2:
            if not st.session_state["classes"]: st.info("Nenhuma turma cadastrada.")
            else:
                turma_nomes = [t["nome"] for t in st.session_state["classes"]]
                turma_sel = st.selectbox("Selecione a Turma", turma_nomes)
                turma_obj = next((t for t in st.session_state["classes"] if t["nome"] == turma_sel), None)
                
                if turma_obj:
                    with st.form("edit_class"):
                        st.subheader(f"Editando: {turma_obj['nome']}")
                        t_nome = st.text_input("Nome", value=turma_obj["nome"])
                        t_prof = st.selectbox("Professor", teacher_names(), index=teacher_names().index(turma_obj["professor"]) if turma_obj["professor"] in teacher_names() else 0)
                        t_dias = st.text_input("Dias/Horários", value=turma_obj.get("dias", ""))
                        
                        c_edit, c_del = st.columns([1, 1])
                        with c_edit:
                            if st.form_submit_button("💾 Salvar Alterações"):
                                turma_obj["nome"] = t_nome
                                turma_obj["professor"] = t_prof
                                turma_obj["dias"] = t_dias
                                st.success("Turma atualizada!")
                                st.rerun()
                        with c_del:
                            if st.form_submit_button("🗑️ EXCLUIR TURMA", type="primary"):
                                st.session_state["classes"].remove(turma_obj)
                                st.error("Turma excluída.")
                                st.rerun()

    elif menu_coord == "Financeiro":
        st.markdown('<div class="main-header">Financeiro</div>', unsafe_allow_html=True)
        tab1, tab2 = st.tabs(["Contas a Receber", "Contas a Pagar"])
        with tab1:
            with st.form("add_rec"):
                st.markdown("### Lançar Recebimento")
                c1, c2 = st.columns(2)
                with c1: desc = st.text_input("Descrição (Ex: Mensalidade)")
                with c2: val = st.text_input("Valor (Ex: 150,00)")
                aluno = st.selectbox("Aluno", [s["nome"] for s in st.session_state["students"]])
                if st.form_submit_button("Lançar"):
                    add_receivable(aluno, desc, val, datetime.date.today(), "Boleto", "Mensalidade")
                    st.success("Lançado!")
            st.dataframe(pd.DataFrame(st.session_state["receivables"]), use_container_width=True)
        with tab2:
            with st.form("add_pag"):
                st.markdown("### Lançar Despesa")
                c1, c2 = st.columns(2)
                with c1: desc = st.text_input("Descrição")
                with c2: val = st.text_input("Valor")
                forn = st.text_input("Fornecedor")
                if st.form_submit_button("Lançar"):
                    st.session_state["payables"].append({"descricao": desc, "valor": val, "fornecedor": forn})
                    st.success("Lançado!")
            st.dataframe(pd.DataFrame(st.session_state["payables"]), use_container_width=True)

    elif menu_coord == "Notas":
        st.markdown('<div class="main-header">Aprovação de Notas</div>', unsafe_allow_html=True)
        pendentes = [g for g in st.session_state["grades"] if g.get("status") == "Pendente"]
        if pendentes:
            st.dataframe(pd.DataFrame(pendentes), use_container_width=True)
            if st.button("Aprovar Todas as Pendentes", type="primary"):
                for g in st.session_state["grades"]:
                    if g.get("status") == "Pendente": g["status"] = "Aprovado"
                st.success("Notas aprovadas!")
                st.rerun()
        else:
            st.info("Nenhuma nota pendente.")

    elif menu_coord == "Usuarios":
        st.markdown('<div class="main-header">Controle de Usuários (Login)</div>', unsafe_allow_html=True)
        tab1, tab2 = st.tabs(["➕ Novo Usuário", "✏️ Gerenciar / Excluir"])
        with tab1:
            with st.form("new_user"):
                c1, c2, c3 = st.columns(3)
                with c1: u_user = st.text_input("Usuário")
                with c2: u_pass = st.text_input("Senha", type="password")
                with c3: u_role = st.selectbox("Perfil", ["Aluno", "Professor", "Coordenador"])
                if st.form_submit_button("Criar Acesso"):
                    st.session_state["users"].append({"usuario": u_user, "senha": u_pass, "perfil": u_role})
                    st.success("Usuário criado!")
        with tab2:
            if not st.session_state["users"]: st.info("Nenhum usuário cadastrado.")
            else:
                user_list = [u["usuario"] for u in st.session_state["users"]]
                user_sel = st.selectbox("Selecione o Usuário", user_list)
                user_obj = next((u for u in st.session_state["users"] if u["usuario"] == user_sel), None)
                if user_obj:
                    with st.form("edit_user"):
                        new_user = st.text_input("Usuário (Login)", value=user_obj["usuario"])
                        new_pass = st.text_input("Nova Senha (deixe igual para manter)", value=user_obj["senha"])
                        new_role = st.selectbox("Perfil", ["Aluno", "Professor", "Coordenador"], index=["Aluno", "Professor", "Coordenador"].index(user_obj["perfil"]) if user_obj["perfil"] in ["Aluno", "Professor", "Coordenador"] else 0)
                        c_edit, c_del = st.columns([1, 1])
                        with c_edit:
                            if st.form_submit_button("💾 Salvar Alterações"):
                                user_obj["usuario"] = new_user
                                user_obj["senha"] = new_pass
                                user_obj["perfil"] = new_role
                                st.success("Usuário atualizado!")
                                st.rerun()
                        with c_del:
                            if st.form_submit_button("🗑️ EXCLUIR USUÁRIO", type="primary"):
                                if user_obj["usuario"] == "admin": st.error("Não é possível excluir o Admin principal.")
                                else:
                                    st.session_state["users"].remove(user_obj)
                                    st.success("Usuário excluído.")
                                    st.rerun()
    
    elif menu_coord == "Conteudos":
        st.markdown('<div class="main-header">Conteúdos</div>', unsafe_allow_html=True)
        st.write("Use esta área para gerenciar mensagens globais e materiais pedagógicos.")