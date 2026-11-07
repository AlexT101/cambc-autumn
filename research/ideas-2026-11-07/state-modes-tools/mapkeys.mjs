// Per map: name, W, H, wall count, altar sum (x*128+y), for modes.cc's hash.
import fs from 'node:fs';
import path from 'node:path';
import { createEngine } from '/home/ubuntu/cambc-autumn/tools/mapgen/wasm.mjs';
const engine = await createEngine();
const out = [];
for (const dir of process.argv.slice(3)) {
  for (const f of fs.readdirSync(dir).filter(x => x.endsWith('.map26a'))) {
    const m = engine.decode(fs.readFileSync(path.join(dir, f)));
    let s = 0; for (const [x, y] of m.altars) s += x * 128 + y;
    out.push({ map: f.replace(/\.map26a$/, ''), W: m.width, H: m.height, walls: m.walls.length, altars: s });
  }
}
fs.writeFileSync(process.argv[2], JSON.stringify(out));
console.log(out.length, out[0]);
