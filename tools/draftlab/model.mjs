// Draft lab model (tools/draftlab/README.md): fit, plan a batch, report.
//   node tools/draftlab/model.mjs fit    --lab DIR [--search]
//   node tools/draftlab/model.mjs plan   --lab DIR --batch N --out FILE [--vehicles V] [--games G] [--mode explore|adapt]
//   node tools/draftlab/model.mjs report --lab DIR
// P(A wins) = sigmoid(S(A) - S(B) + sum over a in A, b in B of M[a,b] + side), S(T) = sum over T of
// (b_c + w_c . z(map)) + sum over pairs in T of syn; M antisymmetric. One fit per pick count, penalised
// toward a fit pooled over pick counts; penalties and the soft-target weight by 5-fold cross-validation
// over maps, scored on wins only.
import fs from 'node:fs';
import path from 'node:path';

export const CHAMPS = ['ryth', 'vesper_vale', 'vendetta', 'cassi_and_issac', 'stellar', 'prism', 'marcella', 'willow', 'ren', 'varg', 'tavi', 'heart_of_ruin'];
const SHORT = ['Ryth', 'Vesp', 'Vend', 'Cass', 'Stel', 'Pris', 'Marc', 'Will', 'Ren', 'Varg', 'Tavi', 'HoR'];
const NC = CHAMPS.length, PICKS = [3, 4, 5];
// [metric, transform]: features.mjs names. log for sizes and distances, log1p for counts that can be 0.
export const FEATURES = [
  ['area', 'log'], ['reach_frac'], ['spawn_dist', 'log'], ['detour'], ['choke_rel'], ['openness'], ['bushes'], ['holes'],
  ['altars', 'log1p'], ['altar_ratio'], ['altar_centre'], ['gems_side', 'log1p'], ['gold_side', 'log1p'], ['big_share'],
  ['cluster_share'], ['contested_share'], ['big_camp_share'], ['dash_short'], ['camp_near', 'log1p'],
];
const K = FEATURES.length;
const PAIRS = [], PI = Array.from({ length: NC }, () => new Int32Array(NC).fill(-1));
for (let i = 0; i < NC; i++) for (let j = i + 1; j < NC; j++) { PI[i][j] = PI[j][i] = PAIRS.length; PAIRS.push([i, j]); }
const L = { B: 0, W: NC, SYN: NC + NC * K, CTR: NC + NC * K + PAIRS.length, SIDE: NC + NC * K + 2 * PAIRS.length };
L.P = L.SIDE + 1;
const P = L.P;
const GROUPS = ['b', 'w', 'syn', 'ctr', 'side'];
const GROUP = new Int8Array(P).map((_, j) => j < L.W ? 0 : j < L.SYN ? 1 : j < L.CTR ? 2 : j < L.SIDE ? 3 : 4);
const FOLDS = 5, KAPPA = 5;
// A logit difference of d is about 25 d win-percentage points near 50%.
const PTS = 25;

// ---- io ---------------------------------------------------------------------------------------
const readJsonl = f => fs.existsSync(f) ? fs.readFileSync(f, 'utf8').split('\n').filter(Boolean).map(l => JSON.parse(l)) : [];
const readJson = (f, d = null) => fs.existsSync(f) ? JSON.parse(fs.readFileSync(f, 'utf8')) : d;
const cid = name => { const i = CHAMPS.indexOf(name); if (i < 0) throw new Error(`unknown champion ${name}`); return i; };

function args() {
  const a = process.argv.slice(3), o = {};
  for (let i = 0; i < a.length; i++) {
    if (!a[i].startsWith('--')) throw new Error(`unexpected ${a[i]}`);
    const k = a[i].slice(2), v = a[i + 1] && !a[i + 1].startsWith('--') ? a[++i] : true;
    o[k] = v;
  }
  return o;
}

function rng(seed) {
  let s = (seed >>> 0) || 1;
  return () => { s ^= s << 13; s >>>= 0; s ^= s >> 17; s ^= s << 5; s >>>= 0; return s / 4294967296; };
}
function hash(str) { let h = 2166136261; for (let i = 0; i < str.length; i++) h = Math.imul(h ^ str.charCodeAt(i), 16777619); return h >>> 0; }
function gauss(r) { let u = 0; while (!u) u = r(); return Math.sqrt(-2 * Math.log(u)) * Math.cos(2 * Math.PI * r()); }

// ---- maps -------------------------------------------------------------------------------------
function raw(m, [name, tf]) {
  const v = m.f[name];
  if (v === null || v === undefined || !Number.isFinite(v)) return NaN;
  return tf === 'log' ? Math.log(Math.max(v, 1)) : tf === 'log1p' ? Math.log1p(Math.max(v, 0)) : v;
}

// Standardised over the whole pool (not the games), so z(map) is the same in every batch's model.
function mapTable(lab) {
  const maps = readJsonl(path.join(lab, 'maps.jsonl')).filter(m => PICKS.includes(m.picks));
  const mean = FEATURES.map(f => { const v = maps.map(m => raw(m, f)).filter(Number.isFinite); return v.reduce((a, b) => a + b, 0) / Math.max(1, v.length); });
  const sd = FEATURES.map((f, k) => { const v = maps.map(m => raw(m, f)).filter(Number.isFinite); return Math.sqrt(v.reduce((a, b) => a + (b - mean[k]) ** 2, 0) / Math.max(1, v.length)) || 1; });
  const byKey = new Map();
  for (const m of maps) {
    m.z = Float64Array.from(FEATURES, (f, k) => { const v = (raw(m, f) - mean[k]) / sd[k]; return Number.isFinite(v) ? Math.max(-4, Math.min(4, v)) : 0; });
    byKey.set(m.key, m);
  }
  return { maps, byKey, mean, sd };
}

// ---- design -----------------------------------------------------------------------------------
const scratch = new Float64Array(P), touched = [];
function design(A, B, z) {
  const add = (i, v) => { if (scratch[i] === 0) touched.push(i); scratch[i] += v; if (scratch[i] === 0) scratch[i] = 1e-300; };
  for (const [T, s] of [[A, 1], [B, -1]]) {
    for (const c of T) { add(L.B + c, s); for (let k = 0; k < K; k++) if (z[k]) add(L.W + c * K + k, s * z[k]); }
    for (let i = 0; i < T.length; i++) for (let j = i + 1; j < T.length; j++) add(L.SYN + PI[T[i]][T[j]], s);
  }
  for (const a of A) for (const b of B) if (a !== b) add(L.CTR + PI[a][b], a < b ? 1 : -1);
  add(L.SIDE, 1);
  touched.sort((p, q) => p - q);
  const idx = [], val = [];
  for (const i of touched) { if (Math.abs(scratch[i]) > 1e-12) { idx.push(i); val.push(scratch[i]); } scratch[i] = 0; }
  touched.length = 0;
  return { idx: Int32Array.from(idx), val: Float64Array.from(val) };
}

const sigmoid = x => 1 / (1 + Math.exp(-x));
const dot = (th, r) => { let e = 0; for (let k = 0; k < r.idx.length; k++) e += th[r.idx[k]] * r.val[k]; return e; };
const softplus = x => x > 30 ? x : Math.log1p(Math.exp(x));

// Rows of finished, draft-checked games; y mixes the win with the wealth margin (tributed + carried at the end).
function gameRows(lab, table) {
  const rows = [];
  for (const g of readJsonl(path.join(lab, 'games.jsonl'))) {
    if (g.error || g.winner === undefined || g.draft_ok === false) continue;
    const m = table.byKey.get(g.key);
    if (!m) continue;
    const A = g.A.map(cid), B = g.B.map(cid), r = design(A, B, m.z);
    const win = g.winner === 0 ? 1 : 0;
    let soft = win;
    if (g.wealth) { const [a, b] = g.wealth; soft = sigmoid(KAPPA * (a - b) / (a + b + 50)); }
    rows.push({ ...r, win, soft, w: 1, picks: g.picks, key: g.key, fold: hash(g.key) % FOLDS, g, A, B, z: m.z });
  }
  return rows;
}

// ---- fit --------------------------------------------------------------------------------------
function cholesky(H) {
  const Lm = new Float64Array(P * P);
  for (let i = 0; i < P; i++) for (let j = 0; j <= i; j++) {
    let s = H[i * P + j];
    for (let k = 0; k < j; k++) s -= Lm[i * P + k] * Lm[j * P + k];
    if (i === j) { if (s <= 0) throw new Error('Hessian not positive definite'); Lm[i * P + i] = Math.sqrt(s); }
    else Lm[i * P + j] = s / Lm[j * P + j];
  }
  return Lm;
}
function cholSolve(Lm, b) {
  const y = Float64Array.from(b);
  for (let i = 0; i < P; i++) { let s = y[i]; for (let k = 0; k < i; k++) s -= Lm[i * P + k] * y[k]; y[i] = s / Lm[i * P + i]; }
  for (let i = P - 1; i >= 0; i--) { let s = y[i]; for (let k = i + 1; k < P; k++) s -= Lm[k * P + i] * y[k]; y[i] = s / Lm[i * P + i]; }
  return y;
}
// x = L^-T e: a draw from N(0, H^-1) when e ~ N(0, I).
function cholBack(Lm, e) {
  const y = Float64Array.from(e);
  for (let i = P - 1; i >= 0; i--) { let s = y[i]; for (let k = i + 1; k < P; k++) s -= Lm[k * P + i] * y[k]; y[i] = s / Lm[i * P + i]; }
  return y;
}

function objective(rows, th, th0, lamv, alpha) {
  let f = 0;
  for (const r of rows) { const e = dot(th, r), y = (1 - alpha) * r.win + alpha * r.soft; f += r.w * (softplus(e) - y * e); }
  for (let j = 0; j < P; j++) f += 0.5 * lamv[j] * (th[j] - th0[j]) ** 2;
  return f;
}

function newton(rows, lam, alpha, th0, init) {
  const lamv = Float64Array.from(GROUP, g => lam[GROUPS[g]]);
  let th = Float64Array.from(init ?? th0), f = objective(rows, th, th0, lamv, alpha), Lm = null;
  for (let it = 0; it < 25; it++) {
    const H = new Float64Array(P * P), g = new Float64Array(P);
    for (const r of rows) {
      const p = sigmoid(dot(th, r)), y = (1 - alpha) * r.win + alpha * r.soft, res = r.w * (p - y), s = r.w * p * (1 - p);
      const { idx, val } = r, n = idx.length;
      for (let a = 0; a < n; a++) {
        g[idx[a]] += res * val[a];
        const sa = s * val[a], row = idx[a] * P;
        for (let b = 0; b <= a; b++) H[row + idx[b]] += sa * val[b];
      }
    }
    for (let j = 0; j < P; j++) { g[j] += lamv[j] * (th[j] - th0[j]); H[j * P + j] += lamv[j]; }
    Lm = cholesky(H);
    const d = cholSolve(Lm, g);
    let step = 1, next, fn;
    for (; step > 1e-4; step /= 2) {
      next = th.map((v, j) => v - step * d[j]);
      fn = objective(rows, next, th0, lamv, alpha);
      if (fn <= f + 1e-9) break;
    }
    const moved = Math.max(...d.map(Math.abs)) * step;
    th = next; f = fn;
    if (moved < 1e-6) break;
  }
  return { theta: th, chol: Lm };
}

// Pooled over pick counts toward 0, then each pick count toward the pooled fit.
function fitAll(rows, lam, alpha, warm) {
  const pooled = newton(rows, lam, alpha, new Float64Array(P), warm?.pooled);
  const picks = {};
  for (const p of PICKS) {
    const rp = rows.filter(r => r.picks === p);
    picks[p] = rp.length ? newton(rp, lam, alpha, pooled.theta, warm?.picks?.[p]?.theta) : { theta: pooled.theta, chol: pooled.chol };
  }
  return { pooled: pooled.theta, picks };
}

function cvLoss(rows, lam, alpha, warm) {
  let loss = 0, n = 0;
  for (let k = 0; k < FOLDS; k++) {
    const train = rows.filter(r => r.fold !== k), test = rows.filter(r => r.fold === k);
    if (!test.length || !train.length) continue;
    const fit = fitAll(train, lam, alpha, warm);
    for (const r of test) { const e = dot(fit.picks[r.picks].theta, r); loss += softplus(e) - r.win * e; n++; }
  }
  return loss / Math.max(1, n);
}

const OFF = 1e9;
function fitCommand(o) {
  const lab = o.lab, table = mapTable(lab), rows = gameRows(lab, table);
  if (rows.length < 200) throw new Error(`only ${rows.length} usable games`);
  const prev = readJson(path.join(lab, 'model.json'));
  let lam = prev?.lam ?? { b: 1, w: 20, syn: 20, ctr: 20, side: 0.1 }, alpha = prev?.alpha ?? 0;
  const cv = {};
  if (o.search) {
    const t0 = Date.now();
    let best = cvLoss(rows, lam, alpha);
    console.error(`cv start ${best.toFixed(5)} ${JSON.stringify(lam)} alpha ${alpha}`);
    for (let pass = 0; pass < 2; pass++) {
      for (const gname of ['w', 'syn', 'ctr', 'b']) for (const mul of [0.25, 4]) {
        const tryLam = { ...lam, [gname]: lam[gname] * mul }, l = cvLoss(rows, tryLam, alpha);
        if (l < best - 1e-6) { best = l; lam = tryLam; console.error(`cv ${l.toFixed(5)} ${gname} x${mul}`); }
      }
      for (const a of [0, 0.3, 0.6]) if (a !== alpha) {
        const l = cvLoss(rows, lam, a);
        if (l < best - 1e-6) { best = l; alpha = a; console.error(`cv ${l.toFixed(5)} alpha ${a}`); }
      }
    }
    cv.model = best;
    cv.no_map = cvLoss(rows, { ...lam, w: OFF }, alpha);
    cv.no_pairs = cvLoss(rows, { ...lam, syn: OFF, ctr: OFF }, alpha);
    cv.intercepts = cvLoss(rows, { ...lam, w: OFF, syn: OFF, ctr: OFF }, alpha);
    cv.coin = Math.log(2);
    console.error(`search ${((Date.now() - t0) / 1000).toFixed(0)} s`);
  } else if (prev?.cv) Object.assign(cv, prev.cv, { stale: true });
  const fit = fitAll(rows, lam, alpha);
  const counts = Object.fromEntries(PICKS.map(p => [p, rows.filter(r => r.picks === p).length]));
  const round = a => Array.from(a, v => +v.toPrecision(7));
  const model = {
    created: new Date().toISOString(), games: rows.length, counts, champions: CHAMPS, features: FEATURES.map(f => f[0]),
    transforms: FEATURES.map(f => f[1] ?? null), mean: table.mean, sd: table.sd, layout: L, lam, alpha, cv,
    pooled: round(fit.pooled), picks: Object.fromEntries(PICKS.map(p => [p, { theta: round(fit.picks[p].theta), chol: round(fit.picks[p].chol) }])),
  };
  // Renamed into place: lab.py plans the next batch while this runs.
  fs.writeFileSync(path.join(lab, 'model.json.tmp'), JSON.stringify(model));
  fs.renameSync(path.join(lab, 'model.json.tmp'), path.join(lab, 'model.json'));
  console.log(`fit ${rows.length} games (${PICKS.map(p => `${p}: ${counts[p]}`).join(', ')}); lam ${JSON.stringify(lam)} alpha ${alpha}` +
    (cv.model ? `; cv log loss ${cv.model.toFixed(4)} (no map ${cv.no_map.toFixed(4)}, no pairs ${cv.no_pairs.toFixed(4)}, intercepts ${cv.intercepts.toFixed(4)})` : ''));
}

function loadModel(lab) {
  const m = readJson(path.join(lab, 'model.json'));
  if (!m) return null;
  if (m.features.join() !== FEATURES.map(f => f[0]).join() || m.layout.P !== P) throw new Error('model.json has another feature set; refit');
  for (const p of PICKS) { m.picks[p].theta = Float64Array.from(m.picks[p].theta); m.picks[p].chol = Float64Array.from(m.picks[p].chol); }
  return m;
}

// ---- team values -------------------------------------------------------------------------------
// Opponent prior per pick count: [{comp: [ids], n}] and the chance each champion is in their team.
function loadPrior(lab) {
  const pr = readJson(path.join(lab, 'prior.json'));
  if (!pr) throw new Error('no prior.json (lab.py init)');
  const out = {};
  for (const p of PICKS) {
    const comps = (pr[p] ?? []).map(e => ({ comp: e.comp.map(cid), n: e.n }));
    const total = comps.reduce((s, e) => s + e.n, 0) || 1, q = new Float64Array(NC);
    for (const e of comps) for (const c of e.comp) q[c] += e.n / total;
    out[p] = { comps, total, q };
  }
  return out;
}

// Each champion's value on this map against the opponent prior: b + w.z + expected counter terms.
function champValues(th, z, q) {
  const v = new Float64Array(NC);
  for (let c = 0; c < NC; c++) {
    let s = th[L.B + c];
    for (let k = 0; k < K; k++) s += th[L.W + c * K + k] * z[k];
    for (let d = 0; d < NC; d++) if (d !== c) s += q[d] * (c < d ? 1 : -1) * th[L.CTR + PI[c][d]];
    v[c] = s;
  }
  return v;
}

function combos(p) {
  const out = [], cur = [];
  const rec = s => { if (cur.length === p) { out.push(cur.slice()); return; } for (let c = s; c < NC; c++) { cur.push(c); rec(c + 1); cur.pop(); } };
  rec(0);
  return out;
}
const COMBOS = Object.fromEntries(PICKS.map(p => [p, combos(p)]));

function teamValue(th, v, T) {
  let s = 0;
  for (let i = 0; i < T.length; i++) { s += v[T[i]]; for (let j = i + 1; j < T.length; j++) s += th[L.SYN + PI[T[i]][T[j]]]; }
  return s;
}

function rankTeams(th, z, q, p) {
  const v = champValues(th, z, q);
  return COMBOS[p].map(T => ({ T, s: teamValue(th, v, T) })).sort((a, b) => b.s - a.s);
}

// Least opponent-dependent first, so the most counter-sensitive pick is made last (when most is known).
function pickOrder(th, T, q) {
  const sens = c => { let s = 0; for (let d = 0; d < NC; d++) if (d !== c) s += q[d] * (1 - q[d]) * th[L.CTR + PI[c][d]] ** 2; return s; };
  return [...T].sort((a, b) => sens(a) - sens(b));
}

function drawTheta(m, p, r) {
  const e = Float64Array.from({ length: P }, () => gauss(r)), d = cholBack(m.picks[p].chol, e), th = m.picks[p].theta;
  return th.map((v, j) => v + d[j]);
}

// ---- plan -------------------------------------------------------------------------------------
function planCommand(o) {
  const lab = o.lab, batch = +o.batch, V = +(o.vehicles ?? 4), G = +(o.games ?? 3000), mode = o.mode ?? 'explore';
  const cfg = readJson(path.join(lab, 'config.json'), {});
  const shares = cfg.pick_shares ?? { 3: 0.33, 4: 0.33, 5: 0.34 }, holdout = new Set(cfg.holdout ?? []);
  const mix = mode === 'explore' ? { explore: 1 } : (cfg.mix ?? { explore: 0.15, thompson: 0.7, probe: 0.15 });
  const ladderOpp = cfg.ladder_opponent ?? 0.5, draws = cfg.thompson_draws ?? 16;
  const r = rng(hash(`${cfg.seed ?? 1}|${batch}`)), table = mapTable(lab), prior = loadPrior(lab);
  const model = mode === 'explore' ? null : loadModel(lab);
  if (mode !== 'explore' && !model) throw new Error('adapt mode needs model.json');
  const seen = new Set(readJsonl(path.join(lab, 'games.jsonl')).map(g => `${g.key}|${g.A}|${g.B}`));

  // Ladder maps every batch; the rest cycle through a fixed shuffle so batches cover the pool evenly.
  const chosen = [];
  for (const p of PICKS) {
    const pool = table.maps.filter(m => m.picks === p && !holdout.has(m.set));
    const ladder = pool.filter(m => m.set === 'maps'), rest = pool.filter(m => m.set !== 'maps');
    const order = rest.map(m => [hash(`${cfg.seed ?? 1}|${m.key}`), m]).sort((a, b) => a[0] - b[0]).map(x => x[1]);
    const want = Math.max(0, Math.round(shares[p] * G / V) - ladder.length);
    chosen.push(...ladder);
    for (let i = 0; i < Math.min(want, order.length); i++) chosen.push(order[(batch * want + i) % order.length]);
  }

  const shuffled = a => { for (let i = a.length - 1; i > 0; i--) { const j = Math.floor(r() * (i + 1)); [a[i], a[j]] = [a[j], a[i]]; } return a; };
  const explore = p => ({ T: shuffled(Array.from({ length: NC }, (_, c) => c)).slice(0, p), src: 'explore', prob: 1 / COMBOS[p].length });
  const ladderComp = p => {
    const pr = prior[p];
    let x = r() * pr.total;
    for (const e of pr.comps) if ((x -= e.n) < 0) return { T: e.comp.slice(), src: 'ladder', prob: e.n / pr.total };
    return explore(p);
  };
  const pickSrc = () => { let x = r(); for (const [k, w] of Object.entries(mix)) if ((x -= w) < 0) return k; return 'explore'; };

  const vehicles = Array.from({ length: V }, () => []), games = [];
  for (const m of chosen) {
    const p = m.picks, q = prior[p].q;
    let ts = null, mean = null;
    if (model) {
      // Thompson: the best team under each posterior draw, against the opponent prior.
      const counts = new Map();
      for (let d = 0; d < draws; d++) { const best = rankTeams(drawTheta(model, p, r), m.z, q, p)[0].T, k = best.join(); counts.set(k, (counts.get(k) ?? 0) + 1); }
      ts = [...counts].map(([k, n]) => ({ T: k.split(',').map(Number), n }));
      mean = rankTeams(model.picks[p].theta, m.z, q, p);
    }
    const thompson = () => { let x = r() * draws; for (const e of ts) if ((x -= e.n) < 0) return { T: e.T.slice(), src: 'thompson', prob: e.n / draws }; return { T: ts[0].T.slice(), src: 'thompson', prob: ts[0].n / draws }; };
    let lastOpp = null;
    for (let k = 0; k < V; k++) {
      let game = null;
      for (let attempt = 0; attempt < 30 && !game; attempt++) {
        const src = model ? pickSrc() : 'explore';
        // Probes pair with the previous game on this map: same opponent and side, the mean model's runner-up.
        let learner, opp, learnerSide;
        if (src === 'probe' && lastOpp) {
          ({ opp, side: learnerSide } = lastOpp);
          const alt = mean.find(t => t.T.join() !== lastOpp.learner.join() && !seen.has(`${m.key}|${sides(learnerSide, t.T, opp.T)}`));
          learner = alt ? { T: alt.T.slice(), src: 'probe', prob: null } : explore(p);
        } else {
          learnerSide = r() < 0.5 ? 0 : 1;
          learner = src === 'thompson' ? thompson() : src === 'probe' ? (mean ? { T: mean[1].T.slice(), src: 'probe', prob: null } : explore(p)) : explore(p);
          opp = r() < ladderOpp ? ladderComp(p) : model && r() < 0.5 ? thompson() : explore(p);
        }
        if (model && learner.src !== 'explore') learner.T = pickOrder(model.picks[p].theta, learner.T, q).map(Number);
        const [A, B] = learnerSide === 0 ? [learner, opp] : [opp, learner];
        const id = `${m.key}|${A.T.map(c => CHAMPS[c])}|${B.T.map(c => CHAMPS[c])}`;
        if (seen.has(id)) continue;
        seen.add(id);
        game = { A, B };
        lastOpp = { opp, side: learnerSide, learner: learner.T.slice().sort((a, b) => a - b) };
      }
      if (!game) continue;
      const names = T => T.map(c => CHAMPS[c]);
      vehicles[k].push({ key: m.key, team: 0, comp: names(game.A.T) }, { key: m.key, team: 1, comp: names(game.B.T) });
      games.push({ vehicle: k, map: m.path, key: m.key, set: m.set, picks: p, A: names(game.A.T), B: names(game.B.T),
        srcA: game.A.src, srcB: game.B.src, probA: game.A.prob, probB: game.B.prob });
    }
  }
  fs.writeFileSync(o.out, JSON.stringify({ batch, mode, mix, created: new Date().toISOString(), vehicles, games }));
  const bySrc = {};
  for (const g of games) for (const s of [g.srcA, g.srcB]) bySrc[s] = (bySrc[s] ?? 0) + 1;
  console.log(`planned ${games.length} games on ${chosen.length} maps, ${V} vehicles; team sources ${JSON.stringify(bySrc)}`);
}
const sides = (side, learner, opp) => side === 0 ? `${learner.map(c => CHAMPS[c])}|${opp.map(c => CHAMPS[c])}` : `${opp.map(c => CHAMPS[c])}|${learner.map(c => CHAMPS[c])}`;

// ---- report -----------------------------------------------------------------------------------
// k-means++ on standardised features, seeded, so cluster numbers are stable for a given pool.
function kmeans(points, k, seed = 7) {
  const r = rng(seed), d2 = (a, b) => a.reduce((s, v, i) => s + (v - b[i]) ** 2, 0);
  const cent = [points[Math.floor(r() * points.length)].slice()];
  while (cent.length < k) {
    const dist = points.map(p => Math.min(...cent.map(c => d2(p, c)))), tot = dist.reduce((a, b) => a + b, 0);
    let x = r() * tot, i = 0;
    for (; i < points.length - 1 && (x -= dist[i]) > 0; i++);
    cent.push(points[i].slice());
  }
  let assign = new Int32Array(points.length);
  for (let it = 0; it < 50; it++) {
    const next = Int32Array.from(points, p => { let b = 0; for (let c = 1; c < k; c++) if (d2(p, cent[c]) < d2(p, cent[b])) b = c; return b; });
    for (let c = 0; c < k; c++) { const mem = points.filter((_, i) => next[i] === c); if (mem.length) cent[c] = mem[0].map((_, j) => mem.reduce((s, p) => s + p[j], 0) / mem.length); }
    if (next.every((v, i) => v === assign[i]) && it) break;
    assign = next;
  }
  return { assign, cent };
}

// Benjamini-Hochberg at level a over two-sided z scores: the set of flagged indices.
function bh(zs, a = 0.1) {
  const ps = zs.map((z, i) => [2 * (1 - normCdf(Math.abs(z))), i]).sort((x, y) => x[0] - y[0]);
  let cut = -1;
  ps.forEach(([p], j) => { if (p <= a * (j + 1) / ps.length) cut = j; });
  return new Set(ps.slice(0, cut + 1).map(x => x[1]));
}
function normCdf(x) { const t = 1 / (1 + 0.2316419 * x), d = 0.3989423 * Math.exp(-x * x / 2); return 1 - d * t * (0.3193815 + t * (-0.3565638 + t * (1.781478 + t * (-1.821256 + t * 1.330274)))); }

// Champion type (cassi and issac apart) to draft id.
const typeToDraft = t => t <= 3 ? t : t === 4 ? 3 : t - 1;

function reportCommand(o) {
  const lab = o.lab, table = mapTable(lab), model = loadModel(lab), prior = loadPrior(lab), rows = gameRows(lab, table);
  if (!model) throw new Error('no model.json');
  const nClusters = +(o.clusters ?? 8);
  const { assign, cent } = kmeans(table.maps.map(m => Array.from(m.z)), nClusters);
  table.maps.forEach((m, i) => { m.cluster = assign[i]; });
  const describe = c => FEATURES.map((f, k) => [f[0], cent[c][k]]).sort((a, b) => Math.abs(b[1]) - Math.abs(a[1])).slice(0, 3)
    .map(([n, v]) => `${n} ${v > 0 ? '+' : ''}${v.toFixed(1)}`).join(', ');
  const out = [];
  const pct = x => `${x >= 0 ? '+' : ''}${(PTS * x).toFixed(1)}`;
  out.push(`# Draft lab report`, '', `${rows.length} games (${PICKS.map(p => `${p} picks ${model.counts[p]}`).join(', ')}), model of ${model.created}.`,
    `Effects are win-percentage points against the average champion (25 x logit), at the map's features, against the ladder prior's opponents.`, '');
  if (model.cv?.model) {
    const c = model.cv;
    out.push(`Cross-validated log loss over maps${c.stale ? ' (from the last --search)' : ''}: model ${c.model.toFixed(4)}, without map terms ${c.no_map.toFixed(4)}, ` +
      `without synergy/counter terms ${c.no_pairs.toFixed(4)}, intercepts only ${c.intercepts.toFixed(4)}, coin ${c.coin.toFixed(4)}. Penalties ${JSON.stringify(model.lam)}, soft weight ${model.alpha}.`, '');
  }
  out.push('## Map clusters', '', '| Cluster | Maps | 3/4/5 picks | Ladder maps | Largest features (sd) |', '|---|---|---|---|---|');
  for (let c = 0; c < nClusters; c++) {
    const ms = table.maps.filter(m => m.cluster === c);
    out.push(`| ${c} | ${ms.length} | ${PICKS.map(p => ms.filter(m => m.picks === p).length).join('/')} | ${ms.filter(m => m.set === 'maps').map(m => m.name).slice(0, 6).join(' ')} | ${describe(c)} |`);
  }
  out.push('');

  for (const p of PICKS) {
    const th = model.picks[p].theta, Lm = model.picks[p].chol, q = prior[p].q, rp = rows.filter(r => r.picks === p);
    // Value of champion c on map z relative to the average champion, and its posterior sd.
    const valueVec = (c, z) => {
      const g = new Float64Array(P);
      for (let d = 0; d < NC; d++) {
        const wgt = (d === c ? 1 : 0) - 1 / NC;
        g[L.B + d] += wgt;
        for (let k = 0; k < K; k++) g[L.W + d * K + k] += wgt * z[k];
      }
      return g;
    };
    const est = g => { let s = 0; for (let j = 0; j < P; j++) s += g[j] * th[j]; const h = cholSolve(Lm, g); let v = 0; for (let j = 0; j < P; j++) v += g[j] * h[j]; return [s, Math.sqrt(Math.max(v, 0))]; };
    out.push(`## ${p} picks (${rp.length} games)`, '');
    // Optimal teams on every pool map: how often each champion is in one.
    const pool = table.maps.filter(m => m.picks === p), freq = new Float64Array(NC), teams = new Map();
    for (const m of pool) { const best = rankTeams(th, m.z, q, p)[0].T; for (const c of best) freq[c]++; const k = best.map(c => SHORT[c]).join(' '); teams.set(k, (teams.get(k) ?? 0) + 1); }
    out.push(`Model-best team against the ladder prior, over the ${pool.length} pool maps: ` +
      [...teams].sort((a, b) => b[1] - a[1]).slice(0, 6).map(([k, n]) => `${k} ${(100 * n / pool.length).toFixed(0)}%`).join('; ') + '.', '',
    `Champions in it: ${CHAMPS.map((_, c) => [c, freq[c]]).sort((a, b) => b[1] - a[1]).map(([c, n]) => `${SHORT[c]} ${(100 * n / pool.length).toFixed(0)}%`).join(', ')}.`, '');
    // Per champion: overall, per cluster (model), misfit (observed - model) and play stats.
    const header = ['Champion', 'games', 'all maps', ...Array.from({ length: nClusters }, (_, c) => `c${c}`)];
    out.push(`| ${header.join(' | ')} |`, `|${header.map(() => '---').join('|')}|`);
    const misfits = [], cells = [];
    for (let c = 0; c < NC; c++) {
      const on = rp.filter(r => r.A.includes(c) !== r.B.includes(c));
      const allZ = new Float64Array(K);
      for (const m of pool) for (let k = 0; k < K; k++) allZ[k] += m.z[k] / pool.length;
      const [s, sd] = est(valueVec(c, allZ));
      const row = [SHORT[c], on.length, `${pct(s)} ±${(PTS * 2 * sd).toFixed(1)}`];
      for (let cl = 0; cl < nClusters; cl++) {
        const ms = pool.filter(m => m.cluster === cl);
        if (!ms.length) { row.push('-'); continue; }
        const zc = new Float64Array(K);
        for (const m of ms) for (let k = 0; k < K; k++) zc[k] += m.z[k] / ms.length;
        const [sc, sdc] = est(valueVec(c, zc));
        // Observed minus model on this champion's games in the cluster: the linear map terms' misfit.
        let res = 0, varr = 0;
        for (const r of on) { if (table.byKey.get(r.key).cluster !== cl) continue; const pr = sigmoid(dot(th, r)), sgn = r.A.includes(c) ? 1 : -1; res += sgn * (r.win - pr); varr += pr * (1 - pr); }
        const zres = varr > 0 ? res / Math.sqrt(varr) : 0;
        misfits.push(zres); cells.push([c, cl, res, varr]);
        row.push(`${pct(sc)}${Math.abs(sc) > 2 * sdc ? '*' : ''}`);
      }
      out.push(`| ${row.join(' | ')} |`);
    }
    out.push('', `\\* more than 2 sd from the average champion.`, '');
    const flagged = bh(misfits);
    if (flagged.size) {
      out.push('Misfits (observed wins differ from the model in a cluster, Benjamini-Hochberg 10%): ' +
        [...flagged].map(i => { const [c, cl, res, v] = cells[i]; return `${SHORT[c]} c${cl} ${res > 0 ? '+' : ''}${res.toFixed(1)} wins over ${v.toFixed(0)} var (z ${misfits[i].toFixed(1)})`; }).join('; ') + '.', '');
    }
    // Biggest synergy and counter terms.
    const top = (base, n, f) => PAIRS.map(([a, b], i) => [a, b, th[base + i]]).sort((x, y) => Math.abs(y[2]) - Math.abs(x[2])).slice(0, n).map(f).join(', ');
    out.push(`Synergy (same team): ${top(L.SYN, 8, ([a, b, v]) => `${SHORT[a]}+${SHORT[b]} ${pct(v)}`)}.`, '',
      `Counters (row beats column): ${top(L.CTR, 8, ([a, b, v]) => v > 0 ? `${SHORT[a]}>${SHORT[b]} ${pct(v)}` : `${SHORT[b]}>${SHORT[a]} ${pct(-v)}`)}.`, '');
  }

  // Play statistics per champion appearance, per pick count and cluster, from the replays.
  const stat = new Map();
  for (const r of rows) {
    const ch = r.g.champions;
    if (!ch) continue;
    const cl = table.byKey.get(r.key).cluster, wonTeam = r.g.winner;
    for (const c of ch) {
      const k = `${r.picks}|${typeToDraft(c.type)}|${cl}`, s = stat.get(k) ?? { n: 0, collected: 0, tributed: 0, carried: 0, deaths: 0, kills: 0, campDmg: 0, campTaken: 0, wins: 0 };
      // Cassi and Issac are one pick: count the pick once and add both bodies' numbers.
      if (c.type !== 4) { s.n++; s.wins += c.team === wonTeam ? 1 : 0; }
      s.collected += c.collectedGems; s.tributed += c.submittedGems; s.carried += c.carried; s.deaths += c.deaths; s.kills += c.kills;
      s.campDmg += c.monsterDamageDone; s.campTaken += c.monsterDamageTaken;
      stat.set(k, s);
    }
  }
  if (stat.size) {
    out.push('## Play statistics per appearance', '', 'Gems collected / tributed / carried at the end, deaths and kills per game, raw win rate (not adjusted for teammates or opponents).', '');
    for (const p of PICKS) {
      out.push(`### ${p} picks`, '', '| Champion | cluster | n | collected | tributed | carried | deaths | kills | raw win |', '|---|---|---|---|---|---|---|---|---|');
      for (let c = 0; c < NC; c++) for (let cl = -1; cl < nClusters; cl++) {
        const sum = { n: 0, collected: 0, tributed: 0, carried: 0, deaths: 0, kills: 0, wins: 0 };
        for (let x = 0; x < nClusters; x++) if (cl < 0 || x === cl) { const s = stat.get(`${p}|${c}|${x}`); if (s) for (const f in sum) sum[f] += s[f]; }
        if (sum.n < (cl < 0 ? 1 : 30)) continue;
        const f = v => (v / sum.n).toFixed(0);
        out.push(`| ${SHORT[c]} | ${cl < 0 ? 'all' : `c${cl}`} | ${sum.n} | ${f(sum.collected)} | ${f(sum.tributed)} | ${f(sum.carried)} | ${(sum.deaths / sum.n).toFixed(2)} | ${(sum.kills / sum.n).toFixed(2)} | ${(100 * sum.wins / sum.n).toFixed(0)}% |`);
      }
      out.push('');
    }
  }
  fs.writeFileSync(path.join(lab, 'report.md'), out.join('\n') + '\n');
  console.log(`wrote ${path.join(lab, 'report.md')}`);
}

const cmd = process.argv[2], opts = args();
if (!opts.lab) { console.error('usage: node tools/draftlab/model.mjs fit|plan|report --lab DIR ...'); process.exit(2); }
const commands = { fit: fitCommand, plan: planCommand, report: reportCommand };
if (!commands[cmd]) { console.error(`unknown command ${cmd}`); process.exit(2); }
commands[cmd](opts);
