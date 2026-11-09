// Decode .map26a files to JSON (both halves: walls, holes, bushes, altars, camps mirrored), for the fork analysis.
//   node tools/combatlab/mapjson.mjs OUT.jsonl MAP...   (one {"file","width","height","symmetry","spawn":[A,B],...} line a map)
import fs from 'node:fs';
import path from 'node:path';
import { createEngine } from '../mapgen/wasm.mjs';

const [out, ...maps] = process.argv.slice(2);
const eng = await createEngine();
const lines = [];
for (const f of maps) {
  const d = eng.decode(fs.readFileSync(f));
  const W = d.width, H = d.height;
  const mir = ([x, y]) => d.symmetry === 'horizontal' ? [W - 1 - x, y] : d.symmetry === 'vertical' ? [x, H - 1 - y] : [W - 1 - x, H - 1 - y];
  const both = ts => { const s = new Set(); const o = []; for (const t of ts) for (const u of [t, mir(t)]) { const k = u[0] * 1000 + u[1]; if (!s.has(k)) { s.add(k); o.push(u); } } return o; };
  const a = d.spawn, c1 = mir([a.minX, a.minY]), c2 = mir([a.maxX, a.maxY]);
  const b = { minX: Math.min(c1[0], c2[0]), maxX: Math.max(c1[0], c2[0]), minY: Math.min(c1[1], c2[1]), maxY: Math.max(c1[1], c2[1]) };
  const camps = []; const seen = new Set();
  for (const c of d.camps) for (const u of [[c.x, c.y], mir([c.x, c.y])]) { const k = u[0] * 1000 + u[1]; if (!seen.has(k)) { seen.add(k); camps.push({ type: c.type, x: u[0], y: u[1] }); } }
  lines.push(JSON.stringify({ file: path.basename(f, '.map26a'), width: W, height: H, symmetry: d.symmetry, picks: d.picks, spawn: [a, b],
    walls: both(d.walls), holes: both(d.holes), bushes: both(d.bushes), altars: both(d.altars), camps }));
}
fs.writeFileSync(out, lines.join('\n') + '\n');
