#!/usr/bin/env node
// Writes two maps with as many camps as a map can hold: 250 and their mirrors, the map editor's limit.
//   max-camps-singles.map26a  50x50, rotate 180°: 500 camps, each a group of its own. Team A's sit on
//                             the tiles where x and y are both even, so no two touch side to side;
//                             their mirrors land where both are odd. Every odd row and column is open.
//   max-camps-group.map26a    40x40, mirror left/right: one group of 500. A 10x25 block of camps
//                             against the axis (x = 10-19, y = 8-32) touches its mirror (x = 20-29),
//                             and camps that touch are one group, across the axis too.
// Camp types go round wolf, elk, gem cluster, gold cluster, monolith: 100 of each in both maps.
//   node more_maps/edge_case/make-max-camps.mjs
import fs from "node:fs";
import path from "node:path";
import { CAMP_TYPES, loadEngine, MapDoc, ROOT } from "../../tools/mapgen/engine.mjs";

const engine = await loadEngine();

function write(name, doc) {
  const { errors } = doc.problems();
  if (errors.length) throw new Error(`${name}: ${errors.map((e) => e.text).join("; ")}`);
  const bytes = doc.encode();
  engine.openMap(bytes).destroy();  // loads as a game, as cambc run would
  const target = path.join(ROOT, `more_maps/edge_case/${name}.map26a`);
  fs.writeFileSync(target, bytes);
  const sizes = doc.groups.map((group) => group.camps.length);
  const gems = doc.groups.reduce((sum, group) => sum + group.gems, 0);
  console.log(`wrote ${path.relative(ROOT, target)} (${bytes.length} bytes): ${doc.camps.length} camps and their mirrors, `
    + `${doc.groups.length} groups listed (largest ${Math.max(...sizes)} of team A's), ${gems} gems in all listed groups`);
}

// 500 groups of one.
{
  const doc = MapDoc.create(engine, { width: 50, height: 50, symmetry: 2, champions: 5 });
  doc.setSpawn(1, 1, 3, 3);
  const spots = [];
  for (let y = 0; y < 50; y += 2) {
    for (let x = 0; x < 50; x += 2) if (x + y < 49 && !(x <= 4 && y <= 4)) spots.push([x, y]);
  }
  // Spread the 250 evenly over team A's half.
  const chosen = Array.from({ length: 250 }, (_, k) => spots[Math.floor((k * spots.length) / 250)]);
  chosen.forEach(([x, y], k) => doc.setCamp(x, y, k % CAMP_TYPES.length));
  doc.setTile(25, 26, "altar");  // and its mirror (24, 23): neither is a camp tile
  write("max-camps-singles", doc);
  doc.destroy();
}

// One group of 500.
{
  const doc = MapDoc.create(engine, { width: 40, height: 40, symmetry: 0, champions: 5 });
  doc.setSpawn(1, 18, 3, 20);
  let k = 0;
  for (let y = 8; y <= 32; y++) for (let x = 10; x <= 19; x++) doc.setCamp(x, y, k++ % CAMP_TYPES.length);
  doc.setTile(15, 36, "altar");  // and its mirror (24, 36), below the block
  write("max-camps-group", doc);
  doc.destroy();
}
