// Whether two replays play the same game step by step, priorities aside: every step but the
// priority sets (coded priorities change every round, so B may set one where A kept its value),
// by kind, actor, positions and round, and every champion's state after it. Prints the first
// difference, or "same" with the step count and each replay's priority sets. Exit 1 on a difference.
//   node tools/antire/same_play.mjs A.repl26a B.repl26a
import fs from 'node:fs';
import { Engine, compileEngine, replayEngine, unwrapReplay } from '../replay/engine.mjs';
const [fa, fb] = process.argv.slice(2);
const open = async f => {
  const bytes = unwrapReplay(fs.readFileSync(f));
  const e = await Engine.create(await compileEngine(replayEngine(bytes)));
  const g = e.openReplay(bytes);
  g.seekStart();
  return g;
};
const ga = await open(fa), gb = await open(fb);
const SET_PRIORITY = 9;
const sets = [0, 0];
// The next step that is not a priority set, as a key; null at the end.
const step = (g, i) => {
  for (;;) {
    const s = g.read(), h = s.header();
    if (h.step.kind !== SET_PRIORITY) {
      const { priority, inputPosition, substep, ...st } = h.step;
      const r = JSON.stringify([h.round, h.team, h.outcome, h.submittedGems, h.currentChampion, st, s.championsLite()]);
      return r;
    }
    sets[i]++;
    if (!g.next()) return null;
  }
};
let n = 0;
for (;;) {
  const a = step(ga, 0), b = step(gb, 1);
  if (a !== b) { console.log(`differ at step ${n}\nA ${a}\nB ${b}`); process.exit(1); }
  if (a === null) break;
  n++;
  const na = ga.next(), nb = gb.next();
  if (!na && !nb) break;
  if (!na || !nb) { console.log(`length differs at step ${n}`); process.exit(1); }
}
console.log(`same ${n} sets ${sets[0]} ${sets[1]}`);
