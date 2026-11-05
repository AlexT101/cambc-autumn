"""Verify frozen fourth-cohort identity, raw hashes, drafts and feature provenance."""
import argparse
import collections
import gzip
import hashlib
import json
from pathlib import Path
from breadth import static_groups,xy
from holder_model import RANK


def main(manifest,cache,source,out):
    root=Path('research/fish-2026-11-05');freeze=json.loads((root/'routes-freeze.json').read_text())
    assert hashlib.sha256(Path(manifest).read_bytes()).hexdigest()==freeze['manifest_sha256']
    for p,h in freeze['files'].items():assert hashlib.sha256(Path(p).read_bytes()).hexdigest()==h,p
    old=[e for n in ('manifest.json','confirmation-manifest.json','third-manifest.json') for e in json.loads((root/n).read_text())]
    entries=json.loads(Path(manifest).read_text())
    for k in ('sha256','match','group'):
        assert not ({e[k] for e in entries if e[k]} & {e[k] for e in old if e[k]}),k
    rows=collections.defaultdict(list)
    for line in gzip.open(source,'rt'):
        r=json.loads(line);rows[r['game']].append(r)
    checked=collections.Counter();engines=collections.Counter();drafts=0
    for e in entries:
        assert hashlib.sha256(Path(e['file']).read_bytes()).hexdigest()==e['sha256']
        key=e['sha256'][:16]
        with gzip.open(Path(cache)/(key+'.json.gz')) as f:g=json.load(f)
        engines[g['engine']]+=1;_,at=static_groups(g['map'])
        detail=json.loads((Path(e['file']).parent/'group.json').read_text())
        match=next(m for m in detail['matches'] if m['id']==e['match'])
        for side in match['sides']:
            expected=[]
            for pick in map(int,side['draft']):expected.extend([3,4] if pick==3 else [pick if pick<3 else pick+1])
            actual=[c['type'] for c in g['roster'] if c['team']==(0 if side['side']=='a' else 1)]
            assert expected==actual
        drafts+=1
        turns={t['step']:t for t in g['turns']}
        for r in rows[key]:
            t=turns[r['step']];s=t['start'];m=s['me'];x=r['x']
            assert (t['round'],t['id'])==(r['round'],r['actor'])
            for a,b in [('hp','hp'),('maxhp','maxHp'),('type','type'),('gems','gems'),('gold','gold'),('channel','channelType'),('timer','channelTimer')]:assert x[a]==m[b]
            assert x['ally_gems']==sum(c['gems'] for c in s['allies'])
            if r['kind']=='incoming':
                assert x['holders']==[c for c in s['allies'] if at.get(xy(c))==x['group']]
                assert x['best_rank']==min(RANK[c['type']] for c in x['holders'])
                assert r['y']['joined']==(t['end']['me']['alive'] and at.get(xy(t['end']['me']))==x['group'])
            if r['kind'] in ('route','trip'):
                for c in x['candidates']:
                    assert c['visits']>=0 and c['route_count']>=0
                    for k in ('visit_age','ally_age'):assert c[k] is None or 0<c[k]<=r['round']
                    assert c['age'] is None or 0<=c['age']<=r['round']
            checked[r['kind']]+=1
    record=dict(games=len(entries),engines=engines,drafts_checked=drafts,observations_checked=checked,
                all_three_cohorts_disjoint=True,frozen_hashes_match=True,
                note='Known group ids checked; the 96-game cohort lacks group ids. Age checks and start-state checks verify provenance bounds, not independent correctness of all derived route-history counts. Raw input audit is separate.')
    with Path(out).open('x') as f:json.dump(record,f,indent=2);f.write('\n')
    print(json.dumps(record,indent=2))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for a in ('manifest','cache','source','out'):p.add_argument(a)
    a=p.parse_args();main(a.manifest,a.cache,a.source,a.out)
