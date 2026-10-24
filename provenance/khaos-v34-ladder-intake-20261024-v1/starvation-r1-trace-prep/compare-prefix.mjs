import fs from 'node:fs';
import { decodeInputs } from './inputs-prefix.mjs';
import { decodeInputs as decodeOriginal } from '../../willow-pilgrimage-fuel-harness-v1/checkout-repo/tools/replay/harness/inputs.mjs';
import { compareInputs } from '../../willow-pilgrimage-fuel-harness-v1/checkout-repo/tools/replay/harness/compare.mjs';

const [originalPath, prefixPath, label] = process.argv.slice(2);
if (!originalPath || !prefixPath || !label) throw new Error('usage: node compare-prefix.mjs ORIGINAL.repl26a PREFIX.repl26a LABEL');
const originalBytes = fs.readFileSync(originalPath);
const a = await decodeOriginal(originalBytes);
const aDerived = await decodeInputs(originalBytes);
const b = await decodeInputs(fs.readFileSync(prefixPath));
const maxRound = 1;
const inputCut = d => ({ ...d, inputs: d.inputs.filter(x => x[1] <= maxRound), roundHashes: [], result: { outcome: 0, round: 0, gems: 0 }, finalHash: 'prefix-only' });
const roundCut = d => ({ ...d, inputs: [], roundHashes: d.roundHashes.filter(x => x[0] <= maxRound + 1), result: { outcome: 0, round: 0, gems: 0 }, finalHash: 'prefix-only' });
const aa = inputCut(a), bb = inputCut(b);
const c = compareInputs(aa, bb);
const roundCmp = compareInputs(roundCut(a), roundCut(b));
const derivedFullOriginalMatchesCanonical = !aDerived.timelineEnded && JSON.stringify(aDerived.inputs) === JSON.stringify(a.inputs) && JSON.stringify(aDerived.roundHashes) === JSON.stringify(a.roundHashes) && aDerived.finalHash === a.finalHash;
const target = d => d.inputs.find(x => x[1] === 1 && x[6] === 1 && x[4] === 10);
const at = target(aa), bt = target(bb);
const out = {
  schema: 'source-replay-prefix-comparison/v1', label,
  max_round_included: maxRound,
  source_was_truncated: b.timelineEnded,
  termination: b.termination,
  last_completed_round: b.lastCompletedRound,
  last_completed_step: b.lastCompletedStep,
  derived_decoder_full_original_crosscheck: { exact: derivedFullOriginalMatchesCanonical, inputs: [a.inputs.length, aDerived.inputs.length], round_hashes: [a.roundHashes.length, aDerived.roundHashes.length] },
  original_input_count_through_round_1: aa.inputs.length,
  candidate_input_count_through_round_1: bb.inputs.length,
  original_round_starts_through_round_2: a.roundHashes.filter(x => x[0] <= maxRound + 1),
  candidate_round_starts_through_round_2: b.roundHashes.filter(x => x[0] <= maxRound + 1),
  first_input_diff: c.firstInputDiff,
  first_round_diff: roundCmp.firstRoundDiff,
  rounds_matched_through_boundary_round_2: roundCmp.roundsMatched,
  prefix_exact_through_round_1: derivedFullOriginalMatchesCanonical && !c.firstInputDiff && !roundCmp.firstRoundDiff && aa.inputs.length === bb.inputs.length && roundCmp.roundsMatched === 3,
  target_actor1_round1_input: { original: at ?? null, candidate: bt ?? null },
  full_result_comparison: 'not applicable: candidate replay is intentionally truncated after round 2',
};
console.log(JSON.stringify(out, null, 2));
