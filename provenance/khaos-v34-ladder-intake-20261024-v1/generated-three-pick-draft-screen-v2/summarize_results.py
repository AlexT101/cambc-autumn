#!/usr/bin/env python3
"""Summarize only the approved 192-row fixed-three screen using explicit source labels."""
import csv,json,pathlib,hashlib,collections,ast,importlib.util
base=pathlib.Path(__file__).resolve().parent; root=base.parents[2]
rows=list(csv.DictReader(open(base/'ROWS.tsv'),delimiter='\t')); freeze=json.load(open(base/'MAP-FREEZE.json')); cells={m['file']:m['cell'] for m in freeze['maps']}
spec=importlib.util.spec_from_file_location('aggregate',root/'provenance/khaos-v34-ladder-intake-20261024-v1/fixtures/candidate-source-aggregation/aggregate.py');agg=importlib.util.module_from_spec(spec);spec.loader.exec_module(agg)
labels=[];paths={}
for r in rows:
 for source,path in [(r['A_source'],r['argv_bot_a']),(r['B_source'],r['argv_bot_b'])]:
  if source not in paths:paths[source]=path;labels.append(source)
label_to_i={x:i for i,x in enumerate(labels)};matches=[]; by_arm=collections.defaultdict(list); by_armopp=collections.defaultdict(list); by_map_side=collections.defaultdict(dict); by_stratum_armopp=collections.defaultdict(list)
for i,r in enumerate(rows):
 st=json.load(open(r['statistics_output']));out=st['match']['outcome'];win='A' if out=='teamA' else 'B';cs=r['candidate_physical_side'];arm=r['arm'];cand_team='team'+cs;opp_team='team'+('B' if cs=='A' else 'A')
 picks=collections.Counter(x['team'] for x in st['roster']['draft']);bodies=collections.Counter(x['team'] for x in st['roster']['champions']); submitted={x['team']:int(x['submittedGems']) for x in st['teams']};fault=st['diagnostics']['botFaults']; expected=ast.literal_eval(r['expected_selection_order']); actual=[x['champion'] for x in st['roster']['draft'] if x['team']==cand_team]; actual=[('Cassi-and-Issac' if x=='Cassi & Issac' else x) for x in actual]
 if picks['teamA']!=3 or picks['teamB']!=3:raise SystemExit(f"bad native picks in {r['statistics_output']}: {picks}")
 if bodies[cand_team]!=int(r['expected_body_count']):raise SystemExit(f"candidate body count mismatch arm {arm}: {bodies[cand_team]} expected {r['expected_body_count']}")
 if fault['teamA'] or fault['teamB']:raise SystemExit(f"native bot faults: {r['statistics_output']}")
 candidate_win=win==cs
 if r['A_source']!= (arm if cs=='A' else r['opponent']) or r['B_source']!=(r['opponent'] if cs=='A' else arm):raise SystemExit('source label/side mismatch')
 item={'order':int(r['order']),'selection_cell':cells[r['map_file']],'arm':arm,'opponent':r['opponent'],'map':r['map_file'],'map_sha256':r['map_sha256'],'suite':r['suite'],'candidate_physical_side':cs,'A_source':r['A_source'],'B_source':r['B_source'],'winner_side':win,'candidate_win':candidate_win,'rounds_completed':st['match']['roundsCompleted'],'submitted_gems_A':submitted['teamA'],'submitted_gems_B':submitted['teamB'],'candidate_submitted_gems':submitted[cand_team],'opponent_submitted_gems':submitted[opp_team],'native_picks_A':picks['teamA'],'native_picks_B':picks['teamB'],'native_bodies_A':bodies['teamA'],'native_bodies_B':bodies['teamB'],'candidate_body_count_expected':int(r['expected_body_count']),'candidate_draft_order':actual,'candidate_expected_draft_order':expected,'candidate_draft_order_matches':actual==expected,'bot_faults':fault,'replay':r['replay_output'],'statistics':r['statistics_output']}
 matches.append(item);by_arm[arm].append(item);by_armopp[(arm,r['opponent'])].append(item);by_map_side[(r['map_file'],cs,r['opponent'])][arm]=candidate_win;by_stratum_armopp[(item['selection_cell']['rampBand'],item['selection_cell']['opennessBand'],arm,r['opponent'])].append(item)

def sm(xs):return {'games':len(xs),'candidate_wins':sum(x['candidate_win'] for x in xs),'candidate_losses':sum(not x['candidate_win'] for x in xs),'candidate_wins_by_physical_side':{s:sum(x['candidate_win'] for x in xs if x['candidate_physical_side']==s) for s in ['A','B']},'mean_rounds':round(sum(x['rounds_completed'] for x in xs)/len(xs),2),'candidate_submitted_gems':sum(x['candidate_submitted_gems'] for x in xs),'opponent_submitted_gems':sum(x['opponent_submitted_gems'] for x in xs),'candidate_draft_order_matches':sum(x['candidate_draft_order_matches'] for x in xs),'candidate_draft_order_mismatches':sum(not x['candidate_draft_order_matches'] for x in xs),'native_body_count_distribution':dict(collections.Counter(str(x['candidate_body_count_expected']) for x in xs)),'bot_faults_A':sum(x['bot_faults']['teamA'] for x in xs),'bot_faults_B':sum(x['bot_faults']['teamB'] for x in xs)}
armOrder=['P','S','C','M'];oppOrder=['f475','v33'];winTables={a:{o:sm(by_armopp[a,o]) for o in oppOrder} for a in armOrder};armTotals={a:sm(by_arm[a]) for a in armOrder}
matched={}
for a in ['S','C','M']:
 matched[a]={}
 for o in oppOrder:
  cells=[(k,v) for k,v in by_map_side.items() if k[2]==o and a in v and 'P' in v]
  c=collections.Counter(('both_win' if v['P'] and v[a] else 'both_loss' if not v['P'] and not v[a] else 'P_only' if v['P'] else f'{a}_only') for k,v in cells)
  matched[a][o]={'matched_map_side_cells':len(cells),'outcome_pairs':dict(c)}
# Ordered per-map/side/opponent matrix; useful for source-specific comparisons without pooling.
mapTable=[]
for mapname,side,opp in sorted(by_map_side):
 wins=by_map_side[(mapname,side,opp)];mapTable.append({'map':mapname,'candidate_physical_side':side,'opponent':opp,'winner_by_arm':{a:('candidate' if wins[a] else opp) for a in armOrder}})
# Native auditor accepts exactly two bot entries per batch; prepare one exact-source input per arm/opponent.
auddir=base/'native-audit';(auddir/'inputs').mkdir(parents=True,exist_ok=True)
for arm in armOrder:
 for opp in oppOrder:
  selected=[(r,m) for r,m in zip(rows,matches) if r['arm']==arm and r['opponent']==opp]
  bots=[paths[arm],paths[opp]]; audit={'bots':bots,'scheduled':len(selected),'completed':len(selected),'release':True,'source_pins':{arm:json.load(open(base/'PLAN.json'))['candidate_sources'][arm]['aggregate_sha256'],opp:json.load(open(base/'PLAN.json'))['baseline_sources'][opp]['aggregate_sha256']},'note':'Reconstructed from approved ROWS.tsv and per-game native statistics; exact arm/opponent source pair and physical A/B roles retained.','matches':[]}
  for i,(r,m) in enumerate(selected):audit['matches'].append({'index':i,'order':[0,1] if r['candidate_physical_side']=='A' else [1,0],'replay':r['replay_output'],'map':r['map']})
  dest=auddir/'inputs'/f'{arm}-vs-{opp}';dest.mkdir(parents=True,exist_ok=True);(dest/'results.json').write_text(json.dumps(audit,indent=2)+'\n')
# Preserve the failed first audit invocation: the auditor requires exactly two bot entries per input batch.
(auddir/'ATTEMPT-1.json').write_text(json.dumps({'status':'failed_before_replay_scan','reason':'native auditor requires exactly two bot entries; initial combined input included six source paths','stderr':'native-audit/audit.stderr.log','follow_up':'Split exact source pairs into eight two-bot audit batches; no replay inputs or outputs were changed.'},indent=2)+'\n')
out={'schema':'generated-three-pick-fixed-carry-screen-results/v1','status':'statistics_complete_native_phase_audit_pending','run_manifest_sha256':hashlib.sha256((base/'RUN.manifest').read_bytes()).hexdigest(),'rows_sha256':hashlib.sha256((base/'ROWS.tsv').read_bytes()).hexdigest(),'map_freeze_sha256':hashlib.sha256((base/'MAP-FREEZE.json').read_bytes()).hexdigest(),'source_specific_aggregator':'fixtures/candidate-source-aggregation/aggregate.py','source_aware_totals':{a:agg.candidate_win_counts([x for x in matches if x['arm']==a],a) for a in armOrder},'by_arm':armTotals,'by_arm_and_opponent':winTables,'matched_side_cell_outcomes_P_vs_other_roles':matched,'by_selection_stratum_and_arm_opponent':{f'{k[0]}|{k[1]}|{k[2]}|{k[3]}':sm(v) for k,v in sorted(by_stratum_armopp.items())},'per_map_side_opponent_winner_matrix':mapTable,'native_draft_audit':{'games':len(matches),'native_picks_per_side':dict(collections.Counter(str(x['native_picks_A']) for x in matches)),'candidate_draft_order_matches':sum(x['candidate_draft_order_matches'] for x in matches),'candidate_draft_order_mismatches':sum(not x['candidate_draft_order_matches'] for x in matches),'candidate_body_count_by_arm':{a:dict(collections.Counter(x['native_bodies_A'] if x['candidate_physical_side']=='A' else x['native_bodies_B'] for x in matches if x['arm']==a)) for a in armOrder},'faults':sum(x['bot_faults']['teamA']+x['bot_faults']['teamB'] for x in matches)},'games':matches,'native_audit_inputs':'native-audit/inputs/{P,S,C,M}-vs-{f475,v33}/results.json','limits':['This is a fixed first-slot screen on 12 outcome-blind selected generated development maps, not an untouched holdout.','No outcome-based selector or threshold was derived.','Control roles are exact f475/v33 as pinned in the plan.']}
(base/'RESULT.json').write_text(json.dumps(out,indent=2)+'\n')
md=['# Fixed-three native screen results','',f"All 192 approved cells completed with normal native drafts. This fixed first-slot screen compares four candidates on 12 outcome-blind selected generated development maps against frozen f475 and v33 controls. These are development maps, not untouched holdout. Aggregation uses the explicit source identities in `ROWS.tsv`; controls are reported separately.",'','|Arm|Opponent|Games|Wins|A candidate-side wins|B candidate-side wins|Mean rounds|Candidate submitted gems|Control submitted gems|Draft order matches|Faults|','|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|']
for a in armOrder:
 for o in oppOrder:
  x=winTables[a][o];md.append(f"|{a}|{o}|{x['games']}|{x['candidate_wins']}|{x['candidate_wins_by_physical_side']['A']}|{x['candidate_wins_by_physical_side']['B']}|{x['mean_rounds']}|{x['candidate_submitted_gems']}|{x['opponent_submitted_gems']}|{x['candidate_draft_order_matches']}/{x['games']}|{x['bot_faults_A']+x['bot_faults_B']}|")
md+=['','## Matched P versus other-role cells','', '|Compared arm|Opponent|Matched map/side cells|Both win|Both lose|P only|Other arm only|','|---|---|---:|---:|---:|---:|---:|']
for a in ['S','C','M']:
 for o in oppOrder:
  x=matched[a][o]['outcome_pairs'];md.append(f"|P vs {a}|{o}|{matched[a][o]['matched_map_side_cells']}|{x.get('both_win',0)}|{x.get('both_loss',0)}|{x.get('P_only',0)}|{x.get(a+'_only',0)}|")
md+=['','## Outcome-blind sample strata','', '|Ramp band|Openness band|Arm|Opponent|Cells|Wins|A-side wins|B-side wins|','|---|---|---|---|---:|---:|---:|---:|']
for (rb,ob,a,o),xs in sorted(by_stratum_armopp.items()):
 q=sm(xs);md.append(f"|{rb}|{ob}|{a}|{o}|{q['games']}|{q['candidate_wins']}|{q['candidate_wins_by_physical_side']['A']}|{q['candidate_wins_by_physical_side']['B']}|")
md+=['','The per-map × candidate-side × opponent × arm outcomes and native draft/body facts are in `RESULT.json`. A separate native replay phase audit is pending; no selector threshold was derived from this screen.']
(base/'RESULT.md').write_text('\n'.join(md)+'\n')
print(json.dumps({'by_arm_and_opponent':winTables,'matched':matched},indent=2))
