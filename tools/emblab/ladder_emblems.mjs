// Emblem orders on the ladder: every champion's new emblems (the first shard of a family and stat, or an emblem
// bought whole) in order, with the round, from downloaded ladder replays (tools/fetch_replays.py).
//   node tools/emblab/ladder_emblems.mjs [replays/ladder] --out replays/emblab/ladder_emblems.jsonl [--threads 16]
// One JSON line per champion: {group, match, map, team, side, type, won, rounds, emblems: [[round, family * 3 + stat], ...]}.
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { Worker, isMainThread, parentPort } from 'node:worker_threads';
import { fileURLToPath } from 'node:url';
import { Engine, compileEngine, replayEngine } from '../replay/engine.mjs';

const READ_EVERY = 256; // engine steps, ~1.3 rounds

async function orders(engines, file) {
  const bytes = fs.readFileSync(file), version = replayEngine(bytes);
  engines[version] ??= await Engine.create(await compileEngine(version));
  const g = engines[version].openReplay(bytes);
  try {
    g.seekStart();
    let prev = null, roster = null, steps = 0;
    const seq = [];
    const scan = s => {
      if (!roster) { roster = s.champions().map(c => ({ team: c.team, type: c.type })); roster.forEach(() => seq.push([])); }
      const round = s.header().round;
      const now = roster.map((_, k) => s.items(k));
      if (prev) for (let k = 0; k < roster.length; k++)
        for (let f = 0; f < 14; f++) for (let st = 0; st < 3; st++) {
          const shard = f * 6 + st * 2, emblem = shard + 1;
          const began = prev[k][shard] === 0 && now[k][shard] > 0;
          const whole = prev[k][shard] === 0 && now[k][emblem] > prev[k][emblem];
          if (began || whole) seq[k].push([round, f * 3 + st]);
        }
      prev = now;
    };
    while (g.next()) if (++steps % READ_EVERY === 0) scan(g.read());
    scan(g.read());
    const { summary } = g.statistics();
    return { rounds: summary.round, winner: summary.outcome === 1 ? 0 : 1, champions: roster.map((c, k) => ({ ...c, emblems: seq[k] })) };
  } finally { g.destroy(); }
}

if (!isMainThread) {
  const engines = {};
  parentPort.on('message', async file => {
    try { parentPort.postMessage({ file, row: await orders(engines, file) }); }
    catch (e) { parentPort.postMessage({ file, error: e.message }); }
  });
} else {
  const args = process.argv.slice(2);
  let dir = 'replays/ladder', out = 'replays/emblab/ladder_emblems.jsonl', threads = Math.min(16, os.cpus().length - 2);
  for (let i = 0; i < args.length; i++) {
    if (args[i] === '--out') out = args[++i];
    else if (args[i] === '--threads') threads = +args[++i];
    else dir = args[i];
  }
  const jobs = [];
  for (const d of fs.readdirSync(dir)) {
    const meta = path.join(dir, d, 'group.json');
    if (!fs.existsSync(meta)) continue;
    const group = JSON.parse(fs.readFileSync(meta, 'utf8'));
    for (const m of group.matches) {
      const file = path.join(dir, d, `${m.position}-${m.map}.repl26a`);
      if (fs.existsSync(file)) jobs.push({ file, group, m });
    }
  }
  const byFile = new Map(jobs.map(j => [j.file, j]));
  const sink = fs.openSync(out, 'w');
  let done = 0, failed = 0, queued = 0;
  const me = fileURLToPath(import.meta.url);
  await Promise.all(Array.from({ length: Math.min(threads, jobs.length) }, () => new Promise(resolve => {
    const w = new Worker(me);
    const feed = () => queued < jobs.length ? w.postMessage(jobs[queued++].file) : (w.terminate(), resolve());
    w.on('message', ({ file, row, error }) => {
      if (error) { failed++; console.error(`FAILED ${file}: ${error}`); }
      else {
        const { group, m } = byFile.get(file), sides = Object.fromEntries(m.sides.map(s => [s.side, s]));
        const lines = row.champions.map(c => {
          const side = c.team === 0 ? 'a' : 'b';
          return JSON.stringify({ group: group.group.id, created: group.group.createdAt, match: m.id, map: m.map, team: sides[side]?.teamName, side,
            type: c.type, won: row.winner === c.team, rounds: row.rounds, emblems: c.emblems });
        });
        fs.writeSync(sink, lines.join('\n') + '\n');
      }
      done++;
      feed();
    });
    feed();
  })));
  fs.closeSync(sink);
  console.error(`${done - failed}/${jobs.length} replays, ${failed} failed -> ${out}`);
}
