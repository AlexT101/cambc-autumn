// Per camp group of team A: steps to the nearest walkable altar against the vault route
// (walk to a launch tile, 3 channel turns, walk inside to a tribute tile).
// node rules-verification/probes/vault/trips.mjs maps/collision.map26a
import fs from 'node:fs';
import { Grid, ALTAR } from '../../../tools/mapgen/grid.mjs';
import { createEngine } from '../../../tools/mapgen/wasm.mjs';

const engine = await createEngine();
for (const file of process.argv.slice(2)) {
  const g = Grid.fromMap(engine.decode(fs.readFileSync(file)));
  const W = g.W, camps = g.campMask(), pass = g.walkable(camps), N = g.t.length;
  const sB = new Set(g.spawnTiles(1)), passA = pass.map((p, i) => (sB.has(i) ? 0 : p));
  const dSpawn = g.bfs(g.spawnTiles(0), passA);
  const tribOf = a => { const x = a % W, y = (a - x) / W, out = []; for (let dy = -1; dy <= 1; dy++) for (let dx = -1; dx <= 1; dx++) if (g.in(x + dx, y + dy) && pass[(y + dy) * W + x + dx]) out.push((y + dy) * W + x + dx); return out; };
  const altars = [...g.t.keys()].filter(i => g.t[i] === ALTAR);
  const walkTrib = altars.filter(a => tribOf(a).some(i => dSpawn[i] >= 0)).flatMap(tribOf).filter(i => dSpawn[i] >= 0);
  const vaults = altars.filter(a => !tribOf(a).some(i => dSpawn[i] >= 0));
  const toWalk = g.bfs(walkTrib, passA);
  // Cost from each outside tile via any vault: min over launch L of dist(p, L) + 3 + inside(T).
  const launchCost = new Int32Array(N).fill(-1);
  for (const v of vaults) {
    const din = g.bfs(tribOf(v), pass);
    for (let L = 0; L < N; L++) {
      if (dSpawn[L] < 0) continue;
      const lx = L % W, ly = (L - lx) / W;
      for (let dy = -3; dy <= 3; dy++) for (let dx = -3; dx <= 3; dx++) {
        if (!g.in(lx + dx, ly + dy)) continue;
        const T = (ly + dy) * W + lx + dx;
        if (din[T] >= 0 && (launchCost[L] < 0 || 3 + din[T] < launchCost[L])) launchCost[L] = 3 + din[T];
      }
    }
  }
  // Multi-source Dijkstra-ish: BFS layers with initial costs.
  const vaultCost = new Int32Array(N).fill(-1);
  const order = [...launchCost.keys()].filter(i => launchCost[i] >= 0).sort((a, b) => launchCost[a] - launchCost[b]);
  const buckets = []; for (const i of order) (buckets[launchCost[i]] ??= []).push(i);
  for (let c = 0; c < buckets.length + N; c++) {
    const b = buckets[c]; if (!b) { if (c > buckets.length + 200) break; continue; }
    for (const i of b) {
      if (vaultCost[i] >= 0) continue;
      vaultCost[i] = c;
      const x = i % W, y = (i - x) / W;
      for (let dy = -1; dy <= 1; dy++) for (let dx = -1; dx <= 1; dx++) {
        if (!(dx || dy) || !g.in(x + dx, y + dy)) continue;
        const j = (y + dy) * W + x + dx;
        if (passA[j] && dSpawn[j] >= 0 && vaultCost[j] < 0) (buckets[c + 1] ??= []).push(j);
      }
    }
  }
  const xy = i => `(${i % W},${Math.floor(i / W)})`;
  const spawnC = g.spawnTiles(0)[0];
  console.log(`${file}: from spawn walk ${Math.min(...walkTrib.map(i => dSpawn[i]))} vault ${vaultCost[spawnC]}`);
  for (const grp of g.groups()) {
    const c = grp.members[0], i = c.y * W + c.x;
    let best = null;
    for (let dy = -1; dy <= 1; dy++) for (let dx = -1; dx <= 1; dx++) { const j = (c.y + dy) * W + c.x + dx; if (g.in(c.x + dx, c.y + dy) && toWalk[j] >= 0 && (!best || toWalk[j] < toWalk[best])) best = j; }
    if (best === null || dSpawn[best] < 0) continue;
    const mine = dSpawn[best] <= g.bfs(g.spawnTiles(1), pass.map((p, k) => (g.spawnTiles(0).includes(k) ? 0 : p)))[best];
    if (!mine) continue;
    console.log(`  group ${xy(i)} ${grp.members.map(m => m.type).join('+')}: walk ${toWalk[best]}, vault ${vaultCost[best]}`);
  }
}
