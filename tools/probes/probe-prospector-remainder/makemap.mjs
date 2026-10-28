// Builds prospector.map26a for probe-prospector-remainder (team A's coordinates; rotational), 30x30, 3 picks:
//   F: gold 3x3 x4..6 y0..2 (180 gold), Stellar farms it alone and buys a Prospector emblem
//   T: 3x3 x4..6 y4..6, gems at (4,4),(5,4),(6,4),(4,5),(4,6) (35 gems), gold at the other 4 (80 gold); Ryth kills it
// Run: node tools/probes/probe-prospector-remainder/makemap.mjs
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { ALTAR, Grid } from '../../../tools/mapgen/grid.mjs';
import { createEngine } from '../../../tools/mapgen/wasm.mjs';

const g = new Grid(30, 30, 'rotational');
g.picks = 3;
g.spawn = { x: 0, y: 0, w: 3, h: 3 };
g.set(10, 10, ALTAR);
const gold = (x, y) => g.camps.push({ type: 'gold_cluster', x, y });
const gem = (x, y) => g.camps.push({ type: 'gem_cluster', x, y });
for (let x = 4; x <= 6; x++) for (let y = 0; y <= 2; y++) gold(x, y);
for (const [x, y] of [[4, 4], [5, 4], [6, 4], [4, 5], [4, 6]]) gem(x, y);
for (const [x, y] of [[5, 5], [6, 5], [5, 6], [6, 6]]) gold(x, y);

const engine = await createEngine();
const bytes = engine.encode(g.toMap());
engine.load(bytes);
const out = path.join(path.dirname(fileURLToPath(import.meta.url)), 'prospector.map26a');
fs.writeFileSync(out, bytes);
console.log(g.render());
console.log(`wrote ${out} (${bytes.length} bytes)`);
