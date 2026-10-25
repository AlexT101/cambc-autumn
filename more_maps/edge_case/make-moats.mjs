#!/usr/bin/env node
// Writes more_maps/edge_case/moats.map26a: `packs` with two walls the full height of the map, x = 13 and x = 17,
// each with a single hole at y = 15. The two halves are joined only by dashing over both holes; nothing
// can walk across.
//   node more_maps/edge_case/make-moats.mjs
import fs from "node:fs";
import os from "node:os";
import path from "node:path";

const ROOT = path.resolve(path.dirname(new URL(import.meta.url).pathname), "../..");
const { Engine } = await import(path.join(ROOT, "tools/oarena/oarena/web/viewer/engine.js"));
// The engine cambc's visualiser ships: the newest one in cambc's asset cache.
const ASSETS = path.join(os.homedir(), ".cache/cambc/assets");
const wasm = fs.readdirSync(ASSETS).map((d) => path.join(ASSETS, d, "visualiser/assets"))
  .filter((d) => fs.existsSync(d)).flatMap((d) => fs.readdirSync(d).filter((f) => f.endsWith(".wasm")).map((f) => path.join(d, f)))
  .sort((a, b) => fs.statSync(b).mtimeMs - fs.statSync(a).mtimeMs)[0];

const engine = await Engine.create(await WebAssembly.compile(fs.readFileSync(wasm)));
const { x, out } = engine;
const source = new Uint8Array(fs.readFileSync(path.join(ROOT, "maps/00packs.map26a")));
const map = engine.withBytes(source, (p, n) => { engine.check(x.MapBuilder_FromFileBytes(p, n, out)); return engine.view.getBigUint64(out, true); });
const is = (kind, px, py) => { engine.check(x[`MapBuilder_Get${kind}`](map, px, py, out)); return engine.view.getUint32(out, true) !== 0; };
const ground = (px, py) => { for (const k of ["Bush", "Wall", "Hole", "Altar"]) engine.check(x[`MapBuilder_Remove${k}`](map, px, py)); };
const wall = (px, py) => { ground(px, py); engine.check(x.MapBuilder_AddWall(map, px, py)); };
const hole = (px, py) => { ground(px, py); engine.check(x.MapBuilder_AddHole(map, px, py)); };

// Two walls the full height of the map, x = 13 and x = 17 (the second is the first's mirror image), each
// with one hole at y = 15: the halves are joined only by two dashes four tiles apart.
for (let y = 0; y <= 30; y++) if (y !== 15) wall(13, y);
hole(13, 15);
for (const [gx, gy] of [[12, 15], [14, 15], [12, 14], [14, 14], [12, 16], [14, 16]]) ground(gx, gy);
engine.check(x.MapBuilder_VerifyIntegrity(map));
engine.check(x.MapBuilder_Encode(map, engine.args, engine.args + 4));
const at = engine.view.getUint32(engine.args, true), size = engine.view.getUint32(engine.args + 4, true);
const target = path.join(ROOT, "more_maps/edge_case/moats.map26a");
fs.writeFileSync(target, new Uint8Array(x.memory.buffer, at, size).slice());

let picture = "";
for (let py = 25; py >= 5; py--) {
  let row = "";
  for (let px = 10; px <= 20; px++) row += is("Wall", px, py) ? "#" : is("Hole", px, py) ? "o" : is("Bush", px, py) ? '"' : ".";
  picture += `  y=${String(py).padStart(2)} ${row}\n`;
}
console.log(`wrote ${path.relative(ROOT, target)} (${size} bytes); x = 10..20, north up:\n${picture}`);
