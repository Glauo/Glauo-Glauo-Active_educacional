import streamlit as st
import streamlit.components.v1 as components
import json
import os
import re
import shutil
import io
import zipfile
import threading
import uuid
import time
import hmac
import hashlib
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta
from typing import Optional
from fpdf import FPDF
from openai import OpenAI
import urllib.parse
import urllib.request
import urllib.error
import math
import calendar
import csv
import base64
import html
from financial_module_v2 import render_financial_module
from clinical_diet_safety import (
    build_clinical_prompt_block,
    build_revision_prompt,
    evaluate_clinical_rules,
    extract_patient_clinical_context,
    load_clinical_rules,
    normalize_text,
    requires_clinical_revision,
    summarize_clinical_audit,
    validate_diet_text,
)
from clinical_ai_knowledge import (
    build_clinical_ai_prompt_block,
    build_global_nutrition_guardrails,
    collect_camila_triage_notes,
    load_clinical_ai_knowledge,
    match_clinical_ai_topics,
    recommend_exams_for_topics,
)
try:
    from PIL import Image
except Exception:
    Image = None
try:
    from zoneinfo import ZoneInfo
except Exception:
    ZoneInfo = None

# =============================================================================
# 0. ASSETS (LANDING)
# =============================================================================
HERO_BG_IMG = "hero.png"
HERO_BG_OPT = "hero_opt.jpg"
NUTRI_BANNER_IMG = "nutri_ia.png"
LANDING_HERO_LOGO_IMG = "logo3_nutri.png"

# Layout inicial (pacote premium importado)
LANDING_ASSETS_DIR = os.path.join("assets", "layout_inicial")
LANDING_BG_PREMIUM_IMG = os.path.join(LANDING_ASSETS_DIR, "Fundos", "Hero_Background_DietHealth.png")
LANDING_GLASS_TEXTURE_IMG = os.path.join(LANDING_ASSETS_DIR, "Fundos", "Glassmorphism_Texture.png")
LANDING_LOGO_PREMIUM_IMG = os.path.join(LANDING_ASSETS_DIR, "Modern_Avocado_Logo_3D.png")
LANDING_AVATAR_PREMIUM_IMG = os.path.join(LANDING_ASSETS_DIR, "AI_Nutritionist_Avatar.png")
LANDING_BTN_ENTER_IMG = os.path.join(LANDING_ASSETS_DIR, "Botoes", "Button_Enter_3D.png")
LANDING_BTN_ASSINE_IMG = os.path.join(LANDING_ASSETS_DIR, "Botoes", "Button_Assine_3D.png")
LANDING_MOCKUP_PREVIEW_IMG = os.path.join(LANDING_ASSETS_DIR, "Mockups", "DietHealth_Home_Expanded_Redesign.png")
LANDING_SIDE_BRAND_LOGO_IMG = os.path.join(os.path.dirname(__file__), "logohealth.png")
CLINICAL_DIET_RULES_PATH = os.path.join(os.path.dirname(__file__), "clinical_diet_rules.json")
CLINICAL_AI_KNOWLEDGE_PATH = os.path.join(os.path.dirname(__file__), "clinical_ai_knowledge.json")


def _clinical_ai_payload() -> dict:
    try:
        return load_clinical_ai_knowledge(CLINICAL_AI_KNOWLEDGE_PATH) or {}
    except Exception:
        return {}


def _clinical_ai_topics(*texts: str) -> list[dict]:
    payload = _clinical_ai_payload()
    if not payload:
        return []
    try:
        return match_clinical_ai_topics(payload, *texts)
    except Exception:
        return []


def _clinical_ai_prompt(module: str, *texts: str) -> str:
    payload = _clinical_ai_payload()
    if not payload:
        return ""
    try:
        topics = match_clinical_ai_topics(payload, *texts)
        return build_clinical_ai_prompt_block(module, payload, topics)
    except Exception:
        return ""

def _inject_google_tag_landing() -> None:
    """
    Injeta Google Tag somente na landing inicial.
    Pode sobrescrever via variavel de ambiente GA_MEASUREMENT_ID.
    """
    measurement_id = (os.getenv("GA_MEASUREMENT_ID") or "G-J9FPT9VKT3").strip()
    if not measurement_id:
        return
    components.html(
        f"""
<script async src="https://www.googletagmanager.com/gtag/js?id={measurement_id}"></script>
<script>
  window.dataLayer = window.dataLayer || [];
  function gtag(){{dataLayer.push(arguments);}}
  gtag('js', new Date());
  gtag('config', '{measurement_id}', {{'send_page_view': true}});
</script>
""",
        height=0,
        width=0,
    )

def _inject_google_site_verification() -> None:
    """
    Inject Google Search Console verification meta into the landing page head.
    Override with GOOGLE_SITE_VERIFICATION if needed.
    """
    verification_token = (
        os.getenv("GOOGLE_SITE_VERIFICATION")
        or "V5hfU_uYVdtWFJ5MFuIXTS-SgBNWy26bTkiJNEZeIYM"
    ).strip()
    if not verification_token:
        return
    token_js = json.dumps(verification_token)
    components.html(
        f"""
<script>
(function() {{
  const token = {token_js};
  const rootDoc = window.parent && window.parent.document ? window.parent.document : document;
  const head = rootDoc.head || document.head;
  if (!head) return;

  let meta = head.querySelector('meta[name="google-site-verification"]');
  if (!meta) {{
    meta = rootDoc.createElement('meta');
    meta.setAttribute('name', 'google-site-verification');
    head.appendChild(meta);
  }}
  meta.setAttribute('content', token);
}})();
</script>
""",
        height=0,
        width=0,
    )

def _file_data_url(path: str) -> str:
    path = (path or "").strip()
    if not path or not os.path.exists(path):
        return ""
    try:
        mtime = float(os.path.getmtime(path))
    except Exception:
        mtime = 0.0
    return _file_data_url_cached(path, mtime)


def _file_data_url_optimized(path: str, max_w: int = 0, max_h: int = 0, prefer_jpeg: bool = False, quality: int = 82) -> str:
    path = (path or "").strip()
    if not path or not os.path.exists(path):
        return ""
    try:
        mtime = float(os.path.getmtime(path))
    except Exception:
        mtime = 0.0
    return _file_data_url_optimized_cached(path, mtime, int(max_w or 0), int(max_h or 0), bool(prefer_jpeg), int(quality or 82))


@st.cache_data(show_spinner=False, max_entries=256)
def _file_data_url_cached(path: str, _mtime: float) -> str:
    try:
        data = base64.b64encode(open(path, "rb").read()).decode("ascii")
        mime = "image/jpeg" if path.lower().endswith((".jpg", ".jpeg")) else "image/png"
        return f"data:{mime};base64,{data}"
    except Exception:
        return ""


@st.cache_data(show_spinner=False, max_entries=256)
def _file_data_url_optimized_cached(
    path: str,
    _mtime: float,
    max_w: int,
    max_h: int,
    prefer_jpeg: bool,
    quality: int,
) -> str:
    try:
        if Image is None:
            return _file_data_url_cached(path, _mtime)

        with Image.open(path) as img:
            has_alpha = (
                img.mode in ("RGBA", "LA")
                or ("transparency" in getattr(img, "info", {}))
            )

            if has_alpha:
                img = img.convert("RGBA")
            else:
                img = img.convert("RGB")

            if max_w > 0 or max_h > 0:
                limit_w = max_w if max_w > 0 else img.width
                limit_h = max_h if max_h > 0 else img.height
                resample = Image.Resampling.LANCZOS if hasattr(Image, "Resampling") else Image.LANCZOS
                img.thumbnail((limit_w, limit_h), resample)

            out = io.BytesIO()
            if prefer_jpeg and not has_alpha:
                img.save(out, format="JPEG", quality=max(55, min(quality, 90)), optimize=True, progressive=True)
                mime = "image/jpeg"
            else:
                img.save(out, format="PNG", optimize=True)
                mime = "image/png"

        encoded = base64.b64encode(out.getvalue()).decode("ascii")
        return f"data:{mime};base64,{encoded}"
    except Exception:
        return _file_data_url_cached(path, _mtime)


def _bg_data_url() -> str:
    """
    Retorna data URL do fundo otimizado para evitar travamento.
    """
    for path in (LANDING_BG_PREMIUM_IMG, HERO_BG_OPT, HERO_BG_IMG):
        url = _file_data_url_optimized(path, max_w=1280, max_h=720, prefer_jpeg=True, quality=68)
        if url:
            return url
    return ""


def _landing_texture_data_url() -> str:
    return _file_data_url_optimized(LANDING_GLASS_TEXTURE_IMG, max_w=900, max_h=900)


def _landing_avatar_data_url() -> str:
    return _file_data_url_optimized(LANDING_AVATAR_PREMIUM_IMG, max_w=220, max_h=220)


def _landing_enter_btn_data_url() -> str:
    return _file_data_url_optimized(LANDING_BTN_ENTER_IMG, max_w=220, max_h=84)


def _landing_assine_btn_data_url() -> str:
    return _file_data_url_optimized(LANDING_BTN_ASSINE_IMG, max_w=220, max_h=84)


def _landing_mockup_data_url() -> str:
    return _file_data_url_optimized(LANDING_MOCKUP_PREVIEW_IMG, max_w=820, max_h=540, prefer_jpeg=True, quality=68)


def _landing_logo_data_url() -> str:
    """
    Retorna data URL do logo principal da landing.
    """
    for path in (
        LANDING_HERO_LOGO_IMG,
        "logo3_nutri.png",
        "logo_abacatesystem2.png.png",
        "logo_abacatesystem.png",
        "logo_abacatesystem.jpg",
        "logo_abacatesystem.jpeg",
        "logo_abacatesystem.webp",
        LANDING_LOGO_PREMIUM_IMG,
        "nutri_ai_logo2_fixed.png",
    ):
        url = _file_data_url_optimized(path, max_w=520, max_h=260, prefer_jpeg=False, quality=72)
        if url:
            return url
    return ""


def _landing_side_brand_logo_data_url() -> str:
    for path in (
        LANDING_SIDE_BRAND_LOGO_IMG,
        LANDING_HERO_LOGO_IMG,
        LANDING_LOGO_PREMIUM_IMG,
    ):
        url = _file_data_url_optimized(path, max_w=760, max_h=320, prefer_jpeg=False, quality=86)
        if url:
            return url
    return ""

# =============================================================================
# 1. CONFIGURAÇÃO GERAL
# =============================================================================

# =============================================================================
# 2. LINKS IMPORTANTES (EDITE AQUI)
# =============================================================================
WHATSAPP_NUMERO = "5516993804499"
WHATSAPP_LINK = f"https://wa.me/{WHATSAPP_NUMERO}?text={urllib.parse.quote('Olá! Quero contratar o DietHealth System.')}"
MERCADO_PAGO_CHECKOUT = ""
MERCADO_PAGO_VIRTUAL = "https://mpago.li/1RHwqSa"

# (Opcional) Se você tiver links diferentes para PIX / BOLETO, coloque aqui.
# Se não tiver, o sistema usa o checkout acima para tudo.
MERCADO_PAGO_PIX = ""
MERCADO_PAGO_BOLETO = ""

# Assinatura (padrão: R$ 49,90 / 30 dias). Pode sobrescrever via variáveis de ambiente no Railway.
def _env_int(name: str, default: int) -> int:
    try:
        return int(str(os.getenv(name, default)).strip())
    except Exception:
        return int(default)

def _env_float(name: str, default: float) -> float:
    try:
        return float(str(os.getenv(name, default)).strip().replace(",", "."))
    except Exception:
        return float(default)

ASSINATURA_DIAS = _env_int("DIETHEALTH_ASSINATURA_DIAS", 30)
FREE_TRIAL_DAYS = 0
FREE_DIET_DAILY_LIMIT = 3
FREE_ANTHRO_DAILY_LIMIT = 3
FREE_ALLOWED_MENU_KEYS = {
    "dashboard",
    "atendimento",
    "consultorio",
    "gerar_dieta",
}
ASSINATURA_VALOR = _env_float("DIETHEALTH_ASSINATURA_VALOR", 49.90)
ONLINE_TIMEOUT_SECONDS = _env_int("DIETHEALTH_ONLINE_TIMEOUT_SECONDS", 120)
ONLINE_HEARTBEAT_SECONDS = _env_int("DIETHEALTH_ONLINE_HEARTBEAT_SECONDS", 90)
WA_GRAPH_VERSION = (os.getenv("WA_GRAPH_VERSION") or "v21.0").strip()

def _mp_access_token() -> str:
    token = (os.getenv("MERCADO_PAGO_ACCESS_TOKEN") or "").strip()
    if not token:
        try:
            token = str(st.secrets.get("MERCADO_PAGO_ACCESS_TOKEN", "")).strip()
        except Exception:
            token = ""
    return token.strip()

def _http_json(method: str, url: str, token: str = "", payload=None, timeout: int = 20, headers_extra=None):
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    if isinstance(headers_extra, dict):
        for k, v in headers_extra.items():
            k_txt = (str(k) if k is not None else "").strip()
            if not k_txt:
                continue
            headers[k_txt] = str(v) if v is not None else ""

    data = None
    if payload is not None:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")

    req = urllib.request.Request(url, data=data, headers=headers, method=method.upper())
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
            return int(getattr(resp, "status", 200)), (json.loads(raw) if raw else None)
    except urllib.error.HTTPError as e:
        try:
            raw = e.read().decode("utf-8", errors="replace")
            parsed = json.loads(raw) if raw else {"error": raw}
        except Exception:
            parsed = {"error": str(e)}
        return int(getattr(e, "code", 0) or 0), parsed
    except Exception as e:
        return 0, {"error": str(e)}

def _mp_external_reference(user_obj: dict) -> str:
    u = (user_obj.get("usuario") or "").strip().lower()
    return f"diethealth:{u}"

def _user_from_external_reference(ext_ref: str):
    if not ext_ref:
        return None
    ext_ref = str(ext_ref).strip()
    if not ext_ref.startswith("diethealth:"):
        return None
    u_norm = ext_ref.split("diethealth:", 1)[-1].strip().lower()
    if not u_norm:
        return None
    return next((x for x in users if (x.get("usuario") or "").strip().lower() == u_norm), None)

def mp_create_checkout_link(user_obj: dict):
    """
    Gera um link de pagamento identificado por usuário via Mercado Pago Preferences.
    Requer variável `MERCADO_PAGO_ACCESS_TOKEN`.
    """
    token = _mp_access_token()
    if not token:
        return None, "MERCADO_PAGO_ACCESS_TOKEN não configurado."

    ext_ref = _mp_external_reference(user_obj)
    base_url = _patient_portal_public_url()
    back_urls = {
        "success": f"{base_url}/?mp=success&ext_ref={urllib.parse.quote(ext_ref)}",
        "pending": f"{base_url}/?mp=pending&ext_ref={urllib.parse.quote(ext_ref)}",
        "failure": f"{base_url}/?mp=failure&ext_ref={urllib.parse.quote(ext_ref)}",
    }
    payload = {
        "items": [
            {
                "title": f"DietHealth Premium - {ASSINATURA_DIAS} dias",
                "quantity": 1,
                "currency_id": "BRL",
                "unit_price": float(ASSINATURA_VALOR),
            }
        ],
        "external_reference": ext_ref,
        "back_urls": back_urls,
        "auto_return": "approved",
        "metadata": {
            "app": "diethealth",
            "usuario": (user_obj.get("usuario") or "").strip().lower(),
            "plano_dias": int(ASSINATURA_DIAS),
        },
    }
    status, data = _http_json("POST", "https://api.mercadopago.com/checkout/preferences", token=token, payload=payload)
    if status not in (200, 201) or not isinstance(data, dict):
        return None, f"Falha ao gerar checkout (status {status})."

    init_point = (data.get("init_point") or "").strip()
    pref_id = (data.get("id") or "").strip()
    if not init_point:
        return None, "Falha ao gerar checkout (init_point vazio)."
    return {"url": init_point, "preference_id": pref_id, "external_reference": ext_ref}, ""

def mp_get_cached_checkout_url(user_obj: dict, force_new: bool = False) -> str:
    if not user_obj or not _mp_access_token():
        return ""
    u_norm = (user_obj.get("usuario") or "").strip().lower()
    if not u_norm:
        return ""
    cached_user = (st.session_state.get("mp_checkout_user") or "").strip().lower()
    cached_url = (st.session_state.get("mp_checkout_url") or "").strip()
    if (not force_new) and cached_user == u_norm and cached_url:
        return cached_url
    info, err = mp_create_checkout_link(user_obj)
    if info and info.get("url"):
        st.session_state["mp_checkout_user"] = u_norm
        st.session_state["mp_checkout_url"] = info.get("url", "")
        st.session_state["mp_checkout_last_err"] = ""
        return st.session_state["mp_checkout_url"]
    st.session_state["mp_checkout_last_err"] = err or "Nao foi possivel gerar o link agora."
    return ""

def mp_search_payments_by_external_reference(external_reference: str, limit: int = 10):
    token = _mp_access_token()
    if not token:
        return None, "MERCADO_PAGO_ACCESS_TOKEN não configurado."

    qref = urllib.parse.quote(str(external_reference))
    url = f"https://api.mercadopago.com/v1/payments/search?sort=date_created&criteria=desc&external_reference={qref}&limit={int(limit)}"
    status, data = _http_json("GET", url, token=token)
    if status != 200 or not isinstance(data, dict):
        return None, f"Falha ao consultar pagamentos (status {status})."
    return data.get("results") or [], ""

def _payments_has_mp_id(mp_id: str) -> bool:
    try:
        mp_id_str = str(mp_id)
    except Exception:
        mp_id_str = ""
    if not mp_id_str:
        return False
    return any(str(p.get("mp_id") or p.get("id") or "") == mp_id_str for p in payments)

def mp_try_auto_activate_user(user_obj: dict) -> bool:
    """
    Tenta localizar pagamento aprovado (Mercado Pago) para o usuário e liberar acesso automaticamente.
    - Atualiza users.json (status + paid_until)
    - Registra em payments.json (idempotente por mp_id)
    """
    if not user_obj or (user_obj.get("tipo") or "") == "admin":
        return False
    token = _mp_access_token()
    if not token:
        return False

    ext_ref = _mp_external_reference(user_obj)
    results, err = mp_search_payments_by_external_reference(ext_ref, limit=10)
    if not results:
        return False

    # Pega o pagamento mais recente aprovado que ainda não foi processado.
    approved = None
    for r in results:
        if not isinstance(r, dict):
            continue
        if (r.get("status") or "").lower() != "approved":
            continue
        mp_id = r.get("id")
        if mp_id and not _payments_has_mp_id(mp_id):
            approved = r
            break

    if not approved:
        return False

    mp_id = str(approved.get("id") or "").strip()
    amount = approved.get("transaction_amount")
    pm = approved.get("payment_method_id") or approved.get("payment_type_id") or ""
    created = approved.get("date_created") or ""

    # Libera acesso por ASSINATURA_DIAS, estendendo se já estiver ativo.
    today = datetime.now().date()
    venc_atual = _parse_date_ymd(user_obj.get("paid_until"))
    base = venc_atual if (venc_atual and venc_atual >= today) else today
    venc_new = base + timedelta(days=int(ASSINATURA_DIAS))

    user_obj["status"] = "active"
    user_obj["paid_until"] = str(venc_new)
    user_obj["mp_last_payment_id"] = mp_id
    user_obj["mp_last_payment_at"] = str(today)
    save_db("users.json", users)

    payments.append({
        "mp_id": mp_id,
        "dono": (user_obj.get("usuario") or "").strip().lower(),
        "external_reference": ext_ref,
        "status": "approved",
        "amount": amount,
        "method": pm,
        "date_created": created,
        "processed_at": str(today),
        "plan_days": int(ASSINATURA_DIAS),
    })
    save_db("payments.json", payments)
    return True

# =============================================================================
# 3. CHAVE DA IA (GROQ / OPENAI COMPATÍVEL)
# =============================================================================
# Melhor prática (recomendado):
# - No Streamlit Cloud, configure em Settings -> Secrets:
#   GROQ_API_KEY="SUA_CHAVE"
# - Localmente, configure variável de ambiente:
#   set GROQ_API_KEY=SUA_CHAVE   (Windows)
#   export GROQ_API_KEY=SUA_CHAVE (Linux/Mac)
#
# Se você quiser forçar no código, edite CHAVE_FIXA abaixo.
CHAVE_FIXA = ""  # deixe vazio (NÃO coloque chave real no código)

def get_api_key() -> str:
    """
    Prioridade:
    1) .streamlit/secrets.toml -> GROQ_API_KEY
    2) variável de ambiente -> GROQ_API_KEY
    3) CHAVE_FIXA (vazia)
    """
    key = ""
    try:
        key = str(st.secrets.get("GROQ_API_KEY", "")).strip()
    except Exception:
        key = ""

    if not key:
        key = os.getenv("GROQ_API_KEY", "").strip()

    if not key:
        key = (CHAVE_FIXA or "").strip()

    # Defensive: Railway/clipboard can introduce hidden whitespace/newlines.
    key = re.sub(r"\s+", "", str(key))
    return key

def get_groq_client():
    key = get_api_key()
    if not key:
        return None
    return OpenAI(api_key=key, base_url="https://api.groq.com/openai/v1")


# =============================================================================
# 3.1 IMC INFANTIL (5–18): Percentil CDC (requer data/cdc_bmi_2_20.csv)
# =============================================================================
CDC_BMI_CSV = os.path.join("data", "cdc_bmi_2_20.csv")
WHO_BMI_0_5_GIRLS_XLSX = os.path.join("data", "oms", "bfa_girls_0_5.xlsx")
WHO_BMI_0_5_BOYS_XLSX = os.path.join("data", "oms", "bfa_boys_0_5.xlsx")
WHO_BMI_5_19_GIRLS_XLSX = os.path.join("data", "oms", "bmi_girls_5_19.xlsx")
WHO_BMI_5_19_BOYS_XLSX = os.path.join("data", "oms", "bmi_boys_5_19.xlsx")

def calc_imc_kg_m(peso_kg: float, altura_m: float) -> float:
    if not peso_kg or not altura_m or altura_m <= 0:
        return 0.0
    return float(peso_kg) / (float(altura_m) ** 2)

def _norm_cdf(z: float) -> float:
    return 0.5 * (1.0 + math.erf(z / math.sqrt(2.0)))

@st.cache_data
def load_cdc_bmi_lms():
    """
    Carrega CSV CDC (BMI-for-age 2–20). Precisa colunas: Sex, Agemos, L, M, S.
    Se o arquivo estiver em formato Excel/binary, retorna None.
    """
    if not os.path.exists(CDC_BMI_CSV):
        return None

    try:
        with open(CDC_BMI_CSV, "rb") as f:
            head = f.read(2048)
            if b"\x00" in head:
                return None
    except Exception:
        return None

    try:
        with open(CDC_BMI_CSV, "r", encoding="utf-8-sig") as f:
            sample = f.read(2048)
    except Exception:
        return None

    # Detecta delimitador simples
    delim = "," if sample.count(",") >= sample.count(";") else ";"

    rows = []
    with open(CDC_BMI_CSV, "r", encoding="utf-8-sig", errors="replace") as f:
        reader = csv.DictReader(f, delimiter=delim)
        for r in reader:
            rows.append({(k or "").strip(): (v.strip() if isinstance(v, str) else v) for k, v in r.items()})
    return rows

def _get_float(d: dict, *keys, default=None):
    for k in keys:
        if k in d and d[k] not in (None, ""):
            try:
                return float(str(d[k]).replace(",", "."))
            except Exception:
                pass
    return default

def cdc_bmi_percentil(idade_anos: int, idade_meses: int, sexo: str, imc: float):
    data = load_cdc_bmi_lms()
    if not data:
        return None, None

    sexo_u = (sexo or "").strip().upper()
    sex_code = 1 if (sexo_u.startswith("M") or "MASC" in sexo_u) else 2

    age_mos = int(idade_anos) * 12 + int(idade_meses)
    target = float(age_mos) + 0.5

    items = []
    for r in data:
        s = int(_get_float(r, "Sex", "sex", default=0) or 0)
        if s != sex_code:
            continue
        ag = _get_float(r, "Agemos", "agemos", "AgeMos", default=None)
        if ag is None:
            continue
        L = _get_float(r, "L", default=None)
        M = _get_float(r, "M", default=None)
        S = _get_float(r, "S", default=None)
        if None in (L, M, S):
            continue
        items.append((ag, L, M, S))

    if not items:
        return None, None

    items.sort(key=lambda x: x[0])

    lo = None
    hi = None
    for it in items:
        if it[0] <= target:
            lo = it
        if it[0] >= target and hi is None:
            hi = it
            break
    if lo is None:
        lo = items[0]
    if hi is None:
        hi = items[-1]

    if hi[0] == lo[0]:
        _, L, M, S = lo
    else:
        t = (target - lo[0]) / (hi[0] - lo[0])
        L = lo[1] + t * (hi[1] - lo[1])
        M = lo[2] + t * (hi[2] - lo[2])
        S = lo[3] + t * (hi[3] - lo[3])

    try:
        if L == 0:
            z = math.log(imc / M) / S
        else:
            z = (((imc / M) ** L) - 1.0) / (L * S)
        perc = _norm_cdf(z) * 100.0
        return perc, z
    except Exception:
        return None, None

def _sexo_ref_masculino(sexo: str) -> bool:
    sexo_u = (sexo or "").strip().upper()
    return sexo_u.startswith("M") or "MASC" in sexo_u

@st.cache_data
def load_who_bmi_lms(path: str, age_col: str):
    if not os.path.exists(path):
        return None
    try:
        df = pd.read_excel(path)
    except Exception:
        return None

    df.columns = [str(c).strip() for c in df.columns]
    needed = {age_col, "L", "M", "S"}
    if not needed.issubset(set(df.columns)):
        return None

    rows = []
    for row in df[[age_col, "L", "M", "S"]].to_dict(orient="records"):
        try:
            age_val = float(row[age_col])
            L = float(row["L"])
            M = float(row["M"])
            S = float(row["S"])
        except Exception:
            continue
        if not all(math.isfinite(x) for x in (age_val, L, M, S)):
            continue
        rows.append((age_val, L, M, S))
    return rows or None

def _interpolate_lms_rows(rows, target: float):
    if not rows:
        return None
    rows = sorted(rows, key=lambda x: x[0])
    lo = None
    hi = None
    for item in rows:
        if item[0] <= target:
            lo = item
        if item[0] >= target and hi is None:
            hi = item
            break
    if lo is None:
        lo = rows[0]
    if hi is None:
        hi = rows[-1]
    if hi[0] == lo[0]:
        _, L, M, S = lo
        return L, M, S
    t = (target - lo[0]) / (hi[0] - lo[0])
    L = lo[1] + t * (hi[1] - lo[1])
    M = lo[2] + t * (hi[2] - lo[2])
    S = lo[3] + t * (hi[3] - lo[3])
    return L, M, S

def _lms_to_zscore(valor: float, L: float, M: float, S: float):
    try:
        if valor <= 0 or M <= 0 or S <= 0:
            return None
        if L == 0:
            return math.log(valor / M) / S
        return (((valor / M) ** L) - 1.0) / (L * S)
    except Exception:
        return None

def who_bmi_0_5_percentil(idade_dias: int, sexo: str, imc: float):
    path = WHO_BMI_0_5_BOYS_XLSX if _sexo_ref_masculino(sexo) else WHO_BMI_0_5_GIRLS_XLSX
    data = load_who_bmi_lms(path, "Day")
    if not data:
        return None, None
    lms = _interpolate_lms_rows(data, float(idade_dias))
    if not lms:
        return None, None
    z = _lms_to_zscore(imc, *lms)
    if z is None:
        return None, None
    return _norm_cdf(z) * 100.0, z

def who_bmi_5_19_percentil(idade_meses: int, sexo: str, imc: float):
    path = WHO_BMI_5_19_BOYS_XLSX if _sexo_ref_masculino(sexo) else WHO_BMI_5_19_GIRLS_XLSX
    data = load_who_bmi_lms(path, "Month")
    if not data:
        return None, None
    lms = _interpolate_lms_rows(data, float(idade_meses))
    if not lms:
        return None, None
    z = _lms_to_zscore(imc, *lms)
    if z is None:
        return None, None
    return _norm_cdf(z) * 100.0, z

def classificar_bmi_oms_0_5(zscore: float) -> str:
    if zscore is None:
        return "Classificação indisponível"
    if zscore < -3:
        return "Magreza acentuada"
    if zscore < -2:
        return "Magreza"
    if zscore <= 1:
        return "Eutrofia"
    if zscore <= 2:
        return "Risco de sobrepeso"
    if zscore <= 3:
        return "Sobrepeso"
    return "Obesidade"

def classificar_bmi_oms_5_19(zscore: float) -> str:
    if zscore is None:
        return "Classificação indisponível"
    if zscore < -3:
        return "Magreza acentuada"
    if zscore < -2:
        return "Magreza"
    if zscore <= 1:
        return "Eutrofia"
    if zscore <= 2:
        return "Sobrepeso"
    return "Obesidade"

def _trimestre_gestacional(semanas: float) -> str:
    if semanas <= 0:
        return ""
    if semanas <= 13:
        return "1º trimestre"
    if semanas <= 27:
        return "2º trimestre"
    return "3º trimestre"

def classificar_imc_crianca(percentil: float) -> str:
    if percentil is None:
        return "Percentil indisponível"
    if percentil < 5:
        return "Baixo peso (< P5)"
    if percentil < 85:
        return "Peso saudável (P5–P84)"
    if percentil < 95:
        return "Sobrepeso (P85–P94)"
    return "Obesidade (≥ P95)"


def classificar_imc_adulto_oms(imc: float) -> str:
    if imc is None or imc <= 0:
        return ""
    if imc < 16.0:
        return "Magreza grave"
    if imc < 17.0:
        return "Magreza moderada"
    if imc < 18.5:
        return "Magreza leve"
    if imc < 25.0:
        return "Peso normal"
    if imc < 30.0:
        return "Sobrepeso (pré-obesidade)"
    if imc < 35.0:
        return "Obesidade Grau 1"
    if imc < 40.0:
        return "Obesidade Grau 2"
    return "Obesidade Grau 3"


def faixa_peso_ideal_oms(altura_m: float) -> tuple[float, float]:
    if not altura_m or altura_m <= 0:
        return (0.0, 0.0)
    return (18.5 * (altura_m ** 2), 24.9 * (altura_m ** 2))

# =============================================================================
# 4. CSS (VISIBILIDADE/CONTRASTE PROFISSIONAL - SEM “APAGAR” TEXTO)
# =============================================================================

# =============================================================================
# 5. BANCO DE DADOS (JSON) E FUNÇÕES ÚTEIS
# =============================================================================
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

DATA_DIR = _get_config_value("DIETHEALTH_DATA_DIR", ".")
BACKUP_DIR = os.path.join(DATA_DIR, "_data_backups")
DATA_IO_LOCK = threading.RLock()
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(BACKUP_DIR, exist_ok=True)

try:
    import psycopg2
    import psycopg2.extras
except Exception:
    psycopg2 = None


def _db_url():
    return _get_config_value("DIETHEALTH_DATABASE_URL", "") or _get_config_value("DATABASE_URL", "")


def _db_enabled():
    return bool(_db_url()) and psycopg2 is not None


def _on_railway():
    return bool(
        os.getenv("RAILWAY_ENVIRONMENT")
        or os.getenv("RAILWAY_PROJECT_ID")
        or os.getenv("RAILWAY_SERVICE_ID")
        or os.getenv("RAILWAY_PUBLIC_DOMAIN")
    )


def _db_connect():
    # New connection per operation keeps behavior predictable across Streamlit reruns.
    return psycopg2.connect(_db_url(), connect_timeout=8)


def _db_init(conn):
    with conn.cursor() as cur:
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS diethealth_kv (
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
                cur.execute("SELECT value FROM diethealth_kv WHERE key = %s", (key,))
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
                    INSERT INTO diethealth_kv (key, value, updated_at)
                    VALUES (%s, %s, now())
                    ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value, updated_at = now()
                    """,
                    (key, payload),
                )
        return True
    except Exception:
        return False


def _db_key(file):
    return str(file).strip()


def _path(file):
    return os.path.join(DATA_DIR, file)


def _atomic_write_json(path, data):
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    payload = json.dumps(data, ensure_ascii=False, indent=4)
    tmp_path = path + ".tmp"
    with open(tmp_path, "w", encoding="utf-8") as f:
        f.write(payload)
    os.replace(tmp_path, path)


def _backup_path(file):
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    base = os.path.basename(file)
    return os.path.join(BACKUP_DIR, f"{base}_{stamp}.bak")


def _rotate_backups(file, keep=50):
    base = os.path.basename(file)
    candidates = []
    for name in os.listdir(BACKUP_DIR):
        if name.startswith(base + "_") and name.endswith(".bak"):
            candidates.append(os.path.join(BACKUP_DIR, name))
    candidates.sort(key=lambda x: os.path.getmtime(x), reverse=True)
    for old in candidates[keep:]:
        try:
            os.remove(old)
        except Exception:
            pass


def _load_latest_backup(file):
    base = os.path.basename(file)
    candidates = []
    for name in os.listdir(BACKUP_DIR):
        if name.startswith(base + "_") and name.endswith(".bak"):
            candidates.append(os.path.join(BACKUP_DIR, name))
    candidates.sort(key=lambda x: os.path.getmtime(x), reverse=True)
    for b in candidates:
        try:
            with open(b, "r", encoding="utf-8") as f:
                data = json.load(f)
            return data
        except Exception:
            continue
    return None


def _sanitize_json(obj):
    if isinstance(obj, float) and not math.isfinite(obj):
        return None
    if isinstance(obj, dict):
        return {k: _sanitize_json(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_sanitize_json(v) for v in obj]
    return obj


def _clean_text(value) -> str:
    if value is None:
        return ""
    txt = str(value).strip()
    if txt.lower() in ("none", "nan"):
        return ""
    return txt


def _beautify_generated_text(text: str) -> str:
    txt = _clean_text(text)
    if not txt:
        return ""
    txt = txt.replace("\r\n", "\n").replace("\r", "\n")
    txt = re.sub(r"[ \t]+\n", "\n", txt)

    heading_rx = re.compile(
        r"^(Rx\s*\d+\s*:|F[oó]rmula\s*\d+\s*-|Se[cç][aã]o\s*\d+\s*:|\d+\.\s+.+)",
        flags=re.IGNORECASE,
    )

    lines_out = []
    for raw in txt.split("\n"):
        line = raw.rstrip()
        if not line:
            if lines_out and lines_out[-1] != "":
                lines_out.append("")
            continue
        if heading_rx.match(line) and lines_out and lines_out[-1] != "":
            lines_out.append("")
        lines_out.append(line)

    while lines_out and lines_out[-1] == "":
        lines_out.pop()
    return "\n".join(lines_out)


def _bold_meal_titles(text: str) -> str:
    """
    Garante títulos de refeições em negrito para facilitar leitura do paciente.
    """
    txt = _clean_text(text)
    if not txt:
        return ""

    meal_rx = re.compile(
        r"^\s*(?:[-*]\s*)?(?:\d+\s*[\)\.\-:]\s*)?"
        r"(cafe da manha|café da manhã|lanche da manha|lanche da manhã|almoco|almoço|"
        r"lanche da tarde|jantar|ceia|pre treino|pré treino|pos treino|pós treino|"
        r"desjejum)\s*[:\-]?\s*(.*)$",
        flags=re.IGNORECASE,
    )

    out = []
    for raw in txt.replace("\r\n", "\n").replace("\r", "\n").split("\n"):
        line = raw.rstrip()
        if not line:
            out.append(line)
            continue
        if "**" in line:
            out.append(line)
            continue
        m = meal_rx.match(line)
        if not m:
            out.append(line)
            continue
        meal = m.group(1).strip()
        rest = m.group(2).strip()
        if rest:
            out.append(f"**{meal}**: {rest}")
        else:
            out.append(f"**{meal}**")
    return "\n".join(out)


def _render_generated_doc_preview(titulo: str, texto: str, meta: str = ""):
    doc = _beautify_generated_text(texto)
    if not doc:
        return
    t = _clean_text(titulo) or "Pre-visualizacao"
    m = _clean_text(meta) or "DietHealth - Documento clinico"
    with st.container(border=True):
        st.markdown(f"**[DOC] {t}**")
        st.caption(m)
        st.text(doc)

def _blank_anamnese() -> dict:
    return {
        "queixa_principal": "",
        "alergias": "",
        "intolerancias": "",
        "condicoes_saude": "",
        "medicamentos_suplementos": "",
        "observacoes_clinicas": "",
    }


def _normalize_anamnese_data(raw) -> dict:
    data = _blank_anamnese()
    if isinstance(raw, str):
        data["observacoes_clinicas"] = _clean_text(raw)
        return data
    if not isinstance(raw, dict):
        return data

    for key in data.keys():
        val = _clean_text(raw.get(key))
        if val:
            data[key] = val

    legacy_alias = {
        "queixa": "queixa_principal",
        "problemas_saude": "condicoes_saude",
        "doencas": "condicoes_saude",
        "doenças": "condicoes_saude",
        "medicacoes": "medicamentos_suplementos",
        "medicações": "medicamentos_suplementos",
        "medicacao": "medicamentos_suplementos",
        "medicação": "medicamentos_suplementos",
        "intolerancias_alimentares": "intolerancias",
        "intolerâncias_alimentares": "intolerancias",
        "obs": "observacoes_clinicas",
        "observacoes": "observacoes_clinicas",
        "observações": "observacoes_clinicas",
    }
    for old_key, new_key in legacy_alias.items():
        if data.get(new_key):
            continue
        val = _clean_text(raw.get(old_key))
        if val:
            data[new_key] = val
    return data


def _anamnese_has_content(anamnese: dict) -> bool:
    if not isinstance(anamnese, dict):
        return False
    return any(_clean_text(v) for v in anamnese.values())


def _ensure_patient_ids(pacs):
    changed = False
    if not isinstance(pacs, list):
        return False
    for p in pacs:
        if not isinstance(p, dict):
            continue
        if not p.get("id"):
            p["id"] = uuid.uuid4().hex
            changed = True
        hist = p.get("historico")
        if not isinstance(hist, list):
            p["historico"] = []
            hist = p["historico"]
            changed = True
        for h in hist:
            if isinstance(h, dict) and not h.get("id"):
                h["id"] = uuid.uuid4().hex
                changed = True

        anamnese = _normalize_anamnese_data(p.get("anamnese"))
        legacy_top_map = {
            "alergias": "alergias",
            "intolerancias": "intolerancias",
            "intolerâncias": "intolerancias",
            "problemas_saude": "condicoes_saude",
            "problemas de saude": "condicoes_saude",
            "doencas": "condicoes_saude",
            "doenças": "condicoes_saude",
            "medicacoes": "medicamentos_suplementos",
            "medicações": "medicamentos_suplementos",
            "observacoes": "observacoes_clinicas",
            "observações": "observacoes_clinicas",
            "anamnese_texto": "observacoes_clinicas",
        }
        for old_key, new_key in legacy_top_map.items():
            if anamnese.get(new_key):
                continue
            legacy_val = _clean_text(p.get(old_key))
            if legacy_val:
                anamnese[new_key] = legacy_val

        if not anamnese.get("observacoes_clinicas"):
            for h in reversed(hist):
                if not isinstance(h, dict):
                    continue
                nota_hist = _clean_text(h.get("nota") or h.get("observacoes") or h.get("observações"))
                if nota_hist:
                    anamnese["observacoes_clinicas"] = nota_hist
                    break

        if p.get("anamnese") != anamnese:
            p["anamnese"] = anamnese
            changed = True
    return changed


def _merge_patient(existing, incoming):
    if not isinstance(existing, dict):
        existing = {}
    if not isinstance(incoming, dict):
        return existing
    merged = dict(existing)
    merged.update(incoming)

    hist_existing = existing.get("historico") if isinstance(existing.get("historico"), list) else []
    hist_incoming = incoming.get("historico") if isinstance(incoming.get("historico"), list) else []

    by_id = {}
    for h in hist_existing:
        if isinstance(h, dict) and h.get("id"):
            by_id[h["id"]] = h
    for h in hist_incoming:
        if isinstance(h, dict) and h.get("id"):
            by_id[h["id"]] = h
        elif isinstance(h, dict):
            # If a history entry has no id, keep it (but we try to ensure ids before merge)
            hid = uuid.uuid4().hex
            by_id[hid] = {**h, "id": hid}
    merged["historico"] = list(by_id.values())
    return merged


def _merge_patients(stored, incoming, keep_missing=True):
    stored = stored if isinstance(stored, list) else []
    incoming = incoming if isinstance(incoming, list) else []

    _ensure_patient_ids(stored)
    _ensure_patient_ids(incoming)

    stored_by_id = {}
    for p in stored:
        if isinstance(p, dict) and p.get("id"):
            stored_by_id[p["id"]] = p

    by_id = {}
    for p in incoming:
        if isinstance(p, dict) and p.get("id"):
            by_id[p["id"]] = _merge_patient(stored_by_id.get(p["id"]), p)
        else:
            # Fallback for malformed records
            pid = uuid.uuid4().hex
            if isinstance(p, dict):
                p = {**p, "id": pid}
            by_id[pid] = p

    if keep_missing:
        for pid, p in stored_by_id.items():
            if pid not in by_id:
                by_id[pid] = p
    return list(by_id.values())


def load_db(file, default):
    """Carrega JSON/DB com fallback para backups.

    Importante:
    - Em hospedagens como Streamlit Cloud, salvar em arquivo local pode ser temporario.
      Para nao perder dados, configure DIETHEALTH_DATABASE_URL (Postgres).
    """
    file = str(file)
    key = _db_key(file)

    with DATA_IO_LOCK:
        if _db_enabled():
            data = _db_get(key)
            if data is not None:
                return data

        path = _path(file)
        bak = path + ".bak"

        paths = [path, bak]
        for pth in paths:
            if not os.path.exists(pth):
                continue
            try:
                with open(pth, "r", encoding="utf-8") as f:
                    data = json.load(f)

                # Se o arquivo principal existir mas vier vazio, tenta recuperar do backup timestamp.
                if (data == [] or data == {}) and pth == path:
                    recovered = _load_latest_backup(file)
                    if recovered not in (None, [], {}):
                        data = recovered
                        _atomic_write_json(path, data)

                # Se carregou do .bak, tenta restaurar o principal.
                if pth != path:
                    try:
                        _atomic_write_json(path, data)
                    except Exception:
                        pass

                # Garante IDs (evita sobrescrita perder pacientes em uso simultaneo)
                if file == "pacientes.json" and isinstance(data, list):
                    if _ensure_patient_ids(data):
                        _atomic_write_json(path, data)

                # Seed no DB (primeira vez)
                if _db_enabled():
                    _db_set(key, data)

                return data
            except Exception:
                continue

        # Ultimo fallback: backup timestamp
        recovered = _load_latest_backup(file)
        if recovered is not None:
            try:
                _atomic_write_json(path, recovered)
            except Exception:
                pass
            if _db_enabled():
                _db_set(key, recovered)
            return recovered

        # Seed no DB mesmo sem arquivo
        if _db_enabled():
            _db_set(key, default)

        return default


# Guardrail: Railway filesystem can be ephemeral; require Postgres to avoid silent data loss.
if _on_railway() and not _db_enabled():
    st.error(
        "ATENCAO: Este DietHealth esta rodando no Railway sem banco de dados configurado. "
        "Isso pode fazer pacientes e historicos sumirem quando o servico reiniciar. "
        "Configure `DIETHEALTH_DATABASE_URL` (Postgres) nas variaveis do Railway e reinicie o servico."
    )
    st.stop()


def save_db(file, data):
    """Salva JSON/DB com backup.

    Para `pacientes.json`, tenta mesclar com o estado atual para reduzir perda em uso simultaneo.
    """
    file = str(file)
    key = _db_key(file)

    try:
        data = _sanitize_json(data)

        with DATA_IO_LOCK:
            # Mescla apenas pacientes ainda presentes na lista recebida.
            # Isso preserva atualizações do mesmo prontuário sem ressuscitar pacientes excluídos manualmente.
            if file == "pacientes.json" and isinstance(data, list):
                try:
                    stored_now = load_db(file, [])
                    data = _merge_patients(stored_now, data, keep_missing=False)
                except Exception:
                    pass

            if _db_enabled():
                _db_set(key, data)

            path = _path(file)
            bak_simple = path + ".bak"

            if os.path.exists(path):
                try:
                    shutil.copy2(path, bak_simple)
                except Exception:
                    pass
                try:
                    shutil.copy2(path, _backup_path(file))
                    _rotate_backups(file)
                except Exception:
                    pass

            _atomic_write_json(path, data)

    except Exception:
        return False

    return True


def _save_users_presence_fast():
    """
    Atualizacao leve de presenca do usuario.
    Evita backup/copia em toda batida de heartbeat para reduzir lentidao.
    """
    try:
        with DATA_IO_LOCK:
            if _db_enabled():
                _db_set(_db_key("users.json"), users)
            _atomic_write_json(_path("users.json"), users)
        return True
    except Exception:
        return False

def filtrar_por_usuario(lista_dados):
    if st.session_state.get("tipo") == "admin":
        return lista_dados
    usuario = (st.session_state.get("usuario") or "").strip().lower()
    return [item for item in lista_dados if (item.get("dono") or "").strip().lower() == usuario]

def _get_user_obj():
    u_norm = (st.session_state.get("usuario") or "").strip().lower()
    return next((x for x in users if (x.get("usuario") or "").strip().lower() == u_norm), None)

def _normalize_wa_provider(value: str) -> str:
    p = (value or "").strip().lower()
    if p in ("wapi", "evolution", "evolution-api", "evolution_api"):
        return "wapi"
    if p in ("cloud", "meta", "meta-cloud", "meta_cloud", "cloud_api"):
        return "cloud"
    return ""

def _guess_user_wa_provider(user_obj) -> str:
    explicit = _normalize_wa_provider((user_obj.get("wa_provider") if user_obj else "") or "")
    if explicit:
        return explicit
    if user_obj and (((user_obj.get("wa_api_url") or "").strip()) or ((user_obj.get("wa_instance") or "").strip())):
        return "wapi"
    if user_obj and ((user_obj.get("wa_phone_id") or "").strip()):
        return "cloud"
    env_provider = _normalize_wa_provider(_secret_or_env("WA_PROVIDER", "WA_PROVIDER_DEFAULT"))
    if env_provider:
        return env_provider
    return "wapi"

def _get_user_whatsapp_settings(user_obj):
    provider = _guess_user_wa_provider(user_obj)

    token = ((user_obj.get("wa_token") if user_obj else "") or "").strip()
    phone_id = ((user_obj.get("wa_phone_id") if user_obj else "") or "").strip()
    api_url = ((user_obj.get("wa_api_url") if user_obj else "") or "").strip()
    instance = ((user_obj.get("wa_instance") if user_obj else "") or "").strip()

    if provider == "wapi":
        if not token:
            token = _secret_or_env("WAPI_TOKEN", "EVOLUTION_API_KEY", "WA_TOKEN")
        if not api_url:
            api_url = _secret_or_env("WAPI_URL", "EVOLUTION_API_URL")
        if not instance:
            instance = _secret_or_env("WAPI_INSTANCE", "EVOLUTION_INSTANCE")
    else:
        if not token:
            token = _secret_or_env("WA_TOKEN")
        if not phone_id:
            phone_id = _secret_or_env("WA_PHONE_ID")

    return {
        "provider": provider,
        "token": token,
        "phone_id": phone_id,
        "api_url": api_url,
        "instance": instance,
    }

def _get_user_whatsapp_creds(user_obj):
    cfg = _get_user_whatsapp_settings(user_obj)
    return cfg.get("token") or "", cfg.get("phone_id") or ""

def _parse_date_ymd(val):
    if not val:
        return None
    try:
        return datetime.strptime(str(val), "%Y-%m-%d").date()
    except Exception:
        return None

def _fmt_date_br(val):
    if not val:
        return ""
    try:
        return datetime.strptime(str(val), "%Y-%m-%d").strftime("%d/%m/%Y")
    except Exception:
        return str(val)

def _check_user_access(user):
    if not user:
        return False, "not_found", None
    user_type = (user.get("tipo") or "").strip().lower()
    if user_type == "admin":
        return True, "", None
    if user_type == "patient":
        status = (user.get("status") or "active").strip().lower()
        if status == "active":
            return True, "", None
        return False, "pending", None
    status = (user.get("status") or "active").strip().lower()
    paid_until = _parse_date_ymd(user.get("paid_until"))
    today = datetime.now().date()
    if status == "blocked":
        return False, "blocked", paid_until
    if paid_until and today <= paid_until and status == "active":
        return True, "premium", paid_until
    # Sem pagamento ou pagamento vencido: acesso free liberado.
    if status == "active":
        return True, "free", paid_until
    return False, "pending", paid_until

def _current_user_obj():
    u_norm = (st.session_state.get("usuario") or "").strip().lower()
    if not u_norm:
        return None
    return next((x for x in users if (x.get("usuario") or "").strip().lower() == u_norm), None)

def _is_premium_user(user) -> bool:
    if not user:
        return False
    user_type = (user.get("tipo") or "").strip().lower()
    if user_type in {"admin", "patient"}:
        return True
    paid_until = _parse_date_ymd(user.get("paid_until"))
    if not paid_until:
        return False
    return datetime.now().date() <= paid_until

def _is_free_user(user) -> bool:
    if not user:
        return False
    user_type = (user.get("tipo") or "").strip().lower()
    if user_type in {"admin", "patient"}:
        return False
    return not _is_premium_user(user)

def _free_diet_usage(user) -> dict:
    usage = user.get("free_diet_usage")
    if not isinstance(usage, dict):
        usage = {}
    return usage

def _free_diet_remaining(user) -> int:
    if not user:
        return 0
    usage = _free_diet_usage(user)
    today = str(datetime.now().date())
    used = int(usage.get(today, 0) or 0)
    return max(0, FREE_DIET_DAILY_LIMIT - used)

def _increment_free_diet_usage(user, count: int = 1) -> None:
    if not user:
        return
    usage = _free_diet_usage(user)
    today = str(datetime.now().date())
    used = int(usage.get(today, 0) or 0)
    usage[today] = used + max(1, int(count))
    user["free_diet_usage"] = usage
    try:
        save_db("users.json", users)
    except Exception:
        pass

def _free_anthro_usage(user) -> dict:
    usage = user.get("free_anthro_usage")
    if not isinstance(usage, dict):
        usage = {}
    return usage

def _free_anthro_remaining(user) -> int:
    if not user:
        return 0
    usage = _free_anthro_usage(user)
    today = str(datetime.now().date())
    used = int(usage.get(today, 0) or 0)
    return max(0, FREE_ANTHRO_DAILY_LIMIT - used)

def _increment_free_anthro_usage(user, count: int = 1) -> None:
    if not user:
        return
    usage = _free_anthro_usage(user)
    today = str(datetime.now().date())
    used = int(usage.get(today, 0) or 0)
    usage[today] = used + max(1, int(count))
    user["free_anthro_usage"] = usage
    try:
        save_db("users.json", users)
    except Exception:
        pass

AUTH_QUERY_KEY = "dh_auth"

def _auth_secret_value() -> str:
    secret = _secret_or_env("DIETHEALTH_AUTH_SECRET", "AUTH_SECRET", "SECRET_KEY")
    if secret:
        return secret
    # Fallback para não quebrar em ambientes sem variável configurada.
    return "diethealth-auth-v1"

def _qp_get(name: str) -> str:
    key = (name or "").strip()
    if not key:
        return ""
    try:
        v = st.query_params.get(key, "")
        if isinstance(v, list):
            return str(v[0]).strip() if v else ""
        return str(v).strip() if v is not None else ""
    except Exception:
        pass
    try:
        raw = st.experimental_get_query_params()
        v = raw.get(key, [""])
        if isinstance(v, list):
            return str(v[0]).strip() if v else ""
        return str(v).strip() if v is not None else ""
    except Exception:
        return ""

def _qp_set(name: str, value: str = ""):
    key = (name or "").strip()
    if not key:
        return
    val = (value or "").strip()
    try:
        qp = st.query_params
        current_val = str(qp.get(key, "") or "").strip()
        if current_val == val:
            return
        if val:
            qp[key] = val
        elif key in qp:
            del qp[key]
        return
    except Exception:
        pass
    try:
        qp = st.experimental_get_query_params()
        current_raw = qp.get(key, [""])
        current_val = str(current_raw[0]).strip() if isinstance(current_raw, list) and current_raw else str(current_raw or "").strip()
        if current_val == val:
            return
        if val:
            qp[key] = val
        else:
            qp.pop(key, None)
        st.experimental_set_query_params(**qp)
    except Exception:
        pass

def _build_login_token(usuario: str) -> str:
    u_norm = (usuario or "").strip().lower()
    if not u_norm:
        return ""
    payload = {"u": u_norm, "iat": int(time.time())}
    payload_txt = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    sig = hmac.new(_auth_secret_value().encode("utf-8"), payload_txt.encode("utf-8"), hashlib.sha256).hexdigest()
    packed = {"p": payload, "s": sig}
    raw = json.dumps(packed, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")

def _read_login_token_usuario(token: str) -> str:
    tok = (token or "").strip()
    if not tok:
        return ""
    try:
        pad = "=" * (-len(tok) % 4)
        raw = base64.urlsafe_b64decode((tok + pad).encode("ascii")).decode("utf-8", errors="replace")
        packed = json.loads(raw)
        payload = packed.get("p") if isinstance(packed, dict) else None
        sig = str((packed or {}).get("s") or "")
        if not isinstance(payload, dict) or not sig:
            return ""
        payload_txt = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
        exp_sig = hmac.new(_auth_secret_value().encode("utf-8"), payload_txt.encode("utf-8"), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(sig, exp_sig):
            return ""
        return str(payload.get("u") or "").strip().lower()
    except Exception:
        return ""

def _persist_login_query(usuario: str):
    tok = _build_login_token(usuario)
    if tok:
        _qp_set(AUTH_QUERY_KEY, tok)

def _clear_persisted_login_query():
    _qp_set(AUTH_QUERY_KEY, "")

def _try_restore_login_from_query() -> bool:
    if st.session_state.get("logado"):
        return True
    tok = _qp_get(AUTH_QUERY_KEY)
    if not tok:
        return False
    u_norm = _read_login_token_usuario(tok)
    if not u_norm:
        _clear_persisted_login_query()
        return False
    user = next((x for x in users if (x.get("usuario") or "").strip().lower() == u_norm), None)
    if not user:
        _clear_persisted_login_query()
        return False
    ok, reason, _venc = _check_user_access(user)
    if (not ok) and reason in ("pending", "blocked"):
        try:
            if mp_try_auto_activate_user(user):
                ok, reason, _venc = _check_user_access(user)
        except Exception:
            pass
    if not ok:
        _clear_persisted_login_query()
        return False
    st.session_state["logado"] = True
    st.session_state["usuario"] = u_norm
    st.session_state["tipo"] = user.get("tipo", "user")
    st.session_state["login_blocked_user"] = ""
    st.session_state["login_blocked_reason"] = ""
    st.session_state["login_blocked_venc"] = ""
    st.session_state["login_verified_user"] = ""
    st.session_state["login_verified_tipo"] = ""
    st.session_state["login_verified_at"] = 0.0
    return True

def _handle_mp_return():
    mp_status = (_qp_get("mp") or "").strip().lower()
    ext_ref = (_qp_get("ext_ref") or "").strip()
    if not mp_status:
        return
    user = _user_from_external_reference(ext_ref)
    if mp_status == "success" and user:
        try:
            if mp_try_auto_activate_user(user):
                st.success("Pagamento confirmado! Seu acesso premium foi liberado.")
                mp_id = str(user.get("mp_last_payment_id") or "").strip()
                if mp_id:
                    st.session_state["mp_webhook_notice_seen"] = mp_id
            else:
                st.info("Pagamento em processamento. Clique em 'Já paguei - verificar' para atualizar.")
        except Exception:
            st.info("Pagamento em processamento. Clique em 'Já paguei - verificar' para atualizar.")
    elif mp_status == "pending":
        st.info("Pagamento pendente. Assim que confirmar, o acesso premium será liberado.")
    elif mp_status == "failure":
        st.error("Pagamento não concluído. Tente novamente.")
    _qp_set("mp", "")
    _qp_set("ext_ref", "")

def _latest_webhook_payment_for_user(user: dict):
    if not user:
        return None
    u_norm = (user.get("usuario") or "").strip().lower()
    if not u_norm:
        return None
    for p in reversed(payments):
        if not isinstance(p, dict):
            continue
        if (p.get("dono") or "").strip().lower() != u_norm:
            continue
        if (p.get("source") or "").strip().lower() != "webhook":
            continue
        return p
    return None

def _maybe_show_webhook_payment_notice():
    if not st.session_state.get("logado"):
        return
    user = _current_user_obj()
    if not user or (user.get("tipo") or "").strip().lower() == "admin":
        return
    payment = _latest_webhook_payment_for_user(user)
    if not payment:
        return
    mp_id = str(payment.get("mp_id") or payment.get("id") or "").strip()
    if not mp_id:
        return
    if st.session_state.get("mp_webhook_notice_seen") == mp_id:
        return
    if _is_premium_user(user):
        st.success("Pagamento confirmado via webhook. Seu acesso premium foi liberado.")
    else:
        st.info("Pagamento confirmado via webhook. Seu acesso será liberado em instantes.")
    st.session_state["mp_webhook_notice_seen"] = mp_id

def _maybe_auto_sync_premium():
    if not st.session_state.get("logado"):
        return
    user = _current_user_obj()
    if not user:
        return
    user_type = (user.get("tipo") or "").strip().lower()
    if user_type in {"admin", "patient"}:
        return
    if _is_premium_user(user):
        return
    if not _mp_access_token():
        return
    now_ts = float(time.time())
    last_ts = float(st.session_state.get("mp_auto_sync_at") or 0.0)
    if (now_ts - last_ts) < 60:
        return
    st.session_state["mp_auto_sync_at"] = now_ts
    try:
        if mp_try_auto_activate_user(user):
            st.success("Pagamento confirmado! Seu acesso premium foi liberado.")
            mp_id = str(user.get("mp_last_payment_id") or "").strip()
            if mp_id:
                st.session_state["mp_webhook_notice_seen"] = mp_id
    except Exception:
        pass

SIDEBAR_MENU_QUERY_KEY = "dh_menu"
SIMPLE_MODE_SESSION_KEY = "dh_simple_mode"
EXPERIENCE_SESSION_KEY = "dh_experience_mode"
VIRTUAL_MENU_SESSION_KEY = "dh_virtual_menu"
SIDEBAR_MENU_ITEMS = [
    {"key": "dashboard", "label": "Dashboard", "icon": "dashboard.png", "route": "dashboard"},
    {"key": "agenda", "label": "Agenda", "icon": "agenda.png", "route": "agenda"},
    {"key": "atendimento", "label": "Atendimento", "icon": "consultorio.png", "route": "atendimento"},
    {"key": "consultorio", "label": "Consultorio", "icon": "consultorio.png", "route": "consultorio"},
    {"key": "gerar_dieta", "label": "Gerar Dieta", "icon": "gerar_dieta.png", "route": "dieta"},
    {"key": "receitas_nutricionais", "label": "Receituário Nutricional", "icon": "receitas_nutricionais.png", "route": "receituario"},
    {"key": "pedidos_exames", "label": "Pedidos Exames", "icon": "pedidos_exames.png", "route": "pedidos_exames"},
    {"key": "atestado", "label": "Atestado", "icon": "atestado.png", "route": "atestado"},
    {"key": "relatorios", "label": "Relatorios", "icon": "relatorios.png", "route": "relatorios"},
    {"key": "consulta_alimentos_ia", "label": "Consulta Alimentos IA", "icon": "consulta_alimentos_ia.png", "route": "consulta_ia"},
    {"key": "graficos", "label": "Graficos", "icon": "graficos.png", "route": "graficos"},
    {"key": "financeiro", "label": "Financeiro", "icon": "financeiro.png", "route": "financeiro"},
    {"key": "biblioteca", "label": "Biblioteca", "icon": "biblioteca.png", "route": "biblioteca"},
    {"key": "chat", "label": "Chat", "icon": "chat.png", "route": "chat"},
    {"key": "suporte", "label": "Suporte", "icon": "suporte.png", "route": "suporte"},
    {"key": "painel_usuario", "label": "WhatsApp API", "icon": "painel_usuario.png", "route": "painel_usuario"},
]
PATIENT_SIDEBAR_MENU_ITEMS = [
    {"key": "portal_dashboard", "label": "Meu Painel", "icon": "dashboard.png", "route": "portal_dashboard"},
    {"key": "portal_consultas", "label": "Minhas Consultas", "icon": "agenda.png", "route": "portal_consultas"},
    {"key": "portal_dietas", "label": "Minhas Dietas", "icon": "gerar_dieta.png", "route": "portal_dietas"},
    {"key": "portal_receitas", "label": "Receitas", "icon": "receitas_nutricionais.png", "route": "portal_receitas"},
    {"key": "portal_exames", "label": "Exames", "icon": "pedidos_exames.png", "route": "portal_exames"},
    {"key": "portal_evolucao", "label": "Evolução", "icon": "graficos.png", "route": "portal_evolucao"},
    {"key": "portal_alimentos", "label": "Consulta Alimentos", "icon": "consulta_alimentos_ia.png", "route": "portal_alimentos"},
    {"key": "portal_chat", "label": "Chat", "icon": "chat.png", "route": "portal_chat"},
    {"key": "portal_online", "label": "Consulta Online", "icon": "relatorios.png", "route": "portal_online"},
    {"key": "portal_avisos", "label": "Avisos", "icon": "suporte.png", "route": "portal_avisos"},
    {"key": "portal_perfil", "label": "Meu Perfil", "icon": "painel_usuario.png", "route": "portal_perfil"},
]
_ICON_DATA_URL_CACHE = {}
_ICON_SRC_CACHE = {}
_STATIC_ICON_SYNC_DONE = False
SIMPLE_MODE_PRIMARY_MENU_KEYS = {
    "dashboard",
    "agenda",
    "atendimento",
    "consultorio",
    "gerar_dieta",
    "portal_dashboard",
    "portal_consultas",
    "portal_dietas",
    "portal_perfil",
}
SIMPLE_MODE_OPTIONAL_MENU_KEYS = {
    "relatorios",
    "portal_online",
}
VIRTUAL_PANEL_MENU_ITEMS = [
    {"key": "camila_home", "label": "Camila"},
    {"key": "camila_atendimento", "label": "Atendimento Inicial"},
    {"key": "camila_dados", "label": "Meus Dados"},
    {"key": "camila_dieta", "label": "Minha Dieta"},
    {"key": "camila_orientacoes", "label": "Orientações"},
]


def _dh_simple_mode_enabled() -> bool:
    return bool(st.session_state.get(SIMPLE_MODE_SESSION_KEY, False))


def _dh_experience_mode() -> str:
    mode = (st.session_state.get(EXPERIENCE_SESSION_KEY) or "traditional").strip().lower()
    return mode if mode in {"traditional", "virtual"} else "traditional"


def _dh_simple_mode_menu_keys(role: str) -> set[str]:
    role_norm = (role or "").strip().lower()
    if role_norm == "patient":
        return set(SIMPLE_MODE_PRIMARY_MENU_KEYS)
    return set(SIMPLE_MODE_PRIMARY_MENU_KEYS | SIMPLE_MODE_OPTIONAL_MENU_KEYS)


def _sidebar_menu_items(role: str):
    role_norm = (role or "").strip().lower()
    if role_norm == "patient":
        items = list(PATIENT_SIDEBAR_MENU_ITEMS)
    else:
        items = list(SIDEBAR_MENU_ITEMS)
        if role_norm == "admin":
            items.append(
                {"key": "admin", "label": "Admin", "icon": "imagen_adm.png", "route": "admin"}
            )
    if _dh_simple_mode_enabled():
        allowed = _dh_simple_mode_menu_keys(role_norm)
        items = [item for item in items if (item.get("key") or "").strip().lower() in allowed]
    return items


def _dedupe_sidebar_menu_items(items):
    unique = []
    seen_keys = set()
    seen_icon_route = set()
    for item in items:
        key = str(item.get("key") or "").strip().lower()
        route = str(item.get("route") or "").strip().lower()
        icon = str(item.get("icon") or "").strip().lower()
        if not key:
            continue
        signature = (icon, route)
        if key in seen_keys or signature in seen_icon_route:
            continue
        seen_keys.add(key)
        seen_icon_route.add(signature)
        unique.append(item)
    return unique


def _project_base_dir() -> str:
    return os.path.dirname(os.path.abspath(__file__)) if "__file__" in globals() else os.getcwd()


def _icon_file_path(icon_name: str) -> str:
    base_dir = _project_base_dir()
    candidates = [
        os.path.join("assets", "layout_inicial", "Icones", icon_name),
        os.path.join(base_dir, "assets", "layout_inicial", "Icones", icon_name),
        os.path.join(base_dir, "..", "assets", "layout_inicial", "Icones", icon_name),
        os.path.join(os.getcwd(), "assets", "layout_inicial", "Icones", icon_name),
        os.path.join("assets", "menu", "_norm", icon_name),
        os.path.join(base_dir, "assets", "menu", "_norm", icon_name),
        os.path.join(base_dir, "..", "assets", "menu", "_norm", icon_name),
        os.path.join(os.getcwd(), "assets", "menu", "_norm", icon_name),
        os.path.join("assets", "menu", icon_name),
        os.path.join(base_dir, "assets", "menu", icon_name),
        os.path.join(base_dir, "..", "assets", "menu", icon_name),
        os.path.join(os.getcwd(), "assets", "menu", icon_name),
        os.path.join("assets", "icons", icon_name),
        os.path.join(base_dir, "assets", "icons", icon_name),
        os.path.join(base_dir, "..", "assets", "icons", icon_name),
        os.path.join(os.getcwd(), "assets", "icons", icon_name),
    ]
    return next((p for p in candidates if os.path.exists(p)), "")


def _icon_data_url(icon_name: str) -> str:
    path = _icon_file_path(icon_name)
    try:
        version = int(os.path.getmtime(path)) if path else 0
    except Exception:
        version = 0
    cache_key = f"{path}::{version}::thumb44" if path else f"missing::{icon_name}"
    cached = _ICON_DATA_URL_CACHE.get(cache_key)
    if cached is not None:
        return cached
    if not path:
        _ICON_DATA_URL_CACHE[cache_key] = ""
        return ""
    try:
        with open(path, "rb") as f:
            raw = f.read()
        mime = "image/png"

        # Reduz payload do sidebar: gera miniatura pequena para abrir mais rápido em mobile e desktop.
        if Image is not None:
            with Image.open(io.BytesIO(raw)) as img:
                img = img.convert("RGBA")
                img.thumbnail((44, 44), Image.Resampling.LANCZOS if hasattr(Image, "Resampling") else Image.LANCZOS)
                out = io.BytesIO()
                img.save(out, format="PNG", optimize=True)
                raw = out.getvalue()
        else:
            ext = os.path.splitext(path)[1].lower()
            if ext in (".jpg", ".jpeg"):
                mime = "image/jpeg"

        encoded = base64.b64encode(raw).decode("ascii")
        url = f"data:{mime};base64,{encoded}"
        _ICON_DATA_URL_CACHE[cache_key] = url
        return url
    except Exception:
        _ICON_DATA_URL_CACHE[cache_key] = ""
        return ""


def _static_serving_enabled() -> bool:
    try:
        return bool(st.get_option("server.enableStaticServing"))
    except Exception:
        return False


def _sync_static_menu_icons() -> str:
    global _STATIC_ICON_SYNC_DONE
    base_dir = _project_base_dir()
    static_dir = os.path.join(base_dir, "static", "icons")
    if _STATIC_ICON_SYNC_DONE and os.path.isdir(static_dir):
        return static_dir
    try:
        os.makedirs(static_dir, exist_ok=True)
    except Exception:
        return ""

    for item in SIDEBAR_MENU_ITEMS + PATIENT_SIDEBAR_MENU_ITEMS + [{"icon": "imagen_adm.png"}]:
        icon_name = str(item.get("icon") or "").strip()
        if not icon_name:
            continue
        src = _icon_file_path(icon_name)
        if not src:
            continue
        dst = os.path.join(static_dir, icon_name)
        try:
            src_size = os.path.getsize(src)
            src_mtime = int(os.path.getmtime(src))
            dst_exists = os.path.exists(dst)
            dst_size = os.path.getsize(dst) if dst_exists else -1
            dst_mtime = int(os.path.getmtime(dst)) if dst_exists else -1
            if (not dst_exists) or (src_size != dst_size) or (src_mtime != dst_mtime):
                shutil.copy2(src, dst)
        except Exception:
            try:
                shutil.copy2(src, dst)
            except Exception:
                continue

    _STATIC_ICON_SYNC_DONE = True
    return static_dir


def _icon_src(icon_name: str) -> str:
    path = _icon_file_path(icon_name)
    if not path:
        return ""
    try:
        version = int(os.path.getmtime(path))
    except Exception:
        version = 0
    cache_key = f"data::{path}::{version}"
    cached = _ICON_SRC_CACHE.get(cache_key)
    if cached is not None:
        return cached

    # Prefer data URL to avoid broken /static paths behind reverse proxies.
    url = _icon_data_url(icon_name)
    _ICON_SRC_CACHE[cache_key] = url
    return url


def _menu_icon_path(icon_name: str) -> str:
    icon = (icon_name or "").strip()
    if not icon:
        return ""
    base_dir = _project_base_dir()
    candidates = [
        os.path.join("assets", "layout_inicial", "Icones", icon),
        os.path.join(base_dir, "assets", "layout_inicial", "Icones", icon),
        os.path.join("assets", "menu", "_norm", icon),
        os.path.join(base_dir, "assets", "menu", "_norm", icon),
        os.path.join("assets", "menu", icon),
        os.path.join(base_dir, "assets", "menu", icon),
        os.path.join("assets", "icons", icon),
        os.path.join(base_dir, "assets", "icons", icon),
    ]
    return next((p for p in candidates if os.path.exists(p)), "")


def _sidebar_href(menu_key: str) -> str:
    params = {}
    auth_tok = _qp_get(AUTH_QUERY_KEY)
    if auth_tok:
        params[AUTH_QUERY_KEY] = auth_tok
    params[SIDEBAR_MENU_QUERY_KEY] = menu_key
    return f"?{urllib.parse.urlencode(params)}"


def _render_sidebar_icon_menu(role: str) -> str:
    items = _dedupe_sidebar_menu_items(_sidebar_menu_items(role))
    if not items:
        return "dashboard"

    if "dh_payment_prompt" not in st.session_state:
        st.session_state["dh_payment_prompt"] = False
    if "dh_payment_prompt_user" not in st.session_state:
        st.session_state["dh_payment_prompt_user"] = ""

    user_obj = _current_user_obj()
    is_free_user = _is_free_user(user_obj)
    locked_keys = set()
    if is_free_user:
        for item in items:
            k = (item.get("key") or "").strip().lower()
            if k and k not in FREE_ALLOWED_MENU_KEYS:
                locked_keys.add(k)

    key_to_route = {item["key"]: item["route"] for item in items}
    route_to_key = {item["route"]: item["key"] for item in items}
    if "receituario" in route_to_key:
        route_to_key.setdefault("recibo", route_to_key["receituario"])
        route_to_key.setdefault("receita", route_to_key["receituario"])
    default_key = "dashboard" if "dashboard" in key_to_route else next(iter(key_to_route), "")

    qp_selected = (_qp_get(SIDEBAR_MENU_QUERY_KEY) or "").strip().lower()
    state_selected = (st.session_state.get("dh_selected_menu") or "").strip().lower()
    qp_selected = route_to_key.get(qp_selected, qp_selected)
    state_selected = route_to_key.get(state_selected, state_selected)
    selected_key = (qp_selected or state_selected or default_key).strip().lower()
    if selected_key not in key_to_route:
        selected_key = default_key
    if selected_key in locked_keys:
        # Mantém seleção em área liberada quando usuário é free.
        allowed_keys = [k for k in key_to_route.keys() if k not in locked_keys]
        selected_key = allowed_keys[0] if allowed_keys else default_key
    st.session_state["dh_selected_menu"] = selected_key
    if qp_selected != selected_key:
        _qp_set(SIDEBAR_MENU_QUERY_KEY, selected_key)

    st.markdown(
        """
        <script>
        (function () {
          if (window.dhCloseSidebar) return;
          window.dhCloseSidebar = function () {
            try {
              const host = window.parent || window;
              const doc = host.document;
              const candidates = [
                'button[data-testid="stSidebarCollapseButton"]',
                'div[data-testid="stSidebarCollapseButton"] button',
                'button[data-testid="sidebarCollapseButton"]',
                'div[data-testid="sidebarCollapseButton"] button',
                'button[aria-label*="Close sidebar"]',
                'button[aria-label*="Fechar"]',
                'button[title*="Close sidebar"]',
                'button[title*="Fechar"]'
              ];
              for (const selector of candidates) {
                const node = doc.querySelector(selector);
                if (node) {
                  try { node.click(); } catch (e) {}
                  break;
                }
              }
            } catch (e) {}
            return true;
          };
          window.dhOpenSidebar = function () {
            try {
              const host = window.parent || window;
              const doc = host.document;
              const candidates = [
                'button[data-testid="stSidebarCollapseButton"]',
                'div[data-testid="stSidebarCollapseButton"] button',
                'button[data-testid="sidebarCollapseButton"]',
                'div[data-testid="sidebarCollapseButton"] button',
                'button[aria-label*="Open sidebar"]',
                'button[aria-label*="Abrir"]',
                'button[title*="Open sidebar"]',
                'button[title*="Abrir"]'
              ];
              for (const selector of candidates) {
                const node = doc.querySelector(selector);
                if (node) {
                  try { node.click(); } catch (e) {}
                  break;
                }
              }
            } catch (e) {}
            return true;
          };
          window.dhNavigateMenu = function (url) {
            try {
              if (window.dhCloseSidebar) {
                window.dhCloseSidebar();
              }
            } catch (e) {}
            window.setTimeout(function () {
              try {
                const host = window.parent || window;
                host.location.assign(url);
              } catch (e) {
                window.location.assign(url);
              }
            }, 80);
            return false;
          };
        })();
        </script>
        """,
        unsafe_allow_html=True,
    )

    if st.session_state.get("dh_payment_prompt") and user_obj:
        u_norm = (user_obj.get("usuario") or "").strip().lower()
        prompt_user = (st.session_state.get("dh_payment_prompt_user") or "").strip().lower()
        if prompt_user and prompt_user != u_norm:
            st.session_state["dh_payment_prompt"] = False
            st.session_state["dh_payment_prompt_user"] = ""
        else:
            st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
            st.markdown("**Pagamento Premium**")
            st.markdown(
                """
                <style>
                .dh-premium-callout{
                  padding: 12px 14px;
                  border-radius: 14px;
                  border: 1px solid rgba(120, 245, 189, 0.28);
                  background: linear-gradient(135deg, rgba(9, 38, 40, 0.92), rgba(7, 20, 32, 0.92));
                  box-shadow: 0 12px 24px rgba(0,0,0,0.24);
                  display: grid;
                  gap: 6px;
                  font-family: "Poppins", "Montserrat", "Segoe UI", sans-serif;
                  color: #E9FFF5;
                }
                .dh-premium-callout-tag{
                  display: inline-flex;
                  align-items: center;
                  width: fit-content;
                  padding: 4px 10px;
                  border-radius: 999px;
                  background: rgba(120, 245, 189, 0.18);
                  color: #8CFFD0;
                  font-size: 0.7rem;
                  font-weight: 700;
                  text-transform: uppercase;
                  letter-spacing: 0.06em;
                }
                .dh-premium-callout-title{
                  font-size: 0.95rem;
                  font-weight: 700;
                  color: #F4FFFA;
                }
                .dh-premium-callout-note{
                  font-size: 0.88rem;
                  color: rgba(215, 243, 232, 0.9);
                }
                </style>
                """,
                unsafe_allow_html=True,
            )
            st.markdown(
                """
                <div class="dh-premium-callout">
                  <div class="dh-premium-callout-tag">Acesso Premium</div>
                  <div class="dh-premium-callout-title">Este recurso é exclusivo do plano Premium.</div>
                  <div class="dh-premium-callout-note">Para liberar o acesso, gere o link e clique em <strong>PAGAR AGORA</strong>.</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
            if _mp_access_token():
                url = ""
                if st.button("Gerar link de pagamento", key="mp_gen_link_sidebar_prompt", use_container_width=True):
                    url = mp_get_cached_checkout_url(user_obj, force_new=True)
                if not url and st.session_state.get("mp_checkout_user") == u_norm:
                    url = (st.session_state.get("mp_checkout_url") or "").strip()
                if url:
                    st.link_button("PAGAR AGORA (Pix/Cartão)", url, use_container_width=True)
                else:
                    err = (st.session_state.get("mp_checkout_last_err") or "").strip()
                    if err:
                        st.error(err)
                    st.caption("Após gerar o link, clique em PAGAR AGORA (Pix/Cartão).")
            else:
                st.caption("Configure MERCADO_PAGO_ACCESS_TOKEN para liberar pagamento.")
            if st.button("Fechar", key="mp_close_sidebar_prompt", use_container_width=True):
                st.session_state["dh_payment_prompt"] = False
                st.session_state["dh_payment_prompt_user"] = ""
                st.rerun()
            st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

    for item in items:
        key = item["key"]
        label = item["label"]
        if key in ("receitas_nutricionais", "receituario", "recibo", "receita") or item.get("route") in ("receituario", "recibo", "receita"):
            label = "Receituário Nutricional"
        locked = key in locked_keys
        if locked:
            label = f"🔒 {label}"
        btn_type = "primary" if key == selected_key else "secondary"
        if st.button(label, key=f"dh_menu_btn_{key}", use_container_width=True, help=label, type=btn_type):
            if locked:
                st.warning("Este recurso é Premium. Para liberar, faça upgrade para Premium e clique em Gerar link de pagamento.")
                if user_obj:
                    st.session_state["dh_payment_prompt"] = True
                    st.session_state["dh_payment_prompt_user"] = (user_obj.get("usuario") or "").strip().lower()
                st.rerun()
            st.session_state["dh_selected_menu"] = key
            st.session_state["dh_close_sidebar_after_nav"] = True
            _qp_set(SIDEBAR_MENU_QUERY_KEY, key)
            st.rerun()
    return key_to_route.get(selected_key, "dashboard")


def _menu_key_from_route(route: str) -> str:
    route = (route or "").strip().lower()
    if not route:
        return ""
    if route in ("recibo", "receita"):
        return "receitas_nutricionais"
    for item in SIDEBAR_MENU_ITEMS:
        if (item.get("route") or "").strip().lower() == route:
            return (item.get("key") or "").strip().lower()
    return route

def _wa_sanitize_numero(num):
    if num is None:
        return ""
    return "".join(ch for ch in str(num) if ch.isdigit())

def _wa_normalize_to_send(num):
    digits = _wa_sanitize_numero(num)
    if not digits:
        return ""
    # Convenção padrão do app (Brasil): se vier apenas DDD+numero, prefixa 55.
    if not digits.startswith("55") and len(digits) in (10, 11):
        return f"55{digits}"
    return digits

def _wa_link(num, texto):
    numero = _wa_normalize_to_send(num)
    if not numero:
        return ""
    msg = texto or ""
    return f"https://wa.me/{numero}?text={urllib.parse.quote(msg)}"

def _patient_portal_public_url() -> str:
    raw = (
        _get_config_value("DIETHEALTH_PORTAL_URL", "")
        or _get_config_value("PUBLIC_APP_URL", "")
        or _get_config_value("SITE_URL", "")
        or "https://diethealthsystem.com"
    )
    raw = (raw or "").strip()
    if not raw:
        return "https://diethealthsystem.com"
    if not re.match(r"^https?://", raw, flags=re.IGNORECASE):
        raw = f"https://{raw}"
    return raw.rstrip("/")

def _patient_portal_status_ui(status: str) -> tuple[str, str, str]:
    status_norm = (status or "nao_ativado").strip().lower()
    mapping = {
        "ativo": ("Ativo", "dh-status-active", "Paciente já validou o primeiro acesso e pode entrar com CPF e senha."),
        "pendente": ("Pendente", "dh-status-pending", "Cadastro localizado, mas o fluxo do portal ainda não foi concluído."),
        "bloqueado": ("Bloqueado", "dh-status-blocked", "A conta existe, mas está bloqueada e precisa ser liberada."),
        "nao_ativado": ("Não ativado", "dh-status-inactive", "O paciente ainda precisa validar CPF + código e criar a senha."),
    }
    return mapping.get(status_norm, ("Pendente", "dh-status-pending", "Acompanhe este acesso antes de orientar o paciente."))

def _build_patient_portal_message(p_obj: dict) -> str:
    patient = p_obj or {}
    nome = (patient.get("nome") or "Paciente").strip()
    cpf = _patient_record_cpf(patient) or "-"
    codigo = (patient.get("codigo_paciente") or "").strip().upper() or "-"
    portal_url = _patient_portal_public_url()
    return (
        f"Olá, {nome}.\n\n"
        "Seu acesso ao Portal do Paciente do DietHealth foi liberado.\n\n"
        "Para seu primeiro acesso, utilize:\n"
        f"CPF: {cpf}\n"
        f"Código do paciente: {codigo}\n\n"
        "Depois da validação, você poderá criar sua senha e acessar normalmente o portal com CPF + senha.\n\n"
        f"Link de acesso: {portal_url}\n\n"
        "Se tiver dúvidas, entre em contato com sua nutricionista."
    )

def _build_patient_portal_instruction_block(p_obj: dict) -> str:
    patient = p_obj or {}
    nome = (patient.get("nome") or "Paciente").strip()
    cpf = _patient_record_cpf(patient) or "-"
    codigo = (patient.get("codigo_paciente") or "").strip().upper() or "-"
    status_label, _, status_note = _patient_portal_status_ui(patient.get("status_acesso_portal"))
    portal_url = _patient_portal_public_url()
    return (
        f"Paciente: {nome}\n"
        f"Status do acesso: {status_label}\n"
        f"CPF vinculado: {cpf}\n"
        f"Código do paciente: {codigo}\n"
        f"Link do portal: {portal_url}\n\n"
        "Fluxo do primeiro acesso:\n"
        "1. Entrar no portal com CPF + código do paciente.\n"
        "2. Validar os dados e criar a senha.\n"
        "3. A partir do próximo acesso, usar CPF + senha.\n\n"
        f"Observação operacional: {status_note}"
    )

def _render_clipboard_button(label: str, text: str, key_suffix: str, tone: str = "soft"):
    payload = json.dumps(text or "", ensure_ascii=False)
    btn_id = f"dh-copy-{re.sub(r'[^a-zA-Z0-9_-]+', '-', str(key_suffix))}-{uuid.uuid4().hex[:8]}"
    palette = {
        "soft": ("linear-gradient(135deg, #f8fafc, #dbeafe)", "#0f172a", "rgba(148,163,184,0.38)"),
        "accent": ("linear-gradient(135deg, #22c55e, #16a34a)", "#f8fffb", "rgba(22,163,74,0.45)"),
        "dark": ("linear-gradient(135deg, #0f172a, #1e293b)", "#f8fafc", "rgba(100,116,139,0.44)"),
    }
    bg, fg, border = palette.get(tone, palette["soft"])
    components.html(
        f"""
        <div style="width:100%;padding:0;margin:0;">
          <button id="{btn_id}" type="button" style="
            width:100%;
            min-height:46px;
            border-radius:14px;
            border:1px solid {border};
            background:{bg};
            color:{fg};
            font-weight:800;
            font-size:14px;
            padding:10px 14px;
            cursor:pointer;
            box-shadow:0 12px 24px rgba(15,23,42,0.12);
          ">{html.escape(label)}</button>
          <div id="{btn_id}-msg" style="margin-top:6px;font-size:12px;color:#64748b;text-align:center;"></div>
        </div>
        <script>
        const btn = document.getElementById({json.dumps(btn_id)});
        const msg = document.getElementById({json.dumps(btn_id + "-msg")});
        btn.addEventListener("click", async () => {{
          try {{
            await navigator.clipboard.writeText({payload});
            msg.innerText = "Copiado com sucesso";
          }} catch (err) {{
            msg.innerText = "Não foi possível copiar automaticamente";
          }}
        }});
        </script>
        """,
        height=72,
    )

def _is_valid_email(email: str) -> bool:
    txt = (email or "").strip()
    if not txt or len(txt) > 254:
        return False
    return re.match(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$", txt) is not None

def _is_valid_celular(num: str) -> bool:
    digits = _wa_sanitize_numero(num)
    if not digits:
        return False
    if digits.startswith("55"):
        return len(digits) in (12, 13)
    return len(digits) in (10, 11)

def _normalize_cpf(cpf: str) -> str:
    return re.sub(r"\D+", "", cpf or "")

def _is_valid_cpf(cpf: str) -> bool:
    digits = _normalize_cpf(cpf)
    if len(digits) != 11 or digits == digits[0] * 11:
        return False
    total = sum(int(digits[i]) * (10 - i) for i in range(9))
    dv1 = (total * 10 % 11) % 10
    total = sum(int(digits[i]) * (11 - i) for i in range(10))
    dv2 = (total * 10 % 11) % 10
    return digits[-2:] == f"{dv1}{dv2}"

def _cpf_already_exists(cpf: str, ignore_user: str = "") -> bool:
    digits = _normalize_cpf(cpf)
    ignore_norm = (ignore_user or "").strip().lower()
    if not digits:
        return False
    for user in users:
        if (user.get("usuario") or "").strip().lower() == ignore_norm:
            continue
        if _normalize_cpf(user.get("cpf")) == digits:
            return True
    return False

def _portal_user_by_cpf(cpf: str, ignore_user: str = ""):
    cpf_norm = _normalize_cpf(cpf)
    ignore_norm = (ignore_user or "").strip().lower()
    if not cpf_norm:
        return None
    for user in users:
        if (user.get("usuario") or "").strip().lower() == ignore_norm:
            continue
        if (user.get("tipo") or "").strip().lower() != "patient":
            continue
        if _normalize_cpf(user.get("cpf")) == cpf_norm:
            return user
    return None

def _generate_patient_portal_code() -> str:
    existing = {
        str((item.get("codigo_paciente") or "")).strip().upper()
        for item in pacientes
        if isinstance(item, dict)
    }
    while True:
        code = f"DH{uuid.uuid4().hex[:8].upper()}"
        if code not in existing:
            return code

def _derive_patient_portal_status(portal_user: dict = None) -> str:
    if not isinstance(portal_user, dict):
        return "nao_ativado"
    status = (portal_user.get("status") or "").strip().lower()
    if status == "active":
        return "ativo"
    if status == "blocked":
        return "bloqueado"
    if status:
        return "pendente"
    return "nao_ativado"

def _ensure_patient_portal_access_fields(p_obj: dict, persist: bool = False):
    if not isinstance(p_obj, dict):
        return None
    changed = False
    if not (p_obj.get("codigo_paciente") or "").strip():
        p_obj["codigo_paciente"] = _generate_patient_portal_code()
        changed = True
    portal_user = _portal_user_by_cpf(_patient_record_cpf(p_obj))
    desired_status = _derive_patient_portal_status(portal_user)
    if (p_obj.get("status_acesso_portal") or "").strip().lower() != desired_status:
        p_obj["status_acesso_portal"] = desired_status
        changed = True
    if persist and changed:
        save_db("pacientes.json", pacientes)
    return p_obj

def _find_patient_by_portal_code(cpf: str, codigo: str):
    cpf_norm = _normalize_cpf(cpf)
    code_norm = (codigo or "").strip().upper()
    if not cpf_norm or not code_norm:
        return None
    matches = _find_patient_matches_by_cpf(cpf_norm)
    for item in matches:
        _ensure_patient_portal_access_fields(item)
        if (item.get("codigo_paciente") or "").strip().upper() == code_norm:
            return item
    return None

def _patient_login_lookup(identifier: str, password: str):
    ident_norm = (identifier or "").strip().lower()
    cpf_norm = _normalize_cpf(identifier)
    if not (ident_norm or cpf_norm) or not password:
        return None
    for user in users:
        if (user.get("tipo") or "").strip().lower() != "patient":
            continue
        if user.get("senha") != password:
            continue
        if cpf_norm and _normalize_cpf(user.get("cpf")) == cpf_norm:
            return user
        if (user.get("usuario") or "").strip().lower() == ident_norm:
            return user
    return None

def _activate_patient_portal_access(cpf: str, codigo: str, senha: str, senha_confirm: str, email: str = "", telefone: str = ""):
    cpf_norm = _normalize_cpf(cpf)
    if not cpf_norm:
        return False, "Informe o CPF do paciente."
    if not _is_valid_cpf(cpf_norm):
        return False, "Informe um CPF válido."
    if not (codigo or "").strip():
        return False, "Informe o código do paciente."
    if not senha:
        return False, "Informe uma senha."
    if senha != senha_confirm:
        return False, "As senhas não conferem."
    linked = _find_patient_by_portal_code(cpf_norm, codigo)
    if not linked:
        conflict = _find_patient_matches_by_cpf(cpf_norm)
        if len(conflict) > 1:
            return False, "Este CPF aparece em mais de uma base. O ADMIN precisa revisar o vínculo antes de liberar o portal."
        if conflict:
            return False, "Código do paciente inválido."
        return False, "CPF não encontrado na base clínica. Seu acesso precisa ser validado pelo ADMIN ou pela nutricionista."
    existing_user = _portal_user_by_cpf(cpf_norm)
    if existing_user:
        status_now = (existing_user.get("status") or "").strip().lower()
        if status_now == "active":
            return False, "Seu acesso ao Portal do Paciente já está ativo. Use o login ou a recuperação de senha."
        existing_user["senha"] = senha
        existing_user["status"] = "active"
        existing_user["usuario"] = _normalize_cpf(cpf_norm)
        existing_user["nome"] = existing_user.get("nome") or linked.get("nome") or "Paciente"
        existing_user["cpf"] = cpf_norm
        existing_user["linked_cpf"] = cpf_norm
        existing_user["linked_owner"] = (linked.get("dono") or "").strip().lower()
        existing_user["linked_patient_name"] = linked.get("nome") or ""
        if (email or "").strip():
            existing_user["email"] = (email or "").strip()
        elif linked.get("email"):
            existing_user["email"] = linked.get("email")
        if (telefone or "").strip():
            existing_user["telefone"] = (telefone or "").strip()
        elif linked.get("telefone"):
            existing_user["telefone"] = linked.get("telefone")
    else:
        users.append({
            "signup_id": _new_signup_id(),
            "nome": linked.get("nome") or "Paciente",
            "cpf": cpf_norm,
            "usuario": cpf_norm,
            "senha": senha,
            "tipo": "patient",
            "status": "active",
            "paid_until": "",
            "wa_provider": "wapi",
            "wa_token": "",
            "wa_phone_id": "",
            "wa_api_url": "",
            "wa_instance": "",
            "wa_notify_admin_num": "",
            "email": (email or linked.get("email") or "").strip(),
            "telefone": (telefone or linked.get("telefone") or "").strip(),
            "created_at": str(datetime.now().date()),
            "linked_cpf": cpf_norm,
            "linked_owner": (linked.get("dono") or "").strip().lower(),
            "linked_patient_name": linked.get("nome") or "",
        })
    linked["status_acesso_portal"] = "ativo"
    save_db("users.json", users)
    save_db("pacientes.json", pacientes)
    return True, "Acesso do paciente ativado com sucesso. Agora use CPF e senha para entrar no portal."

def _reset_patient_portal_password(cpf: str, codigo: str, senha: str, senha_confirm: str):
    cpf_norm = _normalize_cpf(cpf)
    portal_user = _portal_user_by_cpf(cpf_norm)
    if not portal_user:
        return False, "Este CPF ainda não possui acesso ativo ao portal."
    linked = _find_patient_by_portal_code(cpf_norm, codigo)
    if not linked:
        return False, "Código do paciente inválido."
    if not senha:
        return False, "Informe uma nova senha."
    if senha != senha_confirm:
        return False, "As senhas não conferem."
    portal_user["senha"] = senha
    if (portal_user.get("status") or "").strip().lower() != "active":
        portal_user["status"] = "active"
    linked["status_acesso_portal"] = "ativo"
    save_db("users.json", users)
    save_db("pacientes.json", pacientes)
    return True, "Senha redefinida com sucesso. Agora entre com CPF e senha."

def _parse_dt_any(value):
    txt = (str(value) if value is not None else "").strip()
    if not txt:
        return None
    try:
        iso_txt = txt[:-1] + "+00:00" if txt.endswith("Z") else txt
        dt = datetime.fromisoformat(iso_txt)
        if dt.tzinfo is not None:
            dt = dt.astimezone().replace(tzinfo=None)
        return dt
    except Exception:
        pass
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%d/%m/%Y %H:%M:%S", "%d/%m/%Y %H:%M"):
        try:
            return datetime.strptime(txt, fmt)
        except Exception:
            continue
    return None

def _is_user_online(user_obj: dict, now_dt=None) -> bool:
    if not isinstance(user_obj, dict):
        return False
    last_seen = _parse_dt_any(user_obj.get("last_seen_at"))
    if not last_seen:
        return False
    now_dt = now_dt or datetime.now()
    delta = (now_dt - last_seen).total_seconds()
    return 0 <= delta <= int(ONLINE_TIMEOUT_SECONDS)

def _fmt_last_seen_value(value) -> str:
    dt = _parse_dt_any(value)
    if not dt:
        return ""
    return dt.strftime("%d/%m/%Y %H:%M:%S")

def _touch_user_presence(force: bool = False):
    if not st.session_state.get("logado"):
        return
    u_norm = (st.session_state.get("usuario") or "").strip().lower()
    if not u_norm:
        return
    now_ts = float(time.time())
    last_write = float(st.session_state.get("presence_last_write_ts") or 0.0)
    if (not force) and last_write and (now_ts - last_write) < float(ONLINE_HEARTBEAT_SECONDS):
        return
    user_obj = next((x for x in users if (x.get("usuario") or "").strip().lower() == u_norm), None)
    if not user_obj:
        return
    user_obj["last_seen_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    _save_users_presence_fast()
    st.session_state["presence_last_write_ts"] = now_ts

def _mark_user_offline(usuario: str = ""):
    u_norm = (usuario or st.session_state.get("usuario") or "").strip().lower()
    if not u_norm:
        return
    user_obj = next((x for x in users if (x.get("usuario") or "").strip().lower() == u_norm), None)
    if not user_obj:
        return
    if (user_obj.get("last_seen_at") or "").strip():
        user_obj["last_seen_at"] = ""
        save_db("users.json", users)
    st.session_state["presence_last_write_ts"] = 0.0

def _secret_or_env(*keys: str) -> str:
    for key in keys:
        val = (os.getenv(key) or "").strip()
        if val:
            return val
        try:
            val = str(st.secrets.get(key, "")).strip()
        except Exception:
            val = ""
        if val:
            return val
    return ""

def _now_local():
    tz_name = (_secret_or_env("DIETHEALTH_TZ", "APP_TIMEZONE", "TZ") or "America/Sao_Paulo").strip()
    if ZoneInfo is not None:
        try:
            return datetime.now(ZoneInfo(tz_name))
        except Exception:
            try:
                return datetime.now(ZoneInfo("America/Sao_Paulo"))
            except Exception:
                pass
    # Fallback: horario de Brasil (UTC-3) quando zoneinfo nao estiver disponivel.
    return datetime.utcnow() - timedelta(hours=3)

def _new_signup_id() -> str:
    stamp = _now_local().strftime("%Y%m%d%H%M%S")
    suffix = uuid.uuid4().hex[:6].upper()
    return f"CAD-{stamp}-{suffix}"

def _resolve_admin_whatsapp_num(admin_obj: dict):
    raw = (
        (admin_obj.get("wa_notify_admin_num") if admin_obj else "")
        or (admin_obj.get("telefone") if admin_obj else "")
        or _secret_or_env("ADMIN_WHATSAPP_NUMERO", "WA_ADMIN_NUMERO")
        or WHATSAPP_NUMERO
    )
    num = _wa_normalize_to_send(raw)
    return num

def _wa_send_cloud_text(token: str, phone_id: str, to_number: str, message: str):
    token = (token or "").strip()
    phone_id = (phone_id or "").strip()
    phone_id_digits = _wa_sanitize_numero(phone_id)
    to_num = _wa_normalize_to_send(to_number)
    msg = (message or "").strip()
    if not token or not phone_id:
        return False, "API WhatsApp não configurada (token/phone_id)."
    if not phone_id_digits:
        return False, "Phone Number ID inválido."
    if not to_num:
        return False, "Número de destino inválido para WhatsApp."
    if not msg:
        return False, "Mensagem vazia para envio no WhatsApp."
    payload = {
        "messaging_product": "whatsapp",
        "to": to_num,
        "type": "text",
        "text": {"preview_url": False, "body": msg[:4096]},
    }
    version = (WA_GRAPH_VERSION or "v21.0").strip()
    url = f"https://graph.facebook.com/{version}/{phone_id}/messages"
    status, data = _http_json("POST", url, token=token, payload=payload, timeout=20)
    if status in (200, 201):
        return True, ""
    err_msg = f"falha no envio (status {status})"
    if isinstance(data, dict):
        err_data = data.get("error")
        if isinstance(err_data, dict):
            base = (
                (err_data.get("error_user_msg") or "").strip()
                or (err_data.get("message") or "").strip()
                or err_msg
            )
            code = err_data.get("code")
            subcode = err_data.get("error_subcode")
            code_txt = ""
            if code is not None:
                code_txt = f" | code={code}"
                if subcode is not None:
                    code_txt += f" subcode={subcode}"
            err_msg = f"{base}{code_txt}"
        elif err_data:
            err_msg = str(err_data)
    if len(phone_id_digits) <= 13:
        err_msg = f"{err_msg} | possível Phone Number ID incorreto (parece número de telefone)"
    return False, err_msg

def _wa_split_url(raw_url: str):
    raw = (raw_url or "").strip()
    if not raw:
        return urllib.parse.SplitResult("", "", "", "", "")
    if not re.match(r"^https?://", raw, flags=re.IGNORECASE):
        raw = f"https://{raw}"
    return urllib.parse.urlsplit(raw)

def _wa_error_text(status: int, data) -> str:
    msg = f"falha no envio W-API (status {status})"
    if isinstance(data, dict):
        msg = (
            str(data.get("message") or "").strip()
            or str(data.get("error") or "").strip()
            or msg
        )
    elif data:
        msg = str(data)
    return msg

def _wa_collect_texts(obj):
    out = []
    if obj is None:
        return out
    if isinstance(obj, str):
        out.append(obj)
        return out
    if isinstance(obj, dict):
        for v in obj.values():
            out.extend(_wa_collect_texts(v))
        return out
    if isinstance(obj, (list, tuple, set)):
        for item in obj:
            out.extend(_wa_collect_texts(item))
        return out
    return out

def _wa_payload_error_reason(data):
    texts = [t for t in _wa_collect_texts(data) if isinstance(t, str) and t.strip()]
    if not texts:
        return ""
    keywords = [
        "not found", "não encontrada", "nao encontrada", "não encontrado", "nao encontrado",
        "invalid", "inválido", "invalido", "unauthorized", "forbidden", "denied",
        "erro", "error", "failed", "falha", "offline", "disconnected", "not connected",
        "instance", "instância", "instancia"
    ]
    for txt in texts:
        low = txt.lower()
        if any(k in low for k in keywords):
            return txt.strip()
    return ""

def _wa_find_first_value(obj, keys):
    if obj is None:
        return ""
    if isinstance(obj, dict):
        lower_map = {str(k).lower(): v for k, v in obj.items()}
        for key in keys:
            val = lower_map.get(str(key).lower())
            if val not in (None, ""):
                return str(val).strip()
        for val in obj.values():
            found = _wa_find_first_value(val, keys)
            if found:
                return found
        return ""
    if isinstance(obj, list):
        for item in obj:
            found = _wa_find_first_value(item, keys)
            if found:
                return found
    return ""

def _wa_message_reference(data):
    ref = _wa_find_first_value(
        data,
        ["messageId", "message_id", "insertedId", "id", "key.id"],
    )
    return (ref or "").strip()

def _wa_payload_has_send_ack(data):
    if isinstance(data, dict):
        for k in ("success", "sent", "delivered", "ack"):
            if data.get(k) is True:
                return True
        status_txt = str(data.get("status") or data.get("state") or "").strip().lower()
        if status_txt in {"ok", "success", "sent", "queued", "accepted", "processing"}:
            return True
        if (data.get("messageId") or data.get("message_id")) and not _wa_payload_error_reason(data):
            return True
        for k in ("data", "result", "response", "message"):
            if k in data and _wa_payload_has_send_ack(data.get(k)):
                return True
    elif isinstance(data, list):
        return any(_wa_payload_has_send_ack(x) for x in data)
    return False

def _wa_is_placeholder_instance(value: str) -> bool:
    txt = (value or "").strip().lower()
    if not txt:
        return False
    placeholders = {
        "instance_id",
        "instanceid",
        "instance-id",
        "your_instance_id",
        "your-instance-id",
        "seu_instance_id",
        "seu-instance-id",
    }
    return txt in placeholders

def _wa_build_wapi_endpoints(api_url: str, instance: str):
    parts = _wa_split_url(api_url)
    if not parts.netloc:
        return [], (instance or "").strip(), "URL da W-API inválida."

    inst = (instance or "").strip()
    if _wa_is_placeholder_instance(inst):
        inst = ""
    q = urllib.parse.parse_qs(parts.query or "", keep_blank_values=True)
    if not inst:
        inst_q = (q.get("instanceId", [""])[0] or q.get("instance", [""])[0] or "").strip()
        if not _wa_is_placeholder_instance(inst_q):
            inst = inst_q

    path_txt = (parts.path or "").lower()
    host = (parts.netloc or "").lower()
    endpoints = []

    # Caso usuário informe endpoint completo (ex: .../message/send-text?instanceId=...)
    if ("send-text" in path_txt) or ("sendtext" in path_txt):
        q2 = urllib.parse.parse_qs(parts.query or "", keep_blank_values=True)
        # Se a instância foi informada no campo separado, ela prevalece sempre.
        # Também substitui placeholders como INSTANCE_ID vindos da URL de exemplo.
        if inst:
            q2["instanceId"] = [inst]
        else:
            current_q_inst = (
                (q2.get("instanceId", [""])[0] or "")
                or (q2.get("instance", [""])[0] or "")
                or (q2.get("instanceName", [""])[0] or "")
                or (q2.get("instance_id", [""])[0] or "")
            ).strip()
            if _wa_is_placeholder_instance(current_q_inst):
                return [], inst, "Instância com ID real não configurada (URL está com placeholder INSTANCE_ID)."
            if not current_q_inst and not inst:
                return [], inst, "Instância da W-API não configurada."
        if "w-api.app" in host:
            # W-API usa query principal `instanceId`.
            q2 = {"instanceId": [inst]}
        else:
            if inst and not q2.get("instance"):
                q2["instance"] = [inst]
            if inst and not q2.get("instanceName"):
                q2["instanceName"] = [inst]
            if inst and not q2.get("instance_id"):
                q2["instance_id"] = [inst]
        url_direct = urllib.parse.urlunsplit(
            (parts.scheme, parts.netloc, parts.path, urllib.parse.urlencode(q2, doseq=True), "")
        )
        endpoints.append(url_direct)
        return list(dict.fromkeys(endpoints)), inst, ""

    base_path = (parts.path or "").rstrip("/")

    # Padrão W-API (w-api.app): /v1/message/send-text?instanceId=...
    if "w-api.app" in host:
        if not base_path:
            base_path = "/v1"
        q3 = {"instanceId": inst} if inst else {}
        url_wapi = urllib.parse.urlunsplit(
            (parts.scheme, parts.netloc, f"{base_path}/message/send-text", urllib.parse.urlencode(q3), "")
        )
        endpoints.append(url_wapi)

    # Padrão Evolution: /message/sendText/{instance}
    if inst:
        url_evo = urllib.parse.urlunsplit(
            (parts.scheme, parts.netloc, f"{base_path}/message/sendText/{urllib.parse.quote(inst)}", "", "")
        )
        endpoints.append(url_evo)

    if not endpoints:
        return [], inst, "Não foi possível montar endpoint da W-API. Verifique URL/instância."
    return list(dict.fromkeys(endpoints)), inst, ""

def _wa_wapi_device_url(api_url: str, instance: str):
    parts = _wa_split_url(api_url)
    if not parts.netloc:
        return "", ""
    inst = (instance or "").strip()
    if _wa_is_placeholder_instance(inst):
        inst = ""
    q = urllib.parse.parse_qs(parts.query or "", keep_blank_values=True)
    if not inst:
        inst = (q.get("instanceId", [""])[0] or q.get("instance", [""])[0] or "").strip()
    if _wa_is_placeholder_instance(inst):
        inst = ""
    if not inst:
        return "", ""

    path = (parts.path or "")
    path_low = path.lower()
    if "/message/" in path_low:
        idx = path_low.index("/message/")
        base_path = path[:idx]
    else:
        base_path = path
    base_path = (base_path or "").rstrip("/")
    if not base_path:
        base_path = "/v1"
    if not str(base_path).startswith("/"):
        base_path = f"/{base_path}"

    q_url = urllib.parse.urlencode({"instanceId": inst})
    url = urllib.parse.urlunsplit((parts.scheme, parts.netloc, f"{base_path}/instance/device", q_url, ""))
    return url, inst

def _wa_get_connected_number_wapi(api_url: str, instance: str, token: str):
    url, inst = _wa_wapi_device_url(api_url, instance)
    if not url:
        return None, "", ""
    api_key = (token or "").strip()
    if not api_key:
        return None, "", ""

    header_variants = [
        {"apikey": api_key},
        {"Authorization": f"Bearer {api_key}"},
        {"Authorization": api_key},
        {"token": api_key},
    ]

    errors = []
    for headers in header_variants:
        status, data = _http_json(
            "GET",
            url,
            timeout=20,
            headers_extra=headers,
        )
        if status in (200, 201):
            reason = _wa_payload_error_reason(data)
            if reason:
                errors.append(reason)
                continue
            connected = _wa_normalize_to_send(
                _wa_find_first_value(
                    data,
                    ["connectedPhone", "connected_phone", "phone", "number", "wid"],
                )
            )
            return True, connected, ""
        errors.append(_wa_error_text(status, data))

    if errors:
        return False, "", errors[-1]
    return None, "", ""

def _wa_send_wapi_text(api_url: str, instance: str, token: str, to_number: str, message: str):
    api_key = (token or "").strip()
    to_num = _wa_normalize_to_send(to_number)
    msg = (message or "").strip()
    endpoints, inst, err_ep = _wa_build_wapi_endpoints(api_url, instance)

    if not endpoints:
        return False, err_ep or "URL da W-API/Evolution não configurada."
    if not inst and all("/message/sendText/" in e for e in endpoints):
        return False, "Instância da W-API/Evolution não configurada."
    if not api_key:
        return False, "API Key/Token da W-API/Evolution não configurado."
    if not to_num:
        return False, "Número de destino inválido para WhatsApp."
    if not msg:
        return False, "Mensagem vazia para envio no WhatsApp."

    payload_variants = [
        {"number": to_num, "text": msg[:4096]},
        {"phone": to_num, "message": msg[:4096]},
        {"phone": to_num, "text": msg[:4096]},
    ]
    header_variants = [
        {"apikey": api_key},
        {"Authorization": f"Bearer {api_key}"},
        {"Authorization": api_key},
        {"token": api_key},
    ]

    same_as_connected = False
    connected_num = ""
    # Para W-API, checa número conectado da instância para evitar falso envio para o próprio remetente.
    try:
        if any("w-api.app" in urllib.parse.urlsplit(e).netloc.lower() for e in endpoints):
            state_ok, connected_num, state_err = _wa_get_connected_number_wapi(api_url, inst, api_key)
            if connected_num and connected_num == to_num:
                same_as_connected = True
    except Exception:
        pass

    errors = []
    for url in endpoints:
        for headers in header_variants:
            for payload in payload_variants:
                status, data = _http_json(
                    "POST",
                    url,
                    payload=payload,
                    timeout=20,
                    headers_extra=headers,
                )
                if status in (200, 201, 202):
                    reason = _wa_payload_error_reason(data)
                    if reason:
                        errors.append(reason)
                        continue
                    if _wa_payload_has_send_ack(data):
                        ref = _wa_message_reference(data)
                        if ref:
                            if same_as_connected:
                                return True, f"ref={ref}, aviso=destino_igual_instancia({connected_num})"
                            return True, f"ref={ref}"
                        if same_as_connected:
                            return True, f"ack=2xx, aviso=destino_igual_instancia({connected_num})"
                        return True, "ack=2xx"
                    errors.append("API respondeu 2xx sem confirmação explícita de envio.")
                    continue
                errors.append(_wa_error_text(status, data))

    msg_err = errors[-1] if errors else "falha no envio W-API."
    if same_as_connected:
        msg_err = (
            "destino igual ao número conectado na instância W-API; "
            "muitos provedores não entregam mensagem para o próprio número. "
            f"Detalhe da API: {msg_err}"
        )
    return False, msg_err

def _wa_send_text_for_user(user_obj, to_number: str, message: str):
    cfg = _get_user_whatsapp_settings(user_obj)
    provider = cfg.get("provider")
    if provider == "wapi":
        return _wa_send_wapi_text(
            cfg.get("api_url") or "",
            cfg.get("instance") or "",
            cfg.get("token") or "",
            to_number,
            message,
        )
    return _wa_send_cloud_text(
        cfg.get("token") or "",
        cfg.get("phone_id") or "",
        to_number,
        message,
    )

def _notify_admin_new_signup(new_user: dict):
    admin_obj = next((x for x in users if (x.get("tipo") or "").strip().lower() == "admin"), None)
    admin_num = _resolve_admin_whatsapp_num(admin_obj)
    if not admin_num:
        return False, "Número de WhatsApp do admin não configurado."
    nome = (new_user.get("nome") or "").strip() or "(sem nome)"
    usuario = (new_user.get("usuario") or "").strip().lower()
    email = (new_user.get("email") or "").strip()
    celular = (new_user.get("telefone") or "").strip()
    signup_id = (new_user.get("signup_id") or "").strip() or _new_signup_id()
    criado_em = _now_local().strftime("%d/%m/%Y %H:%M")
    texto = (
        "Novo cadastro no DietHealth.\n"
        f"ID cadastro: {signup_id}\n"
        f"Nome: {nome}\n"
        f"Usuario: {usuario}\n"
        f"Email: {email}\n"
        f"Celular: {celular}\n"
        f"Data/Hora: {criado_em}"
    )
    ok, detail = _wa_send_text_for_user(admin_obj, admin_num, texto)
    if ok:
        provider = (_get_user_whatsapp_settings(admin_obj).get("provider") or "wapi").upper()
        extra = f", {detail}" if (detail or "").strip() else ""
        return True, f"provedor={provider}, destino={admin_num}{extra}"
    return False, detail

def _fmt_data_br(data_str):
    try:
        return datetime.strptime(str(data_str), "%Y-%m-%d").strftime("%d/%m/%Y")
    except Exception:
        return str(data_str)

def _fmt_hora_str(hora_str):
    try:
        s = str(hora_str)
        return s[:5] if len(s) >= 5 else s
    except Exception:
        return str(hora_str)

def _table_height(rows_count: int, min_height: int = 300, max_height: int = 820, row_height: int = 42) -> int:
    try:
        rows = int(rows_count)
    except Exception:
        rows = 0
    rows = max(6, rows)
    calc = 68 + (rows * row_height)
    return max(min_height, min(max_height, calc))

def render_table(data, *, use_container_width: bool = True, min_height: int = 300, max_height: int = 820):
    """
    Render padrão para tabelas do app:
    - visual consistente
    - altura dinâmica por quantidade de linhas
    """
    df = data if isinstance(data, pd.DataFrame) else pd.DataFrame(data)
    h = _table_height(len(df), min_height=min_height, max_height=max_height)
    st.dataframe(df, use_container_width=use_container_width, height=h)

def _calc_idade_from_dob(dob):
    if not dob:
        return None
    try:
        if isinstance(dob, str):
            dob = datetime.strptime(dob, "%Y-%m-%d").date()
        today = datetime.now().date()
        if dob > today:
            return None
        years = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
        return max(0, years)
    except Exception:
        return None

users = load_db("users.json", [{"nome": "Admin", "usuario": "admin", "senha": "252523", "tipo": "admin"}])


def _refresh_users_cache():
    global users
    try:
        users = load_db("users.json", users)
    except Exception:
        pass
    return users
pacientes = load_db("pacientes.json", [])
agenda = load_db("agenda.json", [])
chat_log = load_db("chat_log.json", [])
chatbot_ia_log = load_db("chatbot_ia.json", [])
patient_messages = load_db("patient_messages.json", [])
noticias = load_db("noticias.json", [])
financeiro = load_db("financeiro.json", [])
payments = load_db("payments.json", [])
support_tickets = load_db("support_tickets.json", [])
feedbacks = load_db("feedbacks.json", [])


# =============================================================================
# 4B. AJUDANTES (PACIENTE / HISTÓRICO)
# =============================================================================
def get_paciente_obj(nome_paciente: str):
    '''
    Retorna o objeto do paciente respeitando permissão (admin vê tudo; user vê os próprios).
    '''
    if not nome_paciente:
        return None
    if st.session_state.get("tipo") == "admin":
        return next((x for x in pacientes if x.get("nome") == nome_paciente), None)
    usuario = (st.session_state.get("usuario") or "").strip().lower()
    return next(
        (x for x in pacientes if x.get("nome") == nome_paciente and (x.get("dono") or "").strip().lower() == usuario),
        None
    )

def get_ultimos_dados(p_obj: dict):
    '''
    Puxa dados do último registro do prontuário, quando existir.
    Suporta adulto/adolescente e infantil (criança), pois as chaves podem variar.
    '''
    if not p_obj or not p_obj.get("historico"):
        return {}

    last = p_obj["historico"][-1] or {}
    dv = last.get("dados_vitais", {}) or {}

    # Idade: adulto costuma vir como "idade". Infantil pode vir como "idade_anos" / "idade_total_meses".
    idade = dv.get("idade")
    if idade is None:
        idade = dv.get("idade_anos")
    if idade is None and dv.get("idade_total_meses") is not None:
        try:
            idade = round(float(dv.get("idade_total_meses")) / 12.0, 2)
        except Exception:
            idade = None

    # Altura: adulto costuma vir como "altura" (m). Infantil pode vir como "altura_cm".
    altura = dv.get("altura")
    if altura is None and dv.get("altura_cm") is not None:
        try:
            altura = float(dv.get("altura_cm")) / 100.0
        except Exception:
            altura = None

    # Peso: geralmente "peso"
    peso = dv.get("peso")

    # Outros
    sexo = dv.get("sexo")
    imc = dv.get("imc")

    return {
        "tipo_registro": last.get("tipo"),
        "data": last.get("data"),
        "idade": idade,
        "idade_anos": dv.get("idade_anos"),
        "idade_meses": dv.get("idade_meses"),
        "peso": peso,
        "altura": altura,
        "altura_cm": dv.get("altura_cm"),
        "sexo": sexo,
        "imc": imc,
        "medidas": last.get("medidas") or {},
        "observacoes": dv.get("observacoes") or last.get("observacoes") or "",
    }

    last = p_obj["historico"][-1] or {}
    dv = last.get("dados_vitais", {}) or {}
    return {
        "data": last.get("data"),
        "idade": dv.get("idade"),
        "sexo": dv.get("sexo"),
        "peso": dv.get("peso"),
        "altura": dv.get("altura"),
        "imc": dv.get("imc"),
        "bio_gord": dv.get("bioimpedancia"),
        "visceral": dv.get("visceral"),
    }


def get_anamnese_paciente(p_obj: dict) -> dict:
    anamnese = _normalize_anamnese_data((p_obj or {}).get("anamnese"))
    if not _anamnese_has_content(anamnese) and p_obj:
        ult = get_ultimos_dados(p_obj) or {}
        obs_ult = _clean_text(ult.get("observacoes"))
        if obs_ult:
            anamnese["observacoes_clinicas"] = obs_ult
    return anamnese


def _anamnese_lines(anamnese: dict) -> list:
    anamnese = _normalize_anamnese_data(anamnese)
    labels = [
        ("queixa_principal", "Queixa principal"),
        ("alergias", "Alergias"),
        ("intolerancias", "Intolerâncias"),
        ("condicoes_saude", "Condições de saúde"),
        ("medicamentos_suplementos", "Medicamentos/suplementos"),
        ("observacoes_clinicas", "Observações clínicas"),
    ]
    linhas = []
    for key, label in labels:
        val = _clean_text(anamnese.get(key))
        if val:
            linhas.append(f"- {label}: {val}")
    return linhas


def _patient_record_cpf(p_obj: dict) -> str:
    if not isinstance(p_obj, dict):
        return ""
    return _normalize_cpf(p_obj.get("cpf") or p_obj.get("documento") or "")


def _find_patient_matches_by_cpf(cpf: str) -> list:
    cpf_norm = _normalize_cpf(cpf)
    if not cpf_norm:
        return []
    return [p for p in pacientes if _patient_record_cpf(p) == cpf_norm]


def _get_portal_defaults() -> dict:
    return {
        "liberar_consultas": True,
        "liberar_agenda": True,
        "liberar_dietas": False,
        "liberar_receitas": False,
        "liberar_exames": False,
        "liberar_evolucao": True,
        "liberar_chat": True,
        "liberar_online": False,
        "liberar_avisos": True,
        "status_portal": "ativo",
        "resumo_plano": "",
        "orientacoes": "",
        "dieta_atual": "",
        "receitas_recomendadas": "",
        "exames_resultados": "",
        "online_link": "",
        "online_instrucoes": "",
        "avisos": [],
    }


def _get_patient_portal_config(p_obj: dict) -> dict:
    portal = dict(_get_portal_defaults())
    if isinstance((p_obj or {}).get("portal"), dict):
        portal.update(p_obj.get("portal") or {})
    return portal


def _set_patient_portal_config(p_obj: dict, portal_cfg: dict):
    if not isinstance(p_obj, dict):
        return
    merged = _get_portal_defaults()
    merged.update(portal_cfg or {})
    p_obj["portal"] = merged


def _get_linked_patient_record(user_obj: dict = None):
    user_obj = user_obj or _get_user_obj()
    if not user_obj:
        return None
    if (user_obj.get("tipo") or "").strip().lower() == "admin":
        return None
    linked_cpf = _normalize_cpf(user_obj.get("linked_cpf") or user_obj.get("cpf") or "")
    linked_owner = (user_obj.get("linked_owner") or "").strip().lower()
    linked_name = (user_obj.get("linked_patient_name") or "").strip()
    candidates = pacientes
    if linked_cpf:
        candidates = [p for p in candidates if _patient_record_cpf(p) == linked_cpf]
    if linked_owner:
        candidates = [p for p in candidates if (p.get("dono") or "").strip().lower() == linked_owner]
    if linked_name:
        exact = next((p for p in candidates if (p.get("nome") or "").strip() == linked_name), None)
        if exact:
            return exact
    return candidates[0] if candidates else None


def _find_unique_patient_match_by_cpf(cpf: str):
    matches = _find_patient_matches_by_cpf(cpf)
    if len(matches) == 1:
        return matches[0]
    return None


def _ensure_patient_user_link(user_obj: dict) -> dict:
    if not isinstance(user_obj, dict):
        return user_obj
    if (user_obj.get("tipo") or "").strip().lower() != "patient":
        return user_obj
    linked = _get_linked_patient_record(user_obj)
    if not linked:
        return user_obj
    desired_owner = (linked.get("dono") or "").strip().lower()
    desired_name = (linked.get("nome") or "").strip()
    desired_cpf = _patient_record_cpf(linked)
    changed = False
    if desired_owner and (user_obj.get("linked_owner") or "").strip().lower() != desired_owner:
        user_obj["linked_owner"] = desired_owner
        changed = True
    if desired_name and (user_obj.get("linked_patient_name") or "").strip() != desired_name:
        user_obj["linked_patient_name"] = desired_name
        changed = True
    if desired_cpf and _normalize_cpf(user_obj.get("linked_cpf") or "") != desired_cpf:
        user_obj["linked_cpf"] = desired_cpf
        changed = True
    if changed:
        save_db("users.json", users)
    return user_obj


def _portal_flag_enabled(p_obj: dict, flag_name: str, default: bool = False) -> bool:
    cfg = _get_patient_portal_config(p_obj)
    return bool(cfg.get(flag_name, default))


def _render_patient_portal_admin_panel(p_obj: dict, escolha: str):
    _ensure_patient_portal_access_fields(p_obj, persist=True)
    portal_cfg = _get_patient_portal_config(p_obj)
    with st.expander("🔐 Portal do Paciente • Publicação e vínculo", expanded=True):
        cpf_atual = _patient_record_cpf(p_obj)
        portal_user = _portal_user_by_cpf(cpf_atual)
        codigo_paciente = (p_obj.get("codigo_paciente") or "").strip().upper()
        status_acesso = (p_obj.get("status_acesso_portal") or "nao_ativado").strip().lower()
        status_label, status_class, status_note = _patient_portal_status_ui(status_acesso)
        login_portal = ((portal_user or {}).get("usuario") or cpf_atual or "-")
        telefone_portal = (p_obj.get("telefone") or "").strip()
        telefone_ok = _is_valid_celular(telefone_portal)
        telefone_formatado = _wa_normalize_to_send(telefone_portal) if telefone_ok else ""
        portal_url = _patient_portal_public_url()
        msg_portal = _build_patient_portal_message(p_obj)
        orientacao_completa = _build_patient_portal_instruction_block(p_obj)
        wa_link_portal = _wa_link(telefone_portal, msg_portal) if telefone_ok else ""

        st.markdown(
            f"""
            <div class="dh-portal-shell">
              <div class="dh-portal-head">
                <div>
                  <div class="dh-portal-kicker">Portal do Paciente</div>
                  <div class="dh-portal-title">Liberação de acesso com orientação clara para a nutricionista e para o paciente</div>
                  <div class="dh-portal-subtitle">
                    Visualize o status do portal, confirme CPF e código do paciente, copie as instruções completas e envie tudo por WhatsApp sem sair do fluxo de atendimento.
                  </div>
                </div>
                <div class="dh-portal-status {status_class}">{status_label}</div>
              </div>
              <div class="dh-portal-grid">
                <div class="dh-portal-stat">
                  <div class="dh-portal-stat-label">Código do paciente</div>
                  <div class="dh-portal-stat-value">{html.escape(codigo_paciente or "-")}</div>
                  <div class="dh-portal-stat-note">Use no primeiro acesso junto com o CPF.</div>
                </div>
                <div class="dh-portal-stat">
                  <div class="dh-portal-stat-label">CPF vinculado</div>
                  <div class="dh-portal-stat-value">{html.escape(cpf_atual or "Não informado")}</div>
                  <div class="dh-portal-stat-note">O portal depende do CPF válido no cadastro clínico.</div>
                </div>
                <div class="dh-portal-stat">
                  <div class="dh-portal-stat-label">Login após ativação</div>
                  <div class="dh-portal-stat-value">{html.escape(login_portal)}</div>
                  <div class="dh-portal-stat-note">Depois do primeiro acesso, o paciente entra com CPF e senha.</div>
                </div>
                <div class="dh-portal-stat">
                  <div class="dh-portal-stat-label">WhatsApp do paciente</div>
                  <div class="dh-portal-stat-value">{html.escape(telefone_formatado or telefone_portal or "Não cadastrado")}</div>
                  <div class="dh-portal-stat-note">{html.escape(status_note)}</div>
                </div>
              </div>
              <div class="dh-portal-steps">
                <div class="dh-portal-step">
                  <div class="dh-portal-step-index">1</div>
                  <h4>Primeiro acesso</h4>
                  <p>O paciente entra em <strong>{html.escape(portal_url)}</strong> usando CPF + código do paciente.</p>
                </div>
                <div class="dh-portal-step">
                  <div class="dh-portal-step-index">2</div>
                  <h4>Validação e senha</h4>
                  <p>Depois da validação, ele cria a própria senha e passa a usar CPF + senha nos próximos acessos.</p>
                </div>
                <div class="dh-portal-step">
                  <div class="dh-portal-step-index">3</div>
                  <h4>Operação rápida</h4>
                  <p>Copie o código, copie as instruções completas e envie tudo por WhatsApp com um clique.</p>
                </div>
              </div>
              <div class="dh-portal-help">
                <strong>Resumo operacional</strong>
                <p>{html.escape(status_note)}</p>
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        if cpf_atual:
            st.caption(f"CPF vinculado ao portal: {cpf_atual}")
        else:
            st.warning("Este paciente ainda não possui CPF/documento válido. O vínculo automático do portal depende do CPF.")
        if not telefone_ok:
            st.warning("O paciente ainda não possui WhatsApp válido cadastrado. Atualize o telefone para habilitar o envio rápido das instruções.")
        elif not telefone_formatado:
            st.info("O número foi cadastrado, mas precisa ser normalizado para envio via WhatsApp.")

        ac1, ac2, ac3, ac4 = st.columns(4)
        with ac1:
            _render_clipboard_button("Copiar código do paciente", codigo_paciente or "-", f"portal-code-{escolha}", tone="accent")
        with ac2:
            _render_clipboard_button("Copiar instruções completas", orientacao_completa, f"portal-full-{escolha}", tone="soft")
        with ac3:
            if wa_link_portal:
                st.markdown(f'<a class="dh-btn dh-btn-green" href="{wa_link_portal}" target="_blank">Abrir WhatsApp com mensagem pronta</a>', unsafe_allow_html=True)
            else:
                st.caption("Cadastre um WhatsApp válido para habilitar a abertura automática da conversa.")
        with ac4:
            st.markdown(f'<a class="dh-btn dh-btn-dark" href="{portal_url}" target="_blank">Abrir Portal do Paciente</a>', unsafe_allow_html=True)

        send_col1, send_col2 = st.columns(2)
        enviar_api = send_col1.button("Enviar automaticamente por WhatsApp", key=f"portal_auto_send_{escolha}", use_container_width=True, disabled=not telefone_ok)
        reenviar_api = send_col2.button("Reenviar instruções", key=f"portal_resend_{escolha}", use_container_width=True, disabled=not telefone_ok)
        if enviar_api or reenviar_api:
            user_obj = _get_user_obj()
            ok_wa, detail_wa = _wa_send_text_for_user(user_obj, telefone_portal, msg_portal)
            if ok_wa:
                acao_txt = "reenviadas" if reenviar_api else "enviadas"
                st.success(f"Instruções {acao_txt} com sucesso pelo WhatsApp.")
                if detail_wa:
                    st.caption(f"Detalhe do envio: {detail_wa}")
            else:
                st.warning(f"Não foi possível enviar automaticamente agora: {detail_wa or 'integração indisponível'}. Use o botão de abrir WhatsApp como fallback.")

        a1, a2 = st.columns(2)
        if a1.button("Regenerar código do paciente", key=f"portal_regenerate_code_{escolha}", use_container_width=True):
            p_obj["codigo_paciente"] = _generate_patient_portal_code()
            if portal_user and (portal_user.get("status") or "").strip().lower() != "active":
                p_obj["status_acesso_portal"] = "nao_ativado"
            save_db("pacientes.json", pacientes)
            st.success("Código do paciente regenerado.")
            st.rerun()
        toggle_label = "Bloquear acesso" if (portal_user and (portal_user.get("status") or "").strip().lower() == "active") else "Liberar/Desbloquear acesso"
        if a2.button(toggle_label, key=f"portal_toggle_access_{escolha}", use_container_width=True):
            if portal_user:
                current_status = (portal_user.get("status") or "").strip().lower()
                portal_user["status"] = "blocked" if current_status == "active" else "active"
                p_obj["status_acesso_portal"] = _derive_patient_portal_status(portal_user)
                save_db("users.json", users)
                save_db("pacientes.json", pacientes)
                st.success("Status do acesso atualizado.")
                st.rerun()
            st.warning("Este paciente ainda não ativou o Portal do Paciente.")

        st.text_area("Mensagem pronta de acesso", value=msg_portal, height=200, key=f"portal_msg_template_{escolha}")

        pc1, pc2, pc3 = st.columns(3)
        liberar_consultas = pc1.checkbox("Liberar consultas", value=portal_cfg.get("liberar_consultas", True), key=f"portal_consultas_{escolha}")
        liberar_agenda = pc2.checkbox("Liberar agenda", value=portal_cfg.get("liberar_agenda", True), key=f"portal_agenda_{escolha}")
        liberar_evolucao = pc3.checkbox("Liberar evolução", value=portal_cfg.get("liberar_evolucao", True), key=f"portal_evolucao_{escolha}")

        pc4, pc5, pc6 = st.columns(3)
        liberar_dietas = pc4.checkbox("Liberar dietas", value=portal_cfg.get("liberar_dietas", False), key=f"portal_dietas_{escolha}")
        liberar_receitas = pc5.checkbox("Liberar receitas", value=portal_cfg.get("liberar_receitas", False), key=f"portal_receitas_{escolha}")
        liberar_exames = pc6.checkbox("Liberar exames", value=portal_cfg.get("liberar_exames", False), key=f"portal_exames_{escolha}")

        pc7, pc8, pc9 = st.columns(3)
        liberar_chat = pc7.checkbox("Liberar chat", value=portal_cfg.get("liberar_chat", True), key=f"portal_chat_{escolha}")
        liberar_online = pc8.checkbox("Liberar consulta online", value=portal_cfg.get("liberar_online", False), key=f"portal_online_{escolha}")
        liberar_avisos = pc9.checkbox("Liberar avisos", value=portal_cfg.get("liberar_avisos", True), key=f"portal_avisos_{escolha}")

        status_portal = st.selectbox("Status do portal", ["ativo", "pendente", "oculto"], index=["ativo", "pendente", "oculto"].index((portal_cfg.get("status_portal") or "ativo") if (portal_cfg.get("status_portal") or "ativo") in ["ativo", "pendente", "oculto"] else "ativo"), key=f"portal_status_{escolha}")
        resumo_plano = st.text_input("Resumo do plano atual", value=portal_cfg.get("resumo_plano", ""), key=f"portal_resumo_{escolha}")
        orientacoes_portal = st.text_area("Orientações visíveis ao paciente", value=portal_cfg.get("orientacoes", ""), height=110, key=f"portal_orient_{escolha}")
        dieta_portal = st.text_area("Dieta publicada no portal", value=portal_cfg.get("dieta_atual", ""), height=140, key=f"portal_dieta_publicada_{escolha}")
        receitas_portal = st.text_area("Receitas recomendadas", value=portal_cfg.get("receitas_recomendadas", ""), height=120, key=f"portal_receitas_publicadas_{escolha}")
        exames_portal = st.text_area("Exames / resultados liberados", value=portal_cfg.get("exames_resultados", ""), height=120, key=f"portal_exames_publicados_{escolha}")
        online_link = st.text_input("Link da consulta online", value=portal_cfg.get("online_link", ""), key=f"portal_link_online_{escolha}")
        online_instrucoes = st.text_area("Instruções da consulta online", value=portal_cfg.get("online_instrucoes", ""), height=90, key=f"portal_online_instr_{escolha}")
        avisos_portal = st.text_area("Avisos do paciente (1 por linha)", value="\n".join(portal_cfg.get("avisos", []) if isinstance(portal_cfg.get("avisos"), list) else [str(portal_cfg.get("avisos") or "")]), height=120, key=f"portal_avisos_text_{escolha}")

        if st.button("Salvar Portal do Paciente", key=f"portal_save_{escolha}", use_container_width=True):
            _set_patient_portal_config(
                p_obj,
                {
                    "liberar_consultas": liberar_consultas,
                    "liberar_agenda": liberar_agenda,
                    "liberar_dietas": liberar_dietas,
                    "liberar_receitas": liberar_receitas,
                    "liberar_exames": liberar_exames,
                    "liberar_evolucao": liberar_evolucao,
                    "liberar_chat": liberar_chat,
                    "liberar_online": liberar_online,
                    "liberar_avisos": liberar_avisos,
                    "status_portal": status_portal,
                    "resumo_plano": resumo_plano,
                    "orientacoes": orientacoes_portal,
                    "dieta_atual": dieta_portal,
                    "receitas_recomendadas": receitas_portal,
                    "exames_resultados": exames_portal,
                    "online_link": online_link,
                    "online_instrucoes": online_instrucoes,
                    "avisos": [x.strip() for x in avisos_portal.splitlines() if x.strip()],
                },
            )
            save_db("pacientes.json", pacientes)
            st.success("Configurações do Portal do Paciente salvas.")
            time.sleep(0.4)
            st.rerun()


def _patient_agenda_items(p_obj: dict) -> list:
    if not p_obj:
        return []
    patient_name = (p_obj.get("nome") or "").strip()
    owner = (p_obj.get("dono") or "").strip().lower()
    items = []
    for item in agenda:
        if (item.get("paciente") or "").strip() != patient_name:
            continue
        item_owner = (item.get("dono") or "").strip().lower()
        if owner and item_owner and item_owner != owner:
            continue
        items.append(item)
    return sorted(items, key=lambda x: (_finance_parse_date(x.get("data")), _fmt_hora_str(x.get("hora"))), reverse=True)


def _patient_financial_items(p_obj: dict) -> list:
    if not p_obj:
        return []
    patient_name = (p_obj.get("nome") or "").strip().lower()
    owner = (p_obj.get("dono") or "").strip().lower()
    out = []
    for item in financeiro:
        item_owner = (item.get("dono") or "").strip().lower()
        item_patient = (item.get("paciente") or "").strip().lower()
        if owner and item_owner and item_owner != owner:
            continue
        if item_patient and item_patient != patient_name:
            continue
        if item_patient == patient_name:
            out.append(item)
    return sorted(out, key=lambda x: _finance_parse_date(x.get("data")), reverse=True)


def _patient_message_thread(p_obj: dict) -> list:
    if not p_obj:
        return []
    patient_cpf = _patient_record_cpf(p_obj)
    owner = (p_obj.get("dono") or "").strip().lower()
    thread = []
    for item in patient_messages:
        item_cpf = _normalize_cpf(item.get("patient_cpf") or "")
        item_owner = (item.get("owner") or "").strip().lower()
        if patient_cpf and item_cpf != patient_cpf:
            continue
        if owner and item_owner and item_owner != owner:
            continue
        thread.append(item)
    return sorted(thread, key=lambda x: str(x.get("created_at") or ""))


def _append_patient_message(p_obj: dict, sender_role: str, sender_name: str, message_text: str):
    if not p_obj or not (message_text or "").strip():
        return
    patient_messages.append({
        "patient_cpf": _patient_record_cpf(p_obj),
        "patient_name": p_obj.get("nome") or "",
        "owner": (p_obj.get("dono") or "").strip().lower(),
        "sender_role": (sender_role or "").strip().lower(),
        "sender": (sender_name or "").strip() or "Usuario",
        "msg": (message_text or "").strip(),
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    })
    save_db("patient_messages.json", patient_messages)


def _patient_history_df(p_obj: dict) -> pd.DataFrame:
    historico = (p_obj or {}).get("historico") or []
    rows = []
    for item in historico:
        dv = item.get("dados_vitais") or {}
        medidas = item.get("medidas") or {}
        peso = dv.get("peso")
        altura = dv.get("altura")
        imc_val = dv.get("imc")
        if (imc_val in (None, "")) and peso and altura:
            try:
                imc_val = calc_imc_kg_m(float(peso), float(altura))
            except Exception:
                imc_val = None
        rows.append({
            "data": item.get("data") or "",
            "tipo": item.get("tipo") or "",
            "peso": _as_float_safe(peso),
            "imc": _as_float_safe(imc_val),
            "gordura": _as_float_safe(dv.get("bioimpedancia") or item.get("dobras", {}).get("percentual_gordura")),
            "cintura": _as_float_safe(medidas.get("cintura")),
            "quadril": _as_float_safe(medidas.get("quadril")),
        })
    df = pd.DataFrame(rows)
    if not df.empty:
        df["data_dt"] = pd.to_datetime(df["data"], errors="coerce")
        df = df.sort_values("data_dt")
    return df


def _as_float_safe(val):
    try:
        if val in (None, ""):
            return None
        return float(str(val).replace(",", "."))
    except Exception:
        return None


def _portal_metric_card(title: str, value: str, help_text: str = ""):
    st.markdown(
        _html_block(
            f"""
<div class="dh-soft-metric">
  <div class="dh-soft-metric-title">{html.escape(title)}</div>
  <div class="dh-soft-metric-value">{html.escape(str(value))}</div>
  <div class="dh-soft-metric-sub">{html.escape(help_text)}</div>
</div>
"""
        ),
        unsafe_allow_html=True,
    )


def _render_patient_portal_shell(title: str, subtitle: str):
    st.markdown(
        _html_block(
            f"""
<div class="dh-patient-hero">
  <div class="dh-patient-hero-copy">
    <div class="dh-patient-eyebrow">Portal do Paciente</div>
    <h1>{html.escape(title)}</h1>
    <p>{html.escape(subtitle)}</p>
  </div>
</div>
"""
        ),
        unsafe_allow_html=True,
    )


def _patient_notices(p_obj: dict) -> list:
    cfg = _get_patient_portal_config(p_obj)
    notices = cfg.get("avisos") or []
    if isinstance(notices, list):
        return [str(x).strip() for x in notices if str(x).strip()]
    if str(notices).strip():
        return [str(notices).strip()]
    auto_notices = []
    agenda_items = _patient_agenda_items(p_obj)
    if agenda_items:
        proxima = next((x for x in reversed(agenda_items) if _finance_parse_date(x.get("data")) and _finance_parse_date(x.get("data")) >= datetime.now().date()), None)
        if proxima:
            auto_notices.append(
                f"Proxima consulta em {_fmt_data_br(proxima.get('data'))} as {_fmt_hora_str(proxima.get('hora'))}."
            )
    return auto_notices


def _patient_related_recipes(p_obj: dict) -> list:
    cfg = _get_patient_portal_config(p_obj)
    text = str(cfg.get("receitas_recomendadas") or "").strip()
    if not text:
        return []
    return [x.strip() for x in re.split(r"[\n;]+", text) if x.strip()]


def _portal_patient_status(user_obj: dict = None) -> str:
    user_obj = user_obj or _get_user_obj()
    if not user_obj:
        return "not_found"
    if (user_obj.get("tipo") or "").strip().lower() != "patient":
        return "not_patient"
    if _get_linked_patient_record(user_obj):
        return "linked"
    return (user_obj.get("status") or "pending_link").strip().lower()


def _portal_patient_owner(user_obj: dict = None) -> str:
    user_obj = user_obj or _get_user_obj()
    if not user_obj:
        return ""
    p_obj = _get_linked_patient_record(user_obj)
    if p_obj:
        return (p_obj.get("dono") or "").strip().lower()
    return (user_obj.get("linked_owner") or "").strip().lower()


def _portal_patient_agenda(p_obj: dict) -> list:
    if not p_obj:
        return []
    nome = (p_obj.get("nome") or "").strip()
    dono = (p_obj.get("dono") or "").strip().lower()
    registros = [
        a for a in agenda
        if (a.get("paciente") or "").strip() == nome and (a.get("dono") or "").strip().lower() == dono
    ]
    registros.sort(key=lambda x: f"{x.get('data','')} {x.get('hora','')}")
    return registros


def _portal_patient_finance(p_obj: dict) -> list:
    if not p_obj:
        return []
    nome = (p_obj.get("nome") or "").strip()
    dono = (p_obj.get("dono") or "").strip().lower()
    return [
        item for item in financeiro
        if (item.get("paciente") or "").strip() == nome and (item.get("dono") or "").strip().lower() == dono
    ]


def _portal_patient_messages(user_obj: dict = None) -> list:
    user_obj = user_obj or _get_user_obj()
    if not user_obj:
        return []
    cpf_norm = _normalize_cpf(user_obj.get("linked_cpf") or user_obj.get("cpf") or "")
    owner = _portal_patient_owner(user_obj)
    mensagens = [
        msg for msg in patient_messages
        if _normalize_cpf(msg.get("patient_cpf") or "") == cpf_norm
        and (msg.get("owner") or "").strip().lower() == owner
    ]
    mensagens.sort(key=lambda x: str(x.get("created_at") or ""))
    return mensagens


def _portal_latest_diet_text(p_obj: dict) -> str:
    portal = _get_patient_portal_config(p_obj)
    if _clean_text(portal.get("dieta_atual")):
        return portal.get("dieta_atual")
    for hist in reversed((p_obj or {}).get("historico", []) or []):
        dieta = hist.get("dieta") or hist.get("dietas") or hist.get("plano_alimentar") or hist.get("plano")
        dieta_txt = _clean_text(dieta)
        if dieta_txt:
            return dieta_txt
    return ""


def _portal_latest_recipe_text(p_obj: dict) -> str:
    portal = _get_patient_portal_config(p_obj)
    if _clean_text(portal.get("receitas_recomendadas")):
        return portal.get("receitas_recomendadas")
    for hist in reversed((p_obj or {}).get("historico", []) or []):
        receita = hist.get("receita") or hist.get("receitas") or hist.get("prescricao") or hist.get("prescricoes")
        receita_txt = _clean_text(receita)
        if receita_txt:
            return receita_txt
    return ""


def _portal_latest_exam_text(p_obj: dict) -> str:
    portal = _get_patient_portal_config(p_obj)
    if _clean_text(portal.get("exames_resultados")):
        return portal.get("exames_resultados")
    for hist in reversed((p_obj or {}).get("historico", []) or []):
        texto = hist.get("exames") or hist.get("resultado") or hist.get("resultados") or hist.get("laudo")
        txt = _clean_text(texto)
        if txt:
            return txt
    return ""


def _portal_notifications(p_obj: dict) -> list:
    portal = _get_patient_portal_config(p_obj)
    avisos = []
    for idx, item in enumerate(portal.get("avisos") or []):
        if isinstance(item, dict):
            avisos.append(item)
        elif str(item).strip():
            avisos.append({"titulo": f"Aviso {idx+1}", "descricao": str(item).strip(), "data": ""})
    if _clean_text(portal.get("orientacoes")):
        avisos.insert(0, {"titulo": "Orientações da nutricionista", "descricao": portal.get("orientacoes"), "data": ""})
    return avisos


def _portal_metric_card(label: str, value: str, note: str = ""):
    note_html = f'<div class="dh-patient-metric-note">{html.escape(note)}</div>' if note else ""
    st.markdown(
        _html_block(
            f"""
<div class="dh-patient-metric">
  <div class="dh-patient-metric-label">{html.escape(label)}</div>
  <div class="dh-patient-metric-value">{html.escape(value)}</div>
  {note_html}
</div>
"""
        ),
        unsafe_allow_html=True,
    )


def _portal_pending_state():
    st.markdown(
        _html_block(
            """
<div class="dh-patient-empty">
  <h3>Cadastro aguardando vínculo</h3>
  <p>Seu acesso foi criado, mas o CPF ainda não foi encontrado na base clínica de uma nutricionista. Aguarde validação do ADMIN ou da profissional responsável para liberar o portal completo.</p>
</div>
"""
        ),
        unsafe_allow_html=True,
    )


def _inject_patient_portal_styles():
    st.markdown(
        """
        <style>
        .dh-patient-shell{display:grid;gap:18px;}
        .dh-patient-hero{display:grid;grid-template-columns:minmax(0,1.8fr) minmax(260px,1fr);gap:18px;padding:24px;border-radius:22px;border:1px solid rgba(88,227,179,0.14);background:linear-gradient(135deg, rgba(11,24,43,0.98), rgba(13,30,55,0.94));box-shadow:0 28px 52px rgba(0,0,0,0.24);}
        .dh-patient-hero h2{margin:0;color:#f8fbff;font-size:2rem;font-weight:800;letter-spacing:-0.02em;}
        .dh-patient-hero p{margin:8px 0 0;color:#bdd0e4;line-height:1.6;}
        .dh-patient-hero-side{display:grid;gap:12px;align-content:start;}
        .dh-patient-soft-card{padding:16px;border-radius:18px;border:1px solid rgba(255,255,255,0.06);background:rgba(10,20,37,0.88);box-shadow:0 16px 30px rgba(0,0,0,0.18);}
        .dh-patient-soft-card h4{margin:0 0 8px;color:#f5f8ff;font-size:1rem;font-weight:780;}
        .dh-patient-soft-card p,.dh-patient-soft-card li{color:#b8c8d9;line-height:1.55;}
        .dh-patient-grid-4{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:14px;}
        .dh-patient-grid-3{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:14px;}
        .dh-patient-grid-2{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:16px;}
        .dh-patient-metric{padding:16px 18px;border-radius:18px;border:1px solid rgba(109,230,187,0.16);background:linear-gradient(180deg, rgba(15,28,48,0.96), rgba(10,19,35,0.94));min-height:118px;}
        .dh-patient-metric-label{font-size:0.86rem;font-weight:700;color:#95afc8;text-transform:uppercase;letter-spacing:0.05em;}
        .dh-patient-metric-value{margin-top:10px;color:#f8fbff;font-size:2rem;font-weight:850;line-height:1;}
        .dh-patient-metric-note{margin-top:10px;color:#9ecfb7;font-size:0.88rem;line-height:1.4;}
        .dh-patient-kicker{display:inline-flex;align-items:center;gap:8px;padding:7px 12px;border-radius:999px;border:1px solid rgba(108,229,186,0.24);background:rgba(11,26,42,0.78);color:#d9fff0;font-size:0.82rem;font-weight:700;}
        .dh-patient-section-title{margin:6px 0 10px;color:#f5f8ff;font-size:1.08rem;font-weight:800;}
        .dh-patient-list{display:grid;gap:12px;}
        .dh-patient-list-item{padding:14px 15px;border-radius:16px;border:1px solid rgba(255,255,255,0.06);background:rgba(11,21,38,0.88);}
        .dh-patient-list-title{color:#f5f8ff;font-weight:760;}
        .dh-patient-list-meta{color:#8fb4cd;font-size:0.86rem;margin-top:4px;}
        .dh-patient-list-body{color:#bfd0df;line-height:1.55;margin-top:10px;}
        .dh-patient-empty{padding:22px;border-radius:18px;border:1px dashed rgba(255,255,255,0.12);background:rgba(10,19,34,0.78);color:#b8c7d9;}
        .dh-patient-empty h3{margin:0 0 8px;color:#f7fbff;font-size:1.2rem;}
        .dh-patient-table-caption{color:#8fb4cd;font-size:0.9rem;margin-bottom:8px;}
        @media (max-width: 1080px){.dh-patient-grid-4,.dh-patient-grid-3{grid-template-columns:repeat(2,minmax(0,1fr));}.dh-patient-hero,.dh-patient-grid-2{grid-template-columns:1fr;}}
        @media (max-width: 720px){.dh-patient-grid-4,.dh-patient-grid-3{grid-template-columns:1fr;}}
        </style>
        """,
        unsafe_allow_html=True,
    )


def _portal_patient_context():
    user_obj = _ensure_patient_user_link(_get_user_obj())
    p_obj = _get_linked_patient_record(user_obj)
    portal = _get_patient_portal_config(p_obj)
    return user_obj, p_obj, portal


def _portal_patient_header(title: str, subtitle: str):
    _inject_patient_portal_styles()
    user_obj, p_obj, portal = _portal_patient_context()
    if not p_obj:
        st.title(title)
        st.caption(subtitle)
        _portal_pending_state()
        return user_obj, p_obj, portal
    prox_agenda = next((a for a in _portal_patient_agenda(p_obj) if str(a.get("data") or "") >= datetime.now().strftime("%Y-%m-%d")), None)
    resumo_plano = _clean_text(portal.get("resumo_plano")) or "Acompanhamento em andamento"
    st.markdown(
        _html_block(
            f"""
<div class="dh-patient-hero">
  <div>
    <div class="dh-patient-kicker">Portal do Paciente</div>
    <h2>{html.escape(title)}</h2>
    <p>{html.escape(subtitle)}</p>
    <p style="margin-top:14px;"><strong style="color:#f8fbff;">Plano atual:</strong> {html.escape(resumo_plano)}</p>
  </div>
  <div class="dh-patient-hero-side">
    <div class="dh-patient-soft-card"><h4>Paciente</h4><p>{html.escape(p_obj.get("nome") or "-")}</p></div>
    <div class="dh-patient-soft-card"><h4>Próxima consulta</h4><p>{html.escape((prox_agenda or {}).get("data") or "Sem agendamento")} {html.escape((prox_agenda or {}).get("hora") or "")}</p></div>
  </div>
</div>
"""
        ),
        unsafe_allow_html=True,
    )
    return user_obj, p_obj, portal


def modulo_paciente_dashboard():
    user_obj, p_obj, portal = _portal_patient_header("Meu acompanhamento", "Veja as principais atualizações do seu tratamento, próximas ações e conteúdos liberados pela nutricionista.")
    if not p_obj:
        return
    agenda_itens = _portal_patient_agenda(p_obj)
    futuros = [a for a in agenda_itens if str(a.get("data") or "") >= datetime.now().strftime("%Y-%m-%d")]
    historico = (p_obj.get("historico") or [])
    ultimos = get_ultimos_dados(p_obj) or {}
    finance_items = _portal_patient_finance(p_obj)
    total_pago = sum(float(item.get("valor") or 0) for item in finance_items if (item.get("tipo") or "").lower() == "receita" and (item.get("status") or "").lower() in ("pago", "recebido"))
    k1, k2, k3, k4 = st.columns(4)
    with k1: _portal_metric_card("Próxima consulta", (futuros[0].get("data") if futuros else "Sem agenda"), (futuros[0].get("hora") if futuros else ""))
    with k2: _portal_metric_card("Última consulta", ultimos.get("data") or "-", (historico[-1].get("tipo") if historico else "Sem registros"))
    with k3: _portal_metric_card("Status da dieta", "Liberada" if _clean_text(_portal_latest_diet_text(p_obj)) else "Pendente", "Atualizada pela nutricionista")
    with k4: _portal_metric_card("Total investido", _format_brl(total_pago), f"{len(finance_items)} lançamentos vinculados")

    left, right = st.columns([1.4, 1], gap="large")
    with left:
        st.markdown("### Próximos passos")
        cards = [
            ("Dieta", "Consulte seu plano alimentar atual e orientações liberadas.", "portal_dietas"),
            ("Exames", "Confira resultados liberados e observações clínicas.", "portal_exames"),
            ("Chat", "Tire dúvidas diretamente com sua nutricionista.", "portal_chat"),
        ]
        cols = st.columns(3)
        for idx, (label, desc, route) in enumerate(cards):
            with cols[idx]:
                st.markdown(f'<div class="dh-patient-soft-card"><h4>{html.escape(label)}</h4><p>{html.escape(desc)}</p></div>', unsafe_allow_html=True)
                if st.button(f"Abrir {label}", key=f"portal_dash_jump_{route}", use_container_width=True):
                    target_key = _menu_key_from_route(route)
                    st.session_state["dh_selected_menu"] = target_key
                    _qp_set(SIDEBAR_MENU_QUERY_KEY, target_key)
                    st.rerun()
        st.markdown("### Avisos importantes")
        avisos = _portal_notifications(p_obj)
        if avisos:
            for idx, aviso in enumerate(avisos[:4], start=1):
                st.markdown(
                    f'<div class="dh-patient-list-item"><div class="dh-patient-list-title">{html.escape(aviso.get("titulo") or f"Aviso {idx}")}</div><div class="dh-patient-list-meta">{html.escape(aviso.get("data") or "")}</div><div class="dh-patient-list-body">{html.escape(aviso.get("descricao") or "")}</div></div>',
                    unsafe_allow_html=True,
                )
        else:
            st.markdown('<div class="dh-patient-empty">Nenhum aviso liberado no momento.</div>', unsafe_allow_html=True)
    with right:
        st.markdown("### Resumo rápido")
        st.markdown(
            f'<div class="dh-patient-soft-card"><h4>Medidas mais recentes</h4><p>Peso: {html.escape(str(ultimos.get("peso") or "-"))} kg<br>IMC: {html.escape(str(round(float(ultimos.get("imc") or 0),2) if ultimos.get("imc") else "-"))}<br>Altura: {html.escape(str(ultimos.get("altura") or "-"))} m</p></div>',
            unsafe_allow_html=True,
        )
        st.markdown(
            f'<div class="dh-patient-soft-card"><h4>Orientações atuais</h4><p>{html.escape(_clean_text(portal.get("orientacoes")) or "Sem orientações adicionais liberadas.")}</p></div>',
            unsafe_allow_html=True,
        )


def modulo_paciente_consultas():
    user_obj, p_obj, portal = _portal_patient_header("Minhas consultas", "Acompanhe histórico, próximos atendimentos, observações liberadas e orientações pós-consulta.")
    if not p_obj:
        return
    if not portal.get("liberar_consultas", True):
        st.info("Sua nutricionista ainda não liberou este módulo.")
        return
    itens = _portal_patient_agenda(p_obj)
    if not itens:
        st.markdown('<div class="dh-patient-empty">Ainda não há consultas vinculadas ao seu cadastro.</div>', unsafe_allow_html=True)
        return
    for item in itens:
        titulo = f"{item.get('data') or '-'} {item.get('hora') or ''}".strip()
        meta = f"{item.get('tipo') or 'Consulta'} • {item.get('status') or 'Agendado'}"
        corpo = item.get("obs") or "Sem observações liberadas."
        st.markdown(
            f'<div class="dh-patient-list-item"><div class="dh-patient-list-title">{html.escape(titulo)}</div><div class="dh-patient-list-meta">{html.escape(meta)}</div><div class="dh-patient-list-body">{html.escape(corpo)}</div></div>',
            unsafe_allow_html=True,
        )


def modulo_paciente_dietas():
    user_obj, p_obj, portal = _portal_patient_header("Minhas dietas", "Visualize o plano alimentar liberado, instruções e orientações práticas do seu acompanhamento.")
    if not p_obj:
        return
    if not portal.get("liberar_dietas"):
        st.info("Sua dieta ainda não foi liberada no portal.")
        return
    dieta = _portal_latest_diet_text(p_obj)
    if not dieta:
        st.markdown('<div class="dh-patient-empty">Nenhuma dieta publicada até o momento.</div>', unsafe_allow_html=True)
        return
    st.markdown("### Plano alimentar atual")
    st.text_area("Plano", value=dieta, height=380, disabled=True, key="portal_dieta_text")
    if _clean_text(portal.get("orientacoes")):
        st.markdown("### Observações da nutricionista")
        st.info(portal.get("orientacoes"))


def modulo_paciente_receitas():
    user_obj, p_obj, portal = _portal_patient_header("Receitas recomendadas", "Receitas e sugestões liberadas para facilitar a adesão ao plano alimentar.")
    if not p_obj:
        return
    if not portal.get("liberar_receitas"):
        st.info("As receitas ainda não foram liberadas para o seu portal.")
        return
    receitas_txt = _portal_latest_recipe_text(p_obj)
    if not receitas_txt:
        st.markdown('<div class="dh-patient-empty">Nenhuma receita recomendada foi publicada ainda.</div>', unsafe_allow_html=True)
        return
    for bloco in [x.strip() for x in receitas_txt.split("\n\n") if x.strip()]:
        st.markdown(f'<div class="dh-patient-list-item"><div class="dh-patient-list-body">{html.escape(bloco)}</div></div>', unsafe_allow_html=True)


def modulo_paciente_exames():
    user_obj, p_obj, portal = _portal_patient_header("Exames e resultados", "Acesse exames, laudos, observações e resultados liberados pela nutricionista.")
    if not p_obj:
        return
    if not portal.get("liberar_exames"):
        st.info("Os exames ainda não foram liberados no portal.")
        return
    exames_txt = _portal_latest_exam_text(p_obj)
    if exames_txt:
        st.text_area("Resultados e observações", value=exames_txt, height=320, disabled=True, key="portal_exam_text")
    else:
        st.markdown('<div class="dh-patient-empty">Não há exames ou resultados publicados até o momento.</div>', unsafe_allow_html=True)
    st.markdown("### Enviar exame para revisão")
    exame_upload = st.file_uploader("Upload controlado de exame (PDF/JPG/PNG)", type=["pdf", "png", "jpg", "jpeg"], key="portal_exam_upload")
    if exame_upload is not None:
        st.success("Arquivo recebido. A nutricionista poderá revisar o material no painel principal.")


def modulo_paciente_evolucao():
    user_obj, p_obj, portal = _portal_patient_header("Medidas e evolução", "Acompanhe peso, IMC, percentual de gordura e sua evolução ao longo do tratamento.")
    if not p_obj:
        return
    if not portal.get("liberar_evolucao", True):
        st.info("A visualização de evolução ainda não foi liberada.")
        return
    historico = []
    for h in (p_obj.get("historico") or []):
        vitais = h.get("dados_vitais") or {}
        historico.append({
            "Data": _finance_parse_date(h.get("data")),
            "Peso": float(vitais.get("peso") or 0) if vitais.get("peso") not in (None, "") else None,
            "IMC": float(vitais.get("imc") or 0) if vitais.get("imc") not in (None, "") else None,
            "% Gordura": float(vitais.get("bioimpedancia") or 0) if vitais.get("bioimpedancia") not in (None, "") else None,
            "Gordura visceral": float(vitais.get("visceral") or 0) if vitais.get("visceral") not in (None, "") else None,
        })
    evo_df = pd.DataFrame(historico)
    if evo_df.empty:
        st.markdown('<div class="dh-patient-empty">Ainda não há medições suficientes para exibir a evolução.</div>', unsafe_allow_html=True)
        return
    evo_df["Data"] = pd.to_datetime(evo_df["Data"], errors="coerce")
    evo_df = evo_df.sort_values("Data")
    k1, k2, k3 = st.columns(3)
    last_row = evo_df.dropna(how="all").iloc[-1]
    with k1: _portal_metric_card("Peso atual", f"{last_row.get('Peso') or '-'} kg")
    with k2: _portal_metric_card("IMC atual", f"{round(float(last_row.get('IMC')),2) if pd.notna(last_row.get('IMC')) else '-'}")
    with k3: _portal_metric_card("% gordura", f"{round(float(last_row.get('% Gordura')),1) if pd.notna(last_row.get('% Gordura')) else '-'}")
    chart_cols = st.columns(2)
    with chart_cols[0]:
        peso_df = evo_df.dropna(subset=["Peso"]).copy()
        if not peso_df.empty:
            fig_peso = px.line(peso_df, x="Data", y="Peso", markers=True, template="plotly_dark", title="Peso por período")
            st.plotly_chart(fig_peso, use_container_width=True, config={"displayModeBar": False})
    with chart_cols[1]:
        imc_df = evo_df.dropna(subset=["IMC"]).copy()
        if not imc_df.empty:
            fig_imc = px.line(imc_df, x="Data", y="IMC", markers=True, template="plotly_dark", title="IMC por período")
            st.plotly_chart(fig_imc, use_container_width=True, config={"displayModeBar": False})
    if evo_df["% Gordura"].notna().any():
        fig_gord = px.bar(evo_df.dropna(subset=["% Gordura"]), x="Data", y="% Gordura", template="plotly_dark", title="Percentual de gordura")
        st.plotly_chart(fig_gord, use_container_width=True, config={"displayModeBar": False})
    st.markdown("### Histórico")
    st.dataframe(evo_df.fillna(""), use_container_width=True, height=260)


def modulo_paciente_alimentos():
    user_obj, p_obj, portal = _portal_patient_header("Consulta nutricional de alimentos", "Pesquise alimentos e veja calorias, macronutrientes e uma leitura nutricional simples, sem prescrição clínica.")
    if not p_obj:
        return
    alimento = st.text_input("Pesquisar alimento", placeholder="Ex: abacate, arroz integral, whey...")
    if not alimento:
        st.markdown('<div class="dh-patient-empty">Digite um alimento para consultar a tabela nutricional simplificada.</div>', unsafe_allow_html=True)
        return
    resposta = ""
    if ia_ok():
        try:
            client = get_groq_client()
            if client is not None:
                res = client.chat.completions.create(
                    model=os.getenv("model", "llama-3.3-70b-versatile"),
                    temperature=0.1,
                    max_tokens=650,
                    messages=[
                        {"role": "system", "content": "Você é um assistente limitado a tabela nutricional de alimentos. Responda apenas calorias, macros, porção e observações alimentares simples. Não prescreva dieta, não atue como nutricionista clínico."},
                        {"role": "user", "content": f"Mostre tabela nutricional resumida, porção de referência e observações simples para o alimento: {alimento}."},
                    ],
                )
                resposta = (res.choices[0].message.content or "").strip()
        except Exception:
            resposta = ""
    if not resposta:
        resposta = f"Tabela nutricional simplificada indisponível no momento para `{alimento}`. Configure a IA para habilitar a consulta inteligente."
    st.markdown("### Resultado")
    st.write(resposta)


def modulo_paciente_chat():
    user_obj, p_obj, portal = _portal_patient_header("Chat com a nutricionista", "Envie mensagens dentro do sistema e acompanhe o histórico da conversa referente ao seu acompanhamento.")
    if not p_obj:
        return
    if not portal.get("liberar_chat", True):
        st.info("O chat ainda não foi liberado para o seu acompanhamento.")
        return
    historico = _portal_patient_messages(user_obj)
    for msg in historico[-40:]:
        role = "assistant" if (msg.get("sender_role") or "").lower() in ("nutritionist", "admin") else "user"
        with st.chat_message(role):
            st.markdown(msg.get("content") or "")
            if msg.get("created_at"):
                st.caption(msg.get("created_at"))
    nova_msg = st.chat_input("Escreva sua mensagem")
    if nova_msg:
        patient_messages.append({
            "id": uuid.uuid4().hex,
            "owner": _portal_patient_owner(user_obj),
            "patient_cpf": _normalize_cpf(user_obj.get("linked_cpf") or user_obj.get("cpf") or ""),
            "patient_user": (user_obj.get("usuario") or "").strip().lower(),
            "sender_role": "patient",
            "sender_user": (user_obj.get("usuario") or "").strip().lower(),
            "content": nova_msg,
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        })
        save_db("patient_messages.json", patient_messages)
        st.rerun()


def modulo_paciente_online():
    user_obj, p_obj, portal = _portal_patient_header("Sala de consulta online", "Encontre o link da consulta, instruções pré-atendimento e acesso rápido quando a modalidade for online.")
    if not p_obj:
        return
    if not portal.get("liberar_online"):
        st.info("Sua nutricionista ainda não liberou consulta online para este acompanhamento.")
        return
    link = (portal.get("online_link") or "").strip()
    instrucoes = _clean_text(portal.get("online_instrucoes")) or "Acesse alguns minutos antes do horário e mantenha câmera e áudio prontos."
    st.markdown(f'<div class="dh-patient-soft-card"><h4>Instruções</h4><p>{html.escape(instrucoes)}</p></div>', unsafe_allow_html=True)
    if link:
        st.link_button("Entrar na consulta online", link, use_container_width=True)
    else:
        st.markdown('<div class="dh-patient-empty">Nenhum link de consulta foi configurado ainda.</div>', unsafe_allow_html=True)


def modulo_paciente_avisos():
    user_obj, p_obj, portal = _portal_patient_header("Avisos e notificações", "Consulte lembretes de consulta, novas dietas liberadas, mensagens e orientações importantes.")
    if not p_obj:
        return
    avisos = _portal_notifications(p_obj)
    if not avisos:
        st.markdown('<div class="dh-patient-empty">Nenhuma notificação recente.</div>', unsafe_allow_html=True)
        return
    for idx, aviso in enumerate(avisos, start=1):
        st.markdown(
            f'<div class="dh-patient-list-item"><div class="dh-patient-list-title">{html.escape(aviso.get("titulo") or f"Aviso {idx}")}</div><div class="dh-patient-list-meta">{html.escape(aviso.get("data") or "")}</div><div class="dh-patient-list-body">{html.escape(aviso.get("descricao") or "")}</div></div>',
            unsafe_allow_html=True,
        )


def modulo_paciente_perfil():
    user_obj, p_obj, portal = _portal_patient_header("Meu perfil", "Consulte seus dados cadastrais, informações de acompanhamento e preferências básicas disponíveis no portal.")
    if not p_obj:
        return
    col1, col2 = st.columns(2)
    with col1:
        st.markdown(f'<div class="dh-patient-soft-card"><h4>Dados cadastrais</h4><p><strong>Nome:</strong> {html.escape(p_obj.get("nome") or "-")}<br><strong>CPF:</strong> {html.escape(_patient_record_cpf(p_obj) or "-")}<br><strong>Email:</strong> {html.escape(p_obj.get("email") or "-")}<br><strong>Telefone:</strong> {html.escape(p_obj.get("telefone") or "-")}</p></div>', unsafe_allow_html=True)
    with col2:
        st.markdown(f'<div class="dh-patient-soft-card"><h4>Acompanhamento</h4><p><strong>Status:</strong> {html.escape(portal.get("status_portal") or "ativo")}<br><strong>Cidade:</strong> {html.escape(p_obj.get("cidade") or "-")}<br><strong>Sexo:</strong> {html.escape(p_obj.get("sexo") or "-")}<br><strong>Idade:</strong> {html.escape(str(p_obj.get("idade") or "-"))}</p></div>', unsafe_allow_html=True)


def _historico_prescricao_lines(p_obj: dict, max_entries: int = 30) -> list:
    historico = (p_obj or {}).get("historico")
    if not isinstance(historico, list) or not historico:
        return []

    linhas = []
    for reg in historico[-max_entries:]:
        if not isinstance(reg, dict):
            continue
        data = _clean_text(reg.get("data")) or "sem data"
        tipo = _clean_text(reg.get("tipo")) or "registro_clinico"
        dados_vitais = reg.get("dados_vitais") if isinstance(reg.get("dados_vitais"), dict) else {}
        medidas = reg.get("medidas") if isinstance(reg.get("medidas"), dict) else {}

        partes = []
        for key, label in [
            ("idade", "idade"),
            ("sexo", "sexo"),
            ("peso", "peso"),
            ("altura", "altura"),
            ("altura_cm", "altura_cm"),
            ("imc", "imc"),
            ("bioimpedancia", "bioimpedância"),
            ("visceral", "gordura_visceral"),
            ("imc_percentil", "percentil_imc"),
            ("classificacao", "classificação"),
            ("status_massa_magra", "status_massa_magra"),
        ]:
            val = _clean_text(dados_vitais.get(key))
            if val:
                partes.append(f"{label}: {val}")

        # Medidas clínicas úteis para prescrição.
        for key, label in [
            ("cintura_cm", "cintura_cm"),
            ("quadril", "quadril"),
            ("rcq", "rcq"),
        ]:
            val = _clean_text(medidas.get(key))
            if val:
                partes.append(f"{label}: {val}")

        obs = _clean_text(reg.get("observacoes") or reg.get("nota") or dados_vitais.get("observacoes"))
        if obs:
            partes.append(f"obs: {obs}")

        if partes:
            linhas.append(f"- {data} ({tipo}): " + "; ".join(partes))

    return linhas


def calc_tdee(peso_kg: float, altura_m: float, idade: int, sexo: str, atividade: str):
    '''
    Estimativa de TDEE (gasto calórico diário) via Mifflin-St Jeor + fator de atividade.
    Retorna dict com bmr, tdee e fator.
    '''
    if not (peso_kg and altura_m and idade and sexo and atividade):
        return None
    altura_cm = altura_m * 100.0
    # Mifflin-St Jeor
    if sexo == "Masculino":
        bmr = 10 * peso_kg + 6.25 * altura_cm - 5 * idade + 5
    else:
        bmr = 10 * peso_kg + 6.25 * altura_cm - 5 * idade - 161

    fatores = {
        "Sedentário": 1.2,
        "Leve": 1.375,
        "Moderado": 1.55,
        "Intenso": 1.725
    }
    fator = fatores.get(atividade, 1.2)
    tdee = bmr * fator
    return {"bmr": bmr, "tdee": tdee, "fator": fator}


# =============================================================================
# 6. PDF E FUNÇÕES ÚTEIS
# =============================================================================
class PDF(FPDF):
    def header(self):
        self.set_fill_color(10, 22, 43)
        self.rect(0, 0, 210, 28, "F")

        logo_encontrado = _find_pdf_logo()
        if logo_encontrado:
            try:
                self.image(logo_encontrado, 11, 6, 16)
            except Exception:
                pass

        self.set_text_color(244, 248, 255)
        self.set_font("Helvetica", "B", 14)
        self.set_xy(30, 7)
        self.cell(0, 6, "DietHealth System", 0, 1, "L")
        self.set_font("Helvetica", "", 8)
        self.set_xy(30, 14)
        self.cell(0, 5, "Documento clínico nutricional", 0, 1, "L")

        self.set_draw_color(46, 125, 200)
        self.set_line_width(0.5)
        self.line(10, 28, 200, 28)
        self.ln(13)

    def footer(self):
        self.set_y(-14)
        self.set_draw_color(205, 214, 225)
        self.line(10, self.get_y(), 200, self.get_y())
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(120, 129, 141)
        self.cell(0, 10, _pdf_safe_text(f"Página {self.page_no()} - DietHealth"), 0, 0, "C")


def _find_pdf_logo():
    possibilidades = [
        "logo2_nutri.png",
        "logo2_nutri.jpg",
        "logo2_nutri.jpeg",
        "logo_nutri.png",
        "logo_nutri.jpg",
        "logo_nutri.jpeg",
        "logo.png",
    ]
    for p in possibilidades:
        if os.path.exists(p):
            return p
    return None


def _pdf_safe_text(value) -> str:
    return str(value or "").encode("latin-1", "replace").decode("latin-1")


def _strip_markdown_text(text: str) -> str:
    txt = _pdf_safe_text(text)
    txt = re.sub(r"^\s{0,3}#{1,6}\s*", "", txt)
    txt = re.sub(r"\*\*(.*?)\*\*", r"\1", txt)
    txt = re.sub(r"__(.*?)__", r"\1", txt)
    txt = txt.replace("`", "")
    return txt


def _split_meal_line_for_pdf(line: str):
    clean = _strip_markdown_text(line).strip()
    m = re.match(r"^(?P<prefix>(?:[-*]\s*)?(?:\d+\s*[\)\.\-:]\s*)?)(?P<body>.+)$", clean, flags=re.IGNORECASE)
    if not m:
        return None

    prefix = m.group("prefix") or ""
    body = (m.group("body") or "").strip()
    meal_match = re.match(
        r"^(?P<meal>caf.\s+da\s+manh.|lanche\s+da\s+manh.|almo.o|lanche\s+da\s+tarde|"
        r"jantar|ceia|pre\s+treino|pr.\s+treino|pos\s+treino|p.\s*s\s+treino|desjejum)"
        r"(?P<suffix>\s*[:\-]?\s*.*)$",
        body,
        flags=re.IGNORECASE,
    )
    if not meal_match:
        return None

    return (
        _pdf_safe_text(prefix),
        _pdf_safe_text(meal_match.group("meal") or ""),
        _pdf_safe_text(meal_match.group("suffix") or ""),
    )


def _extract_markdown_heading(line: str):
    m = re.match(r"^\s{0,3}(#{2,6})\s+(.+?)\s*$", line or "")
    if not m:
        return None
    level = len(m.group(1))
    title = _strip_markdown_text(m.group(2)).strip()
    if not title:
        return None
    return level, _pdf_safe_text(title)


def _write_meal_line_pdf(pdf: PDF, line_height: float, line: str):
    parts = _split_meal_line_for_pdf(line)
    if not parts:
        _pdf_multicell_line(pdf, line_height, line)
        return

    prefix, meal, suffix = parts
    pdf.set_font("Helvetica", "", 10.5)
    if prefix:
        pdf.write(line_height, prefix)
    pdf.set_font("Helvetica", "B", 10.5)
    pdf.write(line_height, meal)
    pdf.set_font("Helvetica", "", 10.5)
    if suffix:
        pdf.write(line_height, suffix)
    pdf.ln(line_height)


def _pdf_multicell_line(pdf: PDF, line_height: float, text: str):
    safe_text = _strip_markdown_text(text)
    try:
        pdf.multi_cell(0, line_height, safe_text, new_x="LMARGIN", new_y="NEXT")
    except TypeError:
        # Compatibilidade com implementacoes antigas do FPDF sem new_x/new_y.
        pdf.multi_cell(0, line_height, safe_text)
        pdf.set_x(pdf.l_margin)


def _write_pdf_document_body(pdf: PDF, texto: str):
    conteudo = _beautify_generated_text(texto)
    lines = conteudo.split("\n") if conteudo else []

    pdf.set_text_color(30, 40, 55)
    pdf.set_font("Helvetica", "", 10.5)

    for raw in lines:
        line = raw.strip()
        if not line:
            pdf.ln(2)
            continue

        md_heading = _extract_markdown_heading(line)
        if md_heading:
            level, title = md_heading
            pdf.ln(1)
            if level <= 3:
                pdf.set_text_color(18, 86, 145)
                pdf.set_font("Helvetica", "B", 11.2)
                _pdf_multicell_line(pdf, 6.6, title)
            else:
                pdf.set_text_color(24, 96, 168)
                pdf.set_font("Helvetica", "B", 10.8)
                _pdf_multicell_line(pdf, 6.2, title)
            pdf.set_text_color(30, 40, 55)
            pdf.set_font("Helvetica", "", 10.5)
            continue

        if re.match(r"^(Rx\s*\d+\s*:|F[oó]rmula\s*\d+\s*-)", line, flags=re.IGNORECASE):
            pdf.ln(1)
            pdf.set_text_color(15, 78, 128)
            pdf.set_font("Helvetica", "B", 11)
            _pdf_multicell_line(pdf, 6.5, line)
            pdf.set_text_color(30, 40, 55)
            pdf.set_font("Helvetica", "", 10.5)
            continue

        if re.match(r"^(Se[cç][aã]o\s*\d+\s*:|\d+\.\s+)", line, flags=re.IGNORECASE):
            pdf.ln(1)
            pdf.set_text_color(21, 101, 192)
            pdf.set_font("Helvetica", "B", 10.8)
            _pdf_multicell_line(pdf, 6.2, line)
            pdf.set_text_color(30, 40, 55)
            pdf.set_font("Helvetica", "", 10.5)
            continue

        if line.startswith("- "):
            line = "- " + line[2:]

        if _split_meal_line_for_pdf(line):
            _write_meal_line_pdf(pdf, 6.2, line)
        else:
            _pdf_multicell_line(pdf, 6.2, line)

def gerar_pdf_pro(nome_paciente, texto, titulo, nome_prof="Nutricionista", registro_prof=""):
    pdf = PDF()
    pdf.add_page()
    pdf.set_text_color(16, 29, 48)
    pdf.set_font("Helvetica", "B", 14)
    pdf.cell(0, 9, _pdf_safe_text(titulo), 0, 1, "C")
    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(105, 116, 130)
    pdf.cell(0, 5, _pdf_safe_text(datetime.now().strftime("Gerado em %d/%m/%Y às %H:%M")), 0, 1, "C")
    pdf.ln(4)

    info_y = pdf.get_y()
    pdf.set_fill_color(236, 244, 255)
    pdf.set_draw_color(194, 213, 239)
    pdf.rect(10, info_y, 190, 20, "DF")
    pdf.set_xy(14, info_y + 3)
    pdf.set_font("Helvetica", "B", 10)
    pdf.set_text_color(28, 61, 106)
    pdf.cell(96, 5, _pdf_safe_text(f"Paciente: {nome_paciente}"), 0, 0, "L")
    pdf.cell(80, 5, _pdf_safe_text(f"Registro: {registro_prof or '-'}"), 0, 1, "R")
    pdf.set_x(14)
    pdf.set_font("Helvetica", "", 9.5)
    pdf.set_text_color(71, 82, 98)
    pdf.cell(96, 5, _pdf_safe_text(f"Profissional: {nome_prof or 'Nutricionista'}"), 0, 0, "L")
    pdf.cell(80, 5, _pdf_safe_text("Documento emitido pelo DietHealth"), 0, 1, "R")
    pdf.set_y(info_y + 24)

    _write_pdf_document_body(pdf, texto)

    if pdf.get_y() > 220:
        pdf.add_page()
    pdf.ln(8)

    assinatura_img = None
    if os.path.exists("assinatura_img.png"):
        assinatura_img = "assinatura_img.png"
    elif os.path.exists("assinatura_img.jpg"):
        assinatura_img = "assinatura_img.jpg"
    elif os.path.exists("assinatura_img.jpeg"):
        assinatura_img = "assinatura_img.jpeg"

    if assinatura_img:
        current_y = pdf.get_y()
        try:
            pdf.image(assinatura_img, x=80, y=current_y, w=50)
            pdf.ln(24)
        except Exception:
            pdf.cell(0, 8, "[Erro na imagem da assinatura]", 0, 1, "C")
    else:
        pdf.set_font("Helvetica", "B", 11)
        pdf.cell(0, 8, "_" * 40, 0, 1, "C")

    pdf.set_font("Helvetica", "B", 11)
    pdf.set_text_color(18, 30, 50)
    pdf.cell(0, 5, _pdf_safe_text(nome_prof), 0, 1, "C")
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(70, 80, 95)
    pdf.cell(0, 5, _pdf_safe_text(f"Nutricionista - Reg: {registro_prof}"), 0, 1, "C")
    pdf.ln(5)

    pdf_out = pdf.output(dest="S")
    if isinstance(pdf_out, bytes):
        return pdf_out
    if isinstance(pdf_out, bytearray):
        return bytes(pdf_out)
    return str(pdf_out).encode("latin-1")

def gerar_link_google(titulo, data, hora, desc):
    """Cria link de evento no Google Agenda."""
    try:
        data_str = str(data or "").strip()
        hora_str = str(hora or "").strip()
        if not data_str or not hora_str:
            return "#"
        if " " in data_str:
            data_str = data_str.split(" ")[0]
        if len(hora_str) >= 8:
            hora_str = hora_str[:8]
        elif len(hora_str) == 5:
            hora_str = f"{hora_str}:00"
        inicio = datetime.strptime(f"{data_str} {hora_str}", "%Y-%m-%d %H:%M:%S")
        fim = inicio + timedelta(hours=1)
        fmt = "%Y%m%dT%H%M%S"
        base = "https://calendar.google.com/calendar/render?action=TEMPLATE"
        return (
            f"{base}&text={urllib.parse.quote(titulo)}"
            f"&dates={inicio.strftime(fmt)}/{fim.strftime(fmt)}"
            f"&details={urllib.parse.quote(desc)}"
        )
    except Exception:
        return "#"

def ia_ok() -> bool:
    return bool(get_api_key())

# =============================================================================
# 7. MÓDULOS
def _dashboard_month_label(value):
    return _finance_parse_date(value).strftime("%Y-%m")


def _dashboard_currency(value):
    return _format_brl(value) if "_format_brl" in globals() else f"R$ {float(value or 0):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _dashboard_empty_state(title, text):
    st.markdown(
        f"""
        <div class="dh-admin-empty">
          <strong>{html.escape(title)}</strong>
          <span>{html.escape(text)}</span>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _dashboard_df_height(row_count: int, minimum: int = 148, maximum: int = 300) -> int:
    safe_rows = max(1, int(row_count or 0))
    return max(minimum, min(maximum, 52 + (safe_rows * 36)))


def modulo_dashboard():
    simple_mode = _dh_simple_mode_enabled()
    if st.session_state.get("tipo") == "admin":
        _refresh_users_cache()
    meus_pacientes = filtrar_por_usuario(pacientes)
    minha_agenda = filtrar_por_usuario(agenda)
    meu_financeiro = filtrar_por_usuario(_finance_all_entries() if "_finance_all_entries" in globals() else financeiro)
    hoje = datetime.now().date()
    inicio_mes = hoje.replace(day=1)

    pacientes_df = pd.DataFrame(meus_pacientes) if meus_pacientes else pd.DataFrame(columns=["nome", "data"])
    agenda_df = pd.DataFrame(minha_agenda) if minha_agenda else pd.DataFrame(columns=["paciente", "data"])
    financeiro_df = pd.DataFrame(meu_financeiro) if meu_financeiro else pd.DataFrame(
        columns=["descricao", "data", "valor", "tipo", "categoria", "status", "paciente"]
    )

    if not pacientes_df.empty:
        pacientes_data = pacientes_df["data"] if "data" in pacientes_df.columns else pd.Series([""] * len(pacientes_df), index=pacientes_df.index)
        pacientes_df["data_ref"] = pacientes_data.map(_finance_parse_date)
        pacientes_df["mes"] = pacientes_df["data_ref"].map(lambda d: d.strftime("%Y-%m"))
    if not agenda_df.empty:
        agenda_data = agenda_df["data"] if "data" in agenda_df.columns else pd.Series([""] * len(agenda_df), index=agenda_df.index)
        agenda_df["data_ref"] = agenda_data.map(_finance_parse_date)
        agenda_df["mes"] = agenda_df["data_ref"].map(lambda d: d.strftime("%Y-%m"))
    if not financeiro_df.empty:
        financeiro_data = financeiro_df["data"] if "data" in financeiro_df.columns else pd.Series([""] * len(financeiro_df), index=financeiro_df.index)
        financeiro_df["data_ref"] = financeiro_data.map(_finance_parse_date)
        financeiro_df["mes"] = financeiro_df["data_ref"].map(lambda d: d.strftime("%Y-%m"))
        financeiro_df["valor"] = financeiro_df["valor"].map(_finance_float)

    receitas_df = financeiro_df[financeiro_df.get("tipo", pd.Series(dtype=str)) == "Receita"].copy() if not financeiro_df.empty else pd.DataFrame()
    despesas_df = financeiro_df[financeiro_df.get("tipo", pd.Series(dtype=str)) == "Despesa"].copy() if not financeiro_df.empty else pd.DataFrame()

    receita_total = receitas_df["valor"].sum() if not receitas_df.empty else 0.0
    despesa_total = despesas_df["valor"].sum() if not despesas_df.empty else 0.0
    saldo_total = receita_total - despesa_total
    receita_mes = receitas_df.loc[receitas_df["data_ref"] >= inicio_mes, "valor"].sum() if not receitas_df.empty else 0.0
    despesa_mes = despesas_df.loc[despesas_df["data_ref"] >= inicio_mes, "valor"].sum() if not despesas_df.empty else 0.0
    saldo_mes = receita_mes - despesa_mes
    novos_pacientes_mes = len(pacientes_df[pacientes_df["data_ref"] >= inicio_mes]) if not pacientes_df.empty else 0
    atendimentos_mes = len(agenda_df[agenda_df["data_ref"] >= inicio_mes]) if not agenda_df.empty else 0
    pendencias = len([f for f in meu_financeiro if (f.get("status") or "").strip().title() == "Pendente"])
    vencidos = len([f for f in meu_financeiro if _finance_is_overdue(f)]) if "_finance_is_overdue" in globals() else 0
    ticket_medio = receita_total / max(1, len(receitas_df)) if len(receitas_df) else 0.0

    proximos_agendamentos = sorted(minha_agenda, key=lambda x: _finance_parse_date(x.get("data")))
    proximos_agendamentos = [a for a in proximos_agendamentos if _finance_parse_date(a.get("data")) >= hoje][:6]
    ultimos_pacientes = sorted(meus_pacientes, key=lambda x: _finance_parse_date(x.get("data")), reverse=True)[:6]
    ultimos_financeiros = sorted(meu_financeiro, key=lambda x: _finance_parse_date(x.get("data")), reverse=True)[:7]
    finance_rows = [
        {
            "Data": _finance_parse_date(item.get("data")).strftime("%d/%m/%Y"),
            "Descricao": item.get("descricao") or "-",
            "Tipo": item.get("tipo") or "-",
            "Status": item.get("status") or "-",
            "Valor": _dashboard_currency(item.get("valor")),
        }
        for item in ultimos_financeiros
    ]
    upcoming_rows = [
        {
            "Data": _finance_parse_date(item.get("data")).strftime("%d/%m/%Y"),
            "Hora": (item.get("hora") or "--:--").strip(),
            "Paciente": item.get("paciente") or "-",
            "Detalhe": item.get("anotacoes") or "Atendimento agendado",
        }
        for item in proximos_agendamentos
    ]
    recent_patient_rows = [
        {
            "Data": _finance_parse_date(item.get("data")).strftime("%d/%m/%Y"),
            "Paciente": item.get("nome") or "-",
            "Objetivo": item.get("objetivo") or "Cadastro recente",
        }
        for item in ultimos_pacientes
    ]

    header_icon = (
        '<svg viewBox="0 0 24 24">'
        '<path d="M4 19h16" />'
        '<path d="M7 15v-4" />'
        '<path d="M12 15V7" />'
        '<path d="M17 15v-2" />'
        '</svg>'
    )
    icon_pacientes = (
        '<svg viewBox="0 0 24 24">'
        '<path d="M16 19v-1.4a3.6 3.6 0 0 0-3.6-3.6H8.6A3.6 3.6 0 0 0 5 17.6V19" />'
        '<circle cx="10.5" cy="9.2" r="2.5" />'
        '<path d="M19 19v-1.2a3 3 0 0 0-2-2.8" />'
        '<path d="M15.9 6.8a2.1 2.1 0 1 1 0 4.2" />'
        '</svg>'
    )
    icon_agenda = (
        '<svg viewBox="0 0 24 24">'
        '<rect x="3.5" y="5" width="17" height="15" rx="2.4" />'
        '<path d="M8 3v4" />'
        '<path d="M16 3v4" />'
        '<path d="M3.5 10h17" />'
        '<path d="M8.5 13h7" />'
        '</svg>'
    )
    icon_biblioteca = (
        '<svg viewBox="0 0 24 24">'
        '<path d="M5 4.8h4v14.4H5z" />'
        '<path d="M10 4.8h4v14.4h-4z" />'
        '<path d="M15 4.8h4v14.4h-4z" />'
        '<path d="M4 19.2h16" />'
        '</svg>'
    )
    icon_receita = (
        '<svg viewBox="0 0 24 24">'
        '<rect x="3.5" y="6" width="17" height="12" rx="2.3" />'
        '<path d="M3.5 10h17" />'
        '<circle cx="16.8" cy="14" r="2.4" />'
        '</svg>'
    )

    st.markdown(
        _html_block(
            f"""
<section class="dh-admin-head">
  <div class="dh-admin-head-main">
    <div class="dh-admin-head-icon" aria-hidden="true">{header_icon}</div>
    <div class="dh-admin-head-copy">
      <h2>Painel de Controle</h2>
      <p>Leitura executiva do consult&oacute;rio com indicadores, crescimento, agenda e financeiro em uma vis&atilde;o &uacute;nica.</p>
    </div>
  </div>
  <div class="dh-admin-head-side">
    <div class="dh-admin-head-chip">Pacientes e agenda</div>
    <div class="dh-admin-head-chip">Financeiro consolidado</div>
    <div class="dh-admin-head-chip">Atividade recente</div>
  </div>
</section>
"""
        ),
        unsafe_allow_html=True,
    )

    if st.session_state.get("tipo") == "admin":
        now_dt = datetime.now()
        online_users = [
            x for x in users
            if (x.get("tipo") or "").strip().lower() != "admin" and _is_user_online(x, now_dt)
        ]
        if online_users:
            nomes_online = ", ".join(sorted((x.get("usuario") or "").strip() for x in online_users if x.get("usuario")))
            st.success(f"Usuários online agora ({len(online_users)}): {nomes_online}")
        else:
            st.caption("Nenhum usuário online agora.")

    cards = [
        ("Pacientes", str(len(meus_pacientes)), f"{novos_pacientes_mes} novos no mes", "metric-pacientes", icon_pacientes),
        ("Agendamentos", str(len(minha_agenda)), f"{atendimentos_mes} no mes atual", "metric-agenda", icon_agenda),
        ("Biblioteca", str(len(noticias)), "Conteudos e materiais", "metric-biblioteca", icon_biblioteca),
        ("Receita total", _dashboard_currency(receita_total), _dashboard_currency(receita_mes) + " no mes", "metric-receita", icon_receita),
        ("Despesas", _dashboard_currency(despesa_total), _dashboard_currency(despesa_mes) + " no mes", "metric-despesa", icon_receita),
        ("Saldo do mes", _dashboard_currency(saldo_mes), f"{pendencias} pendentes / {vencidos} vencidos", "metric-saldo", icon_receita),
        ("Ticket medio", _dashboard_currency(ticket_medio), "Media por receita registrada", "metric-ticket", icon_receita),
        ("Receita liquida", _dashboard_currency(saldo_total), "Historico acumulado", "metric-liquido", icon_receita),
    ]
    if simple_mode:
        cards = [
            ("Pacientes", str(len(meus_pacientes)), f"{novos_pacientes_mes} novos no mes", "metric-pacientes", icon_pacientes),
            ("Agendamentos", str(len(minha_agenda)), f"{atendimentos_mes} no mes atual", "metric-agenda", icon_agenda),
            ("Receita do mes", _dashboard_currency(receita_mes), f"{pendencias} pendentes", "metric-receita", icon_receita),
            ("Saldo do mes", _dashboard_currency(saldo_mes), f"{vencidos} vencidos", "metric-saldo", icon_receita),
        ]
    cards_html = "".join(
        f"""
  <article class="metric-container {klass}">
    <div class="metric-top"><span class="metric-icon" aria-hidden="true">{icon}</span></div>
    <div class="metric-value">{html.escape(value)}</div>
    <div class="metric-label">{html.escape(label)}</div>
    <div class="metric-note">{html.escape(note)}</div>
  </article>
"""
        for label, value, note, klass, icon in cards
    )

    st.markdown(
        _html_block(
            f"""
<section class="dh-admin-kpi-grid dh-admin-kpi-grid--rich">
{cards_html}
</section>
<div class="dh-admin-divider" aria-hidden="true"></div>
"""
        ),
        unsafe_allow_html=True,
    )

    if simple_mode:
        st.info("Modo simples ativo: painel reduzido para visão rápida do dia, com foco em pacientes, agenda e financeiro essencial.")
        col_left, col_right = st.columns([1.08, 0.92], gap="large")
        with col_left:
            with st.container(key="dh_dashboard_simple_upcoming_shell"):
                st.markdown('<div class="dh-admin-panel-title">Próximos agendamentos</div>', unsafe_allow_html=True)
                if upcoming_rows:
                    st.dataframe(
                        pd.DataFrame(upcoming_rows),
                        use_container_width=True,
                        hide_index=True,
                        height=_dashboard_df_height(len(upcoming_rows), minimum=188, maximum=292),
                    )
                else:
                    _dashboard_empty_state("Sem agenda futura", "Quando houver atendimentos programados, eles aparecerão aqui.")
            with st.container(key="dh_dashboard_simple_recent_shell"):
                st.markdown('<div class="dh-admin-panel-title">Pacientes recentes</div>', unsafe_allow_html=True)
                if recent_patient_rows:
                    st.dataframe(
                        pd.DataFrame(recent_patient_rows),
                        use_container_width=True,
                        hide_index=True,
                        height=_dashboard_df_height(len(recent_patient_rows), minimum=188, maximum=292),
                    )
                else:
                    _dashboard_empty_state("Nenhum paciente cadastrado", "Os pacientes mais recentes aparecerão aqui.")
        with col_right:
            with st.container(key="dh_dashboard_simple_activity_shell"):
                st.markdown('<div class="dh-admin-panel-title">Atividade recente</div>', unsafe_allow_html=True)
                activity_rows = []
                for p in ultimos_pacientes[:4]:
                    activity_rows.append(
                        {"Data": _finance_parse_date(p.get("data")).strftime("%d/%m/%Y"), "Tipo": "Paciente", "Descricao": p.get("nome") or "-", "Detalhe": p.get("objetivo") or "Novo cadastro"}
                    )
                for a in proximos_agendamentos[:4]:
                    activity_rows.append(
                        {"Data": _finance_parse_date(a.get("data")).strftime("%d/%m/%Y"), "Tipo": "Agenda", "Descricao": a.get("paciente") or "-", "Detalhe": a.get("hora") or "Atendimento programado"}
                    )
                if activity_rows:
                    st.dataframe(
                        pd.DataFrame(activity_rows).sort_values("Data", ascending=False),
                        use_container_width=True,
                        hide_index=True,
                        height=_dashboard_df_height(len(activity_rows), minimum=236, maximum=396),
                    )
                else:
                    _dashboard_empty_state("Sem atividade recente", "O sistema exibirá movimentações conforme a rotina for usada.")
            with st.container(key="dh_dashboard_simple_shortcuts_shell"):
                st.markdown('<div class="dh-admin-panel-title">Atalhos essenciais</div>', unsafe_allow_html=True)
                st.markdown(
                    _html_block(
                        """
                        <div class="dh-admin-summary-card">
                          <div class="dh-admin-inline-stat"><span>Agenda</span><strong>Confirmar consultas e encaixes</strong></div>
                          <div class="dh-admin-inline-stat"><span>Atendimento</span><strong>Cadastrar e localizar paciente</strong></div>
                          <div class="dh-admin-inline-stat"><span>Consultório</span><strong>Avaliação e anamnese</strong></div>
                          <div class="dh-admin-inline-stat"><span>Gerar Dieta</span><strong>Plano alimentar com agilidade</strong></div>
                        </div>
                        """
                    ),
                    unsafe_allow_html=True,
                )
        return

    if not financeiro_df.empty:
        monthly_fin = (
            financeiro_df.groupby(["mes", "tipo"], dropna=False)["valor"]
            .sum()
            .reset_index()
            .pivot(index="mes", columns="tipo", values="valor")
            .fillna(0)
            .reset_index()
            .sort_values("mes")
        )
        monthly_fin["Saldo"] = monthly_fin.get("Receita", 0) - monthly_fin.get("Despesa", 0)
        fig_fin = px.line(
            monthly_fin,
            x="mes",
            y=[c for c in ["Receita", "Despesa", "Saldo"] if c in monthly_fin.columns],
            markers=True,
            title="Evolucao financeira por mes",
            color_discrete_map={"Receita": "#38bdf8", "Despesa": "#fb7185", "Saldo": "#22c55e"},
        )
        fig_fin.update_layout(
            height=318,
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            legend_title_text="",
            margin=dict(l=10, r=10, t=52, b=10),
            xaxis_title="",
            yaxis_title="Valor",
            font=dict(color="#dbeafe"),
        )
    else:
        fig_fin = None

    if not pacientes_df.empty or not agenda_df.empty:
        growth_rows = []
        if not pacientes_df.empty:
            growth_rows.append(
                pacientes_df.groupby("mes").size().reset_index(name="Total").assign(Indicador="Pacientes")
            )
        if not agenda_df.empty:
            growth_rows.append(
                agenda_df.groupby("mes").size().reset_index(name="Total").assign(Indicador="Agendamentos")
            )
        growth_df = pd.concat(growth_rows, ignore_index=True).sort_values("mes") if growth_rows else pd.DataFrame()
        fig_growth = px.bar(
            growth_df,
            x="mes",
            y="Total",
            color="Indicador",
            barmode="group",
            title="Crescimento de pacientes e atendimentos",
            color_discrete_map={"Pacientes": "#60a5fa", "Agendamentos": "#34d399"},
        )
        fig_growth.update_layout(
            height=318,
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            legend_title_text="",
            margin=dict(l=10, r=10, t=52, b=10),
            xaxis_title="",
            yaxis_title="Volume",
            font=dict(color="#dbeafe"),
        )
    else:
        fig_growth = None

    category_df = pd.DataFrame()
    if not financeiro_df.empty:
        category_df = (
            financeiro_df.groupby(["categoria", "tipo"], dropna=False)["valor"]
            .sum()
            .reset_index()
            .sort_values("valor", ascending=False)
        )

    finance_summary_html = "".join(
        f"""
        <tr>
          <td>
            <span class="dh-admin-fin-label">{html.escape(label)}</span>
            <span class="dh-admin-fin-note">{html.escape(note)}</span>
          </td>
          <td>{html.escape(total)}</td>
          <td>{html.escape(period)}</td>
        </tr>
        """
        for label, total, period, note in [
            ("Receitas", _dashboard_currency(receita_total), _dashboard_currency(receita_mes), "Total acumulado e valor do mes atual."),
            ("Despesas", _dashboard_currency(despesa_total), _dashboard_currency(despesa_mes), "Saidas registradas no historico financeiro."),
            ("Saldo", _dashboard_currency(saldo_total), _dashboard_currency(saldo_mes), "Resultado consolidado e saldo do mes."),
        ]
    )

    top_left, top_right = st.columns([1.12, 0.88], gap="large")
    with top_left:
        with st.container(key="dh_dashboard_chart_growth_shell"):
            st.markdown('<div class="dh-admin-panel-title">Crescimento operacional</div>', unsafe_allow_html=True)
            if fig_growth is None:
                _dashboard_empty_state("Sem base historica suficiente", "Cadastre pacientes e agendamentos para acompanhar crescimento e volume de atendimento.")
            else:
                st.plotly_chart(fig_growth, use_container_width=True, config={"displayModeBar": False})

        with st.container(key="dh_dashboard_finance_rows_shell_bottom"):
            st.markdown('<div class="dh-admin-panel-title">Ultimos lancamentos</div>', unsafe_allow_html=True)
            if finance_rows:
                st.dataframe(
                    pd.DataFrame(finance_rows),
                    use_container_width=True,
                    hide_index=True,
                    height=_dashboard_df_height(len(finance_rows), minimum=172, maximum=280),
                )
            else:
                _dashboard_empty_state("Sem lancamentos recentes", "O historico financeiro recente sera exibido aqui.")

        with st.container(key="dh_dashboard_upcoming_shell"):
            st.markdown('<div class="dh-admin-panel-title">Proximos agendamentos</div>', unsafe_allow_html=True)
            if upcoming_rows:
                st.dataframe(
                    pd.DataFrame(upcoming_rows),
                    use_container_width=True,
                    hide_index=True,
                    height=_dashboard_df_height(len(upcoming_rows), minimum=168, maximum=268),
                )
            else:
                _dashboard_empty_state("Sem agenda futura", "Quando houver atendimentos programados, eles aparecerao aqui.")

    with top_right:
        with st.container(key="dh_dashboard_fin_summary_shell"):
            st.markdown('<div class="dh-admin-panel-title">Receitas, despesas e saldo</div>', unsafe_allow_html=True)
            if financeiro_df.empty:
                _dashboard_empty_state("Sem movimentacoes financeiras", "Registre receitas ou despesas para preencher esta leitura financeira.")
            else:
                st.markdown(
                    _html_block(
                        f"""
                        <div class="dh-admin-fin-table-wrap">
                          <table class="dh-admin-fin-table">
                            <thead>
                              <tr>
                                <th>Indicador</th>
                                <th>Acumulado</th>
                                <th>Mes atual</th>
                              </tr>
                            </thead>
                            <tbody>
                              {finance_summary_html}
                            </tbody>
                          </table>
                        </div>
                        """
                    ),
                    unsafe_allow_html=True,
                )

        with st.container(key="dh_dashboard_category_shell"):
            st.markdown('<div class="dh-admin-panel-title">Analise por categoria financeira</div>', unsafe_allow_html=True)
            if not category_df.empty:
                fig_cat = px.bar(
                    category_df,
                    x="valor",
                    y="categoria",
                    color="tipo",
                    orientation="h",
                    barmode="group",
                    title="Categorias com maior impacto",
                    color_discrete_map={"Receita": "#22c55e", "Despesa": "#f97316"},
                )
                fig_cat.update_layout(
                    height=284,
                    paper_bgcolor="rgba(0,0,0,0)",
                    plot_bgcolor="rgba(0,0,0,0)",
                    legend_title_text="",
                    margin=dict(l=10, r=10, t=52, b=10),
                    xaxis_title="Valor",
                    yaxis_title="",
                    font=dict(color="#dbeafe"),
                )
                st.plotly_chart(fig_cat, use_container_width=True, config={"displayModeBar": False})
            else:
                _dashboard_empty_state("Sem categorias para analisar", "O painel mostrara origem das receitas e destino das despesas conforme o financeiro for utilizado.")

        with st.container(key="dh_dashboard_summary_shell"):
            st.markdown('<div class="dh-admin-panel-title">Resumo operacional</div>', unsafe_allow_html=True)
            summary_items = [
                ("Novos pacientes no mes", str(novos_pacientes_mes)),
                ("Atendimentos no mes", str(atendimentos_mes)),
                ("Pendencias financeiras", str(pendencias)),
                ("Lancamentos vencidos", str(vencidos)),
                ("Conteudos salvos", str(len(noticias))),
                ("Saldo acumulado", _dashboard_currency(saldo_total)),
            ]
            summary_html = "".join(
                f'<div class="dh-admin-inline-stat"><span>{html.escape(label)}</span><strong>{html.escape(value)}</strong></div>'
                for label, value in summary_items
            )
            st.markdown(f'<div class="dh-admin-summary-card">{summary_html}</div>', unsafe_allow_html=True)

    bottom_left, bottom_right = st.columns([0.92, 1.08], gap="large")
    with bottom_left:
        with st.container(key="dh_dashboard_recent_patients_shell"):
            st.markdown('<div class="dh-admin-panel-title">Ultimos pacientes cadastrados</div>', unsafe_allow_html=True)
            if recent_patient_rows:
                st.dataframe(
                    pd.DataFrame(recent_patient_rows),
                    use_container_width=True,
                    hide_index=True,
                    height=_dashboard_df_height(len(recent_patient_rows), minimum=208, maximum=300),
                )
            else:
                _dashboard_empty_state("Nenhum paciente cadastrado", "Os pacientes mais recentes aparecerao aqui para consulta rapida.")

    with bottom_right:
        with st.container(key="dh_dashboard_activity_shell"):
            st.markdown('<div class="dh-admin-panel-title">Atividade recente</div>', unsafe_allow_html=True)
            activity_rows = []
            for p in ultimos_pacientes[:3]:
                activity_rows.append(
                    {"Data": _finance_parse_date(p.get("data")).strftime("%d/%m/%Y"), "Tipo": "Paciente", "Descricao": p.get("nome") or "-", "Detalhe": p.get("objetivo") or "Novo cadastro"}
                )
            for a in proximos_agendamentos[:3]:
                activity_rows.append(
                    {"Data": _finance_parse_date(a.get("data")).strftime("%d/%m/%Y"), "Tipo": "Agenda", "Descricao": a.get("paciente") or "-", "Detalhe": a.get("hora") or "Atendimento programado"}
                )
            for f in ultimos_financeiros[:3]:
                activity_rows.append(
                    {"Data": _finance_parse_date(f.get("data")).strftime("%d/%m/%Y"), "Tipo": f.get("tipo") or "Financeiro", "Descricao": f.get("descricao") or "-", "Detalhe": _dashboard_currency(f.get("valor"))}
                )
            if activity_rows:
                activity_df = pd.DataFrame(activity_rows).sort_values("Data", ascending=False)
                st.dataframe(
                    activity_df,
                    use_container_width=True,
                    hide_index=True,
                    height=_dashboard_df_height(len(activity_rows), minimum=208, maximum=300),
                )
            else:
                _dashboard_empty_state("Sem atividade recente", "O sistema exibira movimentacoes recentes conforme pacientes, agenda e financeiro forem utilizados.")

def modulo_agenda_pro():
    with st.container(key="agenda_soft_wrap"):
        st.markdown(
            """
<style>
div[class*="st-key-agenda_soft_wrap"] [data-baseweb="tab-list"]{ gap: 8px; }
div[class*="st-key-agenda_soft_wrap"] [data-baseweb="tab"]{
  border-radius: 12px;
  transition: all .2s ease;
  padding: 8px 14px;
}
div[class*="st-key-agenda_soft_wrap"] [aria-selected="true"]{
  background: rgba(82,224,180,.12) !important;
}
div[class*="st-key-agenda_soft_wrap"] .stTextInput input,
div[class*="st-key-agenda_soft_wrap"] .stNumberInput input,
div[class*="st-key-agenda_soft_wrap"] .stDateInput input,
div[class*="st-key-agenda_soft_wrap"] .stTimeInput input,
div[class*="st-key-agenda_soft_wrap"] .stTextArea textarea,
div[class*="st-key-agenda_soft_wrap"] div[data-baseweb="select"] input{
  border-radius: 12px !important;
  border: 1px solid rgba(148,163,184,.28) !important;
  background: rgba(248,250,252,.98) !important;
  color: #081423 !important;
  transition: all .2s ease !important;
}
div[class*="st-key-agenda_soft_wrap"] div[data-baseweb="select"] > div,
div[class*="st-key-agenda_soft_wrap"] .stDateInput > div > div,
div[class*="st-key-agenda_soft_wrap"] .stTimeInput > div > div{
  background: rgba(248,250,252,.98) !important;
  color: #081423 !important;
}
div[class*="st-key-agenda_soft_wrap"] .stTextInput input::placeholder,
div[class*="st-key-agenda_soft_wrap"] .stTextArea textarea::placeholder{
  color: #64748b !important;
}
div[class*="st-key-agenda_soft_wrap"] .stTextInput input:focus,
div[class*="st-key-agenda_soft_wrap"] .stNumberInput input:focus,
div[class*="st-key-agenda_soft_wrap"] .stDateInput input:focus,
div[class*="st-key-agenda_soft_wrap"] .stTimeInput input:focus,
div[class*="st-key-agenda_soft_wrap"] .stTextArea textarea:focus,
div[class*="st-key-agenda_soft_wrap"] div[data-baseweb="select"] input:focus{
  border-color: #52e0b4 !important;
  box-shadow: 0 0 0 2px rgba(82,224,180,.15) !important;
}
div[class*="st-key-agenda_soft_wrap"] label{font-weight: 600;}
div[class*="st-key-agenda_soft_wrap"] .stForm button[kind="primary"],
div[class*="st-key-agenda_soft_wrap"] button[kind="secondaryFormSubmit"]{
  color:#f8fbff !important;
  font-weight:800 !important;
}
.dh-agenda-hero{display:grid;grid-template-columns:minmax(0,2.2fr) minmax(280px,1fr);gap:18px;padding:24px;border-radius:24px;border:1px solid rgba(82,224,180,.14);background:linear-gradient(135deg, rgba(10,20,37,.98), rgba(16,33,58,.94));box-shadow:0 24px 48px rgba(0,0,0,.28);margin-bottom:18px;}
.dh-agenda-hero h2{margin:0;color:#f7fbff;font-size:2.1rem;font-weight:800;letter-spacing:-0.03em;}
.dh-agenda-hero p{margin:10px 0 0;color:#b7c9dd;line-height:1.6;max-width:780px;}
.dh-agenda-pill-row{display:flex;flex-wrap:wrap;gap:10px;margin-top:18px;}
.dh-agenda-pill{padding:8px 12px;border-radius:999px;border:1px solid rgba(87,223,179,.18);background:rgba(17,34,58,.88);color:#dffcf2;font-size:.82rem;font-weight:700;}
.dh-agenda-kpis{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px;}
.dh-agenda-kpi{padding:15px 16px;border-radius:18px;background:rgba(10,20,36,.82);border:1px solid rgba(255,255,255,.06);min-height:96px;}
.dh-agenda-kpi strong{display:block;color:#ffffff;font-size:1.25rem;margin-bottom:4px;}
.dh-agenda-kpi span{display:block;color:#9ab2ca;font-size:.86rem;line-height:1.45;}
.dh-agenda-panel{border-radius:22px;padding:18px;background:linear-gradient(180deg, rgba(15,26,46,.97), rgba(11,19,35,.97));border:1px solid rgba(255,255,255,.06);box-shadow:0 20px 36px rgba(0,0,0,.2);}
.dh-agenda-panel h4{margin:0 0 10px;color:#f4f8ff;font-size:1.05rem;font-weight:800;}
.dh-agenda-panel p{margin:0;color:#b8c8d8;line-height:1.58;}
.dh-agenda-mini{padding:14px;border-radius:18px;background:rgba(11,23,40,.76);border:1px solid rgba(255,255,255,.06);height:100%;}
.dh-agenda-mini strong{display:block;color:#f7fbff;margin-bottom:6px;font-size:.98rem;}
.dh-agenda-mini span{display:block;color:#9eb5cc;font-size:.88rem;line-height:1.48;}
.dh-agenda-empty{border:1px dashed rgba(255,255,255,.12);background:rgba(10,20,36,.7);border-radius:18px;padding:18px;color:#a8bdd3;}
.dh-agenda-autofill{padding:14px 16px;border-radius:18px;background:linear-gradient(180deg, rgba(17,34,58,.92), rgba(11,24,40,.88));border:1px solid rgba(82,224,180,.16);margin-bottom:12px;}
.dh-agenda-autofill strong{display:block;color:#f7fbff;font-size:1rem;margin-bottom:6px;}
.dh-agenda-autofill span{display:block;color:#bfd0e2;font-size:.88rem;line-height:1.55;}
@media (max-width:980px){.dh-agenda-hero{grid-template-columns:1fr;}.dh-agenda-kpis{grid-template-columns:1fr 1fr;}}
@media (max-width:760px){.dh-agenda-kpis{grid-template-columns:1fr;}}
</style>
            """,
            unsafe_allow_html=True,
        )

        meus_pacientes = filtrar_por_usuario(pacientes)
        minha_agenda = filtrar_por_usuario(agenda)
        hoje = datetime.now().date()
        inicio_mes = hoje.replace(day=1)

        agenda_df = pd.DataFrame(minha_agenda) if minha_agenda else pd.DataFrame(columns=["paciente", "data", "hora", "obs", "tipo", "idade", "sexo"])
        if not agenda_df.empty:
            agenda_df["data_ref"] = agenda_df["data"].map(_finance_parse_date)
            agenda_df["mes"] = agenda_df["data_ref"].map(lambda d: d.strftime("%Y-%m"))
        total_agendamentos = len(minha_agenda)
        agendamentos_mes = len(agenda_df[agenda_df["data_ref"] >= inicio_mes]) if not agenda_df.empty else 0
        agendamentos_hoje = len(agenda_df[agenda_df["data_ref"] == hoje]) if not agenda_df.empty else 0
        proximos = sorted(minha_agenda, key=lambda x: (_finance_parse_date(x.get("data")), _fmt_hora_str(x.get("hora"))))
        proximos = [a for a in proximos if _finance_parse_date(a.get("data")) >= hoje]
        proximos_7 = [a for a in proximos if (_finance_parse_date(a.get("data")) - hoje).days <= 7]
        sem_cadastro = sum(1 for a in minha_agenda if not any(p.get("nome") == a.get("paciente") for p in meus_pacientes))

        st.markdown(
            f"""
            <div class="dh-agenda-hero">
              <div>
                <h2>Agenda inteligente</h2>
                <p>Gerencie consultas, acompanhe a carga da semana e registre novos atendimentos em um fluxo unico. A agenda continua integrada ao Google Agenda e ao envio por WhatsApp.</p>
                <div class="dh-agenda-pill-row">
                  <div class="dh-agenda-pill">{total_agendamentos} agendamentos cadastrados</div>
                  <div class="dh-agenda-pill">{agendamentos_mes} no mes atual</div>
                  <div class="dh-agenda-pill">{agendamentos_hoje} para hoje</div>
                  <div class="dh-agenda-pill">Google Agenda + WhatsApp</div>
                </div>
              </div>
              <div class="dh-agenda-kpis">
                <div class="dh-agenda-kpi"><strong>{len(proximos_7)}</strong><span>atendimentos programados para os proximos 7 dias</span></div>
                <div class="dh-agenda-kpi"><strong>{len(meus_pacientes)}</strong><span>pacientes disponiveis para agendamento rapido</span></div>
                <div class="dh-agenda-kpi"><strong>{sem_cadastro}</strong><span>agendamentos sem paciente vinculado no cadastro</span></div>
                <div class="dh-agenda-kpi"><strong>{_fmt_data_br(str(proximos[0].get('data'))) if proximos else '--/--/----'}</strong><span>proximo atendimento planejado</span></div>
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        t1, t2 = st.tabs(["Novo Agendamento", "Visualizar Agenda"])
        with t1:
            main_col, side_col = st.columns([1.5, 1], gap="large")
            with main_col:
                with st.container(key="agenda_soft_form_card"):
                    st.markdown('<div class="dh-agenda-panel"><h4>Novo agendamento</h4><p>Cadastre consultas rapidamente, aproveitando dados do paciente ja salvo sempre que possivel.</p></div>', unsafe_allow_html=True)
                    with st.form("ag"):
                        nm = st.selectbox("Paciente", ["-- Novo --"] + [p["nome"] for p in meus_pacientes])
                        pac_sel = next((p for p in meus_pacientes if p.get("nome") == nm), None) if nm != "-- Novo --" else None
                        nome_novo = ""
                        if nm == "-- Novo --":
                            nome_novo = st.text_input("Nome do paciente")
                        else:
                            idade_ag_default = 0
                            if pac_sel and pac_sel.get("idade") not in (None, ""):
                                try:
                                    idade_ag_default = int(float(pac_sel.get("idade")))
                                except Exception:
                                    idade_ag_default = 0
                            sexo_ag_default = (pac_sel.get("sexo") or "") if pac_sel else ""
                            telefone_ag_default = (pac_sel.get("telefone") or "") if pac_sel else ""
                            email_ag_default = (pac_sel.get("email") or "") if pac_sel else ""
                            st.markdown(
                                f"""
                                <div class="dh-agenda-autofill">
                                  <strong>Dados carregados automaticamente</strong>
                                  <span><b>Paciente:</b> {html.escape(pac_sel.get("nome") or "Paciente")}<br>
                                  <b>Idade:</b> {idade_ag_default or "--"}<br>
                                  <b>Sexo:</b> {html.escape(sexo_ag_default or "--")}<br>
                                  <b>WhatsApp:</b> {html.escape(telefone_ag_default or "--")}<br>
                                  <b>E-mail:</b> {html.escape(email_ag_default or "--")}</span>
                                </div>
                                """,
                                unsafe_allow_html=True,
                            )

                        idade_ag_default = 0
                        if pac_sel and pac_sel.get("idade") not in (None, ""):
                            try:
                                idade_ag_default = int(float(pac_sel.get("idade")))
                            except Exception:
                                idade_ag_default = 0
                        sexo_ag_default = (pac_sel.get("sexo") or "") if pac_sel else ""
                        sexo_ag_index = 0
                        if sexo_ag_default:
                            sexo_ag_index = 1 if sexo_ag_default.strip().lower().startswith("m") else 2

                        telefone_ag_default = (pac_sel.get("telefone") or "") if pac_sel else ""
                        email_ag_default = (pac_sel.get("email") or "") if pac_sel else ""

                        if nm == "-- Novo --":
                            c_name1, c_name2 = st.columns([1, 1])
                            idade_ag = c_name1.number_input("Idade (opcional)", min_value=0, max_value=120, value=idade_ag_default)
                            sexo_ag = c_name2.selectbox("Sexo (opcional)", ["", "Masculino", "Feminino"], index=sexo_ag_index)
                        else:
                            idade_ag = idade_ag_default
                            sexo_ag = sexo_ag_default

                        c_date, c_time = st.columns(2)
                        dt = c_date.date_input("Data")
                        hr = c_time.time_input("Hora")
                        obs = st.text_area("Observacoes do atendimento", height=140, placeholder="Ex: retorno, foco em perda de peso, paciente pediu encaixe...")
                        nutricionista_nome = (st.session_state.get("usuario") or "Nutricionista").strip() or "Nutricionista"
                        p_nome_preview = nm if nm != "-- Novo --" else (nome_novo.strip() or "Paciente")
                        msg_agendamento = (
                            f"Ola {p_nome_preview}, tudo bem?\n\n"
                            f"Sua consulta com a nutricionista {nutricionista_nome} foi agendada com sucesso.\n"
                            f"Data: {_fmt_data_br(str(dt))}\n"
                            f"Hora: {_fmt_hora_str(str(hr))}\n"
                            f"Paciente: {p_nome_preview}\n"
                        )
                        if obs.strip():
                            msg_agendamento += f"Observacoes: {obs.strip()}\n"
                        msg_agendamento += "\nQualquer necessidade, me avise."

                        if nm != "-- Novo --":
                            st.text_area("Mensagem pronta para o paciente", value=msg_agendamento, height=170, disabled=True)
                        if st.form_submit_button("Salvar na Agenda", use_container_width=True):
                            p_nome = nm if nm != "-- Novo --" else (nome_novo.strip() or "Novo")
                            if p_nome != "Novo":
                                dono = (st.session_state.get("usuario") or "").strip().lower()
                                p_exist = next((p for p in pacientes if p.get("nome") == p_nome and (p.get("dono") or "").strip().lower() == dono), None)
                                if p_exist:
                                    if idade_ag:
                                        p_exist["idade"] = int(idade_ag)
                                    if sexo_ag:
                                        p_exist["sexo"] = sexo_ag
                                else:
                                    pacientes.append({
                                        "dono": dono,
                                        "nome": p_nome,
                                        "email": "",
                                        "telefone": "",
                                        "idade": int(idade_ag) if idade_ag else None,
                                        "cpf": "",
                                        "documento": "",
                                        "sexo": sexo_ag,
                                        "cidade": "",
                                        "codigo_paciente": _generate_patient_portal_code(),
                                        "status_acesso_portal": "nao_ativado",
                                        "anamnese": _blank_anamnese(),
                                        "historico": []
                                    })
                                save_db("pacientes.json", pacientes)

                            agenda.append({
                                "dono": st.session_state["usuario"],
                                "paciente": p_nome,
                                "data": str(dt),
                                "hora": str(hr),
                                "obs": obs,
                                "tipo": "Consulta",
                                "idade": int(idade_ag) if idade_ag else None,
                                "sexo": sexo_ag,
                                "telefone": (pac_sel.get("telefone") if pac_sel else ""),
                                "email": (pac_sel.get("email") if pac_sel else ""),
                            })
                            save_db("agenda.json", agenda)
                            lnk = gerar_link_google(f"Consulta - {p_nome}", str(dt), str(hr), obs)
                            st.success("Agendado com sucesso!")
                            if lnk and lnk != "#":
                                st.markdown(f'<a href="{lnk}" target="_blank" class="dh-pill">Adicionar ao Google Agenda</a>', unsafe_allow_html=True)
                            else:
                                st.warning("Nao foi possivel gerar o link do Google Agenda para este horario. Revise a data e a hora.")

                            tel_wa_form = _wa_normalize_to_send((pac_sel.get("telefone") if pac_sel else ""))
                            if tel_wa_form:
                                wa_form = _wa_link(tel_wa_form, msg_agendamento)
                                if wa_form:
                                    st.markdown(f'<a class="dh-btn dh-btn-green" href="{wa_form}" target="_blank">Enviar agendamento para o paciente</a>', unsafe_allow_html=True)
                            elif nm != "-- Novo --":
                                st.caption("Paciente sem WhatsApp cadastrado. Atualize o telefone para habilitar o envio rapido.")

            with side_col:
                st.markdown('<div class="dh-agenda-panel"><h4>Resumo rapido da agenda</h4><p>Use este painel para avaliar a ocupacao da semana e localizar gargalos de agenda antes que virem retrabalho.</p></div>', unsafe_allow_html=True)
                st.write("")
                mini1, mini2 = st.columns(2)
                mini1.markdown(f'<div class="dh-agenda-mini"><strong>Hoje</strong><span>{agendamentos_hoje} atendimento(s) programados para o dia.</span></div>', unsafe_allow_html=True)
                mini2.markdown(f'<div class="dh-agenda-mini"><strong>Semana</strong><span>{len(proximos_7)} agenda(s) previstas nos proximos 7 dias.</span></div>', unsafe_allow_html=True)
                st.write("")
                st.markdown("#### Proximos atendimentos")
                if proximos[:5]:
                    for item in proximos[:5]:
                        st.markdown(
                            f'<div class="dh-agenda-mini" style="margin-bottom:10px;"><strong>{item.get("paciente") or "Paciente"}</strong><span>{_fmt_data_br(item.get("data"))} as {_fmt_hora_str(item.get("hora"))}<br>{(item.get("obs") or "Sem observacoes")[:90]}</span></div>',
                            unsafe_allow_html=True,
                        )
                else:
                    st.markdown('<div class="dh-agenda-empty">Sem atendimentos futuros cadastrados. Crie um novo agendamento para iniciar o fluxo.</div>', unsafe_allow_html=True)

        with t2:
            filter_col1, filter_col2, filter_col3 = st.columns([1.3, 1, 1])
            busca_agenda = filter_col1.text_input("Buscar paciente ou observacao", key="agenda_busca", placeholder="Ex: Maria, retorno, encaixe...")
            periodo = filter_col2.selectbox("Periodo", ["Todos", "Hoje", "Proximos 7 dias", "Este mes", "Atrasados"], key="agenda_periodo")
            ordenacao = filter_col3.selectbox("Ordenar por", ["Mais proximos", "Mais recentes", "Paciente A-Z"], key="agenda_ordenacao")

            agenda_filtrada = list(minha_agenda)
            termo = (busca_agenda or "").strip().lower()
            if termo:
                agenda_filtrada = [
                    item for item in agenda_filtrada
                    if termo in " ".join([
                        str(item.get("paciente") or ""),
                        str(item.get("obs") or ""),
                        str(item.get("hora") or ""),
                    ]).lower()
                ]

            if periodo == "Hoje":
                agenda_filtrada = [item for item in agenda_filtrada if _finance_parse_date(item.get("data")) == hoje]
            elif periodo == "Proximos 7 dias":
                agenda_filtrada = [item for item in agenda_filtrada if 0 <= (_finance_parse_date(item.get("data")) - hoje).days <= 7]
            elif periodo == "Este mes":
                agenda_filtrada = [item for item in agenda_filtrada if _finance_parse_date(item.get("data")) >= inicio_mes]
            elif periodo == "Atrasados":
                agenda_filtrada = [item for item in agenda_filtrada if _finance_parse_date(item.get("data")) < hoje]

            if ordenacao == "Mais proximos":
                agenda_filtrada = sorted(agenda_filtrada, key=lambda x: (_finance_parse_date(x.get("data")), _fmt_hora_str(x.get("hora"))))
            elif ordenacao == "Mais recentes":
                agenda_filtrada = sorted(agenda_filtrada, key=lambda x: (_finance_parse_date(x.get("data")), _fmt_hora_str(x.get("hora"))), reverse=True)
            else:
                agenda_filtrada = sorted(agenda_filtrada, key=lambda x: str(x.get("paciente") or "").lower())

            agenda_mes_ref = st.date_input("Mes de referencia da agenda", value=hoje, key="agenda_mes_ref")
            ano_cal = agenda_mes_ref.year
            mes_cal = agenda_mes_ref.month
            eventos_mes = [item for item in agenda_filtrada if _finance_parse_date(item.get("data")).year == ano_cal and _finance_parse_date(item.get("data")).month == mes_cal]
            eventos_por_dia = {}
            for item in eventos_mes:
                dia = _finance_parse_date(item.get("data")).day
                eventos_por_dia.setdefault(dia, []).append(item)

            cal_rows = []
            for week in calendar.monthcalendar(ano_cal, mes_cal):
                row_cells = []
                for day in week:
                    if day == 0:
                        row_cells.append('<td class="dh-cal-empty"></td>')
                        continue
                    items_day = sorted(eventos_por_dia.get(day, []), key=lambda x: _fmt_hora_str(x.get("hora")))
                    badges = "".join(
                        f"<div class='dh-cal-item'><strong>{html.escape(_fmt_hora_str(it.get('hora')))}</strong> {html.escape((it.get('paciente') or 'Paciente')[:18])}</div>"
                        for it in items_day[:3]
                    )
                    more_tag = f"<div class='dh-cal-more'>+{len(items_day)-3} mais</div>" if len(items_day) > 3 else ""
                    row_cells.append(
                        f"<td class='dh-cal-cell'><div class='dh-cal-day'>{day}</div>{badges}{more_tag}</td>"
                    )
                cal_rows.append("<tr>" + "".join(row_cells) + "</tr>")

            st.markdown(
                f"""
                <style>
                .dh-cal-wrap{{border-radius:22px;padding:18px;background:linear-gradient(180deg, rgba(18,33,58,.98), rgba(15,28,50,.96));border:1px solid rgba(147,197,253,.12);box-shadow:0 20px 36px rgba(0,0,0,.2);}}
                .dh-cal-head{{display:flex;justify-content:space-between;align-items:center;gap:12px;margin-bottom:14px;}}
                .dh-cal-head h4{{margin:0;color:#f4f8ff;font-size:1.05rem;font-weight:800;}}
                .dh-cal-table{{width:100%;border-collapse:separate;border-spacing:8px;table-layout:fixed;}}
                .dh-cal-table th{{color:#d7e5f6;font-size:.78rem;font-weight:800;text-transform:uppercase;padding-bottom:4px;}}
                .dh-cal-cell,.dh-cal-empty{{vertical-align:top;min-height:110px;height:110px;border-radius:18px;padding:10px;background:rgba(25,42,70,.84);border:1px solid rgba(203,213,225,.1);}}
                .dh-cal-empty{{background:rgba(18,31,52,.5);border-style:dashed;}}
                .dh-cal-day{{color:#ffffff;font-weight:900;margin-bottom:8px;}}
                .dh-cal-item{{font-size:.76rem;line-height:1.35;color:#eff8ff;padding:5px 8px;border-radius:12px;background:rgba(34,197,94,.16);border:1px solid rgba(134,239,172,.24);margin-bottom:6px;}}
                .dh-cal-item strong{{color:#d9ffe8;}}
                .dh-cal-more{{font-size:.72rem;color:#b6f2cf;font-weight:700;}}
                </style>
                <div class="dh-cal-wrap">
                  <div class="dh-cal-head">
                    <div><h4>Calendario da agenda</h4><p style="margin:6px 0 0;color:#b8c8d8;">{html.escape(calendar.month_name[mes_cal])} de {ano_cal} com horarios marcados e pacientes vinculados.</p></div>
                    <div class="dh-agenda-pill">{len(eventos_mes)} evento(s) no mes</div>
                  </div>
                  <table class="dh-cal-table">
                    <thead><tr><th>Seg</th><th>Ter</th><th>Qua</th><th>Qui</th><th>Sex</th><th>Sab</th><th>Dom</th></tr></thead>
                    <tbody>{"".join(cal_rows)}</tbody>
                  </table>
                </div>
                """,
                unsafe_allow_html=True,
            )

            list_col, wa_col = st.columns([1.45, 1], gap="large")
            with list_col:
                with st.container(key="agenda_soft_list_card_main"):
                    st.markdown('<div class="dh-agenda-panel"><h4>Lista operacional da agenda</h4><p>Revise agendamentos, filtre rapidamente por periodo e acompanhe o volume de atendimentos sem perder contexto.</p></div>', unsafe_allow_html=True)
                    st.write("")
                    if agenda_filtrada:
                        render_table(agenda_filtrada)
                    else:
                        st.markdown('<div class="dh-agenda-empty">Nenhum agendamento encontrado para esse filtro. Ajuste a busca ou registre um novo atendimento.</div>', unsafe_allow_html=True)

            with wa_col:
                with st.container(key="agenda_soft_list_card_whatsapp"):
                    st.markdown('<div class="dh-agenda-panel"><h4>Enviar por WhatsApp</h4><p>Selecione um agendamento para gerar uma mensagem pronta e confirmar a consulta com o paciente.</p></div>', unsafe_allow_html=True)
                    st.write("")
                    ag_items = []
                    for a in agenda_filtrada:
                        pac = a.get("paciente") or "Paciente"
                        data_str = _fmt_data_br(a.get("data"))
                        hora_str = _fmt_hora_str(a.get("hora"))
                        label = f"{pac} - {data_str} {hora_str}"
                        ag_items.append((label, a))
                    if ag_items:
                        label_sel = st.selectbox("Selecione o agendamento", [x[0] for x in ag_items], key="ag_wa_sel")
                        ag_sel = next((x[1] for x in ag_items if x[0] == label_sel), ag_items[0][1])
                        pac_sel = ag_sel.get("paciente")
                        p_obj = next((p for p in meus_pacientes if p.get("nome") == pac_sel), None)
                        tel_default = (p_obj.get("telefone") if p_obj else "") or ""
                        tel_default = tel_default or ag_sel.get("telefone") or ""
                        tel_wa = st.text_input("WhatsApp do paciente", value=tel_default, key="ag_wa_tel")
                        nome_nutri = (st.session_state.get("usuario") or "Nutricionista").strip() or "Nutricionista"
                        msg_base = (
                            f"Ola {pac_sel}, tudo bem?\n\n"
                            f"Sua consulta com a nutricionista {nome_nutri} esta agendada para "
                            f"{_fmt_data_br(ag_sel.get('data'))} as {_fmt_hora_str(ag_sel.get('hora'))}.\n"
                            f"Paciente: {pac_sel}\n"
                        )
                        if ag_sel.get("obs"):
                            msg_base += f"Observacoes: {ag_sel.get('obs')}\n"
                        msg_base += "\nQualquer ajuste, me avise."
                        msg_edit = st.text_area("Mensagem", value=msg_base, height=140, key="ag_wa_msg")
                        wa = _wa_link(tel_wa, msg_edit)
                        if wa:
                            st.markdown(f'<a class="dh-btn dh-btn-green" href="{wa}" target="_blank">Enviar WhatsApp</a>', unsafe_allow_html=True)
                        else:
                            st.caption("Informe o numero do WhatsApp do paciente para gerar o link.")
                    else:
                        st.markdown('<div class="dh-agenda-empty">Nenhum agendamento disponivel para gerar mensagem por WhatsApp.</div>', unsafe_allow_html=True)

def classify_imc_child_percentile(percentil: float) -> str:
    return classificar_imc_crianca(percentil)

def modulo_atendimento():
    simple_mode = _dh_simple_mode_enabled()
    st.markdown(
        """
        <style>
        .dh-att-hero{
          display:grid;
          grid-template-columns:minmax(0,1.7fr) minmax(280px,1fr);
          gap:18px;
          padding:24px;
          border-radius:24px;
          border:1px solid rgba(82,224,180,0.16);
          background:linear-gradient(135deg, rgba(10,20,37,0.98), rgba(16,33,58,0.94));
          box-shadow:0 24px 52px rgba(0,0,0,0.26);
          margin-bottom:18px;
        }
        .dh-att-kicker{display:inline-flex;padding:7px 12px;border-radius:999px;background:rgba(82,224,180,0.12);border:1px solid rgba(82,224,180,0.22);color:#e7fff7;font-weight:800;font-size:0.78rem;letter-spacing:0.04em;text-transform:uppercase;}
        .dh-att-title{margin:14px 0 0;color:#f8fbff;font-size:2rem;font-weight:800;line-height:1.08;letter-spacing:-0.03em;}
        .dh-att-subtitle{margin:12px 0 0;color:#c4d4e6;line-height:1.65;font-size:1rem;max-width:820px;}
        .dh-att-side{display:grid;gap:12px;align-content:start;}
        .dh-att-chip{display:inline-flex;align-items:center;justify-content:center;min-height:44px;padding:0 14px;border-radius:999px;background:rgba(255,255,255,0.92);border:1px solid rgba(148,163,184,0.16);color:#16233b;font-weight:780;box-shadow:0 12px 22px rgba(2,6,23,0.08);}
        .dh-att-shell{padding:18px;border-radius:22px;border:1px solid rgba(148,163,184,0.14);background:linear-gradient(180deg, rgba(255,255,255,0.06), rgba(255,255,255,0.03));box-shadow:0 16px 30px rgba(2,6,23,0.12);margin-bottom:16px;}
        .dh-att-shell h3{margin:0 0 8px;color:#f3f8ff;font-size:1.14rem;font-weight:800;}
        .dh-att-shell p{margin:0;color:#bcd0e3;line-height:1.58;}
        .dh-att-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:14px;margin-top:14px;}
        .dh-att-card{padding:16px;border-radius:18px;border:1px solid rgba(120,165,207,0.18);background:linear-gradient(145deg, rgba(9,24,39,0.82), rgba(10,20,34,0.74));}
        .dh-att-card-label{font-size:0.8rem;font-weight:800;color:#9cc3df;text-transform:uppercase;letter-spacing:0.04em;}
        .dh-att-card-value{margin-top:8px;color:#f5f9ff;font-size:1.04rem;font-weight:760;line-height:1.28;word-break:break-word;}
        .dh-att-card-note{margin-top:6px;color:#a9bfd3;font-size:0.86rem;line-height:1.5;}
        @media (max-width: 1024px){.dh-att-hero{grid-template-columns:1fr;}.dh-att-grid{grid-template-columns:repeat(2,minmax(0,1fr));}}
        @media (max-width: 768px){.dh-att-hero{padding:18px 16px;}.dh-att-grid{grid-template-columns:1fr;}}
        </style>
        """,
        unsafe_allow_html=True,
    )

    st.title("🧾 Atendimento")
    if simple_mode:
        st.info("Modo simples ativo: esta tela prioriza cadastro básico, seleção do paciente e acesso rápido ao consultório.")

    meus_pacientes = filtrar_por_usuario(pacientes)
    nomes_pacientes = [p.get("nome") for p in meus_pacientes if p.get("nome")]
    preferred = (st.session_state.get("dh_selected_patient_name") or "").strip()
    options = ["-- Novo --"] + nomes_pacientes
    default_index = options.index(preferred) if preferred in options else 0

    st.markdown(
        '<div class="dh-att-shell"><h3>Seleção do paciente</h3><p>Escolha um paciente existente para revisar cadastro e acesso ao portal, ou crie um novo cadastro inicial para começar o vínculo.</p></div>',
        unsafe_allow_html=True,
    )
    escolha = st.selectbox("Paciente", options, index=default_index, key="atendimento_paciente_sel")

    def _parse_br_date(value):
        try:
            if isinstance(value, datetime):
                return value.date()
            txt = str(value or "").strip()
            if not txt:
                return None
            if re.match(r"^\d{4}-\d{2}-\d{2}$", txt):
                return datetime.strptime(txt, "%Y-%m-%d").date()
            return datetime.strptime(txt, "%d/%m/%Y").date()
        except Exception:
            return None

    if escolha == "-- Novo --":
        st.markdown(
            '<div class="dh-att-shell"><h3>Novo cadastro</h3><p>Cadastre identificação e contato do paciente. O prontuário clínico permanece intacto e poderá ser preenchido depois no Consultório.</p></div>',
            unsafe_allow_html=True,
        )
        n = st.text_input("Nome", key="att_cad_nome")
        e = st.text_input("Email", key="att_cad_email")
        t = st.text_input("WhatsApp", key="att_cad_tel")
        c1, c2, c3, c4 = st.columns(4)
        data_nasc = c1.date_input("Data de nascimento", min_value=datetime(1920, 1, 1).date(), max_value=datetime.now().date(), format="DD/MM/YYYY", key="att_cad_dob")
        idade_calc = _calc_idade_from_dob(data_nasc)
        documento = c2.text_input("CPF / Documento", key="att_cad_doc")
        sexo = c3.selectbox("Sexo", ["", "Masculino", "Feminino"], key="att_cad_sexo")
        cidade = c4.text_input("Cidade", key="att_cad_cidade")
        if st.button("Cadastrar paciente", key="att_cad_submit", use_container_width=True):
            dono = (st.session_state.get("usuario") or "").strip().lower()
            novo_nome = (n or "").strip()
            if not novo_nome:
                st.warning("Informe o nome do paciente.")
            else:
                pacientes.append({
                    "dono": dono,
                    "nome": novo_nome,
                    "email": e,
                    "telefone": t,
                    "data": str(datetime.now().date()),
                    "data_nascimento": data_nasc.strftime("%d/%m/%Y") if data_nasc else None,
                    "idade": int(idade_calc) if idade_calc is not None else None,
                    "cpf": _normalize_cpf(documento),
                    "documento": documento,
                    "sexo": sexo,
                    "cidade": cidade,
                    "codigo_paciente": _generate_patient_portal_code(),
                    "status_acesso_portal": "nao_ativado",
                    "anamnese": _blank_anamnese(),
                    "historico": [],
                })
                save_db("pacientes.json", pacientes)
                st.session_state["dh_selected_patient_name"] = novo_nome
                st.success("Paciente cadastrado com sucesso.")
                st.rerun()
        return

    p_obj = next(
        (x for x in pacientes if x.get("nome") == escolha and (x.get("dono") == st.session_state.get("usuario") or st.session_state.get("tipo") == "admin")),
        None,
    )
    if not p_obj:
        st.error("Paciente não encontrado.")
        return

    st.session_state["dh_selected_patient_name"] = escolha
    _ensure_patient_portal_access_fields(p_obj, persist=True)
    status_label, _, status_note = _patient_portal_status_ui(p_obj.get("status_acesso_portal"))
    data_cadastro = str(p_obj.get("data") or "").strip() or "Não informada"
    cpf_atual = _patient_record_cpf(p_obj) or (p_obj.get("documento") or "Não informado")
    codigo_atual = (p_obj.get("codigo_paciente") or "").strip().upper() or "Não gerado"

    st.markdown(
        f"""
        <div class="dh-att-shell">
          <h3>Visão administrativa do paciente</h3>
          <p>Cadastro básico, status de acesso e ações rápidas para o Portal do Paciente.</p>
          <div class="dh-att-grid">
            <div class="dh-att-card">
              <div class="dh-att-card-label">Paciente</div>
              <div class="dh-att-card-value">{html.escape(escolha)}</div>
              <div class="dh-att-card-note">Cadastro principal usado no sistema.</div>
            </div>
            <div class="dh-att-card">
              <div class="dh-att-card-label">CPF</div>
              <div class="dh-att-card-value">{html.escape(cpf_atual)}</div>
              <div class="dh-att-card-note">Documento usado no vínculo com o portal.</div>
            </div>
            <div class="dh-att-card">
              <div class="dh-att-card-label">WhatsApp</div>
              <div class="dh-att-card-value">{html.escape((p_obj.get("telefone") or "Não informado"))}</div>
              <div class="dh-att-card-note">Canal principal para envio do acesso.</div>
            </div>
            <div class="dh-att-card">
              <div class="dh-att-card-label">E-mail</div>
              <div class="dh-att-card-value">{html.escape((p_obj.get("email") or "Não informado"))}</div>
              <div class="dh-att-card-note">Contato complementar do paciente.</div>
            </div>
            <div class="dh-att-card">
              <div class="dh-att-card-label">Status do portal</div>
              <div class="dh-att-card-value">{html.escape(status_label)}</div>
              <div class="dh-att-card-note">{html.escape(status_note)}</div>
            </div>
            <div class="dh-att-card">
              <div class="dh-att-card-label">Código do paciente</div>
              <div class="dh-att-card-value">{html.escape(codigo_atual)}</div>
              <div class="dh-att-card-note">{html.escape(f"Cadastro em {data_cadastro}")}</div>
            </div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    act1, act2 = st.columns([1.3, 1])
    if act1.button("Abrir no Consultório", key=f"att_open_consult_{escolha}", use_container_width=True):
        st.session_state["dh_selected_patient_name"] = escolha
        st.session_state["dh_selected_menu"] = "consultorio"
        _qp_set(SIDEBAR_MENU_QUERY_KEY, "consultorio")
        st.rerun()
    if act2.button("Excluir paciente", key=f"att_delete_patient_{escolha}", type="primary", use_container_width=True):
        pacientes.remove(p_obj)
        save_db("pacientes.json", pacientes)
        st.session_state["dh_selected_patient_name"] = ""
        st.success("Paciente excluído com sucesso.")
        st.rerun()

    st.markdown(
        '<div class="dh-att-shell"><h3>Editar cadastro básico</h3><p>Atualize nome, contato e identificação sem entrar no fluxo clínico do Consultório.</p></div>',
        unsafe_allow_html=True,
    )
    current_dob = _parse_br_date(p_obj.get("data_nascimento")) or datetime.now().date()
    ec1, ec2, ec3, ec4 = st.columns(4)
    nome_edit = ec1.text_input("Nome", value=p_obj.get("nome") or "", key=f"att_nome_{escolha}")
    email_edit = ec2.text_input("Email", value=p_obj.get("email") or "", key=f"att_email_{escolha}")
    tel_edit = ec3.text_input("WhatsApp", value=p_obj.get("telefone") or "", key=f"att_tel_{escolha}")
    cidade_edit = ec4.text_input("Cidade", value=p_obj.get("cidade") or "", key=f"att_cidade_{escolha}")
    ed1, ed2, ed3 = st.columns(3)
    data_nasc_edit = ed1.date_input("Data de nascimento", value=current_dob, min_value=datetime(1920, 1, 1).date(), max_value=datetime.now().date(), format="DD/MM/YYYY", key=f"att_dob_{escolha}")
    documento_edit = ed2.text_input("CPF / Documento", value=p_obj.get("documento") or p_obj.get("cpf") or "", key=f"att_doc_{escolha}")
    sexo_opts = ["", "Masculino", "Feminino"]
    sexo_cur = p_obj.get("sexo") if (p_obj.get("sexo") in sexo_opts) else ""
    sexo_edit = ed3.selectbox("Sexo", sexo_opts, index=sexo_opts.index(sexo_cur), key=f"att_sexo_{escolha}")
    if st.button("Salvar cadastro básico", key=f"att_save_basic_{escolha}", use_container_width=True):
        p_obj["nome"] = (nome_edit or "").strip() or p_obj.get("nome")
        p_obj["email"] = (email_edit or "").strip()
        p_obj["telefone"] = (tel_edit or "").strip()
        p_obj["cidade"] = (cidade_edit or "").strip()
        p_obj["data_nascimento"] = data_nasc_edit.strftime("%d/%m/%Y") if data_nasc_edit else None
        p_obj["idade"] = _calc_idade_from_dob(data_nasc_edit)
        p_obj["documento"] = (documento_edit or "").strip()
        p_obj["cpf"] = _normalize_cpf(documento_edit)
        p_obj["sexo"] = sexo_edit
        if not p_obj.get("data"):
            p_obj["data"] = str(datetime.now().date())
        save_db("pacientes.json", pacientes)
        st.session_state["dh_selected_patient_name"] = p_obj.get("nome") or escolha
        st.success("Cadastro básico atualizado.")
        st.rerun()

    if simple_mode:
        with st.expander("Portal do Paciente e configurações avançadas", expanded=False):
            _render_patient_portal_admin_panel(p_obj, escolha)
    else:
        _render_patient_portal_admin_panel(p_obj, escolha)


def modulo_consultorio_completo():
    simple_mode = _dh_simple_mode_enabled()
    st.markdown(
        """
        <style>
        .dh-consult-hero{
          display:grid;
          grid-template-columns:minmax(0,1.7fr) minmax(250px,1fr);
          gap:18px;
          padding:22px 24px;
          margin:8px 0 18px;
          border-radius:24px;
          border:1px solid rgba(96,165,250,0.16);
          background:
            radial-gradient(circle at top left, rgba(34,197,94,0.12), transparent 32%),
            radial-gradient(circle at bottom right, rgba(59,130,246,0.12), transparent 30%),
            linear-gradient(145deg, rgba(9,20,37,0.98), rgba(13,31,57,0.96));
          box-shadow:0 24px 44px rgba(2,6,23,0.24);
        }
        .dh-consult-kicker{
          display:inline-flex;
          align-items:center;
          gap:8px;
          padding:8px 12px;
          border-radius:999px;
          background:rgba(34,197,94,0.12);
          border:1px solid rgba(34,197,94,0.24);
          color:#d9ffed;
          font-size:.8rem;
          font-weight:800;
          letter-spacing:.03em;
          text-transform:uppercase;
        }
        .dh-consult-title{
          margin:12px 0 0;
          color:#f8fbff;
          font-size:clamp(1.34rem,1.05rem + .86vw,1.96rem);
          font-weight:850;
          line-height:1.08;
        }
        .dh-consult-subtitle{
          margin:10px 0 0;
          color:#c6d7e7;
          line-height:1.68;
          max-width:820px;
        }
        .dh-consult-hero-side{
          display:grid;
          gap:12px;
          align-content:start;
        }
        .dh-consult-chip{
          display:inline-flex;
          align-items:center;
          justify-content:center;
          min-height:42px;
          padding:0 14px;
          border-radius:999px;
          background:rgba(255,255,255,0.9);
          border:1px solid rgba(148,163,184,0.16);
          color:#16233b;
          font-weight:780;
          box-shadow:0 10px 22px rgba(2,6,23,0.08);
        }
        .dh-consult-shell{
          padding:18px 18px 16px;
          margin:0 0 16px;
          border-radius:22px;
          border:1px solid rgba(148,163,184,0.14);
          background:linear-gradient(180deg, rgba(255,255,255,0.06), rgba(255,255,255,0.03));
          box-shadow:0 16px 32px rgba(2,6,23,0.12);
        }
        .dh-consult-shell-title{
          margin:0 0 6px;
          color:#f8fbff;
          font-size:1.02rem;
          font-weight:820;
        }
        .dh-consult-shell-copy{
          margin:0;
          color:#bdd0e4;
          line-height:1.6;
        }
        .dh-consult-grid{
          display:grid;
          grid-template-columns:repeat(4,minmax(0,1fr));
          gap:14px;
          margin:14px 0 18px;
        }
        .dh-consult-card{
          min-height:106px;
          padding:16px 16px 18px;
          border-radius:18px;
          border:1px solid rgba(148,163,184,0.14);
          background:linear-gradient(180deg, rgba(255,255,255,0.07), rgba(255,255,255,0.04));
          box-shadow:0 12px 22px rgba(2,6,23,0.08);
        }
        .dh-consult-card-label{
          color:#9fb4c9;
          font-size:.78rem;
          font-weight:800;
          text-transform:uppercase;
          letter-spacing:.05em;
        }
        .dh-consult-card-value{
          margin-top:9px;
          color:#f8fbff;
          font-size:1rem;
          font-weight:780;
          line-height:1.28;
          overflow-wrap:anywhere;
        }
        .dh-consult-card-note{
          margin-top:7px;
          color:#b8cada;
          font-size:.87rem;
          line-height:1.5;
        }
        .dh-consult-action-row{
          display:grid;
          grid-template-columns:minmax(0,1fr) auto auto;
          gap:12px;
          align-items:center;
          margin:10px 0 18px;
        }
        .dh-consult-timer{
          display:inline-flex;
          align-items:center;
          gap:8px;
          min-height:44px;
          padding:0 14px;
          border-radius:999px;
          border:1px solid rgba(96,165,250,0.22);
          background:rgba(15,23,42,0.54);
          color:#e1efff;
          font-weight:780;
          white-space:nowrap;
        }
        .dh-consult-section-intro{
          padding:14px 16px;
          border-radius:18px;
          background:linear-gradient(180deg, rgba(20,121,101,0.2), rgba(15,118,110,0.18));
          border:1px solid rgba(45,212,191,0.18);
          color:#e8fff9;
          line-height:1.6;
          margin:6px 0 16px;
        }
        @media (max-width: 1024px){
          .dh-consult-hero{grid-template-columns:1fr;}
          .dh-consult-grid{grid-template-columns:repeat(2,minmax(0,1fr));}
          .dh-consult-action-row{grid-template-columns:1fr;}
        }
        @media (max-width: 768px){
          .dh-consult-hero{padding:18px 16px;}
          .dh-consult-shell{padding:16px 14px 14px;}
          .dh-consult-grid{grid-template-columns:1fr;}
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
    st.title("🩺 Consultas")
    if simple_mode:
        st.info("Modo simples ativo: foco em seleção do paciente, anamnese e avaliação principal. Fluxos menos usados ficam recolhidos.")

    meus_pacientes = filtrar_por_usuario(pacientes)

    if "timer" not in st.session_state:
        st.session_state["timer"] = None

    st.markdown(
        '<div class="dh-consult-shell"><h3 class="dh-consult-shell-title">Seleção do paciente</h3><p class="dh-consult-shell-copy">Escolha um paciente já cadastrado para abrir automaticamente o prontuário completo. O cadastro inicial e o acesso ao portal agora ficam no módulo Atendimento.</p></div>',
        unsafe_allow_html=True,
    )
    if not meus_pacientes:
        st.info("Nenhum paciente cadastrado. Use o módulo Atendimento para cadastrar o paciente antes de abrir o Consultório.")
        return

    nomes_pacientes = [p["nome"] for p in meus_pacientes]
    preferred = (st.session_state.get("dh_selected_patient_name") or "").strip()
    default_index = nomes_pacientes.index(preferred) if preferred in nomes_pacientes else 0
    escolha = st.selectbox("Paciente:", nomes_pacientes, index=default_index)
    st.session_state["dh_selected_patient_name"] = escolha

    p_obj = next(
        (x for x in pacientes
         if x.get("nome") == escolha and (x.get("dono") == st.session_state["usuario"] or st.session_state.get("tipo") == "admin")),
        None
    )
    if not p_obj:
        st.error("Paciente não encontrado.")
        return

    historico = p_obj.get("historico", []) or []

    def _last_hist(predicate):
        for h in reversed(historico):
            if predicate(h):
                return h
        return None

    ultimo_adulto = _last_hist(lambda h: (h.get("tipo") or "").strip().lower() not in {"avaliacao_crianca", "avaliacao_bebe", "avaliacao_gestante"})
    ultimo_crianca = _last_hist(lambda h: (h.get("tipo") or "").strip().lower() == "avaliacao_crianca")
    ultimo_bebe = _last_hist(lambda h: (h.get("tipo") or "").strip().lower() == "avaliacao_bebe")
    ultimo_gestante = _last_hist(lambda h: (h.get("tipo") or "").strip().lower() == "avaliacao_gestante")

    def _as_int(val, default=0):
        try:
            if val is None or val == "":
                return default
            return int(float(val))
        except Exception:
            return default

    def _as_float(val, default=0.0):
        try:
            if val is None or val == "":
                return default
            if isinstance(val, str):
                val = val.replace(",", ".")
            v = float(val)
            return v if math.isfinite(v) else default
        except Exception:
            return default

    def _clamp(val, lo, hi):
        if val < lo:
            return lo
        if val > hi:
            return hi
        return val

    def _sexo_norm(txt):
        t = (txt or "").strip().lower()
        return "Masculino" if t.startswith("m") else "Feminino"

    def _faixa_gordura_ref(sexo, idade):
        idade_v = _as_int(idade, 0)
        sexo_v = _sexo_norm(sexo)
        tabelas = {
            "Masculino": [
                {"max_idade": 29, "excelente": (6, 13), "boa": (14, 17), "normal": (18, 24), "elevado": (25, 29), "muito_elevado": (30, 100)},
                {"max_idade": 39, "excelente": (7, 14), "boa": (15, 18), "normal": (19, 25), "elevado": (26, 30), "muito_elevado": (31, 100)},
                {"max_idade": 49, "excelente": (8, 15), "boa": (16, 19), "normal": (20, 26), "elevado": (27, 31), "muito_elevado": (32, 100)},
                {"max_idade": 59, "excelente": (9, 16), "boa": (17, 20), "normal": (21, 27), "elevado": (28, 32), "muito_elevado": (33, 100)},
                {"max_idade": 200, "excelente": (10, 17), "boa": (18, 21), "normal": (22, 28), "elevado": (29, 33), "muito_elevado": (34, 100)},
            ],
            "Feminino": [
                {"max_idade": 29, "excelente": (14, 20), "boa": (21, 24), "normal": (25, 31), "elevado": (32, 37), "muito_elevado": (38, 100)},
                {"max_idade": 39, "excelente": (15, 21), "boa": (22, 25), "normal": (26, 32), "elevado": (33, 38), "muito_elevado": (39, 100)},
                {"max_idade": 49, "excelente": (16, 22), "boa": (23, 26), "normal": (27, 33), "elevado": (34, 39), "muito_elevado": (40, 100)},
                {"max_idade": 59, "excelente": (17, 23), "boa": (24, 27), "normal": (28, 34), "elevado": (35, 40), "muito_elevado": (41, 100)},
                {"max_idade": 200, "excelente": (18, 24), "boa": (25, 28), "normal": (29, 35), "elevado": (36, 41), "muito_elevado": (42, 100)},
            ],
        }
        for faixa in tabelas.get(sexo_v, tabelas["Masculino"]):
            if idade_v <= faixa["max_idade"]:
                return faixa
        return tabelas["Masculino"][-1]

    def _classificar_gordura(sexo, idade, pct):
        if pct is None or pct <= 0:
            return ""
        faixa = _faixa_gordura_ref(sexo, idade)
        if pct <= faixa["excelente"][1]:
            return "Excelente"
        if pct <= faixa["boa"][1]:
            return "Boa"
        if pct <= faixa["normal"][1]:
            return "Normal"
        if pct <= faixa["elevado"][1]:
            return "Elevado"
        return "Muito elevado"

    def _faixa_gordura_nih(sexo, idade):
        idade_v = _as_int(idade, 0)
        sexo_v = _sexo_norm(sexo)
        tabelas = {
            "Feminino": [
                {"max_idade": 39, "normal": (21.0, 32.9), "alto": (33.0, 38.9), "muito": 39.0},
                {"max_idade": 59, "normal": (23.0, 33.9), "alto": (34.0, 39.9), "muito": 40.0},
                {"max_idade": 79, "normal": (24.0, 35.9), "alto": (36.0, 41.9), "muito": 42.0},
            ],
            "Masculino": [
                {"max_idade": 39, "normal": (8.0, 19.9), "alto": (20.0, 24.9), "muito": 25.0},
                {"max_idade": 59, "normal": (11.0, 21.9), "alto": (22.0, 27.9), "muito": 28.0},
                {"max_idade": 79, "normal": (13.0, 24.0), "alto": (25.0, 29.9), "muito": 30.0},
            ],
        }
        for faixa in tabelas.get(sexo_v, tabelas["Masculino"]):
            if idade_v <= faixa["max_idade"]:
                return faixa
        return tabelas.get(sexo_v, tabelas["Masculino"])[-1]

    def _classificar_gordura_nih(sexo, idade, pct):
        if pct is None or pct <= 0:
            return ""
        faixa = _faixa_gordura_nih(sexo, idade)
        if pct < faixa["normal"][0]:
            return "Baixo"
        if pct <= faixa["normal"][1]:
            return "Normal"
        if pct <= faixa["alto"][1]:
            return "Alto"
        return "Muito alto"

    def _classificar_gordura_visceral(visc):
        if visc is None or visc <= 0:
            return ""
        if visc <= 9:
            return "Normal"
        if visc <= 14:
            return "Alto"
        return "Muito alto"

    def _faixa_musculo_esqueletico(sexo, idade):
        idade_v = _as_int(idade, 0)
        sexo_v = _sexo_norm(sexo)
        tabelas = {
            "Feminino": [
                {"max_idade": 39, "normal": (24.3, 30.3), "alto": (30.4, 35.3), "muito": 35.4},
                {"max_idade": 59, "normal": (24.1, 30.1), "alto": (30.2, 35.1), "muito": 35.2},
                {"max_idade": 80, "normal": (23.9, 29.9), "alto": (30.0, 34.9), "muito": 35.0},
            ],
            "Masculino": [
                {"max_idade": 39, "normal": (33.3, 39.3), "alto": (39.4, 44.0), "muito": 44.1},
                {"max_idade": 59, "normal": (33.1, 39.1), "alto": (39.2, 43.8), "muito": 43.9},
                {"max_idade": 80, "normal": (32.9, 38.9), "alto": (39.0, 43.6), "muito": 43.7},
            ],
        }
        for faixa in tabelas.get(sexo_v, tabelas["Masculino"]):
            if idade_v <= faixa["max_idade"]:
                return faixa
        return tabelas.get(sexo_v, tabelas["Masculino"])[-1]

    def _classificar_musculo_esqueletico(sexo, idade, pct):
        if pct is None or pct <= 0:
            return ""
        faixa = _faixa_musculo_esqueletico(sexo, idade)
        if pct < faixa["normal"][0]:
            return "Baixo"
        if pct <= faixa["normal"][1]:
            return "Normal"
        if pct <= faixa["alto"][1]:
            return "Alto"
        return "Muito alto"

    def _faixa_massa_magra_ideal(sexo, idade):
        faixa = _faixa_gordura_ref(sexo, idade)
        g_min, g_max = faixa["normal"]
        mm_min = 100.0 - g_max
        mm_max = 100.0 - g_min
        return (mm_min, mm_max)

    ult_ad_vitais = (ultimo_adulto or {}).get("dados_vitais", {}) or {}
    ult_ad_perim = (ultimo_adulto or {}).get("perimetria", {}) or {}
    ult_ad_dobras = (ultimo_adulto or {}).get("dobras", {}) or {}
    ult_ad_medidas = (ultimo_adulto or {}).get("medidas", {}) or {}
    ult_ad_nota = (ultimo_adulto or {}).get("nota") or (ultimo_adulto or {}).get("observacoes") or ""

    ult_ch_vitais = (ultimo_crianca or {}).get("dados_vitais", {}) or {}
    ult_ch_medidas = (ultimo_crianca or {}).get("medidas", {}) or {}
    ult_ch_obs = (ultimo_crianca or {}).get("observacoes") or ""
    ult_bebe_vitais = (ultimo_bebe or {}).get("dados_vitais", {}) or {}
    ult_bebe_medidas = (ultimo_bebe or {}).get("medidas", {}) or {}
    ult_bebe_obs = (ultimo_bebe or {}).get("observacoes") or ""
    ult_gest_vitais = (ultimo_gestante or {}).get("dados_vitais", {}) or {}
    ult_gest_obs = (ultimo_gestante or {}).get("observacoes") or ""
    anamnese_atual = get_anamnese_paciente(p_obj)
    gestacao_flag = any(
        token in (str(anamnese_atual.get("gestacao_lactacao") or "")).strip().lower()
        for token in ["sim", "gest", "grav"]
    )
    pac_dob = None
    for fmt in ("%d/%m/%Y", "%Y-%m-%d"):
        try:
            raw_dob = str(p_obj.get("data_nascimento") or "").strip()
            if raw_dob:
                pac_dob = datetime.strptime(raw_dob, fmt).date()
                break
        except Exception:
            continue
    agenda_ref = next(
        (
            item for item in reversed(agenda)
            if (item.get("paciente") or "").strip() == (p_obj.get("nome") or "").strip()
            and ((item.get("dono") or "").strip().lower() == (st.session_state.get("usuario") or "").strip().lower() or st.session_state.get("tipo") == "admin")
        ),
        {},
    )
    pac_idade = _as_int(p_obj.get("idade"), _as_int(agenda_ref.get("idade"), 0))
    pac_sexo = (p_obj.get("sexo") or agenda_ref.get("sexo") or "").strip()
    hoje_ref = datetime.now().date()
    pac_age_days = max(0, (hoje_ref - pac_dob).days) if pac_dob else max(0, pac_idade * 365)
    pac_age_months = max(0, int(round(pac_age_days / 30.4375))) if pac_age_days else 0
    cpf_atual = _patient_record_cpf(p_obj) or (p_obj.get("documento") or "")
    contato_atual = (p_obj.get("telefone") or "").strip() or "Não informado"
    email_atual = (p_obj.get("email") or "").strip() or "Não informado"
    cidade_atual = (p_obj.get("cidade") or "").strip() or "Não informada"
    nasc_atual = (p_obj.get("data_nascimento") or "").strip() or "Não informada"

    st.markdown(
        f"""
        <div class="dh-consult-shell">
          <h3 class="dh-consult-shell-title">Paciente em atendimento</h3>
          <p class="dh-consult-shell-copy">Antes de entrar na área técnica, revise rapidamente identificação, contato e dados cadastrais. Isso ajuda no fluxo do consultório sem alterar a estrutura nutricional do prontuário.</p>
          <div class="dh-consult-grid">
            <div class="dh-consult-card">
              <div class="dh-consult-card-label">Paciente</div>
              <div class="dh-consult-card-value">{html.escape(escolha)}</div>
              <div class="dh-consult-card-note">Prontuário ativo para avaliação, anamnese e histórico.</div>
            </div>
            <div class="dh-consult-card">
              <div class="dh-consult-card-label">Contato</div>
              <div class="dh-consult-card-value">{html.escape(contato_atual)}</div>
              <div class="dh-consult-card-note">Contato rápido do paciente durante o atendimento.</div>
            </div>
            <div class="dh-consult-card">
              <div class="dh-consult-card-label">Documento</div>
              <div class="dh-consult-card-value">{html.escape(cpf_atual or "Não informado")}</div>
              <div class="dh-consult-card-note">Documento principal vinculado ao prontuário clínico.</div>
            </div>
            <div class="dh-consult-card">
              <div class="dh-consult-card-label">Dados cadastrais</div>
              <div class="dh-consult-card-value">{html.escape(email_atual)}</div>
              <div class="dh-consult-card-note">{html.escape(f"{cidade_atual} • nascimento {nasc_atual}")}</div>
            </div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    c_h, c_d = st.columns([4, 1])
    c_h.markdown(f"### Atendendo: **{escolha}**")
    with c_d:
        if st.button("🗑️ Excluir Paciente", type="primary"):
            pacientes.remove(p_obj)
            save_db("pacientes.json", pacientes)
            st.rerun()

    act1, act2, act3 = st.columns([1.4, 1, 1])
    with act1:
        if st.session_state["timer"]:
            st.markdown(
                f'<div class="dh-consult-timer">⏱️ Tempo de atendimento: {str(datetime.now()-st.session_state["timer"]).split(".")[0]}</div>',
                unsafe_allow_html=True
            )
        else:
            st.markdown(
                '<div class="dh-consult-timer">⏱️ Cronômetro do atendimento pronto para iniciar</div>',
                unsafe_allow_html=True
            )
    with act2:
        if st.session_state["timer"]:
            if st.button("Parar"):
                st.session_state["timer"] = None
                st.rerun()
        else:
            if st.button("Iniciar"):
                st.session_state["timer"] = datetime.now()
                st.rerun()
    with act3:
        st.caption("Ações rápidas do atendimento atual.")

    anamnese_atual = get_anamnese_paciente(p_obj)
    st.markdown(
        '<div class="dh-consult-shell"><h3 class="dh-consult-shell-title">Anamnese clínica</h3><p class="dh-consult-shell-copy">Esta seção concentra contexto clínico, observações e histórico textual do paciente. O conteúdo continua sendo aplicado automaticamente no Diet Generator e nos demais fluxos já existentes.</p></div>',
        unsafe_allow_html=True,
    )
    st.markdown("### 🧾 Anamnese Clínica")
    st.caption("Esses dados são usados automaticamente no Diet Generator para respeitar alergias, intolerâncias e condições clínicas.")
    with st.form(f"anamnese_form_{p_obj.get('id') or escolha}"):
        ca1, ca2 = st.columns(2)
        queixa_principal = ca1.text_area(
            "Queixa principal",
            value=anamnese_atual.get("queixa_principal", ""),
            placeholder="Motivo principal da consulta.",
        )
        alergias = ca2.text_area(
            "Alergias",
            value=anamnese_atual.get("alergias", ""),
            placeholder="Ex: amendoim, crustáceos, dipirona.",
        )
        intolerancias = st.text_area(
            "Intolerâncias",
            value=anamnese_atual.get("intolerancias", ""),
            placeholder="Ex: lactose, glúten, FODMAPs.",
        )
        condicoes_saude = st.text_area(
            "Doenças / Condições de saúde",
            value=anamnese_atual.get("condicoes_saude", ""),
            placeholder="Ex: diabetes, hipertensão, SOP, gastrite, doença renal.",
        )
        medicamentos_suplementos = st.text_area(
            "Medicamentos / Suplementos em uso",
            value=anamnese_atual.get("medicamentos_suplementos", ""),
            placeholder="Ex: metformina, losartana, whey, creatina.",
        )
        observacoes_clinicas = st.text_area(
            "Observações clínicas relevantes",
            value=anamnese_atual.get("observacoes_clinicas", ""),
            placeholder="Rotina, horários, sintomas, preferências e pontos de atenção.",
        )
        salvar_anamnese = st.form_submit_button("💾 Salvar Anamnese")
    if salvar_anamnese:
        p_obj["anamnese"] = _normalize_anamnese_data({
            "queixa_principal": queixa_principal,
            "alergias": alergias,
            "intolerancias": intolerancias,
            "condicoes_saude": condicoes_saude,
            "medicamentos_suplementos": medicamentos_suplementos,
            "observacoes_clinicas": observacoes_clinicas,
        })
        save_db("pacientes.json", pacientes)
        st.success("✅ Anamnese salva. Ela será aplicada automaticamente ao gerar dieta com IA.")
        time.sleep(0.4)
        st.rerun()

    if simple_mode:
        tab_adulto = st.container()
        tab_crianca = st.expander("👶 Avaliação infantil e adolescente", expanded=False)
    else:
        tab_adulto, tab_crianca = st.tabs(["🧑 Adulto/Adolescente", "👶 Criança"])

    with tab_adulto:
        with st.form("pront"):
                st.markdown("#### 1. Dados Vitais & IMC")
                c_idade, c_sexo, c1, c2 = st.columns(4)
                idade_default = _clamp(_as_int(ult_ad_vitais.get("idade"), pac_idade if pac_idade else 30), 0, 110)
                meses_default = _clamp(_as_int(ult_ad_vitais.get("idade_meses"), 0), 0, 11)
                sexo_default = (ult_ad_vitais.get("sexo") or pac_sexo or "Masculino")
                sexo_index = 0 if _sexo_norm(sexo_default) == "Masculino" else 1
                peso_default = max(0.0, _as_float(ult_ad_vitais.get("peso"), 0.0))
                altura_default = _clamp(_as_float(ult_ad_vitais.get("altura"), 1.70), 0.0, 3.0)

                idade = c_idade.number_input("Idade", min_value=0, max_value=110, value=idade_default)
                meses = st.number_input("Meses (0-11) — use para crianças/adolescentes", min_value=0, max_value=11, value=meses_default)
                sexo = c_sexo.selectbox("Sexo", ["Masculino", "Feminino"], index=sexo_index)
                peso = c1.number_input("Peso (kg)", min_value=0.0, value=peso_default, step=0.01, format="%.2f")
                alt = c2.number_input("Altura (m)", min_value=0.00, max_value=3.00, value=altura_default, step=0.01, format="%.2f")

                imc = 0.0
                classificacao_imc = ""
                if peso > 0 and alt > 0:
                    imc = peso / (alt ** 2)
                    classificacao_imc = classificar_imc_adulto_oms(imc)
                    peso_ideal_min, peso_ideal_max = faixa_peso_ideal_oms(alt)
                    st.markdown(
                        f'<div class="dh-pill-soft"><b>IMC:</b> {imc:.2f} kg/m² &nbsp;|&nbsp; <b>Classificação OMS:</b> {classificacao_imc} &nbsp;|&nbsp; <b>Faixa saudável OMS:</b> {peso_ideal_min:.1f}–{peso_ideal_max:.1f} kg</div>',
                        unsafe_allow_html=True
                    )

                c_gord, c_bio, c_musc, c_visc = st.columns(4)
                gord_default = max(0.0, _as_float(ult_ad_dobras.get("percentual_gordura"), 0.0))
                bio_gord_default = max(0.0, _as_float(ult_ad_vitais.get("bioimpedancia"), 0.0))
                musc_pct_default = max(0.0, _as_float(ult_ad_vitais.get("bio_musculo_esqueletico_pct"), 0.0))
                visc_default = max(0, _as_int(ult_ad_vitais.get("visceral"), 0))
                agua_corporal_default = max(0.0, _as_float(ult_ad_vitais.get("agua_corporal"), 0.0))
                bio_osso_default = max(0.0, _as_float(ult_ad_vitais.get("bio_massa_ossea"), 0.0))
                gord_container = c_gord.container()
                bio_gord = c_bio.number_input("Gordura % (Bioimpedância)", min_value=0.0, value=bio_gord_default, step=0.1)
                musc_pct = c_musc.number_input("Músculo esquelético % (Bioimpedância)", min_value=0.0, value=musc_pct_default, step=0.1)
                visc = c_visc.number_input("Gordura Visceral", min_value=0, value=visc_default)

                c_agua, c_osso = st.columns(2)
                agua_corporal = c_agua.number_input("Água corporal (L)", min_value=0.0, value=agua_corporal_default, step=0.1)
                bio_massa_ossea = c_osso.number_input("Massa óssea (kg) — Bioimpedância", min_value=0.0, value=bio_osso_default, step=0.1)

                st.markdown("#### 2. Perimetria & RCQ")
                p1, p2, p3, p4 = st.columns(4)
                torax_default = max(0.0, _as_float(ult_ad_perim.get("torax"), 0.0))
                cint_default = max(0.0, _as_float(ult_ad_perim.get("cintura"), 0.0))
                abd_default = max(0.0, _as_float(ult_ad_perim.get("abdomen"), 0.0))
                quad_default = max(0.0, _as_float(ult_ad_perim.get("quadril"), 0.0))
                torax = p1.number_input("Tórax", min_value=0.0, value=torax_default, step=0.1)
                cint = p2.number_input("Cintura", min_value=0.0, value=cint_default, step=0.1)
                abd = p3.number_input("Abdômen", min_value=0.0, value=abd_default, step=0.1)
                quad = p4.number_input("Quadril", min_value=0.0, value=quad_default, step=0.1)

                if cint > 0 and quad > 0:
                    rcq = cint / quad
                    limite_rcq = 0.90 if _sexo_norm(sexo) == "Masculino" else 0.85
                    if rcq > limite_rcq:
                        risco_rcq = "Alto risco cardiometabólico"
                    else:
                        risco_rcq = "Baixo risco cardiometabólico"
                    st.markdown(
                        f'<div class="dh-pill-soft"><b>RCQ:</b> {rcq:.2f} &nbsp;|&nbsp; <b>Risco cardiometabólico:</b> {risco_rcq} (Normal ≤ {limite_rcq:.2f})</div>',
                        unsafe_allow_html=True
                    )


                st.markdown("#### 3. Membros")
                ms1, ms2, ms3, ms4 = st.columns(4)
                br_d_rel_default = max(0.0, _as_float(ult_ad_medidas.get("braco_d_rel"), 0.0))
                br_e_rel_default = max(0.0, _as_float(ult_ad_medidas.get("braco_e_rel"), 0.0))
                br_d_con_default = max(0.0, _as_float(ult_ad_medidas.get("braco_d_con"), 0.0))
                br_e_con_default = max(0.0, _as_float(ult_ad_medidas.get("braco_e_con"), 0.0))
                br_d_rel = ms1.number_input("Braço D. Rel", min_value=0.0, value=br_d_rel_default, step=0.1)
                br_e_rel = ms2.number_input("Braço E. Rel", min_value=0.0, value=br_e_rel_default, step=0.1)
                br_d_con = ms3.number_input("Braço D. Con", min_value=0.0, value=br_d_con_default, step=0.1)
                br_e_con = ms4.number_input("Braço E. Con", min_value=0.0, value=br_e_con_default, step=0.1)

                mi1, mi2, mi3, mi4 = st.columns(4)
                cx_prox_d_default = max(0.0, _as_float(ult_ad_medidas.get("coxa_prox_d"), 0.0))
                cx_prox_e_default = max(0.0, _as_float(ult_ad_medidas.get("coxa_prox_e"), 0.0))
                cx_med_d_default = max(0.0, _as_float(ult_ad_medidas.get("coxa_med_d"), 0.0))
                cx_med_e_default = max(0.0, _as_float(ult_ad_medidas.get("coxa_med_e"), 0.0))
                cx_prox_d = mi1.number_input("Coxa P. D", min_value=0.0, value=cx_prox_d_default, step=0.1)
                cx_prox_e = mi2.number_input("Coxa P. E", min_value=0.0, value=cx_prox_e_default, step=0.1)
                cx_med_d = mi3.number_input("Coxa M. D", min_value=0.0, value=cx_med_d_default, step=0.1)
                cx_med_e = mi4.number_input("Coxa M. E", min_value=0.0, value=cx_med_e_default, step=0.1)

                mi5, mi6, mi7, mi8 = st.columns(4)
                cx_dist_d_default = max(0.0, _as_float(ult_ad_medidas.get("coxa_dist_d"), 0.0))
                cx_dist_e_default = max(0.0, _as_float(ult_ad_medidas.get("coxa_dist_e"), 0.0))
                pant_d_default = max(0.0, _as_float(ult_ad_medidas.get("panturrilha_d"), 0.0))
                pant_e_default = max(0.0, _as_float(ult_ad_medidas.get("panturrilha_e"), 0.0))
                cx_dist_d = mi5.number_input("Coxa D. D", min_value=0.0, value=cx_dist_d_default, step=0.1)
                cx_dist_e = mi6.number_input("Coxa D. E", min_value=0.0, value=cx_dist_e_default, step=0.1)
                pant_d = mi7.number_input("Panturrilha D", min_value=0.0, value=pant_d_default, step=0.1)
                pant_e = mi8.number_input("Panturrilha E", min_value=0.0, value=pant_e_default, step=0.1)

                st.markdown("#### 5. Dobras Cutâneas (mm)")
                d1, d2, d3, d4 = st.columns(4)
                tri_default = max(0.0, _as_float(ult_ad_dobras.get("triceps"), 0.0))
                bi_default = max(0.0, _as_float(ult_ad_dobras.get("biceps"), 0.0))
                sub_default = max(0.0, _as_float(ult_ad_dobras.get("subescapular"), 0.0))
                supra_default = max(0.0, _as_float(ult_ad_dobras.get("suprailiaca"), 0.0))
                tri = d1.number_input("Tríceps", min_value=0.0, value=tri_default, step=0.1)
                bi = d2.number_input("Bíceps", min_value=0.0, value=bi_default, step=0.1)
                sub = d3.number_input("Subescapular", min_value=0.0, value=sub_default, step=0.1)
                supra = d4.number_input("Supra-ilíaca", min_value=0.0, value=supra_default, step=0.1)

                d5, d6, d7, d8 = st.columns(4)
                peit_default = max(0.0, _as_float(ult_ad_dobras.get("peitoral"), 0.0))
                axil_default = max(0.0, _as_float(ult_ad_dobras.get("axilar"), 0.0))
                abdo_default = max(0.0, _as_float(ult_ad_dobras.get("abdominal"), 0.0))
                coxa_default = max(0.0, _as_float(ult_ad_dobras.get("coxa"), 0.0))
                peit = d5.number_input("Peitoral", min_value=0.0, value=peit_default, step=0.1)
                axil = d6.number_input("Axilar M", min_value=0.0, value=axil_default, step=0.1)
                abdo = d7.number_input("Abdominal", min_value=0.0, value=abdo_default, step=0.1)
                coxa = d8.number_input("Coxa", min_value=0.0, value=coxa_default, step=0.1)

                gordura_calc = 0.0
                massa_gorda = 0.0
                massa_magra = 0.0
                peso_osseo = 0.0
                peso_residual = 0.0
                massa_muscular = 0.0
                bio_massa_gorda = 0.0
                bio_massa_magra = 0.0
                bio_massa_magra_pct = 0.0
                classif_gord_dobras = ""
                classif_gord_bio = ""
                classif_gord_dobras_nih = ""
                classif_gord_bio_nih = ""
                classif_visc = ""
                classif_musc = ""
                massa_magra_base_pct = None
                massa_magra_base_desc = ""
                massa_magra_ideal_pct_min = None
                massa_magra_ideal_pct_max = None
                massa_magra_ideal_kg_min = None
                massa_magra_ideal_kg_max = None
                massa_magra_status = ""
                mm_status_dobras = ""
                mm_status_bio = ""

                if tri > 0 and br_d_rel > 0:
                    cmb = br_d_rel - (0.314 * tri)
                    st.markdown(f'<div class="dh-pill-soft"><b>CMB:</b> {cmb:.2f} cm</div>', unsafe_allow_html=True)

                soma_dobras = tri + bi + sub + supra + peit + axil + abdo + coxa
                if soma_dobras > 0 and idade > 0 and peso > 0:
                    densidade = 0.0
                    if sexo == "Masculino":
                        densidade = 1.112 - (0.00043499 * soma_dobras) + (0.00000055 * (soma_dobras ** 2)) - (0.00028826 * idade)
                    else:
                        densidade = 1.097 - (0.00046971 * soma_dobras) + (0.00000056 * (soma_dobras ** 2)) - (0.00012828 * idade)
                    if densidade > 0:
                        gordura_calc = (495 / densidade) - 450
                    if not math.isfinite(gordura_calc) or gordura_calc <= 0:
                        gordura_calc = 0.0

                gord_value = gordura_calc if gordura_calc > 0 else gord_default
                gord = gord_container.number_input(
                    "Gordura % (Cálculo Dobras)",
                    min_value=0.0,
                    value=gord_value,
                    step=0.1,
                    disabled=(gordura_calc > 0)
                )
                if gordura_calc <= 0 and peso > 0 and gord > 0:
                    gordura_calc = gord
                if gordura_calc > 0:
                    gord_container.caption("Calculado automaticamente a partir das dobras.")

                if peso > 0 and gordura_calc > 0:
                    massa_gorda = peso * (gordura_calc / 100)
                    massa_magra = peso - massa_gorda

                st.markdown("#### 6. Diâmetros Ósseos (cm)")
                st.caption("Atenção: Use PONTO para decimais (ex: 10.50).")
                do1, do2, do3 = st.columns(3)
                diam_umero_default = max(0.0, _as_float(ult_ad_medidas.get("diam_umero"), 0.0))
                diam_punho_default = max(0.0, _as_float(ult_ad_medidas.get("diam_punho"), 0.0))
                diam_femur_default = max(0.0, _as_float(ult_ad_medidas.get("diam_femur"), 0.0))
                diam_umero = do1.number_input("Diâmetro do Úmero", min_value=0.0, value=diam_umero_default, step=0.01, format="%.2f")
                diam_punho = do2.number_input("Diâmetro do Punho", min_value=0.0, value=diam_punho_default, step=0.01, format="%.2f")
                diam_femur = do3.number_input("Diâmetro do Fêmur", min_value=0.0, value=diam_femur_default, step=0.01, format="%.2f")

                if alt > 0 and diam_punho > 0 and diam_femur > 0:
                    h_m = alt
                    r_m = diam_punho / 100
                    f_m = diam_femur / 100
                    peso_osseo = 3.02 * ((h_m ** 2 * r_m * f_m * 400) ** 0.712)

                if peso > 0:
                    peso_residual = peso * (0.241 if sexo == "Masculino" else 0.209)

                if peso > 0 and massa_gorda > 0 and peso_osseo > 0:
                    massa_muscular = peso - (massa_gorda + peso_osseo + peso_residual)

                if peso > 0 and bio_gord > 0:
                    bio_massa_magra_pct = max(0.0, 100.0 - bio_gord)
                    bio_massa_gorda = peso * (bio_gord / 100)
                    bio_massa_magra = peso - bio_massa_gorda

                if gordura_calc > 0:
                    classif_gord_dobras = _classificar_gordura(sexo, idade, gordura_calc)
                    classif_gord_dobras_nih = _classificar_gordura_nih(sexo, idade, gordura_calc)
                if bio_gord > 0:
                    classif_gord_bio = _classificar_gordura(sexo, idade, bio_gord)
                    classif_gord_bio_nih = _classificar_gordura_nih(sexo, idade, bio_gord)
                if visc > 0:
                    classif_visc = _classificar_gordura_visceral(visc)
                if musc_pct > 0:
                    classif_musc = _classificar_musculo_esqueletico(sexo, idade, musc_pct)

                if bio_gord > 0:
                    massa_magra_base_pct = 100.0 - bio_gord
                    massa_magra_base_desc = "Bioimpedância"
                elif gordura_calc > 0:
                    massa_magra_base_pct = 100.0 - gordura_calc
                    massa_magra_base_desc = "Dobras"

                if peso > 0:
                    mm_min, mm_max = _faixa_massa_magra_ideal(sexo, idade)
                    massa_magra_ideal_pct_min = mm_min
                    massa_magra_ideal_pct_max = mm_max
                    massa_magra_ideal_kg_min = peso * (mm_min / 100)
                    massa_magra_ideal_kg_max = peso * (mm_max / 100)

                    if gordura_calc > 0:
                        mm_pct_dobras = 100.0 - gordura_calc
                        if mm_pct_dobras < mm_min:
                            mm_status_dobras = "Abaixo do ideal"
                        elif mm_pct_dobras > mm_max:
                            mm_status_dobras = "Acima do ideal"
                        else:
                            mm_status_dobras = "Dentro da faixa ideal"
                    if bio_gord > 0:
                        mm_pct_bio = 100.0 - bio_gord
                        if mm_pct_bio < mm_min:
                            mm_status_bio = "Abaixo do ideal"
                        elif mm_pct_bio > mm_max:
                            mm_status_bio = "Acima do ideal"
                        else:
                            mm_status_bio = "Dentro da faixa ideal"

                    if massa_magra_base_pct is not None:
                        if massa_magra_base_pct < mm_min:
                            massa_magra_status = "Abaixo do ideal (possível perda de massa magra)"
                        elif massa_magra_base_pct > mm_max:
                            massa_magra_status = "Acima do ideal"
                        else:
                            massa_magra_status = "Dentro da faixa ideal"

                if peso > 0 and (gordura_calc > 0 or bio_gord > 0):
                    resumo_items = []
                    if gordura_calc > 0:
                        txt = f"<b>% Gordura (Pollock):</b> {gordura_calc:.2f}%"
                        if classif_gord_dobras_nih:
                            txt += f" ({classif_gord_dobras_nih})"
                        resumo_items.append(txt)
                    if bio_gord > 0:
                        txt = f"<b>% Gordura (Bioimpedância):</b> {bio_gord:.2f}%"
                        if classif_gord_bio_nih:
                            txt += f" ({classif_gord_bio_nih})"
                        resumo_items.append(txt)
                    if bio_massa_magra_pct > 0:
                        resumo_items.append(f"<b>% Massa magra (Bioimpedância):</b> {bio_massa_magra_pct:.2f}%")
                    if musc_pct > 0:
                        tag = f" ({classif_musc})" if classif_musc else ""
                        resumo_items.append(f"<b>% Músculo esquelético:</b> {musc_pct:.2f}%{tag}")

                    resumo_html = " &nbsp;|&nbsp; ".join(resumo_items) if resumo_items else "—"

                    linhas = []
                    if massa_gorda > 0:
                        tag = f" ({classif_gord_dobras_nih})" if classif_gord_dobras_nih else ""
                        linhas.append(f"<b>Massa gorda (Pollock):</b> {massa_gorda:.2f} kg{tag}")
                    if massa_magra > 0:
                        tag = f" ({mm_status_dobras})" if mm_status_dobras else ""
                        linhas.append(f"<b>Massa magra (Pollock):</b> {massa_magra:.2f} kg{tag}")
                    if bio_massa_gorda > 0:
                        tag = f" ({classif_gord_bio_nih})" if classif_gord_bio_nih else ""
                        linhas.append(f"<b>Massa gorda (Bioimpedância):</b> {bio_massa_gorda:.2f} kg{tag}")
                    if bio_massa_magra > 0:
                        tag = f" ({mm_status_bio})" if mm_status_bio else ""
                        linhas.append(f"<b>Massa magra (Bioimpedância):</b> {bio_massa_magra:.2f} kg{tag}")
                    if visc > 0:
                        tag = f" ({classif_visc})" if classif_visc else ""
                        linhas.append(f"<b>Gordura visceral:</b> {visc}{tag}")
                    if agua_corporal > 0:
                        linhas.append(f"<b>Água corporal:</b> {agua_corporal:.2f} L")
                    if bio_massa_ossea > 0:
                        linhas.append(f"<b>Massa óssea (Bioimpedância):</b> {bio_massa_ossea:.2f} kg")
                    if peso_osseo > 0:
                        linhas.append(f"<b>Peso ósseo (diâmetros):</b> {peso_osseo:.2f} kg")
                    if peso_residual > 0:
                        linhas.append(f"<b>Peso residual:</b> {peso_residual:.2f} kg")
                    if massa_muscular > 0:
                        linhas.append(f"<b>Massa muscular estimada:</b> {massa_muscular:.2f} kg")

                    if massa_magra_ideal_pct_min is not None and massa_magra_ideal_pct_max is not None:
                        linhas.append(
                            f"<b>Faixa ideal de massa magra (idade):</b> {massa_magra_ideal_kg_min:.2f}–{massa_magra_ideal_kg_max:.2f} kg "
                            f"({massa_magra_ideal_pct_min:.1f}–{massa_magra_ideal_pct_max:.1f}%)"
                        )
                    if massa_magra_status:
                        base_txt = f" — base {massa_magra_base_desc}" if massa_magra_base_desc else ""
                        linhas.append(f"<b>Status de massa magra:</b> {massa_magra_status}{base_txt}")

                    detalhes_html = "<br>".join(linhas) if linhas else "—"

                    st.markdown(
                        f"""
                        <div class="dh-panel">
                            <h4>Composição Corporal Completa</h4>
                            <div class="dh-pill-soft">
                              {resumo_html}
                            </div>
                            <br>
                            {detalhes_html}
                        </div>
                        """,
                        unsafe_allow_html=True
                    )

                nota = st.text_area("Evolução / Anamnese", value=ult_ad_nota)

                if st.form_submit_button("💾 Salvar Avaliação Completa"):
                    user_obj = _current_user_obj()
                    if _is_free_user(user_obj):
                        remaining = _free_anthro_remaining(user_obj)
                        if remaining <= 0:
                            st.error("Limite diário do plano básico atingido (3 avaliações/dia). Assine o premium para acesso completo.")
                            st.stop()
                        _increment_free_anthro_usage(user_obj, 1)
                    reg = {
                        "data": str(datetime.now().date()),
                        "dados_vitais": {
                            "idade": idade, "idade_meses": meses, "sexo": sexo, "peso": peso, "altura": alt, "imc": imc,
                            "visceral": visc, "bioimpedancia": bio_gord,
                            "bio_percentual_massa_magra": bio_massa_magra_pct if bio_gord > 0 else None,
                            "bio_massa_gorda": bio_massa_gorda if bio_gord > 0 else None,
                            "bio_massa_magra": bio_massa_magra if bio_gord > 0 else None,
                            "agua_corporal": agua_corporal if agua_corporal > 0 else None,
                            "bio_massa_ossea": bio_massa_ossea if bio_massa_ossea > 0 else None,
                            "classificacao_gordura_bio": classif_gord_bio or None,
                            "classificacao_gordura_bio_nih": classif_gord_bio_nih or None,
                            "classificacao_gordura_visceral": classif_visc or None,
                            "bio_musculo_esqueletico_pct": musc_pct if musc_pct > 0 else None,
                            "classificacao_musculo_esqueletico": classif_musc or None,
                            "massa_magra_ideal_pct_min": massa_magra_ideal_pct_min,
                            "massa_magra_ideal_pct_max": massa_magra_ideal_pct_max,
                            "massa_magra_ideal_kg_min": massa_magra_ideal_kg_min,
                            "massa_magra_ideal_kg_max": massa_magra_ideal_kg_max,
                            "status_massa_magra": massa_magra_status or None,
                            "massa_magra_base": massa_magra_base_desc or None
                        },
                        "perimetria": {"torax": torax, "cintura": cint, "abdomen": abd, "quadril": quad, "rcq": (cint / quad) if (cint > 0 and quad > 0) else 0},
                        "dobras": {
                            "triceps": tri, "biceps": bi, "subescapular": sub, "suprailiaca": supra,
                            "peitoral": peit, "axilar": axil, "abdominal": abdo, "coxa": coxa,
                            "percentual_gordura": gordura_calc if gordura_calc > 0 else None,
                            "classificacao_gordura_dobras": classif_gord_dobras or None,
                            "classificacao_gordura_dobras_nih": classif_gord_dobras_nih or None,
                            "massa_gorda": massa_gorda if massa_gorda > 0 else None,
                            "massa_magra": massa_magra if massa_magra > 0 else None,
                            "massa_muscular": massa_muscular if massa_muscular > 0 else None,
                            "peso_osseo": peso_osseo if peso_osseo > 0 else None,
                            "peso_residual": peso_residual if peso_residual > 0 else None
                        },
                        "medidas": {
                            "braco_d_rel": br_d_rel, "braco_e_rel": br_e_rel,
                            "braco_d_con": br_d_con, "braco_e_con": br_e_con,
                            "coxa_prox_d": cx_prox_d, "coxa_prox_e": cx_prox_e,
                            "coxa_med_d": cx_med_d, "coxa_med_e": cx_med_e,
                            "coxa_dist_d": cx_dist_d, "coxa_dist_e": cx_dist_e,
                            "panturrilha_d": pant_d, "panturrilha_e": pant_e,
                            "diam_umero": diam_umero, "diam_punho": diam_punho, "diam_femur": diam_femur
                        },
                        "nota": nota
                    }
                    p_obj["historico"].append(reg)
                    p_obj["idade"] = int(idade) if idade is not None else p_obj.get("idade")
                    p_obj["sexo"] = sexo or p_obj.get("sexo")
                    save_db("pacientes.json", pacientes)
                    st.success("Salvo com sucesso!")


    with tab_crianca:
        st.markdown("### 🧒 Antropometria OMS")
        st.markdown(
            '<div class="dh-pill-soft"><b>OMS ativa:</b> fluxo separado para <b>5–19 anos</b>, <b>0–5 anos</b> e <b>gestante</b>, preservando o prontuário e o vínculo do paciente.</div>',
            unsafe_allow_html=True,
        )

        perfil_labels = ["Criança / adolescente (OMS 5–19)", "Bebê / primeira infância (OMS 0–5)", "Gestante"]
        perfil_default = 2 if gestacao_flag else (1 if pac_age_months and pac_age_months < 61 else 0)
        perfil_antropometrico = st.radio(
            "Perfil antropométrico",
            perfil_labels,
            index=perfil_default,
            horizontal=True,
            key=f"dh_oms_profile_{(p_obj.get('id') or p_obj.get('nome') or 'paciente')}",
        )

        if perfil_antropometrico == "Criança / adolescente (OMS 5–19)":
            st.markdown(
                '<div class="dh-pill-soft">Use a referência OMS <b>5–19 anos</b> com <b>IMC/idade por z-score</b>. '
                'Classificação clínica: magreza acentuada, magreza, eutrofia, sobrepeso e obesidade.</div>',
                unsafe_allow_html=True,
            )

            idade_anos_base = int(pac_age_months // 12) if pac_age_months else (pac_idade if pac_idade else 5)
            idade_meses_base = int(pac_age_months % 12) if pac_age_months else 0

            with st.form("pront_child"):
                c1, c2, c3, c4 = st.columns(4)
                idade_anos_default = _clamp(_as_int(ult_ch_vitais.get("idade_anos"), idade_anos_base), 0, 19)
                idade_meses_default = _clamp(_as_int(ult_ch_vitais.get("idade_meses"), idade_meses_base), 0, 11)
                sexo_c_default = (ult_ch_vitais.get("sexo") or pac_sexo or "Masculino")
                sexo_c_index = 0 if _sexo_norm(sexo_c_default) == "Masculino" else 1
                peso_c_default = max(0.0, _as_float(ult_ch_vitais.get("peso"), 0.0))
                altura_cm_default = _clamp(_as_float(ult_ch_vitais.get("altura_cm"), 110.0), 0.0, 250.0)

                idade_anos = c1.number_input("Idade (anos)", min_value=0, max_value=19, value=idade_anos_default)
                idade_meses = c2.number_input("Meses (0-11)", min_value=0, max_value=11, value=idade_meses_default)
                sexo_c = c3.selectbox("Sexo", ["Masculino", "Feminino"], index=sexo_c_index)
                peso_c = c4.number_input("Peso (kg)", min_value=0.0, value=peso_c_default, step=0.01, format="%.2f")
                altura_cm = st.number_input("Altura (cm)", min_value=0.0, max_value=250.0, value=altura_cm_default, step=0.1, format="%.1f")

                idade_total_meses = int(idade_anos) * 12 + int(idade_meses)
                altura_m = (altura_cm / 100.0) if altura_cm > 0 else 0.0
                imc_c = (peso_c / (altura_m ** 2)) if (peso_c > 0 and altura_m > 0) else 0.0

                percentil_auto = None
                zscore_auto = None
                zscore_final = None
                percentil_final = None
                aviso_percentil = None

                if imc_c > 0 and 61 <= idade_total_meses <= 228:
                    try:
                        percentil_auto, zscore_auto = who_bmi_5_19_percentil(int(idade_total_meses), sexo_c, imc_c)
                    except Exception:
                        percentil_auto, zscore_auto = None, None
                elif imc_c > 0:
                    aviso_percentil = "Para a OMS 5–19, a idade deve ficar entre 61 e 228 meses. Para menores de 5 anos, use o perfil Bebê / 0–5 anos."

                if zscore_auto is None and imc_c > 0:
                    aviso_percentil = aviso_percentil or "Não consegui calcular automaticamente pela OMS 5–19. Você pode informar o z-score manualmente e salvar sem perder o fluxo."
                    zscore_final = st.slider("Z-score IMC/idade (manual - OMS 5–19)", -4.0, 4.0, 0.0, 0.1)
                    percentil_final = int(round(_norm_cdf(zscore_final) * 100.0))
                else:
                    zscore_final = float(zscore_auto) if zscore_auto is not None else None
                    percentil_final = int(round(percentil_auto)) if percentil_auto is not None else None

                classif_c = classificar_bmi_oms_5_19(zscore_final) if zscore_final is not None else ""

                if imc_c > 0:
                    txt = f"<b>IMC:</b> {imc_c:.2f} kg/m²"
                    if zscore_final is not None:
                        txt += (
                            f" &nbsp;|&nbsp; <b>Z-score OMS:</b> {zscore_final:.2f}"
                            f" &nbsp;|&nbsp; <b>Percentil:</b> {percentil_final}"
                            f" &nbsp;|&nbsp; <b>Classificação:</b> {classif_c}"
                        )
                    st.markdown(f'<div class="dh-pill-soft">{txt}</div>', unsafe_allow_html=True)

                if aviso_percentil:
                    st.warning(aviso_percentil)

                st.markdown("#### Medidas (opcional)")
                m1, m2, m3, m4 = st.columns(4)
                cabeca_default = max(0.0, _as_float(ult_ch_medidas.get("cabeca_cm"), 0.0))
                cintura_default = max(0.0, _as_float(ult_ch_medidas.get("cintura_cm"), 0.0))
                braco_default = max(0.0, _as_float(ult_ch_medidas.get("braco_cm"), 0.0))
                pant_default = max(0.0, _as_float(ult_ch_medidas.get("panturrilha_cm"), 0.0))
                cabeca = m1.number_input("Circunferência da cabeça (cm) — opcional", min_value=0.0, value=cabeca_default, step=0.1)
                cintura = m2.number_input("Cintura (cm) — opcional", min_value=0.0, value=cintura_default, step=0.1)
                braco = m3.number_input("Braço (cm) — opcional", min_value=0.0, value=braco_default, step=0.1)
                pant = m4.number_input("Panturrilha (cm) — opcional", min_value=0.0, value=pant_default, step=0.1)

                observacoes = st.text_area("Observações (OMS 5–19)", value=ult_ch_obs)
                ok_child = st.form_submit_button("💾 Salvar Avaliação OMS 5–19")

            if ok_child:
                user_obj = _current_user_obj()
                if _is_free_user(user_obj):
                    remaining = _free_anthro_remaining(user_obj)
                    if remaining <= 0:
                        st.error("Limite diário do plano básico atingido (3 avaliações/dia). Assine o premium para acesso completo.")
                        st.stop()
                    _increment_free_anthro_usage(user_obj, 1)
                reg = {
                    "tipo": "avaliacao_crianca",
                    "subtipo": "oms_5_19",
                    "data": datetime.now().strftime("%d/%m/%Y %H:%M"),
                    "dados_vitais": {
                        "idade_anos": int(idade_anos),
                        "idade_meses": int(idade_meses),
                        "idade_total_meses": int(idade_total_meses),
                        "sexo": sexo_c,
                        "peso": float(peso_c),
                        "altura_cm": float(altura_cm),
                        "imc": float(imc_c),
                        "imc_percentil": int(percentil_final) if percentil_final is not None else None,
                        "imc_zscore": round(float(zscore_final), 2) if zscore_final is not None else None,
                        "classificacao": classif_c if classif_c else None,
                        "referencia": "OMS 5-19"
                    },
                    "medidas": {
                        "cabeca_cm": float(cabeca),
                        "cintura_cm": float(cintura),
                        "braco_cm": float(braco),
                        "panturrilha_cm": float(pant)
                    },
                    "observacoes": observacoes
                }
                p_obj.setdefault("historico", []).append(reg)
                p_obj["idade"] = int(idade_anos) if idade_anos is not None else p_obj.get("idade")
                p_obj["sexo"] = sexo_c or p_obj.get("sexo")
                save_db("pacientes.json", pacientes)
                st.success("✅ Avaliação OMS 5–19 salva no histórico do paciente.")
                time.sleep(0.6)
                st.rerun()

        elif perfil_antropometrico == "Bebê / primeira infância (OMS 0–5)":
            st.markdown(
                '<div class="dh-pill-soft">Fluxo para <b>0–5 anos</b> com referência OMS em <b>IMC/idade</b>. '
                'A idade é calculada automaticamente pela data de nascimento quando disponível.</div>',
                unsafe_allow_html=True,
            )

            nasc_default = pac_dob or (hoje_ref - timedelta(days=min(max(pac_age_days, 30), 365 * 2)))
            sexo_bebe_default = (ult_bebe_vitais.get("sexo") or pac_sexo or "Masculino")
            sexo_bebe_index = 0 if _sexo_norm(sexo_bebe_default) == "Masculino" else 1

            with st.form("pront_bebe"):
                b1, b2, b3, b4 = st.columns(4)
                data_nascimento_bebe = b1.date_input("Data de nascimento", value=nasc_default, min_value=datetime(2000, 1, 1).date(), max_value=hoje_ref, format="DD/MM/YYYY")
                sexo_bebe = b2.selectbox("Sexo", ["Masculino", "Feminino"], index=sexo_bebe_index)
                peso_bebe_default = max(0.0, _as_float(ult_bebe_vitais.get("peso"), 0.0))
                altura_bebe_default = _clamp(_as_float(ult_bebe_vitais.get("altura_cm"), 75.0), 0.0, 150.0)
                peso_bebe = b3.number_input("Peso (kg)", min_value=0.0, value=peso_bebe_default, step=0.01, format="%.2f")
                altura_cm_bebe = b4.number_input("Altura (cm)", min_value=0.0, max_value=150.0, value=altura_bebe_default, step=0.1, format="%.1f")

                idade_dias_bebe = max(0, (hoje_ref - data_nascimento_bebe).days) if data_nascimento_bebe else 0
                idade_meses_bebe = round(idade_dias_bebe / 30.4375, 1) if idade_dias_bebe > 0 else 0.0
                altura_m_bebe = (altura_cm_bebe / 100.0) if altura_cm_bebe > 0 else 0.0
                imc_bebe = (peso_bebe / (altura_m_bebe ** 2)) if (peso_bebe > 0 and altura_m_bebe > 0) else 0.0

                percentil_bebe = None
                zscore_bebe = None
                zscore_bebe_final = None
                percentil_bebe_final = None
                aviso_bebe = None

                if imc_bebe > 0 and 0 <= idade_dias_bebe <= 1856:
                    try:
                        percentil_bebe, zscore_bebe = who_bmi_0_5_percentil(int(idade_dias_bebe), sexo_bebe, imc_bebe)
                    except Exception:
                        percentil_bebe, zscore_bebe = None, None
                elif imc_bebe > 0:
                    aviso_bebe = "A referência OMS 0–5 cobre até 1856 dias de vida. Para idade maior, use o perfil Criança / adolescente (OMS 5–19)."

                if zscore_bebe is None and imc_bebe > 0:
                    aviso_bebe = aviso_bebe or "Não consegui calcular automaticamente pela OMS 0–5. Você pode informar o z-score manualmente para não travar o atendimento."
                    zscore_bebe_final = st.slider("Z-score IMC/idade (manual - OMS 0–5)", -4.0, 4.0, 0.0, 0.1)
                    percentil_bebe_final = int(round(_norm_cdf(zscore_bebe_final) * 100.0))
                else:
                    zscore_bebe_final = float(zscore_bebe) if zscore_bebe is not None else None
                    percentil_bebe_final = int(round(percentil_bebe)) if percentil_bebe is not None else None

                classif_bebe = classificar_bmi_oms_0_5(zscore_bebe_final) if zscore_bebe_final is not None else ""

                if imc_bebe > 0:
                    txt = (
                        f"<b>Idade:</b> {idade_dias_bebe} dias ({idade_meses_bebe:.1f} meses)"
                        f" &nbsp;|&nbsp; <b>IMC:</b> {imc_bebe:.2f} kg/m²"
                    )
                    if zscore_bebe_final is not None:
                        txt += (
                            f" &nbsp;|&nbsp; <b>Z-score OMS:</b> {zscore_bebe_final:.2f}"
                            f" &nbsp;|&nbsp; <b>Percentil:</b> {percentil_bebe_final}"
                            f" &nbsp;|&nbsp; <b>Classificação:</b> {classif_bebe}"
                        )
                    st.markdown(f'<div class="dh-pill-soft">{txt}</div>', unsafe_allow_html=True)

                if aviso_bebe:
                    st.warning(aviso_bebe)

                st.markdown("#### Medidas (opcional)")
                bm1, bm2, bm3, bm4 = st.columns(4)
                cabeca_bebe_default = max(0.0, _as_float(ult_bebe_medidas.get("cabeca_cm"), 0.0))
                cintura_bebe_default = max(0.0, _as_float(ult_bebe_medidas.get("cintura_cm"), 0.0))
                braco_bebe_default = max(0.0, _as_float(ult_bebe_medidas.get("braco_cm"), 0.0))
                pant_bebe_default = max(0.0, _as_float(ult_bebe_medidas.get("panturrilha_cm"), 0.0))
                cabeca_bebe = bm1.number_input("Circunferência da cabeça (cm)", min_value=0.0, value=cabeca_bebe_default, step=0.1)
                cintura_bebe = bm2.number_input("Cintura (cm)", min_value=0.0, value=cintura_bebe_default, step=0.1)
                braco_bebe = bm3.number_input("Braço (cm)", min_value=0.0, value=braco_bebe_default, step=0.1)
                pant_bebe = bm4.number_input("Panturrilha (cm)", min_value=0.0, value=pant_bebe_default, step=0.1)

                obs_bebe = st.text_area("Observações (OMS 0–5)", value=ult_bebe_obs)
                ok_bebe = st.form_submit_button("💾 Salvar Avaliação OMS 0–5")

            if ok_bebe:
                user_obj = _current_user_obj()
                if _is_free_user(user_obj):
                    remaining = _free_anthro_remaining(user_obj)
                    if remaining <= 0:
                        st.error("Limite diário do plano básico atingido (3 avaliações/dia). Assine o premium para acesso completo.")
                        st.stop()
                    _increment_free_anthro_usage(user_obj, 1)
                reg = {
                    "tipo": "avaliacao_bebe",
                    "subtipo": "oms_0_5",
                    "data": datetime.now().strftime("%d/%m/%Y %H:%M"),
                    "dados_vitais": {
                        "idade_dias": int(idade_dias_bebe),
                        "idade_meses": float(idade_meses_bebe),
                        "sexo": sexo_bebe,
                        "peso": float(peso_bebe),
                        "altura_cm": float(altura_cm_bebe),
                        "imc": float(imc_bebe),
                        "imc_percentil": int(percentil_bebe_final) if percentil_bebe_final is not None else None,
                        "imc_zscore": round(float(zscore_bebe_final), 2) if zscore_bebe_final is not None else None,
                        "classificacao": classif_bebe if classif_bebe else None,
                        "referencia": "OMS 0-5"
                    },
                    "medidas": {
                        "cabeca_cm": float(cabeca_bebe),
                        "cintura_cm": float(cintura_bebe),
                        "braco_cm": float(braco_bebe),
                        "panturrilha_cm": float(pant_bebe)
                    },
                    "observacoes": obs_bebe
                }
                p_obj.setdefault("historico", []).append(reg)
                p_obj["data_nascimento"] = data_nascimento_bebe.strftime("%d/%m/%Y") if data_nascimento_bebe else p_obj.get("data_nascimento")
                p_obj["idade"] = int(idade_dias_bebe / 365.25) if idade_dias_bebe else p_obj.get("idade")
                p_obj["sexo"] = sexo_bebe or p_obj.get("sexo")
                save_db("pacientes.json", pacientes)
                st.success("✅ Avaliação OMS 0–5 salva no histórico do paciente.")
                time.sleep(0.6)
                st.rerun()

        else:
            st.markdown(
                '<div class="dh-pill-soft"><b>Gestante:</b> o sistema registra <b>IMC pré-gestacional pela OMS</b>, '
                '<b>ganho de peso atual</b> e dados de acompanhamento sem aplicar fórmula obstétrica fora de protocolo.</div>',
                unsafe_allow_html=True,
            )

            with st.form("pront_gestante"):
                g1, g2, g3, g4 = st.columns(4)
                idade_gest_default = _clamp(_as_int(ult_gest_vitais.get("idade"), pac_idade if pac_idade else 18), 0, 60)
                semanas_default = _clamp(_as_float(ult_gest_vitais.get("idade_gestacional_semanas"), 12.0 if gestacao_flag else 0.0), 0.0, 45.0)
                peso_pre_default = max(0.0, _as_float(ult_gest_vitais.get("peso_pre_gestacional"), 0.0))
                peso_atual_default = max(0.0, _as_float(ult_gest_vitais.get("peso"), 0.0))
                altura_gest_default = _clamp(_as_float(ult_gest_vitais.get("altura"), 1.60), 0.0, 2.50)

                idade_gest = g1.number_input("Idade", min_value=0, max_value=60, value=idade_gest_default)
                semanas_gest = g2.number_input("Idade gestacional (semanas)", min_value=0.0, max_value=45.0, value=semanas_default, step=0.1)
                peso_pre = g3.number_input("Peso pré-gestacional (kg)", min_value=0.0, value=peso_pre_default, step=0.01, format="%.2f")
                peso_atual = g4.number_input("Peso atual (kg)", min_value=0.0, value=peso_atual_default, step=0.01, format="%.2f")
                altura_gest = st.number_input("Altura (m)", min_value=0.00, max_value=2.50, value=altura_gest_default, step=0.01, format="%.2f")

                gg1, gg2 = st.columns(2)
                edema = gg1.selectbox("Edema", ["", "Não", "Leve", "Moderado", "Importante"], index=0)
                pa_text = gg2.text_input("PA / pressão arterial", value=str(ult_gest_vitais.get("pressao_arterial") or ""))

                trimestre = _trimestre_gestacional(semanas_gest)
                imc_pre = (peso_pre / (altura_gest ** 2)) if (peso_pre > 0 and altura_gest > 0) else 0.0
                classif_imc_pre = classificar_imc_adulto_oms(imc_pre) if imc_pre > 0 else ""
                ganho_gestacional = (peso_atual - peso_pre) if (peso_atual > 0 and peso_pre > 0) else 0.0

                if imc_pre > 0:
                    st.markdown(
                        f'<div class="dh-pill-soft"><b>Trimestre:</b> {trimestre or "—"}'
                        f' &nbsp;|&nbsp; <b>IMC pré-gestacional (OMS):</b> {imc_pre:.2f} kg/m²'
                        f' &nbsp;|&nbsp; <b>Classificação:</b> {classif_imc_pre or "—"}'
                        f' &nbsp;|&nbsp; <b>Ganho de peso atual:</b> {ganho_gestacional:.2f} kg</div>',
                        unsafe_allow_html=True,
                    )

                st.info("O ganho de peso gestacional deve ser interpretado com o protocolo obstétrico adotado no serviço. Aqui o sistema preserva a leitura pré-gestacional OMS e o acompanhamento evolutivo.")
                obs_gest = st.text_area("Observações (gestante)", value=ult_gest_obs)
                ok_gest = st.form_submit_button("💾 Salvar Avaliação Gestante")

            if ok_gest:
                user_obj = _current_user_obj()
                if _is_free_user(user_obj):
                    remaining = _free_anthro_remaining(user_obj)
                    if remaining <= 0:
                        st.error("Limite diário do plano básico atingido (3 avaliações/dia). Assine o premium para acesso completo.")
                        st.stop()
                    _increment_free_anthro_usage(user_obj, 1)
                reg = {
                    "tipo": "avaliacao_gestante",
                    "data": datetime.now().strftime("%d/%m/%Y %H:%M"),
                    "dados_vitais": {
                        "idade": int(idade_gest),
                        "sexo": "Feminino",
                        "idade_gestacional_semanas": float(semanas_gest),
                        "trimestre": trimestre or None,
                        "peso_pre_gestacional": float(peso_pre),
                        "peso": float(peso_atual),
                        "altura": float(altura_gest),
                        "imc_pre_gestacional": round(float(imc_pre), 2) if imc_pre > 0 else None,
                        "classificacao_imc_pre_gestacional": classif_imc_pre or None,
                        "ganho_gestacional_kg": round(float(ganho_gestacional), 2) if ganho_gestacional else None,
                        "edema": edema or None,
                        "pressao_arterial": pa_text or None,
                        "referencia": "OMS pré-gestacional"
                    },
                    "observacoes": obs_gest
                }
                p_obj.setdefault("historico", []).append(reg)
                p_obj["idade"] = int(idade_gest) if idade_gest is not None else p_obj.get("idade")
                p_obj["sexo"] = "Feminino"
                save_db("pacientes.json", pacientes)
                st.success("✅ Avaliação gestante salva no histórico do paciente.")
                time.sleep(0.6)
                st.rerun()

def _render_prescricao_workspace(title: str, subtitle: str, chips: list[str], accent: str = "green"):
    def _rx_fix(txt: str) -> str:
        raw = (txt or "").strip()
        if not raw:
            return raw
        raw = re.sub(r"\bRecibo\b", "Receituário", raw, flags=re.IGNORECASE)
        raw = re.sub(r"\bReceita\b", "Receituário", raw, flags=re.IGNORECASE)
        raw = re.sub(r"\bRecebimento\b", "Receituário", raw, flags=re.IGNORECASE)
        return raw

    title = _rx_fix(title)
    subtitle = _rx_fix(subtitle)
    chips = [_rx_fix(chip) for chip in (chips or [])]
    chip_items = "".join(f'<span class="dh-rx-chip">{html.escape(item)}</span>' for item in chips if item)
    accent_map = {
        "green": ("rgba(34,197,94,.14)", "rgba(34,197,94,.3)", "#d9ffea"),
        "blue": ("rgba(59,130,246,.14)", "rgba(59,130,246,.28)", "#dff1ff"),
    }
    badge_bg, badge_border, badge_text = accent_map.get(accent, accent_map["green"])
    st.markdown(
        f"""
        <style>
        .dh-rx-hero{{display:grid;grid-template-columns:1fr;gap:12px;padding:16px;border-radius:18px;border:1px solid rgba(96,165,250,.14);background:
          radial-gradient(circle at top left, rgba(34,197,94,.14), transparent 36%),
          radial-gradient(circle at bottom right, rgba(59,130,246,.16), transparent 34%),
          linear-gradient(135deg, rgba(9,20,37,.98), rgba(15,33,59,.95));box-shadow:0 18px 36px rgba(0,0,0,.2);margin-bottom:16px;}}
        .dh-rx-hero h2{{margin:0;color:#f8fbff;font-size:1.6rem;font-weight:850;letter-spacing:-.03em;line-height:1.12;}}
        .dh-rx-hero p{{margin:8px 0 0;color:#c1d2e5;line-height:1.55;max-width:720px;font-size:.95rem;}}
        .dh-rx-badge{{display:inline-flex;align-items:center;gap:6px;padding:7px 12px;border-radius:999px;background:{badge_bg};border:1px solid {badge_border};color:{badge_text};font-size:.74rem;font-weight:900;text-transform:uppercase;letter-spacing:.04em;box-shadow:0 6px 12px rgba(15,23,42,.08);}}
        .dh-rx-chip-row{{display:flex;flex-wrap:wrap;gap:8px;justify-content:flex-start;align-content:flex-start;}}
        .dh-rx-chip{{display:inline-flex;align-items:center;padding:7px 12px;border-radius:999px;background:rgba(255,255,255,.08);border:1px solid rgba(148,163,184,.16);color:#f3f8ff;font-size:.78rem;font-weight:800;box-shadow:0 8px 14px rgba(2,6,23,.08);}}
        .dh-rx-panel{{padding:14px;border-radius:16px;background:linear-gradient(180deg, rgba(15,26,46,.97), rgba(11,19,35,.96));border:1px solid rgba(255,255,255,.06);box-shadow:0 12px 22px rgba(0,0,0,.16);margin:0 0 12px;}}
        .dh-rx-panel h4{{margin:0 0 6px;color:#f4f8ff;font-size:.95rem;font-weight:840;letter-spacing:-.01em;}}
        .dh-rx-panel p{{margin:0;color:#bfd0df;line-height:1.55;font-size:.88rem;}}
        .dh-rx-patient-card{{padding:11px 13px;border-radius:14px;background:linear-gradient(180deg, rgba(255,255,255,.07), rgba(255,255,255,.045));border:1px solid rgba(148,163,184,.15);height:auto;margin-bottom:8px;box-shadow:0 10px 18px rgba(2,6,23,.08);}}
        .dh-rx-patient-card strong{{display:block;color:#f8fbff;font-size:.9rem;margin-bottom:4px;}}
        .dh-rx-patient-card span{{display:block;color:#abc0d7;font-size:.84rem;line-height:1.5;overflow-wrap:anywhere;}}
        .dh-rx-soft-tip{{padding:11px 13px;border-radius:14px;background:linear-gradient(180deg, rgba(22,101,52,.28), rgba(6,78,59,.24));border:1px solid rgba(52,211,153,.24);color:#e9fff3 !important;line-height:1.5;margin:6px 0 12px;font-weight:750;box-shadow:0 8px 16px rgba(0,0,0,.08);}}
        .dh-rx-info-grid{{display:grid;grid-template-columns:1fr;gap:10px;margin:4px 0 12px;}}
        .dh-rx-info-card{{padding:12px;border-radius:14px;background:linear-gradient(180deg, rgba(255,255,255,.07), rgba(255,255,255,.045));border:1px solid rgba(148,163,184,.14);box-shadow:0 10px 18px rgba(2,6,23,.08);}}
        .dh-rx-info-card h5{{margin:0 0 6px;color:#f8fbff;font-size:.92rem;font-weight:840;letter-spacing:-.01em;}}
        .dh-rx-info-card p,.dh-rx-info-card li{{margin:0;color:#c3d4e6;line-height:1.5;font-size:.86rem;}}
        .dh-rx-info-card ul{{margin:0;padding-left:18px;display:grid;gap:6px;}}
        .dh-rx-choice-card{{padding:14px 14px 12px;border-radius:18px;background:
          radial-gradient(circle at top right, rgba(59,130,246,.12), transparent 38%),
          linear-gradient(180deg, rgba(255,255,255,.07), rgba(255,255,255,.045));border:1px solid rgba(148,163,184,.16);box-shadow:0 12px 20px rgba(2,6,23,.1);margin-bottom:10px;}}
        .dh-rx-choice-card h5{{margin:0 0 5px;color:#f8fbff;font-size:.92rem;font-weight:840;letter-spacing:-.01em;}}
        .dh-rx-choice-card p{{margin:0;color:#bfd1e3;font-size:.86rem;line-height:1.5;}}
        .dh-rx-choice-note{{padding:10px 12px;border-radius:14px;background:rgba(59,130,246,.1);border:1px solid rgba(96,165,250,.18);color:#dbeafe;line-height:1.5;font-size:.84rem;margin:6px 0 14px;}}
        .dh-rx-kpi-grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:12px;margin:12px 0 16px;}}
        .dh-rx-kpi{{padding:12px 13px;border-radius:16px;background:linear-gradient(180deg, rgba(15,23,42,.9), rgba(9,16,31,.86));border:1px solid rgba(148,163,184,.12);box-shadow:0 10px 18px rgba(2,6,23,.08);min-height:80px;}}
        .dh-rx-kpi strong{{display:block;color:#f8fbff;font-size:1.08rem;line-height:1.1;margin-bottom:3px;}}
        .dh-rx-kpi span{{display:block;color:#a9bfd6;font-size:.8rem;line-height:1.45;}}
        .dh-rx-hero + div, .dh-rx-panel + div[data-testid="stSelectbox"], .dh-rx-patient-card + .dh-rx-patient-card{{margin-top:0;}}
        a.dh-btn, a.dh-btn:visited{{text-decoration:none !important;}}
        a.dh-btn-green, a.dh-btn-green:visited{{display:inline-flex;align-items:center;justify-content:center;min-height:48px;padding:0 18px;border-radius:14px;background:linear-gradient(135deg, #22c55e, #16a34a) !important;color:#ffffff !important;font-weight:800 !important;box-shadow:0 14px 28px rgba(34,197,94,.22);}}
        a.dh-btn-green:hover{{transform:translateY(-1px);filter:brightness(1.03);}}
        @media (max-width:960px){{
          .dh-rx-hero{{grid-template-columns:1fr;}}
          .dh-rx-chip-row{{justify-content:flex-start;}}
          .dh-rx-info-grid,.dh-rx-kpi-grid{{grid-template-columns:1fr;}}
          .dh-rx-choice-card{{margin-bottom:16px;}}
        }}
        </style>
        <div class="dh-rx-hero">
          <div>
            <div class="dh-rx-badge">Workspace clínico</div>
            <h2>{html.escape(title)}</h2>
            <p>{html.escape(subtitle)}</p>
          </div>
          <div class="dh-rx-chip-row">{chip_items}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

def _prescricao_common_context(prefix: str, panel_title: str, panel_text: str):
    meus_pacientes = filtrar_por_usuario(pacientes)
    lista_p = [p["nome"] for p in meus_pacientes]
    if not lista_p:
        st.warning("Cadastre um paciente primeiro.")
        return None, None, "", "", []

    st.markdown(f'<div class="dh-rx-panel"><h4>{html.escape(panel_title)}</h4><p>{html.escape(panel_text)}</p></div>', unsafe_allow_html=True)
    paciente_sel = st.selectbox("Selecione o paciente", lista_p, key=f"{prefix}_paciente")
    p_obj = get_paciente_obj(paciente_sel)
    p_cols = st.columns(2)
    p_cols[0].markdown(f'<div class="dh-rx-patient-card"><strong>Paciente</strong><span>{html.escape(paciente_sel)}</span></div>', unsafe_allow_html=True)
    p_cols[1].markdown(f'<div class="dh-rx-patient-card"><strong>WhatsApp</strong><span>{html.escape((p_obj or {}).get("telefone") or "Não informado")}</span></div>', unsafe_allow_html=True)
    st.markdown(f'<div class="dh-rx-patient-card"><strong>CPF / Documento</strong><span>{html.escape(_patient_record_cpf(p_obj) or (p_obj or {}).get("documento") or "Não informado")}</span></div>', unsafe_allow_html=True)

    st.markdown('<div class="dh-rx-panel"><h4>Assinatura profissional</h4><p>Esses dados são aplicados no PDF final para manter o documento pronto para envio ou impressão.</p></div>', unsafe_allow_html=True)
    c_prof1, c_prof2 = st.columns(2)
    nome_prof = c_prof1.text_input("Seu nome completo", key=f"{prefix}_prof_name")
    reg_prof = c_prof2.text_input("Seu registro (CRN/CRM)", key=f"{prefix}_prof_reg")
    return paciente_sel, p_obj, nome_prof, reg_prof, meus_pacientes

def _render_document_whatsapp_box(prefix: str, paciente_sel: str, p_obj: dict, titulo: str, msg_base: str):
    st.markdown(f'<div class="dh-rx-panel"><h4>{html.escape(titulo)}</h4><p>Use o WhatsApp do paciente já cadastrado para agilizar o envio operacional do documento.</p></div>', unsafe_allow_html=True)
    tel_default = (p_obj.get("telefone") if p_obj else "") or ""
    tel_wa = st.text_input("WhatsApp do paciente", value=tel_default, key=f"{prefix}_wa_tel")
    msg_edit = st.text_area("Mensagem para WhatsApp", value=msg_base, height=120, key=f"{prefix}_wa_msg")
    wa = _wa_link(tel_wa, msg_edit)
    if wa:
        st.markdown(f'<a class="dh-btn dh-btn-green" href="{wa}" target="_blank">Enviar WhatsApp</a>', unsafe_allow_html=True)
        st.caption("Anexe o PDF baixado no WhatsApp.")
    else:
        st.caption("Informe o número do WhatsApp do paciente para gerar o link.")

def modulo_prescricoes(view: str = "receituario"):
    is_exam_view = (view or "").strip().lower() == "pedidos_exames"
    if is_exam_view:
        st.title("🩸 Pedido de Exames")
        _render_prescricao_workspace(
            "Pedido de exames",
            "Esta área agora é exclusiva para solicitação de exames. O receituário ficou separado para evitar mistura de fluxos e deixar a operação mais clara.",
            ["Fluxo separado", "Pedido objetivo", "PDF assinado", "WhatsApp rápido"],
            accent="blue",
        )
        paciente_sel, p_obj, nome_prof, reg_prof, _ = _prescricao_common_context(
            "exam",
            "Solicitação clínica",
            "Monte um pedido de exames limpo, objetivo e com melhor leitura para o paciente e para o laboratório.",
        )
        if not paciente_sel:
            return
        anamnese = get_anamnese_paciente(p_obj)
        anamnese_txt_exam = "\n".join(_anamnese_lines(anamnese))

        st.markdown('<div class="dh-rx-soft-tip">Aqui ficam apenas pedidos de exames. Receituário não aparece mais neste módulo.</div>', unsafe_allow_html=True)
        st.markdown(
            """
            <div class="dh-rx-info-grid">
              <div class="dh-rx-info-card">
                <h5>Fluxo recomendado</h5>
                <ul>
                  <li>Descreva a indicação clínica do pedido.</li>
                  <li>Marque os exames essenciais e complemente se necessário.</li>
                  <li>Baixe o PDF já com assinatura e envie ao paciente.</li>
                </ul>
              </div>
              <div class="dh-rx-info-card">
                <h5>Padrão premium</h5>
                <p>O documento fica mais limpo quando a justificativa clínica e as observações são curtas, objetivas e coerentes com o caso.</p>
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        indicacao = st.text_area(
            "Objetivo clínico / justificativa",
            placeholder="Ex: investigar resistência insulínica, fadiga persistente, monitoramento de perfil lipídico, controle de deficiência nutricional.",
            key="exam_indicacao",
            height=120,
        )
        observacoes = st.text_area(
            "Observações adicionais para o pedido",
            placeholder="Ex: realizar em jejum, considerar coleta matinal, correlacionar com sintomas e histórico do paciente.",
            key="exam_observacoes",
            height=110,
        )
        exam_topics = _clinical_ai_topics(indicacao, observacoes, anamnese_txt_exam)
        exam_guided_items = recommend_exams_for_topics(exam_topics)
        if exam_topics:
            chips = "".join(f'<span class="dh-rx-chip">{html.escape(item)}</span>' for item in exam_guided_items)
            st.markdown(
                f"""
                <div class="dh-rx-panel">
                  <h4>Base clínica complementar ativa</h4>
                  <p>Tópicos reconhecidos: {html.escape(", ".join(topic.get("label") or "-" for topic in exam_topics))}.</p>
                  <p>Esses exames podem ser úteis como apoio ao seu julgamento clínico, conforme o contexto do caso:</p>
                  <div class="dh-rx-chip-row" style="justify-content:flex-start;">{chips}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        apply_exam_guided = st.checkbox(
            "Somar exames sugeridos pela base clínica",
            value=bool(exam_guided_items),
            key="exam_apply_guided",
            help="Aplica automaticamente os exames sugeridos pela base SBD/OMS junto da sua seleção manual.",
        )
        exam_presets = {
            "Metabólico": ["Hemograma completo", "Perfil lipídico", "Glicemia e insulina", "TGO e TGP", "PCR ultrassensível"],
            "Hormonal": ["TSH e T4 livre", "Cortisol basal"],
            "Intestinal": ["Hemograma completo", "Ferritina", "Vitamina B12", "PCR ultrassensível"],
            "Esportivo": ["Hemograma completo", "Creatinina e ureia", "Ferritina", "Vitamina D", "Magnésio sérico", "CK total"],
            "Deficiências nutricionais": ["Ferritina", "Vitamina D", "Vitamina B12", "Zinco sérico", "Ácido fólico"],
        }
        st.markdown('<div class="dh-rx-panel"><h4>Grupos clínicos prontos</h4><p>Use presets para montar o pedido mais rápido. Eles não substituem seu julgamento clínico: servem como ponto de partida operacional.</p></div>', unsafe_allow_html=True)
        preset_sel = st.multiselect(
            "Aplicar grupos clínicos",
            list(exam_presets.keys()),
            default=[],
            key="exam_presets",
            help="Os exames desses grupos serão somados ao pedido final automaticamente.",
        )
        preset_items = []
        for group in preset_sel:
            preset_items.extend(exam_presets.get(group, []))
        preset_items = list(dict.fromkeys(preset_items))
        if preset_sel:
            preset_html = "".join(f'<span class="dh-rx-chip">{html.escape(item)}</span>' for item in preset_items)
            st.markdown(f'<div class="dh-rx-panel"><h4>Exames sugeridos pelos grupos selecionados</h4><div class="dh-rx-chip-row" style="justify-content:flex-start;">{preset_html}</div></div>', unsafe_allow_html=True)
        st.markdown('<div class="dh-rx-panel"><h4>Seleção de exames</h4><p>Escolha os exames principais e acrescente exames complementares quando necessário.</p></div>', unsafe_allow_html=True)
        g1, g2 = st.columns(2)
        with g1:
            st.markdown('<div class="dh-rx-choice-card"><h5>Metabólico e inflamatório</h5><p>Selecione os exames mais usados para avaliação metabólica, inflamatória e monitoramento nutricional.</p></div>', unsafe_allow_html=True)
            e1 = st.checkbox("Hemograma completo", key="exam_hmg")
            e2 = st.checkbox("Perfil lipídico", key="exam_lipid")
            e3 = st.checkbox("Glicemia e insulina", key="exam_glic")
            e4 = st.checkbox("TGO / TGP", key="exam_tgo")
            e5 = st.checkbox("Cortisol basal", key="exam_cort")
        with g2:
            st.markdown('<div class="dh-rx-choice-card"><h5>Micronutrientes e apoio clínico</h5><p>Use este bloco para carências nutricionais, marcadores complementares e apoio à correlação clínica.</p></div>', unsafe_allow_html=True)
            e6 = st.checkbox("Vitamina D / B12", key="exam_vits")
            e7 = st.checkbox("Ferritina", key="exam_ferritina")
            e8 = st.checkbox("TSH / T4 livre", key="exam_tireoide")
            e9 = st.checkbox("Creatinina / ureia", key="exam_renal")
            e10 = st.checkbox("PCR ultrassensível", key="exam_pcr")
        exames_base_count = sum(bool(x) for x in [e1, e2, e3, e4, e5, e6, e7, e8, e9, e10])
        st.markdown('<div class="dh-rx-choice-note">Os blocos acima foram organizados para reduzir ruído visual e facilitar a montagem do pedido sem misturar exames metabólicos com marcadores de apoio clínico.</div>', unsafe_allow_html=True)
        exames_custom = st.text_area(
            "Exames complementares personalizados",
            placeholder="Ex: zinco sérico, magnésio, homocisteína, testosterona total e livre, ácido fólico.",
            key="exam_custom_list",
            height=120,
        )
        extras_preview = [x.strip(" -•\t") for x in exames_custom.splitlines() if x.strip()]
        st.markdown(
            f"""
            <div class="dh-rx-kpi-grid">
              <div class="dh-rx-kpi"><strong>{exames_base_count}</strong><span>exames principais selecionados</span></div>
              <div class="dh-rx-kpi"><strong>{len(preset_sel)}</strong><span>grupos clínicos aplicados</span></div>
              <div class="dh-rx-kpi"><strong>{len(extras_preview)}</strong><span>itens complementares personalizados</span></div>
              <div class="dh-rx-kpi"><strong>{'Sim' if indicacao.strip() else 'Não'}</strong><span>justificativa clínica preenchida</span></div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        if st.button("Gerar pedido de exames", key="exam_generate_pdf", use_container_width=True):
            selecionados = []
            if e1: selecionados.append("Hemograma completo")
            if e2: selecionados.append("Perfil lipídico")
            if e3: selecionados.append("Glicemia e insulina")
            if e4: selecionados.append("TGO e TGP")
            if e5: selecionados.append("Cortisol basal")
            if e6: selecionados.append("Vitaminas D e B12")
            if e7: selecionados.append("Ferritina")
            if e8: selecionados.append("TSH e T4 livre")
            if e9: selecionados.append("Creatinina e ureia")
            if e10: selecionados.append("PCR ultrassensível")
            selecionados.extend(preset_items)
            if apply_exam_guided:
                selecionados.extend(exam_guided_items)
            extras = [x.strip(" -•\t") for x in exames_custom.splitlines() if x.strip()]
            selecionados.extend(extras)
            selecionados = list(dict.fromkeys(selecionados))
            if not selecionados:
                st.warning("Selecione pelo menos um exame ou informe exames complementares personalizados.")
            else:
                corpo = [f"PEDIDO DE EXAMES - {paciente_sel}", ""]
                if indicacao.strip():
                    corpo.extend(["Indicação clínica:", indicacao.strip(), ""])
                if preset_sel:
                    corpo.extend(["Grupos clínicos utilizados:", ", ".join(preset_sel), ""])
                corpo.append("Solicito os seguintes exames:")
                corpo.extend([f"- {item}" for item in selecionados])
                if observacoes.strip():
                    corpo.extend(["", "Observações:", observacoes.strip()])
                lista = _beautify_generated_text("\n".join(corpo))
                pdf_ex = gerar_pdf_pro(paciente_sel, lista, "PEDIDO DE EXAMES", nome_prof, reg_prof)
                st.session_state["exames_pdf"] = pdf_ex
                st.session_state["temp_exames"] = lista
                st.download_button("📥 Baixar pedido em PDF", pdf_ex, "pedido_exames.pdf", "application/pdf")
        if st.session_state.get("temp_exames"):
            _render_generated_doc_preview("Pré-visualização do Pedido de Exames", st.session_state.get("temp_exames", ""), "Documento clínico • DietHealth")
            _render_document_whatsapp_box("exam", paciente_sel, p_obj, "Enviar pedido de exames por WhatsApp", f"Olá {paciente_sel}, segue o pedido de exames em PDF.")
        return

    st.title("💊 Receituário Nutricional")
    _render_prescricao_workspace(
        "Receituário nutricional",
        "Separei o receituário do pedido de exames. Aqui fica apenas a prescrição nutricional, com apoio de IA, assinatura profissional e fluxo rápido de envio ao paciente.",
        ["IA clínica", "PDF assinado", "WhatsApp rápido", "Fluxo separado do pedido de exames"],
        accent="green",
    )
    paciente_sel, p_obj, nome_prof, reg_prof, _ = _prescricao_common_context(
        "rx",
        "Receituário nutricional",
        "Monte um receituário mais técnico e legível, com base no prontuário e nas diretrizes da nutricionista.",
    )
    if not paciente_sel:
        return

    st.markdown('<div class="dh-rx-soft-tip">O receituário fica restrito à prescrição nutricional. Pedidos de exames agora possuem módulo próprio.</div>', unsafe_allow_html=True)
    anamnese = get_anamnese_paciente(p_obj)
    anamnese_linhas = _anamnese_lines(anamnese)
    historico_linhas = _historico_prescricao_lines(p_obj, max_entries=50)
    if anamnese_linhas or historico_linhas:
        st.caption("Anamnese e histórico do prontuário aplicados automaticamente no prompt da IA.")
    st.markdown(
        """
        <div class="dh-rx-info-grid">
          <div class="dh-rx-info-card">
            <h5>O que entra no receituário</h5>
            <ul>
              <li>Prescrição alimentar.</li>
              <li>Suplementos, bioativos e fitoterápicos.</li>
              <li>Formulações magistrais quando fizer sentido clínico.</li>
            </ul>
          </div>
          <div class="dh-rx-info-card">
            <h5>Boas práticas</h5>
            <p>Quanto mais claro o objetivo clínico e as diretrizes do profissional, mais técnico e utilizável fica o receituário gerado pela IA.</p>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    sintomas = st.text_area(
            "Deficiências / necessidades clínicas e objetivo",
            placeholder="Ex: intolerância à lactose, baixa ingestão proteica, disbiose intestinal, deficiência de vitamina D, objetivo de hipertrofia.",
            key="rx_sintomas",
            height=130,
    )
    diretrizes = st.text_area(
        "Diretrizes do profissional",
        placeholder="Ex: priorizar cápsulas, evitar cafeína noturna, foco em adesão, evitar compostos alergênicos.",
        key="rx_diretrizes",
        height=120,
    )
    rx_ai_topics = _clinical_ai_topics(
        sintomas,
        diretrizes,
        "\n".join(anamnese_linhas),
        "\n".join(historico_linhas),
    )
    rx_ai_prompt_block = _clinical_ai_prompt(
        "receituario",
        sintomas,
        diretrizes,
        "\n".join(anamnese_linhas),
        "\n".join(historico_linhas),
    )
    if rx_ai_topics:
        st.markdown(
            f'''
            <div class="dh-pill-soft">
              <b>Base SBD/OMS aplicada:</b> {", ".join(topic.get("label") or "-" for topic in rx_ai_topics)}.
              O receituário vai respeitar escopo nutricional, comorbidades e pontos de cautela clínica.
            </div>
            ''',
            unsafe_allow_html=True,
        )
    categorias_all = [
        "Suplementos e produtos bioativos",
        "Fitoterápicos (plantas, chás e drogas vegetais)",
        "MIPs baseados em nutrientes",
        "Nutrição enteral (oral ou via sonda)",
        "Chás naturais",
    ]
    st.markdown("Categorias para incluir no receituário")
    categorias_sel = []
    cat_cols = st.columns(2)
    for idx, cat in enumerate(categorias_all):
        col = cat_cols[idx % 2]
        key = f"rx_cat_{idx}"
        checked = col.checkbox(cat, value=st.session_state.get(key, True), key=key)
        if checked:
            categorias_sel.append(cat)
    st.markdown(
        f"""
        <div class="dh-rx-kpi-grid">
          <div class="dh-rx-kpi"><strong>{len(categorias_sel)}</strong><span>categorias clínicas selecionadas</span></div>
          <div class="dh-rx-kpi"><strong>{'Sim' if sintomas.strip() else 'Não'}</strong><span>objetivo clínico preenchido</span></div>
          <div class="dh-rx-kpi"><strong>{'Sim' if diretrizes.strip() else 'Não'}</strong><span>diretrizes profissionais adicionadas</span></div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    if st.button("🤖 Gerar receituário com IA", key="rx_generate_ai", use_container_width=True):
        if not ia_ok():
            st.error("Configure a GROQ_API_KEY (Secrets ou variável de ambiente).")
        elif not sintomas.strip():
            st.warning("Informe as deficiências/necessidades clínicas para gerar uma prescrição objetiva.")
        else:
            client = get_groq_client()
            if client is None:
                st.error("GROQ_API_KEY nao encontrada. Configure a variavel no Railway e reinicie o servico.")
                st.stop()
            with st.spinner("Gerando receituário premium..."):
                try:
                    anamnese_txt = "\n".join(anamnese_linhas) if anamnese_linhas else "- Sem anamnese estruturada no prontuário."
                    historico_txt = "\n".join(historico_linhas) if historico_linhas else "- Sem histórico clínico registrado no prontuário."
                    categorias_txt = ", ".join(categorias_sel) if categorias_sel else ", ".join(categorias_all)
                    prompt = f"""
Você é um nutricionista clínico e deve gerar um RECEITUÁRIO NUTRICIONAL.
NÃO gerar receitas culinárias, ingredientes culinários, modo de preparo ou texto em estilo de bula.
NÃO gerar texto de orientação genérica; gerar somente prescrição direta e objetiva.

ESCOPO DE PRESCRIÇÃO (somente dentro deste escopo)
- Suplementos e produtos bioativos: nutrientes (vitaminas/minerais), substâncias bioativas, probióticos, alimentos apícolas e novos alimentos autorizados pela ANVISA.
- Fitoterápicos: plantas in natura, chás e drogas vegetais.
- MIPs: apenas os baseados em nutrientes (vitaminas/proteínas).
- Nutrição enteral: alimentos para dietas via sonda ou oral.
- Chás naturais.

CONDIÇÃO / OBJETIVO
{sintomas}

DIRETRIZES ADICIONAIS DO PROFISSIONAL
{diretrizes if diretrizes.strip() else "Nenhuma."}

ANAMNESE / PRONTUÁRIO
{anamnese_txt}

HISTÓRICO CLÍNICO CONSOLIDADO DO PRONTUÁRIO
{historico_txt}

CATEGORIAS SELECIONADAS
{categorias_txt}

BASE CLINICA COMPLEMENTAR
{rx_ai_prompt_block if rx_ai_prompt_block else "Sem topicos especificos reconhecidos. Manter postura conservadora, alimentacao adequada e foco em seguranca clinica."}

REQUISITOS
1) Título: "RECEITUÁRIO NUTRICIONAL PADRÃO".
2) Estrutura obrigatória de saída:
   - Seção 1: Prescrição Alimentar
   - Seção 2: Suplementos e Fitoterápicos
   - Seção 3: Formulações Magistrais (quando aplicável)
   - Seção 4: Cuidados e Contraindicações
3) Em TODAS as seções, escrever em formato de prescrição clínica (não orientação).
4) Proibido usar frases genéricas como: "orientar", "sugerir", "pode ser", "recomenda-se" sem prescrição objetiva.
5) Gerar no mínimo 10 itens prescritos no total, em sequência contínua: "Rx 1:", "Rx 2:", ...
6) A seção "Suplementos e Fitoterápicos" deve ter no mínimo 5 itens Rx clínicos quando houver categorias compatíveis selecionadas.
7) Cada Rx deve conter obrigatoriamente:
   - Item prescrito
   - Categoria
   - Forma/apresentação
   - Posologia (dose + frequência + horário)
   - Via de uso (quando aplicável)
   - Duração
   - Objetivo clínico
   - Observações/contraindicações
8) Se houver pedido de FORMULAÇÃO/MANIPULAÇÃO (ex.: "modulação intestinal"), gerar fórmula completa.
9) Para cada fórmula completa, usar este padrão:
   Fórmula X - Nome da formulação
   - Componente 1 ........ dose/unidade
   - Componente 2 ........ dose/unidade
   - Componente 3 ........ dose/unidade
   Forma farmacêutica: ...
   Posologia: ...
   Duração: ...
   Objetivo clínico: ...
10) Quando houver formulação solicitada, gerar no mínimo 2 fórmulas completas com no mínimo 3 componentes ativos cada.
11) Em probióticos para modulação intestinal, preferir blend de cepas (ex.: acidophilus, casei, longum) com unidades claras (UFC/bilhões).
12) Prescrever suplementos/fitoterápicos apenas dentro das categorias selecionadas: {categorias_txt}.
13) Respeitar alergias/intolerâncias/condições clínicas como contraindicação absoluta.
14) Em MIPs, permitir apenas os baseados em nutrientes.
15) Não prescrever medicamentos fora do escopo nutricional.
16) Se faltar dado para dose exata, escrever: "Ajustar dose conforme avaliação clínica presencial".
17) Nunca usar os termos "recibo" ou "recebimento"; usar sempre "receituário".
18) Quando aplicável clinicamente, pode citar exemplos de produtos do mercado brasileiro (nome comercial) junto do item prescrito, sem transformar o texto em propaganda.
19) Linguagem técnica, objetiva, português do Brasil correto e sem erros gramaticais.
"""
                    res = client.chat.completions.create(
                        messages=[{"role": "user", "content": prompt}],
                        model="llama-3.3-70b-versatile"
                    ).choices[0].message.content
                    if isinstance(res, str):
                        res = _fix_pt_br_text(res)
                        res = re.sub(r"\bRecibo\b", "Receituário Nutricional", res)
                        res = re.sub(r"\brecibo\b", "receituário nutricional", res)
                        res = re.sub(r"\bReceita\b", "Receituário Nutricional", res)
                        res = re.sub(r"\breceita\b", "receituário nutricional", res)
                        res = re.sub(r"\bRecebimento\b", "Receituário Nutricional", res)
                        res = re.sub(r"\brecebimento\b", "receituário nutricional", res)
                        res = _beautify_generated_text(res)
                    st.session_state["temp_receita"] = res
                except Exception as e:
                    if "invalid_api_key" in str(e).lower() or "invalid api key" in str(e).lower():
                        st.error("Erro IA: chave invalida. Confirme GROQ_API_KEY no Railway (sem espacos/quebras de linha) e reinicie o servico.")
                    else:
                        st.error(f"Erro: {e}")
    receita_atual = _beautify_generated_text(st.session_state.get("temp_receita", ""))
    if receita_atual:
        _render_generated_doc_preview("Pré-visualização do Receituário Nutricional", receita_atual, "Documento clínico • DietHealth")
    texto = st.text_area("Conteúdo do receituário", value=receita_atual, height=340, key="rx_texto_final")
    if st.button("Gerar PDF do receituário", key="rx_pdf_button", use_container_width=True):
        pdf_data = gerar_pdf_pro(paciente_sel, texto, "RECEITUÁRIO NUTRICIONAL", nome_prof, reg_prof)
        st.session_state["receita_pdf"] = pdf_data
        st.download_button("📥 Baixar PDF", pdf_data, "receituario.pdf", "application/pdf")
    _render_document_whatsapp_box("rx", paciente_sel, p_obj, "Enviar receituário por WhatsApp", f"Olá {paciente_sel}, segue seu receituário em PDF.")


def modulo_atestado():
    st.title("📄 Atestado")
    st.markdown(
        '<div class="dh-pill-soft">Crie atestado nutricional com apoio de IA, identificação profissional e assinatura digital no PDF.</div>',
        unsafe_allow_html=True
    )
    st.write("")

    meus_pacientes = filtrar_por_usuario(pacientes)
    lista_p = [p["nome"] for p in meus_pacientes]
    if not lista_p:
        st.warning("Cadastre um paciente primeiro.")
        return

    paciente_sel = st.selectbox("Selecione o Paciente:", lista_p, key="atestado_p")
    p_obj = get_paciente_obj(paciente_sel)
    ult = get_ultimos_dados(p_obj) or {}
    anamnese = get_anamnese_paciente(p_obj)
    anamnese_linhas = _anamnese_lines(anamnese)

    st.markdown("##### 📝 Identificação do Nutricionista")
    c_prof1, c_prof2 = st.columns(2)
    nome_prof = c_prof1.text_input("Seu Nome Completo", key="prof_name_atestado")
    reg_prof = c_prof2.text_input("Seu Registro (CRN/CRM)", key="prof_reg_atestado")
    st.caption("A assinatura digital enviada na barra lateral será aplicada automaticamente nos PDFs.")

    st.subheader("1. Dados do Atestado")
    c_tipo, c_data = st.columns([2, 1])
    tipo_atestado = c_tipo.selectbox(
        "Tipo de atestado",
        [
            "Comparecimento em consulta nutricional",
            "Acompanhamento nutricional",
            "Necessidade de dieta específica",
            "Uso de suplementação nutricional",
            "Nutrição enteral/oral especializada",
            "Outro",
        ],
        key="atestado_tipo"
    )
    data_emissao = c_data.date_input("Data de emissão", value=datetime.now().date(), format="DD/MM/YYYY", key="atestado_data")

    c_ini, c_dias = st.columns(2)
    inicio_periodo = c_ini.date_input("Início do período (opcional)", value=datetime.now().date(), format="DD/MM/YYYY", key="atestado_inicio")
    dias_periodo = c_dias.number_input("Duração (dias, opcional)", min_value=0, max_value=120, value=0, step=1, key="atestado_dias")
    fim_periodo = inicio_periodo + timedelta(days=int(dias_periodo)) if int(dias_periodo) > 0 else None
    if fim_periodo:
        st.caption(f"Período sugerido: {_fmt_data_br(str(inicio_periodo))} até {_fmt_data_br(str(fim_periodo))}.")

    finalidade = st.text_area(
        "Finalidade / justificativa clínica",
        placeholder="Ex: paciente em acompanhamento nutricional com necessidade de manter plano alimentar específico e rotina orientada."
    )
    observacoes = st.text_area(
        "Observações adicionais (opcional)",
        placeholder="Ex: restrições alimentares, recomendações gerais, orientações ao responsável/empresa."
    )
    incluir_anamnese = st.checkbox("Usar contexto do prontuário/anamnese na IA", value=True)

    if ult.get("data"):
        st.caption(
            f"Última avaliação: {ult.get('data')} • "
            f"Idade: {ult.get('idade') or '—'} • Sexo: {ult.get('sexo') or '—'} • "
            f"Peso: {ult.get('peso') or '—'} kg"
        )

    st.subheader("2. Otimização com IA")
    if st.button("🤖 Gerar Atestado com IA"):
        if not ia_ok():
            st.error("Configure a GROQ_API_KEY (Secrets ou variável de ambiente).")
        else:
            client = get_groq_client()
            if client is None:
                st.error("GROQ_API_KEY não encontrada. Configure a variável no Railway e reinicie o serviço.")
                st.stop()
            with st.spinner("Gerando atestado..."):
                try:
                    anamnese_txt = "\n".join(anamnese_linhas) if (incluir_anamnese and anamnese_linhas) else "Sem contexto adicional do prontuário."
                    periodo_txt = (
                        f"Início: {_fmt_data_br(str(inicio_periodo))}; duração: {int(dias_periodo)} dia(s); "
                        f"término estimado: {_fmt_data_br(str(fim_periodo))}."
                        if fim_periodo else
                        "Não informado."
                    )
                    prompt = f"""
Você é um nutricionista clínico e deve redigir um ATESTADO NUTRICIONAL formal, claro e objetivo.

DADOS DO NUTRICIONISTA
- Nome: {nome_prof or "A INFORMAR"}
- Registro profissional: {reg_prof or "A INFORMAR"}

DADOS DO PACIENTE
- Nome: {paciente_sel}
- Sexo: {ult.get("sexo") or (p_obj or {}).get("sexo") or "Não informado"}
- Idade: {ult.get("idade") or (p_obj or {}).get("idade") or "Não informada"}

DADOS DO ATESTADO
- Tipo: {tipo_atestado}
- Data de emissão: {_fmt_data_br(str(data_emissao))}
- Período: {periodo_txt}
- Finalidade clínica: {finalidade if finalidade.strip() else "Não informada"}
- Observações adicionais: {observacoes if observacoes.strip() else "Nenhuma"}

PRONTUÁRIO / ANAMNESE (usar como contexto)
{anamnese_txt}

REQUISITOS OBRIGATÓRIOS
1) Título: "ATESTADO NUTRICIONAL".
2) Incluir identificação do paciente e do nutricionista.
3) Incluir a declaração técnica de forma objetiva, sem linguagem culinária.
4) Não incluir CID, diagnóstico médico fechado ou prescrição de medicamentos fora do escopo nutricional.
5) Encerrar com local/data e campo de assinatura com nome e CRN.
6) Texto pronto para impressão em documento clínico.
"""
                    res = client.chat.completions.create(
                        messages=[{"role": "user", "content": prompt}],
                        model=os.getenv("model", "llama-3.3-70b-versatile")
                    ).choices[0].message.content
                    st.session_state["temp_atestado"] = res
                except Exception as e:
                    if "invalid_api_key" in str(e).lower() or "invalid api key" in str(e).lower():
                        st.error("Erro IA: chave inválida. Confirme GROQ_API_KEY no Railway e reinicie o serviço.")
                    else:
                        st.error(f"Erro IA: {e}")

    texto = st.text_area("Conteúdo do Atestado:", value=st.session_state.get("temp_atestado", ""), height=360)

    c_pdf, c_hist = st.columns(2)
    if c_pdf.button("📄 Gerar PDF do Atestado", type="primary"):
        if not texto.strip():
            st.warning("Gere ou escreva o conteúdo do atestado antes de exportar.")
        else:
            pdf_data = gerar_pdf_pro(paciente_sel, texto, "ATESTADO NUTRICIONAL", nome_prof, reg_prof)
            st.session_state["atestado_pdf"] = pdf_data
            st.download_button("📥 Baixar PDF", pdf_data, "atestado_nutricional.pdf", "application/pdf")

    if c_hist.button("💾 Salvar no Prontuário"):
        if not texto.strip():
            st.warning("Preencha o conteúdo do atestado antes de salvar.")
        elif not p_obj:
            st.warning("Paciente não encontrado.")
        else:
            p_obj.setdefault("historico", []).append({
                "tipo": "atestado_nutricional",
                "data": datetime.now().strftime("%d/%m/%Y %H:%M"),
                "atestado": texto,
                "observacoes": finalidade or observacoes or "",
            })
            save_db("pacientes.json", pacientes)
            st.success("Atestado salvo no prontuário do paciente.")

    st.markdown("##### Enviar Atestado por WhatsApp")
    tel_default = (p_obj.get("telefone") if p_obj else "") or ""
    tel_wa = st.text_input("WhatsApp do paciente", value=tel_default, key="wa_atestado_tel")
    msg_base = f"Olá {paciente_sel}, segue seu atestado nutricional em PDF."
    msg_edit = st.text_area("Mensagem para WhatsApp", value=msg_base, height=120, key="wa_atestado_msg")
    wa = _wa_link(tel_wa, msg_edit)
    if wa:
        st.markdown(f'<a class="dh-btn dh-btn-green" href="{wa}" target="_blank">Enviar WhatsApp</a>', unsafe_allow_html=True)
        st.caption("Anexe o PDF baixado no WhatsApp.")
    else:
        st.caption("Informe o número do WhatsApp do paciente para gerar o link.")


def modulo_dieta_ia():
    st.title("🥑 Diet Generator (IA)")
    st.markdown('<div class="dh-pill-soft">Gere cardápios completos com IA. Agora o sistema puxa dados do paciente (última avaliação) e permite ajustes rápidos.</div>', unsafe_allow_html=True)
    st.write("")

    meus_pacientes = filtrar_por_usuario(pacientes)
    if not meus_pacientes:
        st.warning("Cadastre um paciente primeiro.")
        return

    nome_paciente = st.selectbox("Paciente", [x['nome'] for x in meus_pacientes], key="diet_p")
    p_obj = get_paciente_obj(nome_paciente)
    ult = get_ultimos_dados(p_obj)
    anamnese = get_anamnese_paciente(p_obj)
    anamnese_linhas = _anamnese_lines(anamnese)

    restricoes_auto_linhas = []
    if _clean_text(anamnese.get("alergias")):
        restricoes_auto_linhas.append(f"Alergias: {anamnese['alergias']}")
    if _clean_text(anamnese.get("intolerancias")):
        restricoes_auto_linhas.append(f"Intolerâncias: {anamnese['intolerancias']}")
    if _clean_text(anamnese.get("condicoes_saude")):
        restricoes_auto_linhas.append(f"Condições de saúde: {anamnese['condicoes_saude']}")

    obs_auto_linhas = []
    if _clean_text(anamnese.get("queixa_principal")):
        obs_auto_linhas.append(f"Queixa principal: {anamnese['queixa_principal']}")
    if _clean_text(anamnese.get("medicamentos_suplementos")):
        obs_auto_linhas.append(f"Medicamentos/suplementos: {anamnese['medicamentos_suplementos']}")
    if _clean_text(anamnese.get("observacoes_clinicas")):
        obs_auto_linhas.append(f"Observações clínicas: {anamnese['observacoes_clinicas']}")
    if _clean_text(ult.get("observacoes")):
        obs_auto_linhas.append(f"Última evolução registrada: {_clean_text(ult.get('observacoes'))}")

    restricoes_auto_txt = "\n".join(restricoes_auto_linhas)
    obs_auto_txt = "\n".join(obs_auto_linhas)

    paciente_ctx_token = (p_obj or {}).get("id") or nome_paciente
    ctx_signature = f"{paciente_ctx_token}::{restricoes_auto_txt}::{obs_auto_txt}"
    if st.session_state.get("diet_context_signature") != ctx_signature:
        st.session_state["diet_context_signature"] = ctx_signature
        st.session_state["diet_context_patient_token"] = paciente_ctx_token
        st.session_state["diet_rest_auto"] = restricoes_auto_txt
        st.session_state["diet_obs_auto"] = obs_auto_txt

    # =========================
    # Bloco: dados do paciente
    # =========================
    st.subheader("1. Dados do Paciente")
    cA, cB, cC, cD = st.columns([1.2, 1, 1, 1])

    # Prefill com a última avaliação quando existir
    idade_default = int(ult.get("idade") or 0)
    sexo_default = ult.get("sexo") or "Masculino"
    peso_default = float(ult.get("peso") or 0.0)
    altura_default = float(ult.get("altura") or 0.0)

    idade = cA.number_input("Idade (anos)", min_value=0, max_value=120, value=idade_default, step=1)
    sexo = cB.selectbox("Sexo", ["Masculino", "Feminino"], index=(0 if sexo_default == "Masculino" else 1))
    peso = cC.number_input("Peso (kg)", min_value=0.0, value=peso_default, step=0.1, format="%.1f")
    altura = cD.number_input("Altura (m)", min_value=0.0, value=altura_default, step=0.01, format="%.2f")

    if ult.get("data"):
        st.caption(f"Última avaliação registrada em: {ult.get('data')}")

    # =========================
    # Bloco: configuração do plano
    # =========================
    st.subheader("2. Configuração do Plano")

    c1, c2, c3 = st.columns([1, 1, 1])
    obj = c1.selectbox("Objetivo", ["Emagrecer", "Hipertrofia", "Manutenção"])
    ativ = c2.selectbox("Atividade", ["Sedentário", "Leve", "Moderado", "Intenso"])
    refeicoes = c3.selectbox("Refeições/dia", [3, 4, 5, 6], index=1)

    if anamnese_linhas:
        st.info("Dados de anamnese aplicados automaticamente ao plano:\n" + "\n".join(anamnese_linhas))
    else:
        st.caption("Sem anamnese estruturada no prontuário. Preencha a seção de anamnese para automatizar esse bloco.")

    rest = st.text_area(
        "Restrições / Preferências",
        key="diet_rest_auto",
        placeholder="Ex: sem lactose, vegetariano, intolerância a glúten, prefere frango/peixe, etc.",
    )
    obs_plano = st.text_area(
        "Observações clínicas (opcional)",
        key="diet_obs_auto",
        placeholder="Ex: objetivo secundário, rotina do paciente, horário de treino, suplementos, etc.",
    )
    incluir_semana = st.checkbox("Gerar plano para 7 dias (mais completo)", value=True)

    clinical_rules = []
    clinical_context = {}
    clinical_evaluation = {"matched_conditions": [], "grouped": {}}
    clinical_prompt_block = ""
    ai_knowledge_topics = []
    ai_knowledge_prompt_block = ""
    clinical_rules_error = ""
    try:
        rules_payload = load_clinical_rules(CLINICAL_DIET_RULES_PATH) or {}
        clinical_rules = list(rules_payload.get("rules") or [])
        clinical_context = extract_patient_clinical_context(
            clinical_rules,
            anamnese=anamnese,
            restrictions_text=rest,
            notes_text=obs_plano,
            objective_text=obj,
        )
        clinical_evaluation = evaluate_clinical_rules(clinical_rules, clinical_context)
        clinical_prompt_block = build_clinical_prompt_block(clinical_context, clinical_evaluation)
        ai_knowledge_topics = _clinical_ai_topics(
            nome_paciente,
            "\n".join(anamnese_linhas),
            rest,
            obs_plano,
            obj,
            ativ,
        )
        ai_knowledge_prompt_block = _clinical_ai_prompt(
            "diet",
            nome_paciente,
            "\n".join(anamnese_linhas),
            rest,
            obs_plano,
            obj,
            ativ,
        )
    except Exception as exc:
        clinical_rules_error = str(exc)

    if clinical_rules_error:
        st.warning("Base clinica estruturada indisponivel no momento. A geracao segue com as restricoes textuais, mas sem a camada extra de seguranca.")
    elif clinical_evaluation.get("matched_conditions"):
        matched_labels = ", ".join(clinical_evaluation.get("matched_conditions") or [])
        st.markdown(
            f'''
            <div class="dh-pill-soft">
              <b>Seguranca clinica ativa:</b> {matched_labels}. A geracao aplicara bloqueios absolutos, restricoes condicionais e alertas antes da sugestao final.
            </div>
            ''',
            unsafe_allow_html=True,
        )
    if ai_knowledge_topics:
        st.markdown(
            f'''
            <div class="dh-pill-soft">
              <b>Base SBD/OMS aplicada:</b> {", ".join(topic.get("label") or "-" for topic in ai_knowledge_topics)}.
              O prompt vai reforçar condutas conservadoras de dieta, exercício, comorbidades e segurança clínica.
            </div>
            ''',
            unsafe_allow_html=True,
        )

    # Estimativas (se houver dados suficientes)
    tdee_info = None
    imc_atual_dieta = 0.0
    classificacao_imc_dieta = ""
    objetivo_efetivo = obj
    objetivo_alerta = ""
    objetivo_nota_prompt = ""
    if peso > 0 and altura > 0 and idade > 0:
        tdee_info = calc_tdee(peso, altura, int(idade), sexo, ativ)
    if peso > 0 and altura > 0:
        imc_atual_dieta = peso / (altura ** 2)
        classificacao_imc_dieta = classificar_imc_adulto_oms(imc_atual_dieta)

    if imc_atual_dieta > 0 and imc_atual_dieta < 18.5:
        if obj == "Emagrecer":
            objetivo_efetivo = "Recuperação ponderal"
            objetivo_alerta = (
                f"Paciente com IMC {imc_atual_dieta:.2f} kg/m² ({classificacao_imc_dieta}). "
                "Objetivo de emagrecimento foi bloqueado por segurança clínica."
            )
        elif obj == "Manutenção":
            objetivo_efetivo = "Manutenção com recuperação ponderal"
        if imc_atual_dieta < 16.0:
            objetivo_nota_prompt = "Paciente em magreza grave. Nao prescrever deficit calorico. Priorizar seguranca, recuperacao ponderal e densidade nutricional."
        elif imc_atual_dieta < 17.0:
            objetivo_nota_prompt = "Paciente em magreza moderada. Nao prescrever deficit calorico. Priorizar recuperacao ponderal e adequacao nutricional."
        else:
            objetivo_nota_prompt = "Paciente em magreza leve. Evitar deficit calorico e priorizar recuperacao ponderal gradual."

    if tdee_info:
        # Ajuste calórico por objetivo
        ajuste = 0
        if imc_atual_dieta > 0 and imc_atual_dieta < 16.0:
            ajuste = +500
        elif imc_atual_dieta > 0 and imc_atual_dieta < 18.5:
            ajuste = +300
        elif objetivo_efetivo == "Emagrecer":
            ajuste = -450
        elif objetivo_efetivo == "Hipertrofia":
            ajuste = +300
        alvo = max(1200, tdee_info["tdee"] + ajuste)

        if imc_atual_dieta > 0:
            st.markdown(
                f'''
                <div class="dh-pill-soft">
                  <b>IMC atual:</b> {imc_atual_dieta:.2f} kg/m² • <b>Classificação OMS:</b> {classificacao_imc_dieta or "-"}
                </div>
                ''',
                unsafe_allow_html=True
            )

        if objetivo_alerta:
            st.error(objetivo_alerta)

        st.markdown(
            f'''
            <div class="dh-pill-soft">
              <b>Estimativa automática:</b> BMR {tdee_info["bmr"]:.0f} kcal • TDEE {tdee_info["tdee"]:.0f} kcal
              • <b>Meta sugerida ({objetivo_efetivo}):</b> {alvo:.0f} kcal/dia
            </div>
            ''',
            unsafe_allow_html=True
        )
    else:
        alvo = None


    # =========================
    # Gerar com IA
    # =========================
    st.subheader("3. Gerar Cardápio com IA")

    col_btn1, col_btn_sub, col_btn2 = st.columns([1, 1, 2.2])
    with col_btn1:
        gerar = st.button("🤖 Gerar Cardápio", type="primary", key="diet_btn_generate")
    with col_btn_sub:
        gerar_subs = st.button("🔁 Gerar Substituicoes", key="diet_btn_subs")
    with col_btn2:
        st.caption("Dica: se não houver avaliação, preencha idade/sexo/peso/altura para melhorar muito a qualidade do cardápio.")

    if gerar or gerar_subs:
        modo_substituicoes = bool(gerar_subs)
        if not ia_ok():
            st.warning("IA não configurada neste ambiente. Defina a GROQ_API_KEY para liberar a geração de cardápio.")
        else:
            user_obj = _current_user_obj()
            if _is_free_user(user_obj):
                remaining = _free_diet_remaining(user_obj)
                if remaining <= 0:
                    st.error("Limite diário do plano básico atingido (15 dietas/dia). Assine o premium para acesso completo.")
                    st.stop()
                _increment_free_diet_usage(user_obj, 1)

            client = get_groq_client()
            if client is None:
                st.warning("IA não configurada neste ambiente. Defina a GROQ_API_KEY e reinicie o serviço.")
                st.stop()
            # Prompt profissional e estruturado
            bloco_anamnese = "\n".join(anamnese_linhas) if anamnese_linhas else "- Sem anamnese estruturada registrada."
            base = f"""Você é um nutricionista clínico. Monte um plano alimentar profissional, seguro e específico para o paciente abaixo.
Respeite rigorosamente condições clínicas e restrições. NÃO inclua alimentos incompatíveis.

DADOS DO PACIENTE
- Nome: {nome_paciente}
- Sexo: {sexo}
- Idade: {idade} anos
- Peso: {peso} kg
- Altura: {altura} m

OBJETIVO E ROTINA
- Objetivo selecionado: {obj}
- Objetivo efetivo para prescricao: {objetivo_efetivo}
- Nível de atividade: {ativ}
- Refeições por dia: {refeicoes}
- IMC atual: {f"{imc_atual_dieta:.2f} kg/m²" if imc_atual_dieta > 0 else "Nao calculado"}
- Classificação OMS do IMC: {classificacao_imc_dieta or "Nao disponivel"}

ANAMNESE / PRONTUÁRIO CLÍNICO (MIGRADO AUTOMATICAMENTE)
{bloco_anamnese}

RESTRIÇÕES / PREFERÊNCIAS (OBRIGATÓRIAS)
{rest if rest.strip() else "Nenhuma informada."}

OBSERVAÇÕES CLÍNICAS (se houver)
{obs_plano if obs_plano.strip() else "Nenhuma."}
"""

            if alvo:
                base += f"""

METAS CALÓRICAS (estimativa)
- Meta diária aproximada: {alvo:.0f} kcal/dia
"""

            if objetivo_nota_prompt:
                base += f"""

ALERTA CLINICO DE ESTADO NUTRICIONAL
- {objetivo_nota_prompt}
"""

            if clinical_prompt_block:
                base += f"""

{clinical_prompt_block}
"""

            if ai_knowledge_prompt_block:
                base += f"""

{ai_knowledge_prompt_block}
"""

            base += """

REQUISITOS DE SAÍDA
1) Primeiro cruze diagnosticos, alergias, intolerancias, restricoes e observacoes com a camada de seguranca clinica.
2) Nunca inclua alimento com regra de proibido_absoluto.
3) Em restricao_condicional, adote conduta conservadora e sinalize revisao profissional quando depender de exame, estagio, sintoma ou tolerancia.
4) Em alerta_preferencia, favoreca a alternativa mais segura sem inventar proibicoes absolutas.
5) Liste as refeições (com horários sugeridos), quantidades aproximadas e opções de substituição SEGURAS.
6) Inclua variações para facilitar adesão (pelo menos 2 opções por refeição), sempre compatíveis.
7) Inclua lista de compras resumida.
8) Linguagem clara e direta, formato em tópicos.
9) Inclua uma seção "Alimentos proibidos" com base nas restrições/observações clínicas e uma seção "Pontos para validação profissional" quando houver regra condicional relevante.
10) Antes de responder, FAÇA UMA CHECAGEM e garanta que nenhum alimento proibido ou inadequado foi incluído.
11) Escreva títulos de refeições em Markdown negrito, por exemplo: **Cafe da manha**, **Almoco**, **Jantar**.
12) Ao sugerir carnes, sempre informar ANIMAL + TIPO/CORTE (ex: bovino patinho, bovino coxao mole, bovino alcatra, frango peito, suino bisteca, peixe tilapia).
13) Ao sugerir frutas, informar sempre a variedade/tipo (ex: banana prata, maca fuji, mamao papaya, pera williams).
14) Se o IMC indicar magreza, nunca prescreva emagrecimento ou deficit calorico. Priorize recuperacao ponderal, adequacao energetica e densidade nutricional.
"""

            if incluir_semana:
                base += """15) Gere um plano de 7 dias (Seg-Dom), mantendo coerência com objetivo e restrições.
"""
            else:
                base += """15) Gere plano de 1 dia muito completo e uma seção de substituições (proteínas, carboidratos, gorduras, frutas/verduras).
"""

            if modo_substituicoes:
                dieta_base = _clean_text(st.session_state.get("diet_temp", ""))
                base += f"""

MODO ESPECIAL: SUBSTITUICOES
- Foque em uma tabela completa de substituicoes por refeicao.
- Para cada refeicao, entregue no minimo 5 opcoes por grupo alimentar.
- Em proteinas animais, sempre detalhar ANIMAL + CORTE/TIPO.
- Em frutas, sempre detalhar VARIEDADE/TIPO.
- Formato objetivo, pratico e direto para prescricao nutricional.
- Se houver plano anterior, use como base:
{dieta_base if dieta_base else "- Sem plano anterior salvo."}
"""

            with st.spinner("Gerando com IA..."):
                try:
                    res = client.chat.completions.create(
                        messages=[{"role": "user", "content": base}],
                        model = os.getenv("model", "llama-3.3-70b-versatile")
                    ).choices[0].message.content
                    validation = {"blocked_conflicts": [], "conditional_alerts": [], "preference_alerts": [], "audit_log": [], "needs_revision": False}
                    if isinstance(res, str) and clinical_evaluation.get("rules"):
                        validation = validate_diet_text(res, clinical_evaluation)
                        if requires_clinical_revision(validation):
                            revision_prompt = build_revision_prompt(base, res, validation, clinical_evaluation)
                            revised = client.chat.completions.create(
                                messages=[{"role": "user", "content": revision_prompt}],
                                model=os.getenv("model", "llama-3.3-70b-versatile")
                            ).choices[0].message.content
                            if isinstance(revised, str) and revised.strip():
                                res = revised
                                validation = validate_diet_text(res, clinical_evaluation)
                    if isinstance(res, str):
                        res = _fix_pt_br_text(res)
                        res = _beautify_generated_text(res)
                        res = _bold_meal_titles(res)
                    if modo_substituicoes and _clean_text(st.session_state.get("diet_temp")):
                        anterior = _beautify_generated_text(st.session_state.get("diet_temp", ""))
                        st.session_state['diet_temp'] = f"{anterior}\n\n## Substituicoes detalhadas\n\n{res}"
                    else:
                        st.session_state['diet_temp'] = res
                    st.session_state["diet_clinical_audit"] = {
                        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "evaluation": clinical_evaluation,
                        "validation": validation,
                        "summary": summarize_clinical_audit(clinical_evaluation, validation),
                    }
                except Exception as e:
                    if "invalid_api_key" in str(e).lower() or "invalid api key" in str(e).lower():
                        st.error("Erro IA: chave invalida. Confirme GROQ_API_KEY no Railway (sem espacos/quebras de linha) e redeploy/restart.")
                    else:
                        st.error(f"Erro IA: {e}")


    # =========================
    # Editar + PDF
    # =========================
    if 'diet_temp' in st.session_state:
        audit_payload = st.session_state.get("diet_clinical_audit") or {}
        audit_summary = audit_payload.get("summary") or {}
        if audit_summary.get("matched_conditions"):
            with st.expander("Seguranca clinica aplicada na geracao", expanded=False):
                st.write("Condições reconhecidas:", ", ".join(audit_summary.get("matched_conditions") or []))
                st.write(
                    f"Bloqueios absolutos detectados: {audit_summary.get('blocked_total', 0)} | "
                    f"Alertas condicionais: {audit_summary.get('conditional_total', 0)} | "
                    f"Alertas de preferencia: {audit_summary.get('preference_total', 0)}"
                )
                for log in audit_summary.get("audit_log") or []:
                    st.caption(f"- {log}")
                if audit_summary.get("blocked_total", 0) > 0:
                    st.warning("A geracao ainda encontrou conflito absoluto apos a validacao automatica. Revise clinicamente antes de usar o plano.")

        st.subheader("4. Editar & Exportar em PDF")
        c_prof1, c_prof2 = st.columns(2)
        nome_prof_diet = c_prof1.text_input("Seu Nome Completo (Assinatura)", key="prof_name_diet")
        reg_prof_diet = c_prof2.text_input("Seu Registro (CRN/CRM)", key="prof_reg_diet")

        dieta_atual = _bold_meal_titles(_beautify_generated_text(st.session_state.get("diet_temp", "")))
        if dieta_atual:
            _render_generated_doc_preview(
                "Pre-visualizacao da Dieta",
                dieta_atual,
                "Plano alimentar - DietHealth",
            )

        # Evita reset de widget/diff instavel no frontend (mobile/tablet)
        if st.session_state.get("diet_editor_source") != dieta_atual:
            st.session_state["diet_editor_source"] = dieta_atual
            st.session_state["diet_editor_text"] = dieta_atual

        texto_final = st.text_area("Cardapio Gerado:", key="diet_editor_text", height=620)
        st.session_state['diet_final'] = texto_final

        if st.button("Gerar PDF Final", type="primary", key="diet_btn_pdf"):
            pdf_data = gerar_pdf_pro(nome_paciente, st.session_state['diet_final'], f"PLANO ALIMENTAR - {objetivo_efetivo.upper()}", nome_prof_diet, reg_prof_diet)
            st.session_state["dieta_pdf"] = pdf_data

        if st.session_state.get("dieta_pdf"):
            st.download_button(
                "Baixar Dieta em PDF",
                st.session_state["dieta_pdf"],
                file_name=f"Dieta_{nome_paciente}.pdf",
                mime="application/pdf",
                key="diet_btn_download_pdf",
            )

        st.markdown("##### Enviar Dieta por WhatsApp")
        tel_default = (p_obj.get("telefone") if p_obj else "") or ""
        tel_wa = st.text_input("WhatsApp do paciente", value=tel_default, key="wa_diet_tel")
        msg_base = f"Ola {nome_paciente}, segue seu plano alimentar em PDF."
        msg_edit = st.text_area("Mensagem para WhatsApp", value=msg_base, height=120, key="wa_diet_msg")
        wa = _wa_link(tel_wa, msg_edit)
        if wa:
            st.markdown(f'<a class="dh-btn dh-btn-green" href="{wa}" target="_blank">Enviar WhatsApp</a>', unsafe_allow_html=True)
            st.caption("Anexe o PDF baixado no WhatsApp.")
        else:
            st.caption("Informe o número do WhatsApp do paciente para gerar o link.")


def modulo_tabela_ia():
    st.title("🔍 Consulta Nutricional (IA)")
    st.markdown('<div class="dh-pill-soft">Digite um alimento e peça para a IA retornar a tabela nutricional completa.</div>', unsafe_allow_html=True)
    st.write("")

    alimento = st.text_input("Digite o alimento para ver a tabela:")
    if st.button("Consultar"):
        if not ia_ok():
            st.warning("Consulta IA não configurada neste ambiente. Defina a GROQ_API_KEY para habilitar esse módulo.")
        else:
            client = get_groq_client()
            if client is None:
                st.warning("Consulta IA não configurada neste ambiente. Defina a GROQ_API_KEY e reinicie o serviço.")
                st.stop()
            with st.spinner("Buscando..."):
                try:
                    res = client.chat.completions.create(
                        messages=[{"role": "user", "content": f"Retorne uma tabela nutricional completa e bem formatada (porção 100g), incluindo macros e micros principais para: {alimento}."}],
                        model="llama-3.3-70b-versatile"
                    ).choices[0].message.content
                    st.markdown(res)
                except Exception as e:
                    if "invalid_api_key" in str(e).lower() or "invalid api key" in str(e).lower():
                        st.error("Erro IA: chave invalida. Confirme GROQ_API_KEY no Railway (sem espacos/quebras de linha) e reinicie o servico.")
                    else:
                        st.error(f"Erro: {e}")

FINANCE_INCOME_CATEGORIES = [
    "Consulta nutricional",
    "Retorno",
    "Plano alimentar",
    "Avaliacao fisica",
    "Acompanhamento mensal",
    "Pacote de consultas",
    "Venda de material",
    "Outro",
]

FINANCE_EXPENSE_CATEGORIES = [
    "Aluguel",
    "Internet",
    "Marketing",
    "Plataforma/sistema",
    "Impostos",
    "Energia",
    "Secretaria",
    "Materiais",
    "Cursos",
    "Trafego pago",
    "Taxas bancarias",
    "Outro",
]

FINANCE_PAYMENT_METHODS = [
    "Pix",
    "Dinheiro",
    "Cartao de credito",
    "Cartao de debito",
    "Transferencia",
    "Boleto",
    "Assinatura",
    "Outro",
]

FINANCE_ORIGINS = ["Manual", "Consulta", "Pacote", "Recorrencia", "Sistema", "Outro"]


def _format_brl(value) -> str:
    try:
        number = float(value or 0)
    except Exception:
        number = 0.0
    return f"R$ {number:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _finance_float(value) -> float:
    try:
        return round(float(value or 0), 2)
    except Exception:
        return 0.0


def _finance_parse_date(value):
    if hasattr(value, "year") and hasattr(value, "month") and hasattr(value, "day"):
        try:
            return value if not hasattr(value, "date") else value.date()
        except Exception:
            pass
    if isinstance(value, str):
        value = value.strip()
        for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%Y/%m/%d"):
            try:
                return datetime.strptime(value, fmt).date()
            except Exception:
                continue
    return datetime.now().date()


def _finance_add_months(base_date, offset: int):
    base_date = _finance_parse_date(base_date)
    month_index = (base_date.month - 1) + int(offset)
    year = base_date.year + (month_index // 12)
    month = (month_index % 12) + 1
    day = min(base_date.day, calendar.monthrange(year, month)[1])
    return base_date.replace(year=year, month=month, day=day)


def _finance_status_options(tipo: str):
    return ["Recebido", "Pendente", "Vencido"] if tipo == "Receita" else ["Pago", "Pendente", "Vencido"]


def _finance_default_status(tipo: str) -> str:
    return "Recebido" if tipo == "Receita" else "Pago"


def _finance_categories_for(tipo: str):
    return FINANCE_INCOME_CATEGORIES if tipo == "Receita" else FINANCE_EXPENSE_CATEGORIES


def _finance_normalize_entry(item):
    if not isinstance(item, dict):
        return None

    tipo_raw = (item.get("tipo") or "").strip().lower()
    tipo = "Despesa" if tipo_raw in ("despesa", "gasto", "saida", "saída") else "Receita"
    status = (item.get("status") or "").strip().title()
    if status not in _finance_status_options(tipo):
        status = _finance_default_status(tipo)

    data_lanc = _finance_parse_date(item.get("data"))
    parcelas_total = max(1, int(item.get("parcelas_total") or 1))
    parcela_atual = max(1, min(int(item.get("parcela_atual") or 1), parcelas_total))

    return {
        "id": (item.get("id") or uuid.uuid4().hex),
        "dono": (item.get("dono") or st.session_state.get("usuario") or "").strip().lower(),
        "data": str(data_lanc),
        "descricao": (item.get("descricao") or item.get("desc") or "").strip(),
        "valor": _finance_float(item.get("valor")),
        "tipo": tipo,
        "categoria": (item.get("categoria") or "Outro").strip(),
        "subcategoria": (item.get("subcategoria") or "").strip(),
        "forma_pagamento": (item.get("forma_pagamento") or item.get("pagamento") or "Pix").strip(),
        "status": status,
        "observacoes": (item.get("observacoes") or item.get("obs") or "").strip(),
        "paciente": (item.get("paciente") or item.get("paciente_nome") or "").strip(),
        "origem": (item.get("origem") or "Manual").strip(),
        "recorrente": bool(item.get("recorrente")),
        "parcelas_total": parcelas_total,
        "parcela_atual": parcela_atual,
        "created_at": (item.get("created_at") or datetime.now().isoformat(timespec="seconds")),
        "updated_at": (item.get("updated_at") or datetime.now().isoformat(timespec="seconds")),
    }


def _finance_prepare_store():
    normalized = []
    changed = False
    for item in financeiro:
        norm = _finance_normalize_entry(item)
        if not norm:
            changed = True
            continue
        if norm != item:
            changed = True
        normalized.append(norm)
    return normalized, changed


def _finance_commit(entries):
    financeiro[:] = entries
    save_db("financeiro.json", financeiro)


def _finance_all_entries():
    entries, changed = _finance_prepare_store()
    if changed:
        _finance_commit(entries)
    return entries


def _finance_patient_options():
    available = filtrar_por_usuario(pacientes)
    return sorted({(p.get("nome") or "").strip() for p in available if (p.get("nome") or "").strip()})


def _finance_is_overdue(entry) -> bool:
    if (entry.get("status") or "").strip().title() == "Vencido":
        return True
    return (entry.get("status") or "").strip().title() == "Pendente" and _finance_parse_date(entry.get("data")) < datetime.now().date()


def _finance_reset_form():
    today = datetime.now().date()
    defaults = {
        "fin_desc": "",
        "fin_valor": 0.0,
        "fin_tipo": "Receita",
        "fin_categoria": FINANCE_INCOME_CATEGORIES[0],
        "fin_subcategoria": "",
        "fin_data": today,
        "fin_pagamento": "Pix",
        "fin_status": "Recebido",
        "fin_tem_paciente": False,
        "fin_paciente": "",
        "fin_origem": "Manual",
        "fin_obs": "",
        "fin_recorrente": False,
        "fin_parcelas": 1,
    }
    for key, value in defaults.items():
        st.session_state[key] = value
    st.session_state["finance_edit_id"] = ""


def _finance_load_entry_into_form(entry):
    st.session_state["finance_edit_id"] = entry.get("id", "")
    st.session_state["fin_desc"] = entry.get("descricao", "")
    st.session_state["fin_valor"] = _finance_float(entry.get("valor"))
    st.session_state["fin_tipo"] = entry.get("tipo", "Receita")
    st.session_state["fin_categoria"] = entry.get("categoria") or _finance_categories_for(entry.get("tipo", "Receita"))[0]
    st.session_state["fin_subcategoria"] = entry.get("subcategoria", "")
    st.session_state["fin_data"] = _finance_parse_date(entry.get("data"))
    st.session_state["fin_pagamento"] = entry.get("forma_pagamento") or "Pix"
    st.session_state["fin_status"] = entry.get("status") or _finance_default_status(entry.get("tipo", "Receita"))
    st.session_state["fin_tem_paciente"] = bool(entry.get("paciente"))
    st.session_state["fin_paciente"] = entry.get("paciente", "")
    st.session_state["fin_origem"] = entry.get("origem") or "Manual"
    st.session_state["fin_obs"] = entry.get("observacoes", "")
    st.session_state["fin_recorrente"] = bool(entry.get("recorrente"))
    st.session_state["fin_parcelas"] = int(entry.get("parcelas_total") or 1)


def _finance_ensure_form_state():
    if "fin_desc" not in st.session_state:
        _finance_reset_form()


def _finance_filter_entries(entries, dt_ini, dt_fim, tipo, categoria, status, paciente, pagamento):
    result = []
    for entry in entries:
        data_ref = _finance_parse_date(entry.get("data"))
        if data_ref < dt_ini or data_ref > dt_fim:
            continue
        if tipo != "Todos" and entry.get("tipo") != tipo:
            continue
        if categoria != "Todas" and entry.get("categoria") != categoria:
            continue
        if status != "Todos" and entry.get("status") != status:
            continue
        if paciente != "Todos" and (entry.get("paciente") or "") != paciente:
            continue
        if pagamento != "Todos" and (entry.get("forma_pagamento") or "") != pagamento:
            continue
        result.append(entry)
    return result


def _finance_summary_by_category(entries, tipo):
    rows = [e for e in entries if e.get("tipo") == tipo]
    if not rows:
        return pd.DataFrame(columns=["Categoria", "Total", "Lancamentos"])
    df = pd.DataFrame(rows)
    return (
        df.groupby("categoria", dropna=False)
        .agg(Total=("valor", "sum"), Lancamentos=("id", "count"))
        .reset_index()
        .rename(columns={"categoria": "Categoria"})
        .sort_values("Total", ascending=False)
    )


def _finance_build_table(entries):
    rows = []
    for entry in sorted(entries, key=lambda x: (x.get("data", ""), x.get("created_at", "")), reverse=True):
        parcela = "-"
        if int(entry.get("parcelas_total") or 1) > 1:
            parcela = f'{entry.get("parcela_atual", 1)}/{entry.get("parcelas_total", 1)}'
        rows.append(
            {
                "Data": datetime.strptime(entry["data"], "%Y-%m-%d").strftime("%d/%m/%Y"),
                "Descricao": entry.get("descricao", ""),
                "Categoria": entry.get("categoria", ""),
                "Tipo": entry.get("tipo", ""),
                "Status": entry.get("status", ""),
                "Valor": _format_brl(entry.get("valor")),
                "Paciente": entry.get("paciente", "-") or "-",
                "Pagamento": entry.get("forma_pagamento", ""),
                "Parcela": parcela,
            }
        )
    return pd.DataFrame(rows)


def _inject_financeiro_styles():
    st.markdown(
        """
<style>
.dh-fin-hero{padding:10px 2px 6px 2px;}
.dh-fin-title{margin:0;font-size:2rem;line-height:1.05;font-weight:800;color:rgba(241,245,249,0.98);}
.dh-fin-subtitle{margin:10px 0 0 0;color:rgba(191,206,229,0.88);font-size:0.98rem;line-height:1.55;}
.dh-fin-grid{display:grid;grid-template-columns:repeat(6,minmax(0,1fr));gap:14px;margin-top:18px;}
.dh-fin-kpi{border-radius:18px;padding:16px 18px;background:linear-gradient(180deg,rgba(15,23,42,0.96),rgba(10,16,31,0.94));border:1px solid rgba(132,156,214,0.16);box-shadow:0 14px 28px rgba(0,0,0,0.18);}
.dh-fin-kpi-label{color:rgba(148,163,184,0.92);font-size:0.76rem;text-transform:uppercase;letter-spacing:0.08em;font-weight:700;}
.dh-fin-kpi-value{margin-top:8px;color:rgba(241,245,249,0.98);font-size:1.55rem;font-weight:800;}
.dh-fin-kpi-note{margin-top:6px;color:rgba(148,163,184,0.86);font-size:0.8rem;}
.dh-fin-panel{border-radius:20px;padding:18px 18px 20px 18px;background:linear-gradient(180deg,rgba(16,24,43,0.94),rgba(9,15,29,0.93));border:1px solid rgba(132,156,214,0.14);box-shadow:0 16px 36px rgba(0,0,0,0.18);}
.dh-fin-panel-title{margin:0;color:rgba(241,245,249,0.98);font-size:1.06rem;font-weight:800;}
.dh-fin-panel-subtitle{margin:6px 0 0 0;color:rgba(148,163,184,0.86);font-size:0.88rem;}
.dh-fin-inline-stat{display:flex;justify-content:space-between;align-items:center;gap:12px;padding:10px 0;border-bottom:1px solid rgba(255,255,255,0.06);}
.dh-fin-inline-stat:last-child{border-bottom:none;}
.dh-fin-inline-label{color:rgba(191,206,229,0.90);font-size:0.9rem;}
.dh-fin-inline-value{color:rgba(241,245,249,0.98);font-weight:700;}
.dh-fin-badge{display:inline-flex;align-items:center;gap:8px;border-radius:999px;padding:8px 12px;border:1px solid rgba(34,197,94,0.18);background:rgba(34,197,94,0.08);color:rgba(167,243,208,0.96);font-size:0.8rem;font-weight:700;}
.dh-fin-empty{border-radius:18px;padding:18px;border:1px dashed rgba(132,156,214,0.22);background:rgba(15,23,42,0.48);color:rgba(191,206,229,0.82);}
.dh-fin-entry{border-radius:18px;padding:14px 16px;border:1px solid rgba(132,156,214,0.14);background:linear-gradient(180deg,rgba(14,21,39,0.94),rgba(10,16,31,0.92));}
.dh-fin-entry-top{display:flex;justify-content:space-between;align-items:flex-start;gap:16px;}
.dh-fin-entry-title{color:rgba(241,245,249,0.98);font-size:1rem;font-weight:800;margin:0;}
.dh-fin-entry-meta{margin-top:4px;color:rgba(148,163,184,0.86);font-size:0.84rem;}
.dh-fin-entry-value{font-size:1rem;font-weight:800;white-space:nowrap;}
.dh-fin-entry-tags{display:flex;flex-wrap:wrap;gap:8px;margin-top:12px;}
.dh-fin-chip{display:inline-flex;align-items:center;border-radius:999px;padding:6px 10px;background:rgba(255,255,255,0.06);color:rgba(226,232,240,0.94);font-size:0.76rem;font-weight:700;}
.dh-fin-chip-income{background:rgba(34,197,94,0.12);color:rgba(134,239,172,0.98);}
.dh-fin-chip-expense{background:rgba(248,113,113,0.12);color:rgba(254,202,202,0.98);}
.dh-fin-chip-alert{background:rgba(250,204,21,0.12);color:rgba(253,224,71,0.98);}
@media (max-width: 1200px){.dh-fin-grid{grid-template-columns:repeat(3,minmax(0,1fr));}}
@media (max-width: 720px){.dh-fin-grid{grid-template-columns:repeat(2,minmax(0,1fr));}}
</style>
""",
        unsafe_allow_html=True,
    )


def modulo_financeiro():
    _inject_financeiro_styles()

    all_entries = _finance_all_entries()
    meu_financeiro = filtrar_por_usuario(all_entries)
    _finance_ensure_form_state()

    dt_hoje = datetime.now().date()
    dt_inicio_mes = dt_hoje.replace(day=1)
    pacientes_opts = _finance_patient_options()
    categorias_filtro = ["Todas"] + sorted({e.get("categoria") or "Outro" for e in meu_financeiro})
    status_filtro = ["Todos"] + sorted({e.get("status") or "Pendente" for e in meu_financeiro})
    pagamentos_filtro = ["Todos"] + sorted({e.get("forma_pagamento") or "Pix" for e in meu_financeiro})
    pacientes_filtro = ["Todos"] + pacientes_opts

    if st.session_state.get("fin_filter_categoria") not in categorias_filtro:
        st.session_state["fin_filter_categoria"] = "Todas"
    if st.session_state.get("fin_filter_status") not in status_filtro:
        st.session_state["fin_filter_status"] = "Todos"
    if st.session_state.get("fin_filter_pagamento") not in pagamentos_filtro:
        st.session_state["fin_filter_pagamento"] = "Todos"
    if st.session_state.get("fin_filter_paciente") not in pacientes_filtro:
        st.session_state["fin_filter_paciente"] = "Todos"

    st.markdown(
        """
<div class="dh-fin-hero">
  <h1 class="dh-fin-title">Meu Financeiro</h1>
  <p class="dh-fin-subtitle">Controle entradas, saídas, pendências e categorias do consultório em um fluxo simples, rápido e operacional.</p>
</div>
""",
        unsafe_allow_html=True,
    )

    f1, f2, f3, f4, f5, f6 = st.columns(6)
    with f1:
        dt_ini = st.date_input("Periodo inicial", value=dt_inicio_mes, key="fin_filter_dt_ini")
    with f2:
        dt_fim = st.date_input("Periodo final", value=dt_hoje, key="fin_filter_dt_fim")
    with f3:
        tipo_filter = st.selectbox("Tipo", ["Todos", "Receita", "Despesa"], key="fin_filter_tipo")
    with f4:
        categoria_filter = st.selectbox("Categoria", categorias_filtro, key="fin_filter_categoria")
    with f5:
        status_filter = st.selectbox("Status", status_filtro, key="fin_filter_status")
    with f6:
        pagamento_filter = st.selectbox("Pagamento", pagamentos_filtro, key="fin_filter_pagamento")

    paciente_filter = st.selectbox("Paciente", pacientes_filtro, key="fin_filter_paciente")

    if _finance_parse_date(dt_ini) > _finance_parse_date(dt_fim):
        dt_ini, dt_fim = dt_fim, dt_ini

    filtrados = _finance_filter_entries(
        meu_financeiro,
        _finance_parse_date(dt_ini),
        _finance_parse_date(dt_fim),
        tipo_filter,
        categoria_filter,
        status_filter,
        paciente_filter,
        pagamento_filter,
    )

    total_receitas = sum(e.get("valor", 0) for e in filtrados if e.get("tipo") == "Receita")
    total_despesas = sum(e.get("valor", 0) for e in filtrados if e.get("tipo") == "Despesa")
    saldo_periodo = total_receitas - total_despesas
    pendentes = [e for e in filtrados if (e.get("status") or "").strip().title() == "Pendente"]
    vencidos = [e for e in filtrados if _finance_is_overdue(e)]
    ticket_medio = total_receitas / max(1, len([e for e in filtrados if e.get("tipo") == "Receita"])) if filtrados else 0.0

    cards = [
        ("Receita do periodo", _format_brl(total_receitas), f'{len([e for e in filtrados if e.get("tipo") == "Receita"])} lancamentos'),
        ("Despesa do periodo", _format_brl(total_despesas), f'{len([e for e in filtrados if e.get("tipo") == "Despesa"])} lancamentos'),
        ("Saldo do periodo", _format_brl(saldo_periodo), "Entradas menos saídas"),
        ("Pendentes", str(len(pendentes)), "Lancamentos aguardando baixa"),
        ("Vencidos", str(len(vencidos)), "Revisar cobranca ou pagamento"),
        ("Ticket medio", _format_brl(ticket_medio), "Media por receita filtrada"),
    ]
    cards_html = "".join(
        f"""
<article class="dh-fin-kpi">
  <div class="dh-fin-kpi-label">{html.escape(label)}</div>
  <div class="dh-fin-kpi-value">{html.escape(value)}</div>
  <div class="dh-fin-kpi-note">{html.escape(note)}</div>
</article>
"""
        for label, value, note in cards
    )
    st.markdown(f'<section class="dh-fin-grid">{cards_html}</section>', unsafe_allow_html=True)

    if st.button("Limpar filtros", key="fin_reset_filters"):
        for key in (
            "fin_filter_dt_ini",
            "fin_filter_dt_fim",
            "fin_filter_tipo",
            "fin_filter_categoria",
            "fin_filter_status",
            "fin_filter_pagamento",
            "fin_filter_paciente",
        ):
            if key in st.session_state:
                del st.session_state[key]
        st.rerun()

    tipo_options = ["Receita", "Despesa"]
    if st.session_state.get("fin_tipo") not in tipo_options:
        st.session_state["fin_tipo"] = "Receita"
    if st.session_state.get("fin_categoria") not in _finance_categories_for(st.session_state["fin_tipo"]):
        st.session_state["fin_categoria"] = _finance_categories_for(st.session_state["fin_tipo"])[0]
    if st.session_state.get("fin_status") not in _finance_status_options(st.session_state["fin_tipo"]):
        st.session_state["fin_status"] = _finance_default_status(st.session_state["fin_tipo"])

    form_col, insight_col = st.columns([1.3, 0.9], gap="large")

    with form_col:
        st.markdown(
            """
<section class="dh-fin-panel">
  <h3 class="dh-fin-panel-title">Novo lancamento</h3>
  <p class="dh-fin-panel-subtitle">Registre receitas, despesas, recorrencias e vincule pacientes quando fizer sentido.</p>
</section>
""",
            unsafe_allow_html=True,
        )
        c1, c2 = st.columns([1.4, 0.8], gap="medium")
        with c1:
            st.text_input("Descricao", key="fin_desc", placeholder="Ex: Consulta de retorno, aluguel da sala, campanha de marketing")
        with c2:
            st.number_input("Valor", min_value=0.0, step=10.0, format="%.2f", key="fin_valor")

        c3, c4, c5 = st.columns(3, gap="medium")
        with c3:
            st.selectbox("Tipo", tipo_options, key="fin_tipo")
        with c4:
            st.selectbox("Categoria", _finance_categories_for(st.session_state["fin_tipo"]), key="fin_categoria")
        with c5:
            st.text_input("Subcategoria", key="fin_subcategoria", placeholder="Opcional")

        c6, c7, c8 = st.columns(3, gap="medium")
        with c6:
            st.date_input("Data do lancamento", key="fin_data")
        with c7:
            st.selectbox("Forma de pagamento", FINANCE_PAYMENT_METHODS, key="fin_pagamento")
        with c8:
            st.selectbox("Status", _finance_status_options(st.session_state["fin_tipo"]), key="fin_status")

        c9, c10, c11 = st.columns([0.8, 1.2, 1], gap="medium")
        with c9:
            st.checkbox("Vincular paciente", key="fin_tem_paciente")
        with c10:
            if st.session_state.get("fin_tem_paciente"):
                st.selectbox("Paciente", [""] + pacientes_opts, key="fin_paciente")
            else:
                st.text_input("Paciente", value="", disabled=True, key="fin_paciente_disabled")
        with c11:
            st.selectbox("Origem", FINANCE_ORIGINS, key="fin_origem")

        c12, c13 = st.columns([0.8, 0.6], gap="medium")
        with c12:
            st.checkbox("Lancamento recorrente mensal", key="fin_recorrente")
        with c13:
            st.number_input("Parcelas", min_value=1, max_value=24, step=1, key="fin_parcelas")

        st.text_area(
            "Observacoes",
            key="fin_obs",
            height=110,
            placeholder="Detalhes adicionais, comprovante, observacao da consulta, taxa, imposto, etc.",
        )

        action_cols = st.columns([1, 1, 1.2], gap="medium")
        with action_cols[0]:
            submit_label = "Atualizar lancamento" if st.session_state.get("finance_edit_id") else "Salvar lancamento"
            submit_clicked = st.button(submit_label, type="primary", use_container_width=True, key="fin_submit")
        with action_cols[1]:
            clear_clicked = st.button("Limpar formulario", use_container_width=True, key="fin_clear")
        with action_cols[2]:
            st.markdown('<span class="dh-fin-badge">Fluxo pensado para consultorio e pequena clinica</span>', unsafe_allow_html=True)

        if clear_clicked:
            _finance_reset_form()
            st.rerun()

        if submit_clicked:
            descricao = (st.session_state.get("fin_desc") or "").strip()
            valor = _finance_float(st.session_state.get("fin_valor"))
            tipo = st.session_state.get("fin_tipo") or "Receita"
            categoria = st.session_state.get("fin_categoria") or _finance_categories_for(tipo)[0]
            subcategoria = (st.session_state.get("fin_subcategoria") or "").strip()
            data_ref = _finance_parse_date(st.session_state.get("fin_data"))
            forma_pagamento = st.session_state.get("fin_pagamento") or "Pix"
            status = st.session_state.get("fin_status") or _finance_default_status(tipo)
            observacoes = (st.session_state.get("fin_obs") or "").strip()
            paciente_nome = (st.session_state.get("fin_paciente") or "").strip() if st.session_state.get("fin_tem_paciente") else ""
            origem = st.session_state.get("fin_origem") or "Manual"
            recorrente = bool(st.session_state.get("fin_recorrente"))
            parcelas = max(1, int(st.session_state.get("fin_parcelas") or 1))

            if not descricao:
                st.error("Informe a descricao do lancamento.")
            elif valor <= 0:
                st.error("Informe um valor valido maior que zero.")
            else:
                edit_id = st.session_state.get("finance_edit_id") or ""
                if edit_id:
                    updated_entries = []
                    for entry in all_entries:
                        if entry.get("id") != edit_id:
                            updated_entries.append(entry)
                            continue
                        updated_entries.append(
                            {
                                **entry,
                                "data": str(data_ref),
                                "descricao": descricao,
                                "valor": valor,
                                "tipo": tipo,
                                "categoria": categoria,
                                "subcategoria": subcategoria,
                                "forma_pagamento": forma_pagamento,
                                "status": status,
                                "observacoes": observacoes,
                                "paciente": paciente_nome,
                                "origem": origem,
                                "recorrente": recorrente,
                                "parcelas_total": parcelas,
                                "parcela_atual": min(int(entry.get("parcela_atual") or 1), parcelas),
                                "updated_at": datetime.now().isoformat(timespec="seconds"),
                            }
                        )
                    _finance_commit(updated_entries)
                    st.success("Lancamento atualizado.")
                else:
                    owner = (st.session_state.get("usuario") or "").strip().lower()
                    created = 0
                    for idx in range(parcelas):
                        parcela_date = _finance_add_months(data_ref, idx) if (recorrente or parcelas > 1) else data_ref
                        all_entries.append(
                            {
                                "id": uuid.uuid4().hex,
                                "dono": owner,
                                "data": str(parcela_date),
                                "descricao": descricao,
                                "valor": valor,
                                "tipo": tipo,
                                "categoria": categoria,
                                "subcategoria": subcategoria,
                                "forma_pagamento": forma_pagamento,
                                "status": status if idx == 0 else "Pendente",
                                "observacoes": observacoes,
                                "paciente": paciente_nome,
                                "origem": "Recorrencia" if (recorrente or parcelas > 1) else origem,
                                "recorrente": recorrente or parcelas > 1,
                                "parcelas_total": parcelas,
                                "parcela_atual": idx + 1,
                                "created_at": datetime.now().isoformat(timespec="seconds"),
                                "updated_at": datetime.now().isoformat(timespec="seconds"),
                            }
                        )
                        created += 1
                    _finance_commit(all_entries)
                    st.success(f"{created} lancamento(s) salvo(s).")
                _finance_reset_form()
                st.rerun()

    with insight_col:
        st.markdown(
            """
<section class="dh-fin-panel">
  <h3 class="dh-fin-panel-title">Resumo do periodo</h3>
  <p class="dh-fin-panel-subtitle">Leitura rapida do caixa, pendencias e categorias que mais impactam o consultorio.</p>
</section>
""",
            unsafe_allow_html=True,
        )
        top_receitas = _finance_summary_by_category(filtrados, "Receita")
        top_despesas = _finance_summary_by_category(filtrados, "Despesa")
        insights_html = [
            f'<div class="dh-fin-inline-stat"><span class="dh-fin-inline-label">Saldo atual</span><span class="dh-fin-inline-value">{html.escape(_format_brl(saldo_periodo))}</span></div>',
            f'<div class="dh-fin-inline-stat"><span class="dh-fin-inline-label">Pendencias abertas</span><span class="dh-fin-inline-value">{len(pendentes)}</span></div>',
            f'<div class="dh-fin-inline-stat"><span class="dh-fin-inline-label">Maior categoria de receita</span><span class="dh-fin-inline-value">{html.escape(top_receitas.iloc[0]["Categoria"] if not top_receitas.empty else "-")}</span></div>',
            f'<div class="dh-fin-inline-stat"><span class="dh-fin-inline-label">Maior categoria de despesa</span><span class="dh-fin-inline-value">{html.escape(top_despesas.iloc[0]["Categoria"] if not top_despesas.empty else "-")}</span></div>',
        ]
        st.markdown(f'<div class="dh-fin-panel">{"".join(insights_html)}</div>', unsafe_allow_html=True)

        if top_despesas.empty and top_receitas.empty:
            st.markdown('<div class="dh-fin-empty">Ainda nao ha dados suficientes para gerar insights por categoria.</div>', unsafe_allow_html=True)
        else:
            if not top_receitas.empty:
                st.caption("Receitas por categoria")
                receita_preview = top_receitas.copy()
                receita_preview["Total"] = receita_preview["Total"].map(_format_brl)
                st.dataframe(receita_preview.head(5), use_container_width=True, height=240)
            if not top_despesas.empty:
                st.caption("Despesas por categoria")
                despesa_preview = top_despesas.copy()
                despesa_preview["Total"] = despesa_preview["Total"].map(_format_brl)
                st.dataframe(despesa_preview.head(5), use_container_width=True, height=240)

    st.write("")
    st.markdown(
        """
<section class="dh-fin-panel">
  <h3 class="dh-fin-panel-title">Historico de movimentacoes</h3>
  <p class="dh-fin-panel-subtitle">Tabela operacional com filtros ativos e painel de acoes para editar, duplicar, excluir ou dar baixa.</p>
</section>
""",
        unsafe_allow_html=True,
    )

    if filtrados:
        render_table(_finance_build_table(filtrados), min_height=260, max_height=620)
    else:
        st.markdown('<div class="dh-fin-empty">Nenhum lancamento encontrado com os filtros atuais.</div>', unsafe_allow_html=True)

    st.write("")
    st.markdown("### Lancamentos recentes")
    recentes = sorted(filtrados, key=lambda x: (x.get("data", ""), x.get("created_at", "")), reverse=True)[:12]
    if not recentes:
        st.markdown('<div class="dh-fin-empty">Registre o primeiro lancamento para comecar o controle financeiro do consultorio.</div>', unsafe_allow_html=True)
    for entry in recentes:
        valor_color = "rgba(134,239,172,0.98)" if entry.get("tipo") == "Receita" else "rgba(254,202,202,0.98)"
        st.markdown(
            f"""
<div class="dh-fin-entry">
  <div class="dh-fin-entry-top">
    <div>
      <div class="dh-fin-entry-title">{html.escape(entry.get("descricao") or "Lancamento sem descricao")}</div>
      <div class="dh-fin-entry-meta">{html.escape(datetime.strptime(entry["data"], "%Y-%m-%d").strftime("%d/%m/%Y"))} · {html.escape(entry.get("categoria") or "Outro")} · {html.escape(entry.get("forma_pagamento") or "Pix")}</div>
    </div>
    <div class="dh-fin-entry-value" style="color:{valor_color};">{html.escape(_format_brl(entry.get("valor")))}</div>
  </div>
  <div class="dh-fin-entry-tags">
    <span class="dh-fin-chip {'dh-fin-chip-income' if entry.get('tipo') == 'Receita' else 'dh-fin-chip-expense'}">{html.escape(entry.get("tipo"))}</span>
    <span class="dh-fin-chip">{html.escape(entry.get("status"))}</span>
    <span class="dh-fin-chip">{html.escape(entry.get("paciente") or "Sem paciente")}</span>
    {"<span class='dh-fin-chip dh-fin-chip-alert'>Vencido</span>" if _finance_is_overdue(entry) else ""}
  </div>
</div>
""",
            unsafe_allow_html=True,
        )
        a1, a2, a3, a4, a5 = st.columns(5, gap="small")
        with a1:
            if st.button("Editar", key=f"fin_edit_{entry['id']}", use_container_width=True):
                _finance_load_entry_into_form(entry)
                st.rerun()
        with a2:
            if st.button("Excluir", key=f"fin_del_{entry['id']}", use_container_width=True):
                _finance_commit([e for e in all_entries if e.get("id") != entry.get("id")])
                st.rerun()
        with a3:
            mark_label = "Marcar recebido" if entry.get("tipo") == "Receita" else "Marcar pago"
            if st.button(mark_label, key=f"fin_mark_{entry['id']}", use_container_width=True):
                updated = []
                final_status = "Recebido" if entry.get("tipo") == "Receita" else "Pago"
                for current in all_entries:
                    if current.get("id") == entry.get("id"):
                        updated.append({**current, "status": final_status, "updated_at": datetime.now().isoformat(timespec="seconds")})
                    else:
                        updated.append(current)
                _finance_commit(updated)
                st.rerun()
        with a4:
            if st.button("Duplicar", key=f"fin_dup_{entry['id']}", use_container_width=True):
                all_entries.append(
                    {
                        **entry,
                        "id": uuid.uuid4().hex,
                        "data": str(datetime.now().date()),
                        "status": _finance_default_status(entry.get("tipo", "Receita")),
                        "created_at": datetime.now().isoformat(timespec="seconds"),
                        "updated_at": datetime.now().isoformat(timespec="seconds"),
                    }
                )
                _finance_commit(all_entries)
                st.rerun()
        with a5:
            with st.popover("Detalhes", use_container_width=True):
                st.write(f"**Descricao:** {entry.get('descricao')}")
                st.write(f"**Tipo:** {entry.get('tipo')}")
                st.write(f"**Categoria:** {entry.get('categoria')}")
                st.write(f"**Subcategoria:** {entry.get('subcategoria') or '-'}")
                st.write(f"**Status:** {entry.get('status')}")
                st.write(f"**Paciente:** {entry.get('paciente') or '-'}")
                st.write(f"**Origem:** {entry.get('origem') or '-'}")
                st.write(f"**Observacoes:** {entry.get('observacoes') or '-'}")

    st.write("")
    st.markdown("### Analise por categoria")
    resumo_rec = _finance_summary_by_category(filtrados, "Receita")
    resumo_desp = _finance_summary_by_category(filtrados, "Despesa")
    chart_col1, chart_col2 = st.columns(2, gap="large")
    with chart_col1:
        st.caption("Receitas")
        if resumo_rec.empty:
            st.info("Sem receitas no periodo selecionado.")
        else:
            fig_rec = px.bar(
                resumo_rec.head(7),
                x="Total",
                y="Categoria",
                orientation="h",
                text="Total",
                color_discrete_sequence=["#22c55e"],
            )
            fig_rec.update_layout(height=330, margin=dict(l=10, r=10, t=10, b=10), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
            fig_rec.update_yaxes(categoryorder="total ascending")
            st.plotly_chart(fig_rec, use_container_width=True)
    with chart_col2:
        st.caption("Despesas")
        if resumo_desp.empty:
            st.info("Sem despesas no periodo selecionado.")
        else:
            fig_desp = px.bar(
                resumo_desp.head(7),
                x="Total",
                y="Categoria",
                orientation="h",
                text="Total",
                color_discrete_sequence=["#fb7185"],
            )
            fig_desp.update_layout(height=330, margin=dict(l=10, r=10, t=10, b=10), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
            fig_desp.update_yaxes(categoryorder="total ascending")
            st.plotly_chart(fig_desp, use_container_width=True)


def modulo_financeiro():
    render_financial_module(
        {
            "load_db": load_db,
            "save_db": save_db,
            "patients": pacientes,
            "filter_patients": filtrar_por_usuario,
            "patient_cpf": _patient_record_cpf,
            "wa_link": _wa_link,
            "format_brl": _format_brl,
            "to_float": _finance_float,
            "parse_date": _finance_parse_date,
            "receipt_pdf": gerar_pdf_pro,
            "get_user": _get_user_obj,
        }
    )

def modulo_biblioteca():
    st.markdown(
        """
        <style>
        .dh-library-shell{display:flex;flex-direction:column;gap:18px;}
        .dh-library-hero{display:grid;grid-template-columns:minmax(0,2.25fr) minmax(280px,1fr);gap:18px;padding:24px;border-radius:24px;border:1px solid rgba(82,224,180,0.14);background:linear-gradient(135deg, rgba(10,20,37,0.98), rgba(16,33,58,0.94));box-shadow:0 24px 52px rgba(0,0,0,0.28);}
        .dh-library-hero h2{margin:0;color:#f8fbff;font-size:2.1rem;font-weight:800;letter-spacing:-0.03em;}
        .dh-library-hero p{margin:10px 0 0;color:#b8cae0;line-height:1.62;font-size:1rem;max-width:780px;}
        .dh-library-pills{display:flex;flex-wrap:wrap;gap:10px;margin-top:18px;}
        .dh-library-pill{padding:8px 12px;border-radius:999px;border:1px solid rgba(87,223,179,0.18);background:rgba(17,34,58,0.88);color:#e9fff6;font-size:0.82rem;font-weight:700;}
        .dh-library-kpis{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px;}
        .dh-library-kpi{padding:16px;border-radius:18px;background:rgba(10,20,36,0.82);border:1px solid rgba(255,255,255,0.06);min-height:102px;}
        .dh-library-kpi strong{display:block;color:#ffffff;font-size:1.28rem;margin-bottom:4px;}
        .dh-library-kpi span{display:block;color:#99b3ca;font-size:0.87rem;line-height:1.45;}
        .dh-library-card{border-radius:22px;border:1px solid rgba(255,255,255,0.06);background:linear-gradient(180deg, rgba(15,26,46,0.97), rgba(11,19,35,0.97));padding:18px;box-shadow:0 20px 36px rgba(0,0,0,0.2);}
        .dh-library-card h4,.dh-library-card h5{margin:0 0 10px;color:#f4f8ff;font-weight:800;}
        .dh-library-card p{margin:0;color:#b9cadb;line-height:1.58;}
        .dh-library-topic-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:14px;}
        .dh-library-topic{padding:16px;border-radius:18px;border:1px solid rgba(255,255,255,0.06);background:rgba(14,26,44,0.92);height:100%;}
        .dh-library-topic small{display:block;color:#66e4b7;font-size:0.77rem;font-weight:700;text-transform:uppercase;letter-spacing:0.05em;margin-bottom:7px;}
        .dh-library-topic b{display:block;color:#f8fbff;margin-bottom:8px;font-size:0.98rem;}
        .dh-library-topic p{margin:0;color:#b8c7d9;line-height:1.5;font-size:0.9rem;}
        .dh-library-empty{border:1px dashed rgba(255,255,255,0.12);background:rgba(10,20,36,0.7);border-radius:18px;padding:18px;color:#a8bdd3;}
        .dh-library-mini{padding:15px;border-radius:18px;background:rgba(11,23,40,0.74);border:1px solid rgba(255,255,255,0.06);}
        .dh-library-mini strong{display:block;color:#f8fbff;margin-bottom:6px;}
        .dh-library-mini span{color:#9db4cb;font-size:0.88rem;line-height:1.48;}
        .dh-library-public-shell{display:flex;flex-direction:column;gap:18px;}
        .dh-library-public-hero{padding:24px;border-radius:24px;border:1px solid rgba(82,224,180,0.16);background:linear-gradient(135deg, rgba(10,20,37,0.98), rgba(16,33,58,0.94));box-shadow:0 24px 52px rgba(0,0,0,0.28);}
        .dh-library-public-hero h2{margin:0;color:#f8fbff;font-size:2rem;font-weight:800;letter-spacing:-0.03em;}
        .dh-library-public-hero p{margin:10px 0 0;color:#c4d4e6;line-height:1.65;font-size:1rem;max-width:760px;}
        .dh-library-public-list{display:flex;flex-direction:column;gap:16px;}
        .dh-library-public-article{position:relative;padding:22px 22px 22px 24px;border-radius:24px;border:1px solid rgba(98,119,150,0.26);background:linear-gradient(180deg, rgba(20,31,52,0.98), rgba(12,20,35,0.98));box-shadow:0 18px 36px rgba(0,0,0,0.22);overflow:hidden;}
        .dh-library-public-article::before{content:"";position:absolute;left:0;top:0;bottom:0;width:4px;background:linear-gradient(180deg,#52e0b4,#79b8ff);}
        .dh-library-public-meta{display:flex;flex-wrap:wrap;gap:10px;margin-bottom:14px;}
        .dh-library-public-badge{display:inline-flex;align-items:center;padding:7px 12px;border-radius:999px;background:rgba(82,224,180,0.12);border:1px solid rgba(82,224,180,0.22);color:#dffdf3;font-size:0.8rem;font-weight:700;}
        .dh-library-public-article h3{margin:0 0 12px;color:#f8fbff;font-size:1.6rem;line-height:1.18;font-weight:800;letter-spacing:-0.02em;}
        .dh-library-public-article p{margin:0;color:#d3dfec;line-height:1.72;font-size:1rem;}
        .dh-library-public-actions{display:flex;flex-wrap:wrap;gap:12px;margin-top:16px;align-items:center;}
        .dh-library-public-link{display:inline-flex;align-items:center;gap:8px;color:#7ee7c2 !important;font-weight:700;text-decoration:none !important;}
        .dh-library-public-link:hover{color:#b5f5de !important;}
        .dh-library-public-note{color:#93a9c2;font-size:0.9rem;line-height:1.5;}
        @media (max-width:1100px){.dh-library-hero{grid-template-columns:1fr;}.dh-library-topic-grid{grid-template-columns:1fr;}.dh-library-kpis{grid-template-columns:1fr 1fr;}}
        @media (max-width:760px){.dh-library-kpis{grid-template-columns:1fr;}.dh-library-public-hero{padding:20px;}.dh-library-public-article{padding:18px 18px 18px 20px;}.dh-library-public-article h3{font-size:1.32rem;}.dh-library-public-actions{flex-direction:column;align-items:flex-start;gap:8px;}}
        </style>
        """,
        unsafe_allow_html=True,
    )

    def _news_sort_key(article):
        try:
            return datetime.strptime(str(article.get("data", "")), "%Y-%m-%d")
        except Exception:
            return datetime.min

    normalized_news = []
    for idx, article in enumerate(list(noticias)):
        item = dict(article or {})
        item["_index"] = idx
        item["titulo"] = item.get("titulo") or "(Sem titulo)"
        item["texto"] = item.get("texto") or ""
        item["link"] = item.get("link") or ""
        item["categoria"] = item.get("categoria") or "Atualizacoes"
        item["data"] = item.get("data") or str(datetime.now().date())
        texto_limpo = (item["texto"] or "").strip()
        item["resumo_curto"] = (texto_limpo[:180] + "...") if len(texto_limpo) > 180 else (texto_limpo or "Sem resumo.")
        normalized_news.append(item)

    is_admin = st.session_state.get("tipo") == "admin"
    sorted_news = sorted(normalized_news, key=_news_sort_key, reverse=True)
    categories = sorted({item.get("categoria", "Atualizacoes") for item in sorted_news}) or ["Atualizacoes"]
    current_month = datetime.now().strftime("%Y-%m")
    news_this_month = sum(1 for item in sorted_news if str(item.get("data", "")).startswith(current_month))
    linked_news = sum(1 for item in sorted_news if item.get("link"))
    category_df = pd.DataFrame(sorted_news)
    if not category_df.empty:
        category_summary = (
            category_df.groupby("categoria", as_index=False)
            .agg(Publicacoes=("titulo", "count"))
            .sort_values("Publicacoes", ascending=False)
        )
    else:
        category_summary = pd.DataFrame(columns=["categoria", "Publicacoes"])

    highlighted_topics = [
        {"categoria": "Clinico", "titulo": "Materiais de apoio", "texto": "Centralize protocolos, resumos tecnicos e orientacoes para acesso rapido no atendimento."},
        {"categoria": "Operacional", "titulo": "Atualizacoes internas", "texto": "Registre mudancas no fluxo, novas rotinas e comunicados para toda a equipe."},
        {"categoria": "IA", "titulo": "Pesquisa assistida", "texto": "Gere resumos praticos para estudo, marketing ou organizacao do consultorio."},
    ]
    if sorted_news:
        highlighted_topics = [
            {
                "categoria": item.get("categoria", "Atualizacoes"),
                "titulo": item.get("titulo", "(Sem titulo)"),
                "texto": item.get("resumo_curto", "Sem resumo."),
            }
            for item in sorted_news[:3]
        ]

    if not is_admin:
        st.markdown(
            f"""
            <div class="dh-library-public-shell">
                <div class="dh-library-public-hero">
                    <h2>Biblioteca</h2>
                    <p>Aqui ficam apenas as noticias publicadas pelo admin para consulta rapida da equipe e dos usuarios do sistema.</p>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        if sorted_news:
            st.markdown('<div class="dh-library-public-list">', unsafe_allow_html=True)
            for item in sorted_news:
                link_html = ""
                if item.get("link"):
                    safe_link = html.escape(item.get("link", ""))
                    link_html = f'<a class="dh-library-public-link" href="{safe_link}" target="_blank">Abrir fonte original</a>'
                st.markdown(
                    f"""
                    <article class="dh-library-public-article">
                        <div class="dh-library-public-meta">
                            <span class="dh-library-public-badge">{html.escape(item.get("categoria", "Atualizacoes"))}</span>
                            <span class="dh-library-public-badge">{html.escape(item.get("data", ""))}</span>
                        </div>
                        <h3>{html.escape(item.get("titulo", "(Sem titulo)"))}</h3>
                        <p>{html.escape(item.get("texto", "") or item.get("resumo_curto", "Sem resumo."))}</p>
                        <div class="dh-library-public-actions">
                            {link_html}
                            <span class="dh-library-public-note">Comunicado publicado na Biblioteca do DietHealth.</span>
                        </div>
                    </article>
                    """,
                    unsafe_allow_html=True,
                )
            st.markdown("</div>", unsafe_allow_html=True)
        else:
            st.markdown(
                '<div class="dh-library-empty">Nenhuma noticia publicada no momento.</div>',
                unsafe_allow_html=True,
            )
        return

    st.markdown(
        f"""
        <div class="dh-library-hero">
            <div>
                <h2>Biblioteca inteligente</h2>
                <p>Transforme a Biblioteca em um hub de conteudo para o consultorio: noticias internas, referencias rapidas, pesquisas por IA e materiais de apoio organizados por categoria.</p>
                <div class="dh-library-pills">
                    <div class="dh-library-pill">{len(sorted_news)} itens publicados</div>
                    <div class="dh-library-pill">{news_this_month} publicados neste mes</div>
                    <div class="dh-library-pill">{len(categories)} categorias ativas</div>
                    <div class="dh-library-pill">Pesquisa IA integrada</div>
                </div>
            </div>
            <div class="dh-library-kpis">
                <div class="dh-library-kpi"><strong>{len(sorted_news)}</strong><span>conteudos disponiveis para consulta rapida no sistema</span></div>
                <div class="dh-library-kpi"><strong>{linked_news}</strong><span>itens com fonte externa ou link original associado</span></div>
                <div class="dh-library-kpi"><strong>{category_summary.iloc[0]['categoria'] if not category_summary.empty else 'Atualizacoes'}</strong><span>categoria com mais volume de materiais hoje</span></div>
                <div class="dh-library-kpi"><strong>{'Admin' if is_admin else 'Usuario'}</strong><span>perfil atual de acesso na central de conteudo</span></div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    t1, t2 = st.tabs(["Conteudos", "Pesquisa IA"])

    with t1:
        filter_col1, filter_col2, filter_col3 = st.columns([1.45, 1, 1])
        news_search = filter_col1.text_input(
            "Buscar conteudo",
            placeholder="Ex: consulta nutricional, marketing, atualizacao, protocolo clinico...",
            key="biblioteca_busca",
        )
        selected_category = filter_col2.selectbox("Categoria", ["Todas"] + categories, key="biblioteca_categoria")
        sort_mode = filter_col3.selectbox("Ordenar por", ["Mais recentes", "Mais antigos", "Titulo A-Z"], key="biblioteca_ordenacao")

        filtered_news = []
        search_term = (news_search or "").strip().lower()
        for item in sorted_news:
            haystack = " ".join([item.get("titulo", ""), item.get("texto", ""), item.get("categoria", "")]).lower()
            if selected_category != "Todas" and item.get("categoria") != selected_category:
                continue
            if search_term and search_term not in haystack:
                continue
            filtered_news.append(item)

        if sort_mode == "Mais antigos":
            filtered_news = sorted(filtered_news, key=_news_sort_key)
        elif sort_mode == "Titulo A-Z":
            filtered_news = sorted(filtered_news, key=lambda item: str(item.get("titulo", "")).lower())

        st.markdown("#### Temas em destaque")
        st.markdown('<div class="dh-library-topic-grid">', unsafe_allow_html=True)
        for topic in highlighted_topics:
            st.markdown(
                f'<div class="dh-library-topic"><small>{topic.get("categoria","Atualizacoes")}</small><b>{topic.get("titulo","(Sem titulo)")}</b><p>{topic.get("texto","Sem resumo.")}</p></div>',
                unsafe_allow_html=True,
            )
        st.markdown("</div>", unsafe_allow_html=True)

        overview_col, insight_col = st.columns([1.55, 1], gap="large")
        with overview_col:
            with st.container(key="dh_library_recent_shell"):
                st.markdown("### Conteudos recentes")
                if filtered_news:
                    for item in filtered_news:
                        with st.container(border=True):
                            title_col, tag_col = st.columns([1.4, 0.6])
                            title_col.markdown(f"### {item.get('titulo', '(Sem titulo)')}")
                            tag_col.markdown(
                                f'<div class="dh-pill-soft" style="margin-top:6px;">{item.get("categoria","Atualizacoes")} - {item.get("data","")}</div>',
                                unsafe_allow_html=True,
                            )
                            st.write(item.get("texto", ""))
                            st.caption(f"Resumo curto: {item.get('resumo_curto', 'Sem resumo.')}")
                            action_cols = st.columns([0.95, 0.85, 1.05])
                            if item.get("link"):
                                action_cols[0].markdown(f"Abrir fonte original: [link]({item['link']})")
                            else:
                                action_cols[0].caption("Sem link externo")
                            if action_cols[1].button("Copiar resumo", key=f"copy_news_{item['_index']}"):
                                st.code(item.get("texto", ""), language="text")
                            if is_admin:
                                if action_cols[2].button("Excluir", key=f"del_news_{item['_index']}"):
                                    noticias.pop(item["_index"])
                                    save_db("noticias.json", noticias)
                                    st.rerun()
                else:
                    st.markdown(
                        '<div class="dh-library-empty">Nenhum conteudo encontrado com esse filtro. Ajuste a busca, a categoria ou publique um novo material.</div>',
                        unsafe_allow_html=True,
                    )

        with insight_col:
            with st.container(key="dh_library_side_shell"):
                if is_admin:
                    st.markdown(
                        '<div class="dh-library-card"><h4>Nova postagem</h4><p>Publique atualizacoes, referencias clinicas, avisos operacionais e materiais de apoio para o consultorio.</p></div>',
                        unsafe_allow_html=True,
                    )
                    with st.form("post"):
                        t = st.text_input("Titulo da postagem")
                        categoria = st.selectbox(
                            "Categoria da postagem",
                            ["Atualizacoes", "Conteudo clinico", "Marketing", "Sistema", "Financeiro", "WhatsApp/API", "Outro"],
                            index=0,
                        )
                        c = st.text_area("Conteudo / Resumo", height=180)
                        l = st.text_input("Link original (URL)", placeholder="https://...")
                        if st.form_submit_button("Postar noticia"):
                            noticias.append({
                                "titulo": t,
                                "texto": c,
                                "link": l,
                                "categoria": categoria,
                                "data": str(datetime.now().date()),
                            })
                            save_db("noticias.json", noticias)
                            st.rerun()
                else:
                    st.markdown(
                        '<div class="dh-library-card"><h4>Resumo rapido</h4><p>Use busca e categorias para achar materiais mais rapido. A biblioteca funciona melhor quando cada item tem titulo objetivo, resumo claro e categoria consistente.</p></div>',
                        unsafe_allow_html=True,
                    )

                st.write("")
                mini1, mini2 = st.columns(2)
                mini1.markdown(
                    '<div class="dh-library-mini"><strong>Como usar melhor</strong><span>Crie titulos curtos e categorias padronizadas para facilitar busca futura e reaproveitamento do conteudo.</span></div>',
                    unsafe_allow_html=True,
                )
                mini2.markdown(
                    '<div class="dh-library-mini"><strong>Fluxo ideal</strong><span>Publique noticias internas, links de referencia e resumos praticos para consulta rapida durante o atendimento.</span></div>',
                    unsafe_allow_html=True,
                )

                if not category_summary.empty:
                    st.write("")
                    st.markdown("#### Volume por categoria")
                    fig_cat = px.bar(
                        category_summary.head(6),
                        x="Publicacoes",
                        y="categoria",
                        orientation="h",
                        text="Publicacoes",
                        color_discrete_sequence=["#52e0b4"],
                    )
                    fig_cat.update_layout(
                        height=280,
                        margin=dict(l=10, r=10, t=10, b=10),
                        paper_bgcolor="rgba(0,0,0,0)",
                        plot_bgcolor="rgba(0,0,0,0)",
                    )
                    fig_cat.update_yaxes(categoryorder="total ascending")
                    st.plotly_chart(fig_cat, use_container_width=True)

        st.write("")
        analytics_col1, analytics_col2 = st.columns([1.1, 1], gap="large")
        with analytics_col1:
            st.markdown("### Leitura operacional")
            metric_cols = st.columns(3)
            metric_cols[0].metric("Filtrados agora", len(filtered_news))
            metric_cols[1].metric("Com link externo", sum(1 for item in filtered_news if item.get("link")))
            metric_cols[2].metric("Sem categoria customizada", sum(1 for item in filtered_news if item.get("categoria") == "Atualizacoes"))

            recent_df = pd.DataFrame(filtered_news)
            if not recent_df.empty:
                view_df = recent_df[["data", "titulo", "categoria", "link"]].rename(
                    columns={"data": "Data", "titulo": "Titulo", "categoria": "Categoria", "link": "Link"}
                )
                st.dataframe(view_df, use_container_width=True, hide_index=True)
            else:
                st.info("Sem conteudos para listar com os filtros atuais.")

        with analytics_col2:
            st.markdown("### FAQ rapido da Biblioteca")
            with st.expander("Como registrar um conteudo util para a equipe?", expanded=True):
                st.write("Use um titulo objetivo, descreva o contexto no resumo e adicione categoria coerente. Se houver fonte original, inclua o link.")
            with st.expander("Qual a melhor categoria para atualizacao interna?"):
                st.write("Use 'Sistema' para mudancas tecnicas, 'Atualizacoes' para comunicados gerais e 'Conteudo clinico' para materiais de apoio ao atendimento.")
            with st.expander("Como reaproveitar a pesquisa IA na rotina?"):
                st.write("Pesquise um tema, copie o resumo e transforme em procedimento interno, checklist de atendimento ou material de referencia.")

    with t2:
        top_ia_col, top_ia_side = st.columns([1.55, 1], gap="large")
        with top_ia_col:
            st.markdown(
                '<div class="dh-library-card"><h4>Pesquisa IA para consultorio</h4><p>Pesquise temas clinicos, operacionais ou de marketing e gere uma base inicial para estudo, comunicados internos e padroes de atendimento.</p></div>',
                unsafe_allow_html=True,
            )
        with top_ia_side:
            st.markdown(
                '<div class="dh-library-card"><h4>Atalhos uteis</h4><p>Use os temas sugeridos para acelerar pesquisas comuns do dia a dia, sem depender de um prompt manual toda vez.</p></div>',
                unsafe_allow_html=True,
            )

        suggestion_cols = st.columns(3)
        suggested_prompts = [
            "Como estruturar retorno nutricional com melhor adesao?",
            "Ideias de conteudo para captar pacientes pelo Instagram",
            "Checklist para organizar o fluxo financeiro do consultorio",
        ]
        for idx, prompt_text in enumerate(suggested_prompts):
            if suggestion_cols[idx].button(prompt_text, key=f"biblioteca_ia_prompt_{idx}", use_container_width=True):
                st.session_state["biblioteca_ia_tema"] = prompt_text
                st.rerun()

        q_col1, q_col2 = st.columns([1.15, 0.85])
        q = q_col1.text_input("Tema de pesquisa", key="biblioteca_ia_tema")
        quick_topic = q_col2.selectbox(
            "Temas sugeridos",
            [
                "Livre",
                "Marketing nutricional",
                "Consulta de retorno",
                "Educacao alimentar",
                "Gestao de consultorio",
                "WhatsApp para pacientes",
                "Avaliacao fisica",
                "Plano alimentar semanal",
            ],
            index=0,
            key="biblioteca_ia_sugestao",
        )
        if quick_topic != "Livre" and not q:
            q = quick_topic

        extra_col1, extra_col2, extra_col3 = st.columns([1, 1, 1])
        tone = extra_col1.selectbox("Formato da resposta", ["Resumo pratico", "Checklist", "Passo a passo", "Ideias de aplicacao"], index=0)
        focus = extra_col2.selectbox("Foco", ["Clinico", "Operacional", "Marketing", "Educacional"], index=1)
        depth = extra_col3.selectbox("Profundidade", ["Rapida", "Intermediaria", "Detalhada"], index=1)

        if st.button("Pesquisar com IA", key="biblioteca_ia_buscar"):
            if not q.strip():
                st.warning("Informe um tema antes de pesquisar.")
            elif not ia_ok():
                st.error("Configure a GROQ_API_KEY (Secrets ou variavel de ambiente).")
            else:
                clinical_prompt_block = _clinical_ai_prompt("assistant", q, focus, tone, depth)
                client = get_groq_client()
                if client is None:
                    st.error("GROQ_API_KEY nao encontrada. Configure a variavel no Railway e reinicie o servico.")
                    st.stop()
                with st.spinner("Pesquisando..."):
                    try:
                        prompt = (
                            f"Crie um {tone.lower()} sobre '{q}' com foco {focus.lower()} para uso no DietHealth. "
                            f"Nivel de profundidade: {depth.lower()}. "
                            "Responda em portugues brasileiro, com orientacoes objetivas, subtitulos claros, bullets praticos "
                            "e uma secao final chamada 'Como aplicar no consultorio'."
                        )
                        if clinical_prompt_block:
                            prompt = f"{prompt}\n\n{clinical_prompt_block}"
                        res = client.chat.completions.create(
                            messages=[{"role": "user", "content": prompt}],
                            model="llama-3.3-70b-versatile",
                        ).choices[0].message.content
                        result_col, helper_col = st.columns([1.5, 0.9], gap="large")
                        with result_col:
                            st.markdown("### Resultado da pesquisa")
                            st.write(res)
                        with helper_col:
                            st.markdown(
                                '<div class="dh-library-card"><h4>Como aproveitar melhor</h4><p>Transforme a resposta em checklist interno, protocolo curto ou base para conteudo educativo. Ajuste o texto antes de usar com pacientes.</p></div>',
                                unsafe_allow_html=True,
                            )
                            st.markdown(
                                '<div class="dh-library-card" style="margin-top:12px;"><h4>Perguntas relacionadas</h4><p>Pesquise tambem por fluxos complementares, objecoes frequentes e padroes de atendimento para aprofundar o tema.</p></div>',
                                unsafe_allow_html=True,
                            )
                    except Exception as e:
                        if "invalid_api_key" in str(e).lower() or "invalid api key" in str(e).lower():
                            st.error("Erro IA: chave invalida. Confirme GROQ_API_KEY no Railway e reinicie o servico.")
                        else:
                            st.error(f"Erro: {e}")


def modulo_chat():
    st.title("💬 Chat da Equipe (Global)")
    st.markdown('<div class="dh-pill-soft">Mensagens internas entre usuários logados.</div>', unsafe_allow_html=True)
    st.write("")

    for m in chat_log:
        st.write(f"**{m.get('user','')}**: {m.get('msg','')}")
    if x := st.chat_input("Msg"):
        chat_log.append({"user": st.session_state["usuario"], "msg": x})
        save_db("chat_log.json", chat_log)
        st.rerun()

def _build_ia_system_prompt(modo: str, custom: str = "") -> str:
    modo = (modo or "").strip().lower()
    guardrails = build_global_nutrition_guardrails(_clinical_ai_payload())
    if modo == "suporte":
        return (
            "Você é o suporte oficial do DietHealth System. Responda de forma objetiva, "
            "com passos claros e linguagem simples. Se faltar informação, pergunte. "
            "Escreva sempre em português brasileiro correto, com ortografia e gramática revisadas."
        )
    if modo == "marketing":
        return (
            "Você é especialista em marketing e vendas para nutricionistas. "
            "Crie textos persuasivos, claros e curtos, sem promessas médicas. "
            "Escreva sempre em português brasileiro correto, com ortografia e gramática revisadas."
        )
    if modo == "personalizado":
        return custom.strip() if custom.strip() else "Você é um assistente útil e objetivo."
    return (
        "Você é um assistente nutricional clínico. Forneça orientações gerais e seguras, "
        "sem substituir avaliação profissional. Evite diagnósticos e prescrição médica. "
        "Escreva sempre em português brasileiro correto, com ortografia e gramática revisadas. "
        f"{guardrails}"
    )

DIETHEALTH_SUPPORT_KB = """
O DietHealth System é um software para nutricionistas/consultórios com os módulos:
- Dashboard: visão geral rápida.
- Agenda: agendar, editar e visualizar atendimentos.
- Consultório/Prontuário: cadastro de pacientes, avaliações, histórico e anexos.
- Portal do Paciente (web/PWA): painel do paciente com dietas, consultas, avisos e chat.
- Prescrições & Exames: criação de prescrições e PDFs com assinatura.
- Atestado: emissão de atestado nutricional com IA e PDF assinado.
- Gráficos: evolução (peso e indicadores).
- Relatórios: exportações e relatórios em PDF/CSV.
- Diet Generator: geração de cardápio com IA a partir de dados do paciente.
- Consulta Alimentos (IA): pesquisa e apoio por IA.
- Super Health IA (Groq): chat interno (nutrição/suporte/marketing).
- Financeiro: registrar receitas/despesas.
- Biblioteca: notícias e pesquisa.
- Chat: mensagens internas.
- Admin: gerenciar usuários, assinaturas e backup.
 - App PWA (instalável): botão `Instalar app` na página inicial para criar ícone no celular/desktop.
 - Pagamento Premium (Mercado Pago): geração de link para ativar recursos bloqueados.
Regras de acesso:
- Usuários podem ficar pendentes/bloqueados até o pagamento.
- A assinatura tem vencimento (paid_until) e bloqueia quando expira.
- Recursos Premium aparecem com cadeado; ao clicar, o sistema abre `Pagamento Premium`.
"""

def _support_system_prompt() -> str:
    return (
        "Você é o Super Health IA, o suporte oficial do software DietHealth System. "
        "Você deve responder SOMENTE sobre como usar o DietHealth (telas, botões, fluxo do sistema, cadastro, agenda, relatórios, IA, backup e assinaturas). "
        "Se o usuário perguntar sobre nutrição/saúde, prescrições médicas, programação, ou qualquer assunto fora do DietHealth, responda que seu suporte é limitado ao DietHealth e peça para reformular a dúvida para o software. "
        "Responda com passos numerados e objetivos. "
        "Se faltar informação, faça perguntas curtas para diagnosticar. "
        "Escreva sempre em português brasileiro correto, com ortografia e gramática revisadas antes de responder. "
        "\n\nBASE DO SISTEMA:\n"
        f"{DIETHEALTH_SUPPORT_KB.strip()}"
    )


_PT_BR_WORD_FIXES = {
    "nao": "não",
    "servico": "serviço",
    "variavel": "variável",
    "usuario": "usuário",
    "usuarios": "usuários",
    "invalida": "inválida",
    "informacao": "informação",
    "informacoes": "informações",
    "configuracao": "configuração",
    "configuracoes": "configurações",
    "relatorio": "relatório",
    "relatorios": "relatórios",
    "historico": "histórico",
    "historicos": "históricos",
    "conteudo": "conteúdo",
    "duvida": "dúvida",
    "duvidas": "dúvidas",
    "nutricao": "nutrição",
    "clinico": "clínico",
    "clinica": "clínica",
    "diagnostico": "diagnóstico",
    "prescricao": "prescrição",
    "prescricoes": "prescrições",
    "possivel": "possível",
    "medico": "médico",
}


def _preserve_case_replace(original: str, corrected: str) -> str:
    if original.isupper():
        return corrected.upper()
    if original[:1].isupper():
        return corrected[:1].upper() + corrected[1:]
    return corrected


def _fix_pt_br_text(text: str) -> str:
    if not isinstance(text, str) or not text.strip():
        return text

    def _fix_plain_segment(seg: str) -> str:
        out = seg
        for wrong, right in _PT_BR_WORD_FIXES.items():
            pattern = re.compile(rf"\b{re.escape(wrong)}\b", flags=re.IGNORECASE)
            out = pattern.sub(lambda m: _preserve_case_replace(m.group(0), right), out)
        return out

    # Mantém blocos de código sem alteração.
    parts = re.split(r"(```[\s\S]*?```)", text)
    fixed_parts = []
    for part in parts:
        if part.startswith("```") and part.endswith("```"):
            fixed_parts.append(part)
            continue
        subparts = re.split(r"(`[^`]*`)", part)
        for sp in subparts:
            if sp.startswith("`") and sp.endswith("`"):
                fixed_parts.append(sp)
            else:
                fixed_parts.append(_fix_plain_segment(sp))
    return "".join(fixed_parts)


SUPPORT_TOPICS = {
    "Atendimento: cadastro e acesso do paciente": {
        "category": "Atendimento",
        "summary": "Cadastro inicial do paciente e liberacao do acesso ao Portal do Paciente no modulo Atendimento.",
        "steps": [
            "Abra o modulo `Atendimento` no menu lateral.",
            "Clique em `Cadastrar paciente` e preencha nome, CPF, telefone e e-mail.",
            "Salve o cadastro e gere o codigo de acesso do paciente.",
            "Use os botoes de copiar instrucoes ou enviar por WhatsApp para liberar o portal.",
        ],
        "tips": [
            "Preencha telefone e e-mail para envio automatico do acesso.",
            "Se o paciente nao recebeu, use `Reenviar instrucoes` no mesmo card.",
        ],
        "errors": [
            "Paciente nao aparece na lista: revise se o cadastro foi salvo sem espacos extras.",
            "WhatsApp nao abre: verifique se o telefone esta com DDD e formato correto.",
        ],
        "related": ["Como usar avaliacao e historico", "Agendar atendimento na Agenda"],
        "action_label": "Abrir Atendimento",
        "action_route": "atendimento",
    },
    "Como usar avaliacao e historico": {
        "category": "Consultorio",
        "summary": "Registrar evolucao clinica, medidas, observacoes e acompanhar a linha do tempo do paciente.",
        "steps": [
            "Entre em `Consultorio` e selecione o paciente desejado (cadastro vem do Atendimento).",
            "Abra a area de avaliacao ou historico dentro do prontuario.",
            "Registre medidas, observacoes e condutas.",
            "Salve para que as informacoes possam ser reaproveitadas em outros modulos.",
        ],
        "tips": [
            "Use observacoes objetivas para encontrar a informacao depois com mais rapidez.",
            "Manter datas consistentes melhora graficos e analises.",
        ],
        "errors": [
            "Dados duplicados normalmente indicam novo registro em vez de edicao.",
            "Graficos vazios podem indicar datas antigas ou campos numericos em branco.",
        ],
        "related": ["Atendimento: cadastro e acesso do paciente", "Como gerar dieta com dados do paciente"],
        "action_label": "Ver prontuario",
        "action_route": "consultorio",
    },
    "Agendar atendimento na Agenda": {
        "category": "Agenda",
        "summary": "Criar, revisar e organizar atendimentos com controle de horario e paciente.",
        "steps": [
            "Abra o modulo `Agenda`.",
            "Clique em `Novo agendamento`.",
            "Selecione paciente, data, horario e observacoes necessarias.",
            "Salve e revise se o agendamento ficou no dia correto.",
        ],
        "tips": [
            "Use descricoes curtas para localizar agendamentos com rapidez.",
            "Se houver retorno, registre isso na descricao para diferenciar consultas.",
        ],
        "errors": [
            "Agendamento nao aparece: confira o periodo filtrado na tela.",
            "Paciente nao carrega: o cadastro precisa existir antes no Atendimento.",
        ],
        "related": ["Atendimento: cadastro e acesso do paciente", "Como configurar WhatsApp API"],
        "action_label": "Abrir Agenda",
        "action_route": "agenda",
    },
    "Como gerar dieta com dados do paciente": {
        "category": "Dietas",
        "summary": "Gerar cardapio com IA aproveitando dados do prontuario e do objetivo clinico.",
        "steps": [
            "Abra `Gerar Dieta`.",
            "Selecione o paciente e revise peso, altura, idade e objetivo.",
            "Complete observacoes clinicas e preferencias alimentares.",
            "Clique em `Gerar` e revise o cardapio antes de salvar.",
        ],
        "tips": [
            "Quanto mais consistente o prontuario, melhor a qualidade da dieta gerada.",
            "Use observacoes objetivas para reduzir retrabalho na revisao.",
        ],
        "errors": [
            "Dieta generica: faltam dados ou observacoes relevantes no paciente.",
            "Paciente nao aparece: confirme o cadastro e atualize a tela.",
        ],
        "related": ["Como editar uma dieta gerada", "Como usar avaliacao e historico"],
        "action_label": "Abrir Gerar Dieta",
        "action_route": "dieta",
    },
    "Como lancar no financeiro": {
        "category": "Financeiro",
        "summary": "Registrar receitas e despesas com categoria, status e paciente vinculado quando necessario.",
        "steps": [
            "Abra `Financeiro`.",
            "Use o formulario de novo lancamento.",
            "Informe tipo, categoria, valor, data e status.",
            "Se fizer sentido, vincule um paciente e salve o lancamento.",
        ],
        "tips": [
            "Manter categorias consistentes melhora os indicadores e graficos.",
            "Use status pendente para nao perder recebimentos futuros.",
        ],
        "errors": [
            "Saldo estranho: reveja status, tipo e duplicidade de lancamentos.",
            "Paciente nao aparece: o cadastro precisa existir antes no sistema.",
        ],
        "related": ["Como interpretar o resumo financeiro", "Agendar atendimento na Agenda"],
        "action_label": "Abrir Financeiro",
        "action_route": "financeiro",
    },
    "Como usar biblioteca e materiais": {
        "category": "Biblioteca",
        "summary": "Localizar conteudos, materiais de apoio e referencias internas do sistema.",
        "steps": [
            "Abra `Biblioteca` no menu lateral.",
            "Use busca ou filtros para localizar o material desejado.",
            "Abra o item e revise o conteudo antes de compartilhar ou reutilizar.",
            "Combine com dieta, prescricoes ou relatorios quando fizer sentido.",
        ],
        "tips": [
            "Padronizar termos de busca ajuda a encontrar os mesmos temas depois.",
            "Use a biblioteca como apoio, nao como substituto do contexto clinico.",
        ],
        "errors": [
            "Nada encontrado: tente termos mais curtos ou categoria diferente.",
            "Conteudo desatualizado: revise a origem antes de usar com o paciente.",
        ],
        "related": ["Como gerar dieta com dados do paciente", "Como gerar relatorios e graficos"],
        "action_label": "Abrir Biblioteca",
        "action_route": "biblioteca",
    },
    "Como configurar WhatsApp API": {
        "category": "WhatsApp/API",
        "summary": "Configurar token, instancia e validar a integracao para mensagens operacionais.",
        "steps": [
            "Abra `WhatsApp API`.",
            "Preencha token, instancia, base URL e demais campos exigidos.",
            "Salve e teste a conexao antes de enviar mensagens reais.",
            "Valide retorno ou historico para garantir que a API esta ativa.",
        ],
        "tips": [
            "Tokens invalidos ou expirados costumam ser a causa principal de falha.",
            "Guarde as credenciais fora do prontuario para nao misturar dados clinicos e tecnicos.",
        ],
        "errors": [
            "Erro de autenticacao: revise token, headers e URL base.",
            "API conecta mas nao envia: confira permissao da instancia e numero de destino.",
        ],
        "related": ["Agendar atendimento na Agenda", "Problemas comuns de acesso ou configuracao"],
        "action_label": "Abrir WhatsApp API",
        "action_route": "painel_usuario",
    },
    "Portal do Paciente: liberar acesso e orientar": {
        "category": "Portal do Paciente",
        "summary": "Gerar codigo, liberar acesso e enviar orientacoes para o paciente entrar no portal.",
        "steps": [
            "Abra `Atendimento` e selecione o paciente.",
            "No bloco `Portal do Paciente`, confira CPF e codigo do paciente.",
            "Copie as instrucoes completas ou envie por WhatsApp.",
            "O paciente entra com CPF + codigo, cria a senha e depois acessa com CPF + senha.",
        ],
        "tips": [
            "CPF valido e sem duplicidade e obrigatorio para vinculo do portal.",
            "Se o paciente nao recebeu, use `Reenviar instrucoes` no mesmo card.",
        ],
        "errors": [
            "CPF aparece em mais de uma base: admin precisa revisar o vinculo.",
            "Codigo invalido: regenere o codigo e envie novamente.",
        ],
        "related": ["Atendimento: cadastro e acesso do paciente", "Instalar o app (PWA) no celular ou computador"],
        "action_label": "Abrir Atendimento",
        "action_route": "atendimento",
    },
    "Instalar o app (PWA) no celular ou computador": {
        "category": "App/PWA",
        "summary": "Instalar o DietHealth como app com icone no celular/desktop usando o navegador.",
        "steps": [
            "Abra o DietHealth no navegador (Chrome/Edge).",
            "Na pagina inicial, clique em `Instalar app`.",
            "Se aparecer instrucoes: iPhone -> Compartilhar > Adicionar a Tela de Inicio; Android/Chrome -> menu ⋮ > Instalar app.",
            "Depois abra o icone instalado e faca login normalmente.",
        ],
        "tips": [
            "Use HTTPS e navegador atualizado para liberar a instalacao.",
            "Se ja estiver instalado, o botao pode sumir automaticamente.",
        ],
        "errors": [
            "Botao aparece mas nao instala: use a opcao do menu do navegador.",
            "Icone nao aparece: limpe cache/dados do site e tente novamente.",
        ],
        "related": ["Problemas comuns de acesso ou configuracao", "Portal do Paciente: liberar acesso e orientar"],
        "action_label": "Voltar para a pagina inicial",
        "action_route": None,
    },
    "Recursos Premium (cadeado) e pagamento": {
        "category": "Assinatura e pagamento",
        "summary": "Liberar recursos Premium ao gerar link de pagamento e concluir a assinatura.",
        "steps": [
            "Clique no botao com cadeado.",
            "O sistema abre `Pagamento Premium`.",
            "Clique em `Gerar link de pagamento` e depois em `PAGAR AGORA (Pix/Cartao)`.",
            "Apos o pagamento, atualize a pagina e tente novamente.",
        ],
        "tips": [
            "O link e gerado por usuario; se mudar de conta, gere novamente.",
            "A liberacao pode levar alguns minutos apos o pagamento.",
        ],
        "errors": [
            "Token Mercado Pago ausente: admin precisa configurar `MERCADO_PAGO_ACCESS_TOKEN`.",
            "Pagamento concluido mas acesso bloqueado: abra chamado com usuario e data.",
        ],
        "related": ["Problemas comuns de acesso ou configuracao", "Como exportar backup e restaurar"],
        "action_label": "Abrir chamado tecnico",
        "action_route": None,
    },
    "Problemas comuns de acesso ou configuracao": {
        "category": "Acesso e cadastro",
        "summary": "Diagnosticar travamentos de login, permissao, cadastro incompleto e configuracoes basicas.",
        "steps": [
            "Confirme usuario, senha e status da conta.",
            "Revise se o perfil esta ativo e sem bloqueio financeiro.",
            "Teste atualizar a pagina e refazer o login.",
            "Se persistir, abra chamado com a mensagem exata do erro.",
        ],
        "tips": [
            "Erros com texto claro ajudam muito no atendimento tecnico.",
            "Quando houver mudanca de ambiente, faca novo login e limpe cache do navegador.",
        ],
        "errors": [
            "Tela em branco: pode ser cache antigo ou erro de deploy.",
            "Acesso negado: perfil sem permissao ou conta bloqueada.",
        ],
        "related": ["Como configurar WhatsApp API", "Como exportar backup e restaurar"],
        "action_label": "Abrir chamado tecnico",
        "action_route": None,
    },
    "Como exportar backup e restaurar": {
        "category": "Configuracoes",
        "summary": "Gerar backup do sistema e restaurar dados com cuidado para nao sobrescrever informacoes erradas.",
        "steps": [
            "Abra `Admin` e localize a area de backup.",
            "Gere o arquivo de backup e salve em local seguro.",
            "Para restaurar, envie o arquivo correto e confirme a operacao.",
            "Depois valide pacientes, agenda e financeiro para garantir integridade.",
        ],
        "tips": [
            "Sempre mantenha pelo menos uma copia externa do backup.",
            "Nao restaure sem validar a origem do arquivo.",
        ],
        "errors": [
            "Backup vazio: revise se havia dados salvos antes da exportacao.",
            "Restauracao parcial: pode indicar arquivo incompleto ou estrutura diferente.",
        ],
        "related": ["Problemas comuns de acesso ou configuracao", "Como gerar relatorios e graficos"],
        "action_label": "Abrir Admin",
        "action_route": "admin",
    },
}

SUPPORT_POPULAR_TOPICS = [
    "Atendimento: cadastro e acesso do paciente",
    "Agendar atendimento na Agenda",
    "Como gerar dieta com dados do paciente",
    "Como lancar no financeiro",
    "Recursos Premium (cadeado) e pagamento",
    "Instalar o app (PWA) no celular ou computador",
    "Como configurar WhatsApp API",
    "Problemas comuns de acesso ou configuracao",
]


def _support_open_route(route: Optional[str]):
    if not route:
        return
    if route == "admin":
        st.session_state["dh_selected_menu"] = "admin"
        _qp_set(SIDEBAR_MENU_QUERY_KEY, "admin")
        st.rerun()
    for item in SIDEBAR_MENU_ITEMS:
        if item.get("route") == route:
            st.session_state["dh_selected_menu"] = item.get("key")
            _qp_set(SIDEBAR_MENU_QUERY_KEY, item.get("key"))
            st.rerun()


def _inject_support_styles():
    st.markdown(
        """
        <style>
        .dh-support-hero{display:grid;grid-template-columns:minmax(0,2.1fr) minmax(260px,1fr);gap:18px;padding:22px 24px;border-radius:22px;border:1px solid rgba(82,224,180,0.14);background:linear-gradient(135deg, rgba(13,24,42,0.98), rgba(15,31,53,0.94));box-shadow:0 24px 48px rgba(0,0,0,0.26);margin-bottom:20px;}
        .dh-support-hero h2{margin:0;color:#f8fbff;font-size:2rem;font-weight:800;letter-spacing:-0.02em;}
        .dh-support-hero p{margin:8px 0 0;color:#b2c5db;line-height:1.55;font-size:0.98rem;}
        .dh-support-pills{display:flex;flex-wrap:wrap;gap:10px;margin-top:16px;}
        .dh-support-pill{padding:8px 12px;border-radius:999px;border:1px solid rgba(87,223,179,0.18);background:rgba(17,34,58,0.88);color:#dffcf2;font-size:0.82rem;font-weight:700;}
        .dh-support-hero-side{display:grid;gap:12px;align-content:start;}
        .dh-support-mini-stat{padding:14px 16px;border-radius:18px;background:rgba(11,23,40,0.76);border:1px solid rgba(255,255,255,0.06);}
        .dh-support-mini-stat strong{display:block;color:#ffffff;font-size:1.15rem;margin-bottom:4px;}
        .dh-support-mini-stat span{color:#9eb5cf;font-size:0.88rem;}
        .dh-support-card{border-radius:20px;border:1px solid rgba(255,255,255,0.06);background:linear-gradient(180deg, rgba(15,26,46,0.96), rgba(11,19,35,0.96));padding:18px 18px 16px;box-shadow:0 20px 36px rgba(0,0,0,0.2);height:100%;}
        .dh-support-card h4{margin:0 0 10px;color:#f4f8ff;font-size:1.03rem;font-weight:800;}
        .dh-support-card p,.dh-support-card li{color:#b8c7d9;line-height:1.56;}
        .dh-support-topic-card{padding:14px 15px;border-radius:18px;border:1px solid rgba(255,255,255,0.06);background:rgba(14,26,44,0.92);min-height:132px;}
        .dh-support-topic-card b{color:#f8fbff;display:block;margin-bottom:6px;}
        .dh-support-topic-meta{color:#66e4b7;font-size:0.78rem;font-weight:700;margin-bottom:8px;text-transform:uppercase;letter-spacing:0.04em;}
        .dh-support-step{display:grid;grid-template-columns:42px minmax(0,1fr);gap:12px;align-items:start;padding:12px 0;border-top:1px solid rgba(255,255,255,0.05);}
        .dh-support-step:first-child{border-top:none;padding-top:4px;}
        .dh-support-step-num{width:38px;height:38px;border-radius:12px;display:flex;align-items:center;justify-content:center;background:linear-gradient(135deg, rgba(34,197,94,0.2), rgba(16,185,129,0.1));border:1px solid rgba(52,211,153,0.3);color:#dffcf2;font-weight:800;}
        .dh-support-step-body strong{display:block;color:#f4f8ff;margin-bottom:3px;}
        .dh-support-helpbox{border-radius:16px;background:rgba(10,21,37,0.85);border:1px solid rgba(255,255,255,0.05);padding:14px 15px;margin-top:10px;}
        .dh-support-bullet{display:flex;gap:9px;align-items:flex-start;margin-bottom:9px;color:#b8c7d9;}
        .dh-support-bullet span{color:#58d8ae;font-weight:800;}
        .dh-support-empty{border:1px dashed rgba(255,255,255,0.12);background:rgba(10,20,36,0.7);border-radius:18px;padding:18px;color:#a8bdd3;}
        @media (max-width:980px){.dh-support-hero{grid-template-columns:1fr;}}
        </style>
        """,
        unsafe_allow_html=True,
    )

def modulo_suporte():
    _inject_support_styles()
    support_categories = sorted({cfg["category"] for cfg in SUPPORT_TOPICS.values()})
    current_route = next(
        (
            item.get("route")
            for item in SIDEBAR_MENU_ITEMS
            if item.get("key") == st.session_state.get("dh_selected_menu")
        ),
        "",
    )
    suggested_topic = next(
        (name for name, cfg in SUPPORT_TOPICS.items() if cfg.get("action_route") == current_route),
        SUPPORT_POPULAR_TOPICS[0],
    )
    if "sup_selected_topic" not in st.session_state:
        st.session_state["sup_selected_topic"] = suggested_topic
    if "sup_search_text" not in st.session_state:
        st.session_state["sup_search_text"] = ""
    if "sup_category_filter" not in st.session_state:
        st.session_state["sup_category_filter"] = "Todas"

    st.markdown(
        f"""
        <div class="dh-support-hero">
            <div>
                <h2>Central inteligente de suporte</h2>
                <p>Tire duvidas operacionais, encontre fluxos do sistema com rapidez e use a IA do DietHealth para recuperar contexto sem precisar cacar instrucoes em telas diferentes.</p>
                <div class="dh-support-pills">
                    <div class="dh-support-pill">Topico sugerido: {suggested_topic}</div>
                    <div class="dh-support-pill">Busca orientada por modulo</div>
                    <div class="dh-support-pill">Passo a passo + erros comuns + acao rapida</div>
                </div>
            </div>
            <div class="dh-support-hero-side">
                <div class="dh-support-mini-stat"><strong>{len(SUPPORT_TOPICS)}</strong><span>fluxos guiados disponiveis</span></div>
                <div class="dh-support-mini-stat"><strong>{len(support_tickets)}</strong><span>chamados registrados no sistema</span></div>
                <div class="dh-support-mini-stat"><strong>{len(feedbacks)}</strong><span>feedbacks acumulados para melhoria</span></div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    tab_help, tab_ia, tab_chamado, tab_feedback = st.tabs(
        ["Central de ajuda", "Super Health IA", "Abrir chamado", "Feedback"]
    )

    with tab_help:
        st.markdown("### Como posso te ajudar?")
        filters_col1, filters_col2 = st.columns([1.4, 1])
        search_text = filters_col1.text_input(
            "Buscar por duvida, modulo ou acao",
            value=st.session_state.get("sup_search_text", ""),
            placeholder="Ex: cadastro de paciente, financeiro, WhatsApp...",
            key="sup_search_box",
        )
        st.session_state["sup_search_text"] = search_text
        selected_category = filters_col2.selectbox(
            "Categoria",
            ["Todas"] + support_categories,
            index=(["Todas"] + support_categories).index(st.session_state.get("sup_category_filter", "Todas")),
            key="sup_category_box",
        )
        st.session_state["sup_category_filter"] = selected_category

        search_terms = (search_text or "").strip().lower()
        filtered_topic_names = []
        for topic_name, cfg in SUPPORT_TOPICS.items():
            haystack = " ".join(
                [
                    topic_name,
                    cfg.get("category", ""),
                    cfg.get("summary", ""),
                    " ".join(cfg.get("steps", [])),
                    " ".join(cfg.get("tips", [])),
                    " ".join(cfg.get("errors", [])),
                ]
            ).lower()
            if selected_category != "Todas" and cfg.get("category") != selected_category:
                continue
            if search_terms and search_terms not in haystack:
                continue
            filtered_topic_names.append(topic_name)

        if not filtered_topic_names:
            st.markdown(
                '<div class="dh-support-empty">Nenhum topico encontrado com esse filtro. Tente buscar por termos mais curtos ou escolher outra categoria.</div>',
                unsafe_allow_html=True,
            )
            filtered_topic_names = [suggested_topic]

        if st.session_state.get("sup_selected_topic") not in filtered_topic_names:
            st.session_state["sup_selected_topic"] = filtered_topic_names[0]

        st.markdown("#### Temas mais acessados")
        topic_grid_cols = st.columns(3)
        for idx, topic_name in enumerate(SUPPORT_POPULAR_TOPICS):
            cfg = SUPPORT_TOPICS[topic_name]
            with topic_grid_cols[idx % 3]:
                st.markdown(
                    f'<div class="dh-support-topic-card"><div class="dh-support-topic-meta">{cfg["category"]}</div><b>{topic_name}</b><div style="color:#b8c7d9; line-height:1.45;">{cfg["summary"]}</div></div>',
                    unsafe_allow_html=True,
                )
                if st.button("Abrir topico", key=f"sup_pop_{idx}", use_container_width=True):
                    st.session_state["sup_selected_topic"] = topic_name
                    st.rerun()

        selected_topic = st.selectbox(
            "Assunto principal",
            filtered_topic_names,
            index=filtered_topic_names.index(st.session_state.get("sup_selected_topic")),
            key="sup_topic_select",
        )
        st.session_state["sup_selected_topic"] = selected_topic
        topic_cfg = SUPPORT_TOPICS[selected_topic]

        left_col, right_col = st.columns([1.5, 1], gap="large")

        with left_col:
            st.markdown(
                f'<div class="dh-support-card"><h4>{selected_topic}</h4><p>{topic_cfg["summary"]}</p></div>',
                unsafe_allow_html=True,
            )
            st.write("")
            st.markdown('<div class="dh-support-card"><h4>Passo a passo visual</h4>', unsafe_allow_html=True)
            for idx, step in enumerate(topic_cfg.get("steps", []), start=1):
                st.markdown(
                    f'<div class="dh-support-step"><div class="dh-support-step-num">{idx}</div><div class="dh-support-step-body"><strong>Etapa {idx}</strong><div>{step}</div></div></div>',
                    unsafe_allow_html=True,
                )
            st.markdown("</div>", unsafe_allow_html=True)

            st.write("")
            st.markdown('<div class="dh-support-card"><h4>Perguntas relacionadas</h4></div>', unsafe_allow_html=True)
            rel_cols = st.columns(2)
            for idx, related_topic in enumerate(topic_cfg.get("related", [])):
                with rel_cols[idx % 2]:
                    if st.button(related_topic, key=f"sup_rel_{selected_topic}_{idx}", use_container_width=True):
                        st.session_state["sup_selected_topic"] = related_topic
                        st.rerun()

        with right_col:
            st.markdown('<div class="dh-support-card"><h4>Dicas rapidas</h4></div>', unsafe_allow_html=True)
            for tip in topic_cfg.get("tips", []):
                st.markdown(
                    f'<div class="dh-support-helpbox"><div class="dh-support-bullet"><span>•</span><div>{tip}</div></div></div>',
                    unsafe_allow_html=True,
                )

            st.write("")
            st.markdown('<div class="dh-support-card"><h4>Erros comuns</h4></div>', unsafe_allow_html=True)
            for err in topic_cfg.get("errors", []):
                st.markdown(
                    f'<div class="dh-support-helpbox"><div class="dh-support-bullet"><span>!</span><div>{err}</div></div></div>',
                    unsafe_allow_html=True,
                )

            st.write("")
            st.markdown(
                '<div class="dh-support-card"><h4>Acoes rapidas</h4><p>Va direto para a area relacionada ou continue o fluxo com o assistente.</p></div>',
                unsafe_allow_html=True,
            )
            if topic_cfg.get("action_route"):
                if st.button(topic_cfg.get("action_label", "Abrir area"), key=f"sup_action_{selected_topic}", use_container_width=True):
                    _support_open_route(topic_cfg.get("action_route"))
            if st.button("Perguntar para a IA sobre este topico", key=f"sup_to_ai_{selected_topic}", use_container_width=True):
                st.session_state["support_messages"] = [
                    {"role": "user", "content": f"Explique com detalhes: {selected_topic}"}
                ]
                st.rerun()
            st.info("Ainda precisa de ajuda? Use a aba `Super Health IA` para diagnosticar sua situacao com mais contexto.")

    with tab_ia:
        st.markdown(
            '<div class="dh-pill-soft">Assistente limitado ao uso do DietHealth, com foco em duvidas operacionais do sistema.</div>',
            unsafe_allow_html=True,
        )
        st.write("")

        if "support_messages" not in st.session_state:
            st.session_state["support_messages"] = []

        shortcut_col1, shortcut_col2 = st.columns([1.2, 0.8])
        shortcut = shortcut_col1.selectbox(
            "Atalhos de suporte",
            [
                "Como cadastrar um paciente do zero?",
                "Como agendar um atendimento na Agenda?",
                "Como gerar um cardapio no Diet Generator?",
                "Como lancar receita ou despesa no Financeiro?",
                "Como configurar o WhatsApp API?",
                "Meu acesso esta bloqueado. Como resolver?",
            ],
            key="sup_atalho",
        )
        if shortcut_col2.button("Enviar atalho", key="sup_send_atalho", use_container_width=True):
            st.session_state["support_messages"].append({"role": "user", "content": shortcut})

        if not ia_ok():
            st.error("Configure a GROQ_API_KEY nas variaveis de ambiente para usar a IA do suporte.")

        for m in st.session_state["support_messages"][-40:]:
            role = "assistant" if m.get("role") == "assistant" else "user"
            with st.chat_message(role):
                st.markdown(m.get("content", ""))

        def _support_send(user_text: str):
            if not user_text:
                return
            st.session_state["support_messages"].append({"role": "user", "content": user_text})

            if not ia_ok():
                resposta = "Erro IA: GROQ_API_KEY nao configurada. Ajuste a variavel de ambiente e reinicie o servico."
            else:
                msgs_api = [{"role": "system", "content": _support_system_prompt()}]
                msgs_api.extend(st.session_state["support_messages"][-20:])
                with st.spinner("Pensando..."):
                    try:
                        client = get_groq_client()
                        if client is None:
                            resposta = "Erro IA: GROQ_API_KEY nao encontrada. Configure no ambiente e reinicie o servico."
                        else:
                            res = client.chat.completions.create(
                                messages=msgs_api,
                                model=os.getenv("model", "llama-3.3-70b-versatile"),
                                temperature=0.2,
                                max_tokens=900,
                            )
                            resposta = res.choices[0].message.content
                    except Exception as e:
                        if "invalid_api_key" in str(e).lower() or "invalid api key" in str(e).lower():
                            resposta = "Erro IA: chave invalida. Confirme GROQ_API_KEY e reinicie o servico."
                        else:
                            resposta = f"Erro IA: {e}"

            resposta = _fix_pt_br_text(resposta)
            st.session_state["support_messages"].append({"role": "assistant", "content": resposta})

        user_text = st.chat_input("Descreva sua duvida operacional no DietHealth")
        if user_text:
            _support_send(user_text)
            st.rerun()

        if st.button("Limpar conversa", key="sup_clear"):
            st.session_state["support_messages"] = []
            st.rerun()

    with tab_chamado:
        st.markdown("### Abrir chamado tecnico")
        st.caption("Registre um problema com contexto suficiente para acelerar o atendimento.")

        with st.form("support_ticket_form"):
            assunto = st.text_input("Assunto", placeholder="Ex: Erro ao gerar PDF")
            categoria = st.selectbox("Categoria", ["Duvida", "Erro/Bug", "Sugestao"], index=0)
            prioridade = st.selectbox("Prioridade", ["Baixa", "Media", "Alta"], index=1)
            msg = st.text_area("Descreva o problema", placeholder="O que aconteceu, em qual tela e qual foi a mensagem exibida?")
            if st.form_submit_button("Enviar chamado"):
                tid = uuid.uuid4().hex
                support_tickets.append({
                    "id": tid,
                    "dono": (st.session_state.get("usuario") or "").strip().lower(),
                    "tipo": (st.session_state.get("tipo") or "user"),
                    "assunto": assunto,
                    "categoria": categoria,
                    "prioridade": prioridade,
                    "mensagem": msg,
                    "status": "aberto",
                    "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                })
                save_db("support_tickets.json", support_tickets)
                st.success(f"Chamado enviado com sucesso. ID: {tid}")

        st.divider()
        st.markdown("### Meus chamados")
        meus = filtrar_por_usuario(support_tickets)
        if meus:
            render_table(meus)
        else:
            st.info("Voce ainda nao abriu chamados.")

        if st.session_state.get("tipo") == "admin":
            st.divider()
            st.markdown("### Painel admin de chamados")
            if support_tickets:
                sel = st.selectbox("Chamado", [t.get("id") for t in support_tickets if t.get("id")], key="sup_admin_sel")
                t_obj = next((t for t in support_tickets if t.get("id") == sel), None)
                if t_obj:
                    admin_col1, admin_col2 = st.columns(2)
                    novo_status = admin_col1.selectbox(
                        "Status",
                        ["aberto", "em_andamento", "resolvido"],
                        index=["aberto", "em_andamento", "resolvido"].index(t_obj.get("status", "aberto")) if t_obj.get("status", "aberto") in ["aberto", "em_andamento", "resolvido"] else 0,
                        key="sup_admin_status",
                    )
                    nova_prioridade = admin_col2.selectbox(
                        "Prioridade",
                        ["Baixa", "Media", "Alta"],
                        index=["Baixa", "Media", "Alta"].index(t_obj.get("prioridade", "Media")) if t_obj.get("prioridade", "Media") in ["Baixa", "Media", "Alta"] else 1,
                        key="sup_admin_priority",
                    )
                    if st.button("Atualizar chamado", key="sup_admin_update"):
                        t_obj["status"] = novo_status
                        t_obj["prioridade"] = nova_prioridade
                        t_obj["updated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        save_db("support_tickets.json", support_tickets)
                        st.success("Chamado atualizado.")

    with tab_feedback:
        st.markdown("### Feedback do suporte")
        st.caption("Use este espaco para apontar melhoria de UX, duvidas recorrentes e lacunas do produto.")

        with st.form("feedback_form"):
            nota = st.slider("Nota (1-5)", min_value=1, max_value=5, value=5)
            comentario = st.text_area("Comentario", placeholder="O que funcionou bem? O que ainda precisa melhorar?")
            if st.form_submit_button("Enviar feedback"):
                fid = uuid.uuid4().hex
                feedbacks.append({
                    "id": fid,
                    "dono": (st.session_state.get("usuario") or "").strip().lower(),
                    "nota": int(nota),
                    "comentario": comentario,
                    "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                })
                save_db("feedbacks.json", feedbacks)
                st.success("Feedback enviado. Obrigado.")

        if st.session_state.get("tipo") == "admin" and feedbacks:
            st.divider()
            st.markdown("### Feedbacks recebidos")
            render_table(feedbacks)

def modulo_painel_usuario():
    st.title("👤 Painel do Usuário")
    st.markdown(
        '<div class="dh-pill-soft">Configurações privadas da conta e integração WhatsApp (W-API ou Cloud API).</div>',
        unsafe_allow_html=True
    )

    user_obj = _get_user_obj()
    if user_obj is None:
        st.error("Usuário não encontrado na sessão.")
        return

    st.markdown("### WhatsApp API")
    st.caption("Esta área só aparece para usuário logado. Não fica exposta na tela inicial.")

    cfg_cur = _get_user_whatsapp_settings(user_obj)
    provider_cur = cfg_cur.get("provider") or "wapi"
    provider_label_cur = "W-API / Evolution" if provider_cur == "wapi" else "Meta Cloud API"
    is_admin_user = ((user_obj.get("tipo") or "").strip().lower() == "admin")
    wa_notify_admin_num_cur = (user_obj.get("wa_notify_admin_num") or "").strip()

    with st.form("wa_api_form_user_panel"):
        st.caption("Selecione o provedor que você realmente usa.")
        provider_label = st.selectbox(
            "Provedor",
            ["W-API / Evolution", "Meta Cloud API"],
            index=0 if provider_cur == "wapi" else 1,
        )
        provider = "wapi" if provider_label.startswith("W-API") else "cloud"

        if provider == "wapi":
            st.caption(
                "Aceita URL base (ex: https://api.w-api.app/v1) "
                "OU endpoint completo (ex: https://api.w-api.app/v1/message/send-text?instanceId=SEU_ID)."
            )
            wa_api_url = st.text_input("URL da API", value=(cfg_cur.get("api_url") or "").strip())
            wa_instance = st.text_input("Instância (opcional se já estiver no instanceId da URL)", value=(cfg_cur.get("instance") or "").strip())
            wa_token = st.text_input("API Key / Token", value=(cfg_cur.get("token") or "").strip(), type="password")
            wa_phone_id = (user_obj.get("wa_phone_id") or "").strip()
        else:
            st.caption("Meta Cloud API: Access Token + Phone Number ID.")
            wa_token = st.text_input("Access Token", value=(cfg_cur.get("token") or "").strip(), type="password")
            wa_phone_id = st.text_input("Phone Number ID", value=(cfg_cur.get("phone_id") or "").strip())
            wa_api_url = (user_obj.get("wa_api_url") or "").strip()
            wa_instance = (user_obj.get("wa_instance") or "").strip()

        if is_admin_user:
            st.caption("Notificação de novos cadastros (admin).")
            wa_notify_admin_num = st.text_input(
                "Número para receber notificação de cadastro (com DDI)",
                value=wa_notify_admin_num_cur,
            )
        else:
            wa_notify_admin_num = wa_notify_admin_num_cur

        if st.form_submit_button("Salvar API"):
            wa_notify_admin_num = (wa_notify_admin_num or "").strip()
            if is_admin_user and wa_notify_admin_num and not _is_valid_celular(wa_notify_admin_num):
                st.error("Número de notificação do admin inválido. Use celular com DDD (e DDI quando necessário).")
            else:
                user_obj["wa_provider"] = provider
                user_obj["wa_token"] = (wa_token or "").strip()
                user_obj["wa_phone_id"] = (wa_phone_id or "").strip()
                user_obj["wa_api_url"] = (wa_api_url or "").strip()
                user_obj["wa_instance"] = (wa_instance or "").strip()
                if is_admin_user:
                    user_obj["wa_notify_admin_num"] = wa_notify_admin_num
                save_db("users.json", users)
                st.success(f"Configuração salva ({provider_label}).")
                st.rerun()

    cfg_eff = _get_user_whatsapp_settings(user_obj)
    provider_eff = cfg_eff.get("provider") or "wapi"
    if provider_eff == "wapi":
        if cfg_eff.get("token") and cfg_eff.get("api_url") and cfg_eff.get("instance"):
            st.success("Credenciais W-API detectadas.")
        else:
            st.warning("Credenciais incompletas. Preencha URL da API, Instância e API Key.")
    else:
        if cfg_eff.get("token") and cfg_eff.get("phone_id"):
            st.success("Credenciais da Cloud API detectadas.")
        else:
            st.warning("Credenciais incompletas. Preencha Access Token e Phone Number ID.")

    phone_digits = _wa_sanitize_numero(cfg_eff.get("phone_id"))
    if provider_eff == "cloud" and phone_digits and len(phone_digits) <= 13:
        st.info("Atenção: esse valor parece número de telefone. Em Cloud API use o Phone Number ID.")

    if provider_eff == "wapi":
        st.caption(
            "Rota usada automaticamente: "
            "/v1/message/send-text?instanceId=... (W-API) ou /message/sendText/{instancia} (Evolution)."
        )
    else:
        st.caption("Rota de envio usada: Graph API /{phone_number_id}/messages.")

    if is_admin_user:
        admin_notify_num = _resolve_admin_whatsapp_num(user_obj)
        if admin_notify_num:
            st.caption(f"Destino atual de notificação de novos cadastros: {admin_notify_num}")
        else:
            st.warning("Defina o número de notificação do admin para receber aviso de novos cadastros.")

    st.markdown("### Teste de envio")
    tel_default = (user_obj.get("telefone") or "").strip()
    msg_default = (
        f"Teste WhatsApp ({provider_eff.upper()}) via DietHealth.\n"
        f"Usuário: {(user_obj.get('usuario') or '').strip().lower()}\n"
        f"Data/Hora: {_now_local().strftime('%d/%m/%Y %H:%M:%S')}"
    )
    with st.form("wa_api_test_form_user_panel"):
        wa_test_num = st.text_input("Número destino (com DDI, ex: 5511999999999)", value=tel_default)
        wa_test_msg = st.text_area("Mensagem de teste", value=msg_default, height=130)
        if st.form_submit_button("Enviar teste"):
            if not _is_valid_celular(wa_test_num):
                st.error("Número destino inválido. Informe celular com DDD (e DDI para envio internacional).")
            elif provider_eff == "wapi" and not (cfg_eff.get("token") and cfg_eff.get("api_url") and cfg_eff.get("instance")):
                st.warning("Integração WhatsApp ainda não configurada. Preencha URL da API, instância e API key antes do teste.")
            elif provider_eff == "cloud" and not (cfg_eff.get("token") and cfg_eff.get("phone_id")):
                st.warning("Integração WhatsApp Cloud ainda não configurada. Preencha Access Token e Phone Number ID antes do teste.")
            else:
                ok, err = _wa_send_text_for_user(user_obj, wa_test_num, wa_test_msg)
                if ok:
                    st.success("Mensagem enviada com sucesso.")
                else:
                    st.error(f"Falha no envio: {err}")
                    if provider_eff == "wapi":
                        st.caption("Dica: valide URL, instância e API key da W-API/Evolution.")
                    else:
                        st.caption("Dica: confirme o Phone Number ID e se o destinatário está permitido no ambiente da Meta.")

def _build_paciente_context(p_obj: dict) -> str:
    if not p_obj:
        return ""
    ult = get_ultimos_dados(p_obj) or {}
    anamnese = get_anamnese_paciente(p_obj)
    linhas = [
        "CONTEXTO DO PACIENTE (use como referência):",
        f"Nome: {p_obj.get('nome') or '—'}",
        f"Sexo: {ult.get('sexo') or p_obj.get('sexo') or '—'}",
        f"Idade: {ult.get('idade') or p_obj.get('idade') or '—'}",
        f"Peso: {ult.get('peso') or '—'}",
        f"Altura: {ult.get('altura') or '—'}",
        f"IMC: {ult.get('imc') or '—'}",
        f"Última avaliação: {ult.get('data') or '—'}",
    ]
    obs = ult.get("observacoes") or ""
    if obs:
        linhas.append(f"Observações: {obs}")
    anamnese_ctx = _anamnese_lines(anamnese)
    if anamnese_ctx:
        linhas.append("Anamnese clínica:")
        linhas.extend(anamnese_ctx)
    return "\n".join(linhas)

def _format_chat_transcript(msgs: list) -> str:
    linhas = []
    for m in msgs:
        role = m.get("role")
        if role == "system":
            continue
        nome = "Usuário" if role == "user" else "Super Health IA"
        linhas.append(f"{nome}: {m.get('content','')}")
    return "\n\n".join(linhas)

def modulo_chatbot_ia():
    st.title("🤖 Super Health IA (Groq)")
    st.markdown(
        '<div class="dh-pill-soft">Assistente inteligente para suporte, clínica e marketing. '
        'Use com cautela em orientações sensíveis.</div>',
        unsafe_allow_html=True
    )
    st.write("")

    if not ia_ok():
        st.error("Configure a GROQ_API_KEY (Secrets ou variável de ambiente).")
        return

    if "ia_messages" not in st.session_state:
        st.session_state["ia_messages"] = []

    c1, c2, c3 = st.columns([1.2, 1, 1])
    modo = c1.selectbox("Modo", ["Nutrição", "Suporte", "Marketing", "Personalizado"], index=0)
    temperatura = c2.slider("Criatividade", min_value=0.0, max_value=1.0, value=0.4, step=0.05)
    max_tokens = c3.number_input("Máx tokens", min_value=256, max_value=4096, value=900, step=64)

    custom_prompt = ""
    if modo == "Personalizado":
        custom_prompt = st.text_area("Instruções personalizadas", placeholder="Defina o papel e limites do chatbot.")

    meus_pacientes = filtrar_por_usuario(pacientes)
    usar_paciente = st.checkbox("Usar contexto de paciente", value=False)
    p_obj = None
    if usar_paciente:
        if not meus_pacientes:
            st.warning("Sem pacientes cadastrados.")
        else:
            p_sel = st.selectbox("Paciente", [p["nome"] for p in meus_pacientes], key="ia_paciente_sel")
            p_obj = get_paciente_obj(p_sel)

    st.markdown("### Conversa")
    for m in st.session_state["ia_messages"]:
        role = "assistant" if m.get("role") == "assistant" else "user"
        with st.chat_message(role):
            st.markdown(m.get("content", ""))

    def _send_to_ia(user_text: str):
        if not user_text:
            return
        st.session_state["ia_messages"].append({"role": "user", "content": user_text})

        system_prompt = _build_ia_system_prompt(
            "nutricao" if modo == "Nutrição" else modo.lower(),
            custom_prompt
        )
        msgs_api = [{"role": "system", "content": system_prompt}]

        patient_ctx = ""
        if usar_paciente and p_obj:
            patient_ctx = _build_paciente_context(p_obj)
            if patient_ctx:
                msgs_api.append({"role": "system", "content": patient_ctx})

        if modo == "Nutrição":
            assistant_clinical_block = _clinical_ai_prompt("assistant", user_text, patient_ctx)
            if assistant_clinical_block:
                msgs_api.append({"role": "system", "content": assistant_clinical_block})

        # Limita histórico para evitar excesso
        historico = st.session_state["ia_messages"][-20:]
        msgs_api.extend(historico)

        with st.spinner("Pensando..."):
            try:
                client = get_groq_client()
                if client is None:
                    resposta = "Erro IA: GROQ_API_KEY não encontrada. Configure no Railway e reinicie o serviço."
                else:
                    res = client.chat.completions.create(
                        messages=msgs_api,
                        model=os.getenv("model", "llama-3.3-70b-versatile"),
                        temperature=temperatura,
                        max_tokens=int(max_tokens),
                    )
                    resposta = res.choices[0].message.content
            except Exception as e:
                if "invalid_api_key" in str(e).lower() or "invalid api key" in str(e).lower():
                    resposta = "Erro IA: chave inválida. Confirme GROQ_API_KEY no Railway (sem espaços/quebras de linha) e reinicie o serviço."
                else:
                    resposta = f"Erro IA: {e}"

        resposta = _fix_pt_br_text(resposta)
        st.session_state["ia_messages"].append({"role": "assistant", "content": resposta})

    col_a, col_b, col_c = st.columns([1, 1, 2])
    if col_a.button("Limpar conversa"):
        st.session_state["ia_messages"] = []
        st.rerun()

    if col_b.button("Salvar conversa"):
        chat_entry = {
            "user": st.session_state.get("usuario"),
            "data": str(datetime.now()),
            "mensagens": st.session_state["ia_messages"]
        }
        chatbot_ia_log.append(chat_entry)
        save_db("chatbot_ia.json", chatbot_ia_log)
        st.success("Conversa salva no histórico.")

    if col_c.button("Salvar no prontuário"):
        if not p_obj:
            st.warning("Selecione um paciente para salvar no prontuário.")
        else:
            transcript = _format_chat_transcript(st.session_state["ia_messages"])
            p_obj.setdefault("historico", []).append({
                "tipo": "chatbot_ia",
                "data": datetime.now().strftime("%d/%m/%Y %H:%M"),
                "observacoes": transcript
            })
            save_db("pacientes.json", pacientes)
            st.success("Conversa salva no histórico do paciente.")

    st.markdown("### Atalhos rápidos")
    atalho = st.selectbox(
        "Escolha um pedido",
        [
            "Resuma a conversa em 5 tópicos",
            "Sugira próximos passos práticos",
            "Crie uma resposta curta para WhatsApp",
            "Gere uma mensagem de cobrança amigável",
            "Crie um texto de venda do DietHealth (curto)"
        ],
        index=0
    )
    if st.button("Enviar atalho"):
        _send_to_ia(atalho)
        st.rerun()

    user_text = st.chat_input("Digite sua mensagem")
    if user_text:
        _send_to_ia(user_text)
        st.rerun()

def modulo_graficos():
    st.markdown(
        """
        <style>
        .dh-chart-hero{display:grid;grid-template-columns:minmax(0,2.15fr) minmax(280px,1fr);gap:18px;padding:24px;border-radius:24px;border:1px solid rgba(82,224,180,0.14);background:linear-gradient(135deg, rgba(10,20,37,0.98), rgba(16,33,58,0.94));box-shadow:0 24px 48px rgba(0,0,0,0.28);margin-bottom:18px;}
        .dh-chart-hero h2{margin:0;color:#f7fbff;font-size:2.05rem;font-weight:800;letter-spacing:-0.03em;}
        .dh-chart-hero p{margin:10px 0 0;color:#b8c9dc;line-height:1.6;max-width:760px;}
        .dh-chart-pill-row{display:flex;flex-wrap:wrap;gap:10px;margin-top:18px;}
        .dh-chart-pill{padding:8px 12px;border-radius:999px;border:1px solid rgba(87,223,179,0.18);background:rgba(17,34,58,0.88);color:#dffcf2;font-size:.82rem;font-weight:700;}
        .dh-chart-kpis{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px;}
        .dh-chart-kpi{padding:15px 16px;border-radius:18px;background:rgba(10,20,36,0.82);border:1px solid rgba(255,255,255,0.06);min-height:96px;}
        .dh-chart-kpi strong{display:block;color:#ffffff;font-size:1.22rem;margin-bottom:4px;}
        .dh-chart-kpi span{display:block;color:#9ab2ca;font-size:.86rem;line-height:1.45;}
        .dh-chart-panel{border-radius:22px;padding:18px;background:linear-gradient(180deg, rgba(15,26,46,0.97), rgba(11,19,35,0.97));border:1px solid rgba(255,255,255,0.06);box-shadow:0 20px 36px rgba(0,0,0,.2);}
        .dh-chart-panel h4{margin:0 0 10px;color:#f4f8ff;font-size:1.04rem;font-weight:800;}
        .dh-chart-panel p{margin:0;color:#b8c8d8;line-height:1.58;}
        .dh-chart-mini{padding:14px;border-radius:18px;background:rgba(11,23,40,.76);border:1px solid rgba(255,255,255,.06);height:100%;}
        .dh-chart-mini strong{display:block;color:#f7fbff;margin-bottom:6px;font-size:.98rem;}
        .dh-chart-mini span{display:block;color:#9eb5cc;font-size:.88rem;line-height:1.48;}
        .dh-chart-empty{border:1px dashed rgba(255,255,255,.12);background:rgba(10,20,36,.7);border-radius:18px;padding:18px;color:#a8bdd3;}
        @media (max-width:980px){.dh-chart-hero{grid-template-columns:1fr;}.dh-chart-kpis{grid-template-columns:1fr 1fr;}}
        @media (max-width:760px){.dh-chart-kpis{grid-template-columns:1fr;}}
        </style>
        """,
        unsafe_allow_html=True,
    )

    meus_pacientes = filtrar_por_usuario(pacientes)
    if not meus_pacientes:
        st.warning("Sem pacientes.")
        return

    p_nome = st.selectbox("Paciente", [x["nome"] for x in meus_pacientes], key="g_sel")
    obj = next((x for x in meus_pacientes if x.get("nome") == p_nome), None)
    historico = list((obj or {}).get("historico") or [])

    registros = []
    for idx, item in enumerate(historico):
        reg = item or {}
        dados = reg.get("dados_vitais") if isinstance(reg.get("dados_vitais"), dict) else reg
        data_ref = _finance_parse_date(reg.get("data") or dados.get("data") or "")
        peso = _as_float_safe(dados.get("peso"))
        altura = _as_float_safe(dados.get("altura"))
        if altura in (None, 0):
            altura = _as_float_safe(dados.get("altura_m"))
        if altura in (None, 0):
            altura_cm = _as_float_safe(dados.get("altura_cm"))
            altura = (altura_cm / 100.0) if altura_cm else None
        imc = _as_float_safe(dados.get("imc"))
        if imc in (None, 0) and peso and altura and altura > 0:
            imc = calc_imc_kg_m(peso, altura)
        gordura = _as_float_safe(dados.get("gordura_calc"))
        if gordura in (None, 0):
            gordura = _as_float_safe(dados.get("bio_gord"))
        cintura = _as_float_safe(dados.get("cintura"))
        massa_magra = _as_float_safe(dados.get("massa_magra"))
        massa_gorda = _as_float_safe(dados.get("massa_gorda"))
        registros.append({
            "Ordem": idx,
            "Data": data_ref,
            "Peso": peso,
            "IMC": imc,
            "% Gordura": gordura,
            "Cintura": cintura,
            "Massa magra": massa_magra,
            "Massa gorda": massa_gorda,
            "Observacao": reg.get("observacoes") or dados.get("observacoes") or "",
        })

    df = pd.DataFrame(registros)
    if not df.empty:
        df = df.sort_values(["Data", "Ordem"]).reset_index(drop=True)
        df["DataLabel"] = df["Data"].map(lambda d: d.strftime("%d/%m/%Y"))

    ultimo_peso = float(df["Peso"].dropna().iloc[-1]) if not df.empty and df["Peso"].dropna().any() else 0.0
    primeiro_peso = float(df["Peso"].dropna().iloc[0]) if not df.empty and df["Peso"].dropna().any() else 0.0
    delta_peso = ultimo_peso - primeiro_peso if ultimo_peso and primeiro_peso else 0.0
    ultimo_imc = float(df["IMC"].dropna().iloc[-1]) if not df.empty and df["IMC"].dropna().any() else 0.0
    ultimo_gord = float(df["% Gordura"].dropna().iloc[-1]) if not df.empty and df["% Gordura"].dropna().any() else 0.0
    ultima_data = df["DataLabel"].iloc[-1] if not df.empty else "--/--/----"

    st.markdown(
        f"""
        <div class="dh-chart-hero">
          <div>
            <h2>Evolucao clinica</h2>
            <p>Acompanhe peso, IMC, gordura corporal e outros indicadores do prontuario em uma visao mais clara para consultas de retorno e tomada de decisao.</p>
            <div class="dh-chart-pill-row">
              <div class="dh-chart-pill">Paciente: {p_nome}</div>
              <div class="dh-chart-pill">{len(historico)} registro(s) no historico</div>
              <div class="dh-chart-pill">Ultima atualizacao: {ultima_data}</div>
            </div>
          </div>
          <div class="dh-chart-kpis">
            <div class="dh-chart-kpi"><strong>{ultimo_peso:.1f} kg</strong><span>peso mais recente registrado</span></div>
            <div class="dh-chart-kpi"><strong>{delta_peso:+.1f} kg</strong><span>variacao entre primeiro e ultimo peso salvo</span></div>
            <div class="dh-chart-kpi"><strong>{ultimo_imc:.1f}</strong><span>IMC atual considerando o ultimo registro valido</span></div>
            <div class="dh-chart-kpi"><strong>{ultimo_gord:.1f}%</strong><span>percentual de gordura mais recente encontrado</span></div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if df.empty or not any(df[col].dropna().any() for col in ["Peso", "IMC", "% Gordura", "Cintura", "Massa magra", "Massa gorda"] if col in df.columns):
        st.markdown('<div class="dh-chart-empty">Sem dados suficientes no historico do paciente. Salve avaliacoes no prontuario para liberar a evolucao automatica nesta tela.</div>', unsafe_allow_html=True)
        return

    filter_col1, filter_col2 = st.columns([1.2, 1])
    periodo = filter_col1.selectbox("Periodo", ["Tudo", "Ultimos 30 dias", "Ultimos 90 dias", "Ultimos 180 dias"], key="grafico_periodo")
    indicador_principal = filter_col2.selectbox("Indicador principal", ["Peso", "IMC", "% Gordura", "Cintura", "Massa magra", "Massa gorda"], key="grafico_indicador")

    df_filtrado = df.copy()
    if periodo != "Tudo":
        dias = {"Ultimos 30 dias": 30, "Ultimos 90 dias": 90, "Ultimos 180 dias": 180}[periodo]
        limite = datetime.now().date() - timedelta(days=dias)
        df_filtrado = df_filtrado[df_filtrado["Data"] >= limite]

    resumo_col1, resumo_col2, resumo_col3 = st.columns(3)
    resumo_col1.markdown(f'<div class="dh-chart-mini"><strong>Registros visiveis</strong><span>{len(df_filtrado)} linha(s) no periodo selecionado.</span></div>', unsafe_allow_html=True)
    resumo_col2.markdown(f'<div class="dh-chart-mini"><strong>Indicador principal</strong><span>{indicador_principal} em foco para a leitura atual do retorno.</span></div>', unsafe_allow_html=True)
    ultima_obs = next((obs for obs in reversed(df_filtrado["Observacao"].tolist()) if str(obs).strip()), "Sem observacoes recentes.") if not df_filtrado.empty else "Sem observacoes recentes."
    resumo_col3.markdown(f'<div class="dh-chart-mini"><strong>Ultima observacao</strong><span>{str(ultima_obs)[:90]}</span></div>', unsafe_allow_html=True)

    chart_col1, chart_col2 = st.columns([1.35, 1], gap="large")
    with chart_col1:
        st.markdown('<div class="dh-chart-panel"><h4>Evolucao principal</h4><p>Leitura longitudinal do indicador selecionado para apoiar consultas de acompanhamento.</p></div>', unsafe_allow_html=True)
        serie_principal = df_filtrado[["DataLabel", indicador_principal]].dropna()
        if not serie_principal.empty:
            fig_main = px.line(
                serie_principal,
                x="DataLabel",
                y=indicador_principal,
                markers=True,
                color_discrete_sequence=["#52e0b4"],
            )
            fig_main.update_layout(height=380, margin=dict(l=10, r=10, t=10, b=10), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
            st.plotly_chart(fig_main, use_container_width=True, config={"displayModeBar": False})
        else:
            st.markdown('<div class="dh-chart-empty">Sem pontos suficientes para o indicador selecionado neste periodo.</div>', unsafe_allow_html=True)

    with chart_col2:
        st.markdown('<div class="dh-chart-panel"><h4>Composicao corporal</h4><p>Compare massa magra, massa gorda e percentual de gordura sem sair do fluxo do paciente.</p></div>', unsafe_allow_html=True)
        comp_cols = [col for col in ["Massa magra", "Massa gorda", "% Gordura"] if col in df_filtrado.columns and df_filtrado[col].dropna().any()]
        if comp_cols:
            ultimo_comp = df_filtrado[comp_cols].dropna(how="all")
            if not ultimo_comp.empty:
                ultimo_comp = ultimo_comp.iloc[-1].dropna()
                donut_df = pd.DataFrame(
                    {
                        "Indicador": list(ultimo_comp.index),
                        "Valor": [float(v) for v in ultimo_comp.tolist()],
                    }
                )
                fig_donut = px.pie(
                    donut_df,
                    names="Indicador",
                    values="Valor",
                    hole=0.58,
                    color="Indicador",
                    color_discrete_map={
                        "Massa magra": "#52e0b4",
                        "Massa gorda": "#ff7f7f",
                        "% Gordura": "#f6c85f",
                    },
                )
                fig_donut.update_traces(textposition="inside", textinfo="percent+label")
                fig_donut.update_layout(height=260, margin=dict(l=10, r=10, t=10, b=10), paper_bgcolor="rgba(0,0,0,0)")
                st.plotly_chart(fig_donut, use_container_width=True, config={"displayModeBar": False})

            melt_df = df_filtrado[["DataLabel"] + comp_cols].melt(id_vars="DataLabel", var_name="Indicador", value_name="Valor").dropna()
            fig_comp = px.line(melt_df, x="DataLabel", y="Valor", color="Indicador", markers=True)
            fig_comp.update_layout(height=260, margin=dict(l=10, r=10, t=10, b=10), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
            st.plotly_chart(fig_comp, use_container_width=True, config={"displayModeBar": False})
        else:
            st.markdown('<div class="dh-chart-empty">Ainda nao ha dados de composicao corporal suficientes para comparar.</div>', unsafe_allow_html=True)

    bottom_col1, bottom_col2 = st.columns([1.15, 1], gap="large")
    with bottom_col1:
        st.markdown('<div class="dh-chart-panel"><h4>Comparativo de indicadores</h4><p>Analise rapidamente a relacao entre peso, IMC e cintura nos registros mais recentes.</p></div>', unsafe_allow_html=True)
        compare_cols = [col for col in ["Peso", "IMC", "Cintura"] if df_filtrado[col].dropna().any()]
        if compare_cols:
            compare_df = df_filtrado[["DataLabel"] + compare_cols].tail(8).melt(id_vars="DataLabel", var_name="Indicador", value_name="Valor").dropna()
            fig_compare = px.bar(compare_df, x="DataLabel", y="Valor", color="Indicador", barmode="group")
            fig_compare.update_layout(height=330, margin=dict(l=10, r=10, t=10, b=10), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
            st.plotly_chart(fig_compare, use_container_width=True, config={"displayModeBar": False})
        else:
            st.markdown('<div class="dh-chart-empty">Nao ha indicadores comparativos suficientes para montar esse grafico.</div>', unsafe_allow_html=True)

    with bottom_col2:
        st.markdown('<div class="dh-chart-panel"><h4>Historico resumido</h4><p>Use esta tabela para revisar a progressao do paciente e localizar rapidamente os registros salvos no prontuario.</p></div>', unsafe_allow_html=True)
        view_cols = [col for col in ["DataLabel", "Peso", "IMC", "% Gordura", "Cintura", "Massa magra", "Massa gorda"] if col in df_filtrado.columns]
        view_df = df_filtrado[view_cols].rename(columns={"DataLabel": "Data"})
        st.dataframe(view_df, use_container_width=True, hide_index=True)

def modulo_relatorios():
    st.title("📋 Relatórios de Pacientes")
    st.markdown(
        '<div class="dh-pill-soft">Central clínica premium para leitura rápida, evolução e tomada de decisão.</div>',
        unsafe_allow_html=True,
    )
    st.write("")
    st.markdown(
        """
        <style>
        .dh-report-shell{display:flex;flex-direction:column;gap:16px;}
        .dh-report-hero{display:flex;flex-direction:column;gap:16px;}
        .dh-report-panel,.dh-report-summary,.dh-report-hero-card{background:linear-gradient(180deg,rgba(11,23,43,.94),rgba(9,17,33,.9));border:1px solid rgba(148,163,184,.16);border-radius:24px;padding:20px 22px;box-shadow:0 16px 38px rgba(0,0,0,.24);}
        .dh-report-hero-card{display:flex;flex-direction:column;gap:18px;}
        .dh-report-hero-top{display:grid;grid-template-columns:minmax(0,1.3fr) minmax(320px,1fr);gap:18px;align-items:start;}
        .dh-report-hero-copy{min-width:0;}
        .dh-report-hero-summary{min-width:0;display:flex;flex-direction:column;gap:14px;padding:2px 0 0 10px;border-left:1px solid rgba(148,163,184,.12);}
        .dh-report-title{font-size:2rem;font-weight:900;color:#f8fbff;margin-bottom:8px;letter-spacing:-.02em;}
        .dh-report-subtitle{color:#c4d3ea;line-height:1.65;font-size:1rem;margin-bottom:14px;}
        .dh-report-pills{display:flex;flex-wrap:wrap;gap:8px;}
        .dh-report-pill{display:inline-flex;align-items:center;gap:6px;padding:7px 12px;border-radius:999px;background:rgba(16,185,129,.12);border:1px solid rgba(16,185,129,.2);color:#b7ffdf;font-weight:700;font-size:.85rem;}
        .dh-report-summary-head{display:flex;justify-content:space-between;gap:12px;align-items:flex-start;}
        .dh-report-summary-name{color:#f8fbff;font-size:1.45rem;font-weight:900;margin-bottom:4px;}
        .dh-report-summary-meta{color:#9fb2cc;font-size:.95rem;line-height:1.55;}
        .dh-report-badge{display:inline-flex;align-items:center;justify-content:center;padding:8px 12px;border-radius:999px;font-weight:800;font-size:.83rem;white-space:nowrap;}
        .dh-report-badge.ok{background:rgba(34,197,94,.16);border:1px solid rgba(34,197,94,.3);color:#b7ffcf;}
        .dh-report-badge.warn{background:rgba(245,158,11,.16);border:1px solid rgba(245,158,11,.28);color:#ffe3a5;}
        .dh-report-summary-goal{background:rgba(255,255,255,.04);border:1px solid rgba(148,163,184,.11);border-radius:18px;padding:14px 16px;}
        .dh-report-summary-goal-label{color:#8ea4c2;font-size:.78rem;text-transform:uppercase;letter-spacing:.06em;font-weight:800;margin-bottom:7px;}
        .dh-report-summary-goal-value{color:#e5eefc;font-size:.96rem;line-height:1.62;font-weight:600;}
        .dh-report-kpis{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:12px;}
        .dh-report-kpi{background:rgba(255,255,255,.04);border:1px solid rgba(148,163,184,.13);border-radius:18px;padding:14px 14px 12px;}
        .dh-report-kpi-label{color:#8ea4c2;font-size:.8rem;text-transform:uppercase;letter-spacing:.04em;font-weight:700;margin-bottom:8px;}
        .dh-report-kpi-value{color:#fff;font-size:1.45rem;font-weight:900;line-height:1.1;margin-bottom:4px;}
        .dh-report-kpi-foot{color:#95aac8;font-size:.83rem;}
        .dh-report-section-title{color:#f8fbff;font-size:1.05rem;font-weight:900;margin-bottom:6px;}
        .dh-report-section-subtitle{color:#9fb2cc;font-size:.93rem;line-height:1.55;margin-bottom:12px;}
        .dh-report-data-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px;}
        .dh-report-data-item{background:rgba(255,255,255,.035);border:1px solid rgba(148,163,184,.11);border-radius:16px;padding:12px 14px;min-height:78px;}
        .dh-report-data-label{color:#8ea4c2;font-size:.78rem;text-transform:uppercase;letter-spacing:.04em;font-weight:700;margin-bottom:8px;}
        .dh-report-data-value{color:#f8fbff;font-size:1rem;line-height:1.55;font-weight:700;word-break:break-word;}
        .dh-report-alerts,.dh-report-notes{display:flex;flex-direction:column;gap:10px;}
        .dh-report-alert{background:rgba(245,158,11,.12);border:1px solid rgba(245,158,11,.22);color:#ffe7b3;border-radius:16px;padding:12px 14px;line-height:1.55;font-weight:600;}
        .dh-report-alert.ok{background:rgba(34,197,94,.12);border:1px solid rgba(34,197,94,.22);color:#bcf7ce;}
        .dh-report-note,.dh-report-timeline-item{background:rgba(255,255,255,.04);border:1px solid rgba(148,163,184,.11);border-radius:16px;padding:14px 16px;color:#e5eefc;line-height:1.65;}
        .dh-report-timeline-item{margin-bottom:12px;}
        .dh-report-timeline-title{color:#f8fbff;font-weight:900;font-size:1rem;margin-bottom:4px;}
        .dh-report-timeline-meta{color:#96abca;font-size:.9rem;margin-bottom:10px;}
        @media (max-width:980px){.dh-report-hero-top{grid-template-columns:1fr}.dh-report-hero-summary{padding:0;border-left:none;border-top:1px solid rgba(148,163,184,.12);padding-top:14px}.dh-report-kpis{grid-template-columns:repeat(2,minmax(0,1fr))}.dh-report-data-grid{grid-template-columns:1fr}}
        @media (max-width:640px){.dh-report-kpis{grid-template-columns:1fr}}
        </style>
        """,
        unsafe_allow_html=True,
    )

    meus_pacientes = filtrar_por_usuario(pacientes)
    if not meus_pacientes:
        st.warning("Sem pacientes.")
        return

    def _report_fmt(val):
        if val is None or val == "":
            return "—"
        if isinstance(val, float):
            txt = f"{val:.2f}"
            return txt.rstrip("0").rstrip(".")
        return str(val)

    def _report_label(key):
        return str(key).replace("_", " ").title()

    def _is_filled(v):
        if v is None:
            return False
        if isinstance(v, str):
            return bool(v.strip())
        if isinstance(v, (list, dict, tuple, set)):
            return len(v) > 0
        return True

    p_nome = st.selectbox("Paciente", [x["nome"] for x in meus_pacientes], key="r_sel")
    obj = next((x for x in meus_pacientes if x.get("nome") == p_nome), None)
    if not obj:
        st.warning("Paciente não encontrado.")
        return

    historico = obj.get("historico", []) or []
    anamnese = get_anamnese_paciente(obj) or {}
    ultimos = get_ultimos_dados(obj) or {}
    cad_data = {k: v for k, v in obj.items() if k not in {"historico", "anamnese", "portal"}}

    records = []
    for item in historico:
        dados_vitais = item.get("dados_vitais") or {}
        dobras = item.get("dobras") or {}
        perimetria = item.get("perimetria") or {}
        data_raw = item.get("data")
        records.append(
            {
                "Data": _fmt_data_br(data_raw) if data_raw else "—",
                "Data_dt": pd.to_datetime(data_raw, errors="coerce"),
                "Tipo": (item.get("tipo") or "Avaliação").replace("_", " ").title(),
                "Peso": pd.to_numeric(dados_vitais.get("peso"), errors="coerce"),
                "IMC": pd.to_numeric(dados_vitais.get("imc"), errors="coerce"),
                "% Gordura": pd.to_numeric(dados_vitais.get("bioimpedancia", dobras.get("percentual_gordura")), errors="coerce"),
                "Cintura": pd.to_numeric(perimetria.get("cintura"), errors="coerce"),
                "Quadril": pd.to_numeric(perimetria.get("quadril"), errors="coerce"),
                "RCQ": pd.to_numeric(perimetria.get("rcq"), errors="coerce"),
                "Obs": item.get("nota") or item.get("observacoes") or item.get("observações") or "",
                "Receita": item.get("receita") or item.get("receitas") or item.get("prescricao") or "",
                "Dieta": item.get("dieta") or item.get("dietas") or item.get("plano_alimentar") or "",
                "Medicamentos": item.get("medicacoes") or item.get("medicações") or item.get("medicacao") or "",
            }
        )

    df_hist = pd.DataFrame(records)
    if not df_hist.empty and "Data_dt" in df_hist.columns:
        df_hist = df_hist.sort_values("Data_dt", na_position="last").reset_index(drop=True)

    def _series_or_none(df_src, col):
        if df_src.empty or col not in df_src.columns:
            return pd.Series(dtype="float64")
        return pd.to_numeric(df_src[col], errors="coerce")

    def _last_valid(series):
        valid = series.dropna()
        return valid.iloc[-1] if not valid.empty else None

    peso_series = _series_or_none(df_hist, "Peso")
    imc_series = _series_or_none(df_hist, "IMC")
    gordura_series = _series_or_none(df_hist, "% Gordura")
    cintura_series = _series_or_none(df_hist, "Cintura")
    peso_atual = _last_valid(peso_series)
    imc_atual = _last_valid(imc_series)
    gordura_atual = _last_valid(gordura_series)
    cintura_atual = _last_valid(cintura_series)
    cadastro_ignorados = {"id", "dono", "created_at", "updated_at"}
    campos_cadastro = [k for k in cad_data.keys() if k not in cadastro_ignorados]
    total_campos = len(campos_cadastro) or 1
    campos_preenchidos = sum(1 for k in campos_cadastro if _is_filled(cad_data.get(k)))
    pct_cadastro = int(round((campos_preenchidos / total_campos) * 100))
    ultima_consulta = ultimos.get("data") or (df_hist["Data"].iloc[-1] if not df_hist.empty else "—")
    status_acomp = "Em acompanhamento" if historico else "Sem avaliações"
    status_cls = "ok" if historico else "warn"
    objetivo = _clean_text(anamnese.get("queixa_principal") or obj.get("objetivo") or obj.get("objetivo_principal") or "") or "Objetivo clínico ainda não registrado."
    idade_txt = obj.get("idade") or ultimos.get("idade") or "—"
    sexo_txt = obj.get("sexo") or ultimos.get("sexo") or "—"
    atualizacao = obj.get("updated_at") or obj.get("created_at") or ultimos.get("data") or ultima_consulta
    pendencias = []
    if pct_cadastro < 70:
        pendencias.append("Cadastro com preenchimento abaixo de 70%.")
    if not historico:
        pendencias.append("Paciente sem histórico de avaliação salvo.")
    if not _is_filled(obj.get("email")) and not _is_filled(obj.get("telefone")):
        pendencias.append("Contato principal incompleto.")
    if not _is_filled(anamnese.get("queixa_principal")):
        pendencias.append("Queixa principal ainda não documentada.")

    st.markdown('<div class="dh-report-shell">', unsafe_allow_html=True)
    st.markdown(
        f"""
        <div class="dh-report-hero">
          <div class="dh-report-hero-card">
            <div class="dh-report-hero-top">
              <div class="dh-report-hero-copy">
                <div class="dh-report-title">Relatório clínico premium</div>
                <div class="dh-report-subtitle">Acompanhe rapidamente o estado do paciente, evolução corporal, contexto clínico e pendências de acompanhamento em uma visão consolidada.</div>
                <div class="dh-report-pills">
                  <span class="dh-report-pill">📌 Relatório individual</span>
                  <span class="dh-report-pill">📈 Evolução clínica</span>
                  <span class="dh-report-pill">🧾 Exportação pronta</span>
                </div>
              </div>
              <div class="dh-report-hero-summary">
                <div class="dh-report-summary-head">
                  <div>
                    <div class="dh-report-summary-name">{html.escape(_report_fmt(obj.get("nome")))}</div>
                    <div class="dh-report-summary-meta">{html.escape(_report_fmt(idade_txt))} • {html.escape(_report_fmt(sexo_txt))}<br>Última consulta: {html.escape(_report_fmt(ultima_consulta))}<br>Atualização: {html.escape(_report_fmt(atualizacao))}</div>
                  </div>
                  <span class="dh-report-badge {status_cls}">{html.escape(status_acomp)}</span>
                </div>
                <div class="dh-report-summary-goal">
                  <div class="dh-report-summary-goal-label">Objetivo clínico</div>
                  <div class="dh-report-summary-goal-value">{html.escape(_report_fmt(objetivo))}</div>
                </div>
              </div>
            </div>
            <div class="dh-report-kpis">
              <div class="dh-report-kpi"><div class="dh-report-kpi-label">Consultas</div><div class="dh-report-kpi-value">{len(historico)}</div><div class="dh-report-kpi-foot">Registros salvos no histórico</div></div>
              <div class="dh-report-kpi"><div class="dh-report-kpi-label">Peso atual</div><div class="dh-report-kpi-value">{html.escape(_report_fmt(peso_atual))}</div><div class="dh-report-kpi-foot">Kg mais recente registrado</div></div>
              <div class="dh-report-kpi"><div class="dh-report-kpi-label">IMC atual</div><div class="dh-report-kpi-value">{html.escape(_report_fmt(imc_atual))}</div><div class="dh-report-kpi-foot">Indicador corporal consolidado</div></div>
              <div class="dh-report-kpi"><div class="dh-report-kpi-label">% gordura</div><div class="dh-report-kpi-value">{html.escape(_report_fmt(gordura_atual))}</div><div class="dh-report-kpi-foot">Última composição disponível</div></div>
              <div class="dh-report-kpi"><div class="dh-report-kpi-label">Cintura</div><div class="dh-report-kpi-value">{html.escape(_report_fmt(cintura_atual))}</div><div class="dh-report-kpi-foot">Perimetria atual</div></div>
              <div class="dh-report-kpi"><div class="dh-report-kpi-label">Cadastro</div><div class="dh-report-kpi-value">{pct_cadastro}%</div><div class="dh-report-kpi-foot">{campos_preenchidos}/{total_campos} campos preenchidos</div></div>
            </div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    tab_visao, tab_evolucao, tab_historico, tab_dados = st.tabs(["Visão Geral", "Evolução", "Histórico Clínico", "Dados Cadastrais"])

    with tab_visao:
        col_left, col_right = st.columns([1.3, 0.95], gap="large")
        with col_left:
            st.markdown('<div class="dh-report-panel"><div class="dh-report-section-title">Resumo do paciente</div><div class="dh-report-section-subtitle">Dados essenciais de identificação e acompanhamento para leitura rápida.</div>', unsafe_allow_html=True)
            resumo_items = {"Nome": obj.get("nome"), "Idade": idade_txt, "Sexo": sexo_txt, "Última consulta": ultima_consulta, "E-mail": obj.get("email"), "Telefone": obj.get("telefone"), "Cidade": obj.get("cidade"), "Documento": obj.get("documento")}
            resumo_html = "".join(f'<div class="dh-report-data-item"><div class="dh-report-data-label">{html.escape(_report_label(k))}</div><div class="dh-report-data-value">{html.escape(_report_fmt(v))}</div></div>' for k, v in resumo_items.items())
            st.markdown(f'<div class="dh-report-data-grid">{resumo_html}</div></div>', unsafe_allow_html=True)

            ultima_obs = "Sem observações recentes registradas."
            if not df_hist.empty and "Obs" in df_hist.columns:
                obs_validas = df_hist["Obs"].replace("", pd.NA).dropna()
                if not obs_validas.empty:
                    ultima_obs = _clean_text(obs_validas.iloc[-1])
            contexto = _clean_text(anamnese.get("doencas") or anamnese.get("condicoes") or anamnese.get("alergias") or anamnese.get("intolerancias") or "") or "Sem condições clínicas destacadas."
            notes = [("Objetivo principal", objetivo), ("Últimas observações", ultima_obs), ("Condições e contexto", contexto)]
            notes_html = "".join(f'<div class="dh-report-note"><div class="dh-report-data-label">{html.escape(t)}</div><div class="dh-report-data-value">{html.escape(v)}</div></div>' for t, v in notes)
            st.markdown(f'<div class="dh-report-panel"><div class="dh-report-section-title">Visão clínica resumida</div><div class="dh-report-section-subtitle">Objetivos, contexto clínico e observações mais recentes sem percorrer todo o prontuário.</div><div class="dh-report-notes">{notes_html}</div></div>', unsafe_allow_html=True)

        with col_right:
            alerts_html = "".join(f'<div class="dh-report-alert">{html.escape(item)}</div>' for item in pendencias) if pendencias else '<div class="dh-report-alert ok">Cadastro e histórico sem pendências críticas.</div>'
            st.markdown(f'<div class="dh-report-panel"><div class="dh-report-section-title">Status e pendências</div><div class="dh-report-section-subtitle">Pontos que merecem atenção para melhorar a qualidade do acompanhamento.</div><div class="dh-report-alerts">{alerts_html}</div></div>', unsafe_allow_html=True)
            st.markdown('<div class="dh-report-panel"><div class="dh-report-section-title">Últimos registros</div><div class="dh-report-section-subtitle">Últimas medições consolidadas para conferência rápida.</div>', unsafe_allow_html=True)
            if not df_hist.empty:
                st.dataframe(df_hist[["Data", "Tipo", "Peso", "IMC", "% Gordura", "Cintura"]].tail(5), use_container_width=True, hide_index=True)
            else:
                st.info("Paciente ainda não possui avaliações registradas.")
            st.markdown("</div>", unsafe_allow_html=True)


    with tab_evolucao:
        st.markdown('<div class="dh-report-panel"><div class="dh-report-section-title">Evolução corporal e comparativos</div><div class="dh-report-section-subtitle">Gráficos clínicos para acompanhar tendência, progresso e variações ao longo do tempo.</div></div>', unsafe_allow_html=True)
        if df_hist.empty or df_hist["Data_dt"].dropna().empty:
            st.info("Ainda não há dados históricos suficientes para gerar gráficos de evolução.")
        else:
            chart_data = df_hist.dropna(subset=["Data_dt"]).copy()
            c1, c2 = st.columns(2, gap="large")
            with c1:
                if chart_data["Peso"].notna().any():
                    fig_peso = px.line(chart_data, x="Data_dt", y="Peso", markers=True, title="Evolução do peso", template="plotly_dark")
                    fig_peso.update_layout(margin=dict(l=20, r=20, t=46, b=20), xaxis_title="", yaxis_title="Kg")
                    st.plotly_chart(fig_peso, use_container_width=True)
                else:
                    st.info("Sem peso suficiente para o gráfico.")
            with c2:
                if chart_data["IMC"].notna().any():
                    fig_imc = px.line(chart_data, x="Data_dt", y="IMC", markers=True, title="Evolução do IMC", template="plotly_dark")
                    fig_imc.update_layout(margin=dict(l=20, r=20, t=46, b=20), xaxis_title="", yaxis_title="IMC")
                    st.plotly_chart(fig_imc, use_container_width=True)
                else:
                    st.info("Sem IMC suficiente para o gráfico.")
            c3, c4 = st.columns(2, gap="large")
            with c3:
                if chart_data["% Gordura"].notna().any():
                    fig_g = px.line(chart_data, x="Data_dt", y="% Gordura", markers=True, title="Evolução do percentual de gordura", template="plotly_dark")
                    fig_g.update_layout(margin=dict(l=20, r=20, t=46, b=20), xaxis_title="", yaxis_title="%")
                    st.plotly_chart(fig_g, use_container_width=True)
                else:
                    st.info("Sem percentual de gordura suficiente para o gráfico.")
            with c4:
                compare_cols = [c for c in ["Peso", "IMC", "% Gordura", "Cintura"] if chart_data[c].notna().any()]
                if compare_cols:
                    df_compare = chart_data[["Data_dt"] + compare_cols].melt(id_vars="Data_dt", value_vars=compare_cols, var_name="Indicador", value_name="Valor")
                    fig_compare = px.line(df_compare, x="Data_dt", y="Valor", color="Indicador", markers=True, title="Comparativo entre indicadores", template="plotly_dark")
                    fig_compare.update_layout(margin=dict(l=20, r=20, t=46, b=20), xaxis_title="", yaxis_title="")
                    st.plotly_chart(fig_compare, use_container_width=True)
                else:
                    st.info("Sem indicadores suficientes para o comparativo.")
            st.markdown('<div class="dh-report-panel"><div class="dh-report-section-title">Tabela histórica</div><div class="dh-report-section-subtitle">Comparativo clínico por data para consulta rápida e exportação.</div></div>', unsafe_allow_html=True)
            st.dataframe(chart_data[["Data", "Tipo", "Peso", "IMC", "% Gordura", "Cintura", "RCQ"]].copy(), use_container_width=True, hide_index=True)

    with tab_historico:
        st.markdown('<div class="dh-report-panel"><div class="dh-report-section-title">Histórico clínico e observações</div><div class="dh-report-section-subtitle">Registro longitudinal das consultas com observações, receitas, dietas e medicamentos.</div></div>', unsafe_allow_html=True)
        if not historico:
            st.info("Paciente sem histórico clínico registrado.")
        else:
            total_hist = len(historico)
            for idx, item in enumerate(reversed(historico), start=1):
                dados_vitais = item.get("dados_vitais") or {}
                dobras = item.get("dobras") or {}
                perimetria = item.get("perimetria") or {}
                tipo_label = (item.get("tipo") or "Avaliação").replace("_", " ").title()
                data_label = _fmt_data_br(item.get("data")) if item.get("data") else "Sem data"
                resumo_linha = [f"Peso: {_report_fmt(dados_vitais.get('peso'))}", f"IMC: {_report_fmt(dados_vitais.get('imc'))}", f"% Gordura: {_report_fmt(dados_vitais.get('bioimpedancia', dobras.get('percentual_gordura')))}", f"Cintura: {_report_fmt(perimetria.get('cintura'))}"]
                st.markdown(f'<div class="dh-report-timeline-item"><div class="dh-report-timeline-title">Consulta {total_hist - idx + 1} • {html.escape(tipo_label)}</div><div class="dh-report-timeline-meta">{html.escape(data_label)} • {" • ".join(html.escape(x) for x in resumo_linha)}</div></div>', unsafe_allow_html=True)
                with st.expander(f"Ver detalhes da consulta • {data_label}", expanded=False):
                    obs_text = item.get("nota") or item.get("observacoes") or item.get("observações") or "Sem observações registradas."
                    dieta_text = item.get("dieta") or item.get("dietas") or item.get("plano_alimentar") or "Sem plano alimentar registrado."
                    receita_text = item.get("receita") or item.get("receitas") or item.get("prescricao") or "Sem prescrição registrada."
                    medicamentos_text = item.get("medicacoes") or item.get("medicações") or item.get("medicacao") or "Sem medicações registradas."
                    cols_hist = st.columns(2, gap="large")
                    with cols_hist[0]:
                        st.markdown("**Observações / evolução**")
                        st.write(obs_text)
                        st.markdown("**Dieta / plano alimentar**")
                        st.write(dieta_text)
                    with cols_hist[1]:
                        st.markdown("**Receitas / prescrições**")
                        st.write(receita_text)
                        st.markdown("**Medicamentos / suplementos**")
                        st.write(medicamentos_text)


    with tab_dados:
        st.markdown('<div class="dh-report-panel"><div class="dh-report-section-title">Dados cadastrais e clínicos</div><div class="dh-report-section-subtitle">Informações estruturadas do cadastro e dos dados clínicos mais recentes, sem aparência de planilha bruta.</div></div>', unsafe_allow_html=True)
        cadastro_html = "".join(f'<div class="dh-report-data-item"><div class="dh-report-data-label">{html.escape(_report_label(k))}</div><div class="dh-report-data-value">{html.escape(_report_fmt(cad_data.get(k)))}</div></div>' for k in campos_cadastro)
        st.markdown(f'<div class="dh-report-panel"><div class="dh-report-section-title">Dados cadastrais</div><div class="dh-report-section-subtitle">Estrutura refinada para leitura rápida dos dados de identificação e contato.</div><div class="dh-report-data-grid">{cadastro_html}</div></div>', unsafe_allow_html=True)
        dados_clinicos_src = {}
        if isinstance(ultimos, dict):
            dados_clinicos_src.update(ultimos)
        if historico:
            last_item = historico[-1]
            for bloco in ["dados_vitais", "dobras", "perimetria", "medidas"]:
                bloco_data = last_item.get(bloco) or {}
                if isinstance(bloco_data, dict):
                    dados_clinicos_src.update(bloco_data)
        clinical_fields = ["peso", "altura", "imc", "bioimpedancia", "percentual_gordura", "massa_magra", "massa_gorda", "cintura", "quadril", "rcq"]
        clinical_html = "".join(f'<div class="dh-report-data-item"><div class="dh-report-data-label">{html.escape(_report_label(field))}</div><div class="dh-report-data-value">{html.escape(_report_fmt(dados_clinicos_src.get(field)))}</div></div>' for field in clinical_fields)
        st.markdown(f'<div class="dh-report-panel"><div class="dh-report-section-title">Dados clínicos consolidados</div><div class="dh-report-section-subtitle">Indicadores mais importantes da avaliação atual, organizados para uso clínico rápido.</div><div class="dh-report-data-grid">{clinical_html}</div></div>', unsafe_allow_html=True)
        notes = [("Queixa principal", anamnese.get("queixa_principal")), ("Alergias / intolerâncias", anamnese.get("alergias") or anamnese.get("intolerancias")), ("Observações clínicas", anamnese.get("observacoes") or anamnese.get("observações"))]
        notes_html = "".join(f'<div class="dh-report-note"><div class="dh-report-data-label">{html.escape(title)}</div><div class="dh-report-data-value">{html.escape(_clean_text(text) or "Não informado.")}</div></div>' for title, text in notes)
        st.markdown(f'<div class="dh-report-panel"><div class="dh-report-section-title">Observações e contexto clínico</div><div class="dh-report-section-subtitle">Pontos qualitativos que complementam os dados objetivos do relatório.</div><div class="dh-report-notes">{notes_html}</div></div>', unsafe_allow_html=True)

    st.markdown('<div class="dh-report-panel"><div class="dh-report-section-title">Exportações</div><div class="dh-report-section-subtitle">Gere arquivos prontos para análise externa, envio e impressão profissional.</div></div>', unsafe_allow_html=True)
    export_df = df_hist.copy() if not df_hist.empty else pd.DataFrame(historico)
    if "Data_dt" in export_df.columns:
        export_df = export_df.drop(columns=["Data_dt"])
    csv_data = export_df.to_csv(index=False).encode("utf-8")
    resumo_pdf = [f"RELATÓRIO CLÍNICO DO PACIENTE: {_report_fmt(obj.get('nome'))}", "", f"Última consulta: {_report_fmt(ultima_consulta)}", f"Status: {status_acomp}", f"Cadastro preenchido: {pct_cadastro}%", f"Peso atual: {_report_fmt(peso_atual)}", f"IMC atual: {_report_fmt(imc_atual)}", f"Percentual de gordura atual: {_report_fmt(gordura_atual)}", "", "Objetivo principal:", objetivo, "", "Observações clínicas:", _clean_text(anamnese.get("observacoes") or anamnese.get("observações") or "") or "Sem observações adicionais.", "", f"Total de registros no histórico: {len(historico)}"]
    pdf_data = gerar_pdf_pro(_report_fmt(obj.get("nome")), "\\n".join(resumo_pdf), "RELATÓRIO CLÍNICO")
    exp_col1, exp_col2 = st.columns(2, gap="large")
    with exp_col1:
        st.download_button("⬇️ Baixar histórico (CSV)", csv_data, file_name=f"historico_{_clean_text(_report_fmt(obj.get('nome'))).replace(' ', '_')}.csv", mime="text/csv", use_container_width=True)
    with exp_col2:
        st.download_button("⬇️ Baixar relatório (PDF)", pdf_data, file_name=f"relatorio_{_clean_text(_report_fmt(obj.get('nome'))).replace(' ', '_')}.pdf", mime="application/pdf", use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)


def _diethealth_backup_datasets():
    return [
        ("users.json", users),
        ("pacientes.json", pacientes),
        ("agenda.json", agenda),
        ("chat_log.json", chat_log),
        ("chatbot_ia.json", chatbot_ia_log),
        ("noticias.json", noticias),
        ("financeiro.json", financeiro),
        ("payments.json", payments),
        ("support_tickets.json", support_tickets),
        ("feedbacks.json", feedbacks),
    ]


def _build_diethealth_backup_zip():
    datasets = _diethealth_backup_datasets()
    meta = {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "db_enabled": _db_enabled(),
        "counts": {name: (len(data) if isinstance(data, list) else None) for name, data in datasets},
    }
    bio = io.BytesIO()
    with zipfile.ZipFile(bio, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("meta.json", json.dumps(meta, ensure_ascii=False, indent=2).encode("utf-8"))
        for name, data in datasets:
            zf.writestr(name, json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8"))
    return bio.getvalue(), datasets, meta


def modulo_admin():
    if st.session_state.get("tipo") != "admin":
        st.error("Acesso negado.")
        return

    _refresh_users_cache()
    st.title("⚙️ Gerenciar Usuários")
    st.markdown('<div class="dh-pill-soft">Crie e remova usuários do sistema.</div>', unsafe_allow_html=True)
    backup_bytes, _backup_datasets, _backup_meta = _build_diethealth_backup_zip()
    quick_backup_col_left, quick_backup_col_right = st.columns([0.58, 0.42], gap="large")
    with quick_backup_col_right:
        st.download_button(
            "⬇️ Backup rápido do sistema",
            data=backup_bytes,
            file_name=f"diethealth_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip",
            mime="application/zip",
            use_container_width=True,
            key="admin_quick_backup_btn",
        )
    st.write("")

    now_dt = datetime.now()
    online_users = [
        x for x in users
        if (x.get("tipo") or "").strip().lower() != "admin" and _is_user_online(x, now_dt)
    ]
    if online_users:
        nomes_online = ", ".join(sorted((x.get("usuario") or "").strip() for x in online_users if x.get("usuario")))
        st.success(f"Usuários online agora ({len(online_users)}): {nomes_online}")
    else:
        st.caption("Nenhum usuário online agora.")

    users_view = []
    for u in users:
        row = dict(u)
        row["online_agora"] = "Sim" if _is_user_online(u, now_dt) else "Não"
        row["ultimo_acesso"] = _fmt_last_seen_value(u.get("last_seen_at"))
        users_view.append(row)
    render_table(users_view, min_height=360, max_height=860)

    t1, t2, t3, t4 = st.tabs(["➕ Criar", "🗑️ Excluir", "💳 Assinaturas", "💾 Backup"])
    with t1:
        with st.form("new"):
            n = st.text_input("Nome completo")
            cpf = st.text_input("CPF")
            u = st.text_input("User")
            s = st.text_input("Pass", type="password")
            tp = st.selectbox("Tipo", ["user", "admin"])
            status = st.selectbox("Status", ["active", "pending", "blocked"])
            venc = st.date_input("Vencimento (opcional)", value=datetime.now().date() + timedelta(days=FREE_TRIAL_DAYS))
            if st.form_submit_button("Criar"):
                u_norm = (u or "").strip().lower()
                cpf_norm = _normalize_cpf(cpf)
                if any((x.get("usuario") or "").strip().lower() == u_norm for x in users):
                    st.error("Existe!")
                elif tp != "admin" and not _is_valid_cpf(cpf_norm):
                    st.error("Informe um CPF valido.")
                elif tp != "admin" and _cpf_already_exists(cpf_norm):
                    st.error("Ja existe cadastro com este CPF.")
                else:
                    users.append({
                        "nome": n,
                        "cpf": cpf_norm if tp != "admin" else "",
                        "usuario": u_norm,
                        "senha": s,
                        "tipo": tp,
                        "status": status if tp != "admin" else "active",
                        "paid_until": str(venc) if tp != "admin" else None,
                        "wa_provider": "wapi",
                        "wa_token": "",
                        "wa_phone_id": "",
                        "wa_api_url": "",
                        "wa_instance": "",
                        "wa_notify_admin_num": "",
                        "created_at": str(datetime.now().date())
                    })
                    save_db("users.json", users)
                    st.success("Criado!")
                    st.rerun()

    with t2:
        ud = st.selectbox("Excluir quem?", [x.get("usuario") for x in users if x.get("usuario")])
        if st.button("🗑️ Confirmar Exclusão"):
            if ud == st.session_state.get("usuario"):
                st.error("Não pode se excluir!")
            else:
                for x in list(users):
                    if x.get("usuario") == ud:
                        users.remove(x)
                        break
                save_db("users.json", users)
                st.success("Feito!")
                st.rerun()

    with t3:
        st.markdown("### Controle de Assinaturas")
        lista_usuarios = [x for x in users if (x.get("usuario") and (x.get("tipo") != "admin"))]
        if not lista_usuarios:
            st.info("Sem usuários para gerenciar.")
        else:
            sel = st.selectbox("Usuário", [x.get("usuario") for x in lista_usuarios], key="sub_user")
            u_obj = next((x for x in lista_usuarios if x.get("usuario") == sel), None)
            if u_obj:
                status_atual = (u_obj.get("status") or "pending").lower()
                status_new = st.selectbox("Status", ["active", "pending", "blocked"], index=["active","pending","blocked"].index(status_atual) if status_atual in ["active","pending","blocked"] else 1)
                venc_atual = _parse_date_ymd(u_obj.get("paid_until")) or datetime.now().date()
                venc_new = st.date_input("Vencimento", value=venc_atual, key="sub_due")

                col_a, col_b, col_c = st.columns(3)
                if col_a.button("+30 dias"):
                    venc_new = venc_atual + timedelta(days=30)
                if col_b.button("+90 dias"):
                    venc_new = venc_atual + timedelta(days=90)
                if col_c.button("+365 dias"):
                    venc_new = venc_atual + timedelta(days=365)

                if st.button("Salvar assinatura"):
                    u_obj["status"] = status_new
                    u_obj["paid_until"] = str(venc_new) if status_new == "active" else u_obj.get("paid_until")
                    save_db("users.json", users)
                    st.success("Atualizado!")

                st.markdown("#### Mercado Pago")
                if not _mp_access_token():
                    st.caption("Configure `MERCADO_PAGO_ACCESS_TOKEN` para habilitar verificação automática de pagamentos.")
                else:
                    if st.button("Verificar pagamento (Mercado Pago)", key=f"admin_mp_check_{sel}"):
                        if mp_try_auto_activate_user(u_obj):
                            st.success("Pagamento aprovado encontrado. Acesso atualizado automaticamente.")
                        else:
                            st.info("Nenhum pagamento aprovado novo encontrado para este usuário (ainda).")

                pay_user = [
                    p for p in payments
                    if (p.get("dono") or "").strip().lower() == (sel or "").strip().lower()
                ]
                if pay_user:
                    render_table(pay_user, min_height=260, max_height=620)
                else:
                    st.caption("Sem pagamentos registrados para este usuário.")


    with t4:
        st.markdown("### Backup e Persistencia")
        storage_mode = "Banco de Dados (Postgres)" if _db_enabled() else "Arquivos locais (podem sumir em hospedagens temporarias)"
        st.write(f"**Armazenamento atual:** {storage_mode}")
        if not _db_enabled():
            st.warning(
                "Para nao perder pacientes e historicos, configure `DIETHEALTH_DATABASE_URL` (Postgres). "
                "Em Streamlit Cloud, arquivos locais podem ser apagados quando o app reinicia/atualiza."
            )

        datasets = _diethealth_backup_datasets()

        st.markdown("#### Exportar")
        backup_bytes, _backup_datasets, meta = _build_diethealth_backup_zip()
        st.download_button(
            "Baixar backup (.zip)",
            data=backup_bytes,
            file_name=f"diethealth_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip",
            mime="application/zip",
        )

        st.markdown("#### Restaurar")
        up = st.file_uploader("Envie um .zip gerado pelo backup", type=["zip"], key="diethealth_restore_zip")
        confirm = st.checkbox("Confirmo que quero restaurar e substituir os dados atuais.", value=False, key="diethealth_restore_confirm")
        if up and confirm and st.button("Restaurar agora", type="primary", key="diethealth_restore_btn"):
            try:
                restored = {}
                with zipfile.ZipFile(up, "r") as zf:
                    for fname in [n for n, _ in datasets]:
                        try:
                            raw = zf.read(fname).decode("utf-8", errors="replace")
                            restored[fname] = json.loads(raw)
                        except Exception:
                            continue

                if "users.json" in restored and isinstance(restored["users.json"], list):
                    users[:] = restored["users.json"]
                    save_db("users.json", users)
                if "pacientes.json" in restored and isinstance(restored["pacientes.json"], list):
                    pacientes[:] = restored["pacientes.json"]
                    save_db("pacientes.json", pacientes)
                if "agenda.json" in restored:
                    agenda[:] = restored["agenda.json"]
                    save_db("agenda.json", agenda)
                if "chat_log.json" in restored:
                    chat_log[:] = restored["chat_log.json"]
                    save_db("chat_log.json", chat_log)
                if "chatbot_ia.json" in restored:
                    chatbot_ia_log[:] = restored["chatbot_ia.json"]
                    save_db("chatbot_ia.json", chatbot_ia_log)
                if "noticias.json" in restored:
                    noticias[:] = restored["noticias.json"]
                    save_db("noticias.json", noticias)
                if "financeiro.json" in restored:
                    financeiro[:] = restored["financeiro.json"]
                    save_db("financeiro.json", financeiro)
                if "payments.json" in restored and isinstance(restored["payments.json"], list):
                    payments[:] = restored["payments.json"]
                    save_db("payments.json", payments)
                if "support_tickets.json" in restored and isinstance(restored["support_tickets.json"], list):
                    support_tickets[:] = restored["support_tickets.json"]
                    save_db("support_tickets.json", support_tickets)
                if "feedbacks.json" in restored and isinstance(restored["feedbacks.json"], list):
                    feedbacks[:] = restored["feedbacks.json"]
                    save_db("feedbacks.json", feedbacks)

                st.success("Backup restaurado com sucesso.")
                time.sleep(0.4)
                st.rerun()
            except Exception as exc:
                st.error(f"Falha ao restaurar: {exc}")

# =============================================================================
# 8. LANDING PAGE (IMAGEM + CARD PREMIUM + LOGIN + PAGAMENTOS + WHATSAPP)
# =============================================================================
def _html_block(markup: str) -> str:
    # Left-align all lines to avoid Markdown code blocks inside HTML.
    return "\n".join(line.lstrip() for line in markup.strip().splitlines())


def html_premium_card():
    return _html_block(f"""
<div class="dh-premium-card">
<div style="display:flex; justify-content:space-between; align-items:center; gap:12px;">
<div class="dh-premium-title">PLANO PREMIUM</div>
<div class="dh-badge">Recomendado</div>
</div>
<div class="dh-price">R$ 49,90 <span>/mês</span></div>
<div class="dh-premium-desc">
Sistema completo para Nutricionistas e Consultórios com prontuário, agenda e IA.
</div>
<div class="dh-features">
<div class="dh-feature">✅ Área Restrita (Senha)</div>
<div class="dh-feature">✅ Prontuário & Avaliação Física</div>
<div class="dh-feature">✅ Dieta com IA + substituições</div>
<div class="dh-feature">✅ Sincronização Google Agenda</div>
<div class="dh-feature">✅ Assistente Nutricional (Super Health IA)</div>
<div class="dh-feature">✅ Prescrições ilimitadas + PDF</div>
<div class="dh-feature">✅ Composição corporal completa</div>
</div>
<div class="dh-cta-row">
<a class="dh-cta" href="#dh-auth-anchor" target="_self">
<button class="dh-btn dh-btn-green">ASSINE AGORA</button>
</a>
</div>
</div>
""")

def html_pagamento_card():
    return _html_block(f"""
<div class="dh-pay-card">
<div class="dh-pay-title">Formas de pagamento</div>
<div class="dh-cta-row">
<a class="dh-cta" href="#dh-auth-anchor" target="_self">
<button class="dh-btn dh-btn-blue">PAGAR COM CARTÃO (Checkout)</button>
</a>
</div>
<div class="dh-cta-row">
<a class="dh-cta" href="#dh-auth-anchor" target="_self">
<button class="dh-btn dh-btn-green">PAGAR NO PIX</button>
</a>
<a class="dh-cta" href="#dh-auth-anchor" target="_self">
<button class="dh-btn dh-btn-dark">GERAR BOLETO</button>
</a>
</div>
<div class="dh-cta-row">
<a class="dh-cta" href="{WHATSAPP_LINK}" target="_blank">
<button class="dh-btn dh-btn-dark">FALAR NO WHATSAPP</button>
</a>
</div>
</div>
""")

def mostrar_landing_page():
    _inject_google_tag_landing()
    _inject_google_site_verification()
    bg_url = _bg_data_url()
    if not bg_url:
        bg_url = HERO_BG_OPT if os.path.exists(HERO_BG_OPT) else HERO_BG_IMG
    texture_url = _landing_texture_data_url() or bg_url
    logo_url = _landing_logo_data_url()
    side_brand_logo_url = (
        _file_data_url_optimized(os.path.join(os.path.dirname(__file__), "logohealth.png"), max_w=760, max_h=320, prefer_jpeg=False, quality=86)
        or _landing_side_brand_logo_data_url()
        or logo_url
    )
    hero_col_bg_url = ""
    for _p in (
        os.path.join(LANDING_ASSETS_DIR, "Fundos", "Hero_IA_Profile_Glow.png"),
        os.path.join(LANDING_ASSETS_DIR, "Fundos", "Hero_IA_Brain_Glow.png"),
        os.path.join(LANDING_ASSETS_DIR, "IA_Nutritionist_Avatar.png"),
        os.path.join(LANDING_ASSETS_DIR, "Icones", "Robot_IA_Icon_3D.png"),
    ):
        hero_col_bg_url = _file_data_url_optimized(_p, max_w=420, max_h=420)
        if hero_col_bg_url:
            break
    avatar_url = _landing_avatar_data_url()
    enter_btn_url = _landing_enter_btn_data_url()
    assine_btn_url = _landing_assine_btn_data_url()
    mockup_url = _landing_mockup_data_url()
    robot_icon_url = _file_data_url_optimized(os.path.join(LANDING_ASSETS_DIR, "Icones", "Robot_IA_Icon_3D.png"), max_w=140, max_h=140)
    patient_icon_url = _file_data_url_optimized(os.path.join(LANDING_ASSETS_DIR, "Icones", "Consultorio_Dark_3D.png"), max_w=140, max_h=140)
    finance_icon_url = _file_data_url_optimized(os.path.join(LANDING_ASSETS_DIR, "Icones", "Financeiro_Dark_3D.png"), max_w=140, max_h=140)
    patient_profile_url = _file_data_url_optimized(os.path.join(LANDING_ASSETS_DIR, "Icones", "Admin_Dark_3D.png"), max_w=140, max_h=140)
    css = """
<style>
body, .stApp, section[data-testid="stAppViewContainer"] {
  background: radial-gradient(circle at 18% 8%, rgba(0, 247, 255, 0.10), transparent 36%),
              radial-gradient(circle at 83% 88%, rgba(0, 200, 150, 0.10), transparent 34%),
              linear-gradient(135deg, rgba(8,14,28,0.88), rgba(8,14,28,0.92)),
              url("__BG_URL__") !important;
  background-size: cover !important;
  background-position: center center !important;
  background-attachment: fixed !important;
  background-repeat: no-repeat !important;
}
section[data-testid="stAppViewContainer"] .main .block-container {
  background: transparent !important;
  padding-top: 0.35rem !important;
  padding-bottom: 1.2rem !important;
  max-width: 100% !important;
}
/* Landing layout */
header[data-testid="stHeader"],
div[data-testid="stToolbar"],
div[data-testid="stDecoration"]{
  display: none !important;
}
.dh-hero-title{
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 12px;
  text-align: center;
  font-size: 3.2rem;
  font-weight: 900;
  color: #f5f8ff;
  margin-top: 0;
}
.dh-hero-logo{
  font-size: 3.0rem;
}
.dh-top-logo-wrap{
  width: 100%;
  display: flex;
  justify-content: center;
  align-items: center;
  margin: 8px auto 14px auto;
}
.dh-top-logo-img{
  width: min(100%, 520px);
  max-width: 520px;
  max-height: 190px;
  height: auto;
  object-fit: contain;
  object-position: center center;
  filter: drop-shadow(0 14px 28px rgba(0,0,0,0.25));
}
.dh-hero-box{
  margin: 8px auto 10px auto;
  padding: 14px 18px;
  width: 100%;
  max-width: 100%;
  text-align: center;
  background:
    linear-gradient(180deg, rgba(21,101,192,0.22), rgba(10,18,35,0.55)),
    url("__TEXTURE_URL__");
  background-size: cover;
  background-position: center center;
  border: 1px solid rgba(136,221,255,0.26);
  border-radius: 14px;
  box-shadow: 0 14px 30px rgba(0,0,0,0.30);
  backdrop-filter: blur(8px);
}
.dh-hero-sub{
  font-size: 1.18rem;
  font-weight: 700;
  color: rgba(245,248,255,0.96);
}
.dh-hero-sub2{
  margin-top: 6px;
  font-size: 1.05rem;
  font-weight: 600;
  opacity: 0.95;
}
.dh-lead-card{
  background:
    linear-gradient(135deg, rgba(16,120,74,0.28), rgba(12,92,60,0.42)),
    url("__TEXTURE_URL__");
  background-size: cover;
  background-position: center;
  border: 1px solid rgba(136,221,255,0.28);
  border-radius: 16px;
  padding: 20px 20px;
  min-height: 560px;
  box-shadow: inset 0 1px 0 rgba(255,255,255,0.18), 0 14px 30px rgba(0,0,0,0.25);
  backdrop-filter: blur(6px);
}
.dh-landing-cta-strip{
  margin: 10px auto 14px auto;
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 14px;
  flex-wrap: wrap;
}
.dh-landing-cta-strip img{
  height: 56px;
  width: auto;
  max-width: min(100%, 220px);
  object-fit: contain;
  filter: drop-shadow(0 12px 22px rgba(0,0,0,0.34));
}
.dh-landing-avatar{
  margin: 8px auto 0 auto;
  width: min(100%, 210px);
  display: flex;
  justify-content: center;
}
.dh-landing-avatar img{
  width: 100%;
  max-width: 210px;
  height: auto;
  object-fit: contain;
  filter: drop-shadow(0 15px 26px rgba(0,0,0,0.38));
}
.dh-landing-mockup-wrap{
  margin: 8px auto 12px auto;
  width: 100%;
  padding: 10px;
  border-radius: 20px;
  background:
    linear-gradient(160deg, rgba(15, 45, 88, 0.48), rgba(8, 23, 54, 0.44)),
    url("__TEXTURE_URL__");
  background-size: cover;
  background-position: center;
  border: 1px solid rgba(120, 224, 255, 0.34);
  box-shadow:
    inset 0 1px 0 rgba(255,255,255,0.20),
    0 22px 48px rgba(0,0,0,0.32);
  backdrop-filter: blur(8px);
}
.dh-landing-mockup-wrap img{
  width: 100%;
  height: auto;
  border-radius: 14px;
  border: 1px solid rgba(170, 236, 255, 0.22);
  display: block;
}
div[data-testid="column"]:has(.login-box-note) div[data-testid="stForm"] button{
  border: 1px solid rgba(132, 221, 255, 0.42) !important;
  border-radius: 999px !important;
  color: #f2f9ff !important;
  font-weight: 900 !important;
  letter-spacing: 0.03em !important;
  text-shadow: 0 1px 2px rgba(0,0,0,0.45) !important;
  background:
    linear-gradient(180deg, rgba(8, 20, 46, 0.28), rgba(8, 20, 46, 0.44)),
    url("__BTN_ENTER_URL__") center center / cover no-repeat !important;
  box-shadow: 0 10px 24px rgba(0,0,0,0.34), inset 0 1px 0 rgba(255,255,255,0.25) !important;
}
div[data-testid="column"]:has(.login-box-note) div[data-testid="stForm"] button:hover{
  transform: translateY(-1px);
  filter: brightness(1.08);
}
section[data-testid="stSidebar"] div[class*="st-key-toggle_register_form"] button,
div[class*="st-key-toggle_register_form"] button{
  border: 1px solid rgba(113, 226, 184, 0.48) !important;
  border-radius: 999px !important;
  color: #eafff7 !important;
  font-weight: 900 !important;
  letter-spacing: 0.03em !important;
  text-shadow: 0 1px 2px rgba(0,0,0,0.45) !important;
  background:
    linear-gradient(180deg, rgba(7, 34, 25, 0.32), rgba(7, 34, 25, 0.48)),
    url("__BTN_ASSINE_URL__") center center / cover no-repeat !important;
  box-shadow: 0 10px 24px rgba(0,0,0,0.34), inset 0 1px 0 rgba(255,255,255,0.20) !important;
}
.dh-lead-title{
  font-weight: 800;
  font-size: 1.32rem;
  color: #f5f8ff;
  margin-bottom: 8px;
  letter-spacing: 0.2px;
}
.dh-lead-desc{
  font-size: 1.02rem;
  line-height: 1.55;
  color: rgba(245,248,255,0.96);
}
.dh-lead-list{
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 14px 24px;
}
.dh-lead-list .item{
  white-space: nowrap;
  padding: 4px 0;
}
.dh-lead-item + .dh-lead-item{
  margin-top: 10px;
}
.dh-lead-item-title{
  font-weight: 800;
  font-size: 0.98rem;
  margin-bottom: 4px;
}
.dh-lead-item-desc{
  font-size: 0.95rem;
  line-height: 1.45;
  opacity: 0.96;
}
.dh-banner-wrap{
  margin-top: 26px;
  padding: 8px;
  border-radius: 22px;
  background: rgba(255,255,255,0.06);
  border: 1px solid rgba(255,255,255,0.12);
  box-shadow: 0 18px 45px rgba(0,0,0,0.30);
}
.dh-banner-wrap img{ border-radius: 18px; }

/* New landing layout (hero + social proof + features + testimonials + pricing) */
.dh-lp-shell{
  max-width: 1320px;
  margin: 0 auto;
  font-family: "Inter", "Segoe UI", "Montserrat", sans-serif;
  color: #f7fbff;
}
.dh-lp-glass{
  background: rgba(10, 25, 20, 0.40);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  border: 1px solid rgba(255, 255, 255, 0.10);
  border-radius: 16px;
  box-shadow: 0 0 20px rgba(0, 255, 150, 0.20);
}
.dh-lp-header{
  display: none !important;
  justify-content: center;
  align-items: center;
  gap: 0;
  padding: 4px 0 18px 0;
  background: transparent !important;
}
.dh-lp-stream-header-logo{
  display:flex;
  align-items:center;
  justify-content:center;
  width:100%;
  min-height: 112px;
  padding: 0;
}
.dh-lp-stream-header-logo .dh-lp-header-logo{
  width: min(100%, 520px);
  max-width: 520px;
  max-height: 210px;
}
.dh-lp-header-logo{
  width: min(100%, 720px);
  max-width: 720px;
  height: auto;
  max-height: 280px;
  object-fit: contain;
  object-position: center center;
  filter:
    drop-shadow(0 0 2px rgba(255, 255, 255, 0.75))
    drop-shadow(0 10px 22px rgba(0, 0, 0, 0.34))
    brightness(1.22)
    contrast(1.18)
    saturate(1.08);
}
.dh-lp-top-brand{
  display: inline-flex;
  align-items: center;
  gap: 16px;
  min-height: 72px;
}
.dh-lp-top-brand-logo{
  width: 120px;
  height: 120px;
  object-fit: contain;
  filter:
    drop-shadow(0 0 2px rgba(255, 255, 255, 0.64))
    drop-shadow(0 10px 20px rgba(0, 0, 0, 0.26))
    brightness(1.18)
    contrast(1.08);
}
.dh-lp-top-brand-copy{
  display: grid;
  gap: 3px;
  align-items: center;
  text-align: center;
}
.dh-lp-top-brand-title{
  color: #f6fcff;
  font-size: 2.7rem;
  font-weight: 800;
  line-height: 1.08;
  letter-spacing: -0.02em;
  margin-left: 0;
}
.dh-lp-top-brand-note{
  color: rgba(208, 231, 223, 0.84);
  font-size: 1.05rem;
  font-weight: 500;
  line-height: 1.4;
  max-width: 440px;
  text-align: center;
}
.dh-lp-hero-stage{
  position: relative;
  margin: 10px auto 16px auto;
  padding: 18px 16px 4px 16px;
  text-align: center;
}
.dh-lp-hero-stage::before{
  content: "";
  position: absolute;
  inset: 0;
  background:
    radial-gradient(circle at 50% 0%, rgba(47, 212, 160, 0.12), transparent 42%),
    radial-gradient(circle at 20% 18%, rgba(9, 190, 255, 0.05), transparent 34%);
  pointer-events: none;
}
.dh-lp-hero-stage > *{
  position: relative;
  z-index: 1;
}
.dh-lp-hero-stage-logo{
  display: flex;
  align-items: center;
  justify-content: center;
  margin: 0 auto 6px auto;
}
.dh-lp-hero-stage .dh-lp-header-logo{
  width: min(100%, 620px);
  max-width: 620px;
  max-height: 226px;
}
.dh-lp-hero-stage-badge{
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-height: 34px;
  padding: 0 14px;
  border-radius: 999px;
  border: 1px solid rgba(132, 238, 204, 0.34);
  background: rgba(9, 27, 35, 0.48);
  color: rgba(217, 249, 236, 0.94);
  font-size: 0.82rem;
  font-weight: 700;
  letter-spacing: 0.03em;
  text-transform: uppercase;
}
.dh-lp-hero-stage-title{
  margin: 14px auto 10px auto;
  max-width: 14.5ch;
  color: #f9fcff;
  font-size: clamp(2.2rem, 3.6vw, 3.65rem);
  font-weight: 900;
  line-height: 1.04;
  letter-spacing: -0.035em;
  text-wrap: balance;
  text-shadow: 0 8px 24px rgba(0, 0, 0, 0.26);
}
.dh-lp-hero-stage-sub{
  margin: 0 auto;
  max-width: 62ch;
  color: rgba(220, 238, 232, 0.90);
  font-size: 1.03rem;
  line-height: 1.66;
}
.dh-lp-hero-stage-actions{
  margin-top: 18px;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 12px;
  flex-wrap: wrap;
}
.dh-lp-hero-stage-primary,
.dh-lp-hero-stage-secondary{
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-height: 52px;
  padding: 0 24px;
  border-radius: 999px;
  text-decoration: none !important;
  font-size: 0.98rem;
  font-weight: 820;
  letter-spacing: 0.01em;
  transition: transform 0.2s ease, box-shadow 0.2s ease, filter 0.2s ease;
}
.dh-lp-hero-stage-primary{
  border: 1px solid rgba(126, 255, 198, 0.66);
  background: linear-gradient(180deg, rgba(7, 27, 38, 0.94), rgba(6, 24, 34, 0.90));
  color: #ecfff5 !important;
  box-shadow: 0 0 14px rgba(0, 255, 150, 0.15), 0 12px 24px rgba(0, 0, 0, 0.24);
}
.dh-lp-hero-stage-secondary{
  border: 1px solid rgba(171, 221, 205, 0.22);
  background: rgba(9, 24, 36, 0.56);
  color: rgba(232, 244, 239, 0.96) !important;
  box-shadow: 0 10px 22px rgba(0, 0, 0, 0.16);
}
.dh-lp-hero-stage-primary:hover,
.dh-lp-hero-stage-secondary:hover{
  transform: translateY(-2px);
  filter: brightness(1.04);
}
.dh-lp-hero{
  display: grid;
  grid-template-columns: minmax(0, 1.12fr) minmax(300px, 0.88fr);
  gap: 18px;
  align-items: stretch;
}
.dh-lp-hero-left{
  padding: 28px 30px;
  display: flex;
  flex-direction: column;
  justify-content: center;
  gap: 10px;
  position: relative;
  overflow: hidden;
  background:
    linear-gradient(135deg, rgba(6, 16, 29, 0.88), rgba(6, 18, 28, 0.84)),
    radial-gradient(circle at 18% 26%, rgba(45, 188, 140, 0.10), transparent 54%);
}
.dh-lp-hero-left::before{
  content: "";
  position: absolute;
  inset: 0;
  background: url("__HERO_COL_BG__") right center / cover no-repeat;
  opacity: 0.10;
  filter: saturate(1.05) contrast(0.92);
  pointer-events: none;
}
.dh-lp-hero-left::after{
  content: "";
  position: absolute;
  inset: 0;
  background:
    linear-gradient(180deg, rgba(4, 12, 22, 0.42), rgba(4, 12, 22, 0.52)),
    radial-gradient(circle at 80% 22%, rgba(3, 9, 18, 0.06), transparent 52%);
  pointer-events: none;
}
.dh-lp-hero-left > *{
  position: relative;
  z-index: 1;
}
.dh-lp-hero-badge{
  align-self: flex-start;
  padding: 6px 12px;
  border-radius: 999px;
  border: 1px solid rgba(132, 238, 204, 0.38);
  background: rgba(9, 27, 35, 0.55);
  color: rgba(217, 249, 236, 0.95);
  font-size: 0.78rem;
  font-weight: 760;
  letter-spacing: 0.03em;
  text-transform: uppercase;
}
.dh-lp-hero-title-box{
  width: 100%;
  max-width: none;
  align-self: stretch;
  padding: 0;
  border-radius: 0;
  border: none;
  background: transparent;
  backdrop-filter: blur(4px);
  -webkit-backdrop-filter: blur(4px);
  box-shadow: none;
}
.dh-lp-hero-left h1{
  margin: 0;
  font-size: clamp(2.02rem, 2.45vw, 2.72rem);
  line-height: 1.08;
  font-weight: 880;
  letter-spacing: -0.028em;
  color: #f8fcff;
  max-width: 16.5ch;
  margin-left: 0;
  margin-right: 0;
  text-align: left;
  text-wrap: balance;
  text-shadow: 0 2px 10px rgba(0, 0, 0, 0.24);
}
.dh-lp-hero-left .dh-lp-sub{
  margin-top: 2px;
  max-width: 52ch;
  font-size: 0.96rem;
  line-height: 1.52;
  color: rgba(221, 238, 232, 0.88);
  margin-left: 0;
  margin-right: 0;
}
.dh-lp-get-started{
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-height: 46px;
  padding: 0 22px;
  border-radius: 999px;
  border: 1px solid rgba(126, 255, 198, 0.66);
  color: #ecfff5 !important;
  text-decoration: none !important;
  font-size: 0.9rem;
  font-weight: 800;
  letter-spacing: 0.01em;
  background: linear-gradient(180deg, rgba(7, 27, 38, 0.94), rgba(6, 24, 34, 0.90));
  box-shadow: 0 0 14px rgba(0, 255, 150, 0.15), 0 12px 24px rgba(0, 0, 0, 0.24);
  transition: transform 0.2s ease, filter 0.2s ease, box-shadow 0.2s ease;
  width: 100%;
}
.dh-lp-get-started:hover{
  filter: brightness(1.07) saturate(1.02);
  transform: translateY(-2px);
  box-shadow: 0 0 18px rgba(0, 255, 150, 0.20), 0 15px 28px rgba(0, 0, 0, 0.30);
}
.dh-lp-hero-left .dh-lp-hero-stage-actions{
  justify-content: flex-start;
  margin-top: 2px;
}
.dh-lp-hero-left .dh-lp-get-started,
.dh-lp-hero-left .dh-lp-hero-stage-secondary{
  width: auto;
  min-width: 168px;
}
.dh-lp-hero-brand{
  padding: 18px 18px 16px 18px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 10px;
  position: relative;
  overflow: hidden;
  background:
    radial-gradient(circle at 50% 24%, rgba(74, 238, 183, 0.16), transparent 36%),
    radial-gradient(circle at 84% 16%, rgba(26, 175, 255, 0.10), transparent 28%),
    linear-gradient(180deg, rgba(7, 18, 29, 0.82), rgba(8, 22, 33, 0.66));
}
.dh-lp-hero-brand::before{
  content: "";
  position: absolute;
  inset: 12% 14%;
  border-radius: 24px;
  border: 1px solid rgba(175, 241, 218, 0.12);
  background: radial-gradient(circle at 50% 50%, rgba(255,255,255,0.03), transparent 62%);
  pointer-events: none;
}
.dh-lp-hero-brand > *{
  position: relative;
  z-index: 1;
}
.dh-lp-hero-brand-logo{
  display: flex;
  align-items: center;
  justify-content: center;
  width: 100%;
}
.dh-lp-hero-brand-logo .dh-lp-header-logo{
  width: min(100%, 320px);
  max-width: 320px;
  max-height: 156px;
}
.dh-lp-hero-brand-note{
  margin: 0;
  max-width: 26ch;
  color: rgba(221, 238, 232, 0.82);
  font-size: 0.88rem;
  line-height: 1.42;
  text-align: center;
}
.dh-lp-hero-brand-chips{
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: center;
  gap: 8px;
}
.dh-lp-hero-brand-chip{
  display: inline-flex;
  align-items: center;
  min-height: 30px;
  padding: 0 10px;
  border-radius: 999px;
  border: 1px solid rgba(167, 232, 208, 0.22);
  background: rgba(8, 22, 33, 0.40);
  color: rgba(227, 245, 236, 0.90);
  font-size: 0.76rem;
  font-weight: 700;
}
.dh-lp-benefits{
  margin-top: 6px;
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 9px;
}
.dh-lp-benefit{
  display: flex;
  align-items: center;
  justify-content: flex-start;
  gap: 8px;
  min-height: 44px;
  padding: 8px 10px;
  border-radius: 12px;
  border: 1px solid rgba(167, 232, 208, 0.22);
  background: rgba(8, 22, 33, 0.40);
  color: rgba(227, 245, 236, 0.92);
  font-size: 0.84rem;
  font-weight: 650;
  text-align: left;
}
.dh-lp-benefit-icon{
  width: 24px;
  height: 24px;
  min-width: 24px;
  border-radius: 8px;
  border: 1px solid rgba(162, 236, 207, 0.28);
  background: rgba(7, 20, 30, 0.56);
  display: inline-flex;
  align-items: center;
  justify-content: center;
}
.dh-lp-benefit-icon svg{
  width: 14px;
  height: 14px;
  stroke: rgba(183, 255, 224, 0.94);
  stroke-width: 1.8;
  fill: none;
  stroke-linecap: round;
  stroke-linejoin: round;
}
.dh-lp-benefit-label{
  line-height: 1.3;
}
.dh-lp-social{
  padding: 28px 24px;
  display: flex;
  flex-direction: column;
  justify-content: flex-start;
  gap: 14px;
}
.dh-lp-social-badge{
  align-self: flex-start;
  padding: 7px 12px;
  border-radius: 999px;
  border: 1px solid rgba(165, 234, 210, 0.30);
  background: rgba(8, 24, 34, 0.40);
  color: rgba(210, 245, 232, 0.92);
  font-size: 0.78rem;
  font-weight: 700;
  letter-spacing: 0.02em;
  text-transform: none;
}
.dh-lp-social h3{
  margin: 0;
  font-size: clamp(1.7rem, 2.2vw, 2.1rem);
  font-weight: 780;
  line-height: 1.18;
  letter-spacing: -0.01em;
  color: rgba(244, 251, 255, 0.96);
  max-width: 17ch;
}
.dh-lp-social-note{
  margin: 0;
  color: rgba(210, 230, 222, 0.88);
  font-size: 0.98rem;
  line-height: 1.58;
  max-width: 46ch;
}
.dh-lp-social-grid{
  margin-top: 2px;
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
}
.dh-lp-module-card{
  border-radius: 14px;
  border: 1px solid rgba(185, 244, 225, 0.22);
  background: rgba(8, 22, 33, 0.44);
  min-height: 112px;
  padding: 12px 12px;
  display: flex;
  flex-direction: column;
  justify-content: flex-start;
  gap: 8px;
}
.dh-lp-module-head{
  display: flex;
  align-items: center;
  gap: 9px;
}
.dh-lp-module-icon{
  width: 30px;
  height: 30px;
  min-width: 30px;
  border-radius: 9px;
  border: 1px solid rgba(153, 236, 206, 0.30);
  background: rgba(7, 20, 30, 0.52);
  display: inline-flex;
  align-items: center;
  justify-content: center;
}
.dh-lp-module-icon svg{
  width: 17px;
  height: 17px;
  stroke: rgba(183, 255, 224, 0.94);
  stroke-width: 1.8;
  fill: none;
  stroke-linecap: round;
  stroke-linejoin: round;
}
.dh-lp-module-title{
  margin: 0;
  color: rgba(238, 248, 243, 0.96);
  font-size: 0.94rem;
  font-weight: 720;
  line-height: 1.34;
}
.dh-lp-module-desc{
  margin: 0;
  color: rgba(198, 224, 214, 0.84);
  font-size: 0.84rem;
  line-height: 1.45;
  padding-left: 2px;
}
.dh-lp-social-footer{
  margin: 4px 0 0 0;
  color: rgba(192, 218, 210, 0.78);
  font-size: 0.84rem;
  line-height: 1.45;
  font-weight: 520;
  letter-spacing: 0.01em;
}
.dh-lp-main-grid{
  margin-top: 18px;
  display: grid;
  grid-template-columns: minmax(0, 1.18fr) minmax(0, 1.06fr);
  gap: 18px;
  align-items: stretch;
}
.dh-lp-features{
  padding: 14px 14px 16px 14px;
  height: 100%;
  display: flex;
  flex-direction: column;
}
.dh-lp-section-title{
  margin: 0 0 12px 0;
  font-size: 1.52rem;
  font-weight: 900;
  color: #f5fbff;
}
.dh-lp-features-grid{
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 9px;
  flex: 1 1 auto;
}
.dh-lp-feature-card{
  border-radius: 14px;
  border: 1px solid rgba(173, 240, 215, 0.24);
  background: rgba(7, 18, 30, 0.52);
  padding: 10px;
  min-height: 294px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.dh-lp-feature-card h4{
  margin: 0;
  font-size: 1.04rem;
  font-weight: 850;
  line-height: 1.18;
}
.dh-lp-feature-img-wrap{
  margin: 2px 0 4px 0;
  border-radius: 12px;
  border: 1px solid rgba(168, 236, 211, 0.22);
  background: rgba(8, 24, 32, 0.46);
  min-height: 128px;
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
}
.dh-lp-feature-img-wrap img{
  width: 90%;
  max-height: 120px;
  object-fit: contain;
  filter: drop-shadow(0 10px 18px rgba(0,0,0,0.34));
}
.dh-lp-checklist{
  margin: 0;
  padding: 0;
  list-style: none;
  display: grid;
  gap: 5px;
}
.dh-lp-checklist li{
  color: rgba(225, 245, 235, 0.90);
  font-size: 0.84rem;
  line-height: 1.24;
}
.dh-lp-right{
  display: grid;
  grid-template-rows: minmax(0, auto) minmax(0, 1fr);
  gap: 12px;
  height: 100%;
  align-content: start;
}
.dh-lp-right > *{
  width: 100%;
}
.dh-lp-testimonials{
  padding: 14px 14px 16px 14px;
  min-height: 0;
  height: 100%;
  display: flex;
  flex-direction: column;
}
.dh-lp-testimonials-grid{
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
  align-items: stretch;
  flex: 1 1 auto;
}
.dh-lp-testimonial{
  border-radius: 14px;
  border: 1px solid rgba(177, 241, 218, 0.24);
  background: rgba(8, 22, 33, 0.52);
  padding: 13px 13px 12px 13px;
  min-height: 150px;
  height: 100%;
}
.dh-lp-person{
  display: flex;
  align-items: flex-start;
  gap: 10px;
}
.dh-lp-person img{
  width: 44px;
  height: 44px;
  border-radius: 999px;
  object-fit: cover;
  border: 1px solid rgba(191, 247, 227, 0.35);
}
.dh-lp-person-name{
  margin: 0;
  font-size: 1.02rem;
  font-weight: 900;
}
.dh-lp-person-role{
  margin: 2px 0 0 0;
  font-size: 0.8rem;
  color: rgba(205, 228, 220, 0.72);
}
.dh-lp-testimonial p{
  margin: 8px 0 0 0;
  font-size: 0.92rem;
  color: rgba(215, 236, 227, 0.90);
  line-height: 1.42;
}
.dh-lp-virtual-card{
  border-radius: 16px;
  border-radius: 16px;
  border: 1px solid rgba(176, 239, 215, 0.24);
  background:
    radial-gradient(circle at 16% 16%, rgba(76, 235, 182, 0.14), transparent 34%),
    linear-gradient(180deg, rgba(8, 22, 33, 0.66), rgba(7, 18, 29, 0.58));
  padding: 16px 16px 16px 16px;
  box-shadow: 0 0 20px rgba(0, 255, 150, 0.18), 0 18px 34px rgba(0,0,0,0.22);
  min-height: 0;
}
.dh-lp-virtual-card-inner{
  display: grid;
  grid-template-columns: minmax(116px, 142px) minmax(0, 1fr);
  gap: 16px;
  align-items: start;
}
.dh-lp-virtual-media{
  border-radius: 14px;
  border: 1px solid rgba(168, 236, 211, 0.22);
  background: rgba(8, 24, 32, 0.46);
  min-height: 132px;
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
}
.dh-lp-virtual-media img{
  width: 94%;
  max-height: 122px;
  object-fit: contain;
  filter: drop-shadow(0 14px 22px rgba(0,0,0,0.34));
}
.dh-lp-virtual-copy{
  min-width: 0;
  display: grid;
  align-content: start;
}
.dh-lp-virtual-kicker{
  margin: 0 0 8px 0;
  display: inline-flex;
  align-items: center;
  padding: 5px 11px;
  border-radius: 999px;
  border: 1px solid rgba(130, 245, 197, 0.28);
  background: rgba(10, 27, 36, 0.56);
  color: rgba(221, 255, 241, 0.92);
  font-size: 0.74rem;
  font-weight: 760;
  letter-spacing: 0.03em;
  text-transform: uppercase;
}
.dh-lp-virtual-card h4{
  margin: 0;
  color: #f4fbff;
  font-size: 1.22rem;
  font-weight: 900;
  line-height: 1.12;
  letter-spacing: -0.02em;
}
.dh-lp-virtual-note{
  margin: 0;
  color: rgba(211, 232, 224, 0.92);
  font-size: 0.88rem;
  line-height: 1.46;
}
.dh-lp-virtual-list{
  margin: 12px 0 0 0;
  padding: 0;
  list-style: none;
  display: grid;
  gap: 6px;
}
.dh-lp-virtual-list li{
  color: rgba(228, 246, 238, 0.94);
  font-size: 0.85rem;
  line-height: 1.34;
}
.dh-lp-virtual-list strong{
  color: #f8feff;
  font-weight: 820;
}
.dh-lp-virtual-access-intro{
  margin-top: 16px;
  padding: 24px 26px;
}
.dh-lp-virtual-access-kicker,
.dh-lp-virtual-access-mini{
  display: inline-flex;
  align-items: center;
  padding: 6px 12px;
  border-radius: 999px;
  border: 1px solid rgba(130, 245, 197, 0.24);
  background: rgba(10, 27, 36, 0.56);
  color: rgba(221, 255, 241, 0.92);
  font-size: 0.74rem;
  font-weight: 760;
  letter-spacing: 0.03em;
  text-transform: uppercase;
}
.dh-lp-virtual-access-note{
  margin: 10px 0 0 0;
  color: rgba(215, 236, 227, 0.92);
  font-size: 0.98rem;
  line-height: 1.62;
}
.dh-lp-virtual-access-copy{
  height: 100%;
  border-radius: 22px;
  border: 1px solid rgba(176, 239, 215, 0.20);
  background:
    radial-gradient(circle at 12% 18%, rgba(76, 235, 182, 0.10), transparent 34%),
    linear-gradient(180deg, rgba(8, 22, 33, 0.70), rgba(7, 18, 29, 0.64));
  padding: 24px 24px 22px 24px;
  box-shadow: 0 18px 34px rgba(0,0,0,0.18);
}
.dh-lp-virtual-access-copy h4{
  margin: 16px 0 10px 0;
  color: #f4fbff;
  font-size: 1.68rem;
  font-weight: 880;
  line-height: 1.12;
  letter-spacing: -0.02em;
}
.dh-lp-virtual-access-list{
  margin: 0;
  padding-left: 1.1rem;
  color: rgba(225, 244, 238, 0.94);
  display: grid;
  gap: 9px;
  line-height: 1.5;
  font-size: 0.95rem;
}
.dh-lp-virtual-login-head h4{
  margin: 0 0 6px 0;
  color: #f7fdff;
  font-size: 1.34rem;
  font-weight: 860;
}
.dh-lp-virtual-login-head p{
  margin: 0 0 16px 0;
  color: rgba(213, 234, 226, 0.88);
  font-size: 0.93rem;
}
.dh-lp-pricing{
  margin-top: 14px;
  padding: 16px 18px;
}
.dh-lp-pricing-grid{
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 18px;
  align-items: stretch;
}
.dh-lp-pricing-grid-single{
  grid-template-columns: minmax(0, 1fr);
  max-width: 920px;
  margin: 0 auto;
}
.dh-lp-plan{
  border-radius: 16px;
  border: 1px solid rgba(176, 239, 215, 0.28);
  background: rgba(8, 22, 32, 0.54);
  min-width: 0;
  padding: 16px 16px 14px 16px;
}
.dh-lp-plan h4{
  margin: 0 0 8px 0;
  font-size: 1.34rem;
  font-weight: 840;
  letter-spacing: 0.01em;
  line-height: 1.18;
  font-family: "Montserrat", "Inter", "Segoe UI", sans-serif;
}
.dh-lp-price{
  margin: 2px 0 10px 0;
  color: #78ffc5;
  display: flex;
  align-items: flex-end;
  gap: 8px;
  flex-wrap: nowrap;
  white-space: nowrap;
  font-size: clamp(2.25rem, 3.6vw, 3rem);
  line-height: 1;
  font-weight: 900;
  letter-spacing: -0.015em;
  text-shadow: 0 6px 20px rgba(0, 0, 0, 0.25);
}
.dh-lp-price span{
  flex: 0 0 auto;
  font-size: 0.42em;
  font-weight: 760;
  color: rgba(209, 255, 233, 0.92);
}
.dh-lp-plan ul{
  margin: 0;
  padding-left: 18px;
  display: grid;
  gap: 7px;
}
.dh-lp-plan li{
  color: rgba(221, 242, 232, 0.93);
  font-size: 0.9rem;
  line-height: 1.42;
}
.dh-lp-plan-premium-main{
  box-shadow: 0 0 22px rgba(0, 255, 150, 0.16), 0 16px 28px rgba(0, 0, 0, 0.30);
}
.dh-lp-plan-kicker{
  margin: 0 0 8px 0;
  font-size: 0.78rem;
  color: rgba(185, 241, 216, 0.90);
  letter-spacing: 0.03em;
  text-transform: uppercase;
  font-weight: 700;
}
.dh-lp-pay-title{
  margin: 12px 0 8px 0;
  font-size: 0.84rem;
  color: rgba(210, 236, 226, 0.92);
  font-weight: 760;
}
.dh-lp-pay-methods{
  gap: 8px !important;
}
.dh-lp-pay-chip{
  min-height: 34px !important;
  padding: 0 12px !important;
  font-size: 0.8rem !important;
}
.dh-lp-plan-cta{
  margin-top: 12px !important;
  min-height: 44px !important;
  font-size: 0.9rem !important;
  letter-spacing: 0.01em !important;
}
.dh-lp-virtual-tail{
  margin-top: 18px;
  padding: 16px 18px;
}
.dh-lp-virtual-tail-shell{
  display: grid;
  grid-template-columns: minmax(0, 1.08fr) minmax(300px, 0.92fr);
  gap: 14px;
  align-items: stretch;
}
.dh-lp-virtual-tail-copy{
  border-radius: 16px;
  border: 1px solid rgba(176, 239, 215, 0.14);
  background: rgba(8, 22, 32, 0.30);
  padding: 16px 16px 14px 16px;
}
.dh-lp-virtual-tail-kicker{
  display: inline-flex;
  align-items: center;
  min-height: 28px;
  padding: 0 10px;
  border-radius: 999px;
  border: 1px solid rgba(130, 245, 197, 0.18);
  background: rgba(10, 27, 36, 0.42);
  color: rgba(221, 255, 241, 0.84);
  font-size: 0.72rem;
  font-weight: 740;
  letter-spacing: 0.03em;
  text-transform: uppercase;
}
.dh-lp-virtual-tail-copy h4{
  margin: 10px 0 8px 0;
  color: #f4fbff;
  font-size: 1.18rem;
  font-weight: 840;
  line-height: 1.18;
}
.dh-lp-virtual-tail-copy p{
  margin: 0;
  color: rgba(211, 232, 224, 0.86);
  font-size: 0.9rem;
  line-height: 1.5;
}
.dh-lp-virtual-tail-list{
  margin: 12px 0 0 0;
  padding-left: 1rem;
  color: rgba(228, 246, 238, 0.9);
  font-size: 0.88rem;
  line-height: 1.45;
  display: grid;
  gap: 6px;
}
.dh-lp-virtual-tail-login-head h4{
  margin: 0 0 5px 0;
  color: #f4fbff;
  font-size: 1.08rem;
  font-weight: 820;
}
.dh-lp-virtual-tail-login-head p{
  margin: 0 0 12px 0;
  color: rgba(211, 232, 224, 0.78);
  font-size: 0.86rem;
  line-height: 1.45;
}
.dh-lp-pay-methods{
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
}
.dh-lp-pay-chip{
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-height: 38px;
  padding: 8px 12px;
  border-radius: 10px;
  border: 1px solid rgba(176, 239, 215, 0.34);
  background: rgba(6, 20, 32, 0.60);
  color: #dcfff0 !important;
  text-decoration: none !important;
  font-size: 0.86rem;
  font-weight: 760;
}
.dh-lp-plan-cta{
  margin-top: 16px;
  display: inline-flex;
  width: 100%;
  align-items: center;
  justify-content: center;
  min-height: 48px;
  border-radius: 12px;
  border: 1px solid rgba(115, 255, 190, 0.70);
  background: linear-gradient(180deg, rgba(11, 45, 58, 0.95), rgba(8, 32, 44, 0.90));
  color: #ebfff6 !important;
  text-decoration: none !important;
  font-size: 1rem;
  font-weight: 820;
  letter-spacing: 0.01em;
  box-shadow: 0 0 18px rgba(0, 255, 150, 0.23);
  transition: transform 0.2s ease, filter 0.2s ease, box-shadow 0.2s ease;
}
.dh-lp-plan-cta:hover{
  transform: translateY(-1px);
  filter: brightness(1.08);
  box-shadow: 0 0 22px rgba(0, 255, 150, 0.28);
}
@media (max-width: 720px){
  .dh-lp-pricing{
    padding: 18px 16px;
  }
  .dh-lp-pricing-grid{
    grid-template-columns: 1fr;
    gap: 14px;
  }
  .dh-lp-plan{
    padding: 18px 16px;
  }
  .dh-lp-pay-methods{
    grid-template-columns: 1fr;
  }
}
@media (max-width: 1360px){
  .dh-lp-pricing-grid{
    grid-template-columns: 1fr;
  }
}
@media (max-width: 1200px){
  .dh-lp-main-grid{
    grid-template-columns: 1fr;
  }
  .dh-lp-features-grid{
    grid-template-columns: 1fr;
  }
  .dh-lp-testimonials-grid{
    grid-template-columns: 1fr;
  }
  .dh-lp-right{
    gap: 14px;
  }
  .dh-lp-virtual-card-inner{
    grid-template-columns: 1fr;
  }
  .dh-lp-virtual-media{
    min-height: 148px;
  }
}
@media (max-width: 980px){
  .dh-lp-hero{
    grid-template-columns: 1fr;
  }
  .dh-lp-hero-left,
  .dh-lp-hero-brand{
    padding: 24px 22px;
  }
  .dh-lp-virtual-tail-shell{
    grid-template-columns: 1fr;
  }
  .dh-lp-hero-left h1{
    max-width: 100%;
  }
  .dh-lp-benefits{
    grid-template-columns: 1fr 1fr;
  }
  .dh-lp-hero-brand-logo .dh-lp-header-logo{
    width: min(100%, 380px);
    max-height: 176px;
  }
}
@media (max-width: 720px){
  .dh-lp-top-brand{
    justify-content: center;
  }
  .dh-lp-top-brand-logo{
    width: 48px;
    height: 48px;
  }
  .dh-lp-hero-left .dh-lp-hero-stage-actions{
    justify-content: center;
  }
  .dh-lp-hero-left .dh-lp-get-started,
  .dh-lp-hero-left .dh-lp-hero-stage-secondary{
    width: 100%;
    max-width: none;
    min-width: 0;
  }
  .dh-lp-hero-left h1{
    font-size: clamp(1.95rem, 8vw, 2.55rem);
    line-height: 1.08;
  }
  .dh-lp-hero-left .dh-lp-sub{
    font-size: 0.95rem;
  }
  .dh-lp-virtual-tail{
    padding: 14px 14px;
  }
  .dh-lp-virtual-tail-copy{
    padding: 14px 14px 12px 14px;
  }
  .dh-lp-hero-brand-logo .dh-lp-header-logo{
    width: min(100%, 320px);
    max-height: 144px;
  }
  .dh-lp-benefits,
  .dh-lp-social-grid{
    grid-template-columns: 1fr;
  }
  .dh-lp-module-card{
    min-height: auto;
    padding: 11px 11px;
  }
  .dh-lp-social h3{
    max-width: 100%;
  }
  .dh-lp-get-started{
    width: 100%;
  }
}
@media (max-width: 1100px){
  .dh-top-logo-img{
    width: min(100%, 460px);
    max-width: 460px;
    max-height: 170px;
  }
}
@media (max-width: 900px){
  .dh-top-logo-img{
    width: min(100%, 360px);
    max-width: 360px;
    max-height: 145px;
  }
  .dh-lead-card{
    min-height: auto;
  }
  .dh-lead-list{
    grid-template-columns: 1fr;
    gap: 8px;
  }
  .dh-landing-cta-strip img{
    height: 50px;
  }
  .dh-landing-avatar{
    width: min(100%, 170px);
  }
}

/* Isolated landing refresh */
html body::after,
body::after{
  content: none !important;
  display: none !important;
}
.dhx-shell{
  max-width: 1280px;
  margin: 0 auto;
  padding: 0 24px 24px 24px;
  color: #f4fbff;
}
.dhx-panel{
  position: relative;
  overflow: hidden;
  border-radius: 28px;
  border: 1px solid rgba(123, 244, 202, 0.12);
  background:
    linear-gradient(180deg, rgba(5, 15, 25, 0.96), rgba(5, 14, 24, 0.9)),
    radial-gradient(circle at top right, rgba(51, 214, 165, 0.08), transparent 36%);
  box-shadow:
    0 22px 46px rgba(0, 0, 0, 0.3),
    inset 0 1px 0 rgba(255, 255, 255, 0.05);
}
.dhx-panel,
.dhx-feature-card,
.dhx-quote-card,
.dhx-pricing,
.dhx-metric,
.dhx-stack-card,
.dhx-pay-chip{
  transition: transform 0.2s ease, box-shadow 0.2s ease;
}
.dhx-panel:hover,
.dhx-feature-card:hover,
.dhx-quote-card:hover,
.dhx-pricing:hover,
.dhx-metric:hover,
.dhx-stack-card:hover{
  transform: translateY(-4px);
  box-shadow:
    0 28px 58px rgba(0, 0, 0, 0.34),
    inset 0 1px 0 rgba(255, 255, 255, 0.05);
}
.dhx-pay-chip:hover{
  transform: translateY(-2px);
  box-shadow: 0 14px 30px rgba(0, 0, 0, 0.28);
}
.dhx-panel::before{
  content: "";
  position: absolute;
  inset: 0;
  background:
    radial-gradient(circle at 14% 16%, rgba(49, 231, 174, 0.08), transparent 30%),
    radial-gradient(circle at 82% 78%, rgba(20, 169, 255, 0.06), transparent 28%);
  pointer-events: none;
}
.dhx-panel > *{
  position: relative;
  z-index: 1;
}
.dhx-hero-grid{
  display: grid;
  grid-template-columns: minmax(0, 1.2fr) minmax(0, 0.8fr);
  gap: 28px;
  align-items: stretch;
}
.dhx-hero-main{
  min-height: 560px;
  padding: 44px 46px;
}
.dhx-kicker{
  display: inline-flex;
  align-items: center;
  min-height: 36px;
  padding: 0 16px;
  border-radius: 999px;
  border: 1px solid rgba(133, 245, 205, 0.28);
  background: rgba(8, 27, 36, 0.52);
  color: #dffcef;
  font-size: 0.8rem;
  font-weight: 700;
  letter-spacing: 0.02em;
  text-transform: uppercase;
}
.dhx-title{
  margin: 24px 0 24px 0;
  max-width: 19ch;
  color: #f7fbff;
  font-size: clamp(3.65rem, 4.4vw, 4.5rem);
  line-height: 1.05;
  font-weight: 800;
  letter-spacing: -0.035em;
  text-wrap: balance;
  text-shadow: 0 12px 30px rgba(0, 0, 0, 0.28);
}
.dhx-sub{
  max-width: 60ch;
  margin: 0 0 30px 0;
  color: rgba(215, 231, 225, 0.9);
  font-size: 1.4rem;
  line-height: 1.55;
}
.dhx-actions{
  margin-top: 0;
  display: flex;
  gap: 14px;
  flex-wrap: wrap;
}
.dhx-btn-primary,
.dhx-btn-secondary{
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-height: 54px;
  padding: 0 24px;
  border-radius: 18px;
  text-decoration: none !important;
  font-size: 1.05rem;
  font-weight: 700;
  letter-spacing: 0.01em;
  transition: transform 0.2s ease, filter 0.2s ease, box-shadow 0.2s ease;
}
.dhx-btn-primary{
  border: 1px solid rgba(126, 255, 198, 0.52);
  background: linear-gradient(180deg, rgba(10, 46, 58, 0.96), rgba(8, 34, 45, 0.92));
  color: #edfff6 !important;
  box-shadow: 0 18px 30px rgba(0, 0, 0, 0.22), 0 0 18px rgba(0, 255, 150, 0.14);
}
.dhx-btn-secondary{
  border: 1px solid rgba(156, 192, 211, 0.2);
  background: rgba(10, 23, 36, 0.56);
  color: #edf4f7 !important;
}
.dh-pwa-inline{
  min-height: 46px;
  padding: 0 18px;
  font-size: 0.96rem;
  border-radius: 16px;
  opacity: 0.92;
}
.dhx-btn-primary:hover,
.dhx-btn-secondary:hover{
  transform: translateY(-2px);
  filter: brightness(1.05);
}
.dhx-metrics{
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 14px;
  margin-top: 30px;
}
.dhx-metric{
  min-height: 120px;
  padding: 18px 18px 16px 18px;
  border-radius: 18px;
  border: 1px solid rgba(174, 241, 217, 0.14);
  background: rgba(7, 20, 31, 0.5);
  display: grid;
  align-content: space-between;
  gap: 8px;
}
.dhx-metric strong{
  color: #f8fdff;
  font-size: 1rem;
  font-weight: 700;
  line-height: 1.2;
}
.dhx-metric span{
  color: rgba(201, 223, 218, 0.82);
  font-size: 0.82rem;
  line-height: 1.45;
}
.dhx-side{
  min-height: 560px;
  padding: 32px 32px 28px 32px;
  display: grid;
  gap: 16px;
  align-content: start;
}
.dhx-side-top{
  display: grid;
  gap: 10px;
}
.dhx-brand-badge{
  display: inline-flex;
  align-items: center;
  min-height: 32px;
  padding: 0 13px;
  border-radius: 999px;
  border: 1px solid rgba(129, 239, 199, 0.16);
  background: rgba(7, 24, 34, 0.48);
  color: rgba(215, 251, 239, 0.88);
  font-size: 0.75rem;
  font-weight: 700;
  letter-spacing: 0.03em;
  text-transform: uppercase;
}
.dhx-side-logo{
  display: flex;
  align-items: center;
  justify-content: center;
}
.dhx-side-logo img{
  width: min(100%, 240px);
  max-width: 240px;
  max-height: 160px;
  object-fit: contain;
  filter: drop-shadow(0 16px 26px rgba(0, 0, 0, 0.26));
}
.dhx-side-logo-text{
  color: #f6fbff;
  font-size: 1.45rem;
  font-weight: 900;
  letter-spacing: -0.03em;
}
.dhx-side-note{
  margin: 0;
  color: rgba(214, 232, 226, 0.86);
  font-size: 1rem;
  line-height: 1.6;
}
.dhx-stack{
  display: grid;
  gap: 12px;
}
.dhx-stack-card{
  display: grid;
  grid-template-columns: 52px minmax(0, 1fr);
  gap: 12px;
  padding: 16px 16px;
  border-radius: 16px;
  border: 1px solid rgba(171, 233, 210, 0.12);
  background: rgba(7, 20, 31, 0.48);
  min-height: 82px;
}
.dhx-stack-media{
  min-height: 48px;
  border-radius: 12px;
  border: 1px solid rgba(168, 236, 211, 0.18);
  background: rgba(9, 26, 36, 0.56);
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
}
.dhx-stack-media img{
  width: 80%;
  max-height: 40px;
  object-fit: contain;
  filter: drop-shadow(0 10px 18px rgba(0, 0, 0, 0.34));
}
.dhx-stack-copy strong{
  display: block;
  color: #f7fcff;
  font-size: 0.96rem;
  font-weight: 700;
  line-height: 1.2;
}
.dhx-stack-copy span{
  display: block;
  margin-top: 3px;
  color: rgba(197, 220, 214, 0.84);
  font-size: 0.84rem;
  line-height: 1.4;
}
.dhx-side-chips{
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 18px;
}
.dhx-side-chip{
  display: inline-flex;
  align-items: center;
  min-height: 32px;
  padding: 0 13px;
  border-radius: 999px;
  border: 1px solid rgba(167, 232, 208, 0.18);
  background: rgba(9, 24, 35, 0.4);
  color: rgba(226, 245, 236, 0.88);
  font-size: 0.78rem;
  font-weight: 700;
}
.dhx-main-grid{
  margin-top: 10px;
  display: grid;
  grid-template-columns: minmax(0, 1.08fr) minmax(0, 0.92fr);
  gap: 10px;
  align-items: start;
}
.dhx-section{
  padding: 24px;
}
.dhx-section-header{
  display: grid;
  gap: 6px;
  margin-bottom: 18px;
}
.dhx-section-kicker{
  color: rgba(170, 241, 216, 0.82);
  font-size: 0.76rem;
  font-weight: 800;
  letter-spacing: 0.04em;
  text-transform: uppercase;
}
.dhx-section h3{
  margin: 0;
  color: #f8fbff;
  font-size: clamp(1.9rem, 2.4vw, 2.5rem);
  line-height: 1.03;
  font-weight: 900;
  letter-spacing: -0.035em;
}
.dhx-section p{
  margin: 0;
  color: rgba(205, 223, 217, 0.84);
  font-size: 0.95rem;
  line-height: 1.58;
}
.dhx-feature-grid{
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
}
.dhx-feature-card{
  border-radius: 22px;
  border: 1px solid rgba(177, 241, 218, 0.16);
  background: rgba(7, 20, 31, 0.54);
  padding: 14px;
  display: grid;
  align-content: start;
  gap: 10px;
  min-height: 100%;
}
.dhx-feature-card h4{
  margin: 0;
  color: #f7fcff;
  font-size: 1.08rem;
  font-weight: 840;
  line-height: 1.16;
}
.dhx-feature-media{
  min-height: 156px;
  border-radius: 18px;
  border: 1px solid rgba(168, 236, 211, 0.18);
  background: linear-gradient(180deg, rgba(7, 22, 34, 0.68), rgba(6, 18, 29, 0.58));
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
}
.dhx-feature-media img{
  width: 86%;
  max-height: 136px;
  object-fit: contain;
  filter: drop-shadow(0 12px 20px rgba(0, 0, 0, 0.3));
}
.dhx-feature-list{
  margin: 0;
  padding-left: 1rem;
  color: rgba(223, 241, 234, 0.9);
  display: grid;
  gap: 7px;
  font-size: 0.88rem;
  line-height: 1.42;
}
.dhx-right-rail{
  display: grid;
  gap: 18px;
}
.dhx-quote-list{
  display: grid;
  gap: 12px;
}
.dhx-quote-card{
  border-radius: 22px;
  border: 1px solid rgba(177, 241, 218, 0.16);
  background: rgba(7, 20, 31, 0.52);
  padding: 16px;
}
.dhx-quote-head{
  display: flex;
  align-items: center;
  gap: 12px;
}
.dhx-quote-head img{
  width: 48px;
  height: 48px;
  border-radius: 999px;
  object-fit: cover;
  border: 1px solid rgba(194, 247, 228, 0.28);
}
.dhx-quote-name{
  color: #f8fdff;
  font-size: 1rem;
  font-weight: 820;
}
.dhx-quote-role{
  color: rgba(185, 209, 202, 0.72);
  font-size: 0.82rem;
  margin-top: 2px;
}
.dhx-quote-card blockquote{
  margin: 12px 0 0 0;
  padding: 0;
  border: none;
  color: rgba(223, 241, 234, 0.92);
  font-size: 0.96rem;
  line-height: 1.54;
}
.dhx-pricing{
  padding: 22px;
}
.dhx-pricing h3{
  margin: 8px 0 0 0;
  color: #f8fbff;
  font-size: clamp(1.7rem, 2.2vw, 2.1rem);
  line-height: 1.05;
  font-weight: 860;
  letter-spacing: -0.03em;
}
.dhx-price{
  display: flex;
  align-items: flex-end;
  gap: 10px;
  margin: 12px 0 14px 0;
  color: #74ffc4;
  font-size: clamp(3.2rem, 5.3vw, 4.7rem);
  line-height: 0.92;
  font-weight: 900;
  letter-spacing: -0.05em;
}
.dhx-price span{
  color: rgba(218, 255, 239, 0.92);
  font-size: 0.34em;
  font-weight: 760;
  letter-spacing: 0;
}
.dhx-pricing-note{
  margin: 6px 0 10px 0;
  padding: 10px 12px;
  border-radius: 12px;
  border: 1px solid rgba(120, 219, 189, 0.28);
  background: rgba(9, 24, 34, 0.6);
  color: rgba(214, 245, 231, 0.9);
  font-size: 0.88rem;
  line-height: 1.45;
}
.dhx-pricing-list{
  margin: 0;
  padding-left: 1.1rem;
  display: grid;
  gap: 9px;
  color: rgba(223, 241, 234, 0.92);
  font-size: 0.92rem;
  line-height: 1.46;
}
.dhx-pay-grid{
  margin-top: 18px;
  display: grid;
  grid-template-columns: 1fr 1fr 1fr;
  gap: 10px;
}
.dhx-pay-chip{
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-height: 44px;
  border-radius: 14px;
  border: 1px solid rgba(126, 255, 198, 0.22);
  background: rgba(8, 24, 35, 0.5);
  color: #ecfff5 !important;
  text-decoration: none !important;
  font-size: 0.9rem;
  font-weight: 780;
}
.dhx-plan-cta{
  margin-top: 12px;
  display: inline-flex;
  width: 100%;
  align-items: center;
  justify-content: center;
  min-height: 54px;
  border-radius: 16px;
  border: 1px solid rgba(115, 255, 190, 0.64);
  background: linear-gradient(180deg, rgba(11, 45, 58, 0.98), rgba(8, 33, 44, 0.94));
  color: #ecfff5 !important;
  text-decoration: none !important;
  font-size: 1rem;
  font-weight: 840;
  letter-spacing: 0.01em;
  box-shadow: 0 0 18px rgba(0, 255, 150, 0.2);
  transition: transform 0.2s ease, filter 0.2s ease;
}
.dhx-plan-cta:hover{
  transform: translateY(-1px);
  filter: brightness(1.05);
}
@media (max-width: 1180px){
  .dhx-hero-grid,
  .dhx-main-grid{
    grid-template-columns: 1fr;
  }
  .dhx-feature-grid{
    grid-template-columns: 1fr;
  }
  .dhx-metrics{
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
  .dhx-hero-main,
  .dhx-side{
    padding: 32px 34px;
    min-height: auto;
  }
  .dhx-title{
    font-size: clamp(2.9rem, 4.8vw, 3.5rem);
    max-width: 20ch;
  }
  .dhx-sub{
    font-size: 1.15rem;
  }
  .dhx-btn-primary,
  .dhx-btn-secondary{
    min-height: 48px;
    font-size: 0.98rem;
  }
}
@media (max-width: 760px){
  .dhx-shell{
    padding: 8px 18px 24px 18px;
  }
  .dhx-hero-main,
  .dhx-side,
  .dhx-section,
  .dhx-pricing{
    padding: 20px 18px;
  }
  .dhx-title{
    max-width: 100%;
    font-size: clamp(2.15rem, 9vw, 2.6rem);
    line-height: 1.1;
  }
  .dhx-sub{
    font-size: 0.98rem;
    line-height: 1.5;
  }
  .dhx-actions,
  .dhx-pay-grid{
    grid-template-columns: 1fr;
    flex-direction: column;
  }
  .dhx-btn-primary,
  .dhx-btn-secondary{
    width: 100%;
    min-height: 52px;
  }
  .dhx-metrics{
    grid-template-columns: 1fr;
  }
  .dhx-metric{
    min-height: 112px;
  }
  .dhx-stack-card{
    grid-template-columns: 1fr;
  }
  .dhx-stack-media{
    min-height: 82px;
  }
  .dhx-price{
    font-size: clamp(2.6rem, 14vw, 3.6rem);
  }
}

</style>
""".replace("__BG_URL__", bg_url).replace("__TEXTURE_URL__", texture_url).replace("__BTN_ENTER_URL__", enter_btn_url).replace("__BTN_ASSINE_URL__", assine_btn_url).replace("__HERO_COL_BG__", hero_col_bg_url or texture_url)
    st.markdown(css, unsafe_allow_html=True)
    st.markdown(
        """
<style>
.dh-top-logo-wrap,.dh-hero-box,.dh-landing-cta-strip,.dh-landing-avatar,.dh-landing-mockup-wrap,.dh-lead-card,.dh-premium-card{
  display:none !important;
}
</style>
        """,
        unsafe_allow_html=True,
    )

    logo_markup = (
        f'<img class="dh-lp-header-logo" src="{html.escape(logo_url, quote=True)}" alt="DietHealth System Logo"/>'
        if logo_url
        else '<span class="dh-lp-header-logo">🥑</span>'
    )
    robot_markup = (
        f'<img src="{html.escape(robot_icon_url, quote=True)}" alt="Gerador de Dieta IA"/>'
        if robot_icon_url
        else ""
    )
    patient_markup = (
        f'<img src="{html.escape(patient_icon_url, quote=True)}" alt="App do Paciente IA"/>'
        if patient_icon_url
        else ""
    )
    finance_markup = (
        f'<img src="{html.escape(finance_icon_url, quote=True)}" alt="Gestao Financeira"/>'
        if finance_icon_url
        else ""
    )
    profile_a_markup = (
        f'<img src="{html.escape(avatar_url, quote=True)}" alt="Dr. Mariana Costa"/>'
        if avatar_url
        else ""
    )
    virtual_service_markup = (
        f'<img src="{html.escape(avatar_url, quote=True)}" alt="Atendimento Virtual DietHealth"/>'
        if avatar_url
        else ""
    )
    profile_b_markup = (
        f'<img src="{html.escape(patient_profile_url, quote=True)}" alt="Lucas Almeida"/>'
        if patient_profile_url
        else profile_a_markup
    )
    top_logo_markup = (
        f'<img class="dh-lp-top-brand-logo" src="{html.escape(logo_url, quote=True)}" alt="DietHealth System"/>'
        if logo_url
        else '<span class="dh-lp-top-brand-logo">🥑</span>'
    )
    brand_logo_markup = (
        f'<img src="{html.escape(side_brand_logo_url, quote=True)}" alt="DietHealth System"/>'
        if side_brand_logo_url
        else '<span class="dhx-side-logo-text">🥑 DietHealth</span>'
    )
    with st.container(key="lp_access_topbar_wrap"):
        header_brand_col, header_actions_col = st.columns([0.62, 0.38], gap="small", vertical_alignment="center")
        with header_brand_col:
            with st.container(key="lp_access_brand_wrap"):
                st.markdown(
                    f"""
                    <div class="dh-lp-top-brand">
                      {top_logo_markup}
                      <div class="dh-lp-top-brand-copy">
                        <div class="dh-lp-top-brand-title">DietHealth System</div>
                        <div class="dh-lp-top-brand-note">Plataforma premium para nutrição inteligente</div>
                      </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
        with header_actions_col:
            with st.container(key="lp_access_actions_wrap"):
                access_bar_cols = st.columns([1, 1], gap="small", vertical_alignment="center")
                with access_bar_cols[0]:
                    with st.container(key="lp_auth_topbar_wrap"):
                        login_slot = st.container()
                with access_bar_cols[1]:
                    with st.container(key="lp_auth_topbar_wrap_register"):
                        register_slot = st.container()

    landing_checkout_url = "#dh-auth-anchor"
    landing_checkout_label = "Cadastre-se para assinar"
    landing_checkout_note = ""
    if not st.session_state.get("logado"):
        landing_checkout_note = (
            "<div class=\"dhx-pricing-note\">Para assinar, crie sua conta ou faça login. "
            "Após o cadastro, o pagamento é liberado automaticamente.</div>"
        )
    st.markdown(
        _html_block(
            f"""
<div class="dhx-shell">
  <section class="dhx-hero-grid">
    <article class="dhx-panel dhx-hero-main">
      <div class="dhx-kicker">Fluxo cl&iacute;nico com IA</div>
      <h1 class="dhx-title">Nutri&ccedil;&atilde;o com mais clareza, presen&ccedil;a e ritmo de opera&ccedil;&atilde;o</h1>
      <p class="dhx-sub">Organize atendimento, prontu&aacute;rio, dietas, agenda e financeiro em uma experi&ecirc;ncia &uacute;nica, com linguagem mais premium e menos atrito operacional no dia a dia do consult&oacute;rio.</p>
      <div class="dhx-actions">
        <a class="dhx-btn-primary" href="#dh-auth-anchor">Entrar e testar</a>
        <a class="dhx-btn-secondary" href="#dh-main-grid-anchor">Ver m&oacute;dulos do sistema</a>
        <button class="dhx-btn-secondary dh-pwa-inline" id="dh-pwa-install-inline" type="button">Instalar app</button>
      </div>
      <div class="dhx-metrics">
        <div class="dhx-metric">
          <strong>Dietas com IA</strong>
          <span>Gera&ccedil;&atilde;o, revis&atilde;o e personaliza&ccedil;&atilde;o por paciente em minutos.</span>
        </div>
        <div class="dhx-metric">
          <strong>Agenda integrada</strong>
          <span>Consultas, retornos e lembretes no mesmo fluxo de atendimento.</span>
        </div>
        <div class="dhx-metric">
          <strong>Prontu&aacute;rio vivo</strong>
          <span>Evolu&ccedil;&atilde;o cl&iacute;nica, relat&oacute;rios e hist&oacute;rico centralizado.</span>
        </div>
        <div class="dhx-metric">
          <strong>Financeiro pr&aacute;tico</strong>
          <span>Receitas, despesas e cobran&ccedil;as com leitura mais executiva.</span>
        </div>
      </div>
    </article>
    <aside class="dhx-panel dhx-side">
      <div class="dhx-side-top">
        <span class="dhx-brand-badge">DietHealth System</span>
        <div class="dhx-side-logo">{brand_logo_markup}</div>
        <p class="dhx-side-note">Uma camada visual mais forte para um software que precisa transmitir organiza&ccedil;&atilde;o, autoridade cl&iacute;nica e agilidade comercial sem parecer gen&eacute;rico.</p>
      </div>
      <div class="dhx-stack">
        <div class="dhx-stack-card">
          <div class="dhx-stack-media">{robot_markup}</div>
          <div class="dhx-stack-copy">
            <strong>Motor de dieta e orienta&ccedil;&atilde;o</strong>
            <span>Planejamento alimentar com apoio de IA, ajustes e exporta&ccedil;&atilde;o em PDF.</span>
          </div>
        </div>
        <div class="dhx-stack-card">
          <div class="dhx-stack-media">{patient_markup}</div>
          <div class="dhx-stack-copy">
            <strong>Vis&atilde;o do paciente</strong>
            <span>Acompanhamento, evolu&ccedil;&atilde;o, rotina de consultas e comunica&ccedil;&atilde;o em um s&oacute; lugar.</span>
          </div>
        </div>
        <div class="dhx-stack-card">
          <div class="dhx-stack-media">{finance_markup}</div>
          <div class="dhx-stack-copy">
            <strong>Gest&atilde;o financeira integrada</strong>
            <span>Fechamento mais claro, cobran&ccedil;as e leitura operacional para o consult&oacute;rio.</span>
          </div>
        </div>
      </div>
      <div class="dhx-side-chips">
        <span class="dhx-side-chip">Dieta inteligente</span>
        <span class="dhx-side-chip">Agenda integrada</span>
        <span class="dhx-side-chip">Relat&oacute;rios cl&iacute;nicos</span>
        <span class="dhx-side-chip">Financeiro unificado</span>
      </div>
    </aside>
  </section>
  <div id="dh-main-grid-anchor"></div>
  <section class="dhx-main-grid">
    <article class="dhx-panel dhx-section">
      <div class="dhx-section-header">
        <span class="dhx-section-kicker">M&oacute;dulos principais</span>
        <h3>Funcionalidades que sustentam a rotina inteira</h3>
        <p>Sem trocar de sistema para cada etapa. O foco aqui &eacute; deixar atendimento, gest&atilde;o e entrega cl&iacute;nica no mesmo circuito.</p>
      </div>
      <div class="dhx-feature-grid">
        <div class="dhx-feature-card">
          <h4>Gerador de Dieta IA</h4>
          <div class="dhx-feature-media">{robot_markup}</div>
          <ul class="dhx-feature-list">
            <li>Planos alimentares personalizados</li>
            <li>Recomenda&ccedil;&otilde;es din&acirc;micas e revis&otilde;es mais r&aacute;pidas</li>
            <li>Balanceamento nutricional automatizado</li>
          </ul>
        </div>
        <div class="dhx-feature-card">
          <h4>App do Paciente IA</h4>
          <div class="dhx-feature-media">{patient_markup}</div>
          <ul class="dhx-feature-list">
            <li>Dashboard e prontu&aacute;rio do paciente</li>
            <li>Agendamento, rotina de acompanhamento e hist&oacute;rico</li>
            <li>Mais clareza na rela&ccedil;&atilde;o entre paciente e nutricionista</li>
          </ul>
        </div>
        <div class="dhx-feature-card">
          <h4>Gest&atilde;o Financeira</h4>
          <div class="dhx-feature-media">{finance_markup}</div>
          <ul class="dhx-feature-list">
            <li>Cobran&ccedil;as e faturas</li>
            <li>Controle de receitas e despesas</li>
            <li>Leitura mensal inteligente da opera&ccedil;&atilde;o</li>
          </ul>
        </div>
      </div>
    </article>
    <div class="dhx-right-rail">
      <article class="dhx-panel dhx-section">
        <div class="dhx-section-header">
          <span class="dhx-section-kicker">Percep&ccedil;&atilde;o de valor</span>
          <h3>O sistema precisa parecer t&atilde;o s&oacute;lido quanto o atendimento</h3>
          <p>Uma interface mais segura, mais limpa e mais profissional melhora uso interno e tamb&eacute;m o valor percebido pelo paciente.</p>
        </div>
        <div class="dhx-quote-list">
          <div class="dhx-quote-card">
            <div class="dhx-quote-head">
              {profile_a_markup}
              <div>
                <div class="dhx-quote-name">Dra. Mariana Costa</div>
                <div class="dhx-quote-role">Nutricionista</div>
              </div>
            </div>
            <blockquote>"O DietHealth transformou meu fluxo cl&iacute;nico e o acompanhamento dos pacientes."</blockquote>
          </div>
          <div class="dhx-quote-card">
            <div class="dhx-quote-head">
              {profile_b_markup}
              <div>
                <div class="dhx-quote-name">Lucas Almeida</div>
                <div class="dhx-quote-role">Paciente</div>
              </div>
            </div>
            <blockquote>"Consegui melhorar meus h&aacute;bitos com mais velocidade e clareza no plano nutricional."</blockquote>
          </div>
        </div>
      </article>
      <article class="dhx-panel dhx-pricing">
        <span class="dhx-section-kicker">Plano Premium</span>
        <h3>Plano Premium DietHealth</h3>
        <div class="dhx-price">R$ 49,90<span>/m&ecirc;s</span></div>
        {landing_checkout_note}
        <ul class="dhx-pricing-list">
          <li>Dietas com IA em minutos com personaliza&ccedil;&atilde;o por paciente</li>
          <li>Agenda integrada com gest&atilde;o de consultas e lembretes</li>
          <li>Relat&oacute;rios autom&aacute;ticos de evolu&ccedil;&atilde;o e performance cl&iacute;nica</li>
          <li>Controle financeiro com receitas, despesas e fechamento mensal</li>
          <li>Prontu&aacute;rio digital completo e hist&oacute;rico centralizado</li>
          <li>Exporta&ccedil;&atilde;o em PDF e compartilhamento por WhatsApp</li>
        </ul>
        <div class="dhx-pay-grid">
          <a class="dhx-pay-chip" href="{landing_checkout_url}" target="_self" title="Cadastre-se ou faça login para liberar o pagamento.">PIX</a>
          <a class="dhx-pay-chip" href="{landing_checkout_url}" target="_self" title="Cadastre-se ou faça login para liberar o pagamento.">Boleto</a>
          <a class="dhx-pay-chip" href="{landing_checkout_url}" target="_self" title="Cadastre-se ou faça login para liberar o pagamento.">Cart&atilde;o</a>
        </div>
        <a class="dhx-plan-cta" href="{landing_checkout_url}" target="_self">{landing_checkout_label}</a>
      </article>
    </div>
  </section>
</div>
"""
        ),
        unsafe_allow_html=True,
    )
    st.markdown('<div id="dh-auth-anchor"></div>', unsafe_allow_html=True)
    if not st.session_state.get("logado"):
        st.warning("Para assinar o Premium, primeiro crie sua conta ou faça login. Após o cadastro, o pagamento é liberado automaticamente.")

    st.markdown(
        """
<style>
div[class*="st-key-lp_pop_login_wrap"]{
  position: static !important;
  width: auto;
  display: inline-flex !important;
  margin: 0 !important;
  vertical-align: top;
}
div[class*="st-key-lp_pop_register_wrap"]{
  position: static !important;
  width: auto;
  display: inline-flex !important;
  margin: 0 !important;
  vertical-align: top;
}
div[class*="st-key-lp_pop_login_wrap"] > div > button,
div[class*="st-key-lp_pop_register_wrap"] > div > button{
  border-radius: 999px !important;
  border: 1px solid rgba(109, 235, 195, 0.42) !important;
  background: linear-gradient(180deg, rgba(6, 20, 31, 0.92), rgba(7, 24, 37, 0.82)) !important;
  color: #e8fff4 !important;
  font-weight: 800 !important;
  font-size: 0.82rem !important;
  letter-spacing: 0.01em !important;
  box-shadow: 0 0 0 1px rgba(32, 209, 147, 0.08), 0 8px 18px rgba(0,0,0,0.22) !important;
  min-height: 36px !important;
  padding: 0 0.8rem !important;
}
div[class*="st-key-lp_pop_login_wrap"] > div > button:hover,
div[class*="st-key-lp_pop_register_wrap"] > div > button:hover{
  border-color: rgba(121, 244, 202, 0.62) !important;
  background: linear-gradient(180deg, rgba(8, 27, 40, 0.96), rgba(8, 30, 46, 0.90)) !important;
  color: #f5fff9 !important;
}
div[class*="st-key-lp_login_pop_body"],
div[class*="st-key-lp_register_pop_body"]{
  width: min(92vw, 360px);
}
div[class*="st-key-lp_login_pop_shell"],
div[class*="st-key-lp_register_pop_shell"],
div[class*="st-key-lp_login_pop_body"],
div[class*="st-key-lp_register_pop_body"]{
  color: #E2E8F0 !important;
}
        .dh-auth-pop-head{
          display:grid;
          gap:8px;
          padding:4px 0 2px 0;
        }
        .dh-auth-pop-head h3{
          margin:0 !important;
          color:#F8FBFF !important;
          font-size:1.72rem !important;
          font-weight:900 !important;
          line-height:1.08 !important;
          letter-spacing:-0.03em !important;
          opacity:1 !important;
          text-shadow:none !important;
          filter:none !important;
        }
        .dh-auth-pop-subtitle{
          color:#D9E7F5 !important;
          font-size:0.98rem !important;
          font-weight:600 !important;
          line-height:1.55 !important;
          opacity:1 !important;
          text-shadow:none !important;
          filter:none !important;
        }
div[class*="st-key-lp_login_pop_shell"] h1,
div[class*="st-key-lp_login_pop_shell"] h2,
div[class*="st-key-lp_login_pop_shell"] h3,
div[class*="st-key-lp_login_pop_shell"] p,
div[class*="st-key-lp_login_pop_shell"] span,
div[class*="st-key-lp_login_pop_body"] p,
div[class*="st-key-lp_login_pop_body"] span,
div[class*="st-key-lp_register_pop_shell"] h1,
div[class*="st-key-lp_register_pop_shell"] h2,
div[class*="st-key-lp_register_pop_shell"] h3,
div[class*="st-key-lp_register_pop_shell"] p,
div[class*="st-key-lp_register_pop_shell"] span,
div[class*="st-key-lp_register_pop_body"] p,
div[class*="st-key-lp_register_pop_body"] span{
  color: #E2E8F0 !important;
  opacity: 1 !important;
  text-shadow: none !important;
}
div[class*="st-key-lp_login_pop_shell"] label,
div[class*="st-key-lp_register_pop_shell"] label,
div[class*="st-key-lp_login_pop_body"] label,
div[class*="st-key-lp_register_pop_body"] label{
  color: #CBD5E1 !important;
  opacity: 1 !important;
}
div[class*="st-key-lp_register_pop_body"]{
  max-height: 72vh;
  overflow-y: auto;
  padding-right: 4px;
}
@media (max-width: 900px){
  div[class*="st-key-lp_pop_login_wrap"],
  div[class*="st-key-lp_pop_register_wrap"]{
    width: 100%;
  }
}
@media (max-width: 720px){
  div[class*="st-key-lp_pop_login_wrap"]{
    position: static !important;
    width: 100%;
    margin: 0 !important;
  }
  div[class*="st-key-lp_pop_register_wrap"]{
    position: static !important;
    width: 100%;
    margin: 0 !important;
  }
}
</style>
        """,
        unsafe_allow_html=True,
    )

    if "landing_auth_mode" not in st.session_state:
        st.session_state["landing_auth_mode"] = ""
    if EXPERIENCE_SESSION_KEY not in st.session_state:
        st.session_state[EXPERIENCE_SESSION_KEY] = "traditional"

    st.markdown(
        """
        <style>
        div[class*="st-key-lp_access_topbar_wrap"]{
          width: min(100%, 1280px);
          display: flex;
          align-items: center;
          justify-content: space-between;
          max-width: 1280px;
          position: relative;
          left: auto;
          top: auto;
          transform: none;
          z-index: 1000;
          margin: 4px auto 6px auto;
          padding: 0 16px;
        }
        div[class*="st-key-lp_access_topbar_wrap"] > div{
          width: 100%;
        }
        div[class*="st-key-lp_access_topbar_wrap"] > div,
        div[class*="st-key-lp_access_topbar_wrap"] [data-testid="stHorizontalBlock"]{
          align-items: center !important;
          gap: 10px !important;
          padding: 0 !important;
          border-radius: 0 !important;
          border: none !important;
          background: transparent !important;
          box-shadow: none !important;
          backdrop-filter: none !important;
          -webkit-backdrop-filter: none !important;
        }
        .dh-lp-access-status-inline{
          margin: 0 !important;
          justify-content: flex-end;
          min-height: 36px;
        }
        .dh-lp-access-status-inline span{
          white-space: nowrap;
        }
        div[class*="st-key-lp_access_topbar_wrap"] button{
          min-height: 40px !important;
          border-radius: 999px !important;
          font-size: 0.84rem !important;
          font-weight: 820 !important;
          letter-spacing: 0.01em !important;
          white-space: nowrap !important;
        }
        div[class*="st-key-lp_access_topbar_wrap"] button[kind="secondary"],
        div[class*="st-key-lp_access_topbar_wrap"] button[kind="tertiary"]{
          border: 1px solid rgba(151, 214, 196, 0.26) !important;
          background: rgba(9, 24, 36, 0.84) !important;
          color: rgba(236, 247, 243, 0.96) !important;
          box-shadow: inset 0 1px 0 rgba(255,255,255,0.04) !important;
        }
        div[class*="st-key-lp_access_topbar_wrap"] button[kind="primary"]{
          border: 1px solid rgba(120, 245, 189, 0.42) !important;
          background: linear-gradient(180deg, rgba(13, 53, 67, 0.98), rgba(8, 32, 43, 0.95)) !important;
          color: #effff6 !important;
          box-shadow: 0 14px 26px rgba(0,0,0,0.24), 0 0 18px rgba(55, 214, 158, 0.10) !important;
        }
        div[class*="st-key-lp_access_switch_wrap"]{
          max-width: none;
          margin: 0;
          padding: 8px 10px 8px 10px;
          border-radius: 16px;
          border: 1px solid rgba(167, 233, 212, 0.14);
          background:
            linear-gradient(180deg, rgba(8, 21, 33, 0.82), rgba(8, 21, 33, 0.70)),
            radial-gradient(circle at top left, rgba(33, 211, 138, 0.08), transparent 45%);
          backdrop-filter: blur(8px);
          -webkit-backdrop-filter: blur(8px);
          box-shadow: 0 14px 28px rgba(0,0,0,0.18);
        }
        .dh-lp-access-status{
          display:flex;
          align-items:center;
          gap:8px;
          margin: 0 0 7px 2px;
          color: rgba(205, 224, 217, 0.82);
          font-size: 0.70rem;
          font-weight: 700;
          letter-spacing: 0.03em;
          text-transform: uppercase;
        }
        .dh-lp-access-status span{
          display:inline-flex;
          align-items:center;
          min-height: 22px;
          padding: 3px 9px;
          border-radius: 999px;
          border: 1px solid rgba(151, 235, 203, 0.16);
          background: rgba(8, 27, 36, 0.62);
          color: #ecfff5;
          text-transform: none;
          font-size: 0.72rem;
          font-weight: 700;
          letter-spacing: 0.01em;
        }
        div[class*="st-key-lp_auth_topbar_wrap"] [data-testid="column"],
        div[class*="st-key-lp_auth_topbar_wrap_register"] [data-testid="column"]{
          display: flex !important;
          align-items: flex-start !important;
          justify-content: flex-end !important;
        }
        div[class*="st-key-lp_auth_topbar_wrap"] div[class*="st-key-lp_pop_login_wrap"],
        div[class*="st-key-lp_auth_topbar_wrap_register"] div[class*="st-key-lp_pop_register_wrap"]{
          align-self: flex-start !important;
        }
        div[class*="st-key-lp_pop_login_wrap"] > div,
        div[class*="st-key-lp_pop_register_wrap"] > div{
          width: auto !important;
        }
        div[class*="st-key-lp_pop_login_wrap"] > div > button,
        div[class*="st-key-lp_pop_register_wrap"] > div > button{
          width: auto !important;
          min-width: 102px !important;
          padding-left: 0.92rem !important;
          padding-right: 0.92rem !important;
          white-space: nowrap !important;
        }
        div[class*="st-key-lp_login_pop_body"] [role="radiogroup"]{
          gap: 0.5rem !important;
          flex-wrap: wrap !important;
          margin-top: 0.15rem !important;
        }
        div[class*="st-key-lp_login_pop_body"] [role="radiogroup"] > label{
          margin: 0 !important;
          padding: 0.55rem 0.85rem !important;
          border-radius: 999px !important;
          border: 1px solid rgba(122, 170, 186, 0.22) !important;
          background: rgba(7, 18, 30, 0.72) !important;
        }
        div[class*="st-key-lp_login_pop_body"] [role="radiogroup"] > label:has(input:checked){
          border-color: rgba(119, 241, 195, 0.42) !important;
          background: linear-gradient(180deg, rgba(10, 41, 54, 0.96), rgba(9, 29, 41, 0.92)) !important;
          box-shadow: 0 8px 18px rgba(0,0,0,0.18) !important;
        }
        div[class*="st-key-lp_login_pop_body"] [role="radiogroup"] p{
          color: #e8eef6 !important;
          font-weight: 700 !important;
          font-size: 0.96rem !important;
          margin: 0 !important;
        }
        div[class*="st-key-lp_virtual_access_card"]{
          height: 100%;
          padding: 16px 16px 14px 16px;
          border-radius: 18px;
          border: 1px solid rgba(151, 214, 196, 0.16);
          background:
            radial-gradient(circle at top left, rgba(33, 211, 138, 0.06), transparent 42%),
            linear-gradient(180deg, rgba(8, 21, 33, 0.72), rgba(8, 21, 33, 0.62));
          backdrop-filter: blur(8px);
          -webkit-backdrop-filter: blur(8px);
          box-shadow: 0 12px 24px rgba(0,0,0,0.14);
        }
        div[class*="st-key-lp_virtual_access_card"] [data-testid="stTextInput"] label,
        div[class*="st-key-lp_virtual_access_card"] [data-testid="stTextInput"] p{
          color: #edf8ff !important;
          font-weight: 700 !important;
        }
        div[class*="st-key-lp_virtual_access_card"] [data-testid="stTextInput"] input{
          min-height: 42px !important;
          border-radius: 14px !important;
          border: 1px solid rgba(153, 214, 197, 0.20) !important;
          background: rgba(247, 250, 252, 0.96) !important;
          color: #0f172a !important;
        }
        div[class*="st-key-lp_virtual_access_card"] button[kind="secondary"],
        div[class*="st-key-lp_virtual_access_card"] button[kind="primary"]{
          min-height: 42px !important;
          border-radius: 999px !important;
          font-weight: 820 !important;
          font-size: 0.86rem !important;
        }
        @media (max-width: 1080px){
          div[class*="st-key-lp_access_topbar_wrap"]{
            display: block;
          }
        }
        @media (max-width: 980px){
          .dh-lp-access-status-inline{
            justify-content: flex-start;
          }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    with login_slot:
        with st.container(key="lp_pop_login_wrap"):
            with st.popover("Entrar", use_container_width=True):
                with st.container(key="lp_login_pop_shell"):
                    st.markdown(
                        """
                        <div class="dh-auth-pop-head">
                          <h3>Entrar no Sistema</h3>
                          <div class="dh-auth-pop-subtitle">Entre com seu usuario e senha para continuar.</div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

                with st.container(key="lp_login_pop_body"):
                    with st.form("login_form"):
                        login_tipo = st.radio(
                            "Entrar como",
                            ["Usuário", "Paciente"],
                            horizontal=True,
                            key="login_tipo_acesso",
                        )
                        login_tipo_normalized = (login_tipo or "").strip().lower()
                        is_patient_login = login_tipo_normalized == "paciente"
                        u = st.text_input("CPF" if is_patient_login else "Usuario", placeholder="000.000.000-00" if is_patient_login else "admin")
                        s = st.text_input("Senha", type="password", placeholder="123")
                        if st.form_submit_button("ENTRAR AGORA", use_container_width=True):
                            st.session_state["landing_login_target"] = login_tipo_normalized
                            u_norm = (u or "").strip().lower()
                            expected_tipo = "patient" if is_patient_login else None
                            user = _patient_login_lookup(u, s) if expected_tipo == "patient" else next(
                                (x for x in users if (x.get("usuario") or "").strip().lower() == u_norm and x.get("senha") == s),
                                None,
                            )
                            if user and expected_tipo and (user.get("tipo") or "").strip().lower() != expected_tipo:
                                st.session_state["login_blocked_user"] = ""
                                st.session_state["login_blocked_reason"] = ""
                                st.session_state["login_blocked_venc"] = ""
                                st.session_state["login_verified_user"] = ""
                                st.session_state["login_verified_tipo"] = ""
                                st.session_state["login_verified_at"] = 0.0
                                st.error("Este acesso não pertence ao perfil Paciente. Para ADMIN e nutricionista, use a opção Usuário.")
                            elif user:
                                ok, reason, venc = _check_user_access(user)
                                if not ok and reason in ("pending", "blocked"):
                                    try:
                                        if mp_try_auto_activate_user(user):
                                            ok, reason, venc = _check_user_access(user)
                                    except Exception:
                                        pass
                                if ok:
                                    st.session_state["login_blocked_user"] = ""
                                    st.session_state["login_blocked_reason"] = ""
                                    st.session_state["login_blocked_venc"] = ""
                                    st.session_state["login_verified_user"] = ""
                                    st.session_state["login_verified_tipo"] = ""
                                    st.session_state["login_verified_at"] = 0.0
                                    st.session_state["logado"] = True
                                    st.session_state["usuario"] = (user.get("usuario") or "").strip().lower()
                                    st.session_state["tipo"] = user.get("tipo", "user")
                                    st.session_state[EXPERIENCE_SESSION_KEY] = "traditional"
                                    _persist_login_query(st.session_state["usuario"])
                                    _touch_user_presence(force=True)
                                    st.rerun()
                                else:
                                    blocked_u = (user.get("usuario") or "").strip().lower()
                                    st.session_state["login_blocked_user"] = blocked_u
                                    st.session_state["login_blocked_reason"] = reason
                                    st.session_state["login_blocked_venc"] = str(venc) if venc else ""
                                    st.session_state["login_verified_user"] = blocked_u
                                    st.session_state["login_verified_tipo"] = user.get("tipo", "user")
                                    st.session_state["login_verified_at"] = float(time.time())
                                    if reason == "blocked":
                                        st.error("Acesso bloqueado. Procure o admin para liberar.")
                                    else:
                                        st.error("Cadastro pendente de pagamento/liberacao.")
                            else:
                                st.session_state["login_blocked_user"] = ""
                                st.session_state["login_blocked_reason"] = ""
                                st.session_state["login_blocked_venc"] = ""
                                st.session_state["login_verified_user"] = ""
                                st.session_state["login_verified_tipo"] = ""
                                st.session_state["login_verified_at"] = 0.0
                                st.error("Dados incorretos!")

                if (st.session_state.get("login_tipo_acesso") or "").strip().lower() == "paciente":
                    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
                    first_tab, reset_tab = st.tabs(["Primeiro acesso", "Esqueci minha senha"])
                    with first_tab:
                        with st.form("patient_first_access_form"):
                            cpf_first = st.text_input("CPF", key="patient_first_cpf", placeholder="000.000.000-00")
                            codigo_first = st.text_input("Código do paciente", key="patient_first_code", placeholder="DHXXXXXX")
                            senha_first = st.text_input("Criar senha", type="password", key="patient_first_pass")
                            senha_first_2 = st.text_input("Confirmar senha", type="password", key="patient_first_pass2")
                            if st.form_submit_button("ATIVAR ACESSO", use_container_width=True):
                                ok, msg = _activate_patient_portal_access(cpf_first, codigo_first, senha_first, senha_first_2)
                                if ok:
                                    st.success(msg)
                                else:
                                    st.error(msg)
                    with reset_tab:
                        with st.form("patient_reset_access_form"):
                            cpf_reset = st.text_input("CPF", key="patient_reset_cpf", placeholder="000.000.000-00")
                            codigo_reset = st.text_input("Código do paciente", key="patient_reset_code", placeholder="DHXXXXXX")
                            senha_reset = st.text_input("Nova senha", type="password", key="patient_reset_pass")
                            senha_reset_2 = st.text_input("Confirmar nova senha", type="password", key="patient_reset_pass2")
                            if st.form_submit_button("REDEFINIR SENHA", use_container_width=True):
                                ok, msg = _reset_patient_portal_password(cpf_reset, codigo_reset, senha_reset, senha_reset_2)
                                if ok:
                                    st.success(msg)
                                else:
                                    st.error(msg)

                blocked_user = (st.session_state.get("login_blocked_user") or "").strip().lower()
                if blocked_user:
                    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
                    blocked_reason = (st.session_state.get("login_blocked_reason") or "").strip().lower()
                    blocked_venc = (st.session_state.get("login_blocked_venc") or "").strip()
                    if blocked_reason in ("pending", "blocked"):
                        st.error("Cadastro pendente de pagamento/liberacao.")
                    st.caption("Para liberacao automatica, use o pagamento gerado aqui para identificar seu usuario.")
                    u_obj = next((x for x in users if (x.get("usuario") or "").strip().lower() == blocked_user), None)

                    if u_obj and _mp_access_token():
                        col_p1, col_p2 = st.columns([1, 1])
                        if col_p1.button("Gerar link de pagamento", key="mp_gen_link_login", use_container_width=True):
                            url_gen = mp_get_cached_checkout_url(u_obj, force_new=True)
                            if url_gen:
                                st.success("Link gerado. Clique em pagar abaixo.")
                            else:
                                st.error((st.session_state.get("mp_checkout_last_err") or "").strip() or "Nao foi possivel gerar o link agora.")

                        url = ""
                        if st.session_state.get("mp_checkout_user") == blocked_user:
                            url = (st.session_state.get("mp_checkout_url") or "").strip()
                        if url:
                            st.link_button("PAGAR AGORA (Pix/Cartão)", url, use_container_width=True)
                        else:
                            st.info("Clique em Gerar link de pagamento para abrir Pix/Cartão.")

                        if col_p2.button("Ja paguei - verificar", key="mp_check_login", use_container_width=True):
                            if mp_try_auto_activate_user(u_obj):
                                st.session_state["login_blocked_user"] = ""
                                st.session_state["login_blocked_reason"] = ""
                                st.session_state["login_blocked_venc"] = ""
                                verified_user = (st.session_state.get("login_verified_user") or "").strip().lower()
                                verified_tipo = (st.session_state.get("login_verified_tipo") or u_obj.get("tipo") or "user")
                                verified_at = float(st.session_state.get("login_verified_at") or 0.0)
                                can_auto_login = (verified_user == blocked_user) and ((time.time() - verified_at) <= 15 * 60)
                                if can_auto_login:
                                    login_target = (st.session_state.get("landing_login_target") or "").strip().lower()
                                    auto_virtual_login = login_target == "atendimento virtual"
                                    st.session_state["logado"] = True
                                    st.session_state["usuario"] = blocked_user
                                    st.session_state["tipo"] = verified_tipo
                                    st.session_state[EXPERIENCE_SESSION_KEY] = "virtual" if auto_virtual_login else "traditional"
                                    if auto_virtual_login:
                                        st.session_state[VIRTUAL_MENU_SESSION_KEY] = "camila_home"
                                    _persist_login_query(st.session_state["usuario"])
                                    st.session_state["login_verified_user"] = ""
                                    st.session_state["login_verified_tipo"] = ""
                                    st.session_state["login_verified_at"] = 0.0
                                    _touch_user_presence(force=True)
                                    st.success("Pagamento confirmado! Acesso liberado. Entrando no sistema...")
                                    time.sleep(0.3)
                                else:
                                    st.success("Pagamento confirmado! Seu acesso foi liberado. Faca login novamente.")
                                st.rerun()
                            else:
                                st.warning("Ainda nao encontrei pagamento aprovado para seu usuario. Aguarde e tente novamente.")
                    else:
                        if not _mp_access_token():
                            st.caption("Liberacao automatica depende de configurar MERCADO_PAGO_ACCESS_TOKEN no servidor.")

    with register_slot:
        with st.container(key="lp_pop_register_wrap"):
            with st.popover("Cadastro", use_container_width=True):
                with st.container(key="lp_register_pop_shell"):
                    st.markdown(
                        """
                        <div class="dh-auth-pop-head">
                          <h3>Criar Conta</h3>
                          <div class="dh-auth-pop-subtitle">Preencha seus dados para criar sua conta.</div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )
                with st.container(key="lp_register_pop_body"):
                    with st.form("register_form"):
                        tipo_conta = st.radio("Tipo de acesso", ["Nutricionista", "Paciente", "Atendimento Virtual"], horizontal=True, key="reg_tipo_conta")
                        nome_r = st.text_input("Nome completo", key="reg_nome")
                        cpf_r = st.text_input("CPF", key="reg_cpf", placeholder="000.000.000-00")
                        email_r = st.text_input("Email", key="reg_email")
                        tel_r = st.text_input("WhatsApp", key="reg_tel")
                        is_patient_signup_ui = (tipo_conta or "").strip().lower() == "paciente"
                        codigo_r = st.text_input("Código do paciente", key="reg_codigo_paciente", placeholder="DHXXXXXX") if is_patient_signup_ui else ""
                        user_r = st.text_input("Usuario", key="reg_user") if not is_patient_signup_ui else ""
                        pass_r = st.text_input("Senha", type="password", key="reg_pass")
                        pass_r2 = st.text_input("Confirmar senha", type="password", key="reg_pass2")
                        if st.form_submit_button("CRIAR CONTA", use_container_width=True):
                            u_norm = (user_r or "").strip().lower()
                            cpf_norm = _normalize_cpf(cpf_r)
                            email_clean = (email_r or "").strip()
                            tel_clean = (tel_r or "").strip()
                            signup_access_type = (tipo_conta or "").strip().lower()
                            is_patient_signup = signup_access_type == "paciente"
                            is_virtual_signup = signup_access_type == "atendimento virtual"
                            patient_match = _find_unique_patient_match_by_cpf(cpf_norm) if is_patient_signup else None
                            patient_conflict = is_patient_signup and cpf_norm and len(_find_patient_matches_by_cpf(cpf_norm)) > 1
                            portal_user_existing = _portal_user_by_cpf(cpf_norm) if is_patient_signup else None
                            if (not is_patient_signup) and (not u_norm or not pass_r):
                                st.error("Usuario e senha sao obrigatorios.")
                            elif pass_r != pass_r2:
                                st.error("As senhas nao conferem.")
                            elif not cpf_norm:
                                st.error("CPF e obrigatorio.")
                            elif not _is_valid_cpf(cpf_norm):
                                st.error("Informe um CPF valido.")
                            elif (not is_patient_signup) and _cpf_already_exists(cpf_norm):
                                st.error("Ja existe cadastro com este CPF.")
                            elif (not is_patient_signup) and not email_clean:
                                st.error("Email e obrigatorio.")
                            elif (not is_patient_signup) and not _is_valid_email(email_clean):
                                st.error("Informe um email valido.")
                            elif (not is_patient_signup) and not tel_clean:
                                st.error("Celular/WhatsApp e obrigatorio.")
                            elif (not is_patient_signup) and not _is_valid_celular(tel_clean):
                                st.error("Informe um celular valido com DDD.")
                            elif (not is_patient_signup) and any((x.get("usuario") or "").strip().lower() == u_norm for x in users):
                                st.error("Usuario ja existe.")
                            elif patient_conflict:
                                st.error("Este CPF aparece em mais de uma base. O ADMIN precisa revisar o vínculo antes de liberar o portal.")
                            elif is_patient_signup and portal_user_existing and (portal_user_existing.get("status") or "").strip().lower() == "active":
                                st.error("Este paciente já possui acesso ativo ao portal. Use a opção Entrar ou Esqueci minha senha.")
                            elif is_patient_signup and not patient_match:
                                st.error("CPF não encontrado na base clínica. O acesso do paciente precisa ser validado antes da ativação.")
                            elif is_patient_signup and not (codigo_r or "").strip():
                                st.error("Informe o código do paciente para ativar o portal.")
                            else:
                                if is_patient_signup:
                                    ok, msg = _activate_patient_portal_access(cpf_norm, codigo_r, pass_r, pass_r2, email_clean, tel_clean)
                                    if ok:
                                        st.success(msg)
                                    else:
                                        st.error(msg)
                                else:
                                    new_user = {
                                        "signup_id": _new_signup_id(),
                                        "nome": nome_r,
                                        "cpf": cpf_norm,
                                        "usuario": u_norm,
                                        "senha": pass_r,
                                        "tipo": "user",
                                        "status": "active",
                                        "paid_until": "",
                                        "wa_provider": "wapi",
                                        "wa_token": "",
                                        "wa_phone_id": "",
                                        "wa_api_url": "",
                                        "wa_instance": "",
                                        "wa_notify_admin_num": "",
                                        "email": email_clean,
                                        "telefone": tel_clean,
                                        "created_at": str(datetime.now().date()),
                                        "signup_access_type": "virtual" if is_virtual_signup else "traditional",
                                        "experience_preference": "virtual" if is_virtual_signup else "traditional",
                                    }
                                    users.append(new_user)
                                    save_db("users.json", users)
                                    if is_virtual_signup:
                                        st.success("Cadastro do Atendimento Virtual criado! Acesso liberado no plano básico.")
                                    else:
                                        st.success("Cadastro criado! Acesso liberado no plano básico.")
                                    wa_ok, wa_msg = _notify_admin_new_signup(new_user)
                                    if wa_ok:
                                        st.caption(f"Notificacao enviada para API do admin ({wa_msg}).")
                                    else:
                                        st.warning(f"Cadastro salvo, mas nao foi possivel notificar o admin no WhatsApp: {wa_msg}")
                                    if is_virtual_signup:
                                        st.link_button("Assinar Atendimento Virtual", MERCADO_PAGO_VIRTUAL, use_container_width=True)
                                    elif _mp_access_token():
                                        u_obj_new = next((x for x in users if (x.get("usuario") or "").strip().lower() == u_norm), None)
                                        info, err = mp_create_checkout_link(u_obj_new) if u_obj_new else (None, "Usuario nao encontrado.")
                                        if info and (info.get("url") or "").strip():
                                            st.link_button("Assinar agora (opcional)", info["url"], use_container_width=True)
                                        elif err:
                                            st.caption(err)
                                    else:
                                        st.caption("Pagamento online automatico depende de MERCADO_PAGO_ACCESS_TOKEN no servidor.")

    components.html(
        """
        <script>
        (function () {
          const host = window.parent || window;
          const doc = host.document;

          const ensureAuthStyle = () => {
            try {
              const css = `
                div[data-baseweb="popover"] div[class*="st-key-lp_login_pop_shell"],
                div[data-baseweb="popover"] div[class*="st-key-lp_register_pop_shell"],
                div[data-baseweb="popover"] div[class*="st-key-lp_login_pop_body"],
                div[data-baseweb="popover"] div[class*="st-key-lp_register_pop_body"],
                div[data-testid="stPopover"] div[class*="st-key-lp_login_pop_shell"],
                div[data-testid="stPopover"] div[class*="st-key-lp_register_pop_shell"],
                div[data-testid="stPopover"] div[class*="st-key-lp_login_pop_body"],
                div[data-testid="stPopover"] div[class*="st-key-lp_register_pop_body"],
                div[class*="st-key-lp_login_pop_shell"],
                div[class*="st-key-lp_register_pop_shell"],
                div[class*="st-key-lp_login_pop_body"],
                div[class*="st-key-lp_register_pop_body"]{
                  color:#EAF2FF !important;
                  opacity:1 !important;
                }
                .dh-auth-pop-head,
                .dh-auth-pop-head *{
                  opacity:1 !important;
                  filter:none !important;
                  text-shadow:none !important;
                }
                .dh-auth-pop-head h3{
                  color:#F8FBFF !important;
                  font-size:1.72rem !important;
                  font-weight:900 !important;
                  line-height:1.08 !important;
                  letter-spacing:-0.03em !important;
                }
                .dh-auth-pop-subtitle{
                  color:#D9E7F5 !important;
                  font-size:0.98rem !important;
                  font-weight:600 !important;
                  line-height:1.55 !important;
                }
                div[data-baseweb="popover"] div[class*="st-key-lp_login_pop_shell"] h1,
                div[data-baseweb="popover"] div[class*="st-key-lp_login_pop_shell"] h2,
                div[data-baseweb="popover"] div[class*="st-key-lp_login_pop_shell"] h3,
                div[data-baseweb="popover"] div[class*="st-key-lp_login_pop_shell"] p,
                div[data-baseweb="popover"] div[class*="st-key-lp_login_pop_shell"] span,
                div[data-baseweb="popover"] div[class*="st-key-lp_register_pop_shell"] h1,
                div[data-baseweb="popover"] div[class*="st-key-lp_register_pop_shell"] h2,
                div[data-baseweb="popover"] div[class*="st-key-lp_register_pop_shell"] h3,
                div[data-baseweb="popover"] div[class*="st-key-lp_register_pop_shell"] p,
                div[data-baseweb="popover"] div[class*="st-key-lp_register_pop_shell"] span,
                div[data-testid="stPopover"] div[class*="st-key-lp_login_pop_shell"] h1,
                div[data-testid="stPopover"] div[class*="st-key-lp_login_pop_shell"] h2,
                div[data-testid="stPopover"] div[class*="st-key-lp_login_pop_shell"] h3,
                div[data-testid="stPopover"] div[class*="st-key-lp_login_pop_shell"] p,
                div[data-testid="stPopover"] div[class*="st-key-lp_login_pop_shell"] span,
                div[data-testid="stPopover"] div[class*="st-key-lp_register_pop_shell"] h1,
                div[data-testid="stPopover"] div[class*="st-key-lp_register_pop_shell"] h2,
                div[data-testid="stPopover"] div[class*="st-key-lp_register_pop_shell"] h3,
                div[data-testid="stPopover"] div[class*="st-key-lp_register_pop_shell"] p,
                div[data-testid="stPopover"] div[class*="st-key-lp_register_pop_shell"] span,
                div[class*="st-key-lp_login_pop_shell"] h1,
                div[class*="st-key-lp_login_pop_shell"] h2,
                div[class*="st-key-lp_login_pop_shell"] h3,
                div[class*="st-key-lp_login_pop_shell"] p,
                div[class*="st-key-lp_login_pop_shell"] span,
                div[class*="st-key-lp_register_pop_shell"] h1,
                div[class*="st-key-lp_register_pop_shell"] h2,
                div[class*="st-key-lp_register_pop_shell"] h3,
                div[class*="st-key-lp_register_pop_shell"] p,
                div[class*="st-key-lp_register_pop_shell"] span{
                  color:#F8FBFF !important;
                  opacity:1 !important;
                }
                div[data-baseweb="popover"] div[class*="st-key-lp_login_pop_body"] label,
                div[data-baseweb="popover"] div[class*="st-key-lp_register_pop_body"] label,
                div[data-baseweb="popover"] div[class*="st-key-lp_login_pop_body"] [data-baseweb="radio"] *,
                div[data-baseweb="popover"] div[class*="st-key-lp_register_pop_body"] [data-baseweb="radio"] *,
                div[data-testid="stPopover"] div[class*="st-key-lp_login_pop_body"] label,
                div[data-testid="stPopover"] div[class*="st-key-lp_register_pop_body"] label,
                div[data-testid="stPopover"] div[class*="st-key-lp_login_pop_body"] [data-baseweb="radio"] *,
                div[data-testid="stPopover"] div[class*="st-key-lp_register_pop_body"] [data-baseweb="radio"] *,
                div[class*="st-key-lp_login_pop_body"] label,
                div[class*="st-key-lp_register_pop_body"] label,
                div[class*="st-key-lp_login_pop_body"] [data-baseweb="radio"] *,
                div[class*="st-key-lp_register_pop_body"] [data-baseweb="radio"] *{
                  color:#D6E3F1 !important;
                  opacity:1 !important;
                }
              `;
              let style = doc.getElementById('dh-auth-contrast-style');
              if (!style) {
                style = doc.createElement('style');
                style.id = 'dh-auth-contrast-style';
                doc.head.appendChild(style);
              }
              if (style.textContent !== css) {
                style.textContent = css;
              }
              doc.head.appendChild(style);
            } catch (e) {}
          };

          const applyAuthContrast = () => {
            try {
              ensureAuthStyle();
              const titleSelectors = [
                '.dh-auth-pop-head h3',
                'div[class*="st-key-lp_login_pop_shell"] h3',
                'div[class*="st-key-lp_register_pop_shell"] h3'
              ];
              titleSelectors.forEach((selector) => {
                doc.querySelectorAll(selector).forEach((node) => {
                  node.style.setProperty('color', '#F8FBFF', 'important');
                  node.style.setProperty('opacity', '1', 'important');
                  node.style.setProperty('text-shadow', 'none', 'important');
                  node.style.setProperty('filter', 'none', 'important');
                  node.style.setProperty('font-weight', '900', 'important');
                });
              });

              doc.querySelectorAll('.dh-auth-pop-subtitle').forEach((node) => {
                node.style.setProperty('color', '#D9E7F5', 'important');
                node.style.setProperty('opacity', '1', 'important');
                node.style.setProperty('text-shadow', 'none', 'important');
                node.style.setProperty('filter', 'none', 'important');
                node.style.setProperty('font-weight', '600', 'important');
              });

              const shellSelectors = [
                'div[class*="st-key-lp_login_pop_shell"]',
                'div[class*="st-key-lp_register_pop_shell"]'
              ];
              shellSelectors.forEach((selector) => {
                doc.querySelectorAll(selector).forEach((node) => {
                  node.style.setProperty('opacity', '1', 'important');
                  node.style.setProperty('color', '#EAF2FF', 'important');
                });
              });
            } catch (e) {}
          };

          applyAuthContrast();
          let runs = 0;
          const interval = host.setInterval(() => {
            applyAuthContrast();
            runs += 1;
            if (runs > 40) host.clearInterval(interval);
          }, 200);

          try {
            const observer = new host.MutationObserver(() => applyAuthContrast());
            observer.observe(doc.body, { childList: true, subtree: true, attributes: true });
            host.setTimeout(() => observer.disconnect(), 15000);
          } catch (e) {}
        })();
        </script>
        """,
        height=0,
        width=0,
    )


def _inject_pwa_shell() -> None:
    pwa_version = "20260408"
    pwa_version_js = json.dumps(pwa_version)
    components.html(
        f"""
<script>
(function() {{
  const version = {pwa_version_js};
  const rootWin = window.parent && window.parent.document ? window.parent : window;
  const rootDoc = rootWin.document || document;
  const head = rootDoc.head || document.head;
  if (!head) return;

  const upsertLink = (selector, attrs) => {{
    let el = head.querySelector(selector);
    if (!el) {{
      el = rootDoc.createElement('link');
      head.appendChild(el);
    }}
    Object.entries(attrs).forEach(([k, v]) => el.setAttribute(k, v));
  }};

  const upsertMeta = (selector, attrs) => {{
    let el = head.querySelector(selector);
    if (!el) {{
      el = rootDoc.createElement('meta');
      head.appendChild(el);
    }}
    Object.entries(attrs).forEach(([k, v]) => el.setAttribute(k, v));
  }};

  upsertLink('link[rel="manifest"]', {{ rel: 'manifest', href: `/app/static/manifest.webmanifest?v=${{version}}` }});
  upsertLink('link[rel="apple-touch-icon"]', {{ rel: 'apple-touch-icon', href: `/app/static/pwa-icon-192.png?v=${{version}}` }});
  upsertLink('link[data-dh-pwa-icon="512"]', {{ rel: 'icon', type: 'image/png', sizes: '512x512', href: `/app/static/pwa-icon-512.png?v=${{version}}`, 'data-dh-pwa-icon': '512' }});
  upsertMeta('meta[name="theme-color"]', {{ name: 'theme-color', content: '#081424' }});
  upsertMeta('meta[name="mobile-web-app-capable"]', {{ name: 'mobile-web-app-capable', content: 'yes' }});
  upsertMeta('meta[name="apple-mobile-web-app-capable"]', {{ name: 'apple-mobile-web-app-capable', content: 'yes' }});
  upsertMeta('meta[name="apple-mobile-web-app-status-bar-style"]', {{ name: 'apple-mobile-web-app-status-bar-style', content: 'black-translucent' }});
  upsertMeta('meta[name="apple-mobile-web-app-title"]', {{ name: 'apple-mobile-web-app-title', content: 'DietHealth' }});

  const nav = rootWin.navigator || navigator;
  if (!nav || !('serviceWorker' in nav)) return;

  const swUrl = `/app/static/service-worker.js?v=${{version}}`;
  const registerSw = () =>
    nav.serviceWorker.register(swUrl, {{ scope: '/' }})
      .catch(() => nav.serviceWorker.register(swUrl).catch(() => null));
  registerSw();

  let deferredPrompt = null;
  const isStandalone = () =>
    (rootWin.matchMedia && rootWin.matchMedia('(display-mode: standalone)').matches) ||
    (rootWin.navigator && rootWin.navigator.standalone);

  const bindInstallHandler = (btn) => {{
    if (!btn || btn.dataset.dhPwaBound === '1') return;
    btn.dataset.dhPwaBound = '1';
    btn.addEventListener('click', async () => {{
      if (deferredPrompt) {{
        deferredPrompt.prompt();
        try {{
          await deferredPrompt.userChoice;
        }} catch (e) {{}}
        deferredPrompt = null;
        const floating = rootDoc.getElementById('dh-pwa-install');
        if (floating) floating.remove();
        return;
      }}
      if (rootDoc.getElementById('dh-pwa-guide')) return;
      const guide = rootDoc.createElement('div');
      guide.id = 'dh-pwa-guide';
      guide.className = 'dh-pwa-guide';
      guide.innerHTML = `
        <div class="dh-pwa-guide-card">
          <div class="dh-pwa-guide-title">Instalar DietHealth</div>
          <div class="dh-pwa-guide-text">
            No iPhone: toque em Compartilhar → Adicionar à Tela de Início.<br/>
            No Android/Chrome: menu ⋮ → Instalar app.
          </div>
          <button type="button" class="dh-pwa-guide-close">Fechar</button>
        </div>
      `;
      rootDoc.body.appendChild(guide);
      const closeBtn = guide.querySelector('.dh-pwa-guide-close');
      if (closeBtn) {{
        closeBtn.addEventListener('click', () => {{
          try {{ guide.remove(); }} catch (e) {{}}
        }});
      }}
    }});
  }};

  const ensureInstallButton = () => {{
    if (isStandalone()) {{
      const inlineBtn = rootDoc.getElementById('dh-pwa-install-inline');
      if (inlineBtn) inlineBtn.style.display = 'none';
      const floating = rootDoc.getElementById('dh-pwa-install');
      if (floating) floating.remove();
      return;
    }}
    const inlineBtn = rootDoc.getElementById('dh-pwa-install-inline');
    if (inlineBtn) {{
      inlineBtn.style.display = '';
      bindInstallHandler(inlineBtn);
      return;
    }}
    if (rootDoc.getElementById('dh-pwa-install')) return;
    const btn = rootDoc.createElement('button');
    btn.id = 'dh-pwa-install';
    btn.type = 'button';
    btn.textContent = 'Instalar app';
    btn.className = 'dh-pwa-install-btn';
    bindInstallHandler(btn);
    rootDoc.body.appendChild(btn);
  }};

  rootWin.addEventListener('beforeinstallprompt', (e) => {{
    e.preventDefault();
    deferredPrompt = e;
    ensureInstallButton();
  }});

  rootWin.addEventListener('appinstalled', () => {{
    deferredPrompt = null;
    const btn = rootDoc.getElementById('dh-pwa-install');
    if (btn) btn.remove();
  }});

  if (!isStandalone()) {{
    // Exibe o botao mesmo sem prompt para orientar instalacao manual (iOS/Android).
    rootWin.setTimeout(() => {{
      ensureInstallButton();
    }}, 1200);
  }}
}})();
</script>
""",
        height=0,
        width=0,
    )

    st.markdown(
        """
        <style>
        div[data-baseweb="popover"] div[class*="st-key-lp_login_pop_shell"] .dh-auth-pop-head h3,
        div[data-baseweb="popover"] div[class*="st-key-lp_register_pop_shell"] .dh-auth-pop-head h3,
        div[data-testid="stPopover"] div[class*="st-key-lp_login_pop_shell"] .dh-auth-pop-head h3,
        div[data-testid="stPopover"] div[class*="st-key-lp_register_pop_shell"] .dh-auth-pop-head h3,
        div[class*="st-key-lp_login_pop_shell"] .dh-auth-pop-head h3,
        div[class*="st-key-lp_register_pop_shell"] .dh-auth-pop-head h3{
          color:#F8FBFF !important;
          -webkit-text-fill-color:#F8FBFF !important;
          opacity:1 !important;
          filter:none !important;
          text-shadow:none !important;
          font-weight:900 !important;
        }

        div[data-baseweb="popover"] div[class*="st-key-lp_login_pop_shell"] .dh-auth-pop-subtitle,
        div[data-baseweb="popover"] div[class*="st-key-lp_register_pop_shell"] .dh-auth-pop-subtitle,
        div[data-testid="stPopover"] div[class*="st-key-lp_login_pop_shell"] .dh-auth-pop-subtitle,
        div[data-testid="stPopover"] div[class*="st-key-lp_register_pop_shell"] .dh-auth-pop-subtitle,
        div[class*="st-key-lp_login_pop_shell"] .dh-auth-pop-subtitle,
        div[class*="st-key-lp_register_pop_shell"] .dh-auth-pop-subtitle{
          color:#D9E7F5 !important;
          -webkit-text-fill-color:#D9E7F5 !important;
          opacity:1 !important;
          filter:none !important;
          text-shadow:none !important;
          font-weight:600 !important;
        }

        div[data-baseweb="popover"] div[class*="st-key-lp_login_pop_body"] [data-testid="stWidgetLabel"] *,
        div[data-baseweb="popover"] div[class*="st-key-lp_register_pop_body"] [data-testid="stWidgetLabel"] *,
        div[data-testid="stPopover"] div[class*="st-key-lp_login_pop_body"] [data-testid="stWidgetLabel"] *,
        div[data-testid="stPopover"] div[class*="st-key-lp_register_pop_body"] [data-testid="stWidgetLabel"] *,
        div[class*="st-key-lp_login_pop_body"] [data-testid="stWidgetLabel"] *,
        div[class*="st-key-lp_register_pop_body"] [data-testid="stWidgetLabel"] *{
          color:#D6E3F1 !important;
          -webkit-text-fill-color:#D6E3F1 !important;
          opacity:1 !important;
          filter:none !important;
          text-shadow:none !important;
        }

        div[data-baseweb="popover"] div[class*="st-key-lp_login_pop_shell"] [data-testid="stMarkdownContainer"] *,
        div[data-baseweb="popover"] div[class*="st-key-lp_register_pop_shell"] [data-testid="stMarkdownContainer"] *,
        div[data-testid="stPopover"] div[class*="st-key-lp_login_pop_shell"] [data-testid="stMarkdownContainer"] *,
        div[data-testid="stPopover"] div[class*="st-key-lp_register_pop_shell"] [data-testid="stMarkdownContainer"] *,
        div[class*="st-key-lp_login_pop_shell"] [data-testid="stMarkdownContainer"] *,
        div[class*="st-key-lp_register_pop_shell"] [data-testid="stMarkdownContainer"] *{
          opacity:1 !important;
          filter:none !important;
        }

        .dh-pwa-install-btn{
          position: fixed;
          right: 18px;
          bottom: 18px;
          z-index: 2000;
          min-height: 42px;
          padding: 0 16px;
          border-radius: 999px;
          border: 1px solid rgba(120, 255, 199, 0.5);
          background: linear-gradient(180deg, rgba(8, 30, 40, 0.95), rgba(6, 22, 32, 0.9));
          color: #ecfff6;
          font-weight: 700;
          font-size: 0.95rem;
          box-shadow: 0 12px 24px rgba(0,0,0,0.28);
          cursor: pointer;
        }
        .dh-pwa-install-btn:hover{
          transform: translateY(-1px);
          filter: brightness(1.05);
        }
        .dh-pwa-guide{
          position: fixed;
          right: 18px;
          bottom: 72px;
          z-index: 2000;
          max-width: 320px;
        }
        .dh-pwa-guide-card{
          background: linear-gradient(180deg, rgba(6, 20, 32, 0.98), rgba(6, 18, 28, 0.94));
          border: 1px solid rgba(120, 255, 199, 0.24);
          border-radius: 16px;
          padding: 14px 16px;
          box-shadow: 0 16px 32px rgba(0,0,0,0.32);
          color: #E9FFF5;
          font-family: "Poppins", "Montserrat", "Segoe UI", sans-serif;
          display: grid;
          gap: 8px;
        }
        .dh-pwa-guide-title{
          font-weight: 800;
          font-size: 0.95rem;
        }
        .dh-pwa-guide-text{
          font-size: 0.88rem;
          color: rgba(219, 246, 236, 0.92);
          line-height: 1.45;
        }
        .dh-pwa-guide-close{
          border: 1px solid rgba(120, 255, 199, 0.28);
          background: rgba(8, 30, 40, 0.85);
          color: #F0FFF8;
          border-radius: 999px;
          padding: 6px 12px;
          font-size: 0.78rem;
          font-weight: 700;
          cursor: pointer;
        }
        @media (max-width: 760px){
          .dh-pwa-guide{
            right: 12px;
            left: 12px;
            bottom: 72px;
            max-width: none;
          }
          .dh-pwa-guide-card{
            border-radius: 14px;
          }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    st.markdown('<div id="dh-auth-anchor"></div>', unsafe_allow_html=True)
    st.markdown('<div style="height:12px"></div>', unsafe_allow_html=True)

    st.session_state["landing_auth_mode"] = ""
    auth_mode = (st.session_state.get("landing_auth_mode") or "").strip().lower()
    if False and auth_mode in ("login", "cadastro"):
        auth_h1, auth_h2 = st.columns([0.88, 0.12], gap="small", vertical_alignment="center")
        with auth_h1:
            if auth_mode == "login":
                st.markdown("### 🔐 Entrar no Sistema")
                st.caption("Entre com seu usuario e senha para continuar.")
            else:
                st.markdown("### Criar Conta")
                st.caption("Preencha seus dados para criar sua conta.")
        with auth_h2:
            if st.button("Fechar", key="lp_close_auth", use_container_width=True):
                st.session_state["landing_auth_mode"] = ""
                st.rerun()

        if auth_mode == "login":
            with st.form("login_form"):
                u = st.text_input("Usuario", placeholder="admin")
                s = st.text_input("Senha", type="password", placeholder="123")
                if st.form_submit_button("ENTRAR AGORA"):
                    u_norm = (u or "").strip().lower()
                    user = next(
                        (x for x in users if (x.get("usuario") or "").strip().lower() == u_norm and x.get("senha") == s),
                        None,
                    )
                    if user:
                        ok, reason, venc = _check_user_access(user)
                        if not ok and reason in ("pending", "blocked"):
                            try:
                                if mp_try_auto_activate_user(user):
                                    ok, reason, venc = _check_user_access(user)
                            except Exception:
                                pass
                        if ok:
                            st.session_state["login_blocked_user"] = ""
                            st.session_state["login_blocked_reason"] = ""
                            st.session_state["login_blocked_venc"] = ""
                            st.session_state["login_verified_user"] = ""
                            st.session_state["login_verified_tipo"] = ""
                            st.session_state["login_verified_at"] = 0.0
                            st.session_state["logado"] = True
                            st.session_state["usuario"] = (user.get("usuario") or "").strip().lower()
                            st.session_state["tipo"] = user.get("tipo", "user")
                            _persist_login_query(st.session_state["usuario"])
                            _touch_user_presence(force=True)
                            st.rerun()
                        else:
                            blocked_u = (user.get("usuario") or "").strip().lower()
                            st.session_state["login_blocked_user"] = blocked_u
                            st.session_state["login_blocked_reason"] = reason
                            st.session_state["login_blocked_venc"] = str(venc) if venc else ""
                            st.session_state["login_verified_user"] = blocked_u
                            st.session_state["login_verified_tipo"] = user.get("tipo", "user")
                            st.session_state["login_verified_at"] = float(time.time())
                            if reason == "blocked":
                                st.error("Acesso bloqueado. Procure o admin para liberar.")
                            else:
                                st.error("Cadastro pendente de pagamento/liberacao.")
                    else:
                        st.session_state["login_blocked_user"] = ""
                        st.session_state["login_blocked_reason"] = ""
                        st.session_state["login_blocked_venc"] = ""
                        st.session_state["login_verified_user"] = ""
                        st.session_state["login_verified_tipo"] = ""
                        st.session_state["login_verified_at"] = 0.0
                        st.error("Dados incorretos!")

            blocked_user = (st.session_state.get("login_blocked_user") or "").strip().lower()
            if blocked_user:
                st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
                blocked_reason = (st.session_state.get("login_blocked_reason") or "").strip().lower()
                blocked_venc = (st.session_state.get("login_blocked_venc") or "").strip()
                if blocked_reason in ("pending", "blocked"):
                    st.error("Cadastro pendente de pagamento/liberacao.")
                st.caption("Para liberacao automatica, use o pagamento gerado aqui para identificar seu usuario.")
                u_obj = next((x for x in users if (x.get("usuario") or "").strip().lower() == blocked_user), None)

                if u_obj and _mp_access_token():
                    col_p1, col_p2 = st.columns([1, 1])
                    if col_p1.button("Gerar link de pagamento", key="mp_gen_link_login"):
                        url_gen = mp_get_cached_checkout_url(u_obj, force_new=True)
                        if url_gen:
                            st.success("Link gerado. Clique em pagar abaixo.")
                        else:
                            st.error((st.session_state.get("mp_checkout_last_err") or "").strip() or "Nao foi possivel gerar o link agora.")

                    url = ""
                    if st.session_state.get("mp_checkout_user") == blocked_user:
                        url = (st.session_state.get("mp_checkout_url") or "").strip()
                    if url:
                        st.link_button("PAGAR AGORA (Pix/Cartão)", url, type="primary")
                    else:
                        st.info("Clique em Gerar link de pagamento para abrir Pix/Cartão.")

                    if col_p2.button("Ja paguei - verificar", key="mp_check_login"):
                        if mp_try_auto_activate_user(u_obj):
                            st.session_state["login_blocked_user"] = ""
                            st.session_state["login_blocked_reason"] = ""
                            st.session_state["login_blocked_venc"] = ""
                            verified_user = (st.session_state.get("login_verified_user") or "").strip().lower()
                            verified_tipo = (st.session_state.get("login_verified_tipo") or u_obj.get("tipo") or "user")
                            verified_at = float(st.session_state.get("login_verified_at") or 0.0)
                            can_auto_login = (verified_user == blocked_user) and ((time.time() - verified_at) <= 15 * 60)
                            if can_auto_login:
                                st.session_state["logado"] = True
                                st.session_state["usuario"] = blocked_user
                                st.session_state["tipo"] = verified_tipo
                                _persist_login_query(st.session_state["usuario"])
                                st.session_state["login_verified_user"] = ""
                                st.session_state["login_verified_tipo"] = ""
                                st.session_state["login_verified_at"] = 0.0
                                _touch_user_presence(force=True)
                                st.success("Pagamento confirmado! Acesso liberado. Entrando no sistema...")
                                time.sleep(0.3)
                            else:
                                st.success("Pagamento confirmado! Seu acesso foi liberado. Faca login novamente.")
                            st.rerun()
                        else:
                            st.warning("Ainda nao encontrei pagamento aprovado para seu usuario. Aguarde e tente novamente.")
                else:
                    if not _mp_access_token():
                        st.caption("Liberacao automatica depende de configurar MERCADO_PAGO_ACCESS_TOKEN no servidor.")
        else:
            with st.form("register_form"):
                tipo_conta = st.radio("Tipo de acesso", ["Nutricionista", "Atendimento Virtual"], horizontal=True, key="reg_tipo_conta_legacy")
                nome_r = st.text_input("Nome completo", key="reg_nome")
                cpf_r = st.text_input("CPF", key="reg_cpf", placeholder="000.000.000-00")
                email_r = st.text_input("Email", key="reg_email")
                tel_r = st.text_input("WhatsApp", key="reg_tel")
                user_r = st.text_input("Usuario", key="reg_user")
                pass_r = st.text_input("Senha", type="password", key="reg_pass")
                pass_r2 = st.text_input("Confirmar senha", type="password", key="reg_pass2")
                if st.form_submit_button("CRIAR CONTA"):
                    u_norm = (user_r or "").strip().lower()
                    cpf_norm = _normalize_cpf(cpf_r)
                    email_clean = (email_r or "").strip()
                    tel_clean = (tel_r or "").strip()
                    trial_until = None
                    signup_access_type = (tipo_conta or "").strip().lower()
                    is_virtual_signup = signup_access_type == "atendimento virtual"
                    if not u_norm or not pass_r:
                        st.error("Usuario e senha sao obrigatorios.")
                    elif pass_r != pass_r2:
                        st.error("As senhas nao conferem.")
                    elif not cpf_norm:
                        st.error("CPF e obrigatorio.")
                    elif not _is_valid_cpf(cpf_norm):
                        st.error("Informe um CPF valido.")
                    elif _cpf_already_exists(cpf_norm):
                        st.error("Ja existe cadastro com este CPF.")
                    elif not email_clean:
                        st.error("Email e obrigatorio.")
                    elif not _is_valid_email(email_clean):
                        st.error("Informe um email valido.")
                    elif not tel_clean:
                        st.error("Celular/WhatsApp e obrigatorio.")
                    elif not _is_valid_celular(tel_clean):
                        st.error("Informe um celular valido com DDD.")
                    elif any((x.get("usuario") or "").strip().lower() == u_norm for x in users):
                        st.error("Usuario ja existe.")
                    else:
                        new_user = {
                            "signup_id": _new_signup_id(),
                            "nome": nome_r,
                            "cpf": cpf_norm,
                            "usuario": u_norm,
                            "senha": pass_r,
                            "tipo": "user",
                            "status": "active",
                            "paid_until": "",
                            "wa_provider": "wapi",
                            "wa_token": "",
                            "wa_phone_id": "",
                            "wa_api_url": "",
                            "wa_instance": "",
                            "wa_notify_admin_num": "",
                            "email": email_clean,
                            "telefone": tel_clean,
                            "created_at": str(datetime.now().date()),
                            "signup_access_type": "virtual" if is_virtual_signup else "traditional",
                            "experience_preference": "virtual" if is_virtual_signup else "traditional",
                        }
                        users.append(new_user)
                        save_db("users.json", users)
                        if is_virtual_signup:
                            st.success("Cadastro do Atendimento Virtual criado! Acesso liberado no plano básico.")
                        else:
                            st.success("Cadastro criado! Acesso liberado no plano básico.")
                        wa_ok, wa_msg = _notify_admin_new_signup(new_user)
                        if wa_ok:
                            st.caption(f"Notificacao enviada para API do admin ({wa_msg}).")
                        else:
                            st.warning(f"Cadastro salvo, mas nao foi possivel notificar o admin no WhatsApp: {wa_msg}")
                        if is_virtual_signup:
                            st.link_button("Assinar Atendimento Virtual", MERCADO_PAGO_VIRTUAL)
                        elif _mp_access_token():
                            u_obj_new = next((x for x in users if (x.get("usuario") or "").strip().lower() == u_norm), None)
                            info, err = mp_create_checkout_link(u_obj_new) if u_obj_new else (None, "Usuario nao encontrado.")
                            if info and (info.get("url") or "").strip():
                                st.link_button("Assinar agora (opcional)", info["url"])
                            elif err:
                                st.caption(err)
                        else:
                            st.caption("Pagamento online automatico depende de MERCADO_PAGO_ACCESS_TOKEN no servidor.")

# =============================================================================
# 8B. ATENDIMENTO VIRTUAL CAMILA
# =============================================================================
def _camila_default_profile() -> dict:
    return {
        "nome_preferido": "",
        "objetivo": "",
        "idade_informada": "",
        "sexo_informado": "",
        "deficiencia_informada": "",
        "rotina_alimentar": "",
        "rotina_trabalho": "",
        "horarios": "",
        "agua_litros": "",
        "sono_horas": "",
        "atividade_fisica": "",
        "cafe_manha": "",
        "almoco_rotina": "",
        "jantar_rotina": "",
        "faz_lanches": "",
        "dificuldades_rotina": "",
        "come_fora": "",
        "pula_refeicoes": "",
        "preferencias": "",
        "aversoes": "",
        "sintomas": "",
        "alergias_confirmadas": "",
        "intolerancias_confirmadas": "",
        "doencas_informadas": "",
        "medicamentos_uso": "",
        "gestacao_lactacao": "",
        "peso_informado": "",
        "altura_informada": "",
        "resumo_atendimento": "",
        "chat_stage": "intro",
        "chat_case_status": "",
        "chat_ready_for_diet": False,
        "dieta_rascunho": "",
        "dieta_logica_resumo": "",
        "dieta_ajuste_pedido": "",
        "dieta_versao": 0,
        "dieta_ultima_geracao": "",
        "orientacoes_custom": "",
        "comentario_evolucao": "",
        "ultima_atualizacao": "",
    }


def _camila_virtual_user_record(user_obj: dict) -> dict:
    if not isinstance(user_obj, dict):
        return None
    base_profile = user_obj.setdefault("camila_virtual_profile", _camila_default_profile())
    for key, value in _camila_default_profile().items():
        base_profile.setdefault(key, value)
    if _clean_text(user_obj.get("nome")) and not _clean_text(base_profile.get("nome_preferido")):
        base_profile["nome_preferido"] = _clean_text(user_obj.get("nome"))
    return {
        "__camila_ctx_type": "user",
        "__camila_user_ref": user_obj,
        "id": f"camila_user_{(user_obj.get('signup_id') or user_obj.get('usuario') or user_obj.get('cpf') or uuid.uuid4().hex)}",
        "nome": _clean_text(user_obj.get("nome")) or "Usuário",
        "email": _clean_text(user_obj.get("email")),
        "telefone": _clean_text(user_obj.get("telefone")),
        "cpf": _normalize_cpf(user_obj.get("cpf") or ""),
        "sexo": _clean_text(user_obj.get("sexo")),
        "idade": _clean_text(user_obj.get("idade")),
        "cidade": _clean_text(user_obj.get("cidade")),
        "historico": list(user_obj.get("camila_virtual_history") or []),
        "anamnese": dict(user_obj.get("camila_virtual_anamnese") or {}),
        "camila_virtual": base_profile,
    }


def _camila_patient_context():
    role = (st.session_state.get("tipo") or "").strip().lower()
    user_obj = _get_user_obj()
    return user_obj, _camila_virtual_user_record(user_obj), role


def _camila_profile(p_obj: dict) -> dict:
    if not p_obj:
        return _camila_default_profile()
    base = p_obj.setdefault("camila_virtual", _camila_default_profile())
    for key, value in _camila_default_profile().items():
        base.setdefault(key, value)
    return base


def _camila_save_profile(p_obj: dict, updates: dict):
    if not p_obj:
        return
    profile = _camila_profile(p_obj)
    for key, value in (updates or {}).items():
        profile[key] = value
    profile["ultima_atualizacao"] = datetime.now().strftime("%d/%m/%Y %H:%M")
    if (p_obj.get("__camila_ctx_type") or "").strip().lower() == "user":
        user_ref = p_obj.get("__camila_user_ref")
        if isinstance(user_ref, dict):
            user_ref["camila_virtual_profile"] = profile
            save_db("users.json", users)
        return
    save_db("pacientes.json", pacientes)


def _camila_chat_key(p_obj: dict) -> str:
    base = (p_obj or {}).get("cpf") or (p_obj or {}).get("documento") or (p_obj or {}).get("nome") or "default"
    safe = re.sub(r"[^a-zA-Z0-9_]+", "_", str(base))
    return f"dh_camila_chat_{safe}"


def _camila_chat_messages(p_obj: dict) -> list:
    key = _camila_chat_key(p_obj)
    if key not in st.session_state:
        st.session_state[key] = []
    return st.session_state[key]


def _camila_append_message(p_obj: dict, role: str, content: str):
    if not content:
        return
    _camila_chat_messages(p_obj).append({"role": role, "content": content})


def _camila_numeric_text(raw) -> str:
    txt = str(raw or "").strip().replace(",", ".")
    return txt


def _camila_yes_no(text: str) -> str:
    low = (text or "").strip().lower()
    if any(x in low for x in ["sim", "faço", "faco", "tenho", "positivo"]):
        return "Sim"
    if any(x in low for x in ["não", "nao", "nunca", "negativo"]):
        return "Não"
    return (text or "").strip()


def _camila_existing_value(profile: dict, p_obj: dict, anamnese: dict, field: str):
    mapping = {
        "nome_preferido": profile.get("nome_preferido") or (p_obj or {}).get("nome"),
        "objetivo": profile.get("objetivo") or _clean_text((anamnese or {}).get("queixa_principal")) or (p_obj or {}).get("objetivo"),
        "idade_informada": profile.get("idade_informada") or (p_obj or {}).get("idade"),
        "sexo_informado": profile.get("sexo_informado") or (p_obj or {}).get("sexo"),
        "deficiencia_informada": profile.get("deficiencia_informada"),
        "peso_informado": profile.get("peso_informado") or (get_ultimos_dados(p_obj) or {}).get("peso"),
        "altura_informada": profile.get("altura_informada") or (get_ultimos_dados(p_obj) or {}).get("altura"),
        "atividade_fisica": profile.get("atividade_fisica"),
        "sono_horas": profile.get("sono_horas"),
        "agua_litros": profile.get("agua_litros"),
        "cafe_manha": profile.get("cafe_manha"),
        "almoco_rotina": profile.get("almoco_rotina"),
        "jantar_rotina": profile.get("jantar_rotina"),
        "faz_lanches": profile.get("faz_lanches"),
        "horarios": profile.get("horarios"),
        "dificuldades_rotina": profile.get("dificuldades_rotina"),
        "come_fora": profile.get("come_fora"),
        "pula_refeicoes": profile.get("pula_refeicoes"),
        "alergias_confirmadas": profile.get("alergias_confirmadas") or _clean_text((anamnese or {}).get("alergias")),
        "intolerancias_confirmadas": profile.get("intolerancias_confirmadas") or _clean_text((anamnese or {}).get("intolerancias")),
        "aversoes": profile.get("aversoes"),
        "preferencias": profile.get("preferencias"),
        "doencas_informadas": profile.get("doencas_informadas") or _clean_text((anamnese or {}).get("condicoes_saude")),
        "sintomas": profile.get("sintomas"),
        "medicamentos_uso": profile.get("medicamentos_uso") or _clean_text((anamnese or {}).get("medicamentos_suplementos")),
        "gestacao_lactacao": profile.get("gestacao_lactacao"),
    }
    val = mapping.get(field)
    if val is None:
        return ""
    return str(val).strip()


def _camila_flow_sequence() -> list[tuple[str, str]]:
    return [
        ("nome_preferido", "Para começar, como você prefere ser chamado(a)?"),
        ("objetivo", "Qual é o seu objetivo principal com o atendimento nutricional?"),
        ("idade_informada", "Qual é a sua idade?"),
        ("sexo_informado", "Qual é o seu sexo?"),
        ("peso_informado", "Qual é o seu peso atual?"),
        ("altura_informada", "Qual é a sua altura atual?"),
        ("deficiencia_informada", "Existe alguma deficiência, limitação ou condição especial que eu precise considerar?"),
        ("rotina_trabalho", "Como é sua rotina de trabalho ou estudo no dia a dia?"),
        ("atividade_fisica", "Como está seu nível de atividade física hoje?"),
        ("sono_horas", "Como está seu sono? Quantas horas costuma dormir por noite?"),
        ("agua_litros", "Quanto de água você costuma beber por dia?"),
        ("cafe_manha", "Como costuma ser seu café da manhã?"),
        ("almoco_rotina", "Como costuma ser seu almoço?"),
        ("jantar_rotina", "Como costuma ser seu jantar?"),
        ("faz_lanches", "Você costuma fazer lanches entre as refeições?"),
        ("horarios", "Quais são seus horários de refeição ao longo do dia?"),
        ("dificuldades_rotina", "Qual é a maior dificuldade da sua rotina alimentar hoje?"),
        ("come_fora", "Você costuma comer fora de casa com frequência?"),
        ("pula_refeicoes", "Você costuma pular refeições?"),
        ("alergias_confirmadas", "Você tem alguma alergia alimentar?"),
        ("intolerancias_confirmadas", "Existe alguma intolerância alimentar que eu precise considerar?"),
        ("aversoes", "Existe algum alimento que você não gosta ou evita?"),
        ("preferencias", "Tem alguma preferência alimentar que eu deva respeitar?"),
        ("doencas_informadas", "Existe alguma doença ou condição de saúde já conhecida?"),
        ("sintomas", "Você tem sintomas digestivos ou desconfortos que aparecem com frequência?"),
        ("medicamentos_uso", "Você usa algum medicamento ou suplemento com frequência?"),
        ("gestacao_lactacao", "Existe gestação ou lactação em andamento?"),
    ]


def _camila_field_prompt(field: str) -> str:
    return dict(_camila_flow_sequence()).get(field, "")


def _camila_next_missing_field(p_obj: dict) -> str:
    profile = _camila_profile(p_obj)
    anamnese = get_anamnese_paciente(p_obj)
    for field, _prompt in _camila_flow_sequence():
        if not _camila_existing_value(profile, p_obj, anamnese, field):
            return field
    return ""


def _camila_store_field_answer(p_obj: dict, field: str, answer: str):
    txt = (answer or "").strip()
    if not txt:
        return
    if field in {"faz_lanches", "come_fora", "pula_refeicoes", "gestacao_lactacao"}:
        txt = _camila_yes_no(txt)
    _camila_save_profile(p_obj, {field: txt})


def _camila_validate_stage_answer(field: str, answer: str) -> str:
    txt = (answer or "").strip()
    if field == "idade_informada":
        num = pd.to_numeric(_camila_numeric_text(txt), errors="coerce")
        if pd.isna(num) or float(num) <= 0 or float(num) > 120:
            return "Me confirme sua idade em anos, por favor."
    if field == "peso_informado":
        num = pd.to_numeric(_camila_numeric_text(txt), errors="coerce")
        if pd.isna(num) or float(num) <= 0 or float(num) > 500:
            return "Pode me passar seu peso atual em kg? Exemplo: 72,5."
    if field == "altura_informada":
        num = pd.to_numeric(_camila_numeric_text(txt), errors="coerce")
        if pd.isna(num) or float(num) <= 0:
            return "Pode me informar sua altura? Exemplo: 1,68."
    return ""


def _camila_knowledge_topics(p_obj: dict) -> list[dict]:
    profile = _camila_profile(p_obj)
    anamnese = get_anamnese_paciente(p_obj)
    return _clinical_ai_topics(
        _camila_existing_value(profile, p_obj, anamnese, "objetivo"),
        _camila_existing_value(profile, p_obj, anamnese, "deficiencia_informada"),
        _camila_existing_value(profile, p_obj, anamnese, "alergias_confirmadas"),
        _camila_existing_value(profile, p_obj, anamnese, "intolerancias_confirmadas"),
        _camila_existing_value(profile, p_obj, anamnese, "doencas_informadas"),
        _camila_existing_value(profile, p_obj, anamnese, "sintomas"),
        _camila_existing_value(profile, p_obj, anamnese, "medicamentos_uso"),
    )


def _camila_triage_result(p_obj: dict) -> tuple[bool, list[str]]:
    profile = _camila_profile(p_obj)
    anamnese = get_anamnese_paciente(p_obj)
    alerts = []

    idade_txt = _camila_existing_value(profile, p_obj, anamnese, "idade_informada")
    idade_num = pd.to_numeric(_camila_numeric_text(idade_txt), errors="coerce")
    if pd.notna(idade_num) and float(idade_num) < 18:
        alerts.append("menor de idade")

    gest = _camila_existing_value(profile, p_obj, anamnese, "gestacao_lactacao").lower()
    if any(x in gest for x in ["sim", "gest", "lacta"]):
        alerts.append("gestação ou lactação")

    alergias = _camila_existing_value(profile, p_obj, anamnese, "alergias_confirmadas").lower()
    if any(x in alergias for x in ["anafil", "grave", "severa", "severo"]):
        alerts.append("alergia grave")

    condicoes = _camila_existing_value(profile, p_obj, anamnese, "doencas_informadas").lower()
    if any(x in condicoes for x in ["diabetes", "renal", "rim", "cancer", "hipertens", "pressão alta", "pressao alta", "cirurgia", "transtorno alimentar"]):
        alerts.append("doença relevante")
    if any(x in condicoes for x in ["dm1", "dialise", "diálise", "nefrop", "cirrose", "depress", "bulimi", "anorex", "compuls", "insuficiencia cardiaca", "insuficiência cardíaca"]):
        alerts.append("condição que exige revisão especializada")

    sintomas = _camila_existing_value(profile, p_obj, anamnese, "sintomas").lower()
    if any(x in sintomas for x in ["sangue", "desmaio", "dor forte", "dor intensa", "febre", "vomit", "diarreia persist", "diarreia constante"]):
        alerts.append("sinal de alerta")
    if any(x in sintomas for x in ["hipoglic", "hiperglic", "ceto", "ulcera", "úlcera", "ferida no pe", "ferida no pé", "ideacao suic", "ideação suic", "vomitos repetidos"]):
        alerts.append("sintoma ou complicação que exige revisão")

    restriction_count = sum(
        1 for txt in [
            _camila_existing_value(profile, p_obj, anamnese, "alergias_confirmadas"),
            _camila_existing_value(profile, p_obj, anamnese, "intolerancias_confirmadas"),
            _camila_existing_value(profile, p_obj, anamnese, "doencas_informadas"),
        ] if txt
    )
    if restriction_count >= 3:
        alerts.append("múltiplas restrições")

    knowledge_notes = collect_camila_triage_notes(_camila_knowledge_topics(p_obj))
    for note in knowledge_notes:
        low_note = normalize_text(note)
        if any(token in low_note for token in ["exige revisao", "exigem revisao", "imediata", "dialise", "fragilidade", "menor de idade"]):
            alerts.append(note)

    alerts = list(dict.fromkeys(alerts))
    return bool(alerts), alerts


def _camila_profile_summary(p_obj: dict) -> str:
    profile = _camila_profile(p_obj)
    anamnese = get_anamnese_paciente(p_obj)
    objetivo = _camila_existing_value(profile, p_obj, anamnese, "objetivo") or "sem objetivo definido"
    idade = _camila_existing_value(profile, p_obj, anamnese, "idade_informada") or "idade não informada"
    sexo = _camila_existing_value(profile, p_obj, anamnese, "sexo_informado") or "sexo não informado"
    peso = _camila_existing_value(profile, p_obj, anamnese, "peso_informado") or "peso não informado"
    altura = _camila_existing_value(profile, p_obj, anamnese, "altura_informada") or "altura não informada"
    deficiencia = _camila_existing_value(profile, p_obj, anamnese, "deficiencia_informada") or "sem deficiência ou condição especial registrada"
    rotina = _camila_existing_value(profile, p_obj, anamnese, "rotina_trabalho") or "rotina ainda não detalhada"
    dificuldade = _camila_existing_value(profile, p_obj, anamnese, "dificuldades_rotina") or "sem dificuldade principal informada"
    preferencias = _camila_existing_value(profile, p_obj, anamnese, "preferencias") or "sem preferência importante registrada"
    restricoes = " | ".join(
        x for x in [
            _camila_existing_value(profile, p_obj, anamnese, "alergias_confirmadas"),
            _camila_existing_value(profile, p_obj, anamnese, "intolerancias_confirmadas"),
            _camila_existing_value(profile, p_obj, anamnese, "doencas_informadas"),
        ] if x
    ) or "sem restrições relevantes registradas"
    return (
        f"Entendi. Seu foco principal é {objetivo}, você informou idade {idade}, sexo {sexo}, peso {peso}, altura {altura} "
        f"e condição especial/deficiência {deficiencia}. Sua rotina é {rotina}, "
        f"sua maior dificuldade hoje é {dificuldade}, suas preferências atuais são {preferencias} "
        f"e eu preciso considerar: {restricoes}."
    )


def _camila_who_guidance_note() -> str:
    return "Vou seguir uma orientação inicial conservadora, alinhada a princípios gerais de saúde e segurança nutricional usados pela OMS, sem substituir avaliação humana quando o caso exigir."


def _camila_intro_messages(p_obj: dict):
    profile = _camila_profile(p_obj)
    messages = _camila_chat_messages(p_obj)
    if messages:
        return
    _camila_append_message(
        p_obj,
        "assistant",
        "Olá, eu sou a Camila, sua nutricionista virtual. Vou te ajudar com seu atendimento nutricional inicial, entender sua rotina e montar uma orientação prática para você.",
    )
    next_field = _camila_next_missing_field(p_obj)
    profile["chat_stage"] = next_field or "summary"
    save_db("pacientes.json", pacientes)
    if next_field:
        _camila_append_message(p_obj, "assistant", _camila_field_prompt(next_field))


def _camila_handle_summary_confirmation(p_obj: dict, user_text: str) -> str:
    low = (user_text or "").strip().lower()
    profile = _camila_profile(p_obj)
    if any(x in low for x in ["sim", "pode", "ok", "certo", "seguir", "pode seguir"]):
        diet_result = _camila_generate_virtual_diet(p_obj)
        guidance = _camila_generate_guidance(p_obj)
        _camila_save_profile(
            p_obj,
            {
                "dieta_rascunho": diet_result.get("text") or "",
                "dieta_logica_resumo": diet_result.get("logic") or "",
                "dieta_versao": diet_result.get("version") or 1,
                "dieta_ultima_geracao": datetime.now().strftime("%d/%m/%Y %H:%M"),
                "orientacoes_custom": guidance,
                "chat_stage": "completed",
                "chat_ready_for_diet": True,
            },
        )
        return "Perfeito. Agora já entendi seu perfil inicial e vou organizar uma proposta alimentar prática para você. Já deixei um rascunho inicial de dieta e orientações básicas disponíveis nas áreas da Camila."
    _camila_save_profile(p_obj, {"chat_stage": "summary_adjustment"})
    return "Sem problema. Me diga qual ponto você quer ajustar ou complementar antes de eu seguir para a proposta inicial."


def _camila_process_conversation(p_obj: dict, user_text: str) -> str:
    profile = _camila_profile(p_obj)
    current_stage = (profile.get("chat_stage") or "intro").strip().lower()
    clean_text = (user_text or "").strip()
    if not clean_text:
        return "Pode me responder com tranquilidade. Vou seguir passo a passo para deixar seu atendimento organizado."

    if current_stage == "completed":
        return f"{_camila_reply_text(p_obj, clean_text)} {_camila_who_guidance_note()}"

    if current_stage == "summary_confirm":
        return _camila_handle_summary_confirmation(p_obj, clean_text)

    if current_stage == "summary_adjustment":
        resumo_base = _camila_profile_summary(p_obj)
        _camila_save_profile(
            p_obj,
            {
                "resumo_atendimento": f"{resumo_base} Ajuste informado pelo cliente: {clean_text}",
                "chat_stage": "summary_confirm",
            },
        )
        return f"{resumo_base} Ajuste informado: {clean_text}. Posso seguir agora para organizar a proposta alimentar inicial?"

    if current_stage and current_stage != "completed":
        validation_msg = _camila_validate_stage_answer(current_stage, clean_text)
        if validation_msg:
            return validation_msg
        _camila_store_field_answer(p_obj, current_stage, clean_text)

    next_field = _camila_next_missing_field(p_obj)
    if next_field:
        _camila_save_profile(p_obj, {"chat_stage": next_field})
        return _camila_field_prompt(next_field)

    is_complex, alerts = _camila_triage_result(p_obj)
    summary_text = _camila_profile_summary(p_obj)
    updates = {
        "resumo_atendimento": summary_text,
        "chat_stage": "summary_confirm",
        "chat_case_status": "human_review" if is_complex else "basic_flow",
    }
    _camila_save_profile(p_obj, updates)
    triage_text = ""
    if is_complex:
        triage_text = (
            " Para sua segurança, esse ponto precisa de validação do nutricionista. "
            "Posso continuar com orientações iniciais básicas, mas esse caso exige acompanhamento humano."
            f" Pontos identificados: {', '.join(alerts)}."
        )
    return f"{summary_text}{triage_text} {_camila_who_guidance_note()} Posso seguir para montar sua proposta alimentar inicial?"


def _camila_latest_weight_points(p_obj: dict) -> list:
    pts = []
    for item in (p_obj or {}).get("historico", []) or []:
        dv = item.get("dados_vitais") or {}
        peso = pd.to_numeric(dv.get("peso"), errors="coerce")
        data_ref = pd.to_datetime(item.get("data"), errors="coerce")
        if pd.notna(peso) and pd.notna(data_ref):
            pts.append({"Data": data_ref, "Peso": float(peso), "Origem": "Histórico"})
    profile = _camila_profile(p_obj)
    peso_inf = pd.to_numeric(profile.get("peso_informado"), errors="coerce")
    if pd.notna(peso_inf):
        pts.append({"Data": pd.Timestamp.now(), "Peso": float(peso_inf), "Origem": "Camila"})
    pts.sort(key=lambda x: x["Data"])
    return pts


def _camila_header(p_obj: dict, compact: bool = False):
    profile = _camila_profile(p_obj)
    anamnese = get_anamnese_paciente(p_obj) if p_obj else {}
    ultimos = get_ultimos_dados(p_obj) if p_obj else {}
    objetivo = _clean_text(profile.get("objetivo") or anamnese.get("queixa_principal") or (p_obj or {}).get("objetivo"))
    nome = (p_obj or {}).get("nome") or "Cliente"
    ultima_atualizacao = profile.get("ultima_atualizacao") or ultimos.get("data") or "Agora"
    if compact:
        st.markdown(
            _html_block(
                f"""
<section class="dh-camila-minihead">
  <div class="dh-camila-minihead-main">
    <div class="dh-camila-mini-avatar">C</div>
    <div>
      <div class="dh-camila-mini-kicker">Camila</div>
      <div class="dh-camila-mini-sub">{html.escape(nome)}</div>
    </div>
  </div>
  <div class="dh-camila-mini-badge">Online</div>
</section>
"""
            ),
            unsafe_allow_html=True,
        )
        return
    st.markdown(
        _html_block(
            f"""
<div class="dh-camila-shell">
  <section class="dh-camila-hero dh-camila-hero-compact">
    <div class="dh-camila-hero-main">
      <div class="dh-camila-kicker-row">
        <div class="dh-camila-kicker">Nutricionista Virtual</div>
        <div class="dh-camila-status"><span></span>Online</div>
      </div>
      <div class="dh-camila-hero-title-row">
        <div class="dh-camila-avatar">C</div>
        <div>
          <h1>Camila</h1>
          <div class="dh-camila-subtitle">Olá, estou aqui para te ajudar com seu atendimento nutricional.</div>
        </div>
      </div>
      <div class="dh-camila-chip-row">
        <span class="dh-camila-chip">Atendimento guiado por IA</span>
        <span class="dh-camila-chip">Triagem segura</span>
        <span class="dh-camila-chip">Plano inicial</span>
      </div>
    </div>
    <div class="dh-camila-hero-side dh-camila-hero-side-compact">
      <div class="dh-camila-summary-card">
        <div class="dh-camila-summary-label">Cliente</div>
        <div class="dh-camila-summary-value">{html.escape(nome)}</div>
      </div>
      <div class="dh-camila-summary-card">
        <div class="dh-camila-summary-label">Objetivo</div>
        <div class="dh-camila-summary-text">{html.escape(objetivo or "Acolhimento inicial em andamento.")}</div>
      </div>
      <div class="dh-camila-summary-card">
        <div class="dh-camila-summary-label">Atualização</div>
        <div class="dh-camila-summary-text">{html.escape(str(ultima_atualizacao))}</div>
      </div>
    </div>
  </section>
</div>
"""
        ),
        unsafe_allow_html=True,
    )
    k1, k2, k3, k4 = st.columns(4)
    with k1:
        st.metric("Peso atual", str(ultimos.get("peso") or profile.get("peso_informado") or "-"))
    with k2:
        st.metric("IMC", f"{float(ultimos.get('imc')):.2f}" if ultimos.get("imc") not in (None, "") else "-")
    with k3:
        st.metric("Água/dia", str(profile.get("agua_litros") or "-"))
    with k4:
        st.metric("Sono", str(profile.get("sono_horas") or "-"))


def _camila_reply_text(p_obj: dict, user_text: str) -> str:
    txt = (user_text or "").strip()
    if not txt:
        return "Posso começar pelo seu objetivo, pelas medidas ou pela rotina alimentar. Me diga por onde você quer seguir."
    low = txt.lower()
    anamnese = get_anamnese_paciente(p_obj) if p_obj else {}
    restricoes = [x for x in [
        _clean_text(anamnese.get("alergias")),
        _clean_text(anamnese.get("intolerancias")),
        _clean_text(anamnese.get("condicoes_saude")),
    ] if x]
    if any(term in low for term in ["diabetes", "pressão", "hipertensão", "rim", "renal", "gravidez", "gestante", "febre", "dor forte"]):
        return "Entendi. Esse ponto merece acompanhamento humano direto. Posso organizar suas informações e te orientar de forma geral, mas casos clínicos mais delicados precisam de avaliação profissional individual."
    if any(term in low for term in ["dieta", "plano", "cardápio"]):
        return "Eu consigo montar um rascunho inicial prático com base no seu objetivo, rotina e restrições. Antes disso, confirme peso, altura, horários e se existe alguma alergia, intolerância ou condição de saúde relevante."
    if any(term in low for term in ["água", "hidratação"]):
        return "Uma meta inicial simples é distribuir água ao longo do dia, especialmente entre refeições. Se quiser, eu organizo uma rotina de hidratação compatível com seus horários."
    if any(term in low for term in ["peso", "imc", "medida", "altura"]):
        return "Posso organizar suas medidas básicas agora. Me passe peso, altura e qualquer outra medida importante que você queira acompanhar."
    if restricoes:
        return f"Já considerei estas restrições no atendimento: {'; '.join(restricoes)}. Posso seguir com orientações gerais e um plano inicial seguro dentro desse contexto."
    return "Perfeito. Vou manter o atendimento de forma simples e organizada. Posso seguir com objetivo, rotina alimentar, medidas ou rascunho de dieta inicial."


def _camila_generate_draft(p_obj: dict) -> str:
    if not p_obj:
        return ""
    profile = _camila_profile(p_obj)
    anamnese = get_anamnese_paciente(p_obj)
    ultimos = get_ultimos_dados(p_obj)
    objetivo = _clean_text(profile.get("objetivo") or anamnese.get("queixa_principal")) or "melhorar rotina alimentar"
    horarios = _clean_text(profile.get("horarios")) or "07h, 12h, 16h e 20h"
    preferencias = _clean_text(profile.get("preferencias")) or "preparações simples e práticas"
    idade = _camila_existing_value(profile, p_obj, anamnese, "idade_informada") or "-"
    sexo = _camila_existing_value(profile, p_obj, anamnese, "sexo_informado") or "-"
    deficiencia = _camila_existing_value(profile, p_obj, anamnese, "deficiencia_informada") or "sem deficiência ou condição especial registrada"
    restricoes = "; ".join(
        x for x in [
            _clean_text(anamnese.get("alergias")),
            _clean_text(anamnese.get("intolerancias")),
            _clean_text(anamnese.get("condicoes_saude")),
        ] if x
    ) or "sem restrições registradas"
    peso = ultimos.get("peso") or profile.get("peso_informado") or "-"
    altura = ultimos.get("altura") or profile.get("altura_informada") or "-"
    draft = f"""RASCUNHO INICIAL DE DIETA - CAMILA

Cliente: {p_obj.get('nome') or '-'}
Objetivo: {objetivo}
Idade: {idade}
Sexo: {sexo}
Peso de referência: {peso}
Altura de referência: {altura}
Deficiência / condição especial: {deficiencia}
Horários sugeridos: {horarios}
Preferências: {preferencias}
Restrições e cuidados: {restricoes}

1. Café da manhã
- Fonte de proteína prática
- Fruta ou opção com fibras
- Bebida sem excesso de açúcar

2. Almoço
- Metade do prato com vegetais
- Proteína magra
- Carboidrato em porção ajustada ao objetivo

3. Lanche
- Opção simples e aderente à rotina
- Priorizar saciedade e praticidade

4. Jantar
- Refeição leve, com proteína e vegetais
- Ajustar carboidrato conforme fome, treino e rotina

Orientação da Camila:
- Este plano é inicial e ajustável.
- Respeitar alergias, intolerâncias e condições já informadas.
- Em caso de sintomas relevantes, doenças complexas ou piora clínica, o atendimento deve ser revisto por profissional humano."""
    return draft


def _camila_has_any(text: str, terms: list[str]) -> bool:
    low = normalize_text(text)
    return any(normalize_text(term) in low for term in terms if term)


def _camila_pick_protein(preferences: str, restrictions: str, version: int = 0) -> tuple[str, str]:
    pref = normalize_text(preferences)
    rest = normalize_text(restrictions)
    avoid_beef = any(t in pref or t in rest for t in ["nao como carne vermelha", "sem carne vermelha", "aversao a carne vermelha"])
    avoid_chicken = any(t in pref or t in rest for t in ["nao como frango", "sem frango", "aversao a frango"])
    vegetarian = any(t in pref or t in rest for t in ["vegetar", "vegano", "sem carne", "sem carnes"])
    if vegetarian:
        proteins = [
            ("tofu grelhado 120 g", "trocar por lentilha cozida 1 concha ou grão-de-bico 1 concha"),
            ("omelete com 2 ovos e legumes", "trocar por tofu mexido 120 g ou feijão + quinoa"),
            ("grão-de-bico cozido 1 concha", "trocar por lentilha 1 concha ou ervilha 1 concha"),
        ]
    else:
        proteins = [
            ("frango peito grelhado 120 g", "trocar por peixe tilápia 120 g ou bovino patinho 100 g"),
            ("peixe tilápia assado 120 g", "trocar por frango peito 120 g ou bovino coxão mole 100 g"),
            ("bovino patinho grelhado 100 g", "trocar por frango peito 120 g ou peixe tilápia 120 g"),
        ]
        if avoid_beef:
            proteins = [item for item in proteins if "bovino" not in item[0]]
        if avoid_chicken:
            proteins = [item for item in proteins if "frango" not in item[0]]
        if not proteins:
            proteins = [("peixe tilápia assado 120 g", "trocar por tofu grelhado 120 g ou ovos 2 unidades")]
    return proteins[version % len(proteins)]


def _camila_breakfast_options(restrictions: str, preferences: str, version: int = 0) -> tuple[str, str]:
    avoid_lactose = _camila_has_any(restrictions, ["lactose", "leite", "aplv"])
    avoid_gluten = _camila_has_any(restrictions, ["gluten", "trigo", "celiaca", "celíaca"])
    avoid_egg = _camila_has_any(restrictions + " " + preferences, ["ovo", "ovos"])
    options = []
    if not avoid_egg:
        options.append(
            ("2 ovos mexidos + 1 fatia de pão integral" if not avoid_gluten else "2 ovos mexidos + 2 colheres de tapioca",
             "trocar por mingau de aveia" if not avoid_gluten else "trocar por iogurte vegetal com fruta")
        )
    if avoid_lactose:
        options.append(
            ("iogurte vegetal sem açúcar 1 pote + banana prata 1 un + chia 1 colher", "trocar por vitamina com bebida vegetal + fruta")
        )
    else:
        options.append(
            ("iogurte natural 1 pote + aveia 2 colheres + mamão papaya 1 fatia", "trocar por kefir natural ou leite fermentado sem açúcar")
        )
    if avoid_gluten:
        options.append(
            ("tapioca 2 colheres com pasta de ricota sem lactose" if not avoid_lactose else "tapioca 2 colheres com pasta de grão-de-bico",
             "trocar por cuscuz de milho 1 porção")
        )
    return options[version % len(options)]


def _camila_build_logic_summary(p_obj: dict) -> str:
    profile = _camila_profile(p_obj)
    anamnese = get_anamnese_paciente(p_obj)
    objetivo = _camila_existing_value(profile, p_obj, anamnese, "objetivo") or "organizar a alimentação"
    idade = _camila_existing_value(profile, p_obj, anamnese, "idade_informada") or "idade não informada"
    sexo = _camila_existing_value(profile, p_obj, anamnese, "sexo_informado") or "sexo não informado"
    deficiencia = _camila_existing_value(profile, p_obj, anamnese, "deficiencia_informada") or "sem deficiência ou condição especial registrada"
    rotina = _camila_existing_value(profile, p_obj, anamnese, "rotina_trabalho") or "rotina não detalhada"
    atividade = _camila_existing_value(profile, p_obj, anamnese, "atividade_fisica") or "atividade física não detalhada"
    horarios = _camila_existing_value(profile, p_obj, anamnese, "horarios") or "horários ainda não definidos"
    preferencias = _camila_existing_value(profile, p_obj, anamnese, "preferencias") or "sem preferências marcantes"
    restricoes = " | ".join(
        x for x in [
            _camila_existing_value(profile, p_obj, anamnese, "alergias_confirmadas"),
            _camila_existing_value(profile, p_obj, anamnese, "intolerancias_confirmadas"),
            _camila_existing_value(profile, p_obj, anamnese, "doencas_informadas"),
            _camila_existing_value(profile, p_obj, anamnese, "deficiencia_informada"),
        ] if x
    ) or "sem restrições críticas registradas"
    knowledge_topics = _camila_knowledge_topics(p_obj)
    topics_text = ", ".join(topic.get("label") or "-" for topic in knowledge_topics) if knowledge_topics else "sem tópicos clínicos complementares relevantes"
    return (
        f"Plano estruturado com foco em {objetivo}, considerando idade {idade}, sexo {sexo}, condição especial/deficiência {deficiencia}, rotina {rotina}, nível de atividade {atividade}, "
        f"horários {horarios}, preferências {preferencias} e restrições {restricoes}. "
        f"A montagem prioriza constância, execução real e princípios gerais de alimentação saudável usados pela OMS. Base complementar reconhecida: {topics_text}."
    )


def _camila_generate_structured_diet(p_obj: dict, adjustment: str = "", version: int = 0) -> str:
    profile = _camila_profile(p_obj)
    anamnese = get_anamnese_paciente(p_obj)
    ultimos = get_ultimos_dados(p_obj)
    objetivo = _camila_existing_value(profile, p_obj, anamnese, "objetivo") or "organização alimentar"
    idade = _camila_existing_value(profile, p_obj, anamnese, "idade_informada") or "-"
    sexo = _camila_existing_value(profile, p_obj, anamnese, "sexo_informado") or "-"
    deficiencia = _camila_existing_value(profile, p_obj, anamnese, "deficiencia_informada") or "sem deficiência ou condição especial registrada"
    horarios = _camila_existing_value(profile, p_obj, anamnese, "horarios") or "07h | 10h | 13h | 16h | 19h | 21h"
    restricoes = " | ".join(
        x for x in [
            _camila_existing_value(profile, p_obj, anamnese, "alergias_confirmadas"),
            _camila_existing_value(profile, p_obj, anamnese, "intolerancias_confirmadas"),
            _camila_existing_value(profile, p_obj, anamnese, "doencas_informadas"),
            _camila_existing_value(profile, p_obj, anamnese, "deficiencia_informada"),
        ] if x
    )
    prefs = " | ".join(
        x for x in [
            _camila_existing_value(profile, p_obj, anamnese, "preferencias"),
            _camila_existing_value(profile, p_obj, anamnese, "aversoes"),
        ] if x
    )
    breakfast_main, breakfast_swap = _camila_breakfast_options(restricoes + " " + prefs, prefs, version)
    protein_main, protein_swap = _camila_pick_protein(prefs, restricoes, version)
    jantar_main, jantar_swap = _camila_pick_protein(prefs, restricoes, version + 1)
    snack_am = "fruta + castanhas 1 porção pequena" if not _camila_has_any(restricoes, ["castanha", "noz", "amendoim"]) else "fruta + semente de girassol 1 colher"
    snack_pm = "iogurte natural + fruta" if not _camila_has_any(restricoes, ["lactose", "leite", "aplv"]) else "iogurte vegetal + fruta"
    if _camila_has_any(restricoes, ["diabetes"]):
        snack_am = "fruta com fibra + fonte de proteína leve"
        snack_pm = "iogurte natural sem açúcar ou opção vegetal + chia"
    draft = f"""PLANO ALIMENTAR INICIAL - CAMILA

Cliente: {p_obj.get('nome') or '-'}
Objetivo: {objetivo}
Idade: {idade}
Sexo: {sexo}
Peso de referência: {ultimos.get('peso') or profile.get('peso_informado') or '-'}
Altura de referência: {ultimos.get('altura') or profile.get('altura_informada') or '-'}
Deficiência / condição especial: {deficiencia}
Horários de base: {horarios}
Restrições e cuidados: {restricoes or 'sem restrições relevantes registradas'}
Preferências e aversões consideradas: {prefs or 'sem observações adicionais'}
{f"Ajuste solicitado: {adjustment}" if adjustment else ""}

**Café da manhã**
- {breakfast_main}
- Quantidade: porção individual equilibrada para início do dia
- Observação prática: priorizar proteína + fibra para maior saciedade
- Substituição simples: {breakfast_swap}

**Lanche da manhã**
- {snack_am}
- Quantidade: 1 porção
- Observação prática: usar se houver intervalo maior entre refeições
- Substituição simples: trocar por fruta de fácil transporte

**Almoço**
- {protein_main}
- Arroz integral 3 a 4 colheres de sopa
- Feijão 1 concha pequena
- Salada variada 1 prato de sobremesa
- Observação prática: montar prato simples, com metade de vegetais
- Substituição simples: {protein_swap}

**Lanche da tarde**
- {snack_pm}
- Quantidade: 1 porção
- Observação prática: lanche leve para reduzir fome no fim do dia
- Substituição simples: trocar por sanduíche simples com proteína magra

**Jantar**
- {jantar_main}
- Legumes cozidos ou salteados 1 porção generosa
- Carboidrato ajustado à fome e à rotina: 2 a 3 colheres
- Observação prática: refeição mais leve e previsível para facilitar constância
- Substituição simples: {jantar_swap}

**Ceia**
- Se houver fome: fruta leve ou bebida proteica simples
- Quantidade: pequena
- Observação prática: usar apenas se realmente necessário
- Substituição simples: chá sem açúcar + alimento leve

Resumo da estratégia:
Montei um plano inicial com foco na sua rotina, no seu objetivo e nas suas preferências. A ideia é começar de forma prática e sustentável.
"""
    return _bold_meal_titles(_beautify_generated_text(draft))


def _camila_generate_virtual_diet(p_obj: dict, regenerate: bool = False, adjustment: str = "") -> dict:
    profile = _camila_profile(p_obj)
    anamnese = get_anamnese_paciente(p_obj)
    objective_text = _camila_existing_value(profile, p_obj, anamnese, "objetivo")
    restrictions_text = "\n".join(
        x for x in [
            _camila_existing_value(profile, p_obj, anamnese, "alergias_confirmadas"),
            _camila_existing_value(profile, p_obj, anamnese, "intolerancias_confirmadas"),
            _camila_existing_value(profile, p_obj, anamnese, "doencas_informadas"),
            _camila_existing_value(profile, p_obj, anamnese, "deficiencia_informada"),
            _camila_existing_value(profile, p_obj, anamnese, "aversoes"),
            _camila_existing_value(profile, p_obj, anamnese, "preferencias"),
        ] if x
    )
    notes_text = "\n".join(
        x for x in [
            _camila_existing_value(profile, p_obj, anamnese, "rotina_trabalho"),
            _camila_existing_value(profile, p_obj, anamnese, "atividade_fisica"),
            _camila_existing_value(profile, p_obj, anamnese, "sintomas"),
            _camila_existing_value(profile, p_obj, anamnese, "resumo_atendimento"),
            adjustment,
        ] if x
    )
    rules_payload = load_clinical_rules(CLINICAL_DIET_RULES_PATH) or {}
    clinical_rules = list(rules_payload.get("rules") or [])
    clinical_context = extract_patient_clinical_context(
        clinical_rules,
        anamnese=anamnese,
        restrictions_text=restrictions_text,
        notes_text=notes_text,
        objective_text=objective_text,
    )
    clinical_evaluation = evaluate_clinical_rules(clinical_rules, clinical_context)
    is_complex, alerts = _camila_triage_result(p_obj)
    version = int(profile.get("dieta_versao") or 0) + (1 if regenerate else 0)

    if is_complex:
        text = (
            "ORIENTAÇÃO INICIAL SIMPLIFICADA - CAMILA\n\n"
            "Este caso precisa de validação humana antes de uma dieta completa.\n"
            f"Pontos de atenção: {', '.join(alerts)}.\n\n"
            "Enquanto isso, a orientação inicial é:\n"
            "- manter regularidade das refeições;\n"
            "- priorizar hidratação;\n"
            "- evitar ultraprocessados em excesso;\n"
            "- observar sintomas e evolução;\n"
            "- aguardar revisão do nutricionista para ajuste individual.\n\n"
            "Essa conduta é conservadora e alinhada à segurança clínica e a princípios gerais de saúde da OMS."
        )
        validation = {"blocked_conflicts": [], "conditional_alerts": [], "preference_alerts": [], "audit_log": alerts, "needs_revision": False}
        logic = "Caso classificado como complexo. Dieta completa bloqueada e substituída por orientação inicial simplificada até validação humana."
    else:
        text = _camila_generate_structured_diet(p_obj, adjustment=adjustment, version=version)
        validation = validate_diet_text(text, clinical_evaluation) if clinical_evaluation.get("rules") else {"blocked_conflicts": [], "conditional_alerts": [], "preference_alerts": [], "audit_log": [], "needs_revision": False}
        logic = _camila_build_logic_summary(p_obj)
    summary = summarize_clinical_audit(clinical_evaluation, validation)
    return {
        "text": text,
        "logic": logic,
        "audit": {"evaluation": clinical_evaluation, "validation": validation, "summary": summary},
        "complex_case": is_complex,
        "alerts": alerts,
        "version": version,
    }


def _camila_generate_guidance(p_obj: dict) -> str:
    if not p_obj:
        return ""
    profile = _camila_profile(p_obj)
    objetivo = _clean_text(profile.get("objetivo")) or "consistência alimentar"
    topic_notes = []
    for topic in _camila_knowledge_topics(p_obj)[:4]:
        for point in list(topic.get("camila_guidance") or [])[:1]:
            topic_notes.append(f"- {point}")
    extra_block = "\n".join(dict.fromkeys(topic_notes))
    return f"""ORIENTAÇÕES INICIAIS DA CAMILA

- Foque em regularidade das refeições antes de buscar perfeição.
- Organize água, sono e horários para melhorar adesão.
- Planeje compras simples para facilitar a rotina.
- Faça trocas alimentares práticas, sem radicalismo.
- Objetivo atual em foco: {objetivo}.
- Se houver sintomas persistentes, alergias importantes ou condição clínica complexa, procure revisão com nutricionista humano.
{extra_block if extra_block else ""}"""


def _inject_camila_styles():
    st.markdown(
        """
        <style>
        .dh-camila-shell{display:grid;gap:18px;}
        .dh-camila-hero{display:grid;grid-template-columns:minmax(0,1.45fr) minmax(300px,.95fr);gap:18px;padding:26px;border-radius:26px;border:1px solid rgba(120,181,255,.14);background:
          radial-gradient(circle at top left, rgba(88,199,255,.14), transparent 34%),
          radial-gradient(circle at bottom right, rgba(35,211,138,.12), transparent 32%),
          linear-gradient(145deg, rgba(8,18,34,.98), rgba(11,25,48,.96));box-shadow:0 26px 52px rgba(0,0,0,.24);}
        .dh-camila-hero-compact{gap:14px;padding:18px 20px;border-radius:22px;}
        .dh-camila-kicker-row{display:flex;align-items:center;justify-content:space-between;gap:12px;flex-wrap:wrap;}
        .dh-camila-kicker{display:inline-flex;align-items:center;padding:6px 10px;border-radius:999px;background:rgba(34,197,94,.12);border:1px solid rgba(34,197,94,.24);color:#d7ffee;font-size:.72rem;font-weight:800;}
        .dh-camila-status{display:inline-flex;align-items:center;gap:8px;padding:6px 10px;border-radius:999px;background:rgba(15,23,42,.54);border:1px solid rgba(148,163,184,.18);color:#f2fff8;font-size:.74rem;font-weight:800;}
        .dh-camila-status span{width:9px;height:9px;border-radius:999px;background:#3ee57f;box-shadow:0 0 12px rgba(62,229,127,.85);}
        .dh-camila-hero-title-row{display:flex;align-items:center;gap:12px;margin-top:10px;}
        .dh-camila-avatar{width:50px;height:50px;border-radius:16px;display:flex;align-items:center;justify-content:center;background:linear-gradient(145deg, rgba(118,194,255,.34), rgba(44,115,189,.18));border:1px solid rgba(144,210,255,.24);color:#f8fbff;font-size:1.25rem;font-weight:900;box-shadow:0 10px 18px rgba(0,0,0,.16);}
        .dh-camila-hero h1{margin:8px 0 0;color:#f8fbff;font-size:1.75rem;font-weight:900;letter-spacing:-.03em;}
        .dh-camila-subtitle{margin-top:2px;color:#c4d7ea;line-height:1.5;max-width:680px;font-size:.93rem;}
        .dh-camila-chip-row{display:flex;flex-wrap:wrap;gap:8px;margin-top:14px;}
        .dh-camila-chip{display:inline-flex;align-items:center;padding:7px 10px;border-radius:999px;background:rgba(255,255,255,.06);border:1px solid rgba(148,163,184,.16);color:#eff8ff;font-weight:700;font-size:.74rem;}
        .dh-camila-hero-side{display:grid;gap:12px;}
        .dh-camila-hero-side-compact{grid-template-columns:repeat(3,minmax(0,1fr));align-content:start;}
        .dh-camila-summary-card{padding:12px 14px;border-radius:16px;border:1px solid rgba(148,163,184,.12);background:rgba(9,19,35,.84);}
        .dh-camila-summary-label{color:#92abc6;font-size:.76rem;text-transform:uppercase;letter-spacing:.06em;font-weight:800;margin-bottom:7px;}
        .dh-camila-summary-value{color:#f8fbff;font-size:1rem;font-weight:800;}
        .dh-camila-summary-text{color:#c4d7ea;line-height:1.55;}
        .dh-camila-minihead{display:flex;align-items:center;justify-content:space-between;gap:12px;margin-bottom:12px;padding:10px 12px;border-radius:16px;border:1px solid rgba(148,163,184,.12);background:rgba(8,16,30,.82);}
        .dh-camila-minihead-main{display:flex;align-items:center;gap:10px;}
        .dh-camila-mini-avatar{width:38px;height:38px;border-radius:12px;display:flex;align-items:center;justify-content:center;background:linear-gradient(145deg, rgba(118,194,255,.34), rgba(44,115,189,.18));border:1px solid rgba(144,210,255,.22);color:#f8fbff;font-size:1rem;font-weight:900;}
        .dh-camila-mini-kicker{color:#f8fbff;font-size:1rem;font-weight:850;line-height:1.1;}
        .dh-camila-mini-sub{color:#a9bfd6;font-size:.82rem;line-height:1.2;}
        .dh-camila-mini-badge{display:inline-flex;align-items:center;padding:6px 10px;border-radius:999px;border:1px solid rgba(34,197,94,.24);background:rgba(34,197,94,.10);color:#e7fff2;font-size:.74rem;font-weight:800;}
        .dh-camila-panel{padding:18px;border-radius:20px;border:1px solid rgba(148,163,184,.12);background:linear-gradient(180deg, rgba(10,20,37,.96), rgba(8,16,30,.94));box-shadow:0 18px 34px rgba(0,0,0,.18);}
        .dh-camila-panel h3{margin:0 0 8px;color:#f8fbff;font-size:1.05rem;font-weight:850;}
        .dh-camila-panel p{margin:0;color:#bed0e3;line-height:1.58;}
        .dh-camila-home-grid{display:grid;grid-template-columns:minmax(0,1.18fr) minmax(320px,.82fr);gap:18px;align-items:start;}
        .dh-camila-chat-card{display:grid;gap:14px;}
        .dh-camila-chat-header{display:flex;align-items:center;justify-content:space-between;gap:12px;flex-wrap:wrap;}
        .dh-camila-chat-title{display:grid;gap:6px;}
        .dh-camila-chat-title h3{margin:0;color:#f8fbff;font-size:1.08rem;font-weight:850;}
        .dh-camila-chat-title p{margin:0;color:#bcd0e3;line-height:1.55;}
        .dh-camila-chat-log{display:grid;gap:12px;max-height:540px;overflow:auto;padding:4px 6px 8px 0;}
        .dh-camila-msg{padding:14px 15px;border-radius:18px;line-height:1.6;border:1px solid rgba(148,163,184,.1);}
        .dh-camila-msg-user{background:rgba(59,130,246,.12);color:#e8f2ff;}
        .dh-camila-msg-ai{background:rgba(34,197,94,.10);color:#eafff2;}
        .dh-camila-side-grid{display:grid;gap:12px;}
        .dh-camila-actions{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:10px;}
        .dh-camila-measure-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px;}
        .dh-camila-data{padding:14px 15px;border-radius:16px;background:rgba(255,255,255,.04);border:1px solid rgba(148,163,184,.1);}
        .dh-camila-data strong{display:block;color:#f8fbff;margin-bottom:6px;}
        .dh-camila-data span{display:block;color:#bfd1e5;line-height:1.5;}
        .dh-camila-diet-actions{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:10px;}
        .dh-camila-guidance-list{display:grid;gap:10px;}
        .dh-camila-guidance-item{padding:12px 13px;border-radius:14px;background:rgba(255,255,255,.04);border:1px solid rgba(148,163,184,.1);color:#d6e3f2;line-height:1.5;}
        .dh-camila-lux-header{position:relative;overflow:hidden;padding:20px 22px;border-radius:24px;border:1px solid rgba(178,224,255,.16);background:
          radial-gradient(circle at top left, rgba(111,255,214,.16), transparent 28%),
          radial-gradient(circle at top right, rgba(255,214,102,.11), transparent 30%),
          linear-gradient(135deg, rgba(7,18,35,.98), rgba(12,26,48,.97));box-shadow:0 24px 50px rgba(0,0,0,.22), inset 0 1px 0 rgba(255,255,255,.04);}
        .dh-camila-lux-header:after{content:"";position:absolute;inset:0;background:linear-gradient(120deg, transparent 0%, rgba(255,255,255,.05) 48%, transparent 100%);pointer-events:none;}
        .dh-camila-lux-kicker{display:inline-flex;align-items:center;padding:7px 12px;border-radius:999px;background:rgba(255,214,102,.12);border:1px solid rgba(255,214,102,.26);color:#fff2c4;font-size:.72rem;font-weight:800;letter-spacing:.08em;text-transform:uppercase;}
        .dh-camila-lux-header h3{margin:14px 0 8px;color:#f8fbff;font-size:1.2rem;font-weight:900;letter-spacing:-.03em;}
        .dh-camila-lux-header p{margin:0;color:#d8e8f6;line-height:1.65;max-width:760px;}
        .dh-camila-lux-note{margin-top:14px;display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:12px;}
        .dh-camila-lux-note div{padding:12px 13px;border-radius:16px;background:rgba(255,255,255,.045);border:1px solid rgba(178,224,255,.12);color:#dcebf8;font-size:.88rem;line-height:1.45;box-shadow:inset 0 1px 0 rgba(255,255,255,.03);}
        .dh-camila-lux-note strong{display:block;color:#fef6d3;font-size:.76rem;letter-spacing:.07em;text-transform:uppercase;margin-bottom:5px;}
        div[class*="st-key-camila_intake_shell"] div[data-testid="stForm"]{padding:20px 20px 10px;border-radius:26px;border:1px solid rgba(178,224,255,.14);background:
          radial-gradient(circle at top left, rgba(102,217,255,.10), transparent 32%),
          linear-gradient(180deg, rgba(11,23,41,.96), rgba(7,16,31,.96));box-shadow:0 26px 48px rgba(0,0,0,.24), inset 0 1px 0 rgba(255,255,255,.04);}
        div[class*="st-key-camila_intake_shell"] div[data-testid="stForm"] form{display:grid;gap:10px;}
        div[class*="st-key-camila_intake_shell"] .stTextInput label,
        div[class*="st-key-camila_intake_shell"] .stTextArea label,
        div[class*="st-key-camila_intake_shell"] .stSelectbox label{color:#eef7ff !important;font-size:.82rem !important;font-weight:850 !important;letter-spacing:.025em;line-height:1.15 !important;margin-bottom:6px !important;}
        div[class*="st-key-camila_intake_shell"] .stTextInput > div,
        div[class*="st-key-camila_intake_shell"] .stTextArea > div,
        div[class*="st-key-camila_intake_shell"] .stSelectbox > div{margin-top:0;}
        div[class*="st-key-camila_intake_shell"] .stTextInput,
        div[class*="st-key-camila_intake_shell"] .stTextArea,
        div[class*="st-key-camila_intake_shell"] .stSelectbox{padding:10px 12px 12px;border-radius:20px;background:linear-gradient(180deg, rgba(255,255,255,.035), rgba(255,255,255,.018));border:1px solid rgba(182,224,248,.08);box-shadow:inset 0 1px 0 rgba(255,255,255,.025);}
        div[class*="st-key-camila_intake_shell"] .stTextInput input,
        div[class*="st-key-camila_intake_shell"] .stNumberInput input,
        div[class*="st-key-camila_intake_shell"] .stTextArea textarea,
        div[class*="st-key-camila_intake_shell"] .stSelectbox [data-baseweb="select"] > div{
          min-height:54px !important;background:linear-gradient(180deg, rgba(251,253,255,.985), rgba(238,246,252,.985)) !important;
          color:#07111f !important;-webkit-text-fill-color:#07111f !important;border:1px solid rgba(152,205,235,.58) !important;border-radius:16px !important;
          box-shadow:0 10px 20px rgba(0,0,0,.10), inset 0 1px 0 rgba(255,255,255,.84) !important;transition:all .18s ease !important;padding-left:14px !important;padding-right:14px !important;}
        div[class*="st-key-camila_intake_shell"] .stTextInput input,
        div[class*="st-key-camila_intake_shell"] .stNumberInput input{height:54px !important;line-height:54px !important;}
        div[class*="st-key-camila_intake_shell"] .stTextArea textarea{min-height:126px !important;padding-top:14px !important;line-height:1.55 !important;}
        div[class*="st-key-camila_intake_shell"] .stSelectbox [data-baseweb="select"] > div{padding-top:0 !important;padding-bottom:0 !important;display:flex !important;align-items:center !important;}
        div[class*="st-key-camila_intake_shell"] .stSelectbox [data-baseweb="select"] > div > div{display:flex !important;align-items:center !important;min-height:54px !important;}
        div[class*="st-key-camila_intake_shell"] .stSelectbox [data-baseweb="select"] input{color:#07111f !important;-webkit-text-fill-color:#07111f !important;}
        div[class*="st-key-camila_intake_shell"] .stSelectbox svg{color:#28445d !important;}
        div[class*="st-key-camila_intake_shell"] .stTextInput input::placeholder,
        div[class*="st-key-camila_intake_shell"] .stNumberInput input::placeholder,
        div[class*="st-key-camila_intake_shell"] .stTextArea textarea::placeholder{color:#6b7d90 !important;-webkit-text-fill-color:#6b7d90 !important;}
        div[class*="st-key-camila_intake_shell"] .stTextInput input:focus,
        div[class*="st-key-camila_intake_shell"] .stNumberInput input:focus,
        div[class*="st-key-camila_intake_shell"] .stTextArea textarea:focus,
        div[class*="st-key-camila_intake_shell"] .stSelectbox [data-baseweb="select"] > div:focus-within{
          border-color:rgba(74,222,128,.62) !important;box-shadow:0 0 0 1px rgba(74,222,128,.22), 0 16px 30px rgba(0,0,0,.14), inset 0 1px 0 rgba(255,255,255,.88) !important;transform:translateY(-1px);}
        div[class*="st-key-camila_intake_shell"] [data-testid="stFormSubmitButton"] > button{
          min-height:54px;border:none !important;border-radius:18px !important;background:
          linear-gradient(135deg, #7cf0c4 0%, #44d0a4 38%, #c9a34f 100%) !important;
          color:#041018 !important;font-size:1rem !important;font-weight:900 !important;letter-spacing:.02em !important;
          box-shadow:0 18px 32px rgba(24,60,54,.28), inset 0 1px 0 rgba(255,255,255,.36) !important;transition:transform .18s ease, box-shadow .18s ease, filter .18s ease !important;}
        div[class*="st-key-camila_intake_shell"] [data-testid="stFormSubmitButton"] > button:hover{
          transform:translateY(-2px);filter:saturate(1.04) brightness(1.02);box-shadow:0 24px 38px rgba(20,61,52,.34), inset 0 1px 0 rgba(255,255,255,.42) !important;}
        div[class*="st-key-camila_intake_shell"] [data-testid="stFormSubmitButton"] > button:active{transform:translateY(0);}
        div[class*="st-key-camila_intake_shell"] [data-testid="column"]{align-self:start;}
        .dh-camila-mobile-summary{display:none;}
        body.dh-camila-active .stTextInput label,body.dh-camila-active .stTextArea label{color:#d9e7f5 !important;}
        body.dh-camila-active .stTextArea [data-baseweb="base-input"],
        body.dh-camila-active .stTextArea [data-baseweb="textarea"],
        body.dh-camila-active div[data-baseweb="textarea"],
        body.dh-camila-active div[data-baseweb="input"] > div{
          background:#f8fafc !important;
          border:1px solid rgba(120,181,255,.22) !important;
          border-radius:14px !important;
          box-shadow:none !important;
        }
        body.dh-camila-active .stTextInput input,
        body.dh-camila-active .stNumberInput input,
        body.dh-camila-active .stTextArea textarea,
        body.dh-camila-active [data-testid="stTextArea"] textarea,
        body.dh-camila-active div[data-baseweb="textarea"] textarea,
        body.dh-camila-active [data-testid="stChatInput"] textarea,
        body.dh-camila-active [data-testid="stChatInput"] input{
          background:#f8fafc !important;
          color:#0f172a !important;
          -webkit-text-fill-color:#0f172a !important;
          caret-color:#0f172a !important;
          border:1px solid rgba(120,181,255,.22) !important;
          box-shadow:none !important;
          opacity:1 !important;
        }
        body.dh-camila-active .stTextInput input:disabled,
        body.dh-camila-active .stNumberInput input:disabled,
        body.dh-camila-active .stTextArea textarea:disabled,
        body.dh-camila-active [data-testid="stTextArea"] textarea:disabled,
        body.dh-camila-active div[data-baseweb="textarea"] textarea:disabled,
        body.dh-camila-active [data-testid="stChatInput"] textarea:disabled,
        body.dh-camila-active [data-testid="stChatInput"] input:disabled{
          background:#f8fafc !important;
          color:#0f172a !important;
          -webkit-text-fill-color:#0f172a !important;
          opacity:1 !important;
          border:1px solid rgba(120,181,255,.22) !important;
        }
        body.dh-camila-active .stTextInput input::placeholder,
        body.dh-camila-active .stNumberInput input::placeholder,
        body.dh-camila-active .stTextArea textarea::placeholder,
        body.dh-camila-active [data-testid="stTextArea"] textarea::placeholder,
        body.dh-camila-active div[data-baseweb="textarea"] textarea::placeholder,
        body.dh-camila-active [data-testid="stChatInput"] textarea::placeholder,
        body.dh-camila-active [data-testid="stChatInput"] input::placeholder{
          color:#64748b !important;
          -webkit-text-fill-color:#64748b !important;
          opacity:1 !important;
        }
        body.dh-camila-active .stTextInput input:focus,
        body.dh-camila-active .stNumberInput input:focus,
        body.dh-camila-active .stTextArea textarea:focus,
        body.dh-camila-active [data-testid="stChatInput"] textarea:focus,
        body.dh-camila-active [data-testid="stChatInput"] input:focus{
          border-color:rgba(113,241,184,.42) !important;
          box-shadow:0 0 0 1px rgba(113,241,184,.18) !important;
        }
        body.dh-camila-active [data-testid="stChatInput"]{
          background:rgba(8,16,30,.92) !important;
          border:1px solid rgba(113,241,184,.24) !important;
          border-radius:14px !important;
          padding:6px 8px !important;
        }
        [data-testid="stSuccess"]{
          background:linear-gradient(180deg, rgba(6,78,59,.88), rgba(5,46,34,.94)) !important;
          border:1px solid rgba(52,211,153,.42) !important;
          border-radius:16px !important;
          color:#eafff4 !important;
        }
        [data-testid="stSuccess"] *{
          color:#eafff4 !important;
        }
        @media (max-width: 980px){
          .dh-camila-hero,.dh-camila-home-grid{grid-template-columns:1fr;}
          .dh-camila-hero-side-compact{grid-template-columns:1fr;}
          .dh-camila-actions{grid-template-columns:repeat(2,minmax(0,1fr));}
          .dh-camila-lux-note{grid-template-columns:1fr;}
          .dh-camila-mobile-summary{display:block;}
        }
        @media (max-width: 720px){
          .dh-camila-actions,.dh-camila-measure-grid,.dh-camila-diet-actions{grid-template-columns:1fr;}
          .dh-camila-hero{padding:16px 14px;}
          .dh-camila-hero-title-row{align-items:flex-start;}
          .dh-camila-minihead{padding:9px 10px;}
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
    components.html(
        """
        <script>
        (function () {
          const rootDoc = window.parent && window.parent.document ? window.parent.document : document;
          if (!rootDoc || !rootDoc.body) return;
          rootDoc.body.classList.add('dh-camila-active');
        })();
        </script>
        """,
        height=0,
        width=0,
    )


def modulo_camila_home():
    _inject_camila_styles()
    _, p_obj, _ = _camila_patient_context()
    if not p_obj:
        st.warning("Nenhum usuário disponível para o Atendimento Virtual.")
        return
    _camila_intro_messages(p_obj)
    _camila_header(p_obj)
    profile = _camila_profile(p_obj)
    anamnese = get_anamnese_paciente(p_obj)
    ultimos = get_ultimos_dados(p_obj)
    chat_messages = _camila_chat_messages(p_obj)
    objetivo = profile.get("objetivo") or anamnese.get("queixa_principal") or "Ainda não informado"
    peso = ultimos.get("peso") or profile.get("peso_informado") or "Sem registro"
    altura = ultimos.get("altura") or profile.get("altura_informada") or "Sem registro"
    imc_txt = f"{float(ultimos.get('imc')):.2f}" if ultimos.get("imc") not in (None, "") else "Sem cálculo"
    idade = _camila_existing_value(profile, p_obj, anamnese, "idade_informada") or "Não informada"
    sexo = _camila_existing_value(profile, p_obj, anamnese, "sexo_informado") or (p_obj.get("sexo") or ultimos.get("sexo") or "Não informado")
    deficiencia = _camila_existing_value(profile, p_obj, anamnese, "deficiencia_informada") or "Sem deficiência ou condição especial registrada"
    restricoes = " | ".join(
        x for x in [
            _clean_text(anamnese.get("condicoes_saude")),
            _clean_text(anamnese.get("intolerancias")),
            _clean_text(profile.get("alergias_confirmadas")),
            _clean_text(profile.get("intolerancias_confirmadas")),
            _clean_text(profile.get("deficiencia_informada")),
        ] if x
    ) or "Sem restrições registradas"
    alergias = _clean_text(anamnese.get("alergias")) or "Sem alergias registradas"
    dieta_atual = profile.get("dieta_rascunho") or _camila_generate_draft(p_obj)
    dieta_resumo = "\n".join((dieta_atual or "").splitlines()[:6]).strip() or "Nenhum rascunho gerado ainda."
    orientacoes = profile.get("orientacoes_custom") or _camila_generate_guidance(p_obj)
    orientacoes_lista = [line.strip("- ").strip() for line in orientacoes.splitlines() if line.strip().startswith("-")][:4]

    left, right = st.columns([1.24, 0.86], gap="large")
    with left:
        st.markdown(
            """
            <div class="dh-camila-panel dh-camila-chat-card">
              <div class="dh-camila-chat-header">
                <div class="dh-camila-chat-title">
                  <h3>Atendimento com a Camila</h3>
                  <p>Conversa central do atendimento virtual, com acolhimento, triagem básica e orientação progressiva.</p>
                </div>
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        log_html = []
        for msg in chat_messages[-10:]:
            klass = "dh-camila-msg-user" if msg.get("role") == "user" else "dh-camila-msg-ai"
            log_html.append(f'<div class="dh-camila-msg {klass}">{html.escape(msg.get("content") or "")}</div>')
        st.markdown(f'<div class="dh-camila-chat-log">{"".join(log_html)}</div>', unsafe_allow_html=True)

        st.markdown("### Ações essenciais")
        action_cols = st.columns(3)
        if action_cols[0].button("Atendimento", use_container_width=True, type="primary"):
            st.session_state[VIRTUAL_MENU_SESSION_KEY] = "camila_atendimento"
            st.rerun()
        if action_cols[1].button("Minha Dieta", use_container_width=True):
            st.session_state[VIRTUAL_MENU_SESSION_KEY] = "camila_dieta"
            st.rerun()
        if action_cols[2].button("Orientações", use_container_width=True):
            st.session_state[VIRTUAL_MENU_SESSION_KEY] = "camila_orientacoes"
            st.rerun()

        st.markdown('<div class="dh-camila-panel"><h3>Resumo atual</h3><p>Somente o essencial para conduzir seu atendimento e montar o plano inicial.</p></div>', unsafe_allow_html=True)
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Peso", str(peso))
        m2.metric("Altura", str(altura))
        m3.metric("IMC", imc_txt)
        m4.metric("Última atualização", str(profile.get("ultima_atualizacao") or ultimos.get("data") or "-"))

        st.markdown(f'<div class="dh-camila-panel"><h3>Objetivo principal</h3><p>{html.escape(str(objetivo))}</p></div>', unsafe_allow_html=True)

        st.markdown('<div class="dh-camila-panel"><h3>Dieta inicial</h3><p>Plano inicial prático, feito só para você, com base no seu cadastro e nas informações do atendimento virtual.</p></div>', unsafe_allow_html=True)
        d1, d2 = st.columns(2)
        if d1.button("Gerar dieta", key="camila_home_generate_draft", use_container_width=True, type="primary"):
            result = _camila_generate_virtual_diet(p_obj)
            _camila_save_profile(
                p_obj,
                {
                    "dieta_rascunho": result.get("text") or "",
                    "dieta_logica_resumo": result.get("logic") or "",
                    "dieta_versao": result.get("version") or 1,
                    "dieta_ultima_geracao": datetime.now().strftime("%d/%m/%Y %H:%M"),
                },
            )
            st.success("Rascunho inicial atualizado.")
            st.rerun()
        if d2.button("Ver dieta atual", key="camila_home_open_draft", use_container_width=True):
            st.session_state[VIRTUAL_MENU_SESSION_KEY] = "camila_dieta"
            st.rerun()
        st.text_area("Resumo da dieta", value=dieta_resumo, height=170, disabled=True, key="camila_home_diet_resume")

    with right:
        with st.container():
            st.markdown("### Seu resumo")
            resumo_items = [
                ("Nome", p_obj.get("nome") or "Não informado"),
                ("Idade", idade),
                ("Sexo", sexo),
                ("Peso", peso),
                ("Altura", altura),
                ("Deficiência", deficiencia),
                ("IMC", imc_txt),
                ("Objetivo", objetivo),
                ("Restrições", restricoes),
                ("Alergias", alergias),
                ("Status", "Atendimento pessoal ativo"),
            ]
            cards = "".join(f'<div class="dh-camila-data"><strong>{html.escape(label)}</strong><span>{html.escape(str(value))}</span></div>' for label, value in resumo_items)
            st.markdown(f'<div class="dh-camila-side-grid">{cards}</div>', unsafe_allow_html=True)

        st.markdown('<div class="dh-camila-panel"><h3>Orientações iniciais</h3><p>Recomendações curtas para ajudar no começo do atendimento e na adesão à rotina.</p></div>', unsafe_allow_html=True)
        orient_html = "".join(f'<div class="dh-camila-guidance-item">{html.escape(item)}</div>' for item in orientacoes_lista)
        st.markdown(f'<div class="dh-camila-guidance-list">{orient_html}</div>', unsafe_allow_html=True)

    user_text = st.chat_input("Digite sua resposta...")
    if user_text:
        _camila_append_message(p_obj, "user", user_text)
        resposta = _camila_process_conversation(p_obj, user_text)
        _camila_append_message(p_obj, "assistant", resposta)
        st.rerun()


def modulo_camila_atendimento():
    _inject_camila_styles()
    _, p_obj, _ = _camila_patient_context()
    if not p_obj:
        st.warning("Nenhum usuário disponível para o Atendimento Virtual.")
        return
    _camila_header(p_obj, compact=True)
    profile = _camila_profile(p_obj)
    anamnese = get_anamnese_paciente(p_obj)
    with st.container(key="camila_intake_shell"):
        st.markdown(
            '''
            <div class="dh-camila-lux-header">
              <span class="dh-camila-lux-kicker">Atendimento premium</span>
              <h3>Atendimento inicial</h3>
              <p>Organize os dados essenciais do paciente com uma ficha mais elegante, clara e preparada para alimentar automaticamente a experiência da Camila e a geração do plano alimentar.</p>
              <div class="dh-camila-lux-note">
                <div><strong>Cadastro essencial</strong>Idade, sexo, peso, altura e deficiência entram direto no contexto do atendimento virtual.</div>
                <div><strong>Integração automática</strong>Ao salvar, a Camila reaproveita essas informações no resumo e na dieta sem retrabalho.</div>
                <div><strong>Visual premium</strong>Campos mais sofisticados, leitura mais limpa e apresentação mais profissional no painel.</div>
              </div>
            </div>
            ''',
            unsafe_allow_html=True,
        )
        with st.form("camila_intake_form"):
            dados1, dados2, dados3, dados4, dados5 = st.columns(5)
            idade_inf = dados1.text_input("Idade", value=_camila_existing_value(profile, p_obj, anamnese, "idade_informada"))
            sexo_opcoes = ["", "Masculino", "Feminino", "Outro"]
            sexo_atual = _camila_existing_value(profile, p_obj, anamnese, "sexo_informado")
            sexo_index = sexo_opcoes.index(sexo_atual) if sexo_atual in sexo_opcoes else 0
            sexo_inf = dados2.selectbox("Sexo", sexo_opcoes, index=sexo_index)
            peso_inf = dados3.text_input("Peso", value=_camila_existing_value(profile, p_obj, anamnese, "peso_informado"))
            altura_inf = dados4.text_input("Altura", value=_camila_existing_value(profile, p_obj, anamnese, "altura_informada"))
            deficiencia_inf = dados5.text_input("Deficiência", value=_camila_existing_value(profile, p_obj, anamnese, "deficiencia_informada"))
            c1, c2 = st.columns(2)
            objetivo = c1.text_area("Objetivo do cliente", value=profile.get("objetivo") or anamnese.get("queixa_principal") or "", height=110)
            rotina = c2.text_area("Rotina de trabalho/estudo", value=profile.get("rotina_trabalho") or profile.get("rotina_alimentar") or "", height=110)
            horarios = st.text_input("Horários e rotina do dia", value=profile.get("horarios") or "")
            c3, c4, c5 = st.columns(3)
            agua = c3.text_input("Água por dia", value=profile.get("agua_litros") or "")
            sono = c4.text_input("Sono por noite", value=profile.get("sono_horas") or "")
            atividade = c5.text_input("Atividade física", value=profile.get("atividade_fisica") or "")
            preferencias = st.text_area("Preferências alimentares", value=profile.get("preferencias") or "", height=90)
            aversoes = st.text_area("Aversões alimentares", value=profile.get("aversoes") or "", height=90)
            sintomas = st.text_area("Sintomas ou observações básicas", value=profile.get("sintomas") or "", height=90)
            resumo = st.text_area("Resumo do atendimento", value=profile.get("resumo_atendimento") or "", height=120)
            if st.form_submit_button("Salvar atendimento inicial", use_container_width=True):
                _camila_save_profile(
                    p_obj,
                    {
                        "idade_informada": idade_inf,
                        "sexo_informado": sexo_inf,
                        "peso_informado": peso_inf,
                        "altura_informada": altura_inf,
                        "deficiencia_informada": deficiencia_inf,
                        "objetivo": objetivo,
                        "rotina_trabalho": rotina,
                        "rotina_alimentar": rotina,
                        "horarios": horarios,
                        "agua_litros": agua,
                        "sono_horas": sono,
                        "atividade_fisica": atividade,
                        "preferencias": preferencias,
                        "aversoes": aversoes,
                        "sintomas": sintomas,
                        "resumo_atendimento": resumo,
                    },
                )
                st.success("Atendimento inicial salvo com sucesso.")
                st.rerun()


def modulo_camila_dados():
    _inject_camila_styles()
    _, p_obj, role = _camila_patient_context()
    if not p_obj:
        st.warning("Nenhum usuário disponível para o Atendimento Virtual.")
        return
    _camila_header(p_obj, compact=True)
    ultimos = get_ultimos_dados(p_obj)
    profile = _camila_profile(p_obj)
    dados = {
        "Nome": p_obj.get("nome"),
        "CPF": p_obj.get("cpf") or "Não informado",
        "Email": p_obj.get("email") or "Não informado",
        "WhatsApp": p_obj.get("telefone") or "Não informado",
        "Cidade": p_obj.get("cidade") or "Não informada",
        "Sexo": _camila_existing_value(profile, p_obj, {}, "sexo_informado") or "Não informado",
        "Idade": _camila_existing_value(profile, p_obj, {}, "idade_informada") or "Não informada",
        "Peso": _camila_existing_value(profile, p_obj, {}, "peso_informado") or "Não informado",
        "Altura": _camila_existing_value(profile, p_obj, {}, "altura_informada") or "Não informada",
        "Deficiência": _camila_existing_value(profile, p_obj, {}, "deficiencia_informada") or "Não informada",
        "Objetivo": profile.get("objetivo") or "Ainda não informado",
    }
    cards = "".join(f'<div class="dh-camila-data"><strong>{html.escape(k)}</strong><span>{html.escape(str(v))}</span></div>' for k, v in dados.items())
    st.markdown(f'<div class="dh-camila-side-grid">{cards}</div>', unsafe_allow_html=True)
    if role != "patient":
        st.caption("Os dados acima vêm do próprio cadastro do usuário usado no Atendimento Virtual.")


def modulo_camila_medidas():
    _inject_camila_styles()
    _, p_obj, _ = _camila_patient_context()
    if not p_obj:
        st.warning("Nenhum usuário disponível para o Atendimento Virtual.")
        return
    _camila_header(p_obj, compact=True)
    profile = _camila_profile(p_obj)
    ultimos = get_ultimos_dados(p_obj)
    st.markdown('<div class="dh-camila-panel"><h3>Medidas básicas</h3><p>Consome as medidas existentes do sistema e organiza um acompanhamento simples para o atendimento virtual.</p></div>', unsafe_allow_html=True)
    c1, c2, c3 = st.columns(3)
    c1.metric("Peso do sistema", str(ultimos.get("peso") or "-"))
    c2.metric("Altura do sistema", str(ultimos.get("altura") or "-"))
    c3.metric("IMC do sistema", f"{float(ultimos.get('imc')):.2f}" if ultimos.get("imc") not in (None, "") else "-")
    with st.form("camila_medidas_form"):
        m1, m2 = st.columns(2)
        peso_inf = m1.text_input("Peso informado no atendimento virtual", value=profile.get("peso_informado") or "")
        altura_inf = m2.text_input("Altura informada no atendimento virtual", value=profile.get("altura_informada") or "")
        comentario = st.text_area("Comentário de progresso", value=profile.get("comentario_evolucao") or "", height=100)
        if st.form_submit_button("Salvar medidas virtuais", use_container_width=True):
            _camila_save_profile(p_obj, {"peso_informado": peso_inf, "altura_informada": altura_inf, "comentario_evolucao": comentario})
            st.success("Medidas virtuais atualizadas.")
            st.rerun()


def modulo_camila_dieta():
    _inject_camila_styles()
    _, p_obj, _ = _camila_patient_context()
    if not p_obj:
        st.warning("Nenhum usuário disponível para o Atendimento Virtual.")
        return
    _camila_header(p_obj, compact=True)
    profile = _camila_profile(p_obj)
    phone = (p_obj.get("telefone") or "").strip()
    diet_text = profile.get("dieta_rascunho") or ""
    logic_text = profile.get("dieta_logica_resumo") or ""
    last_generated = profile.get("dieta_ultima_geracao") or ""
    version = int(profile.get("dieta_versao") or 0)
    adjustment_key = f"camila_diet_adjust_{p_obj.get('id') or p_obj.get('nome') or 'paciente'}"
    copy_payload = json.dumps(diet_text or "", ensure_ascii=False)

    st.markdown(
        '<div class="dh-camila-panel"><h3>Plano alimentar inicial</h3><p>Proposta prática, segura e ajustável dentro da experiência da Camila, respeitando dados do cadastro, restrições, alergias, intolerâncias e condições registradas.</p></div>',
        unsafe_allow_html=True,
    )

    a1, a2, a3 = st.columns(3)
    if a1.button("Gerar dieta", use_container_width=True, type="primary"):
        result = _camila_generate_virtual_diet(p_obj)
        _camila_save_profile(
            p_obj,
            {
                "dieta_rascunho": result.get("text") or "",
                "dieta_logica_resumo": result.get("logic") or "",
                "dieta_versao": result.get("version") or max(version, 1),
                "dieta_ultima_geracao": datetime.now().strftime("%d/%m/%Y %H:%M"),
            },
        )
        st.success("Plano inicial gerado com a Camila.")
        st.rerun()
    if a2.button("Gerar nova versão", use_container_width=True, disabled=not diet_text):
        result = _camila_generate_virtual_diet(p_obj, regenerate=True)
        _camila_save_profile(
            p_obj,
            {
                "dieta_rascunho": result.get("text") or "",
                "dieta_logica_resumo": result.get("logic") or "",
                "dieta_versao": result.get("version") or (version + 1),
                "dieta_ultima_geracao": datetime.now().strftime("%d/%m/%Y %H:%M"),
            },
        )
        st.success("Nova versão da dieta gerada.")
        st.rerun()
    if a3.button("Copiar dieta", use_container_width=True, disabled=not diet_text):
        components.html(
            f"""
            <script>
            navigator.clipboard.writeText({copy_payload});
            </script>
            <div style="font-family:Segoe UI, sans-serif;color:#d7ffee;font-size:14px;">Dieta copiada para a área de transferência.</div>
            """,
            height=28,
        )

    st.session_state.setdefault(adjustment_key, profile.get("dieta_ajuste_pedido") or "")
    adjustment = st.text_area(
        "Ajuste solicitado para a Camila",
        key=adjustment_key,
        height=96,
        placeholder="Ex: retirar leite, deixar jantar mais prático, adaptar para rotina de trabalho externa.",
    )

    b1, b2, b3 = st.columns([1.15, 1.15, 1.2])
    if b1.button("Ajustar dieta", use_container_width=True, disabled=not adjustment.strip()):
        result = _camila_generate_virtual_diet(p_obj, regenerate=True, adjustment=adjustment.strip())
        _camila_save_profile(
            p_obj,
            {
                "dieta_rascunho": result.get("text") or "",
                "dieta_logica_resumo": result.get("logic") or "",
                "dieta_ajuste_pedido": adjustment.strip(),
                "dieta_versao": result.get("version") or (version + 1),
                "dieta_ultima_geracao": datetime.now().strftime("%d/%m/%Y %H:%M"),
            },
        )
        st.success("Dieta ajustada com base no pedido informado.")
        st.rerun()
    if b2.button("Ver resumo da lógica", use_container_width=True, disabled=not (diet_text or logic_text)):
        st.session_state["camila_show_diet_logic"] = not st.session_state.get("camila_show_diet_logic", False)
    pdf_payload = gerar_pdf_pro(
        p_obj.get("nome") or "paciente",
        diet_text or "Plano alimentar ainda não gerado.",
        "PLANO ALIMENTAR INICIAL - CAMILA",
        "Camila",
        "Assistente Virtual",
    )
    b3.download_button(
        "Baixar PDF",
        data=pdf_payload,
        file_name=f"plano_camila_{(p_obj.get('nome') or 'paciente').replace(' ', '_').lower()}.pdf",
        mime="application/pdf",
        use_container_width=True,
        disabled=not diet_text,
    )

    if st.session_state.get("camila_show_diet_logic") and (diet_text or logic_text):
        st.markdown(
            f'<div class="dh-camila-panel"><h3>Resumo da lógica da dieta</h3><p>{html.escape(logic_text or "A lógica será exibida após a primeira geração.")}</p></div>',
            unsafe_allow_html=True,
        )

    if last_generated or version:
        meta_parts = []
        if version:
            meta_parts.append(f"Versão {version}")
        if last_generated:
            meta_parts.append(f"Última geração: {last_generated}")
        st.caption(" • ".join(meta_parts))

    st.text_area(
        "Plano alimentar",
        value=diet_text or "A Camila ainda não gerou o plano alimentar inicial.",
        height=430,
        key="camila_dieta_text",
        disabled=True,
    )

    current_result = None
    if diet_text:
        current_result = _camila_generate_virtual_diet(p_obj, adjustment=profile.get("dieta_ajuste_pedido") or "")
    audit_summary = (((current_result or {}).get("audit") or {}).get("summary") or {}) if current_result else {}
    if current_result and current_result.get("complex_case"):
        st.warning(
            "Caso classificado como complexo pela triagem da Camila. O sistema manteve apenas orientação inicial simplificada até revisão humana."
        )
    if audit_summary:
        matched = ", ".join(audit_summary.get("matched_conditions") or []) or "nenhuma condição adicional destacada"
        st.info(
            f"Validação clínica ativa: {matched}. "
            f"Bloqueios absolutos: {audit_summary.get('blocked_total', 0)}. "
            f"Alertas condicionais: {audit_summary.get('conditional_total', 0)}. "
            f"Conflitos de preferência: {audit_summary.get('preference_total', 0)}."
        )

    if diet_text:
        intro = "Montei um plano inicial com foco na sua rotina, no seu objetivo e nas suas preferências. A ideia é começar de forma prática e sustentável."
        st.markdown(
            f'<div class="dh-camila-panel"><h3>Explicação da Camila</h3><p>{html.escape(intro)}</p></div>',
            unsafe_allow_html=True,
        )

    wa_href = _wa_link(phone, f"Olá {p_obj.get('nome') or ''}, segue seu plano alimentar inicial montado pela Camila.\n\n{diet_text[:1200]}")
    send_disabled = not (diet_text and phone)
    c1, c2 = st.columns([1.2, 1])
    if send_disabled:
        c1.caption("Para enviar ao paciente, gere a dieta e confirme um WhatsApp válido no cadastro.")
    else:
        c1.markdown(f'<a class="dh-btn dh-btn-green" href="{wa_href}" target="_blank">Enviar dieta ao paciente</a>', unsafe_allow_html=True)
    c2.caption("O envio abre o WhatsApp com a mensagem pronta para revisão final.")


def modulo_camila_orientacoes():
    _inject_camila_styles()
    _, p_obj, _ = _camila_patient_context()
    if not p_obj:
        st.warning("Nenhum usuário disponível para o Atendimento Virtual.")
        return
    _camila_header(p_obj, compact=True)
    profile = _camila_profile(p_obj)
    guidance = profile.get("orientacoes_custom") or _camila_generate_guidance(p_obj)
    st.text_area("Orientações da Camila", value=guidance, height=320, key="camila_guidance_text")
    if st.button("Salvar orientações atuais", use_container_width=True):
        _camila_save_profile(p_obj, {"orientacoes_custom": guidance})
        st.success("Orientações registradas.")


def modulo_camila_evolucao():
    _inject_camila_styles()
    _, p_obj, _ = _camila_patient_context()
    if not p_obj:
        st.warning("Nenhum usuário disponível para o Atendimento Virtual.")
        return
    _camila_header(p_obj, compact=True)
    pontos = _camila_latest_weight_points(p_obj)
    if not pontos:
        st.info("Ainda não há medidas suficientes para exibir evolução.")
        return
    df = pd.DataFrame(pontos)
    fig = px.line(df, x="Data", y="Peso", color="Origem", markers=True, title="Evolução de peso no atendimento virtual")
    fig.update_layout(
        height=360,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        legend_title_text="",
        margin=dict(l=10, r=10, t=52, b=10),
        font=dict(color="#dbeafe"),
    )
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
    comentario = _camila_profile(p_obj).get("comentario_evolucao") or "Sem comentário adicional registrado."
    st.markdown(f'<div class="dh-camila-panel"><h3>Comentário resumido</h3><p>{html.escape(comentario)}</p></div>', unsafe_allow_html=True)


def modulo_camila_chat():
    _inject_camila_styles()
    _, p_obj, _ = _camila_patient_context()
    if not p_obj:
        st.warning("Nenhum usuário disponível para o Atendimento Virtual.")
        return
    _camila_intro_messages(p_obj)
    _camila_header(p_obj, compact=True)
    chat_messages = _camila_chat_messages(p_obj)
    for msg in chat_messages:
        with st.chat_message("assistant" if msg.get("role") == "assistant" else "user"):
            st.write(msg.get("content") or "")
    user_text = st.chat_input("Fale com a Camila")
    if user_text:
        _camila_append_message(p_obj, "user", user_text)
        resposta = _camila_process_conversation(p_obj, user_text)
        _camila_append_message(p_obj, "assistant", resposta)
        st.rerun()


def _render_camila_sidebar(role: str) -> str:
    selected = (st.session_state.get(VIRTUAL_MENU_SESSION_KEY) or "camila_home").strip().lower()
    valid = {item["key"] for item in VIRTUAL_PANEL_MENU_ITEMS}
    if selected not in valid:
        selected = "camila_home"
    st.session_state[VIRTUAL_MENU_SESSION_KEY] = selected
    st.markdown('<div class="dh-menu-title">Camila</div>', unsafe_allow_html=True)
    for item in VIRTUAL_PANEL_MENU_ITEMS:
        btn_type = "primary" if item["key"] == selected else "secondary"
        if st.button(item["label"], key=f"dh_virtual_btn_{item['key']}", use_container_width=True, type=btn_type):
            st.session_state[VIRTUAL_MENU_SESSION_KEY] = item["key"]
            st.session_state["dh_close_sidebar_after_nav"] = True
            st.rerun()
    return selected

# =============================================================================
# 9. APP PRINCIPAL
# =============================================================================
def main():
    _inject_pwa_shell()
    if "logado" not in st.session_state:
        st.session_state["logado"] = False
    if "usuario" not in st.session_state:
        st.session_state["usuario"] = ""
    if "tipo" not in st.session_state:
        st.session_state["tipo"] = "user"
    if SIMPLE_MODE_SESSION_KEY not in st.session_state:
        st.session_state[SIMPLE_MODE_SESSION_KEY] = False
    if EXPERIENCE_SESSION_KEY not in st.session_state:
        st.session_state[EXPERIENCE_SESSION_KEY] = "traditional"
    if VIRTUAL_MENU_SESSION_KEY not in st.session_state:
        st.session_state[VIRTUAL_MENU_SESSION_KEY] = "camila_home"

    _try_restore_login_from_query()
    _handle_mp_return()
    _maybe_show_webhook_payment_notice()
    _maybe_auto_sync_premium()

    # Bloqueia acesso apenas se estiver pendente/bloqueado (free continua liberado)
    if st.session_state.get("logado"):
        u_norm = (st.session_state.get("usuario") or "").strip().lower()
        user = next((x for x in users if (x.get("usuario") or "").strip().lower() == u_norm), None)
        ok, reason, venc = _check_user_access(user)
        # Tenta liberar automaticamente via pagamento (Mercado Pago) quando houver token configurado.
        if not ok and reason in ("pending", "blocked"):
            try:
                if mp_try_auto_activate_user(user):
                    ok, reason, venc = _check_user_access(user)
            except Exception:
                pass
        if not ok:
            if reason == "not_found":
                _mark_user_offline(u_norm)
                _clear_persisted_login_query()
                st.session_state["logado"] = False
                st.session_state["usuario"] = ""
                st.session_state["tipo"] = "user"
                st.session_state["login_blocked_user"] = ""
                st.session_state["login_blocked_reason"] = ""
                st.session_state["login_blocked_venc"] = ""
                st.session_state["login_verified_user"] = ""
                st.session_state["login_verified_tipo"] = ""
                st.session_state["login_verified_at"] = 0.0
                st.error("Usuário não encontrado. Faça login novamente.")
                mostrar_landing_page()
                return

            _mark_user_offline(u_norm)
            _clear_persisted_login_query()
            st.session_state["logado"] = False
            st.session_state["login_blocked_user"] = u_norm
            st.session_state["login_blocked_reason"] = reason
            st.session_state["login_blocked_venc"] = str(venc) if venc else ""
            # Usuário já estava autenticado nesta sessão: permite auto-login após confirmar pagamento.
            st.session_state["login_verified_user"] = u_norm
            st.session_state["login_verified_tipo"] = (user.get("tipo") if user else st.session_state.get("tipo") or "user")
            st.session_state["login_verified_at"] = float(time.time())

            if reason == "pending":
                st.error("Cadastro pendente de pagamento/liberação.")
            elif reason == "blocked":
                st.error("Acesso bloqueado. Procure o admin para liberar.")
            else:
                st.error("Acesso negado. Faça login novamente.")

            mostrar_landing_page()
            return
        # Aviso de vencimento no topo do sistema
        if user and user.get("tipo") != "admin":
            paid_until = _parse_date_ymd(user.get("paid_until"))
            if paid_until:
                dias = (paid_until - datetime.now().date()).days
                if dias < 0:
                    st.warning(f"Assinatura vencida em {_fmt_date_br(paid_until)}.")
                elif dias <= 7:
                    st.warning(f"Sua assinatura vence em {_fmt_date_br(paid_until)}.")
                else:
                    st.info(f"Assinatura ativa até {_fmt_date_br(paid_until)}.")


    # CSS mínimo: garante visual moderno também após login
    st.markdown(
        """
        <style>
        section[data-testid="stSidebar"]{
          background: linear-gradient(180deg, rgba(6,10,25,0.96), rgba(6,10,25,0.93)) !important;
          border-right: 1px solid rgba(255,255,255,0.08) !important;
          min-width: 272px !important;
          max-width: 272px !important;
        }
        section[data-testid="stSidebar"] *{ color: #f7faff !important; }

        /* Default app background (inside system) */
        body, .stApp, section[data-testid="stAppViewContainer"]{
          background: radial-gradient(1200px 700px at 15% 20%, rgba(0,191,165,0.08), transparent 60%),
                      radial-gradient(1200px 700px at 75% 30%, rgba(41,98,255,0.10), transparent 60%),
                      linear-gradient(115deg, #0f172a, #0b1320) !important;
        }
        section[data-testid="stAppViewContainer"] .main .block-container{
          background: transparent !important;
        }

        :root{
          --dh-font-main: "Segoe UI", "Inter", "Helvetica Neue", Arial, sans-serif;
        }
        body, .stApp{
          font-family: var(--dh-font-main) !important;
        }

        .dh-doc-preview{
          margin: 12px 0 14px 0;
          border: 1px solid rgba(255,255,255,0.14);
          border-radius: 16px;
          overflow: hidden;
          background: linear-gradient(180deg, rgba(255,255,255,0.10), rgba(255,255,255,0.04));
          box-shadow: 0 18px 34px rgba(0,0,0,0.28);
          backdrop-filter: blur(4px);
        }
        .dh-doc-preview-head{
          display: flex;
          align-items: center;
          justify-content: space-between;
          gap: 10px;
          padding: 12px 14px;
          background: linear-gradient(90deg, rgba(35,99,180,0.42), rgba(22,54,96,0.42));
          border-bottom: 1px solid rgba(255,255,255,0.14);
        }
        .dh-doc-preview-title{
          font-weight: 800;
          font-size: 1rem;
          color: #f7fbff !important;
          letter-spacing: 0.2px;
        }
        .dh-doc-preview-meta{
          font-size: 0.8rem;
          font-weight: 700;
          color: #d3e6ff !important;
          white-space: nowrap;
        }
        .dh-doc-preview-body{
          padding: 14px 16px 16px 16px;
          font-size: 0.96rem;
          line-height: 1.72;
          color: #ecf4ff !important;
          letter-spacing: 0.15px;
        }


        /* Hero (landing) */
        .dh-hero-box{
          margin: 10px auto 18px auto;
          padding: 12px 18px;
          max-width: 820px;
          text-align: center;
          background: linear-gradient(180deg, rgba(21,101,192,0.22), rgba(10,18,35,0.55));
          border: 1px solid rgba(255,255,255,0.18);
          border-radius: 14px;
          box-shadow: 0 14px 30px rgba(0,0,0,0.30);
          backdrop-filter: blur(6px);
        }
        .dh-hero-line{
          font-weight: 700;
          letter-spacing: 0.2px;
          color: #f5f8ff !important;
          font-size: 1.02rem;
          line-height: 1.5;
        }
        .dh-hero-line + .dh-hero-line{
          margin-top: 6px;
          font-weight: 600;
          font-size: 0.98rem;
          opacity: 0.95;
        }
        .dh-panel{
          background: transparent !important;
          border: none !important;
          box-shadow: none !important;
          padding: 0 !important;
        }
        .dh-panel img{
          border-radius: 18px;
          box-shadow: 0 18px 45px rgba(0,0,0,0.28);
        }
        .login-box div[data-baseweb="input"] > div,
        .login-box input{
          background: rgba(246, 250, 255, 0.92) !important;
          border: 1px solid rgba(126, 166, 255, 0.55) !important;
          color: #0b1320 !important;
          border-radius: 12px !important;
          min-height: 44px !important;
          box-shadow: none !important;
        }
        .login-box input::placeholder{
          color: rgba(11,19,32,0.55) !important;
        }


        /* Radio em “botão” */
        section[data-testid="stSidebar"] div[role="radiogroup"]{
          width: 100% !important;
        }
        section[data-testid="stSidebar"] div[role="radiogroup"] > label{
          background: rgba(255,255,255,0.06) !important;
          border: 1px solid rgba(255,255,255,0.10) !important;
          padding: 10px 12px !important;
          border-radius: 12px !important;
          margin: 6px 0 !important;
          width: 100% !important;
          min-width: 100% !important;
          max-width: 100% !important;
          box-sizing: border-box !important;
          display: flex !important;
          align-items: center !important;
        }
        section[data-testid="stSidebar"] div[role="radiogroup"] > label:hover{
          background: rgba(46,125,50,0.18) !important;
          border-color: rgba(46,125,50,0.35) !important;
        }
        section[data-testid="stSidebar"] div[role="radiogroup"] > label:has(input:checked){
          background: rgba(46,125,50,0.26) !important;
          border-color: rgba(46,125,50,0.55) !important;
          box-shadow: 0 10px 26px rgba(0,0,0,0.35) !important;
        }
        section[data-testid="stSidebar"] div[role="radiogroup"] > label > div:first-child{ display:none !important; }
        section[data-testid="stSidebar"] div[role="radiogroup"] > label > div:last-child{
          width: 100% !important;
          min-width: 0 !important;
        }

        /* Sidebar user card */
        .dh-sign-card{
          background: linear-gradient(180deg, rgba(255,255,255,0.07), rgba(255,255,255,0.03)) !important;
          border: 1px solid rgba(255,255,255,0.10) !important;
          border-radius: 14px !important;
          box-shadow: 0 12px 24px rgba(0,0,0,0.22) !important;
          padding: 10px 10px !important;
        }
        .dh-side-top{
          width: 100%;
          margin-bottom: 8px;
        }
        .dh-side-user{
          width: 100%;
          box-sizing: border-box;
          display: grid;
          grid-template-columns: 44px 1fr;
          gap: 10px;
          align-items: center;
          padding: 10px 11px !important;
          border-radius: 14px !important;
          border: 1px solid rgba(113, 198, 255, 0.24) !important;
          background:
            radial-gradient(circle at 12% 14%, rgba(88, 199, 255, 0.18), transparent 34%),
            linear-gradient(155deg, rgba(18, 29, 58, 0.94), rgba(13, 21, 48, 0.93));
          box-shadow:
            inset 0 1px 0 rgba(255,255,255,0.14),
            0 12px 22px rgba(0,0,0,0.28),
            0 0 16px rgba(78, 170, 255, 0.08);
        }
        .dh-side-avatar{
          width: 44px;
          height: 44px;
          border-radius: 12px;
          border: 1px solid rgba(148, 217, 255, 0.32);
          background:
            radial-gradient(circle at 28% 22%, rgba(145, 227, 255, 0.80), rgba(52, 126, 201, 0.35) 56%, rgba(24, 54, 99, 0.70) 100%);
          box-shadow:
            inset 0 1px 0 rgba(255,255,255,0.32),
            0 8px 14px rgba(8, 15, 35, 0.32);
          display: flex;
          align-items: center;
          justify-content: center;
          font-size: 20px;
        }
        .dh-side-user-info{
          min-width: 0;
        }
        .dh-side-name{
          font-weight: 900;
          font-size: 1rem;
          line-height: 1.14;
          color: #f1f7ff;
          text-shadow: 0 1px 0 rgba(0,0,0,0.34);
        }
        .dh-side-role{
          margin-top: 1px;
          font-size: 0.8rem;
          color: rgba(214, 232, 255, 0.82);
          line-height: 1.2;
        }
        .dh-side-user-pill{
          margin-top: 5px;
          display: inline-flex;
          align-items: center;
          gap: 6px;
          padding: 2px 7px;
          border-radius: 999px;
          border: 1px solid rgba(97, 211, 155, 0.34);
          background: rgba(44, 156, 114, 0.16);
          color: #d5ffe9;
          font-size: 0.68rem;
          font-weight: 800;
          letter-spacing: 0.02em;
        }
        .dh-side-user-pill::before{
          content: "";
          width: 8px;
          height: 8px;
          border-radius: 999px;
          background: #43f0aa;
          box-shadow: 0 0 10px rgba(67, 240, 170, 0.85);
        }
        .dh-menu-title{
          display: inline-block;
          padding: 7px 14px;
          border-radius: 12px;
          background: linear-gradient(120deg, rgba(34,55,146,0.92), rgba(24,35,99,0.92));
          border: 1px solid rgba(152,181,255,0.22);
          color: #f8fbff;
          font-weight: 780;
          font-size: 0.92rem;
          letter-spacing: 0.01em;
          margin: 4px 0 7px 0;
          box-shadow: 0 8px 18px rgba(4,10,28,0.34), inset 0 1px 0 rgba(255,255,255,0.16);
        }

        .dh-menu-card{
          width: 100%;
          min-height: 54px;
          border-radius: 13px;
          border: 1px solid rgba(132, 156, 214, 0.1);
          background: linear-gradient(180deg, rgba(13,22,43,0.78), rgba(10,16,34,0.72));
          display: flex;
          flex-direction: row;
          align-items: center;
          justify-content: flex-start;
          padding: 8px 11px;
          gap: 10px;
          box-sizing: border-box;
          box-shadow:
            inset 0 1px 0 rgba(255,255,255,0.04),
            0 7px 14px rgba(0,0,0,0.1);
          transition: transform 0.18s ease, box-shadow 0.18s ease, border-color 0.18s ease, background 0.18s ease;
        }
        .dh-menu-card-active{
          border-color: rgba(62,215,149,0.34);
          background: linear-gradient(180deg, rgba(10,42,50,0.9), rgba(8,28,36,0.88));
          box-shadow:
            inset 0 1px 0 rgba(255,255,255,0.06),
            0 8px 18px rgba(0,0,0,0.14),
            0 0 0 1px rgba(34,197,94,0.05);
        }
        .dh-menu-card-icon{
          width: 34px;
          min-width: 34px;
          height: 34px;
          display: flex;
          align-items: center;
          justify-content: center;
          border-radius: 9px;
          overflow: hidden;
          background: linear-gradient(180deg, rgba(18,29,58,0.72), rgba(11,20,40,0.62));
          border: 1px solid rgba(151, 177, 233, 0.1);
          flex-shrink: 0;
        }
        .dh-menu-icon-img{
          width: 22px;
          height: 22px;
          object-fit: contain;
          object-position: center;
          filter: saturate(1.02) contrast(1.01);
          display: block;
        }
        .dh-menu-card-label{
          flex: 1 1 auto;
          min-width: 0;
          font-size: 0.9rem;
          line-height: 1.16;
          font-weight: 700;
          color: rgba(240,248,255,0.94) !important;
          text-shadow: 0 1px 0 rgba(0,0,0,0.28);
          display: block;
          text-align: left;
          white-space: normal;
          overflow: hidden;
          text-overflow: ellipsis;
          letter-spacing: 0.01em;
        }
        .dh-menu-link{
          display: block;
          text-decoration: none !important;
          width: 100%;
        }
        .dh-menu-fab{
          position: fixed;
          top: 16px;
          left: 16px;
          z-index: 10050;
          display: none;
          align-items: center;
          gap: 8px;
          padding: 8px 12px;
          border-radius: 999px;
          background: linear-gradient(135deg, rgba(15,23,42,0.92), rgba(9,16,31,0.92));
          border: 1px solid rgba(148,163,184,0.22);
          color: #f8fbff;
          font-weight: 800;
          box-shadow: 0 12px 22px rgba(0,0,0,0.28);
          cursor: pointer;
        }
        .dh-menu-fab span:first-child{
          font-size: 1rem;
        }
        .dh-menu-fab span:last-child{
          font-size: 0.88rem;
          letter-spacing: 0.01em;
        }
        body.dh-sidebar-collapsed .dh-menu-fab{
          display: inline-flex;
        }
        body.dh-sidebar-open .dh-menu-fab{
          display: none;
        }
        section[data-testid="stSidebar"]{
          transition: transform 0.22s ease, box-shadow 0.22s ease;
          will-change: transform;
        }
        body.dh-sidebar-collapsed section[data-testid="stSidebar"]{
          transform: translateX(-105%);
          box-shadow: none !important;
        }
        @media (max-width: 980px){
          section[data-testid="stSidebar"]{
            position: fixed !important;
            top: 0;
            left: 0;
            height: 100dvh;
            max-height: 100dvh;
            z-index: 9999;
            background: rgba(7,14,28,0.98);
            overflow: hidden !important;
            overscroll-behavior: contain;
            touch-action: pan-y pinch-zoom;
          }
          section[data-testid="stSidebar"] > div,
          section[data-testid="stSidebar"] > div:first-child,
          section[data-testid="stSidebar"] [data-testid="stSidebarUserContent"],
          section[data-testid="stSidebar"] [data-testid="stSidebarContent"]{
            height: 100% !important;
            max-height: 100dvh !important;
            overflow-y: auto !important;
            overflow-x: hidden !important;
            -webkit-overflow-scrolling: touch !important;
            overscroll-behavior: contain !important;
            touch-action: pan-y pinch-zoom !important;
            padding-bottom: max(18px, env(safe-area-inset-bottom));
          }
        }
        .dh-menu-card-empty{
          display: none;
        }
        .dh-menu-card:hover{
          border-color: rgba(108, 205, 166, 0.24);
          background: linear-gradient(180deg, rgba(16,28,52,0.9), rgba(11,19,40,0.88));
          box-shadow:
            inset 0 1px 0 rgba(255,255,255,0.05),
            0 9px 16px rgba(0,0,0,0.14);
          transform: translateY(-1px);
        }
        @media (max-width: 900px){
          section[data-testid="stSidebar"]{
            min-width: 250px !important;
            max-width: 250px !important;
          }
          .dh-menu-card{
            min-height: 52px;
            padding: 8px 10px;
            gap: 9px;
            border-radius: 13px;
          }
          .dh-menu-card-icon{
            width: 32px;
            min-width: 32px;
            height: 32px;
            border-radius: 9px;
          }
          .dh-menu-icon-img{
            width: 21px;
            height: 21px;
          }
          .dh-menu-card-label{
            font-size: 0.86rem;
          }
          .dh-menu-gap{height:4px;}
          .dh-side-user{
            grid-template-columns: 40px 1fr;
            padding: 9px 10px !important;
          }
          .dh-side-avatar{
            width: 40px;
            height: 40px;
            font-size: 18px;
          }
          .dh-side-name{font-size:0.95rem;}
          .dh-side-role{font-size:0.76rem;}
        }
        .dh-icon-menu-fallback{
          width: 28px;
          height: 28px;
          border-radius: 9px;
          border: 1px dashed rgba(255,255,255,0.20);
          display: flex;
          align-items: center;
          justify-content: center;
          text-align: center;
          padding: 3px;
          font-size: 0.46rem;
          font-weight: 800;
          line-height: 1.05;
          color: #dff7ef !important;
          background: rgba(8, 25, 21, 0.52);
        }
        .dh-menu-gap{
          height: 5px;
        }
        
        /* Botões do menu lateral em modo estável */
        [data-testid="stSidebar"] div[class*="st-key-dh_menu_btn_"]{
          margin: 0 0 8px 0 !important;
          height: auto !important;
          min-height: 0 !important;
          overflow: visible !important;
          position: static !important;
          z-index: auto !important;
        }
        [data-testid="stSidebar"] div[class*="st-key-dh_menu_btn_"] > div{
          height: auto !important;
          min-height: 0 !important;
        }
        [data-testid="stSidebar"] div[class*="st-key-dh_menu_btn_"] .stButton > button,
        [data-testid="stSidebar"] div[class*="st-key-dh_menu_btn_"] button{
          width: 100% !important;
          min-height: 54px !important;
          height: 54px !important;
          border-radius: 13px !important;
          border: 1px solid rgba(132,156,214,0.12) !important;
          background: linear-gradient(180deg, rgba(13,22,43,0.88), rgba(10,16,34,0.82)) !important;
          color: rgba(240,248,255,0.96) !important;
          font-weight: 800 !important;
          text-align: left !important;
          justify-content: flex-start !important;
          padding: 0 14px !important;
          margin: 0 !important;
          box-shadow: inset 0 1px 0 rgba(255,255,255,0.04), 0 7px 14px rgba(0,0,0,0.10) !important;
          opacity: 1 !important;
          transform: none !important;
        }
        [data-testid="stSidebar"] div[class*="st-key-dh_menu_btn_"] button[kind="primary"]{
          border-color: rgba(62,215,149,0.34) !important;
          background: linear-gradient(180deg, rgba(10,42,50,0.94), rgba(8,28,36,0.90)) !important;
        }
        [data-testid="stSidebar"] div[class*="st-key-dh_menu_btn_"] button:hover{
          border-color: rgba(108,205,166,0.24) !important;
          background: linear-gradient(180deg, rgba(16,28,52,0.92), rgba(11,19,40,0.90)) !important;
        }
        [data-testid="stSidebar"] div[class*="st-key-dh_menu_btn_"] button,
        [data-testid="stSidebar"] div[class*="st-key-dh_menu_btn_"] button *{
          font-size: inherit !important;
          line-height: inherit !important;
          color: rgba(240,248,255,0.96) !important;
        }

        /* Botões no sidebar (Upload / Sair) - garante contraste em qualquer navegador */
        [data-testid="stSidebar"] .dh-logout .stButton > button,
        [data-testid="stSidebar"] [data-testid="stFileUploader"] button{
          background: rgba(255,255,255,0.22) !important; /* cinza visível */
          border: 1px solid rgba(255,255,255,0.30) !important;
          color: rgba(255,255,255,0.96) !important;
          font-weight: 800 !important;
          border-radius: 12px !important;
        }
        [data-testid="stSidebar"] .dh-logout .stButton > button:hover,
        [data-testid="stSidebar"] [data-testid="stFileUploader"] button:hover{
          background: rgba(255,255,255,0.30) !important;
          border-color: rgba(255,255,255,0.40) !important;
        }

/* ===== Fix contraste de inputs (Selectbox / Date / Time / Text) ===== */
div[data-baseweb="select"] > div,
div[data-baseweb="input"] > div,
div[data-baseweb="datepicker"] > div {
  background: rgba(10, 20, 35, 0.55) !important;
  border: 1px solid rgba(255,255,255,0.18) !important;
}

div[data-baseweb="select"] span,
div[data-baseweb="select"] input,
div[data-baseweb="input"] input,
div[data-baseweb="datepicker"] input,
div[data-baseweb="timepicker"] input,
div[data-baseweb="textarea"] textarea {
  color: rgba(255,255,255,0.95) !important;
}

div[data-baseweb="select"] svg,
div[data-baseweb="datepicker"] svg {
  fill: rgba(255,255,255,0.80) !important;
}

/* Placeholder */
div[data-baseweb="input"] input::placeholder,
div[data-baseweb="select"] input::placeholder,
div[data-baseweb="datepicker"] input::placeholder,
div[data-baseweb="textarea"] textarea::placeholder {
  color: rgba(255,255,255,0.55) !important;
}

/* Dropdown do select (lista de pacientes) */
ul[role="listbox"] {
  background: rgba(255,255,255,0.96) !important;
  border: 1px solid rgba(0,0,0,0.18) !important;
  box-shadow: 0 12px 28px rgba(0,0,0,0.35) !important;
}
li[role="option"] {
  color: #0d1627 !important;
}
li[role="option"][aria-selected="true"] {
  background: rgba(46, 125, 50, 0.18) !important;
}

/* Calendário do date_input (popup) */
div[data-baseweb="popover"] div[role="dialog"] {
  background: rgba(255,255,255,0.96) !important;
  color: #0d1627 !important;
  border: 1px solid rgba(0,0,0,0.18) !important;
}
div[data-baseweb="calendar"] * {
  color: #0d1627 !important;
}

/* KPI usa st.container(border=True) para estabilidade em producao */




/* ==========================================================
   FIX: Sidebar toggle + legibilidade de inputs (produção)
   ========================================================== */

/* 1) Toggle do Sidebar (não pode sumir).
   Streamlit muda data-testid entre versões, então cobrimos os dois. */
div[data-testid="collapsedControl"],
div[data-testid="stSidebarCollapsedControl"]{
  display: flex !important;
  visibility: visible !important;
  opacity: 1 !important;
  position: fixed !important;
  top: 14px !important;
  left: 14px !important;
  z-index: 99999 !important;
  pointer-events: auto !important;
}
div[data-testid="collapsedControl"] button,
div[data-testid="stSidebarCollapsedControl"] button{
  background: rgba(255,255,255,0.11) !important;
  border: 1px solid rgba(255,255,255,0.22) !important;
  border-radius: 11px !important;
  width: 40px !important;
  height: 40px !important;
  padding: 7px !important;
  color: #ffffff !important;
  box-shadow: 0 8px 18px rgba(0,0,0,0.24) !important;
}
div[data-testid="collapsedControl"] button:hover,
div[data-testid="stSidebarCollapsedControl"] button:hover{
  background: rgba(46,125,50,0.22) !important;
  border-color: rgba(46,125,50,0.42) !important;
}
div[data-testid="collapsedControl"] svg,
div[data-testid="stSidebarCollapsedControl"] svg{
  fill: currentColor !important;
  stroke: currentColor !important;
}
/* 2) Inputs/Selects/Calendário sempre legíveis (texto escuro em fundo claro) */

/* Campos de texto / número / área / data / hora */
div[data-testid="stTextInput"] input,
div[data-testid="stNumberInput"] input,
div[data-testid="stTextArea"] textarea,
div[data-testid="stDateInput"] input,
div[data-testid="stTimeInput"] input{
  background: rgba(255,255,255,0.92) !important;
  color: #0d1627 !important;
  border: 1px solid rgba(0,0,0,0.18) !important;
}

div[data-testid="stTextInput"] input::placeholder,
div[data-testid="stNumberInput"] input::placeholder,
div[data-testid="stTextArea"] textarea::placeholder,
div[data-testid="stDateInput"] input::placeholder,
div[data-testid="stTimeInput"] input::placeholder{
  color: rgba(0,0,0,0.45) !important;
}

/* Select (valor) - combobox (mais robusto) */
div[data-testid="stSelectbox"] div[data-baseweb="select"] div[role="combobox"],
div[data-testid="stMultiSelect"] div[data-baseweb="select"] div[role="combobox"]{
  background: rgba(255,255,255,0.92) !important;
  color: #0d1627 !important;
  border: 1px solid rgba(0,0,0,0.18) !important;
}
div[data-testid="stSelectbox"] div[data-baseweb="select"] div[role="combobox"] *,
div[data-testid="stMultiSelect"] div[data-baseweb="select"] div[role="combobox"] *{
  color: #0d1627 !important;
}
div[data-testid="stSelectbox"] div[data-baseweb="select"] input,
div[data-testid="stMultiSelect"] div[data-baseweb="select"] input{
  color: #0d1627 !important;
}

/* Select (fallback - algumas versões renderizam diferente) */
div[data-testid="stSelectbox"] div[data-baseweb="select"] > div,
div[data-testid="stMultiSelect"] div[data-baseweb="select"] > div{
  background: rgba(255,255,255,0.92) !important;
  color: #0d1627 !important;
  border: 1px solid rgba(0,0,0,0.18) !important;
}

/* Popover/lista do select */
div[data-baseweb="popover"]{
  z-index: 999999 !important;
}
div[role="listbox"],
ul[role="listbox"],
div[data-testid="stSelectbox"] ul{
  background: #ffffff !important;
  color: #0d1627 !important;
  border: 1px solid rgba(0,0,0,0.18) !important;
}
div[role="option"],
li[role="option"]{
  color: #0d1627 !important;
}
div[role="option"]:hover,
li[role="option"]:hover{
  background: rgba(46,125,50,0.10) !important;
}

/* Calendário (DateInput) */
div[data-baseweb="calendar"],
div[data-baseweb="calendar"] *{
  background: #ffffff !important;
  color: #0d1627 !important;
}


/* ================= DietHealth fixes (dashboard + selects) ================= */

/* DataFrames: maiores, mais bonitas e com sensação dinâmica */
div[data-testid="stDataFrame"]{
  background: linear-gradient(135deg, rgba(8,20,46,0.86), rgba(10,35,73,0.78)) !important;
  border: 1px solid rgba(80,168,255,0.34) !important;
  border-radius: 18px !important;
  padding: 8px !important;
  box-shadow: 0 14px 30px rgba(0,0,0,0.30), inset 0 1px 0 rgba(255,255,255,0.05) !important;
  transition: transform .18s ease, box-shadow .18s ease, border-color .18s ease !important;
}
div[data-testid="stDataFrame"]:hover{
  transform: translateY(-1px) !important;
  border-color: rgba(69,201,166,0.50) !important;
  box-shadow: 0 20px 36px rgba(0,0,0,0.35), inset 0 1px 0 rgba(255,255,255,0.08) !important;
}
div[data-testid="stDataFrame"] > div{
  border-radius: 12px !important;
}
div[data-testid="stDataFrame"] button{
  border-radius: 10px !important;
}

/* KPI cards (Painel de Controle) */
.dh-admin-head{
  display: grid;
  grid-template-columns:minmax(0,1.6fr) minmax(240px,1fr);
  align-items: stretch;
  gap: 12px;
  margin: 6px 0 14px 0;
  padding: 14px 16px;
  border-radius: 24px;
  border: 1px solid rgba(121,192,232,0.14);
  background:
    radial-gradient(circle at top left, rgba(34,197,94,0.12), transparent 34%),
    radial-gradient(circle at bottom right, rgba(59,130,246,0.14), transparent 32%),
    linear-gradient(145deg, rgba(10,24,42,0.98), rgba(13,31,57,0.96));
  box-shadow: 0 24px 46px rgba(2,6,23,0.22);
}
.dh-admin-head-main{
  display:flex;
  align-items:flex-start;
  gap:10px;
}
.dh-admin-head-icon{
  width: 40px;
  height: 40px;
  border-radius: 12px;
  border: 1px solid rgba(120,218,192,0.34);
  background: linear-gradient(150deg, rgba(9,29,46,0.80), rgba(7,20,35,0.74));
  display: inline-flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 14px 26px rgba(0,0,0,0.22);
}
.dh-admin-head-icon svg{
  width: 20px;
  height: 20px;
  stroke: rgba(189,255,238,0.96);
  stroke-width: 1.9;
  fill: none;
  stroke-linecap: round;
  stroke-linejoin: round;
}
.dh-admin-head-copy h2{
  margin: 0;
  color: rgba(244,251,255,0.98);
  font-size: clamp(1.35rem, 2.1vw, 1.75rem);
  line-height: 1.16;
  letter-spacing: -0.02em;
  font-weight: 800;
}
.dh-admin-head-copy p{
  margin: 6px 0 0 0;
  color: rgba(202,224,233,0.82);
  font-size: 0.9rem;
  line-height: 1.5;
  max-width: 820px;
}
.dh-admin-head-side{
  display:grid;
  gap:8px;
  align-content:start;
}
.dh-admin-head-chip{
  display:inline-flex;
  align-items:center;
  justify-content:center;
  min-height:36px;
  padding:0 10px;
  border-radius:999px;
  background:rgba(255,255,255,0.92);
  border:1px solid rgba(148,163,184,0.16);
  color:#16233b;
  font-size: 0.85rem;
  font-weight:760;
  box-shadow:0 12px 22px rgba(2,6,23,0.08);
}
.dh-admin-kpi-grid{
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 14px;
  margin-bottom: 10px;
}
.dh-admin-kpi-grid--rich{
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 15px;
}
.metric-container{
  position: relative;
  isolation: isolate;
  border-radius: 22px !important;
  border: 1px solid rgba(169,224,255,0.16) !important;
  background:
    linear-gradient(160deg, rgba(11,29,46,0.9), rgba(8,19,34,0.84)),
    radial-gradient(circle at 86% 16%, rgba(79,181,157,0.18), transparent 46%) !important;
  padding: 16px 16px 18px !important;
  min-height: 144px;
  display: flex;
  flex-direction: column;
  justify-content: flex-start;
  gap: 8px;
  box-shadow: 0 18px 34px rgba(0,0,0,0.22), inset 0 1px 0 rgba(255,255,255,0.04) !important;
  transition: transform .2s ease, border-color .2s ease, box-shadow .2s ease;
}
.metric-container::before{
  content: "";
  position: absolute;
  left: 16px;
  right: 16px;
  top: 0;
  height: 1px;
  background: linear-gradient(90deg, transparent, rgba(176,255,229,0.30), transparent);
  pointer-events: none;
}
.metric-container:hover{
  transform: translateY(-2px);
  border-color: rgba(123,236,208,0.36) !important;
  box-shadow: 0 20px 38px rgba(0,0,0,0.28), inset 0 1px 0 rgba(255,255,255,0.07) !important;
}
.metric-top{
  display: flex;
  justify-content: flex-start;
  align-items: center;
}
.metric-icon{
  width: 31px;
  height: 31px;
  border-radius: 10px;
  border: 1px solid rgba(160,228,255,0.28);
  background: rgba(8,22,37,0.66);
  display: inline-flex;
  align-items: center;
  justify-content: center;
}
.metric-icon svg{
  width: 16px;
  height: 16px;
  stroke: rgba(206,246,255,0.95);
  stroke-width: 1.8;
  fill: none;
  stroke-linecap: round;
  stroke-linejoin: round;
}
.metric-value{
  margin-top: 2px !important;
  font-size: clamp(1.65rem, 2.35vw, 2.15rem) !important;
  line-height: 1.08 !important;
  font-weight: 820 !important;
  letter-spacing: -0.015em !important;
  color: #f3f9ff !important;
}
.metric-label{
  margin-top: auto !important;
  font-size: 0.82rem !important;
  font-weight: 700 !important;
  letter-spacing: 0.02em !important;
  color: rgba(196,219,228,0.86) !important;
  text-transform: uppercase;
}
.metric-note{
  font-size: 0.83rem;
  color: rgba(176, 204, 219, 0.8);
  line-height: 1.42;
}
.metric-pacientes{ border-color: rgba(96,218,179,0.25) !important; }
.metric-agenda{ border-color: rgba(112,183,255,0.26) !important; }
.metric-biblioteca{ border-color: rgba(159,200,255,0.25) !important; }
.metric-receita{ border-color: rgba(115,232,200,0.29) !important; }
.metric-receita .metric-value{ color: rgba(142,255,214,0.96) !important; }
.metric-despesa{ border-color: rgba(251, 146, 60, 0.28) !important; }
.metric-despesa .metric-value{ color: rgba(255, 195, 113, 0.96) !important; }
.metric-saldo{ border-color: rgba(74, 222, 128, 0.30) !important; }
.metric-saldo .metric-value{ color: rgba(187, 255, 206, 0.98) !important; }
.metric-ticket{ border-color: rgba(168, 139, 250, 0.28) !important; }
.metric-ticket .metric-value{ color: rgba(224, 204, 255, 0.96) !important; }
.metric-liquido{ border-color: rgba(45, 212, 191, 0.28) !important; }
.metric-liquido .metric-value{ color: rgba(171, 255, 244, 0.96) !important; }
.dh-admin-divider{
  height: 1px;
  margin: 6px 0 16px 0;
  background: linear-gradient(90deg, rgba(153,199,231,0.04), rgba(153,199,231,0.28), rgba(153,199,231,0.04));
}
.dh-admin-subtitle{
  margin: 6px 0 10px 0 !important;
  color: rgba(241,248,255,0.95) !important;
  font-size: 1.52rem !important;
  line-height: 1.12 !important;
  font-weight: 760 !important;
  letter-spacing: -0.01em;
}
.dh-admin-panel-title{
  margin: 0 0 12px 0;
  color: rgba(241,248,255,0.96);
  font-size: 1.08rem;
  line-height: 1.2;
  font-weight: 780;
  letter-spacing: -0.01em;
}
.dh-admin-panel-shell{
  padding:18px;
  margin:0 0 16px;
  border-radius:22px;
  border:1px solid rgba(148,163,184,0.14);
  background:linear-gradient(180deg, rgba(255,255,255,0.06), rgba(255,255,255,0.03));
  box-shadow:0 16px 30px rgba(2,6,23,0.12);
}
.dh-admin-panel-shell--compact{
  padding:16px;
}
div[class*="st-key-dh_dashboard_chart_fin_shell"],
div[class*="st-key-dh_dashboard_chart_growth_shell"],
div[class*="st-key-dh_dashboard_fin_summary_shell"],
div[class*="st-key-dh_dashboard_category_shell"],
div[class*="st-key-dh_dashboard_recent_patients_shell"],
div[class*="st-key-dh_dashboard_upcoming_shell"],
div[class*="st-key-dh_dashboard_summary_shell"],
div[class*="st-key-dh_dashboard_finance_rows_shell"],
div[class*="st-key-dh_dashboard_finance_rows_shell_bottom"],
div[class*="st-key-dh_dashboard_activity_shell"],
div[class*="st-key-dh_library_recent_shell"],
div[class*="st-key-dh_library_side_shell"]{
  padding:18px;
  margin:0 0 16px;
  border-radius:22px;
  border:1px solid rgba(148,163,184,0.14);
  background:linear-gradient(180deg, rgba(255,255,255,0.06), rgba(255,255,255,0.03));
  box-shadow:0 16px 30px rgba(2,6,23,0.12);
}
div[class*="st-key-dh_dashboard_chart_fin_shell"],
div[class*="st-key-dh_dashboard_chart_growth_shell"]{
  min-height: 0;
}
div[class*="st-key-dh_dashboard_fin_summary_shell"]{
  min-height: 0;
}
div[class*="st-key-dh_dashboard_recent_patients_shell"],
div[class*="st-key-dh_dashboard_upcoming_shell"],
div[class*="st-key-dh_dashboard_summary_shell"],
div[class*="st-key-dh_dashboard_finance_rows_shell"],
div[class*="st-key-dh_dashboard_finance_rows_shell_bottom"],
div[class*="st-key-dh_dashboard_activity_shell"],
div[class*="st-key-dh_library_recent_shell"],
div[class*="st-key-dh_library_side_shell"]{
  padding:16px;
}
div[class*="st-key-dh_dashboard_chart_fin_shell"] [data-testid="stVerticalBlock"],
div[class*="st-key-dh_dashboard_chart_growth_shell"] [data-testid="stVerticalBlock"],
div[class*="st-key-dh_dashboard_fin_summary_shell"] [data-testid="stVerticalBlock"],
div[class*="st-key-dh_dashboard_activity_shell"] [data-testid="stDataFrame"],
div[class*="st-key-dh_dashboard_finance_rows_shell"] [data-testid="stDataFrame"],
div[class*="st-key-dh_library_recent_shell"] [data-testid="stVerticalBlock"],
div[class*="st-key-dh_library_side_shell"] [data-testid="stVerticalBlock"]{
  min-width:0 !important;
}
div[class*="st-key-dh_dashboard_chart_fin_shell"] .js-plotly-plot,
div[class*="st-key-dh_dashboard_chart_growth_shell"] .js-plotly-plot,
div[class*="st-key-dh_dashboard_category_shell"] .js-plotly-plot{
  margin-bottom:0 !important;
}
div[class*="st-key-dh_dashboard_chart_fin_shell"] [data-testid="stPlotlyChart"],
div[class*="st-key-dh_dashboard_chart_growth_shell"] [data-testid="stPlotlyChart"],
div[class*="st-key-dh_dashboard_category_shell"] [data-testid="stPlotlyChart"]{
  margin-bottom: 0 !important;
}
.dh-admin-fin-table-wrap{
  border-radius: 18px;
  border: 1px solid rgba(125,173,204,0.18);
  overflow: hidden;
  background: linear-gradient(180deg, rgba(10,24,42,0.52), rgba(8,18,33,0.3));
}
.dh-admin-fin-table{
  width: 100%;
  border-collapse: collapse;
}
.dh-admin-fin-table thead th{
  text-align: left;
  padding: 11px 12px;
  font-size: 0.8rem;
  font-weight: 760;
  color: rgba(196,219,228,0.86);
  background: rgba(255,255,255,0.04);
  border-bottom: 1px solid rgba(125,173,204,0.14);
}
.dh-admin-fin-table tbody td{
  padding: 11px 12px;
  font-size: 0.92rem;
  color: rgba(241,248,255,0.94);
  border-bottom: 1px solid rgba(125,173,204,0.1);
  vertical-align: middle;
}
.dh-admin-fin-table tbody tr:last-child td{
  border-bottom: none;
}
.dh-admin-fin-table tbody td:last-child{
  text-align: right;
  white-space: nowrap;
  font-weight: 760;
}
.dh-admin-fin-label{
  font-weight: 720;
  color: rgba(244,251,255,0.98);
}
.dh-admin-fin-note{
  display: block;
  margin-top: 3px;
  font-size: 0.8rem;
  line-height: 1.35;
  color: rgba(176, 204, 219, 0.8);
}
.dh-admin-empty{
  display: flex;
  flex-direction: column;
  gap: 6px;
  padding: 14px 16px;
  border-radius: 16px;
  border: 1px dashed rgba(125, 173, 204, 0.28);
  background: linear-gradient(180deg, rgba(10,26,43,0.66), rgba(9,18,32,0.52));
  color: rgba(192, 215, 229, 0.82);
}
.dh-admin-empty strong{
  color: rgba(239, 248, 255, 0.96);
  font-size: 0.98rem;
}
.dh-admin-empty span{
  line-height: 1.45;
  font-size: 0.91rem;
}
.dh-admin-list-item{
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 14px;
  padding: 13px 14px;
  margin-bottom: 10px;
  border-radius: 16px;
  border: 1px solid rgba(119, 176, 210, 0.16);
  background: linear-gradient(145deg, rgba(9,24,39,0.82), rgba(10,20,34,0.74));
  box-shadow: inset 0 1px 0 rgba(255,255,255,0.03), 0 10px 18px rgba(2,6,23,0.08);
}
.dh-admin-list-item strong{
  display: block;
  color: rgba(246, 250, 255, 0.97);
  font-size: 0.95rem;
  font-weight: 700;
}
.dh-admin-list-item span{
  display: block;
  margin-top: 3px;
  color: rgba(181, 204, 219, 0.78);
  font-size: 0.84rem;
  line-height: 1.35;
}
.dh-admin-list-item small{
  white-space: nowrap;
  color: rgba(150, 190, 214, 0.78);
  font-size: 0.8rem;
}
.dh-admin-summary-card{
  display: grid;
  gap: 10px;
  padding: 16px;
  margin-bottom: 0;
  border-radius: 20px;
  border: 1px solid rgba(109, 176, 211, 0.18);
  background: linear-gradient(160deg, rgba(10,28,45,0.9), rgba(8,18,33,0.82));
  box-shadow: 0 14px 28px rgba(0,0,0,0.18);
}
.dh-admin-inline-stat{
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 10px;
  padding-bottom: 9px;
  border-bottom: 1px solid rgba(120, 160, 188, 0.12);
}
.dh-admin-inline-stat:last-child{
  border-bottom: none;
  padding-bottom: 0;
}
.dh-admin-inline-stat span{
  color: rgba(185, 211, 228, 0.80);
  font-size: 0.88rem;
}
.dh-admin-inline-stat strong{
  color: rgba(245, 249, 255, 0.98);
  font-size: 0.92rem;
  font-weight: 730;
}
@media (max-width: 1100px){
  .dh-admin-head{
    grid-template-columns:1fr;
  }
  .dh-admin-kpi-grid{
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
  .dh-admin-kpi-grid--rich{
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}
@media (max-width: 680px){
  .dh-admin-head{
    gap: 12px;
    margin-bottom: 14px;
    padding:16px;
  }
  .dh-admin-head-icon{
    width: 40px;
    height: 40px;
    border-radius: 12px;
  }
  .dh-admin-head-copy p{
    font-size: 0.9rem;
  }
  .dh-admin-head-chip{
    min-height:40px;
    font-size:.84rem;
  }
  .dh-admin-kpi-grid{
    grid-template-columns: 1fr;
    gap: 11px;
  }
  .dh-admin-kpi-grid--rich{
    grid-template-columns: 1fr;
  }
  .metric-container{
    min-height: 126px;
    padding: 14px 13px 15px !important;
  }
  .dh-admin-list-item{
    align-items: flex-start;
    flex-direction: column;
  }
  .dh-admin-panel-shell{
    padding:15px;
  }
  div[class*="st-key-dh_dashboard_chart_fin_shell"],
  div[class*="st-key-dh_dashboard_chart_growth_shell"],
  div[class*="st-key-dh_dashboard_category_shell"],
  div[class*="st-key-dh_dashboard_recent_patients_shell"],
  div[class*="st-key-dh_dashboard_upcoming_shell"],
  div[class*="st-key-dh_dashboard_summary_shell"],
  div[class*="st-key-dh_dashboard_finance_rows_shell"],
  div[class*="st-key-dh_dashboard_activity_shell"],
  div[class*="st-key-dh_library_recent_shell"],
  div[class*="st-key-dh_library_side_shell"]{
    padding:15px;
  }
}

/* Inputs: sempre legíveis */
div[data-testid="stTextInput"] input,
div[data-testid="stNumberInput"] input,
div[data-testid="stTextArea"] textarea,
div[data-testid="stDateInput"] input,
div[data-testid="stTimeInput"] input{
  background: rgba(255,255,255,0.95) !important;
  color: #0d1627 !important;
}
div[data-testid="stTextInput"] input::placeholder,
div[data-testid="stTextArea"] textarea::placeholder,
div[data-testid="stDateInput"] input::placeholder,
div[data-testid="stTimeInput"] input::placeholder{
  color: rgba(13,22,39,0.55) !important;
}

/* Selectbox / Combobox: dropdown e itens legíveis ("-- Novo --", pacientes, calendário etc.) */
div[data-baseweb="select"] > div{
  background: rgba(255,255,255,0.95) !important;
  color: #0d1627 !important;
}
div[data-baseweb="select"] span,
div[data-baseweb="select"] input{
  color: #0d1627 !important;
}
div[data-baseweb="select"] svg{
  fill: #0d1627 !important;
}

/* Popovers (lista do select e calendário do date_input) */
div[data-baseweb="popover"]{
  z-index: 100000 !important;
}
div[data-baseweb="popover"] [role="listbox"],
div[data-baseweb="popover"] ul{
  background: rgba(255,255,255,0.98) !important;
}
div[data-baseweb="popover"] [role="option"],
div[data-baseweb="popover"] li{
  background: transparent !important;
  color: #0d1627 !important;
}
div[data-baseweb="popover"] [role="option"]:hover,
div[data-baseweb="popover"] li:hover{
  background: rgba(46,125,50,0.12) !important;
}

/* Calendário: dias e cabeçalho */
div[data-baseweb="popover"] [role="dialog"],
div[data-baseweb="popover"] [aria-label="calendar"],
div[data-baseweb="popover"] [data-baseweb="calendar"]{
  background: rgba(255,255,255,0.98) !important;
  color: #0d1627 !important;
}

/* Evita que qualquer regra global de cor deixe itens do popover invisíveis */
div[data-baseweb="popover"] *{
  color: #0d1627 !important;
}

/* ================= End fixes ================= */
/* ================= Readability boost (app interno) ================= */
/* Texto geral do conteudo principal sempre claro no fundo escuro */
[data-testid="stAppViewContainer"] .main .block-container,
[data-testid="stAppViewContainer"] .main .block-container p,
[data-testid="stAppViewContainer"] .main .block-container li,
[data-testid="stAppViewContainer"] .main .block-container span,
[data-testid="stAppViewContainer"] .main .block-container label,
[data-testid="stAppViewContainer"] .main .block-container div,
[data-testid="stAppViewContainer"] .main .block-container small{
  color: rgba(236, 245, 255, 0.96) !important;
}

/* Titulos com contraste forte */
[data-testid="stAppViewContainer"] .main .block-container h1,
[data-testid="stAppViewContainer"] .main .block-container h2,
[data-testid="stAppViewContainer"] .main .block-container h3,
[data-testid="stAppViewContainer"] .main .block-container h4,
[data-testid="stAppViewContainer"] .main .block-container h5{
  color: #f7fbff !important;
  text-shadow: 0 1px 6px rgba(0,0,0,0.28);
}

/* Caption e ajuda nao podem ficar apagados */
[data-testid="stAppViewContainer"] .main .stCaption,
[data-testid="stAppViewContainer"] .main .stCaption p{
  color: rgba(220, 234, 246, 0.90) !important;
}

/* Tabelas (inclusive markdown table) */
[data-testid="stAppViewContainer"] .main table{
  background: rgba(8, 22, 40, 0.42) !important;
  border: 1px solid rgba(150, 193, 235, 0.20) !important;
}
[data-testid="stAppViewContainer"] .main table th{
  color: #eaf4ff !important;
  background: rgba(15, 35, 60, 0.52) !important;
  border-color: rgba(150, 193, 235, 0.18) !important;
}
[data-testid="stAppViewContainer"] .main table td{
  color: rgba(232, 243, 255, 0.95) !important;
  border-color: rgba(150, 193, 235, 0.14) !important;
}

/* Links mais visiveis */
[data-testid="stAppViewContainer"] .main a{
  color: #8dd3ff !important;
}
[data-testid="stAppViewContainer"] .main a:hover{
  color: #b6e5ff !important;
}

        /* Premium card */
        .dh-premium-card{
          background: linear-gradient(160deg, rgba(9,24,44,0.97) 0%, rgba(11,43,72,0.94) 46%, rgba(16,92,84,0.90) 100%);
          border: 1px solid rgba(128,255,225,0.30);
          border-radius: 18px;
          padding: 20px;
          min-height: 560px;
          box-shadow: 0 24px 48px rgba(0,0,0,0.32);
          backdrop-filter: blur(8px);
        }
        .dh-premium-title{
          font-size: 0.95rem;
          font-weight: 900;
          letter-spacing: 2.4px;
          color: #9ff7de;
          text-transform: uppercase;
        }
        .dh-badge{
          font-size: 0.78rem;
          font-weight: 900;
          letter-spacing: 0.2px;
          color: #08211c;
          background: linear-gradient(90deg, #e7ff9a, #b9ff6f);
          padding: 6px 10px;
          border-radius: 999px;
          box-shadow: 0 8px 20px rgba(6,14,22,0.35);
          border: 1px solid rgba(255,255,255,0.35);
          white-space: nowrap;
        }
        .dh-premium-desc{
          color: #d9fff2;
          font-weight: 600;
          line-height: 1.5;
          margin-top: 8px;
        }
        .dh-premium-card .dh-price{
          margin-top: 6px;
          font-size: 3rem;
          font-weight: 900;
          color: #f2fff9 !important;
          line-height: 1.04;
          text-shadow: 0 8px 24px rgba(0,0,0,0.30);
        }
        .dh-premium-card .dh-price span{
          font-size: 1.05rem !important;
          color: #bfffe8 !important;
          font-weight: 700;
        }
        .dh-premium-card .dh-features{
          background: linear-gradient(180deg, rgba(5,16,31,0.45), rgba(5,16,31,0.30));
          border: 1px solid rgba(156,255,228,0.20);
          border-radius: 12px;
          padding: 10px 12px;
          margin-top: 12px;
        }
        .dh-premium-card .dh-feature{
          display:flex;
          gap:10px;
          align-items:flex-start;
          padding: 6px 2px;
          border-bottom: 1px solid rgba(186,255,236,0.14);
          font-weight: 700;
          color: #f5fffb !important;
        }
        .dh-premium-card .dh-feature:last-child{ border-bottom:none; }

        .dh-pay-card{
          margin-top: 12px;
          background: linear-gradient(180deg, rgba(3,11,24,0.64), rgba(3,11,24,0.54));
          border: 1px solid rgba(160,255,230,0.18);
          border-radius: 14px;
          padding: 12px;
          box-shadow: 0 12px 30px rgba(0,0,0,0.24);
        }
        .dh-pay-title{
          font-weight: 800;
          color: #caffed;
          margin-bottom: 8px;
        }
        .dh-login-card{
          margin-top: 16px;
          background: linear-gradient(180deg, rgba(8,14,28,0.95), rgba(8,14,28,0.88));
          border: 1px solid rgba(255,255,255,0.10);
          border-radius: 16px;
          padding: 16px;
          box-shadow: 0 18px 45px rgba(0,0,0,0.35);
        }

        .dh-cta-row{
          display: flex;
          gap: 10px;
          margin-top: 10px;
        }
        .dh-cta{
          width: 100%;
          display: inline-block;
          text-decoration: none !important;
        }
        .dh-btn{
          width: 100%;
          border: 1px solid rgba(0,0,0,0.08);
          border-radius: 12px;
          padding: 10px 12px;
          font-weight: 800;
          cursor: pointer;
          box-shadow: 0 10px 20px rgba(0,0,0,0.12);
          transition: transform 0.08s ease, box-shadow 0.08s ease;
        }
        .dh-btn:hover{
          transform: translateY(-1px);
          box-shadow: 0 14px 26px rgba(0,0,0,0.16);
        }
        .dh-btn-blue{ background: linear-gradient(90deg, #2962FF, #1565C0); color: #fff; }
        .dh-btn-green{ background: linear-gradient(90deg, #25D366, #128C7E); color: #fff; }
        .dh-btn-dark{ background: linear-gradient(90deg, #1b2236, #0f1629); color: #fff; }

        /* Login card */
        div[data-testid="column"]:has(.login-box-note) .stMarkdown,
        div[data-testid="column"]:has(.login-box-note) .stCaption,
        div[data-testid="column"]:has(.login-box-note) .stAlert,
        div[data-testid="column"]:has(.login-box-note) div[data-testid="stForm"]{
          max-width: 230px;
          width: 230px !important;
          margin-left: auto;
          margin-right: auto;
        }
        div[data-testid="column"]:has(.login-box-note) div[data-testid="stForm"]{
          background: linear-gradient(180deg, rgba(240, 248, 255, 0.96) 0%, rgba(225, 242, 236, 0.96) 100%);
          border: 1px solid rgba(116, 160, 236, 0.22);
          border-radius: 18px;
          padding: 8px 8px 6px 8px !important;
          box-shadow: 0 18px 34px rgba(7,17,34,0.22);
          backdrop-filter: blur(12px);
        }
        div[data-testid="column"]:has(.login-box-note) div[data-testid="stForm"] form{
          gap: 0.18rem !important;
        }
        div[data-testid="column"]:has(.login-box-note) div[data-testid="stForm"] .stTextInput,
        div[data-testid="column"]:has(.login-box-note) div[data-testid="stForm"] .stTextInput > div,
        div[data-testid="column"]:has(.login-box-note) div[data-testid="stForm"] .stTextInput > div > div,
        div[data-testid="column"]:has(.login-box-note) div[data-testid="stForm"] .stTextInput input,
        div[data-testid="column"]:has(.login-box-note) div[data-testid="stForm"] .stButton,
        div[data-testid="column"]:has(.login-box-note) div[data-testid="stForm"] .stButton > button{
          width: 100% !important;
          max-width: 100% !important;
        }
        div[data-testid="column"]:has(.login-box-note) div[data-testid="stForm"] label{
          margin-bottom: 0.1rem !important;
        }
        div[data-testid="column"]:has(.login-box-note) h3{
          margin-bottom: 2px !important;
          color: #f6fbff !important;
        }
        div[data-testid="column"]:has(.login-box-note) p{
          color: rgba(232, 242, 255, 0.9) !important;
        }
        .login-box-note{
          margin: 8px 0 10px 0;
          padding: 8px 10px;
          border-radius: 12px;
          background: linear-gradient(90deg, rgba(8, 48, 94, 0.96), rgba(7, 87, 92, 0.94));
          border: 1px solid rgba(88, 181, 255, 0.42);
          color: #ffffff;
          text-shadow: 0 1px 0 rgba(0,0,0,0.35);
          font-size: 0.95rem;
          font-weight: 800;
          line-height: 1.35;
        }
        @media (max-width: 900px){
          div[data-testid="column"]:has(.login-box-note) .stMarkdown,
          div[data-testid="column"]:has(.login-box-note) .stCaption,
          div[data-testid="column"]:has(.login-box-note) .stAlert,
          div[data-testid="column"]:has(.login-box-note) div[data-testid="stForm"]{
            max-width: 100%;
            width: 100% !important;
          }
        }

        /* ===== DietHealth global design system override (final) ===== */
        :root{
          --dh-title: #F1F5F9;
          --dh-text: #CBD5E1;
          --dh-text-2: #94A3B8;
          --dh-accent: #22C55E;
          --dh-surface: rgba(15,23,42,0.85);
          --dh-input-bg: rgba(2,6,23,0.6);
          --dh-input-border: rgba(255,255,255,0.08);
          --dh-danger: #ef4444;
          --dh-warning: #f59e0b;
          --dh-info: #38bdf8;
          --dh-radius-sm: 12px;
          --dh-radius-md: 16px;
          --dh-radius-lg: 20px;
          --dh-shadow-soft: 0 12px 28px rgba(2,6,23,0.14);
          --dh-shadow-card: 0 18px 34px rgba(2,6,23,0.18);
          --dh-surface-1: linear-gradient(180deg, rgba(15,23,42,0.78), rgba(10,16,30,0.72));
          --dh-surface-2: linear-gradient(180deg, rgba(255,255,255,0.06), rgba(255,255,255,0.03));
          --dh-border-soft: rgba(148,163,184,0.16);
          --dh-font-sm: clamp(0.96rem, 0.9rem + 0.2vw, 1.02rem);
          --dh-font-md: clamp(1.02rem, 0.96rem + 0.34vw, 1.12rem);
          --dh-font-label: clamp(0.95rem, 0.9rem + 0.2vw, 1rem);
          --dh-font-xl: clamp(1.5rem, 1.12rem + 1.08vw, 2.08rem);
        }

        [data-testid="stAppViewContainer"] .main .block-container *{
          opacity: 1 !important;
        }
        [data-testid="stAppViewContainer"] .main .block-container > div{
          border-radius: var(--dh-radius-md);
        }
        [data-testid="stHeading"] h1,
        [data-testid="stHeading"] h2,
        [data-testid="stHeading"] h3,
        [data-testid="stHeading"] h4,
        [data-testid="stAppViewContainer"] .main .block-container h1,
        [data-testid="stAppViewContainer"] .main .block-container h2,
        [data-testid="stAppViewContainer"] .main .block-container h3,
        [data-testid="stAppViewContainer"] .main .block-container h4{
          color: var(--dh-title) !important;
          font-weight: 600 !important;
          text-shadow: 0 1px 8px rgba(0,0,0,0.30) !important;
        }
        [data-testid="stAppViewContainer"] .main .block-container p,
        [data-testid="stAppViewContainer"] .main .block-container li,
        [data-testid="stAppViewContainer"] .main .block-container td,
        [data-testid="stAppViewContainer"] .main .block-container th,
        [data-testid="stAppViewContainer"] .main .block-container span,
        [data-testid="stAppViewContainer"] .main .stMarkdown,
        [data-testid="stAppViewContainer"] .main [data-testid="stCaptionContainer"],
        [data-testid="stAppViewContainer"] .main small{
          color: var(--dh-text) !important;
        }
        [data-testid="stAppViewContainer"] .main .stCaption,
        [data-testid="stAppViewContainer"] .main [data-testid="stCaptionContainer"] *,
        [data-testid="stAppViewContainer"] .main .secondary-text,
        [data-testid="stAppViewContainer"] .main .muted{
          color: var(--dh-text-2) !important;
        }
        [data-testid="stAppViewContainer"] .main [data-testid="stMarkdownContainer"] > p + p{
          margin-top: 0.68rem !important;
        }
        [data-testid="stAppViewContainer"] .main a,
        [data-testid="stAppViewContainer"] .main .stLinkButton a,
        [data-testid="stTabs"] button[role="tab"][aria-selected="true"]{
          color: var(--dh-accent) !important;
        }
        [data-testid="stTabs"] button[role="tab"]{
          color: var(--dh-text) !important;
          font-weight: 600 !important;
        }

        [data-testid="stAppViewContainer"] .main label,
        [data-testid="stAppViewContainer"] .main .stTextInput label,
        [data-testid="stAppViewContainer"] .main .stNumberInput label,
        [data-testid="stAppViewContainer"] .main .stDateInput label,
        [data-testid="stAppViewContainer"] .main .stTimeInput label,
        [data-testid="stAppViewContainer"] .main .stSelectbox label,
        [data-testid="stAppViewContainer"] .main .stMultiSelect label,
        [data-testid="stAppViewContainer"] .main .stTextArea label{
          color: var(--dh-text-2) !important;
          font-weight: 500 !important;
        }

        [data-testid="stAppViewContainer"] .main .stTextInput > div,
        [data-testid="stAppViewContainer"] .main .stNumberInput > div,
        [data-testid="stAppViewContainer"] .main .stDateInput > div,
        [data-testid="stAppViewContainer"] .main .stTimeInput > div,
        [data-testid="stAppViewContainer"] .main .stTextArea > div,
        [data-testid="stAppViewContainer"] .main .stSelectbox > div,
        [data-testid="stAppViewContainer"] .main .stMultiSelect > div{
          border-radius: var(--dh-radius-md) !important;
        }
        [data-testid="stAppViewContainer"] .main .stTextInput input,
        [data-testid="stAppViewContainer"] .main .stNumberInput input,
        [data-testid="stAppViewContainer"] .main .stDateInput input,
        [data-testid="stAppViewContainer"] .main .stTimeInput input,
        [data-testid="stAppViewContainer"] .main .stTextArea textarea,
        [data-testid="stAppViewContainer"] .main .stSelectbox [data-baseweb="select"] > div{
          min-height: 42px !important;
          border-radius: var(--dh-radius-md) !important;
          border: 1px solid var(--dh-input-border) !important;
          background: linear-gradient(180deg, rgba(10,18,34,0.82), rgba(7,14,28,0.78)) !important;
          color: var(--dh-title) !important;
          padding-left: 12px !important;
          padding-right: 12px !important;
          box-shadow: inset 0 1px 0 rgba(255,255,255,0.03), var(--dh-shadow-soft) !important;
        }
        [data-testid="stAppViewContainer"] .main .stTextInput input::placeholder,
        [data-testid="stAppViewContainer"] .main .stNumberInput input::placeholder,
        [data-testid="stAppViewContainer"] .main .stTextArea textarea::placeholder{
          color: var(--dh-text-2) !important;
          opacity: 0.95 !important;
        }
        [data-testid="stAppViewContainer"] .main .stTextInput input:focus,
        [data-testid="stAppViewContainer"] .main .stNumberInput input:focus,
        [data-testid="stAppViewContainer"] .main .stDateInput input:focus,
        [data-testid="stAppViewContainer"] .main .stTimeInput input:focus,
        [data-testid="stAppViewContainer"] .main .stTextArea textarea:focus,
        [data-testid="stAppViewContainer"] .main .stSelectbox [data-baseweb="select"] > div:focus-within{
          border-color: var(--dh-accent) !important;
          box-shadow: 0 0 0 2px rgba(34,197,94,0.15), var(--dh-shadow-soft) !important;
        }

        [data-testid="stAppViewContainer"] .main .stButton > button,
        [data-testid="stAppViewContainer"] .main [data-testid="stFormSubmitButton"] > button,
        [data-testid="stAppViewContainer"] .main .stDownloadButton > button{
          min-height: 46px !important;
          border-radius: 14px !important;
          border: 1px solid rgba(34,197,94,0.2) !important;
          background: linear-gradient(135deg,#22C55E,#16A34A) !important;
          color: #ffffff !important;
          font-weight: 700 !important;
          box-shadow: 0 14px 24px rgba(22,163,74,0.18) !important;
          transition: transform .18s ease, box-shadow .18s ease, filter .18s ease !important;
        }
        [data-testid="stAppViewContainer"] .main .stButton > button:hover,
        [data-testid="stAppViewContainer"] .main [data-testid="stFormSubmitButton"] > button:hover,
        [data-testid="stAppViewContainer"] .main .stDownloadButton > button:hover{
          transform: translateY(-1px) !important;
          filter: brightness(1.02) !important;
          box-shadow: 0 16px 28px rgba(34,197,94,0.22) !important;
        }
        [data-testid="stAppViewContainer"] .main [data-testid="stFormSubmitButton"] > button:disabled{
          opacity: 0.95 !important;
          color: #ffffff !important;
          filter: saturate(0.95) !important;
        }
        [data-testid="stAppViewContainer"] .main .stLinkButton > a{
          min-height: 46px !important;
          border-radius: 14px !important;
          border: 1px solid var(--dh-border-soft) !important;
          background: linear-gradient(180deg, rgba(255,255,255,0.06), rgba(255,255,255,0.03)) !important;
          color: var(--dh-title) !important;
          font-weight: 700 !important;
          box-shadow: var(--dh-shadow-soft) !important;
        }
        [data-testid="stAppViewContainer"] .main .stLinkButton > a:hover{
          border-color: rgba(96,165,250,0.28) !important;
          color: #f8fbff !important;
        }

        /* ===== Readability and responsiveness hardening ===== */
        [data-testid="stAppViewContainer"] .main .block-container{
          max-width: 1240px;
          width: 100%;
          font-size: var(--dh-font-sm);
          line-height: 1.68;
          padding-left: clamp(0.9rem, 1.2vw, 1.5rem) !important;
          padding-right: clamp(0.9rem, 1.2vw, 1.5rem) !important;
        }
        [data-testid="stAppViewContainer"] .main .block-container h1,
        [data-testid="stAppViewContainer"] .main .block-container h2,
        [data-testid="stAppViewContainer"] .main .block-container h3,
        [data-testid="stAppViewContainer"] .main .block-container h4{
          font-weight: 720 !important;
          line-height: 1.12 !important;
          letter-spacing: -0.02em !important;
          text-wrap: balance;
          overflow-wrap: anywhere;
        }
        [data-testid="stAppViewContainer"] .main .block-container h1{font-size:var(--dh-font-xl) !important;}
        [data-testid="stAppViewContainer"] .main .block-container h2{font-size:clamp(1.38rem,1.06rem + .92vw,1.86rem) !important;}
        [data-testid="stAppViewContainer"] .main .block-container h3{font-size:clamp(1.12rem,.98rem + .58vw,1.42rem) !important;}
        [data-testid="stAppViewContainer"] .main .block-container h4{font-size:clamp(1rem,.94rem + .34vw,1.18rem) !important;}
        [data-testid="stAppViewContainer"] .main .block-container p,
        [data-testid="stAppViewContainer"] .main .block-container li{
          font-size: var(--dh-font-sm) !important;
          line-height: 1.72 !important;
          overflow-wrap: break-word;
          word-break: normal;
          hyphens: auto;
        }
        [data-testid="stAppViewContainer"] .main .block-container ul,
        [data-testid="stAppViewContainer"] .main .block-container ol{
          padding-left: 1.1rem !important;
        }
        [data-testid="stAppViewContainer"] .main .block-container hr{
          margin: 1.1rem 0 1.2rem !important;
        }
        [data-testid="stAppViewContainer"] .main div[data-testid="column"]{
          min-width: 0 !important;
        }
        [data-testid="stAppViewContainer"] .main .block-container strong,
        [data-testid="stAppViewContainer"] .main .block-container b{
          color: var(--dh-title) !important;
          font-weight: 760 !important;
        }
        [data-testid="stTabs"]{
          gap: 8px !important;
          margin-bottom: 0.25rem !important;
        }
        [data-testid="stTabs"] [role="tablist"]{
          gap: 0.45rem !important;
          padding: 0.18rem 0 0.25rem !important;
        }
        [data-testid="stTabs"] button[role="tab"]{
          min-height: 48px !important;
          padding: 0.62rem 0.95rem !important;
          border-radius: 14px !important;
          border: 1px solid rgba(148,163,184,0.12) !important;
          background: linear-gradient(180deg, rgba(255,255,255,0.05), rgba(255,255,255,0.025)) !important;
          font-size: clamp(0.95rem, 0.9rem + 0.18vw, 1rem) !important;
          white-space: normal !important;
          line-height: 1.25 !important;
          font-weight: 700 !important;
          box-shadow: none !important;
        }
        [data-testid="stTabs"] button[role="tab"][aria-selected="true"]{
          font-weight: 800 !important;
          text-shadow: none !important;
          border-color: rgba(34,197,94,0.26) !important;
          background: linear-gradient(180deg, rgba(34,197,94,0.16), rgba(21,128,61,0.12)) !important;
          box-shadow: 0 10px 18px rgba(2,6,23,0.1) !important;
        }
        [data-testid="stAppViewContainer"] .main label,
        [data-testid="stAppViewContainer"] .main .stTextInput label,
        [data-testid="stAppViewContainer"] .main .stNumberInput label,
        [data-testid="stAppViewContainer"] .main .stDateInput label,
        [data-testid="stAppViewContainer"] .main .stTimeInput label,
        [data-testid="stAppViewContainer"] .main .stSelectbox label,
        [data-testid="stAppViewContainer"] .main .stMultiSelect label,
        [data-testid="stAppViewContainer"] .main .stTextArea label{
          color: var(--dh-text) !important;
          font-weight: 700 !important;
          font-size: var(--dh-font-label) !important;
          line-height: 1.35 !important;
        }
        [data-testid="stAppViewContainer"] .main .stTextInput input,
        [data-testid="stAppViewContainer"] .main .stNumberInput input,
        [data-testid="stAppViewContainer"] .main .stDateInput input,
        [data-testid="stAppViewContainer"] .main .stTimeInput input,
        [data-testid="stAppViewContainer"] .main .stTextArea textarea,
        [data-testid="stAppViewContainer"] .main .stSelectbox [data-baseweb="select"] > div{
          font-size: 1rem !important;
          line-height: 1.5 !important;
          min-height: 46px !important;
        }
        [data-testid="stAppViewContainer"] .main .stTextArea textarea{
          min-height: 132px !important;
          padding-top: 0.72rem !important;
          padding-bottom: 0.72rem !important;
        }
        [data-testid="stAppViewContainer"] .main .stTextInput input::placeholder,
        [data-testid="stAppViewContainer"] .main .stNumberInput input::placeholder,
        [data-testid="stAppViewContainer"] .main .stTextArea textarea::placeholder{
          color: rgba(186, 201, 220, 0.94) !important;
        }
        [data-testid="stAppViewContainer"] .main [data-testid="stAlertContainer"] p,
        [data-testid="stAppViewContainer"] .main [data-testid="stAlertContainer"] div{
          color: inherit !important;
        }
        [data-testid="stAppViewContainer"] .main [data-testid="stAlertContainer"]{
          border-radius: var(--dh-radius-md) !important;
          overflow: hidden !important;
        }
        [data-testid="stAppViewContainer"] .main [data-testid="stAlertContainer"] > div{
          border-radius: var(--dh-radius-md) !important;
          border: 1px solid rgba(148,163,184,0.14) !important;
          box-shadow: var(--dh-shadow-soft) !important;
        }
        [data-testid="stAppViewContainer"] .main [data-testid="stTable"],
        [data-testid="stAppViewContainer"] .main [data-testid="stDataFrame"]{
          border-radius: var(--dh-radius-lg) !important;
          overflow: hidden !important;
          border: 1px solid rgba(148,163,184,0.14) !important;
          background: var(--dh-surface-1) !important;
          box-shadow: var(--dh-shadow-card) !important;
        }
        [data-testid="stAppViewContainer"] .main table{
          font-size: 0.95rem !important;
          line-height: 1.5 !important;
        }
        [data-testid="stAppViewContainer"] .main thead tr th{
          color: var(--dh-title) !important;
          font-weight: 800 !important;
          white-space: normal !important;
          background: rgba(15,23,42,0.58) !important;
        }
        [data-testid="stAppViewContainer"] .main tbody tr td{
          color: var(--dh-text) !important;
          vertical-align: top !important;
          white-space: normal !important;
        }
        [data-testid="stAppViewContainer"] .main [data-testid="metric-container"]{
          border-radius: var(--dh-radius-lg) !important;
          border: 1px solid rgba(148,163,184,0.14) !important;
          background: var(--dh-surface-2) !important;
          box-shadow: var(--dh-shadow-soft) !important;
          padding: 0.95rem 1rem !important;
        }
        [data-testid="stAppViewContainer"] .main [data-testid="stMetricValue"]{
          color: var(--dh-title) !important;
          font-size: clamp(1.3rem, 1rem + 0.95vw, 1.95rem) !important;
          line-height: 1.08 !important;
        }
        [data-testid="stAppViewContainer"] .main [data-testid="stMetricLabel"]{
          color: var(--dh-text) !important;
          font-weight: 700 !important;
          line-height: 1.35 !important;
        }
        [data-testid="stAppViewContainer"] .main details{
          border-radius: var(--dh-radius-lg) !important;
          border: 1px solid rgba(148,163,184,0.14) !important;
          background: var(--dh-surface-2) !important;
          box-shadow: var(--dh-shadow-soft) !important;
          overflow: hidden !important;
        }
        [data-testid="stAppViewContainer"] .main summary{
          padding: 0.9rem 1rem !important;
          font-weight: 700 !important;
          color: var(--dh-title) !important;
        }
        .dh-admin-empty,
        .dh-agenda-empty,
        .dh-library-empty,
        .dh-fin-empty,
        .dh-chart-empty,
        .dh-support-empty,
        .dh-patient-empty{
          border-radius: var(--dh-radius-lg) !important;
          border: 1px dashed rgba(148,163,184,0.18) !important;
          background: linear-gradient(180deg, rgba(15,23,42,0.54), rgba(10,16,30,0.48)) !important;
          box-shadow: var(--dh-shadow-soft) !important;
          padding: 1.05rem 1.1rem !important;
        }

        .dh-portal-shell{
          margin: 8px 0 18px;
          padding: 22px;
          border-radius: 24px;
          border: 1px solid rgba(96,165,250,0.16);
          background: linear-gradient(145deg, rgba(9,20,37,0.98), rgba(13,31,57,0.96));
          box-shadow: 0 24px 48px rgba(2,6,23,0.28);
        }
        .dh-portal-head{
          display:flex;
          justify-content:space-between;
          align-items:flex-start;
          gap:16px;
          flex-wrap:wrap;
          margin-bottom:18px;
        }
        .dh-portal-kicker{
          display:inline-flex;
          align-items:center;
          gap:8px;
          padding:8px 12px;
          border-radius:999px;
          background:rgba(34,197,94,0.12);
          border:1px solid rgba(34,197,94,0.24);
          color:#d9ffed;
          font-size:.8rem;
          font-weight:800;
          letter-spacing:.03em;
          text-transform:uppercase;
        }
        .dh-portal-title{
          margin:10px 0 0;
          color:#f8fbff;
          font-size:clamp(1.25rem, 1rem + 0.8vw, 1.85rem);
          font-weight:850;
          line-height:1.08;
        }
        .dh-portal-subtitle{
          margin:10px 0 0;
          color:#c7d7e7;
          max-width:860px;
          line-height:1.65;
          font-size:clamp(.95rem,.88rem + .24vw,1.02rem);
        }
        .dh-portal-status{
          display:inline-flex;
          align-items:center;
          gap:8px;
          padding:10px 14px;
          border-radius:999px;
          border:1px solid rgba(148,163,184,0.28);
          font-weight:800;
          font-size:.92rem;
        }
        .dh-status-active{background:rgba(34,197,94,0.16);color:#d6ffe7;border-color:rgba(34,197,94,0.32);}
        .dh-status-pending{background:rgba(245,158,11,0.16);color:#ffe9bc;border-color:rgba(245,158,11,0.34);}
        .dh-status-inactive{background:rgba(56,189,248,0.14);color:#d9f6ff;border-color:rgba(56,189,248,0.28);}
        .dh-status-blocked{background:rgba(239,68,68,0.15);color:#ffd6d6;border-color:rgba(239,68,68,0.3);}
        .dh-portal-grid{
          display:grid;
          grid-template-columns:repeat(4,minmax(0,1fr));
          gap:14px;
          margin:16px 0 18px;
        }
        .dh-portal-stat{
          min-height:118px;
          padding:16px 16px 18px;
          border-radius:18px;
          border:1px solid rgba(226,232,240,0.08);
          background:linear-gradient(180deg, rgba(15,23,42,0.9), rgba(10,16,30,0.82));
        }
        .dh-portal-stat-label{
          color:#9fb4c9;
          font-size:.78rem;
          font-weight:800;
          text-transform:uppercase;
          letter-spacing:.05em;
        }
        .dh-portal-stat-value{
          margin-top:10px;
          color:#f8fbff;
          font-size:clamp(1rem,.92rem + .45vw,1.24rem);
          font-weight:840;
          line-height:1.2;
          overflow-wrap:anywhere;
        }
        .dh-portal-stat-note{
          margin-top:8px;
          color:#b9cada;
          font-size:.88rem;
          line-height:1.5;
        }
        .dh-portal-steps{
          display:grid;
          grid-template-columns:repeat(3,minmax(0,1fr));
          gap:14px;
          margin:10px 0 18px;
        }
        .dh-portal-step{
          padding:16px 16px 18px;
          border-radius:18px;
          background:rgba(255,255,255,0.04);
          border:1px solid rgba(148,163,184,0.16);
        }
        .dh-portal-step-index{
          display:inline-flex;
          width:28px;
          height:28px;
          align-items:center;
          justify-content:center;
          border-radius:999px;
          background:rgba(34,197,94,0.14);
          color:#dbffea;
          font-weight:900;
          margin-bottom:10px;
        }
        .dh-portal-step h4{
          margin:0 0 6px;
          color:#f8fbff;
          font-size:1rem;
          font-weight:780;
        }
        .dh-portal-step p{
          margin:0;
          color:#c5d4e2;
          line-height:1.58;
        }
        .dh-portal-help{
          padding:16px 18px;
          border-radius:18px;
          background:linear-gradient(180deg, rgba(11,31,51,0.9), rgba(8,22,39,0.86));
          border:1px solid rgba(96,165,250,0.16);
          margin-bottom:16px;
        }
        .dh-portal-help strong{display:block;margin-bottom:6px;}
        .dh-portal-help p{margin:0;color:#d3e1ec;}

        @media (prefers-color-scheme: light){
          .dh-portal-shell{
            background: linear-gradient(145deg, rgba(255,255,255,0.98), rgba(239,246,255,0.96));
            border-color: rgba(37,99,235,0.12);
            box-shadow: 0 18px 34px rgba(15,23,42,0.1);
          }
          .dh-portal-kicker{color:#166534;background:rgba(34,197,94,0.12);}
          .dh-portal-title,.dh-portal-stat-value,.dh-portal-step h4{color:#0f172a;}
          .dh-portal-subtitle,.dh-portal-step p,.dh-portal-stat-note,.dh-portal-help p{color:#334155;}
          .dh-portal-stat,.dh-portal-step,.dh-portal-help{
            background: rgba(255,255,255,0.82);
            border-color: rgba(148,163,184,0.2);
          }
          .dh-portal-stat-label{color:#64748b;}
        }
        @media (max-width: 1024px){
          .dh-portal-grid{grid-template-columns:repeat(2,minmax(0,1fr));}
          .dh-portal-steps{grid-template-columns:1fr;}
        }
        @media (max-width: 768px){
          [data-testid="stAppViewContainer"] .main .block-container{
            max-width: 100%;
            padding-left: 0.82rem !important;
            padding-right: 0.82rem !important;
            line-height: 1.72;
          }
          [data-testid="stAppViewContainer"] .main .block-container h1{
            font-size: clamp(1.44rem, 1.2rem + 1vw, 1.82rem) !important;
          }
          [data-testid="stAppViewContainer"] .main .block-container h2{
            font-size: clamp(1.24rem, 1.08rem + .85vw, 1.56rem) !important;
          }
          [data-testid="stAppViewContainer"] .main .block-container h3{
            font-size: clamp(1.08rem, 1rem + .52vw, 1.28rem) !important;
          }
          [data-testid="stAppViewContainer"] .main .block-container p,
          [data-testid="stAppViewContainer"] .main .block-container li{
            line-height: 1.76 !important;
          }
          [data-testid="stTabs"] button[role="tab"]{
            min-height: 52px !important;
            padding: 0.72rem 0.88rem !important;
            font-size: 0.96rem !important;
          }
          [data-testid="stAppViewContainer"] .main .stTextInput input,
          [data-testid="stAppViewContainer"] .main .stNumberInput input,
          [data-testid="stAppViewContainer"] .main .stDateInput input,
          [data-testid="stAppViewContainer"] .main .stTimeInput input,
          [data-testid="stAppViewContainer"] .main .stTextArea textarea,
          [data-testid="stAppViewContainer"] .main .stSelectbox [data-baseweb="select"] > div{
            font-size: 16px !important;
            min-height: 48px !important;
          }
          [data-testid="stAppViewContainer"] .main label,
          [data-testid="stAppViewContainer"] .main .stTextInput label,
          [data-testid="stAppViewContainer"] .main .stNumberInput label,
          [data-testid="stAppViewContainer"] .main .stDateInput label,
          [data-testid="stAppViewContainer"] .main .stTimeInput label,
          [data-testid="stAppViewContainer"] .main .stSelectbox label,
          [data-testid="stAppViewContainer"] .main .stMultiSelect label,
          [data-testid="stAppViewContainer"] .main .stTextArea label{
            font-size: 0.98rem !important;
          }
          [data-testid="stAppViewContainer"] .main [data-testid="stMetricValue"]{
            font-size: clamp(1.2rem, 1.06rem + .7vw, 1.52rem) !important;
          }
          .dh-portal-shell{padding:18px 16px;}
          .dh-portal-grid{grid-template-columns:1fr;}
        }

        /* Login/Cadastro shell (compact SaaS) */
        div[data-testid="stPopover"] [class*="st-key-lp_login_pop_body"],
        div[data-testid="stPopover"] [class*="st-key-lp_register_pop_body"]{
          width: min(95vw, 420px) !important;
          max-width: 420px !important;
          margin: 0 auto !important;
        }
        div[data-testid="stPopover"] [class*="st-key-lp_login_pop_shell"],
        div[data-testid="stPopover"] [class*="st-key-lp_register_pop_shell"],
        div[data-testid="stPopover"] [class*="st-key-lp_login_pop_body"],
        div[data-testid="stPopover"] [class*="st-key-lp_register_pop_body"],
        div[data-testid="column"]:has(.login-box-note) div[data-testid="stForm"]{
          background: var(--dh-surface) !important;
          backdrop-filter: blur(8px) !important;
          border-radius: 14px !important;
          padding: 28px !important;
          border: 1px solid rgba(255,255,255,0.05) !important;
          box-shadow: 0 20px 40px rgba(0,0,0,0.35) !important;
        }
        div[data-testid="stPopover"] [class*="st-key-lp_login_pop_shell"] h1,
        div[data-testid="stPopover"] [class*="st-key-lp_login_pop_shell"] h2,
        div[data-testid="stPopover"] [class*="st-key-lp_login_pop_shell"] h3,
        div[data-testid="stPopover"] [class*="st-key-lp_register_pop_shell"] h1,
        div[data-testid="stPopover"] [class*="st-key-lp_register_pop_shell"] h2,
        div[data-testid="stPopover"] [class*="st-key-lp_register_pop_shell"] h3{
          color: var(--dh-title) !important;
          font-weight: 600 !important;
        }
        div[data-testid="stPopover"] [class*="st-key-lp_login_pop_shell"] p,
        div[data-testid="stPopover"] [class*="st-key-lp_login_pop_shell"] span,
        div[data-testid="stPopover"] [class*="st-key-lp_register_pop_shell"] p,
        div[data-testid="stPopover"] [class*="st-key-lp_register_pop_shell"] span,
        div[data-testid="stPopover"] [class*="st-key-lp_login_pop_body"] label,
        div[data-testid="stPopover"] [class*="st-key-lp_register_pop_body"] label{
          color: var(--dh-text) !important;
          text-shadow: none !important;
        }
        div[data-testid="stPopover"] [class*="st-key-lp_login_pop_body"] [data-testid="stVerticalBlock"],
        div[data-testid="stPopover"] [class*="st-key-lp_register_pop_body"] [data-testid="stVerticalBlock"]{
          gap: 14px !important;
        }
        div[data-testid="stPopover"] [class*="st-key-lp_login_pop_body"] .stTextInput input,
        div[data-testid="stPopover"] [class*="st-key-lp_login_pop_body"] .stNumberInput input,
        div[data-testid="stPopover"] [class*="st-key-lp_login_pop_body"] .stTextArea textarea,
        div[data-testid="stPopover"] [class*="st-key-lp_register_pop_body"] .stTextInput input,
        div[data-testid="stPopover"] [class*="st-key-lp_register_pop_body"] .stNumberInput input,
        div[data-testid="stPopover"] [class*="st-key-lp_register_pop_body"] .stTextArea textarea{
          height: 42px !important;
          border-radius: 10px !important;
          border: 1px solid var(--dh-input-border) !important;
          background: var(--dh-input-bg) !important;
          color: var(--dh-title) !important;
          padding: 0 12px !important;
        }
        div[data-testid="stPopover"] [class*="st-key-lp_login_pop_body"] input:focus,
        div[data-testid="stPopover"] [class*="st-key-lp_register_pop_body"] input:focus{
          border-color: var(--dh-accent) !important;
          box-shadow: 0 0 0 2px rgba(34,197,94,0.15) !important;
        }
        div[data-testid="stPopover"] [class*="st-key-lp_login_pop_body"] .stButton > button,
        div[data-testid="stPopover"] [class*="st-key-lp_register_pop_body"] .stButton > button,
        div[data-testid="stPopover"] [class*="st-key-lp_login_pop_body"] [data-testid="stFormSubmitButton"] > button,
        div[data-testid="stPopover"] [class*="st-key-lp_register_pop_body"] [data-testid="stFormSubmitButton"] > button{
          height: 44px !important;
          border-radius: 10px !important;
          background: linear-gradient(135deg,#22C55E,#16A34A) !important;
          color: #ffffff !important;
          font-weight: 600 !important;
          border: none !important;
        }
        .login-box-note{
          background: rgba(34,197,94,0.12) !important;
          border: 1px solid rgba(34,197,94,0.25) !important;
          color: #22C55E !important;
          padding: 8px 14px !important;
          border-radius: 999px !important;
          font-size: 13px !important;
          display: inline-block !important;
          line-height: 1.35 !important;
          font-weight: 600 !important;
          text-shadow: none !important;
        }

        [data-testid="stChatInput"] textarea,
        [data-testid="stChatInput"] input{
          color: #0f2238 !important;
          -webkit-text-fill-color: #0f2238 !important;
          caret-color: #0f2238 !important;
          background: rgba(248,250,252,0.98) !important;
          border: 1px solid rgba(148,163,184,0.26) !important;
        }
        [data-testid="stChatInput"] textarea::placeholder,
        [data-testid="stChatInput"] input::placeholder{
          color: #64748b !important;
          -webkit-text-fill-color: #64748b !important;
        }
        section[data-testid="stSidebar"] [data-testid="stFileUploaderDropzone"]{
          background: rgba(236,244,255,0.95) !important;
          border: 1px solid rgba(84,128,176,0.35) !important;
        }
        section[data-testid="stSidebar"] [data-testid="stFileUploaderDropzone"] *{
          color: #0f2238 !important;
          opacity: 1 !important;
        }

        @media (max-width: 900px){
          div[data-testid="stPopover"] [class*="st-key-lp_login_pop_body"],
          div[data-testid="stPopover"] [class*="st-key-lp_register_pop_body"]{
            max-width: 95% !important;
          }
          div[data-testid="stPopover"] [class*="st-key-lp_login_pop_shell"],
          div[data-testid="stPopover"] [class*="st-key-lp_register_pop_shell"],
          div[data-testid="stPopover"] [class*="st-key-lp_login_pop_body"],
          div[data-testid="stPopover"] [class*="st-key-lp_register_pop_body"]{
            padding: 22px !important;
          }
          div[data-testid="stPopover"] [class*="st-key-lp_login_pop_body"] .stTextInput input,
          div[data-testid="stPopover"] [class*="st-key-lp_login_pop_body"] .stNumberInput input,
          div[data-testid="stPopover"] [class*="st-key-lp_register_pop_body"] .stTextInput input,
          div[data-testid="stPopover"] [class*="st-key-lp_register_pop_body"] .stNumberInput input{
            height: 40px !important;
          }
          div[data-testid="stPopover"] [class*="st-key-lp_login_pop_body"] [data-testid="stFormSubmitButton"] > button,
          div[data-testid="stPopover"] [class*="st-key-lp_register_pop_body"] [data-testid="stFormSubmitButton"] > button{
            height: 42px !important;
          }
        }

        /* ===== Force patch v3 (popover + low contrast legacy rules) ===== */
        /* app marker para confirmar deploy visualmente */
        body::after{
          content: "UI v3 2026-03-10";
          position: fixed;
          right: 8px;
          bottom: 6px;
          z-index: 999999;
          font-size: 10px;
          color: rgba(148,163,184,0.75);
          pointer-events: none;
        }

        /* fallback robusto: alguns builds renderizam popover com data-baseweb */
        div[data-baseweb="popover"] [class*="st-key-lp_login_pop_shell"],
        div[data-baseweb="popover"] [class*="st-key-lp_register_pop_shell"],
        div[data-baseweb="popover"] [class*="st-key-lp_login_pop_body"],
        div[data-baseweb="popover"] [class*="st-key-lp_register_pop_body"],
        div[data-testid="stPopover"] [class*="st-key-lp_login_pop_shell"],
        div[data-testid="stPopover"] [class*="st-key-lp_register_pop_shell"],
        div[data-testid="stPopover"] [class*="st-key-lp_login_pop_body"],
        div[data-testid="stPopover"] [class*="st-key-lp_register_pop_body"]{
          background: rgba(15,23,42,0.92) !important;
          color: #CBD5E1 !important;
          border: 1px solid rgba(255,255,255,0.08) !important;
          border-radius: 14px !important;
          box-shadow: 0 20px 40px rgba(0,0,0,0.35) !important;
          backdrop-filter: blur(8px) !important;
        }

        div[data-baseweb="popover"] [class*="st-key-lp_login_pop_shell"] h1,
        div[data-baseweb="popover"] [class*="st-key-lp_login_pop_shell"] h2,
        div[data-baseweb="popover"] [class*="st-key-lp_login_pop_shell"] h3,
        div[data-baseweb="popover"] [class*="st-key-lp_register_pop_shell"] h1,
        div[data-baseweb="popover"] [class*="st-key-lp_register_pop_shell"] h2,
        div[data-baseweb="popover"] [class*="st-key-lp_register_pop_shell"] h3,
        div[data-baseweb="popover"] [class*="st-key-lp_login_pop_shell"] p,
        div[data-baseweb="popover"] [class*="st-key-lp_register_pop_shell"] p,
        div[data-baseweb="popover"] [class*="st-key-lp_login_pop_body"] label,
        div[data-baseweb="popover"] [class*="st-key-lp_register_pop_body"] label,
        div[data-testid="stPopover"] [class*="st-key-lp_login_pop_shell"] h1,
        div[data-testid="stPopover"] [class*="st-key-lp_login_pop_shell"] h2,
        div[data-testid="stPopover"] [class*="st-key-lp_login_pop_shell"] h3,
        div[data-testid="stPopover"] [class*="st-key-lp_register_pop_shell"] h1,
        div[data-testid="stPopover"] [class*="st-key-lp_register_pop_shell"] h2,
        div[data-testid="stPopover"] [class*="st-key-lp_register_pop_shell"] h3,
        div[data-testid="stPopover"] [class*="st-key-lp_login_pop_shell"] p,
        div[data-testid="stPopover"] [class*="st-key-lp_register_pop_shell"] p,
        div[data-testid="stPopover"] [class*="st-key-lp_login_pop_body"] label,
        div[data-testid="stPopover"] [class*="st-key-lp_register_pop_body"] label{
          color: #F1F5F9 !important;
          text-shadow: none !important;
          opacity: 1 !important;
        }

        /* login/cadastro inputs sempre visíveis */
        div[data-baseweb="popover"] [class*="st-key-lp_login_pop_body"] input,
        div[data-baseweb="popover"] [class*="st-key-lp_register_pop_body"] input,
        div[data-baseweb="popover"] [class*="st-key-lp_login_pop_body"] textarea,
        div[data-baseweb="popover"] [class*="st-key-lp_register_pop_body"] textarea,
        div[data-testid="stPopover"] [class*="st-key-lp_login_pop_body"] input,
        div[data-testid="stPopover"] [class*="st-key-lp_register_pop_body"] input,
        div[data-testid="stPopover"] [class*="st-key-lp_login_pop_body"] textarea,
        div[data-testid="stPopover"] [class*="st-key-lp_register_pop_body"] textarea{
          background: rgba(2,6,23,0.6) !important;
          color: #F1F5F9 !important;
          border: 1px solid rgba(255,255,255,0.08) !important;
        }
        div[data-baseweb="popover"] [class*="st-key-lp_login_pop_body"] input::placeholder,
        div[data-baseweb="popover"] [class*="st-key-lp_register_pop_body"] input::placeholder,
        div[data-testid="stPopover"] [class*="st-key-lp_login_pop_body"] input::placeholder,
        div[data-testid="stPopover"] [class*="st-key-lp_register_pop_body"] input::placeholder{
          color: #94A3B8 !important;
        }

        /* reforço de legibilidade para telas internas */
        [data-testid="stAppViewContainer"] .main .block-container .dh-admin-head-copy h2,
        [data-testid="stAppViewContainer"] .main .block-container .dh-admin-subtitle,
        [data-testid="stAppViewContainer"] .main .block-container .dh-cad-title,
        [data-testid="stAppViewContainer"] .main .block-container .dh-report-title{
          color: #F1F5F9 !important;
          text-shadow: 0 1px 8px rgba(0,0,0,0.30) !important;
          opacity: 1 !important;
        }
        [data-testid="stAppViewContainer"] .main .block-container .dh-admin-head-copy p,
        [data-testid="stAppViewContainer"] .main .block-container .dh-pill-soft,
        [data-testid="stAppViewContainer"] .main .block-container .dh-side-role{
          color: #CBD5E1 !important;
          opacity: 1 !important;
        }

        /* ===== Force patch v4 (global readability + auth + assinatura) ===== */
        body::after{
          content: "UI v4 2026-03-10";
        }

        /* 1) GLOBAL: nunca deixar texto principal escuro no tema dark */
        [data-testid="stAppViewContainer"] .main,
        [data-testid="stAppViewContainer"] .main *{
          color: #CBD5E1 !important;
        }
        [data-testid="stAppViewContainer"] .main h1,
        [data-testid="stAppViewContainer"] .main h2,
        [data-testid="stAppViewContainer"] .main h3,
        [data-testid="stAppViewContainer"] .main h4,
        [data-testid="stAppViewContainer"] .main h5,
        [data-testid="stAppViewContainer"] .main [data-testid="stHeading"] *{
          color: #F1F5F9 !important;
          font-weight: 600 !important;
        }
        [data-testid="stAppViewContainer"] .main .stCaption,
        [data-testid="stAppViewContainer"] .main [data-testid="stCaptionContainer"],
        [data-testid="stAppViewContainer"] .main small,
        [data-testid="stAppViewContainer"] .main label{
          color: #94A3B8 !important;
        }
        [data-testid="stAppViewContainer"] .main a,
        [data-testid="stAppViewContainer"] .main .stLinkButton a{
          color: #22C55E !important;
        }

        /* 2) INPUTS/SELECTS: legíveis e consistentes */
        [data-testid="stAppViewContainer"] .main div[data-baseweb="select"] > div,
        [data-testid="stAppViewContainer"] .main div[data-baseweb="input"] > div,
        [data-testid="stAppViewContainer"] .main div[data-baseweb="datepicker"] > div,
        [data-testid="stAppViewContainer"] .main div[data-baseweb="textarea"] > div,
        [data-testid="stAppViewContainer"] .main .stTextInput input,
        [data-testid="stAppViewContainer"] .main .stNumberInput input,
        [data-testid="stAppViewContainer"] .main .stDateInput input,
        [data-testid="stAppViewContainer"] .main .stTimeInput input,
        [data-testid="stAppViewContainer"] .main .stTextArea textarea{
          background: rgba(2,6,23,0.6) !important;
          color: #F1F5F9 !important;
          border: 1px solid rgba(255,255,255,0.08) !important;
          border-radius: 10px !important;
          min-height: 42px !important;
        }
        [data-testid="stAppViewContainer"] .main div[data-baseweb="select"] span,
        [data-testid="stAppViewContainer"] .main div[data-baseweb="select"] input,
        [data-testid="stAppViewContainer"] .main div[data-baseweb="select"] svg{
          color: #F1F5F9 !important;
          fill: #F1F5F9 !important;
        }
        [data-testid="stAppViewContainer"] .main input::placeholder,
        [data-testid="stAppViewContainer"] .main textarea::placeholder{
          color: #94A3B8 !important;
          opacity: 1 !important;
        }

        /* 3) LOGIN/CADASTRO: card dark SaaS compacto */
        div[class*="st-key-lp_login_pop_shell"],
        div[class*="st-key-lp_register_pop_shell"],
        div[class*="st-key-lp_login_pop_body"],
        div[class*="st-key-lp_register_pop_body"],
        div[class*="st-key-lp_login_pop_body"] div[data-testid="stForm"],
        div[class*="st-key-lp_register_pop_body"] div[data-testid="stForm"]{
          width: min(95vw, 420px) !important;
          max-width: 420px !important;
          margin: 0 auto !important;
          background: rgba(15,23,42,0.88) !important;
          backdrop-filter: blur(8px) !important;
          border-radius: 14px !important;
          padding: 28px !important;
          border: 1px solid rgba(255,255,255,0.05) !important;
          box-shadow: 0 20px 40px rgba(0,0,0,0.35) !important;
        }
        div[class*="st-key-lp_login_pop_shell"] h1,
        div[class*="st-key-lp_login_pop_shell"] h2,
        div[class*="st-key-lp_login_pop_shell"] h3,
        div[class*="st-key-lp_register_pop_shell"] h1,
        div[class*="st-key-lp_register_pop_shell"] h2,
        div[class*="st-key-lp_register_pop_shell"] h3{
          color: #F1F5F9 !important;
          font-weight: 600 !important;
        }
        div[class*="st-key-lp_login_pop_shell"] p,
        div[class*="st-key-lp_register_pop_shell"] p,
        div[class*="st-key-lp_login_pop_body"] label,
        div[class*="st-key-lp_register_pop_body"] label{
          color: #CBD5E1 !important;
          opacity: 1 !important;
        }
        div[class*="st-key-lp_login_pop_body"] input,
        div[class*="st-key-lp_register_pop_body"] input{
          height: 42px !important;
          border-radius: 10px !important;
          border: 1px solid rgba(255,255,255,0.08) !important;
          background: rgba(2,6,23,0.6) !important;
          color: #F1F5F9 !important;
          padding: 0 12px !important;
        }
        div[class*="st-key-lp_login_pop_body"] input:focus,
        div[class*="st-key-lp_register_pop_body"] input:focus{
          border-color: #22C55E !important;
          box-shadow: 0 0 0 2px rgba(34,197,94,0.15) !important;
        }
        div[class*="st-key-lp_login_pop_body"] [data-testid="stFormSubmitButton"] > button,
        div[class*="st-key-lp_register_pop_body"] [data-testid="stFormSubmitButton"] > button{
          height: 44px !important;
          border-radius: 10px !important;
          background: linear-gradient(135deg,#22C55E,#16A34A) !important;
          color: #fff !important;
          font-weight: 600 !important;
          border: none !important;
        }
        .login-box-note{
          background: rgba(34,197,94,0.12) !important;
          border: 1px solid rgba(34,197,94,0.25) !important;
          color: #22C55E !important;
          padding: 8px 14px !important;
          border-radius: 999px !important;
          font-size: 13px !important;
          display: inline-block !important;
          font-weight: 600 !important;
        }

        /* 4) ASSINATURA DIGITAL (sidebar) moderna */
        section[data-testid="stSidebar"] [data-testid="stFileUploaderDropzone"]{
          background: rgba(15,23,42,0.72) !important;
          border: 1px solid rgba(255,255,255,0.10) !important;
          border-radius: 14px !important;
          box-shadow: 0 14px 28px rgba(0,0,0,0.28) !important;
          padding: 14px !important;
        }
        section[data-testid="stSidebar"] [data-testid="stFileUploaderDropzone"] *{
          color: #CBD5E1 !important;
          opacity: 1 !important;
        }
        section[data-testid="stSidebar"] [data-testid="stFileUploaderDropzone"] button{
          height: 38px !important;
          border-radius: 10px !important;
          border: 1px solid rgba(34,197,94,0.35) !important;
          background: linear-gradient(135deg,#22C55E,#16A34A) !important;
          color: #fff !important;
          font-weight: 600 !important;
        }

        @media (max-width: 900px){
          div[class*="st-key-lp_login_pop_shell"],
          div[class*="st-key-lp_register_pop_shell"],
          div[class*="st-key-lp_login_pop_body"],
          div[class*="st-key-lp_register_pop_body"],
          div[class*="st-key-lp_login_pop_body"] div[data-testid="stForm"],
          div[class*="st-key-lp_register_pop_body"] div[data-testid="stForm"]{
            max-width: 95% !important;
            padding: 22px !important;
          }
        }

        /* ===== Force patch v5 (logo + auth clean) ===== */
        body::after{
          content: "UI v5 2026-03-10";
        }

        /* login/cadastro final (cartão claro premium, compacto) */
        div[data-baseweb="popover"] [class*="st-key-lp_login_pop_body"],
        div[data-baseweb="popover"] [class*="st-key-lp_register_pop_body"],
        div[data-testid="stPopover"] [class*="st-key-lp_login_pop_body"],
        div[data-testid="stPopover"] [class*="st-key-lp_register_pop_body"]{
          width: min(94vw, 400px) !important;
          max-width: 400px !important;
        }
        div[data-baseweb="popover"] [class*="st-key-lp_login_pop_shell"],
        div[data-baseweb="popover"] [class*="st-key-lp_register_pop_shell"],
        div[data-baseweb="popover"] [class*="st-key-lp_login_pop_body"] div[data-testid="stForm"],
        div[data-baseweb="popover"] [class*="st-key-lp_register_pop_body"] div[data-testid="stForm"],
        div[data-testid="stPopover"] [class*="st-key-lp_login_pop_shell"],
        div[data-testid="stPopover"] [class*="st-key-lp_register_pop_shell"],
        div[data-testid="stPopover"] [class*="st-key-lp_login_pop_body"] div[data-testid="stForm"],
        div[data-testid="stPopover"] [class*="st-key-lp_register_pop_body"] div[data-testid="stForm"]{
          background: rgba(255,255,255,0.96) !important;
          backdrop-filter: blur(6px) !important;
          border: 1px solid rgba(15,23,42,0.08) !important;
          border-radius: 14px !important;
          box-shadow: 0 18px 36px rgba(2,8,20,0.22) !important;
          padding: 22px !important;
          margin: 0 auto !important;
        }
        div[data-baseweb="popover"] [class*="st-key-lp_login_pop_shell"] h1,
        div[data-baseweb="popover"] [class*="st-key-lp_login_pop_shell"] h2,
        div[data-baseweb="popover"] [class*="st-key-lp_login_pop_shell"] h3,
        div[data-baseweb="popover"] [class*="st-key-lp_register_pop_shell"] h1,
        div[data-baseweb="popover"] [class*="st-key-lp_register_pop_shell"] h2,
        div[data-baseweb="popover"] [class*="st-key-lp_register_pop_shell"] h3,
        div[data-testid="stPopover"] [class*="st-key-lp_login_pop_shell"] h1,
        div[data-testid="stPopover"] [class*="st-key-lp_login_pop_shell"] h2,
        div[data-testid="stPopover"] [class*="st-key-lp_login_pop_shell"] h3,
        div[data-testid="stPopover"] [class*="st-key-lp_register_pop_shell"] h1,
        div[data-testid="stPopover"] [class*="st-key-lp_register_pop_shell"] h2,
        div[data-testid="stPopover"] [class*="st-key-lp_register_pop_shell"] h3{
          color: #0f172a !important;
          font-weight: 700 !important;
        }
        div[data-baseweb="popover"] [class*="st-key-lp_login_pop_shell"] p,
        div[data-baseweb="popover"] [class*="st-key-lp_register_pop_shell"] p,
        div[data-baseweb="popover"] [class*="st-key-lp_login_pop_body"] label,
        div[data-baseweb="popover"] [class*="st-key-lp_register_pop_body"] label,
        div[data-testid="stPopover"] [class*="st-key-lp_login_pop_shell"] p,
        div[data-testid="stPopover"] [class*="st-key-lp_register_pop_shell"] p,
        div[data-testid="stPopover"] [class*="st-key-lp_login_pop_body"] label,
        div[data-testid="stPopover"] [class*="st-key-lp_register_pop_body"] label{
          color: #475569 !important;
          opacity: 1 !important;
        }
        div[data-baseweb="popover"] [class*="st-key-lp_login_pop_body"] input,
        div[data-baseweb="popover"] [class*="st-key-lp_register_pop_body"] input,
        div[data-baseweb="popover"] [class*="st-key-lp_login_pop_body"] textarea,
        div[data-baseweb="popover"] [class*="st-key-lp_register_pop_body"] textarea,
        div[data-testid="stPopover"] [class*="st-key-lp_login_pop_body"] input,
        div[data-testid="stPopover"] [class*="st-key-lp_register_pop_body"] input,
        div[data-testid="stPopover"] [class*="st-key-lp_login_pop_body"] textarea,
        div[data-testid="stPopover"] [class*="st-key-lp_register_pop_body"] textarea{
          height: 42px !important;
          background: #ffffff !important;
          color: #0f172a !important;
          border: 1px solid rgba(15,23,42,0.18) !important;
          border-radius: 10px !important;
          padding: 0 12px !important;
        }
        div[data-baseweb="popover"] [class*="st-key-lp_login_pop_body"] input::placeholder,
        div[data-baseweb="popover"] [class*="st-key-lp_register_pop_body"] input::placeholder,
        div[data-testid="stPopover"] [class*="st-key-lp_login_pop_body"] input::placeholder,
        div[data-testid="stPopover"] [class*="st-key-lp_register_pop_body"] input::placeholder{
          color: #64748b !important;
        }
        div[data-baseweb="popover"] [class*="st-key-lp_login_pop_body"] [data-testid="stFormSubmitButton"] > button,
        div[data-baseweb="popover"] [class*="st-key-lp_register_pop_body"] [data-testid="stFormSubmitButton"] > button,
        div[data-testid="stPopover"] [class*="st-key-lp_login_pop_body"] [data-testid="stFormSubmitButton"] > button,
        div[data-testid="stPopover"] [class*="st-key-lp_register_pop_body"] [data-testid="stFormSubmitButton"] > button{
          height: 44px !important;
          border-radius: 10px !important;
          background: linear-gradient(135deg,#22C55E,#16A34A) !important;
          color: #ffffff !important;
          border: none !important;
          font-weight: 700 !important;
        }
        .login-box-note{
          background: rgba(34,197,94,0.12) !important;
          border: 1px solid rgba(34,197,94,0.28) !important;
          color: #15803d !important;
          border-radius: 999px !important;
          font-size: 13px !important;
          font-weight: 700 !important;
          padding: 8px 12px !important;
        }

        /* ===== Force patch v6 (logo bigger + auth much smaller) ===== */
        body::after{
          content: "UI v6 2026-03-10";
        }

        /* 1) Logo principal maior (como o antigo) */
        .dh-lp-header-logo{
          width: min(100%, 860px) !important;
          max-width: 860px !important;
          max-height: 340px !important;
          height: auto !important;
        }
        @media (max-width: 900px){
          .dh-lp-header-logo{
            width: min(100%, 640px) !important;
            max-width: 640px !important;
            max-height: 260px !important;
          }
        }

        /* 2) Login/Cadastro compactos e sem "duplo card" */
        div[data-baseweb="popover"] > div{
          max-height: none !important;
          overflow: visible !important;
        }
        div[data-baseweb="popover"] [class*="st-key-lp_login_pop_shell"],
        div[data-baseweb="popover"] [class*="st-key-lp_register_pop_shell"],
        div[data-baseweb="popover"] [class*="st-key-lp_login_pop_body"],
        div[data-baseweb="popover"] [class*="st-key-lp_register_pop_body"],
        div[data-testid="stPopover"] [class*="st-key-lp_login_pop_shell"],
        div[data-testid="stPopover"] [class*="st-key-lp_register_pop_shell"],
        div[data-testid="stPopover"] [class*="st-key-lp_login_pop_body"],
        div[data-testid="stPopover"] [class*="st-key-lp_register_pop_body"]{
          background: transparent !important;
          border: none !important;
          box-shadow: none !important;
          backdrop-filter: none !important;
          padding: 0 !important;
          width: min(92vw, 340px) !important;
          max-width: 340px !important;
          margin: 0 auto !important;
        }
        div[data-baseweb="popover"] [class*="st-key-lp_login_pop_body"] div[data-testid="stForm"],
        div[data-baseweb="popover"] [class*="st-key-lp_register_pop_body"] div[data-testid="stForm"],
        div[data-testid="stPopover"] [class*="st-key-lp_login_pop_body"] div[data-testid="stForm"],
        div[data-testid="stPopover"] [class*="st-key-lp_register_pop_body"] div[data-testid="stForm"]{
          width: 100% !important;
          max-width: 340px !important;
          margin: 8px auto 0 auto !important;
          padding: 14px !important;
          border-radius: 12px !important;
          background: rgba(255,255,255,0.97) !important;
          border: 1px solid rgba(15,23,42,0.10) !important;
          box-shadow: 0 12px 24px rgba(2,8,20,0.20) !important;
        }
        div[data-baseweb="popover"] [class*="st-key-lp_login_pop_shell"] h1,
        div[data-baseweb="popover"] [class*="st-key-lp_login_pop_shell"] h2,
        div[data-baseweb="popover"] [class*="st-key-lp_login_pop_shell"] h3,
        div[data-baseweb="popover"] [class*="st-key-lp_register_pop_shell"] h1,
        div[data-baseweb="popover"] [class*="st-key-lp_register_pop_shell"] h2,
        div[data-baseweb="popover"] [class*="st-key-lp_register_pop_shell"] h3,
        div[data-testid="stPopover"] [class*="st-key-lp_login_pop_shell"] h1,
        div[data-testid="stPopover"] [class*="st-key-lp_login_pop_shell"] h2,
        div[data-testid="stPopover"] [class*="st-key-lp_login_pop_shell"] h3,
        div[data-testid="stPopover"] [class*="st-key-lp_register_pop_shell"] h1,
        div[data-testid="stPopover"] [class*="st-key-lp_register_pop_shell"] h2,
        div[data-testid="stPopover"] [class*="st-key-lp_register_pop_shell"] h3{
          margin: 0 0 6px 0 !important;
          font-size: 1.05rem !important;
        }
        div[data-baseweb="popover"] [class*="st-key-lp_login_pop_body"] input,
        div[data-baseweb="popover"] [class*="st-key-lp_register_pop_body"] input,
        div[data-testid="stPopover"] [class*="st-key-lp_login_pop_body"] input,
        div[data-testid="stPopover"] [class*="st-key-lp_register_pop_body"] input{
          height: 38px !important;
          border-radius: 9px !important;
          font-size: 0.98rem !important;
        }
        div[data-baseweb="popover"] [class*="st-key-lp_login_pop_body"] [data-testid="stFormSubmitButton"] > button,
        div[data-baseweb="popover"] [class*="st-key-lp_register_pop_body"] [data-testid="stFormSubmitButton"] > button,
        div[data-testid="stPopover"] [class*="st-key-lp_login_pop_body"] [data-testid="stFormSubmitButton"] > button,
        div[data-testid="stPopover"] [class*="st-key-lp_register_pop_body"] [data-testid="stFormSubmitButton"] > button{
          height: 40px !important;
          border-radius: 9px !important;
        }
        .login-box-note{
          font-size: 12px !important;
          padding: 6px 10px !important;
        }

        /* ===== Force patch v7 (auth contrast + less logo vertical gap) ===== */
        body::after{
          content: "UI v7 2026-03-10";
        }

        /* reduzir espaço acima/abaixo do logo sem alterar tamanho do logo */
        .dh-lp-shell{
          margin-top: -6px !important;
        }
        .dh-lp-header{
          padding: 0 0 4px 0 !important;
          margin: 0 !important;
        }
        .dh-lp-hero{
          margin-top: -4px !important;
        }

        /* login/cadastro com visual dark limpo e alta legibilidade */
        div[data-baseweb="popover"] [class*="st-key-lp_login_pop_shell"],
        div[data-baseweb="popover"] [class*="st-key-lp_register_pop_shell"],
        div[data-baseweb="popover"] [class*="st-key-lp_login_pop_body"],
        div[data-baseweb="popover"] [class*="st-key-lp_register_pop_body"],
        div[data-testid="stPopover"] [class*="st-key-lp_login_pop_shell"],
        div[data-testid="stPopover"] [class*="st-key-lp_register_pop_shell"],
        div[data-testid="stPopover"] [class*="st-key-lp_login_pop_body"],
        div[data-testid="stPopover"] [class*="st-key-lp_register_pop_body"]{
          width: min(92vw, 336px) !important;
          max-width: 336px !important;
          margin: 0 auto !important;
          background: rgba(8,17,35,0.94) !important;
          border: 1px solid rgba(255,255,255,0.10) !important;
          border-radius: 12px !important;
          box-shadow: 0 16px 30px rgba(0,0,0,0.36) !important;
          padding: 14px !important;
          backdrop-filter: blur(6px) !important;
        }
        div[data-baseweb="popover"] [class*="st-key-lp_login_pop_body"] div[data-testid="stForm"],
        div[data-baseweb="popover"] [class*="st-key-lp_register_pop_body"] div[data-testid="stForm"],
        div[data-testid="stPopover"] [class*="st-key-lp_login_pop_body"] div[data-testid="stForm"],
        div[data-testid="stPopover"] [class*="st-key-lp_register_pop_body"] div[data-testid="stForm"]{
          background: transparent !important;
          border: none !important;
          box-shadow: none !important;
          padding: 0 !important;
          margin: 8px 0 0 0 !important;
          max-width: 100% !important;
          width: 100% !important;
        }
        div[data-baseweb="popover"] [class*="st-key-lp_login_pop_shell"] h1,
        div[data-baseweb="popover"] [class*="st-key-lp_login_pop_shell"] h2,
        div[data-baseweb="popover"] [class*="st-key-lp_login_pop_shell"] h3,
        div[data-baseweb="popover"] [class*="st-key-lp_register_pop_shell"] h1,
        div[data-baseweb="popover"] [class*="st-key-lp_register_pop_shell"] h2,
        div[data-baseweb="popover"] [class*="st-key-lp_register_pop_shell"] h3,
        div[data-testid="stPopover"] [class*="st-key-lp_login_pop_shell"] h1,
        div[data-testid="stPopover"] [class*="st-key-lp_login_pop_shell"] h2,
        div[data-testid="stPopover"] [class*="st-key-lp_login_pop_shell"] h3,
        div[data-testid="stPopover"] [class*="st-key-lp_register_pop_shell"] h1,
        div[data-testid="stPopover"] [class*="st-key-lp_register_pop_shell"] h2,
        div[data-testid="stPopover"] [class*="st-key-lp_register_pop_shell"] h3{
          color: #F1F5F9 !important;
          font-weight: 700 !important;
          font-size: 1.02rem !important;
          margin: 0 0 6px 0 !important;
        }
        div[data-baseweb="popover"] [class*="st-key-lp_login_pop_shell"] p,
        div[data-baseweb="popover"] [class*="st-key-lp_register_pop_shell"] p,
        div[data-baseweb="popover"] [class*="st-key-lp_login_pop_body"] label,
        div[data-baseweb="popover"] [class*="st-key-lp_register_pop_body"] label,
        div[data-testid="stPopover"] [class*="st-key-lp_login_pop_shell"] p,
        div[data-testid="stPopover"] [class*="st-key-lp_register_pop_shell"] p,
        div[data-testid="stPopover"] [class*="st-key-lp_login_pop_body"] label,
        div[data-testid="stPopover"] [class*="st-key-lp_register_pop_body"] label{
          color: #CBD5E1 !important;
          opacity: 1 !important;
        }
        div[data-baseweb="popover"] [class*="st-key-lp_login_pop_body"] input,
        div[data-baseweb="popover"] [class*="st-key-lp_register_pop_body"] input,
        div[data-testid="stPopover"] [class*="st-key-lp_login_pop_body"] input,
        div[data-testid="stPopover"] [class*="st-key-lp_register_pop_body"] input{
          height: 38px !important;
          background: rgba(2,6,23,0.72) !important;
          color: #F1F5F9 !important;
          border: 1px solid rgba(255,255,255,0.12) !important;
          border-radius: 9px !important;
        }
        div[data-baseweb="popover"] [class*="st-key-lp_login_pop_body"] input::placeholder,
        div[data-baseweb="popover"] [class*="st-key-lp_register_pop_body"] input::placeholder,
        div[data-testid="stPopover"] [class*="st-key-lp_login_pop_body"] input::placeholder,
        div[data-testid="stPopover"] [class*="st-key-lp_register_pop_body"] input::placeholder{
          color: #94A3B8 !important;
        }
        .login-box-note{
          color: #22C55E !important;
          border-color: rgba(34,197,94,0.28) !important;
          background: rgba(34,197,94,0.12) !important;
        }

        /* ===== Force patch v8 (auth complete SaaS redesign) ===== */
        body::after{
          content: "UI v8 2026-03-10";
        }

        /* Base container (login/cadastro) */
        div[data-baseweb="popover"] [class*="st-key-lp_login_pop_shell"],
        div[data-baseweb="popover"] [class*="st-key-lp_register_pop_shell"],
        div[data-baseweb="popover"] [class*="st-key-lp_login_pop_body"],
        div[data-baseweb="popover"] [class*="st-key-lp_register_pop_body"],
        div[data-testid="stPopover"] [class*="st-key-lp_login_pop_shell"],
        div[data-testid="stPopover"] [class*="st-key-lp_register_pop_shell"],
        div[data-testid="stPopover"] [class*="st-key-lp_login_pop_body"],
        div[data-testid="stPopover"] [class*="st-key-lp_register_pop_body"]{
          width: min(92vw, 420px) !important;
          max-width: 420px !important;
          margin: 0 auto !important;
          background: rgba(15,23,42,0.85) !important;
          backdrop-filter: blur(10px) !important;
          border-radius: 16px !important;
          padding: 28px !important;
          border: 1px solid rgba(255,255,255,0.06) !important;
          box-shadow: 0 20px 40px rgba(0,0,0,0.35) !important;
        }

        /* Remove nested white card from previous patches */
        div[data-baseweb="popover"] [class*="st-key-lp_login_pop_body"] div[data-testid="stForm"],
        div[data-baseweb="popover"] [class*="st-key-lp_register_pop_body"] div[data-testid="stForm"],
        div[data-testid="stPopover"] [class*="st-key-lp_login_pop_body"] div[data-testid="stForm"],
        div[data-testid="stPopover"] [class*="st-key-lp_register_pop_body"] div[data-testid="stForm"]{
          background: transparent !important;
          border: none !important;
          box-shadow: none !important;
          padding: 0 !important;
          margin: 14px 0 0 0 !important;
          width: 100% !important;
          max-width: 100% !important;
        }
        div[data-baseweb="popover"] [class*="st-key-lp_login_pop_body"] div[data-testid="stForm"] form,
        div[data-baseweb="popover"] [class*="st-key-lp_register_pop_body"] div[data-testid="stForm"] form,
        div[data-testid="stPopover"] [class*="st-key-lp_login_pop_body"] div[data-testid="stForm"] form,
        div[data-testid="stPopover"] [class*="st-key-lp_register_pop_body"] div[data-testid="stForm"] form{
          display: grid !important;
          gap: 14px !important;
        }

        /* Title */
        div[data-baseweb="popover"] [class*="st-key-lp_login_pop_shell"] h1,
        div[data-baseweb="popover"] [class*="st-key-lp_login_pop_shell"] h2,
        div[data-baseweb="popover"] [class*="st-key-lp_login_pop_shell"] h3,
        div[data-baseweb="popover"] [class*="st-key-lp_register_pop_shell"] h1,
        div[data-baseweb="popover"] [class*="st-key-lp_register_pop_shell"] h2,
        div[data-baseweb="popover"] [class*="st-key-lp_register_pop_shell"] h3,
        div[data-testid="stPopover"] [class*="st-key-lp_login_pop_shell"] h1,
        div[data-testid="stPopover"] [class*="st-key-lp_login_pop_shell"] h2,
        div[data-testid="stPopover"] [class*="st-key-lp_login_pop_shell"] h3,
        div[data-testid="stPopover"] [class*="st-key-lp_register_pop_shell"] h1,
        div[data-testid="stPopover"] [class*="st-key-lp_register_pop_shell"] h2,
        div[data-testid="stPopover"] [class*="st-key-lp_register_pop_shell"] h3{
          font-size: 22px !important;
          font-weight: 600 !important;
          color: #F1F5F9 !important;
          margin: 0 0 6px 0 !important;
          text-shadow: none !important;
        }
        div[data-baseweb="popover"] [class*="st-key-lp_login_pop_shell"] p,
        div[data-baseweb="popover"] [class*="st-key-lp_register_pop_shell"] p,
        div[data-testid="stPopover"] [class*="st-key-lp_login_pop_shell"] p,
        div[data-testid="stPopover"] [class*="st-key-lp_register_pop_shell"] p{
          color: #CBD5E1 !important;
        }

        /* Badge */
        .login-box-note{
          background: rgba(34,197,94,0.15) !important;
          border: 1px solid rgba(34,197,94,0.35) !important;
          color: #22C55E !important;
          padding: 8px 14px !important;
          border-radius: 999px !important;
          font-size: 13px !important;
          display: inline-block !important;
          font-weight: 600 !important;
        }

        /* Inputs */
        div[data-baseweb="popover"] [class*="st-key-lp_login_pop_body"] label,
        div[data-baseweb="popover"] [class*="st-key-lp_register_pop_body"] label,
        div[data-testid="stPopover"] [class*="st-key-lp_login_pop_body"] label,
        div[data-testid="stPopover"] [class*="st-key-lp_register_pop_body"] label{
          color: #94A3B8 !important;
          font-weight: 500 !important;
        }
        div[data-baseweb="popover"] [class*="st-key-lp_login_pop_body"] input,
        div[data-baseweb="popover"] [class*="st-key-lp_register_pop_body"] input,
        div[data-baseweb="popover"] [class*="st-key-lp_login_pop_body"] textarea,
        div[data-baseweb="popover"] [class*="st-key-lp_register_pop_body"] textarea,
        div[data-testid="stPopover"] [class*="st-key-lp_login_pop_body"] input,
        div[data-testid="stPopover"] [class*="st-key-lp_register_pop_body"] input,
        div[data-testid="stPopover"] [class*="st-key-lp_login_pop_body"] textarea,
        div[data-testid="stPopover"] [class*="st-key-lp_register_pop_body"] textarea{
          height: 42px !important;
          border-radius: 10px !important;
          border: 1px solid rgba(255,255,255,0.08) !important;
          background: rgba(2,6,23,0.6) !important;
          color: #F1F5F9 !important;
          padding: 0 12px !important;
        }
        div[data-baseweb="popover"] [class*="st-key-lp_login_pop_body"] input::placeholder,
        div[data-baseweb="popover"] [class*="st-key-lp_register_pop_body"] input::placeholder,
        div[data-testid="stPopover"] [class*="st-key-lp_login_pop_body"] input::placeholder,
        div[data-testid="stPopover"] [class*="st-key-lp_register_pop_body"] input::placeholder{
          color: #94A3B8 !important;
          opacity: 1 !important;
        }
        div[data-baseweb="popover"] [class*="st-key-lp_login_pop_body"] input:focus,
        div[data-baseweb="popover"] [class*="st-key-lp_register_pop_body"] input:focus,
        div[data-testid="stPopover"] [class*="st-key-lp_login_pop_body"] input:focus,
        div[data-testid="stPopover"] [class*="st-key-lp_register_pop_body"] input:focus{
          border-color: #22C55E !important;
          box-shadow: 0 0 0 2px rgba(34,197,94,0.15) !important;
        }

        /* Password field icon area */
        div[data-baseweb="popover"] [class*="st-key-lp_login_pop_body"] div[data-baseweb="input"] > div,
        div[data-baseweb="popover"] [class*="st-key-lp_register_pop_body"] div[data-baseweb="input"] > div,
        div[data-testid="stPopover"] [class*="st-key-lp_login_pop_body"] div[data-baseweb="input"] > div,
        div[data-testid="stPopover"] [class*="st-key-lp_register_pop_body"] div[data-baseweb="input"] > div{
          background: rgba(2,6,23,0.6) !important;
          border-radius: 10px !important;
          border: 1px solid rgba(255,255,255,0.08) !important;
        }
        div[data-baseweb="popover"] [class*="st-key-lp_login_pop_body"] div[data-baseweb="input"] button,
        div[data-baseweb="popover"] [class*="st-key-lp_register_pop_body"] div[data-baseweb="input"] button,
        div[data-testid="stPopover"] [class*="st-key-lp_login_pop_body"] div[data-baseweb="input"] button,
        div[data-testid="stPopover"] [class*="st-key-lp_register_pop_body"] div[data-baseweb="input"] button{
          min-width: 36px !important;
          width: 36px !important;
          border-radius: 8px !important;
          color: #CBD5E1 !important;
          background: rgba(15,23,42,0.75) !important;
        }

        /* Submit button */
        div[data-baseweb="popover"] [class*="st-key-lp_login_pop_body"] [data-testid="stFormSubmitButton"] > button,
        div[data-baseweb="popover"] [class*="st-key-lp_register_pop_body"] [data-testid="stFormSubmitButton"] > button,
        div[data-testid="stPopover"] [class*="st-key-lp_login_pop_body"] [data-testid="stFormSubmitButton"] > button,
        div[data-testid="stPopover"] [class*="st-key-lp_register_pop_body"] [data-testid="stFormSubmitButton"] > button{
          height: 44px !important;
          border-radius: 10px !important;
          background: linear-gradient(135deg,#22C55E,#16A34A) !important;
          color: #ffffff !important;
          font-weight: 600 !important;
          border: none !important;
          transition: transform .18s ease, box-shadow .18s ease !important;
        }
        div[data-baseweb="popover"] [class*="st-key-lp_login_pop_body"] [data-testid="stFormSubmitButton"] > button:hover,
        div[data-baseweb="popover"] [class*="st-key-lp_register_pop_body"] [data-testid="stFormSubmitButton"] > button:hover,
        div[data-testid="stPopover"] [class*="st-key-lp_login_pop_body"] [data-testid="stFormSubmitButton"] > button:hover,
        div[data-testid="stPopover"] [class*="st-key-lp_register_pop_body"] [data-testid="stFormSubmitButton"] > button:hover{
          transform: translateY(-1px) !important;
          box-shadow: 0 6px 18px rgba(34,197,94,0.25) !important;
        }

        @media (max-width: 900px){
          div[data-baseweb="popover"] [class*="st-key-lp_login_pop_shell"],
          div[data-baseweb="popover"] [class*="st-key-lp_register_pop_shell"],
          div[data-baseweb="popover"] [class*="st-key-lp_login_pop_body"],
          div[data-baseweb="popover"] [class*="st-key-lp_register_pop_body"],
          div[data-testid="stPopover"] [class*="st-key-lp_login_pop_shell"],
          div[data-testid="stPopover"] [class*="st-key-lp_register_pop_shell"],
          div[data-testid="stPopover"] [class*="st-key-lp_login_pop_body"],
          div[data-testid="stPopover"] [class*="st-key-lp_register_pop_body"]{
            max-width: 92% !important;
            padding: 22px !important;
          }
        }

        /* ===== Final override v12 (compact auth + cleanup) ===== */
        body::after{
          content: "UI v12 2026-03-13";
        }

        /* ===== Emergency contrast rescue ===== */
        :root{
          --dh-title: #eef6ff;
          --dh-text: #d7e4f3;
          --dh-text-2: #aac0d8;
          --dh-accent: #34d399;
          --dh-surface: rgba(15,23,42,0.88);
          --dh-input-bg: rgba(248,250,252,0.98);
          --dh-input-border: rgba(148,163,184,0.26);
        }
        [data-testid="stHeading"] h1,
        [data-testid="stHeading"] h2,
        [data-testid="stHeading"] h3,
        [data-testid="stHeading"] h4,
        [data-testid="stAppViewContainer"] .main .block-container h1,
        [data-testid="stAppViewContainer"] .main .block-container h2,
        [data-testid="stAppViewContainer"] .main .block-container h3,
        [data-testid="stAppViewContainer"] .main .block-container h4,
        [data-testid="stAppViewContainer"] .main .block-container h5{
          color: #eef6ff !important;
          text-shadow: 0 1px 10px rgba(2,6,23,0.34) !important;
        }
        [data-testid="stAppViewContainer"] .main .block-container p,
        [data-testid="stAppViewContainer"] .main .block-container li,
        [data-testid="stAppViewContainer"] .main .block-container td,
        [data-testid="stAppViewContainer"] .main .block-container th,
        [data-testid="stAppViewContainer"] .main .block-container span,
        [data-testid="stAppViewContainer"] .main .stMarkdown,
        [data-testid="stAppViewContainer"] .main [data-testid="stCaptionContainer"],
        [data-testid="stAppViewContainer"] .main small{
          color: #d7e4f3 !important;
        }
        [data-testid="stAppViewContainer"] .main label,
        [data-testid="stAppViewContainer"] .main .stTextInput label,
        [data-testid="stAppViewContainer"] .main .stNumberInput label,
        [data-testid="stAppViewContainer"] .main .stDateInput label,
        [data-testid="stAppViewContainer"] .main .stTimeInput label,
        [data-testid="stAppViewContainer"] .main .stSelectbox label,
        [data-testid="stAppViewContainer"] .main .stMultiSelect label,
        [data-testid="stAppViewContainer"] .main .stTextArea label{
          color: #dfeaf5 !important;
          font-weight: 650 !important;
        }
        .dh-rx-hero{
          background: linear-gradient(135deg, rgba(245,250,255,.98), rgba(236,246,250,.96)) !important;
          border-color: rgba(135,206,193,.45) !important;
          box-shadow: 0 22px 42px rgba(0,0,0,.18) !important;
          padding: 14px 16px !important;
          border-radius: 18px !important;
        }
        .dh-rx-hero h2{
          color: #16233b !important;
          text-shadow: none !important;
          font-size: 1.45rem !important;
        }
        .dh-rx-hero p{
          color: #334155 !important;
          font-size: 0.92rem !important;
        }
        .dh-rx-badge{
          background: rgba(197,248,231,.92) !important;
          border-color: rgba(110,231,183,.58) !important;
          color: #0f5b4d !important;
          text-shadow: none !important;
          padding: 6px 10px !important;
        }
        .dh-rx-chip{
          background: rgba(255,255,255,.95) !important;
          border-color: rgba(148,163,184,.18) !important;
          color: #16233b !important;
          padding: 6px 10px !important;
        }
        .dh-rx-panel,
        .dh-rx-patient-card,
        .dh-rx-info-card,
        .dh-rx-kpi,
        .dh-rx-choice-card{
          background: linear-gradient(180deg, rgba(212,245,237,.95), rgba(196,238,230,.92)) !important;
          border-color: rgba(95,180,163,.26) !important;
          box-shadow: 0 14px 28px rgba(3,7,18,.08) !important;
          padding: 14px !important;
          border-radius: 16px !important;
        }
        .dh-rx-panel h4,
        .dh-rx-patient-card strong,
        .dh-rx-info-card h5,
        .dh-rx-kpi strong,
        .dh-rx-choice-card h5{
          color: #10243c !important;
          text-shadow: none !important;
          font-size: 0.92rem !important;
        }
        .dh-rx-panel p,
        .dh-rx-patient-card span,
        .dh-rx-info-card p,
        .dh-rx-info-card li,
        .dh-rx-kpi span,
        .dh-rx-choice-card p{
          color: #2e475f !important;
          font-size: 0.86rem !important;
        }
        .dh-rx-soft-tip{
          background: linear-gradient(180deg, rgba(20,121,101,.24), rgba(15,118,110,.22)) !important;
          border-color: rgba(45,212,191,.28) !important;
          color: #e9fff9 !important;
          padding: 10px 12px !important;
        }
        .dh-rx-choice-note{
          background: rgba(203,247,237,.92) !important;
          border-color: rgba(94,234,212,.32) !important;
          color: #124e50 !important;
          padding: 10px 12px !important;
        }

        /* Topo da landing compacto, estável e sem duplicidade entre desktop e mobile */
        section[data-testid="stAppViewContainer"] .main{
          padding-top: 0 !important;
        }
        section[data-testid="stAppViewContainer"] .main > div,
        section[data-testid="stAppViewContainer"] .main .block-container{
          padding-top: 0 !important;
          margin-top: 0 !important;
        }
        .dh-lp-shell{
          margin-top: 0 !important;
          padding-top: 0 !important;
        }
        .dh-lp-header{
          display: none !important;
        }
        div[class*="st-key-lp_access_topbar_wrap"]{
          width: min(100%, 1280px) !important;
          display: block !important;
          max-width: 1280px !important;
          position: relative !important;
          left: auto !important;
          right: auto !important;
          top: auto !important;
          transform: none !important;
          z-index: 1 !important;
          padding: 0 24px !important;
          margin: 6px auto 8px auto !important;
        }
        div[class*="st-key-lp_access_topbar_wrap"] > div{
          width: 100% !important;
          padding: 0 !important;
          border: none !important;
          background: transparent !important;
          box-shadow: none !important;
          border-radius: 0 !important;
          backdrop-filter: none !important;
          -webkit-backdrop-filter: none !important;
        }
        div[class*="st-key-lp_access_brand_wrap"]{
          display: flex !important;
          align-items: center !important;
          justify-content: center !important;
          min-height: 70px !important;
          padding: 4px 0 0 0 !important;
        }
        div[class*="st-key-lp_access_actions_wrap"]{
          position: fixed !important;
          right: 18px !important;
          top: 10px !important;
          z-index: 1000 !important;
          display: flex !important;
          align-items: center !important;
          justify-content: flex-end !important;
          min-height: auto !important;
        }
        div[class*="st-key-lp_access_actions_wrap"] [data-testid="column"]{
          display: flex !important;
          align-items: center !important;
          justify-content: flex-end !important;
        }
        div[class*="st-key-lp_access_actions_wrap"] [data-testid="stHorizontalBlock"]{
          width: fit-content !important;
          margin-left: auto !important;
          gap: 12px !important;
          padding: 6px 8px !important;
          border-radius: 18px !important;
          border: 1px solid rgba(139, 236, 203, 0.16) !important;
          background:
            linear-gradient(180deg, rgba(7, 20, 31, 0.9), rgba(7, 18, 28, 0.82)) !important;
          box-shadow: 0 10px 18px rgba(0,0,0,0.18) !important;
          backdrop-filter: blur(10px) !important;
          -webkit-backdrop-filter: blur(10px) !important;
        }
        .dh-lp-top-brand{
          justify-content: center !important;
          min-height: 72px !important;
          gap: 16px !important;
        }
        .dh-lp-top-brand-logo{
          width: 110px !important;
          height: 110px !important;
        }
        .dh-lp-top-brand-title{
          font-size: 3rem !important;
          margin-left: 10px !important;
        }
        .dh-lp-top-brand-note{
          font-size: 1.1rem !important;
        }
        .dh-lp-hero{
          margin-top: 0 !important;
          grid-template-columns: minmax(0, 1.1fr) minmax(0, 0.9fr) !important;
          gap: 28px !important;
        }
        div[class*="st-key-lp_access_topbar_wrap"] button{
          margin-top: 0 !important;
          min-width: 112px !important;
          min-height: 42px !important;
          padding-left: 1.1rem !important;
          padding-right: 1.1rem !important;
          font-size: 0.92rem !important;
          font-weight: 600 !important;
          border-radius: 18px !important;
          transition: transform 0.2s ease, filter 0.2s ease !important;
        }
        @media (max-width: 760px){
          div[class*="st-key-lp_access_topbar_wrap"] [data-testid="stHorizontalBlock"]{
            padding: 0 !important;
            border-radius: 0 !important;
          }
          div[class*="st-key-lp_access_brand_wrap"]{
            justify-content: center !important;
            min-height: auto !important;
            margin-bottom: 6px !important;
          }
          div[class*="st-key-lp_access_actions_wrap"]{
            justify-content: center !important;
            min-height: auto !important;
          }
          div[class*="st-key-lp_access_actions_wrap"] [data-testid="column"]{
            justify-content: center !important;
          }
          div[class*="st-key-lp_access_topbar_wrap"]{
            width: calc(100vw - 20px) !important;
            padding: 0 10px !important;
            margin: 6px auto 8px auto !important;
          }
          div[class*="st-key-lp_access_topbar_wrap"] > div{
            width: 100% !important;
            padding: 0 !important;
            border-radius: 0 !important;
          }
          .dh-lp-top-brand{
            justify-content: center !important;
            text-align: center !important;
            min-height: 52px !important;
            gap: 12px !important;
          }
          .dh-lp-top-brand-logo{
            width: 56px !important;
            height: 56px !important;
          }
          .dh-lp-top-brand-title{
            font-size: 1.5rem !important;
          }
          .dh-lp-top-brand-note{
            font-size: 0.9rem !important;
          }
          .dh-lp-hero{
            grid-template-columns: 1fr !important;
            gap: 16px !important;
            margin-top: 0 !important;
          }
          div[class*="st-key-lp_pop_login_wrap"],
          div[class*="st-key-lp_pop_register_wrap"]{
            width: auto !important;
            max-width: none !important;
          }
          div[class*="st-key-lp_access_topbar_wrap"] button{
            min-width: 120px !important;
            min-height: 40px !important;
            padding: 0.6rem 0.8rem !important;
            font-size: 0.85rem !important;
          }
        }

        /* Override final: remove faixa grande e deixar apenas o pill de acoes no topo */
        div[class*="st-key-lp_access_topbar_wrap"],
        div[class*="st-key-lp_access_topbar_wrap"] > div,
        div[class*="st-key-lp_access_topbar_wrap"] [data-testid="stVerticalBlock"],
        div[class*="st-key-lp_access_topbar_wrap"] [data-testid="stHorizontalBlock"]{
          background: transparent !important;
          border: none !important;
          box-shadow: none !important;
          backdrop-filter: none !important;
          -webkit-backdrop-filter: none !important;
          padding: 0 !important;
        }
        div[class*="st-key-lp_access_topbar_wrap"]{
          margin: 0 !important;
          padding: 0 24px !important;
        }
        div[class*="st-key-lp_access_brand_wrap"]{
          justify-content: center !important;
        }
        .dh-lp-top-brand{
          justify-content: center !important;
        }
        div[class*="st-key-lp_access_brand_wrap"] > div{
          background: transparent !important;
          border: none !important;
          box-shadow: none !important;
          padding: 0 !important;
        }
        div[class*="st-key-lp_access_brand_wrap"] [data-testid="stHorizontalBlock"]{
          background: transparent !important;
          border: none !important;
          box-shadow: none !important;
          padding: 0 !important;
        }
        .dh-lp-top-brand{
          min-height: 52px !important;
          background: transparent !important;
          border: none !important;
          box-shadow: none !important;
          padding: 0 !important;
          text-align: left !important;
          justify-content: flex-start !important;
        }
        .dh-lp-top-brand-copy{
          text-align: left !important;
          align-items: flex-start !important;
        }
        .dhx-shell{
          padding-top: 8px !important;
        }
        div[class*="st-key-lp_access_topbar_wrap"] *{
          background: transparent !important;
          border: none !important;
          box-shadow: none !important;
          outline: none !important;
        }
        div[class*="st-key-lp_access_topbar_wrap"] [data-testid="stHorizontalBlock"]{
          display: flex !important;
          align-items: center !important;
          justify-content: space-between !important;
          gap: 6px !important;
          background: transparent !important;
          border: none !important;
          box-shadow: none !important;
        }
        .dhx-hero-grid{
          margin-top: -10px !important;
        }
        .dhx-shell{
          padding-bottom: 12px !important;
        }
        div[class*="st-key-lp_access_topbar_wrap"]{
          width: min(100%, 1280px) !important;
          margin: 4px auto 6px auto !important;
          padding: 0 18px !important;
        }
        div[class*="st-key-lp_access_actions_wrap"]{
          position: static !important;
          right: auto !important;
          top: auto !important;
          z-index: 1000 !important;
          display: flex !important;
          align-items: center !important;
          justify-content: flex-end !important;
        }
        div[class*="st-key-lp_access_actions_wrap"] [data-testid="stHorizontalBlock"]{
          gap: 8px !important;
          display: flex !important;
          flex-wrap: nowrap !important;
          padding: 4px 6px !important;
          border-radius: 16px !important;
          border: 1px solid rgba(139, 236, 203, 0.16) !important;
          background: linear-gradient(180deg, rgba(7, 20, 31, 0.88), rgba(7, 18, 28, 0.8)) !important;
          box-shadow: 0 10px 18px rgba(0,0,0,0.18) !important;
          backdrop-filter: blur(10px) !important;
          -webkit-backdrop-filter: blur(10px) !important;
        }
        div[class*="st-key-lp_access_actions_wrap"] [data-testid="column"]{
          width: auto !important;
          flex: 0 0 auto !important;
        }
        div[class*="st-key-lp_access_actions_wrap"] button{
          white-space: nowrap !important;
          word-break: keep-all !important;
          line-height: 1 !important;
          min-width: 120px !important;
          min-height: 40px !important;
          padding: 0 14px !important;
        }
        div[class*="st-key-lp_access_actions_wrap"] button *{
          white-space: nowrap !important;
          word-break: keep-all !important;
        }
        .dh-lp-top-brand-logo{
          width: 180px !important;
          height: 180px !important;
        }
        @media (max-width: 760px){
          div[class*="st-key-lp_access_topbar_wrap"]{
            padding: 0 12px !important;
            margin: 6px auto !important;
          }
          div[class*="st-key-lp_access_actions_wrap"]{
            justify-content: center !important;
          }
          div[class*="st-key-lp_access_actions_wrap"] [data-testid="stHorizontalBlock"]{
            padding: 4px 6px !important;
            gap: 6px !important;
          }
          div[class*="st-key-lp_access_actions_wrap"] button{
            min-width: 98px !important;
            min-height: 36px !important;
            padding: 0 10px !important;
            font-size: 0.78rem !important;
          }
          .dh-lp-top-brand-logo{
            width: 84px !important;
            height: 84px !important;
          }
          .dhx-shell{
            padding-top: 0 !important;
          }
        }

        /* Forca contraste alto no login/cadastro */
        div[data-baseweb="popover"] [class*="st-key-lp_login_pop_shell"],
        div[data-baseweb="popover"] [class*="st-key-lp_register_pop_shell"],
        div[data-baseweb="popover"] [class*="st-key-lp_login_pop_body"],
        div[data-baseweb="popover"] [class*="st-key-lp_register_pop_body"],
        div[data-testid="stPopover"] [class*="st-key-lp_login_pop_shell"],
        div[data-testid="stPopover"] [class*="st-key-lp_register_pop_shell"],
        div[data-testid="stPopover"] [class*="st-key-lp_login_pop_body"],
        div[data-testid="stPopover"] [class*="st-key-lp_register_pop_body"]{
          background: rgba(8,16,36,0.96) !important;
          opacity: 1 !important;
          color: #E2E8F0 !important;
          border-color: rgba(148,163,184,0.22) !important;
          width: min(90vw, 360px) !important;
          max-width: 360px !important;
          padding: 18px !important;
        }

        div[data-baseweb="popover"] [class*="st-key-lp_login_pop_shell"] *,
        div[data-baseweb="popover"] [class*="st-key-lp_register_pop_shell"] *,
        div[data-baseweb="popover"] [class*="st-key-lp_login_pop_body"] *,
        div[data-baseweb="popover"] [class*="st-key-lp_register_pop_body"] *,
        div[data-testid="stPopover"] [class*="st-key-lp_login_pop_shell"] *,
        div[data-testid="stPopover"] [class*="st-key-lp_register_pop_shell"] *,
        div[data-testid="stPopover"] [class*="st-key-lp_login_pop_body"] *,
        div[data-testid="stPopover"] [class*="st-key-lp_register_pop_body"] *{
          opacity: 1 !important;
        }

        div[data-baseweb="popover"] [class*="st-key-lp_login_pop_body"] input,
        div[data-baseweb="popover"] [class*="st-key-lp_register_pop_body"] input,
        div[data-testid="stPopover"] [class*="st-key-lp_login_pop_body"] input,
        div[data-testid="stPopover"] [class*="st-key-lp_register_pop_body"] input{
          color: #F8FAFC !important;
          background: rgba(8, 16, 36, 0.94) !important;
          border-color: rgba(148,163,184,0.28) !important;
        }
        div[data-baseweb="popover"] [class*="st-key-lp_login_pop_body"] input::placeholder,
        div[data-baseweb="popover"] [class*="st-key-lp_register_pop_body"] input::placeholder,
        div[data-testid="stPopover"] [class*="st-key-lp_login_pop_body"] input::placeholder,
        div[data-testid="stPopover"] [class*="st-key-lp_register_pop_body"] input::placeholder{
          color: rgba(203,213,225,0.7) !important;
        }

        div[data-baseweb="popover"] [class*="st-key-lp_login_pop_shell"] h1,
        div[data-baseweb="popover"] [class*="st-key-lp_login_pop_shell"] h2,
        div[data-baseweb="popover"] [class*="st-key-lp_login_pop_shell"] h3,
        div[data-baseweb="popover"] [class*="st-key-lp_register_pop_shell"] h1,
        div[data-baseweb="popover"] [class*="st-key-lp_register_pop_shell"] h2,
        div[data-baseweb="popover"] [class*="st-key-lp_register_pop_shell"] h3,
        div[data-testid="stPopover"] [class*="st-key-lp_login_pop_shell"] h1,
        div[data-testid="stPopover"] [class*="st-key-lp_login_pop_shell"] h2,
        div[data-testid="stPopover"] [class*="st-key-lp_login_pop_shell"] h3,
        div[data-testid="stPopover"] [class*="st-key-lp_register_pop_shell"] h1,
        div[data-testid="stPopover"] [class*="st-key-lp_register_pop_shell"] h2,
        div[data-testid="stPopover"] [class*="st-key-lp_register_pop_shell"] h3{
          color: #F8FAFC !important;
          text-shadow: none !important;
        }

        div[data-baseweb="popover"] [class*="st-key-lp_login_pop_shell"] p,
        div[data-baseweb="popover"] [class*="st-key-lp_register_pop_shell"] p,
        div[data-baseweb="popover"] [class*="st-key-lp_login_pop_body"] p,
        div[data-baseweb="popover"] [class*="st-key-lp_register_pop_body"] p,
        div[data-baseweb="popover"] [class*="st-key-lp_login_pop_body"] label,
        div[data-baseweb="popover"] [class*="st-key-lp_register_pop_body"] label,
        div[data-testid="stPopover"] [class*="st-key-lp_login_pop_shell"] p,
        div[data-testid="stPopover"] [class*="st-key-lp_register_pop_shell"] p,
        div[data-testid="stPopover"] [class*="st-key-lp_login_pop_body"] p,
        div[data-testid="stPopover"] [class*="st-key-lp_register_pop_body"] p,
        div[data-testid="stPopover"] [class*="st-key-lp_login_pop_body"] label,
        div[data-testid="stPopover"] [class*="st-key-lp_register_pop_body"] label{
          color: #CBD5E1 !important;
        }

        /* Fallback forte: alguns browsers/renderizacoes nao mantem o wrapper stPopover */
        div[class*="st-key-lp_login_pop_shell"],
        div[class*="st-key-lp_register_pop_shell"],
        div[class*="st-key-lp_login_pop_body"],
        div[class*="st-key-lp_register_pop_body"]{
          background: rgba(8,16,36,0.96) !important;
          color: #E2E8F0 !important;
          opacity: 1 !important;
          width: min(90vw, 360px) !important;
          max-width: 360px !important;
          padding: 18px !important;
        }
        div[class*="st-key-lp_login_pop_shell"] h1,
        div[class*="st-key-lp_login_pop_shell"] h2,
        div[class*="st-key-lp_login_pop_shell"] h3,
        div[class*="st-key-lp_register_pop_shell"] h1,
        div[class*="st-key-lp_register_pop_shell"] h2,
        div[class*="st-key-lp_register_pop_shell"] h3{
          color: #F8FAFC !important;
          opacity: 1 !important;
          text-shadow: none !important;
        }
        div[class*="st-key-lp_login_pop_shell"] p,
        div[class*="st-key-lp_register_pop_shell"] p,
        div[class*="st-key-lp_login_pop_body"] p,
        div[class*="st-key-lp_register_pop_body"] p,
        div[class*="st-key-lp_login_pop_body"] label,
        div[class*="st-key-lp_register_pop_body"] label{
          color: #CBD5E1 !important;
          opacity: 1 !important;
        }
        div[class*="st-key-lp_login_pop_body"] input,
        div[class*="st-key-lp_register_pop_body"] input,
        div[class*="st-key-lp_login_pop_body"] textarea,
        div[class*="st-key-lp_register_pop_body"] textarea{
          color: #F8FAFC !important;
          -webkit-text-fill-color: #F8FAFC !important;
          background: rgba(2,6,23,0.96) !important;
          border-color: rgba(100,116,139,0.45) !important;
        }
        div[class*="st-key-lp_login_pop_body"] input::placeholder,
        div[class*="st-key-lp_register_pop_body"] input::placeholder,
        div[class*="st-key-lp_login_pop_body"] textarea::placeholder,
        div[class*="st-key-lp_register_pop_body"] textarea::placeholder{
          color: #94A3B8 !important;
          opacity: 1 !important;
        }
        div[class*="st-key-lp_login_pop_body"] div[data-baseweb="input"] > div,
        div[class*="st-key-lp_register_pop_body"] div[data-baseweb="input"] > div{
          background: rgba(2,6,23,0.96) !important;
          border-color: rgba(100,116,139,0.45) !important;
        }

        .login-box-note{
          display: none !important;
        }

        div[data-baseweb="popover"] [class*="st-key-lp_login_pop_body"] div[data-testid="stForm"],
        div[data-baseweb="popover"] [class*="st-key-lp_register_pop_body"] div[data-testid="stForm"],
        div[data-testid="stPopover"] [class*="st-key-lp_login_pop_body"] div[data-testid="stForm"],
        div[data-testid="stPopover"] [class*="st-key-lp_register_pop_body"] div[data-testid="stForm"],
        div[class*="st-key-lp_login_pop_body"] div[data-testid="stForm"],
        div[class*="st-key-lp_register_pop_body"] div[data-testid="stForm"]{
          margin-top: 8px !important;
        }

        div[data-baseweb="popover"] [class*="st-key-lp_login_pop_body"] div[data-testid="stForm"] form,
        div[data-baseweb="popover"] [class*="st-key-lp_register_pop_body"] div[data-testid="stForm"] form,
        div[data-testid="stPopover"] [class*="st-key-lp_login_pop_body"] div[data-testid="stForm"] form,
        div[data-testid="stPopover"] [class*="st-key-lp_register_pop_body"] div[data-testid="stForm"] form{
          gap: 10px !important;
        }

        div[data-baseweb="popover"] [class*="st-key-lp_login_pop_body"] [data-testid="stFormSubmitButton"] > button,
        div[data-baseweb="popover"] [class*="st-key-lp_register_pop_body"] [data-testid="stFormSubmitButton"] > button,
        div[data-testid="stPopover"] [class*="st-key-lp_login_pop_body"] [data-testid="stFormSubmitButton"] > button,
        div[data-testid="stPopover"] [class*="st-key-lp_register_pop_body"] [data-testid="stFormSubmitButton"] > button,
        div[class*="st-key-lp_login_pop_body"] [data-testid="stFormSubmitButton"] > button,
        div[class*="st-key-lp_register_pop_body"] [data-testid="stFormSubmitButton"] > button{
          height: 40px !important;
        }

        @media (max-width: 900px){
          div[data-baseweb="popover"] [class*="st-key-lp_login_pop_shell"],
          div[data-baseweb="popover"] [class*="st-key-lp_register_pop_shell"],
          div[data-baseweb="popover"] [class*="st-key-lp_login_pop_body"],
          div[data-baseweb="popover"] [class*="st-key-lp_register_pop_body"],
          div[data-testid="stPopover"] [class*="st-key-lp_login_pop_shell"],
          div[data-testid="stPopover"] [class*="st-key-lp_register_pop_shell"],
          div[data-testid="stPopover"] [class*="st-key-lp_login_pop_body"],
          div[data-testid="stPopover"] [class*="st-key-lp_register_pop_body"],
          div[class*="st-key-lp_login_pop_shell"],
          div[class*="st-key-lp_register_pop_shell"],
          div[class*="st-key-lp_login_pop_body"],
          div[class*="st-key-lp_register_pop_body"]{
            width: min(92vw, 344px) !important;
            max-width: 344px !important;
            padding: 16px !important;
          }
        }

        /* ===== Final mobile/UX polish for critical screens ===== */
        .dh-admin-panel-title,
        .dh-report-section-title,
        .dh-chart-panel h4,
        .dh-agenda-panel h4{
          line-height: 1.2 !important;
          letter-spacing: -0.01em !important;
          text-wrap: balance !important;
        }
        .metric-container,
        .dh-admin-summary-card,
        .dh-report-panel,
        .dh-report-summary,
        .dh-chart-panel,
        .dh-agenda-panel{
          overflow: hidden !important;
        }
        .metric-label,
        .metric-note,
        .dh-admin-summary-item,
        .dh-report-subtitle,
        .dh-report-section-subtitle,
        .dh-chart-panel p,
        .dh-agenda-panel p{
          overflow-wrap: anywhere !important;
          word-break: break-word !important;
        }
        .dh-report-data-value,
        .dh-report-summary-meta,
        .dh-chart-mini span,
        .dh-agenda-mini span{
          line-height: 1.58 !important;
        }
        .metric-container{
          min-height: 208px !important;
        }
        .dh-report-title{
          font-size: clamp(1.5rem, 1.1rem + 1vw, 2rem) !important;
          line-height: 1.08 !important;
        }
        .dh-report-kpi-value,
        .dh-chart-kpi strong,
        .dh-agenda-kpi strong{
          line-height: 1.05 !important;
        }
        div[class*="st-key-lp_pop_login_wrap"] button,
        div[class*="st-key-lp_pop_register_wrap"] button{
          min-height: 46px !important;
          font-size: 0.94rem !important;
        }

        @media (max-width: 980px){
          .metric-container{
            min-height: 186px !important;
          }
          .dh-report-kpis{
            grid-template-columns: repeat(2, minmax(0,1fr)) !important;
          }
        }

        @media (max-width: 760px){
          div[class*="st-key-lp_pop_login_wrap"]{
            width: min(100%, 136px) !important;
            max-width: 150px !important;
          }
          div[class*="st-key-lp_pop_register_wrap"]{
            width: min(100%, 136px) !important;
            max-width: 150px !important;
          }
          div[class*="st-key-lp_pop_login_wrap"] button,
          div[class*="st-key-lp_pop_register_wrap"] button{
            min-height: 44px !important;
            padding: 0.72rem 0.7rem !important;
            font-size: 0.88rem !important;
          }
          div[class*="st-key-lp_login_pop_body"],
          div[class*="st-key-lp_register_pop_body"]{
            width: min(94vw, 360px) !important;
          }
          .metric-container{
            min-height: auto !important;
            padding: 16px 14px 18px !important;
          }
          .metric-value{
            font-size: clamp(1.35rem, 1.15rem + 1vw, 1.75rem) !important;
          }
          .metric-label{
            font-size: 0.88rem !important;
          }
          .metric-note{
            font-size: 0.84rem !important;
          }
          .dh-admin-panel-title{
            font-size: 1.02rem !important;
          }
          .dh-agenda-hero,
          .dh-chart-hero,
          .dh-report-hero{
            grid-template-columns: 1fr !important;
          }
          .dh-agenda-kpis,
          .dh-chart-kpis,
          .dh-report-kpis{
            grid-template-columns: 1fr !important;
          }
          .dh-report-data-grid{
            grid-template-columns: 1fr !important;
          }
          .dh-report-panel,
          .dh-report-summary,
          .dh-chart-panel,
          .dh-agenda-panel{
            padding: 16px 14px !important;
            border-radius: 18px !important;
          }
          .dh-report-summary-head{
            flex-direction: column !important;
            align-items: flex-start !important;
          }
          .dh-report-badge{
            white-space: normal !important;
          }
          .dh-lp-virtual-access-intro{
            padding: 18px 16px !important;
          }
          .dh-lp-virtual-access-copy{
            padding: 18px 16px !important;
          }
          .dh-lp-virtual-access-copy h4{
            font-size: 1.34rem !important;
          }
          div[class*="st-key-lp_virtual_access_card"]{
            padding: 18px 16px !important;
          }
          .dh-chart-mini,
          .dh-agenda-mini{
            padding: 12px !important;
          }
        }

        /* Header mobile final: remove a caixa grande e deixa apenas a faixa compacta */
        @media (max-width: 760px){
          div[class*="st-key-lp_access_topbar_wrap"]{
            position: static !important;
            left: auto !important;
            top: auto !important;
            transform: none !important;
            width: 100% !important;
            max-width: none !important;
            margin: 0 0 2px 0 !important;
            padding: 0 !important;
          }
          div[class*="st-key-lp_access_topbar_wrap"] > div,
          div[class*="st-key-lp_access_topbar_wrap"] [data-testid="stHorizontalBlock"]{
            background: transparent !important;
            border: none !important;
            box-shadow: none !important;
            backdrop-filter: none !important;
            -webkit-backdrop-filter: none !important;
            padding: 0 !important;
            border-radius: 0 !important;
            gap: 6px !important;
          }
          div[class*="st-key-lp_access_brand_wrap"]{
            margin-bottom: 0 !important;
          }
          div[class*="st-key-lp_access_actions_wrap"]{
            justify-content: flex-end !important;
          }
          div[class*="st-key-lp_access_actions_wrap"] [data-testid="stHorizontalBlock"]{
            width: fit-content !important;
            margin-left: auto !important;
            justify-content: flex-end !important;
            padding: 6px 8px !important;
            border-radius: 16px !important;
            border: 1px solid rgba(139, 236, 203, 0.14) !important;
            background:
              linear-gradient(180deg, rgba(7, 20, 31, 0.92), rgba(7, 18, 28, 0.84)),
              radial-gradient(circle at top left, rgba(24, 208, 145, 0.09), transparent 42%) !important;
            box-shadow: 0 10px 18px rgba(0,0,0,0.14) !important;
          }
          div[class*="st-key-lp_pop_login_wrap"],
          div[class*="st-key-lp_pop_register_wrap"]{
            width: auto !important;
            max-width: none !important;
          }
          div[class*="st-key-lp_pop_login_wrap"] button,
          div[class*="st-key-lp_pop_register_wrap"] button,
          div[class*="st-key-lp_access_topbar_wrap"] button{
            min-width: 88px !important;
            min-height: 34px !important;
            padding: 0.48rem 0.72rem !important;
            font-size: 0.78rem !important;
          }
        }

        /* Override final: garante legibilidade do Entrar/Cadastro acima de qualquer regra anterior */
        div[class*="st-key-lp_login_pop_shell"],
        div[class*="st-key-lp_register_pop_shell"],
        div[class*="st-key-lp_login_pop_body"],
        div[class*="st-key-lp_register_pop_body"]{
          color: #EAF2FF !important;
          opacity: 1 !important;
        }
        div[class*="st-key-lp_login_pop_shell"] h1,
        div[class*="st-key-lp_login_pop_shell"] h2,
        div[class*="st-key-lp_login_pop_shell"] h3,
        div[class*="st-key-lp_register_pop_shell"] h1,
        div[class*="st-key-lp_register_pop_shell"] h2,
        div[class*="st-key-lp_register_pop_shell"] h3,
        div[class*="st-key-lp_login_pop_body"] h1,
        div[class*="st-key-lp_login_pop_body"] h2,
        div[class*="st-key-lp_login_pop_body"] h3,
        div[class*="st-key-lp_register_pop_body"] h1,
        div[class*="st-key-lp_register_pop_body"] h2,
        div[class*="st-key-lp_register_pop_body"] h3{
          color: #F8FBFF !important;
          opacity: 1 !important;
          filter: none !important;
          text-shadow: none !important;
        }
        div[class*="st-key-lp_login_pop_shell"] p,
        div[class*="st-key-lp_register_pop_shell"] p,
        div[class*="st-key-lp_login_pop_body"] p,
        div[class*="st-key-lp_register_pop_body"] p,
        div[class*="st-key-lp_login_pop_body"] label,
        div[class*="st-key-lp_register_pop_body"] label,
        div[class*="st-key-lp_login_pop_body"] span,
        div[class*="st-key-lp_register_pop_body"] span,
        div[class*="st-key-lp_login_pop_body"] div,
        div[class*="st-key-lp_register_pop_body"] div{
          color: #D6E3F1 !important;
          opacity: 1 !important;
          filter: none !important;
        }
        div[class*="st-key-lp_login_pop_body"] input,
        div[class*="st-key-lp_register_pop_body"] input,
        div[class*="st-key-lp_login_pop_body"] textarea,
        div[class*="st-key-lp_register_pop_body"] textarea,
        div[class*="st-key-lp_login_pop_body"] input[type="text"],
        div[class*="st-key-lp_register_pop_body"] input[type="text"],
        div[class*="st-key-lp_login_pop_body"] input[type="password"],
        div[class*="st-key-lp_register_pop_body"] input[type="password"]{
          color: #F8FBFF !important;
          -webkit-text-fill-color: #F8FBFF !important;
          caret-color: #5EEAD4 !important;
          background: rgba(3,9,24,0.96) !important;
          opacity: 1 !important;
        }
        div[class*="st-key-lp_login_pop_body"] input::placeholder,
        div[class*="st-key-lp_register_pop_body"] input::placeholder,
        div[class*="st-key-lp_login_pop_body"] textarea::placeholder,
        div[class*="st-key-lp_register_pop_body"] textarea::placeholder{
          color: #8FA6BE !important;
          opacity: 1 !important;
        }
        div[class*="st-key-lp_login_pop_body"] [role="radiogroup"] *,
        div[class*="st-key-lp_register_pop_body"] [role="radiogroup"] *,
        div[class*="st-key-lp_login_pop_body"] [data-baseweb="radio"] *,
        div[class*="st-key-lp_register_pop_body"] [data-baseweb="radio"] *{
          color: #EAF2FF !important;
          opacity: 1 !important;
        }
        div[class*="st-key-lp_login_pop_body"] [data-testid="stFormSubmitButton"] > button,
        div[class*="st-key-lp_register_pop_body"] [data-testid="stFormSubmitButton"] > button{
          color: #04111f !important;
          font-weight: 800 !important;
          opacity: 1 !important;
        }

        /* Header final: remover coluna/caixa do topo e centralizar logo/texto */
        div[class*="st-key-lp_access_topbar_wrap"],
        div[class*="st-key-lp_access_topbar_wrap"] > div,
        div[class*="st-key-lp_access_topbar_wrap"] [data-testid="stVerticalBlock"],
        div[class*="st-key-lp_access_topbar_wrap"] [data-testid="stHorizontalBlock"],
        div[class*="st-key-lp_access_brand_wrap"],
        div[class*="st-key-lp_access_brand_wrap"] > div,
        div[class*="st-key-lp_access_brand_wrap"] [data-testid="column"],
        div[class*="st-key-lp_access_brand_wrap"] [data-testid="stHorizontalBlock"]{
          background: transparent !important;
          border: none !important;
          box-shadow: none !important;
          backdrop-filter: none !important;
          -webkit-backdrop-filter: none !important;
        }
        div[class*="st-key-lp_access_brand_wrap"]{
          display: flex !important;
          justify-content: center !important;
          align-items: center !important;
          padding: 0 !important;
          margin: 0 !important;
        }
        .dh-lp-top-brand{
          justify-content: center !important;
          margin: 0 !important;
          padding: 0 !important;
        }

        /* Remove qualquer "caixa" residual ao redor do logo/titulo */
        div[class*="st-key-lp_access_brand_wrap"] > div,
        div[class*="st-key-lp_access_brand_wrap"] > div > div,
        div[class*="st-key-lp_access_brand_wrap"] > div > div > div,
        div[class*="st-key-lp_access_brand_wrap"] [data-testid="stVerticalBlock"],
        div[class*="st-key-lp_access_brand_wrap"] [data-testid="stHorizontalBlock"],
        div[class*="st-key-lp_access_brand_wrap"] [data-testid="stMarkdownContainer"]{
          background: transparent !important;
          border: none !important;
          box-shadow: none !important;
          outline: none !important;
          border-radius: 0 !important;
          padding: 0 !important;
          margin: 0 !important;
        }

        /* Entrar/Cadastro pequenos e discretos no topo direito */
        div[class*="st-key-lp_access_actions_wrap"]{
          position: fixed !important;
          right: 14px !important;
          top: 10px !important;
          z-index: 1000 !important;
        }
        div[class*="st-key-lp_access_actions_wrap"] [data-testid="stHorizontalBlock"]{
          gap: 8px !important;
          padding: 5px 7px !important;
          border-radius: 14px !important;
          border: 1px solid rgba(139, 236, 203, 0.14) !important;
          background: linear-gradient(180deg, rgba(7, 20, 31, 0.86), rgba(7, 18, 28, 0.78)) !important;
          box-shadow: 0 8px 14px rgba(0,0,0,0.18) !important;
        }
        div[class*="st-key-lp_access_actions_wrap"] button{
          min-width: 98px !important;
          min-height: 34px !important;
          padding: 0.45rem 0.8rem !important;
          font-size: 0.82rem !important;
          border-radius: 14px !important;
        }

        /* Ajuste final do topo + correção mobile */
        div[class*="st-key-lp_access_topbar_wrap"],
        div[class*="st-key-lp_access_topbar_wrap"] > div,
        div[class*="st-key-lp_access_topbar_wrap"] [data-testid="stHorizontalBlock"],
        div[class*="st-key-lp_access_topbar_wrap"] [data-testid="stVerticalBlock"]{
          background: transparent !important;
          border: none !important;
          box-shadow: none !important;
          backdrop-filter: none !important;
          -webkit-backdrop-filter: none !important;
        }
        div[class*="st-key-lp_access_topbar_wrap"]{
          display: inline-flex !important;
          align-items: center !important;
          width: auto !important;
          max-width: calc(100vw - 32px) !important;
          margin: 0 0 6px 16px !important;
          padding: 0 !important;
        }
        div[class*="st-key-lp_access_topbar_wrap"] > div,
        div[class*="st-key-lp_access_topbar_wrap"] [data-testid="stVerticalBlock"]{
          width: auto !important;
          max-width: none !important;
        }
        div[class*="st-key-lp_access_topbar_wrap"] [data-testid="stHorizontalBlock"]{
          width: auto !important;
          padding: 0 !important;
          gap: 10px !important;
          align-items: center !important;
          justify-content: flex-start !important;
          display: inline-flex !important;
          flex-wrap: nowrap !important;
        }
        div[class*="st-key-lp_access_topbar_wrap"] [data-testid="column"]{
          width: auto !important;
          flex: 0 0 auto !important;
          max-width: none !important;
          min-width: 0 !important;
        }
        div[class*="st-key-lp_access_brand_wrap"]{
          flex: 0 0 auto !important;
          min-width: 0 !important;
          margin-right: 6px !important;
        }
        div[class*="st-key-lp_access_actions_wrap"]{
          position: static !important;
          right: auto !important;
          top: auto !important;
          z-index: 2000 !important;
          display: flex !important;
          justify-content: flex-start !important;
          align-items: center !important;
          min-height: auto !important;
          margin-left: 6px !important;
        }
        div[class*="st-key-lp_access_actions_wrap"]{
          width: auto !important;
          flex: 0 0 auto !important;
        }
        div[class*="st-key-lp_access_actions_wrap"] [data-testid="stHorizontalBlock"]{
          width: fit-content !important;
          max-width: 100% !important;
          padding: 0 !important;
          border: none !important;
          background: transparent !important;
          box-shadow: none !important;
          gap: 6px !important;
          justify-content: flex-end !important;
        }
        div[class*="st-key-lp_access_actions_wrap"] button{
          white-space: nowrap !important;
          word-break: keep-all !important;
          line-height: 1 !important;
        }
        div[class*="st-key-lp_access_actions_wrap"] button *{
          white-space: nowrap !important;
        }
        section[data-testid="stAppViewContainer"] .main .block-container{
          padding-top: 0 !important;
          margin-top: 0 !important;
        }
        .dhx-shell{
          padding-top: 0 !important;
        }
        .dhx-hero-grid{
          margin-top: 0 !important;
        }
        @media (max-width: 760px){
          div[class*="st-key-lp_access_topbar_wrap"]{
            display: flex !important;
            width: 100% !important;
            margin: 4px auto 6px auto !important;
            padding: 0 12px !important;
          }
          div[class*="st-key-lp_access_topbar_wrap"] [data-testid="stHorizontalBlock"]{
            width: 100% !important;
            flex-wrap: wrap !important;
            justify-content: center !important;
            gap: 8px !important;
          }
          div[class*="st-key-lp_access_brand_wrap"]{
            width: 100% !important;
            justify-content: center !important;
            margin-right: 0 !important;
          }
          div[class*="st-key-lp_access_actions_wrap"]{
            position: static !important;
            right: auto !important;
            top: auto !important;
            width: 100% !important;
            justify-content: center !important;
            margin-top: 4px !important;
            margin-left: 0 !important;
          }
          div[class*="st-key-lp_access_actions_wrap"] [data-testid="stHorizontalBlock"]{
            width: auto !important;
            flex-direction: row !important;
            flex-wrap: wrap !important;
            align-items: center !important;
            justify-content: center !important;
            gap: 6px !important;
          }
          div[class*="st-key-lp_access_actions_wrap"] button{
            min-width: 84px !important;
            min-height: 30px !important;
            padding: 0 8px !important;
            font-size: 0.72rem !important;
          }
        }

        /* Override final: topo realmente colado e sem espaço sobrando */
        section[data-testid="stAppViewContainer"] .main,
        section[data-testid="stAppViewContainer"] .main .block-container,
        div[data-testid="stMainBlockContainer"]{
          padding-top: 0 !important;
          margin-top: 0 !important;
        }
        section[data-testid="stAppViewContainer"] .main .block-container > div:first-child{
          margin-top: 0 !important;
          padding-top: 0 !important;
        }
        div[class*="st-key-lp_access_topbar_wrap"]{
          position: fixed !important;
          top: 6px !important;
          left: 50% !important;
          transform: translateX(-50%) !important;
          width: min(1080px, calc(100vw - 24px)) !important;
          margin: 0 !important;
          padding: 0 8px !important;
          z-index: 5000 !important;
        }
        div[class*="st-key-lp_access_topbar_wrap"] [data-testid="stHorizontalBlock"]{
          width: 100% !important;
          display: flex !important;
          align-items: center !important;
          justify-content: space-between !important;
          gap: 12px !important;
        }
        div[class*="st-key-lp_access_brand_wrap"]{
          flex: 1 1 auto !important;
          min-width: 0 !important;
        }
        div[class*="st-key-lp_access_actions_wrap"]{
          position: fixed !important;
          top: 8px !important;
          right: 14px !important;
          z-index: 5200 !important;
          display: flex !important;
          align-items: center !important;
          justify-content: flex-end !important;
          width: auto !important;
          flex: 0 0 auto !important;
        }
        div[class*="st-key-lp_access_actions_wrap"] [data-testid="stHorizontalBlock"]{
          gap: 6px !important;
          padding: 2px 6px !important;
          border-radius: 999px !important;
          border: 1px solid rgba(139, 236, 203, 0.1) !important;
          background: rgba(6, 16, 26, 0.32) !important;
          box-shadow: 0 4px 10px rgba(0,0,0,0.16) !important;
          backdrop-filter: blur(8px) !important;
          -webkit-backdrop-filter: blur(8px) !important;
        }
        div[class*="st-key-lp_access_actions_wrap"] button{
          min-width: 78px !important;
          min-height: 28px !important;
          padding: 0.2rem 0.55rem !important;
          font-size: 0.7rem !important;
          border-radius: 999px !important;
          opacity: 0.9 !important;
        }
        .dh-lp-top-brand{
          justify-content: flex-start !important;
          gap: 12px !important;
        }
        .dh-lp-top-brand-copy{
          text-align: left !important;
          align-items: flex-start !important;
        }
        .dh-lp-top-brand-title{
          white-space: nowrap !important;
        }
        .dhx-shell{
          padding-top: 60px !important;
        }
        @media (min-width: 761px){
          div[class*="st-key-lp_access_brand_wrap"]{
            position: fixed !important;
            top: 8px !important;
            left: 18px !important;
            z-index: 5200 !important;
            max-width: calc(100vw - 240px) !important;
          }
        }
        @media (max-width: 900px){
          .dh-lp-top-brand-title{
            white-space: normal !important;
          }
        }
        @media (max-width: 760px){
          div[class*="st-key-lp_access_topbar_wrap"]{
            position: static !important;
            left: auto !important;
            transform: none !important;
            width: 100% !important;
            margin: 0 auto 6px auto !important;
            padding: 0 12px !important;
          }
          div[class*="st-key-lp_access_brand_wrap"]{
            position: static !important;
            top: auto !important;
            left: auto !important;
            max-width: 100% !important;
          }
          div[class*="st-key-lp_access_actions_wrap"]{
            position: fixed !important;
            top: 8px !important;
            right: 8px !important;
            width: auto !important;
            justify-content: flex-end !important;
            margin-top: 0 !important;
          }
          div[class*="st-key-lp_access_actions_wrap"] [data-testid="stHorizontalBlock"]{
            padding: 2px 4px !important;
            border-radius: 999px !important;
            background: rgba(6, 16, 26, 0.4) !important;
          }
          div[class*="st-key-lp_access_actions_wrap"] button{
            min-width: 72px !important;
            min-height: 28px !important;
            font-size: 0.68rem !important;
          }
          .dhx-shell{
            padding-top: 0 !important;
          }
        }

        /* Fix final: header stick no topo no desktop (nao rola com a pagina) */
        @media (min-width: 761px){
          div[class*="st-key-lp_access_topbar_wrap"]{
            position: sticky !important;
            top: 6px !important;
            left: auto !important;
            transform: none !important;
            width: min(100%, 1280px) !important;
            margin: 0 auto 8px auto !important;
            z-index: 5200 !important;
          }
          div[class*="st-key-lp_access_brand_wrap"]{
            position: static !important;
            top: auto !important;
            left: auto !important;
          }
          div[class*="st-key-lp_access_actions_wrap"]{
            position: fixed !important;
            top: 10px !important;
            right: 14px !important;
            margin-left: 0 !important;
            z-index: 5200 !important;
          }
        }

</style>
        """,
        unsafe_allow_html=True
    )
    if not st.session_state["logado"]:
        mostrar_landing_page()
        return

    _touch_user_presence()

    if _dh_simple_mode_enabled():
        st.markdown(
            """
            <style>
            section[data-testid="stAppViewContainer"] .main .block-container{
              padding-top:1rem !important;
              padding-bottom:1.25rem !important;
            }
            </style>
            """,
            unsafe_allow_html=True,
        )

    experience_mode = _dh_experience_mode()

    with st.sidebar:
        tipo_atual = (st.session_state.get("tipo") or "user").strip().lower()
        user_obj = _ensure_patient_user_link(_get_user_obj())
        user_label = (user_obj.get("nome") or st.session_state.get("usuario") or "admin").strip()
        is_admin = (tipo_atual == "admin")
        is_patient = (tipo_atual == "patient")
        if is_admin:
            role_label = "Administrador"
        elif is_patient:
            role_label = "Paciente"
        else:
            role_label = "Nutricionista"

        st.markdown(
            _html_block(f"""
<div class="dh-side-top">
  <div class="dh-side-user">
    <div class="dh-side-avatar">&#128100;</div>
    <div class="dh-side-user-info">
      <div class="dh-side-name">{user_label}</div>
      <div class="dh-side-role">{role_label} - DietHealth</div>
      <div class="dh-side-user-pill">Usuario ativo</div>
    </div>
  </div>
</div>
"""),
            unsafe_allow_html=True
        )

        st.markdown('<div style="height:4px"></div>', unsafe_allow_html=True)

        if experience_mode == "virtual":
            st.caption("Painel de Atendimento Virtual separado do sistema principal.")
        elif not is_patient:
            simple_toggle = st.toggle(
                "Modo Simples",
                value=_dh_simple_mode_enabled(),
                key="dh_simple_mode_toggle",
                help="Mostra uma interface mais enxuta, com foco no essencial do atendimento.",
            )
            if bool(simple_toggle) != _dh_simple_mode_enabled():
                st.session_state[SIMPLE_MODE_SESSION_KEY] = bool(simple_toggle)
                st.rerun()
            st.caption("Interface Essencial para atendimentos mais rápidos.")

        if experience_mode == "virtual":
            menu_route = _render_camila_sidebar(role=tipo_atual)
        else:
            st.markdown('<div class="dh-menu-title">Menu</div>', unsafe_allow_html=True)
            menu_route = _render_sidebar_icon_menu(role=tipo_atual)
        components.html(
            """
            <script>
            (function () {
              const host = window.parent || window;
              const doc = host.document;
              const updateSidebarState = () => {
                try {
                  const sb = doc.querySelector('section[data-testid="stSidebar"]');
                  if (!sb) return;
                  const rect = sb.getBoundingClientRect();
                  const collapsed = rect.width < 40;
                  doc.body.classList.toggle('dh-sidebar-collapsed', collapsed);
                  doc.body.classList.toggle('dh-sidebar-open', !collapsed);
                } catch (e) {}
              };
              updateSidebarState();
              const t = host.setInterval(updateSidebarState, 250);
              host.setTimeout(() => host.clearInterval(t), 6000);
            })();
            </script>
            """,
            height=0,
        )

        if st.session_state.get("dh_close_sidebar_after_nav"):
            components.html(
                """
                <script>
                (function () {
                  try {
                    const host = window.parent || window;
                    if (host.dhCloseSidebar) {
                      host.dhCloseSidebar();
                    }
                  } catch (e) {}
                })();
                </script>
                """,
                height=0,
            )
            st.session_state["dh_close_sidebar_after_nav"] = False

        if st.button("Sair", key="logout_btn_menu"):
            _mark_user_offline(st.session_state.get("usuario"))
            _clear_persisted_login_query()
            _qp_set(SIDEBAR_MENU_QUERY_KEY, "")
            st.session_state["logado"] = False
            st.session_state["usuario"] = ""
            st.session_state["tipo"] = "user"
            st.session_state[EXPERIENCE_SESSION_KEY] = "traditional"
            st.session_state[VIRTUAL_MENU_SESSION_KEY] = "camila_home"
            st.rerun()


        if (experience_mode != "virtual") and not is_patient:
            st.divider()
            with st.expander("✒️ Assinatura Digital", expanded=False):
                st.caption("Envie uma imagem da sua assinatura/carimbo (PNG/JPG). Ela será usada automaticamente nos PDFs.")
                uploaded_ass = st.file_uploader("Carregar imagem", type=["png", "jpg", "jpeg"], key="upload_ass_sidebar")

                usuario_atual = (st.session_state.get("usuario") or "admin").strip().lower()
                assin_dir = os.path.join("assets", "assinaturas")
                os.makedirs(assin_dir, exist_ok=True)

                atual = None
                for ext in ("png", "jpg", "jpeg"):
                    p = os.path.join(assin_dir, f"assin_{usuario_atual}.{ext}")
                    if os.path.exists(p):
                        atual = p
                        break
                if atual:
                    st.caption("Assinatura atual:")
                    st.image(atual, use_container_width=True)

                if uploaded_ass is not None:
                    ext = uploaded_ass.name.split(".")[-1].lower()
                    p_user = os.path.join(assin_dir, f"assin_{usuario_atual}.{ext}")
                    p_root = f"assinatura_img.{ext}"

                    with open(p_user, "wb") as f:
                        f.write(uploaded_ass.getbuffer())
                    with open(p_root, "wb") as f:
                        f.write(uploaded_ass.getbuffer())

                    st.success("Assinatura salva com sucesso. Ela será aplicada nos PDFs.")
                    time.sleep(0.4)
                    st.rerun()

    st.markdown(
        """
        <div class="dh-menu-fab" onclick="window.dhOpenSidebar && window.dhOpenSidebar();">
          <span>☰</span><span>Menu</span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if experience_mode == "virtual":
        if menu_route == "camila_home":
            modulo_camila_home()
        elif menu_route == "camila_atendimento":
            modulo_camila_atendimento()
        elif menu_route == "camila_dados":
            modulo_camila_dados()
        elif menu_route == "camila_medidas":
            modulo_camila_medidas()
        elif menu_route == "camila_dieta":
            modulo_camila_dieta()
        elif menu_route == "camila_orientacoes":
            modulo_camila_orientacoes()
        elif menu_route == "camila_evolucao":
            modulo_camila_evolucao()
        elif menu_route == "camila_chat":
            modulo_camila_chat()
        return

    if menu_route == "dashboard":
        modulo_dashboard()
    elif menu_route == "agenda":
        modulo_agenda_pro()
    elif menu_route == "atendimento":
        modulo_atendimento()
    elif menu_route == "consultorio":
        modulo_consultorio_completo()
    elif menu_route == "prescricoes":
        modulo_prescricoes("receituario")
    elif menu_route in ("receituario", "recibo", "receita"):
        modulo_prescricoes("receituario")
    elif menu_route == "pedidos_exames":
        modulo_prescricoes("pedidos_exames")
    elif menu_route == "atestado":
        modulo_atestado()
    elif menu_route == "graficos":
        modulo_graficos()
    elif menu_route == "relatorios":
        modulo_relatorios()
    elif menu_route == "dieta":
        modulo_dieta_ia()
    elif menu_route == "consulta_ia":
        modulo_tabela_ia()
    elif menu_route == "suporte":
        modulo_suporte()
    elif menu_route == "painel_usuario":
        modulo_painel_usuario()
    elif menu_route == "financeiro":
        modulo_financeiro()
    elif menu_route == "biblioteca":
        modulo_biblioteca()
    elif menu_route == "chat":
        modulo_chat()
    elif menu_route == "admin":
        modulo_admin()
    elif menu_route == "portal_dashboard":
        modulo_paciente_dashboard()
    elif menu_route == "portal_consultas":
        modulo_paciente_consultas()
    elif menu_route == "portal_dietas":
        modulo_paciente_dietas()
    elif menu_route == "portal_receitas":
        modulo_paciente_receitas()
    elif menu_route == "portal_exames":
        modulo_paciente_exames()
    elif menu_route == "portal_evolucao":
        modulo_paciente_evolucao()
    elif menu_route == "portal_alimentos":
        modulo_paciente_alimentos()
    elif menu_route == "portal_chat":
        modulo_paciente_chat()
    elif menu_route == "portal_online":
        modulo_paciente_online()
    elif menu_route == "portal_avisos":
        modulo_paciente_avisos()
    elif menu_route == "portal_perfil":
        modulo_paciente_perfil()

if __name__ == "__main__":
    main()
