import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { ALTAR, BUSH, GROUND, Grid, HOLE, WALL, makeRng } from './grid.mjs';
import { BANDS, GenFail, PRESETS, TEMPLATES, candidates, connect, generate, markVaults, metrics, sideGroups, spawnFields, stillConnected, tryGroup, validate } from './generate.mjs';
import { createEngine } from './wasm.mjs';

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..');

// The stored pool in maps/gen: [preset, count] or [{ mutate: map, ops }, count].
const PLAN = [
  ['small-brawl', 3], ['large-open', 2], ['maze', 3], ['caves', 3], ['many-camps', 2], ['lanes', 3], ['islands', 2],
  ['jungle', 2], ['monolith', 2], ['fortress', 2], ['rows', 2], ['altar-rich', 2], ['altar-poor', 2], ['contested-centre', 2],
  ['vaults', 2], ['tiny', 1], ['huge', 1], ['random', 4],
  [{ mutate: 'expanse', ops: ['walls*0.3', 'camps*1.4'] }, 1], [{ mutate: 'rows', ops: ['walls*0.5', 'bushes*0.5'] }, 1],
  [{ mutate: 'monolith', ops: ['camps*0.7', 'picks=3'] }, 1], [{ mutate: 'interlock', ops: ['walls*1.6', 'altars-1'] }, 1],
  [{ mutate: 'lanes', ops: ['camps+4', 'bushes*0.3'] }, 1], [{ mutate: 'corners', ops: ['holes*0', 'camps*0.8', 'picks=4'] }, 1],
  [{ mutate: 'collision', ops: ['camps*1.3', 'altars+2', 'picks=5'] }, 1], [{ mutate: 'elkring', ops: ['walls+0.06', 'picks=3'] }, 1],
  ['classic', 12],
  // Second half: appended, since seeds follow plan position and the first half must not change.
  ['small-brawl', 3], ['large-open', 2], ['maze', 3], ['caves', 3], ['many-camps', 2], ['lanes', 3], ['islands', 2],
  ['jungle', 2], ['monolith', 2], ['fortress', 2], ['rows', 2], ['altar-rich', 2], ['altar-poor', 2], ['contested-centre', 2],
  ['vaults', 2], ['tiny', 1], ['huge', 1], ['random', 4],
  [{ mutate: 'packs', ops: ['walls*1.5', 'camps*1.2', 'picks=4'] }, 1], [{ mutate: 'expanse', ops: ['bushes*2', 'altars-1', 'picks=5'] }, 1],
  [{ mutate: 'monolith', ops: ['walls*0.5', 'camps+3'] }, 1], [{ mutate: 'interlock', ops: ['camps*0.7', 'picks=3'] }, 1],
  [{ mutate: 'lanes', ops: ['walls*0.5', 'altars+2', 'picks=3'] }, 1], [{ mutate: 'corners', ops: ['bushes*2', 'camps*1.3'] }, 1],
  [{ mutate: 'collision', ops: ['walls*0.6', 'camps*0.8', 'picks=4'] }, 1], [{ mutate: 'elkring', ops: ['camps*1.3', 'bushes*0.5', 'picks=4'] }, 1],
  ['classic', 12],
  // Gems only from a monolith per side, or only from one shared group (ladder maps contest, stampede).
  ['monolith-only', 4], [{ mutate: 'contest', ops: ['walls*2', 'camps*1.2', 'picks=4'] }, 1], [{ mutate: 'contest', ops: ['camps*0.8', 'bushes+0.04'] }, 1],
  ['shared-gems', 4], [{ mutate: 'stampede', ops: ['holes*0.5', 'bushes*0.5', 'picks=4'] }, 1], [{ mutate: 'stampede', ops: ['camps*1.3', 'walls+0.03', 'picks=3'] }, 1],
];
// maps/gen-central: every spawn's nearest altar in the middle zone (0.4-0.6 of the walk between
// spawns), as on the ladder maps collision, corners, elkring, interlock and monolith.
// Presets are generated with altar_zone=mid; entries may add a third element of overrides.
const CENTRAL_PLAN = [
  [{ mutate: 'collision', ops: ['walls*0.6', 'camps*1.2', 'picks=4'] }, 1], [{ mutate: 'collision', ops: ['bushes*0.5', 'camps+3', 'picks=5'] }, 1],
  [{ mutate: 'collision', ops: ['walls*1.5', 'camps*0.8'] }, 1],
  [{ mutate: 'elkring', ops: ['walls+0.04', 'picks=3'] }, 1], [{ mutate: 'elkring', ops: ['holes*0', 'camps+2', 'picks=4'] }, 1],
  [{ mutate: 'elkring', ops: ['bushes*3', 'camps*1.3'] }, 1],
  [{ mutate: 'interlock', ops: ['walls*0.5', 'camps*1.2', 'picks=5'] }, 1], [{ mutate: 'interlock', ops: ['walls*1.6', 'picks=3'] }, 1],
  [{ mutate: 'interlock', ops: ['bushes*2', 'camps+3'] }, 1],
  [{ mutate: 'monolith', ops: ['walls*0.5', 'camps*0.8', 'picks=3'] }, 1], [{ mutate: 'monolith', ops: ['walls*1.5', 'camps+3', 'picks=4'] }, 1],
  [{ mutate: 'monolith', ops: ['bushes*2', 'altars-1'] }, 1],
  [{ mutate: 'corners', ops: ['holes*0', 'camps*0.8', 'picks=3'] }, 1], [{ mutate: 'corners', ops: ['walls+0.04', 'bushes*2', 'picks=4'] }, 1],
  [{ mutate: 'corners', ops: ['camps*1.3', 'altars-1'] }, 1],
  [{ mutate: 'expanse', ops: ['altars-3', 'altars=mid', 'walls*0.6', 'picks=4'] }, 1], [{ mutate: 'lanes', ops: ['altars-5', 'altars=mid', 'camps*1.2'] }, 1],
  [{ mutate: 'packs', ops: ['altars=mid', 'walls+0.03', 'picks=5'] }, 1], [{ mutate: 'rows', ops: ['altars=mid', 'walls*0.6', 'picks=3'] }, 1],
  ['classic', 6], ['small-brawl', 2], ['tiny', 1], ['maze', 2], ['caves', 1], ['monolith', 2], ['contested-centre', 2], ['altar-poor', 1],
  ['jungle', 1], ['fortress', 1], ['islands', 1], ['vaults', 1],
  ['monolith-only', 2], [{ mutate: 'contest', ops: ['walls+0.04', 'camps*1.3', 'picks=4'] }, 1],
  ['shared-gems', 2], [{ mutate: 'stampede', ops: ['camps*0.8', 'holes*0', 'picks=5'] }, 1],
];
const SUITES = {
  gen: { dir: 'maps/gen', plan: PLAN, seed: 3107 },
  central: { dir: 'maps/gen-central', plan: CENTRAL_PLAN, seed: 3108, zone: 'mid' },
};
const FEATURES = ['area', 'reach_frac', 'walls', 'holes', 'bushes', 'spawn_dist', 'detour', 'choke', 'openness', 'altars', 'groups_side', 'gems_side', 'camp_ratio', 'picks'];

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

function loadGrid(engine, file) {
  const p = fs.existsSync(file) ? file : path.join(ROOT, 'maps', file.endsWith('.map26a') ? file : `${file}.map26a`);
  return Grid.fromMap(engine.decode(fs.readFileSync(p)));
}

function mutated(engine, source, seed, ops, zone) {
  const base = markVaults(loadGrid(engine, source));
  for (let attempt = 0; attempt < 20; attempt++) {
    const rng = makeRng(`mutate:${source}:${seed}:${attempt}`), g = mutate(base.clone(), rng, ops);
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
  const vec = cands.map(c => FEATURES.map(f => +(c.meta.metrics[f] ?? 0)));
  const lo = FEATURES.map((_, j) => Math.min(...vec.map(v => v[j]))), hi = FEATURES.map((_, j) => Math.max(...vec.map(v => v[j])));
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
  const index = [], files = new Map(), overrides = def.zone ? { altar_zone: def.zone } : {};
  for (const [idx, [what, n, extra]] of def.plan.entries()) {
    const cands = [];
    for (let j = 0; j < n * (typeof what === 'string' ? over : 1); j++) {
      const s = seed * 100000 + idx * 100 + j;
      try {
        const g = typeof what === 'string' ? generate(what, s, { ...overrides, ...extra }) : mutated(engine, what.mutate, s, what.ops, def.zone);
        g.name = typeof what === 'string' ? `gen-${what}-${s}` : `mut-${what.mutate}-${s}`;
        g.bytes = encode(engine, g);
        cands.push(g);
      } catch (e) {
        if (!(e instanceof GenFail)) throw e;
        console.log(`  skip ${typeof what === 'string' ? what : what.mutate}:${s}: ${e.message}`);
      }
    }
    const picked = pickDiverse(cands, n);
    if (picked.length < n) console.log(`  warning: ${typeof what === 'string' ? what : what.mutate} produced ${picked.length}/${n}`);
    for (const g of picked) {
      files.set(`${g.name}.map26a`, g.bytes);
      index.push({ file: `${g.name}.map26a`, ...g.meta, spec: g.meta.spec && Object.fromEntries(Object.entries(g.meta.spec).filter(([k]) => !['camp_mix', 'altar_bands'].includes(k))) });
      console.log(summary(g.name, g.meta.metrics));
    }
  }
  // Other runs may be reading the pool: replace only changed files, each by an atomic rename.
  files.set('index.json', Buffer.from(JSON.stringify({ generator: `tools/mapgen/mapgen.mjs suite${name === 'gen' ? '' : ` ${name}`}`, seed, oversample: over, maps: index }, null, 1) + '\n'));
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

const USAGE = `usage: node tools/mapgen/mapgen.mjs <command>
  list                                       presets
  gen PRESET [--seed N] [--set k=v]... [--out FILE] [--show]
  mutate MAP [--seed N] --op OP [--op OP]... [--out FILE] [--show]
      OP: walls|holes|bushes *F (scale), +P/-P (add/remove fraction of the map), camps *F (rescale
      distance from spawn), camps|altars +N/-N, picks=N, altars=mid (move walkable altars to the centre)
  suite [gen|central] [--out DIR] [--seed S] [--oversample K]   rebuild a stored pool: maps/gen, or
      maps/gen-central (nearest altars central)
  check FILE... [--show] [--json]           validate maps (any .map26a) and print metrics
  show FILE                                  ASCII view (1/2 spawns, # wall, o hole, " bush, A altar, camps lowercase as stored, uppercase their mirrors)`;

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
