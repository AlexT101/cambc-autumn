import { BUSH, GROUND, HOLE, WALL, valueNoise } from './grid.mjs';

export const KIND = { wall: WALL, hole: HOLE, bush: BUSH, ground: GROUND };

function fill(g, kind) { g.t.fill(kind); }

function rect(g, x0, y0, w, h, kind, only) {
  for (let y = y0; y < y0 + h; y++) for (let x = x0; x < x0 + w; x++)
    if (g.in(x, y) && (only === undefined || g.t[g.idx(x, y)] === only)) g.t[g.idx(x, y)] = kind;
}

// Rasterises a polyline 4-connectedly (a diagonal step adds the orthogonal tile), so a 1-thick line
// blocks walking. `gap(k)` leaves the k-th tile along the line open.
export function plot(g, pts, kind, thick = 1, gap = null) {
  let px = null, py = null, k = 0;
  const put = (x, y) => { for (let j = 0; j < thick; j++) for (let i = 0; i < thick; i++) if (g.in(x + i, y + j)) g.t[g.idx(x + i, y + j)] = kind; };
  for (let s = 0; s + 1 < pts.length; s++) {
    const [x0, y0] = pts[s], [x1, y1] = pts[s + 1], n = Math.ceil(2 * Math.max(Math.abs(x1 - x0), Math.abs(y1 - y0))) + 1;
    for (let t = 0; t <= n; t++) {
      const x = Math.round(x0 + (x1 - x0) * t / n), y = Math.round(y0 + (y1 - y0) * t / n);
      if (x === px && y === py) continue;
      const open = gap && gap(k++);
      if (!open) { if (px !== null && x !== px && y !== py) put(x, py); put(x, y); }
      px = x; py = y;
    }
  }
}

// ---- playable-area shapes ----------------------------------------------------------------
// Each returns f(u, v, x, y) over normalised coordinates u, v in [-1, 1]: 1 playable, 0 outside
// (filled with spec.void_kind), 2 core (filled with spec.core_kind).
export const SHAPES = {
  circle: rng => { const r = rng.uniform(0.92, 1); return (u, v) => +(u * u + v * v <= r * r); },
  // p < 1 is a concave four-pointed star, 1 a diamond, above 1 a rounded square.
  diamond: rng => { const p = rng.choice([0.6, 0.75, 1, 1, 1.4]); return (u, v) => +(Math.abs(u) ** p + Math.abs(v) ** p <= 1); },
  star: rng => {
    const k = rng.int(3, 8), a = rng.uniform(0.35, 0.6), ph = rng.uniform(0, 2 * Math.PI), p = rng.uniform(0.8, 2);
    return (u, v) => +(Math.hypot(u, v) <= a + (1 - a) * ((1 + Math.cos(k * (Math.atan2(v, u) - ph))) / 2) ** p);
  },
  donut: rng => {
    const p = rng.choice([1, 2, 2, 8]), outer = rng.uniform(0.92, 1), inner = rng.uniform(0.22, 0.5);
    const m = (u, v) => p === 8 ? Math.max(Math.abs(u), Math.abs(v)) : (Math.abs(u) ** p + Math.abs(v) ** p) ** (1 / p);
    return (u, v) => { const d = m(u, v); return d > outer ? 0 : d < inner ? 2 : 1; };
  },
  cross: rng => {
    const w = rng.uniform(0.2, 0.42), plaza = rng.chance(0.5) ? rng.uniform(0.3, 0.55) : 0, kind = rng.weighted({ plus: 3, x: 1.5, h: 1 });
    return (u, v) => {
      if (plaza && u * u + v * v <= plaza * plaza) return 1;
      if (kind === 'x') return +(Math.abs(u - v) <= w * 1.4 || Math.abs(u + v) <= w * 1.4);
      if (kind === 'h') return +(Math.abs(u) >= 1 - w || Math.abs(v) <= w * 0.8);
      return +(Math.abs(u) <= w || Math.abs(v) <= w);
    };
  },
  // Two wedges meeting at a neck in the middle.
  hourglass: rng => {
    const neck = rng.uniform(0.1, 0.28), k = rng.uniform(0.7, 1.2), alongX = rng.chance(0.5);
    return (u, v) => { if (!alongX) [u, v] = [v, u]; return +(Math.abs(v) <= Math.max(neck, Math.abs(u) * k)); };
  },
  // A diagonal strip between two opposite corners, sometimes with a round plaza in the middle.
  band: rng => {
    const w = rng.uniform(0.3, 0.6), anti = rng.chance(0.5), bulge = rng.chance(0.5) ? rng.uniform(0.35, 0.6) : 0;
    return (u, v) => +(Math.abs(anti ? u + v : u - v) / Math.SQRT2 <= w || (bulge && u * u + v * v <= bulge * bulge));
  },
  islands: rng => {
    const list = [];
    if (rng.chance(0.5)) list.push([0, 0, rng.uniform(0.15, 0.32)]);
    for (let k = rng.int(3, 8); k > 0; k--) list.push([rng.uniform(-0.85, 0.85), rng.uniform(-0.85, 0.85), rng.uniform(0.14, 0.36)]);
    return (u, v) => +list.some(([cx, cy, r]) => (u - cx) ** 2 + (v - cy) ** 2 <= r * r);
  },
  // Rectangular rooms on an irregular lattice; the tunnels between them come from connect().
  lattice: (rng, g) => {
    const nx = rng.int(2, Math.max(2, Math.floor(g.W / 12))), ny = rng.int(2, Math.max(2, Math.floor(g.H / 12))), rooms = [];
    for (let j = 0; j < ny; j++) for (let i = 0; i < nx; i++) {
      if (rng.chance(0.12)) continue;
      const cw = 2 / nx, ch = 2 / ny, mx = rng.uniform(0.08, 0.3) * cw, my = rng.uniform(0.08, 0.3) * ch;
      rooms.push([-1 + i * cw + mx, -1 + j * ch + my, -1 + (i + 1) * cw - mx, -1 + (j + 1) * ch - my]);
    }
    return (u, v) => +rooms.some(([a, b, c, d]) => u >= a && u <= c && v >= b && v <= d);
  },
  // Noise with a radial falloff, cut so that 45-75% of the map is playable.
  blob: (rng, g) => {
    const n = valueNoise(rng, g.W, g.H, rng.uniform(8, 20), 3), k = rng.uniform(0.15, 0.5), val = new Float32Array(g.W * g.H);
    for (let y = 0; y < g.H; y++) for (let x = 0; x < g.W; x++) val[y * g.W + x] = n[y * g.W + x] - k * (((2 * x - g.W + 1) / (g.W - 1)) ** 2 + ((2 * y - g.H + 1) / (g.H - 1)) ** 2);
    const cut = Float32Array.from(val).sort()[Math.floor(rng.uniform(0.25, 0.55) * val.length)];
    return (u, v, x, y) => +(val[y * g.W + x] > cut);
  },
};

// ---- interior terrain --------------------------------------------------------------------
// Perfect maze on a cell lattice, braided with extra openings, plus a few cleared plazas.
function labyrinth(g, rng, s) {
  const c = rng.int(1, 3), t = rng.int(1, 2), p = c + t, nx = Math.floor((g.W - t) / p), ny = Math.floor((g.H - t) / p);
  const ox = Math.floor((g.W - nx * p - t) / 2) + t, oy = Math.floor((g.H - ny * p - t) / 2) + t, braid = rng.uniform(0.08, 0.4);
  fill(g, WALL);
  const seen = new Uint8Array(nx * ny), cell = (i, j) => rect(g, ox + i * p, oy + j * p, c, c, GROUND);
  const join = (i, j, di, dj) => rect(g, ox + i * p + (di > 0 ? c : di < 0 ? -t : 0), oy + j * p + (dj > 0 ? c : dj < 0 ? -t : 0), di ? t : c, dj ? t : c, GROUND);
  const stack = [[rng.int(0, nx - 1), rng.int(0, ny - 1)]];
  seen[stack[0][1] * nx + stack[0][0]] = 1;
  cell(...stack[0]);
  while (stack.length) {
    const [i, j] = stack.at(-1), next = rng.shuffle([[1, 0], [-1, 0], [0, 1], [0, -1]]).filter(([di, dj]) => i + di >= 0 && j + dj >= 0 && i + di < nx && j + dj < ny && !seen[(j + dj) * nx + i + di]);
    if (!next.length) { stack.pop(); continue; }
    const [di, dj] = next[0];
    join(i, j, di, dj); cell(i + di, j + dj); seen[(j + dj) * nx + i + di] = 1; stack.push([i + di, j + dj]);
  }
  for (let j = 0; j < ny; j++) for (let i = 0; i < nx; i++) {
    if (i + 1 < nx && rng.chance(braid)) join(i, j, 1, 0);
    if (j + 1 < ny && rng.chance(braid)) join(i, j, 0, 1);
  }
  for (let k = rng.int(2, 2 + Math.floor(g.W * g.H / 900)); k > 0; k--) rect(g, rng.int(0, g.W - 5), rng.int(0, g.H - 5), rng.int(4, 9), rng.int(4, 9), GROUND);
}

function spiral(g, rng) {
  const cx = (g.W - 1) / 2, cy = (g.H - 1) / 2, arms = rng.int(1, 2), d = rng.int(6, 10), thick = rng.int(1, 2);
  const period = rng.int(14, 32), gap = rng.int(3, 5), sx = g.W / Math.max(g.W, g.H), sy = g.H / Math.max(g.W, g.H), R = Math.max(g.W, g.H) * 0.72, dir = rng.choice([1, -1]);
  for (let a = 0; a < arms; a++) {
    const ph = a * 2 * Math.PI / arms + rng.uniform(0, 2 * Math.PI), pts = [], off = rng.int(0, period);
    for (let th = 0; ; th += 0.03) {
      const r = 3 + d * arms * th / (2 * Math.PI);
      if (r > R) break;
      pts.push([cx + r * Math.cos(dir * th + ph) * sx, cy + r * Math.sin(dir * th + ph) * sy]);
    }
    plot(g, pts, WALL, thick, k => (k + off) % period < gap);
  }
}

function pillars(g, rng) {
  const sp = rng.int(3, 7), size = rng.int(1, 2), mode = rng.weighted({ wall: 3, hole: 1, bush: 1, mixed: 1.5 }), stagger = rng.chance(0.5);
  const jitter = rng.chance(0.3), skip = rng.uniform(0, 0.3), x0 = rng.int(0, sp - 1), y0 = rng.int(0, sp - 1);
  for (let y = y0, row = 0; y < g.H; y += sp, row++) for (let x = x0 + (stagger && row % 2 ? sp >> 1 : 0); x < g.W; x += sp) {
    if (rng.chance(skip)) continue;
    const kind = mode === 'mixed' ? KIND[rng.weighted({ wall: 2, hole: 1, bush: 1 })] : KIND[mode];
    rect(g, x + (jitter ? rng.int(-1, 1) : 0), y + (jitter ? rng.int(-1, 1) : 0), size, size, kind);
  }
}

// Voronoi cells walled off from each other, with a door between most neighbouring cells.
function cells(g, rng) {
  const size = rng.int(8, 16), n = Math.max(4, Math.round(g.W * g.H / (size * size))), sites = Array.from({ length: n }, () => [rng.uniform(0, g.W), rng.uniform(0, g.H)]);
  const label = new Int32Array(g.W * g.H), door = rng.int(2, 3), pairs = new Map();
  for (let y = 0; y < g.H; y++) for (let x = 0; x < g.W; x++) {
    let best = 0, bd = Infinity;
    for (let k = 0; k < n; k++) { const d = (sites[k][0] - x) ** 2 + (sites[k][1] - y) ** 2; if (d < bd) { bd = d; best = k; } }
    label[y * g.W + x] = best;
  }
  const fills = sites.map(() => rng.weighted({ none: 10, bush: 1, hole: 0.6 }));
  for (let y = 0; y < g.H; y++) for (let x = 0; x < g.W; x++) {
    const i = y * g.W + x, a = label[i];
    if (fills[a] !== 'none') g.t[i] = KIND[fills[a]];
    for (const [dx, dy] of [[1, 0], [0, 1], [1, 1]]) {
      if (!g.in(x + dx, y + dy)) continue;
      const b = label[(y + dy) * g.W + x + dx];
      if (b === a) continue;
      g.t[i] = WALL;
      const key = Math.min(a, b) * n + Math.max(a, b);
      if (!pairs.has(key)) pairs.set(key, []);
      pairs.get(key).push([x, y]);
    }
  }
  for (const list of pairs.values()) {
    if (rng.chance(0.15)) continue;
    const [x, y] = rng.choice(list);
    rect(g, x - (door >> 1), y - (door >> 1), door + 1, door + 1, GROUND, WALL);
  }
}

// Parallel 2-thick diagonal bands (diagonal steps cannot slip through), broken by gaps.
function diagonals(g, rng) {
  const kind = rng.chance(0.75) ? WALL : HOLE, sets = rng.chance(0.3) ? [false, true] : [rng.chance(0.5)];
  for (const anti of sets) {
    const sp = rng.int(6, 12) + (sets.length > 1 ? 4 : 0), per = rng.int(9, 18), gap = rng.int(2, 4) + (sets.length > 1 ? 1 : 0), phase = Array.from({ length: 64 }, () => rng.int(0, per));
    for (let y = 0; y < g.H; y++) for (let x = 0; x < g.W; x++) {
      const d = anti ? x + y : x - y + g.H, band = Math.floor(d / sp);
      if (d % sp < 2 && (x + phase[band % 64]) % per >= gap) g.t[y * g.W + x] = kind;
    }
  }
}

// Solid rock carved by random-walk tunnels of width 1-3, with the odd small room.
function tunnels(g, rng) {
  fill(g, WALL);
  const target = rng.uniform(0.3, 0.5) * g.W * g.H, wmax = rng.int(1, 3), turn = rng.uniform(0.06, 0.25), dirs = [[1, 0], [-1, 0], [0, 1], [0, -1]];
  let open = 0;
  const carve = (x, y, w) => { for (let j = 0; j < w; j++) for (let i = 0; i < w; i++) if (g.in(x + i, y + j) && g.t[g.idx(x + i, y + j)] === WALL) { g.t[g.idx(x + i, y + j)] = GROUND; open++; } };
  for (let walker = 0; open < target && walker < 400; walker++) {
    let x = walker ? rng.int(0, g.W - 1) : g.W >> 1, y = walker ? rng.int(0, g.H - 1) : g.H >> 1, [dx, dy] = rng.choice(dirs);
    const w = rng.int(1, wmax);
    if (walker && g.t[g.idx(x, y)] === WALL) continue;
    for (let step = rng.int(30, 160); step > 0 && open < target; step--) {
      carve(x, y, w);
      if (rng.chance(0.015)) carve(x - 2, y - 2, rng.int(4, 6));
      if (rng.chance(turn)) [dx, dy] = rng.choice(dirs);
      if (!g.in(x + dx, y + dy)) [dx, dy] = [-dx, -dy];
      x += dx; y += dy;
    }
  }
}

// Rectangular blocks (buildings, bush parks, ponds) on an irregular street grid.
function city(g, rng) {
  const street = rng.int(2, 4), bmin = rng.int(3, 6), bmax = bmin + rng.int(2, 6), kinds = { wall: 5, bush: 1.5, hole: 1, open: 1.2, court: 1 };
  const cuts = len => { const out = []; for (let p = rng.int(0, street + 2); p < len; ) { const b = rng.int(bmin, bmax); out.push([p, Math.min(b, len - p)]); p += b + street; } return out; };
  for (const [y, h] of cuts(g.H)) for (const [x, w] of cuts(g.W)) {
    const k = rng.weighted(kinds);
    if (k === 'open') continue;
    if (k === 'court') { rect(g, x, y, w, h, WALL); if (w > 4 && h > 4) rect(g, x + 1, y + 1, w - 2, h - 2, GROUND); rect(g, x + (w >> 1), y, 2, 1, GROUND); }
    else rect(g, x, y, w, h, KIND[k]);
  }
}

// Comb walls across the axis between the spawns, attached to alternate sides: one long winding
// corridor. Drawn symmetrically with g.set so symmetrisation keeps it.
function serpentine(g, rng) {
  const alongX = g.sym === 'horizontal' || (g.sym === 'rotational' && g.W >= g.H), len = alongX ? g.W : g.H, across = alongX ? g.H : g.W;
  const d = rng.int(5, 10), gap = rng.int(3, 6), thick = rng.int(1, 2), start = rng.int(4, 9);
  for (let p = start, k = 0; p < len / 2 - 1; p += d, k++) {
    const low = k % 2 === 0;
    for (let a = low ? 0 : gap; a < (low ? across - gap : across); a++) for (let t = 0; t < thick; t++)
      alongX ? g.set(p + t, a, WALL) : g.set(a, p + t, WALL);
  }
}

// Spokes from the centre, each broken by a gap or two, sometimes with a gated ring.
function radial(g, rng) {
  const cx = (g.W - 1) / 2, cy = (g.H - 1) / 2, k = rng.int(3, 8), ph = rng.uniform(0, Math.PI), sx = g.W / 2, sy = g.H / 2;
  const rin = rng.uniform(0.12, 0.3), rout = rng.uniform(0.6, 0.95), kind = rng.chance(0.8) ? WALL : HOLE;
  for (let s = 0; s < k; s++) {
    const a = ph + s * 2 * Math.PI / k, per = rng.int(12, 30), gap = rng.int(3, 5), off = rng.int(0, per);
    plot(g, [[cx + rin * sx * Math.cos(a), cy + rin * sy * Math.sin(a)], [cx + rout * sx * Math.cos(a), cy + rout * sy * Math.sin(a)]], kind, 1, j => (j + off) % per < gap);
  }
  if (rng.chance(0.5)) {
    const r = rng.uniform(0.35, 0.6), gates = Array.from({ length: rng.int(2, 4) }, () => rng.uniform(0, 2 * Math.PI)), half = 2.5 / (r * Math.min(sx, sy));
    let arc = [];
    for (let a = 0; a <= 2 * Math.PI + 0.02; a += 0.02) {
      if (gates.some(b => Math.abs(((a - b + 3 * Math.PI) % (2 * Math.PI)) - Math.PI) < half)) { if (arc.length > 1) plot(g, arc, kind); arc = []; continue; }
      arc.push([cx + r * sx * Math.cos(a), cy + r * sy * Math.sin(a)]);
    }
    if (arc.length > 1) plot(g, arc, kind);
  }
}

export const TERRAIN_EXTRA = { labyrinth, spiral, pillars, cells, diagonals, tunnels, city, serpentine, radial };
