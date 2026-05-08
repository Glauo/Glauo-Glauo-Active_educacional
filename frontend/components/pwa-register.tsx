"use client";

import { useEffect } from "react";

export function PWARegister() {
  useEffect(() => {
    if ("serviceWorker" in navigator) {
      if ("caches" in window) {
        caches
          .keys()
          .then((keys) => Promise.all(keys.filter((key) => key.startsWith("ativo-edu-") && !key.startsWith("ativo-edu-v3")).map((key) => caches.delete(key))))
          .catch(() => {});
      }

      navigator.serviceWorker
        .register("/sw.js")
        .then((registration) => registration.update())
        .catch(() => {});
    }
  }, []);

  return null;
}
