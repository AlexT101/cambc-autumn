// Builds campunseen.map26a for probe-camp-unseen: 30x30 rotational, team A's spawn (0..2, 0..2), team B's (27..29, 27..29).
// Group G: gold clusters on (20,24),(21,24), 22+ tiles from A's spawn. Its rotational twin (9,5),(8,5) sits near A's spawn.
// Run: node tools/probes/probe-camp-unseen/makemap.mjs
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { Grid } from '../../../tools/mapgen/grid.mjs';
import { createEngine } from '../../../tools/mapgen/wasm.mjs';

const g = new Grid(30, 30, 'rotational');
g.picks = 3;
g.spawn = { x: 0, y: 0, w: 3, h: 3 };
g.camps.push({ type: 'gold_cluster', x: 9, y: 5 }, { type: 'gold_cluster', x: 8, y: 5 });

const engine = await createEngine();
const bytes = engine.encode(g.toMap());
engine.load(bytes);
const out = path.join(path.dirname(fileURLToPath(import.meta.url)), 'campunseen.map26a');
fs.writeFileSync(out, bytes);
console.log(g.render());
console.log(`wrote ${out} (${bytes.length} bytes)`);
