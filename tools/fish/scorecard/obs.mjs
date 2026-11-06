// Observer decode for the Fish fidelity scorecard: tools/fish/farm3_decode.mjs's per-round camp-phase
// snapshots (same fields, so farm3_common.Game and payouts() read it), plus each champion's emblem
// formations (round, item), deaths during the camp phase (killed by a camp), and the engine's
// end-of-game statistics (kills, deaths, spent gold, items bought, damage).
//   node tools/fish/scorecard/obs.mjs OUT_DIR [--jobs N] MANIFEST...
// Writes OUT_DIR/<SHA16>.json.gz; skips existing files. Observer data: descriptive statistics only.
import fs from 'node:fs';
import path from 'node:path';
import zlib from 'node:zlib';
import crypto from 'node:crypto';
import { Worker, isMainThread, parentPort } from 'node:worker_threads';
import { Engine, compileEngine, replayEngine, ITEMS } from '../../replay/engine.mjs';

const r1 = v => Math.round(v * 10) / 10;

async function decode(entry, engines) {
  const bytes = fs.readFileSync(entry.file);
  if (crypto.createHash('sha256').update(bytes).digest('hex') !== entry.sha256) throw new Error(`hash changed: ${entry.file}`);
  const version = replayEngine(bytes);
  if (!engines.has(version)) engines.set(version, await Engine.create(await compileEngine(version)));
  const g = engines.get(version).openReplay(bytes);
  try {
    const map = g.map();
    let roster = null, camps = null, round = 0, lastPhase = -1, prevAlive = null;
    const rounds = [], emblems = {}, campDeaths = [], emCount = new Map();
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
      if (h.phase === 9 || st.phase === 9) {
        // Deaths inside the camp phase are camp kills.
        const lite = snap.championsLite();
        if (prevAlive) for (const c of lite) if (prevAlive.get(c.id) && !c.alive) campDeaths.push([round, c.id]);
        prevAlive = new Map(lite.map(c => [c.id, c.alive]));
      } else prevAlive = null;
      if (h.phase === 9 && lastPhase !== 9 && (!rounds.length || rounds[rounds.length - 1].r !== round)) {
        const lite = snap.championsLite();
        prevAlive = new Map(lite.map(c => [c.id, c.alive]));
        const ch = lite.map(c => [c.id, c.alive ? 1 : 0, c.x, c.y, r1(c.hp), r1(c.maxHp), c.gold, c.gems,
          c.earned, c.ct, c.cT, c.kills, c.deaths]);
        const gs = snap.groups().map(x => [x.state, x.captureTeam > 1 ? -1 : x.captureTeam, x.captureTimer, x.respawn]);
        const cl = snap.campsLite();
        rounds.push({ r: round, ch, gs, hp: Array.from(cl.hp, v => Math.round(v)), aw: Array.from(cl.awake), sub: h.submittedGems });
        // Emblem formations since the last snapshot (odd item indices are emblems).
        for (let k = 0; k < lite.length; k++) {
          const id = lite[k].id, it = snap.items(k), prev = emCount.get(id) ?? new Array(it.length).fill(0);
          for (let j = 1; j < it.length; j += 2) if (it[j] > prev[j]) (emblems[id] ??= []).push([round, ITEMS[j]]);
          emCount.set(id, Array.from(it));
        }
      }
      lastPhase = h.phase;
    } while (g.next());
    const stats = g.statistics();
    const champStats = stats.champions.map(s => ({ id: s.champion, team: s.team, type: s.type, kills: s.kills, deaths: s.deaths,
      earnedGold: s.earnedGold, spentGold: s.spentGold, collectedGems: s.collectedGems, submittedGems: s.submittedGems,
      shards: s.itemsBought.reduce((a, v, j) => a + (j % 2 === 0 ? v : 0), 0), consumables: s.consumablesBought,
      championDamageDone: r1(s.championDamageDone), championDamageTaken: r1(s.championDamageTaken),
      monsterDamageDone: r1(s.monsterDamageDone), monsterDamageTaken: r1(s.monsterDamageTaken), healingDone: r1(s.healingDone) }));
    return { schema: 1, game: entry.sha256.slice(0, 16), sha256: entry.sha256, map: entry.map, side: entry.side, group: entry.group,
      match: entry.match, kind: entry.kind, opponent: entry.opponent, engine: version,
      mapData: { width: map.width, height: map.height, symmetry: map.symmetry, spawnA: map.spawnA, altars: map.altars,
        walls: map.walls, holes: map.holes, bushes: map.bushes }, roster, camps,
      winner: stats.summary.outcome === 1 ? 0 : stats.summary.outcome === 2 ? 1 : null, finalRound: stats.summary.round,
      finalGems: stats.summary.submittedGems, emblems, campDeaths, champStats, rounds };
  } finally { g.destroy(); }
}

if (isMainThread) {
  const args = process.argv.slice(2), out = args.shift();
  let jobs = 6;
  const ji = args.indexOf('--jobs');
  if (ji >= 0) { jobs = +args[ji + 1]; args.splice(ji, 2); }
  if (!out || !args.length) throw new Error('usage: node tools/fish/scorecard/obs.mjs OUT_DIR [--jobs N] MANIFEST...');
  fs.mkdirSync(out, { recursive: true });
  const seen = new Map();
  for (const m of args) for (const e of JSON.parse(fs.readFileSync(m))) if (!seen.has(e.sha256)) seen.set(e.sha256, e);
  const entries = [...seen.values()].filter(e => !fs.existsSync(path.join(out, `${e.sha256.slice(0, 16)}.json.gz`)));
  let next = 0, done = 0;
  const errors = [];
  await Promise.all(Array.from({ length: Math.min(jobs, entries.length) }, () => new Promise((resolve, reject) => {
    const w = new Worker(new URL(import.meta.url));
    const feed = () => { if (next < entries.length) w.postMessage({ entry: entries[next++], out }); else w.terminate().then(resolve); };
    w.on('message', m => {
      done++;
      if (m.error) { errors.push(m); console.error(m.file, m.error); }
      else if (done % 25 === 0 || done === entries.length) console.error(`obs ${done}/${entries.length}`);
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
      const dest = path.join(out, `${res.game}.json.gz`);
      fs.writeFileSync(dest + '.tmp', zlib.gzipSync(JSON.stringify(res)));
      fs.renameSync(dest + '.tmp', dest);
      parentPort.postMessage({ game: res.game });
    } catch (err) { parentPort.postMessage({ error: String(err.stack ?? err), file: e.file }); }
  });
}
