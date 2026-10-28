// Builds tpmember.map26a for probe-teleport-dead-member (team A's coordinates; mirrored rotationally for team B):
// spawn (0..2, 0..2); one-tile gold cluster G1 on (4,1); two-member gold group X (5,3) + Y (6,3).
// Run: node tools/probes/probe-teleport-dead-member/makemap.mjs
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { Grid } from '../../../tools/mapgen/grid.mjs';
import { createEngine } from '../../../tools/mapgen/wasm.mjs';

const g = new Grid(30, 30, 'rotational');
g.picks = 3;
g.spawn = { x: 0, y: 0, w: 3, h: 3 };
g.camps.push({ type: 'gold_cluster', x: 4, y: 1 }, { type: 'gold_cluster', x: 5, y: 3 }, { type: 'gold_cluster', x: 6, y: 3 });

const engine = await createEngine();
const bytes = engine.encode(g.toMap());
engine.load(bytes);
const out = path.join(path.dirname(fileURLToPath(import.meta.url)), 'tpmember.map26a');
fs.writeFileSync(out, bytes);
console.log(g.render());
console.log(`wrote ${out} (${bytes.length} bytes)`);
