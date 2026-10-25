#!/usr/bin/env node
// Writes more_maps/edge_case/gauntlet.map26a: a 100x100 map built to be as hard as possible for a dash champion's
// pathing (bots/v0/src/path/dash.h). Rotationally symmetric; the engine's MapBuilder mirrors every edit,
// so only the bottom half (y <= 49) is drawn here.
//   ring road   x 0..2 and y 0..2 (and their mirrors) join everything; spawns in the corners
//   wall maze   bottom left, x 3..49: a serpentine of 1-wide corridors, about 1,000 tiles to walk, so
//               every distance field has very many layers (the engine prices a field per layer); a
//               column of hole windows at x = 26, two tiles apart, gives a dash route with a crossing
//               every second tile
//   hole comb   bottom right, y 3..23: corridors separated by rows of holes one tile thick; walking is
//               a serpentine, dashing crosses a row every second tile; long lines of opened holes touch
//   moats       bottom right, centre (73,36): four rings round a pocket, crossed by a hole window, a
//               solid ring of holes, an altar window and another hole window: four dashes in
//   trap        x 88..93, y 40..45: a walled box with one hole window holding a shape where the dash
//               field promises a way no move takes (opened holes that touch), so dash mode dead-ends
//               and the levels fallback has to run
//   node more_maps/edge_case/make-gauntlet.mjs
import fs from "node:fs";
import os from "node:os";
import path from "node:path";

const ROOT = path.resolve(path.dirname(new URL(import.meta.url).pathname), "../..");
const { Engine } = await import(path.join(ROOT, "tools/oarena/oarena/web/viewer/engine.js"));
const { DEFAULT_THEME } = await import(path.join(ROOT, "tools/oarena/oarena/web/editor/mapdoc.js"));
// The engine cambc's visualiser ships: the newest one in cambc's asset cache.
const ASSETS = path.join(os.homedir(), ".cache/cambc/assets");
const wasm = fs.readdirSync(ASSETS).map((d) => path.join(ASSETS, d, "visualiser/assets"))
  .filter((d) => fs.existsSync(d)).flatMap((d) => fs.readdirSync(d).filter((f) => f.endsWith(".wasm")).map((f) => path.join(d, f)))
  .sort((a, b) => fs.statSync(b).mtimeMs - fs.statSync(a).mtimeMs)[0];

const engine = await Engine.create(await WebAssembly.compile(fs.readFileSync(wasm)));
const { x, out } = engine;
const ROTATIONAL = 2; // MapBuilder_GetSymmetry: 0 horizontal, 1 vertical, 2 rotational
engine.check(x.MapBuilder_Create(100, 100, ROTATIONAL, out));
const map = engine.view.getBigUint64(out, true);
engine.check(x.MapBuilder_SetNumChampsPerTeam(map, 3));
// A new map's colours are all 0 (black ground); give it the stock ones, as the map editor does.
for (const [key, rgb] of Object.entries(DEFAULT_THEME)) if (!key.startsWith("BushTint")) engine.check(x[`MapBuilder_Set${key}`](map, rgb));
engine.check(x.MapBuilder_SetBushTintRange(map, DEFAULT_THEME.BushTintMin, DEFAULT_THEME.BushTintMax));
for (const [i, v] of [0, 0, 3, 3].entries()) engine.view.setInt32(engine.args + 4 * i, v, true); // far corner exclusive
engine.check(x.MapBuilder_SetTeamASpawnArea(map, engine.args));

const is = (kind, px, py) => { engine.check(x[`MapBuilder_Get${kind}`](map, px, py, out)); return engine.view.getUint32(out, true) !== 0; };
const ground = (px, py) => { for (const k of ["Bush", "Wall", "Hole", "Altar"]) engine.check(x[`MapBuilder_Remove${k}`](map, px, py)); };
const put = (kind) => (px, py) => { ground(px, py); engine.check(x[`MapBuilder_Add${kind}`](map, px, py)); };
const wall = put("Wall"), hole = put("Hole"), altar = put("Altar");
const box = (x0, y0, x1, y1, draw) => {
  for (let px = x0; px <= x1; px++) draw(px, y0), draw(px, y1);
  for (let py = y0; py <= y1; py++) draw(x0, py), draw(x1, py);
};

// Wall maze, bottom left.
box(3, 3, 49, 49, wall);
ground(3, 4); // the way in, from the road
for (let k = 0, y = 5; y <= 47; k++, y += 2) {
  for (let px = 4; px <= 48; px++) wall(px, y);
  ground(k % 2 ? 4 : 48, y); // serpentine: the gap alternates ends
  hole(26, y);               // a window every second row
}

// Hole comb, bottom right.
box(50, 3, 96, 23, wall);
ground(96, 4); // the way in, from the road
for (let k = 0, y = 5; y <= 21; k++, y += 2) {
  for (let px = 51; px <= 95; px++) hole(px, y);
  ground(k % 2 ? 51 : 95, y);
}

// Moats, bottom right above the comb.
box(50, 23, 96, 49, wall);
ground(96, 26); // the way in, from the road
box(62, 25, 84, 47, wall); hole(73, 25);   // ring 1: a hole window
box(65, 28, 81, 44, hole);                 // ring 2: solid holes
box(68, 31, 78, 41, wall); altar(78, 36);  // ring 3: an altar window
box(71, 34, 75, 38, wall); hole(73, 34);   // ring 4: a hole window; the pocket is x 72..74, y 35..37

// Trap: a walled box whose inside is the dead-end shape found by test-bots/dash-planner (rows from the
// top; X is where dash mode dead-ends, T the target it should still reach, O and o holes).
//   X # # .
//   O O # T
//   . O O #
//   o O . o
box(88, 40, 93, 45, wall);
const shape = ["X##.", "OO#T", ".OO#", "oO.o"];
shape.forEach((row, r) => [...row].forEach((c, i) => {
  const px = 89 + i, py = 44 - r;
  if (c === "#") wall(px, py);
  else if (c === "O" || c === "o") hole(px, py);
  else ground(px, py);
}));
hole(88, 44); // the one window, next to X, from the open ground at (87,44)

engine.check(x.MapBuilder_VerifyIntegrity(map));
engine.check(x.MapBuilder_Encode(map, engine.args, engine.args + 4));
const at = engine.view.getUint32(engine.args, true), size = engine.view.getUint32(engine.args + 4, true);
const target = path.join(ROOT, "more_maps/edge_case/gauntlet.map26a");
fs.writeFileSync(target, new Uint8Array(x.memory.buffer, at, size).slice());

let picture = "";
for (let py = 99; py >= 0; py--) {
  let row = "";
  for (let px = 0; px <= 99; px++) row += is("Wall", px, py) ? "#" : is("Hole", px, py) ? "o" : is("Altar", px, py) ? "A" : is("Bush", px, py) ? '"' : ".";
  picture += row + "\n";
}
fs.writeFileSync(path.join(ROOT, "more_maps/edge_case/gauntlet.txt"), picture);
console.log(`wrote ${path.relative(ROOT, target)} (${size} bytes) and more_maps/edge_case/gauntlet.txt (the map as text, north up)`);
