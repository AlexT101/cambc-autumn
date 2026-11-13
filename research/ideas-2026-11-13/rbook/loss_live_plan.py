"""Prepare live coverage and collateral checks for a locally verified loss-only book. No API calls."""
import argparse
import json
from pathlib import Path

from refresh_build import ls
from refresh_queue import write


def step_prefix(state):
    version = state['host_version']
    default = f'rbook-loss-v{version}'
    name = Path(state.get('bot',default)).name
    return f'loss-v{version}' if name == default else name.removeprefix('rbook-')


def source_rows(work, pins):
    rows = {r['match'][-12:]:r for r in ls.read_jsonl(ls.DATA/'games.jsonl')}
    extra = work/'foreign-metadata.json'
    if extra.exists():
        for key,row in json.loads(extra.read_text()).items():
            if row.get('target_refset') != pins.get(row.get('opp')):
                raise RuntimeError(f'Foreign candidate targets another pin: {key}')
            if row.get('qualification') != 'local_exact_live_pending':
                raise RuntimeError(f'Foreign candidate lacks local qualification: {key}')
            rows[key.rsplit('-',1)[1]] = row
    return rows


def coverage(entries, forced, baseline, sources, opponents):
    checks = {}
    for entry in entries:
        cell = (entry['map'],entry['side'])
        key = (entry['opp'],*cell)
        if key not in baseline or baseline[key]['result'] != 'loss':
            raise RuntimeError(f'Entry is not a confirmed host loss: {key}')
        source = sources[entry['key'].rsplit('-',1)[1]]
        base = baseline[key]
        known_win = (source.get('result') == 'win' and source.get('pin') == 'ref'
                     and source.get('refset') == base.get('refset')
                     and source.get('opp_id') == base.get('opp_id'))
        if not known_win:
            checks[key] = dict(require_win=True,reason='book entry needs target-pin validation')
        for other in opponents:
            other_key = (other,*cell)
            if other == entry['opp']:
                continue
            if other_key not in baseline:
                raise RuntimeError(f'Missing collateral baseline: {other_key}')
            base = baseline[other_key]
            same_draft = (source['our_picks'] == base['our_picks']
                          and source['opp_picks'] == base['opp_picks'])
            if (entry['key'] in forced or same_draft) and base['result'] == 'win':
                checks.setdefault(other_key,dict(require_win=True,
                    reason='forced draft collateral' if entry['key'] in forced else 'shared draft collateral'))
    return checks


def required_checks(entries, forced, baseline, sources, opponents, policy=None):
    checks=coverage(entries,forced,baseline,sources,opponents)
    seen=set()
    for recovery in (policy or {}).get('recovery_cells',[]):
        key=(recovery['opponent'],recovery['map'],recovery['side'])
        if (key in seen or key[0] not in opponents or key[2] not in ('a','b')
                or baseline.get(key,{}).get('result') != 'win'):
            raise RuntimeError(f'Recovery check lacks unique matching host win: {key}')
        if any((e['map'],e['side'])==key[1:] for e in entries):
            raise RuntimeError(f'Recovery cell still has a book entry: {key}')
        seen.add(key)
        checks[key]=dict(require_win=True,reason='removed forced entry: restore known host win')
    return checks


def plan(work):
    state = json.loads((work/'build-state.json').read_text())
    if state['phase'] != 'ready_for_live_checks':
        raise RuntimeError('Local verification must finish before planning live checks')
    policy_path=work/'validation-policy.json'
    policy=json.loads(policy_path.read_text()) if policy_path.exists() else {}
    if policy:
        if policy.get('pinned_only') is not True or not policy.get('reason'):
            raise RuntimeError('Invalid explicit live validation policy')
        state['current_opponent_checks']=False
        state['validation_policy']=policy
        write(work/'build-state.json',state)
    version,pins = state['host_version'],state['pins']
    prefix = step_prefix(state)
    entries = json.loads((work/'book_cells.json').read_text())
    forced = set((work/'force.txt').read_text().splitlines())
    baseline = {(r['opp_name'].split()[-1].lower(),r['map'],r['side']):r for r in ls.games(version)
                if r.get('purpose') == 'set' and r.get('pin') == 'ref'
                and pins.get(r['opp_name'].split()[-1].lower()) == r.get('refset')}
    sources = source_rows(work,pins)
    checks = required_checks(entries,forced,baseline,sources,pins,state.get('validation_policy'))
    steps,expected = [],[]
    for opp,pin in pins.items():
        cells = sorted([list(k[1:]) for k in checks if k[0] == opp])
        if not cells:
            continue
        sid = f'{prefix}-{opp}-{pin}'
        path = work/f'live-{opp}-pinned.json';write(path,cells)
        steps.append([str(path),sid,opp,pin,version,'ref'])
        expected += [dict(step=sid,opponent=opp,map=m,side=s,pin='ref',refset=pin,
                         **checks[(opp,m,s)]) for m,s in cells]
    # Latest-opponent samples are optional only under an explicit essential-pinned-only policy.
    for opp,pin in (pins.items() if state.get('current_opponent_checks',True) else []):
        candidates = sorted((c for c in entries if c['opp'] == opp),
                            key=lambda c:(c['key'] not in forced,c['map'],c['side']))
        cells = sorted({(c['map'],c['side']) for c in candidates[:20 if opp=='mite' else 10]})
        if not cells:
            continue
        sid = f'{prefix}-{opp}-current'
        path = work/f'live-{opp}-current.json';write(path,cells)
        steps.append([str(path),sid,opp,pin,version,'none'])
        expected += [dict(step=sid,opponent=opp,map=m,side=s,pin='none',refset=None,
                         require_win=True,reason='current opponent coverage; handover wins qualify') for m,s in cells]
    write(work/'live-steps.json',steps)
    write(work/'live-expectations.json',expected)
    write(work/'live-plan.json',dict(phase='prepared',host_version=version,pins=pins,
          book_entries=len(entries),pinned_cells=len(checks),current_cells=len(expected)-len(checks),
          note='No upload performed. Same-pin source wins rely on completed combined-book exact replay verification; '
               'live pin checks cover provisional sources and collateral host wins. '
               'Validate exact task provenance, full collection and zero suspect groups. '
               'Required wins include collateral host wins. Replay divergence alone is not failure.'))


if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--work',type=Path,required=True)
    plan(ap.parse_args().work)
