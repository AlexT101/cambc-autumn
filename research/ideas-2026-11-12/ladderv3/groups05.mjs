// The 05 maps' camp groups, spawns and terrain next to another set: the source of generate.mjs's calibration 4 tables.
// Make-ups are share of a map's team A groups (maps weighted equally), as LADDER_GROUPS; shapes as LADDER_SHAPES.
//   node research/ideas-2026-11-12/ladderv3/groups05.mjs DIR_OR_FILE... [--json]
import fs from 'node:fs';
import path from 'node:path';
import { Grid, WALL, HOLE, BUSH, N4 } from '../../../tools/mapgen/grid.mjs';
import { sideGroups, spawnFields } from '../../../tools/mapgen/generate.mjs';
import { createEngine } from '../../../tools/mapgen/wasm.mjs';

const L = { wolf: 'W', elk: 'E', golem: 'G', monolith: 'M', gem_cluster: 'g', gold_cluster: 'd' };
const args = process.argv.slice(2), json = args.includes('--json');
const files = args.filter(a => !a.startsWith('--')).flatMap(p => fs.statSync(p).isDirectory() ? fs.readdirSync(p).filter(f => f.endsWith('.map26a')).sort().map(f => path.join(p, f)) : [p]);
const engine = await createEngine();
const canon = cells => {
  let best = null;
  for (let t = 0; t < 8; t++) {
    let c = cells.map(([x, y, k]) => { let a = x, b = y; if (t & 1) a = -a; if (t & 2) b = -b; if (t & 4) [a, b] = [b, a]; return [a, b, k]; });
    const mx = Math.min(...c.map(p => p[0])), my = Math.min(...c.map(p => p[1]));
    c = c.map(([a, b, k]) => [a - mx, b - my, k]);
    const W = Math.max(...c.map(p => p[0])) + 1, H = Math.max(...c.map(p => p[1])) + 1, rows = [];
    for (let y = 0; y < H; y++) { let s = ''; for (let x = 0; x < W; x++) { const q = c.find(p => p[0] === x && p[1] === y); s += q ? q[2] : '.'; } rows.push(s); }
    const key = rows.join('/'), shape = key.replace(/[^./]/g, '#');
    if (!best || shape < best.shape || (shape === best.shape && key < best.key)) best = { shape, key };
  }
  return best;
};
const rectDist = (sp, x, y) => Math.max(sp.x - x, 0, x - (sp.x + sp.w - 1), sp.y - y, y - (sp.y + sp.h - 1));
const make = {}, shapes = {}, keys = {}, perMap = [];
for (const f of files) {
  const g = Grid.fromMap(engine.decode(fs.readFileSync(f))), { mine, shared } = sideGroups(g);
  const n = mine.length || 1, m = {};
  for (const q of mine) {
    const k = q.members.map(c => L[c.type]).sort().join('');
    const label = q.members.length >= 10 ? `big:${q.members.some(c => !c.type.endsWith('_cluster')) ? 'guarded' : q.members.every(c => c.type === 'gem_cluster') ? 'gems' : q.members.every(c => c.type === 'gold_cluster') ? 'gold' : 'mixed'}` : k;
    m[label] = (m[label] ?? 0) + 1 / n;
    if (q.members.length >= 3 && q.members.length <= 9) {
      const c = canon(q.members.map(c => [c.x, c.y, L[c.type]]));
      (shapes[q.members.length] ??= {})[c.shape] = (shapes[q.members.length][c.shape] ?? 0) + 1;
      (keys[c.shape] ??= {})[c.key] = (keys[c.shape][c.key] ?? 0) + 1;
    }
  }
  for (const [k, v] of Object.entries(m)) make[k] = (make[k] ?? 0) + v / files.length;
  const sp = g.spawn, cnt = k => g.t.reduce((s, t) => s + (t === k), 0) / g.t.length;
  const near = Math.min(...g.allCamps().map(c => rectDist(sp, c.x, c.y)), 99);
  const nearMon = Math.min(...g.allCamps().filter(c => !c.type.endsWith('_cluster')).map(c => rectDist(sp, c.x, c.y)), 99);
  // Bush clusters: count and mean size.
  const seen = new Uint8Array(g.t.length), sizes = [];
  for (let i = 0; i < g.t.length; i++) if (g.t[i] === BUSH && !seen[i]) {
    let s = 0; const st = [i]; seen[i] = 1;
    while (st.length) { const j = st.pop(); s++; const x = j % g.W, y = (j - x) / g.W; for (const [dx, dy] of N4) { const k = (y + dy) * g.W + x + dx; if (g.in(x + dx, y + dy) && !seen[k] && g.t[k] === BUSH) { seen[k] = 1; st.push(k); } } }
    sizes.push(s);
  }
  perMap.push({ map: path.basename(f, '.map26a'), W: g.W, H: g.H, sym: g.sym, spawn: `${Math.max(sp.w, sp.h)}x${Math.min(sp.w, sp.h)}`, near_camp: near, near_monster: nearMon,
    walls: +cnt(WALL).toFixed(3), holes: +cnt(HOLE).toFixed(3), bushes: +cnt(BUSH).toFixed(3), bush_clusters: sizes.length, bush_mean: sizes.length ? +(sizes.reduce((a, b) => a + b, 0) / sizes.length).toFixed(1) : 0,
    groups: mine.length, shared: shared.length, shared_sizes: shared.map(q => q.members.length), monsters_per_group: +(mine.reduce((s, q) => s + q.members.filter(c => !c.type.endsWith('_cluster')).length, 0) / n).toFixed(2) });
}
if (json) { console.log(JSON.stringify({ make, shapes, keys, perMap })); process.exit(0); }
console.log(`${files.length} maps`);
console.log('make-ups (% of a map\'s groups):');
console.log(Object.entries(make).sort((a, b) => b[1] - a[1]).map(([k, v]) => `${k}:${(100 * v).toFixed(1)}`).join(' '));
for (const n of Object.keys(shapes)) {
  const tot = Object.values(shapes[n]).reduce((a, b) => a + b, 0);
  console.log(`n=${n} (${tot}): ` + Object.entries(shapes[n]).sort((a, b) => b[1] - a[1]).slice(0, 8).map(([s, v]) => `${s} ${(100 * v / tot).toFixed(0)}% [${Object.entries(keys[s]).sort((a, b) => b[1] - a[1]).slice(0, 3).map(([k, c]) => `${k}:${c}`).join(' ')}]`).join('  '));
}
for (const r of perMap) console.log(JSON.stringify(r));
