#!/usr/bin/env python3
"""Merge the approved 1,024 generated-map cells with the exact 80 published40 reuse cells."""
import csv,json,pathlib,hashlib,collections,importlib.util
base=pathlib.Path(__file__).resolve().parent
root=base.parents[2]
reuse=list(csv.DictReader(open(base/'REUSE-80.tsv'),delimiter='\t'))
new=json.load(open(base/'STATS-RESULT.json'))['games']
spec=importlib.util.spec_from_file_location('aggregate',root/'provenance/khaos-v34-ladder-intake-20261024-v1/fixtures/candidate-source-aggregation/aggregate.py');mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
def native_row(r,st,suite,order):
 out=st['match']['outcome']; win='A' if out=='teamA' else 'B'; cs=r['candidate_physical_side']; picks=collections.Counter(x['team'] for x in st['roster']['draft']); bodies=collections.Counter(x['team'] for x in st['roster']['champions']);
 if len(set(picks.values()))!=1: raise SystemExit(f"uneven picks for {r['map_name']}")
 p=next(iter(picks.values())); sub={x['team']:int(x['submittedGems']) for x in st['teams']}; faults=st['diagnostics']['botFaults']
 if faults['teamA'] or faults['teamB']:raise SystemExit(f"faults {r['statistics_output']}")
 return {'order':order,'suite':suite,'map':r['map_name'],'map_sha256':r['map_sha256'],'candidate_physical_side':cs,'opponent':'f475','A_source':'marcella-hop' if cs=='A' else 'f475','B_source':'f475' if cs=='A' else 'marcella-hop','winner_side':win,'candidate_win':win==cs,'rounds_completed':st['match']['roundsCompleted'],'native_picks_per_side':p,'native_bodies_A':bodies['teamA'],'native_bodies_B':bodies['teamB'],'candidate_submitted_gems':sub['team'+cs],'opponent_submitted_gems':sub['team'+('B' if cs=='A' else 'A')],'bot_faults':faults,'replay':r['replay_output'],'statistics':r['statistics_output']}
full=list(new)
for x in reuse:
 rp=pathlib.Path(x['replay_output']);sp=pathlib.Path(x['statistics_output']);
 if hashlib.sha256(rp.read_bytes()).hexdigest()!=x['replay_sha256'] or hashlib.sha256(sp.read_bytes()).hexdigest()!=x['statistics_sha256']:raise SystemExit('reuse output hash mismatch')
 st=json.load(open(sp));
 if st['match']['mapHash']!=x['map_sha256']:raise SystemExit('reuse map pin mismatch')
 r={'candidate_physical_side':x['candidate_physical_side'],'map_name':x['map_name'],'map_sha256':x['map_sha256'],'replay_output':x['replay_output'],'statistics_output':x['statistics_output']}
 full.append(native_row(r,st,'published40',int(x['original_order'])))
if len(full)!=1104 or len({(x['map_sha256'],x['candidate_physical_side']) for x in full})!=1104:raise SystemExit('expected 1104 unique map/side cells')
for x in full:
 if x['A_source'] not in ('marcella-hop','f475') or x['B_source'] not in ('marcella-hop','f475'):raise SystemExit('source attribution missing')

def summary(xs):
 return {'games':len(xs),'candidate_wins':sum(x['candidate_win'] for x in xs),'candidate_losses':sum(not x['candidate_win'] for x in xs),'candidate_wins_by_candidate_side':{s:sum(x['candidate_win'] for x in xs if x['candidate_physical_side']==s) for s in ['A','B']},'mean_rounds':round(sum(x['rounds_completed'] for x in xs)/len(xs),2) if xs else None,'candidate_submitted_gems':sum(x['candidate_submitted_gems'] for x in xs),'opponent_submitted_gems':sum(x['opponent_submitted_gems'] for x in xs),'bot_faults_A':sum(x['bot_faults']['teamA'] for x in xs),'bot_faults_B':sum(x['bot_faults']['teamB'] for x in xs)}
by_suite=collections.defaultdict(list);by_side=collections.defaultdict(list);by_picks=collections.defaultdict(list)
for x in full:by_suite[x['suite']].append(x);by_side[x['candidate_physical_side']].append(x);by_picks[str(x['native_picks_per_side'])].append(x)
runp=base/'RUN.manifest';rowp=base/'ROWS.tsv'
out={'schema':'marcella-hop-f475-full1104-result/v1','status':'native_stats_complete_native_phase_audit_pending','plan':'PLAN.json','plan_sha256':hashlib.sha256((base/'PLAN.json').read_bytes()).hexdigest(),'run_manifest_sha256':hashlib.sha256(runp.read_bytes()).hexdigest(),'rows_sha256':hashlib.sha256(rowp.read_bytes()).hexdigest(),'reuse_manifest_sha256':hashlib.sha256((base/'REUSE-80.tsv').read_bytes()).hexdigest(),'new_rows':1024,'exact_reused_rows':len(reuse),'full_frame_cells':len(full),'reuse_rows_hash_verified':True,'candidate_source_aggregate_sha256':'709ba31a186fb1e5b27a180ac58d50a913af10cba42ccbc31151ae36c04f26f4','f475_source_aggregate_sha256':'f475b8521cada611754076822402a266c43be8de76ce0f2b504b268ff3335824','source_specific_aggregator':'fixtures/candidate-source-aggregation/aggregate.py','source_aware_total':mod.candidate_win_counts(full,'marcella-hop'),'by_suite':{k:summary(v) for k,v in sorted(by_suite.items())},'by_candidate_physical_side':{k:summary(v) for k,v in sorted(by_side.items())},'by_native_picks_per_side':{k:summary(v) for k,v in sorted(by_picks.items())},'games':sorted(full,key=lambda x:(x['suite'],x['map'],x['candidate_physical_side'])),'native_audit':'native-audit/RESULT.json (pending for 1024 new cells); exact80 reused phase counts are available in marcella-combination-screen-480-v1/NATIVE-PHASE-AUDIT.json group marcella-hop-vs-f475.','limits':['Scores are native submitted gems and round completion from statistics, not a separately derived endgame score.','Generated suites are development maps, not untouched holdout.']}
(base/'FULL-RESULT.json').write_text(json.dumps(out,indent=2)+'\n')
md=['# M+H vs f475, full 1,104-cell frame','', 'The frame combines 1,024 new `gen`/`gen-s1` games with the exact 80 published40 M+H/f475 rows listed in `REUSE-80.tsv`. The two generated suites are development maps, not an untouched holdout. Results below use explicit source identities and the tested source-side aggregator. Scores are submitted gems; they are not a separate game-score measure.','',f"Overall: {out['source_aware_total']['candidate_wins']}/{out['source_aware_total']['candidate_games']} M+H wins.",'','|Suite|Cells|M+H wins|M+H A-side wins|M+H B-side wins|Mean rounds|M+H submitted gems|f475 submitted gems|','|---|---:|---:|---:|---:|---:|---:|---:|']
for k,v in sorted(out['by_suite'].items()):md.append(f"|{k}|{v['games']}|{v['candidate_wins']}|{v['candidate_wins_by_candidate_side']['A']}|{v['candidate_wins_by_candidate_side']['B']}|{v['mean_rounds']}|{v['candidate_submitted_gems']}|{v['opponent_submitted_gems']}|")
md += ['', '|Native picks per side|Cells|M+H wins|M+H A-side wins|M+H B-side wins|Mean rounds|M+H submitted gems|f475 submitted gems|','|---:|---:|---:|---:|---:|---:|---:|---:|']
for k,v in sorted(out['by_native_picks_per_side'].items()):md.append(f"|{k}|{v['games']}|{v['candidate_wins']}|{v['candidate_wins_by_candidate_side']['A']}|{v['candidate_wins_by_candidate_side']['B']}|{v['mean_rounds']}|{v['candidate_submitted_gems']}|{v['opponent_submitted_gems']}|")
md += ['', 'Native phase/error audit is still pending for the 1,024 new cells; see `native-audit/RESULT.json` when complete. Statistics report zero bot faults across these cells.']
(base/'FULL-RESULT.md').write_text('\n'.join(md)+'\n')
print(json.dumps({'total':out['source_aware_total'],'suite':{k:summary(v) for k,v in sorted(by_suite.items())},'picks':{k:summary(v) for k,v in sorted(by_picks.items())}},indent=2))
