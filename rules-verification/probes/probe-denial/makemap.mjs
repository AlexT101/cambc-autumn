// Builds denial.map26a for probe-denial (team A's coordinates; the builder mirrors rotationally for team B):
//   R      wolf (8,5) + gold cluster (9,5)              respawn 50, 125 gold, 22 gems   (respawn scenarios)
//   PSMALL gem (4,9) + gold (5,9) + gold (6,9)           24 gems, split 8/8/8 by three allies
//   PBIG   gem (4,13), (5,13), (6,13)                    72 gems for one champion
//   Q      gem (15,8), next to altar (14,8)              a camp tile within 1 of an altar
// Run: node rules-verification/probes/probe-denial/makemap.mjs
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { ALTAR, Grid } from '../../../tools/mapgen/grid.mjs';
import { createEngine } from '../../../tools/mapgen/wasm.mjs';

const g = new Grid(30, 30, 'rotational');
g.picks = 3;
g.spawn = { x: 0, y: 0, w: 3, h: 3 };
g.set(14, 8, ALTAR);
g.camps.push(
  { type: 'wolf', x: 8, y: 5 }, { type: 'gold_cluster', x: 9, y: 5 },
  { type: 'gem_cluster', x: 4, y: 9 }, { type: 'gold_cluster', x: 5, y: 9 }, { type: 'gold_cluster', x: 6, y: 9 },
  { type: 'gem_cluster', x: 4, y: 13 }, { type: 'gem_cluster', x: 5, y: 13 }, { type: 'gem_cluster', x: 6, y: 13 },
  { type: 'gem_cluster', x: 15, y: 8 },
);

const engine = await createEngine();
const bytes = engine.encode(g.toMap());
engine.load(bytes);
const out = path.join(path.dirname(fileURLToPath(import.meta.url)), 'denial.map26a');
fs.writeFileSync(out, bytes);
console.log(g.render());
console.log(`wrote ${out} (${bytes.length} bytes)`);
