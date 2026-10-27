// Builds capvis.map26a for probe-capture-vision (team A's coordinates; mirrored rotationally for team B):
// a 2-tile gem-cluster group on (12,2),(13,2). From (4,1) only (12,2) is within vision radius 8.
// Run: node tools/probes/probe-capture-vision/makemap.mjs
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { Grid } from '../../../tools/mapgen/grid.mjs';
import { createEngine } from '../../../tools/mapgen/wasm.mjs';

const g = new Grid(30, 30, 'rotational');
g.picks = 3;
g.spawn = { x: 0, y: 0, w: 3, h: 3 };
g.camps.push({ type: 'gem_cluster', x: 12, y: 2 }, { type: 'gem_cluster', x: 13, y: 2 });

const engine = await createEngine();
const bytes = engine.encode(g.toMap());
engine.load(bytes);
const out = path.join(path.dirname(fileURLToPath(import.meta.url)), 'capvis.map26a');
fs.writeFileSync(out, bytes);
console.log(g.render());
console.log(`wrote ${out} (${bytes.length} bytes)`);
