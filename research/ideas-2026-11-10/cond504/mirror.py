"""One fixed direct Ocean mirror sample: unique maps, both sides, no noise repeats."""
import argparse
import json
import math
from pathlib import Path
import statistics
import sys
from run import R,D,T,BASE,CAND,sha,write,command,pooled,verify


def paired_scores(rows, expected):
    cells={}
    for row in rows:
        assert row.get('winner') in (0,1) and row['order'] in ([0,1],[1,0]), 'Invalid result'
        cell=(Path(row['map']).stem,tuple(row['order']))
        assert cell not in cells, ('Duplicate mirror cell',cell)
        cells[cell]=int(row['winner']==0)
    want={(name,order) for name in expected for order in ((0,1),(1,0))}
    assert set(cells)==want, 'Missing or unexpected mirror map/side'
    return {name:(cells[(name,(0,1))]+cells[(name,(1,0))])/2 for name in sorted(expected)}


def prepare_maps():
    out=D/'mirror';out.mkdir(exist_ok=True)
    if (out/'maps.done').exists():return
    assert not (out/'maps.json').exists(), 'Partial mirror map preparation needs review'
    roots=[R/'maps',Path('/home/ubuntu/tmp-offload/diverse/fresh/pool'),Path('/home/ubuntu/tmp-offload/condarms/fresh/pool'),Path('/home/ubuntu/tmp-offload/localq/maps/dl'),D/'pool']
    seen=set();coverage=[]
    for root in roots:
        assert root.is_dir(), ('Missing novelty root',str(root))
        paths=list(root.glob('*.map26a') if root==R/'maps' else root.rglob('*.map26a'))
        assert paths, ('Empty novelty root',str(root))
        hashes={sha(p) for p in paths};seen.update(hashes)
        coverage.append({'path':str(root),'exists':True,'map_paths':len(paths),'distinct_hashes':len(hashes)})
    selected=[];seeds=[]
    for seed in range(2415000,2415036):
        if len(selected)==8192:break
        generated=out/'generated'/f'fresh-{seed}'
        assert not generated.exists(), 'Partial map generation needs review'
        pooled(['node','tools/mapgen/mapgen.mjs','suite','--jobs','1','--mix','ladder-v2','--seed',str(seed),'--out',generated],out/'maps.log')
        seeds.append(seed)
        for p in sorted(generated.glob('*.map26a')):
            h=sha(p)
            if h in seen or len(selected)==8192:continue
            seen.add(h);chunk=len(selected)%8;directory=out/'pool'/f'm{chunk}';directory.mkdir(parents=True,exist_ok=True)
            link=directory/p.name;assert not link.exists();link.symlink_to(p)
            selected.append({'path':str(link),'sha256':h,'chunk':chunk})
    assert len(selected)==len({x['sha256'] for x in selected})==8192
    write(out/'maps.json',{'selected':selected,'generated_seeds':seeds,'novelty_scope':coverage,
          'note':'Exact byte novelty in declared scope including main conditional pool. Fixed map sample shared across arms, never duplicated within an arm.'})
    write(out/'maps-seal.json',{str(out/'maps.json'):sha(out/'maps.json')})
    (out/'maps.done').write_text('complete\n')


def read_chunk(arm,j):
    name=f'exploit504-{arm}-ocean-mirror-m{j}-200k'
    sp=R/'replays/ab'/name/'summary.json';s=json.loads(sp.read_text())
    assert s['games']==2048 and s['errors']==0 and s['release'] is True and s['fuel']==200000 and s['cambc']=='5.0.1', name
    assert s['cand']['spec']==CAND[arm] and s['ref']['spec']==BASE,name
    rows=[];hashes={}
    for suite in s['suites']:
        path=R/suite['batch']/'results.json';b=json.loads(path.read_text())
        assert b['scheduled']==b['completed']==2048 and b['errors']==0,name
        rows.extend(b['matches']);hashes[str(path)]=sha(path)
    expected={Path(x['path']).stem for x in json.loads((D/'mirror/maps.json').read_text())['selected'] if x['chunk']==j}
    assert len(expected)==1024
    scores=paired_scores(rows,expected)
    return scores,{'name':name,'summary_sha256':sha(sp),'batches':hashes,
                  'draft_counts':{key:s.get(key) for key in ('early_losses','handoff_failures','capped_drafts')}}


def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('arm',choices=CAND);a=ap.parse_args();verify()
    prepare_maps();verify();scores={};audit=[]
    for j in range(8):
        verify();name=f'exploit504-{a.arm}-ocean-mirror-m{j}-200k'
        if not (R/'replays/ab'/name/'summary.json').exists():
            command([sys.executable,R/'tools/ab.py',CAND[a.arm],BASE,'--no-test-draft','--fuel','200000','--suites',D/'mirror/pool'/f'm{j}',
                     '--keep-replays','1','--name',name],D/a.arm/'mirror-runs.log')
        chunk,record=read_chunk(a.arm,j);assert not scores.keys() & chunk.keys()
        scores.update(chunk);audit.append(record)
    assert len(scores)==8192
    values=list(scores.values());mean=statistics.mean(values);se=statistics.stdev(values)/math.sqrt(len(values))
    ci=[max(0,mean-1.96*se),min(1,mean+1.96*se)]
    # A bounded empirical-Bernstein interval stays nondegenerate when every pair splits 1–1.
    radius=math.sqrt(2*statistics.variance(values)*math.log(40)/len(values))+7*math.log(40)/(3*(len(values)-1))
    bounded=[max(0,mean-radius),min(1,mean+radius)]
    result={'arm':a.arm,'candidate':CAND[a.arm],'opponent':BASE,'comparison':'absolute direct head-to-head, not replica performance delta',
            'fuel':200000,'engine':'5.0.1','release':True,'maps':8192,'games':16384,'candidate_wins':round(2*sum(values)),
            'winrate':mean,'map_paired_normal_95ci':ci,'map_paired_empirical_bernstein_95ci':bounded,
            'pair_counts':{str(x):values.count(x) for x in (0,.5,1)},'audit':audit,
            'interpretation':'Detected mirror harm' if ci[1]<.5 else 'Mirror requires joint coordinator review; crossing50 is not proof of safety',
            'manifest_sha256':sha(D/'manifest.json'),'map_manifest_sha256':sha(D/'mirror/maps.json'),
            'note':'Fixed sample, no sequential looks or noise repetition. Pair intervals average both sides per unique map. Normal approximation and conservative bounded interval assume sampled map pairs represent the stated generator distribution. No automatic extension, normal-fuel admission or shipping.'}
    write(D/a.arm/'mirror-paired-scores.json',scores);result['paired_scores_sha256']=sha(D/a.arm/'mirror-paired-scores.json')
    verify();write(D/a.arm/'mirror-result-200000.json',result);print(json.dumps(result),flush=True)

if __name__=='__main__':main()
