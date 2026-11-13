// Per map: altars, the enemy's altar options (our_side from their spawn: their walk at most 2 longer than ours,
// to a tile beside the altar) and contested altars (on both sides). Symmetric maps: the same for either team.
// node altarsides.mjs DIR... > out.json
import fs from 'node:fs';
import path from 'node:path';
import { Grid, ALTAR } from '../../../tools/mapgen/grid.mjs';
import { spawnFields } from '../../../tools/mapgen/generate.mjs';
import { createEngine } from '../../../tools/mapgen/wasm.mjs';
const engine = await createEngine();
const out = {};
for (const dir of process.argv.slice(2))
  for (const x of fs.readdirSync(dir).filter(x => x.endsWith('.map26a'))) {
    const bytes = fs.readFileSync(path.join(dir, x));
    let g;
    try { engine.load(bytes); g = Grid.fromMap(engine.decode(bytes)); } catch (e) { continue; }
    const f = spawnFields(g, null, 0);
    let altars = 0, eopt = 0, contested = 0;
    for (let i = 0; i < g.t.length; i++) {
      if (g.t[i] !== ALTAR) continue;
      altars++;
      const ax = i % g.W, ay = (i - ax) / g.W;
      let dA = g.reachNear(f.dA, ax, ay), dB = g.reachNear(f.dB, ax, ay);
      const U = 1e9; if (dA < 0) dA = U; if (dB < 0) dB = U;
      const theirs = dB <= dA + 2, ours = dA <= dB + 2;
      eopt += theirs; contested += theirs && ours;
    }
    out[path.basename(x, '.map26a')] = { altars, eopt, contested };
  }
console.log(JSON.stringify(out));
