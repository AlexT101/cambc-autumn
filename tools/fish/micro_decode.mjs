// Observer decode for the combat-micro study (MICRO.md): per round the camp-phase champion states,
// the real champion turn order, and every champion action with its step and the full effect on
// every champion (ehp, alive, stun before/after: AoE, splash, Ren's reflection, HoR's dash) and on
// every camp. Observer data: labels, attribution and diagnostics only, never a policy input.
//   node tools/fish/micro_decode.mjs OUT_DIR [--jobs N] MANIFEST...
// Writes OUT_DIR/<SHA16>.json.gz; refuses existing files (skips them only with --resume).
import fs from 'node:fs';
import path from 'node:path';
import zlib from 'node:zlib';
import crypto from 'node:crypto';
import { Worker, isMainThread, parentPort } from 'node:worker_threads';
import { Engine, compileEngine, replayEngine, STEP_KINDS } from '../replay/engine.mjs';

const r1 = v => Math.round(v * 10) / 10;
// Move, Attack, Cast, Set priority, Recall, Submit gems, Place ward, Consumable, Cancel channel,
// Place altar lock, Teleport channel, Movement blocked.
const ACTS = new Set([4, 5, 6, 9, 11, 12, 14, 15, 16, 20, 21, 23]);

function champState(c) {
  const sh = (c.buffs ?? []).filter(b => b.type === 0).reduce((s, b) => s + b.mag, 0);
  const stun = (c.buffs ?? []).filter(b => b.type === 1).reduce((s, b) => Math.max(s, b.timer), -1);
  // [id, alive, x, y, hp, maxHp, shield, gems, priority, nextPriority, channelType, channelTimer, stun, cd0, cd1, strength, focus]
  return [c.id, c.alive ? 1 : 0, c.x ?? -1, c.y ?? -1, r1(c.hp), r1(c.maxHp), r1(sh), c.gems ?? 0, c.priority, c.nextPriority,
    c.channelType ?? 0, c.channelTimer ?? 0, stun, c.cd?.[0] ?? 0, c.cd?.[1] ?? 0, r1(c.strength ?? 0), r1(c.focus ?? 0)];
}

// Champions whose effective health, liveness or stun changed between two lite reads.
function champDiff(a, b) {
  const out = [];
  for (const c of b) {
    const p = a.find(x => x.id === c.id);
    if (!p) continue;
    const e0 = p.hp + p.shield, e1 = c.hp + c.shield;
    if (Math.abs(e0 - e1) > 1e-6 || p.alive !== c.alive || p.stun !== c.stun || p.kills !== c.kills)
      out.push([c.id, r1(e0), r1(e1), c.alive ? 1 : 0, p.stun, c.stun, c.kills - p.kills]);
  }
  return out;
}

function campDiff(a, b) {
  const out = [];
  for (let k = 0; k < b.hp.length; k++) if (Math.abs(a.hp[k] - b.hp[k]) > 1e-6) out.push([k, r1(a.hp[k]), r1(b.hp[k])]);
  return out;
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
    let prevCh = null, prevCamp = null, step = -1;  // step numbering matches extract.mjs
    const rounds = [];
    g.seekStart();
    do {
      step++;
      const snap = g.read(), h = snap.header(), st = h.step;
      if (h.phase === 12 || st.phase === 12) continue;
      if (!roster) {
        roster = snap.champions().map(c => ({ id: c.id, team: c.team, type: c.type }));
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
        const awake = [];
        for (let k = 0; k < cl.hp.length; k++) if (cl.awake[k] && cl.hp[k] > 0) awake.push([k, r1(cl.hp[k])]);
        R.cp = { ch: snap.champions().map(champState), awake };
      }
      if (st.phase === 9 && kind === 5 && st.actor.kind === 2 && prevCh) {
        // Camp attack: [camp, champion diffs].
        R.attacks.push([st.actor.index, champDiff(prevCh, ch)]);
      }
      if (st.phase === 10 && st.actor.kind === 1) {
        const id = st.actor.index;
        if (!turn || turn.id !== id) {
          const c0 = prevCh?.find(c => c.id === id);
          turn = { id, start: c0 ? [c0.x, c0.y, r1(c0.hp), r1(c0.shield), c0.alive ? 1 : 0] : null, acts: [] };
          R.turns.push(turn);
        }
        if (ACTS.has(kind)) {
          // [kind, x, y, slot, abilityType, step, champion diffs, camp diffs]
          const a = [STEP_KINDS[kind], st.to.x, st.to.y, kind === 6 ? st.abilitySlot : null, kind === 6 ? st.abilityType : null, step];
          if (prevCh && prevCamp) { a.push(champDiff(prevCh, ch)); a.push(campDiff(prevCamp, cl)); } else { a.push([]); a.push([]); }
          if (kind === 4) { const me = ch.find(c => c.id === id); a.push([me.x, me.y]); }
          turn.acts.push(a);
        }
        if ([8, 26, 27].includes(kind)) {
          turn.end = champState(snap.champions().find(c => c.id === id));
          turn.finish = STEP_KINDS[kind];
          R.order.push(id);
          turn = null;
        }
      }
      lastPhase = h.phase;
      prevCh = ch; prevCamp = cl;
    } while (g.next());
    return { schema: 1, game: entry.sha256.slice(0, 16), sha256: entry.sha256, map: entry.map, side: entry.side, group: entry.group,
      engine: version, mapData: { width: map.width, height: map.height, symmetry: map.symmetry, spawnA: map.spawnA, altars: map.altars,
        walls: map.walls, holes: map.holes, bushes: map.bushes }, roster, camps, rounds };
  } finally { g.destroy(); }
}

if (isMainThread) {
  const args = process.argv.slice(2), out = args.shift();
  let jobs = 6, resume = false;
  const ji = args.indexOf('--jobs');
  if (ji >= 0) { jobs = +args[ji + 1]; args.splice(ji, 2); }
  const ri = args.indexOf('--resume');
  if (ri >= 0) { resume = true; args.splice(ri, 1); }
  if (!out || !args.length) throw new Error('usage: node tools/fish/micro_decode.mjs OUT_DIR [--jobs N] [--resume] MANIFEST...');
  fs.mkdirSync(out, { recursive: true });
  const seen = new Map();
  for (const m of args) for (const e of JSON.parse(fs.readFileSync(m))) if (!seen.has(e.sha256)) seen.set(e.sha256, { ...e, cohort: path.basename(m) });
  const exists = e => fs.existsSync(path.join(out, `${e.sha256.slice(0, 16)}.json.gz`));
  const present = [...seen.values()].filter(exists);
  if (present.length && !resume) throw new Error(`refusing to overwrite ${present.length} files in ${out} (pass --resume to skip them)`);
  const entries = [...seen.values()].filter(e => !exists(e));
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
