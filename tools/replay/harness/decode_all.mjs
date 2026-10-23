// Decodes many replays' input streams in parallel (inputs.mjs), one gzipped JSON per replay.
//   node tools/replay/harness/decode_all.mjs --list LIST.json --out DIR [--threads N] [--force]
// LIST.json: [{key, replay}] (paths relative to the repo root or absolute).
import fs from 'node:fs';
import path from 'node:path';
import os from 'node:os';
import zlib from 'node:zlib';
import { fileURLToPath } from 'node:url';
import { Worker, isMainThread, parentPort, workerData } from 'node:worker_threads';
import { decodeInputs } from './inputs.mjs';

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..', '..', '..');

if (isMainThread) {
  const args = process.argv.slice(2);
  const opt = { threads: Math.max(1, os.cpus().length - 2), force: false };
  for (let i = 0; i < args.length; i++) {
    if (args[i] === '--list') opt.list = args[++i];
    else if (args[i] === '--out') opt.out = args[++i];
    else if (args[i] === '--threads') opt.threads = +args[++i];
    else if (args[i] === '--force') opt.force = true;
  }
  if (!opt.list || !opt.out) { console.error('usage: decode_all.mjs --list LIST.json --out DIR [--threads N] [--force]'); process.exit(2); }
  fs.mkdirSync(opt.out, { recursive: true });
  const todo = JSON.parse(fs.readFileSync(opt.list, 'utf8')).filter(g => opt.force || !fs.existsSync(path.join(opt.out, `${g.key}.json.gz`)));
  let next = 0, done = 0, failed = 0;
  const t0 = Date.now();
  await Promise.all(Array.from({ length: Math.min(opt.threads, todo.length) }, () => new Promise(res => {
    const w = new Worker(fileURLToPath(import.meta.url), { workerData: { out: opt.out } });
    const feed = () => { if (next < todo.length) w.postMessage(todo[next++]); else { w.terminate(); res(); } };
    w.on('message', m => {
      done++;
      if (m.error) { failed++; console.error(`${m.key}: ${m.error}`); }
      if (done % 25 === 0 || done === todo.length) console.error(`${done}/${todo.length} (${((Date.now() - t0) / 1000).toFixed(0)} s)`);
      feed();
    });
    w.on('error', e => { console.error(e); failed++; res(); });
    feed();
  })));
  process.exit(failed ? 1 : 0);
} else {
  parentPort.on('message', async g => {
    try {
      const file = path.isAbsolute(g.replay) ? g.replay : path.join(ROOT, g.replay);
      const d = await decodeInputs(fs.readFileSync(file));
      d.key = g.key;
      fs.writeFileSync(path.join(workerData.out, `${g.key}.json.gz`), zlib.gzipSync(JSON.stringify(d)));
      parentPort.postMessage({ key: g.key });
    } catch (e) { parentPort.postMessage({ key: g.key, error: String(e.stack ?? e) }); }
  });
}
