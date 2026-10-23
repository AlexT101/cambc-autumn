// Vault altars (tribute tiles unreachable on foot): launch tiles, trip lengths and line of sight.
// node tools/probes/vault/geometry.mjs maps/collision.map26a ...
import fs from 'node:fs';
import { Grid, GROUND, BUSH, WALL, ALTAR } from '../../../tools/mapgen/grid.mjs';
import { createEngine } from '../../../tools/mapgen/wasm.mjs';

const engine = await createEngine();
const cheb = (a, b, W) => Math.max(Math.abs(a % W - b % W), Math.abs(Math.floor(a / W) - Math.floor(b / W)));
for (const file of process.argv.slice(2)) {
  const g = Grid.fromMap(engine.decode(fs.readFileSync(file)));
  const W = g.W, camps = g.campMask(), pass = g.walkable(camps);
  const sA = g.spawnTiles(0), sB = g.spawnTiles(1);
  const passA = pass.slice(); for (const i of sB) passA[i] = 0;
  const dA = g.bfs(sA, passA);
  const near = (d, i) => { const x = i % W, y = (i - x) / W; return g.reachNear(d, x, y); };
  const altars = [...g.t.keys()].filter(i => g.t[i] === ALTAR);
  const walkAltar = Math.min(...altars.map(i => near(dA, i)).filter(d => d >= 0));
  for (const a of altars) {
    if (near(dA, a) >= 0) continue;
    const ax = a % W, ay = (a - ax) / W;
    const trib = [];
    for (let dy = -1; dy <= 1; dy++) for (let dx = -1; dx <= 1; dx++) { const j = (ay + dy) * W + ax + dx; if (g.in(ax + dx, ay + dy) && pass[j]) trib.push(j); }
    const din = g.bfs(trib, pass);
    let region = 0; for (const d of din) region += d >= 0;
    let best = null, launches = 0;
    for (let L = 0; L < g.t.length; L++) {
      if (dA[L] < 0) continue;
      let land = null;
      for (let T = 0; T < g.t.length; T++) if (din[T] >= 0 && cheb(L, T, W) <= 3 && (!land || din[T] < din[land])) land = T;
      if (land === null) continue;
      launches++;
      const cost = dA[L] + 3 + din[land];
      if (!best || cost < best.cost) best = { cost, L, land, walk: dA[L], inside: din[land] };
    }
    const xy = i => `(${i % W},${Math.floor(i / W)})`;
    console.log(`${file} vault altar ${xy(a)}: tribute tiles ${trib.length}, region ${region}, launch tiles ${launches}; ` +
      `A spawn: nearest walkable altar ${walkAltar} steps, vault ${best.cost} (walk ${best.walk} to ${xy(best.L)}, 3, land ${xy(best.land)}, ${best.inside} inside)`);
  }
}
