"use client";

import { useEffect } from "react";

export function PWARegister() {
  useEffect(() => {
    if ("caches" in window) {
      caches
        .keys()
        .then((keys) => Promise.all(keys.filter((key) => key.startsWith("ativo-edu-")).map((key) => caches.delete(key))))
        .catch(() => {});
    }

    if ("serviceWorker" in navigator) {
      navigator.serviceWorker
        .getRegistrations()
        .then((registrations) => Promise.all(registrations.map((registration) => registration.unregister())))
        .catch(() => {});
    }
  }, []);

  return null;
}
