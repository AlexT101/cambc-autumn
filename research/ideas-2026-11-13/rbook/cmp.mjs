// Compares a rerun's per-round state hashes with a live replay's (extract.mjs output or a replay).
//   node cmp.mjs LIVE(.repl26a|extract json line file) RERUN.repl26a
import fs from 'node:fs';
import { decodeInputs } from '../../../tools/replay/harness/inputs.mjs';
async function hashes(f) {
  if (f.endsWith('.jsonl')) { const r = JSON.parse(fs.readFileSync(f, 'utf8').split('\n')[0]); return { h: r.roundHashes, fin: r.finalHash, res: [r.rounds, r.outcome, r.gems] }; }
  const d = await decodeInputs(fs.readFileSync(f));
  return { h: d.roundHashes.map(x => x[2]), fin: d.finalHash, res: [d.result.round, d.result.outcome, d.result.gems] };
}
const [a, b] = await Promise.all(process.argv.slice(2, 4).map(hashes));
let first = -1;
for (let i = 0; i < Math.max(a.h.length, b.h.length); i++) if (a.h[i] !== b.h[i]) { first = i; break; }
console.log(JSON.stringify({ live: a.res, rerun: b.res, rounds: [a.h.length, b.h.length], firstDiff: first, finalSame: a.fin === b.fin }));
