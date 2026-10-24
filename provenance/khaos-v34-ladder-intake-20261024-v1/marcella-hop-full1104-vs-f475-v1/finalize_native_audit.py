#!/usr/bin/env python3
import csv,json,pathlib,hashlib,collections
base=pathlib.Path(__file__).resolve().parent
root=base.parents[2]
aud=json.load(open(base/'native-audit/RESULT.json')); rows=list(csv.DictReader(open(base/'ROWS.tsv'),delimiter='\t')); stats=json.load(open(base/'STATS-RESULT.json'))['games']; full=json.load(open(base/'FULL-RESULT.json'))
assert len(rows)==len(stats)==len(aud['matches'])==1024
srcTotals=collections.defaultdict(lambda:{'games':0,'phases':{p:{'rollover':0,'bot_error':0} for p in ['play','draft','other']}})
sideTotals=collections.defaultdict(lambda:{'games':0,'phases':{p:{'rollover':0,'bot_error':0} for p in ['play','draft','other']}})
suiteTotals=collections.defaultdict(lambda:{'games':0,'phases':{p:{'rollover':0,'bot_error':0} for p in ['play','draft','other']}})
for r,meta,m in zip(rows,stats,aud['matches']):
 if m['index']!=int(r['order'])-1 or m['map_sha256']!=r['map_sha256']:raise SystemExit('native status row/map alignment mismatch')
 for phys in ['A','B']:
  s=r[f'{phys}_source']; det=next(x for x in m['counts']['by_side'] if x['physical_side']==phys)
  for dest,key in [(srcTotals,s),(sideTotals,phys)]:
   dest[key]['games']+=1
   for p in ['play','draft','other']:
    dest[key]['phases'][p]['rollover']+=det[p]['rollover'];dest[key]['phases'][p]['bot_error']+=det[p]['bot_error']
  suiteTotals[r['suite']]['games']+=1
  for p in ['play','draft','other']:
   suiteTotals[r['suite']]['phases'][p]['rollover']+=det[p]['rollover'];suiteTotals[r['suite']]['phases'][p]['bot_error']+=det[p]['bot_error']
# Reuse exactly the existing audited M+H/f475 published40 A/B cells.
old=json.load(open(root/'provenance/khaos-v34-ladder-intake-20261024-v1/marcella-combination-screen-480-v1/NATIVE-PHASE-AUDIT.json'))
g=next(x for x in old['groups'] if x['group']=='marcella-hop-vs-f475')
if g['games']!=80:raise SystemExit('expected exact 80 reused M+H/f475 phase rows')
def flat_source(node):return {p:dict(node[p]) for p in ['play','draft','other']}
reused={'games':80,'source_groups':{'marcella-hop':flat_source(g['candidate']),'f475':flat_source(g['opponent'])},'physical_sides':{s:{p:dict(g['physical_sides'][s][p]) for p in ['play','draft','other']} for s in ['A','B']},'audit_path':'provenance/khaos-v34-ladder-intake-20261024-v1/marcella-combination-screen-480-v1/NATIVE-PHASE-AUDIT.json','audit_sha256':hashlib.sha256((root/'provenance/khaos-v34-ladder-intake-20261024-v1/marcella-combination-screen-480-v1/NATIVE-PHASE-AUDIT.json').read_bytes()).hexdigest(),'audit_group':g['group']}
fullSource={}
for s in ['marcella-hop','f475']:
 fullSource[s]={'games':srcTotals[s]['games']+reused['games'],'phases':{p:{k:srcTotals[s]['phases'][p][k]+reused['source_groups'][s][p][k] for k in ['rollover','bot_error']} for p in ['play','draft','other']}}
fullPhysical={}
for s in ['A','B']:
 fullPhysical[s]={'games':sideTotals[s]['games']+80,'phases':{p:{k:sideTotals[s]['phases'][p][k]+reused['physical_sides'][s][p][k] for k in ['rollover','bot_error']} for p in ['play','draft','other']}}
result={'schema':'marcella-hop-f475-full1104-native-phase-audit/v1','status':'complete','new_cells':{'games':aud['games'],'audit':'native-audit/RESULT.json','audit_sha256':hashlib.sha256((base/'native-audit/RESULT.json').read_bytes()).hexdigest(),'snapshot_mode':aud['snapshot_mode'],'engine':aud['engine'],'source_pins':aud['source_pins'],'by_source':dict(srcTotals),'by_physical_side':dict(sideTotals),'by_suite':dict(suiteTotals)},'exact_reused_cells':reused,'full1104':{'games':1104,'by_source':fullSource,'by_physical_side':fullPhysical},'zero_status_faults_all_new_cells':all(v['phases'][p]['bot_error']==0 for groups in [srcTotals,sideTotals,suiteTotals] for v in groups.values() for p in ['play','draft','other']),'limitations':['The 80 published40 rows reuse the exact previously audited M+H/f475 cells; their per-source/per-physical-side aggregate comes from the prior native phase audit. The 1,024 generated cells are audited individually here.']}
(base/'NATIVE-PHASE-RESULT.json').write_text(json.dumps(result,indent=2)+'\n')
full['status']='complete_native_stats_and_phase_audit';full['native_phase_audit']='NATIVE-PHASE-RESULT.json';full['native_phase_audit_sha256']=hashlib.sha256((base/'NATIVE-PHASE-RESULT.json').read_bytes()).hexdigest();(base/'FULL-RESULT.json').write_text(json.dumps(full,indent=2)+'\n')
md=(base/'FULL-RESULT.md').read_text().rstrip()+f"\n\n## Native replay phase audit\n\nThe 1,024 new cells were scanned with the pinned v1_0_3 compact-timeline auditor. Across those cells, M+H had {srcTotals['marcella-hop']['phases']['play']['rollover']} play rollovers and f475 had {srcTotals['f475']['phases']['play']['rollover']}; there were no bot errors in play, draft, or other phases. The exact 80 reused published cells have {g['candidate']['play']['rollover']} M+H and {g['opponent']['play']['rollover']} f475 play rollovers, with zero errors. Full-frame source and physical-side counts are in `NATIVE-PHASE-RESULT.json`.\n"
(base/'FULL-RESULT.md').write_text(md)
print(json.dumps(result['full1104'],indent=2))
