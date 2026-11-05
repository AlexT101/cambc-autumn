import fs from 'node:fs';
import path from 'node:path';
import zlib from 'node:zlib';
import crypto from 'node:crypto';
import { Engine, compileEngine, replayEngine, STEP_KINDS, CHAMPIONS } from '../replay/engine.mjs';

// Read decision states from the actor's own engine perspective, before its input.
const [manifest, out, split = 'train', limit = '999999'] = process.argv.slice(2);
if (!manifest || !out) throw new Error('usage: node tools/fish/extract.mjs MANIFEST OUT [train|test|all] [LIMIT]');
fs.mkdirSync(out, { recursive: true });
const engines = new Map();
const compact = c => {
  const keys = ['id', 'team', 'type', 'alive', 'x', 'y', 'hp', 'maxHp', 'strength', 'focus', 'gems', 'gold', 'cd', 'channelType', 'channelTimer', 'priority', 'roundFlags', 'buffs'];
  return Object.fromEntries(keys.filter(k => c[k] !== undefined).map(k => [k, c[k]]));
};
const context = (g, id, side) => {
  const snap = g.read({ team: side, champion: id });
  const champs = snap.champions().filter(c => c.id === id || (c.alive && (c.known & 1)));
  const me = champs.find(c => c.id === id);
  const camps = snap.camps().filter(c => c.known & 1).map(c => ({ id: c.id, group: c.group, type: c.type, x: c.x, y: c.y, hp: c.hp, awake: c.awake }));
  return { me: compact(me), allies: champs.filter(c => c.id !== id && c.team === side).map(compact),
    enemies: champs.filter(c => c.team !== side).map(compact), camps,
    groups: snap.groups().map((c, i) => [i, c.state, c.captureTeam, c.captureTimer, c.respawn]).filter(c => c[1]),
    score: snap.header().submittedGems };
};
for (const entry of JSON.parse(fs.readFileSync(manifest)).filter(x => split === 'all' || x.split === split).slice(0, +limit)) {
  const key = entry.sha256.slice(0, 16), dest = path.join(out, `${key}.json.gz`);
  if (fs.existsSync(dest)) continue;
  const bytes = fs.readFileSync(entry.file);
  if (crypto.createHash('sha256').update(bytes).digest('hex') !== entry.sha256) throw new Error(`hash changed: ${entry.file}`);
  const version = replayEngine(bytes);
  if (!engines.has(version)) engines.set(version, await Engine.create(await compileEngine(version)));
  const g = engines.get(version).openReplay(bytes);
  try {
    const map = g.map(), turns = [], pending = new Map();
    let step = -1, previous = null, active = null, roster = null, priorityChecks = 0;
    g.seekStart();
    do {
      step++;
      const snap = g.read(), h = snap.header(), st = h.step;
      if (h.phase === 12 || st.phase === 12) continue;
      roster ??= snap.champions().map(c => ({ id: c.id, team: c.team, type: c.type, name: CHAMPIONS[c.type] }));
      const actor = roster.find(c => c.id === st.actor.index);
      if (st.actor.kind === 1 && actor?.team === entry.side && active && actor.id === active.id && h.round === active.round) {
        if ([4, 5, 6, 9, 11, 12, 13, 14, 15, 16, 20, 21, 23, 25].includes(st.kind)) {
          if (!previous || previous.me.id !== actor.id) throw new Error('missing pre-action perspective');
          const a = { step, kind: STEP_KINDS[st.kind], to: [st.to.x, st.to.y] };
          if ([5, 6, 9, 11, 12].includes(st.kind)) a.before = previous;
          if (st.kind === 6) { a.slot = st.abilitySlot; a.ability = st.abilityType; }
          if (st.kind === 9) {
            a.value = st.priority;
            const c = snap.champions().find(c => c.id === actor.id);
            if (c.nextPriority !== st.priority) throw new Error('priority event disagrees with snapshot');
            priorityChecks++;
          }
          active.actions.push(a);
        }
        if ([8, 26, 27].includes(st.kind)) {
          active.end = previous;
          active.finish = STEP_KINDS[st.kind];
          active = null;
        }
      }
      const c = roster.find(c => c.id === h.currentChampion);
      if (h.phase === 10 && c?.team === entry.side && ![8, 26, 27].includes(st.kind)) {
        previous = context(g, c.id, entry.side);
        if (!active || active.round !== h.round || active.id !== c.id) {
          active = { round: h.round, turn: h.turn, id: c.id, step, start: previous, actions: [] };
          const prior = pending.get(c.id);
          if (prior !== undefined && previous.me.priority !== prior) throw new Error('next-round priority did not persist');
          turns.push(active);
        }
        const writes = active.actions.filter(a => a.kind === 'Set priority');
        pending.set(c.id, writes.at(-1)?.value ?? previous.me.priority);
      } else previous = null;
    } while (g.next());
    fs.writeFileSync(dest, zlib.gzipSync(JSON.stringify({ schema: 1, ...entry, engine: version, map, roster, priorityChecks, turns })));
    console.log(`${key}: ${turns.length} turns, ${priorityChecks} priority checks`);
  } finally { g.destroy(); }
}
