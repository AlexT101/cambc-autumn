// Per-map big-group features from .map26a files: for team A's side groups and the shared ones, the members by
// type. One JSON line a map. Usage: node mapfeat.mjs DIR > feats.jsonl   (run from the repo root)
import fs from 'node:fs';
import path from 'node:path';
import { Grid } from '../../../tools/mapgen/grid.mjs';
import { sideGroups } from '../../../tools/mapgen/generate.mjs';
import { createEngine } from '../../../tools/mapgen/wasm.mjs';
const GEMS = { wolf: 4, elk: 15, golem: 36, gem_cluster: 7, gold_cluster: 0, monolith: 200 };
const GOLD = { wolf: 40, elk: 90, golem: 160, gem_cluster: 0, gold_cluster: 20, monolith: 300 };
const HP = { wolf: 1350, elk: 2400, golem: 5000, gem_cluster: 120, gold_cluster: 120, monolith: 20000 };
const RESP = { wolf: 40, elk: 60, golem: 80, gem_cluster: 50, gold_cluster: 50, monolith: 150 };
const engine = await createEngine();
const dir = process.argv[2];
for (const f of fs.readdirSync(dir).filter(f => f.endsWith('.map26a')).sort()) {
  const g = Grid.fromMap(engine.decode(fs.readFileSync(path.join(dir, f))));
  const { mine, shared } = sideGroups(g);
  const row = q => {
    const n = {};
    for (const m of q.members) n[m.type] = (n[m.type] ?? 0) + 1;
    const sum = T => Object.entries(n).reduce((a, [t, k]) => a + T[t] * k, 0);
    return { n, gems: sum(GEMS), gold: sum(GOLD), hp: sum(HP), resp: Math.max(...Object.keys(n).map(t => RESP[t])), dA: q.dA, dB: q.dB };
  };
  console.log(JSON.stringify({ map: f.replace(/\.map26a$/, ''), W: g.W, H: g.H, picks: g.picks, mine: mine.map(row), shared: shared.map(row) }));
}
