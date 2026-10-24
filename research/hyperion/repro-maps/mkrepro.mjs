// Stall repro maps for CHANGES 138: `node research/hyperion/repro-maps/mkrepro.mjs` rewrites them here.
import fs from 'node:fs';
const T = new URL('../../../tools/mapgen/', import.meta.url).href;
const { Grid, GROUND, WALL, HOLE, BUSH, ALTAR } = await import(T + 'grid.mjs');
const { createEngine } = await import(T + 'wasm.mjs');
const { validate } = await import(T + 'generate.mjs');
const OUT = new URL('./', import.meta.url).pathname.replace(/^\/([A-Za-z]:)/, '$1');
const engine = await createEngine();

function base() {
  const g = new Grid(30, 30, 'rotational');
  g.spawn = { x: 2, y: 2, w: 3, h: 3 };
  g.picks = 3;
  return g;
}
const camp = (g, type, x, y) => g.camps.push({ type, x, y });
// Island: altar at (ax,ay), ground within 1, holes at Chebyshev distance 2..(1+w).
function island(g, ax, ay, w) {
  for (let y = ay - 1 - w; y <= ay + 1 + w; y++) for (let x = ax - 1 - w; x <= ax + 1 + w; x++) {
    if (!g.in(x, y)) continue;
    const d = Math.max(Math.abs(x - ax), Math.abs(y - ay));
    g.set(x, y, d === 0 ? ALTAR : d === 1 ? GROUND : HOLE);
  }
}
function save(g, name) {
  const bytes = engine.encode(g.toMap());
  engine.load(bytes);
  const { errors, warnings } = validate(g, { strict: false });
  console.log(`== ${name}: errors=${JSON.stringify(errors)} warnings=${JSON.stringify(warnings)}`);
  console.log(g.render());
  fs.writeFileSync(OUT + name + '.map26a', bytes);
}

{ // 1. spawnpin: elk at (7,3) reaches spawn columns x=3,4 (Chebyshev 4).
  const g = base();
  camp(g, 'elk', 7, 3);
  camp(g, 'gem_cluster', 10, 10); camp(g, 'gem_cluster', 10, 11);
  camp(g, 'gold_cluster', 14, 6);
  camp(g, 'wolf', 5, 15);
  camp(g, 'gem_cluster', 12, 17);
  g.set(4, 11, ALTAR);
  g.set(13, 13, ALTAR);
  g.set(9, 6, WALL); g.set(9, 7, WALL); g.set(18, 9, WALL); g.set(19, 9, WALL);
  save(g, 'spawnpin');
}
{ // 1b. spawnpin-golem: elk at (7,3) reaches spawn columns x=3,4 (Chebyshev 4).
  const g = base();
  camp(g, 'golem', 7, 3);
  camp(g, 'gem_cluster', 10, 10); camp(g, 'gem_cluster', 10, 11);
  camp(g, 'gold_cluster', 14, 6);
  camp(g, 'wolf', 5, 15);
  camp(g, 'gem_cluster', 12, 17);
  g.set(4, 11, ALTAR);
  g.set(13, 13, ALTAR);
  g.set(9, 6, WALL); g.set(9, 7, WALL); g.set(18, 9, WALL); g.set(19, 9, WALL);
  save(g, 'spawnpin-golem');
}
{ // 2. crystalaltar: both altars on islands with a 2-wide hole moat.
  const g = base();
  island(g, 10, 10, 2);
  camp(g, 'gem_cluster', 4, 9); camp(g, 'gem_cluster', 5, 9);
  camp(g, 'wolf', 9, 3);
  camp(g, 'gold_cluster', 15, 5);
  camp(g, 'gem_cluster', 4, 18); camp(g, 'gem_cluster', 4, 19);
  camp(g, 'elk', 14, 15);
  save(g, 'crystalaltar');
}
{ // 3. deadaltar: nearest altar on an island with a 4-wide moat; a walkable altar farther out.
  const g = base();
  island(g, 12, 4, 4);
  g.set(4, 17, ALTAR);
  camp(g, 'gem_cluster', 7, 11); camp(g, 'gem_cluster', 8, 11);
  camp(g, 'wolf', 3, 12);
  camp(g, 'gold_cluster', 10, 13);
  camp(g, 'gem_cluster', 13, 18);
  save(g, 'deadaltar');
}
