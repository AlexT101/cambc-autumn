#!/usr/bin/env python3
"""Bounded first-100 macro chronology for six predeclared C/M vs v33 A-side replays."""
import gzip, hashlib, json
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
BASE = Path(__file__).resolve().parent
EXTRACTED = BASE / 'extracted'
PANEL = ROOT / 'provenance/khaos-v34-ladder-intake-20261024-v1/generated-three-pick-draft-screen-v2'
TARGETS = {
 ('C','rows'): 'C-gen-gen-rows-102301101-vs-v33-candidate-A',
 ('M','rows'): 'M-gen-gen-rows-102301101-vs-v33-candidate-A',
 ('C','star'): 'C-gen-gen-star-102305406-vs-v33-candidate-A',
 ('M','star'): 'M-gen-gen-star-102305406-vs-v33-candidate-A',
 ('C','classic'): 'C-gen-s1-gen-classic-102400016-vs-v33-candidate-A',
 ('M','classic'): 'M-gen-s1-gen-classic-102400016-vs-v33-candidate-A',
}

def sha(path):
 h=hashlib.sha256()
 with open(path,'rb') as f:
  for b in iter(lambda:f.read(1<<20),b''): h.update(b)
 return h.hexdigest()

def load(path): return json.loads(path.read_text())
def group_info(mp):
 camps={c['id']:c for c in mp['camps']}
 groups={g['id']:g for g in mp['groups']}
 def desc(gid):
  g=groups.get(gid,{})
  return {'id':gid,'types':g.get('types',[]),'gems':g.get('gems'),'gold':g.get('gold'),'side':g.get('side'),'tiles':g.get('tiles',[])}
 return camps,groups,desc

def run(base):
 d=next(p for p in EXTRACTED.iterdir() if p.is_dir() and (p/'meta.json').is_file() and (load(p/'meta.json').get('map',{}).get('name')==base))
 meta=load(d/'meta.json'); mp=load(EXTRACTED/'maps'/f"{meta['map']['hash']}.json")
 rounds=load_gz(d/'rounds.json.gz')
 events=[json.loads(l) for l in gzip.open(d/'events.jsonl.gz','rt')]
 champs={c['id']:c for c in meta['champions']}; byteam={t:[c for c in meta['champions'] if c['team']==t] for t in (0,1)}
 camps,groups,desc=group_info(mp)
 teamnames={0:'candidate A',1:'v33 B'}
 def nm(cid): return champs.get(cid,{}).get('name',str(cid))
 def tn(t): return teamnames.get(t,str(t))
 def group_label(gid):
  x=desc(gid); return f"g{gid} {','.join(sorted(set(x['types'])))} {x['gems']}g/{x['gold']}gold side={x['side']}"
 def group_for_camp(camp): return camps.get(camp,{}).get('group')
 def summarize_item_event(e):
  parts=[]
  for name,count in (e.get('items') or {}).items():
   if count: parts.append(f'{name}×{count}')
  for name,count in (e.get('cons') or {}).items():
   if count: parts.append(f'{name}×{count}')
  return ', '.join(parts) or 'unlisted item/consumable'
 # Convert arrays by champion / round index.
 r_index={r:i for i,r in enumerate(rounds['round'])}
 def at(t,r,key):
  i=r_index.get(r)
  if i is None:return None
  return rounds['champions'][next(j for j,c in enumerate(rounds['champions']) if c['id']==t)][key][i]
 # grouped first100 actions
 by_team_groups=defaultdict(lambda:defaultdict(float))
 round_team_groups=defaultdict(set)
 round_actor_groups=defaultdict(lambda:defaultdict(set))
 first_by_actor={}
 group_damage_events=[]
 for e in events:
  if e['r']>100: continue
  if e['k'] in ('attack','cast') and e.get('cdmg'):
   actor=e['a']; team=champs[actor]['team']
   local=defaultdict(float)
   for camp,amt in e['cdmg']:
    gid=group_for_camp(camp)
    if gid is not None and amt>0:
     local[gid]+=amt; by_team_groups[team][gid]+=amt; round_team_groups[(team,e['r'])].add(gid); round_actor_groups[(team,e['r'])][actor].add(gid); first_by_actor.setdefault(actor,{'round':e['r'],'group':gid,'camp':camp,'damage':round(amt,1),'action':e['k']})
   if local:
    group_damage_events.append({'round':e['r'],'team':team,'actor':nm(actor),'groups':{str(g):round(v,1) for g,v in local.items()}})
 # actions first camp work by team; group clear and capture
 first_work={}
 for e in events:
  if e['r']<=100 and e['k'] in ('attack','cast') and e.get('cdmg'):
   for camp,amt in e['cdmg']:
    if amt>0:
     t=champs[e['a']]['team']; first_work.setdefault(t,{'round':e['r'],'actor':nm(e['a']),'group':group_for_camp(camp),'camp':camp,'damage':round(amt,1),'action':e['k']})
     break
 clears=[{'round':e['r'],'team':champs[e['by']]['team'] if e.get('by') in champs else None,'actor':nm(e['by']) if e.get('by') in champs else None,'group':e['g'],'descriptor':group_label(e['g'])} for e in events if e['r']<=100 and e['k']=='group_clear']
 captures=[]
 for e in events:
  if e['r']<=100 and e['k']=='capture':
   captures.append({'round':e['r'],'team':e['team'],'group':e['g'],'descriptor':group_label(e['g']),'shares':[{'champion':nm(x[0]),'gems':x[1],'gold':x[2]} for x in e.get('shares',[])]})
 tributes=[]
 for e in events:
  if e['r']<=100 and e['k'] in ('tribute_start','tribute_end'):
   tributes.append({'round':e['r'],'event':e['k'],'team':champs[e['a']]['team'],'actor':nm(e['a']),'gems':e.get('gems'),'team_total':e.get('total'),'altar':e.get('altar'),'earned_gold':e.get('earnedGold')})
 deaths=[]
 for e in events:
  if e['r']<=100 and e['k']=='death':
   deaths.append({'round':e['r'],'victim':nm(e['v']),'team':champs[e['v']]['team'],'at':e.get('at'),'cause':e.get('cause'),'by':nm(e['by']) if e.get('by') in champs else None,'camp':e.get('camp'),'lost_gems':e.get('gems'),'killer_gems':e.get('gemsTo'),'linked_to':nm(e['linked']) if e.get('linked') in champs else None})
 purchases=[]
 for e in events:
  if e['r']<=100 and e['k'] in ('shop','sell','consumable'):
   purchases.append({'round':e['r'],'team':champs[e['a']]['team'],'actor':nm(e['a']),'event':e['k'],'gold_change':e.get('gold'),'items':e.get('items'),'consumables':e.get('cons')})
 first_purchase={}
 for e in purchases:
  if e['event']=='shop' and e.get('items'):
   first_purchase.setdefault(e['team'],e)
 # first same-round distinct groups attacked by multiple work streams
 parallel=[]
 for (t,r),gs in sorted(round_team_groups.items(),key=lambda x:x[0][1]):
  if len(gs)>1:
   parallel.append({'round':r,'team':t,'groups':[group_label(g) for g in sorted(gs)]})
 checkpoints={}
 for r in (25,50,100):
  gi=r_index.get(r)
  if gi is None: continue
  teams=[]
  for t in (0,1):
   crows=[c for c in rounds['champions'] if c['team']==t]
   bag=sum((c['gems'][gi] or 0) for c in crows)
   details=[]
   for c in crows:
    inv=[]; items=c['items'][gi] or []
    for j in range(0,len(items),2):
     idx,count=items[j:j+2]
     if count: inv.append({'name':load(EXTRACTED/'enums.json')['items'][idx],'count':count})
    details.append({'champion':nm(c['id']),'gold':c['gold'][gi],'earned':c['earned'][gi],'carried_gems':c['gems'][gi],'alive':c['alive'][gi],'items':inv})
   teams.append({'team':t,'name':tn(t),'submitted_gems':rounds['gems'][t][gi],'carried_gems':bag,'banked_gold':sum(c['gold'][gi] or 0 for c in crows),'earned_gold_lifetime':sum(c['earned'][gi] or 0 for c in crows),'champions':details})
  checkpoints[str(r)]=teams
 # multi-body work on distinct groups in the same round
 parallel_actor=[]
 for (t,r), actors in sorted(round_actor_groups.items(),key=lambda z:(z[0][1],z[0][0])):
  gids=set.union(*actors.values()) if actors else set()
  if t==0 and len(actors)>1 and len(gids)>1:
   parallel_actor.append({'round':r,'team':t,'actors':[{'champion':nm(cid),'groups':[group_label(g) for g in sorted(gs)]} for cid,gs in sorted(actors.items())]})
 # native phase metadata / provenance
 replay=ROOT/meta['source']; input_path=ROOT/replay
 return {
  'identity':{'label':base,'arm':base[0],'map':meta['map'],'source':meta['source'],'replay_sha256':sha(input_path),'decoded_sha256':meta['sha256'],'decoder_engine':meta['engine'],'validation':meta['validation'],'rounds_total':meta['result']['rounds'],'winner_team':meta['result']['winner'],'final_submitted_gems':meta['result']['gems'],'candidate_team':0,'opponent_team':1,'candidate_roster':[c['name'] for c in byteam[0]],'opponent_roster':[c['name'] for c in byteam[1]]},
  'first100':{'first_productive_work':{tn(t):dict(v,descriptor=group_label(v['group'])) for t,v in first_work.items()},'group_clears':clears,'captures':captures,'tributes':tributes,'purchases':purchases,'first_shop_purchase_by_team':{tn(t):e for t,e in first_purchase.items()},'deaths':deaths,'same_round_multi_group_damage':parallel,'multi_actor_distinct_group_work':parallel_actor,'first_camp_work_by_actor':{nm(cid):dict(v,descriptor=group_label(v['group'])) for cid,v in first_by_actor.items() if champs[cid]['team']==0},'damage_by_team_group':{tn(t):[{**desc(g),'damage':round(d,1)} for g,d in sorted(vals.items())] for t,vals in by_team_groups.items()},'checkpoints':checkpoints}
 }

def load_gz(path):
 with gzip.open(path,'rt') as f:return json.load(f)

results=[run(name) for name in TARGETS.values()]
# stable index of status by arm/map
out={'schema':'willow-first100-macro-v1','scope':'six predeclared candidate-A vs v33 rows only; rounds 1-100; objective replay chronology, not own-view or hidden decision attribution','source_analysis':'tools/replay/extract.mjs and tools/replay/README.md; pinned v1_0_3 engine in each meta.json','files':results,'limits':['Replay events are engine-observed omniscient chronology; they do not establish what an actor knew or why it chose an action.','No own-view window, decision attribution, counterfactual, or gameplay change is included.','Soft derived event discrepancies are reported verbatim in per-file validation; engine final stats remain authoritative.']}
(BASE/'RESULT.json').write_text(json.dumps(out,indent=2)+'\n')
# readable compact output
tn=lambda t: {0:'candidate A',1:'v33 B'}.get(t,str(t))
lines=['# First-100 macro readouts: candidate A vs v33','', 'Six existing, predeclared rows from the v2 three-pick screen. Rows 1–100 only. This is an omniscient replay chronology and native-event audit, not actor-knowledge or decision attribution. No own-view export or new game was used.','']
for f in results:
 i=f['identity']; a=f['first100']; lines += [f"## {i['label']}", '', f"Outcome: candidate A {'won' if i['winner_team']==0 else 'lost'}; {i['final_submitted_gems'][0]}–{i['final_submitted_gems'][1]} at round {i['rounds_total']}. Map hash {i['map']['hash']}; replay SHA-256 `{i['replay_sha256']}`; decoded event source SHA-256 `{i['decoded_sha256']}`. Draft A: {', '.join(i['candidate_roster'])}; B: {', '.join(i['opponent_roster'])}.", f"Validation: hard {len(i['validation']['hard'])}, soft {len(i['validation']['soft'])}." ]
 if i['validation']['soft']: lines += [f"Soft differences: {'; '.join(i['validation']['soft'])}."]
 for t, w in a['first_productive_work'].items(): lines.append(f"First productive work, {t}: r{w['round']} {w['actor']} attacks {w['descriptor']} ({w['damage']} damage).")
 # Concise event order: first capture per team, first completed tribute per team, then checkpoint snapshots.
 for t in (0,1):
  c=next((x for x in a['captures'] if x['team']==t),None)
  if c:
   shares=', '.join('{} {} gems/{} gold'.format(s['champion'],s['gems'],s['gold']) for s in c['shares']) or 'none'
   lines.append(f"First capture, {tn(t)}: r{c['round']} {c['descriptor']}; reward share {shares}.")
  tr=next((x for x in a['tributes'] if x['team']==t and x['event']=='tribute_end'),None)
  if tr: lines.append(f"First completed tribute, {tn(t)}: r{tr['round']} {tr['actor']} submits {tr['gems']} gems (team total {tr['team_total']}).")
 if not a['captures']: lines.append('No capture through r100.')
 for t,e in a['first_shop_purchase_by_team'].items(): lines.append(f"First shop purchase, {t}: r{e['round']} {e['actor']} {e['items']} (gold change {e['gold_change']}).")
 if not a['first_shop_purchase_by_team']: lines.append('No item shop purchase by either team through r100.')
 for r,teams in a['checkpoints'].items():
  lines.append(f"At r{r}: "+' | '.join(f"{x['name']} submitted={x['submitted_gems']} carried={x['carried_gems']} banked={x['banked_gold']} earned={x['earned_gold_lifetime']}" for x in teams)+'.')
 lines.append('First candidate work by body: '+('; '.join(f"{c}: r{v['round']} group g{v['group']}" for c,v in a['first_camp_work_by_actor'].items()) or 'none')+'.')
 lines.append('Candidate multi-body distinct-group work: '+('; '.join(f"r{x['round']} "+'; '.join(f"{y['champion']}→{','.join(g.split(' ',1)[0] for g in y['groups'])}" for y in x['actors']) for x in a['multi_actor_distinct_group_work'][:6]) or 'none')+'.')
 lines.append('First-100 deaths: '+('; '.join(f"r{x['round']} {x['victim']} ({'linked to '+x['linked_to'] if x['linked_to'] else 'camp '+str(x['camp']) if x['camp'] is not None else 'by '+str(x['by'])}) lost {x['lost_gems']}" for x in a['deaths']) or 'none')+'.')
 lines.append('')
lines += ['## Limits','',*['- '+x for x in out['limits']],'']
(BASE/'RESULT.md').write_text('\n'.join(lines))
print(f"wrote {BASE/'RESULT.md'} and RESULT.json for {len(results)} exact rows")
