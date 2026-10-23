// Builds hiddencamp.map26a for probe-dash-hidden-camp: a lone gem cluster on a one-tile bush at (8,8), so
// the diagonal dash (7,7)->(9,9) has exactly one path, through the unseen camp. Rotational; team B mirrored.
// A second gem cluster on ground at (8,14) is the visible control.
// Run: node tools/probes/probe-dash-hidden-camp/makemap.mjs
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { BUSH, Grid } from '../../../tools/mapgen/grid.mjs';
import { createEngine } from '../../../tools/mapgen/wasm.mjs';

const g = new Grid(30, 30, 'rotational');
g.picks = 3;
g.spawn = { x: 0, y: 0, w: 3, h: 3 };
g.set(8, 8, BUSH);
g.camps.push({ type: 'gem_cluster', x: 8, y: 8 });
g.camps.push({ type: 'gem_cluster', x: 8, y: 14 }); // control: visible camp on ground, dash (7,13)->(9,15)

const engine = await createEngine();
const bytes = engine.encode(g.toMap());
engine.load(bytes);
const back = Grid.fromMap(engine.decode(bytes));
console.log(`(8,8) tile=${back.get(8, 8)} camps=${JSON.stringify(back.camps)}`);
const out = path.join(path.dirname(fileURLToPath(import.meta.url)), 'hiddencamp.map26a');
fs.writeFileSync(out, bytes);
console.log(back.render());
console.log(`wrote ${out} (${bytes.length} bytes)`);
