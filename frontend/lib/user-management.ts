type Row = Record<string, unknown>;
const text = (v: unknown) => String(v || "").trim();
const lower = (v: unknown) => text(v).toLowerCase();
const active = (row: Row) => row.is_active !== false && !row.deleted_at && !/inativ|cancel|arquiv/i.test(text(row.status));
const admin = (row: Row) => lower(row.perfil).includes("admin");

export class UserManagementError extends Error {
  constructor(message: string, public status: number) { super(message); }
}

export function linkedTeacherUser(users: Row[], teacher: Row) {
  const id = text(teacher.id || teacher.nome);
  const login = lower(teacher.usuario || teacher.login);
  const matches = users.filter(user => (id && text(user.professor_id) === id) ||
    (login && lower(user.usuario) === login));
  return matches.length === 1 ? matches[0] : null;
}

export function mutateManagedUser(values: Record<string, unknown>, body: Row, action: "edit" | "delete" | "reset", actor: string, passwordHash?: string) {
  const source = text(body.source), id = text(body.id);
  const key = source === "internal" ? "users" : source === "teacher" ? "teachers" : source === "student" ? "students" : "";
  if (!key || !id) throw new UserManagementError("Fonte e id invalidos.", 400);
  const rows = (Array.isArray(values[key]) ? values[key] : []) as Row[];
  const users = (Array.isArray(values.users) ? values.users : []) as Row[];
  const idx = rows.findIndex(row => text(row.id || (source === "internal" ? row.usuario : row.nome)) === id);
  if (idx < 0) throw new UserManagementError("Usuario nao encontrado.", 404);
  const current = rows[idx];
  const beforeAdmins = users.filter(row => admin(row) && active(row)).length;
  const linked = source === "teacher" ? linkedTeacherUser(users, current) : null;
  const now = new Date().toISOString();
  const next: Row = { ...current, updated_at: now, updated_by: actor };
  if (action === "edit") {
    const login = lower(body.usuario || current.usuario || current.login);
    if (!login) throw new UserManagementError("Login obrigatorio.", 400);
    const conflicts = source === "student" ? [...rows, ...users] : users;
    if (conflicts.some(row => row !== current && row !== linked && active(row) && lower(row.usuario || row.login) === login)) {
      throw new UserManagementError("Este login ja esta em uso.", 409);
    }
    const name = text(body.nome || current.nome || current.pessoa);
    const enabled = body.is_active === undefined ? active(current) : body.is_active === true;
    Object.assign(next, { nome: name, usuario: login, is_active: enabled,
      status: enabled ? "Ativo" : "Inativo", deleted_at: enabled ? "" : text(current.deleted_at) || now,
      deleted_by: enabled ? "" : actor });
    if (source === "internal") Object.assign(next, { pessoa: name, perfil: text(body.perfil || current.perfil) });
    else next.login = login;
    for (const field of ["email", "cpf", "telefone"]) {
      if (body[field] !== undefined) next[field] = field === "cpf" ? text(body[field]).replace(/\D/g, "") : text(body[field]);
    }
    if (body.telefone !== undefined) Object.assign(next, { celular: next.telefone, whatsapp: next.telefone });
    // Do not overwrite the guardian's separate contact with the student's contact.
  } else if (action === "delete") {
    Object.assign(next, { is_active: false, status: "Inativo", deleted_at: now, deleted_by: actor });
  } else {
    if (!passwordHash || !text(current.usuario || current.login)) throw new UserManagementError("Cadastre o login antes de redefinir a senha.", 400);
    Object.assign(next, { senha: passwordHash, must_change_password: true, password_reset_at: now, password_reset_by: actor });
  }
  rows[idx] = next;
  values[key] = rows;
  if (source === "teacher" && linked) {
    const linkedIndex = users.indexOf(linked);
    users[linkedIndex] = action === "reset" ? { ...linked, senha: passwordHash, must_change_password: true,
      password_reset_at: now, password_reset_by: actor } : { ...linked, pessoa: next.nome,
      usuario: next.usuario || linked.usuario, email: next.email, telefone: next.telefone, celular: next.celular,
      cpf: next.cpf, is_active: next.is_active, status: next.status, deleted_at: next.deleted_at,
      deleted_by: next.deleted_by, updated_at: now, updated_by: actor };
    values.users = users;
  } else if (source === "teacher" && action === "reset") {
    users.push({ id: crypto.randomUUID(), professor_id: text(next.id || next.nome), pessoa: next.nome,
      usuario: lower(next.usuario || next.login), senha: passwordHash, perfil: "Professor",
      is_active: active(next), status: next.status, deleted_at: next.deleted_at,
      must_change_password: true, password_reset_at: now, created_at: now });
    values.users = users;
  }
  const afterUsers = values.users as Row[] || users;
  if (beforeAdmins > 0 && afterUsers.filter(row => admin(row) && active(row)).length === 0) {
    throw new UserManagementError("Nao e permitido remover ou desativar o ultimo administrador.", 409);
  }
  const logs = (Array.isArray(values.users_audit) ? values.users_audit : []) as Row[];
  logs.push({ id: crypto.randomUUID(), data: now, acao: action, fonte: source, usuario_id: id, actor });
  values.users_audit = logs;
  return next;
}
