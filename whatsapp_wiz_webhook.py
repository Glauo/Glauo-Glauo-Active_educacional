import datetime
import json
import os
import re
import threading
import unicodedata
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qsl, quote, urlencode, urlsplit, urlunsplit
import urllib.error
import urllib.request

from openai import OpenAI


DATA_DIR = Path(os.getenv("ACTIVE_DATA_DIR", "./data")).expanduser()
DATA_DIR.mkdir(parents=True, exist_ok=True)

USERS_FILE = DATA_DIR / "users.json"
STUDENTS_FILE = DATA_DIR / "students.json"
CLASSES_FILE = DATA_DIR / "classes.json"
RECEIVABLES_FILE = DATA_DIR / "receivables.json"
CLASS_SESSIONS_FILE = DATA_DIR / "class_sessions.json"
MATERIALS_FILE = DATA_DIR / "materials.json"
MESSAGES_FILE = DATA_DIR / "messages.json"
WIZ_SETTINGS_FILE = DATA_DIR / "wiz_settings.json"
WIZ_WEBHOOK_SEEN_FILE = DATA_DIR / "wiz_whatsapp_seen.json"
WIZ_WEBHOOK_LOG_FILE = DATA_DIR / "wiz_whatsapp_log.json"

DATA_LOCK = threading.Lock()

DEFAULT_WIZ_SETTINGS = {
    "enabled": True,
    "notify_whatsapp": True,
    "mister_wiz_paused": False,
}


def _load_json(path, default):
    with DATA_LOCK:
        if not path.exists():
            return default
        try:
            with path.open("r", encoding="utf-8") as fh:
                data = json.load(fh)
            if isinstance(default, list):
                return data if isinstance(data, list) else list(default)
            if isinstance(default, dict):
                return data if isinstance(data, dict) else dict(default)
            return data
        except Exception:
            return default


def _save_json(path, data):
    with DATA_LOCK:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(path.suffix + ".tmp")
        with tmp.open("w", encoding="utf-8") as fh:
            json.dump(data, fh, ensure_ascii=False, indent=2)
        tmp.replace(path)


def _norm_text(value):
    value = unicodedata.normalize("NFKD", str(value or ""))
    value = "".join(ch for ch in value if not unicodedata.combining(ch))
    return re.sub(r"\s+", " ", value).strip().lower()


def _digits(value):
    return re.sub(r"\D+", "", str(value or ""))


def _normalize_whatsapp_number(value):
    digits = _digits(value)
    if not digits:
        return ""
    if digits.startswith("00"):
        digits = digits[2:]
    if len(digits) in (10, 11):
        digits = "55" + digits
    return digits


def _parse_date(value):
    raw = str(value or "").strip()
    if not raw:
        return None
    for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y", "%Y/%m/%d"):
        try:
            return datetime.datetime.strptime(raw, fmt).date()
        except Exception:
            pass
    return None


def _get_groq_api_key():
    return str(os.getenv("GROQ_API_KEY", "")).strip() or str(os.getenv("ACTIVE_GROQ_API_KEY", "")).strip()


def _get_model_name():
    return str(os.getenv("ACTIVE_WIZ_MODEL", "")).strip() or str(os.getenv("ACTIVE_CHATBOT_MODEL", "llama-3.3-70b-versatile")).strip()


def _wiz_settings():
    data = dict(DEFAULT_WIZ_SETTINGS)
    raw = _load_json(WIZ_SETTINGS_FILE, {})
    if isinstance(raw, dict):
        for key in data:
            if key in raw:
                data[key] = bool(raw.get(key))
    return data


def _save_wiz_settings(data):
    merged = dict(DEFAULT_WIZ_SETTINGS)
    if isinstance(data, dict):
        for key in merged:
            if key in data:
                merged[key] = bool(data.get(key))
    _save_json(WIZ_SETTINGS_FILE, merged)
    return merged


def _wiz_control_command(text):
    norm = _norm_text(text)
    stop_cmds = {"!parar", "parar", "!pausar", "pausar", "assumir controle", "!assumir", "bot parar"}
    resume_cmds = {"!retomar", "retomar", "!continuar", "continuar", "!iniciar", "iniciar bot", "retomar bot"}
    if norm in stop_cmds:
        return "stop"
    if norm in resume_cmds:
        return "resume"
    return ""


def _admin_whatsapp_numbers():
    numbers = set()
    raw_env = (
        str(os.getenv("ACTIVE_ADMIN_WHATSAPP", "")).strip()
        or str(os.getenv("ACTIVE_ADMIN_WHATSAPPS", "")).strip()
        or str(os.getenv("ACTIVE_ADMIN_NUMBERS", "")).strip()
    )
    for chunk in re.split(r"[;, \n]+", raw_env):
        num = _normalize_whatsapp_number(chunk)
        if num:
            numbers.add(num)
    for user in _load_json(USERS_FILE, []):
        if not isinstance(user, dict):
            continue
        if str(user.get("perfil", "")).strip() not in ("Admin", "Coordenador"):
            continue
        num = _normalize_whatsapp_number(user.get("celular", ""))
        if num:
            numbers.add(num)
    return numbers


def _message_matches_student(message_obj, aluno_nome, turma_aluno):
    msg = message_obj if isinstance(message_obj, dict) else {}
    publico = str(msg.get("publico", "Alunos")).strip()
    destinatario_unico = str(msg.get("destinatario_unico", "")).strip()
    aluno_msg = str(msg.get("aluno", "")).strip()
    turma_msg = str(msg.get("turma", "")).strip()
    if publico == "Todos":
        return True
    if destinatario_unico and destinatario_unico == aluno_nome:
        return True
    if aluno_msg and aluno_msg == aluno_nome:
        return True
    if publico == "Alunos" and (not turma_msg or turma_msg == turma_aluno):
        return True
    return False


def _student_by_phone(number):
    normalized = _normalize_whatsapp_number(number)
    if not normalized:
        return {}
    students = _load_json(STUDENTS_FILE, [])
    for student in students:
        if not isinstance(student, dict):
            continue
        own = _normalize_whatsapp_number(student.get("celular", ""))
        resp = _normalize_whatsapp_number((student.get("responsavel", {}) or {}).get("celular", ""))
        if normalized in {own, resp}:
            return student
    return {}


def _student_context(student):
    aluno = student if isinstance(student, dict) else {}
    nome = str(aluno.get("nome", "")).strip()
    turma = str(aluno.get("turma", "")).strip() or "Sem turma"
    livro = str(aluno.get("livro", "")).strip() or "Livro 1"
    receivables = [
        r for r in _load_json(RECEIVABLES_FILE, [])
        if str(r.get("aluno", "")).strip() == nome and str(r.get("categoria_lancamento", "Aluno")).strip() == "Aluno"
    ]
    open_items = [r for r in receivables if str(r.get("status", "")).strip().lower() not in {"pago", "cancelado"}]
    today = datetime.date.today()
    overdue_items = [
        r for r in open_items
        if (_parse_date(r.get("vencimento", "")) or today) < today
    ]
    sessions = [
        s for s in _load_json(CLASS_SESSIONS_FILE, [])
        if str(s.get("turma", "")).strip() == turma and str(s.get("status", "")).strip().lower() == "finalizada"
    ]
    sessions = sorted(
        sessions,
        key=lambda item: _parse_date(item.get("data", "")) or datetime.date(1900, 1, 1),
        reverse=True,
    )[:5]
    session_texts = []
    for session in sessions:
        txt = str(session.get("licao", "")).strip() or str(session.get("resumo_final", "")).strip()
        if txt:
            session_texts.append(txt[:220])
    materials = [
        m for m in _load_json(MATERIALS_FILE, [])
        if str(m.get("turma", "")).strip() in ("", "Todas", turma)
    ][:5]
    material_titles = [str(m.get("titulo", "")).strip() for m in materials if str(m.get("titulo", "")).strip()]
    notices = [
        m for m in _load_json(MESSAGES_FILE, [])
        if _message_matches_student(m, nome, turma)
    ][:5]
    notice_titles = [str(m.get("titulo", "")).strip() for m in notices if str(m.get("titulo", "")).strip()]
    return {
        "nome": nome,
        "turma": turma,
        "livro": livro,
        "responsavel": str((aluno.get("responsavel", {}) or {}).get("nome", "")).strip(),
        "abertas": len(open_items),
        "vencidas": len(overdue_items),
        "a_pagar": sum(float(str(r.get("valor_parcela", r.get("valor", 0))).replace(".", "").replace(",", ".")) if str(r.get("valor_parcela", r.get("valor", 0))).strip() else 0.0 for r in open_items),
        "licoes": session_texts,
        "materiais": material_titles,
        "avisos": notice_titles,
    }


def _extract_text_candidates(obj, found=None):
    found = found or []
    if isinstance(obj, dict):
        for key, value in obj.items():
            key_norm = _norm_text(key)
            if isinstance(value, str) and key_norm in {
                "text", "body", "conversation", "message", "caption", "content", "title"
            }:
                txt = str(value).strip()
                if txt:
                    found.append(txt)
            else:
                _extract_text_candidates(value, found)
    elif isinstance(obj, list):
        for item in obj:
            _extract_text_candidates(item, found)
    return found


def _extract_sender_candidates(obj, found=None):
    found = found or []
    if isinstance(obj, dict):
        for key, value in obj.items():
            key_norm = _norm_text(key)
            if isinstance(value, str) and key_norm in {
                "from", "sender", "phone", "number", "remotejid", "chatid", "author", "participant"
            }:
                digits = _normalize_whatsapp_number(value)
                if digits:
                    found.append(digits)
            else:
                _extract_sender_candidates(value, found)
    elif isinstance(obj, list):
        for item in obj:
            _extract_sender_candidates(item, found)
    return found


def _extract_message_id(obj):
    if isinstance(obj, dict):
        for key in ("id", "messageId", "message_id"):
            value = obj.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
        for value in obj.values():
            msg_id = _extract_message_id(value)
            if msg_id:
                return msg_id
    elif isinstance(obj, list):
        for item in obj:
            msg_id = _extract_message_id(item)
            if msg_id:
                return msg_id
    return ""


def _extract_from_me(obj):
    if isinstance(obj, dict):
        for key in ("fromMe", "from_me", "isFromMe", "self"):
            if key in obj:
                return bool(obj.get(key))
        for value in obj.values():
            flag = _extract_from_me(value)
            if flag:
                return True
    elif isinstance(obj, list):
        for item in obj:
            flag = _extract_from_me(item)
            if flag:
                return True
    return False


def _extract_incoming(payload):
    msg_id = _extract_message_id(payload)
    sender = next(iter(_extract_sender_candidates(payload)), "")
    texts = [txt for txt in _extract_text_candidates(payload) if txt and not txt.startswith("http")]
    text = texts[0].strip() if texts else ""
    from_me = _extract_from_me(payload)
    return {
        "id": msg_id,
        "sender": sender,
        "text": text,
        "from_me": from_me,
        "payload": payload,
    }


def _seen_before(message_key):
    if not message_key:
        return False
    seen = _load_json(WIZ_WEBHOOK_SEEN_FILE, [])
    if message_key in seen:
        return True
    seen.append(message_key)
    seen = seen[-800:]
    _save_json(WIZ_WEBHOOK_SEEN_FILE, seen)
    return False


def _append_log(entry):
    logs = _load_json(WIZ_WEBHOOK_LOG_FILE, [])
    logs.append(entry)
    _save_json(WIZ_WEBHOOK_LOG_FILE, logs[-500:])


def _http_post_json(url, headers, payload, timeout=20):
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=body, method="POST")
    req.add_header("Content-Type", "application/json")
    for key, value in (headers or {}).items():
        req.add_header(str(key), str(value))
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read()
            return int(resp.status), raw.decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        raw = exc.read() if hasattr(exc, "read") else b""
        return int(exc.code), raw.decode("utf-8", errors="replace")
    except Exception as exc:
        return None, str(exc)


def _send_whatsapp_wapi(number, text):
    number = _normalize_whatsapp_number(number)
    base_url = str(os.getenv("WAPI_BASE_URL", "")).strip()
    token = str(os.getenv("WAPI_TOKEN", "")).strip()
    instance_id = str(os.getenv("WAPI_INSTANCE_ID", "")).strip() or str(os.getenv("WAPI_INSTANCE", "")).strip()
    if not (number and text and base_url and token and instance_id):
        return False, "WAPI incompleto"
    split = urlsplit(base_url)
    base_root = urlunsplit((split.scheme, split.netloc, "", "", "")).rstrip("/")
    inst_q = quote(instance_id, safe="")
    candidates = [
        f"{base_root}/v1/message/send-text?instanceId={inst_q}",
        f"{base_root}/api/v1/message/send-text?instanceId={inst_q}",
        f"{base_root}/message/send-text?instanceId={inst_q}",
        f"{base_root}/v1/messages/send-text?instanceId={inst_q}",
    ]
    payloads = [
        {"phone": number, "message": text},
        {"number": number, "message": text},
        {"to": number, "text": text},
        {"instanceId": instance_id, "phone": number, "message": text},
    ]
    header_sets = [
        {"Authorization": token if token.lower().startswith("bearer ") else f"Bearer {token}", "Accept": "application/json"},
        {"apikey": token, "Accept": "application/json"},
        {"x-api-key": token, "Accept": "application/json"},
    ]
    for url in candidates:
        for headers in header_sets:
            for payload in payloads:
                status, body = _http_post_json(url, headers, payload, timeout=20)
                if status is not None and 200 <= int(status) < 300:
                    return True, f"enviado HTTP {status}"
                text_preview = str(body or "")[:180].lower()
                if any(token_ok in text_preview for token_ok in ("success", "sucesso", "sent")):
                    return True, text_preview
    return False, "falha ao enviar via WAPI"


def _general_context():
    classes = _load_json(CLASSES_FILE, [])
    students = _load_json(STUDENTS_FILE, [])
    return (
        f"Escola de inglês Active Educacional / Mister Wiz. "
        f"Turmas cadastradas: {len(classes)}. "
        f"Alunos cadastrados: {len(students)}."
    )


def _build_prompt(sender, text):
    student = _student_by_phone(sender)
    if student:
        ctx = _student_context(student)
        base = [
            "Você é o Bot Mister Wiz da escola de inglês Mister Wiz.",
            "Responda em português do Brasil, com clareza e objetividade.",
            "Atenda como assistente escolar oficial pelo WhatsApp.",
            "Nunca invente dados do sistema.",
            "Quando não houver dado confirmado, diga isso claramente.",
            "Se o assunto for financeiro, seja respeitoso e direto.",
            "Se o aluno pedir algo pedagógico, oriente com foco em inglês.",
            f"Aluno identificado: {ctx['nome']}.",
            f"Turma: {ctx['turma']}.",
            f"Livro/Nível: {ctx['livro']}.",
            f"Lançamentos em aberto: {ctx['abertas']}.",
            f"Lançamentos vencidos: {ctx['vencidas']}.",
        ]
        if ctx["responsavel"]:
            base.append(f"Responsável financeiro: {ctx['responsavel']}.")
        if ctx["licoes"]:
            base.append("Lições recentes: " + " | ".join(ctx["licoes"]))
        if ctx["materiais"]:
            base.append("Materiais recentes: " + " | ".join(ctx["materiais"]))
        if ctx["avisos"]:
            base.append("Avisos ativos: " + " | ".join(ctx["avisos"]))
        return "\n".join(base), student
    base = [
        "Você é o Bot Mister Wiz da escola de inglês Mister Wiz.",
        "Responda em português do Brasil, de forma simples, útil e profissional.",
        "Atenda como recepção/secretaria escolar pelo WhatsApp.",
        "Nunca invente dados do sistema.",
        "Se a pessoa pedir algo que depende de cadastro interno não identificado, peça nome completo e turma.",
        _general_context(),
    ]
    return "\n".join(base), {}


def _generate_reply(sender, text):
    api_key = _get_groq_api_key()
    if not api_key:
        return "O atendimento automático está temporariamente indisponível. Por favor, fale com a secretaria da escola."
    system_prompt, student = _build_prompt(sender, text)
    client = OpenAI(api_key=api_key, base_url="https://api.groq.com/openai/v1")
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": str(text or "").strip()},
    ]
    result = client.chat.completions.create(
        model=_get_model_name(),
        messages=messages,
        temperature=0.2,
        max_tokens=700,
    )
    answer = (result.choices[0].message.content or "").strip()
    if not answer:
        answer = "Não consegui responder agora. Envie novamente com mais detalhes."
    if student and _norm_text(text) in {"oi", "ola", "olá", "bom dia", "boa tarde", "boa noite"}:
        answer = f"Olá, {str(student.get('nome', '')).strip()}! {answer}"
    return answer


def _authorized_request(handler):
    required = str(os.getenv("ACTIVE_WIZ_WEBHOOK_TOKEN", "")).strip()
    if not required:
        return True
    header_token = str(handler.headers.get("X-Webhook-Token", "")).strip()
    url_token = ""
    try:
        url_token = dict(parse_qsl(urlsplit(handler.path).query)).get("token", "")
    except Exception:
        url_token = ""
    return required == header_token or required == str(url_token).strip()


class WizWebhookHandler(BaseHTTPRequestHandler):
    server_version = "WizWebhook/1.0"

    def _write_json(self, status_code, payload):
        raw = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(int(status_code))
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def do_GET(self):
        if self.path.startswith("/health"):
            self._write_json(200, {"ok": True, "service": "wiz-whatsapp-webhook"})
            return
        if self.path.startswith("/wapi/webhook"):
            self._write_json(200, {"ok": True, "message": "Webhook ativo"})
            return
        self._write_json(404, {"ok": False, "message": "Not found"})

    def do_POST(self):
        if not self.path.startswith("/wapi/webhook"):
            self._write_json(404, {"ok": False, "message": "Not found"})
            return
        if not _authorized_request(self):
            self._write_json(403, {"ok": False, "message": "Token inválido"})
            return
        length = int(self.headers.get("Content-Length", "0") or "0")
        body = self.rfile.read(length) if length > 0 else b"{}"
        try:
            payload = json.loads(body.decode("utf-8", errors="replace") or "{}")
        except Exception:
            self._write_json(400, {"ok": False, "message": "JSON inválido"})
            return
        incoming = _extract_incoming(payload)
        sender = incoming.get("sender", "")
        text = str(incoming.get("text", "")).strip()
        msg_id = str(incoming.get("id", "")).strip()
        from_me = bool(incoming.get("from_me"))
        message_key = msg_id or f"{sender}:{_norm_text(text)}"

        if from_me or not sender or not text:
            self._write_json(200, {"ok": True, "ignored": True, "reason": "without text or from me"})
            return
        if _seen_before(message_key):
            self._write_json(200, {"ok": True, "ignored": True, "reason": "duplicate"})
            return

        settings = _wiz_settings()
        cmd = _wiz_control_command(text)
        if sender in _admin_whatsapp_numbers() and cmd:
            settings["mister_wiz_paused"] = (cmd == "stop")
            _save_wiz_settings(settings)
            reply = "Bot Mister Wiz pausado. Atendimento humano assumido." if cmd == "stop" else "Bot Mister Wiz retomado e ativo."
            ok_send, status_send = _send_whatsapp_wapi(sender, reply)
            _append_log({
                "date": datetime.datetime.now().isoformat(),
                "sender": sender,
                "text": text,
                "reply": reply,
                "status": status_send,
                "control": cmd,
            })
            self._write_json(200, {"ok": ok_send, "message": status_send, "control": cmd})
            return

        if not settings.get("enabled", True) or settings.get("mister_wiz_paused", False):
            self._append_log({
                "date": datetime.datetime.now().isoformat(),
                "sender": sender,
                "text": text,
                "reply": "",
                "status": "bot pausado",
            })
            self._write_json(200, {"ok": True, "ignored": True, "reason": "bot paused"})
            return

        try:
            reply = _generate_reply(sender, text)
        except Exception as exc:
            reply = f"Não consegui responder agora. Erro temporário do atendimento automático: {exc}"
        ok_send, status_send = _send_whatsapp_wapi(sender, reply)
        _append_log({
            "date": datetime.datetime.now().isoformat(),
            "sender": sender,
            "text": text,
            "reply": reply,
            "status": status_send,
        })
        self._write_json(200, {"ok": ok_send, "message": status_send})

    def log_message(self, fmt, *args):
        return


def main():
    host = str(os.getenv("WIZ_WEBHOOK_HOST", "0.0.0.0")).strip() or "0.0.0.0"
    port = int(str(os.getenv("WIZ_WEBHOOK_PORT", "8787")).strip() or "8787")
    server = ThreadingHTTPServer((host, port), WizWebhookHandler)
    print(f"Wiz WhatsApp webhook listening on {host}:{port}", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
