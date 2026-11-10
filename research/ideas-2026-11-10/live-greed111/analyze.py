"""Completed v111 only: cached live pairs, no API calls/downloads/game creation."""
import collections
import hashlib
import json
import math
from pathlib import Path
import sys
import zipfile

R=Path('/home/ubuntu/cambc-autumn')
D=Path('/home/ubuntu/tmp-offload/handoff/codex/live-analysis/greed111')
sys.path.insert(0,str(R/'tools'))
import ladder_scrims as ls
KEY=lambda r:(r['opp_id'],r.get('refset'),r['map'],r['side'])
CONTEXT=['our_picks','opp_picks','draft','seed','engine','engine_hash','map_id','pin','refset','source_group']
SCORES=['result','rounds','our_gems','opp_gems','our_gold','opp_gold','our_kills','opp_kills','end_reason']


def dump(p,x):p.write_text(json.dumps(x,indent=2)+'\n')
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()


def collect_inputs():
    tasks={x['id']:x for x in ls.read_jsonl(ls.DATA/'tasks.jsonl') if x.get('version')==111 and x.get('purpose')=='set' and x.get('pin')=='ref'}
    events=ls.read_jsonl(ls.DATA/'events.jsonl')
    bad={x['group'] for x in events if x['ev']=='suspect'}
    creates=[x for x in events if x['ev']=='created' and x.get('live')==111 and x.get('task') in tasks and x['group'] not in bad]
    finished={x['group'] for x in events if x['ev']=='finished'}
    assert len(tasks)==104 and len(creates)==104 and {x['task'] for x in creates}==set(tasks), 'Normal104 groups not all created cleanly'
    assert all(x['group'] in finished for x in creates), 'Wait for all104 normal groups collected'
    raw=ls.read_jsonl(ls.DATA/'games.jsonl')
    groups={x['group']:x for x in creates}
    valid={}
    for x in raw:
        if x.get('version')!=111 or x['group'] not in groups:continue
        task=tasks[x['task']];game=task['games'][x['position']-1]
        assert x['status']=='finished' and x['result'] in ('win','loss') and x['pin']=='ref' and x['purpose']=='set'
        assert x['map_id']==game['map_id'] and x['map']==game['map'] and x['side']==game['side']
        assert bool(x['filler'])==bool(game.get('filler'))
        assert x.get('replay') and (R/x['replay']).exists()
        valid[x['match']]=x
    assert len(valid)==520 and collections.Counter(x['group'] for x in valid.values())==collections.Counter({g:5 for g in groups})
    allrows={}
    for v in (105,106,107,111):
        selected={}
        for x in raw:
            if x.get('version')!=v or x.get('purpose')!='set' or x.get('pin')!='ref' or x.get('filler') or x['group'] in bad:continue
            if x['result'] not in ('win','loss') or x.get('status')!='finished':continue
            if v==111:assert x['match'] in valid
            selected.setdefault(KEY(x),x)
        allrows[v]=selected
    assert len(allrows[111])==512
    for opp in {x['opp_id'] for x in allrows[111].values()}:
        cells=[x for x in allrows[111].values() if x['opp_id']==opp]
        assert len(cells)==256 and len({x['map'] for x in cells})==128
    dump(D/'input-rows.json',{str(v):list(rows.values()) for v,rows in allrows.items()})
    dump(D/'collection-proof.json',{'normal_tasks':104,'created_clean_groups':104,'collected_groups':104,
         'raw_matches':520,'excluded_fillers':sum(x['filler'] for x in valid.values()),'unique_normal_cells':512,
         'tasks':tasks,'creates':creates,'finished_events':[x for x in events if x['ev']=='finished' and x['group'] in groups],
         'excluded_purposes':['oppcheck'],'excluded_suspect_groups':sorted(bad&set(groups)),
         'input_rows_sha256':digest(D/'input-rows.json')})
    return allrows


ZIP={}
def raw_info(r):
    p=R/r['replay']
    if str(p) not in ZIP:
        with zipfile.ZipFile(p) as z:
            i=z.getinfo('replay.repl26a')
            ZIP[str(p)]={'path':str(p),'size':i.file_size,'crc32':i.CRC}
    return ZIP[str(p)]
def raw_sha(info):
    if 'sha256' not in info:
        with zipfile.ZipFile(info['path']) as z:
            with z.open('replay.repl26a') as f:
                h=hashlib.sha256()
                for chunk in iter(lambda:f.read(1024*1024),b''):h.update(chunk)
                info['sha256']=h.hexdigest()
    return info['sha256']
def identical(a,b):
    x,y=raw_info(a),raw_info(b)
    if (x['size'],x['crc32'])!=(y['size'],y['crc32']):return False,'different raw size/CRC proves inequality'
    return raw_sha(x)==raw_sha(y),'raw SHA256 compared after equal size/CRC'


def compare(rows,b):
    A,B=rows[111],rows[b];out={}
    for opp in sorted({k[0] for k in A}):
        keys=sorted(k for k in A.keys()&B.keys() if k[0]==opp)
        assert keys
        ds=[int(A[k]['result']=='win')-int(B[k]['result']=='win') for k in keys]
        md=collections.defaultdict(list)
        for k,d in zip(keys,ds):md[k[2]].append(d)
        assert all(len(v)==2 for v in md.values()), 'Require both sides in every included map cluster'
        mapmeans=[sum(v)/2 for v in md.values()];mean=sum(mapmeans)/len(mapmeans)
        se=math.sqrt(sum((v-mean)**2 for v in mapmeans)/(len(mapmeans)-1)/len(mapmeans))
        mismatches={f:sum(A[k].get(f)!=B[k].get(f) for k in keys) for f in CONTEXT}
        cells=[]
        for k,d in zip(keys,ds):
            same_context=all(A[k].get(f)==B[k].get(f) for f in CONTEXT)
            equal,method=identical(A[k],B[k]) if same_context else (None,'context mismatch: excluded from raw identity claim')
            cells.append({'map':k[2],'side':k[3],'refset':k[1],'delta':d,'candidate_match':A[k]['match'],'base_match':B[k]['match'],
                          'context_equal':same_context,'raw_replay_equal':equal,'identity_method':method,
                          'score_fingerprint_equal':all(A[k].get(f)==B[k].get(f) for f in SCORES)})
        ar=[x for k,x in A.items() if k[0]==opp]
        out[A[keys[0]]['opp_name']]={'candidate_total':len(ar),'candidate_total_wins':sum(x['result']=='win' for x in ar),
          'paired_cells':len(keys),'candidate_paired_wins':sum(A[k]['result']=='win' for k in keys),'base_paired_wins':sum(B[k]['result']=='win' for k in keys),
          'refsets':sorted({k[1] for k in keys}),'flips_for':ds.count(1),'flips_against':ds.count(-1),'maps':len(md),
          'map_cluster_mean_pp':100*mean,'map_cluster_approx_ci95_half_pp':196*se,
          'map_net_positive':sum(sum(v)>0 for v in md.values()),'map_net_negative':sum(sum(v)<0 for v in md.values()),
          'context_mismatches':mismatches,'identical_raw_replays':sum(x['raw_replay_equal'] is True for x in cells),
          'identical_score_fingerprints':sum(x['score_fingerprint_equal'] for x in cells),'cells':cells}
    return out


def main():
    rows=collect_inputs()
    provenance=json.loads((D/'provenance.json').read_text())
    for v,p in provenance['versions'].items():
        root=Path(p['history']['workspace'])/'bots/ocean/src'
        assert {str(x.relative_to(root)):digest(x) for x in root.rglob('*') if x.is_file()}==p['submitted_source']
    result={'at':ls.now(),'candidate':111,'primary_mask_confounded':{'base':105,'opponents':compare(rows,105)},
            'same_mask_different_feature_diagnostics':{str(b):compare(rows,b) for b in (106,107)},
            'source_provenance_sha256':digest(D/'provenance.json'),'collection_proof_sha256':digest(D/'collection-proof.json'),
            'local_gate':json.loads(Path('/home/ubuntu/tmp-offload/diverse/gate-logs/fgate-sm-greed--ocean-16d6f78p4q.json').read_text()),
            'caveats':['105 differs in mask as well as Greed; only80Miter5cells are shared, olderMitepins excluded.',
                       '106/107 share mask/SDK but differ in reserve+q1/shield respectively; neither isolatesGreed.',
                       'Map-cluster normal intervals are descriptive on this reused deterministic128-map suite, not fresh confirmation.',
                       'Known currentMite differs pinnedr5; pinned evaluation remains r5. No repin or new current-version inference.',
                       'Existing current-mask105control is prospective cleaner comparison, subject actual source/pin/context reverification.']}
    dump(D/'result.json',result);dump(D/'raw-replay-proofs.json',ZIP)
    for label,opps in [('105',result['primary_mask_confounded']['opponents']),*result['same_mask_different_feature_diagnostics'].items()]:
        for name,x in opps.items():print(label,name,json.dumps({k:v for k,v in x.items() if k!='cells'}))


if __name__=='__main__':main()
