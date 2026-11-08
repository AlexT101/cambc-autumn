// F92 team scores (no counters) for every locked team on the ladder maps. node score.mjs LAB OUT.json
import fs from 'node:fs';
import { derived } from '/home/ubuntu/cambc-autumn/tools/draftlab/derived.mjs';
const [lab, out, mapsFile] = process.argv.slice(2);
const m = JSON.parse(fs.readFileSync(lab + '/model.json'));
const NC = 12, PI = Array.from({ length: NC }, () => new Int32Array(NC).fill(-1)); let np = 0;
for (let i = 0; i < NC; i++) for (let j = i + 1; j < NC; j++) { PI[i][j] = PI[j][i] = np++; }
const lay = m.layout;
const raw = (mp, name, tf) => { const v = mp.f[name] ?? derived(mp.f, name); if (v == null || !Number.isFinite(v)) return NaN;
  return tf === 'log' ? Math.log(Math.max(v, 1)) : tf === 'log1p' ? Math.log1p(Math.max(v, 0)) : v; };
const combos = p => { const o = [], c = []; const r = s => { if (c.length === p) { o.push(c.slice()); return; } for (let x = s; x < NC; x++) { c.push(x); r(x + 1); c.pop(); } }; r(0); return o; };
const allowed = T => true;
const res = [];
for (const line of fs.readFileSync(mapsFile ?? lab + '/maps.jsonl', 'utf8').split('\n')) {
  if (!line) continue; const mp = JSON.parse(line); if (mp.set !== 'maps') continue;
  const z = m.features.map((f, k) => { const v = (raw(mp, f, m.transforms[k] ?? undefined) - m.mean[k]) / m.sd[k]; return Number.isFinite(v) ? Math.max(-4, Math.min(4, v)) : 0; });
  const th = m.picks[mp.picks].theta;
  const v = Array.from({ length: NC }, (_, c) => { let s = th[lay.B + c]; for (let k = 0; k < lay.K; k++) s += th[lay.W + c * lay.K + k] * z[k]; return s; });
  const teams = combos(mp.picks).filter(allowed).map(T => { let s = 0; for (let i = 0; i < T.length; i++) { s += v[T[i]]; for (let j = i + 1; j < T.length; j++) s += th[lay.SYN + PI[T[i]][T[j]]]; } return [T, s]; });
  let best = teams[0]; for (const t of teams) if (t[1] > best[1]) best = t;
  res.push({ name: mp.name, key: mp.key, picks: mp.picks, z, v, best: best[0], teams });
}
fs.writeFileSync(out, JSON.stringify(res)); console.log(res.length, 'maps');
