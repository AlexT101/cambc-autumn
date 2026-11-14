// sites.mjs FILE|DIR...: per map, altar tiles and sites (tiles within Chebyshev 3 merged), as JSON lines.
import fs from 'node:fs';
import path from 'node:path';
import { ALTAR, Grid } from '../../../../tools/mapgen/grid.mjs';
import { createEngine } from '../../../../tools/mapgen/wasm.mjs';
const engine = await createEngine();
const files = process.argv.slice(2).flatMap(f => fs.statSync(f).isDirectory()
  ? fs.readdirSync(f).filter(x => x.endsWith('.map26a')).map(x => path.join(f, x)) : [f]);
for (const f of files) {
  let g;
  try { const b = fs.readFileSync(f); engine.load(b); g = Grid.fromMap(engine.decode(b)); } catch (e) { continue; }
  const alt = [];
  for (let i = 0; i < g.W * g.H; ++i) if (g.t[i] === ALTAR) alt.push([i % g.W, Math.floor(i / g.W)]);
  const site = alt.map((_, i) => i);
  const find = i => site[i] === i ? i : (site[i] = find(site[i]));
  for (let i = 0; i < alt.length; ++i) for (let j = i + 1; j < alt.length; ++j)
    if (Math.max(Math.abs(alt[i][0] - alt[j][0]), Math.abs(alt[i][1] - alt[j][1])) <= 3) site[find(i)] = find(j);
  const sizes = {};
  alt.forEach((_, i) => { const r = find(i); sizes[r] = (sizes[r] || 0) + 1; });
  console.log(JSON.stringify({ file: path.resolve(f), name: path.basename(f, '.map26a'), altars: alt.length, sites: Object.keys(sizes).length, site_sizes: Object.values(sizes).sort((a, b) => b - a), W: g.W, H: g.H }));
}
