#!/usr/bin/env python3
"""Summarize the pinned M+H full1104 extension from native statistics and approved ROWS.tsv."""
import csv,json,pathlib,collections,hashlib,importlib.util
here=pathlib.Path(__file__).resolve().parent
base=here.parent
rows=list(csv.DictReader(open(base/'ROWS.tsv'),delimiter='\t'))
spec=importlib.util.spec_from_file_location('aggregate',base.parent/'fixtures/candidate-source-aggregation/aggregate.py');mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
by_suite=collections.defaultdict(list);by_side=collections.defaultdict(list);by_picks=collections.defaultdict(list);matches=[]
for row in rows:
 st=json.load(open(row['statistics_output']));outcome=st['match']['outcome'];win='A' if outcome=='teamA' else 'B'
 cand_side=row['candidate_physical_side']; candwin=win==cand_side
 draft=st['roster']['draft']; teams=collections.Counter(x['team'] for x in draft)
 if len(set(teams.values()))!=1: raise SystemExit(f"uneven draft picks: {row['map_name']} {teams}")
 picks=next(iter(teams.values()))
 bodies=collections.Counter(x['team'] for x in st['roster']['champions'])
 fault=st['diagnostics']['botFaults']
 if fault['teamA'] or fault['teamB']: raise SystemExit(f"native bot fault: {row['replay_output']}")
 submitted={x['team']:int(x['submittedGems']) for x in st['teams']}
 o={'order':int(row['order']),'suite':row['suite'],'map':row['map_name'],'map_sha256':row['map_sha256'],'candidate_physical_side':cand_side,'opponent':'f475','A_source':row['A_source'],'B_source':row['B_source'],'winner_side':win,'candidate_win':candwin,'rounds_completed':st['match']['roundsCompleted'],'native_picks_per_side':picks,'native_bodies_A':bodies['teamA'],'native_bodies_B':bodies['teamB'],'submitted_gems_A':submitted['teamA'],'submitted_gems_B':submitted['teamB'],'candidate_submitted_gems':submitted['team'+cand_side],'opponent_submitted_gems':submitted['team'+('B' if cand_side=='A' else 'A')],'bot_faults':fault,'replay':row['replay_output'],'statistics':row['statistics_output']}
 matches.append(o);by_suite[row['suite']].append(o);by_side[cand_side].append(o);by_picks[str(picks)].append(o)
# Tested source-aware aggregation logic, using explicit identities from the approved rows.
agg=mod.candidate_win_counts(matches,'marcella-hop')
def summary(xs):
 return {'games':len(xs),'candidate_wins':sum(x['candidate_win'] for x in xs),'candidate_losses':sum(not x['candidate_win'] for x in xs),'candidate_wins_by_candidate_side':{s:sum(x['candidate_win'] for x in xs if x['candidate_physical_side']==s) for s in ['A','B']},'mean_rounds':round(sum(x['rounds_completed'] for x in xs)/len(xs),2) if xs else None,'candidate_submitted_gems':sum(x['candidate_submitted_gems'] for x in xs),'opponent_submitted_gems':sum(x['opponent_submitted_gems'] for x in xs),'bot_faults_A':sum(x['bot_faults']['teamA'] for x in xs),'bot_faults_B':sum(x['bot_faults']['teamB'] for x in xs)}
out={'schema':'marcella-hop-full1104-stats-result/v1','status':'native_statistics_summarized_native_status_audit_pending','run_manifest_sha256':hashlib.sha256((base/'RUN.manifest').read_bytes()).hexdigest(),'rows_sha256':hashlib.sha256((base/'ROWS.tsv').read_bytes()).hexdigest(),'candidate_source_aggregate_sha256':'709ba31a186fb1e5b27a180ac58d50a913af10cba42ccbc31151ae36c04f26f4','f475_source_aggregate_sha256':'f475b8521cada611754076822402a266c43be8de76ce0f2b504b268ff3335824','source_specific_aggregator':'fixtures/candidate-source-aggregation/aggregate.py','source_aware_total':agg,'by_suite':{k:summary(v) for k,v in sorted(by_suite.items())},'by_candidate_physical_side':{k:summary(v) for k,v in sorted(by_side.items())},'by_native_picks_per_side':{k:summary(v) for k,v in sorted(by_picks.items())},'games':matches,'limits':['Score fields are native submitted gems and round completion from statistics; not a separately derived endgame scoring metric.','Native play/draft rollover and error phase audit is pending in native-audit/RESULT.json.']}
(base/'STATS-RESULT.json').write_text(json.dumps(out,indent=2)+'\n')
print(json.dumps({'rows':len(matches),'total':agg,'picks':{k:summary(v) for k,v in sorted(by_picks.items())}},indent=2))
