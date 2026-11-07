// Builds clustersleep.map26a for probe-cluster-sleep (team A's coordinates; rotated for team B): 64x64, 5 picks,
// spawn (0..2,0..2). Ten scenarios, kept 6 rows apart so no hold tile is within 5 of another scenario's camps:
// column x=8 (team A's scenarios 0-4), column x=30 (team B's 5-9, run on B's rotated copy). See main.cpp.
// Run: node tools/probes/probe-cluster-sleep/makemap.mjs
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { Grid } from '../../../tools/mapgen/grid.mjs';
import { createEngine } from '../../../tools/mapgen/wasm.mjs';

const g = new Grid(64, 64, 'rotational');
g.picks = 5;
g.spawn = { x: 0, y: 0, w: 3, h: 3 };
const c = (type, x, y) => g.camps.push({ type, x, y });
c('gem_cluster', 8, 4);                                                    // 0
c('gem_cluster', 8, 10);                                                   // 1
c('gold_cluster', 8, 16);                                                  // 2
c('gold_cluster', 8, 22);                                                  // 3
c('gem_cluster', 8, 28);                                                   // 4
c('gold_cluster', 30, 4);                                                  // 5
c('elk', 30, 10); c('gem_cluster', 31, 10); c('gold_cluster', 32, 10);     // 6
c('elk', 30, 16); c('gold_cluster', 31, 16); c('gem_cluster', 32, 16);     // 7
c('gem_cluster', 30, 22); c('gold_cluster', 31, 22);                       // 8
c('elk', 30, 28); c('gem_cluster', 30, 29);                                // 9

const engine = await createEngine();
const bytes = engine.encode(g.toMap());
engine.load(bytes);
const out = path.join(path.dirname(fileURLToPath(import.meta.url)), 'clustersleep.map26a');
fs.writeFileSync(out, bytes);
console.log(g.render());
console.log(`wrote ${out} (${bytes.length} bytes)`);
