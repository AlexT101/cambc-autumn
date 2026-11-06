// Observer decode for the farm3 study (FARM3.md): one snapshot per round at the start of the camp
// phase (after respawns and captures, before camp attacks and champion turns): every champion's
// position, health, gold, earned gold, gems, channel and kda; every live group's state, capture team,
// capture timer and respawn countdown; every camp's health; both teams' tributed gems.
//   node tools/fish/farm3_decode.mjs OUT_DIR [--jobs N] MANIFEST...
// Writes OUT_DIR/<SHA16>.json.gz and refuses to overwrite one. Observer data: labels and
// descriptive statistics only, never a policy input.
import fs from 'node:fs';
import path from 'node:path';
import zlib from 'node:zlib';
import crypto from 'node:crypto';
import { Worker, isMainThread, parentPort } from 'node:worker_threads';
import { Engine, compileEngine, replayEngine } from '../replay/engine.mjs';

const r1 = v => Math.round(v * 10) / 10;

async function decode(entry, engines) {
  const bytes = fs.readFileSync(entry.file);
  if (crypto.createHash('sha256').update(bytes).digest('hex') !== entry.sha256) throw new Error(`hash changed: ${entry.file}`);
  const version = replayEngine(bytes);
  if (!engines.has(version)) engines.set(version, await Engine.create(await compileEngine(version)));
  const g = engines.get(version).openReplay(bytes);
  try {
    const map = g.map();
    let roster = null, camps = null, round = 0, lastPhase = -1;
    const rounds = [];
    g.seekStart();
    do {
      const snap = g.read(), h = snap.header(), st = h.step;
      if (h.phase === 12 || st.phase === 12) { lastPhase = h.phase; continue; }
      if (!roster) {
        roster = snap.champions().map(c => ({ id: c.id, team: c.team, type: c.type }));
        camps = snap.camps().map((c, k) => {
          if (c.id !== k) throw new Error('camp id != index');
          return { id: c.id, group: c.group, type: c.type, x: c.x, y: c.y, maxHp: c.maxHp };
        });
      }
      if (h.round !== round) round = h.round;
      if (h.phase === 9 && lastPhase !== 9 && (!rounds.length || rounds[rounds.length - 1].r !== round)) {
        const ch = snap.championsLite().map(c => [c.id, c.alive ? 1 : 0, c.x, c.y, r1(c.hp), r1(c.maxHp), c.gold, c.gems,
          c.earned, c.ct, c.cT, c.kills, c.deaths]);
        const gs = snap.groups().map(x => [x.state, x.captureTeam > 1 ? -1 : x.captureTeam, x.captureTimer, x.respawn]);
        const cl = snap.campsLite();
        rounds.push({ r: round, ch, gs, hp: Array.from(cl.hp, v => Math.round(v)), aw: Array.from(cl.awake), sub: h.submittedGems });
      }
      lastPhase = h.phase;
    } while (g.next());
    const stats = g.statistics();
    return { schema: 1, game: entry.sha256.slice(0, 16), sha256: entry.sha256, map: entry.map, side: entry.side, group: entry.group,
      match: entry.match, kind: entry.kind, opponent: entry.opponent, engine: version,
      mapData: { width: map.width, height: map.height, symmetry: map.symmetry, spawnA: map.spawnA, altars: map.altars,
        walls: map.walls, holes: map.holes, bushes: map.bushes }, roster, camps,
      winner: stats.summary.outcome === 1 ? 0 : stats.summary.outcome === 2 ? 1 : null, rounds };
  } finally { g.destroy(); }
}

if (isMainThread) {
  const args = process.argv.slice(2), out = args.shift();
  let jobs = 6;
  const ji = args.indexOf('--jobs');
  if (ji >= 0) { jobs = Math.min(6, +args[ji + 1]); args.splice(ji, 2); }
  if (!out || !args.length) throw new Error('usage: node tools/fish/farm3_decode.mjs OUT_DIR [--jobs N] MANIFEST...');
  fs.mkdirSync(out, { recursive: true });
  const seen = new Map();
  for (const m of args) for (const e of JSON.parse(fs.readFileSync(m))) if (!seen.has(e.sha256)) seen.set(e.sha256, { ...e, cohort: path.basename(m) });
  const entries = [...seen.values()].filter(e => !fs.existsSync(path.join(out, `${e.sha256.slice(0, 16)}.json.gz`)));
  let next = 0, done = 0;
  const errors = [];
  await Promise.all(Array.from({ length: Math.min(jobs, entries.length) }, () => new Promise((resolve, reject) => {
    const w = new Worker(new URL(import.meta.url));
    const feed = () => { if (next < entries.length) w.postMessage({ entry: entries[next++], out }); else w.terminate().then(resolve); };
    w.on('message', m => {
      done++;
      if (m.error) { errors.push(m); console.error(m.file, m.error); }
      else console.error(`${done}/${entries.length} ${m.game}`);
      feed();
    });
    w.on('error', reject);
    feed();
  })));
  if (errors.length) { fs.writeFileSync(path.join(out, `errors-${Date.now()}.json`), JSON.stringify(errors)); process.exitCode = 1; }
} else {
  const engines = new Map();
  parentPort.on('message', async ({ entry: e, out }) => {
    try {
      const res = await decode(e, engines);
      res.cohort = e.cohort;
      const dest = path.join(out, `${res.game}.json.gz`);
      if (fs.existsSync(dest)) throw new Error(`refusing to overwrite ${dest}`);
      fs.writeFileSync(dest + '.tmp', zlib.gzipSync(JSON.stringify(res)));
      fs.renameSync(dest + '.tmp', dest);
      parentPort.postMessage({ game: res.game });
    } catch (err) { parentPort.postMessage({ error: String(err.stack ?? err), file: e.file }); }
  });
}
