// Emblem lab round-2 fit (tools/emblab/PLAN.md): one row per forced new-emblem decision (k < 12), the outcome
// whether that team won. The arm was drawn in the game from a known proposal q(a | state) (evehicle.py), so given
// the state at the decision (which q depends on, through the current logic's values v) the arm is as good as random.
//   node tools/emblab/dfit.mjs --labs r2 [--out replays/emblab/r2/dmodel.json] [--search] [--boot N] [--threads 90]
//
// logit P(team wins) = baseline + phi(chosen) - phi(base), with
//   baseline: side, the draft (champion intercepts, shared and per pick count), the state at the decision (score
//     difference and total, round, gold, allies alive, carried gems) per ordinal bucket, and intercepts per ordinal
//     and pick count and per type and bucket (reaching a decision goes with winning);
//   phi(arm), for type t, pick count p, ordinal k (bucket kc), family f, stat s, on a map with features z:
//     EA[t, k, arm] + ETF[t, kc, f] + ETS[t, kc, s] + EKF[k, f] + EKS[k, s] + EPF[p, t, f] + EPS[p, t, s]
//     + (EV[kc] + EVT[t, kc]) (v[arm] - v[base]) + EC[kc] [arm is the current logic's] + ECF[kc] [same family]
//     + MZ[f] . z + MZS[s] . z + ESD[f] score difference + ESR[f] round.
// Each worker parses its own byte range of decisions.jsonl and keeps its rows; L-BFGS runs here, the workers return
// their share of the loss and gradient. CV and bootstrap are over maps.
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { Worker, isMainThread, parentPort, workerData } from 'node:worker_threads';
import { spawn } from 'node:child_process';
import readline from 'node:readline';
import { FEATURES } from '../draftlab/model.mjs';
import { mapTable, FAMILIES, STATS, TYPES } from './fit.mjs';
import { NB, partitions, mapReport } from './mapdr.mjs';

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..');
const CHAMPS = ['ryth', 'vesper_vale', 'vendetta', 'cassi_and_issac', 'stellar', 'prism', 'marcella', 'willow', 'ren', 'varg', 'tavi', 'heart_of_ruin'];
// The map features: the draft lab's base ones (its first 30). Its squares and products (draftfeat, 92 in all) would
// put ~370 entries in every forced row.
const NC = CHAMPS.length, NT = TYPES.length, NF = FAMILIES.length, K = Math.min(FEATURES.length, 30), NA = 42, ORD = 12, NP = 3, FOLDS = 5;
// Opponent kinds beyond "self" (round 4: sparring bodies, a lab's config.json opponents), an intercept each per pick count.
const NOPP = 4;
const KC = k => k < 3 ? k : k < 6 ? 3 : 4, NKC = 5;
const ARMS = [];
for (let f = 0; f < NF; f++) if (FAMILIES[f] !== 'greed') for (let s = 0; s < 3; s++) ARMS.push(f * 3 + s);
const armName = a => `${FAMILIES[Math.floor(a / 3)]}-${STATS[a % 3]}`;
const NSTATE = 6;

// ---- columns -------------------------------------------------------------------------------------
const L = {}, GROUPS = [];
let P = 0;
function block(name, n, group) { L[name] = P; for (let i = 0; i < n; i++) GROUPS.push(group); P += n; }
block('SIDE', NP, 'base');
block('B', NC, 'base'); block('BP', NC * NP, 'basep');
block('S', NSTATE * NKC, 'base');
block('KI', ORD * NP, 'base'); block('TK', NT * NKC, 'basep');
block('OPP', NOPP * NP, 'base');
block('EA', NT * ORD * NA, 'ea');
block('ETF', NT * NKC * NF, 'et'); block('ETS', NT * NKC * 3, 'et');
block('EKF', ORD * NF, 'ek'); block('EKS', ORD * 3, 'ek');
block('EPF', NP * NT * NF, 'ep'); block('EPS', NP * NT * 3, 'ep');
block('EV', NKC, 'ev'); block('EVT', NT * NKC, 'evt');
block('EC', NKC, 'ev'); block('ECF', NKC, 'ev');
block('ESD', NF, 'es'); block('ESR', NF, 'es');
block('MZ', NF * K, 'mz'); block('MZS', 3 * K, 'mz');
const GNAMES = ['base', 'basep', 'ea', 'et', 'ek', 'ep', 'ev', 'evt', 'es', 'mz'];
const GROUP = Int8Array.from(GROUPS, g => GNAMES.indexOf(g));
const VARIANTS = {
  baseline: ['base', 'basep'],
  static: ['base', 'basep', 'ea', 'et', 'ek', 'ep'],
  state: ['base', 'basep', 'ea', 'et', 'ek', 'ep', 'ev', 'evt', 'es'],
  full: ['base', 'basep', 'ea', 'et', 'ek', 'ep', 'ev', 'evt', 'es', 'mz'],
  // Static and map terms only: what a bot could deploy with the map's features and no pass over every arm's value.
  map: ['base', 'basep', 'ea', 'et', 'ek', 'ep', 'mz'],
};
const DEFAULT_LAM = { base: 1, basep: 10, ea: 3000, et: 300, ek: 100, ep: 1000, ev: 1, evt: 30, es: 100, mz: 3000 };

const sigmoid = x => 1 / (1 + Math.exp(-x));
const softplus = x => x > 30 ? x : x < -30 ? Math.exp(x) : Math.log1p(Math.exp(x));
function hash(str) { let h = 2166136261; for (let i = 0; i < str.length; i++) h = Math.imul(h ^ str.charCodeAt(i), 16777619); return h >>> 0; }
function mix32(x) { x = Math.imul(x ^ (x >>> 16), 0x85ebca6b); x = Math.imul(x ^ (x >>> 13), 0xc2b2ae35); return (x ^ (x >>> 16)) >>> 0; }
// Poisson(1) from a uniform, for bootstrap weights per map.
function poisson1(u) { let k = 0, p = Math.exp(-1), c = p; while (u > c && k < 12) { k++; p /= k; c += p; } return k; }

// ---- rows ------------------------------------------------------------------------------------------
// State features at the decision, from the team's side.
function stateOf(d) {
  return [Math.max(-4, Math.min(4, (d.own_gems - d.enemy_gems) / 100)), (d.own_gems + d.enemy_gems) / 1000, d.round / 1000, Math.min(d.gold, 3000) / 1000,
    d.alive / 5, Math.min(d.carried, 300) / 100];
}

// phi(arm) for decision d (type t, pick index pi, ordinal k) on map z, added with sign s.
function addArm(add, d, pi, z, a, s, vb, st) {
  const t = d.type, k = d.k, kc = KC(k), f = Math.floor(a / 3), sa = a % 3;
  add(L.EA + (t * ORD + k) * NA + a, s);
  add(L.ETF + (t * NKC + kc) * NF + f, s); add(L.ETS + (t * NKC + kc) * 3 + sa, s);
  add(L.EKF + k * NF + f, s); add(L.EKS + k * 3 + sa, s);
  add(L.EPF + (pi * NT + t) * NF + f, s); add(L.EPS + (pi * NT + t) * 3 + sa, s);
  const gap = (d.v[a] ?? vb) - vb;
  add(L.EV + kc, s * gap); add(L.EVT + t * NKC + kc, s * gap);
  if (a === d.current) add(L.EC + kc, s);
  if (f === Math.floor(d.current / 3)) add(L.ECF + kc, s);
  add(L.ESD + f, s * st[0]); add(L.ESR + f, s * st[2]);
  for (let q = 0; q < K; q++) if (z[q]) { add(L.MZ + f * K + q, s * z[q]); add(L.MZS + sa * K + q, s * z[q]); }
}

// The row's entries (sorted, summed) for decision d of a game g (team side 0/1).
function rowOf(d, g, z) {
  const m = new Map(), add = (i, v) => { if (v) m.set(i, (m.get(i) ?? 0) + v); };
  const pi = g.pi, st = stateOf(d), kc = KC(d.k);
  if (d.team === 0) add(L.SIDE + pi, 1);
  for (const [cs, s] of [[g.draft[d.team], 1], [g.draft[1 - d.team], -1]])
    for (const c of cs) if (c >= 0) { add(L.B + c, s); add(L.BP + pi * NC + c, s); }
  for (let j = 0; j < NSTATE; j++) add(L.S + j * NKC + kc, st[j]);
  add(L.KI + d.k * NP + pi, 1); add(L.TK + d.type * NKC + kc, 1);
  if (g.opp) add(L.OPP + (g.opp - 1) * NP + pi, 1);
  if (d.chosen !== d.base) {
    const vb = d.v[d.base] ?? 0;
    addArm(add, d, pi, z, d.chosen, 1, vb, st);
    addArm(add, d, pi, z, d.base, -1, vb, st);
  }
  return [...m].filter(([, v]) => Math.abs(v) > 1e-12).sort((a, b) => a[0] - b[0]);
}

// ---- worker ------------------------------------------------------------------------------------------
class Grow {
  constructor(T, n = 1 << 16) { this.T = T; this.a = new T(n); this.n = 0; }
  push(x) { if (this.n === this.a.length) { const b = new this.T(this.a.length * 2); b.set(this.a); this.a = b; } this.a[this.n++] = x; }
  done() { return this.a.subarray(0, this.n); }
}

// Lines whose first byte is in [lo, hi): a range starting mid-line leaves that line to the one before.
function* rangeLines(file, lo, hi) {
  const fd = fs.openSync(file, 'r'), chunk = 1 << 24;
  try {
    let start = lo;
    if (lo > 0) {
      const b = Buffer.alloc(1);
      fs.readSync(fd, b, 0, 1, lo - 1);
      if (b[0] !== 10) {
        // Skip to after the next newline.
        const buf = Buffer.alloc(1 << 20);
        for (let pos = lo; ; pos += buf.length) {
          const n = fs.readSync(fd, buf, 0, buf.length, pos);
          if (n <= 0) return;
          const i = buf.subarray(0, n).indexOf(10);
          if (i >= 0) { start = pos + i + 1; break; }
        }
      }
    }
    let carry = Buffer.alloc(0), at = start; // at: file offset of carry[0]
    for (let pos = start; ;) {
      const buf = Buffer.alloc(chunk), n = fs.readSync(fd, buf, 0, chunk, pos);
      const data = n > 0 ? Buffer.concat([carry, buf.subarray(0, n)]) : carry;
      let i = 0;
      for (let j; (j = data.indexOf(10, i)) >= 0; i = j + 1) {
        if (at + i >= hi) return;
        if (j > i) yield data.toString('utf8', i, j);
      }
      if (n <= 0) { if (i < data.length && at + i < hi) yield data.toString('utf8', i); return; }
      carry = data.subarray(i); at += i; pos += n;
    }
  } finally { fs.closeSync(fd); }
}

// Round 4 on: a lab's decisions are a compressed file a batch (decisions/bNNN.jsonl.zst). Each is read by `parts`
// workers, every one streaming it through zstd and keeping the lines whose number is its own modulo `parts`, so
// nothing is decompressed to disk (~25 GB a million games).
async function* zstLines(file, part, parts) {
  const p = spawn('zstd', ['-dc', file], { stdio: ['ignore', 'pipe', 'inherit'] });
  let i = 0;
  for await (const l of readline.createInterface({ input: p.stdout, crlfDelay: Infinity })) if (i++ % parts === part && l) yield l;
}

const RAW = 17 + NA; // type, k, pi, map, base, chosen, current, q, forced, mode, state x 6, qb, v x 42
// Thresholds (logit) on the predicted gain for the held-out policy check; 0.04 is about a win point.
const TAUS = [0, 0.02, 0.04, 0.08, 0.12, Infinity]; // Infinity: always the base
const CHECK = 5 + TAUS.length;

// ---- doubly robust policy scores ---------------------------------------------------------------------
// The lab's proposal q(a | state) (evehicle.py), recomputed from the logged values: eps / n uniform over drawable
// arms plus (1 - eps) softmax((v[a] - v[base]) / tau + corr[a] / corr_tau); mode 1 uniform.
const EPS = 0.3, TAU = 0.04, CORR_TAU = 0.04;
function proposal(v, base, t, k, pi, mode, corr, out) {
  let n = 0, top = -Infinity;
  const vb = Number.isNaN(v[base]) ? 0 : v[base];
  for (let a = 0; a < NA; a++) {
    if (Number.isNaN(v[a])) { out[a] = -Infinity; continue; }
    n++;
    out[a] = (v[a] - vb) / TAU + corr[((pi * NT + t) * ORD + k) * NA + a] / CORR_TAU;
    if (out[a] > top) top = out[a];
  }
  let sum = 0;
  for (let a = 0; a < NA; a++) if (out[a] > -Infinity) sum += (out[a] = Math.exp(out[a] - top)); else out[a] = 0;
  const eps = mode === 1 ? 1 : EPS;
  for (let a = 0; a < NA; a++) if (!Number.isNaN(v[a])) out[a] = eps / n + (1 - eps) * out[a] / sum;
  return n;
}

// Policy classes: cell = (pick index, type, ordinal) [class 0] or that and the current logic's pick family [class 1].
// Candidates per cell: 0..41 a fixed arm (the current logic's choice where it is not drawable), 42 the current
// logic. Per (class, cell, candidate): sum and sum of squares of D = Gamma(candidate) - Gamma(base) and the row count,
// Gamma(a) = mu(a) + 1[chosen = a] (y - mu(chosen)) / P(chosen), P the logging probability of the chosen arm.
const NCAND = NA + 1, NCELL0 = NP * NT * ORD, NCELL1 = NCELL0 * NF;
// The model's own policy: its best drawable arm where the predicted gain over the base (win probability) clears a
// threshold, else the base; scored doubly robustly on the fold it was not fitted on, per opponent kind.
const MTAU = [0, 0.0025, 0.005, 0.01, 0.015, 0.02, 0.03];
function drStats(task, R, RW, zs, th) {
  const corr = task.corr, mz = task.mz;
  const s0 = new Float64Array(NCELL0 * NCAND * 3), s1 = new Float64Array(NCELL1 * NCAND * 3);
  // Class 0's sums again per opponent kind (0 self), to read a selection's gain against each.
  const sk = new Float64Array((NOPP + 1) * NCELL0 * NCAND * 3);
  // --mapdr: the same sums per (cell, partition bin) for mapdr.mjs, the map's bin of each partition in task.parts.
  const np = task.parts ? task.npart : 0, nslot = np * NB, sm = np ? new Float64Array(NCELL0 * nslot * NCAND * 3) : null, Dv = new Float64Array(NCAND);
  const q = new Float64Array(NA), mu = new Float64Array(NA), mp = new Float64Array((NOPP + 1) * MTAU.length * 3);
  let qerr = 0, qn = 0, rows = 0;
  for (let i = 0; i < R.n; i++) {
    if (R.fold[i] !== task.fold) continue;
    const r = RW.subarray(i * RAW, (i + 1) * RAW);
    const t = r[0], k = r[1], pi = r[2], map = r[3], base = r[4], chosen = r[5], current = r[6], qlog = r[7], forced = r[8], mode = r[9];
    const st = Array.from(r.subarray(10, 16)), qbase = r[16], v = r.subarray(17), kind = R.opp[i];
    const d = { type: t, k, current, v: Array.from(v, x => Number.isNaN(x) ? undefined : x) };
    const vb = d.v[base] ?? 0, zz = zs.subarray(map * K, map * K + K);
    const phi = a => { let e = 0; addArm((j, x) => { if (mz || j < L.MZ) e += th[j] * x; }, d, pi, zz, a, 1, vb, st); return e; };
    let e = 0;
    for (let x = R.ptr[i]; x < R.ptr[i + 1]; x++) { const j = R.idx[x]; if (mz || j < L.MZ) e += th[j] * R.val[x]; }
    const pb = phi(base), eb = e - (chosen === base ? 0 : phi(chosen) - pb);
    for (let a = 0; a < NA; a++) mu[a] = Number.isNaN(v[a]) && a !== base ? NaN : sigmoid(eb + (a === base ? 0 : phi(a) - pb));
    const pf = mode === 1 ? task.pUniform : task.pForce[k];
    let pc;
    if (Number.isFinite(qbase)) {
      // Round 4 on: the proposal's probability of the base is logged with every decision (qb), of the chosen arm with
      // a forced one (q), so nothing is recomputed (corr may change between batches).
      pc = chosen === base ? 1 - pf + pf * qbase : forced ? pf * qlog : 0;
    } else {
      const n = proposal(v, base, t, k, pi, mode, corr, q);
      const P = a => (a === base ? 1 - pf : 0) + (n ? pf * q[a] : a === base ? pf : 0);
      if (forced && chosen !== base && n && qlog > 0) { qerr += Math.abs(q[chosen] - qlog) / qlog; qn++; }
      pc = P(chosen);
    }
    if (!(pc > 0) || !Number.isFinite(eb) || Number.isNaN(mu[chosen]) || Number.isNaN(mu[base])) continue;
    rows++;
    const corrTerm = (R.y[i] - mu[chosen]) / pc;
    const G = a => mu[a] + (a === chosen ? corrTerm : 0);
    const gb = G(base);
    const fallback = Number.isNaN(v[current]) ? base : current;
    const c0 = (pi * NT + t) * ORD + k, c1 = c0 * NF + Math.floor(current / 3);
    {
      let best = base, bm = mu[base];
      for (let a = 0; a < NA; a++) if (a !== base && !Number.isNaN(v[a]) && FAMILIES[Math.floor(a / 3)] !== 'greed' && mu[a] > bm) bm = mu[a], best = a;
      const D = G(best) - gb, lead = bm - mu[base];
      for (let j = 0; j < MTAU.length; j++) { const o = (kind * MTAU.length + j) * 3; mp[o + 2]++; if (best !== base && lead > MTAU[j]) { mp[o] += D; mp[o + 1] += D * D; } }
    }
    for (let c = 0; c < NCAND; c++) {
      const arm = c === NA ? fallback : Number.isNaN(v[c]) ? fallback : c;
      Dv[c] = NaN;
      if (c < NA && FAMILIES[Math.floor(c / 3)] === 'greed') continue;
      const D = Dv[c] = G(arm) - gb;
      for (const [S, cell] of [[s0, c0], [s1, c1], [sk, kind * NCELL0 + c0]]) { const o = (cell * NCAND + c) * 3; S[o] += D; S[o + 1] += D * D; S[o + 2]++; }
    }
    for (let p = 0; p < np; p++) {
      const o0 = (c0 * nslot + p * NB + task.parts[map * np + p]) * NCAND * 3;
      for (let c = 0; c < NCAND; c++) { const D = Dv[c]; if (Number.isNaN(D)) continue; const o = o0 + c * 3; sm[o] += D; sm[o + 1] += D * D; sm[o + 2]++; }
    }
  }
  return { s0, s1, sk, mp, sm, qerr: qn ? qerr / qn : 0, qn, rows };
}

async function workerMain() {
  const W = workerData, G = W.games, zs = W.z;
  const ptr = new Grow(Int32Array), idx = new Grow(Int32Array), val = new Grow(Float32Array);
  const y = new Grow(Uint8Array), fold = new Grow(Uint8Array), mapi = new Grow(Int32Array), raw = new Grow(Float32Array, 1 << 20), frc = new Grow(Uint8Array), oppk = new Grow(Uint8Array);
  ptr.push(0);
  const ID = /^b(\d+)-g(\d+)$/;
  for await (const l of W.zst ? zstLines(W.file, W.part, W.parts) : rangeLines(W.file, W.lo, W.hi)) {
    const d = JSON.parse(l);
    // A truncated EMB2 line would shift every later row's raw fields.
    if (d.k >= ORD || !(d.forced || W.unforced) || d.v?.length !== NA) continue;
    const m = ID.exec(d.id), off = G.offsets[W.lab][+m[1]];
    if (off === undefined) continue;
    const gi = off + +m[2];
    if (!G.ok[gi]) continue;
    const g = { pi: G.pi[gi], opp: G.opp[gi], draft: [0, 1].map(s => Array.from(G.draft.subarray(gi * 10 + s * 5, gi * 10 + s * 5 + 5))) }, map = G.map[gi];
    const z = zs.subarray(map * K, map * K + K);
    for (const [i, v] of rowOf(d, g, z)) { idx.push(i); val.push(v); }
    ptr.push(idx.n);
    y.push(G.winner[gi] === d.team ? 1 : 0); fold.push(G.fold[gi]); mapi.push(map); frc.push(d.forced ? 1 : 0); oppk.push(G.bySrc ? G.src[gi * 2 + d.team] : g.opp);
    for (const x of [d.type, d.k, g.pi, map, d.base, d.chosen, d.current, d.q, d.forced, d.mode, ...stateOf(d), d.qb ?? NaN, ...d.v.map(x => x ?? NaN)]) raw.push(x);
  }
  const R = { ptr: ptr.done(), idx: idx.done(), val: val.done(), y: y.done(), fold: fold.done(), map: mapi.done(), forced: frc.done(), opp: oppk.done(), n: y.n };
  const th = new Float64Array(W.thBuf), grad = new Float64Array(W.gradBuf);
  parentPort.postMessage({ ready: R.n, nnz: R.idx.length });
  parentPort.on('message', task => {
    if (task.cmd === 'eval') {
      // Loss and gradient (into this worker's slot) over training rows: fold !== task.fold, bootstrap weights by map.
      grad.fill(0);
      let f = 0;
      const mzLive = task.mz;
      for (let i = 0; i < R.n; i++) {
        if (R.fold[i] === task.fold || !(R.forced[i] || task.fitall)) continue;
        const w = task.boot >= 0 ? poisson1(mix32(R.map[i] * 2654435761 ^ (task.boot + 1) * 40503) / 4294967296) : 1;
        if (!w) continue;
        const a = R.ptr[i], b = R.ptr[i + 1];
        let e = 0;
        for (let k = a; k < b; k++) { const j = R.idx[k]; if (mzLive || j < L.MZ) e += th[j] * R.val[k]; }
        f += w * (softplus(e) - R.y[i] * e);
        const gg = w * (sigmoid(e) - R.y[i]);
        for (let k = a; k < b; k++) { const j = R.idx[k]; if (mzLive || j < L.MZ) grad[j] += gg * R.val[k]; }
      }
      parentPort.postMessage({ f });
    } else if (task.cmd === 'score') {
      let loss = 0, n = 0;
      for (let i = 0; i < R.n; i++) {
        if (R.fold[i] !== task.fold || !(R.forced[i] || task.fitall)) continue;
        let e = 0;
        for (let k = R.ptr[i]; k < R.ptr[i + 1]; k++) { const j = R.idx[k]; if (task.mz || j < L.MZ) e += th[j] * R.val[k]; }
        const p = Math.min(1 - 1e-9, Math.max(1e-9, sigmoid(e)));
        loss -= R.y[i] ? Math.log(p) : Math.log(1 - p); n++;
      }
      parentPort.postMessage({ loss, n });
    } else if (task.cmd === 'policy') {
      // Per (pick index, type, ordinal): rows, the mean predicted gain of the best drawable arm over the base, how
      // often each arm is best, and the single-decision IPW estimate: mean of y 1[chosen = best] / q among forced
      // rows against the rows' mean y.
      const cells = new Map(), z = zs, RW = raw.done(), check = new Grow(Float32Array, 1 << 20);
      let badRows = 0;
      for (let i = 0; i < R.n; i++) {
        if (!R.forced[i] || (task.fold >= 0 && R.fold[i] !== task.fold)) continue;
        const r = Array.from(RW.subarray(i * RAW, (i + 1) * RAW));
        const [t, k, pi, map, base, chosen, current, q, forced, mode] = r, st = r.slice(10, 16), v = r.slice(17);
        const d = { type: t, k, current, v: v.map(x => Number.isNaN(x) ? undefined : x) };
        const vb = d.v[base] ?? 0, zz = z.subarray(map * K, map * K + K);
        const phi = a => { let e = 0; addArm((j, x) => { if (task.mz || j < L.MZ) e += th[j] * x; }, d, pi, zz, a, 1, vb, st); return e; };
        const pb = phi(base);
        let best = base, gain = 0;
        for (const a of ARMS) if (d.v[a] !== undefined && a !== base) { const g = phi(a) - pb; if (g > gain) gain = g, best = a; }
        const key = `${pi},${t},${k}`;
        let c = cells.get(key);
        if (!c) cells.set(key, c = { n: 0, gain: 0, best: {}, ipw: 0, ipwn: 0, y: 0, change: 0 });
        c.n++; c.gain += gain; c.best[best] = (c.best[best] ?? 0) + 1; c.y += R.y[i]; c.change += best !== base;
        if (forced && chosen === best) c.ipw += R.y[i] / q;
        if (forced) c.ipwn += 1;
        // Held-out checks: the row's logit, the drawn arm's predicted gain over the base, and per threshold tau the
        // importance weight of following the model there (best arm if its gain clears tau, else the base).
        let e = 0;
        for (let x = R.ptr[i]; x < R.ptr[i + 1]; x++) { const j = R.idx[x]; if (task.mz || j < L.MZ) e += th[j] * R.val[x]; }
        const gc = chosen === base ? 0 : phi(chosen) - pb;
        if (!(q > 0 && q <= 1 && Number.isFinite(e) && Number.isFinite(gain))) { badRows++; continue; }
        for (const x of [k, e, gc, R.y[i], gain]) check.push(x);
        for (const tau of TAUS) check.push((gain > tau ? best : base) === chosen ? 1 / q : 0);
      }
      const C = check.done();
      parentPort.postMessage({ cells: [...cells], check: C, bad: badRows }, [C.buffer]);
    } else if (task.cmd === 'dr') {
      const r = drStats(task, R, raw.done(), zs, th);
      parentPort.postMessage(r, r.sm ? [r.sm.buffer] : []);
    }
  });
}

// ---- main ------------------------------------------------------------------------------------------
function args() {
  const a = process.argv.slice(2), o = {};
  for (let i = 0; i < a.length; i++) { const k = a[i].slice(2), v = a[i + 1] && !a[i + 1].startsWith('--') ? a[++i] : true; o[k] = v; }
  return o;
}
function* jsonl(f) {
  const fd = fs.openSync(f, 'r'), buf = Buffer.alloc(1 << 24);
  let rest = '';
  try {
    for (let n; (n = fs.readSync(fd, buf, 0, buf.length, null)) > 0;) {
      const lines = (rest + buf.toString('utf8', 0, n)).split('\n');
      rest = lines.pop();
      for (const l of lines) if (l) yield JSON.parse(l);
    }
    // A lab still playing may be half-way through appending its last line.
    if (rest) { let last; try { last = JSON.parse(rest); } catch { last = null; } if (last) yield last; }
  } finally { fs.closeSync(fd); }
}

class Cluster {
  constructor(workers) { this.ws = workers; }
  static async start(files, games, z, threads, unforced) {
    const thBuf = new SharedArrayBuffer(P * 8), grads = [];
    const ranges = [];
    const plain = files.filter(f => !f[2]), zst = files.filter(f => f[2]);
    for (const [lab, file] of plain) {
      const size = fs.statSync(file).size, per = Math.ceil(threads / files.length);
      for (let i = 0; i < per; i++) ranges.push({ file, lab, lo: Math.floor(size * i / per), hi: Math.floor(size * (i + 1) / per) });
    }
    const parts = Math.max(1, Math.round(threads / Math.max(1, zst.length)));
    for (const [lab, file] of zst) for (let part = 0; part < parts; part++) ranges.push({ file, lab, zst: true, part, parts });
    const ws = await Promise.all(ranges.map(r => new Promise((resolve, reject) => {
      const gradBuf = new SharedArrayBuffer(P * 8);
      const w = new Worker(fileURLToPath(import.meta.url), { workerData: { ...r, games, z, thBuf, gradBuf, unforced } });
      w.once('message', m => resolve({ w, grad: new Float64Array(gradBuf), rows: m.ready, nnz: m.nnz }));
      w.on('error', reject);
    })));
    const c = new Cluster(ws);
    c.th = new Float64Array(thBuf);
    return c;
  }
  ask(task) { return Promise.all(this.ws.map(x => new Promise(res => { x.w.once('message', res); x.w.postMessage(task); }))); }
  close() { for (const x of this.ws) x.w.terminate(); }
  // Penalised loss and gradient at th (copied into the shared buffer).
  async objective(th, lam, task, g) {
    this.th.set(th);
    const parts = await this.ask({ cmd: 'eval', ...task });
    let f = parts.reduce((a, p) => a + p.f, 0);
    g.fill(0);
    for (const x of this.ws) for (let j = 0; j < P; j++) g[j] += x.grad[j];
    for (let j = 0; j < P; j++) if (lam[j]) { f += 0.5 * lam[j] * th[j] * th[j]; g[j] += lam[j] * th[j]; }
    return f;
  }
  async fit(lamv, task, init, iters = 200, m = 10) {
    const n = P, live = Uint8Array.from(lamv, v => Number.isFinite(v) ? 1 : 0), lam = Float64Array.from(lamv, v => Number.isFinite(v) ? v : 0);
    const th = Float64Array.from(init ?? new Float64Array(n)), g = new Float64Array(n), gn = new Float64Array(n), tn = new Float64Array(n);
    for (let j = 0; j < n; j++) if (!live[j]) th[j] = 0;
    const S = [], Y = [], R = [];
    let f = await this.objective(th, lam, task, g);
    for (let j = 0; j < n; j++) if (!live[j]) g[j] = 0;
    for (let it = 0; it < iters; it++) {
      const q = Float64Array.from(g), a = [];
      for (let i = S.length - 1; i >= 0; i--) { let s = 0; for (let j = 0; j < n; j++) s += S[i][j] * q[j]; a[i] = R[i] * s; for (let j = 0; j < n; j++) q[j] -= a[i] * Y[i][j]; }
      if (S.length) { const i = S.length - 1; let sy = 0, yy = 0; for (let j = 0; j < n; j++) { sy += S[i][j] * Y[i][j]; yy += Y[i][j] * Y[i][j]; } for (let j = 0; j < n; j++) q[j] *= sy / yy; }
      else { let gg = 0; for (let j = 0; j < n; j++) gg += g[j] * g[j]; const sc = 1 / Math.max(1, Math.sqrt(gg)); for (let j = 0; j < n; j++) q[j] *= sc; }
      for (let i = 0; i < S.length; i++) { let s = 0; for (let j = 0; j < n; j++) s += Y[i][j] * q[j]; const b = R[i] * s; for (let j = 0; j < n; j++) q[j] += S[i][j] * (a[i] - b); }
      let gd = 0;
      for (let j = 0; j < n; j++) { q[j] = -q[j] * live[j]; gd += q[j] * g[j]; }
      if (gd >= 0) { gd = 0; for (let j = 0; j < n; j++) { q[j] = -g[j]; gd += q[j] * g[j]; } S.length = Y.length = R.length = 0; }
      let step = 1, fn;
      for (let ls = 0; ls < 20; ls++) {
        for (let j = 0; j < n; j++) tn[j] = th[j] + step * q[j];
        fn = await this.objective(tn, lam, task, gn);
        if (fn <= f + 1e-4 * step * gd) break;
        step *= 0.5;
      }
      for (let j = 0; j < n; j++) if (!live[j]) gn[j] = 0;
      const s = new Float64Array(n), yv = new Float64Array(n);
      let sy = 0;
      for (let j = 0; j < n; j++) { s[j] = tn[j] - th[j]; yv[j] = gn[j] - g[j]; sy += s[j] * yv[j]; }
      const done = Math.abs(f - fn) < 1e-9 * Math.max(1, Math.abs(f));
      th.set(tn); g.set(gn); f = fn;
      if (sy > 1e-12) { S.push(s); Y.push(yv); R.push(1 / sy); if (S.length > m) { S.shift(); Y.shift(); R.shift(); } }
      if (done) break;
    }
    return th;
  }
  async cv(variant, lam) {
    const lamv = lamVector(variant, lam), mz = VARIANTS[variant].includes('mz');
    let loss = 0, n = 0;
    for (let f = 0; f < FOLDS; f++) {
      const th = await this.fit(lamv, { fold: f, boot: -1, mz, fitall: this.fitall });
      this.th.set(th);
      for (const p of await this.ask({ cmd: 'score', fold: f, mz, fitall: this.fitall })) { loss += p.loss; n += p.n; }
    }
    return loss / n;
  }
}
function lamVector(variant, lam) {
  const on = new Set(VARIANTS[variant]);
  return Float64Array.from(GROUP, g => on.has(GNAMES[g]) ? lam[GNAMES[g]] : Infinity);
}

async function main() {
  const o = args();
  const labs = String(o.labs ?? 'r2').split(',').map(l => path.join(ROOT, 'replays', 'emblab', l));
  const out = path.resolve(o.out ?? path.join(labs[0], 'dmodel.json'));
  const t0 = Date.now(), secs = () => ((Date.now() - t0) / 1000).toFixed(0);
  const table = mapTable(labs[0]), mapIndex = new Map(table.maps.map((m, i) => [m.key, i]));
  const z = new Float64Array(new SharedArrayBuffer(table.maps.length * K * 8));
  table.maps.forEach((m, i) => z.set(m.z.subarray(0, K), i * K));
  // Games in shared arrays, indexed by offsets[lab][batch] + game number.
  const list = [], offsets = labs.map(() => ({}));
  labs.forEach((lab, li) => {
    for (const g of jsonl(path.join(lab, 'games.jsonl'))) {
      const [, b, n] = /^b(\d+)-g(\d+)$/.exec(g.id).map(Number);
      list.push([li, b, n, g]);
    }
  });
  const size = {};
  for (const [li, b, n] of list) size[`${li},${b}`] = Math.max(size[`${li},${b}`] ?? 0, n + 1);
  let total = 0;
  for (const key of Object.keys(size).sort((a, b) => a.localeCompare(b, undefined, { numeric: true }))) {
    const [li, b] = key.split(',').map(Number);
    offsets[li][b] = total; total += size[key];
  }
  const sab = (T, n) => new T(new SharedArrayBuffer(n * T.BYTES_PER_ELEMENT));
  const games = { offsets, ok: sab(Uint8Array, total), winner: sab(Int8Array, total), pi: sab(Uint8Array, total), map: sab(Int32Array, total),
    fold: sab(Uint8Array, total), opp: sab(Uint8Array, total), src: sab(Uint8Array, total * 2), draft: sab(Int8Array, total * 10).fill(-1) };
  // --kinds src: the doubly robust sums per draft source of the deciding team (explore, ladder, model: what the bot
  // itself drafts) in place of per opponent kind. Only "model" teams are the ones a deployed table meets.
  const SRCS = ['explore', 'ladder', 'model'];
  games.bySrc = o.kinds === 'src';
  const cfg0 = JSON.parse(fs.readFileSync(path.join(labs[0], 'config.json'), 'utf8'));
  const KINDS = Object.keys(cfg0.opponents ?? { self: 1 }).filter(k => k !== 'self');
  if (KINDS.length > NOPP) throw new Error(`more than ${NOPP} opponent kinds`);
  let usable = 0;
  for (const [li, b, n, g] of list) {
    const pi = [3, 4, 5].indexOf(g.picks), gi = offsets[li][b] + n;
    if (g.error || g.winner === undefined || g.draft_ok === false || !mapIndex.has(g.key) || pi < 0) continue;
    games.ok[gi] = 1; games.winner[gi] = g.winner; games.pi[gi] = pi; games.map[gi] = mapIndex.get(g.key); games.fold[gi] = hash(g.key) % FOLDS;
    games.opp[gi] = g.opp && g.opp !== 'self' ? KINDS.indexOf(g.opp) + 1 : 0;
    ['A', 'B'].forEach((S, t) => { games.src[gi * 2 + t] = Math.max(0, SRCS.indexOf(g[`src${S}`])); });
    [g.A, g.B].forEach((T, s) => T.forEach((c, i) => { games.draft[gi * 10 + s * 5 + i] = CHAMPS.indexOf(c); }));
    usable++;
  }
  list.length = 0;
  games.length = usable;
  console.log(`${games.length} games; ${P} columns (${secs()} s)`);
  const threads = +(o.threads ?? Math.max(1, os.cpus().length - 6));
  // Per lab: decisions.jsonl when it is there (rounds 1-3, or decompressed by hand), else its compressed batch files.
  const files = labs.flatMap((l, i) => fs.existsSync(path.join(l, 'decisions.jsonl')) ? [[i, path.join(l, 'decisions.jsonl'), false]]
    : fs.existsSync(path.join(l, 'decisions')) ? fs.readdirSync(path.join(l, 'decisions')).filter(f => f.endsWith('.jsonl.zst')).sort().map(f => [i, path.join(l, 'decisions', f), true]) : []);
  if (o.mapdr) o.dr = true;
  const C = await Cluster.start(files, games, z, threads, !!(o.unforced || o.dr));
  const rows = C.ws.reduce((a, x) => a + x.rows, 0), nnz = C.ws.reduce((a, x) => a + x.nnz, 0);
  console.log(`${rows} decision rows, ${nnz} entries, ${C.ws.length} workers (${secs()} s)`);
  const prev = fs.existsSync(out) ? JSON.parse(fs.readFileSync(out, 'utf8')) : null;
  let lam = { ...DEFAULT_LAM, ...(prev?.lam ?? {}) };
  const cv = {};
  if (o.search) {
    // --rounds 0 keeps lam and scores only the variants (a finished search's lam, carried in the out file).
    const rounds = +(o.rounds ?? 2);
    let best = rounds ? await C.cv('state', lam) : NaN;
    if (rounds) console.log(`start ${best.toFixed(5)} (${secs()} s)`);
    for (let round = 0; round < rounds; round++)
      for (const g of ['ea', 'et', 'ek', 'ep', 'evt', 'es', 'basep']) {
        for (const mult of [0.25, 4]) {
          const trial = { ...lam, [g]: lam[g] * mult }, l = await C.cv('state', trial);
          console.log(`  ${g} x${mult}: ${l.toFixed(5)} (${secs()} s)`);
          if (l < best - 1e-6) { best = l; lam = trial; }
        }
      }
    for (const mult of [1, 4]) {
      const trial = { ...lam, mz: lam.mz * mult }, l = await C.cv('full', trial);
      console.log(`  full, mz x${mult}: ${l.toFixed(5)}`);
      if (!cv.full || l < cv.full) { cv.full = l; if (mult > 1) lam = trial; }
    }
    for (const v of ['baseline', 'static', 'state']) cv[v] = await C.cv(v, lam);
    console.log('cv log loss by variant:', Object.entries(cv).map(([k, v]) => `${k} ${v.toFixed(5)}`).join(', '));
  }
  const scored = Object.keys(cv).length ? cv : prev?.cv ?? {};
  const variant = o.variant ?? (Object.keys(scored).length ? Object.entries(scored).sort((a, b) => a[1] - b[1])[0][0] : 'state');
  const mz = VARIANTS[variant].includes('mz'), lamv = lamVector(variant, lam);
  // --fitall (a sparse lab, where few rows are forced): unforced rows train the baseline terms too.
  C.fitall = !!o.fitall;
  const th = await C.fit(lamv, { fold: -1, boot: -1, mz, fitall: C.fitall });
  // Held-out policy check: per fold, the model fitted without it picks the arms on its rows.
  const cells = new Map(), checks = [], dr = [];
  const cfg = JSON.parse(fs.readFileSync(path.join(labs[0], 'config.json'), 'utf8'));
  // --mapsplits a,b --mapcuts 2,4,6 --mapkmeans 2,3: the map-keyed search's splits (mapdr.mjs partitions).
  const csv = (v, f = x => x) => typeof v === "string" ? v.split(",").map(f) : undefined;
  const mapParts = o.mapdr ? partitions(table, { splits: csv(o.mapsplits), cuts: csv(o.mapcuts, Number), kmeans: o.mapsplits ? csv(o.mapkmeans, Number) ?? [] : csv(o.mapkmeans, Number), dims: K }) : null, mapFolds = [];
  const drTask = o.dr ? { cmd: 'dr', mz, corr: corrTable(cfg.corr_model), pForce: cfg.p_force, pUniform: cfg.p_uniform,
    parts: mapParts?.bins, npart: mapParts?.npart } : null;
  for (let f = 0; f < FOLDS; f++) {
    C.th.set(await C.fit(lamv, { fold: f, boot: -1, mz, fitall: C.fitall }, th));
    if (drTask) {
      const parts = await C.ask({ ...drTask, fold: f });
      if (mapParts) {
        // Summed here: 90 workers' copies of every fold would not fit in memory.
        const S = new Float64Array(parts[0].sm.length);
        for (const p of parts) { for (let i = 0; i < S.length; i++) S[i] += p.sm[i]; p.sm = null; }
        mapFolds.push(S);
      }
      dr.push(parts);
    }
    const parts = await C.ask({ cmd: 'policy', fold: f, mz });
    for (const p of parts) checks.push(p.check);
    const bad = parts.reduce((a, p) => a + p.bad, 0);
    if (bad) console.log(`fold ${f}: ${bad} rows with a bad q, logit or gain left out of the checks`);
    for (const p of parts)
      for (const [key, c] of p.cells) {
        const t = cells.get(key) ?? { n: 0, gain: 0, best: {}, ipw: 0, ipwn: 0, y: 0, change: 0 };
        t.n += c.n; t.gain += c.gain; t.ipw += c.ipw; t.ipwn += c.ipwn; t.y += c.y; t.change += c.change;
        for (const [a, x] of Object.entries(c.best)) t.best[a] = (t.best[a] ?? 0) + x;
        cells.set(key, t);
      }
  }
  const boots = [];
  for (let b = 0; b < +(o.boot ?? 0); b++) boots.push(Array.from(await C.fit(lamv, { fold: -1, boot: b, mz, fitall: C.fitall }, th, 60)));
  C.close();
  fs.writeFileSync(out, JSON.stringify({ created: new Date().toISOString(), labs: labs.map(l => path.basename(l)), rows, variant, lam, cv: scored, L, P,
    features: FEATURES.slice(0, K), mean: table.mean.slice(0, K), sd: table.sd.slice(0, K), kinds: KINDS, theta: Array.from(th), boots }) + '\n');
  const drRows = dr.flat().reduce((a, p) => a + p.rows, 0);
  if (mapParts) {
    // The map-keyed sums, for selection rules tried offline: per fold, (sum D, sum D^2, n) per (cell, partition, bin, candidate).
    const fd = fs.openSync(out.replace(/\.json$/, '.mapsums.bin'), 'w');
    for (const S of mapFolds) for (let at = 0; at < S.byteLength; at += 1 << 28) fs.writeSync(fd, Buffer.from(S.buffer, S.byteOffset + at, Math.min(1 << 28, S.byteLength - at)));
    fs.closeSync(fd);
    fs.writeFileSync(out.replace(/\.json$/, '.mapsums.json'), JSON.stringify({ folds: mapFolds.length, NP, NT, ORD, NCAND, NA, NB, rows: drRows,
      parts: mapParts.list.map(p => ({ name: p.name, kind: p.kind, feature: p.feature, cuts: p.cuts, nb: p.nb })),
      layout: 'per fold: Float64 [NP*NT*ORD][parts][NB][NCAND][3]; bin = number of cuts (standardised feature) at or below the value' }) + '\n');
  }
  const checkLines = [...heldOut(checks), ...(drTask ? drReport(dr, out, games.bySrc ? SRCS : ['self', ...KINDS]) : []),
    ...(mapParts ? mapReport(mapFolds, drRows, mapParts, { NP, NT, ORD, NKC, KC, NCAND, NA, TYPES, armName }, out) : [])];
  console.log(checkLines.join('\n'));
  report(cells, out, variant, lam, scored, rows, checkLines);
  console.log(`wrote ${path.relative(ROOT, out)} (${secs()} s)`);
}

// Calibration: per ordinal bucket, the slope b of y ~ sigmoid(e - g + b g) on held-out rows (1: the predicted arm
// gains are right; below 1: too optimistic). Policy check: per tau, the self-normalised IPW win rate of following the
// model where its predicted gain clears tau, minus that of the base (tau = infinity), in win points, with a
// standard error that ignores rows sharing a game (so somewhat small).
function heldOut(checks) {
  const lines = ['Held-out checks (models fitted without each fold, scored on it): calibration slope b of the predicted arm',
    'gains (1: right, below 1: too optimistic); per tau (logit; 0.04 ~ a win point), following the model where its gain',
    'clears tau against the base, by self-normalised IPW, win points +- 1 se (rows of one game share it: se a bit small).'];
  const base = TAUS.length - 1;
  for (const [lo, hi] of [[0, 0], [1, 1], [2, 2], [3, 5], [6, 11], [0, 11]]) {
    const rows = [];
    for (const C of checks) for (let i = 0; i < C.length; i += CHECK) if (C[i] >= lo && C[i] <= hi) rows.push(i, C);
    let b = 1;
    for (let it = 0; it < 8; it++) {
      let g1 = 0, h = 0;
      for (let r = 0; r < rows.length; r += 2) {
        const i = rows[r], C = rows[r + 1], g = C[i + 2];
        if (!g) continue;
        const p = sigmoid(C[i + 1] - g + b * g);
        g1 += (p - C[i + 3]) * g; h += p * (1 - p) * g * g;
      }
      if (h > 0) b -= g1 / h;
    }
    const est = TAUS.map((_, j) => {
      let sw = 0, swy = 0;
      for (let r = 0; r < rows.length; r += 2) { const i = rows[r], C = rows[r + 1], w = C[i + 5 + j]; sw += w; swy += w * C[i + 3]; }
      const mu = swy / Math.max(1e-9, sw);
      let v = 0;
      for (let r = 0; r < rows.length; r += 2) { const i = rows[r], C = rows[r + 1], w = C[i + 5 + j]; v += w * w * (C[i + 3] - mu) ** 2; }
      return { mu, var: v / Math.max(1e-9, sw * sw) };
    });
    const diffs = TAUS.slice(0, base).map((t, j) => `tau ${t} ${(100 * (est[j].mu - est[base].mu)).toFixed(1)} +- ${(100 * Math.sqrt(est[j].var + est[base].var)).toFixed(1)}`);
    lines.push(`  k${lo}${hi > lo ? '-' + hi : ''} (${rows.length / 2} rows): b ${b.toFixed(2)}; base ${(100 * est[base].mu).toFixed(1)}%; ` + diffs.join(', '));
  }
  return lines;
}

// Round 1's static arm gains (the proposal's corr), as evehicle.py corr_values.
function corrTable(modelPath) {
  const out = new Float64Array(NP * NT * ORD * NA);
  if (!modelPath) return out;
  const m = JSON.parse(fs.readFileSync(path.join(ROOT, modelPath), 'utf8')), th = m.theta;
  if (m.L.EA !== undefined) return out; // a per-decision model (round 4 on): its rows log qb, nothing is recomputed
  const at = (name, i, pi) => th[m.L[name] + i] + th[m.L[name + 'P'] + pi * m.N[name] + i];
  for (let pi = 0; pi < NP; pi++) for (let t = 0; t < NT; t++) for (let k = 0; k < ORD; k++) for (const a of ARMS) {
    const kb = Math.min(k, 3), f = Math.floor(a / 3), sa = a % 3;
    out[((pi * NT + t) * ORD + k) * NA + a] = at('ET', t * NF + f, pi) + at('ST', t * 3 + sa, pi) + at('EK', kb * NF + f, pi) + at('SK', kb * 3 + sa, pi);
  }
  return out;
}

// Cross-fitted policy selection: for each fold, per cell the candidate with the best mean D on the other folds
// (kept only if it clears z standard errors there, else the base), scored on the fold. Summed over folds: the
// gain per decision of a policy chosen without its scoring data. Writes <out>.policy2.json: the selection on all
// folds per class and z.
function drReport(dr, out, kindNames = ['self']) {
  const kinds = kindNames.slice(1), first = kindNames[0];
  const lines = [], folds = dr.map(parts => {
    const s0 = new Float64Array(NCELL0 * NCAND * 3), s1 = new Float64Array(NCELL1 * NCAND * 3), sk = new Float64Array((NOPP + 1) * NCELL0 * NCAND * 3);
    let qerr = 0, qn = 0, rows = 0;
    for (const p of parts) { for (let i = 0; i < s0.length; i++) s0[i] += p.s0[i]; for (let i = 0; i < s1.length; i++) s1[i] += p.s1[i]; for (let i = 0; i < sk.length; i++) sk[i] += p.sk[i]; qerr += p.qerr * p.qn; qn += p.qn; rows += p.rows; }
    const mp = new Float64Array((NOPP + 1) * MTAU.length * 3);
    for (const p of parts) for (let i = 0; i < mp.length; i++) mp[i] += p.mp[i];
    return { s: [s0, s1], sk, mp, qerr: qn ? qerr / qn : 0, rows };
  });
  const rows = folds.reduce((a, f) => a + f.rows, 0);
  // The sums themselves, for selection rules tried offline (tools/emblab/select.py): per fold, class 0's (sum D,
  // sum D^2, n) per (cell, candidate), then the same per opponent kind.
  {
    const fd = fs.openSync(out.replace(/\.json$/, '.drsums.bin'), 'w');
    for (const f of folds) { fs.writeSync(fd, Buffer.from(f.s[0].buffer, f.s[0].byteOffset, f.s[0].byteLength)); fs.writeSync(fd, Buffer.from(f.sk.buffer, f.sk.byteOffset, f.sk.byteLength)); }
    fs.closeSync(fd);
    fs.writeFileSync(out.replace(/\.json$/, '.drsums.json'), JSON.stringify({ folds: folds.length, NP, NT, ORD, NCAND, NA, kinds: [first, ...kinds], NOPP, rows: folds.map(f => f.rows),
      layout: 'per fold: Float64 s0[NP*NT*ORD][NCAND][3], then sk[NOPP+1][NP*NT*ORD][NCAND][3]; cell = (pi*NT + t)*ORD + k; candidate NA = the current logic', types: TYPES, families: FAMILIES }) + '\n');
  }
  lines.push('', `Doubly robust policy selection (${rows} decisions, forced and not; recomputed proposal against the logged q: mean relative error ${(100 * folds[0].qerr).toFixed(2)}%; rows with a logged qb recompute nothing).`,
    '');
  {
    // (sum D, sum D^2, rows) per kind and threshold; D is 0 where the policy keeps the base.
    const mp = new Float64Array(folds[0].mp.length);
    for (const f of folds) for (let i = 0; i < mp.length; i++) mp[i] += f.mp[i];
    lines.push("The model's own policy (its best arm where the predicted gain clears t win points, else the base), cross-fitted, points per decision +- se:");
    MTAU.forEach((t, j) => {
      const cell = q => { const o = (q * MTAU.length + j) * 3, n = mp[o + 2]; return n ? `${(100 * mp[o] / n).toFixed(3)} +- ${(100 * Math.sqrt(Math.max(0, mp[o + 1] - mp[o] * mp[o] / n)) / n).toFixed(3)}` : '-'; };
      let S = 0, S2 = 0, N = 0;
      for (let q = 0; q <= NOPP; q++) { const o = (q * MTAU.length + j) * 3; S += mp[o]; S2 += mp[o + 1]; N += mp[o + 2]; }
      lines.push(`  t ${(100 * t).toFixed(2)}: ${(100 * S / N).toFixed(3)} +- ${(100 * Math.sqrt(Math.max(0, S2 - S * S / N)) / N).toFixed(3)}` + (kinds.length ? '; against ' + [first, ...kinds].map((name, q) => `${name} ${cell(q)}`).join(', ') : ''));
    });
  }
  lines.push('Per class and z: cross-fitted gain per decision in win points +- se, and the share of decisions whose cell leaves the base.');
  const selection = {};
  for (const cls of [0, 1]) for (const zc of [0, 1, 1.5, 2, 2.5, 3]) {
    const ncell = cls ? NCELL1 : NCELL0;
    const pick = S => {
      const sel = new Int16Array(ncell).fill(-1);
      for (let c = 0; c < ncell; c++) {
        let best = -1, bm = 0;
        for (let k = 0; k < NCAND; k++) {
          const o = (c * NCAND + k) * 3, n = S[o + 2];
          if (n < 30) continue;
          const m = S[o] / n, se = Math.sqrt(Math.max(0, S[o + 1] / n - m * m) / n);
          if (m - zc * se > bm) bm = m - zc * se, best = k;
        }
        sel[c] = best;
      }
      return sel;
    };
    let gain = 0, v = 0, moved = 0;
    const byK = new Float64Array(ORD * 2), byKind = new Float64Array((NOPP + 1) * 3);
    folds.forEach((f, fi) => {
      const train = new Float64Array(f.s[cls].length);
      folds.forEach((g, gi) => { if (gi !== fi) for (let i = 0; i < train.length; i++) train[i] += g.s[cls][i]; });
      const sel = pick(train), S = f.s[cls];
      for (let c = 0; c < ncell; c++) {
        if (sel[c] < 0) continue;
        const o = (c * NCAND + sel[c]) * 3, n = S[o + 2];
        if (!n) continue;
        gain += S[o]; v += S[o + 1] - S[o] * S[o] / n; moved += n;
        const k = (cls ? Math.floor(c / NF) : c) % ORD;
        byK[k * 2] += S[o]; byK[k * 2 + 1] += n;
        if (!cls) for (let q = 0; q <= NOPP; q++) { const ok = ((q * NCELL0 + c) * NCAND + sel[c]) * 3, nk = f.sk[ok + 2]; if (nk) { byKind[q * 3] += f.sk[ok]; byKind[q * 3 + 1] += f.sk[ok + 1] - f.sk[ok] * f.sk[ok] / nk; } }
      }
    });
    lines.push(`  class ${cls ? '(type, k, picks, current family)' : '(type, k, picks)'} z ${zc}: ${(100 * gain / rows).toFixed(2)} +- ${(100 * Math.sqrt(v) / rows).toFixed(2)} ` +
      `points per decision; moves ${(100 * moved / rows).toFixed(0)}%; gain within moved cells by k: ` +
      Array.from({ length: ORD }, (_, k) => byK[k * 2 + 1] ? `${k}:${(100 * byK[k * 2] / byK[k * 2 + 1]).toFixed(1)}` : `${k}:-`).join(' '));
    if (!cls && kinds.length) {
      // Per opponent kind: the same selection's gain per decision of that kind (all its decisions, moved or not).
      const tot = new Float64Array(NOPP + 1);
      for (const f of folds) for (let q = 0; q <= NOPP; q++) for (let c = 0; c < NCELL0; c++) tot[q] += f.sk[((q * NCELL0 + c) * NCAND + NA) * 3 + 2];
      lines.push('      against ' + [first, ...kinds].map((name, q) => tot[q] ? `${name} ${(100 * byKind[q * 3] / tot[q]).toFixed(2)} +- ${(100 * Math.sqrt(byKind[q * 3 + 1]) / tot[q]).toFixed(2)} (${tot[q]} decisions)` : `${name} -`).join(', '));
    }
    const all = new Float64Array(folds[0].s[cls].length);
    for (const f of folds) for (let i = 0; i < all.length; i++) all[i] += f.s[cls][i];
    const sel = pick(all), cellsOut = [];
    for (let c = 0; c < ncell; c++) if (sel[c] >= 0) {
      const o = (c * NCAND + sel[c]) * 3, n = all[o + 2];
      const c0 = cls ? Math.floor(c / NF) : c, k = c0 % ORD, t = Math.floor(c0 / ORD) % NT, pi = Math.floor(c0 / (ORD * NT));
      cellsOut.push({ picks: pi + 3, type: TYPES[t], k, current_family: cls ? FAMILIES[c % NF] : null,
        choice: sel[c] === NA ? 'current' : armName(sel[c]), arm: sel[c] === NA ? -1 : sel[c], gain: all[o] / n, n });
    }
    selection[`${cls}-${zc}`] = cellsOut;
  }
  fs.writeFileSync(out.replace(/\.json$/, '.policy2.json'), JSON.stringify(selection) + '\n');
  return lines;
}

function report(cells, out, variant, lam, cv, rows, checkLines = []) {
  const lines = [`${rows} forced decisions; variant ${variant}; lam ${JSON.stringify(lam)}; cv ${JSON.stringify(cv)}`, '', ...checkLines, '',
    'Per pick count, type and ordinal, on held-out folds: rows, share where the model would leave the base, mean predicted gain',
    '(win points, x25 logit), the most common best arms, and the single-decision IPW estimate of following the model there',
    '(mean y 1[chosen = best] / q over forced rows, against the cell\'s mean y; noisy).'];
  for (const [pi, p] of [3, 4, 5].entries()) {
    lines.push('', `${p} picks`);
    for (let t = 0; t < NT; t++) for (let k = 0; k < ORD; k++) {
      const c = cells.get(`${pi},${t},${k}`);
      if (!c || c.n < 200) continue;
      const top = Object.entries(c.best).sort((a, b) => b[1] - a[1]).slice(0, 3).map(([a, x]) => `${armName(+a)} ${(100 * x / c.n).toFixed(0)}%`).join(', ');
      const ipw = c.ipwn ? (c.ipw / c.ipwn - c.y / c.n) * 100 : NaN;
      lines.push(`  ${TYPES[t].padEnd(14)} k${String(k).padEnd(2)} n ${String(c.n).padStart(6)}  change ${(100 * c.change / c.n).toFixed(0).padStart(3)}%  gain ${(25 * c.gain / c.n).toFixed(2).padStart(5)}  ${top}  | ipw ${ipw.toFixed(1)}`);
    }
  }
  fs.writeFileSync(out.replace(/\.json$/, '.md'), lines.join('\n') + '\n');
}

const self = p => fs.realpathSync(p).toLowerCase();
if (!isMainThread) workerMain();
else if (process.argv[1] && self(process.argv[1]) === self(fileURLToPath(import.meta.url))) await main();
