// Independently count raw engine actions, including actions outside our turn grouping.
import fs from 'node:fs';
import path from 'node:path';
import zlib from 'node:zlib';
import { Engine, compileEngine, replayEngine, STEP_KINDS } from '../replay/engine.mjs';

const [manifest, cache] = process.argv.slice(2);
if (!manifest || !cache) throw new Error('usage: node tools/fish/audit.mjs MANIFEST CACHE');
const engines = new Map();
const kinds = new Set([4, 5, 6, 9, 11, 12, 13, 14, 15, 16, 20, 21, 23, 25]);
let games = 0, actions = 0, turns = 0;
for (const entry of JSON.parse(fs.readFileSync(manifest))) {
  const cached = JSON.parse(zlib.gunzipSync(fs.readFileSync(path.join(cache, `${entry.sha256.slice(0,16)}.json.gz`))));
  const ids = new Set(cached.roster.filter(c => c.team === entry.side).map(c => c.id));
  const want = cached.turns.flatMap(t => t.actions.map(a => [a.step, t.round, t.id, a.kind]));
  const bytes = fs.readFileSync(entry.file), version = replayEngine(bytes);
  if (!engines.has(version)) engines.set(version, await Engine.create(await compileEngine(version)));
  const g = engines.get(version).openReplay(bytes);
  let step = -1, actual = [], ended = 0;
  try {
    g.seekStart();
    do {
      step++;
      const h = g.read().header(), st = h.step;
      if (h.phase === 12 || st.phase === 12 || st.actor.kind !== 1 || !ids.has(st.actor.index)) continue;
      // Recall arrival is also a Move step, in phase 14, and is not a bot input.
      if (st.phase === 10 && kinds.has(st.kind)) actual.push([step, h.round, st.actor.index, STEP_KINDS[st.kind]]);
      if ([8,26,27].includes(st.kind)) ended++;
    } while (g.next());
  } finally { g.destroy(); }
  if (JSON.stringify(want) !== JSON.stringify(actual)) {
    const i = actual.findIndex((a, i) => JSON.stringify(a) !== JSON.stringify(want[i]));
    throw new Error(`input accounting mismatch: ${entry.file}: ${want.length}/${actual.length}; index ${i}; cached ${JSON.stringify(want.slice(i,i+3))}; raw ${JSON.stringify(actual.slice(i,i+3))}`);
  }
  if (ended !== cached.turns.filter(t => t.finish).length) throw new Error(`turn accounting mismatch: ${entry.file}`);
  games++; actions += actual.length; turns += ended;
}
console.log(JSON.stringify({games, actions, completedTurns: turns, exactActionAccounting: true}, null, 2));
