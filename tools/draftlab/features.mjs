// Map features and keys for the draft lab: one JSON line per map.
//   node tools/draftlab/features.mjs DIR_OR_FILE... [--out replays/draftlab/maps.jsonl]
// The key is what the trainer vehicle computes in its draft (trainer.h map_key): it must match bit
// for bit, so change both together. Maps that fail to decode or measure are reported, not written.
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { ALTAR, BUSH, HOLE, WALL, Grid } from '../mapgen/grid.mjs';
import { metrics, spawnFields } from '../mapgen/generate.mjs';
import { createEngine, CAMP_TYPES } from '../mapgen/wasm.mjs';

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..');
const M64 = (1n << 64n) - 1n;

function mix(z) {
  z = (z + 0x9E3779B97F4A7C15n) & M64;
  z = ((z ^ (z >> 30n)) * 0xBF58476D1CE4E5B9n) & M64;
  z = ((z ^ (z >> 27n)) * 0x94D049BB133111EBn) & M64;
  return z ^ (z >> 31n);
}

// Order-independent over camps, since the engine's camp handles need not follow the file's order.
export function mapKey(g) {
  const count = k => BigInt(g.t.reduce((n, t) => n + (t === k), 0));
  let h = mix(BigInt(g.W));
  for (const v of [BigInt(g.H), count(WALL), count(BUSH), count(HOLE), count(ALTAR)]) h = mix(h ^ v);
  const camps = g.allCamps();
  let sum = 0n;
  for (const c of camps) sum = (sum + mix(BigInt(CAMP_TYPES.indexOf(c.type)) | BigInt(c.x) << 8n | BigInt(c.y) << 16n)) & M64;
  h = mix(h ^ sum);
  return mix(h ^ BigInt(camps.length)).toString(16).padStart(16, '0');
}

// Features beyond mapgen's metrics: big camp groups (splash and area stuns), altar centrality and
// dash shortcuts (tiles a dash brings 6+ travel nearer team A's spawn, or reaches at all).
function extras(g) {
  const groups = g.groups(), camps = g.allCamps().length;
  const big = groups.filter(q => q.members.length >= 3);
  const cx = (g.W - 1) / 2, cy = (g.H - 1) / 2, half = Math.max(g.W, g.H) / 2;
  const altars = [];
  for (let i = 0; i < g.t.length; i++) if (g.t[i] === ALTAR) altars.push(Math.max(Math.abs(i % g.W - cx), Math.abs(Math.floor(i / g.W) - cy)) / half);
  const walk = spawnFields(g, null, 0).dA, dash = spawnFields(g, null, 1).dA;
  let reach = 0, short = 0, only = 0;
  for (let i = 0; i < walk.length; i++) {
    if (walk[i] >= 0) { reach++; if (dash[i] >= 0 && walk[i] - dash[i] >= 6) short++; }
    else if (dash[i] >= 0 && g.t[i] !== WALL) only++;
  }
  return {
    walkable: reach, big_groups: big.length,
    big_camp_share: camps ? big.reduce((n, q) => n + q.members.length, 0) / camps : 0,
    max_group: Math.max(0, ...groups.map(q => q.members.length)),
    altar_centre: altars.length ? altars.reduce((a, b) => a + b, 0) / altars.length : null,
    dash_short: reach ? short / reach : 0, dash_only: reach ? only / reach : 0,
  };
}

// One maps.jsonl row: the model's features are f's FEATURES (model.mjs).
export function mapRow(g, rel) {
  const m = metrics(g), key = mapKey(g);
  const { size, spawn, types, sym, picks, access, altar_zone, ...num } = m;
  return { path: rel, name: path.basename(rel, '.map26a'), set: path.dirname(rel), key, picks, sym, W: g.W, H: g.H,
    access, ...indexInfo(rel), f: { ...num, ...extras(g) } };
}

export function walk(p, out) {
  const st = fs.statSync(p);
  if (st.isDirectory()) for (const f of fs.readdirSync(p).sort()) walk(path.join(p, f), out);
  else if (p.endsWith('.map26a')) out.push(p);
}

// mapgen's index.json (kind, preset) for maps of generated suites.
const indexes = new Map();
function indexInfo(file) {
  file = path.resolve(ROOT, file);
  const dir = path.dirname(file);
  if (!indexes.has(dir)) {
    let m = new Map();
    try { for (const e of JSON.parse(fs.readFileSync(path.join(dir, 'index.json'), 'utf8')).maps) m.set(e.file, e); } catch { /* no index */ }
    indexes.set(dir, m);
  }
  const e = indexes.get(dir).get(path.basename(file));
  return e ? { kind: e.kind, preset: e.preset } : {};
}

async function main() {
  const args = process.argv.slice(2), inputs = [];
  let out = path.join(ROOT, 'replays', 'draftlab', 'maps.jsonl');
  for (let i = 0; i < args.length; i++) if (args[i] === '--out') out = path.resolve(args[++i]); else inputs.push(args[i]);
  if (!inputs.length) { console.error('usage: node tools/draftlab/features.mjs DIR_OR_FILE... [--out FILE]'); return 2; }
  const files = [];
  for (const p of inputs) walk(path.resolve(ROOT, p), files);
  const engine = await createEngine(), lines = [], keys = new Map();
  let failed = 0;
  for (const file of files) {
    const rel = path.relative(ROOT, file).split(path.sep).join('/');
    try {
      const row = mapRow(Grid.fromMap(engine.decode(fs.readFileSync(file))), rel), key = row.key;
      // So far always a mutation whose edits changed nothing (ladder_nn dist 0).
      if (keys.has(key)) { console.error(`same key as ${keys.get(key)}: ${rel} (skipped)`); failed++; continue; }
      keys.set(key, rel);
      lines.push(JSON.stringify(row));
    } catch (e) {
      console.error(`FAILED ${rel}: ${e.message}`);
      failed++;
    }
  }
  fs.mkdirSync(path.dirname(out), { recursive: true });
  fs.writeFileSync(out, lines.join('\n') + '\n');
  console.log(`${lines.length} maps -> ${path.relative(ROOT, out)}; ${failed} skipped`);
  return 0;
}

// Run as a script, not imported (native.mjs); Windows paths compare case-insensitively.
if (process.argv[1] && path.resolve(process.argv[1]).toLowerCase() === fileURLToPath(import.meta.url).toLowerCase()) process.exitCode = await main();
