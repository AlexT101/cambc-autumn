// Camp-group features (campfeat, 2026-11-08): per map, one JSON line {path, key, f: {...}}.
//   node research/ideas-2026-11-08/campfeat-tools/campfeat.mjs --list FILE_OF_PATHS [--out OUT.jsonl] [--groups]
//   node research/ideas-2026-11-08/campfeat-tools/campfeat.mjs DIR_OR_FILE... [--out OUT.jsonl]
// Counts are per side: team A's groups (sideGroups) plus the shared ones.
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { BUSH, CAMP, GROUND, WALL, Grid } from '../../../tools/mapgen/grid.mjs';
import { sideGroups } from '../../../tools/mapgen/generate.mjs';
import { createEngine } from '../../../tools/mapgen/wasm.mjs';
import { mapKey, walk } from '../../../tools/draftlab/features.mjs';

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../../..');
const HP = { wolf: 1350, elk: 2400, golem: 5000, gem_cluster: 120, gold_cluster: 120, monolith: 20000 };
const STR = { wolf: 20, elk: 60, golem: 120, gem_cluster: 0, gold_cluster: 0, monolith: 200 };
const R = 8;

// Symmetric shadowcasting (Albert Ford), clipped to the Chebyshev radius R square. Out of bounds is opaque.
function fov(g, ox, oy, opaque, mark) {
  mark(ox, oy);
  const T = [(r, c) => [ox + c, oy - r], (r, c) => [ox + c, oy + r], (r, c) => [ox + r, oy + c], (r, c) => [ox - r, oy + c]];
  for (const tr of T) {
    const wall = (r, c) => { const [x, y] = tr(r, c); return !g.in(x, y) || opaque(x, y); };
    const scan = (depth, s0, s1) => {
      if (depth > R) return;
      const lo = Math.floor(depth * s0 + 0.5), hi = Math.ceil(depth * s1 - 0.5);
      let prev = null; // null, 'w', 'f'
      for (let c = lo; c <= hi; c++) {
        const w = wall(depth, c);
        if (w || (c >= depth * s0 && c <= depth * s1)) { const [x, y] = tr(depth, c); if (g.in(x, y)) mark(x, y); }
        if (prev === 'w' && !w) s0 = (2 * c - 1) / (2 * depth);
        if (prev === 'f' && w) scan(depth + 1, s0, (2 * c - 1) / (2 * depth));
        prev = w ? 'w' : 'f';
      }
      if (prev === 'f') scan(depth + 1, s0, s1);
    };
    scan(1, -1, 1);
  }
}

// Whether one ground tile sees every member tile (a champion standing there can watch the whole group).
function seenFromOne(g, q, camp) {
  const xs = q.members.map(c => c.x), ys = q.members.map(c => c.y);
  const x0 = Math.max(...xs) - R, x1 = Math.min(...xs) + R, y0 = Math.max(...ys) - R, y1 = Math.min(...ys) + R;
  if (x0 > x1 || y0 > y1) return false;
  const opaque = (x, y) => { const t = g.t[y * g.W + x]; return t === WALL || t === BUSH; };
  const need = new Set(q.members.map(c => c.y * g.W + c.x));
  for (let y = Math.max(0, y0); y <= Math.min(g.H - 1, y1); y++) for (let x = Math.max(0, x0); x <= Math.min(g.W - 1, x1); x++) {
    if (g.t[y * g.W + x] !== GROUND || camp[y * g.W + x]) continue;
    let n = 0;
    const seen = new Set();
    fov(g, x, y, opaque, (a, b) => { const i = b * g.W + a; if (need.has(i) && !seen.has(i)) { seen.add(i); n++; } });
    if (n === need.size) return true;
  }
  return false;
}

export function campFeatures(g, withGroups = false) {
  const { mine, shared } = sideGroups(g), side = [...mine, ...shared], camp = g.campMask();
  const has = (q, t) => q.members.some(c => c.type === t);
  const info = side.map(q => {
    const hp = q.members.reduce((s, c) => s + HP[c.type], 0), str = q.members.reduce((s, c) => s + STR[c.type], 0);
    const heavy = has(q, 'golem') || has(q, 'monolith'), val = q.gems + q.gold / 10;
    const compact = seenFromOne(g, q, camp);
    return { n: q.members.length, gems: q.gems, gold: q.gold, hp, str, heavy, compact, shared: q.shared,
      gc: q.members.filter(c => c.type === 'gem_cluster').length, oc: q.members.filter(c => c.type === 'gold_cluster').length,
      // reward per kill time, with ~1000 HP of fixed cost (walk in, hold 6 rounds)
      rate: val / ((hp + 1000) / 1000), val };
  });
  const gemG = info.filter(q => q.gc > 0).length, goldG = info.filter(q => q.oc > 0).length;
  const light = info.filter(q => q.compact && !q.heavy);
  // "One big ball worth taking": seen whole from one tile, no Golem or Monolith, >= 40 gem-equivalents (gold / 10)
  // at >= 12 per 1000 HP of kill time.
  const big = light.filter(q => q.val >= 40 && q.rate >= 12 && q.n >= 3), total = info.reduce((s, q) => s + q.val, 0);
  const f = {
    gem_groups: gemG, one_gem_group: +(gemG === 1), gold_groups: goldG, one_gold_group: +(goldG === 1),
    hv_compact: +(big.length > 0),
    hv_rate: Math.max(0, ...light.filter(q => q.val >= 10).map(q => q.rate)),
    hv_val: Math.max(0, ...light.map(q => q.val)),
    hv_share: total ? Math.max(0, ...light.map(q => q.val)) / total : 0,
    compact_share: info.length ? info.filter(q => q.compact).length / info.length : 0,
  };
  return withGroups ? { f, groups: info } : { f };
}

async function main() {
  const a = process.argv.slice(2), inputs = [];
  let out = null, list = null, groups = false;
  for (let i = 0; i < a.length; i++) {
    if (a[i] === '--out') out = a[++i]; else if (a[i] === '--list') list = a[++i]; else if (a[i] === '--groups') groups = true; else inputs.push(a[i]);
  }
  const files = list ? fs.readFileSync(list, 'utf8').split('\n').filter(Boolean).map(p => path.resolve(ROOT, p)) : [];
  for (const p of inputs) walk(path.resolve(ROOT, p), files);
  const engine = await createEngine(), lines = [];
  for (const file of files) {
    const rel = path.relative(ROOT, file).split(path.sep).join('/');
    try {
      const g = Grid.fromMap(engine.decode(fs.readFileSync(file)));
      lines.push(JSON.stringify({ path: rel, key: mapKey(g), W: g.W, H: g.H, ...campFeatures(g, groups) }));
    } catch (e) { console.error(`FAILED ${rel}: ${e.message}`); }
  }
  const text = lines.join('\n') + '\n';
  if (out) fs.writeFileSync(out, text); else process.stdout.write(text);
}
if (process.argv[1] && fs.realpathSync(process.argv[1]) === fileURLToPath(import.meta.url)) await main();
