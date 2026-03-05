import base64
import datetime
import hashlib
import hmac
import importlib
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
from decimal import Decimal, InvalidOperation
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
if "finance_settings" not in st.session_state:
    st.session_state["finance_settings"] = {}
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
FINANCE_SETTINGS_FILE = DATA_DIR / "finance_settings.json"
WIZ_ACTION_AUDIT_FILE = DATA_DIR / "wiz_action_audit.json"
BACKUP_META_FILE = DATA_DIR / "backup_meta.json"
WHATSAPP_NUMBER = "5516996043314" 
WAPI_DEFAULT_INSTANCE_ID = ""
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

def _wapi_instance_from_url(url_value):
    try:
        raw_url = str(url_value or "").strip()
        if not raw_url:
            return ""
        split = urlsplit(raw_url)
        qs = dict(parse_qsl(split.query, keep_blank_values=True))
        for key in ("instanceId", "instance_id", "instance", "instanceName", "instance_name"):
            val = str(qs.get(key, "")).strip()
            if val:
                return val
    except Exception:
        return ""
    return ""

def _wapi_token():
    return (
        _get_config_value("WAPI_TOKEN", "")
        or _get_config_value("W_API_TOKEN", "")
        or _get_config_value("WAPI_API_KEY", "")
    ).strip()

def _wapi_instance_id():
    explicit = (
        _get_config_value("WAPI_INSTANCE_ID", "")
        or _get_config_value("W_API_INSTANCE_ID", "")
        or _get_config_value("WAPI_INSTANCE", "")
        or _get_config_value("W_API_INSTANCE", "")
    ).strip()
    if explicit:
        return explicit
    from_url = _wapi_instance_from_url(
        _get_config_value("WAPI_URL", "")
        or _get_config_value("W_API_URL", "")
        or _get_config_value("WAPI_BASE_URL", "")
    )
    if from_url:
        return str(from_url).strip()
    return str(WAPI_DEFAULT_INSTANCE_ID or "").strip()

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

DEFAULT_FINANCE_SETTINGS = {
    "smtp_host": "",
    "smtp_port": "587",
    "smtp_user": "",
    "smtp_pass": "",
    "smtp_tls": "1",
    "smtp_from": "",
    "boleto_provider": "link",
    "boleto_base_url": "",
    "boleto_link_template": "",
    "boleto_api_url": "",
    "boleto_api_key": "",
    "boleto_api_auth_header": "Authorization",
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

def get_wiz_settings(refresh=True):
    raw = {}
    if refresh:
        raw = _load_json_dict(WIZ_SETTINGS_FILE, DEFAULT_WIZ_SETTINGS)
        if isinstance(raw, dict):
            st.session_state["wiz_settings"] = dict(raw)
    else:
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

def get_finance_settings():
    raw = st.session_state.get("finance_settings") or {}
    merged = dict(DEFAULT_FINANCE_SETTINGS)
    if isinstance(raw, dict):
        for key in merged:
            val = raw.get(key, None)
            if val is not None:
                merged[key] = str(val)
    return merged

def save_finance_settings(settings):
    merged = dict(DEFAULT_FINANCE_SETTINGS)
    if isinstance(settings, dict):
        for key in merged:
            if key in settings:
                merged[key] = str(settings.get(key, ""))
    st.session_state["finance_settings"] = merged
    _save_json_dict(FINANCE_SETTINGS_FILE, merged)
    return merged

def _finance_config_value(env_key, settings_key, default=""):
    env_val = _get_config_value(env_key, "")
    if str(env_val).strip():
        return str(env_val).strip()
    settings = get_finance_settings()
    val = str(settings.get(settings_key, "")).strip()
    return val or default

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

def wiz_chatbot_paused():
    return bool(get_wiz_settings().get("mister_wiz_paused", False))

def set_wiz_chatbot_paused(paused):
    settings = get_wiz_settings()
    settings["mister_wiz_paused"] = bool(paused)
    save_wiz_settings(settings)
    return bool(settings.get("mister_wiz_paused", False))

def _wiz_control_command(text):
    norm = _wiz_norm_text(text)
    norm_simple = re.sub(r"\s+", " ", re.sub(r"[^a-z0-9! ]+", " ", norm)).strip()
    stop_cmds = {
        "!parar",
        "parar",
        "!pausar",
        "pausar",
        "assumir controle",
        "assumir atendimento",
        "!assumir",
        "bot parar",
    }
    resume_cmds = {
        "!retomar",
        "retomar",
        "!continuar",
        "continuar",
        "!iniciar",
        "iniciar bot",
        "retomar bot",
        "bot retomar",
    }
    if norm in stop_cmds or norm_simple in stop_cmds:
        return "stop"
    if norm in resume_cmds or norm_simple in resume_cmds:
        return "resume"
    return ""

def _wiz_admin_whatsapp_numbers():
    numbers = set()
    raw_env = (
        _get_config_value("ACTIVE_ADMIN_WHATSAPP", "")
        or _get_config_value("ACTIVE_ADMIN_WHATSAPPS", "")
        or _get_config_value("ACTIVE_ADMIN_NUMBERS", "")
    )
    for chunk in re.split(r"[;, \n]+", str(raw_env or "").strip()):
        normalized = _normalize_whatsapp_number(chunk)
        if normalized:
            numbers.add(normalized)
    for user in st.session_state.get("users", []):
        if not isinstance(user, dict):
            continue
        perfil = str(user.get("perfil", "")).strip()
        if perfil not in ("Admin", "Coordenador"):
            continue
        normalized = _normalize_whatsapp_number(user.get("celular", ""))
        if normalized:
            numbers.add(normalized)
    return numbers

def handle_wiz_control_from_admin_number(sender_number, text):
    sender = _normalize_whatsapp_number(sender_number)
    cmd = _wiz_control_command(text)
    if not sender or not cmd:
        return False, ""
    if sender not in _wiz_admin_whatsapp_numbers():
        return False, ""
    paused = (cmd == "stop")
    set_wiz_chatbot_paused(paused)
    status = "pausado (atendimento humano)" if paused else "retomado (bot ativo)"
    return True, f"Controle recebido do admin. Mister Wiz {status}."

def apply_wiz_control_from_operator_message(message_text, assume_control=False):
    cmd = _wiz_control_command(message_text)
    if cmd == "resume":
        set_wiz_chatbot_paused(False)
        return "Bot Mister Wiz retomado por comando do operador."
    if cmd == "stop" or bool(assume_control):
        set_wiz_chatbot_paused(True)
        if cmd == "stop":
            return "Bot Mister Wiz pausado por comando do operador."
        return "Bot Mister Wiz pausado automaticamente: atendimento humano assumido."
    return ""

def _query_param_value(*keys):
    for key in keys:
        try:
            value = st.query_params.get(key, "")
            if isinstance(value, list):
                value = value[0] if value else ""
            value = str(value or "").strip()
            if value:
                return value
        except Exception:
            pass
        try:
            params = st.experimental_get_query_params() or {}
            value = params.get(key, [""])
            if isinstance(value, list):
                value = value[0] if value else ""
            value = str(value or "").strip()
            if value:
                return value
        except Exception:
            pass
    return ""

def _clear_query_params(*keys):
    clean_keys = [str(k).strip() for k in keys if str(k).strip()]
    if not clean_keys:
        return
    try:
        for k in clean_keys:
            if k in st.query_params:
                del st.query_params[k]
        return
    except Exception:
        pass
    try:
        params = st.experimental_get_query_params() or {}
        for k in clean_keys:
            params.pop(k, None)
        st.experimental_set_query_params(**params)
    except Exception:
        pass

def process_wiz_remote_control_from_query():
    sender = _query_param_value("wiz_from", "from", "sender", "number", "phone")
    text = _query_param_value("wiz_text", "text", "message", "body", "cmd")
    if not (sender and text):
        return False, ""

    required_token = str(_get_config_value("ACTIVE_WIZ_REMOTE_TOKEN", "")).strip()
    provided_token = _query_param_value("wiz_token", "token", "key")
    if required_token and provided_token != required_token:
        _clear_query_params("wiz_from", "from", "sender", "number", "phone", "wiz_text", "text", "message", "body", "cmd", "wiz_token", "token", "key")
        return False, "Comando remoto ignorado: token invalido."

    handled, msg = handle_wiz_control_from_admin_number(sender, text)
    _clear_query_params("wiz_from", "from", "sender", "number", "phone", "wiz_text", "text", "message", "body", "cmd", "wiz_token", "token", "key")
    return handled, (msg or "")
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
    if not (number and message_text and base_url and token):
        return False, "wapi nao configurado", []

    split = urlsplit(base_url)
    path_lower = str(split.path or "").lower()
    direct_endpoint = any(token in path_lower for token in ("send-text", "sendtext", "send-message", "sendmessage"))
    qs_initial = dict(parse_qsl(split.query, keep_blank_values=True))
    url_instance = (
        str(qs_initial.get("instanceId", "")).strip()
        or str(qs_initial.get("instance_id", "")).strip()
        or str(qs_initial.get("instance", "")).strip()
    )
    effective_instance = str(instance_id or url_instance or "").strip()
    if not effective_instance:
        return False, "instanceId da W-API nao configurado", []
    endpoint_urls = []
    if direct_endpoint:
        qs = dict(qs_initial)
        # Try multiple variants to avoid stale instanceId in URL query.
        qs_forced = dict(qs)
        if effective_instance:
            qs_forced["instanceId"] = effective_instance
            if "instance_id" in qs_forced:
                qs_forced["instance_id"] = effective_instance
        qs_original = dict(qs)
        qs_without_instance = {k: v for k, v in qs.items() if str(k) not in ("instanceId", "instance_id")}
        direct_url_forced = urlunsplit((split.scheme, split.netloc, split.path, urlencode(qs_forced), split.fragment))
        direct_url_original = urlunsplit((split.scheme, split.netloc, split.path, urlencode(qs_original), split.fragment))
        direct_url_no_instance = urlunsplit((split.scheme, split.netloc, split.path, urlencode(qs_without_instance), split.fragment))
        endpoint_urls = []
        for u in (direct_url_forced, direct_url_original, direct_url_no_instance):
            u = str(u).strip()
            if u and u not in endpoint_urls:
                endpoint_urls.append(u)
    else:
        host_root = urlunsplit((split.scheme, split.netloc, "", "", "")).rstrip("/")
        base_root = base_url.rstrip("/")
        roots = []
        for r in (base_root, host_root):
            r = str(r).rstrip("/")
            if r and r not in roots:
                roots.append(r)
        inst_q = quote(effective_instance, safe="")
        path_candidates = [
            "/v1/message/send-text",
            f"/v1/message/send-text?instanceId={inst_q}",
            f"/v1/message/send-text?instance_id={inst_q}",
            "/v1/messages/send-text",
            f"/v1/messages/send-text?instanceId={inst_q}",
            f"/v1/messages/send-text?instance_id={inst_q}",
            "/v1/message/sendText",
            f"/v1/message/sendText?instanceId={inst_q}",
            "/api/v1/message/send-text",
            f"/api/v1/message/send-text?instanceId={inst_q}",
            f"/api/v1/message/send-text?instance_id={inst_q}",
            "/api/v1/messages/send-text",
            f"/api/v1/messages/send-text?instanceId={inst_q}",
            f"/api/v1/messages/send-text?instance_id={inst_q}",
            "/message/send-text",
            f"/message/send-text?instanceId={inst_q}",
            f"/message/send-text?instance_id={inst_q}",
            "/message/sendText",
            f"/message/sendText?instanceId={inst_q}",
            f"/api/v1/instances/{quote(effective_instance, safe='')}/send-text",
            f"/instance/{quote(effective_instance, safe='')}/send-text",
        ]
        endpoint_urls = [root + path for root in roots for path in path_candidates]

    headers_list = [
        {"Authorization": token if token.lower().startswith("bearer ") else f"Bearer {token}"},
        {"apikey": token},
        {"x-api-key": token},
    ]
    payloads = [
        {"phone": number, "message": message_text},
        {"number": number, "message": message_text},
        {"to": number, "message": message_text},
        {"to": number, "text": message_text},
        {"instanceId": effective_instance, "phone": number, "message": message_text},
        {"instanceId": effective_instance, "number": number, "text": message_text},
        {"instance_id": effective_instance, "phone": number, "message": message_text},
        {"instance": effective_instance, "phone": number, "message": message_text},
    ]

    attempts = []
    for url in endpoint_urls:
        for auth_headers in headers_list:
            headers = {"Accept": "application/json", "Content-Type": "application/json", "User-Agent": "Active-Wiz-Automation/1.0"}
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
    detail = str(last.get("preview", "") or last.get("error", "")).strip()
    if detail:
        detail = detail[:120]
    return False, f"falha wapi (HTTP {last.get('status')}) {detail}".strip(), attempts

def _has_wapi_config():
    return bool(_wapi_base_url() and _wapi_token() and _wapi_instance_id())

def _has_evolution_config():
    return bool(_evolution_base_url() and _evolution_api_key() and _evolution_instance_name())

def _send_whatsapp_auto(number, text, timeout=20):
    provider = str(_get_config_value("ACTIVE_WHATSAPP_PROVIDER", "auto")).strip().lower()
    if provider == "wapi":
        ok, status, attempts = _send_whatsapp_wapi(number, text, timeout=timeout)
        if ok or not _has_evolution_config():
            return ok, status, attempts
        ok2, status2, attempts2 = _send_whatsapp_evolution(number, text, timeout=timeout)
        if ok2:
            return ok2, status2, attempts2
        return ok, f"{status} | fallback evolution: {status2}", attempts + attempts2
    if provider == "evolution":
        ok, status, attempts = _send_whatsapp_evolution(number, text, timeout=timeout)
        if ok or not _has_wapi_config():
            return ok, status, attempts
        ok2, status2, attempts2 = _send_whatsapp_wapi(number, text, timeout=timeout)
        if ok2:
            return ok2, status2, attempts2
        return ok, f"{status} | fallback wapi: {status2}", attempts + attempts2

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

def notify_student_financial_event(aluno_nome, itens, send_email=True, send_whatsapp=True):
    if not wiz_event_enabled("on_financial_created"):
        return {"email_total": 0, "email_ok": 0, "whatsapp_total": 0, "whatsapp_ok": 0}
    student = next((s for s in st.session_state.get("students", []) if s.get("nome") == aluno_nome), {})
    if not student:
        return {"email_total": 0, "email_ok": 0, "whatsapp_total": 0, "whatsapp_ok": 0}
    lines = []
    for item in itens[:12]:
        item_line = (
            f"- {item.get('descricao','Lancamento')} | Venc: {item.get('vencimento','')} | "
            f"Parcela: {item.get('parcela','')} | Valor: {item.get('valor_parcela', item.get('valor',''))}"
        )
        if item.get("boleto_url"):
            item_line += f" | Boleto: {item.get('boleto_url')}"
        lines.append(item_line)
    assunto = "[Active] Novo lançamento financeiro"
    corpo = "Foram lançados novos itens financeiros no seu cadastro.\n\n" + "\n".join(lines)
    return _notify_direct_contacts(
        student.get("nome", "Aluno"),
        _message_recipients_for_student(student) if bool(send_email) else [],
        _student_whatsapp_recipients(student) if bool(send_whatsapp) else [],
        assunto,
        corpo,
        "Financeiro",
    )

def notify_student_profile_update(student, autor="", origem="Atualizacao Aluno", send_email=True, send_whatsapp=True):
    if not isinstance(student, dict):
        return {"email_total": 0, "email_ok": 0, "whatsapp_total": 0, "whatsapp_ok": 0}
    nome = str(student.get("nome", "")).strip() or "Aluno"
    turma = str(student.get("turma", "")).strip() or "Sem Turma"
    livro = str(student.get("livro", "")).strip() or "A definir"
    matricula = str(student.get("matricula", "")).strip() or "-"
    assunto = "[Active] Atualizacao de cadastro"
    corpo = (
        f"Ola, {nome}!\n"
        "Seu cadastro no Active foi atualizado.\n\n"
        f"Data: {datetime.date.today().strftime('%d/%m/%Y')}\n"
        f"Turma: {turma}\n"
        f"Livro/Nivel: {livro}\n"
        f"Matricula: {matricula}\n"
    )
    portal = _student_portal_url()
    if portal:
        corpo += f"Portal do aluno: {portal}\n"
    if str(autor or "").strip():
        corpo += f"Atualizado por: {str(autor).strip()}\n"
    corpo += "\nSe tiver duvidas, responda esta mensagem."
    return _notify_direct_contacts(
        nome,
        _message_recipients_for_student(student) if bool(send_email) else [],
        _student_whatsapp_recipients(student) if bool(send_whatsapp) else [],
        assunto,
        corpo,
        origem,
    )

def _smtp_config_diagnostics():
    host = _finance_config_value("ACTIVE_SMTP_HOST", "smtp_host", "")
    port = _finance_config_value("ACTIVE_SMTP_PORT", "smtp_port", "587")
    user = _finance_config_value("ACTIVE_SMTP_USER", "smtp_user", "")
    sender = _finance_config_value("ACTIVE_EMAIL_FROM", "smtp_from", "")
    return {
        "host_ok": bool(str(host).strip()),
        "port_ok": bool(str(port).strip()),
        "user_ok": bool(str(user).strip()),
        "pass_ok": bool(_finance_config_value("ACTIVE_SMTP_PASS", "smtp_pass", "")),
        "from_ok": bool(str(sender).strip() or str(user).strip()),
        "tls_on": str(_finance_config_value("ACTIVE_SMTP_TLS", "smtp_tls", "1")).strip().lower() not in ("0", "false", "no"),
    }

def _boleto_config_diagnostics():
    provider = str(_finance_config_value("ACTIVE_BOLETO_PROVIDER", "boleto_provider", "link")).strip().lower() or "link"
    return {
        "provider": provider,
        "base_url_ok": bool(str(_finance_config_value("ACTIVE_BOLETO_BASE_URL", "boleto_base_url", "")).strip()),
        "template_ok": bool(str(_finance_config_value("ACTIVE_BOLETO_LINK_TEMPLATE", "boleto_link_template", "")).strip()),
        "api_url_ok": bool(str(_finance_config_value("ACTIVE_BOLETO_API_URL", "boleto_api_url", "")).strip()),
        "api_key_ok": bool(str(_finance_config_value("ACTIVE_BOLETO_API_KEY", "boleto_api_key", "")).strip()),
    }

def _find_student_by_name(name):
    target = str(name or "").strip().lower()
    if not target:
        return {}
    for student in st.session_state.get("students", []):
        if str(student.get("nome", "")).strip().lower() == target:
            return student
    return {}

def _format_boleto_linha(raw_digits):
    digits = re.sub(r"\D+", "", str(raw_digits or ""))
    if not digits:
        return ""
    groups = [digits[i:i + 5] for i in range(0, len(digits), 5)]
    return " ".join(groups).strip()

def _default_boleto_linha(rec_obj):
    codigo = re.sub(r"\D+", "", str(rec_obj.get("codigo", "")))
    valor_cent = int(round(parse_money(rec_obj.get("valor_parcela", rec_obj.get("valor", ""))) * 100))
    venc = parse_date(rec_obj.get("vencimento", ""))
    venc_token = venc.strftime("%d%m%Y") if venc else datetime.date.today().strftime("%d%m%Y")
    base = f"{codigo}{venc_token}{valor_cent:010d}"
    if len(base) < 47:
        base = (base + ("0" * 47))[:47]
    else:
        base = base[:47]
    return _format_boleto_linha(base)

def _build_boleto_link_from_template(template, rec_obj, student):
    venc = parse_date(rec_obj.get("vencimento", ""))
    valor_num = parse_money(rec_obj.get("valor_parcela", rec_obj.get("valor", "")))
    raw_map = {
        "codigo": str(rec_obj.get("codigo", "")).strip(),
        "aluno": str(rec_obj.get("aluno", "")).strip(),
        "descricao": str(rec_obj.get("descricao", "")).strip(),
        "vencimento": str(rec_obj.get("vencimento", "")).strip(),
        "vencimento_iso": venc.strftime("%Y-%m-%d") if venc else "",
        "valor": f"{valor_num:.2f}",
        "valor_centavos": str(int(round(valor_num * 100))),
        "parcela": str(rec_obj.get("parcela", "")).strip(),
        "categoria": str(rec_obj.get("categoria", "")).strip(),
        "cpf": str((student or {}).get("cpf", "")).strip(),
        "email": str((student or {}).get("email", "")).strip().lower(),
    }
    mapping = {}
    for key, val in raw_map.items():
        val_txt = str(val)
        mapping[key] = quote(val_txt, safe="")
        mapping[f"{key}_raw"] = val_txt

    def _replace(match):
        token = str(match.group(1))
        return str(mapping.get(token, ""))

    return re.sub(r"\{([A-Za-z0-9_]+)\}", _replace, str(template or "")).strip()

def _extract_boleto_info_from_json(payload):
    if not isinstance(payload, dict):
        return "", ""
    url_keys = [
        "boleto_url",
        "url_boleto",
        "link_boleto",
        "payment_url",
        "invoice_url",
        "bank_slip_url",
        "url",
        "link",
    ]
    linha_keys = [
        "linha_digitavel",
        "linha",
        "bar_code",
        "barcode",
        "digitable_line",
    ]
    boleto_url = ""
    linha = ""
    for key in url_keys:
        val = str(payload.get(key, "")).strip()
        if val and val.lower().startswith(("http://", "https://")):
            boleto_url = val
            break
    for key in linha_keys:
        val = str(payload.get(key, "")).strip()
        if val:
            linha = _format_boleto_linha(val)
            break
    if not boleto_url:
        for val in payload.values():
            if isinstance(val, dict):
                nested_url, nested_linha = _extract_boleto_info_from_json(val)
                if nested_url and not boleto_url:
                    boleto_url = nested_url
                if nested_linha and not linha:
                    linha = nested_linha
            if boleto_url and linha:
                break
    return boleto_url, linha

def generate_boleto_for_receivable(rec_obj, force=False):
    if not isinstance(rec_obj, dict):
        return False, "recebimento invalido"
    if rec_obj.get("boleto_url") and not force:
        return True, "boleto ja gerado"

    student = _find_student_by_name(rec_obj.get("aluno", ""))
    api_url = str(_finance_config_value("ACTIVE_BOLETO_API_URL", "boleto_api_url", "")).strip()
    api_key = str(_finance_config_value("ACTIVE_BOLETO_API_KEY", "boleto_api_key", "")).strip()
    boleto_url = ""
    linha = ""
    erro_api = ""

    if api_url:
        payload = {
            "codigo": str(rec_obj.get("codigo", "")).strip(),
            "aluno": str(rec_obj.get("aluno", "")).strip(),
            "descricao": str(rec_obj.get("descricao", "")).strip(),
            "valor": parse_money(rec_obj.get("valor_parcela", rec_obj.get("valor", ""))),
            "valor_formatado": str(rec_obj.get("valor_parcela", rec_obj.get("valor", ""))).strip(),
            "vencimento": str(rec_obj.get("vencimento", "")).strip(),
            "categoria": str(rec_obj.get("categoria", "")).strip(),
            "parcela": str(rec_obj.get("parcela", "")).strip(),
            "cobranca": str(rec_obj.get("cobranca", "")).strip(),
            "aluno_cpf": str(student.get("cpf", "")).strip() if isinstance(student, dict) else "",
            "aluno_email": str(student.get("email", "")).strip() if isinstance(student, dict) else "",
        }
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "User-Agent": "Active-Wiz-Automation/1.0",
        }
        if api_key:
            auth_header = str(_finance_config_value("ACTIVE_BOLETO_API_AUTH_HEADER", "boleto_api_auth_header", "Authorization")).strip() or "Authorization"
            if auth_header.lower() == "authorization":
                headers["Authorization"] = api_key if api_key.lower().startswith("bearer ") else f"Bearer {api_key}"
            else:
                headers[auth_header] = api_key
        status, ct, body, err = _http_request(
            "POST",
            api_url,
            headers=headers,
            json_payload=payload,
            timeout=20,
        )
        parsed, preview = _try_parse_json(ct, body)
        ok_http = status is not None and 200 <= int(status) < 300
        if ok_http and isinstance(parsed, dict):
            boleto_url, linha = _extract_boleto_info_from_json(parsed)
        if not ok_http:
            erro_api = f"falha api boleto (HTTP {status})"
            if err:
                erro_api += f" {err}"
            elif preview:
                erro_api += f" {preview[:120]}"

    if not boleto_url:
        template = str(_finance_config_value("ACTIVE_BOLETO_LINK_TEMPLATE", "boleto_link_template", "")).strip()
        base_url = str(_finance_config_value("ACTIVE_BOLETO_BASE_URL", "boleto_base_url", "")).strip()
        if template:
            boleto_url = _build_boleto_link_from_template(template, rec_obj, student)
        elif base_url:
            params = {
                "codigo": str(rec_obj.get("codigo", "")).strip(),
                "aluno": str(rec_obj.get("aluno", "")).strip(),
                "valor": str(rec_obj.get("valor_parcela", rec_obj.get("valor", ""))).strip(),
                "vencimento": str(rec_obj.get("vencimento", "")).strip(),
                "parcela": str(rec_obj.get("parcela", "")).strip(),
            }
            sep = "&" if "?" in base_url else "?"
            boleto_url = f"{base_url}{sep}{urlencode(params)}"

    if not linha:
        linha = _default_boleto_linha(rec_obj)

    if not boleto_url and not linha:
        msg = "configure ACTIVE_BOLETO_LINK_TEMPLATE ou ACTIVE_BOLETO_BASE_URL para gerar boleto"
        if erro_api:
            msg = f"{msg} ({erro_api})"
        return False, msg

    rec_obj["boleto_url"] = str(boleto_url).strip()
    rec_obj["boleto_linha_digitavel"] = str(linha).strip()
    rec_obj["boleto_status"] = "Gerado"
    rec_obj["boleto_gerado_em"] = datetime.datetime.now().strftime("%d/%m/%Y %H:%M")
    save_list(RECEIVABLES_FILE, st.session_state.get("receivables", []))
    if erro_api and not rec_obj.get("boleto_url"):
        return True, f"boleto gerado por link local ({erro_api})"
    return True, "boleto gerado"

def send_receivable_boleto_to_student(rec_obj):
    if not isinstance(rec_obj, dict):
        return False, "recebimento invalido", {"email_total": 0, "email_ok": 0, "whatsapp_total": 0, "whatsapp_ok": 0}
    if str(rec_obj.get("categoria_lancamento", "Aluno")).strip() != "Aluno":
        return False, "envio automatico disponivel apenas para lancamentos de aluno", {"email_total": 0, "email_ok": 0, "whatsapp_total": 0, "whatsapp_ok": 0}
    student = _find_student_by_name(rec_obj.get("aluno", ""))
    if not student:
        return False, "aluno nao encontrado para envio", {"email_total": 0, "email_ok": 0, "whatsapp_total": 0, "whatsapp_ok": 0}

    ok_gen, status_gen = generate_boleto_for_receivable(rec_obj, force=False)
    if not ok_gen:
        return False, status_gen, {"email_total": 0, "email_ok": 0, "whatsapp_total": 0, "whatsapp_ok": 0}

    valor = str(rec_obj.get("valor_parcela", rec_obj.get("valor", ""))).strip()
    assunto = f"[Active] Boleto {rec_obj.get('descricao', 'Mensalidade')} - {rec_obj.get('vencimento', '')}"
    corpo = (
        f"Ola, {student.get('nome', 'Aluno')}.\n\n"
        f"Seu boleto esta disponivel.\n"
        f"Descricao: {rec_obj.get('descricao', '')}\n"
        f"Valor: {valor}\n"
        f"Vencimento: {rec_obj.get('vencimento', '')}\n"
        f"Parcela: {rec_obj.get('parcela', '')}\n"
        f"Codigo: {rec_obj.get('codigo', '')}\n"
    )
    if rec_obj.get("boleto_linha_digitavel"):
        corpo += f"Linha digitavel: {rec_obj.get('boleto_linha_digitavel')}\n"
    if rec_obj.get("boleto_url"):
        corpo += f"Boleto: {rec_obj.get('boleto_url')}\n"

    stats = _notify_direct_contacts(
        student.get("nome", "Aluno"),
        _message_recipients_for_student(student),
        _student_whatsapp_recipients(student),
        assunto,
        corpo,
        "Financeiro Boleto",
    )

    rec_obj["boleto_enviado_em"] = datetime.datetime.now().strftime("%d/%m/%Y %H:%M")
    rec_obj["boleto_enviado_canais"] = (
        f"email {stats.get('email_ok', 0)}/{stats.get('email_total', 0)} | "
        f"whatsapp {stats.get('whatsapp_ok', 0)}/{stats.get('whatsapp_total', 0)}"
    )
    save_list(RECEIVABLES_FILE, st.session_state.get("receivables", []))

    return True, "boleto enviado", stats

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

def _wiz_to_bool(value, default=False):
    if isinstance(value, bool):
        return value
    txt = str(value or "").strip().lower()
    if txt in ("1", "true", "sim", "yes", "y", "on"):
        return True
    if txt in ("0", "false", "nao", "não", "no", "n", "off"):
        return False
    return bool(default)

def _wiz_norm_text(value):
    text = str(value or "").strip().lower()
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    return re.sub(r"\s+", " ", text).strip()

def _wiz_digits(value):
    return re.sub(r"\D", "", str(value or ""))

def _wiz_can_operate_system():
    role = str(st.session_state.get("role", "")).strip()
    profile = str(st.session_state.get("account_profile", role)).strip()
    allowed_profiles = {"Admin", "Coordenador"}
    if role != "Coordenador":
        return False, f"perfil atual sem permissao para execucao automatica ({role or 'desconhecido'})"
    if profile not in allowed_profiles:
        return False, f"perfil da conta sem permissao ({profile or 'desconhecido'})"
    return True, ""

def _wiz_mask_secret(value):
    raw = str(value or "")
    if not raw:
        return ""
    if len(raw) <= 4:
        return "*" * len(raw)
    return f"{raw[:2]}{'*' * (len(raw) - 4)}{raw[-2:]}"

def _wiz_sanitize_action_data(data, depth=0):
    if depth > 4:
        return "<depth_limit>"
    if isinstance(data, dict):
        out = {}
        for k, v in data.items():
            key_txt = str(k)
            low = key_txt.lower()
            is_sensitive = any(token in low for token in ("senha", "password", "token", "secret", "apikey", "api_key", "authorization"))
            if is_sensitive:
                out[key_txt] = _wiz_mask_secret(v)
            else:
                out[key_txt] = _wiz_sanitize_action_data(v, depth + 1)
        return out
    if isinstance(data, list):
        return [_wiz_sanitize_action_data(v, depth + 1) for v in data[:100]]
    if isinstance(data, (bytes, bytearray)):
        return f"<bytes:{len(data)}>"
    if isinstance(data, (str, int, float, bool)) or data is None:
        return data
    try:
        return str(data)
    except Exception:
        return "<unserializable>"

def _wiz_log_action_batch(actions, reports):
    if not isinstance(reports, list) or not reports:
        return
    existing = load_list(WIZ_ACTION_AUDIT_FILE)
    logs = existing if isinstance(existing, list) else []
    now_txt = datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    actor = str(st.session_state.get("user_name", "")).strip()
    role = str(st.session_state.get("role", "")).strip()
    profile = str(st.session_state.get("account_profile", "")).strip()

    for idx, rep in enumerate(reports):
        if not isinstance(rep, dict):
            continue
        action_obj = actions[idx] if isinstance(actions, list) and idx < len(actions) and isinstance(actions[idx], dict) else {}
        action_type = str(action_obj.get("type", rep.get("type", ""))).strip()
        action_data = action_obj.get("data", {}) if isinstance(action_obj.get("data", {}), dict) else {}
        logs.append(
            {
                "timestamp": now_txt,
                "usuario": actor,
                "role": role,
                "perfil_conta": profile,
                "action": action_type,
                "ok": bool(rep.get("ok", False)),
                "message": str(rep.get("message", "")).strip(),
                "data": _wiz_sanitize_action_data(action_data),
            }
        )
    if len(logs) > 5000:
        logs = logs[-5000:]
    save_list(WIZ_ACTION_AUDIT_FILE, logs)

def _wiz_book_defaults_from_id(book_id):
    bid = str(book_id or "").strip().lower()
    defaults = {"titulo": "", "categoria": "", "nivel": "", "parte": ""}
    mt = re.match(r"^ingles_livro_(\d+)_parte_(\d+)$", bid)
    if mt:
        num = int(mt.group(1))
        part = int(mt.group(2))
        defaults["titulo"] = f"Ingles - Livro {num} - Parte {part}"
        defaults["categoria"] = "Ingles"
        defaults["nivel"] = f"Livro {num}"
        defaults["parte"] = f"Parte {part}"
        return defaults

    tpl = next(
        (
            t
            for t in library_book_templates()
            if str(t.get("book_id", "")).strip().lower() == bid
        ),
        None,
    )
    if isinstance(tpl, dict):
        defaults["titulo"] = str(tpl.get("titulo", "")).strip()
        defaults["categoria"] = str(tpl.get("categoria", "")).strip()
        defaults["nivel"] = str(tpl.get("nivel", "")).strip()
        defaults["parte"] = str(tpl.get("parte", "")).strip()
    return defaults

def _wiz_guess_book_id_from_filename(file_name):
    stem = Path(str(file_name or "").strip()).stem
    if not stem:
        return ""
    candidate = infer_library_book_id(
        {
            "titulo": stem,
            "nivel": stem,
            "categoria": stem,
            "parte": stem,
        }
    )
    if candidate:
        return candidate
    norm = _wiz_norm_text(stem).replace("-", " ").replace("_", " ")
    mt = re.search(r"livro\s*(\d+)", norm)
    if mt:
        part = 2 if "parte 2" in norm else 1
        return f"ingles_livro_{int(mt.group(1))}_parte_{part}"
    if "lideranca" in norm:
        return "lideranca"
    if "empreendedorismo" in norm:
        return "empreendedorismo"
    if "educacao financeira" in norm:
        return "educacao_financeira"
    if "inteligencia emocional" in norm:
        return "inteligencia_emocional"
    return ""

def _wiz_actions_from_book_uploads(user_text, uploaded_files):
    request_norm = _wiz_norm_text(user_text)
    triggers = ("livro", "biblioteca", "anex", "post", "public", "cadastr")
    if not any(token in request_norm for token in triggers):
        return []

    actions = []
    for up in uploaded_files or []:
        file_name = str(getattr(up, "name", "") or "").strip()
        if not file_name:
            continue
        try:
            raw = up.getvalue() if hasattr(up, "getvalue") else b""
        except Exception:
            raw = b""
        if not isinstance(raw, (bytes, bytearray)) or not raw:
            continue

        book_id = _wiz_guess_book_id_from_filename(file_name)
        defaults = _wiz_book_defaults_from_id(book_id)
        title_fallback = Path(file_name).stem.replace("_", " ").replace("-", " ").strip() or "Livro"
        actions.append(
            {
                "type": "cadastrar_livro",
                "data": {
                    "book_id": book_id,
                    "titulo": defaults.get("titulo") or title_fallback,
                    "categoria": defaults.get("categoria", ""),
                    "nivel": defaults.get("nivel", ""),
                    "parte": defaults.get("parte", ""),
                    "file_name": file_name,
                    "file_bytes": bytes(raw),
                },
            }
        )
    return actions

def _wiz_build_execution_message(base_reply, reports, missing=None):
    base = str(base_reply or "").strip()
    missing = missing if isinstance(missing, list) else []
    reports = reports if isinstance(reports, list) else []
    total = len(reports)
    ok = len([r for r in reports if isinstance(r, dict) and r.get("ok")])
    fail = total - ok
    lines = []
    if base:
        lines.append(base)
    if total > 0:
        lines.append(f"Execução no sistema: {ok} concluída(s), {fail} com falha.")
        for rep in reports[:8]:
            if not isinstance(rep, dict):
                continue
            icon = "OK" if rep.get("ok") else "Falha"
            msg = str(rep.get("message", "")).strip()
            if msg:
                lines.append(f"- {icon}: {msg}")
    if missing:
        pend = [str(m).strip() for m in missing if str(m).strip()]
        if pend:
            lines.append("Dados faltantes para próximas ações:")
            for m in pend[:8]:
                lines.append(f"- {m}")
    if not lines:
        lines.append("Não houve ação para executar.")
    return "\n".join(lines)

def _wiz_plan_actions_with_ai(user_text, chat_history=None):
    api_key = get_groq_api_key()
    if not api_key:
        return {"reply": "", "actions": [], "missing": []}

    history_lines = []
    for msg in (chat_history or [])[-6:]:
        if not isinstance(msg, dict):
            continue
        role = str(msg.get("role", "")).strip().lower()
        content = str(msg.get("content", "")).strip()
        if role in ("user", "assistant") and content:
            history_lines.append(f"{role}: {content}")
    hist_txt = "\n".join(history_lines)

    schema_hint = (
        "{"
        '"reply":"texto curto ao usuario",'
        '"actions":[{"type":"acao","data":{}}],'
        '"missing":["campo faltante"]'
        "}"
    )
    try:
        context_txt = get_active_context_text()
    except Exception:
        context_txt = ""
    system_prompt = "\n".join(
        [
            "Voce e um orquestrador de acoes internas do sistema Active Educacional.",
            "Retorne SOMENTE JSON valido, sem markdown.",
            "Nunca invente dados obrigatorios que nao foram informados.",
            "Nunca invente fatos do sistema (nomes, turmas, valores, status, quantidades, datas ou links).",
            "Se nao houver confirmacao no contexto/dados do pedido, nao afirme certeza e preencha missing com o que falta.",
            "Se o pedido for apenas pergunta, orientacao ou analise, retorne actions = [].",
            "Se o pedido exigir execucao interna, preencha actions com os tipos suportados.",
            "Nunca inclua DietHealth.",
            "Para enviar_comunicado com turma='Todas', use por padrao somente alunos com turma valida existente.",
            "Inclua alunos sem turma apenas se o usuario pedir explicitamente.",
            "Se o usuario pedir envio para turmas existentes, use no data: {\"somente_turmas_existentes\": true}.",
            "Acoes suportadas:",
            "- cadastrar_aluno",
            "- atualizar_aluno",
            "- excluir_aluno",
            "- cadastrar_professor",
            "- atualizar_professor",
            "- excluir_professor",
            "- cadastrar_usuario",
            "- atualizar_usuario",
            "- excluir_usuario",
            "- cadastrar_turma",
            "- atualizar_turma",
            "- excluir_turma",
            "- agendar_aula",
            "- atualizar_aula",
            "- excluir_aula",
            "- atualizar_link_turma",
            "- enviar_comunicado",
            "- publicar_noticia",
            "- cadastrar_livro",
            "- atualizar_livro",
            "- excluir_livro",
            "- lancar_recebivel",
            "- atualizar_recebivel",
            "- excluir_recebivel",
            "- baixar_recebivel",
            "- lancar_despesa",
            "- atualizar_despesa",
            "- excluir_despesa",
            "- baixar_despesa",
            "- lancar_nota",
            "Para comunicados para alunos/turmas, prefira enviar_comunicado.",
            "Para exclusao/baixa use somente quando o pedido do usuario for explicito.",
            "Nao confirme execucao na resposta; a confirmacao final vem do relatorio de execucao do sistema.",
            ("Contexto atual:\n" + context_txt) if context_txt else "Contexto atual: indisponivel.",
            f"Formato JSON: {schema_hint}",
        ]
    )
    user_prompt = (
        f"Historico recente:\n{hist_txt}\n\n"
        f"Pedido atual do usuario:\n{str(user_text or '').strip()}\n\n"
        "Gere o JSON."
    )
    try:
        client = OpenAI(api_key=api_key, base_url="https://api.groq.com/openai/v1")
        model_name = os.getenv("ACTIVE_WIZ_MODEL", os.getenv("ACTIVE_CHATBOT_MODEL", "llama-3.3-70b-versatile"))
        result = client.chat.completions.create(
            model=model_name,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.05,
            max_tokens=1400,
        )
        raw = (result.choices[0].message.content or "").strip()
        obj = _extract_first_json(raw)
    except Exception:
        obj = {}

    reply = str(obj.get("reply", "")).strip()
    missing = obj.get("missing", [])
    if not isinstance(missing, list):
        missing = []
    actions = obj.get("actions", [])
    if isinstance(actions, dict):
        actions = [actions]
    if not isinstance(actions, list):
        actions = []

    clean_actions = []
    for a in actions:
        if not isinstance(a, dict):
            continue
        kind = str(a.get("type", "")).strip().lower()
        data = a.get("data", {})
        if not kind or not isinstance(data, dict):
            continue
        clean_actions.append({"type": kind, "data": data})

    return {
        "reply": reply,
        "actions": clean_actions,
        "missing": [str(m).strip() for m in missing if str(m).strip()],
    }

def _wiz_execute_actions(actions):
    actions = actions if isinstance(actions, list) else []
    if not actions:
        return []

    reports = []
    can_run, deny_msg = _wiz_can_operate_system()
    if not can_run:
        for action in actions:
            action_type = str((action or {}).get("type", "")).strip().lower() if isinstance(action, dict) else ""
            reports.append(
                {
                    "type": action_type or "acao",
                    "ok": False,
                    "message": f"execucao bloqueada: {deny_msg}",
                }
            )
        _wiz_log_action_batch(actions, reports)
        return reports

    alias = {
        "incluir_aluno": "cadastrar_aluno",
        "criar_aluno": "cadastrar_aluno",
        "editar_aluno": "atualizar_aluno",
        "alterar_aluno": "atualizar_aluno",
        "deletar_aluno": "excluir_aluno",
        "remover_aluno": "excluir_aluno",
        "incluir_professor": "cadastrar_professor",
        "criar_professor": "cadastrar_professor",
        "editar_professor": "atualizar_professor",
        "alterar_professor": "atualizar_professor",
        "deletar_professor": "excluir_professor",
        "remover_professor": "excluir_professor",
        "incluir_usuario": "cadastrar_usuario",
        "criar_usuario": "cadastrar_usuario",
        "editar_usuario": "atualizar_usuario",
        "alterar_usuario": "atualizar_usuario",
        "deletar_usuario": "excluir_usuario",
        "remover_usuario": "excluir_usuario",
        "incluir_turma": "cadastrar_turma",
        "criar_turma": "cadastrar_turma",
        "editar_turma": "atualizar_turma",
        "alterar_turma": "atualizar_turma",
        "deletar_turma": "excluir_turma",
        "remover_turma": "excluir_turma",
        "lançar_recebivel": "lancar_recebivel",
        "lancar_recebimento": "lancar_recebivel",
        "atualizar_recebimento": "atualizar_recebivel",
        "excluir_recebimento": "excluir_recebivel",
        "deletar_recebivel": "excluir_recebivel",
        "dar_baixa_recebivel": "baixar_recebivel",
        "baixa_recebivel": "baixar_recebivel",
        "lançar_despesa": "lancar_despesa",
        "deletar_despesa": "excluir_despesa",
        "dar_baixa_despesa": "baixar_despesa",
        "baixa_despesa": "baixar_despesa",
        "incluir_livro": "cadastrar_livro",
        "criar_livro": "cadastrar_livro",
        "anexar_livro": "cadastrar_livro",
        "postar_livro": "cadastrar_livro",
        "editar_livro": "atualizar_livro",
        "alterar_livro": "atualizar_livro",
        "deletar_livro": "excluir_livro",
        "remover_livro": "excluir_livro",
        "atualizar_agenda": "atualizar_aula",
        "editar_aula": "atualizar_aula",
        "alterar_aula": "atualizar_aula",
        "cancelar_aula": "excluir_aula",
        "deletar_aula": "excluir_aula",
        "remover_aula": "excluir_aula",
        "enviar_aviso": "enviar_comunicado",
        "publicar_comunicado": "enviar_comunicado",
        "comunicar_turma": "enviar_comunicado",
        "enviar_mensagem_turma": "enviar_comunicado",
        "disparar_comunicado": "enviar_comunicado",
    }

    def _find_indices_by_codes(items, codes):
        code_set = {str(c).strip().upper() for c in (codes or []) if str(c).strip()}
        if not code_set:
            return []
        return [i for i, obj in enumerate(items) if str(obj.get("codigo", "")).strip().upper() in code_set]

    def _find_receivable_indices(data):
        items = st.session_state.get("receivables", [])
        codes = []
        code_one = str(data.get("codigo", "")).strip()
        if code_one:
            codes.append(code_one)
        code_many = data.get("codigos", [])
        if isinstance(code_many, list):
            codes.extend([str(c).strip() for c in code_many if str(c).strip()])
        idx = _find_indices_by_codes(items, codes)
        if idx:
            return idx
        lote = str(data.get("lote_id", "")).strip()
        if lote:
            return [i for i, r in enumerate(items) if str(r.get("lote_id", "")).strip() == lote]
        return []

    def _find_payable_indices(data):
        items = st.session_state.get("payables", [])
        codes = []
        code_one = str(data.get("codigo", "")).strip()
        if code_one:
            codes.append(code_one)
        code_many = data.get("codigos", [])
        if isinstance(code_many, list):
            codes.extend([str(c).strip() for c in code_many if str(c).strip()])
        idx = _find_indices_by_codes(items, codes)
        if idx:
            return idx
        lote = str(data.get("lote_id", "")).strip()
        if lote:
            return [i for i, r in enumerate(items) if str(r.get("lote_id", "")).strip() == lote]
        return []

    def _norm(value):
        return _wiz_norm_text(value)

    def _match_text(value, expected):
        value_norm = _norm(value)
        expected_norm = _norm(expected)
        if not expected_norm:
            return True
        if not value_norm:
            return False
        return expected_norm in value_norm or value_norm in expected_norm

    def _find_student_indices(data):
        items = st.session_state.get("students", [])
        nome = str(data.get("nome", data.get("aluno", ""))).strip()
        matricula = str(data.get("matricula", "")).strip()
        email = str(data.get("email", "")).strip().lower()
        cpf = _wiz_digits(data.get("cpf", ""))
        usuario = str(data.get("usuario", data.get("login", ""))).strip().lower()
        if not any([nome, matricula, email, cpf, usuario]):
            return []
        found = []
        for idx, obj in enumerate(items):
            if matricula and str(obj.get("matricula", "")).strip() != matricula:
                continue
            if email and str(obj.get("email", "")).strip().lower() != email:
                continue
            if cpf and _wiz_digits(obj.get("cpf", "")) != cpf:
                continue
            if usuario and str(obj.get("usuario", "")).strip().lower() != usuario:
                continue
            if nome and not _match_text(obj.get("nome", ""), nome):
                continue
            found.append(idx)
        return found

    def _find_teacher_indices(data):
        items = st.session_state.get("teachers", [])
        nome = str(data.get("nome", data.get("professor", ""))).strip()
        email = str(data.get("email", "")).strip().lower()
        usuario = str(data.get("usuario", data.get("login", ""))).strip().lower()
        if not any([nome, email, usuario]):
            return []
        found = []
        for idx, obj in enumerate(items):
            if email and str(obj.get("email", "")).strip().lower() != email:
                continue
            if usuario and str(obj.get("usuario", "")).strip().lower() != usuario:
                continue
            if nome and not _match_text(obj.get("nome", ""), nome):
                continue
            found.append(idx)
        return found

    def _find_user_indices(data):
        items = st.session_state.get("users", [])
        usuario = str(data.get("usuario", data.get("login", ""))).strip().lower()
        email = str(data.get("email", "")).strip().lower()
        pessoa = str(data.get("pessoa", data.get("nome", ""))).strip()
        perfil = str(data.get("perfil", "")).strip().lower()
        if not any([usuario, email, pessoa, perfil]):
            return []
        found = []
        for idx, obj in enumerate(items):
            if usuario and str(obj.get("usuario", "")).strip().lower() != usuario:
                continue
            if email and str(obj.get("email", "")).strip().lower() != email:
                continue
            if pessoa and not _match_text(obj.get("pessoa", ""), pessoa):
                continue
            if perfil and str(obj.get("perfil", "")).strip().lower() != perfil:
                continue
            found.append(idx)
        return found

    def _find_class_indices(data):
        items = st.session_state.get("classes", [])
        nome = str(data.get("nome", data.get("turma", ""))).strip()
        professor = str(data.get("professor", "")).strip()
        livro = str(data.get("livro", "")).strip()
        if not any([nome, professor, livro]):
            return []
        found = []
        for idx, obj in enumerate(items):
            if nome and not _match_text(obj.get("nome", ""), nome):
                continue
            if professor and not _match_text(obj.get("professor", ""), professor):
                continue
            if livro and not _match_text(obj.get("livro", ""), livro):
                continue
            found.append(idx)
        return found

    def _find_agenda_indices(data):
        items = st.session_state.get("agenda", [])
        turma = str(data.get("turma", "")).strip()
        titulo = str(data.get("titulo", "")).strip()
        professor = str(data.get("professor", "")).strip()
        data_txt = str(data.get("data", "")).strip()
        hora_txt = str(data.get("hora", "")).strip()
        if not any([turma, titulo, professor, data_txt, hora_txt]):
            return []
        found = []
        for idx, obj in enumerate(items):
            if turma and not _match_text(obj.get("turma", ""), turma):
                continue
            if titulo and not _match_text(obj.get("titulo", ""), titulo):
                continue
            if professor and not _match_text(obj.get("professor", ""), professor):
                continue
            if data_txt and str(obj.get("data", "")).strip() != data_txt:
                continue
            if hora_txt and str(obj.get("hora", "")).strip() != hora_txt:
                continue
            found.append(idx)
        return found

    def _find_book_indices(data):
        items = st.session_state.get("books", [])
        bid = str(data.get("book_id", "")).strip().lower()
        titulo = str(data.get("titulo", "")).strip()
        categoria = str(data.get("categoria", "")).strip()
        nivel = str(data.get("nivel", "")).strip()
        parte = str(data.get("parte", "")).strip()
        if not any([bid, titulo, categoria, nivel, parte]):
            return []
        found = []
        for idx, obj in enumerate(items):
            if bid and str(obj.get("book_id", "")).strip().lower() != bid:
                continue
            if titulo and not _match_text(obj.get("titulo", ""), titulo):
                continue
            if categoria and not _match_text(obj.get("categoria", ""), categoria):
                continue
            if nivel and not _match_text(obj.get("nivel", ""), nivel):
                continue
            if parte and not _match_text(obj.get("parte", ""), parte):
                continue
            found.append(idx)
        return found

    for action in actions:
        kind = str((action or {}).get("type", "")).strip().lower()
        kind = alias.get(kind, kind)
        data = action.get("data", {}) if isinstance(action, dict) else {}
        try:
            if kind == "cadastrar_aluno":
                nome = str(data.get("nome", "")).strip()
                email = str(data.get("email", "")).strip().lower()
                celular = str(data.get("celular", data.get("telefone", ""))).strip()
                if not nome:
                    reports.append({"type": kind, "ok": False, "message": "nome e obrigatorio"})
                    continue
                if not email and celular:
                    email = ""
                novo = {
                    "nome": nome,
                    "matricula": _next_student_matricula(st.session_state.get("students", [])),
                    "idade": int(data.get("idade") or 18),
                    "genero": str(data.get("genero", data.get("sexo", ""))).strip(),
                    "data_nascimento": str(data.get("data_nascimento", "")),
                    "celular": celular,
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
            elif kind == "atualizar_aluno":
                idx_list = _find_student_indices(data)
                if not idx_list:
                    reports.append({"type": kind, "ok": False, "message": "aluno nao encontrado"})
                    continue
                if not _wiz_to_bool(data.get("aplicar_em_lote", False), default=False):
                    idx_list = idx_list[:1]
                touched = 0
                for idx in idx_list:
                    if idx < 0 or idx >= len(st.session_state.get("students", [])):
                        continue
                    obj = st.session_state["students"][idx]
                    old_nome = str(obj.get("nome", "")).strip()
                    new_nome = str(data.get("novo_nome", data.get("nome", ""))).strip()
                    if new_nome:
                        obj["nome"] = new_nome
                    if str(data.get("matricula", "")).strip():
                        obj["matricula"] = str(data.get("matricula", "")).strip()
                    if str(data.get("idade", "")).strip():
                        obj["idade"] = parse_int(data.get("idade")) or obj.get("idade", "")
                    if str(data.get("sexo", data.get("genero", ""))).strip():
                        obj["genero"] = str(data.get("sexo", data.get("genero", ""))).strip()
                    if str(data.get("data_nascimento", "")).strip():
                        obj["data_nascimento"] = str(data.get("data_nascimento", "")).strip()
                    if str(data.get("celular", data.get("telefone", ""))).strip():
                        obj["celular"] = str(data.get("celular", data.get("telefone", ""))).strip()
                    if str(data.get("email", "")).strip():
                        obj["email"] = str(data.get("email", "")).strip().lower()
                    if str(data.get("rg", "")).strip():
                        obj["rg"] = str(data.get("rg", "")).strip()
                    if str(data.get("cpf", "")).strip():
                        obj["cpf"] = str(data.get("cpf", "")).strip()
                    if str(data.get("cidade_natal", "")).strip():
                        obj["cidade_natal"] = str(data.get("cidade_natal", "")).strip()
                    if str(data.get("pais", "")).strip():
                        obj["pais"] = str(data.get("pais", "")).strip()
                    if str(data.get("cep", "")).strip():
                        obj["cep"] = str(data.get("cep", "")).strip()
                    if str(data.get("cidade", "")).strip():
                        obj["cidade"] = str(data.get("cidade", "")).strip()
                    if str(data.get("bairro", "")).strip():
                        obj["bairro"] = str(data.get("bairro", "")).strip()
                    if str(data.get("rua", data.get("endereco", ""))).strip():
                        obj["rua"] = str(data.get("rua", data.get("endereco", ""))).strip()
                    if str(data.get("numero", "")).strip():
                        obj["numero"] = str(data.get("numero", "")).strip()
                    if str(data.get("complemento", data.get("observacao_endereco", ""))).strip():
                        obj["complemento"] = str(data.get("complemento", data.get("observacao_endereco", ""))).strip()
                    if str(data.get("turma", "")).strip():
                        obj["turma"] = str(data.get("turma", "")).strip()
                    if str(data.get("modulo", "")).strip():
                        obj["modulo"] = str(data.get("modulo", "")).strip()
                    if str(data.get("livro", "")).strip():
                        obj["livro"] = str(data.get("livro", "")).strip()
                    if str(data.get("usuario", data.get("login", ""))).strip():
                        obj["usuario"] = str(data.get("usuario", data.get("login", ""))).strip()
                    if str(data.get("senha", "")).strip():
                        obj["senha"] = str(data.get("senha", "")).strip()

                    if "responsavel" not in obj or not isinstance(obj.get("responsavel"), dict):
                        obj["responsavel"] = {}
                    if str(data.get("responsavel_nome", "")).strip():
                        obj["responsavel"]["nome"] = str(data.get("responsavel_nome", "")).strip()
                    if str(data.get("responsavel_cpf", "")).strip():
                        obj["responsavel"]["cpf"] = str(data.get("responsavel_cpf", "")).strip()
                    if str(data.get("responsavel_celular", "")).strip():
                        obj["responsavel"]["celular"] = str(data.get("responsavel_celular", "")).strip()
                    if str(data.get("responsavel_email", "")).strip():
                        obj["responsavel"]["email"] = str(data.get("responsavel_email", "")).strip().lower()

                    new_nome_eff = str(obj.get("nome", "")).strip()
                    if old_nome and new_nome_eff and old_nome != new_nome_eff:
                        for rec in st.session_state.get("receivables", []):
                            if str(rec.get("aluno", "")).strip() == old_nome:
                                rec["aluno"] = new_nome_eff
                        for g in st.session_state.get("grades", []):
                            if str(g.get("aluno", "")).strip() == old_nome:
                                g["aluno"] = new_nome_eff
                        save_list(RECEIVABLES_FILE, st.session_state.get("receivables", []))
                        save_list(GRADES_FILE, st.session_state.get("grades", []))
                    touched += 1
                save_list(STUDENTS_FILE, st.session_state["students"])
                reports.append({"type": kind, "ok": True, "message": f"aluno atualizado em {touched} registro(s)"})
            elif kind == "excluir_aluno":
                idx_list = _find_student_indices(data)
                if not idx_list:
                    reports.append({"type": kind, "ok": False, "message": "aluno nao encontrado para exclusao"})
                    continue
                usuarios_remover = set()
                nomes_removidos = []
                for idx in sorted(set(idx_list), reverse=True):
                    if 0 <= idx < len(st.session_state.get("students", [])):
                        aluno_obj = st.session_state["students"][idx]
                        usuario_aluno = str(aluno_obj.get("usuario", "")).strip().lower()
                        if usuario_aluno:
                            usuarios_remover.add(usuario_aluno)
                        nomes_removidos.append(str(aluno_obj.get("nome", "")).strip())
                        st.session_state["students"].pop(idx)
                save_list(STUDENTS_FILE, st.session_state["students"])

                if _wiz_to_bool(data.get("remover_usuario", True), default=True) and usuarios_remover:
                    st.session_state["users"] = [
                        u for u in st.session_state.get("users", [])
                        if not (
                            str(u.get("usuario", "")).strip().lower() in usuarios_remover
                            and str(u.get("perfil", "")).strip() == "Aluno"
                        )
                    ]
                    save_users(st.session_state["users"])

                if _wiz_to_bool(data.get("excluir_financeiro_relacionado", False), default=False):
                    nome_norm_set = {_wiz_norm_text(n) for n in nomes_removidos if str(n).strip()}
                    st.session_state["receivables"] = [
                        rec for rec in st.session_state.get("receivables", [])
                        if _wiz_norm_text(rec.get("aluno", "")) not in nome_norm_set
                    ]
                    save_list(RECEIVABLES_FILE, st.session_state["receivables"])

                reports.append({"type": kind, "ok": True, "message": f"{len(set(idx_list))} aluno(s) excluido(s)"})
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
            elif kind == "atualizar_professor":
                idx_list = _find_teacher_indices(data)
                if not idx_list:
                    reports.append({"type": kind, "ok": False, "message": "professor nao encontrado"})
                    continue
                if not _wiz_to_bool(data.get("aplicar_em_lote", False), default=False):
                    idx_list = idx_list[:1]
                touched = 0
                for idx in idx_list:
                    if idx < 0 or idx >= len(st.session_state.get("teachers", [])):
                        continue
                    obj = st.session_state["teachers"][idx]
                    old_nome = str(obj.get("nome", "")).strip()
                    new_nome = str(data.get("novo_nome", data.get("nome", ""))).strip()
                    if new_nome:
                        obj["nome"] = new_nome
                    if str(data.get("area", "")).strip():
                        obj["area"] = str(data.get("area", "")).strip()
                    if str(data.get("email", "")).strip():
                        obj["email"] = str(data.get("email", "")).strip().lower()
                    if str(data.get("celular", data.get("telefone", ""))).strip():
                        obj["celular"] = str(data.get("celular", data.get("telefone", ""))).strip()
                    if str(data.get("usuario", data.get("login", ""))).strip():
                        obj["usuario"] = str(data.get("usuario", data.get("login", ""))).strip()
                    if str(data.get("senha", "")).strip():
                        obj["senha"] = str(data.get("senha", "")).strip()

                    if old_nome and str(obj.get("nome", "")).strip() and old_nome != str(obj.get("nome", "")).strip():
                        for turma in st.session_state.get("classes", []):
                            if str(turma.get("professor", "")).strip() == old_nome:
                                turma["professor"] = str(obj.get("nome", "")).strip()
                        save_list(CLASSES_FILE, st.session_state.get("classes", []))

                    login_prof = str(obj.get("usuario", "")).strip()
                    senha_prof = str(obj.get("senha", "")).strip()
                    if login_prof:
                        user_obj = find_user(login_prof)
                        if user_obj:
                            user_obj["perfil"] = "Professor"
                            user_obj["pessoa"] = str(obj.get("nome", "")).strip()
                            if senha_prof:
                                user_obj["senha"] = senha_prof
                            if str(obj.get("email", "")).strip():
                                user_obj["email"] = str(obj.get("email", "")).strip().lower()
                            if str(obj.get("celular", "")).strip():
                                user_obj["celular"] = str(obj.get("celular", "")).strip()
                        elif senha_prof:
                            st.session_state["users"].append(
                                {
                                    "usuario": login_prof,
                                    "senha": senha_prof,
                                    "perfil": "Professor",
                                    "pessoa": str(obj.get("nome", "")).strip(),
                                    "email": str(obj.get("email", "")).strip().lower(),
                                    "celular": str(obj.get("celular", "")).strip(),
                                }
                            )
                        save_users(st.session_state["users"])
                    touched += 1
                save_list(TEACHERS_FILE, st.session_state["teachers"])
                reports.append({"type": kind, "ok": True, "message": f"professor atualizado em {touched} registro(s)"})
            elif kind == "excluir_professor":
                idx_list = _find_teacher_indices(data)
                if not idx_list:
                    reports.append({"type": kind, "ok": False, "message": "professor nao encontrado para exclusao"})
                    continue
                logins_remove = set()
                nomes_remove = []
                for idx in sorted(set(idx_list), reverse=True):
                    if 0 <= idx < len(st.session_state.get("teachers", [])):
                        prof_obj = st.session_state["teachers"][idx]
                        logins_remove.add(str(prof_obj.get("usuario", "")).strip().lower())
                        nomes_remove.append(str(prof_obj.get("nome", "")).strip())
                        st.session_state["teachers"].pop(idx)
                save_list(TEACHERS_FILE, st.session_state["teachers"])

                nome_norm_set = {_wiz_norm_text(n) for n in nomes_remove if str(n).strip()}
                for turma in st.session_state.get("classes", []):
                    if _wiz_norm_text(turma.get("professor", "")) in nome_norm_set:
                        turma["professor"] = "Sem Professor"
                save_list(CLASSES_FILE, st.session_state["classes"])

                if _wiz_to_bool(data.get("remover_usuario", True), default=True):
                    st.session_state["users"] = [
                        u for u in st.session_state.get("users", [])
                        if not (
                            str(u.get("usuario", "")).strip().lower() in logins_remove
                            and str(u.get("perfil", "")).strip() == "Professor"
                        )
                    ]
                    save_users(st.session_state["users"])

                reports.append({"type": kind, "ok": True, "message": f"{len(set(idx_list))} professor(es) excluido(s)"})
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
            elif kind == "atualizar_usuario":
                idx_list = _find_user_indices(data)
                if not idx_list:
                    reports.append({"type": kind, "ok": False, "message": "usuario nao encontrado"})
                    continue
                if not _wiz_to_bool(data.get("aplicar_em_lote", False), default=False):
                    idx_list = idx_list[:1]
                new_login = str(data.get("novo_usuario", data.get("usuario_novo", ""))).strip()
                if new_login and len(idx_list) > 1:
                    reports.append({"type": kind, "ok": False, "message": "novo login so pode ser aplicado em um usuario por vez"})
                    continue
                if new_login:
                    exists_other = any(
                        str(u.get("usuario", "")).strip().lower() == new_login.lower()
                        and i not in idx_list
                        for i, u in enumerate(st.session_state.get("users", []))
                    )
                    if exists_other:
                        reports.append({"type": kind, "ok": False, "message": "novo login ja existe"})
                        continue

                touched = 0
                for idx in idx_list:
                    if idx < 0 or idx >= len(st.session_state.get("users", [])):
                        continue
                    obj = st.session_state["users"][idx]
                    old_login = str(obj.get("usuario", "")).strip()
                    if new_login:
                        obj["usuario"] = new_login
                    if str(data.get("senha", "")).strip():
                        obj["senha"] = str(data.get("senha", "")).strip()
                    if str(data.get("perfil", "")).strip():
                        perfil = str(data.get("perfil", "")).strip()
                        obj["perfil"] = perfil if perfil in ("Aluno", "Professor", "Coordenador", "Admin", "Comercial") else obj.get("perfil", "Coordenador")
                    if str(data.get("pessoa", data.get("nome", ""))).strip():
                        obj["pessoa"] = str(data.get("pessoa", data.get("nome", ""))).strip()
                    if str(data.get("email", "")).strip():
                        obj["email"] = str(data.get("email", "")).strip().lower()
                    if str(data.get("celular", data.get("telefone", ""))).strip():
                        obj["celular"] = str(data.get("celular", data.get("telefone", ""))).strip()

                    login_effective = str(obj.get("usuario", "")).strip()
                    if old_login and login_effective and old_login != login_effective:
                        for prof in st.session_state.get("teachers", []):
                            if str(prof.get("usuario", "")).strip() == old_login:
                                prof["usuario"] = login_effective
                                if str(obj.get("senha", "")).strip():
                                    prof["senha"] = str(obj.get("senha", "")).strip()
                        for aluno in st.session_state.get("students", []):
                            if str(aluno.get("usuario", "")).strip() == old_login:
                                aluno["usuario"] = login_effective
                                if str(obj.get("senha", "")).strip():
                                    aluno["senha"] = str(obj.get("senha", "")).strip()
                    touched += 1

                save_users(st.session_state["users"])
                save_list(TEACHERS_FILE, st.session_state.get("teachers", []))
                save_list(STUDENTS_FILE, st.session_state.get("students", []))
                reports.append({"type": kind, "ok": True, "message": f"usuario atualizado em {touched} registro(s)"})
            elif kind == "excluir_usuario":
                idx_list = _find_user_indices(data)
                if not idx_list:
                    reports.append({"type": kind, "ok": False, "message": "usuario nao encontrado para exclusao"})
                    continue
                logins = []
                for idx in sorted(set(idx_list), reverse=True):
                    if 0 <= idx < len(st.session_state.get("users", [])):
                        logins.append(str(st.session_state["users"][idx].get("usuario", "")).strip())
                        st.session_state["users"].pop(idx)
                save_users(st.session_state["users"])

                if _wiz_to_bool(data.get("desvincular_professor_aluno", True), default=True):
                    login_set = {str(l).strip() for l in logins if str(l).strip()}
                    for prof in st.session_state.get("teachers", []):
                        if str(prof.get("usuario", "")).strip() in login_set:
                            prof["usuario"] = ""
                            prof["senha"] = ""
                    for aluno in st.session_state.get("students", []):
                        if str(aluno.get("usuario", "")).strip() in login_set:
                            aluno["usuario"] = ""
                            aluno["senha"] = ""
                    save_list(TEACHERS_FILE, st.session_state.get("teachers", []))
                    save_list(STUDENTS_FILE, st.session_state.get("students", []))

                reports.append({"type": kind, "ok": True, "message": f"{len(set(idx_list))} usuario(s) excluido(s)"})
            elif kind == "cadastrar_turma":
                nome = str(data.get("nome", data.get("turma", ""))).strip()
                if not nome:
                    reports.append({"type": kind, "ok": False, "message": "nome da turma e obrigatorio"})
                    continue
                exists = next((t for t in st.session_state.get("classes", []) if str(t.get("nome", "")).strip().lower() == nome.lower()), None)
                if exists and not _wiz_to_bool(data.get("permitir_duplicado", False), default=False):
                    reports.append({"type": kind, "ok": False, "message": "turma ja existe"})
                    continue
                dias_raw = data.get("dias_semana", data.get("dias", []))
                if isinstance(dias_raw, str):
                    dias_semana = infer_class_days_from_text(dias_raw)
                elif isinstance(dias_raw, list):
                    dias_semana = [str(d).strip() for d in dias_raw if str(d).strip() in WEEKDAY_OPTIONS_PT]
                else:
                    dias_semana = []
                if not dias_semana:
                    dias_semana = [WEEKDAY_OPTIONS_PT[0]]
                hora_inicio_obj = parse_time(str(data.get("hora_inicio", data.get("hora", "19:00"))).strip() or "19:00")
                hora_inicio = hora_inicio_obj.strftime("%H:%M")
                hora_fim_default_obj = (datetime.datetime.combine(datetime.date.today(), hora_inicio_obj) + datetime.timedelta(hours=1)).time()
                hora_fim_obj = parse_time(str(data.get("hora_fim", "")).strip() or hora_fim_default_obj.strftime("%H:%M"))
                if hora_fim_obj <= hora_inicio_obj:
                    hora_fim_obj = (datetime.datetime.combine(datetime.date.today(), hora_inicio_obj) + datetime.timedelta(hours=1)).time()
                hora_fim = hora_fim_obj.strftime("%H:%M")
                turma_obj = {
                    "nome": nome,
                    "professor": str(data.get("professor", "Sem Professor")).strip() or "Sem Professor",
                    "modulo": str(data.get("modulo", "Presencial em Turma")).strip() or "Presencial em Turma",
                    "dias": format_class_schedule(dias_semana, hora_inicio, hora_fim),
                    "dias_semana": dias_semana,
                    "hora_inicio": hora_inicio,
                    "hora_fim": hora_fim,
                    "link_zoom": str(data.get("link_zoom", data.get("link", ""))).strip(),
                    "livro": str(data.get("livro", "")).strip(),
                }
                st.session_state["classes"].append(turma_obj)
                save_list(CLASSES_FILE, st.session_state["classes"])
                reports.append({"type": kind, "ok": True, "message": f"turma {nome} cadastrada"})
            elif kind == "atualizar_turma":
                idx_list = _find_class_indices(data)
                if not idx_list:
                    reports.append({"type": kind, "ok": False, "message": "turma nao encontrada"})
                    continue
                if not _wiz_to_bool(data.get("aplicar_em_lote", False), default=False):
                    idx_list = idx_list[:1]
                touched = 0
                for idx in idx_list:
                    if idx < 0 or idx >= len(st.session_state.get("classes", [])):
                        continue
                    turma_obj = st.session_state["classes"][idx]
                    old_nome = str(turma_obj.get("nome", "")).strip()
                    novo_nome = str(data.get("novo_nome", data.get("nome", data.get("turma", "")))).strip()
                    if novo_nome:
                        turma_obj["nome"] = novo_nome
                    if str(data.get("professor", "")).strip():
                        turma_obj["professor"] = str(data.get("professor", "")).strip()
                    if str(data.get("modulo", "")).strip():
                        turma_obj["modulo"] = str(data.get("modulo", "")).strip()
                    if str(data.get("livro", "")).strip():
                        turma_obj["livro"] = str(data.get("livro", "")).strip()
                    if str(data.get("link_zoom", data.get("link", ""))).strip():
                        turma_obj["link_zoom"] = str(data.get("link_zoom", data.get("link", ""))).strip()

                    dias_raw = data.get("dias_semana", data.get("dias", None))
                    dias_semana = None
                    if isinstance(dias_raw, str) and str(dias_raw).strip():
                        dias_semana = infer_class_days_from_text(dias_raw)
                    elif isinstance(dias_raw, list):
                        dias_semana = [str(d).strip() for d in dias_raw if str(d).strip() in WEEKDAY_OPTIONS_PT]

                    hora_inicio = str(turma_obj.get("hora_inicio", "19:00")).strip() or "19:00"
                    hora_fim = str(turma_obj.get("hora_fim", "20:00")).strip() or "20:00"
                    if str(data.get("hora_inicio", "")).strip():
                        hora_inicio = parse_time(str(data.get("hora_inicio", "")).strip()).strftime("%H:%M")
                    if str(data.get("hora_fim", "")).strip():
                        hora_fim = parse_time(str(data.get("hora_fim", "")).strip()).strftime("%H:%M")
                    hora_inicio_obj = parse_time(hora_inicio)
                    hora_fim_obj = parse_time(hora_fim)
                    if hora_fim_obj <= hora_inicio_obj:
                        hora_fim_obj = (datetime.datetime.combine(datetime.date.today(), hora_inicio_obj) + datetime.timedelta(hours=1)).time()
                    hora_fim = hora_fim_obj.strftime("%H:%M")

                    if dias_semana:
                        turma_obj["dias_semana"] = dias_semana
                    dias_eff = turma_obj.get("dias_semana", dias_semana or [])
                    turma_obj["hora_inicio"] = hora_inicio
                    turma_obj["hora_fim"] = hora_fim
                    turma_obj["dias"] = format_class_schedule(dias_eff, hora_inicio, hora_fim)

                    if old_nome and novo_nome and old_nome != novo_nome:
                        for aluno in st.session_state.get("students", []):
                            if str(aluno.get("turma", "")).strip() == old_nome:
                                aluno["turma"] = novo_nome
                        save_list(STUDENTS_FILE, st.session_state["students"])
                    touched += 1
                save_list(CLASSES_FILE, st.session_state["classes"])
                reports.append({"type": kind, "ok": True, "message": f"turma atualizada em {touched} registro(s)"})
            elif kind == "excluir_turma":
                idx_list = _find_class_indices(data)
                if not idx_list:
                    reports.append({"type": kind, "ok": False, "message": "turma nao encontrada para exclusao"})
                    continue
                turmas_nomes = []
                for idx in sorted(set(idx_list), reverse=True):
                    if 0 <= idx < len(st.session_state.get("classes", [])):
                        turmas_nomes.append(str(st.session_state["classes"][idx].get("nome", "")).strip())
                        st.session_state["classes"].pop(idx)
                save_list(CLASSES_FILE, st.session_state["classes"])
                turma_set = {str(t).strip() for t in turmas_nomes if str(t).strip()}
                for aluno in st.session_state.get("students", []):
                    if str(aluno.get("turma", "")).strip() in turma_set:
                        aluno["turma"] = "Sem Turma"
                save_list(STUDENTS_FILE, st.session_state["students"])
                reports.append({"type": kind, "ok": True, "message": f"{len(set(idx_list))} turma(s) excluida(s)"})
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
            elif kind == "atualizar_aula":
                idx_list = _find_agenda_indices(data)
                if not idx_list:
                    reports.append({"type": kind, "ok": False, "message": "aula nao encontrada na agenda"})
                    continue
                if not _wiz_to_bool(data.get("aplicar_em_lote", False), default=False):
                    idx_list = idx_list[:1]
                touched = 0
                for idx in idx_list:
                    if idx < 0 or idx >= len(st.session_state.get("agenda", [])):
                        continue
                    obj = st.session_state["agenda"][idx]
                    for src, dst in [
                        ("turma", "turma"),
                        ("professor", "professor"),
                        ("titulo", "titulo"),
                        ("descricao", "descricao"),
                        ("data", "data"),
                        ("hora", "hora"),
                        ("link", "link"),
                    ]:
                        if str(data.get(src, "")).strip():
                            obj[dst] = str(data.get(src, "")).strip()
                    obj["google_calendar_link"] = build_google_calendar_event_link(obj)
                    touched += 1
                save_list(AGENDA_FILE, st.session_state["agenda"])
                reports.append({"type": kind, "ok": True, "message": f"aula atualizada em {touched} registro(s)"})
            elif kind == "excluir_aula":
                idx_list = _find_agenda_indices(data)
                if not idx_list:
                    reports.append({"type": kind, "ok": False, "message": "aula nao encontrada para exclusao"})
                    continue
                for idx in sorted(set(idx_list), reverse=True):
                    if 0 <= idx < len(st.session_state.get("agenda", [])):
                        st.session_state["agenda"].pop(idx)
                save_list(AGENDA_FILE, st.session_state["agenda"])
                reports.append({"type": kind, "ok": True, "message": f"{len(set(idx_list))} aula(s) removida(s) da agenda"})
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
                somente_turmas_existentes = _wiz_to_bool(
                    data.get(
                        "somente_turmas_existentes",
                        data.get(
                            "apenas_turmas_existentes",
                            data.get(
                                "somente_com_turma",
                                data.get("apenas_com_turma", True),
                            ),
                        ),
                    ),
                    default=True,
                )
                post_message_and_notify(
                    autor=st.session_state.get("user_name", "Assistente Wiz"),
                    titulo=titulo,
                    mensagem=mensagem,
                    turma=turma,
                    origem="Assistente Wiz",
                    student_only_existing_classes=bool(somente_turmas_existentes),
                    include_students_without_turma_when_all=False,
                )
                reports.append({"type": kind, "ok": True, "message": "noticia publicada"})
            elif kind == "enviar_comunicado":
                titulo = str(data.get("titulo", data.get("assunto", "Comunicado"))).strip() or "Comunicado"
                mensagem = str(data.get("mensagem", data.get("texto", ""))).strip()
                turma = str(data.get("turma", "Todas")).strip() or "Todas"
                if not mensagem:
                    reports.append({"type": kind, "ok": False, "message": "mensagem e obrigatoria"})
                    continue
                somente_turmas_existentes = _wiz_to_bool(
                    data.get(
                        "somente_turmas_existentes",
                        data.get(
                            "apenas_turmas_existentes",
                            data.get(
                                "somente_com_turma",
                                data.get("apenas_com_turma", True),
                            ),
                        ),
                    ),
                    default=True,
                )
                incluir_sem_turma = _wiz_to_bool(
                    data.get("incluir_sem_turma", data.get("incluir_alunos_sem_turma", False)),
                    default=False,
                )
                turmas_existentes = {str(c.get("nome", "")).strip() for c in st.session_state.get("classes", []) if str(c.get("nome", "")).strip()}
                if turma != "Todas" and somente_turmas_existentes and turma not in turmas_existentes:
                    reports.append(
                        {
                            "type": kind,
                            "ok": False,
                            "message": f"turma '{turma}' nao existe no cadastro de turmas",
                        }
                    )
                    continue
                stats = post_message_and_notify(
                    autor=st.session_state.get("user_name", "Assistente Wiz"),
                    titulo=titulo,
                    mensagem=mensagem,
                    turma=turma,
                    origem="Assistente Wiz",
                    student_only_existing_classes=bool(somente_turmas_existentes),
                    include_students_without_turma_when_all=bool(incluir_sem_turma),
                )
                filtro_label = "somente alunos com turma existente"
                if not bool(somente_turmas_existentes):
                    filtro_label = "todos os alunos do filtro informado"
                    if turma == "Todas" and bool(incluir_sem_turma):
                        filtro_label = "todos os alunos, incluindo sem turma"
                reports.append(
                    {
                        "type": kind,
                        "ok": True,
                        "message": (
                            f"comunicado enviado para {turma} "
                            f"[filtro: {filtro_label}; alunos considerados {int(stats.get('student_total', 0))}; "
                            f"alunos com contato {int(stats.get('student_with_channel', 0))}] "
                            f"(e-mail {int(stats.get('email_ok', 0))}/{int(stats.get('email_total', 0))}, "
                            f"whatsapp {int(stats.get('whatsapp_ok', 0))}/{int(stats.get('whatsapp_total', 0))})"
                        ),
                    }
                )
            elif kind in ("cadastrar_livro", "atualizar_livro"):
                books = ensure_library_catalog(st.session_state.get("books", []))
                st.session_state["books"] = books
                idx_list = _find_book_indices(data)
                book_id = str(data.get("book_id", "")).strip()
                titulo_in = str(data.get("titulo", "")).strip()
                if not idx_list and book_id:
                    idx_list = _find_book_indices({"book_id": book_id})
                if not idx_list and titulo_in:
                    idx_list = _find_book_indices({"titulo": titulo_in})

                if kind == "atualizar_livro" and not idx_list:
                    reports.append({"type": kind, "ok": False, "message": "livro nao encontrado para atualizacao"})
                    continue

                if idx_list:
                    idx = idx_list[0]
                    obj = books[idx]
                else:
                    inferred_id = book_id or infer_library_book_id(data) or _wiz_guess_book_id_from_filename(str(data.get("file_name", "")).strip())
                    defaults = _wiz_book_defaults_from_id(inferred_id)
                    obj = {
                        "book_id": inferred_id,
                        "nivel": defaults.get("nivel", ""),
                        "titulo": defaults.get("titulo") or "Livro",
                        "categoria": defaults.get("categoria", ""),
                        "parte": defaults.get("parte", ""),
                        "url": "",
                        "file_path": "",
                        "file_b64": "",
                        "file_name": "",
                    }
                    books.append(obj)

                if str(data.get("book_id", "")).strip():
                    obj["book_id"] = str(data.get("book_id", "")).strip()
                if titulo_in:
                    obj["titulo"] = titulo_in
                if str(data.get("categoria", "")).strip():
                    obj["categoria"] = str(data.get("categoria", "")).strip()
                if str(data.get("nivel", "")).strip():
                    obj["nivel"] = str(data.get("nivel", "")).strip()
                if str(data.get("parte", "")).strip():
                    obj["parte"] = str(data.get("parte", "")).strip()
                if str(data.get("url", data.get("link", ""))).strip():
                    obj["url"] = str(data.get("url", data.get("link", ""))).strip()

                file_bytes = data.get("file_bytes")
                file_b64 = str(data.get("file_b64", "")).strip()
                if isinstance(file_bytes, (bytes, bytearray)) and file_bytes:
                    obj["file_b64"] = base64.b64encode(bytes(file_bytes)).decode("ascii")
                    obj["file_name"] = str(data.get("file_name", obj.get("file_name", ""))).strip() or "livro.pdf"
                    obj["file_path"] = ""
                elif file_b64:
                    try:
                        decoded = base64.b64decode(file_b64.encode("ascii"), validate=False)
                        if decoded:
                            obj["file_b64"] = base64.b64encode(decoded).decode("ascii")
                            obj["file_name"] = str(data.get("file_name", obj.get("file_name", ""))).strip() or obj.get("file_name", "livro.pdf")
                            obj["file_path"] = ""
                    except Exception:
                        pass

                st.session_state["books"] = ensure_library_catalog(books)
                save_list(BOOKS_FILE, st.session_state["books"])
                reports.append({"type": kind, "ok": True, "message": f"livro salvo: {obj.get('titulo', 'Livro')}"})
            elif kind == "excluir_livro":
                books = ensure_library_catalog(st.session_state.get("books", []))
                st.session_state["books"] = books
                idx_list = _find_book_indices(data)
                if not idx_list:
                    reports.append({"type": kind, "ok": False, "message": "livro nao encontrado para exclusao"})
                    continue

                template_ids = {str(t.get("book_id", "")).strip() for t in library_book_templates()}
                removed = 0
                for idx in sorted(set(idx_list), reverse=True):
                    if idx < 0 or idx >= len(books):
                        continue
                    obj = books[idx]
                    bid = str(obj.get("book_id", "")).strip()
                    if bid and bid in template_ids:
                        obj["url"] = ""
                        obj["file_path"] = ""
                        obj["file_b64"] = ""
                        obj["file_name"] = ""
                    else:
                        books.pop(idx)
                    removed += 1
                st.session_state["books"] = ensure_library_catalog(books)
                save_list(BOOKS_FILE, st.session_state["books"])
                reports.append({"type": kind, "ok": True, "message": f"{removed} livro(s) processado(s) para exclusao"})
            elif kind == "lancar_recebivel":
                aluno = str(data.get("aluno", data.get("referencia", ""))).strip()
                descricao = str(data.get("descricao", "Mensalidade")).strip()
                categoria = str(data.get("categoria", "Mensalidade")).strip() or "Mensalidade"
                categoria_lancamento = str(data.get("categoria_lancamento", data.get("tipo_categoria", "Aluno"))).strip() or "Aluno"
                cobranca = str(data.get("cobranca", "Boleto")).strip() or "Boleto"
                qtd = max(1, min(24, parse_int(data.get("qtd_parcelas", data.get("parcelas", 1))) or 1))
                parcela_inicial = max(1, parse_int(data.get("parcela_inicial", 1)) or 1)
                valor_parcela_num = parse_money(str(data.get("valor_parcela", data.get("valor", ""))))
                valor_total_num = parse_money(str(data.get("valor_total", data.get("valor", ""))))
                if valor_parcela_num <= 0 and valor_total_num > 0:
                    valor_parcela_num = valor_total_num / qtd
                if valor_total_num <= 0 and valor_parcela_num > 0:
                    valor_total_num = valor_parcela_num * qtd
                if not aluno or valor_parcela_num <= 0:
                    reports.append({"type": kind, "ok": False, "message": "aluno/referencia e valor valido sao obrigatorios"})
                    continue
                data_lanc = parse_date(str(data.get("data_lancamento", ""))) or datetime.date.today()
                venc0 = parse_date(str(data.get("vencimento", ""))) or datetime.date.today()
                valor_parcela_txt = f"{valor_parcela_num:.2f}".replace(".", ",")
                valor_total_txt = f"{valor_total_num:.2f}".replace(".", ",")
                lote_id = str(data.get("lote_id", "")).strip() or f"REC-LOT-{uuid.uuid4().hex[:10].upper()}"
                count = 0
                for i in range(qtd):
                    venc_item = add_months(venc0, i) if qtd > 1 else venc0
                    parcela_txt = f"{parcela_inicial + i}/{qtd}" if qtd > 1 else str(parcela_inicial)
                    add_receivable(
                        aluno=aluno,
                        descricao=descricao,
                        valor=valor_total_txt,
                        vencimento=venc_item,
                        cobranca=cobranca,
                        categoria=categoria,
                        data_lancamento=data_lanc,
                        valor_parcela=valor_parcela_txt,
                        parcela=parcela_txt,
                        numero_pedido=str(data.get("numero_pedido", "")),
                        item_codigo=str(data.get("item_codigo", "")),
                        categoria_lancamento=categoria_lancamento,
                        lote_id=lote_id,
                    )
                    count += 1
                reports.append({"type": kind, "ok": True, "message": f"recebivel lancado ({count} parcela(s))"})
            elif kind == "atualizar_recebivel":
                idx_list = _find_receivable_indices(data)
                if not idx_list:
                    reports.append({"type": kind, "ok": False, "message": "recebivel nao encontrado"})
                    continue
                apply_lote = _wiz_to_bool(data.get("aplicar_em_lote", True), default=True)
                if not apply_lote:
                    idx_list = idx_list[:1]
                itens = st.session_state.get("receivables", [])
                qtd_ref = max(1, len(idx_list))
                val_total_in = str(data.get("valor_total", data.get("valor", ""))).strip()
                val_parc_in = str(data.get("valor_parcela", "")).strip()
                val_total_num = parse_money(val_total_in) if val_total_in else 0
                val_parc_num = parse_money(val_parc_in) if val_parc_in else 0
                if val_parc_num <= 0 and val_total_num > 0:
                    val_parc_num = val_total_num / qtd_ref
                if val_total_num <= 0 and val_parc_num > 0:
                    val_total_num = val_parc_num * qtd_ref
                val_total_txt = f"{val_total_num:.2f}".replace(".", ",") if val_total_num > 0 else ""
                val_parc_txt = f"{val_parc_num:.2f}".replace(".", ",") if val_parc_num > 0 else ""
                novo_venc = parse_date(str(data.get("vencimento", "")))
                idx_list = sorted(
                    idx_list,
                    key=lambda i: (
                        parse_int(str(itens[i].get("parcela", "1")).split("/")[0]) or 1,
                        i,
                    ),
                )
                for pos, idx in enumerate(idx_list, start=1):
                    obj = itens[idx]
                    if str(data.get("descricao", "")).strip():
                        obj["descricao"] = str(data.get("descricao", "")).strip()
                    if str(data.get("aluno", data.get("referencia", ""))).strip():
                        obj["aluno"] = str(data.get("aluno", data.get("referencia", ""))).strip()
                    if str(data.get("categoria", "")).strip():
                        obj["categoria"] = str(data.get("categoria", "")).strip()
                    if str(data.get("categoria_lancamento", "")).strip():
                        obj["categoria_lancamento"] = str(data.get("categoria_lancamento", "")).strip()
                    if str(data.get("cobranca", "")).strip():
                        obj["cobranca"] = str(data.get("cobranca", "")).strip()
                    if str(data.get("status", "")).strip():
                        obj["status"] = str(data.get("status", "")).strip()
                    if str(data.get("numero_pedido", "")).strip():
                        obj["numero_pedido"] = str(data.get("numero_pedido", "")).strip()
                    if str(data.get("item_codigo", "")).strip():
                        obj["item_codigo"] = str(data.get("item_codigo", "")).strip()
                    if val_total_txt:
                        obj["valor"] = val_total_txt
                    if val_parc_txt:
                        obj["valor_parcela"] = val_parc_txt
                    if apply_lote:
                        obj["parcela"] = f"{pos}/{len(idx_list)}" if len(idx_list) > 1 else "1"
                        if novo_venc:
                            obj["vencimento"] = add_months(novo_venc, pos - 1).strftime("%d/%m/%Y")
                    elif novo_venc:
                        obj["vencimento"] = novo_venc.strftime("%d/%m/%Y")
                save_list(RECEIVABLES_FILE, st.session_state["receivables"])
                reports.append({"type": kind, "ok": True, "message": f"recebivel atualizado em {len(idx_list)} registro(s)"})
            elif kind == "excluir_recebivel":
                idx_list = _find_receivable_indices(data)
                if not idx_list:
                    reports.append({"type": kind, "ok": False, "message": "nenhum recebivel encontrado para exclusao"})
                    continue
                for idx in sorted(set(idx_list), reverse=True):
                    if 0 <= idx < len(st.session_state.get("receivables", [])):
                        st.session_state["receivables"].pop(idx)
                save_list(RECEIVABLES_FILE, st.session_state["receivables"])
                reports.append({"type": kind, "ok": True, "message": f"{len(set(idx_list))} recebivel(is) excluido(s)"})
            elif kind == "baixar_recebivel":
                idx_list = _find_receivable_indices(data)
                if not idx_list:
                    aluno_ref = str(data.get("aluno", "")).strip()
                    if aluno_ref:
                        somente_vencidos = _wiz_to_bool(data.get("somente_vencidos", True), default=True)
                        ate = parse_date(str(data.get("ate_data", ""))) or datetime.date.today()
                        idx_list = []
                        for idx, obj in enumerate(st.session_state.get("receivables", [])):
                            if str(obj.get("aluno", "")).strip() != aluno_ref:
                                continue
                            if str(obj.get("status", "")).strip().lower() == "pago":
                                continue
                            if somente_vencidos:
                                venc_obj = parse_date(str(obj.get("vencimento", "")))
                                if venc_obj and venc_obj > ate:
                                    continue
                            idx_list.append(idx)
                if not idx_list:
                    reports.append({"type": kind, "ok": False, "message": "nenhum recebivel encontrado para baixa"})
                    continue
                hoje_txt = datetime.date.today().strftime("%d/%m/%Y")
                count = 0
                for idx in sorted(set(idx_list)):
                    if 0 <= idx < len(st.session_state.get("receivables", [])):
                        obj = st.session_state["receivables"][idx]
                        if str(obj.get("status", "")).strip().lower() != "pago":
                            obj["status"] = "Pago"
                            obj["baixa_data"] = hoje_txt
                            obj["baixa_tipo"] = "Assistente Wiz"
                            count += 1
                save_list(RECEIVABLES_FILE, st.session_state["receivables"])
                reports.append({"type": kind, "ok": True, "message": f"baixa aplicada em {count} recebivel(is)"})
            elif kind == "lancar_despesa":
                descricao = str(data.get("descricao", "")).strip()
                fornecedor = str(data.get("fornecedor", data.get("referencia", ""))).strip()
                if not descricao or not fornecedor:
                    reports.append({"type": kind, "ok": False, "message": "descricao e fornecedor/referencia sao obrigatorios"})
                    continue
                qtd = max(1, min(24, parse_int(data.get("qtd_parcelas", data.get("parcelas", 1))) or 1))
                val_parc_num = parse_money(str(data.get("valor_parcela", data.get("valor", ""))))
                val_total_num = parse_money(str(data.get("valor_total", data.get("valor", ""))))
                if val_parc_num <= 0 and val_total_num > 0:
                    val_parc_num = val_total_num / qtd
                if val_total_num <= 0 and val_parc_num > 0:
                    val_total_num = val_parc_num * qtd
                if val_parc_num <= 0:
                    reports.append({"type": kind, "ok": False, "message": "valor invalido para despesa"})
                    continue
                val_parc_txt = f"{val_parc_num:.2f}".replace(".", ",")
                val_total_txt = f"{val_total_num:.2f}".replace(".", ",")
                data_lanc = parse_date(str(data.get("data", data.get("data_lancamento", "")))) or datetime.date.today()
                venc0 = parse_date(str(data.get("vencimento", ""))) or datetime.date.today()
                lote_id = str(data.get("lote_id", "")).strip() or f"PAG-LOT-{uuid.uuid4().hex[:10].upper()}"
                for i in range(qtd):
                    venc_item = add_months(venc0, i) if qtd > 1 else venc0
                    parcela_txt = f"{1 + i}/{qtd}" if qtd > 1 else "1"
                    st.session_state["payables"].append(
                        {
                            "codigo": f"PAG-{uuid.uuid4().hex[:8].upper()}",
                            "descricao": descricao,
                            "valor": val_total_txt,
                            "valor_parcela": val_parc_txt,
                            "parcela": parcela_txt,
                            "fornecedor": fornecedor,
                            "categoria_lancamento": str(data.get("categoria_lancamento", "Fornecedor")).strip() or "Fornecedor",
                            "numero_pedido": str(data.get("numero_pedido", "")).strip(),
                            "data": data_lanc.strftime("%d/%m/%Y"),
                            "vencimento": venc_item.strftime("%d/%m/%Y"),
                            "cobranca": str(data.get("cobranca", "Boleto")).strip() or "Boleto",
                            "status": str(data.get("status", "Aberto")).strip() or "Aberto",
                            "lote_id": lote_id,
                        }
                    )
                save_list(PAYABLES_FILE, st.session_state["payables"])
                reports.append({"type": kind, "ok": True, "message": f"despesa lancada ({qtd} parcela(s))"})
            elif kind == "atualizar_despesa":
                idx_list = _find_payable_indices(data)
                if not idx_list:
                    reports.append({"type": kind, "ok": False, "message": "despesa nao encontrada"})
                    continue
                apply_lote = _wiz_to_bool(data.get("aplicar_em_lote", True), default=True)
                if not apply_lote:
                    idx_list = idx_list[:1]
                itens = st.session_state.get("payables", [])
                qtd_ref = max(1, len(idx_list))
                val_total_in = str(data.get("valor_total", data.get("valor", ""))).strip()
                val_parc_in = str(data.get("valor_parcela", "")).strip()
                val_total_num = parse_money(val_total_in) if val_total_in else 0
                val_parc_num = parse_money(val_parc_in) if val_parc_in else 0
                if val_parc_num <= 0 and val_total_num > 0:
                    val_parc_num = val_total_num / qtd_ref
                if val_total_num <= 0 and val_parc_num > 0:
                    val_total_num = val_parc_num * qtd_ref
                val_total_txt = f"{val_total_num:.2f}".replace(".", ",") if val_total_num > 0 else ""
                val_parc_txt = f"{val_parc_num:.2f}".replace(".", ",") if val_parc_num > 0 else ""
                novo_venc = parse_date(str(data.get("vencimento", "")))
                idx_list = sorted(
                    idx_list,
                    key=lambda i: (
                        parse_int(str(itens[i].get("parcela", "1")).split("/")[0]) or 1,
                        i,
                    ),
                )
                for pos, idx in enumerate(idx_list, start=1):
                    obj = itens[idx]
                    if str(data.get("descricao", "")).strip():
                        obj["descricao"] = str(data.get("descricao", "")).strip()
                    if str(data.get("fornecedor", data.get("referencia", ""))).strip():
                        obj["fornecedor"] = str(data.get("fornecedor", data.get("referencia", ""))).strip()
                    if str(data.get("categoria_lancamento", "")).strip():
                        obj["categoria_lancamento"] = str(data.get("categoria_lancamento", "")).strip()
                    if str(data.get("numero_pedido", "")).strip():
                        obj["numero_pedido"] = str(data.get("numero_pedido", "")).strip()
                    if str(data.get("cobranca", "")).strip():
                        obj["cobranca"] = str(data.get("cobranca", "")).strip()
                    if str(data.get("status", "")).strip():
                        obj["status"] = str(data.get("status", "")).strip()
                    if str(data.get("data", data.get("data_lancamento", ""))).strip():
                        data_upd = parse_date(str(data.get("data", data.get("data_lancamento", ""))))
                        if data_upd:
                            obj["data"] = data_upd.strftime("%d/%m/%Y")
                    if val_total_txt:
                        obj["valor"] = val_total_txt
                    if val_parc_txt:
                        obj["valor_parcela"] = val_parc_txt
                    if apply_lote:
                        obj["parcela"] = f"{pos}/{len(idx_list)}" if len(idx_list) > 1 else "1"
                        if novo_venc:
                            obj["vencimento"] = add_months(novo_venc, pos - 1).strftime("%d/%m/%Y")
                    elif novo_venc:
                        obj["vencimento"] = novo_venc.strftime("%d/%m/%Y")
                save_list(PAYABLES_FILE, st.session_state["payables"])
                reports.append({"type": kind, "ok": True, "message": f"despesa atualizada em {len(idx_list)} registro(s)"})
            elif kind == "excluir_despesa":
                idx_list = _find_payable_indices(data)
                if not idx_list:
                    reports.append({"type": kind, "ok": False, "message": "nenhuma despesa encontrada para exclusao"})
                    continue
                for idx in sorted(set(idx_list), reverse=True):
                    if 0 <= idx < len(st.session_state.get("payables", [])):
                        st.session_state["payables"].pop(idx)
                save_list(PAYABLES_FILE, st.session_state["payables"])
                reports.append({"type": kind, "ok": True, "message": f"{len(set(idx_list))} despesa(s) excluida(s)"})
            elif kind == "baixar_despesa":
                idx_list = _find_payable_indices(data)
                if not idx_list:
                    fornecedor_ref = str(data.get("fornecedor", "")).strip()
                    if fornecedor_ref:
                        idx_list = [
                            idx for idx, obj in enumerate(st.session_state.get("payables", []))
                            if str(obj.get("fornecedor", "")).strip() == fornecedor_ref
                            and str(obj.get("status", "")).strip().lower() != "pago"
                        ]
                if not idx_list:
                    reports.append({"type": kind, "ok": False, "message": "nenhuma despesa encontrada para baixa"})
                    continue
                hoje_txt = datetime.date.today().strftime("%d/%m/%Y")
                count = 0
                for idx in sorted(set(idx_list)):
                    if 0 <= idx < len(st.session_state.get("payables", [])):
                        obj = st.session_state["payables"][idx]
                        if str(obj.get("status", "")).strip().lower() != "pago":
                            obj["status"] = "Pago"
                            obj["baixa_data"] = hoje_txt
                            obj["baixa_tipo"] = "Assistente Wiz"
                            count += 1
                save_list(PAYABLES_FILE, st.session_state["payables"])
                reports.append({"type": kind, "ok": True, "message": f"baixa aplicada em {count} despesa(s)"})
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
    _wiz_log_action_batch(actions, reports)
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
                    pdf_reader_cls = None
                    for pdf_module_name in ("pypdf", "PyPDF2"):
                        try:
                            pdf_module = importlib.import_module(pdf_module_name)
                            pdf_reader_cls = getattr(pdf_module, "PdfReader", None)
                            if pdf_reader_cls:
                                break
                        except Exception:
                            continue
                    if pdf_reader_cls:
                        reader = pdf_reader_cls(io.BytesIO(raw))
                        parts = []
                        for page in reader.pages[:3]:
                            parts.append((page.extract_text() or "").strip())
                        text = "\n".join([p for p in parts if p])
                    else:
                        text = ""
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

def _render_wiz_action_history_panel():
    with st.expander("Historico de execucoes do Wiz", expanded=False):
        logs = load_list(WIZ_ACTION_AUDIT_FILE)
        logs = logs if isinstance(logs, list) else []
        if not logs:
            st.info("Sem historico de execucao ate o momento.")
            return

        rows = []
        for item in reversed(logs[-2000:]):
            if not isinstance(item, dict):
                continue
            payload = item.get("data", {})
            payload_txt = ""
            if isinstance(payload, (dict, list)):
                try:
                    payload_txt = json.dumps(payload, ensure_ascii=False)
                except Exception:
                    payload_txt = str(payload)
            else:
                payload_txt = str(payload or "")
            if len(payload_txt) > 400:
                payload_txt = payload_txt[:400] + "..."
            rows.append(
                {
                    "Data/Hora": str(item.get("timestamp", "")).strip(),
                    "Usuario": str(item.get("usuario", "")).strip(),
                    "Role": str(item.get("role", "")).strip(),
                    "Perfil Conta": str(item.get("perfil_conta", "")).strip(),
                    "Acao": str(item.get("action", "")).strip(),
                    "Status": "OK" if bool(item.get("ok", False)) else "Falha",
                    "Mensagem": str(item.get("message", "")).strip(),
                    "Dados": payload_txt,
                }
            )
        if not rows:
            st.info("Sem registros validos no historico.")
            return

        df_hist = pd.DataFrame(rows)
        f1, f2, f3 = st.columns([1.2, 1.2, 2.0])
        with f1:
            status_sel = st.selectbox(
                "Status",
                ["Todos", "OK", "Falha"],
                key="wiz_hist_status",
            )
        with f2:
            action_options = ["Todas"] + sorted([a for a in df_hist["Acao"].dropna().unique().tolist() if str(a).strip()])
            action_sel = st.selectbox(
                "Acao",
                action_options,
                key="wiz_hist_action",
            )
        with f3:
            only_me = st.checkbox(
                "Mostrar apenas minhas acoes",
                value=True,
                key="wiz_hist_only_me",
            )

        df_view = df_hist.copy()
        if status_sel != "Todos":
            df_view = df_view[df_view["Status"] == status_sel]
        if action_sel != "Todas":
            df_view = df_view[df_view["Acao"] == action_sel]
        if only_me:
            current_user = str(st.session_state.get("user_name", "")).strip()
            if current_user:
                df_view = df_view[df_view["Usuario"] == current_user]

        st.caption(f"Registros exibidos: {len(df_view)}")
        st.dataframe(df_view, use_container_width=True, hide_index=True)

        csv_data = df_view.to_csv(index=False).encode("utf-8")
        d1, d2 = st.columns([1.2, 2.0])
        with d1:
            st.download_button(
                "Exportar historico (CSV)",
                data=csv_data,
                file_name="wiz_historico_execucao.csv",
                mime="text/csv",
                key="wiz_hist_export_csv",
            )
        with d2:
            confirm_clear = st.checkbox(
                "Confirmo apagar o historico de execucao",
                value=False,
                key="wiz_hist_confirm_clear",
            )
            if st.button("Apagar historico", key="wiz_hist_clear_btn"):
                if not confirm_clear:
                    st.warning("Marque a confirmacao para apagar o historico.")
                else:
                    save_list(WIZ_ACTION_AUDIT_FILE, [])
                    st.success("Historico do Wiz apagado.")
                    st.rerun()

def _render_wiz_automation_panel():
    settings = get_wiz_settings()
    smtp_diag = _smtp_config_diagnostics()
    wa_diag = _whatsapp_config_diagnostics()

    with st.expander("Configurar automacoes e notificacoes do Assistente Wiz", expanded=True):
        c1, c2, c3 = st.columns(3)
        with c1:
            wiz_enabled_flag = st.checkbox(
                "Assistente habilitado",
                value=bool(settings.get("enabled", True)),
                key="wiz_cfg_enabled",
            )
        with c2:
            notify_email_flag = st.checkbox(
                "Enviar e-mail",
                value=bool(settings.get("notify_email", True)),
                key="wiz_cfg_notify_email",
            )
        with c3:
            notify_whatsapp_flag = st.checkbox(
                "Enviar WhatsApp",
                value=bool(settings.get("notify_whatsapp", True)),
                key="wiz_cfg_notify_whatsapp",
            )

        e1, e2, e3 = st.columns(3)
        with e1:
            on_student_created = st.checkbox(
                "Cadastro de alunos",
                value=bool(settings.get("on_student_created", True)),
                key="wiz_cfg_on_student_created",
            )
            on_teacher_created = st.checkbox(
                "Cadastro de professores",
                value=bool(settings.get("on_teacher_created", True)),
                key="wiz_cfg_on_teacher_created",
            )
            on_user_created = st.checkbox(
                "Cadastro de usuarios",
                value=bool(settings.get("on_user_created", True)),
                key="wiz_cfg_on_user_created",
            )
        with e2:
            on_news_posted = st.checkbox(
                "Publicacao de notificacoes",
                value=bool(settings.get("on_news_posted", True)),
                key="wiz_cfg_on_news_posted",
            )
            on_grade_approved = st.checkbox(
                "Aprovacao de notas",
                value=bool(settings.get("on_grade_approved", True)),
                key="wiz_cfg_on_grade_approved",
            )
            on_agenda_created = st.checkbox(
                "Agendamento de aula",
                value=bool(settings.get("on_agenda_created", True)),
                key="wiz_cfg_on_agenda_created",
            )
        with e3:
            on_class_link_updated = st.checkbox(
                "Alteracao de link de turma",
                value=bool(settings.get("on_class_link_updated", True)),
                key="wiz_cfg_on_class_link_updated",
            )
            on_financial_created = st.checkbox(
                "Lancamento financeiro",
                value=bool(settings.get("on_financial_created", True)),
                key="wiz_cfg_on_financial_created",
            )
            auto_daily_backup = st.checkbox(
                "Backup diario automatico",
                value=bool(settings.get("auto_daily_backup", False)),
                key="wiz_cfg_auto_daily_backup",
            )

        merged = {
            "enabled": bool(wiz_enabled_flag),
            "notify_email": bool(notify_email_flag),
            "notify_whatsapp": bool(notify_whatsapp_flag),
            "on_student_created": bool(on_student_created),
            "on_teacher_created": bool(on_teacher_created),
            "on_user_created": bool(on_user_created),
            "on_news_posted": bool(on_news_posted),
            "on_grade_approved": bool(on_grade_approved),
            "on_agenda_created": bool(on_agenda_created),
            "on_class_link_updated": bool(on_class_link_updated),
            "on_financial_created": bool(on_financial_created),
            "auto_daily_backup": bool(auto_daily_backup),
        }

        b1, b2 = st.columns([1.3, 1.0])
        with b1:
            if st.button("Salvar configuracoes do Assistente Wiz", key="wiz_cfg_save"):
                save_wiz_settings(merged)
                st.success("Configuracoes do Assistente Wiz salvas.")
                st.rerun()
        with b2:
            if st.button("Reativar todos os envios", key="wiz_cfg_reactivate_all"):
                force_on = dict(DEFAULT_WIZ_SETTINGS)
                force_on["enabled"] = True
                force_on["notify_email"] = True
                force_on["notify_whatsapp"] = True
                save_wiz_settings(force_on)
                st.success("Envios por e-mail e WhatsApp reativados.")
                st.rerun()

        m1, m2, m3, m4 = st.columns(4)
        with m1:
            st.metric("SMTP", "Configurado" if (smtp_diag.get("host_ok") and smtp_diag.get("from_ok")) else "Pendente")
        with m2:
            st.metric("WhatsApp", "Configurado" if (wa_diag.get("wapi_ready") or wa_diag.get("evolution_ready")) else "Pendente")
        with m3:
            provider_label = str(wa_diag.get("provider", "auto")).strip() or "auto"
            st.metric("Provedor WA", provider_label.upper())
        with m4:
            st.metric("Automacoes", "Ativas" if bool(merged.get("enabled")) else "Desativadas")

        if not merged.get("notify_whatsapp"):
            st.warning("Enviar WhatsApp esta desativado. Ative para voltar a disparar mensagens automaticas.")

def run_wiz_assistant():
    st.markdown('<div class="main-header">ASSISTENTE WIZ</div>', unsafe_allow_html=True)
    st.caption("Conversa simples com o Wiz para Coordenação/Admin. Anexe arquivo/imagem e escreva seu pedido.")

    account_profile = str(st.session_state.get("account_profile") or st.session_state.get("role") or "")
    if account_profile not in ("Admin", "Coordenador"):
        st.error("Acesso restrito para Coordenador/Admin.")
        return

    _render_wiz_automation_panel()

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

    wiz_auto_exec = st.checkbox(
        "Executar tarefas internas automaticamente",
        value=True,
        key="wiz_auto_exec_enabled",
        help="Quando ligado, o Wiz executa no sistema as tarefas que voce pedir (financeiro, agenda, cadastros e comunicados).",
    )
    st.caption("Acoes internas disponiveis apenas para Coordenador/Admin.")

    q1, q2 = st.columns([1.3, 2.0])
    with q1:
        if st.button("Reativar envios agora", key="wiz_quick_reactivate"):
            force_on = dict(DEFAULT_WIZ_SETTINGS)
            force_on["enabled"] = True
            force_on["notify_email"] = True
            force_on["notify_whatsapp"] = True
            save_wiz_settings(force_on)
            st.success("Envios por e-mail e WhatsApp reativados.")
            st.rerun()
    with q2:
        _wa_diag = _whatsapp_config_diagnostics()
        _smtp_diag = _smtp_config_diagnostics()
        wa_ok = bool(_wa_diag.get("wapi_ready") or _wa_diag.get("evolution_ready"))
        smtp_ok = bool(_smtp_diag.get("host_ok") and _smtp_diag.get("from_ok"))
        st.caption(
            f"Status rapido: WhatsApp {'OK' if wa_ok else 'PENDENTE'} | SMTP {'OK' if smtp_ok else 'PENDENTE'}."
        )

    last_exec = st.session_state.get("wiz_last_execution", [])
    if isinstance(last_exec, list) and last_exec:
        with st.expander("Ultima execucao do Wiz no sistema", expanded=False):
            for rep in last_exec[:12]:
                if not isinstance(rep, dict):
                    continue
                icon = "OK" if rep.get("ok") else "Falha"
                st.write(f"- {icon}: {str(rep.get('message', '')).strip()}")

    _render_wiz_action_history_panel()

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

    normalized_user_text = _wiz_norm_text(user_text)
    force_reactivate = any(
        token in normalized_user_text
        for token in (
            "reativar envio",
            "reativar envios",
            "reative envio",
            "reative envios",
            "reativa envio",
            "reativa envios",
            "reativar whatsapp",
            "reative whatsapp",
            "reativa whatsapp",
            "ativar envio",
            "ativar envios",
            "ativar notificacoes",
            "ativar mensagens",
            "ativar whatsapp",
            "ativar e-mail",
            "ativar email",
            "religar whatsapp",
            "ligar whatsapp",
            "whatsapp nao envia",
            "whatsapp nao esta enviando",
            "nao esta enviando whatsapp",
        )
    )
    if force_reactivate:
        force_on = dict(DEFAULT_WIZ_SETTINGS)
        force_on["enabled"] = True
        force_on["notify_email"] = True
        force_on["notify_whatsapp"] = True
        save_wiz_settings(force_on)
        answer = (
            "Pronto. Reativei os envios automáticos do sistema (e-mail e WhatsApp) e mantive "
            "as automações do Assistente Wiz habilitadas."
        )
        chat_history.append({"role": "user", "content": str(user_text).strip()})
        chat_history.append({"role": "assistant", "content": answer})
        st.session_state["active_chat_histories"][chat_key] = chat_history
        st.rerun()

    api_key = get_groq_api_key()

    full_user_text = str(user_text or "").strip()
    if summaries:
        full_user_text += "\n\nAnexos recebidos:\n" + "\n".join(summaries)
    if content_blocks:
        full_user_text += "\n\nConteúdo lido dos anexos:\n" + "\n\n".join(content_blocks)

    chat_history.append({"role": "user", "content": str(user_text).strip()})

    fallback_actions = _wiz_actions_from_book_uploads(user_text, uploaded_files) if wiz_auto_exec else []
    if not api_key and not fallback_actions:
        st.error("Configure GROQ_API_KEY para usar o Assistente Wiz.")
        return

    if api_key:
        with st.spinner("Wiz esta processando seu pedido..."):
            plan = _wiz_plan_actions_with_ai(full_user_text, chat_history[-10:])
    else:
        plan = {"reply": "", "actions": [], "missing": []}

    plan_actions = plan.get("actions", []) if isinstance(plan, dict) else []
    plan_reply = str((plan or {}).get("reply", "")).strip()
    plan_missing = (plan or {}).get("missing", []) if isinstance(plan, dict) else []
    if not plan_actions and fallback_actions:
        plan_actions = fallback_actions
        if not plan_reply:
            plan_reply = "Entendi. Ja executei o cadastro/anexo dos livros enviados na biblioteca."
    answer = ""

    if wiz_auto_exec and plan_actions:
        reports = _wiz_execute_actions(plan_actions)
        st.session_state["wiz_last_execution"] = reports
        answer = _wiz_build_execution_message(plan_reply, reports, plan_missing)
    elif plan_actions and not wiz_auto_exec:
        answer = _wiz_build_execution_message(
            plan_reply or "Identifiquei acoes internas para executar.",
            [],
            plan_missing,
        )
        answer += "\n\nAtive a opcao de execucao automatica para o Wiz realizar essas tarefas no sistema."
    else:
        system_prompt = "\n".join(
            [
                "Você é o Assistente Wiz da Active Educacional para Coordenador/Admin.",
                "Responda em português do Brasil, de forma simples, direta e útil.",
                "Nunca responda com JSON, código ou estrutura técnica.",
                "Quando houver dados faltantes para executar algo interno, peça apenas os dados faltantes.",
                "Se houver anexo, use o conteúdo anexado como base da resposta.",
                "Nunca invente informacoes do sistema (alunos, turmas, valores, status, datas, links ou resultados).",
                "Nao diga que tem certeza sem validacao no contexto atual.",
                "Se nao conseguir confirmar algo no sistema, diga explicitamente que nao foi possivel confirmar agora.",
                "Nunca mencione DietHealth.",
                get_active_context_text(),
            ]
        )
        request_messages = [{"role": "system", "content": system_prompt}]
        request_messages += chat_history[-12:]
        request_messages.append({"role": "user", "content": full_user_text})
        client = OpenAI(api_key=api_key, base_url="https://api.groq.com/openai/v1")
        model_name = os.getenv("ACTIVE_WIZ_MODEL", os.getenv("ACTIVE_CHATBOT_MODEL", "llama-3.3-70b-versatile"))
        with st.spinner("Wiz esta pensando..."):
            try:
                result = client.chat.completions.create(
                    model=model_name,
                    messages=request_messages,
                    temperature=0.2,
                    max_tokens=1200,
                )
                answer = (result.choices[0].message.content or "").strip()
                if not answer:
                    answer = "Nao consegui responder agora. Tente novamente com mais detalhes."
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

ACTIVE_AUTH_QUERY_PARAM = "active_auth"


def _auth_ttl_seconds():
    try:
        days = int(str(os.getenv("ACTIVE_LOGIN_REMEMBER_DAYS", "30")).strip())
    except Exception:
        days = 30
    days = max(1, min(days, 365))
    return days * 24 * 60 * 60


def _auth_secret_key():
    env_secret = str(os.getenv("ACTIVE_AUTH_SECRET", "")).strip()
    if env_secret:
        return env_secret
    return "active-educacional-auth-secret-2026"


def _b64u_encode(raw_bytes):
    return base64.urlsafe_b64encode(raw_bytes).decode("ascii").rstrip("=")


def _b64u_decode(raw_text):
    text = str(raw_text or "").strip()
    if not text:
        return b""
    text += "=" * (-len(text) % 4)
    return base64.urlsafe_b64decode(text.encode("ascii"))


def _get_auth_query_token():
    try:
        value = st.query_params.get(ACTIVE_AUTH_QUERY_PARAM, "")
        if isinstance(value, list):
            value = value[0] if value else ""
        return str(value or "").strip()
    except Exception:
        try:
            params = st.experimental_get_query_params() or {}
            value = params.get(ACTIVE_AUTH_QUERY_PARAM, [""])
            if isinstance(value, list):
                value = value[0] if value else ""
            return str(value or "").strip()
        except Exception:
            return ""


def _set_auth_query_token(token):
    token_txt = str(token or "").strip()
    try:
        if token_txt:
            st.query_params[ACTIVE_AUTH_QUERY_PARAM] = token_txt
        elif ACTIVE_AUTH_QUERY_PARAM in st.query_params:
            del st.query_params[ACTIVE_AUTH_QUERY_PARAM]
        return
    except Exception:
        pass
    try:
        params = st.experimental_get_query_params() or {}
        if token_txt:
            params[ACTIVE_AUTH_QUERY_PARAM] = [token_txt]
        else:
            params.pop(ACTIVE_AUTH_QUERY_PARAM, None)
        st.experimental_set_query_params(**params)
    except Exception:
        pass


def _build_auth_token(username, role, unit, account_profile, display_name):
    username_txt = str(username or "").strip()
    role_txt = str(role or "").strip()
    if not username_txt or not role_txt:
        return ""
    now_ts = int(time.time())
    payload = {
        "u": username_txt,
        "r": role_txt,
        "un": str(unit or "").strip(),
        "p": str(account_profile or "").strip(),
        "n": str(display_name or "").strip(),
        "iat": now_ts,
        "exp": now_ts + _auth_ttl_seconds(),
    }
    payload_raw = json.dumps(payload, ensure_ascii=True, separators=(",", ":"), sort_keys=True).encode("utf-8")
    signature = hmac.new(_auth_secret_key().encode("utf-8"), payload_raw, hashlib.sha256).digest()
    return f"{_b64u_encode(payload_raw)}.{_b64u_encode(signature)}"


def _parse_auth_token(token):
    token_txt = str(token or "").strip()
    if "." not in token_txt:
        return None
    left, right = token_txt.split(".", 1)
    try:
        payload_raw = _b64u_decode(left)
        signature_raw = _b64u_decode(right)
    except Exception:
        return None
    expected = hmac.new(_auth_secret_key().encode("utf-8"), payload_raw, hashlib.sha256).digest()
    if not hmac.compare_digest(expected, signature_raw):
        return None
    try:
        payload = json.loads(payload_raw.decode("utf-8"))
    except Exception:
        return None
    exp_ts = int(payload.get("exp", 0) or 0)
    if exp_ts <= int(time.time()):
        return None
    return payload


def restore_login_from_query():
    if st.session_state.get("logged_in", False):
        return
    token = _get_auth_query_token()
    if not token:
        return
    payload = _parse_auth_token(token)
    if not isinstance(payload, dict):
        _set_auth_query_token("")
        return

    username_txt = str(payload.get("u", "")).strip()
    role_txt = str(payload.get("r", "")).strip()
    unit_txt = str(payload.get("un", "")).strip()
    if not username_txt or not role_txt:
        _set_auth_query_token("")
        return

    users_now = load_users()
    users_now = ensure_admin_user(users_now)
    users_now = sync_users_from_profiles(users_now)
    st.session_state["users"] = users_now
    user_obj = find_user(username_txt)
    if not user_obj:
        _set_auth_query_token("")
        return

    account_profile = str(user_obj.get("perfil", "")).strip()
    allowed = allowed_portals(account_profile)
    if role_txt not in allowed:
        if not allowed:
            _set_auth_query_token("")
            return
        role_txt = allowed[0]

    display_name = str(user_obj.get("pessoa", "")).strip() or str(payload.get("n", "")).strip() or username_txt
    st.session_state["logged_in"] = True
    st.session_state["role"] = role_txt
    st.session_state["user_name"] = display_name
    st.session_state["unit"] = unit_txt or "Matriz"
    st.session_state["account_profile"] = account_profile
    st.session_state["_active_runtime_loaded"] = False

    refreshed_token = _build_auth_token(
        username_txt,
        role_txt,
        st.session_state.get("unit", ""),
        account_profile,
        display_name,
    )
    if refreshed_token:
        _set_auth_query_token(refreshed_token)


def login_user(role, name, unit, account_profile, username_login=""):
    st.session_state["logged_in"] = True
    st.session_state["role"] = role
    st.session_state["user_name"] = name
    st.session_state["unit"] = unit
    st.session_state["account_profile"] = account_profile
    username_txt = str(username_login or "").strip()
    if username_txt:
        token = _build_auth_token(username_txt, role, unit, account_profile, name)
        if token:
            _set_auth_query_token(token)
    st.rerun()


def logout_user():
    _set_auth_query_token("")
    st.session_state["logged_in"] = False
    st.session_state["role"] = None
    st.session_state["user_name"] = ""
    st.session_state["unit"] = ""
    st.session_state["account_profile"] = None
    st.session_state["_active_runtime_loaded"] = False
    st.rerun()

# --- HELPER FUNCTIONS DE NEGOCIO ---
def class_names():
    return [c["nome"] for c in st.session_state["classes"]]

def teacher_names():
    return [t["nome"] for t in st.session_state["teachers"]]

def parse_money(value):
    try:
        if value is None:
            return 0.0
        if isinstance(value, (int, float)):
            return float(value)
        raw = str(value).strip()
        if not raw:
            return 0.0

        clean = re.sub(r"[^\d,.\-]", "", raw)
        if not clean:
            return 0.0

        if "," in clean and "." in clean:
            # Formato brasileiro: 1.234,56
            if clean.rfind(",") > clean.rfind("."):
                clean = clean.replace(".", "").replace(",", ".")
            else:
                # Formato internacional: 1,234.56
                clean = clean.replace(",", "")
        elif "," in clean:
            clean = clean.replace(".", "").replace(",", ".")
        elif clean.count(".") > 1:
            parts = clean.split(".")
            clean = "".join(parts[:-1]) + "." + parts[-1]
        elif "." in clean:
            left, right = clean.split(".", 1)
            # 3.588 -> 3588 (milhar), 299.50 -> decimal
            if len(right) == 3 and left.isdigit() and right.isdigit():
                clean = left + right

        return float(clean)
    except Exception:
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
    duracao = parse_int(event.get("duracao_minutos", 60))
    if duracao <= 0:
        duracao = 60
    fim = inicio + datetime.timedelta(minutes=duracao)
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

def build_sales_google_calendar_event_link(schedule_obj):
    schedule_obj = schedule_obj if isinstance(schedule_obj, dict) else {}
    lead_nome = str(schedule_obj.get("lead_nome", "")).strip() or "Lead"
    tipo = str(schedule_obj.get("tipo", "Agendamento")).strip() or "Agendamento"
    vendedor = str(schedule_obj.get("vendedor", "")).strip()
    telefone = str(schedule_obj.get("lead_telefone", "")).strip()
    detalhes = str(schedule_obj.get("detalhes", "")).strip()
    meeting_link = str(schedule_obj.get("meeting_link", "")).strip() or str(_get_config_value("ACTIVE_COMERCIAL_MEETING_LINK", "")).strip()
    descricao_linhas = [f"Tipo: {tipo}", f"Lead: {lead_nome}"]
    if telefone:
        descricao_linhas.append(f"Telefone: {telefone}")
    if vendedor:
        descricao_linhas.append(f"Consultor: {vendedor}")
    if detalhes:
        descricao_linhas.append(f"Detalhes: {detalhes}")
    event = {
        "data": str(schedule_obj.get("data", "")).strip(),
        "hora": str(schedule_obj.get("hora", "")).strip(),
        "duracao_minutos": parse_int(schedule_obj.get("duracao_minutos", 45)) or 45,
        "titulo": f"Comercial Active - {tipo} ({lead_nome})",
        "turma": "Comercial",
        "professor": vendedor,
        "descricao": "\n".join(descricao_linhas).strip(),
        "link": meeting_link,
    }
    return build_google_calendar_event_link(event)

def book_levels():
    books = st.session_state.get("books", [])
    levels = []
    seen = set()
    for b in books:
        nivel = normalize_text(str((b or {}).get("nivel", "")).strip())
        canon = ""
        if "livro 4.5" in nivel or "livro4.5" in nivel or "livro 4,5" in nivel or "livro4,5" in nivel:
            canon = "Livro 5"
        if "livro" in nivel:
            for i in range(1, 6):
                if f"livro {i}" in nivel or f"livro{i}" in nivel:
                    canon = f"Livro {i}"
                    break
        if canon and canon not in seen:
            seen.add(canon)
            levels.append(canon)
    return levels or ["Livro 1", "Livro 2", "Livro 3", "Livro 4", "Livro 5"]

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
    level_norm = normalize_text(level)
    if "livro 4.5" in level_norm or "livro4.5" in level_norm or "livro 4,5" in level_norm or "livro4,5" in level_norm:
        return "Livro 5"
    # Accept "Livro 1".."Livro 5" (and minor variations).
    for i in range(1, 6):
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

def _is_vip_module_label(value):
    modulo_norm = normalize_text(value)
    return "vip" in modulo_norm

def _vip_plan_total(plan_label):
    plan_norm = normalize_text(plan_label)
    if "avulsa" in plan_norm:
        return 1
    if "pacote" in plan_norm and "10" in plan_norm:
        return 10
    return 0

def _student_vip_summary(student_obj):
    if not isinstance(student_obj, dict):
        return None
    modulo = str(student_obj.get("modulo", "")).strip()
    if not _is_vip_module_label(modulo):
        return None
    plano = str(student_obj.get("vip_tipo_plano", "")).strip()
    if not plano:
        return None
    total = max(0, parse_int(student_obj.get("vip_aulas_total", 0)))
    restantes = max(0, parse_int(student_obj.get("vip_aulas_restantes", total)))
    return {
        "plano": plano,
        "total": total,
        "restantes": restantes,
    }

def _consume_vip_package_for_class(turma_nome):
    turma_label = str(turma_nome or "").strip()
    if not turma_label:
        return []
    consumidos = []
    changed = False
    for aluno in st.session_state.get("students", []):
        if str(aluno.get("turma", "")).strip() != turma_label:
            continue
        resumo_vip = _student_vip_summary(aluno)
        if not resumo_vip:
            continue
        restantes = int(resumo_vip.get("restantes", 0))
        if restantes <= 0:
            continue
        aluno["vip_aulas_total"] = int(resumo_vip.get("total", 0))
        aluno["vip_aulas_restantes"] = max(0, restantes - 1)
        consumidos.append(
            {
                "nome": str(aluno.get("nome", "")).strip(),
                "restantes": int(aluno.get("vip_aulas_restantes", 0)),
            }
        )
        changed = True
    if changed:
        save_list(STUDENTS_FILE, st.session_state.get("students", []))
    return consumidos

def _vip_students_for_class(turma_nome):
    turma_label = str(turma_nome or "").strip()
    if not turma_label:
        return []
    vip_alunos = []
    for aluno in st.session_state.get("students", []):
        if str(aluno.get("turma", "")).strip() != turma_label:
            continue
        resumo_vip = _student_vip_summary(aluno)
        if not resumo_vip:
            continue
        vip_alunos.append(
            {
                "nome": str(aluno.get("nome", "")).strip(),
                "plano": str(resumo_vip.get("plano", "")).strip(),
                "restantes": int(resumo_vip.get("restantes", 0)),
                "total": int(resumo_vip.get("total", 0)),
            }
        )
    vip_alunos.sort(key=lambda item: normalize_text(item.get("nome", "")))
    return vip_alunos

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

def _challenge_target_type(value):
    target_norm = normalize_text(value)
    if "turma" in target_norm:
        return "turma"
    if "vip" in target_norm and "aluno" in target_norm:
        return "aluno_vip"
    if "aluno" in target_norm:
        return "aluno_vip"
    return "nivel"

def _challenge_target_parts(challenge_obj):
    ch = challenge_obj if isinstance(challenge_obj, dict) else {}
    return (
        _challenge_target_type(ch.get("target_type", "nivel")),
        str(ch.get("target_turma", "")).strip(),
        str(ch.get("target_aluno", "")).strip(),
    )


def _challenge_send_turmas(challenge_obj):
    ch = challenge_obj if isinstance(challenge_obj, dict) else {}
    raw = ch.get("target_turmas_envio", [])
    if isinstance(raw, list):
        return [str(x).strip() for x in raw if str(x).strip()]
    if isinstance(raw, str):
        return [part.strip() for part in raw.split(",") if part.strip()]
    return []


def _challenge_target_label(challenge_obj):
    target_type, target_turma, target_aluno = _challenge_target_parts(challenge_obj)
    if target_type == "turma":
        return f"Turma: {target_turma or '-'}"
    if target_type == "aluno_vip":
        return f"Aluno VIP: {target_aluno or '-'}"
    extra_turmas = _challenge_send_turmas(challenge_obj)
    base = f"Nivel: {_norm_book_level((challenge_obj or {}).get('nivel', '')) or '-'}"
    if extra_turmas:
        base += f" | Turmas: {', '.join(extra_turmas)}"
    return base

def get_weekly_challenge_for_target(level, week_key, target_type="nivel", target_turma="", target_aluno=""):
    level = _norm_book_level(level)
    week_key = str(week_key or "").strip()
    target_type = _challenge_target_type(target_type)
    target_turma = str(target_turma or "").strip()
    target_aluno = str(target_aluno or "").strip()
    for ch in st.session_state.get("challenges", []):
        ch_type, ch_turma, ch_aluno = _challenge_target_parts(ch)
        if str(ch.get("semana", "")).strip() != week_key:
            continue
        if ch_type != target_type:
            continue
        if target_type == "turma":
            if ch_turma != target_turma:
                continue
        elif target_type == "aluno_vip":
            if ch_aluno != target_aluno:
                continue
        elif _norm_book_level(ch.get("nivel", "")) != level:
            continue
        return ch
    return None

def get_weekly_challenge(level, week_key):
    return get_weekly_challenge_for_target(level, week_key, target_type="nivel")

def _challenge_matches_student(challenge_obj, student_obj):
    if not isinstance(challenge_obj, dict) or not isinstance(student_obj, dict):
        return False
    target_type, target_turma, target_aluno = _challenge_target_parts(challenge_obj)
    aluno_nome = str(student_obj.get("nome", "")).strip()
    turma_nome = str(student_obj.get("turma", "")).strip()
    allowed_turmas = set(_challenge_send_turmas(challenge_obj))
    if target_type == "turma":
        return bool(target_turma) and target_turma == turma_nome
    if target_type == "aluno_vip":
        return bool(target_aluno) and target_aluno == aluno_nome
    if allowed_turmas and turma_nome not in allowed_turmas:
        return False
    return student_book_level(student_obj) == _norm_book_level(challenge_obj.get("nivel", ""))

def _students_for_challenge_target(level, target_type="nivel", target_turma="", target_aluno="", target_turmas_envio=None):
    level = _norm_book_level(level)
    target_type = _challenge_target_type(target_type)
    target_turma = str(target_turma or "").strip()
    target_aluno = str(target_aluno or "").strip()
    raw_turmas = target_turmas_envio if isinstance(target_turmas_envio, (list, tuple, set)) else []
    allowed_turmas = {str(x).strip() for x in raw_turmas if str(x).strip()}
    out = []
    for student in st.session_state.get("students", []):
        if target_type == "turma":
            if str(student.get("turma", "")).strip() != target_turma:
                continue
        elif target_type == "aluno_vip":
            if str(student.get("nome", "")).strip() != target_aluno:
                continue
        else:
            if allowed_turmas and str(student.get("turma", "")).strip() not in allowed_turmas:
                continue
            if student_book_level(student) != level:
                continue
        out.append(student)
    return out

def get_student_weekly_challenges(student_obj, week_key):
    week_key = str(week_key or "").strip()
    desafios = [
        ch for ch in st.session_state.get("challenges", [])
        if str(ch.get("semana", "")).strip() == week_key and _challenge_matches_student(ch, student_obj)
    ]
    desafios.sort(
        key=lambda ch: (
            {"aluno_vip": 0, "turma": 1, "nivel": 2}.get(_challenge_target_type(ch.get("target_type", "nivel")), 9),
            str(ch.get("titulo", "")).strip().lower(),
        )
    )
    return desafios

def upsert_weekly_challenge(level, week_key, titulo, descricao, pontos, autor, due_date=None, rubrica="", dica="", target_type="nivel", target_turma="", target_aluno="", reference_theme="", reference_book="", reference_subject="", reference_note="", target_turmas_envio=None):
    level = _norm_book_level(level)
    week_key = str(week_key or "").strip()
    titulo = str(titulo or "").strip()
    descricao = str(descricao or "").strip()
    pontos = int(pontos or 0)
    autor = str(autor or "").strip()
    due_str = due_date.strftime("%d/%m/%Y") if isinstance(due_date, datetime.date) else str(due_date or "").strip()
    rubrica = str(rubrica or "").strip()
    dica = str(dica or "").strip()
    target_type = _challenge_target_type(target_type)
    target_turma = str(target_turma or "").strip()
    target_aluno = str(target_aluno or "").strip()
    target_turmas_envio = [str(x).strip() for x in (target_turmas_envio or []) if str(x).strip()]
    reference_theme = str(reference_theme or "").strip()
    reference_book = str(reference_book or "").strip()
    reference_subject = str(reference_subject or "").strip()
    reference_note = str(reference_note or "").strip()
    existing = get_weekly_challenge_for_target(level, week_key, target_type=target_type, target_turma=target_turma, target_aluno=target_aluno)
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
        existing["target_type"] = target_type
        existing["target_turma"] = target_turma
        existing["target_aluno"] = target_aluno
        existing["target_turmas_envio"] = target_turmas_envio
        existing["reference_theme"] = reference_theme
        existing["reference_book"] = reference_book
        existing["reference_subject"] = reference_subject
        existing["reference_note"] = reference_note
        existing["updated_at"] = datetime.datetime.now().strftime("%d/%m/%Y %H:%M")
        saved = existing
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
            "target_type": target_type,
            "target_turma": target_turma,
            "target_aluno": target_aluno,
            "target_turmas_envio": target_turmas_envio,
            "reference_theme": reference_theme,
            "reference_book": reference_book,
            "reference_subject": reference_subject,
            "reference_note": reference_note,
            "created_at": datetime.datetime.now().strftime("%d/%m/%Y %H:%M"),
            "updated_at": "",
        }
        st.session_state["challenges"].append(ch)
        saved = ch
    save_list(CHALLENGES_FILE, st.session_state["challenges"])
    return saved

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
    if existing:
        return False, "Tentativa unica: voce ja enviou resposta para este desafio."

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
            "challenge_title": str(challenge_obj.get("titulo", "")).strip(),
            "challenge_target": _challenge_target_label(challenge_obj),
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

def _is_homework_activity(activity_obj):
    activity_obj = activity_obj if isinstance(activity_obj, dict) else {}
    tipo = normalize_text(activity_obj.get("tipo", ""))
    titulo = normalize_text(activity_obj.get("titulo", ""))
    markers = ("licao de casa", "licoes de casa", "tarefa de casa", "homework")
    return any(tag in tipo for tag in markers) or any(tag in titulo for tag in markers)

def _recent_class_lessons_for_homework(turma_nome, limit=4):
    turma_nome = str(turma_nome or "").strip()
    sessions = [
        s for s in st.session_state.get("class_sessions", [])
        if str(s.get("turma", "")).strip() == turma_nome and str(s.get("status", "")).strip().lower() == "finalizada"
    ]
    sessions = sorted(
        sessions,
        key=lambda x: (
            parse_date(x.get("data", "")) or datetime.date(1900, 1, 1),
            parse_time(x.get("hora_inicio_real", x.get("hora_inicio_prevista", "00:00"))),
        ),
        reverse=True,
    )
    out = []
    for sess in sessions:
        txt = str(sess.get("licao", "")).strip() or str(sess.get("resumo_final", "")).strip()
        if txt:
            out.append(txt)
        if len(out) >= max(1, int(limit or 4)):
            break
    return out

def _current_subject_for_challenge(turma_nome, turma_obj=None):
    turma_nome = str(turma_nome or "").strip()
    turma_obj = turma_obj if isinstance(turma_obj, dict) else {}
    lesson_reader = globals().get("_recent_class_lessons_for_homework")
    if turma_nome and callable(lesson_reader):
        try:
            latest = lesson_reader(turma_nome, limit=1) or [""]
            subject = str(latest[0] or "").strip()
            if subject:
                return subject
        except Exception:
            pass
    for field in ("materia", "conteudo", "disciplina", "modulo"):
        value = str(turma_obj.get(field, "")).strip()
        if value:
            return value
    return ""

def _normalize_activity_questions_from_ai(raw_questions, fallback_count=3):
    items = raw_questions if isinstance(raw_questions, list) else []
    normalized = []
    for idx, question in enumerate(items, start=1):
        q = question if isinstance(question, dict) else {}
        q_type_raw = normalize_text(q.get("tipo", "aberta"))
        is_multiple = any(token in q_type_raw for token in ("multipla", "multiple", "objetiva", "escolha"))
        enunciado = str(q.get("enunciado", q.get("pergunta", ""))).strip() or f"Questao {idx}"
        pontos = parse_int(q.get("pontos", 10))
        if pontos <= 0:
            pontos = 10
        pontos = max(1, min(100, pontos))

        if is_multiple:
            opcoes_raw = q.get("opcoes", q.get("alternativas", []))
            if isinstance(opcoes_raw, str):
                opcoes = [line.strip() for line in opcoes_raw.splitlines() if line.strip()]
            elif isinstance(opcoes_raw, list):
                opcoes = [str(opt).strip() for opt in opcoes_raw if str(opt).strip()]
            else:
                opcoes = []
            if len(opcoes) < 2:
                normalized.append(
                    {
                        "id": uuid.uuid4().hex,
                        "tipo": "aberta",
                        "enunciado": enunciado,
                        "opcoes": [],
                        "correta_idx": None,
                        "pontos": pontos,
                    }
                )
                continue
            correta_idx = q.get("correta_idx", q.get("correta", None))
            try:
                correta_idx = int(correta_idx)
            except Exception:
                correta_idx = None
            # Aceita 1-based vindo da IA e converte para 0-based.
            if correta_idx is not None and 1 <= correta_idx <= len(opcoes):
                correta_idx = correta_idx - 1
            if correta_idx is not None and (correta_idx < 0 or correta_idx >= len(opcoes)):
                correta_idx = None
            normalized.append(
                {
                    "id": uuid.uuid4().hex,
                    "tipo": "multipla_escolha",
                    "enunciado": enunciado,
                    "opcoes": opcoes,
                    "correta_idx": correta_idx,
                    "pontos": pontos,
                }
            )
        else:
            normalized.append(
                {
                    "id": uuid.uuid4().hex,
                    "tipo": "aberta",
                    "enunciado": enunciado,
                    "opcoes": [],
                    "correta_idx": None,
                    "pontos": pontos,
                }
            )

    if normalized:
        return normalized

    fallback_total = max(1, min(10, parse_int(fallback_count or 3)))
    return [
        {
            "id": uuid.uuid4().hex,
            "tipo": "aberta",
            "enunciado": f"Questao {idx}",
            "opcoes": [],
            "correta_idx": None,
            "pontos": 10,
        }
        for idx in range(1, fallback_total + 1)
    ]

def generate_weekly_homework_ai(turma_nome, livro_nome, week_key, lesson_context, question_count=5, foco_extra=""):
    turma_nome = str(turma_nome or "").strip() or "Turma"
    livro_nome = _norm_book_level(livro_nome or "")
    week_key = str(week_key or "").strip()
    question_count = max(1, min(10, parse_int(question_count or 5)))
    lesson_context = [str(x).strip() for x in (lesson_context or []) if str(x).strip()]
    focus = str(foco_extra or "").strip()
    lessons_text = "; ".join(lesson_context[:4]) if lesson_context else "Sem licao registrada."

    messages = [
        {
            "role": "system",
            "content": (
                "Voce e o Professor Wiz (IA) e cria licoes de casa semanais de ingles para turmas escolares.\n"
                "Responda SOMENTE em JSON valido, sem markdown."
            ),
        },
        {
            "role": "user",
            "content": (
                f"Turma: {turma_nome}\n"
                f"Livro/Nivel: {livro_nome}\n"
                f"Semana: {week_key}\n"
                f"Licoes recentes da turma: {lessons_text}\n"
                f"Foco opcional informado pelo professor/coordenador: {focus or 'Nenhum'}\n\n"
                f"Crie uma licao de casa semanal com {question_count} questoes.\n"
                "A atividade deve poder ser respondida no portal do aluno.\n\n"
                "Retorne JSON com campos:\n"
                "titulo (string), descricao (string), questions (array).\n"
                "Cada item de questions deve ter:\n"
                "tipo ('aberta' ou 'multipla_escolha'), enunciado (string), pontos (int),\n"
                "opcoes (array, somente para multipla_escolha) e correta_idx (int opcional).\n"
            ),
        },
    ]
    raw = _groq_chat_text(messages, temperature=0.3, max_tokens=1400)
    obj = _extract_json_object(raw)
    titulo = str(obj.get("titulo", "")).strip() or f"Licao de Casa Semanal - {turma_nome}"
    descricao = str(obj.get("descricao", "")).strip() or "Resolva as questoes com base no conteudo da semana."
    questions_payload = _normalize_activity_questions_from_ai(obj.get("questions", []), fallback_count=question_count)
    return {
        "turma": turma_nome,
        "livro": livro_nome,
        "semana": week_key,
        "titulo": titulo,
        "descricao": descricao,
        "questions": questions_payload,
    }

def _publish_homework_activity(
    turma_nome,
    titulo,
    descricao,
    due_date,
    questions_payload,
    autor_nome,
    allow_resubmission=False,
    notify_students=True,
):
    turma_nome = str(turma_nome or "").strip()
    titulo = str(titulo or "").strip() or "Licao de Casa"
    descricao = str(descricao or "").strip()
    if isinstance(due_date, datetime.datetime):
        due_obj = due_date.date()
    elif isinstance(due_date, datetime.date):
        due_obj = due_date
    else:
        due_obj = parse_date(str(due_date or ""))
    due_txt = due_obj.strftime("%d/%m/%Y") if due_obj else ""
    questions_payload = _normalize_activity_questions_from_ai(questions_payload, fallback_count=3)

    activity_obj = {
        "id": uuid.uuid4().hex,
        "turma": turma_nome,
        "tipo": "Licao de Casa",
        "titulo": titulo,
        "descricao": descricao,
        "questions": questions_payload,
        "allow_resubmission": bool(allow_resubmission),
        "status": "Ativa",
        "autor": str(autor_nome or "Professor").strip() or "Professor",
        "due_date": due_txt,
        "created_at": datetime.datetime.now().strftime("%d/%m/%Y %H:%M"),
        "updated_at": "",
    }
    st.session_state["activities"].append(activity_obj)
    save_list(ACTIVITIES_FILE, st.session_state["activities"])

    stats = {"email_total": 0, "email_ok": 0, "whatsapp_total": 0, "whatsapp_ok": 0}
    if notify_students and turma_nome:
        assunto = f"[Active] Nova licao de casa - Turma {turma_nome}"
        corpo = (
            f"Nova licao de casa semanal publicada.\n"
            f"Turma: {turma_nome}\n"
            f"Prazo: {due_txt or 'Sem prazo'}\n\n"
            f"{titulo}\n\n"
            f"{descricao}\n\n"
            "Acesse o portal do aluno > Licoes de Casa para responder."
        )
        stats = email_students_by_turma(turma_nome, assunto, corpo, "Licoes de Casa")
    return activity_obj, stats

def run_weekly_homework_panel(panel_key, turmas_disponiveis, autor_nome):
    turmas = sorted({str(t).strip() for t in (turmas_disponiveis or []) if str(t).strip()})
    st.markdown('<div class="main-header">Licoes de Casa Semanais</div>', unsafe_allow_html=True)
    st.caption("Publique licoes de casa semanais por turma. O aluno responde direto no portal.")
    if not turmas:
        st.info("Nenhuma turma disponivel para publicar licao de casa.")
        return

    draft_key = f"{panel_key}_homework_ai_draft"
    tab_ia, tab_manual, tab_publicadas, tab_respostas = st.tabs(
        ["Gerar com IA (Wiz)", "Publicar manual", "Licoes publicadas", "Respostas dos alunos"]
    )

    with tab_ia:
        turma_sel = st.selectbox("Turma", turmas, key=f"{panel_key}_hw_ia_turma")
        turma_obj = next((c for c in st.session_state.get("classes", []) if str(c.get("nome", "")).strip() == turma_sel), {})
        livro_turma = _norm_book_level(turma_obj.get("livro", ""))
        semana = current_week_key(datetime.date.today())
        licoes_recentes = _recent_class_lessons_for_homework(turma_sel, limit=4)
        st.caption(f"Livro/Nivel da turma: {livro_turma or 'Nao definido'}")
        if licoes_recentes:
            st.caption("Ultimas licoes da turma: " + " | ".join(licoes_recentes[:3]))
        else:
            st.caption("Sem licoes finalizadas registradas para esta turma.")

        c1, c2 = st.columns(2)
        with c1:
            qtd_questoes = st.number_input(
                "Quantidade de questoes",
                min_value=1,
                max_value=10,
                value=4,
                step=1,
                key=f"{panel_key}_hw_ia_qtd",
            )
            prazo_dias = st.number_input(
                "Prazo (dias a partir de hoje)",
                min_value=1,
                max_value=30,
                value=7,
                step=1,
                key=f"{panel_key}_hw_ia_prazo",
            )
        with c2:
            allow_resubmission = st.checkbox(
                "Permitir reenvio do aluno",
                value=False,
                key=f"{panel_key}_hw_ia_reenvio",
            )
            enviar_comunicado = st.checkbox(
                "Enviar comunicado automatico (e-mail + WhatsApp)",
                value=True,
                key=f"{panel_key}_hw_ia_notify",
            )
        foco_extra = st.text_input(
            "Foco da semana (opcional)",
            key=f"{panel_key}_hw_ia_foco",
            placeholder="Ex: Simple Present, leitura da Unit 3, vocabulario de rotina...",
        )
        if st.button("Gerar licao semanal com IA", type="primary", key=f"{panel_key}_hw_ia_generate"):
            api_key = get_groq_api_key()
            if not api_key:
                st.error("Configure GROQ_API_KEY para gerar licao com IA.")
            else:
                try:
                    draft = generate_weekly_homework_ai(
                        turma_sel,
                        livro_turma,
                        semana,
                        licoes_recentes,
                        question_count=qtd_questoes,
                        foco_extra=foco_extra,
                    )
                    draft["allow_resubmission"] = bool(allow_resubmission)
                    draft["notify_students"] = bool(enviar_comunicado)
                    draft["due_date"] = datetime.date.today() + datetime.timedelta(days=int(prazo_dias))
                    st.session_state[draft_key] = draft
                    st.success("Licao de casa gerada com IA. Revise e publique.")
                    st.rerun()
                except Exception as exc:
                    st.error(f"Falha ao gerar licao com IA: {exc}")

        draft = st.session_state.get(draft_key)
        if isinstance(draft, dict):
            st.markdown("---")
            st.markdown("### Rascunho gerado")
            st.markdown(f"**Titulo:** {draft.get('titulo', '')}")
            st.write(str(draft.get("descricao", "")).strip())
            due_obj = draft.get("due_date")
            due_txt = due_obj.strftime("%d/%m/%Y") if isinstance(due_obj, (datetime.date, datetime.datetime)) else str(due_obj or "")
            st.caption(f"Turma: {draft.get('turma', '')} | Prazo: {due_txt or 'Sem prazo'}")

            for idx, q in enumerate(draft.get("questions", []), start=1):
                st.markdown(f"**{idx}. {q.get('enunciado', '')}**")
                st.caption(f"Tipo: {q.get('tipo', 'aberta')} | Pontos: {q.get('pontos', 0)}")
                if q.get("tipo") == "multipla_escolha":
                    for opt_idx, opt in enumerate(q.get("opcoes", []), start=1):
                        st.write(f"{opt_idx}) {opt}")

            p1, p2 = st.columns([1, 1])
            with p1:
                if st.button("Publicar no portal do aluno", type="primary", key=f"{panel_key}_hw_ia_publish"):
                    _, stats = _publish_homework_activity(
                        turma_nome=draft.get("turma", ""),
                        titulo=draft.get("titulo", ""),
                        descricao=draft.get("descricao", ""),
                        due_date=draft.get("due_date", ""),
                        questions_payload=draft.get("questions", []),
                        autor_nome=autor_nome,
                        allow_resubmission=bool(draft.get("allow_resubmission", False)),
                        notify_students=bool(draft.get("notify_students", True)),
                    )
                    st.success("Licao publicada com sucesso.")
                    if bool(draft.get("notify_students", True)):
                        st.info(
                            "Comunicado enviado: "
                            f"E-mail {stats.get('email_ok', 0)}/{stats.get('email_total', 0)} | "
                            f"WhatsApp {stats.get('whatsapp_ok', 0)}/{stats.get('whatsapp_total', 0)}."
                        )
                    st.session_state.pop(draft_key, None)
                    st.rerun()
            with p2:
                if st.button("Descartar rascunho", key=f"{panel_key}_hw_ia_discard"):
                    st.session_state.pop(draft_key, None)
                    st.rerun()

    with tab_manual:
        with st.form(f"{panel_key}_hw_manual_form"):
            turma_atividade = st.selectbox("Turma", turmas, key=f"{panel_key}_hw_manual_turma")
            titulo_atividade = st.text_input("Titulo", key=f"{panel_key}_hw_manual_titulo")
            descricao_atividade = st.text_area("Descricao / instrucoes", key=f"{panel_key}_hw_manual_desc")
            due_date = st.date_input(
                "Prazo final",
                value=datetime.date.today() + datetime.timedelta(days=7),
                format="DD/MM/YYYY",
                key=f"{panel_key}_hw_manual_due",
            )
            allow_resubmission = st.checkbox(
                "Permitir reenvio do aluno",
                value=False,
                key=f"{panel_key}_hw_manual_reenvio",
            )
            enviar_comunicado = st.checkbox(
                "Enviar comunicado automatico (e-mail + WhatsApp)",
                value=True,
                key=f"{panel_key}_hw_manual_notify",
            )
            qtd_questoes = st.number_input(
                "Quantidade de questoes",
                min_value=1,
                max_value=20,
                value=3,
                step=1,
                key=f"{panel_key}_hw_manual_qtd",
            )
            st.caption("Monte as questoes abaixo. Em multipla escolha, informe uma opcao por linha.")

            questions_payload = []
            validation_errors = []
            for idx in range(int(qtd_questoes)):
                st.markdown(f"#### Questao {idx + 1}")
                q_tipo_label = st.selectbox(
                    "Tipo da questao",
                    ["Multipla escolha", "Resposta aberta"],
                    key=f"{panel_key}_hw_manual_qtype_{idx}",
                )
                q_enunciado = st.text_area("Enunciado", key=f"{panel_key}_hw_manual_qtext_{idx}")
                q_pontos = st.number_input(
                    "Pontos da questao",
                    min_value=1,
                    max_value=100,
                    value=10,
                    step=1,
                    key=f"{panel_key}_hw_manual_qpoints_{idx}",
                )
                if not str(q_enunciado).strip():
                    validation_errors.append(f"Questao {idx + 1}: informe o enunciado.")
                if q_tipo_label == "Multipla escolha":
                    q_opcoes_text = st.text_area(
                        "Opcoes (uma por linha)",
                        value="Opcao A\nOpcao B\nOpcao C\nOpcao D",
                        key=f"{panel_key}_hw_manual_qopts_{idx}",
                    )
                    q_opcoes = [line.strip() for line in str(q_opcoes_text or "").splitlines() if line.strip()]
                    if len(q_opcoes) < 2:
                        validation_errors.append(f"Questao {idx + 1}: multipla escolha precisa de ao menos 2 opcoes.")
                    corretas_opts = ["Nao definir"] + q_opcoes if q_opcoes else ["Nao definir"]
                    q_correta = st.selectbox(
                        "Resposta correta (opcional)",
                        corretas_opts,
                        key=f"{panel_key}_hw_manual_qcorrect_{idx}",
                    )
                    correta_idx = q_opcoes.index(q_correta) if q_correta != "Nao definir" and q_correta in q_opcoes else None
                    questions_payload.append(
                        {
                            "id": uuid.uuid4().hex,
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
                            "id": uuid.uuid4().hex,
                            "tipo": "aberta",
                            "enunciado": str(q_enunciado).strip(),
                            "opcoes": [],
                            "correta_idx": None,
                            "pontos": int(q_pontos),
                        }
                    )

            if st.form_submit_button("Publicar licao de casa", type="primary"):
                if not str(titulo_atividade).strip():
                    st.error("Informe o titulo da licao.")
                elif validation_errors:
                    st.error(validation_errors[0])
                else:
                    _, stats = _publish_homework_activity(
                        turma_nome=turma_atividade,
                        titulo=titulo_atividade,
                        descricao=descricao_atividade,
                        due_date=due_date,
                        questions_payload=questions_payload,
                        autor_nome=autor_nome,
                        allow_resubmission=bool(allow_resubmission),
                        notify_students=bool(enviar_comunicado),
                    )
                    st.success("Licao de casa publicada com sucesso.")
                    if enviar_comunicado:
                        st.info(
                            "Comunicado enviado: "
                            f"E-mail {stats.get('email_ok', 0)}/{stats.get('email_total', 0)} | "
                            f"WhatsApp {stats.get('whatsapp_ok', 0)}/{stats.get('whatsapp_total', 0)}."
                        )
                    st.rerun()

    with tab_publicadas:
        homework_items = [
            a for a in st.session_state.get("activities", [])
            if str(a.get("turma", "")).strip() in set(turmas) and _is_homework_activity(a)
        ]
        homework_items = sorted(
            homework_items,
            key=lambda a: (
                0 if _is_activity_open(a) else 1,
                parse_date(a.get("due_date", "")) or datetime.date(2100, 1, 1),
                str(a.get("created_at", "")),
            ),
        )
        if not homework_items:
            st.info("Nenhuma licao de casa publicada ainda.")
        else:
            for atividade in homework_items:
                activity_id = str(atividade.get("id", "")).strip()
                titulo = str(atividade.get("titulo", "Licao de Casa")).strip() or "Licao de Casa"
                turma = str(atividade.get("turma", "")).strip()
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
                        f"Prazo: {due_date} | Questoes: {len(atividade.get('questions', []) or [])} | Pontos: {total_pontos}"
                    )
                    st.caption(f"Respostas recebidas: {total_submissoes}/{len(alunos_turma)}")
                    if str(atividade.get("descricao", "")).strip():
                        st.write(str(atividade.get("descricao", "")).strip())
                    if _is_activity_open(atividade):
                        if st.button("Encerrar licao", key=f"{panel_key}_close_hw_{activity_id}"):
                            atividade["status"] = "Encerrada"
                            atividade["updated_at"] = datetime.datetime.now().strftime("%d/%m/%Y %H:%M")
                            save_list(ACTIVITIES_FILE, st.session_state["activities"])
                            st.success("Licao encerrada.")
                            st.rerun()
                    else:
                        if st.button("Reabrir licao", key=f"{panel_key}_open_hw_{activity_id}"):
                            atividade["status"] = "Ativa"
                            atividade["updated_at"] = datetime.datetime.now().strftime("%d/%m/%Y %H:%M")
                            save_list(ACTIVITIES_FILE, st.session_state["activities"])
                            st.success("Licao reaberta.")
                            st.rerun()

    with tab_respostas:
        homework_items = [
            a for a in st.session_state.get("activities", [])
            if str(a.get("turma", "")).strip() in set(turmas) and _is_homework_activity(a)
        ]
        homework_items = sorted(
            homework_items,
            key=lambda a: (
                parse_date(a.get("due_date", "")) or datetime.date(2100, 1, 1),
                str(a.get("created_at", "")),
            ),
            reverse=True,
        )
        if not homework_items:
            st.info("Nenhuma licao de casa publicada para acompanhar respostas.")
        else:
            atividade_labels = []
            atividade_map = {}
            for atividade in homework_items:
                aid = str(atividade.get("id", "")).strip()
                label = (
                    f"{str(atividade.get('turma', '')).strip()} | "
                    f"{str(atividade.get('titulo', 'Licao de Casa')).strip()} | "
                    f"#{aid[:6]}"
                )
                atividade_labels.append(label)
                atividade_map[label] = atividade
            atividade_sel_label = st.selectbox("Licao", atividade_labels, key=f"{panel_key}_hw_ans_select")
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
                st.info("Ainda nao ha respostas para esta licao.")
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

                    with st.form(f"{panel_key}_grade_hw_{sub_id}"):
                        nota_default = activity_submission_final_score(sub)
                        nota_prof = st.number_input(
                            "Nota final do professor",
                            min_value=0.0,
                            max_value=float(nota_total if nota_total > 0 else 100.0),
                            value=float(min(max(nota_default, 0.0), nota_total if nota_total > 0 else 100.0)),
                            step=0.5,
                            key=f"{panel_key}_grade_hw_value_{sub_id}",
                        )
                        feedback_prof = st.text_area(
                            "Feedback para o aluno",
                            value=str(sub.get("feedback_professor", "")).strip(),
                            key=f"{panel_key}_grade_hw_feedback_{sub_id}",
                        )
                        if st.form_submit_button("Salvar avaliacao"):
                            sub["score_professor"] = float(nota_prof)
                            sub["feedback_professor"] = str(feedback_prof).strip()
                            sub["status"] = "Avaliada"
                            sub["avaliado_em"] = datetime.datetime.now().strftime("%d/%m/%Y %H:%M")
                            save_list(ACTIVITY_SUBMISSIONS_FILE, st.session_state["activity_submissions"])
                            st.success("Avaliacao salva.")
                            st.rerun()

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

def sales_pipeline_stage_options():
    return [
        "Descoberta",
        "Contato inicial",
        "Qualificacao",
        "Apresentacao",
        "Negociacao",
        "Fechamento",
        "Pos-venda",
        "Descartado",
    ]

def sales_state_options():
    return [
        "",
        "AC", "AL", "AP", "AM", "BA", "CE", "DF", "ES", "GO",
        "MA", "MT", "MS", "MG", "PA", "PB", "PR", "PE", "PI",
        "RJ", "RN", "RS", "RO", "RR", "SC", "SP", "SE", "TO",
    ]

def _lead_tags_list(raw_value):
    items = []
    if isinstance(raw_value, (list, tuple, set)):
        items = [str(v).strip() for v in raw_value]
    else:
        text = str(raw_value or "").strip()
        if text:
            text = text.replace(";", ",").replace("\n", ",")
            items = [p.strip() for p in text.split(",")]
    tags = []
    seen = set()
    for item in items:
        if not item:
            continue
        key = normalize_text(item)
        if key and key not in seen:
            tags.append(item)
            seen.add(key)
    return tags

def _lead_tags_text(lead_obj):
    if not isinstance(lead_obj, dict):
        return ""
    return ", ".join(_lead_tags_list(lead_obj.get("tags", [])))

def _lead_custom_fields_to_text(custom_obj):
    if not isinstance(custom_obj, dict):
        return ""
    lines = []
    for key, value in custom_obj.items():
        k = str(key or "").strip()
        v = str(value or "").strip()
        if k:
            lines.append(f"{k}: {v}")
    return "\n".join(lines)

def _lead_custom_fields_from_text(raw_text):
    custom = {}
    for raw_line in str(raw_text or "").splitlines():
        line = str(raw_line or "").strip()
        if not line:
            continue
        if ":" in line:
            key, val = line.split(":", 1)
        elif "=" in line:
            key, val = line.split("=", 1)
        else:
            key, val = line, ""
        key = str(key or "").strip()
        val = str(val or "").strip()
        if key:
            custom[key] = val
    return custom

def _lead_last_contact_date(lead_obj):
    if not isinstance(lead_obj, dict):
        return None
    raw_contact = str(lead_obj.get("ultimo_contato", "")).strip()
    if raw_contact:
        dt = parse_date(raw_contact.split(" ")[0])
        if dt:
            return dt
    for inter in reversed(lead_obj.get("interacoes", [])):
        if not isinstance(inter, dict):
            continue
        raw_dt = str(inter.get("data_hora", "")).strip()
        if not raw_dt:
            continue
        dt = parse_date(raw_dt.split(" ")[0])
        if dt:
            return dt
    return None

def _sales_stage_from_status(status_txt):
    status_txt = normalize_text(status_txt)
    if status_txt == normalize_text("Fechado"):
        return "Fechamento"
    if status_txt == normalize_text("Desistir"):
        return "Descartado"
    if status_txt == normalize_text("Leads quentes"):
        return "Negociacao"
    if status_txt == normalize_text("Leads frios"):
        return "Contato inicial"
    return "Qualificacao"

def _sales_match_option(raw_value, options, default_value):
    value = str(raw_value or "").strip()
    if not value:
        return default_value
    norm = normalize_text(value)
    for opt in options:
        if normalize_text(opt) == norm:
            return opt
    return default_value

def _sales_import_normalize_key(key):
    text = normalize_text(key).replace("_", " ").replace("-", " ").replace("/", " ")
    return " ".join(text.split())

def _sales_import_parse_rows(uploaded_file):
    if not uploaded_file:
        return [], "Arquivo nao enviado."
    name = str(getattr(uploaded_file, "name", "") or "").strip()
    ext = Path(name).suffix.lower()
    raw = uploaded_file.getvalue()
    if not raw:
        return [], "Arquivo vazio."
    try:
        if ext in (".csv", ".txt"):
            text = raw.decode("utf-8-sig", errors="ignore")
            df = pd.read_csv(io.StringIO(text), sep=None, engine="python", dtype=str)
        elif ext in (".xlsx", ".xls", ".xlsb"):
            if ext == ".xlsb":
                try:
                    df = pd.read_excel(io.BytesIO(raw), dtype=str, engine="pyxlsb")
                except Exception:
                    df = pd.read_excel(io.BytesIO(raw), dtype=str)
            else:
                df = pd.read_excel(io.BytesIO(raw), dtype=str)
        elif ext == ".json":
            parsed = json.loads(raw.decode("utf-8-sig", errors="ignore"))
            if isinstance(parsed, list):
                rows = parsed
            elif isinstance(parsed, dict):
                if isinstance(parsed.get("leads"), list):
                    rows = parsed.get("leads", [])
                elif isinstance(parsed.get("data"), list):
                    rows = parsed.get("data", [])
                else:
                    rows = [parsed]
            else:
                return [], "JSON invalido para importacao de leads."
            clean_rows = [r for r in rows if isinstance(r, dict)]
            return clean_rows, ""
        else:
            return [], "Formato nao suportado. Use CSV, XLSX ou JSON."
    except Exception as ex:
        return [], f"Falha ao ler arquivo: {ex}"
    if df is None or df.empty:
        return [], "Arquivo sem linhas para importar."
    df = df.fillna("")
    return df.to_dict("records"), ""

def _sales_extract_text_candidates(normalized_row):
    items = []
    for key_norm, value in (normalized_row or {}).items():
        text = str(value or "").strip()
        if not text:
            continue
        items.append((key_norm, text))
    return items

def _sales_numeric_token_to_digits(text):
    raw = str(text or "").strip()
    if not raw:
        return ""
    token = raw.replace("\u00a0", "").replace(" ", "").replace(",", ".")
    if not re.fullmatch(r"[+\-]?\d+(?:\.\d+)?(?:[eE][+\-]?\d+)?", token):
        return ""
    try:
        dec_value = Decimal(token)
    except InvalidOperation:
        return ""
    if dec_value <= 0:
        return ""
    dec_int = dec_value.to_integral_value()
    if dec_value != dec_int:
        return ""
    return re.sub(r"\D", "", format(dec_int, "f"))

def _sales_guess_phone_from_text(text):
    raw = str(text or "").strip()
    if not raw:
        return ""
    from_numeric_token = _sales_numeric_token_to_digits(raw)
    if len(from_numeric_token) >= 10:
        normalized_num = _normalize_whatsapp_number(from_numeric_token)
        if normalized_num:
            return normalized_num
    # Prioriza padrao brasileiro com DDD + numero (10/11 digitos), com ou sem +55.
    pattern = re.compile(r"(?:\+?55[\s\-\.]?)?(?:\(?\d{2}\)?[\s\-\.]?)?(?:9?\d{4})[\s\-\.]?\d{4}")
    matches = pattern.findall(raw)
    for match in matches:
        normalized = _normalize_whatsapp_number(match)
        if normalized:
            return normalized
    # Sequencias separadas por texto (evita juntar campos diferentes).
    number_chunks = re.findall(r"\d{10,16}", raw)
    for chunk in number_chunks:
        normalized_chunk = _normalize_whatsapp_number(chunk)
        if normalized_chunk:
            return normalized_chunk
    # Fallback por sequencia de digitos.
    digits = re.sub(r"\D+", "", raw)
    if len(digits) >= 10:
        return _normalize_whatsapp_number(digits)
    return ""

def _sales_guess_email_from_text(text):
    raw = str(text or "").strip()
    if not raw:
        return ""
    m = re.search(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", raw)
    if not m:
        return ""
    return str(m.group(0)).strip().lower()

def _sales_guess_name_from_candidates(candidates):
    best = ""
    best_score = -1
    blocked_keywords = {
        "telefone", "fone", "celular", "whatsapp", "email", "e mail",
        "origem", "status", "estagio", "funil", "cidade", "estado",
        "empresa", "cargo", "interesse", "cpf", "cnpj", "rg", "cep",
        "observacao", "descricao", "comentario", "anotacao",
    }
    for key_norm, value in candidates:
        text = str(value or "").strip()
        if not text:
            continue
        low = normalize_text(text)
        if "@" in text or "http://" in low or "https://" in low:
            continue
        if any(block in key_norm for block in blocked_keywords):
            continue
        text_for_name = re.sub(
            r"(?:\+?55[\s\-\.]?)?(?:\(?\d{2}\)?[\s\-\.]?)?(?:9?\d{4})[\s\-\.]?\d{4}",
            " ",
            text,
        )
        text_for_name = re.sub(r"\d+", " ", text_for_name)
        text_for_name = " ".join(text_for_name.split())
        if not text_for_name:
            continue
        letters = len(re.findall(r"[A-Za-zÀ-ÿ]", text_for_name))
        digits = len(re.findall(r"\d", text_for_name))
        if letters < 2:
            continue
        if digits > 0 and digits >= letters:
            continue
        words = [w for w in re.split(r"\s+", text_for_name) if w]
        if not words:
            continue
        score = letters + len(words) * 4
        if digits > 0:
            score -= digits * 2
        if len(words) >= 2:
            score += 12
        if len(text_for_name) > 60:
            score -= 10
        if score > best_score:
            best = text_for_name
            best_score = score
    return best

def _sales_reconcile_lead_record(lead_obj):
    if not isinstance(lead_obj, dict):
        return False

    changed = False

    old_nome = str(lead_obj.get("nome", "")).strip()
    old_telefone = str(lead_obj.get("telefone", "")).strip()
    old_celular = str(lead_obj.get("celular", "")).strip()
    old_email = str(lead_obj.get("email", "")).strip().lower()

    candidates = []
    for key in ["nome", "telefone", "celular", "email", "observacao", "interesse", "cargo", "empresa", "origem"]:
        value = str(lead_obj.get(key, "")).strip()
        if value:
            candidates.append((_sales_import_normalize_key(key), value))

    custom_fields = lead_obj.get("campos_personalizados", {})
    if isinstance(custom_fields, dict):
        for k, v in custom_fields.items():
            value = str(v or "").strip()
            if value:
                candidates.append((_sales_import_normalize_key(k), value))

    nome = old_nome
    telefone = _sales_guess_phone_from_text(old_telefone) if old_telefone else ""
    celular = _sales_guess_phone_from_text(old_celular) if old_celular else ""
    email_val = _sales_guess_email_from_text(old_email) if old_email else ""

    if not telefone and nome:
        telefone = _sales_guess_phone_from_text(nome)
    if not celular and nome:
        celular = _sales_guess_phone_from_text(nome)
    if not email_val and nome:
        email_val = _sales_guess_email_from_text(nome)

    if not telefone:
        blocked_for_phone = ["cpf", "cnpj", "rg", "cep", "idade", "nascimento", "matricula"]
        for key_norm, candidate_text in candidates:
            if any(k in key_norm for k in blocked_for_phone):
                continue
            guessed = _sales_guess_phone_from_text(candidate_text)
            if guessed:
                telefone = guessed
                break

    if not celular:
        preferred_mobile_keys = ["celular", "whatsapp", "mobile", "phone", "telefone", "fone", "numero"]
        for key_norm, candidate_text in candidates:
            if not any(k in key_norm for k in preferred_mobile_keys):
                continue
            guessed = _sales_guess_phone_from_text(candidate_text)
            if guessed:
                celular = guessed
                break
        if not celular:
            blocked_for_phone = ["cpf", "cnpj", "rg", "cep", "idade", "nascimento", "matricula"]
            for key_norm, candidate_text in candidates:
                if any(k in key_norm for k in blocked_for_phone):
                    continue
                guessed = _sales_guess_phone_from_text(candidate_text)
                if guessed:
                    celular = guessed
                    break
        if not celular and telefone:
            celular = telefone

    if not telefone and celular:
        telefone = celular

    if not email_val:
        for _, candidate_text in candidates:
            guessed = _sales_guess_email_from_text(candidate_text)
            if guessed:
                email_val = guessed
                break

    if nome:
        nome_limpo = _sales_guess_name_from_candidates([("nome", nome)])
    else:
        preferred_name = [
            (k, v)
            for k, v in candidates
            if any(tag in k for tag in ["nome", "name", "lead", "contato", "cliente"])
        ]
        nome_limpo = _sales_guess_name_from_candidates(preferred_name or candidates)
    if nome_limpo:
        nome = nome_limpo

    if not nome and email_val:
        local = str(email_val).split("@", 1)[0].replace(".", " ").replace("_", " ").replace("-", " ")
        local = " ".join(w for w in local.split() if w)
        if local:
            nome = local.title()
    if not nome and (telefone or celular):
        base_num = celular or telefone
        nome = f"Lead {str(base_num)[-4:]}"

    if nome != old_nome:
        lead_obj["nome"] = nome
        changed = True
    if telefone != old_telefone:
        lead_obj["telefone"] = telefone
        changed = True
    if celular != old_celular:
        lead_obj["celular"] = celular
        changed = True
    if email_val != old_email:
        lead_obj["email"] = email_val
        changed = True

    return changed

def _sales_import_map_row(row_obj, vendedor_atual, origem_padrao="", usar_wiz_detect=True):
    if not isinstance(row_obj, dict):
        return {}, "Linha invalida."
    normalized = {}
    original_by_norm = {}
    for raw_key, raw_val in row_obj.items():
        key_norm = _sales_import_normalize_key(raw_key)
        if not key_norm:
            continue
        value = str(raw_val or "").strip()
        if key_norm not in normalized or (not normalized.get(key_norm) and value):
            normalized[key_norm] = value
            original_by_norm[key_norm] = str(raw_key or "").strip()

    def pick(*aliases):
        for alias in aliases:
            alias_norm = _sales_import_normalize_key(alias)
            if alias_norm in normalized and str(normalized.get(alias_norm, "")).strip():
                return str(normalized.get(alias_norm, "")).strip()
        return ""

    nome = pick("nome", "nome completo", "primeiro nome", "first name", "name", "lead", "contato", "cliente")
    telefone = pick(
        "telefone",
        "telefone principal",
        "fone",
        "phone",
        "phone number",
        "telefone 1",
        "telefone 2",
        "fone 1",
        "fone 2",
        "numero telefone",
    )
    celular = pick(
        "celular",
        "telefone celular",
        "telefone whatsapp",
        "whatsapp",
        "mobile",
        "cel",
        "celular whatsapp",
        "whats",
        "numero",
    )
    telefone_guess_from_alias = _sales_guess_phone_from_text(telefone)
    if telefone_guess_from_alias:
        telefone = telefone_guess_from_alias
    celular_guess_from_alias = _sales_guess_phone_from_text(celular)
    if celular_guess_from_alias:
        celular = celular_guess_from_alias
    email_val = pick("email", "e-mail", "mail")

    candidates = _sales_extract_text_candidates(normalized)
    if usar_wiz_detect and not email_val:
        for _, candidate_text in candidates:
            guessed_email = _sales_guess_email_from_text(candidate_text)
            if guessed_email:
                email_val = guessed_email
                break

    if usar_wiz_detect and nome:
        if not telefone:
            guessed_from_nome = _sales_guess_phone_from_text(nome)
            if guessed_from_nome:
                telefone = guessed_from_nome
        if not celular:
            guessed_from_nome = _sales_guess_phone_from_text(nome)
            if guessed_from_nome:
                celular = guessed_from_nome
        if not email_val:
            guessed_email_from_nome = _sales_guess_email_from_text(nome)
            if guessed_email_from_nome:
                email_val = guessed_email_from_nome

    if usar_wiz_detect and not telefone:
        # 1) tenta apenas campos de telefone/contato
        preferred_phone_keys = ["telefone", "fone", "celular", "whatsapp", "phone", "mobile", "numero"]
        for key_norm, candidate_text in candidates:
            if not any(k in key_norm for k in preferred_phone_keys):
                continue
            guessed_phone = _sales_guess_phone_from_text(candidate_text)
            if guessed_phone:
                telefone = guessed_phone
                break
        # 2) fallback: varre campos gerais, ignorando campos sabidamente nao-telefone
        if not telefone:
            blocked_for_phone = ["cpf", "cnpj", "rg", "cep", "idade", "nascimento", "matricula"]
            for key_norm, candidate_text in candidates:
                if any(k in key_norm for k in blocked_for_phone):
                    continue
                guessed_phone = _sales_guess_phone_from_text(candidate_text)
                if guessed_phone:
                    telefone = guessed_phone
                    break

    if usar_wiz_detect and not celular:
        preferred_mobile_keys = ["celular", "whatsapp", "mobile", "phone", "telefone", "fone", "numero"]
        for key_norm, candidate_text in candidates:
            if not any(k in key_norm for k in preferred_mobile_keys):
                continue
            guessed_mobile = _sales_guess_phone_from_text(candidate_text)
            if guessed_mobile:
                celular = guessed_mobile
                break

    if usar_wiz_detect and not nome:
        # 1) tenta extrair nome de campos usuais
        preferred_name_keys = ["nome", "name", "lead", "contato", "cliente"]
        for key_norm, candidate_text in candidates:
            if any(k in key_norm for k in preferred_name_keys):
                maybe_name = _sales_guess_name_from_candidates([(key_norm, candidate_text)])
                if maybe_name:
                    nome = maybe_name
                    break
        # 2) fallback geral com heuristica
        if not nome:
            nome = _sales_guess_name_from_candidates(candidates)
        # 3) fallback do e-mail
        if not nome and email_val:
            local = str(email_val).split("@", 1)[0].replace(".", " ").replace("_", " ").replace("-", " ")
            local = " ".join(w for w in local.split() if w)
            if local:
                nome = local.title()
    elif usar_wiz_detect and nome:
        nome_limpo = _sales_guess_name_from_candidates([("nome", nome)])
        if nome_limpo:
            nome = nome_limpo

    if not telefone and celular:
        telefone = celular
    if not celular and telefone:
        celular = telefone

    # Regra solicitada: mesmo incompleto, cadastra com o que tiver.
    if not nome and not telefone and not celular and not email_val:
        return {}, "Linha sem informacao minima para cadastro."
    if not nome and telefone:
        nome = f"Lead {str(telefone)[-4:]}"
    if not nome and celular:
        nome = f"Lead {str(celular)[-4:]}"
    if not nome and email_val:
        nome = "Lead sem nome"

    status = _sales_match_option(pick("status", "situacao"), sales_lead_status_options(), "Novo contato")
    estagio_raw = pick("estagio", "estagio funil", "estagio no funil", "funil", "pipeline", "etapa")
    estagio = _sales_match_option(estagio_raw, sales_pipeline_stage_options(), _sales_stage_from_status(status))

    origem = pick("origem", "source", "canal")
    if not origem:
        origem = str(origem_padrao or "").strip()

    mapped = {
        "nome": nome,
        "telefone": telefone,
        "celular": celular,
        "email": str(email_val or "").lower(),
        "status": status,
        "estagio_funil": estagio,
        "origem": origem,
        "interesse": pick("interesse", "curso", "produto"),
        "cargo": pick("cargo", "profissao", "profissao cargo"),
        "empresa": pick("empresa", "company", "organizacao"),
        "cidade": pick("cidade", "city"),
        "estado": pick("estado", "uf", "state").upper(),
        "tags": _lead_tags_list(pick("tags", "tag", "etiquetas", "labels")),
        "observacao": pick("observacao", "observacoes", "obs", "anotacoes", "comentarios", "descricao"),
        "vendedor": pick("vendedor", "consultor", "responsavel", "owner") or vendedor_atual,
    }

    used_aliases = {
        _sales_import_normalize_key(a)
        for a in [
            "nome", "nome completo", "primeiro nome", "first name", "name", "lead", "contato", "cliente",
            "telefone", "telefone whatsapp", "telefone celular", "telefone principal", "whatsapp", "celular", "fone", "phone", "phone number", "mobile", "numero", "numero telefone",
            "email", "e-mail", "mail", "status", "situacao",
            "estagio", "estagio funil", "estagio no funil", "funil", "pipeline", "etapa",
            "origem", "source", "canal", "interesse", "curso", "produto",
            "cargo", "profissao", "profissao cargo", "empresa", "company", "organizacao",
            "cidade", "city", "estado", "uf", "state",
            "tags", "tag", "etiquetas", "labels",
            "observacao", "observacoes", "obs", "anotacoes", "comentarios", "descricao",
            "vendedor", "consultor", "responsavel", "owner",
        ]
    }
    custom_fields = {}
    for key_norm, val in normalized.items():
        if key_norm in used_aliases:
            continue
        k_raw = original_by_norm.get(key_norm, key_norm).strip()
        v_raw = str(val or "").strip()
        if k_raw and v_raw:
            custom_fields[k_raw] = v_raw
    mapped["campos_personalizados"] = custom_fields
    return mapped, ""

def _sales_import_register_leads(uploaded_file, vendedor_atual, origem_padrao="", atualizar_existentes=True, usar_wiz_detect=True):
    rows, err = _sales_import_parse_rows(uploaded_file)
    if err:
        return False, err, {"total_linhas": 0, "cadastrados": 0, "atualizados": 0, "ignorados": 0}, []

    leads_store = st.session_state.get("sales_leads", [])
    by_phone = {}
    by_email = {}
    by_name = {}
    for lead in leads_store:
        if not isinstance(lead, dict):
            continue
        phone_digits = re.sub(r"\D", "", str(lead.get("telefone", "") or ""))
        cell_digits = re.sub(r"\D", "", str(lead.get("celular", "") or ""))
        email_key = str(lead.get("email", "") or "").strip().lower()
        name_key = normalize_text(lead.get("nome", ""))
        if phone_digits:
            by_phone[phone_digits] = lead
        if cell_digits:
            by_phone[cell_digits] = lead
        if email_key:
            by_email[email_key] = lead
        if name_key:
            by_name[name_key] = lead

    now = datetime.datetime.now().strftime("%d/%m/%Y %H:%M")
    cadastrados = 0
    atualizados = 0
    ignorados = 0
    ignorados_sem_dados = 0
    erros = []

    for idx, row in enumerate(rows, start=1):
        mapped, map_err = _sales_import_map_row(
            row,
            vendedor_atual=vendedor_atual,
            origem_padrao=origem_padrao,
            usar_wiz_detect=usar_wiz_detect,
        )
        if map_err:
            ignorados += 1
            if str(map_err).strip().lower() == "linha sem informacao minima para cadastro.":
                ignorados_sem_dados += 1
            else:
                erros.append({"linha": idx, "erro": map_err})
            continue
        _sales_reconcile_lead_record(mapped)

        phone_digits = re.sub(r"\D", "", str(mapped.get("telefone", "") or ""))
        cell_digits = re.sub(r"\D", "", str(mapped.get("celular", "") or ""))
        if not phone_digits and cell_digits:
            phone_digits = cell_digits
        email_key = str(mapped.get("email", "") or "").strip().lower()
        existing = None
        if phone_digits and phone_digits in by_phone:
            existing = by_phone[phone_digits]
        elif cell_digits and cell_digits in by_phone:
            existing = by_phone[cell_digits]
        elif email_key and email_key in by_email:
            existing = by_email[email_key]
        else:
            name_key = normalize_text(mapped.get("nome", ""))
            if name_key and name_key in by_name:
                existing = by_name[name_key]

        if existing and not atualizar_existentes:
            ignorados += 1
            erros.append({"linha": idx, "erro": "Lead ja existe (telefone/e-mail)."})
            continue

        if existing:
            for field in ["nome", "telefone", "celular", "email", "status", "estagio_funil", "origem", "interesse", "cargo", "empresa", "cidade", "estado", "observacao", "vendedor"]:
                value = str(mapped.get(field, "")).strip()
                if value:
                    existing[field] = value
            if not str(existing.get("celular", "")).strip() and str(existing.get("telefone", "")).strip():
                existing["celular"] = str(existing.get("telefone", "")).strip()
            if not str(existing.get("telefone", "")).strip() and str(existing.get("celular", "")).strip():
                existing["telefone"] = str(existing.get("celular", "")).strip()
            existing_tags = _lead_tags_list(existing.get("tags", []))
            existing["tags"] = _lead_tags_list(existing_tags + _lead_tags_list(mapped.get("tags", [])))
            custom_existing = existing.get("campos_personalizados", {}) if isinstance(existing.get("campos_personalizados"), dict) else {}
            custom_new = mapped.get("campos_personalizados", {}) if isinstance(mapped.get("campos_personalizados"), dict) else {}
            custom_existing.update(custom_new)
            existing["campos_personalizados"] = custom_existing
            _sales_reconcile_lead_record(existing)
            existing.setdefault("interacoes", []).append(
                {
                    "data_hora": now,
                    "canal": "Importacao",
                    "acao": "Lead atualizado por importacao",
                    "descricao": "Atualizacao automatica via arquivo de leads.",
                    "pagina": "",
                }
            )
            existing["updated_at"] = now
            existing_phone_digits = re.sub(r"\D", "", str(existing.get("telefone", "") or ""))
            existing_cell_digits = re.sub(r"\D", "", str(existing.get("celular", "") or ""))
            if existing_phone_digits:
                by_phone[existing_phone_digits] = existing
            if existing_cell_digits:
                by_phone[existing_cell_digits] = existing
            atualizados += 1
            continue

        novo = {
            "id": uuid.uuid4().hex,
            "nome": str(mapped.get("nome", "")).strip(),
            "telefone": str(mapped.get("telefone", "")).strip(),
            "celular": str(mapped.get("celular", "")).strip() or str(mapped.get("telefone", "")).strip(),
            "email": str(mapped.get("email", "")).strip().lower(),
            "status": str(mapped.get("status", "Novo contato")).strip() or "Novo contato",
            "estagio_funil": str(mapped.get("estagio_funil", "Qualificacao")).strip() or "Qualificacao",
            "origem": str(mapped.get("origem", "")).strip(),
            "interesse": str(mapped.get("interesse", "")).strip(),
            "cargo": str(mapped.get("cargo", "")).strip(),
            "empresa": str(mapped.get("empresa", "")).strip(),
            "cidade": str(mapped.get("cidade", "")).strip(),
            "estado": str(mapped.get("estado", "")).strip(),
            "tags": _lead_tags_list(mapped.get("tags", [])),
            "campos_personalizados": mapped.get("campos_personalizados", {}) if isinstance(mapped.get("campos_personalizados"), dict) else {},
            "observacao": str(mapped.get("observacao", "")).strip(),
            "vendedor": str(mapped.get("vendedor", "")).strip() or vendedor_atual,
            "created_at": now,
            "updated_at": "",
            "ultimo_contato": "",
            "interacoes": [
                {
                    "data_hora": now,
                    "canal": "Importacao",
                    "acao": "Lead importado",
                    "descricao": "Cadastro automatizado via arquivo de leads.",
                    "pagina": "",
                }
            ],
            "landing_pages": [],
            "conversoes": [],
        }
        _sales_reconcile_lead_record(novo)
        leads_store.append(novo)
        if phone_digits:
            by_phone[phone_digits] = novo
        new_cell_digits = re.sub(r"\D", "", str(novo.get("celular", "") or ""))
        if new_cell_digits:
            by_phone[new_cell_digits] = novo
        if email_key:
            by_email[email_key] = novo
        name_key = normalize_text(novo.get("nome", ""))
        if name_key:
            by_name[name_key] = novo
        cadastrados += 1

    if cadastrados > 0 or atualizados > 0:
        save_list(SALES_LEADS_FILE, st.session_state["sales_leads"])

    stats = {
        "total_linhas": len(rows),
        "cadastrados": cadastrados,
        "atualizados": atualizados,
        "ignorados": ignorados,
        "linhas_sem_dados": ignorados_sem_dados,
    }
    return True, "Importacao concluida.", stats, erros

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
        if _sales_reconcile_lead_record(lead):
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
        if "estagio_funil" not in lead or not str(lead.get("estagio_funil", "")).strip():
            status_atual = str(lead.get("status", "")).strip()
            if status_atual == "Fechado":
                lead["estagio_funil"] = "Fechamento"
            elif status_atual == "Desistir":
                lead["estagio_funil"] = "Descartado"
            elif status_atual == "Leads quentes":
                lead["estagio_funil"] = "Negociacao"
            elif status_atual == "Leads frios":
                lead["estagio_funil"] = "Contato inicial"
            else:
                lead["estagio_funil"] = "Qualificacao"
            leads_changed = True
        if "cargo" not in lead:
            lead["cargo"] = ""
            leads_changed = True
        if "cidade" not in lead:
            lead["cidade"] = ""
            leads_changed = True
        if "estado" not in lead:
            lead["estado"] = ""
            leads_changed = True
        if "empresa" not in lead:
            lead["empresa"] = ""
            leads_changed = True
        if "celular" not in lead:
            lead["celular"] = str(lead.get("telefone", "")).strip()
            leads_changed = True
        elif not str(lead.get("celular", "")).strip() and str(lead.get("telefone", "")).strip():
            lead["celular"] = str(lead.get("telefone", "")).strip()
            leads_changed = True
        elif not str(lead.get("telefone", "")).strip() and str(lead.get("celular", "")).strip():
            lead["telefone"] = str(lead.get("celular", "")).strip()
            leads_changed = True
        if "tags" not in lead:
            lead["tags"] = []
            leads_changed = True
        else:
            tags_norm = _lead_tags_list(lead.get("tags", []))
            if tags_norm != lead.get("tags", []):
                lead["tags"] = tags_norm
                leads_changed = True
        if "campos_personalizados" not in lead or not isinstance(lead.get("campos_personalizados"), dict):
            lead["campos_personalizados"] = {}
            leads_changed = True
        if "interacoes" not in lead or not isinstance(lead.get("interacoes"), list):
            lead["interacoes"] = []
            leads_changed = True
        if "landing_pages" not in lead or not isinstance(lead.get("landing_pages"), list):
            lead["landing_pages"] = []
            leads_changed = True
        if "conversoes" not in lead or not isinstance(lead.get("conversoes"), list):
            lead["conversoes"] = []
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
    meeting_link = str(schedule_obj.get("meeting_link", "")).strip()
    google_link = str(schedule_obj.get("google_calendar_link", "")).strip() or build_sales_google_calendar_event_link(schedule_obj)
    mensagem = (
        f"Ola, {nome}.\n"
        f"Seu agendamento foi registrado no Active.\n"
        f"Tipo: {tipo}\n"
        f"Data: {data}\n"
        f"Horario: {hora or '-'}\n"
    )
    if detalhes:
        mensagem += f"Detalhes: {detalhes}\n"
    if meeting_link:
        mensagem += f"Link da reuniao: {meeting_link}\n"
    if google_link:
        mensagem += f"Google Agenda: {google_link}\n"
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

def generate_weekly_challenge_ai(level, week_key, reference_title="", reference_text="", challenge_theme="Livro / Conteudo atual"):
    level = _norm_book_level(level)
    week_key = str(week_key or "").strip()
    reference_title = str(reference_title or "").strip()
    reference_text = str(reference_text or "").strip()
    challenge_theme = str(challenge_theme or "Livro / Conteudo atual").strip()
    messages = [
        {
            "role": "system",
            "content": (
                "Voce e o Professor Wiz (IA) e cria desafios semanais educacionais da Mister Wiz.\n"
                "Gere UM desafio adequado ao nivel do aluno e que possa ser respondido no portal.\n"
                "Use a referencia pedagogica enviada como base obrigatoria do desafio.\n"
                "Responda SOMENTE em JSON valido, sem markdown."
            ),
        },
        {
            "role": "user",
            "content": (
                f"Nivel: {level}\n"
                f"Semana: {week_key}\n"
                f"Linha do desafio: {challenge_theme}\n"
                f"Livro/Nivel de referencia: {reference_title or level or '-'}\n\n"
                f"Referencia pedagogica para gerar o desafio:\n{reference_text or 'Sem referencia adicional informada.'}\n\n"
                "Crie um desafio de 10 a 20 minutos com foco na referencia acima.\n"
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

def library_book_templates():
    templates = []
    for livro in range(1, 6):
        for parte in (1, 2):
            templates.append(
                {
                    "book_id": f"ingles_livro_{livro}_parte_{parte}",
                    "nivel": f"Livro {livro}",
                    "titulo": f"Ingles - Livro {livro} - Parte {parte}",
                    "categoria": "Ingles",
                    "parte": f"Parte {parte}",
                    "url": "",
                    "file_path": "",
                    "file_b64": "",
                    "file_name": "",
                }
            )
    templates.extend(
        [
            {
                "book_id": "lideranca",
                "nivel": "",
                "titulo": "Lideranca",
                "categoria": "Lideranca",
                "parte": "Parte unica",
                "url": "",
                "file_path": "",
                "file_b64": "",
                "file_name": "",
            },
            {
                "book_id": "empreendedorismo",
                "nivel": "",
                "titulo": "Empreendedorismo",
                "categoria": "Empreendedorismo",
                "parte": "Parte unica",
                "url": "",
                "file_path": "",
                "file_b64": "",
                "file_name": "",
            },
            {
                "book_id": "educacao_financeira",
                "nivel": "",
                "titulo": "Educacao Financeira",
                "categoria": "Educacao Financeira",
                "parte": "Parte unica",
                "url": "",
                "file_path": "",
                "file_b64": "",
                "file_name": "",
            },
            {
                "book_id": "inteligencia_emocional",
                "nivel": "",
                "titulo": "Inteligencia Emocional",
                "categoria": "Inteligencia Emocional",
                "parte": "Parte unica",
                "url": "",
                "file_path": "",
                "file_b64": "",
                "file_name": "",
            },
            {
                "book_id": "empreendedorismo_business_adults_1",
                "nivel": "",
                "titulo": "Mister Wiz livro Business Adults",
                "categoria": "Empreendedorismo",
                "parte": "Business Adults",
                "url": "",
                "file_path": "",
                "file_b64": "",
                "file_name": "",
            },
            {
                "book_id": "empreendedorismo_business_adults_2",
                "nivel": "",
                "titulo": "Mister Wiz livro Business Adults 2",
                "categoria": "Empreendedorismo",
                "parte": "Business Adults 2",
                "url": "",
                "file_path": "",
                "file_b64": "",
                "file_name": "",
            },
            {
                "book_id": "empreendedorismo_business_adults_3",
                "nivel": "",
                "titulo": "Mister Wiz livro Business Adults 3",
                "categoria": "Empreendedorismo",
                "parte": "Business Adults 3",
                "url": "",
                "file_path": "",
                "file_b64": "",
                "file_name": "",
            },
            {
                "book_id": "empreendedorismo_empreendedoresmo_1",
                "nivel": "",
                "titulo": "Mister Wiz livro empreendedoresmo 1",
                "categoria": "Empreendedorismo",
                "parte": "Empreendedoresmo 1",
                "url": "",
                "file_path": "",
                "file_b64": "",
                "file_name": "",
            },
            {
                "book_id": "empreendedorismo_empreendedoresmo_2",
                "nivel": "",
                "titulo": "Mister Wiz livro empreendedoresmo 2",
                "categoria": "Empreendedorismo",
                "parte": "Empreendedoresmo 2",
                "url": "",
                "file_path": "",
                "file_b64": "",
                "file_name": "",
            },
            {
                "book_id": "empreendedorismo_jovens_1_1",
                "nivel": "",
                "titulo": "Mister Wiz livro jovens empreendedor 1.1",
                "categoria": "Empreendedorismo",
                "parte": "Jovens Empreendedor 1.1",
                "url": "",
                "file_path": "",
                "file_b64": "",
                "file_name": "",
            },
            {
                "book_id": "empreendedorismo_jovens_1",
                "nivel": "",
                "titulo": "Mister Wiz livro jovens empreendedor 1",
                "categoria": "Empreendedorismo",
                "parte": "Jovens Empreendedor 1",
                "url": "",
                "file_path": "",
                "file_b64": "",
                "file_name": "",
            },
            {
                "book_id": "empreendedorismo_jovens_2",
                "nivel": "",
                "titulo": "Mister Wiz livro jovens empreendedor 2",
                "categoria": "Empreendedorismo",
                "parte": "Jovens Empreendedor 2",
                "url": "",
                "file_path": "",
                "file_b64": "",
                "file_name": "",
            },
            {
                "book_id": "empreendedorismo_jovens_3",
                "nivel": "",
                "titulo": "Mister Wiz livro jovens empreendedor 3",
                "categoria": "Empreendedorismo",
                "parte": "Jovens Empreendedor 3",
                "url": "",
                "file_path": "",
                "file_b64": "",
                "file_name": "",
            },
            {
                "book_id": "empreendedorismo_jovens_4",
                "nivel": "",
                "titulo": "Mister Wiz livro jovens empreendedor 4",
                "categoria": "Empreendedorismo",
                "parte": "Jovens Empreendedor 4",
                "url": "",
                "file_path": "",
                "file_b64": "",
                "file_name": "",
            },
            {
                "book_id": "inteligencia_emocional_livro_1",
                "nivel": "",
                "titulo": "Mister Wiz livro inteligencia emocional 1",
                "categoria": "Inteligencia Emocional",
                "parte": "Livro 1",
                "url": "",
                "file_path": "",
                "file_b64": "",
                "file_name": "",
            },
            {
                "book_id": "inteligencia_emocional_livro_2",
                "nivel": "",
                "titulo": "Mister Wiz livro inteligencia emocional 2",
                "categoria": "Inteligencia Emocional",
                "parte": "Livro 2",
                "url": "",
                "file_path": "",
                "file_b64": "",
                "file_name": "",
            },
            {
                "book_id": "inteligencia_emocional_livro_2_2",
                "nivel": "",
                "titulo": "Mister Wiz livro inteligencia emocional 2.2",
                "categoria": "Inteligencia Emocional",
                "parte": "Livro 2.2",
                "url": "",
                "file_path": "",
                "file_b64": "",
                "file_name": "",
            },
            {
                "book_id": "inteligencia_emocional_livro_3",
                "nivel": "",
                "titulo": "Mister Wiz inteligencia emocional livro 3",
                "categoria": "Inteligencia Emocional",
                "parte": "Livro 3",
                "url": "",
                "file_path": "",
                "file_b64": "",
                "file_name": "",
            },
            {
                "book_id": "inteligencia_emocional_livro_3_3",
                "nivel": "",
                "titulo": "Mister Wiz inteligencia emocional livro 3.3",
                "categoria": "Inteligencia Emocional",
                "parte": "Livro 3.3",
                "url": "",
                "file_path": "",
                "file_b64": "",
                "file_name": "",
            },
            {
                "book_id": "inteligencia_emocional_livro_4",
                "nivel": "",
                "titulo": "Mister Wiz inteligencia emocional livro 4",
                "categoria": "Inteligencia Emocional",
                "parte": "Livro 4",
                "url": "",
                "file_path": "",
                "file_b64": "",
                "file_name": "",
            },
            {
                "book_id": "inteligencia_emocional_base",
                "nivel": "",
                "titulo": "Mister Wiz livro inteligencia emocional",
                "categoria": "Inteligencia Emocional",
                "parte": "Base",
                "url": "",
                "file_path": "",
                "file_b64": "",
                "file_name": "",
            },
            {
                "book_id": "inteligencia_emocional_express_adults",
                "nivel": "",
                "titulo": "Mister Wiz livro express adults",
                "categoria": "Inteligencia Emocional",
                "parte": "Express Adults",
                "url": "",
                "file_path": "",
                "file_b64": "",
                "file_name": "",
            },
            {
                "book_id": "inteligencia_emocional_express_teens",
                "nivel": "",
                "titulo": "Mister Wiz livro express teens",
                "categoria": "Inteligencia Emocional",
                "parte": "Express Teens",
                "url": "",
                "file_path": "",
                "file_b64": "",
                "file_name": "",
            },
            {
                "book_id": "inteligencia_emocional_express_teens_3",
                "nivel": "",
                "titulo": "Mister Wiz livro express teens 3",
                "categoria": "Inteligencia Emocional",
                "parte": "Express Teens 3",
                "url": "",
                "file_path": "",
                "file_b64": "",
                "file_name": "",
            },
        ]
    )
    return templates

def _normalize_legacy_book_label(value):
    txt = str(value or "").strip()
    if not txt:
        return ""
    txt = re.sub(r"(?i)\blivro\s*4[.,]5\b", "Livro 5", txt)
    return txt

def _extract_livro_num(text):
    norm = normalize_text(text)
    if "livro 4.5" in norm or "livro4.5" in norm or "livro 4,5" in norm or "livro4,5" in norm:
        return 5
    for i in range(1, 6):
        if f"livro {i}" in norm or f"livro{i}" in norm:
            return i
    return None

def _extract_parte_num(text):
    norm = normalize_text(text)
    if "parte 2" in norm or "parte2" in norm:
        return 2
    if "parte 1" in norm or "parte1" in norm:
        return 1
    return None

def infer_library_book_id(book_obj):
    if not isinstance(book_obj, dict):
        return ""
    explicit = str(book_obj.get("book_id", "")).strip()
    if explicit:
        return explicit

    titulo = str(book_obj.get("titulo", "")).strip()
    nivel = str(book_obj.get("nivel", "")).strip()
    categoria = str(book_obj.get("categoria", "")).strip()
    parte = str(book_obj.get("parte", "")).strip()

    livro_num = _extract_livro_num(titulo) or _extract_livro_num(nivel)
    if livro_num:
        parte_num = _extract_parte_num(titulo) or _extract_parte_num(parte) or 1
        return f"ingles_livro_{livro_num}_parte_{parte_num}"

    norm_candidates = [
        normalize_text(categoria),
        normalize_text(titulo),
        normalize_text(nivel),
    ]
    joined = " | ".join([c for c in norm_candidates if c])
    detailed_mapping = [
        ("business adults 3", "empreendedorismo_business_adults_3"),
        ("business adults 2", "empreendedorismo_business_adults_2"),
        ("business adults", "empreendedorismo_business_adults_1"),
        ("empreendedoresmo 2", "empreendedorismo_empreendedoresmo_2"),
        ("empreendedorismo 2", "empreendedorismo_empreendedoresmo_2"),
        ("empreendedoresmo 1", "empreendedorismo_empreendedoresmo_1"),
        ("empreendedorismo 1", "empreendedorismo_empreendedoresmo_1"),
        ("jovens empreendedor 4", "empreendedorismo_jovens_4"),
        ("jovens empreendedor 3", "empreendedorismo_jovens_3"),
        ("jovens empreendedor 2", "empreendedorismo_jovens_2"),
        ("jovens empreendedor 1.1", "empreendedorismo_jovens_1_1"),
        ("jovens empreendedor 1...", "empreendedorismo_jovens_1_1"),
        ("jovens empreendedor 1", "empreendedorismo_jovens_1"),
        ("inteligencia emocional livro 3.3", "inteligencia_emocional_livro_3_3"),
        ("inteligencia emocional livro 2.2", "inteligencia_emocional_livro_2_2"),
        ("inteligencia emocional livro 4", "inteligencia_emocional_livro_4"),
        ("inteligencia emocional livro 3", "inteligencia_emocional_livro_3"),
        ("inteligencia emocional livro 2", "inteligencia_emocional_livro_2"),
        ("inteligencia emocional livro 1", "inteligencia_emocional_livro_1"),
        ("express teens 3", "inteligencia_emocional_express_teens_3"),
        ("express teens", "inteligencia_emocional_express_teens"),
        ("express adults", "inteligencia_emocional_express_adults"),
        ("livro inteligencia emocional", "inteligencia_emocional_base"),
    ]
    for key, val in detailed_mapping:
        if key in joined:
            return val

    mapping = {
        "lideranca": "lideranca",
        "empreendedorismo": "empreendedorismo",
        "educacao financeira": "educacao_financeira",
        "inteligencia emocional": "inteligencia_emocional",
    }
    for cand in norm_candidates:
        for key, val in mapping.items():
            if key in cand:
                return val
    return ""

def ensure_library_catalog(books):
    books = books if isinstance(books, list) else []
    templates = library_book_templates()
    template_ids = {t.get("book_id", "") for t in templates}
    mapped_existing = {}
    extras = []

    for raw in books:
        if not isinstance(raw, dict):
            continue
        obj = dict(raw)
        obj["titulo"] = _normalize_legacy_book_label(obj.get("titulo", ""))
        obj["nivel"] = _normalize_legacy_book_label(obj.get("nivel", ""))
        bid = infer_library_book_id(obj)
        if bid and bid in template_ids and bid not in mapped_existing:
            obj["book_id"] = bid
            mapped_existing[bid] = obj
        else:
            extras.append(obj)

    merged = []
    for tpl in templates:
        bid = str(tpl.get("book_id", "")).strip()
        old = mapped_existing.get(bid, {})
        merged.append(
            {
                "book_id": bid,
                "nivel": str(old.get("nivel", tpl.get("nivel", ""))).strip(),
                "titulo": str(old.get("titulo", tpl.get("titulo", ""))).strip() or str(tpl.get("titulo", "")),
                "categoria": str(old.get("categoria", tpl.get("categoria", ""))).strip() or str(tpl.get("categoria", "")),
                "parte": str(old.get("parte", tpl.get("parte", ""))).strip() or str(tpl.get("parte", "")),
                "url": str(old.get("url", "")).strip(),
                "file_path": str(old.get("file_path", "")).strip(),
                "file_b64": str(old.get("file_b64", "")).strip(),
                "file_name": str(old.get("file_name", "")).strip(),
            }
        )

    for extra in extras:
        if not isinstance(extra, dict):
            continue
        bid = infer_library_book_id(extra)
        if bid and bid in template_ids:
            continue
        merged.append(
            {
                "book_id": str(extra.get("book_id", "")).strip(),
                "nivel": str(extra.get("nivel", "")).strip(),
                "titulo": str(extra.get("titulo", "")).strip() or "Livro",
                "categoria": str(extra.get("categoria", "")).strip(),
                "parte": str(extra.get("parte", "")).strip(),
                "url": str(extra.get("url", "")).strip(),
                "file_path": str(extra.get("file_path", "")).strip(),
                "file_b64": str(extra.get("file_b64", "")).strip(),
                "file_name": str(extra.get("file_name", "")).strip(),
            }
        )
    return merged

def _book_binary_payload(book_obj):
    if not isinstance(book_obj, dict):
        return b"", ""
    file_b64 = str(book_obj.get("file_b64", "")).strip()
    file_name = str(book_obj.get("file_name", "")).strip()
    if file_b64:
        try:
            data = base64.b64decode(file_b64.encode("ascii"), validate=False)
            if data:
                return data, file_name or "livro.pdf"
        except Exception:
            pass
    file_path = str(book_obj.get("file_path", "")).strip()
    if file_path and Path(file_path).exists():
        try:
            return Path(file_path).read_bytes(), Path(file_path).name
        except Exception:
            return b"", ""
    return b"", ""

def _normalize_book_url(url):
    raw = str(url or "").strip()
    if not raw:
        return ""
    low = raw.lower()
    if low.startswith(("http://", "https://")):
        return raw
    if low.startswith("www."):
        return f"https://{raw}"
    return ""

def render_books_section(books, title="Livros Didáticos", key_prefix="books", allow_download=True):
    st.markdown(f"### {title}")
    if not books:
        st.info("Nenhum livro disponível.")
        return
    for idx, b in enumerate(books):
        titulo = b.get("titulo") or b.get("nivel") or "Livro"
        st.markdown(f"**{titulo}**")
        categoria = str(b.get("categoria", "")).strip()
        parte = str(b.get("parte", "")).strip()
        details = [d for d in [categoria, parte] if d]
        if details:
            st.caption(" | ".join(details))
        c1, c2 = st.columns(2)
        file_data, file_name = _book_binary_payload(b)
        raw_url = str(b.get("url", "")).strip()
        url = _normalize_book_url(raw_url)
        invalid_url = bool(raw_url and not url)
        if allow_download:
            if file_data:
                c1.download_button("Baixar livro", data=file_data, file_name=file_name or "livro.pdf", key=f"{key_prefix}_download_{idx}")
            elif url:
                c1.link_button("Baixar livro", url)
            else:
                c1.button("Baixar livro", disabled=True, key=f"{key_prefix}_disabled_{idx}")
        else:
            c1.button("Baixar livro", disabled=True, key=f"{key_prefix}_download_blocked_{idx}")

        if url:
            c2.link_button("Abrir livro", url)
        else:
            c2.button("Abrir livro", disabled=True, key=f"{key_prefix}_open_disabled_{idx}")
        if invalid_url:
            st.warning("Link do livro inválido. Use um link completo com http:// ou https://.")
        if not url and not file_data:
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

def add_receivable(
    aluno,
    descricao,
    valor,
    vencimento,
    cobranca,
    categoria,
    data_lancamento=None,
    valor_parcela=None,
    parcela=None,
    numero_pedido="",
    item_codigo="",
    categoria_lancamento="Aluno",
    lote_id=None,
):
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
        "lote_id": str(lote_id).strip() if str(lote_id or "").strip() else f"REC-LOT-{uuid.uuid4().hex[:10].upper()}",
        "vencimento": vencimento.strftime("%d/%m/%Y"),
        "status": "Aberto",
        "boleto_url": "",
        "boleto_linha_digitavel": "",
        "boleto_status": "Nao Gerado",
        "boleto_gerado_em": "",
        "boleto_enviado_em": "",
        "boleto_enviado_canais": "",
    })
    save_list(RECEIVABLES_FILE, st.session_state["receivables"])
    return codigo

def _current_month_bounds(base_date=None):
    ref = base_date if isinstance(base_date, datetime.date) else datetime.date.today()
    month_start = ref.replace(day=1)
    month_end = add_months(month_start, 1) - datetime.timedelta(days=1)
    return month_start, month_end

def _financial_open_status(item_obj):
    status = normalize_text((item_obj or {}).get("status", "Aberto"))
    return status not in ("pago", "cancelado")

def _financial_due_total_for_month(items, date_field="vencimento", ref_date=None):
    month_start, month_end = _current_month_bounds(ref_date)
    total = 0.0
    for item in items or []:
        if not _financial_open_status(item):
            continue
        due_date = parse_date((item or {}).get(date_field, ""))
        if not due_date or due_date < month_start or due_date > month_end:
            continue
        total += parse_money((item or {}).get("valor_parcela", (item or {}).get("valor", 0)))
    return total


def _financial_is_overdue(item_obj, date_field="vencimento", ref_date=None):
    if not _financial_open_status(item_obj):
        return False
    today_ref = ref_date if isinstance(ref_date, datetime.date) else datetime.date.today()
    due_date = parse_date((item_obj or {}).get(date_field, ""))
    return bool(due_date and due_date < today_ref)


def _financial_overdue_items(items, date_field="vencimento", ref_date=None):
    return [item for item in (items or []) if _financial_is_overdue(item, date_field=date_field, ref_date=ref_date)]


def _financial_overdue_total(items, date_field="vencimento", ref_date=None):
    return sum(
        parse_money((item or {}).get("valor_parcela", (item or {}).get("valor", 0)))
        for item in _financial_overdue_items(items, date_field=date_field, ref_date=ref_date)
    )

def _teacher_payment_ref_for_session(session_obj):
    sess = session_obj if isinstance(session_obj, dict) else {}
    sess_id = str(sess.get("id", "")).strip()
    if sess_id:
        return f"CLS-{sess_id}"
    parts = [
        str(sess.get("turma", "")).strip(),
        str(sess.get("professor", "")).strip(),
        str(sess.get("data", "")).strip(),
        str(sess.get("hora_inicio_real", sess.get("hora_inicio_prevista", ""))).strip(),
        str(sess.get("titulo", "")).strip(),
        str(sess.get("licao", "")).strip(),
    ]
    return "CLS-" + re.sub(r"[^A-Z0-9]+", "-", normalize_text("|".join(parts)).upper()).strip("-")

def _class_session_effective_date(session_obj):
    sess = session_obj if isinstance(session_obj, dict) else {}
    for field in ("data", "fim_em", "inicio_em"):
        raw = str(sess.get(field, "")).strip()
        if not raw:
            continue
        parsed = parse_date(raw)
        if parsed:
            return parsed
        if " " in raw:
            parsed = parse_date(raw.split(" ", 1)[0].strip())
            if parsed:
                return parsed
    return None

def _class_session_is_finalized(session_obj):
    sess = session_obj if isinstance(session_obj, dict) else {}
    status_norm = normalize_text(sess.get("status", ""))
    if status_norm in ("finalizada", "finalizado", "concluida", "concluido", "encerrada", "encerrado", "fechada", "fechado"):
        return True
    if str(sess.get("hora_fim_real", "")).strip():
        return True
    if str(sess.get("fim_em", "")).strip():
        return True
    return False

def _session_duration_minutes_from_times(session_obj, turma_obj=None):
    sess = session_obj if isinstance(session_obj, dict) else {}
    turma = turma_obj if isinstance(turma_obj, dict) else {}
    hora_inicio = (
        str(sess.get("hora_inicio_real", "")).strip()
        or str(sess.get("hora_inicio_prevista", "")).strip()
        or str(turma.get("hora_inicio", "")).strip()
    )
    hora_fim = (
        str(sess.get("hora_fim_real", "")).strip()
        or str(sess.get("hora_fim_prevista", "")).strip()
        or str(turma.get("hora_fim", "")).strip()
    )
    inicio_time = parse_time(hora_inicio)
    fim_time = parse_time(hora_fim)
    if not inicio_time or not fim_time:
        return 0
    inicio_dt = datetime.datetime.combine(datetime.date.today(), inicio_time)
    fim_dt = datetime.datetime.combine(datetime.date.today(), fim_time)
    if fim_dt <= inicio_dt:
        return 0
    return int((fim_dt - inicio_dt).total_seconds() // 60)

def _teacher_payment_minutes_for_module(module_label, session_obj=None, turma_obj=None):
    modulo_norm = normalize_text(module_label)
    if "intensivo" in modulo_norm and "vip" in modulo_norm:
        return 30
    if "vip" in modulo_norm and "intensivo" not in modulo_norm:
        return 60
    if "presencial em turma" in modulo_norm or ("presencial" in modulo_norm and "turma" in modulo_norm):
        return 120
    if "turma online" in modulo_norm or ("online" in modulo_norm and "turma" in modulo_norm):
        return 120
    if "grupo" in modulo_norm:
        return 120
    if "kids" in modulo_norm and "completo" in modulo_norm:
        return 120
    if "terceira idade" in modulo_norm:
        return 120
    minutes_by_time = _session_duration_minutes_from_times(session_obj, turma_obj)
    if minutes_by_time > 0:
        return minutes_by_time
    return 60

def _teacher_payment_value_for_minutes(minutes):
    if minutes <= 30:
        return 25.0
    if minutes <= 60:
        return 50.0
    return 100.0

def _teacher_payment_info_for_session(session_obj):
    sess = session_obj if isinstance(session_obj, dict) else {}
    turma_nome = str(sess.get("turma", "")).strip()
    turma_obj = next(
        (c for c in st.session_state.get("classes", []) if str(c.get("nome", "")).strip() == turma_nome),
        {},
    )
    sess_date = _class_session_effective_date(sess)
    modulo_label = str(turma_obj.get("modulo", "")).strip() or str(sess.get("modulo", "")).strip()
    professor_label = str(sess.get("professor", "")).strip() or str(turma_obj.get("professor", "")).strip()
    minutos = _teacher_payment_minutes_for_module(modulo_label, sess, turma_obj)
    valor = _teacher_payment_value_for_minutes(minutos)
    return {
        "ref": _teacher_payment_ref_for_session(sess),
        "professor": professor_label,
        "turma": turma_nome,
        "modulo": modulo_label,
        "data": sess_date.strftime("%d/%m/%Y") if sess_date else str(sess.get("data", "")).strip(),
        "hora": str(sess.get("hora_inicio_real", sess.get("hora_inicio_prevista", ""))).strip(),
        "minutos": int(minutos),
        "valor": float(valor),
        "descricao": f"Pagamento aula {turma_nome} - {(sess_date.strftime('%d/%m/%Y') if sess_date else str(sess.get('data', '')).strip())}",
        "session_id": str(sess.get("id", "")).strip(),
    }

def _teacher_payment_already_launched(session_obj):
    ref = _teacher_payment_ref_for_session(session_obj)
    for payable in st.session_state.get("payables", []):
        if str(payable.get("class_session_ref", "")).strip() == ref:
            return True
    return False

def _teacher_payment_candidates(month_ref=None, professor_name="Todos", turma_name="Todas"):
    month_start, month_end = _current_month_bounds(month_ref)
    prof_target = str(professor_name or "Todos").strip() or "Todos"
    turma_target = str(turma_name or "Todas").strip() or "Todas"
    prof_target_norm = normalize_text(prof_target)
    turma_target_norm = normalize_text(turma_target)
    out = []
    for sess in st.session_state.get("class_sessions", []):
        if not _class_session_is_finalized(sess):
            continue
        turma_nome = str(sess.get("turma", "")).strip()
        turma_obj = next(
            (c for c in st.session_state.get("classes", []) if normalize_text(c.get("nome", "")) == normalize_text(turma_nome)),
            {},
        )
        sess_date = _class_session_effective_date(sess)
        if not sess_date or sess_date < month_start or sess_date > month_end:
            continue
        professor_session = str(sess.get("professor", "")).strip()
        professor_turma = str(turma_obj.get("professor", "")).strip()
        if prof_target != "Todos":
            if normalize_text(professor_session) != prof_target_norm and normalize_text(professor_turma) != prof_target_norm:
                continue
        if turma_target != "Todas" and normalize_text(turma_nome) != turma_target_norm:
            continue
        if _teacher_payment_already_launched(sess):
            continue
        out.append(_teacher_payment_info_for_session(sess))
    out.sort(key=lambda item: (parse_date(item.get("data", "")) or month_start, item.get("professor", ""), item.get("turma", "")))
    return out

def allowed_portals(profile):
    if profile == "Aluno": return ["Aluno"]
    if profile == "Professor": return ["Professor"]
    if profile == "Comercial": return ["Comercial"]
    if profile == "Coordenador": return ["Aluno", "Professor", "Comercial", "Coordenador"]
    if profile == "Admin": return ["Aluno", "Professor", "Comercial", "Coordenador"]
    return []

def _send_email_smtp(to_email, subject, body):
    host = _finance_config_value("ACTIVE_SMTP_HOST", "smtp_host", "").strip()
    if not host:
        return False, "SMTP nao configurado"
    try:
        port = int(_finance_config_value("ACTIVE_SMTP_PORT", "smtp_port", "587"))
    except Exception:
        port = 587
    user = _finance_config_value("ACTIVE_SMTP_USER", "smtp_user", "").strip()
    password = _finance_config_value("ACTIVE_SMTP_PASS", "smtp_pass", "").strip()
    use_tls = _finance_config_value("ACTIVE_SMTP_TLS", "smtp_tls", "1").strip().lower() not in ("0", "false", "no")
    sender = _finance_config_value("ACTIVE_EMAIL_FROM", "smtp_from", user or "noreply@active.local").strip()
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

def _existing_class_name_set():
    out = set()
    for turma_obj in st.session_state.get("classes", []):
        nome = str(turma_obj.get("nome", "")).strip()
        if nome:
            out.add(nome)
    return out

def _student_has_existing_class(student, existing_classes=None):
    turma_nome = str((student or {}).get("turma", "")).strip()
    if not turma_nome:
        return False
    if turma_nome.strip().lower() in ("sem turma", "todos", "todas"):
        return False
    if existing_classes is None:
        existing_classes = _existing_class_name_set()
    return turma_nome in existing_classes

def notify_students_by_turma_channels(
    turma,
    assunto,
    corpo,
    origem,
    send_email=True,
    send_whatsapp=True,
    only_existing_classes=False,
    include_students_without_turma_when_all=True,
):
    stats = {
        "email_total": 0,
        "email_ok": 0,
        "whatsapp_total": 0,
        "whatsapp_ok": 0,
        "student_total": 0,
        "student_with_channel": 0,
        "student_contacted": 0,
    }
    turma_target = str(turma or "Todas").strip() or "Todas"
    existing_classes = _existing_class_name_set() if bool(only_existing_classes) else None
    for student in st.session_state.get("students", []):
        student_turma = str(student.get("turma", "")).strip()
        if turma_target != "Todas" and student_turma != turma_target:
            continue
        if bool(only_existing_classes) and not _student_has_existing_class(student, existing_classes):
            continue
        if turma_target == "Todas" and not bool(include_students_without_turma_when_all):
            if not student_turma or student_turma.lower() in ("sem turma", "todos", "todas"):
                continue
        partial = _notify_direct_contacts(
            student.get("nome", "Aluno"),
            _message_recipients_for_student(student) if bool(send_email) else [],
            _student_whatsapp_recipients(student) if bool(send_whatsapp) else [],
            assunto,
            corpo,
            origem,
        )
        stats["student_total"] += 1
        if int(partial.get("email_total", 0)) + int(partial.get("whatsapp_total", 0)) > 0:
            stats["student_with_channel"] += 1
        if int(partial.get("email_ok", 0)) + int(partial.get("whatsapp_ok", 0)) > 0:
            stats["student_contacted"] += 1
        for key in stats:
            stats[key] += int(partial.get(key, 0))
    return stats

def notify_teachers_channels(assunto, corpo, origem, professor="Todos", send_email=True, send_whatsapp=True):
    teacher_target = str(professor or "Todos").strip() or "Todos"
    stats = {"email_total": 0, "email_ok": 0, "whatsapp_total": 0, "whatsapp_ok": 0}
    for teacher in st.session_state.get("teachers", []):
        if teacher_target != "Todos" and str(teacher.get("nome", "")).strip() != teacher_target:
            continue
        partial = _notify_direct_contacts(
            teacher.get("nome", "Professor"),
            [teacher.get("email", "")] if bool(send_email) else [],
            [teacher.get("celular", "")] if bool(send_whatsapp) else [],
            assunto,
            corpo,
            origem,
        )
        for key in stats:
            stats[key] += int(partial.get(key, 0))
    return stats

def email_students_by_turma(turma, assunto, corpo, origem):
    stats = notify_students_by_turma_channels(
        turma,
        assunto,
        corpo,
        origem,
        send_email=True,
        send_whatsapp=True,
    )
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

def notify_new_challenge(challenge_obj, send_email=True, send_whatsapp=True):
    challenge = challenge_obj if isinstance(challenge_obj, dict) else {}
    title_label = str(challenge.get("titulo", "Desafio da semana")).strip() or "Desafio da semana"
    description_label = str(challenge.get("descricao", "")).strip()
    week_label = str(challenge.get("semana", "")).strip()
    level_label = _norm_book_level(challenge.get("nivel", ""))
    due_label = str(challenge.get("due_date", "")).strip()
    target_label = _challenge_target_label(challenge)
    recipients = _students_for_challenge_target(
        challenge.get("nivel", ""),
        target_type=challenge.get("target_type", "nivel"),
        target_turma=challenge.get("target_turma", ""),
        target_aluno=challenge.get("target_aluno", ""),
        target_turmas_envio=_challenge_send_turmas(challenge),
    )
    stats = {"email_total": 0, "email_ok": 0, "whatsapp_total": 0, "whatsapp_ok": 0}
    for student in recipients:
        aluno_nome = str(student.get("nome", "")).strip()
        if not aluno_nome:
            continue
        mensagem = (
            f"Novo desafio liberado no Active.\n"
            f"{target_label}\n"
            f"Semana: {week_label}\n"
            f"Nivel: {level_label or '-'}\n"
            f"Prazo: {due_label or 'sem prazo'}\n\n"
            f"{description_label}\n\n"
            f"Acesse o portal do aluno > Desafios para responder."
        )
        partial = post_message_and_notify(
            autor=str(challenge.get("autor", "Coordenacao")).strip() or "Coordenacao",
            titulo=title_label,
            mensagem=mensagem,
            turma=str(student.get("turma", "")).strip() or "Sem Turma",
            origem="Desafios",
            publico="Alunos",
            send_email=bool(send_email),
            send_whatsapp=bool(send_whatsapp),
            aluno=aluno_nome,
        )
        for key in stats:
            stats[key] += int(partial.get(key, 0))
    stats["total"] = stats["email_total"]
    stats["enviados"] = stats["email_ok"]
    return stats

def notify_new_challenge_by_level(level, week_key, titulo, descricao, target_turmas_envio=None):
    challenge_obj = {
        "nivel": level,
        "semana": week_key,
        "titulo": titulo,
        "descricao": descricao,
        "target_type": "nivel",
        "target_turma": "",
        "target_aluno": "",
        "target_turmas_envio": [str(x).strip() for x in (target_turmas_envio or []) if str(x).strip()],
        "autor": st.session_state.get("user_name", "Coordenacao"),
    }
    return notify_new_challenge(challenge_obj, send_email=True, send_whatsapp=True)


def _notification_theme(origem, titulo, mensagem):
    origem_norm = _wiz_norm_text(origem)
    titulo_norm = _wiz_norm_text(titulo)
    mensagem_norm = _wiz_norm_text(mensagem)
    combined = " ".join([origem_norm, titulo_norm, mensagem_norm]).strip()
    if any(token in combined for token in ("financeiro", "boleto", "mensalidade", "vencimento", "pagamento", "cobranca")):
        return {
            "header": "💸 *Financeiro Active*",
            "title_emoji": "📌",
            "meta_emoji": "💼",
            "message_emoji": "💰",
            "footer": "📲 Consulte seu portal ou fale com a administracao para regularizacao.",
        }
    if any(token in combined for token in ("desafio", "atividade da semana", "weekly challenge")):
        return {
            "header": "🚀 *Novo Desafio no Active*",
            "title_emoji": "🏆",
            "meta_emoji": "🎯",
            "message_emoji": "✍️",
            "footer": "📚 Acesse o portal do aluno e conclua dentro do prazo.",
        }
    if any(token in combined for token in ("material", "livro", "apostila", "biblioteca", "pedido de material")):
        return {
            "header": "📚 *Atualizacao de Material*",
            "title_emoji": "📝",
            "meta_emoji": "📦",
            "message_emoji": "📘",
            "footer": "✅ Em caso de duvida, responda esta mensagem ou fale com a administracao.",
        }
    return {
        "header": "📢 *Active Educacional*",
        "title_emoji": "✨",
        "meta_emoji": "👤",
        "message_emoji": "💬",
        "footer": "😊 Qualquer duvida, estamos a disposicao.",
    }


def _build_notification_body(mensagem_obj, origem="Mensagens"):
    mensagem = mensagem_obj if isinstance(mensagem_obj, dict) else {}
    publico_label = str(mensagem.get("publico", "Alunos")).strip() or "Alunos"
    theme = _notification_theme(origem, mensagem.get("titulo", ""), mensagem.get("mensagem", ""))
    corpo_linhas = [
        theme["header"],
        "",
        f"{theme['title_emoji']} *{str(mensagem.get('titulo', 'Aviso')).strip() or 'Aviso'}*",
        "",
        f"{theme['meta_emoji']} Enviado por: {str(mensagem.get('autor', 'Sistema')).strip() or 'Sistema'}",
        f"👥 Publico: {publico_label}",
    ]
    if str(mensagem.get("aluno", "")).strip():
        corpo_linhas.append(f"🎓 Aluno: {str(mensagem.get('aluno', '')).strip()}")
        if str(mensagem.get("turma", "")).strip():
            corpo_linhas.append(f"🏫 Turma: {str(mensagem.get('turma', '')).strip()}")
    elif str(mensagem.get("professor_individual", "")).strip():
        corpo_linhas.append(f"👨‍🏫 Professor: {str(mensagem.get('professor_individual', '')).strip()}")
    elif str(mensagem.get("destinatario_unico", "")).strip():
        corpo_linhas.append(f"🙋 Destinatario: {str(mensagem.get('destinatario_unico', '')).strip()}")
    elif publico_label == "Professores":
        corpo_linhas.append(f"👨‍🏫 Professor(es): {str(mensagem.get('professor', 'Todos')).strip() or 'Todos'}")
    elif publico_label == "Alunos e Professores":
        if str(mensagem.get("turma", "")).strip():
            corpo_linhas.append(f"🏫 Turma: {str(mensagem.get('turma', '')).strip()}")
        corpo_linhas.append(f"👨‍🏫 Professor(es): {str(mensagem.get('professor', 'Todos')).strip() or 'Todos'}")
    else:
        if str(mensagem.get("turma", "")).strip():
            corpo_linhas.append(f"🏫 Turma: {str(mensagem.get('turma', '')).strip()}")
    corpo_linhas.extend(
        [
            f"📅 Data: {str(mensagem.get('data', '')).strip()}",
            "",
            f"{theme['message_emoji']} *Mensagem:*",
            str(mensagem.get("mensagem", "")).strip(),
        ]
    )
    footer = str(theme.get("footer", "")).strip()
    if footer:
        corpo_linhas.extend(["", footer])
    return "\n".join(corpo_linhas)


def post_message_and_notify(
    autor,
    titulo,
    mensagem,
    turma="Todas",
    origem="Mensagens",
    publico="Alunos",
    professor="Todos",
    send_email=True,
    send_whatsapp=True,
    student_only_existing_classes=False,
    include_students_without_turma_when_all=True,
    aluno="",
    professor_individual="",
    recipient_entry=None,
):
    aluno = str(aluno or "").strip()
    professor_individual = str(professor_individual or "").strip()
    recipient_entry = recipient_entry if isinstance(recipient_entry, dict) else {}
    recipient_name = str(recipient_entry.get("name", "")).strip()
    recipient_label = str(recipient_entry.get("label", recipient_name)).strip() or recipient_name
    recipient_emails = [str(x).strip().lower() for x in recipient_entry.get("emails", []) if str(x).strip()]
    recipient_whatsapps = [str(x).strip() for x in recipient_entry.get("whatsapps", []) if str(x).strip()]
    turma = str(turma or "Todas").strip() or "Todas"
    publico_label = str(publico or "Alunos").strip() or "Alunos"
    professor_label = str(professor or "Todos").strip() or "Todos"
    student_obj = next(
        (s for s in st.session_state.get("students", []) if str(s.get("nome", "")).strip() == aluno),
        {},
    ) if aluno else {}
    teacher_obj = next(
        (t for t in st.session_state.get("teachers", []) if str(t.get("nome", "")).strip() == professor_individual),
        {},
    ) if professor_individual else {}
    turma_destino = str(student_obj.get("turma", turma)).strip() or turma
    publico_destino = publico_label
    if aluno:
        publico_destino = "Aluno especifico"
    elif professor_individual:
        publico_destino = "Professor especifico"
    elif recipient_name:
        publico_destino = "Pessoa especifica"
    mensagem_obj = {
        "titulo": (titulo or "Aviso").strip(),
        "mensagem": (mensagem or "").strip(),
        "data": datetime.date.today().strftime("%d/%m/%Y"),
        "autor": autor.strip() if autor else "Sistema",
        "turma": turma_destino,
        "publico": publico_destino,
        "professor": professor_label,
        "aluno": aluno,
        "professor_individual": professor_individual,
        "destinatario_unico": recipient_label,
    }
    st.session_state["messages"].append(mensagem_obj)
    save_list(MESSAGES_FILE, st.session_state["messages"])
    assunto = f"[Active] {mensagem_obj['titulo']}"
    corpo = _build_notification_body(mensagem_obj, origem=origem)
    if mensagem_obj["aluno"] and student_obj:
        stats = _notify_direct_contacts(
            student_obj.get("nome", "Aluno"),
            _message_recipients_for_student(student_obj) if bool(send_email) else [],
            _student_whatsapp_recipients(student_obj) if bool(send_whatsapp) else [],
            assunto,
            corpo,
            origem,
        )
    elif mensagem_obj["aluno"]:
        stats = {"email_total": 0, "email_ok": 0, "whatsapp_total": 0, "whatsapp_ok": 0}
    elif str(mensagem_obj.get("professor_individual", "")).strip() and teacher_obj:
        stats = _notify_direct_contacts(
            teacher_obj.get("nome", "Professor"),
            [teacher_obj.get("email", "")] if bool(send_email) else [],
            [teacher_obj.get("celular", "")] if bool(send_whatsapp) else [],
            assunto,
            corpo,
            origem,
        )
    elif str(mensagem_obj.get("professor_individual", "")).strip():
        stats = {"email_total": 0, "email_ok": 0, "whatsapp_total": 0, "whatsapp_ok": 0}
    elif str(mensagem_obj.get("destinatario_unico", "")).strip():
        stats = _notify_direct_contacts(
            mensagem_obj.get("destinatario_unico", "Destinatario"),
            recipient_emails if bool(send_email) else [],
            recipient_whatsapps if bool(send_whatsapp) else [],
            assunto,
            corpo,
            origem,
        )
    elif publico_label == "Professores":
        stats = notify_teachers_channels(
            assunto,
            corpo,
            origem,
            professor=mensagem_obj.get("professor", "Todos"),
            send_email=bool(send_email),
            send_whatsapp=bool(send_whatsapp),
        )
    elif publico_label == "Alunos e Professores":
        stats_alunos = notify_students_by_turma_channels(
            mensagem_obj["turma"],
            assunto,
            corpo,
            origem,
            send_email=bool(send_email),
            send_whatsapp=bool(send_whatsapp),
            only_existing_classes=bool(student_only_existing_classes),
            include_students_without_turma_when_all=bool(include_students_without_turma_when_all),
        )
        stats_prof = notify_teachers_channels(
            assunto,
            corpo,
            origem,
            professor=mensagem_obj.get("professor", "Todos"),
            send_email=bool(send_email),
            send_whatsapp=bool(send_whatsapp),
        )
        stats = {
            "email_total": int(stats_alunos.get("email_total", 0)) + int(stats_prof.get("email_total", 0)),
            "email_ok": int(stats_alunos.get("email_ok", 0)) + int(stats_prof.get("email_ok", 0)),
            "whatsapp_total": int(stats_alunos.get("whatsapp_total", 0)) + int(stats_prof.get("whatsapp_total", 0)),
            "whatsapp_ok": int(stats_alunos.get("whatsapp_ok", 0)) + int(stats_prof.get("whatsapp_ok", 0)),
            "student_total": int(stats_alunos.get("student_total", 0)),
            "student_with_channel": int(stats_alunos.get("student_with_channel", 0)),
            "student_contacted": int(stats_alunos.get("student_contacted", 0)),
        }
    else:
        stats = notify_students_by_turma_channels(
            mensagem_obj["turma"],
            assunto,
            corpo,
            origem,
            send_email=bool(send_email),
            send_whatsapp=bool(send_whatsapp),
            only_existing_classes=bool(student_only_existing_classes),
            include_students_without_turma_when_all=bool(include_students_without_turma_when_all),
        )
    stats["total"] = stats.get("email_total", 0)
    stats["enviados"] = stats.get("email_ok", 0)
    return stats

def _message_matches_student(message_obj, aluno_nome, turma_aluno):
    publico_msg = str((message_obj or {}).get("publico", "Alunos")).strip()
    if publico_msg in ("Professores", "Professor especifico", "Pessoa especifica"):
        return False
    destinatario_unico = str((message_obj or {}).get("destinatario_unico", "")).strip()
    if destinatario_unico:
        destinatario_base = destinatario_unico.split("(", 1)[0].strip()
        return destinatario_base == str(aluno_nome or "").strip()
    aluno_msg = str((message_obj or {}).get("aluno", "")).strip()
    if aluno_msg:
        return aluno_msg == str(aluno_nome or "").strip()
    turma_msg = str((message_obj or {}).get("turma", "")).strip()
    if not turma_msg or turma_msg == "Todas":
        return False
    return turma_msg == str(turma_aluno or "").strip()

def _message_matches_teacher(message_obj, prof_nome, turmas_prof):
    msg = message_obj or {}
    prof_name = str(prof_nome or "").strip().lower()
    turmas_set = {str(t).strip() for t in (turmas_prof or []) if str(t).strip()}
    publico_msg = str(msg.get("publico", "Alunos")).strip() or "Alunos"
    aluno_msg = str(msg.get("aluno", "")).strip()
    professor_individual_msg = str(msg.get("professor_individual", "")).strip()
    professor_msg = str(msg.get("professor", "Todos")).strip() or "Todos"
    turma_msg = str(msg.get("turma", "")).strip() or "Todas"

    if aluno_msg:
        return False
    if professor_individual_msg:
        return professor_individual_msg.lower() == prof_name
    if publico_msg == "Pessoa especifica":
        return False
    if publico_msg == "Professores":
        return professor_msg == "Todos" or professor_msg.strip().lower() == prof_name
    if publico_msg == "Alunos e Professores":
        if professor_msg != "Todos" and professor_msg.strip().lower() != prof_name:
            return False
        return turma_msg == "Todas" or turma_msg in turmas_set
    return turma_msg == "Todas" or turma_msg in turmas_set

def _message_destination_label(message_obj):
    publico_msg = str((message_obj or {}).get("publico", "Alunos")).strip() or "Alunos"
    professor_msg = str((message_obj or {}).get("professor", "Todos")).strip() or "Todos"
    aluno_msg = str((message_obj or {}).get("aluno", "")).strip()
    professor_individual_msg = str((message_obj or {}).get("professor_individual", "")).strip()
    destinatario_unico = str((message_obj or {}).get("destinatario_unico", "")).strip()
    turma_msg = str((message_obj or {}).get("turma", "")).strip() or "Todas"
    if aluno_msg:
        return f"Publico: Aluno especifico | Destino: {aluno_msg} | Turma: {turma_msg}"
    if professor_individual_msg:
        return f"Publico: Professor especifico | Destino: {professor_individual_msg}"
    if destinatario_unico:
        return f"Publico: Pessoa especifica | Destino: {destinatario_unico}"
    if publico_msg == "Professores":
        return f"Publico: Professores | Professor(es): {professor_msg}"
    if publico_msg == "Alunos e Professores":
        return f"Publico: Alunos e Professores | Turma: {turma_msg} | Professor(es): {professor_msg}"
    return f"Publico: {publico_msg} | Turma: {turma_msg}"

def _message_uid(message_obj):
    msg = message_obj if isinstance(message_obj, dict) else {}
    msg_id = str(msg.get("id", "")).strip()
    if msg_id:
        return msg_id
    raw = "|".join(
        [
            str(msg.get("data", "")).strip(),
            str(msg.get("autor", "")).strip(),
            str(msg.get("titulo", "")).strip(),
            str(msg.get("mensagem", "")).strip(),
            str(msg.get("publico", "")).strip(),
            str(msg.get("turma", "")).strip(),
            str(msg.get("aluno", "")).strip(),
            str(msg.get("professor_individual", "")).strip(),
            str(msg.get("destinatario_unico", "")).strip(),
        ]
    )
    return hashlib.md5(raw.encode("utf-8", errors="ignore")).hexdigest()[:16]

def _student_read_message_ids(student_obj):
    student = student_obj if isinstance(student_obj, dict) else {}
    raw = student.get("mensagens_lidas", [])
    if isinstance(raw, list):
        return {str(x).strip() for x in raw if str(x).strip()}
    if isinstance(raw, str):
        return {part.strip() for part in raw.split(",") if part.strip()}
    return set()

def _mark_student_messages_read(student_name, messages_list):
    aluno_nome = str(student_name or "").strip()
    if not aluno_nome:
        return 0
    student = next(
        (s for s in st.session_state.get("students", []) if str(s.get("nome", "")).strip() == aluno_nome),
        None,
    )
    if not isinstance(student, dict):
        return 0
    current = _student_read_message_ids(student)
    incoming = {_message_uid(m) for m in (messages_list or []) if isinstance(m, dict)}
    incoming = {x for x in incoming if x}
    if not incoming:
        return 0
    new_ids = incoming - current
    if not new_ids:
        return 0
    merged = list(current | incoming)
    # Evita crescimento indefinido do cadastro.
    student["mensagens_lidas"] = merged[-800:]
    save_list(STUDENTS_FILE, st.session_state.get("students", []))
    return len(new_ids)

def sidebar_menu(title, options, key):
    icon_map = {
        "Dashboard": "🏠",
        "Painel": "🏠",
        "Agenda": "📅",
        "Links Ao Vivo": "🔗",
        "Minhas Turmas": "👩‍🏫",
        "Minhas Aulas": "🧑‍🏫",
        "Alunos": "🎓",
        "Professores": "👨‍🏫",
        "Usuários": "👥",
        "Usuarios": "👥",
        "Turmas": "🏫",
        "Financeiro": "💸",
        "Estoque": "📦",
        "Certificados": "📜",
        "Biblioteca": "📚",
        "Livros": "📚",
        "Aprovação Notas": "✅",
        "Caixa de Entrada": "📨",
        "Conteúdos": "🗂️",
        "Desafios": "🧩",
        "Atividades": "📝",
        "Mensagens": "💬",
        "Aulas Gravadas": "🎬",
        "Materiais de Estudo": "🧠",
        "WhatsApp (Evolution)": "🟢",
        "Backup": "🛟",
        "ASSISTENTE WIZ": "🤖",
        "Professor Wiz": "✨",
    }
    st.markdown(f"<h3 style='color:#1e3a8a; font-family:Sora; margin-top:0;'>{title}</h3>", unsafe_allow_html=True)
    if key not in st.session_state or st.session_state.get(key) not in options:
        st.session_state[key] = options[0]
    for option in options:
        active = st.session_state[key] == option
        icon = icon_map.get(str(option).strip(), "•")
        option_label = f"{icon}  {option}"
        if st.button(option_label, key=f"{key}_{option}", type="primary" if active else "secondary"):
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
    raw = str(value or "").strip().lower()
    raw = unicodedata.normalize("NFKD", raw)
    raw = "".join(ch for ch in raw if not unicodedata.combining(ch))
    raw = re.sub(r"[^a-z0-9]+", "_", raw)
    return raw.strip("_")

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
        "nome_aluno": "nome",
        "nome_completo": "nome",
        "matricula": "matricula",
        "numero_matricula": "matricula",
        "numero_da_matricula": "matricula",
        "n_matricula": "matricula",
        "turma": "turma",
        "email": "email",
        "e_mail": "email",
        "celular": "celular",
        "telefone": "celular",
        "telefone_celular": "celular",
        "celular_whatsapp": "celular",
        "whatsapp": "celular",
        "data_nascimento": "data_nascimento",
        "nascimento": "data_nascimento",
        "idade": "idade",
        "genero": "genero",
        "sexo": "genero",
        "rg": "rg",
        "cpf": "cpf",
        "cidade": "cidade",
        "cidade_endereco": "cidade",
        "bairro": "bairro",
        "bairro_endereco": "bairro",
        "cidade_natal": "cidade_natal",
        "pais": "pais",
        "cep": "cep",
        "codigo_postal": "cep",
        "rua": "rua",
        "endereco": "rua",
        "logradouro": "rua",
        "endereco_rua": "rua",
        "numero": "numero",
        "numero_endereco": "numero",
        "n_numero": "numero",
        "complemento": "complemento",
        "complemento_endereco": "complemento",
        "endereco_completo": "complemento",
        "observacao_endereco": "complemento",
        "observacoes_endereco": "complemento",
        "obs_endereco": "complemento",
        "apto": "complemento",
        "modulo": "modulo",
        "livro": "livro",
        "usuario": "usuario",
        "login": "usuario",
        "senha": "senha",
        "responsavel_nome": "responsavel_nome",
        "nome_responsavel": "responsavel_nome",
        "responsavel_cpf": "responsavel_cpf",
        "responsavel_celular": "responsavel_celular",
        "nome_do_responsavel": "responsavel_nome",
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
                destino_txt = _message_destination_label(msg)
                with st.container():
                    st.markdown(
                        f"""<div style="background:white; padding:16px; border-radius:12px; border:1px solid #e2e8f0; margin-bottom:10px;">
                        <div style="font-weight:700; color:#1e3a8a;">{msg.get('titulo','Noticia')}</div>
                        <div style="font-size:0.85rem; color:#64748b; margin-bottom:8px;">{msg.get('data','')} | {msg.get('autor','')} | {destino_txt}</div>
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
        "Nunca afirme com certeza dados de alunos, turmas, valores, agenda ou financeiro sem confirmacao no sistema.",
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


def _student_bot_state_key(student_name, suffix):
    return f"student_wiz:{suffix}:{_wiz_norm_text(student_name)}"


def _student_cpf_matches(student_obj, raw_text):
    student = student_obj if isinstance(student_obj, dict) else {}
    expected = _wiz_digits(student.get("cpf", ""))
    informed = _wiz_digits(raw_text)
    return bool(expected and informed and expected == informed)


def _student_active_info_request(text):
    norm = _wiz_norm_text(text)
    if not norm:
        return False
    keywords = [
        "financeiro", "boleto", "mensalidade", "pagamento", "vencimento", "cobranca",
        "turma", "horario", "agenda", "aula", "zoom", "link da aula",
        "material", "materiais", "livro", "apostila",
        "nota", "notas", "media", "frequencia", "frequencia", "presenca", "presenca",
        "prova", "certificado", "matricula", "professor", "desafio", "portal", "cadastro",
    ]
    return any(token in norm for token in keywords)


def _student_material_request_intent(text):
    norm = _wiz_norm_text(text)
    if not norm:
        return False
    material_terms = ["material", "materiais", "livro", "apostila", "book", "kit"]
    request_terms = [
        "pedido", "pedir", "solicitar", "solicito", "preciso", "quero", "gostaria",
        "comprar", "adquirir", "receber", "entregar", "enviar", "separar", "retirar",
        "nao recebi", "nao tenho", "sem material", "faltando", "falta", "perdi",
    ]
    return any(term in norm for term in material_terms) and any(term in norm for term in request_terms)


def _student_admin_contacts():
    admins = []
    coords = []
    for user in st.session_state.get("users", []):
        if not isinstance(user, dict):
            continue
        perfil = str(user.get("perfil", "")).strip()
        if perfil == "Admin":
            admins.append(user)
        elif perfil == "Coordenador":
            coords.append(user)
    selected = admins or coords
    names = []
    emails = set()
    whatsapps = set()
    for user in selected:
        nome = str(user.get("nome", user.get("usuario", ""))).strip()
        if nome:
            names.append(nome)
        email = str(user.get("email", "")).strip().lower()
        celular = str(user.get("celular", "")).strip()
        if email:
            emails.add(email)
        if celular:
            whatsapps.add(celular)
    return {
        "names": names,
        "emails": sorted(emails),
        "whatsapps": sorted(whatsapps),
    }


def _create_material_order_from_student_bot(student_obj, request_text):
    student = student_obj if isinstance(student_obj, dict) else {}
    aluno_nome = str(student.get("nome", st.session_state.get("user_name", ""))).strip() or "Aluno"
    turma = str(student.get("turma", "")).strip() or "Sem Turma"
    livro = student_book_level(student) or str(student.get("livro", "")).strip()
    request_norm = _wiz_norm_text(request_text)
    is_book_request = any(token in request_norm for token in ("livro", "apostila", "book"))
    tipo = "Livro didático" if is_book_request else "Material"
    item_codigo = livro if is_book_request else ""
    item_desc = f"Livro didático {livro}" if is_book_request and livro else "Pedido de material do aluno"
    pedido = {
        "id": uuid.uuid4().hex[:10],
        "data": datetime.datetime.now().strftime("%d/%m/%Y %H:%M"),
        "solicitante": aluno_nome,
        "tipo": tipo,
        "item_codigo": item_codigo,
        "item": item_desc,
        "quantidade": 1,
        "status": "Aberto",
        "observacao": f"Pedido via Bot Mister Wiz: {str(request_text or '').strip()}",
        "aluno": aluno_nome,
        "turma": turma,
        "livro": livro,
        "origem": "Bot Mister Wiz",
    }
    st.session_state["material_orders"].append(pedido)
    save_list(MATERIAL_ORDERS_FILE, st.session_state["material_orders"])
    return pedido


def _notify_admin_material_request(order_obj):
    order = order_obj if isinstance(order_obj, dict) else {}
    contacts = _student_admin_contacts()
    assunto = "[Active] Novo pedido de material via Bot Mister Wiz"
    corpo = (
        "Novo pedido de material aberto automaticamente pelo Bot Mister Wiz.\n\n"
        f"Aluno: {str(order.get('aluno', '')).strip() or str(order.get('solicitante', 'Aluno')).strip()}\n"
        f"Turma: {str(order.get('turma', '')).strip() or 'Sem Turma'}\n"
        f"Livro/Nivel: {str(order.get('livro', '')).strip() or '-'}\n"
        f"Tipo: {str(order.get('tipo', '')).strip() or 'Material'}\n"
        f"Item: {str(order.get('item', '')).strip() or 'Pedido de material'}\n"
        f"Data: {str(order.get('data', '')).strip()}\n"
        f"Observacao: {str(order.get('observacao', '')).strip() or '-'}"
    )
    return _notify_direct_contacts(
        ", ".join(contacts.get("names", []) or ["Administrador"]),
        [],
        contacts.get("whatsapps", []),
        assunto,
        corpo,
        "Bot Mister Wiz",
    )


def _student_active_account_context(student_obj):
    student = student_obj if isinstance(student_obj, dict) else {}
    aluno_nome = str(student.get("nome", st.session_state.get("user_name", ""))).strip()
    turma = str(student.get("turma", "")).strip() or "Sem Turma"
    livro = student_book_level(student) or str(student.get("livro", "")).strip() or "Livro 1"
    matricula = str(student.get("matricula", "")).strip() or "-"
    turma_obj = next(
        (c for c in st.session_state.get("classes", []) if str(c.get("nome", "")).strip() == turma),
        {},
    )
    professor = str(turma_obj.get("professor", "")).strip() or "Nao informado"
    modulo = str(turma_obj.get("modulo", "")).strip() or "Nao informado"
    dias_raw = turma_obj.get("dias_semana", turma_obj.get("dias", []))
    if isinstance(dias_raw, list):
        dias_txt = ", ".join(str(d).strip() for d in dias_raw if str(d).strip())
    else:
        dias_txt = str(dias_raw or "").strip()
    hora_inicio = str(turma_obj.get("hora_inicio", "")).strip()
    hora_fim = str(turma_obj.get("hora_fim", "")).strip()

    recebiveis = [
        r for r in st.session_state.get("receivables", [])
        if str(r.get("aluno", "")).strip() == aluno_nome
    ]
    abertos = [r for r in recebiveis if str(r.get("status", "")).strip().lower() != "pago"]
    total_aberto = sum(parse_money(r.get("valor_parcela", r.get("valor", 0))) for r in abertos)
    proximos_boletos = sorted(
        abertos,
        key=lambda r: parse_date(r.get("vencimento", "")) or datetime.date(2100, 1, 1),
    )[:3]

    notas_aprovadas = [
        g for g in st.session_state.get("grades", [])
        if str(g.get("aluno", "")).strip() == aluno_nome and str(g.get("status", "")).strip().lower() == "aprovado"
    ]
    notas_numericas = []
    presencas = []
    for nota_obj in notas_aprovadas:
        avaliacao_norm = _wiz_norm_text(nota_obj.get("avaliacao", ""))
        nota_txt = str(nota_obj.get("nota", "")).strip()
        match_num = re.search(r"-?\d+(?:[.,]\d+)?", nota_txt)
        if not match_num:
            continue
        valor_nota = _parse_float(match_num.group(0), default=0.0)
        if "%" in nota_txt or "presenca" in avaliacao_norm:
            presencas.append(max(0.0, min(100.0, valor_nota)))
        else:
            notas_numericas.append(valor_nota)
    media_label = f"{(sum(notas_numericas) / len(notas_numericas)):.1f}" if notas_numericas else "Sem notas"
    frequencia_label = f"{(sum(presencas) / len(presencas)):.0f}%" if presencas else "Sem frequencia"

    provas = []
    hoje = datetime.date.today()
    for nota_obj in st.session_state.get("grades", []):
        if str(nota_obj.get("aluno", "")).strip() != aluno_nome:
            continue
        avaliacao_txt = str(nota_obj.get("avaliacao", "")).strip()
        if "prova" not in _wiz_norm_text(avaliacao_txt) and "test" not in _wiz_norm_text(avaliacao_txt):
            continue
        data_prova = parse_date(nota_obj.get("data", ""))
        if data_prova and data_prova >= hoje:
            provas.append(f"{data_prova.strftime('%d/%m/%Y')} - {avaliacao_txt or 'Prova'}")

    materiais = sorted(
        filter_items_by_turma(st.session_state.get("materials", []), turma),
        key=lambda m: str(m.get("data", "")),
        reverse=True,
    )[:5]
    mensagens = [
        m for m in st.session_state.get("messages", [])
        if _message_matches_student(m, aluno_nome, turma)
    ]
    mensagens = sorted(mensagens, key=lambda m: str(m.get("data", "")), reverse=True)[:5]

    desafios = get_student_weekly_challenges(student, current_week_key())[:5]
    sessoes = [
        s for s in st.session_state.get("class_sessions", [])
        if str(s.get("turma", "")).strip() == turma and str(s.get("status", "")).strip().lower() == "finalizada"
    ]
    sessoes = sorted(
        sessoes,
        key=lambda s: (
            parse_date(s.get("data", "")) or datetime.date(1900, 1, 1),
            parse_time(s.get("hora_inicio_real", s.get("hora_inicio_prevista", "00:00"))),
        ),
        reverse=True,
    )[:3]

    lines = [
        "Dados confirmados do aluno no Active:",
        f"Aluno: {aluno_nome or 'Nao informado'}",
        f"Matricula: {matricula}",
        f"Turma: {turma}",
        f"Livro/Nivel: {livro}",
        f"Professor da turma: {professor}",
        f"Modulo da turma: {modulo}",
    ]
    if dias_txt or hora_inicio or hora_fim:
        lines.append(f"Horario da turma: {dias_txt or '-'} | {hora_inicio or '--:--'} as {hora_fim or '--:--'}")
    lines.append(f"Financeiro em aberto: {len(abertos)} lancamento(s) | Total {format_money(total_aberto)}")
    if proximos_boletos:
        lines.append(
            "Proximos vencimentos: " + " ; ".join(
                f"{str(item.get('vencimento', '')).strip()} - {str(item.get('descricao', 'Lancamento')).strip()} - {format_money(parse_money(item.get('valor_parcela', item.get('valor', 0))))}"
                for item in proximos_boletos
            )
        )
    lines.append(f"Media geral atual: {media_label}")
    lines.append(f"Frequencia atual: {frequencia_label}")
    if provas:
        lines.append("Proximas provas: " + " ; ".join(provas[:3]))
    if materiais:
        lines.append(
            "Materiais recentes: " + " ; ".join(
                str(m.get("titulo", "Material")).strip() or "Material"
                for m in materiais
            )
        )
    if mensagens:
        lines.append(
            "Mensagens recentes do aluno: " + " ; ".join(
                f"{str(m.get('data', '')).strip()} - {str(m.get('titulo', 'Mensagem')).strip() or 'Mensagem'}"
                for m in mensagens
            )
        )
    if desafios:
        lines.append(
            "Desafios vigentes: " + " ; ".join(
                f"{str(ch.get('titulo', 'Desafio')).strip()} ({_challenge_target_label(ch)})"
                for ch in desafios
            )
        )
    if sessoes:
        lines.append(
            "Ultimas aulas finalizadas: " + " ; ".join(
                f"{str(s.get('data', '')).strip()} - {str(s.get('licao', s.get('resumo_final', 'Aula finalizada'))).strip() or 'Aula finalizada'}"
                for s in sessoes
            )
        )
    return "\n".join(lines)


def get_student_active_prompt(student_obj):
    return "\n".join(
        [
            "Voce e o Bot Mister Wiz integrado ao sistema Active Educacional.",
            "O CPF do aluno ja foi confirmado nesta sessao antes desta consulta.",
            "Responda somente com dados do proprio aluno informado abaixo.",
            "Nunca exponha dados de outros alunos, professores ou usuarios.",
            "Nao invente informacoes. Se o dado nao estiver no contexto, diga claramente que nao foi encontrado no Active.",
            _student_active_account_context(student_obj),
        ]
    )


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
        st.caption("Modo automatico do aluno: ingles por livro/licao da turma. Consultas do Active e pedido de material exigem confirmacao de CPF.")
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
        user_text = str(user_text).strip()
        answer = ""
        request_messages = []

        if role == "Aluno":
            aluno_nome = str(st.session_state.get("user_name", "")).strip()
            aluno_obj = _find_student_by_name(aluno_nome)
            contexto_aluno = student_wiz_context(aluno_nome)
            verified_key = _student_bot_state_key(aluno_nome, "cpf_verified")
            pending_key = _student_bot_state_key(aluno_nome, "pending_question")
            pending_kind_key = _student_bot_state_key(aluno_nome, "pending_kind")
            pending_question = str(st.session_state.get(pending_key, "")).strip()
            pending_kind = str(st.session_state.get(pending_kind_key, "")).strip()
            display_user_text = "CPF informado para confirmacao." if _wiz_digits(user_text) else user_text
            chat_history.append({"role": "user", "content": display_user_text})

            if _wiz_norm_text(user_text) in ("cancelar", "cancela", "deixa pra la", "deixa pra lá"):
                st.session_state.pop(pending_key, None)
                st.session_state.pop(pending_kind_key, None)
                answer = "Solicitacao cancelada. Se quiser consultar dados do Active ou pedir material, envie a mensagem novamente."
            elif pending_question:
                if _student_cpf_matches(aluno_obj, user_text):
                    st.session_state[verified_key] = True
                    st.session_state.pop(pending_key, None)
                    st.session_state.pop(pending_kind_key, None)
                    if pending_kind == "material":
                        pedido = _create_material_order_from_student_bot(aluno_obj, pending_question)
                        notify_stats = _notify_admin_material_request(pedido)
                        admin_msg = "Administrador avisado no WhatsApp." if int(notify_stats.get("whatsapp_ok", 0)) > 0 else "Pedido registrado; verifique a configuracao do WhatsApp do administrador."
                        answer = (
                            "Pedido de material registrado com sucesso.\n\n"
                            f"Tipo: {str(pedido.get('tipo', '')).strip() or 'Material'}\n"
                            f"Item: {str(pedido.get('item', '')).strip() or 'Pedido de material'}\n"
                            f"Turma: {str(pedido.get('turma', '')).strip() or 'Sem Turma'}\n"
                            f"{admin_msg}"
                        )
                    else:
                        system_prompt = get_student_active_prompt(aluno_obj)
                        request_messages = [
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": pending_question},
                        ]
                else:
                    answer = (
                        "CPF nao confirmado. Envie seu CPF exatamente como esta no cadastro para liberar consulta do Active ou pedido de material."
                        if _wiz_digits(user_text)
                        else "Para continuar, confirme seu CPF cadastrado. Se quiser cancelar, envie: cancelar."
                    )
            elif _student_material_request_intent(user_text):
                if not _wiz_digits((aluno_obj or {}).get("cpf", "")):
                    answer = "Seu CPF nao esta cadastrado no Active. Procure a secretaria para liberar esse atendimento."
                elif not bool(st.session_state.get(verified_key, False)):
                    st.session_state[pending_key] = user_text
                    st.session_state[pending_kind_key] = "material"
                    answer = "Para abrir seu pedido de material, confirme primeiro seu CPF cadastrado."
                else:
                    pedido = _create_material_order_from_student_bot(aluno_obj, user_text)
                    notify_stats = _notify_admin_material_request(pedido)
                    admin_msg = "Administrador avisado no WhatsApp." if int(notify_stats.get("whatsapp_ok", 0)) > 0 else "Pedido registrado; verifique a configuracao do WhatsApp do administrador."
                    answer = (
                        "Pedido de material registrado com sucesso.\n\n"
                        f"Tipo: {str(pedido.get('tipo', '')).strip() or 'Material'}\n"
                        f"Item: {str(pedido.get('item', '')).strip() or 'Pedido de material'}\n"
                        f"Turma: {str(pedido.get('turma', '')).strip() or 'Sem Turma'}\n"
                        f"{admin_msg}"
                    )
            elif _student_active_info_request(user_text):
                if not _wiz_digits((aluno_obj or {}).get("cpf", "")):
                    answer = "Seu CPF nao esta cadastrado no Active. Procure a secretaria para liberar consultas administrativas no bot."
                elif not bool(st.session_state.get(verified_key, False)):
                    st.session_state[pending_key] = user_text
                    st.session_state[pending_kind_key] = "active_info"
                    answer = "Para consultar seus dados do Active, confirme primeiro seu CPF cadastrado."
                else:
                    system_prompt = get_student_active_prompt(aluno_obj)
                    request_messages = [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_text},
                    ]
            else:
                system_prompt = get_tutor_wiz_prompt(contexto_aluno)
                request_messages = [{"role": "system", "content": system_prompt}] + chat_history[-16:]
        else:
            chat_history.append({"role": "user", "content": user_text})
            if role == "Professor":
                system_prompt = get_active_system_prompt("Pedagogico", include_context=include_context) + (
                    "\nAtenda apenas temas pedagogicos da escola de ingles: plano de aula, tarefa, avaliacao, rubrica e reforco."
                )
            else:
                system_prompt = get_active_system_prompt(mode, include_context)
            request_messages = [{"role": "system", "content": system_prompt}] + chat_history[-16:]

        if not answer:
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

def render_sales_leads_manage(vendedor_atual):
    leads = st.session_state.get("sales_leads", [])
    if not leads:
        st.info("Nenhum lead cadastrado.")
        return
    leads_changed_runtime = False
    for lead in leads:
        if not isinstance(lead, dict):
            continue
        if not str(lead.get("id", "")).strip():
            lead["id"] = uuid.uuid4().hex
            leads_changed_runtime = True
        if _sales_reconcile_lead_record(lead):
            leads_changed_runtime = True
    if leads_changed_runtime:
        save_list(SALES_LEADS_FILE, st.session_state.get("sales_leads", []))

    st.markdown("### Base de Leads (dinamica e personalizavel)")
    all_origens = sorted(
        {
            str(l.get("origem", "")).strip()
            for l in leads
            if str(l.get("origem", "")).strip()
        }
    )
    all_estados = sorted(
        {
            str(l.get("estado", "")).strip().upper()
            for l in leads
            if str(l.get("estado", "")).strip()
        }
    )
    all_vendedores = sorted(
        {
            str(l.get("vendedor", "")).strip()
            for l in leads
            if str(l.get("vendedor", "")).strip()
        }
    )
    all_tags = sorted(
        {
            tag
            for l in leads
            for tag in _lead_tags_list(l.get("tags", []))
        }
    )

    with st.expander("Filtro", expanded=False):
        f1, f2, f3, f4 = st.columns(4)
        with f1:
            segmento = st.selectbox(
                "Segmentacao",
                [
                    "Todos",
                    "Sem contato ha 7 dias",
                    "Leads quentes sem agendamento",
                    "Com conversoes",
                    "Sem e-mail",
                ],
                key="sales_lead_segmento",
            )
        with f2:
            busca = st.text_input("Busca rapida", key="sales_lead_busca")
        with f3:
            status_filter = st.multiselect("Status", sales_lead_status_options(), key="sales_lead_status_filter")
        with f4:
            estagio_filter = st.multiselect("Estagio no funil", sales_pipeline_stage_options(), key="sales_lead_estagio_filter")

        f5, f6, f7, f8 = st.columns(4)
        with f5:
            origem_filter = st.multiselect("Origem", all_origens, key="sales_lead_origem_filter")
        with f6:
            estado_filter = st.multiselect("Estado (UF)", all_estados, key="sales_lead_estado_filter")
        with f7:
            tag_filter = st.multiselect("Tags", all_tags, key="sales_lead_tag_filter")
        with f8:
            vendedor_filter = st.multiselect("Consultor", all_vendedores, key="sales_lead_vendedor_filter")

    agenda = st.session_state.get("sales_agenda", [])
    lead_ids_com_agenda = {
        str(a.get("lead_id", "")).strip()
        for a in agenda
        if isinstance(a, dict) and str(a.get("status", "")).strip() == "Agendado"
    }

    filtrados = []
    busca_norm = normalize_text(busca)
    hoje = datetime.date.today()
    for lead in leads:
        if not isinstance(lead, dict):
            continue
        lead_status = str(lead.get("status", "")).strip()
        lead_estagio = str(lead.get("estagio_funil", "")).strip()
        lead_origem = str(lead.get("origem", "")).strip()
        lead_estado = str(lead.get("estado", "")).strip().upper()
        lead_vendedor = str(lead.get("vendedor", "")).strip()
        lead_tags = _lead_tags_list(lead.get("tags", []))
        lead_id = str(lead.get("id", "")).strip()

        if status_filter and lead_status not in status_filter:
            continue
        if estagio_filter and lead_estagio not in estagio_filter:
            continue
        if origem_filter and lead_origem not in origem_filter:
            continue
        if estado_filter and lead_estado not in estado_filter:
            continue
        if vendedor_filter and lead_vendedor not in vendedor_filter:
            continue
        if tag_filter and not any(tag in lead_tags for tag in tag_filter):
            continue

        if busca_norm:
            lead_texto = " ".join(
                [
                    str(lead.get("nome", "")),
                    str(lead.get("email", "")),
                    str(lead.get("celular", "")),
                    str(lead.get("telefone", "")),
                    str(lead.get("cargo", "")),
                    str(lead.get("cidade", "")),
                    str(lead.get("estado", "")),
                    str(lead.get("origem", "")),
                    str(lead.get("estagio_funil", "")),
                    str(lead.get("interesse", "")),
                    str(lead.get("vendedor", "")),
                    _lead_tags_text(lead),
                ]
            )
            if busca_norm not in normalize_text(lead_texto):
                continue

        if segmento == "Sem contato ha 7 dias":
            last_contact_dt = _lead_last_contact_date(lead)
            if last_contact_dt is not None and (hoje - last_contact_dt).days < 7:
                continue
        elif segmento == "Leads quentes sem agendamento":
            if lead_status != "Leads quentes":
                continue
            if lead_id in lead_ids_com_agenda:
                continue
        elif segmento == "Com conversoes":
            if not lead.get("conversoes", []):
                continue
        elif segmento == "Sem e-mail":
            if str(lead.get("email", "")).strip():
                continue

        filtrados.append(lead)

    total = len(filtrados)
    quentes = len([l for l in filtrados if str(l.get("status", "")).strip() == "Leads quentes"])
    fechados = len([l for l in filtrados if str(l.get("status", "")).strip() == "Fechado"])
    sem_contato_7 = len(
        [
            l for l in filtrados
            if (_lead_last_contact_date(l) is None or (hoje - _lead_last_contact_date(l)).days >= 7)
        ]
    )
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Total de leads", str(total))
    m2.metric("Leads quentes", str(quentes))
    m3.metric("Fechados", str(fechados))
    m4.metric("Sem contato >= 7 dias", str(sem_contato_7))

    rows = []
    for lead in filtrados:
        lead_id = str(lead.get("id", "")).strip() or uuid.uuid4().hex
        show_cell = str(lead.get("celular", "")).strip() or str(lead.get("telefone", "")).strip()
        rows.append(
            {
                "ID": lead_id,
                "Nome": str(lead.get("nome", "")).strip(),
                "Email": str(lead.get("email", "")).strip(),
                "Celular": show_cell,
                "Telefone": str(lead.get("telefone", "")).strip(),
                "Cargo": str(lead.get("cargo", "")).strip(),
                "Cidade": str(lead.get("cidade", "")).strip(),
                "Estado": str(lead.get("estado", "")).strip(),
                "Origem": str(lead.get("origem", "")).strip(),
                "Estagio no Funil": str(lead.get("estagio_funil", "")).strip(),
                "Tags": _lead_tags_text(lead),
                "Status": str(lead.get("status", "")).strip(),
                "Interesse": str(lead.get("interesse", "")).strip(),
                "Empresa": str(lead.get("empresa", "")).strip(),
                "Consultor": str(lead.get("vendedor", "")).strip(),
                "Ultimo Contato": str(lead.get("ultimo_contato", "")).strip(),
                "Interacoes": len(lead.get("interacoes", [])),
                "Conversoes": len(lead.get("conversoes", [])),
                "Criado em": str(lead.get("created_at", "")).strip(),
            }
        )

    if not rows:
        st.info("Nenhum lead encontrado com os filtros aplicados.")
    else:
        df_leads = pd.DataFrame(rows)
        all_cols = list(df_leads.columns)
        default_cols = [
            "Nome",
            "Email",
            "Celular",
            "Cargo",
            "Cidade",
            "Estado",
            "Origem",
            "Estagio no Funil",
            "Tags",
            "Status",
            "Consultor",
            "Ultimo Contato",
        ]
        with st.expander("Filtro de colunas", expanded=False):
            visible_cols = st.multiselect(
                "Colunas visiveis",
                all_cols,
                default=[c for c in default_cols if c in all_cols],
                key="sales_lead_visible_cols",
            )
        if not visible_cols:
            visible_cols = ["Nome", "Email", "Celular", "Status"]
        if "Celular" in all_cols and "Celular" not in visible_cols:
            if "Email" in visible_cols:
                idx_email = visible_cols.index("Email") + 1
                visible_cols = visible_cols[:idx_email] + ["Celular"] + visible_cols[idx_email:]
            else:
                visible_cols = ["Celular"] + visible_cols
        s1, s2 = st.columns(2)
        with s1:
            sort_col = st.selectbox("Ordenar por", all_cols, index=all_cols.index("Nome") if "Nome" in all_cols else 0)
        with s2:
            sort_desc = st.checkbox("Ordem decrescente", value=False)
        df_show = df_leads.sort_values(by=[sort_col], ascending=not sort_desc, na_position="last")
        column_cfg = {
            "Nome": st.column_config.TextColumn("Nome", width="medium"),
            "Email": st.column_config.TextColumn("Email", width="medium"),
            "Celular": st.column_config.TextColumn("Celular", width="small"),
            "Telefone": st.column_config.TextColumn("Telefone", width="small"),
            "Cargo": st.column_config.TextColumn("Cargo", width="small"),
            "Cidade": st.column_config.TextColumn("Cidade", width="small"),
            "Estado": st.column_config.TextColumn("Estado", width="small"),
            "Origem": st.column_config.TextColumn("Origem", width="small"),
            "Estagio no Funil": st.column_config.TextColumn("Estagio no Funil", width="small"),
            "Status": st.column_config.TextColumn("Status", width="small"),
            "Interacoes": st.column_config.NumberColumn("Interacoes", width="small"),
            "Conversoes": st.column_config.NumberColumn("Conversoes", width="small"),
            "ID": st.column_config.TextColumn("ID", width="small"),
        }
        st.dataframe(
            df_show[visible_cols],
            use_container_width=True,
            height=420,
            hide_index=True,
            column_config=column_cfg,
        )

        csv_bytes = df_show.to_csv(index=False).encode("utf-8-sig")
        st.download_button(
            "Exportar base filtrada (CSV)",
            data=csv_bytes,
            file_name=f"base_leads_{datetime.date.today().strftime('%Y%m%d')}.csv",
            mime="text/csv",
            key="sales_leads_export_filtered",
        )

    lead_labels_by_id = {}
    for lead in filtrados:
        lead_id = str(lead.get("id", "")).strip()
        if not lead_id:
            continue
        show_cell = str(lead.get("celular", "")).strip() or str(lead.get("telefone", "")).strip() or "-"
        show_mail = str(lead.get("email", "")).strip() or "-"
        lead_labels_by_id[lead_id] = f"{str(lead.get('nome', '')).strip()} | {show_cell} | {show_mail}"

    if lead_labels_by_id:
        st.markdown("#### Acoes rapidas por lead")
        q1, q2, q3, q4 = st.columns([4, 1.5, 1.5, 2])
        quick_ids = list(lead_labels_by_id.keys())
        quick_default = st.session_state.get("sales_lead_quick_pick", "")
        if quick_default not in quick_ids:
            st.session_state["sales_lead_quick_pick"] = quick_ids[0]
        with q1:
            quick_lead_id = st.selectbox(
                "Lead para acao rapida",
                quick_ids,
                key="sales_lead_quick_pick",
                format_func=lambda lid: lead_labels_by_id.get(lid, lid),
            )
        quick_lead = next(
            (
                l
                for l in filtrados
                if str(l.get("id", "")).strip() == str(quick_lead_id).strip()
            ),
            None,
        )
        quick_phone_digits = ""
        if isinstance(quick_lead, dict):
            quick_phone_raw = str(quick_lead.get("celular", "")).strip() or str(quick_lead.get("telefone", "")).strip()
            quick_phone_digits = re.sub(r"\D", "", quick_phone_raw)
        with q2:
            if st.button("Abrir ficha", key="sales_quick_open_detail_btn"):
                st.session_state["sales_lead_detail_id"] = str(quick_lead_id).strip()
                st.rerun()
        with q3:
            if quick_phone_digits:
                st.link_button(
                    "WhatsApp",
                    f"https://wa.me/{quick_phone_digits}",
                    key=f"sales_quick_wa_{quick_lead_id}",
                )
            else:
                st.caption("Sem celular")
        with q4:
            selected_quick_ids = st.session_state.get("sales_leads_bulk_selected_ids", [])
            if st.button("Selecionar em massa", key="sales_quick_add_bulk_btn"):
                updated = [sid for sid in selected_quick_ids if str(sid).strip() in lead_labels_by_id]
                if str(quick_lead_id).strip() not in updated:
                    updated.append(str(quick_lead_id).strip())
                st.session_state["sales_leads_bulk_selected_ids"] = updated
                st.rerun()

    st.markdown("### Acoes em massa")
    bulk_ids = [str(lead.get("id", "")).strip() for lead in filtrados if str(lead.get("id", "")).strip()]
    all_bulk_ids = [
        str(lead.get("id", "")).strip()
        for lead in st.session_state.get("sales_leads", [])
        if str(lead.get("id", "")).strip()
    ]
    all_lead_labels_by_id = {}
    for lead in st.session_state.get("sales_leads", []):
        lead_id = str(lead.get("id", "")).strip()
        if not lead_id:
            continue
        show_cell = str(lead.get("celular", "")).strip() or str(lead.get("telefone", "")).strip() or "-"
        show_mail = str(lead.get("email", "")).strip() or "-"
        all_lead_labels_by_id[lead_id] = f"{str(lead.get('nome', '')).strip()} | {show_cell} | {show_mail}"

    sr1, sr2 = st.columns([2, 1])
    with sr1:
        bulk_select_mode = st.selectbox(
            "Selecao rapida",
            ["Manual", "Todos da base", "Todos filtrados", "Limpar selecao"],
            key="sales_leads_bulk_select_mode",
        )
    with sr2:
        if st.button("Aplicar selecao", key="sales_leads_bulk_apply_select_mode"):
            if bulk_select_mode == "Todos da base":
                st.session_state["sales_leads_bulk_selected_ids"] = list(all_bulk_ids)
            elif bulk_select_mode == "Todos filtrados":
                st.session_state["sales_leads_bulk_selected_ids"] = list(bulk_ids)
            elif bulk_select_mode == "Limpar selecao":
                st.session_state["sales_leads_bulk_selected_ids"] = []
            st.rerun()

    selected_ids = st.multiselect(
        "Selecionar leads",
        all_bulk_ids,
        key="sales_leads_bulk_selected_ids",
        format_func=lambda lid: all_lead_labels_by_id.get(str(lid).strip(), str(lid).strip()),
    )

    qbulk1, qbulk2, qbulk3, qbulk4 = st.columns(4)
    with qbulk1:
        if st.button("Selecionar todos filtrados", key="sales_leads_bulk_select_all"):
            st.session_state["sales_leads_bulk_selected_ids"] = list(bulk_ids)
            st.rerun()
    with qbulk2:
        if st.button("Selecionar TODOS da base", key="sales_leads_bulk_select_all_base"):
            st.session_state["sales_leads_bulk_selected_ids"] = list(all_bulk_ids)
            st.rerun()
    with qbulk3:
        if st.button("Limpar selecao", key="sales_leads_bulk_clear"):
            st.session_state["sales_leads_bulk_selected_ids"] = []
            st.rerun()
    with qbulk4:
        st.caption(f"{len(selected_ids)} lead(s) selecionado(s)")

    st.markdown("#### Exclusao rapida em massa")
    d1, d2, d3 = st.columns([1.3, 1.2, 1.5])
    with d1:
        quick_delete_confirm = st.checkbox(
            "Confirmar exclusao",
            value=False,
            key="sales_leads_bulk_quick_delete_confirm",
        )
    with d2:
        st.caption("Acao permanente")
    with d3:
        if st.button(
            "Excluir selecionados agora",
            type="primary",
            key="sales_leads_bulk_quick_delete_btn",
            disabled=not bool(selected_ids),
        ):
            if not quick_delete_confirm:
                st.error("Marque a confirmacao para excluir.")
            else:
                before = len(st.session_state.get("sales_leads", []))
                st.session_state["sales_leads"] = [
                    l for l in st.session_state.get("sales_leads", [])
                    if str(l.get("id", "")).strip() not in selected_ids
                ]
                removed = before - len(st.session_state.get("sales_leads", []))
                save_list(SALES_LEADS_FILE, st.session_state["sales_leads"])
                st.session_state["sales_leads_bulk_selected_ids"] = []
                st.success(f"{removed} lead(s) excluido(s).")
                st.rerun()

    st.markdown("#### Limpeza total da base")
    t1, t2, t3 = st.columns([1.4, 1.2, 1.6])
    with t1:
        wipe_all_confirm = st.checkbox(
            "Confirmo apagar TODOS os leads",
            value=False,
            key="sales_leads_wipe_all_confirm",
        )
    with t2:
        wipe_all_confirm_2 = st.checkbox(
            "Confirmacao final",
            value=False,
            key="sales_leads_wipe_all_confirm_2",
        )
    with t3:
        if st.button(
            "Excluir TODOS os leads",
            type="primary",
            key="sales_leads_wipe_all_btn",
            disabled=not bool(st.session_state.get("sales_leads", [])),
        ):
            if not (wipe_all_confirm and wipe_all_confirm_2):
                st.error("Marque as duas confirmacoes para excluir todos os leads.")
            else:
                total_before = len(st.session_state.get("sales_leads", []))
                st.session_state["sales_leads"] = []
                st.session_state["sales_leads_bulk_selected_ids"] = []
                save_list(SALES_LEADS_FILE, st.session_state["sales_leads"])
                st.success(f"Base zerada com sucesso. {total_before} lead(s) excluido(s).")
                st.rerun()

    b1, b2 = st.columns(2)
    with b1:
        bulk_action = st.selectbox(
            "Acao",
            [
                "Atualizar status",
                "Atualizar estagio no funil",
                "Adicionar tag",
                "Remover tag",
                "Definir consultor",
                "Excluir selecionados",
            ],
            key="sales_leads_bulk_action",
        )
    with b2:
        if bulk_action == "Atualizar status":
            bulk_value = st.selectbox("Novo status", sales_lead_status_options(), key="sales_leads_bulk_value_status")
        elif bulk_action == "Atualizar estagio no funil":
            bulk_value = st.selectbox("Novo estagio", sales_pipeline_stage_options(), key="sales_leads_bulk_value_stage")
        elif bulk_action in ("Adicionar tag", "Remover tag"):
            bulk_value = st.text_input("Tag", key="sales_leads_bulk_value_tag")
        elif bulk_action == "Definir consultor":
            bulk_value = st.text_input("Nome do consultor", key="sales_leads_bulk_value_consultor")
        else:
            bulk_value = st.checkbox("Confirmo exclusao em massa", value=False, key="sales_leads_bulk_delete_confirm")

    if bulk_action == "Excluir selecionados":
        bx1, bx2, bx3 = st.columns(3)
        with bx1:
            if st.button("Selecionar TODOS para excluir", key="sales_leads_bulk_delete_select_all_visible"):
                st.session_state["sales_leads_bulk_selected_ids"] = list(all_bulk_ids)
                st.rerun()
        with bx2:
            if st.button("Selecionar filtrados para excluir", key="sales_leads_bulk_delete_select_filtered_visible"):
                st.session_state["sales_leads_bulk_selected_ids"] = list(bulk_ids)
                st.rerun()
        with bx3:
            if st.button("Limpar selecionados", key="sales_leads_bulk_delete_clear_visible"):
                st.session_state["sales_leads_bulk_selected_ids"] = []
                st.rerun()
        st.caption(f"Selecionados para exclusao: {len(st.session_state.get('sales_leads_bulk_selected_ids', []))}")

    if st.button("Aplicar acao em massa", type="primary", key="sales_leads_bulk_apply"):
        if not selected_ids:
            st.error("Selecione ao menos um lead.")
        else:
            changes = 0
            for lead in st.session_state.get("sales_leads", []):
                lead_id = str(lead.get("id", "")).strip()
                if lead_id not in selected_ids:
                    continue
                if bulk_action == "Atualizar status":
                    lead["status"] = str(bulk_value or "").strip()
                elif bulk_action == "Atualizar estagio no funil":
                    lead["estagio_funil"] = str(bulk_value or "").strip()
                elif bulk_action == "Adicionar tag":
                    tag_txt = str(bulk_value or "").strip()
                    if tag_txt:
                        lead["tags"] = _lead_tags_list(list(_lead_tags_list(lead.get("tags", []))) + [tag_txt])
                elif bulk_action == "Remover tag":
                    tag_txt = normalize_text(str(bulk_value or "").strip())
                    lead["tags"] = [t for t in _lead_tags_list(lead.get("tags", [])) if normalize_text(t) != tag_txt]
                elif bulk_action == "Definir consultor":
                    lead["vendedor"] = str(bulk_value or "").strip()
                elif bulk_action == "Excluir selecionados":
                    continue
                lead["updated_at"] = datetime.datetime.now().strftime("%d/%m/%Y %H:%M")
                changes += 1

            if bulk_action == "Excluir selecionados":
                if bulk_value is not True:
                    st.error("Marque a confirmacao para excluir.")
                else:
                    st.session_state["sales_leads"] = [
                        l for l in st.session_state.get("sales_leads", [])
                        if str(l.get("id", "")).strip() not in selected_ids
                    ]
                    save_list(SALES_LEADS_FILE, st.session_state["sales_leads"])
                    st.success(f"{len(selected_ids)} lead(s) excluido(s).")
                    st.rerun()
            elif changes > 0:
                save_list(SALES_LEADS_FILE, st.session_state["sales_leads"])
                st.success("Acoes em massa aplicadas com sucesso.")
                st.rerun()
            else:
                st.warning("Nenhuma alteracao aplicada.")

    if selected_ids:
        selected_rows = []
        for lead in st.session_state.get("sales_leads", []):
            if str(lead.get("id", "")).strip() in selected_ids:
                selected_rows.append(
                    {
                        "Nome": str(lead.get("nome", "")).strip(),
                        "Celular": str(lead.get("celular", "")).strip() or str(lead.get("telefone", "")).strip(),
                        "Telefone": str(lead.get("telefone", "")).strip(),
                        "Email": str(lead.get("email", "")).strip(),
                        "Status": str(lead.get("status", "")).strip(),
                        "Estagio no Funil": str(lead.get("estagio_funil", "")).strip(),
                        "Tags": _lead_tags_text(lead),
                    }
                )
        if selected_rows:
            selected_csv = pd.DataFrame(selected_rows).to_csv(index=False).encode("utf-8-sig")
            st.download_button(
                "Exportar selecionados (CSV)",
                data=selected_csv,
                file_name=f"leads_selecionados_{datetime.date.today().strftime('%Y%m%d')}.csv",
                mime="text/csv",
                key="sales_leads_export_selected",
            )

    st.markdown("### Ficha completa do lead")
    detail_by_id = {
        str(l.get("id", "")).strip(): l
        for l in filtrados
        if str(l.get("id", "")).strip()
    }
    detail_ids = list(detail_by_id.keys())
    if not detail_ids:
        st.info("Sem lead para detalhar com os filtros atuais.")
        return

    current_detail_id = str(st.session_state.get("sales_lead_detail_id", "")).strip()
    if current_detail_id not in detail_ids:
        st.session_state["sales_lead_detail_id"] = detail_ids[0]
    detail_id = st.selectbox(
        "Selecionar lead",
        detail_ids,
        key="sales_lead_detail_id",
        format_func=lambda lid: lead_labels_by_id.get(str(lid).strip(), str(lid).strip()),
    )
    lead_id = str(detail_id).strip()
    lead_obj = detail_by_id.get(lead_id, detail_by_id[detail_ids[0]])

    d1, d2, d3, d4 = st.columns(4)
    d1.metric("Status", str(lead_obj.get("status", "")).strip() or "-")
    d2.metric("Estagio", str(lead_obj.get("estagio_funil", "")).strip() or "-")
    d3.metric("Interacoes", str(len(lead_obj.get("interacoes", []))))
    d4.metric("Conversoes", str(len(lead_obj.get("conversoes", []))))

    info_tab, inter_tab, conv_tab = st.tabs(["Dados do lead", "Historico de interacoes", "Conversoes e paginas"])

    with info_tab:
        with st.form(f"sales_edit_lead_{lead_id}"):
            e1, e2 = st.columns(2)
            with e1:
                new_nome = st.text_input("Nome", value=str(lead_obj.get("nome", "")).strip())
            with e2:
                new_tel = st.text_input("Telefone", value=str(lead_obj.get("telefone", "")).strip() or str(lead_obj.get("celular", "")).strip())
            e3, e4, e5 = st.columns(3)
            with e3:
                new_email = st.text_input("E-mail", value=str(lead_obj.get("email", "")).strip())
            with e4:
                new_celular = st.text_input("Celular", value=str(lead_obj.get("celular", "")).strip() or str(lead_obj.get("telefone", "")).strip())
            with e5:
                status_atual = str(lead_obj.get("status", "Novo contato")).strip()
                new_status = st.selectbox(
                    "Status",
                    sales_lead_status_options(),
                    index=sales_lead_status_options().index(status_atual) if status_atual in sales_lead_status_options() else 0,
                )
            e5, e6 = st.columns(2)
            with e5:
                estagio_atual = str(lead_obj.get("estagio_funil", "Contato inicial")).strip()
                new_stage = st.selectbox(
                    "Estagio no funil",
                    sales_pipeline_stage_options(),
                    index=sales_pipeline_stage_options().index(estagio_atual) if estagio_atual in sales_pipeline_stage_options() else 0,
                )
            with e6:
                new_origem = st.text_input("Origem", value=str(lead_obj.get("origem", "")).strip())

            e7, e8, e9 = st.columns(3)
            with e7:
                new_cargo = st.text_input("Cargo", value=str(lead_obj.get("cargo", "")).strip())
            with e8:
                new_empresa = st.text_input("Empresa", value=str(lead_obj.get("empresa", "")).strip())
            with e9:
                new_interesse = st.text_input("Interesse", value=str(lead_obj.get("interesse", "")).strip())

            e10, e11, e12 = st.columns(3)
            with e10:
                new_cidade = st.text_input("Cidade", value=str(lead_obj.get("cidade", "")).strip())
            with e11:
                estado_atual = str(lead_obj.get("estado", "")).strip()
                new_estado = st.selectbox(
                    "Estado (UF)",
                    sales_state_options(),
                    index=sales_state_options().index(estado_atual) if estado_atual in sales_state_options() else 0,
                )
            with e12:
                new_consultor = st.text_input("Consultor", value=str(lead_obj.get("vendedor", "")).strip())

            new_tags = st.text_input("Tags", value=_lead_tags_text(lead_obj))
            new_obs = st.text_area("Observacoes", value=str(lead_obj.get("observacao", "")).strip())
            custom_txt = st.text_area(
                "Campos personalizados",
                value=_lead_custom_fields_to_text(lead_obj.get("campos_personalizados", {})),
                placeholder="campo: valor",
            )

            c_save, c_del = st.columns(2)
            with c_save:
                save_lead = st.form_submit_button("Salvar alteracoes")
            with c_del:
                delete_lead = st.form_submit_button("Excluir lead", type="primary")

            if save_lead:
                if not new_nome.strip() or (not str(new_tel or "").strip() and not str(new_celular or "").strip()):
                    st.error("Nome e celular/telefone sao obrigatorios.")
                else:
                    tel_final = str(new_tel or "").strip()
                    cel_final = str(new_celular or "").strip()
                    if not tel_final and cel_final:
                        tel_final = cel_final
                    if not cel_final and tel_final:
                        cel_final = tel_final
                    lead_obj["nome"] = new_nome.strip()
                    lead_obj["telefone"] = tel_final
                    lead_obj["celular"] = cel_final
                    lead_obj["email"] = new_email.strip().lower()
                    lead_obj["status"] = new_status
                    lead_obj["estagio_funil"] = new_stage
                    lead_obj["origem"] = new_origem.strip()
                    lead_obj["cargo"] = new_cargo.strip()
                    lead_obj["empresa"] = new_empresa.strip()
                    lead_obj["interesse"] = new_interesse.strip()
                    lead_obj["cidade"] = new_cidade.strip()
                    lead_obj["estado"] = new_estado.strip()
                    lead_obj["vendedor"] = new_consultor.strip()
                    lead_obj["tags"] = _lead_tags_list(new_tags)
                    lead_obj["observacao"] = new_obs.strip()
                    lead_obj["campos_personalizados"] = _lead_custom_fields_from_text(custom_txt)
                    lead_obj["updated_at"] = datetime.datetime.now().strftime("%d/%m/%Y %H:%M")
                    save_list(SALES_LEADS_FILE, st.session_state["sales_leads"])
                    st.success("Lead atualizado.")
                    st.rerun()
            if delete_lead:
                st.session_state["sales_leads"] = [
                    l for l in st.session_state.get("sales_leads", [])
                    if str(l.get("id", "")).strip() != lead_id
                ]
                save_list(SALES_LEADS_FILE, st.session_state["sales_leads"])
                st.success("Lead excluido.")
                st.rerun()

    with inter_tab:
        interacoes = lead_obj.get("interacoes", [])
        if interacoes:
            df_inter = pd.DataFrame(interacoes)
            col_order_inter = ["data_hora", "canal", "acao", "descricao", "pagina"]
            df_inter = df_inter[[c for c in col_order_inter if c in df_inter.columns]]
            st.dataframe(df_inter, use_container_width=True)
        else:
            st.info("Nenhuma interacao registrada para este lead.")

        with st.form(f"sales_add_interaction_{lead_id}", clear_on_submit=True):
            i1, i2, i3 = st.columns(3)
            with i1:
                data_inter = st.date_input("Data", value=datetime.date.today(), format="DD/MM/YYYY")
            with i2:
                hora_inter = st.time_input("Horario", value=datetime.datetime.now().time().replace(second=0, microsecond=0))
            with i3:
                canal_inter = st.selectbox("Canal", ["WhatsApp", "Ligacao", "E-mail", "Reuniao", "Landing Page", "Outro"])
            acao_inter = st.text_input("Acao", placeholder="Ex: Follow-up, envio de proposta, retorno do lead")
            desc_inter = st.text_area("Resumo da interacao")
            pagina_inter = st.text_input("Landing page visitada (opcional)")
            if st.form_submit_button("Registrar interacao", type="primary"):
                data_hora_inter = datetime.datetime.combine(data_inter, hora_inter).strftime("%d/%m/%Y %H:%M")
                if not str(acao_inter).strip():
                    st.error("Informe a acao da interacao.")
                else:
                    lead_obj.setdefault("interacoes", []).append(
                        {
                            "data_hora": data_hora_inter,
                            "canal": str(canal_inter or "").strip(),
                            "acao": str(acao_inter or "").strip(),
                            "descricao": str(desc_inter or "").strip(),
                            "pagina": str(pagina_inter or "").strip(),
                        }
                    )
                    page_clean = str(pagina_inter or "").strip()
                    if page_clean and page_clean not in lead_obj.get("landing_pages", []):
                        lead_obj.setdefault("landing_pages", []).append(page_clean)
                    lead_obj["ultimo_contato"] = data_hora_inter
                    lead_obj["updated_at"] = datetime.datetime.now().strftime("%d/%m/%Y %H:%M")
                    save_list(SALES_LEADS_FILE, st.session_state["sales_leads"])
                    st.success("Interacao registrada.")
                    st.rerun()

    with conv_tab:
        conversoes = lead_obj.get("conversoes", [])
        if conversoes:
            df_conv = pd.DataFrame(conversoes)
            col_order_conv = ["data", "tipo", "origem", "valor", "descricao"]
            df_conv = df_conv[[c for c in col_order_conv if c in df_conv.columns]]
            st.dataframe(df_conv, use_container_width=True)
        else:
            st.info("Nenhuma conversao registrada para este lead.")

        with st.form(f"sales_add_conversion_{lead_id}", clear_on_submit=True):
            c1, c2, c3 = st.columns(3)
            with c1:
                conv_data = st.date_input("Data da conversao", value=datetime.date.today(), format="DD/MM/YYYY")
            with c2:
                conv_tipo = st.selectbox("Tipo", ["Matricula", "Aula experimental", "Retorno", "Reuniao", "Outro"])
            with c3:
                conv_origem = st.text_input("Origem", value=str(lead_obj.get("origem", "")).strip())
            conv_valor = st.text_input("Valor (opcional)")
            conv_desc = st.text_area("Descricao")
            if st.form_submit_button("Registrar conversao", type="primary"):
                lead_obj.setdefault("conversoes", []).append(
                    {
                        "data": conv_data.strftime("%d/%m/%Y") if conv_data else "",
                        "tipo": str(conv_tipo or "").strip(),
                        "origem": str(conv_origem or "").strip(),
                        "valor": str(conv_valor or "").strip(),
                        "descricao": str(conv_desc or "").strip(),
                    }
                )
                lead_obj["updated_at"] = datetime.datetime.now().strftime("%d/%m/%Y %H:%M")
                save_list(SALES_LEADS_FILE, st.session_state["sales_leads"])
                st.success("Conversao registrada.")
                st.rerun()

        st.markdown("#### Landing pages visitadas")
        pages = [str(p).strip() for p in lead_obj.get("landing_pages", []) if str(p).strip()]
        if pages:
            st.dataframe(pd.DataFrame({"landing_page": pages}), use_container_width=True)
        else:
            st.caption("Sem landing pages registradas para este lead.")

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
        lead_views = ["Novo Lead", "Base de Leads (Dinamica)"]
        if st.session_state.get("sales_leads_view", "") not in lead_views:
            st.session_state["sales_leads_view"] = "Novo Lead"
        lead_view = st.radio(
            "Visualizacao",
            lead_views,
            horizontal=True,
            key="sales_leads_view",
        )

        import_flash = st.session_state.pop("sales_leads_import_flash", None)
        if isinstance(import_flash, dict) and bool(import_flash.get("ok")):
            stats_import = import_flash.get("stats", {}) if isinstance(import_flash.get("stats"), dict) else {}
            st.success(
                f"{str(import_flash.get('message', 'Importacao concluida.')).strip()} Linhas: {stats_import.get('total_linhas', 0)} | "
                f"Novos: {stats_import.get('cadastrados', 0)} | "
                f"Atualizados: {stats_import.get('atualizados', 0)} | "
                f"Ignorados: {stats_import.get('ignorados', 0)} | "
                f"Vazias: {stats_import.get('linhas_sem_dados', 0)}"
            )
            linhas_sem_dados = int(stats_import.get("linhas_sem_dados", 0) or 0)
            if linhas_sem_dados > 0:
                st.info(f"{linhas_sem_dados} linha(s) vazia(s) foram ignoradas automaticamente.")
            erros_import = import_flash.get("errors", [])
            if isinstance(erros_import, list) and erros_import:
                st.warning("Algumas linhas tiveram erro real de importacao.")
                st.dataframe(pd.DataFrame(erros_import), use_container_width=True)

        if lead_view == "Novo Lead":
            with st.expander("Importar lista de leads (cadastro automatico)", expanded=False):
                st.caption("Envie CSV, XLSX ou JSON para cadastrar leads em lote.")
                import_file = st.file_uploader(
                    "Arquivo da lista de leads",
                    type=["csv", "xlsx", "xls", "xlsb", "json"],
                    key="sales_leads_import_file",
                )
                i1, i2, i3 = st.columns(3)
                with i1:
                    origem_padrao_import = st.text_input(
                        "Origem padrao para linhas sem origem (opcional)",
                        key="sales_leads_import_origem_padrao",
                    )
                with i2:
                    atualizar_existentes = st.checkbox(
                        "Atualizar lead existente (telefone/e-mail)",
                        value=True,
                        key="sales_leads_import_update_existing",
                    )
                with i3:
                    usar_wiz_detect = st.checkbox(
                        "Wiz identificar nome/telefone",
                        value=True,
                        key="sales_leads_import_wiz_detect",
                    )
                st.caption("Importacao parcial habilitada: se vier nome, telefone ou e-mail, o lead sera cadastrado e voce pode completar depois.")
                if st.button("Importar e cadastrar leads automaticamente", type="primary", key="sales_leads_import_btn"):
                    if not import_file:
                        st.error("Selecione um arquivo para importar.")
                    else:
                        ok_import, msg_import, stats_import, erros_import = _sales_import_register_leads(
                            import_file,
                            vendedor_atual=vendedor_atual,
                            origem_padrao=origem_padrao_import,
                            atualizar_existentes=atualizar_existentes,
                            usar_wiz_detect=usar_wiz_detect,
                        )
                        if ok_import:
                            st.session_state["sales_leads_import_flash"] = {
                                "ok": True,
                                "message": str(msg_import or "Importacao concluida."),
                                "stats": stats_import,
                                "errors": erros_import,
                            }
                            st.session_state["sales_leads_view"] = "Base de Leads (Dinamica)"
                            st.rerun()
                        else:
                            st.error(msg_import)
            st.markdown("---")
            with st.form("sales_new_lead", clear_on_submit=True):
                c1, c2 = st.columns(2)
                with c1:
                    nome = st.text_input("Nome completo *")
                with c2:
                    telefone = st.text_input("Telefone / WhatsApp *")
                c3, c4, c5s = st.columns(3)
                with c3:
                    email = st.text_input("E-mail")
                with c4:
                    celular = st.text_input("Celular")
                with c5s:
                    status = st.selectbox("Status", sales_lead_status_options(), index=0)
                c5, c6, c7 = st.columns(3)
                with c5:
                    origem = st.text_input("Origem do lead (Instagram, indicacao, etc.)")
                with c6:
                    estagio_funil = st.selectbox("Estagio no funil", sales_pipeline_stage_options(), index=1)
                with c7:
                    interesse = st.text_input("Interesse / curso")
                c8, c9, c10, c11 = st.columns(4)
                with c8:
                    cargo = st.text_input("Cargo")
                with c9:
                    empresa = st.text_input("Empresa")
                with c10:
                    cidade = st.text_input("Cidade")
                with c11:
                    estado = st.selectbox("Estado (UF)", sales_state_options(), index=0)
                tags_raw = st.text_input("Tags (separadas por virgula)")
                observacao = st.text_area("Observacoes")
                campos_personalizados_txt = st.text_area(
                    "Campos personalizados (1 por linha: campo: valor)",
                    placeholder="Ex: faixa_etaria: adulto\ncanal_preferido: WhatsApp",
                )
                if st.form_submit_button("Cadastrar lead", type="primary"):
                    tel_final = str(telefone or "").strip()
                    cel_final = str(celular or "").strip()
                    if not tel_final and cel_final:
                        tel_final = cel_final
                    if not cel_final and tel_final:
                        cel_final = tel_final
                    if not nome.strip() or (not tel_final and not cel_final):
                        st.error("Informe nome e celular/telefone do lead.")
                    else:
                        created_at = datetime.datetime.now().strftime("%d/%m/%Y %H:%M")
                        tags_list = _lead_tags_list(tags_raw)
                        custom_fields = _lead_custom_fields_from_text(campos_personalizados_txt)
                        st.session_state["sales_leads"].append(
                            {
                                "id": uuid.uuid4().hex,
                                "nome": nome.strip(),
                                "telefone": tel_final,
                                "celular": cel_final,
                                "email": email.strip().lower(),
                                "status": status,
                                "estagio_funil": estagio_funil,
                                "origem": origem.strip(),
                                "interesse": interesse.strip(),
                                "cargo": cargo.strip(),
                                "empresa": empresa.strip(),
                                "cidade": cidade.strip(),
                                "estado": estado.strip(),
                                "tags": tags_list,
                                "campos_personalizados": custom_fields,
                                "observacao": observacao.strip(),
                                "vendedor": vendedor_atual,
                                "created_at": created_at,
                                "updated_at": "",
                                "ultimo_contato": "",
                                "interacoes": [
                                    {
                                        "data_hora": created_at,
                                        "canal": "Sistema",
                                        "acao": "Lead cadastrado",
                                        "descricao": "Registro inicial criado no Comercial.",
                                        "pagina": "",
                                    }
                                ],
                                "landing_pages": [],
                                "conversoes": [],
                            }
                        )
                        save_list(SALES_LEADS_FILE, st.session_state["sales_leads"])
                        st.success("Lead cadastrado com sucesso.")
                        st.rerun()

        else:
            render_sales_leads_manage(vendedor_atual)

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
                    c1, c2, c3 = st.columns(3)
                    with c1:
                        data_ag = st.date_input("Data (DD/MM/AAAA)", value=datetime.date.today(), format="DD/MM/YYYY")
                    with c2:
                        hora_ag = st.time_input("Horario inicial", value=datetime.time(10, 0))
                    with c3:
                        duracao_min = st.number_input("Duracao (min)", min_value=30, max_value=240, value=45, step=15)
                    st.caption(f"Data selecionada: {format_date_br(data_ag)}")
                    meeting_link = st.text_input("Link da reuniao (Google Meet/Zoom) - opcional")
                    detalhes = st.text_area("Detalhes")
                    c4, c5 = st.columns(2)
                    with c4:
                        send_auto = st.checkbox("Enviar no WhatsApp automaticamente ao salvar", value=True)
                    with c5:
                        add_google = st.checkbox("Gerar link no Google Agenda", value=True)
                    if st.form_submit_button("Salvar agendamento", type="primary"):
                        item = {
                            "id": uuid.uuid4().hex,
                            "lead_id": str(lead_obj.get("id", "")).strip(),
                            "lead_nome": str(lead_obj.get("nome", "")).strip(),
                            "lead_telefone": str(lead_obj.get("telefone", "")).strip(),
                            "tipo": tipo,
                            "data": data_ag.strftime("%d/%m/%Y") if data_ag else "",
                            "hora": hora_ag.strftime("%H:%M") if hora_ag else "",
                            "duracao_minutos": int(duracao_min or 45),
                            "detalhes": str(detalhes or "").strip(),
                            "meeting_link": str(meeting_link or "").strip(),
                            "status": "Agendado",
                            "vendedor": vendedor_atual,
                            "created_at": datetime.datetime.now().strftime("%d/%m/%Y %H:%M"),
                            "whatsapp_sent": False,
                            "whatsapp_status": "",
                        }
                        if add_google:
                            item["google_calendar_link"] = build_sales_google_calendar_event_link(item)
                        if send_auto:
                            ok, status, _ = _send_sales_schedule_whatsapp(lead_obj, item)
                            item["whatsapp_sent"] = bool(ok)
                            item["whatsapp_status"] = str(status or "")
                        st.session_state["sales_agenda"].append(item)
                        save_list(SALES_AGENDA_FILE, st.session_state["sales_agenda"])
                        st.success("Agendamento salvo.")
                        gcal = str(item.get("google_calendar_link", "")).strip()
                        if gcal:
                            st.markdown(f"[Abrir no Google Agenda]({gcal})")

        with tab_list:
            agenda = st.session_state.get("sales_agenda", [])
            if not agenda:
                st.info("Nenhum agendamento cadastrado.")
            else:
                agenda_changed = False
                for item in agenda:
                    if not isinstance(item, dict):
                        continue
                    if parse_int(item.get("duracao_minutos", 0)) <= 0:
                        item["duracao_minutos"] = 45
                        agenda_changed = True
                    if "meeting_link" not in item:
                        item["meeting_link"] = ""
                        agenda_changed = True
                    if not str(item.get("google_calendar_link", "")).strip():
                        item["google_calendar_link"] = build_sales_google_calendar_event_link(item)
                        agenda_changed = True
                if agenda_changed:
                    save_list(SALES_AGENDA_FILE, st.session_state["sales_agenda"])

                hoje = datetime.date.today()
                semana_ini = hoje - datetime.timedelta(days=hoje.weekday())
                semana_fim = semana_ini + datetime.timedelta(days=6)
                total_itens = len(agenda)
                total_hoje = sum(1 for a in agenda if (parse_date(a.get("data", "")) == hoje))
                total_semana = sum(
                    1 for a in agenda
                    if (parse_date(a.get("data", "")) is not None and semana_ini <= parse_date(a.get("data", "")) <= semana_fim)
                )
                total_pendentes = sum(1 for a in agenda if str(a.get("status", "")).strip() == "Agendado")

                m1, m2, m3, m4 = st.columns(4)
                with m1:
                    st.markdown(f"**Total**  \n### {total_itens}")
                with m2:
                    st.markdown(f"**Hoje**  \n### {total_hoje}")
                with m3:
                    st.markdown(f"**Esta semana**  \n### {total_semana}")
                with m4:
                    st.markdown(f"**Pendentes**  \n### {total_pendentes}")

                f1, f2, f3, f4 = st.columns(4)
                with f1:
                    tipo_filtro = st.selectbox("Tipo", ["Todos"] + sales_agenda_type_options(), key="sales_agenda_tipo_filtro")
                with f2:
                    status_filtro = st.selectbox("Status", ["Todos", "Agendado", "Concluido", "Cancelado"], key="sales_agenda_status_filtro")
                with f3:
                    data_ini = st.date_input("De (DD/MM/AAAA)", value=hoje - datetime.timedelta(days=7), format="DD/MM/YYYY", key="sales_agenda_data_ini")
                with f4:
                    data_fim = st.date_input("Ate (DD/MM/AAAA)", value=hoje + datetime.timedelta(days=30), format="DD/MM/YYYY", key="sales_agenda_data_fim")
                busca = st.text_input("Buscar por lead, telefone ou detalhes", key="sales_agenda_busca")
                st.caption(f"Periodo aplicado: {format_date_br(data_ini)} ate {format_date_br(data_fim)}")

                agenda_filtrada = []
                busca_norm = normalize_text(busca)
                for a in agenda:
                    if not isinstance(a, dict):
                        continue
                    if tipo_filtro != "Todos" and str(a.get("tipo", "")).strip() != tipo_filtro:
                        continue
                    if status_filtro != "Todos" and str(a.get("status", "")).strip() != status_filtro:
                        continue
                    dt_item = parse_date(a.get("data", ""))
                    if dt_item and (dt_item < data_ini or dt_item > data_fim):
                        continue
                    texto_busca = " ".join(
                        [
                            str(a.get("lead_nome", "")),
                            str(a.get("lead_telefone", "")),
                            str(a.get("tipo", "")),
                            str(a.get("detalhes", "")),
                        ]
                    )
                    if busca_norm and busca_norm not in normalize_text(texto_busca):
                        continue
                    agenda_filtrada.append(a)

                agenda_filtrada = sorted(
                    agenda_filtrada,
                    key=lambda a: (
                        parse_date(a.get("data", "")) or datetime.date(2100, 1, 1),
                        parse_time(a.get("hora", "00:00")),
                    ),
                )

                with st.expander("Visao dinamica da agenda (Google integrado)", expanded=True):
                    if agenda_filtrada:
                        view_rows = []
                        for ag in agenda_filtrada:
                            view_rows.append(
                                {
                                    "Data": format_date_br(ag.get("data", "")),
                                    "Horario": str(ag.get("hora", "")).strip(),
                                    "Duracao (min)": parse_int(ag.get("duracao_minutos", 45)) or 45,
                                    "Lead": str(ag.get("lead_nome", "")).strip(),
                                    "Telefone": str(ag.get("lead_telefone", "")).strip(),
                                    "Tipo": str(ag.get("tipo", "")).strip(),
                                    "Status": str(ag.get("status", "")).strip(),
                                    "Reuniao": str(ag.get("meeting_link", "")).strip(),
                                    "Google Agenda": str(ag.get("google_calendar_link", "")).strip(),
                                    "Consultor": str(ag.get("vendedor", "")).strip(),
                                }
                            )
                        df_agenda_view = pd.DataFrame(view_rows)
                        if hasattr(st, "column_config"):
                            st.data_editor(
                                df_agenda_view,
                                use_container_width=True,
                                hide_index=True,
                                disabled=True,
                                column_config={
                                    "Reuniao": st.column_config.LinkColumn("Reuniao"),
                                    "Google Agenda": st.column_config.LinkColumn("Google Agenda"),
                                },
                                key="sales_agenda_dynamic_table",
                            )
                        else:
                            st.dataframe(df_agenda_view, use_container_width=True)
                    else:
                        st.caption("Sem registros para a grade dinamica.")

                if not agenda_filtrada:
                    st.info("Nenhum item na agenda para os filtros selecionados.")
                else:
                    st.caption(f"Exibindo {len(agenda_filtrada)} agendamento(s).")
                    status_colors = {
                        "Agendado": "#1e3a8a",
                        "Concluido": "#15803d",
                        "Cancelado": "#c2410c",
                    }
                    for ag_obj in agenda_filtrada:
                        ag_id = str(ag_obj.get("id", "")).strip() or uuid.uuid4().hex
                        status = str(ag_obj.get("status", "Agendado")).strip() or "Agendado"
                        cor = status_colors.get(status, "#334155")
                        data_txt = format_date_br(ag_obj.get("data", ""))
                        hora_txt = str(ag_obj.get("hora", "")).strip() or "--:--"
                        duracao_txt = parse_int(ag_obj.get("duracao_minutos", 45)) or 45
                        lead_nome = str(ag_obj.get("lead_nome", "")).strip() or "Lead"
                        lead_tel = str(ag_obj.get("lead_telefone", "")).strip()
                        tipo_txt = str(ag_obj.get("tipo", "Agendamento")).strip()
                        detalhes_txt = str(ag_obj.get("detalhes", "")).strip()
                        vendedor_txt = str(ag_obj.get("vendedor", "")).strip()
                        meeting_link = str(ag_obj.get("meeting_link", "")).strip()
                        google_link = str(ag_obj.get("google_calendar_link", "")).strip() or build_sales_google_calendar_event_link(ag_obj)
                        if google_link and not str(ag_obj.get("google_calendar_link", "")).strip():
                            ag_obj["google_calendar_link"] = google_link
                            save_list(SALES_AGENDA_FILE, st.session_state["sales_agenda"])

                        st.markdown(
                            f"""
<div style="border:1px solid #dbe7f6;border-left:6px solid {cor};border-radius:12px;padding:14px 16px;margin:10px 0;background:#ffffff;">
  <div style="display:flex;justify-content:space-between;gap:12px;align-items:center;">
    <div style="font-weight:700;color:#0f172a;">{tipo_txt} - {lead_nome}</div>
    <div style="font-weight:700;color:{cor};">{status}</div>
  </div>
  <div style="margin-top:4px;color:#334155;">{data_txt} | {hora_txt} | {duracao_txt} min</div>
  <div style="margin-top:4px;color:#475569;">Telefone: {lead_tel or "-"}</div>
  <div style="margin-top:4px;color:#475569;">Vendedor: {vendedor_txt or "-"}</div>
  <div style="margin-top:4px;color:#475569;">Detalhes: {detalhes_txt or "-"}</div>
</div>
""",
                            unsafe_allow_html=True,
                        )

                        a1, a2, a3, a4, a5 = st.columns([1, 1, 1.1, 1.2, 1.2])
                        if a1.button("Concluir", key=f"sales_ag_done_{ag_id}"):
                            ag_obj["status"] = "Concluido"
                            save_list(SALES_AGENDA_FILE, st.session_state["sales_agenda"])
                            st.success("Agenda atualizada.")
                            st.rerun()
                        if a2.button("Cancelar", key=f"sales_ag_cancel_{ag_id}"):
                            ag_obj["status"] = "Cancelado"
                            save_list(SALES_AGENDA_FILE, st.session_state["sales_agenda"])
                            st.success("Agenda atualizada.")
                            st.rerun()
                        if a3.button("Reenviar WhatsApp", key=f"sales_ag_wa_{ag_id}"):
                            lead_ref = next(
                                (l for l in st.session_state.get("sales_leads", []) if str(l.get("id", "")).strip() == str(ag_obj.get("lead_id", "")).strip()),
                                {"nome": ag_obj.get("lead_nome", ""), "telefone": ag_obj.get("lead_telefone", "")},
                            )
                            ok, status_wa, _ = _send_sales_schedule_whatsapp(lead_ref, ag_obj)
                            ag_obj["whatsapp_sent"] = bool(ok)
                            ag_obj["whatsapp_status"] = str(status_wa or "")
                            save_list(SALES_AGENDA_FILE, st.session_state["sales_agenda"])
                            if ok:
                                st.success("Mensagem enviada no WhatsApp.")
                            else:
                                st.error(f"Falha ao enviar WhatsApp: {status_wa}")
                            st.rerun()
                        if meeting_link:
                            a4.markdown(f"[Abrir reuniao]({meeting_link})")
                        else:
                            a4.button("Abrir reuniao", disabled=True, key=f"sales_ag_meet_disabled_{ag_id}")
                        if google_link:
                            a5.markdown(f"[Google Agenda]({google_link})")
                        else:
                            a5.button("Google Agenda", disabled=True, key=f"sales_ag_gcal_disabled_{ag_id}")

                    with st.expander("Ver tabela completa", expanded=False):
                        df_ag = pd.DataFrame(agenda_filtrada)
                        col_order = [
                            "data",
                            "hora",
                            "duracao_minutos",
                            "lead_nome",
                            "lead_telefone",
                            "tipo",
                            "status",
                            "whatsapp_sent",
                            "whatsapp_status",
                            "meeting_link",
                            "google_calendar_link",
                            "detalhes",
                            "vendedor",
                        ]
                        df_ag = df_ag[[c for c in col_order if c in df_ag.columns]]
                        st.dataframe(df_ag, use_container_width=True)

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
                    fail_details = []
                    for label in selected:
                        lead_obj = leads_filtrados[labels.index(label)]
                        number = _lead_phone_for_whatsapp(lead_obj)
                        if not number:
                            fail_count += 1
                            fail_details.append(
                                {
                                    "lead": str(lead_obj.get("nome", "")).strip() or "(sem nome)",
                                    "telefone": str(lead_obj.get("telefone", "")).strip(),
                                    "erro": "telefone invalido ou ausente",
                                }
                            )
                            continue
                        total += 1
                        ok, status, attempts = _send_whatsapp_auto(number, str(mensagem).strip())
                        if ok:
                            ok_count += 1
                            lead_obj["ultimo_contato"] = datetime.datetime.now().strftime("%d/%m/%Y %H:%M")
                            lead_obj["updated_at"] = lead_obj["ultimo_contato"]
                            lead_obj["ultimo_erro_whatsapp"] = ""
                        else:
                            fail_count += 1
                            lead_obj["ultimo_erro_whatsapp"] = str(status or "")
                            last_attempt = attempts[-1] if isinstance(attempts, list) and attempts else {}
                            fail_details.append(
                                {
                                    "lead": str(lead_obj.get("nome", "")).strip() or "(sem nome)",
                                    "telefone": number,
                                    "erro": str(status or "falha desconhecida"),
                                    "http": str(last_attempt.get("status", "") or ""),
                                    "endpoint": str(last_attempt.get("url", last_attempt.get("path", "")) or "")[:120],
                                }
                            )
                    save_list(SALES_LEADS_FILE, st.session_state["sales_leads"])
                    st.success(f"Envio concluido. Sucesso: {ok_count} | Falhas: {fail_count} | Tentativas: {total}")
                    if fail_details:
                        st.warning("Alguns envios falharam. Veja os detalhes abaixo.")
                        st.dataframe(pd.DataFrame(fail_details), use_container_width=True)

    elif menu_sales == "Professor Wiz":
        run_active_chatbot()

restore_login_from_query()

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
        :root { --sidebar-width: 336px; --sidebar-menu-btn-width: 300px; }
        section[data-testid="stAppViewContainer"] { background: #eef5ff; }
        .main-header { font-family: 'Sora', sans-serif; font-size: 1.8rem; font-weight: 700; color: #1e3a8a; margin-bottom: 20px; }
        section[data-testid="stSidebar"] { background-color: #f3f8ff; border-right: 1px solid #dbe7f6; box-shadow: 2px 0 10px rgba(15,23,42,0.04); min-width: var(--sidebar-width) !important; max-width: var(--sidebar-width) !important; }
        section[data-testid="stSidebar"] .stButton { width: var(--sidebar-menu-btn-width) !important; min-width: var(--sidebar-menu-btn-width) !important; max-width: var(--sidebar-menu-btn-width) !important; margin-right: auto; }
        section[data-testid="stSidebar"] .stButton > button { background: linear-gradient(135deg, rgba(37,99,235,0.08) 0%, rgba(16,185,129,0.08) 100%); border: 1px solid #d3e0f3; color: #334155; text-align: left; font-weight: 700; padding: 0 0.9rem; width: var(--sidebar-menu-btn-width) !important; min-width: var(--sidebar-menu-btn-width) !important; max-width: var(--sidebar-menu-btn-width) !important; border-radius: 13px; transition: all 0.2s ease; margin-bottom: 7px; box-shadow: 0 4px 12px rgba(15, 23, 42, 0.05); height: 48px !important; min-height: 48px !important; max-height: 48px !important; display: flex; align-items: center; justify-content: flex-start; box-sizing: border-box; white-space: nowrap; overflow: visible; text-overflow: clip; }
        section[data-testid="stSidebar"] .stButton > button p { margin: 0 !important; line-height: 1 !important; white-space: nowrap !important; overflow: visible !important; text-overflow: clip !important; }
        section[data-testid="stSidebar"] .stButton > button:active { transform: none !important; }
        section[data-testid="stSidebar"] .stButton > button[data-testid="stBaseButton-secondary"] { height: 48px !important; }
        section[data-testid="stSidebar"] .stButton > button[data-testid="stBaseButton-primary"] { height: 48px !important; }
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
        .finance-radio-anchor { display:none; }
        div[data-testid="stVerticalBlock"]:has(.finance-radio-anchor) div[data-testid="stRadio"] [role="radiogroup"] {
            display: flex;
            flex-wrap: wrap;
            gap: 8px;
        }
        div[data-testid="stVerticalBlock"]:has(.finance-radio-anchor) div[data-testid="stRadio"] [role="radiogroup"] > label {
            background: #ffffff;
            border: 1px solid #dbe5f2;
            border-radius: 12px;
            padding: 7px 12px;
            box-shadow: 0 3px 10px rgba(15, 23, 42, 0.05);
            margin: 0 !important;
            transition: all 0.2s ease;
        }
        div[data-testid="stVerticalBlock"]:has(.finance-radio-anchor) div[data-testid="stRadio"] [role="radiogroup"] > label:hover {
            border-color: #93c5fd;
            transform: translateY(-1px);
        }
        div[data-testid="stVerticalBlock"]:has(.finance-radio-anchor) div[data-testid="stRadio"] [role="radiogroup"] > label:has(input:checked) {
            background: linear-gradient(90deg, #1d4ed8 0%, #0f766e 100%);
            border-color: #1d4ed8;
            color: #ffffff;
            box-shadow: 0 8px 18px rgba(29, 78, 216, 0.25);
        }
        div[data-testid="stVerticalBlock"]:has(.finance-radio-anchor) div[data-testid="stRadio"] [role="radiogroup"] > label:has(input:checked) p {
            color: #ffffff !important;
            font-weight: 700;
        }
        div[data-testid="stDataFrame"] { background: white; padding: 16px; border-radius: 12px; border: 1px solid #e2e8f0; box-shadow: 0 2px 8px rgba(0,0,0,0.02); margin-bottom: 16px; }
        div[data-testid="stForm"] { background: white; padding: 30px; border-radius: 16px; border: 1px solid #e2e8f0; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05); margin-bottom: 20px; }
        div[data-baseweb="tag"] {
            background: #e8f1ff !important;
            border: 1px solid #bfd7ff !important;
            border-radius: 10px !important;
            box-shadow: inset 0 0 0 1px rgba(59, 130, 246, 0.06);
        }
        div[data-baseweb="tag"] span,
        div[data-baseweb="tag"] p {
            color: #1e3a8a !important;
            font-weight: 700 !important;
        }
        div[data-baseweb="tag"] button {
            background: transparent !important;
            border: none !important;
            box-shadow: none !important;
            color: #2563eb !important;
        }
        div[data-baseweb="tag"] button:hover {
            background: rgba(37, 99, 235, 0.12) !important;
            border-radius: 8px !important;
        }
        div[data-baseweb="tag"] svg {
            color: #2563eb !important;
        }
        div[data-baseweb="tag"]:hover {
            background: #dbeafe !important;
            border-color: #93c5fd !important;
        }
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
    st.session_state["finance_settings"] = _load_json_dict(FINANCE_SETTINGS_FILE, DEFAULT_FINANCE_SETTINGS)
    st.session_state["_active_users_loaded"] = True

remote_handled, remote_msg = process_wiz_remote_control_from_query()
if remote_handled:
    st.session_state["wiz_remote_control_notice"] = remote_msg or "Comando remoto processado."
elif remote_msg:
    st.session_state["wiz_remote_control_notice"] = remote_msg

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

    books_before = st.session_state.get("books", [])
    books_normalized = ensure_library_catalog(books_before)
    if books_before != books_normalized:
        st.session_state["books"] = books_normalized
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
                    login_user(role, display_name, str(unidade).strip(), perfil_conta, usuario.strip())

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
        aluno_sidebar_obj = next(
            (s for s in st.session_state.get("students", []) if s.get("nome") == st.session_state.get("user_name", "")),
            {},
        )
        nivel_aluno_sidebar = student_book_level(aluno_sidebar_obj) or "Sem nivel definido"
        st.info(f"Nível: {nivel_aluno_sidebar}")
        st.markdown("---")
        menu_aluno_label = sidebar_menu(
            "Navegacao",
            [
                "Painel",
                "Agenda",
                "Minhas Aulas",
                "Boletim e Frequencia",
                "Mensagens",
                "Atividades",
                "Lições de Casa",
                "Desafios",
                "Aulas Gravadas",
                "Financeiro",
                "Materiais de Estudo",
                "Professor Wiz",
            ],
            "menu_aluno",
        )
        st.markdown("---")
        st.markdown('<div class="logout-btn">', unsafe_allow_html=True)
        if st.button("Sair"): logout_user()
        st.markdown('</div>', unsafe_allow_html=True)

    menu_aluno_map = {
        "Painel": "Dashboard",
        "Agenda": "Agenda",
        "Minhas Aulas": "Minhas Aulas",
        "Boletim e Frequencia": "Boletim & Frequencia",
        "Mensagens": "Mensagens",
        "Atividades": "Atividades",
        "Lições de Casa": "Atividades",
        "Desafios": "Desafios",
        "Aulas Gravadas": "Aulas Gravadas",
        "Financeiro": "Financeiro",
        "Materiais de Estudo": "Materiais de Estudo",
        "Professor Wiz": "Professor Wiz",
    }
    menu_aluno = menu_aluno_map.get(menu_aluno_label, "Dashboard")

    if menu_aluno == "Dashboard":
        st.markdown('<div class="main-header">Painel do Aluno</div>', unsafe_allow_html=True)
        aluno_nome = st.session_state.get("user_name", "")
        aluno_obj = next((s for s in st.session_state.get("students", []) if s.get("nome") == aluno_nome), {})
        link_aula = "https://zoom.us/join"
        turma_aluno = str(aluno_obj.get("turma", "")).strip()
        turma_obj = {}
        if turma_aluno:
            turma_obj = next((c for c in st.session_state["classes"] if c["nome"] == turma_aluno), None)
            if turma_obj and "link_zoom" in turma_obj: link_aula = turma_obj["link_zoom"]
        st.error("AULA AO VIVO AGORA")
        st.link_button("ENTRAR NA AULA (ZOOM)", link_aula, type="primary")

        mensagens_aluno_dashboard = [
            m for m in st.session_state.get("messages", [])
            if _message_matches_student(m, aluno_nome, turma_aluno)
        ]
        lidas_ids = _student_read_message_ids(aluno_obj)
        mensagens_nao_lidas = [
            m for m in mensagens_aluno_dashboard
            if _message_uid(m) not in lidas_ids
        ]
        semana_atual_dashboard = current_week_key()
        desafios_dashboard = get_student_weekly_challenges(aluno_obj, semana_atual_dashboard)
        desafios_pendentes = [
            ch for ch in desafios_dashboard
            if not get_challenge_submission(str(ch.get("id", "")).strip(), aluno_nome)
        ]
        atividades_turma_dashboard = [
            a for a in st.session_state.get("activities", [])
            if str(a.get("turma", "")).strip() == turma_aluno and _is_activity_open(a)
        ]
        atividades_pendentes = [
            a for a in atividades_turma_dashboard
            if not get_activity_submission(str(a.get("id", "")).strip(), aluno_nome)
        ]
        total_notificacoes = len(mensagens_nao_lidas) + len(desafios_pendentes) + len(atividades_pendentes)
        if total_notificacoes > 0:
            st.warning(f"Você tem {total_notificacoes} notificacao(oes) pendente(s).")
            n1, n2, n3 = st.columns(3)
            with n1:
                st.metric("Desafios pendentes", len(desafios_pendentes))
            with n2:
                st.metric("Tarefas pendentes", len(atividades_pendentes))
            with n3:
                st.metric("Mensagens nao lidas", len(mensagens_nao_lidas))
            if desafios_pendentes:
                st.caption("Desafios: " + " | ".join(str(ch.get("titulo", "Desafio")).strip() for ch in desafios_pendentes[:3]))
            if atividades_pendentes:
                st.caption("Tarefas: " + " | ".join(str(a.get("titulo", "Atividade")).strip() for a in atividades_pendentes[:3]))
            if mensagens_nao_lidas:
                st.caption("Mensagens: " + " | ".join(str(m.get("titulo", "Mensagem")).strip() for m in mensagens_nao_lidas[:3]))
        else:
            st.success("Sem pendencias no momento: desafios, tarefas e mensagens em dia.")

        sessoes_finalizadas = [
            s for s in st.session_state.get("class_sessions", [])
            if str(s.get("turma", "")).strip() == turma_aluno
            and str(s.get("status", "")).strip().lower() == "finalizada"
        ]
        total_aulas_turma = len(sessoes_finalizadas)

        notas_aluno_aprovadas = [
            g for g in st.session_state.get("grades", [])
            if str(g.get("aluno", "")).strip() == aluno_nome
            and str(g.get("status", "")).strip().lower() == "aprovado"
        ]
        notas_numericas = []
        presencas_percent = []
        for nota_obj in notas_aluno_aprovadas:
            nota_txt = str(nota_obj.get("nota", "")).strip()
            if not nota_txt:
                continue
            match_num = re.search(r"-?\d+(?:[.,]\d+)?", nota_txt)
            if not match_num:
                continue
            valor_nota = _parse_float(match_num.group(0), default=0.0)
            avaliacao_norm = normalize_text(nota_obj.get("avaliacao", ""))
            if "%" in nota_txt or "presenca" in avaliacao_norm:
                presencas_percent.append(max(0.0, min(100.0, valor_nota)))
            elif 0.0 <= valor_nota <= 10.0:
                notas_numericas.append(valor_nota)

        presenca_media = (sum(presencas_percent) / len(presencas_percent)) if presencas_percent else None
        if total_aulas_turma > 0:
            fator_presenca = (presenca_media / 100.0) if presenca_media is not None else 1.0
            aulas_assistidas = int(round(total_aulas_turma * fator_presenca))
            aulas_assistidas = max(0, min(total_aulas_turma, aulas_assistidas))
            aulas_label = f"{aulas_assistidas}/{total_aulas_turma}"
            aulas_percent_label = f"{(aulas_assistidas / total_aulas_turma) * 100:.0f}%"
        else:
            aulas_label = "--"
            aulas_percent_label = f"{presenca_media:.0f}%" if presenca_media is not None else "Sem dados"

        media_geral = (sum(notas_numericas) / len(notas_numericas)) if notas_numericas else None
        media_label = f"{media_geral:.1f}" if media_geral is not None else "--"
        media_sub_label = f"{len(notas_numericas)} avaliacao(oes)" if notas_numericas else "Sem notas aprovadas"

        provas_futuras = []
        hoje = datetime.date.today()
        for nota_obj in st.session_state.get("grades", []):
            if str(nota_obj.get("aluno", "")).strip() != aluno_nome:
                continue
            avaliacao_txt = str(nota_obj.get("avaliacao", "")).strip()
            avaliacao_norm = normalize_text(avaliacao_txt)
            if "prova" not in avaliacao_norm and "test" not in avaliacao_norm:
                continue
            data_prova = parse_date(nota_obj.get("data", ""))
            if data_prova and data_prova >= hoje:
                provas_futuras.append((data_prova, avaliacao_txt or "Prova"))
        if not provas_futuras and turma_aluno:
            for agenda_obj in st.session_state.get("agenda", []):
                if str(agenda_obj.get("turma", "")).strip() != turma_aluno:
                    continue
                titulo_agenda = str(agenda_obj.get("titulo", "")).strip()
                titulo_norm = normalize_text(titulo_agenda)
                if "prova" not in titulo_norm and "test" not in titulo_norm:
                    continue
                data_agenda = parse_date(agenda_obj.get("data", ""))
                if data_agenda and data_agenda >= hoje:
                    provas_futuras.append((data_agenda, titulo_agenda or "Prova"))
        provas_futuras = sorted(provas_futuras, key=lambda item: item[0])
        if provas_futuras:
            proxima_prova_data, proxima_prova_titulo = provas_futuras[0]
            proxima_prova_data_label = proxima_prova_data.strftime("%d/%m")
            proxima_prova_titulo_label = proxima_prova_titulo
        else:
            proxima_prova_data_label = "--"
            proxima_prova_titulo_label = "Sem prova agendada"

        st.markdown("<br>", unsafe_allow_html=True)
        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown(
                f"""<div class="dash-card"><div><div class="card-title">Aulas Assistidas</div><div class="card-value">{aulas_label}</div></div><div class="card-sub"><span class="trend-up">{aulas_percent_label}</span> <span class="trend-neutral">da sua turma</span></div></div>""",
                unsafe_allow_html=True,
            )
        with col2:
            st.markdown(
                f"""<div class="dash-card"><div><div class="card-title">Média Geral</div><div class="card-value">{media_label}</div></div><div class="card-sub"><span class="trend-neutral">{media_sub_label}</span></div></div>""",
                unsafe_allow_html=True,
            )
        with col3:
            st.markdown(
                f"""<div class="dash-card"><div><div class="card-title">Próxima Prova</div><div class="card-value">{proxima_prova_data_label}</div></div><div class="card-sub"><span style="color:#64748b">{proxima_prova_titulo_label}</span></div></div>""",
                unsafe_allow_html=True,
            )
        vip_resumo_dashboard = _student_vip_summary(aluno_obj)
        if vip_resumo_dashboard:
            st.info(
                f"Plano VIP: {vip_resumo_dashboard.get('plano', '-')} | "
                f"Aulas restantes: {int(vip_resumo_dashboard.get('restantes', 0))}/{int(vip_resumo_dashboard.get('total', 0))}"
            )
        if isinstance(turma_obj, dict) and turma_obj:
            st.caption(
                f"Turma: {turma_aluno or '-'} | Modulo: {str(turma_obj.get('modulo', '')).strip() or '-'} | "
                f"Livro/Nivel: {student_book_level(aluno_obj) or str(turma_obj.get('livro', '')).strip() or '-'}"
            )

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
        aluno_nome = st.session_state.get("user_name", "")
        aluno_obj = next((s for s in st.session_state.get("students", []) if s.get("nome") == aluno_nome), {})
        turma_aluno = str(aluno_obj.get("turma", "")).strip()
        if not turma_aluno:
            st.info("Seu usuario nao esta vinculado a uma turma.")
        else:
            turma_obj = next(
                (c for c in st.session_state.get("classes", []) if str(c.get("nome", "")).strip() == turma_aluno),
                {},
            )
            livro_aluno = student_book_level(aluno_obj) or str(turma_obj.get("livro", "")).strip()
            c_grade_1, c_grade_2, c_grade_3 = st.columns(3)
            with c_grade_1:
                st.metric("Turma", turma_aluno)
            with c_grade_2:
                st.metric("Modulo", str(turma_obj.get("modulo", "")).strip() or "-")
            with c_grade_3:
                st.metric("Livro/Nivel", livro_aluno or "-")
            dias_grade = str(turma_obj.get("dias", "")).strip()
            if dias_grade:
                st.caption(f"Grade da turma: {dias_grade}")
            link_turma = str(turma_obj.get("link_zoom", "")).strip()
            if link_turma:
                st.link_button("Entrar na aula da turma (Zoom)", link_turma)

            st.markdown("### Conteudos e materias salvos pelo professor")
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
                for sessao in historico_aulas[:20]:
                    data_label = str(sessao.get("data", "")).strip() or "-"
                    titulo_label = str(sessao.get("titulo", "")).strip() or "Aula"
                    with st.expander(f"{data_label} | {titulo_label}", expanded=False):
                        professor_label = str(sessao.get("professor", "")).strip() or "-"
                        hora_inicio = str(sessao.get("hora_inicio_real", sessao.get("hora_inicio_prevista", ""))).strip()
                        hora_fim = str(sessao.get("hora_fim_real", sessao.get("hora_fim_prevista", ""))).strip()
                        if hora_inicio or hora_fim:
                            st.caption(f"Professor: {professor_label} | Horario: {hora_inicio or '--'} - {hora_fim or '--'}")
                        else:
                            st.caption(f"Professor: {professor_label}")
                        st.markdown(f"**Licao/Conteudo:** {str(sessao.get('licao', '')).strip() or '-'}")
                        resumo_final = str(sessao.get("resumo_final", "")).strip()
                        resumo_inicio = str(sessao.get("resumo_inicio", "")).strip()
                        if resumo_final:
                            st.markdown(f"**Resumo final:** {resumo_final}")
                        elif resumo_inicio:
                            st.markdown(f"**Objetivo da aula:** {resumo_inicio}")

    elif menu_aluno == "Boletim & Frequencia":
        st.markdown('<div class="main-header">Desempenho Acadêmico</div>', unsafe_allow_html=True)
        tab1, tab2 = st.tabs(["Notas", "Presença"])
        aluno_nome = st.session_state["user_name"]
        notas = [g for g in st.session_state["grades"] if g.get("aluno") == aluno_nome and g.get("status") == "Aprovado"]
        with tab1:
            if notas: st.dataframe(pd.DataFrame(notas), use_container_width=True)
            else: st.info("Nenhuma nota lançada.")
        with tab2:
            presencas = []
            for nota_obj in notas:
                avaliacao_norm = normalize_text(nota_obj.get("avaliacao", ""))
                nota_txt = str(nota_obj.get("nota", "")).strip()
                if "%" not in nota_txt and "presenca" not in avaliacao_norm:
                    continue
                match_num = re.search(r"-?\d+(?:[.,]\d+)?", nota_txt)
                if not match_num:
                    continue
                presencas.append(max(0.0, min(100.0, _parse_float(match_num.group(0), default=0.0))))
            if presencas:
                media_presenca = sum(presencas) / len(presencas)
                st.success(f"Frequência atual: {media_presenca:.0f}%")
            else:
                st.info("Frequência: sem dados aprovados ainda.")

    elif menu_aluno == "Mensagens":
        st.markdown('<div class="main-header">Mensagens</div>', unsafe_allow_html=True)
        aluno_nome = st.session_state.get("user_name", "")
        turma_aluno = next((s.get("turma") for s in st.session_state["students"] if s.get("nome") == aluno_nome), "")
        mensagens_aluno = [
            m for m in st.session_state["messages"]
            if _message_matches_student(m, aluno_nome, turma_aluno)
        ]
        if mensagens_aluno:
            novos_lidos = _mark_student_messages_read(aluno_nome, mensagens_aluno)
            if novos_lidos > 0:
                st.caption(f"{novos_lidos} mensagem(ns) marcada(s) como lida(s).")
        if not mensagens_aluno: st.info("Sem mensagens.")
        for msg in reversed(mensagens_aluno):
            destino_txt = _message_destination_label(msg)
            with st.container():
                st.markdown(f"""<div style="background:white; padding:16px; border-radius:12px; border:1px solid #e2e8f0; margin-bottom:10px;"><div style="font-weight:700; color:#1e3a8a;">{msg.get('titulo','Mensagem')}</div><div style="font-size:0.85rem; color:#64748b; margin-bottom:8px;">{msg.get('data','')} | {msg.get('autor','')} | {destino_txt}</div><div>{msg.get('mensagem','')}</div></div>""", unsafe_allow_html=True)

    elif menu_aluno == "Atividades":
        only_homework = str(menu_aluno_label).strip() == "Lições de Casa"
        page_title = "Licoes de Casa" if only_homework else "Atividades e Licoes de Casa"
        st.markdown(f'<div class="main-header">{page_title}</div>', unsafe_allow_html=True)
        aluno_nome = st.session_state.get("user_name", "")
        turma_aluno = _student_class_name(aluno_nome)
        if not turma_aluno:
            st.info("Seu usuario nao esta vinculado a uma turma.")
        else:
            atividades_turma = [
                a for a in st.session_state.get("activities", [])
                if str(a.get("turma", "")).strip() == turma_aluno
            ]
            if only_homework:
                atividades_turma = [a for a in atividades_turma if _is_homework_activity(a)]
            atividades_turma = sorted(
                atividades_turma,
                key=lambda a: (
                    0 if _is_activity_open(a) else 1,
                    parse_date(a.get("due_date", "")) or datetime.date(2100, 1, 1),
                    str(a.get("created_at", "")),
                ),
            )
            if not atividades_turma:
                if only_homework:
                    st.info("Nenhuma licao de casa publicada para sua turma.")
                else:
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

        desafios_semana = get_student_weekly_challenges(aluno_obj, semana)
        if not desafios_semana:
            st.info("Ainda nao foi publicado desafio para voce nesta semana.")
        else:
            st.markdown("### Desafios disponiveis")
            for idx, ch in enumerate(desafios_semana, start=1):
                st.markdown(f"### {idx}. {ch.get('titulo','Desafio')}")
                st.caption(
                    f"{_challenge_target_label(ch)} | Pontos: {ch.get('pontos', 0)} | "
                    f"Publicado por: {ch.get('autor','')} | Prazo: {ch.get('due_date','') or 'sem prazo'}"
                )
                st.write(ch.get("descricao", ""))
                if str(ch.get("dica", "")).strip():
                    st.info(f"Dica: {str(ch.get('dica','')).strip()}")
                cid = ch.get("id", "")
                sub = get_challenge_submission(cid, aluno_nome) or {}
                done = has_completed_challenge(cid, aluno_nome)
                ja_enviado = bool(sub)

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
                        with st.expander(f"Ver minha resposta - {ch.get('titulo','Desafio')}"):
                            st.write(sub.get("resposta", ""))

                if ja_enviado:
                    if done:
                        st.success("Voce ja concluiu este desafio (aprovado).")
                    else:
                        st.warning("Tentativa unica registrada. Este desafio ja foi respondido.")
                    st.info("Regra ativa: apenas 1 tentativa por desafio.")
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
                                ev = evaluate_challenge_answer_ai(ch, _norm_book_level(ch.get("nivel", "")) or nivel, resposta)
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
                                        st.warning("Resposta enviada e avaliada como reprovada. Tentativa unica encerrada.")
                                    st.rerun()
                                else:
                                    st.error(msg)
                st.divider()

        st.markdown("### Historico de concluidos")
        concluidos = [c for c in st.session_state.get("challenge_completions", []) if str(c.get("aluno", "")).strip() == aluno_nome]
        if not concluidos:
            st.info("Nenhum desafio concluido ainda.")
        else:
            df = pd.DataFrame(concluidos)
            col_order = [c for c in ["done_at", "semana", "challenge_title", "challenge_target", "nivel", "status", "score", "pontos", "challenge_id"] if c in df.columns]
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
        turma_nome = str(aluno_obj.get("turma", "")).strip()
        livro_aluno = student_book_level(aluno_obj)
        livros = st.session_state.get("books", [])
        livro_aluno_norm = _norm_book_level(livro_aluno)
        livros_filtrados = []
        for b in livros:
            if not isinstance(b, dict):
                continue
            nivel_item_norm = _norm_book_level(str(b.get("nivel", "")).strip())
            # Mostra os livros do nivel do aluno e livros gerais (sem nivel).
            if livro_aluno_norm and nivel_item_norm and nivel_item_norm != livro_aluno_norm:
                continue
            livros_filtrados.append(b)
        render_books_section(livros_filtrados, "Livro do Aluno", key_prefix="aluno_livro", allow_download=True)

        materiais_aluno = filter_items_by_turma(st.session_state.get("materials", []), turma_nome)
        if not materiais_aluno:
            st.info("Sem materiais para sua turma.")
        for m in reversed(materiais_aluno):
            with st.container():
                st.markdown(f"**{m['titulo']}**")
                st.write(m['descricao'])
                if m['link']: st.markdown(f"[Baixar Arquivo]({m['link']})")
                meta = []
                if m.get("turma"):
                    meta.append(f"Turma: {m.get('turma')}")
                if m.get("autor"):
                    meta.append(f"Autor: {m.get('autor')}")
                if m.get("data"):
                    meta.append(f"Data: {m.get('data')}")
                if meta:
                    st.caption(" | ".join(meta))
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
        menu_prof_label = sidebar_menu(
            "Gestão",
            ["Minhas Turmas", "Agenda", "Mensagens", "Atividades", "Lições de Casa", "Lançar Notas", "Biblioteca", "Professor Wiz"],
            "menu_prof",
        )
        st.markdown("---")
        st.markdown('<div class="logout-btn">', unsafe_allow_html=True)
        if st.button("Sair"): logout_user()
        st.markdown('</div>', unsafe_allow_html=True)

    menu_prof_map = {
        "Minhas Turmas": "Minhas Turmas",
        "Agenda": "Agenda",
        "Mensagens": "Mensagens",
        "Atividades": "Atividades",
        "Lições de Casa": "Licoes de Casa",
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
                vip_alunos_turma = _vip_students_for_class(turma_ctrl)
                aulas_turma = [
                    a for a in st.session_state.get("agenda", [])
                    if str(a.get("turma", "")).strip() == str(turma_ctrl).strip()
                ]
                aulas_turma = sort_agenda(aulas_turma)

                st.markdown("### Saldo VIP da turma")
                if vip_alunos_turma:
                    df_vip = pd.DataFrame(vip_alunos_turma)
                    st.dataframe(df_vip, use_container_width=True, hide_index=True)
                else:
                    st.caption("Nenhum aluno VIP nesta turma.")

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
                            vip_consumidos = _consume_vip_package_for_class(sessao_ativa.get("turma", ""))
                            if vip_consumidos:
                                sessao_ativa["vip_consumed_students"] = [
                                    {
                                        "nome": item.get("nome", ""),
                                        "restantes": int(item.get("restantes", 0)),
                                    }
                                    for item in vip_consumidos
                                ]
                            save_list(CLASS_SESSIONS_FILE, st.session_state["class_sessions"])
                            if vip_consumidos:
                                resumo_vip = ", ".join(
                                    f"{item.get('nome', '')}: {int(item.get('restantes', 0))} aula(s)"
                                    for item in vip_consumidos
                                )
                                st.success(f"Aula fechada. Pacote VIP atualizado automaticamente: {resumo_vip}.")
                            else:
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
                n1, n2 = st.columns(2)
                with n1:
                    send_prof_msg_email = st.checkbox(
                        "Enviar por e-mail",
                        value=True,
                        key="prof_msg_notify_email",
                    )
                with n2:
                    send_prof_msg_whatsapp = st.checkbox(
                        "Enviar por WhatsApp",
                        value=True,
                        key="prof_msg_notify_whatsapp",
                    )
                titulo_msg = st.text_input("Titulo da mensagem")
                corpo_msg = st.text_area("Mensagem")
                if st.form_submit_button("Publicar mensagem"):
                    if not titulo_msg.strip() or not corpo_msg.strip():
                        st.error("Preencha titulo e mensagem.")
                    elif not send_prof_msg_email and not send_prof_msg_whatsapp:
                        st.error("Ative pelo menos um canal: e-mail ou WhatsApp.")
                    else:
                        stats = post_message_and_notify(
                            autor=st.session_state.get("user_name", "Professor"),
                            titulo=titulo_msg,
                            mensagem=corpo_msg,
                            turma=turma_msg,
                            origem="Mensagens Professor",
                            send_email=bool(send_prof_msg_email),
                            send_whatsapp=bool(send_prof_msg_whatsapp),
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
                if _message_matches_teacher(m, prof_nome, turmas_prof)
            ]
            if not historico:
                st.info("Sem mensagens.")
            for msg in historico:
                destino_txt = _message_destination_label(msg)
                st.markdown(
                    f"""<div style="background:white; padding:16px; border-radius:12px; border:1px solid #e2e8f0; margin-bottom:10px;">
<div style="font-weight:700; color:#1e3a8a;">{msg.get('titulo','Mensagem')}</div>
<div style="font-size:0.85rem; color:#64748b; margin-bottom:8px;">{msg.get('data','')} | {msg.get('autor','')} | {destino_txt}</div>
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

    elif menu_prof == "Licoes de Casa":
        turmas_prof = _teacher_class_names_for_user(st.session_state.get("user_name", ""))
        run_weekly_homework_panel(
            panel_key="prof_homework",
            turmas_disponiveis=turmas_prof,
            autor_nome=st.session_state.get("user_name", "Professor"),
        )

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
            "Lições de Casa",
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
        "Lições de Casa": "Licoes de Casa",
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
        total_rec = sum(
            parse_money(i.get("valor_parcela", i.get("valor", 0)))
            for i in st.session_state["receivables"]
            if str(i.get("status", "Aberto")).strip().lower() not in ("pago", "cancelado")
        )
        total_pag = sum(
            parse_money(i.get("valor_parcela", i.get("valor", 0)))
            for i in st.session_state["payables"]
            if str(i.get("status", "Aberto")).strip().lower() not in ("pago", "cancelado")
        )
        total_rec_mes = _financial_due_total_for_month(st.session_state.get("receivables", []), date_field="vencimento")
        total_pag_mes = _financial_due_total_for_month(st.session_state.get("payables", []), date_field="vencimento")
        total_rec_venc = _financial_overdue_total(st.session_state.get("receivables", []), date_field="vencimento")
        total_pag_venc = _financial_overdue_total(st.session_state.get("payables", []), date_field="vencimento")
        qtd_rec_venc = len(_financial_overdue_items(st.session_state.get("receivables", []), date_field="vencimento"))
        qtd_pag_venc = len(_financial_overdue_items(st.session_state.get("payables", []), date_field="vencimento"))
        saldo = total_rec - total_pag
        c4, c5, c6 = st.columns(3)
        with c4: st.markdown(f"""<div class=\"dash-card\"><div><div class=\"card-title\">A Receber</div><div class=\"card-value\" style=\"color:#2563eb;\">{format_money(total_rec)}</div></div></div>""", unsafe_allow_html=True)
        with c5: st.markdown(f"""<div class=\"dash-card\"><div><div class=\"card-title\">A Pagar</div><div class=\"card-value\" style=\"color:#dc2626;\">{format_money(total_pag)}</div></div></div>""", unsafe_allow_html=True)
        with c6:
             color = "#16a34a" if saldo >= 0 else "#dc2626"
             st.markdown(f"""<div class=\"dash-card\"><div><div class=\"card-title\">Saldo Atual</div><div class=\"card-value\" style=\"color:{color};\">{format_money(saldo)}</div></div></div>""", unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown(
            f"""
            <div class="dash-card">
              <div class="card-title">Mes Vigente</div>
              <div style="display:flex; gap:32px; flex-wrap:wrap; margin-top:10px;">
                <div>
                  <div class="card-sub">A receber no mes</div>
                  <div class="card-value" style="color:#2563eb;">{format_money(total_rec_mes)}</div>
                </div>
                <div>
                  <div class="card-sub">A pagar no mes</div>
                  <div class="card-value" style="color:#dc2626;">{format_money(total_pag_mes)}</div>
                </div>
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.markdown("<br>", unsafe_allow_html=True)
        vd1, vd2 = st.columns(2)
        with vd1:
            st.markdown(
                f"""
                <div class="dash-card">
                  <div class="card-title">Vencidos a Receber</div>
                  <div class="card-value" style="color:#dc2626;">{format_money(total_rec_venc)}</div>
                  <div class="card-sub"><span class="trend-neutral">{qtd_rec_venc} lançamento(s) vencido(s)</span></div>
                </div>
                """,
                unsafe_allow_html=True,
            )
            if st.button("Ver vencidos a receber", key="dash_overdue_receivables_btn"):
                st.session_state["menu_coord"] = "Financeiro"
                st.session_state["finance_overdue_focus"] = "receber"
                st.rerun()
        with vd2:
            st.markdown(
                f"""
                <div class="dash-card">
                  <div class="card-title">Vencidos a Pagar</div>
                  <div class="card-value" style="color:#dc2626;">{format_money(total_pag_venc)}</div>
                  <div class="card-sub"><span class="trend-neutral">{qtd_pag_venc} lançamento(s) vencido(s)</span></div>
                </div>
                """,
                unsafe_allow_html=True,
            )
            if st.button("Ver vencidos a pagar", key="dash_overdue_payables_btn"):
                st.session_state["menu_coord"] = "Financeiro"
                st.session_state["finance_overdue_focus"] = "pagar"
                st.rerun()

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

                    # Force refresh of readonly fields whenever class selection changes.
                    st.session_state["coord_agenda_professor_preview"] = str(prof_default).strip()
                    st.session_state["coord_agenda_link_preview"] = str(link_default).strip()
                    st.text_input(
                        "Professor",
                        key="coord_agenda_professor_preview",
                        disabled=True,
                    )
                    st.text_input(
                        "Link da aula",
                        key="coord_agenda_link_preview",
                        disabled=True,
                    )
                    c_notify_1, c_notify_2 = st.columns(2)
                    with c_notify_1:
                        enviar_email_convite = st.checkbox(
                            "Enviar comunicado por e-mail",
                            value=True,
                            key="coord_agenda_notify_email",
                        )
                    with c_notify_2:
                        enviar_whatsapp_convite = st.checkbox(
                            "Enviar comunicado por WhatsApp",
                            value=True,
                            key="coord_agenda_notify_whatsapp",
                        )
                    if st.form_submit_button("Agendar aula"):
                        if repetir and repetir_por_data and not dias_repeticao:
                            st.error("Selecione pelo menos um dia para repetição por data.")
                        elif not enviar_email_convite and not enviar_whatsapp_convite:
                            st.error("Ative pelo menos um canal: e-mail ou WhatsApp.")
                        else:
                            # Re-read class data at submit time to avoid stale professor/link.
                            turma_obj_submit = next(
                                (c for c in st.session_state["classes"] if c.get("nome") == turma_sel),
                                {},
                            )
                            professor_submit = str(turma_obj_submit.get("professor", "")).strip()
                            link_aula_submit = str(turma_obj_submit.get("link_zoom", "")).strip()
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
                                    "professor": professor_submit,
                                    "titulo": titulo.strip() or "Aula ao vivo",
                                    "descricao": descricao.strip(),
                                    "data": data_item.strftime("%d/%m/%Y") if data_item else "",
                                    "hora": hora_aula.strftime("%H:%M") if hora_aula else "",
                                    "link": link_aula_submit,
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
                                if enviar_email_convite or enviar_whatsapp_convite:
                                    notif_stats = notify_students_by_turma_channels(
                                        turma_sel,
                                        assunto,
                                        corpo,
                                        "Agenda",
                                        send_email=bool(enviar_email_convite),
                                        send_whatsapp=bool(enviar_whatsapp_convite),
                                    )
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
                l1, l2 = st.columns(2)
                with l1:
                    enviar_link_email = st.checkbox(
                        "Enviar atualizacao por e-mail",
                        value=True,
                        key="coord_link_notify_email",
                    )
                with l2:
                    enviar_link_whatsapp = st.checkbox(
                        "Enviar atualizacao por WhatsApp",
                        value=True,
                        key="coord_link_notify_whatsapp",
                    )
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
                            notif_stats = notify_students_by_turma_channels(
                                turma_sel,
                                assunto,
                                corpo,
                                "Links",
                                send_email=bool(enviar_link_email),
                                send_whatsapp=bool(enviar_link_whatsapp),
                            )
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
        books_current = st.session_state.get("books", [])
        books_normalized = ensure_library_catalog(books_current)
        if books_current != books_normalized:
            st.session_state["books"] = books_normalized
            save_list(BOOKS_FILE, st.session_state["books"])

        tab1, tab2 = st.tabs(["Biblioteca", "Anexar Livros"])
        with tab1:
            render_books_section(st.session_state.get("books", []), "Todos os Livros", key_prefix="coord_livros")
        with tab2:
            st.caption(
                "Anexe por botao: Ingles (5 livros em 2 partes), Lideranca, Empreendedorismo, Educacao Financeira e Inteligencia Emocional."
            )

            template_by_id = {str(t.get("book_id", "")).strip(): t for t in library_book_templates()}
            books_list = st.session_state.get("books", [])
            books_by_id = {
                str(b.get("book_id", "")).strip(): b
                for b in books_list
                if str(b.get("book_id", "")).strip()
            }

            def _book_obj(book_id):
                bid = str(book_id).strip()
                obj = books_by_id.get(bid)
                if obj is None:
                    tpl = dict(template_by_id.get(bid, {}))
                    tpl.setdefault("book_id", bid)
                    tpl.setdefault("titulo", "Livro")
                    tpl.setdefault("nivel", "")
                    tpl.setdefault("categoria", "")
                    tpl.setdefault("parte", "")
                    tpl.setdefault("url", "")
                    tpl.setdefault("file_path", "")
                    tpl.setdefault("file_b64", "")
                    tpl.setdefault("file_name", "")
                    books_list.append(tpl)
                    books_by_id[bid] = tpl
                    obj = tpl
                return obj

            def _save_book_item(book_id, url_value, uploaded_file):
                obj = _book_obj(book_id)
                obj["url"] = str(url_value or "").strip()
                if uploaded_file is not None:
                    raw = uploaded_file.getvalue()
                    if raw:
                        obj["file_b64"] = base64.b64encode(raw).decode("ascii")
                        obj["file_name"] = str(getattr(uploaded_file, "name", "") or "").strip()
                        obj["file_path"] = ""
                st.session_state["books"] = ensure_library_catalog(books_list)
                save_list(BOOKS_FILE, st.session_state["books"])

            def _render_book_editor(book_id, fallback_title):
                obj = _book_obj(book_id)
                title = str(obj.get("titulo", "")).strip() or str(fallback_title or "Livro").strip()
                st.markdown(f"**{title}**")
                r1, r2, r3, r4 = st.columns([2.2, 2.2, 1.0, 1.0])
                with r1:
                    url_item = st.text_input(
                        "Link",
                        value=str(obj.get("url", "")).strip(),
                        key=f"coord_book_url_{book_id}",
                    )
                with r2:
                    upload_item = st.file_uploader(
                        "Anexar arquivo",
                        type=["pdf", "doc", "docx", "ppt", "pptx", "zip", "txt", "epub"],
                        key=f"coord_book_upload_{book_id}",
                    )
                with r3:
                    if st.button("Anexar e salvar", key=f"coord_book_save_{book_id}", type="primary"):
                        _save_book_item(book_id, url_item, upload_item)
                        st.success(f"{title} salvo.")
                        st.rerun()
                with r4:
                    if st.button("Remover anexo", key=f"coord_book_clear_{book_id}"):
                        obj["file_b64"] = ""
                        obj["file_name"] = ""
                        obj["file_path"] = ""
                        st.session_state["books"] = ensure_library_catalog(books_list)
                        save_list(BOOKS_FILE, st.session_state["books"])
                        st.success("Anexo removido.")
                        st.rerun()
                _, existing_name = _book_binary_payload(obj)
                if existing_name:
                    st.caption(f"Arquivo anexado: {existing_name}")

            with st.container(border=True):
                st.markdown("#### Importar DOC/PDF para Biblioteca")
                st.caption("Escolha o livro de destino e anexe DOC, DOCX, PDF ou outro formato permitido.")

                quick_options = []
                for tpl in library_book_templates():
                    bid = str(tpl.get("book_id", "")).strip()
                    if not bid:
                        continue
                    titulo = str(tpl.get("titulo", "")).strip() or bid
                    categoria = str(tpl.get("categoria", "")).strip()
                    parte = str(tpl.get("parte", "")).strip()
                    label_parts = [titulo]
                    if categoria:
                        label_parts.append(categoria)
                    if parte:
                        label_parts.append(parte)
                    quick_options.append((bid, " | ".join(label_parts)))
                quick_options = sorted(quick_options, key=lambda x: x[1])
                quick_map = {label: bid for bid, label in quick_options}
                if not quick_options:
                    st.warning("Nenhum template de livro encontrado para importacao rapida.")
                else:
                    q1, q2 = st.columns([2, 2])
                    with q1:
                        quick_target_label = st.selectbox(
                            "Livro de destino",
                            [label for _, label in quick_options],
                            key="coord_book_quick_target",
                        )
                    with q2:
                        quick_link = st.text_input(
                            "Link opcional",
                            key="coord_book_quick_link",
                        )

                    quick_file = st.file_uploader(
                        "Arquivo (DOC, DOCX, PDF, PPT, PPTX, ZIP, TXT, EPUB)",
                        type=["pdf", "doc", "docx", "ppt", "pptx", "zip", "txt", "epub"],
                        key="coord_book_quick_file",
                    )

                    if st.button("Importar e anexar no livro", key="coord_book_quick_save", type="primary"):
                        target_id = quick_map.get(quick_target_label, "")
                        if not target_id:
                            st.error("Selecione um livro de destino.")
                        elif quick_file is None and not str(quick_link).strip():
                            st.error("Anexe um arquivo ou informe um link.")
                        else:
                            _save_book_item(target_id, quick_link, quick_file)
                            target_obj = _book_obj(target_id)
                            st.success(f"Arquivo salvo em: {target_obj.get('titulo', 'Livro')}.")
                            st.rerun()

            st.markdown("### Ingles (5 livros em 2 partes)")
            for livro in range(1, 6):
                st.markdown(f"#### Livro {livro}")
                for parte in (1, 2):
                    book_id = f"ingles_livro_{livro}_parte_{parte}"
                    _render_book_editor(book_id, f"Livro {livro} - Parte {parte}")
                    st.markdown("---")

            st.markdown("### Trilhas Complementares")
            trilhas = [
                ("Lideranca", ["lideranca"]),
                (
                    "Empreendedorismo",
                    [
                        "empreendedorismo_business_adults_1",
                        "empreendedorismo_business_adults_2",
                        "empreendedorismo_business_adults_3",
                        "empreendedorismo_empreendedoresmo_1",
                        "empreendedorismo_empreendedoresmo_2",
                        "empreendedorismo_jovens_1_1",
                        "empreendedorismo_jovens_1",
                        "empreendedorismo_jovens_2",
                        "empreendedorismo_jovens_3",
                        "empreendedorismo_jovens_4",
                        "empreendedorismo",
                    ],
                ),
                ("Educacao Financeira", ["educacao_financeira"]),
                (
                    "Inteligencia Emocional",
                    [
                        "inteligencia_emocional_livro_1",
                        "inteligencia_emocional_livro_2",
                        "inteligencia_emocional_livro_2_2",
                        "inteligencia_emocional_livro_3",
                        "inteligencia_emocional_livro_3_3",
                        "inteligencia_emocional_livro_4",
                        "inteligencia_emocional_base",
                        "inteligencia_emocional_express_adults",
                        "inteligencia_emocional_express_teens",
                        "inteligencia_emocional_express_teens_3",
                        "inteligencia_emocional",
                    ],
                ),
            ]
            for secao, ids in trilhas:
                st.markdown(f"#### {secao}")
                for book_id in ids:
                    tpl = template_by_id.get(book_id, {})
                    fallback_title = str(tpl.get("titulo", "")).strip() or secao
                    _render_book_editor(book_id, fallback_title)
                    st.markdown("---")

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
                filtro_panel_key = "students_list_filter_open"
                turma_filter_key = "students_list_turma_filter"
                prof_filter_key = "students_list_prof_filter"
                st.session_state.setdefault(filtro_panel_key, False)

                cbtn1, _ = st.columns([1, 5])
                with cbtn1:
                    if st.button("Filtro", key="students_list_filter_toggle"):
                        st.session_state[filtro_panel_key] = not bool(st.session_state.get(filtro_panel_key, False))

                if st.session_state.get(turma_filter_key) not in turmas_opts:
                    st.session_state[turma_filter_key] = "Todas"
                if st.session_state.get(prof_filter_key) not in (profs_opts if profs_opts else ["Todos"]):
                    st.session_state[prof_filter_key] = "Todos"

                if st.session_state.get(filtro_panel_key, False):
                    col_f1, col_f2 = st.columns(2)
                    with col_f1:
                        st.selectbox("Filtrar por Turma", turmas_opts, key=turma_filter_key)
                    with col_f2:
                        st.selectbox("Filtrar por Professor", profs_opts if profs_opts else ["Todos"], key=prof_filter_key)

                turma_filtro = str(st.session_state.get(turma_filter_key, "Todas"))
                prof_filtro = str(st.session_state.get(prof_filter_key, "Todos"))

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
                        "modulo",
                        "vip_tipo_plano",
                        "vip_aulas_restantes",
                        "email",
                        "celular",
                        "data_nascimento",
                        "idade",
                        "rg",
                        "cpf",
                        "cep",
                        "rua",
                        "numero",
                        "complemento",
                        "cidade",
                        "bairro",
                        "responsavel.nome",
                        "responsavel.celular",
                        "responsavel.email",
                    ]
                    colunas = list(df_alunos.columns)
                    colunas_key = "students_list_visible_cols"
                    colunas_default = [c for c in col_default if c in colunas]
                    colunas_saved = [c for c in st.session_state.get(colunas_key, colunas_default) if c in colunas]
                    if not colunas_saved:
                        colunas_saved = list(colunas_default)
                    st.session_state[colunas_key] = colunas_saved

                    if st.session_state.get(filtro_panel_key, False):
                        st.multiselect(
                            "Colunas visíveis",
                            colunas,
                            default=colunas_saved,
                            key=colunas_key,
                        )

                    colunas_sel = [c for c in st.session_state.get(colunas_key, []) if c in colunas]
                    if not colunas_sel:
                        colunas_sel = list(colunas_default)
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
            st.session_state.setdefault("add_student_edit_idx", -1)
            st.session_state.setdefault("add_student_edit_matricula", "")
            form_ver = int(st.session_state["add_student_form_version"])

            def _sfk(name: str) -> str:
                return f"{name}__v{form_ver}"

            student_form_defaults = {
                _sfk("add_student_nome"): "",
                _sfk("add_student_data_nascimento"): datetime.date.today(),
                _sfk("add_student_genero"): "Masculino",
                _sfk("add_student_status"): "Ativo",
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
                _sfk("add_student_vip_tipo"): "Aula avulsa",
                _sfk("add_student_vip_restantes"): 1,
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
            status_opts = ["Ativo", "Inativo", "Pausado"]
            status_key = _sfk("add_student_status")
            if st.session_state.get(status_key) not in status_opts:
                st.session_state[status_key] = "Ativo"

            feedback = st.session_state.pop("add_student_feedback", None)
            if feedback:
                st.success(feedback.get("success", "Cadastro realizado com sucesso!"))
                info_msg = feedback.get("info")
                if info_msg:
                    st.info(info_msg)

            if st.session_state.get("students"):
                st.markdown("### Puxar Aluno Cadastrado")
                alunos_pull = st.session_state.get("students", [])
                pull_options = list(range(len(alunos_pull)))
                selected_pull_idx = st.selectbox(
                    "Selecione um aluno para carregar no formulario",
                    pull_options,
                    format_func=lambda i: (
                        f"{str(alunos_pull[i].get('nome', '')).strip()} | "
                        f"Matricula: {str(alunos_pull[i].get('matricula', '')).strip() or '-'} | "
                        f"Celular: {str(alunos_pull[i].get('celular', '')).strip() or '-'}"
                    ),
                    key=f"add_student_pull_idx__v{form_ver}",
                )
                p1, p2 = st.columns(2)
                with p1:
                    if st.button("Puxar para corrigir neste formulario", key=f"add_student_pull_btn__v{form_ver}"):
                        aluno_src = alunos_pull[int(selected_pull_idx)]
                        resp_src = aluno_src.get("responsavel", {})
                        if not isinstance(resp_src, dict):
                            resp_src = {}
                        dn_src = parse_date(
                            str(aluno_src.get("data_nascimento", "")).strip()
                            or str(aluno_src.get("nascimento", "")).strip()
                        ) or datetime.date.today()

                        st.session_state["add_student_edit_idx"] = int(selected_pull_idx)
                        st.session_state["add_student_edit_matricula"] = str(aluno_src.get("matricula", "")).strip()
                        st.session_state[_sfk("add_student_nome")] = str(aluno_src.get("nome", "")).strip()
                        st.session_state[_sfk("add_student_data_nascimento")] = dn_src
                        st.session_state[_sfk("add_student_genero")] = str(aluno_src.get("genero", "Masculino")).strip() or "Masculino"
                        st.session_state[_sfk("add_student_status")] = str(aluno_src.get("status", "Ativo")).strip() or "Ativo"
                        st.session_state[_sfk("add_student_celular")] = str(aluno_src.get("celular", "")).strip()
                        st.session_state[_sfk("add_student_email")] = str(aluno_src.get("email", "")).strip()
                        st.session_state[_sfk("add_student_rg")] = str(aluno_src.get("rg", "")).strip()
                        st.session_state[_sfk("add_student_cpf")] = str(aluno_src.get("cpf", "")).strip()
                        st.session_state[_sfk("add_student_natal")] = str(aluno_src.get("cidade_natal", "")).strip()
                        st.session_state[_sfk("add_student_pais")] = str(aluno_src.get("pais", "Brasil")).strip() or "Brasil"
                        st.session_state[_sfk("add_student_cep")] = str(aluno_src.get("cep", "")).strip()
                        st.session_state[_sfk("add_student_cidade")] = str(aluno_src.get("cidade", "")).strip()
                        st.session_state[_sfk("add_student_bairro")] = str(aluno_src.get("bairro", "")).strip()
                        st.session_state[_sfk("add_student_rua")] = str(aluno_src.get("rua", "")).strip()
                        st.session_state[_sfk("add_student_numero")] = str(aluno_src.get("numero", "")).strip()
                        st.session_state[_sfk("add_student_complemento")] = str(aluno_src.get("complemento", "")).strip()
                        st.session_state[_sfk("add_student_turma")] = str(aluno_src.get("turma", "Sem Turma")).strip() or "Sem Turma"
                        st.session_state[_sfk("add_student_modulo")] = str(aluno_src.get("modulo", modulos[0])).strip() or modulos[0]
                        st.session_state[_sfk("add_student_livro")] = str(aluno_src.get("livro", "Automatico (Turma)")).strip() or "Automatico (Turma)"
                        vip_tipo_src = str(aluno_src.get("vip_tipo_plano", "Aula avulsa")).strip() or "Aula avulsa"
                        vip_total_src = _vip_plan_total(vip_tipo_src)
                        vip_restantes_src = parse_int(aluno_src.get("vip_aulas_restantes", vip_total_src))
                        if vip_restantes_src is None or vip_restantes_src < 0:
                            vip_restantes_src = vip_total_src
                        st.session_state[_sfk("add_student_vip_tipo")] = vip_tipo_src
                        st.session_state[_sfk("add_student_vip_restantes")] = int(vip_restantes_src)
                        st.session_state[_sfk("add_student_login")] = str(aluno_src.get("usuario", "")).strip()
                        st.session_state[_sfk("add_student_senha")] = str(aluno_src.get("senha", "")).strip()
                        st.session_state[_sfk("add_student_resp_nome")] = str(resp_src.get("nome", "")).strip()
                        st.session_state[_sfk("add_student_resp_cpf")] = str(resp_src.get("cpf", "")).strip()
                        st.session_state[_sfk("add_student_resp_cel")] = str(resp_src.get("celular", "")).strip()
                        st.session_state[_sfk("add_student_resp_email")] = str(resp_src.get("email", "")).strip()
                        st.rerun()
                with p2:
                    if st.button("Novo cadastro (limpar formulario)", key=f"add_student_new_btn__v{form_ver}"):
                        st.session_state["add_student_edit_idx"] = -1
                        st.session_state["add_student_edit_matricula"] = ""
                        st.session_state["add_student_form_version"] = form_ver + 1
                        st.rerun()

            edit_idx_active = int(st.session_state.get("add_student_edit_idx", -1) or -1)
            edit_student_active = None
            if 0 <= edit_idx_active < len(st.session_state.get("students", [])):
                edit_student_active = st.session_state["students"][edit_idx_active]
                st.info(
                    "Modo correcao ativo para: "
                    f"{str(edit_student_active.get('nome', '')).strip()} "
                    f"(Matricula {str(edit_student_active.get('matricula', '')).strip() or '-'})"
                )

            with st.form("add_student_full", clear_on_submit=False):
                st.markdown("### Dados Pessoais")
                c1, c2, c3, c4 = st.columns(4)
                with c1: nome = st.text_input("Nome Completo *", key=_sfk("add_student_nome"))
                matricula_auto = _next_student_matricula(st.session_state["students"])
                matricula_edicao = str(st.session_state.get("add_student_edit_matricula", "")).strip()
                matricula_view = matricula_edicao or matricula_auto
                with c2: st.text_input("No. da Matricula", value=matricula_view, disabled=True)
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

                c7, c8, c9, c10, c11 = st.columns(5)
                with c7: cpf = st.text_input("CPF", key=_sfk("add_student_cpf"))
                with c8: natal = st.text_input("Cidade Natal", key=_sfk("add_student_natal"))
                with c9: pais = st.text_input("Pais de Origem", key=_sfk("add_student_pais"))
                with c10: genero = st.selectbox("Sexo", ["Masculino", "Feminino"], key=genero_key)
                with c11: status_aluno = st.selectbox("Status do aluno", status_opts, key=status_key)

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
                vip_tipo_plano = ""
                vip_aulas_total = 0
                vip_aulas_restantes = 0
                if _is_vip_module_label(modulo_sel):
                    st.markdown("### Plano VIP")
                    vip_tipo_key = _sfk("add_student_vip_tipo")
                    vip_restantes_key = _sfk("add_student_vip_restantes")
                    vip_opcoes = ["Aula avulsa", "Pacote 10 aulas"]
                    if st.session_state.get(vip_tipo_key) not in vip_opcoes:
                        st.session_state[vip_tipo_key] = vip_opcoes[0]
                    vip_tipo_plano = st.selectbox("Tipo do plano VIP", vip_opcoes, key=vip_tipo_key)
                    vip_aulas_total = _vip_plan_total(vip_tipo_plano)
                    valor_restante_padrao = parse_int(st.session_state.get(vip_restantes_key, vip_aulas_total))
                    if valor_restante_padrao is None:
                        valor_restante_padrao = vip_aulas_total
                    valor_restante_padrao = max(0, min(50, int(valor_restante_padrao)))
                    st.session_state[vip_restantes_key] = valor_restante_padrao
                    vip_aulas_restantes = int(
                        st.number_input(
                            "Aulas restantes no pacote",
                            min_value=0,
                            max_value=50,
                            step=1,
                            key=vip_restantes_key,
                        )
                    )
                    vip_aulas_total = max(int(vip_aulas_total), int(vip_aulas_restantes))

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

                st.markdown("### Envio automatico de boas-vindas")
                n1, n2 = st.columns(2)
                with n1:
                    send_student_email = st.checkbox(
                        "Enviar mensagem por e-mail",
                        value=True,
                        key=_sfk("add_student_notify_email"),
                    )
                with n2:
                    send_student_whatsapp = st.checkbox(
                        "Enviar mensagem por WhatsApp",
                        value=True,
                        key=_sfk("add_student_notify_whatsapp"),
                    )

                submit_with_notify = False
                if edit_student_active:
                    sb1, sb2 = st.columns(2)
                    with sb1:
                        submit_base = st.form_submit_button("Salvar Correcao do Aluno")
                    with sb2:
                        submit_with_notify = st.form_submit_button("Salvar Correcao + Notificar (E-mail/WhatsApp)")
                    submit_pressed = bool(submit_base or submit_with_notify)
                else:
                    submit_pressed = st.form_submit_button("Cadastrar Aluno")
                if submit_pressed:
                    idade_final = _calc_age_from_date_obj(data_nascimento) or 1
                    edit_idx_submit = int(st.session_state.get("add_student_edit_idx", -1) or -1)
                    edit_obj_submit = None
                    if 0 <= edit_idx_submit < len(st.session_state.get("students", [])):
                        edit_obj_submit = st.session_state["students"][edit_idx_submit]
                    matricula_final = (
                        str(st.session_state.get("add_student_edit_matricula", "")).strip()
                        or str((edit_obj_submit or {}).get("matricula", "")).strip()
                        or _next_student_matricula(st.session_state["students"])
                    )
                    nome = nome.strip()
                    email = email.strip()
                    login_aluno = login_aluno.strip()
                    senha_aluno = senha_aluno.strip()
                    resp_nome = resp_nome.strip()
                    resp_cpf = resp_cpf.strip()
                    resp_email = resp_email.strip()
                    old_login = str((edit_obj_submit or {}).get("usuario", "")).strip()
                    old_senha = str((edit_obj_submit or {}).get("senha", "")).strip()
                    login_final = login_aluno or old_login
                    senha_final = senha_aluno or old_senha

                    if idade_final < 18 and (not resp_nome or not resp_cpf):
                        st.error("ERRO: Aluno menor de idade! E obrigatorio preencher Nome e CPF do Responsavel.")
                    elif not nome or not email:
                        st.error("ERRO: Nome e E-mail sao obrigatorios.")
                    elif not edit_obj_submit and ((login_final and not senha_final) or (senha_final and not login_final)):
                        st.error("ERRO: Para criar o login, informe usuario e senha.")
                    else:
                        login_conflict = find_user(login_final) if login_final else None
                        if login_conflict and (not old_login or str(login_final).strip().lower() != str(old_login).strip().lower()):
                            st.error("ERRO: Este login ja existe.")
                        else:
                            turma_obj = next((c for c in st.session_state["classes"] if c.get("nome") == turma), {})
                            livro_turma = turma_obj.get("livro", "")
                            livro_final = livro_turma if livro_sel == "Automatico (Turma)" else livro_sel
                            aluno_payload = {
                                "nome": nome,
                                "matricula": matricula_final,
                                "idade": idade_final,
                                "genero": genero,
                                "status": status_aluno,
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
                                "vip_tipo_plano": vip_tipo_plano if _is_vip_module_label(modulo_sel) else "",
                                "vip_aulas_total": int(vip_aulas_total) if _is_vip_module_label(modulo_sel) else 0,
                                "vip_aulas_restantes": int(vip_aulas_restantes) if _is_vip_module_label(modulo_sel) else 0,
                                "usuario": login_final,
                                "senha": senha_final,
                                "responsavel": {
                                    "nome": resp_nome,
                                    "cpf": resp_cpf,
                                    "celular": resp_cel,
                                    "email": resp_email.lower(),
                                },
                            }
                            if edit_obj_submit:
                                edit_obj_submit.update(aluno_payload)
                                edit_obj_submit.pop("nascimento", None)
                                save_list(STUDENTS_FILE, st.session_state["students"])

                                if login_final:
                                    user_obj = find_user(old_login) if old_login else None
                                    if user_obj:
                                        user_obj["usuario"] = login_final
                                        user_obj["senha"] = senha_final
                                        user_obj["perfil"] = "Aluno"
                                        user_obj["pessoa"] = nome
                                    elif not find_user(login_final):
                                        st.session_state["users"].append(
                                            {
                                                "usuario": login_final,
                                                "senha": senha_final,
                                                "perfil": "Aluno",
                                                "pessoa": nome,
                                            }
                                        )
                                    save_users(st.session_state["users"])

                                update_notify_stats = {"email_total": 0, "email_ok": 0, "whatsapp_total": 0, "whatsapp_ok": 0}
                                if bool(submit_with_notify):
                                    update_notify_stats = notify_student_profile_update(
                                        edit_obj_submit,
                                        autor=st.session_state.get("user_name", "Coordenacao"),
                                        origem="Atualizacao Aluno",
                                        send_email=True,
                                        send_whatsapp=True,
                                    )
                                st.session_state["add_student_feedback"] = {
                                    "success": "Aluno atualizado com sucesso no Cadastro Completo!",
                                    "info": (
                                        "Os dados foram carregados e corrigidos sem duplicar cadastro."
                                        if not bool(submit_with_notify)
                                        else (
                                            "Disparos de atualizacao: "
                                            f"E-mail {update_notify_stats.get('email_ok', 0)}/{update_notify_stats.get('email_total', 0)} | "
                                            f"WhatsApp {update_notify_stats.get('whatsapp_ok', 0)}/{update_notify_stats.get('whatsapp_total', 0)}."
                                        )
                                    ),
                                }
                            else:
                                novo_aluno = dict(aluno_payload)
                                st.session_state["students"].append(novo_aluno)
                                save_list(STUDENTS_FILE, st.session_state["students"])

                                if login_final and senha_final:
                                    st.session_state["users"].append(
                                        {
                                            "usuario": login_final,
                                            "senha": senha_final,
                                            "perfil": "Aluno",
                                            "pessoa": nome,
                                        }
                                    )
                                    save_users(st.session_state["users"])

                                turma_link = str(turma_obj.get("link_zoom", "")).strip() if isinstance(turma_obj, dict) else ""
                                portal_url = _student_portal_url()
                                login_info = login_final or "Nao informado"
                                senha_info = senha_final or "Nao informada"
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
                                        _message_recipients_for_student(novo_aluno) if bool(send_student_email) else [],
                                        _student_whatsapp_recipients(novo_aluno) if bool(send_student_whatsapp) else [],
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

                            st.session_state["add_student_edit_idx"] = -1
                            st.session_state["add_student_edit_matricula"] = ""
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
                        st.markdown("### Dados Pessoais")
                        c1, c2, c3, c4 = st.columns(4)
                        with c1:
                            new_nome = st.text_input("Nome Completo *", value=aluno_obj.get("nome", ""))
                        matricula_atual = aluno_obj.get("matricula", "") or _next_student_matricula(st.session_state["students"])
                        with c2:
                            st.text_input("No. da Matricula", value=matricula_atual, disabled=True)
                        with c3:
                            new_dn = st.date_input(
                                "Data de Nascimento *",
                                value=current_dn,
                                format="DD/MM/YYYY",
                                help="Formato: DD/MM/AAAA",
                                min_value=datetime.date(1900, 1, 1),
                                max_value=datetime.date(2036, 12, 31),
                            )
                        idade_edit_auto = _calc_age_from_date_obj(new_dn) or current_idade
                        with c4:
                            st.number_input("Idade *", min_value=1, max_value=120, step=1, value=idade_edit_auto, disabled=True)

                        c5, c6, c7 = st.columns(3)
                        with c5:
                            new_cel = st.text_input("Celular/WhatsApp *", value=aluno_obj.get("celular", ""))
                        with c6:
                            new_email = st.text_input("E-mail do Aluno *", value=aluno_obj.get("email", ""))
                        with c7:
                            new_rg = st.text_input("RG", value=aluno_obj.get("rg", ""))

                        c8, c9, c10, c11, c12 = st.columns(5)
                        with c8:
                            new_cpf = st.text_input("CPF", value=aluno_obj.get("cpf", ""))
                        with c9:
                            new_natal = st.text_input("Cidade Natal", value=aluno_obj.get("cidade_natal", ""))
                        with c10:
                            new_pais = st.text_input("Pais de Origem", value=aluno_obj.get("pais", "Brasil"))
                        with c11:
                            generos = ["Masculino", "Feminino"]
                            genero_atual = str(aluno_obj.get("genero", "Masculino")).strip()
                            if genero_atual not in generos:
                                generos.append(genero_atual)
                            new_genero = st.selectbox(
                                "Sexo",
                                generos,
                                index=generos.index(genero_atual) if genero_atual in generos else 0,
                            )
                        with c12:
                            status_edit_opts = ["Ativo", "Inativo", "Pausado"]
                            status_atual = str(aluno_obj.get("status", "Ativo")).strip() or "Ativo"
                            if status_atual not in status_edit_opts:
                                status_edit_opts.append(status_atual)
                            new_status = st.selectbox(
                                "Status do aluno",
                                status_edit_opts,
                                index=status_edit_opts.index(status_atual) if status_atual in status_edit_opts else 0,
                            )

                        st.divider()
                        st.markdown("### Endereco")
                        ce1, ce2, ce3 = st.columns(3)
                        with ce1:
                            new_cep = st.text_input("CEP", value=aluno_obj.get("cep", ""))
                        with ce2:
                            new_cidade = st.text_input("Cidade", value=aluno_obj.get("cidade", ""))
                        with ce3:
                            new_bairro = st.text_input("Bairro", value=aluno_obj.get("bairro", ""))

                        ce4, ce5, ce6 = st.columns([3, 1, 2])
                        with ce4:
                            new_rua = st.text_input("Rua", value=aluno_obj.get("rua", ""))
                        with ce5:
                            new_numero = st.text_input("Numero", value=aluno_obj.get("numero", ""))
                        with ce6:
                            new_complemento = st.text_input(
                                "Observacao (Apto, Bloco, Casa)",
                                value=aluno_obj.get("complemento", ""),
                            )

                        st.divider()
                        st.markdown("### Turma")
                        new_turma = st.selectbox("Vincular a Turma", turmas, index=turmas.index(current_turma))
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
                            "Modulo do curso",
                            modulos,
                            index=modulos.index(modulo_atual) if modulo_atual in modulos else 0,
                        )
                        livro_atual = aluno_obj.get("livro", "")
                        livro_opts = ["Automatico (Turma)"] + book_levels()
                        if livro_atual and livro_atual not in livro_opts:
                            livro_opts.append(livro_atual)
                        livro_index = livro_opts.index(livro_atual) if livro_atual in livro_opts else 0
                        new_livro = st.selectbox("Livro/Nivel", livro_opts, index=livro_index)
                        new_vip_tipo = ""
                        new_vip_total = 0
                        new_vip_restantes = 0
                        if _is_vip_module_label(new_modulo):
                            vip_edit_opcoes = ["Aula avulsa", "Pacote 10 aulas"]
                            vip_tipo_atual = str(aluno_obj.get("vip_tipo_plano", vip_edit_opcoes[0])).strip() or vip_edit_opcoes[0]
                            if vip_tipo_atual not in vip_edit_opcoes:
                                vip_edit_opcoes.append(vip_tipo_atual)
                            new_vip_tipo = st.selectbox(
                                "Tipo do plano VIP",
                                vip_edit_opcoes,
                                index=vip_edit_opcoes.index(vip_tipo_atual) if vip_tipo_atual in vip_edit_opcoes else 0,
                            )
                            new_vip_total = _vip_plan_total(new_vip_tipo)
                            vip_restantes_atual = parse_int(aluno_obj.get("vip_aulas_restantes", new_vip_total))
                            if vip_restantes_atual is None:
                                vip_restantes_atual = new_vip_total
                            vip_restantes_atual = max(0, min(50, int(vip_restantes_atual)))
                            new_vip_restantes = int(
                                st.number_input(
                                    "Aulas restantes no pacote",
                                    min_value=0,
                                    max_value=50,
                                    step=1,
                                    value=vip_restantes_atual,
                                )
                            )
                            new_vip_total = max(int(new_vip_total), int(new_vip_restantes))

                        st.divider()
                        st.markdown("### Acesso do Aluno (opcional)")
                        ca1, ca2 = st.columns(2)
                        with ca1:
                            new_login = st.text_input("Login do Aluno", value=aluno_obj.get("usuario", ""))
                        with ca2:
                            new_senha = st.text_input("Senha do Aluno", value=aluno_obj.get("senha", ""), type="password")

                        st.divider()
                        st.markdown("### Responsavel Legal / Financeiro")
                        resp_atual = aluno_obj.get("responsavel", {})
                        if not isinstance(resp_atual, dict):
                            resp_atual = {}
                        cr1, cr2 = st.columns(2)
                        with cr1:
                            new_resp_nome = st.text_input("Nome do Responsavel", value=resp_atual.get("nome", ""))
                        with cr2:
                            new_resp_cpf = st.text_input("CPF do Responsavel", value=resp_atual.get("cpf", ""))
                        cr3, cr4 = st.columns(2)
                        with cr3:
                            new_resp_cel = st.text_input("Celular do Responsavel", value=resp_atual.get("celular", ""))
                        with cr4:
                            new_resp_email = st.text_input("E-mail do Responsavel", value=resp_atual.get("email", ""))

                        c_edit, c_del = st.columns([1, 1])
                        with c_edit:
                            save_student = st.form_submit_button("Salvar Alterações")
                            save_student_notify = st.form_submit_button("Salvar + Notificar (E-mail/WhatsApp)")
                            if save_student or save_student_notify:
                                old_login = aluno_obj.get("usuario", "").strip()
                                login = new_login.strip() or old_login
                                senha = new_senha.strip() or aluno_obj.get("senha", "")

                                if login and find_user(login) and (not old_login or login.lower() != old_login.lower()):
                                    st.error("ERRO: Este login já existe.")
                                else:
                                    idade_final = _calc_age_from_date_obj(new_dn) or current_idade
                                    if idade_final < 18 and (not str(new_resp_nome).strip() or not str(new_resp_cpf).strip()):
                                        st.error("ERRO: Aluno menor de idade! E obrigatorio preencher Nome e CPF do Responsavel.")
                                    elif not str(new_nome).strip() or not str(new_email).strip():
                                        st.error("ERRO: Nome e E-mail sao obrigatorios.")
                                    else:
                                        if login:
                                            user_obj = find_user(old_login) if old_login else None
                                            if user_obj:
                                                user_obj["usuario"] = login
                                                user_obj["senha"] = senha
                                                user_obj["perfil"] = "Aluno"
                                                user_obj["pessoa"] = str(new_nome or "").strip()
                                            else:
                                                st.session_state["users"].append(
                                                    {
                                                        "usuario": login,
                                                        "senha": senha,
                                                        "perfil": "Aluno",
                                                        "pessoa": str(new_nome or "").strip(),
                                                    }
                                                )
                                            save_users(st.session_state["users"])

                                        turma_obj = next((c for c in st.session_state["classes"] if c.get("nome") == new_turma), {})
                                        livro_turma = turma_obj.get("livro", "")
                                        livro_final = livro_turma if new_livro == "Automatico (Turma)" else new_livro

                                        aluno_obj["nome"] = str(new_nome or "").strip()
                                        aluno_obj["matricula"] = matricula_atual
                                        aluno_obj["celular"] = str(new_cel or "").strip()
                                        aluno_obj["turma"] = str(new_turma or "").strip()
                                        aluno_obj["email"] = str(new_email or "").strip().lower()
                                        aluno_obj["data_nascimento"] = new_dn.strftime("%d/%m/%Y") if new_dn else ""
                                        aluno_obj["idade"] = idade_final
                                        aluno_obj["genero"] = str(new_genero or "").strip()
                                        aluno_obj["status"] = str(new_status or "").strip() or "Ativo"
                                        aluno_obj["rg"] = str(new_rg or "").strip()
                                        aluno_obj["cpf"] = str(new_cpf or "").strip()
                                        aluno_obj["cidade_natal"] = str(new_natal or "").strip()
                                        aluno_obj["pais"] = str(new_pais or "").strip()
                                        aluno_obj["cep"] = str(new_cep or "").strip()
                                        aluno_obj["cidade"] = str(new_cidade or "").strip()
                                        aluno_obj["bairro"] = str(new_bairro or "").strip()
                                        aluno_obj["rua"] = str(new_rua or "").strip()
                                        aluno_obj["numero"] = str(new_numero or "").strip()
                                        aluno_obj["complemento"] = str(new_complemento or "").strip()
                                        aluno_obj["modulo"] = str(new_modulo or "").strip()
                                        aluno_obj["livro"] = str(livro_final or "").strip()
                                        aluno_obj["vip_tipo_plano"] = str(new_vip_tipo or "").strip() if _is_vip_module_label(new_modulo) else ""
                                        aluno_obj["vip_aulas_total"] = int(new_vip_total) if _is_vip_module_label(new_modulo) else 0
                                        aluno_obj["vip_aulas_restantes"] = int(new_vip_restantes) if _is_vip_module_label(new_modulo) else 0
                                        aluno_obj["usuario"] = str(login or "").strip()
                                        aluno_obj["senha"] = str(senha or "").strip()
                                        aluno_obj["responsavel"] = {
                                            "nome": str(new_resp_nome or "").strip(),
                                            "cpf": str(new_resp_cpf or "").strip(),
                                            "celular": str(new_resp_cel or "").strip(),
                                            "email": str(new_resp_email or "").strip().lower(),
                                        }
                                        aluno_obj.pop("nascimento", None)

                                        save_list(STUDENTS_FILE, st.session_state["students"])
                                        update_notify_stats = {"email_total": 0, "email_ok": 0, "whatsapp_total": 0, "whatsapp_ok": 0}
                                        if bool(save_student_notify):
                                            update_notify_stats = notify_student_profile_update(
                                                aluno_obj,
                                                autor=st.session_state.get("user_name", "Coordenacao"),
                                                origem="Atualizacao Aluno",
                                                send_email=True,
                                                send_whatsapp=True,
                                            )
                                        if bool(save_student_notify):
                                            st.success(
                                                "Dados atualizados! "
                                                f"E-mail {update_notify_stats.get('email_ok', 0)}/{update_notify_stats.get('email_total', 0)} | "
                                                f"WhatsApp {update_notify_stats.get('whatsapp_ok', 0)}/{update_notify_stats.get('whatsapp_total', 0)}."
                                            )
                                        else:
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

                n1, n2 = st.columns(2)
                with n1:
                    send_prof_email = st.checkbox(
                        "Enviar mensagem por e-mail",
                        value=True,
                        key="add_prof_notify_email",
                    )
                with n2:
                    send_prof_whatsapp = st.checkbox(
                        "Enviar mensagem por WhatsApp",
                        value=True,
                        key="add_prof_notify_whatsapp",
                    )

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
                                [email_prof] if bool(send_prof_email) else [],
                                [celular_prof] if bool(send_prof_whatsapp) else [],
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
                    col_class_form, col_class_students = st.columns([2.2, 1.4], gap="large")
                    with col_class_form:
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
                    with col_class_students:
                        st.markdown("#### Alunos da turma selecionada")
                        alunos_turma = [
                            {
                                "Aluno": str(aluno.get("nome", "")).strip(),
                                "Matricula": str(aluno.get("matricula", "")).strip() or "-",
                                "E-mail": str(aluno.get("email", "")).strip() or "-",
                                "WhatsApp": str(aluno.get("celular", "")).strip() or "-",
                            }
                            for aluno in st.session_state.get("students", [])
                            if str(aluno.get("turma", "")).strip() == turma_sel and str(aluno.get("nome", "")).strip()
                        ]
                        alunos_turma = sorted(alunos_turma, key=lambda item: str(item.get("Aluno", "")).lower())
                        if alunos_turma:
                            st.dataframe(
                                pd.DataFrame(alunos_turma),
                                use_container_width=True,
                                hide_index=True,
                                height=420,
                            )
                        else:
                            st.info("Nenhum aluno vinculado a esta turma.")

    elif menu_coord == "Financeiro":
        st.markdown('<div class="main-header">Financeiro</div>', unsafe_allow_html=True)
        finance_focus = str(st.session_state.get("finance_overdue_focus", "")).strip().lower()

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

        def _sort_indices_by_parcela(items, indices):
            return sorted(
                indices,
                key=lambda idx: (
                    _parse_parcela_info(items[idx].get("parcela", "1"))[0],
                    parse_date(items[idx].get("vencimento", "")) or datetime.date.today(),
                    idx,
                ),
            )

        def _related_receivable_indices(items, base_idx):
            if base_idx < 0 or base_idx >= len(items):
                return []
            base = items[base_idx]
            base_lote = str(base.get("lote_id", "")).strip()
            if base_lote:
                rel = [i for i, item in enumerate(items) if str(item.get("lote_id", "")).strip() == base_lote]
                if rel:
                    return rel
            _, base_total = _parse_parcela_info(base.get("parcela", "1"))
            if base_total <= 1:
                return [base_idx]
            base_key = (
                normalize_text(base.get("aluno", "")),
                normalize_text(base.get("descricao", "")),
                normalize_text(base.get("categoria", "")),
                normalize_text(base.get("categoria_lancamento", "Aluno")),
                normalize_text(base.get("cobranca", "")),
                str(base.get("data", "")).strip(),
                normalize_text(base.get("item_codigo", "")),
                base_total,
            )
            rel = []
            for idx, item in enumerate(items):
                _, total_item = _parse_parcela_info(item.get("parcela", "1"))
                item_key = (
                    normalize_text(item.get("aluno", "")),
                    normalize_text(item.get("descricao", "")),
                    normalize_text(item.get("categoria", "")),
                    normalize_text(item.get("categoria_lancamento", "Aluno")),
                    normalize_text(item.get("cobranca", "")),
                    str(item.get("data", "")).strip(),
                    normalize_text(item.get("item_codigo", "")),
                    total_item,
                )
                if item_key == base_key:
                    rel.append(idx)
            return rel or [base_idx]

        def _related_payable_indices(items, base_idx):
            if base_idx < 0 or base_idx >= len(items):
                return []
            base = items[base_idx]
            base_lote = str(base.get("lote_id", "")).strip()
            if base_lote:
                rel = [i for i, item in enumerate(items) if str(item.get("lote_id", "")).strip() == base_lote]
                if rel:
                    return rel
            _, base_total = _parse_parcela_info(base.get("parcela", "1"))
            if base_total <= 1:
                return [base_idx]
            base_key = (
                normalize_text(base.get("fornecedor", "")),
                normalize_text(base.get("descricao", "")),
                normalize_text(base.get("categoria_lancamento", "Fornecedor")),
                normalize_text(base.get("cobranca", "")),
                str(base.get("data", "")).strip(),
                normalize_text(base.get("numero_pedido", "")),
                base_total,
            )
            rel = []
            for idx, item in enumerate(items):
                _, total_item = _parse_parcela_info(item.get("parcela", "1"))
                item_key = (
                    normalize_text(item.get("fornecedor", "")),
                    normalize_text(item.get("descricao", "")),
                    normalize_text(item.get("categoria_lancamento", "Fornecedor")),
                    normalize_text(item.get("cobranca", "")),
                    str(item.get("data", "")).strip(),
                    normalize_text(item.get("numero_pedido", "")),
                    total_item,
                )
                if item_key == base_key:
                    rel.append(idx)
            return rel or [base_idx]

        def _month_due_date(base_date, due_day):
            ref_date = base_date if isinstance(base_date, datetime.date) else datetime.date.today()
            due_day_int = max(1, min(30, parse_int(due_day) or ref_date.day))
            month_start = ref_date.replace(day=1)
            month_end = add_months(month_start, 1) - datetime.timedelta(days=1)
            safe_day = min(due_day_int, month_end.day)
            return ref_date.replace(day=safe_day)

        def _render_overdue_receivables_panel():
            overdue_receivables = [
                r for r in _financial_overdue_items(st.session_state.get("receivables", []), date_field="vencimento")
                if str(r.get("categoria_lancamento", "Aluno")).strip() == "Aluno" and str(r.get("aluno", "")).strip()
            ]
            if not overdue_receivables:
                st.info("Nenhum recebimento vencido para alunos.")
                return
            summary_map = {}
            for item in overdue_receivables:
                aluno_nome = str(item.get("aluno", "")).strip()
                row = summary_map.setdefault(
                    aluno_nome,
                    {"aluno": aluno_nome, "qtd_vencidos": 0, "total_vencido": 0.0, "ultimo_vencimento": ""},
                )
                row["qtd_vencidos"] += 1
                row["total_vencido"] += parse_money(item.get("valor_parcela", item.get("valor", 0)))
                venc_txt = str(item.get("vencimento", "")).strip()
                venc_dt = parse_date(venc_txt)
                last_dt = parse_date(row.get("ultimo_vencimento", ""))
                if venc_dt and (not last_dt or venc_dt > last_dt):
                    row["ultimo_vencimento"] = venc_txt
            summary_rows = sorted(summary_map.values(), key=lambda r: (-r["total_vencido"], r["aluno"].lower()))
            st.markdown("#### Alunos com recebimentos vencidos")
            summary_df = pd.DataFrame(
                [
                    {
                        "aluno": row["aluno"],
                        "qtd_vencidos": row["qtd_vencidos"],
                        "total_vencido": format_money(row["total_vencido"]),
                        "ultimo_vencimento": row["ultimo_vencimento"],
                    }
                    for row in summary_rows
                ]
            )
            st.dataframe(summary_df, use_container_width=True)
            st.markdown("#### Selecionar aluno")
            selected_student = str(st.session_state.get("finance_overdue_selected_student", "")).strip()
            for row in summary_rows:
                c1, c2, c3, c4 = st.columns([2.2, 1, 1, 0.9])
                with c1:
                    st.markdown(f"**{row['aluno']}**")
                with c2:
                    st.caption(f"{row['qtd_vencidos']} vencido(s)")
                with c3:
                    st.caption(format_money(row["total_vencido"]))
                with c4:
                    if st.button("Ver", key=f"finance_overdue_student_btn_{row['aluno']}"):
                        st.session_state["finance_overdue_selected_student"] = row["aluno"]
                        selected_student = row["aluno"]
                        st.rerun()
            if not selected_student and summary_rows:
                selected_student = summary_rows[0]["aluno"]
            if selected_student:
                st.markdown(f"#### Pagamentos vencidos de {selected_student}")
                student_items = [
                    {
                        "codigo": str(item.get("codigo", "")).strip(),
                        "descricao": str(item.get("descricao", "")).strip(),
                        "categoria": str(item.get("categoria", "")).strip(),
                        "valor_parcela": str(item.get("valor_parcela", item.get("valor", ""))).strip(),
                        "parcela": str(item.get("parcela", "")).strip(),
                        "vencimento": str(item.get("vencimento", "")).strip(),
                        "cobranca": str(item.get("cobranca", "")).strip(),
                        "status": str(item.get("status", "")).strip(),
                    }
                    for item in overdue_receivables
                    if str(item.get("aluno", "")).strip() == selected_student
                ]
                st.dataframe(pd.DataFrame(student_items), use_container_width=True)

        def _render_overdue_payables_panel():
            overdue_payables = _financial_overdue_items(st.session_state.get("payables", []), date_field="vencimento")
            if not overdue_payables:
                st.info("Nenhuma conta a pagar vencida.")
                return
            summary_map = {}
            for item in overdue_payables:
                fornecedor = str(item.get("fornecedor", "")).strip() or "Sem fornecedor"
                row = summary_map.setdefault(
                    fornecedor,
                    {"fornecedor": fornecedor, "qtd_vencidos": 0, "total_vencido": 0.0, "ultimo_vencimento": ""},
                )
                row["qtd_vencidos"] += 1
                row["total_vencido"] += parse_money(item.get("valor_parcela", item.get("valor", 0)))
                venc_txt = str(item.get("vencimento", "")).strip()
                venc_dt = parse_date(venc_txt)
                last_dt = parse_date(row.get("ultimo_vencimento", ""))
                if venc_dt and (not last_dt or venc_dt > last_dt):
                    row["ultimo_vencimento"] = venc_txt
            summary_rows = sorted(summary_map.values(), key=lambda r: (-r["total_vencido"], r["fornecedor"].lower()))
            st.markdown("#### Contas a pagar vencidas")
            summary_df = pd.DataFrame(
                [
                    {
                        "fornecedor": row["fornecedor"],
                        "qtd_vencidos": row["qtd_vencidos"],
                        "total_vencido": format_money(row["total_vencido"]),
                        "ultimo_vencimento": row["ultimo_vencimento"],
                    }
                    for row in summary_rows
                ]
            )
            st.dataframe(summary_df, use_container_width=True)
            selected_supplier = str(st.session_state.get("finance_overdue_selected_supplier", "")).strip()
            for row in summary_rows:
                c1, c2, c3, c4 = st.columns([2.2, 1, 1, 0.9])
                with c1:
                    st.markdown(f"**{row['fornecedor']}**")
                with c2:
                    st.caption(f"{row['qtd_vencidos']} vencido(s)")
                with c3:
                    st.caption(format_money(row["total_vencido"]))
                with c4:
                    if st.button("Ver", key=f"finance_overdue_supplier_btn_{row['fornecedor']}"):
                        st.session_state["finance_overdue_selected_supplier"] = row["fornecedor"]
                        selected_supplier = row["fornecedor"]
                        st.rerun()
            if not selected_supplier and summary_rows:
                selected_supplier = summary_rows[0]["fornecedor"]
            if selected_supplier:
                st.markdown(f"#### Contas vencidas de {selected_supplier}")
                supplier_items = [
                    {
                        "codigo": str(item.get("codigo", "")).strip(),
                        "descricao": str(item.get("descricao", "")).strip(),
                        "categoria_lancamento": str(item.get("categoria_lancamento", "")).strip(),
                        "valor_parcela": str(item.get("valor_parcela", item.get("valor", ""))).strip(),
                        "parcela": str(item.get("parcela", "")).strip(),
                        "vencimento": str(item.get("vencimento", "")).strip(),
                        "cobranca": str(item.get("cobranca", "")).strip(),
                        "status": str(item.get("status", "")).strip(),
                    }
                    for item in overdue_payables
                    if (str(item.get("fornecedor", "")).strip() or "Sem fornecedor") == selected_supplier
                ]
                st.dataframe(pd.DataFrame(supplier_items), use_container_width=True)

        if finance_focus in ("receber", "pagar"):
            with st.container(border=True):
                st.markdown("### Vencimentos em destaque")
                st.caption("Atalho aberto a partir do Painel do Coordenador.")
                if finance_focus == "receber":
                    _render_overdue_receivables_panel()
                else:
                    _render_overdue_payables_panel()
                if st.button("Fechar destaque de vencimentos", key="finance_close_overdue_focus"):
                    st.session_state.pop("finance_overdue_focus", None)
                    st.rerun()

        finance_main_options = ["Contas a Receber", "Contas a Pagar", "Aprovacoes Comercial", "Vencimentos"]
        if finance_focus in ("receber", "pagar"):
            st.session_state["finance_main_menu"] = "Vencimentos"
        if st.session_state.get("finance_main_menu") not in finance_main_options:
            st.session_state["finance_main_menu"] = finance_main_options[0]
        st.markdown('<div class="finance-radio-anchor"></div>', unsafe_allow_html=True)
        finance_main = st.radio(
            "Area do financeiro",
            finance_main_options,
            horizontal=True,
            key="finance_main_menu",
            label_visibility="collapsed",
        )

        if finance_main == "Contas a Receber":
            finance_receber_options = [
                "Lancar Recebimento",
                "Recebimentos",
                "Acoes em massa (Recebimentos)",
                "Gerenciamento de Recebimentos",
                "Lancar Material do Estoque",
                "Baixa de Recebimentos",
                "Configuracao automatica de e-mail e boleto",
            ]
            if st.session_state.get("finance_receber_menu") not in finance_receber_options:
                st.session_state["finance_receber_menu"] = finance_receber_options[0]
            finance_receber_menu = st.radio(
                "Opcoes de Contas a Receber",
                finance_receber_options,
                key="finance_receber_menu",
            )
            if finance_receber_menu == "Configuracao automatica de e-mail e boleto":
                with st.expander("Configuracao automatica de e-mail e boleto", expanded=True):
                    smtp_diag = _smtp_config_diagnostics()
                    boleto_diag = _boleto_config_diagnostics()
                    whatsapp_diag = _whatsapp_config_diagnostics()
                    smtp_ready = smtp_diag["host_ok"] and smtp_diag["port_ok"] and smtp_diag["from_ok"]
                    boleto_ready = boleto_diag["template_ok"] or boleto_diag["base_url_ok"] or boleto_diag["api_url_ok"]

                    d1, d2, d3 = st.columns(3)
                    with d1:
                        st.metric("SMTP", "Configurado" if smtp_ready else "Pendente")
                    with d2:
                        st.metric("Boleto", "Configurado" if boleto_ready else "Pendente")
                    with d3:
                        st.metric("WhatsApp", "Configurado" if whatsapp_diag.get("wapi_ready") or whatsapp_diag.get("evolution_ready") else "Pendente")

                    st.caption(
                        "Se variaveis de ambiente estiverem definidas (ACTIVE_*), elas tem prioridade sobre os campos abaixo."
                    )

                    current_cfg = get_finance_settings()
                    with st.form("finance_auto_cfg_form"):
                        st.markdown("#### SMTP (envio de e-mail)")
                        sm1, sm2, sm3 = st.columns(3)
                        with sm1:
                            cfg_smtp_host = st.text_input("Servidor SMTP", value=str(current_cfg.get("smtp_host", "")))
                        with sm2:
                            cfg_smtp_port = st.text_input("Porta SMTP", value=str(current_cfg.get("smtp_port", "587")))
                        with sm3:
                            cfg_smtp_tls = st.selectbox(
                                "TLS",
                                ["1", "0"],
                                index=0 if str(current_cfg.get("smtp_tls", "1")) != "0" else 1,
                                format_func=lambda v: "Ativo" if str(v) == "1" else "Desativado",
                            )
                        sm4, sm5, sm6 = st.columns(3)
                        with sm4:
                            cfg_smtp_user = st.text_input("Usuario SMTP", value=str(current_cfg.get("smtp_user", "")))
                        with sm5:
                            cfg_smtp_pass = st.text_input("Senha SMTP", value=str(current_cfg.get("smtp_pass", "")), type="password")
                        with sm6:
                            cfg_smtp_from = st.text_input("E-mail remetente", value=str(current_cfg.get("smtp_from", "")))

                        st.markdown("#### Boleto")
                        bl1, bl2 = st.columns(2)
                        with bl1:
                            cfg_boleto_provider = st.selectbox(
                                "Provedor",
                                ["link", "api"],
                                index=0 if str(current_cfg.get("boleto_provider", "link")).strip().lower() != "api" else 1,
                            )
                        with bl2:
                            cfg_boleto_base_url = st.text_input(
                                "Base URL do boleto (opcional)",
                                value=str(current_cfg.get("boleto_base_url", "")),
                                help="Se informar somente a base URL, o sistema adiciona os parametros automaticamente.",
                            )
                        cfg_boleto_template = st.text_input(
                            "Template do link (opcional)",
                            value=str(current_cfg.get("boleto_link_template", "")),
                            help="Exemplo: https://provedor.com/boleto/{codigo}?aluno={aluno}",
                        )
                        bl3, bl4, bl5 = st.columns(3)
                        with bl3:
                            cfg_boleto_api_url = st.text_input("API URL (opcional)", value=str(current_cfg.get("boleto_api_url", "")))
                        with bl4:
                            cfg_boleto_api_key = st.text_input("API Key (opcional)", value=str(current_cfg.get("boleto_api_key", "")), type="password")
                        with bl5:
                            cfg_boleto_api_auth = st.text_input(
                                "Header da API Key",
                                value=str(current_cfg.get("boleto_api_auth_header", "Authorization")),
                                help="Exemplo: Authorization ou apikey",
                            )

                        salvar_fin_cfg = st.form_submit_button("Salvar configuracoes automaticas")
                        if salvar_fin_cfg:
                            save_finance_settings(
                                {
                                    "smtp_host": cfg_smtp_host,
                                    "smtp_port": cfg_smtp_port,
                                    "smtp_user": cfg_smtp_user,
                                    "smtp_pass": cfg_smtp_pass,
                                    "smtp_tls": cfg_smtp_tls,
                                    "smtp_from": cfg_smtp_from,
                                    "boleto_provider": cfg_boleto_provider,
                                    "boleto_base_url": cfg_boleto_base_url,
                                    "boleto_link_template": cfg_boleto_template,
                                    "boleto_api_url": cfg_boleto_api_url,
                                    "boleto_api_key": cfg_boleto_api_key,
                                    "boleto_api_auth_header": cfg_boleto_api_auth,
                                }
                            )
                            st.success("Configuracoes financeiras salvas.")
                            st.rerun()

            if finance_receber_menu == "Lancar Recebimento":
                with st.form("add_rec"):
                    st.markdown("### Lançar Recebimento")
                    c1, c2, c3, c4 = st.columns(4)
                    with c1: desc = st.text_input("Descricao (Ex: Mensalidade)")
                    with c2: val_parcela_input = st.text_input("Valor Parcela * (Ex: 150,00)")
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
                    c4, c5, c6, c6b = st.columns(4)
                    with c4: data_lanc = st.date_input("Data do lançamento", value=datetime.date.today(), format="DD/MM/YYYY")
                    with c5: venc = st.date_input("Primeiro vencimento", value=datetime.date.today(), format="DD/MM/YYYY")
                    with c6b:
                        rec_due_day = st.selectbox(
                            "Dia do vencimento",
                            list(range(1, 31)),
                            index=max(0, min(29, datetime.date.today().day - 1)),
                            format_func=lambda d: f"Dia {d}",
                        )
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
                    with c7:
                        parcela_inicial = st.number_input("Parcela inicial", min_value=1, step=1, value=1, disabled=is_material)
                    material_parcelado = categoria == "Material" and material_payment in ("Parcelado no Cartao", "Parcelado no Boleto")
                    if categoria == "Mensalidade":
                        qtd_meses = st.number_input("Parcelas *", min_value=1, max_value=24, value=12)
                    elif categoria == "Material":
                        qtd_meses = st.number_input(
                            "Parcelas *",
                            min_value=1,
                            max_value=6,
                            value=2 if material_parcelado else 1,
                            disabled=not material_parcelado,
                        )
                    else:
                        qtd_meses = st.number_input("Parcelas *", min_value=1, max_value=24, value=1)

                    if categoria == "Material" and not material_parcelado:
                        qtd_parcelas_calc = 1
                    else:
                        qtd_parcelas_calc = max(1, int(qtd_meses))

                    valor_parcela_num = parse_money(val_parcela_input)
                    valor_parcela_txt = f"{valor_parcela_num:.2f}".replace(".", ",") if valor_parcela_num > 0 else "0,00"
                    valor_total_num = valor_parcela_num * max(1, int(qtd_parcelas_calc))
                    valor_total_auto = f"{valor_total_num:.2f}".replace(".", ",")
                    with c9:
                        st.text_input("Valor Total * (automatico)", value=valor_total_auto, disabled=True, key="rec_valor_total_auto")
                    d1, d2 = st.columns(2)
                    with d1:
                        enviar_fin_email = st.checkbox(
                            "Enviar comunicado por e-mail",
                            value=True,
                            key="rec_notify_email",
                            disabled=(categoria_lancamento != "Aluno"),
                        )
                    with d2:
                        enviar_fin_whatsapp = st.checkbox(
                            "Enviar comunicado por WhatsApp",
                            value=True,
                            key="rec_notify_whatsapp",
                            disabled=(categoria_lancamento != "Aluno"),
                        )
                    if categoria_lancamento != "Aluno":
                        st.caption("Envio automático de e-mail/WhatsApp disponível para lançamentos da categoria Aluno.")

                    if st.form_submit_button("Lancar"):
                        if not str(aluno).strip() or valor_parcela_num <= 0:
                            st.error("Informe referencia e valor da parcela valido.")
                        elif categoria_lancamento == "Aluno" and not enviar_fin_email and not enviar_fin_whatsapp:
                            st.error("Ative pelo menos um canal: e-mail ou WhatsApp.")
                        else:
                            before_count = len(st.session_state.get("receivables", []))
                            total_lancados = 0
                            lote_id_rec = f"REC-LOT-{uuid.uuid4().hex[:10].upper()}"
                            venc_base = _month_due_date(venc, rec_due_day)
                            if categoria == "Mensalidade":
                                for i in range(qtd_parcelas_calc):
                                    data_venc = add_months(venc_base, i)
                                    parcela = f"{parcela_inicial + i}/{qtd_parcelas_calc}"
                                    add_receivable(
                                        aluno,
                                        desc,
                                        valor_total_auto,
                                        data_venc,
                                        cobranca,
                                        categoria,
                                        data_lancamento=data_lanc,
                                        valor_parcela=valor_parcela_txt,
                                        parcela=parcela,
                                        categoria_lancamento=categoria_lancamento,
                                        lote_id=lote_id_rec,
                                    )
                                    total_lancados += 1
                                st.success(f"Mensalidades lancadas! ({total_lancados} parcelas)")
                            elif categoria == "Material":
                                qtd_material = qtd_parcelas_calc
                                for i in range(qtd_material):
                                    data_venc = add_months(venc_base, i)
                                    parcela = f"{1 + i}/{qtd_material}" if qtd_material > 1 else "1"
                                    add_receivable(
                                        aluno,
                                        desc or "Material",
                                        valor_total_auto,
                                        data_venc,
                                        cobranca,
                                        categoria,
                                        data_lancamento=data_lanc,
                                        valor_parcela=valor_parcela_txt,
                                        parcela=parcela,
                                        categoria_lancamento=categoria_lancamento,
                                        lote_id=lote_id_rec,
                                    )
                                    total_lancados += 1
                                st.success(f"Material lancado com parcelamento em {qtd_material}x.")
                            else:
                                for i in range(qtd_parcelas_calc):
                                    data_venc = add_months(venc_base, i) if qtd_parcelas_calc > 1 else venc_base
                                    parcela = f"{parcela_inicial + i}/{qtd_parcelas_calc}" if qtd_parcelas_calc > 1 else str(parcela_inicial)
                                    add_receivable(
                                        aluno,
                                        desc,
                                        valor_total_auto,
                                        data_venc,
                                        cobranca,
                                        categoria,
                                        data_lancamento=data_lanc,
                                        valor_parcela=valor_parcela_txt,
                                        parcela=parcela,
                                        categoria_lancamento=categoria_lancamento,
                                        lote_id=lote_id_rec,
                                    )
                                    total_lancados += 1
                                st.success(f"Lancado! ({total_lancados} parcela(s))")
                            if wiz_event_enabled("on_financial_created") and categoria_lancamento == "Aluno":
                                new_items = st.session_state.get("receivables", [])[before_count:]
                                stats_fin = notify_student_financial_event(
                                    aluno,
                                    new_items,
                                    send_email=bool(enviar_fin_email),
                                    send_whatsapp=bool(enviar_fin_whatsapp),
                                )
                                st.info(
                                    "Disparos financeiros: "
                                    f"E-mail {stats_fin.get('email_ok', 0)}/{stats_fin.get('email_total', 0)} | "
                                    f"WhatsApp {stats_fin.get('whatsapp_ok', 0)}/{stats_fin.get('whatsapp_total', 0)}."
                                )
            recebimentos = st.session_state["receivables"]
            recebimentos_filtrados = list(recebimentos)
            rec_bulk_all_codes = []
            rec_bulk_filtered_codes = []
            rec_labels_by_code = {}
            if finance_receber_menu in ("Recebimentos", "Acoes em massa (Recebimentos)"):
                st.markdown("### Recebimentos")
                with st.container(border=True):
                    st.markdown("#### Filtros de Recebimentos")
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
                    busca = st.text_input("Buscar por descricao")

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
                        "boleto_status",
                        "boleto_enviado_em",
                    ]
                    df_rec = df_rec[[c for c in col_order if c in df_rec.columns]]
                    st.dataframe(df_rec, use_container_width=True)
                else:
                    st.info("Nenhum recebimento encontrado.")

            if finance_receber_menu == "Acoes em massa (Recebimentos)":
                st.markdown("### Acoes em massa (Recebimentos)")
                if st.session_state.pop("fin_rec_bulk_reset_pending", False):
                    st.session_state.pop("fin_rec_bulk_codes", None)
                    st.session_state.pop("fin_rec_bulk_confirm_delete", None)
                rec_bulk_all_codes = list(
                    dict.fromkeys(
                        [
                            str(r.get("codigo", "")).strip()
                            for r in recebimentos
                            if str(r.get("codigo", "")).strip()
                        ]
                    )
                )
                rec_bulk_filtered_codes = list(
                    dict.fromkeys(
                        [
                            str(r.get("codigo", "")).strip()
                            for r in recebimentos_filtrados
                            if str(r.get("codigo", "")).strip()
                        ]
                    )
                )
                rec_labels_by_code = {}
                for r in recebimentos:
                    codigo_item = str(r.get("codigo", "")).strip()
                    if not codigo_item:
                        continue
                    rec_labels_by_code[codigo_item] = (
                        f"{codigo_item} | {str(r.get('aluno', '')).strip()} | "
                        f"{str(r.get('descricao', '')).strip()} | Parcela {str(r.get('parcela', '')).strip()} | "
                        f"{str(r.get('valor_parcela', r.get('valor', ''))).strip()} | {str(r.get('status', '')).strip()}"
                    )

                rbk1, rbk2, rbk3, rbk4 = st.columns(4)
                with rbk1:
                    if st.button("Selecionar filtrados", key="fin_rec_bulk_sel_filtered"):
                        st.session_state["fin_rec_bulk_codes"] = list(rec_bulk_filtered_codes)
                        st.rerun()
                with rbk2:
                    if st.button("Selecionar TODOS", key="fin_rec_bulk_sel_all"):
                        st.session_state["fin_rec_bulk_codes"] = list(rec_bulk_all_codes)
                        st.rerun()
                with rbk3:
                    if st.button("Limpar selecao", key="fin_rec_bulk_sel_clear"):
                        st.session_state["fin_rec_bulk_codes"] = []
                        st.rerun()
                with rbk4:
                    st.caption(f"Filtrados: {len(rec_bulk_filtered_codes)} | Base: {len(rec_bulk_all_codes)}")

                selected_rec_codes = st.multiselect(
                    "Selecionar recebimentos",
                    rec_bulk_all_codes,
                    key="fin_rec_bulk_codes",
                    format_func=lambda code: rec_labels_by_code.get(code, code),
                )
                rbk5, rbk6 = st.columns([1.6, 2.4])
                with rbk5:
                    rec_bulk_confirm = st.checkbox(
                        "Confirmo exclusao em massa",
                        value=False,
                        key="fin_rec_bulk_confirm_delete",
                    )
                with rbk6:
                    if st.button(
                        "Excluir recebimentos selecionados",
                        type="primary",
                        key="fin_rec_bulk_delete_btn",
                        disabled=not bool(selected_rec_codes),
                    ):
                        if not rec_bulk_confirm:
                            st.error("Marque a confirmacao para excluir em massa.")
                        else:
                            before_rec = len(st.session_state.get("receivables", []))
                            st.session_state["receivables"] = [
                                r
                                for r in st.session_state.get("receivables", [])
                                if str(r.get("codigo", "")).strip() not in selected_rec_codes
                            ]
                            removed_rec = before_rec - len(st.session_state.get("receivables", []))
                            save_list(RECEIVABLES_FILE, st.session_state["receivables"])
                            st.session_state["fin_rec_bulk_reset_pending"] = True
                            st.success(f"{removed_rec} recebimento(s) excluido(s).")
                            st.rerun()

            if finance_receber_menu == "Gerenciamento de Recebimentos":
                st.markdown("### Gerenciamento de Recebimentos (Editar/Excluir Cobranca)")
                if not recebimentos:
                    st.info("Nenhum recebimento para gerenciar.")
                else:
                    opcoes_rec = [
                        f"{r.get('codigo','')} | {r.get('aluno','')} | {r.get('descricao','')} | Venc: {r.get('vencimento','')}"
                        for r in recebimentos
                    ]
                    idx_rec = st.selectbox(
                        "Selecione a cobranca para editar/excluir",
                        list(range(len(recebimentos))),
                        format_func=lambda i: opcoes_rec[i],
                        key="manage_rec_idx",
                    )
                    rec_obj = recebimentos[idx_rec]
                    rec_obj.setdefault("boleto_url", "")
                    rec_obj.setdefault("boleto_linha_digitavel", "")
                    rec_obj.setdefault("boleto_status", "Nao Gerado")
                    rec_obj.setdefault("boleto_gerado_em", "")
                    rec_obj.setdefault("boleto_enviado_em", "")
                    rec_obj.setdefault("boleto_enviado_canais", "")
                    parcela_atual_rec, qtd_atual_rec = _parse_parcela_info(rec_obj.get("parcela", "1/1"))
                    venc_atual_rec = parse_date(rec_obj.get("vencimento", "")) or datetime.date.today()
                    qtd_base_rec = max(1, int(qtd_atual_rec))
                    valor_parcela_base_rec_num = parse_money(rec_obj.get("valor_parcela", ""))
                    if valor_parcela_base_rec_num <= 0:
                        valor_total_base_rec_num = parse_money(rec_obj.get("valor", ""))
                        if valor_total_base_rec_num > 0:
                            valor_parcela_base_rec_num = valor_total_base_rec_num / qtd_base_rec
                    valor_parcela_base_rec_txt = (
                        f"{valor_parcela_base_rec_num:.2f}".replace(".", ",")
                        if valor_parcela_base_rec_num > 0
                        else ""
                    )

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
                            new_val_parcela_rec_input = st.text_input(
                                "Valor da parcela",
                                value=valor_parcela_base_rec_txt,
                            )
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

                        new_val_parcela_num = parse_money(new_val_parcela_rec_input)
                        new_qtd_rec_int = max(1, int(new_qtd_rec))
                        new_val_total_num = new_val_parcela_num * new_qtd_rec_int
                        new_valor_parcela_rec = f"{new_val_parcela_num:.2f}".replace(".", ",") if new_val_parcela_num > 0 else "0,00"
                        new_val_total_rec_auto = f"{new_val_total_num:.2f}".replace(".", ",") if new_val_total_num > 0 else "0,00"
                        st.text_input("Valor total (automatico)", value=new_val_total_rec_auto, disabled=True)

                        mb1, mb2 = st.columns(2)
                        with mb1:
                            new_boleto_url = st.text_input("Link do boleto", value=str(rec_obj.get("boleto_url", "")))
                        with mb2:
                            new_boleto_linha = st.text_input("Linha digitavel", value=str(rec_obj.get("boleto_linha_digitavel", "")))

                        related_preview_idx = _related_receivable_indices(recebimentos, idx_rec)
                        total_relacionados = len(set(related_preview_idx)) if related_preview_idx else 1
                        apply_all_rec = True
                        st.info(
                            "Edicao em lote ativa: ao salvar, o sistema atualiza todas as parcelas do mesmo lancamento "
                            f"({total_relacionados} parcela(s))."
                        )

                        mc1, mc2 = st.columns(2)
                        with mc1:
                            salvar_rec = st.form_submit_button("Salvar cobranca (todas parcelas)")
                        with mc2:
                            excluir_rec = st.form_submit_button("Excluir cobranca (todas parcelas)", type="primary")

                    if salvar_rec:
                        if not new_ref_rec.strip() or new_val_parcela_num <= 0:
                            st.error("Informe referencia e valor da parcela valido.")
                        else:
                                lote_id_rec = str(rec_obj.get("lote_id", "")).strip() or f"REC-LOT-{uuid.uuid4().hex[:10].upper()}"
                                ref_data_rec = str(rec_obj.get("data", "")).strip() or datetime.date.today().strftime("%d/%m/%Y")
                                ref_item_codigo = str(rec_obj.get("item_codigo", "")).strip()
                                new_boleto_url_txt = str(new_boleto_url).strip()
                                new_boleto_linha_txt = _format_boleto_linha(new_boleto_linha)
                                new_boleto_status = "Gerado" if (new_boleto_url_txt or new_boleto_linha_txt) else "Nao Gerado"
                                new_boleto_em = datetime.datetime.now().strftime("%d/%m/%Y %H:%M") if new_boleto_status == "Gerado" else ""

                                if apply_all_rec:
                                    related_idx = _related_receivable_indices(recebimentos, idx_rec)
                                    related_idx = _sort_indices_by_parcela(recebimentos, related_idx)
                                    if not related_idx:
                                        related_idx = [idx_rec]
                                    related_items = [recebimentos[i] for i in related_idx if 0 <= i < len(recebimentos)]
                                    existing_codes = [str(item.get("codigo", "")).strip() for item in related_items if str(item.get("codigo", "")).strip()]
                                    if not existing_codes:
                                        existing_codes = [str(rec_obj.get("codigo", "")).strip()] if str(rec_obj.get("codigo", "")).strip() else []

                                    parcela_base = max(1, parcela_atual_rec)
                                    primeiro_venc = add_months(new_venc_rec, -(parcela_base - 1)) if parcela_base > 1 else new_venc_rec
                                    if primeiro_venc is None:
                                        primeiro_venc = new_venc_rec

                                    related_set = set(related_idx)
                                    st.session_state["receivables"] = [
                                        r for pos, r in enumerate(recebimentos) if pos not in related_set
                                    ]
                                    recebimentos = st.session_state["receivables"]

                                    prefix_rec = re.sub(r"[^A-Z0-9]+", "", str(new_cobranca_rec).upper()) or "REC"
                                    for i in range(new_qtd_rec_int):
                                        codigo_item = (
                                            existing_codes[i]
                                            if i < len(existing_codes) and existing_codes[i]
                                            else f"{prefix_rec}-{uuid.uuid4().hex[:8].upper()}"
                                        )
                                        venc_item = add_months(primeiro_venc, i) or new_venc_rec
                                        parcela_txt = f"{i + 1}/{new_qtd_rec_int}" if new_qtd_rec_int > 1 else "1"
                                        st.session_state["receivables"].append(
                                            {
                                                "descricao": new_desc_rec.strip() or rec_obj.get("descricao", "Mensalidade"),
                                                "aluno": new_ref_rec.strip(),
                                                "categoria": new_cat_rec,
                                                "categoria_lancamento": new_cat_lanc_rec,
                                                "cobranca": new_cobranca_rec,
                                                "codigo": codigo_item,
                                                "valor": new_val_total_rec_auto,
                                                "data": ref_data_rec,
                                                "valor_parcela": new_valor_parcela_rec,
                                                "parcela": parcela_txt,
                                                "numero_pedido": "",
                                                "item_codigo": ref_item_codigo,
                                                "lote_id": lote_id_rec,
                                                "vencimento": venc_item.strftime("%d/%m/%Y"),
                                                "status": new_status_rec,
                                                "boleto_url": new_boleto_url_txt,
                                                "boleto_linha_digitavel": new_boleto_linha_txt,
                                                "boleto_status": new_boleto_status,
                                                "boleto_gerado_em": new_boleto_em,
                                                "boleto_enviado_em": "",
                                                "boleto_enviado_canais": "",
                                            }
                                        )
                                else:
                                    rec_obj["descricao"] = new_desc_rec.strip() or rec_obj.get("descricao", "Mensalidade")
                                    rec_obj["aluno"] = new_ref_rec.strip()
                                    rec_obj["categoria"] = new_cat_rec
                                    rec_obj["categoria_lancamento"] = new_cat_lanc_rec
                                    rec_obj["cobranca"] = new_cobranca_rec
                                    rec_obj["valor"] = new_val_total_rec_auto
                                    rec_obj["valor_parcela"] = new_valor_parcela_rec
                                    rec_obj["vencimento"] = new_venc_rec.strftime("%d/%m/%Y")
                                    rec_obj["status"] = new_status_rec
                                    rec_obj["parcela"] = f"{parcela_atual_rec}/{new_qtd_rec_int}" if new_qtd_rec_int > 1 else str(parcela_atual_rec)
                                    rec_obj["numero_pedido"] = ""
                                    rec_obj["item_codigo"] = ref_item_codigo
                                    rec_obj["lote_id"] = lote_id_rec
                                    rec_obj["boleto_url"] = new_boleto_url_txt
                                    rec_obj["boleto_linha_digitavel"] = new_boleto_linha_txt
                                    rec_obj["boleto_status"] = new_boleto_status
                                    if new_boleto_status == "Gerado":
                                        if not rec_obj.get("boleto_gerado_em"):
                                            rec_obj["boleto_gerado_em"] = new_boleto_em
                                    else:
                                        rec_obj["boleto_gerado_em"] = ""
                                    rec_obj["boleto_enviado_em"] = ""
                                    rec_obj["boleto_enviado_canais"] = ""
                                save_list(RECEIVABLES_FILE, st.session_state["receivables"])
                                st.success("Cobranca atualizada em lote!")
                                st.rerun()

                        if excluir_rec:
                            related_del_idx = _related_receivable_indices(recebimentos, idx_rec)
                            related_del_idx = sorted(set(related_del_idx), reverse=True)
                            removed_count = 0
                            for del_idx in related_del_idx:
                                if 0 <= del_idx < len(st.session_state.get("receivables", [])):
                                    st.session_state["receivables"].pop(del_idx)
                                    removed_count += 1
                            save_list(RECEIVABLES_FILE, st.session_state["receivables"])
                            st.success(f"Cobranca excluida em lote ({removed_count} parcela(s)).")
                            st.rerun()

                    aluno_lancamento = str(rec_obj.get("categoria_lancamento", "Aluno")).strip() == "Aluno"
                    st.caption("Boleto automatico: gere o boleto e envie diretamente por e-mail e WhatsApp.")
                    rb1, rb2, rb3 = st.columns([1, 1, 2])
                    with rb1:
                        if st.button("Gerar boleto", key=f"fin_gen_boleto_{idx_rec}_{rec_obj.get('codigo','')}"):
                            ok_bol, status_bol = generate_boleto_for_receivable(rec_obj, force=True)
                            if ok_bol:
                                st.success(f"Boleto gerado: {status_bol}.")
                            else:
                                st.error(f"Falha ao gerar boleto: {status_bol}.")
                            st.rerun()
                    with rb2:
                        if st.button(
                            "Gerar e enviar",
                            key=f"fin_send_boleto_{idx_rec}_{rec_obj.get('codigo','')}",
                            disabled=not aluno_lancamento,
                            help="Disponivel somente para lancamentos com categoria 'Aluno'.",
                        ):
                            ok_send, status_send, stats_send = send_receivable_boleto_to_student(rec_obj)
                            if ok_send:
                                st.success(
                                    "Boleto enviado. "
                                    f"E-mail {stats_send.get('email_ok', 0)}/{stats_send.get('email_total', 0)} | "
                                    f"WhatsApp {stats_send.get('whatsapp_ok', 0)}/{stats_send.get('whatsapp_total', 0)}."
                                )
                            else:
                                st.error(f"Falha no envio: {status_send}.")
                            st.rerun()
                    with rb3:
                        if rec_obj.get("boleto_url"):
                            st.markdown(f"[Abrir boleto]({rec_obj.get('boleto_url')})")
                        if rec_obj.get("boleto_linha_digitavel"):
                            st.caption(f"Linha digitavel: {rec_obj.get('boleto_linha_digitavel')}")
                        if rec_obj.get("boleto_enviado_em"):
                            st.caption(
                                f"Enviado em {rec_obj.get('boleto_enviado_em')} "
                                f"({rec_obj.get('boleto_enviado_canais', '')})"
                            )

            if finance_receber_menu == "Lancar Material do Estoque":
                with st.container(border=True):
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
                            due_day_mat = st.selectbox(
                                "Dia do vencimento",
                                list(range(1, 31)),
                                index=max(0, min(29, datetime.date.today().day - 1)),
                                format_func=lambda d: f"Dia {d}",
                                key="due_day_mat_fin",
                            )
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
                                venc_base_mat = _month_due_date(venc, due_day_mat)
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
                                    lote_id_mat = f"REC-LOT-{uuid.uuid4().hex[:10].upper()}"
                                    for i in range(parcelas):
                                        data_venc = add_months(venc_base_mat, i)
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
                                            lote_id=lote_id_mat,
                                        )
                                        count += 1
                                st.success(f"Material lançado no financeiro! ({count} parcelas)")
                                st.rerun()

            if finance_receber_menu == "Baixa de Recebimentos":
                with st.container(border=True):
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
        if finance_main == "Contas a Pagar":
            finance_pagar_options = [
                "Pagamento de Aulas do Professor",
                "Lancar Despesa",
                "Despesas",
                "Acoes em massa (Despesas)",
                "Gerenciamento de Despesas",
            ]
            if st.session_state.get("finance_pagar_menu") not in finance_pagar_options:
                st.session_state["finance_pagar_menu"] = finance_pagar_options[0]
            finance_pagar_menu = st.radio(
                "Opcoes de Contas a Pagar",
                finance_pagar_options,
                key="finance_pagar_menu",
            )
            if st.session_state.pop("fin_teacher_pay_reset_pending", False):
                st.session_state.pop("fin_teacher_pay_selected_refs", None)
            with st.container(border=True):
                st.markdown("### Lancar Pagamento de Aulas do Professor")
                st.caption("Valores automaticos: 30min = R$ 25,00 | 1 hora = R$ 50,00 | 2 horas = R$ 100,00.")
                tp1, tp2, tp3 = st.columns(3)
                with tp1:
                    teacher_pay_month_ref = st.date_input(
                        "Mes de referencia",
                        value=datetime.date.today(),
                        format="DD/MM/YYYY",
                        key="fin_teacher_pay_month_ref",
                    )
                teacher_options = ["Todos"] + sorted(
                    {
                        str(t.get("nome", "")).strip()
                        for t in st.session_state.get("teachers", [])
                        if str(t.get("nome", "")).strip()
                    }
                )
                turma_options_pay = ["Todas"] + class_names()
                with tp2:
                    teacher_pay_prof = st.selectbox("Professor", teacher_options, key="fin_teacher_pay_prof")
                with tp3:
                    teacher_pay_turma = st.selectbox("Turma", turma_options_pay, key="fin_teacher_pay_turma")

                teacher_candidates = _teacher_payment_candidates(
                    month_ref=teacher_pay_month_ref,
                    professor_name=teacher_pay_prof,
                    turma_name=teacher_pay_turma,
                )
                teacher_labels = {
                    item["ref"]: (
                        f"{item['data']} | {item['professor']} | {item['turma']} | "
                        f"{item['modulo'] or 'Modulo nao informado'} | "
                        f"{item['minutos']} min | {format_money(item['valor'])}"
                    )
                    for item in teacher_candidates
                }
                teacher_total = sum(float(item.get("valor", 0) or 0) for item in teacher_candidates)
                st.caption(
                    f"Aulas finalizadas disponiveis: {len(teacher_candidates)} | "
                    f"Total potencial: {format_money(teacher_total)}"
                )
                selected_teacher_refs = st.multiselect(
                    "Aulas finalizadas para lancar pagamento",
                    [item["ref"] for item in teacher_candidates],
                    key="fin_teacher_pay_selected_refs",
                    format_func=lambda ref: teacher_labels.get(ref, ref),
                )
                selected_teacher_items = [item for item in teacher_candidates if item.get("ref") in set(selected_teacher_refs)]
                selected_teacher_total = sum(float(item.get("valor", 0) or 0) for item in selected_teacher_items)
                st.caption(
                    f"Selecionadas: {len(selected_teacher_items)} aula(s) | "
                    f"Total a lancar: {format_money(selected_teacher_total)}"
                )
                tp4, tp5, tp6 = st.columns(3)
                with tp4:
                    teacher_pay_data = st.date_input(
                        "Data do lancamento",
                        value=datetime.date.today(),
                        format="DD/MM/YYYY",
                        key="fin_teacher_pay_data",
                    )
                with tp5:
                    teacher_pay_venc = st.date_input(
                        "Vencimento",
                        value=datetime.date.today(),
                        format="DD/MM/YYYY",
                        key="fin_teacher_pay_venc",
                    )
                with tp6:
                    teacher_pay_status = st.selectbox(
                        "Status",
                        ["Aberto", "Pago"],
                        key="fin_teacher_pay_status",
                    )
                teacher_pay_due_day = st.selectbox(
                    "Dia do vencimento",
                    list(range(1, 31)),
                    index=max(0, min(29, datetime.date.today().day - 1)),
                    format_func=lambda d: f"Dia {d}",
                    key="fin_teacher_pay_due_day",
                )
                teacher_pay_cobranca = st.selectbox(
                    "Forma de pagamento",
                    ["Transferencia", "Pix", "Dinheiro", "Boleto", "Cartao"],
                    index=0,
                    key="fin_teacher_pay_cobranca",
                )
                if st.button(
                    "Lancar pagamentos das aulas selecionadas",
                    type="primary",
                    key="fin_teacher_pay_launch_btn",
                    disabled=not bool(selected_teacher_refs),
                ):
                    if not selected_teacher_refs:
                        st.error("Selecione ao menos uma aula finalizada.")
                    else:
                        candidates_by_ref = {item["ref"]: item for item in teacher_candidates}
                        lote_id_teacher = f"PAG-LOT-{uuid.uuid4().hex[:10].upper()}"
                        launched = 0
                        for ref in selected_teacher_refs:
                            item = candidates_by_ref.get(ref)
                            if not item:
                                continue
                            valor_txt = f"{float(item.get('valor', 0) or 0):.2f}".replace(".", ",")
                            st.session_state["payables"].append(
                                {
                                    "codigo": f"PAG-{uuid.uuid4().hex[:8].upper()}",
                                    "descricao": str(item.get("descricao", "")).strip() or "Pagamento de aula",
                                    "valor": valor_txt,
                                    "valor_parcela": valor_txt,
                                    "parcela": "1",
                                    "fornecedor": str(item.get("professor", "")).strip(),
                                    "categoria_lancamento": "Professor",
                                    "numero_pedido": ref,
                                    "class_session_ref": ref,
                                    "class_session_id": str(item.get("session_id", "")).strip(),
                                    "turma": str(item.get("turma", "")).strip(),
                                    "modulo": str(item.get("modulo", "")).strip(),
                                    "data_aula": str(item.get("data", "")).strip(),
                                    "duracao_minutos": int(item.get("minutos", 0) or 0),
                                    "data": teacher_pay_data.strftime("%d/%m/%Y"),
                                    "vencimento": _month_due_date(teacher_pay_venc, teacher_pay_due_day).strftime("%d/%m/%Y"),
                                    "cobranca": teacher_pay_cobranca,
                                    "status": teacher_pay_status,
                                    "lote_id": lote_id_teacher,
                                }
                            )
                            launched += 1
                        save_list(PAYABLES_FILE, st.session_state["payables"])
                        st.session_state["fin_teacher_pay_reset_pending"] = True
                        st.success(f"Pagamento de {launched} aula(s) lancado com sucesso.")
                        st.rerun()

                st.divider()
                st.markdown("### Lancamento manual de pagamento")
                manual_turma_options = class_names()
                if not manual_turma_options:
                    st.info("Nenhuma turma cadastrada para lancamento manual.")
                else:
                    mp1, mp2, mp3 = st.columns(3)
                    with mp1:
                        teacher_manual_month_ref = st.date_input(
                            "Mes de referencia (manual)",
                            value=datetime.date.today(),
                            format="DD/MM/YYYY",
                            key="fin_teacher_manual_month_ref",
                        )
                    with mp2:
                        teacher_manual_turma = st.selectbox(
                            "Turma (manual)",
                            manual_turma_options,
                            key="fin_teacher_manual_turma",
                        )
                    turma_manual_obj = next(
                        (c for c in st.session_state.get("classes", []) if str(c.get("nome", "")).strip() == str(teacher_manual_turma).strip()),
                        {},
                    )
                    modulo_manual = str(turma_manual_obj.get("modulo", "")).strip()
                    professor_manual = str(turma_manual_obj.get("professor", "")).strip()
                    minutos_manual = _teacher_payment_minutes_for_module(modulo_manual, turma_obj=turma_manual_obj)
                    valor_unitario_manual = _teacher_payment_value_for_minutes(minutos_manual)
                    with mp3:
                        teacher_manual_qtd = st.number_input(
                            "Quantidade de aulas",
                            min_value=1,
                            max_value=100,
                            value=1,
                            step=1,
                            key="fin_teacher_manual_qtd",
                        )
                    st.caption(
                        f"Professor: {professor_manual or '-'} | Modulo: {modulo_manual or '-'} | "
                        f"Duracao por aula: {minutos_manual} min | Valor unitario: {format_money(valor_unitario_manual)}"
                    )
                    teacher_manual_total = float(valor_unitario_manual) * int(teacher_manual_qtd or 0)
                    st.caption(f"Total manual a lancar: {format_money(teacher_manual_total)}")
                    if st.button(
                        "Lancar pagamento manual do professor",
                        type="secondary",
                        key="fin_teacher_manual_launch_btn",
                    ):
                        if not professor_manual or not modulo_manual:
                            st.error("A turma selecionada precisa ter professor e modulo cadastrados.")
                        else:
                            mes_manual_label = teacher_manual_month_ref.strftime("%m/%Y") if teacher_manual_month_ref else datetime.date.today().strftime("%m/%Y")
                            valor_total_manual_txt = f"{teacher_manual_total:.2f}".replace(".", ",")
                            st.session_state["payables"].append(
                                {
                                    "codigo": f"PAG-{uuid.uuid4().hex[:8].upper()}",
                                    "descricao": f"Pagamento manual de aulas - {teacher_manual_turma} - {mes_manual_label}",
                                    "valor": valor_total_manual_txt,
                                    "valor_parcela": valor_total_manual_txt,
                                    "parcela": "1",
                                    "fornecedor": professor_manual,
                                    "categoria_lancamento": "Professor",
                                    "numero_pedido": f"MANUAL-{uuid.uuid4().hex[:6].upper()}",
                                    "turma": str(teacher_manual_turma).strip(),
                                    "modulo": modulo_manual,
                                    "duracao_minutos": int(minutos_manual),
                                    "quantidade_aulas": int(teacher_manual_qtd),
                                    "valor_unitario_aula": f"{float(valor_unitario_manual):.2f}".replace(".", ","),
                                    "data": teacher_pay_data.strftime("%d/%m/%Y"),
                                    "vencimento": _month_due_date(teacher_pay_venc, teacher_pay_due_day).strftime("%d/%m/%Y"),
                                    "cobranca": teacher_pay_cobranca,
                                    "status": teacher_pay_status,
                                    "lote_id": f"PAG-LOT-{uuid.uuid4().hex[:10].upper()}",
                                }
                            )
                            save_list(PAYABLES_FILE, st.session_state["payables"])
                            st.success("Pagamento manual do professor lancado com sucesso.")
                            st.rerun()

            with st.form("add_pag"):
                st.markdown("### Lancar Despesa")
                c1, c2, c3 = st.columns(3)
                with c1:
                    desc = st.text_input("Descricao")
                with c2:
                    val_parcela_pag_input = st.text_input("Valor Parcela *")
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
                c4, c5, c6, c6b = st.columns(4)
                with c4:
                    forn = st.text_input(f"{ref_pag}")
                with c5:
                    data_pag = st.date_input("Data do lancamento", value=datetime.date.today(), format="DD/MM/YYYY")
                with c6:
                    venc_pag = st.date_input("Primeiro vencimento", value=datetime.date.today(), format="DD/MM/YYYY")
                with c6b:
                    pag_due_day = st.selectbox(
                        "Dia do vencimento",
                        list(range(1, 31)),
                        index=max(0, min(29, datetime.date.today().day - 1)),
                        format_func=lambda d: f"Dia {d}",
                    )

                c7, c8, c9 = st.columns(3)
                with c7:
                    qtd_pag = st.number_input("Parcelas *", min_value=1, max_value=24, value=1, step=1)
                val_parcela_pag_num = parse_money(val_parcela_pag_input)
                qtd_pag_int = max(1, int(qtd_pag))
                valor_parcela_pag = f"{val_parcela_pag_num:.2f}".replace(".", ",") if val_parcela_pag_num > 0 else "0,00"
                val_total_pag_num = val_parcela_pag_num * qtd_pag_int
                valor_total_pag_txt = f"{val_total_pag_num:.2f}".replace(".", ",")
                with c8:
                    st.text_input("Valor Total * (automatico)", value=valor_total_pag_txt, disabled=True, key="pag_valor_total_auto")
                with c9:
                    numero_pedido_pag = st.text_input("Numero do pedido")

                c10, c11 = st.columns(2)
                with c10:
                    cobranca_pag = st.selectbox("Forma de pagamento", ["Boleto", "Pix", "Cartao", "Dinheiro", "Transferencia"])
                with c11:
                    status_pag = st.selectbox("Status", ["Aberto", "Pago"])

                if st.form_submit_button("Lancar"):
                    if not desc.strip() or not forn.strip() or val_parcela_pag_num <= 0:
                        st.error("Informe descricao, referencia e valor da parcela valido.")
                    else:
                        lote_id_pag = f"PAG-LOT-{uuid.uuid4().hex[:10].upper()}"
                        venc_pag_base = _month_due_date(venc_pag, pag_due_day)
                        for i in range(qtd_pag_int):
                            venc_item = add_months(venc_pag_base, i) if qtd_pag_int > 1 else venc_pag_base
                            parcela_txt = f"{1 + i}/{qtd_pag_int}" if qtd_pag_int > 1 else "1"
                            st.session_state["payables"].append(
                                {
                                    "codigo": f"PAG-{uuid.uuid4().hex[:8].upper()}",
                                    "descricao": desc.strip(),
                                    "valor": valor_total_pag_txt,
                                    "valor_parcela": valor_parcela_pag,
                                    "parcela": parcela_txt,
                                    "fornecedor": forn.strip(),
                                    "categoria_lancamento": categoria_lancamento_pag,
                                    "numero_pedido": numero_pedido_pag.strip(),
                                    "data": data_pag.strftime("%d/%m/%Y"),
                                    "vencimento": venc_item.strftime("%d/%m/%Y"),
                                    "cobranca": cobranca_pag,
                                    "status": status_pag,
                                    "lote_id": lote_id_pag,
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
                    "turma",
                    "modulo",
                    "data_aula",
                    "duracao_minutos",
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

            st.markdown("### Acoes em massa (Despesas)")
            if st.session_state.pop("fin_pag_bulk_reset_pending", False):
                st.session_state.pop("fin_pag_bulk_codes", None)
                st.session_state.pop("fin_pag_bulk_confirm_delete", None)
            pag_bulk_all_codes = list(
                dict.fromkeys(
                    [
                        str(p.get("codigo", "")).strip()
                        for p in despesas
                        if str(p.get("codigo", "")).strip()
                    ]
                )
            )
            pag_labels_by_code = {}
            for p in despesas:
                codigo_pag = str(p.get("codigo", "")).strip()
                if not codigo_pag:
                    continue
                pag_labels_by_code[codigo_pag] = (
                    f"{codigo_pag} | {str(p.get('fornecedor', '')).strip()} | "
                    f"{str(p.get('descricao', '')).strip()} | Parcela {str(p.get('parcela', '')).strip()} | "
                    f"{str(p.get('valor_parcela', p.get('valor', ''))).strip()} | {str(p.get('status', '')).strip()}"
                )

            pbk1, pbk2, pbk3 = st.columns(3)
            with pbk1:
                if st.button("Selecionar TODAS", key="fin_pag_bulk_sel_all"):
                    st.session_state["fin_pag_bulk_codes"] = list(pag_bulk_all_codes)
                    st.rerun()
            with pbk2:
                if st.button("Limpar selecao", key="fin_pag_bulk_sel_clear"):
                    st.session_state["fin_pag_bulk_codes"] = []
                    st.rerun()
            with pbk3:
                st.caption(f"Base: {len(pag_bulk_all_codes)} despesa(s)")

            selected_pag_codes = st.multiselect(
                "Selecionar despesas",
                pag_bulk_all_codes,
                key="fin_pag_bulk_codes",
                format_func=lambda code: pag_labels_by_code.get(code, code),
            )
            pbk4, pbk5 = st.columns([1.6, 2.4])
            with pbk4:
                pag_bulk_confirm = st.checkbox(
                    "Confirmo exclusao em massa",
                    value=False,
                    key="fin_pag_bulk_confirm_delete",
                )
            with pbk5:
                if st.button(
                    "Excluir despesas selecionadas",
                    type="primary",
                    key="fin_pag_bulk_delete_btn",
                    disabled=not bool(selected_pag_codes),
                ):
                    if not pag_bulk_confirm:
                        st.error("Marque a confirmacao para excluir em massa.")
                    else:
                        before_pag = len(st.session_state.get("payables", []))
                        st.session_state["payables"] = [
                            p
                            for p in st.session_state.get("payables", [])
                            if str(p.get("codigo", "")).strip() not in selected_pag_codes
                        ]
                        removed_pag = before_pag - len(st.session_state.get("payables", []))
                        save_list(PAYABLES_FILE, st.session_state["payables"])
                        st.session_state["fin_pag_bulk_reset_pending"] = True
                        st.success(f"{removed_pag} despesa(s) excluida(s).")
                        st.rerun()

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
                qtd_base_pag = max(1, int(qtd_atual_pag))
                valor_parcela_base_pag_num = parse_money(pag_obj.get("valor_parcela", ""))
                if valor_parcela_base_pag_num <= 0:
                    valor_total_base_pag_num = parse_money(pag_obj.get("valor", ""))
                    if valor_total_base_pag_num > 0:
                        valor_parcela_base_pag_num = valor_total_base_pag_num / qtd_base_pag
                valor_parcela_base_pag_txt = (
                    f"{valor_parcela_base_pag_num:.2f}".replace(".", ",")
                    if valor_parcela_base_pag_num > 0
                    else ""
                )

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
                        new_val_parcela_pag_input = st.text_input(
                            "Valor da parcela",
                            value=valor_parcela_base_pag_txt,
                        )
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

                    new_val_parcela_pag_num = parse_money(new_val_parcela_pag_input)
                    new_qtd_pag_int = max(1, int(new_qtd_pag))
                    new_val_total_pag_num = new_val_parcela_pag_num * new_qtd_pag_int
                    new_valor_parcela_pag = f"{new_val_parcela_pag_num:.2f}".replace(".", ",") if new_val_parcela_pag_num > 0 else "0,00"
                    new_val_total_pag = f"{new_val_total_pag_num:.2f}".replace(".", ",") if new_val_total_pag_num > 0 else "0,00"
                    with mp11:
                        st.text_input("Valor total (automatico)", value=new_val_total_pag, disabled=True)

                    apply_all_pag = st.checkbox(
                        "Aplicar alteracoes em todas as parcelas do mesmo lancamento",
                        value=bool(qtd_atual_pag > 1),
                        key=f"pag_apply_all_{idx_pag}",
                    )

                    mpc1, mpc2 = st.columns(2)
                    with mpc1:
                        salvar_pag = st.form_submit_button("Salvar alteracoes")
                    with mpc2:
                        excluir_pag = st.form_submit_button("Excluir despesa", type="primary")

                    if salvar_pag:
                        if not new_desc_pag.strip() or not new_forn_pag.strip() or new_val_parcela_pag_num <= 0:
                            st.error("Informe descricao, referencia e valor da parcela valido.")
                        else:
                            lote_id_pag = str(pag_obj.get("lote_id", "")).strip() or f"PAG-LOT-{uuid.uuid4().hex[:10].upper()}"

                            if apply_all_pag:
                                related_idx = _related_payable_indices(despesas, idx_pag)
                                related_idx = _sort_indices_by_parcela(despesas, related_idx)
                                if not related_idx:
                                    related_idx = [idx_pag]
                                related_items = [despesas[i] for i in related_idx if 0 <= i < len(despesas)]
                                existing_codes = [str(item.get("codigo", "")).strip() for item in related_items if str(item.get("codigo", "")).strip()]
                                if not existing_codes:
                                    existing_codes = [str(pag_obj.get("codigo", "")).strip()] if str(pag_obj.get("codigo", "")).strip() else []

                                parcela_base_pag = max(1, parcela_atual_pag)
                                primeiro_venc_pag = add_months(new_venc_pag, -(parcela_base_pag - 1)) if parcela_base_pag > 1 else new_venc_pag
                                if primeiro_venc_pag is None:
                                    primeiro_venc_pag = new_venc_pag

                                related_set_pag = set(related_idx)
                                st.session_state["payables"] = [
                                    p for pos, p in enumerate(despesas) if pos not in related_set_pag
                                ]
                                despesas = st.session_state["payables"]

                                for i in range(new_qtd_pag_int):
                                    codigo_pag_item = (
                                        existing_codes[i]
                                        if i < len(existing_codes) and existing_codes[i]
                                        else f"PAG-{uuid.uuid4().hex[:8].upper()}"
                                    )
                                    venc_pag_item = add_months(primeiro_venc_pag, i) or new_venc_pag
                                    parcela_txt_pag = f"{i + 1}/{new_qtd_pag_int}" if new_qtd_pag_int > 1 else "1"
                                    st.session_state["payables"].append(
                                        {
                                            "codigo": codigo_pag_item,
                                            "descricao": new_desc_pag.strip(),
                                            "valor": new_val_total_pag,
                                            "valor_parcela": new_valor_parcela_pag,
                                            "parcela": parcela_txt_pag,
                                            "fornecedor": new_forn_pag.strip(),
                                            "categoria_lancamento": new_cat_pag,
                                            "numero_pedido": new_numero_pedido_pag.strip(),
                                            "data": new_data_pag.strftime("%d/%m/%Y"),
                                            "vencimento": venc_pag_item.strftime("%d/%m/%Y"),
                                            "cobranca": new_cobranca_pag,
                                            "status": new_status_pag,
                                            "lote_id": lote_id_pag,
                                        }
                                    )
                            else:
                                pag_obj["descricao"] = new_desc_pag.strip()
                                pag_obj["valor"] = new_val_total_pag
                                pag_obj["valor_parcela"] = new_valor_parcela_pag
                                pag_obj["parcela"] = f"{parcela_atual_pag}/{new_qtd_pag_int}" if new_qtd_pag_int > 1 else str(parcela_atual_pag)
                                pag_obj["fornecedor"] = new_forn_pag.strip()
                                pag_obj["categoria_lancamento"] = new_cat_pag
                                pag_obj["numero_pedido"] = new_numero_pedido_pag.strip()
                                pag_obj["data"] = new_data_pag.strftime("%d/%m/%Y")
                                pag_obj["vencimento"] = new_venc_pag.strftime("%d/%m/%Y")
                                pag_obj["cobranca"] = new_cobranca_pag
                                pag_obj["status"] = new_status_pag
                                pag_obj["lote_id"] = lote_id_pag
                            save_list(PAYABLES_FILE, st.session_state["payables"])
                            st.success("Despesa atualizada!")
                            st.rerun()

                    if excluir_pag:
                        st.session_state["payables"].remove(pag_obj)
                        save_list(PAYABLES_FILE, st.session_state["payables"])
                        st.success("Despesa excluida.")
                        st.rerun()

        if finance_main == "Aprovacoes Comercial":
            finance_aprov_options = ["Pagamentos de matricula"]
            if st.session_state.get("finance_aprov_menu") not in finance_aprov_options:
                st.session_state["finance_aprov_menu"] = finance_aprov_options[0]
            st.radio(
                "Opcoes de Aprovacoes Comercial",
                finance_aprov_options,
                key="finance_aprov_menu",
            )
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

        if finance_main == "Vencimentos":
            finance_venc_options = ["A receber vencidos", "A pagar vencidos"]
            if finance_focus == "receber":
                st.session_state["finance_overdue_mode"] = "A receber vencidos"
            elif finance_focus == "pagar":
                st.session_state["finance_overdue_mode"] = "A pagar vencidos"
            if st.session_state.get("finance_overdue_mode") not in finance_venc_options:
                st.session_state["finance_overdue_mode"] = finance_venc_options[0]
            overdue_mode = st.radio(
                "Opcoes de Vencimentos",
                finance_venc_options,
                key="finance_overdue_mode",
            )
            if overdue_mode == "A receber vencidos":
                _render_overdue_receivables_panel()
            else:
                _render_overdue_payables_panel()

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
                n1, n2 = st.columns(2)
                with n1:
                    send_user_email = st.checkbox(
                        "Enviar mensagem por e-mail",
                        value=True,
                        key="new_user_notify_email",
                    )
                with n2:
                    send_user_whatsapp = st.checkbox(
                        "Enviar mensagem por WhatsApp",
                        value=True,
                        key="new_user_notify_whatsapp",
                    )
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
                            [u_email] if bool(send_user_email) else [],
                            [u_cel] if bool(send_user_whatsapp) else [],
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

    elif menu_coord == "Licoes de Casa":
        run_weekly_homework_panel(
            panel_key="coord_homework",
            turmas_disponiveis=class_names(),
            autor_nome=st.session_state.get("user_name", "Coordenacao"),
        )
    elif menu_coord == "Conteudos":
        st.markdown('<div class="main-header">Caixa de Entrada</div>', unsafe_allow_html=True)
        tab_msg, tab_hist = st.tabs(["Publicar Mensagem", "Historico"])
        with tab_msg:
            turmas_msg = ["Todas"] + class_names()
            with st.form("coord_publish_message", clear_on_submit=True):
                publico_msg = st.selectbox(
                    "Destinatarios",
                    ["Alunos", "Professores", "Alunos e Professores", "Aluno (individual)", "Professor (individual)"],
                )
                turma_msg = "Todas"
                professor_msg = "Todos"
                aluno_obj_msg = None
                professor_individual_msg = ""
                if publico_msg in ("Alunos", "Alunos e Professores", "Aluno (individual)"):
                    turma_msg = st.selectbox("Turma de destino (alunos)", turmas_msg)
                if publico_msg in ("Professores", "Alunos e Professores"):
                    prof_opts = ["Todos"] + teacher_names()
                    professor_msg = st.selectbox("Professor(es) de destino", prof_opts)
                if publico_msg == "Aluno (individual)":
                    alunos_destino = [
                        s for s in st.session_state.get("students", [])
                        if str(s.get("nome", "")).strip()
                        and (turma_msg == "Todas" or str(s.get("turma", "")).strip() == turma_msg)
                    ]
                    alunos_destino = sorted(alunos_destino, key=lambda s: str(s.get("nome", "")).strip().lower())
                    aluno_opts = [None] + alunos_destino
                    aluno_obj_msg = st.selectbox(
                        "Pessoa de destino (aluno)",
                        aluno_opts,
                        format_func=lambda s: (
                            "Selecione"
                            if s is None
                            else (
                                f"{str(s.get('nome', '')).strip()} ({str(s.get('turma', '')).strip() or 'Sem Turma'})"
                                + (
                                    f" - Matricula {str(s.get('matricula', '')).strip()}"
                                    if str(s.get("matricula", "")).strip()
                                    else ""
                                )
                            )
                        ),
                    )
                if publico_msg == "Professor (individual)":
                    professores_destino = sorted(
                        {
                            str(t.get("nome", "")).strip()
                            for t in st.session_state.get("teachers", [])
                            if str(t.get("nome", "")).strip()
                        }
                    )
                    professor_individual_msg = st.selectbox(
                        "Pessoa de destino (professor)",
                        [""] + professores_destino,
                        format_func=lambda p: "Selecione" if not str(p).strip() else str(p).strip(),
                    )
                st.markdown("**Envio individual extra (opcional)**")
                alunos_extra_opts = sorted(
                    {
                        str(s.get("nome", "")).strip()
                        for s in st.session_state.get("students", [])
                        if str(s.get("nome", "")).strip()
                    }
                )
                professores_extra_opts = sorted(
                    {
                        str(t.get("nome", "")).strip()
                        for t in st.session_state.get("teachers", [])
                        if str(t.get("nome", "")).strip()
                    }
                )
                coordenadores_map = {}
                for user_obj in st.session_state.get("users", []):
                    perfil_user = str(user_obj.get("perfil", "")).strip().lower()
                    if perfil_user not in ("coordenador", "admin"):
                        continue
                    nome_user = str(user_obj.get("pessoa", "")).strip() or str(user_obj.get("usuario", "")).strip()
                    if not nome_user:
                        continue
                    key_nome = nome_user.lower()
                    if key_nome not in coordenadores_map:
                        coordenadores_map[key_nome] = {
                            "nome": nome_user,
                            "email": str(user_obj.get("email", "")).strip().lower(),
                            "celular": str(user_obj.get("celular", "")).strip(),
                        }
                coordenadores_extra_opts = sorted(item.get("nome", "") for item in coordenadores_map.values() if item.get("nome", ""))
                ce1, ce2, ce3 = st.columns(3)
                with ce1:
                    extra_aluno_nome = st.selectbox(
                        "Aluno (extra individual)",
                        [""] + alunos_extra_opts,
                        format_func=lambda p: "Selecione" if not str(p).strip() else str(p).strip(),
                    )
                with ce2:
                    extra_prof_nome = st.selectbox(
                        "Professor (extra individual)",
                        [""] + professores_extra_opts,
                        format_func=lambda p: "Selecione" if not str(p).strip() else str(p).strip(),
                    )
                with ce3:
                    extra_coord_nome = st.selectbox(
                        "Coordenador (extra individual)",
                        [""] + coordenadores_extra_opts,
                        format_func=lambda p: "Selecione" if not str(p).strip() else str(p).strip(),
                    )
                ch1, ch2 = st.columns(2)
                with ch1:
                    send_msg_email = st.checkbox(
                        "Enviar por e-mail",
                        value=True,
                        key="coord_msg_notify_email",
                    )
                with ch2:
                    send_msg_whatsapp = st.checkbox(
                        "Enviar por WhatsApp",
                        value=True,
                        key="coord_msg_notify_whatsapp",
                    )
                titulo_msg = st.text_input("Titulo da mensagem")
                corpo_msg = st.text_area("Mensagem")
                if st.form_submit_button("Publicar e enviar comunicado (e-mail + WhatsApp)"):
                    if not titulo_msg.strip() or not corpo_msg.strip():
                        st.error("Preencha titulo e mensagem.")
                    elif not send_msg_email and not send_msg_whatsapp:
                        st.error("Ative pelo menos um canal: e-mail ou WhatsApp.")
                    elif sum(1 for v in (extra_aluno_nome, extra_prof_nome, extra_coord_nome) if str(v).strip()) > 1:
                        st.error("No envio individual extra, selecione somente uma pessoa.")
                    elif not any(str(v).strip() for v in (extra_aluno_nome, extra_prof_nome, extra_coord_nome)) and publico_msg == "Aluno (individual)" and not isinstance(aluno_obj_msg, dict):
                        st.error("Selecione a pessoa de destino.")
                    elif not any(str(v).strip() for v in (extra_aluno_nome, extra_prof_nome, extra_coord_nome)) and publico_msg == "Professor (individual)" and not professor_individual_msg:
                        st.error("Selecione a pessoa de destino.")
                    else:
                        aluno_nome_msg = str(aluno_obj_msg.get("nome", "")).strip() if isinstance(aluno_obj_msg, dict) else ""
                        publico_api = publico_msg
                        recipient_entry_msg = None
                        if publico_msg == "Aluno (individual)":
                            publico_api = "Alunos"
                        elif publico_msg == "Professor (individual)":
                            publico_api = "Professores"
                        extra_alvo = ""
                        extra_tipo = ""
                        if str(extra_aluno_nome).strip():
                            extra_tipo = "aluno"
                            extra_alvo = str(extra_aluno_nome).strip()
                        elif str(extra_prof_nome).strip():
                            extra_tipo = "professor"
                            extra_alvo = str(extra_prof_nome).strip()
                        elif str(extra_coord_nome).strip():
                            extra_tipo = "coordenador"
                            extra_alvo = str(extra_coord_nome).strip()
                        if extra_tipo == "aluno":
                            aluno_nome_msg = extra_alvo
                            publico_api = "Alunos"
                        elif extra_tipo == "professor":
                            professor_individual_msg = extra_alvo
                            publico_api = "Professores"
                        elif extra_tipo == "coordenador":
                            coord_ref = coordenadores_map.get(extra_alvo.lower(), {})
                            publico_api = "Pessoa especifica"
                            recipient_entry_msg = {
                                "name": extra_alvo,
                                "label": f"{extra_alvo} (Coordenador)",
                                "emails": [str(coord_ref.get("email", "")).strip().lower()],
                                "whatsapps": [str(coord_ref.get("celular", "")).strip()],
                            }
                        assume_control_auto = bool(send_msg_whatsapp) and (
                            publico_msg in ("Aluno (individual)", "Professor (individual)")
                            or extra_tipo in ("aluno", "professor")
                        )
                        pause_feedback = apply_wiz_control_from_operator_message(corpo_msg, assume_control=assume_control_auto)
                        stats = post_message_and_notify(
                            autor=st.session_state.get("user_name", "Coordenacao"),
                            titulo=titulo_msg,
                            mensagem=corpo_msg,
                            turma=turma_msg,
                            origem="Mensagens Coordenacao",
                            publico=publico_api,
                            professor=professor_msg,
                            send_email=bool(send_msg_email),
                            send_whatsapp=bool(send_msg_whatsapp),
                            aluno=aluno_nome_msg,
                            professor_individual=professor_individual_msg,
                            recipient_entry=recipient_entry_msg,
                        )
                        if pause_feedback:
                            st.info(pause_feedback)
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
                    destino_txt = _message_destination_label(msg)
                    st.markdown(
                        f"""<div style="background:white; padding:16px; border-radius:12px; border:1px solid #e2e8f0; margin-bottom:10px;">
<div style="font-weight:700; color:#1e3a8a;">{msg.get('titulo','Mensagem')}</div>
<div style="font-size:0.85rem; color:#64748b; margin-bottom:8px;">{msg.get('data','')} | {msg.get('autor','')} | {destino_txt}</div>
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
            target_options = ["Por livro", "Turma", "Aluno VIP"]
            if st.session_state.get("coord_ch_target_type") not in target_options:
                st.session_state["coord_ch_target_type"] = target_options[0]
            target_choice = st.selectbox("Diretorio do desafio", target_options, key="coord_ch_target_type")
            target_type = _challenge_target_type(target_choice)
            target_turma = ""
            target_aluno = ""
            target_turmas_envio = []
            nivel = "Livro 1"
            turma_obj = {}
            aluno_vip_obj = {}
            materia_atual = ""
            if target_type == "turma":
                turma_options = class_names()
                if not turma_options:
                    st.warning("Nenhuma turma cadastrada para direcionar o desafio.")
                else:
                    target_turma = st.selectbox("Turma de destino", turma_options, key="coord_ch_target_turma")
                    turma_obj = next((c for c in st.session_state.get("classes", []) if str(c.get("nome", "")).strip() == target_turma), {})
                    nivel = _norm_book_level(turma_obj.get("livro", "")) or "Livro 1"
                    materia_atual = _current_subject_for_challenge(target_turma, turma_obj)
                    st.caption(f"Nivel detectado pela turma: {nivel}")
            elif target_type == "aluno_vip":
                vip_students = [s for s in st.session_state.get("students", []) if _student_vip_summary(s)]
                vip_names = [str(s.get("nome", "")).strip() for s in vip_students if str(s.get("nome", "")).strip()]
                if not vip_names:
                    st.warning("Nenhum aluno VIP cadastrado para direcionar o desafio.")
                else:
                    target_aluno = st.selectbox("Aluno VIP de destino", vip_names, key="coord_ch_target_aluno")
                    aluno_vip_obj = next((s for s in vip_students if str(s.get("nome", "")).strip() == target_aluno), {})
                    nivel = student_book_level(aluno_vip_obj) or "Livro 1"
                    turma_aluno_vip = str(aluno_vip_obj.get("turma", "")).strip()
                    materia_atual = _current_subject_for_challenge(turma_aluno_vip) if turma_aluno_vip else ""
                    st.caption(f"Nivel detectado pelo aluno VIP: {nivel}")
            else:
                nivel = st.selectbox("Nivel (Livro)", book_levels(), key="coord_ch_level")
            base_date = st.date_input(
                "Semana (escolha uma data)",
                value=datetime.date.today(),
                format="DD/MM/YYYY",
                key="coord_ch_date",
            )
            semana = current_week_key(base_date)
            st.caption(f"Chave da semana: {semana}")

            existing = get_weekly_challenge_for_target(
                nivel,
                semana,
                target_type=target_type,
                target_turma=target_turma,
                target_aluno=target_aluno,
            ) or {}
            target_key_label = target_turma or target_aluno or nivel
            key_prefix = f"coord_ch_{target_type}_{str(target_key_label).replace(' ', '_')}_{str(semana).replace('-', '_')}"

            titulo_key = f"{key_prefix}_titulo"
            descricao_key = f"{key_prefix}_descricao"
            rubrica_key = f"{key_prefix}_rubrica"
            dica_key = f"{key_prefix}_dica"
            pontos_key = f"{key_prefix}_pontos"
            sem_prazo_key = f"{key_prefix}_sem_prazo"
            due_key = f"{key_prefix}_due"
            notify_key = f"{key_prefix}_notify_level"
            draft_info_key = f"{key_prefix}_draft_info"
            theme_key = f"{key_prefix}_reference_theme"
            ref_book_key = f"{key_prefix}_reference_book"
            ref_subject_key = f"{key_prefix}_reference_subject"
            ref_note_key = f"{key_prefix}_reference_note"
            preview_key = f"{key_prefix}_preview_box"
            preview_seed_key = f"{key_prefix}_preview_seed"
            use_preview_on_save_key = f"{key_prefix}_use_preview_on_save"
            send_turmas_key = f"{key_prefix}_send_turmas"
            draft_patch_key = f"{key_prefix}_draft_patch"
            draft_action_key = f"{key_prefix}_draft_action"
            draft_error_key = f"{key_prefix}_draft_error"
            editor_titulo_key = f"{key_prefix}_editor_titulo"
            editor_descricao_key = f"{key_prefix}_editor_descricao"
            editor_rubrica_key = f"{key_prefix}_editor_rubrica"
            editor_dica_key = f"{key_prefix}_editor_dica"
            editor_pontos_key = f"{key_prefix}_editor_pontos"

            pending_draft_patch = st.session_state.pop(draft_patch_key, None)
            if isinstance(pending_draft_patch, dict):
                for patch_key, patch_value in pending_draft_patch.items():
                    st.session_state[patch_key] = patch_value

            if titulo_key not in st.session_state:
                st.session_state[titulo_key] = str(existing.get("titulo", ""))
            if descricao_key not in st.session_state:
                st.session_state[descricao_key] = str(existing.get("descricao", ""))
            if rubrica_key not in st.session_state:
                st.session_state[rubrica_key] = str(existing.get("rubrica", ""))
            if dica_key not in st.session_state:
                st.session_state[dica_key] = str(existing.get("dica", ""))
            if pontos_key not in st.session_state:
                st.session_state[pontos_key] = int(existing.get("pontos") or 10)
            if sem_prazo_key not in st.session_state:
                st.session_state[sem_prazo_key] = not bool(str(existing.get("due_date", "")).strip())
            if due_key not in st.session_state:
                st.session_state[due_key] = parse_date(existing.get("due_date", "")) or (base_date + datetime.timedelta(days=7))
            if notify_key not in st.session_state:
                st.session_state[notify_key] = True
            if use_preview_on_save_key not in st.session_state:
                st.session_state[use_preview_on_save_key] = False
            if draft_info_key not in st.session_state:
                st.session_state[draft_info_key] = ""
            if send_turmas_key not in st.session_state:
                raw_send_turmas = existing.get("target_turmas_envio", [])
                if isinstance(raw_send_turmas, str):
                    raw_send_turmas = [part.strip() for part in raw_send_turmas.split(",") if part.strip()]
                st.session_state[send_turmas_key] = [str(x).strip() for x in raw_send_turmas if str(x).strip()]
            if theme_key not in st.session_state:
                st.session_state[theme_key] = str(existing.get("reference_theme", "Livro / Conteudo atual")).strip() or "Livro / Conteudo atual"
            default_book_reference = (
                str(existing.get("reference_book", "")).strip()
                or (str(turma_obj.get("livro", "")).strip() if turma_obj else "")
                or nivel
            )
            if ref_book_key not in st.session_state:
                st.session_state[ref_book_key] = default_book_reference
            if ref_subject_key not in st.session_state:
                st.session_state[ref_subject_key] = str(existing.get("reference_subject", "")).strip() or materia_atual
            if ref_note_key not in st.session_state:
                base_note = str(existing.get("reference_note", "")).strip()
                if not base_note:
                    base_note = (
                        f"Linha do desafio: {st.session_state.get(theme_key, 'Livro / Conteudo atual')}\n"
                        f"Livro/Nivel de referencia: {default_book_reference or '-'}\n"
                        f"Materia/Conteudo de referencia: {str(materia_atual or 'Nao informado').strip()}\n"
                        "Use essa base para gerar um desafio coerente com a turma e com o livro."
                    )
                st.session_state[ref_note_key] = base_note
            if draft_error_key not in st.session_state:
                st.session_state[draft_error_key] = ""
            pending_draft_action = str(st.session_state.pop(draft_action_key, "")).strip()
            if pending_draft_action == "gen_ai":
                api_key = get_groq_api_key()
                if not api_key:
                    st.session_state[draft_error_key] = "Configure GROQ_API_KEY para gerar desafios com IA."
                elif target_type == "turma" and not target_turma:
                    st.session_state[draft_error_key] = "Selecione a turma de destino antes de gerar o desafio."
                elif target_type == "aluno_vip" and not target_aluno:
                    st.session_state[draft_error_key] = "Selecione o aluno VIP de destino antes de gerar o desafio."
                else:
                    try:
                        gen = generate_weekly_challenge_ai(
                            nivel,
                            semana,
                            reference_title=str(st.session_state.get(ref_book_key, default_book_reference)).strip() or default_book_reference,
                            reference_text=str(st.session_state.get(ref_note_key, "")).strip(),
                            challenge_theme=str(st.session_state.get(theme_key, "Livro / Conteudo atual")).strip() or "Livro / Conteudo atual",
                        )
                        st.session_state[draft_patch_key] = {
                            titulo_key: str(gen.get("titulo", "")).strip(),
                            descricao_key: str(gen.get("descricao", "")).strip(),
                            rubrica_key: str(gen.get("rubrica", "")).strip(),
                            dica_key: str(gen.get("dica", "")).strip(),
                            pontos_key: int(gen.get("pontos") or 10),
                            editor_titulo_key: str(gen.get("titulo", "")).strip(),
                            editor_descricao_key: str(gen.get("descricao", "")).strip(),
                            editor_rubrica_key: str(gen.get("rubrica", "")).strip(),
                            editor_dica_key: str(gen.get("dica", "")).strip(),
                            editor_pontos_key: int(gen.get("pontos") or 10),
                            draft_info_key: f"Rascunho gerado com IA para {nivel} - {semana}. Revise os campos abaixo e clique em Salvar desafio.",
                        }
                        st.session_state[draft_error_key] = ""
                        st.rerun()
                    except Exception as exc:
                        st.session_state[draft_error_key] = f"Falha ao gerar desafio com IA: {exc}"

            st.markdown("#### Rascunho do desafio")
            st.caption("Voce pode criar manualmente ou gerar com IA, revisar os campos e salvar quando estiver bom.")

            st.markdown("#### Referencia do desafio")
            if target_type == "nivel":
                target_turmas_envio = st.multiselect(
                    "Turmas para enviar o desafio",
                    class_names(),
                    key=send_turmas_key,
                    help="Se nao selecionar nenhuma turma, o desafio vai para todos os alunos do livro selecionado.",
                )
            reference_theme = st.selectbox(
                "Linha do desafio",
                ["Livro / Conteudo atual", "Empreendedorismo", "Inteligencia Emocional"],
                key=theme_key,
            )
            ref_col1, ref_col2 = st.columns(2)
            with ref_col1:
                reference_book = st.text_input("Livro/Nivel de referencia", key=ref_book_key)
            with ref_col2:
                st.text_input(
                    "Materia/Conteudo atual da turma",
                    key=ref_subject_key,
                    placeholder="Ex: Unit 3 - Simple Present",
                )
            reference_subject = str(st.session_state.get(ref_subject_key, "")).strip()
            st.caption("Opcoes especiais disponiveis: Empreendedorismo e Inteligencia Emocional.")
            st.text_area(
                "Base de referencia para IA (visualize e edite antes de gerar)",
                height=120,
                key=ref_note_key,
            )

            autor = st.session_state.get("user_name", "Coordenacao")

            draft_info = str(st.session_state.get(draft_info_key, "")).strip()
            if draft_info:
                st.info(draft_info)
            draft_error = str(st.session_state.get(draft_error_key, "")).strip()
            if draft_error:
                st.error(draft_error)

            ai_col1, ai_col2 = st.columns([1, 1])
            if ai_col1.button("Gerar rascunho com IA", key=f"{key_prefix}_gen_ai"):
                st.session_state[draft_action_key] = "gen_ai"
                st.rerun()

            if ai_col2.button("Gerar com IA para todos livros (semana atual)", key=f"{key_prefix}_gen_ai_all"):
                api_key = get_groq_api_key()
                if not api_key:
                    st.error("Configure GROQ_API_KEY para gerar desafios com IA.")
                else:
                    week_now = current_week_key(datetime.date.today())
                    levels = book_levels()
                    created = 0
                    failed = 0
                    notify_stats = {"email_total": 0, "email_ok": 0, "whatsapp_total": 0, "whatsapp_ok": 0}
                    for lv in levels:
                        if get_weekly_challenge(lv, week_now):
                            continue
                        try:
                            gen = generate_weekly_challenge_ai(
                                lv,
                                week_now,
                                reference_title=lv,
                                reference_text=f"Linha do desafio: Livro / Conteudo atual\nLivro/Nivel de referencia: {lv}\nGere um desafio semanal alinhado ao livro selecionado.",
                                challenge_theme="Livro / Conteudo atual",
                            )
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
                                reference_theme="Livro / Conteudo atual",
                                reference_book=lv,
                                reference_subject="",
                                reference_note=f"Linha do desafio: Livro / Conteudo atual\nLivro/Nivel de referencia: {lv}",
                            )
                            if notify_new_challenge_enabled:
                                partial_stats = notify_new_challenge_by_level(
                                    lv,
                                    week_now,
                                    gen.get("titulo", "Desafio da semana"),
                                    gen.get("descricao", ""),
                                    target_turmas_envio=target_turmas_envio,
                                )
                                for key in notify_stats:
                                    notify_stats[key] += int(partial_stats.get(key, 0))
                            created += 1
                        except Exception:
                            failed += 1
                    if created:
                        if notify_new_challenge_enabled:
                            st.info(
                                "Comunicado de novo desafio enviado: "
                                f"E-mail {notify_stats.get('email_ok', 0)}/{notify_stats.get('email_total', 0)} | "
                                f"WhatsApp {notify_stats.get('whatsapp_ok', 0)}/{notify_stats.get('whatsapp_total', 0)}."
                            )
                        st.success(f"Gerados {created} desafio(s) para a semana {week_now}.")
                        st.rerun()
                    if not created and not failed:
                        st.info(f"Ja existem desafios publicados para a semana {week_now}.")
            manual_col1, manual_col2 = st.columns([1, 1])
            if manual_col1.button("Limpar rascunho", key=f"{key_prefix}_clear"):
                st.session_state[draft_patch_key] = {
                    titulo_key: "",
                    descricao_key: "",
                    rubrica_key: "",
                    dica_key: "",
                    pontos_key: 10,
                    draft_info_key: "Formulario limpo para criacao manual.",
                }
                st.rerun()
            if manual_col2.button("Carregar desafio salvo", key=f"{key_prefix}_load_existing"):
                load_patch = {
                    titulo_key: str(existing.get("titulo", "")),
                    descricao_key: str(existing.get("descricao", "")),
                    rubrica_key: str(existing.get("rubrica", "")),
                    dica_key: str(existing.get("dica", "")),
                    pontos_key: int(existing.get("pontos") or 10),
                    sem_prazo_key: not bool(str(existing.get("due_date", "")).strip()),
                    due_key: parse_date(existing.get("due_date", "")) or (base_date + datetime.timedelta(days=7)),
                    theme_key: str(existing.get("reference_theme", "Livro / Conteudo atual")).strip() or "Livro / Conteudo atual",
                    ref_book_key: str(existing.get("reference_book", "")).strip() or default_book_reference,
                    ref_subject_key: str(existing.get("reference_subject", "")).strip() or materia_atual,
                    ref_note_key: str(existing.get("reference_note", "")).strip() or st.session_state.get(ref_note_key, ""),
                }
                raw_send_turmas = existing.get("target_turmas_envio", [])
                if isinstance(raw_send_turmas, str):
                    raw_send_turmas = [part.strip() for part in raw_send_turmas.split(",") if part.strip()]
                load_patch[send_turmas_key] = [str(x).strip() for x in raw_send_turmas if str(x).strip()]
                load_patch[draft_info_key] = "Desafio salvo carregado no formulario." if existing else "Nao existe desafio salvo para esse destino/semana."
                st.session_state[draft_patch_key] = load_patch
                st.rerun()

            st.markdown("#### Ajuste final antes de salvar")
            st.caption("Edite o desafio aqui antes de publicar. A caixa abaixo tambem aceita edicao direta.")

            titulo = st.text_input("Titulo", key=titulo_key)
            descricao = st.text_area(
                "Descricao",
                height=160,
                key=descricao_key,
            )
            rubrica = st.text_input(
                "Rubrica (como sera avaliado)",
                key=rubrica_key,
            )
            dica = st.text_input(
                "Dica (opcional)",
                key=dica_key,
            )
            pontos = st.number_input(
                "Pontos",
                min_value=0,
                max_value=100,
                step=1,
                key=pontos_key,
            )
            sem_prazo = st.checkbox("Sem prazo", key=sem_prazo_key)
            due_date = None
            if not sem_prazo:
                due_date = st.date_input("Prazo", format="DD/MM/YYYY", key=due_key)

            notify_new_challenge_enabled = st.checkbox(
                "Enviar comunicado de novo desafio (e-mail + WhatsApp)",
                key=notify_key,
            )

            preview_text = (
                f"Destino: {_challenge_target_label({'target_type': target_type, 'target_turma': target_turma, 'target_aluno': target_aluno, 'nivel': nivel, 'target_turmas_envio': target_turmas_envio})}\n"
                f"Turmas de envio: {', '.join(target_turmas_envio) if target_turmas_envio else 'Todas do livro'}\n"
                f"Linha do desafio: {reference_theme}\n"
                f"Livro/Nivel de referencia: {reference_book or '-'}\n"
                f"Materia/Conteudo de referencia: {reference_subject or '-'}\n"
                f"Semana: {semana}\n"
                f"Pontos: {int(pontos)}\n"
                f"Prazo: {'Sem prazo' if sem_prazo else (due_date.strftime('%d/%m/%Y') if isinstance(due_date, datetime.date) else '-')}\n"
                "\n--- TITULO ---\n"
                f"{str(titulo).strip() or '-'}\n"
                "\n--- DESCRICAO ---\n"
                f"{str(descricao).strip() or '-'}\n"
                "\n--- RUBRICA ---\n"
                f"{str(rubrica).strip() or '-'}\n"
                "\n--- DICA ---\n"
                f"{str(dica).strip() or '-'}"
            )
            previous_seed = str(st.session_state.get(preview_seed_key, ""))
            current_preview = str(st.session_state.get(preview_key, ""))
            if preview_key not in st.session_state or current_preview.strip() == previous_seed.strip():
                st.session_state[preview_key] = preview_text
            st.session_state[preview_seed_key] = preview_text
            st.text_area(
                "Pre-visualizacao e edicao antes de postar",
                height=240,
                key=preview_key,
                help="Voce pode ajustar o texto aqui. Para salvar usando esta caixa, marque a opcao abaixo.",
            )
            st.checkbox(
                "Salvar usando o texto da pre-visualizacao (opcional)",
                key=use_preview_on_save_key,
                help="Desmarcado: salva exatamente os campos manuais (Titulo, Descricao, Rubrica e Dica).",
            )

            if st.button("Salvar desafio", type="primary", key=f"{key_prefix}_salvar"):
                preview_source = str(st.session_state.get(preview_key, "")).strip()
                use_preview_on_save = bool(st.session_state.get(use_preview_on_save_key, False))

                def _extract_preview_section(section_name):
                    pattern = rf"---\s*{section_name}\s*---\s*(.*?)(?=\n---\s*(?:TITULO|DESCRICAO|RUBRICA|DICA)\s*---|\Z)"
                    match = re.search(pattern, preview_source, flags=re.IGNORECASE | re.DOTALL)
                    return str(match.group(1)).strip() if match else ""

                if use_preview_on_save and preview_source:
                    parsed_titulo = _extract_preview_section("TITULO")
                    parsed_descricao = _extract_preview_section("DESCRICAO")
                    parsed_rubrica = _extract_preview_section("RUBRICA")
                    parsed_dica = _extract_preview_section("DICA")
                    if parsed_titulo:
                        titulo = parsed_titulo
                    if parsed_descricao:
                        descricao = parsed_descricao
                    if parsed_rubrica:
                        rubrica = parsed_rubrica
                    if parsed_dica:
                        dica = parsed_dica

                if not str(titulo).strip() or not str(descricao).strip():
                    st.error("Preencha titulo e descricao.")
                elif target_type == "turma" and not target_turma:
                    st.error("Selecione a turma de destino.")
                elif target_type == "aluno_vip" and not target_aluno:
                    st.error("Selecione o aluno VIP de destino.")
                else:
                    saved_challenge = upsert_weekly_challenge(
                        level=nivel,
                        week_key=semana,
                        titulo=titulo,
                        descricao=descricao,
                        pontos=int(pontos),
                        autor=autor,
                        due_date=due_date,
                        rubrica=rubrica,
                        dica=dica,
                        target_type=target_type,
                        target_turma=target_turma,
                        target_aluno=target_aluno,
                        reference_theme=reference_theme,
                        reference_book=reference_book,
                        reference_subject=reference_subject,
                        reference_note=str(st.session_state.get(ref_note_key, "")).strip(),
                        target_turmas_envio=target_turmas_envio,
                    )
                    if notify_new_challenge_enabled:
                        stats = notify_new_challenge(saved_challenge, send_email=True, send_whatsapp=True)
                        st.info(
                            "Comunicado de novo desafio enviado: "
                            f"E-mail {stats.get('email_ok', 0)}/{stats.get('email_total', 0)} | "
                            f"WhatsApp {stats.get('whatsapp_ok', 0)}/{stats.get('whatsapp_total', 0)}."
                        )
                    st.session_state[draft_info_key] = ""
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
                df["destino"] = [
                    _challenge_target_label(ch) if isinstance(ch, dict) else "-"
                    for ch in chs
                ]
                col_order = [c for c in ["semana", "destino", "nivel", "target_turmas_envio", "reference_theme", "reference_book", "reference_subject", "titulo", "pontos", "rubrica", "dica", "autor", "due_date", "created_at", "updated_at", "id"] if c in df.columns]
                if col_order:
                    df = df[col_order]
                if "semana" in df.columns and "nivel" in df.columns:
                    df = df.sort_values(["semana", "nivel"], ascending=[False, True])
                st.dataframe(df, use_container_width=True)

    elif menu_coord == "WhatsApp":
        st.markdown('<div class="main-header">WhatsApp (Evolution)</div>', unsafe_allow_html=True)
        st.caption("Tenta obter o QR code da sua instancia do WhatsApp via Evolution API.")

        remote_notice = str(st.session_state.pop("wiz_remote_control_notice", "")).strip()
        if remote_notice:
            st.success(remote_notice)

        wiz_paused = wiz_chatbot_paused()
        st.info(
            "Status do Bot Mister Wiz: "
            + ("Pausado (atendimento humano)." if wiz_paused else "Ativo.")
        )
        wc1, wc2 = st.columns([1, 1])
        if wc1.button("Assumir controle (!parar)", key="wa_wiz_pause_btn", disabled=wiz_paused):
            set_wiz_chatbot_paused(True)
            st.success("Bot Mister Wiz pausado.")
            st.rerun()
        if wc2.button("Retomar bot (!retomar)", key="wa_wiz_resume_btn", disabled=not wiz_paused):
            set_wiz_chatbot_paused(False)
            st.success("Bot Mister Wiz retomado.")
            st.rerun()

        with st.expander("Comando remoto por numero admin (teste)"):
            admin_sender = st.text_input(
                "Numero do admin (com DDI)",
                value="",
                placeholder="Ex: 5516999999999",
                key="wa_wiz_admin_sender",
            )
            admin_text = st.text_input(
                "Mensagem recebida",
                value="!parar",
                key="wa_wiz_admin_text",
            )
            if st.button("Processar comando remoto", key="wa_wiz_process_remote"):
                handled, remote_msg = handle_wiz_control_from_admin_number(admin_sender, admin_text)
                if handled:
                    st.success(remote_msg)
                    st.rerun()
                else:
                    st.warning("Comando ignorado. Verifique numero admin cadastrado e comando (!parar ou !retomar).")
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


