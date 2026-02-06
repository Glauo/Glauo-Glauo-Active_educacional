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
STUDENTS_FILE = Path("students.json")
TEACHERS_FILE = Path("teachers.json")
CLASSES_FILE = Path("classes.json")
MESSAGES_FILE = Path("messages.json")
VIDEOS_FILE = Path("videos.json")
MATERIALS_FILE = Path("materials.json")
GRADES_FILE = Path("grades.json")
FINANCIAL_FILE = Path("financial.json")

WHATSAPP_NUMBER = "5516996043314" 
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "123"

# --- FUNCOES DE UTILIDADE (LOAD/SAVE) ---
def get_logo_path():
    candidates = [Path("image_8fc66d.png"), Path("logo_active2.png"), Path("logo.png")]
    for path in candidates:
        if path.exists(): return path
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
        users.append({"usuario": ADMIN_USERNAME, "senha": ADMIN_PASSWORD, "perfil": "Admin", "pessoa": "Administrador"})
        save_data(USERS_FILE, users)
    return users

def create_or_update_login(username, password, role, person_name):
    users = st.session_state["users"]
    # Remove se ja existir para atualizar
    users = [u for u in users if u["usuario"] != username]
    users.append({"usuario": username, "senha": password, "perfil": role, "pessoa": person_name})
    st.session_state["users"] = users
    save_data(USERS_FILE, users)

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
    try: return float(str(value).replace(",", "."))
    except ValueError: return 0.0

def format_money(value):
    return f"R$ {value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

def allowed_portals(profile):
    if profile == "Aluno": return ["Aluno"]
    if profile == "Professor": return ["Professor"]
    if profile in ["Coordenador", "Admin"]: return ["Aluno", "Professor", "Coordenador"]
    return []

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
# CSS E ESTILOS
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
# INICIALIZACAO DE DADOS
# ==============================================================================
if "init_done" not in st.session_state:
    st.session_state["users"] = ensure_admin_user()
    st.session_state["students"] = load_data(STUDENTS_FILE)
    st.session_state["teachers"] = load_data(TEACHERS_FILE)
    st.session_state["classes"] = load_data(CLASSES_FILE)
    st.session_state["messages"] = load_data(MESSAGES_FILE)
    st.session_state["videos"] = load_data(VIDEOS_FILE)
    st.session_state["materials"] = load_data(MATERIALS_FILE)
    st.session_state["grades"] = load_data(GRADES_FILE)
    rec, pag = load_financial()
    st.session_state["receivables"] = rec
    st.session_state["payables"] = pag
    st.session_state["init_done"] = True

# ==============================================================================
# TELA DE LOGIN
# ==============================================================================
if not st.session_state["logged_in"]:
    # Aplica fundo de login
    st.markdown("""<style>.stApp {background: linear-gradient(135deg, #0f172a 0%, #1e3a8a 50%, #3b82f6 100%);}</style>""", unsafe_allow_html=True)
    
    col_left, col_right = st.columns([1, 0.8], gap="large")
    with col_left:
        logo_path = get_logo_path()
        logo_html = f"<img src='data:image/png;base64,{base64.b64encode(logo_path.read_bytes()).decode()}' style='max-width:80px;'>" if logo_path else ""
        st.markdown(f"""
        <div class="info-card">
            <div style="margin-bottom:24px;">{logo_html}</div>
            <div style="font-family:'Sora'; font-size:2rem; font-weight:700; color:#0f172a; line-height:1.2; margin-bottom:12px;">Sistema Educacional<br>Ativo</div>
            <div style="color:#64748b; margin-bottom:32px;">Gestão acadêmica, comunicação e conteúdo.</div>
            <a href="https://wa.me/{WHATSAPP_NUMBER}" target="_blank" class="whatsapp-button">📱 Suporte WhatsApp</a>
        </div>""", unsafe_allow_html=True)

    with col_right:
        st.write(""); st.write("")
        with st.form("login_form"):
            st.markdown("<h3 style='font-family:Sora;'>Conecte-se</h3>", unsafe_allow_html=True)
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
        st.markdown(f"### Olá, {st.session_state['user_name']}")
        st.info("Painel do Aluno")
        menu = sidebar_menu("Menu", ["🏠 Painel", "📚 Minhas Aulas", "📊 Boletim", "💬 Mensagens", "🎥 Aulas Gravadas", "💰 Financeiro", "📂 Materiais"], "aluno_menu")
        if st.button("Sair"): logout_user()

    if menu == "🏠 Painel":
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

    elif menu == "📚 Minhas Aulas":
        st.markdown('<div class="main-header">Minhas Aulas</div>', unsafe_allow_html=True)
        st.info("Conteúdo programático das aulas.")

    elif menu == "📊 Boletim":
        st.markdown('<div class="main-header">Boletim</div>', unsafe_allow_html=True)
        my_grades = [g for g in st.session_state["grades"] if g["aluno"] == st.session_state["user_name"]]
        if my_grades: st.dataframe(pd.DataFrame(my_grades), use_container_width=True)
        else: st.info("Sem notas lançadas.")

    elif menu == "💬 Mensagens":
        st.markdown('<div class="main-header">Mensagens</div>', unsafe_allow_html=True)
        for m in reversed(st.session_state["messages"]):
            st.markdown(f"**{m['titulo']}** ({m.get('data','')})\n\n{m['mensagem']}\n\n---")

    elif menu == "🎥 Aulas Gravadas":
        st.markdown('<div class="main-header">Aulas Gravadas</div>', unsafe_allow_html=True)
        for v in reversed(st.session_state["videos"]):
            with st.expander(v['titulo']):
                if v['url']: st.video(v['url'])

    elif menu == "💰 Financeiro":
        st.markdown('<div class="main-header">Financeiro</div>', unsafe_allow_html=True)
        my_fin = [r for r in st.session_state["receivables"] if r["aluno"] == st.session_state["user_name"]]
        if my_fin: st.dataframe(pd.DataFrame(my_fin), use_container_width=True)
        else: st.info("Nada consta.")

    elif menu == "📂 Materiais":
        st.markdown('<div class="main-header">Materiais</div>', unsafe_allow_html=True)
        for mat in st.session_state["materials"]:
            st.markdown(f"📄 **{mat['titulo']}**: {mat['descricao']}")
            if mat['link']: st.markdown(f"[Baixar]({mat['link']})")
            st.markdown("---")

# ==============================================================================
# DASHBOARD: PROFESSOR
# ==============================================================================
elif st.session_state["role"] == "Professor":
    with st.sidebar:
        st.markdown(f"### Prof. {st.session_state['user_name']}")
        menu = sidebar_menu("Docência", ["👥 Minhas Turmas", "🧑‍🎓 Meus Alunos", "📝 Diário", "📊 Notas", "🎥 Cadastrar Aula", "📂 Cadastrar Material"], "prof_menu")
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

    elif menu == "🎥 Cadastrar Aula":
        with st.form("new_aula"):
            titulo = st.text_input("Título da Aula")
            link_yt = st.text_input("Link YouTube")
            if st.form_submit_button("Salvar Aula"):
                st.session_state["videos"].append({"titulo": titulo, "url": link_yt, "data": str(datetime.date.today())})
                save_data(VIDEOS_FILE, st.session_state["videos"])
                st.success("Aula salva!")

    elif menu == "📂 Cadastrar Material":
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
        st.markdown(f"### Coord. {st.session_state['user_name']}")
        menu = sidebar_menu("Admin", ["📊 Dash", "🔗 Links Ao Vivo", "🧑‍🎓 Alunos", "👩‍🏫 Professores", "🏫 Turmas", "💰 Financeiro", "🔐 Usuários"], "coord_menu")
        if st.button("Sair"): logout_user()

    if menu == "📊 Dash":
        st.markdown('<div class="main-header">Visão Geral</div>', unsafe_allow_html=True)
        c1, c2, c3 = st.columns(3)
        c1.metric("Total Alunos", len(st.session_state["students"]))
        c2.metric("Professores", len(st.session_state["teachers"]))
        c3.metric("Turmas", len(st.session_state["classes"]))

    elif menu == "🔗 Links Ao Vivo":
        st.markdown('<div class="main-header">Gerenciar Links Ao Vivo</div>', unsafe_allow_html=True)
        turmas = [t["nome"] for t in st.session_state["classes"]]
        if not turmas: st.warning("Sem turmas cadastradas.")
        else:
            sel = st.selectbox("Selecione a Turma", turmas)
            obj = next(t for t in st.session_state["classes"] if t["nome"] == sel)
            
            st.info("Este link aparecerá automaticamente para todos os alunos desta turma.")
            novo = st.text_input("Link Zoom/Meet", value=obj.get("link_zoom", ""))
            
            if st.button("Salvar Link"):
                obj["link_zoom"] = novo
                save_data(CLASSES_FILE, st.session_state["classes"])
                st.success("Link atualizado!")

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
            with st.form("cad_aluno"):
                st.subheader("Dados Pessoais")
                c1, c2 = st.columns(2)
                nome = c1.text_input("Nome Completo *")
                nasc = c2.date_input("Data Nascimento", datetime.date(2010,1,1), format="DD/MM/YYYY")
                
                c3, c4, c5 = st.columns(3)
                idade = c3.number_input("Idade", 1, 100)
                rg = c4.text_input("RG")
                cpf = c5.text_input("CPF")
                
                c6, c7 = st.columns(2)
                celular = c6.text_input("Celular *")
                email = c7.text_input("Email *")
                
                st.subheader("Endereço")
                ce1, ce2 = st.columns(2)
                cidade = ce1.text_input("Cidade")
                bairro = ce2.text_input("Bairro")
                ce3, ce4 = st.columns([3, 1])
                rua = ce3.text_input("Rua")
                num = ce4.text_input("Nº")
                
                st.subheader("Turma & Acesso")
                turma = st.selectbox("Turma", ["Sem Turma"] + class_names())
                login_u = st.text_input("Criar Login do Aluno")
                login_p = st.text_input("Criar Senha do Aluno", type="password")
                
                st.subheader("Responsável (Obrigatório se < 18)")
                resp_nome = st.text_input("Nome Responsável")
                resp_cpf = st.text_input("CPF Responsável")
                
                if st.form_submit_button("Salvar Aluno"):
                    if idade < 18 and not resp_nome:
                        st.error("Menor de idade exige responsável.")
                    elif not nome:
                        st.error("Nome é obrigatório.")
                    else:
                        new_student = {
                            "nome": nome, "idade": idade, "nascimento": str(nasc),
                            "rg": rg, "cpf": cpf, "celular": celular, "email": email,
                            "cidade": cidade, "bairro": bairro, "rua": rua, "numero": num,
                            "turma": turma, "responsavel_nome": resp_nome, "responsavel_cpf": resp_cpf
                        }
                        st.session_state["students"].append(new_student)
                        save_data(STUDENTS_FILE, st.session_state["students"])
                        
                        if login_u and login_p:
                            create_or_update_login(login_u, login_p, "Aluno", nome)
                            st.toast("Login criado!")
                        
                        st.success("Aluno cadastrado com sucesso!")
        
        with tab2:
            names = [s["nome"] for s in st.session_state["students"]]
            sel = st.selectbox("Selecione Aluno", names) if names else None
            if sel:
                obj = next(s for s in st.session_state["students"] if s["nome"] == sel)
                with st.form("edit_aluno"):
                    st.write(f"Editando: {sel}")
                    nn = st.text_input("Nome", obj["nome"])
                    nt = st.selectbox("Turma", ["Sem Turma"] + class_names())
                    nc = st.text_input("Celular", obj.get("celular", ""))
                    
                    c_ed, c_del = st.columns(2)
                    if c_ed.form_submit_button("Salvar Alterações"):
                        obj["nome"] = nn
                        obj["turma"] = nt
                        obj["celular"] = nc
                        save_data(STUDENTS_FILE, st.session_state["students"])
                        st.success("Salvo!")
                        st.rerun()
                    
                    if c_del.form_submit_button("🗑️ EXCLUIR ALUNO", type="primary"):
                        st.session_state["students"].remove(obj)
                        save_data(STUDENTS_FILE, st.session_state["students"])
                        st.error("Aluno excluído.")
                        st.rerun()

    elif menu == "👩‍🏫 Professores":
        st.markdown('<div class="main-header">Gestão de Professores</div>', unsafe_allow_html=True)
        tab1, tab2 = st.tabs(["➕ Novo", "✏️ Gerenciar"])
        with tab1:
            with st.form("cad_prof"):
                nome = st.text_input("Nome")
                area = st.text_input("Área")
                lu = st.text_input("Criar Login")
                lp = st.text_input("Criar Senha", type="password")
                if st.form_submit_button("Salvar"):
                    st.session_state["teachers"].append({"nome": nome, "area": area})
                    save_data(TEACHERS_FILE, st.session_state["teachers"])
                    if lu and lp: create_or_update_login(lu, lp, "Professor", nome)
                    st.success("Professor salvo!")
        with tab2:
            pnames = [t["nome"] for t in st.session_state["teachers"]]
            sel = st.selectbox("Selecione", pnames) if pnames else None
            if sel:
                obj = next(t for t in st.session_state["teachers"] if t["nome"] == sel)
                with st.form("edit_prof"):
                    nn = st.text_input("Nome", obj["nome"])
                    na = st.text_input("Área", obj.get("area",""))
                    c1, c2 = st.columns(2)
                    if c1.form_submit_button("Salvar"):
                        obj["nome"] = nn
                        obj["area"] = na
                        save_data(TEACHERS_FILE, st.session_state["teachers"])
                        st.success("Salvo!")
                        st.rerun()
                    if c2.form_submit_button("Excluir", type="primary"):
                        st.session_state["teachers"].remove(obj)
                        save_data(TEACHERS_FILE, st.session_state["teachers"])
                        st.rerun()

    elif menu == "🏫 Turmas":
        st.markdown('<div class="main-header">Gestão de Turmas</div>', unsafe_allow_html=True)
        tab1, tab2 = st.tabs(["➕ Nova Turma", "✏️ Gerenciar"])
        with tab1:
            with st.form("new_class"):
                tnome = st.text_input("Nome Turma")
                tprof = st.selectbox("Professor", teacher_names())
                tdias = st.text_input("Dias")
                if st.form_submit_button("Salvar"):
                    st.session_state["classes"].append({"nome": tnome, "professor": tprof, "dias": tdias})
                    save_data(CLASSES_FILE, st.session_state["classes"])
                    st.success("Turma criada!")
        with tab2:
            tnames = class_names()
            sel = st.selectbox("Selecione Turma", tnames) if tnames else None
            if sel:
                obj = next(c for c in st.session_state["classes"] if c["nome"] == sel)
                with st.form("edit_class"):
                    nn = st.text_input("Nome", obj["nome"])
                    np = st.selectbox("Professor", teacher_names())
                    nd = st.text_input("Dias", obj.get("dias",""))
                    c1, c2 = st.columns(2)
                    if c1.form_submit_button("Salvar"):
                        obj["nome"] = nn
                        obj["professor"] = np
                        obj["dias"] = nd
                        save_data(CLASSES_FILE, st.session_state["classes"])
                        st.success("Atualizado!")
                        st.rerun()
                    if c2.form_submit_button("Excluir", type="primary"):
                        st.session_state["classes"].remove(obj)
                        save_data(CLASSES_FILE, st.session_state["classes"])
                        st.rerun()

    elif menu == "🔐 Usuários":
        st.markdown('<div class="main-header">Controle de Usuários</div>', unsafe_allow_html=True)
        tab1, tab2 = st.tabs(["Novo", "Excluir"])
        with tab1:
            with st.form("u_new"):
                u = st.text_input("User")
                p = st.text_input("Pass", type="password")
                r = st.selectbox("Perfil", ["Aluno", "Professor", "Coordenador"])
                if st.form_submit_button("Criar"):
                    create_or_update_login(u, p, r, "Novo Usuário")
                    st.success("Criado!")
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