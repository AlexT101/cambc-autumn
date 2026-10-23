// Decodes a replay's input stream (every bot action the engine recorded, in order) plus a hash of the
// observer snapshot at each round start. The puppet generator and the fidelity check both use it.
//
//   node tools/replay/harness/inputs.mjs <replay.repl26a> [out.json]
import fs from 'node:fs';
import crypto from 'node:crypto';
import { fileURLToPath } from 'node:url';
import { Engine, compileEngine, replayEngine, unwrapReplay, STEP_KINDS, ITEMS, CONSUMABLES } from '../engine.mjs';

export const K = Object.fromEntries(STEP_KINDS.map((n, i) => [n, i]));
const NONE = 0xFFFFFFFF;

const engines = new Map();
export async function engineFor(bytes) {
  const v = replayEngine(bytes);
  if (!engines.has(v)) engines.set(v, Engine.create(await compileEngine(v)));
  return engines.get(v);
}

// Input record columns.
export const COLS = ['s', 'r', 'ip', 'kind', 'phase', 'actorKind', 'actor', 'fx', 'fy', 'tx', 'ty', 'slot', 'ab', 'pr', 'x1', 'x2'];
// x1/x2: Shop/Sell: item id, count (Shop: 100 + consumable id for a consumable). Consumable: consumable id, count. Attack/Cast: target kind
// (0 none/ground, 1 champion, 2 camp, 6 altar lock), target id (champion id, camp index, lock team).
// Movement blocked: x1 = what could block (see below).

export async function decodeInputs(bytes, { hashSteps = null } = {}) {
  bytes = unwrapReplay(bytes);
  const e = await engineFor(bytes);
  const g = e.openReplay(bytes);
  try {
    g.seekStart();
    const inputs = [], roundHashes = [];
    let s = 0, lastIp = -1, round = -1;
    let roster = null;
    const stepHashes = hashSteps ? [] : null;
    const snapBytes = () => new Uint8Array(e.x.memory.buffer, e.snap, e.snapshotSize);
    const hash = () => crypto.createHash('sha1').update(snapBytes()).digest('hex').slice(0, 16);
    let prevItems = null, prevCons = null, prevChamps = null, prevCamps = null, prevWards = null, prevFlags = null;
    do {
      const snap = g.read();
      const h = snap.header(), st = h.step;
      if (h.round !== round && h.phase !== 12) { roundHashes.push([h.round, s, hash()]); round = h.round; }
      if (stepHashes && s >= hashSteps[0] && s < hashSteps[1]) stepHashes.push([s, hash()]);
      if (!roster && h.phase !== 12 && st.phase !== 12) roster = snap.champions().map(c => ({ id: c.id, team: c.team, type: c.type }));
      if (st.inputPosition !== lastIp) {
        lastIp = st.inputPosition;
        const rec = [s, h.round, st.inputPosition, st.kind, st.phase, st.actor.kind, st.actor.index, st.from.x, st.from.y, st.to.x, st.to.y,
          st.abilitySlot ?? -1, st.abilityType ?? -1, st.priority, 0, 0];
        if (roster && st.actor.kind === 1) {
          const k = roster.findIndex(c => c.id === st.actor.index);
          if (st.kind === K.Shop || st.kind === K['Sell item']) {
            const items = snap.items(k), before = prevItems[k];
            // Shards sit at even ids, their emblem at the next id; five shards combine into one emblem.
            let best = -1, cnt = 0;
            for (let i = 0; i < items.length; i += 2) {
              const d = items[i] - before[i] + 5 * (items[i + 1] - before[i + 1]);
              if (st.kind === K.Shop && d > 0) { best = i; cnt = d; }
              if (st.kind === K['Sell item']) {
                if (items[i] < before[i]) { best = i; cnt = before[i] - items[i]; }
                if (items[i + 1] < before[i + 1]) { best = i + 1; cnt = before[i + 1] - items[i + 1]; }
              }
            }
            rec[14] = best; rec[15] = cnt;
            if (best < 0 && st.kind === K.Shop) {
              // Consumables are bought through the same step: 100 + consumable id.
              const cons = snap.consumables(k), cb = prevCons[k];
              for (let i = 0; i < cons.length; i++) if (cons[i] > cb[i]) { rec[14] = 100 + i; rec[15] = cons[i] - cb[i]; }
            }
          } else if (st.kind === K.Consumable) {
            const cons = snap.consumables(k), before = prevCons[k];
            for (let i = 0; i < cons.length; i++) if (cons[i] !== before[i]) { rec[14] = i; rec[15] = cons[i] - before[i]; }
          } else if (st.kind === K['Movement blocked']) {
            // The blocked action is not recorded: note what could have blocked it (1 a unit on the
            // tile, 2 an allied ward there) and 4 if the actor had already walked this turn.
            const team = roster[k].team;
            const unit = prevChamps.some(c => c.alive && c.x === st.to.x && c.y === st.to.y) || prevCamps.some(c => c.hp > 0 && c.x === st.to.x && c.y === st.to.y);
            const ward = prevWards.some(w => w.team === team && w.x === st.to.x && w.y === st.to.y);
            rec[14] = (unit ? 1 : 0) | (ward ? 2 : 0) | ((prevFlags[k] ?? 0) & 2048 ? 4 : 0);
          } else if (st.kind === K.Attack || st.kind === K['Cast ability']) {
            const tc = prevChamps.find(c => c.alive && c.x === st.to.x && c.y === st.to.y);
            if (tc) { rec[14] = 1; rec[15] = tc.id; }
            else {
              const ci = prevCamps.findIndex(c => c.hp > 0 && c.x === st.to.x && c.y === st.to.y);
              if (ci >= 0) { rec[14] = 2; rec[15] = ci; } else if (st.kind === K.Attack) { rec[14] = 6; rec[15] = -1; }
            }
          }
        }
        inputs.push(rec);
      }
      if (roster) {
        prevItems = roster.map((_, k) => snap.items(k));
        prevCons = roster.map((_, k) => snap.consumables(k));
        prevChamps = snap.championsLite();
        prevCamps = snap.camps().map(c => ({ hp: c.hp ?? 0, x: c.x, y: c.y }));
        prevWards = snap.wards();
        prevFlags = snap.champions().map(c => c.roundFlags);
      }
      s++;
    } while (g.next());
    const fin = g.read();
    const fh = fin.header();
    const draft = fin.draft();
    return {
      engine: replayEngine(bytes), steps: s, roster, draft, cols: COLS, inputs, roundHashes, stepHashes,
      result: { outcome: fh.outcome, round: fh.round, gems: fh.submittedGems }, finalHash: hash(),
    };
  } finally { g.destroy(); }
}

if (process.argv[1] && fileURLToPath(import.meta.url) === process.argv[1]) {
  const [file, out] = process.argv.slice(2);
  const t0 = performance.now();
  const d = await decodeInputs(fs.readFileSync(file));
  const kinds = {};
  for (const r of d.inputs) { const k = `${STEP_KINDS[r[3]]}@${r[4]}`; kinds[k] = (kinds[k] ?? 0) + 1; }
  console.error(`${d.steps} steps, ${d.inputs.length} inputs, ${d.roundHashes.length} rounds, ${(performance.now() - t0).toFixed(0)} ms`, kinds);
  if (out) fs.writeFileSync(out, JSON.stringify(d));
}
