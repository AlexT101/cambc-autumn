// Scenario presets. Vision and mobility: hole mazes (sight and path disagree), dash and wall
// lattices, leaky diagonals and checkerboards, fog fields and bush-ringed altars. Economy: gold in
// the centre, turtle gradients, far, moated and clustered altars, cluster carpets, mega-groups and a
// fuel stress test. Designers follow design.mjs: drawn with g.set (so symmetric as drawn), objectives
// named as sites for generate.mjs to fill.
import { ALTAR, BUSH, GROUND, GenFail, HOLE, WALL, valueNoise } from './grid.mjs';
import { altarPlan, along, begin, blob, box, centre, clearSpawn, clumps, disc, dist, lerp, meander, mirrorPt, onSideA, placeSpawn, put, raise, scatterPrefabs, site, smooth, spawnCentre, stroke, tier } from './design.mjs';
// Cyclic import: used only inside functions.
import { TEMPLATES as GEN_TEMPLATES, stillConnected, tryGroup } from './generate.mjs';

const N4 = [[1, 0], [-1, 0], [0, 1], [0, -1]];
const cheb = (a, b) => Math.max(Math.abs(a[0] - b[0]), Math.abs(a[1] - b[1]));
const xy = (g, i) => [i % g.W, Math.floor(i / g.W)];

// A self-mirrored tile at the centre, if the dimensions have one (an altar there is everyone's).
function selfTile(g) {
  const [cx, cy] = centre(g), ok = g.sym === 'horizontal' ? g.W % 2 : g.sym === 'vertical' ? g.H % 2 : g.W % 2 && g.H % 2;
  return ok ? [Math.round(cx), Math.round(cy)] : null;
}

// Points on team A's side, apart from each other (and their mirrors), the spawns and the axis.
function spots(g, rng, n, { gap = 8, spawnGap = 8, axisGap = gap, margin = 3 } = {}) {
  const S = spawnCentre(g), S2 = mirrorPt(g, S), out = [];
  for (let tries = 0; out.length < n && tries < 400; tries++) {
    const p = [rng.int(margin, g.W - 1 - margin), rng.int(margin, g.H - 1 - margin)];
    if (!onSideA(g, p) || dist(p, S) < spawnGap || dist(p, S2) < spawnGap || dist(p, mirrorPt(g, p)) < axisGap) continue;
    if (out.some(q => dist(q, p) < gap || dist(mirrorPt(g, q), p) < gap)) continue;
    out.push(p);
  }
  return out;
}

// Exact camp groups from tiles (their mirrors added): each 4-connected piece is one group, shared
// when the symmetry maps it onto itself (stored as its canonical half), else stored on A's side.
function cellGroups(g, tiles, typeAt) {
  const set = new Set(), done = new Set(), S = spawnCentre(g), out = [];
  for (const [x, y] of tiles) if (g.in(x, y)) { set.add(y * g.W + x); set.add(g.mirror(y * g.W + x)); }
  for (const i of set) {
    if (done.has(i)) continue;
    const comp = [i];
    done.add(i);
    for (let h = 0; h < comp.length; h++) {
      const [x, y] = xy(g, comp[h]);
      for (const [dx, dy] of N4) { const k = (y + dy) * g.W + x + dx; if (g.in(x + dx, y + dy) && set.has(k) && !done.has(k)) { done.add(k); comp.push(k); } }
    }
    const shared = comp.includes(g.mirror(i));
    let cells = comp;
    if (shared) cells = comp.filter(k => k <= g.mirror(k));
    else {
      const c = comp.reduce((a, k) => [a[0] + xy(g, k)[0] / comp.length, a[1] + xy(g, k)[1] / comp.length], [0, 0]), dA = dist(c, S), dB = dist(mirrorPt(g, c), S);
      if (dA > dB || (dA === dB && Math.min(...comp) > Math.min(...comp.map(k => g.mirror(k))))) continue;
    }
    out.push({ cells: cells.map((k, n) => [typeAt(...xy(g, k), n), ...xy(g, k)]), shared });
  }
  return out;
}

// As sites, for generate.mjs to place.
const pushCells = (g, tiles, typeAt, extra = {}) => { for (const q of cellGroups(g, tiles, typeAt)) g.sites.push({ ...q, ...extra }); };

// Placed now, all or none (for designers that retry a layout).
function placeCells(g, s, tiles, typeAt) {
  const before = g.camps.length;
  for (const q of cellGroups(g, tiles, typeAt)) if (!tryGroup(g, q.cells, s, q.shared)) { g.camps.length = before; return false; }
  return true;
}

// A 4-connected tile path along a polyline (a diagonal step also takes the orthogonal tile).
function pathTiles(pts) {
  const out = [], seen = new Set();
  let px = null, py = null;
  const add = (x, y) => { if (!seen.has(`${x},${y}`)) { seen.add(`${x},${y}`); out.push([x, y]); } };
  for (let s = 0; s + 1 < pts.length; s++) {
    const n = Math.max(1, Math.ceil(dist(pts[s], pts[s + 1]) * 3));
    for (let k = 0; k <= n; k++) {
      const [fx, fy] = lerp(pts[s], pts[s + 1], k / n), x = Math.round(fx), y = Math.round(fy);
      if (x === px && y === py) continue;
      if (px !== null && x !== px && y !== py) add(x, py);
      add(x, y);
      px = x; py = y;
    }
  }
  return out;
}

// n cells grown 4-connected from (0, 0); `compact` rejects most growth with a single neighbour.
function growBlob(rng, n, compact = 0.6) {
  const cells = [[0, 0]], seen = new Set(['0,0']);
  for (let guard = 0; cells.length < n && guard < n * 200; guard++) {
    const [cx, cy] = rng.choice(cells), [dx, dy] = rng.choice(N4), x = cx + dx, y = cy + dy;
    if (seen.has(`${x},${y}`) || (N4.filter(([ex, ey]) => seen.has(`${x + ex},${y + ey}`)).length < 2 && rng.chance(compact))) continue;
    seen.add(`${x},${y}`); cells.push([x, y]);
  }
  return cells;
}

// Edge-connected components of the tiles matching `pred`.
function components(g, pred) {
  const seen = new Uint8Array(g.t.length), out = [];
  for (let i = 0; i < g.t.length; i++) {
    if (seen[i] || !pred(i)) continue;
    const c = [i];
    seen[i] = 1;
    for (let h = 0; h < c.length; h++) {
      const [x, y] = xy(g, c[h]);
      for (const [dx, dy] of N4) { const k = (y + dy) * g.W + x + dx; if (g.in(x + dx, y + dy) && !seen[k] && pred(k)) { seen[k] = 1; c.push(k); } }
    }
    out.push(c);
  }
  return out;
}

// Light cover on open ground: wall, bush and pond prefabs, bush clumps, sometimes a pond.
function backdrop(g, rng, { where = () => true, n = null } = {}) {
  const m = Math.min(g.W, g.H);
  scatterPrefabs(g, rng, n ?? rng.int(2, Math.max(2, Math.round(m / 6))), { gap: 6, where, kinds: { [WALL]: 3, [BUSH]: 1, [HOLE]: 0.4 } });
  clumps(g, rng, rng.int(2, 6), [3, 8], { where });
  if (rng.chance(0.35)) for (let k = rng.int(1, 2); k > 0; k--) {
    const p = [rng.int(4, g.W - 5), rng.int(4, g.H - 5)];
    if (where(...p) && cheb(p, spawnCentre(g)) > 8 && cheb(p, mirrorPt(g, spawnCentre(g))) > 8) blob(g, rng, p, rng.uniform(1.5, 3.2), 0.2, HOLE, [GROUND]);
  }
}

// The usual objectives: a home farm, altars by altarPlan, a treasure and a few mid-map groups.
function usualSites(g, rng, s, { altars = true, home = 8, mids = [1, 3], treasure = 0.5 } = {}) {
  const S = spawnCentre(g), C = centre(g);
  site(g, lerp(S, C, 0.2), home, tier(rng, s, 'home'), { required: true, home: true });
  if (altars) altarPlan(g, rng, S, C);
  if (rng.chance(treasure)) site(g, lerp(C, S, 0.12), 7, tier(rng, s, 'treasure'));
  for (let k = rng.int(...mids); k > 0; k--) site(g, lerp(S, C, rng.uniform(0.3, 0.8)).map((v, i) => v + rng.uniform(-0.3, 0.3) * (i ? g.H : g.W)), 7, tier(rng, s, 'mid'));
}

// ---- lattices ------------------------------------------------------------------------------
// Interior line positions along an axis of n tiles, mirrored onto themselves: n - 1 = 2o + k c.
// `odd` keeps a line off the middle, where a 2-thick line could not be its own mirror.
function axisLines(n, c, odd) {
  // The first cell size near c whose margins fit within a cell.
  let best = null;
  for (const cc of [c, c + 1, c - 1, c + 2, c - 2].filter(v => v >= 4)) {
    let k = Math.floor((n - 1) / cc);
    while (k >= 3 && ((n - 1 - k * cc) % 2 || (odd && k % 2 === 0))) k--;
    if (k < 3) continue;
    best = { o: n - 1 - k * cc, cc, k };
    if (best.o <= cc) break;
  }
  if (!best || best.o > 2 * best.cc) throw new GenFail('no lattice fits');
  const { o, cc, k } = best;
  return { cells: k, lines: Array.from({ length: k - 1 }, (_, j) => o / 2 + (j + 1) * cc) };
}

// A 2-thick line grows away from the middle, so it and its mirror coincide.
const thick = (p, n, t) => t === 1 ? [p] : p < (n - 1) / 2 ? [p, p + 1] : [p - 1, p];

// Lines of `kind` on a symmetric grid of cells, opened along a spanning tree (with each edge its
// mirror) plus `braid` extra links. Open links are 'full' (the whole side: maze corridors) or a door
// of `doorW`; with doorP < 1 some tree links stay shut (cells reached only across a line). `alt`
// redraws a share of the shut sides in another kind.
function lattice(g, rng, { kind, t, cx, cy, open, doorW = [1, 2], doorP = 1, braid = 0, alt = null, altShare = 0 }) {
  const fx = g.sym !== 'vertical', fy = g.sym !== 'horizontal', X = axisLines(g.W, cx, t > 1 && fx), Y = axisLines(g.H, cy, t > 1 && fy), nx = X.cells, ny = Y.cells;
  const xt = X.lines.map(p => thick(p, g.W, t)), yt = Y.lines.map(p => thick(p, g.H, t));
  for (const xs of xt) for (const x of xs) for (let y = 0; y < g.H; y++) g.t[y * g.W + x] = kind;
  for (const ys of yt) for (const y of ys) for (let x = 0; x < g.W; x++) g.t[y * g.W + x] = kind;
  const span = (ts, j, n, N) => [j ? Math.max(...ts[j - 1]) + 1 : 0, j < N - 1 ? Math.min(...ts[j]) - 1 : n - 1];
  const edges = [];
  for (let j = 0; j < ny; j++) for (let i = 0; i + 1 < nx; i++) edges.push({ a: j * nx + i, b: j * nx + i + 1, across: xt[i], along: span(yt, j, g.H, ny), vert: true, key: `x${i},${j}`, mkey: `x${fx ? nx - 2 - i : i},${fy ? ny - 1 - j : j}` });
  for (let j = 0; j + 1 < ny; j++) for (let i = 0; i < nx; i++) edges.push({ a: j * nx + i, b: (j + 1) * nx + i, across: yt[j], along: span(xt, i, g.W, nx), vert: false, key: `y${i},${j}`, mkey: `y${fx ? nx - 1 - i : i},${fy ? ny - 2 - j : j}` });
  const mcell = c => { const i = c % nx, j = (c - i) / nx; return (fy ? ny - 1 - j : j) * nx + (fx ? nx - 1 - i : i); };
  // A spanning tree over mirror orbits (an edge comes with its mirror, so a tree over cells would
  // open about every edge), then edge pairs joining what is still apart (the two halves).
  const uf = () => { const p = Array.from({ length: nx * ny }, (_, i) => i), f = i => p[i] === i ? i : (p[i] = f(p[i])); return { f, u: (a, b) => { p[f(a)] = f(b); } }; };
  const Q = uf(), F = uf(), orb = c => Math.min(c, mcell(c)), tree = new Set(), opened = new Set(), order = rng.shuffle(edges.slice());
  const take = e => { tree.add(e.key); tree.add(e.mkey); Q.u(orb(e.a), orb(e.b)); F.u(e.a, e.b); F.u(mcell(e.a), mcell(e.b)); };
  for (const e of order) if (Q.f(orb(e.a)) !== Q.f(orb(e.b))) take(e);
  for (const e of order) if (F.f(e.a) !== F.f(e.b)) take(e);
  let shut = false;
  // Decisions on the canonical edge of each mirror pair; g.set draws the mirror.
  for (const e of edges) {
    if (e.key > e.mkey) continue;
    if (tree.has(e.key) ? rng.chance(doorP) : rng.chance(braid)) opened.add(e.key);
    else shut ||= tree.has(e.key);
  }
  const tile = (e, u, v) => e.vert ? [u, v] : [v, u];
  for (const e of edges) {
    if (e.key > e.mkey) continue;
    const [lo, hi] = e.along;
    if (opened.has(e.key)) {
      const w = open === 'full' ? hi - lo + 1 : Math.min(hi - lo + 1, rng.int(...doorW)), at = lo + rng.int(0, hi - lo + 1 - w);
      for (const u of e.across) for (let v = at; v < at + w; v++) g.set(...tile(e, u, v), GROUND);
    } else if (alt !== null && rng.chance(altShare)) for (const u of e.across) for (let v = lo; v <= hi; v++) g.set(...tile(e, u, v), alt);
  }
  const lo = (ts, i) => i ? Math.max(...ts[i - 1]) + 1 : 0, hi = (ts, i, n, N) => i < N - 1 ? Math.min(...ts[i]) - 1 : n - 1;
  const cells = [];
  for (let j = 0; j < ny; j++) for (let i = 0; i < nx; i++) {
    const x0 = lo(xt, i), x1 = hi(xt, i, g.W, nx), y0 = lo(yt, j), y1 = hi(yt, j, g.H, ny);
    cells.push({ c: [(x0 + x1) / 2, (y0 + y1) / 2], r: Math.min(x1 - x0, y1 - y0) / 2 + 0.5 });
  }
  return { nx, ny, cells, shut };
}

// Three lattice styles. 'maze': corridors walled by holes (2 thick: a crystal crosses, a dash
// does not; 1 thick: a dash crosses), so you see and shoot an enemy who is far on foot. 'dash':
// hole lines one tile thick everywhere, with doors only on a spanning tree. 'thick': walls two
// thick (a crystal crosses, a dash cannot), doors on a spanning tree: a long walk around.
function latticeDesign(g, rng, s) {
  begin(g, GROUND);
  const style = s.lattice, m = Math.min(g.W, g.H), t = style === 'maze' ? s.line_thick : style === 'dash' ? 1 : 2, wide = style === 'maze' ? t - 1 : 0;
  const cx = s.cell + wide, cy = (rng.chance(0.6) ? s.cell : s.cell_y) + wide, partial = rng.chance(s.partial_doors ?? 0);
  const L = lattice(g, rng, {
    kind: style === 'thick' ? WALL : HOLE, t, cx, cy, open: style === 'maze' ? 'full' : 'door', doorW: style === 'thick' ? [1, 3] : [1, 2],
    doorP: partial ? rng.uniform(0.55, 0.9) : 1, braid: s.braid,
    alt: style === 'thick' ? HOLE : WALL, altShare: s.alt_share,
  });
  placeSpawn(g, rng, rng.weighted({ corner: 3, edge: 1.5, inset: 1 }), 1);
  const S = spawnCentre(g), C = centre(g), { w, h } = g.spawn;
  // A home plaza holds the home farm on foot even where tree doors stay shut.
  const plaza = Math.max(w, h) / 2 + (partial || style !== 'maze' ? rng.uniform(5, 7) : rng.uniform(2, 4));
  if (dist(S, mirrorPt(g, S)) < 2 * plaza + 4) throw new GenFail('home plazas overlap');
  disc(g, S, plaza, GROUND);
  if (rng.chance(0.5)) disc(g, C, rng.uniform(2, style === 'maze' ? 3.5 : Math.max(2.5, m / 10)), GROUND);
  if (style === 'maze' && rng.chance(0.5)) clumps(g, rng, rng.int(2, 6), [3, 6], { nearWall: 0.8 });
  if (L.shut) raise(g, t === 1 ? 'dash' : 'teleport');
  clearSpawn(g, 1);
  site(g, S, plaza + 2, tier(rng, s, 'home'), { required: true, home: true });
  altarPlan(g, rng, S, C, Math.max(5, Math.min(cx, cy)));
  if (rng.chance(0.6)) site(g, lerp(C, S, 0.1), Math.max(5, Math.min(cx, cy)), tier(rng, s, 'treasure'));
  const mids = L.cells.filter(c => onSideA(g, c.c) && dist(c.c, S) > plaza + 3);
  for (const c of rng.shuffle(mids).slice(0, rng.int(1, 3) + (m > 60))) site(g, c.c, c.r + 1, tier(rng, s, 'mid'));
}

// ---- leaky diagonals -----------------------------------------------------------------------
// A thin ring around P: one tile per row (or column) in each octant, so its diagonal runs leak
// (diagonal steps pass between diagonal blockers) while its flat runs seal. 'diamond': all leak.
function leakyRing(g, P, r, kind, shape, keep = () => true) {
  const fa = P[0] % 1 ? 0.5 : 0, fb = P[1] % 1 ? 0.5 : 0, snap = (v, f) => Math.round(v - f) + f, R = (z, f) => snap(Math.sqrt(Math.max(0, r * r - z * z)), f);
  const rd = Math.round(r) + ((fa + fb) % 1);
  for (let y = Math.floor(P[1] - r - 1); y <= P[1] + r + 1; y++) for (let x = Math.floor(P[0] - r - 1); x <= P[0] + r + 1; x++) {
    const a = Math.abs(x - P[0]), b = Math.abs(y - P[1]);
    const on = shape === 'diamond' ? Math.abs(a + b - rd) < 0.01 : (b <= a && Math.abs(a - R(b, fa)) < 0.01) || (a <= b && Math.abs(b - R(a, fb)) < 0.01);
    if (on && g.in(x, y) && keep(x, y)) put(g, x, y, kind);
  }
}

function leaky(g, rng, s) {
  begin(g, GROUND);
  placeSpawn(g, rng, rng.weighted({ corner: 3, edge: 2, inset: 1 }), 2);
  const C = centre(g), S = spawnCentre(g), S2 = mirrorPt(g, S), m = Math.min(g.W, g.H), sp = g.spawn;
  const kind = () => rng.chance(s.hole_share) ? HOLE : WALL, nearSpawn = (x, y) => [S, S2].some(p => cheb([x, y], p) < Math.max(sp.w, sp.h) / 2 + 3);
  const keep = (x, y) => !nearSpawn(x, y);
  let feats = ['crater', 'fences', 'checker', 'courtyard'].filter(f => rng.chance({ crater: 0.6, fences: 0.5, checker: 0.6, courtyard: 0.35 }[f]));
  if (feats.length < 2) feats = rng.shuffle(['crater', 'fences', 'checker', 'courtyard']).slice(0, 2);
  const fields = [];
  let crater = 0;
  if (feats.includes('crater')) {
    crater = m * rng.uniform(0.12, 0.26) + 2;
    const shape = rng.weighted({ circle: 3, diamond: 1 }), k = kind();
    if (rng.chance(0.4)) blob(g, rng, C, crater * rng.uniform(0.3, 0.5), 0.15, rng.chance(0.7) ? HOLE : WALL);
    leakyRing(g, C, crater, k, shape, keep);
    if (rng.chance(0.4) && crater + 5 < m / 2 - 2) leakyRing(g, C, crater + rng.uniform(3, 5), kind(), rng.chance(0.5) ? shape : 'circle', keep);
  }
  if (feats.includes('courtyard')) {
    const r = Math.max(sp.w, sp.h) / 2 + rng.uniform(4, 7);
    if (dist(S, S2) > 2 * r + 4) leakyRing(g, S, r, kind(), rng.weighted({ circle: 2, diamond: 1 }));
  }
  if (feats.includes('fences')) {
    // Pure diagonal fences across team A's half, roughly across the spawn-to-spawn line: only
    // corner-cutting crosses them (and a rare real gap).
    const u = [S2[0] - S[0], S2[1] - S[1]], d = Math.abs(u[0] + u[1]) < Math.abs(u[0] - u[1]) ? [1, 1] : [1, -1], k = kind();
    for (let n = rng.int(2, 4), j = 0; j < n; j++) {
      const q = lerp(S, C, rng.uniform(0.25, 0.85)).map(Math.round), gap = rng.chance(0.3) ? rng.int(-m, m) : null;
      for (let a = -2 * m; a <= 2 * m; a++) {
        const x = q[0] + d[0] * a, y = q[1] + d[1] * a;
        if (!g.in(x, y) || !onSideA(g, [x, y]) || dist([x, y], mirrorPt(g, [x, y])) < 3 || nearSpawn(x, y) || (gap !== null && Math.abs(a - gap) <= 1)) continue;
        put(g, x, y, k);
      }
    }
  }
  if (feats.includes('checker')) {
    const n = rng.int(1, 2) + (m > 60), ps = spots(g, rng, n, { gap: 12, spawnGap: 9, axisGap: 12 });
    if (rng.chance(0.3)) ps.push(C);
    for (const p of ps) {
      const r = p === C ? rng.uniform(3, 5) : rng.uniform(3, 6.5), k = kind(), par = rng.int(0, 1), sq = rng.chance(0.4);
      for (let y = Math.floor(p[1] - r); y <= p[1] + r; y++) for (let x = Math.floor(p[0] - r); x <= p[0] + r; x++) {
        if (!g.in(x, y) || (sq ? cheb([x, y], p) > r : dist([x, y], p) > r) || nearSpawn(x, y) || (p === C && g.mirror(y * g.W + x) < y * g.W + x)) continue;
        put(g, x, y, (x + y) % 2 === par ? k : GROUND);
      }
      fields.push({ p, r });
    }
  }
  // Ordinary sealed cover and bush, kept off the leaky features.
  scatterPrefabs(g, rng, rng.int(1, Math.max(1, Math.round(m / 9))), { gap: 6, kinds: { [WALL]: 3, [BUSH]: 1 } });
  clumps(g, rng, rng.int(2, 5), [3, 7]);
  clearSpawn(g);
  site(g, lerp(S, C, 0.2), 8, tier(rng, s, 'home'), { required: true, home: true });
  altarPlan(g, rng, S, C, crater ? Math.min(8, crater - 1) : 8);
  if (crater) { if (rng.chance(0.5)) g.sites.push({ shared: 'treasure' }); else site(g, lerp(C, S, 0.1), crater - 1, tier(rng, s, 'treasure')); }
  for (const f of fields.filter(f => f.p !== C)) site(g, f.p, f.r + 1, tier(rng, s, 'mid'));
  for (let k = rng.int(1, 2); k > 0; k--) site(g, lerp(S, C, rng.uniform(0.3, 0.8)).map((v, i) => v + rng.uniform(-0.3, 0.3) * (i ? g.H : g.W)), 7, tier(rng, s, 'mid'));
}

// ---- fog -----------------------------------------------------------------------------------
// One giant bush cluster: a blanket over all but the bases, a band across the middle, or a
// patchwork of noise. Rocks and ponds inside it, ground glades holding the objectives (camps and
// altars never sit on bush).
function fog(g, rng, s) {
  begin(g, GROUND);
  placeSpawn(g, rng, rng.weighted({ corner: 3, edge: 2, inset: 1 }), 2);
  const C = centre(g), S = spawnCentre(g), S2 = mirrorPt(g, S), m = Math.min(g.W, g.H), mode = s.fog, D = dist(S, S2);
  const n = valueNoise(rng, g.W, g.H, mode === 'patchwork' ? rng.uniform(8, 14) : rng.uniform(5, 12), 2), home = Math.max(g.spawn.w, g.spawn.h) / 2 + rng.uniform(3, 7), cover = s.fog_cover;
  const score = new Float32Array(g.t.length).fill(-Infinity), vals = [];
  for (let i = 0; i < g.t.length; i++) {
    if (i > g.mirror(i)) continue;
    const p = xy(g, i), dS = Math.min(dist(p, S), dist(p, S2));
    if (dS < home) continue;
    score[i] = mode === 'band' ? 0.6 * n[i] - 2.2 * Math.abs(dist(p, S) - dist(p, S2)) / D : mode === 'blanket' ? 0.35 * n[i] + 0.5 * Math.min(1, (dS - home) / 8) : n[i];
    vals.push(score[i]);
  }
  vals.sort((a, b) => b - a);
  const cut = vals[Math.min(vals.length - 1, Math.floor(cover * vals.length))];
  for (let i = 0; i < g.t.length; i++) if (score[i] >= cut) g.set(...xy(g, i), BUSH);
  const rocks = rng.int(1, Math.max(2, Math.round(m / 10)));
  for (let k = 0; k < rocks; k++) blob(g, rng, [rng.int(3, g.W - 4), rng.int(3, g.H - 4)], rng.uniform(0.8, 2.5), 0.25, rng.chance(0.7) ? WALL : HOLE, [BUSH]);
  // Glades: a contested one near the centre and a few on each side.
  const glades = [{ p: lerp(C, S, rng.uniform(0, 0.12)), r: rng.uniform(2.5, 4.5) }];
  for (const p of spots(g, rng, rng.int(2, 3) + (m > 60), { gap: 10, spawnGap: home + 4, axisGap: 8 })) glades.push({ p, r: rng.uniform(2.2, 4) });
  for (const gl of glades) blob(g, rng, gl.p, gl.r, 0.15, GROUND);
  // Keep the largest cluster (a glade or rock may have cut it) and small clumps outside it.
  const cl = components(g, i => g.t[i] === BUSH).sort((a, b) => b.length - a.length);
  for (const c of cl.slice(1)) if (g.t[c[0]] === BUSH && (c.length > 12 || rng.chance(0.5))) for (const i of c) g.set(...xy(g, i), GROUND);
  if (!cl.length || cl[0].length < 0.3 * g.walkable().reduce((a, v) => a + v, 0)) throw new GenFail('fog too thin');
  if (rng.chance(0.6)) scatterPrefabs(g, rng, rng.int(1, 4), { gap: 6, kinds: { [WALL]: 1 } });
  clearSpawn(g);
  site(g, lerp(S, C, 0.15), home + 3, tier(rng, s, 'home'), { required: true, home: true });
  const [mid, ...rest] = glades;
  site(g, mid.p, mid.r + 1, { altar: rng.chance(0.3) ? 'self' : true }, { required: true });
  if (rng.chance(0.4)) site(g, lerp(S, C, 0.3), 6, { altar: true });
  for (const gl of rest) site(g, gl.p, gl.r + 1, rng.chance(0.25) ? { altar: true } : tier(rng, s, rng.chance(0.25) ? 'treasure' : 'mid'));
  if (rng.chance(0.5)) site(g, mid.p, mid.r + 2, tier(rng, s, 'treasure'));
}

// ---- shrines: bush-ringed and moated altars ------------------------------------------------
// Every altar sits in a shrine. 'bush': ringed by bush (a grove, a hedge square, or a walled temple
// with bush gates), so tributes are hidden from outside. 'moat': on an islet behind a moat of holes
// one thick (a dash) or two thick, or of walls (a crystal only).
function shrines(g, rng, s) {
  begin(g, GROUND);
  placeSpawn(g, rng, rng.weighted({ corner: 3, edge: 2, inset: 1 }), 2);
  const C = centre(g), S = spawnCentre(g), m = Math.min(g.W, g.H), moat = s.shrine === 'moat', self = selfTile(g), list = [];
  const make = () => {
    if (!moat) { const style = rng.weighted({ grove: 2, hedge: 1.5, temple: 1.2 }); return { style, R: style === 'temple' ? 3 : style === 'hedge' ? rng.int(1, 2) + 1 : 3 }; }
    const lock = rng.weighted({ dash: 2, teleport: 1.5 }), ri = rng.chance(0.75) ? 1 : 2, mt = lock === 'dash' ? 1 : rng.int(1, 2), mk = lock === 'dash' ? HOLE : mt === 1 ? WALL : rng.weighted({ [WALL]: 1, [HOLE]: 1 }) | 0;
    return { lock, ri, mt, mk, R: ri + mt + 1 };
  };
  // A shrine's cleared box must miss the others, their mirrors, its own mirror and the spawns.
  const spawnTiles = [...g.spawnTiles(0), ...g.spawnTiles(1)].map(i => xy(g, i));
  const fits = q => q.p.every((v, k) => v - q.R - 1 >= 0 && v + q.R + 1 < (k ? g.H : g.W)) && (q.self || cheb(q.p, mirrorPt(g, q.p)) > 2 * q.R + 3)
    && spawnTiles.every(t => cheb(t, q.p) > q.R + 4) && list.every(o => [o.p, mirrorPt(g, o.p)].every(op => cheb(op, q.p) > q.R + o.R + 3));
  const add = q => { if (fits(q)) list.push(q); };
  const sh = make();
  if (self && rng.chance(0.45)) add({ ...sh, p: self, self: true });
  else {
    // The contested shrine, pulled towards A until it clears its mirror.
    let p = lerp(C, S, rng.uniform(0.05, 0.2)).map(Math.round);
    for (let k = 0; k < 40 && cheb(p, mirrorPt(g, p)) <= 2 * sh.R + 3; k++) p = lerp(p, S, 0.06).map(Math.round);
    add({ ...sh, p });
  }
  if (rng.chance(0.3)) add({ ...make(), p: lerp(S, C, rng.uniform(0.25, 0.35)).map(Math.round), home: true });
  for (const p of spots(g, rng, rng.int(0, 2) + (m > 64), { gap: 12, spawnGap: 10, axisGap: 14 })) add({ ...make(), p });
  if (!list.some(q => !q.home)) throw new GenFail('no shrine fits');
  const inShrine = (x, y) => list.some(q => cheb([x, y], q.p) <= q.R + 2 || cheb([x, y], mirrorPt(g, q.p)) <= q.R + 2);
  backdrop(g, rng, { where: (x, y) => !inShrine(x, y) });
  for (const q of list) {
    const [px, py] = q.p, ring = d => { const out = []; for (let dy = -d; dy <= d; dy++) for (let dx = -d; dx <= d; dx++) if (Math.max(Math.abs(dx), Math.abs(dy)) === d) out.push([px + dx, py + dy]); return out; };
    box(g, px - q.R - 1, py - q.R - 1, 2 * q.R + 3, 2 * q.R + 3, GROUND);
    if (moat) {
      for (let d = q.ri + 1; d <= q.ri + q.mt; d++) for (const [x, y] of ring(d)) put(g, x, y, q.mk);
      for (let d = 1; d <= q.ri; d++) for (const [x, y] of ring(d)) g.noCamp.add(y * g.W + x);
      for (const [x, y] of ring(q.R)) g.noCamp.add(y * g.W + x);
      g.intents.push({ at: q.p, r: q.ri + 0.5, min: q.lock });
      raise(g, q.lock);
    } else if (q.style === 'grove') disc(g, q.p, rng.uniform(1.5, 2.9), BUSH);
    else if (q.style === 'hedge') box(g, px - q.R + 1, py - q.R + 1, 2 * q.R - 1, 2 * q.R - 1, BUSH);
    else {
      for (const [x, y] of ring(1)) put(g, x, y, BUSH);
      const wall = ring(2), gates = new Set(rng.shuffle(wall.filter(([x, y]) => Math.abs(x - px) < 2 || Math.abs(y - py) < 2)).slice(0, rng.int(1, 3)).map(t => t.join()));
      for (const [x, y] of wall) put(g, x, y, gates.has(`${x},${y}`) ? BUSH : WALL);
    }
    put(g, px, py, GROUND);
  }
  clearSpawn(g);
  for (const q of list) site(g, q.p, 0.5, { altar: q.self ? 'self' : true }, { required: !q.home });
  usualSites(g, rng, s, { altars: false });
}

// ---- mega-groups ---------------------------------------------------------------------------
const PACKS = {
  wolves: () => ({ wolf: 8, elk: 1.5, gold_cluster: 1 }),
  herd: () => ({ elk: 3, wolf: 3, gem_cluster: 2 }),
  garden: () => ({ gem_cluster: 3, gold_cluster: 2, wolf: 0.5 }),
  gems: () => ({ gem_cluster: 1 }),
};

// One to two mega-groups (20-50 camps in one group) per side: a pack grown as a blob, a ring of
// camps around an altar (adjacent to it at radius 1), a snake along a walled corridor, a vault of
// clusters behind walls with doors (open or dash), and sometimes a ring around a central altar.
function mega(g, rng, s) {
  begin(g, GROUND);
  placeSpawn(g, rng, rng.weighted({ corner: 3, edge: 2, inset: 1 }), 2);
  const C = centre(g), S = spawnCentre(g), m = Math.min(g.W, g.H), self = selfTile(g);
  let budget = 100;
  const kinds = rng.shuffle(['pack', 'ring', 'snake', 'vault']).slice(0, m >= 56 ? 2 : 1), feats = [];
  const ps = spots(g, rng, kinds.length, { gap: 18, spawnGap: 12, axisGap: 16, margin: 5 });
  if (!ps.length) throw new GenFail('no room for a mega-group');
  kinds.slice(0, ps.length).forEach((kind, k) => feats.push({ kind, p: ps[k] }));
  const central = self && rng.chance(0.45) && m >= 40 ? { kind: 'cring', p: self } : null;
  // A snake's path must stay on the map, off the axis and away from the spawns; else a pack.
  const sp = g.spawn, far = ([x, y]) => Math.max(sp.x - x, x - sp.x - sp.w + 1, sp.y - y, y - sp.y - sp.h + 1) > 6;
  for (const f of feats.filter(f => f.kind === 'snake')) {
    const len = Math.min(budget, rng.int(20, 42)), half = len / 2.4;
    for (let k = 0; k < 12 && !f.cells; k++) {
      const ang = rng.uniform(0, 2 * Math.PI), a = [f.p[0] - Math.cos(ang) * half, f.p[1] - Math.sin(ang) * half], b = [f.p[0] + Math.cos(ang) * half, f.p[1] + Math.sin(ang) * half];
      f.pts = smooth(meander(rng, a, b, rng.uniform(0.04, 0.12), rng.uniform(0.6, 1.4)), 1);
      f.cells = pathTiles(f.pts).slice(0, len);
      if (f.cells.some(p => p[0] < 2 || p[1] < 2 || p[0] > g.W - 3 || p[1] > g.H - 3 || dist(p, mirrorPt(g, p)) < 4 || !far(p) || !far(mirrorPt(g, p)))) f.cells = null;
    }
    if (!f.cells) f.kind = 'pack';
  }
  const area = (x, y) => [...feats, ...(central ? [central] : [])].some(f => Math.min(dist([x, y], f.p), dist([x, y], mirrorPt(g, f.p))) < (f.kind === 'snake' ? 14 : 8));
  backdrop(g, rng, { where: (x, y) => !area(x, y) });
  const typer = pal => { const w = PACKS[pal](); return (x, y) => rng.weighted(w); };
  for (const [j, f] of feats.entries()) {
    const extra = { required: j === 0 };
    if (f.kind === 'pack') {
      const n = Math.min(budget, rng.int(20, 50)), cells = growBlob(rng, n, rng.uniform(0.3, 0.8)).map(([x, y]) => [f.p[0] + x, f.p[1] + y]);
      for (const [x, y] of cells) disc(g, [x, y], 1.5, GROUND);
      const pal = rng.weighted({ wolves: 3, herd: 2, garden: 1.5 }), boss = rng.chance(0.4) ? rng.int(0, cells.length - 1) : -1, type = typer(pal);
      pushCells(g, cells, (x, y, k) => k === boss ? 'golem' : type(x, y), extra);
      budget -= cells.length;
    } else if (f.kind === 'ring') {
      // One gate: a C of 21-35 camps, one group.
      const r = rng.int(1, 3), cells = ringCells(g, f.p, r, r < 3, [rng.uniform(0, 2 * Math.PI)], rng.int(1, 2));
      box(g, f.p[0] - r - 3, f.p[1] - r - 3, 2 * r + 7, 2 * r + 7, GROUND);
      site(g, f.p, 0.5, { altar: true }, extra);
      const type = rng.weighted({ alt: 2, wolves: 1.5, elk: 0.7, gems: 1 }), [t1, t2] = type === 'alt' ? rng.choice([['wolf', 'gem_cluster'], ['wolf', 'gold_cluster'], ['elk', 'gem_cluster']]) : [{ wolves: 'wolf', elk: 'elk', gems: 'gem_cluster' }[type], null];
      pushCells(g, cells, (x, y) => t2 && (x + y) % 2 ? t2 : t1, extra);
      budget -= cells.length;
    } else if (f.kind === 'snake') {
      const { pts, cells } = f;
      for (const [x, y] of cells) disc(g, [x, y], 2.5, GROUND);
      if (rng.chance(0.65)) for (const side of [1, -1]) {
        const off = side > 0 ? rng.uniform(3, 4) : rng.uniform(3, 4.5), wall = [];
        for (let k = 0; k <= 30; k++) { const { p, d } = along(pts, 0.08 + 0.84 * k / 30); wall.push([p[0] - d[1] * off * side, p[1] + d[0] * off * side]); }
        stroke(g, wall, 1, rng.chance(0.8) ? WALL : HOLE);
      }
      // Where the corridor bends tight its wall may cross the snake: the snake wins.
      for (const [x, y] of cells) disc(g, [x, y], 1.5, GROUND);
      const pal = rng.weighted({ garden: 2, wolves: 1, gems: 1 }), type = typer(pal);
      pushCells(g, cells, type, extra);
      budget -= cells.length;
    } else {
      const w = rng.int(4, 7), h = Math.max(4, Math.min(7, Math.round(rng.int(20, 49) / w))), x0 = Math.round(f.p[0] - w / 2), y0 = Math.round(f.p[1] - h / 2), cells = [];
      box(g, x0 - 2, y0 - 2, w + 4, h + 4, WALL);
      box(g, x0 - 1, y0 - 1, w + 2, h + 2, GROUND);
      for (let y = y0; y < y0 + h; y++) for (let x = x0; x < x0 + w; x++) cells.push([x, y]);
      // Doors in the wall ring: open, or a hole across it (a dash).
      const doors = rng.int(2, 3), dash = rng.chance(0.45), sides = rng.shuffle([0, 1, 2, 3]).slice(0, doors);
      for (const sd of sides) {
        const horiz = sd < 2, len = horiz ? w : h, o = rng.int(0, Math.max(0, len - 2)), fixed = sd === 0 ? y0 - 2 : sd === 1 ? y0 + h + 1 : sd === 2 ? x0 - 2 : x0 + w + 1;
        for (let q = o; q < o + 2; q++) put(g, horiz ? x0 + q : fixed, horiz ? fixed : y0 + q, dash ? HOLE : GROUND);
      }
      if (dash) raise(g, 'dash');
      const pal = rng.weighted({ gems: 3, garden: 1.5 }), type = typer(pal), boss = rng.chance(0.3);
      pushCells(g, cells, (x, y) => boss && x === x0 + (w >> 1) && y === y0 + (h >> 1) ? 'golem' : type(x, y), extra);
      budget -= cells.length;
    }
  }
  if (central) {
    // A gate on the axis is its own mirror: one shared C. Under rotation a gate and its mirror
    // make two groups, so the ring is doubled.
    const f = central, rot = g.sym === 'rotational', r = rng.int(2, 3), side = rng.chance(0.5) ? 1 : -1;
    const a = g.sym === 'horizontal' ? side * Math.PI / 2 : g.sym === 'vertical' ? (side > 0 ? 0 : Math.PI) : rng.uniform(0, Math.PI);
    const cells = ringCells(g, f.p, r, rot, rot ? [a, a + Math.PI] : [a], rng.int(1, 2));
    box(g, f.p[0] - r - 2, f.p[1] - r - 2, 2 * r + 5, 2 * r + 5, GROUND);
    site(g, f.p, 0.5, { altar: 'self' }, { required: true });
    const [t1, t2] = rng.choice([['wolf', 'gem_cluster'], ['elk', 'gem_cluster'], ['gem_cluster', 'gem_cluster'], ['wolf', 'wolf']]);
    pushCells(g, cells, (x, y) => (x + y) % 2 ? t2 : t1);
  }
  clearSpawn(g);
  // Altars at exact spots clear of the groups: with camp_altar_gap 0, placeSites would put a site
  // altar on a camp tile.
  const busy = g.sites.filter(q => q.cells).flatMap(q => q.cells.flatMap(([, x, y]) => [[x, y], mirrorPt(g, [x, y])]));
  const spawnTiles = [...g.spawnTiles(0), ...g.spawnTiles(1)].map(i => xy(g, i));
  const spotNear = p => {
    const near = [];
    for (let y = Math.floor(p[1] - 8); y <= p[1] + 8; y++) for (let x = Math.floor(p[0] - 8); x <= p[0] + 8; x++) if (g.in(x, y)) near.push([dist([x, y], p) + rng.uniform(0, 2), x, y]);
    const hit = near.sort((a, b) => a[0] - b[0]).find(([, x, y]) => g.get(x, y) === GROUND && cheb([x, y], mirrorPt(g, [x, y])) > 4 && busy.every(t => cheb(t, [x, y]) > 2) && spawnTiles.every(t => cheb(t, [x, y]) > 4));
    return hit ? hit.slice(1) : null;
  };
  for (const [p, req] of [[central ? null : lerp(C, S, rng.uniform(0, 0.12)), true], [rng.chance(0.35) ? lerp(S, C, 0.3) : null, false]]) {
    if (!p) continue;
    const at = spotNear(p);
    if (at) site(g, at, 0.5, { altar: true }, { required: req });
    else if (req) throw new GenFail('no altar spot');
  }
  usualSites(g, rng, s, { altars: false, mids: [0, 2], treasure: 0.3 });
}

// A square ring of camps at Chebyshev r around P (and r + 1 if `two`), open at the gate angles
// (so what it guards is reached past the live camps). A tile is left open when it or its mirror
// falls in a gate, so a ring around a self-mirrored tile stays symmetric.
function ringCells(g, P, r, two, gates, gw) {
  const out = [], on = ([x, y]) => { const d = cheb([x, y], P); return d === r || (two && d === r + 1); };
  const gate = ([x, y]) => on([x, y]) && gates.some(a => Math.abs(((Math.atan2(y - P[1], x - P[0]) - a) % (2 * Math.PI) + 3 * Math.PI) % (2 * Math.PI) - Math.PI) < (gw / 2 + 0.3) / cheb([x, y], P));
  for (let dy = -r - 1; dy <= r + 1; dy++) for (let dx = -r - 1; dx <= r + 1; dx++) {
    const p = [P[0] + dx, P[1] + dy];
    if (on(p) && !gate(p) && !gate(mirrorPt(g, p))) out.push(p);
  }
  return out;
}

// ---- altar clusters ------------------------------------------------------------------------
// Adjacent altars (pairs, lines, L's, 2x2 blocks) with camps hugging them, like the ladder's
// contest, great-wall and yellow-brick-road: on each side and often straddling the centre.
const FORMS = { pair: [[0, 0], [1, 0]], diag: [[0, 0], [1, 1]], line: [[0, 0], [1, 0], [2, 0]], ell: [[0, 0], [1, 0], [0, 1]], block: [[0, 0], [1, 0], [0, 1], [1, 1]], stack: [[0, 0], [0, 1]] };

function altarClusters(g, rng, s) {
  begin(g, GROUND);
  placeSpawn(g, rng, rng.weighted({ corner: 3, edge: 2, inset: 1 }), 2);
  const C = centre(g), S = spawnCentre(g), m = Math.min(g.W, g.H), clusters = [];
  if (rng.chance(0.65)) {
    // Straddling the centre: one or two tiles near it and their mirrors (adjacent when the axis
    // runs between two tiles).
    const base = C.map(v => Math.floor(v)), tiles = [base], [mx, my] = mirrorPt(g, base);
    if ((mx === base[0] && my === base[1]) || cheb(base, [mx, my]) > 1 || rng.chance(0.4)) tiles.push(rng.choice([[1, 0], [0, 1], [1, 1], [1, -1]]).map((d, k) => base[k] + d));
    clusters.push({ tiles: tiles.flatMap(t => [t, mirrorPt(g, t)]), p: C, central: true });
  }
  const n = rng.int(1, 2) + (m > 64) - (clusters.length && m < 44 ? 1 : 0);
  for (const p of spots(g, rng, Math.max(1, n), { gap: 14, spawnGap: 9, axisGap: 10, margin: 4 })) {
    const f = FORMS[rng.weighted({ pair: 2, diag: 1, line: 1, ell: 1.2, block: 1.2, stack: 1 })];
    clusters.push({ tiles: f.map(([dx, dy]) => [p[0] + dx, p[1] + dy]), p });
  }
  const near = (x, y) => clusters.some(c => [c.p, mirrorPt(g, c.p)].some(q => cheb([x, y], q) < 7));
  backdrop(g, rng, { where: (x, y) => !near(x, y) });
  if (rng.chance(0.4)) for (const c of clusters.filter(c => !c.central)) {
    // A pen: bush or wall around the cluster at distance 3, open on one or two sides.
    const xs = c.tiles.map(t => t[0]), ys = c.tiles.map(t => t[1]), x0 = Math.min(...xs) - 3, y0 = Math.min(...ys) - 3, x1 = Math.max(...xs) + 3, y1 = Math.max(...ys) + 3, k = rng.chance(0.6) ? BUSH : WALL, skip = rng.int(0, 3);
    for (let y = y0; y <= y1; y++) for (let x = x0; x <= x1; x++) if ((x === x0 && skip !== 0) || (x === x1 && skip !== 1) || (y === y0 && skip !== 2) || (y === y1 && skip !== 3)) put(g, x, y, k);
  }
  clearSpawn(g);
  const placed = [];
  for (const c of clusters) {
    const saved = c.tiles.map(([x, y]) => g.in(x, y) ? g.get(x, y) : null);
    if (saved.includes(null)) continue;
    for (const [x, y] of c.tiles) box(g, x - 1, y - 1, 3, 3, GROUND, [WALL, HOLE, BUSH]);
    for (const [x, y] of c.tiles) g.set(x, y, ALTAR);
    if (!stillConnected(g)) { c.tiles.forEach(([x, y], k) => g.set(x, y, saved[k])); continue; }
    placed.push(c);
  }
  if (!placed.length) throw new GenFail('no altar cluster');
  // Camps hugging each cluster: an arc of its collar (the tiles next to it), tried at a few angles
  // (an arc may box an altar in).
  for (const c of placed) {
    if (!rng.chance(0.85)) continue;
    const alt = new Set(c.tiles.map(([x, y]) => y * g.W + x)), collar = new Map();
    for (const i of alt) for (let dy = -1; dy <= 1; dy++) for (let dx = -1; dx <= 1; dx++) { const [x, y] = xy(g, i); if (g.in(x + dx, y + dy) && !alt.has((y + dy) * g.W + x + dx)) collar.set(`${x + dx},${y + dy}`, [x + dx, y + dy]); }
    const cx = c.tiles.reduce((a, t) => a + t[0], 0) / c.tiles.length, cy = c.tiles.reduce((a, t) => a + t[1], 0) / c.tiles.length;
    const [t1, t2] = rng.choice([['gem_cluster', 'gem_cluster'], ['wolf', 'gem_cluster'], ['gold_cluster', 'gem_cluster'], ['elk', 'gem_cluster'], ['wolf', 'wolf']]);
    for (let k = 0; k < 6; k++) {
      const a0 = rng.uniform(0, 2 * Math.PI), span = rng.uniform(0.3, 0.6) * 2 * Math.PI;
      const arc = [...collar.values()].filter(([x, y]) => (((Math.atan2(y - cy, x - cx) - a0) % (2 * Math.PI)) + 2 * Math.PI) % (2 * Math.PI) < span);
      if (arc.length && placeCells(g, s, arc, (x, y) => (x + y) % 2 ? t2 : t1)) break;
    }
  }
  usualSites(g, rng, s, { altars: false, mids: [1, 3] });
}

// ---- fuel stress ---------------------------------------------------------------------------
// Mostly gold, so the ~500 camps hold a few hundred gems a side and games run long enough to stress fuel.
const FUEL_MIX = { wolf: 1.5, gem: 0.6, gold: 4, wolf_pair: 0.8, elk_gold: 1, gems: 0.4, gold_row: 3, golem_gold: 0.3, scen_gold_patch: 1.5, scen_gold_carpet: 0.6 };

// A near-maximal map: 90-100 tiles a side, dense cover, dozens of bush clusters, many altars and
// close to the map format's 250 stored camps (each mirrored: about 500 in play), to expose per-turn
// blow-ups. Camps are placed here (a count cap the filler lacks); altars through sites after them.
function fuel(g, rng, s) {
  begin(g, GROUND);
  placeSpawn(g, rng, rng.weighted({ corner: 3, edge: 2, inset: 1 }), 2);
  const S = spawnCentre(g), m = Math.min(g.W, g.H);
  scatterPrefabs(g, rng, rng.int(Math.round(m / 3), Math.round(m / 2)), { gap: 5, kinds: { [WALL]: 3, [BUSH]: 1, [HOLE]: 0.5 } });
  for (let k = rng.int(2, 6); k > 0; k--) {
    const a = [rng.int(3, g.W - 4), rng.int(3, g.H - 4)], b = [a[0] + rng.int(-14, 14), a[1] + rng.int(-14, 14)];
    if (dist(a, S) > 10 && dist(b, S) > 10 && dist(a, mirrorPt(g, a)) > 6) stroke(g, meander(rng, a, b, 0.1), 1, rng.chance(0.7) ? WALL : HOLE);
  }
  for (let k = rng.int(0, 3); k > 0; k--) leakyRing(g, [rng.int(8, g.W - 9), rng.int(8, g.H - 9)], rng.uniform(3, 6), WALL, 'circle', (x, y) => cheb([x, y], S) > 8 && cheb([x, y], mirrorPt(g, S)) > 8);
  clumps(g, rng, rng.int(30, 45), [3, 10], { nearWall: 0.4 });
  clearSpawn(g);
  // Camps: up to `want` stored (the format holds 250; a self-mirrored one counts once).
  const want = s.camp_target;
  for (let tries = 0; g.camps.length < want - 1 && tries < 3000; tries++) {
    const tpl = GEN_TEMPLATES[rng.weighted(FUEL_MIX)](rng);
    if (tpl.length > want - g.camps.length) continue;
    const x = rng.int(1, g.W - 2), y = rng.int(1, g.H - 2);
    if (g.get(x, y) !== GROUND) continue;
    tryGroup(g, tpl.map(([t, dx, dy]) => [t, x + dx, y + dy]), s);
  }
  const self = selfTile(g);
  if (self) site(g, self, 3, { altar: 'self' });
  for (let k = s.altar_sites; k > 0; k--) site(g, [rng.uniform(4, g.W - 5), rng.uniform(4, g.H - 5)], 6, { altar: true }, { required: k === 1 });
}

// ---- templates -----------------------------------------------------------------------------
// Carpets: 15-30 cardinally connected clusters, one group (a rectangle, blob, strip or ring).
function carpetCells(rng, n) {
  const shape = rng.weighted({ rect: 3, blob: 2, strip: 1, frame: 1 });
  if (shape === 'rect') { const w = rng.int(3, 6), h = Math.max(3, Math.round(n / w)); return Array.from({ length: w * h }, (_, k) => [k % w, Math.floor(k / w)]); }
  if (shape === 'strip') { const w = rng.int(1, 2), l = Math.round(n / w); return Array.from({ length: w * l }, (_, k) => [k % l, Math.floor(k / l)]); }
  if (shape === 'frame') { const a = rng.int(4, 7), b = Math.max(4, Math.min(8, Math.round(n / 2 - a + 2))), out = []; for (let y = 0; y < b; y++) for (let x = 0; x < a; x++) if ((x === 0 || y === 0 || x === a - 1 || y === b - 1) && !(y === 0 && x === a >> 1)) out.push([x, y]); return out; }
  return growBlob(rng, n, 0.7);
}

const carpet = types => rng => { const ts = types(rng); return carpetCells(rng, rng.int(15, 30)).map(([x, y]) => [ts(x, y), x, y]); };
const mixType = rng => { const p = rng.int(0, 2); return (x, y) => p === 0 ? 'gem_cluster' : p === 1 ? 'gold_cluster' : (x + y) % 2 ? 'gold_cluster' : 'gem_cluster'; };

export const TEMPLATES = {
  scen_carpet: rng => carpet(mixType)(rng),
  scen_gem_carpet: carpet(() => () => 'gem_cluster'),
  scen_gold_carpet: carpet(() => () => 'gold_cluster'),
  scen_gold_patch: rng => carpetCells(rng, rng.int(5, 9)).slice(0, 9).map(([x, y]) => ['gold_cluster', x, y]),
  scen_gem_patch: rng => growBlob(rng, rng.int(4, 7), 0.6).map(([x, y]) => ['gem_cluster', x, y]),
  scen_pack: rng => { const w = PACKS[rng.weighted({ wolves: 3, herd: 2 })](); return growBlob(rng, rng.int(12, 24), 0.5).map(([x, y]) => [rng.weighted(w), x, y]); },
};

// ---- economies -----------------------------------------------------------------------------
export const CAMP_MODES = {
  // Gems (no gold: clusters only) at home; gold only in the contested middle and on the axis.
  'scen-gold-centre': { camp_mix: { gems: 3, gem: 2, scen_gem_patch: 1 }, camp_bias: 'near', contested_groups: [3, 6], contested_mix: { gold_row: 2, gold: 2, scen_gold_patch: 1.5, golem_gold: 0.4 }, shared_gold: [1, 3], monoliths: 0, shared_camp: 0 },
  // Richest at home, poorest in the middle: only altars draw fights.
  'scen-turtle': { camp_bias: 'near', camp_mix: { elk_gems: 3, golem_gems: 1.5, gems: 2, elk_gold: 1.5, gold_gems: 1, golem_gold: 1, elk_pair: 1 }, contested_groups: [1, 3], contested_mix: { wolf: 2, gold: 2, gem: 1 }, monoliths: { 0: 3, 1: 1 }, monolith_band: 'near', shared_camp: 0 },
  'scen-carpets': { camp_mix: { scen_carpet: 2, scen_gem_carpet: 1.5, scen_gold_carpet: 1, gold: 1, wolf: 1, elk_gold: 0.5 }, groups: [3, 6], scale_counts: false, monoliths: 0, shared_camp: 0 },
};

// ---- presets -------------------------------------------------------------------------------
// The designed mix without 'poor' (its 80-gem cap cannot hold a mega-group or an altar collar).
const RICHER = { standard: 5, rich: 1, 'gold-rich': 0.7, 'gold-poor': 0.7, jackpot: 0.8, golem: 0.4, sparse: 0.4, dense: 0.4 };
const designed = (doc, design, spec = {}) => ({ doc, design, designed: true, ...spec });
const exotic = (doc, spec = {}) => ({ doc, exotic: true, ...spec });

export const PRESETS = {
  'hole-maze': designed('A maze whose corridors are walled by holes (mostly two thick: a crystal crosses, a dash does not): you see and shoot an enemy who is far away on foot', 'scen-lattice',
    { altars: 0, lattice: 'maze', line_thick: { 1: 1, 2: 3 }, cell: [4, 6], cell_y: [4, 6], braid: [0, 0.12], alt_share: [0, 0.15], size: [30, 90], groups: [2, 6] }),
  'dash-lattice': designed('Hole lines one tile thick on a grid, walked through only at doors on a spanning tree (sometimes fewer): dashers cut straight across', 'scen-lattice',
    { altars: 0, lattice: 'dash', cell: [5, 8], cell_y: [5, 8], braid: [0, 0.05], alt_share: [0, 0.2], partial_doors: 0.45, size: [30, 90], groups: [2, 6] }),
  'wall-lattice': designed('Walls two thick on a grid with doors on a spanning tree: a crystal crosses a wall, a dash cannot, walking goes the long way round', 'scen-lattice',
    { altars: 0, lattice: 'thick', cell: [6, 10], cell_y: [6, 10], braid: [0, 0.12], alt_share: [0, 0.2], partial_doors: 0.3, size: [36, 100], groups: [2, 6] }),
  'leaky-diagonals': designed('Unsealed diagonal wall and hole lines: leaky craters, fences and courtyards and checkerboard fields that only corner-cutting passes (like crater)', 'scen-leaky',
    { altars: 0, hole_share: [0, 0.4], size: [30, 96], groups: [2, 7] }),
  'fog-field': designed('One giant bush cluster (a blanket, a middle band or a noise patchwork) with rocks, ponds and ground glades holding the objectives', 'scen-fog',
    { altars: 0, fog: { blanket: 2, band: 1.5, patchwork: 1 }, fog_cover: [0.55, 0.85], size: [30, 90], groups: [2, 7], max_bush_clusters: 20 }),
  'shrouded-altars': designed('Every altar ringed by bush (a grove, a hedge square or a walled temple with bush gates): tributes are hidden from outside', 'scen-shrines',
    { shrine: 'bush', size: [30, 90], altars: 0, groups: [2, 7] }),
  'moated-altars': designed('Every altar on an islet behind a moat: holes one thick (a dash), or holes or walls two thick and walls one thick (a crystal)', 'scen-shrines',
    { shrine: 'moat', size: [32, 90], altars: 0, groups: [2, 7] }),
  'mega-groups': designed('Single camp groups of 20-50: grown packs, rings of camps around (even adjacent to) an altar, snakes along corridors, walled vaults of clusters', 'scen-mega',
    { size: [36, 96], camp_altar_gap: 0, group_gap: { 0: 1, 1: 1 }, groups: [1, 4], scale_counts: false, altars: 0, camp_mode: RICHER }),
  'altar-clusters': designed('Adjacent altars (pairs, lines, L shapes, 2x2 blocks, across the centre) with camps hugging them', 'scen-altar-clusters',
    { size: [30, 90], camp_altar_gap: 0, altar_crowd: 0, group_gap: { 0: 1, 1: 1 }, altars: 0, groups: [2, 7], camp_mode: RICHER }),
  'fuel-stress': designed('90-100 tiles a side with dense cover, dozens of bush clusters, many altars and close to the format\'s 250 stored camps (about 500 in play): per-turn fuel blow-ups', 'scen-fuel',
    { size: [90, 100], aspect: { square: 3, wide: 1 }, picks: { 4: 1, 5: 3 }, camp_target: [215, 245], altar_sites: [5, 9], groups: 0, scale_counts: false, altars: 0, max_bush_clusters: 90, camp_spawn_gap: 4, group_gap: { 0: 1, 1: 2 }, camp_mode: 'standard' }),
  'gold-centre': exotic('Gem clusters only at home, gold only in the contested middle and on the axis: shopping means fighting (gem-centre reversed)', { camp_mode: 'scen-gold-centre' }),
  turtle: exotic('Richest camps at home, poorest in the middle (a reversed value gradient): only the central altars draw fights', { camp_mode: 'scen-turtle', altar_mode: { central: 3, single: 1, contested: 1 } }),
  'far-altars': exotic('Altars at least 8-13 tiles from every camp: long carries with gems at risk', { size: [50, 100], camp_altar_gap: [7, 12], altars: [1, 2], altar_mode: { corners: 2, central: 2, own: 1, spread: 1 }, scale_counts: false, groups: [4, 12], shared_camp: 0, camp_mode: { standard: 4, golem: 1, sparse: 1, dense: 0.6, clusters: 0.5, monsters: 0.5 } }),
  'cluster-carpets': exotic('Carpets of 15-30 gem or gold clusters (one group each), plus a few small groups', { camp_mode: 'scen-carpets', terrain: { open: 3, scatter: 2, pillars: 0.5, city: 0.4 }, wall_density: [0.01, 0.06], shape: { none: 5, circle: 1, diamond: 0.5 } }),
};

export const DESIGNS = { 'scen-lattice': latticeDesign, 'scen-leaky': leaky, 'scen-fog': fog, 'scen-shrines': shrines, 'scen-mega': mega, 'scen-altar-clusters': altarClusters, 'scen-fuel': fuel };
