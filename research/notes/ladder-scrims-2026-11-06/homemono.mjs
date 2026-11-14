import fs from 'node:fs';
import path from 'node:path';
const ROOT='/home/ubuntu/cambc-autumn';
const { Grid } = await import(ROOT+'/tools/mapgen/grid.mjs');
const { createEngine } = await import(ROOT+'/tools/mapgen/wasm.mjs');
const engine = await createEngine();
const out={};
for (const f of fs.readdirSync(ROOT+'/maps').filter(f=>f.endsWith('.map26a')).sort()) {
  const g = Grid.fromMap(engine.decode(fs.readFileSync(ROOT+'/maps/'+f)));
  const tiles = g.spawnTiles(0).map(i=>[i%g.W, Math.floor(i/g.W)]);
  let best=1e9;
  for (const c of g.allCamps()) if (c.type==='monolith') for (const [x,y] of tiles) best=Math.min(best, Math.max(Math.abs(c.x-x),Math.abs(c.y-y)));
  out[path.basename(f,'.map26a')]=best;
}
console.log(JSON.stringify(out));
