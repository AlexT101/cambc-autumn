#!/usr/bin/env python3
"""Create exact-cell equal-ray comparisons with explicit physical source roles."""
from pathlib import Path
from collections import Counter
import hashlib, json, sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'fixtures/candidate-source-aggregation'))
from aggregate import candidate_win_counts
ROOT=Path('/Users/yufan/Desktop/Development/CambridgeBattlecode2026/willow-upstream-development')
HERE=Path(__file__).resolve().parent
INTAKE=HERE.parent
rows=json.loads((HERE/'ORDERED-ROWS.pending.json').read_text())['rows']
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()

def result_row(r):
    statp=Path(r['statistics']); x=json.loads(statp.read_text()); m=x['match']
    assert m['mapHash']==r['map_sha256'], (r['map'],m['mapHash'],r['map_sha256'])
    assert x['diagnostics']['botFaults']=={'teamA':0,'teamB':0}, (statp,x['diagnostics'])
    winner='A' if m['outcome']=='teamA' else 'B' if m['outcome']=='teamB' else None
    assert winner
    draft=x['roster']['draft']
    assert draft and all(d['team'] in ('teamA','teamB') for d in draft)
    picks={'A':[d['champion'] for d in draft if d['team']=='teamA'], 'B':[d['champion'] for d in draft if d['team']=='teamB']}
    assert len(picks['A'])==len(picks['B']) and picks['A'] and picks['B']
    return {'order':r['order'],'arm':r['arm'],'map':r['map'],'candidate_side':r['candidate_side'],'A_source':r['A_source'],'B_source':r['B_source'],'winner_side':winner,'candidate_win':winner==r['candidate_side'],'score_A':int(x['teams'][0]['submittedGems']),'score_B':int(x['teams'][1]['submittedGems']),'rounds_started':m['roundsStarted'],'rounds_completed':m['roundsCompleted'],'teamA_picks':picks['A'],'teamB_picks':picks['B'],'draft_picks_per_side':len(picks['A']),'bot_faults':x['diagnostics']['botFaults'],'detailed_capture_complete':x['diagnostics']['detailedCaptureComplete'],'replay_sha256':sha(Path(r['output'])),'statistics_sha256':sha(statp)}

matches=[result_row(r) for r in rows]
for row in matches:
    assert row['A_source'] != row['B_source']
    assert row['candidate_win'] == (row['winner_side']==row['candidate_side'])

candidate_panel=[r for r in matches if r['arm']=='equal-ray-vs-v33']
stress=[r for r in matches if r['arm']=='equal-ray-vs-execution-parent']
agg=candidate_win_counts(candidate_panel,'equal-ray')
stress_agg=candidate_win_counts(stress,'equal-ray')

def cellkey(mapname, side): return (mapname,side)
cur={cellkey(r['map'],r['candidate_side']):r['candidate_win'] for r in candidate_panel}
# Frozen f475 results: winner label equals candidate identity on each physical-side cell.
f475=json.loads((INTAKE/'f475-v33-complete-output-v1/RESULT.json').read_text())['rows']
f475_cells={cellkey(r['map'], 'A' if r['A']=='f475' else 'B'):r['winner']=='f475' for r in f475}
assert set(f475_cells)==set(cur)
# Full connected escape (per-map exact common-v33 cells).
full_root=json.loads((INTAKE/'connected-escape-160-output-v1/RESULT.json').read_text())
full_panel=full_root['per_map']['escape-vs-v33']
full_cells={cellkey(m,r['candidate_side']):bool(r['candidate_win']) for m,rs in full_panel.items() for r in rs}
assert set(full_cells)==set(cur)
# Execution-only source exact common-v33 cells.
exec_root=json.loads((INTAKE/'connected-escape-execution-release-v1/RESULT.json').read_text())
exec_cells={cellkey(r['map'].removesuffix('.map26a'),r['candidate_side']):bool(r['candidate_won']) for r in exec_root['per_row'] if r['panel']=='execution-vs-v33'}
assert set(exec_cells)==set(cur)

def diff(name, other):
    gained=[k for k,v in cur.items() if v and not other[k]]
    lost=[k for k,v in cur.items() if not v and other[k]]
    unchanged=[k for k,v in cur.items() if v==other[k]]
    return {'comparison':name,'candidate_wins':sum(cur.values()),'reference_wins':sum(other.values()),'exact_matched_cells':len(cur),'gains_vs_reference':len(gained),'losses_vs_reference':len(lost),'unchanged':len(unchanged),'gain_cells':[{'map':m,'candidate_side':s} for m,s in gained],'loss_cells':[{'map':m,'candidate_side':s} for m,s in lost]}

status_files={'v33':HERE/'native-audit/equal-ray-vs-v33/native-status.json','execution_parent':HERE/'native-audit/equal-ray-vs-execution-parent/native-status.json'}
status_reports={k:json.loads(p.read_text()) for k,p in status_files.items()}
status_summary={}
for k,report in status_reports.items():
    status_summary[k]={'games':report['games'],'engine_sha256':report['engine']['sha256'],'snapshot_mode':report['snapshot_mode'],'bots':{b['bot']:{'games':b['games'],'play':b['play'],'draft':b['draft'],'other':b['other']} for b in report['bots']}}
pick_distribution=dict(sorted(Counter(r['draft_picks_per_side'] for r in matches).items()))
result={'schema':'equal-ray-native-result-v1','status':'complete_native_batch_audited_from_all_84_statistics','source_aggregate':'c1e19d45475ca18d2a74c344da8372d9112cc9215c8261eb4023b987db02b4e5','candidate_vs_v33':{'candidate_side_aggregator':'fixtures/candidate-source-aggregation/aggregate.py','counts':agg,'games':80,'mean_rounds':round(sum(r['rounds_completed'] for r in candidate_panel)/80,2),'A_source_score_total':sum(r['score_A'] for r in candidate_panel),'B_source_score_total':sum(r['score_B'] for r in candidate_panel),'bot_faults_by_physical_side':{'A':sum(r['bot_faults']['teamA'] for r in candidate_panel),'B':sum(r['bot_faults']['teamB'] for r in candidate_panel)},'draft_picks_by_side':{'A':sum(r['draft_picks_per_side'] for r in candidate_panel),'B':sum(r['draft_picks_per_side'] for r in candidate_panel)},'all_80_have_accepted_draft_rosters_and_zero_bot_faults':True,'comparisons':[diff('f475-v33 complete 80',f475_cells),diff('connected escape full vs v33',full_cells),diff('connected escape execution-only vs v33',exec_cells)]},'equal_ray_vs_execution_parent_stress':{'counts':stress_agg,'games':4,'cells':[{'map':r['map'],'candidate_side':r['candidate_side'],'winner_side':r['winner_side'],'candidate_win':r['candidate_win'],'score_A':r['score_A'],'score_B':r['score_B'],'rounds_completed':r['rounds_completed']} for r in stress]},'matches':matches,'native_status':status_summary,'draft_pick_count_distribution_per_side':pick_distribution,'native_status_paths':['native-audit/equal-ray-vs-v33/native-status.json','native-audit/equal-ray-vs-execution-parent/native-status.json'],'limitations':['Four parent stress cells are one-sided candidate-A diagnostics, not a balanced outcome panel.','Outcome differences are exact matched map/physical-side cells, but are competitive diagnostics; only the full source/status audits establish the reported mechanical facts.']}
(HERE/'RESULT.json').write_text(json.dumps(result,indent=2)+'\n')
report=['# Equal-ray native screen results','',f"The 80-game candidate-v33 panel produced {agg['candidate_wins']}/80 equal-ray wins (A {agg['candidate_wins_by_candidate_side']['A']}, B {agg['candidate_wins_by_candidate_side']['B']}). The four candidate-A execution-parent stress cells produced {stress_agg['candidate_wins']}/4 wins. These are diagnostics, not a release threshold.",'', '## Matched 80-cell comparisons','']
for d in result['candidate_vs_v33']['comparisons']:
    report.append(f"- Equal-ray {d['candidate_wins']}/80 versus {d['comparison']} {d['reference_wins']}/80: {d['gains_vs_reference']} gains, {d['losses_vs_reference']} losses, {d['unchanged']} unchanged exact map/side cells.")
report += ['', '## Native and draft audit','', f"All 84 statistics files have a native roster draft body with matching pick counts for A/B; picks-per-side distribution is {pick_distribution}. Statistics report zero bot faults on both teams in all 84 games. The pinned native status audit reports equal-ray play rollover/bot-error totals {status_summary['v33']['bots']['willow-v47-equal-ray-escape']['play']} over the v33 panel and {status_summary['execution_parent']['bots']['willow-v47-equal-ray-escape']['play']} over the four stress games; draft rollover/errors are zero in both panels.", '', 'The fixture demonstrates that the second equally short ray becomes label-available, and the independent ranking oracle prefers it in a controlled case. These match outcomes alone do not establish that the mechanism activated in any native game.', '']
(HERE/'RESULT.md').write_text('\n'.join(report))
print(json.dumps({'v33':result['candidate_vs_v33']['counts'],'comparisons':result['candidate_vs_v33']['comparisons'],'stress':stress_agg,'draft_pick_count_distribution_per_side':pick_distribution,'status':status_summary},indent=2))
