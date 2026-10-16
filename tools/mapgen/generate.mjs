import { ALTAR, BUSH, CAMP, GROUND, Grid, HOLE, N4, WALL, makeRng, valueNoise } from './grid.mjs';

export class GenFail extends Error {}

const cheb = (ax, ay, bx, by) => Math.max(Math.abs(ax - bx), Math.abs(ay - by));
const rectDist = (s, x, y) => Math.max(Math.max(s.x - x, 0, x - (s.x + s.w - 1)), Math.max(s.y - y, 0, y - (s.y + s.h - 1)));

// ---- terrain ------------------------------------------------------------------------------
function line(g, x0, y0, dx, dy, len, kind, thick = 1) {
  for (let k = 0; k < len; k++) for (let t = 0; t < thick; t++) {
    const x = x0 + dx * k + (dy ? t : 0), y = y0 + dy * k + (dx && !dy ? t : 0);
    if (g.in(x, y)) g.t[g.idx(x, y)] = kind;
  }
}

function rect(g, x0, y0, w, h, kind, only) {
  for (let y = y0; y < y0 + h; y++) for (let x = x0; x < x0 + w; x++)
    if (g.in(x, y) && (only === undefined || g.t[g.idx(x, y)] === only)) g.t[g.idx(x, y)] = kind;
}

const count = (g, kind) => g.t.reduce((n, k) => n + (k === kind), 0);

function scatter(g, rng, s) {
  const target = s.wall_density * g.W * g.H, maxLen = Math.max(4, Math.round(Math.min(g.W, g.H) * s.wall_length));
  for (let guard = 0; count(g, WALL) < target && guard < 5000; guard++) {
    const x = rng.int(0, g.W - 1), y = rng.int(0, g.H - 1), thick = rng.chance(0.25) ? 2 : 1;
    const shape = rng.weighted({ line: 5, diagonal: 1, ell: 3, block: 2, plus: 1 });
    const len = rng.int(3, maxLen), dir = rng.choice([[1, 0], [0, 1]]);
    if (shape === 'line') line(g, x, y, ...dir, len, WALL, thick);
    else if (shape === 'diagonal') line(g, x, y, 1, rng.choice([1, -1]), len, WALL, 1);
    else if (shape === 'ell') { line(g, x, y, 1, 0, len, WALL, thick); line(g, x, y, 0, rng.choice([1, -1]), rng.int(3, maxLen), WALL, thick); }
    else if (shape === 'block') rect(g, x, y, rng.int(2, 4), rng.int(2, 4), WALL);
    else { line(g, x - (len >> 1), y, 1, 0, len, WALL); line(g, x, y - (len >> 1), 0, 1, len, WALL); }
  }
}

function caves(g, rng, s) {
  const { W, H } = g;
  let a = Uint8Array.from({ length: W * H }, () => rng.chance(s.cave_fill));
  for (let it = 0; it < s.cave_iters; it++) {
    const b = new Uint8Array(W * H);
    for (let y = 0; y < H; y++) for (let x = 0; x < W; x++) {
      let n = 0;
      for (let dy = -1; dy <= 1; dy++) for (let dx = -1; dx <= 1; dx++) {
        if (!dx && !dy) continue;
        const nx = x + dx, ny = y + dy;
        n += nx < 0 || ny < 0 || nx >= W || ny >= H ? 1 : a[ny * W + nx];
      }
      b[y * W + x] = a[y * W + x] ? n >= 4 : n >= 5;
    }
    a = b;
  }
  for (let i = 0; i < a.length; i++) if (a[i]) g.t[i] = WALL;
}

// Recursive division: rooms split by 1-thick walls with wide doors.
function rooms(g, rng, s) {
  const split = (x0, y0, w, h, depth) => {
    const horizontalCut = w === h ? rng.chance(0.5) : h > w;
    const span = horizontalCut ? h : w;
    if (span < 2 * s.room_size + 1 || depth > 12) return;
    const at = rng.int(s.room_size, span - s.room_size - 1), len = horizontalCut ? w : h;
    const doors = len > 3 * s.room_size ? 2 : 1, gaps = [];
    for (let d = 0; d < doors; d++) gaps.push(rng.int(0, Math.max(0, len - s.door_width)));
    for (let k = 0; k < len; k++) {
      if (gaps.some(o => k >= o && k < o + s.door_width)) continue;
      const x = horizontalCut ? x0 + k : x0 + at, y = horizontalCut ? y0 + at : y0 + k;
      g.t[g.idx(x, y)] = WALL;
    }
    if (horizontalCut) { split(x0, y0, w, at, depth + 1); split(x0, y0 + at + 1, w, h - at - 1, depth + 1); }
    else { split(x0, y0, at, h, depth + 1); split(x0 + at + 1, y0, w - at - 1, h, depth + 1); }
  };
  const m = s.room_margin;
  split(m, m, g.W - 2 * m, g.H - 2 * m, 0);
}

// Strips of wall or hole along the long axis, broken by crossings.
function lanes(g, rng, s) {
  const along = g.W >= g.H, len = along ? g.W : g.H, across = along ? g.H : g.W;
  const n = s.lane_count, kind = s.lane_kind === 'hole' ? HOLE : WALL;
  for (let k = 1; k < n; k++) {
    const pos = Math.round(k * across / n), every = rng.int(10, 20), gap = rng.int(2, 4), phase = rng.int(0, every);
    for (let i = 4; i < len - 4; i++) {
      if ((i + phase) % every < gap) continue;
      for (let t = 0; t < s.lane_thick; t++) {
        const x = along ? i : pos + t, y = along ? pos + t : i;
        if (g.in(x, y)) g.t[g.idx(x, y)] = kind;
      }
    }
  }
}

function rings(g, rng, s) {
  const cx = (g.W - 1) / 2, cy = (g.H - 1) / 2, step = s.ring_step, kind = s.ring_kind === 'hole' ? HOLE : WALL;
  for (let r = step; r < Math.min(g.W, g.H) / 2 - 3; r += step) {
    const pts = [];
    for (let y = 0; y < g.H; y++) for (let x = 0; x < g.W; x++) {
      const d = s.ring_shape === 'diamond' ? (Math.abs(x - cx) + Math.abs(y - cy)) / 1.5 : Math.max(Math.abs(x - cx), Math.abs(y - cy));
      if (Math.abs(d - r) < 0.5) pts.push([x, y, Math.atan2(y - cy, x - cx)]);
    }
    const gates = Array.from({ length: s.ring_gates }, () => rng.uniform(-Math.PI, Math.PI)), width = s.door_width / r;
    for (const [x, y, a] of pts) if (!gates.some(b => Math.abs(((a - b + 3 * Math.PI) % (2 * Math.PI)) - Math.PI) < width)) g.t[g.idx(x, y)] = kind;
  }
}

// Staggered parallel wall segments, like the competition map "rows".
function rows(g, rng, s) {
  const gap = s.row_gap, seg = rng.int(6, 14), hole = rng.int(3, 6), diag = rng.chance(0.4);
  for (let r = gap; r < g.H - 2; r += gap) {
    const off = rng.int(0, seg + hole);
    for (let x = -off; x < g.W; x += seg + hole)
      if (diag) line(g, x, r, 1, 1, Math.min(seg, 6), WALL); else line(g, x, r, 1, 0, seg, WALL);
  }
}

function holes(g, rng, s) {
  if (s.holes === 'lakes') {
    const n = valueNoise(rng, g.W, g.H, rng.uniform(8, 18), 3), cut = quantile(n, 1 - s.hole_amount);
    for (let i = 0; i < n.length; i++) if (n[i] > cut && g.t[i] === GROUND) g.t[i] = HOLE;
  } else if (s.holes === 'moat') {
    const vertical = g.sym === 'horizontal' || (g.sym === 'rotational' && g.W > g.H);
    const len = vertical ? g.H : g.W, mid = Math.floor((vertical ? g.W : g.H) / 2) - 1;
    const thick = rng.int(2, 3), off = rng.int(-Math.floor(len / 6), Math.floor(len / 6));
    const gapAt = [rng.int(2, Math.floor(len / 3)), rng.int(Math.floor(2 * len / 3), len - 6)], gw = s.door_width + 1;
    for (let k = 0; k < len; k++) {
      if (gapAt.some(o => k >= o && k < o + gw)) continue;
      for (let t = 0; t < thick; t++) {
        const x = vertical ? mid + off + t : k, y = vertical ? k : mid + off + t;
        if (g.in(x, y) && g.t[g.idx(x, y)] === GROUND) g.t[g.idx(x, y)] = HOLE;
      }
    }
  } else if (s.holes === 'pits') {
    const target = s.hole_amount * g.W * g.H;
    for (let guard = 0; count(g, HOLE) < target && guard < 2000; guard++)
      rect(g, rng.int(0, g.W - 1), rng.int(0, g.H - 1), rng.int(1, 4), rng.int(1, 4), HOLE, GROUND);
  }
}

function bushes(g, rng, s) {
  if (s.bushes === 'blobs') {
    const n = valueNoise(rng, g.W, g.H, rng.uniform(5, 12), 2), cut = quantile(n, 1 - s.bush_amount);
    for (let i = 0; i < n.length; i++) if (n[i] > cut && g.t[i] === GROUND) g.t[i] = BUSH;
  } else if (s.bushes === 'patches' || s.bushes === 'strips') {
    const target = s.bush_amount * g.W * g.H;
    for (let guard = 0; count(g, BUSH) < target && guard < 3000; guard++) {
      const x = rng.int(0, g.W - 1), y = rng.int(0, g.H - 1);
      if (s.bushes === 'patches') rect(g, x, y, rng.int(2, 7), rng.int(2, 6), BUSH, GROUND);
      else if (rng.chance(0.5)) rect(g, x, y, rng.int(4, 14), rng.int(1, 2), BUSH, GROUND);
      else rect(g, x, y, rng.int(1, 2), rng.int(4, 14), BUSH, GROUND);
    }
  }
}

// Drops bush clusters (edge-connected, as vision groups them) under `min` tiles, then the smallest
// beyond `max`: the map file stores a table over cluster pairs (~4 bytes x clusters squared).
function pruneBushes(g, min, max) {
  const pass = Uint8Array.from(g.t, k => k === BUSH), seen = new Uint8Array(g.t.length), clusters = [];
  for (let i = 0; i < g.t.length; i++) {
    if (!pass[i] || seen[i]) continue;
    const cluster = [i];
    seen[i] = 1;
    for (let h = 0; h < cluster.length; h++) {
      const j = cluster[h], x = j % g.W, y = (j - x) / g.W;
      for (const [dx, dy] of N4) {
        const k = (y + dy) * g.W + x + dx;
        if (g.in(x + dx, y + dy) && pass[k] && !seen[k]) { seen[k] = 1; cluster.push(k); }
      }
    }
    clusters.push(cluster);
  }
  clusters.sort((p, q) => p.length - q.length || p[0] - q[0]);
  let left = clusters.length;
  for (const c of clusters) {
    if (c.length >= min && left <= max) break;
    if (g.t[c[0]] !== BUSH) continue;
    for (const j of c) g.set(j % g.W, Math.floor(j / g.W), GROUND);
    left -= g.mirror(c[0]) !== c[0] && c.includes(g.mirror(c[0])) ? 1 : 2;
  }
}

function quantile(arr, q) {
  const s = Float32Array.from(arr).sort();
  return s[Math.min(s.length - 1, Math.max(0, Math.floor(q * s.length)))];
}

const TERRAIN = { open: () => {}, scatter, caves, rooms, lanes, rings, rows };

// ---- spawn and connectivity ----------------------------------------------------------------
function placeSpawn(g, rng, s) {
  const n = s.spawn_size, { W, H } = g, inset = rng.int(0, 3);
  let x, y;
  const place = s.spawn_place;
  const edgeX = () => inset, midY = () => Math.floor(H / 2) - (n >> 1) + rng.int(-Math.floor(H / 6), Math.floor(H / 6));
  const farX = () => Math.round(W * rng.uniform(0.1, 0.22)), farY = () => Math.round(H * rng.uniform(0.1, 0.22));
  if (g.sym === 'horizontal') {
    x = place === 'inset' ? farX() : edgeX();
    y = place === 'edge' || place === 'inset' ? midY() : (rng.chance(0.5) ? inset : H - n - inset);
  } else if (g.sym === 'vertical') {
    y = place === 'inset' ? farY() : inset;
    x = place === 'edge' || place === 'inset' ? Math.floor(W / 2) - (n >> 1) + rng.int(-Math.floor(W / 6), Math.floor(W / 6)) : (rng.chance(0.5) ? inset : W - n - inset);
  } else if (place === 'corner') { x = inset; y = rng.chance(0.5) ? inset : H - n - inset; }
  else if (place === 'edge') { if (W >= H) { x = inset; y = midY(); } else { y = inset; x = Math.floor(W / 2) - (n >> 1) + rng.int(-Math.floor(W / 6), Math.floor(W / 6)); } }
  else { x = farX(); y = farY(); }
  x = Math.max(0, Math.min(W - n, x)); y = Math.max(0, Math.min(H - n, y));
  g.spawn = { x, y, w: n, h: n };
  const [bx, by] = g.mirrorXY(x, y), b = { x: Math.min(bx, g.mirrorXY(x + n - 1, y + n - 1)[0]), y: Math.min(by, g.mirrorXY(x + n - 1, y + n - 1)[1]) };
  const gap = Math.max(Math.abs(b.x - x), Math.abs(b.y - y)) - n + 1;
  if (gap < Math.max(16, 0.45 * Math.min(W, H))) throw new GenFail(`spawns too close (${gap})`);
  for (let yy = y - 2; yy < y + n + 2; yy++) for (let xx = x - 2; xx < x + n + 2; xx++)
    if (g.in(xx, yy) && g.get(xx, yy) !== BUSH) g.set(xx, yy, GROUND);
  if (!s.spawn_bush) for (let yy = y; yy < y + n; yy++) for (let xx = x; xx < x + n; xx++) g.set(xx, yy, GROUND);
}

// Joins every walkable component to the spawn's by symmetric tunnels (cheapest through holes,
// then walls); fills components too small to matter.
function connect(g, rng, s) {
  const { W, H } = g;
  for (let round = 0; round < 400; round++) {
    const pass = g.walkable(), { comp, sizes } = g.components(pass);
    const main = comp[g.spawnTiles(0)[0]], vault = new Set([...g.vaults].map(i => comp[i]));
    if (sizes.length <= 1) return;
    const other = sizes.findIndex((n, id) => id !== main && !vault.has(id) && n >= s.min_pocket);
    if (other < 0) {
      const fill = [];
      for (let i = 0; i < comp.length; i++) if (comp[i] >= 0 && comp[i] !== main && !vault.has(comp[i]) && comp[i] !== comp[g.mirror(g.spawnTiles(0)[0])]) fill.push([i, fillFor(g, i)]);
      for (const [i, k] of fill) g.t[i] = k;
      if (comp[g.mirror(g.spawnTiles(0)[0])] === main) return;
      continue;
    }
    const cost = new Float64Array(W * H).fill(Infinity), prev = new Int32Array(W * H).fill(-1), heap = [];
    const push = (c, i) => { heap.push([c, i]); let k = heap.length - 1; while (k) { const p = (k - 1) >> 1; if (heap[p][0] <= heap[k][0]) break; [heap[p], heap[k]] = [heap[k], heap[p]]; k = p; } };
    const pop = () => { const top = heap[0], last = heap.pop(); if (heap.length) { heap[0] = last; let k = 0; for (;;) { const l = 2 * k + 1, r = l + 1; let m = k; if (l < heap.length && heap[l][0] < heap[m][0]) m = l; if (r < heap.length && heap[r][0] < heap[m][0]) m = r; if (m === k) break; [heap[m], heap[k]] = [heap[k], heap[m]]; k = m; } } return top; };
    for (let i = 0; i < comp.length; i++) if (comp[i] === main) { cost[i] = 0; push(0, i); }
    let goal = -1;
    while (heap.length) {
      const [c, i] = pop();
      if (c > cost[i]) continue;
      if (comp[i] === other) { goal = i; break; }
      const x = i % W, y = (i - x) / W;
      for (const [dx, dy] of N4) {
        const nx = x + dx, ny = y + dy;
        if (nx < 0 || ny < 0 || nx >= W || ny >= H) continue;
        const j = ny * W + nx, k = g.t[j];
        const step = k === ALTAR ? Infinity : k === HOLE ? s.hole_cost : k === WALL ? 3 : 0.01;
        const nc = c + step + (step > 0.01 ? rng.float() * 0.5 : 0);
        if (nc < cost[j]) { cost[j] = nc; prev[j] = i; push(nc, j); }
      }
    }
    if (goal < 0) throw new GenFail('cannot connect map');
    for (let i = goal; i >= 0; i = prev[i]) {
      const x = i % W, y = (i - x) / W;
      for (let dy = 0; dy < s.carve_width; dy++) for (let dx = 0; dx < s.carve_width; dx++)
        if (g.in(x + dx, y + dy) && (g.get(x + dx, y + dy) === WALL || g.get(x + dx, y + dy) === HOLE)) g.set(x + dx, y + dy, GROUND);
    }
  }
  throw new GenFail('connectivity repair did not converge');
}

function fillFor(g, i) {
  const x = i % g.W, y = (i - x) / g.W;
  let holes = 0, walls = 0;
  for (const [dx, dy] of N4) if (g.in(x + dx, y + dy)) { const k = g.get(x + dx, y + dy); holes += k === HOLE; walls += k === WALL; }
  return holes > walls ? HOLE : WALL;
}

// ---- placement ----------------------------------------------------------------------------
// Walking distances from each spawn (team B's spawn is impassable to team A and vice versa).
function spawnFields(g, blockers) {
  const pass = g.walkable(blockers), a = g.spawnTiles(0), b = g.spawnTiles(1);
  const passA = pass.slice(), passB = pass.slice();
  for (const i of b) passA[i] = 0;
  for (const i of a) passB[i] = 0;
  return { dA: g.bfs(a, passA), dB: g.bfs(b, passB), pass };
}

// Contest ratio of a tile: 0 at team A's spawn, 0.5 equidistant, 1 at team B's.
const ratio = (dA, dB, i) => dA[i] < 0 || dB[i] < 0 ? -1 : dA[i] / Math.max(1, dA[i] + dB[i]);

const BANDS = { near: [0.06, 0.26], mid: [0.22, 0.42], contested: [0.38, 0.5], central: [0.4, 0.5], any: [0.06, 0.5] };

function bandFor(rng, bias) {
  const w = { near: { near: 6, mid: 3, contested: 1 }, spread: { near: 3, mid: 4, contested: 3 }, contested: { near: 1, mid: 3, contested: 6 } }[bias];
  return BANDS[rng.weighted(w)];
}

function candidates(g, rng, f, band, pred) {
  const out = [];
  for (let i = 0; i < g.t.length; i++) {
    const r = ratio(f.dA, f.dB, i);
    if (r >= band[0] && r <= band[1] && pred(i % g.W, Math.floor(i / g.W), i)) out.push(i);
  }
  return rng.shuffle(out);
}

// Accepts the map state if every objective is still reachable with camps blocking, and camps
// cut off no pocket of the map.
function stillConnected(g) {
  const camps = g.campMask(), blocked = spawnFields(g, camps), open = spawnFields(g);
  const a = g.spawnTiles(0), b = g.spawnTiles(1);
  if (!b.some(i => g.reachNear(blocked.dA, i % g.W, Math.floor(i / g.W)) >= 0)) return false;
  for (let i = 0; i < g.t.length; i++) {
    if (g.t[i] === ALTAR && !g.vaults.has(i) && g.reachNear(blocked.dA, i % g.W, Math.floor(i / g.W)) < 0) return false;
    if (open.pass[i] && !camps[i] && open.dA[i] >= 0 && blocked.dA[i] < 0 && blocked.dB[i] < 0 && !a.includes(i) && !b.includes(i)) return false;
  }
  for (const grp of g.groups()) if (![...grp.tiles].some(i => g.vaults.has(i)) && !grp.members.some(c => g.reachNear(blocked.dA, c.x, c.y) >= 0 || g.reachNear(blocked.dB, c.x, c.y) >= 0)) return false;
  return true;
}

// Walled pockets that only a teleport crystal (range 3) reaches, holding an altar or a camp group,
// like the altar behind the double wall in the competition map "collision".
function placeVaults(g, rng, s) {
  for (let v = 0; v < s.vaults; v++) {
    const k = rng.int(3, 4), t = rng.int(1, 2), size = k + 2 * t, f = spawnFields(g), band = BANDS[rng.choice(['mid', 'contested'])];
    const content = rng.weighted({ altar: 2, gems: 1, elk_gold: 1, wolf_pair: 1 });
    for (const i of candidates(g, rng, f, band, () => true).slice(0, 200)) {
      const x0 = i % g.W, y0 = (i - x0) / g.W, box = [];
      for (let y = y0; y < y0 + size; y++) for (let x = x0; x < x0 + size; x++) box.push([x, y]);
      if (!box.every(([x, y]) => g.in(x, y) && (g.get(x, y) === GROUND || g.get(x, y) === BUSH) && rectDist(g.spawn, x, y) >= 6 && rectDist(g.spawn, ...g.mirrorXY(x, y)) >= 6)) continue;
      const mirrored = new Set(box.map(([x, y]) => g.idx(...g.mirrorXY(x, y))));
      if (box.some(([x, y]) => { for (let dy = -2; dy <= 2; dy++) for (let dx = -2; dx <= 2; dx++) if (mirrored.has(g.idx(x + dx, y + dy))) return true; return false; })) continue;
      if (g.camps.length && g.allCamps().some(c => box.some(([x, y]) => cheb(c.x, c.y, x, y) <= 1))) continue;
      const saved = g.t.slice(), savedCamps = g.camps.length, savedVaults = new Set(g.vaults);
      const inner = box.filter(([x, y]) => x >= x0 + t && y >= y0 + t && x < x0 + t + k && y < y0 + t + k);
      for (const [x, y] of box) g.set(x, y, WALL);
      for (const [x, y] of inner) { g.set(x, y, GROUND); g.vaults.add(g.idx(x, y)); g.vaults.add(g.mirror(g.idx(x, y))); }
      const cx = x0 + t + (k >> 1) - 1, cy = y0 + t + (k >> 1) - 1;
      if (content === 'altar') g.set(cx + rng.int(0, 1), cy + rng.int(0, 1), ALTAR);
      else for (const [type, dx, dy] of TEMPLATES[content](rng)) g.camps.push({ type, x: cx + dx, y: cy + dy });
      if (stillConnected(g) && inner.every(([x, y]) => g.get(x, y) !== WALL)) break;
      g.t = saved; g.camps.length = savedCamps; g.vaults = savedVaults;
    }
  }
}

function placeAltars(g, rng, s) {
  const placed = [];
  const free = (x, y) => g.get(x, y) === GROUND && rectDist(g.spawn, x, y) >= 3 && rectDist(g.spawn, ...g.mirrorXY(x, y)) >= 3 && !g.reserved?.has(g.idx(x, y))
    && [...placed, ...placed.map(([px, py]) => g.mirrorXY(px, py))].every(([px, py]) => cheb(px, py, x, y) >= s.altar_spacing);
  if (s.shared_altar) {
    const cx = (g.W - 1) / 2, cy = (g.H - 1) / 2, self = [];
    for (let y = 0; y < g.H; y++) for (let x = 0; x < g.W; x++) { const [mx, my] = g.mirrorXY(x, y); if (mx === x && my === y && cheb(x, y, cx, cy) <= Math.min(g.W, g.H) / 4) self.push([x, y]); }
    for (const [x, y] of rng.shuffle(self)) {
      if (!free(x, y)) continue;
      g.set(x, y, ALTAR);
      if (stillConnected(g)) { placed.push([x, y]); break; }
      g.set(x, y, GROUND);
    }
  }
  for (let k = 0; k < s.altars; k++) {
    const f = spawnFields(g), band = s.altar_zone === 'mid' ? BANDS.central : k === 0 && s.altar_near ? BANDS.near : BANDS[rng.weighted(s.altar_bands)];
    let ok = false;
    for (const i of candidates(g, rng, f, band, free).slice(0, 40)) {
      const x = i % g.W, y = (i - x) / g.W, [mx, my] = g.mirrorXY(x, y);
      if (mx === x && my === y) continue;
      g.set(x, y, ALTAR);
      if (stillConnected(g)) { placed.push([x, y]); ok = true; break; }
      g.set(x, y, GROUND);
    }
    if (!ok && k === 0) throw new GenFail('no altar placement');
  }
}

const TEMPLATES = {
  wolf: () => [['wolf', 0, 0]],
  wolf_pair: rng => rng.chance(0.5) ? [['wolf', 0, 0], ['wolf', 1, 0]] : [['wolf', 0, 0], ['wolf', 0, 1]],
  wolf_pack: rng => rng.choice([[['wolf', 0, 0], ['wolf', 1, 0], ['wolf', 2, 0]], [['wolf', 0, 0], ['wolf', 1, 0], ['wolf', 1, 1]], [['wolf', 0, 0], ['wolf', 0, 1], ['wolf', 0, 2]]]),
  elk: () => [['elk', 0, 0]],
  elk_gold: rng => [['elk', 0, 0], rng.choice([['gold_cluster', 1, 0], ['gold_cluster', 0, 1]])],
  elk_gems: rng => rng.chance(0.5) ? [['elk', 0, 1], ['gem_cluster', 1, 0], ['gem_cluster', 1, 1], ['gem_cluster', 1, 2]] : [['elk', 0, 0], ['gem_cluster', 1, 0]],
  gems: rng => [[['gem_cluster', 0, 0]], [['gem_cluster', 0, 0], ['gem_cluster', 1, 0]], [['gem_cluster', 0, 0], ['gem_cluster', 1, 0], ['gem_cluster', 0, 1], ['gem_cluster', 1, 1]], [['gem_cluster', 0, 0], ['gem_cluster', 0, 1], ['gem_cluster', 0, 2]]][rng.int(0, 3)],
  gold: rng => rng.chance(0.6) ? [['gold_cluster', 0, 0]] : [['gold_cluster', 0, 0], ['gold_cluster', 1, 0]],
  gold_row: () => [['gold_cluster', 0, 0], ['gold_cluster', 1, 0], ['gold_cluster', 2, 0]],
  gold_gems: () => [['gem_cluster', 0, 0], ['gem_cluster', 1, 1], ['gold_cluster', 1, 0], ['gold_cluster', 0, 1]],
  monolith: () => [['monolith', 0, 0]],
  monolith_ring: () => [['monolith', 1, 1], ...[[0, 0], [1, 0], [2, 0], [0, 1], [2, 1], [0, 2], [1, 2], [2, 2]].map(([x, y]) => ['gem_cluster', x, y])],
};

function campCellsOk(g, cells, s, shared) {
  const camps = g.allCamps(), mirrors = cells.map(([, x, y]) => g.mirrorXY(x, y));
  for (const [, x, y] of cells) {
    if (!g.in(x, y) || g.get(x, y) !== GROUND) return false;
    if (rectDist(g.spawn, x, y) < s.camp_spawn_gap || rectDist(g.spawn, ...g.mirrorXY(x, y)) < s.camp_spawn_gap) return false;
    if (camps.some(c => cheb(c.x, c.y, x, y) <= 1)) return false;
    for (let dy = -1; dy <= 1; dy++) for (let dx = -1; dx <= 1; dx++) if (g.in(x + dx, y + dy) && g.get(x + dx, y + dy) === ALTAR) return false;
    if (mirrors.some(([mx, my]) => (shared ? cheb(mx, my, x, y) === 0 : cheb(mx, my, x, y) <= 1))) return false;
  }
  return true;
}

function tryGroup(g, cells, s, shared = false) {
  if (!campCellsOk(g, cells, s, shared)) return false;
  const before = g.camps.length;
  for (const [type, x, y] of cells) g.camps.push({ type, x, y });
  const grp = g.groups().filter(q => cells.some(([, x, y]) => q.tiles.has(y * g.W + x)));
  if (grp.length === 1 && grp[0].shared === shared && stillConnected(g)) return true;
  g.camps.length = before;
  return false;
}

// A self-mirrored band straddling the symmetry axis (through the centre, under rotation): `len`
// tiles along it and `depth` rows on each side; inner[k] types the axis row, outer the rest.
// Returns team A's half of the cells and every tile of the band plus a one-tile margin.
function axisBand(g, rng, len, depth, inner, outer) {
  const rot = g.sym === 'rotational', rowsY = g.sym === 'vertical' || (rot && g.H % 2 === 0 && (g.W % 2 === 1 || rng.chance(0.5)));
  const across = rowsY ? g.H : g.W, along = rowsY ? g.W : g.H, xy = (u, v) => rowsY ? [u, v] : [v, u];
  if (across % 2 || (rot && (along - len) % 2) || len + 2 > along) return null;
  const a = rot ? (along - len) / 2 : rng.int(1, along - len - 1), cells = [], area = new Set();
  for (let k = 0; k < len; k++) for (let d = 0; d < depth; d++) cells.push([d ? outer : inner[rot ? Math.min(k, len - 1 - k) : k], ...xy(a + k, across / 2 - 1 - d)]);
  for (let u = a - 1; u <= a + len; u++) for (let v = across / 2 - depth - 1; v <= across / 2 + depth; v++) {
    const [x, y] = xy(u, v);
    if (g.in(x, y)) { area.add(g.idx(x, y)); area.add(g.mirror(g.idx(x, y))); }
  }
  return { cells, area };
}

// Carves a clearing for one large shared group worth 240-480 gems, placed first by placeCamps.
function reserveShared(g, rng) {
  for (let guard = 0; guard < 50; guard++) {
    const len = rng.int(2, 6), depth = rng.chance(0.65) ? 2 : 1, inner = Array.from({ length: len }, () => rng.weighted({ elk: 3, wolf: 1, gem_cluster: 1 }));
    const band = axisBand(g, rng, len, depth, inner, 'gem_cluster');
    if (!band) continue;
    const gems = 2 * band.cells.reduce((n, [t]) => n + CAMP[t].gems, 0);
    if (gems < 240 || gems > 480) continue;
    for (const i of band.area) g.t[i] = GROUND;
    g.reserved = band.area;
    g.sharedCells = band.cells;
    return;
  }
  throw new GenFail('no room for a shared gem group');
}

function placeCamps(g, rng, s) {
  const total = () => g.camps.length;
  if (g.sharedCells && !tryGroup(g, g.sharedCells, s, true)) throw new GenFail('shared gem group blocked');
  for (let k = 0; k < (s.shared_gold ?? 0); k++)
    for (let guard = 0; guard < 30; guard++) {
      const len = rng.int(1, 3), band = axisBand(g, rng, len, 1, Array(len).fill('gold_cluster'), 'gold_cluster');
      if (band && tryGroup(g, band.cells, s, true)) break;
    }
  if (s.shared_camp) {
    const cx = Math.floor((g.W - 1) / 2), cy = Math.floor((g.H - 1) / 2), shapes = [[[0, 0]], [[0, 0], [1, 0]], [[0, 0], [0, 1]], [[0, 0], [1, 0], [0, 1]]];
    const type = rng.choice(['elk', 'wolf', 'gem_cluster']);
    outer: for (let r = 0; r <= 4; r++) for (const shape of shapes) for (let dy = -r; dy <= r; dy++) for (let dx = -r; dx <= r; dx++) {
      const cells = shape.map(([sx, sy], k) => [k ? 'gem_cluster' : type, cx + dx + sx, cy + dy + sy]);
      if (tryGroup(g, cells, s, true)) break outer;
    }
  }
  for (let k = 0; k < s.monoliths; k++) {
    const f = spawnFields(g), tpl = TEMPLATES[rng.chance(s.monolith_ring) ? 'monolith_ring' : 'monolith'](rng);
    for (const i of candidates(g, rng, f, BANDS[s.monolith_band], () => true).slice(0, 300)) {
      const x = i % g.W, y = (i - x) / g.W;
      if (tryGroup(g, tpl.map(([t, dx, dy]) => [t, x + dx, y + dy]), s)) break;
    }
  }
  let made = 0;
  for (let guard = 0; made < s.groups && guard < s.groups * 4 && total() < 200; guard++) {
    const f = spawnFields(g), tpl = TEMPLATES[rng.weighted(s.camp_mix)](rng), band = bandFor(rng, s.camp_bias);
    const flip = rng.chance(0.5), cells = tpl.map(([t, dx, dy]) => [t, flip ? dy : dx, flip ? dx : dy]);
    for (const i of candidates(g, rng, f, band, () => true).slice(0, 60)) {
      const x = i % g.W, y = (i - x) / g.W;
      if (tryGroup(g, cells.map(([t, dx, dy]) => [t, x + dx, y + dy]), s)) { made++; break; }
    }
  }
  if (made < Math.min(s.groups, 1)) throw new GenFail('no camp placement');
}

// ---- validation and metrics ----------------------------------------------------------------
// Groups on team A's side (each non-shared group's mirror is on team B's), and shared groups.
export function sideGroups(g, f = spawnFields(g)) {
  const mine = [], shared = [], near = (d, q) => Math.min(...q.members.map(c => { const v = g.reachNear(d, c.x, c.y); return v < 0 ? Infinity : v; }));
  for (const q of g.groups()) {
    if (q.shared) { shared.push(q); continue; }
    const dA = near(f.dA, q), dB = near(f.dB, q), lo = Math.min(...q.tiles), mlo = Math.min(...[...q.tiles].map(i => g.mirror(i)));
    if (dA < dB || (dA === dB && lo < mlo)) mine.push({ ...q, dA, dB });
  }
  return { mine, shared };
}

// Tiles reachable from team A's walking field when teleport crystals (range 3, terrain ignored,
// landing on a free ground or bush tile outside the enemy spawn) may be chained with walking.
function teleportClosure(g, dA, camps, enemySpawn) {
  const reached = Int32Array.from(dA, d => (d >= 0 ? 0 : -1)), land = i => (g.t[i] === GROUND || g.t[i] === BUSH) && !camps[i] && !enemySpawn.has(i);
  const pass = g.walkable(camps);
  for (;;) {
    const fresh = [];
    for (let i = 0; i < reached.length; i++) {
      if (reached[i] >= 0 || !land(i)) continue;
      const x = i % g.W, y = (i - x) / g.W;
      if (g.reachNear(reached, x, y, 3) >= 0) fresh.push(i);
    }
    if (!fresh.length) return reached;
    const d = g.bfs(fresh, pass);
    for (let i = 0; i < d.length; i++) if (d[i] >= 0 && reached[i] < 0 && !enemySpawn.has(i)) reached[i] = 1;
  }
}

// Records existing teleport-only pockets (and altars beside them) as vaults, e.g. on loaded maps.
export function markVaults(g) {
  const camps = g.campMask(), open = spawnFields(g), b = new Set(g.spawnTiles(1)), tele = teleportClosure(g, open.dA, camps, b);
  for (let i = 0; i < g.t.length; i++) if (open.pass[i] && open.dA[i] < 0 && tele[i] >= 0) g.vaults.add(i);
  for (let i = 0; i < g.t.length; i++) if (g.t[i] === ALTAR && g.reachNear(open.dA, i % g.W, Math.floor(i / g.W)) < 0) g.vaults.add(i);
  return g;
}

export function validate(g, { strict = true } = {}) {
  const errors = [], warnings = [];
  if (g.W < 30 || g.H < 30 || g.W > 100 || g.H > 100) (strict ? errors : warnings).push(`size ${g.W}x${g.H} outside 30..100`);
  if (g.picks < 3 || g.picks > 5) errors.push(`picks ${g.picks}`);
  const s = g.spawn, area = s.w * s.h;
  if (area < 9 || area > 16) errors.push(`spawn area ${s.w}x${s.h}`);
  else if (!(s.w === s.h && (s.w === 3 || s.w === 4))) warnings.push(`spawn ${s.w}x${s.h} (competition maps use 3x3 or 4x4)`);
  if (!g.isSymmetric()) errors.push('terrain is not symmetric');
  const a = new Set(g.spawnTiles(0)), b = g.spawnTiles(1);
  if (b.some(i => a.has(i))) errors.push('spawns overlap');
  for (const i of [...a, ...b]) if (g.t[i] !== GROUND && g.t[i] !== BUSH) { errors.push('spawn not clear'); break; }
  const seen = new Set();
  for (const c of g.allCamps()) {
    const i = c.y * g.W + c.x;
    if (seen.has(i)) errors.push(`camps overlap at (${c.x}, ${c.y})`);
    seen.add(i);
    if (a.has(i) || b.includes(i)) errors.push(`camp on spawn at (${c.x}, ${c.y})`);
    if (g.t[i] !== GROUND && g.t[i] !== BUSH) errors.push(`camp on blocked tile at (${c.x}, ${c.y})`);
  }
  if (g.camps.length > 250) errors.push(`${g.camps.length} camps (limit 250)`);
  if (errors.length) return { errors, warnings };
  const camps = g.campMask(), blocked = spawnFields(g, camps), open = spawnFields(g), bSet = new Set(b);
  const tele = teleportClosure(g, open.dA, camps, bSet), at = (d, x, y) => g.reachNear(d, x, y) >= 0;
  // Objectives walled off but within teleport-crystal reach (as in the competition map "collision").
  const unreachable = (what, walk, viaTeleport, vault) => {
    if (walk) return;
    if (viaTeleport) (!strict || vault ? warnings : errors).push(`${what} reachable only by teleport crystal`);
    else errors.push(`${what} unreachable`);
  };
  if (!b.some(i => g.reachNear(blocked.dA, i % g.W, Math.floor(i / g.W)) >= 0)) errors.push('spawns not connected');
  let altars = 0;
  for (let i = 0; i < g.t.length; i++) {
    if (g.t[i] !== ALTAR) continue;
    altars++;
    const x = i % g.W, y = (i - x) / g.W;
    unreachable(`altar (${x}, ${y})`, at(blocked.dA, x, y), at(tele, x, y), g.vaults.has(i));
  }
  if (!altars) (strict ? errors : warnings).push('no altars');
  for (const grp of g.groups()) {
    const c = grp.members[0], walk = grp.members.every(m => at(open.dA, m.x, m.y));
    unreachable(`camp group at (${c.x}, ${c.y})`, walk, grp.members.every(m => at(tele, m.x, m.y)), [...grp.tiles].some(i => g.vaults.has(i)));
    if (walk && !grp.members.some(m => at(blocked.dA, m.x, m.y) || at(blocked.dB, m.x, m.y))) errors.push(`camp group at (${c.x}, ${c.y}) enclosed by other camps`);
  }
  if (!g.groups().length) (strict ? errors : warnings).push('no camps');
  let pocket = 0, telePocket = 0;
  for (let i = 0; i < g.t.length; i++) if (open.pass[i] && open.dA[i] < 0 && !a.has(i) && !bSet.has(i)) { pocket++; telePocket += tele[i] >= 0; }
  if (pocket) warnings.push(`${pocket} walkable tiles unreachable on foot${telePocket ? ` (${telePocket} by teleport crystal)` : ''}`);
  return { errors, warnings };
}

export const altarZone = r => r === null ? null : r < 0.4 ? 'own' : r > 0.6 ? 'enemy' : 'mid';

export function metrics(g) {
  const camps = g.campMask(), f = spawnFields(g, camps), open = spawnFields(g);
  const b = g.spawnTiles(1);
  const S = Math.min(...b.map(i => g.reachNear(f.dA, i % g.W, Math.floor(i / g.W))).filter(d => d >= 0));
  const s = g.spawn, [bx, by] = g.mirrorXY(s.x, s.y);
  const cheby = Math.max(Math.abs(bx - s.x), Math.abs(by - s.y)) - s.w + 1;
  let reach = 0;
  for (let i = 0; i < g.t.length; i++) reach += open.dA[i] >= 0;
  const front = new Int32Array(S + 2);
  for (let i = 0; i < g.t.length; i++) if (f.dA[i] >= 0 && f.dA[i] <= S) front[f.dA[i]]++;
  let choke = Infinity;
  for (let d = Math.floor(S * 0.25); d <= Math.ceil(S * 0.75); d++) choke = Math.min(choke, front[d]);
  const clear = g.clearance();
  let clearSum = 0;
  for (let i = 0; i < g.t.length; i++) if (open.dA[i] >= 0) clearSum += Math.min(clear[i], 6);
  const altars = [], altarRatios = [];
  for (let i = 0; i < g.t.length; i++) {
    if (g.t[i] !== ALTAR) continue;
    const x = i % g.W, y = (i - x) / g.W, dA = g.reachNear(f.dA, x, y), dB = g.reachNear(f.dB, x, y);
    altars.push(dA);
    if (dA >= 0 && dB >= 0) altarRatios.push([dA, dA / Math.max(1, dA + dB)]);
  }
  altarRatios.sort((p, q) => p[0] - q[0] || p[1] - q[1]);
  const altarRatio = altarRatios.length ? altarRatios[0][1] : null;
  const { mine, shared } = sideGroups(g, open);
  const campDist = mine.map(q => q.dA).filter(Number.isFinite);
  const ratios = mine.filter(q => Number.isFinite(q.dA + q.dB)).map(q => q.dA / Math.max(1, q.dA + q.dB));
  const types = {};
  for (const q of [...mine, ...shared]) for (const c of q.members) types[c.type] = (types[c.type] ?? 0) + (q.shared ? 0.5 : 1);
  const frac = k => Math.round(1000 * g.t.reduce((n, t) => n + (t === k), 0) / g.t.length) / 1000;
  const median = arr => arr.length ? [...arr].sort((p, q) => p - q)[arr.length >> 1] : null;
  return {
    size: `${g.W}x${g.H}`, area: g.W * g.H, sym: g.sym, picks: g.picks, spawn: `${s.w}x${s.h}`,
    walls: frac(WALL), holes: frac(HOLE), bushes: frac(BUSH),
    reach_frac: Math.round(1000 * reach / g.t.length) / 1000,
    spawn_dist: S, detour: Math.round(100 * S / Math.max(1, cheby)) / 100, choke: choke === Infinity ? null : choke,
    openness: Math.round(100 * clearSum / Math.max(1, reach)) / 100,
    altars: altars.length, altar_near: altars.length ? Math.min(...altars) : null,
    // Nearest walkable altar's distance from own spawn over the sum of both spawns' distances.
    altar_ratio: altarRatio === null ? null : Math.round(100 * altarRatio) / 100, altar_zone: altarZone(altarRatio),
    groups_side: mine.length, shared_groups: shared.length, camps_side: Object.values(types).reduce((a, b) => a + b, 0), types,
    gems_side: mine.reduce((n, q) => n + q.gems, 0) + shared.reduce((n, q) => n + q.gems / 2, 0),
    gold_side: mine.reduce((n, q) => n + q.gold, 0) + shared.reduce((n, q) => n + q.gold / 2, 0),
    monoliths: types.monolith ?? 0,
    camp_near: campDist.length ? Math.min(...campDist) : null, camp_ratio: median(ratios.map(r => Math.round(100 * r) / 100)),
    contested_share: ratios.length ? Math.round(100 * ratios.filter(r => r >= 0.38).length / ratios.length) / 100 : 0,
  };
}

// ---- presets -------------------------------------------------------------------------------
const DEFAULTS = {
  symmetry: { rotational: 5, horizontal: 2.5, vertical: 2.5 }, picks: [3, 5], spawn_size: { 3: 1, 4: 1 }, spawn_place: { corner: 5, edge: 3, inset: 2 }, spawn_bush: 0.15,
  terrain: { open: 1, scatter: 4, caves: 1.5, rooms: 1.5, lanes: 1, rings: 1, rows: 1 }, wall_density: [0.02, 0.12], wall_length: [0.1, 0.35],
  cave_fill: [0.38, 0.46], cave_iters: [3, 5], room_size: [7, 14], door_width: [2, 4], room_margin: [0, 4], lane_count: [2, 4], lane_kind: { wall: 2, hole: 1 }, lane_thick: [1, 2],
  ring_step: [7, 11], ring_gates: [2, 4], ring_kind: { wall: 3, hole: 1 }, ring_shape: { square: 2, diamond: 1 }, row_gap: [5, 9],
  holes: { none: 3, lakes: 2, moat: 1.5, pits: 2 }, hole_amount: [0.02, 0.1], bushes: { none: 1, blobs: 3, patches: 3, strips: 2 }, bush_amount: [0.03, 0.15],
  min_pocket: 20, carve_width: 2, hole_cost: 1.5, max_bush_clusters: 24, vaults: { 0: 12, 1: 1 },
  altars: [1, 5], altar_near: 0.6, shared_altar: 0.25, altar_spacing: [5, 9], altar_bands: { near: 2, mid: 3, contested: 3 },
  groups: [3, 14], camp_mix: { wolf: 3, wolf_pair: 2, wolf_pack: 1, elk: 2, elk_gold: 1.5, elk_gems: 1, gems: 2.5, gold: 2, gold_gems: 1 },
  camp_bias: { near: 1, spread: 3, contested: 1 }, camp_spawn_gap: 5, monoliths: { 0: 6, 1: 1 }, monolith_ring: 0.5, monolith_band: { mid: 1, contested: 2 }, shared_camp: 0.1,
  size: [30, 100], aspect: { square: 3, wide: 1 },
};

export const PRESETS = {
  'small-brawl': { doc: 'Small open map, 3 picks, few altars and nearby camps', size: [30, 36], aspect: 'square', picks: 3, terrain: { open: 1, scatter: 2 }, wall_density: [0.01, 0.04], altars: [1, 2], groups: [3, 6], camp_bias: 'near', spawn_size: 3 },
  'large-open': { doc: 'Large sparse map, 5 picks, spread camps', size: [80, 100], aspect: 'square', picks: 5, terrain: { open: 1, scatter: 2 }, wall_density: [0.01, 0.04], altars: [3, 6], groups: [10, 18], camp_bias: 'spread', spawn_size: 4 },
  maze: { doc: 'Rooms joined by narrow doors (chokepoints)', size: [40, 70], terrain: 'rooms', door_width: [2, 3], room_size: [6, 10], picks: [3, 4], holes: { none: 3, pits: 1 }, groups: [5, 10] },
  caves: { doc: 'Cellular-automaton caverns with carved tunnels', size: [40, 80], terrain: 'caves', bushes: { none: 1, blobs: 2 }, holes: { none: 2, lakes: 1 } },
  'many-camps': { doc: 'Dense jungle of 18-30 camp groups per side', size: [50, 75], terrain: 'scatter', groups: [18, 30], camp_spawn_gap: 4 },
  lanes: { doc: 'Long map with parallel lanes and crossings', size: [80, 100], aspect: 'lanes', terrain: 'lanes', spawn_place: 'edge', holes: 'none', bushes: { strips: 2, patches: 1 } },
  islands: { doc: 'Large lakes of holes crossed by carved bridges', size: [50, 80], terrain: { open: 1, scatter: 1 }, wall_density: [0.01, 0.04], holes: 'lakes', hole_amount: [0.2, 0.32], hole_cost: 0.6, carve_width: 2 },
  jungle: { doc: 'Heavy bush cover for vision games', max_bush_clusters: 40, size: [40, 70], bushes: { blobs: 2, patches: 1 }, bush_amount: [0.25, 0.4], terrain: { open: 1, scatter: 2 } },
  monolith: { doc: 'A monolith per side (often ringed by gem clusters)', size: [40, 64], monoliths: 1, monolith_ring: 0.7, groups: [4, 10] },
  fortress: { doc: 'Concentric rings with gated openings', size: [50, 80], aspect: 'square', terrain: 'rings', ring_gates: [2, 3], spawn_place: { corner: 2, edge: 1 }, door_width: [3, 4] },
  rows: { doc: 'Staggered parallel wall rows', size: [40, 70], terrain: 'rows', bushes: { strips: 1, blobs: 1 } },
  'altar-rich': { doc: 'Six to nine altars per side plus a shared one', size: [50, 80], altars: [6, 9], shared_altar: 1, altar_spacing: [5, 6] },
  'altar-poor': { doc: 'A single, contested altar per side', size: [40, 70], altars: 1, altar_near: 0, altar_bands: { contested: 1 }, shared_altar: 0 },
  'contested-centre': { doc: 'Shared camp group and altar straddling the centre', size: [40, 60], shared_camp: 1, shared_altar: 1, camp_bias: 'contested' },
  vaults: { doc: 'One or two walled pockets reachable only by teleport crystal', size: [40, 70], vaults: [1, 2] },
  tiny: { doc: '30x30, 5 picks, crowded', size: 30, aspect: 'square', picks: 5, groups: [3, 7] },
  huge: { doc: '100x100, many objectives', size: 100, aspect: 'square', picks: [4, 5], altars: [4, 8], groups: [14, 24] },
  random: { doc: 'Everything sampled from the full legal space' },
  'monolith-only': {
    doc: 'One to three monoliths per side are the only gem source; every other camp is gold (like the ladder map "contest")',
    size: [40, 70], picks: { 4: 1, 5: 3 }, terrain: { open: 2, scatter: 3, rows: 0.5 }, wall_density: [0.01, 0.08],
    holes: { none: 3, pits: 1, moat: 1 }, hole_amount: [0.01, 0.05], bushes: { none: 2, patches: 2, strips: 1 }, bush_amount: [0.01, 0.06],
    altars: [1, 3], altar_bands: { mid: 1, contested: 2 }, monoliths: [1, 3], monolith_ring: 0, groups: [4, 9], camp_mix: { gold: 3, gold_row: 1 }, shared_camp: 0, vaults: 0,
  },
  'shared-gems': {
    doc: 'One large self-mirrored gem group on the symmetry axis is the only gem source; every other camp is gold (like "stampede")',
    size: [44, 70], aspect: { square: 1, wide: 2 }, symmetry: { vertical: 2, horizontal: 2, rotational: 1 }, picks: { 3: 1, 4: 2, 5: 2 },
    terrain: { open: 2, scatter: 1, lanes: 0.5 }, wall_density: [0.01, 0.05], holes: { lakes: 2, moat: 1, pits: 1, none: 1 }, hole_amount: [0.05, 0.2],
    bushes: { strips: 2, patches: 2, blobs: 1 }, bush_amount: [0.05, 0.16], altars: [1, 3], groups: [3, 8], camp_mix: { gold: 3, gold_row: 1 },
    monoliths: 0, shared_camp: 0, shared_gems: true, shared_gold: [0, 2], vaults: 0,
  },
  classic: {
    doc: 'Like the competition maps: sparse wall lines, bush blocks, thin hole moats, counts scaled to size',
    size: [30, 90], aspect: { square: 5, wide: 1, lanes: 1 }, terrain: { scatter: 5, open: 1, rows: 1 }, wall_density: [0, 0.09], wall_length: [0.15, 0.45],
    holes: { none: 2, moat: 2, pits: 1 }, hole_amount: [0.01, 0.04], bushes: { patches: 3, strips: 2, none: 1 }, bush_amount: [0.01, 0.13], max_bush_clusters: 14,
    altars: [1, 4], groups: [4, 12], scale_counts: true, monoliths: { 0: 4, 1: 1 }, shared_camp: 0.15, vaults: { 0: 8, 1: 1 },
  },
};

function sampleValue(rng, v) {
  if (Array.isArray(v)) return Number.isInteger(v[0]) && Number.isInteger(v[1]) ? rng.int(v[0], v[1]) : rng.uniform(v[0], v[1]);
  if (v && typeof v === 'object') { const k = rng.weighted(v); return /^\d+$/.test(k) ? +k : k; }
  return v;
}

const KEEP_OBJECT = new Set(['camp_mix', 'altar_bands']);

export function sampleSpec(rng, preset, overrides = {}) {
  const src = { ...DEFAULTS, ...PRESETS[preset], ...overrides }, spec = { preset };
  for (const [k, v] of Object.entries(src)) {
    if (k === 'doc') continue;
    spec[k] = KEEP_OBJECT.has(k) && typeof v === 'object' && !Array.isArray(v) ? v : sampleValue(rng, v);
  }
  for (const k of ['spawn_bush', 'altar_near', 'shared_altar', 'shared_camp']) if (typeof spec[k] === 'number') spec[k] = rng.chance(spec[k]);
  if (typeof spec.camp_bias !== 'string') spec.camp_bias = 'spread';
  const n = spec.size;
  let W = n, H = n;
  if (spec.aspect === 'wide') { H = Math.max(30, Math.round(n * rng.uniform(0.55, 0.85))); }
  else if (spec.aspect === 'lanes') { H = rng.int(30, 40); }
  if (spec.aspect !== 'square' && rng.chance(0.5)) [W, H] = [H, W];
  spec.width = W; spec.height = H;
  if (spec.aspect === 'lanes') spec.symmetry = overrides.symmetry ?? (W > H ? rng.choice(['horizontal', 'rotational']) : rng.choice(['vertical', 'rotational']));
  const scale = W * H / 2500;
  if (preset === 'random' || spec.scale_counts) { spec.groups = Math.max(2, Math.round(spec.groups * Math.sqrt(scale))); spec.altars = Math.max(1, Math.min(8, Math.round(spec.altars * Math.sqrt(scale)))); }
  return spec;
}

export function generate(preset, seed, overrides = {}, attempts = 40) {
  let last;
  for (let attempt = 0; attempt < attempts; attempt++) {
    const rng = makeRng(`${preset}:${seed}:${attempt}`), spec = sampleSpec(rng, preset, overrides);
    try {
      const g = new Grid(spec.width, spec.height, spec.symmetry);
      g.picks = spec.picks;
      TERRAIN[spec.terrain](g, rng, spec);
      holes(g, rng, spec);
      bushes(g, rng, spec);
      g.symmetrize();
      if (spec.shared_gems) reserveShared(g, rng);
      pruneBushes(g, 4, spec.max_bush_clusters);
      placeSpawn(g, rng, spec);
      connect(g, rng, spec);
      placeVaults(g, rng, spec);
      placeAltars(g, rng, spec);
      placeCamps(g, rng, spec);
      const { errors } = validate(g);
      if (errors.length) throw new GenFail(errors[0]);
      const met = metrics(g);
      const why = gate(met, g, spec);
      if (why) throw new GenFail(why);
      g.meta = { preset, seed, attempt, overrides, spec, metrics: met };
      return g;
    } catch (e) {
      if (!(e instanceof GenFail)) throw e;
      last = e.message;
    }
  }
  throw new GenFail(`${preset}:${seed} failed after ${attempts} attempts (last: ${last})`);
}

function gate(met, g, spec) {
  if (met.reach_frac < 0.35) return `only ${Math.round(100 * met.reach_frac)}% walkable and reachable`;
  if (met.spawn_dist < Math.max(20, 0.45 * Math.max(g.W, g.H))) return `spawns ${met.spawn_dist} apart`;
  if (met.gems_side < 120) return `only ${met.gems_side} gems per side`;
  if (!met.altars) return 'no altars';
  if (spec.altar_zone && met.altar_zone !== spec.altar_zone) return `nearest altar in zone ${met.altar_zone}`;
  return null;
}

export { spawnFields, stillConnected, connect, TEMPLATES, tryGroup, candidates, BANDS };
