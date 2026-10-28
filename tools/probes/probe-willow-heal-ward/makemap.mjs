// Builds healward.map26a for probe-willow-heal-ward (team A's coordinates; mirrored rotationally for team B):
// spawn (0..2, 0..2); two-tile bush cluster B (7,6) + BW (7,5); wolf (9,8).
// Run: node tools/probes/probe-willow-heal-ward/makemap.mjs
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { Grid, BUSH } from '../../../tools/mapgen/grid.mjs';
import { createEngine } from '../../../tools/mapgen/wasm.mjs';

const g = new Grid(30, 30, 'rotational');
g.picks = 2;
g.spawn = { x: 0, y: 0, w: 3, h: 3 };
g.set(7, 6, BUSH);
g.set(7, 5, BUSH);
g.camps.push({ type: 'wolf', x: 9, y: 8 });

const engine = await createEngine();
const bytes = engine.encode(g.toMap());
engine.load(bytes);
const out = path.join(path.dirname(fileURLToPath(import.meta.url)), 'healward.map26a');
fs.writeFileSync(out, bytes);
console.log(g.render());
console.log(`wrote ${out} (${bytes.length} bytes)`);
