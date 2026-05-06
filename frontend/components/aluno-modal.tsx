"use client";

import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { BOOK_LEVELS, COURSE_MODULES, formatModuleValue, isVipModule, teacherClassValueByModule, vipPlanTotal } from "@/lib/course-modules";

type AlunoData = {
  id?: string;
  nome?: string;
  name?: string;
  turma?: string;
  classe?: string;
  livro?: string;
  book?: string;
  modulo?: string;
  modalidade?: string;
  responsavel?: unknown;
  responsavel_nome?: string;
  responsavel_cpf?: string;
  responsavel_email?: string;
  responsavel_telefone?: string;
  telefone?: string;
  celular?: string;
  email?: string;
  data_nascimento?: string;
  nascimento?: string;
  cpf?: string;
  endereco?: string;
  dia_vencimento?: string | number;
  vencimento?: string;
  valor_mensalidade?: string | number;
  vip_tipo_plano?: string;
  vip_aulas_total?: string | number;
  vip_aulas_restantes?: string | number;
  observacoes?: string;
  login?: string;
  senha?: string;
  status?: string;
  [k: string]: unknown;
};

type Form = {
  nome: string;
  turma: string;
  modulo: string;
  livro: string;
  data_nascimento: string;
  cpf: string;
  responsavel_nome: string;
  responsavel_cpf: string;
  responsavel_telefone: string;
  responsavel_email: string;
  telefone: string;
  email: string;
  endereco: string;
  dia_vencimento: string;
  vencimento: string;
  valor_mensalidade: string;
  vip_tipo_plano: string;
  vip_aulas_total: string;
  vip_aulas_restantes: string;
  observacoes: string;
  login: string;
  senha: string;
  status: string;
};

type TurmaOption = {
  id?: string;
  nome?: string;
  name?: string;
  livro?: string;
  book?: string;
  modulo?: string;
  tipo_aula?: string;
  modalidade?: string;
  [k: string]: unknown;
};

function text(value: unknown) {
  if (value && typeof value === "object" && !Array.isArray(value)) {
    const row = value as Record<string, unknown>;
    return String(row.nome || row.name || row.celular || row.telefone || row.email || "").trim();
  }
  return String(value || "").trim();
}

function objValue(value: unknown, key: string) {
  return value && typeof value === "object" && !Array.isArray(value) ? text((value as Record<string, unknown>)[key]) : "";
}

function fromAluno(a?: AlunoData): Form {
  return {
    nome: text(a?.nome || a?.name),
    turma: text(a?.turma || a?.classe),
    modulo: text(a?.modulo || a?.modalidade || "Ingles em turma online"),
    livro: text(a?.livro || a?.book),
    data_nascimento: text(a?.data_nascimento || a?.nascimento),
    cpf: text(a?.cpf),
    responsavel_nome: text(a?.responsavel_nome) || objValue(a?.responsavel, "nome") || text(a?.responsavel),
    responsavel_cpf: text(a?.responsavel_cpf) || objValue(a?.responsavel, "cpf"),
    responsavel_telefone: text(a?.responsavel_telefone || a?.telefone) || objValue(a?.responsavel, "celular") || objValue(a?.responsavel, "telefone"),
    responsavel_email: text(a?.responsavel_email || a?.email) || objValue(a?.responsavel, "email"),
    telefone: text(a?.celular),
    email: text(a?.email),
    endereco: text(a?.endereco),
    dia_vencimento: text(a?.dia_vencimento),
    vencimento: text(a?.vencimento),
    valor_mensalidade: text(a?.valor_mensalidade),
    vip_tipo_plano: text(a?.vip_tipo_plano || "Pacote 10 aulas"),
    vip_aulas_total: text(a?.vip_aulas_total || ""),
    vip_aulas_restantes: text(a?.vip_aulas_restantes || ""),
    observacoes: text(a?.observacoes),
    login: text(a?.login),
    senha: text(a?.senha),
    status: text(a?.status || "Ativo"),
  };
}

function credentialMessage(form: Form) {
  return [
    `Olá! O acesso de ${form.nome || "aluno"} ao portal Active Educacional foi atualizado.`,
    "",
    `Login: ${form.login}`,
    `Senha: ${form.senha}`,
    "",
    "Portal: https://activeeducacional.tech/aluno/login",
  ].join("\n");
}

function whatsappUrl(phone: string, message: string) {
  const digits = phone.replace(/\D/g, "");
  return `https://wa.me/${digits}?text=${encodeURIComponent(message)}`;
}

function mailtoUrl(email: string, form: Form) {
  return `mailto:${email}?subject=${encodeURIComponent("Acesso ao portal Active Educacional")}&body=${encodeURIComponent(credentialMessage(form))}`;
}

function AlunoModal({ aluno, onClose, onSaved }: { aluno?: AlunoData; onClose: () => void; onSaved: () => void }) {
  const isEdit = Boolean(aluno?.id);
  const [form, setForm] = useState<Form>(fromAluno(aluno));
  const [turmas, setTurmas] = useState<TurmaOption[]>([]);
  const [saving, setSaving] = useState(false);
  const [erro, setErro] = useState("");
  const [savingCred, setSavingCred] = useState(false);
  const [credFeedback, setCredFeedback] = useState("");
  const [credWhatsappLink, setCredWhatsappLink] = useState("");
  const vip = isVipModule(form.modulo);
  const planTotal = vipPlanTotal(form.vip_tipo_plano);
  const turmaOptions = useMemo(() => {
    const names = turmas.map((t) => text(t.nome || t.name)).filter(Boolean);
    const unique = Array.from(new Set(["Sem Turma", ...names, form.turma].filter(Boolean)));
    return unique;
  }, [turmas, form.turma]);
  const livroOptions = useMemo(() => Array.from(new Set([...BOOK_LEVELS, form.livro].filter(Boolean))), [form.livro]);

  useEffect(() => {
    fetch("/api/turmas")
      .then((res) => res.json())
      .then((data) => setTurmas(Array.isArray(data?.turmas) ? data.turmas : []))
      .catch(() => setTurmas([]));
  }, []);

  function update<K extends keyof Form>(field: K, value: Form[K]) {
    setForm((prev) => ({ ...prev, [field]: value }));
    setErro("");
  }

  function selecionarTurma(turmaNome: string) {
    const turma = turmas.find((t) => text(t.nome || t.name) === turmaNome);
    setForm((prev) => ({
      ...prev,
      turma: turmaNome,
      livro: text(turma?.livro || turma?.book) || prev.livro,
      modulo: text(turma?.modulo || turma?.tipo_aula || turma?.modalidade) || prev.modulo,
    }));
    setErro("");
  }

  async function excluir() {
    if (!confirm(`Excluir o aluno "${text(aluno?.nome)}"? Esta acao nao pode ser desfeita.`)) return;
    setSaving(true);
    await fetch(`/api/alunos?id=${encodeURIComponent(text(aluno?.id || aluno?.nome))}`, { method: "DELETE" });
    setSaving(false);
    onSaved();
  }

  async function salvar() {
    if (!form.nome.trim()) {
      setErro("O nome do aluno e obrigatorio.");
      return;
    }
    setSaving(true);
    const payload = {
      ...(isEdit ? { id: aluno!.id || aluno!.nome } : {}),
      ...form,
      nome: form.nome.trim(),
      turma: form.turma.trim(),
      classe: form.turma.trim(),
      livro: form.livro.trim(),
      book: form.livro.trim(),
      modulo: form.modulo,
      valor_professor_aula: teacherClassValueByModule(form.modulo),
      vip_tipo_plano: vip ? form.vip_tipo_plano : "",
      vip_aulas_total: vip ? Number(form.vip_aulas_total || planTotal || 0) : 0,
      vip_aulas_restantes: vip ? Number(form.vip_aulas_restantes || form.vip_aulas_total || planTotal || 0) : 0,
      responsavel: {
        nome: form.responsavel_nome.trim(),
        cpf: form.responsavel_cpf.trim(),
        celular: form.responsavel_telefone.trim(),
        telefone: form.responsavel_telefone.trim(),
        email: form.responsavel_email.trim(),
      },
      responsavel_nome: form.responsavel_nome.trim(),
      responsavel_cpf: form.responsavel_cpf.trim(),
      responsavel_telefone: form.responsavel_telefone.trim(),
      responsavel_email: form.responsavel_email.trim(),
      telefone: form.responsavel_telefone.trim(),
      celular: form.telefone.trim(),
      email: form.email.trim(),
      login: form.login.trim().toLowerCase(),
      senha: form.senha.trim(),
    };
    const res = await fetch("/api/alunos", {
      method: isEdit ? "PUT" : "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    setSaving(false);
    if (!res.ok) {
      const d = await res.json().catch(() => ({}));
      setErro((d as { error?: string }).error || "Erro ao salvar.");
      return;
    }
    onSaved();
  }

  async function salvarCredenciais() {
    if (!isEdit || !aluno?.id) return;
    if (!form.login.trim() || form.senha.trim().length < 4) {
      setCredFeedback("Informe login e senha com pelo menos 4 caracteres.");
      return;
    }
    setSavingCred(true);
    setCredFeedback("");
    const res = await fetch("/api/alunos/credenciais", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ id: aluno.id, login: form.login, senha: form.senha }),
    });
    setSavingCred(false);
    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      setCredFeedback(String(data.error || "Erro ao salvar login/senha."));
      return;
    }
    const savedLogin = String(data.login || form.login).trim();
    update("login", savedLogin);
    setCredWhatsappLink(String(data.whatsapp_url || whatsappUrl(form.responsavel_telefone, credentialMessage({ ...form, login: savedLogin }))));
    setCredFeedback("Login e senha salvos. Agora pode enviar por WhatsApp ou e-mail.");
  }

  return (
    <div className="modal-overlay" onClick={(e) => e.target === e.currentTarget && onClose()}>
      <div className="modal-box" style={{ maxWidth: 920 }}>
        <div className="modal-header">
          <div>
            <div className="modal-title">{isEdit ? "Editar aluno completo" : "Novo aluno"}</div>
            <div className="modal-subtitle">Cadastro academico, modulo, responsavel e financeiro do sistema antigo</div>
          </div>
          <button className="modal-close" onClick={onClose}>
            <svg viewBox="0 0 20 20" fill="currentColor"><path fillRule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clipRule="evenodd" /></svg>
          </button>
        </div>

        <div className="modal-body">
          <div className="form-grid">
            <div className="form-group form-group-span2">
              <label className="form-label">Nome completo *</label>
              <input className="form-input" placeholder="Nome do aluno" value={form.nome} onChange={(e) => update("nome", e.target.value)} autoFocus />
            </div>
            <div className="form-group">
              <label className="form-label">Turma</label>
              <select className="form-input" value={form.turma || "Sem Turma"} onChange={(e) => selecionarTurma(e.target.value)}>
                {turmaOptions.map((t) => <option key={t}>{t}</option>)}
              </select>
            </div>
            <div className="form-group">
              <label className="form-label">Modulo *</label>
              <select className="form-input" value={form.modulo} onChange={(e) => update("modulo", e.target.value)}>
                {COURSE_MODULES.map((m) => <option key={m}>{m}</option>)}
              </select>
              <div className="form-help">Pagamento do professor: {formatModuleValue(form.modulo)} por aula.</div>
            </div>
            {vip && (
              <>
                <div className="form-group">
                  <label className="form-label">Tipo do plano VIP</label>
                  <select
                    className="form-input"
                    value={form.vip_tipo_plano}
                    onChange={(e) => {
                      const total = vipPlanTotal(e.target.value);
                      update("vip_tipo_plano", e.target.value);
                      update("vip_aulas_total", String(total));
                      update("vip_aulas_restantes", String(total));
                    }}
                  >
                    <option>Aula avulsa</option>
                    <option>Pacote 10 aulas</option>
                  </select>
                </div>
                <div className="form-group">
                  <label className="form-label">Aulas do pacote VIP</label>
                  <input className="form-input" type="number" min="0" value={form.vip_aulas_total || planTotal} onChange={(e) => update("vip_aulas_total", e.target.value)} />
                </div>
                <div className="form-group">
                  <label className="form-label">Aulas restantes</label>
                  <input className="form-input" type="number" min="0" value={form.vip_aulas_restantes || form.vip_aulas_total || planTotal} onChange={(e) => update("vip_aulas_restantes", e.target.value)} />
                  <div className="form-help">Exemplo: pacote de 10 com 7 restantes significa 3 aulas dadas.</div>
                </div>
              </>
            )}
            <div className="form-group">
              <label className="form-label">Livro</label>
              <select className="form-input" value={form.livro || "Livro 1"} onChange={(e) => update("livro", e.target.value)}>
                {livroOptions.map((livro) => <option key={livro}>{livro}</option>)}
              </select>
            </div>
            <div className="form-group">
              <label className="form-label">Data de nascimento</label>
              <input className="form-input" placeholder="DD/MM/AAAA" value={form.data_nascimento} onChange={(e) => update("data_nascimento", e.target.value)} />
            </div>
            <div className="form-group">
              <label className="form-label">CPF do aluno</label>
              <input className="form-input" placeholder="000.000.000-00" value={form.cpf} onChange={(e) => update("cpf", e.target.value)} />
            </div>
            <div className="form-group">
              <label className="form-label">Responsavel</label>
              <input className="form-input" placeholder="Nome do responsavel" value={form.responsavel_nome} onChange={(e) => update("responsavel_nome", e.target.value)} />
            </div>
            <div className="form-group">
              <label className="form-label">CPF do responsavel</label>
              <input className="form-input" placeholder="000.000.000-00" value={form.responsavel_cpf} onChange={(e) => update("responsavel_cpf", e.target.value)} />
            </div>
            <div className="form-group">
              <label className="form-label">Telefone do responsavel</label>
              <input className="form-input" placeholder="(11) 99999-0000" value={form.responsavel_telefone} onChange={(e) => update("responsavel_telefone", e.target.value)} />
            </div>
            <div className="form-group">
              <label className="form-label">E-mail do responsavel</label>
              <input className="form-input" type="email" placeholder="responsavel@email.com" value={form.responsavel_email} onChange={(e) => update("responsavel_email", e.target.value)} />
            </div>
            <div className="form-group">
              <label className="form-label">Celular do aluno</label>
              <input className="form-input" placeholder="Opcional" value={form.telefone} onChange={(e) => update("telefone", e.target.value)} />
            </div>
            <div className="form-group">
              <label className="form-label">E-mail do aluno</label>
              <input className="form-input" type="email" placeholder="Opcional" value={form.email} onChange={(e) => update("email", e.target.value)} />
            </div>
            <div className="form-group form-group-span2">
              <label className="form-label">Endereco</label>
              <input className="form-input" placeholder="Rua, numero, bairro, cidade" value={form.endereco} onChange={(e) => update("endereco", e.target.value)} />
            </div>
            <div className="form-group">
              <label className="form-label">Dia de vencimento</label>
              <input className="form-input" type="number" min="1" max="31" placeholder="Ex: 10" value={form.dia_vencimento} onChange={(e) => update("dia_vencimento", e.target.value)} />
            </div>
            <div className="form-group">
              <label className="form-label">Primeiro vencimento / fatura</label>
              <input className="form-input" placeholder="DD/MM/AAAA" value={form.vencimento} onChange={(e) => update("vencimento", e.target.value)} />
            </div>
            <div className="form-group">
              <label className="form-label">Valor da mensalidade</label>
              <input className="form-input" inputMode="decimal" placeholder="Ex: 350,00" value={form.valor_mensalidade} onChange={(e) => update("valor_mensalidade", e.target.value)} />
            </div>
            <div className="form-group">
              <label className="form-label">Status</label>
              <select className="form-input" value={form.status} onChange={(e) => update("status", e.target.value)}>
                <option>Ativo</option>
                <option>Inativo</option>
                <option>Em atencao</option>
              </select>
            </div>
            <div className="form-group form-group-span2">
              <label className="form-label">Observacoes</label>
              <textarea className="form-input form-textarea" rows={3} value={form.observacoes} onChange={(e) => update("observacoes", e.target.value)} />
            </div>
            {isEdit && (
              <>
                <div className="form-group">
                  <label className="form-label">Login do aluno</label>
                  <input className="form-input" placeholder="login do portal" value={form.login} onChange={(e) => update("login", e.target.value)} />
                </div>
                <div className="form-group">
                  <label className="form-label">Senha do aluno</label>
                  <input className="form-input" placeholder="senha do portal" value={form.senha} onChange={(e) => update("senha", e.target.value)} />
                </div>
                <div className="form-group form-group-span2">
                  <label className="form-label">Enviar acesso ao responsavel</label>
                  <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
                    <button className="btn btn-primary btn-sm" type="button" onClick={salvarCredenciais} disabled={savingCred}>
                      {savingCred ? "Salvando..." : "Salvar login/senha"}
                    </button>
                    <a
                      className={`btn btn-secondary btn-sm${!form.login || !form.senha || !form.responsavel_telefone ? " disabled" : ""}`}
                      href={credWhatsappLink || (form.login && form.senha && form.responsavel_telefone ? whatsappUrl(form.responsavel_telefone, credentialMessage(form)) : "#")}
                      target="_blank"
                      rel="noreferrer"
                    >
                      Enviar login e senha por WhatsApp
                    </a>
                    <a
                      className={`btn btn-secondary btn-sm${!form.login || !form.senha || !form.responsavel_email ? " disabled" : ""}`}
                      href={form.login && form.senha && form.responsavel_email ? mailtoUrl(form.responsavel_email, form) : "#"}
                    >
                      Enviar login e senha por e-mail
                    </a>
                  </div>
                  <div className="form-help">{credFeedback || "Clique em Salvar login/senha antes de enviar quando mudar o acesso."}</div>
                </div>
              </>
            )}
          </div>
          {erro && <div className="form-error">{erro}</div>}
        </div>

        <div className="modal-footer">
          {isEdit && <button className="btn btn-danger btn-sm" onClick={excluir} disabled={saving} style={{ marginRight: "auto" }}>Excluir</button>}
          <button className="btn btn-secondary" onClick={onClose} disabled={saving}>Cancelar</button>
          <button className="btn btn-primary" onClick={salvar} disabled={saving}>{saving ? "Salvando..." : isEdit ? "Salvar alteracoes" : "Cadastrar aluno"}</button>
        </div>
      </div>
    </div>
  );
}

export function NovoAlunoBtn() {
  const router = useRouter();
  const [open, setOpen] = useState(false);
  return (
    <>
      <button className="btn btn-primary" onClick={() => setOpen(true)}>
        <svg viewBox="0 0 20 20" fill="currentColor"><path fillRule="evenodd" d="M10 3a1 1 0 011 1v5h5a1 1 0 110 2h-5v5a1 1 0 11-2 0v-5H4a1 1 0 110-2h5V4a1 1 0 011-1z" clipRule="evenodd" /></svg>
        Novo aluno
      </button>
      {open && <AlunoModal onClose={() => setOpen(false)} onSaved={() => { setOpen(false); router.refresh(); }} />}
    </>
  );
}

export function EditarAlunoBtn({ aluno }: { aluno: AlunoData }) {
  const router = useRouter();
  const [open, setOpen] = useState(false);
  return (
    <>
      <button className="btn btn-ghost btn-sm btn-icon" title="Editar" onClick={() => setOpen(true)}>
        <svg viewBox="0 0 20 20" fill="currentColor"><path d="M13.586 3.586a2 2 0 112.828 2.828l-.793.793-2.828-2.828.793-.793zM11.379 5.793L3 14.172V17h2.828l8.38-8.379-2.83-2.828z" /></svg>
      </button>
      {open && <AlunoModal aluno={aluno} onClose={() => setOpen(false)} onSaved={() => { setOpen(false); router.refresh(); }} />}
    </>
  );
}
