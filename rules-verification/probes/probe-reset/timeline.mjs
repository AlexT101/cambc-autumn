// Prints the engine's own capture state for a replay: every step that changes a cleared group's
// (state, capture team, capture timer), and every step that moves a champion onto or off a group tile.
//   node rules-verification/probes/probe-reset/timeline.mjs <replay.repl26a>
import fs from 'node:fs';
import { Engine, STEP_KINDS, PHASES, GROUP_STATES, compileEngine, replayEngine } from '../../../tools/replay/engine.mjs';

const bytes = fs.readFileSync(process.argv[2]);
const e = await Engine.create(await compileEngine(replayEngine(bytes)));
const g = e.openReplay(bytes);
const NONE = 0xFFFFFFFF;
const team = t => ['A', 'B', '-'][t] ?? t;
let prev = null, prevPos = new Map(), groupTiles = null;
g.seekStart();
do {
  const s = g.read(), h = s.header();
  if (h.phase === 12) continue;
  const camps = s.camps(), groups = s.groups(), champs = s.championsLite();
  if (!groupTiles) {
    groupTiles = new Map();
    camps.forEach(c => groupTiles.set(`${c.x},${c.y}`, c.group));
  }
  const where = `r=${h.round} t=${h.turn === NONE ? '-' : h.turn} ${PHASES[h.step.phase] ?? h.step.phase}/${STEP_KINDS[h.step.kind] ?? h.step.kind} actor=${h.step.actor.index === NONE ? '-' : h.step.actor.index}`;
  const on = gi => champs.filter(c => c.alive && groupTiles.get(`${c.x},${c.y}`) === gi).map(c => `${c.id}${team(c.team)}@${c.x},${c.y}`).join(' ') || '-';
  for (const c of champs) {
    const p = prevPos.get(c.id), k = `${c.x},${c.y}`;
    if (p && p !== k && (groupTiles.has(p) || groupTiles.has(k)) && c.alive) {
      const gi = groupTiles.get(k) ?? groupTiles.get(p);
      if (groups[gi].state !== 1) console.log(`${where} move ${c.id}${team(c.team)} ${p}->${k} g${gi} on=[${on(gi)}]`);
    }
    prevPos.set(c.id, k);
  }
  groups.forEach((q, gi) => {
    const p = prev?.[gi];
    if (!p || q.state === 1 && p.state === 1) return;
    if (p.state === q.state && p.captureTeam === q.captureTeam && p.captureTimer === q.captureTimer && (q.state === 3 || p.respawn === q.respawn)) return;
    const gold = q.state === 3 && p.state === 2 ? ' gold=' + champs.map(c => `${c.id}:${c.gold}/${c.gems}`).join(',') : '';
    console.log(`${where} g${gi} ${GROUP_STATES[q.state]} team=${team(q.captureTeam)} timer=${q.captureTimer} respawn=${q.respawn} on=[${on(gi)}]${gold}`);
  });
  prev = groups;
} while (step());

function step() {
  try { return g.next(); } catch (err) { if (/end of timeline/i.test(err.message)) return false; throw err; }
}
