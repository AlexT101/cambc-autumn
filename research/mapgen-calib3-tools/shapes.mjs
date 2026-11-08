// Team A's group shapes of 3-9 cells (canonical under the 8 symmetries) by size, with their commonest member layouts
// (W wolf, E elk, G golem, M monolith, g gem, d gold cluster): the source of generate.mjs's LADDER_SHAPES.
//   node research/mapgen-calib3-tools/shapes.mjs maps/*.map26a
import fs from 'node:fs';
import { Grid } from '../../tools/mapgen/grid.mjs';
import { sideGroups } from '../../tools/mapgen/generate.mjs';
import { createEngine } from '../../tools/mapgen/wasm.mjs';
const L = { wolf: 'W', elk: 'E', golem: 'G', monolith: 'M', gem_cluster: 'g', gold_cluster: 'd' };
const files = process.argv.slice(2), engine = await createEngine(), pat = {}, types = {};
const canon = cells => {
  let best = null;
  for (let t = 0; t < 8; t++) {
    let c = cells.map(([x, y, k]) => { let a = x, b = y; if (t & 1) a = -a; if (t & 2) b = -b; if (t & 4) [a, b] = [b, a]; return [a, b, k]; });
    const mx = Math.min(...c.map(p => p[0])), my = Math.min(...c.map(p => p[1]));
    c = c.map(([a, b, k]) => [a - mx, b - my, k]);
    const W = Math.max(...c.map(p => p[0])) + 1, H = Math.max(...c.map(p => p[1])) + 1, rows = [];
    for (let y = 0; y < H; y++) { let s = ''; for (let x = 0; x < W; x++) { const q = c.find(p => p[0] === x && p[1] === y); s += q ? q[2] : '.'; } rows.push(s); }
    const key = rows.join('/');
    const shape = key.replace(/[^./]/g, '#');
    if (!best || shape < best.shape || (shape === best.shape && key < best.key)) best = { shape, key };
  }
  return best;
};
for (const f of files) {
  const g = Grid.fromMap(engine.decode(fs.readFileSync(f)));
  const { mine, shared } = sideGroups(g);
  for (const q of [...mine]) {
    const n = q.members.length; if (n < 3 || n > 9) continue;
    const c = canon(q.members.map(m => [m.x, m.y, L[m.type]]));
    (pat[n] ??= {})[c.shape] = (pat[n][c.shape] ?? 0) + 1;
    (types[c.shape] ??= {})[c.key] = (types[c.shape][c.key] ?? 0) + 1;
  }
}
for (const n of Object.keys(pat)) {
  const tot = Object.values(pat[n]).reduce((a, b) => a + b, 0);
  console.log(`n=${n} (${tot})`);
  for (const [s, v] of Object.entries(pat[n]).sort((a, b) => b[1] - a[1]).slice(0, 8)) {
    const ex = Object.entries(types[s]).sort((a, b) => b[1] - a[1]).slice(0, 4).map(([k, c]) => `${k}:${c}`).join('  ');
    console.log(`  ${s.padEnd(14)} ${(100 * v / tot).toFixed(0).padStart(3)}%   ${ex}`);
  }
}
