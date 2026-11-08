// Gem zones: gem-bearing camp groups clustered by Chebyshev gap between their tiles (with --box,
// between their boxes, as economy/gem_zone.cc does).
// node gemzone.mjs GAP [--box] DIR_OR_FILE... -> one JSON line per map (cwd: the repo root)
import fs from 'node:fs';
import path from 'node:path';
const ROOT = new URL('../../..', import.meta.url).pathname;
const { Grid, ALTAR, CAMP } = await import(ROOT + '/tools/mapgen/grid.mjs');
const { createEngine } = await import(ROOT + '/tools/mapgen/wasm.mjs');
const { walk } = await import(ROOT + '/tools/draftlab/features.mjs');

const [gap, ...rest] = process.argv.slice(2);
const BOX = rest.includes('--box'), inputs = rest.filter(a => a !== '--box');
const GAP = Number(gap);
const files = [];
for (const p of inputs) walk(path.resolve(p), files);
const engine = await createEngine();
for (const f of files) {
  let g;
  try { g = Grid.fromMap(engine.decode(fs.readFileSync(f))); } catch (e) { continue; }
  const groups = g.groups().filter(q => q.gems > 0);
  const tiles = q => [...q.tiles].map(i => [i % g.W, Math.floor(i / g.W)]);
  const T = groups.map(tiles);
  const dTiles = (a, b) => { let m = 1e9; for (const [x, y] of a) for (const [u, v] of b) m = Math.min(m, Math.max(Math.abs(x - u), Math.abs(y - v))); return m; };
  const bx = a => { const xs = a.map(p => p[0]), ys = a.map(p => p[1]); return [Math.min(...xs), Math.min(...ys), Math.max(...xs), Math.max(...ys)]; };
  const dBox = (a, b) => { const A = bx(a), B = bx(b); return Math.max(B[0] - A[2], A[0] - B[2], B[1] - A[3], A[1] - B[3], 0); };
  const d = BOX ? dBox : dTiles;
  const comp = groups.map((_, i) => i);
  const find = i => comp[i] === i ? i : (comp[i] = find(comp[i]));
  for (let i = 0; i < T.length; i++) for (let j = i + 1; j < T.length; j++) if (d(T[i], T[j]) <= GAP) comp[find(i)] = find(j);
  const zones = new Map();
  for (let i = 0; i < T.length; i++) { const r = find(i); if (!zones.has(r)) zones.set(r, []); zones.get(r).push(i); }
  const rate = q => q.gems / Math.max(...q.members.map(m => CAMP[m.type].respawn));
  const total = groups.reduce((s, q) => s + q.gems, 0), rtotal = groups.reduce((s, q) => s + rate(q), 0);
  const sp = g.spawnTiles(0).map(i => [i % g.W, Math.floor(i / g.W)]), sb = g.spawnTiles(1).map(i => [i % g.W, Math.floor(i / g.W)]);
  const zs = [...zones.values()].map(ix => {
    const all = ix.flatMap(i => T[i]);
    const xs = all.map(p => p[0]), ys = all.map(p => p[1]);
    return { gems: ix.reduce((s, i) => s + groups[i].gems, 0), rate: ix.reduce((s, i) => s + rate(groups[i]), 0), groups: ix.length, dA: d(all, sp), dB: d(all, sb),
      types: ix.flatMap(i => groups[i].members.map(m => m.type)).sort().join(','),
      bbox: [Math.min(...xs), Math.min(...ys), Math.max(...xs), Math.max(...ys)] };
  }).sort((a, b) => b.rate - a.rate);
  let altars = 0; for (const t of g.t) altars += t === ALTAR;
  console.log(JSON.stringify({ file: path.relative(ROOT, f), W: g.W, H: g.H, sym: g.sym, altars, total, nzones: zs.length,
    top_share: total ? zs[0].gems / total : 0, rtop: rtotal ? zs[0].rate / rtotal : 0, rtotal, zones: zs }));
}
