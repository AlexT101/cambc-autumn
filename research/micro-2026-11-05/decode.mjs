// Per-action micro decode of ladder replays: every champion input step with the actor's state before and after, plus
// each champion's state at every round start. Feeds detect.py.
//   node research/micro-2026-11-05/decode.mjs --list LIST.json --out DIR [--threads N]
// LIST.json: [{key, replay, teams: [nameA, nameB], group, n}]
import fs from 'node:fs';
import path from 'node:path';
import zlib from 'node:zlib';
import { fileURLToPath } from 'node:url';
import { Worker, isMainThread, parentPort, workerData } from 'node:worker_threads';
import { Engine, compileEngine, replayEngine, unwrapReplay, mirror } from '../../tools/replay/engine.mjs';

const engines = new Map();
async function engineFor(bytes) {
  const v = replayEngine(bytes);
  if (!engines.has(v)) engines.set(v, Engine.create(await compileEngine(v)));
  return engines.get(v);
}

// Step kinds that are a champion's own input (Move .. Sell item, plus rollover and bot error).
const ACTION = new Set([4, 5, 6, 8, 9, 11, 12, 13, 14, 15, 16, 20, 21, 23, 24, 25, 26, 27]);

async function decode(bytes) {
  bytes = unwrapReplay(bytes);
  const e = await engineFor(bytes);
  const g = e.openReplay(bytes);
  try {
    const map = g.map();
    g.seekStart();
    const acts = [], rounds = [];
    let lastIp = -1, round = -1, roster = null, prev = null, prevItems = null, prevCons = null, prevCd = null;
    do {
      const snap = g.read();
      const h = snap.header(), st = h.step;
      if (!roster && h.phase !== 12 && st.phase !== 12) roster = snap.champions().map(c => ({ id: c.id, team: c.team, type: c.type }));
      if (!roster) continue;
      const lite = snap.championsLite();
      if (h.round !== round && h.phase !== 12) {
        round = h.round;
        const full = snap.champions();
        // [round, id, x, y, hp, maxHp, alive, gold, gems, prio, str, foc, cd0, cd1, chanType, chanT, items(flat nonzero)]
        rounds.push(full.map((c, k) => [h.round, c.id, c.x ?? -1, c.y ?? -1, +(c.hp ?? 0).toFixed(1), +(c.maxHp ?? 0).toFixed(1), c.alive ? 1 : 0,
          c.gold ?? 0, c.gems ?? 0, c.priority, +(c.strength ?? 0).toFixed(2), +(c.focus ?? 0).toFixed(2), c.cd?.[0] ?? 0, c.cd?.[1] ?? 0,
          c.channelType ?? 0, c.channelTimer ?? 0, (c.items ?? []).flatMap((n, i) => n ? [i, n] : [])]));
      }
      if (st.inputPosition !== lastIp && st.actor.kind === 1 && ACTION.has(st.kind) && prev) {
        lastIp = st.inputPosition;
        const k = roster.findIndex(c => c.id === st.actor.index);
        const b = prev[k], a = lite[k];
        const rec = { r: h.round, a: st.actor.index, k: st.kind, f: [st.from.x, st.from.y], to: [st.to.x, st.to.y] };
        if (st.abilitySlot !== undefined) { rec.slot = st.abilitySlot; rec.ab = st.abilityType; }
        if (st.kind === 9) rec.pr = st.priority;
        rec.b = [b.x, b.y, +b.hp.toFixed(1), +b.maxHp.toFixed(1), b.gold, b.alive ? 1 : 0, b.gems, b.ct, b.cT];
        rec.af = [a.x, a.y, +a.hp.toFixed(1), +a.maxHp.toFixed(1), a.gold, a.alive ? 1 : 0, a.gems, a.ct, a.cT];
        if (st.kind === 13 || st.kind === 25 || st.kind === 15) {
          const it = snap.items(k), cons = snap.consumables(k), d = [], dc = [];
          for (let i = 0; i < it.length; i++) if (it[i] !== prevItems[k][i]) d.push([i, it[i] - prevItems[k][i]]);
          for (let i = 0; i < cons.length; i++) if (cons[i] !== prevCons[k][i]) dc.push([i, cons[i] - prevCons[k][i]]);
          rec.it = d; rec.cons = dc;
        }
        if (st.kind === 5 || st.kind === 6) {
          // Damage dealt: hp+shield lost by every other unit this step.
          const hits = [];
          for (let j = 0; j < lite.length; j++) {
            if (j === k) continue;
            const lost = (prev[j].hp + prev[j].shield) - (lite[j].hp + lite[j].shield);
            if (lost > 0.01) hits.push([lite[j].id, +lost.toFixed(1), prev[j].team === b.team ? 1 : 0]);
          }
          rec.hits = hits;
          const tc = prev.find(c => c.alive && c.x === st.to.x && c.y === st.to.y);
          if (tc) rec.tgt = tc.id;
          const full = snap.champions()[k];
          rec.str = +(full.strength ?? 0).toFixed(2); rec.foc = +(full.focus ?? 0).toFixed(2);
        }
        if (st.kind === 8 || st.kind === 9) { delete rec.f; delete rec.to; delete rec.af; rec.b = rec.b.slice(0, 2); }
        acts.push(rec);
      }
      prev = lite;
      prevItems = roster.map((_, k) => snap.items(k));
      prevCons = roster.map((_, k) => snap.consumables(k));
    } while (g.next());
    const fin = g.read().header();
    const spawnB = (() => {
      const s = map.spawnA, p = mirror(map, s.minX, s.minY), q = mirror(map, s.maxX, s.maxY);
      return { minX: Math.min(p[0], q[0]), minY: Math.min(p[1], q[1]), maxX: Math.max(p[0], q[0]), maxY: Math.max(p[1], q[1]) };
    })();
    return {
      engine: replayEngine(bytes), roster, acts, rounds,
      map: { w: map.width, h: map.height, sym: map.symmetry, spawn: [map.spawnA, spawnB], altars: map.altars, bushes: map.bushes.length },
      result: { outcome: fin.outcome, round: fin.round, gems: fin.submittedGems.map(Number) },
    };
  } finally { g.destroy(); }
}

if (isMainThread) {
  const args = process.argv.slice(2), opt = { threads: 8 };
  for (let i = 0; i < args.length; i++) {
    if (args[i] === '--list') opt.list = args[++i];
    else if (args[i] === '--out') opt.out = args[++i];
    else if (args[i] === '--threads') opt.threads = +args[++i];
  }
  fs.mkdirSync(opt.out, { recursive: true });
  const todo = JSON.parse(fs.readFileSync(opt.list, 'utf8')).filter(g => !fs.existsSync(path.join(opt.out, `${g.key}.json.gz`)));
  let next = 0, done = 0, failed = 0;
  const t0 = Date.now();
  await Promise.all(Array.from({ length: Math.min(opt.threads, todo.length) }, () => new Promise(res => {
    const w = new Worker(fileURLToPath(import.meta.url), { workerData: { out: opt.out } });
    const feed = () => { if (next < todo.length) w.postMessage(todo[next++]); else { w.terminate(); res(); } };
    w.on('message', m => {
      done++;
      if (m.error) { failed++; console.error(`${m.key}: ${m.error}`); }
      if (done % 100 === 0 || done === todo.length) console.error(`${done}/${todo.length} (${((Date.now() - t0) / 1000).toFixed(0)} s, ${failed} failed)`);
      feed();
    });
    w.on('error', err => { console.error(err); failed++; res(); });
    feed();
  })));
  process.exit(failed ? 1 : 0);
} else {
  parentPort.on('message', async g => {
    try {
      const d = await decode(fs.readFileSync(g.replay));
      Object.assign(d, { key: g.key, teams: g.teams, group: g.group, n: g.n, created: g.created });
      fs.writeFileSync(path.join(workerData.out, `${g.key}.json.gz`), zlib.gzipSync(JSON.stringify(d)));
      parentPort.postMessage({ key: g.key });
    } catch (err) { parentPort.postMessage({ key: g.key, error: String(err.stack ?? err) }); }
  });
}
