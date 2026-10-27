// Builds recall-<variant>.map26a for probe-recall-land: open 30x30, 3x3 spawns, 5 picks. Team A's spawn:
//   rot    (6..8,6..8), rotational      rot-nw (6..8,20..22), rotational      hor (6..8,6..8), horizontal
// rot-nw separates "row-major from (minX, minY)" from "the corner farthest from the centre"; hor checks B's order under
// another symmetry. (The builder rejects spawns under 9 tiles, so 5 champions can never fill one.)
// Run: node tools/probes/probe-recall-land/makemap.mjs <rot|rot-nw|hor>
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { Grid } from '../../../tools/mapgen/grid.mjs';
import { createEngine } from '../../../tools/mapgen/wasm.mjs';

const variant = process.argv[2] ?? 'rot';
const spec = { rot: ['rotational', 6], 'rot-nw': ['rotational', 20], hor: ['horizontal', 6] }[variant];
if (!spec) throw new Error(`unknown variant ${variant}`);
const g = new Grid(30, 30, spec[0]);
g.picks = 5;
g.spawn = { x: 6, y: spec[1], w: 3, h: 3 };

const engine = await createEngine();
const bytes = engine.encode(g.toMap());
engine.load(bytes);
const out = path.join(path.dirname(fileURLToPath(import.meta.url)), `recall-${variant}.map26a`);
fs.writeFileSync(out, bytes);
console.log(g.render());
console.log(`wrote ${out} (${bytes.length} bytes)`);
