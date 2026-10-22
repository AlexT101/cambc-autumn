// node clangd_diag.js CLANGD ROOT FILE... -> JSON {file: [{line, col, severity, code, message}]} for each .htb file,
// opened the way the HTB extension opens them (language htb; the bot's .clangd supplies -xc++ and the context).
const cp = require('child_process'), fs = require('fs'), path = require('path');
const rpc = require(path.join(__dirname, '..', 'vscode', 'node_modules', 'vscode-jsonrpc', 'node'));
const [clangd, root, ...files] = process.argv.slice(2);
const proc = cp.spawn(clangd, ['--header-insertion=never', '--log=error', '--pch-storage=memory', '--background-index=false'], { cwd: root });
const conn = rpc.createMessageConnection(new rpc.StreamMessageReader(proc.stdout), new rpc.StreamMessageWriter(proc.stdin));
const got = new Map();
conn.onNotification('textDocument/publishDiagnostics', (p) => { if (p.version === 1) got.set(decodeURIComponent(p.uri.replace('file://', '')), p.diagnostics); });
conn.listen();
(async () => {
  await conn.sendRequest('initialize', { processId: process.pid, rootUri: 'file://' + root,
    capabilities: { textDocument: { publishDiagnostics: { versionSupport: true } } } });
  conn.sendNotification('initialized', {});
  for (const f of files)
    conn.sendNotification('textDocument/didOpen', { textDocument: { uri: 'file://' + encodeURI(f).replace(/#/g, '%23'), languageId: 'htb', version: 1, text: fs.readFileSync(f, 'utf8') } });
  for (let i = 0; i < 1200 && files.some((f) => !got.has(f)); i++) await new Promise((r) => setTimeout(r, 50));
  const out = {};
  for (const f of files) out[f] = got.has(f) ? got.get(f).map((d) => ({ line: d.range.start.line + 1, col: d.range.start.character + 1,
    severity: d.severity, code: d.code, message: d.message.split('\n')[0] })) : null;
  process.stdout.write(JSON.stringify(out));
  await conn.sendRequest('shutdown'); conn.sendNotification('exit'); setTimeout(() => process.exit(0), 100);
})();
