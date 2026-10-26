// Per map: the deepest field (layers) over farmed group centres and the ally spawn, on walking walls,
// and search_cost_estimate's price for it. node fieldcost.mjs REPO_ROOT DIR... > out.json
import fs from 'node:fs';
import path from 'node:path';
const root = process.argv[2];
const { Grid } = await import(path.join(root, 'tools/mapgen/grid.mjs').replace(/\\/g, '/').replace(/^([A-Za-z]):/, 'file:///$1:'));
const { createEngine } = await import(path.join(root, 'tools/mapgen/wasm.mjs').replace(/\\/g, '/').replace(/^([A-Za-z]):/, 'file:///$1:'));
const engine = await createEngine();
const dirs = process.argv.slice(3);
const rows = [];
for (const dir of dirs) {
  for (const f of fs.readdirSync(dir).filter(f => f.endsWith('.map26a'))) {
    const g = Grid.fromMap(engine.decode(fs.readFileSync(path.join(dir, f))));
    const W = g.W, H = g.H;
    const pass = g.walkable();
    for (const i of g.spawnTiles(1)) pass[i] = 0;
    const chunks = Math.ceil(W / 8) * Math.ceil(H / 8);
    const cost = l => 4000 + chunks * (20 + l);
    const ecc = starts => { const d = g.bfs(starts, pass); let m = -1; for (const v of d) m = Math.max(m, v); return m + 1; };
    const groups = g.groups();
    let deepest = ecc(g.spawnTiles(0)), sum = 0, n = 0, over40 = 0;
    const centre = gr => {
      const mx = gr.members.reduce((s, c) => s + c.x, 0) / gr.members.length, my = gr.members.reduce((s, c) => s + c.y, 0) / gr.members.length;
      let best = null, bd = 1e9;
      for (const c of gr.members) { const d = (c.x - mx) ** 2 + (c.y - my) ** 2; if (d < bd) bd = d, best = c; }
      return best.y * W + best.x;
    };
    for (const gr of groups) {
      if (gr.members.some(c => c.type === 'monolith')) continue;
      const l = ecc([centre(gr)]);
      deepest = Math.max(deepest, l), sum += cost(l), n++;
      if (cost(l) > 40000) over40++;
    }
    // spawn to spawn walking
    const d = g.bfs(g.spawnTiles(0), g.walkable());
    let s2s = 1e9; for (const i of g.spawnTiles(1)) if (d[i] >= 0) s2s = Math.min(s2s, d[i]);
    rows.push({ dir: path.basename(dir), map: f.replace('.map26a', ''), size: `${W}x${H}`, groups: groups.length, deepest, cost: cost(deepest), mean_centre: n ? Math.round(sum / n) : 0, over40, s2s });
  }
}
rows.sort((a, b) => b.cost - a.cost);
console.log(JSON.stringify(rows));
