// Draft-and-map win-rate model fitted on ladder group metadata (fetch_replays.py --no-replays):
// P(team A wins) = sigmoid(S_A - S_B + e * Elo difference), where a team's score S sums, over its
// picks, that champion's intercept plus its weights on the map's features. Fitted by L2-penalised
// Newton; the penalty is chosen by leave-one-map-out cross-validation, since map terms only matter
// on maps the fit hasn't seen.
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { ALTAR, BUSH, CAMP, Grid } from '../mapgen/grid.mjs';
import { metrics } from '../mapgen/generate.mjs';
import { createEngine } from '../mapgen/wasm.mjs';

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..');
const MAPS = path.join(ROOT, 'maps');
// Indexed by the API's draft ids (the SDK's champion_draft order).
const CHAMPS = ['ryth', 'vesper_vale', 'vendetta', 'cassi_and_issac', 'stellar', 'prism', 'marcella', 'willow', 'ren', 'varg', 'tavi', 'heart_of_ruin'];
const FEATURES = ['size', 'altars', 'camps', 'power', 'gold_sum', 'gold_avg', 'gems_sum', 'gems_avg', 'bush', 'spawn_dist'];
const HP_STR = { wolf: [1350, 20], elk: [2400, 60], golem: [5000, 120], gem_cluster: [120, 0], gold_cluster: [120, 0], monolith: [20000, 200] };
const C = CHAMPS.length, K = FEATURES.length + 1;
// Elo falloff below --top-elo for the training weights (Infinity: every game counts fully).
const BANDWIDTHS = [50, 100, 200, 400, 800, Infinity];
// Map weights for the focus games: cross-validated within the same maps, so lighter penalties can pay.
const LAMBDA_W_FOCUS = [30, 100, 300, 1000, 3000, 3e4, Infinity];
const LAMBDA_B = [100, 1000, 1e4, 1e5], LAMBDA_W = [300, 3000, 3e4, 3e5, 3e6, Infinity];

// ---- map features ---------------------------------------------------------------------------

// The ladder's map name (00road_of_riches; older groups drop the prefix) as a file stem under maps/.
const mapKeys = new Map();
function mapKey(name) {
  if (!mapKeys.has(name)) mapKeys.set(name, findMap(name));
  return mapKeys.get(name);
}

function findMap(name) {
  const want = `${name.replace(/_/g, '-')}.map26a`, files = fs.readdirSync(MAPS);
  const hit = files.find(f => f === want) ?? files.find(f => f.replace(/^\d\d/, '') === want.replace(/^\d\d/, ''));
  return hit?.replace(/\.map26a$/, '');
}

// Whole-map counts over the engine's camp groups (cardinally connected camps), both sides.
function mapFeatures(g) {
  const groups = g.groups(), n = groups.length, sum = (a, f) => a.reduce((s, x) => s + f(x), 0);
  const respawn = q => Math.max(...q.members.map(c => CAMP[c.type].respawn));
  // Damage taken clearing a group scales with its hp and its Strength; clusters have none.
  const power = q => Math.sqrt(sum(q.members, c => HP_STR[c.type][0]) * sum(q.members, c => HP_STR[c.type][1]));
  const gold = sum(groups, q => q.gold / respawn(q)), gems = sum(groups, q => q.gems / respawn(q));
  const count = k => g.t.reduce((s, t) => s + (t === k), 0);
  return {
    size: g.W * g.H, altars: count(ALTAR), camps: n, power: sum(groups, power) / n,
    gold_sum: gold, gold_avg: gold / n, gems_sum: gems, gems_avg: gems / n,
    bush: count(BUSH) / g.t.length, spawn_dist: metrics(g).spawn_dist,
  };
}

async function loadMaps(keys) {
  const engine = await createEngine(), out = {};
  for (const key of keys) {
    const g = Grid.fromMap(engine.decode(fs.readFileSync(path.join(MAPS, `${key}.map26a`))));
    out[key] = { picks: g.picks, ...mapFeatures(g) };
  }
  return out;
}

// ---- games ----------------------------------------------------------------------------------

// Games as fetch.py stores them: { id, group, at, map, a, b }, each side { team, name, rating, draft, result, error }.
function* groupGames(dirs) {
  for (const dir of dirs) for (const d of fs.readdirSync(dir)) {
    const p = path.join(dir, d, 'group.json');
    if (!fs.existsSync(p)) continue;
    const { group, matches } = JSON.parse(fs.readFileSync(p, 'utf8'));
    if (group.kind !== 'ranked') continue;
    const rating = Object.fromEntries(group.sides.map(s => [s.teamId, s.ratingBefore]));
    for (const m of matches) {
      if (m.status !== 'finished') continue;
      const side = k => {
        const s = m.sides.find(x => x.side === k);
        return s && { team: s.teamId, name: s.teamName, rating: rating[s.teamId], draft: s.draft, result: s.result, error: s.botError };
      };
      yield { id: m.id, group: group.id, at: group.createdAt, map: m.map, a: side('a'), b: side('b') };
    }
  }
}

function* fileGames(file) {
  for (const line of fs.readFileSync(file, 'utf8').split('\n')) if (line) yield JSON.parse(line);
}

function loadGames(source, since, minRating) {
  const games = [], skipped = {}, seen = new Set(), skip = why => { skipped[why] = (skipped[why] ?? 0) + 1; };
  for (const m of source) {
    if (m.at < since || seen.has(m.id)) continue;
    seen.add(m.id);
    const { a, b } = m;
    if (!a || !b) { skip('unfinished'); continue; }
    if (!a.draft?.length || !b.draft?.length) { skip('no draft'); continue; }
    if (a.error || b.error) { skip('bot error'); continue; }
    if (!['win', 'loss'].includes(a.result)) { skip(`result ${a.result}`); continue; }
    const r = [a.rating, b.rating];
    if (r.some(v => typeof v !== 'number')) { skip('no rating'); continue; }
    if (minRating && !(Math.min(...r) >= minRating)) { skip('below --min-rating'); continue; }
    const map = mapKey(m.map);
    if (!map) { skip(`map ${m.map} not in maps/`); continue; }
    games.push({ id: m.id, group: m.group, map, teams: [a.name, b.name], picks: [a.draft.map(Number), b.draft.map(Number)], y: a.result === 'win' ? 1 : 0, r });
  }
  return { games, skipped };
}

// ---- model ----------------------------------------------------------------------------------

const sigmoid = z => 1 / (1 + Math.exp(-z));

// Dense row-major Cholesky solve of (symmetric positive definite) A x = b.
function solve(A, b, n) {
  const L = new Float64Array(n * n);
  for (let i = 0; i < n; i++) for (let j = 0; j <= i; j++) {
    let s = A[i * n + j];
    for (let k = 0; k < j; k++) s -= L[i * n + k] * L[j * n + k];
    L[i * n + j] = i === j ? Math.sqrt(Math.max(s, 1e-12)) : s / L[j * n + j];
  }
  const y = new Float64Array(n), x = new Float64Array(n);
  for (let i = 0; i < n; i++) { let s = b[i]; for (let k = 0; k < i; k++) s -= L[i * n + k] * y[k]; y[i] = s / L[i * n + i]; }
  for (let i = n - 1; i >= 0; i--) { let s = y[i]; for (let k = i + 1; k < n; k++) s -= L[k * n + i] * x[k]; x[i] = s / L[i * n + i]; }
  return x;
}

// Games as flat arrays: map index m, result y (team A won), Elo term r, and the champions in only
// one draft (mirror picks cancel): c[j], d[j] (+1 team A, -1 team B) for j in at[i]..at[i + 1].
function pack(games, mIndex) {
  const n = games.length, D = { n, m: new Int32Array(n), y: new Uint8Array(n), r: new Float64Array(n), at: new Int32Array(n + 1), z: new Float64Array(n) };
  const cs = [], ds = [];
  games.forEach((g, i) => {
    const d = new Map();
    for (const c of g.picks[0]) d.set(c, (d.get(c) ?? 0) + 1);
    for (const c of g.picks[1]) d.set(c, (d.get(c) ?? 0) - 1);
    for (const [c, v] of d) if (v) { cs.push(c); ds.push(v); }
    D.m[i] = mIndex.get(g.map);
    D.y[i] = g.y;
    D.r[i] = (g.r[0] - g.r[1]) * Math.LN10 / 400;
    D.at[i + 1] = cs.length;
  });
  D.c = Uint8Array.from(cs);
  D.d = Int8Array.from(ds);
  return D;
}

// U[m] = [1, standardised features]. Parameters: theta[c * K + k], then the rating weight. `w`
// weights the games (0 leaves one out; null: all 1); `init` (a fit with the same options) only
// warm-starts the search. The Hessian is built per map (sum over the map's games of w d d^T, times
// U U^T), so a Newton step costs O(games + maps * (C K)^2) whatever the game count.
function fit(D, U, { lb, lw, rating = false, champs = true }, init, w) {
  const M = U.length, P = C * K + (rating ? 1 : 0), theta = init ? Float64Array.from(init) : new Float64Array(P);
  const pen = new Float64Array(P);
  for (let c = 0; c < C; c++) for (let k = 0; k < K; k++) pen[c * K + k] = !champs ? 1e12 : k ? (lw === Infinity ? 1e12 : lw) : lb;
  if (rating) pen[C * K] = 1e-6;
  const { n, m, y, r, at, c: cs, d: ds, z } = D, V = new Float64Array(M * C);
  const objective = th => {
    for (let mm = 0; mm < M; mm++) for (let c = 0; c < C; c++) { let s = 0; for (let k = 0; k < K; k++) s += th[c * K + k] * U[mm][k]; V[mm * C + c] = s; }
    const beta = rating ? th[C * K] : 0;
    let nll = 0;
    for (let i = 0; i < n; i++) {
      const wi = w ? w[i] : 1;
      if (!wi) continue;
      let zi = beta * r[i];
      for (let j = at[i], base = m[i] * C; j < at[i + 1]; j++) zi += ds[j] * V[base + cs[j]];
      z[i] = zi;
      nll += wi * (y[i] ? Math.log1p(Math.exp(-zi)) : Math.log1p(Math.exp(zi)));
    }
    for (let i = 0; i < P; i++) nll += 0.5 * pen[i] * th[i] * th[i];
    return nll;
  };
  let obj = objective(theta);
  for (let iter = 0; iter < 60; iter++) {
    const G = new Float64Array(M * C), A = new Float64Array(M * C * C), B = new Float64Array(M * C);
    let gr = 0, hrr = 0;
    for (let i = 0; i < n; i++) {
      const wi = w ? w[i] : 1;
      if (!wi) continue;
      const p = sigmoid(z[i]), e = wi * (y[i] - p), h = wi * p * (1 - p), base = m[i] * C;
      for (let j = at[i]; j < at[i + 1]; j++) {
        const cj = base + cs[j], dj = ds[j];
        G[cj] += e * dj;
        for (let j2 = at[i]; j2 < at[i + 1]; j2++) A[cj * C + cs[j2]] += h * dj * ds[j2];
        if (rating) B[cj] += h * dj * r[i];
      }
      if (rating) { gr += e * r[i]; hrr += h * r[i] * r[i]; }
    }
    const grad = new Float64Array(P), H = new Float64Array(P * P);
    for (let mm = 0; mm < M; mm++) {
      const u = U[mm];
      for (let c = 0; c < C; c++) {
        const gc = G[mm * C + c];
        if (gc) for (let k = 0; k < K; k++) grad[c * K + k] += gc * u[k];
        for (let c2 = 0; c2 < C; c2++) {
          const a = A[(mm * C + c) * C + c2];
          if (!a) continue;
          for (let k = 0; k < K; k++) for (let k2 = 0; k2 < K; k2++) H[(c * K + k) * P + c2 * K + k2] += a * u[k] * u[k2];
        }
        if (rating && B[mm * C + c]) for (let k = 0; k < K; k++) { H[(c * K + k) * P + C * K] += B[mm * C + c] * u[k]; H[C * K * P + c * K + k] += B[mm * C + c] * u[k]; }
      }
    }
    if (rating) { grad[C * K] += gr; H[C * K * P + C * K] += hrr; }
    for (let i = 0; i < P; i++) { grad[i] -= pen[i] * theta[i]; H[i * P + i] += pen[i]; }
    const step = solve(H, grad, P);
    let t = 1, next, nobj;
    for (;;) {
      next = theta.map((v, i) => v + t * step[i]);
      nobj = objective(next);
      if (nobj <= obj + 1e-9 || t < 1e-4) break;
      t /= 2;
    }
    const done = obj - nobj < 1e-9 * Math.max(1, obj);
    theta.set(next);
    obj = nobj;
    if (done) break;
  }
  return { theta, beta: rating ? theta[C * K] : 0 };
}

function predict(model, U, D, i) {
  let z = model.beta * D.r[i];
  const u = U[D.m[i]];
  for (let j = D.at[i]; j < D.at[i + 1]; j++) {
    let v = 0;
    for (let k = 0; k < K; k++) v += model.theta[D.c[j] * K + k] * u[k];
    z += D.d[j] * v;
  }
  return sigmoid(z);
}

function score(probs, idx, D) {
  let ll = 0, brier = 0, hit = 0;
  idx.forEach((g, i) => {
    const p = Math.min(1 - 1e-9, Math.max(1e-9, probs[i])), y = D.y[g];
    ll -= y ? Math.log(p) : Math.log(1 - p);
    brier += (p - y) ** 2;
    hit += p === 0.5 ? 0.5 : (p > 0.5) === (y === 1) ? 1 : 0;
  });
  const n = idx.length;
  return { logloss: ll / n, brier: brier / n, accuracy: hit / n, n };
}

// Trains on the games outside each fold (weighted by `train` if given) and scores the fold's games
// (only those `test`, a 0/1 mask, keeps).
function crossValidate(D, U, opts, folds, { train, test } = {}) {
  const start = fit(D, U, opts, null, train).theta, w = new Float64Array(D.n), idx = [], probs = [];
  let nf = 0;
  for (const f of folds) nf = Math.max(nf, f + 1);
  for (let f = 0; f < nf; f++) {
    for (let i = 0; i < D.n; i++) w[i] = folds[i] !== f ? (train ? train[i] : 1) : 0;
    const model = fit(D, U, opts, start, w);
    for (let i = 0; i < D.n; i++) if (folds[i] === f && (!test || test[i])) { idx.push(i); probs.push(predict(model, U, D, i)); }
  }
  return score(probs, idx, D);
}

function hash(s) { let h = 2166136261; for (const ch of s) h = Math.imul(h ^ ch.charCodeAt(0), 16777619); return h >>> 0; }

function makeRng(seed) {
  let s = seed >>> 0;
  return () => { s = (s + 0x6D2B79F5) >>> 0; let t = Math.imul(s ^ (s >>> 15), 1 | s); t ^= t + Math.imul(t ^ (t >>> 7), 61 | t); return ((t ^ (t >>> 14)) >>> 0) / 4294967296; };
}

// ---- commands -------------------------------------------------------------------------------

function parseArgs(argv) {
  const opts = { _: [] };
  for (let i = 0; i < argv.length; i++) {
    if (!argv[i].startsWith('--')) { opts._.push(argv[i]); continue; }
    const key = argv[i].slice(2), val = argv[i + 1] && !argv[i + 1].startsWith('--') ? argv[++i] : true;
    opts[key] = val;
  }
  return opts;
}

const fmt = (v, d = 3) => (v >= 0 ? ' ' : '') + v.toFixed(d);
const pct = v => `${(100 * v).toFixed(1)}%`;

// Standardised value of champion c on map features z (the logit it adds to its team's score).
const value = (theta, c, u) => { let s = 0; for (let k = 0; k < K; k++) s += theta[c * K + k] * u[k]; return s; };

async function cmdFit(opts) {
  const since = opts.since ?? '2026-10-22', dirs = (opts.dirs ?? 'replays/ladder').split(',').map(d => path.resolve(ROOT, d));
  const out = path.resolve(ROOT, opts.out ?? 'replays/winrate'), boots = Number(opts.bootstrap ?? 200);
  const file = opts.games && path.resolve(ROOT, opts.games), source = file ? path.relative(ROOT, file) : dirs.map(d => path.relative(ROOT, d)).join(', ');
  const { games, skipped } = loadGames(file ? fileGames(file) : groupGames(dirs), since, opts['min-rating'] ? Number(opts['min-rating']) : 0);
  // --focus-dirs: groups (fetch_replays.py folders) whose games get their own comparison.
  const focus = opts['focus-dirs'] && new Set([...groupGames(opts['focus-dirs'].split(',').map(d => path.resolve(ROOT, d)))].map(m => m.group));
  const maps = await loadMaps(fs.readdirSync(MAPS).filter(f => f.endsWith('.map26a')).map(f => f.replace(/\.map26a$/, '')).sort());
  const used = games;
  if (!used.length) throw new Error(`no games since ${since} in ${source}`);

  // Standardise over games, so intercepts are values on the average game's map.
  const mapNames = [...new Set(used.map(g => g.map))].sort(), mIndex = new Map(mapNames.map((n, i) => [n, i]));
  const mean = FEATURES.map(f => used.reduce((s, g) => s + maps[g.map][f], 0) / used.length);
  const sd = FEATURES.map((f, k) => Math.sqrt(used.reduce((s, g) => s + (maps[g.map][f] - mean[k]) ** 2, 0) / used.length) || 1);
  const standard = f => [1, ...FEATURES.map((k, i) => (f[k] - mean[i]) / sd[i])];
  const U = mapNames.map(n => standard(maps[n]));
  const D = pack(used, mIndex), byGroup = Int32Array.from(used, g => hash(g.group) % 5), byMap = D.m;

  console.log(`${used.length} games, ${new Set(used.map(g => g.group)).size} groups, ${mapNames.length} maps since ${since}; skipped ${JSON.stringify(skipped)}`);
  // Penalties by leave-one-map-out log loss, with the rating term in (it soaks up team strength,
  // so the champion terms aren't credited with the skill of the teams that pick them).
  const grid = [];
  for (const lb of LAMBDA_B) for (const lw of LAMBDA_W) grid.push({ lb, lw, lomo: crossValidate(D, U, { lb, lw, rating: true }, byMap) });
  const best = grid.reduce((a, b) => (b.lomo.logloss < a.lomo.logloss ? b : a));
  const flat = grid.filter(x => x.lw === Infinity).reduce((a, b) => (b.lomo.logloss < a.lomo.logloss ? b : a));
  console.log(`best penalties: intercepts ${best.lb}, map weights ${best.lw}`);
  const main = { lb: best.lb, lw: best.lw, rating: true }, draftOnly = { lb: best.lb, lw: best.lw };

  const variants = [
    ['coin flip', null],
    ['Elo difference only', { lb: 1, lw: Infinity, rating: true, champs: false }],
    ['Elo + champion intercepts', { lb: flat.lb, lw: Infinity, rating: true }],
    ['Elo + intercepts + map features (the model)', main],
    ['intercepts + map features, no Elo (draft only)', draftOnly],
  ].map(([name, o]) => {
    if (!o) { const s = score(new Array(D.n).fill(0.5), [...Array(D.n).keys()], D); return { name, group: s, lomo: s }; }
    return { name, opts: o, group: crossValidate(D, U, o, byGroup), lomo: crossValidate(D, U, o, byMap) };
  });

  // Does the rest of the data help predict the focus games? Champion values differ by skill, so
  // games below --top-elo (by the two teams' mean) are weighted down by a Gaussian falloff in Elo.
  // Each training set is scored at its best penalties for those games (5-fold by group), so all are
  // equally optimistic; the best becomes the model.
  let focusRows = [], focusGroups = 0, focusPick = null, trainW = null;
  if (focus) {
    const top = Number(opts['top-elo'] ?? 2000), meanElo = used.map(g => (g.r[0] + g.r[1]) / 2);
    const inFocus = Uint8Array.from(used, g => (focus.has(g.group) ? 1 : 0));
    focusGroups = new Set(used.filter(g => focus.has(g.group)).map(g => g.group)).size;
    const best = train => LAMBDA_B.flatMap(lb => LAMBDA_W_FOCUS.map(lw => ({ lb, lw, ...crossValidate(D, U, { lb, lw, rating: true }, byGroup, { train, test: inFocus }) })))
      .reduce((a, b) => (b.logloss < a.logloss ? b : a));
    const elo = { lb: 1, lw: Infinity, rating: true, champs: false }, sum = w => w.reduce((s, v) => s + v, 0);
    focusRows = [
      { name: 'Elo only', games: D.n, ...crossValidate(D, U, elo, byGroup, { test: inFocus }) },
      { name: `the model, the focus groups' games only`, games: sum(inFocus), train: inFocus, ...best(inFocus) },
      ...BANDWIDTHS.map(h => {
        // Negligible weights are dropped so the fit skips those games.
        const train = Float64Array.from(meanElo, e => { const w = e >= top ? 1 : Math.exp(-0.5 * ((top - e) / h) ** 2); return w < 1e-4 ? 0 : w; });
        return { name: h === Infinity ? 'the model, every game at full weight' : `the model, games below ${top} Elo weighted with h = ${h}`, games: sum(train), train, ...best(train) };
      }),
    ];
    focusPick = focusRows.slice(1).reduce((a, b) => (b.logloss < a.logloss ? b : a));
    main.lb = draftOnly.lb = focusPick.lb;
    main.lw = draftOnly.lw = focusPick.lw;
    trainW = focusPick.train;
    console.log(`focus games: best training set "${focusPick.name}", penalties ${focusPick.lb} / ${focusPick.lw}`);
  }

  const model = fit(D, U, main, null, trainW), noElo = fit(D, U, draftOnly, null, trainW);
  // Cluster bootstrap over groups (a group is five games of the same two bots): each game weighted
  // by how often its group was drawn.
  const groups = [...new Set(used.map(g => g.group))], gIndex = new Map(groups.map((id, i) => [id, i]));
  const groupOf = Int32Array.from(used, g => gIndex.get(g.group)), drawn = new Uint16Array(groups.length), w = new Float64Array(D.n);
  const rng = makeRng(7), draws = CHAMPS.map(() => []);
  for (let b = 0; b < boots; b++) {
    drawn.fill(0);
    for (let i = 0; i < groups.length; i++) drawn[Math.floor(rng() * groups.length)]++;
    for (let i = 0; i < D.n; i++) w[i] = drawn[groupOf[i]] * (trainW ? trainW[i] : 1);
    const th = fit(D, U, main, model.theta, w).theta;
    CHAMPS.forEach((_, c) => draws[c].push(th[c * K]));
  }
  const quantile = (a, q) => { const s = [...a].sort((x, y) => x - y); return s[Math.min(s.length - 1, Math.floor(q * s.length))]; };

  // Per-champion usage and raw win rate in non-mirror games, over the games the model was trained on.
  const stat = CHAMPS.map(() => ({ picks: 0, nm: 0, wins: 0 }));
  used.forEach((g, i) => {
    if (trainW && !trainW[i]) return;
    for (const t of [0, 1]) for (const c of g.picks[t]) {
      stat[c].picks++;
      if (g.picks[1 - t].includes(c)) continue;
      stat[c].nm++;
      stat[c].wins += t === 0 ? g.y : 1 - g.y;
    }
  });

  // Raw-unit coefficients: c0 + sum_k c_k f_k equals the standardised value.
  const coefficients = theta => Object.fromEntries(CHAMPS.map((name, c) => {
    const w = FEATURES.map((_, k) => theta[c * K + k + 1]);
    const raw = { c0: theta[c * K] - w.reduce((s, v, k) => s + v * mean[k] / sd[k], 0) };
    FEATURES.forEach((f, k) => { raw[f] = w[k] / sd[k]; });
    return [name, { intercept: theta[c * K], weights: Object.fromEntries(FEATURES.map((f, k) => [f, w[k]])), raw }];
  }));
  fs.mkdirSync(out, { recursive: true });
  const json = {
    since, fitted: new Date().toISOString(), games: used.length, maps: mapNames, features: FEATURES, mean, sd,
    penalties: { intercepts: main.lb, weights: main.lw }, training: focusPick?.name ?? 'every game at full weight', elo: model.beta, champions: coefficients(model.theta),
    draftOnly: { champions: coefficients(noElo.theta) }, mapFeatures: maps,
    note: 'score(team) = sum over picks of c0 + sum_k raw[k] * feature_k; P(A wins) = sigmoid(score(A) - score(B) + elo * (Elo A - Elo B) * ln(10) / 400). '
      + 'Scores are relative to the average champion. draftOnly was fitted without the Elo term.',
  };
  fs.writeFileSync(path.join(out, 'model.json'), JSON.stringify(json, null, 1));

  // ---- report ----
  const L = [];
  L.push(`# Draft win-rate model (${since} on)`, '');
  L.push(`P(A wins) = sigmoid(S_A - S_B + e (Elo_A - Elo_B) ln10/400); S = sum over a team's picks of b_c + w_c . z(map), z the map's features standardised over games. `
    + `Champion terms are identified only up to a common shift (both teams pick the same number), so they are relative to the average champion.`, '');
  L.push(`- ${used.length} ranked games (${groups.length} groups) on ${mapNames.length} maps, from ${source}; skipped: ${Object.entries(skipped).map(([k, v]) => `${v} ${k}`).join(', ') || 'none'}.`);
  L.push(`- Team A won ${pct(used.reduce((s, g) => s + g.y, 0) / used.length)}. Penalties (leave-one-map-out): intercepts ${best.lb}, map weights ${best.lw}. Elo weight e = ${model.beta.toFixed(3)} (1 = what the rating itself predicts).`, '');
  L.push('## Cross-validated fit', '', '| Model | log loss (5-fold by group) | accuracy | log loss (leave one map out) | accuracy |', '|---|---|---|---|---|');
  for (const v of variants) L.push(`| ${v.name} | ${v.group.logloss.toFixed(4)} | ${pct(v.group.accuracy)} | ${v.lomo.logloss.toFixed(4)} | ${pct(v.lomo.accuracy)} |`);
  if (focusRows.length) {
    L.push('', `## Predicting the focus games (${focusRows[0].n} games in ${focusGroups} groups from --focus-dirs)`, '',
      `Trained on all ${D.n} games or a weighted part (the effective count is the sum of the weights); penalties are each row's best for these games. `
        + `The champion table, model.json and the drafts below use the best row: ${focusPick.name}.`, '',
      '| Training | effective games | penalties | log loss (5-fold by group) | accuracy |', '|---|---|---|---|---|');
    for (const v of focusRows) L.push(`| ${v.name} | ${Math.round(v.games)} | ${v.lb === undefined ? '-' : `${v.lb} / ${v.lw}`} | ${v.logloss.toFixed(4)} | ${pct(v.accuracy)} |`);
  }
  L.push('', '## Champions', '', `b: logit added to the team's score on the average map, 90% interval from ${boots} group bootstraps; b no Elo: the draft-only fit, which also credits champions with the skill of the teams that pick them.`, '');
  L.push(`| Champion | picks | non-mirror win | b | 90% | b no Elo | ${FEATURES.join(' | ')} |`, `|---|---|---|---|---|---|${FEATURES.map(() => '---').join('|')}|`);
  const order = CHAMPS.map((_, c) => c).sort((a, b) => model.theta[b * K] - model.theta[a * K]);
  for (const c of order) {
    const s = stat[c];
    L.push(`| ${CHAMPS[c]} | ${s.picks} | ${s.nm ? pct(s.wins / s.nm) : '-'} (${s.nm}) | ${fmt(model.theta[c * K])} | ${fmt(quantile(draws[c], 0.05), 2)}..${fmt(quantile(draws[c], 0.95), 2)} | ${fmt(noElo.theta[c * K])} | ${FEATURES.map((_, k) => fmt(model.theta[c * K + k + 1])).join(' | ')} |`);
  }
  L.push('', `Map weights are logit per standard deviation of the feature (sd: ${FEATURES.map((f, k) => `${f} ${+sd[k].toPrecision(3)}`).join(', ')}). Raw-unit coefficients are in model.json.`, '');
  const head = L.length;
  const counts = new Map();
  for (const g of used) counts.set(g.map, (counts.get(g.map) ?? 0) + 1);
  L.push('## Best draft per map', '', 'Champions by value on the map, the logit over the average champion; the top `picks` (bold) are the draft the model prefers. The score is additive, so the best draft ignores the opponent.', '');
  L.push('| Map | games | picks | ranking |', '|---|---|---|---|');
  for (const [name, f] of Object.entries(maps)) {
    const u = standard(f), rank = CHAMPS.map((_, c) => [c, value(model.theta, c, u)]).sort((a, b) => b[1] - a[1]);
    L.push(`| ${name} | ${counts.get(name) ?? 0} | ${f.picks} | ${rank.map(([c, v], i) => (i < f.picks ? `**${CHAMPS[c]} ${fmt(v, 2).trim()}**` : `${CHAMPS[c]} ${fmt(v, 2).trim()}`)).join(', ')} |`);
  }
  fs.writeFileSync(path.join(out, 'report.md'), L.join('\n') + '\n');
  console.log(L.slice(0, head).join('\n'));
  console.log(`\nwrote ${path.relative(ROOT, out)}/model.json and report.md`);
}

async function cmdPredict(opts) {
  const model = JSON.parse(fs.readFileSync(path.resolve(ROOT, opts.model ?? 'replays/winrate/model.json'), 'utf8'));
  const key = mapKey(opts.map) ?? opts.map, f = model.mapFeatures[key] ?? (mapKey(opts.map) && (await loadMaps([key]))[key]);
  if (!f) throw new Error(`unknown map ${opts.map}`);
  const champions = opts['draft-only'] ? model.draftOnly.champions : model.champions;
  const val = c => champions[c].raw.c0 + model.features.reduce((s, k) => s + champions[c].raw[k] * f[k], 0);
  const team = s => s.split(',').map(x => { const c = CHAMPS.find(n => n === x) ?? CHAMPS.find(n => n.startsWith(x)); if (!c) throw new Error(`unknown champion ${x}`); return c; });
  if (opts.a && opts.b) {
    const [A, B] = [team(opts.a), team(opts.b)], sa = A.reduce((s, c) => s + val(c), 0), sb = B.reduce((s, c) => s + val(c), 0);
    const elo = opts['draft-only'] ? 0 : model.elo * (Number(opts['elo-a'] ?? 0) - Number(opts['elo-b'] ?? 0)) * Math.LN10 / 400;
    console.log(`${key}: S_A ${sa.toFixed(3)}, S_B ${sb.toFixed(3)}, Elo term ${elo.toFixed(3)}, P(A wins) ${pct(sigmoid(sa - sb + elo))}`);
    return;
  }
  const rank = CHAMPS.map(c => [c, val(c)]).sort((a, b) => b[1] - a[1]);
  console.log(`${key} (${f.picks} picks):`);
  for (const [c, v] of rank) console.log(`  ${c.padEnd(16)} ${fmt(v)}`);
}

// The model's raw-unit coefficients as a C++ header for a draft bot.
function cmdCpp(opts) {
  const file = path.resolve(ROOT, opts.model ?? 'replays/winrate/model.json'), model = JSON.parse(fs.readFileSync(file, 'utf8'));
  const champions = opts['draft-only'] ? model.draftOnly.champions : model.champions, num = v => v.toPrecision(10);
  const rows = CHAMPS.map(c => `    {${['c0', ...model.features].map(k => num(champions[c].raw[k])).join(', ')}}, // ${c}`);
  process.stdout.write(`#pragma once
// Generated by \`node tools/winrate/winrate.mjs cpp\` from ${path.relative(ROOT, file)} (${model.games} ladder games from ${model.since}${opts['draft-only'] ? ', draft-only fit' : ''}).
// A champion's value on a map is c0 + sum_k coef[k + 1] * feature_k, the logit it adds to its team's score.

namespace aph::winrate {

// ${model.features.join(', ')}
inline constexpr int features = ${model.features.length};
// Over the fitted games; stands in for a feature the map leaves undefined.
inline constexpr double mean[features] = {${model.mean.map(num).join(', ')}};
// By champion_draft id.
inline constexpr double coef[${CHAMPS.length}][features + 1] = {
${rows.join('\n')}
};

} // namespace aph::winrate
`);
}

const [cmd, ...rest] = process.argv.slice(2), opts = parseArgs(rest);
if (cmd === 'fit') await cmdFit(opts);
else if (cmd === 'predict' && opts.map) await cmdPredict(opts);
else if (cmd === 'cpp') cmdCpp(opts);
else console.log(`node tools/winrate/winrate.mjs fit [--since 2026-10-22] [--dirs replays/ladder | --games replays/winrate/games.jsonl] [--focus-dirs replays/ladder [--top-elo 2000]] [--min-rating R] [--bootstrap 200] [--out replays/winrate]
node tools/winrate/winrate.mjs predict --map NAME [--a ryth,varg,... --b ... [--elo-a R --elo-b R]] [--draft-only] [--model replays/winrate/model.json]
node tools/winrate/winrate.mjs cpp [--draft-only] [--model replays/winrate/model.json] > winrate_model.h`);
