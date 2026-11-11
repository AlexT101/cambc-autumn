import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { fork } from 'node:child_process';
import { clumps, scatterPrefabs } from './design.mjs';
import { ALTAR, BUSH, GROUND, Grid, HOLE, LEVELS, N4, WALL, makeRng } from './grid.mjs';
import { BANDS, CALIB, GenFail, PICKS_BY_AREA, PRESETS, TEMPLATES, candidates, connect, familyOf, gaps, generate, metrics, naturalAccess, quirkTiles, sideGroups, spawnFields, stillConnected, tidy, tryGroup, validate } from './generate.mjs';
import { MapError, createEngine } from './wasm.mjs';

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..');

// The stress plan, and the stored pool in maps/gen: [preset, count] or [{ mutate: 'random' }, count]. Each entry is
// oversampled and the most mutually different candidates kept; `suite --mix varied` reweighs the counts per seed. About a sixth is ladder-like (presets close to the ladder, and
// ladder maps under random edits), a quarter designed scenarios (design.mjs), a quarter exotic
// shapes, interiors and economies, and a third the quirks, topology and scenario families.
const PLAN = [
  // Ladder-like.
  ['classic', 8], ['small-brawl', 2], ['maze', 2], ['caves', 2], ['lanes', 1], ['lakes', 2], ['jungle', 2], ['monolith', 3], ['rows', 1],
  ['altar-rich', 2], ['altar-poor', 2], ['contested-centre', 2], ['tiny', 1], ['huge', 2], ['random', 1], ['monolith-only', 2], ['shared-gems', 2], ['vaults', 2],
  // Ladder maps under random edits (the map and the edits both drawn from the seed).
  [{ mutate: 'random' }, 22],
  // Designed scenarios.
  ['atoll', 7], ['archipelago', 6], ['rivers', 7], ['fortress', 6], ['gatekeeper', 6], ['dungeon', 6], ['three-lane', 5], ['arena', 7],
  ['farmland', 5], ['continent', 6], ['hedges', 5],
  // Exotic playable-area shapes.
  ['round', 2], ['star', 2], ['donut', 3], ['cross', 2], ['hourglass', 2], ['band', 1], ['chambers', 3], ['blob', 2],
  // Exotic interiors.
  ['labyrinth', 3], ['spiral', 1], ['pillars', 2], ['cells', 2], ['diagonals', 1], ['tunnels', 2], ['city', 3], ['serpentine', 2], ['open-field', 1], ['long-thin', 2],
  // Exotic spawn distances and economies.
  ['close-spawns', 2], ['far-spawns', 2], ['golem-heavy', 2], ['gem-centre', 2], ['huge-shared', 2], ['tiny-groups', 1], ['sparse-camps', 2], ['dense-camps', 2],
  ['monsters-only', 1], ['clusters-only', 1], ['gem-drought', 2], ['gem-flood', 1], ['gold-flood', 1],
  // Relaxed constraints (generate.mjs): composed groups; every ladder quirk at once.
  ['big-groups', 4], ['wild', 7],
  // Topology and spawn extremes (topology.mjs).
  ['topo-web', 3], ['topo-tree', 2], ['topo-split', 3], ['topo-island', 2], ['topo-backdoor', 3], ['topo-toll', 2], ['topo-shortcut', 3], ['topo-necks', 3],
  ['topo-odd-spawn', 2], ['topo-duel', 3], ['topo-gatehouse', 2], ['topo-capital', 2],
  // Vision, mobility and economy layouts (scenarios.mjs).
  ['hole-maze', 3], ['dash-lattice', 3], ['wall-lattice', 2], ['leaky-diagonals', 2], ['fog-field', 3], ['shrouded-altars', 2], ['moated-altars', 2], ['mega-groups', 3],
  ['altar-clusters', 2], ['fuel-stress', 1], ['gold-centre', 2], ['turtle', 2], ['far-altars', 2], ['cluster-carpets', 2],
];
// The ladder mix's plan (`suite --mix ladder`, the default with --out since 2026-11-05): calibration 2's ladder-like presets
// and ladder maps under random edits, no stress families, in counts whose maps match the 128 ladder maps'
// distribution (research/mapgen-vs-ladder-2026-11-05.md, "After").
const LADDER_PLAN = [
  ['ladder', 112], ['classic', 30], ['small-brawl', 4], ['maze', 3], ['caves', 2], ['lanes', 2], ['lakes', 4], ['jungle', 2], ['monolith', 5], ['rows', 3],
  ['contested-centre', 4], ['tiny', 6], ['huge', 4], ['monolith-only', 3], ['shared-gems', 3], ['vaults', 3], ['altar-poor', 2],
  [{ mutate: 'random' }, 64],
];
// The paradigms mix's plan (`suite --mix paradigms`, 2026-11-08): paradigms.mjs's layouts, none of them in the
// ladder mixes, each under calibration 3's ladder rates for everything but the layout, in equal shares.
const PARADIGM_PLAN = [
  ['ring-road', 22], ['colosseum', 21], ['isles', 21], ['choke-web', 21], ['corridors', 21], ['stones', 21], ['mesa-field', 21], ['contours', 22],
  ['compartments', 21], ['braided-lanes', 22], ['home-keeps', 22], ['meander-river', 21],
];
// Suite mixes: the plan, the calibration, how counts are drawn (fixed or varied per seed) and how candidates are
// kept ('diverse': farthest-point picks from --oversample (3) times the count; 'first': the first that succeed,
// in seed order, from 1.3 times the count, so the suite keeps the sampler's distribution). The -v1 mixes remake
// the maps of the generator of 2026-10-30 to 2026-11-05 byte for byte.
const MIXES = {
  ladder: { plan: LADDER_PLAN, calib: 2, counts: 'fixed', select: 'first', over: 1.3 },
  'ladder-v2': { plan: LADDER_PLAN, calib: 3, counts: 'fixed', select: 'first', over: 1.3 },
  paradigms: { plan: PARADIGM_PLAN, calib: 3, counts: 'fixed', select: 'first', over: 1.5 },
  varied: { plan: PLAN, calib: 2, counts: 'varied', select: 'diverse', over: 3 },
  fixed: { plan: PLAN, calib: 2, counts: 'fixed', select: 'diverse', over: 3 },
  'varied-v1': { plan: PLAN, calib: 1, counts: 'varied', select: 'diverse', over: 3 },
  'fixed-v1': { plan: PLAN, calib: 1, counts: 'fixed', select: 'diverse', over: 3 },
};
const SUITES = { gen: { dir: 'maps/gen', seed: 6001 }, 'gen-s1': { dir: 'maps/gen-s1', seed: 6002 } };
const LADDER_DIR = path.join(ROOT, 'maps');

// The metric space of `diversity`, the nearest-ladder distance and the diverse pick.
const FEATURES = {
  log_area: m => Math.log(m.area), aspect: m => m.aspect, reach_frac: m => m.reach_frac, walls: m => m.walls, holes: m => m.holes, bushes: m => m.bushes,
  spawn_rel: m => m.spawn_rel, detour: m => Math.min(m.detour, 4), choke_rel: m => m.choke_rel ?? 0, openness: m => m.openness, boundary: m => m.boundary, cramped: m => m.cramped,
  fill_corner: m => m.fill_corner, fill_centre: m => m.fill_centre, fill_edge: m => m.fill_edge,
  altars: m => Math.log(1 + m.altars), altar_ratio: m => m.altar_ratio ?? 0.5, groups: m => Math.log(1 + m.groups_side + m.shared_groups), camp_density: m => m.camp_density,
  log_gems: m => Math.log(1 + m.gems_side), big_share: m => m.big_share, shared_share: m => m.shared_share, cluster_share: m => m.cluster_share,
  camp_ratio: m => m.camp_ratio ?? 0.3, picks: m => m.picks, dash_gems: m => m.dash_gems ?? 0, tele_gems: m => m.tele_gems ?? 0,
  dash_gain: m => Math.log(m.dash_gain ?? 1), tele_gain: m => Math.log(m.tele_gain ?? 1), narrow: m => m.narrow ?? 0, leaky: m => Math.log(1 + (m.leaky ?? 0)), spawn_ring: m => m.spawn_ring ?? 0,
  max_group: m => Math.log(1 + (m.max_group ?? 1)), diag_groups: m => Math.log(1 + (m.diag_groups ?? 0)), sight_gap: m => m.sight_gap ?? 0,
};
const featureVector = m => Object.values(FEATURES).map(f => +f(m) || 0);
const shapeClass = m => m.fill_centre < 0.3 ? 'ring' : m.fill_corner < 0.3 ? (m.fill_edge < 0.3 ? 'round' : 'cross/band') : m.fill_corner < 0.6 ? 'irregular' : 'full';

function parseSet(items) {
  const out = {};
  for (const item of items) {
    const [k, ...rest] = item.split('='), v = rest.join('=');
    try { out[k] = JSON.parse(v); } catch { out[k] = v; }
  }
  return out;
}

function parseArgs(argv) {
  const opts = { _: [], set: [], op: [] };
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i];
    if (!a.startsWith('--')) { opts._.push(a); continue; }
    const key = a.slice(2);
    if (['show', 'force', 'json'].includes(key)) opts[key] = true;
    else if (key === 'set' || key === 'op') opts[key].push(argv[++i]);
    else opts[key] = argv[++i];
  }
  return opts;
}

// Encodes with the engine's MapBuilder, reloads as a game, and checks the engine saw the same map.
function encode(engine, g) {
  const bytes = engine.encode(g.toMap());
  engine.load(bytes);
  const back = Grid.fromMap(engine.decode(bytes));
  if (Buffer.compare(Buffer.from(back.t), Buffer.from(g.t)) || back.camps.length !== g.camps.length) throw new GenFail('engine round trip differs');
  return bytes;
}

function summary(name, m) {
  const types = Object.entries(m.types).map(([k, v]) => `${k.replace('_cluster', '')}:${v}`).join(',');
  return `${name.padEnd(30)} ${m.size.padStart(7)} ${m.sym.padEnd(10)} picks=${m.picks} spawn=${m.spawn} walls=${m.walls} holes=${m.holes} bush=${m.bushes} ` +
    `dist=${m.spawn_dist} choke=${m.choke} altars=${m.altars} altar=${m.altar_zone}:${m.altar_ratio} groups/side=${m.groups_side}${m.shared_groups ? `+${m.shared_groups} shared` : ''} gems/side=${m.gems_side} [${types}]`;
}

// ---- mutation -----------------------------------------------------------------------------
function canonicalTiles(g, kind) {
  const out = [];
  for (let i = 0; i < g.t.length; i++) if (g.t[i] === kind && i <= g.mirror(i)) out.push(i);
  return out;
}

const MUT_SPEC = { carve_width: 2, min_pocket: 20, hole_cost: 1.5, camp_spawn_gap: 4 };

// Each team A side group as canonical cells; shared groups stay as placed.
function campGroupsCanonical(g) {
  return sideGroups(g).mine.map(q => q.members.map(c => [c.type, c.x, c.y]));
}

function sharedCamps(g) {
  const tiles = new Set(sideGroups(g).shared.flatMap(q => [...q.tiles]));
  return g.camps.filter(c => tiles.has(c.y * g.W + c.x));
}

function placeAltar(g, rng, band) {
  const f = spawnFields(g), occupied = g.campMask(), all = [];
  for (let i = 0; i < g.t.length; i++) if (g.t[i] === ALTAR) all.push(i);
  const free = (x, y, i) => g.t[i] === GROUND && !occupied[i] && i !== g.mirror(i) && all.every(j => Math.max(Math.abs(j % g.W - x), Math.abs(Math.floor(j / g.W) - y)) >= 5)
    && [0, 1].every(team => g.spawnTiles(team).every(j => Math.max(Math.abs(j % g.W - x), Math.abs(Math.floor(j / g.W) - y)) >= 3));
  for (const i of candidates(g, rng, f, band, free).slice(0, 40)) {
    g.set(i % g.W, Math.floor(i / g.W), ALTAR);
    if (stillConnected(g)) return true;
    g.set(i % g.W, Math.floor(i / g.W), GROUND);
  }
  return false;
}

// Partitions the canonical tiles of `kind` into edge-connected chunks of at most `max` tiles, grown
// from random seeds: removing or converting whole chunks breaks a wall into segments with gaps,
// as a designer would, where removing random tiles leaves specks.
function chunks(g, rng, kind, max) {
  const seen = new Uint8Array(g.t.length), out = [];
  for (const s of rng.shuffle(canonicalTiles(g, kind))) {
    if (seen[s]) continue;
    const chunk = [s];
    seen[s] = seen[g.mirror(s)] = 1;
    for (let h = 0; h < chunk.length && chunk.length < max; h++) {
      const x = chunk[h] % g.W, y = Math.floor(chunk[h] / g.W);
      for (const [dx, dy] of N4) {
        const j = (y + dy) * g.W + x + dx;
        if (g.in(x + dx, y + dy) && !seen[j] && g.t[j] === kind && chunk.length < max) { seen[j] = seen[g.mirror(j)] = 1; chunk.push(j); }
      }
    }
    out.push(chunk);
  }
  return out;
}

const setAll = (g, tiles, kind) => { for (const i of tiles) g.set(i % g.W, Math.floor(i / g.W), kind); };
const KINDS = { walls: WALL, holes: HOLE, bushes: BUSH };
const spawnDist = (g, x, y) => Math.min(...[0, 1].map(team => Math.min(...g.spawnTiles(team).map(j => Math.max(Math.abs(j % g.W - x), Math.abs(Math.floor(j / g.W) - y))))));

// Doors: a wall run at most 3 thick between walkable tiles, opened 2-3 wide.
function doors(g, rng, n) {
  const pass = g.walkable(), open = (x, y) => g.in(x, y) && pass[y * g.W + x];
  let made = 0;
  for (const i of rng.shuffle(canonicalTiles(g, WALL))) {
    if (made >= n) break;
    const x = i % g.W, y = Math.floor(i / g.W);
    for (const [dx, dy] of rng.shuffle([[1, 0], [0, 1]])) {
      let a = 0, b = 0;
      while (a < 3 && g.in(x - dx * (a + 1), y - dy * (a + 1)) && g.get(x - dx * (a + 1), y - dy * (a + 1)) === WALL) a++;
      while (b < 3 && g.in(x + dx * (b + 1), y + dy * (b + 1)) && g.get(x + dx * (b + 1), y + dy * (b + 1)) === WALL) b++;
      if (a + b + 1 > 3 || !open(x - dx * (a + 1), y - dy * (a + 1)) || !open(x + dx * (b + 1), y + dy * (b + 1))) continue;
      const w = rng.int(2, 3);
      for (let k = -a; k <= b; k++) for (let q = 0; q < w; q++) {
        const xx = x + dx * k + dy * q, yy = y + dy * k + dx * q;
        if (g.in(xx, yy) && g.get(xx, yy) === WALL) g.set(xx, yy, GROUND);
      }
      made++;
      break;
    }
  }
}

// Vaults: a wall ring around a team A camp group or altar, two tiles out, leaving a one-tile walk
// inside to land on: a crystal reaches it, nothing else.
function vaults(g, rng, n) {
  const { mine } = sideGroups(g), altars = canonicalTiles(g, ALTAR).filter(i => i !== g.mirror(i)).map(i => [[i % g.W, Math.floor(i / g.W)]]);
  const targets = rng.shuffle([...mine.map(q => q.members.map(c => [c.x, c.y])), ...altars]);
  let made = 0;
  for (const cells of targets) {
    if (made >= n) break;
    const x0 = Math.min(...cells.map(c => c[0])) - 2, x1 = Math.max(...cells.map(c => c[0])) + 2, y0 = Math.min(...cells.map(c => c[1])) - 2, y1 = Math.max(...cells.map(c => c[1])) + 2;
    if (x0 < 0 || y0 < 0 || x1 >= g.W || y1 >= g.H || spawnDist(g, x0, y0) < 6 || spawnDist(g, x1, y1) < 6) continue;
    const ring = [], inside = [], own = new Set(cells.map(([x, y]) => y * g.W + x)), camps = g.campMask();
    let ok = true;
    for (let y = y0; y <= y1 && ok; y++) for (let x = x0; x <= x1; x++) {
      const i = y * g.W + x, edge = x === x0 || x === x1 || y === y0 || y === y1;
      // Clear of other camps and altars, and of its own mirror.
      if (!own.has(i) && (camps[i] || g.t[i] === ALTAR)) { ok = false; break; }
      const [mx, my] = g.mirrorXY(x, y);
      if (mx >= x0 - 1 && mx <= x1 + 1 && my >= y0 - 1 && my <= y1 + 1) { ok = false; break; }
      (edge ? ring : inside).push(i);
    }
    if (!ok) continue;
    const saved = g.t.slice();
    setAll(g, ring, WALL);
    for (const i of inside) if (!own.has(i) && g.t[i] !== GROUND && g.t[i] !== BUSH) g.set(i % g.W, Math.floor(i / g.W), GROUND);
    for (const i of inside) { g.vaults.add(i); g.vaults.add(g.mirror(i)); }
    if (stillConnected(g)) { made++; continue; }
    g.t = saved;
    for (const i of inside) { g.vaults.delete(i); g.vaults.delete(g.mirror(i)); }
  }
  return made;
}

// Economy retyping: each canonical camp may become a richer or poorer one in place.
const ECON = {
  rich: { wolf: ['elk', 0.5], elk: ['golem', 0.25], gold_cluster: ['gem_cluster', 0.4], golem: ['monolith', 0.1] },
  poor: { golem: ['elk', 0.7], monolith: ['golem', 0.7], elk: ['wolf', 0.6], gem_cluster: ['gold_cluster', 0.5] },
  gold: { gem_cluster: ['gold_cluster', 0.7], elk: ['wolf', 0.3] },
  gems: { gold_cluster: ['gem_cluster', 0.7], wolf: ['elk', 0.3] },
};

function mutate(g, rng, ops) {
  for (const op of ops) {
    if (op === 'altars=mid') {
      // Moves every walkable altar pair (and self-mirrored altar) into the central band.
      const f = spawnFields(g), tiles = canonicalTiles(g, ALTAR).filter(i => g.reachNear(f.dA, i % g.W, Math.floor(i / g.W)) >= 0);
      for (const i of tiles) g.set(i % g.W, Math.floor(i / g.W), GROUND);
      for (let k = 0; k < tiles.length; k++) placeAltar(g, rng, BANDS.central);
      continue;
    }
    let m = /^econ=(rich|poor|gold|gems)$/.exec(op);
    if (m) {
      const table = ECON[m[1]];
      g.camps = g.camps.map(c => table[c.type] && rng.chance(table[c.type][1]) ? { ...c, type: table[c.type][0] } : c);
      continue;
    }
    m = /^(walls|holes|bushes)~(walls|holes|bushes)\*([\d.]+)$/.exec(op);
    if (m) {
      const from = KINDS[m[1]], to = KINDS[m[2]], list = chunks(g, rng, from, rng.int(4, 10)), occupied = g.campMask();
      for (const c of list.slice(0, Math.round(list.length * Math.min(1, +m[3])))) setAll(g, c.filter(i => !occupied[i]), to);
      if (to !== BUSH) repair(g, rng);
      continue;
    }
    m = /^(doors|gaps|vaults)\+(\d+)$/.exec(op);
    if (m) {
      if (m[1] === 'doors') doors(g, rng, +m[2]);
      else if (m[1] === 'gaps' && gaps(g, rng, +m[2])) raise(g, 'dash');
      else if (m[1] === 'vaults') vaults(g, rng, +m[2]);
      continue;
    }
    m = /^(walls|holes|bushes|camps|altars|picks)([*+=-])([\d.]+)$/.exec(op);
    if (!m) throw new Error(`bad --op ${op}; see usage`);
    const [, what, sign, num] = m, v = +num;
    if (what === 'picks') { g.picks = v; continue; }
    if (['walls', 'holes', 'bushes'].includes(what)) {
      const kind = KINDS[what];
      if (sign === '*' && v < 1 || sign === '-') {
        // Whole chunks (bush: whole clusters, which vision groups) go.
        const list = chunks(g, rng, kind, kind === BUSH ? Infinity : rng.int(4, 10)), drop = sign === '*' ? Math.round(list.length * (1 - v)) : v;
        for (const c of list.slice(0, drop)) setAll(g, c, GROUND);
      } else {
        const add = sign === '*' ? Math.max(1, Math.round(canonicalTiles(g, kind).length * (v - 1) / 4)) : v;
        const where = (x, y) => spawnDist(g, x, y) > 4;
        if (kind === BUSH) clumps(g, rng, add, [3, 9], { where });
        else scatterPrefabs(g, rng, add, { gap: 4, where, kinds: { [kind]: 1 }, names: kind === HOLE ? ['pond', 'bar', 'ell', 'post', 'pillar'] : undefined });
      }
      if (kind !== BUSH) repair(g, rng);
      continue;
    }
    if (what === 'altars') {
      const tiles = canonicalTiles(g, ALTAR);
      if (sign === '-') for (const i of rng.shuffle(tiles).slice(0, Math.min(v, tiles.length - 1))) g.set(i % g.W, Math.floor(i / g.W), GROUND);
      else for (let k = 0; k < v; k++) placeAltar(g, rng, BANDS.any);
      continue;
    }
    const groups = campGroupsCanonical(g);
    if (sign === '-') {
      const kept = rng.shuffle(groups.slice()).slice(Math.min(v, groups.length - 1));
      g.camps = [...sharedCamps(g), ...kept.flat().map(([type, x, y]) => ({ type, x, y }))];
    } else if (sign === '+') {
      for (let k = 0, guard = 0; k < v && guard < v * 6; guard++) {
        const tpl = TEMPLATES[rng.choice(['wolf', 'wolf_pair', 'elk', 'elk_gold', 'gems', 'gold', 'elk_gems', 'golem_gold'])](rng), f = spawnFields(g);
        for (const i of candidates(g, rng, f, BANDS.any, () => true).slice(0, 60))
          if (tryGroup(g, tpl.map(([t, dx, dy]) => [t, i % g.W + dx, Math.floor(i / g.W) + dy]), MUT_SPEC)) { k++; break; }
      }
    } else {
      // Rescale each group's walking distance from its own spawn, keeping its shape and heading.
      const open = spawnFields(g);
      g.camps = sharedCamps(g);
      for (const cells of groups) {
        const [, ax, ay] = cells[0], d0 = Math.max(1, open.dA[ay * g.W + ax] >= 0 ? open.dA[ay * g.W + ax] : g.reachNear(open.dA, ax, ay)), target = d0 * v;
        const f = spawnFields(g), opts = [];
        for (let i = 0; i < g.t.length; i++) {
          if (f.dA[i] < 0 || f.dB[i] < 0 || f.dA[i] > f.dB[i] || Math.abs(f.dA[i] - target) > Math.max(2, 0.08 * target)) continue;
          const x = i % g.W, y = (i - x) / g.W;
          opts.push([Math.hypot(x - ax, y - ay) + rng.float(), x, y]);
        }
        opts.sort((p, q) => p[0] - q[0]);
        let placed = false;
        for (const [, x, y] of opts.slice(0, 80)) if (tryGroup(g, cells.map(([t, cx, cy]) => [t, cx - ax + x, cy - ay + y]), MUT_SPEC)) { placed = true; break; }
        if (!placed) tryGroup(g, cells, MUT_SPEC);
      }
    }
  }
  return g;
}

const raise = (g, level) => { if (LEVELS.indexOf(level) > LEVELS.indexOf(g.access)) g.access = level; };

// A map that needs only walking is kept that way (blocked pockets are tunnelled to); one that
// already needs a dash or a crystal is left as edited, for validation to judge.
function repair(g, rng) {
  if (g.access !== 'walk') return;
  connect(g, rng, MUT_SPEC);
  if (!stillConnected(g)) {
    const groups = campGroupsCanonical(g);
    g.camps = sharedCamps(g);
    for (const cells of groups) tryGroup(g, cells, MUT_SPEC);
  }
}

const LADDER_NAMES = () => fs.readdirSync(LADDER_DIR).filter(f => f.endsWith('.map26a')).map(f => f.replace(/^\d\d/, '').replace(/\.map26a$/, '')).sort();

// A random edit list: one or two terrain edits, often an economy or camp edit, sometimes an altar,
// access (dash gaps, crystal vaults) or pick-count edit.
export function randomOps(rng, area = null) {
  const ops = [], f = (lo, hi) => rng.uniform(lo, hi).toFixed(2);
  for (let k = rng.int(1, 2); k > 0; k--) {
    const t = rng.weighted({ fewer_walls: 2, more_walls: 2, fewer_holes: 1, more_holes: 1, fewer_bushes: 1.2, more_bushes: 1.5, doors: 1.5, convert: 1.5 });
    if (t === 'fewer_walls') ops.push(`walls*${f(0.3, 0.8)}`);
    else if (t === 'more_walls') ops.push(`walls+${rng.int(3, 10)}`);
    else if (t === 'fewer_holes') ops.push(`holes*${f(0.2, 0.7)}`);
    else if (t === 'more_holes') ops.push(`holes+${rng.int(2, 6)}`);
    else if (t === 'fewer_bushes') ops.push(`bushes*${f(0, 0.6)}`);
    else if (t === 'more_bushes') ops.push(`bushes+${rng.int(3, 10)}`);
    else if (t === 'doors') ops.push(`doors+${rng.int(2, 6)}`);
    else ops.push(`${rng.choice(['walls~holes', 'holes~walls', 'walls~bushes', 'bushes~walls'])}*${f(0.3, 1)}`);
  }
  if (rng.chance(0.65)) {
    const e = rng.weighted({ scale: 2, add: 1.5, drop: 1, econ: 2 });
    ops.push(e === 'scale' ? `camps*${f(0.6, 1.5)}` : e === 'add' ? `camps+${rng.int(1, 5)}` : e === 'drop' ? `camps-${rng.int(1, 3)}` : `econ=${rng.choice(['rich', 'poor', 'gold', 'gems'])}`);
  }
  if (rng.chance(0.4)) ops.push(rng.weighted({ 'altars=mid': 2, [`altars+${rng.int(1, 2)}`]: 1, [`altars-${rng.int(1, 2)}`]: 1 }));
  if (rng.chance(0.3)) ops.push(rng.chance(0.6) ? `gaps+${rng.int(1, 4)}` : `vaults+${rng.int(1, 2)}`);
  if (rng.chance(0.5)) ops.push(`picks=${area === null ? rng.int(3, 5) : rng.weighted(PICKS_BY_AREA.find(([lim]) => area < lim)[1])}`);
  return ops;
}

function loadGrid(engine, file) {
  const name = file.endsWith('.map26a') ? file : `${file}.map26a`;
  const prefixed = fs.readdirSync(LADDER_DIR).find(f => f.replace(/^\d\d/, '') === name);
  const p = fs.existsSync(file) ? file : path.join(LADDER_DIR, prefixed ?? name);
  return Grid.fromMap(engine.decode(fs.readFileSync(p)));
}

// The source keeps its access: a map whose objectives need a dash or a crystal (islands, vaults)
// may still need them, and one whose camps plug the way (boss-battle) is gated. With no `ops`, the
// source and the edits are drawn from `seed`.
// Calibration 2 draws a pick-count edit from the ladder's picks for the map's area.
function mutated(engine, source, seed, ops, calib = CALIB) {
  let base;
  if (!ops?.length || source === 'random') {
    const rng = makeRng(`mutation:${seed}`);
    if (source === 'random') source = rng.choice(LADDER_NAMES());
    if (calib >= 2) base = loadGrid(engine, source);
    if (!ops?.length) ops = randomOps(rng, calib >= 2 ? base.W * base.H : null);
  }
  base ??= loadGrid(engine, source);
  base.access = LEVELS[naturalAccess(base)];
  base.gated = validate(base, { strict: false }).warnings.some(w => /past the camps|enclosed by/.test(w));
  const zone = ops.includes('altars=mid') ? 'mid' : null, baseDist = metrics(base).spawn_dist, keep = calib >= 2 ? quirkTiles(base) : null;
  for (let attempt = 0; attempt < 20; attempt++) {
    const rng = makeRng(`mutate:${source}:${seed}:${attempt}`), g = base.clone();
    g.access = base.access; g.gated = base.gated;
    try { mutate(g, rng, ops); } catch (e) { if (e instanceof GenFail) continue; throw e; }
    // Calibration 2 tidies the leaky diagonals and 1-wide gaps the edits made, not the map's own.
    if (keep) tidy(g, { unleak: true, unnarrow: true }, keep);
    const { errors } = validate(g, { minSide: calib >= 2 ? 28 : 30 });
    if (errors.length) continue;
    const met = metrics(g);
    if (zone && met.altar_zone !== zone) continue;
    // Edits that open a short way between the spawns (walls to bush, doors) undo the map's design.
    if (met.spawn_dist < Math.min(18, baseDist)) continue;
    g.meta = { mutate: path.basename(source, '.map26a'), ops, seed, attempt, ...(calib >= 2 && { calib }), metrics: met };
    return g;
  }
  throw new GenFail(`mutating ${source} with ${ops.join(' ')} failed`);
}

// Greedy farthest-point selection on normalised metrics (from unsw-battlecode's map_gen).
function pickDiverse(cands, k) {
  if (cands.length <= k) return cands;
  const vec = cands.map(c => featureVector(c.meta.metrics));
  const lo = vec[0].map((_, j) => Math.min(...vec.map(v => v[j]))), hi = vec[0].map((_, j) => Math.max(...vec.map(v => v[j])));
  const norm = vec.map(v => v.map((x, j) => (x - lo[j]) / ((hi[j] - lo[j]) || 1)));
  // Quotas per altar zone in proportion to the candidates: farthest-point picks favour the extreme
  // altar ratios (nearest altars by the spawn) otherwise.
  const zone = c => c.meta.metrics.altar_zone, quota = {}, used = {};
  for (const c of cands) quota[zone(c)] = (quota[zone(c)] ?? 0) + k / cands.length;
  const chosen = [0];
  used[zone(cands[0])] = 1;
  while (chosen.length < k) {
    let best = -1, bestD = -1;
    for (let i = 0; i < cands.length; i++) {
      if (chosen.includes(i) || (used[zone(cands[i])] ?? 0) >= Math.ceil(quota[zone(cands[i])])) continue;
      const d = Math.min(...chosen.map(j => norm[i].reduce((s, x, f) => s + (x - norm[j][f]) ** 2, 0)));
      if (d > bestD) { bestD = d; best = i; }
    }
    chosen.push(best);
    used[zone(cands[best])] = (used[zone(cands[best])] ?? 0) + 1;
  }
  return chosen.sort((a, b) => a - b).map(i => cands[i]);
}

// One candidate of a suite: the map or the reason it failed. Candidates depend only on their seed, so
// worker threads can make them in any order.
function candidate(engine, { what, s, extra, calib }) {
  try {
    const g = typeof what === 'string' ? generate(what, s, { ...extra, calib }) : mutated(engine, what.mutate, s, what.ops, calib);
    g.name = typeof what === 'string' ? `gen-${what}-${s}` : `mut-${g.meta.mutate}-${s}`;
    return { name: g.name, bytes: encode(engine, g), meta: g.meta };
  } catch (e) {
    if (!(e instanceof GenFail) && !(e instanceof MapError)) throw e;
    return { skip: `  skip ${typeof what === 'string' ? what : what.mutate}:${s}: ${e.message}` };
  }
}

async function makeCandidates(tasks, jobs) {
  if (jobs <= 1) { const engine = await createEngine(); return tasks.map(t => candidate(engine, t)); }
  const out = new Array(tasks.length);
  // Slowest first, so no long candidate starts last: atoll and archipelago take up to ~1.4 s (2026-10-29).
  const cost = ({ what }) => typeof what !== 'string' ? 3 : { atoll: 0, archipelago: 1 }[what] ?? (PRESETS[what].designed ? 2 : 3);
  const order = tasks.map((_, k) => k).sort((a, b) => cost(tasks[a]) - cost(tasks[b]) || a - b);
  let next = 0;
  // Child processes, not worker threads: 48 threads in one process kept only ~29 busy (2026-10-29).
  await Promise.all(Array.from({ length: Math.min(jobs, tasks.length) }, () => new Promise((resolve, reject) => {
    const w = fork(fileURLToPath(import.meta.url), [], { serialization: 'advanced', env: { ...process.env, MAPGEN_ROLE: 'candidate' } });
    const feed = () => next < tasks.length ? (k => w.send({ k, task: tasks[k] }))(order[next++]) : w.disconnect();
    w.on('message', ({ k, r }) => { out[k] = r; feed(); });
    w.on('error', reject);
    w.on('exit', code => code ? reject(new Error(`candidate process exited ${code}`)) : resolve());
    feed();
  })));
  return out;
}

// A suite's count per plan entry. 'varied' weighs each family and each preset by a
// random log-normal factor drawn from the seed, drops a preset now and then, and rescales to the
// plan's size, so fresh suites stress different things; 'fixed' keeps the plan's counts.
function suiteCounts(plan, seed, mix, over) {
  const base = plan.map(([, n]) => n), total = base.reduce((s, n) => s + n, 0);
  if (mix === 'fixed') return base;
  const rng = makeRng(`mix:${seed}`), normal = () => Math.sqrt(-2 * Math.log(1 - rng.float())) * Math.cos(2 * Math.PI * rng.float());
  const fam = {}, family = what => typeof what === 'string' ? familyOf(what) : 'mutation', size = {};
  for (const [what] of plan) size[family(what)] = (size[family(what)] ?? 0) + 1;
  // A family's only entry (the mutations) is never dropped, so the drop never removes a family.
  const w = plan.map(([what, n]) => { fam[family(what)] ??= Math.exp(0.5 * normal()); return rng.chance(0.12) && size[family(what)] > 1 ? 0 : n * fam[family(what)] * Math.exp(0.6 * normal()); });
  // Candidate seeds number an entry's candidates below 100.
  const cap = plan.map(([what]) => Math.floor(99 / (typeof what === 'string' ? over : 2))), out = base.map(() => 0);
  for (let left = total, round = 0; left > 0 && round < 10; round++, left = total - out.reduce((s, n) => s + n, 0)) {
    const open = w.map((x, i) => out[i] < cap[i] ? x : 0), sum = open.reduce((s, x) => s + x, 0);
    if (!sum) break;
    const want = open.map(x => x / sum * left), add = want.map((x, i) => Math.min(Math.floor(x), cap[i] - out[i]));
    let rem = left - add.reduce((s, x) => s + x, 0);
    for (const [, i] of want.map((x, i) => [x - Math.floor(x), i]).sort((p, q) => q[0] - p[0])) if (rem > 0 && open[i] && out[i] + add[i] < cap[i]) { add[i]++; rem--; }
    add.forEach((x, i) => { out[i] += x; });
  }
  return out;
}

// Seeds as a comma list with ranges: 3001,3005-3008.
const seedList = spec => String(spec).split(',').flatMap(r => { const [a, b = a] = r.split('-').map(Number); return Array.from({ length: b - a + 1 }, (_, k) => a + k); });

async function suite(opts) {
  // Rebuilding maps/gen or gen-s1 (no --out) defaults to the mix they were made with, so the A/B suites keep their maps.
  const name = opts._[0] ?? 'gen', mix = opts.mix ?? (opts.out ? 'ladder' : 'varied-v1'), m = MIXES[mix];
  if (!SUITES[name]) throw new Error(`unknown suite ${name}; one of ${Object.keys(SUITES).join(', ')}`);
  if (!m) throw new Error(`unknown --mix ${mix}; one of ${Object.keys(MIXES).join(', ')}`);
  const def = { ...SUITES[name], plan: m.plan }, over = +(opts.oversample ?? m.over), seeds = seedList(opts.seed ?? def.seed), counts = new Map(seeds.map(seed => [seed, suiteCounts(def.plan, seed, m.counts, over)]));
  // 'first' suites number an entry's candidates below 1000 (the plan has under 100 entries), 'diverse' ones below 100.
  const per = m.select === 'first' ? 1000 : 100, tries = (what, n) => Math.ceil(n * (typeof what === 'string' || m.select === 'first' ? over : 2));
  if (m.select === 'first' && def.plan.length >= 100) throw new Error('a first-select plan needs under 100 entries');
  // Without --out the A/B suite is replaced in place: only its own seed and mix keep its maps.
  if (!opts.out && ((opts.seed !== undefined && String(opts.seed) !== String(def.seed)) || mix !== 'varied-v1'))
    throw new Error(`without --out this replaces ${def.dir} (seed ${def.seed}, --mix varied-v1) in place; pass --out DIR for a fresh suite`);
  if (seeds.length > 1 && !opts.out?.includes('{seed}')) throw new Error('several seeds need --out with {seed}, e.g. maps/suites/fresh/fresh-{seed}');
  // More than ~48 processes was slower on 96 cores (memory-bound, 2026-10-29): 10 suites in 9.2 s at 48, 10.3 at 94.
  const jobs = +(opts.jobs ?? Math.max(1, Math.min(48, os.availableParallelism() - 2))), tasks = [];
  for (const seed of seeds) for (const [idx, [what, , extra]] of def.plan.entries())
    for (let j = 0; j < (m.select === 'first' ? tries(what, counts.get(seed)[idx]) : counts.get(seed)[idx] * (typeof what === 'string' ? over : 2)); j++)
      tasks.push({ seed, idx, what, extra, calib: m.calib, s: seed * 100000 + idx * per + j });
  const t0 = Date.now(), made = await makeCandidates(tasks, jobs), engine = await createEngine();
  console.log(`${tasks.length} candidates for ${seeds.length} suite(s) in ${((Date.now() - t0) / 1000).toFixed(1)} s in ${Math.min(jobs, tasks.length)} process(es)`);
  for (const seed of seeds) writeSuite(engine, def, seed, over, mix, counts.get(seed), path.resolve(opts.out?.replaceAll('{seed}', seed) ?? path.join(ROOT, def.dir)),
    tasks.map((t, k) => [t, made[k]]).filter(([t]) => t.seed === seed));
}

function writeSuite(engine, def, seed, over, mix, counts, out, made) {
  const { calib, select } = MIXES[mix];
  fs.mkdirSync(out, { recursive: true });
  const index = [], files = new Map(), picks = [];
  for (const [idx, [what]] of def.plan.entries()) {
    const n = counts[idx], cands = [];
    for (const [t, r] of made) {
      if (t.idx !== idx) continue;
      if (r.skip) console.log(r.skip);
      else cands.push(r);
    }
    const picked = select === 'first' ? cands.slice(0, n) : pickDiverse(cands, n);
    if (picked.length < n) console.log(`  warning: ${typeof what === 'string' ? what : what.mutate} produced ${picked.length}/${n}`);
    for (const g of picked) {
      files.set(`${g.name}.map26a`, g.bytes);
      const kind = typeof what === 'string' ? familyOf(what) : 'mutation';
      index.push({ file: `${g.name}.map26a`, kind, ...g.meta, spec: g.meta.spec && Object.fromEntries(Object.entries(g.meta.spec).filter(([k]) => !['camp_mix', 'altar_bands', 'contested_mix'].includes(k))) });
      picks.push(g.meta.metrics);
      console.log(summary(g.name, g.meta.metrics));
    }
  }
  // Each map's nearest competition map in the normalised metric space.
  const ladder = ladderMetrics(engine), { z } = normaliser([...ladder.map(l => l.m), ...picks]);
  for (const [k, row] of index.entries()) {
    const v = z(featureVector(picks[k]));
    let best = null;
    for (const l of ladder) { const d = dist(v, z(featureVector(l.m))); if (!best || d < best.dist) best = { map: l.name, dist: Math.round(100 * d) / 100 }; }
    row.ladder_nn = best;
  }
  // Other runs may be reading the pool: replace only changed files, each by an atomic rename.
  const plan = Object.fromEntries(def.plan.map(([what], idx) => [typeof what === 'string' ? what : 'mutation', counts[idx]]));
  files.set('index.json', Buffer.from(JSON.stringify({ generator: 'tools/mapgen/mapgen.mjs suite', seed, oversample: over, mix, ...(calib >= 2 && { calib, select }), plan, maps: index }, null, 1) + '\n'));
  let changed = 0, removed = 0;
  for (const [f, bytes] of files) {
    const dest = path.join(out, f);
    if (fs.existsSync(dest) && !Buffer.compare(fs.readFileSync(dest), bytes)) continue;
    fs.writeFileSync(`${dest}.tmp`, bytes);
    fs.renameSync(`${dest}.tmp`, dest);
    changed++;
  }
  for (const f of fs.readdirSync(out)) if (f.endsWith('.map26a') && !files.has(f)) { fs.unlinkSync(path.join(out, f)); removed++; }
  console.log(`${files.size - 1} maps in ${path.relative(ROOT, out) || out}: ${changed} files written, ${removed} removed, the rest unchanged`);
}

// ---- diversity ----------------------------------------------------------------------------
function mapFiles(spec) {
  return spec.split(',').flatMap(f => fs.statSync(f).isDirectory() ? fs.readdirSync(f).filter(x => x.endsWith('.map26a')).sort().map(x => path.join(f, x)) : [f]);
}

function loadMetrics(engine, file) {
  const g = Grid.fromMap(engine.decode(fs.readFileSync(file)));
  return { name: path.basename(file, '.map26a'), m: metrics(g) };
}

let ladderCache;
function ladderMetrics(engine) {
  ladderCache ??= fs.readdirSync(LADDER_DIR).filter(f => f.endsWith('.map26a')).sort().map(f => loadMetrics(engine, path.join(LADDER_DIR, f)));
  return ladderCache;
}

// z-scores per feature over a pooled population, so no set's own spread sets its scale.
function normaliser(population) {
  const vecs = population.map(featureVector), nf = vecs[0].length;
  const mean = Array.from({ length: nf }, (_, j) => vecs.reduce((s, v) => s + v[j], 0) / vecs.length);
  const sd = Array.from({ length: nf }, (_, j) => Math.sqrt(vecs.reduce((s, v) => s + (v[j] - mean[j]) ** 2, 0) / vecs.length) || 1);
  return { z: v => v.map((x, j) => (x - mean[j]) / sd[j]) };
}

// Root-mean-square difference per feature, in pooled standard deviations.
const dist = (a, b) => Math.sqrt(a.reduce((s, x, j) => s + (x - b[j]) ** 2, 0) / a.length);
const quant = (arr, q) => { const s = [...arr].sort((a, b) => a - b); return s.length ? s[Math.min(s.length - 1, Math.floor(q * s.length))] : null; };
const r2 = x => Math.round(100 * x) / 100;

function shares(list, key) {
  const c = {};
  for (const m of list) { const k = key(m); c[k] = (c[k] ?? 0) + 1; }
  return Object.entries(c).sort((a, b) => b[1] - a[1]).map(([k, v]) => `${k} ${Math.round(100 * v / list.length)}%`).join(', ');
}

async function diversity(opts) {
  const engine = await createEngine(), ladder = ladderMetrics(engine);
  const sets = opts._.map(spec => ({ name: spec, maps: mapFiles(spec).map(f => loadMetrics(engine, f)) }));
  const { z } = normaliser([...ladder, ...sets.flatMap(s => s.maps)].map(x => x.m)), lv = ladder.map(l => z(featureVector(l.m)));
  const nnLadder = (v, skip = -1) => Math.min(...lv.filter((_, k) => k !== skip).map(w => dist(v, w)));
  const loo = lv.map((v, k) => nnLadder(v, k)), far = quant(loo, 0.9);
  const lo = lv[0].map((_, j) => Math.min(...lv.map(v => v[j]))), hi = lv[0].map((_, j) => Math.max(...lv.map(v => v[j])));
  const report = { features: Object.keys(FEATURES), ladder: { maps: ladder.length, loo_nn_median: r2(quant(loo, 0.5)), loo_nn_p90: r2(far) }, sets: [] };
  for (const set of [{ name: 'ladder (maps/)', maps: ladder, isLadder: true }, ...sets]) {
    const vs = set.maps.map(x => z(featureVector(x.m))), nn = set.isLadder ? loo : vs.map(v => nnLadder(v));
    let pair = 0, pairs = 0;
    for (let a = 0; a < vs.length; a++) for (let b = a + 1; b < vs.length; b++) { pair += dist(vs[a], vs[b]); pairs++; }
    const outside = vs.map(v => v.filter((x, j) => x < lo[j] - 0.25 || x > hi[j] + 0.25).length);
    const ms = set.maps.map(x => x.m);
    const row = {
      set: set.name, maps: vs.length, ladder_nn_mean: r2(nn.reduce((s, x) => s + x, 0) / nn.length), ladder_nn_median: r2(quant(nn, 0.5)),
      beyond_ladder_p90: r2(nn.filter(d => d > far).length / nn.length), mean_pairwise: r2(pair / Math.max(1, pairs)),
      outside_ladder_range: r2(outside.filter(n => n > 0).length / vs.length), features_sd: r2(vs[0].map((_, j) => Math.sqrt(Math.max(0, vs.reduce((s, v) => s + v[j] ** 2, 0) / vs.length - (vs.reduce((s, v) => s + v[j], 0) / vs.length) ** 2))).reduce((s, x) => s + x, 0) / vs[0].length),
      altar_zone: shares(ms, m => m.altar_zone), shape: shares(ms, shapeClass), symmetry: shares(ms, m => m.sym), picks: shares(ms, m => m.picks),
      size: shares(ms, m => m.area < 1600 ? '<40^2' : m.area < 3600 ? '40-60^2' : m.area < 6400 ? '60-80^2' : '80-100^2'), aspect: shares(ms, m => m.aspect >= 2 ? '>=2' : m.aspect > 1.15 ? '1.15-2' : 'square'),
    };
    report.sets.push(row);
  }
  if (opts.json) { console.log(JSON.stringify(report, null, 1)); return; }
  console.log(`${ladder.length} ladder maps; their leave-one-out nearest-ladder distance: median ${report.ladder.loo_nn_median}, 90th percentile ${report.ladder.loo_nn_p90}`);
  console.log(`distances are RMS over ${report.features.length} features in pooled standard deviations: ${report.features.join(' ')}`);
  for (const r of report.sets) {
    console.log(`\n${r.set}: ${r.maps} maps`);
    console.log(`  nearest ladder map: mean ${r.ladder_nn_mean}, median ${r.ladder_nn_median}; beyond the ladder's own 90th percentile: ${Math.round(100 * r.beyond_ladder_p90)}%`);
    console.log(`  spread: mean pairwise distance ${r.mean_pairwise}, mean feature sd ${r.features_sd}; maps with a feature outside the ladder's range: ${Math.round(100 * r.outside_ladder_range)}%`);
    for (const k of ['altar_zone', 'shape', 'symmetry', 'picks', 'size', 'aspect']) console.log(`  ${k}: ${r[k]}`);
  }
}

const USAGE = `usage: node tools/mapgen/mapgen.mjs <command>
  list                                       presets
  gen PRESET [--seed N] [--set k=v]... [--calib 1|2|3] [--out FILE] [--show]   calibration 2 (the default)
      is fitted to the 128 ladder maps of 2026-11-05; 3 adds their group shapes and gem-ball rate
      (2026-11-08, --mix ladder-v2); 1 makes the maps of before
  mutate MAP|random [--seed N] [--op OP]... [--calib 1|2|3] [--out FILE] [--show]   without --op the edits are drawn
      from the seed (random: the ladder map too). OP: walls|holes|bushes *F (F<1 removes whole
      chunks, F>1 stamps cover pieces), +N/-N (stamp/remove N pieces), K1~K2*F (turn a share F of
      K1's chunks into K2, e.g. walls~bushes*0.5), doors+N, gaps+N (dash-only cuts across narrow
      passages), vaults+N (wall a group or altar in: crystal only), camps *F (rescale distance from
      spawn), camps|altars +N/-N, econ=rich|poor|gold|gems (retype camps), picks=N, altars=mid
  suite [NAME] [--out DIR] [--seed S] [--oversample K] [--jobs N] [--mix MIX]   rebuild maps/gen (or NAME: gen-s1),
      or with --out a fresh suite. MIX: ladder (the default with --out: LADDER_PLAN, ladder-like presets and
      mutations at fixed counts, the first candidates kept, calibration 2); ladder-v2 (the same under
      calibration 3, nearer the ladder: preferred for new programmes); paradigms (12 layouts the ladder mixes
      lack, paradigms.mjs, under calibration 3's ladder rates otherwise); varied (the stress PLAN, families and
      presets reweighed per seed) or fixed (the PLAN's counts), both keeping the most different;
      varied-v1, fixed-v1: those under calibration 1, byte for byte the suites of before 2026-11-05
      (varied-v1 is the default without --out, so maps/gen and gen-s1 rebuild as they were)
      (only changed files are rewritten); candidates in N processes (default 48, at most cores - 2). Several
      suites at once share the threads: --seed 3001-3004,3010 --out maps/suites/fresh/fresh-{seed}
  check FILE... [--show] [--json]           validate maps (any .map26a) and print metrics
  diversity SET... [--json]                  compare map sets (a dir, file, or comma-joined list each) with
      the ladder maps in maps/ in a normalised metric space: nearest-ladder distance, spread, shares
  show FILE                                  ASCII view (1/2 spawns, # wall, o hole, " bush, A altar, camps w wolf, e elk, k golem, m monolith, g gem and $ gold cluster: lowercase as stored, uppercase their mirrors)`;

async function main() {
  const [cmd, ...rest] = process.argv.slice(2), opts = parseArgs(rest);
  if (cmd === 'list') {
    for (const [k, v] of Object.entries(PRESETS)) console.log(`${k.padEnd(18)} ${v.doc}`);
    return 0;
  }
  if (cmd === 'gen' || cmd === 'mutate') {
    const engine = await createEngine(), seed = +(opts.seed ?? 0), name = opts._[0];
    if (!name) { console.error(USAGE); return 2; }
    if (cmd === 'gen' && !PRESETS[name]) { console.error(`unknown preset ${name}; see list`); return 2; }
    let g;
    const calib = +(opts.calib ?? CALIB);
    try { g = cmd === 'gen' ? generate(name, seed, { ...parseSet(opts.set), calib }) : mutated(engine, name, seed, opts.op, calib); }
    catch (e) { if (e instanceof GenFail) { console.error(e.message); return 1; } throw e; }
    const bytes = encode(engine, g);
    if (opts.show) console.log(g.render());
    console.log(summary(cmd === 'gen' ? `gen-${name}-${seed}` : `mut-${g.meta.mutate}-${seed}`, g.meta.metrics));
    if (cmd === 'mutate') console.log(`  ops: ${g.meta.ops.join(' ')}`);
    if (opts.out) { fs.mkdirSync(path.dirname(path.resolve(opts.out)), { recursive: true }); fs.writeFileSync(opts.out, bytes); console.log(`wrote ${opts.out}`); }
    return 0;
  }
  if (cmd === 'suite') { await suite(opts); return 0; }
  if (cmd === 'diversity') { await diversity(opts); return 0; }
  if (cmd === 'check' || cmd === 'show') {
    const engine = await createEngine();
    let failed = false;
    const files = opts._.flatMap(f => fs.statSync(f).isDirectory() ? fs.readdirSync(f).filter(x => x.endsWith('.map26a')).map(x => path.join(f, x)) : [f]);
    for (const f of files) {
      let g;
      try { const bytes = fs.readFileSync(f); engine.load(bytes); g = Grid.fromMap(engine.decode(bytes)); }
      catch (e) { console.log(`${f}: ERROR ${e.message}`); failed = true; continue; }
      if (cmd === 'show' || opts.show) console.log(g.render());
      if (cmd === 'show') continue;
      const { errors, warnings } = validate(g, { strict: false });
      failed ||= errors.length > 0;
      const m = errors.length ? null : metrics(g);
      if (opts.json) console.log(JSON.stringify({ file: f, errors, warnings, metrics: m }));
      else console.log(`${errors.length ? 'ERROR ' + errors.join('; ') : 'ok   '} ${m ? summary(path.basename(f, '.map26a'), m) : f}${warnings.length ? `\n      warn: ${warnings.join('; ')}` : ''}`);
    }
    return failed ? 1 : 0;
  }
  console.error(USAGE);
  return 2;
}

if (process.env.MAPGEN_ROLE !== 'candidate') process.exitCode = await main();
else {
  const engine = await createEngine();
  process.on('message', ({ k, task }) => process.send({ k, r: candidate(engine, task) }));
}
