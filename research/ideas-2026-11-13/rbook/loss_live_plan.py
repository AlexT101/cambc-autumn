"""Prepare live coverage and collateral checks for a locally verified loss-only book. No API calls."""
import argparse
import json
from pathlib import Path

from refresh_build import ls
from refresh_queue import write


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


def plan(work):
    state = json.loads((work/'build-state.json').read_text())
    if state['phase'] != 'ready_for_live_checks':
        raise RuntimeError('Local verification must finish before planning live checks')
    version,pins = state['host_version'],state['pins']
    entries = json.loads((work/'book_cells.json').read_text())
    forced = set((work/'force.txt').read_text().splitlines())
    baseline = {(r['opp_name'].split()[-1].lower(),r['map'],r['side']):r for r in ls.games(version)
                if r.get('purpose') == 'set' and r.get('pin') == 'ref'
                and pins.get(r['opp_name'].split()[-1].lower()) == r.get('refset')}
    sources = source_rows(work,pins)
    checks = coverage(entries,forced,baseline,sources,pins)
    steps,expected = [],[]
    for opp,pin in pins.items():
        cells = sorted([list(k[1:]) for k in checks if k[0] == opp])
        if not cells:
            continue
        sid = f'loss-v{version}-{opp}-{pin}'
        path = work/f'live-{opp}-pinned.json';write(path,cells)
        steps.append([str(path),sid,opp,pin,version,'ref'])
        expected += [dict(step=sid,opponent=opp,map=m,side=s,pin='ref',refset=pin,
                         **checks[(opp,m,s)]) for m,s in cells]
    # Latest-opponent checks are coverage checks, not a book-free strength comparison.
    for opp,pin in pins.items():
        candidates = sorted((c for c in entries if c['opp'] == opp),
                            key=lambda c:(c['key'] not in forced,c['map'],c['side']))
        cells = sorted({(c['map'],c['side']) for c in candidates[:20 if opp=='mite' else 10]})
        if not cells:
            continue
        sid = f'loss-v{version}-{opp}-current'
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
