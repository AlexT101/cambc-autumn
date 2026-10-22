// Talks to clangd exactly as extension.js does (same command, flags, language id) and prints what VS Code would show.
const cp = require('child_process'), path = require('path'), fs = require('fs');
const rpc = require('vscode-jsonrpc/node');
let ROOT = __dirname;
while (!fs.existsSync(path.join(ROOT, 'cambc.toml')) && path.dirname(ROOT) !== ROOT) ROOT = path.dirname(ROOT);
// the example bot: the first bots/<bot>/bot.htb with the starter's play_turn (htb-starter, or starter-cpp here)
const file = fs.readdirSync(path.join(ROOT, 'bots')).map((b) => path.join(ROOT, 'bots', b, 'bot.htb'))
  .find((f) => fs.existsSync(f) && fs.readFileSync(f, 'utf8').includes('void play_turn() {'));
console.log('testing', path.relative(ROOT, file));
const clangd = fs.existsSync('/opt/homebrew/opt/llvm/bin/clangd') ? '/opt/homebrew/opt/llvm/bin/clangd' : 'clangd';
const proc = cp.spawn(clangd, ['--header-insertion=never', '--log=error', '--pch-storage=memory'], { cwd: ROOT });
const conn = rpc.createMessageConnection(new rpc.StreamMessageReader(proc.stdout), new rpc.StreamMessageWriter(proc.stdin));
const diags = [];
conn.onNotification('textDocument/publishDiagnostics', (p) => diags.push(p));
conn.listen();
const uri = 'file://' + file;
const wait = (ms) => new Promise((r) => setTimeout(r, ms));
const waitDiag = async (version) => { for (let i = 0; i < 100; i++) { const d = diags.filter((x) => x.version === version); if (d.length) return d[d.length - 1].diagnostics; await wait(100); } return null; };
(async () => {
  await conn.sendRequest('initialize', { processId: process.pid, rootUri: 'file://' + ROOT, capabilities: { textDocument: { publishDiagnostics: { versionSupport: true }, completion: { completionItem: { snippetSupport: false } } } } });
  conn.sendNotification('initialized', {});
  const clean = fs.readFileSync(file, 'utf8');
  conn.sendNotification('textDocument/didOpen', { textDocument: { uri, languageId: 'htb', version: 1, text: clean } });
  const d1 = await waitDiag(1);
  console.log('clean bot.htb:', d1 ? `${d1.length} diagnostics` : 'no answer', (d1 || []).map((d) => `L${d.range.start.line + 1}: ${d.message}`));
  // completion: a function from random.htb, typed in bot.htb
  const lines = clean.split('\n'), li = lines.findIndex((l) => l.includes('void play_turn() {')) + 1;
  const typed = lines.slice(0, li).concat(['        random_'], lines.slice(li)).join('\n');
  conn.sendNotification('textDocument/didChange', { textDocument: { uri, version: 2 }, contentChanges: [{ text: typed }] });
  const comp = await conn.sendRequest('textDocument/completion', { textDocument: { uri }, position: { line: li, character: 15 } });
  const items = (comp.items || comp).map((c) => c.label.trim()).filter((l) => l.startsWith('random'));
  console.log('completion after "random_":', items);
  // errors: an undeclared name and an unclosed bracket
  const broken = lines.slice(0, li).concat(['        int x = random_numbr(3);', '        if (x > 1 {'], lines.slice(li)).join('\n');
  conn.sendNotification('textDocument/didChange', { textDocument: { uri, version: 3 }, contentChanges: [{ text: broken }] });
  const d3 = await waitDiag(3);
  console.log('broken bot.htb:', (d3 || []).map((d) => `L${d.range.start.line + 1}:${d.range.start.character + 1} [${d.severity === 1 ? 'error' : 'warning'}] ${d.message.split('\n')[0]}`));
  // hover on a class from another file
  conn.sendNotification('textDocument/didChange', { textDocument: { uri, version: 4 }, contentChanges: [{ text: clean }] });
  await waitDiag(4);
  const callLine = lines.findIndex((l) => l.includes('random_number(3)')), callCol = lines[callLine].indexOf('random_number') + 3;
  const hov = await conn.sendRequest('textDocument/hover', { textDocument: { uri }, position: { line: callLine, character: callCol } });
  const def = await conn.sendRequest('textDocument/definition', { textDocument: { uri }, position: { line: callLine, character: callCol } });
  console.log('go to definition of random_number ->', (Array.isArray(def) ? def : [def]).map((d) => d && `${path.relative(ROOT, (d.uri || d.targetUri).replace('file://', ''))}:${((d.range || d.targetRange).start.line) + 1}`));
  const { toSource } = require('./map');
  console.log('  ... the extension sends VS Code to', (Array.isArray(def) ? def : [def]).map((d) => { const f = (d.uri || d.targetUri).replace('file://', ''), l = (d.range || d.targetRange).start.line; const m = toSource(f, l); return m ? `${path.relative(ROOT, m.file)}:${m.line + 1}` : 'unchanged'; }));
  console.log('hover on random_number (defined in random.htb):', hov ? hov.contents.value.split('\n').slice(0, 3).join(' | ') : null);
  await conn.sendRequest('shutdown'); conn.sendNotification('exit'); setTimeout(() => process.exit(0), 300);
})();
