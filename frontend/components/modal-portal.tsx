"use client";

import { useEffect, useState } from "react";
import { createPortal } from "react-dom";

let openModals = 0;
let lockedScrollY = 0;
let previousBodyStyles: Partial<CSSStyleDeclaration> = {};

export function ModalPortal({ children }: { children: React.ReactNode }) {
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);

    if (openModals === 0) {
      lockedScrollY = window.scrollY;
      previousBodyStyles = {
        overflow: document.body.style.overflow,
        position: document.body.style.position,
        top: document.body.style.top,
        width: document.body.style.width,
      };
      document.body.style.overflow = "hidden";
      document.body.style.position = "fixed";
      document.body.style.top = `-${lockedScrollY}px`;
      document.body.style.width = "100%";
    }

    openModals += 1;

    return () => {
      openModals = Math.max(0, openModals - 1);
      if (openModals === 0) {
        document.body.style.overflow = previousBodyStyles.overflow || "";
        document.body.style.position = previousBodyStyles.position || "";
        document.body.style.top = previousBodyStyles.top || "";
        document.body.style.width = previousBodyStyles.width || "";
        window.scrollTo(0, lockedScrollY);
      }
    };
  }, []);

  if (!mounted) return null;
  return createPortal(children, document.body);
}
