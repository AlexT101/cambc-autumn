// Builds dash.map26a for probe-dash-diagonal: one station per dash path shape, each forcing a
// dash whose only <= 2 king step paths cross a hole or altar diagonally, or squeeze diagonally
// between blockers. Coordinates are team A's; the builder mirrors everything (rotational) for team B.
// Keep in sync with STATIONS in src/main.cpp.
// Run: node tools/probes/probe-dash-diagonal/makemap.mjs
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { ALTAR, Grid, HOLE, WALL } from '../../../tools/mapgen/grid.mjs';
import { createEngine } from '../../../tools/mapgen/wasm.mjs';

const g = new Grid(30, 30, 'rotational');
g.picks = 3;
g.spawn = { x: 0, y: 0, w: 3, h: 3 };
const put = (kind, ...pts) => { for (const [x, y] of pts) g.set(x, y, kind); };
put(HOLE, [6, 6]);                                   // K (5,5): (2,2) only via a hole
put(HOLE, [12, 5], [12, 6]);                         // L (11,5): (2,1) only via a hole, cardinal+diagonal
put(WALL, [18, 5], [17, 6]); put(HOLE, [18, 6]);     // M (17,5): (2,2) squeezes onto a hole between walls
put(ALTAR, [24, 6]);                                 // N (23,5): (2,2) only via an altar
put(WALL, [6, 12]);                                  // O (5,11): (2,2) only via a wall: refused
put(WALL, [12, 11], [11, 12], [13, 12], [12, 13]);   // P (11,11): (2,2) squeezes twice between walls
put(HOLE, [18, 11], [18, 12]); put(WALL, [17, 12]);  // Q (17,11): (1,2) only via holes, with a squeeze

const engine = await createEngine();
const bytes = engine.encode(g.toMap());
engine.load(bytes);
const out = path.join(path.dirname(fileURLToPath(import.meta.url)), 'dash.map26a');
fs.writeFileSync(out, bytes);
console.log(g.render());
console.log(`wrote ${out} (${bytes.length} bytes)`);
