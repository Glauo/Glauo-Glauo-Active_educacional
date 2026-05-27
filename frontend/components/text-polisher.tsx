"use client";

import { useEffect } from "react";
import { polishPortugueseText } from "@/lib/portuguese-text";

const TEXT_ATTRS = ["placeholder", "title", "aria-label", "alt"];
const IGNORED_TAGS = new Set(["SCRIPT", "STYLE", "TEXTAREA", "CODE", "PRE", "NOSCRIPT"]);

function polishNode(node: Node) {
  if (node.nodeType === Node.TEXT_NODE) {
    const current = node.nodeValue || "";
    const polished = polishPortugueseText(current);
    if (polished !== current) node.nodeValue = polished;
    return;
  }

  if (node.nodeType !== Node.ELEMENT_NODE) return;
  const element = node as Element;
  if (IGNORED_TAGS.has(element.tagName) || element.closest("[data-no-text-polish]")) return;

  for (const attr of TEXT_ATTRS) {
    const current = element.getAttribute(attr);
    if (!current) continue;
    const polished = polishPortugueseText(current);
    if (polished !== current) element.setAttribute(attr, polished);
  }

  const walker = document.createTreeWalker(element, NodeFilter.SHOW_TEXT, {
    acceptNode(textNode) {
      const parent = textNode.parentElement;
      if (!parent || IGNORED_TAGS.has(parent.tagName) || parent.closest("[data-no-text-polish]")) {
        return NodeFilter.FILTER_REJECT;
      }
      return NodeFilter.FILTER_ACCEPT;
    },
  });

  const textNodes: Text[] = [];
  while (walker.nextNode()) textNodes.push(walker.currentNode as Text);
  textNodes.forEach(polishNode);
}

export function TextPolisher() {
  useEffect(() => {
    polishNode(document.body);
    const observer = new MutationObserver((mutations) => {
      for (const mutation of mutations) {
        if (mutation.type === "characterData") polishNode(mutation.target);
        mutation.addedNodes.forEach(polishNode);
        if (mutation.type === "attributes") polishNode(mutation.target);
      }
    });
    observer.observe(document.body, {
      childList: true,
      subtree: true,
      characterData: true,
      attributes: true,
      attributeFilter: TEXT_ATTRS,
    });
    return () => observer.disconnect();
  }, []);

  return null;
}
