// altars.mjs DIR... > out.json: {map path: altar tile count} for every .map26a (recursing).
import fs from 'node:fs';
import path from 'node:path';
import { Grid, ALTAR } from '/home/ubuntu/cambc-autumn/tools/mapgen/grid.mjs';
import { createEngine } from '/home/ubuntu/cambc-autumn/tools/mapgen/wasm.mjs';
const engine = await createEngine(), out = {};
const walk = p => { const st = fs.statSync(p); if (st.isDirectory()) for (const f of fs.readdirSync(p)) walk(path.join(p, f)); else if (p.endsWith('.map26a')) {
  const g = Grid.fromMap(engine.decode(fs.readFileSync(p))); out[fs.realpathSync(p)] = g.t.reduce((n, t) => n + (t === ALTAR), 0); } };
for (const a of process.argv.slice(2)) walk(path.resolve(a));
process.stdout.write(JSON.stringify(out));
