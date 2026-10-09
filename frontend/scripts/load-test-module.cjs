// Compile the project's TypeScript for node:test, using only the existing compiler.
// Database, network and session dependencies are explicitly replaced by each test.
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const { createRequire } = require('node:module');
const ts = require('typescript');
const root = path.resolve(__dirname, '..');

exports.load = function load(relative, mocks = {}, globals = {}) {
  const cache = new Map();
  function compile(filename) {
    if (cache.has(filename)) return cache.get(filename).exports;
    const mod = { exports: {} };
    cache.set(filename, mod);
    const native = createRequire(filename);
    const source = ts.transpileModule(fs.readFileSync(filename, 'utf8'), {
      compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022, esModuleInterop: true },
      fileName: filename,
    }).outputText;
    const requireMock = (id) => {
      if (id in mocks) return mocks[id];
      if (id.startsWith('@/') || id.startsWith('.')) {
        let resolved = id.startsWith('@/') ? path.join(root, id.slice(2)) : path.resolve(path.dirname(filename), id);
        if (!path.extname(resolved)) resolved += '.ts';
        const alias = '@/' + path.relative(root, resolved).replaceAll('\\', '/').replace(/\.ts$/, '');
        if (alias in mocks) return mocks[alias];
        return compile(resolved);
      }
      return native(id);
    };
    vm.runInNewContext(source, { module: mod, exports: mod.exports, require: requireMock,
      console, Buffer, URL, AbortSignal, TextEncoder, crypto: require('node:crypto').webcrypto,
      setTimeout, clearTimeout, process: { env: { ACTIVE_MERCADO_PAGO_ACCESS_TOKEN: 'test-only' } },
      fetch: () => { throw new Error('Unexpected network access'); }, ...globals }, { filename });
    return mod.exports;
  }
  return compile(path.join(root, relative));
};

exports.memoryDb = function memoryDb(initial = {}) {
  let data = structuredClone(initial), tail = Promise.resolve();
  const key = name => name.replace(/\.json$/, '');
  const db = {
    snapshot: () => structuredClone(data),
    dbGet: async name => structuredClone(data[key(name)] ?? null),
    dbList: async name => structuredClone(data[key(name)] ?? []),
    dbListFresh: async name => structuredClone(data[key(name)] ?? []),
    dbSet: async (name, value) => { data[key(name)] = structuredClone(value); },
    dbTransaction: async (keys, update) => {
      const run = tail.then(async () => {
        const copy = structuredClone(data);
        const result = await update(copy);
        data = copy;
        return result;
      });
      tail = run.catch(() => {});
      return run;
    },
    dbUpdate: async (name, update, fallback) => db.dbTransaction([name], async values => {
      const result = await update(values[key(name)] ?? fallback);
      values[key(name)] = result;
      return result;
    }),
  };
  return db;
};
