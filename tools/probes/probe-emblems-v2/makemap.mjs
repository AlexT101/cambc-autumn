// Builds emblems.map26a for probe-emblems-v2 (team A's coordinates; mirrored rotationally for team B), 40x40, 5 picks:
//   gold 3x3 blocks (180 gold each): Ryth x4..6 y0..2, Prism x0..2 y4..6, Stellar x4..6 y4..6
//   X: gold (8,1); Y: gold (8,3),(8,4)            Capture emblem: hold X alone, then Ryth joins Vendetta's capture of Y
//   altar (10,10); gem groups 2/3/4/8 clusters    Tribute emblem: bags of 14, 21, 28, 56
//   wolf (18,15) near the Stellar meeting tile (18,18); B's Stellar meets at (21,21)
// Run: node tools/probes/probe-emblems-v2/makemap.mjs
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { ALTAR, Grid } from '../../../tools/mapgen/grid.mjs';
import { createEngine } from '../../../tools/mapgen/wasm.mjs';

const g = new Grid(40, 40, 'rotational');
g.picks = 5;
g.spawn = { x: 0, y: 0, w: 3, h: 3 };
g.set(10, 10, ALTAR);
const gold = (x, y) => g.camps.push({ type: 'gold_cluster', x, y });
const gem = (x, y) => g.camps.push({ type: 'gem_cluster', x, y });
for (const [x0, y0] of [[4, 0], [0, 4], [4, 4]])
  for (let x = x0; x < x0 + 3; x++) for (let y = y0; y < y0 + 3; y++) gold(x, y);
gold(8, 1); gold(8, 3); gold(8, 4);
gem(9, 11); gem(8, 11);
gem(11, 11); gem(11, 12); gem(11, 13);
gem(11, 9); gem(12, 9); gem(11, 8); gem(12, 8);
for (let x = 8; x <= 9; x++) for (let y = 6; y <= 9; y++) gem(x, y);
g.camps.push({ type: 'wolf', x: 18, y: 15 });

const engine = await createEngine();
const bytes = engine.encode(g.toMap());
engine.load(bytes);
const out = path.join(path.dirname(fileURLToPath(import.meta.url)), 'emblems.map26a');
fs.writeFileSync(out, bytes);
console.log(g.render());
console.log(`wrote ${out} (${bytes.length} bytes)`);
