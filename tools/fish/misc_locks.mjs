// Altar-lock placement opportunities for Fish (MISC.md section 2), decoded from raw replays.
//   node tools/fish/misc_locks.mjs OUT.json.gz [--jobs N] MANIFEST...
// At every completed Fish turn whose actor is alive and carried a lock at turn start, and every
// lock placement, records: actor position at turn end (or just before placing), gems, the altars
// within 2 and, per altar, whether Fish's and the enemy's locks are on it (observer lock table:
// a lock within 2 tiles is in the actor's sight except behind walls, so this is a label proxy).
// Refuses to overwrite OUT.
import fs from 'node:fs';
import zlib from 'node:zlib';
import crypto from 'node:crypto';
import os from 'node:os';
import { Worker, isMainThread, parentPort } from 'node:worker_threads';
import { Engine, compileEngine, replayEngine, STEP_KINDS, CONSUMABLES } from '../replay/engine.mjs';

const LOCK = CONSUMABLES.indexOf('Altar lock');
const cheb = (a, b) => Math.max(Math.abs(a[0] - b[0]), Math.abs(a[1] - b[1]));

async function decode(entry, engines) {
  const bytes = fs.readFileSync(entry.file);
  if (crypto.createHash('sha256').update(bytes).digest('hex') !== entry.sha256) throw new Error(`hash changed: ${entry.file}`);
  const version = replayEngine(bytes);
  if (!engines.has(version)) engines.set(version, await Engine.create(await compileEngine(version)));
  const g = engines.get(version).openReplay(bytes);
  try {
    const map = g.map(), side = entry.side, altars = map.altars;
    const rows = [];
    let cur = null; // {id, round, carry, pos, placed:[]}
    g.seekStart();
    do {
      const snap = g.read(), h = snap.header(), st = h.step;
      if (h.phase === 12 || st.phase === 12) continue;
      if (st.actor.kind !== 1) continue;
      const c = snap.champions().find(x => x.id === st.actor.index);
      if (!c || c.team !== side) continue;
      if (!cur || cur.id !== c.id || cur.round !== h.round) {
        // First step of this actor's turn: the state before it is the snapshot before this step,
        // but carry only changes by shopping (turn start) or placing, both recorded below.
        cur = { id: c.id, round: h.round, carry: null, pos: null, placed: [] };
      }
      const kind = STEP_KINDS[st.kind];
      if (kind === 'Place altar lock') {
        const t = [st.to.x, st.to.y], near = altars.filter(a => cheb([c.x, c.y], a) <= 2);
        const locks = g.altarLocks(near);
        cur.placed.push({ to: t, pos: [c.x, c.y], gems: c.gems, near, locks });
      }
      if ([8, 26, 27].includes(st.kind)) {
        if (c.alive) {
          const carry = c.consumables[LOCK], pos = [c.x, c.y];
          const near = altars.filter(a => cheb(pos, a) <= 2);
          if ((carry > 0 || cur.placed.length) && near.length)
            rows.push({ r: h.round, id: c.id, pos, gems: c.gems, carryEnd: carry, finish: kind, near, locks: g.altarLocks(near), placed: cur.placed });
        }
        cur = null;
      }
    } while (g.next());
    return { game: entry.sha256.slice(0, 16), map: entry.map, side, group: entry.group, rows };
  } finally { g.destroy(); }
}

if (isMainThread) {
  const args = process.argv.slice(2), out = args.shift();
  let jobs = Math.min(6, os.cpus().length);
  const ji = args.indexOf('--jobs');
  if (ji >= 0) { jobs = +args[ji + 1]; args.splice(ji, 2); }
  if (!out || !args.length) throw new Error('usage: node tools/fish/misc_locks.mjs OUT.json.gz [--jobs N] MANIFEST...');
  if (fs.existsSync(out)) throw new Error(`refusing to overwrite ${out}`);
  const seen = new Map();
  for (const m of args) for (const e of JSON.parse(fs.readFileSync(m))) if (!seen.has(e.sha256)) seen.set(e.sha256, { ...e, cohort: m.split('/').at(-1) });
  const entries = [...seen.values()], results = [], errors = [];
  let next = 0;
  await Promise.all(Array.from({ length: jobs }, () => new Promise((resolve, reject) => {
    const w = new Worker(new URL(import.meta.url));
    const feed = () => { if (next < entries.length) w.postMessage(entries[next++]); else w.terminate().then(resolve); };
    w.on('message', m => { (m.error ? errors : results).push(m); console.error(`${results.length + errors.length}/${entries.length}`); feed(); });
    w.on('error', reject);
    feed();
  })));
  fs.writeFileSync(out, zlib.gzipSync(JSON.stringify({ schema: 1, games: results, errors })));
  console.error(`${results.length} games, ${errors.length} errors -> ${out}`);
  if (errors.length) { console.error(errors.slice(0, 3)); process.exitCode = 1; }
} else {
  const engines = new Map();
  parentPort.on('message', async e => {
    try { parentPort.postMessage({ ...(await decode(e, engines)), cohort: e.cohort }); }
    catch (err) { parentPort.postMessage({ error: String(err.stack ?? err), file: e.file }); }
  });
}
