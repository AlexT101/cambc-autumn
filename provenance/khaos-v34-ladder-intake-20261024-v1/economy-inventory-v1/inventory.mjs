import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import { fileURLToPath } from 'node:url';
import { createEngine } from '../../../tools/mapgen/wasm.mjs';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../../../');
const source = path.join(root, 'provenance/willow-focus-safe-yield-v33-full1104-preflight-20261024-v1/map-inventory.json');
const inv = JSON.parse(fs.readFileSync(source, 'utf8'));
const maps = inv.suites.find(s => s.name === 'published40').maps;
const reward = { wolf: [4,40], elk: [15,90], golem: [36,160], gem_cluster: [7,0], gold_cluster: [0,20], monolith: [200,300] };
const engine = await createEngine();
const rows = [];
for (const row of maps) {
  const bytes = fs.readFileSync(row.path);
  const sha256 = crypto.createHash('sha256').update(bytes).digest('hex');
  if (sha256 !== row.sha256) throw new Error(`source hash mismatch: ${row.path}`);
  engine.load(bytes);
  const m = engine.decode(bytes);
  const counts = Object.fromEntries(Object.keys(reward).map(k => [k, m.camps.filter(c => c.type === k).length]));
  const ordinary = Object.fromEntries(['gems','gold'].map((what, i) => [what, Object.entries(counts).filter(([k]) => k !== 'monolith').reduce((n,[k,v]) => n + v * reward[k][i], 0)]));
  const gs = m.groups.filter(g => g.camps.every(i => m.camps[i].type !== 'monolith'));
  const mixed = m.groups.filter(g => g.camps.some(i => m.camps[i].type === 'monolith') && g.camps.some(i => m.camps[i].type !== 'monolith')).length;
  const ordinaryGroups = m.groups.length - m.groups.filter(g => g.camps.some(i => m.camps[i].type === 'monolith')).length;
  rows.push({name:path.basename(row.path,'.map26a'),path:row.path,sha256,width:m.width,height:m.height,pickcount:m.picks,nativeTeamSize:m.picks,campCounts:counts,ordinaryRewards:ordinary,ordinaryGroupCount:ordinaryGroups,ordinaryMixedGroupCount:gs.filter(g=>g.camps.length>1).length,groupsContainingMonolith:m.groups.length-ordinaryGroups,monolithMixedGroupCount:mixed,gemClusterStratum:counts.gem_cluster===0?'zero':counts.gem_cluster===1?'minimum-positive':'above-minimum',goldClusterStratum:counts.gold_cluster===0?'zero':counts.gold_cluster===1?'minimum-positive':'above-minimum'});
}
for (const k of ['gem_cluster','gold_cluster']) { const positive = rows.map(r => r.campCounts[k]).filter(n => n > 0); const min = Math.min(...positive); for (const r of rows) r[k === 'gem_cluster' ? 'gemClusterStratum' : 'goldClusterStratum'] = r.campCounts[k] === 0 ? 'zero' : r.campCounts[k] === min ? `minimum-positive-${min}` : 'above-minimum'; }
const out = {schema:'public40-static-economy-inventory-v1',sourceManifest:source,sourceManifestSha256:crypto.createHash('sha256').update(fs.readFileSync(source)).digest('hex'),mapCount:rows.length,rulesSource:'cambc-rules.yaml (camp rewards and group semantics)',scope:'Public whole-layout native map description; all mirrored camps/groups included. Accessibility/vision/ownership shares are not inferred.',rows};
fs.writeFileSync(path.join(path.dirname(fileURLToPath(import.meta.url)),'RESULT.json'),JSON.stringify(out,null,2)+'\n');
const lines=['# Published 40-map static economy inventory','','Native map data for the exact `published40` set in the source inventory manifest. Rewards use the current engine-verified camp values. Counts and ordinary reward totals include the mirrored whole map; ordinary totals exclude every monolith. These are whole-layout supplies, not a claim that one team can access or capture them. This static parse does not infer accessible share, capture timing, combat effort, or weighted-selection eligibility.','', '| Map | Size | Picks/team | Wolf | Elk | Golem | Gem clusters | Gold clusters | Monoliths | Ordinary gems | Ordinary gold | Ordinary groups | Ordinary mixed groups |','|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|'];
for(const r of rows) lines.push(`| ${r.name} | ${r.width}×${r.height} | ${r.pickcount} | ${r.campCounts.wolf} | ${r.campCounts.elk} | ${r.campCounts.golem} | ${r.campCounts.gem_cluster} | ${r.campCounts.gold_cluster} | ${r.campCounts.monolith} | ${r.ordinaryRewards.gems} | ${r.ordinaryRewards.gold} | ${r.ordinaryGroupCount} | ${r.ordinaryMixedGroupCount} |`);
const strata=(key)=>Object.fromEntries([...new Set(rows.map(r=>r[key]))].map(s=>[s,rows.filter(r=>r[key]===s).length]));
lines.push('',`Gem cluster strata: ${JSON.stringify(strata('gemClusterStratum'))}.`,`Gold cluster strata: ${JSON.stringify(strata('goldClusterStratum'))}.`);
const five=rows.filter(r=>r.pickcount===5).sort((a,b)=>a.ordinaryRewards.gold-b.ordinaryRewards.gold);
lines.push('',`Lowest ordinary gold among ${five.length} five-pick maps: ${five[0]?.name} (${five[0]?.ordinaryRewards.gold}).`,'','The native map schema exposes full map geometry, camp types, groups, and pick count. Team size equals map pick count under the rules. The inventory does not compute pathable/visible share or model team strategy.');
fs.writeFileSync(path.join(path.dirname(fileURLToPath(import.meta.url)),'RESULT.md'),lines.join('\n')+'\n');
console.log(`wrote ${rows.length} map rows`);
