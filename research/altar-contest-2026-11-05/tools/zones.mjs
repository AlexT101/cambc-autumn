// Altar zones by walk, as astraeus's presence change counts them (economy/presence.cc): altars are
// linked when the walk between their tribute tiles (open tiles within 1) is at most LINK, around
// walls, holes and altars. Prints one line a map: "<file> <altars> <zones> <camp-gem share within 10>".
// usage: node zones.mjs [--link 10] DIR|FILE...
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../../..');
const { createEngine } = await import(path.join(ROOT, 'tools/mapgen/wasm.mjs'));
const engine = await createEngine();

let link = 10;
const files = [];
const args = process.argv.slice(2);
for (let i = 0; i < args.length; i++) {
  if (args[i] === '--link') { link = +args[++i]; continue; }
  const st = fs.statSync(args[i]);
  if (st.isDirectory()) for (const f of fs.readdirSync(args[i]).sort()) { if (f.endsWith('.map26a')) files.push(path.join(args[i], f)); }
  else files.push(args[i]);
}

const GAMES_GEMS = { wolf: 4, elk: 15, golem: 36, gem_cluster: 7, gold_cluster: 0, monolith: 200 };

for (const file of files) {
  const m = engine.decode(fs.readFileSync(file));
  const W = m.width, H = m.height, blocked = new Uint8Array(W * H);
  for (const key of ['walls', 'holes', 'altars']) for (const [x, y] of m[key]) blocked[y * W + x] = 1;
  const altars = m.altars;
  const tribute = altars.map(([ax, ay]) => {
    const t = [];
    for (let dy = -1; dy <= 1; dy++) for (let dx = -1; dx <= 1; dx++) {
      const x = ax + dx, y = ay + dy;
      if (x >= 0 && y >= 0 && x < W && y < H && !blocked[y * W + x]) t.push(y * W + x);
    }
    return t;
  });
  const bfs = (src, cap) => {
    const d = new Int32Array(W * H).fill(-1), q = [];
    for (const s of src) { d[s] = 0; q.push(s); }
    for (let h = 0; h < q.length; h++) {
      const i = q[h], x = i % W, y = (i / W) | 0;
      if (d[i] >= cap) continue;
      for (let dy = -1; dy <= 1; dy++) for (let dx = -1; dx <= 1; dx++) {
        const nx = x + dx, ny = y + dy;
        if ((dx || dy) && nx >= 0 && ny >= 0 && nx < W && ny < H) {
          const j = ny * W + nx;
          if (!blocked[j] && d[j] < 0) { d[j] = d[i] + 1; q.push(j); }
        }
      }
    }
    return d;
  };
  // Union-find over walk links.
  const parent = altars.map((_, i) => i);
  const find = i => (parent[i] === i ? i : (parent[i] = find(parent[i])));
  for (let a = 0; a < altars.length; a++) {
    const d = bfs(tribute[a], link);
    for (let b = a + 1; b < altars.length; b++)
      if (tribute[b].some(i => d[i] >= 0 && d[i] <= link)) parent[find(a)] = find(b);
  }
  const zones = new Set(altars.map((_, i) => find(i))).size;
  // Team A's camp gems with a camp tile within Chebyshev 10 of an altar, over all of team A's.
  let tot = 0, near = 0;
  for (const c of m.camps ?? []) {
    const g = GAMES_GEMS[c.type] ?? 0;
    tot += g;
    if (altars.some(([ax, ay]) => Math.max(Math.abs(ax - c.x), Math.abs(ay - c.y)) <= 10)) near += g;
  }
  console.log(`${path.basename(file)} ${altars.length} ${zones} ${tot ? (near / tot).toFixed(3) : 'na'}`);
}
