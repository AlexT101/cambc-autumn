// Builds corner.map26a for probe-corner: one station per blocker type, each station S with blockers on
// S+(1,0) and/or S+(0,1), so S -> S+(1,1) is a diagonal squeeze. Coordinates are team A's; the builder
// mirrors everything (rotational) for team B. Keep in sync with STATIONS in src/main.cpp.
// Run: node tools/probes/probe-corner/makemap.mjs
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { ALTAR, Grid, HOLE, WALL } from '../../../tools/mapgen/grid.mjs';
import { createEngine } from '../../../tools/mapgen/wasm.mjs';

const g = new Grid(30, 30, 'rotational');
g.picks = 3;
g.spawn = { x: 0, y: 0, w: 3, h: 3 };
const put = (kind, ...pts) => { for (const [x, y] of pts) g.set(x, y, kind); };
put(WALL, [7, 5]);                                   // A (6,5): one wall
put(HOLE, [12, 5], [11, 6]);                         // B (11,5): two holes
put(HOLE, [17, 5]);                                  // C (16,5): one hole
put(ALTAR, [22, 5], [21, 6]);                        // D (21,5): two altars
put(ALTAR, [27, 5]);                                 // E (26,5): one altar
g.camps.push({ type: 'gem_cluster', x: 7, y: 11 }, { type: 'gem_cluster', x: 6, y: 12 }); // F (6,11): two camps
g.camps.push({ type: 'gem_cluster', x: 12, y: 11 }); // G (11,11): one camp
                                                     // H (16,11): allies on (17,11) and (16,12)
for (let k = -2; k <= 3; k++) put(WALL, [22 + k, 11 - k]); // I (21,11): diagonal wall line (20,13)..(25,8)
put(WALL, [27, 14], [26, 15]);                       // J (26,14): two walls, no line

const engine = await createEngine();
const bytes = engine.encode(g.toMap());
engine.load(bytes);
const out = path.join(path.dirname(fileURLToPath(import.meta.url)), 'corner.map26a');
fs.writeFileSync(out, bytes);
console.log(g.render());
console.log(`wrote ${out} (${bytes.length} bytes)`);
