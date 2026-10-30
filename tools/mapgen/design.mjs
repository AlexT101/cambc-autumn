// Designed maps: each designer lays out a scenario the way a map maker would (a layout of regions
// and links first, then coherent features: islands, rivers, keeps, rooms, lanes, hedges), and
// names its key objectives as sites for generate.mjs to fill. Everything is drawn with g.set, so it
// is symmetric as drawn. A designer sets g.access (the most an objective may need: walk, dash or
// teleport), g.sites, g.intents (access the layout must produce) and g.gated (camps plug a route).
import { BUSH, GROUND, GenFail, HOLE, WALL, valueNoise } from './grid.mjs';

// ---- geometry ------------------------------------------------------------------------------
const dist = (a, b) => Math.hypot(a[0] - b[0], a[1] - b[1]);
const lerp = (a, b, t) => [a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t];
const centre = g => [(g.W - 1) / 2, (g.H - 1) / 2];
export const mirrorPt = (g, [x, y]) => g.sym === 'horizontal' ? [g.W - 1 - x, y] : g.sym === 'vertical' ? [x, g.H - 1 - y] : [g.W - 1 - x, g.H - 1 - y];
const spawnCentre = g => [g.spawn.x + (g.spawn.w - 1) / 2, g.spawn.y + (g.spawn.h - 1) / 2];
// Team A's side: nearer A's spawn than B's.
const onSideA = (g, p) => { const s = spawnCentre(g); return dist(p, s) < dist(p, mirrorPt(g, s)); };
const inMap = (g, [x, y], m = 0) => x >= m && y >= m && x <= g.W - 1 - m && y <= g.H - 1 - m;

// ---- brushes -------------------------------------------------------------------------------
function put(g, x, y, kind, only) {
  x = Math.round(x); y = Math.round(y);
  if (!g.in(x, y) || (only && !only.includes(g.get(x, y)))) return;
  g.set(x, y, kind);
}

function box(g, x0, y0, w, h, kind, only) {
  for (let y = y0; y < y0 + h; y++) for (let x = x0; x < x0 + w; x++) put(g, x, y, kind, only);
}

function disc(g, [cx, cy], r, kind, only) {
  for (let y = Math.floor(cy - r - 1); y <= cy + r + 1; y++) for (let x = Math.floor(cx - r - 1); x <= cx + r + 1; x++)
    if ((x - cx) ** 2 + (y - cy) ** 2 <= r * r + 0.3) put(g, x, y, kind, only);
}

// A disc with a wobbly rim (a few low harmonics of the angle), so islands and lobes look drawn.
function blob(g, rng, [cx, cy], r, rough, kind, only) {
  const harm = [2, 3, 4, 5].map(k => [k, rng.uniform(0, rough) / Math.sqrt(k - 1), rng.uniform(0, 2 * Math.PI)]);
  const R = a => r * (1 + harm.reduce((s, [k, amp, ph]) => s + amp * Math.cos(k * a + ph), 0));
  const out = r * (1 + 2 * rough) + 1;
  for (let y = Math.floor(cy - out); y <= cy + out; y++) for (let x = Math.floor(cx - out); x <= cx + out; x++)
    if (Math.hypot(x - cx, y - cy) <= R(Math.atan2(y - cy, x - cx))) put(g, x, y, kind, only);
}

// A polyline painted with a square brush of width w (a number or a function of the fraction along
// it). A diagonal step also paints the orthogonal tile, so even a 1-wide line blocks walking.
function stroke(g, pts, w, kind, only) {
  const total = pts.slice(1).reduce((s, p, k) => s + dist(pts[k], p), 0) || 1;
  let done = 0, px = null, py = null;
  const brush = (x, y, t) => {
    const ww = Math.max(1, Math.round(typeof w === 'function' ? w(t) : w)), o = (ww - 1) / 2;
    for (let j = 0; j < ww; j++) for (let i = 0; i < ww; i++) put(g, x - o + i, y - o + j, kind, only);
  };
  for (let s = 0; s + 1 < pts.length; s++) {
    const len = dist(pts[s], pts[s + 1]), n = Math.max(1, Math.ceil(len * 3));
    for (let k = 0; k <= n; k++) {
      const [fx, fy] = lerp(pts[s], pts[s + 1], k / n), x = Math.round(fx), y = Math.round(fy), t = (done + len * k / n) / total;
      if (x === px && y === py) continue;
      if (px !== null && x !== px && y !== py) brush(x, py, t);
      brush(x, y, t);
      px = x; py = y;
    }
    done += len;
  }
}

// Closes diagonal-only contacts along a drawn line of `kind` (walkers slip between diagonally
// touching blockers) by filling one orthogonal tile of each.
function seal(g, tiles, kind) {
  const set = new Set(tiles.map(([x, y]) => y * g.W + x));
  for (const [x, y] of tiles) for (const [dx, dy] of [[1, 1], [1, -1]]) {
    if (!g.in(x + dx, y + dy) || !set.has((y + dy) * g.W + x + dx)) continue;
    if (g.get(x + dx, y) !== kind && g.get(x, y + dy) !== kind) put(g, x + dx, y, kind);
  }
}

// A smooth wandering path from a to b: the straight line displaced sideways by two sine waves.
function meander(rng, a, b, amp, waves = rng.uniform(0.5, 2)) {
  const len = dist(a, b), n = Math.max(2, Math.ceil(len / 1.5)), nx = -(b[1] - a[1]) / (len || 1), ny = (b[0] - a[0]) / (len || 1);
  const ph1 = rng.uniform(0, 2 * Math.PI), ph2 = rng.uniform(0, 2 * Math.PI), a2 = rng.uniform(0, 0.4);
  return Array.from({ length: n + 1 }, (_, k) => {
    const t = k / n, off = amp * len * Math.sin(Math.PI * t) * (Math.sin(waves * Math.PI * t + ph1) + a2 * Math.sin(2.7 * waves * Math.PI * t + ph2));
    return [a[0] + (b[0] - a[0]) * t + nx * off, a[1] + (b[1] - a[1]) * t + ny * off];
  });
}

// A path through the given points, rounded at the corners (Chaikin's corner cutting).
function smooth(pts, iters = 2) {
  for (let it = 0; it < iters; it++) {
    const out = [pts[0]];
    for (let k = 0; k + 1 < pts.length; k++) out.push(lerp(pts[k], pts[k + 1], 0.25), lerp(pts[k], pts[k + 1], 0.75));
    out.push(pts.at(-1));
    pts = out;
  }
  return pts;
}

// Point and tangent at fraction t of a polyline.
function along(pts, t) {
  const lens = pts.slice(1).map((p, k) => dist(pts[k], p)), total = lens.reduce((s, l) => s + l, 0);
  let want = t * total;
  for (let k = 0; k < lens.length; k++) {
    if (want <= lens[k] || k === lens.length - 1) {
      const u = lens[k] ? Math.min(1, want / lens[k]) : 0, d = [(pts[k + 1][0] - pts[k][0]) / (lens[k] || 1), (pts[k + 1][1] - pts[k][1]) / (lens[k] || 1)];
      return { p: lerp(pts[k], pts[k + 1], u), d };
    }
    want -= lens[k];
  }
  return { p: pts.at(-1), d: [1, 0] };
}

// A cut across a path at p: a band `gap` tiles thick, perpendicular to the path's dominant axis
// (axis-aligned, so a 1-thick hole cut is exactly one dash), `reach` tiles to each side.
function cut(g, p, d, gap, reach, kind, keep) {
  const alongX = Math.abs(d[0]) >= Math.abs(d[1]), x0 = Math.round(p[0] - (gap - 1) / 2), y0 = Math.round(p[1] - (gap - 1) / 2);
  for (let a = 0; a < gap; a++) for (let b = -reach; b <= reach; b++) {
    const x = alongX ? x0 + a : Math.round(p[0]) + b, y = alongX ? Math.round(p[1]) + b : y0 + a;
    if (g.in(x, y) && !keep?.(x, y)) put(g, x, y, kind);
  }
}

// Authored cover pieces: '#' takes the stamp's kind, '"' is always bush, 'o' always hole.
const PREFABS = {
  bar: ['####'], long: ['######'], ell: ['###', '#..', '#..'], tee: ['###', '.#.', '.#.'], cup: ['#..#', '#..#', '####'],
  plus: ['.#.', '###', '.#.'], pillar: ['##', '##'], post: ['#'], broken: ['##.##'], posts: ['#..#', '....', '#..#'],
  arch: ['.##.', '#..#', '#..#'], hook: ['###.', '..#.', '..##'], zig: ['##..', '.##.', '..##'],
  bunker: ['"##"', '#..#', '#..#'], skirt: ['####', '""""'], hedge: ['""""""'], copse: ['.""', '"""', '"".'], pond: ['.oo.', 'oooo', '.oo.'],
  corner: ['###', '#""', '#".'], screen: ['#"#"#'],
};

function prefabTiles(rng, rows) {
  const rot = rng.int(0, 3), flip = rng.chance(0.5), out = [];
  rows.forEach((row, j) => [...row].forEach((ch, i) => {
    if (ch === '.') return;
    let [x, y] = [flip ? row.length - 1 - i : i, j];
    for (let r = 0; r < rot; r++) [x, y] = [-y, x];
    out.push([x, y, ch]);
  }));
  return out;
}

// Stamps `n` prefabs on open ground, kept apart from each other, their mirrors and the spawns.
// `where(x, y)` filters anchor points; `kinds` weighs the kind '#' becomes.
function scatterPrefabs(g, rng, n, { names = Object.keys(PREFABS), kinds = { [WALL]: 1 }, gap = 5, where = () => true, spawnGap = 5 } = {}) {
  const placed = [];
  for (let tries = 0; placed.length < n && tries < n * 60; tries++) {
    const x = rng.int(1, g.W - 2), y = rng.int(1, g.H - 2);
    if (!where(x, y) || [...placed, ...placed.map(p => mirrorPt(g, p))].some(p => Math.max(Math.abs(p[0] - x), Math.abs(p[1] - y)) < gap)) continue;
    if (g.spawn && [spawnCentre(g), mirrorPt(g, spawnCentre(g))].some(p => Math.max(Math.abs(p[0] - x), Math.abs(p[1] - y)) < spawnGap + 2)) continue;
    const tiles = prefabTiles(rng, PREFABS[rng.choice(names)]), kind = +rng.weighted(kinds);
    // The footprint and a one-tile margin must be open ground, and clear of its own mirror.
    const ok = tiles.every(([dx, dy]) => {
      for (let j = -1; j <= 1; j++) for (let i = -1; i <= 1; i++) if (!g.in(x + dx + i, y + dy + j) || g.get(x + dx + i, y + dy + j) !== GROUND) return false;
      const [mx, my] = mirrorPt(g, [x + dx, y + dy]);
      return Math.max(Math.abs(mx - x - dx), Math.abs(my - y - dy)) > 2;
    });
    if (!ok) continue;
    for (const [dx, dy, ch] of tiles) put(g, x + dx, y + dy, ch === '"' ? BUSH : ch === 'o' ? HOLE : kind);
    placed.push([x, y]);
  }
  return placed;
}

// Bush clumps grown edge-connected from seeds on open ground, `size` tiles each; with `nearWall`
// most seeds sit beside a wall or hole (cover to hide behind), as a designer would place them.
function clumps(g, rng, n, [lo, hi], { nearWall = 0.6, where = () => true } = {}) {
  for (let k = 0, tries = 0; k < n && tries < n * 40; tries++) {
    const x = rng.int(1, g.W - 2), y = rng.int(1, g.H - 2);
    if (g.get(x, y) !== GROUND || !where(x, y)) continue;
    const besideBlock = [[1, 0], [-1, 0], [0, 1], [0, -1], [2, 0], [-2, 0], [0, 2], [0, -2]].some(([dx, dy]) => g.in(x + dx, y + dy) && [WALL, HOLE].includes(g.get(x + dx, y + dy)));
    if (rng.chance(nearWall) && !besideBlock) continue;
    const want = rng.int(lo, hi), cells = [[x, y]], seen = new Set([y * g.W + x]);
    while (cells.length < want) {
      const [cx, cy] = rng.choice(cells), [dx, dy] = rng.choice([[1, 0], [-1, 0], [0, 1], [0, -1]]), nx = cx + dx, ny = cy + dy;
      if (!g.in(nx, ny) || g.get(nx, ny) !== GROUND || seen.has(ny * g.W + nx)) { if (rng.chance(0.05)) break; continue; }
      seen.add(ny * g.W + nx); cells.push([nx, ny]);
    }
    for (const [cx, cy] of cells) put(g, cx, cy, BUSH, [GROUND]);
    k++;
  }
}

// Bush along the rim of open ground facing `kinds` (coasts, river banks), in runs set by noise.
function rims(g, rng, kinds, share) {
  const n = valueNoise(rng, g.W, g.H, rng.uniform(4, 9), 2);
  for (let y = 0; y < g.H; y++) for (let x = 0; x < g.W; x++) {
    if (g.get(x, y) !== GROUND || n[y * g.W + x] < 1 - share) continue;
    if ([[1, 0], [-1, 0], [0, 1], [0, -1]].some(([dx, dy]) => g.in(x + dx, y + dy) && kinds.includes(g.get(x + dx, y + dy)))) put(g, x, y, BUSH);
  }
}

// ---- spawns --------------------------------------------------------------------------------
export function spawnDims(rng) {
  const [w, h] = rng.weighted({ '3x3': 5, '4x4': 3, '4x3': 1, '5x2': 0.4 }).split('x').map(Number);
  return rng.chance(0.5) ? [w, h] : [h, w];
}

// Team A's spawn: 'corner', 'edge' (middle of A's edge) or 'inset' (pulled in from the corner).
export function placeSpawn(g, rng, where, clear = 2) {
  const [w, h] = spawnDims(rng), i = rng.int(0, 2), { W, H } = g, midY = Math.round(H / 2 - h / 2 + rng.int(-Math.floor(H / 8), Math.floor(H / 8)));
  const midX = Math.round(W / 2 - w / 2 + rng.int(-Math.floor(W / 8), Math.floor(W / 8))), low = rng.chance(0.5);
  let x, y;
  if (g.sym === 'vertical') {
    y = where === 'inset' ? Math.round(H * rng.uniform(0.08, 0.16)) : i;
    x = where === 'edge' ? midX : where === 'inset' ? Math.round(W * rng.uniform(0.1, 0.3)) : low ? i : W - w - i;
  } else {
    x = where === 'inset' ? Math.round(W * rng.uniform(0.08, 0.16)) : i;
    y = where === 'edge' ? midY : where === 'inset' ? Math.round(H * rng.uniform(0.1, 0.3)) : low ? i : H - h - i;
  }
  x = Math.max(0, Math.min(W - w, x)); y = Math.max(0, Math.min(H - h, y));
  g.spawn = { x, y, w, h };
  clearSpawn(g, clear);
}

export function clearSpawn(g, clear = 2) {
  const { x, y, w, h } = g.spawn;
  box(g, x - clear, y - clear, w + 2 * clear, h + 2 * clear, GROUND, [WALL, HOLE]);
  box(g, x, y, w, h, GROUND);
}

// ---- objective tiers -----------------------------------------------------------------------
// Template mixes per role (home farm, mid-map, treasure) and economy (spec.camp_mode). Every home
// mix pays gold, so a team walled in by dash or teleport links can still buy a crystal.
const TIERS = {
  standard: {
    home: { wolf: 3, wolf_pair: 2, gold: 3, elk_gold: 1.5, gold_gems: 1 },
    mid: { elk: 2, elk_gold: 2, elk_gems: 2, wolf_pack: 1.5, gems: 2, gold_gems: 1, golem: 0.4 },
    treasure: { golem_gems: 2, elk_pair: 2, monolith_ring: 1, monolith_gold: 0.5, golem_pair: 1, elk_gems: 1.5 },
  },
  poor: { home: { wolf: 2, gold: 3 }, mid: { wolf: 2, gem: 1, gold: 2, elk_gold: 1 }, treasure: { elk_gems: 1, elk: 1, gems: 1 } },
  rich: {
    home: { elk_gold: 2, gold_gems: 2, wolf_pair: 1, elk_gems: 1 },
    mid: { elk_gems: 2, golem_gems: 1.5, elk_pair: 1.5, gems: 2, golem_pair: 0.5 },
    treasure: { monolith_ring: 2, golem_pair: 1.5, golem_gems: 1.5, monolith: 0.5 },
  },
  'gold-rich': { home: { gold: 2, gold_row: 3, golem_gold: 0.5 }, mid: { gold_row: 2, golem_gold: 2, elk_gold: 2, gems: 1 }, treasure: { monolith_gold: 2, golem_gold: 1, golem_gems: 1 } },
  'gold-poor': { home: { wolf: 2, gold: 1, gems: 2 }, mid: { gems: 3, elk_gems: 2, gem: 1 }, treasure: { golem_gems: 1, monolith_ring: 1, elk_gems: 1 } },
  jackpot: { home: { wolf: 2, gold: 2 }, mid: { gold: 2, wolf: 1, gem: 1 }, treasure: { monolith_ring: 3, golem_pair: 1, monolith_gold: 1 } },
};

export const tier = (rng, s, role) => rng.weighted((TIERS[s.camp_mode] ?? TIERS.standard)[role]);
export const site = (g, at, r, what, extra = {}) => g.sites.push({ at, r, ...(typeof what === 'string' ? { tpl: what } : what), ...extra });

// Where tributes happen: a safe home altar, contested ones towards the centre (a pair or one on the
// symmetry axis), or both. At least one is required.
// `mid` is where a contested altar goes (by default the centre; a gate or crossing where the centre
// is a barrier).
export function altarPlan(g, rng, S, C, r = 8, mid = null) {
  const plan = rng.weighted({ home: 1.5, mid: 5, both: 1.5 });
  if (plan !== 'mid') site(g, lerp(S, C, rng.uniform(0.15, 0.35)), r, { altar: true }, { required: plan === 'home' });
  if (plan !== 'home') site(g, mid ?? (rng.chance(0.4) ? C : lerp(C, S, rng.uniform(0, 0.08))), r, { altar: !mid && rng.chance(0.35) ? 'self' : true }, { required: true });
}

export function begin(g, fill) {
  g.t.fill(fill);
  g.sites = []; g.intents = []; g.noCamp = new Set(); g.access = 'walk'; g.gated = false;
}

export const raise = (g, level) => { const order = ['walk', 'dash', 'teleport']; if (order.indexOf(level) > order.indexOf(g.access)) g.access = level; };

// ---- designers -----------------------------------------------------------------------------
// Islands in a sea of holes (or rock) joined by typed links: walked bridges, dash crossings (a
// one-hole cut), crystal crossings (a two-hole or wall cut). 'atoll': a central treasure island
// reached only across stepping stones; 'chain' and 'graph': islands joined by a mix of links.
function islands(g, rng, s) {
  const voidKind = s.void_kind === 'wall' ? WALL : HOLE, C = centre(g), m = Math.min(g.W, g.H), layout = s.layout;
  begin(g, voidKind);
  placeSpawn(g, rng, rng.weighted({ corner: 3, edge: 2, inset: 1 }), 1);
  const S = spawnCentre(g), S2 = mirrorPt(g, S), rough = rng.uniform(0.05, 0.22);
  const home = { p: lerp(S, C, rng.uniform(0.04, 0.14)), r: m * rng.uniform(0.12, 0.19) + 2.5, role: 'home' }, nodes = [home];
  let hub = null;
  if (layout === 'atoll' || (layout === 'graph' && rng.chance(0.5))) hub = { p: C, r: m * (layout === 'atoll' ? rng.uniform(0.1, 0.16) : rng.uniform(0.06, 0.1)) + 2, role: 'hub', self: true };
  // Islands stay at least 4 tiles of sea apart (past their wobble), shrunk to fit if need be.
  const outer = r => r * (1 + 2 * rough);
  if (dist(home.p, mirrorPt(g, home.p)) < 2 * outer(home.r) + 4) home.r = (dist(home.p, mirrorPt(g, home.p)) - 4) / 2 / (1 + 2 * rough);
  if (hub) {
    const room = dist(home.p, C) - 4;
    if (outer(home.r) + outer(hub.r) > room) { const k = room / (outer(home.r) + outer(hub.r)); home.r *= k; hub.r *= k; }
  }
  if (home.r < Math.max(g.spawn.w, g.spawn.h) + 1.5 || (hub && hub.r < 2.5)) throw new GenFail('islands do not fit');
  const want = layout === 'atoll' ? rng.int(1, 3) : rng.int(2, 5), others = () => [...nodes, ...nodes.map(n => ({ p: mirrorPt(g, n.p), r: n.r })), ...(hub ? [hub] : [])];
  for (let tries = 0; nodes.length - 1 < want && tries < 300; tries++) {
    const r = m * rng.uniform(0.05, 0.1) + 1.5, p = [rng.uniform(r + 1, g.W - 2 - r), rng.uniform(r + 1, g.H - 2 - r)];
    if (!onSideA(g, p) || dist(p, mirrorPt(g, p)) < 2 * outer(r) + 5 || others().some(n => dist(n.p, p) < outer(n.r) + outer(r) + 5)) continue;
    nodes.push({ p, r, role: 'isle' });
  }
  if (hub) nodes.push(hub);
  for (const n of nodes) blob(g, rng, n.p, n.r, rough, GROUND);
  // Links: Kruskal over the islands and their mirrors (each link drawn brings its mirror), then a
  // few extra links for loops.
  const N = nodes.length, mir = i => nodes[i % N].self ? i % N : (i + N) % (2 * N), pos = i => i < N ? nodes[i].p : mirrorPt(g, nodes[i - N].p);
  const parent = Array.from({ length: 2 * N }, (_, i) => i), find = i => parent[i] === i ? i : (parent[i] = find(parent[i]));
  const cands = [];
  for (let a = 0; a < N; a++) for (let b = 0; b < 2 * N; b++) {
    if (b === a || (b < N && b < a) || nodes[b % N].self && b >= N) continue;
    const gap = dist(pos(a), pos(b)) - nodes[a].r - nodes[b % N].r;
    if (gap > 2) cands.push({ a, b, gap });
  }
  cands.sort((p, q) => p.gap - q.gap);
  const links = [];
  for (const c of cands) {
    if (find(c.a) === find(c.b)) continue;
    links.push(c);
    parent[find(c.a)] = find(c.b); parent[find(mir(c.a))] = find(mir(c.b));
  }
  for (const c of cands) if (!links.includes(c) && c.gap < m * 0.3 && rng.chance(s.loops)) links.push(c);
  const typeOf = c => {
    const roles = [nodes[c.a].role, nodes[c.b % N].role];
    if (voidKind === WALL) return rng.weighted({ walk: 2, teleport: 1 });
    if (roles.includes('hub')) return layout === 'atoll' ? rng.weighted({ dash: 3, teleport: 1 }) : rng.weighted({ walk: 1, dash: 2, teleport: 1 });
    return rng.weighted({ walk: 2, dash: 2, teleport: 0.7 });
  };
  const inIsland = (x, y) => [...nodes, ...nodes.map(n => ({ p: mirrorPt(g, n.p), r: n.r }))].some(n => dist([x, y], n.p) <= n.r * (1 + 2 * rough) + 1);
  for (const c of links) {
    const a = pos(c.a), b = pos(c.b), type = typeOf(c), w = type === 'walk' ? rng.int(1, 3) : rng.int(2, 3);
    const mid = lerp(a, b, 0.5), len = dist(a, b), bend = rng.uniform(-0.12, 0.12) * len;
    const pts = smooth([a, [mid[0] - (b[1] - a[1]) / len * bend, mid[1] + (b[0] - a[0]) / len * bend], b]);
    stroke(g, pts, w, GROUND);
    if (type === 'walk') continue;
    raise(g, type);
    // Cuts along the stretch between the islands; stepping stones widen the land between cuts.
    const ra = nodes[c.a].r * (1 + 2 * rough) + 1, rb = nodes[c.b % N].r * (1 + 2 * rough) + 1, t0 = ra / len, t1 = 1 - rb / len;
    if (t1 - t0 <= 0.02) throw new GenFail('no room for a crossing');
    const span = (t1 - t0) * len, k = layout === 'atoll' && nodes[c.b % N].role === 'hub' ? Math.max(1, Math.round(span / rng.uniform(4, 7))) : rng.int(1, Math.max(1, Math.min(2, Math.floor(span / 5))));
    const at = Array.from({ length: k }, (_, j) => t0 + (t1 - t0) * (j + 1) / (k + 1));
    for (let j = 0; j + 1 < k; j++) if (rng.chance(0.7)) disc(g, along(pts, (at[j] + at[j + 1]) / 2).p, rng.uniform(1, 2.2), GROUND, [voidKind]);
    for (const t of at) {
      const { p, d } = along(pts, t);
      cut(g, p, d, type === 'dash' ? 1 : 2, w + 3, voidKind, inIsland);
      for (let dy = -3; dy <= 3; dy++) for (let dx = -3; dx <= 3; dx++) g.noCamp.add(Math.round(p[1] + dy) * g.W + Math.round(p[0] + dx));
    }
  }
  // A walking route can bypass every cut; intents check the hub needs what its links say.
  if (hub) g.intents.push({ at: C, r: Math.max(1.5, hub.r * 0.5), min: links.filter(c => nodes[c.b % N].role === 'hub' || nodes[c.a].role === 'hub').length ? 'dash' : 'walk' });
  if (rng.chance(0.7)) rims(g, rng, [voidKind], rng.uniform(0.2, 0.45));
  for (const n of nodes) if (n.r >= 6) scatterPrefabs(g, rng, rng.int(0, 2), { gap: 4, where: (x, y) => dist([x, y], n.p) < n.r - 2 });
  clearSpawn(g, 1);
  site(g, home.p, home.r, tier(rng, s, 'home'), { required: true, home: true });
  if (hub) {
    if (rng.chance(0.5)) g.sites.push({ shared: 'treasure', required: true });
    else site(g, lerp(C, S, 0.12), hub.r + 1, tier(rng, s, 'treasure'), { required: true });
    altarPlan(g, rng, home.p, C, Math.min(home.r, hub.r));
  } else {
    const inner = nodes.reduce((b, n) => dist(n.p, C) < dist(b.p, C) ? n : b);
    altarPlan(g, rng, home.p, inner.p, Math.max(3, Math.min(home.r, inner.r)));
  }
  for (const n of nodes.filter(q => q.role === 'isle')) site(g, n.p, n.r, rng.chance(0.25) ? { altar: true } : tier(rng, s, rng.chance(0.3) ? 'treasure' : 'mid'));
}

// Rivers of holes (sometimes rock ravines) crossing grass, with bridges, dash fords, bushy banks
// and a lake. 'divide' splits the teams along the symmetry axis, 'tributary' runs rivers from the
// edges into a central lake, 'lanes' runs them alongside the spawn-to-spawn axis.
function rivers(g, rng, s) {
  begin(g, GROUND);
  placeSpawn(g, rng, rng.weighted({ corner: 3, edge: 2, inset: 1 }));
  const C = centre(g), S = spawnCentre(g), S2 = mirrorPt(g, S), kind = rng.chance(0.82) ? HOLE : WALL, layout = s.layout, m = Math.min(g.W, g.H);
  const paths = [], base = rng.int(2, 4);
  const edgePoint = (dir) => {
    // Where a ray from the centre along dir leaves the map.
    const tx = dir[0] ? (dir[0] > 0 ? (g.W - 1 - C[0]) / dir[0] : -C[0] / dir[0]) : Infinity, ty = dir[1] ? (dir[1] > 0 ? (g.H - 1 - C[1]) / dir[1] : -C[1] / dir[1]) : Infinity;
    const t = Math.min(tx, ty) + 2;
    return [C[0] + dir[0] * t, C[1] + dir[1] * t];
  };
  const axis = [S2[0] - S[0], S2[1] - S[1]], al = Math.hypot(...axis), u = [axis[0] / al, axis[1] / al], perp = [-u[1], u[0]];
  if (layout === 'divide') {
    const a = rng.uniform(-0.35, 0.35), dir = [perp[0] * Math.cos(a) - perp[1] * Math.sin(a), perp[0] * Math.sin(a) + perp[1] * Math.cos(a)];
    paths.push({ pts: meander(rng, C, edgePoint(dir), rng.uniform(0.03, 0.1)), w: base + 1, divide: true });
    if (rng.chance(0.4)) disc(g, C, rng.uniform(2.5, m * 0.08 + 2), kind);
  } else if (layout === 'tributary') {
    disc(g, C, rng.uniform(2.5, m * 0.1 + 2), kind);
    for (let k = rng.int(1, 2); k > 0; k--) {
      const ang = rng.uniform(-1.3, 1.3), dir = [-u[0] * Math.cos(ang) + perp[0] * Math.sin(ang), -u[1] * Math.cos(ang) + perp[1] * Math.sin(ang)];
      paths.push({ pts: meander(rng, C, edgePoint([dir[0] * 0.7 + perp[0] * (k - 1.5), dir[1] * 0.7 + perp[1] * (k - 1.5)].map((v, i, arr) => v / Math.hypot(...arr))), rng.uniform(0.04, 0.12)), w: base });
    }
  } else {
    // Two long rivers beside the spawn-to-spawn line make three lanes; their mirrors overlap them.
    for (const side of [1, -1]) {
      const off = m * rng.uniform(0.15, 0.3) * side, a = [S[0] + perp[0] * off + u[0] * 6, S[1] + perp[1] * off + u[1] * 6];
      paths.push({ pts: meander(rng, a, [C[0] + perp[0] * off, C[1] + perp[1] * off], rng.uniform(0.02, 0.07)), w: base });
    }
  }
  for (const r of paths) stroke(g, r.pts, t => r.w + (Math.sin(t * 9 + r.w) > 0.6 ? 1 : 0), kind);
  // Crossings: walked bridges, and fords one hole wide (a dash, or a crystal for rock).
  for (const r of paths) {
    const n = r.divide ? rng.int(2, 3) : rng.int(1, 3), ts = Array.from({ length: n }, (_, k) => (k + rng.uniform(0.25, 0.75)) / n);
    let bridges = 0;
    for (const [k, t] of ts.entries()) {
      const { p, d } = along(r.pts, t), nrm = [-d[1], d[0]], half = r.w / 2 + 2.5, bw = rng.int(2, 3);
      if (!inMap(g, p, 2)) continue;
      const ford = rng.chance(0.35) && !(k === ts.length - 1 && !bridges);
      stroke(g, [[p[0] - nrm[0] * half, p[1] - nrm[1] * half], [p[0] + nrm[0] * half, p[1] + nrm[1] * half]], bw, GROUND, [kind]);
      if (ford) { cut(g, p, nrm, 1, bw + 1, kind); raise(g, kind === HOLE ? 'dash' : 'teleport'); }
      else bridges++;
    }
  }
  if (rng.chance(0.75)) rims(g, rng, [kind], rng.uniform(0.25, 0.5));
  scatterPrefabs(g, rng, rng.int(2, Math.round(m / 7)), { gap: 6, kinds: { [WALL]: 3, [BUSH]: 1 } });
  clumps(g, rng, rng.int(2, 6), [4, 9]);
  clearSpawn(g);
  site(g, lerp(S, C, 0.2), 8, tier(rng, s, 'home'), { required: true, home: true });
  altarPlan(g, rng, S, C);
  site(g, lerp(C, S, 0.15), 8, tier(rng, s, 'treasure'));
  for (let k = rng.int(1, 3); k > 0; k--) site(g, lerp(S, C, rng.uniform(0.35, 0.8)).map((v, i) => v + perp[i] * rng.uniform(-0.3, 0.3) * m), 7, tier(rng, s, 'mid'));
}

// Gated walls around the treasure. The keep's ring has gates that are open, bush-curtained, plugged
// by a camp group, cut by a dash moat, or sealed (a wall a crystal can cross); bases sit in
// walled courtyards; the field has cover.
function fortress(g, rng, s) {
  begin(g, GROUND);
  placeSpawn(g, rng, rng.weighted({ corner: 3, edge: 1, inset: 1 }));
  const C = centre(g), S = spawnCentre(g), m = Math.min(g.W, g.H), sx = (g.W - 1) / 2, sy = (g.H - 1) / 2;
  const R = m * rng.uniform(0.14, 0.24) + 2, t = rng.int(1, 2), shape = rng.weighted({ square: 2, octagon: 2, circle: 1.5 });
  const metric = (x, y) => { const u = (x - C[0]) * Math.min(sx, sy) / sx, v = (y - C[1]) * Math.min(sx, sy) / sy; return shape === 'square' ? Math.max(Math.abs(u), Math.abs(v)) : shape === 'circle' ? Math.hypot(u, v) : Math.max(Math.abs(u), Math.abs(v), (Math.abs(u) + Math.abs(v)) / 1.4); };
  const moat = rng.chance(0.45) ? rng.int(1, 3) : 0, angOf = (x, y) => Math.atan2(y - C[1], x - C[0]), ring = [], water = [];
  for (let y = 0; y < g.H; y++) for (let x = 0; x < g.W; x++) {
    const d = metric(x, y);
    if (d > R - t && d <= R) { put(g, x, y, WALL); ring.push([x, y]); }
    else if (moat && d > R + 2 && d <= R + 2 + moat) { put(g, x, y, HOLE); water.push([x, y]); }
  }
  seal(g, ring, WALL); seal(g, water, HOLE);
  if (moat === 1) raise(g, 'dash');
  // Gates on team A's half of the ring (their mirrors open B's).
  const toward = angOf(...S), gates = [], k = rng.int(1, 2), types = { open: 3, bush: 1, boss: 0.8, dash: 0.8, sealed: 0.5 };
  for (let j = 0; j < k; j++) gates.push({ a: toward + (k === 1 ? rng.uniform(-0.6, 0.6) : (j ? 1 : -1) * rng.uniform(0.5, 1.3)), type: j === 0 ? rng.weighted({ open: 3, bush: 1, boss: 0.8, dash: 0.8 }) : rng.weighted(types), w: rng.int(2, 3) });
  for (const gate of gates) {
    const half = (gate.w / 2 + 0.3) / R, opening = [];
    for (let y = 0; y < g.H; y++) for (let x = 0; x < g.W; x++) {
      const d = metric(x, y), da = Math.abs(((angOf(x, y) - gate.a + 3 * Math.PI) % (2 * Math.PI)) - Math.PI);
      if (da > half) continue;
      if (d > R - t && d <= R && gate.type !== 'sealed') { put(g, x, y, gate.type === 'bush' ? BUSH : GROUND); opening.push([x, y]); }
      if (moat && d > R + 2 && d <= R + 2 + moat && (gate.type !== 'dash' || moat > 1)) put(g, x, y, GROUND);
    }
    if (gate.type === 'sealed') raise(g, 'teleport');
    if (gate.type === 'dash') {
      // A one-hole moat across the gate's mouth, just outside the wall.
      for (let y = 0; y < g.H; y++) for (let x = 0; x < g.W; x++) {
        const d = metric(x, y), da = Math.abs(((angOf(x, y) - gate.a + 3 * Math.PI) % (2 * Math.PI)) - Math.PI);
        if (da <= half + 1 / R && d > R && d <= R + 1) put(g, x, y, HOLE);
      }
      raise(g, 'dash');
    }
    if (gate.type === 'boss' && opening.length && opening.length <= 6) {
      const boss = rng.weighted({ elk: 2, golem: 1, wolf: 1 });
      g.sites.push({ cells: opening.map(([x, y], i) => [i ? rng.weighted({ [boss]: 1, wolf: 1, gold_cluster: 0.5 }) : boss, x, y]), required: true, gate: true });
      g.gated = true;
    }
  }
  if (rng.chance(0.35)) {
    const r2 = R * rng.uniform(0.35, 0.55), ga = toward + rng.uniform(-1, 1), inner = [];
    for (let y = 0; y < g.H; y++) for (let x = 0; x < g.W; x++) {
      const d = metric(x, y), da = Math.abs(((angOf(x, y) - ga + 3 * Math.PI) % (2 * Math.PI)) - Math.PI);
      if (d > r2 - 1 && d <= r2 && da > 1.4 / r2) { put(g, x, y, WALL); inner.push([x, y]); }
    }
    seal(g, inner, WALL);
  }
  // Courtyards: a wall around the spawn at distance 4-7, open towards the map.
  if (rng.chance(0.55)) {
    const d = rng.int(4, 7), { x, y, w, h } = g.spawn, x0 = x - d, y0 = y - d, x1 = x + w - 1 + d, y1 = y + h - 1 + d;
    for (let yy = y0; yy <= y1; yy++) for (let xx = x0; xx <= x1; xx++) if ((xx === x0 || xx === x1 || yy === y0 || yy === y1) && g.in(xx, yy) && xx > 0 && yy > 0 && xx < g.W - 1 && yy < g.H - 1) put(g, xx, yy, WALL);
    for (let j = 0; j < 2; j++) {
      const side = rng.int(0, 3), gw = rng.int(2, 4), at = rng.int(1, Math.max(1, (side % 2 ? y1 - y0 : x1 - x0) - gw));
      for (let q = 0; q < gw; q++) {
        const px = side === 0 ? x0 + at + q : side === 1 ? x1 : side === 2 ? x0 + at + q : x0, py = side === 0 ? y0 : side === 1 ? y0 + at + q : side === 2 ? y1 : y0 + at + q;
        put(g, px, py, GROUND);
      }
    }
  }
  scatterPrefabs(g, rng, rng.int(3, Math.round(m / 6)), { gap: 6, where: (x, y) => metric(x, y) > R + 4 + moat, kinds: { [WALL]: 3, [HOLE]: 0.5 } });
  clumps(g, rng, rng.int(2, 6), [3, 8], { where: (x, y) => metric(x, y) > R + 1 + moat });
  clearSpawn(g);
  site(g, lerp(S, C, 0.25), 9, tier(rng, s, 'home'), { required: true, home: true });
  if (rng.chance(0.5)) g.sites.push({ shared: 'treasure', required: true });
  else site(g, lerp(C, S, 0.1), R - t - 1, tier(rng, s, 'treasure'), { required: true });
  altarPlan(g, rng, S, C, Math.min(8, R - t - 1));
  for (let j = rng.int(1, 3); j > 0; j--) site(g, lerp(S, C, rng.uniform(0.3, 0.6)).map((v, i) => v + rng.uniform(-0.25, 0.25) * (i ? g.H : g.W)), 7, tier(rng, s, 'mid'));
}

// A barrier between the halves (a wall too thick to teleport, or a wide chasm) crossed only at
// gates: open, bush, plugged by a camp group (kill it to pass, like "boss-battle"), dash (hole
// lines), or a thinned wall a crystal can cross.
function barrier(g, rng, s) {
  begin(g, GROUND);
  placeSpawn(g, rng, rng.weighted({ corner: 2, edge: 2, inset: 1 }));
  const C = centre(g), S = spawnCentre(g), S2 = mirrorPt(g, S), m = Math.min(g.W, g.H), kind = rng.weighted({ [WALL]: 3, [HOLE]: 1.5 }) | 0;
  const t = kind === WALL ? rng.int(3, 4) : rng.int(3, 5);
  // Direction of the barrier: across the spawn-to-spawn line, through the centre.
  const ax = [S2[0] - S[0], S2[1] - S[1]], al = Math.hypot(...ax), dir = g.sym === 'horizontal' ? [0, 1] : g.sym === 'vertical' ? [1, 0] : (() => { const a = rng.uniform(-0.4, 0.4), p = [-ax[1] / al, ax[0] / al]; return [p[0] * Math.cos(a) - p[1] * Math.sin(a), p[0] * Math.sin(a) + p[1] * Math.cos(a)]; })();
  const reach = Math.hypot(g.W, g.H), end = [C[0] + dir[0] * reach, C[1] + dir[1] * reach], line = g.sym === 'rotational' ? meander(rng, C, end, rng.uniform(0, 0.05)) : [[C[0] - dir[0] * reach, C[1] - dir[1] * reach], end];
  stroke(g, line, t, kind);
  // Gates along team A's half of the line (for a mirror axis the line is its own mirror).
  const usable = [];
  for (let q = 0.06; q <= 0.94; q += 0.01) { const { p } = along(line, q); if (inMap(g, p, 3) && (g.sym === 'rotational' || dist(p, S) <= dist(p, S2) + 1)) usable.push(q); }
  const n = rng.int(2, 3), qs = rng.shuffle(usable.slice()).filter((q, i, arr) => arr.slice(0, i).every(o => Math.abs(o - q) > 0.12)).slice(0, n);
  if (!qs.length) throw new GenFail('no gate site');
  const types = qs.map((_, i) => i === 0 ? rng.weighted({ open: 2, boss: 2, bush: 1 }) : rng.weighted({ open: 1.5, boss: 1.5, dash: kind === HOLE ? 1.5 : 1, thin: kind === WALL ? 1.2 : 0, bush: 0.6 }));
  let approach = null;
  qs.forEach((q, i) => {
    const { p, d } = along(line, q), nrm = [-d[1], d[0]], gw = types[i] === 'boss' ? rng.int(1, 2) : rng.int(2, 3), across = t / 2 + 1.5, tiles = [];
    const a = [p[0] - nrm[0] * across, p[1] - nrm[1] * across], b = [p[0] + nrm[0] * across, p[1] + nrm[1] * across];
    if (types[i] === 'thin') {
      // Notches either side leave a wall two thick: a crystal crosses (range 3), nothing else.
      const keepFrom = Math.floor(t / 2) - 1;
      for (let k = -2; k <= 2; k++) for (let j = 0; j < t; j++) {
        if (j >= keepFrom && j < keepFrom + 2) continue;
        const o = j - (t - 1) / 2;
        put(g, p[0] + d[0] * k + nrm[0] * o, p[1] + d[1] * k + nrm[1] * o, GROUND);
      }
      raise(g, 'teleport');
      return;
    }
    stroke(g, [a, b], gw, types[i] === 'bush' ? BUSH : GROUND, [kind]);
    // The gate's mouth on team A's side.
    if (!approach || rng.chance(0.4)) approach = [a, b].reduce((u, v) => dist(u, S) < dist(v, S) ? u : v).map((v, k) => v + (k ? d[1] : d[0]) * rng.uniform(-2, 2));
    if (types[i] === 'dash') {
      // A hole line one thick: on a mirror axis it sits off the axis and its mirror is a second,
      // separate dash; under rotation one line across the middle.
      const off = g.sym === 'rotational' ? 0 : Math.max(1, t / 2 - 0.5);
      cut(g, [p[0] + nrm[0] * off, p[1] + nrm[1] * off], nrm, 1, gw + 1, HOLE);
      raise(g, 'dash');
    }
    if (types[i] === 'boss') {
      for (let y = Math.floor(p[1] - t); y <= p[1] + t; y++) for (let x = Math.floor(p[0] - t); x <= p[0] + t; x++) {
        if (!g.in(x, y) || g.get(x, y) !== GROUND) continue;
        // Tiles of the opening: ground with barrier on both sides along the line.
        const side = k => { const xx = Math.round(x + d[0] * k), yy = Math.round(y + d[1] * k); return g.in(xx, yy) && g.get(xx, yy) === kind; };
        if ([1, 2, 3].some(side) && [-1, -2, -3].some(side)) tiles.push([x, y]);
      }
      const mine = g.sym === 'rotational' ? tiles : tiles.filter(([x, y]) => { const [mx, my] = mirrorPt(g, [x, y]); return x * g.H + y <= mx * g.H + my; });
      if (mine.length && mine.length <= 6) {
        const boss = rng.weighted({ elk: 2, golem: 1.2, wolf: 1, monolith: g.sym === 'rotational' ? 0 : 0.3 });
        g.sites.push({ cells: mine.map(([x, y], j) => [j ? rng.weighted({ [boss]: 1, wolf: 1 }) : boss, x, y]), shared: g.sym !== 'rotational', required: true, gate: true });
        g.gated = true;
      }
    }
    // Ambush cover at the approaches.
    if (rng.chance(0.6)) for (const side of [-1, 1]) disc(g, [p[0] + nrm[0] * side * (t / 2 + 3) + d[0] * (gw + 1), p[1] + nrm[1] * side * (t / 2 + 3) + d[1] * (gw + 1)], 1.2, BUSH, [GROUND]);
  });
  scatterPrefabs(g, rng, rng.int(3, Math.round(m / 6)), { gap: 6, kinds: { [WALL]: 3, [BUSH]: 1 } });
  clumps(g, rng, rng.int(2, 6), [3, 8]);
  clearSpawn(g);
  site(g, lerp(S, C, 0.25), 8, tier(rng, s, 'home'), { required: true, home: true });
  for (let j = rng.int(2, 4); j > 0; j--) site(g, lerp(S, C, rng.uniform(0.3, 0.75)).map((v, i) => v + rng.uniform(-0.25, 0.25) * (i ? g.H : g.W)), 7, tier(rng, s, rng.chance(0.3) ? 'treasure' : 'mid'));
  altarPlan(g, rng, S, C, 6, approach);
}

// Rooms and corridors cut from rock (or floating over holes): a grid of rooms, a spanning tree of
// corridors plus loops, and themed rooms (pillared halls, bush gardens, pools, treasure vaults,
// shrines with an altar).
function dungeon(g, rng, s) {
  const voidKind = s.void_kind === 'hole' ? HOLE : WALL;
  begin(g, voidKind);
  const cell = rng.int(8, 13), nx = Math.max(3, Math.floor(g.W / cell)), ny = Math.max(3, Math.floor(g.H / cell)), cw = g.W / nx, ch = g.H / ny;
  const rooms = [];
  for (let j = 0; j < ny; j++) for (let i = 0; i < nx; i++) {
    const big = rng.chance(0.75), w = big ? rng.int(4, Math.max(4, Math.floor(cw) - 2)) : rng.int(1, 2), h = big ? rng.int(4, Math.max(4, Math.floor(ch) - 2)) : w;
    const x = Math.floor(i * cw) + 1 + rng.int(0, Math.max(0, Math.floor(cw) - w - 2)), y = Math.floor(j * ch) + 1 + rng.int(0, Math.max(0, Math.floor(ch) - h - 2));
    rooms.push({ i, j, x, y, w, h, big, c: [x + (w - 1) / 2, y + (h - 1) / 2] });
  }
  // The mirror of a room is drawn by g.set; only the canonical one of each pair is drawn and themed.
  const id = (i, j) => j * nx + i, mirrorRoom = r => { const [mx, my] = mirrorPt(g, r.c); return rooms.reduce((b, q) => dist(q.c, [mx, my]) < dist(b.c, [mx, my]) ? q : b); };
  const canon = rooms.filter(r => id(r.i, r.j) <= id(mirrorRoom(r).i, mirrorRoom(r).j));
  for (const r of canon) box(g, r.x, r.y, r.w, r.h, GROUND);
  // Spawn room: the canonical room nearest a corner, grown to hold the spawn.
  const corner = g.sym === 'vertical' ? [rng.chance(0.5) ? 0 : g.W - 1, 0] : [0, rng.chance(0.5) ? 0 : g.H - 1];
  const home = canon.filter(r => r.big).reduce((b, q) => dist(q.c, corner) < dist(b.c, corner) ? q : b);
  const [sw, sh] = spawnDims(rng);
  home.w = Math.max(home.w, sw + 4); home.h = Math.max(home.h, sh + 4);
  home.x = Math.max(0, Math.min(g.W - home.w, home.x)); home.y = Math.max(0, Math.min(g.H - home.h, home.y));
  box(g, home.x, home.y, home.w, home.h, GROUND);
  home.c = [home.x + (home.w - 1) / 2, home.y + (home.h - 1) / 2];
  g.spawn = { x: home.x + 2 + rng.int(0, home.w - sw - 4), y: home.y + 2 + rng.int(0, home.h - sh - 4), w: sw, h: sh };
  // Themes before corridors, so a corridor through a pool becomes a bridge.
  const themed = [];
  for (const r of canon) {
    if (r === home || !r.big) continue;
    const theme = rng.weighted({ plain: 3, pillars: 1.2, garden: 1, pool: r.w >= 6 && r.h >= 6 ? 1 : 0, treasure: 1, shrine: 0.6, crops: 0.6 });
    themed.push([r, theme]);
    if (theme === 'pillars') { const sp = rng.int(2, 3); for (let y = r.y + 1; y < r.y + r.h - 1; y += sp) for (let x = r.x + 1; x < r.x + r.w - 1; x += sp) put(g, x, y, WALL); }
    else if (theme === 'garden') box(g, r.x + 1, r.y + 1, r.w - 2, r.h - 2, BUSH);
    else if (theme === 'crops') for (let y = r.y + 1; y < r.y + r.h - 1; y += 2) box(g, r.x + 1, y, r.w - 2, 1, BUSH);
    else if (theme === 'pool') blob(g, rng, r.c, Math.min(r.w, r.h) / 2 - 1.5, 0.15, HOLE);
  }
  const loops = s.loops, edges = [], seen = new Set([id(home.i, home.j)]), stack = [home];
  while (stack.length) {
    const r = stack.at(-1), next = rng.shuffle([[1, 0], [-1, 0], [0, 1], [0, -1]]).map(([di, dj]) => rooms[id(r.i + di, r.j + dj)]).filter(q => q && Math.abs(q.i - r.i) + Math.abs(q.j - r.j) === 1 && !seen.has(id(q.i, q.j)));
    if (!next.length) { stack.pop(); continue; }
    edges.push([r, next[0]]); seen.add(id(next[0].i, next[0].j)); stack.push(next[0]);
  }
  for (const r of rooms) for (const [di, dj] of [[1, 0], [0, 1]]) { const q = rooms[id(r.i + di, r.j + dj)]; if (q && r.i + di < nx && rng.chance(loops)) edges.push([r, q]); }
  const width = { 1: 2, 2: 3, 3: 1.2 };
  for (const [a, b] of edges) {
    const w = +rng.weighted(width), bendFirst = rng.chance(0.5), mid = bendFirst ? [b.c[0], a.c[1]] : [a.c[0], b.c[1]];
    stroke(g, [a.c, mid, b.c], w, GROUND, [voidKind, HOLE, BUSH]);
    if (rng.chance(0.2)) { const { p } = along([a.c, mid, b.c], 0.5); disc(g, p, 0.8, BUSH, [GROUND]); }
  }
  if (voidKind === HOLE) raise(g, 'dash');
  for (const [r, theme] of themed) {
    if (theme === 'treasure') site(g, r.c, Math.max(r.w, r.h) / 2, tier(rng, s, 'treasure'), { required: true });
    else if (theme === 'shrine') site(g, r.c, Math.max(r.w, r.h) / 2, { altar: true });
    else if (rng.chance(0.6)) site(g, r.c, Math.max(r.w, r.h) / 2, tier(rng, s, onSideA(g, r.c) && dist(r.c, home.c) < g.W / 3 ? 'home' : 'mid'));
  }
  clearSpawn(g, 0);
  site(g, home.c, Math.max(home.w, home.h), tier(rng, s, 'home'), { required: true, home: true });
  const C = centre(g), hall = canon.filter(r => r.big && r !== home).reduce((b, r) => dist(r.c, C) < dist(b.c, C) ? r : b, home);
  altarPlan(g, rng, home.c, C, Math.max(4, Math.max(hall.w, hall.h) / 2 + 1), hall.c);
}

// Three lanes between corner bases (top, middle, bottom) with jungle between them: clearings joined
// by winding paths, a river across the middle lane with bush, and a boss at the centre.
function threeLane(g, rng, s) {
  const voidKind = s.void_kind === 'hole' ? HOLE : WALL;
  begin(g, voidKind);
  const { W, H } = g, e = rng.int(2, 5), lw = rng.int(3, 5), C = centre(g);
  const [sw, sh] = spawnDims(rng), inset = rng.int(1, 3);
  g.spawn = { x: inset, y: inset, w: sw, h: sh };
  const S = spawnCentre(g), S2 = mirrorPt(g, S), TL = [e + lw / 2, H - 1 - e - lw / 2];
  disc(g, S, rng.uniform(5, 8), GROUND);
  stroke(g, smooth([S, [S[0], S[1] + (TL[1] - S[1]) * 0.6], TL, [TL[0] + (S2[0] - TL[0]) * 0.4, TL[1]], S2], 3), lw, GROUND);
  stroke(g, meander(rng, S, C, rng.uniform(0, 0.05)), lw, GROUND);
  // Jungle clearings in the upper-left triangle (its mirror is the lower-right one).
  const inTri = ([x, y]) => (y / (H - 1)) - (x / (W - 1)) > 0.12 && x > e + lw + 3 && y < H - 1 - e - lw - 3;
  const clear = [];
  for (let tries = 0; clear.length < rng.int(3, 6) && tries < 400; tries++) {
    const p = [rng.uniform(3, W - 4), rng.uniform(3, H - 4)], r = rng.uniform(2.5, 4.5);
    if (!inTri(p) || clear.some(q => dist(q.p, p) < q.r + r + 4)) continue;
    clear.push({ p, r });
  }
  for (const c of clear) blob(g, rng, c.p, c.r, 0.15, GROUND);
  // Paths: each clearing to its nearest neighbour and to the nearest lane point.
  const lanePt = p => { const opts = [[e + lw / 2, p[1]], [p[0], H - 1 - e - lw / 2], (() => { const t = ((p[0] - S[0]) + (p[1] - S[1])) / ((C[0] - S[0]) + (C[1] - S[1])) ; const q = lerp(S, C, Math.max(0, Math.min(1, t))); return q; })()]; return opts.reduce((b, q) => dist(q, p) < dist(b, p) ? q : b); };
  for (const [k, c] of clear.entries()) {
    stroke(g, meander(rng, c.p, lanePt(c.p), 0.1), 2, GROUND);
    const other = clear.filter((_, j) => j !== k).sort((a, b) => dist(a.p, c.p) - dist(b.p, c.p))[0];
    if (other && rng.chance(0.7)) stroke(g, meander(rng, c.p, other.p, 0.12), 2, GROUND);
  }
  // River: from the centre towards the top-left corner, ground with bush banks.
  const river = meander(rng, C, [e + lw + 1, H - 2 - e - lw], 0.06);
  stroke(g, river, rng.int(2, 3), GROUND);
  for (let k = 0; k < 3; k++) { const { p } = along(river, rng.uniform(0.2, 0.8)); disc(g, p, 1.3, BUSH, [GROUND]); }
  disc(g, C, rng.uniform(3, 5), GROUND);
  rims(g, rng, [voidKind], rng.uniform(0.1, 0.25));
  clearSpawn(g);
  site(g, S, 9, tier(rng, s, 'home'), { required: true, home: true });
  const riverAltar = rng.chance(0.7);
  if (riverAltar) site(g, along(river, rng.uniform(0.3, 0.6)).p, 5, { altar: true }, { required: true });
  if (!riverAltar || rng.chance(0.3)) site(g, S, 10, { altar: true }, { required: true });
  g.sites.push({ shared: 'treasure', required: rng.chance(0.5) });
  for (const c of clear) site(g, c.p, c.r + 1, tier(rng, s, 'mid'));
  for (const t of [0.35, 0.65]) if (rng.chance(0.6)) site(g, along([S, [S[0], TL[1]], TL, [S2[0], TL[1]]], t).p, 3, 'gold');
}

// A small arena for fights: a shaped border, a jackpot in the middle, symmetric cover rings and a
// thin home economy.
function arena(g, rng, s) {
  const voidKind = rng.chance(0.6) ? WALL : HOLE, C = centre(g), m = Math.min(g.W, g.H), shape = rng.weighted({ octagon: 2, circle: 1.5, square: 1 });
  begin(g, GROUND);
  for (let y = 0; y < g.H; y++) for (let x = 0; x < g.W; x++) {
    const u = (2 * x - g.W + 1) / (g.W - 1), v = (2 * y - g.H + 1) / (g.H - 1);
    const out = shape === 'circle' ? Math.hypot(u, v) > 1.08 : shape === 'octagon' ? Math.abs(u) + Math.abs(v) > 1.45 : false;
    if (out) put(g, x, y, voidKind);
  }
  placeSpawn(g, rng, rng.weighted({ edge: 2, inset: 1.5, corner: shape === 'square' ? 1 : 0 }), 2);
  const S = spawnCentre(g), rings = rng.int(1, 2);
  for (let k = 0; k < rings; k++) {
    const R = m * (k ? rng.uniform(0.3, 0.38) : rng.uniform(0.12, 0.2)), n = rng.int(2, 4), ph = rng.uniform(0, Math.PI), kinds = { [WALL]: 3, [BUSH]: 1.5, [HOLE]: voidKind === HOLE ? 1 : 0.3 };
    const names = rng.shuffle(['bar', 'ell', 'pillar', 'broken', 'hook', 'arch', 'bunker', 'corner', 'screen', 'skirt']).slice(0, 2);
    for (let j = 0; j < n; j++) {
      const a = ph + j * Math.PI / n, p = [C[0] + R * Math.cos(a), C[1] + R * Math.sin(a)];
      scatterPrefabs(g, rng, 1, { names, kinds, gap: 3, where: (x, y) => Math.hypot(x - p[0], y - p[1]) < 2, spawnGap: 3 });
    }
  }
  clumps(g, rng, rng.int(2, 5), [3, 7]);
  clearSpawn(g);
  g.sites.push({ shared: 'treasure', required: true });
  if (rng.chance(0.5)) site(g, C, 5, { altar: rng.chance(0.5) ? 'self' : true }, { required: true });
  else site(g, lerp(S, C, 0.55), 6, { altar: true }, { required: true });
  site(g, lerp(S, C, 0.25), 6, tier(rng, s, 'home'), { required: true, home: true });
}

// Farm country: each half is a patchwork of fenced fields (hedges, low walls, ditches) holding camp
// groups, divided from the other half by a river or wall crossed far from the spawns.
function farmland(g, rng, s) {
  begin(g, GROUND);
  placeSpawn(g, rng, rng.weighted({ edge: 2, corner: 2 }));
  const C = centre(g), S = spawnCentre(g), S2 = mirrorPt(g, S), m = Math.min(g.W, g.H), kind = rng.weighted({ [HOLE]: 2, [WALL]: 1 }) | 0, t = rng.int(2, 3);
  const ax = [S2[0] - S[0], S2[1] - S[1]], al = Math.hypot(...ax), dir = g.sym === 'horizontal' ? [0, 1] : g.sym === 'vertical' ? [1, 0] : [-ax[1] / al, ax[0] / al];
  const reach = Math.hypot(g.W, g.H), line = g.sym === 'rotational' ? meander(rng, C, [C[0] + dir[0] * reach, C[1] + dir[1] * reach], 0.04) : [[C[0] - dir[0] * reach, C[1] - dir[1] * reach], [C[0] + dir[0] * reach, C[1] + dir[1] * reach]];
  stroke(g, line, t, kind);
  // Crossings far out along the divide.
  // Crossings far out along the divide: at a fraction of the way from the centre to the edge (on a
  // mirror axis the line is its own mirror, so both ends get one; under rotation the mirror does).
  const toEdge = Math.min(...[0, 1].map(i => dir[i] ? Math.abs((dir[i] > 0 ? (i ? g.H : g.W) - 1 - C[i] : C[i]) / dir[i]) : Infinity));
  let approach = null;
  for (const u of g.sym === 'rotational' ? [rng.uniform(0.45, 0.85)] : [rng.uniform(0.45, 0.85), -rng.uniform(0.45, 0.85)]) {
    const p = [C[0] + dir[0] * u * toEdge, C[1] + dir[1] * u * toEdge], d = dir, nrm = [-d[1], d[0]];
    approach ??= [-1, 1].map(k => [p[0] + nrm[0] * k * (t + 3), p[1] + nrm[1] * k * (t + 3)]).reduce((u, v) => dist(u, S) < dist(v, S) ? u : v);
    if (inMap(g, p, 2)) stroke(g, [[p[0] - nrm[0] * (t + 2), p[1] - nrm[1] * (t + 2)], [p[0] + nrm[0] * (t + 2), p[1] + nrm[1] * (t + 2)]], rng.int(2, 4), GROUND, [kind]);
  }
  // Fields: fenced rectangles in team A's half, apart from each other and the spawn.
  const fields = [];
  for (let tries = 0; fields.length < rng.int(4, 9) && tries < 600; tries++) {
    const w = rng.int(5, 11), h = rng.int(5, 9), x = rng.int(1, g.W - w - 1), y = rng.int(1, g.H - h - 1), c = [x + (w - 1) / 2, y + (h - 1) / 2];
    if (!onSideA(g, c) || dist(c, mirrorPt(g, c)) < Math.max(w, h) + 4 || dist(c, S) < Math.max(w, h) / 2 + 5) continue;
    if (fields.some(f => x < f.x + f.w + 3 && f.x < x + w + 3 && y < f.y + f.h + 3 && f.y < y + h + 3)) continue;
    let clean = true;
    for (let yy = y - 1; yy <= y + h && clean; yy++) for (let xx = x - 1; xx <= x + w; xx++) if (g.in(xx, yy) && g.get(xx, yy) !== GROUND) { clean = false; break; }
    if (clean) fields.push({ x, y, w, h, c });
  }
  for (const f of fields) {
    const fence = +rng.weighted({ [BUSH]: 3, [WALL]: 2, [HOLE]: 0.7, 0: 0.8 });
    if (fence) for (let yy = f.y; yy < f.y + f.h; yy++) for (let xx = f.x; xx < f.x + f.w; xx++) if (xx === f.x || yy === f.y || xx === f.x + f.w - 1 || yy === f.y + f.h - 1) put(g, xx, yy, fence);
    for (let j = rng.int(1, 2); j > 0; j--) {
      const side = rng.int(0, 3), gw = 2, at = rng.int(1, (side % 2 ? f.h : f.w) - gw - 1);
      for (let q = 0; q < gw; q++) put(g, side % 2 ? (side === 1 ? f.x + f.w - 1 : f.x) : f.x + at + q, side % 2 ? f.y + at + q : (side === 0 ? f.y : f.y + f.h - 1), GROUND);
    }
    if (rng.chance(0.3)) for (let yy = f.y + 2; yy < f.y + f.h - 2; yy += 2) box(g, f.x + 2, yy, f.w - 4, 1, BUSH);
    site(g, f.c, Math.min(f.w, f.h) / 2, tier(rng, s, dist(f.c, S) < dist(f.c, C) ? 'home' : 'mid'));
  }
  scatterPrefabs(g, rng, rng.int(2, Math.round(m / 8)), { gap: 7, names: ['bar', 'long', 'ell', 'copse', 'hedge', 'posts'] });
  clearSpawn(g);
  site(g, lerp(S, C, 0.2), 8, tier(rng, s, 'home'), { required: true, home: true });
  altarPlan(g, rng, S, C, 8, approach);
  if (rng.chance(0.4)) site(g, lerp(C, S, 0.1), 6, tier(rng, s, 'treasure'));
}

// An organic landmass in a sea of holes (or rock): lobes joined by isthmuses, its coast drawn from
// a signed distance with low-frequency noise. Sometimes one strait is a dash wide.
function continent(g, rng, s) {
  const voidKind = s.void_kind === 'wall' ? WALL : HOLE, C = centre(g), m = Math.min(g.W, g.H);
  begin(g, voidKind);
  placeSpawn(g, rng, rng.weighted({ corner: 2, edge: 2, inset: 1 }), 1);
  const S = spawnCentre(g), lobes = [{ p: lerp(S, C, 0.12), r: m * rng.uniform(0.12, 0.2) + 2 }];
  if (rng.chance(0.75)) lobes.push({ p: C, r: m * rng.uniform(0.08, 0.2) + 1.5 });
  for (let tries = 0; lobes.length < 2 + rng.int(1, 3) && tries < 300; tries++) {
    const r = m * rng.uniform(0.07, 0.15) + 1.5, p = [rng.uniform(r, g.W - 1 - r), rng.uniform(r, g.H - 1 - r)];
    if (!onSideA(g, p) || dist(p, mirrorPt(g, p)) < 2 * r + 3 || lobes.some(l => dist(l.p, p) < (l.r + r) * 0.9)) continue;
    lobes.push({ p, r });
  }
  // Isthmuses: each lobe to its nearest earlier lobe, plus the centre or a mirrored lobe.
  const necks = [];
  for (let k = 1; k < lobes.length; k++) {
    const to = lobes.slice(0, k).reduce((b, l) => dist(l.p, lobes[k].p) < dist(b.p, lobes[k].p) ? l : b);
    necks.push([lobes[k].p, to.p, rng.uniform(1.2, 3.5)]);
  }
  const far = lobes.slice(1).reduce((b, l) => dist(l.p, mirrorPt(g, l.p)) < dist(b.p, mirrorPt(g, b.p)) ? l : b, lobes[0]);
  necks.push([far.p, mirrorPt(g, far.p), rng.uniform(1.5, 3.5)]);
  if (rng.chance(0.4)) necks.push([lobes[0].p, rng.choice(lobes.slice(1)).p, rng.uniform(1.2, 2.5)]);
  const segDist = (p, a, b) => { const l2 = (b[0] - a[0]) ** 2 + (b[1] - a[1]) ** 2, t = l2 ? Math.max(0, Math.min(1, ((p[0] - a[0]) * (b[0] - a[0]) + (p[1] - a[1]) * (b[1] - a[1])) / l2)) : 0; return dist(p, lerp(a, b, t)); };
  const amp = rng.uniform(1, 3.5), noise = valueNoise(rng, g.W, g.H, rng.uniform(6, 14), 2);
  const sdf = p => Math.min(...lobes.map(l => dist(p, l.p) - l.r), ...necks.map(([a, b, r]) => segDist(p, a, b) - r));
  for (let i = 0; i < g.t.length; i++) {
    const j = g.mirror(i);
    if (j < i) continue;
    const x = i % g.W, y = (i - x) / g.W, p = [x, y], d = Math.min(sdf(p), sdf(mirrorPt(g, p))) + amp * (noise[i] - 0.5) * 2;
    if (d <= 0) g.set(x, y, GROUND);
  }
  // A strait: one isthmus cut by a single row of holes.
  if (voidKind === HOLE && necks.length > 2 && rng.chance(0.35)) {
    const [a, b] = rng.choice(necks.slice(0, -1)), mid = lerp(a, b, 0.5), d = [(b[0] - a[0]) / dist(a, b), (b[1] - a[1]) / dist(a, b)];
    cut(g, mid, d, 1, 6, HOLE);
    raise(g, 'dash');
  }
  for (const l of lobes) if (l.r > 6 && rng.chance(0.4)) blob(g, rng, lerp(l.p, C, 0.2), l.r * rng.uniform(0.15, 0.3), 0.2, HOLE, [GROUND]);
  if (rng.chance(0.7)) rims(g, rng, [voidKind], rng.uniform(0.15, 0.4));
  scatterPrefabs(g, rng, rng.int(1, Math.round(m / 9)), { gap: 6 });
  clumps(g, rng, rng.int(1, 5), [3, 8]);
  clearSpawn(g, 1);
  site(g, lobes[0].p, lobes[0].r, tier(rng, s, 'home'), { required: true, home: true });
  altarPlan(g, rng, lobes[0].p, C, Math.min(8, lobes[0].r + 3));
  for (const l of lobes.slice(1)) site(g, l.p, l.r, rng.chance(0.2) ? { altar: true } : tier(rng, s, dist(l.p, C) < 3 ? 'treasure' : 'mid'));
}

// A hedge maze: corridors bounded by bush hedges (walkable, but they block sight), some hedges
// stiffened into walls, and a few plazas. Walking is easy; seeing is not.
function hedges(g, rng, s) {
  begin(g, GROUND);
  const c = rng.int(4, 6), nx = Math.floor((g.W - 1) / c), ny = Math.floor((g.H - 1) / c), ox = Math.floor((g.W - nx * c) / 2), oy = Math.floor((g.H - ny * c) / 2);
  const wallShare = rng.uniform(0.05, 0.25), braid = rng.uniform(0.1, 0.35), open = new Set(), seen = new Uint8Array(nx * ny), stack = [[0, 0]];
  seen[0] = 1;
  const key = (i, j, di, dj) => `${Math.min(i, i + di)},${Math.min(j, j + dj)},${di ? 'h' : 'v'}`;
  while (stack.length) {
    const [i, j] = stack.at(-1), next = rng.shuffle([[1, 0], [-1, 0], [0, 1], [0, -1]]).filter(([di, dj]) => i + di >= 0 && j + dj >= 0 && i + di < nx && j + dj < ny && !seen[(j + dj) * nx + i + di]);
    if (!next.length) { stack.pop(); continue; }
    const [di, dj] = next[0];
    open.add(key(i, j, di, dj)); seen[(j + dj) * nx + i + di] = 1; stack.push([i + di, j + dj]);
  }
  // Hedges between cells that are not joined; drawn with their mirrors, which only adds hedges.
  for (let j = 0; j < ny; j++) for (let i = 0; i < nx; i++) {
    for (const [di, dj] of [[1, 0], [0, 1]]) {
      if (i + di >= nx || j + dj >= ny || open.has(key(i, j, di, dj)) || rng.chance(braid)) continue;
      const kind = rng.chance(wallShare) ? WALL : BUSH, x = ox + (i + di) * c, y = oy + (j + dj) * c;
      if (di) box(g, x, oy + j * c, 1, c + 1, kind); else box(g, ox + i * c, y, c + 1, 1, kind);
    }
  }
  const C = centre(g);
  disc(g, C, rng.uniform(3, 6), GROUND);
  for (let k = rng.int(1, 3); k > 0; k--) { const p = [rng.uniform(5, g.W - 6), rng.uniform(5, g.H - 6)]; disc(g, p, rng.uniform(2.5, 4.5), GROUND); }
  placeSpawn(g, rng, rng.weighted({ corner: 3, edge: 1 }), 2);
  const S = spawnCentre(g);
  site(g, lerp(S, C, 0.2), 8, tier(rng, s, 'home'), { required: true, home: true });
  altarPlan(g, rng, S, C);
  g.sites.push({ shared: 'treasure' });
  for (let k = rng.int(2, 4); k > 0; k--) site(g, lerp(S, C, rng.uniform(0.3, 0.8)).map((v, i) => v + rng.uniform(-0.3, 0.3) * (i ? g.H : g.W)), 6, tier(rng, s, 'mid'));
}

export const DESIGNS = { islands, rivers, fortress, barrier, dungeon, 'three-lane': threeLane, arena, farmland, continent, hedges };
export { PREFABS, prefabTiles, scatterPrefabs, clumps, stroke, disc, blob, box, put, seal, rims, cut, meander, smooth, along, dist, lerp, centre, spawnCentre, onSideA, inMap };
