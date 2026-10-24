import fs from 'node:fs';
import { decodeInputs } from './inputs-prefix.mjs';
import { bundleFiles } from '../../willow-pilgrimage-fuel-harness-v1/checkout-repo/tools/replay/harness/compare.mjs';
import { STEP_KINDS } from '../../willow-pilgrimage-fuel-harness-v1/checkout-repo/tools/replay/engine.mjs';
const [recPath, tracePath, sourceJsonPath, label] = process.argv.slice(2);
if (!recPath || !tracePath || !sourceJsonPath || !label) throw new Error('usage: validate-trace.mjs RECORDER TRACE FULL_SOURCE_JSON LABEL');
const recBytes=fs.readFileSync(recPath), traceBytes=fs.readFileSync(tracePath);
const rec=await decodeInputs(recBytes), trace=await decodeInputs(traceBytes), source=JSON.parse(fs.readFileSync(sourceJsonPath,'utf8'));
const files=b=>bundleFiles(b);
const decodeText=b=>b.toString('utf8').replaceAll('\0','');
const recText=decodeText(files(recBytes)['team-a.stdout']??Buffer.alloc(0));
const traceText=decodeText(files(traceBytes)['team-a.stdout']??Buffer.alloc(0));
function records(text, marker, pattern) { const out={}; for(const line of text.split(/\r?\n/)){const m=line.match(pattern); if(m) out[`${m[1]}:${m[2]}`]=m.slice(3).map(Number);} return out; }
const recY=records(recText,'@y',/^@y (-?\d+) (\d+) (\d+) (\d+) (\d+)$/);
const traceV=records(traceText,'@v',/^@v (-?\d+) (\d+) (\d+) (\d+) (\d+)$/);
const recR=records(recText,'@r',/^@r (-?\d+) (\d+) (\d+) (\d+)$/);
const traceO=records(traceText,'@o',/^@o (-?\d+) (\d+) (\d+) (\d+)$/);
const mismatchLines=traceText.split(/\r?\n/).filter(x=>x.startsWith('@! '));
const hardMismatch=mismatchLines.filter(x=>!x.startsWith('@! tail '));
const keyCompare=(a,b)=>{const ak=Object.keys(a).sort(),bk=Object.keys(b).sort();const common=ak.filter(k=>k in b);return {counts:[ak.length,bk.length],common:common.length,diff:common.filter(k=>JSON.stringify(a[k])!==JSON.stringify(b[k])).slice(0,20),onlyA:ak.filter(k=>!(k in b)).slice(0,20),onlyB:bk.filter(k=>!(k in a)).slice(0,20)};};
const roster=new Map(source.roster.map(x=>[x.id,x.team]));
const status={};
const statusKinds=new Set([STEP_KINDS.indexOf('Turn rollover'),STEP_KINDS.indexOf('Bot error')]);
for(const r of source.inputs){if(r[1]>1 || r[4]!==10 || !statusKinds.has(r[3]))continue;const team=roster.get(r[6]);const k=`${team===0?'A':team===1?'B':'?'}:actor${r[6]}:${STEP_KINDS[r[3]]}`;status[k]=(status[k]??0)+1;}
const starLines=traceText.split(/\r?\n/).filter(x=>/^STAR_(ALTAR|LATE|SCAN|PICK|ROUTE|GOALS) /.test(x));
const parseFields=line=>{const [tag,...parts]=line.split(/\s+/);const vals={};for(const p of parts){const m=p.match(/^([a-zA-Z_]+)(-?\d+(?:\.\d+)?(?:,-?\d+(?:\.\d+)?)?)$/);if(!m)continue;let k=m[1],raw=m[2];if(k==='r')k='round';if(k==='g')k='group';if(raw.includes(',')){vals[k]=raw.split(',').map(Number);continue;}vals[k]=Number(raw);}return {tag,values:vals,line};};
const out={schema:'starvation-r1-trace-validation/v1',label,
  timeline:{recorderEndedAtTimeline:rec.timelineEnded,traceEndedAtTimeline:trace.timelineEnded,recorderLastRound:rec.lastCompletedRound,traceLastRound:trace.lastCompletedRound},
  hostCallValidation:{recorderSegments:Object.keys(recY).length,traceSegments:Object.keys(traceV).length,segmentComparison:keyCompare(recY,traceV),recorderRolloverPoints:Object.keys(recR).length,traceReproducedRolloverPoints:Object.keys(traceO).length,rolloverComparison:keyCompare(recR,traceO),mismatchLines,hardMismatchLines:hardMismatch,passed:!hardMismatch.length&&keyCompare(recY,traceV).diff.length===0&&keyCompare(recR,traceO).diff.length===0&&keyCompare(recY,traceV).onlyA.length===0&&keyCompare(recY,traceV).onlyB.length===0},
  originalReplayNativeStatusThroughRound1:status,
  statusNote:'Counts are sourced from the matching original full replay but filtered to round <= 1; empty means no native rollover or Bot error in the target prefix.',
  traceFields:starLines.map(parseFields),
  source_prefix_validation:`${label}-recorder-prefix-validation.json`,
  trace_replay_sha256:(await import('node:crypto')).createHash('sha256').update(traceBytes).digest('hex'),
  recorder_replay_sha256:(await import('node:crypto')).createHash('sha256').update(recBytes).digest('hex')};
console.log(JSON.stringify(out,null,2));
