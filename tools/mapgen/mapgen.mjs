import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { fork } from 'node:child_process';
import { clumps, scatterPrefabs } from './design.mjs';
import { ALTAR, BUSH, GROUND, Grid, HOLE, LEVELS, N4, WALL, makeRng } from './grid.mjs';
import { BANDS, GenFail, PRESETS, TEMPLATES, candidates, connect, generate, metrics, naturalAccess, sideGroups, spawnFields, stillConnected, tryGroup, validate } from './generate.mjs';
import { MapError, createEngine } from './wasm.mjs';

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..');

// The stored pool in maps/gen: [preset, count] or [{ mutate: 'random' }, count]. Each entry is
// oversampled and the most mutually different candidates kept. About a third is straightforward
// (ladder-like presets and random mutations of ladder maps), a third designed scenarios
// (design.mjs) and a third exotic shapes, interiors and economies.
const PLAN = [
  // Ladder-like.
  ['classic', 10], ['small-brawl', 2], ['maze', 3], ['caves', 3], ['lanes', 2], ['lakes', 2], ['jungle', 3], ['monolith', 3], ['rows', 2],
  ['altar-rich', 2], ['altar-poor', 2], ['contested-centre', 2], ['tiny', 2], ['huge', 2], ['random', 2], ['monolith-only', 2], ['shared-gems', 2], ['vaults', 3],
  // Ladder maps under random edits (the map and the edits both drawn from the seed).
  [{ mutate: 'random' }, 32],
  // Designed scenarios.
  ['atoll', 10], ['archipelago', 10], ['rivers', 10], ['fortress', 9], ['gatekeeper', 9], ['dungeon', 9], ['three-lane', 8], ['arena', 10],
  ['farmland', 8], ['continent', 9], ['hedges', 6],
  // Exotic playable-area shapes.
  ['round', 4], ['star', 3], ['donut', 4], ['cross', 3], ['hourglass', 3], ['band', 2], ['chambers', 4], ['blob', 3],
  // Exotic interiors.
  ['labyrinth', 4], ['spiral', 2], ['pillars', 2], ['cells', 2], ['diagonals', 2], ['tunnels', 3], ['city', 4], ['serpentine', 3], ['open-field', 2], ['long-thin', 2],
  // Exotic spawn distances and economies.
  ['close-spawns', 2], ['far-spawns', 2], ['golem-heavy', 2], ['gem-centre', 3], ['huge-shared', 3], ['tiny-groups', 2], ['sparse-camps', 2], ['dense-camps', 2],
  ['monsters-only', 1], ['clusters-only', 1], ['gem-drought', 2], ['gem-flood', 2], ['gold-flood', 1],
];
const SUITES = { gen: { dir: 'maps/gen', plan: PLAN, seed: 6001 }, 'gen-s1': { dir: 'maps/gen-s1', plan: PLAN, seed: 6002 } };
const LADDER_DIR = path.join(ROOT, 'maps');
const EXOTIC_PRESETS = new Set(Object.entries(PRESETS).filter(([, v]) => v.exotic).map(([k]) => k));

// The metric space of `diversity`, the nearest-ladder distance and the diverse pick.
const FEATURES = {
  log_area: m => Math.log(m.area), aspect: m => m.aspect, reach_frac: m => m.reach_frac, walls: m => m.walls, holes: m => m.holes, bushes: m => m.bushes,
  spawn_rel: m => m.spawn_rel, detour: m => Math.min(m.detour, 4), choke_rel: m => m.choke_rel ?? 0, openness: m => m.openness, boundary: m => m.boundary, cramped: m => m.cramped,
  fill_corner: m => m.fill_corner, fill_centre: m => m.fill_centre, fill_edge: m => m.fill_edge,
  altars: m => Math.log(1 + m.altars), altar_ratio: m => m.altar_ratio ?? 0.5, groups: m => Math.log(1 + m.groups_side + m.shared_groups), camp_density: m => m.camp_density,
  log_gems: m => Math.log(1 + m.gems_side), big_share: m => m.big_share, shared_share: m => m.shared_share, cluster_share: m => m.cluster_share,
  camp_ratio: m => m.camp_ratio ?? 0.3, picks: m => m.picks, dash_gems: m => m.dash_gems ?? 0, tele_gems: m => m.tele_gems ?? 0,
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

// Gaps: a passage at most 3 wide is cut across by a line of holes, so only a dash (or a crystal)
// gets through there.
function gaps(g, rng, n) {
  const pass = g.walkable(), occupied = g.campMask(), spawn = new Set([...g.spawnTiles(0), ...g.spawnTiles(1)]);
  const blocked = (x, y) => !g.in(x, y) || !pass[y * g.W + x];
  let made = 0;
  for (let tries = 0; made < n && tries < 4000; tries++) {
    const x = rng.int(1, g.W - 2), y = rng.int(1, g.H - 2), i = y * g.W + x;
    if (!pass[i] || occupied[i] || spawnDist(g, x, y) < 5) continue;
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
      setAll(g, line, HOLE);
      made++;
      break;
    }
  }
  return made;
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
export function randomOps(rng) {
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
  if (rng.chance(0.5)) ops.push(`picks=${rng.int(3, 5)}`);
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
function mutated(engine, source, seed, ops) {
  if (!ops?.length || source === 'random') {
    const rng = makeRng(`mutation:${seed}`);
    if (source === 'random') source = rng.choice(LADDER_NAMES());
    if (!ops?.length) ops = randomOps(rng);
  }
  const base = loadGrid(engine, source);
  base.access = LEVELS[naturalAccess(base)];
  base.gated = validate(base, { strict: false }).warnings.some(w => /past the camps|enclosed by/.test(w));
  const zone = ops.includes('altars=mid') ? 'mid' : null, baseDist = metrics(base).spawn_dist;
  for (let attempt = 0; attempt < 20; attempt++) {
    const rng = makeRng(`mutate:${source}:${seed}:${attempt}`), g = base.clone();
    g.access = base.access; g.gated = base.gated;
    try { mutate(g, rng, ops); } catch (e) { if (e instanceof GenFail) continue; throw e; }
    const { errors } = validate(g);
    if (errors.length) continue;
    const met = metrics(g);
    if (zone && met.altar_zone !== zone) continue;
    // Edits that open a short way between the spawns (walls to bush, doors) undo the map's design.
    if (met.spawn_dist < Math.min(18, baseDist)) continue;
    g.meta = { mutate: path.basename(source, '.map26a'), ops, seed, attempt, metrics: met };
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
function candidate(engine, { what, s, extra }) {
  try {
    const g = typeof what === 'string' ? generate(what, s, extra) : mutated(engine, what.mutate, s, what.ops);
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

// Seeds as a comma list with ranges: 3001,3005-3008.
const seedList = spec => String(spec).split(',').flatMap(r => { const [a, b = a] = r.split('-').map(Number); return Array.from({ length: b - a + 1 }, (_, k) => a + k); });

async function suite(opts) {
  const name = opts._[0] ?? 'gen', def = SUITES[name];
  if (!def) throw new Error(`unknown suite ${name}; one of ${Object.keys(SUITES).join(', ')}`);
  const seeds = seedList(opts.seed ?? def.seed), over = +(opts.oversample ?? 3);
  if (seeds.length > 1 && !opts.out?.includes('{seed}')) throw new Error('several seeds need --out with {seed}, e.g. maps/fresh-{seed}');
  // More than ~48 processes was slower on 96 cores (memory-bound, 2026-10-29): 10 suites in 9.2 s at 48, 10.3 at 94.
  const jobs = +(opts.jobs ?? Math.max(1, Math.min(48, os.availableParallelism() - 2))), tasks = [];
  for (const seed of seeds) for (const [idx, [what, n, extra]] of def.plan.entries())
    for (let j = 0; j < n * (typeof what === 'string' ? over : 2); j++) tasks.push({ seed, idx, what, extra, s: seed * 100000 + idx * 100 + j });
  const t0 = Date.now(), made = await makeCandidates(tasks, jobs), engine = await createEngine();
  console.log(`${tasks.length} candidates for ${seeds.length} suite(s) in ${((Date.now() - t0) / 1000).toFixed(1)} s in ${Math.min(jobs, tasks.length)} process(es)`);
  for (const seed of seeds) writeSuite(engine, def, seed, over, path.resolve(opts.out?.replaceAll('{seed}', seed) ?? path.join(ROOT, def.dir)),
    tasks.map((t, k) => [t, made[k]]).filter(([t]) => t.seed === seed));
}

function writeSuite(engine, def, seed, over, out, made) {
  fs.mkdirSync(out, { recursive: true });
  const index = [], files = new Map(), picks = [];
  for (const [idx, [what, n]] of def.plan.entries()) {
    const cands = [];
    for (const [t, r] of made) {
      if (t.idx !== idx) continue;
      if (r.skip) console.log(r.skip);
      else cands.push(r);
    }
    const picked = pickDiverse(cands, n);
    if (picked.length < n) console.log(`  warning: ${typeof what === 'string' ? what : what.mutate} produced ${picked.length}/${n}`);
    for (const g of picked) {
      files.set(`${g.name}.map26a`, g.bytes);
      const kind = typeof what === 'string' ? (PRESETS[what].designed ? 'designed' : EXOTIC_PRESETS.has(what) ? 'exotic' : 'ladder-like') : 'mutation';
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
  files.set('index.json', Buffer.from(JSON.stringify({ generator: 'tools/mapgen/mapgen.mjs suite', seed, oversample: over, maps: index }, null, 1) + '\n'));
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
  gen PRESET [--seed N] [--set k=v]... [--out FILE] [--show]
  mutate MAP|random [--seed N] [--op OP]... [--out FILE] [--show]   without --op the edits are drawn
      from the seed (random: the ladder map too). OP: walls|holes|bushes *F (F<1 removes whole
      chunks, F>1 stamps cover pieces), +N/-N (stamp/remove N pieces), K1~K2*F (turn a share F of
      K1's chunks into K2, e.g. walls~bushes*0.5), doors+N, gaps+N (dash-only cuts across narrow
      passages), vaults+N (wall a group or altar in: crystal only), camps *F (rescale distance from
      spawn), camps|altars +N/-N, econ=rich|poor|gold|gems (retype camps), picks=N, altars=mid
  suite [NAME] [--out DIR] [--seed S] [--oversample K] [--jobs N]   rebuild maps/gen (or NAME: gen-s1) from the PLAN
      (only changed files are rewritten); candidates in N processes (default 48, at most cores - 2). Several
      suites at once share the threads: --seed 3001-3004,3010 --out maps/fresh-{seed}
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
    try { g = cmd === 'gen' ? generate(name, seed, parseSet(opts.set)) : mutated(engine, name, seed, opts.op); }
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
