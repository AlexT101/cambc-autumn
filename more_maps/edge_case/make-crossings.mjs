#!/usr/bin/env node
// Writes more_maps/edge_case/crossings.map26a: `packs` with a wall down x = 15 from y = 4 to 26 and three
// holes in it, each crossable by one dash shape only. Walking round the wall's ends is long.
//   (15,8)   knight-shaped only: (14,8) -> (16,9)
//   (15,12)  corner to corner on one side only: (14,13) -> (16,13), the wall (15,13) between them
//   (15,15)  straight and diagonal, the usual window
// The map is rotationally symmetric and the engine's MapBuilder mirrors every edit, so each hole has
// a twin: (15,22), (15,18) and (15,15) itself.
//   node more_maps/edge_case/make-crossings.mjs
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

const holes = [[15, 8], [15, 12], [15, 15]];
for (let y = 4; y <= 15; y++) if (!holes.some(([hx, hy]) => hx === 15 && hy === y)) wall(15, y);
for (const [hx, hy] of holes) hole(hx, hy);
for (const [wx, wy] of [[14, 7], [14, 9], [16, 7], [16, 8]]) wall(wx, wy);   // knight only at (15,8)
for (const [wx, wy] of [[14, 11], [14, 12], [16, 11], [16, 12]]) wall(wx, wy); // one side only at (15,12)
for (const [gx, gy] of [[14, 8], [16, 9], [14, 13], [16, 13], [14, 14], [16, 14], [14, 15], [16, 15], [14, 16], [16, 16]]) ground(gx, gy);

engine.check(x.MapBuilder_VerifyIntegrity(map));
engine.check(x.MapBuilder_Encode(map, engine.args, engine.args + 4));
const at = engine.view.getUint32(engine.args, true), size = engine.view.getUint32(engine.args + 4, true);
const target = path.join(ROOT, "more_maps/edge_case/crossings.map26a");
fs.writeFileSync(target, new Uint8Array(x.memory.buffer, at, size).slice());

let picture = "";
for (let py = 25; py >= 5; py--) {
  let row = "";
  for (let px = 11; px <= 19; px++) row += is("Wall", px, py) ? "#" : is("Hole", px, py) ? "o" : is("Bush", px, py) ? '"' : ".";
  picture += `  y=${String(py).padStart(2)} ${row}\n`;
}
console.log(`wrote ${path.relative(ROOT, target)} (${size} bytes); x = 11..19, north up:\n${picture}`);
