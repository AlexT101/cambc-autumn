import fs from 'node:fs';
const ROOT = new URL('../../..', import.meta.url).pathname;
const { Grid } = await import(ROOT + '/tools/mapgen/grid.mjs');
const { createEngine } = await import(ROOT + '/tools/mapgen/wasm.mjs');
const e = await createEngine();
for (const f of process.argv.slice(2)) { const g = Grid.fromMap(e.decode(fs.readFileSync(f))); console.log(f); console.log(g.render()); }
