// Builds tpcamp.map26a for probe-teleport-dead-camp (team A's coordinates; mirrored rotationally for team B):
// spawn (0..2, 0..2); one-tile gold clusters G1 on (4,1) and G2 on (5,3), both within 3 of spawn tile (2,2).
// Run: node tools/probes/probe-teleport-dead-camp/makemap.mjs
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { Grid } from '../../../tools/mapgen/grid.mjs';
import { createEngine } from '../../../tools/mapgen/wasm.mjs';

const g = new Grid(30, 30, 'rotational');
g.picks = 3;
g.spawn = { x: 0, y: 0, w: 3, h: 3 };
g.camps.push({ type: 'gold_cluster', x: 4, y: 1 }, { type: 'gold_cluster', x: 5, y: 3 });

const engine = await createEngine();
const bytes = engine.encode(g.toMap());
engine.load(bytes);
const out = path.join(path.dirname(fileURLToPath(import.meta.url)), 'tpcamp.map26a');
fs.writeFileSync(out, bytes);
console.log(g.render());
console.log(`wrote ${out} (${bytes.length} bytes)`);
