// Checks frame specs against the replay: plays each frame's replay with the engine to the first step of the
// frame's round (the state extract.mjs records as the end of the previous round) and compares every field.
//   node tools/combatlab/spotcheck.mjs replays/combatlab/NAME/frames.jsonl [--n 20] [--seed 1] [--verbose]
import fs from 'node:fs';
import path from 'node:path';
import readline from 'node:readline';
import zlib from 'node:zlib';
import { fileURLToPath } from 'node:url';
import { Engine, compileEngine, replayEngine } from '../replay/engine.mjs';

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..');
const args = process.argv.slice(2);
const opt = { n: 20, seed: 1, verbose: false, file: null };
for (let i = 0; i < args.length; i++) {
  if (args[i] === '--n') opt.n = +args[++i];
  else if (args[i] === '--seed') opt.seed = +args[++i];
  else if (args[i] === '--verbose') opt.verbose = true;
  else opt.file = args[i];
}
if (!opt.file) { console.error('usage: node tools/combatlab/spotcheck.mjs FRAMES.jsonl[.gz] [--n N] [--seed S] [--verbose]'); process.exit(2); }

// Reservoir sample of N frames (the bank can be large).
let rnd = opt.seed >>> 0 || 1;
const rand = () => { rnd ^= rnd << 13; rnd >>>= 0; rnd ^= rnd >>> 17; rnd ^= rnd << 5; rnd >>>= 0; return rnd / 4294967296; };
// Half the sample from frames holding a shield, a stun or a part-awake camp group (rare states), half from all.
const pools = [[], []], seenN = [0, 0];
const special = l => /"shield":\{"amount":[1-9]/.test(l) || /"stun":[1-9]/.test(l) || /"awake":true/.test(l);
const input = fs.createReadStream(opt.file);
const lines = readline.createInterface({ input: opt.file.endsWith('.gz') ? input.pipe(zlib.createGunzip()) : input, crlfDelay: Infinity });
for await (const line of lines) {
  if (!line) continue;
  for (const p of special(line) ? [0, 1] : [1]) {
    const cap = p === 0 ? Math.floor(opt.n / 2) : opt.n - Math.floor(opt.n / 2);
    seenN[p]++;
    if (pools[p].length < cap) pools[p].push(line);
    else { const j = Math.floor(rand() * seenN[p]); if (j < cap) pools[p][j] = line; }
  }
}
const sample = [...new Set([...pools[0], ...pools[1]])];
const frames = sample.map(l => JSON.parse(l));
const byReplay = new Map();
for (const f of frames) { const k = f.source.replay; if (!byReplay.has(k)) byReplay.set(k, []); byReplay.get(k).push(f); }

const engines = {};
const tally = {};
const bad = (field, msg) => { tally[field] = tally[field] ?? { ok: 0, bad: 0, ex: [] }; tally[field].bad++; if (tally[field].ex.length < 5) tally[field].ex.push(msg); };
const good = field => { tally[field] = tally[field] ?? { ok: 0, bad: 0, ex: [] }; tally[field].ok++; };
const cmp = (field, a, b, id, tol = 0) => {
  const eq = typeof a === 'number' && typeof b === 'number' ? Math.abs(a - b) <= tol : JSON.stringify(a) === JSON.stringify(b);
  if (eq) good(field); else bad(field, `${id}: spec ${JSON.stringify(a)} replay ${JSON.stringify(b)}`);
};

let checked = 0, champsChecked = 0, campsChecked = 0, enhanced = 0;
const nonzero = { shield: 0, stun: 0, dead: 0, awakeCamp: 0 };
for (const [replay, fs2] of byReplay) {
  const bytes = fs.readFileSync(path.join(ROOT, replay));
  const v = replayEngine(bytes);
  engines[v] ??= await Engine.create(await compileEngine(v));
  const g = engines[v].openReplay(bytes);
  try {
    fs2.sort((a, b) => a.round - b.round);
    let k = 0;
    g.seekStart();
    do {
      const snap = g.read();
      const h = snap.header();
      if (h.phase === 12 || h.step.phase === 12) continue;
      while (k < fs2.length && h.round === fs2[k].round) {
        const f = fs2[k++];
        checked++;
        const chs = new Map(snap.champions().map(c => [c.id, c]));
        for (const c of f.champions) {
          const r = chs.get(c.id), id = `${f.id} champ ${c.id}`;
          champsChecked++;
          cmp('alive', c.alive, r.alive, id);
          if (c.alive) {
            cmp('position', [c.x, c.y], [r.x, r.y], id);
            cmp('hp', c.hp, r.hp, id, 0.051);
          } else cmp('respawn', c.respawn, r.respawn, id);
          cmp('maxHp', c.maxHp, r.maxHp, id, 0.051);
          cmp('gold', c.gold, r.gold, id);
          cmp('gems', c.gems, r.gems, id);
          const items = {}; r.items.forEach((n, i) => { if (n) items[String(i)] = n; });
          cmp('items', c.items, items, id);
          cmp('cons', c.cons, r.consumables, id);
          cmp('cd', c.cd, r.cd, id);
          const buff = t => r.buffs?.find(b => b.type === t);
          cmp('stun', c.stun, buff(1)?.timer ?? 0, id);
          cmp('shield.amount', c.shield.amount, buff(0)?.mag ?? 0, id, 0.051);
          cmp('shield.turns', c.shield.turns, buff(0)?.timer ?? 0, id);
          cmp('prio', c.prio, r.priority, id);
          cmp('ward [charges, recharge]', c.ward, r.ward ? [r.ward.charges, r.ward.recharge] : null, id);
          if (buff(2)) enhanced++;
          if (buff(0)) nonzero.shield++;
          if (buff(1)) nonzero.stun++;
          if (!r.alive) nonzero.dead++;
          if (c.fighter) {
            const feint = f.context.feints.includes(c.id);
            cmp('fighter channel (none or a feint recall)', feint ? 1 : 0, r.channelType ?? 0, id);
          }
        }
        const camps = snap.camps();
        for (const c of f.camps) {
          const r = camps[c.id], id = `${f.id} camp ${c.id}`;
          campsChecked++;
          if (r.hp > 0) cmp('camp position', [c.x, c.y], [r.x, r.y], id);
          cmp('camp hp', c.hp, Math.max(0, r.hp), id, 0.11);
          cmp('camp alive', c.alive, r.hp > 0, id);
          cmp('camp awake', c.awake, !!r.awake && r.hp > 0, id);
          if (r.awake && r.hp > 0) nonzero.awakeCamp++;
        }
        const groups = snap.groups();
        for (const q of f.context.groups) {
          const r = groups[q.id], id = `${f.id} group ${q.id}`;
          cmp('group state/team/timer/respawn', [q.state, q.team, q.timer, q.respawn], [r.state, r.captureTeam, r.captureTimer, r.respawn], id);
        }
        cmp('tributed', f.context.tributed, h.submittedGems, f.id);
      }
      if (k >= fs2.length) break;
    } while (g.next());
    if (k < fs2.length) bad('round reached', `${replay}: ${fs2.length - k} frames past the end`);
  } finally { g.destroy(); }
}

console.log(`${checked} frames from ${byReplay.size} replays: ${champsChecked} champion entries, ${campsChecked} camp entries; ${enhanced} with an enhanced-attack buff at the frame (not in the spec); in the replay: ${nonzero.shield} shielded, ${nonzero.stun} stunned, ${nonzero.dead} dead champions, ${nonzero.awakeCamp} awake camps`);
for (const [field, t] of Object.entries(tally)) {
  console.log(`${t.bad ? 'MISMATCH' : 'ok      '} ${field}: ${t.ok}/${t.ok + t.bad}`);
  if (t.bad) for (const e of t.ex.slice(0, opt.verbose ? 5 : 2)) console.log(`    ${e}`);
}
process.exitCode = Object.values(tally).some(t => t.bad) ? 1 : 0;
