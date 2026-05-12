"use client";

import { useEffect } from "react";

const RELOAD_KEY = "active_last_chunk_reload";

function isChunkOrCacheError(reason: unknown) {
  const message = String(
    reason instanceof Error
      ? reason.message
      : typeof reason === "object" && reason !== null && "message" in reason
        ? (reason as { message?: unknown }).message
        : reason || ""
  ).toLowerCase();

  return message.includes("chunk") ||
    message.includes("failed to fetch dynamically imported module") ||
    message.includes("loading css chunk") ||
    message.includes("could not load");
}

async function clearAppCaches() {
  if (!("caches" in window)) return;
  const keys = await caches.keys();
  await Promise.all(keys.filter((key) => key.startsWith("ativo-edu-")).map((key) => caches.delete(key)));
}

function reloadOnce() {
  const last = Number(sessionStorage.getItem(RELOAD_KEY) || "0");
  if (Date.now() - last < 15000) return;
  sessionStorage.setItem(RELOAD_KEY, String(Date.now()));
  void clearAppCaches().finally(() => window.location.reload());
}

export function AppRecovery() {
  useEffect(() => {
    function onUnhandled(event: PromiseRejectionEvent) {
      if (isChunkOrCacheError(event.reason)) reloadOnce();
    }

    function onError(event: ErrorEvent) {
      if (isChunkOrCacheError(event.error || event.message)) reloadOnce();
    }

    window.addEventListener("unhandledrejection", onUnhandled);
    window.addEventListener("error", onError);
    return () => {
      window.removeEventListener("unhandledrejection", onUnhandled);
      window.removeEventListener("error", onError);
    };
  }, []);

  return null;
}
