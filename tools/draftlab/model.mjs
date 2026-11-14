// Draft lab model (tools/draftlab/README.md): fit, plan a batch, report.
//   node tools/draftlab/model.mjs fit    --lab DIR [--search]
//   node tools/draftlab/model.mjs plan   --lab DIR --batch N --out FILE [--vehicles V] [--games G] [--mode explore|adapt]
//   node tools/draftlab/model.mjs report --lab DIR
//   node tools/draftlab/model.mjs cpp    --lab DIR [--out FILE]        # astraeus's src/draft/draft_model.h
//   node tools/draftlab/model.mjs teams  --lab DIR [--features FILE]   # the deployed draft per map
// P(A wins) = sigmoid(S(A) - S(B) + sum over a in A, b in B of M[a,b] + side), S(T) = sum over T of
// (b_c + w_c . z(map)) + sum over pairs in T of syn; M antisymmetric. One fit per pick count, penalised
// toward a fit pooled over pick counts; penalties and the soft-target weight by 5-fold cross-validation
// over maps, scored on wins only.
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import os from 'node:os';
import { Worker, isMainThread, workerData, parentPort } from 'node:worker_threads';
import { derived } from './derived.mjs';

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..');

export const CHAMPS = ['ryth', 'vesper_vale', 'vendetta', 'cassi_and_issac', 'stellar', 'prism', 'marcella', 'willow', 'ren', 'varg', 'tavi', 'heart_of_ruin'];
const SHORT = ['Ryth', 'Vesp', 'Vend', 'Cass', 'Stel', 'Pris', 'Marc', 'Will', 'Ren', 'Varg', 'Tavi', 'HoR'];
const NC = CHAMPS.length, PICKS = [3, 4, 5];
// [metric, transform]: features.mjs names. log for sizes and distances, log1p for counts that can be 0. The order is
// astraeus's map_features.h names (compute()'s output): append, never reorder. From dash_gain on (draft3): mapgen's
// quirk metrics (shapeMetrics), all but walk_split (dash_gain says it) and tele_gain (a crystal travel field from
// every map's spawn, too dear for the draft turn).
export const FEATURES = [
  ['area', 'log'], ['reach_frac'], ['spawn_dist', 'log'], ['detour'], ['choke_rel'], ['openness'], ['bushes'], ['holes'],
  ['altars', 'log1p'], ['altar_ratio'], ['altar_centre'], ['gems_side', 'log1p'], ['gold_side', 'log1p'], ['big_share'],
  ['cluster_share'], ['contested_share'], ['big_camp_share'], ['dash_short'], ['camp_near', 'log1p'],
  ['dash_gain', 'log'], ['narrow'], ['spawn_ring'], ['max_group', 'log1p'], ['camp_altar', 'log'], ['sight_gap'],
  // draftfeat (2026-11-06, research/notes/ideas-2026-11-05/draftfeat.md): mapgen metrics left out before, then derived ones
  // (derived.mjs: one_altar, squares and products of the transformed base features).
  ['monoliths', 'log1p'], ['golems', 'log1p'], ['camps_side', 'log1p'], ['walls'], ['shared_groups', 'log1p'],
  ['one_altar'], ['sq_area'], ['sq_reach_frac'], ['sq_spawn_dist'], ['sq_detour'], ['sq_choke_rel'], ['sq_openness'],
  ['sq_bushes'], ['sq_holes'], ['sq_altars'], ['sq_altar_ratio'], ['sq_altar_centre'], ['sq_gems_side'],
  ['sq_gold_side'], ['sq_big_share'], ['sq_cluster_share'], ['sq_contested_share'], ['sq_big_camp_share'],
  ['sq_dash_short'], ['sq_camp_near'], ['sq_dash_gain'], ['sq_narrow'], ['sq_spawn_ring'], ['sq_max_group'],
  ['sq_camp_altar'], ['sq_sight_gap'], ['pr_area__openness'], ['pr_area__altar_centre'], ['pr_area__gems_side'],
  ['pr_area__gold_side'], ['pr_area__contested_share'], ['pr_reach_frac__gems_side'], ['pr_reach_frac__gold_side'],
  ['pr_spawn_dist__altars'], ['pr_spawn_dist__altar_ratio'], ['pr_spawn_dist__dash_short'],
  ['pr_spawn_dist__dash_gain'], ['pr_detour__altar_ratio'], ['pr_choke_rel__dash_short'],
  ['pr_choke_rel__dash_gain'], ['pr_altars__gold_side'], ['pr_altar_ratio__gold_side'],
  ['pr_altar_ratio__big_camp_share'], ['pr_altar_centre__gems_side'], ['pr_altar_centre__gold_side'],
  ['pr_altar_centre__big_camp_share'], ['pr_altar_centre__dash_gain'], ['pr_altar_centre__camp_altar'],
  ['pr_gems_side__gold_side'], ['pr_gems_side__big_share'], ['pr_gems_side__cluster_share'],
  ['pr_gems_side__max_group'], ['pr_gold_side__big_share'], ['pr_gold_side__cluster_share'],
  ['pr_gold_side__contested_share'], ['pr_gold_side__big_camp_share'], ['pr_gold_side__max_group'],
  ['pr_big_share__cluster_share'], ['pr_big_share__big_camp_share'], ['pr_big_share__max_group'],
  ['pr_cluster_share__max_group'], ['pr_dash_short__dash_gain'],
];
const PAIRS = [], PI = Array.from({ length: NC }, () => new Int32Array(NC).fill(-1));
for (let i = 0; i < NC; i++) for (let j = i + 1; j < NC; j++) { PI[i][j] = PI[j][i] = PAIRS.length; PAIRS.push([i, j]); }
// The team lock (a user decision, 2026-11-03): every team we draft holds Cassi & Issac and never Stellar. Teams
// the model ranks for us (deployedTeam, Thompson, probes, reports) and our random teams obey it; ladder and other
// opponents' teams do not. A lab's config.json "team_lock" overrides it; draft_model.h carries it as masks.
export const TEAM_LOCK = { require: ['cassi_and_issac'], ban: ['stellar'] };
let LOCK, ALLOWED = {};
export function useLock(lock = TEAM_LOCK) {
  const mask = names => names.reduce((m, c) => m | (1 << cid(c)), 0);
  LOCK = { req: mask(lock.require ?? []), ban: mask(lock.ban ?? []), names: lock };
  ALLOWED = {};
}
const lockAllows = T => { let m = 0; for (const c of T) m |= 1 << c; return (m & LOCK.req) === LOCK.req && !(m & LOCK.ban); };
// Parameter layout for k map features and n opponent bots; a deployed model may have been fitted on others than the
// lab's (loadModel). Opponent terms (draft6, config.json "opponents"): per opponent bot an offset (OPP, its strength)
// and per-champion deviations (DEV: how it plays a champion unlike our bot), on the team that bot plays only. The bot
// deploys B, W, SYN, CTR; with n = 0 the layout is the one before.
function layoutOf(k, n = 0) {
  const lay = { K: k, B: 0, W: NC, SYN: NC + NC * k, CTR: NC + NC * k + PAIRS.length, SIDE: NC + NC * k + 2 * PAIRS.length };
  lay.OPP = lay.SIDE + 1; lay.DEV = lay.OPP + n; lay.N = n;
  lay.P = lay.DEV + n * NC;
  return lay;
}
const GROUPS = ['b', 'w', 'syn', 'ctr', 'side', 'opp', 'dev'];
// Penalties of the opponent groups when a lab's lam predates them.
const OPP_LAM = { opp: 1, dev: 64 };
// The lab's features (config.json "features", names in FEATURES order) and their layout. A config without the key is
// a lab from before draft3 (night1, draft2), fitted on the first 19. The bot measures only what its model reads, so a
// feature left out here costs no draft fuel once deployed.
export const LEGACY_FEATURES = FEATURES.slice(0, 19).map(f => f[0]);
let FEAT, K, L, P, GROUP, scratch, OPPS = [];
// opps: the opponent bots' names (config.json "opponents" less "self"), in config order.
function useFeatures(names, opps = OPPS) {
  FEAT = names ? FEATURES.filter(f => names.includes(f[0])) : FEATURES;
  if (names && FEAT.length !== names.length) throw new Error(`unknown features in ${names.join(',')}`);
  OPPS = opps;
  K = FEAT.length, L = layoutOf(K, OPPS.length), P = L.P, scratch = new Float64Array(P);
  GROUP = new Int8Array(P).map((_, j) => j < L.W ? 0 : j < L.SYN ? 1 : j < L.CTR ? 2 : j < L.SIDE ? 3 : j === L.SIDE ? 4 : j < L.DEV ? 5 : 6);
}
const oppsOf = cfg => Object.keys(cfg.opponents ?? {}).filter(o => o !== 'self');
// A game's bot index per side: -1 for the lab's own bot ("self", or a game from before draft6).
const botIndex = name => { if (!name || name === 'self') return -1; const i = OPPS.indexOf(name); if (i < 0) throw new Error(`unknown opponent bot ${name}`); return i; };
const lamVec = lam => Float64Array.from(GROUP, g => lam[GROUPS[g]] ?? OPP_LAM[GROUPS[g]]);
// The key that keeps a (map, drafts, bots) game from being planned twice; self-play keeps the old form.
const gameId = (key, A, B, botA = 'self', botB = 'self') => `${key}|${A}|${B}` + (botA === 'self' && botB === 'self' ? '' : `|${botA}|${botB}`);
useFeatures(null);
const FOLDS = 5, KAPPA = 5;
// A logit difference of d is about 25 d win-percentage points near 50%.
const PTS = 25;

// ---- io ---------------------------------------------------------------------------------------
// Read in chunks: a lab's games.jsonl outgrows Node's longest string (512 MB) near 170k games.
// Bytes [start, end) only, when given.
function readJsonl(f, start = 0, end = Infinity) {
  if (!fs.existsSync(f)) return [];
  const out = [], fd = fs.openSync(f, 'r'), buf = Buffer.alloc(1 << 24);
  let rest = '', pos = start;
  try {
    for (let n; pos < end && (n = fs.readSync(fd, buf, 0, Math.min(buf.length, end - pos), pos)) > 0;) {
      pos += n;
      const lines = (rest + buf.toString('utf8', 0, n)).split('\n');
      rest = lines.pop();
      for (const l of lines) if (l) out.push(JSON.parse(l));
    }
    if (rest.trim()) out.push(JSON.parse(rest));
  } finally { fs.closeSync(fd); }
  return out;
}
const readJson = (f, d = null) => fs.existsSync(f) ? JSON.parse(fs.readFileSync(f, 'utf8')) : d;

// A lab's games: lab.py keeps games.slim.jsonl, the fields read here of games.jsonl's first `bytes` (games.slim.json),
// ~8x smaller; games.jsonl past that is read in full. Slim games carry champions as SLIM_CHAMP arrays (champs()).
const SLIM_CHAMP = ['type', 'team', 'carried', 'collectedGems', 'submittedGems', 'deaths', 'kills', 'monsterDamageDone', 'monsterDamageTaken'];
function readGames(file) {
  const meta = readJson(file.replace(/\.jsonl$/, '.slim.json'));
  if (!meta) return readJsonl(file);
  return readJsonl(file.replace(/\.jsonl$/, '.slim.jsonl'), 0, meta.slim_bytes).concat(readJsonl(file, meta.bytes));
}
const champs = g => g.champions ?? g.ch?.map(a => Object.fromEntries(SLIM_CHAMP.map((k, i) => [k, a[i]])));
const cid = name => { const i = CHAMPS.indexOf(name); if (i < 0) throw new Error(`unknown champion ${name}`); return i; };
useLock();

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
  // Derived features (derived.mjs) from the row's other values when it predates them.
  const v = m.f[name] ?? derived(m.f, name);
  if (v === null || v === undefined || !Number.isFinite(v)) return NaN;
  return tf === 'log' ? Math.log(Math.max(v, 1)) : tf === 'log1p' ? Math.log1p(Math.max(v, 0)) : v;
}

// Standardised over the whole pool (not the games), so z(map) is the same in every batch's model.
function mapTable(lab) {
  const maps = readJsonl(path.join(lab, 'maps.jsonl')).filter(m => PICKS.includes(m.picks));
  const mean = FEAT.map(f => { const v = maps.map(m => raw(m, f)).filter(Number.isFinite); return v.reduce((a, b) => a + b, 0) / Math.max(1, v.length); });
  const sd = FEAT.map((f, k) => { const v = maps.map(m => raw(m, f)).filter(Number.isFinite); return Math.sqrt(v.reduce((a, b) => a + (b - mean[k]) ** 2, 0) / Math.max(1, v.length)) || 1; });
  const byKey = new Map();
  for (const m of maps) {
    m.z = Float64Array.from(FEAT, (f, k) => { const v = (raw(m, f) - mean[k]) / sd[k]; return Number.isFinite(v) ? Math.max(-4, Math.min(4, v)) : 0; });
    byKey.set(m.key, m);
  }
  return { maps, byKey, mean, sd };
}

// ---- design -----------------------------------------------------------------------------------
const touched = [];
function design(A, B, z, oa = -1, ob = -1) {
  const add = (i, v) => { if (scratch[i] === 0) touched.push(i); scratch[i] += v; if (scratch[i] === 0) scratch[i] = 1e-300; };
  for (const [T, s, o] of [[A, 1, oa], [B, -1, ob]]) {
    for (const c of T) { add(L.B + c, s); for (let k = 0; k < K; k++) if (z[k]) add(L.W + c * K + k, s * z[k]); }
    for (let i = 0; i < T.length; i++) for (let j = i + 1; j < T.length; j++) add(L.SYN + PI[T[i]][T[j]], s);
    if (o >= 0) { add(L.OPP + o, s); for (const c of T) add(L.DEV + o * NC + c, s); }
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
// config.json's prior_games (another lab's games, e.g. night1's under older bot logic) join at prior_weight and are
// never scored in cross-validation.
function gameRows(lab, table) {
  const rows = [], cfg = readJson(path.join(lab, 'config.json'), {});
  const sources = [[path.join(lab, 'games.jsonl'), 1, false]];
  if (cfg.prior_games && (cfg.prior_weight ?? 0.25) > 0) sources.push([path.join(ROOT, cfg.prior_games), cfg.prior_weight ?? 0.25, true]);
  for (const [file, w, prior] of sources) for (const g of readGames(file)) {
    if (g.error || g.winner === undefined || g.draft_ok === false) continue;
    const m = table.byKey.get(g.key);
    if (!m) continue;
    const A = g.A.map(cid), B = g.B.map(cid), oa = botIndex(g.botA), ob = botIndex(g.botB), r = design(A, B, m.z, oa, ob);
    const win = g.winner === 0 ? 1 : 0;
    let soft = win;
    if (g.wealth) { const [a, b] = g.wealth; soft = sigmoid(KAPPA * (a - b) / (a + b + 50)); }
    // om: the opponent bots in the game (bits), half: a split by game for the selection check.
    const om = (oa >= 0 ? 1 << oa : 0) | (ob >= 0 ? 1 << ob : 0);
    rows.push({ ...r, win, soft, w, prior, picks: g.picks, key: g.key, fold: hash(g.key) % FOLDS, om, half: hash(g.id ?? '') % 2, g, A, B, z: m.z });
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
  if (rows.pool) f = poolRun(2, th, alpha, rows).f;
  else for (const r of rows) { const e = dot(th, r), y = (1 - alpha) * r.win + alpha * r.soft; f += r.w * (softplus(e) - y * e); }
  for (let j = 0; j < P; j++) f += 0.5 * lamv[j] * (th[j] - th0[j]) ** 2;
  return f;
}

function newton(rows, lam, alpha, th0, init) {
  const lamv = lamVec(lam);
  let th = Float64Array.from(init ?? th0), f = objective(rows, th, th0, lamv, alpha), Lm = null;
  for (let it = 0; it < 25; it++) {
    let H = new Float64Array(P * P), g = new Float64Array(P);
    if (rows.pool) ({ H, g } = poolRun(1, th, alpha, rows));
    else for (const r of rows) {
      const p = sigmoid(dot(th, r)), y = (1 - alpha) * r.win + alpha * r.soft, res = r.w * (p - y), s = r.w * p * (1 - p);
      const { idx, val } = r, n = idx.length;
      for (let a = 0; a < n; a++) {
        g[idx[a]] += res * val[a];
        const sa = s * val[a], row = idx[a] * P;
        for (let b = 0; b <= a; b++) H[row + idx[b]] += sa * val[b];
      }
    }
    for (let j = 0; j < P; j++) { g[j] += lamv[j] * (th[j] - th0[j]); H[j * P + j] += lamv[j]; }
    const tc = now();
    Lm = cholesky(H);
    PROF.chol += now() - tc; PROF.iters++;
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
    const rp = rows.pool ? poolView(rows.exclude, p, rows.xopp, rows.xhalf) : rows.filter(r => r.picks === p);
    picks[p] = rp.length ? newton(rp, lam, alpha, pooled.theta, warm?.picks?.[p]?.theta) : { theta: pooled.theta, chol: pooled.chol };
  }
  return { pooled: pooled.theta, picks };
}

// ---- fit on worker threads ----------------------------------------------------------------------
// The rows packed into shared memory once; each worker sums the gradient and Hessian (cmd 1) or the objective (cmd 2)
// over its share of the rows a view selects (fold `exclude` left out, pick count `picks`, 0 for all), and the main
// thread waits on Atomics, so newton stays synchronous. Sums are by worker then added: the last bits differ from
// one thread's. ctrl: [generation, cmd, exclude, picks, done].
let POOL = null;
const PROF = { passes: 0, hess: 0, obj: 0, sum: 0, chol: 0, newtons: 0, iters: 0 };
const now = () => Number(process.hrtime.bigint()) / 1e9;
function startPool(rows, threads, force = false) {
  if (!force && (threads < 2 || rows.length < 20000)) return;
  const R = rows.length, nnz = rows.reduce((s, r) => s + r.idx.length, 0), shared = (T, n) => new T(new SharedArrayBuffer(T.BYTES_PER_ELEMENT * n));
  const d = { off: shared(Int32Array, R + 1), idx: shared(Int32Array, nnz), val: shared(Float64Array, nnz), win: shared(Float64Array, R),
    soft: shared(Float64Array, R), w: shared(Float64Array, R), picks: shared(Int8Array, R), fold: shared(Int8Array, R),
    om: shared(Int8Array, R), half: shared(Int8Array, R) };
  // In a fixed shuffled order: games.jsonl runs pick count by pick count within each batch, so contiguous shares would
  // leave most workers idle in the per-pick-count fits.
  const order = Array.from({ length: R }, (_, i) => i), rnd = rng(12345);
  for (let i = R - 1; i > 0; i--) { const j = Math.floor(rnd() * (i + 1)); [order[i], order[j]] = [order[j], order[i]]; }
  let o = 0;
  order.forEach((src, i) => {
    const r = rows[src];
    d.off[i] = o; d.idx.set(r.idx, o); d.val.set(r.val, o); o += r.idx.length;
    d.win[i] = r.win; d.soft[i] = r.soft; d.w[i] = r.w; d.picks[i] = r.picks; d.fold[i] = r.fold; d.om[i] = r.om ?? 0; d.half[i] = r.half ?? 0;
  });
  d.off[R] = o;
  const ctrl = shared(Int32Array, 8), th = shared(Float64Array, P + 1), workers = [], outs = [];
  for (let k = 0; k < threads; k++) {
    const out = shared(Float64Array, TRI(P) + P + 1);
    outs.push(out);
    workers.push(new Worker(new URL(import.meta.url), { workerData: { fitWorker: true, P, d, ctrl, th, out, lo: Math.floor(R * k / threads), hi: Math.floor(R * (k + 1) / threads) } }));
  }
  POOL = { rows, d, ctrl, th, outs, workers };
}
function stopPool() {
  if (!POOL) return;
  for (const w of POOL.workers) w.terminate();
  POOL = null;
}
// xopp: rows with any of these opponent bits left out; xhalf: the selection check's half left out (-1 none).
function poolView(exclude, picks, xopp = 0, xhalf = -1) {
  let n = 0;
  const { fold, picks: pk, om, half } = POOL.d;
  for (let i = 0; i < fold.length; i++) if (fold[i] !== exclude && (!picks || pk[i] === picks) && !(om[i] & xopp) && half[i] !== xhalf) n++;
  return { pool: true, exclude, picks, xopp, xhalf, length: n };
}
function poolRun(cmd, theta, alpha, view) {
  const { ctrl, th, outs } = POOL;
  th.set(theta); th[P] = alpha;
  ctrl[1] = cmd; ctrl[2] = view.exclude; ctrl[3] = view.picks; ctrl[5] = view.xopp ?? 0; ctrl[6] = view.xhalf ?? -1;
  Atomics.store(ctrl, 4, 0);
  Atomics.add(ctrl, 0, 1);
  Atomics.notify(ctrl, 0);
  const t0 = now();
  for (let done; (done = Atomics.load(ctrl, 4)) < outs.length;) Atomics.wait(ctrl, 4, done);
  const t1 = now();
  const nt = TRI(P);
  if (cmd === 2) { PROF.obj += t1 - t0; return { f: outs.reduce((s, out) => s + out[nt + P], 0) }; }
  PROF.hess += t1 - t0; PROF.passes++;
  const packed = new Float64Array(nt), H = new Float64Array(P * P), g = new Float64Array(P);
  for (const out of outs) {
    for (let j = 0; j < nt; j++) packed[j] += out[j];
    for (let j = 0; j < P; j++) g[j] += out[nt + j];
  }
  for (let i = 0, k = 0; i < P; i++) for (let j = 0; j <= i; j++) H[i * P + j] = packed[k++];
  PROF.sum += now() - t1;
  return { H, g };
}
// The worker's Hessian is the packed lower triangle (row i at TRI(i)): half the dense matrix, within a core's L2.
const TRI = n => n * (n + 1) / 2;
function fitWorker({ P: np, d, ctrl, th, out, lo, hi }) {
  const nt = TRI(np), H = out.subarray(0, nt), g = out.subarray(nt, nt + np);
  for (let gen = 0; ;) {
    Atomics.wait(ctrl, 0, gen);
    gen = Atomics.load(ctrl, 0);
    const cmd = ctrl[1], exclude = ctrl[2], picks = ctrl[3], xopp = ctrl[5], xhalf = ctrl[6], alpha = th[np];
    if (cmd === 1) { H.fill(0); g.fill(0); }
    let f = 0;
    for (let i = lo; i < hi; i++) {
      if (d.fold[i] === exclude || (picks && d.picks[i] !== picks) || (d.om[i] & xopp) || d.half[i] === xhalf) continue;
      const a0 = d.off[i], a1 = d.off[i + 1];
      let e = 0;
      for (let a = a0; a < a1; a++) e += th[d.idx[a]] * d.val[a];
      const y = (1 - alpha) * d.win[i] + alpha * d.soft[i], w = d.w[i];
      if (cmd === 2) { f += w * (softplus(e) - y * e); continue; }
      const p = sigmoid(e), res = w * (p - y), s = w * p * (1 - p);
      for (let a = a0; a < a1; a++) {
        const ia = d.idx[a], va = d.val[a];
        g[ia] += res * va;
        const sa = s * va, row = TRI(ia);
        for (let b = a0; b <= a; b++) H[row + d.idx[b]] += sa * d.val[b];
      }
    }
    out[nt + np] = f;
    Atomics.add(ctrl, 4, 1);
    Atomics.notify(ctrl, 4);
  }
}

// Times one gradient-and-Hessian pass over every game: one thread (newton's own loop), then the pool at each
// --threads count (default 1,8,16,32), at the lab's model (or zeros).
function fitbenchCommand(o) {
  const rows = gameRows(o.lab, mapTable(o.lab)), prev = loadModel(o.lab), th = prev ? prev.pooled ? Float64Array.from(prev.pooled) : new Float64Array(P) : new Float64Array(P);
  const time = f => { const t0 = process.hrtime.bigint(); f(); return Number(process.hrtime.bigint() - t0) / 1e9; };
  const lam = { b: OFF, w: OFF, syn: OFF, ctr: OFF, side: OFF, opp: OFF, dev: OFF }, lamv = lamVec(lam);
  if (!o['no-serial']) console.log(`${rows.length} games: 1 thread (serial) ${time(() => objective(rows, th, th, lamv, 0)).toFixed(2)} s objective, ` +
    `${time(() => { const H = new Float64Array(P * P), g = new Float64Array(P); for (const r of rows) { const p = sigmoid(dot(th, r)), res = p - r.win, s = p * (1 - p); for (let a = 0; a < r.idx.length; a++) { g[r.idx[a]] += res * r.val[a]; const sa = s * r.val[a], row = r.idx[a] * P; for (let b = 0; b <= a; b++) H[row + r.idx[b]] += sa * r.val[b]; } } }).toFixed(2)} s Hessian`);
  if (o.cv) {
    const m = readJson(path.join(o.lab, 'model.json')), n = +(o.threads ?? 32);
    startPool(rows, n, true);
    const warm = o.warm ? fitAll(poolView(-1, 0), m.lam, m.alpha ?? 0) : undefined;
    Object.keys(PROF).forEach(k => { PROF[k] = 0; });
    const t0 = now(), l = cvLoss(rows, m.lam, m.alpha ?? 0, warm), t = now() - t0;
    console.log(`cvLoss ${l.toFixed(5)} on ${n} threads: ${t.toFixed(1)} s; ${PROF.iters} newton steps, ${PROF.passes} Hessian passes ` +
      `${PROF.hess.toFixed(1)} s, objective ${PROF.obj.toFixed(1)} s, summing ${PROF.sum.toFixed(1)} s, cholesky ${PROF.chol.toFixed(1)} s, ` +
      `other ${(t - PROF.hess - PROF.obj - PROF.sum - PROF.chol).toFixed(1)} s`);
    stopPool();
    return;
  }
  for (const n of String(o.threads ?? '1,8,16,32').split(',').map(Number)) {
    POOL = null; startPool(rows, n, true);
    poolRun(1, th, 0, poolView(-1, 0));
    const tH = Math.min(...[0, 1, 2].map(() => time(() => poolRun(1, th, 0, poolView(-1, 0)))));
    const tF = Math.min(...[0, 1, 2].map(() => time(() => poolRun(2, th, 0, poolView(-1, 0)))));
    console.log(`${n} threads: Hessian ${tH.toFixed(3)} s, objective ${tF.toFixed(3)} s`);
    stopPool();
  }
}

function cvLoss(rows, lam, alpha, warm) {
  let loss = 0, n = 0;
  for (let k = 0; k < FOLDS; k++) {
    const train = POOL?.rows === rows ? poolView(k, 0) : rows.filter(r => r.fold !== k), test = rows.filter(r => r.fold === k && !r.prior);
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
  const prev = readJson(path.join(lab, 'model.json')), cfg = readJson(path.join(lab, 'config.json'), {});
  let lam = prev?.lam ?? cfg.initial_lam ?? { b: 1, w: 20, syn: 20, ctr: 20, side: 0.1 }, alpha = prev?.alpha ?? cfg.initial_alpha ?? 0;
  if (OPPS.length) lam = { ...OPP_LAM, ...lam };
  // --lam JSON: penalties to use (and start a search from) instead of the last ones.
  if (o.lam) lam = { ...lam, ...JSON.parse(o.lam) };
  const cv = {};
  startPool(rows, +(o.threads ?? process.env.DRAFTLAB_FIT_THREADS ?? Math.min(32, os.availableParallelism())));
  if (o.search) {
    const t0 = Date.now();
    // Every fold's fits start from the full fit at the starting penalties: the optimum is the same (the objective is
    // convex), in fewer Newton steps.
    const warm = fitAll(POOL ? poolView(-1, 0) : rows, lam, alpha), loss = (l, a) => cvLoss(rows, l, a, warm);
    let best = loss(lam, alpha);
    console.error(`cv start ${best.toFixed(5)} ${JSON.stringify(lam)} alpha ${alpha}`);
    // A ctr penalty of 1e8 or more pins the counters at 0 (draft3 on): never searched, so they stay out.
    // --groups a,b and --passes N narrow the search (draft6: F92's CV passes take minutes each).
    const searched = (o.groups ? String(o.groups).split(',') : ['w', 'syn', 'ctr', 'b', ...(OPPS.length ? ['dev'] : [])]).filter(g => g !== 'ctr' || lam.ctr < 1e8);
    for (let pass = 0; pass < +(o.passes ?? 2); pass++) {
      for (const gname of searched) for (const mul of [0.25, 4, 16]) {
        const tryLam = { ...lam, [gname]: lam[gname] * mul }, l = loss(tryLam, alpha);
        if (l < best - 1e-6) { best = l; lam = tryLam; console.error(`cv ${l.toFixed(5)} ${gname} x${mul}`); }
      }
      if (!o.groups) for (const a of [0, 0.3, 0.6]) if (a !== alpha) {
        const l = loss(lam, a);
        if (l < best - 1e-6) { best = l; alpha = a; console.error(`cv ${l.toFixed(5)} alpha ${a}`); }
      }
    }
    cv.model = best;
    cv.no_map = loss({ ...lam, w: OFF }, alpha);
    cv.no_pairs = loss({ ...lam, syn: OFF, ctr: OFF }, alpha);
    cv.no_syn = loss({ ...lam, syn: OFF }, alpha);
    cv.no_ctr = loss({ ...lam, ctr: OFF }, alpha);
    cv.intercepts = loss({ ...lam, w: OFF, syn: OFF, ctr: OFF }, alpha);
    cv.coin = Math.log(2);
    console.error(`search ${((Date.now() - t0) / 1000).toFixed(0)} s`);
  } else if (prev?.cv) Object.assign(cv, prev.cv, { stale: true });
  // From the last model (convex: the same optimum, in fewer Newton steps).
  const prevFit = prev?.features?.join() === FEAT.map(f => f[0]).join() && prev.pooled?.length === P ? prev : undefined;
  const fit = fitAll(POOL ? poolView(-1, 0) : rows, lam, alpha, prevFit);
  stopPool();
  const counts = Object.fromEntries(PICKS.map(p => [p, rows.filter(r => r.picks === p).length]));
  const round = a => Array.from(a, v => +v.toPrecision(7));
  const model = {
    created: new Date().toISOString(), games: rows.length, counts, champions: CHAMPS, features: FEAT.map(f => f[0]), opponents: OPPS,
    transforms: FEAT.map(f => f[1] ?? null), mean: table.mean, sd: table.sd, layout: L, lam, alpha, cv,
    pooled: round(fit.pooled), picks: Object.fromEntries(PICKS.map(p => [p, { theta: round(fit.picks[p].theta), chol: round(fit.picks[p].chol) }])),
  };
  // Renamed into place: lab.py plans the next batch while this runs.
  fs.writeFileSync(path.join(lab, 'model.json.tmp'), JSON.stringify(model));
  fs.renameSync(path.join(lab, 'model.json.tmp'), path.join(lab, 'model.json'));
  console.log(`fit ${rows.length} games (${PICKS.map(p => `${p}: ${counts[p]}`).join(', ')}); lam ${JSON.stringify(lam)} alpha ${alpha}` +
    (cv.model ? `; cv log loss ${cv.model.toFixed(4)} (no map ${cv.no_map.toFixed(4)}, no pairs ${cv.no_pairs.toFixed(4)}` +
      (cv.no_syn !== undefined ? `, no synergy ${cv.no_syn.toFixed(4)}, no counters ${cv.no_ctr.toFixed(4)}` : '') + `, intercepts ${cv.intercepts.toFixed(4)})` : ''));
}

// Learning curve: cross-validated log loss of each model variant on the first n exploration games (no Thompson or
// probe team, so the game mix is the same at every n), at model.json's penalties.
function curveCommand(o) {
  const lab = o.lab, table = mapTable(lab), prev = readJson(path.join(lab, 'model.json'));
  const lam = prev?.lam ?? { b: 1, w: 20, syn: 20, ctr: 20, side: 0.1 }, alpha = prev?.alpha ?? 0;
  const rows = gameRows(lab, table).filter(r => ![r.g.srcA, r.g.srcB].some(s => s === 'thompson' || s === 'probe'));
  const sizes = (o.sizes ? String(o.sizes).split(',').map(Number) : [1500, 3000, 6000, 12000]).filter(n => n < rows.length).concat(rows.length);
  console.log(`${rows.length} exploration games; lam ${JSON.stringify(lam)} alpha ${alpha}`);
  console.log('games | model | no map | no pairs | intercepts');
  for (const n of sizes) {
    const sub = rows.slice(0, n), f = l => cvLoss(sub, l, alpha).toFixed(4);
    console.log(`${n} | ${f(lam)} | ${f({ ...lam, w: OFF })} | ${f({ ...lam, syn: OFF, ctr: OFF })} | ${f({ ...lam, w: OFF, syn: OFF, ctr: OFF })}`);
  }
}

// Expected win rate against the ladder prior's teams (both sides averaged, so no side term) of: a given draft per pick
// count (--current), the model's best single team per pick count, and its best team on each map. Choices use the
// posterior mean; each is scored under posterior draws, so the gain is not inflated by choosing the luckiest estimate.
function gainCommand(o) {
  const lab = o.lab, table = mapTable(lab), model = loadModel(lab), prior = loadPrior(lab), r = rng(11), D = +(o.draws ?? 60);
  const current = Object.fromEntries(String(o.current ?? '3:marcella,vendetta,heart_of_ruin;4:prism,vendetta,marcella,heart_of_ruin;5:prism,vendetta,marcella,willow,heart_of_ruin')
    .split(';').map(s => s.split(':')).map(([p, d]) => [p, d.split(',').map(cid)]));
  const winP = (th, T, z, opps) => {
    const v = new Float64Array(NC);
    for (let c = 0; c < NC; c++) { let s = th[L.B + c]; for (let k = 0; k < K; k++) s += th[L.W + c * K + k] * z[k]; v[c] = s; }
    const team = X => { let s = 0; for (let i = 0; i < X.length; i++) { s += v[X[i]]; for (let j = i + 1; j < X.length; j++) s += th[L.SYN + PI[X[i]][X[j]]]; } return s; };
    const sT = team(T);
    let p = 0, w = 0;
    for (const { comp, n } of opps) {
      let e = sT - team(comp);
      for (const a of T) for (const b of comp) if (a !== b) e += (a < b ? 1 : -1) * th[L.CTR + PI[a][b]];
      p += n * sigmoid(e); w += n;
    }
    return p / w;
  };
  const out = [];
  for (const p of PICKS) {
    const th = model.picks[p].theta, q = prior[p].q, opps = prior[p].comps.slice(0, 40);
    for (const [label, maps] of [['pool', table.maps.filter(m => m.picks === p && !(readJson(path.join(lab, 'config.json'), {}).holdout ?? []).includes(m.set))], ['ladder', table.maps.filter(m => m.picks === p && m.set === 'maps')]]) {
      if (!maps.length) continue;
      // Best single team: highest mean value over these maps under the posterior mean (expected-counter ranking).
      const zbar = new Float64Array(K);
      for (const m of maps) for (let k = 0; k < K; k++) zbar[k] += m.z[k] / maps.length;
      const fixed = bestTeam(th, zbar, q, p), perMap = maps.map(m => bestTeam(th, m.z, q, p));
      const score = thd => {
        let a = 0, b = 0, c = 0;
        maps.forEach((m, i) => { a += winP(thd, current[p], m.z, opps); b += winP(thd, fixed, m.z, opps); c += winP(thd, perMap[i], m.z, opps); });
        return [a, b, c].map(x => x / maps.length);
      };
      const draws = Array.from({ length: D }, () => score(drawTheta(model, p, r)));
      const stat = f => { const xs = draws.map(f).sort((x, y) => x - y); return `${(100 * xs.reduce((s, x) => s + x, 0) / D).toFixed(1)} [${(100 * xs[Math.floor(0.05 * D)]).toFixed(1)}, ${(100 * xs[Math.ceil(0.95 * D) - 1]).toFixed(1)}]`; };
      const names = T => T.map(c => SHORT[c]).join(' ');
      out.push(`${p} picks, ${label} (${maps.length} maps): current ${names(current[p])} ${stat(d => d[0])}; best fixed ${names(fixed)} ${stat(d => d[1])}; per map ${stat(d => d[2])}`);
      out.push(`    per map - current ${stat(d => d[2] - d[0])} points; per map - best fixed ${stat(d => d[2] - d[1])}; best fixed - current ${stat(d => d[1] - d[0])}`);
    }
  }
  console.log(`Win % against the ladder prior's top 40 teams per pick count, mean [90% interval] over ${D} posterior draws:`);
  console.log(out.join('\n'));
}

// Stability of the model's choices: share of each pick count's pool maps where the best team (against the ladder
// prior) under model.json equals the one under --old FILE (an earlier model.json).
function compareCommand(o) {
  const lab = o.lab, table = mapTable(lab), prior = loadPrior(lab), now = loadModel(lab), old = loadModel(lab, o.old);
  const holdout = readJson(path.join(lab, 'config.json'), {}).holdout ?? [];
  for (const p of PICKS) {
    const maps = table.maps.filter(m => m.picks === p && !holdout.includes(m.set));
    const same = maps.filter(m => bestTeam(now.picks[p].theta, m.z, prior[p].q, p).join() === bestTeam(old.picks[p].theta, m.z, prior[p].q, p).join()).length;
    console.log(`${p} picks: same best team on ${same}/${maps.length} maps (${(100 * same / maps.length).toFixed(1)}%); games ${old.counts[p]} -> ${now.counts[p]}`);
  }
}

// The lab's own model must have the lab's features (fit, plan and the analyses share its layout); a deployed one
// (`any`) may have others: it carries its feature list (feat) and layout (lay).
function loadModel(lab, file = path.join(lab, 'model.json'), { any = false } = {}) {
  const m = readJson(file);
  if (!m) return null;
  m.feat = m.features.map((name, k) => [name, m.transforms[k] ?? undefined]);
  m.lay = layoutOf(m.features.length, m.opponents?.length ?? 0);
  const known = m.feat.every(([name, tf]) => FEATURES.some(f => f[0] === name && f[1] === tf));
  if (m.layout.P !== m.lay.P || !known) throw new Error(`${file}: features or transforms not in FEATURES`);
  if (!any && m.features.join() !== FEAT.map(f => f[0]).join()) throw new Error('model.json has another feature set; refit');
  if (!any && (m.opponents ?? []).join() !== OPPS.join()) throw new Error('model.json has other opponents; refit');
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
function champValues(th, z, q, lay = L) {
  const v = new Float64Array(NC);
  for (let c = 0; c < NC; c++) {
    let s = th[lay.B + c];
    for (let k = 0; k < lay.K; k++) s += th[lay.W + c * lay.K + k] * z[k];
    for (let d = 0; d < NC; d++) if (d !== c) s += q[d] * (c < d ? 1 : -1) * th[lay.CTR + PI[c][d]];
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

function teamValue(th, v, T, lay = L) {
  let s = 0;
  for (let i = 0; i < T.length; i++) { s += v[T[i]]; for (let j = i + 1; j < T.length; j++) s += th[lay.SYN + PI[T[i]][T[j]]]; }
  return s;
}

// Our teams, so only those the lock allows.
const allowed = p => ALLOWED[p] ??= COMBOS[p].filter(lockAllows);
function rankTeams(th, z, q, p, lay = L) {
  const v = champValues(th, z, q, lay);
  return allowed(p).map(T => ({ T, s: teamValue(th, v, T, lay) })).sort((a, b) => b.s - a.s);
}
// rankTeams(...)[0].T without the sort (ties go to the first, as the stable sort's).
function bestTeam(th, z, q, p, lay = L) {
  const v = champValues(th, z, q, lay);
  let best = null, top = -Infinity;
  for (const T of allowed(p)) { const s = teamValue(th, v, T, lay); if (s > top) { top = s; best = T; } }
  return best;
}

// Least opponent-dependent first, so the most counter-sensitive pick is made last (when most is known).
function pickOrder(th, T, q, lay = L) {
  const sens = c => { let s = 0; for (let d = 0; d < NC; d++) if (d !== c) s += q[d] * (1 - q[d]) * th[lay.CTR + PI[c][d]] ** 2; return s; };
  return [...T].sort((a, b) => sens(a) - sens(b));
}

function drawTheta(m, p, r) {
  const e = Float64Array.from({ length: P }, () => gauss(r)), d = cholBack(m.picks[p].chol, e), th = m.picks[p].theta;
  return th.map((v, j) => v + d[j]);
}

// ---- plan -------------------------------------------------------------------------------------
async function planCommand(o) {
  const lab = o.lab, batch = +o.batch, V = +(o.vehicles ?? 4), G = +(o.games ?? 3000), mode = o.mode ?? 'explore';
  const cfg = readJson(path.join(lab, 'config.json'), {});
  const shares = cfg.pick_shares ?? { 3: 0.33, 4: 0.33, 5: 0.34 }, holdout = new Set(cfg.holdout ?? []);
  const mix = mode === 'explore' ? (cfg.explore_mix ?? { explore: 1 }) : (cfg.mix ?? { explore: 0.15, thompson: 0.7, probe: 0.15 });
  const ladderOpp = cfg.ladder_opponent ?? 0.5, draws = cfg.thompson_draws ?? 16;
  const r = rng(hash(`${cfg.seed ?? 1}|${batch}`)), table = mapTable(lab), prior = loadPrior(lab);
  const model = mode === 'explore' ? null : loadModel(lab);
  if (mode !== 'explore' && !model) throw new Error('adapt mode needs model.json');
  // current: the team the source bot drafts (current_lab's model, the one its draft_model.h was generated from,
  // under this lab's lock, so the C++ team exactly), a source for our side beside random teams.
  const current = cfg.current_lab ? loadModel(path.resolve(ROOT, cfg.current_lab), undefined, { any: true }) : null;
  if (Object.keys(mix).includes('current') && !current) throw new Error('mix has current but config.json names no current_lab model');
  const seen = new Set(readGames(path.join(lab, 'games.jsonl')).map(g => gameId(g.key, g.A, g.B, g.botA, g.botB)));
  // --exclude PLAN[,PLAN]: batches planned but not merged yet (lab.py plans the next batch while one plays).
  for (const f of String(o.exclude ?? '').split(',').filter(Boolean)) for (const g of readJson(f).games) seen.add(gameId(g.key, g.A, g.B, g.botA, g.botB));
  // draft6: the bot playing the other side of each game, by config.json "opponents" shares ("self": the lab's own bot
  // on both sides, as before). Opponent bots draft from their own vehicles' tables (oppVehicles).
  const oppShares = cfg.opponents;
  const pickBot = () => { let x = r(), k = 'self'; for (const [s, w] of Object.entries(oppShares)) if ((x -= w) < 0) { k = s; break; } return k; };

  // Ladder maps every batch; the rest cycle through a fixed shuffle so batches cover the pool evenly.
  const chosen = [];
  for (const p of PICKS) {
    // prior: sets are the prior games' maps, for their features only.
    const pool = table.maps.filter(m => m.picks === p && !holdout.has(m.set) && !m.set.startsWith('prior:'));
    const ladder = pool.filter(m => m.set === 'maps'), rest = pool.filter(m => m.set !== 'maps');
    const order = rest.map(m => [hash(`${cfg.seed ?? 1}|${m.key}`), m]).sort((a, b) => a[0] - b[0]).map(x => x[1]);
    const want = Math.max(0, Math.round(shares[p] * G / V) - ladder.length);
    chosen.push(...ladder);
    for (let i = 0; i < Math.min(want, order.length); i++) chosen.push(order[(batch * want + i) % order.length]);
  }

  const shuffled = a => { for (let i = a.length - 1; i > 0; i--) { const j = Math.floor(r() * (i + 1)); [a[i], a[j]] = [a[j], a[i]]; } return a; };
  // Random teams leave out explore_exclude (Stellar: no top team drafts it and earlier labs never chose it).
  const allowed = Array.from({ length: NC }, (_, c) => c).filter(c => !(cfg.explore_exclude ?? []).includes(CHAMPS[c]));
  const choose = (n, k) => { let x = 1; for (let i = 0; i < k; i++) x = x * (n - i) / (i + 1); return x; };
  const explore = p => ({ T: shuffled(allowed.slice()).slice(0, p), src: 'explore', prob: 1 / choose(allowed.length, p) });
  // Our random teams (the learner's): the lock's required champions, the rest at random from what it allows.
  const req = Array.from({ length: NC }, (_, c) => c).filter(c => LOCK.req & (1 << c));
  const free = allowed.filter(c => !(LOCK.req & (1 << c)) && !(LOCK.ban & (1 << c)));
  const exploreOurs = p => {
    const T = shuffled([...req, ...shuffled(free.slice()).slice(0, p - req.length)]);
    return { T, src: 'explore', prob: 1 / choose(free.length, p - req.length) };
  };
  const ladderComp = p => {
    const pr = prior[p];
    let x = r() * pr.total;
    for (const e of pr.comps) if ((x -= e.n) < 0) return { T: e.comp.slice(), src: 'ladder', prob: e.n / pr.total };
    return explore(p);
  };
  const pickSrc = () => {
    let x = r(), k = 'explore';
    for (const [s, w] of Object.entries(mix)) if ((x -= w) < 0) { k = s; break; }
    return (k === 'thompson' || k === 'probe') && !model ? 'explore' : k;
  };

  // Thompson: the best team under each posterior draw, against the opponent prior; each map's draws seeded by the map,
  // so the plan is the same on any number of threads.
  const threads = +(o.threads ?? process.env.DRAFTLAB_PLAN_THREADS ?? Math.min(16, os.availableParallelism()));
  const tsAll = model ? await thompsonAll(model, chosen.map((m, i) => ({ p: m.picks, z: m.z, seed: hash(`${cfg.seed ?? 1}|${batch}|${i}|${m.key}`) })),
    Object.fromEntries(PICKS.map(p => [p, prior[p].q])), draws, threads) : null;

  const vehicles = Array.from({ length: V }, () => []), games = [];
  const oppVehicles = Object.fromEntries(OPPS.map(b => [b, Array.from({ length: V }, () => [])]));
  for (let mi = 0; mi < chosen.length; mi++) {
    const m = chosen[mi], p = m.picks, q = prior[p].q;
    let ts = null, mean = null;
    if (model) {
      ts = tsAll[mi];
      mean = rankTeams(model.picks[p].theta, m.z, q, p);
    }
    const cur = current ? bestTeam(noCounters(current.picks[p].theta, current.lay), zOf(current, m), q, p, current.lay) : null;
    const ours = src => src === 'current' && cur ? { T: cur.slice(), src: 'current', prob: 1 } : exploreOurs(p);
    const thompson = () => { let x = r() * draws; for (const e of ts) if ((x -= e.n) < 0) return { T: e.T.slice(), src: 'thompson', prob: e.n / draws }; return { T: ts[0].T.slice(), src: 'thompson', prob: ts[0].n / draws }; };
    let lastOpp = null;
    const names = T => T.map(c => CHAMPS[c]);
    const bots = (side, bot) => side === 0 ? ['self', bot] : [bot, 'self'];
    for (let k = 0; k < V; k++) {
      let game = null;
      for (let attempt = 0; attempt < 30 && !game; attempt++) {
        const src = pickSrc();
        // Probes pair with the previous game on this map: same opponent (team, side and bot), the mean model's runner-up.
        let learner, opp, learnerSide, bot = 'self';
        if (src === 'probe' && lastOpp) {
          ({ opp, side: learnerSide, bot } = lastOpp);
          const alt = mean.find(t => t.T.join() !== lastOpp.learner.join() && !seen.has(gameId(m.key, ...(learnerSide === 0 ? [names(t.T), names(opp.T)] : [names(opp.T), names(t.T)]), ...bots(learnerSide, bot))));
          learner = alt ? { T: alt.T.slice(), src: 'probe', prob: null } : exploreOurs(p);
        } else {
          learnerSide = r() < 0.5 ? 0 : 1;
          learner = src === 'thompson' ? thompson() : src === 'probe' ? (mean ? { T: mean[1].T.slice(), src: 'probe', prob: null } : exploreOurs(p)) : ours(src);
          opp = r() < ladderOpp ? ladderComp(p) : model && r() < 0.5 ? thompson() : explore(p);
          if (oppShares) bot = pickBot();
        }
        if (model && learner.src !== 'explore' && learner.src !== 'current') learner.T = pickOrder(model.picks[p].theta, learner.T, q).map(Number);
        const [A, B] = learnerSide === 0 ? [learner, opp] : [opp, learner];
        const id = gameId(m.key, names(A.T), names(B.T), ...bots(learnerSide, bot));
        if (seen.has(id)) continue;
        seen.add(id);
        game = { A, B, bot, learnerSide };
        lastOpp = { opp, side: learnerSide, bot, learner: learner.T.slice().sort((a, b) => a - b) };
      }
      if (!game) continue;
      const row = { vehicle: k, map: m.path, key: m.key, set: m.set, picks: p, A: names(game.A.T), B: names(game.B.T),
        srcA: game.A.src, srcB: game.B.src, probA: game.A.prob, probB: game.B.prob };
      if (game.bot === 'self') vehicles[k].push({ key: m.key, team: 0, comp: row.A }, { key: m.key, team: 1, comp: row.B });
      else {
        const ls = game.learnerSide;
        vehicles[k].push({ key: m.key, team: ls, comp: ls === 0 ? row.A : row.B });
        oppVehicles[game.bot][k].push({ key: m.key, team: 1 - ls, comp: ls === 0 ? row.B : row.A });
      }
      if (oppShares) [row.botA, row.botB] = bots(game.learnerSide, game.bot);
      games.push(row);
    }
  }
  fs.writeFileSync(o.out, JSON.stringify({ batch, mode, mix, created: new Date().toISOString(), vehicles, ...(OPPS.length ? { oppVehicles } : {}), games }));
  const bySrc = {}, byBot = {};
  for (const g of games) { for (const s of [g.srcA, g.srcB]) bySrc[s] = (bySrc[s] ?? 0) + 1; const b = g.botA === 'self' ? g.botB : g.botA; if (b) byBot[b] = (byBot[b] ?? 0) + 1; }
  console.log(`planned ${games.length} games on ${chosen.length} maps, ${V} vehicles; team sources ${JSON.stringify(bySrc)}` + (oppShares ? `; opponent bots ${JSON.stringify(byBot)}` : ''));
}
// jobs: [{p, z, seed}] -> per job [{T, n}], the draws' best teams and how often each was best.
function thompson(model, jobs, q, draws) {
  return jobs.map(({ p, z, seed }) => {
    const r = rng(seed), counts = new Map();
    for (let d = 0; d < draws; d++) { const k = bestTeam(drawTheta(model, p, r), z, q[p], p).join(); counts.set(k, (counts.get(k) ?? 0) + 1); }
    return [...counts].map(([k, n]) => ({ T: k.split(',').map(Number), n }));
  });
}
function planWorker({ features, opps, lock, model, jobs, q, draws }) {
  useFeatures(features, opps);
  useLock(lock);
  parentPort.postMessage(thompson(model, jobs, q, draws));
}
async function thompsonAll(model, jobs, q, draws, threads) {
  if (threads < 2 || jobs.length < 200) return thompson(model, jobs, q, draws);
  const shared = { features: FEAT.map(f => f[0]), opps: OPPS, lock: LOCK.names, q, draws,
    model: { picks: Object.fromEntries(PICKS.map(p => [p, { theta: model.picks[p].theta, chol: model.picks[p].chol }])) } };
  const parts = await Promise.all(Array.from({ length: threads }, (_, k) => new Promise((resolve, reject) => {
    const w = new Worker(new URL(import.meta.url), { workerData: { planWorker: true, ...shared,
      jobs: jobs.slice(Math.floor(jobs.length * k / threads), Math.floor(jobs.length * (k + 1) / threads)) } });
    w.once('message', resolve);
    w.once('error', reject);
    w.once('exit', code => code && reject(new Error(`plan worker exited with ${code}`)));
  })));
  return parts.flat();
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
  const describe = c => FEAT.map((f, k) => [f[0], cent[c][k]]).sort((a, b) => Math.abs(b[1]) - Math.abs(a[1])).slice(0, 3)
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
    for (const m of pool) { const best = bestTeam(th, m.z, q, p); for (const c of best) freq[c]++; const k = best.map(c => SHORT[c]).join(' '); teams.set(k, (teams.get(k) ?? 0) + 1); }
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
    const ch = champs(r.g);
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
  fs.writeFileSync(path.join(lab, `report.md.${process.pid}`), out.join('\n') + '\n');
  fs.renameSync(path.join(lab, `report.md.${process.pid}`), path.join(lab, 'report.md'));
  console.log(`wrote ${path.join(lab, 'report.md')}`);
}

// ---- ladder cross-check -----------------------------------------------------------------------
// ladder.jsonl (games among the top teams, ours included) with team effects, so a strong team's usual champions are not
// credited with its skill: logit P(A wins) = t_A - t_B + e (Elo_A - Elo_B) ln10/400 + side + sum over A of
// (b_c + w_c . z) - the same over B, per pick count. Champion effects are identified only by teams varying their
// drafts. Compared with the self-play model's champion values on the same maps.
function ladderCommand(o) {
  const lab = o.lab, table = mapTable(lab), model = loadModel(lab);
  const byName = new Map();
  for (const m of table.maps) { byName.set(m.name, m); byName.set(m.name.replace(/^\d\d/, ''), m); }
  const findMap = n => byName.get(n.replace(/_/g, '-')) ?? byName.get(n.replace(/_/g, '-').replace(/^\d\d/, ''));
  const games = readJsonl(path.join(lab, 'ladder.jsonl')).map(g => ({ ...g, m: findMap(g.map) })).filter(g => g.m && g.ratingA && g.ratingB);
  const teams = [...new Set(games.flatMap(g => [g.teamA, g.teamB]))], TI = new Map(teams.map((t, i) => [t, i]));
  const nB = NC, nW = NC * K, oT = nB + nW, oE = oT + teams.length, oS = oE + 1, n = oS + 1;
  const lam = Float64Array.from({ length: n }, (_, j) => j < nB ? +(o.lamb ?? 10) : j < oT ? +(o.lamw ?? 1000) : j < oE ? +(o.lamt ?? 1) : 0.01);
  const out = [`Ladder cross-check: ${games.length} games among the top teams on ${new Set(games.map(g => g.m.key)).size} maps, ${teams.length} teams.`];
  for (const p of PICKS) {
    const rows = games.filter(g => g.A.length === p && g.B.length === p).map(g => {
      const x = new Float64Array(n);
      for (const [T, s] of [[g.A, 1], [g.B, -1]]) for (const name of T) { const c = cid(name); x[c] += s; for (let k = 0; k < K; k++) x[nB + c * K + k] += s * g.m.z[k]; }
      x[oT + TI.get(g.teamA)] += 1; x[oT + TI.get(g.teamB)] -= 1; x[oE] = (g.ratingA - g.ratingB) * Math.LN10 / 400; x[oS] = 1;
      const idx = [], val = [];
      x.forEach((v, j) => { if (v) { idx.push(j); val.push(v); } });
      return { idx, val, y: g.winner === 0 ? 1 : 0, m: g.m };
    });
    if (rows.length < 200) { out.push(`${p} picks: ${rows.length} games, skipped`); continue; }
    let th = new Float64Array(n), H;
    for (let it = 0; it < 30; it++) {
      H = new Float64Array(n * n); const g = new Float64Array(n);
      for (const r of rows) {
        let e = 0; for (let a = 0; a < r.idx.length; a++) e += th[r.idx[a]] * r.val[a];
        const pr = sigmoid(e), s = pr * (1 - pr);
        for (let a = 0; a < r.idx.length; a++) { g[r.idx[a]] += (pr - r.y) * r.val[a]; for (let b = 0; b < r.idx.length; b++) H[r.idx[a] * n + r.idx[b]] += s * r.val[a] * r.val[b]; }
      }
      for (let j = 0; j < n; j++) { g[j] += lam[j] * th[j]; H[j * n + j] += lam[j]; }
      const d = solveDense(H, g, n);
      th = th.map((v, j) => v - d[j]);
      if (Math.max(...d.map(Math.abs)) < 1e-7) break;
    }
    // Champion value relative to the average champion, averaged over these games' maps, with its sd.
    const zbar = new Float64Array(K);
    for (const r of rows) for (let k = 0; k < K; k++) zbar[k] += r.m.z[k] / rows.length;
    const vec = c => { const v = new Float64Array(n); for (let d = 0; d < NC; d++) { const w = (d === c ? 1 : 0) - 1 / NC; v[d] += w; for (let k = 0; k < K; k++) v[nB + d * K + k] += w * zbar[k]; } return v; };
    const sp = model.picks[p].theta, selfVal = c => { let s = 0; for (let d = 0; d < NC; d++) { const w = (d === c ? 1 : 0) - 1 / NC; s += w * sp[L.B + d]; for (let k = 0; k < K; k++) s += w * sp[L.W + d * K + k] * zbar[k]; } return s; };
    const res = CHAMPS.map((_, c) => { const v = vec(c), h = solveDense(H, v, n); let est = 0, vr = 0; for (let j = 0; j < n; j++) { est += v[j] * th[j]; vr += v[j] * h[j]; } return { c, est, sd: Math.sqrt(Math.max(vr, 0)), self: selfVal(c), n: rows.filter(r => r.idx.includes(c)).length }; });
    const clear = res.filter(r => Math.abs(r.est) > 2 * r.sd), agree = clear.filter(r => Math.sign(r.est) === Math.sign(r.self)).length;
    const xs = res.map(r => r.est), ys = res.map(r => r.self), mx = xs.reduce((a, b) => a + b) / NC, my = ys.reduce((a, b) => a + b) / NC;
    const corr = xs.reduce((s, x, i) => s + (x - mx) * (ys[i] - my), 0) / Math.sqrt(xs.reduce((s, x) => s + (x - mx) ** 2, 0) * ys.reduce((s, y) => s + (y - my) ** 2, 0));
    const tsd = Math.sqrt(teams.reduce((s, _, i) => s + th[oT + i] ** 2, 0) / teams.length);
    out.push('', `${p} picks: ${rows.length} games; Elo coefficient ${th[oE].toFixed(2)}, team effects sd ${(PTS * tsd).toFixed(1)} points; ` +
      `correlation with self-play champion values ${corr.toFixed(2)}; ${clear.length} champions clear of 2 sd, ${agree} agree in sign with self-play.`,
      '| Champion | games with | ladder (points) | self-play (points) |', '|---|---|---|---|',
      ...res.sort((a, b) => b.est - a.est).map(r => `| ${SHORT[r.c]} | ${r.n} | ${r.est >= 0 ? '+' : ''}${(PTS * r.est).toFixed(1)} ±${(PTS * 2 * r.sd).toFixed(1)} | ${r.self >= 0 ? '+' : ''}${(PTS * r.self).toFixed(1)} |`));
  }
  const text = out.join('\n') + '\n';
  fs.writeFileSync(path.join(lab, 'ladder.md'), text);
  console.log(text);
}

// Dense symmetric positive definite solve (Cholesky) for any size n.
function solveDense(H, b, n) {
  const Lm = new Float64Array(n * n);
  for (let i = 0; i < n; i++) for (let j = 0; j <= i; j++) {
    let s = H[i * n + j];
    for (let k = 0; k < j; k++) s -= Lm[i * n + k] * Lm[j * n + k];
    Lm[i * n + j] = i === j ? Math.sqrt(Math.max(s, 1e-12)) : s / Lm[j * n + j];
  }
  const y = Float64Array.from(b);
  for (let i = 0; i < n; i++) { let s = y[i]; for (let k = 0; k < i; k++) s -= Lm[i * n + k] * y[k]; y[i] = s / Lm[i * n + i]; }
  for (let i = n - 1; i >= 0; i--) { let s = y[i]; for (let k = i + 1; k < n; k++) s -= Lm[k * n + i] * y[k]; y[i] = s / Lm[i * n + i]; }
  return y;
}

// ---- deployment -------------------------------------------------------------------------------
// The deployed draft (astraeus draft.cc model_draft): z from the model's own mean and sd, the best
// team against the ladder prior, in pickOrder. map_features.cc model_team is the same in C++.
function zOf(model, m) {
  return Float64Array.from(model.feat, (f, k) => { const v = (raw(m, f) - model.mean[k]) / model.sd[k]; return Number.isFinite(v) ? Math.max(-4, Math.min(4, v)) : 0; });
}
// The bot has no counter terms (cross-validation fitted them to ~1e-4), so it scores teams without them and
// picks in champion id order: nothing it drafts depends on the opponent's picks.
// The bot's first-round team in pick order. Without counters (the bot's draft_model.h then has none) it is in
// champion id order; with them, least opponent-dependent first (pickOrder). Later rounds re-rank against the
// opponent's revealed picks in the bot only (map_features.cc model_team).
// deploy (a lab config's "deploy", draft6): {kappa, draws, top, seed}: with kappa > 0 the team is lcbTeam's over the
// deployment draws (deployDraws, the ones draft_model.h carries); no counters.
export function deployedTeam(model, prior, m, counters = false, deploy = null) {
  const p = m.picks;
  if (!PICKS.includes(p)) return null;
  const lay = model.lay, th = counters ? model.picks[p].theta : noCounters(model.picks[p].theta, lay);
  if (deploy?.kappa > 0 && !counters) return lcbTeam(th, deployDraws(model, deploy, p), zOf(model, m), prior[p].q, p, deploy.kappa, lay, deploy.top ?? 64);
  const T = bestTeam(th, zOf(model, m), prior[p].q, p, lay);
  return counters ? pickOrder(th, T, prior[p].q, lay) : T;
}
// The deployed model's posterior draws (counters zeroed) for pick count p, in its own layout; cached.
const DRAWS = new Map();
export function deployDraws(model, deploy, p) {
  const k = `${model.created}|${deploy.seed}|${deploy.draws}|${p}`;
  if (DRAWS.has(k)) return DRAWS.get(k);
  const n = model.lay.P, Lm = model.picks[p].chol, th = model.picks[p].theta, r = rng(hash(`deploy|${deploy.seed ?? 1}|${p}`));
  const out = Array.from({ length: deploy.draws ?? 32 }, () => {
    const y = Float64Array.from({ length: n }, () => gauss(r));
    for (let i = n - 1; i >= 0; i--) { let s = y[i]; for (let k2 = i + 1; k2 < n; k2++) s -= Lm[k2 * n + i] * y[k2]; y[i] = s / Lm[i * n + i]; }
    return noCounters(th.map((v, j) => v + y[j]), model.lay);
  });
  DRAWS.set(k, out);
  return out;
}
const noCounters = (th, lay = L) => { const out = Float64Array.from(th); out.fill(0, lay.CTR, lay.CTR + PAIRS.length); return out; };
// Above this (logit) the dropped counter terms could change a team the bot drafts.
const COUNTER_LIMIT = 1e-3;
export const loadDeployed = lab => {
  const cfg = readJson(path.join(lab, 'config.json'), {});
  useLock(cfg.team_lock ?? TEAM_LOCK);
  return { model: loadModel(lab, undefined, { any: true }), prior: loadPrior(lab), deploy: cfg.deploy ?? null };
};

// One line per map (features.mjs rows): key, picks, name, the team in pick order.
function teamsCommand(o) {
  const { model, prior, deploy } = loadDeployed(o.lab);
  if (!model) throw new Error('no model.json');
  for (const m of readJsonl(o.features ? path.resolve(o.features) : path.join(o.lab, 'maps.jsonl'))) {
    const T = deployedTeam(model, prior, m, !!o.counters, deploy);
    console.log(`${m.key} ${m.picks} ${m.name} ${T ? T.map(c => CHAMPS[c]).join(',') : '-'}`);
  }
}

// draft_model.h for astraeus (map_features.cc): everything model_team needs, as exact doubles
// (String(x) is the shortest round-trip form, so each C++ literal parses to the same double).
function cppCommand(o) {
  const { model, prior, deploy } = loadDeployed(o.lab), counters = !!o.counters;
  const lcb = deploy?.kappa > 0 && !counters;
  if (!model) throw new Error('no model.json');
  const lay = model.lay;
  const out = o.out ? path.resolve(o.out) : path.join(ROOT, 'bots', 'astraeus', 'src', 'draft', 'draft_model.h');
  const num = v => { if (!Number.isFinite(v)) throw new Error(`non-finite value ${v}`); return String(v); };
  const list = (a, per, indent) => {
    const xs = Array.from(a, num), rows = [];
    for (let i = 0; i < xs.length; i += per) rows.push(xs.slice(i, i + per).join(', '));
    return rows.length > 1 ? `{\n${rows.map(r => `${indent}    ${r},`).join('\n')}\n${indent}}` : `{${rows[0] ?? ''}}`;
  };
  const tf = { log: 'tf_log', log1p: 'tf_log1p' };
  // Labs live in the main checkout's replays/draftlab/ (gitignored): name it so from a worktree too.
  const rel = path.relative(ROOT, path.resolve(o.lab)).split(path.sep).join('/');
  const labName = rel.startsWith('..') ? `replays/draftlab/${path.basename(path.resolve(o.lab))}` : rel, npairs = PAIRS.length;
  const blocks = PICKS.map(p => {
    const th = model.picks[p].theta;
    const counter = Math.max(...th.subarray(lay.CTR, lay.CTR + npairs).map(Math.abs));
    if (!counters && counter > COUNTER_LIMIT) throw new Error(`${p} picks: counter terms up to ${counter}: generate with --counters, or refit without them`);
    const ctr = counters ? th.subarray(lay.CTR, lay.CTR + npairs) : new Float64Array(npairs);
    const w = Array.from({ length: NC }, (_, c) => `            ${list(th.subarray(lay.W + c * lay.K, lay.W + (c + 1) * lay.K), 10, '            ')},`);
    return [`    {`, `        ${p},`, `        ${list(th.subarray(lay.B, lay.B + NC), NC, '        ')},`, `        {`, ...w, `        },`,
      `        ${list(th.subarray(lay.SYN, lay.SYN + npairs), 6, '        ')},`, `        ${list(ctr, 6, '        ')},`,
      `        ${list(prior[p].q, NC, '        ')},`, `    },`].join('\n');
  });
  const text = `#pragma once
// Generated by \`node tools/draftlab/model.mjs cpp --lab ${labName}${counters ? ' --counters' : ''}\`: its model.json of
// ${model.created} (${model.games} games) and prior.json. Do not edit; regenerate after a refit.
// Read by map_features.cc model_team, which mirrors model.mjs deployedTeam.
namespace aph::draft_model {

inline constexpr int champions = ${NC}, features = ${lay.K}, pairs = ${npairs};
// cambc::champion_draft order (model.mjs CHAMPS).
inline constexpr const char* champion_names[champions] = {${CHAMPS.map(c => `"${c}"`).join(', ')}};
enum Transform : int { tf_none, tf_log, tf_log1p };
inline constexpr const char* feature_names[features] = {${model.feat.map(f => `"${f[0]}"`).join(', ')}};
inline constexpr Transform transforms[features] = {${model.feat.map(f => tf[f[1]] ?? 'tf_none').join(', ')}};
// z = clamp((transform(raw) - mean) / sd, -4, 4), 0 where raw is missing.
inline constexpr double mean[features] = ${list(model.mean, 5, '')};
inline constexpr double sd[features] = ${list(model.sd, 5, '')};

// model.mjs PAIRS: (i, j) with i < j, in lexicographic order.
constexpr int pair(int i, int j) { return i < j ? i * champions - i * (i + 1) / 2 + j - i - 1 : pair(j, i); }

struct PickModel {
    int picks;
    double b[champions];
    double w[champions][features];
    double syn[pairs]; // same-team pair terms
    // Counter terms: for our c against their d, sign(c < d) * ctr[pair(c, d)]; all 0 unless generated with
    // --counters. q: the ladder prior's chance of each champion in the opponent's team (model.mjs loadPrior).
    double ctr[pairs];
    double q[champions];
};
inline constexpr bool counters = ${counters};
// The team lock (model.mjs TEAM_LOCK), bits by champion id: every team we draft holds all of required and none of
// banned (required: ${LOCK.names.require?.join(', ') || 'none'}; banned: ${LOCK.names.ban?.join(', ') || 'none'}).
inline constexpr unsigned required = ${LOCK.req}u, banned = ${LOCK.ban}u;

inline constexpr PickModel models[] = {
${blocks.join('\n')}
};

// draft6's lower-confidence-bound rule (model.mjs lcbTeam): with kappa > 0, the top teams by the mean score are
// re-scored as mean - kappa x sd over these posterior draws (b, w, syn; counters 0) of the team's score less the
// candidates' mean score in the same draw. kappa 0: the mean's best team (no draws).
inline constexpr double kappa = ${lcb ? num(deploy.kappa) : 0};
inline constexpr int draws = ${lcb ? deploy.draws ?? 32 : 0}, top = ${lcb ? deploy.top ?? 64 : 0};
${lcb ? `struct PickDraws {
    int picks;
    double b[draws][champions];
    double w[draws][champions][features];
    double syn[draws][pairs];
};
inline constexpr PickDraws draw_models[] = {
${PICKS.map(p => { const ds = deployDraws(model, deploy, p); return [`    {`, `        ${p},`,
    `        {${ds.map(d => list(d.subarray(lay.B, lay.B + NC), NC, '        ')).join(', ')}},`,
    `        {${ds.map(d => `{${Array.from({ length: NC }, (_, c) => list(d.subarray(lay.W + c * lay.K, lay.W + (c + 1) * lay.K), 1000, '')).join(', ')}}`).join(',\n         ')}},`,
    `        {${ds.map(d => list(d.subarray(lay.SYN, lay.SYN + npairs), 1000, '')).join(',\n         ')}},`, `    },`].join('\n'); }).join('\n')}
};` : ''}

} // namespace aph::draft_model
`;
  fs.writeFileSync(out, text);
  console.log(`wrote ${path.relative(ROOT, out)} (model of ${model.created}, ${model.games} games)`);
}


// ---- draft6: opponent transfer and the selection check -----------------------------------------
// Leave-one-opponent-out CV (draft6.md): for each opponent bot o, fit without any game against it, then predict its
// games with its champion deviations at 0 and its offset u_o (one number) fitted on half of its maps (hash of the key)
// and scored on the other half, both ways. Also the usual map-fold CV scored on each opponent's games and on
// self-play. --lam JSON overrides model.json's penalties.
//   node tools/draftlab/model.mjs oppcv --lab DIR [--lam JSON] [--threads N]
function oppcvCommand(o) {
  const lab = o.lab, table = mapTable(lab), rows = gameRows(lab, table), m = readJson(path.join(lab, 'model.json'));
  if (!OPPS.length) throw new Error('no opponents in config.json');
  const lam = { ...OPP_LAM, ...m.lam, ...(o.lam ? JSON.parse(o.lam) : {}) }, alpha = m.alpha ?? 0;
  startPool(rows, +(o.threads ?? 32), true);
  const warm = fitAll(poolView(-1, 0), lam, alpha);
  const ll = (e, y) => softplus(e) - y * e;
  const out = { lam, alpha, looo: {}, mapcv: {} };
  for (let i = 0; i < OPPS.length; i++) {
    const fit = fitAll(poolView(-1, 0, 1 << i), lam, alpha, warm);
    const test = rows.filter(r => r.om & (1 << i));
    // Each test row's linear predictor without u_o and the sign u_o enters with.
    const e0 = test.map(r => dot(fit.picks[r.picks].theta, r));
    const sg = test.map(r => { for (let a = 0; a < r.idx.length; a++) if (r.idx[a] === L.OPP + i) return r.val[a]; return 0; });
    const halfOf = r => hash(`opp|${r.key}`) % 2;
    let loss = 0, coin = 0, n = 0;
    const us = [];
    for (const h of [0, 1]) {
      let u = 0;
      for (let it = 0; it < 30; it++) {
        let g = 0, H = 1e-9;
        test.forEach((r, j) => { if (halfOf(r) !== h) return; const p = sigmoid(e0[j] + u * sg[j]); g += (p - r.win) * sg[j]; H += p * (1 - p); });
        u -= g / H;
        if (Math.abs(g / H) < 1e-9) break;
      }
      us.push(u);
      test.forEach((r, j) => { if (halfOf(r) === h) return; loss += ll(e0[j] + u * sg[j], r.win); coin += Math.log(2); n++; });
    }
    out.looo[OPPS[i]] = { games: n, loss: loss / n, coin: coin / n, u: us };
    console.error(`looo ${OPPS[i]}: ${n} games, log loss ${(loss / n).toFixed(5)} (u ${us.map(u => u.toFixed(3)).join(', ')})`);
  }
  // Map-fold CV, scored by who the opponent was (the same 5 folds as cvLoss).
  const acc = {};
  for (let k = 0; k < FOLDS; k++) {
    const fit = fitAll(poolView(k, 0), lam, alpha, warm);
    for (const r of rows) {
      if (r.fold !== k || r.prior) continue;
      const who = r.om ? OPPS[Math.log2(r.om & -r.om)] : 'self', a = acc[who] ??= { loss: 0, n: 0 };
      a.loss += ll(dot(fit.picks[r.picks].theta, r), r.win); a.n++;
    }
  }
  for (const [who, a] of Object.entries(acc)) out.mapcv[who] = { games: a.n, loss: a.loss / a.n };
  stopPool();
  console.log(JSON.stringify(out));
}

// The deployed rule with a lower confidence bound (draft6.md): rank teams by the posterior mean (no counters), keep
// the top `top`, and score each by mean - kappa x sd over posterior draws of its score less the kept teams' mean
// score in the same draw. kappa 0 is bestTeam. draws: [{b, w, syn}] in the layout of th (lay).
export function lcbTeam(th, draws, z, q, p, kappa, lay = L, top = 64) {
  const v = champValues(th, z, q, lay);
  const ranked = allowed(p).map(T => ({ T, s: teamValue(th, v, T, lay) })).sort((a, b) => b.s - a.s);
  if (!kappa || !draws?.length) return ranked[0].T;
  const cand = ranked.slice(0, top), D = draws.length, S = cand.map(() => new Float64Array(D));
  draws.forEach((thd, d) => {
    const vd = champValues(thd, z, q, lay);
    let mean = 0;
    cand.forEach((c, i) => { S[i][d] = teamValue(thd, vd, c.T, lay); mean += S[i][d]; });
    mean /= cand.length;
    for (let i = 0; i < cand.length; i++) S[i][d] -= mean;
  });
  let best = null, bs = -Infinity;
  cand.forEach((c, i) => {
    let m = 0; for (let d = 0; d < D; d++) m += S[i][d]; m /= D;
    // Products, not **, so map_features.cc's sums match bit for bit.
    let vv = 0; for (let d = 0; d < D; d++) { const x = S[i][d] - m; vv += x * x; }
    const sc = c.s - kappa * Math.sqrt(vv / (D - 1));
    if (sc > bs) { bs = sc; best = c.T; }
  });
  return best;
}
// D posterior draws of a fit's theta (counters zeroed), seeded.
function drawsOf(theta, chol, D, seed) {
  const r = rng(seed);
  return Array.from({ length: D }, () => {
    const e = Float64Array.from({ length: P }, () => gauss(r)), d = cholBack(chol, e);
    return noCounters(theta.map((v, j) => v + d[j]));
  });
}

// Split-half selection check (draft6.md): fit on each half of the games (by game id), choose per map the team under
// that half's posterior (kappa grid; --mult scales the w and syn penalties for more shrinkage), and value it under the
// other half's posterior mean against the base's own team (current_lab's), as win % against the ladder prior's top 40
// teams. "self" values it under the choosing half: the gap between the two is the optimizer's curse.
//   node tools/draftlab/model.mjs selcheck --lab DIR [--kappas 0,0.5,1,2,3] [--mult 1,4] [--maps N] [--draws 32]
function selcheckCommand(o) {
  const lab = o.lab, table = mapTable(lab), rows = gameRows(lab, table), m = readJson(path.join(lab, 'model.json'));
  const cfg = readJson(path.join(lab, 'config.json'), {}), prior = loadPrior(lab), D = +(o.draws ?? 32);
  const current = loadModel(path.resolve(ROOT, cfg.current_lab), undefined, { any: true });
  const kappas = String(o.kappas ?? '0,0.5,1,1.5,2,3').split(',').map(Number), mults = String(o.mult ?? '1').split(',').map(Number);
  const lam0 = { ...OPP_LAM, ...m.lam }, alpha = m.alpha ?? 0;
  const r = rng(77), pool = table.maps.filter(x => PICKS.includes(x.picks) && x.set !== 'maps' && !String(x.set).startsWith('prior:'));
  const sample = pool.map(x => [r(), x]).sort((a, b) => a[0] - b[0]).slice(0, +(o.maps ?? 1500)).map(x => x[1]);
  const evalMaps = [...table.maps.filter(x => PICKS.includes(x.picks) && x.set === 'maps').map(x => ({ m: x, kind: 'ladder' })), ...sample.map(x => ({ m: x, kind: 'pool' }))];
  const winP = (th, T, z, opps) => {
    const v = champValues(th, z, new Float64Array(NC));
    const sT = teamValue(th, v, T);
    let pr = 0, w = 0;
    for (const { comp, n } of opps) { pr += n * sigmoid(sT - teamValue(th, v, comp)); w += n; }
    return pr / w;
  };
  startPool(rows, +(o.threads ?? 32), true);
  const res = [];
  for (const mult of mults) {
    const lam = { ...lam0, w: lam0.w * mult, syn: lam0.syn * mult };
    const fits = [0, 1].map(h => fitAll(poolView(-1, 0, 0, 1 - h), lam, alpha));
    // One set of draws per half and pick count for every map, as the bot's header carries.
    const drawSets = [0, 1].map(h => Object.fromEntries(PICKS.map(p => [p, drawsOf(fits[h].picks[p].theta, fits[h].picks[p].chol, D, hash(`${h}|${p}`))])));
    const acc = new Map();
    for (const { m: mp, kind } of evalMaps) {
      const p = mp.picks, q = prior[p].q, opps = prior[p].comps.slice(0, 40);
      const T0 = bestTeam(noCounters(current.picks[p].theta, current.lay), zOf(current, mp), q, p, current.lay);
      const oneAltar = mp.f.altars === 1;
      for (const h of [0, 1]) {
        const mine = fits[h].picks[p], other = fits[1 - h].picks[p];
        const draws = drawSets[h][p];
        for (const kappa of kappas) {
          const T = lcbTeam(noCounters(mine.theta), draws, mp.z, q, p, kappa);
          const same = T.join() === [...T0].sort((a, b) => a - b).join() ? 1 : 0;
          const honest = winP(noCounters(other.theta), T, mp.z, opps) - winP(noCounters(other.theta), T0, mp.z, opps);
          const selfv = winP(noCounters(mine.theta), T, mp.z, opps) - winP(noCounters(mine.theta), T0, mp.z, opps);
          for (const tag of [kind, `${kind}-${oneAltar ? 'one' : 'multi'}`, `${kind}-${p}`]) {
            const k = `${mult}|${kappa}|${tag}`, a = acc.get(k) ?? { n: 0, honest: 0, honest2: 0, self: 0, same: 0 };
            a.n++; a.honest += honest; a.honest2 += honest * honest; a.self += selfv; a.same += same;
            acc.set(k, a);
          }
        }
      }
    }
    for (const [k, a] of acc) {
      const [mu, ka, tag] = k.split('|'), mean = a.honest / a.n, sd = Math.sqrt(Math.max(0, a.honest2 / a.n - mean * mean) / a.n);
      res.push({ mult: +mu, kappa: +ka, tag, maps: a.n / 2, honest: 100 * mean, se: 100 * sd, self: 100 * a.self / a.n, changed: 1 - a.same / a.n });
    }
  }
  stopPool();
  res.sort((x, y) => x.tag.localeCompare(y.tag) || x.mult - y.mult || x.kappa - y.kappa);
  console.log('| mult | kappa | maps | honest gain (points) | se | self-assessed | teams changed |');
  console.log('|---|---|---|---|---|---|---|');
  for (const x of res) console.log(`| ${x.tag} x${x.mult} | ${x.kappa} | ${x.maps} | ${x.honest.toFixed(2)} | ${x.se.toFixed(2)} | ${x.self.toFixed(2)} | ${(100 * x.changed).toFixed(0)}% |`);
}

// The composition game's equilibrium per pick count: the meta rational opponents converge to under this model.
//   node tools/draftlab/model.mjs nash --lab DIR [--model FILE] [--top N] [--maps M] [--iters I]
//        [--blend PRIOR.json --alpha A --out PRIOR.json]
// Payoff of team A against B is P(A beats B) averaged over a sample of the lab's maps (side term dropped, so the game
// is symmetric zero-sum). Without counter terms the game is transitive and the equilibrium is the strongest team,
// so --model should be a fit with counters on (opponent modelling only; the bot keeps counters off). Teams are
// unrestricted (opponents have no lock), pruned to the --top strongest by mean value. Fictitious play; prints the
// mixture and its exploitability. --blend writes n(c) = n_prior(c) + alpha * p_nash(c), keyed by champion set (the
// prior's pick order kept; equilibrium-only teams in id order).
function nashCommand(o) {
  const model = loadModel(o.lab, o.model ? path.resolve(o.model) : undefined, { any: true }), lay = model.lay;
  const top = +(o.top ?? 150), nMaps = +(o.maps ?? 400), iters = +(o.iters ?? 20000), alpha = +(o.alpha ?? 200);
  const maps = readJsonl(path.join(o.lab, 'maps.jsonl')).filter(m => PICKS.includes(m.picks) && !String(m.set ?? '').startsWith('prior:'));
  const out = {};
  for (const p of PICKS) {
    const th = model.picks[p].theta, r = rng(1000 + p);
    const ms = maps.filter(m => m.picks === p).sort(() => r() - 0.5).slice(0, nMaps).map(m => zOf(model, m));
    const teams = COMBOS[p], q0 = new Float64Array(NC);
    // Per-map team values without counters: champValues with an empty prior.
    const val = teams.map(T => Float64Array.from(ms, z => teamValue(th, champValues(th, z, q0, lay), T, lay)));
    const mean = val.map(v => v.reduce((a, b) => a + b, 0) / v.length);
    const idx = mean.map((s, i) => [s, i]).sort((a, b) => b[0] - a[0]).slice(0, top).map(x => x[1]);
    const N = idx.length, C = new Float64Array(N * N);
    for (let i = 0; i < N; i++) for (let j = 0; j < N; j++) if (i !== j) {
      let c = 0;
      for (const a of teams[idx[i]]) for (const b of teams[idx[j]]) if (a !== b) c += (a < b ? 1 : -1) * th[lay.CTR + PI[a][b]];
      C[i * N + j] = c;
    }
    // Fictitious play on one payoff matrix: each step adds the best response to the running mixture.
    const solve = (A, n) => {
      const cnt = new Float64Array(N), u = new Float64Array(N);
      let br = 0;
      for (let t = 0; t < n; t++) {
        cnt[br] += 1;
        for (let i = 0; i < N; i++) u[i] += A[i * N + br];
        br = 0; for (let i = 1; i < N; i++) if (u[i] > u[br]) br = i;
      }
      const x = Array.from(cnt, c => c / n);
      let worst = -Infinity;
      for (let i = 0; i < N; i++) { let s = 0; for (let j = 0; j < N; j++) s += A[i * N + j] * x[j]; worst = Math.max(worst, s); }
      return { x, exploit: worst };
    };
    const payoff = ks => {
      const A = new Float64Array(N * N);
      for (let i = 0; i < N; i++) for (let j = i + 1; j < N; j++) {
        const vi = val[idx[i]], vj = val[idx[j]];
        let s = 0;
        for (const k of ks) s += sigmoid(vi[k] - vj[k] + C[i * N + j]);
        A[i * N + j] = s / ks.length - 0.5; A[j * N + i] = -A[i * N + j];
      }
      return A;
    };
    // Teams draft per map: by default each map's own equilibrium, averaged over maps (--pooled: one game on the
    // map-averaged payoffs).
    let x, exploit;
    if (o.pooled) ({ x, exploit } = solve(payoff(ms.map((_, k) => k)), iters));
    else {
      x = new Array(N).fill(0); exploit = 0;
      const per = Math.max(500, Math.round(iters / 10));
      for (let k = 0; k < ms.length; k++) {
        const r1 = solve(payoff([k]), per);
        for (let i = 0; i < N; i++) x[i] += r1.x[i] / ms.length;
        exploit += r1.exploit / ms.length;
      }
    }
    const mix = idx.map((ti, i) => ({ comp: teams[ti].map(c => CHAMPS[c]), p: x[i] })).filter(e => e.p >= 1e-3).sort((a, b) => b.p - a.p);
    const share = new Float64Array(NC);
    for (const e of mix) for (const c of e.comp) share[CHAMPS.indexOf(c)] += e.p;
    const maxCtr = Math.max(...th.subarray(lay.CTR, lay.CTR + PAIRS.length).map(Math.abs));
    console.log(`${p} picks: ${N} teams on ${ms.length} maps; max |counter| ${maxCtr.toFixed(4)}; exploitability ${(100 * exploit).toFixed(2)} pts; ` +
      `strongest alone ${teams[idx[0]].map(c => SHORT[c]).join('+')}`);
    for (const e of mix.slice(0, 12)) console.log(`  ${(100 * e.p).toFixed(1)}% ${e.comp.join(', ')}`);
    console.log(`  champion shares: ${CHAMPS.map((c, i) => [c, share[i]]).sort((a, b) => b[1] - a[1]).filter(e => e[1] > 0.005).map(([c, s]) => `${c} ${(100 * s).toFixed(0)}%`).join(', ')}`);
    out[p] = mix;
  }
  if (o.out) {
    const prior = o.blend ? readJson(path.resolve(o.blend)) : {};
    const res = { ...prior, nash: { alpha, model: o.model ?? 'model.json', created: new Date().toISOString() } };
    for (const p of PICKS) {
      const byKey = new Map();
      for (const e of prior[p] ?? []) byKey.set([...e.comp].sort().join(), { comp: e.comp, n: e.n });
      for (const e of out[p]) {
        const k = [...e.comp].sort().join(), cur = byKey.get(k) ?? { comp: e.comp, n: 0 };
        cur.n += alpha * e.p; byKey.set(k, cur);
      }
      res[p] = [...byKey.values()].map(e => ({ comp: e.comp, n: +e.n.toFixed(3) })).sort((a, b) => b.n - a.n);
    }
    fs.writeFileSync(path.resolve(o.out), JSON.stringify(res, null, 1));
    console.log(`wrote ${o.out}`);
  }
}

// Run as a script, not imported (native.mjs). import.meta.url is the real path, argv[1] as typed, and
// Windows paths compare case-insensitively.
const self = p => fs.realpathSync(p).toLowerCase();
if (!isMainThread && workerData?.fitWorker) fitWorker(workerData);
else if (!isMainThread && workerData?.planWorker) planWorker(workerData);
else if (process.argv[1] && self(process.argv[1]) === self(fileURLToPath(import.meta.url))) {
  const cmd = process.argv[2], opts = args();
  if (!opts.lab) { console.error('usage: node tools/draftlab/model.mjs fit|plan|report|curve|gain|compare|cpp|teams --lab DIR ...'); process.exit(2); }
  useFeatures(readJson(path.join(opts.lab, 'config.json'), {}).features ?? LEGACY_FEATURES, oppsOf(readJson(path.join(opts.lab, 'config.json'), {})));
  useLock(readJson(path.join(opts.lab, 'config.json'), {}).team_lock ?? TEAM_LOCK);
  const commands = { fit: fitCommand, plan: planCommand, report: reportCommand, curve: curveCommand, gain: gainCommand,
    compare: compareCommand, ladder: ladderCommand, cpp: cppCommand, teams: teamsCommand, fitbench: fitbenchCommand, nash: nashCommand,
    oppcv: oppcvCommand, selcheck: selcheckCommand };
  if (!commands[cmd]) { console.error(`unknown command ${cmd}`); process.exit(2); }
  Promise.resolve(commands[cmd](opts)).catch(e => { console.error(e); process.exit(1); });
}
