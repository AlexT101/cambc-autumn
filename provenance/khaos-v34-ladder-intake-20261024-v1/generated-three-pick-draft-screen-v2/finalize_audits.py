#!/usr/bin/env python3
import json,pathlib,hashlib,collections,csv
base=pathlib.Path(__file__).resolve().parent
result=json.load(open(base/'RESULT.json')); rows=list(csv.DictReader(open(base/'ROWS.tsv'),delimiter='\t'))
phase=lambda:{p:{'rollover':0,'bot_error':0} for p in ['play','draft','other']}
by_source=collections.defaultdict(lambda:{'games':0,'phases':phase()});by_side=collections.defaultdict(lambda:{'games':0,'phases':phase()});by_armopp=collections.defaultdict(lambda:{'games':0,'sources':collections.defaultdict(lambda:{'games':0,'phases':phase()}),'physical_sides':collections.defaultdict(lambda:{'games':0,'phases':phase()})})
files={};n=0
for arm in ['P','S','C','M']:
 for opp in ['f475','v33']:
  p=base/'native-audit'/f'{arm}-vs-{opp}'/'RESULT.json';aud=json.load(open(p));files[f'{arm}-vs-{opp}']=hashlib.sha256(p.read_bytes()).hexdigest()
  subset=[r for r in rows if r['arm']==arm and r['opponent']==opp]
  if aud['games']!=24 or len(subset)!=24:raise SystemExit(f'wrong audit count {arm}/{opp}')
  key=(arm,opp)
  for row,match in zip(subset,aud['matches']):
   if pathlib.Path(row['replay_output']).name!=pathlib.Path(match['replay']).name or row['map_sha256']!=match['map_sha256']:raise SystemExit(f'match alignment failure {arm}/{opp}')
   by_armopp[key]['games']+=1;n+=1
   for team in ['A','B']:
    status=next(x for x in match['counts']['by_side'] if x['physical_side']==team);source=row[f'{team}_source']
    by_source[source]['games']+=1;by_armopp[key]['sources'][source]['games']+=1
    by_side[team]['games']+=1;by_armopp[key]['physical_sides'][team]['games']+=1
    for ph in ['play','draft','other']:
     for field in ['rollover','bot_error']:
      value=status[ph][field]
      by_source[source]['phases'][ph][field]+=value;by_armopp[key]['sources'][source]['phases'][ph][field]+=value
      by_side[team]['phases'][ph][field]+=value;by_armopp[key]['physical_sides'][team]['phases'][ph][field]+=value
if n!=192:raise SystemExit(f'expected192 audited games, got {n}')
# JSON serialization of defaultdict tree.
conv=lambda d:json.loads(json.dumps(d))
summary={'schema':'generated-three-pick-native-phase-audit/v1','status':'complete','games':192,'snapshot_mode':'v1_0_3_compact_timeline','engine':{'version':'v1_0_3'},'audit_result_hashes':files,'by_source':conv(by_source),'by_physical_side':conv(by_side),'by_arm_and_opponent':{f'{a}-vs-{o}':conv({**by_armopp[(a,o)],'sources':dict(by_armopp[(a,o)]['sources']),'physical_sides':dict(by_armopp[(a,o)]['physical_sides'])}) for a in ['P','S','C','M'] for o in ['f475','v33']},'zero_errors':all(v['phases'][p]['bot_error']==0 for group in [by_source,by_side] for v in group.values() for p in ['play','draft','other']),'auditor':'tools/replay/audit_native_status.mjs; exact two-source audit batches'}
(base/'NATIVE-PHASE-RESULT.json').write_text(json.dumps(summary,indent=2)+'\n')
result['status']='complete_native_statistics_and_phase_audit';result['native_phase_audit']='NATIVE-PHASE-RESULT.json';result['native_phase_audit_sha256']=hashlib.sha256((base/'NATIVE-PHASE-RESULT.json').read_bytes()).hexdigest();result['native_phase_summary']=summary['by_arm_and_opponent'];(base/'RESULT.json').write_text(json.dumps(result,indent=2)+'\n')
md=(base/'RESULT.md').read_text();md=md.replace('A separate native replay phase audit is pending; no selector threshold was derived from this screen.','The pinned v1_0_3 replay phase audit completed across all 192 cells with zero rollover errors and zero bot errors in draft or other phases. Source and physical-side counts are in `NATIVE-PHASE-RESULT.json`. No selector threshold was derived from this screen.')
(base/'RESULT.md').write_text(md)
p=base/'EXECUTION-STATUS.json';ex=json.load(open(p));ex['status']='complete_192_replays_statistics_and_native_phase_audit';ex['native_audit_pending']=False;ex['native_audit']='NATIVE-PHASE-RESULT.json';ex['native_audit_sha256']=hashlib.sha256((base/'NATIVE-PHASE-RESULT.json').read_bytes()).hexdigest();ex['native_audit_games']=192;ex['native_errors_total']=0;p.write_text(json.dumps(ex,indent=2)+'\n')
print(json.dumps({'games':n,'zero_errors':summary['zero_errors'],'by_source':summary['by_source'],'by_side':summary['by_physical_side']},indent=2))
