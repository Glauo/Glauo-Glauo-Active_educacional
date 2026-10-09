// Local browser check with synthetic data only. Never connects to production.
const { spawn } = require('node:child_process');
const { once } = require('node:events');
const fs = require('node:fs');
const path = require('node:path');
const assert = require('node:assert/strict');
const { randomBytes } = require('node:crypto');
const WebSocket = require('next/dist/compiled/ws');
const root = path.resolve(__dirname, '..');
const build = path.join(root, '.next');
const profile = fs.mkdtempSync(path.join(build, 'users-ui-smoke-'));
const chromePath = process.env.CHROME_PATH || 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe';
const secret = randomBytes(48).toString('hex');
const port = 4317;
const pause = ms => new Promise(resolve => setTimeout(resolve, ms));

(async () => {
  let server, browser, socket, command;
  try {
    server = spawn(process.execPath, ['node_modules/next/dist/bin/next', 'start', '--hostname', '127.0.0.1', '-p', String(port)], {
      cwd: root, windowsHide: true, stdio: 'ignore', env: { ...process.env, JWT_SECRET: secret,
        ACTIVE_DATABASE_URL: '', DATABASE_URL: '', POSTGRES_URL: '' },
    });
    let ready = false;
    for (let i = 0; i < 80; i++) {
      if (await fetch(`http://127.0.0.1:${port}/login`).then(r => r.ok).catch(() => false)) { ready = true; break; }
      await pause(250);
    }
    assert.ok(ready, 'Local test server did not start');
    browser = spawn(chromePath, ['--headless=new', '--disable-gpu', '--no-first-run', '--no-default-browser-check',
      '--remote-debugging-port=0', `--user-data-dir=${profile}`, 'about:blank'], { windowsHide: true, stdio: 'ignore' });
    const portFile = path.join(profile, 'DevToolsActivePort');
    for (let i = 0; !fs.existsSync(portFile) && i < 80; i++) await pause(250);
    const cdpPort = fs.readFileSync(portFile, 'utf8').split('\n')[0];
    const targets = await fetch(`http://127.0.0.1:${cdpPort}/json/list`).then(r => r.json());
    socket = new WebSocket(targets.find(target => target.type === 'page').webSocketDebuggerUrl);
    await once(socket, 'open');
    let id = 0;
    const pending = new Map(), errors = [];
    command = (method, params = {}) => new Promise((resolve, reject) => {
      const messageId = ++id;
      const timer = setTimeout(() => { pending.delete(messageId); reject(new Error(`CDP timeout: ${method}`)); }, 15000);
      pending.set(messageId, { resolve, reject, timer });
      socket.send(JSON.stringify({ id: messageId, method, params }));
    });
    socket.on('message', raw => {
      const message = JSON.parse(String(raw));
      if (message.id && pending.has(message.id)) {
        const task = pending.get(message.id); pending.delete(message.id); clearTimeout(task.timer);
        message.error ? task.reject(new Error(message.error.message)) : task.resolve(message.result);
      }
      if (message.method === 'Runtime.exceptionThrown') errors.push(message.params.exceptionDetails.text);
      if (message.method === 'Fetch.requestPaused') {
        const { requestId, request } = message.params;
        const url = new URL(request.url);
        let body = { blockedRoutes: [], modules: [] };
        if (url.pathname === '/api/usuarios/gestao') body = { usuarios: [{ id: 'test-coordinator', source: 'internal',
          nome: 'Coordenador de teste', usuario: 'coordenador.teste', perfil: 'Coordenador', email: 'test@example.invalid',
          telefone: '(11) 99999-0000', cpf: '000.000.000-00', status: 'Ativo', is_active: true, tem_acesso: true }] };
        if (url.pathname === '/api/acessos/permissoes') body = { usuarios: [] };
        void command('Fetch.fulfillRequest', { requestId, responseCode: 200,
          responseHeaders: [{ name: 'Content-Type', value: 'application/json' }],
          body: Buffer.from(JSON.stringify(body)).toString('base64') }).catch(error => errors.push(error.message));
      }
    });
    await command('Page.enable'); await command('Runtime.enable'); await command('Network.enable');
    await command('Fetch.enable', { patterns: [{ urlPattern: `http://127.0.0.1:${port}/api/*` }] });
    const { SignJWT } = await import('jose');
    const token = await new SignJWT({ usuario: 'test-admin', perfil: 'Admin', pessoa: 'Administrador teste' })
      .setProtectedHeader({ alg: 'HS256' }).setIssuedAt().setExpirationTime('5m').sign(new TextEncoder().encode(secret));
    await command('Network.setCookie', { name: 'ae_session', value: token, url: `http://127.0.0.1:${port}`, httpOnly: true });
    for (const width of [1366, 390]) {
      await command('Emulation.setDeviceMetricsOverride', { width, height: 844, deviceScaleFactor: 1, mobile: width < 500 });
      await command('Page.navigate', { url: `http://127.0.0.1:${port}/usuarios/credenciais` });
      let loaded = false;
      for (let i = 0; i < 60; i++) {
        const result = await command('Runtime.evaluate', { expression: 'document.body.innerText.includes("Coordenador de teste")', returnByValue: true });
        if (result.result.value) { loaded = true; break; }
        await pause(250);
      }
      assert.ok(loaded, 'User listing did not render');
      const layout = await command('Runtime.evaluate', { expression: 'JSON.stringify({width:innerWidth,scroll:document.documentElement.scrollWidth,buttons:[...document.querySelectorAll("button")].some(b=>b.textContent.includes("Redefinir senha"))})', returnByValue: true });
      const info = JSON.parse(layout.result.value);
      assert.ok(info.buttons); assert.ok(info.scroll <= info.width + 1, `Horizontal page overflow at ${width}: ${info.scroll}`);
      const shot = await command('Page.captureScreenshot', { format: 'png', captureBeyondViewport: false });
      fs.writeFileSync(path.join(build, `users-ui-${width}.png`), Buffer.from(shot.data, 'base64'));
      console.log(`Users UI ${width}px: rendered, actions present, no page overflow`);
    }
    assert.equal(errors.length, 0, errors.join('\n'));
  } finally {
    if (command && socket?.readyState === WebSocket.OPEN) await command('Browser.close').catch(() => {});
    socket?.close(); browser?.kill(); server?.kill();
    await pause(2500);
    const resolved = path.resolve(profile);
    if (!resolved.startsWith(build + path.sep) || !path.basename(resolved).startsWith('users-ui-smoke-')) throw new Error('Invalid cleanup path');
    try { fs.rmSync(resolved, { recursive: true, force: true, maxRetries: 20, retryDelay: 300 }); }
    catch { console.error(`Test profile cleanup pending: ${resolved}`); }
  }
})().catch(error => { console.error(error.message); process.exitCode = 1; });
