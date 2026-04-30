import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: {
    template: "%s | Active Educacional",
    default: "Active Educacional — Sistema de Gestão Premium"
  },
  description: "Plataforma completa de gestão educacional: alunos, turmas, professores, financeiro e muito mais.",
  icons: {
    icon: "/favicon.ico"
  }
};

export default function RootLayout({
  children
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="pt-BR">
      <body>{children}</body>
    </html>
  );
}
