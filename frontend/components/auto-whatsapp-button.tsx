"use client";

import { CSSProperties, useState } from "react";

type Props = {
  phone: unknown;
  message: string;
  label?: string;
  className?: string;
  style?: CSSProperties;
};

function text(value: unknown) {
  return String(value || "").trim();
}

export function AutoWhatsAppButton({
  phone,
  message,
  label = "WhatsApp",
  className = "btn btn-secondary btn-sm",
  style,
}: Props) {
  const [sending, setSending] = useState(false);
  const telefone = text(phone);

  async function send() {
    if (!telefone || sending) return;
    setSending(true);
    try {
      const res = await fetch("/api/whatsapp/send", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ telefone, mensagem: message }),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok || !data.ok) {
        alert(`WhatsApp nao enviado automaticamente: ${String(data.status || data.error || "verifique a WAPI")}`);
      }
    } catch {
      alert("Erro ao enviar WhatsApp automatico.");
    } finally {
      setSending(false);
    }
  }

  return (
    <button className={className} style={style} type="button" onClick={send} disabled={!telefone || sending}>
      {sending ? "Enviando..." : label}
    </button>
  );
}
