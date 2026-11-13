// Map ids (extract.mjs's mapId) of every map file given; reports collisions.   node mapids.mjs [--full] MAP... > ids.json
// --full: per map {id, w, h, counts} (counts: walls, bushes, holes, altars), what book.cc's start() tests.
import fs from 'node:fs';
import { Engine, compileEngine } from '../../../tools/replay/engine.mjs';
import { mapId, layoutHash } from './extract.mjs';
const e = await Engine.create(await compileEngine());
const ids = {}, seen = new Map();
const args = process.argv.slice(2), full = args[0] === '--full';
for (const f of full ? args.slice(1) : args) {
  const g = e.openMap(fs.readFileSync(f));
  try {
    const m = g.map(), id = mapId(m).toString(16).padStart(16, '0');
    ids[f] = full ? { id, layout: layoutHash(m).toString(16).padStart(16, '0'), w: m.width, h: m.height, counts: ['walls', 'bushes', 'holes', 'altars'].map(k => m[k].length) } : id; if (seen.has(id)) console.error('COLLISION', id, seen.get(id), f); seen.set(id, f); } finally { g.destroy(); }
}
console.log(JSON.stringify(ids));
console.error(Object.keys(ids).length, 'maps,', seen.size, 'distinct ids');
