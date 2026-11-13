// As cmp.mjs, for a book that plays plain priorities (build_book.py --prio plain): compares every input row of the two
// replays in order (so the turn order too), with the values of team SIDE's own set-priority rows left out.
//   node cmp2.mjs LIVE.repl26a RERUN.repl26a SIDE(a|b)
import fs from 'node:fs';
import { decodeInputs, K } from '../../../tools/replay/harness/inputs.mjs';
const side = process.argv[4] === 'b' ? 1 : 0;
async function rows(f) {
  const d = await decodeInputs(fs.readFileSync(f));
  const ours = new Set(d.roster.filter(c => c.team === side).map(c => c.id));
  const out = d.inputs.map(r => {
    const x = r.slice();
    if (x[3] === K['Set priority'] && x[5] === 1 && ours.has(x[6])) x[13] = 0;
    return [x[1], JSON.stringify(x)];
  });
  return { out, res: [d.result.round, d.result.outcome, d.result.gems] };
}
const [a, b] = await Promise.all(process.argv.slice(2, 4).map(rows));
let first = -1;
for (let i = 0; i < Math.max(a.out.length, b.out.length); i++)
  if (!a.out[i] || !b.out[i] || a.out[i][1] !== b.out[i][1]) { first = (a.out[i] ?? b.out[i])[0]; break; }
console.log(JSON.stringify({ live: a.res, rerun: b.res, rows: [a.out.length, b.out.length], firstDiff: first, finalSame: JSON.stringify(a.res) === JSON.stringify(b.res) }));
