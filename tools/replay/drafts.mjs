// Each replay's draft, read by stepping through the draft phase only (~0.004 s a game; extract.mjs plays whole games).
//   node tools/replay/drafts.mjs <file listing .repl26a paths, one a line>   ->   path<TAB>team A picks<TAB>team B picks
// For a batch, split the list and run several in parallel (40,960 games: 3.3 s on 16 processes).
import fs from 'node:fs';
import { Engine, compileEngine, replayEngine, DRAFT_CHAMPIONS } from './engine.mjs';

const files = fs.readFileSync(process.argv[2], 'utf8').split('\n').filter(Boolean);
const engines = {};
for (const f of files) {
  const bytes = fs.readFileSync(f);
  const v = replayEngine(bytes);
  engines[v] ??= await Engine.create(await compileEngine(v));
  const g = engines[v].openReplay(bytes);
  g.seekStart();
  let snap;
  do {
    snap = g.read();
    const h = snap.header();
    if (!(h.phase === 12 || h.step.phase === 12)) break;
  } while (g.next());
  const d = snap.draft();
  const names = t => d.picks[t].slice(0, d.counts[t] || d.numRounds).map(i => DRAFT_CHAMPIONS[i] ?? i).join(',');
  process.stdout.write(`${f}\t${names(0)}\t${names(1)}\n`);
  g.destroy();
}
