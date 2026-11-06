import fs from 'node:fs';
import { Grid } from '/home/ubuntu/cambc-autumn/tools/mapgen/grid.mjs';
import { metrics } from '/home/ubuntu/cambc-autumn/tools/mapgen/generate.mjs';
import { createEngine } from '/home/ubuntu/cambc-autumn/tools/mapgen/wasm.mjs';
const e = await createEngine();
for (const f of process.argv.slice(2)) { const b = fs.readFileSync(f); e.load(b); const g = Grid.fromMap(e.decode(b)); console.log(JSON.stringify({file: f, metrics: metrics(g)})); }
