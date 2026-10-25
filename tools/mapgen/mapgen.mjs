import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { ALTAR, BUSH, GROUND, Grid, HOLE, WALL, makeRng } from './grid.mjs';
import { BANDS, GenFail, PRESETS, TEMPLATES, candidates, connect, generate, metrics, sideGroups, spawnFields, stillConnected, tryGroup, validate } from './generate.mjs';
import { MapError, createEngine } from './wasm.mjs';

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..');

// The stored pool in maps/gen: [preset, count] or [{ mutate: map, ops }, count]. Each preset
// entry is oversampled and the most mutually different candidates kept. Altar placement is a
// dimension of every preset (altar_mode), so central-altar maps are spread over all of them.
const PLAN = [
  // Ladder-like: the competition-map preset, the older presets and mutations of ladder maps.
  ['classic', 14], ['small-brawl', 2], ['large-open', 2], ['maze', 3], ['caves', 3], ['many-camps', 2], ['lanes', 2], ['islands', 2],
  ['jungle', 3], ['monolith', 3], ['fortress', 2], ['rows', 2], ['altar-rich', 2], ['altar-poor', 2], ['contested-centre', 2],
  ['tiny', 2], ['huge', 2], ['random', 4], ['monolith-only', 2], ['shared-gems', 2],
  [{ mutate: 'ambush', ops: ['walls*0.6', 'camps*1.2', 'picks=4'] }, 1], [{ mutate: 'big-world', ops: ['holes*0.5', 'altars=mid', 'picks=4'] }, 1],
  [{ mutate: 'boss-battle', ops: ['walls*0.8', 'bushes+0.03', 'picks=4'] }, 1], [{ mutate: 'boss-battle', ops: ['walls*0.7', 'altars+2', 'picks=3'] }, 1],
  [{ mutate: 'broken-curve', ops: ['walls*0.6', 'altars=mid'] }, 1],
  [{ mutate: 'collision', ops: ['walls*0.6', 'camps*1.2', 'picks=4'] }, 1], [{ mutate: 'collision', ops: ['bushes*0.5', 'camps+3', 'altars=mid', 'picks=5'] }, 1],
  [{ mutate: 'concentrated-wealth', ops: ['walls*0.6', 'bushes*0.5', 'picks=4'] }, 1], [{ mutate: 'concentrated-wealth', ops: ['camps*1.3', 'altars=mid', 'picks=3'] }, 1],
  [{ mutate: 'contest', ops: ['walls*2', 'camps*1.2', 'picks=4'] }, 1],
  [{ mutate: 'corners', ops: ['holes*0', 'camps*0.8', 'altars=mid', 'picks=3'] }, 1], [{ mutate: 'corners', ops: ['bushes*2', 'camps*1.3'] }, 1],
  [{ mutate: 'corridors', ops: ['walls*0.6', 'picks=4'] }, 1], [{ mutate: 'eight', ops: ['camps+3', 'picks=4'] }, 1],
  [{ mutate: 'elk-arena', ops: ['walls*1.5', 'camps*1.2', 'picks=4'] }, 1],
  [{ mutate: 'elkring', ops: ['walls+0.04', 'picks=3'] }, 1], [{ mutate: 'elkring', ops: ['holes*0', 'camps+2', 'picks=4'] }, 1],
  [{ mutate: 'expanse', ops: ['altars-3', 'altars=mid', 'walls*0.6', 'picks=4'] }, 1], [{ mutate: 'fracture', ops: ['holes*0.5', 'camps*0.8', 'picks=4'] }, 1],
  [{ mutate: 'fragment', ops: ['holes*0.6', 'camps+2', 'picks=4'] }, 1],
  [{ mutate: 'gold-rush', ops: ['bushes*0.5', 'camps+2', 'picks=4'] }, 1], [{ mutate: 'gold-rush', ops: ['holes*0.5', 'altars=mid', 'picks=5'] }, 1],
  [{ mutate: 'hooks', ops: ['walls*1.4', 'camps+2', 'picks=3'] }, 1],
  [{ mutate: 'interlock', ops: ['walls*0.5', 'camps*1.2', 'picks=5'] }, 1], [{ mutate: 'interlock', ops: ['walls*1.6', 'altars=mid', 'picks=3'] }, 1],
  [{ mutate: 'islands', ops: ['camps*0.8', 'picks=4'] }, 1],
  [{ mutate: 'lanes', ops: ['camps+4', 'bushes*0.3'] }, 1], [{ mutate: 'lanes', ops: ['altars-5', 'altars=mid', 'camps*1.2'] }, 1],
  [{ mutate: 'monolith', ops: ['walls*0.5', 'camps+3'] }, 1], [{ mutate: 'monolith', ops: ['bushes*2', 'altars=mid', 'picks=4'] }, 1],
  [{ mutate: 'packs', ops: ['altars=mid', 'walls+0.03', 'picks=5'] }, 1], [{ mutate: 'rows', ops: ['walls*0.5', 'bushes*0.5'] }, 1],
  [{ mutate: 'stampede', ops: ['holes*0.5', 'bushes*0.5', 'picks=4'] }, 1],
  // Exotic playable-area shapes.
  ['round', 8], ['star', 6], ['diamond', 6], ['donut', 8], ['cross', 7], ['hourglass', 5], ['band', 4], ['archipelago', 7], ['chambers', 7], ['blob', 4],
  // Exotic interiors.
  ['labyrinth', 7], ['spiral', 5], ['pillars', 6], ['cells', 6], ['diagonals', 5], ['tunnels', 6], ['city', 6], ['serpentine', 5], ['open-field', 5], ['long-thin', 6],
  // Exotic spawn distances and economies.
  ['close-spawns', 6], ['far-spawns', 5],
  ['golem-heavy', 5], ['monolith-heavy', 4], ['gem-centre', 5], ['huge-shared', 6], ['tiny-groups', 4], ['sparse-camps', 4], ['dense-camps', 3], ['monsters-only', 2], ['clusters-only', 2],
];
const SUITES = { gen: { dir: 'maps/gen', plan: PLAN, seed: 1027 }, 'gen-s1': { dir: 'maps/gen-s1', plan: PLAN, seed: 1028 } };
const LADDER_DIR = path.join(ROOT, 'maps');
const EXOTIC_PRESETS = new Set(Object.entries(PRESETS).filter(([, v]) => v.exotic).map(([k]) => k));

// The metric space of `diversity`, the nearest-ladder distance and the diverse pick.
const FEATURES = {
  log_area: m => Math.log(m.area), aspect: m => m.aspect, reach_frac: m => m.reach_frac, walls: m => m.walls, holes: m => m.holes, bushes: m => m.bushes,
  spawn_rel: m => m.spawn_rel, detour: m => Math.min(m.detour, 4), choke_rel: m => m.choke_rel ?? 0, openness: m => m.openness, boundary: m => m.boundary, cramped: m => m.cramped,
  fill_corner: m => m.fill_corner, fill_centre: m => m.fill_centre, fill_edge: m => m.fill_edge,
  altars: m => Math.log(1 + m.altars), altar_ratio: m => m.altar_ratio ?? 0.5, groups: m => Math.log(1 + m.groups_side + m.shared_groups), camp_density: m => m.camp_density,
  log_gems: m => Math.log(1 + m.gems_side), big_share: m => m.big_share, shared_share: m => m.shared_share, cluster_share: m => m.cluster_share,
  camp_ratio: m => m.camp_ratio ?? 0.3, picks: m => m.picks,
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

function mutate(g, rng, ops) {
  for (const op of ops) {
    if (op === 'altars=mid') {
      // Moves every walkable altar pair (and self-mirrored altar) into the central band.
      const f = spawnFields(g), tiles = canonicalTiles(g, ALTAR).filter(i => g.reachNear(f.dA, i % g.W, Math.floor(i / g.W)) >= 0);
      for (const i of tiles) g.set(i % g.W, Math.floor(i / g.W), GROUND);
      for (let k = 0; k < tiles.length; k++) placeAltar(g, rng, BANDS.central);
      continue;
    }
    const m = /^(walls|holes|bushes|camps|altars|picks)([*+=-])([\d.]+)$/.exec(op);
    if (!m) throw new Error(`bad --op ${op}: use walls|holes|bushes|camps|altars with *F, +N or -N, picks=N or altars=mid`);
    const [, what, sign, num] = m, v = +num;
    if (what === 'picks') { g.picks = v; continue; }
    if (['walls', 'holes', 'bushes'].includes(what)) {
      const kind = { walls: WALL, holes: HOLE, bushes: BUSH }[what], tiles = canonicalTiles(g, kind);
      if (sign === '*' && v <= 1) for (const i of rng.shuffle(tiles).slice(0, Math.round(tiles.length * (1 - v)))) g.set(i % g.W, Math.floor(i / g.W), GROUND);
      else {
        const add = sign === '*' ? Math.round(tiles.length * (v - 1)) : sign === '+' ? Math.round(v * g.W * g.H / 2) : 0;
        if (sign === '-') for (const i of rng.shuffle(tiles).slice(0, Math.round(v * g.W * g.H / 2))) g.set(i % g.W, Math.floor(i / g.W), GROUND);
        const occupied = g.campMask(), spawn = new Set([...g.spawnTiles(0), ...g.spawnTiles(1)]);
        for (let n = 0, guard = 0; n < add && guard < add * 50; guard++) {
          const x = rng.int(0, g.W - 1), y = rng.int(0, g.H - 1), len = kind === BUSH ? rng.int(2, 4) : rng.int(2, 6), horiz = rng.chance(0.5);
          for (let k = 0; k < len; k++) {
            const xx = x + (horiz ? k : 0), yy = y + (horiz ? 0 : k), i = yy * g.W + xx;
            if (!g.in(xx, yy) || g.t[i] !== GROUND || occupied[i] || occupied[g.mirror(i)] || spawn.has(i) || spawn.has(g.mirror(i))) continue;
            if (Math.min(...[0, 1].map(team => Math.min(...g.spawnTiles(team).map(j => Math.max(Math.abs(j % g.W - xx), Math.abs(Math.floor(j / g.W) - yy)))))) <= 2) continue;
            g.set(xx, yy, kind); n++;
          }
        }
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
        const tpl = TEMPLATES[rng.choice(['wolf', 'wolf_pair', 'elk', 'elk_gold', 'gems', 'gold'])](rng), f = spawnFields(g);
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

function repair(g, rng) {
  connect(g, rng, MUT_SPEC);
  if (!stillConnected(g)) {
    const groups = campGroupsCanonical(g);
    g.camps = sharedCamps(g);
    for (const cells of groups) tryGroup(g, cells, MUT_SPEC);
  }
}

// Competition-map spawns that are not 3x3 or 4x4 (boss-battle's is 5x2, shortcut's 4x3) become the nearest such
// square, centred on the old one; camps under it move off.
function fixSpawn(g) {
  const s = g.spawn;
  if (s.w === s.h && (s.w === 3 || s.w === 4)) return;
  const n = s.w * s.h > 12 ? 4 : 3, x = Math.max(0, Math.min(g.W - n, Math.round(s.x + (s.w - n) / 2))), y = Math.max(0, Math.min(g.H - n, Math.round(s.y + (s.h - n) / 2)));
  g.spawn = { x, y, w: n, h: n };
  const tiles = new Set([...g.spawnTiles(0), ...g.spawnTiles(1)]);
  for (const i of tiles) if (g.t[i] !== GROUND && g.t[i] !== BUSH) g.t[i] = GROUND;
  g.camps = g.camps.filter(c => !tiles.has(c.y * g.W + c.x) && !tiles.has(g.mirror(c.y * g.W + c.x)));
}

function loadGrid(engine, file) {
  const name = file.endsWith('.map26a') ? file : `${file}.map26a`;
  const prefixed = fs.readdirSync(LADDER_DIR).find(f => f.replace(/^\d\d/, '') === name);
  const p = fs.existsSync(file) ? file : path.join(LADDER_DIR, prefixed ?? name);
  return Grid.fromMap(engine.decode(fs.readFileSync(p)));
}

// Teleport-only pockets of the source (vaults, dash-only islands) are first joined on foot, since
// generated maps keep every objective walkable.
function mutated(engine, source, seed, ops) {
  const base = loadGrid(engine, source), zone = ops.includes('altars=mid') ? 'mid' : null;
  fixSpawn(base);
  for (let attempt = 0; attempt < 20; attempt++) {
    const rng = makeRng(`mutate:${source}:${seed}:${attempt}`), g = base.clone();
    try { connect(g, rng, { ...MUT_SPEC, min_pocket: 1 }); mutate(g, rng, ops); } catch (e) { if (e instanceof GenFail) continue; throw e; }
    const { errors } = validate(g);
    if (errors.length) continue;
    const met = metrics(g);
    if (zone && met.altar_zone !== zone) continue;
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
  const chosen = [0];
  while (chosen.length < k) {
    let best = -1, bestD = -1;
    for (let i = 0; i < cands.length; i++) {
      if (chosen.includes(i)) continue;
      const d = Math.min(...chosen.map(j => norm[i].reduce((s, x, f) => s + (x - norm[j][f]) ** 2, 0)));
      if (d > bestD) { bestD = d; best = i; }
    }
    chosen.push(best);
  }
  return chosen.sort((a, b) => a - b).map(i => cands[i]);
}

async function suite(opts) {
  const name = opts._[0] ?? 'gen', def = SUITES[name];
  if (!def) throw new Error(`unknown suite ${name}; one of ${Object.keys(SUITES).join(', ')}`);
  const engine = await createEngine(), out = path.resolve(opts.out ?? path.join(ROOT, def.dir)), seed = +(opts.seed ?? def.seed), over = +(opts.oversample ?? 3);
  fs.mkdirSync(out, { recursive: true });
  const index = [], files = new Map(), picks = [];
  for (const [idx, [what, n, extra]] of def.plan.entries()) {
    const cands = [];
    for (let j = 0; j < n * (typeof what === 'string' ? over : 1); j++) {
      const s = seed * 100000 + idx * 100 + j;
      try {
        const g = typeof what === 'string' ? generate(what, s, extra) : mutated(engine, what.mutate, s, what.ops);
        g.name = typeof what === 'string' ? `gen-${what}-${s}` : `mut-${what.mutate}-${s}`;
        g.bytes = encode(engine, g);
        cands.push(g);
      } catch (e) {
        if (!(e instanceof GenFail) && !(e instanceof MapError)) throw e;
        console.log(`  skip ${typeof what === 'string' ? what : what.mutate}:${s}: ${e.message}`);
      }
    }
    const picked = pickDiverse(cands, n);
    if (picked.length < n) console.log(`  warning: ${typeof what === 'string' ? what : what.mutate} produced ${picked.length}/${n}`);
    for (const g of picked) {
      files.set(`${g.name}.map26a`, g.bytes);
      const kind = typeof what === 'string' ? (EXOTIC_PRESETS.has(what) ? 'exotic' : 'ladder-like') : 'mutation';
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
      outside_ladder_range: r2(outside.filter(n => n > 0).length / vs.length), features_sd: r2(vs[0].map((_, j) => Math.sqrt(vs.reduce((s, v) => s + v[j] ** 2, 0) / vs.length - (vs.reduce((s, v) => s + v[j], 0) / vs.length) ** 2)).reduce((s, x) => s + x, 0) / vs[0].length),
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
  mutate MAP [--seed N] --op OP [--op OP]... [--out FILE] [--show]
      OP: walls|holes|bushes *F (scale), +P/-P (add/remove fraction of the map), camps *F (rescale
      distance from spawn), camps|altars +N/-N, picks=N, altars=mid (move walkable altars to the centre)
  suite [NAME] [--out DIR] [--seed S] [--oversample K]   rebuild maps/gen (or NAME: gen-s1) from the PLAN (only changed files are rewritten)
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
    console.log(summary(cmd === 'gen' ? `gen-${name}-${seed}` : `mut-${path.basename(name, '.map26a')}-${seed}`, g.meta.metrics));
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

process.exitCode = await main();
