// node monomaps.mjs DIR... : prints basenames of maps holding a Monolith camp.
import fs from 'node:fs'; import path from 'node:path';
const { createEngine } = await import(path.resolve('tools/mapgen/wasm.mjs'));
const e = await createEngine();
for (const dir of process.argv.slice(2)) for (const f of fs.readdirSync(dir)) {
  if (!f.endsWith('.map26a')) continue;
  const m = e.decode(fs.readFileSync(path.join(dir, f)));
  const s = JSON.stringify(m.camps ?? m);
  if (/monolith/i.test(s)) console.log(f);
}
