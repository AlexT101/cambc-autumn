// Outcomes of local replays for the draft lab, without extract.mjs's per-step decoding: each team's
// tributed and carried gems at checkpoint rounds and at the end, and every champion's engine statistics.
//   node tools/draftlab/outcome.mjs FILE_OR_DIR... [--out FILE.jsonl] [--threads N] [--delete]
// One JSON line per replay: {file, rounds, winner, draft, cp: {round: [[tributed, carried] A, B]}, champions}.
// Carried gems count because some champions (Prism) bank late by design. --delete removes each replay once read.
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { Worker, isMainThread, parentPort, workerData } from 'node:worker_threads';
import { fileURLToPath } from 'node:url';
import { Engine, compileEngine, replayEngine } from '../replay/engine.mjs';

const CHECKPOINTS = [300, 600, 1000, 1500];
// Snapshots are read only this often (in engine steps, ~200 a round), so checkpoints land a round or two late.
const READ_EVERY = 256;

const bags = s => {
  const out = [[s.header().submittedGems[0], 0], [s.header().submittedGems[1], 0]];
  for (const c of s.championsLite()) if (c.alive && c.team < 2) out[c.team][1] += c.gems;
  return out;
};

async function outcome(engines, file) {
  const bytes = fs.readFileSync(file), version = replayEngine(bytes);
  engines[version] ??= await Engine.create(await compileEngine(version));
  const g = engines[version].openReplay(bytes);
  try {
    g.seekStart();
    const cp = {};
    let next = 0, steps = 0;
    while (g.next()) {
      if (++steps % READ_EVERY || next >= CHECKPOINTS.length) continue;
      const s = g.read();
      while (next < CHECKPOINTS.length && s.header().round >= CHECKPOINTS[next]) cp[CHECKPOINTS[next++]] = bags(s);
    }
    const s = g.read(), h = s.header(), end = bags(s), { summary, champions } = g.statistics();
    cp.end = end;
    const lite = new Map(s.championsLite().map(c => [c.id, c]));
    return {
      file: path.basename(file), rounds: summary.round, winner: summary.outcome === 1 ? 0 : 1, outcome: summary.outcome,
      draft: summary.drafts.map((d, t) => d.slice(0, summary.draftCounts[t])), cp, tributed: h.submittedGems,
      champions: champions.map(c => ({ id: c.champion, team: c.team, type: c.type, carried: lite.get(c.champion)?.alive ? lite.get(c.champion).gems : 0,
        kills: c.kills, deaths: c.deaths, earnedGold: c.earnedGold, collectedGems: c.collectedGems, submittedGems: c.submittedGems,
        monsterDamageDone: Math.round(c.monsterDamageDone), monsterDamageTaken: Math.round(c.monsterDamageTaken),
        championDamageDone: Math.round(c.championDamageDone), championDamageTaken: Math.round(c.championDamageTaken),
        healingDone: Math.round(c.healingDone), shieldingDone: Math.round(c.shieldingDone) })),
    };
  } finally { g.destroy(); }
}

if (!isMainThread) {
  const engines = {};
  parentPort.on('message', async file => {
    try { parentPort.postMessage({ file, row: await outcome(engines, file) }); }
    catch (e) { parentPort.postMessage({ file, error: e.message }); }
  });
} else {
  const args = process.argv.slice(2), inputs = [];
  let out = null, threads = Math.max(1, Math.min(8, os.cpus().length - 2)), del = false;
  for (let i = 0; i < args.length; i++) {
    if (args[i] === '--out') out = path.resolve(args[++i]);
    else if (args[i] === '--threads') threads = Math.max(1, +args[++i]);
    else if (args[i] === '--delete') del = true;
    else inputs.push(args[i]);
  }
  const files = [];
  const walk = p => fs.statSync(p).isDirectory() ? fs.readdirSync(p).sort().forEach(f => walk(path.join(p, f))) : p.endsWith('.repl26a') && files.push(p);
  inputs.forEach(p => walk(path.resolve(p)));
  const sink = out ? fs.openSync(out, 'a') : 1;
  let done = 0, failed = 0, queued = 0;
  const t0 = Date.now();
  const me = fileURLToPath(import.meta.url);
  await Promise.all(Array.from({ length: Math.min(threads, files.length) }, () => new Promise(resolve => {
    const w = new Worker(me);
    const feed = () => queued < files.length ? w.postMessage(files[queued++]) : (w.terminate(), resolve());
    w.on('message', ({ file, row, error }) => {
      if (error) { failed++; console.error(`FAILED ${file}: ${error}`); }
      else { fs.writeSync(sink, JSON.stringify(row) + '\n'); if (del) fs.unlinkSync(file); }
      done++;
      feed();
    });
    feed();
  })));
  if (out) fs.closeSync(sink);
  console.error(`${done - failed}/${files.length} replays in ${((Date.now() - t0) / 1000).toFixed(1)} s, ${failed} failed`);
  process.exitCode = failed ? 1 : 0;
}
