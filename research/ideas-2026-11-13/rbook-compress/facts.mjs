// Map facts the live priority mask's game seed is made from (prio_stream::setup): symmetry, team A's spawn box and
// the camp groups, read from a replay.   node facts.mjs OUT.jsonl < lines "REPLAY KEY"
import fs from 'node:fs';
import { engineFor } from '../../../tools/replay/harness/inputs.mjs';
import { unwrapReplay, mirror } from '../../../tools/replay/engine.mjs';

const [out] = process.argv.slice(2);
const fd = fs.openSync(out, 'w');
for (const line of fs.readFileSync(0, 'utf8').trim().split('\n')) {
  const [file, key] = line.trim().split(/\s+/);
  try {
    const bytes = fs.readFileSync(file);
    const e = await engineFor(unwrapReplay(bytes));
    const g = e.openReplay(bytes);
    let map;
    try { map = g.map(); } finally { g.destroy(); }
    // Engine groups: cardinally connected camps over the canonical half and its mirror image.
    const tiles = new Map();
    for (const c of map.camps) {
      tiles.set(c.x * 1000 + c.y, 1);
      const [mx, my] = mirror(map, c.x, c.y);
      tiles.set(mx * 1000 + my, 1);
    }
    let components = 0;
    const seen = new Set();
    for (const t of tiles.keys()) {
      if (seen.has(t)) continue;
      components++;
      const stack = [t];
      seen.add(t);
      while (stack.length) {
        const u = stack.pop();
        for (const v of [u + 1000, u - 1000, u + 1, u - 1]) if (tiles.has(v) && !seen.has(v)) seen.add(v), stack.push(v);
      }
    }
    fs.writeSync(fd, JSON.stringify({ key, width: map.width, height: map.height, symmetry: map.symmetry, spawnA: map.spawnA,
      stored: map.groups.length, groups: components }) + '\n');
  } catch (err) { console.error('FAIL', file, err.message); }
}
fs.closeSync(fd);
