// Scratch: dump raw step headers of a replay.
import fs from 'node:fs';
import { Engine, compileEngine, replayEngine, STEP_KINDS, PHASES } from '../engine.mjs';
const [file, from = '0', to = '300'] = process.argv.slice(2);
const bytes = fs.readFileSync(file);
const e = await Engine.create(await compileEngine(replayEngine(bytes)));
const g = e.openReplay(bytes);
g.seekStart();
let s = 0;
do {
  if (s >= +from && s < +to) {
    const h = g.read().header();
    const st = h.step;
    console.log(s, `r${h.round} t${h.turn} team${h.team} ph${h.phase} cur${h.currentChampion} in${h.inputPosition}`, '|', STEP_KINDS[st.kind] ?? st.kind, `ph${st.phase}`, `actor${st.actor.kind}:${st.actor.index}`, `f(${st.from.x},${st.from.y}) to(${st.to.x},${st.to.y})`, `r${st.round} ip${st.inputPosition} sub${st.substep} slot${st.abilitySlot} ab${st.abilityType} pr${st.priority}`);
  }
  s++;
  if (s >= +to) break;
} while (g.next());
