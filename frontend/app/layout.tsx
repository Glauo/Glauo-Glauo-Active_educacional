import type { Metadata, Viewport } from "next";
import "./globals.css";
import { PWARegister } from "@/components/pwa-register";
import { AppRecovery } from "@/components/app-recovery";

export const metadata: Metadata = {
  title: {
    template: "%s | Ativo Educacional",
    default: "Ativo Educacional - Sistema de Gestao Educacional"
  },
  description: "Plataforma completa de gestão educacional: alunos, turmas, professores, financeiro e muito mais.",
  manifest: "/manifest.json",
  appleWebApp: {
    capable: true,
    statusBarStyle: "black-translucent",
    title: "Ativo Edu"
  },
  icons: {
    icon: [
      { url: "/icons/icon-192.png", sizes: "192x192", type: "image/png" },
      { url: "/icons/icon-512.png", sizes: "512x512", type: "image/png" }
    ],
    apple: [
      { url: "/icons/apple-touch-icon.png", sizes: "180x180", type: "image/png" }
    ]
  },
  other: {
    "mobile-web-app-capable": "yes"
  }
};

export const viewport: Viewport = {
  themeColor: "#0a1628",
  width: "device-width",
  initialScale: 1,
  maximumScale: 1,
  userScalable: false
};

export default function RootLayout({
  children
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="pt-BR">
      <head>
        <script
          dangerouslySetInnerHTML={{
            __html: `(() => { try { if ("serviceWorker" in navigator) { navigator.serviceWorker.getRegistrations().then((regs) => regs.forEach((reg) => reg.unregister())); } if ("caches" in window) { caches.keys().then((keys) => keys.filter((key) => key.startsWith("ativo-edu-")).forEach((key) => caches.delete(key))); } } catch (_) {} })();`,
          }}
        />
        <link rel="apple-touch-icon" href="/icons/apple-touch-icon.png" />
        <meta name="apple-mobile-web-app-capable" content="yes" />
        <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent" />
        <meta name="apple-mobile-web-app-title" content="Ativo Edu" />
        <meta name="application-name" content="Ativo Educacional" />
        <meta name="msapplication-TileColor" content="#0a1628" />
        <meta name="msapplication-TileImage" content="/icons/icon-192.png" />
      </head>
      <body>
        <PWARegister />
        <AppRecovery />
        {children}
      </body>
    </html>
  );
}
