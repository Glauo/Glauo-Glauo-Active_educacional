const { test } = require('node:test');
const assert = require('node:assert/strict');
const { createHmac } = require('node:crypto');
const { NextRequest } = require('next/server');
const { load, memoryDb } = require('./load-test-module.cjs');

const invoice = { id: 'invoice-1', aluno_id: 'student-1', status: 'Pendente', valor: 100, mercado_pago_payment_id: '987' };
const payment = { id: 987, external_reference: 'invoice-1', status: 'approved', transaction_amount: 100,
  currency_id: 'BRL', metadata: { aluno_id: 'student-1' }, date_last_updated: '2026-10-02T10:00:00Z' };
function finance(initial = [invoice], remote = payment) {
  const db = memoryDb({ receivables: initial });
  let calls = 0;
  const mod = load('lib/mercadopago-sync.ts', { '@/lib/db': db,
    '@/lib/student-payment-automation': { releaseStudentAccessAfterPayment: async () => ({}) } },
  { fetch: async url => { calls++; assert.equal(url, 'https://api.mercadopago.com/v1/payments/987'); return { ok: true, json: async () => remote }; } });
  return { ...mod, db, calls: () => calls };
}
test('approved queries real API contract and atomically settles only linked installment', async () => {
  const f = finance([invoice, { ...invoice, id: 'invoice-2', mercado_pago_payment_id: '988' }]);
  const result = await f.syncMercadoPagoPayment('987', 'webhook');
  assert.equal(f.calls(), 1); assert.equal(result.paid, true);
  const rows = f.db.snapshot();
  assert.equal(rows.receivables[0].status, 'Pago'); assert.equal(rows.receivables[1].status, 'Pendente');
  assert.equal(rows.receipts.length, 1); assert.equal(rows.receivables[0].valor_pago, 100);
  assert.ok(rows.receivables[0].webhook_received_at);
});

test('administrator entering through CondoJob still lands in the full admin dashboard', async () => {
  const route = load('app/api/auth/route.ts', {
    '@/lib/auth': {
      validateCredentials: async () => ({ usuario: 'admin', perfil: 'Admin', pessoa: 'Administrador', unit: 'CondoJob' }),
      signToken: async () => 'test-session', COOKIE_NAME: 'ae_session', TTL_SECONDS: 28800,
      dashboardForPerfil: () => '/',
    },
    '@/lib/db': { dbUpdate: async () => [] },
  });
  const response = await route.POST(new NextRequest('https://example.test/api/auth', {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ usuario: 'admin', senha: 'test', unit: 'CondoJob' }),
  }));
  assert.equal(response.status, 200);
  assert.equal((await response.json()).redirectTo, '/');
});
test('concurrent duplicate webhooks create exactly one receipt', async () => {
  const f = finance();
  await Promise.all(Array.from({ length: 15 }, () => f.syncMercadoPagoPayment('987', 'webhook')));
  assert.equal(f.db.snapshot().receipts.length, 1);
});
for (const status of ['pending', 'in_process', 'rejected', 'cancelled', 'refunded', 'charged_back']) {
  test(`${status} never settles installment or creates a receipt`, async () => {
    const f = finance([invoice], { ...payment, status });
    const result = await f.syncMercadoPagoPayment('987', 'webhook');
    assert.equal(result.paid, false); assert.equal(f.db.snapshot().receipts.length, 0);
    assert.notEqual(f.db.snapshot().receivables[0].status, 'Pago');
  });
}
test('rejects conflicting installment/student metadata and ambiguous references', async () => {
  for (const remote of [{ ...payment, external_reference: 'wrong' }, { ...payment, metadata: { aluno_id: 'other' } }]) {
    const f = finance([invoice], remote);
    assert.equal((await f.syncMercadoPagoPayment('987', 'webhook')).matched, false);
    assert.equal(f.db.snapshot().receivables[0].status, 'Pendente');
  }
  const f = finance([invoice, { ...invoice, id: 'duplicate' }]);
  assert.equal((await f.syncMercadoPagoPayment('987', 'webhook')).matched, false);
});
test('does not match by email or CPF and amount alone', async () => {
  const f = finance([{ id: 'other', aluno_id: 'student-1', email: 'same@example.test', valor: 100 }],
    { ...payment, external_reference: '', payer: { email: 'same@example.test' } });
  assert.equal((await f.syncMercadoPagoPayment('987', 'webhook')).matched, false);
});
test('old pending status does not reopen a settled installment', async () => {
  const f = finance([{ ...invoice, status: 'Pago', valor_pago: 100 }], { ...payment, status: 'pending' });
  await f.syncMercadoPagoPayment('987', 'webhook');
  assert.equal(f.db.snapshot().receivables[0].status, 'Pago');
});
test('manual verification cannot settle a different requested installment', async () => {
  const f = finance();
  assert.equal((await f.syncMercadoPagoPayment('987', 'manual', 'other')).matched, false);
});
test('API returned id must match requested payment', async () => {
  const f = finance([invoice], { ...payment, id: 222 });
  await assert.rejects(() => f.syncMercadoPagoPayment('987', 'webhook'), /nao corresponde/);
  assert.equal(f.db.snapshot().receivables[0].status, 'Pendente');
});
test('approved payment with a different amount is flagged and never settles the receivable', async () => {
  const expected = { ...invoice, mercado_pago_transaction_amount: 110 };
  const f = finance([expected], { ...payment, transaction_amount: 100,
    transaction_details: { total_paid_amount: 112 } });
  const result = await f.syncMercadoPagoPayment('987', 'webhook');
  const rows = f.db.snapshot();
  assert.equal(result.matched, true);
  assert.equal(result.paid, false);
  assert.equal(result.requiresReview, true);
  assert.equal(result.expectedAmount, 110);
  assert.equal(result.actualAmount, 100);
  assert.equal(rows.receivables[0].status, 'Pendente');
  assert.equal(rows.receivables[0].mercado_pago_revisao_necessaria, true);
  assert.equal((rows.receipts || []).length, 0);
  assert.equal(rows.finance_audit.at(-1).acao, 'mercado_pago_valor_divergente_revisao_manual');
});
test('approved payment with no stored receivable amount is held for review', async () => {
  const f = finance([{ ...invoice, valor: undefined }], payment);
  const result = await f.syncMercadoPagoPayment('987', 'webhook');
  assert.equal(result.requiresReview, true);
  assert.equal(result.expectedAmount, 0);
  assert.equal(f.db.snapshot().receivables[0].status, 'Pendente');
  assert.equal((f.db.snapshot().receipts || []).length, 0);
});
test('webhook rejects invalid configured signature and does not expose financial data', async () => {
  let called = 0;
  const db = memoryDb({ boleto_config: { webhook_secret: 'test-secret' } });
  const route = load('app/api/financeiro/mercado-pago/webhook/route.ts', { '@/lib/db': db,
    '@/lib/mercadopago-sync': { syncMercadoPagoPayment: async () => { called++; return { matched: true, paid: true, status: 'approved', lancamento: { private: true } }; } } });
  const url = 'https://example.test/api/financeiro/mercado-pago/webhook?data.id=987';
  const body = JSON.stringify({ type: 'payment', data: { id: '987' } });
  assert.equal((await route.POST(new NextRequest(url, { method: 'POST', body }))).status, 401);
  assert.equal(called, 0);
  const signature = createHmac('sha256', 'test-secret').update('id:987;request-id:request;ts:123;').digest('hex');
  const response = await route.POST(new NextRequest(url, { method: 'POST', body,
    headers: { 'x-signature': `ts=123,v1=${signature}`, 'x-request-id': 'request' } }));
  assert.equal(response.status, 200); assert.equal(called, 1);
  assert.equal((await response.json()).lancamento, undefined);
});
test('webhook fails closed when Mercado Pago signature secret is missing', async () => {
  let called = 0;
  const db = memoryDb({ boleto_config: { access_token: 'test-token' } });
  const route = load('app/api/financeiro/mercado-pago/webhook/route.ts', { '@/lib/db': db,
    '@/lib/mercadopago-sync': { syncMercadoPagoPayment: async () => { called++; return { matched: true, paid: true, status: 'approved' }; } } });
  const response = await route.POST(new NextRequest('https://example.test/api/financeiro/mercado-pago/webhook?data.id=987', {
    method: 'POST', body: JSON.stringify({ type: 'payment', data: { id: '987' } }),
  }));
  assert.equal(response.status, 503);
  assert.equal(called, 0);
  assert.equal(db.snapshot().finance_audit.at(-1).acao, 'mercado_pago_webhook_sem_chave_secreta');
});
test('scheduled payment reconciliation requires internal secret and returns aggregate results only', async () => {
  let calls = 0;
  const route = load('app/api/financeiro/cron-pagamentos/route.ts', {
    '@/lib/mercadopago-sync': { reconcileMercadoPagoPendingReceivables: async options => {
      calls++; assert.equal(options.limit, 12); assert.equal(options.minIntervalMs, 0);
      return { checked: 2, matched: 2, paid: 1, errors: 0 };
    } },
  }, { process: { env: { CRON_SECRET: 'cron-test-secret-with-at-least-32-characters' } } });
  const url = 'https://example.test/api/financeiro/cron-pagamentos';
  assert.equal((await route.POST(new NextRequest(url, { method: 'POST' }))).status, 401);
  assert.equal((await route.POST(new NextRequest(url, { method: 'POST', headers: { 'x-cron-secret': 'wrong' } }))).status, 401);
  assert.equal(calls, 0);
  const response = await route.POST(new NextRequest(url, { method: 'POST', headers: { 'x-cron-secret': 'cron-test-secret-with-at-least-32-characters' } }));
  assert.equal(response.status, 200); assert.equal(calls, 1);
  assert.deepEqual(await response.json().then(({ ok, checked, matched, paid, errors }) => ({ ok, checked, matched, paid, errors })),
    { ok: true, checked: 2, matched: 2, paid: 1, errors: 0 });
});
test('boleto creation sends the resolved technical expiration and installment reference', async () => {
  let submitted;
  const mod = load('lib/criar-pagamento-boleto.ts', { mercadopago: {
    MercadoPagoConfig: class {}, Payment: class { async create(input) { submitted = input; return { id: 987, status: 'pending' }; } },
  } });
  await mod.criarPagamentoBoleto({ accessToken: 'test', transactionAmount: 100, externalReference: 'invoice-1',
    dateOfExpiration: '2026-11-01T12:00:00.000Z',
    payer: { email: 'test@example.test', firstName: 'Test', lastName: 'User', identificationType: 'CPF',
      identificationNumber: '00000000000', address: {} } });
  assert.equal(submitted.body.date_of_expiration, '2026-11-01T12:00:00.000Z');
  assert.equal(submitted.body.external_reference, 'invoice-1');
  assert.equal(submitted.requestOptions.idempotencyKey, 'active-boleto-invoice-1');
});
test('Mercado Pago boleto expiry uses the 30-day maximum without changing installment due date', () => {
  const mod = load('lib/mercadopago-boleto.ts', {
    '@/lib/db': { dbGet: async () => null, dbList: async () => [], dbSet: async () => true, dbUpdate: async () => [] },
    '@/lib/criar-pagamento-boleto': { criarPagamentoBoleto: async () => ({ ok: true }) },
    '@/lib/criar-pagamento-pix': { criarPagamentoPix: async () => ({ ok: true }) },
  });
  const issuedAt = new Date('2026-10-03T12:00:00.000Z');
  const expiry = mod.resolveMercadoPagoBoletoExpiration(issuedAt);
  assert.equal(Date.parse(expiry.dateOfExpiration) - issuedAt.getTime(), 30 * 24 * 60 * 60 * 1000);
  assert.equal(expiry.reason, 'maximum_30_days_from_issue');
  assert.equal(mod.isMercadoPagoPaymentExpired({ status: 'pending', date_of_expiration: '2026-10-02T12:00:00.000Z' }, issuedAt), true);
  assert.equal(mod.isMercadoPagoPaymentExpired({ status: 'approved', date_of_expiration: '2026-10-02T12:00:00.000Z' }, issuedAt), false);
});

const management = load('lib/user-management.ts');
test('last admin cannot be demoted, disabled or soft-deleted', () => {
  for (const [action, body] of [['edit', { perfil: 'Coordenador' }], ['edit', { is_active: false }], ['delete', {}]]) {
    const values = { users: [{ id: 'a', usuario: 'admin', perfil: 'Admin', is_active: true }] };
    assert.throws(() => management.mutateManagedUser(values, { source: 'internal', id: 'a', ...body }, action, 'admin'), /ultimo administrador/);
  }
});
test('admin can edit all supported sources including coordinator, with linked data preserved', () => {
  for (const [source, key, profile] of [['internal', 'users', 'Coordenador'], ['internal', 'users', 'Comercial'], ['teacher', 'teachers', 'Professor'], ['student', 'students', 'Aluno']]) {
    const values = { users: [], [key]: [{ id: 'u', usuario: 'test', nome: 'Original', perfil: profile, aluno_id: 'preserve', responsavel_email: 'guardian@example.test' }] };
    const next = management.mutateManagedUser(values, { source, id: 'u', nome: 'Edited', email: 'new@example.test' }, 'edit', 'admin');
    assert.equal(next.nome, 'Edited'); assert.equal(next.aluno_id, 'preserve');
    assert.equal(next.responsavel_email, 'guardian@example.test');
    assert.equal(values.users_audit.length, 1);
  }
});
test('student login edits cannot collide with active staff accounts', () => {
  const values = {
    users: [{ id: 'staff', usuario: 'shared-login', perfil: 'Coordenador', is_active: true }],
    students: [{ id: 'student', login: 'student-login', nome: 'Student', is_active: true }],
  };
  assert.throws(() => management.mutateManagedUser(values,
    { source: 'student', id: 'student', usuario: 'shared-login' }, 'edit', 'admin'), /login ja esta em uso/);
  assert.equal(values.students[0].login, 'student-login');
});
test('blank teacher identifiers do not match unrelated users', () => {
  assert.equal(management.linkedTeacherUser([{ usuario: '', pessoa: '' }], { nome: 'Teacher' }), null);
});
test('passwords are cryptographic salted hashes and legacy login remains compatible', async () => {
  const { hashPassword, verifyPassword, generatedTempPassword } = load('lib/passwords.ts');
  const bcrypt = require('bcryptjs');
  const password = generatedTempPassword();
  assert.match(password, /[A-Z]/); assert.match(password, /[a-z]/); assert.match(password, /\d/); assert.ok(password.length >= 8);
  const hash = await hashPassword(password);
  assert.notEqual(hash, password); assert.equal(await verifyPassword(password, hash), true);
  assert.equal(await verifyPassword('wrong', hash), false);
  const legacyAdminHash = await bcrypt.hash('AdminAccess2026!', 4);
  assert.equal(await verifyPassword('AdminAccess2026!', legacyAdminHash), true);
  assert.equal(await verifyPassword('wrong', legacyAdminHash), false);
  assert.equal(await verifyPassword('AdminAccess2026!', legacyAdminHash.replace(/^\$2b\$/, '$2y$')), true);
  assert.equal(await verifyPassword('legacy', 'legacy'), true);
  assert.notEqual(await hashPassword(password), hash);
});
test('non-admin roles cannot manage users through any HTTP method', async () => {
  for (const perfil of ['Aluno', 'Professor', 'Coordenador', 'Comercial']) {
    const route = load('app/api/usuarios/gestao/route.ts', { '@/lib/auth': { getSession: async () => ({ perfil }) },
      '@/lib/db': memoryDb(), '@/lib/email': { sendEmail: async () => ({ ok: true }) },
      '@/lib/whatsapp': { sendWhatsApp: async () => ({ ok: true }) } });
    for (const method of ['GET', 'PUT', 'POST', 'DELETE']) {
      assert.equal((await route[method](new NextRequest('https://example.test/api/usuarios/gestao', { method }))).status, 403);
    }
  }
});
test('admin listing includes coordinator and never returns stored credentials', async () => {
  const route = load('app/api/usuarios/gestao/route.ts', { '@/lib/auth': { getSession: async () => ({ perfil: 'Admin' }) },
    '@/lib/db': memoryDb({ users: [{ id: 'c', usuario: 'coord', pessoa: 'Coordinator', perfil: 'Coordenador', senha: 'secret' }] }),
    '@/lib/email': {}, '@/lib/whatsapp': {} });
  const body = await (await route.GET()).json();
  assert.equal(body.usuarios[0].perfil, 'Coordenador'); assert.equal(body.usuarios[0].senha, undefined);
});

test('reset route stores only hash, returns temporary password once and sends only instructions', async () => {
  const db = memoryDb({ users: [{ id: 'c', usuario: 'coord', perfil: 'Coordenador', email: 'test@example.test' }] });
  let message;
  const route = load('app/api/usuarios/gestao/route.ts', { '@/lib/auth': { getSession: async () => ({ perfil: 'Admin', usuario: 'admin' }) },
    '@/lib/db': db, '@/lib/email': { sendEmail: async (_, __, text) => { message = text; return { ok: true }; } }, '@/lib/whatsapp': {} });
  const res = await route.POST(new NextRequest('https://example.test/api/usuarios/gestao', { method: 'POST',
    body: JSON.stringify({ source: 'internal', id: 'c', action: 'reset_password' }) }));
  assert.equal(res.status, 200);
  const body = await res.json(), user = db.snapshot().users[0];
  assert.match(user.senha, /^scrypt\$/); assert.equal(user.must_change_password, true);
  assert.equal(await load('lib/passwords.ts').verifyPassword(body.senha_temporaria, user.senha), true);
  assert.equal(JSON.stringify(db.snapshot()).includes(body.senha_temporaria), false);
  assert.equal(message.includes(body.senha_temporaria), false);
});
test('concurrent admin deactivation retains one active administrator', async () => {
  const db = memoryDb({ users: ['a', 'b'].map(id => ({ id, usuario: id, perfil: 'Admin', is_active: true })) });
  const results = await Promise.allSettled(['a', 'b'].map(id => db.dbTransaction(['users', 'users_audit'], values =>
    management.mutateManagedUser(values, { source: 'internal', id }, 'delete', 'admin'))));
  assert.equal(results.filter(result => result.status === 'fulfilled').length, 1);
  assert.equal(db.snapshot().users.filter(user => user.is_active).length, 1);
});
test('session validation revokes deactivated accounts, reset passwords and stale admin roles', async () => {
  const db = memoryDb({ users: [{ usuario: 'admin', perfil: 'Coordenador', is_active: true }] });
  const auth = load('lib/auth.ts', { '@/lib/db': db,
    jose: { jwtVerify: async () => ({ payload: { usuario: 'admin', perfil: 'Admin' } }) },
    'next/headers': { cookies: async () => ({ get: () => ({ value: 'signed-test-token' }) }) } });
  assert.equal((await auth.getSession()).perfil, 'Coordenador');
  await db.dbSet('users', [{ usuario: 'admin', perfil: 'Admin', is_active: false }]);
  assert.equal(await auth.getSession(), null);
  await db.dbSet('users', [{ usuario: 'admin', perfil: 'Admin', password_reset_at: 'new-version' }]);
  assert.equal(await auth.getSession(), null);
});
test('hashed credentials can login and empty database has no built-in admin fallback', async () => {
  const password = 'Example123!';
  const hash = await load('lib/passwords.ts').hashPassword(password);
  const db = memoryDb({ users: [{ usuario: 'coord', senha: hash, perfil: 'Coordenador', must_change_password: true }] });
  const auth = load('lib/auth.ts', { '@/lib/db': db, jose: {}, 'next/headers': {} });
  assert.equal((await auth.validateCredentials('coord', password)).must_change_password, true);
  assert.equal(await auth.validateCredentials('coord', 'wrong'), null);
  await db.dbSet('users', []);
  assert.equal(await auth.validateCredentials('admin', '2523'), null);
});
test('administrator can authenticate with an existing bcrypt credential hash', async () => {
  const password = 'AdminAccess2026!';
  const hash = await require('bcryptjs').hash(password, 4);
  const db = memoryDb({ users: [{ usuario: 'admin', senha: hash, perfil: 'Admin', pessoa: 'Administrador', is_active: true }] });
  const auth = load('lib/auth.ts', { '@/lib/db': db, jose: {}, 'next/headers': {} });
  const user = await auth.validateCredentials(' ADMIN ', password);
  assert.equal(user.perfil, 'Admin');
  assert.equal(user.usuario, 'admin');
  assert.equal(await auth.validateCredentials('admin', 'wrong'), null);
});
test('valid administrator login is not rejected when last-login audit write fails', async () => {
  const route = load('app/api/auth/route.ts', {
    '@/lib/auth': {
      validateCredentials: async (usuario, senha) => usuario === 'admin' && senha === 'correct'
        ? { usuario: 'admin', perfil: 'Admin', pessoa: 'Administrador' } : null,
      signToken: async () => 'signed-session', COOKIE_NAME: 'ae_session', TTL_SECONDS: 3600,
      dashboardForPerfil: () => '/',
    },
    '@/lib/db': { dbUpdate: async () => { throw new Error('temporary database write failure'); } },
  }, { console: { error: () => {} } });
  const request = new NextRequest('https://example.test/api/auth', { method: 'POST',
    headers: { 'content-type': 'application/json' }, body: JSON.stringify({ usuario: 'admin', senha: 'correct' }) });
  const response = await route.POST(request);
  assert.equal(response.status, 200);
  assert.equal((await response.json()).ok, true);
  assert.match(response.headers.get('set-cookie') || '', /ae_session=signed-session/);
});
test('numeric account ids survive authentication and are matched when opening the session', async () => {
  const hash = await load('lib/passwords.ts').hashPassword('AdminAccess2026!');
  const db = memoryDb({ users: [{ id: 123, usuario: 'admin', senha: hash, perfil: 'Admin', pessoa: 'Administrador', is_active: true }] });
  let payload;
  const auth = load('lib/auth.ts', { '@/lib/db': db,
    jose: { jwtVerify: async () => ({ payload }) },
    'next/headers': { cookies: async () => ({ get: () => ({ value: 'test' }) }) } });
  payload = await auth.validateCredentials('admin', 'AdminAccess2026!');
  assert.equal(payload.record_id, '123');
  assert.equal((await auth.getSession()).perfil, 'Admin');
});
test('password change replaces hash and updates session while clearing mandatory-change flag', async () => {
  const hash = await load('lib/passwords.ts').hashPassword('Temporary1!');
  const db = memoryDb({ users: [{ usuario: 'coord', senha: hash, must_change_password: true, password_reset_at: 'v1' }] });
  let signed;
  const route = load('app/api/auth/alterar-senha/route.ts', { '@/lib/db': db,
    '@/lib/auth': { getSession: async () => ({ usuario: 'coord', perfil: 'Coordenador', password_reset_at: 'v1' }),
      signToken: async value => { signed = value; return 'new-token'; }, COOKIE_NAME: 'ae_session', TTL_SECONDS: 100,
      dashboardForPerfil: () => '/' } });
  const request = new NextRequest('https://example.test/api/auth/alterar-senha', { method: 'POST',
    body: JSON.stringify({ senha_atual: 'Temporary1!', nova_senha: 'Personal123!' }) });
  assert.equal((await route.POST(request)).status, 200);
  assert.equal(signed.must_change_password, false);
  assert.equal(db.snapshot().users[0].must_change_password, false);
  assert.equal(await load('lib/passwords.ts').verifyPassword('Personal123!', db.snapshot().users[0].senha), true);
});

test('students sharing a birthdate login are identified by credential and stable record id', async () => {
  const db = memoryDb({ students: [
    { id: 's1', nome: 'Student One', login: '01012010', senha: '111111' },
    { id: 's2', nome: 'Student Two', login: '01012010', senha: '222222' },
  ] });
  let payload;
  const auth = load('lib/auth.ts', { '@/lib/db': db,
    jose: { jwtVerify: async () => ({ payload }) },
    'next/headers': { cookies: async () => ({ get: () => ({ value: 'test' }) }) } });
  payload = await auth.validateStudentCredentials('01012010', '222222');
  assert.equal(payload.record_id, 's2');
  assert.equal((await auth.getSession()).record_id, 's2');
  assert.equal(await auth.validateStudentCredentials('01012010', 'wrong'), null);
});

test('database transaction locks absent keys and rolls back all related writes on failure', async () => {
  const queries = [];
  let released = 0;
  const client = { query: async (sql, args) => {
    queries.push({ sql, args });
    if (sql.startsWith('INSERT') && args[0] === 'receipts') throw new Error('simulated write failure');
    return { rows: [] };
  }, release: () => { released++; } };
  const db = load('lib/db.ts', { pg: { Pool: class { async connect() { return client; } } } },
    { process: { env: { ACTIVE_DATABASE_URL: 'postgresql://test.invalid/test?sslmode=disable' } } });
  await assert.rejects(() => db.dbTransaction(['receivables', 'receipts'], values => {
    values.receivables = [{ id: 'test', status: 'Pago' }]; values.receipts = [{ id: 'receipt' }];
  }), /simulated write failure/);
  assert.equal(queries.filter(q => q.sql.includes('pg_advisory_xact_lock')).length, 2);
  assert.equal(queries.some(q => q.sql === 'COMMIT'), false);
  assert.equal(queries.at(-1).sql, 'ROLLBACK'); assert.equal(released, 1);
});
