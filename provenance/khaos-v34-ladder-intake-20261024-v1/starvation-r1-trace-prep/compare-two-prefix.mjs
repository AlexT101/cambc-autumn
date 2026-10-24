import fs from 'node:fs';
import { decodeInputs } from './inputs-prefix.mjs';
import { compareInputs } from '../../willow-pilgrimage-fuel-harness-v1/checkout-repo/tools/replay/harness/compare.mjs';
const [referencePath, candidatePath, label] = process.argv.slice(2);
if (!referencePath || !candidatePath || !label) throw new Error('usage: node compare-two-prefix.mjs RECORDER.repl26a TRACE.repl26a LABEL');
const reference = await decodeInputs(fs.readFileSync(referencePath));
const candidate = await decodeInputs(fs.readFileSync(candidatePath));
const maxRound = 1;
const inCut = d => ({...d, inputs:d.inputs.filter(x=>x[1]<=maxRound), roundHashes:[], result:{}, finalHash:''});
const roundCut = d => ({...d, inputs:[], roundHashes:d.roundHashes.filter(x=>x[0]<=maxRound+1), result:{}, finalHash:''});
const ci=compareInputs(inCut(reference),inCut(candidate));
const cr=compareInputs(roundCut(reference),roundCut(candidate));
const targets=d=>d.inputs.filter(x=>x[1]===1&&x[6]===1&&x[4]===10);
const out={schema:'recorder-tracer-prefix-validation/v1',label,rounds_included:[0,1],
  reference_truncated:reference.timelineEnded,candidate_truncated:candidate.timelineEnded,
  reference_last_round:reference.lastCompletedRound,candidate_last_round:candidate.lastCompletedRound,
  inputs_through_round_1:[ci.inputs[0],ci.inputs[1]],first_input_diff:ci.firstInputDiff,
  round_starts_through_boundary_round_2:[cr.rounds[0],cr.rounds[1]],first_round_diff:cr.firstRoundDiff,
  rounds_matched_through_boundary_round_2:cr.roundsMatched,
  actor1_round1_inputs:{reference:targets(reference),candidate:targets(candidate)},
  prefix_exact_through_round_1:!ci.firstInputDiff&&!cr.firstRoundDiff&&ci.inputs[0]===ci.inputs[1]&&cr.roundsMatched===3};
console.log(JSON.stringify(out,null,2));
