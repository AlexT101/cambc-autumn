"""Full200k targeted-half tests on a new common pool, with no precision-only stop."""
import argparse
import importlib.util
import json
import math
from pathlib import Path
import random
import sys
import time

from run import R,D,BASE,CAND,write,sha,source,verify,body_seal
from stats import decision


def validate(fg, cand, ref, k):
    records=[]
    for o in 'FM':
        for tag,suite,games in fg.suites(k):
            directory=R/'maps' if suite=='ladder' else Path(suite)
            expected={(p.stem,side) for p in directory.glob('*.map26a') for side in 'ab'}
            assert len(expected)==games
            for bot in (ref,cand):
                name=fg.rname(bot,k,o,tag);sp=R/'replays/ab'/name/'summary.json';s=json.loads(sp.read_text())
                assert s['games']==games and s['errors']==0 and s['release'] is True and s['cambc']=='5.0.1' and s['fuel']==200000,name
                assert s['cand']['spec']==bot and s['ref']['spec']==fg.mdir(k,o),name
                cells=[];hashes={}
                for sub in s['suites']:
                    bp=R/sub['batch']/'results.json';b=json.loads(bp.read_text())
                    assert b['errors']==0 and b['completed']==b['scheduled']==games,name
                    for x in b['matches']:
                        assert x.get('winner') in (0,1) and x['order'] in ([0,1],[1,0]),name
                        cells.append((Path(x['map']).stem,'a' if x['order'][0]==0 else 'b'))
                    hashes[str(bp)]=sha(bp)
                assert len(cells)==len(set(cells))==games and set(cells)==expected,name
                records.append({'name':name,'summary_sha256':sha(sp),'results':hashes,
                                'draft_counts':{key:s.get(key) for key in ('early_losses','handoff_failures','capped_drafts')}})
    return {'noise':k,'records':records,'bodies':{fg.mdir(k,o):source(fg.mdir(k,o)) for o in 'FM'}}


def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('arm',choices=CAND);a=ap.parse_args()
    verify();p=json.loads((D/'protocol.json').read_text());on='M' if a.arm=='chanM' else 'F';off='F' if on=='M' else 'M'
    spec=importlib.util.spec_from_file_location('cond504_fgate',R/'research/ideas-2026-11-09/freshgate-tools/fgate.py')
    fg=importlib.util.module_from_spec(spec);spec.loader.exec_module(fg)
    first,last=1004,2003;fg.FUEL=200000;fg.BODY['F'],fg.BODY['M']='Flp4','Mt3q'
    fg.POOL=[str(D/'pool'/f'x{j}') for j in range(8)]
    fg.slice_of=lambda k:(k-first)%8
    fg.suites=lambda k:[('L','ladder',256),(f'x504f{fg.slice_of(k)}',fg.POOL[fg.slice_of(k)],2*len(list(Path(fg.POOL[fg.slice_of(k)]).glob('*.map26a'))))]
    for line in (D/'features.jsonl').read_text().splitlines():
        x=json.loads(line);fg.FT[x['name'].replace('_','-')]=x['f']
    runner=fg.Runner(4);u={'L':{},'fresh':{}};outcome=None;gain_h0=harm_h1=False;count=0
    audits=D/a.arm/'blocks';audits.mkdir(parents=True,exist_ok=True)
    for k in range(first,last+1):
        verify();fg.build_version(k);body_seal(k)
        while True:
            for o in 'FM':
                for tag,suite,games in fg.suites(k):
                    for bot in (BASE,CAND[a.arm]):runner.want(bot,k,o,tag,suite,games)
            if all(fg.done(fg.rname(bot,k,o,tag),games) for o in 'FM' for tag,_,games in fg.suites(k) for bot in (BASE,CAND[a.arm])):break
            time.sleep(1)
        record=validate(fg,CAND[a.arm],BASE,k);write(audits/f'{k}.json',record)
        for key,groups in fg.block_units(CAND[a.arm],BASE,k,random.Random(k)).items():
            for name,values in groups.items():u[key].setdefault(name,[]).extend(values)
        count+=1;target=u['fresh'][on];other=u['fresh'][off]
        gain=fg.ab.llr(target,.5000,.5025);harm=fg.ab.llr(target,.4975,.5000);oh=fg.ab.llr(other,.4975,.5000);broad=fg.ab.llr(target,.505,.5075)
        outcome,gain_h0,harm_h1=decision(gain,harm,oh,gain_h0,harm_h1)
        print(f'block {count} noise {k}: target{on} {fg.est(target)} n={len(target)} gainLLR={gain:+.3f} harmLLR={harm:+.3f}; off{off} {fg.est(other)} harmLLR={oh:+.3f}; broad diagnostic={broad:+.3f}; {outcome or "continue"}',flush=True)
        if outcome:break
    while runner.procs:runner.poll();time.sleep(1)
    result={'arm':a.arm,'cand':CAND[a.arm],'ref':BASE,'on':on,'off':off,'fuel':200000,'engine':fg.CAMBC,'release':True,
            'outcome':outcome or 'UNRESOLVED:1000-block cap','blocks':count,'first_noise':first,'last_noise':k,
            'fresh_target':fg.est(target),'fresh_offtarget':fg.est(other),'fresh_all':fg.est(u['fresh']['all']),
            'fresh_fish':fg.est(u['fresh']['F']),'fresh_mite':fg.est(u['fresh']['M']),
            'ladder_fish':fg.est(u['L']['F']),'ladder_mite':fg.est(u['L']['M']),
            'fresh_target_units':len(target),'gain_llr':gain,'harm_llr':harm,'offtarget_harm_llr':oh,'broad_diagnostic_llr':broad,
            'gain_h0_crossed':gain_h0,'harm_h1_crossed':harm_h1,'manifest_sha256':sha(D/'manifest.json'),
            'note':'Target gain vs zero is primary; off-target effect remains a shipping constraint. No automatic100k, merge, live test or repeated run. Intervals are descriptive on repeated noise/map units; not distinct new maps each block.'}
    verify();write(D/a.arm/'result-200000.json',result)
    write(D/a.arm/'review-required.json',{'stage':'200k complete','result_sha256':sha(D/a.arm/'result-200000.json'),
          'decision':'Coordinator must review target and off-target evidence, any normal-fuel admission and final disposition before releasing next job.'})
    print(json.dumps(result),flush=True)

if __name__=='__main__':main()
