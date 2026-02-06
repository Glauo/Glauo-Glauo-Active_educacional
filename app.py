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

# --- ARQUIVOS DE DADOS (PERSISTENCIA) ---
USERS_FILE = Path("users.json")
MESSAGES_FILE = Path("messages.json")
VIDEOS_FILE = Path("videos.json")
MATERIALS_FILE = Path("materials.json")
GRADES_FILE = Path("grades.json")
FINANCIAL_FILE = Path("financial.json")

WHATSAPP_NUMBER = "5516996043314" 

# --- FUNCOES DE UTILIDADE (LOAD/SAVE) ---
def get_logo_path():
    candidates = [Path("image_8fc66d.png"), Path("logo_active2.png"), Path("logo.png")]
    for path in candidates:
        if path.exists():
            return path
    return None

def load_data(path):
    if path.exists():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            return data if isinstance(data, list) else []
        except Exception: return []
    return []

def save_data(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

def load_financial():
    if FINANCIAL_FILE.exists():
        try:
            data = json.loads(FINANCIAL_FILE.read_text(encoding="utf-8"))
            return data.get("receivables", []), data.get("payables", [])
        except: return [], []
    return [], []

def save_financial():
    data = {
        "receivables": st.session_state["receivables"],
        "payables": st.session_state["payables"]
    }
    FINANCIAL_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

def ensure_admin_user():
    users = load_data(USERS_FILE)
    if not any(u.get("usuario") == ADMIN_USERNAME for u in users):
        users.append({
            "usuario": ADMIN_USERNAME,
            "senha": ADMIN_PASSWORD,
            "perfil": "Admin",
            "pessoa": "Administrador",
        })
    return users

def create_or_update_login(username, password, role, person_name):
    users = st.session_state["users"]
    # Remove se ja existir para atualizar
    users = [u for u in users if u["usuario"] != username]
    users.append({"usuario": username, "senha": password, "perfil": role, "pessoa": person_name})
    st.session_state["users"] = users
    save_data(USERS_FILE, users)

def find_user(username):
    # Busca usuario no estado atual
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

def allowed_portals(profile):
    # Define quem pode acessar o que
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
    if key not in st.session_state: st.session_state[key] = options[0]
    for option in options:
        active = st.session_state[key] == option
        if st.button(option, key=f"{key}_{option}", type="primary" if active else "secondary"):
            st.session_state[key] = option
            st.rerun()
    return st.session_state[key]
# ==============================================================================
# CSS DINAMICO
# ==============================================================================
CSS_GLOBAL = """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Manrope:wght@400;600;700;800&family=Sora:wght@400;600;700&display=swap');
    .stApp { background: #f8fafc; font-family: 'Manrope', sans-serif; }
    .main-header { font-family: 'Sora', sans-serif; font-size: 1.8rem; font-weight: 700; color: #1e3a8a; margin-bottom: 20px; }
    .dash-card { background: white; padding: 24px; border-radius: 16px; border: 1px solid #e2e8f0; box-shadow: 0 4px 20px rgba(0,0,0,0.03); }
    div[data-testid="stDataFrame"] { background: white; padding: 16px; border-radius: 12px; border: 1px solid #e2e8f0; margin-bottom: 16px; }
    div[data-testid="stForm"] { background: white; padding: 30px; border-radius: 16px; border: 1px solid #e2e8f0; margin-bottom: 20px; }
    button[kind="primary"] { background: #1e3a8a; border-radius: 8px; }
    
    /* Login CSS Especifico */
    .login-bg { background: linear-gradient(135deg, #0f172a 0%, #1e3a8a 50%, #3b82f6 100%); }
    .info-card { background: rgba(255, 255, 255, 0.95); border-radius: 24px; padding: 40px; height: 100%; box-shadow: 0 20px 50px rgba(0,0,0,0.2); }
    .whatsapp-button { display: flex; align-items: center; justify-content: center; gap: 10px; background: #22c55e; color: white !important; font-weight: 700; padding: 14px; border-radius: 12px; text-decoration: none; margin-top: 20px; }
</style>
"""
st.markdown(CSS_GLOBAL, unsafe_allow_html=True)

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
    # Aplica fundo de login
    st.markdown("""<style>.stApp {background: linear-gradient(135deg, #0f172a 0%, #1e3a8a 50%, #3b82f6 100%);}</style>""", unsafe_allow_html=True)
    
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
            unidade = st.selectbox("Unidade", ["Matriz", "Unidade Centro", "Unidade Norte", "Outra"])
            if unidade == "Outra": unidade = st.text_input("Nome da Unidade")
            user_input = st.text_input("Usuário")
            pass_input = st.text_input("Senha", type="password")
            if st.form_submit_button("Entrar"):
                # Procura usuario
                u_obj = next((u for u in st.session_state["users"] if u["usuario"] == user_input), None)
                if not u_obj or u_obj["senha"] != pass_input:
                    st.error("Usuário ou senha inválidos.")
                elif role not in allowed_portals(u_obj.get("perfil", "")):
                    st.error(f"Sem permissão de {role}.")
                else:
                    login_user(role, u_obj.get("pessoa", user_input), str(unidade), u_obj.get("perfil"))

# ==============================================================================
# DASHBOARD: ALUNO
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
        # Logica do Link Zoom
        link = "https://zoom.us/join"
        meu_cadastro = next((s for s in st.session_state["students"] if s["nome"] == st.session_state["user_name"]), None)
        if meu_cadastro:
            minha_turma = next((c for c in st.session_state["classes"] if c["nome"] == meu_cadastro.get("turma")), None)
            if minha_turma and "link_zoom" in minha_turma: link = minha_turma["link_zoom"]
        
        st.error("🔴 AULA AO VIVO")
        st.link_button("ENTRAR NA AULA (ZOOM)", link, type="primary")
        
        c1, c2 = st.columns(2)
        c1.markdown("""<div class="dash-card"><h4>Aulas Assistidas</h4><h2>24/30</h2></div>""", unsafe_allow_html=True)
        c2.markdown("""<div class="dash-card"><h4>Média Geral</h4><h2>8.5</h2></div>""", unsafe_allow_html=True)

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

    if menu == "👥 Minhas Turmas":
        st.markdown('<div class="main-header">Minhas Turmas</div>', unsafe_allow_html=True)
        # Filtra turmas onde o nome do professor aparece
        turmas = [c for c in st.session_state["classes"] if st.session_state["user_name"] in c.get("professor", "")]
        
        if not turmas: 
            st.info("Você não tem turmas vinculadas.")
        else:
            col_sel, col_view = st.columns(2)
            with col_sel:
                st.markdown("##### Configurar Link da Aula (Zoom)")
                t_sel = st.selectbox("Selecione a Turma", [t["nome"] for t in turmas])
                t_obj = next(t for t in turmas if t["nome"] == t_sel)
                
                # Edição do Link
                novo_link = st.text_input("Link Zoom", value=t_obj.get("link_zoom", ""))
                if st.button("Salvar Link e Enviar aos Alunos"):
                    t_obj["link_zoom"] = novo_link
                    save_data(CLASSES_FILE, st.session_state["classes"])
                    st.success(f"Link atualizado para {t_sel}!")
                    st.rerun()

            with col_view:
                st.markdown(f"""
                <div class="dash-card">
                    <h4>Turma: {t_obj['nome']}</h4>
                    <p><strong>Horário:</strong> {t_obj.get('dias', '--')}</p>
                    <p><strong>Link Atual:</strong> <a href="{t_obj.get('link_zoom','#')}" target="_blank">{t_obj.get('link_zoom','Sem link')}</a></p>
                </div>""", unsafe_allow_html=True)
                if t_obj.get("link_zoom"): 
                    st.link_button("Iniciar Aula Agora", t_obj["link_zoom"], type="primary")

    elif menu == "🧑‍🎓 Meus Alunos":
        st.markdown('<div class="main-header">Meus Alunos (Visualização)</div>', unsafe_allow_html=True)
        # 1. Minhas Turmas
        minhas_turmas_nomes = [c["nome"] for c in st.session_state["classes"] if st.session_state["user_name"] in c.get("professor", "")]
        # 2. Alunos dessas turmas
        meus_alunos = [s for s in st.session_state["students"] if s.get("turma") in minhas_turmas_nomes]
        
        if not meus_alunos:
            st.warning("Nenhum aluno encontrado nas suas turmas.")
        else:
            # Mostra dados, mas sem editar
            df = pd.DataFrame(meus_alunos)
            cols = ["nome", "turma", "celular", "email"]
            # Filtra colunas existentes
            valid_cols = [c for c in cols if c in df.columns]
            st.dataframe(df[valid_cols], use_container_width=True)

    elif menu == "📝 Diário":
        st.write("Funcionalidade de chamada (em desenvolvimento).")
    
    elif menu == "📊 Notas":
        with st.form("lancar_notas"):
            st.write("Lançar Notas")
            aluno = st.text_input("Nome do Aluno")
            nota = st.number_input("Nota", 0.0, 10.0)
            obs = st.text_input("Observação")
            if st.form_submit_button("Enviar para Coordenação"):
                st.session_state["grades"].append({
                    "aluno": aluno, "valor": nota, "obs": obs, 
                    "status": "Pendente", "professor": st.session_state["user_name"]
                })
                save_data(GRADES_FILE, st.session_state["grades"])
                st.success("Nota enviada!")

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
            titulo = st.text_input("Título")
            desc = st.text_area("Descrição")
            link_drv = st.text_input("Link Arquivo")
            if st.form_submit_button("Disponibilizar"):
                st.session_state["materials"].append({"titulo": titulo, "descricao": desc, "link": link_drv})
                save_data(MATERIALS_FILE, st.session_state["materials"])
                st.success("Material salvo!")

# ==============================================================================
# DASHBOARD: COORDENADOR
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

    elif menu == "🧑‍🎓 Alunos":
        st.markdown('<div class="main-header">Gestão de Alunos</div>', unsafe_allow_html=True)
        
        # LISTA GERAL
        if st.session_state["students"]:
            with st.expander("📋 Ver Lista Completa de Alunos", expanded=False):
                df = pd.DataFrame(st.session_state["students"])
                # Mostra colunas seguras
                safe_cols = [c for c in ["nome", "turma", "celular", "email", "idade", "responsavel_nome"] if c in df.columns]
                st.dataframe(df[safe_cols], use_container_width=True)
        
        tab1, tab2 = st.tabs(["➕ Novo Cadastro", "✏️ Gerenciar / Excluir"])
        
        with tab1:
            with st.form("add_student_full"):
                st.markdown("### ?? Dados Pessoais")
                c1, c2, c3 = st.columns(3)
                with c1: nome = st.text_input("Nome Completo *")
                with c2: data_nascimento = st.date_input("Data de Nascimento *")
                with c3: idade = st.number_input("Idade *", min_value=1, max_value=120, step=1)

                c4, c5, c6 = st.columns(3)
                with c4: celular = st.text_input("Celular/WhatsApp *")
                with c5: email = st.text_input("E-mail do Aluno *")
                with c6: rg = st.text_input("RG")

                c7, c8, c9 = st.columns(3)
                with c7: cpf = st.text_input("CPF")
                with c8: natal = st.text_input("Cidade Natal")
                with c9: pais = st.text_input("Pa?s de Origem", value="Brasil")

                st.divider()
                st.markdown("### ?? Endere?o")
                ce1, ce2, ce3 = st.columns(3)
                with ce1: cep = st.text_input("CEP")
                with ce2: cidade = st.text_input("Cidade")
                with ce3: bairro = st.text_input("Bairro")

                ce4, ce5 = st.columns([3, 1])
                with ce4: rua = st.text_input("Rua")
                with ce5: numero = st.text_input("N?mero")

                st.divider()
                st.markdown("### ?? Turma")
                turma = st.selectbox("Vincular ? Turma", ["Sem Turma"] + class_names())

                st.divider()
                st.markdown("### ?? Acesso do Aluno (opcional)")
                ca1, ca2 = st.columns(2)
                with ca1: login_aluno = st.text_input("Login do Aluno")
                with ca2: senha_aluno = st.text_input("Senha do Aluno", type="password")

                st.divider()
                st.markdown("### ???????? Respons?vel Legal / Financeiro")
                st.caption("Obrigat?rio para menores de 18 anos.")

                cr1, cr2 = st.columns(2)
                with cr1: resp_nome = st.text_input("Nome do Respons?vel")
                with cr2: resp_cpf = st.text_input("CPF do Respons?vel")

                cr3, cr4 = st.columns(2)
                with cr3: resp_cel = st.text_input("Celular do Respons?vel")
                with cr4: resp_email = st.text_input("E-mail do Respons?vel")

                if st.form_submit_button("Cadastrar Aluno"):
                    if idade < 18 and (not resp_nome or not resp_cpf):
                        st.error("? ERRO: Aluno menor de idade! ? obrigat?rio preencher Nome e CPF do Respons?vel.")
                    elif not nome or not email:
                        st.error("? ERRO: Nome e E-mail s?o obrigat?rios.")
                    elif (login_aluno and not senha_aluno) or (senha_aluno and not login_aluno):
                        st.error("? ERRO: Para criar o login, informe usu?rio e senha.")
                    elif login_aluno and find_user(login_aluno):
                        st.error("? ERRO: Este login j? existe.")
                    else:
                        novo_aluno = {
                            "nome": nome,
                            "idade": idade,
                            "data_nascimento": data_nascimento.strftime("%d/%m/%Y") if data_nascimento else "",
                            "celular": celular,
                            "email": email,
                            "rg": rg,
                            "cpf": cpf,
                            "cidade_natal": natal,
                            "pais": pais,
                            "cep": cep,
                            "cidade": cidade,
                            "bairro": bairro,
                            "rua": rua,
                            "numero": numero,
                            "turma": turma,
                            "usuario": login_aluno.strip(),
                            "senha": senha_aluno.strip(),
                            "responsavel": {
                                "nome": resp_nome,
                                "cpf": resp_cpf,
                                "celular": resp_cel,
                                "email": resp_email,
                            },
                        }
                        st.session_state["students"].append(novo_aluno)

                        if login_aluno and senha_aluno:
                            st.session_state["users"].append(
                                {
                                    "usuario": login_aluno.strip(),
                                    "senha": senha_aluno.strip(),
                                    "perfil": "Aluno",
                                    "pessoa": nome,
                                }
                            )
                            save_users(st.session_state["users"])

                        destinatario_email = resp_email if idade < 18 else email
                        st.toast("? Cadastro realizado com sucesso!", icon="??")
                        st.success(
                            f"?? E-mail enviado automaticamente para {destinatario_email} com: Comunicado de Boas-vindas, Link da Aula e Boletos."
                        )

        with tab2:
            if not st.session_state["students"]:
                st.info("Nenhum aluno cadastrado.")
            else:
                aluno_nomes = [s["nome"] for s in st.session_state["students"]]
                aluno_sel = st.selectbox("Selecione o Aluno para Editar/Excluir", aluno_nomes)
                aluno_obj = next((s for s in st.session_state["students"] if s["nome"] == aluno_sel), None)

                if aluno_obj:
                    turmas = ["Sem Turma"] + class_names()
                    current_turma = aluno_obj.get("turma", "Sem Turma")
                    if current_turma not in turmas:
                        turmas.append(current_turma)
                    current_dn = parse_date(aluno_obj.get("data_nascimento", "")) or datetime.date.today()

                    with st.form("edit_student"):
                        st.subheader(f"Editando: {aluno_obj['nome']}")
                        new_nome = st.text_input("Nome", value=aluno_obj["nome"])

                        c1, c2 = st.columns(2)
                        with c1: new_cel = st.text_input("Celular", value=aluno_obj.get("celular", ""))
                        with c2: new_email = st.text_input("Email", value=aluno_obj.get("email", ""))

                        c3, c4 = st.columns(2)
                        with c3: new_dn = st.date_input("Data de Nascimento", value=current_dn)
                        with c4: new_turma = st.selectbox("Turma", turmas, index=turmas.index(current_turma))

                        st.markdown("### ?? Acesso do Aluno")
                        c5, c6 = st.columns(2)
                        with c5: new_login = st.text_input("Login do Aluno", value=aluno_obj.get("usuario", ""))
                        with c6: new_senha = st.text_input("Senha do Aluno", value=aluno_obj.get("senha", ""), type="password")

                        c_edit, c_del = st.columns([1, 1])
                        with c_edit:
                            if st.form_submit_button("?? Salvar Altera??es"):
                                old_login = aluno_obj.get("usuario", "").strip()
                                login = new_login.strip() or old_login
                                senha = new_senha.strip() or aluno_obj.get("senha", "")

                                if login and find_user(login) and (not old_login or login.lower() != old_login.lower()):
                                    st.error("? ERRO: Este login j? existe.")
                                else:
                                    if login:
                                        user_obj = find_user(old_login) if old_login else None
                                        if user_obj:
                                            user_obj["usuario"] = login
                                            user_obj["senha"] = senha
                                            user_obj["perfil"] = "Aluno"
                                            user_obj["pessoa"] = new_nome
                                        else:
                                            st.session_state["users"].append(
                                                {
                                                    "usuario": login,
                                                    "senha": senha,
                                                    "perfil": "Aluno",
                                                    "pessoa": new_nome,
                                                }
                                            )
                                        save_users(st.session_state["users"])

                                    aluno_obj["nome"] = new_nome
                                    aluno_obj["celular"] = new_cel
                                    aluno_obj["turma"] = new_turma
                                    aluno_obj["email"] = new_email
                                    aluno_obj["data_nascimento"] = new_dn.strftime("%d/%m/%Y") if new_dn else ""
                                    aluno_obj["usuario"] = login
                                    aluno_obj["senha"] = senha

                                    st.success("Dados atualizados!")
                                    st.rerun()
                        with c_del:
                            if st.form_submit_button("??? EXCLUIR ALUNO", type="primary"):
                                login = aluno_obj.get("usuario", "").strip()
                                if login:
                                    user_obj = find_user(login)
                                    if user_obj and user_obj.get("perfil") == "Aluno":
                                        st.session_state["users"].remove(user_obj)
                                        save_users(st.session_state["users"])
                                st.session_state["students"].remove(aluno_obj)
                                st.error("Aluno exclu?do permanentemente.")
                                st.rerun()

    elif menu_coord == "Professores":
        st.markdown('<div class="main-header">Gest?o de Professores</div>', unsafe_allow_html=True)
        tab1, tab2 = st.tabs(["? Novo Professor", "?? Gerenciar / Excluir"])
        with tab1:
            with st.form("add_prof"):
                c1, c2 = st.columns(2)
                with c1: nome = st.text_input("Nome")
                with c2: area = st.text_input("?rea")

                c3, c4 = st.columns(2)
                with c3: login_prof = st.text_input("Login do Professor")
                with c4: senha_prof = st.text_input("Senha do Professor", type="password")

                if st.form_submit_button("Cadastrar"):
                    if (login_prof and not senha_prof) or (senha_prof and not login_prof):
                        st.error("? ERRO: Para criar o login, informe usu?rio e senha.")
                    elif login_prof and find_user(login_prof):
                        st.error("? ERRO: Este login j? existe.")
                    else:
                        st.session_state["teachers"].append(
                            {
                                "nome": nome,
                                "area": area,
                                "usuario": login_prof.strip(),
                                "senha": senha_prof.strip(),
                            }
                        )
                        if login_prof and senha_prof:
                            st.session_state["users"].append(
                                {
                                    "usuario": login_prof.strip(),
                                    "senha": senha_prof.strip(),
                                    "perfil": "Professor",
                                    "pessoa": nome,
                                }
                            )
                            save_users(st.session_state["users"])
                        st.success("Salvo!")
        with tab2:
            if not st.session_state["teachers"]:
                st.info("Nenhum professor cadastrado.")
            else:
                prof_nomes = [t["nome"] for t in st.session_state["teachers"]]
                prof_sel = st.selectbox("Selecione o Professor", prof_nomes)
                prof_obj = next((t for t in st.session_state["teachers"] if t["nome"] == prof_sel), None)
                if prof_obj:
                    with st.form("edit_prof"):
                        new_nome = st.text_input("Nome", value=prof_obj["nome"])
                        new_area = st.text_input("?rea", value=prof_obj.get("area", ""))

                        c3, c4 = st.columns(2)
                        with c3: new_login = st.text_input("Login do Professor", value=prof_obj.get("usuario", ""))
                        with c4: new_senha = st.text_input("Senha do Professor", value=prof_obj.get("senha", ""), type="password")

                        c_edit, c_del = st.columns([1, 1])
                        with c_edit:
                            if st.form_submit_button("?? Salvar Altera??es"):
                                old_login = prof_obj.get("usuario", "").strip()
                                login = new_login.strip() or old_login
                                senha = new_senha.strip() or prof_obj.get("senha", "")

                                if login and find_user(login) and (not old_login or login.lower() != old_login.lower()):
                                    st.error("? ERRO: Este login j? existe.")
                                else:
                                    if login:
                                        user_obj = find_user(old_login) if old_login else None
                                        if user_obj:
                                            user_obj["usuario"] = login
                                            user_obj["senha"] = senha
                                            user_obj["perfil"] = "Professor"
                                            user_obj["pessoa"] = new_nome
                                        else:
                                            st.session_state["users"].append(
                                                {
                                                    "usuario": login,
                                                    "senha": senha,
                                                    "perfil": "Professor",
                                                    "pessoa": new_nome,
                                                }
                                            )
                                        save_users(st.session_state["users"])

                                    # Atualiza nome do professor em turmas
                                    old_nome = prof_obj["nome"]
                                    for turma in st.session_state["classes"]:
                                        if str(turma.get("professor", "")).strip() == str(old_nome).strip():
                                            turma["professor"] = new_nome

                                    prof_obj["nome"] = new_nome
                                    prof_obj["area"] = new_area
                                    prof_obj["usuario"] = login
                                    prof_obj["senha"] = senha
                                    st.success("Professor atualizado!")
                                    st.rerun()
                        with c_del:
                            if st.form_submit_button("??? EXCLUIR PROFESSOR", type="primary"):
                                login = prof_obj.get("usuario", "").strip()
                                if login:
                                    user_obj = find_user(login)
                                    if user_obj and user_obj.get("perfil") == "Professor":
                                        st.session_state["users"].remove(user_obj)
                                        save_users(st.session_state["users"])
                                st.session_state["teachers"].remove(prof_obj)
                                st.error("Professor exclu?do.")
                                st.rerun()

    elif menu_coord == "Turmas":
        st.markdown('<div class="main-header">Gest?o de Turmas</div>', unsafe_allow_html=True)
        tab1, tab2 = st.tabs(["? Nova Turma", "?? Gerenciar / Excluir"])

        with tab1:
            with st.form("add_class"):
                c1, c2 = st.columns(2)
                with c1: nome = st.text_input("Nome da Turma")
                with c2: prof = st.selectbox("Professor", ["Sem Professor"] + teacher_names())
                c3, c4 = st.columns(2)
                with c3: dias = st.text_input("Dias e Hor?rios")
                with c4: link = st.text_input("Link do Zoom (Inicial)")
                if st.form_submit_button("Cadastrar"):
                    st.session_state["classes"].append(
                        {"nome": nome, "professor": prof, "dias": dias, "link_zoom": link}
                    )
                    st.success("Turma salva!")

        with tab2:
            if not st.session_state["classes"]:
                st.info("Nenhuma turma cadastrada.")
            else:
                turma_nomes = [t.get("nome", "") for t in st.session_state["classes"]]
                turma_sel = st.selectbox("Selecione a Turma", turma_nomes)
                turma_obj = next((t for t in st.session_state["classes"] if t.get("nome", "") == turma_sel), None)

                if turma_obj:
                    prof_list = ["Sem Professor"] + teacher_names()
                    current_prof = turma_obj.get("professor", "Sem Professor")
                    if current_prof not in prof_list:
                        prof_list.append(current_prof)

                    with st.form("edit_class"):
                        new_nome = st.text_input("Nome da Turma", value=turma_obj.get("nome", ""))
                        new_prof = st.selectbox("Professor", prof_list, index=prof_list.index(current_prof))
                        new_dias = st.text_input("Dias e Hor?rios", value=turma_obj.get("dias", ""))
                        new_link = st.text_input("Link do Zoom", value=turma_obj.get("link_zoom", ""))

                        c_edit, c_del = st.columns([1, 1])
                        with c_edit:
                            if st.form_submit_button("?? Salvar Altera??es"):
                                old_nome = turma_obj.get("nome", "")
                                turma_obj["nome"] = new_nome
                                turma_obj["professor"] = new_prof
                                turma_obj["dias"] = new_dias
                                turma_obj["link_zoom"] = new_link

                                if old_nome and new_nome and old_nome != new_nome:
                                    for aluno in st.session_state["students"]:
                                        if aluno.get("turma") == old_nome:
                                            aluno["turma"] = new_nome

                                st.success("Turma atualizada!")
                                st.rerun()
                        with c_del:
                            if st.form_submit_button("??? EXCLUIR TURMA", type="primary"):
                                nome_turma = turma_obj.get("nome", "")
                                if nome_turma:
                                    for aluno in st.session_state["students"]:
                                        if aluno.get("turma") == nome_turma:
                                            aluno["turma"] = "Sem Turma"
                                st.session_state["classes"].remove(turma_obj)
                                st.error("Turma exclu?da.")
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
            us = [u["usuario"] for u in st.session_state["users"]]
            sel = st.selectbox("Usuario", us)
            if st.button("Excluir") and sel != "admin":
                obj = next(u for u in st.session_state["users"] if u["usuario"] == sel)
                st.session_state["users"].remove(obj)
                save_data(USERS_FILE, st.session_state["users"])
                st.success("Excluído!")
                st.rerun()

    elif menu == "💰 Financeiro":
        st.markdown('<div class="main-header">Financeiro</div>', unsafe_allow_html=True)
        with st.form("fin_rec"):
            st.write("Lançar Recebimento")
            desc = st.text_input("Descrição")
            val = st.number_input("Valor", 0.0)
            aluno = st.selectbox("Aluno", [s["nome"] for s in st.session_state["students"]])
            if st.form_submit_button("Lançar"):
                st.session_state["receivables"].append({
                    "descricao": desc, "valor": val, "aluno": aluno, 
                    "vencimento": str(datetime.date.today()), "status": "Aberto"
                })
                save_financial()
                st.success("Lançado!")
        if st.session_state["receivables"]:
            st.dataframe(pd.DataFrame(st.session_state["receivables"]))