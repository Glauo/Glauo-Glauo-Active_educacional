import datetime
import json
import os
import re
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qsl, quote, urlencode, urlsplit
import urllib.error
import urllib.request

from openai import OpenAI


def _norm_text(value):
    return re.sub(r"\s+", " ", str(value or "")).strip().lower()


def _digits(value):
    return re.sub(r"\D+", "", str(value or ""))


def _normalize_whatsapp_number(value):
    raw = str(value or "").strip()
    if not raw:
        return ""
    match = re.search(r"(\d{10,15})", raw)
    digits = match.group(1) if match else _digits(raw)
    if not digits:
        return ""
    if digits.startswith("00"):
        digits = digits[2:]
    if len(digits) in (10, 11):
        digits = "55" + digits
    return digits


def _get_groq_api_key():
    return str(os.getenv("GROQ_API_KEY", "")).strip() or str(os.getenv("ACTIVE_GROQ_API_KEY", "")).strip()


def _get_model_name():
    return str(os.getenv("ACTIVE_WIZ_MODEL", "")).strip() or str(os.getenv("ACTIVE_CHATBOT_MODEL", "llama-3.3-70b-versatile")).strip()


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
    raw = (
        str(os.getenv("ACTIVE_ADMIN_WHATSAPP", "")).strip()
        or str(os.getenv("ACTIVE_ADMIN_WHATSAPPS", "")).strip()
        or str(os.getenv("ACTIVE_ADMIN_NUMBERS", "")).strip()
    )
    for chunk in re.split(r"[;, \n]+", raw):
        num = _normalize_whatsapp_number(chunk)
        if num:
            numbers.add(num)
    return numbers


def _extract_text_candidates(obj, found=None):
    found = found or []
    if isinstance(obj, dict):
        for key, value in obj.items():
            key_norm = _norm_text(key)
            if isinstance(value, str) and key_norm in {"text", "body", "conversation", "message", "caption", "content", "title"}:
                txt = str(value).strip()
                if txt:
                    found.append(txt)
            elif isinstance(value, dict) and key_norm in {
                "messagedata",
                "textmessagedata",
                "extendedtextmessagedata",
                "imagemessagedata",
                "videomessagedata",
                "documentmessagedata",
                "quotedmessage",
                "senderdata",
                "msgcontent",
                "messagecontextinfo",
            }:
                _extract_text_candidates(value, found)
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
            if isinstance(value, str) and key_norm in {"from", "sender", "phone", "number", "remotejid", "chatid", "author", "participant"}:
                num = _normalize_whatsapp_number(value)
                if num:
                    found.append(num)
            elif isinstance(value, dict) and key_norm in {"senderdata", "key", "chat", "contact"}:
                _extract_sender_candidates(value, found)
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
            nested = _extract_message_id(value)
            if nested:
                return nested
    elif isinstance(obj, list):
        for item in obj:
            nested = _extract_message_id(item)
            if nested:
                return nested
    return ""


def _extract_from_me(obj):
    if isinstance(obj, dict):
        for key in ("fromMe", "from_me", "isFromMe", "self"):
            if key in obj:
                return bool(obj.get(key))
        for value in obj.values():
            if _extract_from_me(value):
                return True
    elif isinstance(obj, list):
        for item in obj:
            if _extract_from_me(item):
                return True
    return False


def _extract_incoming(payload):
    sender = ""
    texts = [t for t in _extract_text_candidates(payload) if t and not t.startswith("http")]
    if isinstance(payload, dict):
        connected_phone = _normalize_whatsapp_number(payload.get("connectedPhone", ""))
        sender = (
            _normalize_whatsapp_number(payload.get("sender", ""))
            or _normalize_whatsapp_number(payload.get("from", ""))
            or _normalize_whatsapp_number(((payload.get("chat") or {}).get("id", "")))
        )
        sender_data = payload.get("senderData") or payload.get("sender_data") or {}
        if not sender and isinstance(sender_data, dict):
            sender = (
                _normalize_whatsapp_number(sender_data.get("chatId", ""))
                or _normalize_whatsapp_number(sender_data.get("sender", ""))
                or _normalize_whatsapp_number(sender_data.get("remoteJid", ""))
                or _normalize_whatsapp_number(sender_data.get("from", ""))
            )
        message_data = payload.get("messageData") or payload.get("message_data") or {}
        if isinstance(message_data, dict) and not texts:
            direct_candidates = [
                message_data.get("conversation", ""),
                ((message_data.get("textMessageData") or {}).get("textMessage", "")),
                ((message_data.get("extendedTextMessageData") or {}).get("text", "")),
                ((message_data.get("imageMessageData") or {}).get("caption", "")),
                ((message_data.get("videoMessageData") or {}).get("caption", "")),
                ((message_data.get("documentMessageData") or {}).get("caption", "")),
                ((message_data.get("buttonsResponseMessage") or {}).get("selectedDisplayText", "")),
                ((message_data.get("listResponseMessage") or {}).get("title", "")),
            ]
            texts = [str(x).strip() for x in direct_candidates if str(x).strip()]
        msg_content = payload.get("msgContent") or payload.get("msgcontent") or {}
        if isinstance(msg_content, dict) and not texts:
            direct_candidates = [
                msg_content.get("conversation", ""),
                ((msg_content.get("extendedTextMessage") or {}).get("text", "")),
                ((msg_content.get("imageMessage") or {}).get("caption", "")),
                ((msg_content.get("videoMessage") or {}).get("caption", "")),
                ((msg_content.get("documentMessage") or {}).get("caption", "")),
                ((msg_content.get("buttonsResponseMessage") or {}).get("selectedDisplayText", "")),
                ((msg_content.get("listResponseMessage") or {}).get("title", "")),
            ]
            texts = [str(x).strip() for x in direct_candidates if str(x).strip()]
        key_obj = payload.get("key") or {}
        if not sender and isinstance(key_obj, dict):
            sender = (
                _normalize_whatsapp_number(key_obj.get("remoteJid", ""))
                or _normalize_whatsapp_number(key_obj.get("participant", ""))
            )
        if not sender:
            candidates = [
                num
                for num in _extract_sender_candidates(payload)
                if num and (not connected_phone or num != connected_phone)
            ]
            sender = next(iter(candidates), "")
    return {
        "id": _extract_message_id(payload),
        "sender": sender,
        "text": texts[0].strip() if texts else "",
        "from_me": _extract_from_me(payload),
    }


def _http_post_json(url, headers, payload, timeout=20):
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=body, method="POST")
    req.add_header("Content-Type", "application/json")
    for key, value in (headers or {}).items():
        req.add_header(str(key), str(value))
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return int(resp.status), resp.read().decode("utf-8", errors="replace")
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
    base_root = f"{split.scheme}://{split.netloc}".rstrip("/")
    inst_q = quote(instance_id, safe="")
    urls = [
        f"{base_root}/v1/message/send-text?instanceId={inst_q}",
        f"{base_root}/api/v1/message/send-text?instanceId={inst_q}",
        f"{base_root}/message/send-text?instanceId={inst_q}",
    ]
    payloads = [
        {"phone": number, "message": text},
        {"number": number, "message": text},
        {"to": number, "text": text},
        {"instanceId": instance_id, "phone": number, "message": text},
    ]
    headers_list = [
        {"Authorization": token if token.lower().startswith("bearer ") else f"Bearer {token}", "Accept": "application/json"},
        {"apikey": token, "Accept": "application/json"},
        {"x-api-key": token, "Accept": "application/json"},
    ]
    for url in urls:
        for headers in headers_list:
            for payload in payloads:
                status, body = _http_post_json(url, headers, payload)
                print(
                    f"[wizbot] send attempt url={url} status={status} phone={number} preview={str(body or '')[:160]}",
                    flush=True,
                )
                if status is not None and 200 <= int(status) < 300:
                    return True, f"enviado HTTP {status}"
                preview = str(body or "").lower()[:160]
                if any(flag in preview for flag in ("success", "sucesso", "sent")):
                    return True, preview
    return False, "falha ao enviar via WAPI"


def _generate_reply(sender, text):
    api_key = _get_groq_api_key()
    user_text = str(text or "").strip()
    user_norm = _norm_text(user_text)
    if user_norm in {"oi", "ola", "olá", "bom dia", "boa tarde", "boa noite", "menu", "inicio", "início"}:
        return (
            "Olá! Você está falando com o atendimento da Mister Wiz.\n\n"
            "Posso ajudar com informações sobre secretaria, financeiro, agenda, portal do aluno e dúvidas gerais da escola.\n\n"
            "Se quiser, me diga em uma frase o que você precisa."
        )
    if not api_key:
        return (
            "O atendimento automático do Mister Wiz está temporariamente indisponível. "
            "Por favor, envie sua dúvida novamente em alguns minutos."
        )
    system_prompt = "\n".join(
        [
            "Voce e o Bot Mister Wiz da escola de ingles Mister Wiz.",
            "Atenda pelo WhatsApp em portugues do Brasil.",
            "Responda de forma objetiva, educada e profissional.",
            "Quando for uma primeira saudacao, responda de forma curta, clara e acolhedora.",
            "Ajude com duvidas sobre escola, ingles, secretaria, agenda, financeiro e portal.",
            "Quando nao tiver dados confirmados, diga isso com clareza.",
            "Nunca invente informacoes internas.",
            f"Numero remetente identificado: {sender}.",
        ]
    )
    client = OpenAI(api_key=api_key, base_url="https://api.groq.com/openai/v1")
    result = client.chat.completions.create(
        model=_get_model_name(),
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_text},
        ],
        temperature=0.2,
        max_tokens=700,
    )
    answer = (result.choices[0].message.content or "").strip()
    return answer or "Nao consegui responder agora. Tente novamente com mais detalhes."


def _authorized_request(handler):
    required = str(os.getenv("ACTIVE_WIZ_WEBHOOK_TOKEN", "")).strip()
    if not required:
        return True
    header_token = str(handler.headers.get("X-Webhook-Token", "")).strip()
    query = dict(parse_qsl(urlsplit(handler.path).query))
    return required == header_token or required == str(query.get("token", "")).strip()


class WizWebhookHandler(BaseHTTPRequestHandler):
    server_version = "WizbotStandalone/1.0"

    def _write_json(self, status_code, payload):
        raw = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(int(status_code))
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def do_GET(self):
        print(f"[wizbot] GET path={self.path}", flush=True)
        if self.path.startswith("/health"):
            self._write_json(200, {"ok": True, "service": "wizbot-standalone"})
            return
        if self.path.startswith("/wapi/webhook"):
            self._write_json(200, {"ok": True, "message": "Webhook ativo"})
            return
        self._write_json(404, {"ok": False, "message": "Not found"})

    def do_POST(self):
        print(f"[wizbot] POST path={self.path}", flush=True)
        if not self.path.startswith("/wapi/webhook"):
            self._write_json(404, {"ok": False, "message": "Not found"})
            return
        if not _authorized_request(self):
            print("[wizbot] token invalido", flush=True)
            self._write_json(403, {"ok": False, "message": "Token invalido"})
            return
        length = int(self.headers.get("Content-Length", "0") or "0")
        body = self.rfile.read(length) if length > 0 else b"{}"
        try:
            payload = json.loads(body.decode("utf-8", errors="replace") or "{}")
        except Exception:
            print(f"[wizbot] json invalido body={body[:200]}", flush=True)
            self._write_json(400, {"ok": False, "message": "JSON invalido"})
            return
        incoming = _extract_incoming(payload)
        sender = incoming.get("sender", "")
        text = str(incoming.get("text", "")).strip()
        print(
            f"[wizbot] incoming sender={sender} from_me={incoming.get('from_me')} text={text[:200]}",
            flush=True,
        )
        if not sender or not text or incoming.get("from_me"):
            print(f"[wizbot] raw payload={body.decode('utf-8', errors='replace')[:1500]}", flush=True)
            print("[wizbot] ignored incoming", flush=True)
            self._write_json(200, {"ok": True, "ignored": True})
            return
        cmd = _wiz_control_command(text)
        if sender in _admin_whatsapp_numbers() and cmd:
            reply = "Bot Mister Wiz pausado." if cmd == "stop" else "Bot Mister Wiz retomado."
            ok_send, status_send = _send_whatsapp_wapi(sender, reply)
            print(f"[wizbot] admin control cmd={cmd} ok={ok_send} status={status_send}", flush=True)
            self._write_json(200, {"ok": ok_send, "message": status_send, "control": cmd})
            return
        try:
            reply = _generate_reply(sender, text)
        except Exception as exc:
            reply = f"Nao consegui responder agora. Erro temporario: {exc}"
            print(f"[wizbot] ai error={exc}", flush=True)
        ok_send, status_send = _send_whatsapp_wapi(sender, reply)
        print(f"[wizbot] reply ok={ok_send} status={status_send} text={reply[:200]}", flush=True)
        self._write_json(200, {"ok": ok_send, "message": status_send})

    def log_message(self, fmt, *args):
        return


def main():
    host = str(os.getenv("WIZ_WEBHOOK_HOST", "0.0.0.0")).strip() or "0.0.0.0"
    port = int(str(os.getenv("WIZ_WEBHOOK_PORT", "8787")).strip() or "8787")
    server = ThreadingHTTPServer((host, port), WizWebhookHandler)
    print(f"Wizbot standalone listening on {host}:{port}", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
