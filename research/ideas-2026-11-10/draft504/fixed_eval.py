"""Fixed map-cluster comparisons for the three predeclared draft17 approaches."""
import argparse
from collections import defaultdict
import importlib.util
import json
from pathlib import Path
import sys
import time

import numpy as np
from run import R, D, T, BASE, sha, source, write, verify
from audit import validate_block

STAGES = {'selection': (200000, 1, 64), 'confirmation': (200000, 65, 192), 'normal': (100000, 193, 320)}


def estimate(differences):
    a = np.asarray(differences, dtype=float)
    assert len(a) >= 2 and np.isfinite(a).all()
    mean = float(a.mean()); half = float(1.96 * a.std(ddof=1) / np.sqrt(len(a)))
    return {'maps': len(a), 'delta': mean, 'halfwidth': half, 'lower': mean-half, 'upper': mean+half}


def choose(comparisons):
    eligible = [name for name in ('flat', 'conditional') if name in comparisons and comparisons[name]['lower'] > 0]
    return max(eligible, key=lambda name: (comparisons[name]['delta'], name == 'flat')) if eligible else 'control'


def compare(scores, cand, ref, picks):
    assert set(scores[cand]) == set(scores[ref]) == set(picks)
    group = defaultdict(list)
    for m in sorted(picks):
        a, b = scores[cand][m], scores[ref][m]
        assert set(a) == set(b) == {'F', 'M'}
        diffs = {}
        for o in 'FM':
            assert set(a[o]) == set(b[o])
            diffs[o] = float(np.mean([a[o][cell] - b[o][cell] for cell in sorted(a[o])]))
            group[o].append(diffs[o])
        value = (diffs['F'] + diffs['M']) / 2
        group['all'].append(value); group['picks'+str(picks[m])].append(value)
    return {g: estimate(v) for g,v in group.items()}


def collect(fg, bots, first, last, picks, expected_repeats):
    scores = {bot: defaultdict(lambda: defaultdict(dict)) for bot in bots}
    for k in range(first,last+1):
        for tag,suite,_ in fg.suites(k):
            if suite == 'ladder': continue
            for o in 'FM':
                for bot in bots:
                    cells=fg.local.cells(fg.rname(bot,k,o,tag))
                    for (m,side),value in cells.items():
                        key=(k,str(side)); assert key not in scores[bot][m][o]
                        scores[bot][m][o][key]=value
    for bot in bots:
        assert set(scores[bot]) == set(picks)
        for m in picks:
            assert set(scores[bot][m]) == {'F','M'}
            assert all(len(scores[bot][m][o]) == 2*expected_repeats for o in 'FM')
    return scores


def ladder_scores(fg, bots, noise):
    scores = {bot: defaultdict(lambda: defaultdict(dict)) for bot in bots}
    for bot in bots:
        for o in 'FM':
            for (m, side), value in fg.local.cells(fg.rname(bot, noise, o, 'L')).items():
                scores[bot][m][o][(noise, str(side))] = value
    features = json.loads((D / 'inputs/preferences/features.json').read_text())
    picks = {v['name']: v['picks'] for v in features.values()}
    assert len(picks) == 128
    for bot in bots:
        assert set(scores[bot]) == set(picks)
        assert all(len(scores[bot][m][o]) == 2 for m in picks for o in 'FM')
    return scores, picks


def diagnostic_counts(audits):
    unique = {}
    for path in sorted(audits.glob('*.json')):
        for pair in json.loads(path.read_text())['records']:
            for record in pair['records']:
                name = record['name']
                assert name not in unique or unique[name] == record['counts']
                unique[name] = record['counts']
    totals = {kind: {'cand': 0, 'ref': 0, 'unknown_runs': 0}
              for kind in ('early_losses', 'handoff_failures', 'capped_drafts')}
    for counts in unique.values():
        for kind, total in totals.items():
            value = counts.get(kind)
            if not isinstance(value, dict) or any(side not in value for side in ('cand', 'ref')):
                total['unknown_runs'] += 1
            else:
                for side in ('cand', 'ref'): total[side] += value[side]
    return {'unique_runs': len(unique), 'totals': totals,
            'policy': 'Outcomes retained; counts reported for coordinator validity review, never silently excluded.'}


def run(stage):
    verify()
    arms=json.loads((D/'arms.json').read_text())
    aliases=arms['aliases']; dirs=arms['bots']
    if stage=='selection': names=list(dirs)
    else:
        selected=json.loads((D/'selection.json').read_text())['selected']
        names=list(dict.fromkeys([selected,'control']))
    bots=list(dict.fromkeys([BASE,*(dirs[name] for name in names)]))
    for name in names:
        assert source(dirs[name])==json.loads((D/'candidate-sources'/f'{name}.json').read_text())
    spec=importlib.util.spec_from_file_location('draft17_fixed_fgate',R/'research/ideas-2026-11-09/freshgate-tools/fgate.py')
    fg=importlib.util.module_from_spec(spec);spec.loader.exec_module(fg)
    fuel,first,last=STAGES[stage];fg.FUEL=fuel;fg.BODY={'F':'Flp4','M':'Mt3q'}
    pool=D/'evaluation-maps'/stage
    fg.POOL=[str(pool/f'f{j}') for j in range(8)]
    def suites(k):
        j=(k-first)%8; path=fg.POOL[j]
        out=[(f'qdraft17-{stage}-f{j}',path,2*len(list(Path(path).glob('*.map26a'))))]
        if k==first and stage in ('selection','normal'):out.append(('L','ladder',256))
        return out
    fg.suites=suites
    maps=json.loads((D/'maps.json').read_text())['selected'][stage]
    feature_rows=[json.loads(s) for s in (pool/'feat.jsonl').read_text().splitlines() if s]
    picks={r['name'].replace('_','-'):r['picks'] for r in feature_rows}
    assert len(picks)==len(maps)==1024
    fg.FT.update({r['name'].replace('_','-'):r['f'] for r in feature_rows})
    audits=D/f'{stage}-blocks';audits.mkdir(exist_ok=True)
    class StrictRunner(fg.Runner):
        def poll(self):
            for name, (process, _) in self.procs.items():
                code = process.poll()
                if code is not None and code != 0:
                    raise RuntimeError(f'Incomplete or failed AB child {name}: exit {code}; explicit recovery required')
            super().poll()
    runner=StrictRunner(4)
    sys.path.insert(0,str(R/'tools'));from gate_compile_ahead import scope, wait_drained
    import cpu_slots
    try:
        with scope(D/f'compile-ahead-{stage}',D/'manifest.json',audits,Path(fg.__file__),['Flp4','Mt3q'],first=first,last=last):
            for k in range(first,last+1):
                verify()
                held = cpu_slots.acquire(1)
                try: fg.build_version(k)
                finally: cpu_slots.release(held)
                while not all(fg.done(fg.rname(bot,k,o,tag),g) for bot in bots for o in 'FM' for tag,_,g in suites(k)):
                    for bot in bots:
                        for o in 'FM':
                            for tag,suite,g in suites(k):runner.want(bot,k,o,tag,suite,g)
                    time.sleep(1)
                records=[validate_block(fg,bot,BASE,k,fuel) for bot in bots if bot!=BASE]
                write(audits/f'{k:04d}.json',{'block':k,'records':records})
                print(f'{stage} complete block {k-first+1}/{last-first+1}; no interim outcome decision',flush=True)
    finally:
        # Drain outstanding scored children before returning a failed stage to the queue.
        codes = [wait_drained(process) for process,_ in list(runner.procs.values())]
        fg.dgate.Runner.poll(runner)
        assert all(code == 0 for code in codes), 'Failed scored child: stage held for explicit recovery'
    scores=collect(fg,bots,first,last,picks,(last-first+1)//8)
    summaries={name:compare(scores,dirs[name],BASE,picks) for name in names}
    result={'phase':stage,'fuel':fuel,'first_noise':first,'last_noise':last,'manifest_sha256':sha(D/'manifest.json'),
            'maps':len(picks),'vs506':summaries,'cluster':'map, averaging all noise realizations, sides and both opponents',
            'z':1.96,'source_hashes':{name:sha(D/'candidate-sources'/f'{name}.json') for name in names},
            'diagnostic_counts': diagnostic_counts(audits),
            'ladder_diagnostics':'selection noise1 cells reused for confirmation; normal noise193 uses new fuel cells'}
    if stage in ('selection', 'normal'):
        ladder, ladder_picks = ladder_scores(fg, bots, first)
        result['ladder_vs506'] = {name: compare(ladder, dirs[name], BASE, ladder_picks) for name in names}
        result['ladder_vs_control'] = {name: compare(ladder, dirs[name], dirs['control'], ladder_picks)
                                       for name in names if name != 'control'}
    else:
        old = json.loads((D/'selection.json').read_text())
        result['ladder_vs506'] = {name: old['ladder_vs506'][name] for name in names}
        result['ladder_vs_control'] = {name: old['ladder_vs_control'][name] for name in names if name != 'control'}
    if stage=='selection':
        comparisons={name:compare(scores,dirs[name],dirs['control'],picks) for name in names if name!='control'}
        selected=choose({name:value['all'] for name,value in comparisons.items()})
        result.update(vs_control=comparisons,selected=selected,aliases=aliases,
                      decision='Two fixed one-sided comparisons, Bonferroni family alpha .05; control if neither qualifies')
    else:
        selected=json.loads((D/'selection.json').read_text())['selected']
        tests={'vs506':summaries[selected]['all']}
        if selected!='control':
            result['vs_control']=compare(scores,dirs[selected],dirs['control'],picks)
            tests['vs_control']=result['vs_control']['all']
        result.update(selected=selected,positive_gain=all(s['lower']>0 for s in tests.values()),
                      decision='Coordinator review required; no automatic normal fuel, merge, live test or refill')
    verify()
    for name in names:
        assert source(dirs[name]) == json.loads((D/'candidate-sources'/f'{name}.json').read_text())
    write(D/f'{stage}.json',result)
    if stage!='selection':write(D/'review-required.json',{'stage':stage,'result':str(D/f'{stage}.json'),
                              'result_sha256':sha(D/f'{stage}.json'),'positive_gain':result['positive_gain']})


if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('stage',choices=STAGES);run(ap.parse_args().stage)
