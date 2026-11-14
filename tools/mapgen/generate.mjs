import { ALTAR, BUSH, CAMP, GROUND, GenFail, Grid, HOLE, LEVELS, N4, WALL, makeRng, valueNoise } from './grid.mjs';
import { DESIGNS } from './design.mjs';
import * as TOPOLOGY from './topology.mjs';
import * as SCENARIOS from './scenarios.mjs';
import * as PARADIGMS from './paradigms.mjs';
import { KIND, SHAPES, TERRAIN_EXTRA } from './shapes.mjs';

export { GenFail };

const cheb = (ax, ay, bx, by) => Math.max(Math.abs(ax - bx), Math.abs(ay - by));
const rectDist = (s, x, y) => Math.max(Math.max(s.x - x, 0, x - (s.x + s.w - 1)), Math.max(s.y - y, 0, y - (s.y + s.h - 1)));

// ---- terrain ------------------------------------------------------------------------------
// A diagonal line also gets the orthogonal tile of each step: diagonal gaps block nothing.
function line(g, x0, y0, dx, dy, len, kind, thick = 1) {
  for (let k = 0; k < len; k++) for (let t = 0; t < thick; t++) {
    const x = x0 + dx * k + (dy ? t : 0), y = y0 + dy * k + (dx && !dy ? t : 0);
    if (g.in(x, y)) g.t[g.idx(x, y)] = kind;
    if (dx && dy && k + 1 < len && g.in(x + dx, y)) g.t[g.idx(x + dx, y)] = kind;
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

// The 2-tile frame open (POOL_FIT border_clear): the ladder keeps walls and holes off the edge more often than
// scattered terrain does. Winding barriers keep their ends (keep), which seal the detour they make; opened, over half
// their detours went. The frame is its own mirror, so the map stays symmetric.
function clearBorder(g, keep = null) {
  for (let y = 0; y < g.H; y++) for (let x = 0; x < g.W; x++) {
    const i = y * g.W + x;
    if ((x < 2 || y < 2 || x >= g.W - 2 || y >= g.H - 2) && (g.t[i] === WALL || g.t[i] === HOLE) && !keep?.[i]) g.t[i] = GROUND;
  }
}

function holes(g, rng, s) {
  if (s.holes === 'lakes') {
    const n = valueNoise(rng, g.W, g.H, rng.uniform(8, 18), 3), cut = quantile(n, 1 - (s.lake_amount ?? s.hole_amount));
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

// Calibration 2's tidy pass: fills leaky diagonals (two blockers touching only at a corner, which the walk slips
// between) and widens 1-wide gaps, both rare on the ladder (15% and 1% of maps against 39% and 17%). Tiles in `keep`
// (a mutated ladder map's own), camps, altars and spawns stay. Symmetric when the map is. `late` (once camps are
// placed) opens a corner instead of filling one, so the pass never cuts a way.
export function tidy(g, s, keep = null, late = false) {
  const { W, H } = g, blocked = i => g.t[i] === WALL || g.t[i] === HOLE, camps = g.camps.length ? g.campMask() : null;
  const spawn = g.spawn ? new Set([...g.spawnTiles(0), ...g.spawnTiles(1)]) : null, fixed = i => keep?.has(i) || camps?.[i] || spawn?.has(i) || g.t[i] === ALTAR;
  for (let pass = 0; pass < 4; pass++) {
    let changed = 0;
    if (s.unleak) for (let y = 0; y + 1 < H; y++) for (let x = 0; x + 1 < W; x++) {
      const a = y * W + x, b = a + 1, c = a + W, d = c + 1;
      if (late) {
        if (blocked(a) && blocked(d) && !blocked(b) && !blocked(c) && !fixed(a)) { g.set(x, y, GROUND); changed++; }
        else if (blocked(b) && blocked(c) && !blocked(a) && !blocked(d) && !fixed(b)) { g.set(x + 1, y, GROUND); changed++; }
      } else if (blocked(a) && blocked(d) && !blocked(b) && !blocked(c) && !fixed(b)) { g.set(x + 1, y, g.t[a]); changed++; }
      else if (blocked(b) && blocked(c) && !blocked(a) && !blocked(d) && !fixed(a)) { g.set(x, y, g.t[b]); changed++; }
    }
    if (s.unnarrow) for (let y = 0; y < H; y++) for (let x = 0; x < W; x++) {
      const i = y * W + x;
      if (blocked(i) || g.t[i] === ALTAR) continue;
      for (const [dx, dy] of [[1, 0], [0, 1]]) {
        const side = [[x - dx, y - dy], [x + dx, y + dy]], out = ([u, v]) => !g.in(u, v), shut = ([u, v]) => out([u, v]) || blocked(v * W + u);
        if (!side.every(shut)) continue;
        const open = side.filter(t => !out(t) && !fixed(t[1] * W + t[0]));
        if (open.length) { const [u, v] = open[(x + y) % open.length]; g.set(u, v, GROUND); changed++; }
      }
    }
    if (!changed) break;
  }
}

// Tiles of a map's leaky diagonals and 1-wide gaps (tidy's targets), so a mutation keeps the ladder map's own.
export function quirkTiles(g) {
  const { W, H } = g, blocked = (x, y) => !g.in(x, y) || g.t[y * W + x] === WALL || g.t[y * W + x] === HOLE, out = new Set();
  for (let y = 0; y < H; y++) for (let x = 0; x < W; x++) {
    if (x + 1 < W && y + 1 < H && ((blocked(x, y) && blocked(x + 1, y + 1) && !blocked(x + 1, y) && !blocked(x, y + 1)) || (blocked(x + 1, y) && blocked(x, y + 1) && !blocked(x, y) && !blocked(x + 1, y + 1))))
      for (const [u, v] of [[x, y], [x + 1, y], [x, y + 1], [x + 1, y + 1]]) out.add(v * W + u);
    if (!blocked(x, y)) for (const [dx, dy] of [[1, 0], [0, 1]]) if (blocked(x - dx, y - dy) && blocked(x + dx, y + dy))
      for (const [u, v] of [[x, y], [x - dx, y - dy], [x + dx, y + dy]]) if (g.in(u, v)) out.add(v * W + u);
  }
  return out;
}

function quantile(arr, q) {
  const s = Float32Array.from(arr).sort();
  return s[Math.min(s.length - 1, Math.max(0, Math.floor(q * s.length)))];
}

const TERRAIN = { open: () => {}, scatter, caves, rooms, lanes, rings, rows, ...TERRAIN_EXTRA, ...PARADIGMS.TERRAIN };

// The playable area: 1 inside the shape, 0 outside (void_kind), 2 in its core (core_kind). A tile
// is playable if it or its mirror is, so the mask is symmetric.
function shapeMask(g, rng, s) {
  if (!s.shape || s.shape === 'none') return null;
  const f = SHAPES[s.shape](rng, g, s), m = new Uint8Array(g.t.length);
  for (let y = 0; y < g.H; y++) for (let x = 0; x < g.W; x++) m[y * g.W + x] = f((2 * x - (g.W - 1)) / (g.W - 1), (2 * y - (g.H - 1)) / (g.H - 1), x, y);
  for (let i = 0; i < m.length; i++) {
    const j = g.mirror(i), v = m[i] === 1 || m[j] === 1 ? 1 : m[i] === 2 || m[j] === 2 ? 2 : 0;
    m[i] = m[j] = v;
  }
  const play = m.reduce((n, v) => n + (v === 1), 0) / m.length;
  if (play < 0.25) throw new GenFail(`shape leaves ${Math.round(100 * play)}% playable`);
  return m;
}

function applyMask(g, m, s) {
  for (let i = 0; i < m.length; i++) if (m[i] !== 1) g.t[i] = m[i] === 2 ? KIND[s.core_kind] : KIND[s.void_kind];
}

// ---- spawn and connectivity ----------------------------------------------------------------
function placeSpawn(g, rng, s) {
  const [w, h] = spawnWH(rng, s), { W, H } = g, inset = rng.int(0, 3);
  let x, y;
  const place = s.spawn_place;
  const edgeX = () => inset, midY = () => Math.floor(H / 2) - (h >> 1) + rng.int(-Math.floor(H / 6), Math.floor(H / 6));
  const farX = () => Math.round(W * rng.uniform(0.1, 0.22)), farY = () => Math.round(H * rng.uniform(0.1, 0.22));
  if (g.sym === 'horizontal') {
    x = place === 'inset' ? farX() : edgeX();
    y = place === 'edge' || place === 'inset' ? midY() : (rng.chance(0.5) ? inset : H - h - inset);
  } else if (g.sym === 'vertical') {
    y = place === 'inset' ? farY() : inset;
    x = place === 'edge' || place === 'inset' ? Math.floor(W / 2) - (w >> 1) + rng.int(-Math.floor(W / 6), Math.floor(W / 6)) : (rng.chance(0.5) ? inset : W - w - inset);
  } else if (place === 'corner') { x = inset; y = rng.chance(0.5) ? inset : H - h - inset; }
  else if (place === 'edge') { if (W >= H) { x = inset; y = midY(); } else { y = inset; x = Math.floor(W / 2) - (w >> 1) + rng.int(-Math.floor(W / 6), Math.floor(W / 6)); } }
  else { x = farX(); y = farY(); }
  x = Math.max(0, Math.min(W - w, x)); y = Math.max(0, Math.min(H - h, y));
  if (nearReserved(g, x, y, w, h)) throw new GenFail('spawn too close to the shared group');
  g.spawn = { x, y, w, h };
  const [ax, ay] = g.mirrorXY(x, y), [bx, by] = g.mirrorXY(x + w - 1, y + h - 1);
  const gap = Math.max(Math.abs(Math.min(ax, bx) - x) - w, Math.abs(Math.min(ay, by) - y) - h) + 1;
  if (gap < (s.spawn_floor ?? Math.max(16, 0.45 * Math.min(W, H)))) throw new GenFail(`spawns too close (${gap})`);
  const c = s.spawn_clear ?? 2;
  for (let yy = y - c; yy < y + h + c; yy++) for (let xx = x - c; xx < x + w + c; xx++)
    if (g.in(xx, yy) && g.get(xx, yy) !== BUSH) g.set(xx, yy, GROUND);
  if (!s.spawn_bush) for (let yy = y; yy < y + h; yy++) for (let xx = x; xx < x + w; xx++) g.set(xx, yy, GROUND);
}

const RESERVED_GAP = 8;

// Spawn width and height: spawn_dims ('4x3', '5x2'; either way round) or a square of spawn_size.
// Any rectangle of 9-16 tiles loads (1x9 and 2x6 too; probed 2026-10-30), though the ladder has only 3x3, 4x4, 4x3 and 5x2.
const spawnWH = (rng, s) => { if (!s.spawn_dims || s.spawn_dims === 'none') return [s.spawn_size, s.spawn_size]; const [w, h] = String(s.spawn_dims).split('x').map(Number); return rng.chance(0.5) ? [w, h] : [h, w]; };

function nearReserved(g, x, y, w, h = w) {
  if (!g.reserved) return false;
  for (const i of g.reserved) if (rectDist({ x, y, w, h }, i % g.W, Math.floor(i / g.W)) < RESERVED_GAP) return true;
  return false;
}

// Spawn inside the playable area by mode: 'far' (near the largest gap to its mirror), 'corner',
// 'mid' (about half that gap), 'near' (close spawns) or 'touch' (a gap of 1-4 tiles to its mirror).
function placeSpawnMode(g, rng, s) {
  const [w, h] = spawnWH(rng, s), { W, H } = g, m = g.mask, cands = [];
  for (let y = 0; y + h <= H; y++) for (let x = 0; x + w <= W; x++) {
    let ok = true;
    for (let yy = y - 1; ok && yy <= y + h; yy++) for (let xx = x - 1; xx <= x + w; xx++) {
      if (!g.in(xx, yy)) continue;
      const i = g.idx(xx, yy);
      if ((m && m[i] !== 1) || g.reserved?.has(i)) { ok = false; break; }
    }
    if (!ok || nearReserved(g, x, y, w, h)) continue;
    const [ax, ay] = g.mirrorXY(x, y), [bx, by] = g.mirrorXY(x + w - 1, y + h - 1);
    const gap = Math.max(Math.abs(Math.min(ax, bx) - x) - w, Math.abs(Math.min(ay, by) - y) - h) + 1;
    if (gap >= (s.spawn_mode === 'touch' ? 1 : 6)) cands.push({ x, y, gap });
  }
  if (!cands.length) throw new GenFail('no spawn site');
  const max = Math.max(...cands.map(c => c.gap)), corner = c => Math.min(...[[0, 0], [W - w, 0], [0, H - h], [W - w, H - h]].map(([cx, cy]) => Math.max(Math.abs(c.x - cx), Math.abs(c.y - cy))));
  let pool;
  if (s.spawn_mode === 'far') pool = cands.filter(c => c.gap >= 0.88 * max);
  else if (s.spawn_mode === 'corner') pool = cands.filter(c => c.gap >= 0.8 * max).sort((p, q) => corner(p) - corner(q) || p.y - q.y || p.x - q.x).slice(0, 10);
  else if (s.spawn_mode === 'mid') pool = cands.filter(c => c.gap >= 0.45 * max && c.gap <= 0.7 * max);
  else if (s.spawn_mode === 'touch') pool = cands.filter(c => c.gap <= 4);
  else pool = cands.filter(c => c.gap >= Math.max(12, 0.15 * Math.min(W, H)) && c.gap <= Math.max(16, 0.32 * max));
  if (!pool.length) throw new GenFail(`no ${s.spawn_mode} spawn site`);
  const { x, y } = rng.choice(pool);
  g.spawn = { x, y, w, h };
  const c = s.spawn_clear ?? 1;
  for (let yy = y - c; yy < y + h + c; yy++) for (let xx = x - c; xx < x + w + c; xx++)
    if (g.in(xx, yy) && g.get(xx, yy) !== BUSH) g.set(xx, yy, GROUND);
  if (!s.spawn_bush) for (let yy = y; yy < y + h; yy++) for (let xx = x; xx < x + w; xx++) g.set(xx, yy, GROUND);
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
// Travel costs from each spawn (team B's spawn is impassable to team A and vice versa): walking,
// plus dashes or teleport crystals up to `level` (by default the map's access, g.access).
function spawnFields(g, blockers, level = LEVELS.indexOf(g.access ?? 'walk'), teams = 'AB') {
  const pass = g.walkable(blockers), a = g.spawnTiles(0), b = g.spawnTiles(1), n = g.t.length;
  let block = null;
  if (level) {
    block = new Uint8Array(n);
    for (let i = 0; i < n; i++) if (g.t[i] === WALL) block[i] = 1;
    if (blockers) for (let i = 0; i < n; i++) if (blockers[i]) block[i] = 1;
  }
  const field = (own, other) => {
    const p = pass.slice();
    for (const i of other) p[i] = 0;
    if (!level) return g.bfs(own, p);
    const m = block.slice();
    for (const i of other) m[i] = 1;
    return g.travel(own, p, m, level);
  };
  return { dA: teams.includes('A') ? field(a, b) : null, dB: teams.includes('B') ? field(b, a) : null, pass };
}

// Team A's travel fields with camps passable (they can be killed): walking, with dashes, and with
// teleport crystals as well.
function accessFields(g) {
  return LEVELS.map((_, l) => spawnFields(g, null, l));
}

// The least access (0 walk, 1 dash, 2 teleport, 3 none) that reaches any of the tiles or next to
// one. A camp's own tile counts: a camp alone on a one-tile island is shot from range, then its
// tile is free to land on.
function levelOf(g, fields, tiles, team = 'dA') {
  for (let l = 0; l < fields.length; l++) if (tiles.some(i => fields[l][team][i] >= 0 || g.reachNear(fields[l][team], i % g.W, Math.floor(i / g.W)) >= 0)) return l;
  return 3;
}

// Contest ratio of a tile: 0 at team A's spawn, 0.5 equidistant, 1 at team B's.
const ratio = (dA, dB, i) => dA[i] < 0 || dB[i] < 0 ? -1 : dA[i] / Math.max(1, dA[i] + dB[i]);

const BANDS = { near: [0.06, 0.26], mid: [0.22, 0.42], contested: [0.38, 0.5], central: [0.4, 0.5], any: [0.06, 0.5] };

// camp_bands (a weights object over near, mid, contested) overrides the bias's weights.
function bandFor(rng, bias, weights) {
  const w = weights ?? { near: { near: 6, mid: 3, contested: 1 }, spread: { near: 3, mid: 4, contested: 3 }, contested: { near: 1, mid: 3, contested: 6 } }[bias];
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
  // Where camps plug a route (g.gated), they count as killable: only reachability matters.
  const camps = g.campMask(), blocked = spawnFields(g, g.gated ? null : camps);
  const a = g.spawnTiles(0), b = g.spawnTiles(1);
  if (!b.some(i => g.reachNear(blocked.dA, i % g.W, Math.floor(i / g.W)) >= 0)) return false;
  // Walkable tiles neither spawn reaches past the camps: a pocket if team A reaches them with camps open.
  const pass = g.gated ? blocked.pass : g.walkable(), cut = [];
  for (let i = 0; i < g.t.length; i++) {
    if (g.t[i] === ALTAR && !g.vaults.has(i) && g.reachNear(blocked.dA, i % g.W, Math.floor(i / g.W)) < 0) return false;
    if (!g.gated && pass[i] && !camps[i] && blocked.dA[i] < 0 && blocked.dB[i] < 0 && !a.includes(i) && !b.includes(i)) cut.push(i);
  }
  if (cut.length) { const dA = spawnFields(g, null, undefined, 'A').dA; if (cut.some(i => dA[i] >= 0)) return false; }
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

// altar_mode: 'spread' (altar_near and altar_bands), 'own' (nearest on own side), 'central' (all in
// the middle band), 'contested', 'corners' (farthest from the map centre), 'single' (one
// self-mirrored altar near the centre, else one central pair) or 'many' (6-12 per side).
function placeAltars(g, rng, s) {
  const placed = [], mode = s.altar_mode ?? 'spread';
  for (let i = 0; i < g.t.length; i++) if (g.t[i] === ALTAR && i <= g.mirror(i)) placed.push([i % g.W, Math.floor(i / g.W)]);
  const had = placed.length;
  const camps = g.campMask(), ag = s.camp_altar_gap ?? 1, campNear = (x, y) => { for (let dy = -ag; dy <= ag; dy++) for (let dx = -ag; dx <= ag; dx++) if (g.in(x + dx, y + dy) && camps[(y + dy) * g.W + x + dx]) return true; return false; };
  // Designed maps and vaults place camps before the altars: an altar never lands on or (by camp_altar_gap) beside one.
  // altar_open (calibration 2): walkable neighbours an altar needs (the ladder's are rarely cramped).
  const pass = !!s.altar_open, open = (x, y) => { let n = 0; for (let dy = -1; dy <= 1; dy++) for (let dx = -1; dx <= 1; dx++) n += (dx || dy) && g.in(x + dx, y + dy) && (g.get(x + dx, y + dy) === GROUND || g.get(x + dx, y + dy) === BUSH); return n; };
  const free = (x, y) => g.get(x, y) === GROUND && !campNear(x, y) && rectDist(g.spawn, x, y) >= 3 && rectDist(g.spawn, ...g.mirrorXY(x, y)) >= 3 && !g.reserved?.has(g.idx(x, y)) && !g.noCamp?.has(g.idx(x, y))
    && [...placed, ...placed.map(([px, py]) => g.mirrorXY(px, py))].every(([px, py]) => cheb(px, py, x, y) >= s.altar_spacing) && (!pass || open(x, y) >= s.altar_open);
  if (s.calib >= 2) {
    // shared_altars self-mirrored altars: the first near the centre, the rest along the axis.
    const cx = (g.W - 1) / 2, cy = (g.H - 1) / 2, self = [];
    for (let y = 0; y < g.H; y++) for (let x = 0; x < g.W; x++) { const [mx, my] = g.mirrorXY(x, y); if (mx === x && my === y) self.push([x, y]); }
    for (let k = 0; k < (s.shared_altars ?? 0); k++) {
      const r = (k ? 0.3 : 0.2) * Math.max(g.W, g.H) + 1;
      for (const [x, y] of rng.shuffle(self.filter(([x, y]) => cheb(x, y, cx, cy) <= r))) {
        // Terrain in the way is cleared (the 3x3 round the altar), as the ladder's centre altars stand in the open.
        const box = [], saved = g.t.slice();
        for (let dy = -1; dy <= 1; dy++) for (let dx = -1; dx <= 1; dx++) if (g.in(x + dx, y + dy) && [WALL, HOLE, BUSH].includes(g.get(x + dx, y + dy)) && !g.reserved?.has(g.idx(x + dx, y + dy)) && !g.vaults.has(g.idx(x + dx, y + dy))) box.push([x + dx, y + dy]);
        box.forEach(([u, v]) => g.set(u, v, GROUND));
        if (free(x, y)) {
          g.set(x, y, ALTAR);
          if (stillConnected(g)) { placed.push([x, y]); break; }
        }
        g.t = saved;
      }
    }
  } else if (s.shared_altar || mode === 'single') {
    const cx = (g.W - 1) / 2, cy = (g.H - 1) / 2, self = [];
    for (let y = 0; y < g.H; y++) for (let x = 0; x < g.W; x++) { const [mx, my] = g.mirrorXY(x, y); if (mx === x && my === y && cheb(x, y, cx, cy) <= Math.min(g.W, g.H) / (mode === 'single' ? 3 : 4)) self.push([x, y]); }
    for (const [x, y] of rng.shuffle(self)) {
      if (!free(x, y)) continue;
      g.set(x, y, ALTAR);
      if (stillConnected(g)) { placed.push([x, y]); break; }
      g.set(x, y, GROUND);
    }
  }
  let ext = null, cut = 0;
  if (mode === 'corners') {
    const f = spawnFields(g);
    ext = new Float32Array(g.t.length);
    for (let i = 0; i < ext.length; i++) if (f.dA[i] >= 0) { const x = i % g.W, y = (i - x) / g.W; ext[i] = Math.hypot((2 * x - g.W + 1) / (g.W - 1), (2 * y - g.H + 1) / (g.H - 1)); cut = Math.max(cut, ext[i]); }
    cut *= 0.8;
  }
  const v2 = s.calib >= 2, fallback = v2 && !s.altars && placed.length === had;
  const n = mode === 'single' || fallback ? ((v2 ? placed.length > had : placed.length) ? 0 : 1) : s.altars;
  for (let k = 0; k < n; k++) {
    const f = spawnFields(g);
    let band = BANDS.any, pred = free;
    if (mode === 'central' || mode === 'single' || fallback) band = BANDS.central;
    else if (mode === 'hub') { band = BANDS.central; const r = 0.3 * Math.max(g.W, g.H) / 2, cx = (g.W - 1) / 2, cy = (g.H - 1) / 2; pred = (x, y, i) => free(x, y) && cheb(x, y, cx, cy) <= r; }
    // altar_twin: the first pair side by side across the axis (12% of ladder maps have adjacent altars).
    if (v2 && k === 0 && s.altar_twin && band[1] >= 0.5) { const p0 = pred; pred = (x, y, i) => p0(x, y, i) && cheb(x, y, ...g.mirrorXY(x, y)) <= 2; }
    else if (mode === 'own') band = k === 0 ? BANDS.near : BANDS[rng.weighted({ near: 2, mid: 2, contested: 1 })];
    else if (mode === 'contested') band = [0.3, 0.5];
    else if (mode === 'corners') pred = (x, y, i) => free(x, y) && ext[i] >= cut;
    else if (mode === 'spread') band = k === 0 && s.altar_near ? BANDS.near : BANDS[rng.weighted(s.altar_bands)];
    let ok = false;
    for (const i of candidates(g, rng, f, band, pred).slice(0, 40)) {
      const x = i % g.W, y = (i - x) / g.W, [mx, my] = g.mirrorXY(x, y);
      if (mx === x && my === y) continue;
      g.set(x, y, ALTAR);
      if (stillConnected(g)) { placed.push([x, y]); ok = true; break; }
      g.set(x, y, GROUND);
    }
    if (!ok && k === 0 && (v2 ? !placed.length : !had)) throw new GenFail('no altar placement');
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
  monolith_gold: () => [['monolith', 1, 1], ...[[0, 0], [1, 0], [2, 0], [0, 1], [2, 1], [0, 2], [1, 2], [2, 2]].map(([x, y]) => ['gold_cluster', x, y])],
  gem: () => [['gem_cluster', 0, 0]],
  elk_pair: rng => rng.chance(0.5) ? [['elk', 0, 0], ['elk', 1, 0]] : [['elk', 0, 0], ['elk', 0, 1], ['gem_cluster', 1, 0]],
  golem: () => [['golem', 0, 0]],
  golem_gold: rng => rng.chance(0.5) ? [['golem', 1, 0], ['gold_cluster', 0, 0], ['gold_cluster', 2, 0]] : [['golem', 0, 0], ['gold_cluster', 1, 0], ['gold_cluster', 0, 1]],
  golem_pair: rng => rng.chance(0.5) ? [['golem', 0, 0], ['golem', 1, 0]] : [['golem', 0, 0], ['golem', 1, 0], ['gem_cluster', 0, 1], ['gem_cluster', 1, 1]],
  golem_gems: rng => rng.chance(0.5) ? [['golem', 1, 1], ['gem_cluster', 0, 1], ['gem_cluster', 2, 1], ['gem_cluster', 1, 0], ['gem_cluster', 1, 2]] : [['golem', 0, 0], ['gem_cluster', 1, 0], ['gem_cluster', 2, 0]],
  golem_wolves: rng => rng.chance(0.5) ? [['wolf', 0, 0], ['golem', 1, 0], ['wolf', 2, 0]] : [['golem', 0, 0], ['wolf', 1, 0], ['wolf', 0, 1]],
  monolith_ring: () => [['monolith', 1, 1], ...[[0, 0], [1, 0], [2, 0], [0, 1], [2, 1], [0, 2], [1, 2], [2, 2]].map(([x, y]) => ['gem_cluster', x, y])],
  // Composed groups, up to the ladder's largest (vault 49, the-pack 48, yellow-brick-road 30 cells).
  poly: rng => typed(rng, polyomino(rng, rng.int(4, 14), 0)),
  snake: rng => typed(rng, polyomino(rng, rng.int(5, 16), 1)),
  carpet: rng => { const w = rng.int(3, 6), h = rng.int(2, 5), out = []; for (let y = 0; y < h; y++) for (let x = 0; x < w; x++) out.push([x, y]); return typed(rng, out, rng.weighted({ clusters: 3, gems: 1, gold: 1 })); },
  ring: rng => { const w = rng.int(3, 6), h = rng.int(3, 6), out = []; for (let y = 0; y < h; y++) for (let x = 0; x < w; x++) if (!x || !y || x === w - 1 || y === h - 1) out.push([x, y]); return typed(rng, out); },
  pack: rng => typed(rng, polyomino(rng, rng.int(15, 32), rng.uniform(0, 0.6)), rng.weighted({ wolves: 3, beasts: 1, mixed: 1 })),
};

// A random polyomino of n cells from (0, 0); `thin` (0-1) is how strongly it avoids cells with two
// or more neighbours already in it, from blobs (0) to snakes (1).
function polyomino(rng, n, thin) {
  const cells = [[0, 0]], has = new Set(['0,0']), N = [[1, 0], [-1, 0], [0, 1], [0, -1]];
  for (let guard = 0; cells.length < n && guard < n * 60; guard++) {
    const [cx, cy] = thin >= 1 ? cells.at(-1) : rng.choice(cells), [dx, dy] = rng.choice(N), x = cx + dx, y = cy + dy;
    if (has.has(`${x},${y}`)) continue;
    if (N.filter(([ax, ay]) => has.has(`${x + ax},${y + ay}`)).length > 1 && rng.chance(Math.max(thin, 0.05))) continue;
    cells.push([x, y]); has.add(`${x},${y}`);
  }
  return cells;
}

// Members for a composed group's cells, by palette: wolves, beasts (wolves, Elk, a Golem or two),
// clusters (gem and gold), gems, gold or mixed. At most 3 Golems and one Monolith.
function typed(rng, cells, palette = rng.weighted({ wolves: 2, beasts: 1.5, clusters: 1.5, mixed: 2 })) {
  const P = { wolves: { wolf: 8, gem_cluster: 1, gold_cluster: 1 }, beasts: { wolf: 4, elk: 3, golem: 0.6 }, clusters: { gem_cluster: 1, gold_cluster: 1 }, gems: { gem_cluster: 1 }, gold: { gold_cluster: 1 },
    mixed: { wolf: 3, elk: 1.5, golem: 0.3, monolith: 0.08, gem_cluster: 2, gold_cluster: 1.5 } }[palette], left = { golem: 3, monolith: 1 };
  return cells.map(([x, y]) => { let t = rng.weighted(P); if (left[t] === 0) t = 'wolf'; else if (t in left) left[t]--; return [t, x, y]; });
}

// Ladder group make-ups (2026-11-05, 128 maps; share of a map's groups, maps weighted equally, in %): W wolf, E elk,
// G golem, g gem cluster, d gold cluster; 'big:P' a composed group of 9-30 cells typed by palette P. Weights are
// raised for the big and guarded make-ups, which fail placement more often than single clusters.
const LADDER_GROUPS = {
  dd: 7.6, Wd: 7.5, g: 5, d: 5.3, Wg: 5.2, Wdd: 4.2, ggg: 2.8, W: 2.6, Wgg: 3.2, gg: 2, WWd: 2.5, ddd: 2.2, WWdd: 2.6, Edg: 2, gggg: 1.6,
  Wddd: 1.6, WWdg: 1.5, Wdg: 1.3, Egggg: 1.4, Egg: 1.3, Eddd: 1.2, WWgg: 1.2, Wggg: 1.1, ggggg: 1, Edd: 1.1, WWg: 1, Eggg: 1, Wdddd: 1, Eg: 0.8,
  WWggg: 0.9, dddd: 0.7, EEgg: 0.8, Eddg: 0.7, EEdd: 0.7, Edddd: 0.7, EEdg: 0.7, Edgg: 0.6, WW: 0.4, EWddg: 0.6, WWWdd: 0.5, Ed: 0.4,
  Eggggg: 0.5, gggggg: 0.4, Eddgg: 0.4, Ggggg: 0.8, Edddg: 0.4, WWWWdddd: 0.4, G: 0.5, Gddgg: 0.7, Gdd: 0.5, WWgggg: 0.4,
  'big:guarded': 2, 'big:gems': 0.4, 'big:gold': 0.3,
};
// Gem-only economies (adgato-gemcombat1-5, 04gem-caverns, 04gem-rush): gem clusters alone, no gold source at all.
const GEM_GROUPS = { g: 3, gg: 2, ggg: 2, gggg: 2, ggggg: 1, gggggg: 0.6, 'big:gems': 0.6 };
// Self-mirrored groups on the symmetry axis (the ladder's shared groups): their make-up across the axis.
const SHARED_GROUPS = { gems: 4, guarded: 3.5, gold: 1.2, boss: 1, big: 1 };
// Calibration 3's: fewer gem-only and more boss and big ones (the ladder's 115 shared groups: guarded 43%, gems 30%,
// boss 18%, gold 9%; half of them 4-7 cells, 9% 20 or more).
const SHARED_GROUPS_V3 = { gems: 3, guarded: 3.5, gold: 1, boss: 1.8, big: 2.2 };
// Groups 1-3 tiles from a spawn (17% of ladder maps: mostly gold clusters, sometimes wolf-guarded).
const HOME_GROUPS = { d: 2, dd: 3, ddd: 0.6, g: 1, Wd: 1.2, Wdd: 0.8, Wg: 0.5, Eddd: 0.3 };
const LETTER = { W: 'wolf', E: 'elk', G: 'golem', M: 'monolith', g: 'gem_cluster', d: 'gold_cluster' };

// Calibration 4's make-ups: the 40 05 maps of 2026-11-12 (share of a map's team A groups, maps weighted equally, in %;
// research/notes/ideas-2026-11-12/ladderv3/groups05.mjs). Mostly one monster guarding a compact block of clusters; 'big:'
// is 10 cells or more here. Monolith groups come from `monoliths` (placed mid-map), not this table.
const GROUPS_05 = {
  Wgg: 7.9, 'big:guarded': 5.9, Wddd: 4.5, Wdd: 4.3, Wggg: 3.4, g: 2.9, WWdd: 2.9, ggggggggg: 2.7, d: 2.6, Eddd: 2.6, WWd: 2.4, Egggg: 2,
  Edddd: 2, Wd: 2, ggg: 1.7, Wg: 1.7, Eggg: 1.7, gg: 1.5, Wdg: 1.4, Wdggg: 1.4, WWgg: 1.3, G: 1.3, Egg: 1.3, Edggg: 1.3, EWWgggg: 1.2,
  EWWWWWddg: 1.2, Wdddd: 1.2, WWWWddddd: 1.2, Ed: 1.2, Ggggg: 1.2, gggg: 1.1, WWg: 1, WWdddd: 1, EEggggg: 1, Egggggggg: 1, W: 0.9,
  WWddd: 0.8, WWWWWd: 0.8, WWWWW: 0.8, Edddddddd: 0.8, dd: 0.8, WWdg: 0.8, EWddd: 0.8, Wddddd: 0.7, Eggggg: 0.7, Wdgg: 0.6,
  WWWddddd: 0.6, EEWdddddd: 0.6, EEdddddd: 0.6, WWWdd: 0.6, EEdddg: 0.6, EWWWddd: 0.5, EWggggggg: 0.5, Ggggggggg: 0.5, EEddddddd: 0.5,
  Ggggggg: 0.5, EEdggg: 0.4, Edd: 0.4, E: 0.4, WWdgg: 0.3, EEgggg: 0.3, dggg: 0.3, Wddgg: 0.3, Gggggggg: 0.3, Wgggg: 0.3, Egggggg: 0.3,
  Eddg: 0.3, EWWggggg: 0.2, EWdd: 0.2, Gg: 0.2, gggggg: 0.2, Gggggg: 0.2, WWggg: 0.2, EEgggggg: 0.2, EEgg: 0.2, WWddgg: 0.2, Gdddd: 0.2,
  WWdddddd: 0.2, Edddgg: 0.2, WW: 0.2, Gddgggg: 0.2, WWgggg: 0.2, 'big:gold': 0.2, ddd: 0.2,
};

// Ladder maps differ in their groups more than independent draws would: singletons cluster on some maps (43% have
// none, 9% are mostly singletons), and some maps are nearly all big groups or all clusters. Per map, single_mult
// scales the one-cell make-ups, big_mult those of 3 cells or more, cluster_mult the cluster-only ones.
// Calibration 3's ball_mult scales the gem-only make-ups of 3 or more cells and gold_mult the gold-only ones (the
// ladder's gem balls sit on few maps, and half its maps have no gold-only group).
const TABLES = new Map();
const groupTable = (single = 1, big = 1, cl = 1, ball = 1, gold = 1, comp = 1, base = LADDER_GROUPS) => {
  const key = `${base === LADDER_GROUPS ? '' : '05|'}${single}|${big}|${cl}|${ball}|${gold}|${comp}`;
  if (!TABLES.has(key)) TABLES.set(key, Object.fromEntries(Object.entries(base).map(([k, w]) => {
    const n = k.startsWith('big:') ? 9 : k.length, clusters = k.startsWith('big:') ? k !== 'big:guarded' : /^[gd]+$/.test(k);
    const gemBall = n >= 3 && (k === 'big:gems' || /^g+$/.test(k)), goldOnly = k === 'big:gold' || /^d+$/.test(k);
    // On the 05 maps pairs bunch with the singletons: 55% of maps have neither.
    const small = n === 1 || (n === 2 && base === GROUPS_05);
    return [k, w * (small ? +single : 1) * (n >= 3 ? +big : 1) * (clusters ? +cl : 1) * (gemBall ? +ball : 1) * (goldOnly ? +gold : 1) * (k.startsWith('big:') ? +comp : 1)];
  })));
  return TABLES.get(key);
};

// Calibration 3's group shapes: the ladder's (2026-11-08, 128 maps, team A's groups of 3-9 cells under the 8
// symmetries, in %): designed blocks, not random polyominoes (2x2 squares, pluses, 2x3 and 3x3 blocks, rings).
const LADDER_SHAPES = {
  3: { '##/#.': 67, '###': 33 },
  4: { '##/##': 71, '###/.#.': 12, '####': 6, '##./.##': 5, '###/#..': 5 },
  5: { '.#./###/.#.': 61, '###/##.': 31, '###/#../#..': 3, '###/#.#': 2, '#####': 2 },
  6: { '###/###': 82, '###/##./#..': 5, '##./###/.#.': 5, '####/.##.': 5, '.#../####/.#..': 3 },
  7: { '###/###/.#.': 47, '##./###/.##': 40, '###/#.#/##.': 7, '####/###.': 7 },
  8: { '.##./####/.##.': 23, '####/####': 23, '###/#.#/###': 23, '###/###/##.': 15, '#####/.###.': 8, '###/###/#.#': 8 },
  9: { '###/###/###': 1 },
};
// Calibration 4's: the 05 maps' (team A's groups of 3-9 cells), blocks almost without exception.
const SHAPES_05 = {
  3: { '##/#.': 99, '###': 1 },
  4: { '##/##': 95, '###/.#.': 5 },
  5: { '.#./###/.#.': 94, '###/##.': 6 },
  6: { '###/###': 95, '##./###/.#.': 5 },
  7: { '###/###/.#.': 1 },
  8: { '####/####': 43, '###/###/##.': 43, '.##./####/.##.': 14 },
  9: { '###/###/###': 1 },
};
// Per map, line_mult scales the one-row shapes: the ladder's lines sit on few maps (most have none).
const SHAPE_TABLES = new Map();
function shapeTable(n, line = 1, base = LADDER_SHAPES) {
  const key = `${base === LADDER_SHAPES ? '' : '05|'}${n}|${line}`;
  if (!SHAPE_TABLES.has(key)) SHAPE_TABLES.set(key, base[n] && Object.fromEntries(Object.entries(base[n]).map(([k, w]) => [k, w * (k.includes('/') ? 1 : +line)])));
  return SHAPE_TABLES.get(key);
}
// Cells of a shape string, under one of the 8 symmetries.
function shapeCells(rng, pattern) {
  const t = rng.int(0, 7), out = [];
  pattern.split('/').forEach((row, y) => [...row].forEach((ch, x) => {
    if (ch !== '#') return;
    let a = t & 1 ? -x : x, b = t & 2 ? -y : y;
    if (t & 4) [a, b] = [b, a];
    out.push([a, b]);
  }));
  return out;
}
// Groups of 10 or more: blocks of 3-5 by 2-5 with up to 4 corners cut (the ladder's are 85% filled), or now and then
// a cluster line (01yellow-brick-road, 04lines).
function bigCells(rng, line) {
  if (line && rng.chance(0.12)) return Array.from({ length: rng.int(8, 30) }, (_, k) => [k, 0]);
  let w, h;
  do { w = rng.int(3, 5); h = rng.int(2, 5); } while (w * h < 10);
  const cut = new Set(rng.shuffle([[0, 0], [w - 1, 0], [0, h - 1], [w - 1, h - 1]].map(String)).slice(0, Math.min(rng.int(0, 4), w * h - 10))), out = [];
  for (let y = 0; y < h; y++) for (let x = 0; x < w; x++) if (!cut.has(`${x},${y}`)) out.push([x, y]);
  return out;
}
// Monsters on the best-connected cells (the middle of a line, plus or block, the corner of an L), clusters around.
function placeMembers(rng, cells, types) {
  const has = new Set(cells.map(String)), deg = ([x, y]) => N4.filter(([dx, dy]) => has.has(`${x + dx},${y + dy}`)).length;
  const order = rng.chance(0.8) ? rng.shuffle(cells.slice()).sort((a, b) => deg(b) - deg(a)) : rng.shuffle(cells.slice());
  const mons = types.filter(t => !t.endsWith('_cluster')), rest = rng.shuffle(types.filter(t => t.endsWith('_cluster')));
  return order.map(([x, y], k) => [k < mons.length ? mons[k] : rest[k - mons.length], x, y]);
}

// A group from a make-up string ('WWdd': a blob of 4 cells, the members on random cells; calibration 3: a ladder
// shape, monsters inside), or 'big:P'.
function composed(rng, make, s) {
  if (s?.calib >= 3) {
    if (make.startsWith('big:')) {
      // The ladder has 0.7 groups of 6-9 cells a side and 0.09 of 10 or more (not shared). Calibration 4's 'big:' is
      // 10 or more only (its table lists the 6-9 cell make-ups).
      const pal = make.slice(4), cells = s.calib >= 4 ? bigCells(rng, pal === 'gold') : rng.chance(0.75) ? shapeCells(rng, rng.weighted(LADDER_SHAPES[rng.weighted({ 6: 30, 7: 20, 8: 20, 9: 30 })])) : bigCells(rng, pal === 'gold');
      const P = { guarded: { gem_cluster: 4, gold_cluster: 3, wolf: 1, elk: 0.6, golem: 0.15 }, gems: { gem_cluster: 1 }, gold: { gold_cluster: 1 } }[pal], left = { golem: 3 };
      return placeMembers(rng, cells, cells.map(() => { let t = rng.weighted(P); if (left[t] === 0) t = 'gem_cluster'; else if (t in left) left[t]--; return t; }));
    }
    const types = [...make].map(c => LETTER[c]), table = shapeTable(types.length, s.line_mult, s.calib >= 4 ? SHAPES_05 : LADDER_SHAPES);
    return placeMembers(rng, table ? shapeCells(rng, rng.weighted(table)) : polyomino(rng, types.length, rng.uniform(0, 0.4)), types);
  }
  if (make.startsWith('big:')) {
    const pal = make.slice(4), cells = polyomino(rng, rng.int(9, 30), rng.uniform(0, 0.5));
    const P = { guarded: { gem_cluster: 4, gold_cluster: 3, wolf: 1, elk: 0.6, golem: 0.15 }, gems: { gem_cluster: 1 }, gold: { gold_cluster: 1 } }[pal], left = { golem: 3 };
    return cells.map(([x, y]) => { let t = rng.weighted(P); if (left[t] === 0) t = 'gem_cluster'; else if (t in left) left[t]--; return [t, x, y]; });
  }
  const types = rng.shuffle([...make].map(c => LETTER[c])), cells = polyomino(rng, types.length, rng.uniform(0, 0.4));
  return cells.map(([x, y], k) => [types[k], x, y]);
}
Object.assign(TEMPLATES, {
  ladder_group: (rng, s) => composed(rng, rng.weighted(groupTable(s?.single_mult, s?.big_mult, s?.cluster_mult, s?.ball_mult, s?.gold_mult, s?.composed_mult)), s),
  gem_group: (rng, s) => composed(rng, rng.weighted(GEM_GROUPS), s),
  group05: (rng, s) => composed(rng, rng.weighted(groupTable(s?.single_mult, s?.big_mult, s?.cluster_mult, s?.ball_mult, s?.gold_mult, s?.composed_mult, GROUPS_05)), s),
});

const CAMP_REACH = { wolf: 3, elk: 4, golem: 4, monolith: 5 };

// By default no monster reaches within one step of either spawn (spawn_reach_gap 2). Calibration 1 kept every
// camp camp_spawn_gap away as well, so spawn_reach_gap under 2 never brought a monster nearer (a bug); from
// calibration 2 monsters keep reach + spawn_reach_gap and clusters camp_spawn_gap. Calibration 4 keeps every camp
// camp_spawn_gap away as well (the 05 maps keep each camp 5 or more tiles from a spawn, monsters included).
function campCellsOk(g, cells, s, shared) {
  const camps = g.allCamps(), mirrors = cells.map(([, x, y]) => g.mirrorXY(x, y));
  for (const [type, x, y] of cells) {
    const gap = s.calib >= 4 ? Math.max(s.camp_spawn_gap, (CAMP_REACH[type] ?? 0) + (s.spawn_reach_gap ?? 2))
      : s.calib >= 2 ? (type in CAMP_REACH ? CAMP_REACH[type] + (s.spawn_reach_gap ?? 2) : s.camp_spawn_gap)
      : Math.max(s.camp_spawn_gap, (CAMP_REACH[type] ?? 0) + (s.spawn_reach_gap ?? 2)), ag = s.camp_altar_gap ?? 1;
    if (!g.in(x, y) || g.get(x, y) !== GROUND || g.noCamp?.has(y * g.W + x)) return false;
    if (rectDist(g.spawn, x, y) < Math.max(1, gap) || rectDist(g.spawn, ...g.mirrorXY(x, y)) < Math.max(1, gap)) return false;
    // group_gap 0 lets groups touch diagonally (as on several ladder maps); a cardinal touch would merge them.
    if (camps.some(c => cheb(c.x, c.y, x, y) <= (s.group_gap ?? 1) || Math.abs(c.x - x) + Math.abs(c.y - y) === 1)) return false;
    for (let dy = -ag; dy <= ag; dy++) for (let dx = -ag; dx <= ag; dx++) if (g.in(x + dx, y + dy) && g.get(x + dx, y + dy) === ALTAR) return false;
    if (!shared && mirrors.some(([mx, my]) => cheb(mx, my, x, y) <= 1)) return false;
  }
  // A shared group stores team A's half: no cell may be another cell's mirror (a cell may be its own).
  if (shared && cells.some(([, x, y], k) => mirrors.some(([mx, my], j) => j !== k && mx === x && my === y))) return false;
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
// tiles along it and `depth` rows on each side, typed by typeAt(k, d) (d = 0 next to the axis).
// When the axis is a row of tiles, that row is the band's middle and its tiles are their own
// mirrors (flagged in cells[k][3]). Returns team A's half of the cells and every tile of the band
// plus a one-tile margin.
function axisBand(g, rng, len, depth, typeAt, centred = false) {
  const rot = g.sym === 'rotational', rowsY = g.sym === 'vertical' || (rot && rng.chance(0.5));
  const across = rowsY ? g.H : g.W, along = rowsY ? g.W : g.H, xy = (u, v) => rowsY ? [u, v] : [v, u], odd = across % 2 === 1;
  if ((rot && (along - len) % 2) || len + 2 > along) return null;
  const a = rot ? (along - len) / 2 : centred ? Math.floor((along - len) / 2) + rng.int(-1, 1) : rng.int(1, along - len - 1), axis = odd ? (across - 1) / 2 : across / 2 - 1, cells = [], area = new Set();
  for (let d = 0; d < depth; d++) for (let k = 0; k < len; k++) {
    if (odd && !d && rot && k > (len - 1) / 2) continue;
    cells.push([typeAt(rot ? Math.min(k, len - 1 - k) : k, d), ...xy(a + k, axis - d), odd && !d]);
  }
  for (let u = a - 1; u <= a + len; u++) for (let v = axis - depth; v <= across - 1 - axis + depth; v++) {
    const [x, y] = xy(u, v);
    if (g.in(x, y)) { area.add(g.idx(x, y)); area.add(g.mirror(g.idx(x, y))); }
  }
  return { cells, area };
}

const bandGems = cells => cells.reduce((n, [t, , , axis]) => n + CAMP[t].gems * (axis ? 1 : 2), 0);

// Carves a clearing for one large shared group, placed first by placeCamps: elk, wolves and gem
// clusters worth 80-180 gems in all (shared_gems, like "stampede"), or for shared_big anything
// from a lone Monolith or Golem on the axis to a block of Golems, Elk and clusters (60-520).
function reserveShared(g, rng, s) {
  const big = !!s.shared_big, [lo, hi] = big ? [60, 520] : [80, 180];
  for (let guard = 0; guard < 80; guard++) {
    let len = rng.int(2, 7), depth = rng.chance(0.65) ? 2 : 1, typeAt;
    if (!big) { const inner = Array.from({ length: len }, () => rng.weighted({ elk: 3, wolf: 1, gem_cluster: 1 })); typeAt = (k, d) => d ? 'gem_cluster' : inner[k]; }
    else {
      const pal = rng.weighted({ mixed: 3, golems: 1.5, lone: 1, elks: 1 });
      if (pal === 'lone') { len = rng.int(1, 2); depth = rng.int(1, 2); const boss = rng.chance(0.5) ? 'monolith' : 'golem', ring = rng.choice(['gold_cluster', 'gem_cluster']); typeAt = (k, d) => d ? ring : boss; }
      else if (pal === 'golems') { depth = rng.int(1, 2); len = rng.int(1, 4); typeAt = (k, d) => d ? rng.weighted({ gem_cluster: 2, gold_cluster: 2 }) : 'golem'; }
      else if (pal === 'elks') { depth = rng.int(1, 3); typeAt = (k, d) => d === 0 ? 'elk' : rng.weighted({ elk: 1, wolf: 2, gold_cluster: 1 }); }
      else { depth = rng.int(1, 3); const inner = Array.from({ length: len }, () => rng.weighted({ elk: 2, golem: 1, wolf: 1, gem_cluster: 2 })); typeAt = (k, d) => d ? rng.weighted({ gem_cluster: 3, gold_cluster: 1, wolf: 1 }) : inner[k]; }
    }
    const band = axisBand(g, rng, len, depth, typeAt);
    if (!band) continue;
    const gems = bandGems(band.cells), bosses = t => bandGems(band.cells.filter(c => c[0] === t)) / CAMP[t].gems;
    // At most four Golems or two Monoliths, so the block can be taken.
    if (gems < lo || gems > hi || bosses('golem') > 4 || bosses('monolith') > 2 || (bosses('golem') && bosses('monolith'))) continue;
    for (const i of band.area) g.t[i] = GROUND;
    g.reserved = band.area;
    g.sharedCells = band.cells;
    return;
  }
  throw new GenFail('no room for a shared gem group');
}

// A designer's named objectives (g.sites), placed before the filler: a template near a point, an
// altar near a point ('self': a self-mirrored one), exact cells (a gate plug), or a shared treasure
// block on the symmetry axis at the centre. A required site that will not fit fails the attempt.
function placeSites(g, rng, s) {
  for (const site of g.sites ?? []) {
    let ok = false;
    if (site.cells) ok = tryGroup(g, site.cells, s, !!site.shared);
    else if (site.shared) ok = sharedTreasure(g, rng, s);
    else {
      const [ax, ay] = site.at, r = site.r ?? 6, near = [];
      for (let y = Math.floor(ay - r); y <= ay + r; y++) for (let x = Math.floor(ax - r); x <= ax + r; x++) {
        const d = Math.hypot(x - ax, y - ay);
        if (g.in(x, y) && d <= r) near.push([d + rng.uniform(0, 2), x, y]);
      }
      near.sort((p, q) => p[0] - q[0]);
      // Only an odd width (height) across the axis has self-mirrored tiles.
      const selfOk = g.sym === 'horizontal' ? g.W % 2 : g.sym === 'vertical' ? g.H % 2 : g.W % 2 && g.H % 2;
      const wantSelf = site.altar === 'self' && !!selfOk;
      for (const [, x, y] of near.slice(0, 150)) {
        if (site.altar) {
          const [mx, my] = g.mirrorXY(x, y), self = mx === x && my === y;
          const camps = g.campMask();
          if (self !== wantSelf || g.get(x, y) !== GROUND || g.noCamp?.has(y * g.W + x)) continue;
          const ag = s.camp_altar_gap ?? 1, crowdR = s.altar_crowd ?? 4;
          if (camps[y * g.W + x] || ag && [...Array(2 * ag + 1).keys()].some(j => [...Array(2 * ag + 1).keys()].some(i => g.in(x + i - ag, y + j - ag) && camps[(y + j - ag) * g.W + x + i - ag]))) continue;
          if (rectDist(g.spawn, x, y) < 3 || rectDist(g.spawn, mx, my) < 3 || !self && cheb(x, y, mx, my) < 3) continue;
          let crowd = false;
          for (let dy = -crowdR; dy <= crowdR && !crowd; dy++) for (let dx = -crowdR; dx <= crowdR; dx++) if (g.in(x + dx, y + dy) && g.get(x + dx, y + dy) === ALTAR) { crowd = true; break; }
          if (crowd) continue;
          g.set(x, y, ALTAR);
          if (stillConnected(g)) { ok = true; break; }
          g.set(x, y, GROUND);
        } else {
          const tpl = TEMPLATES[site.tpl](rng), flip = rng.chance(0.5);
          if (tryGroup(g, tpl.map(([t, dx, dy]) => [t, x + (flip ? dy : dx), y + (flip ? dx : dy)]), s)) { ok = true; break; }
        }
      }
    }
    if (!ok && site.required) throw new GenFail(`${site.cells ? 'gate' : site.shared ? 'shared treasure' : site.altar ? 'altar' : site.tpl} site does not fit${site.at ? ` near (${site.at.map(Math.round)})` : ''}`);
  }
}

// A shared block straddling the centre of the symmetry axis, sized to the economy.
function sharedTreasure(g, rng, s) {
  const [lo, hi] = { poor: [20, 80], rich: [150, 520], jackpot: [250, 520] }[s.camp_mode] ?? [60, 300];
  for (let guard = 0; guard < 60; guard++) {
    const pal = rng.weighted({ lone: 1.5, golems: 1, elks: 1.5, mixed: 2 });
    let len = rng.int(1, 4), depth = rng.int(1, 2), typeAt;
    if (pal === 'lone') { const boss = rng.weighted({ monolith: 1, golem: 1.5, elk: 1 }), ring = rng.choice(['gold_cluster', 'gem_cluster']); typeAt = (k, d) => d ? ring : boss; len = rng.int(1, 2); }
    else if (pal === 'golems') typeAt = (k, d) => d ? rng.weighted({ gem_cluster: 2, gold_cluster: 1 }) : 'golem';
    else if (pal === 'elks') typeAt = (k, d) => d ? rng.weighted({ gem_cluster: 2, wolf: 1 }) : 'elk';
    else { const inner = Array.from({ length: len }, () => rng.weighted({ elk: 2, golem: 0.7, wolf: 1, gem_cluster: 2 })); typeAt = (k, d) => d ? rng.weighted({ gem_cluster: 3, gold_cluster: 1 }) : inner[k]; }
    const band = axisBand(g, rng, len, depth, typeAt, true);
    if (!band) continue;
    const gems = bandGems(band.cells), bosses = t => bandGems(band.cells.filter(c => c[0] === t)) / CAMP[t].gems;
    if (gems < lo || gems > hi || bosses('golem') > 4 || bosses('monolith') > 2 || (bosses('golem') && bosses('monolith'))) continue;
    if (band.cells.some(([, x, y]) => g.get(x, y) !== GROUND && g.get(x, y) !== BUSH)) continue;
    const cells = band.cells.map(([t, x, y]) => [t, x, y]), saved = cells.map(([, x, y]) => g.get(x, y));
    cells.forEach(([, x, y]) => g.set(x, y, GROUND));
    if (tryGroup(g, cells, s, true)) return true;
    cells.forEach(([, x, y], k) => g.set(x, y, saved[k]));
  }
  return false;
}

// A small self-mirrored group straddling the symmetry axis (calibration 2's shared_groups): under rotation only
// the centre has room, so a second one rarely fits; on a mirror axis they spread along it.
function sharedGroup(g, rng, s, centred) {
  for (let guard = 0; guard < 40; guard++) {
    const pal = s.gem_only ? 'gems' : rng.weighted(s.calib >= 3 ? SHARED_GROUPS_V3 : SHARED_GROUPS), cl = rng.weighted({ gem_cluster: 2, gold_cluster: 1 });
    // Calibration 3 draws smaller ones (half the ladder's are 4-7 cells: 2x2 and 3x2 across an even axis, pluses on
    // an odd one) and leaves out the second row's ends of some 3-long ones (a null type), which makes the pluses.
    const v3 = s.calib >= 3;
    let len = v3 ? +rng.weighted(pal === 'guarded' ? { 1: 1.2, 2: 1, 3: 0.6 } : { 1: 0.5, 2: 1.4, 3: 1 }) : rng.int(1, 3), depth = v3 ? +rng.weighted({ 1: 0.7, 2: 0.3 }) : rng.int(1, 2), typeAt;
    if (pal === 'gems') typeAt = () => 'gem_cluster';
    else if (pal === 'gold') typeAt = () => 'gold_cluster';
    else if (pal === 'guarded') { const m = rng.weighted({ wolf: 3, elk: 1.5 }); depth = 2; typeAt = (k, d) => d ? cl : m; }
    else if (pal === 'boss') { const m = rng.weighted({ monolith: 1, golem: 1.5 }); len = rng.int(1, 2); depth = 2; typeAt = (k, d) => d ? 'gem_cluster' : m; }
    else { len = rng.int(3, 6); depth = rng.int(2, 3); const inner = Array.from({ length: len }, () => rng.weighted({ elk: 1, wolf: 2, golem: 0.3, gem_cluster: 3 })); typeAt = (k, d) => d ? rng.weighted({ gem_cluster: 3, gold_cluster: 2 }) : inner[k]; }
    if (v3 && len === 3 && depth === 2 && ['gems', 'gold', 'guarded'].includes(pal) && rng.chance(0.6)) { const inner = typeAt; typeAt = (k, d) => d && k !== 1 ? null : inner(k, d); }
    const band = axisBand(g, rng, len, depth, typeAt, centred);
    if (band) band.cells = band.cells.filter(([t]) => t);
    if (!band || band.cells.some(([, x, y]) => g.get(x, y) !== GROUND && g.get(x, y) !== BUSH)) continue;
    const cells = band.cells.map(([t, x, y]) => [t, x, y]), saved = cells.map(([, x, y]) => g.get(x, y));
    cells.forEach(([, x, y]) => g.set(x, y, GROUND));
    if (tryGroup(g, cells, s, true)) return true;
    cells.forEach(([, x, y], k) => g.set(x, y, saved[k]));
  }
  return false;
}

// A group 1-3 tiles from team A's spawn (calibration 2's home_camp); its mirror sits by team B's.
function homeGroup(g, rng, s) {
  const hs = { ...s, camp_spawn_gap: 1, spawn_reach_gap: 0 }, sp = g.spawn, cands = [];
  for (let y = sp.y - 3; y < sp.y + sp.h + 3; y++) for (let x = sp.x - 3; x < sp.x + sp.w + 3; x++) if (g.in(x, y) && rectDist(sp, x, y) >= 1) cands.push([x, y]);
  for (let guard = 0; guard < 6; guard++) {
    const cells = composed(rng, rng.weighted(s.gem_only ? { g: 1, gg: 2 } : s.single_mult === 0 ? { dd: 3, ddd: 0.6, Wd: 1.2, Wdd: 0.8, Wg: 0.5, Eddd: 0.3 } : HOME_GROUPS), s);
    for (const [x, y] of rng.shuffle(cands.slice()).slice(0, 40)) if (tryGroup(g, cells.map(([t, dx, dy]) => [t, x + dx, y + dy]), hs)) return true;
  }
  return false;
}

// A group just outside team A's spawn exclusion, camp_spawn_gap tiles away (calibration 4's starter: half the 05
// maps have a group exactly 5 from each spawn, a first farm); its mirror sits by team B's.
function starterGroup(g, rng, s) {
  const sp = g.spawn, r = s.camp_spawn_gap, cands = [];
  for (let y = sp.y - r; y < sp.y + sp.h + r; y++) for (let x = sp.x - r; x < sp.x + sp.w + r; x++) if (g.in(x, y) && rectDist(sp, x, y) === r) cands.push([x, y]);
  for (let guard = 0; guard < 6; guard++) {
    const cells = TEMPLATES[rng.weighted(s.camp_mix)](rng, s);
    // Each cell of the group in turn on the ring; the rest lie farther out or are refused.
    for (const [x, y] of rng.shuffle(cands.slice()).slice(0, 30)) for (const [, cx, cy] of cells)
      if (tryGroup(g, cells.map(([t, dx, dy]) => [t, x + dx - cx, y + dy - cy]), s)) return true;
  }
  return false;
}

// Gaps: a passage at most 3 wide is cut across by a line of holes, so only a dash (or a crystal)
// gets through there.
export function gaps(g, rng, n) {
  const pass = g.walkable(), occupied = g.campMask(), spawn = new Set([...g.spawnTiles(0), ...g.spawnTiles(1)]);
  const blocked = (x, y) => !g.in(x, y) || !pass[y * g.W + x];
  let made = 0;
  for (let tries = 0; made < n && tries < 4000; tries++) {
    const x = rng.int(1, g.W - 2), y = rng.int(1, g.H - 2), i = y * g.W + x;
    if (!pass[i] || occupied[i] || Math.min(...[0, 1].map(team => Math.min(...g.spawnTiles(team).map(j => cheb(j % g.W, Math.floor(j / g.W), x, y))))) < 5) continue;
    for (const [dx, dy] of rng.shuffle([[1, 0], [0, 1]])) {
      // Run across the passage along (dx, dy); the passage runs along the other axis.
      let a = 0, b = 0;
      while (a < 3 && !blocked(x - dx * (a + 1), y - dy * (a + 1))) a++;
      while (b < 3 && !blocked(x + dx * (b + 1), y + dy * (b + 1))) b++;
      if (a + b + 1 > 3 || !blocked(x - dx * (a + 1), y - dy * (a + 1)) || !blocked(x + dx * (b + 1), y + dy * (b + 1))) continue;
      // Open ground on both sides along the passage, so the cut is a crossing, not a dead end.
      if (blocked(x + dy, y + dx) || blocked(x - dy, y - dx)) continue;
      const line = [];
      for (let k = -a; k <= b; k++) line.push((y + dy * k) * g.W + x + dx * k);
      if (line.some(j => occupied[j] || occupied[g.mirror(j)] || spawn.has(j) || spawn.has(g.mirror(j)))) continue;
      for (const j of line) g.set(j % g.W, Math.floor(j / g.W), HOLE);
      made++;
      break;
    }
  }
  return made;
}

// Long barriers across the way between the spawns, attached to alternate sides (calibration 2's winding maps,
// like the ladder's meander, comb or twisty): walls, or 1-thick hole lines that a dash crosses (shortcut,
// reverse-spiral, cuts).
function barriers(g, rng, s, mark = null) {
  const alongX = g.sym === 'horizontal' || (g.sym === 'rotational' && g.W >= g.H), len = alongX ? g.W : g.H, across = alongX ? g.H : g.W;
  const n = rng.int(1, 3), kind = rng.chance(s.winding_holes ?? 0.6) ? HOLE : WALL, thick = kind === HOLE ? 1 : rng.int(1, 2);
  const lo = Math.round(0.12 * len), hi = Math.floor(len / 2) - 2, first = rng.chance(0.5);
  if (hi - lo < 4) return;
  for (let k = 0; k < n; k++) {
    const p = Math.round(lo + (hi - lo) / n * (k + rng.uniform(0.2, 0.8))), low = (k % 2 === 0) === first, reach = Math.round(across * rng.uniform(0.7, 0.92));
    for (let a = low ? 0 : across - reach; a < (low ? reach : across); a++) for (let t = 0; t < thick; t++) {
      const [x, y] = alongX ? [p + t, a] : [a, p + t];
      g.set(x, y, kind);
      if (mark && g.in(x, y)) mark[g.mirror(g.idx(x, y))] = mark[g.idx(x, y)] = 1;
    }
  }
}

function placeCamps(g, rng, s) {
  const total = () => g.camps.length;
  if (g.sharedCells && !tryGroup(g, g.sharedCells, s, true)) throw new GenFail('shared gem group blocked');
  for (let k = 0; k < (s.shared_gold ?? 0); k++)
    for (let guard = 0; guard < 30; guard++) {
      const band = axisBand(g, rng, rng.int(1, 3), 1, () => 'gold_cluster');
      if (band && tryGroup(g, band.cells, s, true)) break;
    }
  for (let k = 0; k < (s.contested_groups ?? 0); k++) {
    const f = spawnFields(g), tpl = TEMPLATES[rng.weighted(s.contested_mix)](rng);
    for (const i of candidates(g, rng, f, [0.36, 0.5], () => true).slice(0, 80)) {
      const x = i % g.W, y = (i - x) / g.W;
      if (tryGroup(g, tpl.map(([t, dx, dy]) => [t, x + dx, y + dy]), s)) break;
    }
  }
  if (s.calib >= 2) {
    for (let k = 0; k < (s.shared_groups ?? 0); k++) sharedGroup(g, rng, s, k === 0);
    if (s.home_camp) homeGroup(g, rng, s);
    if (s.starter) starterGroup(g, rng, s);
  } else if (s.shared_camp) {
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
  for (let guard = 0; made < s.groups && guard < s.groups * 4 && total() < (s.max_camps ?? 200); guard++) {
    const f = spawnFields(g), tpl = TEMPLATES[rng.weighted(s.camp_mix)](rng, s), band = bandFor(rng, s.camp_bias, s.camp_bands);
    const flip = rng.chance(0.5), cells = tpl.map(([t, dx, dy]) => [t, flip ? dy : dx, flip ? dx : dy]);
    for (const i of candidates(g, rng, f, band, () => true).slice(0, 60)) {
      const x = i % g.W, y = (i - x) / g.W;
      if (tryGroup(g, cells.map(([t, dx, dy]) => [t, x + dx, y + dy]), s)) { made++; break; }
    }
  }
  if (made < Math.min(s.groups, 1) && !g.sites?.length) throw new GenFail('no camp placement');
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

const HOW = ['on foot', 'by dash', 'by teleport crystal'];
const RAIDERS = new Set(['golem', 'monolith']);

// The most any objective of the map needs (0 walk, 1 dash, 2 teleport), ignoring unreachable ones.
export function naturalAccess(g) {
  const F = accessFields(g);
  let worst = 0;
  for (let i = 0; i < g.t.length; i++) if (g.t[i] === ALTAR) { const l = levelOf(g, F, [i]); if (l < 3) worst = Math.max(worst, l); }
  for (const grp of g.groups()) { const l = Math.max(...grp.members.map(m => levelOf(g, F, [m.y * g.W + m.x]))); if (l < 3) worst = Math.max(worst, l); }
  return worst;
}

// Objectives may need up to g.access (walk by default; vaults may always need a crystal). When any
// needs more than walking, each team must reach on foot a camp group paying gold that it can take
// early (no Golem or Monolith), so it can buy a crystal.
// minSide: the ladder has 28x28 maps (04pinwheel, 04plaza); calibration 1 generated and mutated only sides of 30 up.
export function validate(g, { strict = true, minSide = 28 } = {}) {
  const errors = [], warnings = [];
  if (g.W < minSide || g.H < minSide || g.W > 100 || g.H > 100) (strict ? errors : warnings).push(`size ${g.W}x${g.H} outside ${minSide}..100`);
  if (g.picks < 3 || g.picks > 5) errors.push(`picks ${g.picks}`);
  const s = g.spawn, area = s.w * s.h;
  if (area < 9 || area > 16) errors.push(`spawn area ${s.w}x${s.h}`);
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
  const allowed = LEVELS.indexOf(g.access ?? 'walk'), F = accessFields(g), camps = g.campMask(), blocked = g.gated ? F[allowed] : spawnFields(g, camps, allowed);
  const at = (d, x, y) => g.reachNear(d, x, y) >= 0;
  let worst = 0;
  const need = (what, level, vault) => {
    if (level === 3) errors.push(`${what} unreachable`);
    else if (level > allowed) (!strict || vault ? warnings : errors).push(`${what} reachable only ${HOW[level]}`);
    if (level < 3) worst = Math.max(worst, level);
  };
  const spawnLevel = levelOf(g, F, b);
  if (spawnLevel > allowed) (spawnLevel < 3 && !strict ? warnings : errors).push(`spawns not connected${spawnLevel < 3 ? ` (only ${HOW[spawnLevel]})` : ''}`);
  else if (!b.some(i => at(blocked.dA, i % g.W, Math.floor(i / g.W)))) (strict ? errors : warnings).push('spawns not connected past the camps');
  let altars = 0;
  for (let i = 0; i < g.t.length; i++) {
    if (g.t[i] !== ALTAR) continue;
    altars++;
    const x = i % g.W, y = (i - x) / g.W, level = levelOf(g, F, [i]);
    need(`altar (${x}, ${y})`, level, g.vaults.has(i));
    if (level <= allowed && !g.vaults.has(i) && !at(blocked.dA, x, y)) (strict ? errors : warnings).push(`altar (${x}, ${y}) enclosed by camps`);
  }
  if (!altars) (strict ? errors : warnings).push('no altars');
  const groups = g.groups();
  for (const grp of groups) {
    const c = grp.members[0], level = Math.max(...grp.members.map(m => levelOf(g, F, [m.y * g.W + m.x])));
    need(`camp group at (${c.x}, ${c.y})`, level, [...grp.tiles].some(i => g.vaults.has(i)));
    if (level <= allowed && !g.gated && !grp.members.some(m => at(blocked.dA, m.x, m.y) || at(blocked.dB, m.x, m.y))) (strict ? errors : warnings).push(`camp group at (${c.x}, ${c.y}) enclosed by other camps`);
  }
  if (!groups.length) (strict ? errors : warnings).push('no camps');
  if (worst > 0 && !groups.some(q => q.gold > 0 && !q.members.some(m => RAIDERS.has(m.type)) && q.members.every(m => at(F[0].dA, m.x, m.y))))
    (strict ? errors : warnings).push('no early gold on foot from the spawn (a crystal costs 10)');
  let pocket = 0, far = 0;
  for (let i = 0; i < g.t.length; i++) if (F[0].pass[i] && F[0].dA[i] < 0 && !a.has(i) && !b.includes(i)) { pocket++; far += F[2].dA[i] < 0; }
  if (pocket) warnings.push(`${pocket} walkable tiles unreachable on foot${far ? ` (${far} even by teleport crystal)` : ''}`);
  return { errors, warnings };
}

export const altarZone = r => r === null ? null : r < 0.4 ? 'own' : r > 0.6 ? 'enemy' : 'mid';

// On foot whatever g.access says, so a map file's metrics match those recorded when it was made.
export function metrics(g) {
  const camps = g.campMask(), open = spawnFields(g, null, 0), b = g.spawnTiles(1);
  const spawnDist = fld => Math.min(...b.map(i => g.reachNear(fld.dA, i % g.W, Math.floor(i / g.W))).filter(d => d >= 0));
  // Through the camps when they wall the spawns apart (as on some competition maps).
  let f = spawnFields(g, camps, 0), S = spawnDist(f);
  if (!Number.isFinite(S)) { f = open; S = spawnDist(f); }
  // Spawns joined only by dashes or crystals: travel cost (a dash 4, a crystal 8).
  if (!Number.isFinite(S)) { f = spawnFields(g, null, 2); S = spawnDist(f); }
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
  // Shape of the playable (walkable and reachable) area: its share of the corners outside the
  // inscribed ellipse, of the central box (|u|, |v| < 0.3) and of the 2-tile border; boundary
  // tiles per playable tile; share of playable tiles in cramped surroundings (at most half of
  // their 5x5 box playable).
  const { W, H } = g, play = Uint8Array.from(open.dA, (d, i) => d >= 0 || open.dB[i] >= 0);
  let nc = 0, fc = 0, ncen = 0, fcen = 0, ne = 0, fe = 0, edge = 0, cramped = 0, playN = 0;
  for (let y = 0; y < H; y++) for (let x = 0; x < W; x++) {
    const i = y * W + x, u = (2 * x - W + 1) / (W - 1), v = (2 * y - H + 1) / (H - 1), p = play[i];
    if (u * u + v * v > 1) { nc++; fc += p; }
    if (Math.max(Math.abs(u), Math.abs(v)) < 0.3) { ncen++; fcen += p; }
    if (x < 2 || y < 2 || x >= W - 2 || y >= H - 2) { ne++; fe += p; }
    if (!p) continue;
    playN++;
    if ([[1, 0], [-1, 0], [0, 1], [0, -1]].some(([dx, dy]) => !g.in(x + dx, y + dy) || !play[(y + dy) * W + x + dx])) edge++;
    let box = 0, tot = 0;
    for (let dy = -2; dy <= 2; dy++) for (let dx = -2; dx <= 2; dx++) if (g.in(x + dx, y + dy)) { tot++; box += play[(y + dy) * W + x + dx]; }
    if (2 * box <= tot) cramped++;
  }
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
  // Gems per side behind a dash or a crystal (from team A; the map is symmetric).
  const F = accessFields(g), groupLevel = q => Math.max(...q.members.map(c => levelOf(g, F, [c.y * g.W + c.x])));
  let dashGems = 0, teleGems = 0, worst = 0;
  for (const q of [...mine, ...shared]) {
    const l = groupLevel(q), v = q.shared ? q.gems / 2 : q.gems;
    if (l < 3) worst = Math.max(worst, l);
    if (l === 1) dashGems += v; else if (l >= 2) teleGems += v;
  }
  let offAltars = 0;
  for (let i = 0; i < g.t.length; i++) if (g.t[i] === ALTAR) { const l = levelOf(g, F, [i]); offAltars += l > 0; if (l < 3) worst = Math.max(worst, l); }
  const campDist = mine.map(q => q.dA).filter(Number.isFinite);
  const ratios = mine.filter(q => Number.isFinite(q.dA + q.dB)).map(q => q.dA / Math.max(1, q.dA + q.dB));
  const types = {};
  for (const q of [...mine, ...shared]) for (const c of q.members) types[c.type] = (types[c.type] ?? 0) + (q.shared ? 0.5 : 1);
  const frac = k => Math.round(1000 * g.t.reduce((n, t) => n + (t === k), 0) / g.t.length) / 1000;
  const median = arr => arr.length ? [...arr].sort((p, q) => p - q)[arr.length >> 1] : null;
  const r2 = v => Math.round(100 * v) / 100, r3 = v => Math.round(1000 * v) / 1000;
  const gems = mine.reduce((n, q) => n + q.gems, 0) + shared.reduce((n, q) => n + q.gems / 2, 0);
  const typeGems = (...ks) => ks.reduce((n, k) => n + (types[k] ?? 0) * CAMP[k].gems, 0) / Math.max(1, gems);
  const campsSide = Object.values(types).reduce((a, c) => a + c, 0);
  return {
    size: `${g.W}x${g.H}`, area: g.W * g.H, aspect: r2(Math.max(W, H) / Math.min(W, H)), sym: g.sym, picks: g.picks, spawn: `${s.w}x${s.h}`,
    walls: frac(WALL), holes: frac(HOLE), bushes: frac(BUSH),
    reach_frac: r3(reach / g.t.length),
    spawn_dist: S, spawn_rel: r2(S / ((W + H) / 2)), detour: r2(S / Math.max(1, cheby)), choke: choke === Infinity ? null : choke,
    choke_rel: choke === Infinity ? null : r2(choke / Math.sqrt(Math.max(1, reach))),
    openness: r2(clearSum / Math.max(1, reach)),
    fill_corner: r2(fc / Math.max(1, nc)), fill_centre: r2(fcen / Math.max(1, ncen)), fill_edge: r2(fe / Math.max(1, ne)),
    boundary: r3(edge / Math.max(1, playN)), cramped: r3(cramped / Math.max(1, playN)),
    altars: altars.length, altar_near: altars.length ? Math.min(...altars) : null,
    // Nearest walkable altar's distance from own spawn over the sum of both spawns' distances.
    altar_ratio: altarRatio === null ? null : r2(altarRatio), altar_zone: altarZone(altarRatio),
    groups_side: mine.length, shared_groups: shared.length, camps_side: campsSide, types,
    // Camps per side per 100 tiles of its half of the playable area.
    camp_density: r2(200 * campsSide / Math.max(1, playN)),
    gems_side: gems, gold_side: mine.reduce((n, q) => n + q.gold, 0) + shared.reduce((n, q) => n + q.gold / 2, 0),
    // Shares of a side's gems from Monoliths and Golems, from shared groups and from gem clusters.
    big_share: r2(typeGems('monolith', 'golem')), shared_share: r2(shared.reduce((n, q) => n + q.gems / 2, 0) / Math.max(1, gems)), cluster_share: r2(typeGems('gem_cluster')),
    monoliths: types.monolith ?? 0, golems: types.golem ?? 0,
    camp_near: campDist.length ? Math.min(...campDist) : null, camp_ratio: median(ratios.map(r2)),
    contested_share: ratios.length ? r2(ratios.filter(r => r >= 0.38).length / ratios.length) : 0,
    access: LEVELS[worst], dash_gems: r2(dashGems / Math.max(1, gems)), tele_gems: r2(teleGems / Math.max(1, gems)), off_altars: r2(offAltars / Math.max(1, altars.length)),
    ...shapeMetrics(g, F, play, playN, mine, shared),
  };
}

// Metrics of the quirks: spawn distances with dashes and crystals, 1-wide corridors, leaky
// diagonals, the spawn's surround, group sizes and contacts, altar crowding, and how often a tile
// in sight is far on foot.
function shapeMetrics(g, F, play, playN, mine, shared) {
  const r2 = v => Math.round(100 * v) / 100, r3 = v => Math.round(1000 * v) / 1000;
  const { W, H } = g, pass = F[0].pass, b = g.spawnTiles(1), blocked = (x, y) => !g.in(x, y) || !pass[y * W + x];
  const sd = l => { const d = Math.min(...b.map(i => g.reachNear(F[l].dA, i % W, Math.floor(i / W))).filter(v => v >= 0)); return Number.isFinite(d) ? d : null; };
  const [s0, s1, s2] = [0, 1, 2].map(sd), gain = (a, c) => c ? r2(Math.min(10, (a ?? 10 * c) / c)) : null;
  let narrow = 0, leaky = 0;
  for (let y = 0; y < H; y++) for (let x = 0; x < W; x++) {
    if (play[y * W + x] && ((blocked(x - 1, y) && blocked(x + 1, y)) || (blocked(x, y - 1) && blocked(x, y + 1)))) narrow++;
    if (x + 1 < W && y + 1 < H && ((blocked(x, y) && blocked(x + 1, y + 1) && !blocked(x + 1, y) && !blocked(x, y + 1)) || (blocked(x + 1, y) && blocked(x, y + 1) && !blocked(x, y) && !blocked(x + 1, y + 1)))) leaky++;
  }
  const sp = g.spawn;
  let ring = 0, ringN = 0;
  for (let y = sp.y - 1; y <= sp.y + sp.h; y++) for (let x = sp.x - 1; x <= sp.x + sp.w; x++) if (g.in(x, y) && (x < sp.x || y < sp.y || x >= sp.x + sp.w || y >= sp.y + sp.h)) { ringN++; ring += !pass[y * W + x]; }
  const groups = g.groups(), gid = new Map();
  groups.forEach((q, k) => q.members.forEach(c => gid.set(c.y * W + c.x, k)));
  let diag = 0;
  for (const [i, k] of gid) for (const [dx, dy] of [[1, 1], [1, -1]]) { const x = i % W + dx, y = Math.floor(i / W) + dy, j = gid.get(y * W + x); if (g.in(x, y) && j !== undefined && j !== k) diag++; }
  const altars = [];
  for (let i = 0; i < g.t.length; i++) if (g.t[i] === ALTAR) altars.push([i % W, Math.floor(i / W)]);
  const camps = g.allCamps(), slots = ([x, y]) => { let n = 0; for (let dy = -1; dy <= 1; dy++) for (let dx = -1; dx <= 1; dx++) n += (dx || dy) && !blocked(x + dx, y + dy); return n; };
  const near = (a, list) => Math.min(...list.filter(p => p !== a).map(p => cheb(a[0], a[1], p[0], p[1])));
  // Sight against walking from every floor(n / 300)-th playable tile (300-599 of them from 300 up): of the tiles
  // 2-3 away (ranged range) on a clear line (no wall or bush between), the share at least 5 steps longer on foot.
  const opaque = i => g.t[i] === WALL || g.t[i] === BUSH, src = [];
  for (let i = 0; i < play.length; i++) if (play[i]) src.push(i);
  let seen = 0, far = 0;
  const step = Math.max(1, Math.floor(src.length / 300)), d = new Int32Array(17 * 17), q = new Int32Array(17 * 17);
  for (let k = 0; k < src.length; k += step) {
    const x0 = src[k] % W, y0 = Math.floor(src[k] / W);
    d.fill(-1); d[8 * 17 + 8] = 0; q[0] = 8 * 17 + 8;
    for (let h = 0, t = 1; h < t; h++) {
      const u = q[h] % 17, v = Math.floor(q[h] / 17);
      if (d[q[h]] >= 8) continue;
      for (let dy = -1; dy <= 1; dy++) for (let dx = -1; dx <= 1; dx++) { const uu = u + dx, vv = v + dy; if (uu >= 0 && vv >= 0 && uu < 17 && vv < 17 && d[vv * 17 + uu] < 0 && !blocked(x0 + uu - 8, y0 + vv - 8)) { d[vv * 17 + uu] = d[q[h]] + 1; q[t++] = vv * 17 + uu; } }
    }
    for (let dy = -3; dy <= 3; dy++) for (let dx = -3; dx <= 3; dx++) {
      const r = Math.max(Math.abs(dx), Math.abs(dy)), x = x0 + dx, y = y0 + dy;
      if (r < 2 || blocked(x, y)) continue;
      let clear = true;
      for (let t = 1; t < 2 * r && clear; t++) { const xx = Math.round(x0 + dx * t / (2 * r)), yy = Math.round(y0 + dy * t / (2 * r)); if ((xx !== x0 || yy !== y0) && (xx !== x || yy !== y) && opaque(yy * W + xx)) clear = false; }
      if (!clear) continue;
      seen++;
      const w = d[(dy + 8) * 17 + dx + 8];
      if (w < 0 || w >= r + 5) far++;
    }
  }
  return {
    walk_split: s0 === null, dash_gain: gain(s0, s1), tele_gain: gain(s0, s2),
    narrow: r3(narrow / Math.max(1, playN)), leaky: r2(1000 * leaky / Math.max(1, playN)), spawn_ring: r2(ring / Math.max(1, ringN)),
    max_group: Math.max(0, ...[...mine, ...shared].map(q => q.members.length)), diag_groups: diag,
    camp_altar: altars.length && camps.length ? Math.min(...altars.map(a => near(a, camps.map(c => [c.x, c.y])))) : null,
    altar_gap: altars.length > 1 ? Math.min(...altars.map(a => near(a, altars))) : null, altar_slots: altars.length ? Math.min(...altars.map(slots)) : null,
    sight_gap: r3(far / Math.max(1, seen)),
  };
}

// ---- presets -------------------------------------------------------------------------------
// altar_mode is one dimension of every preset; the default mix makes about half the maps'
// nearest altars central (the ladder has 20 of 35).
const DEFAULTS = {
  symmetry: { rotational: 5, horizontal: 2.5, vertical: 2.5 }, picks: [3, 5], spawn_size: { 3: 1, 4: 1 }, spawn_place: { corner: 5, edge: 3, inset: 2 }, spawn_bush: 0.15,
  terrain: { open: 1, scatter: 4, caves: 1.5, rooms: 1.5, lanes: 1, rings: 1, rows: 1 }, wall_density: [0.02, 0.12], wall_length: [0.1, 0.35],
  cave_fill: [0.38, 0.46], cave_iters: [3, 5], room_size: [7, 14], door_width: [2, 4], room_margin: [0, 4], lane_count: [2, 4], lane_kind: { wall: 2, hole: 1 }, lane_thick: [1, 2],
  ring_step: [7, 11], ring_gates: [2, 4], ring_kind: { wall: 3, hole: 1 }, ring_shape: { square: 2, diamond: 1 }, row_gap: [5, 9],
  holes: { none: 3, lakes: 2, moat: 1.5, pits: 2 }, hole_amount: [0.02, 0.1], bushes: { none: 1, blobs: 3, patches: 3, strips: 2 }, bush_amount: [0.03, 0.15],
  min_pocket: 20, carve_width: 2, hole_cost: 1.5, max_bush_clusters: 24, vaults: 0,
  altars: [1, 4], altar_near: 0.6, shared_altar: 0.25, altar_spacing: [5, 9], altar_bands: { near: 2, mid: 3, contested: 3 },
  altar_mode: { spread: 1.5, own: 2.5, central: 4.5, contested: 1, corners: 1, single: 0.8, many: 0.35 },
  groups: [3, 14], camp_mix: { wolf: 3, wolf_pair: 2, wolf_pack: 1, elk: 2, elk_gold: 1.5, elk_gems: 1, gems: 2.5, gold: 2, gold_gems: 1, golem: 0.4, golem_gold: 0.4, poly: 0.5, snake: 0.3, ring: 0.2, carpet: 0.2, pack: 0.25 },
  camp_bias: { near: 1, spread: 3, contested: 1 }, camp_spawn_gap: 5, monoliths: { 0: 6, 1: 1 }, monolith_ring: 0.5, monolith_band: { mid: 1, contested: 2 }, shared_camp: 0.1,
  camp_mode: 'standard', shape: 'none', min_reach: 0.35, gem_min: 30,
  size: [30, 100], aspect: { square: 3, wide: 1 },
  // The ladder's quirks at about its rates (2026-10-30, 70 maps): groups touching diagonally (10%), camps
  // beside altars (16%) or reaching a spawn's edge (9%), a partly walled spawn surround (11%), 4x3 and 5x2
  // spawns (7%), groups of 20+ cells (14%; the composed templates below).
  group_gap: { 1: 4, 0: 1 }, camp_altar_gap: { 1: 4, 0: 1 }, spawn_reach_gap: { 2: 5, 1: 1, 0: 1 }, spawn_clear: { 2: 5, 1: 2, 0: 1 }, spawn_dims: { none: 12, '4x3': 1, '5x2': 0.4 },
};

// ---- calibration 2 (2026-11-05): DEFAULTS_V2 and V2_PRESETS, fitted to the 128 ladder maps (42 of them the 04*
// maps of SDK 5.0.0), each map weighted equally; research/notes/mapgen-vs-ladder-2026-11-05.md. Calibration 1 (DEFAULTS,
// the 2026-10-30 rates) is kept as it was, so `--calib 1` and `suite --mix varied-v1` remake older maps exactly.
// Long side (bands, % of maps), aspect (long / short: square, 1.05-1.35, 1.4-1.8, 2-3.1; W > H four times in five),
// picks by area, the altar make-up (pairs + self-mirrored altars) and shared groups by symmetry, as on the ladder.
const LADDER_LONG = { '28-29': 4, '30-31': 15, '32-34': 4, '35-39': 10, '40-44': 12, '45-49': 10, '50-54': 20, '55-59': 2, '60-64': 9, '65-69': 3, '70-74': 5, '75-79': 2, '80-84': 12, '85-89': 4, '90-94': 10, '95-99': 3, '100-100': 5 };
const LADDER_ASPECT = { 1: 59, mild: 30, medium: 6, long: 5 };
const PICKS_BY_AREA = [[1600, { 3: 37, 4: 42, 5: 21 }], [2500, { 3: 23, 4: 23, 5: 54 }], [4900, { 3: 3, 4: 6, 5: 91 }], [Infinity, { 4: 7, 5: 93 }]];
const SHARED_BY_SYM = { rotational: { 0: 68, 1: 32 }, mirror: { 0: 36, 1: 21, 2: 19, 3: 12, 4: 7, 5: 5 } };
// Calibration 3 asks for more under rotation: only the centre fits one there, and about half the asks failed.
const SHARED_BY_SYM_V3 = { rotational: { 0: 45, 1: 55 }, mirror: SHARED_BY_SYM.mirror };
const DEFAULTS_V2 = {
  ...DEFAULTS,
  symmetry: { rotational: 7, horizontal: 2.2, vertical: 1.8 }, picks: 'area', spawn_size: { 3: 6.5, 4: 1 }, spawn_dims: { none: 95, '4x3': 3, '5x2': 1.5, '8x2': 0.7 },
  spawn_clear: { 2: 2, 1: 2, 0: 2.5 }, spawn_reach_gap: { 2: 4, 1: 2, 0: 1.5 }, camp_spawn_gap: { 5: 4, 4: 3, 3: 2 },
  terrain: { open: 1, scatter: 5, caves: 0.5, rooms: 1, lanes: 0.7, rings: 0.7, rows: 1 }, wall_density: [0.02, 0.14], winding: 0.5, winding_holes: 0.4,
  holes: { none: 4.5, lakes: 2.5, moat: 1.2, pits: 1 }, hole_amount: [0.02, 0.1], lake_amount: { '0.03-0.08': 1, '0.08-0.15': 1, '0.15-0.25': 1, '0.25-0.45': 1 },
  bushes: { none: 0.05, blobs: 3, patches: 3, strips: 2 }, bush_amount: [0.015, 0.09], unleak: 0.85, unnarrow: 0.55, single_mult: { 0: 45, 1: 35, 3.5: 20 }, big_mult: { 0.4: 1, 1: 2, 3: 1 }, cluster_mult: { 0.5: 1, 1: 2, 2: 1 },
  altar_cfg: { '0+1': 32, '1+0': 44, '0+2': 5, '1+1': 10, '0+3': 3, '2+0': 20, '1+2': 1, '2+1': 3, '3+0': 5, '5+0': 3, '9+0': 1 },
  altars: undefined, altar_near: 0.3, shared_altar: 0.3, altar_mode: { central: 3, hub: 2.5, spread: 1.5, own: 1.2, contested: 1, corners: 0.3 }, altar_open: { 7: 8, 0: 1 }, altar_twin: 0.2,
  camp_mix: { ladder_group: 1 }, monoliths: { 0: 3, 1: 1 }, shared_camp: undefined, shared_groups: 'sym', home_camp: 0.17, group_scale: 0.15, dash_cuts: 0.12,
  camp_mode: { standard: 94, 'gems-only': 6 }, size: 'ladder', aspect: 'ladder',
};
// Calibration 2's changes to the ladder-like presets: ladder sizes, picks by area and the altar make-up (altars:
// undefined drops the preset's own count).
const V2_PRESETS = {
  classic: { size: 'ladder', aspect: 'ladder', altars: undefined, picks: 'area' },
  'small-brawl': { size: [28, 36], altars: undefined, picks: 'area' },
  maze: { size: 'ladder', aspect: 'ladder', altars: undefined, picks: 'area' },
  caves: { size: 'ladder', aspect: 'ladder', altars: undefined, picks: 'area', cave_fill: [0.36, 0.42] },
  lanes: { altars: undefined, picks: 'area' },
  lakes: { size: 'ladder', aspect: 'ladder', altars: undefined, picks: 'area' },
  jungle: { size: 'ladder', aspect: 'ladder', altars: undefined, picks: 'area' },
  monolith: { size: 'ladder', aspect: 'ladder', altars: undefined, picks: 'area', monoliths: 1 },
  rows: { size: 'ladder', aspect: 'ladder', altars: undefined, picks: 'area' },
  'altar-poor': { picks: 'area' },
  'contested-centre': { size: 'ladder', aspect: 'ladder', picks: 'area', shared_groups: [1, 2], altar_cfg: { '0+1': 2, '1+1': 2, '2+1': 1 } },
  tiny: { size: { 28: 1, 29: 1, 30: 4, 31: 3 } },
  huge: { altars: undefined, picks: 'area', groups: [8, 20] },
  'monolith-only': { size: 'ladder', aspect: 'ladder', altars: undefined, picks: 'area' },
  'shared-gems': { size: 'ladder', aspect: 'ladder', altars: undefined, picks: 'area' },
  vaults: { size: 'ladder', aspect: 'ladder', altars: undefined, picks: 'area' },
};

// ---- calibration 3 (2026-11-08, `suite --mix ladder-v2`; research/notes/mapgen-vs-ladder-2026-11-05.md, "Calibration 3"):
// calibration 2 with the ladder's group shapes (LADDER_SHAPES; lines on few maps, line_mult), gem balls (gem-only
// groups of 3+ cells) on fewer maps (ball_mult: the ladder has one on 28% of maps, calibration 2 on 50%), gold-only
// and cluster-only groups bunched on fewer maps (gold_mult, cluster_mult), composed groups mostly 6-9 cells
// (composed_mult), smaller shared groups and more of them under rotation, a few more lakes, and classic without its
// shared_camp, which under calibration 2 failed every classic map without a shared group (so classic came out mostly
// mirrored and always had one). Calibration 2 is kept as it was.
const DEFAULTS_V3 = {
  ...DEFAULTS_V2, ball_mult: { 0: 70, 1: 20, 3: 10 }, gold_mult: { 0: 40, 1: 30, 2.2: 30 }, line_mult: { 0: 45, 1: 35, 3: 20 }, cluster_mult: { 0.3: 1.5, 1: 1.5, 2.5: 1 }, composed_mult: 2,
  holes: { none: 4.5, lakes: 3.2, moat: 0.9, pits: 0.6 }, lake_amount: { '0.03-0.08': 1, '0.08-0.15': 1, '0.15-0.25': 1.3, '0.25-0.45': 1.4 },
};
// classic and monolith-only drew no bushes on 17% and 40% of maps (the ladder: 3%).
const V3_PRESETS = { classic: { shared_camp: undefined, bushes: { patches: 3, strips: 2, none: 0.1 } }, 'monolith-only': { bushes: { patches: 2, strips: 1, none: 0.1 } } };

// ---- calibration 4 (2026-11-12, the 05 part of `suite --mix ladder-v3`; research/notes/ideas-2026-11-12/ladderv3/):
// calibration 3 refitted to the 40 05 maps, one author's style: 3x3 spawns with every camp 5 or more tiles away,
// groups from GROUPS_05 in SHAPES_05's blocks (on most maps every group guarded; a few maps all clusters or
// singletons), shared groups almost only on mirrored maps, more walls, fewer holes, bushes absent or plentiful.
// Size, aspect, symmetry, picks and altars stay calibration 3's, which the 05 maps match.
const SHARED_BY_SYM_V4 = { rotational: { 0: 96, 1: 4 }, mirror: SHARED_BY_SYM.mirror };
const DEFAULTS_V4 = {
  ...DEFAULTS_V3, spawn_size: 3, spawn_dims: 'none', camp_spawn_gap: 5, spawn_reach_gap: 1, home_camp: 0.03, starter: 0.3, camp_mix: { group05: 1 },
  single_mult: { 0: 70, 1: 15, 5: 15 }, cluster_mult: { 0: 55, 1: 30, 4: 15 }, ball_mult: 1, gold_mult: { 0: 60, 1: 25, 3: 15 }, line_mult: 1, big_mult: 1, composed_mult: 0.6,
  monoliths: { 0: 1.6, 1: 1 }, group_scale: 0.2,
  terrain: { open: 1.8, scatter: 5, caves: 0.5, rooms: 1.5, lanes: 0.7, rings: 0.7, rows: 1 }, wall_density: [0.02, 0.3],
  holes: { none: 11, lakes: 3, moat: 0.6, pits: 0.8 }, bushes: { none: 1, blobs: 2, patches: 2, strips: 1 }, bush_amount: { '0.015-0.06': 2, '0.06-0.12': 1, '0.12-0.25': 0.7 },
};
const V4_PRESETS = {};

// ---- the full-pool layer (2026-11-12, `suite --mix ladder-v4`; research/notes/ladder-v3.md, "Full
// pool"): a classifier on every metric, against all 168 ladder maps, still told calibrations 3 and 4 from the ladder,
// on three things the per-metric fit never saw: the ladder keeps its 2-tile frame open (41% of maps, generated 19%),
// has hole-framed arenas (13% with under half the frame playable, generated 7%) and close spawns (14% under spawn_rel
// 0.5, generated 4%: the spawn gates excluded them). Plan entries pick the layer with { fit }; each part is fitted so
// its generated three quarters (the rest are mutated ladder maps) match its ladder maps. The ladder's partly blocked
// frames are mostly barriers run to the edge (its detour maps' frames are 92-99% open), so maps without winding
// barriers get the open frame (border_clear 0.9) and the 05 maps, with half the detours, fewer barriers (winding).
// Over calibration 3 ('pool') or 4 ('pool05'); without { fit } nothing here is drawn.
const POOL_FIT = {
  pool: { border_clear: 0.9, spawn_mode: { none: 85, near: 13, mid: 2 }, shape: { none: 86, circle: 4, diamond: 4, star: 3, blob: 3 }, void_kind: { hole: 3, wall: 1 }, core_kind: 'hole' },
  pool05: { border_clear: 1, winding: 0.25, spawn_mode: { none: 79, near: 19, mid: 2 }, shape: { none: 86, circle: 4, diamond: 4, star: 3, blob: 3 }, void_kind: { hole: 3, wall: 1 }, core_kind: 'hole' },
};

// The base of the exotic presets: every dimension sampled wide, each preset pinning one or two.
const EXOTIC = {
  size: [30, 100], aspect: { square: 3, wide: 2, thin: 0.6 }, symmetry: { rotational: 4, horizontal: 2, vertical: 2 },
  shape: { none: 3, circle: 1, diamond: 0.7, star: 0.7, donut: 1, cross: 0.8, hourglass: 0.5, band: 0.4, islands: 0.8, lattice: 0.5, blob: 0.7 },
  void_kind: { hole: 1, wall: 1 }, core_kind: { hole: 1, wall: 1 },
  terrain: { open: 1.5, scatter: 2, caves: 0.6, rooms: 0.6, lanes: 0.4, rings: 0.5, rows: 0.4, labyrinth: 0.7, spiral: 0.6, pillars: 0.9, cells: 0.8, diagonals: 0.7, tunnels: 0.5, city: 0.7, serpentine: 0.4, radial: 0.6 },
  wall_density: [0.01, 0.1], holes: { none: 4, lakes: 1.2, moat: 1, pits: 1.5 }, hole_amount: [0.02, 0.12],
  bushes: { none: 2, blobs: 2, patches: 2, strips: 1.5 }, bush_amount: [0.02, 0.3], max_bush_clusters: 32,
  spawn_mode: { far: 4, corner: 2, mid: 2, near: 1.2 },
  camp_mode: { standard: 4, golem: 1, monolith: 1, 'gem-centre': 1, 'huge-shared': 0.8, tiny: 1, sparse: 1, dense: 1, monsters: 0.7, clusters: 0.3 },
  camp_bias: { near: 1, spread: 3, contested: 1.5 }, vaults: 0, min_reach: 0.2, scale_counts: true, carve_width: { 1: 1, 2: 3, 3: 1 },
};

// Camp economies, layered over the preset.
const CAMP_MODES = {
  standard: {},
  golem: { camp_mix: { golem: 3, golem_gold: 2, golem_pair: 1, golem_gems: 1, golem_wolves: 1, gold: 2, wolf: 1 }, groups: [3, 9] },
  monolith: { monoliths: [2, 3], monolith_ring: 0.3, groups: [2, 7], monolith_band: { near: 1, mid: 2, contested: 2 } },
  'gem-centre': { camp_mix: { gold: 3, gold_row: 1, golem_gold: 0.3 }, camp_bias: 'near', contested_groups: [2, 5], contested_mix: { elk_gems: 2, gems: 2, golem_gems: 1, elk_pair: 1, golem: 1 } },
  'huge-shared': { shared_big: true, camp_mix: { gold: 2, gold_row: 1, wolf: 1.5, elk: 1, gems: 1 }, groups: [3, 8], monoliths: 0 },
  tiny: { camp_mix: { wolf: 3, gem: 3, gold: 2, elk: 1 }, groups: [16, 36] },
  sparse: { groups: [2, 4], camp_mix: { elk_gems: 2, golem_gems: 1, wolf_pack: 1, gold_gems: 1, golem: 1, monolith_gold: 0.3 } },
  dense: { groups: [20, 34], camp_spawn_gap: 4 },
  monsters: { camp_mix: { wolf: 3, wolf_pair: 2, wolf_pack: 1, elk: 2, elk_pair: 1, golem: 1, golem_wolves: 0.5 } },
  clusters: { camp_mix: { gems: 3, gold: 2, gold_gems: 1, gem: 1 }, monoliths: 0 },
  // Economy extremes: a gem drought (the round-2000 tiebreaks decide), a gem flood (1000 is in
  // reach), gold everywhere or almost none, and one jackpot worth more than the rest of the map.
  poor: { groups: [1, 4], camp_mix: { wolf: 3, gold: 3, gem: 1, elk_gold: 0.5 }, monoliths: 0, gem_min: 8, gem_max: 80 },
  rich: { groups: [8, 16], camp_mix: { elk_gems: 3, golem_gems: 1.5, elk_pair: 1.5, gems: 3, golem_pair: 0.5, gold_gems: 1 }, gem_min: 350 },
  'gold-rich': { groups: [8, 16], camp_mix: { gold: 3, gold_row: 3, golem_gold: 1, elk_gold: 2, gem: 1 } },
  'gold-poor': { camp_mix: { gems: 3, gem: 2, elk_gems: 2, wolf: 1 } },
  jackpot: { groups: [2, 5], camp_mix: { wolf: 2, gold: 2, gem: 1 }, monoliths: 0 },
  // Composed groups of 4-32 cells among the usual templates.
  packs: { groups: [3, 9], camp_mix: { poly: 2, snake: 1.5, carpet: 1, ring: 1, pack: 1, wolf: 1, elk_gold: 1, gems: 1, gold: 1 }, camp_spawn_gap: 4 },
  // Gem clusters only, no gold source (calibration 2; 7 of the 128 ladder maps).
  'gems-only': { camp_mix: { gem_group: 1 }, monoliths: 0, shared_gold: 0, gem_only: true },
};

// The base of the designed presets: the designer lays out terrain and named objectives; the
// filler groups and altars scale with the area.
const DESIGN = {
  size: [36, 80], aspect: { square: 3, wide: 1.5 }, symmetry: { rotational: 4, horizontal: 2, vertical: 2 }, picks: { 3: 1, 4: 1.5, 5: 2 },
  camp_mode: { standard: 5, poor: 1, rich: 1, 'gold-rich': 0.7, 'gold-poor': 0.7, jackpot: 0.8, golem: 0.4, sparse: 0.4, dense: 0.4 },
  groups: [2, 8], scale_counts: true, altars: { 0: 4, 1: 1 }, altar_mode: { central: 3, contested: 1, spread: 0.5 }, camp_bias: { spread: 3, contested: 1, near: 1 },
  monoliths: 0, shared_camp: 0, vaults: 0, max_bush_clusters: 30, loops: [0.15, 0.4], min_reach: 0.12, camp_spawn_gap: 4, void_kind: { hole: 3, wall: 1 }, terrain: 'open',
};

const designed = (doc, design, spec = {}) => ({ doc, design, designed: true, family: 'designed', ...spec });

const exotic = (doc, spec = {}) => ({ doc, exotic: true, family: 'exotic', ...spec });

// A preset's family, for suite mixes and index.json's kind: designed, exotic, ladder-like, quirks,
// or the extension module (topology, scenarios) that defines it.
export const familyOf = preset => PRESETS[preset].family ?? 'ladder-like';

export const PRESETS = {
  'small-brawl': { doc: 'Small open map, 3 picks, few altars and nearby camps', size: [30, 36], aspect: 'square', picks: 3, terrain: { open: 1, scatter: 2 }, wall_density: [0.01, 0.04], altars: [1, 2], groups: [3, 6], camp_bias: 'near', spawn_size: 3 },
  maze: { doc: 'Rooms joined by narrow doors (chokepoints)', size: [40, 70], terrain: 'rooms', door_width: [1, 2], room_size: [6, 10], picks: [3, 4], holes: { none: 3, pits: 1 }, groups: [5, 10] },
  caves: { doc: 'Cellular-automaton caverns with carved tunnels', size: [40, 80], terrain: 'caves', bushes: { none: 1, blobs: 2 }, holes: { none: 2, lakes: 1 } },
  lanes: { doc: 'Long map with parallel lanes and crossings', size: [80, 100], aspect: 'lanes', terrain: 'lanes', spawn_place: 'edge', holes: 'none', bushes: { strips: 2, patches: 1 } },
  lakes: { doc: 'Large lakes of holes crossed by carved bridges', size: [50, 80], terrain: { open: 1, scatter: 1 }, wall_density: [0.01, 0.04], holes: 'lakes', hole_amount: [0.2, 0.32], hole_cost: 0.6, carve_width: 2 },
  jungle: { doc: 'Heavy bush cover for vision games', max_bush_clusters: 40, size: [40, 70], bushes: { blobs: 2, patches: 1 }, bush_amount: [0.25, 0.4], terrain: { open: 1, scatter: 2 } },
  monolith: { doc: 'A monolith per side (often ringed by gem clusters)', size: [40, 64], monoliths: 1, monolith_ring: 0.7, groups: [4, 10] },
  rows: { doc: 'Staggered parallel wall rows', size: [40, 70], terrain: 'rows', bushes: { strips: 1, blobs: 1 } },
  'altar-rich': { doc: 'Six to nine altars per side plus a shared one', size: [50, 80], altars: [6, 9], shared_altar: 1, altar_spacing: [5, 6], altar_mode: 'spread' },
  'altar-poor': { doc: 'A single, contested altar per side', size: [40, 70], altars: 1, altar_near: 0, altar_bands: { contested: 1 }, shared_altar: 0, altar_mode: 'spread' },
  'contested-centre': { doc: 'Shared camp group and altar straddling the centre', size: [40, 60], shared_camp: 1, shared_altar: 1, need_shared_altar: true, camp_bias: 'contested', altar_mode: { spread: 1, central: 1 } },
  vaults: { doc: 'One or two walled pockets reachable only by teleport crystal', size: [40, 70], vaults: [1, 2], need_access: 'teleport' },
  tiny: { doc: '30x30, 5 picks, crowded', size: 30, aspect: 'square', picks: 5, groups: [3, 7] },
  huge: { doc: 'Large map (80-100), many objectives', size: [80, 100], aspect: { square: 3, wide: 1 }, picks: [4, 5], terrain: { scatter: 3, caves: 1, rooms: 1, rows: 1, open: 0.5 }, wall_density: [0.05, 0.12], altars: [3, 5], groups: [14, 24] },
  random: { doc: 'Everything sampled from the full legal space' },
  ladder: { doc: 'Every dimension at the ladder\'s rates (calibration 2, fitted 2026-11-05 to the 128 ladder maps)', groups: [3, 16] },
  ladder05: { doc: 'The 05 maps\' style (with --calib 4, as in --mix ladder-v3): guarded compact blocks, 3x3 spawns kept clear', groups: [3, 14] },
  'monolith-only': {
    doc: 'One to three monoliths per side are the only gem source; every other camp is gold (like the ladder map "contest")',
    size: [40, 70], picks: { 4: 1, 5: 3 }, terrain: { open: 2, scatter: 3, rows: 0.5 }, wall_density: [0.01, 0.08],
    holes: { none: 3, pits: 1, moat: 1 }, hole_amount: [0.01, 0.05], bushes: { none: 2, patches: 2, strips: 1 }, bush_amount: [0.01, 0.06],
    altars: [1, 3], altar_bands: { mid: 1, contested: 2 }, altar_mode: { spread: 2, central: 2, own: 1 }, monoliths: [1, 3], monolith_ring: 0, groups: [4, 9], camp_mix: { gold: 3, gold_row: 1 }, shared_camp: 0, vaults: 0,
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
    altars: [1, 4], groups: [4, 12], scale_counts: true, monoliths: { 0: 4, 1: 1 }, shared_camp: 0.15,
  },
  // Exotic: the playable area is a shape, the rest hole or wall.
  round: exotic('Round, diamond or rounded-square playable area', { shape: { circle: 2, diamond: 1 }, aspect: { square: 3, wide: 1 }, terrain: { open: 2, scatter: 2, radial: 2, rings: 1, pillars: 1, cells: 0.5, spiral: 0.6 } }),
  star: exotic('Star-shaped playable area with 3-8 points', { shape: 'star', aspect: { square: 3, wide: 1 }, terrain: { open: 3, scatter: 2, pillars: 1, radial: 1, cells: 0.5 } }),
  donut: exotic('Ring-shaped playable area around a hole or wall core', { shape: 'donut', aspect: { square: 3, wide: 1 }, terrain: { open: 3, scatter: 2, pillars: 1, radial: 1, cells: 0.5 } }),
  cross: exotic('Plus, X or H-shaped playable area, sometimes with a central plaza', { shape: 'cross', terrain: { open: 3, scatter: 2, pillars: 1, city: 0.5 } }),
  hourglass: exotic('Two wedges joined by a narrow neck in the middle', { shape: 'hourglass', terrain: { open: 3, scatter: 2, pillars: 1, cells: 0.5 } }),
  band: exotic('Diagonal strip between opposite corners', { shape: 'band', symmetry: 'rotational', spawn_mode: { far: 3, mid: 1 }, terrain: { open: 3, scatter: 2, pillars: 1, diagonals: 1 } }),
  chambers: exotic('Rooms in solid rock joined by tunnels', { shape: { islands: 1, lattice: 1.5 }, void_kind: 'wall', terrain: { open: 3, scatter: 1, pillars: 1 } }),
  blob: exotic('Organic noise-shaped playable area', { shape: 'blob', terrain: { open: 2, scatter: 2, caves: 0.5, pillars: 1 } }),
  // Exotic interiors.
  labyrinth: exotic('Braided maze of 1-3 wide corridors with a few plazas', { terrain: 'labyrinth', shape: { none: 4, circle: 1, donut: 0.5, diamond: 0.5 }, holes: 'none', bushes: { none: 2, patches: 1 } }),
  spiral: exotic('Spiral walls winding from the centre', { terrain: 'spiral', shape: { none: 3, circle: 2, diamond: 0.5 }, aspect: { square: 4, wide: 1 } }),
  pillars: exotic('Regular grid of wall, hole or bush pillars', { terrain: 'pillars', shape: { none: 3, circle: 1, donut: 0.5 }, holes: 'none', bushes: { none: 3, patches: 1 }, bush_amount: [0.02, 0.06] }),
  cells: exotic('Voronoi cells with doors between them', { terrain: 'cells', shape: { none: 4, circle: 1, donut: 0.5 } }),
  diagonals: exotic('Parallel diagonal bands broken by gaps', { terrain: 'diagonals' }),
  tunnels: exotic('Cramped random-walk tunnels through solid rock', { terrain: 'tunnels', shape: 'none', holes: 'none', bushes: { none: 3, patches: 1 }, size: [30, 80] }),
  city: exotic('Blocks of buildings, parks and ponds on a street grid', { terrain: 'city', holes: 'none' }),
  serpentine: exotic('Comb walls making one long winding corridor between the spawns', { terrain: 'serpentine', shape: 'none', spawn_mode: 'far', holes: { none: 3, pits: 1 }, size: [30, 80] }),
  'open-field': exotic('Nearly empty open ground', { terrain: 'open', shape: { none: 3, circle: 1, diamond: 1 }, holes: { none: 3, pits: 1 }, hole_amount: [0.01, 0.03], bushes: { none: 2, patches: 1 }, bush_amount: [0.01, 0.06] }),
  'long-thin': exotic('Long thin map (aspect 2.4-3.3)', { aspect: 'thin', size: [80, 100], shape: 'none', spawn_mode: 'far', terrain: { open: 1, scatter: 2, lanes: 1.5, pillars: 1, diagonals: 1, serpentine: 0.5, city: 0.5, cells: 0.5 } }),
  // Exotic spawn distances.
  'close-spawns': exotic('Spawns close together', { spawn_mode: 'near', size: [40, 100], shape: { none: 4, circle: 1, donut: 1, cross: 0.5 } }),
  'far-spawns': exotic('Large map with spawns as far apart as it allows', { spawn_mode: { corner: 1, far: 1 }, size: [70, 100] }),
  // Exotic economies.
  'golem-heavy': exotic('Golems are the main camps', { camp_mode: 'golem' }),
  'gem-centre': exotic('Gold-only home sides; the gem camps are all in the contested middle', { camp_mode: 'gem-centre' }),
  'huge-shared': exotic('One big shared group on the symmetry axis (from a lone Monolith or Golem to a block of Golems and Elk)', { camp_mode: 'huge-shared' }),
  'tiny-groups': exotic('Many single-tile camp groups', { camp_mode: 'tiny' }),
  'sparse-camps': exotic('Two to four rich camp groups per side', { camp_mode: 'sparse' }),
  'dense-camps': exotic('Twenty to thirty-four groups per side (scaled to size)', { camp_mode: 'dense' }),
  'monsters-only': exotic('Wolves, Elk and Golems, no clusters', { camp_mode: 'monsters' }),
  'clusters-only': exotic('Gem and gold clusters only, no monsters', { camp_mode: 'clusters' }),
  'gem-drought': exotic('Under 80 gems per side on the map at once: games run to round 2000 and the tiebreaks decide', { camp_mode: 'poor', shape: { none: 3, circle: 1 } }),
  'gem-flood': exotic('Over 350 gems per side: a race to 1000', { camp_mode: 'rich', shape: { none: 3, circle: 1 } }),
  // Constraints the other presets keep, relaxed as far as the ladder (or the engine) goes.
  'big-groups': { family: 'quirks', doc: 'Composed camp groups of 4-32 cells (packs, snakes, carpets, rings) beside the usual templates', size: [40, 90], camp_mode: 'packs', terrain: { open: 1, scatter: 3, caves: 1, rooms: 1, rows: 0.5 }, wall_density: [0.02, 0.08], scale_counts: true, groups: [3, 8] },
  wild: exotic('Diagonally touching groups, camps by altars and spawns, adjacent altars, odd spawn rectangles, cramped and close (even touching) spawns', {
    group_gap: [0, 1], camp_altar_gap: [0, 1], altar_crowd: [1, 4], altar_spacing: [1, 6], spawn_reach_gap: [-3, 2], camp_spawn_gap: [1, 5], spawn_clear: [0, 2], spawn_floor: [3, 18],
    spawn_dims: { '3x3': 3, '4x4': 2, '4x3': 2, '5x2': 1.5, '3x5': 1, '2x6': 0.7, '2x8': 0.5, '1x9': 0.4 }, spawn_mode: { far: 2, corner: 1, mid: 2, near: 2, touch: 1 },
    camp_mode: { standard: 2, packs: 2, dense: 1, tiny: 1, sparse: 1 }, family: 'quirks',
  }),
  'gold-flood': exotic('Gold clusters everywhere: shopping decides', { camp_mode: 'gold-rich', shape: { none: 3, circle: 1 } }),
  // Designed scenarios (design.mjs).
  atoll: designed('A central treasure island reached only across stepping stones a dash (or crystal) apart; home islands pay gold', 'islands',
    { layout: 'atoll', void_kind: 'hole', size: [44, 76], aspect: { square: 4, wide: 1 }, groups: [1, 4] }),
  archipelago: designed('Islands joined by walked bridges, dash crossings and crystal-only gaps', 'islands',
    { layout: { graph: 2, chain: 1 }, void_kind: { hole: 4, wall: 1 }, size: [44, 84], groups: [2, 6], need_access: 'off' }),
  rivers: designed('Rivers of holes (or ravines) with bridges, dash fords, bushy banks and a lake', 'rivers',
    { layout: { divide: 2, tributary: 2, lanes: 1.5 }, size: [40, 90], aspect: { square: 2, wide: 1.5 }, groups: [3, 9] }),
  fortress: designed('A walled keep holding the treasure, its gates open, bush, camp-plugged, dash-moated or sealed; walled home courtyards', 'fortress',
    { size: [44, 84], aspect: { square: 4, wide: 1 }, groups: [3, 8] }),
  gatekeeper: designed('A wall or chasm between the halves crossed only at gates: open, bush, plugged by a camp group, dash or a thinned wall', 'barrier',
    { size: [40, 80], symmetry: { horizontal: 2, vertical: 2, rotational: 1.5 }, groups: [3, 8] }),
  dungeon: designed('Rooms and corridors (a spanning tree plus loops) with pillared halls, gardens, pools, treasure rooms and shrines', 'dungeon',
    { size: [40, 80], void_kind: { wall: 4, hole: 1 }, groups: [1, 5] }),
  'three-lane': designed('Corner bases joined by three lanes with jungle clearings between, a river and a boss at the centre', 'three-lane',
    { symmetry: 'rotational', aspect: 'square', size: [50, 90], void_kind: { wall: 3, hole: 1 }, groups: [1, 5] }),
  arena: designed('A small shaped arena: a jackpot in the middle, cover rings, a thin home economy (fight-centric)', 'arena',
    { size: [30, 46], aspect: { square: 3, wide: 1 }, spawn_floor: 12, spawn_max: 1.3, groups: [0, 3], altars: 0,
      camp_mode: { standard: 2, poor: 2, jackpot: 2, rich: 0.5 } }),
  farmland: designed('Fenced fields of camps on each half, divided by a river or wall crossed far from the spawns (farm-centric)', 'farmland',
    { size: [60, 100], symmetry: { horizontal: 2, vertical: 2, rotational: 1 }, groups: [2, 8], camp_mode: { standard: 3, 'gold-rich': 1, dense: 1, rich: 1, poor: 0.5 } }),
  continent: designed('An organic landmass of lobes and isthmuses in a sea of holes or rock, sometimes a dash strait', 'continent',
    { size: [40, 90], aspect: { square: 2, wide: 1.5 }, void_kind: { hole: 3, wall: 1 }, groups: [2, 8] }),
  hedges: designed('A maze of bush hedges (walkable, sight-blocking) with some walls and plazas (vision-centric)', 'hedges',
    { size: [36, 70], max_bush_clusters: 60, groups: [2, 7] }),
};

// Extension modules (topology.mjs, scenarios.mjs) add presets, designers, camp economies and
// templates; none may replace an existing one.
const DESIGN_FNS = { ...DESIGNS };
for (const [family, mod] of [['topology', TOPOLOGY], ['scenarios', SCENARIOS], ['paradigms', PARADIGMS]])
  for (const [table, add] of [[PRESETS, mod.PRESETS], [DESIGN_FNS, mod.DESIGNS], [CAMP_MODES, mod.CAMP_MODES], [TEMPLATES, mod.TEMPLATES]])
    for (const [k, v] of Object.entries(add ?? {})) { if (k in table) throw new Error(`${k} is already defined`); table[k] = table === PRESETS ? { family, ...v } : v; }

function sampleValue(rng, v) {
  if (Array.isArray(v)) return Number.isInteger(v[0]) && Number.isInteger(v[1]) ? rng.int(v[0], v[1]) : rng.uniform(v[0], v[1]);
  if (v && typeof v === 'object') { const k = rng.weighted(v); return /^\d+$/.test(k) ? +k : k; }
  return v;
}

const KEEP_OBJECT = new Set(['camp_mix', 'altar_bands', 'contested_mix', 'camp_bands']);

const SKIP_KEYS = new Set(['doc', 'exotic', 'altar_zone', 'designed', 'family']);

function sampleSpecV2(rng, preset, overrides) {
  const v3 = overrides.calib >= 3, v4 = overrides.calib >= 4, p = PRESETS[preset], fit = POOL_FIT[overrides.fit];
  const layers = [v4 ? DEFAULTS_V4 : v3 ? DEFAULTS_V3 : DEFAULTS_V2, fit ?? {}, p.exotic ? EXOTIC : {}, p.design ? DESIGN : {}, p, V2_PRESETS[preset] ?? {}, (v3 && V3_PRESETS[preset]) || {}, (v4 && V4_PRESETS[preset]) || {}];
  const campMode = sampleValue(rng, overrides.camp_mode ?? Object.assign({}, ...layers).camp_mode);
  const src = Object.assign({}, ...layers, CAMP_MODES[campMode], overrides, { camp_mode: campMode }), spec = { preset };
  if (src.altar_zone === 'mid') src.altar_mode = 'central';
  for (const [k, v] of Object.entries(src)) {
    if (SKIP_KEYS.has(k) || v === undefined) continue;
    spec[k] = KEEP_OBJECT.has(k) && typeof v === 'object' && !Array.isArray(v) ? v : sampleValue(rng, v);
  }
  for (const k of ['spawn_bush', 'altar_near', 'shared_altar', 'home_camp', 'winding', 'unleak', 'unnarrow', 'altar_twin', 'dash_cuts', 'starter', 'border_clear']) if (typeof spec[k] === 'number') spec[k] = rng.chance(spec[k]);
  if (spec.spawn_mode === 'none') delete spec.spawn_mode;
  // A shaped arena needs a spawn inside its mask, which only placeSpawnMode looks for.
  if (fit && spec.shape && spec.shape !== 'none' && !spec.spawn_mode) spec.spawn_mode = 'far';
  if (typeof spec.camp_bias !== 'string') spec.camp_bias = 'spread';
  if (typeof spec.lake_amount === 'string') spec.lake_amount = rng.uniform(...spec.lake_amount.split('-').map(Number));
  if (typeof spec.bush_amount === 'string') spec.bush_amount = rng.uniform(...spec.bush_amount.split('-').map(Number));
  let W, H, n = spec.size === 'ladder' ? rng.int(...rng.weighted(LADDER_LONG).split('-').map(Number)) : spec.size;
  if (spec.aspect === 'ladder') {
    const a = rng.weighted(LADDER_ASPECT), r = a === '1' ? 1 : a === 'mild' ? rng.uniform(1.05, 1.35) : a === 'medium' ? rng.uniform(1.4, 1.8) : rng.uniform(2, 3.1);
    W = n; H = Math.min(n, Math.max(30, Math.round(n / r)));
    if (H !== W && rng.chance(0.2)) [W, H] = [H, W];
    spec.aspect = H === W ? 'square' : r >= 2 ? 'thin' : 'wide';
  } else {
    W = H = n;
    if (spec.aspect === 'wide') { H = Math.max(28, Math.round(n * rng.uniform(0.55, 0.85))); }
    else if (spec.aspect === 'lanes') { H = rng.int(30, 40); }
    else if (spec.aspect === 'thin') { H = Math.max(28, Math.round(n / rng.uniform(2.4, 3.3))); }
    if (spec.aspect !== 'square' && rng.chance(0.5)) [W, H] = [H, W];
  }
  if ((spec.aspect === 'lanes' || spec.aspect === 'thin') && !(overrides.symmetry || typeof p.symmetry === 'string'))
    spec.symmetry = W > H ? rng.choice(['horizontal', 'rotational']) : rng.choice(['vertical', 'rotational']);
  // Altars: the preset's own count of pairs (and maybe one self-mirrored altar), else the ladder's make-up.
  const fromCfg = spec.altars === undefined;
  if (fromCfg) [spec.altars, spec.shared_altars] = spec.altar_cfg.split('+').map(Number);
  else spec.shared_altars = spec.shared_altar ? 1 : 0;
  if (spec.altar_mode === 'single') { spec.shared_altars = Math.max(1, spec.shared_altars); spec.altars = 0; }
  // Rotation has one self-mirrored tile (the centre, on odd sides); a mirror axis has a line of them.
  if (spec.shared_altars > 1 && spec.symmetry === 'rotational') {
    if (overrides.symmetry || typeof p.symmetry === 'string') spec.shared_altars = 1;
    else spec.symmetry = W > H ? 'horizontal' : H > W ? 'vertical' : rng.choice(['horizontal', 'vertical']);
  }
  const odd = v => v % 2 ? v : v < 100 ? v + 1 : v - 1;
  if (spec.shared_altars) { if (spec.symmetry !== 'vertical') W = odd(W); if (spec.symmetry !== 'horizontal') H = odd(H); }
  spec.width = W; spec.height = H;
  if (spec.shared_groups === 'sym') spec.shared_groups = +rng.weighted((v4 ? SHARED_BY_SYM_V4 : v3 ? SHARED_BY_SYM_V3 : SHARED_BY_SYM)[spec.symmetry === 'rotational' ? 'rotational' : 'mirror']);
  if (spec.picks === 'area') spec.picks = +rng.weighted(PICKS_BY_AREA.find(([lim]) => W * H < lim)[1]);
  const scale = W * H / 2500;
  if (spec.group_scale && !spec.scale_counts) spec.groups = Math.max(2, Math.round(spec.groups * scale ** spec.group_scale));
  if (spec.scale_counts) { spec.groups = Math.max(2, Math.round(spec.groups * Math.sqrt(scale))); if (!fromCfg) spec.altars = Math.max(spec.design ? 0 : 1, Math.min(5, Math.round(spec.altars * Math.sqrt(scale)))); }
  if (spec.altar_mode === 'many') { spec.altars = rng.int(5, 9); spec.altar_spacing = rng.int(4, 6); }
  delete spec.altar_cfg;
  spec.spawn_min = spec.spawn_min_abs !== undefined ? spec.spawn_min_abs : spec.spawn_floor !== undefined && !spec.design ? spec.spawn_floor : spec.design ? Math.max(spec.spawn_floor ?? 18, 0.3 * Math.max(W, H)) : spec.spawn_mode === 'near' ? 16 : spec.spawn_mode === 'mid' ? 20 : Math.max(12, (spec.spawn_mode ? 0.4 : 0.42) * Math.max(W, H));
  // Close spawns: the ladder's are 8-36 tiles apart on foot, under the size-scaled walk floor. placeSpawnMode's pool
  // already bounds the gap (a walk is never shorter), so that floor goes.
  if (fit && (spec.spawn_mode === 'near' || spec.spawn_mode === 'mid')) spec.spawn_min = 1;
  return spec;
}

export function sampleSpec(rng, preset, overrides = {}) {
  if (overrides.calib >= 2) return sampleSpecV2(rng, preset, overrides);
  const p = PRESETS[preset], layers = [DEFAULTS, p.exotic ? EXOTIC : {}, p.design ? DESIGN : {}, p];
  const campMode = sampleValue(rng, overrides.camp_mode ?? Object.assign({}, ...layers).camp_mode);
  const src = Object.assign({}, ...layers, CAMP_MODES[campMode], overrides, { camp_mode: campMode }), spec = { preset };
  if (src.altar_zone === 'mid') src.altar_mode = 'central';
  for (const [k, v] of Object.entries(src)) {
    if (k === 'doc' || k === 'exotic' || k === 'altar_zone' || k === 'designed' || k === 'family') continue;
    spec[k] = KEEP_OBJECT.has(k) && typeof v === 'object' && !Array.isArray(v) ? v : sampleValue(rng, v);
  }
  for (const k of ['spawn_bush', 'altar_near', 'shared_altar', 'shared_camp']) if (typeof spec[k] === 'number') spec[k] = rng.chance(spec[k]);
  if (typeof spec.camp_bias !== 'string') spec.camp_bias = 'spread';
  const n = spec.size;
  let W = n, H = n;
  if (spec.aspect === 'wide') { H = Math.max(30, Math.round(n * rng.uniform(0.55, 0.85))); }
  else if (spec.aspect === 'lanes') { H = rng.int(30, 40); }
  else if (spec.aspect === 'thin') { H = Math.max(30, Math.round(n / rng.uniform(2.4, 3.3))); }
  if (spec.aspect !== 'square' && rng.chance(0.5)) [W, H] = [H, W];
  spec.width = W; spec.height = H;
  if ((spec.aspect === 'lanes' || spec.aspect === 'thin') && !(overrides.symmetry || typeof p.symmetry === 'string'))
    spec.symmetry = W > H ? rng.choice(['horizontal', 'rotational']) : rng.choice(['vertical', 'rotational']);
  const scale = W * H / 2500;
  if (preset === 'random' || spec.scale_counts) { spec.groups = Math.max(2, Math.round(spec.groups * Math.sqrt(scale))); spec.altars = Math.max(spec.design ? 0 : 1, Math.min(5, Math.round(spec.altars * Math.sqrt(scale)))); }
  if (spec.altar_mode === 'many') { spec.altars = rng.int(5, 9); spec.altar_spacing = rng.int(4, 6); }
  // Close spawns stay out of each other's sight (spawn_dist 18 is the ladder's closest, elk-arena).
  spec.spawn_min = spec.spawn_min_abs !== undefined ? spec.spawn_min_abs : spec.spawn_floor !== undefined && !spec.design ? spec.spawn_floor : spec.design ? Math.max(spec.spawn_floor ?? 18, 0.3 * Math.max(W, H)) : spec.spawn_mode === 'near' ? 18 : spec.spawn_mode === 'mid' ? 20 : Math.max(20, (spec.spawn_mode ? 0.4 : 0.45) * Math.max(W, H));
  return spec;
}

// The calibration generate() uses unless overrides.calib says otherwise (1: the 2026-10-30 one, as it was).
export const CALIB = 2;

export function generate(preset, seed, overrides = {}, attempts = 40) {
  const { calib = CALIB, ...rest } = overrides;
  overrides = calib >= 2 ? { ...rest, calib } : rest;
  let last;
  for (let attempt = 0; attempt < attempts; attempt++) {
    const rng = makeRng(`${preset}:${seed}:${attempt}`), spec = sampleSpec(rng, preset, overrides);
    try {
      const g = new Grid(spec.width, spec.height, spec.symmetry);
      g.picks = spec.picks;
      if (spec.design) {
        DESIGN_FNS[spec.design](g, rng, spec);
        pruneBushes(g, 3, spec.max_bush_clusters);
        // Nothing after the design makes a tile walkable, so its reach on foot bounds the final map's (gate):
        // failing now skips the placement (atoll and archipelago failed most attempts here, 2026-10-29).
        if (Math.round(1000 * spawnFields(g, null, 0, 'A').dA.reduce((n, d) => n + (d >= 0), 0) / g.t.length) / 1000 < spec.min_reach)
          throw new GenFail('walkable and reachable area too small');
        placeSites(g, rng, spec);
        if (spec.altars) placeAltars(g, rng, spec);
        placeCamps(g, rng, spec);
        sealPockets(g);
        return finish(g, preset, seed, attempt, overrides, spec);
      }
      g.mask = shapeMask(g, rng, spec);
      TERRAIN[spec.terrain](g, rng, spec);
      const barrier = spec.border_clear && spec.winding ? new Uint8Array(g.t.length) : null;
      if (spec.winding) barriers(g, rng, spec, barrier);
      if (g.mask) applyMask(g, g.mask, spec);
      holes(g, rng, spec);
      despeckle(g);
      if (spec.border_clear && !g.mask && spec.holes !== 'moat') clearBorder(g, barrier);
      bushes(g, rng, spec);
      g.symmetrize();
      if (spec.unleak || spec.unnarrow) tidy(g, spec);
      if (spec.shared_gems || spec.shared_big) reserveShared(g, rng, spec);
      pruneBushes(g, 4, spec.max_bush_clusters);
      if (spec.spawn_mode) placeSpawnMode(g, rng, spec); else placeSpawn(g, rng, spec);
      // Paradigms drawn around the spawns (paradigms.mjs); no other preset sets post_spawn.
      if (spec.post_spawn) { PARADIGMS.POST_SPAWN[spec.post_spawn](g, rng, spec); if (spec.unleak || spec.unnarrow) tidy(g, spec); }
      connect(g, rng, spec);
      placeVaults(g, rng, spec);
      placeAltars(g, rng, spec);
      if (spec.need_shared_altar && !g.t.some((k, i) => k === ALTAR && g.mirror(i) === i)) throw new GenFail('no shared altar');
      placeCamps(g, rng, spec);
      if (spec.shared_camp && !sideGroups(g).shared.length) throw new GenFail('shared camp did not fit');
      // dash_cuts: hole lines across narrow passages, a dash's shortcut (and now and then the only way in).
      if (spec.dash_cuts && gaps(g, rng, rng.int(1, 4))) { g.access = LEVELS[Math.max(LEVELS.indexOf(g.access ?? 'walk'), Math.min(1, naturalAccess(g)))]; if (g.access !== 'walk' && !stillConnected(g)) throw new GenFail('dash cuts sealed an objective'); }
      if (spec.unleak) tidy(g, { unleak: true }, g.vaults, true);
      sealPockets(g);
      return finish(g, preset, seed, attempt, overrides, spec);
    } catch (e) {
      if (!(e instanceof GenFail)) throw e;
      last = e.message;
    }
  }
  throw new GenFail(`${preset}:${seed} failed after ${attempts} attempts (last: ${last})`);
}

function finish(g, preset, seed, attempt, overrides, spec) {
  const { errors } = validate(g, { minSide: spec.calib >= 2 ? 28 : 30 });
  if (errors.length) throw new GenFail(errors[0]);
  const met = metrics(g);
  const why = gate(met, g, spec);
  if (why) throw new GenFail(why);
  g.meta = { preset, seed, attempt, overrides, spec, metrics: met, ...(g.gated && { gated: true }) };
  return g;
}

// Wall stubs left poking into holes (walls are drawn before the hole features) become holes.
function despeckle(g) {
  for (let i = 0; i < g.t.length; i++) {
    if (g.t[i] !== WALL) continue;
    const x = i % g.W, y = (i - x) / g.W;
    let holes = 0, walls = 0;
    for (const [dx, dy] of N4) if (g.in(x + dx, y + dy)) { const k = g.get(x + dx, y + dy); holes += k === HOLE; walls += k === WALL; }
    if (holes >= 2 && walls <= 1) g.t[i] = HOLE;
  }
}

// Walkable tiles no spawn reaches at the map's access (pockets an altar sealed) become holes:
// transparent and unwalkable as before, but no teleport destination. Vaults stay.
function sealPockets(g) {
  const f = spawnFields(g), spawns = new Set([...g.spawnTiles(0), ...g.spawnTiles(1)]);
  for (let i = 0; i < g.t.length; i++) if (f.pass[i] && f.dA[i] < 0 && f.dB[i] < 0 && !spawns.has(i) && !g.vaults.has(i)) g.t[i] = HOLE;
}

const ZONE_FOR_MODE = { central: 'mid', single: 'mid', own: 'own', hub: 'mid' };

function gate(met, g, spec) {
  if (met.reach_frac < spec.min_reach) return `only ${Math.round(100 * met.reach_frac)}% walkable and reachable`;
  if (met.spawn_dist < spec.spawn_min) return `spawns ${met.spawn_dist} apart`;
  if (met.spawn_rel > 3.5) return `spawns ${met.spawn_dist} apart on foot`;
  if (met.gems_side < spec.gem_min) return `only ${met.gems_side} gems per side`;
  if (spec.gem_max && met.gems_side > spec.gem_max) return `${met.gems_side} gems per side`;
  if (spec.spawn_max && met.spawn_rel > spec.spawn_max) return `spawns ${met.spawn_dist} apart`;
  // A designed map uses its whole frame: no dead band of void along an edge.
  if (spec.design) {
    const f = spawnFields(g, null, 2);
    let x0 = g.W, x1 = 0, y0 = g.H, y1 = 0;
    for (let i = 0; i < g.t.length; i++) if (f.dA[i] >= 0 || f.dB[i] >= 0) { const x = i % g.W, y = (i - x) / g.W; x0 = Math.min(x0, x); x1 = Math.max(x1, x); y0 = Math.min(y0, y); y1 = Math.max(y1, y); }
    if (x1 - x0 + 1 < 0.8 * g.W || y1 - y0 + 1 < 0.8 * g.H) return 'playable area leaves an empty band';
  }
  // The designer's layout must need what it says: e.g. an atoll's hub must not be walkable.
  if (g.intents?.length) {
    const F = accessFields(g);
    for (const it of g.intents) {
      const tiles = [];
      for (let y = Math.floor(it.at[1] - it.r); y <= it.at[1] + it.r; y++) for (let x = Math.floor(it.at[0] - it.r); x <= it.at[0] + it.r; x++)
        if (g.in(x, y) && Math.hypot(x - it.at[0], y - it.at[1]) <= it.r && (g.t[y * g.W + x] === GROUND || g.t[y * g.W + x] === BUSH)) tiles.push(y * g.W + x);
      if (!tiles.length) return 'intent area gone';
      const l = levelOf(g, F, tiles);
      if (l < LEVELS.indexOf(it.min)) return `intent: ${it.min} area reachable ${HOW[l]}`;
    }
  }
  if (spec.need_access && (spec.need_access === 'off' ? met.access === 'walk' : met.access !== spec.need_access)) return `access ${met.access}, wanted ${spec.need_access}`;
  // About twice the ladder's densest (boss-battle 8.2, then 4.8): more leaves no camp-free path.
  if (met.camp_density > 9.5) return `${met.camp_density} camps per 100 tiles`;
  if (!met.altars) return 'no altars';
  const zone = spec.design ? null : ZONE_FOR_MODE[spec.altar_mode];
  if (zone && met.altar_zone !== zone) return `nearest altar in zone ${met.altar_zone}`;
  return null;
}

export { spawnFields, stillConnected, connect, TEMPLATES, tryGroup, candidates, BANDS, PICKS_BY_AREA };
