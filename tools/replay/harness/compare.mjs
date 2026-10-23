// Fidelity check: does a re-run replay reproduce the original, input by input and state by state?
//   node tools/replay/harness/compare.mjs <original inputs.json[.gz] | .repl26a> <rerun .repl26a> [--fuel LADDER.fuel --team a|b] [--rollover-as-end]
// Compares every recorded input of both teams (step, round, kind, actor, tiles, slot, priority, and
// the decoded item/target), the observer snapshot hash at each round start, the final result and,
// with --fuel, that team's per-turn fuel against the re-run bundle's team-X.fuel. --rollover-as-end
// reports the comparison that treats Turn rollover as End turn (both are always computed).
import fs from 'node:fs';
import path from 'node:path';
import zlib from 'node:zlib';
import { fileURLToPath } from 'node:url';
import { decodeInputs, K, COLS } from './inputs.mjs';
import { STEP_KINDS, unwrapReplay } from '../engine.mjs';
import { loadInputs } from './gen_puppet.mjs';

// Per-turn fuel files ('fuel26a'): 8-byte magic, 5 header bytes, then little-endian u64s: 8 budget
// constants, the draft turns, then one value per champion turn in turn order (fuel used).
export function readFuel(bytes) {
  if (bytes.length < 13 || bytes.toString('latin1', 0, 7) !== 'a62leuf') throw new Error('not a fuel26a file');
  const n = (bytes.length - 13) / 8;
  const v = new Array(n);
  for (let i = 0; i < n; i++) v[i] = Number(bytes.readBigUInt64LE(13 + 8 * i));
  return { header: [...bytes.subarray(8, 13)], values: v };
}

// The files a local bundle holds next to replay.repl26a.
export function bundleFiles(bytes) {
  const out = {};
  if (bytes.readUInt32LE(0) !== 0x04034b50) return out;
  let eocd = bytes.length - 22;
  while (eocd >= 0 && bytes.readUInt32LE(eocd) !== 0x06054b50) eocd--;
  const n = bytes.readUInt16LE(eocd + 10);
  let p = bytes.readUInt32LE(eocd + 16);
  for (let i = 0; i < n; i++) {
    const method = bytes.readUInt16LE(p + 10), csize = bytes.readUInt32LE(p + 20);
    const nameLen = bytes.readUInt16LE(p + 28), extraLen = bytes.readUInt16LE(p + 30), commentLen = bytes.readUInt16LE(p + 32);
    const local = bytes.readUInt32LE(p + 42), name = bytes.subarray(p + 46, p + 46 + nameLen).toString();
    p += 46 + nameLen + extraLen + commentLen;
    const start = local + 30 + bytes.readUInt16LE(local + 26) + bytes.readUInt16LE(local + 28);
    const data = bytes.subarray(start, start + csize);
    out[name] = method === 8 ? zlib.inflateRawSync(data) : Buffer.from(data);
  }
  return out;
}

const describe = r => r ? `s${r[0]} r${r[1]} ${STEP_KINDS[r[3]]}@${r[4]} actor${r[5]}:${r[6]} (${r[7]},${r[8]})->(${r[9]},${r[10]}) slot${r[11]} pr${r[13]} x${r[14]},${r[15]}` : 'end of stream';

// opts.rolloverAsEnd: treat a Turn rollover (out of fuel) as an End turn on both sides.
export function compareInputs(a, b, { rolloverAsEnd = false } = {}) {
  const n = Math.min(a.inputs.length, b.inputs.length);
  const res = { inputs: [a.inputs.length, b.inputs.length], firstInputDiff: null, roundsMatched: 0, rounds: [a.roundHashes.length, b.roundHashes.length], firstRoundDiff: null };
  const kind = v => rolloverAsEnd && v === K['Turn rollover'] ? K['End turn'] : v;
  for (let i = 0; i < n; i++) {
    const x = a.inputs[i], y = b.inputs[i];
    if (x.some((v, j) => j === 3 ? kind(v) !== kind(y[j]) : v !== y[j])) {
      res.firstInputDiff = { index: i, round: x[1], step: x[0], actor: x[6], kind: STEP_KINDS[x[3]], rerunKind: STEP_KINDS[y[3]], original: describe(x), rerun: describe(y), originalRec: x, rerunRec: y };
      break;
    }
  }
  if (!res.firstInputDiff && a.inputs.length !== b.inputs.length) {
    const r = a.inputs[n] ?? b.inputs[n];
    res.firstInputDiff = { index: n, round: r[1], step: r[0], actor: r[6], kind: a.inputs[n] ? STEP_KINDS[r[3]] : null, rerunKind: b.inputs[n] ? STEP_KINDS[r[3]] : null, original: describe(a.inputs[n]), rerun: describe(b.inputs[n]) };
  }
  const hb = new Map(b.roundHashes.map(([r, s, h]) => [r, [s, h]]));
  for (const [r, s, h] of a.roundHashes) {
    const o = hb.get(r);
    if (!o || o[0] !== s || o[1] !== h) { res.firstRoundDiff = { round: r, step: s, rerunStep: o?.[0] }; break; }
    res.roundsMatched++;
  }
  res.result = [a.result, b.result];
  res.resultMatch = JSON.stringify(a.result) === JSON.stringify(b.result) && a.finalHash === b.finalHash;
  res.exact = !res.firstInputDiff && !res.firstRoundDiff && res.resultMatch && a.roundHashes.length === b.roundHashes.length;
  return res;
}

// Champion turns of `team` in order, as the fuel file lists them: one per End turn / Turn rollover / Bot error.
export function teamTurns(d, team) {
  const ids = new Set(d.roster.filter(c => c.team === team).map(c => c.id));
  return d.inputs.filter(r => r[4] === 10 && r[5] === 1 && ids.has(r[6]) && (r[3] === K['End turn'] || r[3] === K['Turn rollover'] || r[3] === K['Bot error']))
    .map(r => ({ round: r[1], id: r[6], step: r[0], rollover: r[3] === K['Turn rollover'] }));
}

// Per-turn fuel of one team: ladder `fa` against re-run `fb`. `turns` (teamTurns of the original)
// labels champion turns; values before them are the 8 budget constants and the draft turns. A first
// turn (the draft's first, or a champion's first) has the 2x/10x budget.
export function compareFuel(fa, fb, turns) {
  const a = fa.values, b = fb.values;
  const nDraft = turns ? a.length - 8 - turns.length : null;
  const res = { lengths: [a.length, b.length], draftTurns: nDraft, diffs: 0, firstTurnDiffs: 0, maxAbs: 0, firstTurnOnly: true, firstDiff: null, list: [] };
  const seen = new Set();
  const label = i => {
    if (i < 8) return { what: 'constant' };
    if (!turns || i < 8 + nDraft) return { what: 'draft', turn: i - 8, first: i === 8 };
    const t = turns[i - 8 - nDraft];
    return t ? { what: 'turn', round: t.round, id: t.id, rollover: t.rollover, first: t.first } : { what: 'extra' };
  };
  if (turns) for (const t of turns) { t.first = !seen.has(t.id); seen.add(t.id); }
  for (let i = 0; i < Math.max(a.length, b.length); i++) {
    if (a[i] === b[i]) continue;
    const l = label(i), d = (b[i] ?? 0) - (a[i] ?? 0);
    res.diffs++;
    if (l.first) res.firstTurnDiffs++; else res.firstTurnOnly = false;
    res.maxAbs = Math.max(res.maxAbs, Math.abs(d));
    const e = { index: i, ladder: a[i], rerun: b[i], delta: d, ...l };
    if (!res.firstDiff) res.firstDiff = e;
    if (res.list.length < 50) res.list.push(e);
  }
  if (!res.diffs) res.firstTurnOnly = null;
  return res;
}

// Validates one re-run against the original: inputs (strict, and with rollovers as end turns),
// round hashes, result and, given the ladder .fuel of `team` (0 a, 1 b), that team's per-turn fuel.
export async function validateRun(orig, rerunBytes, { ladderFuel = null, team = null, decoded = null } = {}) {
  const b = decoded ?? await decodeInputs(rerunBytes);
  const res = compareInputs(orig, b);
  const loose = compareInputs(orig, b, { rolloverAsEnd: true });
  res.exactIgnoringRollovers = loose.exact;
  res.firstInputDiffIgnoringRollovers = loose.firstInputDiff;
  if (ladderFuel && team !== null) {
    const files = bundleFiles(rerunBytes);
    const f = files[`team-${'ab'[team]}.fuel`];
    res.fuel = f ? compareFuel(readFuel(ladderFuel), readFuel(f), teamTurns(orig, team)) : { error: 'no fuel file in the bundle' };
  }
  return { res, decoded: b };
}

if (process.argv[1] && fileURLToPath(import.meta.url) === process.argv[1]) {
  const args = process.argv.slice(2);
  const opt = (k) => { const i = args.indexOf(k); return i >= 0 ? args[i + 1] : null; };
  const [orig, rerun] = args.filter((x, i) => !x.startsWith('--') && !['--fuel', '--team'].includes(args[i - 1]));
  if (!orig || !rerun) { console.error('usage: compare.mjs ORIG(inputs.json[.gz]|.repl26a) RERUN.repl26a [--fuel LADDER.fuel --team a|b] [--rollover-as-end]'); process.exit(2); }
  const a = orig.endsWith('.repl26a') ? await decodeInputs(fs.readFileSync(orig)) : loadInputs(orig);
  const raw = fs.readFileSync(rerun);
  const fuel = opt('--fuel'), team = opt('--team');
  const { res } = await validateRun(a, raw, { ladderFuel: fuel && fs.readFileSync(fuel), team: team === null ? null : 'ab'.indexOf(team) });
  if (args.includes('--rollover-as-end')) { res.exact = res.exactIgnoringRollovers; res.firstInputDiff = res.firstInputDiffIgnoringRollovers; }
  console.log(JSON.stringify(res, null, 1));
}
