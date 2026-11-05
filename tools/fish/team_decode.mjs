// Observer decode for the team/camp-fight study (TEAM.md): per round the camp phase (champion
// states, awake camps, every camp attack with its target), the real champion turn order, and every
// champion turn's end state and actions with resolved targets and hp before/after.
//   node tools/fish/team_decode.mjs OUT_DIR [--jobs N] MANIFEST...
// Writes OUT_DIR/<SHA16>.json.gz; skips existing files. Observer data: labels and diagnostics only.
import fs from 'node:fs';
import path from 'node:path';
import zlib from 'node:zlib';
import crypto from 'node:crypto';
import { Worker, isMainThread, parentPort } from 'node:worker_threads';
import { Engine, compileEngine, replayEngine, STEP_KINDS } from '../replay/engine.mjs';

const r1 = v => Math.round(v * 10) / 10;
const ACTS = new Set([4, 5, 6, 9, 11, 12, 13, 14, 15, 16, 20, 21, 23]);

function champState(c) {
  const sh = (c.buffs ?? []).filter(b => b.type === 0).reduce((s, b) => s + b.mag, 0);
  const stun = (c.buffs ?? []).filter(b => b.type === 1).reduce((s, b) => Math.max(s, b.timer), -1);
  // [id, alive, x, y, hp, maxHp, shield, gems, priority, nextPriority, channelType, channelTimer, stun, cd0, cd1, strength, focus]
  return [c.id, c.alive ? 1 : 0, c.x ?? -1, c.y ?? -1, r1(c.hp), r1(c.maxHp), r1(sh), c.gems ?? 0, c.priority, c.nextPriority,
    c.channelType ?? 0, c.channelTimer ?? 0, stun, c.cd?.[0] ?? 0, c.cd?.[1] ?? 0, r1(c.strength ?? 0), r1(c.focus ?? 0)];
}

async function decode(entry, engines) {
  const bytes = fs.readFileSync(entry.file);
  if (crypto.createHash('sha256').update(bytes).digest('hex') !== entry.sha256) throw new Error(`hash changed: ${entry.file}`);
  const version = replayEngine(bytes);
  if (!engines.has(version)) engines.set(version, await Engine.create(await compileEngine(version)));
  const g = engines.get(version).openReplay(bytes);
  try {
    const map = g.map();
    let roster = null, camps = null, round = 0, R = null, turn = null, lastPhase = -1;
    let prevCh = null, prevCamp = null; // lite state after the previous step: "before" for this one
    const rounds = [];
    g.seekStart();
    do {
      const snap = g.read(), h = snap.header(), st = h.step;
      if (h.phase === 12 || st.phase === 12) continue;
      if (!roster) {
        const cs = snap.champions();
        roster = cs.map(c => ({ id: c.id, team: c.team, type: c.type }));
        camps = snap.camps().map((c, k) => { if (c.id !== k) throw new Error('camp id != index'); return { id: c.id, group: c.group, type: c.type, x: c.x, y: c.y, maxHp: c.maxHp }; });
      }
      if (h.round !== round) {
        round = h.round;
        R = { r: round, cp: null, attacks: [], order: [], turns: [] };
        rounds.push(R);
      }
      const ch = snap.championsLite(), cl = snap.campsLite();
      const kind = st.kind;
      if (h.phase === 9 && lastPhase !== 9 && !R.cp) {
        // Camp phase start: captures and respawns done, no camp attack yet.
        const awake = [];
        for (let k = 0; k < cl.hp.length; k++) if (cl.awake[k] && cl.hp[k] > 0) awake.push([k, r1(cl.hp[k])]);
        const groups = snap.groups().map((x, i) => [i, x.state, x.captureTeam, x.captureTimer]).filter(x => x[1] === 2 || x[2] !== 0xFFFFFFFF && x[2] < 2);
        R.cp = { ch: snap.champions().map(champState), awake, groups };
      }
      if (st.phase === 9 && kind === 5 && st.actor.kind === 2) {
        const tgt = ch.find(c => c.alive && c.x === st.to.x && c.y === st.to.y);
        const before = prevCh?.find(c => c.id === tgt?.id);
        R.attacks.push([st.actor.index, tgt ? tgt.id : -1, before ? r1(before.hp + before.shield) : null, tgt ? r1(tgt.hp + tgt.shield) : null]);
      }
      if (st.phase === 10 && st.actor.kind === 1) {
        const id = st.actor.index;
        if (!turn || turn.id !== id) {
          const c0 = prevCh?.find(c => c.id === id);
          turn = { id, start: c0 ? [c0.x, c0.y, r1(c0.hp), r1(c0.shield), c0.alive ? 1 : 0] : null, acts: [] };
          R.turns.push(turn);
        }
        if (ACTS.has(kind)) {
          const a = [STEP_KINDS[kind], st.to.x, st.to.y];
          if (kind === 6) a.push(st.abilitySlot, st.abilityType); else a.push(null, null);
          a.push(kind === 9 ? st.priority : null);
          if (kind === 5 || kind === 6) {
            // Target at the destination tile: champion (alive, before) or camp.
            const tc = prevCh?.find(c => c.alive && c.x === st.to.x && c.y === st.to.y);
            const tcamp = camps.findIndex(c => c.x === st.to.x && c.y === st.to.y);
            if (tc) { const after = ch.find(c => c.id === tc.id); a.push(1, tc.id, r1(tc.hp + tc.shield), r1(after.hp + after.shield)); }
            else if (tcamp >= 0 && prevCamp && prevCamp.hp[tcamp] > 0) a.push(2, tcamp, r1(prevCamp.hp[tcamp]), r1(cl.hp[tcamp]));
            else a.push(0, -1, null, null);
            // Camps killed by this step (AoE included).
            const killed = [];
            if (prevCamp) for (let k = 0; k < cl.hp.length; k++) if (prevCamp.hp[k] > 0 && cl.hp[k] <= 0) killed.push(k);
            a.push(killed);
          }
          if (kind === 4) { const me = ch.find(c => c.id === id); a.push(me.x, me.y); }
          turn.acts.push(a);
        }
        if ([8, 26, 27].includes(kind)) {
          const full = snap.champions().find(c => c.id === id);
          turn.end = champState(full);
          turn.finish = STEP_KINDS[kind];
          R.order.push(id);
          turn = null;
        }
      }
      lastPhase = h.phase;
      prevCh = ch; prevCamp = cl;
    } while (g.next());
    const stats = g.statistics();
    return { schema: 1, game: entry.sha256.slice(0, 16), sha256: entry.sha256, map: entry.map, side: entry.side, group: entry.group,
      engine: version, mapData: { width: map.width, height: map.height, symmetry: map.symmetry, spawnA: map.spawnA, altars: map.altars,
        walls: map.walls, holes: map.holes }, roster, camps,
      winner: stats.summary.outcome === 1 ? 0 : stats.summary.outcome === 2 ? 1 : null, rounds };
  } finally { g.destroy(); }
}

if (isMainThread) {
  const args = process.argv.slice(2), out = args.shift();
  let jobs = 6;
  const ji = args.indexOf('--jobs');
  if (ji >= 0) { jobs = +args[ji + 1]; args.splice(ji, 2); }
  if (!out || !args.length) throw new Error('usage: node tools/fish/team_decode.mjs OUT_DIR [--jobs N] MANIFEST...');
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
      fs.writeFileSync(dest + '.tmp', zlib.gzipSync(JSON.stringify(res)));
      fs.renameSync(dest + '.tmp', dest);
      parentPort.postMessage({ game: res.game });
    } catch (err) { parentPort.postMessage({ error: String(err.stack ?? err), file: e.file }); }
  });
}
