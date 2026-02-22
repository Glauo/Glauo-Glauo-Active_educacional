import base64
import datetime
import io
import json
import os
import re
import smtplib
import shutil
import threading
import time
import uuid
import calendar
import unicodedata
import zipfile
from email.message import EmailMessage
from pathlib import Path
from urllib.parse import parse_qsl, quote, urlencode, urlsplit, urlunsplit
import urllib.error
import urllib.request

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
    page_title="Ativo Sistema Educacional",
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
if "activities" not in st.session_state:
    st.session_state["activities"] = []
if "activity_submissions" not in st.session_state:
    st.session_state["activity_submissions"] = []
if "sales_leads" not in st.session_state:
    st.session_state["sales_leads"] = []
if "sales_agenda" not in st.session_state:
    st.session_state["sales_agenda"] = []
if "sales_payments" not in st.session_state:
    st.session_state["sales_payments"] = []
if "chatbot_log" not in st.session_state:
    st.session_state["chatbot_log"] = []
if "agenda" not in st.session_state:
    st.session_state["agenda"] = []
if "class_sessions" not in st.session_state:
    st.session_state["class_sessions"] = []
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
if "_data_sources" not in st.session_state:
    st.session_state["_data_sources"] = {}
if "_db_last_error" not in st.session_state:
    st.session_state["_db_last_error"] = ""
if "_db_circuit_open_until" not in st.session_state:
    st.session_state["_db_circuit_open_until"] = 0.0
if "_db_cache_loaded" not in st.session_state:
    st.session_state["_db_cache_loaded"] = False
if "_db_cache" not in st.session_state:
    st.session_state["_db_cache"] = {}
if "_persistence_alert" not in st.session_state:
    st.session_state["_persistence_alert"] = ""
if "evo_instances_cache" not in st.session_state:
    st.session_state["evo_instances_cache"] = []
if "evo_instances_cache_error" not in st.session_state:
    st.session_state["evo_instances_cache_error"] = ""
if "wiz_settings" not in st.session_state:
    st.session_state["wiz_settings"] = {}
if "wiz_action_plan" not in st.session_state:
    st.session_state["wiz_action_plan"] = []
if "wiz_last_execution" not in st.session_state:
    st.session_state["wiz_last_execution"] = []
if "_active_users_loaded" not in st.session_state:
    st.session_state["_active_users_loaded"] = False
if "_active_runtime_loaded" not in st.session_state:
    st.session_state["_active_runtime_loaded"] = False

ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "2523"
VENDAS_USERNAME = str(os.getenv("ACTIVE_VENDAS_USERNAME", "vendas")).strip() or "vendas"
VENDAS_PASSWORD = str(os.getenv("ACTIVE_VENDAS_PASSWORD", "2523")).strip() or "2523"
VENDAS_PERSON_NAME = str(os.getenv("ACTIVE_VENDAS_NOME", "VENDAS")).strip() or "VENDAS"
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
CLASS_SESSIONS_FILE = DATA_DIR / "class_sessions.json"
INVENTORY_FILE = DATA_DIR / "inventory.json"
INVENTORY_MOVES_FILE = DATA_DIR / "inventory_moves.json"
CERTIFICATES_FILE = DATA_DIR / "certificates.json"
BOOKS_FILE = DATA_DIR / "books.json"
MATERIAL_ORDERS_FILE = DATA_DIR / "material_orders.json"
CHALLENGES_FILE = DATA_DIR / "challenges.json"
CHALLENGE_COMPLETIONS_FILE = DATA_DIR / "challenge_completions.json"
ACTIVITIES_FILE = DATA_DIR / "activities.json"
ACTIVITY_SUBMISSIONS_FILE = DATA_DIR / "activity_submissions.json"
SALES_LEADS_FILE = DATA_DIR / "sales_leads.json"
SALES_AGENDA_FILE = DATA_DIR / "sales_agenda.json"
SALES_PAYMENTS_FILE = DATA_DIR / "sales_payments.json"
WIZ_SETTINGS_FILE = DATA_DIR / "wiz_settings.json"
BACKUP_META_FILE = DATA_DIR / "backup_meta.json"
WHATSAPP_NUMBER = "5516996043314" 
WAPI_DEFAULT_INSTANCE_ID = "KLL54G-UZDSJ8-IPZG69"
_PLACEHOLDER_CONFIG_TOKENS = {
    "HOST",
    "PORT",
    "PORTA",
    "USER",
    "USERNAME",
    "USUARIO",
    "PASSWORD",
    "SENHA",
    "DATABASE",
    "DB",
    "NOME_BANCO",
    "PGHOST",
    "PGPORT",
    "PGUSER",
    "PGPASSWORD",
    "PGDATABASE",
}

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

def _resolve_config_reference(value, max_depth=4):
    current = str(value or "").strip().strip('"').strip("'")
    if not current:
        return ""
    seen = set()
    for _ in range(max_depth):
        token = ""
        match = re.fullmatch(r"\$\{([A-Za-z_][A-Za-z0-9_]*)\}", current)
        if match:
            token = match.group(1)
        else:
            match = re.fullmatch(r"\$([A-Za-z_][A-Za-z0-9_]*)", current)
            if match:
                token = match.group(1)
            else:
                match = re.fullmatch(r"%([A-Za-z_][A-Za-z0-9_]*)%", current)
                if match:
                    token = match.group(1)
                elif re.fullmatch(r"[A-Z][A-Z0-9_]{1,63}", current):
                    token = current
        if not token or token in seen:
            break
        replacement = str(_get_config_value(token, "") or "").strip().strip('"').strip("'")
        if not replacement or replacement == current:
            break
        seen.add(token)
        current = replacement
    return current

def _resolve_inline_config_refs(value):
    text = str(value or "").strip()
    if not text:
        return ""

    def _replace(match):
        token = match.group(1)
        replacement = _resolve_config_reference(_get_config_value(token, ""))
        return replacement if replacement else match.group(0)

    text = re.sub(r"\$\{([A-Za-z_][A-Za-z0-9_]*)\}", _replace, text)
    text = re.sub(r"%([A-Za-z_][A-Za-z0-9_]*)%", _replace, text)
    return text

def _is_placeholder_config_value(value):
    text = str(value or "").strip().strip('"').strip("'")
    if not text:
        return False
    upper = text.upper()
    if upper in _PLACEHOLDER_CONFIG_TOKENS:
        return True
    if text.startswith("<") and text.endswith(">"):
        return True
    if text.startswith("[") and text.endswith("]"):
        return True
    if "SEU_" in upper or "SUA_" in upper:
        return True
    return False

def _clean_config_value(value):
    cleaned = _resolve_inline_config_refs(_resolve_config_reference(value)).strip().strip('"').strip("'")
    return "" if _is_placeholder_config_value(cleaned) else cleaned

def _resolve_port_value(value):
    candidate = _clean_config_value(value)
    if candidate.isdigit():
        port_num = int(candidate)
        if 1 <= port_num <= 65535:
            return str(port_num)
    return ""

def _pick_db_port(*values):
    for value in values:
        parsed = _resolve_port_value(value)
        if parsed:
            return parsed
    return "5432"

def _configured_db_port():
    return _pick_db_port(
        _get_config_value("PGPORT", ""),
        _get_config_value("POSTGRES_PORT", ""),
        _get_config_value("POSTGRESPORT", ""),
        _get_config_value("DB_PORT", ""),
        _get_config_value("DATABASE_PORT", ""),
        _get_config_value("PORTA", ""),
        _get_config_value("DB_PORTA", ""),
        _get_config_value("DATABASE_PORTA", ""),
    )

def _normalize_db_url(raw_url):
    url = _clean_config_value(raw_url)
    if not url:
        return ""
    # Streamlit secrets may include accidental line breaks/spaces when editing long URLs.
    url = re.sub(r"\s+", "", url)
    if url.startswith("postgres://"):
        url = "postgresql://" + url[len("postgres://"):]

    url = re.sub(
        r"(?P<sep>:)(?P<token>[A-Za-z_][A-Za-z0-9_]{1,63})(?=(?:[/?#]|$))",
        lambda m: f"{m.group('sep')}{_resolve_port_value(m.group('token')) or _configured_db_port()}",
        url,
        count=1,
    )
    url = re.sub(
        r"(?i)(?P<prefix>[?&]port=)(?P<token>[A-Za-z_][A-Za-z0-9_]{1,63})(?=(?:[&#]|$))",
        lambda m: f"{m.group('prefix')}{_resolve_port_value(m.group('token')) or _configured_db_port()}",
        url,
    )
    try:
        parsed = urlsplit(url)
        if _is_placeholder_config_value(parsed.hostname):
            return ""
    except Exception:
        pass
    return url

def _evolution_base_url():
    url = _get_config_value("EVOLUTION_API_URL", "") or _get_config_value("EVOLUTION_URL", "")
    return str(url).strip().rstrip("/")

def _evolution_api_key():
    return (
        _get_config_value("EVOLUTION_API_KEY", "")
        or _get_config_value("EVOLUTION_APIKEY", "")
        or _get_config_value("EVOLUTION_KEY", "")
    )

def _evolution_instance_name():
    return (
        _get_config_value("EVOLUTION_INSTANCE", "")
        or _get_config_value("EVOLUTION_INSTANCE_NAME", "")
        or _get_config_value("EVOLUTION_INSTANCE_ID", "")
    )

def _wapi_base_url():
    return (
        _get_config_value("WAPI_BASE_URL", "")
        or _get_config_value("W_API_URL", "")
        or _get_config_value("WAPI_URL", "")
    ).strip().rstrip("/")

def _wapi_token():
    return (
        _get_config_value("WAPI_TOKEN", "")
        or _get_config_value("W_API_TOKEN", "")
        or _get_config_value("WAPI_API_KEY", "")
    ).strip()

def _wapi_instance_id():
    return (
        _get_config_value("WAPI_INSTANCE_ID", "")
        or _get_config_value("W_API_INSTANCE_ID", "")
        or _get_config_value("WAPI_INSTANCE", "")
        or _get_config_value("W_API_INSTANCE", "")
        or WAPI_DEFAULT_INSTANCE_ID
    ).strip()

def _student_portal_url():
    return (
        _get_config_value("ALUNO_PORTAL_URL", "")
        or _get_config_value("ACTIVE_PORTAL_URL", "")
        or "https://activeducacional.streamlit.app/"
    ).strip()

def _http_request(method, url, headers=None, json_payload=None, timeout=15):
    headers = dict(headers or {})
    data = None
    if json_payload is not None:
        data = json.dumps(json_payload).encode("utf-8")
        headers.setdefault("Content-Type", "application/json")
    req = urllib.request.Request(url, data=data, method=method)
    for k, v in headers.items():
        if v is None:
            continue
        req.add_header(str(k), str(v))
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            ct = resp.headers.get("Content-Type", "") or ""
            body = resp.read() or b""
            return resp.status, ct, body, None
    except urllib.error.HTTPError as e:
        ct = ""
        try:
            ct = e.headers.get("Content-Type", "") if getattr(e, "headers", None) else ""
        except Exception:
            ct = ""
        try:
            body = e.read() or b""
        except Exception:
            body = b""
        return int(getattr(e, "code", 0) or 0), ct, body, str(e)
    except Exception as exc:
        return None, "", b"", str(exc)

def _try_parse_json(content_type, body_bytes):
    if not isinstance(body_bytes, (bytes, bytearray)):
        return None, str(body_bytes)
    text = body_bytes.decode("utf-8", errors="replace")
    ct = str(content_type or "").lower()
    if "application/json" in ct or text.lstrip().startswith("{") or text.lstrip().startswith("["):
        try:
            return json.loads(text), text
        except Exception:
            return None, text
    return None, text

def _sanitize_for_debug(value, max_str=800, max_items=50, depth=3):
    if depth <= 0:
        return "(...)"
    if isinstance(value, dict):
        out = {}
        for i, (k, v) in enumerate(value.items()):
            if i >= max_items:
                out["..."] = f"+{max(0, len(value) - max_items)} more keys"
                break
            out[str(k)] = _sanitize_for_debug(v, max_str=max_str, max_items=max_items, depth=depth - 1)
        return out
    if isinstance(value, list):
        out = []
        for i, item in enumerate(value):
            if i >= max_items:
                out.append(f"... (+{max(0, len(value) - max_items)} more)")
                break
            out.append(_sanitize_for_debug(item, max_str=max_str, max_items=max_items, depth=depth - 1))
        return out
    if isinstance(value, str):
        s = value.strip()
        if len(s) > max_str:
            return s[:max_str] + f"... (len={len(s)})"
        return s
    return value

def _looks_like_base64(value):
    s = str(value or "").strip()
    if not s:
        return False
    if s.startswith("data:image/") and "," in s:
        return True
    if len(s) < 120:
        return False
    return bool(re.fullmatch(r"[A-Za-z0-9+/=\s]+", s))

def _maybe_decode_qr_image_bytes(value):
    s = str(value or "").strip()
    if not s:
        return None
    if s.startswith("data:image/") and "," in s:
        s = s.split(",", 1)[1].strip()
    if not _looks_like_base64(s):
        return None
    try:
        raw = base64.b64decode(s, validate=False)
    except Exception:
        return None
    sniff = raw.lstrip()[:32]
    if raw.startswith(b"\x89PNG\r\n\x1a\n"):
        return raw
    if raw.startswith(b"\xff\xd8\xff"):
        return raw
    if raw.startswith(b"GIF87a") or raw.startswith(b"GIF89a"):
        return raw
    if sniff.startswith(b"<svg") or sniff.startswith(b"<?xml"):
        return raw
    return None

def _extract_qr_candidate(value):
    if isinstance(value, dict):
        # Common keys used by different Evolution API versions.
        for k in ("qrcode", "qrCode", "qr_code", "qrcodeBase64", "base64", "qr", "code"):
            v = value.get(k)
            if isinstance(v, str) and v.strip():
                return v.strip()
        for k in ("data", "result", "instance", "response"):
            if k in value:
                found = _extract_qr_candidate(value.get(k))
                if found:
                    return found
        for v in value.values():
            found = _extract_qr_candidate(v)
            if found:
                return found
        return ""
    if isinstance(value, list):
        for item in value:
            found = _extract_qr_candidate(item)
            if found:
                return found
        return ""
    if isinstance(value, str) and value.strip():
        s = value.strip()
        if s.startswith("data:image/"):
            return s
        if _looks_like_base64(s):
            return s
        return s if len(s) > 50 else ""
    return ""

def _extract_pairing_code(value):
    if isinstance(value, dict):
        for k in ("pairingCode", "pairing_code", "pairingcode"):
            v = value.get(k)
            if isinstance(v, str) and v.strip():
                return v.strip()
        for k in ("data", "result", "instance", "response"):
            if k in value:
                found = _extract_pairing_code(value.get(k))
                if found:
                    return found
        for v in value.values():
            found = _extract_pairing_code(v)
            if found:
                return found
        return ""
    if isinstance(value, list):
        for item in value:
            found = _extract_pairing_code(item)
            if found:
                return found
        return ""
    if isinstance(value, str) and value.strip():
        s = value.strip()
        # Very loose heuristic to catch formatted pairing codes (e.g. "ABCD-EFGH").
        if 6 <= len(s) <= 32 and any(ch.isdigit() for ch in s) and any(ch.isalpha() for ch in s):
            return s
    return ""

def _qr_content_to_png_bytes(content):
    content = str(content or "").strip()
    if not content:
        return None
    try:
        import qrcode  # type: ignore
    except Exception:
        return None
    try:
        img = qrcode.make(content)
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return buf.getvalue()
    except Exception:
        return None

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
    raw_url = _normalize_db_url(
        _get_config_value("ACTIVE_DATABASE_URL", "")
        or _get_config_value("DATABASE_URL", "")
        or _get_config_value("RAILWAY_DATABASE_URL", "")
        or _get_config_value("URL_DO_BANCO_DE_DADOS_ATIVO", "")
        or _get_config_value("URL_BANCO_DADOS_ATIVO", "")
        or _get_config_value("URL_DO_BANCO_DE_DADOS", "")
        or _get_config_value("URL_BANCO_DADOS", "")
        or _get_config_value("POSTGRES_URL", "")
        or _get_config_value("POSTGRESQL_URL", "")
    )
    if not raw_url:
        host = _clean_config_value(
            _get_config_value("PGHOST", "")
            or _get_config_value("POSTGRES_HOST", "")
            or _get_config_value("POSTGRESHOST", "")
            or _get_config_value("DB_HOST", "")
            or _get_config_value("DATABASE_HOST", "")
            or _get_config_value("HOST_BANCO", "")
        )
        port = _configured_db_port()
        user = _clean_config_value(
            _get_config_value("PGUSER", "")
            or _get_config_value("POSTGRES_USER", "")
            or _get_config_value("POSTGRESUSER", "")
            or _get_config_value("DB_USER", "")
            or _get_config_value("DATABASE_USER", "")
            or _get_config_value("USUARIO_BANCO", "")
        )
        password = _clean_config_value(
            _get_config_value("PGPASSWORD", "")
            or _get_config_value("POSTGRES_PASSWORD", "")
            or _get_config_value("POSTGRESPASSWORD", "")
            or _get_config_value("DB_PASSWORD", "")
            or _get_config_value("DATABASE_PASSWORD", "")
            or _get_config_value("SENHA_BANCO", "")
        )
        database = _clean_config_value(
            _get_config_value("PGDATABASE", "")
            or _get_config_value("POSTGRES_DB", "")
            or _get_config_value("POSTGRESDATABASE", "")
            or _get_config_value("DB_NAME", "")
            or _get_config_value("DATABASE_NAME", "")
            or _get_config_value("NOME_BANCO", "")
        )
        if host and user and database:
            user_enc = quote(str(user), safe="")
            pass_enc = quote(str(password), safe="") if password else ""
            auth = f"{user_enc}:{pass_enc}" if pass_enc else user_enc
            raw_url = f"postgresql://{auth}@{host}:{port}/{database}"
            ssl_mode = (
                _get_config_value("PGSSLMODE", "")
                or _get_config_value("DB_SSLMODE", "")
                or _get_config_value("DATABASE_SSLMODE", "")
            )
            if not ssl_mode and str(host).strip() not in ("localhost", "127.0.0.1"):
                ssl_mode = "require"
            if ssl_mode:
                sep = "&" if "?" in raw_url else "?"
                raw_url = f"{raw_url}{sep}sslmode={ssl_mode}"
    return _normalize_db_url(raw_url)

def _db_key_for_path(path):
    return str(getattr(path, "stem", path)).strip()

def _db_legacy_keys_for_path(path):
    out = []
    seen = set()

    def _add(value):
        value = str(value or "").strip()
        if not value or value in seen:
            return
        seen.add(value)
        out.append(value)

    if isinstance(path, Path):
        _add(path.name)
        _add(path.as_posix())
        _add(str(path))
        _add(f"{path.stem}.json")
    else:
        _add(path)
    return out

_DB_UNAVAILABLE = object()
DB_CONNECT_TIMEOUT_SECONDS = 4
DB_FAILURE_COOLDOWN_SECONDS = 25

def _db_circuit_is_open():
    until = float(st.session_state.get("_db_circuit_open_until", 0.0) or 0.0)
    return until > time.time()

def _db_open_circuit(exc):
    st.session_state["_db_circuit_open_until"] = time.time() + float(DB_FAILURE_COOLDOWN_SECONDS)
    st.session_state["_db_last_error"] = str(exc)

def _db_close_circuit():
    st.session_state["_db_circuit_open_until"] = 0.0

def _db_reset_cache():
    st.session_state["_db_cache_loaded"] = False
    st.session_state["_db_cache"] = {}

def _db_enabled():
    return bool(_db_url()) and psycopg2 is not None and not _db_circuit_is_open()

def _db_connect():
    # New connection per operation keeps behavior predictable across Streamlit reruns.
    url = _db_url()
    conn = psycopg2.connect(url, connect_timeout=DB_CONNECT_TIMEOUT_SECONDS)
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

def _db_load_cache():
    if st.session_state.get("_db_cache_loaded", False):
        return True
    try:
        with _db_connect() as conn:
            _db_init(conn)
            with conn.cursor() as cur:
                cur.execute("SELECT key, value FROM active_kv")
                rows = cur.fetchall() or []
        cache = {}
        for row in rows:
            if not isinstance(row, (tuple, list)) or len(row) < 2:
                continue
            cache[str(row[0])] = row[1]
        st.session_state["_db_cache"] = cache
        st.session_state["_db_cache_loaded"] = True
        st.session_state["_db_last_error"] = ""
        _db_close_circuit()
        return True
    except Exception as exc:
        _db_open_circuit(exc)
        _db_reset_cache()
        return False

def _db_get(key):
    if not _db_enabled():
        return _DB_UNAVAILABLE
    if not _db_load_cache():
        return _DB_UNAVAILABLE
    cache = st.session_state.get("_db_cache", {}) or {}
    return cache.get(str(key))

def _db_set(key, value):
    if not _db_enabled():
        return False
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
        st.session_state["_db_last_error"] = ""
        if st.session_state.get("_db_cache_loaded", False):
            cache = st.session_state.get("_db_cache", {}) or {}
            cache[str(key)] = value
            st.session_state["_db_cache"] = cache
        _db_close_circuit()
        return True
    except Exception as exc:
        _db_open_circuit(exc)
        _db_reset_cache()
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

def _load_json_list_file(path, create_if_missing=True):
    with DATA_IO_LOCK:
        if not path.exists():
            if not create_if_missing:
                return None
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
    key = _db_key_for_path(path)
    if _db_enabled():
        data = _db_get(key)
        if data is _DB_UNAVAILABLE:
            # Banco indisponivel: nao cria arquivo vazio automaticamente.
            local_data = _load_json_list_file(path, create_if_missing=False)
            if isinstance(local_data, list) and local_data:
                st.session_state["_data_sources"][key] = "local_fallback_nonempty"
                return local_data
            st.session_state["_data_sources"][key] = "db_unavailable"
            return local_data if isinstance(local_data, list) else []
        if isinstance(data, list):
            st.session_state["_data_sources"][key] = "db"
            return data
        if data is None:
            # Migra automaticamente caso a versão antiga tenha salvo com outra chave.
            for legacy_key in _db_legacy_keys_for_path(path):
                if legacy_key == key:
                    continue
                legacy_data = _db_get(legacy_key)
                if legacy_data is _DB_UNAVAILABLE:
                    local_data = _load_json_list_file(path, create_if_missing=False)
                    st.session_state["_data_sources"][key] = "db_unavailable"
                    return local_data if isinstance(local_data, list) else []
                if isinstance(legacy_data, list):
                    _db_set(key, legacy_data)
                    st.session_state["_data_sources"][key] = "db_legacy_migrated"
                    return legacy_data
            # First run with DB: seed from local file if exists.
            seeded = _load_json_list_file(path)
            if seeded:
                _db_set(key, seeded)
                st.session_state["_data_sources"][key] = "db_seeded_from_file"
            else:
                st.session_state["_data_sources"][key] = "db_empty"
            return seeded
        st.session_state["_data_sources"][key] = "db_invalid"
        return []
    file_data = _load_json_list_file(path)
    st.session_state["_data_sources"][key] = "file"
    return file_data if isinstance(file_data, list) else []

def _save_json_list(path, data):
    key = _db_key_for_path(path)
    safe_data = data if isinstance(data, list) else []
    if _db_enabled():
        source = st.session_state.get("_data_sources", {}).get(key, "")
        if source == "db_unavailable":
            # Evita sobrescrever dados do banco quando a carga inicial nao foi confiavel.
            _save_json_list_file(path, safe_data)
            return False
        ok = _db_set(key, safe_data)
        if ok:
            st.session_state["_data_sources"][key] = "db"
        else:
            st.session_state["_data_sources"][key] = "db_unavailable"
        mirror = os.getenv("ACTIVE_MIRROR_FILES", "0").strip().lower() in ("1", "true", "yes")
        # Se falhar no banco, salva localmente para nao perder alteracoes da sessao.
        if mirror or not ok:
            _save_json_list_file(path, safe_data)
        return ok
    _save_json_list_file(path, safe_data)
    return True

def load_users():
    return _load_json_list(USERS_FILE)

def save_users(users):
    _save_json_list(USERS_FILE, users)

def load_list(path):
    return _load_json_list(path)

def save_list(path, data):
    _save_json_list(path, data)

DEFAULT_WIZ_SETTINGS = {
    "enabled": True,
    "notify_email": True,
    "notify_whatsapp": True,
    "auto_daily_backup": False,
    "on_student_created": True,
    "on_teacher_created": True,
    "on_user_created": True,
    "on_news_posted": True,
    "on_grade_approved": True,
    "on_agenda_created": True,
    "on_class_link_updated": True,
    "on_financial_created": True,
}

def _load_json_dict(path, default_obj=None):
    default_obj = dict(default_obj or {})
    with DATA_IO_LOCK:
        if not path.exists():
            _atomic_write_json(path, default_obj)
            return dict(default_obj)
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            return data if isinstance(data, dict) else dict(default_obj)
        except Exception:
            return dict(default_obj)

def _save_json_dict(path, data):
    if not isinstance(data, dict):
        data = {}
    with DATA_IO_LOCK:
        _atomic_write_json(path, data)

def get_wiz_settings():
    raw = st.session_state.get("wiz_settings") or {}
    out = dict(DEFAULT_WIZ_SETTINGS)
    if isinstance(raw, dict):
        for key in out:
            if key in raw:
                out[key] = bool(raw.get(key))
    return out

def save_wiz_settings(settings):
    merged = dict(DEFAULT_WIZ_SETTINGS)
    if isinstance(settings, dict):
        for key in merged:
            if key in settings:
                merged[key] = bool(settings.get(key))
    st.session_state["wiz_settings"] = merged
    _save_json_dict(WIZ_SETTINGS_FILE, merged)
    return merged

def _backup_datasets():
    return [
        ("users.json", "users", USERS_FILE),
        ("students.json", "students", STUDENTS_FILE),
        ("classes.json", "classes", CLASSES_FILE),
        ("teachers.json", "teachers", TEACHERS_FILE),
        ("agenda.json", "agenda", AGENDA_FILE),
        ("class_sessions.json", "class_sessions", CLASS_SESSIONS_FILE),
        ("messages.json", "messages", MESSAGES_FILE),
        ("challenges.json", "challenges", CHALLENGES_FILE),
        ("challenge_completions.json", "challenge_completions", CHALLENGE_COMPLETIONS_FILE),
        ("activities.json", "activities", ACTIVITIES_FILE),
        ("activity_submissions.json", "activity_submissions", ACTIVITY_SUBMISSIONS_FILE),
        ("sales_leads.json", "sales_leads", SALES_LEADS_FILE),
        ("sales_agenda.json", "sales_agenda", SALES_AGENDA_FILE),
        ("sales_payments.json", "sales_payments", SALES_PAYMENTS_FILE),
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

def _build_backup_zip_bytes():
    datasets = _backup_datasets()
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
    return bio.getvalue(), snapshot_meta

def _run_wiz_daily_backup(force=False):
    settings = get_wiz_settings()
    if not force and not bool(settings.get("auto_daily_backup", False)):
        return False, "backup diario desativado", None

    meta = _load_json_dict(BACKUP_META_FILE, {})
    today = datetime.date.today().isoformat()
    if not force and str(meta.get("last_daily_backup_date", "")) == today:
        return False, "backup diario ja executado hoje", str(meta.get("last_backup_file", ""))

    try:
        payload, snap_meta = _build_backup_zip_bytes()
        stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = BACKUP_DIR / f"active_daily_{stamp}.zip"
        with DATA_IO_LOCK:
            backup_file.write_bytes(payload)
            old = sorted(BACKUP_DIR.glob("active_daily_*.zip"), key=lambda p: p.stat().st_mtime, reverse=True)
            for stale in old[30:]:
                try:
                    stale.unlink(missing_ok=True)
                except Exception:
                    pass
        _save_json_dict(
            BACKUP_META_FILE,
            {
                "last_daily_backup_date": today,
                "last_backup_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "last_backup_file": str(backup_file),
                "counts": snap_meta.get("counts", {}),
            },
        )
        return True, "backup diario criado", str(backup_file)
    except Exception as exc:
        return False, f"falha no backup diario: {exc}", None

def wiz_enabled():
    return bool(get_wiz_settings().get("enabled", True))

def wiz_event_enabled(event_key):
    settings = get_wiz_settings()
    return bool(settings.get("enabled", True)) and bool(settings.get(event_key, False))

def _normalize_whatsapp_number(number_raw):
    digits = re.sub(r"\D+", "", str(number_raw or ""))
    if not digits:
        return ""
    if digits.startswith("00"):
        digits = digits[2:]
    if len(digits) in (10, 11):
        digits = "55" + digits
    return digits

def _student_whatsapp_recipients(student):
    numbers = set()
    if not isinstance(student, dict):
        return []
    student_number = _normalize_whatsapp_number(student.get("celular", ""))
    if student_number:
        numbers.add(student_number)
    resp = student.get("responsavel", {})
    if isinstance(resp, dict):
        resp_number = _normalize_whatsapp_number(resp.get("celular", ""))
        if resp_number:
            numbers.add(resp_number)
    return sorted(numbers)

def _send_whatsapp_evolution(number, text, timeout=20):
    number = _normalize_whatsapp_number(number)
    message_text = str(text or "").strip()
    base_url = _evolution_base_url()
    api_key = _evolution_api_key()
    instance = _evolution_instance_name()
    if not (number and message_text and base_url and instance and api_key):
        return False, "evolution nao configurado", []

    auth_mode = str(_get_config_value("EVOLUTION_AUTH_MODE", "apikey")).strip().lower()
    headers = {"Accept": "application/json", "User-Agent": "Active-Wiz-Automation/1.0"}
    if auth_mode.startswith("authorization"):
        headers["Authorization"] = api_key if api_key.lower().startswith("bearer ") else f"Bearer {api_key}"
    else:
        headers["apikey"] = api_key

    inst = quote(instance, safe="")
    candidates = []
    number_variants = [number, f"{number}@s.whatsapp.net"]
    prefixes = ["", "/api", "/api/v1", "/v1"]
    payload_shapes = []
    for num in number_variants:
        payload_shapes.extend(
            [
                {"number": num, "text": message_text},
                {"number": num, "message": message_text},
                {"number": num, "textMessage": {"text": message_text}},
                {"number": num, "options": {"delay": 1200}, "textMessage": {"text": message_text}},
            ]
        )
    for pfx in prefixes:
        candidates.extend(
            [
                ("POST", f"{pfx}/message/sendText/{inst}"),
                ("POST", f"{pfx}/chat/sendText/{inst}"),
            ]
        )

    attempts = []
    for method, path in candidates:
        for payload in payload_shapes:
            status, ct, body, err = _http_request(
                method,
                base_url.rstrip("/") + path,
                headers=headers,
                json_payload=payload,
                timeout=int(timeout),
            )
            parsed, text_preview = _try_parse_json(ct, body)
            ok = status is not None and 200 <= int(status) < 300
            attempts.append(
                {
                    "path": path,
                    "status": status,
                    "error": err,
                    "payload_keys": sorted(list(payload.keys())),
                    "preview": (text_preview or "")[:200],
                }
            )
            if ok:
                return True, f"enviado (HTTP {status})", attempts
            if isinstance(parsed, dict):
                msg = str(parsed.get("message", "") or parsed.get("error", "")).strip()
                if msg and ("sent" in msg.lower() or "sucesso" in msg.lower() or "success" in msg.lower()):
                    return True, msg, attempts
    last = attempts[-1] if attempts else {}
    return False, f"falha whatsapp (HTTP {last.get('status')})", attempts

def _send_whatsapp_wapi(number, text, timeout=20):
    number = _normalize_whatsapp_number(number)
    message_text = str(text or "").strip()
    base_url = _wapi_base_url()
    token = _wapi_token()
    instance_id = _wapi_instance_id()
    if not (number and message_text and base_url and token and instance_id):
        return False, "wapi nao configurado", []

    split = urlsplit(base_url)
    direct_endpoint = "send-text" in str(split.path or "").lower()
    endpoint_urls = []
    if direct_endpoint:
        qs = dict(parse_qsl(split.query, keep_blank_values=True))
        if "instanceId" not in qs and "instance_id" not in qs:
            qs["instanceId"] = instance_id
        direct_url = urlunsplit((split.scheme, split.netloc, split.path, urlencode(qs), split.fragment))
        endpoint_urls = [direct_url]
    else:
        endpoint_urls = [base_url.rstrip("/") + p for p in [
            "/api/v1/message/send-text",
            "/api/v1/messages/send-text",
            "/message/send-text",
            "/message/sendText",
            f"/api/v1/instances/{quote(instance_id, safe='')}/send-text",
            f"/instance/{quote(instance_id, safe='')}/send-text",
        ]]

    headers_list = [
        {"Authorization": token if token.lower().startswith("bearer ") else f"Bearer {token}"},
        {"apikey": token},
        {"x-api-key": token},
    ]
    payloads = [
        {"instanceId": instance_id, "phone": number, "message": message_text},
        {"instanceId": instance_id, "number": number, "text": message_text},
        {"instance_id": instance_id, "phone": number, "message": message_text},
        {"instance": instance_id, "phone": number, "message": message_text},
    ]

    attempts = []
    for url in endpoint_urls:
        for auth_headers in headers_list:
            headers = {"Accept": "application/json", "User-Agent": "Active-Wiz-Automation/1.0"}
            headers.update(auth_headers)
            for payload in payloads:
                status, ct, body, err = _http_request(
                    "POST",
                    url,
                    headers=headers,
                    json_payload=payload,
                    timeout=int(timeout),
                )
                parsed, text_preview = _try_parse_json(ct, body)
                ok = status is not None and 200 <= int(status) < 300
                attempts.append(
                    {
                        "url": url,
                        "status": status,
                        "error": err,
                        "auth": next(iter(auth_headers.keys())),
                        "payload_keys": sorted(list(payload.keys())),
                        "preview": (text_preview or "")[:200],
                    }
                )
                if ok:
                    return True, f"enviado (HTTP {status})", attempts
                if isinstance(parsed, dict):
                    msg = str(parsed.get("message", "") or parsed.get("error", "")).strip()
                    if msg and ("sent" in msg.lower() or "sucesso" in msg.lower() or "success" in msg.lower()):
                        return True, msg, attempts
    last = attempts[-1] if attempts else {}
    return False, f"falha wapi (HTTP {last.get('status')})", attempts

def _has_wapi_config():
    return bool(_wapi_base_url() and _wapi_token() and _wapi_instance_id())

def _has_evolution_config():
    return bool(_evolution_base_url() and _evolution_api_key() and _evolution_instance_name())

def _send_whatsapp_auto(number, text, timeout=20):
    provider = str(_get_config_value("ACTIVE_WHATSAPP_PROVIDER", "auto")).strip().lower()
    if provider == "wapi":
        return _send_whatsapp_wapi(number, text, timeout=timeout)
    if provider == "evolution":
        return _send_whatsapp_evolution(number, text, timeout=timeout)

    # auto: prioriza W-API se estiver configurado; caso contrario, Evolution.
    if _has_wapi_config():
        ok, status, attempts = _send_whatsapp_wapi(number, text, timeout=timeout)
        if ok:
            return ok, status, attempts
    if _has_evolution_config():
        return _send_whatsapp_evolution(number, text, timeout=timeout)
    if _has_wapi_config():
        return _send_whatsapp_wapi(number, text, timeout=timeout)
    return False, "nenhum provedor whatsapp configurado", []

def _whatsapp_config_diagnostics():
    provider = str(_get_config_value("ACTIVE_WHATSAPP_PROVIDER", "auto")).strip().lower() or "auto"
    diag = {
        "provider": provider,
        "wapi_base_url": bool(_wapi_base_url()),
        "wapi_token": bool(_wapi_token()),
        "wapi_instance_id": _wapi_instance_id() or "",
        "evolution_base_url": bool(_evolution_base_url()),
        "evolution_api_key": bool(_evolution_api_key()),
        "evolution_instance": bool(_evolution_instance_name()),
    }
    diag["wapi_ready"] = _has_wapi_config()
    diag["evolution_ready"] = _has_evolution_config()
    return diag

def _log_comm_event(destinatario, canal, contato, assunto, mensagem, origem, status):
    st.session_state["email_log"].append(
        {
            "destinatario": destinatario,
            "canal": canal,
            "email": contato if canal == "email" else "",
            "whatsapp": contato if canal == "whatsapp" else "",
            "assunto": assunto,
            "mensagem": mensagem,
            "origem": origem,
            "status": status,
            "data": datetime.date.today().strftime("%d/%m/%Y"),
        }
    )
    save_list(EMAIL_LOG_FILE, st.session_state["email_log"])

def _notify_direct_contacts(destinatario, emails, whatsapps, assunto, mensagem, origem):
    settings = get_wiz_settings()
    stats = {"email_total": 0, "email_ok": 0, "whatsapp_total": 0, "whatsapp_ok": 0}
    email_enabled = bool(settings.get("enabled")) and bool(settings.get("notify_email"))
    wa_enabled = bool(settings.get("enabled")) and bool(settings.get("notify_whatsapp"))

    if email_enabled:
        for email in sorted({str(e).strip().lower() for e in emails if str(e).strip()}):
            ok, status = _send_email_smtp(email, assunto, mensagem)
            stats["email_total"] += 1
            if ok:
                stats["email_ok"] += 1
            _log_comm_event(destinatario, "email", email, assunto, mensagem, origem, status)

    if wa_enabled:
        for number in sorted({str(n).strip() for n in whatsapps if str(n).strip()}):
            ok, status, _ = _send_whatsapp_auto(number, f"{assunto}\n\n{mensagem}")
            stats["whatsapp_total"] += 1
            if ok:
                stats["whatsapp_ok"] += 1
            _log_comm_event(destinatario, "whatsapp", number, assunto, mensagem, origem, status)

    return stats

def notify_students_by_turma_multichannel(turma, assunto, corpo, origem):
    total_stats = {"email_total": 0, "email_ok": 0, "whatsapp_total": 0, "whatsapp_ok": 0}
    for student in st.session_state.get("students", []):
        if turma != "Todas" and student.get("turma") != turma:
            continue
        emails = _message_recipients_for_student(student)
        whatsapps = _student_whatsapp_recipients(student)
        stats = _notify_direct_contacts(student.get("nome", "Aluno"), emails, whatsapps, assunto, corpo, origem)
        for key in total_stats:
            total_stats[key] += stats.get(key, 0)
    return total_stats

def notify_students_by_turma_whatsapp(turma, assunto, corpo, origem):
    total = {"whatsapp_total": 0, "whatsapp_ok": 0}
    settings = get_wiz_settings()
    if not (settings.get("enabled") and settings.get("notify_whatsapp")):
        return total
    for student in st.session_state.get("students", []):
        if turma != "Todas" and student.get("turma") != turma:
            continue
        for number in _student_whatsapp_recipients(student):
            ok, status, _ = _send_whatsapp_auto(number, f"{assunto}\n\n{corpo}")
            total["whatsapp_total"] += 1
            if ok:
                total["whatsapp_ok"] += 1
            _log_comm_event(student.get("nome", "Aluno"), "whatsapp", number, assunto, corpo, origem, status)
    return total

def notify_student_financial_event(aluno_nome, itens):
    if not wiz_event_enabled("on_financial_created"):
        return {"email_total": 0, "email_ok": 0, "whatsapp_total": 0, "whatsapp_ok": 0}
    student = next((s for s in st.session_state.get("students", []) if s.get("nome") == aluno_nome), {})
    if not student:
        return {"email_total": 0, "email_ok": 0, "whatsapp_total": 0, "whatsapp_ok": 0}
    lines = []
    for item in itens[:12]:
        lines.append(
            f"- {item.get('descricao','Lancamento')} | Venc: {item.get('vencimento','')} | "
            f"Parcela: {item.get('parcela','')} | Valor: {item.get('valor_parcela', item.get('valor',''))}"
        )
    assunto = "[Active] Novo lançamento financeiro"
    corpo = "Foram lançados novos itens financeiros no seu cadastro.\n\n" + "\n".join(lines)
    return _notify_direct_contacts(
        student.get("nome", "Aluno"),
        _message_recipients_for_student(student),
        _student_whatsapp_recipients(student),
        assunto,
        corpo,
        "Financeiro",
    )

def _extract_first_json(text):
    raw = str(text or "").strip()
    if not raw:
        return {}
    match = re.search(r"\{[\s\S]*\}", raw)
    if not match:
        return {}
    snippet = match.group(0)
    try:
        return json.loads(snippet)
    except Exception:
        return {}

def _wiz_execute_actions(actions):
    reports = []
    for action in actions:
        kind = str((action or {}).get("type", "")).strip().lower()
        data = action.get("data", {}) if isinstance(action, dict) else {}
        try:
            if kind == "cadastrar_aluno":
                nome = str(data.get("nome", "")).strip()
                email = str(data.get("email", "")).strip().lower()
                if not nome or not email:
                    reports.append({"type": kind, "ok": False, "message": "nome e email sao obrigatorios"})
                    continue
                novo = {
                    "nome": nome,
                    "matricula": _next_student_matricula(st.session_state.get("students", [])),
                    "idade": int(data.get("idade") or 18),
                    "genero": str(data.get("genero", data.get("sexo", ""))).strip(),
                    "data_nascimento": str(data.get("data_nascimento", "")),
                    "celular": str(data.get("celular", "")),
                    "email": email,
                    "rg": str(data.get("rg", "")),
                    "cpf": str(data.get("cpf", "")),
                    "cidade_natal": str(data.get("cidade_natal", "")),
                    "pais": str(data.get("pais", "Brasil")),
                    "cep": str(data.get("cep", "")),
                    "cidade": str(data.get("cidade", "")),
                    "bairro": str(data.get("bairro", "")),
                    "rua": str(data.get("rua", "")),
                    "numero": str(data.get("numero", "")),
                    "complemento": str(data.get("complemento", data.get("observacao_endereco", ""))),
                    "turma": str(data.get("turma", "Sem Turma")),
                    "modulo": str(data.get("modulo", "Presencial em Turma")),
                    "livro": str(data.get("livro", "")),
                    "usuario": str(data.get("usuario", "")),
                    "senha": str(data.get("senha", "")),
                    "responsavel": {
                        "nome": str(data.get("responsavel_nome", "")),
                        "cpf": str(data.get("responsavel_cpf", "")),
                        "celular": str(data.get("responsavel_celular", "")),
                        "email": str(data.get("responsavel_email", "")).strip().lower(),
                    },
                }
                st.session_state["students"].append(novo)
                save_list(STUDENTS_FILE, st.session_state["students"])
                reports.append({"type": kind, "ok": True, "message": f"aluno {nome} cadastrado"})
            elif kind == "cadastrar_professor":
                nome = str(data.get("nome", "")).strip()
                if not nome:
                    reports.append({"type": kind, "ok": False, "message": "nome e obrigatorio"})
                    continue
                prof = {
                    "nome": nome,
                    "area": str(data.get("area", "")),
                    "email": str(data.get("email", "")).strip().lower(),
                    "celular": str(data.get("celular", "")),
                    "usuario": str(data.get("usuario", "")).strip(),
                    "senha": str(data.get("senha", "")).strip(),
                }
                st.session_state["teachers"].append(prof)
                save_list(TEACHERS_FILE, st.session_state["teachers"])
                reports.append({"type": kind, "ok": True, "message": f"professor {nome} cadastrado"})
            elif kind == "cadastrar_usuario":
                usuario = str(data.get("usuario", "")).strip()
                senha = str(data.get("senha", "")).strip()
                perfil = str(data.get("perfil", "Coordenador")).strip()
                if not usuario or not senha:
                    reports.append({"type": kind, "ok": False, "message": "usuario e senha sao obrigatorios"})
                    continue
                st.session_state["users"].append(
                    {
                        "usuario": usuario,
                        "senha": senha,
                        "perfil": perfil if perfil in ("Aluno", "Professor", "Coordenador", "Admin") else "Coordenador",
                        "pessoa": str(data.get("pessoa", "")),
                        "email": str(data.get("email", "")).strip().lower(),
                        "celular": str(data.get("celular", "")),
                    }
                )
                save_users(st.session_state["users"])
                reports.append({"type": kind, "ok": True, "message": f"usuario {usuario} criado"})
            elif kind == "agendar_aula":
                turma = str(data.get("turma", "")).strip()
                if not turma:
                    reports.append({"type": kind, "ok": False, "message": "turma e obrigatoria"})
                    continue
                data_txt = str(data.get("data", datetime.date.today().strftime("%d/%m/%Y")))
                hora_txt = str(data.get("hora", "19:00"))
                item = {
                    "turma": turma,
                    "professor": str(data.get("professor", "")),
                    "titulo": str(data.get("titulo", "Aula ao vivo")).strip() or "Aula ao vivo",
                    "descricao": str(data.get("descricao", "")),
                    "data": data_txt,
                    "hora": hora_txt,
                    "link": str(data.get("link", "")),
                    "recorrencia": "",
                }
                item["google_calendar_link"] = build_google_calendar_event_link(item)
                st.session_state["agenda"].append(item)
                save_list(AGENDA_FILE, st.session_state["agenda"])
                reports.append({"type": kind, "ok": True, "message": f"aula agendada para {turma}"})
            elif kind == "atualizar_link_turma":
                turma = str(data.get("turma", "")).strip()
                novo_link = str(data.get("link", "")).strip()
                turma_obj = next((t for t in st.session_state.get("classes", []) if t.get("nome") == turma), None)
                if not turma_obj:
                    reports.append({"type": kind, "ok": False, "message": "turma nao encontrada"})
                    continue
                turma_obj["link_zoom"] = novo_link
                save_list(CLASSES_FILE, st.session_state["classes"])
                reports.append({"type": kind, "ok": True, "message": f"link atualizado para {turma}"})
            elif kind == "publicar_noticia":
                titulo = str(data.get("titulo", "")).strip()
                mensagem = str(data.get("mensagem", "")).strip()
                turma = str(data.get("turma", "Todas")).strip() or "Todas"
                if not titulo or not mensagem:
                    reports.append({"type": kind, "ok": False, "message": "titulo e mensagem sao obrigatorios"})
                    continue
                post_message_and_notify(
                    autor=st.session_state.get("user_name", "Assistente Wiz"),
                    titulo=titulo,
                    mensagem=mensagem,
                    turma=turma,
                    origem="Assistente Wiz",
                )
                reports.append({"type": kind, "ok": True, "message": "noticia publicada"})
            elif kind == "lancar_recebivel":
                aluno = str(data.get("aluno", "")).strip()
                valor = str(data.get("valor", "")).strip()
                descricao = str(data.get("descricao", "Mensalidade")).strip()
                if not aluno or not valor:
                    reports.append({"type": kind, "ok": False, "message": "aluno e valor sao obrigatorios"})
                    continue
                venc = parse_date(str(data.get("vencimento", ""))) or datetime.date.today()
                codigo = add_receivable(
                    aluno=aluno,
                    descricao=descricao,
                    valor=valor,
                    vencimento=venc,
                    cobranca=str(data.get("cobranca", "Boleto")),
                    categoria=str(data.get("categoria", "Mensalidade")),
                    data_lancamento=datetime.date.today(),
                    valor_parcela=str(data.get("valor_parcela", valor)),
                    parcela=str(data.get("parcela", "1/1")),
                    numero_pedido=str(data.get("numero_pedido", "")),
                    categoria_lancamento=str(data.get("categoria_lancamento", data.get("tipo_categoria", "Aluno"))),
                )
                reports.append({"type": kind, "ok": True, "message": f"recebivel lancado ({codigo})"})
            elif kind == "lancar_nota":
                aluno = str(data.get("aluno", "")).strip()
                if not aluno:
                    reports.append({"type": kind, "ok": False, "message": "aluno e obrigatorio"})
                    continue
                st.session_state["grades"].append(
                    {
                        "aluno": aluno,
                        "turma": str(data.get("turma", "")),
                        "disciplina": str(data.get("disciplina", "Ingles")),
                        "avaliacao": str(data.get("avaliacao", "Avaliação")),
                        "nota": str(data.get("nota", "")),
                        "status": str(data.get("status", "Pendente")),
                        "data": datetime.date.today().strftime("%d/%m/%Y"),
                    }
                )
                save_list(GRADES_FILE, st.session_state["grades"])
                reports.append({"type": kind, "ok": True, "message": f"nota lancada para {aluno}"})
            else:
                reports.append({"type": kind, "ok": False, "message": "acao nao suportada"})
        except Exception as exc:
            reports.append({"type": kind, "ok": False, "message": f"falha: {exc}"})
    return reports

def _wiz_attachment_kind(uploaded_file):
    name = str(getattr(uploaded_file, "name", "") or "").lower()
    mime = str(getattr(uploaded_file, "type", "") or "").lower()
    ext = Path(name).suffix.lower()
    if mime.startswith("image/") or ext in (".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp"):
        return "image"
    if ext in (".txt", ".md", ".json", ".log", ".py", ".sql", ".yaml", ".yml", ".ini"):
        return "text"
    if ext == ".csv":
        return "csv"
    if ext in (".xlsx", ".xls"):
        return "sheet"
    if ext == ".pdf":
        return "pdf"
    return "file"

def _wiz_extract_attachment_context(uploaded_files, max_chars=1800):
    summaries = []
    blocks = []
    for up in uploaded_files or []:
        name = str(getattr(up, "name", "arquivo")).strip() or "arquivo"
        kind = _wiz_attachment_kind(up)
        try:
            raw = up.getvalue() if hasattr(up, "getvalue") else b""
        except Exception:
            raw = b""
        size_kb = (len(raw) / 1024.0) if isinstance(raw, (bytes, bytearray)) else 0.0
        summaries.append(f"- {name} ({kind}, {size_kb:.1f} KB)")
        text = ""
        try:
            if kind == "text" and raw:
                text = raw.decode("utf-8", errors="replace")
            elif kind == "csv" and raw:
                try:
                    text = pd.read_csv(io.BytesIO(raw)).head(20).to_csv(index=False)
                except Exception:
                    text = raw.decode("utf-8", errors="replace")
            elif kind == "sheet" and raw:
                text = pd.read_excel(io.BytesIO(raw)).head(20).to_csv(index=False)
            elif kind == "pdf" and raw:
                try:
                    from pypdf import PdfReader
                    reader = PdfReader(io.BytesIO(raw))
                    parts = []
                    for page in reader.pages[:3]:
                        parts.append((page.extract_text() or "").strip())
                    text = "\n".join([p for p in parts if p])
                except Exception:
                    text = ""
        except Exception:
            text = ""
        if text:
            clean = str(text).strip()
            if len(clean) > max_chars:
                clean = clean[:max_chars] + "..."
            blocks.append(f"[{name}]\n{clean}")
    return summaries, blocks

def run_wiz_assistant():
    st.markdown('<div class="main-header">ASSISTENTE WIZ</div>', unsafe_allow_html=True)
    st.caption("Conversa simples com o Wiz para Coordenação/Admin. Anexe arquivo/imagem e escreva seu pedido.")

    account_profile = str(st.session_state.get("account_profile") or st.session_state.get("role") or "")
    if account_profile not in ("Admin", "Coordenador"):
        st.error("Acesso restrito para Coordenador/Admin.")
        return

    chat_key = f"wiz:{(st.session_state.get('user_name') or '').strip().lower()}"
    if chat_key not in st.session_state["active_chat_histories"]:
        st.session_state["active_chat_histories"][chat_key] = []
    chat_history = st.session_state["active_chat_histories"][chat_key]

    st.markdown("### Anexos")
    uploaded_files = st.file_uploader(
        "Anexar arquivo(s) e imagem(ns)",
        accept_multiple_files=True,
        type=["png", "jpg", "jpeg", "webp", "gif", "bmp", "pdf", "txt", "md", "csv", "json", "xlsx", "xls"],
        key="wiz_simple_uploads",
    )

    summaries, content_blocks = _wiz_extract_attachment_context(uploaded_files)
    if uploaded_files:
        with st.expander("Arquivos anexados", expanded=True):
            for up in uploaded_files:
                name = str(getattr(up, "name", "arquivo"))
                kind = _wiz_attachment_kind(up)
                if kind == "image":
                    st.image(up, caption=name, width=240)
                else:
                    st.caption(f"{name} ({kind})")

    st.markdown("### Conversa com o Wiz")
    for msg in chat_history:
        with st.chat_message("assistant" if msg["role"] == "assistant" else "user"):
            st.markdown(msg["content"])

    a1, a2 = st.columns([1, 1])
    if a1.button("Limpar conversa", key="wiz_simple_clear"):
        st.session_state["active_chat_histories"][chat_key] = []
        st.rerun()
    if a2.button("Salvar conversa", key="wiz_simple_save"):
        st.session_state["chatbot_log"].append(
            {
                "data": datetime.datetime.now().strftime("%d/%m/%Y %H:%M"),
                "usuario": st.session_state.get("user_name", ""),
                "perfil": st.session_state.get("account_profile") or st.session_state.get("role", ""),
                "mensagens": chat_history,
                "canal": "Assistente Wiz",
            }
        )
        save_list(CHATBOT_LOG_FILE, st.session_state["chatbot_log"])
        st.success("Conversa salva.")

    user_text = st.chat_input("Digite o que você precisa no sistema (cadastro, agenda, financeiro, comunicados, etc.)")
    if not user_text:
        return

    api_key = get_groq_api_key()
    if not api_key:
        st.error("Configure GROQ_API_KEY para usar o Assistente Wiz.")
        return

    full_user_text = str(user_text or "").strip()
    if summaries:
        full_user_text += "\n\nAnexos recebidos:\n" + "\n".join(summaries)
    if content_blocks:
        full_user_text += "\n\nConteúdo lido dos anexos:\n" + "\n\n".join(content_blocks)

    chat_history.append({"role": "user", "content": str(user_text).strip()})

    system_prompt = "\n".join(
        [
            "Você é o Assistente Wiz da Active Educacional para Coordenador/Admin.",
            "Responda em português do Brasil, de forma simples, direta e útil.",
            "Nunca responda com JSON, código ou estrutura técnica.",
            "Quando o pedido envolver operação interna, devolva: resumo do pedido, passos práticos e dados faltantes.",
            "Se houver anexo, use o conteúdo anexado como base da resposta.",
            "Nunca mencione DietHealth.",
            get_active_context_text(),
        ]
    )

    request_messages = [{"role": "system", "content": system_prompt}]
    request_messages += chat_history[-12:]
    request_messages.append({"role": "user", "content": full_user_text})

    client = OpenAI(api_key=api_key, base_url="https://api.groq.com/openai/v1")
    model_name = os.getenv("ACTIVE_WIZ_MODEL", os.getenv("ACTIVE_CHATBOT_MODEL", "llama-3.3-70b-versatile"))
    with st.spinner("Wiz está pensando..."):
        try:
            result = client.chat.completions.create(
                model=model_name,
                messages=request_messages,
                temperature=0.2,
                max_tokens=1200,
            )
            answer = (result.choices[0].message.content or "").strip()
            if not answer:
                answer = "Não consegui responder agora. Tente novamente com mais detalhes."
        except Exception as exc:
            answer = f"Falha ao consultar IA: {exc}"

    chat_history.append({"role": "assistant", "content": answer})
    st.session_state["active_chat_histories"][chat_key] = chat_history
    st.rerun()

def ensure_admin_user(users):
    if not any(u.get("usuario") == ADMIN_USERNAME for u in users):
        users.append({
            "usuario": ADMIN_USERNAME,
            "senha": ADMIN_PASSWORD,
            "perfil": "Admin",
            "pessoa": "Administrador",
        })

    has_vendas_user = any(
        str(u.get("usuario", "")).strip().lower() == VENDAS_USERNAME.lower()
        for u in users
    )
    if not has_vendas_user:
        users.append({
            "usuario": VENDAS_USERNAME,
            "senha": VENDAS_PASSWORD,
            "perfil": "Comercial",
            "pessoa": VENDAS_PERSON_NAME,
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

WEEKDAY_OPTIONS_PT = [
    "Segunda",
    "Terca",
    "Quarta",
    "Quinta",
    "Sexta",
    "Sabado",
    "Domingo",
]
WEEKDAY_TO_INDEX = {dia: idx for idx, dia in enumerate(WEEKDAY_OPTIONS_PT)}

WEEKDAY_LABELS_BR = [
    "segunda-feira",
    "terca-feira",
    "quarta-feira",
    "quinta-feira",
    "sexta-feira",
    "sabado",
    "domingo",
]


def normalize_text(value):
    text = unicodedata.normalize("NFKD", str(value or ""))
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    return text.lower().strip()


def weekday_index_from_label(label):
    normalized = normalize_text(label).replace("-feira", "").strip()
    aliases = {
        0: ["segunda", "seg", "2"],
        1: ["terca", "ter", "3"],
        2: ["quarta", "qua", "4"],
        3: ["quinta", "qui", "5"],
        4: ["sexta", "sex", "6"],
        5: ["sabado", "sab", "7"],
        6: ["domingo", "dom", "0"],
    }
    for idx, labels in aliases.items():
        if normalized in labels:
            return idx
    return WEEKDAY_TO_INDEX.get(label, None)


def format_date_br(date_value):
    if isinstance(date_value, datetime.date):
        weekday_label = WEEKDAY_LABELS_BR[date_value.weekday()]
        return f"{weekday_label}, {date_value.strftime('%d/%m/%Y')}"
    parsed = parse_date(str(date_value or ""))
    if parsed:
        return format_date_br(parsed)
    return str(date_value or "")

def infer_class_days_from_text(dias_texto):
    texto = normalize_text(dias_texto)
    dias = []
    for dia in WEEKDAY_OPTIONS_PT:
        idx = weekday_index_from_label(dia)
        labels = [dia, WEEKDAY_LABELS_BR[idx], dia[:3]]
        if any(normalize_text(lbl).replace("-feira", "").strip() in texto for lbl in labels):
            dias.append(dia)
    return dias

def format_class_schedule(dias_semana=None, hora_inicio="", hora_fim=""):
    dias_validos = [dia for dia in (dias_semana or []) if dia in WEEKDAY_OPTIONS_PT]
    if not dias_validos:
        return "Horário a definir"
    faixa = ""
    if hora_inicio and hora_fim:
        faixa = f" | {hora_inicio} - {hora_fim}"
    elif hora_inicio:
        faixa = f" | {hora_inicio}"
    elif hora_fim:
        faixa = f" | {hora_fim}"
    return f"{', '.join(dias_validos)}{faixa}"

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

def _parse_float(value, default=0.0):
    try:
        return float(str(value).replace(",", "."))
    except Exception:
        return float(default)

def _is_activity_open(activity_obj):
    status = str((activity_obj or {}).get("status", "Ativa")).strip().lower()
    if not status:
        return True
    return status in ("ativa", "aberta", "open", "publicada")

def _teacher_class_names_for_user(user_name):
    prof_nome = str(user_name or "").strip().lower()
    out = []
    for turma in st.session_state.get("classes", []):
        turma_nome = str(turma.get("nome", "")).strip()
        turma_prof = str(turma.get("professor", "")).strip().lower()
        if turma_nome and turma_prof == prof_nome:
            out.append(turma_nome)
    return out

def _student_class_name(student_name):
    aluno_nome = str(student_name or "").strip()
    aluno_obj = next(
        (s for s in st.session_state.get("students", []) if str(s.get("nome", "")).strip() == aluno_nome),
        {},
    )
    return str(aluno_obj.get("turma", "")).strip()

def _ensure_activity_store_ids():
    changed = False
    for activity in st.session_state.get("activities", []):
        if not isinstance(activity, dict):
            continue
        if not activity.get("id"):
            activity["id"] = uuid.uuid4().hex
            changed = True
        if "status" not in activity or not str(activity.get("status", "")).strip():
            activity["status"] = "Ativa"
            changed = True
        if "allow_resubmission" not in activity:
            activity["allow_resubmission"] = False
            changed = True
        if not isinstance(activity.get("questions"), list):
            activity["questions"] = []
            changed = True
        for question in activity.get("questions", []):
            if not isinstance(question, dict):
                continue
            if not question.get("id"):
                question["id"] = uuid.uuid4().hex
                changed = True
            q_tipo = str(question.get("tipo", "aberta")).strip().lower()
            if q_tipo not in ("multipla_escolha", "aberta"):
                q_tipo = "aberta"
                question["tipo"] = q_tipo
                changed = True
            pontos = parse_int(question.get("pontos", 1))
            if pontos <= 0:
                question["pontos"] = 1
                changed = True
            if q_tipo == "multipla_escolha":
                opcoes_raw = question.get("opcoes", [])
                if not isinstance(opcoes_raw, list):
                    opcoes_raw = [opcoes_raw]
                opcoes = [str(opt).strip() for opt in opcoes_raw if str(opt).strip()]
                if len(opcoes) < 2:
                    opcoes = ["Opcao 1", "Opcao 2"]
                if question.get("opcoes") != opcoes:
                    question["opcoes"] = opcoes
                    changed = True
                correta_idx = question.get("correta_idx", None)
                try:
                    correta_idx = int(correta_idx)
                except Exception:
                    correta_idx = None
                if correta_idx is not None and (correta_idx < 0 or correta_idx >= len(opcoes)):
                    correta_idx = None
                if question.get("correta_idx", None) != correta_idx:
                    question["correta_idx"] = correta_idx
                    changed = True
            else:
                if question.get("opcoes"):
                    question["opcoes"] = []
                    changed = True
                if question.get("correta_idx", None) is not None:
                    question["correta_idx"] = None
                    changed = True
    if changed:
        save_list(ACTIVITIES_FILE, st.session_state.get("activities", []))

def _activity_points_total(activity_obj):
    total = 0
    for question in (activity_obj or {}).get("questions", []):
        if not isinstance(question, dict):
            continue
        pontos = parse_int(question.get("pontos", 1))
        total += pontos if pontos > 0 else 1
    return total

def get_activity_submission(activity_id, aluno_nome):
    aid = str(activity_id or "").strip()
    aluno_nome = str(aluno_nome or "").strip()
    for submission in st.session_state.get("activity_submissions", []):
        if str(submission.get("activity_id", "")).strip() == aid and str(submission.get("aluno", "")).strip() == aluno_nome:
            return submission
    return None

def _score_activity_submission(activity_obj, answers_by_question):
    answers_by_question = answers_by_question if isinstance(answers_by_question, dict) else {}
    respostas = []
    score_auto = 0
    score_total = 0
    needs_manual_review = False

    for idx, question in enumerate((activity_obj or {}).get("questions", []), start=1):
        if not isinstance(question, dict):
            continue
        qid = str(question.get("id", "")).strip() or f"q_{idx}"
        q_tipo = str(question.get("tipo", "aberta")).strip().lower()
        enunciado = str(question.get("enunciado", "")).strip()
        pontos = parse_int(question.get("pontos", 1))
        pontos = pontos if pontos > 0 else 1
        score_total += pontos

        answer_payload = answers_by_question.get(qid, {})
        if q_tipo == "multipla_escolha":
            opcoes = question.get("opcoes", [])
            if not isinstance(opcoes, list):
                opcoes = []
            opcoes = [str(opt).strip() for opt in opcoes if str(opt).strip()]
            selected_idx = answer_payload.get("indice") if isinstance(answer_payload, dict) else answer_payload
            try:
                selected_idx = int(selected_idx)
            except Exception:
                selected_idx = None
            selected_text = opcoes[selected_idx] if selected_idx is not None and 0 <= selected_idx < len(opcoes) else ""
            correta_idx = question.get("correta_idx", None)
            try:
                correta_idx = int(correta_idx)
            except Exception:
                correta_idx = None

            is_correct = None
            pontos_obtidos = 0
            if correta_idx is None:
                needs_manual_review = True
            elif selected_idx is not None and selected_idx == correta_idx:
                is_correct = True
                pontos_obtidos = pontos
            else:
                is_correct = False
            score_auto += pontos_obtidos
            respostas.append(
                {
                    "question_id": qid,
                    "tipo": "multipla_escolha",
                    "enunciado": enunciado,
                    "opcoes": opcoes,
                    "resposta_indice": selected_idx,
                    "resposta_texto": selected_text,
                    "correta_idx": correta_idx,
                    "correta_texto": opcoes[correta_idx] if correta_idx is not None and 0 <= correta_idx < len(opcoes) else "",
                    "acertou": is_correct,
                    "pontos": pontos,
                    "pontos_obtidos": pontos_obtidos,
                }
            )
        else:
            resposta_texto = answer_payload.get("texto") if isinstance(answer_payload, dict) else answer_payload
            resposta_texto = str(resposta_texto or "").strip()
            needs_manual_review = True
            respostas.append(
                {
                    "question_id": qid,
                    "tipo": "aberta",
                    "enunciado": enunciado,
                    "resposta_texto": resposta_texto,
                    "pontos": pontos,
                    "pontos_obtidos": 0,
                }
            )

    return {
        "respostas": respostas,
        "score_auto": int(score_auto),
        "score_total": int(score_total),
        "needs_manual_review": bool(needs_manual_review),
    }

def upsert_activity_submission(activity_obj, aluno_nome, turma_nome, answers_by_question):
    if not isinstance(activity_obj, dict):
        return False, "Atividade invalida."
    activity_id = str(activity_obj.get("id", "")).strip()
    if not activity_id:
        return False, "Atividade sem ID."
    aluno_nome = str(aluno_nome or "").strip()
    if not aluno_nome:
        return False, "Aluno invalido."
    turma_nome = str(turma_nome or "").strip()
    scoring = _score_activity_submission(activity_obj, answers_by_question)
    now = datetime.datetime.now().strftime("%d/%m/%Y %H:%M")
    existing = get_activity_submission(activity_id, aluno_nome)

    status = "Enviada" if scoring.get("needs_manual_review") else "Corrigida automaticamente"
    record = existing if existing else {"id": uuid.uuid4().hex}
    record.update(
        {
            "activity_id": activity_id,
            "atividade_titulo": str(activity_obj.get("titulo", "")).strip(),
            "atividade_tipo": str(activity_obj.get("tipo", "")).strip(),
            "aluno": aluno_nome,
            "turma": turma_nome,
            "respostas": scoring.get("respostas", []),
            "score_auto": int(scoring.get("score_auto", 0) or 0),
            "score_total": int(scoring.get("score_total", 0) or 0),
            "status": status,
            "submitted_at": now,
        }
    )
    if existing:
        record["updated_at"] = now
        # Em caso de reenvio, limpa avaliacao anterior para evitar inconsistencias.
        record["score_professor"] = None
        record["feedback_professor"] = ""
        record["avaliado_em"] = ""
    else:
        st.session_state["activity_submissions"].append(record)
    save_list(ACTIVITY_SUBMISSIONS_FILE, st.session_state["activity_submissions"])
    return True, "Resposta enviada."

def activity_submission_final_score(submission_obj):
    if not isinstance(submission_obj, dict):
        return 0.0
    score_prof = submission_obj.get("score_professor", None)
    if score_prof is not None and str(score_prof).strip() != "":
        return _parse_float(score_prof, default=0.0)
    return _parse_float(submission_obj.get("score_auto", 0), default=0.0)

def sales_lead_status_options():
    return [
        "Novo contato",
        "Leads frios",
        "Leads quentes",
        "Evoluindo",
        "Fechado",
        "Desistir",
        "Indicacao de alunos",
    ]

def sales_agenda_type_options():
    return [
        "Ligacao a fazer",
        "Ligacao feita",
        "Agendamento de visita",
        "Aula experimental",
        "Aula de nivelamento",
    ]

def sales_payment_method_options():
    return ["Pix", "Dinheiro", "Cartao", "Boleto", "Transferencia"]

def _ensure_sales_store_defaults():
    leads_changed = False
    agenda_changed = False
    payments_changed = False

    for lead in st.session_state.get("sales_leads", []):
        if not isinstance(lead, dict):
            continue
        if not lead.get("id"):
            lead["id"] = uuid.uuid4().hex
            leads_changed = True
        if "status" not in lead or not str(lead.get("status", "")).strip():
            lead["status"] = "Novo contato"
            leads_changed = True
        if "created_at" not in lead:
            lead["created_at"] = datetime.datetime.now().strftime("%d/%m/%Y %H:%M")
            leads_changed = True
        if "updated_at" not in lead:
            lead["updated_at"] = ""
            leads_changed = True

    for item in st.session_state.get("sales_agenda", []):
        if not isinstance(item, dict):
            continue
        if not item.get("id"):
            item["id"] = uuid.uuid4().hex
            agenda_changed = True
        if "status" not in item or not str(item.get("status", "")).strip():
            item["status"] = "Agendado"
            agenda_changed = True
        if "whatsapp_sent" not in item:
            item["whatsapp_sent"] = False
            agenda_changed = True
        if "whatsapp_status" not in item:
            item["whatsapp_status"] = ""
            agenda_changed = True
        if "created_at" not in item:
            item["created_at"] = datetime.datetime.now().strftime("%d/%m/%Y %H:%M")
            agenda_changed = True

    for payment in st.session_state.get("sales_payments", []):
        if not isinstance(payment, dict):
            continue
        if not payment.get("id"):
            payment["id"] = uuid.uuid4().hex
            payments_changed = True
        if "status" not in payment or not str(payment.get("status", "")).strip():
            payment["status"] = "Pendente"
            payments_changed = True
        if "receivable_code" not in payment:
            payment["receivable_code"] = ""
            payments_changed = True
        if "comprovante_nome" not in payment:
            payment["comprovante_nome"] = ""
            payments_changed = True
        if "comprovante_mime" not in payment:
            payment["comprovante_mime"] = ""
            payments_changed = True
        if "comprovante_b64" not in payment:
            payment["comprovante_b64"] = ""
            payments_changed = True
        if "recibo_numero" not in payment or not str(payment.get("recibo_numero", "")).strip():
            payment["recibo_numero"] = f"REC-{datetime.datetime.now().strftime('%Y%m%d')}-{str(payment.get('id', ''))[:6].upper()}"
            payments_changed = True
        if "created_at" not in payment:
            payment["created_at"] = datetime.datetime.now().strftime("%d/%m/%Y %H:%M")
            payments_changed = True
        if "updated_at" not in payment:
            payment["updated_at"] = ""
            payments_changed = True

    if leads_changed:
        save_list(SALES_LEADS_FILE, st.session_state.get("sales_leads", []))
    if agenda_changed:
        save_list(SALES_AGENDA_FILE, st.session_state.get("sales_agenda", []))
    if payments_changed:
        save_list(SALES_PAYMENTS_FILE, st.session_state.get("sales_payments", []))

def _sales_receipt_html(payment_obj):
    payment_obj = payment_obj if isinstance(payment_obj, dict) else {}
    aluno = str(payment_obj.get("aluno", "")).strip() or "Aluno"
    telefone = str(payment_obj.get("telefone", "")).strip()
    vendedor = str(payment_obj.get("vendedor", "")).strip() or "Comercial"
    valor_txt = str(payment_obj.get("valor", "")).strip() or "0,00"
    forma = str(payment_obj.get("forma_pagamento", "")).strip() or "Nao informado"
    data_pag = str(payment_obj.get("data_pagamento", "")).strip() or datetime.date.today().strftime("%d/%m/%Y")
    recibo = str(payment_obj.get("recibo_numero", "")).strip() or f"REC-{datetime.datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"
    observacao = str(payment_obj.get("observacao", "")).strip()
    comprovante_nome = str(payment_obj.get("comprovante_nome", "")).strip()
    return f"""
<!DOCTYPE html>
<html lang="pt-br">
<head>
  <meta charset="UTF-8" />
  <title>Recibo de Matricula</title>
  <style>
    body {{ font-family: Arial, sans-serif; background: #f5f7fb; padding: 24px; }}
    .card {{ max-width: 780px; margin: 0 auto; background: #fff; border: 1px solid #dbe7f6; border-radius: 14px; padding: 26px; }}
    .title {{ font-size: 24px; font-weight: 700; color: #1e3a8a; margin-bottom: 6px; }}
    .sub {{ color: #64748b; margin-bottom: 22px; }}
    .row {{ margin: 8px 0; color: #0f172a; }}
    .lbl {{ color: #64748b; font-size: 13px; text-transform: uppercase; letter-spacing: 0.08em; }}
    .footer {{ margin-top: 30px; font-size: 12px; color: #64748b; }}
  </style>
</head>
<body>
  <div class="card">
    <div class="title">Recibo de Matricula</div>
    <div class="sub">Ativo Sistema Educacional</div>
    <div class="row"><span class="lbl">Recibo:</span> {recibo}</div>
    <div class="row"><span class="lbl">Data do pagamento:</span> {data_pag}</div>
    <div class="row"><span class="lbl">Aluno:</span> {aluno}</div>
    <div class="row"><span class="lbl">Telefone:</span> {telefone or "-"}</div>
    <div class="row"><span class="lbl">Valor recebido:</span> R$ {valor_txt}</div>
    <div class="row"><span class="lbl">Forma de pagamento:</span> {forma}</div>
    <div class="row"><span class="lbl">Vendedor:</span> {vendedor}</div>
    <div class="row"><span class="lbl">Comprovante:</span> {comprovante_nome or "Nao anexado"}</div>
    <div class="row"><span class="lbl">Observacoes:</span> {observacao or "-"}</div>
    <div class="footer">Este recibo registra o pagamento informado pelo Comercial e esta sujeito a aprovacao da Coordenacao.</div>
  </div>
</body>
</html>
""".strip()

def _decode_sales_attachment(payment_obj):
    payload = str((payment_obj or {}).get("comprovante_b64", "")).strip()
    if not payload:
        return b""
    try:
        return base64.b64decode(payload)
    except Exception:
        return b""

def _approve_sales_payment(payment_obj, approver_name):
    if not isinstance(payment_obj, dict):
        return False, "Registro invalido."
    if str(payment_obj.get("status", "")).strip().lower() == "aprovado" and str(payment_obj.get("receivable_code", "")).strip():
        return True, "Pagamento ja estava aprovado."

    aluno = str(payment_obj.get("aluno", "")).strip()
    if not aluno:
        return False, "Pagamento sem aluno."
    valor_txt = str(payment_obj.get("valor", "")).strip()
    valor_num = parse_money(valor_txt)
    if valor_num <= 0:
        return False, "Valor invalido para aprovar."
    data_pag = parse_date(payment_obj.get("data_pagamento", "")) or datetime.date.today()
    cobranca = str(payment_obj.get("forma_pagamento", "Pix")).strip() or "Pix"
    descricao = str(payment_obj.get("descricao", "")).strip() or "Taxa de Matricula (Comercial)"

    receivable_code = str(payment_obj.get("receivable_code", "")).strip()
    if not receivable_code:
        receivable_code = add_receivable(
            aluno=aluno,
            descricao=descricao,
            valor=valor_txt,
            vencimento=data_pag,
            cobranca=cobranca,
            categoria="Taxa de Matricula",
            data_lancamento=data_pag,
            valor_parcela=valor_txt,
            parcela="1",
            categoria_lancamento="Aluno",
        )
        payment_obj["receivable_code"] = receivable_code

    rec_obj = next(
        (r for r in st.session_state.get("receivables", []) if str(r.get("codigo", "")).strip() == receivable_code),
        None,
    )
    if rec_obj:
        rec_obj["status"] = "Pago"
        rec_obj["baixa_data"] = data_pag.strftime("%d/%m/%Y")
        rec_obj["baixa_tipo"] = "Comercial aprovado"
        rec_obj["comercial_payment_id"] = str(payment_obj.get("id", "")).strip()
        rec_obj["descricao"] = descricao
        rec_obj["categoria"] = "Taxa de Matricula"
        rec_obj["cobranca"] = cobranca
        rec_obj["valor"] = valor_txt
        rec_obj["valor_parcela"] = valor_txt
        rec_obj["vencimento"] = data_pag.strftime("%d/%m/%Y")
        save_list(RECEIVABLES_FILE, st.session_state.get("receivables", []))

    payment_obj["status"] = "Aprovado"
    payment_obj["aprovado_por"] = str(approver_name or "").strip()
    payment_obj["aprovado_em"] = datetime.datetime.now().strftime("%d/%m/%Y %H:%M")
    payment_obj["reprovado_motivo"] = ""
    payment_obj["updated_at"] = datetime.datetime.now().strftime("%d/%m/%Y %H:%M")
    save_list(SALES_PAYMENTS_FILE, st.session_state.get("sales_payments", []))
    return True, "Pagamento aprovado e registrado no financeiro geral."

def _reject_sales_payment(payment_obj, approver_name, motivo):
    if not isinstance(payment_obj, dict):
        return False, "Registro invalido."
    payment_obj["status"] = "Reprovado"
    payment_obj["aprovado_por"] = str(approver_name or "").strip()
    payment_obj["aprovado_em"] = datetime.datetime.now().strftime("%d/%m/%Y %H:%M")
    payment_obj["reprovado_motivo"] = str(motivo or "").strip()
    payment_obj["updated_at"] = datetime.datetime.now().strftime("%d/%m/%Y %H:%M")
    save_list(SALES_PAYMENTS_FILE, st.session_state.get("sales_payments", []))
    return True, "Pagamento reprovado."

def _lead_phone_for_whatsapp(lead_obj):
    if not isinstance(lead_obj, dict):
        return ""
    number = _normalize_whatsapp_number(lead_obj.get("telefone", ""))
    if number:
        return number
    return _normalize_whatsapp_number(lead_obj.get("celular", ""))

def _student_phone(student_obj):
    if not isinstance(student_obj, dict):
        return ""
    phone = str(student_obj.get("celular", "")).strip()
    if phone:
        return phone
    resp = student_obj.get("responsavel", {})
    if isinstance(resp, dict):
        return str(resp.get("celular", "")).strip()
    return ""

def _send_sales_schedule_whatsapp(lead_obj, schedule_obj):
    lead_obj = lead_obj if isinstance(lead_obj, dict) else {}
    schedule_obj = schedule_obj if isinstance(schedule_obj, dict) else {}
    number = _lead_phone_for_whatsapp(lead_obj)
    if not number:
        return False, 0, []
    nome = str(lead_obj.get("nome", "")).strip() or "Lead"
    tipo = str(schedule_obj.get("tipo", "Agendamento")).strip()
    data = str(schedule_obj.get("data", "")).strip()
    hora = str(schedule_obj.get("hora", "")).strip()
    detalhes = str(schedule_obj.get("detalhes", "")).strip()
    mensagem = (
        f"Ola, {nome}.\n"
        f"Seu agendamento foi registrado no Active.\n"
        f"Tipo: {tipo}\n"
        f"Data: {data}\n"
        f"Horario: {hora or '-'}\n"
    )
    if detalhes:
        mensagem += f"Detalhes: {detalhes}\n"
    mensagem += "\nQualquer ajuste, responda esta mensagem."
    return _send_whatsapp_auto(number, mensagem)

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
        data_br = format_date_br(a.get("data", ""))
        st.write(f"Data: {data_br} | Horario: {a.get('hora', '')}")
        if a.get("recorrencia"):
            st.caption(f"Recorrencia: {a.get('recorrencia')}")
        if a.get("descricao"):
            st.write(a.get("descricao"))
        if a.get("link"):
            st.link_button("Entrar na aula", a.get("link"))
        google_url = a.get("google_calendar_link") or build_google_calendar_event_link(a)
        if google_url:
            st.link_button("Adicionar no Google Agenda", google_url)
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
            c1.link_button("Baixar livro", url)
        else:
            c1.button("Baixar livro", disabled=True, key=f"{key_prefix}_disabled_{idx}")

        if url:
            c2.link_button("Abrir livro", url)
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

def add_receivable(aluno, descricao, valor, vencimento, cobranca, categoria, data_lancamento=None, valor_parcela=None, parcela=None, numero_pedido="", item_codigo="", categoria_lancamento="Aluno"):
    prefix = re.sub(r"[^A-Z0-9]+", "", str(cobranca).upper()) or "REC"
    codigo = f"{prefix}-{uuid.uuid4().hex[:8].upper()}"
    st.session_state["receivables"].append({
        "descricao": descricao.strip() or "Mensalidade",
        "aluno": aluno.strip(),
        "categoria": categoria,
        "categoria_lancamento": str(categoria_lancamento).strip() or "Aluno",
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
    if profile == "Comercial": return ["Comercial"]
    if profile == "Coordenador": return ["Aluno", "Professor", "Comercial", "Coordenador"]
    if profile == "Admin": return ["Aluno", "Professor", "Comercial", "Coordenador"]
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
    stats = {"email_total": 0, "email_ok": 0, "whatsapp_total": 0, "whatsapp_ok": 0}
    for student in st.session_state.get("students", []):
        if turma != "Todas" and student.get("turma") != turma:
            continue
        partial = _notify_direct_contacts(
            student.get("nome", "Aluno"),
            _message_recipients_for_student(student),
            _student_whatsapp_recipients(student),
            assunto,
            corpo,
            origem,
        )
        for key in stats:
            stats[key] += int(partial.get(key, 0))
    # Compatibilidade com trechos legados que usam total/enviados para e-mail.
    stats["total"] = stats["email_total"]
    stats["enviados"] = stats["email_ok"]
    return stats

def email_students_by_level(level, assunto, corpo, origem):
    level = _norm_book_level(level)
    stats = {"email_total": 0, "email_ok": 0, "whatsapp_total": 0, "whatsapp_ok": 0}
    for student in st.session_state.get("students", []):
        if student_book_level(student) != level:
            continue
        partial = _notify_direct_contacts(
            student.get("nome", "Aluno"),
            _message_recipients_for_student(student),
            _student_whatsapp_recipients(student),
            assunto,
            corpo,
            origem,
        )
        for key in stats:
            stats[key] += int(partial.get(key, 0))
    stats["total"] = stats["email_total"]
    stats["enviados"] = stats["email_ok"]
    return stats

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
    "genero",
    "rg",
    "cpf",
    "cidade",
    "bairro",
    "cidade_natal",
    "pais",
    "cep",
    "rua",
    "numero",
    "complemento",
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
        "genero": "genero",
        "sexo": "genero",
        "rg": "rg",
        "cpf": "cpf",
        "cidade": "cidade",
        "bairro": "bairro",
        "cidade_natal": "cidade_natal",
        "pais": "pais",
        "cep": "cep",
        "rua": "rua",
        "numero": "numero",
        "complemento": "complemento",
        "observacao_endereco": "complemento",
        "apto": "complemento",
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
        "genero": _safe_str(row.get("genero")) or _safe_str(row.get("sexo")),
        "rg": _safe_str(row.get("rg")),
        "cpf": _safe_str(row.get("cpf")),
        "cidade": _safe_str(row.get("cidade")),
        "bairro": _safe_str(row.get("bairro")),
        "cidade_natal": _safe_str(row.get("cidade_natal")),
        "pais": _safe_str(row.get("pais")),
        "cep": _safe_str(row.get("cep")),
        "rua": _safe_str(row.get("rua")),
        "numero": _safe_str(row.get("numero")),
        "complemento": _safe_str(row.get("complemento")) or _safe_str(row.get("observacao_endereco")) or _safe_str(row.get("apto")),
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

def student_wiz_context(student_name):
    aluno = next(
        (s for s in st.session_state.get("students", []) if str(s.get("nome", "")).strip() == str(student_name or "").strip()),
        {},
    )
    turma = str(aluno.get("turma", "Sem Turma")).strip() or "Sem Turma"
    livro = student_book_level(aluno) or "Livro 1"

    sess = [
        s for s in st.session_state.get("class_sessions", [])
        if str(s.get("turma", "")).strip() == turma and str(s.get("status", "")).strip().lower() == "finalizada"
    ]
    sess = sorted(
        sess,
        key=lambda x: (
            parse_date(x.get("data", "")) or datetime.date(1900, 1, 1),
            parse_time(x.get("hora_inicio_real", x.get("hora_inicio_prevista", "00:00"))),
        ),
        reverse=True,
    )[:8]

    licoes = []
    for s in sess:
        texto = str(s.get("licao", "")).strip() or str(s.get("resumo_final", "")).strip()
        if texto:
            licoes.append(texto)

    materiais = [
        m for m in st.session_state.get("materials", [])
        if str(m.get("turma", "")).strip() in ("", "Todas", turma)
    ]
    materiais = sorted(materiais, key=lambda x: str(x.get("data", "")), reverse=True)[:8]
    materiais_titulos = [str(m.get("titulo", "")).strip() for m in materiais if str(m.get("titulo", "")).strip()]

    return {
        "turma": turma,
        "livro": livro,
        "licoes": licoes,
        "materiais": materiais_titulos,
    }


def get_tutor_wiz_prompt(contexto_aluno=None):
    contexto_aluno = contexto_aluno or {}
    livro = str(contexto_aluno.get("livro", "Livro 1")).strip() or "Livro 1"
    turma = str(contexto_aluno.get("turma", "Sem Turma")).strip() or "Sem Turma"
    licoes = contexto_aluno.get("licoes", [])[:5]
    materiais = contexto_aluno.get("materiais", [])[:5]

    base = [
        "Voce e o Professor Wiz (IA) da escola de ingles Mister Wiz.",
        "Atenda somente conteudos de ingles.",
        "Ensine baseado no nivel do livro do aluno e no conteudo da turma.",
        "Se o aluno pedir algo fora de ingles, recuse com educacao e redirecione para ingles.",
        "Responda em portugues do Brasil com exemplos em ingles quando necessario.",
        f"Livro atual do aluno: {livro}.",
        f"Turma atual do aluno: {turma}.",
    ]
    if licoes:
        base.append("Licoes recentes da turma: " + "; ".join(licoes))
    if materiais:
        base.append("Materiais recentes da turma: " + "; ".join(materiais))
    base.append("Sempre proponha explicacao curta + exercicio pratico + correcao guiada.")
    return "\n".join(base)


def run_active_chatbot():
    st.markdown('<div class="main-header">Professor Wiz</div>', unsafe_allow_html=True)
    st.caption("Assistente dedicado ao contexto da Active Educacional e Mister Wiz.")

    api_key = get_groq_api_key()
    if not api_key:
        st.error("Configure GROQ_API_KEY em secrets ou variavel de ambiente para usar o chatbot.")
        return

    role = st.session_state.get("role", "")
    include_context = True
    mode = "Pedagogico"
    chat_key = get_active_chat_history_key()

    if role == "Aluno":
        mode = "Pedagogico"
        chat_key = f"tutor:{chat_key}"
        st.caption("Modo automatico do aluno: estudo de ingles por livro, licao e materiais da turma.")
    elif role == "Professor":
        mode = "Pedagogico"
        chat_key = f"prof:{chat_key}"
        st.caption("Modo automatico do professor: apoio pedagogico para aula e avaliacao.")
        c_prof_ctx, c_prof_temp = st.columns(2)
        with c_prof_ctx:
            include_context = st.checkbox("Usar contexto do sistema", value=True, key="prof_wiz_context")
        with c_prof_temp:
            st.session_state["active_chat_temp"] = st.slider(
                "Criatividade", min_value=0.0, max_value=1.0, value=float(st.session_state["active_chat_temp"]), step=0.05, key="prof_wiz_temp"
            )
    else:
        mode_options = ["Atendimento", "Pedagogico", "Comercial", "Financeiro", "Secretaria"]
        if st.session_state.get("active_chat_mode") not in mode_options:
            st.session_state["active_chat_mode"] = mode_options[0]
        c1, c2, c3 = st.columns([1.2, 1, 1])
        with c1:
            mode = st.selectbox("Modo", mode_options, key="active_chat_mode")
        with c2:
            include_context = st.checkbox("Usar contexto do sistema", value=True, key="coord_wiz_context")
        with c3:
            st.session_state["active_chat_temp"] = st.slider(
                "Criatividade", min_value=0.0, max_value=1.0, value=float(st.session_state["active_chat_temp"]), step=0.05, key="coord_wiz_temp"
            )

    if chat_key not in st.session_state["active_chat_histories"]:
        st.session_state["active_chat_histories"][chat_key] = []
    chat_history = st.session_state["active_chat_histories"][chat_key]

    if role == "Aluno":
        contexto_aluno = student_wiz_context(st.session_state.get("user_name", ""))
        st.info(
            f"Livro: {contexto_aluno.get('livro', 'Livro 1')} | Turma: {contexto_aluno.get('turma', 'Sem Turma')}"
        )
        a1, a2, a3 = st.columns(3)
        if a1.button("Revisar ultima licao", key="wiz_aluno_rev"):
            licao = (contexto_aluno.get("licoes") or ["Nao ha licao registrada."])[0]
            chat_history.append({"role": "user", "content": f"Quero revisar a ultima licao da minha turma: {licao}"})
        if a2.button("Praticar vocabulario", key="wiz_aluno_vocab"):
            chat_history.append({"role": "user", "content": f"Monte exercicios de vocabulario para o meu nivel ({contexto_aluno.get('livro','Livro 1')})."})
        if a3.button("Treinar conversacao", key="wiz_aluno_conv"):
            chat_history.append({"role": "user", "content": "Vamos treinar conversacao em ingles com correcao e feedback."})
    elif role == "Professor":
        p1, p2, p3, p4 = st.columns(4)
        if p1.button("Criar tarefa de casa", key="wiz_prof_hw"):
            chat_history.append({"role": "user", "content": "Crie uma tarefa de casa de ingles com objetivo, instrucoes e gabarito resumido."})
        if p2.button("Criar trabalho avaliativo", key="wiz_prof_assess"):
            chat_history.append({"role": "user", "content": "Crie um trabalho avaliativo de ingles com criterios de correcao."})
        if p3.button("Planejar aula 1 hora", key="wiz_prof_aula1h"):
            chat_history.append({"role": "user", "content": "Monte uma aula de ingles de 1 hora com aquecimento, explicacao, pratica e fechamento."})
        if p4.button("Planejar aula 2 horas", key="wiz_prof_aula2h"):
            chat_history.append({"role": "user", "content": "Monte uma aula de ingles de 2 horas com blocos de ensino, atividades e avaliacao."})
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
        st.session_state["chatbot_log"].append(
            {
                "data": datetime.datetime.now().strftime("%d/%m/%Y %H:%M"),
                "usuario": st.session_state.get("user_name", ""),
                "perfil": st.session_state.get("role", ""),
                "mensagens": chat_history,
            }
        )
        save_list(CHATBOT_LOG_FILE, st.session_state["chatbot_log"])
        st.success("Conversa salva no historico do Active.")

    prompt_label = "Digite sua mensagem para o chatbot"
    if role == "Aluno":
        prompt_label = "Pergunte algo de ingles"
    elif role == "Professor":
        prompt_label = "Descreva sua necessidade pedagogica"

    user_text = st.chat_input(prompt_label)
    if user_text:
        chat_history.append({"role": "user", "content": user_text})

        if role == "Aluno":
            contexto_aluno = student_wiz_context(st.session_state.get("user_name", ""))
            system_prompt = get_tutor_wiz_prompt(contexto_aluno)
        elif role == "Professor":
            system_prompt = get_active_system_prompt("Pedagogico", include_context=include_context) + (
                "\nAtenda apenas temas pedagogicos da escola de ingles: plano de aula, tarefa, avaliacao, rubrica e reforco."
            )
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
    aluno_nome = str(st.session_state.get("user_name", "")).strip()
    recebiveis_aluno = [
        r for r in st.session_state.get("receivables", [])
        if str(r.get("aluno", "")).strip() == aluno_nome
    ]
    hoje = datetime.date.today()

    def _valor_item(item):
        return parse_money(item.get("valor_parcela", item.get("valor", 0)))

    a_vencer = []
    vencidos = []
    pagos = []
    for item in recebiveis_aluno:
        status = str(item.get("status", "")).strip().lower()
        if status == "pago":
            pagos.append(item)
            continue
        dt_venc = parse_date(item.get("vencimento", ""))
        if dt_venc and dt_venc < hoje:
            vencidos.append(item)
        else:
            a_vencer.append(item)

    total_a_vencer = sum(_valor_item(i) for i in a_vencer)
    total_vencido = sum(_valor_item(i) for i in vencidos)
    total_pago = sum(_valor_item(i) for i in pagos)

    m1, m2, m3 = st.columns(3)
    with m1:
        st.metric("Boletos a vencer", f"{len(a_vencer)}")
        st.caption(format_money(total_a_vencer))
    with m2:
        st.metric("Boletos vencidos", f"{len(vencidos)}")
        st.caption(format_money(total_vencido))
    with m3:
        st.metric("Pagamentos realizados", f"{len(pagos)}")
        st.caption(format_money(total_pago))

    st.markdown("### Referencias financeiras")
    ref_opt = st.selectbox(
        "Selecione o que deseja visualizar",
        [
            "Boletos a vencer",
            "Boletos vencidos",
            "Resumo do que foi pago",
            "Todos os lancamentos",
        ],
        key="finance_ref_opt",
    )

    if ref_opt == "Boletos a vencer":
        dados_tabela = a_vencer
        tabela_msg = "Nenhum boleto a vencer."
    elif ref_opt == "Boletos vencidos":
        dados_tabela = vencidos
        tabela_msg = "Nenhum boleto vencido."
    elif ref_opt == "Resumo do que foi pago":
        dados_tabela = pagos
        tabela_msg = "Nenhum pagamento encontrado."
    else:
        dados_tabela = recebiveis_aluno
        tabela_msg = "Nenhum lancamento financeiro encontrado."

    if dados_tabela:
        df = pd.DataFrame(dados_tabela)
        col_order = [
            "data",
            "vencimento",
            "descricao",
            "categoria",
            "valor_parcela",
            "parcela",
            "cobranca",
            "status",
        ]
        df = df[[c for c in col_order if c in df.columns]]
        st.dataframe(df, use_container_width=True)
    else:
        st.info(tabela_msg)

    st.markdown("### Assistente financeiro (Wiz)")
    st.caption("Escolha uma opcao para o Wiz responder com orientacao financeira.")

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

    api_key = get_groq_api_key()
    if not api_key:
        st.warning("Assistente IA indisponivel: configure GROQ_API_KEY para liberar o Wiz nesta tela.")
        return

    chat_key = f"finance:{get_active_chat_history_key()}"
    if chat_key not in st.session_state["active_chat_histories"]:
        st.session_state["active_chat_histories"][chat_key] = []
    chat_history = st.session_state["active_chat_histories"][chat_key]

    col1, col2 = st.columns([1, 1])
    if col1.button("Consultar", type="primary"):
        resumo_contexto = (
            f"A vencer: {len(a_vencer)} ({format_money(total_a_vencer)}). "
            f"Vencidos: {len(vencidos)} ({format_money(total_vencido)}). "
            f"Pagos: {len(pagos)} ({format_money(total_pago)})."
        )
        chat_history.append(
            {
                "role": "user",
                "content": f"Quero ajuda com: {choice}. Contexto financeiro atual: {resumo_contexto}",
            }
        )
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

def run_commercial_panel():
    with st.sidebar:
        logo_path = get_logo_path()
        render_sidebar_logo(logo_path)
        st.markdown(f"### {st.session_state.get('user_name', '')}")
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
        menu_sales_label = sidebar_menu(
            "Comercial",
            [
                "Leads",
                "Agenda Comercial",
                "Financeiro Matricula",
                "Alunos Matriculados",
                "WhatsApp Leads",
                "Professor Wiz",
            ],
            "menu_sales",
        )
        st.markdown("---")
        st.markdown('<div class="logout-btn">', unsafe_allow_html=True)
        if st.button("Sair"):
            logout_user()
        st.markdown("</div>", unsafe_allow_html=True)

    menu_sales_map = {
        "Leads": "Leads",
        "Agenda Comercial": "Agenda",
        "Financeiro Matricula": "Financeiro Matricula",
        "Alunos Matriculados": "Alunos Matriculados",
        "WhatsApp Leads": "WhatsApp Leads",
        "Professor Wiz": "Professor Wiz",
    }
    menu_sales = menu_sales_map.get(menu_sales_label, "Leads")

    vendedor_atual = str(st.session_state.get("user_name", "")).strip() or "Comercial"

    if menu_sales == "Leads":
        st.markdown('<div class="main-header">Leads</div>', unsafe_allow_html=True)
        tab_new, tab_manage = st.tabs(["Novo Lead", "Pipeline / Gerenciar"])

        with tab_new:
            with st.form("sales_new_lead", clear_on_submit=True):
                c1, c2 = st.columns(2)
                with c1:
                    nome = st.text_input("Nome completo *")
                with c2:
                    telefone = st.text_input("Telefone / WhatsApp *")
                c3, c4 = st.columns(2)
                with c3:
                    email = st.text_input("E-mail")
                with c4:
                    status = st.selectbox("Status", sales_lead_status_options(), index=0)
                c5, c6 = st.columns(2)
                with c5:
                    origem = st.text_input("Origem do lead (Instagram, indicacao, etc.)")
                with c6:
                    interesse = st.text_input("Interesse / curso")
                observacao = st.text_area("Observacoes")
                if st.form_submit_button("Cadastrar lead", type="primary"):
                    if not nome.strip() or not telefone.strip():
                        st.error("Informe nome e telefone do lead.")
                    else:
                        st.session_state["sales_leads"].append(
                            {
                                "id": uuid.uuid4().hex,
                                "nome": nome.strip(),
                                "telefone": telefone.strip(),
                                "email": email.strip().lower(),
                                "status": status,
                                "origem": origem.strip(),
                                "interesse": interesse.strip(),
                                "observacao": observacao.strip(),
                                "vendedor": vendedor_atual,
                                "created_at": datetime.datetime.now().strftime("%d/%m/%Y %H:%M"),
                                "updated_at": "",
                                "ultimo_contato": "",
                            }
                        )
                        save_list(SALES_LEADS_FILE, st.session_state["sales_leads"])
                        st.success("Lead cadastrado com sucesso.")
                        st.rerun()

        with tab_manage:
            leads = st.session_state.get("sales_leads", [])
            if not leads:
                st.info("Nenhum lead cadastrado.")
            else:
                status_filter = st.selectbox("Filtrar por status", ["Todos"] + sales_lead_status_options())
                busca = st.text_input("Buscar por nome, telefone ou e-mail")
                filtrados = leads
                if status_filter != "Todos":
                    filtrados = [l for l in filtrados if str(l.get("status", "")).strip() == status_filter]
                if busca.strip():
                    termo = busca.strip().lower()
                    filtrados = [
                        l
                        for l in filtrados
                        if termo in str(l.get("nome", "")).lower()
                        or termo in str(l.get("telefone", "")).lower()
                        or termo in str(l.get("email", "")).lower()
                    ]

                total = len(filtrados)
                quentes = len([l for l in filtrados if str(l.get("status", "")).strip() == "Leads quentes"])
                fechados = len([l for l in filtrados if str(l.get("status", "")).strip() == "Fechado"])
                c1, c2, c3 = st.columns(3)
                c1.metric("Leads", str(total))
                c2.metric("Quentes", str(quentes))
                c3.metric("Fechados", str(fechados))

                if filtrados:
                    df_leads = pd.DataFrame(filtrados)
                    col_order = [
                        "nome",
                        "telefone",
                        "email",
                        "status",
                        "origem",
                        "interesse",
                        "vendedor",
                        "ultimo_contato",
                        "created_at",
                    ]
                    df_leads = df_leads[[c for c in col_order if c in df_leads.columns]]
                    st.dataframe(df_leads, use_container_width=True)

                    labels = [
                        f"{str(l.get('nome', '')).strip()} | {str(l.get('telefone', '')).strip()} | {str(l.get('status', '')).strip()}"
                        for l in filtrados
                    ]
                    lead_sel_label = st.selectbox("Selecionar lead para editar", labels)
                    lead_obj = filtrados[labels.index(lead_sel_label)]
                    with st.form(f"sales_edit_lead_{lead_obj.get('id', uuid.uuid4().hex)}"):
                        e1, e2 = st.columns(2)
                        with e1:
                            new_nome = st.text_input("Nome", value=str(lead_obj.get("nome", "")).strip())
                        with e2:
                            new_tel = st.text_input("Telefone", value=str(lead_obj.get("telefone", "")).strip())
                        e3, e4 = st.columns(2)
                        with e3:
                            new_email = st.text_input("E-mail", value=str(lead_obj.get("email", "")).strip())
                        with e4:
                            new_status = st.selectbox(
                                "Status",
                                sales_lead_status_options(),
                                index=sales_lead_status_options().index(str(lead_obj.get("status", "Novo contato")).strip())
                                if str(lead_obj.get("status", "Novo contato")).strip() in sales_lead_status_options()
                                else 0,
                            )
                        e5, e6 = st.columns(2)
                        with e5:
                            new_origem = st.text_input("Origem", value=str(lead_obj.get("origem", "")).strip())
                        with e6:
                            new_interesse = st.text_input("Interesse", value=str(lead_obj.get("interesse", "")).strip())
                        new_obs = st.text_area("Observacoes", value=str(lead_obj.get("observacao", "")).strip())
                        c_save, c_del = st.columns(2)
                        with c_save:
                            save_lead = st.form_submit_button("Salvar alteracoes")
                        with c_del:
                            delete_lead = st.form_submit_button("Excluir lead", type="primary")

                        if save_lead:
                            if not new_nome.strip() or not new_tel.strip():
                                st.error("Nome e telefone sao obrigatorios.")
                            else:
                                lead_obj["nome"] = new_nome.strip()
                                lead_obj["telefone"] = new_tel.strip()
                                lead_obj["email"] = new_email.strip().lower()
                                lead_obj["status"] = new_status
                                lead_obj["origem"] = new_origem.strip()
                                lead_obj["interesse"] = new_interesse.strip()
                                lead_obj["observacao"] = new_obs.strip()
                                lead_obj["updated_at"] = datetime.datetime.now().strftime("%d/%m/%Y %H:%M")
                                save_list(SALES_LEADS_FILE, st.session_state["sales_leads"])
                                st.success("Lead atualizado.")
                                st.rerun()
                        if delete_lead:
                            st.session_state["sales_leads"].remove(lead_obj)
                            save_list(SALES_LEADS_FILE, st.session_state["sales_leads"])
                            st.success("Lead excluido.")
                            st.rerun()
                else:
                    st.info("Nenhum lead encontrado com os filtros aplicados.")

    elif menu_sales == "Agenda":
        st.markdown('<div class="main-header">Agenda Comercial</div>', unsafe_allow_html=True)
        leads = st.session_state.get("sales_leads", [])
        tab_new, tab_list = st.tabs(["Novo agendamento", "Agenda cadastrada"])
        with tab_new:
            if not leads:
                st.info("Cadastre ao menos um lead para criar agendamentos.")
            else:
                lead_labels = [
                    f"{str(l.get('nome', '')).strip()} | {str(l.get('telefone', '')).strip()} | {str(l.get('status', '')).strip()}"
                    for l in leads
                ]
                with st.form("sales_new_agenda"):
                    lead_label = st.selectbox("Lead", lead_labels)
                    lead_obj = leads[lead_labels.index(lead_label)]
                    tipo = st.selectbox("Tipo", sales_agenda_type_options())
                    c1, c2 = st.columns(2)
                    with c1:
                        data_ag = st.date_input("Data", value=datetime.date.today(), format="DD/MM/YYYY")
                    with c2:
                        hora_ag = st.time_input("Horario", value=datetime.time(10, 0))
                    detalhes = st.text_area("Detalhes")
                    send_auto = st.checkbox("Enviar no WhatsApp automaticamente ao salvar", value=True)
                    if st.form_submit_button("Salvar agendamento", type="primary"):
                        item = {
                            "id": uuid.uuid4().hex,
                            "lead_id": str(lead_obj.get("id", "")).strip(),
                            "lead_nome": str(lead_obj.get("nome", "")).strip(),
                            "lead_telefone": str(lead_obj.get("telefone", "")).strip(),
                            "tipo": tipo,
                            "data": data_ag.strftime("%d/%m/%Y") if data_ag else "",
                            "hora": hora_ag.strftime("%H:%M") if hora_ag else "",
                            "detalhes": str(detalhes or "").strip(),
                            "status": "Agendado",
                            "vendedor": vendedor_atual,
                            "created_at": datetime.datetime.now().strftime("%d/%m/%Y %H:%M"),
                            "whatsapp_sent": False,
                            "whatsapp_status": "",
                        }
                        if send_auto:
                            ok, status, _ = _send_sales_schedule_whatsapp(lead_obj, item)
                            item["whatsapp_sent"] = bool(ok)
                            item["whatsapp_status"] = str(status or "")
                        st.session_state["sales_agenda"].append(item)
                        save_list(SALES_AGENDA_FILE, st.session_state["sales_agenda"])
                        st.success("Agendamento salvo.")
                        st.rerun()

        with tab_list:
            agenda = st.session_state.get("sales_agenda", [])
            if not agenda:
                st.info("Nenhum agendamento cadastrado.")
            else:
                tipo_filtro = st.selectbox("Filtrar por tipo", ["Todos"] + sales_agenda_type_options())
                status_filtro = st.selectbox("Filtrar por status", ["Todos", "Agendado", "Concluido", "Cancelado"])
                agenda_filtrada = agenda
                if tipo_filtro != "Todos":
                    agenda_filtrada = [a for a in agenda_filtrada if str(a.get("tipo", "")).strip() == tipo_filtro]
                if status_filtro != "Todos":
                    agenda_filtrada = [a for a in agenda_filtrada if str(a.get("status", "")).strip() == status_filtro]
                agenda_filtrada = sorted(
                    agenda_filtrada,
                    key=lambda a: (
                        parse_date(a.get("data", "")) or datetime.date(2100, 1, 1),
                        parse_time(a.get("hora", "00:00")),
                    ),
                )
                if agenda_filtrada:
                    df_ag = pd.DataFrame(agenda_filtrada)
                    col_order = [
                        "data",
                        "hora",
                        "lead_nome",
                        "lead_telefone",
                        "tipo",
                        "status",
                        "whatsapp_sent",
                        "whatsapp_status",
                        "detalhes",
                        "vendedor",
                    ]
                    df_ag = df_ag[[c for c in col_order if c in df_ag.columns]]
                    st.dataframe(df_ag, use_container_width=True)

                    labels = [
                        f"{a.get('data','')} {a.get('hora','')} | {a.get('lead_nome','')} | {a.get('tipo','')}"
                        for a in agenda_filtrada
                    ]
                    ag_sel = st.selectbox("Selecionar item da agenda", labels)
                    ag_obj = agenda_filtrada[labels.index(ag_sel)]
                    c1, c2, c3 = st.columns(3)
                    if c1.button("Marcar como concluido", key=f"sales_ag_done_{ag_obj.get('id','')}"):
                        ag_obj["status"] = "Concluido"
                        save_list(SALES_AGENDA_FILE, st.session_state["sales_agenda"])
                        st.success("Agenda atualizada.")
                        st.rerun()
                    if c2.button("Cancelar", key=f"sales_ag_cancel_{ag_obj.get('id','')}"):
                        ag_obj["status"] = "Cancelado"
                        save_list(SALES_AGENDA_FILE, st.session_state["sales_agenda"])
                        st.success("Agenda atualizada.")
                        st.rerun()
                    if c3.button("Reenviar WhatsApp", key=f"sales_ag_wa_{ag_obj.get('id','')}"):
                        lead_ref = next(
                            (l for l in st.session_state.get("sales_leads", []) if str(l.get("id", "")).strip() == str(ag_obj.get("lead_id", "")).strip()),
                            {"nome": ag_obj.get("lead_nome", ""), "telefone": ag_obj.get("lead_telefone", "")},
                        )
                        ok, status, _ = _send_sales_schedule_whatsapp(lead_ref, ag_obj)
                        ag_obj["whatsapp_sent"] = bool(ok)
                        ag_obj["whatsapp_status"] = str(status or "")
                        save_list(SALES_AGENDA_FILE, st.session_state["sales_agenda"])
                        if ok:
                            st.success("Mensagem enviada no WhatsApp.")
                        else:
                            st.error("Falha ao enviar WhatsApp.")
                        st.rerun()
                else:
                    st.info("Nenhum item na agenda para os filtros selecionados.")

    elif menu_sales == "Financeiro Matricula":
        st.markdown('<div class="main-header">Financeiro de Matricula (Comercial)</div>', unsafe_allow_html=True)
        students = [s for s in st.session_state.get("students", []) if str(s.get("nome", "")).strip()]
        if "sales_receipt_preview" not in st.session_state:
            st.session_state["sales_receipt_preview"] = ""
        if "sales_receipt_filename" not in st.session_state:
            st.session_state["sales_receipt_filename"] = "recibo_matricula.html"

        with st.form("sales_payment_form"):
            if students:
                aluno_nome = st.selectbox("Aluno matriculado", [s.get("nome", "") for s in students])
                aluno_obj = next((s for s in students if s.get("nome", "") == aluno_nome), {})
                tel_default = _student_phone(aluno_obj)
            else:
                aluno_nome = st.text_input("Aluno matriculado")
                tel_default = ""
                st.info("Nenhum aluno cadastrado; informe manualmente.")

            c1, c2 = st.columns(2)
            with c1:
                telefone = st.text_input("Telefone do aluno", value=tel_default)
            with c2:
                valor = st.text_input("Valor recebido (R$)")
            c3, c4 = st.columns(2)
            with c3:
                forma_pagamento = st.selectbox("Forma de pagamento", sales_payment_method_options())
            with c4:
                data_pagamento = st.date_input("Data do pagamento", value=datetime.date.today(), format="DD/MM/YYYY")
            descricao = st.text_input("Descricao", value="Taxa de Matricula")
            observacao = st.text_area("Observacoes")
            comprovante = st.file_uploader(
                "Anexar comprovante (imagem ou PDF)",
                type=["png", "jpg", "jpeg", "pdf"],
                key="sales_payment_file",
            )

            b1, b2 = st.columns(2)
            with b1:
                gerar_recibo = st.form_submit_button("Gerar recibo")
            with b2:
                enviar_aprovacao = st.form_submit_button("Enviar para aprovacao do coordenador", type="primary")

            temp_record = {
                "id": uuid.uuid4().hex,
                "aluno": str(aluno_nome or "").strip(),
                "telefone": str(telefone or "").strip(),
                "valor": str(valor or "").strip(),
                "forma_pagamento": str(forma_pagamento or "").strip(),
                "data_pagamento": data_pagamento.strftime("%d/%m/%Y") if data_pagamento else "",
                "descricao": str(descricao or "").strip() or "Taxa de Matricula",
                "observacao": str(observacao or "").strip(),
                "vendedor": vendedor_atual,
                "status": "Pendente",
                "created_at": datetime.datetime.now().strftime("%d/%m/%Y %H:%M"),
                "updated_at": "",
                "recibo_numero": f"REC-{datetime.datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}",
                "receivable_code": "",
                "comprovante_nome": comprovante.name if comprovante else "",
                "comprovante_mime": comprovante.type if comprovante else "",
                "comprovante_b64": base64.b64encode(comprovante.getvalue()).decode("utf-8") if comprovante else "",
            }

            if gerar_recibo:
                if not str(temp_record.get("aluno", "")).strip() or parse_money(temp_record.get("valor", "")) <= 0:
                    st.error("Informe aluno e valor valido para gerar o recibo.")
                else:
                    st.session_state["sales_receipt_preview"] = _sales_receipt_html(temp_record)
                    st.session_state["sales_receipt_filename"] = f"recibo_{str(temp_record.get('aluno', 'aluno')).replace(' ', '_').lower()}.html"
                    st.success("Recibo gerado.")

            if enviar_aprovacao:
                if not str(temp_record.get("aluno", "")).strip() or parse_money(temp_record.get("valor", "")) <= 0:
                    st.error("Informe aluno e valor valido.")
                else:
                    st.session_state["sales_payments"].append(temp_record)
                    save_list(SALES_PAYMENTS_FILE, st.session_state["sales_payments"])
                    st.success("Pagamento enviado para aprovacao do coordenador.")
                    st.rerun()

        if st.session_state.get("sales_receipt_preview"):
            st.markdown("### Pre-visualizacao do recibo")
            st.components.v1.html(st.session_state.get("sales_receipt_preview", ""), height=520, scrolling=True)
            st.download_button(
                "Baixar recibo (HTML)",
                data=st.session_state.get("sales_receipt_preview", ""),
                file_name=st.session_state.get("sales_receipt_filename", "recibo_matricula.html"),
                mime="text/html",
            )

        st.markdown("### Pagamentos enviados para aprovacao")
        my_payments = [
            p for p in st.session_state.get("sales_payments", [])
            if str(p.get("vendedor", "")).strip() == vendedor_atual
        ]
        if not my_payments:
            st.info("Nenhum pagamento enviado.")
        else:
            df_pay = pd.DataFrame(my_payments)
            col_order = [
                "created_at",
                "aluno",
                "telefone",
                "valor",
                "forma_pagamento",
                "data_pagamento",
                "status",
                "recibo_numero",
                "receivable_code",
            ]
            df_pay = df_pay[[c for c in col_order if c in df_pay.columns]]
            st.dataframe(df_pay, use_container_width=True)

    elif menu_sales == "Alunos Matriculados":
        st.markdown('<div class="main-header">Alunos Matriculados</div>', unsafe_allow_html=True)
        alunos = st.session_state.get("students", [])
        if not alunos:
            st.info("Nenhum aluno matriculado.")
        else:
            rows = []
            for aluno in alunos:
                nome = str(aluno.get("nome", "")).strip()
                telefone = _student_phone(aluno)
                if nome:
                    rows.append({"nome_completo": nome, "telefone": telefone})
            if not rows:
                st.info("Nenhum aluno com dados disponiveis.")
            else:
                st.dataframe(pd.DataFrame(rows), use_container_width=True)

    elif menu_sales == "WhatsApp Leads":
        st.markdown('<div class="main-header">WhatsApp para Leads</div>', unsafe_allow_html=True)
        leads = st.session_state.get("sales_leads", [])
        if not leads:
            st.info("Cadastre leads para enviar mensagens.")
        else:
            status_filter = st.selectbox("Filtrar status dos leads", ["Todos"] + sales_lead_status_options())
            leads_filtrados = leads
            if status_filter != "Todos":
                leads_filtrados = [l for l in leads if str(l.get("status", "")).strip() == status_filter]
            labels = [
                f"{str(l.get('nome', '')).strip()} | {str(l.get('telefone', '')).strip()} | {str(l.get('status', '')).strip()}"
                for l in leads_filtrados
            ]
            selected = st.multiselect("Leads para envio", labels, default=labels)
            mensagem = st.text_area("Mensagem", value="Ola! Tudo bem? Aqui e do Comercial da Active Educacional.")
            if st.button("Enviar WhatsApp para selecionados", type="primary"):
                if not selected:
                    st.error("Selecione ao menos um lead.")
                elif not str(mensagem).strip():
                    st.error("Digite uma mensagem.")
                else:
                    total = 0
                    ok_count = 0
                    fail_count = 0
                    for label in selected:
                        lead_obj = leads_filtrados[labels.index(label)]
                        number = _lead_phone_for_whatsapp(lead_obj)
                        if not number:
                            fail_count += 1
                            continue
                        total += 1
                        ok, status, _ = _send_whatsapp_auto(number, str(mensagem).strip())
                        if ok:
                            ok_count += 1
                            lead_obj["ultimo_contato"] = datetime.datetime.now().strftime("%d/%m/%Y %H:%M")
                            lead_obj["updated_at"] = lead_obj["ultimo_contato"]
                        else:
                            fail_count += 1
                            lead_obj["ultimo_erro_whatsapp"] = str(status or "")
                    save_list(SALES_LEADS_FILE, st.session_state["sales_leads"])
                    st.success(f"Envio concluido. Sucesso: {ok_count} | Falhas: {fail_count} | Tentativas: {total}")

    elif menu_sales == "Professor Wiz":
        run_active_chatbot()

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
        .feature-card { border-radius: 20px; padding: 18px 18px; border: 1px solid rgba(148,163,184,0.25); box-shadow: 0 12px 26px rgba(15, 23, 42, 0.24) !important; transition: transform 0.2s ease, border-color 0.2s ease, box-shadow 0.2s ease; }
        .feature-card:hover { transform: translateY(-2px); box-shadow: 0 16px 30px rgba(15, 23, 42, 0.3) !important; }
        .feature-card.feature-blue { background: linear-gradient(135deg, rgba(37,99,235,0.34), rgba(30,58,138,0.28)) !important; border-color: rgba(37,99,235,0.55); }
        .feature-card.feature-green { background: linear-gradient(135deg, rgba(34,197,94,0.3), rgba(22,163,74,0.24)) !important; border-color: rgba(22,163,74,0.55); }
        .feature-card.feature-orange { background: linear-gradient(135deg, rgba(251,146,60,0.34), rgba(234,88,12,0.25)) !important; border-color: rgba(234,88,12,0.55); }
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
        section[data-testid="stSidebar"] .stButton > button { background: linear-gradient(135deg, rgba(30,58,138,0.08) 0%, rgba(22,163,74,0.08) 52%, rgba(234,88,12,0.08) 100%); border: 1px solid #d7e3f5; color: #334155; text-align: left; font-weight: 700; padding: 0 1rem; width: var(--sidebar-menu-btn-width) !important; min-width: var(--sidebar-menu-btn-width) !important; max-width: var(--sidebar-menu-btn-width) !important; border-radius: 14px; transition: all 0.2s ease; margin-bottom: 8px; box-shadow: 0 6px 16px rgba(15, 23, 42, 0.06); height: 56px !important; min-height: 56px !important; max-height: 56px !important; display: flex; align-items: center; justify-content: flex-start; box-sizing: border-box; white-space: nowrap; overflow: visible; text-overflow: clip; }
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
        section[data-testid="stSidebar"] .stButton > button:hover { color: #ffffff !important; background: linear-gradient(90deg, #1e3a8a 0%, #16a34a 52%, #ea580c 100%) !important; border-color: #1e3a8a !important; transform: translateY(-1px); box-shadow: 0 10px 22px rgba(30, 58, 138, 0.25) !important; }
        section[data-testid="stSidebar"] .stButton > button[kind="primary"] { background: linear-gradient(90deg, #1e3a8a 0%, #16a34a 52%, #ea580c 100%); color: #ffffff; border: none; box-shadow: 0 10px 24px rgba(30, 58, 138, 0.28); }
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
if not st.session_state.get("_active_users_loaded", False):
    st.session_state["users"] = load_users()
    users_source = st.session_state.get("_data_sources", {}).get(_db_key_for_path(USERS_FILE), "")
    st.session_state["users"] = ensure_admin_user(st.session_state["users"])
    st.session_state["users"] = sync_users_from_profiles(st.session_state["users"])
    if users_source != "db_unavailable":
        save_users(st.session_state["users"])
    st.session_state["wiz_settings"] = _load_json_dict(WIZ_SETTINGS_FILE, DEFAULT_WIZ_SETTINGS)
    st.session_state["_active_users_loaded"] = True

if st.session_state.get("logged_in", False) and not st.session_state.get("_active_runtime_loaded", False):
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
    st.session_state["class_sessions"] = load_list(CLASS_SESSIONS_FILE)
    st.session_state["inventory"] = load_list(INVENTORY_FILE)
    st.session_state["inventory_moves"] = load_list(INVENTORY_MOVES_FILE)
    st.session_state["certificates"] = load_list(CERTIFICATES_FILE)
    st.session_state["books"] = load_list(BOOKS_FILE)
    st.session_state["material_orders"] = load_list(MATERIAL_ORDERS_FILE)
    st.session_state["challenges"] = load_list(CHALLENGES_FILE)
    st.session_state["challenge_completions"] = load_list(CHALLENGE_COMPLETIONS_FILE)
    st.session_state["activities"] = load_list(ACTIVITIES_FILE)
    st.session_state["activity_submissions"] = load_list(ACTIVITY_SUBMISSIONS_FILE)
    st.session_state["sales_leads"] = load_list(SALES_LEADS_FILE)
    st.session_state["sales_agenda"] = load_list(SALES_AGENDA_FILE)
    st.session_state["sales_payments"] = load_list(SALES_PAYMENTS_FILE)

    _ensure_challenge_store_ids()
    _ensure_activity_store_ids()
    _ensure_sales_store_defaults()

    if not st.session_state["books"]:
        st.session_state["books"] = [
            {"nivel": "Livro 1", "titulo": "Livro 1", "url": "", "file_path": ""},
            {"nivel": "Livro 2", "titulo": "Livro 2", "url": "", "file_path": ""},
            {"nivel": "Livro 3", "titulo": "Livro 3", "url": "", "file_path": ""},
            {"nivel": "Livro 4", "titulo": "Livro 4", "url": "", "file_path": ""},
        ]
        books_source = st.session_state.get("_data_sources", {}).get(_db_key_for_path(BOOKS_FILE), "")
        if books_source != "db_unavailable":
            save_list(BOOKS_FILE, st.session_state["books"])

    if "wiz_daily_backup_checked" not in st.session_state:
        st.session_state["wiz_daily_backup_checked"] = False
    if not st.session_state["wiz_daily_backup_checked"]:
        _run_wiz_daily_backup(force=False)
        st.session_state["wiz_daily_backup_checked"] = True

    st.session_state["_active_runtime_loaded"] = True

_db_sources = st.session_state.get("_data_sources", {}) or {}
_db_has_unavailable = any(str(src).strip() == "db_unavailable" for src in _db_sources.values())
_db_last_error = str(st.session_state.get("_db_last_error", "") or "").strip()
if _db_has_unavailable:
    st.session_state["_persistence_alert"] = (
        "Banco de dados indisponivel no carregamento inicial. O sistema entrou em modo de protecao para nao sobrescrever dados."
    )
    if _db_last_error:
        st.session_state["_persistence_alert"] += f" Erro: {_db_last_error}"
elif not _db_enabled():
    st.session_state["_persistence_alert"] = (
        "Persistencia local ativa. Em hospedagem temporaria os dados podem sumir apos reinicio/deploy. "
        "Configure ACTIVE_DATABASE_URL ou variaveis PG* para persistencia real."
    )
else:
    st.session_state["_persistence_alert"] = ""

if st.session_state.get("_persistence_alert"):
    st.warning(st.session_state.get("_persistence_alert"))

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
  <div class="hero-title">Ativo<br>Sistema Educacional</div>
  <div class="hero-subtitle hero-tagline">Gestao academica, comunicacao e conteudo pedagogico.</div>
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
                role = st.selectbox("Perfil", ["Aluno", "Professor", "Comercial", "Coordenador"])
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
    feature_palette = ["feature-blue", "feature-green", "feature-orange"]
    for i in range(0, len(feature_cards), 3):
        cols = st.columns(3, gap="large")
        for offset, (col, card) in enumerate(zip(cols, feature_cards[i:i+3])):
            title, sub = card
            feature_class = feature_palette[(i + offset) % len(feature_palette)]
            with col:
                st.markdown(
                    f"""
<div class="feature-card {feature_class}">
  <div class="feature-text">{title}</div>
  <div class="feature-sub">{sub}</div>
</div>
""",
                    unsafe_allow_html=True,
                )
    st.markdown(
        f"""
<div class="feature-cta">
  <a href="https://wa.me/{WHATSAPP_NUMBER}" target="_blank" class="whatsapp-button">Falar com Suporte no WhatsApp</a>
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
        menu_aluno_label = sidebar_menu("Navegacao", ["Painel", "Agenda", "Minhas Aulas", "Boletim e Frequencia", "Mensagens", "Atividades", "Desafios", "Aulas Gravadas", "Financeiro", "Materiais de Estudo", "Professor Wiz"], "menu_aluno")
        st.markdown("---")
        st.markdown('<div class="logout-btn">', unsafe_allow_html=True)
        if st.button("Sair"): logout_user()
        st.markdown('</div>', unsafe_allow_html=True)

    menu_aluno_map = {"Painel": "Dashboard", "Agenda": "Agenda", "Minhas Aulas": "Minhas Aulas", "Boletim e Frequencia": "Boletim & Frequencia", "Mensagens": "Mensagens", "Atividades": "Atividades", "Desafios": "Desafios", "Aulas Gravadas": "Aulas Gravadas", "Financeiro": "Financeiro", "Materiais de Estudo": "Materiais de Estudo", "Professor Wiz": "Professor Wiz"}
    menu_aluno = menu_aluno_map.get(menu_aluno_label, "Dashboard")

    if menu_aluno == "Dashboard":
        st.markdown('<div class="main-header">Painel do Aluno</div>', unsafe_allow_html=True)
        link_aula = "https://zoom.us/join"
        turma_aluno = next((s["turma"] for s in st.session_state["students"] if s["nome"] == st.session_state["user_name"]), None)
        if turma_aluno:
            turma_obj = next((c for c in st.session_state["classes"] if c["nome"] == turma_aluno), None)
            if turma_obj and "link_zoom" in turma_obj: link_aula = turma_obj["link_zoom"]
        st.error("AULA AO VIVO AGORA")
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

        st.markdown("### Historico de aulas")
        aluno_nome = st.session_state.get("user_name", "")
        aluno_obj = next((s for s in st.session_state.get("students", []) if s.get("nome") == aluno_nome), {})
        turma_aluno = str(aluno_obj.get("turma", "")).strip()
        historico_aulas = [
            s for s in st.session_state.get("class_sessions", [])
            if str(s.get("turma", "")).strip() == turma_aluno and str(s.get("status", "")).strip().lower() == "finalizada"
        ]
        historico_aulas = sorted(
            historico_aulas,
            key=lambda x: (
                parse_date(x.get("data", "")) or datetime.date(1900, 1, 1),
                parse_time(x.get("hora_inicio_real", x.get("hora_inicio_prevista", "00:00"))),
            ),
            reverse=True,
        )
        if not historico_aulas:
            st.info("Nenhuma aula finalizada registrada para sua turma.")
        else:
            df_hist = pd.DataFrame(historico_aulas)
            col_order = [
                "data",
                "turma",
                "professor",
                "hora_inicio_real",
                "hora_fim_real",
                "titulo",
                "licao",
                "resumo_final",
            ]
            df_hist = df_hist[[c for c in col_order if c in df_hist.columns]]
            st.dataframe(df_hist, use_container_width=True)

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

    elif menu_aluno == "Atividades":
        st.markdown('<div class="main-header">Atividades (Tarefas, Provas e Trabalhos)</div>', unsafe_allow_html=True)
        aluno_nome = st.session_state.get("user_name", "")
        turma_aluno = _student_class_name(aluno_nome)
        if not turma_aluno:
            st.info("Seu usuario nao esta vinculado a uma turma.")
        else:
            atividades_turma = [
                a for a in st.session_state.get("activities", [])
                if str(a.get("turma", "")).strip() == turma_aluno
            ]
            atividades_turma = sorted(
                atividades_turma,
                key=lambda a: (
                    0 if _is_activity_open(a) else 1,
                    parse_date(a.get("due_date", "")) or datetime.date(2100, 1, 1),
                    str(a.get("created_at", "")),
                ),
            )
            if not atividades_turma:
                st.info("Nenhuma atividade publicada para sua turma.")
            else:
                st.caption(f"Turma: {turma_aluno}")
                for atividade in atividades_turma:
                    activity_id = str(atividade.get("id", "")).strip()
                    if not activity_id:
                        continue
                    titulo = str(atividade.get("titulo", "Atividade")).strip() or "Atividade"
                    tipo_atividade = str(atividade.get("tipo", "Atividade")).strip() or "Atividade"
                    data_limite = str(atividade.get("due_date", "")).strip() or "Sem prazo"
                    atividade_aberta = _is_activity_open(atividade)
                    status_atividade = "Ativa" if atividade_aberta else "Encerrada"
                    total_pontos = _activity_points_total(atividade)
                    submission = get_activity_submission(activity_id, aluno_nome)
                    permitir_reenvio = bool(atividade.get("allow_resubmission", False))

                    st.markdown("---")
                    st.markdown(f"### {titulo}")
                    st.caption(
                        f"Tipo: {tipo_atividade} | Status: {status_atividade} | Prazo: {data_limite} | Pontos: {total_pontos}"
                    )
                    if str(atividade.get("descricao", "")).strip():
                        st.write(str(atividade.get("descricao", "")).strip())

                    existing_answers = {}
                    if submission:
                        for ans in submission.get("respostas", []):
                            qid = str(ans.get("question_id", "")).strip()
                            if qid:
                                existing_answers[qid] = ans

                        score_final = activity_submission_final_score(submission)
                        c1, c2, c3 = st.columns(3)
                        c1.metric("Status da sua entrega", str(submission.get("status", "Enviada")))
                        c2.metric("Nota final", f"{score_final:.1f}/{submission.get('score_total', total_pontos)}")
                        c3.metric(
                            "Correcao automatica",
                            f"{_parse_float(submission.get('score_auto', 0), 0.0):.1f}/{submission.get('score_total', total_pontos)}",
                        )
                        if str(submission.get("feedback_professor", "")).strip():
                            st.info(f"Feedback do professor: {submission.get('feedback_professor')}")
                        with st.expander("Ver minhas respostas"):
                            respostas_enviadas = submission.get("respostas", []) or []
                            if not respostas_enviadas:
                                st.caption("Sem respostas registradas.")
                            for idx, resp in enumerate(respostas_enviadas, start=1):
                                enunciado = str(resp.get("enunciado", "")).strip()
                                st.markdown(f"**{idx}. {enunciado or 'Questao'}**")
                                if str(resp.get("tipo", "")).strip() == "multipla_escolha":
                                    st.write(f"Resposta: {str(resp.get('resposta_texto', '')).strip() or '(nao respondida)'}")
                                else:
                                    st.write(str(resp.get("resposta_texto", "")).strip() or "(nao respondida)")

                    if not atividade_aberta:
                        st.warning("Atividade encerrada pelo professor. Novas respostas estao desativadas.")
                        continue

                    if submission and not permitir_reenvio:
                        st.success("Atividade ja enviada. Reenvio desativado pelo professor.")
                        continue

                    with st.form(f"aluno_activity_form_{activity_id}"):
                        answers_payload = {}
                        missing_questions = []
                        questions = [q for q in atividade.get("questions", []) if isinstance(q, dict)]
                        if not questions:
                            st.info("Esta atividade ainda nao possui questoes cadastradas.")
                        for idx, question in enumerate(questions, start=1):
                            qid = str(question.get("id", "")).strip() or f"q_{idx}"
                            q_tipo = str(question.get("tipo", "aberta")).strip().lower()
                            enunciado = str(question.get("enunciado", "")).strip() or f"Questao {idx}"
                            pontos = parse_int(question.get("pontos", 1))
                            pontos = pontos if pontos > 0 else 1
                            st.markdown(f"**{idx}. {enunciado}**")
                            st.caption(f"Pontos: {pontos}")
                            prev_answer = existing_answers.get(qid, {})

                            if q_tipo == "multipla_escolha":
                                opcoes = question.get("opcoes", [])
                                if not isinstance(opcoes, list):
                                    opcoes = []
                                opcoes = [str(opt).strip() for opt in opcoes if str(opt).strip()]
                                placeholder = "Selecione uma opcao"
                                opcoes_select = [placeholder] + opcoes
                                prev_idx = prev_answer.get("resposta_indice", None)
                                try:
                                    prev_idx = int(prev_idx)
                                except Exception:
                                    prev_idx = None
                                default_idx = prev_idx + 1 if prev_idx is not None and 0 <= prev_idx < len(opcoes) else 0
                                escolha = st.selectbox(
                                    "Resposta",
                                    opcoes_select,
                                    index=default_idx,
                                    key=f"aluno_act_{activity_id}_{qid}_choice",
                                )
                                selected_idx = opcoes_select.index(escolha) - 1 if escolha != placeholder else None
                                answers_payload[qid] = {"indice": selected_idx}
                                if selected_idx is None:
                                    missing_questions.append(f"Questao {idx}")
                            else:
                                prev_text = str(prev_answer.get("resposta_texto", "")).strip()
                                resposta_texto = st.text_area(
                                    "Resposta",
                                    value=prev_text,
                                    key=f"aluno_act_{activity_id}_{qid}_text",
                                )
                                answers_payload[qid] = {"texto": resposta_texto}
                                if not str(resposta_texto).strip():
                                    missing_questions.append(f"Questao {idx}")

                        submit_label = "Reenviar atividade" if submission and permitir_reenvio else "Enviar atividade"
                        if st.form_submit_button(submit_label, type="primary"):
                            if not questions:
                                st.error("Esta atividade nao possui questoes para responder.")
                            elif missing_questions:
                                st.error("Responda todas as questoes antes de enviar.")
                            else:
                                ok, msg = upsert_activity_submission(
                                    atividade,
                                    aluno_nome,
                                    turma_aluno,
                                    answers_payload,
                                )
                                if ok:
                                    st.success(msg)
                                    st.rerun()
                                else:
                                    st.error(msg)

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
                if m['link']: st.markdown(f"[Baixar Arquivo]({m['link']})")
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
        menu_prof_label = sidebar_menu("Gestão", ["Minhas Turmas", "Agenda", "Mensagens", "Atividades", "Lançar Notas", "Biblioteca", "Professor Wiz"], "menu_prof")
        st.markdown("---")
        st.markdown('<div class="logout-btn">', unsafe_allow_html=True)
        if st.button("Sair"): logout_user()
        st.markdown('</div>', unsafe_allow_html=True)

    menu_prof_map = {
        "Minhas Turmas": "Minhas Turmas",
        "Agenda": "Agenda",
        "Mensagens": "Mensagens",
        "Atividades": "Atividades",
        "Lançar Notas": "Notas",
        "Lancar Notas": "Notas",
        "Biblioteca": "Livros",
        "Livros": "Livros",
        "Professor Wiz": "Assistente IA",
    }
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
            dias_turma_exibicao = str(turma_obj.get("dias", "")).strip()
            if not dias_turma_exibicao:
                dias_turma_exibicao = format_class_schedule(
                    turma_obj.get("dias_semana", []),
                    str(turma_obj.get("hora_inicio", "")).strip(),
                    str(turma_obj.get("hora_fim", "")).strip(),
                )
            st.write(f"**Dias e Horários:** {dias_turma_exibicao or 'Horário a definir'}")
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
            tab_agenda, tab_controle = st.tabs(["Agenda da Turma", "Iniciar / Fechar Aula"])

            with tab_agenda:
                agenda = [a for a in st.session_state["agenda"] if a.get("turma") in set(turmas_prof)]
                render_agenda(sort_agenda(agenda), "Nenhuma aula agendada para suas turmas.")

            with tab_controle:
                turma_ctrl = st.selectbox("Turma", turmas_prof, key="prof_ctrl_turma")
                turma_obj = next((c for c in st.session_state.get("classes", []) if c.get("nome") == turma_ctrl), {})
                aulas_turma = [
                    a for a in st.session_state.get("agenda", [])
                    if str(a.get("turma", "")).strip() == str(turma_ctrl).strip()
                ]
                aulas_turma = sort_agenda(aulas_turma)

                prof_nome_atual = str(st.session_state.get("user_name", "")).strip()
                sessoes_ativas = [
                    s for s in st.session_state.get("class_sessions", [])
                    if str(s.get("turma", "")).strip() == str(turma_ctrl).strip()
                    and str(s.get("professor", "")).strip() == prof_nome_atual
                    and str(s.get("status", "")).strip().lower() == "em andamento"
                ]

                if not sessoes_ativas:
                    st.markdown("### Iniciar aula")
                    with st.form("prof_start_class_session"):
                        aula_idx = -1
                        if aulas_turma:
                            opcoes = [
                                f"{a.get('data','')} {a.get('hora','')} | {a.get('titulo','Aula')}"
                                for a in aulas_turma
                            ]
                            aula_idx = st.selectbox(
                                "Aula agendada (opcional)",
                                list(range(len(aulas_turma))),
                                format_func=lambda i: opcoes[i],
                                key="prof_start_agenda_idx",
                            )
                        else:
                            st.info("Nao ha aula agendada para essa turma. Voce pode iniciar manualmente.")

                        licao = st.text_area("Licao/Conteudo da aula", placeholder="Ex: Unit 3 - Simple Present + exercicios de conversacao")
                        resumo_inicio = st.text_area("Objetivo da aula (opcional)")

                        if st.form_submit_button("Iniciar aula", type="primary"):
                            if not licao.strip():
                                st.error("Informe a licao/conteudo da aula antes de iniciar.")
                            else:
                                aula_sel = aulas_turma[aula_idx] if aula_idx >= 0 and aula_idx < len(aulas_turma) else {}
                                now_dt = datetime.datetime.now()
                                st.session_state["class_sessions"].append(
                                    {
                                        "id": uuid.uuid4().hex,
                                        "turma": turma_ctrl,
                                        "professor": prof_nome_atual,
                                        "titulo": str(aula_sel.get("titulo", "")).strip() or "Aula",
                                        "data": str(aula_sel.get("data", "")).strip() or now_dt.strftime("%d/%m/%Y"),
                                        "hora_inicio_prevista": str(aula_sel.get("hora", "")).strip() or str(turma_obj.get("hora_inicio", "")).strip(),
                                        "hora_fim_prevista": str(turma_obj.get("hora_fim", "")).strip(),
                                        "link": str(aula_sel.get("link", "")).strip() or str(turma_obj.get("link_zoom", "")).strip(),
                                        "licao": licao.strip(),
                                        "resumo_inicio": resumo_inicio.strip(),
                                        "inicio_em": now_dt.strftime("%d/%m/%Y %H:%M"),
                                        "hora_inicio_real": now_dt.strftime("%H:%M"),
                                        "status": "Em andamento",
                                        "resumo_final": "",
                                        "hora_fim_real": "",
                                        "fim_em": "",
                                    }
                                )
                                save_list(CLASS_SESSIONS_FILE, st.session_state["class_sessions"])
                                st.success("Aula iniciada com sucesso.")
                                st.rerun()
                else:
                    sessao_ativa = sessoes_ativas[0]
                    st.markdown("### Aula em andamento")
                    st.info(
                        f"Turma: {sessao_ativa.get('turma','')} | Inicio: {sessao_ativa.get('inicio_em','')} | "
                        f"Licao: {sessao_ativa.get('licao','')}"
                    )
                    with st.form("prof_close_class_session"):
                        resumo_final = st.text_area(
                            "Resumo final da aula",
                            value=str(sessao_ativa.get("resumo_final", "")).strip() or str(sessao_ativa.get("licao", "")).strip(),
                        )
                        if st.form_submit_button("Fechar aula", type="primary"):
                            now_dt = datetime.datetime.now()
                            sessao_ativa["status"] = "Finalizada"
                            sessao_ativa["resumo_final"] = resumo_final.strip()
                            sessao_ativa["fim_em"] = now_dt.strftime("%d/%m/%Y %H:%M")
                            sessao_ativa["hora_fim_real"] = now_dt.strftime("%H:%M")
                            if not sessao_ativa.get("data"):
                                sessao_ativa["data"] = now_dt.strftime("%d/%m/%Y")
                            save_list(CLASS_SESSIONS_FILE, st.session_state["class_sessions"])
                            st.success("Aula fechada e salva no historico dos alunos.")
                            st.rerun()

                st.markdown("### Ultimas aulas finalizadas da turma")
                historico_turma = [
                    s for s in st.session_state.get("class_sessions", [])
                    if str(s.get("turma", "")).strip() == str(turma_ctrl).strip()
                    and str(s.get("status", "")).strip().lower() == "finalizada"
                ]
                historico_turma = sorted(
                    historico_turma,
                    key=lambda x: (
                        parse_date(x.get("data", "")) or datetime.date(1900, 1, 1),
                        parse_time(x.get("hora_inicio_real", x.get("hora_inicio_prevista", "00:00"))),
                    ),
                    reverse=True,
                )
                if historico_turma:
                    df_hist = pd.DataFrame(historico_turma)
                    col_order = ["data", "turma", "professor", "hora_inicio_real", "hora_fim_real", "titulo", "licao", "resumo_final"]
                    df_hist = df_hist[[c for c in col_order if c in df_hist.columns]]
                    st.dataframe(df_hist, use_container_width=True)
                else:
                    st.info("Ainda nao ha aulas finalizadas para essa turma.")
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
                        st.success(
                            "Mensagem publicada. "
                            f"E-mail: {stats.get('email_ok', 0)}/{stats.get('email_total', 0)} | "
                            f"WhatsApp: {stats.get('whatsapp_ok', 0)}/{stats.get('whatsapp_total', 0)}."
                        )
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
    elif menu_prof == "Atividades":
        st.markdown('<div class="main-header">Atividades (Tarefas, Provas e Trabalhos)</div>', unsafe_allow_html=True)
        turmas_prof = _teacher_class_names_for_user(st.session_state.get("user_name", ""))
        if not turmas_prof:
            st.info("Nenhuma turma atribuida a voce.")
        else:
            tab_publicar, tab_publicadas, tab_respostas = st.tabs(
                ["Publicar atividade", "Atividades publicadas", "Respostas dos alunos"]
            )

            with tab_publicar:
                with st.form("prof_create_activity"):
                    turma_atividade = st.selectbox("Turma", turmas_prof)
                    tipo_atividade = st.selectbox("Tipo", ["Tarefa de Casa", "Prova", "Trabalho"])
                    titulo_atividade = st.text_input("Titulo")
                    descricao_atividade = st.text_area("Descricao / instrucoes")
                    due_date = st.date_input(
                        "Prazo final",
                        value=datetime.date.today() + datetime.timedelta(days=7),
                        format="DD/MM/YYYY",
                    )
                    allow_resubmission = st.checkbox("Permitir reenvio do aluno", value=False)
                    qtd_questoes = st.number_input("Quantidade de questoes", min_value=1, max_value=20, value=3, step=1)
                    st.caption("Monte as questoes abaixo. Em multipla escolha, informe uma opcao por linha.")

                    questions_payload = []
                    validation_errors = []
                    for idx in range(int(qtd_questoes)):
                        st.markdown(f"#### Questao {idx + 1}")
                        q_tipo_label = st.selectbox(
                            "Tipo da questao",
                            ["Multipla escolha", "Resposta aberta"],
                            key=f"prof_activity_qtype_{idx}",
                        )
                        q_enunciado = st.text_area(
                            "Enunciado",
                            key=f"prof_activity_qtext_{idx}",
                        )
                        q_pontos = st.number_input(
                            "Pontos da questao",
                            min_value=1,
                            max_value=100,
                            value=10,
                            step=1,
                            key=f"prof_activity_qpoints_{idx}",
                        )
                        qid = uuid.uuid4().hex

                        if not str(q_enunciado).strip():
                            validation_errors.append(f"Questao {idx + 1}: informe o enunciado.")

                        if q_tipo_label == "Multipla escolha":
                            q_opcoes_text = st.text_area(
                                "Opcoes (uma por linha)",
                                value="Opcao A\nOpcao B\nOpcao C\nOpcao D",
                                key=f"prof_activity_qopts_{idx}",
                            )
                            q_opcoes = [line.strip() for line in str(q_opcoes_text or "").splitlines() if line.strip()]
                            if len(q_opcoes) < 2:
                                validation_errors.append(f"Questao {idx + 1}: multipla escolha precisa de ao menos 2 opcoes.")
                            corretas_opts = ["Nao definir"] + q_opcoes if q_opcoes else ["Nao definir"]
                            q_correta = st.selectbox(
                                "Resposta correta (opcional)",
                                corretas_opts,
                                key=f"prof_activity_qcorrect_{idx}",
                            )
                            correta_idx = q_opcoes.index(q_correta) if q_correta != "Nao definir" and q_correta in q_opcoes else None
                            questions_payload.append(
                                {
                                    "id": qid,
                                    "tipo": "multipla_escolha",
                                    "enunciado": str(q_enunciado).strip(),
                                    "opcoes": q_opcoes,
                                    "correta_idx": correta_idx,
                                    "pontos": int(q_pontos),
                                }
                            )
                        else:
                            questions_payload.append(
                                {
                                    "id": qid,
                                    "tipo": "aberta",
                                    "enunciado": str(q_enunciado).strip(),
                                    "opcoes": [],
                                    "correta_idx": None,
                                    "pontos": int(q_pontos),
                                }
                            )

                    if st.form_submit_button("Publicar atividade", type="primary"):
                        if not str(titulo_atividade).strip():
                            st.error("Informe o titulo da atividade.")
                        elif validation_errors:
                            st.error(validation_errors[0])
                        else:
                            st.session_state["activities"].append(
                                {
                                    "id": uuid.uuid4().hex,
                                    "turma": turma_atividade,
                                    "tipo": str(tipo_atividade).strip(),
                                    "titulo": str(titulo_atividade).strip(),
                                    "descricao": str(descricao_atividade).strip(),
                                    "questions": questions_payload,
                                    "allow_resubmission": bool(allow_resubmission),
                                    "status": "Ativa",
                                    "autor": st.session_state.get("user_name", "Professor"),
                                    "due_date": due_date.strftime("%d/%m/%Y") if due_date else "",
                                    "created_at": datetime.datetime.now().strftime("%d/%m/%Y %H:%M"),
                                    "updated_at": "",
                                }
                            )
                            save_list(ACTIVITIES_FILE, st.session_state["activities"])
                            st.success("Atividade publicada com sucesso.")
                            st.rerun()

            atividades_prof = [
                a for a in st.session_state.get("activities", [])
                if str(a.get("turma", "")).strip() in set(turmas_prof)
            ]
            atividades_prof = sorted(
                atividades_prof,
                key=lambda a: (
                    0 if _is_activity_open(a) else 1,
                    parse_date(a.get("due_date", "")) or datetime.date(2100, 1, 1),
                    str(a.get("created_at", "")),
                ),
            )

            with tab_publicadas:
                if not atividades_prof:
                    st.info("Nenhuma atividade publicada ainda.")
                else:
                    for atividade in atividades_prof:
                        activity_id = str(atividade.get("id", "")).strip()
                        titulo = str(atividade.get("titulo", "Atividade")).strip() or "Atividade"
                        turma = str(atividade.get("turma", "")).strip()
                        tipo = str(atividade.get("tipo", "")).strip()
                        status = "Ativa" if _is_activity_open(atividade) else "Encerrada"
                        due_date = str(atividade.get("due_date", "")).strip() or "Sem prazo"
                        total_pontos = _activity_points_total(atividade)
                        total_submissoes = len(
                            [s for s in st.session_state.get("activity_submissions", []) if str(s.get("activity_id", "")).strip() == activity_id]
                        )
                        alunos_turma = [
                            s.get("nome", "")
                            for s in st.session_state.get("students", [])
                            if str(s.get("turma", "")).strip() == turma
                        ]

                        with st.expander(f"{titulo} | {turma} | {status}"):
                            st.caption(
                                f"Tipo: {tipo} | Prazo: {due_date} | Questoes: {len(atividade.get('questions', []) or [])} | Pontos: {total_pontos}"
                            )
                            st.caption(f"Respostas recebidas: {total_submissoes}/{len(alunos_turma)}")
                            if str(atividade.get("descricao", "")).strip():
                                st.write(str(atividade.get("descricao", "")).strip())

                            if _is_activity_open(atividade):
                                if st.button("Encerrar atividade", key=f"close_activity_{activity_id}"):
                                    atividade["status"] = "Encerrada"
                                    atividade["updated_at"] = datetime.datetime.now().strftime("%d/%m/%Y %H:%M")
                                    save_list(ACTIVITIES_FILE, st.session_state["activities"])
                                    st.success("Atividade encerrada.")
                                    st.rerun()
                            else:
                                if st.button("Reabrir atividade", key=f"open_activity_{activity_id}"):
                                    atividade["status"] = "Ativa"
                                    atividade["updated_at"] = datetime.datetime.now().strftime("%d/%m/%Y %H:%M")
                                    save_list(ACTIVITIES_FILE, st.session_state["activities"])
                                    st.success("Atividade reaberta.")
                                    st.rerun()

            with tab_respostas:
                if not atividades_prof:
                    st.info("Nenhuma atividade publicada para acompanhar respostas.")
                else:
                    atividade_labels = []
                    atividade_map = {}
                    for atividade in atividades_prof:
                        aid = str(atividade.get("id", "")).strip()
                        label = (
                            f"{str(atividade.get('turma', '')).strip()} | "
                            f"{str(atividade.get('tipo', '')).strip()} | "
                            f"{str(atividade.get('titulo', 'Atividade')).strip()} | "
                            f"#{aid[:6]}"
                        )
                        atividade_labels.append(label)
                        atividade_map[label] = atividade
                    atividade_sel_label = st.selectbox("Atividade", atividade_labels)
                    atividade_sel = atividade_map.get(atividade_sel_label, {})
                    aid_sel = str(atividade_sel.get("id", "")).strip()
                    turma_sel = str(atividade_sel.get("turma", "")).strip()
                    total_pontos = _activity_points_total(atividade_sel)
                    alunos_turma = [
                        s.get("nome", "")
                        for s in st.session_state.get("students", [])
                        if str(s.get("turma", "")).strip() == turma_sel
                    ]
                    submissions = [
                        s for s in st.session_state.get("activity_submissions", [])
                        if str(s.get("activity_id", "")).strip() == aid_sel
                    ]
                    submissions = sorted(submissions, key=lambda s: str(s.get("submitted_at", "")), reverse=True)

                    st.caption(f"Respostas recebidas: {len(submissions)}/{len(alunos_turma)}")
                    if not submissions:
                        st.info("Ainda nao ha respostas para esta atividade.")
                    else:
                        for sub in submissions:
                            sub_id = str(sub.get("id", "")).strip() or uuid.uuid4().hex
                            aluno = str(sub.get("aluno", "")).strip() or "Aluno"
                            nota_final = activity_submission_final_score(sub)
                            nota_auto = _parse_float(sub.get("score_auto", 0), 0.0)
                            nota_total = _parse_float(sub.get("score_total", total_pontos), 0.0)
                            status_sub = str(sub.get("status", "Enviada")).strip() or "Enviada"

                            st.markdown("---")
                            st.markdown(f"### {aluno}")
                            c1, c2, c3 = st.columns(3)
                            c1.metric("Status", status_sub)
                            c2.metric("Nota final", f"{nota_final:.1f}/{nota_total:.1f}")
                            c3.metric("Auto", f"{nota_auto:.1f}/{nota_total:.1f}")
                            st.caption(f"Enviado em: {str(sub.get('submitted_at', '')).strip() or '-'}")

                            with st.expander("Ver respostas"):
                                respostas = sub.get("respostas", []) or []
                                if not respostas:
                                    st.caption("Sem respostas registradas.")
                                for idx, resp in enumerate(respostas, start=1):
                                    enunciado = str(resp.get("enunciado", "")).strip()
                                    tipo_resp = str(resp.get("tipo", "")).strip()
                                    st.markdown(f"**{idx}. {enunciado or 'Questao'}**")
                                    if tipo_resp == "multipla_escolha":
                                        st.write(f"Resposta: {str(resp.get('resposta_texto', '')).strip() or '(nao respondida)'}")
                                        if resp.get("correta_idx", None) is not None:
                                            st.caption(
                                                "Correta: "
                                                + (str(resp.get("correta_texto", "")).strip() or "(nao definida)")
                                            )
                                            acertou = resp.get("acertou", None)
                                            if acertou is True:
                                                st.success("Resposta correta.")
                                            elif acertou is False:
                                                st.error("Resposta incorreta.")
                                    else:
                                        st.write(str(resp.get("resposta_texto", "")).strip() or "(nao respondida)")

                            with st.form(f"prof_grade_activity_{sub_id}"):
                                nota_default = activity_submission_final_score(sub)
                                nota_prof = st.number_input(
                                    "Nota final do professor",
                                    min_value=0.0,
                                    max_value=float(nota_total if nota_total > 0 else 100.0),
                                    value=float(min(max(nota_default, 0.0), nota_total if nota_total > 0 else 100.0)),
                                    step=0.5,
                                    key=f"prof_grade_value_{sub_id}",
                                )
                                feedback_prof = st.text_area(
                                    "Feedback para o aluno",
                                    value=str(sub.get("feedback_professor", "")).strip(),
                                    key=f"prof_grade_feedback_{sub_id}",
                                )
                                if st.form_submit_button("Salvar avaliacao"):
                                    sub["score_professor"] = float(nota_prof)
                                    sub["feedback_professor"] = str(feedback_prof).strip()
                                    sub["status"] = "Avaliada"
                                    sub["avaliado_em"] = datetime.datetime.now().strftime("%d/%m/%Y %H:%M")
                                    save_list(ACTIVITY_SUBMISSIONS_FILE, st.session_state["activity_submissions"])
                                    st.success("Avaliacao salva.")
                                    st.rerun()

    elif menu_prof == "Notas":
        st.markdown('<div class="main-header">Lancamento de Notas</div>', unsafe_allow_html=True)
        prof_nome = st.session_state["user_name"].strip().lower()
        turmas_prof = [
            c.get("nome") for c in st.session_state["classes"]
            if str(c.get("professor", "")).strip().lower() == prof_nome
        ]
        if not turmas_prof:
            st.info("Nenhuma turma atribuida a voce.")
        else:
            turma_nota = st.selectbox("Turma", turmas_prof, key="prof_turma_nota")
            alunos_turma = [s.get("nome") for s in st.session_state["students"] if s.get("turma") == turma_nota]
            if not alunos_turma:
                st.info("Nao ha alunos nessa turma para lancar nota.")
            else:
                with st.form("prof_launch_grades"):
                    aluno_nota = st.selectbox("Aluno", alunos_turma)
                    avaliacao_base = st.text_input("Avaliacao", value="Avaliacao mensal")
                    data_avaliacao = st.date_input("Data da avaliacao", value=datetime.date.today(), format="DD/MM/YYYY")
                    c_n1, c_n2, c_n3 = st.columns(3)
                    with c_n1:
                        nota_prova = st.number_input("Nota da prova", min_value=0.0, max_value=10.0, value=0.0, step=0.1)
                    with c_n2:
                        nota_conteudo = st.number_input("Nota de conteudo", min_value=0.0, max_value=10.0, value=0.0, step=0.1)
                    with c_n3:
                        nota_presenca = st.number_input("Presenca (%)", min_value=0, max_value=100, value=100, step=1)
                    observacao = st.text_area("Observacao (opcional)")

                    if st.form_submit_button("Enviar para analise do coordenador"):
                        data_txt = data_avaliacao.strftime("%d/%m/%Y") if data_avaliacao else datetime.date.today().strftime("%d/%m/%Y")
                        lancamentos = [
                            ("Nota da prova", f"{nota_prova:.1f}"),
                            ("Conteudo", f"{nota_conteudo:.1f}"),
                            ("Presenca", f"{nota_presenca}%"),
                        ]
                        for tipo, valor_nota in lancamentos:
                            st.session_state["grades"].append(
                                {
                                    "aluno": aluno_nota,
                                    "turma": turma_nota,
                                    "disciplina": "Ingles",
                                    "avaliacao": f"{avaliacao_base} - {tipo}",
                                    "nota": valor_nota,
                                    "status": "Pendente",
                                    "data": data_txt,
                                    "autor": st.session_state.get("user_name", "Professor"),
                                    "observacao": observacao.strip(),
                                }
                            )
                        save_list(GRADES_FILE, st.session_state["grades"])
                        st.success("Notas enviadas para analise do coordenador.")
                        st.rerun()

                pendentes_prof = [
                    g for g in st.session_state["grades"]
                    if g.get("turma") == turma_nota and g.get("status") == "Pendente"
                ]
                if pendentes_prof:
                    st.markdown("### Pendentes de aprovacao")
                    df_pend = pd.DataFrame(pendentes_prof)
                    col_order = [c for c in ["data", "aluno", "avaliacao", "nota", "status", "autor"] if c in df_pend.columns]
                    if col_order:
                        df_pend = df_pend[col_order]
                    st.dataframe(df_pend, use_container_width=True)
    elif menu_prof == "Livros":
        st.markdown('<div class="main-header">Biblioteca</div>', unsafe_allow_html=True)
        render_books_section(st.session_state.get("books", []), key_prefix="prof_livros")
    elif menu_prof == "Assistente IA":
        run_active_chatbot()

elif st.session_state["role"] == "Comercial":
    run_commercial_panel()

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
        coord_menu_options = [
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
            "Biblioteca",
            "Aprovação Notas",
            "Caixa de Entrada",
            "Desafios",
            "WhatsApp (Evolution)",
            "Backup",
            "Professor Wiz",
        ]
        coord_profile = str(st.session_state.get("account_profile") or st.session_state.get("role") or "")
        if coord_profile in ("Admin", "Coordenador"):
            insert_at = coord_menu_options.index("Backup")
            coord_menu_options.insert(insert_at, "ASSISTENTE WIZ")
        menu_coord_label = sidebar_menu("Administração", coord_menu_options, "menu_coord")
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
        "Biblioteca": "Livros",
        "Livros": "Livros",
        "Aprovação Notas": "Notas",
        "Caixa de Entrada": "Conteudos",
        "Conteúdos": "Conteudos",
        "Desafios": "Desafios",
        "WhatsApp (Evolution)": "WhatsApp",
        "ASSISTENTE WIZ": "Assistente Wiz",
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
                    dias_turma_default = turma_obj.get("dias_semana", [])
                    if isinstance(dias_turma_default, str):
                        dias_turma_default = [dias_turma_default]
                    dias_turma_default = [dia for dia in dias_turma_default if dia in WEEKDAY_OPTIONS_PT]
                    if not dias_turma_default:
                        dias_turma_default = infer_class_days_from_text(turma_obj.get("dias", ""))
                    titulo = st.text_input("Título", value="Aula ao vivo")
                    descricao = st.text_area("Descrição")
                    data_aula = st.date_input("Data", value=datetime.date.today(), format="DD/MM/YYYY")
                    st.caption(f"Data selecionada: {format_date_br(data_aula)}")
                    hora_padrao = parse_time(str(turma_obj.get("hora_inicio", "19:00")).strip() or "19:00")
                    hora_aula = st.time_input("Horário", value=hora_padrao)

                    rep_c1, rep_c2 = st.columns([2, 1])
                    with rep_c1:
                        repetir = st.checkbox("Repetir semanalmente", value=False)
                    with rep_c2:
                        repetir_por_data = st.checkbox("Data", value=False, disabled=not repetir, help="Selecionar dias para repetição")

                    semanas = st.number_input("Número de semanas", min_value=1, max_value=52, value=4, disabled=not repetir)
                    dias_repeticao = []
                    if repetir and repetir_por_data:
                        dia_base = WEEKDAY_OPTIONS_PT[data_aula.weekday()] if data_aula else WEEKDAY_OPTIONS_PT[0]
                        default_days = dias_turma_default or [dia_base]
                        dias_repeticao = st.multiselect(
                            "Dias para repetir as aulas",
                            WEEKDAY_OPTIONS_PT,
                            default=default_days,
                        )

                    st.text_input("Professor", value=prof_default, disabled=True)
                    st.text_input("Link da aula", value=link_default, disabled=True)
                    professor = str(prof_default).strip()
                    link_aula = str(link_default).strip()
                    enviar_email_convite = st.checkbox("Enviar email automatico para alunos da turma", value=True)
                    if st.form_submit_button("Agendar aula"):
                        if repetir and repetir_por_data and not dias_repeticao:
                            st.error("Selecione pelo menos um dia para repetição por data.")
                        else:
                            datas_aulas = []
                            if repetir:
                                total_semanas = int(semanas)
                                if repetir_por_data:
                                    dias_idx = {weekday_index_from_label(dia) for dia in dias_repeticao}
                                    dias_idx = {d for d in dias_idx if d is not None}
                                    inicio_periodo = data_aula
                                    fim_periodo = data_aula + datetime.timedelta(weeks=total_semanas) - datetime.timedelta(days=1)
                                    cursor = inicio_periodo
                                    while cursor <= fim_periodo:
                                        if cursor.weekday() in dias_idx:
                                            datas_aulas.append(cursor)
                                        cursor += datetime.timedelta(days=1)
                                    if not datas_aulas and data_aula:
                                        datas_aulas = [data_aula]
                                else:
                                    datas_aulas = [data_aula + datetime.timedelta(weeks=i) for i in range(total_semanas)] if data_aula else []
                            elif data_aula:
                                datas_aulas = [data_aula]
                            datas_aulas = sorted(list({d for d in datas_aulas if d}))

                            recorrencia = ""
                            if repetir and repetir_por_data and dias_repeticao:
                                recorrencia = f"Semanal ({', '.join(dias_repeticao)})"
                            elif repetir:
                                recorrencia = "Semanal"

                            novos_itens = []
                            for data_item in datas_aulas:
                                agenda_item = {
                                    "turma": turma_sel,
                                    "professor": professor.strip(),
                                    "titulo": titulo.strip() or "Aula ao vivo",
                                    "descricao": descricao.strip(),
                                    "data": data_item.strftime("%d/%m/%Y") if data_item else "",
                                    "hora": hora_aula.strftime("%H:%M") if hora_aula else "",
                                    "link": link_aula.strip(),
                                    "recorrencia": recorrencia,
                                }
                                agenda_item["google_calendar_link"] = build_google_calendar_event_link(agenda_item)
                                st.session_state["agenda"].append(agenda_item)
                                novos_itens.append(agenda_item)

                            save_list(AGENDA_FILE, st.session_state["agenda"])
                            if novos_itens:
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
                                notif_stats = {"email_total": 0, "email_ok": 0, "whatsapp_total": 0, "whatsapp_ok": 0}
                                if enviar_email_convite:
                                    notif_stats = email_students_by_turma(turma_sel, assunto, corpo, "Agenda")
                                st.info(
                                    "Disparos da agenda: "
                                    f"E-mail {notif_stats.get('email_ok', 0)}/{notif_stats.get('email_total', 0)} | "
                                    f"WhatsApp {notif_stats.get('whatsapp_ok', 0)}/{notif_stats.get('whatsapp_total', 0)}."
                                )
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
                        if wiz_event_enabled("on_class_link_updated"):
                            assunto = f"[Active] Link atualizado - Turma {turma_sel}"
                            corpo = (
                                f"O link da aula da turma {turma_sel} foi atualizado.\n\n"
                                f"Novo link: {novo_link}"
                            )
                            notif_stats = email_students_by_turma(turma_sel, assunto, corpo, "Links")
                            st.info(
                                "Disparos do link: "
                                f"E-mail {notif_stats.get('email_ok', 0)}/{notif_stats.get('email_total', 0)} | "
                                f"WhatsApp {notif_stats.get('whatsapp_ok', 0)}/{notif_stats.get('whatsapp_total', 0)}."
                            )
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
        st.markdown('<div class="main-header">Biblioteca</div>', unsafe_allow_html=True)
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
                    st.success("Biblioteca atualizada!")

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
                    st.caption("Importa um Excel no padrão do modelo.")
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
                                        f"Importação concluída: {added} adicionados, {updated} atualizados, {skipped} ignorados."
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
                _sfk("add_student_genero"): "Masculino",
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
                _sfk("add_student_complemento"): "",
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

            genero_key = _sfk("add_student_genero")
            if st.session_state.get(genero_key) not in ("Masculino", "Feminino"):
                st.session_state[genero_key] = "Masculino"

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

                c7, c8, c9, c10 = st.columns(4)
                with c7: cpf = st.text_input("CPF", key=_sfk("add_student_cpf"))
                with c8: natal = st.text_input("Cidade Natal", key=_sfk("add_student_natal"))
                with c9: pais = st.text_input("Pais de Origem", key=_sfk("add_student_pais"))
                with c10: genero = st.selectbox("Sexo", ["Masculino", "Feminino"], key=genero_key)

                st.divider()
                st.markdown("### Endereco")
                ce1, ce2, ce3 = st.columns(3)
                with ce1: cep = st.text_input("CEP", key=_sfk("add_student_cep"))
                with ce2: cidade = st.text_input("Cidade", key=_sfk("add_student_cidade"))
                with ce3: bairro = st.text_input("Bairro", key=_sfk("add_student_bairro"))

                ce4, ce5, ce6 = st.columns([3, 1, 2])
                with ce4: rua = st.text_input("Rua", key=_sfk("add_student_rua"))
                with ce5: numero = st.text_input("Numero", key=_sfk("add_student_numero"))
                with ce6: complemento = st.text_input("Observacao (Apto, Bloco, Casa)", key=_sfk("add_student_complemento"))

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
                            "genero": genero,
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
                            "complemento": complemento,
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

                        turma_link = str(turma_obj.get("link_zoom", "")).strip() if isinstance(turma_obj, dict) else ""
                        portal_url = _student_portal_url()
                        login_info = login_aluno or "Nao informado"
                        senha_info = senha_aluno or "Nao informada"
                        assunto_auto = "[Active] Boas-vindas e acesso inicial"
                        corpo_auto = (
                            f"Ola, {nome}! Seja muito bem-vindo(a) a Mister Wiz! \U0001F389\n\n"
                            f"Seu cadastro foi concluido no Active.\n"
                            f"Turma: {turma}\n"
                            f"Livro/Nivel: {livro_final or 'A definir'}\n"
                            f"Matricula: {matricula_final}\n"
                            f"Login: {login_info}\n"
                            f"Senha: {senha_info}\n"
                        )
                        if portal_url:
                            corpo_auto += f"Portal do aluno: {portal_url}\n"
                        if turma_link:
                            corpo_auto += f"Link da aula: {turma_link}\n"
                        corpo_auto += (
                            "\nFinanceiro, boletos e materiais ficam disponiveis no portal do aluno.\n"
                            "Em caso de duvidas, responda esta mensagem."
                        )
                        notify_stats = {"email_total": 0, "email_ok": 0, "whatsapp_total": 0, "whatsapp_ok": 0}
                        if wiz_event_enabled("on_student_created"):
                            notify_stats = _notify_direct_contacts(
                                nome,
                                _message_recipients_for_student(novo_aluno),
                                _student_whatsapp_recipients(novo_aluno),
                                assunto_auto,
                                corpo_auto,
                                "Cadastro Aluno",
                            )
                        st.session_state["add_student_feedback"] = {
                            "success": "Cadastro realizado com sucesso!",
                            "info": (
                                "Disparos automáticos: "
                                f"E-mail {notify_stats.get('email_ok', 0)}/{notify_stats.get('email_total', 0)} | "
                                f"WhatsApp {notify_stats.get('whatsapp_ok', 0)}/{notify_stats.get('whatsapp_total', 0)}."
                            ),
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
                        generos = ["Masculino", "Feminino"]
                        genero_atual = str(aluno_obj.get("genero", "Masculino")).strip()
                        if genero_atual not in generos:
                            genero_atual = "Masculino"
                        new_genero = st.radio(
                            "Sexo",
                            generos,
                            index=generos.index(genero_atual),
                            horizontal=True,
                            key=f"edit_student_genero_{aluno_sel}",
                        )

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
                                    aluno_obj["genero"] = new_genero
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
                c_email, c_cel = st.columns(2)
                with c_email: email_prof = st.text_input("E-mail do Professor")
                with c_cel: celular_prof = st.text_input("Celular/WhatsApp do Professor")

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
                                "email": email_prof.strip().lower(),
                                "celular": celular_prof.strip(),
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
                                    "email": email_prof.strip().lower(),
                                    "celular": celular_prof.strip(),
                                }
                            )
                            save_users(st.session_state["users"])
                        if wiz_event_enabled("on_teacher_created"):
                            _notify_direct_contacts(
                                nome or "Professor",
                                [email_prof],
                                [celular_prof],
                                "[Active] Cadastro de professor concluído",
                                "Seu acesso de professor foi cadastrado no Active. Em caso de dúvidas, procure a coordenação.",
                                "Cadastro Professor",
                            )
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
                        ec1, ec2 = st.columns(2)
                        with ec1: new_email = st.text_input("E-mail", value=prof_obj.get("email", ""))
                        with ec2: new_cel = st.text_input("Celular/WhatsApp", value=prof_obj.get("celular", ""))

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
                                    prof_obj["email"] = new_email.strip().lower()
                                    prof_obj["celular"] = new_cel.strip()
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
                with c3: dias_semana = st.multiselect("Dias das aulas", WEEKDAY_OPTIONS_PT)
                with c4: link = st.text_input("Link do Zoom (Inicial)")

                c5, c6 = st.columns(2)
                with c5: hora_inicio = st.time_input("Horário inicial", value=datetime.time(19, 0))
                with c6: hora_fim = st.time_input("Horário final", value=datetime.time(20, 0))

                livro = st.selectbox("Livro/Nível da Turma", book_levels())
                if st.form_submit_button("Cadastrar"):
                    nome = nome.strip()
                    dias_semana = [dia for dia in dias_semana if dia in WEEKDAY_OPTIONS_PT]
                    hora_inicio_str = hora_inicio.strftime("%H:%M") if hora_inicio else ""
                    hora_fim_str = hora_fim.strftime("%H:%M") if hora_fim else ""

                    if not nome:
                        st.error("Informe o nome da turma.")
                    elif not dias_semana:
                        st.error("Selecione pelo menos um dia das aulas.")
                    elif hora_fim <= hora_inicio:
                        st.error("O horário final precisa ser maior que o horário inicial.")
                    else:
                        st.session_state["classes"].append(
                            {
                                "nome": nome,
                                "professor": prof,
                                "modulo": modulo,
                                "dias": format_class_schedule(dias_semana, hora_inicio_str, hora_fim_str),
                                "dias_semana": dias_semana,
                                "hora_inicio": hora_inicio_str,
                                "hora_fim": hora_fim_str,
                                "link_zoom": link.strip(),
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

                        dias_salvos = turma_obj.get("dias_semana", [])
                        if isinstance(dias_salvos, str):
                            dias_salvos = [dias_salvos]
                        dias_salvos = [dia for dia in dias_salvos if dia in WEEKDAY_OPTIONS_PT]
                        if not dias_salvos:
                            dias_salvos = infer_class_days_from_text(turma_obj.get("dias", ""))

                        hora_inicio_atual = str(turma_obj.get("hora_inicio", "")).strip()
                        hora_fim_atual = str(turma_obj.get("hora_fim", "")).strip()
                        if not hora_inicio_atual or not hora_fim_atual:
                            horarios_texto = re.findall(r"\b\d{1,2}:\d{2}\b", str(turma_obj.get("dias", "")))
                            if not hora_inicio_atual and horarios_texto:
                                hora_inicio_atual = horarios_texto[0]
                            if not hora_fim_atual and len(horarios_texto) > 1:
                                hora_fim_atual = horarios_texto[1]

                        hora_inicio_padrao = parse_time(hora_inicio_atual or "19:00")
                        hora_fim_padrao = parse_time(hora_fim_atual or "20:00")

                        c_dias_1, c_dias_2 = st.columns(2)
                        with c_dias_1:
                            new_dias_semana = st.multiselect("Dias das aulas", WEEKDAY_OPTIONS_PT, default=dias_salvos)
                        with c_dias_2:
                            new_link = st.text_input("Link do Zoom", value=turma_obj.get("link_zoom", ""))

                        c_hora_1, c_hora_2 = st.columns(2)
                        with c_hora_1:
                            new_hora_inicio = st.time_input("Horário inicial", value=hora_inicio_padrao, key=f"edit_class_hora_inicio_{turma_sel}")
                        with c_hora_2:
                            new_hora_fim = st.time_input("Horário final", value=hora_fim_padrao, key=f"edit_class_hora_fim_{turma_sel}")

                        livro_atual = turma_obj.get("livro", "")
                        livro_opts = book_levels()
                        if livro_atual and livro_atual not in livro_opts:
                            livro_opts.append(livro_atual)
                        new_livro = st.selectbox("Livro/Nível da Turma", livro_opts, index=livro_opts.index(livro_atual) if livro_atual in livro_opts else 0)

                        c_edit, c_del = st.columns([1, 1])
                        with c_edit:
                            if st.form_submit_button("Salvar Alterações"):
                                new_nome = new_nome.strip()
                                dias_limpos = [dia for dia in new_dias_semana if dia in WEEKDAY_OPTIONS_PT]
                                new_hora_inicio_str = new_hora_inicio.strftime("%H:%M") if new_hora_inicio else ""
                                new_hora_fim_str = new_hora_fim.strftime("%H:%M") if new_hora_fim else ""

                                if not new_nome:
                                    st.error("Informe o nome da turma.")
                                elif not dias_limpos:
                                    st.error("Selecione pelo menos um dia das aulas.")
                                elif new_hora_fim <= new_hora_inicio:
                                    st.error("O horário final precisa ser maior que o horário inicial.")
                                else:
                                    old_nome = turma_obj.get("nome", "")
                                    turma_obj["nome"] = new_nome
                                    turma_obj["professor"] = new_prof
                                    turma_obj["modulo"] = new_modulo
                                    turma_obj["dias"] = format_class_schedule(dias_limpos, new_hora_inicio_str, new_hora_fim_str)
                                    turma_obj["dias_semana"] = dias_limpos
                                    turma_obj["hora_inicio"] = new_hora_inicio_str
                                    turma_obj["hora_fim"] = new_hora_fim_str
                                    turma_obj["link_zoom"] = new_link.strip()
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
        def _parse_parcela_info(parcela_txt):
            parcela_str = str(parcela_txt or "").strip()
            atual = 1
            total = 1
            if "/" in parcela_str:
                parte_atual, parte_total = parcela_str.split("/", 1)
                atual = max(1, parse_int(parte_atual) or 1)
                total = max(1, parse_int(parte_total) or 1)
            else:
                atual = max(1, parse_int(parcela_str) or 1)
                total = atual
            return atual, total

        tab1, tab2, tab3 = st.tabs(["Contas a Receber", "Contas a Pagar", "Aprovacoes Comercial"])
        with tab1:
            with st.form("add_rec"):
                st.markdown("### Lançar Recebimento")
                c1, c2, c3, c4 = st.columns(4)
                with c1: desc = st.text_input("Descricao (Ex: Mensalidade)")
                with c2: val = st.text_input("Valor total (Ex: 150,00)")
                with c3: categoria = st.selectbox("Categoria", ["Mensalidade", "Material", "Taxa de Matricula"])
                with c4:
                    categoria_lancamento = st.selectbox(
                        "Categoria do lancamento",
                        ["Aluno", "Fornecedor", "Professor", "Interno", "Outro"],
                    )
                alunos_opts = [s.get("nome", "") for s in st.session_state["students"] if s.get("nome")]
                if categoria_lancamento == "Aluno":
                    if alunos_opts:
                        aluno = st.selectbox("Aluno", alunos_opts)
                    else:
                        aluno = ""
                        st.info("Nenhum aluno cadastrado para lancar recebimento.")
                else:
                    ref_label = {
                        "Fornecedor": "Fornecedor",
                        "Professor": "Professor",
                        "Interno": "Setor interno",
                        "Outro": "Referencia",
                    }.get(categoria_lancamento, "Referencia")
                    aluno = st.text_input(f"{ref_label} *")
                c4, c5, c6 = st.columns(3)
                with c4: data_lanc = st.date_input("Data do lançamento", value=datetime.date.today(), format="DD/MM/YYYY")
                with c5: venc = st.date_input("Primeiro vencimento", value=datetime.date.today(), format="DD/MM/YYYY")
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
                c7, c8 = st.columns(2)
                is_material = categoria == "Material"
                with c7:
                    parcela_inicial = st.number_input("Parcela inicial", min_value=1, step=1, value=1, disabled=is_material)
                material_parcelado = categoria == "Material" and material_payment in ("Parcelado no Cartao", "Parcelado no Boleto")
                if categoria == "Mensalidade":
                    gerar_12 = st.checkbox("Gerar mensalidades em serie", value=True)
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

                if categoria == "Mensalidade" and not gerar_12:
                    qtd_parcelas_calc = 1
                elif categoria == "Material" and not material_parcelado:
                    qtd_parcelas_calc = 1
                else:
                    qtd_parcelas_calc = max(1, int(qtd_meses))

                valor_total_num = parse_money(val)
                valor_parcela_num = (valor_total_num / qtd_parcelas_calc) if valor_total_num > 0 else 0.0
                valor_parcela_auto = f"{valor_parcela_num:.2f}".replace(".", ",")
                with c8:
                    st.text_input("Valor da parcela (automatico)", value=valor_parcela_auto, disabled=True, key="rec_valor_parcela_auto")

                if st.form_submit_button("Lancar"):
                    if not str(aluno).strip() or valor_total_num <= 0:
                        st.error("Informe referencia e valor total valido.")
                    else:
                        before_count = len(st.session_state.get("receivables", []))
                        total_lancados = 0
                        if categoria == "Mensalidade" and gerar_12:
                            for i in range(qtd_parcelas_calc):
                                data_venc = add_months(venc, i)
                                parcela = f"{parcela_inicial + i}/{qtd_parcelas_calc}"
                                add_receivable(
                                    aluno,
                                    desc,
                                    val,
                                    data_venc,
                                    cobranca,
                                    categoria,
                                    data_lancamento=data_lanc,
                                    valor_parcela=valor_parcela_auto,
                                    parcela=parcela,
                                    categoria_lancamento=categoria_lancamento,
                                )
                                total_lancados += 1
                            st.success(f"Mensalidades lancadas! ({total_lancados} parcelas)")
                        elif categoria == "Material":
                            qtd_material = qtd_parcelas_calc
                            for i in range(qtd_material):
                                data_venc = add_months(venc, i)
                                parcela = f"{1 + i}/{qtd_material}" if qtd_material > 1 else "1"
                                add_receivable(
                                    aluno,
                                    desc or "Material",
                                    val,
                                    data_venc,
                                    cobranca,
                                    categoria,
                                    data_lancamento=data_lanc,
                                    valor_parcela=valor_parcela_auto,
                                    parcela=parcela,
                                    categoria_lancamento=categoria_lancamento,
                                )
                                total_lancados += 1
                            st.success(f"Material lancado com parcelamento em {qtd_material}x.")
                        else:
                            for i in range(qtd_parcelas_calc):
                                data_venc = add_months(venc, i) if qtd_parcelas_calc > 1 else venc
                                parcela = f"{parcela_inicial + i}/{qtd_parcelas_calc}" if qtd_parcelas_calc > 1 else str(parcela_inicial)
                                add_receivable(
                                    aluno,
                                    desc,
                                    val,
                                    data_venc,
                                    cobranca,
                                    categoria,
                                    data_lancamento=data_lanc,
                                    valor_parcela=valor_parcela_auto,
                                    parcela=parcela,
                                    categoria_lancamento=categoria_lancamento,
                                )
                                total_lancados += 1
                            st.success(f"Lancado! ({total_lancados} parcela(s))")
                        if wiz_event_enabled("on_financial_created") and categoria_lancamento == "Aluno":
                            new_items = st.session_state.get("receivables", [])[before_count:]
                            stats_fin = notify_student_financial_event(aluno, new_items)
                            st.info(
                                "Disparos financeiros: "
                                f"E-mail {stats_fin.get('email_ok', 0)}/{stats_fin.get('email_total', 0)} | "
                                f"WhatsApp {stats_fin.get('whatsapp_ok', 0)}/{stats_fin.get('whatsapp_total', 0)}."
                            )
            st.markdown("### Recebimentos")
            recebimentos = st.session_state["receivables"]
            c_f1, c_f2, c_f3, c_f4, c_f5 = st.columns(5)
            with c_f1:
                status_opts = ["Todos"] + sorted({r.get("status", "") for r in recebimentos if r.get("status")})
                status_sel = st.selectbox("Status", status_opts)
            with c_f2:
                cat_opts = ["Todos"] + sorted({r.get("categoria", "") for r in recebimentos if r.get("categoria")})
                cat_sel = st.selectbox("Categoria", cat_opts)
            with c_f3:
                cat_lanc_opts = ["Todos"] + sorted({r.get("categoria_lancamento", "Aluno") for r in recebimentos if r.get("categoria_lancamento", "Aluno")})
                cat_lanc_sel = st.selectbox("Categoria do lancamento", cat_lanc_opts)
            with c_f4:
                aluno_opts = ["Todos"] + sorted({r.get("aluno", "") for r in recebimentos if r.get("aluno")})
                aluno_sel = st.selectbox("Aluno/Referencia", aluno_opts)
            with c_f5:
                item_opts = ["Todos"] + sorted({r.get("item_codigo", "") for r in recebimentos if r.get("item_codigo")})
                item_sel = st.selectbox("Item (Codigo)", item_opts)
            busca = st.text_input("Buscar por descrição")

            recebimentos_filtrados = recebimentos
            if status_sel != "Todos":
                recebimentos_filtrados = [r for r in recebimentos_filtrados if r.get("status") == status_sel]
            if cat_sel != "Todos":
                recebimentos_filtrados = [r for r in recebimentos_filtrados if r.get("categoria") == cat_sel]
            if cat_lanc_sel != "Todos":
                recebimentos_filtrados = [r for r in recebimentos_filtrados if r.get("categoria_lancamento", "Aluno") == cat_lanc_sel]
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
                    "categoria_lancamento",
                    "item_codigo",
                    "valor_parcela",
                    "parcela",
                    "vencimento",
                    "status",
                    "cobranca",
                ]
                df_rec = df_rec[[c for c in col_order if c in df_rec.columns]]
                st.dataframe(df_rec, use_container_width=True)
            else:
                st.info("Nenhum recebimento encontrado.")

            st.markdown("### Gerenciamento de Recebimentos")
            if not recebimentos:
                st.info("Nenhum recebimento para gerenciar.")
            else:
                opcoes_rec = [
                    f"{r.get('codigo','')} | {r.get('aluno','')} | {r.get('descricao','')} | Venc: {r.get('vencimento','')}"
                    for r in recebimentos
                ]
                idx_rec = st.selectbox(
                    "Selecione o recebimento",
                    list(range(len(recebimentos))),
                    format_func=lambda i: opcoes_rec[i],
                    key="manage_rec_idx",
                )
                rec_obj = recebimentos[idx_rec]
                parcela_atual_rec, qtd_atual_rec = _parse_parcela_info(rec_obj.get("parcela", "1/1"))
                venc_atual_rec = parse_date(rec_obj.get("vencimento", "")) or datetime.date.today()

                categoria_opts_rec = ["Mensalidade", "Material", "Taxa de Matricula"]
                if rec_obj.get("categoria", "") and rec_obj.get("categoria", "") not in categoria_opts_rec:
                    categoria_opts_rec.append(rec_obj.get("categoria", ""))

                cat_lanc_opts_rec = ["Aluno", "Fornecedor", "Professor", "Interno", "Outro"]
                if rec_obj.get("categoria_lancamento", "") and rec_obj.get("categoria_lancamento", "") not in cat_lanc_opts_rec:
                    cat_lanc_opts_rec.append(rec_obj.get("categoria_lancamento", ""))

                cobranca_opts_rec = ["Boleto", "Pix", "Cartao", "Dinheiro", "A vista", "Parcelado no Cartao", "Parcelado no Boleto"]
                if rec_obj.get("cobranca", "") and rec_obj.get("cobranca", "") not in cobranca_opts_rec:
                    cobranca_opts_rec.append(rec_obj.get("cobranca", ""))

                status_opts_rec = ["Aberto", "Pago", "Cancelado"]
                if rec_obj.get("status", "") and rec_obj.get("status", "") not in status_opts_rec:
                    status_opts_rec.append(rec_obj.get("status", ""))

                with st.form("manage_rec_form"):
                    mr1, mr2, mr3 = st.columns(3)
                    with mr1:
                        new_desc_rec = st.text_input("Descricao", value=str(rec_obj.get("descricao", "")))
                    with mr2:
                        new_val_total_rec = st.text_input("Valor total", value=str(rec_obj.get("valor", rec_obj.get("valor_parcela", ""))))
                    with mr3:
                        new_qtd_rec = st.number_input("Quantidade de parcelas", min_value=1, max_value=24, value=int(max(1, qtd_atual_rec)), step=1)

                    mr4, mr5, mr6 = st.columns(3)
                    with mr4:
                        new_ref_rec = st.text_input("Aluno/Referencia", value=str(rec_obj.get("aluno", "")))
                    with mr5:
                        cat_rec = str(rec_obj.get("categoria", "Mensalidade"))
                        new_cat_rec = st.selectbox(
                            "Categoria",
                            categoria_opts_rec,
                            index=categoria_opts_rec.index(cat_rec) if cat_rec in categoria_opts_rec else 0,
                        )
                    with mr6:
                        cat_lanc_rec = str(rec_obj.get("categoria_lancamento", "Aluno"))
                        new_cat_lanc_rec = st.selectbox(
                            "Categoria do lancamento",
                            cat_lanc_opts_rec,
                            index=cat_lanc_opts_rec.index(cat_lanc_rec) if cat_lanc_rec in cat_lanc_opts_rec else 0,
                        )

                    mr7, mr8, mr9 = st.columns(3)
                    with mr7:
                        new_venc_rec = st.date_input("Vencimento", value=venc_atual_rec, format="DD/MM/YYYY")
                    with mr8:
                        cob_rec = str(rec_obj.get("cobranca", "Boleto"))
                        new_cobranca_rec = st.selectbox(
                            "Cobranca",
                            cobranca_opts_rec,
                            index=cobranca_opts_rec.index(cob_rec) if cob_rec in cobranca_opts_rec else 0,
                        )
                    with mr9:
                        stat_rec = str(rec_obj.get("status", "Aberto"))
                        new_status_rec = st.selectbox(
                            "Status",
                            status_opts_rec,
                            index=status_opts_rec.index(stat_rec) if stat_rec in status_opts_rec else 0,
                        )

                    new_val_total_num = parse_money(new_val_total_rec)
                    new_qtd_rec_int = max(1, int(new_qtd_rec))
                    new_valor_parcela_rec = f"{(new_val_total_num / new_qtd_rec_int):.2f}".replace(".", ",") if new_val_total_num > 0 else "0,00"
                    st.text_input("Valor da parcela (automatico)", value=new_valor_parcela_rec, disabled=True, key="rec_edit_valor_parcela_auto")

                    mc1, mc2 = st.columns(2)
                    with mc1:
                        salvar_rec = st.form_submit_button("Salvar alteracoes")
                    with mc2:
                        excluir_rec = st.form_submit_button("Excluir recebimento", type="primary")

                    if salvar_rec:
                        if not new_ref_rec.strip() or new_val_total_num <= 0:
                            st.error("Informe referencia e valor total valido.")
                        else:
                            rec_obj["descricao"] = new_desc_rec.strip() or rec_obj.get("descricao", "Mensalidade")
                            rec_obj["aluno"] = new_ref_rec.strip()
                            rec_obj["categoria"] = new_cat_rec
                            rec_obj["categoria_lancamento"] = new_cat_lanc_rec
                            rec_obj["cobranca"] = new_cobranca_rec
                            rec_obj["valor"] = new_val_total_rec.strip()
                            rec_obj["valor_parcela"] = new_valor_parcela_rec
                            rec_obj["vencimento"] = new_venc_rec.strftime("%d/%m/%Y")
                            rec_obj["status"] = new_status_rec
                            rec_obj["parcela"] = f"{parcela_atual_rec}/{new_qtd_rec_int}" if new_qtd_rec_int > 1 else str(parcela_atual_rec)
                            rec_obj["numero_pedido"] = ""
                            save_list(RECEIVABLES_FILE, st.session_state["receivables"])
                            st.success("Recebimento atualizado!")
                            st.rerun()

                    if excluir_rec:
                        st.session_state["receivables"].remove(rec_obj)
                        save_list(RECEIVABLES_FILE, st.session_state["receivables"])
                        st.success("Recebimento excluido.")
                        st.rerun()

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
                                    item_codigo=item_codigo,
                                    categoria_lancamento="Aluno",
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
                st.markdown("### Lancar Despesa")
                c1, c2, c3 = st.columns(3)
                with c1:
                    desc = st.text_input("Descricao")
                with c2:
                    val = st.text_input("Valor total")
                with c3:
                    categoria_lancamento_pag = st.selectbox(
                        "Categoria do lancamento",
                        ["Fornecedor", "Professor", "Interno", "Aluno", "Outro"],
                    )
                ref_pag = {
                    "Fornecedor": "Fornecedor",
                    "Professor": "Professor",
                    "Interno": "Setor interno",
                    "Aluno": "Aluno",
                    "Outro": "Referencia",
                }.get(categoria_lancamento_pag, "Referencia")
                c4, c5, c6 = st.columns(3)
                with c4:
                    forn = st.text_input(f"{ref_pag}")
                with c5:
                    data_pag = st.date_input("Data do lancamento", value=datetime.date.today(), format="DD/MM/YYYY")
                with c6:
                    venc_pag = st.date_input("Primeiro vencimento", value=datetime.date.today(), format="DD/MM/YYYY")

                c7, c8, c9 = st.columns(3)
                with c7:
                    qtd_pag = st.number_input("Quantidade de parcelas", min_value=1, max_value=24, value=1, step=1)
                val_total_pag_num = parse_money(val)
                qtd_pag_int = max(1, int(qtd_pag))
                valor_parcela_pag = f"{(val_total_pag_num / qtd_pag_int):.2f}".replace(".", ",") if val_total_pag_num > 0 else "0,00"
                with c8:
                    st.text_input("Valor da parcela (automatico)", value=valor_parcela_pag, disabled=True, key="pag_valor_parcela_auto")
                with c9:
                    numero_pedido_pag = st.text_input("Numero do pedido")

                c10, c11 = st.columns(2)
                with c10:
                    cobranca_pag = st.selectbox("Forma de pagamento", ["Boleto", "Pix", "Cartao", "Dinheiro", "Transferencia"])
                with c11:
                    status_pag = st.selectbox("Status", ["Aberto", "Pago"])

                if st.form_submit_button("Lancar"):
                    if not desc.strip() or not forn.strip() or val_total_pag_num <= 0:
                        st.error("Informe descricao, referencia e valor total valido.")
                    else:
                        for i in range(qtd_pag_int):
                            venc_item = add_months(venc_pag, i) if qtd_pag_int > 1 else venc_pag
                            parcela_txt = f"{1 + i}/{qtd_pag_int}" if qtd_pag_int > 1 else "1"
                            st.session_state["payables"].append(
                                {
                                    "codigo": f"PAG-{uuid.uuid4().hex[:8].upper()}",
                                    "descricao": desc.strip(),
                                    "valor": val.strip(),
                                    "valor_parcela": valor_parcela_pag,
                                    "parcela": parcela_txt,
                                    "fornecedor": forn.strip(),
                                    "categoria_lancamento": categoria_lancamento_pag,
                                    "numero_pedido": numero_pedido_pag.strip(),
                                    "data": data_pag.strftime("%d/%m/%Y"),
                                    "vencimento": venc_item.strftime("%d/%m/%Y"),
                                    "cobranca": cobranca_pag,
                                    "status": status_pag,
                                }
                            )
                        save_list(PAYABLES_FILE, st.session_state["payables"])
                        st.success(f"Despesa lancada! ({qtd_pag_int} parcela(s))")

            st.markdown("### Despesas")
            despesas = st.session_state["payables"]
            if despesas:
                df_pag = pd.DataFrame(despesas)
                col_order_pag = [
                    "codigo",
                    "data",
                    "fornecedor",
                    "descricao",
                    "categoria_lancamento",
                    "numero_pedido",
                    "valor_parcela",
                    "parcela",
                    "vencimento",
                    "status",
                    "cobranca",
                ]
                df_pag = df_pag[[c for c in col_order_pag if c in df_pag.columns]]
                st.dataframe(df_pag, use_container_width=True)
            else:
                st.info("Nenhuma conta a pagar cadastrada.")

            st.markdown("### Gerenciamento de Despesas")
            if not despesas:
                st.info("Nenhuma despesa para gerenciar.")
            else:
                opcoes_pag = [
                    f"{p.get('codigo','')} | {p.get('fornecedor','')} | {p.get('descricao','')} | Venc: {p.get('vencimento','')}"
                    for p in despesas
                ]
                idx_pag = st.selectbox(
                    "Selecione a despesa",
                    list(range(len(despesas))),
                    format_func=lambda i: opcoes_pag[i],
                    key="manage_pag_idx",
                )
                pag_obj = despesas[idx_pag]
                parcela_atual_pag, qtd_atual_pag = _parse_parcela_info(pag_obj.get("parcela", "1/1"))
                data_atual_pag = parse_date(pag_obj.get("data", "")) or datetime.date.today()
                venc_atual_pag = parse_date(pag_obj.get("vencimento", "")) or datetime.date.today()

                cat_lanc_opts_pag = ["Fornecedor", "Professor", "Interno", "Aluno", "Outro"]
                if pag_obj.get("categoria_lancamento", "") and pag_obj.get("categoria_lancamento", "") not in cat_lanc_opts_pag:
                    cat_lanc_opts_pag.append(pag_obj.get("categoria_lancamento", ""))

                cobranca_opts_pag = ["Boleto", "Pix", "Cartao", "Dinheiro", "Transferencia"]
                if pag_obj.get("cobranca", "") and pag_obj.get("cobranca", "") not in cobranca_opts_pag:
                    cobranca_opts_pag.append(pag_obj.get("cobranca", ""))

                status_opts_pag = ["Aberto", "Pago", "Cancelado"]
                if pag_obj.get("status", "") and pag_obj.get("status", "") not in status_opts_pag:
                    status_opts_pag.append(pag_obj.get("status", ""))

                with st.form("manage_pag_form"):
                    mp1, mp2, mp3 = st.columns(3)
                    with mp1:
                        new_desc_pag = st.text_input("Descricao", value=str(pag_obj.get("descricao", "")))
                    with mp2:
                        new_val_total_pag = st.text_input("Valor total", value=str(pag_obj.get("valor", pag_obj.get("valor_parcela", ""))))
                    with mp3:
                        new_qtd_pag = st.number_input("Quantidade de parcelas", min_value=1, max_value=24, value=int(max(1, qtd_atual_pag)), step=1)

                    mp4, mp5, mp6 = st.columns(3)
                    with mp4:
                        new_forn_pag = st.text_input("Fornecedor/Referencia", value=str(pag_obj.get("fornecedor", "")))
                    with mp5:
                        cat_pag = str(pag_obj.get("categoria_lancamento", "Fornecedor"))
                        new_cat_pag = st.selectbox(
                            "Categoria do lancamento",
                            cat_lanc_opts_pag,
                            index=cat_lanc_opts_pag.index(cat_pag) if cat_pag in cat_lanc_opts_pag else 0,
                        )
                    with mp6:
                        new_numero_pedido_pag = st.text_input("Numero do pedido", value=str(pag_obj.get("numero_pedido", "")))

                    mp7, mp8, mp9 = st.columns(3)
                    with mp7:
                        new_data_pag = st.date_input("Data do lancamento", value=data_atual_pag, format="DD/MM/YYYY")
                    with mp8:
                        new_venc_pag = st.date_input("Vencimento", value=venc_atual_pag, format="DD/MM/YYYY")
                    with mp9:
                        cob_pag = str(pag_obj.get("cobranca", "Boleto"))
                        new_cobranca_pag = st.selectbox(
                            "Forma de pagamento",
                            cobranca_opts_pag,
                            index=cobranca_opts_pag.index(cob_pag) if cob_pag in cobranca_opts_pag else 0,
                        )

                    mp10, mp11 = st.columns(2)
                    with mp10:
                        status_pag_atual = str(pag_obj.get("status", "Aberto"))
                        new_status_pag = st.selectbox(
                            "Status",
                            status_opts_pag,
                            index=status_opts_pag.index(status_pag_atual) if status_pag_atual in status_opts_pag else 0,
                        )

                    new_val_total_pag_num = parse_money(new_val_total_pag)
                    new_qtd_pag_int = max(1, int(new_qtd_pag))
                    new_valor_parcela_pag = f"{(new_val_total_pag_num / new_qtd_pag_int):.2f}".replace(".", ",") if new_val_total_pag_num > 0 else "0,00"
                    with mp11:
                        st.text_input("Valor da parcela (automatico)", value=new_valor_parcela_pag, disabled=True, key="pag_edit_valor_parcela_auto")

                    mpc1, mpc2 = st.columns(2)
                    with mpc1:
                        salvar_pag = st.form_submit_button("Salvar alteracoes")
                    with mpc2:
                        excluir_pag = st.form_submit_button("Excluir despesa", type="primary")

                    if salvar_pag:
                        if not new_desc_pag.strip() or not new_forn_pag.strip() or new_val_total_pag_num <= 0:
                            st.error("Informe descricao, referencia e valor total valido.")
                        else:
                            pag_obj["descricao"] = new_desc_pag.strip()
                            pag_obj["valor"] = new_val_total_pag.strip()
                            pag_obj["valor_parcela"] = new_valor_parcela_pag
                            pag_obj["parcela"] = f"{parcela_atual_pag}/{new_qtd_pag_int}" if new_qtd_pag_int > 1 else str(parcela_atual_pag)
                            pag_obj["fornecedor"] = new_forn_pag.strip()
                            pag_obj["categoria_lancamento"] = new_cat_pag
                            pag_obj["numero_pedido"] = new_numero_pedido_pag.strip()
                            pag_obj["data"] = new_data_pag.strftime("%d/%m/%Y")
                            pag_obj["vencimento"] = new_venc_pag.strftime("%d/%m/%Y")
                            pag_obj["cobranca"] = new_cobranca_pag
                            pag_obj["status"] = new_status_pag
                            save_list(PAYABLES_FILE, st.session_state["payables"])
                            st.success("Despesa atualizada!")
                            st.rerun()

                    if excluir_pag:
                        st.session_state["payables"].remove(pag_obj)
                        save_list(PAYABLES_FILE, st.session_state["payables"])
                        st.success("Despesa excluida.")
                        st.rerun()

        with tab3:
            st.markdown("### Pagamentos de matricula enviados pelo Comercial")
            pagamentos = st.session_state.get("sales_payments", [])
            if not pagamentos:
                st.info("Nenhum pagamento enviado pelo Comercial.")
            else:
                filtro_status = st.selectbox(
                    "Status",
                    ["Todos", "Pendente", "Aprovado", "Reprovado"],
                    key="coord_sales_payments_filter_status",
                )
                pagamentos_filtrados = pagamentos
                if filtro_status != "Todos":
                    pagamentos_filtrados = [
                        p for p in pagamentos_filtrados if str(p.get("status", "")).strip() == filtro_status
                    ]

                if pagamentos_filtrados:
                    df_payments = pd.DataFrame(pagamentos_filtrados)
                    col_order = [
                        "created_at",
                        "aluno",
                        "telefone",
                        "valor",
                        "forma_pagamento",
                        "data_pagamento",
                        "vendedor",
                        "status",
                        "recibo_numero",
                        "receivable_code",
                    ]
                    df_payments = df_payments[[c for c in col_order if c in df_payments.columns]]
                    st.dataframe(df_payments, use_container_width=True)

                    labels = [
                        f"{str(p.get('created_at', '')).strip()} | {str(p.get('aluno', '')).strip()} | R$ {str(p.get('valor', '')).strip()} | {str(p.get('status', '')).strip()}"
                        for p in pagamentos_filtrados
                    ]
                    pay_sel_label = st.selectbox("Selecionar pagamento", labels, key="coord_sales_payment_sel")
                    pay_obj = pagamentos_filtrados[labels.index(pay_sel_label)]

                    st.caption(
                        f"Vendedor: {str(pay_obj.get('vendedor', '')).strip()} | Forma: {str(pay_obj.get('forma_pagamento', '')).strip()} | Data pagamento: {str(pay_obj.get('data_pagamento', '')).strip()}"
                    )
                    if str(pay_obj.get("observacao", "")).strip():
                        st.write(f"Observacoes: {str(pay_obj.get('observacao', '')).strip()}")
                    if str(pay_obj.get("reprovado_motivo", "")).strip():
                        st.warning(f"Motivo da reprovacao: {str(pay_obj.get('reprovado_motivo', '')).strip()}")

                    comprovante_bytes = _decode_sales_attachment(pay_obj)
                    comprovante_mime = str(pay_obj.get("comprovante_mime", "")).strip().lower()
                    comprovante_nome = str(pay_obj.get("comprovante_nome", "")).strip() or "comprovante"
                    if comprovante_bytes:
                        st.markdown("#### Comprovante anexado")
                        if comprovante_mime.startswith("image/"):
                            st.image(comprovante_bytes, caption=comprovante_nome)
                        else:
                            st.download_button(
                                "Baixar comprovante",
                                data=comprovante_bytes,
                                file_name=comprovante_nome,
                                mime=comprovante_mime or "application/octet-stream",
                                key=f"coord_sales_down_{str(pay_obj.get('id', ''))}",
                            )
                    else:
                        st.info("Sem comprovante anexado.")

                    recibo_html = _sales_receipt_html(pay_obj)
                    st.download_button(
                        "Baixar recibo (HTML)",
                        data=recibo_html,
                        file_name=f"recibo_{str(pay_obj.get('aluno', 'aluno')).replace(' ', '_').lower()}.html",
                        mime="text/html",
                        key=f"coord_sales_receipt_{str(pay_obj.get('id', ''))}",
                    )

                    motivo_reprovacao = st.text_input(
                        "Motivo da reprovacao (opcional)",
                        value="",
                        key=f"coord_sales_reject_reason_{str(pay_obj.get('id', ''))}",
                    )

                    c1, c2 = st.columns(2)
                    if c1.button("Aprovar pagamento", type="primary", key=f"coord_sales_approve_{str(pay_obj.get('id', ''))}"):
                        ok, msg = _approve_sales_payment(pay_obj, st.session_state.get("user_name", "Coordenacao"))
                        if ok:
                            st.success(msg)
                            st.rerun()
                        else:
                            st.error(msg)

                    if c2.button("Reprovar pagamento", key=f"coord_sales_reject_{str(pay_obj.get('id', ''))}"):
                        ok, msg = _reject_sales_payment(
                            pay_obj,
                            st.session_state.get("user_name", "Coordenacao"),
                            motivo_reprovacao or "Nao informado",
                        )
                        if ok:
                            st.success(msg)
                            st.rerun()
                        else:
                            st.error(msg)
                else:
                    st.info("Nenhum pagamento encontrado para o filtro selecionado.")

    elif menu_coord == "Notas":
        st.markdown('<div class="main-header">Aprovação de Notas</div>', unsafe_allow_html=True)
        pendentes = [g for g in st.session_state["grades"] if g.get("status") == "Pendente"]
        if pendentes:
            st.dataframe(pd.DataFrame(pendentes), use_container_width=True)
            if st.button("Aprovar Todas as Pendentes", type="primary"):
                aprovados_por_aluno = {}
                for g in st.session_state["grades"]:
                    if g.get("status") == "Pendente":
                        g["status"] = "Aprovado"
                        aluno_nome = str(g.get("aluno", "")).strip()
                        if aluno_nome:
                            aprovados_por_aluno.setdefault(aluno_nome, []).append(g)
                save_list(GRADES_FILE, st.session_state["grades"])
                if wiz_event_enabled("on_grade_approved"):
                    sent_students = 0
                    for aluno_nome, notas in aprovados_por_aluno.items():
                        student = next((s for s in st.session_state.get("students", []) if s.get("nome") == aluno_nome), {})
                        if not student:
                            continue
                        linhas = []
                        for n in notas[:12]:
                            linhas.append(
                                f"- {n.get('avaliacao','Avaliação')}: nota {n.get('nota','')} "
                                f"({n.get('disciplina','Inglês')})"
                            )
                        _notify_direct_contacts(
                            student.get("nome", "Aluno"),
                            _message_recipients_for_student(student),
                            _student_whatsapp_recipients(student),
                            "[Active] Notas aprovadas",
                            "Suas notas foram aprovadas:\n\n" + "\n".join(linhas),
                            "Notas",
                        )
                        sent_students += 1
                    if sent_students:
                        st.info(f"Assistente Wiz notificou {sent_students} aluno(s) sobre aprovação de notas.")
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
                with c3: u_role = st.selectbox("Perfil", ["Aluno", "Professor", "Comercial", "Coordenador"])
                d1, d2, d3 = st.columns(3)
                with d1: u_pessoa = st.text_input("Nome da pessoa (opcional)")
                with d2: u_email = st.text_input("E-mail (opcional)")
                with d3: u_cel = st.text_input("Celular/WhatsApp (opcional)")
                if st.form_submit_button("Criar Acesso"):
                    st.session_state["users"].append(
                        {
                            "usuario": u_user,
                            "senha": u_pass,
                            "perfil": u_role,
                            "pessoa": u_pessoa.strip(),
                            "email": u_email.strip().lower(),
                            "celular": u_cel.strip(),
                        }
                    )
                    save_users(st.session_state["users"])
                    if wiz_event_enabled("on_user_created"):
                        _notify_direct_contacts(
                            u_pessoa.strip() or u_user.strip() or "Usuário",
                            [u_email],
                            [u_cel],
                            "[Active] Acesso criado",
                            f"Seu acesso ao Active foi criado.\nPerfil: {u_role}\nUsuário: {u_user}",
                            "Cadastro Usuário",
                        )
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
                        role_opts = ["Aluno", "Professor", "Comercial", "Coordenador"]
                        new_role = st.selectbox(
                            "Perfil",
                            role_opts,
                            index=role_opts.index(user_obj["perfil"]) if user_obj["perfil"] in role_opts else 0,
                        )
                        e1, e2, e3 = st.columns(3)
                        with e1: new_person = st.text_input("Pessoa", value=user_obj.get("pessoa", ""))
                        with e2: new_email = st.text_input("E-mail", value=user_obj.get("email", ""))
                        with e3: new_cel = st.text_input("Celular", value=user_obj.get("celular", ""))
                        c_edit, c_del = st.columns([1, 1])
                        with c_edit:
                            if st.form_submit_button("Salvar Alterações"):
                                user_obj["usuario"] = new_user
                                user_obj["senha"] = new_pass
                                user_obj["perfil"] = new_role
                                user_obj["pessoa"] = new_person.strip()
                                user_obj["email"] = new_email.strip().lower()
                                user_obj["celular"] = new_cel.strip()
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
        st.markdown('<div class="main-header">Caixa de Entrada</div>', unsafe_allow_html=True)
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
                        st.success(
                            "Mensagem publicada. "
                            f"E-mail: {stats.get('email_ok', 0)}/{stats.get('email_total', 0)} | "
                            f"WhatsApp: {stats.get('whatsapp_ok', 0)}/{stats.get('whatsapp_total', 0)}."
                        )
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
                            st.info(
                                "Disparos dos desafios: "
                                f"E-mail {stats.get('email_ok', 0)}/{stats.get('email_total', 0)} | "
                                f"WhatsApp {stats.get('whatsapp_ok', 0)}/{stats.get('whatsapp_total', 0)}."
                            )
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
                        st.info(
                            "Disparos dos desafios: "
                            f"E-mail {stats.get('email_ok', 0)}/{stats.get('email_total', 0)} | "
                            f"WhatsApp {stats.get('whatsapp_ok', 0)}/{stats.get('whatsapp_total', 0)}."
                        )
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

    elif menu_coord == "WhatsApp":
        st.markdown('<div class="main-header">WhatsApp (Evolution)</div>', unsafe_allow_html=True)
        st.caption("Tenta obter o QR code da sua instancia do WhatsApp via Evolution API.")

        base_default = _evolution_base_url()
        key_default = _evolution_api_key()
        inst_default = _evolution_instance_name()

        base_url = st.text_input(
            "EVOLUTION_API_URL",
            value=base_default,
            placeholder="https://seu-evolution-api.exemplo",
            key="evo_url",
        ).strip()
        api_key = st.text_input(
            "EVOLUTION_API_KEY",
            value=key_default,
            type="password",
            key="evo_key",
        ).strip()
        instance_name = st.text_input(
            "EVOLUTION_INSTANCE",
            value=inst_default,
            placeholder="nome-da-instancia",
            key="evo_instance",
        ).strip()
        pair_number = st.text_input(
            "Numero para parear (opcional)",
            value="",
            placeholder="Ex: 5516999999999 (somente digitos, com DDI)",
            key="evo_pair_number",
        ).strip()

        auth_mode = st.selectbox(
            "Header de autenticacao",
            ["apikey", "Authorization: Bearer"],
            index=0,
            help="A maioria das instalacoes usa header 'apikey'.",
            key="evo_auth_mode",
        )
        qr_endpoint = st.selectbox(
            "Endpoint do QR",
            [
                "Auto (tentar comuns)",
                "GET /instance/connect/{instance}",
                "POST /instance/connect/{instance}",
                "GET /instance/qrcode/{instance}",
                "GET /instance/qr/{instance}",
            ],
            index=0,
            key="evo_qr_endpoint",
        )
        timeout_s = st.number_input(
            "Timeout (segundos)",
            min_value=3,
            max_value=60,
            value=15,
            step=1,
            key="evo_timeout_s",
        )

        headers = {"Accept": "application/json", "User-Agent": "Active-Educacional/streamlit"}
        if api_key:
            if auth_mode.startswith("Authorization"):
                if api_key.lower().startswith("bearer "):
                    headers["Authorization"] = api_key
                else:
                    headers["Authorization"] = f"Bearer {api_key}"
            else:
                headers["apikey"] = api_key

        with st.expander("Testar API (opcional)", expanded=False):
            if st.button("Testar / (raiz)", key="evo_test_root"):
                if not base_url:
                    st.error("Informe EVOLUTION_API_URL.")
                else:
                    url = base_url.rstrip("/") + "/"
                    status, ct, body, err = _http_request("GET", url, headers=headers, timeout=int(timeout_s))
                    parsed, text = _try_parse_json(ct, body)
                    st.write(f"HTTP {status} | {ct or 'sem content-type'} | {err or 'ok'}")
                    if isinstance(parsed, dict):
                        st.json(_sanitize_for_debug(parsed))
                        mgr = str(parsed.get("manager", "") or "").strip()
                        if mgr:
                            st.caption(f"manager: {mgr}")
                            if mgr.startswith("http://") and base_url.lower().startswith("https://"):
                                st.warning(
                                    "O campo `manager` esta vindo em http:// enquanto voce acessa por https://. "
                                    "Isso costuma quebrar o QR no navegador (mixed content)."
                                )
                    else:
                        st.code((text or "")[:4000], language="text")

        selected_instance = None
        with st.expander("Encontrar instancia (opcional)", expanded=False):
            if st.button("Buscar instancias", key="evo_list_instances"):
                if not base_url:
                    st.session_state["evo_instances_cache"] = []
                    st.session_state["evo_instances_cache_error"] = "Informe EVOLUTION_API_URL."
                else:
                    list_candidates = [
                        "/instance/fetchInstances",
                        "/api/instance/fetchInstances",
                        "/instance",
                        "/api/instance",
                    ]
                    found = None
                    last_err = ""
                    for path in list_candidates:
                        url = base_url.rstrip("/") + path
                        status, ct, body, err = _http_request("GET", url, headers=headers, timeout=int(timeout_s))
                        parsed, text = _try_parse_json(ct, body)
                        if isinstance(parsed, list) and parsed:
                            found = parsed
                            last_err = ""
                            break
                        last_err = f"{path} -> HTTP {status} ({err or 'ok'})"
                    if found is not None:
                        st.session_state["evo_instances_cache"] = found
                        st.session_state["evo_instances_cache_error"] = ""
                    else:
                        st.session_state["evo_instances_cache"] = []
                        st.session_state["evo_instances_cache_error"] = last_err or "Nao foi possivel listar instancias."

            if st.session_state.get("evo_instances_cache_error"):
                st.warning(st.session_state["evo_instances_cache_error"])

            raw_list = st.session_state.get("evo_instances_cache") or []
            normalized = []
            if isinstance(raw_list, list):
                for item in raw_list:
                    if not isinstance(item, dict):
                        continue
                    inst = item.get("instance") if isinstance(item.get("instance"), dict) else item
                    name = str(inst.get("instanceName", "") or "").strip()
                    iid = str(inst.get("instanceId", "") or "").strip()
                    status = str(inst.get("status", "") or inst.get("connectionStatus", "") or "").strip()
                    if not (name or iid):
                        continue
                    label = f"{name or '(sem nome)'} ({status or 'sem status'}) - {iid or 'sem id'}"
                    normalized.append({"label": label, "instanceName": name, "instanceId": iid, "status": status})

            if normalized:
                st.dataframe(pd.DataFrame(normalized), use_container_width=True)
                labels = [i["label"] for i in normalized]
                chosen = st.selectbox("Selecionar", labels, key="evo_instance_pick_label")
                selected_instance = next((i for i in normalized if i["label"] == chosen), None)
                st.checkbox("Usar instancia selecionada", value=True, key="evo_use_picked_instance")
                st.checkbox("Usar instanceId (em vez do instanceName)", value=False, key="evo_use_instance_id")
            else:
                st.caption("Clique em 'Buscar instancias' para listar (requer URL e, em geral, chave).")

        c1, c2 = st.columns([1, 1])
        fetch = c1.button("Gerar / Atualizar QR", type="primary", key="evo_fetch_qr")
        show_debug = c2.checkbox("Mostrar debug", value=True, key="evo_show_debug")

        if fetch:
            if not base_url:
                st.error("Informe EVOLUTION_API_URL.")
            else:
                instance_value = instance_name
                if st.session_state.get("evo_use_picked_instance") and isinstance(selected_instance, dict):
                    if st.session_state.get("evo_use_instance_id"):
                        instance_value = selected_instance.get("instanceId") or instance_value
                    else:
                        instance_value = selected_instance.get("instanceName") or instance_value
                instance_value = str(instance_value or "").strip()
                if not instance_value:
                    st.error("Informe EVOLUTION_INSTANCE (ou selecione uma instancia).")
                    st.stop()

                inst = quote(instance_value, safe="")
                pair_digits = re.sub(r"\D+", "", str(pair_number or ""))
                qs = f"?number={quote(pair_digits, safe='')}" if pair_digits else ""
                candidates = []
                if qr_endpoint.startswith("Auto"):
                    base_paths = [
                        ("GET", f"/instance/connect/{inst}{qs}"),
                        ("POST", f"/instance/connect/{inst}{qs}"),
                        ("GET", f"/instance/qrcode/{inst}"),
                        ("GET", f"/instance/qr/{inst}"),
                        ("GET", f"/instance/{inst}/qrcode"),
                        ("GET", f"/instance/{inst}/qr"),
                        ("GET", f"/manager/instance/{inst}/qrcode"),
                        ("GET", f"/manager/instance/{inst}/qr"),
                        ("GET", f"/manager/api/instance/{inst}/qrcode"),
                        ("GET", f"/manager/api/v1/instance/{inst}/qrcode"),
                    ]
                    prefixes = ["", "/api", "/api/v1", "/v1"]
                    seen = set()
                    for method, path in base_paths:
                        if path.startswith("/instance/"):
                            for pfx in prefixes:
                                key = (method, pfx + path)
                                if key in seen:
                                    continue
                                seen.add(key)
                                candidates.append(key)
                        else:
                            key = (method, path)
                            if key in seen:
                                continue
                            seen.add(key)
                            candidates.append(key)
                else:
                    try:
                        method, path = qr_endpoint.split(" ", 1)
                        candidates = [(method.strip().upper(), path.strip().replace("{instance}", inst) + qs)]
                    except Exception:
                        candidates = [("GET", f"/instance/connect/{inst}{qs}")]

                attempts = []
                found_img = None
                found_meta = None
                found_pairing_code = ""
                for method, path in candidates:
                    url = base_url.rstrip("/") + path
                    status, ct, body, err = _http_request(method, url, headers=headers, timeout=int(timeout_s))
                    parsed, text = _try_parse_json(ct, body)
                    if not found_pairing_code and isinstance(parsed, (dict, list)):
                        found_pairing_code = _extract_pairing_code(parsed)

                    img_bytes = None
                    qr_candidate = ""
                    if str(ct).lower().startswith("image/") and isinstance(body, (bytes, bytearray)) and body:
                        img_bytes = bytes(body)
                    else:
                        if parsed is not None:
                            qr_candidate = _extract_qr_candidate(parsed)
                        if not qr_candidate:
                            qr_candidate = str(text or "").strip()
                        img_bytes = _maybe_decode_qr_image_bytes(qr_candidate)
                        if img_bytes is None and qr_candidate:
                            gen = _qr_content_to_png_bytes(qr_candidate)
                            if gen:
                                img_bytes = gen

                    if str(ct).lower().startswith("image/"):
                        body_preview = f"(binary image, {len(body or b'')} bytes)"
                    else:
                        body_preview = (str(text or "")[:2000]).strip()

                    attempts.append(
                        {
                            "method": method,
                            "path": path,
                            "status": status,
                            "content_type": ct,
                            "error": err,
                            "body_preview": body_preview,
                            "json": _sanitize_for_debug(parsed) if isinstance(parsed, (dict, list)) else None,
                        }
                    )

                    if img_bytes:
                        found_img = img_bytes
                        found_meta = {"method": method, "path": path, "status": status}
                        break

                if found_img:
                    st.success(f"QR obtido: {found_meta['method']} {found_meta['path']} (HTTP {found_meta['status']})")
                    if found_pairing_code:
                        st.info(f"Pairing code (se seu WhatsApp pedir): {found_pairing_code}")
                    try:
                        sniff = found_img.lstrip()[:16]
                        if sniff.startswith(b"<svg") or sniff.startswith(b"<?xml"):
                            b64 = base64.b64encode(found_img).decode("ascii")
                            st.markdown(
                                f"<img src='data:image/svg+xml;base64,{b64}' style='max-width:340px; width:100%;' />",
                                unsafe_allow_html=True,
                            )
                        else:
                            st.image(found_img, caption=f"Instance: {instance_name}")
                    except Exception as exc:
                        st.error(f"QR obtido, mas falhou ao renderizar imagem: {exc}")
                else:
                    st.error("Nao consegui obter o QR code. Veja o debug abaixo.")

                if show_debug:
                    with st.expander("Debug (Evolution API)", expanded=not bool(found_img)):
                        st.json(attempts)
                        st.caption("Dicas: 401=chave errada. 404=URL/prefixo errado. Se ja estiver conectado, pode nao haver QR.")

    elif menu_coord == "Assistente Wiz":
        run_wiz_assistant()

    elif menu_coord == "Backup":
        st.markdown('<div class="main-header">Backup</div>', unsafe_allow_html=True)
        storage_mode = "Banco de Dados (persistente)" if _db_enabled() else "Arquivos locais (pode apagar em hospedagens temporarias)"
        st.write(f"**Armazenamento atual:** {storage_mode}")
        if _db_enabled() and st.session_state.get("_db_last_error"):
            st.error(f"Falha de conexao com banco detectada: {st.session_state.get('_db_last_error')}")
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
            ("class_sessions.json", "class_sessions", CLASS_SESSIONS_FILE),
            ("messages.json", "messages", MESSAGES_FILE),
            ("challenges.json", "challenges", CHALLENGES_FILE),
            ("challenge_completions.json", "challenge_completions", CHALLENGE_COMPLETIONS_FILE),
            ("activities.json", "activities", ACTIVITIES_FILE),
            ("activity_submissions.json", "activity_submissions", ACTIVITY_SUBMISSIONS_FILE),
            ("sales_leads.json", "sales_leads", SALES_LEADS_FILE),
            ("sales_agenda.json", "sales_agenda", SALES_AGENDA_FILE),
            ("sales_payments.json", "sales_payments", SALES_PAYMENTS_FILE),
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

