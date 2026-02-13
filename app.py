import base64
import datetime
import io
import json
import os
import re
import smtplib
import shutil
import threading
import uuid
import calendar
import zipfile
from email.message import EmailMessage
from pathlib import Path
from urllib.parse import quote

import pandas as pd
import streamlit as st
from openai import OpenAI

try:
    import psycopg2
    import psycopg2.extras
except Exception:
    psycopg2 = None

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
if "challenges" not in st.session_state:
    st.session_state["challenges"] = []
if "challenge_completions" not in st.session_state:
    st.session_state["challenge_completions"] = []
if "chatbot_log" not in st.session_state:
    st.session_state["chatbot_log"] = []
if "agenda" not in st.session_state:
    st.session_state["agenda"] = []
if "inventory" not in st.session_state:
    st.session_state["inventory"] = []
if "inventory_moves" not in st.session_state:
    st.session_state["inventory_moves"] = []
if "cert_preview_html" not in st.session_state:
    st.session_state["cert_preview_html"] = ""
if "cert_preview_pdf" not in st.session_state:
    st.session_state["cert_preview_pdf"] = None
if "cert_preview_data" not in st.session_state:
    st.session_state["cert_preview_data"] = {}
if "certificates" not in st.session_state:
    st.session_state["certificates"] = []
if "books" not in st.session_state:
    st.session_state["books"] = []
if "material_orders" not in st.session_state:
    st.session_state["material_orders"] = []
if "order_ai_summary" not in st.session_state:
    st.session_state["order_ai_summary"] = ""
if "auth_mode" not in st.session_state:
    st.session_state["auth_mode"] = "Login"
if "active_chat_histories" not in st.session_state:
    st.session_state["active_chat_histories"] = {}
if "active_chat_mode" not in st.session_state:
    st.session_state["active_chat_mode"] = "Atendimento"
if "active_chat_temp" not in st.session_state:
    st.session_state["active_chat_temp"] = 0.3

ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "2523"
DATA_DIR = Path(os.getenv("ACTIVE_DATA_DIR", ".")).expanduser()
BACKUP_DIR = DATA_DIR / "_data_backups"
DATA_IO_LOCK = threading.Lock()
DATA_DIR.mkdir(parents=True, exist_ok=True)
BACKUP_DIR.mkdir(parents=True, exist_ok=True)

USERS_FILE = DATA_DIR / "users.json"
MESSAGES_FILE = DATA_DIR / "messages.json"
VIDEOS_FILE = DATA_DIR / "videos.json"
MATERIALS_FILE = DATA_DIR / "materials.json"
GRADES_FILE = DATA_DIR / "grades.json"
STUDENTS_FILE = DATA_DIR / "students.json"
TEACHERS_FILE = DATA_DIR / "teachers.json"
CLASSES_FILE = DATA_DIR / "classes.json"
RECEIVABLES_FILE = DATA_DIR / "receivables.json"
PAYABLES_FILE = DATA_DIR / "payables.json"
FEE_TEMPLATES_FILE = DATA_DIR / "fee_templates.json"
EMAIL_LOG_FILE = DATA_DIR / "email_log.json"
CHATBOT_LOG_FILE = DATA_DIR / "chatbot_active_log.json"
AGENDA_FILE = DATA_DIR / "agenda.json"
INVENTORY_FILE = DATA_DIR / "inventory.json"
INVENTORY_MOVES_FILE = DATA_DIR / "inventory_moves.json"
CERTIFICATES_FILE = DATA_DIR / "certificates.json"
BOOKS_FILE = DATA_DIR / "books.json"
MATERIAL_ORDERS_FILE = DATA_DIR / "material_orders.json"
CHALLENGES_FILE = DATA_DIR / "challenges.json"
CHALLENGE_COMPLETIONS_FILE = DATA_DIR / "challenge_completions.json"
WHATSAPP_NUMBER = "5516996043314" 

def _get_config_value(name, default=""):
    env_val = os.getenv(name, None)
    if env_val is not None and str(env_val).strip():
        return str(env_val).strip()
    try:
        sec_val = st.secrets.get(name, None)
        if sec_val is not None and str(sec_val).strip():
            return str(sec_val).strip()
    except Exception:
        pass
    return default

# --- FUNCOES DE UTILIDADE ---
def get_logo_path():
    candidates = [
        Path("logo_active_novo.png"),
        Path("image_8fc66d.png"),
        Path("logo_active.png"),
        Path("logo_active.jpg"),
        Path("logo_active2.png"),
        Path("logo_active2.jpg"),
        Path("logo.png"),
    ]
    for path in candidates:
        if path.exists():
            return path
    return None

def render_sidebar_logo(logo_path):
    if not logo_path:
        return
    col_left, col_logo, col_right = st.columns([1, 5, 1])
    with col_logo:
        st.image(str(logo_path), width=190)

def get_mister_wiz_logo_path():
    candidates = [
        Path("logo_mister_wiz.png"),
        Path("logo_misterwiz.png"),
        Path("mister_wiz.png"),
        Path("misterwiz.png"),
        Path("logo_mister.png"),
        Path("logo_wiz.png"),
    ]
    for path in candidates:
        if path.exists():
            return path
    return None

def _atomic_write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(data, ensure_ascii=False, indent=2)
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    tmp_path.write_text(payload, encoding="utf-8")
    tmp_path.replace(path)

def _backup_path(path):
    stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    return BACKUP_DIR / f"{path.stem}_{stamp}{path.suffix}.bak"

def _rotate_backups(path, keep=30):
    backups = sorted(
        BACKUP_DIR.glob(f"{path.stem}_*{path.suffix}.bak"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    for old in backups[keep:]:
        try:
            old.unlink(missing_ok=True)
        except Exception:
            pass

def _db_url():
    return _get_config_value("ACTIVE_DATABASE_URL", "") or _get_config_value("DATABASE_URL", "")

def _db_enabled():
    return bool(_db_url()) and psycopg2 is not None

def _db_connect():
    # New connection per operation keeps behavior predictable across Streamlit reruns.
    url = _db_url()
    conn = psycopg2.connect(url, connect_timeout=8)
    try:
        psycopg2.extras.register_default_json(conn, loads=json.loads)
        psycopg2.extras.register_default_jsonb(conn, loads=json.loads)
    except Exception:
        pass
    return conn

def _db_init(conn):
    with conn.cursor() as cur:
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS active_kv (
              key TEXT PRIMARY KEY,
              value JSONB NOT NULL,
              updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
            );
            """
        )

def _db_get(key):
    try:
        with _db_connect() as conn:
            _db_init(conn)
            with conn.cursor() as cur:
                cur.execute("SELECT value FROM active_kv WHERE key = %s", (key,))
                row = cur.fetchone()
                return row[0] if row else None
    except Exception:
        return None

def _db_set(key, value):
    try:
        with _db_connect() as conn:
            _db_init(conn)
            with conn.cursor() as cur:
                payload = psycopg2.extras.Json(value, dumps=lambda v: json.dumps(v, ensure_ascii=False))
                cur.execute(
                    """
                    INSERT INTO active_kv (key, value, updated_at)
                    VALUES (%s, %s, now())
                    ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value, updated_at = now()
                    """,
                    (key, payload),
                )
        return True
    except Exception:
        return False

def _load_latest_backup_list(path):
    backups = sorted(
        BACKUP_DIR.glob(f"{path.stem}_*{path.suffix}.bak"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    for backup in backups:
        try:
            data = json.loads(backup.read_text(encoding="utf-8"))
            if isinstance(data, list):
                return data
        except Exception:
            continue
    return None

def _load_json_list_file(path):
    with DATA_IO_LOCK:
        if not path.exists():
            _atomic_write_json(path, [])
            return []
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            data = data if isinstance(data, list) else []
            auto_restore = os.getenv("ACTIVE_AUTO_RESTORE_EMPTY", "1").strip().lower() not in ("0", "false", "no")
            if auto_restore and path in (STUDENTS_FILE, CLASSES_FILE) and not data:
                restored = _load_latest_backup_list(path)
                if restored:
                    _atomic_write_json(path, restored)
                    return restored
            return data
        except Exception:
            restored = _load_latest_backup_list(path)
            if restored is not None:
                _atomic_write_json(path, restored)
                return restored
            return []

def _save_json_list_file(path, data):
    safe_data = data if isinstance(data, list) else []
    with DATA_IO_LOCK:
        if path.exists():
            try:
                shutil.copy2(path, _backup_path(path))
                _rotate_backups(path)
            except Exception:
                pass
        _atomic_write_json(path, safe_data)

def _load_json_list(path):
    key = str(getattr(path, "stem", path)).strip()
    if _db_enabled():
        data = _db_get(key)
        if isinstance(data, list):
            return data
        if data is None:
            # First run with DB: seed from local file if exists.
            seeded = _load_json_list_file(path)
            _db_set(key, seeded)
            return seeded
        return []
    return _load_json_list_file(path)

def _save_json_list(path, data):
    key = str(getattr(path, "stem", path)).strip()
    if _db_enabled():
        ok = _db_set(key, data if isinstance(data, list) else [])
        mirror = os.getenv("ACTIVE_MIRROR_FILES", "0").strip().lower() in ("1", "true", "yes")
        if mirror:
            _save_json_list_file(path, data)
        return ok
    _save_json_list_file(path, data)
    return True

def load_users():
    return _load_json_list(USERS_FILE)

def save_users(users):
    _save_json_list(USERS_FILE, users)

def load_list(path):
    return _load_json_list(path)

def save_list(path, data):
    _save_json_list(path, data)

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
    target = str(username or "").strip().lower()
    if not target:
        return None
    for user in st.session_state["users"]:
        stored = str(user.get("usuario", "")).strip().lower()
        if stored == target:
            return user
    return None

def sync_users_from_profiles(users):
    if not isinstance(users, list):
        users = []
    by_login = {}
    for u in users:
        login = str(u.get("usuario", "")).strip().lower()
        if login:
            by_login[login] = u

    def ensure_login(login, senha, perfil, pessoa):
        login_norm = str(login or "").strip()
        senha_norm = str(senha or "").strip()
        if not login_norm or not senha_norm:
            return
        key = login_norm.lower()
        existing = by_login.get(key)
        if existing:
            if not existing.get("perfil"):
                existing["perfil"] = perfil
            if not existing.get("pessoa") and pessoa:
                existing["pessoa"] = pessoa
            return
        new_user = {
            "usuario": login_norm,
            "senha": senha_norm,
            "perfil": perfil,
            "pessoa": pessoa or login_norm,
        }
        users.append(new_user)
        by_login[key] = new_user

    for aluno in st.session_state.get("students", []):
        ensure_login(aluno.get("usuario"), aluno.get("senha"), "Aluno", aluno.get("nome"))
    for prof in st.session_state.get("teachers", []):
        ensure_login(prof.get("usuario"), prof.get("senha"), "Professor", prof.get("nome"))

    return users

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

def parse_int(value):
    try:
        return int(str(value).strip())
    except Exception:
        return 0

def parse_date(value):
    try:
        return datetime.datetime.strptime(value, "%d/%m/%Y").date()
    except Exception:
        return None

def add_months(date_value, months):
    if not date_value:
        return None
    month = date_value.month - 1 + months
    year = date_value.year + month // 12
    month = month % 12 + 1
    day = min(date_value.day, calendar.monthrange(year, month)[1])
    return datetime.date(year, month, day)

def parse_time(value):
    try:
        return datetime.datetime.strptime(value, "%H:%M").time()
    except Exception:
        return datetime.time(0, 0)

def build_google_calendar_event_link(event):
    data = parse_date(event.get("data", ""))
    hora = parse_time(event.get("hora", ""))
    if not data:
        return ""
    inicio = datetime.datetime.combine(data, hora)
    fim = inicio + datetime.timedelta(minutes=60)
    text = event.get("titulo", "Aula")
    details_lines = []
    turma = str(event.get("turma", "")).strip()
    professor = str(event.get("professor", "")).strip()
    descricao = str(event.get("descricao", "")).strip()
    link = str(event.get("link", "")).strip()
    if turma:
        details_lines.append(f"Turma: {turma}")
    if professor:
        details_lines.append(f"Professor: {professor}")
    if descricao:
        details_lines.append(descricao)
    if link:
        details_lines.append(f"Link da aula: {link}")
    details = "\n".join(details_lines).strip()
    start_str = inicio.strftime("%Y%m%dT%H%M%S")
    end_str = fim.strftime("%Y%m%dT%H%M%S")
    params = [
        "action=TEMPLATE",
        f"text={quote(text)}",
        f"dates={start_str}/{end_str}",
    ]
    if details:
        params.append(f"details={quote(details)}")
    if link:
        params.append(f"location={quote(link)}")
    return "https://calendar.google.com/calendar/render?" + "&".join(params)

def book_levels():
    books = st.session_state.get("books", [])
    levels = [b.get("nivel", "") for b in books if b.get("nivel")]
    return levels or ["Livro 1", "Livro 2", "Livro 3", "Livro 4"]

def class_module_options():
    return [
        "Presencial em turma",
        "Online em turma",
        "Vip",
        "Intensivo vip online",
        "Kids completo presencial",
    ]

def current_week_key(date_obj=None):
    d = date_obj or datetime.date.today()
    iso = d.isocalendar()
    return f"{iso.year}-W{int(iso.week):02d}"

def _norm_book_level(level):
    level = str(level or "").strip()
    if not level:
        return ""
    # Accept "Livro 1".."Livro 4" (and minor variations).
    for i in range(1, 5):
        if str(i) in level:
            return f"Livro {i}"
    if level.lower().startswith("livro"):
        return level
    return level

def student_book_level(student_obj):
    if not isinstance(student_obj, dict):
        return ""
    livro = str(student_obj.get("livro", "")).strip()
    if livro:
        return _norm_book_level(livro)
    turma_nome = str(student_obj.get("turma", "")).strip()
    turma_obj = next((c for c in st.session_state.get("classes", []) if str(c.get("nome", "")).strip() == turma_nome), {})
    return _norm_book_level(turma_obj.get("livro", ""))

def _ensure_challenge_id(ch):
    if not isinstance(ch, dict):
        return False
    if ch.get("id"):
        return False
    ch["id"] = uuid.uuid4().hex
    return True

def _ensure_challenge_store_ids():
    changed = False
    for ch in st.session_state.get("challenges", []):
        changed = _ensure_challenge_id(ch) or changed
    if changed:
        save_list(CHALLENGES_FILE, st.session_state["challenges"])

def get_weekly_challenge(level, week_key):
    level = _norm_book_level(level)
    week_key = str(week_key or "").strip()
    for ch in st.session_state.get("challenges", []):
        if _norm_book_level(ch.get("nivel", "")) == level and str(ch.get("semana", "")).strip() == week_key:
            return ch
    return None

def upsert_weekly_challenge(level, week_key, titulo, descricao, pontos, autor, due_date=None, rubrica="", dica=""):
    level = _norm_book_level(level)
    week_key = str(week_key or "").strip()
    titulo = str(titulo or "").strip()
    descricao = str(descricao or "").strip()
    pontos = int(pontos or 0)
    autor = str(autor or "").strip()
    due_str = due_date.strftime("%d/%m/%Y") if isinstance(due_date, datetime.date) else str(due_date or "").strip()
    rubrica = str(rubrica or "").strip()
    dica = str(dica or "").strip()
    existing = get_weekly_challenge(level, week_key)
    if existing:
        existing["nivel"] = level
        existing["semana"] = week_key
        existing["titulo"] = titulo
        existing["descricao"] = descricao
        existing["pontos"] = pontos
        existing["autor"] = autor
        existing["due_date"] = due_str
        if rubrica or "rubrica" in existing:
            existing["rubrica"] = rubrica
        if dica or "dica" in existing:
            existing["dica"] = dica
        existing["updated_at"] = datetime.datetime.now().strftime("%d/%m/%Y %H:%M")
    else:
        ch = {
            "id": uuid.uuid4().hex,
            "nivel": level,
            "semana": week_key,
            "titulo": titulo,
            "descricao": descricao,
            "pontos": pontos,
            "autor": autor,
            "due_date": due_str,
            "rubrica": rubrica,
            "dica": dica,
            "created_at": datetime.datetime.now().strftime("%d/%m/%Y %H:%M"),
            "updated_at": "",
        }
        st.session_state["challenges"].append(ch)
    save_list(CHALLENGES_FILE, st.session_state["challenges"])

def has_completed_challenge(challenge_id, aluno_nome):
    cid = str(challenge_id or "").strip()
    aluno_nome = str(aluno_nome or "").strip()
    for c in st.session_state.get("challenge_completions", []):
        if str(c.get("challenge_id", "")).strip() == cid and str(c.get("aluno", "")).strip() == aluno_nome:
            status = str(c.get("status", "")).strip().lower()
            if not status:
                # Backward-compatible: old records had no status field.
                return True
            return status in ("aprovado", "concluido", "concluído", "ok", "done", "true", "1")
    return False

def get_challenge_submission(challenge_id, aluno_nome):
    cid = str(challenge_id or "").strip()
    aluno_nome = str(aluno_nome or "").strip()
    for c in st.session_state.get("challenge_completions", []):
        if str(c.get("challenge_id", "")).strip() == cid and str(c.get("aluno", "")).strip() == aluno_nome:
            return c
    return None

def complete_challenge(challenge_obj, aluno_nome, resposta=None, score=None, feedback=None, status=None, pontos_awarded=None):
    if not isinstance(challenge_obj, dict):
        return False, "Desafio invalido."
    cid = str(challenge_obj.get("id", "")).strip()
    if not cid:
        return False, "Desafio sem ID."
    aluno_nome = str(aluno_nome or "").strip()
    if not aluno_nome:
        return False, "Aluno invalido."
    existing = get_challenge_submission(cid, aluno_nome)
    existing_status = str((existing or {}).get("status", "")).strip().lower()
    if existing and (not existing_status or existing_status in ("aprovado", "concluido", "concluído", "ok", "done", "true", "1")):
        return False, "Desafio ja concluido."

    pontos_base = int(challenge_obj.get("pontos") or 0)
    pontos_final = pontos_base if pontos_awarded is None else int(pontos_awarded or 0)
    status_final = str(status or ("Aprovado" if pontos_final > 0 else "Reprovado")).strip() or "Reprovado"
    now = datetime.datetime.now().strftime("%d/%m/%Y %H:%M")

    rec = existing if existing else {"id": uuid.uuid4().hex}
    rec.update(
        {
            "challenge_id": cid,
            "aluno": aluno_nome,
            "nivel": _norm_book_level(challenge_obj.get("nivel", "")),
            "semana": str(challenge_obj.get("semana", "")).strip(),
            "pontos": int(pontos_final),
            "status": status_final,
            "done_at": now,
        }
    )
    if resposta is not None:
        rec["resposta"] = str(resposta)
    if score is not None:
        rec["score"] = int(score)
    if feedback is not None:
        rec["feedback"] = str(feedback)

    if existing:
        # updated in-place
        pass
    else:
        st.session_state["challenge_completions"].append(rec)
    save_list(CHALLENGE_COMPLETIONS_FILE, st.session_state["challenge_completions"])
    return True, "Registrado."

def student_points(aluno_nome):
    aluno_nome = str(aluno_nome or "").strip()
    return sum(int(c.get("pontos") or 0) for c in st.session_state.get("challenge_completions", []) if str(c.get("aluno", "")).strip() == aluno_nome)

def _strip_code_fences(text):
    t = str(text or "").strip()
    if t.startswith("```"):
        t = re.sub(r"^```[a-zA-Z0-9_-]*\\s*", "", t)
        t = re.sub(r"\\s*```\\s*$", "", t)
    return t.strip()

def _extract_json_object(text):
    t = _strip_code_fences(text)
    start = t.find("{")
    end = t.rfind("}")
    if start != -1 and end != -1 and end > start:
        t = t[start : end + 1]
    return json.loads(t)

def _groq_chat_text(messages, temperature=0.2, max_tokens=900):
    api_key = get_groq_api_key()
    if not api_key:
        raise RuntimeError("GROQ_API_KEY nao configurado.")
    client = OpenAI(api_key=api_key, base_url="https://api.groq.com/openai/v1")
    model_name = os.getenv("ACTIVE_CHALLENGE_MODEL", os.getenv("ACTIVE_CHATBOT_MODEL", "llama-3.3-70b-versatile"))
    result = client.chat.completions.create(
        model=model_name,
        messages=messages,
        temperature=float(temperature),
        max_tokens=int(max_tokens),
    )
    return (result.choices[0].message.content or "").strip()

def generate_weekly_challenge_ai(level, week_key):
    level = _norm_book_level(level)
    week_key = str(week_key or "").strip()
    messages = [
        {
            "role": "system",
            "content": (
                "Voce e o Professor Wiz (IA) e cria desafios semanais de ingles.\n"
                "Gere UM desafio adequado ao nivel do aluno (Livro 1..4) e que possa ser respondido no portal.\n"
                "Responda SOMENTE em JSON valido, sem markdown."
            ),
        },
        {
            "role": "user",
            "content": (
                f"Nivel: {level}\n"
                f"Semana: {week_key}\n\n"
                "Crie um desafio de 10 a 20 minutos com foco em ingles.\n"
                "Formato: resposta escrita curta (texto).\n\n"
                "Campos obrigatorios no JSON:\n"
                "titulo (string), descricao (string), pontos (int 5..50), rubrica (string curta), dica (string opcional).\n"
                "Nao use caracteres especiais no JSON alem de acentos normais."
            ),
        },
    ]
    raw = _groq_chat_text(messages, temperature=0.35, max_tokens=700)
    obj = _extract_json_object(raw)
    titulo = str(obj.get("titulo", "")).strip()
    descricao = str(obj.get("descricao", "")).strip()
    rubrica = str(obj.get("rubrica", "")).strip()
    dica = str(obj.get("dica", "")).strip()
    pontos = int(obj.get("pontos") or 10)
    pontos = max(5, min(50, pontos))
    if not titulo or not descricao:
        raise RuntimeError("IA nao retornou titulo/descricao.")
    return {
        "nivel": level,
        "semana": week_key,
        "titulo": titulo,
        "descricao": descricao,
        "pontos": pontos,
        "rubrica": rubrica,
        "dica": dica,
    }

def evaluate_challenge_answer_ai(challenge_obj, level, answer_text):
    level = _norm_book_level(level)
    titulo = str((challenge_obj or {}).get("titulo", "")).strip()
    descricao = str((challenge_obj or {}).get("descricao", "")).strip()
    rubrica = str((challenge_obj or {}).get("rubrica", "")).strip()
    answer_text = str(answer_text or "").strip()
    if not answer_text:
        return {"score": 0, "passed": False, "feedback": "Resposta vazia."}
    messages = [
        {
            "role": "system",
            "content": (
                "Voce e o Professor Wiz (IA) e avalia respostas de desafios de ingles.\n"
                "Avalie com rigor justo e devolva um feedback curto e pratico.\n"
                "Responda SOMENTE em JSON valido, sem markdown."
            ),
        },
        {
            "role": "user",
            "content": (
                f"Nivel: {level}\n"
                f"Desafio (titulo): {titulo}\n"
                f"Desafio (descricao): {descricao}\n"
                f"Rubrica: {rubrica}\n\n"
                f"Resposta do aluno:\n{answer_text}\n\n"
                "Retorne JSON com:\n"
                "score (int 0..100), passed (bool), feedback (string curta em portugues).\n"
                "Regra: passed = true se score >= 70."
            ),
        },
    ]
    raw = _groq_chat_text(messages, temperature=0.15, max_tokens=450)
    obj = _extract_json_object(raw)
    score = int(obj.get("score") or 0)
    score = max(0, min(100, score))
    passed = bool(obj.get("passed")) if "passed" in obj else (score >= 70)
    feedback = str(obj.get("feedback", "")).strip() or "Feedback indisponivel."
    if score >= 70:
        passed = True
    else:
        passed = False
    return {"score": score, "passed": passed, "feedback": feedback}

def material_payment_options():
    return [
        "A vista",
        "Parcelado no Cartao",
        "Parcelado no Boleto",
        "Pix",
        "Dinheiro",
    ]

def material_payment_to_cobranca(payment_type):
    if payment_type == "Parcelado no Cartao":
        return "Cartao"
    if payment_type == "Parcelado no Boleto":
        return "Boleto"
    if payment_type == "A vista":
        return "A vista"
    return payment_type

def is_overdue(item):
    if item.get("status") == "Pago": return False
    venc = parse_date(item.get("vencimento", ""))
    if not venc: return False
    return venc < datetime.date.today()

def sort_agenda(items):
    return sorted(
        items,
        key=lambda a: (
            parse_date(a.get("data", "")) or datetime.date(1900, 1, 1),
            parse_time(a.get("hora", "")),
        ),
    )

def render_agenda(items, empty_message):
    if not items:
        st.info(empty_message)
        return
    for idx, a in enumerate(items):
        st.markdown(f"**{a.get('titulo', 'Aula agendada')}**")
        st.caption(f"Turma: {a.get('turma', '')} | Professor: {a.get('professor', '')}")
        st.write(f"Data: {a.get('data', '')} | Horário: {a.get('hora', '')}")
        if a.get("descricao"):
            st.write(a.get("descricao"))
        if a.get("link"):
            st.link_button("Entrar na aula", a.get("link"), key=f"agenda_live_{idx}_{a.get('data','')}_{a.get('hora','')}")
        google_url = a.get("google_calendar_link") or build_google_calendar_event_link(a)
        if google_url:
            st.link_button("Adicionar no Google Agenda", google_url, key=f"agenda_google_{idx}_{a.get('data','')}_{a.get('hora','')}")
        st.markdown("---")

def render_books_section(books, title="Livros Didáticos", key_prefix="books"):
    st.markdown(f"### {title}")
    if not books:
        st.info("Nenhum livro disponível.")
        return
    for idx, b in enumerate(books):
        titulo = b.get("titulo") or b.get("nivel") or "Livro"
        st.markdown(f"**{titulo}**")
        c1, c2 = st.columns(2)
        file_path = str(b.get("file_path", "")).strip()
        url = str(b.get("url", "")).strip()
        if file_path and Path(file_path).exists():
            data = Path(file_path).read_bytes()
            c1.download_button("Baixar livro", data=data, file_name=Path(file_path).name, key=f"{key_prefix}_download_{idx}")
        elif url:
            c1.link_button("Baixar livro", url, key=f"{key_prefix}_link_{idx}")
        else:
            c1.button("Baixar livro", disabled=True, key=f"{key_prefix}_disabled_{idx}")

        if url:
            c2.link_button("Abrir livro", url, key=f"{key_prefix}_open_{idx}")
        else:
            c2.button("Abrir livro", disabled=True, key=f"{key_prefix}_open_disabled_{idx}")
        if not url and not (file_path and Path(file_path).exists()):
            st.caption("Link/arquivo do livro não configurado.")
        st.markdown("---")

def build_certificate_html(data, logo_left_b64="", logo_right_b64=""):
    logo_html = ""
    if logo_left_b64 or logo_right_b64:
        left = f"<img src='data:image/png;base64,{logo_left_b64}' style='height:70px;'/>" if logo_left_b64 else ""
        right = f"<img src='data:image/png;base64,{logo_right_b64}' style='height:70px;'/>" if logo_right_b64 else ""
        logo_html = f"""
        <div style="display:flex; justify-content:space-between; align-items:center; gap:20px; margin-bottom:16px;">
          <div style="flex:1; text-align:left;">{left}</div>
          <div style="flex:1; text-align:right;">{right}</div>
        </div>
        """
    return f"""
<!DOCTYPE html>
<html lang="pt-br">
<head>
  <meta charset="UTF-8" />
  <title>Certificado</title>
  <style>
    body {{ background:#f3f4f6; font-family:'Georgia', serif; margin:0; padding:30px; }}
    .cert {{ max-width:900px; margin:0 auto; background:white; border:10px solid #0f172a; padding:50px 60px; }}
    .title {{ font-size:36px; font-weight:700; text-align:center; letter-spacing:2px; color:#0f172a; }}
    .subtitle {{ font-size:14px; text-align:center; color:#64748b; margin-top:6px; }}
    .name {{ font-size:30px; font-weight:700; text-align:center; margin:24px 0 8px; color:#1e3a8a; }}
    .text {{ font-size:18px; line-height:1.6; text-align:center; color:#111827; }}
    .meta {{ display:flex; justify-content:space-between; margin-top:32px; font-size:14px; color:#475569; }}
    .signature {{ margin-top:50px; display:flex; justify-content:space-between; gap:20px; }}
    .sig-box {{ flex:1; text-align:center; }}
    .sig-line {{ border-top:1px solid #111827; margin-top:30px; }}
    .foot {{ font-size:12px; color:#64748b; text-align:center; margin-top:18px; }}
  </style>
</head>
<body>
  <div class="cert">
    {logo_html}
    <div class="title">CERTIFICADO</div>
    <div class="subtitle">{data.get("instituicao","")}</div>
    <div class="text" style="margin-top:24px;">Certificamos que</div>
    <div class="name">{data.get("aluno","")}</div>
    <div class="text">
      concluiu o curso <strong>{data.get("curso","")}</strong>
      com carga horária de <strong>{data.get("carga","")}</strong> horas,
      em {data.get("data","")}.
    </div>
    <div class="meta">
      <div>Turma: {data.get("turma","")}</div>
      <div>Professor: {data.get("professor","")}</div>
    </div>
    <div class="signature">
      <div class="sig-box">
        <div class="sig-line"></div>
        <div>{data.get("assinatura1","Coordenação")}</div>
      </div>
      <div class="sig-box">
        <div class="sig-line"></div>
        <div>{data.get("assinatura2","Direção")}</div>
      </div>
    </div>
    <div class="foot">{data.get("observacao","")}</div>
  </div>
</body>
</html>
""".strip()

def build_certificate_pdf_bytes(data, logo_left_path=None, logo_right_path=None):
    try:
        from fpdf import FPDF
    except Exception:
        return None

    def _safe(text):
        try:
            return str(text).encode("latin-1", "ignore").decode("latin-1")
        except Exception:
            return str(text)

    pdf = FPDF(orientation="P", unit="mm", format="A4")
    pdf.set_auto_page_break(auto=False)
    pdf.add_page()

    # Border
    pdf.set_draw_color(15, 23, 42)
    pdf.set_line_width(1)
    pdf.rect(8, 8, 194, 281)

    y = 12
    if logo_left_path and logo_left_path.exists():
        try:
            pdf.image(str(logo_left_path), x=12, y=y, w=35)
        except Exception:
            pass
    if logo_right_path and logo_right_path.exists():
        try:
            pdf.image(str(logo_right_path), x=163, y=y, w=35)
        except Exception:
            pass

    pdf.set_y(35)
    pdf.set_font("Helvetica", "B", 22)
    pdf.cell(0, 10, _safe("CERTIFICADO"), ln=1, align="C")
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(100, 116, 139)
    pdf.cell(0, 6, _safe(data.get("instituicao", "")), ln=1, align="C")
    pdf.set_text_color(0, 0, 0)
    pdf.ln(8)

    pdf.set_font("Helvetica", "", 12)
    pdf.cell(0, 8, _safe("Certificamos que"), ln=1, align="C")
    pdf.set_font("Helvetica", "B", 18)
    pdf.cell(0, 10, _safe(data.get("aluno", "")), ln=1, align="C")
    pdf.ln(2)

    pdf.set_font("Helvetica", "", 11)
    texto = (
        f"concluiu o curso {data.get('curso','')}, "
        f"com carga horária de {data.get('carga','')} horas, "
        f"em {data.get('data','')}."
    )
    pdf.multi_cell(0, 7, _safe(texto), align="C")
    pdf.ln(4)

    pdf.set_font("Helvetica", "", 10)
    pdf.cell(0, 6, _safe(f"Turma: {data.get('turma','')}"), align="L")
    pdf.cell(0, 6, _safe(f"Professor: {data.get('professor','')}"), ln=1, align="R")
    pdf.ln(20)

    y_line = pdf.get_y()
    pdf.line(30, y_line, 90, y_line)
    pdf.line(120, y_line, 180, y_line)
    pdf.set_font("Helvetica", "", 9)
    pdf.set_y(y_line + 4)
    pdf.set_x(30)
    pdf.cell(60, 6, _safe(data.get("assinatura1", "Coordenacao")), align="C")
    pdf.set_x(120)
    pdf.cell(60, 6, _safe(data.get("assinatura2", "Direcao")), align="C")

    obs = _safe(data.get("observacao", ""))
    if obs:
        pdf.set_text_color(100, 116, 139)
        pdf.set_font("Helvetica", "I", 8)
        pdf.set_y(280)
        pdf.cell(0, 6, obs, align="C")
        pdf.set_text_color(0, 0, 0)

    return pdf.output(dest="S").encode("latin-1", "ignore")

def add_receivable(aluno, descricao, valor, vencimento, cobranca, categoria, data_lancamento=None, valor_parcela=None, parcela=None, numero_pedido="", item_codigo=""):
    prefix = re.sub(r"[^A-Z0-9]+", "", str(cobranca).upper()) or "REC"
    codigo = f"{prefix}-{uuid.uuid4().hex[:8].upper()}"
    st.session_state["receivables"].append({
        "descricao": descricao.strip() or "Mensalidade",
        "aluno": aluno.strip(),
        "categoria": categoria,
        "cobranca": cobranca,
        "codigo": codigo,
        "valor": valor.strip(),
        "data": data_lancamento.strftime("%d/%m/%Y") if data_lancamento else datetime.date.today().strftime("%d/%m/%Y"),
        "valor_parcela": str(valor_parcela).strip() if valor_parcela is not None else valor.strip(),
        "parcela": parcela or "",
        "numero_pedido": str(numero_pedido).strip(),
        "item_codigo": str(item_codigo).strip(),
        "vencimento": vencimento.strftime("%d/%m/%Y"),
        "status": "Aberto",
    })
    save_list(RECEIVABLES_FILE, st.session_state["receivables"])
    return codigo

def allowed_portals(profile):
    if profile == "Aluno": return ["Aluno"]
    if profile == "Professor": return ["Professor"]
    if profile == "Coordenador": return ["Aluno", "Professor", "Coordenador"]
    if profile == "Admin": return ["Aluno", "Professor", "Coordenador"]
    return []

def _send_email_smtp(to_email, subject, body):
    host = os.getenv("ACTIVE_SMTP_HOST", "").strip()
    if not host:
        return False, "SMTP nao configurado"
    port = int(os.getenv("ACTIVE_SMTP_PORT", "587"))
    user = os.getenv("ACTIVE_SMTP_USER", "").strip()
    password = os.getenv("ACTIVE_SMTP_PASS", "").strip()
    use_tls = os.getenv("ACTIVE_SMTP_TLS", "1").strip() not in ("0", "false", "False")
    sender = os.getenv("ACTIVE_EMAIL_FROM", user or "noreply@active.local").strip()
    try:
        msg = EmailMessage()
        msg["Subject"] = subject
        msg["From"] = sender
        msg["To"] = to_email
        msg.set_content(body)
        with smtplib.SMTP(host, port, timeout=20) as smtp:
            if use_tls:
                smtp.starttls()
            if user and password:
                smtp.login(user, password)
            smtp.send_message(msg)
        return True, "enviado"
    except Exception as exc:
        return False, f"falha SMTP: {exc}"

def _message_recipients_for_student(student):
    recipients = set()
    email_aluno = str(student.get("email", "")).strip().lower()
    if email_aluno:
        recipients.add(email_aluno)
    responsavel = student.get("responsavel", {})
    if not isinstance(responsavel, dict):
        responsavel = {}
    resp_email = str(responsavel.get("email", "")).strip().lower()
    if resp_email:
        recipients.add(resp_email)
    return sorted(recipients)

def email_students_by_turma(turma, assunto, corpo, origem):
    delivered = 0
    total = 0
    for student in st.session_state["students"]:
        if turma == "Todas" or student.get("turma") == turma:
            for email in _message_recipients_for_student(student):
                ok, status = _send_email_smtp(email, assunto, corpo)
                total += 1
                if ok:
                    delivered += 1
                st.session_state["email_log"].append({
                    "destinatario": student.get("nome", "Aluno"),
                    "email": email,
                    "assunto": assunto,
                    "mensagem": corpo,
                    "origem": origem,
                    "status": status,
                    "data": datetime.date.today().strftime("%d/%m/%Y"),
                })
    save_list(EMAIL_LOG_FILE, st.session_state["email_log"])
    return {"total": total, "enviados": delivered}

def email_students_by_level(level, assunto, corpo, origem):
    level = _norm_book_level(level)
    delivered = 0
    total = 0
    for student in st.session_state.get("students", []):
        if student_book_level(student) != level:
            continue
        for email in _message_recipients_for_student(student):
            ok, status = _send_email_smtp(email, assunto, corpo)
            total += 1
            if ok:
                delivered += 1
            st.session_state["email_log"].append(
                {
                    "destinatario": student.get("nome", "Aluno"),
                    "email": email,
                    "assunto": assunto,
                    "mensagem": corpo,
                    "origem": origem,
                    "status": status,
                    "data": datetime.date.today().strftime("%d/%m/%Y"),
                }
            )
    save_list(EMAIL_LOG_FILE, st.session_state["email_log"])
    return {"total": total, "enviados": delivered}

def post_message_and_notify(autor, titulo, mensagem, turma="Todas", origem="Mensagens"):
    mensagem_obj = {
        "titulo": (titulo or "Aviso").strip(),
        "mensagem": (mensagem or "").strip(),
        "data": datetime.date.today().strftime("%d/%m/%Y"),
        "autor": autor.strip() if autor else "Sistema",
        "turma": turma or "Todas",
    }
    st.session_state["messages"].append(mensagem_obj)
    save_list(MESSAGES_FILE, st.session_state["messages"])
    assunto = f"[Active] {mensagem_obj['titulo']}"
    corpo = (
        f"Mensagem publicada por {mensagem_obj['autor']}\n"
        f"Turma: {mensagem_obj['turma']}\n"
        f"Data: {mensagem_obj['data']}\n\n"
        f"{mensagem_obj['mensagem']}"
    )
    return email_students_by_turma(mensagem_obj["turma"], assunto, corpo, origem)

def sidebar_menu(title, options, key):
    st.markdown(f"<h3 style='color:#1e3a8a; font-family:Sora; margin-top:0;'>{title}</h3>", unsafe_allow_html=True)
    if key not in st.session_state or st.session_state.get(key) not in options:
        st.session_state[key] = options[0]
    for option in options:
        active = st.session_state[key] == option
        if st.button(option, key=f"{key}_{option}", type="primary" if active else "secondary"):
            st.session_state[key] = option
            st.rerun()
    return st.session_state[key]

STUDENT_IMPORT_COLUMNS = [
    "nome",
    "matricula",
    "turma",
    "email",
    "celular",
    "data_nascimento",
    "idade",
    "rg",
    "cpf",
    "cidade",
    "bairro",
    "cidade_natal",
    "pais",
    "cep",
    "rua",
    "numero",
    "modulo",
    "livro",
    "usuario",
    "senha",
    "responsavel_nome",
    "responsavel_cpf",
    "responsavel_celular",
    "responsavel_email",
]

def _normalize_excel_column(value):
    return (
        str(value or "")
        .strip()
        .lower()
        .replace(" ", "_")
        .replace("-", "_")
        .replace("/", "_")
        .replace(".", "_")
    )

def _safe_str(value):
    if value is None:
        return ""
    if isinstance(value, float) and pd.isna(value):
        return ""
    return str(value).strip()

def _safe_int(value):
    if value is None:
        return None
    if isinstance(value, float) and pd.isna(value):
        return None
    try:
        return int(float(value))
    except Exception:
        return None

def _date_to_str(value):
    if value is None:
        return ""
    if isinstance(value, float) and pd.isna(value):
        return ""
    if isinstance(value, datetime.datetime):
        return value.strftime("%d/%m/%Y")
    if isinstance(value, datetime.date):
        return value.strftime("%d/%m/%Y")
    try:
        parsed = pd.to_datetime(value, dayfirst=True, errors="coerce")
        if pd.isna(parsed):
            return _safe_str(value)
        return parsed.strftime("%d/%m/%Y")
    except Exception:
        return _safe_str(value)

def _calc_age_from_date(date_str):
    if not date_str:
        return None
    try:
        dt = datetime.datetime.strptime(date_str, "%d/%m/%Y").date()
    except Exception:
        return None
    today = datetime.date.today()
    age = today.year - dt.year - ((today.month, today.day) < (dt.month, dt.day))
    return age if age >= 0 else None

def _calc_age_from_date_obj(date_value):
    if not isinstance(date_value, datetime.date):
        return None
    today = datetime.date.today()
    age = today.year - date_value.year - ((today.month, today.day) < (date_value.month, date_value.day))
    return age if age >= 0 else None

def _next_student_matricula(students):
    used = set()
    max_num = 0
    for student in students or []:
        raw = str(student.get("matricula", "")).strip()
        if not raw:
            continue
        digits = "".join(ch for ch in raw if ch.isdigit())
        if not digits:
            continue
        num = int(digits)
        used.add(str(num))
        if num > max_num:
            max_num = num
    candidate = max_num + 1 if max_num > 0 else len(students or []) + 1
    if candidate < 1:
        candidate = 1
    while str(candidate) in used:
        candidate += 1
    return str(candidate)

def _build_students_export_df(students):
    df = pd.json_normalize(students) if students else pd.DataFrame()
    if not df.empty:
        df = df.rename(
            columns={
                "responsavel.nome": "responsavel_nome",
                "responsavel.cpf": "responsavel_cpf",
                "responsavel.celular": "responsavel_celular",
                "responsavel.email": "responsavel_email",
                "nascimento": "data_nascimento",
            }
        )
    for col in STUDENT_IMPORT_COLUMNS:
        if col not in df.columns:
            df[col] = ""
    df = df[STUDENT_IMPORT_COLUMNS]
    return df

def _normalize_import_df(df):
    if df is None or df.empty:
        return pd.DataFrame(columns=STUDENT_IMPORT_COLUMNS)
    aliases = {
        "nome": "nome",
        "aluno": "nome",
        "matricula": "matricula",
        "numero_matricula": "matricula",
        "numero_da_matricula": "matricula",
        "n_matricula": "matricula",
        "turma": "turma",
        "email": "email",
        "e_mail": "email",
        "celular": "celular",
        "telefone": "celular",
        "data_nascimento": "data_nascimento",
        "nascimento": "data_nascimento",
        "idade": "idade",
        "rg": "rg",
        "cpf": "cpf",
        "cidade": "cidade",
        "bairro": "bairro",
        "cidade_natal": "cidade_natal",
        "pais": "pais",
        "cep": "cep",
        "rua": "rua",
        "numero": "numero",
        "modulo": "modulo",
        "livro": "livro",
        "usuario": "usuario",
        "login": "usuario",
        "senha": "senha",
        "responsavel_nome": "responsavel_nome",
        "responsavel_cpf": "responsavel_cpf",
        "responsavel_celular": "responsavel_celular",
        "responsavel_email": "responsavel_email",
        "responsavel_cel": "responsavel_celular",
        "responsavel_telefone": "responsavel_celular",
    }
    rename_map = {}
    for col in df.columns:
        norm = _normalize_excel_column(col)
        mapped = aliases.get(norm)
        if mapped:
            rename_map[col] = mapped
    df = df.rename(columns=rename_map)
    for col in STUDENT_IMPORT_COLUMNS:
        if col not in df.columns:
            df[col] = ""
    return df[STUDENT_IMPORT_COLUMNS]

def _student_from_row(row):
    nome = _safe_str(row.get("nome"))
    email = _safe_str(row.get("email"))
    if not nome or not email:
        return None

    turma = _safe_str(row.get("turma")) or "Sem Turma"
    data_nascimento = _date_to_str(row.get("data_nascimento"))
    idade = _safe_int(row.get("idade"))
    if idade is None:
        idade = _calc_age_from_date(data_nascimento) or ""

    responsavel = {
        "nome": _safe_str(row.get("responsavel_nome")),
        "cpf": _safe_str(row.get("responsavel_cpf")),
        "celular": _safe_str(row.get("responsavel_celular")),
        "email": _safe_str(row.get("responsavel_email")),
    }

    return {
        "nome": nome,
        "matricula": _safe_str(row.get("matricula")),
        "turma": turma,
        "email": email,
        "celular": _safe_str(row.get("celular")),
        "data_nascimento": data_nascimento,
        "idade": idade,
        "rg": _safe_str(row.get("rg")),
        "cpf": _safe_str(row.get("cpf")),
        "cidade": _safe_str(row.get("cidade")),
        "bairro": _safe_str(row.get("bairro")),
        "cidade_natal": _safe_str(row.get("cidade_natal")),
        "pais": _safe_str(row.get("pais")),
        "cep": _safe_str(row.get("cep")),
        "rua": _safe_str(row.get("rua")),
        "numero": _safe_str(row.get("numero")),
        "modulo": _safe_str(row.get("modulo")),
        "livro": _safe_str(row.get("livro")),
        "usuario": _safe_str(row.get("usuario")),
        "senha": _safe_str(row.get("senha")),
        "responsavel": responsavel,
    }

def _normalize_turma(value):
    return str(value or "").strip()

def filter_items_by_turma(items, turma):
    if not turma:
        return items
    if isinstance(turma, (list, tuple, set)):
        allowed = {t for t in (str(x).strip() for x in turma) if t}
        if not allowed:
            return items
    else:
        allowed = {_normalize_turma(turma)}
    filtered = []
    for item in items:
        item_turma = _normalize_turma(item.get("turma"))
        if not item_turma or item_turma.lower() in ("todas", "todos"):
            filtered.append(item)
        elif item_turma in allowed:
            filtered.append(item)
    return filtered

def render_library(title="Biblioteca", turma=None, turma_options=None):
    st.markdown(f'<div class="main-header">{title}</div>', unsafe_allow_html=True)
    turma_selecionada = None
    if turma_options:
        turma_selecionada = st.selectbox("Filtrar por Turma", ["Todas"] + turma_options)
    tab1, tab2, tab3 = st.tabs(["Materiais", "Noticias", "Videos"])

    with tab1:
        materiais = st.session_state["materials"]
        if turma_selecionada and turma_selecionada != "Todas":
            materiais = filter_items_by_turma(materiais, turma_selecionada)
        else:
            materiais = filter_items_by_turma(materiais, turma)
        if not materiais:
            st.info("Sem materiais.")
        else:
            for m in reversed(materiais):
                titulo = m.get("titulo", "Material")
                st.markdown(f"**{titulo}**")
                if m.get("descricao"):
                    st.write(m.get("descricao"))
                meta = []
                if m.get("turma"):
                    meta.append(f"Turma: {m.get('turma')}")
                if m.get("autor"):
                    meta.append(f"Autor: {m.get('autor')}")
                if m.get("data"):
                    meta.append(f"Data: {m.get('data')}")
                if meta:
                    st.caption(" | ".join(meta))
                if m.get("link"):
                    st.markdown(f"[Baixar/Ver material]({m.get('link')})")
                st.markdown("---")

    with tab2:
        noticias = st.session_state["messages"]
        if not noticias:
            st.info("Sem noticias.")
        else:
            for msg in reversed(noticias):
                with st.container():
                    st.markdown(
                        f"""<div style="background:white; padding:16px; border-radius:12px; border:1px solid #e2e8f0; margin-bottom:10px;">
                        <div style="font-weight:700; color:#1e3a8a;">{msg.get('titulo','Noticia')}</div>
                        <div style="font-size:0.85rem; color:#64748b; margin-bottom:8px;">{msg.get('data','')} | {msg.get('autor','')}</div>
                        <div>{msg.get('mensagem','')}</div></div>""",
                        unsafe_allow_html=True,
                    )

    with tab3:
        videos = st.session_state["videos"]
        if turma_selecionada and turma_selecionada != "Todas":
            videos = filter_items_by_turma(videos, turma_selecionada)
        else:
            videos = filter_items_by_turma(videos, turma)
        if not videos:
            st.info("Sem videos.")
        else:
            for v in reversed(videos):
                titulo = v.get("titulo", "Video")
                data = v.get("data", "")
                autor = v.get("autor", "")
                with st.expander(f"{titulo}" + (f" ({data})" if data else "")):
                    meta = []
                    if v.get("turma"):
                        meta.append(f"Turma: {v.get('turma')}")
                    if autor:
                        meta.append(f"Autor: {autor}")
                    if meta:
                        st.caption(" | ".join(meta))
                    if v.get("url"):
                        st.video(v.get("url"))

def get_groq_api_key():
    key = ""
    try:
        key = str(st.secrets.get("GROQ_API_KEY", "")).strip()
    except Exception:
        key = ""
    if not key:
        key = str(os.getenv("GROQ_API_KEY", "")).strip()
    return key

def get_active_chat_history_key():
    role = (st.session_state.get("role") or "").strip().lower()
    user = (st.session_state.get("user_name") or "").strip().lower()
    return f"{role}:{user}"

def get_active_context_text():
    role = st.session_state.get("role", "")
    user_name = st.session_state.get("user_name", "")
    unit = st.session_state.get("unit", "")
    lines = [
        "Contexto do sistema Active Educacional/Mister Wiz:",
        f"Perfil logado: {role}",
        f"Usuario: {user_name}",
    ]
    if unit:
        lines.append(f"Unidade: {unit}")

    if role == "Aluno":
        aluno = next((s for s in st.session_state["students"] if s.get("nome") == user_name), {})
        turma = aluno.get("turma", "Sem Turma")
        pendencias = [r for r in st.session_state["receivables"] if r.get("aluno") == user_name and r.get("status") != "Pago"]
        lines.append(f"Turma do aluno: {turma}")
        lines.append(f"Pendencias financeiras abertas: {len(pendencias)}")
    elif role == "Professor":
        prof = user_name.strip().lower()
        turmas = [c for c in st.session_state["classes"] if str(c.get("professor", "")).strip().lower() == prof]
        qtd_alunos = len([s for s in st.session_state["students"] if s.get("turma") in {t.get("nome") for t in turmas}])
        lines.append(f"Turmas do professor: {len(turmas)}")
        lines.append(f"Total de alunos nas turmas: {qtd_alunos}")
    elif role == "Coordenador":
        lines.append(f"Total de alunos: {len(st.session_state['students'])}")
        lines.append(f"Total de professores: {len(st.session_state['teachers'])}")
        lines.append(f"Total de turmas: {len(st.session_state['classes'])}")
        lines.append(f"Mensagens cadastradas: {len(st.session_state['messages'])}")

    return "\n".join(lines)

def get_active_system_prompt(mode, include_context=True):
    role = st.session_state.get("role", "")
    base = [
        "Voce e o assistente oficial da Active Educacional e da escola de ingles Mister Wiz.",
        "Nunca mencione DietHealth.",
        "Responda em portugues do Brasil, com foco pratico e claro.",
        "Quando faltar contexto, pergunte objetivamente antes de concluir.",
        "Evite inventar dados. Se nao souber, diga que nao ha dados suficientes.",
    ]

    mode_map = {
        "Atendimento": "Atue como atendimento escolar: linguagem acolhedora, objetiva e orientada a solucao.",
        "Pedagogico": "Atue como consultor pedagogico: planos de aula, atividades, rubricas e reforco escolar.",
        "Comercial": "Atue como consultor comercial da escola: capte interesse sem promessas irreais.",
        "Financeiro": "Atue como assistente financeiro educacional: comunicacao de cobranca clara e respeitosa.",
        "Secretaria": "Atue como secretaria escolar: matriculas, documentos, calendarios, horarios e orientacoes administrativas.",
    }
    base.append(mode_map.get(mode, mode_map["Atendimento"]))
    base.append(f"Perfil atual do usuario no sistema: {role}.")
    if include_context:
        base.append(get_active_context_text())
    return "\n".join(base)

def get_tutor_wiz_prompt():
    return "\n".join(
        [
            "Voce e o Professor Wiz (IA) da escola de ingles Mister Wiz.",
            "Ajude o aluno a estudar apenas ingles (gramatica, vocabulario, pronuncia, conversacao e exercicios).",
            "Se o aluno perguntar algo fora do contexto de ingles, recuse e oriente a perguntar sobre ingles.",
            "Responda em portugues do Brasil, com exemplos em ingles quando fizer sentido.",
            "Se nao souber, diga que nao ha dados suficientes.",
        ]
    )

def run_active_chatbot():
    st.markdown('<div class="main-header">Professor Wiz</div>', unsafe_allow_html=True)
    st.caption("Assistente dedicado ao contexto da Active Educacional e Mister Wiz.")

    api_key = get_groq_api_key()
    if not api_key:
        st.error("Configure GROQ_API_KEY em secrets ou variavel de ambiente para usar o chatbot.")
        return

    c1, c2, c3 = st.columns([1.2, 1, 1])
    with c1:
        role = st.session_state.get("role", "")
        if role == "Aluno":
            mode_options = ["Financeiro", "Pedagogico", "Secretaria"]
        else:
            mode_options = ["Atendimento", "Pedagogico", "Comercial", "Financeiro"]
        if st.session_state.get("active_chat_mode") not in mode_options:
            st.session_state["active_chat_mode"] = mode_options[0]
        mode = st.selectbox("Modo", mode_options, key="active_chat_mode")
    include_context = True
    if not (role == "Aluno" and mode == "Secretaria"):
        with c2:
            include_context = st.checkbox("Usar contexto do sistema", value=True)
        with c3:
            st.session_state["active_chat_temp"] = st.slider("Criatividade", min_value=0.0, max_value=1.0, value=float(st.session_state["active_chat_temp"]), step=0.05)

    if role == "Aluno" and mode == "Secretaria":
        st.info("Para abrir um chamado na secretaria, clique abaixo.")
        st.link_button("Abrir chamado no WhatsApp", f"https://wa.me/{WHATSAPP_NUMBER}", type="primary")
        return

    chat_key = get_active_chat_history_key()
    if role == "Aluno" and mode == "Pedagogico":
        chat_key = f"tutor:{chat_key}"
    if chat_key not in st.session_state["active_chat_histories"]:
        st.session_state["active_chat_histories"][chat_key] = []
    chat_history = st.session_state["active_chat_histories"][chat_key]

    if role == "Aluno" and mode == "Pedagogico":
        st.caption("Professor Wiz (IA): ajuda apenas com ingles.")
        st.radio("Opcao", ["Estudar"], index=0, key="tutor_option")
    else:
        qa1, qa2, qa3 = st.columns(3)
        if qa1.button("Sugestao de resposta para responsavel"):
            chat_history.append({"role": "user", "content": "Crie uma resposta curta e profissional para um responsavel sobre desempenho do aluno."})
        if qa2.button("Plano de aula de 50 minutos"):
            chat_history.append({"role": "user", "content": "Monte um plano de aula de ingles de 50 minutos para nivel iniciante, com objetivos e atividade final."})
        if qa3.button("Follow-up comercial no WhatsApp"):
            chat_history.append({"role": "user", "content": "Escreva uma mensagem de follow-up comercial para lead de curso de ingles, tom consultivo e direto."})

    for msg in chat_history:
        with st.chat_message("assistant" if msg["role"] == "assistant" else "user"):
            st.markdown(msg["content"])

    action1, action2 = st.columns([1, 1])
    if action1.button("Limpar conversa"):
        st.session_state["active_chat_histories"][chat_key] = []
        st.rerun()
    if action2.button("Salvar conversa"):
        st.session_state["chatbot_log"].append({
            "data": datetime.datetime.now().strftime("%d/%m/%Y %H:%M"),
            "usuario": st.session_state.get("user_name", ""),
            "perfil": st.session_state.get("role", ""),
            "mensagens": chat_history,
        })
        save_list(CHATBOT_LOG_FILE, st.session_state["chatbot_log"])
        st.success("Conversa salva no historico do Active.")

    prompt_label = "Digite sua mensagem para o chatbot"
    if role == "Aluno" and mode == "Pedagogico":
        prompt_label = "Pergunte algo de ingles"
    user_text = st.chat_input(prompt_label)
    if user_text:
        chat_history.append({"role": "user", "content": user_text})
        if role == "Aluno" and mode == "Pedagogico":
            system_prompt = get_tutor_wiz_prompt()
        else:
            system_prompt = get_active_system_prompt(mode, include_context)
        request_messages = [{"role": "system", "content": system_prompt}] + chat_history[-16:]

        client = OpenAI(api_key=api_key, base_url="https://api.groq.com/openai/v1")
        model_name = os.getenv("ACTIVE_CHATBOT_MODEL", "llama-3.3-70b-versatile")
        with st.spinner("Gerando resposta..."):
            try:
                result = client.chat.completions.create(
                    model=model_name,
                    messages=request_messages,
                    temperature=float(st.session_state["active_chat_temp"]),
                    max_tokens=1000,
                )
                answer = (result.choices[0].message.content or "").strip()
                if not answer:
                    answer = "Nao consegui gerar resposta no momento. Tente novamente."
            except Exception as ex:
                answer = f"Falha ao consultar IA: {ex}"

        chat_history.append({"role": "assistant", "content": answer})
        st.session_state["active_chat_histories"][chat_key] = chat_history
        st.rerun()

def run_student_finance_assistant():
    st.markdown('<div class="main-header">Financeiro</div>', unsafe_allow_html=True)
    st.caption("Escolha uma opcao abaixo para falar com a IA.")

    api_key = get_groq_api_key()
    if not api_key:
        st.error("Configure GROQ_API_KEY em secrets ou variavel de ambiente para usar o assistente financeiro.")
        return

    chat_key = f"finance:{get_active_chat_history_key()}"
    if chat_key not in st.session_state["active_chat_histories"]:
        st.session_state["active_chat_histories"][chat_key] = []
    chat_history = st.session_state["active_chat_histories"][chat_key]

    options = [
        "Historico de pagamentos",
        "Parcelas a vencer",
        "Parcelas vencidas",
        "Segunda via de boletos",
        "Quitar divida",
        "Renegociacao",
        "Abrir chamado",
    ]
    choice = st.selectbox("Opcoes financeiras", options, index=0, key="finance_choice")

    col1, col2 = st.columns([1, 1])
    if col1.button("Consultar", type="primary"):
        chat_history.append({"role": "user", "content": f"Quero ajuda com: {choice}."})
        system_prompt = get_active_system_prompt("Financeiro", include_context=True)
        system_prompt += (
            "\nAtenda somente aos temas: historico de pagamentos, parcelas a vencer, parcelas vencidas, "
            "segunda via de boletos, quitar divida, renegociacao e abrir chamado."
            "\nSe o pedido fugir desses temas, oriente o aluno a escolher uma das opcoes."
        )
        request_messages = [{"role": "system", "content": system_prompt}] + chat_history[-12:]

        client = OpenAI(api_key=api_key, base_url="https://api.groq.com/openai/v1")
        model_name = os.getenv("ACTIVE_CHATBOT_MODEL", "llama-3.3-70b-versatile")
        with st.spinner("Gerando resposta..."):
            try:
                result = client.chat.completions.create(
                    model=model_name,
                    messages=request_messages,
                    temperature=float(st.session_state["active_chat_temp"]),
                    max_tokens=800,
                )
                answer = (result.choices[0].message.content or "").strip()
                if not answer:
                    answer = "Nao consegui gerar resposta no momento. Tente novamente."
            except Exception as ex:
                answer = f"Falha ao consultar IA: {ex}"

        chat_history.append({"role": "assistant", "content": answer})
        st.session_state["active_chat_histories"][chat_key] = chat_history
        st.rerun()

    if col2.button("Limpar conversa"):
        st.session_state["active_chat_histories"][chat_key] = []
        st.rerun()

    for msg in chat_history:
        with st.chat_message("assistant" if msg["role"] == "assistant" else "user"):
            st.markdown(msg["content"])

# ==============================================================================
# CSS DINAMICO
# ==============================================================================

if not st.session_state.get("logged_in", False):
    st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Sora:wght@400;700&family=Inter:wght@400;600&display=swap');
        html, body { background: transparent !important; }
        .stApp { background: radial-gradient(1200px 600px at 10% 10%, rgba(59,130,246,0.25), transparent 60%), linear-gradient(135deg, #0b1020 0%, #1e3a8a 45%, #2f6fe6 100%); font-family: 'Inter', sans-serif; }
        header, footer {visibility: hidden;}
        section[data-testid="stMain"], div[data-testid="stAppViewContainer"], div[data-testid="stAppViewContainer"] > section, div[data-testid="stMainBlockContainer"], div[data-testid="stMainBlockContainer"] > div, section.main, div.main { background: transparent !important; box-shadow: none !important; border-radius: 0 !important; }
        .block-container { padding-top: 3.5rem; padding-bottom: 4rem; max-width: 1500px; background: transparent !important; box-shadow: none !important; }
        .hero-card { background: rgba(255, 255, 255, 0.96); border-radius: 30px; padding: 34px; min-height: 520px; width: 100%; box-shadow: 0 26px 70px rgba(0,0,0,0.18); color: #0f172a; display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 18px; text-align: center; }
        .hero-logo-img { width: 70%; max-width: 420px; height: auto; }
        .hero-title { font-family: 'Sora', sans-serif; font-size: 2.1rem; font-weight: 700; line-height: 1.1; }
        .hero-subtitle { font-size: 1rem; color: #64748b; }
        .hero-tagline { font-weight: 700; color: #0f172a; background: #eef2ff; border-radius: 999px; padding: 8px 16px; display: inline-block; box-shadow: inset 0 0 0 1px rgba(59,130,246,0.2); }
        .hero-meta { font-size: 0.92rem; color: #1e3a8a; font-weight: 700; letter-spacing: 0.3px; text-transform: uppercase; }
        .feature-block { margin-top: 28px; background: linear-gradient(135deg, rgba(255,255,255,0.98) 0%, rgba(239,246,255,0.94) 45%, rgba(255,247,237,0.9) 100%); border-radius: 28px; padding: 26px 30px; border: 1px solid rgba(226,232,240,0.9); box-shadow: 0 26px 60px rgba(15,23,42,0.16); position: relative; overflow: hidden; color: #0f172a; }
        .feature-block::before { content: ""; position: absolute; inset: -40% -20% auto auto; width: 380px; height: 380px; background: radial-gradient(circle, rgba(59,130,246,0.18), transparent 60%); pointer-events: none; }
        .feature-title { font-family: 'Sora', sans-serif; font-size: 1.25rem; font-weight: 700; color: #e2e8f0; margin-bottom: 16px; text-shadow: 0 2px 10px rgba(15,23,42,0.35); }
        .feature-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 16px; position: relative; z-index: 1; }
        .feature-card { background: linear-gradient(135deg, rgba(34,197,94,0.22), rgba(16,185,129,0.16)) !important; border-radius: 20px; padding: 18px 18px; border: 1px solid rgba(34,197,94,0.45); box-shadow: 0 12px 26px rgba(5, 46, 22, 0.35) !important; transition: transform 0.2s ease, border-color 0.2s ease, box-shadow 0.2s ease; }
        .feature-card:hover { transform: translateY(-2px); border-color: rgba(34,197,94,0.7); box-shadow: 0 16px 30px rgba(5, 46, 22, 0.45) !important; }
        .feature-icon { font-size: 1.2rem; width: 44px; height: 44px; border-radius: 14px; display: inline-flex; align-items: center; justify-content: center; margin-bottom: 10px; background: #eff6ff; color: #1d4ed8; box-shadow: inset 0 0 0 1px rgba(37,99,235,0.15); }
        .feature-card:nth-child(2) .feature-icon { background: #ecfdf3; color: #16a34a; box-shadow: inset 0 0 0 1px rgba(22,163,74,0.18); }
        .feature-card:nth-child(3) .feature-icon { background: #fff7ed; color: #ea580c; box-shadow: inset 0 0 0 1px rgba(234,88,12,0.18); }
        .feature-card:nth-child(4) .feature-icon { background: #f5f3ff; color: #7c3aed; box-shadow: inset 0 0 0 1px rgba(124,58,237,0.18); }
        .feature-text { font-weight: 700; color: #f8fafc; font-size: 0.98rem; }
        .feature-sub { font-size: 0.84rem; color: #cbd5e1; margin-top: 4px; }
        .feature-cta { margin-top: 18px; display: flex; justify-content: flex-end; }
        .whatsapp-button { display: inline-flex; align-items: center; justify-content: center; gap: 10px; background: #22c55e; color: white !important; font-weight: 700; padding: 12px 16px; border-radius: 12px; text-decoration: none; transition: transform 0.2s; box-shadow: 0 4px 12px rgba(34, 197, 94, 0.3); }
        .whatsapp-button:hover { transform: translateY(-2px); opacity: 0.95; }
        div[data-testid="stVerticalBlock"]:has(.auth-card-anchor) { background: rgba(255, 255, 255, 0.98); border-radius: 26px; padding: 22px 26px 26px; width: 100%; min-height: 520px; box-shadow: 0 26px 70px rgba(0,0,0,0.18); box-sizing: border-box; }
        div[data-testid="stVerticalBlock"]:has(.auth-card-anchor) div[data-testid="stForm"] { background: transparent; border-radius: 0; padding: 0; border: none; width: 100%; height: auto; min-height: 0; max-height: none; overflow: visible; box-shadow: none; display: flex; flex-direction: column; justify-content: flex-start; }
        .login-header { font-family: 'Sora', sans-serif; font-size: 1.7rem; font-weight: 700; color: #0f172a; margin-bottom: 6px; }
        .login-sub { font-size: 0.95rem; color: #64748b; margin-bottom: 24px; }
        div[data-testid="stVerticalBlock"]:has(.auth-card-anchor) div[data-testid="stForm"] label { font-size: 0.85rem; font-weight: 600; color: #475569; }
        div[data-testid="stVerticalBlock"]:has(.auth-card-anchor) div[data-testid="stForm"] input, div[data-testid="stVerticalBlock"]:has(.auth-card-anchor) div[data-testid="stForm"] select, div[data-testid="stVerticalBlock"]:has(.auth-card-anchor) div[data-testid="stForm"] div[data-baseweb="select"] > div { background-color: #f8fafc !important; border: 1px solid #e2e8f0 !important; border-radius: 12px !important; color: #334155 !important; height: 48px; }
        div[data-testid="stVerticalBlock"]:has(.auth-card-anchor) div[data-testid="stForm"] input:focus { border-color: #3b82f6 !important; box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1) !important; }
        div[data-testid="stVerticalBlock"]:has(.auth-card-anchor) div[data-testid="stForm"] button { background: linear-gradient(90deg, #22c55e 0%, #16a34a 100%); color: white; border: none; border-radius: 12px; font-weight: 700; padding: 0.75rem 1rem; width: 100%; font-size: 1rem; margin-top: 10px; transition: 0.3s ease; }
        div[data-testid="stVerticalBlock"]:has(.auth-card-anchor) div[data-testid="stForm"] button:hover { transform: scale(1.02); box-shadow: 0 5px 15px rgba(34, 197, 94, 0.4); }
        div[data-testid="stPassword"] button { background: transparent !important; border: none !important; width: 28px !important; height: 28px !important; min-height: 28px !important; padding: 0 !important; box-shadow: none !important; color: #94a3b8 !important; }
        div[data-testid="stPassword"] button:hover { background: rgba(148, 163, 184, 0.12) !important; }
        div[data-testid="stPassword"] button svg { width: 14px !important; height: 14px !important; }
    </style>
    """, unsafe_allow_html=True)
else:
    st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Baloo+2:wght@600;700&family=Manrope:wght@400;600;700&family=Sora:wght@500;700&display=swap');
        .stApp { background: #eef5ff; font-family: 'Manrope', sans-serif; }
        :root { --sidebar-width: 352px; --sidebar-menu-btn-width: 320px; }
        section[data-testid="stAppViewContainer"] { background: #eef5ff; }
        .main-header { font-family: 'Sora', sans-serif; font-size: 1.8rem; font-weight: 700; color: #1e3a8a; margin-bottom: 20px; }
        section[data-testid="stSidebar"] { background-color: #f3f8ff; border-right: 1px solid #dbe7f6; box-shadow: 2px 0 10px rgba(15,23,42,0.04); min-width: var(--sidebar-width) !important; max-width: var(--sidebar-width) !important; }
        section[data-testid="stSidebar"] .stButton { width: var(--sidebar-menu-btn-width) !important; min-width: var(--sidebar-menu-btn-width) !important; max-width: var(--sidebar-menu-btn-width) !important; margin-right: auto; }
        section[data-testid="stSidebar"] .stButton > button { background: #f6f9ff; border: 1px solid #dbe7f6; color: #475569; text-align: left; font-weight: 700; padding: 0 1rem; width: var(--sidebar-menu-btn-width) !important; min-width: var(--sidebar-menu-btn-width) !important; max-width: var(--sidebar-menu-btn-width) !important; border-radius: 14px; transition: all 0.2s ease; margin-bottom: 8px; box-shadow: 0 6px 16px rgba(15, 23, 42, 0.06); height: 56px !important; min-height: 56px !important; max-height: 56px !important; display: flex; align-items: center; justify-content: flex-start; box-sizing: border-box; white-space: nowrap; overflow: visible; text-overflow: clip; }
        section[data-testid="stSidebar"] .stButton > button p { margin: 0 !important; line-height: 1 !important; white-space: nowrap !important; overflow: visible !important; text-overflow: clip !important; }
        section[data-testid="stSidebar"] .stButton > button:active { transform: none !important; }
        section[data-testid="stSidebar"] .stButton > button[data-testid="stBaseButton-secondary"] { height: 56px !important; }
        section[data-testid="stSidebar"] .stButton > button[data-testid="stBaseButton-primary"] { height: 56px !important; }
        .logout-btn .stButton > button { background: #fef2f2 !important; border-color: #fecaca !important; color: #991b1b !important; }
        .logout-btn .stButton > button:hover { background: #fee2e2 !important; border-color: #fca5a5 !important; color: #b91c1c !important; }
        .logout-btn .stButton > button:active { background: #fecaca !important; border-color: #f87171 !important; color: #7f1d1d !important; }
        div[data-testid="stButton"] > button:hover,
        div[data-testid="stFormSubmitButton"] > button:hover,
        div[data-testid="stDownloadButton"] > button:hover,
        section[data-testid="stSidebar"] .stButton > button:hover { color: #ffffff !important; background: linear-gradient(90deg, #1e3a8a 0%, #2563eb 100%) !important; border-color: #1e3a8a !important; transform: translateY(-1px); box-shadow: 0 10px 22px rgba(37, 99, 235, 0.25) !important; }
        section[data-testid="stSidebar"] .stButton > button[kind="primary"] { background: linear-gradient(90deg, #1e3a8a 0%, #2563eb 100%); color: #ffffff; border: none; box-shadow: 0 10px 24px rgba(37, 99, 235, 0.28); }
        .profile-card { background: linear-gradient(135deg, rgba(30,58,138,0.12), rgba(255,255,255,0.9)); border: 1px solid rgba(30,58,138,0.15); border-radius: 16px; padding: 12px 14px; margin: 10px 0 12px; box-shadow: 0 10px 22px rgba(15, 23, 42, 0.08); font-family: 'Baloo 2', cursive; color: #0f172a; }
        .profile-label { font-size: 0.68rem; text-transform: uppercase; letter-spacing: 0.12em; color: #64748b; margin-bottom: 2px; }
        .profile-value { font-size: 1.02rem; font-weight: 700; color: #1e3a8a; margin-bottom: 6px; }
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
st.session_state["students"] = load_list(STUDENTS_FILE)
st.session_state["teachers"] = load_list(TEACHERS_FILE)
st.session_state["classes"] = load_list(CLASSES_FILE)
st.session_state["receivables"] = load_list(RECEIVABLES_FILE)
st.session_state["payables"] = load_list(PAYABLES_FILE)
st.session_state["fee_templates"] = load_list(FEE_TEMPLATES_FILE)
st.session_state["email_log"] = load_list(EMAIL_LOG_FILE)
st.session_state["chatbot_log"] = load_list(CHATBOT_LOG_FILE)
st.session_state["agenda"] = load_list(AGENDA_FILE)
st.session_state["inventory"] = load_list(INVENTORY_FILE)
st.session_state["inventory_moves"] = load_list(INVENTORY_MOVES_FILE)
st.session_state["certificates"] = load_list(CERTIFICATES_FILE)
st.session_state["books"] = load_list(BOOKS_FILE)
st.session_state["material_orders"] = load_list(MATERIAL_ORDERS_FILE)
st.session_state["challenges"] = load_list(CHALLENGES_FILE)
st.session_state["challenge_completions"] = load_list(CHALLENGE_COMPLETIONS_FILE)

_ensure_challenge_store_ids()

if not st.session_state["books"]:
    st.session_state["books"] = [
        {"nivel": "Livro 1", "titulo": "Livro 1", "url": "", "file_path": ""},
        {"nivel": "Livro 2", "titulo": "Livro 2", "url": "", "file_path": ""},
        {"nivel": "Livro 3", "titulo": "Livro 3", "url": "", "file_path": ""},
        {"nivel": "Livro 4", "titulo": "Livro 4", "url": "", "file_path": ""},
    ]
    save_list(BOOKS_FILE, st.session_state["books"])

st.session_state["users"] = load_users()
st.session_state["users"] = ensure_admin_user(st.session_state["users"])
st.session_state["users"] = sync_users_from_profiles(st.session_state["users"])
save_users(st.session_state["users"])

# ==============================================================================
# TELA DE LOGIN
# ==============================================================================
if not st.session_state.get("logged_in", False):
    col_left, col_right = st.columns([1, 1], gap="large")
    with col_left:
        logo_path = get_logo_path()
        logo_html = ""
        if logo_path:
            encoded_logo = base64.b64encode(logo_path.read_bytes()).decode("utf-8")
            logo_html = f"<img src='data:image/png;base64,{encoded_logo}' class='hero-logo-img'>"
        st.markdown(
            f"""
<div class="hero-card">
  {logo_html}
  <div class="hero-title">Sistema Educacional<br>Ativo</div>
  <div class="hero-meta">Escola de líderes e inglês Mister Wiz</div>
  <div class="hero-subtitle hero-tagline">Gestão acadêmica, comunicação e conteúdo pedagógico.</div>
</div>
""",
            unsafe_allow_html=True,
        )

    with col_right:
        with st.container():
            st.markdown('<div class="auth-card-anchor"></div>', unsafe_allow_html=True)
            with st.form("login_form"):
                st.markdown(
                    """<div class="login-header">Conecte-se</div><div class="login-sub">Acesse a Plataforma Educacional</div>""",
                    unsafe_allow_html=True,
                )
                role = st.selectbox("Perfil", ["Aluno", "Professor", "Coordenador"])
                unidades = ["Matriz", "Unidade Centro", "Unidade Norte", "Unidade Sul", "Outra"]
                unidade_sel = st.selectbox("Unidade", unidades)
                if unidade_sel == "Outra":
                    unidade = st.text_input("Digite o nome da unidade")
                else:
                    unidade = unidade_sel
                usuario = st.text_input("Usuário", placeholder="Seu usuário de acesso")
                senha = st.text_input("Senha", type="password", placeholder="Sua senha")
                entrar = st.form_submit_button("Entrar no Sistema")

        if entrar:
            st.session_state["users"] = load_users()
            st.session_state["users"] = ensure_admin_user(st.session_state["users"])
            st.session_state["users"] = sync_users_from_profiles(st.session_state["users"])
            save_users(st.session_state["users"])
            user = find_user(usuario.strip())
            if not usuario.strip() or not senha.strip():
                st.error("Informe usuario e senha.")
            elif not user or str(user.get("senha", "")).strip() != senha.strip():
                st.error("Usuario ou senha invalidos.")
            else:
                perfil_conta = user.get("perfil", "")
                if role not in allowed_portals(perfil_conta):
                    st.error(f"Este usuario nao tem permissao de {role}.")
                else:
                    display_name = user.get("pessoa") or usuario.strip()
                    login_user(role, display_name, str(unidade).strip(), perfil_conta)

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown('<div class="feature-title">Recursos do Sistema</div>', unsafe_allow_html=True)
    feature_cards = [
        ("Comunicacao Direta", "Mensagens rapidas para alunos e turmas."),
        ("Professor Wiz IA", "Estudo assistido por IA com orientacao em tempo real."),
        ("Aulas Gravadas", "Conteudo organizado e acessivel a qualquer hora."),
        ("Sistema Automatizado", "Processos de agenda, financeiro e comunicacao integrados."),
        ("Agenda + Google", "Aulas com link para incluir direto no Google Agenda."),
        ("Financeiro", "Controle de matriculas, parcelas e recebimentos."),
    ]
    for i in range(0, len(feature_cards), 3):
        cols = st.columns(3, gap="large")
        for col, card in zip(cols, feature_cards[i:i+3]):
            title, sub = card
            with col:
                st.markdown(
                    f"""
<div class="feature-card">
  <div class="feature-text">{title}</div>
  <div class="feature-sub">{sub}</div>
</div>
""",
                    unsafe_allow_html=True,
                )
    st.markdown(
        f"""
<div class="feature-cta">
  <a href="https://wa.me/{WHATSAPP_NUMBER}" target="_blank" class="whatsapp-button">📱 Falar com Suporte no WhatsApp</a>
</div>
""",
        unsafe_allow_html=True,
    )

# ==============================================================================
# ALUNO
# ==============================================================================
elif st.session_state["role"] == "Aluno":
    with st.sidebar:
        logo_path = get_logo_path()
        render_sidebar_logo(logo_path)
        st.markdown(f"### Olá, {st.session_state['user_name']}")
        if st.session_state["unit"]: st.caption(f"Unidade: {st.session_state['unit']}")
        st.markdown(
            f"""
<div class="profile-card">
  <div class="profile-label">Tipo</div>
  <div class="profile-value">{st.session_state.get('role', '')}</div>
  <div class="profile-label">Perfil</div>
  <div class="profile-value">{st.session_state.get('account_profile') or st.session_state.get('role', '')}</div>
</div>
""",
            unsafe_allow_html=True,
        )
        st.info("Nível: Intermediário B1")
        st.markdown("---")
        menu_aluno_label = sidebar_menu("Navegacao", ["Painel", "Agenda", "Minhas Aulas", "Boletim e Frequencia", "Mensagens", "Desafios", "Aulas Gravadas", "Financeiro", "Materiais de Estudo", "Professor Wiz"], "menu_aluno")
        st.markdown("---")
        st.markdown('<div class="logout-btn">', unsafe_allow_html=True)
        if st.button("Sair"): logout_user()
        st.markdown('</div>', unsafe_allow_html=True)

    menu_aluno_map = {"Painel": "Dashboard", "Agenda": "Agenda", "Minhas Aulas": "Minhas Aulas", "Boletim e Frequencia": "Boletim & Frequencia", "Mensagens": "Mensagens", "Desafios": "Desafios", "Aulas Gravadas": "Aulas Gravadas", "Financeiro": "Financeiro", "Materiais de Estudo": "Materiais de Estudo", "Professor Wiz": "Professor Wiz"}
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

    elif menu_aluno == "Agenda":
        st.markdown('<div class="main-header">Agenda de Aulas</div>', unsafe_allow_html=True)
        aluno_nome = st.session_state["user_name"]
        turma_aluno = next((s.get("turma") for s in st.session_state["students"] if s.get("nome") == aluno_nome), None)
        if not turma_aluno:
            st.info("Nenhuma turma vinculada ao aluno.")
        else:
            agenda = [a for a in st.session_state["agenda"] if a.get("turma") == turma_aluno]
            render_agenda(sort_agenda(agenda), "Nenhuma aula agendada para sua turma.")

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
        aluno_nome = st.session_state.get("user_name", "")
        turma_aluno = next((s.get("turma") for s in st.session_state["students"] if s.get("nome") == aluno_nome), "")
        mensagens_aluno = [
            m for m in st.session_state["messages"]
            if not m.get("turma") or m.get("turma") == "Todas" or m.get("turma") == turma_aluno
        ]
        if not mensagens_aluno: st.info("Sem mensagens.")
        for msg in reversed(mensagens_aluno):
            with st.container():
                st.markdown(f"""<div style="background:white; padding:16px; border-radius:12px; border:1px solid #e2e8f0; margin-bottom:10px;"><div style="font-weight:700; color:#1e3a8a;">{msg.get('titulo','Mensagem')}</div><div style="font-size:0.85rem; color:#64748b; margin-bottom:8px;">{msg.get('data','')} | {msg.get('autor','')} | Turma: {msg.get('turma','Todas')}</div><div>{msg.get('mensagem','')}</div></div>""", unsafe_allow_html=True)

    elif menu_aluno == "Desafios":
        st.markdown('<div class="main-header">Desafios Semanais</div>', unsafe_allow_html=True)
        aluno_nome = st.session_state.get("user_name", "")
        aluno_obj = next((s for s in st.session_state.get("students", []) if s.get("nome") == aluno_nome), {})
        nivel = student_book_level(aluno_obj) or "Livro 1"
        semana = current_week_key()
        st.caption(f"Nivel: {nivel} | Semana: {semana}")

        total_pts = student_points(aluno_nome)
        st.markdown(f"**Pontuacao total:** {total_pts} ponto(s)")

        ch = get_weekly_challenge(nivel, semana)
        if not ch:
            st.info("Ainda nao foi publicado um desafio para sua semana/nivel.")
        else:
            st.markdown(f"### {ch.get('titulo','Desafio')}")
            st.write(ch.get("descricao", ""))
            if str(ch.get("dica", "")).strip():
                st.info(f"Dica: {str(ch.get('dica','')).strip()}")
            st.caption(f"Pontos: {ch.get('pontos', 0)} | Publicado por: {ch.get('autor','')} | Prazo: {ch.get('due_date','') or 'sem prazo'}")
            cid = ch.get("id", "")
            sub = get_challenge_submission(cid, aluno_nome) or {}
            done = has_completed_challenge(cid, aluno_nome)

            if sub:
                st.markdown("#### Sua avaliacao")
                cols = st.columns([1, 1, 1])
                cols[0].metric("Status", str(sub.get("status", "") or "Concluido"))
                if "score" in sub:
                    try:
                        cols[1].metric("Nota", int(sub.get("score") or 0))
                    except Exception:
                        cols[1].metric("Nota", str(sub.get("score", "")))
                cols[2].metric("Pontos", int(sub.get("pontos") or 0))
                if str(sub.get("feedback", "")).strip():
                    st.write(sub.get("feedback", ""))
                if str(sub.get("resposta", "")).strip():
                    with st.expander("Ver minha resposta"):
                        st.write(sub.get("resposta", ""))

            if done:
                st.success("Voce ja concluiu este desafio (aprovado).")
            else:
                api_key = get_groq_api_key()
                if not api_key:
                    st.error("Para responder e ser avaliado automaticamente, configure GROQ_API_KEY em secrets/variavel de ambiente.")
                else:
                    default_answer = str(sub.get("resposta", "") or "")
                    resp_key = f"challenge_answer_{cid}_{aluno_nome}".replace(" ", "_")
                    resposta = st.text_area("Sua resposta (escreva aqui)", value=default_answer, height=180, key=resp_key)
                    if st.button("Enviar resposta para avaliacao", type="primary", key=f"send_ch_{cid}"):
                        try:
                            ev = evaluate_challenge_answer_ai(ch, nivel, resposta)
                        except Exception as exc:
                            st.error(f"Falha ao avaliar com IA: {exc}")
                        else:
                            pontos_awarded = int(ch.get("pontos") or 0) if ev.get("passed") else 0
                            status = "Aprovado" if ev.get("passed") else "Reprovado"
                            ok, msg = complete_challenge(
                                ch,
                                aluno_nome,
                                resposta=resposta,
                                score=ev.get("score"),
                                feedback=ev.get("feedback"),
                                status=status,
                                pontos_awarded=pontos_awarded,
                            )
                            if ok:
                                if pontos_awarded > 0:
                                    st.success("Resposta enviada e aprovada! Pontos adicionados.")
                                else:
                                    st.warning("Resposta enviada, mas ainda nao atingiu a nota minima. Voce pode melhorar e reenviar.")
                                st.rerun()
                            else:
                                st.error(msg)

        st.markdown("### Historico de concluidos")
        concluidos = [c for c in st.session_state.get("challenge_completions", []) if str(c.get("aluno", "")).strip() == aluno_nome]
        if not concluidos:
            st.info("Nenhum desafio concluido ainda.")
        else:
            df = pd.DataFrame(concluidos)
            col_order = [c for c in ["done_at", "semana", "nivel", "status", "score", "pontos", "challenge_id"] if c in df.columns]
            if col_order:
                df = df[col_order]
            st.dataframe(df, use_container_width=True)

    elif menu_aluno == "Aulas Gravadas":
        st.markdown('<div class="main-header">Aulas Gravadas</div>', unsafe_allow_html=True)
        if not st.session_state["videos"]: st.info("Sem vídeos.")
        for v in reversed(st.session_state["videos"]):
            with st.expander(f"🎥 {v['titulo']} ({v['data']})"):
                if v['url']: st.video(v['url'])
            
    elif menu_aluno == "Materiais de Estudo":
        st.markdown('<div class="main-header">Materiais</div>', unsafe_allow_html=True)
        aluno_obj = next((s for s in st.session_state["students"] if s.get("nome") == st.session_state["user_name"]), {})
        livro_aluno = aluno_obj.get("livro", "")
        if not livro_aluno:
            turma_nome = aluno_obj.get("turma", "")
            turma_obj = next((c for c in st.session_state["classes"] if c.get("nome") == turma_nome), {})
            livro_aluno = turma_obj.get("livro", "")
        livros = st.session_state.get("books", [])
        livros_filtrados = [b for b in livros if b.get("nivel") == livro_aluno] if livro_aluno else []
        render_books_section(livros_filtrados, "Livro do Aluno", key_prefix="aluno_livro")
        if not st.session_state["materials"]: st.info("Sem materiais.")
        for m in reversed(st.session_state["materials"]):
            with st.container():
                st.markdown(f"**{m['titulo']}**")
                st.write(m['descricao'])
                if m['link']: st.markdown(f"[📥 Baixar Arquivo]({m['link']})")
                st.markdown("---")

    elif menu_aluno == "Financeiro":
        run_student_finance_assistant()
    elif menu_aluno == "Professor Wiz":
        run_active_chatbot()

# =============================================================================
# PROFESSOR
# =============================================================================
elif st.session_state["role"] == "Professor":
    with st.sidebar:
        logo_path = get_logo_path()
        render_sidebar_logo(logo_path)
        st.markdown(f"### {st.session_state['user_name']}")
        st.markdown(
            f"""
<div class="profile-card">
  <div class="profile-label">Tipo</div>
  <div class="profile-value">{st.session_state.get('role', '')}</div>
  <div class="profile-label">Perfil</div>
  <div class="profile-value">{st.session_state.get('account_profile') or st.session_state.get('role', '')}</div>
</div>
""",
            unsafe_allow_html=True,
        )
        st.markdown("---")
        menu_prof_label = sidebar_menu("Gestao", ["Minhas Turmas", "Agenda", "Mensagens", "Livros", "Professor Wiz"], "menu_prof")
        st.markdown("---")
        st.markdown('<div class="logout-btn">', unsafe_allow_html=True)
        if st.button("Sair"): logout_user()
        st.markdown('</div>', unsafe_allow_html=True)

    menu_prof_map = {"Minhas Turmas": "Minhas Turmas", "Agenda": "Agenda", "Mensagens": "Mensagens", "Livros": "Livros", "Professor Wiz": "Assistente IA"}
    menu_prof = menu_prof_map.get(menu_prof_label, "Minhas Turmas")

    if menu_prof == "Minhas Turmas":
        st.markdown('<div class="main-header">Painel do Professor</div>', unsafe_allow_html=True)
        prof_nome = st.session_state["user_name"].strip().lower()
        minhas_turmas = [
            c for c in st.session_state["classes"]
            if str(c.get("professor", "")).strip().lower() == prof_nome
        ]
        if not minhas_turmas:
            st.info("Nenhuma turma atribuída a você.")
        else:
            turma_options = [t["nome"] for t in minhas_turmas]
            turma_selecionada = st.selectbox("Selecione a Turma", turma_options)
            turma_obj = next(t for t in minhas_turmas if t["nome"] == turma_selecionada)

            st.markdown("### Detalhes da Turma")
            st.write(f"**Turma:** {turma_obj.get('nome', '')}")
            st.write(f"**Professor:** {turma_obj.get('professor', '')}")
            st.write(f"**Dias e Horários:** {turma_obj.get('dias', 'Horário a definir')}")
            st.write(f"**Link da Aula Ao Vivo:** {turma_obj.get('link_zoom', 'Não informado')}")

            st.markdown("### Aula ao Vivo")
            with st.form("prof_update_link"):
                link_live = st.text_input("Link da aula ao vivo", value=turma_obj.get("link_zoom", ""))
                if st.form_submit_button("Salvar link"):
                    turma_obj["link_zoom"] = link_live.strip()
                    save_list(CLASSES_FILE, st.session_state["classes"])
                    st.success("Link atualizado!")
                    st.rerun()

            st.markdown("### Material de Estudo")
            with st.form("prof_add_material"):
                titulo = st.text_input("Título do material")
                descricao = st.text_area("Descrição")
                link_mat = st.text_input("Link do material (Drive, PDF, etc.)")
                turma_material = st.selectbox(
                    "Turma",
                    turma_options,
                    index=turma_options.index(turma_selecionada) if turma_selecionada in turma_options else 0,
                )
                if st.form_submit_button("Publicar material"):
                    if not titulo.strip():
                        st.error("Informe o título do material.")
                    else:
                        st.session_state["materials"].append(
                            {
                                "titulo": titulo.strip(),
                                "descricao": descricao.strip(),
                                "link": link_mat.strip(),
                                "turma": turma_material,
                                "autor": st.session_state.get("user_name", ""),
                                "data": datetime.date.today().strftime("%d/%m/%Y"),
                            }
                        )
                        save_list(MATERIALS_FILE, st.session_state["materials"])
                        st.success("Material publicado!")
                        st.rerun()

            alunos_turma = [
                s for s in st.session_state["students"]
                if s.get("turma") == turma_selecionada
            ]
            st.markdown("### Alunos da Turma")
            if not alunos_turma:
                st.info("Nenhum aluno matriculado nesta turma.")
            else:
                df_alunos = pd.DataFrame(alunos_turma)
                col_order = [c for c in ["nome", "email", "celular", "data_nascimento", "idade"] if c in df_alunos.columns]
                if col_order:
                    df_alunos = df_alunos[col_order]
                st.dataframe(df_alunos, use_container_width=True)
    elif menu_prof == "Agenda":
        st.markdown('<div class="main-header">Agenda de Aulas</div>', unsafe_allow_html=True)
        prof_nome = st.session_state["user_name"].strip().lower()
        turmas_prof = [
            c.get("nome") for c in st.session_state["classes"]
            if str(c.get("professor", "")).strip().lower() == prof_nome
        ]
        if not turmas_prof:
            st.info("Nenhuma turma atribuída a você.")
        else:
            agenda = [a for a in st.session_state["agenda"] if a.get("turma") in set(turmas_prof)]
            render_agenda(sort_agenda(agenda), "Nenhuma aula agendada para suas turmas.")
    elif menu_prof == "Mensagens":
        st.markdown('<div class="main-header">Mensagens da Turma</div>', unsafe_allow_html=True)
        prof_nome = st.session_state["user_name"].strip().lower()
        turmas_prof = [
            c.get("nome") for c in st.session_state["classes"]
            if str(c.get("professor", "")).strip().lower() == prof_nome
        ]
        if not turmas_prof:
            st.info("Nenhuma turma atribuída a você.")
        else:
            with st.form("prof_publish_message", clear_on_submit=True):
                turma_msg = st.selectbox("Turma", turmas_prof)
                titulo_msg = st.text_input("Titulo da mensagem")
                corpo_msg = st.text_area("Mensagem")
                if st.form_submit_button("Publicar mensagem"):
                    if not titulo_msg.strip() or not corpo_msg.strip():
                        st.error("Preencha titulo e mensagem.")
                    else:
                        stats = post_message_and_notify(
                            autor=st.session_state.get("user_name", "Professor"),
                            titulo=titulo_msg,
                            mensagem=corpo_msg,
                            turma=turma_msg,
                            origem="Mensagens Professor",
                        )
                        st.success(f"Mensagem publicada. E-mails processados: {stats['enviados']}/{stats['total']}.")
                        st.rerun()
            st.markdown("### Historico")
            historico = [
                m for m in reversed(st.session_state["messages"])
                if m.get("turma") in turmas_prof or not m.get("turma") or m.get("turma") == "Todas"
            ]
            if not historico:
                st.info("Sem mensagens.")
            for msg in historico:
                st.markdown(
                    f"""<div style="background:white; padding:16px; border-radius:12px; border:1px solid #e2e8f0; margin-bottom:10px;">
<div style="font-weight:700; color:#1e3a8a;">{msg.get('titulo','Mensagem')}</div>
<div style="font-size:0.85rem; color:#64748b; margin-bottom:8px;">{msg.get('data','')} | {msg.get('autor','')} | Turma: {msg.get('turma','Todas')}</div>
<div>{msg.get('mensagem','')}</div></div>""",
                    unsafe_allow_html=True,
                )
    elif menu_prof == "Livros":
        st.markdown('<div class="main-header">Livros Didáticos</div>', unsafe_allow_html=True)
        render_books_section(st.session_state.get("books", []), key_prefix="prof_livros")
    elif menu_prof == "Assistente IA":
        run_active_chatbot()


# ==============================================================================
# COORDENADOR
# ==============================================================================
elif st.session_state["role"] == "Coordenador":
    with st.sidebar:
        logo_path = get_logo_path()
        render_sidebar_logo(logo_path)
        st.markdown(f"### {st.session_state['user_name']}")
        st.markdown(
            f"""
<div class="profile-card">
  <div class="profile-label">Tipo</div>
  <div class="profile-value">{st.session_state.get('role', '')}</div>
  <div class="profile-label">Perfil</div>
  <div class="profile-value">{st.session_state.get('account_profile') or st.session_state.get('role', '')}</div>
</div>
""",
            unsafe_allow_html=True,
        )
        st.markdown("---")
        menu_coord_label = sidebar_menu(
            "Administração",
            [
                "Dashboard",
                "Agenda",
                "Links Ao Vivo",
                "Alunos",
                "Professores",
                "Usuários",
                "Turmas",
                "Financeiro",
                "Estoque",
                "Certificados",
                "Livros",
                "Aprovação Notas",
                "Conteúdos",
                "Desafios",
                "Backup",
                "Professor Wiz",
            ],
            "menu_coord",
        )
        st.markdown("---")
        st.markdown('<div class="logout-btn">', unsafe_allow_html=True)
        if st.button("Sair"): logout_user()
        st.markdown('</div>', unsafe_allow_html=True)

    menu_coord_map = {
        "Dashboard": "Dashboard",
        "Agenda": "Agenda",
        "Links Ao Vivo": "Links",
        "Alunos": "Alunos",
        "Professores": "Professores",
        "Usuários": "Usuarios",
        "Turmas": "Turmas",
        "Financeiro": "Financeiro",
        "Estoque": "Estoque",
        "Certificados": "Certificados",
        "Livros": "Livros",
        "Aprovação Notas": "Notas",
        "Conteúdos": "Conteudos",
        "Desafios": "Desafios",
        "Backup": "Backup",
        "Professor Wiz": "Chatbot IA",
    }
    menu_coord = menu_coord_map.get(menu_coord_label, "Dashboard")

    if menu_coord == "Dashboard":
        st.markdown('<div class="main-header">Painel do Coordenador</div>', unsafe_allow_html=True)
        c1, c2, c3 = st.columns(3)
        with c1: st.markdown(f"""<div class=\"dash-card\"><div><div class=\"card-title\">Total de Alunos</div><div class=\"card-value\">{len(st.session_state['students'])}</div></div><div class=\"card-sub\"><span class=\"trend-up\">Ativos</span></div></div>""", unsafe_allow_html=True)
        with c2: st.markdown(f"""<div class=\"dash-card\"><div><div class=\"card-title\">Professores</div><div class=\"card-value\">{len(st.session_state['teachers'])}</div></div></div>""", unsafe_allow_html=True)
        with c3: st.markdown(f"""<div class=\"dash-card\"><div><div class=\"card-title\">Turmas</div><div class=\"card-value\">{len(st.session_state['classes'])}</div></div></div>""", unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)
        total_rec = sum(parse_money(i["valor"]) for i in st.session_state["receivables"])
        total_pag = sum(parse_money(i["valor"]) for i in st.session_state["payables"])
        saldo = total_rec - total_pag
        c4, c5, c6 = st.columns(3)
        with c4: st.markdown(f"""<div class=\"dash-card\"><div><div class=\"card-title\">A Receber</div><div class=\"card-value\" style=\"color:#2563eb;\">{format_money(total_rec)}</div></div></div>""", unsafe_allow_html=True)
        with c5: st.markdown(f"""<div class=\"dash-card\"><div><div class=\"card-title\">A Pagar</div><div class=\"card-value\" style=\"color:#dc2626;\">{format_money(total_pag)}</div></div></div>""", unsafe_allow_html=True)
        with c6:
             color = "#16a34a" if saldo >= 0 else "#dc2626"
             st.markdown(f"""<div class=\"dash-card\"><div><div class=\"card-title\">Saldo Atual</div><div class=\"card-value\" style=\"color:{color};\">{format_money(saldo)}</div></div></div>""", unsafe_allow_html=True)

    elif menu_coord == "Agenda":
        st.markdown('<div class="main-header">Agenda de Aulas</div>', unsafe_allow_html=True)
        tab1, tab2 = st.tabs(["Aulas Agendadas", "Nova Aula"])
        with tab1:
            agenda = sort_agenda(st.session_state["agenda"])
            render_agenda(agenda, "Nenhuma aula agendada.")
        with tab2:
            turmas = class_names()
            if not turmas:
                st.info("Cadastre turmas antes de agendar aulas.")
            else:
                with st.form("add_agenda"):
                    turma_sel = st.selectbox("Turma", turmas)
                    turma_obj = next((c for c in st.session_state["classes"] if c.get("nome") == turma_sel), {})
                    prof_default = turma_obj.get("professor", "")
                    link_default = turma_obj.get("link_zoom", "")
                    titulo = st.text_input("Título", value="Aula ao vivo")
                    descricao = st.text_area("Descrição")
                    data_aula = st.date_input("Data", value=datetime.date.today(), format="DD/MM/YYYY")
                    hora_aula = st.time_input("Horário", value=datetime.time(19, 0))
                    repetir = st.checkbox("Repetir semanalmente", value=False)
                    semanas = st.number_input("Número de semanas", min_value=1, max_value=52, value=4)
                    professor = st.text_input("Professor", value=prof_default)
                    link_aula = st.text_input("Link da aula", value=link_default)
                    enviar_email_convite = st.checkbox("Enviar email automatico para alunos da turma", value=True)
                    if st.form_submit_button("Agendar aula"):
                        total = int(semanas) if repetir else 1
                        novos_itens = []
                        for i in range(total):
                            data_item = data_aula + datetime.timedelta(weeks=i) if data_aula else None
                            agenda_item = {
                                "turma": turma_sel,
                                "professor": professor.strip(),
                                "titulo": titulo.strip() or "Aula ao vivo",
                                "descricao": descricao.strip(),
                                "data": data_item.strftime("%d/%m/%Y") if data_item else "",
                                "hora": hora_aula.strftime("%H:%M") if hora_aula else "",
                                "link": link_aula.strip(),
                                "recorrencia": "Semanal" if repetir else "",
                            }
                            agenda_item["google_calendar_link"] = build_google_calendar_event_link(agenda_item)
                            st.session_state["agenda"].append(agenda_item)
                            novos_itens.append(agenda_item)
                        save_list(AGENDA_FILE, st.session_state["agenda"])
                        if enviar_email_convite and novos_itens:
                            resumo = []
                            for item in novos_itens:
                                linha = f"- {item.get('data','')} {item.get('hora','')} | {item.get('titulo','Aula')}"
                                gcal = item.get("google_calendar_link", "")
                                if gcal:
                                    linha += f"\n  Google Agenda: {gcal}"
                                if item.get("link"):
                                    linha += f"\n  Link da aula: {item.get('link')}"
                                resumo.append(linha)
                            assunto = f"[Active] Aula agendada - Turma {turma_sel}"
                            corpo = (
                                f"Novas aulas foram agendadas para a turma {turma_sel}.\n\n"
                                + "\n".join(resumo)
                            )
                            stats = email_students_by_turma(turma_sel, assunto, corpo, "Agenda")
                            st.info(f"E-mails processados: {stats['enviados']}/{stats['total']}.")
                        st.success("Aula(s) agendada(s)!")
                        st.rerun()

    elif menu_coord == "Links":
        st.markdown('<div class="main-header">Gerenciar Links Ao Vivo</div>', unsafe_allow_html=True)
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
                        save_list(CLASSES_FILE, st.session_state["classes"])
                        st.success(f"Link atualizado com sucesso para a turma {turma_sel}!")

    elif menu_coord == "Estoque":
        st.markdown('<div class="main-header">Controle de Estoque</div>', unsafe_allow_html=True)
        tab1, tab2, tab3, tab4, tab5 = st.tabs(["Itens", "Novo Item", "Movimentar", "Movimentações", "Pedidos"])

        with tab1:
            c1, c2, c3, c4 = st.columns(4)
            with c1: filtro_desc = st.text_input("Descrição")
            with c2: filtro_cod = st.text_input("Código do produto")
            with c3: filtro_final = st.selectbox("Finalidade", ["Todos", "Venda", "Uso Interno", "Material Didático"])
            with c4: filtro_status = st.selectbox("Situação", ["Todos", "Ativo", "Inativo"])

            itens = st.session_state["inventory"]
            if filtro_desc:
                itens = [i for i in itens if filtro_desc.lower() in str(i.get("descricao", "")).lower()]
            if filtro_cod:
                itens = [i for i in itens if filtro_cod.lower() in str(i.get("codigo", "")).lower()]
            if filtro_final != "Todos":
                itens = [i for i in itens if i.get("finalidade") == filtro_final]
            if filtro_status != "Todos":
                ativo = filtro_status == "Ativo"
                itens = [i for i in itens if bool(i.get("ativo", True)) == ativo]

            itens_criticos = [i for i in itens if parse_int(i.get("saldo", 0)) < parse_int(i.get("minimo", 0))]
            if itens_criticos:
                st.warning(f"Itens abaixo do minimo: {len(itens_criticos)}")

            if itens:
                df_itens = pd.DataFrame(itens)
                col_order = [
                    "codigo",
                    "descricao",
                    "finalidade",
                    "unidade",
                    "saldo",
                    "custo",
                    "preco",
                    "minimo",
                    "maximo",
                    "empresa",
                    "ativo",
                ]
                if "parcelas" in df_itens.columns:
                    col_order = [
                        "codigo",
                        "descricao",
                        "finalidade",
                        "unidade",
                        "saldo",
                        "custo",
                        "preco",
                        "parcelas",
                        "minimo",
                        "maximo",
                        "empresa",
                        "ativo",
                    ]
                df_itens = df_itens[[c for c in col_order if c in df_itens.columns]]
                st.dataframe(df_itens, use_container_width=True)
            else:
                st.info("Nenhum item encontrado.")

            if st.session_state["inventory"]:
                st.markdown("### Editar / Excluir Item")
                codigos = [str(i.get("codigo", "")).strip() for i in st.session_state["inventory"] if i.get("codigo")]
                item_sel = st.selectbox("Selecione o item", codigos)
                item_obj = next((i for i in st.session_state["inventory"] if str(i.get("codigo", "")).strip() == item_sel), None)
                if item_obj:
                    with st.form("edit_item"):
                        codigo = st.text_input("Código", value=item_obj.get("codigo", ""))
                        descricao = st.text_input("Descrição", value=item_obj.get("descricao", ""))
                        finalidade = st.selectbox("Finalidade", ["Venda", "Uso Interno", "Material Didático"], index=["Venda", "Uso Interno", "Material Didático"].index(item_obj.get("finalidade", "Venda")) if item_obj.get("finalidade") in ["Venda", "Uso Interno", "Material Didático"] else 0)
                        unidade = st.selectbox("Unidade", ["Unidade", "Kit", "Pacote", "Caixa"], index=["Unidade", "Kit", "Pacote", "Caixa"].index(item_obj.get("unidade", "Unidade")) if item_obj.get("unidade") in ["Unidade", "Kit", "Pacote", "Caixa"] else 0)
                        saldo = st.number_input("Saldo", min_value=0, step=1, value=parse_int(item_obj.get("saldo", 0)))
                        custo = st.text_input("Custo", value=str(item_obj.get("custo", "")))
                        preco = st.text_input("Preço (parcela)", value=str(item_obj.get("preco", "")))
                        parcelas = st.number_input("Parcelas (qtd)", min_value=1, max_value=6, step=1, value=min(6, max(1, parse_int(item_obj.get("parcelas", 1)))))
                        minimo = st.number_input("Mínimo", min_value=0, step=1, value=parse_int(item_obj.get("minimo", 0)))
                        maximo = st.number_input("Máximo", min_value=0, step=1, value=parse_int(item_obj.get("maximo", 0)))
                        empresa = st.text_input("Empresa", value=item_obj.get("empresa", ""))
                        ativo = st.checkbox("Ativo", value=bool(item_obj.get("ativo", True)))
                        c_save, c_del = st.columns(2)
                        with c_save:
                            if st.form_submit_button("Salvar alterações"):
                                codigo_norm = codigo.strip()
                                if not codigo_norm or not descricao.strip():
                                    st.error("Informe código e descrição.")
                                else:
                                    if codigo_norm != str(item_obj.get("codigo", "")).strip():
                                        if any(str(i.get("codigo", "")).strip() == codigo_norm for i in st.session_state["inventory"]):
                                            st.error("Código já existe.")
                                            st.stop()
                                    item_obj.update(
                                        {
                                            "codigo": codigo_norm,
                                            "descricao": descricao.strip(),
                                            "finalidade": finalidade,
                                            "unidade": unidade,
                                            "saldo": int(saldo),
                                            "custo": parse_money(custo),
                                            "preco": parse_money(preco),
                                            "parcelas": int(parcelas),
                                            "minimo": int(minimo),
                                            "maximo": int(maximo),
                                            "empresa": empresa.strip(),
                                            "ativo": bool(ativo),
                                        }
                                    )
                                    save_list(INVENTORY_FILE, st.session_state["inventory"])
                                    st.success("Item atualizado com sucesso!")
                                    st.rerun()
                        with c_del:
                            if st.form_submit_button("Excluir item", type="primary"):
                                st.session_state["inventory"].remove(item_obj)
                                save_list(INVENTORY_FILE, st.session_state["inventory"])
                                st.success("Item excluído.")
                                st.rerun()

        with tab2:
            with st.form("add_item", clear_on_submit=True):
                codigo = st.text_input("Código do produto *")
                descricao = st.text_input("Descrição *")
                finalidade = st.selectbox("Finalidade", ["Venda", "Uso Interno", "Material Didático"])
                unidade = st.selectbox("Unidade", ["Unidade", "Kit", "Pacote", "Caixa"])
                saldo = st.number_input("Saldo inicial", min_value=0, step=1, value=0)
                custo = st.text_input("Custo")
                preco = st.text_input("Preço (parcela)")
                parcelas = st.number_input("Parcelas (qtd)", min_value=1, max_value=6, step=1, value=1)
                minimo = st.number_input("Mínimo", min_value=0, step=1, value=0)
                maximo = st.number_input("Máximo", min_value=0, step=1, value=0)
                empresa = st.text_input("Empresa")
                ativo = st.checkbox("Ativo", value=True)
                if st.form_submit_button("Incluir item"):
                    codigo_norm = codigo.strip()
                    if not codigo_norm or not descricao.strip():
                        st.error("Informe código e descrição.")
                    elif any(str(i.get("codigo", "")).strip() == codigo_norm for i in st.session_state["inventory"]):
                        st.error("Código já existe.")
                    else:
                        st.session_state["inventory"].append(
                            {
                                "codigo": codigo_norm,
                                "descricao": descricao.strip(),
                                "finalidade": finalidade,
                                "unidade": unidade,
                                "saldo": int(saldo),
                                "custo": parse_money(custo),
                                "preco": parse_money(preco),
                                "parcelas": int(parcelas),
                                "minimo": int(minimo),
                                "maximo": int(maximo),
                                "empresa": empresa.strip(),
                                "ativo": bool(ativo),
                            }
                        )
                        save_list(INVENTORY_FILE, st.session_state["inventory"])
                        st.success("Cadastro realizado com sucesso!")

        with tab3:
            if not st.session_state["inventory"]:
                st.info("Nenhum item cadastrado.")
            else:
                codigos = [str(i.get("codigo", "")).strip() for i in st.session_state["inventory"] if i.get("codigo")]
                item_sel = st.selectbox("Item", codigos, key="mov_item")
                item_obj = next((i for i in st.session_state["inventory"] if str(i.get("codigo", "")).strip() == item_sel), None)
                if item_obj:
                    with st.form("move_item"):
                        tipo = st.selectbox("Tipo de movimentação", ["Entrada", "Saída"])
                        quantidade = st.number_input("Quantidade", min_value=1, step=1, value=1)
                        motivo = st.text_input("Motivo/Observação")
                        if st.form_submit_button("Registrar movimentação"):
                            saldo_atual = parse_int(item_obj.get("saldo", 0))
                            if tipo == "Saída" and quantidade > saldo_atual:
                                st.error("Quantidade maior que o saldo disponível.")
                            else:
                                novo_saldo = saldo_atual + quantidade if tipo == "Entrada" else saldo_atual - quantidade
                                item_obj["saldo"] = int(novo_saldo)
                                mov_desc = f"{tipo} {quantidade}" + (f" - {motivo}" if motivo else "")
                                item_obj["ultima_mov"] = mov_desc
                                st.session_state["inventory_moves"].append(
                                    {
                                        "data": datetime.datetime.now().strftime("%d/%m/%Y %H:%M"),
                                        "codigo": str(item_obj.get("codigo", "")),
                                        "descricao": item_obj.get("descricao", ""),
                                        "tipo": tipo,
                                        "quantidade": int(quantidade),
                                        "motivo": motivo.strip(),
                                        "saldo_resultante": int(novo_saldo),
                                        "usuario": st.session_state.get("user_name", ""),
                                    }
                                )
                                save_list(INVENTORY_MOVES_FILE, st.session_state["inventory_moves"])
                                save_list(INVENTORY_FILE, st.session_state["inventory"])
                                st.success("Movimentação registrada!")
                                st.rerun()

        with tab4:
            moves = st.session_state["inventory_moves"]
            if not moves:
                st.info("Nenhuma movimentação registrada.")
            else:
                codigos = sorted({str(m.get("codigo", "")).strip() for m in moves if m.get("codigo")})
                filtro_item = st.selectbox("Filtrar por item", ["Todos"] + codigos)
                dados = moves
                if filtro_item != "Todos":
                    dados = [m for m in moves if str(m.get("codigo", "")).strip() == filtro_item]
                dados = list(reversed(dados))[:200]
                st.dataframe(pd.DataFrame(dados), use_container_width=True)

        with tab5:
            st.markdown("### Novo Pedido de Material")
            with st.form("add_material_order", clear_on_submit=True):
                solicitante = st.text_input("Solicitante", value=st.session_state.get("user_name", ""))
                tipo = st.selectbox("Tipo", ["Material", "Livro didático", "Outro"])
                item_codigo = ""
                item_desc = ""
                if tipo == "Material":
                    codigos = [f"{i.get('codigo','')} - {i.get('descricao','')}" for i in st.session_state["inventory"]]
                    item_sel = st.selectbox("Item", codigos if codigos else [""])
                    if item_sel:
                        item_codigo = item_sel.split(" - ")[0].strip()
                        item_desc = " - ".join(item_sel.split(" - ")[1:]).strip()
                elif tipo == "Livro didático":
                    nivel = st.selectbox("Livro/Nível", book_levels())
                    item_codigo = nivel
                    item_desc = f"Livro didático {nivel}"
                else:
                    item_desc = st.text_input("Descrição do pedido")
                quantidade = st.number_input("Quantidade", min_value=1, step=1, value=1)
                observacao = st.text_area("Observações")
                if st.form_submit_button("Registrar pedido"):
                    st.session_state["material_orders"].append(
                        {
                            "id": uuid.uuid4().hex[:10],
                            "data": datetime.datetime.now().strftime("%d/%m/%Y %H:%M"),
                            "solicitante": solicitante.strip(),
                            "tipo": tipo,
                            "item_codigo": item_codigo,
                            "item": item_desc,
                            "quantidade": int(quantidade),
                            "status": "Aberto",
                            "observacao": observacao.strip(),
                        }
                    )
                    save_list(MATERIAL_ORDERS_FILE, st.session_state["material_orders"])
                    st.success("Pedido registrado com sucesso!")

            st.markdown("### Pedidos Registrados")
            pedidos = st.session_state["material_orders"]
            if pedidos:
                st.dataframe(pd.DataFrame(pedidos), use_container_width=True)
            else:
                st.info("Nenhum pedido registrado.")

            st.markdown("### Automatizar Pedido (IA)")
            itens_baixo = [
                i for i in st.session_state["inventory"]
                if parse_int(i.get("saldo", 0)) < parse_int(i.get("minimo", 0)) and bool(i.get("ativo", True))
            ]
            if st.button("Gerar pedido automático (IA)"):
                if not itens_baixo:
                    st.info("Nenhum item abaixo do mínimo.")
                else:
                    for item in itens_baixo:
                        saldo = parse_int(item.get("saldo", 0))
                        minimo = parse_int(item.get("minimo", 0))
                        maximo = parse_int(item.get("maximo", 0))
                        qtd = (maximo - saldo) if maximo > 0 else (minimo - saldo)
                        qtd = max(qtd, 1)
                        st.session_state["material_orders"].append(
                            {
                                "id": uuid.uuid4().hex[:10],
                                "data": datetime.datetime.now().strftime("%d/%m/%Y %H:%M"),
                                "solicitante": "Sistema (IA)",
                                "tipo": "Material",
                                "item_codigo": str(item.get("codigo", "")),
                                "item": item.get("descricao", ""),
                                "quantidade": int(qtd),
                                "status": "Sugerido",
                                "observacao": "Pedido automático por estoque abaixo do mínimo.",
                            }
                        )
                    save_list(MATERIAL_ORDERS_FILE, st.session_state["material_orders"])

                    api_key = get_groq_api_key()
                    if not api_key:
                        st.warning("Configure GROQ_API_KEY para gerar resumo automático do pedido.")
                    else:
                        resumo_itens = [
                            f"{i.get('codigo','')}: {i.get('descricao','')} (saldo {i.get('saldo','')}, mínimo {i.get('minimo','')})"
                            for i in itens_baixo
                        ]
                        system_prompt = (
                            "Voce e um assistente de compras. Gere um resumo curto e objetivo para solicitar compra de materiais."
                        )
                        user_prompt = "Itens abaixo do minimo:\n" + "\n".join(resumo_itens)
                        client = OpenAI(api_key=api_key, base_url="https://api.groq.com/openai/v1")
                        try:
                            result = client.chat.completions.create(
                                model=os.getenv("ACTIVE_CHATBOT_MODEL", "llama-3.3-70b-versatile"),
                                messages=[
                                    {"role": "system", "content": system_prompt},
                                    {"role": "user", "content": user_prompt},
                                ],
                                temperature=0.2,
                                max_tokens=300,
                            )
                            st.session_state["order_ai_summary"] = (result.choices[0].message.content or "").strip()
                        except Exception as ex:
                            st.session_state["order_ai_summary"] = f"Falha ao gerar resumo IA: {ex}"

            if st.session_state.get("order_ai_summary"):
                st.markdown("#### Resumo IA")
                st.write(st.session_state["order_ai_summary"])

    elif menu_coord == "Certificados":
        st.markdown('<div class="main-header">Gerador de Certificados</div>', unsafe_allow_html=True)
        alunos = [s.get("nome", "") for s in st.session_state["students"]]
        if not alunos:
            st.info("Nenhum aluno cadastrado.")
        else:
            logo_path = get_logo_path()
            mister_logo_path = get_mister_wiz_logo_path()
            logo_b64 = ""
            mister_b64 = ""
            if logo_path:
                logo_b64 = base64.b64encode(logo_path.read_bytes()).decode("utf-8")
            if mister_logo_path:
                mister_b64 = base64.b64encode(mister_logo_path.read_bytes()).decode("utf-8")

            tab1, tab2 = st.tabs(["Gerar", "Histórico"])

            with tab1:
                with st.form("cert_form", clear_on_submit=True):
                    aluno = st.selectbox("Aluno", alunos)
                    turma = ""
                    prof = ""
                    aluno_obj = next((s for s in st.session_state["students"] if s.get("nome") == aluno), {})
                    turma = aluno_obj.get("turma", "")
                    if turma:
                        turma_obj = next((c for c in st.session_state["classes"] if c.get("nome") == turma), {})
                        prof = turma_obj.get("professor", "")

                    curso = st.text_input("Curso", value="Inglês - Mister Wiz")
                    carga = st.text_input("Carga horária (horas)", value="60")
                    data_cert = st.date_input("Data de conclusão", value=datetime.date.today(), format="DD/MM/YYYY")
                    assinatura1 = st.text_input("Assinatura 1", value="Coordenação")
                    assinatura2 = st.text_input("Assinatura 2", value="Direção")
                    observacao = st.text_input("Observação", value="Certificado válido em todo território nacional.")
                    gerar = st.form_submit_button("Gerar certificado")

                if gerar:
                    data = {
                        "instituicao": "Active Educacional / Mister Wiz",
                        "aluno": aluno,
                        "curso": curso,
                        "carga": carga,
                        "data": data_cert.strftime("%d/%m/%Y") if data_cert else "",
                        "turma": turma,
                        "professor": prof,
                        "assinatura1": assinatura1,
                        "assinatura2": assinatura2,
                        "observacao": observacao,
                    }
                    st.session_state["cert_preview_html"] = build_certificate_html(data, logo_b64, mister_b64)
                    st.session_state["cert_preview_pdf"] = build_certificate_pdf_bytes(data, logo_path, mister_logo_path)
                    st.session_state["cert_preview_data"] = data
                    st.session_state["certificates"].append(
                        {
                            "id": uuid.uuid4().hex[:10],
                            "data_emissao": datetime.datetime.now().strftime("%d/%m/%Y %H:%M"),
                            **data,
                        }
                    )
                    save_list(CERTIFICATES_FILE, st.session_state["certificates"])
                    st.success("Certificado gerado com sucesso!")

            with tab2:
                certs = st.session_state["certificates"]
                if not certs:
                    st.info("Nenhum certificado emitido.")
                else:
                    filtro_aluno = st.selectbox("Filtrar por aluno", ["Todos"] + sorted({c.get("aluno", "") for c in certs}))
                    dados = certs
                    if filtro_aluno != "Todos":
                        dados = [c for c in certs if c.get("aluno") == filtro_aluno]
                    if dados:
                        df = pd.DataFrame(dados)
                        col_order = ["data_emissao", "aluno", "curso", "data", "carga", "turma", "professor"]
                        df = df[[c for c in col_order if c in df.columns]]
                        st.dataframe(df, use_container_width=True)

                        options = [f"{c.get('data_emissao','')} - {c.get('aluno','')} - {c.get('curso','')}" for c in dados]
                        sel = st.selectbox("Abrir certificado", options)
                        sel_obj = dados[options.index(sel)]
                        if st.button("Carregar certificado"):
                            st.session_state["cert_preview_html"] = build_certificate_html(sel_obj, logo_b64, mister_b64)
                            st.session_state["cert_preview_pdf"] = build_certificate_pdf_bytes(sel_obj, logo_path, mister_logo_path)
                            st.session_state["cert_preview_data"] = sel_obj
                    else:
                        st.info("Nenhum certificado encontrado.")

            if st.session_state.get("cert_preview_html"):
                st.markdown("### Pré-visualização")
                st.components.v1.html(st.session_state["cert_preview_html"], height=820, scrolling=True)
                name_base = st.session_state.get("cert_preview_data", {}).get("aluno", "certificado")
                name_base = name_base.replace(" ", "_").lower() if name_base else "certificado"
                st.download_button(
                    "Baixar certificado (HTML)",
                    data=st.session_state["cert_preview_html"],
                    file_name=f"certificado_{name_base}.html",
                    mime="text/html",
                )
                if st.session_state.get("cert_preview_pdf"):
                    st.download_button(
                        "Baixar certificado (PDF)",
                        data=st.session_state["cert_preview_pdf"],
                        file_name=f"certificado_{name_base}.pdf",
                        mime="application/pdf",
                    )
                else:
                    st.warning("Para gerar PDF, instale a biblioteca reportlab.")

    elif menu_coord == "Livros":
        st.markdown('<div class="main-header">Livros Didáticos</div>', unsafe_allow_html=True)
        tab1, tab2 = st.tabs(["Biblioteca", "Configurar Links"])
        with tab1:
            render_books_section(st.session_state.get("books", []), "Todos os Livros", key_prefix="coord_livros")
        with tab2:
            with st.form("edit_books"):
                updated = []
                for idx, b in enumerate(st.session_state.get("books", [])):
                    st.markdown(f"### {b.get('nivel','Livro')}")
                    titulo = st.text_input("Título", value=b.get("titulo", ""), key=f"book_title_{idx}")
                    url = st.text_input("Link para download/abrir", value=b.get("url", ""), key=f"book_url_{idx}")
                    file_path = st.text_input("Arquivo local (opcional)", value=b.get("file_path", ""), key=f"book_file_{idx}")
                    updated.append(
                        {
                            "nivel": b.get("nivel", f"Livro {idx+1}"),
                            "titulo": titulo.strip(),
                            "url": url.strip(),
                            "file_path": file_path.strip(),
                        }
                    )
                    st.markdown("---")
                if st.form_submit_button("Salvar configurações"):
                    st.session_state["books"] = updated
                    save_list(BOOKS_FILE, st.session_state["books"])
                    st.success("Livros atualizados!")

    elif menu_coord == "Alunos":
        st.markdown('<div class="main-header">Gestão de Alunos</div>', unsafe_allow_html=True)
        tab1, tab2, tab3 = st.tabs(["Lista de Alunos", "Cadastro Completo", "Gerenciar / Excluir"])

        with tab1:
            st.markdown("### Importar / Exportar Excel")
            with st.expander("Importar / Exportar Excel", expanded=False):
                col_exp, col_imp = st.columns(2)
                with col_exp:
                    st.caption("Exporta todos os alunos ou apenas os filtrados.")
                    export_scope = st.selectbox(
                        "Exportar",
                        ["Todos os alunos", "Apenas filtrados"],
                        key="students_export_scope",
                    )
                    export_students = st.session_state["students"]
                    if export_scope == "Apenas filtrados":
                        export_students = st.session_state.get("students_filtered", export_students)
                    df_export = _build_students_export_df(export_students)
                    buffer = io.BytesIO()
                    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
                        df_export.to_excel(writer, index=False, sheet_name="alunos")
                    buffer.seek(0)
                    st.download_button(
                        "Exportar Excel",
                        data=buffer,
                        file_name="alunos.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    )
                    template_buffer = io.BytesIO()
                    with pd.ExcelWriter(template_buffer, engine="openpyxl") as writer:
                        pd.DataFrame(columns=STUDENT_IMPORT_COLUMNS).to_excel(
                            writer, index=False, sheet_name="alunos"
                        )
                    template_buffer.seek(0)
                    st.download_button(
                        "Baixar modelo",
                        data=template_buffer,
                        file_name="modelo_alunos.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    )
                with col_imp:
                    st.caption("Importa um Excel no padrÃ£o do modelo.")
                    upload = st.file_uploader(
                        "Arquivo Excel",
                        type=["xlsx", "xls"],
                        key="students_import_file",
                    )
                    atualizar = st.checkbox(
                        "Atualizar alunos existentes (por e-mail ou nome)",
                        value=True,
                        key="students_import_update",
                    )
                    if upload:
                        try:
                            df_raw = pd.read_excel(upload)
                        except Exception as exc:
                            st.error(f"Erro ao ler o Excel: {exc}")
                        else:
                            df_import = _normalize_import_df(df_raw)
                            st.dataframe(df_import.head(50), use_container_width=True)
                            if st.button("Importar alunos", key="students_import_btn"):
                                alunos = st.session_state["students"]
                                index_by_email = {
                                    str(s.get("email", "")).strip().lower(): i
                                    for i, s in enumerate(alunos)
                                    if str(s.get("email", "")).strip()
                                }
                                index_by_name = {
                                    str(s.get("nome", "")).strip().lower(): i
                                    for i, s in enumerate(alunos)
                                    if str(s.get("nome", "")).strip()
                                }
                                added = 0
                                updated = 0
                                skipped = 0
                                new_users = 0

                                for _, row in df_import.iterrows():
                                    student = _student_from_row(row)
                                    if not student:
                                        skipped += 1
                                        continue
                                    email_key = student.get("email", "").strip().lower()
                                    name_key = student.get("nome", "").strip().lower()
                                    idx = index_by_email.get(email_key) if email_key else None
                                    if idx is None and name_key:
                                        idx = index_by_name.get(name_key)

                                    if idx is not None:
                                        if atualizar:
                                            existing = alunos[idx]
                                            for key, value in student.items():
                                                if key == "responsavel":
                                                    if value:
                                                        resp = existing.get("responsavel", {})
                                                        for rkey, rvalue in value.items():
                                                            if rvalue:
                                                                resp[rkey] = rvalue
                                                        existing["responsavel"] = resp
                                                else:
                                                    if value not in ("", None):
                                                        existing[key] = value
                                            if not str(existing.get("matricula", "")).strip():
                                                existing["matricula"] = _next_student_matricula(alunos)
                                            updated += 1
                                        else:
                                            skipped += 1
                                    else:
                                        if not str(student.get("matricula", "")).strip():
                                            student["matricula"] = _next_student_matricula(alunos)
                                        alunos.append(student)
                                        idx_new = len(alunos) - 1
                                        if email_key:
                                            index_by_email[email_key] = idx_new
                                        if name_key:
                                            index_by_name[name_key] = idx_new
                                        added += 1

                                    login = student.get("usuario", "").strip()
                                    senha = student.get("senha", "").strip()
                                    if login and senha and not find_user(login):
                                        st.session_state["users"].append(
                                            {
                                                "usuario": login,
                                                "senha": senha,
                                                "perfil": "Aluno",
                                                "pessoa": student.get("nome", ""),
                                            }
                                        )
                                        new_users += 1

                                if added or updated:
                                    save_list(STUDENTS_FILE, alunos)
                                    if new_users:
                                        save_users(st.session_state["users"])
                                    st.success(
                                        f"ImportaÃ§Ã£o concluÃ­da: {added} adicionados, {updated} atualizados, {skipped} ignorados."
                                    )
                                    st.rerun()
                                else:
                                    st.warning(
                                        f"Nenhum aluno importado. Ignorados: {skipped}."
                                    )
                    else:
                        st.info("Envie um arquivo Excel para importar alunos.")

            if not st.session_state["students"]:
                st.info("Nenhum aluno cadastrado.")
            else:
                turmas_opts = ["Todas"] + sorted({s.get("turma", "Sem Turma") for s in st.session_state["students"]})
                profs_opts = [
                    "Todos"
                ] + sorted({
                    str(c.get("professor", "")).strip()
                    for c in st.session_state["classes"]
                    if str(c.get("professor", "")).strip()
                })

                col_f1, col_f2 = st.columns(2)
                with col_f1:
                    turma_filtro = st.selectbox("Filtrar por Turma", turmas_opts)
                with col_f2:
                    prof_filtro = st.selectbox("Filtrar por Professor", profs_opts if profs_opts else ["Todos"])

                alunos_filtrados = st.session_state["students"]
                if turma_filtro != "Todas":
                    alunos_filtrados = [s for s in alunos_filtrados if s.get("turma") == turma_filtro]
                if prof_filtro != "Todos":
                    turmas_prof = {
                        c.get("nome")
                        for c in st.session_state["classes"]
                        if str(c.get("professor", "")).strip() == prof_filtro
                    }
                    alunos_filtrados = [s for s in alunos_filtrados if s.get("turma") in turmas_prof]
                st.session_state["students_filtered"] = alunos_filtrados

                if not alunos_filtrados:
                    st.info("Nenhum aluno encontrado com os filtros selecionados.")
                else:
                    df_alunos = pd.json_normalize(alunos_filtrados)
                    if "nascimento" in df_alunos.columns and "data_nascimento" not in df_alunos.columns:
                        df_alunos = df_alunos.rename(columns={"nascimento": "data_nascimento"})

                    col_default = [
                        "nome",
                        "matricula",
                        "turma",
                        "email",
                        "celular",
                        "data_nascimento",
                        "idade",
                        "rg",
                        "cpf",
                        "cidade",
                        "bairro",
                        "responsavel.nome",
                        "responsavel.celular",
                        "responsavel.email",
                    ]
                    colunas = list(df_alunos.columns)
                    colunas_sel = st.multiselect(
                        "Colunas visíveis",
                        colunas,
                        default=[c for c in col_default if c in colunas],
                    )
                    if colunas_sel:
                        df_alunos = df_alunos[colunas_sel]
                    st.dataframe(df_alunos, use_container_width=True)

        with tab2:
            modulos = [
                "Presencial em Turma",
                "Turma online",
                "Aulas Vip",
                "Intensivo vip online",
                "Kids e teens completo",
            ]
            # Nao podemos "resetar" valores de widgets diretamente apos o submit (StreamlitAPIException).
            # Em vez disso, usamos chaves versionadas e incrementamos a versao apenas quando o cadastro
            # for concluido com sucesso, o que faz o formulario "limpar" sem mexer nos widgets atuais.
            st.session_state.setdefault("add_student_form_version", 0)
            form_ver = int(st.session_state["add_student_form_version"])

            def _sfk(name: str) -> str:
                return f"{name}__v{form_ver}"

            student_form_defaults = {
                _sfk("add_student_nome"): "",
                _sfk("add_student_data_nascimento"): datetime.date.today(),
                _sfk("add_student_celular"): "",
                _sfk("add_student_email"): "",
                _sfk("add_student_rg"): "",
                _sfk("add_student_cpf"): "",
                _sfk("add_student_natal"): "",
                _sfk("add_student_pais"): "Brasil",
                _sfk("add_student_cep"): "",
                _sfk("add_student_cidade"): "",
                _sfk("add_student_bairro"): "",
                _sfk("add_student_rua"): "",
                _sfk("add_student_numero"): "",
                _sfk("add_student_turma"): "Sem Turma",
                _sfk("add_student_modulo"): modulos[0],
                _sfk("add_student_livro"): "Automatico (Turma)",
                _sfk("add_student_login"): "",
                _sfk("add_student_senha"): "",
                _sfk("add_student_resp_nome"): "",
                _sfk("add_student_resp_cpf"): "",
                _sfk("add_student_resp_cel"): "",
                _sfk("add_student_resp_email"): "",
            }
            for key, default_value in student_form_defaults.items():
                st.session_state.setdefault(key, default_value)

            turma_opts = ["Sem Turma"] + class_names()
            turma_key = _sfk("add_student_turma")
            if st.session_state.get(turma_key) not in turma_opts:
                st.session_state[turma_key] = "Sem Turma"

            modulo_key = _sfk("add_student_modulo")
            if st.session_state.get(modulo_key) not in modulos:
                st.session_state[modulo_key] = modulos[0]

            livro_opts = ["Automatico (Turma)"] + book_levels()
            livro_key = _sfk("add_student_livro")
            if st.session_state.get(livro_key) not in livro_opts:
                st.session_state[livro_key] = "Automatico (Turma)"

            feedback = st.session_state.pop("add_student_feedback", None)
            if feedback:
                st.success(feedback.get("success", "Cadastro realizado com sucesso!"))
                info_msg = feedback.get("info")
                if info_msg:
                    st.info(info_msg)

            with st.form("add_student_full", clear_on_submit=False):
                st.markdown("### Dados Pessoais")
                c1, c2, c3, c4 = st.columns(4)
                with c1: nome = st.text_input("Nome Completo *", key=_sfk("add_student_nome"))
                matricula_auto = _next_student_matricula(st.session_state["students"])
                with c2: st.text_input("No. da Matricula", value=matricula_auto, disabled=True)
                with c3:
                    data_nascimento = st.date_input(
                        "Data de Nascimento *",
                        key=_sfk("add_student_data_nascimento"),
                        format="DD/MM/YYYY",
                        help="Formato: DD/MM/AAAA",
                        min_value=datetime.date(1900, 1, 1),
                        max_value=datetime.date(2036, 12, 31),
                    )
                idade_auto = _calc_age_from_date_obj(data_nascimento) or 1
                with c4: st.number_input("Idade *", min_value=1, max_value=120, step=1, value=idade_auto, disabled=True)

                c4, c5, c6 = st.columns(3)
                with c4: celular = st.text_input("Celular/WhatsApp *", key=_sfk("add_student_celular"))
                with c5: email = st.text_input("E-mail do Aluno *", key=_sfk("add_student_email"))
                with c6: rg = st.text_input("RG", key=_sfk("add_student_rg"))

                c7, c8, c9 = st.columns(3)
                with c7: cpf = st.text_input("CPF", key=_sfk("add_student_cpf"))
                with c8: natal = st.text_input("Cidade Natal", key=_sfk("add_student_natal"))
                with c9: pais = st.text_input("Pais de Origem", key=_sfk("add_student_pais"))

                st.divider()
                st.markdown("### Endereco")
                ce1, ce2, ce3 = st.columns(3)
                with ce1: cep = st.text_input("CEP", key=_sfk("add_student_cep"))
                with ce2: cidade = st.text_input("Cidade", key=_sfk("add_student_cidade"))
                with ce3: bairro = st.text_input("Bairro", key=_sfk("add_student_bairro"))

                ce4, ce5 = st.columns([3, 1])
                with ce4: rua = st.text_input("Rua", key=_sfk("add_student_rua"))
                with ce5: numero = st.text_input("Numero", key=_sfk("add_student_numero"))

                st.divider()
                st.markdown("### Turma")
                turma = st.selectbox("Vincular a Turma", turma_opts, key=turma_key)
                modulo_sel = st.selectbox("Modulo do curso", modulos, key=modulo_key)
                livro_sel = st.selectbox("Livro/Nivel", livro_opts, key=livro_key)

                st.divider()
                st.markdown("### Acesso do Aluno (opcional)")
                ca1, ca2 = st.columns(2)
                with ca1: login_aluno = st.text_input("Login do Aluno", key=_sfk("add_student_login"))
                with ca2: senha_aluno = st.text_input("Senha do Aluno", type="password", key=_sfk("add_student_senha"))

                st.divider()
                st.markdown("### Responsavel Legal / Financeiro")
                st.caption("Obrigatorio para menores de 18 anos.")

                cr1, cr2 = st.columns(2)
                with cr1: resp_nome = st.text_input("Nome do Responsavel", key=_sfk("add_student_resp_nome"))
                with cr2: resp_cpf = st.text_input("CPF do Responsavel", key=_sfk("add_student_resp_cpf"))

                cr3, cr4 = st.columns(2)
                with cr3: resp_cel = st.text_input("Celular do Responsavel", key=_sfk("add_student_resp_cel"))
                with cr4: resp_email = st.text_input("E-mail do Responsavel", key=_sfk("add_student_resp_email"))

                if st.form_submit_button("Cadastrar Aluno"):
                    idade_final = _calc_age_from_date_obj(data_nascimento) or 1
                    matricula_final = _next_student_matricula(st.session_state["students"])
                    nome = nome.strip()
                    email = email.strip()
                    login_aluno = login_aluno.strip()
                    senha_aluno = senha_aluno.strip()
                    resp_nome = resp_nome.strip()
                    resp_cpf = resp_cpf.strip()
                    resp_email = resp_email.strip()

                    if idade_final < 18 and (not resp_nome or not resp_cpf):
                        st.error("ERRO: Aluno menor de idade! E obrigatorio preencher Nome e CPF do Responsavel.")
                    elif not nome or not email:
                        st.error("ERRO: Nome e E-mail sao obrigatorios.")
                    elif (login_aluno and not senha_aluno) or (senha_aluno and not login_aluno):
                        st.error("ERRO: Para criar o login, informe usuario e senha.")
                    elif login_aluno and find_user(login_aluno):
                        st.error("ERRO: Este login ja existe.")
                    else:
                        turma_obj = next((c for c in st.session_state["classes"] if c.get("nome") == turma), {})
                        livro_turma = turma_obj.get("livro", "")
                        livro_final = livro_turma if livro_sel == "Automatico (Turma)" else livro_sel
                        novo_aluno = {
                            "nome": nome,
                            "matricula": matricula_final,
                            "idade": idade_final,
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
                            "modulo": modulo_sel,
                            "livro": livro_final,
                            "usuario": login_aluno,
                            "senha": senha_aluno,
                            "responsavel": {
                                "nome": resp_nome,
                                "cpf": resp_cpf,
                                "celular": resp_cel,
                                "email": resp_email,
                            },
                        }
                        st.session_state["students"].append(novo_aluno)
                        save_list(STUDENTS_FILE, st.session_state["students"])

                        if login_aluno and senha_aluno:
                            st.session_state["users"].append(
                                {
                                    "usuario": login_aluno,
                                    "senha": senha_aluno,
                                    "perfil": "Aluno",
                                    "pessoa": nome,
                                }
                            )
                            save_users(st.session_state["users"])

                        destinatario_email = resp_email if idade_final < 18 else email
                        st.session_state["add_student_feedback"] = {
                            "success": "Cadastro realizado com sucesso!",
                            "info": f"E-mail enviado automaticamente para {destinatario_email} com: Comunicado de Boas-vindas, Link da Aula e Boletos.",
                        }
                        st.session_state["add_student_form_version"] = form_ver + 1
                        st.rerun()

        with tab3:
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

                    current_dn = parse_date(aluno_obj.get("data_nascimento", "") or aluno_obj.get("nascimento", "")) or datetime.date.today()
                    try:
                        current_idade = int(aluno_obj.get("idade") or 1)
                    except Exception:
                        current_idade = 1

                    with st.form("edit_student"):
                        st.subheader(f"Editando: {aluno_obj['nome']}")
                        new_nome = st.text_input("Nome", value=aluno_obj.get("nome", ""))
                        matricula_atual = aluno_obj.get("matricula", "") or _next_student_matricula(st.session_state["students"])
                        st.text_input("Nº da Matrícula", value=matricula_atual, disabled=True)

                        c1, c2 = st.columns(2)
                        with c1: new_cel = st.text_input("Celular", value=aluno_obj.get("celular", ""))
                        with c2: new_email = st.text_input("Email", value=aluno_obj.get("email", ""))

                        c3, c4 = st.columns(2)
                        with c3: new_dn = st.date_input("Data de Nascimento", value=current_dn, format="DD/MM/YYYY", help="Formato: DD/MM/AAAA", min_value=datetime.date(1900, 1, 1), max_value=datetime.date(2036, 12, 31))
                        idade_edit_auto = _calc_age_from_date_obj(new_dn) or current_idade
                        with c4: st.number_input("Idade", min_value=1, max_value=120, step=1, value=idade_edit_auto, disabled=True)

                        new_turma = st.selectbox("Turma", turmas, index=turmas.index(current_turma))
                        modulos = [
                            "Presencial em Turma",
                            "Turma online",
                            "Aulas Vip",
                            "Intensivo vip online",
                            "Kids e teens completo",
                        ]
                        modulo_atual = aluno_obj.get("modulo", modulos[0] if modulos else "")
                        if modulo_atual not in modulos and modulo_atual:
                            modulos.append(modulo_atual)
                        new_modulo = st.selectbox(
                            "Módulo do curso",
                            modulos,
                            index=modulos.index(modulo_atual) if modulo_atual in modulos else 0,
                        )
                        livro_atual = aluno_obj.get("livro", "")
                        livro_opts = ["Automático (Turma)"] + book_levels()
                        if livro_atual and livro_atual not in livro_opts:
                            livro_opts.append(livro_atual)
                        livro_index = livro_opts.index(livro_atual) if livro_atual in livro_opts else 0
                        new_livro = st.selectbox("Livro/Nível", livro_opts, index=livro_index)

                        st.markdown("### Acesso do Aluno")
                        c5, c6 = st.columns(2)
                        with c5: new_login = st.text_input("Login do Aluno", value=aluno_obj.get("usuario", ""))
                        with c6: new_senha = st.text_input("Senha do Aluno", value=aluno_obj.get("senha", ""), type="password")

                        c_edit, c_del = st.columns([1, 1])
                        with c_edit:
                            if st.form_submit_button("Salvar Alterações"):
                                old_login = aluno_obj.get("usuario", "").strip()
                                login = new_login.strip() or old_login
                                senha = new_senha.strip() or aluno_obj.get("senha", "")

                                if login and find_user(login) and (not old_login or login.lower() != old_login.lower()):
                                    st.error("ERRO: Este login já existe.")
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

                                    turma_obj = next((c for c in st.session_state["classes"] if c.get("nome") == new_turma), {})
                                    livro_turma = turma_obj.get("livro", "")
                                    livro_final = livro_turma if new_livro == "Automático (Turma)" else new_livro

                                    aluno_obj["nome"] = new_nome
                                    aluno_obj["matricula"] = matricula_atual
                                    aluno_obj["celular"] = new_cel
                                    aluno_obj["turma"] = new_turma
                                    aluno_obj["email"] = new_email
                                    aluno_obj["data_nascimento"] = new_dn.strftime("%d/%m/%Y") if new_dn else ""
                                    aluno_obj["idade"] = _calc_age_from_date_obj(new_dn) or current_idade
                                    aluno_obj["modulo"] = new_modulo
                                    aluno_obj["livro"] = livro_final
                                    aluno_obj["usuario"] = login
                                    aluno_obj["senha"] = senha
                                    aluno_obj.pop("nascimento", None)

                                    save_list(STUDENTS_FILE, st.session_state["students"])
                                    st.success("Dados atualizados!")
                                    st.rerun()
                        with c_del:
                            if st.form_submit_button("EXCLUIR ALUNO", type="primary"):
                                login = aluno_obj.get("usuario", "").strip()
                                if login:
                                    user_obj = find_user(login)
                                    if user_obj and user_obj.get("perfil") == "Aluno":
                                        st.session_state["users"].remove(user_obj)
                                        save_users(st.session_state["users"])
                                st.session_state["students"].remove(aluno_obj)
                                save_list(STUDENTS_FILE, st.session_state["students"])
                                st.error("Aluno excluído permanentemente.")
                                st.rerun()

    elif menu_coord == "Professores":
        st.markdown('<div class="main-header">Gestão de Professores</div>', unsafe_allow_html=True)
        tab1, tab2 = st.tabs(["Novo Professor", "Gerenciar / Excluir"])
        with tab1:
            with st.form("add_prof", clear_on_submit=True):
                c1, c2 = st.columns(2)
                with c1: nome = st.text_input("Nome")
                with c2: area = st.text_input("Area")

                c3, c4 = st.columns(2)
                with c3: login_prof = st.text_input("Login do Professor")
                with c4: senha_prof = st.text_input("Senha do Professor", type="password")

                if st.form_submit_button("Cadastrar"):
                    if (login_prof and not senha_prof) or (senha_prof and not login_prof):
                        st.error("ERRO: Para criar o login, informe usuário e senha.")
                    elif login_prof and find_user(login_prof):
                        st.error("ERRO: Este login já existe.")
                    else:
                        st.session_state["teachers"].append(
                            {
                                "nome": nome,
                                "area": area,
                                "usuario": login_prof.strip(),
                                "senha": senha_prof.strip(),
                            }
                        )
                        save_list(TEACHERS_FILE, st.session_state["teachers"])
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
                        st.success("Cadastro realizado com sucesso!")
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
                        new_area = st.text_input("Area", value=prof_obj.get("area", ""))

                        c3, c4 = st.columns(2)
                        with c3: new_login = st.text_input("Login do Professor", value=prof_obj.get("usuario", ""))
                        with c4: new_senha = st.text_input("Senha do Professor", value=prof_obj.get("senha", ""), type="password")

                        c_edit, c_del = st.columns([1, 1])
                        with c_edit:
                            if st.form_submit_button("Salvar Alterações"):
                                old_login = prof_obj.get("usuario", "").strip()
                                login = new_login.strip() or old_login
                                senha = new_senha.strip() or prof_obj.get("senha", "")

                                if login and find_user(login) and (not old_login or login.lower() != old_login.lower()):
                                    st.error("ERRO: Este login já existe.")
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

                                    old_nome = prof_obj["nome"]
                                    for turma in st.session_state["classes"]:
                                        if str(turma.get("professor", "")).strip() == str(old_nome).strip():
                                            turma["professor"] = new_nome
                                    save_list(CLASSES_FILE, st.session_state["classes"])

                                    prof_obj["nome"] = new_nome
                                    prof_obj["area"] = new_area
                                    prof_obj["usuario"] = login
                                    prof_obj["senha"] = senha
                                    save_list(TEACHERS_FILE, st.session_state["teachers"])
                                    st.success("Professor atualizado!")
                                    st.rerun()
                        with c_del:
                            if st.form_submit_button("EXCLUIR PROFESSOR", type="primary"):
                                login = prof_obj.get("usuario", "").strip()
                                if login:
                                    user_obj = find_user(login)
                                    if user_obj and user_obj.get("perfil") == "Professor":
                                        st.session_state["users"].remove(user_obj)
                                        save_users(st.session_state["users"])

                                for turma in st.session_state["classes"]:
                                    if str(turma.get("professor", "")).strip() == str(prof_obj.get("nome", "")).strip():
                                        turma["professor"] = "Sem Professor"
                                save_list(CLASSES_FILE, st.session_state["classes"])

                                st.session_state["teachers"].remove(prof_obj)
                                save_list(TEACHERS_FILE, st.session_state["teachers"])
                                st.error("Professor excluído.")
                                st.rerun()

    elif menu_coord == "Turmas":
        st.markdown('<div class="main-header">Gestão de Turmas</div>', unsafe_allow_html=True)
        tab1, tab2 = st.tabs(["Nova Turma", "Gerenciar / Excluir"])

        with tab1:
            with st.form("add_class"):
                c1, c2 = st.columns(2)
                with c1: nome = st.text_input("Nome da Turma")
                with c2: prof = st.selectbox("Professor", ["Sem Professor"] + teacher_names())
                modulo_opts = class_module_options()
                modulo = st.selectbox("Modulo da Turma", modulo_opts)
                c3, c4 = st.columns(2)
                with c3: dias = st.text_input("Dias e Horários")
                with c4: link = st.text_input("Link do Zoom (Inicial)")
                livro = st.selectbox("Livro/Nível da Turma", book_levels())
                if st.form_submit_button("Cadastrar"):
                    st.session_state["classes"].append(
                        {
                            "nome": nome,
                            "professor": prof,
                            "modulo": modulo,
                            "dias": dias,
                            "link_zoom": link,
                            "livro": livro,
                        }
                    )
                    save_list(CLASSES_FILE, st.session_state["classes"])
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
                        current_modulo = turma_obj.get("modulo", "")
                        modulo_opts = class_module_options()
                        if current_modulo and current_modulo not in modulo_opts:
                            modulo_opts.append(current_modulo)
                        modulo_index = modulo_opts.index(current_modulo) if current_modulo in modulo_opts else 0
                        new_modulo = st.selectbox("Modulo da Turma", modulo_opts, index=modulo_index)
                        new_dias = st.text_input("Dias e Horários", value=turma_obj.get("dias", ""))
                        new_link = st.text_input("Link do Zoom", value=turma_obj.get("link_zoom", ""))
                        livro_atual = turma_obj.get("livro", "")
                        livro_opts = book_levels()
                        if livro_atual and livro_atual not in livro_opts:
                            livro_opts.append(livro_atual)
                        new_livro = st.selectbox("Livro/Nível da Turma", livro_opts, index=livro_opts.index(livro_atual) if livro_atual in livro_opts else 0)

                        c_edit, c_del = st.columns([1, 1])
                        with c_edit:
                            if st.form_submit_button("Salvar Alterações"):
                                old_nome = turma_obj.get("nome", "")
                                turma_obj["nome"] = new_nome
                                turma_obj["professor"] = new_prof
                                turma_obj["modulo"] = new_modulo
                                turma_obj["dias"] = new_dias
                                turma_obj["link_zoom"] = new_link
                                turma_obj["livro"] = new_livro

                                if old_nome and new_nome and old_nome != new_nome:
                                    for aluno in st.session_state["students"]:
                                        if aluno.get("turma") == old_nome:
                                            aluno["turma"] = new_nome
                                    save_list(STUDENTS_FILE, st.session_state["students"])

                                save_list(CLASSES_FILE, st.session_state["classes"])
                                st.success("Turma atualizada!")
                                st.rerun()
                        with c_del:
                            if st.form_submit_button("EXCLUIR TURMA", type="primary"):
                                nome_turma = turma_obj.get("nome", "")
                                if nome_turma:
                                    for aluno in st.session_state["students"]:
                                        if aluno.get("turma") == nome_turma:
                                            aluno["turma"] = "Sem Turma"
                                    save_list(STUDENTS_FILE, st.session_state["students"])
                                st.session_state["classes"].remove(turma_obj)
                                save_list(CLASSES_FILE, st.session_state["classes"])
                                st.error("Turma excluída.")
                                st.rerun()

    elif menu_coord == "Financeiro":
        st.markdown('<div class="main-header">Financeiro</div>', unsafe_allow_html=True)
        tab1, tab2 = st.tabs(["Contas a Receber", "Contas a Pagar"])
        with tab1:
            with st.form("add_rec"):
                st.markdown("### Lançar Recebimento")
                c1, c2, c3 = st.columns(3)
                with c1: desc = st.text_input("Descrição (Ex: Mensalidade)")
                with c2: val = st.text_input("Valor (Ex: 150,00)")
                with c3: categoria = st.selectbox("Categoria", ["Mensalidade", "Material", "Taxa de Matrícula"])
                aluno = st.selectbox("Aluno", [s["nome"] for s in st.session_state["students"]])
                c4, c5, c6 = st.columns(3)
                with c4: data_lanc = st.date_input("Data do lançamento", value=datetime.date.today(), format="DD/MM/YYYY")
                with c5: venc = st.date_input("Vencimento", value=datetime.date.today(), format="DD/MM/YYYY")
                material_payment = "A vista"
                if categoria == "Material":
                    with c6:
                        material_payment = st.selectbox(
                            "Pagamento do Material",
                            material_payment_options(),
                        )
                    cobranca = material_payment
                else:
                    with c6: cobranca = st.selectbox("Cobrança", ["Boleto", "Pix", "Cartao", "Dinheiro"])
                c7, c8, c9 = st.columns(3)
                is_material = categoria == "Material"
                with c7: valor_parcela = st.text_input("Valor da parcela", value=val, disabled=is_material)
                with c8: parcela_inicial = st.number_input("Parcela inicial", min_value=1, step=1, value=1, disabled=is_material)
                with c9: numero_pedido = st.text_input("Número do pedido")
                material_parcelado = categoria == "Material" and material_payment in ("Parcelado no Cartao", "Parcelado no Boleto")
                if categoria == "Mensalidade":
                    gerar_12 = st.checkbox("Gerar mensalidades em série", value=True)
                    qtd_meses = st.number_input("Quantidade de parcelas", min_value=1, max_value=24, value=12)
                elif categoria == "Material":
                    gerar_12 = False
                    qtd_meses = st.number_input(
                        "Parcelamento do material (maximo 6x)",
                        min_value=1,
                        max_value=6,
                        value=2 if material_parcelado else 1,
                        disabled=not material_parcelado,
                    )
                else:
                    gerar_12 = False
                    qtd_meses = st.number_input("Quantidade de parcelas", min_value=1, max_value=24, value=1)
                if st.form_submit_button("Lançar"):
                    if not aluno or not val:
                        st.error("Informe aluno e valor.")
                    else:
                        if categoria == "Mensalidade" and gerar_12:
                            for i in range(int(qtd_meses)):
                                data_venc = add_months(venc, i)
                                parcela = f"{parcela_inicial + i}/{qtd_meses}"
                                add_receivable(
                                    aluno,
                                    desc,
                                    val,
                                    data_venc,
                                    cobranca,
                                    categoria,
                                    data_lancamento=data_lanc,
                                    valor_parcela=valor_parcela or val,
                                    parcela=parcela,
                                    numero_pedido=numero_pedido,
                                )
                            st.success("Mensalidades lançadas!")
                        elif categoria == "Material":
                            total_material = parse_money(val)
                            if total_material <= 0:
                                st.error("Informe um valor válido para o material.")
                            else:
                                qtd_material = int(qtd_meses) if material_parcelado else 1
                                valor_parcela_material = total_material / qtd_material
                                for i in range(qtd_material):
                                    data_venc = add_months(venc, i)
                                    parcela = f"{1 + i}/{qtd_material}"
                                    add_receivable(
                                        aluno,
                                        desc or "Material",
                                        val,
                                        data_venc,
                                        cobranca,
                                        categoria,
                                        data_lancamento=data_lanc,
                                        valor_parcela=f"{valor_parcela_material:.2f}".replace(".", ","),
                                        parcela=parcela,
                                        numero_pedido=numero_pedido,
                                    )
                                st.success(f"Material lançado com parcelamento em {qtd_material}x.")
                        else:
                            parcela = f"{parcela_inicial}/{qtd_meses}" if categoria == "Mensalidade" else str(parcela_inicial)
                            add_receivable(
                                aluno,
                                desc,
                                val,
                                venc,
                                cobranca,
                                categoria,
                                data_lancamento=data_lanc,
                                valor_parcela=valor_parcela or val,
                                parcela=parcela,
                                numero_pedido=numero_pedido,
                            )
                            st.success("Lançado!")
            st.markdown("### Recebimentos")
            recebimentos = st.session_state["receivables"]
            c_f1, c_f2, c_f3, c_f4 = st.columns(4)
            with c_f1:
                status_opts = ["Todos"] + sorted({r.get("status", "") for r in recebimentos if r.get("status")})
                status_sel = st.selectbox("Status", status_opts)
            with c_f2:
                cat_opts = ["Todos"] + sorted({r.get("categoria", "") for r in recebimentos if r.get("categoria")})
                cat_sel = st.selectbox("Categoria", cat_opts)
            with c_f3:
                aluno_opts = ["Todos"] + sorted({r.get("aluno", "") for r in recebimentos if r.get("aluno")})
                aluno_sel = st.selectbox("Aluno", aluno_opts)
            with c_f4:
                item_opts = ["Todos"] + sorted({r.get("item_codigo", "") for r in recebimentos if r.get("item_codigo")})
                item_sel = st.selectbox("Item (Código)", item_opts)
            busca = st.text_input("Buscar por descrição")

            recebimentos_filtrados = recebimentos
            if status_sel != "Todos":
                recebimentos_filtrados = [r for r in recebimentos_filtrados if r.get("status") == status_sel]
            if cat_sel != "Todos":
                recebimentos_filtrados = [r for r in recebimentos_filtrados if r.get("categoria") == cat_sel]
            if aluno_sel != "Todos":
                recebimentos_filtrados = [r for r in recebimentos_filtrados if r.get("aluno") == aluno_sel]
            if item_sel != "Todos":
                recebimentos_filtrados = [r for r in recebimentos_filtrados if r.get("item_codigo") == item_sel]
            if busca:
                recebimentos_filtrados = [
                    r for r in recebimentos_filtrados
                    if busca.lower() in str(r.get("descricao", "")).lower()
                ]

            if recebimentos_filtrados:
                df_rec = pd.DataFrame(recebimentos_filtrados)
                col_order = [
                    "data",
                    "aluno",
                    "descricao",
                    "categoria",
                    "item_codigo",
                    "valor_parcela",
                    "parcela",
                    "numero_pedido",
                    "vencimento",
                    "status",
                    "cobranca",
                ]
                df_rec = df_rec[[c for c in col_order if c in df_rec.columns]]
                st.dataframe(df_rec, use_container_width=True)
            else:
                st.info("Nenhum recebimento encontrado.")

            st.markdown("### Lançar Material do Estoque")
            itens_estoque = st.session_state["inventory"]
            if not itens_estoque:
                st.info("Nenhum item de estoque cadastrado.")
            else:
                with st.form("add_rec_stock", clear_on_submit=True):
                    opcoes = [f"{i.get('codigo','')} - {i.get('descricao','')}" for i in itens_estoque]
                    item_sel = st.selectbox("Item", opcoes)
                    modo_destino = st.selectbox("Destino", ["Aluno", "Turma"])
                    aluno_mat = ""
                    turma_mat = ""
                    if modo_destino == "Aluno":
                        aluno_mat = st.selectbox("Aluno", [s["nome"] for s in st.session_state["students"]])
                    else:
                        turma_mat = st.selectbox("Turma", ["Sem Turma"] + class_names())
                    data_lanc = st.date_input("Data do lançamento", value=datetime.date.today(), format="DD/MM/YYYY")
                    venc = st.date_input("Primeiro vencimento", value=datetime.date.today(), format="DD/MM/YYYY", key="venc_mat")
                    material_payment = st.selectbox("Pagamento do Material", material_payment_options(), key="cobranca_mat")
                    material_parcelado = material_payment in ("Parcelado no Cartao", "Parcelado no Boleto")
                    parcelas_material = st.number_input(
                        "Parcelamento do material (maximo 6x)",
                        min_value=1,
                        max_value=6,
                        value=2 if material_parcelado else 1,
                        disabled=not material_parcelado,
                        key="parcelas_mat_fin",
                    )
                    numero_pedido = st.text_input("Número do pedido", key="pedido_mat")
                    if st.form_submit_button("Lançar material"):
                        item_obj = itens_estoque[opcoes.index(item_sel)]
                        preco = parse_money(item_obj.get("preco", 0))
                        parcelas_item = parse_int(item_obj.get("parcelas", 1)) or 1
                        parcelas = min(6, parcelas_item)
                        if material_parcelado:
                            parcelas = int(parcelas_material)
                        else:
                            parcelas = 1
                        cobranca = material_payment
                        descricao = item_obj.get("descricao", "Material")
                        item_codigo = item_obj.get("codigo", "")
                        alunos_destino = []
                        if modo_destino == "Aluno":
                            alunos_destino = [aluno_mat] if aluno_mat else []
                        else:
                            alunos_destino = [
                                s.get("nome") for s in st.session_state["students"]
                                if s.get("turma") == turma_mat
                            ]
                        count = 0
                        for aluno_dest in alunos_destino:
                            for i in range(parcelas):
                                data_venc = add_months(venc, i)
                                parcela = f"{1 + i}/{parcelas}"
                                add_receivable(
                                    aluno_dest,
                                    descricao,
                                    str(preco),
                                    data_venc,
                                    cobranca,
                                    "Material",
                                    data_lancamento=data_lanc,
                                    valor_parcela=str(preco),
                                    parcela=parcela,
                                    numero_pedido=numero_pedido,
                                    item_codigo=item_codigo,
                                )
                                count += 1
                        st.success(f"Material lançado no financeiro! ({count} parcelas)")
                        st.rerun()

            st.markdown("### Baixa de Recebimentos")
            abertos = [r for r in st.session_state["receivables"] if r.get("status") != "Pago"]
            if not abertos:
                st.info("Nenhum recebimento em aberto.")
            else:
                cba1, cba2 = st.columns(2)
                with cba1:
                    alunos = sorted({r.get("aluno", "") for r in abertos if r.get("aluno")})
                    aluno_baixa = st.selectbox("Aluno (baixa automática)", alunos)
                with cba2:
                    modo_baixa = st.selectbox("Tipo de baixa", ["Manual", "Automática"])

                if modo_baixa == "Manual":
                    opcoes = [f"{r.get('codigo','')} | {r.get('aluno','')} | {r.get('descricao','')} | Venc: {r.get('vencimento','')}" for r in abertos]
                    item_sel = st.selectbox("Selecione o lançamento", opcoes)
                    if st.button("Dar baixa manual"):
                        item_obj = abertos[opcoes.index(item_sel)]
                        item_obj["status"] = "Pago"
                        item_obj["baixa_data"] = datetime.date.today().strftime("%d/%m/%Y")
                        item_obj["baixa_tipo"] = "Manual"
                        save_list(RECEIVABLES_FILE, st.session_state["receivables"])
                        st.success("Baixa realizada!")
                        st.rerun()
                else:
                    if st.button("Baixar automaticamente vencidos (Aluno)"):
                        hoje = datetime.date.today()
                        count = 0
                        for r in st.session_state["receivables"]:
                            if r.get("aluno") == aluno_baixa and r.get("status") != "Pago":
                                vencimento = parse_date(r.get("vencimento", ""))
                                if vencimento and vencimento <= hoje:
                                    r["status"] = "Pago"
                                    r["baixa_data"] = hoje.strftime("%d/%m/%Y")
                                    r["baixa_tipo"] = "Automática"
                                    count += 1
                        save_list(RECEIVABLES_FILE, st.session_state["receivables"])
                        st.success(f"Baixa automática realizada: {count} lançamento(s).")
                        st.rerun()
        with tab2:
            with st.form("add_pag"):
                st.markdown("### Lançar Despesa")
                c1, c2 = st.columns(2)
                with c1: desc = st.text_input("Descrição")
                with c2: val = st.text_input("Valor")
                forn = st.text_input("Fornecedor")
                if st.form_submit_button("Lançar"):
                    st.session_state["payables"].append({"descricao": desc, "valor": val, "fornecedor": forn})
                    save_list(PAYABLES_FILE, st.session_state["payables"])
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
                save_list(GRADES_FILE, st.session_state["grades"])
                st.success("Notas aprovadas!")
                st.rerun()
        else:
            st.info("Nenhuma nota pendente.")

    elif menu_coord == "Usuarios":
        st.markdown('<div class="main-header">Controle de Usuários (Login)</div>', unsafe_allow_html=True)
        tab1, tab2 = st.tabs(["Novo Usuário", "Gerenciar / Excluir"])
        with tab1:
            with st.form("new_user", clear_on_submit=True):
                c1, c2, c3 = st.columns(3)
                with c1: u_user = st.text_input("Usuário")
                with c2: u_pass = st.text_input("Senha", type="password")
                with c3: u_role = st.selectbox("Perfil", ["Aluno", "Professor", "Coordenador"])
                if st.form_submit_button("Criar Acesso"):
                    st.session_state["users"].append({"usuario": u_user, "senha": u_pass, "perfil": u_role})
                    save_users(st.session_state["users"])
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
                            if st.form_submit_button("Salvar Alterações"):
                                user_obj["usuario"] = new_user
                                user_obj["senha"] = new_pass
                                user_obj["perfil"] = new_role
                                save_users(st.session_state["users"])
                                st.success("Usuário atualizado!")
                                st.rerun()
                        with c_del:
                            if st.form_submit_button("EXCLUIR USUARIO", type="primary"):
                                if user_obj["usuario"] == "admin": st.error("Não é possível excluir o Admin principal.")
                                else:
                                    st.session_state["users"].remove(user_obj)
                                    save_users(st.session_state["users"])
                                    st.success("Usuário excluído.")
                                    st.rerun()

    elif menu_coord == "Conteudos":
        st.markdown('<div class="main-header">Conteudos</div>', unsafe_allow_html=True)
        tab_msg, tab_hist = st.tabs(["Publicar Mensagem", "Historico"])
        with tab_msg:
            turmas_msg = ["Todas"] + class_names()
            with st.form("coord_publish_message", clear_on_submit=True):
                turma_msg = st.selectbox("Turma de destino", turmas_msg)
                titulo_msg = st.text_input("Titulo da mensagem")
                corpo_msg = st.text_area("Mensagem")
                if st.form_submit_button("Publicar e enviar email"):
                    if not titulo_msg.strip() or not corpo_msg.strip():
                        st.error("Preencha titulo e mensagem.")
                    else:
                        stats = post_message_and_notify(
                            autor=st.session_state.get("user_name", "Coordenacao"),
                            titulo=titulo_msg,
                            mensagem=corpo_msg,
                            turma=turma_msg,
                            origem="Mensagens Coordenacao",
                        )
                        st.success(f"Mensagem publicada. E-mails processados: {stats['enviados']}/{stats['total']}.")
                        st.rerun()
        with tab_hist:
            if not st.session_state["messages"]:
                st.info("Sem mensagens.")
            else:
                for msg in reversed(st.session_state["messages"]):
                    st.markdown(
                        f"""<div style="background:white; padding:16px; border-radius:12px; border:1px solid #e2e8f0; margin-bottom:10px;">
<div style="font-weight:700; color:#1e3a8a;">{msg.get('titulo','Mensagem')}</div>
<div style="font-size:0.85rem; color:#64748b; margin-bottom:8px;">{msg.get('data','')} | {msg.get('autor','')} | Turma: {msg.get('turma','Todas')}</div>
<div>{msg.get('mensagem','')}</div></div>""",
                        unsafe_allow_html=True,
                    )
    elif menu_coord == "Desafios":
        st.markdown('<div class="main-header">Desafios Semanais</div>', unsafe_allow_html=True)
        auto_enabled = str(os.getenv("ACTIVE_AUTO_CHALLENGES", "")).strip().lower() in ("1", "true", "yes", "on")
        if auto_enabled:
            api_key = get_groq_api_key()
            if api_key:
                week_now = current_week_key(datetime.date.today())
                missing = [lv for lv in book_levels() if not get_weekly_challenge(lv, week_now)]
                if missing:
                    with st.spinner(f"Gerando desafios automaticamente para {week_now}..."):
                        autor_auto = st.session_state.get("user_name", "Coordenacao")
                        created = 0
                        for lv in missing:
                            try:
                                gen = generate_weekly_challenge_ai(lv, week_now)
                                upsert_weekly_challenge(
                                    level=lv,
                                    week_key=week_now,
                                    titulo=gen.get("titulo", ""),
                                    descricao=gen.get("descricao", ""),
                                    pontos=int(gen.get("pontos") or 10),
                                    autor=autor_auto,
                                    due_date=None,
                                    rubrica=gen.get("rubrica", ""),
                                    dica=gen.get("dica", ""),
                                )
                                created += 1
                            except Exception:
                                continue
                        if created:
                            st.info(f"Auto-geracao: {created} desafio(s) criados para {week_now}.")
            else:
                st.warning("Auto-geracao ativa (ACTIVE_AUTO_CHALLENGES=1), mas GROQ_API_KEY nao esta configurado.")
        c_pub, c_stats = st.columns([1, 1])

        with c_pub:
            st.markdown("### Publicar / editar")
            nivel = st.selectbox("Nivel (Livro)", book_levels(), key="coord_ch_level")
            base_date = st.date_input(
                "Semana (escolha uma data)",
                value=datetime.date.today(),
                format="DD/MM/YYYY",
                key="coord_ch_date",
            )
            semana = current_week_key(base_date)
            st.caption(f"Chave da semana: {semana}")

            existing = get_weekly_challenge(nivel, semana) or {}
            key_prefix = f"coord_ch_{str(nivel).replace(' ', '_')}_{str(semana).replace('-', '_')}"

            titulo = st.text_input("Titulo", value=str(existing.get("titulo", "")), key=f"{key_prefix}_titulo")
            descricao = st.text_area(
                "Descricao",
                value=str(existing.get("descricao", "")),
                height=160,
                key=f"{key_prefix}_descricao",
            )
            rubrica = st.text_input(
                "Rubrica (como sera avaliado)",
                value=str(existing.get("rubrica", "")),
                key=f"{key_prefix}_rubrica",
            )
            dica = st.text_input(
                "Dica (opcional)",
                value=str(existing.get("dica", "")),
                key=f"{key_prefix}_dica",
            )
            pontos_default = int(existing.get("pontos") or 10)
            pontos = st.number_input(
                "Pontos",
                min_value=0,
                max_value=100,
                value=pontos_default,
                step=1,
                key=f"{key_prefix}_pontos",
            )
            sem_prazo_default = not bool(str(existing.get("due_date", "")).strip())
            sem_prazo = st.checkbox("Sem prazo", value=sem_prazo_default, key=f"{key_prefix}_sem_prazo")
            due_date = None
            if not sem_prazo:
                due_default = parse_date(existing.get("due_date", "")) or (base_date + datetime.timedelta(days=7))
                due_date = st.date_input("Prazo", value=due_default, format="DD/MM/YYYY", key=f"{key_prefix}_due")

            autor = st.session_state.get("user_name", "Coordenacao")
            enviar_email = st.checkbox(
                "Enviar email para alunos deste livro",
                value=False,
                key=f"{key_prefix}_notify_level",
            )

            ai_col1, ai_col2 = st.columns([1, 1])
            if ai_col1.button("Gerar e salvar com IA", key=f"{key_prefix}_gen_ai"):
                api_key = get_groq_api_key()
                if not api_key:
                    st.error("Configure GROQ_API_KEY para gerar desafios com IA.")
                else:
                    try:
                        gen = generate_weekly_challenge_ai(nivel, semana)
                        upsert_weekly_challenge(
                            level=nivel,
                            week_key=semana,
                            titulo=gen.get("titulo", ""),
                            descricao=gen.get("descricao", ""),
                            pontos=int(gen.get("pontos") or 10),
                            autor=autor,
                            due_date=due_date,
                            rubrica=gen.get("rubrica", ""),
                            dica=gen.get("dica", ""),
                        )
                        if enviar_email:
                            assunto = f"[Active] Desafio semanal - {nivel} ({semana})"
                            corpo = (
                                f"Novo desafio semanal publicado.\n"
                                f"Nivel: {nivel}\nSemana: {semana}\n\n"
                                f"{gen.get('titulo','Desafio')}\n\n{gen.get('descricao','')}\n\n"
                                "Acesse o portal do aluno > Desafios para responder e ser avaliado."
                            )
                            stats = email_students_by_level(nivel, assunto, corpo, "Desafios")
                            st.info(f"E-mails processados: {stats['enviados']}/{stats['total']}.")
                        st.success(f"Desafio gerado e salvo para {nivel} - {semana}.")
                        st.rerun()
                    except Exception as exc:
                        st.error(f"Falha ao gerar desafio com IA: {exc}")

            if ai_col2.button("Gerar com IA para todos livros (semana atual)", key=f"{key_prefix}_gen_ai_all"):
                api_key = get_groq_api_key()
                if not api_key:
                    st.error("Configure GROQ_API_KEY para gerar desafios com IA.")
                else:
                    week_now = current_week_key(datetime.date.today())
                    levels = book_levels()
                    created = 0
                    failed = 0
                    for lv in levels:
                        if get_weekly_challenge(lv, week_now):
                            continue
                        try:
                            gen = generate_weekly_challenge_ai(lv, week_now)
                            upsert_weekly_challenge(
                                level=lv,
                                week_key=week_now,
                                titulo=gen.get("titulo", ""),
                                descricao=gen.get("descricao", ""),
                                pontos=int(gen.get("pontos") or 10),
                                autor=autor,
                                due_date=None,
                                rubrica=gen.get("rubrica", ""),
                                dica=gen.get("dica", ""),
                            )
                            created += 1
                        except Exception:
                            failed += 1
                    if created:
                        st.success(f"Gerados {created} desafio(s) para a semana {week_now}.")
                        st.rerun()
                    if not created and not failed:
                        st.info(f"Ja existem desafios publicados para a semana {week_now}.")
            if st.button("Salvar desafio", type="primary", key=f"{key_prefix}_salvar"):
                if not str(titulo).strip() or not str(descricao).strip():
                    st.error("Preencha titulo e descricao.")
                else:
                    upsert_weekly_challenge(
                        level=nivel,
                        week_key=semana,
                        titulo=titulo,
                        descricao=descricao,
                        pontos=int(pontos),
                        autor=autor,
                        due_date=due_date,
                        rubrica=rubrica,
                        dica=dica,
                    )
                    if enviar_email:
                        assunto = f"[Active] Desafio semanal - {nivel} ({semana})"
                        corpo = (
                            f"Novo desafio semanal publicado.\n"
                            f"Nivel: {nivel}\nSemana: {semana}\n\n"
                            f"{titulo}\n\n{descricao}\n\n"
                            "Acesse o portal do aluno > Desafios para responder e ser avaliado."
                        )
                        stats = email_students_by_level(nivel, assunto, corpo, "Desafios")
                        st.info(f"E-mails processados: {stats['enviados']}/{stats['total']}.")
                    st.success(f"Desafio salvo para {nivel} - {semana}.")
                    st.rerun()

            if existing:
                st.caption(f"Criado em: {existing.get('created_at','')} | Atualizado em: {existing.get('updated_at','')}")

        with c_stats:
            st.markdown("### Acompanhamento")
            comps = st.session_state.get("challenge_completions", []) or []
            if not comps:
                st.info("Sem desafios concluidos ainda.")
            else:
                dfc = pd.DataFrame(comps)
                if dfc.empty:
                    st.info("Sem desafios concluidos ainda.")
                else:
                    st.markdown("#### Ranking (pontos)")
                    rank = dfc.groupby("aluno", as_index=False)["pontos"].sum().sort_values("pontos", ascending=False)
                    st.dataframe(rank, use_container_width=True)
                    st.markdown("#### Concluidos (recentes)")
                    recent = dfc.sort_values("done_at", ascending=False).head(50)
                    st.dataframe(recent, use_container_width=True)

        st.markdown("### Desafios publicados")
        chs = list(st.session_state.get("challenges", []) or [])
        if not chs:
            st.info("Nenhum desafio publicado ainda.")
        else:
            df = pd.DataFrame(chs)
            if df.empty:
                st.info("Nenhum desafio publicado ainda.")
            else:
                col_order = [c for c in ["semana", "nivel", "titulo", "pontos", "rubrica", "dica", "autor", "due_date", "created_at", "updated_at", "id"] if c in df.columns]
                if col_order:
                    df = df[col_order]
                if "semana" in df.columns and "nivel" in df.columns:
                    df = df.sort_values(["semana", "nivel"], ascending=[False, True])
                st.dataframe(df, use_container_width=True)

    elif menu_coord == "Backup":
        st.markdown('<div class="main-header">Backup</div>', unsafe_allow_html=True)
        storage_mode = "Banco de Dados (persistente)" if _db_enabled() else "Arquivos locais (pode apagar em hospedagens temporarias)"
        st.write(f"**Armazenamento atual:** {storage_mode}")
        if not _db_enabled():
            st.warning(
                "Se voce usa Streamlit Cloud, os arquivos locais podem ser apagados quando o app reinicia/atualiza. "
                "Para nao perder dados, configure um banco Postgres e defina `ACTIVE_DATABASE_URL` (ou `DATABASE_URL`)."
            )

        datasets = [
            ("users.json", "users", USERS_FILE),
            ("students.json", "students", STUDENTS_FILE),
            ("classes.json", "classes", CLASSES_FILE),
            ("teachers.json", "teachers", TEACHERS_FILE),
            ("agenda.json", "agenda", AGENDA_FILE),
            ("messages.json", "messages", MESSAGES_FILE),
            ("challenges.json", "challenges", CHALLENGES_FILE),
            ("challenge_completions.json", "challenge_completions", CHALLENGE_COMPLETIONS_FILE),
            ("receivables.json", "receivables", RECEIVABLES_FILE),
            ("payables.json", "payables", PAYABLES_FILE),
            ("inventory.json", "inventory", INVENTORY_FILE),
            ("inventory_moves.json", "inventory_moves", INVENTORY_MOVES_FILE),
            ("certificates.json", "certificates", CERTIFICATES_FILE),
            ("books.json", "books", BOOKS_FILE),
            ("materials.json", "materials", MATERIALS_FILE),
            ("material_orders.json", "material_orders", MATERIAL_ORDERS_FILE),
            ("grades.json", "grades", GRADES_FILE),
            ("fee_templates.json", "fee_templates", FEE_TEMPLATES_FILE),
            ("email_log.json", "email_log", EMAIL_LOG_FILE),
        ]

        st.markdown("### Exportar backup")
        snapshot_meta = {
            "generated_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "counts": {name: len(st.session_state.get(key, []) or []) for name, key, _ in datasets if isinstance(st.session_state.get(key, []), list)},
        }
        bio = io.BytesIO()
        with zipfile.ZipFile(bio, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("meta.json", json.dumps(snapshot_meta, ensure_ascii=False, indent=2).encode("utf-8"))
            for file_name, session_key, _ in datasets:
                data = st.session_state.get(session_key, [])
                if session_key == "users":
                    data = st.session_state.get("users", [])
                if not isinstance(data, list):
                    data = []
                zf.writestr(file_name, json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8"))
        st.download_button(
            "Baixar backup (.zip)",
            data=bio.getvalue(),
            file_name=f"active_backup_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.zip",
            mime="application/zip",
        )

        st.markdown("### Restaurar backup")
        up = st.file_uploader("Envie um arquivo .zip gerado pelo backup", type=["zip"])
        confirm = st.checkbox("Confirmo que quero restaurar (isso vai substituir os dados atuais).", value=False)
        if up and confirm and st.button("Restaurar agora", type="primary"):
            try:
                restored_any = False
                with zipfile.ZipFile(up, "r") as zf:
                    names = set(zf.namelist())
                    for file_name, session_key, file_path in datasets:
                        if file_name not in names:
                            continue
                        raw = zf.read(file_name).decode("utf-8", errors="replace")
                        data = json.loads(raw)
                        if not isinstance(data, list):
                            continue
                        if session_key == "users":
                            st.session_state["users"] = data
                            save_users(st.session_state["users"])
                        else:
                            st.session_state[session_key] = data
                            save_list(file_path, data)
                        restored_any = True
                if restored_any:
                    st.success("Backup restaurado com sucesso.")
                    st.rerun()
                else:
                    st.warning("Nenhum dado valido encontrado no backup.")
            except Exception as exc:
                st.error(f"Falha ao restaurar backup: {exc}")

        st.markdown("### Recuperacao rapida (backups locais)")
        st.caption("Tenta recuperar apenas Alunos e Turmas a partir dos ultimos arquivos em `_data_backups` (se existirem no servidor).")
        if st.button("Restaurar ultimo backup local de Alunos e Turmas"):
            restored_students = _load_latest_backup_list(STUDENTS_FILE) or []
            restored_classes = _load_latest_backup_list(CLASSES_FILE) or []
            if restored_students:
                st.session_state["students"] = restored_students
                save_list(STUDENTS_FILE, restored_students)
            if restored_classes:
                st.session_state["classes"] = restored_classes
                save_list(CLASSES_FILE, restored_classes)
            if restored_students or restored_classes:
                st.success("Recuperacao executada. Verifique os dados.")
                st.rerun()
            else:
                st.warning("Nenhum backup local encontrado para Alunos/Turmas.")
    elif menu_coord == "Chatbot IA":
        run_active_chatbot()

