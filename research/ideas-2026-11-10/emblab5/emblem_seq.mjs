// Every champion's new emblems in order (a Greed one as its first shard), a line a champion: checks what an edit buys.
//   node research/ideas-2026-11-10/emblab5/emblem_seq.mjs REPLAY...
import fs from 'node:fs';
import { Engine, compileEngine, replayEngine } from '../../../tools/replay/engine.mjs';
const F = ['monster', 'power', 'durability', 'treasure', 'jungle', 'home', 'bruiser', 'tribute', 'capture', 'prospector', 'hunter', 'skirmish', 'greed', 'collectors'], S = ['str', 'foc', 'hp'];
const T = ['ryth', 'vesper', 'vendetta', 'cassi', 'issac', 'stellar', 'prism', 'marcella', 'willow', 'ren', 'varg', 'tavi', 'hor'];
const engines = {};
for (const f of process.argv.slice(2)) {
  const bytes = fs.readFileSync(f), version = replayEngine(bytes);
  engines[version] ??= await Engine.create(await compileEngine(version));
  const g = engines[version].openReplay(bytes);
  g.seekStart();
  let prev = null, roster = null, steps = 0;
  const seq = [];
  const scan = s => {
    if (!roster) {
      const cs = s.champions();
      if (!cs.length) return;
      roster = cs.map(c => ({ team: c.team, type: c.type }));
      roster.forEach(() => seq.push([]));
    }
    const now = roster.map((_, k) => s.items(k));
    if (prev) for (let k = 0; k < roster.length; k++) for (let fa = 0; fa < 14; fa++) for (let st = 0; st < 3; st++) {
      const shard = fa * 6 + st * 2, emblem = shard + 1;
      if (prev[k][shard] === 0 && (now[k][shard] > 0 || now[k][emblem] > prev[k][emblem])) seq[k].push(`${F[fa]}-${S[st]}`);
    }
    prev = now;
  };
  while (g.next()) if (++steps % 16 === 0) scan(g.read());
  scan(g.read());
  g.destroy();
  console.log(f.split('/').pop());
  roster.forEach((c, k) => { if (k < roster.length / 2) console.log(`  ${String(T[c.type] ?? c.type).padEnd(8)} ${seq[k].join(" ")}`); });
}
