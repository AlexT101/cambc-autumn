// node zones.mjs OUT.json DIR...: per map file name, its altar count and walk-linked zone count (link 10).
import fs from 'node:fs';
import path from 'node:path';
import { createEngine } from '/home/ubuntu/cambc-autumn/tools/mapgen/wasm.mjs';
const [out, ...dirs] = process.argv.slice(2);
const engine = await createEngine();
const res = {};
for (const dir of dirs) for (const f of fs.readdirSync(dir).filter(f => f.endsWith('.map26a'))) {
  const m = engine.decode(fs.readFileSync(path.join(dir, f)));
  const W = m.width, H = m.height, block = new Uint8Array(W * H);
  for (const k of ['walls', 'holes', 'altars']) for (const [x, y] of m[k]) block[y * W + x] = 1;
  const alts = m.altars, n = alts.length;
  const trib = alts.map(([ax, ay]) => { const t = []; for (let dx = -1; dx <= 1; dx++) for (let dy = -1; dy <= 1; dy++) { const x = ax + dx, y = ay + dy; if (x >= 0 && y >= 0 && x < W && y < H && !block[y * W + x]) t.push(y * W + x); } return t; });
  const root = [...Array(n).keys()], find = a => { while (root[a] !== a) a = root[a] = root[root[a]]; return a; };
  for (let a = 0; a < n; a++) {
    const d = new Int32Array(W * H).fill(-1), q = [];
    for (const i of trib[a]) { d[i] = 0; q.push(i); }
    for (let h = 0; h < q.length; h++) { const i = q[h]; if (d[i] >= 10) continue; const x = i % W, y = (i / W) | 0;
      for (let dx = -1; dx <= 1; dx++) for (let dy = -1; dy <= 1; dy++) { const nx = x + dx, ny = y + dy; if (nx < 0 || ny < 0 || nx >= W || ny >= H) continue; const j = ny * W + nx; if (block[j] || d[j] >= 0) continue; d[j] = d[i] + 1; q.push(j); } }
    for (let b = a + 1; b < n; b++) if (trib[b].some(i => d[i] >= 0)) root[find(b)] = find(a);
  }
  res[f] = { altars: n, zones: new Set([...Array(n).keys()].map(find)).size };
}
fs.writeFileSync(out, JSON.stringify(res));
const c = {}; for (const v of Object.values(res)) c[v.zones] = (c[v.zones] || 0) + 1; console.log(Object.keys(res).length, 'maps; by zone count', c);
