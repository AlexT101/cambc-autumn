import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import { fileURLToPath } from 'node:url';
import { createEngine } from '../../../tools/mapgen/wasm.mjs';
import { Grid, GROUND, BUSH, WALL, HOLE, ALTAR, N4, N8 } from '../../../tools/mapgen/grid.mjs';
import { metrics } from '../../../tools/mapgen/generate.mjs';

const here=path.dirname(fileURLToPath(import.meta.url));
const root=path.resolve(here,'../../..');
const sha=b=>crypto.createHash('sha256').update(b).digest('hex');
const indexPins={gen:'57b286d75aead0a5ef255d553268c92c0ec2d296cff26e03415b3a65a121f144','gen-s1':'fcd775d0cd1ca47322070933cc003a947bdc4954860a358c77b2de8b1af8f7ac'};
const camp={wolf:{hp:1350,strength:20,range:3},elk:{hp:2400,strength:60,range:4},golem:{hp:5000,strength:120,range:4},monolith:{hp:20000,strength:200,range:5},gem_cluster:{hp:120,strength:0,range:0},gold_cluster:{hp:120,strength:0,range:0}};
const engine=await createEngine();
const indexEntries=[];
for(const suite of ['gen','gen-s1']){
 const ip=path.join(root,'maps',suite,'index.json'), ib=fs.readFileSync(ip);
 if(sha(ib)!==indexPins[suite]) throw new Error(`${suite} index pin mismatch`);
 const idx=JSON.parse(ib);
 for(const e of idx.maps.filter(x=>x.metrics?.picks===3)) indexEntries.push({suite,preset:e.preset??e.spec?.preset??null,file:e.file,path:path.join(root,'maps',suite,e.file),indexSha256:sha(ib)});
}
const pool=[], seen=new Map(), duplicateHashes=[];
for(const e of indexEntries){
 const bytes=fs.readFileSync(e.path), mapSha=sha(bytes);
 engine.load(bytes); const m=engine.decode(bytes);
 if(m.picks!==3) throw new Error(`index/map native pick mismatch ${e.path}: ${m.picks}`);
 if(seen.has(mapSha)){duplicateHashes.push({sha256:mapSha,canonical:seen.get(mapSha),duplicate:{suite:e.suite,path:e.path}});continue;}
 const g=Grid.fromMap(m), geo=metrics(g);
 const groups=g.groups().map((grp)=>{
  const members=grp.members.slice().sort((a,b)=>a.y-b.y||a.x-b.x||a.type.localeCompare(b.type));
  return {id:members.map(c=>`${c.x},${c.y}:${c.type}`).join('|'),members,shared:grp.shared,gems:grp.gems,gold:grp.gold,hasMonolith:members.some(c=>c.type==='monolith'),hp:members.reduce((n,c)=>n+camp[c.type].hp,0),strength:members.reduce((n,c)=>n+camp[c.type].strength,0),damaging:members.some(c=>camp[c.type].strength>0)};
 });
 const allCamps=g.allCamps(), campMask=g.campMask(), spawnA=g.spawnTiles(0),spawnB=g.spawnTiles(1);
 const passBase=g.walkable();
 const passA=passBase.slice(),passB=passBase.slice(); for(const i of spawnB)passA[i]=0; for(const i of spawnA)passB[i]=0;
 const passAc=passA.slice(),passBc=passB.slice(); for(let i=0;i<campMask.length;i++)if(campMask[i]){passAc[i]=0;passBc[i]=0;}
 const damaging=allCamps.filter(c=>camp[c.type].strength>0);
 const dangerMask=new Uint8Array(g.t.length); for(const c of damaging){const r=camp[c.type].range;for(let y=Math.max(0,c.y-r);y<=Math.min(g.H-1,c.y+r);y++)for(let x=Math.max(0,c.x-r);x<=Math.min(g.W-1,c.x+r);x++)if(Math.max(Math.abs(x-c.x),Math.abs(y-c.y))<=r)dangerMask[y*g.W+x]=1;}
 const passASafe=passAc.slice(),passBSafe=passBc.slice();for(let i=0;i<dangerMask.length;i++)if(dangerMask[i]){passASafe[i]=0;passBSafe[i]=0;}
 const distA=g.bfs(spawnA,passAc),distB=g.bfs(spawnB,passBc),distATerrain=g.bfs(spawnA,passA),distBTerrain=g.bfs(spawnB,passB),distASafe=g.bfs(spawnA,passASafe),distBSafe=g.bfs(spawnB,passBSafe);
 // Terrain-only vision approximation: integer Bresenham centerline; walls and bushes occlude, holes do not.
 const lineVisible=(from,to,bushIds)=>{
  if(g.t[to]===BUSH&&!(g.t[from]===BUSH&&bushIds[from]===bushIds[to]))return false;
  let x0=from%g.W,y0=Math.floor(from/g.W),x1=to%g.W,y1=Math.floor(to/g.W);
  const sx=x0<x1?1:-1,sy=y0<y1?1:-1,dx=Math.abs(x1-x0),dy=Math.abs(y1-y0); let err=dx-dy,x=x0,y=y0;
  while(!(x===x1&&y===y1)){
   const e2=2*err; if(e2>-dy){err-=dy;x+=sx;} if(e2<dx){err+=dx;y+=sy;}
   if(x===x1&&y===y1)break;
   const i=y*g.W+x,k=g.t[i]; if(k===WALL)return false; if(k===BUSH&&!(g.t[from]===BUSH&&bushIds[i]===bushIds[from]))return false;
  }
  return true;
 };
 const bushIds=new Int32Array(g.t.length).fill(-1);let bid=0;
 for(let i=0;i<g.t.length;i++)if(g.t[i]===BUSH&&bushIds[i]<0){const q=[i];bushIds[i]=bid;for(let h=0;h<q.length;h++){const z=q[h],x=z%g.W,y=Math.floor(z/g.W);for(const[dx,dy]of N4){const nx=x+dx,ny=y+dy,j=ny*g.W+nx;if(nx>=0&&ny>=0&&nx<g.W&&ny<g.H&&g.t[j]===BUSH&&bushIds[j]<0){bushIds[j]=bid;q.push(j);}}}bid++;}
 const stationsFor=(team,passes,distance=null,safe=false)=>{
   const d=distance??(team===0?distA:distB), pass=passes;
   const legal=[];for(let i=0;i<pass.length;i++)if(pass[i]&&d[i]>=0)legal.push(i);
   const enemySpawn=team===0?spawnB:spawnA;
   return {d,legal,enemySpawn,safe};
 };
 const memberStation=(c,team,ctx)=>{
   let best=Infinity;
   for(const s of ctx.legal){const sx=s%g.W,sy=Math.floor(s/g.W);if(Math.max(Math.abs(sx-c.x),Math.abs(sy-c.y))>3)continue;
    if(!lineVisible(s,c.y*g.W+c.x,bushIds))continue;
    if(ctx.safe&&damaging.some(d=>Math.max(Math.abs(sx-d.x),Math.abs(sy-d.y))<=camp[d.type].range))continue;
    if(ctx.d[s]>=0&&ctx.d[s]<best)best=ctx.d[s];
   }
   return Number.isFinite(best)?best:null;
 };
 const teams=[];
 for(const team of [0,1]){
  const ownPass=team===0?passAc:passBc, enemyPass=team===0?passBc:passAc, ownSafePass=team===0?passASafe:passBSafe, enemySafePass=team===0?passBSafe:passASafe;
  const ctx=stationsFor(team,ownPass), enemyCtx=stationsFor(1-team,enemyPass), safeCtx=stationsFor(team,ownSafePass,team===0?distASafe:distBSafe,true), enemySafeCtx=stationsFor(1-team,enemySafePass,team===0?distBSafe:distASafe,true);
  const sideGroups=groups.map(gr=>{
   const members=gr.members;
   if(gr.hasMonolith)return null;
   const own=members.map(c=>({x:c.x,y:c.y,type:c.type,hp:camp[c.type].hp,strength:camp[c.type].strength,gems:({wolf:4,elk:15,golem:36,monolith:200,gem_cluster:7,gold_cluster:0})[c.type],gold:({wolf:40,elk:90,golem:160,monolith:300,gem_cluster:0,gold_cluster:20})[c.type],stationDist:memberStation(c,team,ctx),safeStationDist:memberStation(c,team,safeCtx),enemyStationDist:memberStation(c,1-team,enemyCtx),enemySafeStationDist:memberStation(c,1-team,enemySafeCtx)}));
   const ds=own.map(x=>x.stationDist).filter(x=>x!==null), es=own.map(x=>x.enemyStationDist).filter(x=>x!==null);
   if(!ds.length)return null;
   const stationDist=Math.min(...ds),enemyStationDist=es.length?Math.min(...es):null;
   const allMembersAccessible=own.every(x=>x.stationDist!==null),safeAccessible=own.every(x=>x.safeStationDist!==null);
   const ownArrival=allMembersAccessible?Math.max(...own.map(x=>x.stationDist)):stationDist;
   const enemyArrival=own.every(x=>x.enemyStationDist!==null)?Math.max(...own.map(x=>x.enemyStationDist)):enemyStationDist;
   return {id:gr.id,shared:gr.shared,members:own,gems:gr.gems,gold:gr.gold,hp:own.reduce((n,c)=>n+c.hp,0),stationDist,enemyStationDist,allMembersAccessible,safeAccessible,arrivalRelation:enemyArrival===null?'enemy_unreachable':ownArrival<enemyArrival?'own_earlier':ownArrival===enemyArrival?'shared_tie':'enemy_earlier',harmless:own.every(c=>c.strength===0),damaging:own.some(c=>c.strength>0)};
  }).filter(Boolean).sort((a,b)=>a.stationDist-b.stationDist||a.id.localeCompare(b.id));
  const top3=sideGroups.slice(0,3), harmless=top3.filter(x=>x.harmless&&x.allMembersAccessible), safeHarmless=top3.filter(x=>x.harmless&&x.safeAccessible);
  const cutoff=top3.length===3?top3[2].stationDist:null, cutoffTies=cutoff===null?[]:sideGroups.filter(x=>x.stationDist===cutoff);
  const tribute=(pass,d)=>{
    const altars=[];for(let i=0;i<g.t.length;i++)if(g.t[i]===ALTAR){let best=Infinity;for(let yy=-1;yy<=1;yy++)for(let xx=-1;xx<=1;xx++){const x=i%g.W+xx,y=Math.floor(i/g.W)+yy;if((xx||yy)&&x>=0&&y>=0&&x<g.W&&y<g.H){const j=y*g.W+x;if(pass[j]&&d[j]>=0)best=Math.min(best,d[j]);}} if(Number.isFinite(best))altars.push({x:i%g.W,y:Math.floor(i/g.W),distance:best});}
    return altars.sort((a,b)=>a.distance-b.distance||a.y-b.y||a.x-b.x)[0]??null;
  };
  const terrainPass=team===0?passA:passB, terrainD=team===0?distATerrain:distBTerrain;
  const closestSpawnGap=(d,enemy)=>{let best=Infinity;for(const i of enemy){const x=i%g.W,y=Math.floor(i/g.W);for(const[dx,dy]of N8){const nx=x+dx,ny=y+dy;if(nx>=0&&ny>=0&&nx<g.W&&ny<g.H){const z=d[ny*g.W+nx];if(z>=0&&z<best)best=z;}}}return Number.isFinite(best)?best:null;};
  teams.push({team:team===0?'A':'B',openness:geo.openness,choke:geo.choke,walkSpawnSeparation:closestSpawnGap(team===0?distATerrain:distBTerrain,team===0?spawnB:spawnA),spawnSeparationWithCamps:closestSpawnGap(team===0?distA:distB,team===0?spawnB:spawnA),nearestTributeTerrainOnly:tribute(terrainPass,terrainD),nearestTributeWithCampTilesBlocked:tribute(team===0?passAc:passBc,team===0?distA:distB),nearbyOrdinaryGroups:top3,nearestThreeBoundaryTie:{distance:cutoff,groupsAtDistance:cutoffTies.map(x=>x.id),count:cutoffTies.length,deterministicTieBreak:'group id'},earlyHarmlessRampGems:harmless.reduce((n,x)=>n+x.gems,0),earlyHarmlessRampGroupCount:harmless.length,conservativeHarmlessGems:safeHarmless.reduce((n,x)=>n+x.gems,0),conservativeHarmlessGroupCount:safeHarmless.length,parallelHarmlessJobs:harmless.length,damagingGroupsWithinThree:top3.filter(x=>x.damaging).map(x=>({id:x.id,gems:x.gems,gold:x.gold,hp:x.hp,members:x.members.map(c=>({x:c.x,y:c.y,type:c.type,hp:c.hp,strength:c.strength})),stationDist:x.stationDist,legalStationAvailable:x.allMembersAccessible})),bushCount:Array.from(g.t).filter(t=>t===BUSH).length,holeCount:Array.from(g.t).filter(t=>t===HOLE).length});
 }
 const halfTotals={};for(const side of [0,1]){const campsHalf=allCamps.filter(c=>c.team===side);halfTotals[side===0?'A':'B']={counts:Object.fromEntries(Object.keys(camp).map(k=>[k,campsHalf.filter(c=>c.type===k).length])),gems:campsHalf.reduce((n,c)=>n+({wolf:4,elk:15,golem:36,monolith:200,gem_cluster:7,gold_cluster:0})[c.type],0),gold:campsHalf.reduce((n,c)=>n+({wolf:40,elk:90,golem:160,monolith:300,gem_cluster:0,gold_cluster:20})[c.type],0)};}
 const groupKeys=new Set(groups.map(gr=>gr.id));for(const gr of groups){const reflected=gr.members.map(c=>{const [x,y]=g.mirrorXY(c.x,c.y);return {x,y,type:c.type};}).sort((a,b)=>a.y-b.y||a.x-b.x||a.type.localeCompare(b.type)).map(c=>`${c.x},${c.y}:${c.type}`).join('|');if(!groupKeys.has(reflected))throw new Error(`group mirror symmetry mismatch ${e.path} ${gr.id}`);}
 if(JSON.stringify(halfTotals.A)!==JSON.stringify(halfTotals.B))throw new Error(`camp half totals differ ${e.path}`);
 const row={suite:e.suite,preset:e.preset,file:e.file,path:e.path,sha256:mapSha,width:m.width,height:m.height,pickCount:m.picks,symmetry:g.sym,halfTotals,geometry:{openness:geo.openness,choke:geo.choke,reach_frac:geo.reach_frac,spawn_dist:geo.spawn_dist,detour:geo.detour},teams};
 pool.push(row);seen.set(mapSha,{suite:e.suite,path:e.path});
}
const values=pool.map(x=>({v:(x.teams[0].earlyHarmlessRampGems+x.teams[1].earlyHarmlessRampGems)/2,sha:x.sha256})).sort((a,b)=>a.v-b.v||a.sha.localeCompare(b.sha));
const n=values.length, lowCut=values[Math.ceil(n/3)-1]?.v, highCut=values[Math.ceil(2*n/3)-1]?.v; const tiedAtLow=values.filter(x=>x.v===lowCut).length,tiedAtHigh=values.filter(x=>x.v===highCut).length;
const bandBySha=new Map(values.map((x,i)=>[x.sha,i<Math.ceil(n/3)?'low':i<Math.ceil(2*n/3)?'middle':'high']));
for(const r of pool){const v=(r.teams[0].earlyHarmlessRampGems+r.teams[1].earlyHarmlessRampGems)/2;r.selectionFeatures={meanEarlyHarmlessRampGems:v,rampBand:bandBySha.get(r.sha256)};}
const opens=pool.map(r=>r.geometry.openness).sort((a,b)=>a-b), medianOpen=(opens[(n/2)-1]+opens[n/2])/2;
for(const r of pool)r.selectionFeatures.opennessBand=r.geometry.openness<medianOpen?'below-median':'above-or-equal-median';
const selected=[],exceptions=[];
for(const rampBand of ['low','middle','high'])for(const opennessBand of ['below-median','above-or-equal-median']){
 const cell=pool.filter(r=>r.selectionFeatures.rampBand===rampBand&&r.selectionFeatures.opennessBand===opennessBand);
 let picked=[];
 for(const suite of ['gen','gen-s1']){
  const c=cell.filter(r=>r.suite===suite).sort((a,b)=>a.sha256.localeCompare(b.sha256));
  if(!c.length){exceptions.push({cell:{rampBand,opennessBand},suite,reason:'no_suite_representative'});continue;}
  picked.push(c[0]);
 }
 if(picked.length===2&&picked[0].preset===picked[1].preset){const cand=cell.filter(r=>r.suite===picked[1].suite&&r.preset!==picked[0].preset).sort((a,b)=>a.sha256.localeCompare(b.sha256));if(cand.length)picked[1]=cand[0];}
 for(const r of picked)selected.push({...r,selectedCell:{rampBand,opennessBand}});
}
const blockedAltarCases=selected.filter(r=>r.teams.some(t=>t.nearestTributeTerrainOnly&&!t.nearestTributeWithCampTilesBlocked)).map(r=>({suite:r.suite,file:r.file,sha256:r.sha256}));
const mirrorId=(id,r)=>id.split('|').map(item=>{const [xy,type]=item.split(':');const [x,y]=xy.split(',').map(Number);let mx,my;if(r.symmetry==='horizontal'){mx=r.width-1-x;my=y;}else if(r.symmetry==='vertical'){mx=x;my=r.height-1-y;}else{mx=r.width-1-x;my=r.height-1-y;}return {x:mx,y:my,type};}).sort((a,b)=>a.y-b.y||a.x-b.x||a.type.localeCompare(b.type)).map(c=>`${c.x},${c.y}:${c.type}`).join('|');
const tieAsymmetries=selected.filter(r=>r.teams[0].earlyHarmlessRampGems!==r.teams[1].earlyHarmlessRampGems&&(r.teams[0].nearestThreeBoundaryTie.count>3||r.teams[1].nearestThreeBoundaryTie.count>3)).map(r=>{const a=r.teams[0].nearbyOrdinaryGroups,b=r.teams[1].nearbyOrdinaryGroups,mirroredA=a.map(x=>mirrorId(x.id,r)),bIds=b.map(x=>x.id),mismatches=mirroredA.filter(x=>!bIds.includes(x));return {file:r.file,sha256:r.sha256,teamA:{gems:r.teams[0].earlyHarmlessRampGems,tie:r.teams[0].nearestThreeBoundaryTie},teamB:{gems:r.teams[1].earlyHarmlessRampGems,tie:r.teams[1].nearestThreeBoundaryTie},mirrorCheck:{symmetry:r.symmetry,teamATop3Mirrored:mirroredA,teamBTop3:bIds,mismatches,allMismatchesAtCutoff:mismatches.every(id=>a.find(x=>mirrorId(x.id,r)===id)?.stationDist===r.teams[0].nearestThreeBoundaryTie.distance),tieAssociatedOnly:mismatches.length>0&&mismatches.every(id=>a.find(x=>mirrorId(x.id,r)===id)?.stationDist===r.teams[0].nearestThreeBoundaryTie.distance)&&r.teams[0].nearestThreeBoundaryTie.count>3&&r.teams[1].nearestThreeBoundaryTie.count>3}};});
const output={schema:'generated-three-pick-static-inventory/v2',createdUtc:new Date().toISOString(),source:{indexes:['maps/gen/index.json','maps/gen-s1/index.json'],indexSha256:indexPins,eligibleIndexedEntries:indexEntries.length,uniqueNativeThreePickMaps:pool.length,duplicateHashes,selectionFeatureRules:'mean of A/B reachable harmless-group gems among each side’s three nearest station-reachable ordinary groups; exact equal-count terciles by rank sorted by value then map SHA (ties split by SHA); openness median; no outcomes read',selectionExceptions:exceptions,rampTercileDiagnostics:{mapsPerBand:[56,56,56],lowBoundaryValue:lowCut,lowBoundaryTieCount:tiedAtLow,middleBoundaryValue:highCut,middleBoundaryTieCount:tiedAtHigh,tiesSplitBy:'map SHA ascending within identical ramp values'}},coverage:{selectedMaps:selected.length,selectedMapsWithAnyTerrainOnlyTributeButNoneWhenCampTilesBlocked:blockedAltarCases.length,blockedAltarCases,nearestThreeTieAsymmetries:tieAsymmetries},method:{decoder:'tools/mapgen/wasm.mjs native map decoder plus Grid from tools/mapgen/grid.mjs',walk:'8-neighbour Grid.bfs over ground/bush; camp tiles and enemy spawn blocked; station must be reachable and within Chebyshev range 3 with terrain-visible Bresenham centerline',visionApproximation:'Direct centerline approximation: walls block; bushes block except when source and destination are in the same edge-connected bush cluster; holes do not. This is not engine shadowcasting.',danger:'Any static damaging camp is considered to threaten stations within the rules range by Chebyshev distance; no sleep, action timing, combat, or team control modeled.',reward:'Grid.groups() member reward sums from native camp types; member HP/strength/range from cambc-rules.yaml; only groups without monolith are ordinary; harmless means every member has zero strength.',limitations:['These are public initial-layout opportunities, not captured share, guaranteed solo clears, player decision predictions, or selector thresholds.','Group accessibility requires each member to have at least one legal reachable firing station; conservative safe accessibility further requires all such selected stations outside static damaging-camp range.','Bush/LOS handling is a deterministic geometry approximation, not an invocation of the runtime visibility engine. Selected-map sample had no total terrain-accessible altar cases lost when camps were blocked; this does not establish coverage of blocked altars. Any A/B ramp asymmetry is reported with mirrored nearest-three and cutoff-tie diagnostics.'],rulesSha256:sha(fs.readFileSync(path.join(root,'cambc-rules.yaml')))},eligibleMaps:pool,selectedMaps:selected};
fs.writeFileSync(path.join(here,'RESULT.json'),JSON.stringify(output,null,2)+'\n');
const table=['# Generated three-pick static inventory and outcome-blind sample','','All eligible maps come from pinned `gen` and `gen-s1` indexes, are re-decoded natively as three-pick maps, and are deduplicated by full map bytes. No game outcomes were read. Features describe public initial geometry; they do not predict capture shares, guaranteed clears, or champion decisions. LOS uses a documented deterministic approximation rather than the engine shadowcaster.','',`Eligible index entries: ${indexEntries.length}; unique native three-pick maps: ${pool.length}; duplicate bytes removed: ${duplicateHashes.length}.`,`Selection ramp cutoffs: low ≤ ${lowCut}, middle ≤ ${highCut}, openness median ${medianOpen}.`,`Selection exceptions: ${exceptions.length}; exact ramp bands are 56/56/56. Cutoff values are ${lowCut} and ${highCut}, with ${tiedAtLow} and ${tiedAtHigh} tied maps respectively split by SHA.`,`Selected maps with any altar accessible on terrain-only paths but none with camps blocked: ${blockedAltarCases.length}.`,`Selected nearest-three asymmetries intersecting a cutoff tie: ${tieAsymmetries.length}; mirror comparison is in RESULT.json.`,'','|Cell|Suite|Preset|Map|SHA256|mean harmless gems|open|harmless jobs A/B|conservative gems A/B|','|---|---|---|---|---|---:|---:|---|---|'];
for(const r of selected)table.push(`|${r.selectedCell.rampBand}/${r.selectedCell.opennessBand}|${r.suite}|${r.preset}|${r.file}|${r.sha256}|${r.selectionFeatures.meanEarlyHarmlessRampGems}|${r.geometry.openness}|${r.teams[0].parallelHarmlessJobs}/${r.teams[1].parallelHarmlessJobs}|${r.teams[0].conservativeHarmlessGems}/${r.teams[1].conservativeHarmlessGems}|`);
table.push('','## Limits','', 'Terrain station reach is an 8-neighbour BFS with enemy spawn and camp tiles blocked. Complete Grid groups are considered from each spawn regardless of team label; groups with any monolith are excluded as non-ordinary. Cluster HP is 120 per rules. A group counts as independently accessible only when every member has a reachable range-3 firing station. Conservative harmless supply requires both route and endpoint to avoid tiles within static damaging-camp ranges. This omits camp sleep, combat, shared timing, ally allocation and actual team control. Station visibility is approximate and pinned in `RESULT.json`.','');
fs.writeFileSync(path.join(here,'RESULT.md'),table.join('\n'));
console.log(JSON.stringify({entries:indexEntries.length,unique:pool.length,duplicates:duplicateHashes.length,selected:selected.length,exceptions,lowCut,highCut,medianOpen},null,2));
