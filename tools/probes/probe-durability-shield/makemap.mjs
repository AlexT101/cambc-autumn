// Builds durshield.map26a for probe-durability-shield (team A's coordinates; mirrored rotationally for team B):
//   G  2x4 block of gold clusters (4..5, 0..3): one group, 160 gold, no damage
//   GOLEM (12,8): 120 damage per hit, the hit that overflows Varg's 250 shield
// Run: node tools/probes/probe-durability-shield/makemap.mjs
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { ALTAR, Grid } from '../../../tools/mapgen/grid.mjs';
import { createEngine } from '../../../tools/mapgen/wasm.mjs';

const g = new Grid(30, 30, 'rotational');
g.picks = 3;
g.spawn = { x: 0, y: 0, w: 3, h: 3 };
g.set(14, 14, ALTAR);
for (let x = 4; x <= 5; x++) for (let y = 0; y <= 3; y++) g.camps.push({ type: 'gold_cluster', x, y });
g.camps.push({ type: 'golem', x: 12, y: 8 });

const engine = await createEngine();
const bytes = engine.encode(g.toMap());
engine.load(bytes);
const out = path.join(path.dirname(fileURLToPath(import.meta.url)), 'durshield.map26a');
fs.writeFileSync(out, bytes);
console.log(g.render());
console.log(`wrote ${out} (${bytes.length} bytes)`);
