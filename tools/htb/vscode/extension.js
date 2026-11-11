// HTB: C++ written like Java (tools/htb/hgen.py). A clangd of its own serves .htb files -- squiggles while typing, completion,
// hover, go to definition -- reading the per-file .clangd hgen writes (each file sees what the bot's other files declare).
// Saving an .htb file reruns tools/htb/hgen.py for its bot, so those declarations stay current.
const vscode = require('vscode');
const path = require('path');
const fs = require('fs');
const cp = require('child_process');
const { LanguageClient } = require('vscode-languageclient/node');
const { toSource } = require('./map');

let client = null;
let out = null;

function findClangd() {
  const configured = vscode.workspace.getConfiguration('htb').get('clangdPath');
  const win = process.env.ProgramFiles ? path.join(process.env.ProgramFiles, 'LLVM', 'bin', 'clangd.exe') : null;
  for (const c of [configured, '/opt/homebrew/opt/llvm/bin/clangd', '/usr/local/opt/llvm/bin/clangd', win]) if (c && fs.existsSync(c)) return c;
  return 'clangd';
}

// The bot folder (bots/<bot> or bots/archives/<bot>) holding a file.
function botDirOf(file) {
  for (let d = path.dirname(file); d !== path.dirname(d); d = path.dirname(d)) {
    const up = path.dirname(d);
    if (path.basename(up) === 'archives' && path.basename(path.dirname(up)) === 'bots') return d;
    if (path.basename(up) === 'bots' && path.basename(d) !== 'archives') return d;
  }
  return null;
}

// The project root above a bot folder.
function rootOf(bot) {
  let root = path.dirname(bot);
  while (path.basename(root) !== 'bots') root = path.dirname(root);
  return path.dirname(root);
}

function runHgen(bot) {
  const root = rootOf(bot);
  const hgen = [path.join(root, 'tools', 'htb', 'hgen.py'), path.join(root, 'tools', 'hgen.py')].find((p) => fs.existsSync(p));
  if (!hgen) { out.appendLine(`no tools/htb/hgen.py under ${root}`); return Promise.resolve(); }
  const python = vscode.workspace.getConfiguration('htb').get('python') || (process.platform === 'win32' ? 'py' : 'python3');
  return new Promise((resolve) => {
    cp.execFile(python, [hgen, bot], { cwd: root }, (err, stdout, stderr) => {
      const text = `${stdout || ''}${stderr || ''}`.trim();
      if (text) out.appendLine(text);
      if (err) out.appendLine(`hgen failed for ${path.basename(bot)}: ${err.message}`);
      resolve();
    });
  });
}

// clangd answers with places in the generated C++ (src/, .cambc/hgen/): send the editor to the .htb line instead.
function mapUri(uri, range) {
  if (!uri || uri.scheme !== 'file') return null;
  const a = toSource(uri.fsPath, range.start.line);
  if (!a) return null;
  const b = toSource(uri.fsPath, range.end.line) || a;
  return { uri: vscode.Uri.file(a.file), range: new vscode.Range(a.line, range.start.character, b.file === a.file ? b.line : a.line, range.end.character) };
}
function mapLocations(result) {
  if (!result) return result;
  const one = (r) => {
    if (r.targetUri) {   // LocationLink
      const m = mapUri(r.targetUri, r.targetRange), s = mapUri(r.targetUri, r.targetSelectionRange || r.targetRange);
      return m ? { ...r, targetUri: m.uri, targetRange: m.range, targetSelectionRange: s ? s.range : m.range } : r;
    }
    const m = mapUri(r.uri, r.range);
    return m ? new vscode.Location(m.uri, m.range) : r;
  };
  return Array.isArray(result) ? result.map(one) : one(result);
}
const mapped = (fn) => async (...args) => mapLocations(await args[args.length - 1](...args.slice(0, -1)));

function startClient(context) {
  client = new LanguageClient('htb', 'HTB (clangd)',
    { command: findClangd(), args: ['--header-insertion=never', '--log=error', '--pch-storage=memory'] },
    { documentSelector: [{ scheme: 'file', language: 'htb' }], outputChannel: out,
      middleware: { provideDefinition: mapped(), provideDeclaration: mapped(), provideTypeDefinition: mapped(),
                    provideImplementation: mapped(), provideReferences: mapped() } });
  context.subscriptions.push(client);
  return client.start();
}

// One hgen run per bot at a time; a save and the file events around it share one run.
const runs = new Map();     // bot -> { timer, running, again }
const SOURCES = /\.(htb|h|hh|hpp|hxx|inl|ipp|tpp)$/;   // .htb files, and headers hgen copies into src/
function scheduleHgen(file) {
  const bot = botDirOf(file);
  if (!bot) return;
  const top = path.relative(bot, file).split(path.sep)[0];
  if (['src', '.cambc', 'build'].includes(top)) return;   // hgen's own output: never a reason to run it
  const r = runs.get(bot) || {};
  runs.set(bot, r);
  clearTimeout(r.timer);
  r.timer = setTimeout(async () => {
    if (r.running) { r.again = true; return; }
    r.running = true;
    do { r.again = false; await runHgen(bot); } while (r.again);
    r.running = false;
  }, 300);
}

async function activate(context) {
  out = vscode.window.createOutputChannel('HTB');
  context.subscriptions.push(out);
  // Fresh declarations for every .htb bot in the workspace (files in subfolders too) before clangd reads them.
  const files = await vscode.workspace.findFiles('bots/*/**/*.htb', '**/{src,.cambc,node_modules}/**');
  await Promise.all([...new Set(files.map((u) => botDirOf(u.fsPath)).filter(Boolean))].map(runHgen));
  context.subscriptions.push(vscode.workspace.onDidSaveTextDocument((doc) => {
    if (SOURCES.test(doc.fileName)) scheduleHgen(doc.fileName);
  }));
  // Files added, deleted or renamed (here or outside VS Code, e.g. by git) change what the other files see.
  const watcher = vscode.workspace.createFileSystemWatcher('**/bots/*/**/*.{htb,h,hh,hpp,hxx,inl,ipp,tpp}');
  for (const event of [watcher.onDidCreate, watcher.onDidDelete, watcher.onDidChange])
    context.subscriptions.push(event((uri) => scheduleHgen(uri.fsPath)));
  context.subscriptions.push(watcher);
  // A deleted or renamed folder of .htb files reports only the folder.
  context.subscriptions.push(vscode.workspace.onDidDeleteFiles((e) => e.files.forEach((u) => scheduleHgen(u.fsPath))));
  context.subscriptions.push(vscode.workspace.onDidRenameFiles((e) => e.files.forEach((f) => {
    scheduleHgen(f.oldUri.fsPath);
    scheduleHgen(f.newUri.fsPath);
  })));
  context.subscriptions.push(vscode.commands.registerCommand('htb.restart', async () => {
    if (client) await client.stop();
    await startClient(context);
  }));
  out.appendLine(`HTB: clangd ${findClangd()}`);
  await startClient(context);
}

function deactivate() { return client ? client.stop() : undefined; }

module.exports = { activate, deactivate };
