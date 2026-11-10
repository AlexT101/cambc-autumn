import { CAMPS, mirror } from './engine.mjs';

export function buildMap(map, camps0) {
  // The engine's spawn max is exclusive.
  const a = { minX: map.spawnA.minX, minY: map.spawnA.minY, maxX: map.spawnA.maxX - 1, maxY: map.spawnA.maxY - 1 };
  const spawn = [a];
  const [bx0, by0] = mirror(map, a.minX, a.minY), [bx1, by1] = mirror(map, a.maxX, a.maxY);
  spawn.push({ minX: Math.min(bx0, bx1), minY: Math.min(by0, by1), maxX: Math.max(bx0, bx1), maxY: Math.max(by0, by1) });
  const centre = s => [(s.minX + s.maxX) / 2, (s.minY + s.maxY) / 2];
  const cheb = (a, b) => Math.max(Math.abs(a[0] - b[0]), Math.abs(a[1] - b[1]));
  const groups = [];
  camps0.forEach((c, i) => {
    const g = c.group;
    groups[g] ??= { id: g, camps: [], tiles: [] };
    groups[g].camps.push(i);
    groups[g].tiles.push([c.x, c.y]);
  });
  // A camp on the symmetry axis has no second runtime entry, so index shifts cannot join the two lists.
  const sourceAt = new Map(), runtimeAt = new Map(camps0.map(c => [`${c.x},${c.y}`, c]));
  for (const src of map.groups) for (const i of src.camps) {
    const c = map.camps[i];
    sourceAt.set(`${c.x},${c.y}`, src);
    sourceAt.set(mirror(map, c.x, c.y).join(','), src);
  }
  for (const g of groups) {
    const first = camps0[g.camps[0]], src = sourceAt.get(`${first.x},${first.y}`);
    const twin = runtimeAt.get(mirror(map, first.x, first.y).join(','));
    if (!src || !twin) throw new Error(`cannot match static or mirrored camp for group ${g.id}`);
    Object.assign(g, { types: g.camps.map(i => CAMPS[camps0[i].type]), gems: src.gems, gold: src.gold, respawn: src.respawn, mirror: twin.group });
    const c = g.tiles.reduce((a, t) => [a[0] + t[0] / g.tiles.length, a[1] + t[1] / g.tiles.length], [0, 0]);
    const d = spawn.map(s => cheb(c, centre(s)));
    g.side = d[0] < d[1] ? 0 : d[1] < d[0] ? 1 : -1;
  }
  return {
    width: map.width, height: map.height, symmetry: map.symmetry, champsPerTeam: map.champsPerTeam, spawn,
    walls: map.walls, holes: map.holes, bushes: map.bushes, altars: map.altars,
    camps: camps0.map((c, i) => ({ id: i, type: CAMPS[c.type], x: c.x, y: c.y, group: c.group, hp: c.maxHp })),
    groups,
  };
}

