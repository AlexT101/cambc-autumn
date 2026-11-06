// Cross-evaluation: each model's per-map team (teams-*.txt) scored under both models' posterior means, against the
// ladder prior's top 40 compositions (as model.mjs gain), on the ladder and fresh maps. No counters (both ~0).
import fs from 'node:fs';
import { FEATURES, CHAMPS } from '/home/ubuntu/cambc-autumn/tools/draftlab/model.mjs';
import { derived } from '/home/ubuntu/cambc-autumn/tools/draftlab/derived.mjs';
const O = '/home/ubuntu/tmp-offload/draftfeat', R = '/home/ubuntu/cambc-autumn/replays/draftlab';
const NC = 12, PI = []; for (let i = 0; i < NC; i++) { PI.push([]); } let np = 0;
for (let i = 0; i < NC; i++) for (let j = i + 1; j < NC; j++) { PI[i][j] = PI[j][i] = np++; }
const tfOf = Object.fromEntries(FEATURES.map(f => [f[0], f[1]]));
const load = lab => { const m = JSON.parse(fs.readFileSync(`${R}/${lab}/model.json`)); return m; };
const zOf = (m, f) => m.features.map((n, k) => { let v = f[n] ?? derived(f, n); if (v === null || v === undefined || !Number.isFinite(v)) return 0;
  const t = tfOf[n]; v = t === 'log' ? Math.log(Math.max(v, 1)) : t === 'log1p' ? Math.log1p(Math.max(v, 0)) : v; v = (v - m.mean[k]) / m.sd[k]; return Number.isFinite(v) ? Math.max(-4, Math.min(4, v)) : 0; });
const prior = JSON.parse(fs.readFileSync(`${R}/draft5/prior.json`));
const models = { draft5: load('draft5'), feat: load('draft5-feat') };
const teamVal = (m, p, z, T) => { const th = m.picks[p].theta, L = m.layout, K = L.K; let s = 0;
  for (let i = 0; i < T.length; i++) { const c = T[i]; s += th[L.B + c]; for (let k = 0; k < K; k++) s += th[L.W + c * K + k] * z[k]; for (let j = i + 1; j < T.length; j++) s += th[L.SYN + PI[c][T[j]]]; } return s; };
const sig = x => 1 / (1 + Math.exp(-x));
for (const set of ['ladder', 'fresh']) {
  const rows = fs.readFileSync(`${O}/${set}.jsonl`, 'utf8').trim().split('\n').map(JSON.parse);
  const teams = Object.fromEntries(['draft5', 'draft5-feat'].map(l => [l, Object.fromEntries(fs.readFileSync(`${O}/teams-${l}-${set}.txt`, 'utf8').trim().split('\n').map(x => x.split(' ')).filter(x => x[3] !== '-').map(x => [x[0], x[3].split(',').map(c => CHAMPS.indexOf(c))]))]));
  for (const [ename, m] of Object.entries(models)) {
    const acc = {};
    for (const r of rows) {
      const p = r.picks; if (!teams.draft5[r.key]) continue;
      const z = zOf(m, r.f), opps = prior[p].slice(0, 40).map(e => ({ v: teamVal(m, p, z, e.comp.map(c => CHAMPS.indexOf(c))), n: e.n }));
      const W = opps.reduce((s, o) => s + o.n, 0);
      const win = T => { const v = teamVal(m, p, z, T); return opps.reduce((s, o) => s + o.n * sig(v - o.v), 0) / W; };
      const a = acc[p] ??= { n: 0, old: 0, neu: 0, one: { n: 0, d: 0 } };
      const wo = win(teams.draft5[r.key]), wn = win(teams['draft5-feat'][r.key]);
      a.n++; a.old += wo; a.neu += wn; if (r.f.altars === 1) { a.one.n++; a.one.d += wn - wo; }
    }
    console.log(`${set}, scored under ${ename}: ` + Object.entries(acc).map(([p, a]) => `${p} picks (${a.n}) old ${(100 * a.old / a.n).toFixed(1)} new ${(100 * a.neu / a.n).toFixed(1)} (${(100 * (a.neu - a.old) / a.n).toFixed(2)}; one-altar ${a.one.n ? (100 * a.one.d / a.one.n).toFixed(2) : '-'})`).join('; '));
  }
}
