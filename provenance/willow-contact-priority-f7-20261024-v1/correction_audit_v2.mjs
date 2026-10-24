import fs from 'node:fs';
import crypto from 'node:crypto';
import { Engine, compileEngine, replayEngine, CHAMPIONS, unwrapReplay } from '../../tools/replay/engine.mjs';

const inputs = process.argv.slice(2);
if (!inputs.length) throw new Error('pass labeled replay paths as label=path');
function digest(b) { return crypto.createHash('sha256').update(b).digest('hex'); }

const output = { schema: 'contact-priority-correction-audit/v2', replays: {}, comparisons: {} };
for (const arg of inputs) {
  const eq = arg.indexOf('=');
  const label = arg.slice(0, eq), file = arg.slice(eq + 1);
  const bytes = fs.readFileSync(file);
  const version = replayEngine(bytes);
  const payload = unwrapReplay(bytes);
  const engine = await Engine.create(await compileEngine(version));
  const game = engine.openReplay(bytes);
  game.seekStart();
  const item = { file, inner_replay_length: payload.length, inner_replay_sha256: digest(payload), engine: version,
    priority_step_count: 0, willow_priority_steps: 0, willow_target13_steps: 0,
    willow_target13_alive_after_step: 0, willow_target13_dead_after_step: 0, willow_steps: [],
    native_step_header_sha256: null, native_step_count: 0 };
  const traceHash = crypto.createHash('sha256');
  do {
    const snap = game.read();
    const h = snap.header();
    const st = h.step;
    traceHash.update(JSON.stringify(h));
    traceHash.update('\n');
    item.native_step_count++;
    if (st.kind !== 9) continue;
    item.priority_step_count++;
    if (st.actor.kind !== 1) continue;
    const champs = snap.champions();
    const actor = champs.find(c => c.id === st.actor.index);
    if (!actor || actor.type !== CHAMPIONS.indexOf('Willow')) continue;
    item.willow_priority_steps++;
    if (st.priority !== 13) continue;
    item.willow_target13_steps++;
    if (actor.alive) item.willow_target13_alive_after_step++;
    else item.willow_target13_dead_after_step++;
    item.willow_steps.push({ round: h.round, step_round: st.round, team: actor.team, champion_id: actor.id,
      alive_after_step: actor.alive, resulting_priority: actor.priority, step_priority: st.priority });
  } while (game.next());
  item.native_step_header_sha256 = traceHash.digest('hex');
  game.destroy();
  output.replays[label] = item;
}

const pairs = [
  ['candidate-elkring-B', 'parent-elkring-B', 'Elkring candidate-B vs parent-B'],
  ['candidate-pilgrimage-A', 'parent-pilgrimage-A', 'Pilgrimage candidate-A vs parent-A'],
  ['candidate-gold-rush-A', 'parent-gold-rush-A', 'Gold Rush candidate-A vs existing parent-A control'],
];
for (const [a, b, label] of pairs) {
  if (output.replays[a] && output.replays[b]) output.comparisons[label] = {
    inner_replay_bytes_equal: output.replays[a].inner_replay_sha256 === output.replays[b].inner_replay_sha256 && output.replays[a].inner_replay_length === output.replays[b].inner_replay_length,
    inner_replay_sha256: output.replays[a].inner_replay_sha256,
    inner_replay_length: output.replays[a].inner_replay_length,
    native_step_headers_equal: output.replays[a].native_step_header_sha256 === output.replays[b].native_step_header_sha256,
    native_step_header_sha256: output.replays[a].native_step_header_sha256,
    candidate_willow_priority_steps: output.replays[a].willow_priority_steps,
    parent_willow_priority_steps: output.replays[b].willow_priority_steps,
    candidate_willow_target13_steps: output.replays[a].willow_target13_steps,
    parent_willow_target13_steps: output.replays[b].willow_target13_steps,
  };
}
process.stdout.write(`${JSON.stringify(output, null, 2)}\n`);
