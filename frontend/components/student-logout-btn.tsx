"use client";

export function StudentLogoutBtn() {
  async function handleLogout() {
    await fetch("/api/auth", { method: "DELETE" });
    window.location.href = "/aluno/login";
  }

  return (
    <button
      onClick={handleLogout}
      style={{
        background: "none",
        border: "none",
        color: "rgba(255,255,255,0.6)",
        fontSize: "0.8125rem",
        cursor: "pointer",
        padding: 0
      }}
    >
      Sair
    </button>
  );
}
