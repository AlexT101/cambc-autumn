// Per-map stats: draft-lab row (mapgen metrics + extras) plus altar, group (with bounding boxes) and side-group details,
// for compare.py (calibration 3, 2026-11-08).
//   node research/mapgen-calib3-tools/stats.mjs --set NAME --out FILE [--sample N --seed S] DIR_OR_FILE...
// Pass the ladder as maps/*.map26a: a directory is walked recursively.
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { Grid, ALTAR } from '../../tools/mapgen/grid.mjs';
import { spawnFields, sideGroups } from '../../tools/mapgen/generate.mjs';
import { createEngine } from '../../tools/mapgen/wasm.mjs';
import { mapRow, walk } from '../../tools/draftlab/features.mjs';

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..');
const args = process.argv.slice(2), inputs = [];
let set = 'x', out = null, sample = 0, seed = 1;
for (let i = 0; i < args.length; i++) {
  if (args[i] === '--set') set = args[++i]; else if (args[i] === '--out') out = args[++i];
  else if (args[i] === '--sample') sample = +args[++i]; else if (args[i] === '--seed') seed = +args[++i]; else inputs.push(args[i]);
}
let files = [];
for (const p of inputs) walk(p, files);
if (sample && files.length > sample) {
  let s = seed >>> 0; const rnd = () => (s = (s * 1664525 + 1013904223) >>> 0) / 2 ** 32;
  for (let i = files.length - 1; i > 0; i--) { const j = Math.floor(rnd() * (i + 1)); [files[i], files[j]] = [files[j], files[i]]; }
  files = files.slice(0, sample).sort();
}
const cheb = (ax, ay, bx, by) => Math.max(Math.abs(ax - bx), Math.abs(ay - by));
const engine = await createEngine(), lines = [];
let fail = 0;
for (const file of files) {
  try {
    const g = Grid.fromMap(engine.decode(fs.readFileSync(file)));
    const row = mapRow(g, path.relative(ROOT, fs.realpathSync(file)));
    const f = spawnFields(g, null, 0), cx = (g.W - 1) / 2, cy = (g.H - 1) / 2, half = Math.max(g.W, g.H) / 2;
    const sA = g.spawnTiles(0), sB = g.spawnTiles(1);
    const sDist = (ids, x, y) => Math.min(...ids.map(i => cheb(i % g.W, Math.floor(i / g.W), x, y)));
    const altars = [];
    for (let i = 0; i < g.t.length; i++) if (g.t[i] === ALTAR) {
      const x = i % g.W, y = (i - x) / g.W, dA = g.reachNear(f.dA, x, y), dB = g.reachNear(f.dB, x, y);
      altars.push({ self: g.mirror(i) === i, dA, dB, cA: sDist(sA, x, y), cB: sDist(sB, x, y), ctr: cheb(x, y, cx, cy) / half });
    }
    const groups = g.groups().map(q => ({ n: q.members.length, shared: q.shared, gems: q.gems, gold: q.gold,
      types: q.members.reduce((o, c) => (o[c.type] = (o[c.type] ?? 0) + 1, o), {}),
      bw: Math.max(...q.members.map(c => c.x)) - Math.min(...q.members.map(c => c.x)) + 1, bh: Math.max(...q.members.map(c => c.y)) - Math.min(...q.members.map(c => c.y)) + 1,
      sd: Math.min(...q.members.map(c => Math.min(sDist(sA, c.x, c.y), sDist(sB, c.x, c.y)))) }));
    const sg = sideGroups(g), side = [...sg.mine, ...sg.shared];
    const pure = q => q.members.every(c => c.type === 'gem_cluster');
    const side_groups = side.map(q => ({ n: q.members.length, shared: !!q.shared, pure_gem: pure(q), pure_gold: q.members.every(c => c.type === 'gold_cluster') }));
    const sp = g.spawn;
    lines.push(JSON.stringify({ ...row, setname: set, spawn_wh: `${Math.max(sp.w, sp.h)}x${Math.min(sp.w, sp.h)}`, altar_list: altars, group_list: groups, side_groups, camps_total: g.allCamps().length }));
  } catch (e) { console.error(`FAILED ${file}: ${e.message}`); fail++; }
}
fs.writeFileSync(out, lines.join('\n') + '\n');
console.log(`${set}: ${lines.length} maps -> ${out}; ${fail} failed`);
