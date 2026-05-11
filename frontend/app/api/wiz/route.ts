import { NextRequest, NextResponse } from "next/server";
import { getSession } from "@/lib/auth";
import { dbList, dbSet } from "@/lib/db";
import { teacherClassValueByModule } from "@/lib/course-modules";
import { sendWhatsApp } from "@/lib/whatsapp";

type Row = Record<string, unknown>;
type WizSession = NonNullable<Awaited<ReturnType<typeof getSession>>>;

function text(value: unknown) {
  return String(value || "").trim();
}

function lower(value: unknown) {
  return text(value).toLowerCase();
}

function canOperate(perfil: string) {
  const role = lower(perfil);
  return role.includes("admin") || role.includes("coord") || role.includes("dire") || role.includes("prof") || role.includes("comercial");
}

function canAdmin(perfil: string) {
  const role = lower(perfil);
  return role.includes("admin") || role.includes("coord") || role.includes("dire");
}

function normalizeList(value: unknown) {
  if (Array.isArray(value)) return value.map(text).filter(Boolean);
  return text(value).split(/[,\n;]/).map((item) => item.trim()).filter(Boolean);
}

function normalize(value: unknown) {
  return text(value).normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase();
}

function firstName(value: unknown) {
  return text(value).split(/\s+/)[0] || "aluno";
}

function randomPassword() {
  return `Active${Math.floor(1000 + Math.random() * 9000)}`;
}

function portalUrl() {
  return process.env.NEXT_PUBLIC_APP_URL || process.env.APP_URL || "https://ativoeducacional.tech";
}

function studentPhone(row: Row) {
  return text(row.whatsapp || row.telefone || row.responsavel_telefone || row.phone);
}

function studentEmail(row: Row) {
  return text(row.email || row.responsavel_email);
}

function teacherPhone(row: Row) {
  return text(row.whatsapp || row.telefone || row.phone);
}

function teacherEmail(row: Row) {
  return text(row.email);
}

function credentialMessage(kind: "aluno" | "professor", nome: string, login: string, senha: string) {
  return `Ola, ${firstName(nome)}! Seu acesso do Active Educacional foi atualizado.\n\nPainel: ${portalUrl()}\nPerfil: ${kind}\nLogin: ${login}\nSenha: ${senha}\n\nAo entrar, guarde esses dados com seguranca.`;
}

function findByName(items: Row[], needle: unknown) {
  const wanted = normalize(needle);
  if (!wanted) return null;
  return items.find((item) => {
    const id = normalize(item.id);
    const nome = normalize(item.nome || item.name || item.aluno || item.professor || item.usuario || item.login);
    const login = normalize(item.login || item.usuario);
    return id === wanted || login === wanted || nome === wanted || nome.includes(wanted);
  }) || null;
}

function filterRecipients(items: Row[], turma: unknown) {
  const target = normalize(turma || "Todas");
  if (!target || target === "todas" || target === "todos") return items;
  return items.filter((item) => {
    const itemTurma = normalize(item.turma || item.classe || item.class || item.className);
    return itemTurma === target || itemTurma.includes(target);
  });
}

function addMonths(dateStr: string, months: number) {
  const date = new Date(`${dateStr || new Date().toISOString().slice(0, 10)}T12:00:00`);
  date.setMonth(date.getMonth() + months);
  return date.toISOString().slice(0, 10);
}

function parseMoney(value: unknown) {
  const cleaned = text(value).replace(/[^\d,.-]/g, "").replace(/\./g, "").replace(",", ".");
  return Number.parseFloat(cleaned) || 0;
}

function money(value: number) {
  return value.toFixed(2).replace(".", ",");
}

async function audit(action: string, payload: Row, result: Row, actor: string, perfil: string) {
  const log = await dbList<Row>("wiz_action_audit.json");
  const entry = {
    id: crypto.randomUUID(),
    data: new Date().toISOString(),
    acao: action,
    usuario: actor,
    perfil,
    status: result.ok ? "concluido" : "erro",
    resultado: text(result.message),
    data_execucao: payload,
  };
  await dbSet("wiz_action_audit.json", [...log, entry]);
  return entry;
}

async function createWallPost(data: Row, actor: string) {
  const titulo = text(data.titulo || data.title || "Comunicado");
  const mensagem = text(data.mensagem || data.conteudo || data.texto);
  if (!titulo || !mensagem) return { ok: false, message: "Titulo e mensagem sao obrigatorios." };
  const post = {
    id: crypto.randomUUID(),
    titulo: titulo.slice(0, 100),
    mensagem,
    tipo_post: text(data.tipo_post || "Aviso Geral"),
    turma: text(data.turma || "Todas") || "Todas",
    turmas: normalizeList(data.turmas),
    publico: text(data.publico || "Alunos e responsaveis"),
    data: new Date().toLocaleDateString("pt-BR"),
    publicado_em: new Date().toISOString(),
    autor: actor,
    status: "Ativo",
    fixado: Boolean(data.fixado),
    requer_confirmacao: Boolean(data.requer_confirmacao),
    notification_status: {
      push: "pendente",
      whatsapp: data.enviar_whatsapp === false ? "nao_enviado" : "pendente",
      email: data.enviar_email === false ? "nao_enviado" : "pendente",
    },
  };
  const posts = await dbList<Row>("messages.json");
  await dbSet("messages.json", [...posts, post]);
  return { ok: true, message: `Comunicado criado: ${post.titulo}`, item: post };
}

async function logEmail(destinatario: string, assunto: string, mensagem: string, actor: string) {
  const logs = await dbList<Row>("email_log.json");
  await dbSet("email_log.json", [
    ...logs,
    {
      id: crypto.randomUUID(),
      data: new Date().toISOString(),
      canal: "email",
      destinatario,
      assunto,
      mensagem,
      origem: "Assistente Wiz",
      status: "preparado",
      usuario: actor,
    },
  ]);
}

async function sendBulkMessage(data: Row, actor: string, session: WizSession) {
  const mensagem = text(data.mensagem || data.texto);
  if (!mensagem) return { ok: false, message: "Mensagem e obrigatoria para envio em massa." };

  const publico = lower(data.publico || data.destinatarios || "alunos");
  const assunto = text(data.assunto || data.titulo || "Mensagem Active Educacional");
  const source = publico.includes("prof") ? await dbList<Row>("teachers.json") : await dbList<Row>("students.json");
  const recipients = filterRecipients(source, data.turma);
  const enviarWhatsApp = data.enviar_whatsapp !== false;
  const enviarEmail = data.enviar_email !== false;
  let whatsappOk = 0;
  let whatsappFalha = 0;
  let emails = 0;

  for (const item of recipients) {
    const phone = publico.includes("prof") ? teacherPhone(item) : studentPhone(item);
    const email = publico.includes("prof") ? teacherEmail(item) : studentEmail(item);
    if (enviarWhatsApp && phone) {
      const sent = await sendWhatsApp(phone, mensagem, session);
      if (sent.ok) whatsappOk += 1;
      else whatsappFalha += 1;
    }
    if (enviarEmail && email) {
      await logEmail(email, assunto, mensagem, actor);
      emails += 1;
    }
  }

  return {
    ok: true,
    message: `Envio em massa processado: ${recipients.length} destinatario(s), WhatsApp ${whatsappOk} enviado(s), ${whatsappFalha} falha(s), ${emails} e-mail(s) preparado(s).`,
    total: recipients.length,
    whatsapp_enviados: whatsappOk,
    whatsapp_falhas: whatsappFalha,
    emails_preparados: emails,
  };
}

async function createHomework(data: Row, actor: string) {
  const titulo = text(data.titulo || "Tarefa criada pelo Wiz");
  const disciplina = text(data.disciplina || "Ingles");
  const turma = text(data.turma || "Todas") || "Todas";
  const quantidade = Math.max(1, Math.min(15, Number(data.quantidade_questoes || data.quantidade || 5) || 5));
  const foco = text(data.foco || data.conteudo || data.capitulo || "conteudo estudado");
  const questions = Array.from({ length: quantidade }).map((_, index) => ({
    id: crypto.randomUUID(),
    tipo: index % 3 === 0 ? "multipla_escolha" : index % 3 === 1 ? "verdadeiro_falso" : "aberta",
    enunciado: index % 3 === 0
      ? `Sobre ${foco}, escolha a alternativa correta. Questao ${index + 1}.`
      : index % 3 === 1
        ? `Verdadeiro ou falso: ${foco} pode ser aplicado em uma situacao real de comunicacao.`
        : `Explique com suas palavras: ${foco}.`,
    opcoes: index % 3 === 0 ? ["Alternativa correta", "Distrator comum", "Resposta incompleta", "Fora do contexto"] : [],
    correta_idx: index % 3 === 0 ? 0 : null,
    correta_texto: index % 3 === 1 ? "V" : "",
    pontos: index % 3 === 2 ? 3 : 2,
    feedback: "Revise antes de publicar para os alunos.",
  }));
  const item = {
    id: crypto.randomUUID(),
    tipo: "Licao de Casa",
    titulo,
    descricao: text(data.descricao || data.instrucoes || `Atividade objetiva sobre ${foco}.`),
    disciplina,
    turma,
    turmas: normalizeList(data.turmas),
    aluno: text(data.aluno),
    livro: text(data.livro),
    capitulo: text(data.capitulo),
    habilidade: foco,
    due_date: text(data.due_date || data.prazo),
    peso: Number(data.peso) || questions.reduce((sum, q) => sum + q.pontos, 0),
    questions,
    status: text(data.status || "Ativa"),
    autor: actor,
    created_at: new Date().toISOString(),
    notification_status: { push: "pendente", whatsapp: "pendente", email: "pendente" },
  };
  const items = await dbList<Row>("activities.json");
  await dbSet("activities.json", [...items, item]);
  return { ok: true, message: `Tarefa criada: ${titulo}`, item };
}

async function createWork(data: Row, actor: string) {
  const item = {
    id: `d_${Date.now()}`,
    titulo: text(data.titulo || "Trabalho criado pelo Wiz"),
    descricao: text(data.descricao || data.instrucoes || "Trabalho avaliativo com criterios de entrega."),
    turma: text(data.turma || "Todas"),
    disciplina: text(data.disciplina || "Ingles"),
    prazo: text(data.prazo || data.due_date),
    pontos: Number(data.pontos || data.peso || 10),
    criterios: text(data.criterios || "Organizacao, conteudo, entrega e apresentacao."),
    autor: actor,
    status: text(data.status || "Publicado"),
    notification_status: { push: "pendente", whatsapp: "pendente", email: "pendente" },
  };
  const items = await dbList<Row>("challenges.json");
  await dbSet("challenges.json", [...items, item]);
  return { ok: true, message: `Trabalho/desafio criado: ${item.titulo}`, item };
}

async function createStudent(data: Row) {
  const nome = text(data.nome || data.aluno);
  if (!nome) return { ok: false, message: "Nome do aluno e obrigatorio." };
  const modulo = text(data.modulo || "Ingles em turma online");
  const item = {
    id: crypto.randomUUID(),
    nome,
    turma: text(data.turma || "Sem Turma"),
    classe: text(data.turma || "Sem Turma"),
    livro: text(data.livro || "Livro 1"),
    book: text(data.livro || "Livro 1"),
    modulo,
    responsavel_nome: text(data.responsavel),
    responsavel_telefone: text(data.telefone || data.whatsapp),
    responsavel_email: text(data.email),
    telefone: text(data.telefone || data.whatsapp),
    email: text(data.email),
    valor_mensalidade: text(data.valor_mensalidade),
    valor_professor_aula: teacherClassValueByModule(modulo),
    status: "Ativo",
    created_at: new Date().toISOString(),
    created_by: "Assistente Wiz",
  };
  const students = await dbList<Row>("students.json");
  await dbSet("students.json", [...students, item]);
  return { ok: true, message: `Aluno cadastrado: ${nome}`, item };
}

async function createFinancial(data: Row) {
  const aluno = text(data.aluno || data.nome);
  if (!aluno) return { ok: false, message: "Aluno e obrigatorio para recebimento." };
  const total = parseMoney(data.valor_total || data.valor);
  if (total <= 0) return { ok: false, message: "Valor total e obrigatorio." };
  const parcelas = Math.max(1, Math.min(48, Number(data.parcelas || data.qtd_parcelas || 1) || 1));
  const valorParcela = total / parcelas;
  const vencimento = text(data.vencimento || new Date().toISOString().slice(0, 10));
  const items = await dbList<Row>("receivables.json");
  const created = Array.from({ length: parcelas }).map((_, index) => {
    const parcela = `${index + 1}/${parcelas}`;
    return {
      id: crypto.randomUUID(),
      aluno,
      aluno_login: text(data.aluno_login),
      telefone: text(data.telefone || data.whatsapp),
      whatsapp: text(data.telefone || data.whatsapp),
      email: text(data.email),
      data_lancamento: text(data.data_lancamento || new Date().toISOString().slice(0, 10)),
      descricao: `${text(data.categoria || "Mensalidade")} - ${text(data.descricao || "Lancamento Wiz")} - Parcela ${parcela}`,
      categoria: text(data.categoria || "Mensalidade"),
      tipo_lancamento_detalhe: text(data.categoria || "Mensalidade"),
      valor: money(valorParcela),
      valor_total: money(total),
      valor_parcela: money(valorParcela),
      vencimento: addMonths(vencimento, index),
      data_vencimento: addMonths(vencimento, index),
      parcela,
      parcela_numero: index + 1,
      parcela_total: parcelas,
      status: data.gerar_boleto === false ? "Pendente" : "Boleto gerado",
      boleto_status: data.gerar_boleto === false ? "" : "Gerado",
      boleto_codigo: `AE-${Date.now()}-${index + 1}`,
      created_at: new Date().toISOString(),
      created_by: "Assistente Wiz",
      notification_status: { push: "pendente", whatsapp: "pendente", email: "pendente" },
    };
  });
  await dbSet("receivables.json", [...items, ...created]);
  return { ok: true, message: `Recebimento criado: ${parcelas} parcela(s) para ${aluno}`, items: created };
}

async function resetStudentAccess(data: Row, actor: string, session: WizSession) {
  const students = await dbList<Row>("students.json");
  const student = findByName(students, data.aluno || data.nome || data.login || data.id);
  if (!student) return { ok: false, message: "Aluno nao encontrado para atualizar acesso." };

  const nome = text(student.nome || student.name || data.nome);
  const login = text(data.login) || text(student.login) || normalize(nome).replace(/[^a-z0-9]+/g, ".").replace(/^\.+|\.+$/g, "");
  const senha = text(data.senha || data.password) || randomPassword();
  const updated = students.map((item) => item === student ? {
    ...item,
    login,
    usuario: login,
    senha,
    password: senha,
    access_updated_at: new Date().toISOString(),
    access_updated_by: actor,
  } : item);
  await dbSet("students.json", updated);

  const message = credentialMessage("aluno", nome, login, senha);
  const phone = text(data.telefone || data.whatsapp) || studentPhone(student);
  const email = text(data.email) || studentEmail(student);
  const whatsapp = phone ? await sendWhatsApp(phone, message, session) : { ok: false, status: "sem telefone" };
  if (email) await logEmail(email, "Acesso Active Educacional", message, actor);

  return {
    ok: true,
    message: `Acesso do aluno atualizado. WhatsApp: ${whatsapp.status}.`,
    aluno: nome,
    login,
    senha,
    whatsapp_status: whatsapp.status,
    email_preparado: Boolean(email),
  };
}

async function resetTeacherAccess(data: Row, actor: string, session: WizSession) {
  const teachers = await dbList<Row>("teachers.json");
  const teacher = findByName(teachers, data.professor || data.nome || data.login || data.id);
  if (!teacher) return { ok: false, message: "Professor nao encontrado para atualizar acesso." };

  const nome = text(teacher.nome || teacher.name || data.nome);
  const login = text(data.login) || text(teacher.login) || normalize(nome).replace(/[^a-z0-9]+/g, ".").replace(/^\.+|\.+$/g, "");
  const senha = text(data.senha || data.password) || randomPassword();
  await dbSet("teachers.json", teachers.map((item) => item === teacher ? {
    ...item,
    login,
    usuario: login,
    senha,
    password: senha,
    access_updated_at: new Date().toISOString(),
    access_updated_by: actor,
  } : item));

  const users = await dbList<Row>("users.json");
  const existingUser = findByName(users, login) || findByName(users, nome);
  const userRecord = {
    ...(existingUser || {}),
    id: text(existingUser?.id) || text(teacher.id) || crypto.randomUUID(),
    nome,
    pessoa: nome,
    usuario: login,
    login,
    senha,
    password: senha,
    perfil: text(existingUser?.perfil || "professor"),
    professor_id: text(teacher.id),
    status: "Ativo",
    updated_at: new Date().toISOString(),
  };
  await dbSet("users.json", existingUser ? users.map((item) => item === existingUser ? userRecord : item) : [...users, userRecord]);

  const message = credentialMessage("professor", nome, login, senha);
  const phone = text(data.telefone || data.whatsapp) || teacherPhone(teacher);
  const email = text(data.email) || teacherEmail(teacher);
  const whatsapp = phone ? await sendWhatsApp(phone, message, session) : { ok: false, status: "sem telefone" };
  if (email) await logEmail(email, "Acesso Active Educacional", message, actor);

  return {
    ok: true,
    message: `Acesso do professor atualizado. WhatsApp: ${whatsapp.status}.`,
    professor: nome,
    login,
    senha,
    whatsapp_status: whatsapp.status,
    email_preparado: Boolean(email),
  };
}

async function createAgenda(data: Row, actor: string) {
  const titulo = text(data.titulo || data.descricao || "Evento criado pelo Wiz");
  const item = {
    id: crypto.randomUUID(),
    titulo,
    descricao: text(data.descricao),
    data: text(data.data || new Date().toISOString().slice(0, 10)),
    horario: text(data.horario || data.hora),
    turma: text(data.turma),
    professor: text(data.professor),
    status: text(data.status || "Agendado"),
    created_at: new Date().toISOString(),
    created_by: actor,
  };
  const agenda = await dbList<Row>("agenda.json");
  await dbSet("agenda.json", [...agenda, item]);
  return { ok: true, message: `Agenda criada: ${titulo}`, item };
}

async function answerStudent(data: Row, actor: string, session: WizSession) {
  const aluno = text(data.aluno || data.nome || data.destinatario);
  const pergunta = text(data.pergunta || data.mensagem || data.texto);
  if (!aluno || !pergunta) return { ok: false, message: "Informe aluno e mensagem para responder." };

  const students = await dbList<Row>("students.json");
  const student = findByName(students, aluno);
  const livro = text(student?.livro || student?.book || data.livro || "livro cadastrado");
  const resposta = text(data.resposta) || `Ola, ${firstName(aluno)}! Revise o conteudo do ${livro} e pratique com exemplos curtos em ingles. Se a duvida continuar, envie uma frase de exemplo para o professor corrigir.`;
  const item = {
    id: crypto.randomUUID(),
    aluno,
    pergunta,
    resposta,
    livro_referencia: livro,
    origem: "Professor Wiz",
    professor: actor,
    status: "respondido",
    data: new Date().toISOString(),
  };
  const messages = await dbList<Row>("student_messages.json");
  await dbSet("student_messages.json", [...messages, item]);

  const phone = text(data.telefone || data.whatsapp) || (student ? studentPhone(student) : "");
  const whatsapp = phone ? await sendWhatsApp(phone, resposta, session) : { ok: false, status: "sem telefone" };
  return { ok: true, message: `Resposta registrada para ${aluno}. WhatsApp: ${whatsapp.status}.`, item, whatsapp_status: whatsapp.status };
}

async function logMessage(data: Row, actor: string) {
  const item = {
    id: crypto.randomUUID(),
    destinatario: text(data.destinatario || data.aluno || data.turma || "Todos"),
    assunto: text(data.assunto || "Mensagem Wiz"),
    mensagem: text(data.mensagem || data.texto),
    canal: text(data.canal || "WhatsApp e e-mail"),
    status: "preparado",
    origem: "Assistente Wiz",
    usuario: actor,
    data: new Date().toISOString(),
  };
  if (!item.mensagem) return { ok: false, message: "Mensagem e obrigatoria." };
  const logs = await dbList<Row>("email_log.json");
  await dbSet("email_log.json", [...logs, item]);
  return { ok: true, message: `Envio preparado para ${item.destinatario}`, item };
}

function suggestFromPrompt(prompt: string) {
  const norm = lower(prompt);
  if ((norm.includes("massa") || norm.includes("todos") || norm.includes("turma")) && (norm.includes("whatsapp") || norm.includes("email") || norm.includes("mensagem"))) return "send_bulk_message";
  if ((norm.includes("senha") || norm.includes("login") || norm.includes("acesso")) && norm.includes("prof")) return "reset_teacher_access";
  if (norm.includes("senha") || norm.includes("login") || norm.includes("acesso")) return "reset_student_access";
  if (norm.includes("responder") || norm.includes("duvida") || norm.includes("chat")) return "answer_student";
  if (norm.includes("comunic") || norm.includes("aviso") || norm.includes("mensagem")) return "create_wall_post";
  if (norm.includes("tarefa") || norm.includes("licao") || norm.includes("lição") || norm.includes("homework")) return "create_homework";
  if (norm.includes("trabalho") || norm.includes("desafio")) return "create_work";
  if (norm.includes("aluno") && (norm.includes("cadastr") || norm.includes("criar"))) return "create_student";
  if (norm.includes("receb") || norm.includes("boleto") || norm.includes("mensalidade") || norm.includes("financeiro")) return "create_financial";
  if (norm.includes("agenda") || norm.includes("aula") || norm.includes("evento")) return "create_agenda";
  return "answer";
}

async function answer(prompt: string) {
  const action = suggestFromPrompt(prompt);
  return {
    ok: true,
    message: action === "answer"
      ? "Sou o Professor Wiz operacional do Active: posso cadastrar aluno, criar comunicado, gerar tarefa, criar trabalho, lancar recebimento, enviar mensagens, atualizar login/senha, responder aluno e agendar evento. Diga a acao com dados objetivos."
      : `Parece uma solicitacao de ${action}. Use o formulario rapido correspondente ou envie os dados completos para executar.`,
    suggested_action: action,
  };
}

export async function GET() {
  const session = await getSession();
  if (!session) return NextResponse.json({ error: "Nao autorizado" }, { status: 401 });
  const [logs, alunos, turmas, professores] = await Promise.all([
    dbList<Row>("wiz_action_audit.json"),
    dbList<Row>("students.json"),
    dbList<Row>("classes.json"),
    dbList<Row>("teachers.json"),
  ]);
  return NextResponse.json({ logs, alunos, turmas, professores });
}

export async function POST(req: NextRequest) {
  const session = await getSession();
  if (!session || !canOperate(session.perfil)) {
    return NextResponse.json({ error: "Nao autorizado" }, { status: 401 });
  }
  const body = await req.json() as Row;
  const action = text(body.action || "answer");
  const data = (body.data && typeof body.data === "object" ? body.data : body) as Row;
  const actor = session.pessoa || session.usuario;

  let result: Row;
  if (action === "answer") result = await answer(text(data.prompt || body.prompt));
  else if (action === "create_wall_post") result = await createWallPost(data, actor);
  else if (action === "create_homework") result = await createHomework(data, actor);
  else if (action === "create_work") result = await createWork(data, actor);
  else if (action === "create_student") result = canAdmin(session.perfil) || lower(session.perfil).includes("comercial") ? await createStudent(data) : { ok: false, message: "Perfil sem permissao para cadastrar aluno." };
  else if (action === "create_financial") result = canAdmin(session.perfil) || lower(session.perfil).includes("comercial") ? await createFinancial(data) : { ok: false, message: "Perfil sem permissao para financeiro." };
  else if (action === "create_agenda") result = await createAgenda(data, actor);
  else if (action === "prepare_message") result = await logMessage(data, actor);
  else if (action === "send_bulk_message") result = canAdmin(session.perfil) || lower(session.perfil).includes("comercial") ? await sendBulkMessage(data, actor, session) : { ok: false, message: "Perfil sem permissao para envio em massa." };
  else if (action === "reset_student_access") result = canAdmin(session.perfil) || lower(session.perfil).includes("comercial") ? await resetStudentAccess(data, actor, session) : { ok: false, message: "Perfil sem permissao para alterar acesso de aluno." };
  else if (action === "reset_teacher_access") result = canAdmin(session.perfil) ? await resetTeacherAccess(data, actor, session) : { ok: false, message: "Perfil sem permissao para alterar acesso de professor." };
  else if (action === "answer_student") result = await answerStudent(data, actor, session);
  else result = { ok: false, message: "Acao do Wiz nao reconhecida." };

  await audit(action, data, result, actor, session.perfil);
  return NextResponse.json(result, { status: result.ok ? 200 : 400 });
}
