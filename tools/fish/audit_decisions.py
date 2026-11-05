"""Check third-cohort identity/drafts, frozen hashes and observation start-state provenance."""
import argparse
import collections
import gzip
import hashlib
import json
from pathlib import Path


def main(manifest, cache, observations, out):
    root=Path('research/fish-2026-11-05')
    freeze=json.loads((root/'decision-freeze.json').read_text())
    assert hashlib.sha256(Path(manifest).read_bytes()).hexdigest()==freeze['manifest_sha256']
    for p,h in freeze['files'].items():
        assert hashlib.sha256(Path(p).read_bytes()).hexdigest()==h,p
    entries=json.loads(Path(manifest).read_text())
    older=[e for name in ('manifest.json','confirmation-manifest.json') for e in json.loads((root/name).read_text())]
    for key in ('sha256','match','group'):
        assert not ({e[key] for e in entries if e[key]} & {e[key] for e in older if e[key]}),key
    rows=collections.defaultdict(list)
    with gzip.open(observations,'rt') as f:
        for line in f:
            r=json.loads(line); rows[r['game']].append(r)
    engine=collections.Counter(); checked=collections.Counter(); drafts=0
    for e in entries:
        assert hashlib.sha256(Path(e['file']).read_bytes()).hexdigest()==e['sha256']
        with gzip.open(Path(cache)/(e['sha256'][:16]+'.json.gz')) as f:g=json.load(f)
        engine[g['engine']]+=1
        detail=json.loads((Path(e['file']).parent/'group.json').read_text())
        match=next(m for m in detail['matches'] if m['id']==e['match'])
        for side in sorted(match['sides'], key=lambda s:s['side']):
            actual=[c['type'] for c in g['roster'] if c['team']==(0 if side['side']=='a' else 1)]
            expected=[]
            for pick in map(int,side['draft']):
                expected.extend([3,4] if pick==3 else [pick if pick<3 else pick+1])
            assert actual==expected,(e['match'],actual,expected)
            if side['teamName']=='Intercontinental Fish':assert e['side']==(0 if side['side']=='a' else 1)
        drafts+=1
        turns={t['step']:t for t in g['turns']}
        for row in rows[e['sha256'][:16]]:
            t=turns[row['step']];m=t['start']['me'];x=row['x']
            assert (row['round'],row['actor'])==(t['round'],t['id'])
            for a,b in [('type','type'),('hp','hp'),('maxhp','maxHp'),('gold','gold'),('gems','gems'),('channel','channelType'),('timer','channelTimer')]:
                assert x[a]==m[b],(row['kind'],a)
            if row['kind']=='destination':
                for c in x['candidates']:
                    assert c['age'] is None or 0<=c['age']<=row['round']
            checked[row['kind']]+=1
    result=dict(games=len(entries),engines=engine,ordered_draft_matches=drafts,
                disjoint_from_both_older_cohorts=True,frozen_hashes_match=True,
                start_state_observations_checked=checked,
                note='Group-id disjointness is checked where older group ids exist; the 96-game cohort has no group ids. Raw action accounting is in third-audit.json.')
    Path(out).write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('manifest');p.add_argument('cache');p.add_argument('observations');p.add_argument('out')
    a=p.parse_args();main(a.manifest,a.cache,a.observations,a.out)
