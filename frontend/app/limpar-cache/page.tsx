"use client";

import { useEffect, useState } from "react";

async function clearActiveCache() {
  if ("caches" in window) {
    const keys = await caches.keys();
    await Promise.all(keys.filter((key) => key.startsWith("ativo-edu-")).map((key) => caches.delete(key)));
  }

  if ("serviceWorker" in navigator) {
    const registrations = await navigator.serviceWorker.getRegistrations();
    await Promise.all(registrations.map((registration) => registration.unregister()));
  }
}

export default function LimparCachePage() {
  const [status, setStatus] = useState("Limpando cache do sistema...");

  useEffect(() => {
    clearActiveCache()
      .then(() => {
        setStatus("Cache limpo. Redirecionando...");
        window.setTimeout(() => {
          window.location.replace("/login");
        }, 900);
      })
      .catch(() => {
        setStatus("Nao foi possivel limpar automaticamente. Use Ctrl + F5 e tente novamente.");
      });
  }, []);

  return (
    <main className="flex min-h-screen items-center justify-center bg-slate-50 px-6 text-slate-950">
      <section className="w-full max-w-md rounded-2xl border border-slate-200 bg-white p-8 text-center shadow-sm">
        <p className="text-xs font-bold uppercase tracking-[0.24em] text-blue-600">Ativo Educacional</p>
        <h1 className="mt-3 text-2xl font-black">Reparando acesso</h1>
        <p className="mt-3 text-sm leading-6 text-slate-600">{status}</p>
      </section>
    </main>
  );
}
