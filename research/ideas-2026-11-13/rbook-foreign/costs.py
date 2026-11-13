"""What a forced pick costs on each verified entry's cell: who else meets it.

    py costs.py WORK [--rows TSV.gz ...] > WORK/costs.tsv
For the entries WORK/verify.json reproduced (forced.py's WORK/classes.json): the pick at which the draft departs from
525's, the Fish picks seen by then, whether Mite r9 opens the same on the map (so meets the forced pick too), and the
share of other teams' drafts against Fish on the map that open with Fish's prefix (a proxy for the rest of the ladder;
a blind entry's pick 0 meets every opponent on the cell)."""
import argparse, collections, gzip, json
from pathlib import Path

from cells import COLS, FISH, NAMES, OURS


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('work')
    ap.add_argument('--rows', nargs='*', default=[str(Path.home() / f'tmp-offload/rbook-foreign/rows/{f}') for f in ('fish-1112early.tsv.gz', 'fish-1113b.tsv.gz')])
    a = ap.parse_args()
    W = Path(a.work).expanduser()
    cl = json.load(open(W / 'classes.json'))
    ok = {k for k, v in json.load(open(W / 'verify.json')).items() if v is None}
    opens = collections.defaultdict(list)
    for f in a.rows:
        for line in gzip.open(f, 'rt'):
            p = line.rstrip('\n').split('\t')
            if len(p) != len(COLS):
                continue
            r = dict(zip(COLS, p))
            o = 'b' if r['team_a'] == FISH else 'a'
            if r['team_' + o].startswith(OURS):
                continue
            try:
                opens[r['map']].append(json.loads(r['picks_' + o]))
            except Exception:
                pass
    nm = lambda ps: '/'.join(NAMES[i].split()[0] for i in ps) or '-'
    print('key\tcell\tclass\tdeparts_at\tfish_seen\tours_525\tforced\tmite_meets\tladder_share_prefix\topp\trounds')
    for k, v in sorted(cl.items()):
        if k not in ok:
            continue
        d = v['departs_at_pick']
        pre = v['fish'][:d] if d is not None else None
        share = '' if d is None else f"{sum(o[:d] == pre for o in opens[v['cell'].split(':')[0]])}/{len(opens[v['cell'].split(':')[0]])}"
        print('\t'.join(map(str, [k, v['cell'], v['klass'], '' if d is None else d, nm(pre or []) if d is not None else '', nm(v['ours']), nm(v['theirs']),
                                  '' if v['mite_meets_forced'] is None else v['mite_meets_forced'], share, v['opp'], v['rounds']])))


if __name__ == '__main__':
    main()
