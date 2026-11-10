// Each champion's new emblems in order, from local replays (an A/B's kept ones): which arm a candidate really buys.
//   node research/ideas-2026-11-10/emblab4/emblem_orders.mjs DIR [N]    # bot 1 is team A in *-12 files, team B in *-21
import fs from 'node:fs';
import path from 'node:path';
import { Engine, compileEngine, replayEngine } from '../../../tools/replay/engine.mjs';

const F = ['monster', 'power', 'durability', 'treasure', 'jungle', 'home', 'bruiser', 'tribute', 'capture', 'prospector', 'hunter', 'skirmish', 'greed', 'collectors'], S = ['str', 'foc', 'hp'];
const dir = process.argv[2], limit = +(process.argv[3] ?? 40), engines = {};
const first = {};   // bot -> type -> ordinal -> arm -> count
for (const f of fs.readdirSync(dir).filter(f => f.endsWith('.repl26a')).slice(0, limit)) {
  const bytes = fs.readFileSync(path.join(dir, f)), version = replayEngine(bytes);
  engines[version] ??= await Engine.create(await compileEngine(version));
  const g = engines[version].openReplay(bytes);
  g.seekStart();
  let prev = null, roster = null, steps = 0;
  const seq = [];
  const scan = s => {
    if (!roster) { roster = s.champions().map(c => ({ team: c.team, type: c.type })); roster.forEach(() => seq.push([])); }
    const now = roster.map((_, k) => s.items(k));
    if (prev) for (let k = 0; k < roster.length; k++) for (let fa = 0; fa < 14; fa++) for (let st = 0; st < 3; st++) {
      const shard = fa * 6 + st * 2, emblem = shard + 1;
      if (prev[k][shard] === 0 && (now[k][shard] > 0 || now[k][emblem] > prev[k][emblem])) seq[k].push(`${F[fa]}-${S[st]}`);
    }
    prev = now;
  };
  while (g.next()) if (++steps % 64 === 0) scan(g.read());
  scan(g.read());
  g.destroy();
  const botOfTeam = f.includes('-12.') ? [1, 2] : [2, 1];
  roster.forEach((c, k) => seq[k].slice(0, 3).forEach((arm, o) => {
    const t = ((first[botOfTeam[c.team]] ??= {})[c.type] ??= [{}, {}, {}])[o];
    t[arm] = (t[arm] ?? 0) + 1;
  }));
}
for (const bot of [1, 2]) for (const [type, os] of Object.entries(first[bot] ?? {}))
  console.log(`bot ${bot} ${String(type).padEnd(14)} ` + os.map((t, o) => `k${o}: ` + Object.entries(t).sort((a, b) => b[1] - a[1]).slice(0, 3).map(([a, n]) => `${a} ${n}`).join(', ')).join(' | '));
