#!/usr/bin/env node
// Writes more_maps/edge_case/golems.map26a: cambc 3.0.0's 00interlock with every other elk made a golem
// (camp type 5, new in 3.0.0), so golems stand alone and in groups with other monsters. No map of the
// 3.0.0 pool has a golem yet; bots and the viewer still have to handle them.
//   node more_maps/edge_case/make-golems.mjs
import fs from "node:fs";
import path from "node:path";
import { loadEngine, MapDoc, ROOT } from "../../tools/mapgen/engine.mjs";

const GOLEM = 5;
const engine = await loadEngine();
const doc = MapDoc.open(engine, new Uint8Array(fs.readFileSync(path.join(ROOT, "maps/00interlock.map26a"))));
const elks = doc.camps.filter((camp) => camp.type === 1);
elks.forEach((camp, k) => { if (k % 2 === 0) doc.setCamp(camp.x, camp.y, GOLEM); });
const { errors } = doc.problems();
if (errors.length) throw new Error(errors.map((e) => e.text).join("; "));
const bytes = doc.encode();
engine.openMap(bytes).destroy();  // loads as a game, as cambc run would
const target = path.join(ROOT, "more_maps/edge_case/golems.map26a");
fs.writeFileSync(target, bytes);
const golems = doc.camps.filter((camp) => camp.type === GOLEM).length;
console.log(`wrote ${path.relative(ROOT, target)} (${bytes.length} bytes) with ${engine.wasm}: ${golems} golems and their mirrors, `
  + `${elks.length - golems} elk left, ${doc.groups.length} groups`);
doc.destroy();
