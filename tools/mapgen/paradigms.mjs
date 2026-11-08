// Layout paradigms (2026-11-08, `suite --mix paradigms`): layouts the ladder's map makers could plausibly draw but the
// ladder-like presets do not, each under calibration 3's ladder rates for everything else (size, symmetry, picks,
// spawns, altars, camp groups, gems and gold). TERRAIN entries draw before the spawn is placed (generate.mjs
// symmetrises them); POST_SPAWN entries draw after it, around the spawns, with g.set so they stay symmetric.
import { BUSH, GROUND, HOLE, N4, WALL, valueNoise } from './grid.mjs';

const KINDS = { wall: WALL, hole: HOLE, bush: BUSH, ground: GROUND };
const put = (g, x, y, k) => { if (g.in(x, y)) g.t[y * g.W + x] = k; };
const rectDist = (s, x, y) => Math.max(Math.max(s.x - x, 0, x - (s.x + s.w - 1)), Math.max(s.y - y, 0, y - (s.y + s.h - 1)));
const blockedShare = g => g.t.reduce((n, k) => n + (k === WALL || k === HOLE), 0) / g.t.length;
// Angular distance in [0, pi].
const adiff = (a, b) => Math.abs(((a - b + 3 * Math.PI) % (2 * Math.PI)) - Math.PI);
// The map's centre and half its shorter side, in tiles.
const frame = g => ({ cx: (g.W - 1) / 2, cy: (g.H - 1) / 2, half: Math.min(g.W, g.H) / 2 });
const METRIC = { circle: (dx, dy) => Math.hypot(dx, dy), square: (dx, dy) => Math.max(Math.abs(dx), Math.abs(dy)), diamond: (dx, dy) => (Math.abs(dx) + Math.abs(dy)) / 1.4 };

// A ring (distance band [r, r + t) under the metric) with gates: gate tiles take `gate` (ground, bush, or a hole a dash
// crosses). `gates` are angles; a gate spans gw tiles of arc.
function ring(g, F, metric, r, t, kind, gates, gw, gate = GROUND) {
  for (let y = 0; y < g.H; y++) for (let x = 0; x < g.W; x++) {
    const dx = (x - F.cx), dy = (y - F.cy), d = metric(dx, dy);
    if (d < r || d >= r + t) continue;
    const a = Math.atan2(dy, dx);
    put(g, x, y, gates.some(b => adiff(a, b) * Math.max(r, 1) < gw / 2) ? gate : kind);
  }
}

// Sprinkled short wall and bush bits for texture in otherwise open ground (a light `scatter`).
function sprinkle(g, rng, share, ok = () => true) {
  const target = share * g.W * g.H;
  for (let n = 0, guard = 0; n < target && guard < 4000; guard++) {
    const x = rng.int(0, g.W - 1), y = rng.int(0, g.H - 1), k = rng.chance(0.7) ? WALL : BUSH, len = rng.int(2, 5), horiz = rng.chance(0.5);
    for (let j = 0; j < len; j++) { const u = horiz ? x + j : x, v = horiz ? y : y + j; if (g.in(u, v) && g.t[v * g.W + u] === GROUND && ok(u, v)) { put(g, u, v, k); n++; } }
  }
}

// ---- pre-spawn terrains ----------------------------------------------------------------------
// Ring road: an impassable core (a lake, a mesa or a walled jungle), a road around it, and an outer wall ring with
// gates (sometimes two). Lake cores may have a plaza in the middle on bridges.
function ringroad(g, rng) {
  const F = frame(g), metric = METRIC[rng.weighted({ circle: 3, square: 1.5, diamond: 1 })], core = rng.weighted({ hole: 3, wall: 2, bush: 0.8 });
  const rc = Math.max(2.5, rng.uniform(0.18, 0.36) * F.half), road = rng.int(3, Math.max(3, Math.min(8, Math.round(0.18 * F.half))));
  for (let y = 0; y < g.H; y++) for (let x = 0; x < g.W; x++) {
    const d = metric((x - F.cx), (y - F.cy));
    if (d < rc) put(g, x, y, core === 'bush' ? (d >= rc - 1 ? WALL : BUSH) : KINDS[core]);
  }
  if (core === 'bush') ring(g, F, metric, rc - 1, 1, WALL, Array.from({ length: rng.int(2, 4) }, () => rng.uniform(-Math.PI, Math.PI)), 3, BUSH);
  if (core === 'hole' && rc >= 5 && rng.chance(0.4)) {
    const plaza = rng.uniform(1.5, Math.min(4, rc / 2)), spokes = rng.int(2, 4), ph = rng.uniform(0, Math.PI);
    for (let y = 0; y < g.H; y++) for (let x = 0; x < g.W; x++) {
      const dx = (x - F.cx), dy = (y - F.cy), d = metric(dx, dy);
      if (d >= rc) continue;
      const a = Math.atan2(dy, dx), spoke = Array.from({ length: spokes }, (_, k) => ph + k * 2 * Math.PI / spokes).some(b => adiff(a, b) * Math.max(d, 1) < 1.1);
      if (d < plaza || spoke) put(g, x, y, GROUND);
    }
  }
  let r = rc + road;
  for (let k = 0, n = rng.chance(0.3) ? 2 : rng.chance(0.85) ? 1 : 0; k < n && r < 0.88 * F.half; k++) {
    const t = rng.int(1, 2), gates = Array.from({ length: rng.int(2, 5) }, () => rng.uniform(-Math.PI, Math.PI));
    ring(g, F, metric, r, t, rng.chance(0.8) ? WALL : HOLE, gates, rng.int(3, 5), rng.chance(0.25) ? BUSH : GROUND);
    r += t + rng.int(4, 8);
  }
  sprinkle(g, rng, rng.uniform(0, 0.025), (x, y) => metric((x - F.cx), (y - F.cy)) > r);
}

// Colosseum: a walled arena in the middle (gates open, bush or dash-crossable), cover inside, open ground around.
function colosseum(g, rng) {
  const F = frame(g), metric = METRIC[rng.weighted({ circle: 3, square: 1, diamond: 1 })];
  const ra = Math.max(6, rng.uniform(0.32, 0.55) * F.half), t = rng.int(1, 3), ng = rng.int(2, 6), ph = rng.uniform(0, 2 * Math.PI);
  const gates = Array.from({ length: ng }, (_, k) => ph + k * 2 * Math.PI / ng + rng.uniform(-0.3, 0.3));
  ring(g, F, metric, ra, t, WALL, gates, rng.int(3, 5), rng.weighted({ ground: 3, bush: 1, hole: 0.6 }) === 'ground' ? GROUND : rng.chance(0.6) ? BUSH : HOLE);
  // Cover: pillars, bush clumps or low walls inside, and sometimes a pit in the middle.
  const cover = rng.int(2, Math.max(3, Math.round(ra / 2.5))), ck = rng.weighted({ wall: 2, bush: 2, mixed: 1.5 });
  for (let k = 0; k < cover; k++) {
    const a = rng.uniform(0, 2 * Math.PI), d = rng.uniform(0.3, 0.75) * ra, x = Math.round(F.cx + d * Math.cos(a)), y = Math.round(F.cy + d * Math.sin(a));
    const kind = ck === 'mixed' ? (rng.chance(0.5) ? WALL : BUSH) : KINDS[ck], w = rng.int(1, kind === BUSH ? 3 : 2), h = rng.int(1, kind === BUSH ? 3 : 2);
    for (let j = 0; j < h; j++) for (let i = 0; i < w; i++) put(g, x + i, y + j, kind);
  }
  if (rng.chance(0.3)) { const r = rng.uniform(1, 2.2); for (let y = 0; y < g.H; y++) for (let x = 0; x < g.W; x++) if (metric((x - F.cx), (y - F.cy)) < r) put(g, x, y, HOLE); }
  sprinkle(g, rng, rng.uniform(0.01, 0.04), (x, y) => metric((x - F.cx), (y - F.cy)) > ra + t + 1);
}

// Isles: hole channels along one to three noise contours split the map into islands; connect() bridges them on foot
// where nothing else does, so the rest of each channel is a dash (1-2 wide) or a detour.
function isles(g, rng) {
  const n = valueNoise(rng, g.W, g.H, rng.uniform(9, 18), 3), sorted = Float32Array.from(n).sort(), levels = rng.int(1, 3);
  for (let k = 0; k < levels; k++) {
    const L = sorted[Math.floor(sorted.length * rng.uniform(0.25, 0.75))], wide = rng.weighted({ 0: 3, 1: 2, 2: 1 }), edge = new Uint8Array(n.length);
    for (let y = 0; y < g.H; y++) for (let x = 0; x < g.W; x++) {
      const i = y * g.W + x;
      if (n[i] <= L) continue;
      for (const [dx, dy] of N4) if (g.in(x + dx, y + dy) && n[(y + dy) * g.W + x + dx] <= L) { edge[i] = 1; break; }
    }
    for (let i = 0; i < n.length; i++) if (edge[i]) { const x = i % g.W, y = (i - x) / g.W; for (let dy = 0; dy <= +wide; dy++) for (let dx = 0; dx <= +wide; dx++) put(g, x + dx, y + dy, HOLE); }
    if (blockedShare(g) > 0.22) break;
  }
  // Fords: short walked crossings now and then, so not every island is a single bridge away.
  for (let k = rng.int(0, Math.round(g.W * g.H / 500)); k > 0; k--) {
    const x = rng.int(2, g.W - 3), y = rng.int(2, g.H - 3);
    if (g.t[y * g.W + x] !== HOLE) continue;
    const r = rng.int(1, 2);
    for (let dy = -r; dy <= r; dy++) for (let dx = -r; dx <= r; dx++) if (g.in(x + dx, y + dy) && g.t[(y + dy) * g.W + x + dx] === HOLE) put(g, x + dx, y + dy, GROUND);
  }
}

// Choke web: warped Voronoi regions behind thick ridges of wall (some of hole), each pair of neighbours joined by
// passes of 1-5 tiles, or not at all, or merged into one region: an irregular network of chokes.
function chokeweb(g, rng) {
  const size = rng.uniform(11, 20), n = Math.max(5, Math.round(g.W * g.H / (size * size))), warp = rng.uniform(0, 6), noise = valueNoise(rng, g.W, g.H, rng.uniform(6, 12), 2);
  const sites = Array.from({ length: n }, () => [rng.uniform(0, g.W), rng.uniform(0, g.H)]), label = new Int32Array(g.W * g.H);
  for (let y = 0; y < g.H; y++) for (let x = 0; x < g.W; x++) {
    let best = 0, bd = Infinity;
    for (let k = 0; k < n; k++) { const d = Math.hypot(sites[k][0] - x, sites[k][1] - y) + warp * noise[y * g.W + x] * (k % 2 ? 1 : -1); if (d < bd) { bd = d; best = k; } }
    label[y * g.W + x] = best;
  }
  const edges = new Map(), thick = rng.weighted({ 1: 1, 2: 3, 3: 1 });
  for (let y = 0; y < g.H; y++) for (let x = 0; x < g.W; x++) {
    const a = label[y * g.W + x];
    for (const [dx, dy] of [[1, 0], [0, 1], [1, 1], [1, -1]]) {
      if (!g.in(x + dx, y + dy)) continue;
      const b = label[(y + dy) * g.W + x + dx];
      if (a === b) continue;
      const key = Math.min(a, b) * n + Math.max(a, b);
      if (!edges.has(key)) edges.set(key, { tiles: [], kind: rng.chance(0.25) ? HOLE : WALL, open: rng.chance(0.22), passes: +rng.weighted({ 0: 1, 1: 4, 2: 2 }), width: () => +rng.weighted({ 1: 1, 2: 2, 3: 3, 4: 2, 5: 1 }) });
      edges.get(key).tiles.push([x, y]);
    }
  }
  for (const e of edges.values()) {
    if (e.open) continue;
    for (const [x, y] of e.tiles) for (let dy = 0; dy < thick; dy++) for (let dx = 0; dx < thick; dx++) put(g, x + dx, y + dy, e.kind);
  }
  for (const e of edges.values()) {
    if (e.open) continue;
    for (let p = 0; p < e.passes; p++) {
      const [x, y] = rng.choice(e.tiles), w = e.width(), r = Math.floor(w / 2);
      for (let dy = -r - 1; dy <= r + thick; dy++) for (let dx = -r - 1; dx <= r + thick; dx++) if (g.in(x + dx, y + dy) && g.t[(y + dy) * g.W + x + dx] === e.kind && Math.max(Math.abs(dx), Math.abs(dy)) <= r + thick) put(g, x + dx, y + dy, GROUND);
    }
  }
}

// Corridor grid: long parallel walls 4-7 apart (like the ladder's corridors) with doorways (open, bush or a hole a
// dash crosses), cut across by up to 2 open avenues, with open lobbies at the ends. Almost half are serpentine:
// walls across the way between the spawns, one door each at alternate ends.
function corridors(g, rng) {
  const serp = rng.chance(0.45), alongX = serp ? (g.sym === 'vertical' || (g.sym === 'rotational' && g.H > g.W)) : rng.chance(0.5);
  const len = alongX ? g.W : g.H, across = alongX ? g.H : g.W, p = rng.int(4, 7), thick = rng.chance(0.8) ? 1 : 2;
  const margin = rng.int(2, Math.max(2, Math.round(0.15 * len))), off = rng.int(1, p), doorKind = () => KINDS[rng.weighted({ ground: 3, hole: 1, bush: 1.2 })];
  const at = (a, b) => alongX ? [a, b] : [b, a];
  const avenues = serp ? [] : Array.from({ length: rng.int(0, 2) }, () => [rng.int(margin, len - margin - 1), rng.int(2, 4)]);
  for (let c = off, k = 0; c < across - 1; c += p, k++) {
    const every = rng.int(9, 24), dw = rng.int(2, 3), ph = rng.int(0, every), dk = doorKind(), end = k % 2 ? len - margin - dw - rng.int(0, 3) : margin + rng.int(0, 3);
    for (let a = margin; a < len - margin; a++) {
      const door = serp ? a >= end && a < end + dw : (a + ph) % every < dw, avenue = avenues.some(([q, w]) => a >= q && a < q + w);
      if (avenue) continue;
      for (let t = 0; t < thick; t++) { const [x, y] = at(a, c + t); put(g, x, y, door ? dk : WALL); }
    }
  }
}

// Stones: a field of small, evenly spaced obstacles (posts, blocks, pluses, ells) of wall, hole or bush, like the
// ladder's standing-stones or orchard.
function stones(g, rng) {
  const d = rng.int(3, 6), target = rng.uniform(0.05, 0.13) * g.W * g.H, single = rng.chance(0.4) ? rng.weighted({ wall: 3, hole: 1, bush: 1 }) : null;
  const shapes = { dot: [[0, 0]], domino: [[0, 0], [1, 0]], block: [[0, 0], [1, 0], [0, 1], [1, 1]], plus: [[0, 0], [1, 0], [-1, 0], [0, 1], [0, -1]], ell: [[0, 0], [1, 0], [0, 1]] };
  const shapeW = { dot: rng.uniform(0.5, 3), domino: rng.uniform(0.5, 2), block: rng.uniform(0.5, 2.5), plus: rng.uniform(0, 1), ell: rng.uniform(0, 1.5) };
  let placed = 0;
  for (let guard = 0; placed < target && guard < 6000; guard++) {
    const x = rng.int(0, g.W - 1), y = rng.int(0, g.H - 1), cells = shapes[rng.weighted(shapeW)].map(([a, b]) => rng.chance(0.5) ? [x + a, y + b] : [x + b, y + a]);
    if (cells.some(([u, v]) => !g.in(u, v))) continue;
    let ok = true;
    for (const [u, v] of cells) for (let dy = -d + 1; ok && dy < d; dy++) for (let dx = -d + 1; dx < d; dx++) if (g.in(u + dx, v + dy) && g.t[(v + dy) * g.W + u + dx] !== GROUND) { ok = false; break; }
    if (!ok) continue;
    const kind = KINDS[single ?? rng.weighted({ wall: 3, hole: 1.2, bush: 1 })];
    for (const [u, v] of cells) put(g, u, v, kind);
    placed += cells.length;
  }
}

// Mesa field: open ground with a few big obstacles (wall mesas, hole craters), some with a bush rim.
function mesas(g, rng) {
  const count = Math.max(4, Math.min(26, Math.round(g.W * g.H / rng.uniform(220, 520)))), cap = rng.uniform(0.1, 0.22);
  for (let k = 0; k < count && blockedShare(g) < cap; k++) {
    const r = rng.uniform(2.2, Math.max(3, Math.min(7.5, Math.min(g.W, g.H) / 7))), cx = rng.uniform(0, g.W - 1), cy = rng.uniform(0, g.H - 1);
    const kind = rng.chance(0.75) ? WALL : HOLE, rim = rng.chance(0.3) ? 1 : 0, sx = rng.uniform(0.7, 1.4), ph = rng.uniform(0, 2 * Math.PI), lobes = rng.int(2, 5), amp = rng.uniform(0, 0.3);
    for (let y = Math.floor(cy - r - 3); y <= cy + r + 3; y++) for (let x = Math.floor(cx - r * 1.5 - 3); x <= cx + r * 1.5 + 3; x++) {
      if (!g.in(x, y)) continue;
      const dx = (x - cx) / sx, dy = (y - cy) * sx, rr = r * (1 + amp * Math.cos(lobes * Math.atan2(dy, dx) + ph)), d = Math.hypot(dx, dy);
      if (d < rr) put(g, x, y, kind);
      else if (rim && d < rr + rim && g.t[y * g.W + x] === GROUND) put(g, x, y, BUSH);
    }
  }
}

// Contour lines: walls (some lines holes, which a dash crosses) along several levels of a smooth noise field, broken
// by gaps: terraces and waves that wind the walk.
function contours(g, rng) {
  const n = valueNoise(rng, g.W, g.H, rng.uniform(12, 28), 2), sorted = Float32Array.from(n).sort(), k = rng.int(3, 7), gapN = valueNoise(rng, g.W, g.H, rng.uniform(3, 7), 1);
  const gq = Float32Array.from(gapN).sort()[Math.floor(gapN.length * rng.uniform(0.8, 0.93))];
  for (let l = 1; l <= k; l++) {
    const L = sorted[Math.floor(sorted.length * l / (k + 1))], kind = rng.chance(0.25) ? HOLE : WALL;
    for (let y = 0; y < g.H; y++) for (let x = 0; x < g.W; x++) {
      const i = y * g.W + x;
      if (n[i] <= L || gapN[i] > gq) continue;
      if (N4.some(([dx, dy]) => g.in(x + dx, y + dy) && n[(y + dy) * g.W + x + dx] <= L)) put(g, x, y, kind);
    }
  }
}

// Compartments: two or three rooms a side behind thick walls, with one or two gates per wall (open, bush or dash), and
// now and then a plaza at the middle that every room opens onto.
function compartments(g, rng) {
  const nx = rng.int(2, 4), ny = rng.int(2, 3), t = rng.int(2, 3), plaza = rng.chance(0.45) ? rng.uniform(0.12, 0.22) * Math.min(g.W, g.H) : 0, F = frame(g);
  const cuts = (len, k) => Array.from({ length: k - 1 }, (_, j) => Math.round(len * (j + 1) / k + rng.uniform(-0.08, 0.08) * len));
  const xs = cuts(g.W, nx), ys = cuts(g.H, ny), gateKind = () => KINDS[rng.weighted({ ground: 4, bush: 1.2, hole: 0.8 })];
  const wall = (vertical, c, from, to) => {
    const gates = Array.from({ length: rng.int(1, 2) }, () => [rng.int(from + 2, Math.max(from + 2, to - 6)), rng.int(3, 4), gateKind()]);
    for (let a = from; a < to; a++) {
      const gate = gates.find(([q, w]) => a >= q && a < q + w);
      for (let k = 0; k < t; k++) { const [x, y] = vertical ? [c + k, a] : [a, c + k]; put(g, x, y, gate ? gate[2] : WALL); }
    }
  };
  // Each wall runs between its neighbouring cuts, so every room has its own gates.
  const bx = [0, ...xs, g.W], by = [0, ...ys, g.H];
  for (const c of xs) for (let j = 0; j + 1 < by.length; j++) wall(true, c, by[j], by[j + 1]);
  for (const c of ys) for (let j = 0; j + 1 < bx.length; j++) wall(false, c, bx[j], bx[j + 1]);
  if (plaza) for (let y = 0; y < g.H; y++) for (let x = 0; x < g.W; x++) if (Math.hypot((x - F.cx), (y - F.cy)) < plaza && g.t[y * g.W + x] === WALL) put(g, x, y, GROUND);
  sprinkle(g, rng, rng.uniform(0, 0.03));
}

// Under rotation a shared group fits only at the centre: when the spec wants one, the layout leaves the middle 7x7
// open (a plaza in a ring road's core, a ford in a river), as the ladder-like terrains mostly do by chance.
function clearCentre(g, s) {
  if (!(s.shared_groups > 0 && g.sym === 'rotational')) return;
  const cx = (g.W - 1) / 2, cy = (g.H - 1) / 2;
  for (let y = Math.ceil(cy - 3); y <= cy + 3; y++) for (let x = Math.ceil(cx - 3); x <= cx + 3; x++) if (g.in(x, y)) g.set(x, y, GROUND);
}
const withCentre = fns => Object.fromEntries(Object.entries(fns).map(([k, f]) => [k, (g, rng, s) => { f(g, rng, s); clearCentre(g, s); }]));

export const TERRAIN = withCentre({ ringroad, colosseum, isles, chokeweb, corridors, stones, mesas, contours, compartments });

// ---- post-spawn structures ------------------------------------------------------------------
// The spawns' centres, their midpoint, the unit vector from A to B (u) and its normal (n), and A's distance to B.
function axis(g) {
  const s = g.spawn, ax = s.x + (s.w - 1) / 2, ay = s.y + (s.h - 1) / 2, [bx0, by0] = g.mirrorXY(s.x, s.y), [bx1, by1] = g.mirrorXY(s.x + s.w - 1, s.y + s.h - 1);
  const bx = (bx0 + bx1) / 2, by = (by0 + by1) / 2, L = Math.max(1, Math.hypot(bx - ax, by - ay)), u = [(bx - ax) / L, (by - ay) / L];
  return { ax, ay, bx, by, mx: (ax + bx) / 2, my: (ay + by) / 2, L, u, n: [-u[1], u[0]] };
}
// Tiles near either spawn (the spawn and 2 around it) are never drawn on.
const nearSpawn = (g, x, y, gap = 2) => { if (rectDist(g.spawn, x, y) <= gap) return true; const [mx, my] = g.mirrorXY(x, y); return rectDist(g.spawn, mx, my) <= gap; };
const setFree = (g, x, y, k) => { if (g.in(x, y) && !nearSpawn(g, x, y)) g.set(x, y, k); };

// Braided lanes: 2-4 lanes from spawn to spawn between long dividers (wall, hole, or a bush jungle with a wall
// spine), each divider bent and broken by 0-2 crossings, sometimes walled flanks outside the outer lanes. Under a
// mirror the divider and its mirror image cross: braids.
function lanes(g, rng) {
  const A = axis(g), K = rng.int(2, 4), lw = rng.int(5, 9), d = rng.int(2, 4), end = rng.uniform(0.12, 0.28) * A.L, span = Math.max(A.L / 2 - end, 4);
  const dividers = Array.from({ length: K - 1 }, (_, k) => ({ t: (k - (K - 2) / 2) * (lw + d), amp: rng.uniform(0, 0.5) * lw, per: rng.uniform(0.6, 1.6) * A.L, ph: rng.uniform(0, 2 * Math.PI),
    kind: rng.weighted({ wall: 3, hole: 1.2, jungle: 1 }), gaps: Array.from({ length: rng.int(0, 2) }, () => [rng.uniform(-span, span), rng.int(3, 5)]) }));
  const flank = rng.chance(0.45) ? { t: ((K - 1) / 2) * (lw + d) + lw / 2 + d, th: rng.int(2, 3) } : null;
  for (let y = 0; y < g.H; y++) for (let x = 0; x < g.W; x++) {
    const px = x - A.mx, py = y - A.my, s = px * A.u[0] + py * A.u[1], t = px * A.n[0] + py * A.n[1];
    if (Math.abs(s) > span) continue;
    for (const dv of dividers) {
      const c = dv.t + dv.amp * Math.sin(2 * Math.PI * s / dv.per + dv.ph);
      if (Math.abs(t - c) >= d / 2 + (dv.kind === 'jungle' ? 1 : 0) || dv.gaps.some(([q, w]) => Math.abs(s - q) < w / 2)) continue;
      setFree(g, x, y, dv.kind === 'jungle' ? (Math.abs(t - c) < 0.6 ? WALL : BUSH) : KINDS[dv.kind]);
    }
    if (flank && Math.abs(Math.abs(t) - flank.t) < flank.th / 2 && Math.abs(s) < span * 0.9) setFree(g, x, y, WALL);
  }
}

// Home keeps: a walled courtyard (square or round) around each spawn with 2-3 gates facing the map, and on half the maps
// a second wall outside it with its gates turned away from the first's, so the way out winds.
function keeps(g, rng) {
  const A = axis(g), s = g.spawn, metric = rng.chance(0.6) ? 'rect' : 'round', maxR = Math.max(3, Math.min(8, Math.floor(0.16 * A.L)));
  const rings = [{ r: rng.int(3, maxR), t: rng.int(1, 2) }];
  if (rng.chance(0.6)) rings.push({ r: rings[0].r + rings[0].t + rng.int(3, 6), t: rng.int(1, 2) });
  const toward = Math.atan2(A.my - A.ay, A.mx - A.ax);
  let turn = 0;
  for (const rg of rings) {
    const n = rng.int(2, 3), spread = rng.uniform(0.5, 1.2), gates = Array.from({ length: n }, (_, k) => toward + turn + (k - (n - 1) / 2) * spread), gw = rng.int(2, 3);
    const kind = rng.chance(0.85) ? WALL : HOLE, gate = rng.chance(0.2) ? BUSH : GROUND;
    for (let y = 0; y < g.H; y++) for (let x = 0; x < g.W; x++) {
      const d = metric === 'rect' ? rectDist(s, x, y) : Math.hypot(x - A.ax, y - A.ay) - Math.max(s.w, s.h) / 2;
      if (d < rg.r || d >= rg.r + rg.t) continue;
      // Only on team A's side of the middle: the mirror keeps are B's.
      if ((x - A.ax) * A.u[0] + (y - A.ay) * A.u[1] > A.L / 2 - 2) continue;
      const a = Math.atan2(y - A.ay, x - A.ax);
      setFree(g, x, y, gates.some(b => adiff(a, b) * (rg.r + 1) < gw / 2) ? gate : kind);
    }
    turn += rng.choice([-1, 1]) * rng.uniform(0.7, 1.4);
  }
}

// Meander river: a hole river (2-5 wide) across the middle between the spawns, bending; walked bridges and narrows a
// dash crosses; bushy banks on some maps. Under a mirror the river and its image braid.
function river(g, rng) {
  const A = axis(g), w = rng.int(2, 5), amp = rng.uniform(0.04, 0.16) * A.L, per = rng.uniform(0.5, 1.2) * Math.max(g.W, g.H), banks = rng.chance(0.3) ? rng.int(1, 2) : 0;
  const cross = Array.from({ length: rng.int(2, 4) }, () => [rng.uniform(-0.45, 0.45) * Math.max(g.W, g.H), rng.int(2, 4), rng.chance(0.35)]);
  const pond = rng.chance(0.25) ? rng.uniform(3, Math.max(3.5, Math.min(7, A.L / 8))) : 0;
  for (let y = 0; y < g.H; y++) for (let x = 0; x < g.W; x++) {
    const px = x - A.mx, py = y - A.my, s = px * A.u[0] + py * A.u[1], t = px * A.n[0] + py * A.n[1];
    // An odd bend, so the centre point lies on the river and rotation maps it onto itself.
    const off = amp * Math.sin(2 * Math.PI * t / per) + amp * 0.4 * Math.sin(6 * Math.PI * t / per), dist = Math.abs(s - off);
    const c = cross.find(([q, cw]) => Math.abs(t - q) < cw / 2);
    if (pond && Math.hypot(px, py) < pond) setFree(g, x, y, HOLE);
    else if (dist < w / 2) setFree(g, x, y, c ? (c[2] && dist < 1 ? HOLE : GROUND) : HOLE);
    else if (banks && dist < w / 2 + banks && g.t[y * g.W + x] === GROUND && !c) setFree(g, x, y, BUSH);
  }
}

export const POST_SPAWN = withCentre({ lanes, keeps, river });

// ---- presets -----------------------------------------------------------------------------------
// The ladder's long sides (generate.mjs's LADDER_LONG, per side), sides under 50 weighted 1.35x: the layouts fail more
// attempts on small maps, which would otherwise leave the suite short of them.
const LONG = { '28-29': 4, '30-31': 15, '32-34': 4, '35-39': 10, '40-44': 12, '45-49': 10, '50-54': 20, '55-59': 2, '60-64': 9, '65-69': 3, '70-74': 5, '75-79': 2, '80-84': 12, '85-89': 4, '90-94': 10, '95-99': 3, '100-100': 5 };
const SIZE = {};
for (const [band, w] of Object.entries(LONG)) { const [a, b] = band.split('-').map(Number); for (let n = a; n <= b; n++) SIZE[n] = w / (b - a + 1) * (n < 50 ? 1.35 : 1); }
// Calibration 3's ladder rates (DEFAULTS_V3) for everything but the layout: winding barriers on 40% of maps, not 50%
// (none where the layout is the route), and fewer lakes and pits on top.
const P = (doc, spec) => ({ doc, size: SIZE, aspect: 'ladder', picks: 'area', groups: [3, 16], winding: 0.4, holes: { none: 4.5, lakes: 2.4, pits: 0.4 }, ...spec });
export const PRESETS = {
  'ring-road': P('An impassable core (lake, mesa or walled jungle; lakes sometimes with a bridged plaza) ringed by a road and gated walls', { terrain: 'ringroad', holes: { none: 1 }, winding: 0 }),
  colosseum: P('A walled arena in the middle with cover inside and open, bushy ground around it', { terrain: 'colosseum', winding: 0.15 }),
  isles: P('Islands between hole channels along noise contours, bridged on foot where needed, otherwise dash or detour', { terrain: 'isles', holes: 'none' }),
  'choke-web': P('Warped Voronoi regions behind thick ridges, joined by passes of 1-5 tiles: an irregular choke network', { terrain: 'chokeweb', holes: { none: 1 }, unnarrow: 0.3, winding: 0.15 }),
  corridors: P('Long parallel corridors 3-6 wide with doorways (open, bush or dash), cut by open avenues; almost half serpentine', { terrain: 'corridors', holes: { none: 1 }, winding: 0 }),
  stones: P('A field of small evenly spaced posts, blocks and pluses of wall, hole or bush', { terrain: 'stones' }),
  'mesa-field': P('Open ground with a few big wall mesas and hole craters, some bush-rimmed', { terrain: 'mesas' }),
  contours: P('Wall and hole lines along noise contours, broken by gaps: terraces and waves', { terrain: 'contours', holes: { none: 1 }, winding: 0 }),
  compartments: P('Two or three big rooms a side behind thick gated walls, sometimes around a central plaza', { terrain: 'compartments', winding: 0.15 }),
  'braided-lanes': P('Two to four lanes from spawn to spawn between bent, broken dividers (braids under a mirror)', { terrain: { open: 2, scatter: 1 }, wall_density: [0.01, 0.04], post_spawn: 'lanes', winding: 0, spawn_place: { corner: 2, edge: 3, inset: 1 } }),
  'home-keeps': P('A gated courtyard around each spawn, often nested in a second wall with turned gates', { terrain: { open: 1, scatter: 2 }, wall_density: [0.01, 0.05], post_spawn: 'keeps', spawn_place: { corner: 2, edge: 2, inset: 3 } }),
  'meander-river': P('A bending hole river across the middle with bridges, dash narrows, bushy banks and sometimes a pond', { terrain: { open: 1, scatter: 2 }, wall_density: [0.01, 0.06], holes: 'none', post_spawn: 'river' }),
};
