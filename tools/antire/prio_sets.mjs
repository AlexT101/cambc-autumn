// Every priority set in a replay, one per line: round, team (0 = A, 1 = B), champion index, value.
//   node tools/antire/prio_sets.mjs REPLAY
import fs from 'node:fs';
import { Engine, compileEngine, replayEngine, unwrapReplay } from '../replay/engine.mjs';
const bytes = unwrapReplay(fs.readFileSync(process.argv[2]));
const g = (await Engine.create(await compileEngine(replayEngine(bytes)))).openReplay(bytes);
g.seekStart();
const out = [];
do {
  const h = g.read().header();
  if (h.step.kind === 9) out.push(`${h.round} ${h.team} ${h.step.actor.index} ${h.step.priority}`);
} while (g.next());
process.stdout.write(out.join('\n') + '\n');
