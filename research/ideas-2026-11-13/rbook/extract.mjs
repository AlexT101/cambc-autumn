// Decodes replays into book entries: both teams' recorded turns per body, picks, and the map id.
//   node extract.mjs OUT.jsonl REPLAY[:SIDE] ...   (SIDE = our side a|b; the opponent's team is kept too)
// Lines on stdin (one "replay side key" per line) when no replays are given.
import fs from 'node:fs';
import zlib from 'node:zlib';
import { decodeInputs, K, engineFor } from '../../../tools/replay/harness/inputs.mjs';
import { unwrapReplay, mirror } from '../../../tools/replay/engine.mjs';

const A = { MOVE: 1, ATTACK: 2, CAST: 3, PRIORITY: 4, RECALL: 5, SUBMIT: 6, BUY: 7, SELL: 8, BUY_CONS: 9, WARD: 10, CANCEL: 11, LOCK: 12, TELEPORT: 13, BLOCKED: 14, RESIGN: 15, USE_CONS: 16 };
const B = { move: 1, dash: 2, ward: 3, teleport: 4 };
const order = (...w) => w.reduce((acc, x, i) => acc | (B[x] << (4 * i)), 0);
function blockedOrder(r) { // as gen_puppet.mjs
  const flags = r[14], dist = Math.max(Math.abs(r[7] - r[9]), Math.abs(r[8] - r[10]));
  const w = [];
  if ((flags & 2) && dist <= 2) w.push('ward');
  if (dist === 1 && !(flags & 4)) w.push('move');
  if (dist <= 2) w.push('dash');
  if (dist <= 3) w.push('teleport');
  return order(...w);
}

const M64 = (1n << 64n) - 1n;
export function splitmix(x) {
  let z = (BigInt(x) + 0x9E3779B97F4A7C15n) & M64;
  z = ((z ^ (z >> 30n)) * 0xBF58476D1CE4E5B9n) & M64;
  z = ((z ^ (z >> 27n)) * 0x94D049BB133111EBn) & M64;
  return z ^ (z >> 31n);
}
// Must equal book.cc's layout_hash: order-free over the camps (type, tile) with their group's gems and gold, so maps
// that share terrain but not camps (edited ladder maps) differ. The map holds the canonical half: each camp also
// stands at its mirror tile, in a group with the same gems and gold, as the engine (and so the SDK's layout) has it.
export function layoutHash(map) {
  let s = 0n;
  const term = (type, x, y, g) => splitmix((BigInt(type & 255) << 56n) | (BigInt(x & 255) << 48n) | (BigInt(y & 255) << 40n) |
    (BigInt(g.gems & 0xFFFFF) << 20n) | BigInt(g.gold & 0xFFFFF));
  for (const g of map.groups) {
    for (const c of g.camps) {
      const k = map.camps[c], [mx, my] = mirror(map, k.x, k.y);
      s = (s + term(k.type, k.x, k.y, g)) & M64;
      if (mx !== k.x || my !== k.y) s = (s + term(k.type, mx, my, g)) & M64;
    }
  }
  return splitmix(s);
}

// Must equal book.cc's map_id: order-free over the wall, bush, hole and altar tiles (SDK map masks 0-3).
export function mapId(map) {
  const W = map.width;
  let s = splitmix(W * 1024 + map.height), n = 0n;
  ['walls', 'bushes', 'holes', 'altars'].forEach((k, kind) => {
    for (const [x, y] of map[k]) s = (s + splitmix((BigInt(kind) << 40n) + BigInt(y * W + x + 1))) & M64;
    n = (n << 16n) + BigInt(map[k].length);
  });
  return splitmix((s + n) & M64);
}

function teamTurns(d, team) {
  const ids = d.roster.filter(c => c.team === team).map(c => c.id).sort((a, b) => a - b);
  const turns = new Map(), roll = new Set(), problems = [];
  for (const r of d.inputs) {
    const [s, round, , kind, phase, actorKind, actor] = r;
    if (phase !== 10 || actorKind !== 1 || !ids.includes(actor)) continue;
    const [tx, ty] = [r[9], r[10]];
    let a;
    switch (kind) {
      case K.Move: a = [A.MOVE, tx, ty, 0, 0]; break;
      case K.Attack: a = [A.ATTACK, tx, ty, r[14], 0]; break;
      case K['Cast ability']: a = [A.CAST, tx, ty, r[11], r[14]]; break;
      case K['Set priority']: a = [A.PRIORITY, 0, 0, r[13], 0]; break;
      case K.Recall: a = [A.RECALL, 0, 0, 0, 0]; break;
      case K['Submit gems']: a = [A.SUBMIT, tx, ty, 0, 0]; break;
      case K.Shop:
        if (r[14] < 0) problems.push(`s${s}: shop with no item change`);
        a = r[14] >= 100 ? [A.BUY_CONS, 0, 0, r[14] - 100, r[15]] : [A.BUY, 0, 0, r[14], r[15]];
        break;
      case K['Sell item']: a = [A.SELL, 0, 0, r[14], r[15]]; break;
      case K.Consumable: a = [A.USE_CONS, tx, ty, r[14], 0]; problems.push(`s${s}: Consumable step`); break;
      case K['Place ward']: a = [A.WARD, tx, ty, 0, 0]; break;
      case K['Cancel channel']: a = [A.CANCEL, 0, 0, 0, 0]; break;
      case K['Place altar lock']: a = [A.LOCK, tx, ty, 0, 0]; break;
      case K['Teleport channel']: a = [A.TELEPORT, tx, ty, 0, 0]; break;
      case K['Movement blocked']: a = [A.BLOCKED, tx, ty, blockedOrder(r), 0]; break;
      case K.Resign: a = [A.RESIGN, 0, 0, 0, 0]; break;
      case K['Turn rollover']: roll.add(round * 64 + actor); continue;
      case K['End turn']: continue;
      case K['Bot error']: problems.push(`s${s}: Bot error`); continue;
      default: problems.push(`s${s}: unhandled kind ${kind}`); continue;
    }
    const key = round * 64 + actor;
    if (!turns.has(key)) turns.set(key, []);
    turns.get(key).push(a);
  }
  const last = d.result.round;
  const bodies = ids.map(id => {
    const t = [];
    for (let round = 1; round <= last; round++) {
      const key = round * 64 + id;
      t.push([roll.has(key) ? 1 : 0, turns.get(key) ?? []]);
    }
    return { id, turns: t };
  });
  return { bodies, picks: d.draft.picks[team].slice(0, d.draft.counts[team]), problems };
}

export async function extract(file, side, key) {
  let bytes = fs.readFileSync(file);
  if (file.endsWith('.zip')) throw new Error('unzip first');
  const d = await decodeInputs(bytes);
  const e = await engineFor(unwrapReplay(bytes));
  const g = e.openReplay(bytes);
  let map;
  try { map = g.map(); } finally { g.destroy(); }
  const team = side === 'a' ? 0 : 1;
  const ours = teamTurns(d, team), opp = teamTurns(d, 1 - team);
  return {
    key, side, width: map.width, height: map.height, map_id: mapId(map).toString(16).padStart(16, '0'),
    counts: ['walls', 'bushes', 'holes', 'altars'].map(k => map[k].length), layout: layoutHash(map).toString(16).padStart(16, '0'),
    rounds: d.result.round, outcome: d.result.outcome, gems: d.result.gems,
    ours: { picks: ours.picks, bodies: ours.bodies }, opp: { picks: opp.picks, bodies: opp.bodies },
    problems: [...ours.problems.map(p => 'ours ' + p), ...opp.problems.map(p => 'opp ' + p)],
    roundHashes: d.roundHashes.map(h => h[2]), finalHash: d.finalHash,
  };
}

if (process.argv[1] && process.argv[1].endsWith('extract.mjs')) {
  const [out, ...args] = process.argv.slice(2);
  const jobs = args.length ? args.map(a => a.split(':')) : fs.readFileSync(0, 'utf8').trim().split('\n').map(l => l.trim().split(/\s+/));
  const fd = fs.openSync(out, 'w');
  for (const [file, side, key] of jobs) {
    try {
      const r = await extract(file, side ?? 'a', key ?? file);
      fs.writeSync(fd, JSON.stringify(r) + '\n');
      if (r.problems.length) console.error(key, r.problems.slice(0, 5));
    } catch (err) { console.error('FAIL', file, err.message); }
  }
  fs.closeSync(fd);
}
