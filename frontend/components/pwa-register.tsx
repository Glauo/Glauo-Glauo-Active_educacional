"use client";

import { useEffect } from "react";

export function PWARegister() {
  useEffect(() => {
    const clearCaches = () => {
      if (!("caches" in window)) return Promise.resolve();
      return caches
        .keys()
        .then((keys) => Promise.all(keys.filter((key) => key.startsWith("ativo-edu-")).map((key) => caches.delete(key))));
    };

    const unregisterWorkers = () => {
      if (!("serviceWorker" in navigator)) return Promise.resolve();
      return navigator.serviceWorker
        .getRegistrations()
        .then((registrations) => Promise.all(registrations.map((registration) => registration.unregister())));
    };

    Promise.all([clearCaches(), unregisterWorkers()])
      .then(() => {
        if (!("serviceWorker" in navigator) || !navigator.serviceWorker.controller) return;
        const key = "active_sw_cleanup_reload";
        const last = Number(sessionStorage.getItem(key) || "0");
        if (Date.now() - last < 15000) return;
        sessionStorage.setItem(key, String(Date.now()));
        window.location.reload();
      })
      .catch(() => {});
  }, []);

  return null;
}
