// Validates batch release re-runs against their ladder games in parallel (compare.mjs validateRun), writing
// one validation JSON per game. Called by batch.py.
//   node tools/replay/harness/validate_batch.mjs JOBS.json [--threads N]
// JOBS.json: [{key, inputs, ladderFuel, team, release, out, extra}] (absolute paths; release may be null
// when not run). `extra` is copied into the output.
import fs from 'node:fs';
import os from 'node:os';
import { fileURLToPath } from 'node:url';
import { Worker, isMainThread, parentPort } from 'node:worker_threads';
import { validateRun, bundleFiles } from './compare.mjs';
import { loadInputs } from './gen_puppet.mjs';

function puppetErrors(bytes, team) {
  const files = bundleFiles(bytes);
  const out = files[`team-${'ab'[team]}.stdout`];
  if (!out) return null;
  const lines = out.toString('latin1').replace(/\0/g, '').split('\n').filter(l => l.startsWith('PUPPET-ERR'));
  return { count: lines.length, first: lines.slice(0, 10) };
}

async function validate(job) {
  const orig = loadInputs(job.inputs);
  const ladderFuel = job.ladderFuel ? fs.readFileSync(job.ladderFuel) : null;
  const out = { key: job.key, ...job.extra };
  if (job.release && fs.existsSync(job.release)) {
    const raw = fs.readFileSync(job.release);
    out.release = (await validateRun(orig, raw, { ladderFuel, team: job.team })).res;
    out.puppetErrors = puppetErrors(raw, 1 - job.team);
  }
  fs.writeFileSync(job.out, JSON.stringify(out, null, 1));
  return out;
}

if (isMainThread) {
  const args = process.argv.slice(2);
  const ti = args.indexOf('--threads');
  const threads = ti >= 0 ? +args[ti + 1] : Math.max(1, os.cpus().length - 1);
  const jobs = JSON.parse(fs.readFileSync(args[0], 'utf8'));
  let next = 0, done = 0, failed = 0;
  const t0 = Date.now();
  await Promise.all(Array.from({ length: Math.min(threads, jobs.length) }, () => new Promise(res => {
    const w = new Worker(fileURLToPath(import.meta.url));
    const feed = () => { if (next < jobs.length) w.postMessage(jobs[next++]); else { w.terminate(); res(); } };
    w.on('message', m => {
      done++;
      if (m.error) { failed++; console.error(`${m.key}: ${m.error}`); }
      if (done % 25 === 0 || done === jobs.length) console.error(`validated ${done}/${jobs.length} (${((Date.now() - t0) / 1000).toFixed(0)} s)`);
      feed();
    });
    w.on('error', e => { console.error(e); failed++; res(); });
    feed();
  })));
  process.exit(failed ? 1 : 0);
} else {
  parentPort.on('message', async job => {
    try { await validate(job); parentPort.postMessage({ key: job.key }); }
    catch (e) { parentPort.postMessage({ key: job.key, error: String(e.stack ?? e) }); }
  });
}
