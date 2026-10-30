// Topology: maps built around how regions connect. A region graph (home, farms, altars, treasure and
// hubs, joined by typed links: wide or 1-wide walks, bush curtains, dash or crystal gaps, camp plugs
// and long detours) is laid out symmetrically, drawn, then checked against what its layout promises
// (a tree, a split world, a spawn island, a backdoor, a toll road, a shortcut). Also body-blocking
// chokepoints and spawn extremes: touching spawns, gatehouse spawns, central spawns and odd spawn
// rectangles in cramped surrounds.
import { ALTAR, BUSH, GROUND, GenFail, HOLE, WALL } from './grid.mjs';
import { along, begin, blob, box, centre, clearSpawn, clumps, dist, disc, inMap, lerp, meander, mirrorPt, onSideA, put, raise, rims, scatterPrefabs, site, smooth, spawnCentre, spawnDims, stroke, tier } from './design.mjs';

// ---- geometry ------------------------------------------------------------------------------
const segPt = (p, a, b) => {
  const dx = b[0] - a[0], dy = b[1] - a[1], l2 = dx * dx + dy * dy, t = l2 ? Math.max(0, Math.min(1, ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / l2)) : 0;
  return Math.hypot(p[0] - a[0] - t * dx, p[1] - a[1] - t * dy);
};
const polyPt = (P, p) => { let m = P.length === 1 ? dist(P[0], p) : Infinity; for (let k = 0; k + 1 < P.length; k++) m = Math.min(m, segPt(p, P[k], P[k + 1])); return m; };
const plen = pts => pts.slice(1).reduce((s, p, k) => s + dist(pts[k], p), 0);
const resample = (pts, t0, t1, step = 2.5) => { const n = Math.max(1, Math.ceil(plen(pts) * (t1 - t0) / step)); return Array.from({ length: n + 1 }, (_, k) => along(pts, t0 + (t1 - t0) * k / n).p); };
const rectDist = (r, x, y) => Math.max(Math.max(r.x - x, 0, x - (r.x + r.w - 1)), Math.max(r.y - y, 0, y - (r.y + r.h - 1)));
const walkable = k => k === GROUND || k === BUSH;
const idxOf = (g, [x, y]) => Math.round(y) * g.W + Math.round(x);
const noCamp = (g, x, y) => { if (g.in(x, y)) { g.noCamp.add(y * g.W + x); g.noCamp.add(g.mirror(y * g.W + x)); } };

// ---- travel --------------------------------------------------------------------------------
// Cost from a team's spawn (the other spawn is impassable, and blocks dashes): walking, or with
// dashes (level 1) or crystals (level 2) too. `block` marks extra impassable tiles.
function field(g, team = 0, level = 0, block = null) {
  const pass = g.walkable(), foe = g.spawnTiles(1 - team);
  for (const i of foe) pass[i] = 0;
  if (block) for (let i = 0; i < block.length; i++) if (block[i]) pass[i] = 0;
  if (!level) return g.bfs(g.spawnTiles(team), pass);
  const m = Uint8Array.from(g.t, k => k === WALL ? 1 : 0);
  for (const i of foe) m[i] = 1;
  return g.travel(g.spawnTiles(team), pass, m, level);
}
const nearest = (d, tiles) => tiles.reduce((b, i) => d[i] >= 0 && (b < 0 || d[i] < b) ? d[i] : b, -1);

// ---- spawns ----------------------------------------------------------------------------------
// Any rectangle of 9-16 tiles loads; the ladder only has 3x3, 4x4, 4x3 and 5x2.
const ODD = { '1x9': 1, '1x10': 0.4, '1x12': 0.5, '1x16': 0.2, '2x5': 1, '2x6': 1.2, '2x7': 0.6, '2x8': 0.6, '3x4': 1, '3x5': 1.2, '5x2': 0.4 };
const oddDims = rng => { const [w, h] = rng.weighted(ODD).split('x').map(Number); return rng.chance(0.5) ? [w, h] : [h, w]; };

// Team A's spawn: 'corner', 'edge' or 'inset', as design.mjs's placeSpawn but with given dimensions.
function putSpawn(g, rng, where, [w, h], clear = 1) {
  const i = rng.int(0, 2), { W, H } = g, midY = Math.round(H / 2 - h / 2 + rng.int(-Math.floor(H / 8), Math.floor(H / 8)));
  const midX = Math.round(W / 2 - w / 2 + rng.int(-Math.floor(W / 8), Math.floor(W / 8))), low = rng.chance(0.5);
  let x, y;
  if (g.sym === 'vertical') {
    y = where === 'inset' ? Math.round(H * rng.uniform(0.08, 0.16)) : i;
    x = where === 'edge' ? midX : where === 'inset' ? Math.round(W * rng.uniform(0.1, 0.3)) : low ? i : W - w - i;
  } else {
    x = where === 'inset' ? Math.round(W * rng.uniform(0.08, 0.16)) : i;
    y = where === 'edge' ? midY : where === 'inset' ? Math.round(H * rng.uniform(0.1, 0.3)) : low ? i : H - h - i;
  }
  g.spawn = { x: Math.max(0, Math.min(W - w, x)), y: Math.max(0, Math.min(H - h, y)), w, h };
  clearSpawn(g, clear);
}

// Spawn-axis frame for the spawn designers: u runs from team A's spawn towards B's, v across it.
// Under a mirror the axis is u = (U-1)/2; under rotation both u and v flip.
function frame(g, rng) {
  const rot = g.sym === 'rotational', alongX = g.sym === 'horizontal' || (rot && rng.chance(g.W > g.H ? 0.8 : g.W < g.H ? 0.2 : 0.5));
  const U = alongX ? g.W : g.H, V = alongX ? g.H : g.W;
  const xy = (u, v) => alongX ? [u, v] : [v, u];
  return { rot, alongX, U, V, xy, cu: (U - 1) / 2, set: (u, v, k) => { const [x, y] = xy(u, v); put(g, x, y, k); }, get: (u, v) => { const [x, y] = xy(u, v); return g.in(x, y) ? g.get(x, y) : -1; } };
}

// Places team A's spawn at frame cells [u0, u0+du) x [v0, v0+dv).
function frameSpawn(g, F, u0, v0, du, dv) {
  const [x, y] = F.xy(u0, v0), [w, h] = F.alongX ? [du, dv] : [dv, du];
  g.spawn = { x, y, w, h };
  if (g.spawnTiles(1).some(i => g.spawnTiles(0).includes(i))) throw new GenFail('spawns overlap');
  box(g, x, y, w, h, GROUND);
}

// One half of a self-mirrored set of cells (each mirror pair once): a shared group stores this.
const canonical = (g, cells) => cells.filter(([, x, y]) => { const i = y * g.W + x; return i <= g.mirror(i); });

// ---- regions -------------------------------------------------------------------------------
const rectRoom = (x0, y0, x1, y1, extra = {}) => ({ x0, y0, x1, y1, p: [(x0 + x1) / 2, (y0 + y1) / 2], r: Math.min(x1 - x0, y1 - y0) / 2 + 0.5, R: Math.max(x1 - x0, y1 - y0) / 2 + 1, ...extra });
function room(rng, style, p, r, extra = {}) {
  if (style !== 'built') { const rough = rng.uniform(0.04, 0.16); return { p, r, rough, R: r * (1 + 2 * rough) + 0.5, ...extra }; }
  const hx = Math.max(1, Math.round(r * rng.uniform(0.7, 1.1))), hy = Math.max(1, Math.round(r * rng.uniform(0.7, 1.1))), x = Math.round(p[0]), y = Math.round(p[1]);
  return rectRoom(x - hx, y - hy, x + hx, y + hy, extra);
}
const drawRoom = (g, rng, n) => n.x0 !== undefined ? box(g, n.x0, n.y0, n.x1 - n.x0 + 1, n.y1 - n.y0 + 1, GROUND) : blob(g, rng, n.p, n.r, n.rough, GROUND);
const inRoom = (n, [x, y], pad = 0) => n.x0 !== undefined ? x >= n.x0 - pad && x <= n.x1 + pad && y >= n.y0 - pad && y <= n.y1 + pad : dist([x, y], n.p) <= n.R + pad;
const siteR = n => n.x0 !== undefined ? Math.max(n.x1 - n.x0, n.y1 - n.y0) / 2 + 0.6 : n.r;

// Walkable tiles of a room (and of its mirror).
function roomTiles(g, n, both = true) {
  const out = [];
  for (let y = 0; y < g.H; y++) for (let x = 0; x < g.W; x++) {
    if (!walkable(g.get(x, y))) continue;
    if (inRoom(n, [x, y]) || (both && inRoom(n, mirrorPt(g, [x, y])))) out.push(y * g.W + x);
  }
  return out;
}

function homeRoom(g, rng, s, style, big) {
  const { W, H } = g, sp = g.spawn, clip = (x0, y0, x1, y1, extra) => rectRoom(Math.max(0, x0), Math.max(0, y0), Math.min(W - 1, x1), Math.min(H - 1, y1), { role: 'home', ...extra });
  if (s.cramp) return clip(sp.x - 1, sp.y - 1, sp.x + sp.w, sp.y + sp.h, { cramp: true });
  if (style === 'built') { const k = () => big ? rng.int(5, 7) : rng.int(2, 4); return clip(sp.x - k(), sp.y - k(), sp.x + sp.w - 1 + k(), sp.y + sp.h - 1 + k(), { big }); }
  const S = spawnCentre(g), p = lerp(S, centre(g), rng.uniform(0, 0.08)), rough = rng.uniform(0.03, 0.07);
  const r = Math.max((dist(p, S) + Math.hypot(sp.w, sp.h) / 2 + 2) / (1 - 3 * rough), big ? Math.min(W, H) * rng.uniform(0.12, 0.17) + 3 : 0);
  return { p, r, rough, R: r * (1 + 2 * rough) + 0.5, role: 'home', big };
}

// ---- links ---------------------------------------------------------------------------------
// Link types: walks (wide, narrow = 1 wide, bush = a curtain across, detour = a long meander),
// gaps (dash = one hole across; crystal = two holes or one or two walls across) and plug (a camp
// group fills the corridor). Features sit on the stretch between the rooms (`ta`..`tb`).
const GAPS = new Set(['dash', 'crystal']);
const FEATURED = new Set(['dash', 'crystal', 'plug', 'bush', 'toll']);

// Tiles across a link at fraction t: an axis-aligned band `thick` deep, held to the link's own
// corridor (so a nearby corridor is untouched). `over` also paints the void beside it (a wall band
// in a hole sea must reach past the bridge, or a dash would pass beside it).
function band(g, L, t, thick, kind, over = false, rooms = []) {
  const { p, d } = along(L.pts, t), alongX = Math.abs(d[0]) >= Math.abs(d[1]), reach = L.w + 3, out = [];
  const x0 = Math.round(p[0] - (thick - 1) / 2), y0 = Math.round(p[1] - (thick - 1) / 2);
  for (let a = 0; a < thick; a++) for (let b = -reach; b <= reach; b++) {
    const x = alongX ? x0 + a : Math.round(p[0]) + b, y = alongX ? Math.round(p[1]) + b : y0 + a;
    if (!g.in(x, y) || polyPt(L.pts, [x, y]) > L.w / 2 + (over ? 2 : 1.2) || rooms.some(n => inRoom(n, [x, y]) || inRoom(n, mirrorPt(g, [x, y])))) continue;
    if (over || walkable(g.get(x, y))) { if (kind !== null) put(g, x, y, kind); out.push([x, y]); }
  }
  return out;
}

// A fraction along the link's open stretch, kept off its corners (a band at an L-bend would run
// along a leg).
function midT(rng, L, spread = 0.25) {
  const len = L.len, corners = L.pts.slice(1, -1).map((_, k) => plen(L.pts.slice(0, k + 2)) / len);
  for (let k = 0; k < 12; k++) {
    const t = L.ta + (L.tb - L.ta) * (0.5 + rng.uniform(-spread, spread));
    if (L.pts.length > 6 || corners.every(c => Math.abs(c - t) * len > L.w + 3)) return t;
  }
  return null;
}

// Body-blocking pieces cut into the void beside a room, along a cardinal ray from its centre: a
// niche (a 1-wide dead end with an altar at its end: one walkable tile within 1 of it) or an alcove
// (a 1-wide neck into a pocket filled with camps: captured only through the neck).
function rayExit(g, n, [dx, dy]) {
  let x = Math.round(n.p[0]), y = Math.round(n.p[1]);
  for (let k = 0; k < 40 && g.in(x, y) && walkable(g.get(x, y)); k++) { x += dx; y += dy; }
  return g.in(x, y) && !walkable(g.get(x, y)) ? [x, y] : null;
}
const isVoid = (g, x, y) => g.in(x, y) && (g.get(x, y) === WALL || g.get(x, y) === HOLE);
const farFromMirror = (g, x, y, r = 3) => { const [mx, my] = g.mirrorXY(x, y); return Math.max(Math.abs(mx - x), Math.abs(my - y)) >= r; };

function niche(g, rng, n, len) {
  for (const [dx, dy] of rng.shuffle([[1, 0], [-1, 0], [0, 1], [0, -1]])) {
    const e = rayExit(g, n, [dx, dy]);
    if (!e) continue;
    const tiles = Array.from({ length: len + 1 }, (_, k) => [e[0] + dx * k, e[1] + dy * k]), alt = tiles.at(-1), [px, py] = [dy, dx];
    const sideVoid = ([x, y]) => isVoid(g, x, y) && isVoid(g, x + px, y + py) && isVoid(g, x - px, y - py);
    if (!tiles.every(sideVoid) || !sideVoid([alt[0] + dx, alt[1] + dy]) || !tiles.every(([x, y]) => inMap(g, [x, y], 1) && farFromMirror(g, x, y))) continue;
    if (rectDist(g.spawn, ...alt) < 3 || rectDist(g.spawn, ...g.mirrorXY(...alt)) < 3) continue;
    let crowd = false;
    for (let j = -4; j <= 4; j++) for (let i = -4; i <= 4; i++) if (g.in(alt[0] + i, alt[1] + j) && g.get(alt[0] + i, alt[1] + j) === ALTAR) crowd = true;
    if (crowd) continue;
    for (const [x, y] of tiles.slice(0, -1)) { put(g, x, y, GROUND); noCamp(g, x, y); }
    put(g, alt[0], alt[1], ALTAR);
    let open = 0;
    for (let j = -1; j <= 1; j++) for (let i = -1; i <= 1; i++) open += g.in(alt[0] + i, alt[1] + j) && walkable(g.get(alt[0] + i, alt[1] + j));
    if (open >= 1 && open <= 2) { noCamp(g, e[0] - dx, e[1] - dy); return alt; }
    for (const [x, y] of tiles) put(g, x, y, isVoid(g, x + px, y + py) ? g.get(x + px, y + py) : WALL);
  }
  return null;
}

const ALCOVES = [[[0, 0], [0, 1], [1, 0], [1, 1]], [[0, -1], [0, 0], [0, 1]], [[0, 0], [1, 0]], [[0, -1], [0, 0], [0, 1], [1, -1], [1, 0], [1, 1]], [[0, 0], [1, 0], [1, -1], [1, 1], [2, 0]]];
function alcove(g, rng, n, neck) {
  const shape = rng.choice(ALCOVES);
  for (const [dx, dy] of rng.shuffle([[1, 0], [-1, 0], [0, 1], [0, -1]])) {
    const e = rayExit(g, n, [dx, dy]);
    if (!e) continue;
    const [px, py] = [dy, dx], necks = Array.from({ length: neck }, (_, k) => [e[0] + dx * k, e[1] + dy * k]), base = [e[0] + dx * neck, e[1] + dy * neck];
    // Shape coordinates: a along the ray, b across it.
    const cells = shape.map(([a, b]) => [base[0] + dx * a + px * b, base[1] + dy * a + py * b]);
    const key = new Set(cells.map(([x, y]) => y * g.W + x));
    const ok = necks.every(([x, y]) => isVoid(g, x, y) && isVoid(g, x + px, y + py) && isVoid(g, x - px, y - py) && farFromMirror(g, x, y))
      && cells.every(([x, y]) => {
        if (!inMap(g, [x, y], 1) || !farFromMirror(g, x, y, 4)) return false;
        for (let j = -1; j <= 1; j++) for (let i = -1; i <= 1; i++) if (!key.has((y + j) * g.W + x + i) && !(x + i === necks.at(-1)[0] && y + j === necks.at(-1)[1]) && !isVoid(g, x + i, y + j)) return false;
        return true;
      });
    if (!ok) continue;
    for (const [x, y] of necks) { put(g, x, y, GROUND); noCamp(g, x, y); }
    for (const [x, y] of cells) put(g, x, y, GROUND);
    // The cell at the neck is the guard; the rest pay.
    const boss = rng.weighted({ elk: 2, wolf: 2, golem: 0.6 }), pay = rng.weighted({ gems: 2, gold: 1, mixed: 1.5 });
    return cells.map(([x, y], k) => [k === shape.findIndex(([a, b]) => a === 0 && b === 0) ? boss : pay === 'gems' ? 'gem_cluster' : pay === 'gold' ? 'gold_cluster' : rng.weighted({ gem_cluster: 2, gold_cluster: 1, wolf: 1 }), x, y]);
  }
  return null;
}

// ---- the graph designer ------------------------------------------------------------------------
// Layouts: 'web' (cycle-rich), 'tree' (one walking route between any two rooms), 'split' (halves
// joined only by dash or crystal gaps), 'island' (home left only by dash or crystal), 'backdoor',
// 'toll' and 'shortcut' (see the presets).
function topograph(g, rng, s) {
  const lay = s.layout, style = s.style === 'built' ? 'built' : 'cave', voidKind = s.void_kind === 'wall' ? WALL : HOLE;
  begin(g, voidKind);
  const { W, H } = g, C = centre(g), m = Math.min(W, H), M = 1000;
  putSpawn(g, rng, rng.weighted(s.spawn_where ?? { corner: 3, edge: 2, inset: 1.5 }), s.spawn_odd ? oddDims(rng) : spawnDims(rng), 0);
  const nodes = [];
  const home = homeRoom(g, rng, { ...s, cramp: lay !== 'backdoor' && rng.chance(s.cramp ?? 0) }, lay === 'backdoor' ? 'built' : style, lay === 'island' || rng.chance(s.big_home ?? 0.4));
  nodes.push(home);
  if (dist(home.p, mirrorPt(g, home.p)) < 2 * home.R + 4) throw new GenFail('home meets its mirror');
  const all = () => nodes.flatMap(n => n.self ? [[n.p, n.R]] : [[n.p, n.R], [mirrorPt(g, n.p), n.R]]);
  const fits = (n, gap = 5) => all().every(([q, R]) => dist(n.p, q) >= n.R + R + gap);
  let hub = null;
  if (rng.chance(s.hub ?? 0.5)) {
    const n = room(rng, style, C, m * (lay === 'toll' ? rng.uniform(0.04, 0.07) : rng.uniform(0.06, 0.1)) + 2, { self: true, role: 'hub' });
    n.p = C;
    if (fits(n)) { nodes.push(n); hub = n; }
  }
  const bd = lay === 'backdoor' ? backdoorPlan(g, rng, s, nodes, home, hub) : null;
  if (lay === 'toll' && !hub) throw new GenFail('no hub for the toll road');
  const road = lay === 'toll' ? [home.p, C] : null;
  const avoid = n => bd ? [bd.corr, bd.corr.map(p => mirrorPt(g, p))].some(P => polyPt(P, n.p) < n.R + bd.w / 2 + 3)
    : road ? [road, road.map(p => mirrorPt(g, p))].some(P => polyPt(P, n.p) < n.R + 9) : false;
  const pin = lay === 'shortcut' ? hairpin(g, rng, nodes, home, fits, style) : null;
  const want = Math.max(3, Math.min(12, Math.round(W * H / rng.uniform(300, 520)))) - (pin ? pin.length : 0) + (s.extra_rooms ?? 0);
  for (let tries = 0, k = 0; k < want && tries < 600; tries++) {
    const r = m * rng.uniform(0.045, 0.095) + 1.5, n = room(rng, style, [rng.uniform(r + 1, W - 2 - r), rng.uniform(r + 1, H - 2 - r)], r, { role: 'field' });
    if (!onSideA(g, n.p) || dist(n.p, mirrorPt(g, n.p)) < 2 * n.R + 5 || !fits(n) || avoid(n)) continue;
    nodes.push(n); k++;
  }
  // Ids: node k, its mirror k + M (a self-mirrored node is its own mirror).
  const self = id => !!nodes[id % M].self, mir = id => self(id) ? id : id >= M ? id - M : id + M;
  const pos = id => id >= M ? mirrorPt(g, nodes[id - M].p) : nodes[id].p, nd = id => nodes[id % M], isA = id => id < M && !self(id);
  const ids = nodes.flatMap((n, k) => n.self ? [k] : [k, k + M]);
  const parent = new Map(ids.map(i => [i, i])), find = i => { while (parent.get(i) !== i) i = parent.get(i); return i; };
  const join = (a, b) => parent.set(find(a), find(b));
  const links = [];
  const widthOf = type => type === 'narrow' ? 1 : type === 'plug' ? rng.int(1, 2) : type === 'wide' ? rng.int(2, style === 'built' ? 3 : 4) : type === 'bush' ? rng.int(2, 3) : rng.int(1, s.max_w ?? 3);
  const make = (a, b, type, pts = null) => {
    const A = pos(a), B = pos(b), selfL = b === mir(a) || (self(a) && self(b)), w = s.narrow && type !== 'detour' && (a === 0 || b === M) ? 1 : widthOf(type);
    if (!pts) {
      if (selfL) pts = style === 'built' && g.sym === 'rotational' ? (rng.chance(0.5) ? [A, [C[0], A[1]], [C[0], B[1]], B] : [A, [A[0], C[1]], [B[0], C[1]], B]) : [A, B];
      else if (type === 'detour') pts = meander(rng, A, B, rng.uniform(0.25, 0.45), rng.uniform(1.2, 2.5));
      else if (style === 'built' && !GAPS.has(type)) pts = rng.chance(0.5) ? [A, [B[0], A[1]], B] : [A, [A[0], B[1]], B];
      else { const len = dist(A, B), mid = lerp(A, B, 0.5), bend = GAPS.has(type) ? 0 : rng.uniform(-0.15, 0.15) * len; pts = smooth([A, [mid[0] - (B[1] - A[1]) / len * bend, mid[1] + (B[0] - A[0]) / len * bend], B]); }
    }
    const len = plen(pts), ta = (nd(a).R + 1) / len, tb = 1 - (nd(b).R + 1) / len, core = tb > ta ? resample(pts, ta, tb) : null;
    if (FEATURED.has(type) && (!core || (tb - ta) * len < (type === 'toll' ? 6 : 3))) return null;
    return { a, b, type, w, cw: type === 'toll' ? w + 9 : w, pts, len, ta, tb, core, self: selfL, mcore: core && core.map(p => mirrorPt(g, p)) };
  };
  // Links keep apart (and off other rooms), except near a room they share, where they fan out.
  const apart = (L, Q, ends, thr) => L.core.every(p => ends.some(id => dist(p, pos(id)) < nd(id).R + 6) || polyPt(Q, p) >= thr);
  const ok = L => {
    if (!L) return false;
    if (!L.core) return true;
    if (L.core.some(p => !inMap(g, p, 1))) return false;
    for (const id of ids) if (id !== L.a && id !== L.b && polyPt(L.core, pos(id)) < nd(id).R + L.cw / 2 + 2) return false;
    for (const K of links) {
      if (!K.core) continue;
      const thr = (L.cw + K.cw) / 2 + 2.5;
      if (!apart(L, K.core, [L.a, L.b].filter(id => id === K.a || id === K.b), thr) || !apart(L, K.mcore, [L.a, L.b].filter(id => id === mir(K.a) || id === mir(K.b)), thr)) return false;
    }
    return L.self || apart(L, L.mcore, [L.a, L.b].filter(id => id === mir(L.a) || id === mir(L.b)), L.cw + 2.5);
  };
  const add = (a, b, type, tries = 3) => {
    for (let t = 0; t < tries; t++) {
      const L = make(a, b, type);
      if (ok(L)) { links.push(L); join(a, b); join(mir(a), mir(b)); return L; }
    }
    return null;
  };
  const linked = (a, b) => links.some(L => (L.a === a && L.b === b) || (L.a === b && L.b === a) || (L.a === mir(a) && L.b === mir(b)) || (L.a === mir(b) && L.b === mir(a)));
  const free = id => !nd(id).pocket;
  const pairs = (want = () => true) => {
    const out = [];
    for (const a of ids) if (isA(a) && free(a)) for (const b of ids) {
      if (b === a || !free(b) || (isA(b) && b < a) || !want(a, b)) continue;
      out.push([a, b, dist(pos(a), pos(b)) - nd(a).R - nd(b).R]);
    }
    return out.sort((p, q) => p[2] - q[2]);
  };
  const kruskal = (list, type) => { for (const [a, b] of list) if (find(a) !== find(b)) add(a, b, type(a, b)); };
  const loops = (list, chance, type) => { for (const [a, b, gap] of list) if (gap < m * 0.45 && !linked(a, b) && rng.chance(chance)) add(a, b, type(a, b), 2); };
  const walkT = () => rng.weighted(s.walk_links ?? { wide: 3, narrow: 1.5, bush: 0.8, detour: 0.3 });
  const anyT = () => rng.weighted(s.links ?? { wide: 3, narrow: 1.5, bush: 0.8, dash: 1, crystal: 0.5, plug: 0.5, detour: 0.4 });
  const gapT = () => rng.weighted(s.gap_links ?? { dash: 2, crystal: 1 });
  const hubId = hub ? nodes.indexOf(hub) : -1;
  const ctx = { nodes, links, home, hub, hubId, ids, pos, nd, mir, self, isA, M };
  if (bd) bd.link(ctx, make, ok, links, join);
  if (lay === 'web' || lay === 'backdoor') {
    kruskal(pairs(), anyT);
    loops(pairs(), s.loops, anyT);
  } else if (lay === 'tree' || lay === 'shortcut') {
    if (lay === 'shortcut') {
      let prev = 0;
      for (const id of pin) { if (!add(prev, id, rng.weighted({ wide: 2, narrow: 1.5, bush: 0.5 }), 4)) throw new GenFail('hairpin broken'); prev = id; }
    }
    kruskal(pairs((a, b) => isA(b)), walkT);
    for (const [a, b] of pairs((a, b) => hub ? b === hubId : b === mir(a))) if (add(a, b, walkT())) break;
    if (lay === 'shortcut' && !add(0, pin.at(-1), gapT(), 4)) throw new GenFail('no shortcut gap');
  } else if (lay === 'split') {
    kruskal(pairs((a, b) => isA(b)), walkT);
    loops(pairs((a, b) => isA(b)), s.loops * 0.5, walkT);
    if (hub) for (const [a, b] of pairs((a, b) => b === hubId)) if (add(a, b, gapT())) break;
    let n = rng.int(hub ? 0 : 1, 2);
    for (const [a, b] of pairs((a, b) => !isA(b))) if (n > 0 && !linked(a, b) && rng.chance(0.6) && add(a, b, gapT())) n--;
  } else if (lay === 'island') {
    kruskal(pairs(), (a, b) => a === 0 || b === mir(0) ? gapT() : anyT());
    loops(pairs(), s.loops * 0.6, (a, b) => a === 0 || b === mir(0) ? gapT() : anyT());
  } else if (lay === 'toll') {
    // The toll road is drawn but left out of the union, so the rest of the graph must reach the hub
    // another way: a detour of its own, or round through the other rooms.
    const T = hubId;
    for (let t = 0; t < 6 && !ctx.toll; t++) { const L = make(0, T, 'toll'); if (ok(L)) links.push(ctx.toll = L); }
    if (!ctx.toll) throw new GenFail('no toll road');
    if (rng.chance(0.6)) add(0, T, 'detour', 8);
    ctx.T = T;
    kruskal(pairs((a, b) => !(a === 0 && b === T)), walkT);
    loops(pairs((a, b) => !(a === 0 && b === T)), s.loops * 0.4, walkT);
  }
  for (const id of ids) if (find(id) !== find(0)) throw new GenFail('region graph not connected');
  if (lay === 'web') {
    const E = links.reduce((n, L) => n + (L.self ? 1 : 2), 0);
    if (E - ids.length + 1 < Math.max(2, ids.length / 4)) throw new GenFail('too few cycles');
  }
  // ---- draw
  for (const n of nodes) drawRoom(g, rng, n);
  for (const L of links) stroke(g, L.pts, L.w, GROUND, [WALL, HOLE]);
  if (style === 'cave' && voidKind === HOLE && rng.chance(0.6)) rims(g, rng, [HOLE], rng.uniform(0.12, 0.3));
  for (const n of nodes) if (n.r >= 5 && !n.pocket && !n.cramp) scatterPrefabs(g, rng, rng.int(0, 2), { gap: 4, spawnGap: 4, where: (x, y) => dist([x, y], n.p) < n.r - 3, kinds: { [WALL]: 3, [BUSH]: 1, [HOLE]: voidKind === HOLE ? 0.5 : 0 } });
  clumps(g, rng, rng.int(0, 4), [3, 7], { where: (x, y) => nodes.some(n => !n.pocket && inRoom(n, [x, y], -1)) });
  const rooms = nodes;
  for (const L of links) {
    if (L.w === 1 && L.core && L.type !== 'plug') for (const p of resample(L.pts, L.ta, L.tb, 0.5)) noCamp(g, Math.round(p[0]), Math.round(p[1]));
    if (!FEATURED.has(L.type)) continue;
    const t = midT(rng, L);
    if (t === null) throw new GenFail('no room for a link feature');
    let cut = [];
    if (L.type === 'dash') { cut = band(g, L, t, 1, HOLE, false, rooms); raise(g, 'dash'); }
    else if (L.type === 'crystal') {
      cut = rng.chance(voidKind === HOLE ? 0.5 : 0.35) ? band(g, L, t, 2, HOLE, false, rooms) : band(g, L, t, rng.int(1, 2), WALL, true, rooms);
      raise(g, 'teleport');
    } else if (L.type === 'bush') band(g, L, t, L.w === 1 ? 3 : rng.int(2, 3), BUSH, false, rooms);
    else if (L.type === 'plug') {
      const cells = band(g, L, t, 1, null, false, rooms);
      const xs = cells.map(([x, y]) => x + y).sort((p, q) => p - q);
      if (!cells.length || cells.length > 4 || xs.some((v, k) => k && v !== xs[k - 1] + 1) || cells.some(([x, y]) => !farFromMirror(g, x, y))) continue;
      const boss = rng.weighted({ elk: 2, wolf: 1.5, golem: 0.8 });
      for (const [x, y] of cells) put(g, x, y, GROUND);
      g.sites.push({ cells: cells.map(([x, y], k) => [k ? rng.weighted({ [boss]: 1, wolf: 1, gold_cluster: 0.5 }) : boss, x, y]), gate: true });
      g.gated = true;
    } else if (L.type === 'toll') {
      // An alcove beside the road holding the toll camp.
      const { p, d } = along(L.pts, t), side = rng.chance(0.5) ? 1 : -1, nrm = [-d[1] * side, d[0] * side], q = [p[0] + nrm[0] * (L.w / 2 + 2.6), p[1] + nrm[1] * (L.w / 2 + 2.6)];
      disc(g, q, 2.3, GROUND);
      for (const c of resample(L.pts, L.ta, L.tb, 0.5)) for (let j = -1; j <= 1; j++) for (let i = -1; i <= 1; i++) if (polyPt(L.pts, [Math.round(c[0]) + i, Math.round(c[1]) + j]) <= L.w / 2 + 0.6) noCamp(g, Math.round(c[0]) + i, Math.round(c[1]) + j);
      const flip = rng.chance(0.5), at = q.map(Math.round), cells = rng.choice(TOLLS).map(([type, dx, dy]) => [type, at[0] + (flip ? dy : dx), at[1] + (flip ? dx : dy)]);
      if (cells.some(([, x, y]) => !g.in(x, y) || g.get(x, y) !== GROUND || g.noCamp.has(y * g.W + x))) throw new GenFail('toll camp does not fit');
      ctx.tollCells = cells;
      g.sites.push({ cells, required: true });
    }
    for (const [x, y] of cut) for (let j = -2; j <= 2; j++) for (let i = -2; i <= 2; i++) noCamp(g, x + i, y + j);
  }
  // Body-blocking extras: altar niches and camp alcoves.
  const altarsAt = [], spots = rng.shuffle(nodes.filter(n => !n.pocket && !n.self && !n.cramp && n !== home));
  for (let k = 0, want = s.niches ?? 0; k < want && spots.length; k++) { const a = niche(g, rng, spots[k % spots.length], rng.int(1, 2)); if (a) altarsAt.push(a); }
  for (let k = 0, want = s.alcoves ?? 0, made = 0; k < want * 2 && made < want && spots.length; k++) {
    const cells = alcove(g, rng, spots[(k + 1) % spots.length], rng.int(1, 3));
    if (cells) { g.sites.push({ cells, required: made === 0 }); made++; }
  }
  if (home.cramp) crampSpawn(g, rng);
  else clearSpawn(g, 0);
  verify(g, rng, s, ctx);
  graphSites(g, rng, s, ctx, altarsAt.length);
}

// The spawn's one-tile ring, partly blocked: each ring tile turns wall or hole unless the spawn
// would lose its way out.
function crampSpawn(g, rng) {
  clearSpawn(g, 0);
  const sp = g.spawn, ring = [], share = rng.uniform(0.25, 0.55), kind = rng.chance(0.7) ? WALL : HOLE;
  for (let y = sp.y - 1; y <= sp.y + sp.h; y++) for (let x = sp.x - 1; x <= sp.x + sp.w; x++) if (g.in(x, y) && rectDist(sp, x, y) === 1 && walkable(g.get(x, y))) ring.push([x, y]);
  const reach = () => { const d = field(g, 0, 0); return d.reduce((n, v) => n + (v >= 0), 0); }, base = reach();
  for (const [x, y] of rng.shuffle(ring)) {
    if (!rng.chance(share)) continue;
    const was = g.get(x, y);
    put(g, x, y, kind);
    if (reach() < base - 2 * (sp.w + sp.h) - 8) put(g, x, y, was);
  }
}

// What each layout promises, checked on the drawn map.
function verify(g, rng, s, ctx) {
  const { nodes, links, home, pos, nd, ids, mir, M } = ctx, lay = s.layout, walk = field(g, 0, 0);
  const tilesOf = id => { const n = nd(id); return roomTiles(g, id < M ? n : n.x0 !== undefined ? { ...n, ...mirRect(g, n) } : { ...n, p: pos(id) }, false); };
  if (lay === 'tree') {
    // Every link is a bridge: blocking its middle separates its ends (camps ignored, spawns open).
    const pass = g.walkable(), starts = g.spawnTiles(0);
    for (const L of links) {
      if (!L.core) continue;
      for (const Q of [L.pts, L.self ? null : L.pts.map(p => mirrorPt(g, p))]) {
        if (!Q) continue;
        const LL = { ...L, pts: Q }, cut = band(g, LL, (L.ta + L.tb) / 2, 1, null, false, nodes).map(t => idxOf(g, t));
        if (!cut.length) continue;
        const p2 = pass.slice();
        for (const i of cut) p2[i] = 0;
        const d = g.bfs(starts, p2), a = Q === L.pts ? L.a : mir(L.a), b = Q === L.pts ? L.b : mir(L.b);
        if (nearest(d, tilesOf(a)) >= 0 && nearest(d, tilesOf(b)) >= 0) throw new GenFail('tree has a cycle');
      }
    }
  } else if (lay === 'split') {
    if (g.spawnTiles(1).some(i => g.reachNear(walk, i % g.W, Math.floor(i / g.W)) >= 0)) throw new GenFail('halves walk-connected');
  } else if (lay === 'island') {
    for (const id of ids) if (id !== 0 && nearest(walk, tilesOf(id)) >= 0) throw new GenFail('island walk-connected');
  } else if (lay === 'shortcut') {
    // The walk to some objective is at least min_ratio times its cost with a dash or crystal.
    const lv = g.access === 'teleport' ? 2 : 1, jump = field(g, 0, lv), targets = [[-1, g.spawnTiles(1).flatMap(i => [i - 1, i + 1, i - g.W, i + g.W]).filter(i => i >= 0 && i < g.t.length && !g.spawnTiles(1).includes(i))], ...ids.filter(id => id !== 0 && !ctx.self(id)).map(id => [id, tilesOf(id).filter(i => dist([i % g.W, Math.floor(i / g.W)], pos(id)) <= 2.5)])];
    let best = null;
    for (const [id, tiles] of targets) {
      const w = nearest(walk, tiles), j = nearest(jump, tiles);
      if (w > 0 && j > 0 && (!best || w / j > best.r)) best = { id, r: w / j, w, j };
    }
    if (!best || best.r < (s.min_ratio ?? 3.2)) throw new GenFail(`shortcut ratio ${best ? best.r.toFixed(2) : 0}`);
    ctx.target = best.id;
  } else if (lay === 'toll') {
    // Safe: out of every toll camp's range (its own and its mirror).
    const block = new Uint8Array(g.t.length);
    for (const [type, cx, cy] of ctx.tollCells) for (const [px, py] of [[cx, cy], g.mirrorXY(cx, cy)]) {
      const r = REACH[type] ?? 0;
      for (let y = py - r; y <= py + r; y++) for (let x = px - r; x <= px + r; x++) if (g.in(x, y)) block[y * g.W + x] = 1;
    }
    const T = tilesOf(ctx.T).filter(i => dist([i % g.W, Math.floor(i / g.W)], pos(ctx.T)) <= 4), short = nearest(walk, T), safe = nearest(field(g, 0, 0, block), T);
    if (short < 0 || safe < 0 || safe < (s.min_ratio ?? 1.5) * short) throw new GenFail(`toll detour ${safe}/${short}`);
  } else if (lay === 'backdoor') ctx.bd.check(walk);
}

const mirRect = (g, n) => { const [ax, ay] = g.mirrorXY(n.x0, n.y0), [bx, by] = g.mirrorXY(n.x1, n.y1); return { x0: Math.min(ax, bx), x1: Math.max(ax, bx), y0: Math.min(ay, by), y1: Math.max(ay, by), p: mirrorPt(g, n.p) }; };

// Toll camps: a boss beside the road, with clusters or wolves.
const TOLLS = [[['golem', 0, 0], ['gem_cluster', 1, 0], ['gem_cluster', -1, 0]], [['golem', 0, 0], ['golem', 1, 0]], [['elk', 0, 0], ['elk', 1, 0], ['gem_cluster', 0, 1]],
  [['golem', 0, 0], ['wolf', 1, 0], ['wolf', -1, 0]], [['golem', 0, 0], ['gem_cluster', 0, 1]], [['monolith', 0, 0]]];
const REACH = { wolf: 3, elk: 4, golem: 4, monolith: 5 };

const goldTpl = rng => rng.weighted({ gold: 2, wolf: 2, elk_gold: 1.5, wolf_pair: 1, gold_row: 0.5 });

function graphSites(g, rng, s, ctx, niches) {
  const { nodes, home, hub } = ctx, S = spawnCentre(g), S2 = mirrorPt(g, S), ratio = p => dist(p, S) / Math.max(1, dist(p, S) + dist(p, S2));
  const fieldNodes = nodes.filter(n => n.role === 'field' && !n.pocket);
  const needGold = g.access !== 'walk';
  const target = ctx.target >= 0 ? nodes[ctx.target % ctx.M] : null;
  const farm = home.big ? home : fieldNodes.filter(n => n !== target).reduce((b, n) => !b || dist(n.p, S) < dist(b.p, S) ? n : b, null) ?? home;
  site(g, farm.p, siteR(farm), needGold ? goldTpl(rng) : tier(rng, s, 'home'), { required: true, home: true });
  const used = new Set([farm]);
  const special = n => { used.add(n); return n; };
  if (ctx.pocket) site(g, special(ctx.pocket).p, siteR(ctx.pocket), rng.chance(0.3) ? { altar: true } : tier(rng, s, rng.chance(0.6) ? 'treasure' : 'mid'), { required: true });
  if (target && !target.self && !used.has(target)) {
    // The shortcut's far end holds the prize (stored on team A's side; the mirror is B's).
    const n = special(target);
    site(g, n.p, Math.min(siteR(n), 3), rng.chance(0.3) ? { altar: true } : tier(rng, s, 'treasure'), { required: true });
  }
  let altars = niches;
  if (hub && !used.has(hub)) {
    used.add(hub);
    const what = rng.weighted({ treasure: hub.r >= 4 ? 1.2 : 0, altar: 1, mid: 0.4 });
    if (what === 'treasure') g.sites.push({ shared: 'treasure', required: rng.chance(0.5) });
    else if (what === 'altar') { site(g, hub.p, siteR(hub), { altar: (g.sym === 'horizontal' ? g.W : g.sym === 'vertical' ? g.H : g.W * g.H) % 2 && rng.chance(0.6) ? 'self' : true }, { required: true }); altars++; }
    else site(g, hub.p, siteR(hub), tier(rng, s, 'mid'));
  }
  const rest = rng.shuffle(fieldNodes.filter(n => !used.has(n)));
  if (!altars || rng.chance(0.3)) {
    const n = rest.length ? rest.reduce((b, q) => Math.abs(ratio(q.p) - 0.45) < Math.abs(ratio(b.p) - 0.45) ? q : b) : home;
    site(g, n.p, siteR(n), { altar: true }, { required: !altars });
    used.add(n); altars++;
  }
  if (rng.chance(0.25)) site(g, home.p, siteR(home) + 2, { altar: true });
  let treasure = rng.chance(0.5);
  for (const n of rest) {
    if (used.has(n)) continue;
    const r = ratio(n.p);
    site(g, n.p, siteR(n), treasure && r > 0.3 ? tier(rng, s, 'treasure') : tier(rng, s, r < 0.3 ? 'home' : 'mid'));
    if (r > 0.3) treasure = false;
  }
}

// Shortcut layout: a hairpin of rooms out from home along one arm and back along a parallel one, its
// last room a few tiles from home (the gap a dash or crystal crosses). Returns the rooms in order.
function hairpin(g, rng, nodes, home, fits, style) {
  const m = Math.min(g.W, g.H), rmax = m * 0.06 + 1.5, C = centre(g);
  for (let tries = 0; tries < 40; tries++) {
    const off = rng.uniform(-0.9, 0.9), ang = Math.atan2(C[1] - home.p[1], C[0] - home.p[0]) + off, d1 = [Math.cos(ang), Math.sin(ang)];
    // The return arm on the side facing the map, mostly.
    const side = (off > 0 ? -1 : 1) * (rng.chance(0.85) ? 1 : -1), pp = [-d1[1] * side, d1[0] * side];
    const gap = rng.uniform(3, 6), wU = Math.max(home.R + gap + rmax, 2 * rmax + 7), La = m * rng.uniform(0.35, 0.65);
    const P = home.p, turn = [P[0] + d1[0] * La, P[1] + d1[1] * La], line = [P, turn, [turn[0] + pp[0] * wU, turn[1] + pp[1] * wU], [P[0] + pp[0] * wU, P[1] + pp[1] * wU]];
    const total = plen(line), step = 2 * rmax + 6, rooms = [];
    let okEnd = false;
    for (let d = step; d <= total + 0.01; d += step) {
      const last = d + step > total, t = last ? 1 : d / total, n = room(rng, style, along(line, t).p, m * rng.uniform(0.035, 0.06) + 1.5, { role: 'field' });
      const placed = [...nodes, ...rooms];
      const fine = inMap(g, n.p, 2) && onSideA(g, n.p) && dist(n.p, mirrorPt(g, n.p)) >= 2 * n.R + 5
        && placed.filter(q => q !== home).concat(placed.filter(q => !q.self).map(q => ({ p: mirrorPt(g, q.p), R: q.R }))).every(q => dist(n.p, q.p) >= n.R + q.R + 5)
        && (last ? dist(n.p, P) - n.R - home.R >= 2.5 : dist(n.p, P) >= n.R + home.R + 5);
      if (fine) rooms.push(n);
      if (last) { okEnd = fine; break; }
    }
    if (!okEnd || rooms.length < 3) continue;
    const base = nodes.length;
    nodes.push(...rooms);
    return rooms.map((_, k) => base + k);
  }
  throw new GenFail('no room for a hairpin');
}

// Backdoor: a pocket beside home behind a thin wall (one or two tiles: a crystal crosses), its only
// walking way in a corridor along the map's edge that opens in the enemy's half (under rotation) or
// at the symmetry axis, where it meets the enemy's own.
function backdoorPlan(g, rng, s, nodes, home, hub) {
  const { W, H } = g, t = rng.int(1, 2), w = rng.int(1, 2), q = w === 1 ? rng.int(0, 1) : 1;
  const len = rng.int(5, 8), dep = rng.int(3, 5), opts = [];
  if (home.x0 === 0 || home.x1 === W - 1) for (const up of [1, -1]) {
    const x0 = home.x0 === 0 ? 0 : W - dep, y0 = up > 0 ? home.y1 + 1 + t : home.y0 - t - len;
    opts.push(rectRoom(x0, y0, x0 + dep - 1, y0 + len - 1));
  }
  if (home.y0 === 0 || home.y1 === H - 1) for (const right of [1, -1]) {
    const y0 = home.y0 === 0 ? 0 : H - dep, x0 = right > 0 ? home.x1 + 1 + t : home.x0 - t - len;
    opts.push(rectRoom(x0, y0, x0 + len - 1, y0 + dep - 1));
  }
  const P = rng.shuffle(opts).find(n => n.x0 >= 0 && n.y0 >= 0 && n.x1 < W && n.y1 < H && dist(n.p, mirrorPt(g, n.p)) > 2 * n.R + 8 && (!hub || dist(n.p, hub.p) > n.R + hub.R + 5));
  if (!P) throw new GenFail('no pocket site');
  Object.assign(P, { role: 'pocket', pocket: true });
  // The edge loop at inset q, parametrised counter-clockwise from (q, q).
  const a = W - 1 - 2 * q, b = H - 1 - 2 * q, per = 2 * a + 2 * b, at = [0, a, a + b, 2 * a + b];
  const corner = [[q, q], [W - 1 - q, q], [W - 1 - q, H - 1 - q], [q, H - 1 - q]];
  const pt = u => { u = ((u % per) + per) % per; for (let k = 3; k >= 0; k--) if (u >= at[k]) return lerp(corner[k], corner[(k + 1) % 4], (u - at[k]) / (k % 2 ? b : a)); };
  const uOf = ([x, y]) => {
    const cx = Math.max(q, Math.min(W - 1 - q, x)), cy = Math.max(q, Math.min(H - 1 - q, y));
    return [[cx - q, Math.abs(y - q)], [a + cy - q, Math.abs(x - (W - 1 - q))], [a + b + (W - 1 - q - cx), Math.abs(y - (H - 1 - q))], [2 * a + b + (H - 1 - q - cy), Math.abs(x - q)]].reduce((p, c) => c[1] < p[1] ? c : p)[0];
  };
  const path = (u0, u1) => {
    const dir = Math.sign(u1 - u0), cs = [];
    for (let k = -2; k <= 2; k++) for (const c of at) { const v = c + k * per; if (dir > 0 ? v > u0 && v < u1 : v < u0 && v > u1) cs.push(v); }
    cs.sort((p, r) => dir * (p - r));
    return [pt(u0), ...cs.map(pt), pt(u1)];
  };
  const uP = uOf(P.p), uH = uOf(home.p), circ = v => ((v % per) + per + per / 2) % per - per / 2, dir = Math.sign(circ(uP - uH)) || 1;
  let corr, X = null, uE;
  if (g.sym === 'rotational') {
    const lo = per * 0.3, hi = per / 2 - Math.abs(circ(uP - uH)) - Math.max(home.x1 - home.x0, home.y1 - home.y0) / 2 - 6;
    if (hi < lo) throw new GenFail('no room for the backdoor corridor');
    uE = uP + dir * rng.uniform(lo, hi);
  } else {
    const selfs = g.sym === 'horizontal' ? [a / 2, a / 2 + per / 2] : [a + b / 2, a + b / 2 + per / 2];
    uE = uP + dir * Math.min(...selfs.map(v => (((dir * (v - uP)) % per) + per) % per));
    if (Math.abs(uE - uP) > per * 0.45) throw new GenFail('backdoor corridor too long');
    X = { ...room(rng, 'cave', pt(uE), rng.uniform(1.5, 2.5)), self: true, role: 'gate' };
    X.p = pt(uE);
  }
  corr = path(uP, uE);
  const mcorr = corr.map(p => mirrorPt(g, p));
  const clearOf = (n, gap) => [corr, mcorr].every(Q => Q.every(p => !inRoom(n, p, gap)));
  if (!clearOf(home, 3 + w / 2) || (hub && !clearOf(hub, 3 + w / 2))) throw new GenFail('backdoor corridor meets a room');
  nodes.push(P);
  if (X) nodes.push(X);
  const plan = {
    corr, w,
    link(ctx, make, ok, links, join) {
      ctx.pocket = P; ctx.bd = plan;
      const pid = nodes.indexOf(P);
      let end;
      if (X) end = nodes.indexOf(X);
      else {
        // Into the nearest room on the enemy's side.
        // Into the nearest room on the enemy's side, its home first if that is about as near.
        const E = corr.at(-1), far = id => dist(ctx.pos(id), E) * (id === ctx.M ? 0.6 : 1);
        const cands = ctx.ids.filter(id => id !== pid && id !== ctx.mir(pid) && (id >= ctx.M || ctx.self(id)) && !nodes[id % ctx.M].pocket).sort((p, r) => far(p) - far(r));
        for (const id of cands.slice(0, 5)) {
          const L = make(pid, id, 'corridor', [...corr, ctx.pos(id)]);
          L.w = L.cw = w;
          if (ok(L)) { end = id; links.push(L); break; }
        }
        if (end === undefined) throw new GenFail('backdoor corridor has no way in');
      }
      if (X) { const L = make(pid, end, 'corridor', corr); L.w = L.cw = w; links.push(L); }
      join(pid, end); join(ctx.mir(pid), ctx.mir(end));
      if (X && ctx.hub) { const L = make(end, ctx.hubId, 'wide'); if (ok(L)) { links.push(L); join(end, ctx.hubId); } }
      plan.ctx = ctx;
    },
    // Team A reaches its pocket on foot only through tiles at least as near team B, and by crystal
    // in at most half the walk.
    check(walk) {
      const dB = field(g, 1, 0), pocket = roomTiles(g, P, false), mine = new Set(pocket), block = new Uint8Array(g.t.length);
      for (let i = 0; i < g.t.length; i++) if (!mine.has(i) && (walk[i] < 0 || (dB[i] >= 0 && dB[i] <= walk[i]))) block[i] = 1;
      const w0 = nearest(walk, pocket), own = nearest(field(g, 0, 0, block), pocket), tele = nearest(field(g, 0, 2), pocket);
      if (w0 < 0 || own >= 0) throw new GenFail('pocket reachable from home ground');
      if (tele < 0 || 2 * tele > w0) throw new GenFail(`pocket crystal ${tele} vs walk ${w0}`);
    },
  };
  return plan;
}

// ---- spawn designers ---------------------------------------------------------------------------
// Field dressing for the open spawn designers: cover prefabs, bush clumps, hole ponds and wall
// ridges away from the spawns.
function dress(g, rng, keep) {
  const m = Math.min(g.W, g.H);
  for (let k = rng.int(0, 2); k > 0; k--) {
    const p = [rng.uniform(4, g.W - 5), rng.uniform(4, g.H - 5)], r = rng.uniform(1.5, m * 0.07 + 1.5);
    if (!keep(p, r + 3)) blob(g, rng, p, r, 0.15, rng.chance(0.7) ? HOLE : WALL, [GROUND]);
  }
  scatterPrefabs(g, rng, rng.int(Math.round(m / 12), Math.round(m / 5)), { gap: 5, spawnGap: 5, where: (x, y) => !keep([x, y], 4), kinds: { [WALL]: 3, [BUSH]: 1, [HOLE]: 0.6 } });
  clumps(g, rng, rng.int(2, 6), [3, 8], { where: (x, y) => !keep([x, y], 2) });
}

// Duel: spawns face each other across the symmetry axis 0-4 tiles apart, with open ground, a hole
// moat (ranged attacks reach across a gap of 2 or less), a wall or a line of camps between.
function duel(g, rng, s) {
  begin(g, GROUND);
  const F = frame(g, rng), { U, V, cu } = F;
  const [du, dv] = s.spawn_odd && rng.chance(0.35) ? oddDims(rng) : spawnDims(rng);
  const gaps = [0, 1, 2, 3, 4].filter(k => (U - k - 2 * du) % 2 === 0), gap = +rng.weighted(Object.fromEntries(gaps.map(k => [k, k ? 1 : 0.5])));
  const u0 = (U - gap - 2 * du) / 2;
  // Under rotation B's rows are V-v0-dv..V-1-v0: keep at least dv-2 of them facing A's.
  const v0 = F.rot ? rng.choice([...Array(V).keys()].filter(v => v + dv <= V && Math.min(v + dv - 1, V - 1 - v) - Math.max(v, V - v - dv) + 1 >= Math.max(1, dv - 2))) : Math.max(1, Math.min(V - dv - 1, rng.chance(0.6) ? Math.round((V - dv) / 2 + rng.uniform(-0.2, 0.2) * V) : rng.chance(0.5) ? rng.int(1, 3) : V - dv - rng.int(1, 3)));
  const vB = F.rot ? V - v0 - dv : v0, vlo = Math.min(v0, vB), vhi = Math.max(v0 + dv - 1, vB + dv - 1);
  const kind = gap ? rng.weighted(s.between ?? { moat: 3, camps: 2.5, open: 1, wall: 0.6 }) : 'open';
  const [sx, sy] = F.xy(u0, v0), spawnRect = F.alongX ? { x: sx, y: sy, w: du, h: dv } : { x: sx, y: sy, w: dv, h: du };
  const S = [sx + (spawnRect.w - 1) / 2, sy + (spawnRect.h - 1) / 2];
  // Keep features off the duel zone.
  const zone = (p, r) => Math.abs((F.alongX ? p[0] : p[1]) - cu) < du + gap / 2 + r && (F.alongX ? p[1] : p[0]) > vlo - r - 2 && (F.alongX ? p[1] : p[0]) < vhi + r + 2;
  dress(g, rng, (p, r) => zone(p, r + 2) || dist(p, S) < r + 6 || dist(p, mirrorPt(g, S)) < r + 6);
  // Optional flank walls running from the duel zone along the axis, so the halves meet further out.
  const ext = kind === 'moat' || kind === 'wall' ? rng.int(0, Math.round(V * 0.3)) : 0;
  for (let u = u0 + du; u < u0 + du + gap; u++) for (let v = Math.max(0, vlo - ext); v <= Math.min(V - 1, vhi + ext); v++) F.set(u, v, kind === 'moat' ? HOLE : kind === 'wall' ? WALL : GROUND);
  frameSpawn(g, F, u0, v0, du, dv);
  for (let u = u0 - 1; u <= u0 + du; u++) for (let v = v0 - 1; v <= v0 + dv; v++) if (u < u0 + du || kind === 'open') { const k = F.get(u, v); if (k === WALL || k === HOLE) F.set(u, v, GROUND); }
  const plan = new Set();
  if (kind === 'camps') {
    // The middle one or two columns of the gap, the spawns' height and a tile beyond.
    const us = gap % 2 ? [cu] : [cu - 0.5, cu + 0.5], e = rng.int(0, 1), cells = [], mid = Math.floor((vlo + vhi) / 2);
    const boss = rng.chance(0.35) ? rng.weighted({ elk: 2, golem: 0.5 }) : null;
    for (const u of us) for (let v = Math.max(0, vlo - e); v <= Math.min(V - 1, vhi + e); v++) {
      const [x, y] = F.xy(u, v);
      cells.push([boss && Math.abs(v - mid) < 1 ? boss : rng.weighted({ wolf: 3, gold_cluster: 1 }), x, y]);
    }
    for (const [, x, y] of cells) { put(g, x, y, GROUND); plan.add(y * g.W + x); }
    g.sites.push({ cells: canonical(g, cells), shared: true, required: true });
  }
  // No filler camps beside the spawns, only the planned line.
  for (let y = 0; y < g.H; y++) for (let x = 0; x < g.W; x++) if (rectDist(spawnRect, x, y) <= 4 && !plan.has(y * g.W + x)) noCamp(g, x, y);
  const back = F.xy(Math.max(2, u0 - rng.int(6, 10)), v0 + dv / 2);
  site(g, back, 5, tier(rng, s, 'home'), { required: true, home: true });
  const C = centre(g);
  for (let k = rng.int(2, 4); k > 0; k--) site(g, F.xy(rng.uniform(2, cu - 3), rng.uniform(2, V - 3)), 5, tier(rng, s, rng.chance(0.25) ? 'treasure' : 'mid'));
  // A contested altar out along the axis, away from the duel, and sometimes a home one.
  const far = vlo > V - 1 - vhi ? rng.uniform(2, vlo - 6) : rng.uniform(vhi + 6, V - 3);
  site(g, F.xy(cu - rng.uniform(0, 4), Math.max(2, Math.min(V - 3, far))), 5, { altar: rng.chance(0.4) ? 'self' : true }, { required: true });
  if (rng.chance(0.4)) site(g, F.xy(rng.uniform(3, cu * 0.6), rng.uniform(3, V - 4)), 6, { altar: true });
}

// Gatehouse: a thick wall along the symmetry axis; the only way through is a corridor that runs
// through each spawn ('through': the corridor is the spawn's width, so the enemy can never pass and
// each side's backyard is its own) or beside it ('beside': a one- or two-wide lane past the spawn),
// meeting in a small arena on the axis.
function gatehouse(g, rng, s) {
  begin(g, GROUND);
  const F = frame(g, rng), { U, V, cu } = F;
  const mode = rng.weighted(s.gate_mode ?? { through: 1, beside: 1 });
  let [du, dv] = s.spawn_odd && rng.chance(0.5) ? oddDims(rng) : spawnDims(rng);
  if (dv > du && rng.chance(0.7)) [du, dv] = [dv, du];
  let cw = mode === 'through' ? dv : dv + rng.int(1, 2);
  // Under rotation the corridor must be its own mirror: an even margin either side.
  if (F.rot && (V - cw) % 2) { if (mode === 'through' && (V - du) % 2 === 0 && du <= 5) { [du, dv] = [dv, du]; cw = dv; } else if (mode === 'through') throw new GenFail('corridor parity'); else cw++; }
  const v0 = F.rot ? (V - cw) / 2 : rng.int(Math.round(V * 0.25), Math.round(V * 0.75) - cw), vc = v0 + (cw - 1) / 2;
  const ar = rng.int(2, 4), av = Math.max(Math.ceil(cw / 2) + 1, rng.int(2, 5)), lead = rng.int(1, 3), bw = Math.ceil(ar + lead + du + rng.int(1, 5));
  if (cu - bw < Math.max(8, U * 0.22)) throw new GenFail('no room for backyards');
  for (let u = Math.floor(cu - bw); u <= cu; u++) for (let v = 0; v < V; v++) F.set(u, v, WALL);
  for (let u = Math.floor(cu - bw) - 1; u <= cu; u++) for (let v = v0; v < v0 + cw; v++) F.set(u, v, GROUND);
  for (let u = Math.ceil(cu - ar); u <= cu; u++) for (let v = Math.round(vc - av); v <= Math.round(vc + av); v++) F.set(u, v, GROUND);
  const su = Math.ceil(cu - ar) - lead - du, sv = mode === 'through' || rng.chance(0.5) ? v0 : v0 + cw - dv;
  // A postern: a dead end from the arena towards the backyard, two walls short (a crystal raid). The
  // validator wants every objective within team A's reach, so a sealed ('through') backyard has one.
  if (mode === 'through' || rng.chance(s.postern ?? 0.35)) {
    raise(g, 'teleport');
    const pv = rng.chance(0.5) ? Math.round(vc - av) : Math.round(vc + av), out = pv < vc ? -1 : 1;
    const open = (u, v) => { F.set(u, v, GROUND); noCamp(g, ...F.xy(u, v)); };
    for (let v = pv; Math.abs(v - pv) < 3; v += out) open(Math.ceil(cu - ar), v);
    const pu = Math.floor(cu - bw) + 2, row = pv + 2 * out;
    if (row >= 1 && row <= V - 2) for (let u = pu; u <= Math.ceil(cu - ar); u++) open(u, row);
  }
  const wing = Math.floor(cu - bw) - 1;
  frameSpawn(g, F, su, sv, du, dv);
  const S = spawnCentre(g);
  dress(g, rng, (p, r) => (F.alongX ? p[0] : p[1]) > wing - r - 2 && (F.alongX ? p[0] : p[1]) < U - wing + r + 1 || dist(p, S) < r + 4);
  // The corridor and lane stay clear of camps.
  for (let u = Math.floor(cu - bw) - 2; u < Math.ceil(cu - ar); u++) for (let v = v0 - 1; v <= v0 + cw; v++) { const [x, y] = F.xy(u, v); noCamp(g, x, y); }
  // The arena's prize: a self-mirrored camp block or altar on the axis.
  const C = F.xy(cu, vc), prize = rng.weighted({ camps: 1.2, altar: 1 });
  if (prize === 'camps') {
    const us = U % 2 ? [cu] : [cu - 0.5, cu + 0.5], cells = [], h = rng.int(0, 1), boss = rng.weighted({ elk: 2, golem: 1, gem_cluster: 1 });
    for (const u of us) for (let v = Math.round(vc - h); v <= Math.round(vc + h); v++) { const [x, y] = F.xy(u, v); cells.push([v === Math.round(vc) ? boss : rng.weighted({ gem_cluster: 2, gold_cluster: 1 }), x, y]); }
    g.sites.push({ cells: canonical(g, cells), shared: true, required: false });
  }
  site(g, F.xy(cu - ar + 0.5, vc), Math.max(av, ar) + 1, { altar: prize === 'altar' && U % 2 && rng.chance(0.6) ? 'self' : true }, { required: true });
  const yard = () => F.xy(rng.uniform(2, wing - 3), rng.uniform(2, V - 3));
  site(g, F.xy(Math.max(2, wing - rng.int(4, 8)), vc + rng.uniform(-6, 6)), 6, tier(rng, s, 'home'), { required: true, home: true });
  for (let k = rng.int(2, 4); k > 0; k--) site(g, yard(), 6, tier(rng, s, rng.chance(0.3) ? 'treasure' : 'mid'));
  if (rng.chance(0.3)) site(g, yard(), 6, { altar: true });
}

// Capital: both spawns near the centre inside a walled plaza with gates; the camps and altars are
// out in the corners and along the edges.
function capital(g, rng, s) {
  begin(g, GROUND);
  const F = frame(g, rng), { U, V, cu } = F;
  const [du, dv] = spawnDims(rng), gap0 = rng.int(4, 14), gap = gap0 + ((U - gap0 - 2 * du) % 2 + 2) % 2;
  const u0 = (U - gap - 2 * du) / 2, v0 = F.rot ? Math.floor((V - dv) / 2) + rng.int(-1, 1) : Math.round((V - dv) / 2 + rng.int(-3, 3));
  if (u0 < U * 0.22) throw new GenFail('spawns not central');
  // The plaza: a wall ring (one or two thick) round both spawns, gated on each side.
  const pu = rng.int(3, 6), pv = rng.int(3, 6), t = rng.int(1, 2), u1 = u0 - pu, v1 = Math.min(v0, F.rot ? V - v0 - dv : v0) - pv, v2 = V - 1 - v1;
  const ringKind = rng.chance(0.75) ? WALL : HOLE;
  if (u1 < 4 || v1 < 4) throw new GenFail('plaza too big');
  for (let u = u1; u <= cu; u++) for (let v = v1; v <= v2; v++) {
    const ring = (u < u1 + t) || v < v1 + t || v > v2 - t;
    if (ring) F.set(u, v, ringKind);
  }
  // Gates: on the back wall (towards A's edge) and the long sides, each two or three wide.
  const gates = [['back', rng.uniform(0.2, 0.8)], ...(rng.chance(0.7) ? [['side', rng.uniform(0.2, 0.9)]] : []), ...(rng.chance(0.5) || !F.rot ? [['far', rng.uniform(0.2, 0.9)]] : [])];
  for (const [where, f] of gates) {
    const gw = rng.int(2, 3);
    if (where === 'back') { const v = Math.round(v1 + t + f * (v2 - v1 - 2 * t - gw)); for (let k = 0; k < gw; k++) for (let a = 0; a < t; a++) F.set(u1 + a, v + k, GROUND); }
    else { const u = Math.round(u1 + t + f * (cu - u1 - t - gw)); for (let k = 0; k < gw; k++) for (let a = 0; a < t; a++) F.set(u + k, where === 'side' ? v1 + a : v2 - a, GROUND); }
  }
  frameSpawn(g, F, u0, v0, du, dv);
  const S = spawnCentre(g), inPlaza = ([x, y]) => { const [u, v] = F.alongX ? [x, y] : [y, x], mu = Math.min(u, U - 1 - u); return mu >= u1 - 1 && v >= v1 - 1 && v <= v2 + 1; };
  for (let y = 0; y < g.H; y++) for (let x = 0; x < g.W; x++) if (inPlaza([x, y])) noCamp(g, x, y);
  if (rng.chance(0.6)) scatterPrefabs(g, rng, rng.int(1, 2), { gap: 3, spawnGap: 3, where: (x, y) => inPlaza([x, y]) && dist([x, y], S) > 3, names: ['pillar', 'post', 'bar', 'copse'] });
  dress(g, rng, p => inPlaza(p) || dist(p, S) < 6);
  // Corner keeps: an L of wall (or hedge) round each of A's corners, holding a farm or treasure.
  const corners = [[0, 0], [0, V - 1]];
  rng.shuffle(corners).forEach(([cu0, cv0], k) => {
    const sz = rng.int(6, Math.max(7, Math.round(Math.min(u1, V / 2) * 0.7))), du1 = 1, dvv = cv0 ? -1 : 1, kind = rng.weighted({ [WALL]: 2, [BUSH]: 1, 0: 1 }) | 0;
    if (kind) {
      for (let a = 0; a < sz; a++) { if (a < sz - 2 || rng.chance(0.5)) F.set(cu0 + sz, cv0 + dvv * a, kind); F.set(cu0 + a, cv0 + dvv * sz, kind); }
      F.set(cu0 + sz, cv0 + dvv * sz, kind);
      const open = rng.int(1, sz - 3);
      for (let a = 0; a < 2; a++) F.set(cu0 + sz, cv0 + dvv * (open + a), GROUND);
    }
    const c = F.xy(cu0 + sz / 2, cv0 + dvv * sz / 2);
    site(g, c, sz / 2 + 0.5, tier(rng, s, k ? 'mid' : 'treasure'), { required: true });
    if (k === 0 && rng.chance(0.5)) site(g, c, sz / 2 + 1, { altar: true }, { required: false });
  });
  // Altars along the edges: on the axis (contested) or on team A's long edge.
  const edgeV = rng.chance(0.5) ? rng.uniform(1, 4) : V - 1 - rng.uniform(1, 4);
  site(g, F.xy(rng.chance(0.5) ? cu : rng.uniform(2, u1 - 2), edgeV), 6, { altar: rng.chance(0.4) ? 'self' : true }, { required: true });
  for (let k = rng.int(1, 3); k > 0; k--) site(g, F.xy(rng.uniform(2, u1 - 3), rng.uniform(2, V - 3)), 5, tier(rng, s, 'mid'));
  site(g, F.xy(rng.uniform(2, Math.max(3, u1 - 4)), rng.chance(0.5) ? rng.uniform(v1 - 3, v1) : rng.uniform(v2, v2 + 3)), 5, tier(rng, s, 'home'), { home: true });
}

export const DESIGNS = { topograph, 'topo-duel': duel, 'topo-gatehouse': gatehouse, 'topo-capital': capital };

// altars: 0, as placeAltars may put an altar on a site's camp (its free() ignores camps); every designer here places its own.
const designed = (doc, design, spec = {}) => ({ doc, design, designed: true, altars: 0, ...spec });
const sizes = { size: [30, 100], aspect: { square: 3, wide: 1.5 } };

export const PRESETS = {
  'topo-web': designed('Rooms in rock or a hole sea joined by a cycle-rich web of typed links: wide and 1-wide walks, bush curtains, dash and crystal gaps, camp plugs, detours', 'topograph',
    { layout: 'web', ...sizes, style: { cave: 1, built: 1 }, void_kind: { hole: 1, wall: 1.5 }, hub: 0.5, loops: [0.55, 0.9], groups: [2, 6] }),
  'topo-tree': designed('Rooms joined as a tree: exactly one walking route between any two rooms (no loops to flank by)', 'topograph',
    { layout: 'tree', ...sizes, style: { cave: 1, built: 1 }, void_kind: { hole: 1, wall: 2 }, hub: 0.4, groups: [2, 6] }),
  'topo-split': designed('Split world: the halves are not walk-connected and meet only across dash or crystal gaps', 'topograph',
    { layout: 'split', ...sizes, style: { cave: 1.5, built: 1 }, void_kind: { hole: 3, wall: 1 }, hub: 0.4, loops: [0.2, 0.6], groups: [2, 6], min_reach: 0.05 }),
  'topo-island': designed('Spawn island: home holds on-foot gold and is left only by dash or crystal', 'topograph',
    { layout: 'island', ...sizes, style: { cave: 2, built: 1 }, void_kind: { hole: 3, wall: 1 }, hub: 0.4, loops: [0.2, 0.6], groups: [2, 6], min_reach: 0.02 }),
  'topo-backdoor': designed('Backdoor: a pocket of your own camps (or an altar) behind a thin wall from home, a crystal away, but on foot only through enemy or contested ground', 'topograph',
    { layout: 'backdoor', ...sizes, symmetry: { rotational: 3, horizontal: 1, vertical: 1 }, style: { cave: 1, built: 1.5 }, void_kind: 'wall', spawn_where: { corner: 3, edge: 1 }, hub: 0.6, loops: [0.3, 0.7], groups: [2, 6] }),
  'topo-toll': designed('Toll road: a short road to the centre past a big camp in an alcove, or a long safe detour', 'topograph',
    { layout: 'toll', ...sizes, style: { cave: 1.5, built: 1 }, void_kind: { hole: 1, wall: 2 }, hub: 1, loops: [0.2, 0.5], groups: [2, 6] }),
  'topo-shortcut': designed('Shortcut: a long walk through a tree of rooms that a dash or crystal gap cuts 3x or more', 'topograph',
    { layout: 'shortcut', ...sizes, style: { cave: 1, built: 1 }, void_kind: { hole: 1, wall: 1.5 }, hub: 0.3, big_home: 0, walk_links: { wide: 2, narrow: 1.5, detour: 1, bush: 0.5 }, groups: [2, 6], spawn_where: { corner: 2, edge: 1.5, inset: 1 } }),
  'topo-necks': designed('Body-blocking: 1-wide corridors and spawn exits, altars with one or two walkable tiles beside them, camps captured through a 1-wide neck', 'topograph',
    { layout: { web: 2, tree: 1 }, size: [30, 90], aspect: { square: 3, wide: 1.5 }, style: { built: 3, cave: 1 }, void_kind: { wall: 3, hole: 1 }, hub: 0.4, loops: [0.4, 0.8], narrow: true,
      links: { narrow: 5, wide: 1, plug: 0.8, bush: 0.6, dash: 0.3 }, walk_links: { narrow: 5, wide: 1, bush: 0.6 }, niches: [1, 2], alcoves: [1, 3], max_w: 2, groups: [1, 4] }),
  'topo-odd-spawn': designed('Odd spawn rectangles (1x9, 2x6, 3x5 and others of 9-16 tiles) in cramped, partly blocked surrounds', 'topograph',
    { layout: { web: 3, tree: 1 }, ...sizes, style: { cave: 1, built: 1 }, void_kind: { hole: 1, wall: 2 }, spawn_odd: true, cramp: 0.65, hub: 0.4, loops: [0.4, 0.8], groups: [2, 6] }),
  'topo-duel': designed('Spawns face each other 0-4 tiles apart across open ground, a hole moat, a wall or a line of camps', 'topo-duel',
    { size: [30, 100], aspect: { square: 3, wide: 1.5 }, spawn_min_abs: 0, camp_spawn_gap: 1, spawn_reach_gap: -3, spawn_odd: true, groups: [2, 6] }),
  'topo-gatehouse': designed('The only route between the halves runs through (or beside) each spawn, which enemies cannot enter; a small arena on the axis between', 'topo-gatehouse',
    { size: [40, 100], aspect: { square: 2, wide: 2 }, spawn_min_abs: 0, spawn_reach_gap: -2, camp_spawn_gap: 2, spawn_odd: true, groups: [2, 6] }),
  'topo-capital': designed('Spawns near the centre in a gated plaza; camps and altars out in the corners and along the edges', 'topo-capital',
    { size: [36, 100], aspect: { square: 3, wide: 1 }, spawn_min_abs: 0, groups: [1, 3] }),
};

export const CAMP_MODES = {}, TEMPLATES = {};
