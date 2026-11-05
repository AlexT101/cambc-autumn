// Fish's drafts and item builds, from every step's observer snapshot (items are diffed step by step).
//   node tools/fish/drafts_emblems.mjs OUT.json.gz [--jobs N] MANIFEST...
// Manifests are deduplicated by sha256. The held-out cohort (fish-fifth-raw, groups 01a1ad0b/01a1ad15) is refused.
import fs from 'node:fs';
import zlib from 'node:zlib';
import crypto from 'node:crypto';
import os from 'node:os';
import { Worker, isMainThread, parentPort, workerData } from 'node:worker_threads';
import { Engine, compileEngine, replayEngine, CHAMPIONS, DRAFT_CHAMPIONS, ITEMS, CONSUMABLES, STEP_KINDS } from '../replay/engine.mjs';

const HELD_OUT = [/fish-fifth-raw/, /01a1ad0b/, /01a1ad15/];

async function decode(entry, engines) {
  const bytes = fs.readFileSync(entry.file);
  if (crypto.createHash('sha256').update(bytes).digest('hex') !== entry.sha256) throw new Error(`hash changed: ${entry.file}`);
  const version = replayEngine(bytes);
  if (!engines.has(version)) engines.set(version, await Engine.create(await compileEngine(version)));
  const g = engines.get(version).openReplay(bytes);
  try {
    const map = g.map(), side = entry.side;
    let draft = null, roster = null, prev = null, round = 0;
    const log = new Map(); // champion id -> [{r, kind, actor, items: {name: delta}, cons: {name: delta}, alive}]
    g.seekStart();
    do {
      const snap = g.read(), h = snap.header();
      if (h.phase === 12 || h.step.phase === 12) { draft = snap.draft(); continue; }
      round = h.round;
      const champs = snap.champions();
      if (!roster) {
        roster = champs.map(c => ({ id: c.id, team: c.team, type: c.type, name: CHAMPIONS[c.type], draftOrder: c.draftOrder }));
        prev = new Map(champs.map(c => [c.id, { items: c.items, cons: c.consumables }]));
        for (const c of champs) if (c.items.some(Boolean) || c.consumables.some(Boolean)) throw new Error(`items at start: ${c.id}`);
        continue;
      }
      for (const c of champs) {
        if (c.team !== side) continue;
        const p = prev.get(c.id), items = {}, cons = {};
        let changed = false;
        for (let k = 0; k < c.items.length; k++) if (c.items[k] !== p.items[k]) { items[ITEMS[k]] = c.items[k] - p.items[k]; changed = true; }
        for (let k = 0; k < 4; k++) if (c.consumables[k] !== p.cons[k]) { cons[CONSUMABLES[k]] = c.consumables[k] - p.cons[k]; changed = true; }
        if (!changed) continue;
        if (!log.has(c.id)) log.set(c.id, []);
        log.get(c.id).push({ r: round, kind: STEP_KINDS[h.step.kind], actor: h.step.actor.kind === 1 ? h.step.actor.index : null, alive: c.alive, items, cons });
        prev.set(c.id, { items: c.items, cons: c.consumables });
      }
    } while (g.next());
    const last = g.read().champions(), stats = g.statistics();
    const names = t => draft.picks[t].slice(0, draft.counts[t] || draft.numRounds).map(i => DRAFT_CHAMPIONS[i] ?? i);
    const champions = roster.filter(c => c.team === side).map(c => {
      const s = stats.champions.find(x => x.champion === c.id), end = last.find(x => x.id === c.id);
      const nz = a => Object.fromEntries(a.map((v, k) => [k, v]).filter(([, v]) => v).map(([k, v]) => [ITEMS[k], v]));
      return { ...c, log: log.get(c.id) ?? [], itemsBought: nz(s.itemsBought), finalItems: nz(end.items), statItems: nz(s.items),
        consumablesBought: Object.fromEntries(s.consumablesBought.map((v, k) => [CONSUMABLES[k], v]).filter(([, v]) => v)),
        spentGold: s.spentGold, earnedGold: s.earnedGold, deaths: s.deaths,
        // Passive counters, to check the item family indexing (Treasure, Prospector, Collectors).
        treasureGold: end.treasureGold, prospectorGold: end.prospectorGold, prospectorGems: end.prospectorGems, collectorsDamageBonus: end.collectorsDamageBonus };
    });
    return { ...entry, engine: version, champsPerTeam: map.champsPerTeam, symmetry: map.symmetry,
      picks: [names(0), names(1)], fishPicks: names(side), oppPicks: names(1 - side),
      winner: stats.summary.outcome === 1 ? 0 : stats.summary.outcome === 2 ? 1 : null, rounds: stats.summary.round,
      gems: stats.summary.submittedGems, champions };
  } finally { g.destroy(); }
}

if (isMainThread) {
  const args = process.argv.slice(2);
  const out = args.shift();
  let jobs = Math.min(8, os.cpus().length);
  const ji = args.indexOf('--jobs');
  if (ji >= 0) { jobs = +args[ji + 1]; args.splice(ji, 2); }
  if (!out || !args.length) throw new Error('usage: node tools/fish/drafts_emblems.mjs OUT.json.gz [--jobs N] MANIFEST...');
  const seen = new Map();
  for (const m of args) for (const e of JSON.parse(fs.readFileSync(m))) {
    if (HELD_OUT.some(re => re.test(e.file) || re.test(e.group ?? ''))) throw new Error(`held-out game in manifest: ${e.file}`);
    if (!seen.has(e.sha256)) seen.set(e.sha256, { ...e, manifest: m.split('/').at(-1) });
  }
  const entries = [...seen.values()], results = [], errors = [];
  let next = 0;
  await Promise.all(Array.from({ length: jobs }, () => new Promise((resolve, reject) => {
    const w = new Worker(new URL(import.meta.url), { workerData: {} });
    const feed = () => { if (next < entries.length) w.postMessage(entries[next++]); else w.terminate().then(resolve); };
    w.on('message', m => { (m.error ? errors : results).push(m); if (results.length % 50 === 0) console.error(`${results.length}/${entries.length}`); feed(); });
    w.on('error', reject);
    feed();
  })));
  results.sort((a, b) => a.date.localeCompare(b.date) || a.file.localeCompare(b.file));
  fs.writeFileSync(out, zlib.gzipSync(JSON.stringify({ schema: 1, games: results, errors })));
  console.error(`${results.length} games, ${errors.length} errors -> ${out}`);
  if (errors.length) { console.error(errors); process.exitCode = 1; }
} else {
  const engines = new Map();
  parentPort.on('message', async e => {
    try { parentPort.postMessage(await decode(e, engines)); }
    catch (err) { parentPort.postMessage({ error: String(err.stack ?? err), file: e.file }); }
  });
}
